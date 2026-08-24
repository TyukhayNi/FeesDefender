"""Cableado de la atomización de correo en la sala de máquina (spec §6).

Dos grupos, como manda el contrato de tests: (1) con doble del motor, para el orden y
el contrato del evento; (2) contra el MOTOR REAL, porque la rev. 1 de la spec tenía 7
tests con doble que pasaban todos sobre un defecto real de enumeración.
"""
from __future__ import annotations

from email.message import EmailMessage
from pathlib import Path

import pytest

import scripts.sala_maquina as cli
from core.email_atomize.pipeline import AtomizeReport


def _eml(mid: str, subj: str = "Oferta", attachments=None) -> bytes:
    m = EmailMessage()
    m["Message-ID"] = mid
    m["Subject"] = subj
    m["Date"] = "Thu, 12 Jun 2026 10:00:00 +0200"
    m["From"] = "propietario@example.invalid"
    m["To"] = "agencia@example.invalid"
    m.set_content("Cuerpo de prueba.")
    for fn, mime, data in attachments or []:
        maint, _, sub = mime.partition("/")
        m.add_attachment(data, maintype=maint, subtype=sub, filename=fn)
    return m.as_bytes()


@pytest.fixture
def caso(tmp_path, monkeypatch):
    """Caso en `tmp_path` con OCR y log neutralizados.

    Devuelve `(case_dir, eventos)`. El nombre de carpeta lleva W-code entre paréntesis
    para que el detector de contaminación cruzada no calle por `(SIN REFERENCIA)`.
    """
    case_dir = tmp_path / "BaRS9 - Prueba - (W-TEST99) - Vuelta"
    (case_dir / "00_Input" / "03_Email").mkdir(parents=True)
    eventos: list[tuple[str, dict]] = []
    monkeypatch.setattr(cli, "caso_path", lambda cid: case_dir)
    monkeypatch.setattr(cli, "append_event",
                        lambda destino, ev, *, details=None, case_id=None: eventos.append((ev, details or {})))
    monkeypatch.setattr(cli.sm, "ejecutar", lambda *a, **k: [])
    return case_dir, eventos


def _evento(eventos, nombre="atomizado_email"):
    return [d for ev, d in eventos if ev == nombre]


# --- Grupo 1: con doble del motor --------------------------------------------

def test_atomiza_antes_de_construir_el_plan_de_ocr(caso, monkeypatch):
    """Orden real, incluido el rastro: evento y notas ANTES de arrancar el OCR.

    La secuencia `atomize → plan → ejecutar` por sí sola NO basta: una implementación que
    guarde el report en memoria, corra el OCR (~1 h 40) y escriba el evento al final
    pasaría, dejando sin rastro una corrida que muere a mitad (spec §4.5) y sin ver la
    contaminación cruzada hasta después del OCR (objetivo 3 de la spec).
    """
    case_dir, _ = caso
    (case_dir / "00_Input" / "03_Email" / "a.eml").write_bytes(_eml("<a@x>"))
    orden: list[str] = []
    real_echo = cli.typer.echo

    def fake_atomize(*a, **k):
        orden.append("atomize")
        return AtomizeReport(mensajes=1, notas=["W-code ajeno en 1 mensaje: W-00000"])

    def fake_plan(cd, force):
        orden.append("plan")
        # Desde 2026-08-04 `_construir_plan` devuelve además las mediciones del
        # inventario: `(plan, cache, ms_inventario, n_hasheados, agotados)`. El doble
        # cambia de forma, no de propósito — lo que este test fija sigue siendo el ORDEN
        # de las etapas, no lo que el plan contiene.
        return [], {}, 0, 0, frozenset()

    def fake_ejecutar(*a, **k):
        orden.append("ejecutar")
        return []

    def fake_evento(destino, ev, *, details=None, case_id=None):
        orden.append(f"evento:{ev}")

    def fake_echo(msg="", **kw):
        if "NOTA:" in str(msg):
            orden.append("nota")
        real_echo(msg, **kw)

    monkeypatch.setattr(cli.atomize, "atomize_dir", fake_atomize)
    monkeypatch.setattr(cli, "_construir_plan", fake_plan)
    monkeypatch.setattr(cli.sm, "ejecutar", fake_ejecutar)
    monkeypatch.setattr(cli, "append_event", fake_evento)
    monkeypatch.setattr(cli.typer, "echo", fake_echo)

    cli.apply("W-TEST99")

    # Las etapas, en orden y sin duplicados.
    assert [x for x in orden if x in ("atomize", "plan", "ejecutar")] == \
        ["atomize", "plan", "ejecutar"]
    # Rastro y aviso ANTES del OCR. No se fija el orden entre nota y evento: los dos
    # cumplen la spec mientras precedan al plan.
    assert orden.index("evento:atomizado_email") < orden.index("plan")
    assert orden.index("nota") < orden.index("plan")
    # Y el evento del OCR después: nada se ha invertido por el camino.
    assert orden.index("evento:procesado_sala_maquina") > orden.index("ejecutar")


def test_noop_sin_eml_y_sin_arbol_previo(caso, monkeypatch):
    case_dir, eventos = caso
    llamadas: list[int] = []

    def fake_atomize(*a, **k):
        llamadas.append(1)
        return AtomizeReport()

    monkeypatch.setattr(cli.atomize, "atomize_dir", fake_atomize)

    cli.apply("W-TEST99")

    assert llamadas == []                                    # el motor no se invoca
    assert not (case_dir / "01_Procesado" / "Emails").exists()   # no se siembran carpetas
    assert _evento(eventos) == []                            # no se emite evento


def test_con_arbol_previo_y_cero_eml_si_se_atomiza(caso, monkeypatch):
    # La retirada de correos (remedio real de W-02VUDR contra la contaminación) debe
    # reflejarse: con árbol previo se llama al motor aunque no quede un solo .eml.
    case_dir, eventos = caso
    (case_dir / "01_Procesado" / "Emails" / "mensajes").mkdir(parents=True)
    llamadas: list[tuple] = []

    def fake_atomize(fuentes, out, *, case_dir=None):
        llamadas.append((list(fuentes), out, case_dir))
        return AtomizeReport()

    monkeypatch.setattr(cli.atomize, "atomize_dir", fake_atomize)

    cli.apply("W-TEST99")

    assert len(llamadas) == 1
    fuentes, out, cd = llamadas[0]
    # Las fuentes también se comprueban: pasar `[]` o una ruta equivocada dejaría este
    # test verde y la reconciliación sin efecto real.
    assert fuentes == [case_dir / "00_Input" / "03_Email"]
    assert out == case_dir / "01_Procesado" / "Emails"
    assert cd == case_dir            # case_dir explícito: no se infiere de out.parent.parent
    assert _evento(eventos)[0]["status"] == "ok"          # reconciliación declarada
    assert _evento(eventos)[0]["eml_en_disco"] == 0
    assert _evento(eventos)[0]["details_schema"] == 2


def test_el_caso_se_resuelve_una_sola_vez(caso, monkeypatch):
    # Si el helper llamara a `atomize_case(case_id)` en vez de a `atomize_dir` con las
    # rutas derivadas, volvería a localizar el caso (spec §4.6).
    from core.casos import case_locator
    case_dir, _ = caso
    (case_dir / "00_Input" / "03_Email" / "a.eml").write_bytes(_eml("<a@x>"))
    monkeypatch.setattr(cli.atomize, "atomize_dir", lambda *a, **k: AtomizeReport(mensajes=1))

    def prohibido(*a, **k):
        raise AssertionError("re-localización del caso dentro del helper")

    # `resolve_ref` (que sí corre en `_resolver_caso`) NO llama a `path_for` (verificado
    # en `case_locator.list_cases`), así que cualquier llamada a `path_for` viene de un
    # `atomize_case(case_id)` indebido.
    monkeypatch.setattr(case_locator, "path_for", prohibido)
    # Y `resolve_ref` exactamente una vez: la vía barata de re-resolver también cuenta.
    real_resolve = case_locator.resolve_ref
    refs: list[str] = []

    def contar_resolve(ref):
        refs.append(ref)
        return real_resolve(ref)

    monkeypatch.setattr(case_locator, "resolve_ref", contar_resolve)

    cli.apply("W-TEST99")   # no debe lanzar

    assert refs == ["W-TEST99"]


def test_fallo_del_motor_no_aborta_el_ocr_y_emite_evento(caso, monkeypatch, capsys):
    case_dir, eventos = caso
    (case_dir / "00_Input" / "03_Email" / "a.eml").write_bytes(_eml("<a@x>"))
    ejecutado: list[int] = []

    def boom(*a, **k):
        raise RuntimeError("motor roto")

    def fake_ejecutar(*a, **k):
        ejecutado.append(1)
        return []

    monkeypatch.setattr(cli.atomize, "atomize_dir", boom)
    monkeypatch.setattr(cli.sm, "ejecutar", fake_ejecutar)

    cli.apply("W-TEST99")

    assert ejecutado == [1]                      # el OCR corre igual (fallo blando)
    # Igualdad EXACTA: la rama de excepción no fabrica contadores — si el motor no
    # terminó, el payload no finge saber cuántos mensajes hay ni si publicó.
    assert _evento(eventos)[0] == {
        "details_schema": 2, "status": "fallo", "eml_en_disco": 1,
        "errores": ["RuntimeError: motor roto"],
    }
    err = capsys.readouterr().err
    assert "la atomización de correo FALLÓ" in err


def test_status_parcial_cuando_el_motor_termina_con_errores(caso, monkeypatch):
    case_dir, eventos = caso
    (case_dir / "00_Input" / "03_Email" / "a.eml").write_bytes(_eml("<a@x>"))
    monkeypatch.setattr(cli.atomize, "atomize_dir", lambda *a, **k: AtomizeReport(
        eml_enumerados=1, eml_leidos=1, publicado=True, poda_omitida=True,
        mensajes=2, errores=["<x@y>: cabecera ilegible"]))

    cli.apply("W-TEST99")

    # Igualdad exacta también aquí: el motor TERMINÓ, así que el payload debe llevar
    # todos los contadores del schema 2. `poda_omitida=True` es lo coherente con que el
    # motor terminase con errores.
    assert _evento(eventos)[0] == {
        "details_schema": 2, "status": "parcial",
        "eml_en_disco": 1, "eml_leidos": 1, "publicado": True, "poda_omitida": True,
        "mensajes": 2, "adjuntos_unicos": 0, "reconstruidos_b": 0,
        "citas_a_revision": 0, "upgrades": 0,
        "notas": [], "errores": ["<x@y>: cabecera ilegible"], "fallos_lectura": [],
    }


def test_payload_atado_a_los_campos_reales_del_report(caso, monkeypatch, capsys):
    # El doble devuelve un AtomizeReport REAL (no un SimpleNamespace): un campo mal
    # escrito en el payload rompe este test. Igualdad exacta del dict a propósito.
    case_dir, eventos = caso
    (case_dir / "00_Input" / "03_Email" / "a.eml").write_bytes(_eml("<a@x>"))
    report = AtomizeReport(eml_enumerados=1, eml_leidos=1, publicado=True, poda_omitida=False,
                           mensajes=413, adjuntos_unicos=162, reconstruidos_b=136,
                           citas_a_revision=43, upgrades=8,
                           notas=["W-code ajeno en 1 mensaje: W-00000"])
    monkeypatch.setattr(cli.atomize, "atomize_dir", lambda *a, **k: report)

    cli.apply("W-TEST99")

    assert _evento(eventos)[0] == {
        "details_schema": 2, "status": "ok",
        "eml_en_disco": 1, "eml_leidos": 1, "publicado": True, "poda_omitida": False,
        "mensajes": 413, "adjuntos_unicos": 162, "reconstruidos_b": 136,
        "citas_a_revision": 43, "upgrades": 8,
        "notas": ["W-code ajeno en 1 mensaje: W-00000"], "errores": [], "fallos_lectura": [],
    }
    # objetivo 3 de la spec: la contaminación cruzada se ve ANTES del OCR
    assert "W-code ajeno" in capsys.readouterr().err


def test_evento_declara_que_no_publico(caso, monkeypatch):
    # Rama transitoria (T4): el motor TERMINÓ pero no publicó nada (Drive sin
    # hidratar). `report.errores` está vacío, así que `status` no puede derivarse de
    # "parcial si hay errores": sin este caso, un run que publicó CERO se anunciaría
    # como "ok, mensajes: 0" — peor que un error en un corpus probatorio.
    case_dir, eventos = caso
    (case_dir / "00_Input" / "03_Email" / "a.eml").write_bytes(_eml("<a@x>"))
    monkeypatch.setattr(cli.atomize, "atomize_dir", lambda *a, **k: AtomizeReport(
        eml_enumerados=1, eml_leidos=0, publicado=False,
        fallos_lectura=["a.eml: no hidratado"],
        notas=["ATOMIZACIÓN NO PUBLICADA: 1 .eml no se pudieron leer…"]))

    cli.apply("W-TEST99")

    d = _evento(eventos)[0]
    assert d["status"] == "fallo" and d["publicado"] is False
    assert d["fallos_lectura"] == ["a.eml: no hidratado"]


def test_un_fallo_de_log_no_aborta_el_ocr(caso, monkeypatch, capsys):
    case_dir, _ = caso
    (case_dir / "00_Input" / "03_Email" / "a.eml").write_bytes(_eml("<a@x>"))
    ejecutado: list[int] = []

    def log_roto(destino, ev, *, details=None, case_id=None):
        # SOLO el evento de atomización. `apply` emite después `procesado_sala_maquina`
        # con un `append_event` SIN captura (`scripts/sala_maquina.py:195`): un doble que
        # lanzara para todo evento haría fallar este test por una vía ajena al cableado
        # (y así estaba mal escrito en la primera versión del plan).
        if ev == "atomizado_email":
            raise OSError("disco lleno")

    def fake_ejecutar(*a, **k):
        ejecutado.append(1)
        return []

    monkeypatch.setattr(cli.atomize, "atomize_dir", lambda *a, **k: AtomizeReport(mensajes=1))
    monkeypatch.setattr(cli, "append_event", log_roto)
    monkeypatch.setattr(cli.sm, "ejecutar", fake_ejecutar)

    cli.apply("W-TEST99")   # no debe propagar OSError

    assert ejecutado == [1]
    assert "no se pudo registrar el evento atomizado_email" in capsys.readouterr().err


def test_plan_no_atomiza_pero_informa(caso, monkeypatch, capsys):
    case_dir, eventos = caso
    src = case_dir / "00_Input" / "03_Email"
    (src / "a.eml").write_bytes(_eml("<a@x>"))
    (src / "b.eml").write_bytes(_eml("<b@x>"))
    (src / "sub").mkdir()
    (src / "sub" / "c.eml").write_bytes(_eml("<c@x>"))

    def prohibido(*a, **k):
        raise AssertionError("`plan` es preview: no debe atomizar")

    monkeypatch.setattr(cli.atomize, "atomize_dir", prohibido)

    cli.plan("W-TEST99")

    cap = capsys.readouterr()
    # Con el conteo recursivo la subcarpeta cuenta igual: 2 arriba + 1 en `sub/` = 3.
    assert "correo: 3 .eml (se atomizarán en apply)" in cap.out
    assert _evento(eventos) == []
    # Prohibir `atomize_dir` no basta: `plan` tampoco debe escribir en el árbol por su
    # cuenta. Es preview.
    assert not (case_dir / "01_Procesado" / "Emails").exists()


def test_plan_silencioso_sin_eml(caso, monkeypatch, capsys):
    # `plan` copia el condicional de `_atomizar_correo` para su preview; sin ningún
    # .eml (ni nivel superior ni en subcarpetas) debe quedar completamente callado
    # sobre correo: ni la línea `correo:` en stdout ni el banner en stderr. Esta rama
    # de la copia del condicional estaba sin verificar en aislamiento.
    # `caso` deja 00_Input/03_Email creado pero vacío — no hace falta desempaquetarlo.

    cli.plan("W-TEST99")

    cap = capsys.readouterr()
    assert "correo:" not in cap.out
    assert "viven en subcarpetas" not in cap.err


def test_reforzar_no_atomiza(caso, monkeypatch, capsys):
    from core import sala_maquina as sm
    from core.utils import file_sha256
    case_dir, _ = caso
    (case_dir / "00_Input" / "03_Email" / "a.eml").write_bytes(_eml("<a@x>"))
    drive = case_dir / "00_Input" / "01_Drive EV"
    drive.mkdir(parents=True)
    doc = drive / "escaneo.pdf"
    doc.write_bytes(b"%PDF-1.4 escaneo sin texto")
    sha = file_sha256(doc)
    cli._guardar_cobertura(case_dir, [sm.DocCobertura(
        slug=f"escaneo__{sha[:8]}", rel_path="01_Drive EV/escaneo.pdf", metodo="ocr",
        estado="low", chars=10, ocr=True, nota="OCR pobre", sha256=sha)])

    def prohibido(*a, **k):
        raise AssertionError("`reforzar` no debe atomizar")

    monkeypatch.setattr(cli.atomize, "atomize_dir", prohibido)
    monkeypatch.setattr(cli.sm, "vision_cableada", lambda: True)

    cli.reforzar("W-TEST99")

    assert "Reforzados" in capsys.readouterr().out


# --- Grupo 2: contra el MOTOR REAL -------------------------------------------

def test_motor_real_ve_las_subcarpetas(caso, monkeypatch, capsys):
    # El arreglo de #98 contra el motor REAL: el .eml de la subcarpeta ya se atomiza.
    case_dir, eventos = caso
    src = case_dir / "00_Input" / "03_Email"
    (src / "a.eml").write_bytes(_eml("<a@x>", "Visible"))
    (src / "arras").mkdir()
    (src / "arras" / "b.eml").write_bytes(_eml("<b@x>", "AntesInvisible"))

    cli.apply("W-TEST99")

    d = _evento(eventos)[0]
    assert d["status"] == "ok" and d["publicado"] is True
    assert (d["eml_en_disco"], d["eml_leidos"]) == (2, 2)
    assert d["mensajes"] == 2
    mds = list((case_dir / "01_Procesado" / "Emails" / "mensajes").glob("*.md"))
    assert len(mds) == 2
    assert any("AntesInvisible" in p.read_text(encoding="utf-8") for p in mds)


def test_transicion_a_cero_fuentes_poda_mensajes_pero_no_adjuntos(caso, monkeypatch):
    # Retirar el correo (remedio real de W-02VUDR) debe reflejarse en `mensajes/`.
    # `adjuntos/` NO se poda: comportamiento CONOCIDO del motor (MEJORAS #99). El día
    # que se arregle, este test fallará y hay que actualizarlo — eso es lo que se
    # quiere: que la deuda no se olvide.
    case_dir, eventos = caso
    src = case_dir / "00_Input" / "03_Email"
    eml = src / "a.eml"
    eml.write_bytes(_eml("<a@x>", "Con adjunto",
                         attachments=[("contrato.pdf", "application/pdf", b"%PDF datos")]))

    cli.apply("W-TEST99")
    emails = case_dir / "01_Procesado" / "Emails"
    assert len(list((emails / "mensajes").glob("*.md"))) == 1
    adjuntos_antes = sorted(p.name for p in (emails / "adjuntos").glob("*.pdf"))
    assert adjuntos_antes                                  # el adjunto se materializó

    eml.unlink()
    cli.apply("W-TEST99")

    assert list((emails / "mensajes").glob("*.md")) == []  # podado
    assert sorted(p.name for p in (emails / "adjuntos").glob("*.pdf")) == adjuntos_antes
    d = _evento(eventos)[-1]
    assert d["status"] == "ok" and d["mensajes"] == 0


def test_evento_real_es_valido_y_serializable(tmp_path, monkeypatch):
    # Sin parchear `append_event`: verifica que `atomizado_email` está en INTAKE_EVENTS
    # (si no, ValueError) y que el payload es JSON-serializable de verdad.
    from core import intake_log
    case_dir = tmp_path / "BaRS9 - Prueba - (W-TEST99) - Vuelta"
    (case_dir / "00_Input" / "03_Email").mkdir(parents=True)
    (case_dir / "00_Input" / "03_Email" / "a.eml").write_bytes(_eml("<a@x>"))
    monkeypatch.setattr(cli, "caso_path", lambda cid: case_dir)
    monkeypatch.setattr(intake_log, "caso_path", lambda cid: case_dir)
    monkeypatch.setattr(cli.sm, "ejecutar", lambda *a, **k: [])

    cli.apply("W-TEST99")

    eventos = [e for e in intake_log.read_events_de(case_dir)
               if e["event"] == "atomizado_email"]
    assert len(eventos) == 1
    assert eventos[0]["details"]["status"] == "ok"
    assert eventos[0]["details"]["mensajes"] == 1
