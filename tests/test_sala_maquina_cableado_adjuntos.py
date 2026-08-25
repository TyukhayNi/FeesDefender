"""Cableado del contenido de los adjuntos en la sala de máquina (`MEJORAS #87`, pieza 1).

**El defecto que cierra esto no es el motor: es que nadie lo ejecutaba.** Verificado el
2026-08-04 con `git grep` sobre `core/`, `scripts/`, `streamlit_app.py` y `.claude/skills`:
**cero llamadores** de `core.adjuntos_contenido` fuera del propio paquete. Su única vía era
`python -m core.adjuntos_contenido <case_id>`, a mano, y no la menciona ninguna skill ni el
RUNBOOK. Consecuencia: en cualquier caso, el contenido de los adjuntos **no existía en el
árbol** — ni bueno ni malo, no existía. Es la misma clase de defecto que `MEJORAS #113` y que
el cableado del correo que cerró el PR #151.

El orden importa y es el que se fija aquí: **atomizar → contenido de adjuntos → OCR**. Los
adjuntos solo existen en disco después de atomizar, así que antes no hay nada que procesar;
y va antes del OCR para que una corrida que muera a mitad deje ya el rastro del contenido.

Dos grupos, como el test hermano del atomizado: (1) con doble, para el orden y el contrato
del evento; (2) contra el motor REAL, porque un doble del pipeline de contenido dejaría verde
un cableado que apunta a la carpeta equivocada — y la carpeta es justo lo que hay que acertar.
"""

from __future__ import annotations

import json

import pytest

import scripts.sala_maquina as cli
from core.adjuntos_contenido.model import ContenidoReport


@pytest.fixture
def caso(tmp_path, monkeypatch):
    """Caso con árbol de correo atomizado y un adjunto de texto ya materializado."""
    case_dir = tmp_path / "BaRS9 - Prueba - (W-TEST99) - Vuelta"
    (case_dir / "00_Input" / "03_Email").mkdir(parents=True)
    eventos: list[tuple[str, dict]] = []
    monkeypatch.setattr(cli, "caso_path", lambda cid: case_dir)
    monkeypatch.setattr(cli, "append_event",
                        lambda destino, ev, *, details=None, case_id=None: eventos.append((ev, details or {})))
    monkeypatch.setattr(cli, "_atomizar_correo", lambda cid, cd: None)
    monkeypatch.setattr(cli.sm, "ejecutar", lambda *a, **k: [])
    return case_dir, eventos


def _sembrar_adjunto(case_dir, *, nombre="contrato.txt", cuerpo="Cláusula de honorarios."):
    """Deja un adjunto y su ficha como los escribe `email_atomize._escribe_adjunto`."""
    adj = case_dir / "01_Procesado" / "Emails" / "adjuntos"
    adj.mkdir(parents=True, exist_ok=True)
    base = f"2026-06-12_{nombre.rsplit('.', 1)[0]}_ATT-00001"
    # El binario se llama `{base}{suffix de nombre_original}`: es como lo compone
    # `descubrir._binario_para`, y si no coincide el motor no lo encuentra.
    (adj / f"{base}{'.' + nombre.rsplit('.', 1)[1]}").write_text(cuerpo, encoding="utf-8")
    (adj / f"{base}.md").write_text(
        "# GENERADO por core.email_atomize — NO editar.\n\n"
        "- att_id: ATT-00001\n"
        f"- nombre_original: {nombre}\n"
        "- tipo: text/plain\n"
        "- sha256: " + "a" * 64 + "\n"
        "- primera_aparicion: 2026-06-12\n"
        "- mensajes: MSG-00001\n- etiquetas: []\n\n"
        "## Descripción\n\n(pendiente)\n", encoding="utf-8")
    return adj, base


def _evento(eventos, nombre="contenido_adjuntos"):
    return [d for ev, d in eventos if ev == nombre]


# --- Grupo 1: con doble del motor de contenido --------------------------------

def test_procesa_los_adjuntos_entre_atomizar_y_el_ocr(caso, monkeypatch):
    """El orden completo, que es el contrato de esta pieza."""
    case_dir, _ = caso
    _sembrar_adjunto(case_dir)
    orden: list[str] = []

    monkeypatch.setattr(cli, "_atomizar_correo",
                        lambda cid, cd: orden.append("atomize"))
    monkeypatch.setattr(cli.contenido, "procesar_dir",
                        lambda d, **k: orden.append("adjuntos") or ContenidoReport())
    monkeypatch.setattr(cli, "_construir_plan",
                        lambda cd, force: orden.append("plan") or ([], {}, 0, 0, frozenset()))
    monkeypatch.setattr(cli.sm, "ejecutar",
                        lambda *a, **k: orden.append("ejecutar") or [])

    cli.apply("W-TEST99")

    assert orden == ["atomize", "adjuntos", "plan", "ejecutar"]


def test_noop_sin_carpeta_de_adjuntos(caso, monkeypatch):
    """Sin correo atomizado no hay nada que procesar: no se invoca el motor."""
    case_dir, eventos = caso
    llamadas: list[int] = []
    monkeypatch.setattr(cli.contenido, "procesar_dir",
                        lambda d, **k: llamadas.append(1) or ContenidoReport())

    cli.apply("W-TEST99")

    assert llamadas == []
    assert _evento(eventos) == []


def test_el_evento_lleva_los_contadores_del_report(caso, monkeypatch):
    case_dir, eventos = caso
    _sembrar_adjunto(case_dir)
    report = ContenidoReport(extraidos=3, omitidos=2, sin_texto=1, saltados=4,
                             podados=0, pendientes_vision=2,
                             errores=["ATT-00009: binario no encontrado"])
    monkeypatch.setattr(cli.contenido, "procesar_dir", lambda d, **k: report)

    cli.apply("W-TEST99")

    d = _evento(eventos)[0]
    assert d["status"] == "parcial"          # hay errores → no puede ser "ok"
    assert (d["extraidos"], d["omitidos"], d["sin_texto"]) == (3, 2, 1)
    assert d["saltados"] == 4
    assert d["pendientes_vision"] == 2
    assert d["errores"] == ["ATT-00009: binario no encontrado"]


def test_status_ok_cuando_no_hay_errores(caso, monkeypatch):
    case_dir, eventos = caso
    _sembrar_adjunto(case_dir)
    monkeypatch.setattr(cli.contenido, "procesar_dir",
                        lambda d, **k: ContenidoReport(extraidos=1))

    cli.apply("W-TEST99")

    assert _evento(eventos)[0]["status"] == "ok"


def test_un_fallo_del_motor_de_contenido_no_aborta_el_ocr(caso, monkeypatch, capsys):
    """Fallo blando, igual que la atomización: el OCR es lo caro y no depende de esto."""
    case_dir, eventos = caso
    _sembrar_adjunto(case_dir)
    ejecutado: list[int] = []

    def boom(d, **k):
        raise RuntimeError("docling reventó")

    monkeypatch.setattr(cli.contenido, "procesar_dir", boom)
    monkeypatch.setattr(cli.sm, "ejecutar", lambda *a, **k: ejecutado.append(1) or [])

    cli.apply("W-TEST99")

    assert ejecutado == [1]
    assert _evento(eventos)[0] == {"status": "fallo",
                                   "errores": ["RuntimeError: docling reventó"]}
    assert "contenido de los adjuntos FALLÓ" in capsys.readouterr().err


def test_no_vuelve_a_resolver_el_caso(caso, monkeypatch):
    """Se le pasa la RUTA, no el `case_id`.

    `procesar_caso(case_id)` volvería a localizar el caso —`apply` ya lo resolvió— y en un
    checkout apuntaría al árbol equivocado. Misma regla que el cableado del atomizado.
    """
    case_dir, _ = caso
    _sembrar_adjunto(case_dir)

    def prohibido(*a, **k):
        raise AssertionError("re-resolución del caso dentro del helper")

    monkeypatch.setattr(cli.contenido, "procesar_caso", prohibido)
    recibidas: list = []
    monkeypatch.setattr(cli.contenido, "procesar_dir",
                        lambda d, **k: recibidas.append(d) or ContenidoReport())

    cli.apply("W-TEST99")

    assert recibidas == [case_dir / "01_Procesado" / "Emails" / "adjuntos"]


def test_plan_no_procesa_adjuntos_pero_los_cuenta(caso, monkeypatch, capsys):
    """`plan` es preview: no escribe. Pero callar cuántos hay sería esconder el coste."""
    case_dir, eventos = caso
    _sembrar_adjunto(case_dir)

    def prohibido(*a, **k):
        raise AssertionError("`plan` es preview: no debe procesar adjuntos")

    monkeypatch.setattr(cli.contenido, "procesar_dir", prohibido)

    cli.plan("W-TEST99")

    assert "adjuntos: 1" in capsys.readouterr().out
    assert _evento(eventos) == []


# --- Grupo 2: contra el MOTOR REAL -------------------------------------------

def test_motor_real_escribe_el_contenido_del_adjunto(caso):
    """Sin doblar el pipeline de contenido: el `.contenido.md` acaba en disco.

    Es lo que un doble no puede demostrar — que la carpeta cableada es la que el motor
    descubre. Un `.txt` entra por la vía nativa: sin OCR, sin depender de Tesseract.
    """
    case_dir, eventos = caso
    adj, base = _sembrar_adjunto(case_dir)

    cli.apply("W-TEST99")

    destino = adj / f"{base}.contenido.md"
    assert destino.exists(), "el cableado apunta a una carpeta que el motor no descubre"
    md = destino.read_text(encoding="utf-8")
    assert "Cláusula de honorarios." in md
    assert _evento(eventos)[0]["extraidos"] == 1


def test_la_ficha_no_promete_un_pendiente_perpetuo(tmp_path):
    """Pieza 2: la ficha del atomizador APUNTA al contenido, no finge contenerlo.

    Decía `## Descripción\\n\\n(pendiente; OCR en fase 2)` — y como `_escribe_adjunto` la
    reescribe en CADA corrida, y `sala_maquina apply` atomiza en cada corrida, cualquier
    intento de que `adjuntos_contenido` la actualizara quedaba pisado a la siguiente. La
    salida no es actualizarla: es que nunca sea el hogar del contenido.
    """
    from core.email_atomize.model import AdjuntoUnico
    from core.email_atomize.pipeline import _escribe_adjunto

    out = tmp_path / "Emails"
    (out / "adjuntos").mkdir(parents=True)
    att = AdjuntoUnico(att_id="ATT-00001", sha256="b" * 64, tipo="application/pdf",
                       nombre_original="anexo.pdf", data=b"%PDF-1.4 x",
                       primera_aparicion="2026-06-12", mensajes=["MSG-00001"])

    _escribe_adjunto(out, att)

    ficha = (out / "adjuntos" / "2026-06-12_anexo_ATT-00001.md").read_text(encoding="utf-8")
    assert "OCR en fase 2" not in ficha
    assert "2026-06-12_anexo_ATT-00001.contenido.md" in ficha


def test_re_atomizar_no_pisa_el_texto_ya_extraido(caso, monkeypatch):
    """El clobber que la pieza 2 hace imposible, extremo a extremo.

    Secuencia real de dos corridas de `apply`: atomiza (reescribe la ficha) → extrae el
    contenido. En la segunda corrida la ficha se reescribe otra vez, y el `.contenido.md`
    —que es otro fichero— tiene que seguir ahí con su texto.
    """
    from core.email_atomize.model import AdjuntoUnico
    from core.email_atomize.pipeline import _escribe_adjunto

    case_dir, _ = caso
    out = case_dir / "01_Procesado" / "Emails"
    (out / "adjuntos").mkdir(parents=True)
    att = AdjuntoUnico(att_id="ATT-00001", sha256="c" * 64, tipo="text/plain",
                       nombre_original="clausula.txt",
                       data="Honorarios: 3 % + IVA.".encode("utf-8"),
                       primera_aparicion="2026-06-12", mensajes=["MSG-00001"])
    _escribe_adjunto(out, att)

    cli.apply("W-TEST99")                       # extrae el contenido
    destino = out / "adjuntos" / "2026-06-12_clausula_ATT-00001.contenido.md"
    assert "Honorarios: 3 % + IVA." in destino.read_text(encoding="utf-8")

    _escribe_adjunto(out, att)                  # segunda atomización: reescribe la ficha
    cli.apply("W-TEST99")

    assert "Honorarios: 3 % + IVA." in destino.read_text(encoding="utf-8")
    ficha = (out / "adjuntos" / "2026-06-12_clausula_ATT-00001.md").read_text(encoding="utf-8")
    assert "OCR en fase 2" not in ficha


def test_el_evento_real_es_valido_y_serializable(tmp_path, monkeypatch):
    """Sin parchear `append_event`: `contenido_adjuntos` debe estar en INTAKE_EVENTS."""
    from core import intake_log
    case_dir = tmp_path / "BaRS9 - Real - (W-TEST97) - Vuelta"
    (case_dir / "00_Input").mkdir(parents=True)
    monkeypatch.setattr(cli, "caso_path", lambda cid: case_dir)
    # El parche de `intake_log.caso_path` que vivía aquí se retiró con R8/H8-09:
    # era un resto de antes del B0-1. El módulo ya no usa ese símbolo —este test
    # escribe con el `case_dir` explícito y lee por `read_events_de`—, así que el
    # parche no participaba en nada y solo mantenía viva una importación muerta.
    monkeypatch.setattr(cli, "_atomizar_correo", lambda cid, cd: None)
    monkeypatch.setattr(cli.sm, "ejecutar", lambda *a, **k: [])
    _sembrar_adjunto(case_dir)

    cli.apply("W-TEST97")

    eventos = [e for e in intake_log.read_events_de(case_dir)
               if e["event"] == "contenido_adjuntos"]
    assert len(eventos) == 1
    assert eventos[0]["details"]["status"] == "ok"
    assert json.dumps(eventos[0])          # serializable de verdad
