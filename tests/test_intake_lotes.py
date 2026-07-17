# tests/test_intake_lotes.py
"""Layout de 00_Input por lotes (MEJORAS #54, spec 2026-07-17 rev 2)."""
from __future__ import annotations


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
