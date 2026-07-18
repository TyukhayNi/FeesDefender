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
