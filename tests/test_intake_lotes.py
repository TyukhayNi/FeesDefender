# tests/test_intake_lotes.py
"""Layout de 00_Input por lotes (MEJORAS #54, spec 2026-07-17 rev 2)."""
from __future__ import annotations

import importlib
from datetime import date

import pytest

from core import case_manager, config

HOY = date(2026, 7, 17)


@pytest.fixture(autouse=True)
def _reload(tmp_casos_root):
    importlib.reload(config)
    importlib.reload(case_manager)


def test_fuentes_lote_sin_espejos():
    from core import config
    assert config.FUENTES_LOTE == ("whatsapp", "email", "manual", "entrevista")
    assert "drive_ev" not in config.FUENTES_LOTE and "crm" not in config.FUENTES_LOTE
    assert config.ESPEJO_SUBDIRS == ("01_Drive EV", "05_CRM")


def test_lista_unica_de_ficheros_de_control():
    from core import config, intake_drive, intake_manual, inventory
    assert intake_drive.CONTROL_FILES == config.INTAKE_CONTROL_FILES
    assert inventory._CONTROL_FILES == config.INTAKE_CONTROL_FILES
    assert intake_manual._CONTROL_FILES == config.INTAKE_CONTROL_FILES
    # Los índices del canal email también son control (spec §5).
    assert {"_exported_ids.json", "_resolved_links.json", ".pulled", ".synced",
            "_inventory.json"} <= set(config.INTAKE_CONTROL_FILES)


def _caso(case_id="EV-2026-100"):
    case_manager.ensure_case(case_id, titulo="Lotes")
    return case_id


def test_reservar_lote_formato_y_creacion(tmp_casos_root):
    from core import intake_lotes
    case_id = _caso()
    lote = intake_lotes.reservar_lote(case_id, "whatsapp", "whatsapp", hoy=HOY)
    assert lote.name == "2026-07-17_whatsapp_01"
    assert lote.parent == config.caso_path(case_id) / "00_Input"
    assert lote.is_dir()
    assert intake_lotes.PATRON_LOTE.match(lote.name).group(2) == "whatsapp"


def test_reservar_lote_colision_mismo_dia_sube_nn(tmp_casos_root):
    from core import intake_lotes
    case_id = _caso()
    l1 = intake_lotes.reservar_lote(case_id, "manual", "manual", hoy=HOY)
    l2 = intake_lotes.reservar_lote(case_id, "manual", "manual", hoy=HOY)
    assert (l1.name, l2.name) == ("2026-07-17_manual_01", "2026-07-17_manual_02")


def test_reservar_lote_rechaza_espejos(tmp_casos_root):
    from core import intake_lotes
    case_id = _caso()
    for fuente in ("drive_ev", "crm"):
        with pytest.raises(ValueError):
            intake_lotes.reservar_lote(case_id, fuente, fuente, hoy=HOY)


def test_contador_cuenta_lotes_de_la_bandeja(tmp_casos_root):
    # Un intake sobre caso prestado deja su lote en _pendiente_checkin/<origen>/00_Input/;
    # si el contador no lo viera, el checkin fusionaría dos lotes homónimos (spec §4).
    from core import intake_lotes
    case_id = _caso()
    bandeja = (config.caso_path(case_id) / config.PENDIENTE_CHECKIN_SUBDIR
               / "manual" / "00_Input" / "2026-07-17_manual_01")
    bandeja.mkdir(parents=True)
    lote = intake_lotes.reservar_lote(case_id, "manual", "manual", hoy=HOY)
    assert lote.name == "2026-07-17_manual_02"


def test_reserva_atomica_por_mkdir(tmp_casos_root, monkeypatch):
    # Carrera: otro proceso creó el dir entre el escaneo y el mkdir → se prueba NN+1.
    from core import intake_lotes
    case_id = _caso()
    (config.caso_path(case_id) / "00_Input" / "2026-07-17_manual_01").mkdir()
    monkeypatch.setattr(intake_lotes, "_lotes_existentes", lambda case_dir: set())
    lote = intake_lotes.reservar_lote(case_id, "manual", "manual", hoy=HOY)
    assert lote.name == "2026-07-17_manual_02"


def test_clasificar_tipo_contenido():
    from core.intake_lotes import clasificar_tipo_contenido as tc
    assert tc("_chat.txt") == "whatsapp"          # solo _chat.txt es 'whatsapp'
    assert tc("notas.txt") == "txt"
    assert tc("escrito.PDF") == "pdf"
    assert tc("IMG-001.jpg") == "imagen"
    assert tc("video.mp4") == "video"
    assert tc("nota_voz.opus") == "audio"         # _AUDIO_EXTS ya existía (whatsapp_intake:21)
    assert tc("correo.eml") == "eml"
    assert tc("contrato.docx") == "docx"
    assert tc("raro.xyz") == "otros"


def test_manifiesto_round_trip_y_exclusiones(tmp_path):
    from core import intake_lotes as il
    lote = tmp_path / "2026-07-17_manual_01"
    lote.mkdir()
    (lote / "doc.pdf").write_bytes(b"pdf")
    (lote / "_export_original.zip").write_bytes(b"zip")   # SÍ entra (spec §5)
    (lote / "_exported_ids.json").write_text("{}", encoding="utf-8")  # control: NO entra
    (lote / ".pulled").write_text("", encoding="utf-8")               # control: NO entra
    items = il.items_desde_disco(lote)
    assert {i.relpath for i in items} == {"doc.pdf", "_export_original.zip"}

    il.escribir_manifiesto(lote, fuente="manual", fecha_intake="2026-07-17",
                           origen="test", items=items)
    data = il.leer_manifiesto(lote)
    assert data["fuente"] == "manual" and data["origen"] == "test"
    assert {i["relpath"] for i in data["items"]} == {"doc.pdf", "_export_original.zip"}
    # None se omite: sin message_id/duplicado_de no aparecen las claves.
    assert all("duplicado_de" not in i and "message_id" not in i for i in data["items"])
    # El propio manifiesto no se auto-inventaría.
    assert "_manifiesto.yaml" not in {i.relpath for i in il.items_desde_disco(lote)}


def test_manifiesto_message_id_y_duplicado(tmp_path):
    from core import intake_lotes as il
    lote = tmp_path / "2026-07-17_email_01"
    lote.mkdir()
    (lote / "2026-07-01_asunto.eml").write_bytes(b"raw")
    items = il.items_desde_disco(
        lote,
        message_id_de={"2026-07-01_asunto.eml": "<x@y>"},
        duplicados={"2026-07-01_asunto.eml": "2026-06-10_manual_01/copia.eml"},
    )
    il.escribir_manifiesto(lote, fuente="email", fecha_intake="2026-07-17",
                           origen="email_export", items=items)
    item = il.leer_manifiesto(lote)["items"][0]
    assert item["message_id"] == "<x@y>"
    assert item["duplicado_de"] == "2026-06-10_manual_01/copia.eml"
    assert item["tipo_contenido"] == "eml"


def test_fuente_de_contrato_completo():
    from core.intake_lotes import fuente_de
    assert fuente_de("01_Drive EV/w/doc.pdf") == "drive_ev"          # espejo
    assert fuente_de("05_CRM/Civil/demanda.pdf") == "crm"            # espejo
    assert fuente_de("2026-07-17_whatsapp_01/00_Consultor propietario/c/_chat.txt") == "whatsapp"
    assert fuente_de("2026-07-17_email_02/a.eml") == "email"         # lote
    assert fuente_de("02_Whatsapp/rol/chat/_chat.txt") == "whatsapp" # cajón legacy
    assert fuente_de("06_Entrevistas/x.mp4") == "entrevista"         # SINGULAR (spec §4)
    assert fuente_de("suelto_en_raiz.pdf") == "manual"               # raíz
    assert fuente_de("CarpetaRara/x.pdf") == "manual"                # fallback unificado
    assert fuente_de("2026-07-17_manual_01\\a.pdf") == "manual"      # tolera backslash


def test_anexar_items_fusiona_por_relpath(tmp_path):
    from core import intake_lotes as il
    lote = tmp_path / "2026-07-17_manual_01"
    lote.mkdir()
    a = il.ItemManifiesto("a.pdf", "sha-a", 3, "pdf")
    il.anexar_items(lote, [a], origen="ui_manual")
    a2 = il.ItemManifiesto("a.pdf", "sha-a2", 4, "pdf")
    b = il.ItemManifiesto("b.txt", "sha-b", 1, "txt")
    il.anexar_items(lote, [a2, b], origen="ui_manual")
    data = il.leer_manifiesto(lote)
    assert data["fuente"] == "manual" and data["fecha_intake"] == "2026-07-17"
    por_rel = {i["relpath"]: i for i in data["items"]}
    assert set(por_rel) == {"a.pdf", "b.txt"}
    assert por_rel["a.pdf"]["sha256"] == "sha-a2"   # el nuevo gana
