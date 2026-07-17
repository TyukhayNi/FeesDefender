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
