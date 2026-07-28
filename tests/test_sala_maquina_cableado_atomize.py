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
                        lambda cid, ev, *, details=None: eventos.append((ev, details or {})))
    monkeypatch.setattr(cli.sm, "ejecutar", lambda *a, **k: [])
    return case_dir, eventos


def _evento(eventos, nombre="atomizado_email"):
    return [d for ev, d in eventos if ev == nombre]


# --- Grupo 1: con doble del motor --------------------------------------------

def test_atomiza_antes_de_construir_el_plan_de_ocr(caso, monkeypatch):
    # La Task 4 AMPLÍA este test para exigir que el evento y las notas existan también
    # antes del OCR: la secuencia de etapas por sí sola no lo mata.
    case_dir, _ = caso
    (case_dir / "00_Input" / "03_Email" / "a.eml").write_bytes(_eml("<a@x>"))
    orden: list[str] = []

    def fake_atomize(*a, **k):
        orden.append("atomize")
        return AtomizeReport(mensajes=1)

    def fake_plan(cd, force):
        orden.append("plan")
        return []

    def fake_ejecutar(*a, **k):
        orden.append("ejecutar")
        return []

    monkeypatch.setattr(cli.atomize, "atomize_dir", fake_atomize)
    monkeypatch.setattr(cli, "_construir_plan", fake_plan)
    monkeypatch.setattr(cli.sm, "ejecutar", fake_ejecutar)

    cli.apply("W-TEST99")

    assert orden == ["atomize", "plan", "ejecutar"]


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
