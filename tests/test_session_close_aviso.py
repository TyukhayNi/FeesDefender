"""Aviso de cierre: trabajo grapado (commits) que no ha llegado al archivo central.

Prueba la lógica pura de detección (`_trabajo_sin_publicar`) monkeypatcheando las
dos consultas a git (`_git_lines` para enumerar ramas, `_git_count` para contar
commits por rango). Sin tocar git real.
"""

import scripts.session_close as sc


def _fake_lines(mapa):
    """Devuelve un _git_lines falso: mapea el 1er arg del comando a su salida."""
    def _inner(args):
        return mapa.get(args[0], [])
    return _inner


def test_detecta_rama_con_commits_sin_pushear(monkeypatch):
    # Una rama local con upstream, 3 commits por delante del archivo central.
    monkeypatch.setattr(
        sc, "_git_lines",
        _fake_lines({"for-each-ref": ["feat/x\torigin/feat/x"]}),
    )
    monkeypatch.setattr(
        sc, "_git_count",
        lambda rango: 3 if rango == ["origin/feat/x..feat/x"] else 0,
    )

    filas = sc._trabajo_sin_publicar()

    assert filas == [("feat/x", 3, "sin_publicar")]


def test_detecta_rama_nunca_subida(monkeypatch):
    # Rama local SIN upstream, con 5 commits propios sobre origin/main.
    monkeypatch.setattr(
        sc, "_git_lines",
        _fake_lines({"for-each-ref": ["feat/nueva\t"]}),
    )
    monkeypatch.setattr(
        sc, "_git_count",
        lambda rango: 5 if rango == ["origin/main..feat/nueva"] else 0,
    )

    filas = sc._trabajo_sin_publicar()

    assert filas == [("feat/nueva", 5, "nunca_subida")]


def test_nada_pendiente_cuando_todo_esta_publicado(monkeypatch):
    # Dos ramas, ambas al día con su upstream (0 commits por delante).
    monkeypatch.setattr(
        sc, "_git_lines",
        _fake_lines({"for-each-ref": [
            "main\torigin/main",
            "feat/y\torigin/feat/y",
        ]}),
    )
    monkeypatch.setattr(sc, "_git_count", lambda rango: 0)

    filas = sc._trabajo_sin_publicar()

    assert filas == []


def test_aviso_lista_ramas_y_recuerda_el_pr(monkeypatch, capsys):
    monkeypatch.setattr(sc, "_git_lines", _fake_lines({"branch": ["feat/x"]}))
    monkeypatch.setattr(
        sc, "_trabajo_sin_publicar",
        lambda: [("feat/x", 3, "sin_publicar")],
    )

    sc._avisar_publicacion()
    salida = capsys.readouterr().out

    assert "feat/x" in salida
    assert "3" in salida
    assert "PR" in salida  # recuerda la vía rama + PR


def test_aviso_sin_pendientes_dice_todo_publicado(monkeypatch, capsys):
    monkeypatch.setattr(sc, "_git_lines", _fake_lines({"branch": ["main"]}))
    monkeypatch.setattr(sc, "_trabajo_sin_publicar", lambda: [])

    sc._avisar_publicacion()
    salida = capsys.readouterr().out

    assert "main" in salida
    assert "sin commits sin publicar" in salida.lower() or "nada que llevar" in salida.lower()


# --- Coherencia PLAN.md <-> git: item pendiente que cita una rama fantasma ---

def test_plan_flag_rama_fantasma_en_bloque_pendiente():
    # El item describe trabajo PENDIENTE en una rama que git ya no conoce.
    texto = (
        "### [FOO] algo\n"
        "Rama de trabajo: `feat/foo` (worktree ~/Dev/x). Sin commitear aún.\n"
        "- [x] hecho\n"
    )
    filas = sc._plan_items_desfasados(texto, {"main"})
    assert filas == [("[FOO] algo", ["feat/foo"])]


def test_plan_no_flag_si_la_rama_existe():
    # La rama sigue viva en git -> el item es coherente, no se avisa.
    texto = "### [FOO]\nRama de trabajo: `feat/foo`. Sin commitear aún.\n"
    filas = sc._plan_items_desfasados(texto, {"feat/foo", "main"})
    assert filas == []


def test_plan_no_flag_item_completado_aunque_la_rama_este_podada():
    # Item ✅ sin frase de pendiente: cita una rama podada, pero no es drift.
    texto = (
        "### ✅ [FOO] COMPLETA\n"
        "MERGEADA a main. Rama `feat/foo` y worktree ya podados.\n"
    )
    filas = sc._plan_items_desfasados(texto, {"main"})
    assert filas == []


def test_plan_no_flag_rama_futura_sin_frase_de_pendiente():
    # Menciona una rama que aun no existe, pero no afirma trabajo en curso.
    texto = "### [FOO]\nEn el futuro se usara la rama `feat/foo`.\n"
    filas = sc._plan_items_desfasados(texto, {"main"})
    assert filas == []


def test_aviso_plan_desfasado_lista_las_ramas_fantasma(monkeypatch, capsys, tmp_path):
    (tmp_path / "PLAN.md").write_text("contenido", encoding="utf-8")
    monkeypatch.setattr(sc, "ROOT", tmp_path)
    monkeypatch.setattr(sc, "_ramas_conocidas", lambda: {"main"})
    monkeypatch.setattr(
        sc, "_plan_items_desfasados", lambda t, r: [("[FOO] algo", ["feat/foo"])]
    )

    sc._avisar_plan_desfasado()
    salida = capsys.readouterr().out

    assert "feat/foo" in salida
    assert "PLAN.md" in salida


def test_aviso_plan_coherente_no_alarma(monkeypatch, capsys, tmp_path):
    (tmp_path / "PLAN.md").write_text("contenido", encoding="utf-8")
    monkeypatch.setattr(sc, "ROOT", tmp_path)
    monkeypatch.setattr(sc, "_ramas_conocidas", lambda: {"main"})
    monkeypatch.setattr(sc, "_plan_items_desfasados", lambda t, r: [])

    sc._avisar_plan_desfasado()
    salida = capsys.readouterr().out

    assert "PLAN.md" in salida
    assert "[!]" not in salida


# --- Higiene de PLAN.md: detectores puros (D3) ---

_PLAN_CON_LEDGER = (
    "# PLAN\n"
    "## 🎯 Cola priorizada\n"
    "| # | Ítem | Estado |\n"
    "| 1 | B5 | en curso |\n"
    "## [SIGUIENTE-GOOGLE-MCP] F1 ✅ MERGEADA · F4 pendiente\n"
    "texto de un item ABIERTO con una fase hecha\n"
    "## ✅ Cerrados\n"
    "> ledger\n"
    "- ✅ **[FOO]** algo — PR #1\n"
    "- ✅ **[BAR]** otra — PR #2\n"
)

_PLAN_CON_CERRADO_SUELTO = (
    "# PLAN\n"
    "## ✅ [VIEJO] COMPLETA\n"
    "MERGEADA a main. Rama podada.\n"
    "## ✅ Cerrados\n"
    "- ✅ **[FOO]** algo — PR #1\n"
)


def test_contar_lineas():
    assert sc._contar_lineas("a\nb\nc") == 3
    assert sc._contar_lineas("") == 0


def test_indice_cerrados_encuentra_la_seccion():
    lineas = _PLAN_CON_LEDGER.splitlines()
    i = sc._indice_cerrados(lineas)
    assert lineas[i].strip() == "## ✅ Cerrados"


def test_indice_cerrados_none_si_no_existe():
    assert sc._indice_cerrados(["# PLAN", "## Cola"]) is None


def test_cerrados_sin_colapsar_ignora_item_abierto_con_fase_hecha():
    # El ✅ va a mitad del encabezado (fase hecha de un item ABIERTO) -> no se marca.
    # Y las entradas del ledger (bajo ## Cerrados) tampoco se marcan.
    assert sc._cerrados_sin_colapsar(_PLAN_CON_LEDGER) == []


def test_cerrados_sin_colapsar_detecta_bloque_cerrado_arriba():
    # Encabezado cuyo TEXTO empieza por ✅ y está antes de ## Cerrados -> sin colapsar.
    assert sc._cerrados_sin_colapsar(_PLAN_CON_CERRADO_SUELTO) == ["[VIEJO] COMPLETA"]


def test_contar_cerrados_cuenta_las_entradas_del_ledger():
    assert sc._contar_cerrados(_PLAN_CON_LEDGER) == 2


def test_contar_cerrados_sin_seccion_es_cero():
    assert sc._contar_cerrados("# PLAN\n## Cola\n- [ ] tarea\n") == 0


# --- Aviso de higiene de planificacion (D3) ---

def _prep_higiene(monkeypatch, tmp_path, status_lineas, plan_texto):
    (tmp_path / "STATUS.md").write_text("x\n" * status_lineas, encoding="utf-8")
    (tmp_path / "PLAN.md").write_text(plan_texto, encoding="utf-8")
    monkeypatch.setattr(sc, "ROOT", tmp_path)


def test_higiene_avisa_status_grande(monkeypatch, capsys, tmp_path):
    _prep_higiene(monkeypatch, tmp_path, 500, "# PLAN\n## ✅ Cerrados\n")
    sc._avisar_higiene_planificacion()
    out = capsys.readouterr().out
    assert "[!]" in out and "STATUS.md" in out and "500" in out


def test_higiene_avisa_item_sin_colapsar(monkeypatch, capsys, tmp_path):
    _prep_higiene(monkeypatch, tmp_path, 10, _PLAN_CON_CERRADO_SUELTO)
    sc._avisar_higiene_planificacion()
    out = capsys.readouterr().out
    assert "[!]" in out and "[VIEJO] COMPLETA" in out


def test_higiene_avisa_ledger_lleno(monkeypatch, capsys, tmp_path):
    ledger = "# PLAN\n## ✅ Cerrados\n" + "".join(
        f"- ✅ **[I{i}]** x — PR #{i}\n" for i in range(31)
    )
    _prep_higiene(monkeypatch, tmp_path, 10, ledger)
    sc._avisar_higiene_planificacion()
    out = capsys.readouterr().out
    assert "[!]" in out and "31" in out and "area" in out.lower()


def test_higiene_limpia_no_alarma(monkeypatch, capsys, tmp_path):
    _prep_higiene(monkeypatch, tmp_path, 100, _PLAN_CON_LEDGER)
    sc._avisar_higiene_planificacion()
    out = capsys.readouterr().out
    assert "[!]" not in out


# --- Trazabilidad de specs/plans recientes en el ledger -------------------------
# Revision adversarial 2026-07-26:
# docs/superpowers/specs/2026-07-26-gobernanza-indice-adversarial-review.md

_LOG_ALTAS = [
    "a" * 40,
    "docs/superpowers/specs/2026-07-20-crm-atlas-descubrimiento-design.md",
    "b" * 40,
    "docs/superpowers/specs/2026-07-19-otra-cosa-design.md",
]


def test_disenos_recientes_parsea_altas_y_su_pr(monkeypatch):
    # `git log --diff-filter=A --pretty=%H --name-only` intercala sha y ficheros.
    def fake_lines(args):
        if args[0] == "log" and "--name-only" in args:
            return _LOG_ALTAS if "specs/" in args[-1] else []
        if args[0] == "log" and "--pretty=format:%s" in args:
            sha = args[-1]
            return [f"feat(x): algo (#{104 if sha.startswith('a') else 99})"]
        return []
    monkeypatch.setattr(sc, "_git_lines", fake_lines)

    filas = sc._disenos_recientes(dias=10)

    assert filas == [
        ("docs/superpowers/specs/2026-07-19-otra-cosa-design.md", "99"),
        ("docs/superpowers/specs/2026-07-20-crm-atlas-descubrimiento-design.md", "104"),
    ]


def test_pr_del_commit_sin_numero_es_none(monkeypatch):
    monkeypatch.setattr(sc, "_git_lines", lambda args: ["chore: commit directo sin PR"])
    assert sc._pr_del_commit("a" * 40) is None


def test_traza_por_stem():
    recientes = [("docs/superpowers/specs/2026-07-20-crm-atlas-descubrimiento-design.md", None)]
    corpus = "- ✅ [CRM-ATLAS] … [spec](…/2026-07-20-crm-atlas-descubrimiento-design.md)"
    assert sc._disenos_sin_traza(recientes, corpus) == []


def test_traza_por_numero_de_pr_aunque_nadie_escriba_el_stem():
    # Caso real: la fila del ledger cita el PR y enlaza, pero no nombra el plan.
    recientes = [("docs/superpowers/plans/2026-07-20-crm-atlas-fase-b.md", "104")]
    assert sc._disenos_sin_traza(recientes, "- ✅ [CRM-ATLAS] … PR #104 (`b2d624c`)") == []
    # sin la señal, el mismo plan es huerfano
    assert sc._disenos_sin_traza(recientes, "- ✅ [OTRA-COSA] … PR #77") == [
        "docs/superpowers/plans/2026-07-20-crm-atlas-fase-b.md"]


def test_pr_parecido_no_cuenta_como_traza():
    # `#10` no debe dar por trazado al PR #1 ni al reves: la señal es exacta.
    recientes = [("docs/superpowers/plans/x.md", "1")]
    assert sc._disenos_sin_traza(recientes, "PR #104 y PR #10") == ["docs/superpowers/plans/x.md"]


def _prep_corpus(tmp_path, monkeypatch, *, plan="", handoff="", indice="", bitacora=""):
    (tmp_path / "PLAN.md").write_text(plan, encoding="utf-8")
    (tmp_path / "docs").mkdir(exist_ok=True)
    (tmp_path / "docs" / "INDICE.md").write_text(indice, encoding="utf-8")
    (tmp_path / "docs" / "bitacora").mkdir(exist_ok=True)
    (tmp_path / "docs" / "bitacora" / "2026.md").write_text(bitacora, encoding="utf-8")
    hd = tmp_path / "docs" / "superpowers" / "handoffs"
    hd.mkdir(parents=True, exist_ok=True)
    (hd / "handoff-x.md").write_text(handoff, encoding="utf-8")
    monkeypatch.setattr(sc, "ROOT", tmp_path)


def test_handoff_no_cuenta_como_traza(tmp_path, monkeypatch):
    """CRITICO: incluir handoffs/ AUTOANULA el aviso.

    El stem de `crm-atlas` aparece justo dentro del handoff que denuncio el hueco:
    contarlo daria por trazado el defecto por haber sido denunciado (0 disparos).
    `GOBERNANZA_FUENTES_VERDAD §5`: el handoff no es fuente de verdad.
    """
    stem = "2026-07-20-crm-atlas-descubrimiento-design"
    _prep_corpus(tmp_path, monkeypatch,
                 plan="cola de trabajo, sin mencion",
                 handoff=f"el hueco esta en {stem}.md, nadie lo trazo")

    corpus = sc._texto_corpus_trazas()

    assert stem not in corpus
    assert sc._disenos_sin_traza([(f"docs/superpowers/specs/{stem}.md", None)], corpus) == [
        f"docs/superpowers/specs/{stem}.md"]


def test_indice_no_cuenta_como_traza(tmp_path, monkeypatch):
    # INDICE.md es vista derivada, no ledger: no puede dar por trazado nada.
    stem = "2026-07-20-algo-design"
    _prep_corpus(tmp_path, monkeypatch, plan="nada", indice=f"| `{stem}.md` | vigente |")
    assert stem not in sc._texto_corpus_trazas()


def test_bitacora_si_cuenta_como_traza(tmp_path, monkeypatch):
    # La prosa nominal del cierre es señal legitima (asi estan trazados varios planes).
    stem = "2026-06-22-expedientes-xl-conector"
    _prep_corpus(tmp_path, monkeypatch, plan="nada", bitacora=f"cierre: plan {stem} ejecutado")
    assert sc._disenos_sin_traza([(f"docs/superpowers/plans/{stem}.md", None)],
                                 sc._texto_corpus_trazas()) == []


def test_aviso_lista_los_huerfanos(monkeypatch, capsys):
    monkeypatch.setattr(sc, "_disenos_recientes", lambda: [("docs/superpowers/plans/x.md", "9")])
    monkeypatch.setattr(sc, "_texto_corpus_trazas", lambda: "corpus vacio de señales")

    sc._avisar_specs_sin_traza()
    out = capsys.readouterr().out

    assert "[!]" in out and "docs/superpowers/plans/x.md" in out
    assert "Cerrados" in out          # dice donde se arregla
    assert "handoff" in out.lower()   # y por que un handoff no vale


def test_aviso_no_alarma_si_todo_trazado(monkeypatch, capsys):
    monkeypatch.setattr(sc, "_disenos_recientes", lambda: [("docs/superpowers/plans/x.md", "9")])
    monkeypatch.setattr(sc, "_texto_corpus_trazas", lambda: "… PR #9 …")
    sc._avisar_specs_sin_traza()
    assert "[!]" not in capsys.readouterr().out


def test_aviso_sin_specs_recientes_no_alarma(monkeypatch, capsys):
    monkeypatch.setattr(sc, "_disenos_recientes", lambda: [])
    sc._avisar_specs_sin_traza()
    out = capsys.readouterr().out
    assert "[!]" not in out and "Sin specs/plans nuevos" in out
