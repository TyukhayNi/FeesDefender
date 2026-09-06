"""Filtro de ruido administrativo en `export_label` (acción 6a) + `MEJORAS #168`.

La regla que impide que el correo de administración del despacho entre en el expediente
de un cliente vivía SOLO como prosa (`RUNBOOK [APER-38]`) y por eso se repitió tres veces
—W-02XOR7 el 2026-07-13, W-02VUDR el 2026-07-21 dos veces—. Aquí se ejecuta.

**Lo que este filtro NO es:** el detector de W-codes ajenos. Ese avisa y no excluye
(`core/email_atomize/contaminacion.py`), y sigue igual. Este excluye una categoría
distinta: material que no es prueba de NINGÚN caso y que trae confidencialidad de
terceros — los anexos de la circularización de auditoría llevan la cartera completa de
litigios del despacho.

Plan: `docs/superpowers/plans/2026-09-06-accion-6a-filtro-de-ruido-email-export.md`.
"""
from __future__ import annotations

import json

import pytest

from core import email_export as ee


# ---------------------------------------------------------------------------
# T1 — la capa pura: `clasificar_ruido`
# ---------------------------------------------------------------------------

# Asunto real de la plantilla GENERICO (id 404) del CRM, con su separador « · »
# (U+00B7). Verificado en `docs/INTEGRACION_SUDESPACHO.md`: una regex sin el « · »
# NO casa, y ese fue el error del dimensionado previo.
_ASUNTO_CRM_VACIO = "S/R:  · M/R:  · Cliente: EV MMC SPAIN, S.L.U. · Contrario: "
_ASUNTO_CRM_LLENO = (
    "S/R: Ba123 · M/R: 45/2026 · Cliente: EV MMC SPAIN, S.L.U. · Contrario: Juan Pérez"
)


def test_facturacion_al_buzon_de_proveedores_se_excluye():
    regla = ee.clasificar_ruido({
        "subject": "Factura agosto 2026",
        "to": "Proveedores.ES@engelvoelkers.com",
    })
    assert regla == "facturacion_despacho"


def test_facturacion_detectada_tambien_en_copia():
    """`parse_headers` no extraía `cc`, y el buzón de facturación viaja ahí a menudo."""
    regla = ee.clasificar_ruido({
        "subject": "Factura agosto 2026",
        "to": "eva@engelvoelkers.com",
        "cc": "Proveedores ES <Proveedores.ES@engelvoelkers.com>",
    })
    assert regla == "facturacion_despacho"


def test_buzon_de_proveedores_case_insensitive():
    regla = ee.clasificar_ruido({
        "subject": "Factura", "to": "PROVEEDORES.ES@ENGELVOELKERS.COM"})
    assert regla == "facturacion_despacho"


def test_correo_normal_del_caso_no_se_excluye():
    regla = ee.clasificar_ruido({
        "subject": "Oferta de compra del inmueble",
        "from": "Eva <eva@engelvoelkers.com>",
        "to": "despacho@tyukhay.legal",
    })
    assert regla is None


def test_repositorio_con_refs_vacias_se_excluye():
    regla = ee.clasificar_ruido({
        "subject": _ASUNTO_CRM_VACIO,
        "to": "mails.repositorio@gmail.com",
    })
    assert regla == "repositorio_refs_vacias"


def test_repositorio_con_refs_LLENAS_no_se_excluye():
    """El destinatario solo NO basta: un correo del caso reenviado al repositorio
    conserva sus referencias, y ese SÍ es del expediente."""
    regla = ee.clasificar_ruido({
        "subject": _ASUNTO_CRM_LLENO,
        "to": "mails.repositorio@gmail.com",
    })
    assert regla is None


def test_refs_vacias_SIN_el_buzon_del_repositorio_no_se_excluye():
    """La otra mitad de la conjunción: un asunto de plantilla sin rellenar, dirigido
    a una persona, no es un volcado al repositorio."""
    regla = ee.clasificar_ruido({
        "subject": _ASUNTO_CRM_VACIO,
        "to": "eva@engelvoelkers.com",
    })
    assert regla is None


@pytest.mark.parametrize("asunto", [
    "Circularización de auditoría 2026",
    "Circularizacion de auditoria - ejercicio 2025",
    "RV: Carta a los auditores",
    "Carta de auditores Deloitte",
])
def test_auditoria_se_excluye(asunto):
    assert ee.clasificar_ruido({"subject": asunto, "to": "x@y.z"}) == "auditoria"


@pytest.mark.parametrize("asunto", [
    "Acta reunión CFO + Legal",
    "Acta reunion CFO+Legal 12 de junio",
])
def test_gobernanza_interna_se_excluye(asunto):
    assert ee.clasificar_ruido({"subject": asunto, "to": "x@y.z"}) == "gobernanza_interna"


@pytest.mark.parametrize("asunto", [
    # La palabra suelta no basta: el letrado habla de auditoría y de actas en su
    # correspondencia del caso con normalidad. El falso positivo aquí excluye prueba.
    "Auditoría técnica del inmueble",
    "Acta de la reunión con el propietario",
    "Acta notarial de manifestaciones",
    "Nota simple registral",
])
def test_asuntos_del_caso_que_rozan_las_reglas_NO_se_excluyen(asunto):
    assert ee.clasificar_ruido({"subject": asunto, "to": "despacho@tyukhay.legal"}) is None


def test_cabeceras_ausentes_no_revientan():
    assert ee.clasificar_ruido({}) is None


def test_no_mira_el_cuerpo():
    """Misma razón que `contaminacion.detectar_cruce`: el cuerpo da ruido, no señal.

    `clasificar_ruido` recibe cabeceras; si alguien le pasara un cuerpo en una clave
    cualquiera, no debe cambiar el veredicto.
    """
    limpio = {"subject": "Oferta del inmueble", "to": "despacho@tyukhay.legal"}
    con_cuerpo = dict(limpio, body="Adjunto la circularización de auditoría y el acta CFO + Legal")
    assert ee.clasificar_ruido(con_cuerpo) == ee.clasificar_ruido(limpio) is None


# ---------------------------------------------------------------------------
# T4/T5 — el cableado en `export_label`: qué NO se escribe y qué rastro deja
# ---------------------------------------------------------------------------

from tests.test_email_export import (  # noqa: E402  (tras la capa pura, a propósito)
    _ETIQUETA,
    _LABELS,
    _FakeService,
    _build_raw,
    _setup_caso,
)

_CUENTA = "nikolai@engelvoelkers.com"


def _raws_mixtos() -> dict[str, bytes]:
    """Dos del caso y tres de ruido, uno por regla estructural o de asunto."""
    return {
        "g-ok-1": _build_raw(message_id="<ok1@x>", subject="Oferta del inmueble"),
        "g-factura": _build_raw(
            message_id="<fact@x>", subject="Factura agosto",
            to_addr="Proveedores.ES@engelvoelkers.com"),
        "g-ok-2": _build_raw(message_id="<ok2@x>", subject="Arras firmadas"),
        "g-auditoria": _build_raw(
            message_id="<aud@x>", subject="Circularización de auditoría 2026"),
        "g-repo": _build_raw(
            message_id="<repo@x>", to_addr="mails.repositorio@gmail.com",
            subject="S/R:  · M/R:  · Cliente: EV MMC SPAIN, S.L.U. · Contrario: "),
    }


def _svc(raws: dict[str, bytes]) -> "_FakeService":
    return _FakeService(
        labels=_LABELS, pages=[{"messages": [{"id": g} for g in raws]}], raws=raws)


def test_el_ruido_no_se_escribe_y_lo_del_caso_si(tmp_path):
    raws = _raws_mixtos()
    rep = ee.export_label(_CUENTA, _ETIQUETA, tmp_path, service=_svc(raws))

    assert rep.written == 2, "solo los dos del caso"
    nombres = " ".join(rep.files)
    assert "oferta" in nombres and "arras" in nombres
    for prohibido in ("factura", "circulariz", "auditor"):
        assert prohibido not in nombres.lower()
    assert not list(tmp_path.glob("*factura*"))


def test_el_ruido_no_cuenta_como_duplicado(tmp_path):
    """Un excluido no debe tocar `vistos` ni el contador de duplicados: se filtra
    ANTES de esa lógica, o un segundo correo de ruido con el mismo Message-ID
    inflaría un contador que el letrado lee como señal."""
    rep = ee.export_label(_CUENTA, _ETIQUETA, tmp_path, service=_svc(_raws_mixtos()))
    assert rep.duplicados == 0


def test_lo_excluido_queda_en_el_report_con_su_regla(tmp_path):
    rep = ee.export_label(_CUENTA, _ETIQUETA, tmp_path, service=_svc(_raws_mixtos()))

    assert len(rep.excluidos_ruido) == 3
    reglas = {e["regla"] for e in rep.excluidos_ruido}
    assert reglas == {"facturacion_despacho", "auditoria", "repositorio_refs_vacias"}
    # El motivo sin el mensaje al que se refiere no es revisable.
    for e in rep.excluidos_ruido:
        assert e["gmail_id"] and e["asunto"]
    assert "3 excluidos por ruido" in rep.resumen()


def test_la_exclusion_es_REVERSIBLE_el_gid_no_entra_en_el_indice(tmp_path):
    """La propiedad que separa «filtrar» de «perder»: el `gmail_id` excluido no se
    anota como exportado, así que una corrida con `filtrar_ruido=False` lo trae sin
    necesidad de `force`."""
    raws = _raws_mixtos()
    ee.export_label(_CUENTA, _ETIQUETA, tmp_path, service=_svc(raws))

    indice = json.loads((tmp_path / "_exported_ids.json").read_text(encoding="utf-8"))
    exportados = set(indice[_CUENTA])
    assert exportados == {"g-ok-1", "g-ok-2"}

    rep2 = ee.export_label(
        _CUENTA, _ETIQUETA, tmp_path, service=_svc(raws), filtrar_ruido=False)
    assert rep2.written == 3, "los tres excluidos vuelven, sin force"
    assert rep2.excluidos_ruido == []


def test_sin_ruido_no_hay_linea_de_excluidos(tmp_path):
    raws = {"g1": _build_raw(message_id="<a@x>", subject="Oferta del inmueble")}
    rep = ee.export_label(_CUENTA, _ETIQUETA, tmp_path, service=_svc(raws))
    assert rep.excluidos_ruido == []
    assert "excluidos por ruido" not in rep.resumen()


def test_el_evento_durable_dice_que_se_excluyo_y_por_que(tmp_casos_root):
    """La pantalla se pierde y el `.jsonl` no. Sin evento, «se puede revisar» no lo
    cumple nadie."""
    from core import config, intake_log

    case_id = _setup_caso("EMAIL-RUIDO-001")
    dest = config.caso_path(case_id) / "00_Input" / "2026-09-06_email_01"
    dest.mkdir(parents=True)

    ee.export_label(_CUENTA, _ETIQUETA, dest, service=_svc(_raws_mixtos()), case_id=case_id)

    eventos = [e for e in intake_log.read_events(case_id)
               if e.get("event") == "email_excluido_ruido"]
    assert len(eventos) == 1
    detalle = eventos[0]["details"]
    assert detalle["total"] == 3
    assert {x["regla"] for x in detalle["excluidos"]} == {
        "facturacion_despacho", "auditoria", "repositorio_refs_vacias"}


def test_sin_ruido_no_se_emite_evento(tmp_casos_root):
    """Idempotencia del log: un evento vacío es ruido en el propio rastro forense."""
    from core import config, intake_log

    case_id = _setup_caso("EMAIL-RUIDO-002")
    dest = config.caso_path(case_id) / "00_Input" / "2026-09-06_email_01"
    dest.mkdir(parents=True)
    raws = {"g1": _build_raw(message_id="<a@x>", subject="Oferta del inmueble")}

    ee.export_label(_CUENTA, _ETIQUETA, dest, service=_svc(raws), case_id=case_id)

    assert not [e for e in intake_log.read_events(case_id)
                if e.get("event") == "email_excluido_ruido"]


# ---------------------------------------------------------------------------
# T6 — el flag de escape en la CLI
# ---------------------------------------------------------------------------

def test_cli_filtra_por_defecto_y_el_flag_lo_desactiva(monkeypatch, tmp_path):
    """El default es filtrar; `--sin-filtro-ruido` es la vía documentada de vuelta."""
    import scripts.export_label_emails as cli

    capturado: dict[str, object] = {}

    def _fake_export(account, label, dest, **kw):
        capturado.update(kw)
        return ee.ExportReport(account=account, label=label)

    monkeypatch.setattr(cli, "export_label", _fake_export)
    monkeypatch.setattr(cli, "resolve_ref", lambda ref: ref)
    monkeypatch.setattr(cli, "email_dest_dir", lambda cid: tmp_path)
    monkeypatch.setattr(cli, "w_code_de", lambda cid: "W-TEST01")

    import contextlib

    @contextlib.contextmanager
    def _sin_mutex(*a, **kw):
        yield

    monkeypatch.setattr(cli, "sostener", _sin_mutex)

    base = ["--ref", "X", "--account", "a@b.c", "--label", "L"]
    cli.main(base)
    assert capturado["filtrar_ruido"] is True

    cli.main(base + ["--sin-filtro-ruido"])
    assert capturado["filtrar_ruido"] is False


# ---------------------------------------------------------------------------
# T7 — `MEJORAS #168`: un destino EXTERNO no entra en el M9 del caso
# ---------------------------------------------------------------------------

def test_destino_externo_con_nombre_de_lote_no_entra_en_el_M9(tmp_casos_root, tmp_path):
    """Misma frontera que `#149` en el escritor: «lote de este caso» es una
    UBICACIÓN física bajo su `00_Input/`, no un nombre que lo parezca.

    Hoy `_emit_traza` registraría en el manifiesto del caso rutas que no existen en
    su `00_Input`, y `report.errors` quedaría vacío.
    """
    from core.intake_manifest import IntakeManifest

    case_id = _setup_caso("EMAIL-EXT-001")
    fuera = tmp_path / "2026-09-06_email_01"      # nombre de lote, ubicación ajena
    fuera.mkdir(parents=True)
    raws = {"g1": _build_raw(message_id="<x@x>", subject="Oferta del inmueble")}

    rep = ee.export_label(_CUENTA, _ETIQUETA, fuera, service=_svc(raws), case_id=case_id)

    assert rep.written == 1, "el .eml se escribe donde se pidió"
    with IntakeManifest(case_id) as m:
        assert m.all_paths() == set(), "pero NO se registra en el manifiesto del caso"
    assert not rep.intake_logged
    # Nunca en silencio, y nombrando LAS DOS rutas para que se pueda decidir.
    assert rep.errors, "la omisión se declara"
    aviso = " ".join(rep.errors)
    assert str(fuera) in aviso and "00_Input" in aviso


def test_destino_INTERNO_sigue_entrando_en_el_M9(tmp_casos_root):
    """La otra dirección de la frontera: el guard no puede romper el camino normal."""
    from core import config
    from core.intake_manifest import IntakeManifest

    case_id = _setup_caso("EMAIL-INT-001")
    dentro = config.caso_path(case_id) / "00_Input" / "2026-09-06_email_01"
    dentro.mkdir(parents=True)
    raws = {"g1": _build_raw(message_id="<y@x>", subject="Arras firmadas")}

    rep = ee.export_label(_CUENTA, _ETIQUETA, dentro, service=_svc(raws), case_id=case_id)

    with IntakeManifest(case_id) as m:
        assert m.all_paths(), "el lote legítimo sí se traza"
    assert rep.intake_logged


def test_el_buzon_de_facturacion_EN_COPIA_se_caza_end_to_end(tmp_path):
    """`parse_headers` no extraía `cc`, así que el filtro habría sido ciego a la
    mitad de los casos reales aunque la capa pura los clasificara bien. Este test
    pasa por el parseo de verdad; el de la capa pura no."""
    raws = {
        "g-ok": _build_raw(message_id="<ok@x>", subject="Oferta del inmueble"),
        "g-cc": _build_raw(
            message_id="<cc@x>", subject="Factura agosto",
            to_addr="eva@engelvoelkers.com",
            cc="Proveedores ES <Proveedores.ES@engelvoelkers.com>"),
    }
    rep = ee.export_label(_CUENTA, _ETIQUETA, tmp_path, service=_svc(raws))

    assert rep.written == 1
    assert [e["regla"] for e in rep.excluidos_ruido] == ["facturacion_despacho"]
