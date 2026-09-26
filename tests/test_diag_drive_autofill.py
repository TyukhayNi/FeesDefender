"""`scripts/diag_drive_autofill.py`: el diagnóstico del auto-fill desde una carpeta de Drive.

R1/H-06 de la fila #42 (`MEJORAS #296`): imprimía los primeros 30 caracteres del access_token,
antes y después de renovarlo, y leía el token con su propia copia de `rclone config show` (5 s,
y un remote inexistente por existente). Ahora usa el lector único y dice el motivo.
"""
from __future__ import annotations

from unittest.mock import MagicMock

from core import intake_drive
from scripts import diag_drive_autofill as diag

_FOLDER = "1ARbjPzfix-RbYi2o2ZgoZ8W5FMBkP9Oa"
_TOKEN = "ya29.SECRETO-del-access-token-que-no-debe-salir-1234567890"


def test_no_imprime_nada_del_token(monkeypatch, capsys):
    monkeypatch.setattr(diag, "obtener_token_drive",
                        lambda: intake_drive.TokenDrive(_TOKEN, ""))
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"name": "Calle Mayor 5 - W-02UIQU", "driveId": "D1"}
    monkeypatch.setattr("httpx.get", MagicMock(return_value=resp))
    monkeypatch.setattr("sys.argv", ["diag_drive_autofill.py", _FOLDER])

    diag.main()

    salida = capsys.readouterr().out
    assert "ya29" not in salida and "SECRETO" not in salida


def test_sin_token_dice_el_motivo_y_sale_con_1(monkeypatch, capsys):
    monkeypatch.setattr(diag, "obtener_token_drive",
                        lambda: intake_drive.TokenDrive(None, "rclone tardó más de 30 s"))
    monkeypatch.setattr("sys.argv", ["diag_drive_autofill.py", _FOLDER])

    assert diag.main() == 1
    assert "rclone tardó más de 30 s" in capsys.readouterr().out
