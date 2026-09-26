"""`scripts/audit_ev_folder_names.py`: el auditor de los nombres de carpeta de E&V.

Lo tocan dos entradas del backlog que consume: `MEJORAS #296` —sin token, el auditor mandaba
a mirar `rclone config show`, que escribe los secretos en claro, en vez de decir el motivo— y
`MEJORAS #301` —el orden con el W-code delante es un formato válido, no un fallo de naming—.
"""
from __future__ import annotations

from core import intake_drive
from scripts import audit_ev_folder_names as auditor


def test_sin_token_dice_el_motivo_y_sale_con_2(monkeypatch, capsys):
    monkeypatch.setattr(auditor, "obtener_token_drive",
                        lambda: intake_drive.TokenDrive(None, "rclone tardó más de 30 s"))

    reporte, codigo = auditor.audit(team_filter=None, limit=5)

    assert (reporte, codigo) == ({}, 2)
    err = capsys.readouterr().err
    assert "rclone tardó más de 30 s" in err, err
    assert "config show" not in err, "no mandes al operador a volcar los secretos"


def test_una_carpeta_con_el_w_code_delante_no_es_un_fallo(monkeypatch):
    monkeypatch.setattr(auditor, "obtener_token_drive",
                        lambda: intake_drive.TokenDrive("tok", ""))
    monkeypatch.setattr(auditor, "DRIVE_EV_TEAM_IDS", {"SaRS1": "DRIVE1"})
    monkeypatch.setattr(auditor, "_list_drive_folders",
                        lambda did, tok, limit: ([{"id": "a", "name": "W-02UIQU - Calle Mayor 5 - Ana P"},
                                                  {"id": "b", "name": "Calle Menor 2 - W-02XXXX"}],
                                                 None))

    reporte, codigo = auditor.audit(team_filter=None, limit=5)

    assert codigo == 0, reporte
