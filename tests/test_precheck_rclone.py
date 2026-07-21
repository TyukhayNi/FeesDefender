from importlib import import_module
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / ".claude/skills/organizar-sala-lectura/scripts"))
pr = import_module("precheck_rclone")

_CONFIG_PROPIO = """[gdrive_tl]
type = drive
client_id = 111222333444-abcdef.apps.googleusercontent.com
client_secret = GOCSPX-secretazo
token = {"access_token":"ya29.secretoooo","refresh_token":"1//refrescooo"}
"""
_CONFIG_COMPARTIDO = """[gdrive_tl]
type = drive
token = {"access_token":"ya29.x"}
"""
_CONFIG_CLIENT_COMPARTIDO = """[gdrive_tl]
type = drive
client_id = 202264815644-xxxx.apps.googleusercontent.com
"""


def _run(stdout, returncode=0):
    m = MagicMock()
    m.stdout = stdout
    m.returncode = returncode
    return m


def test_exit_0_con_client_propio():
    with patch("subprocess.run", return_value=_run(_CONFIG_PROPIO)):
        assert pr.precheck("gdrive_tl:") == 0


def test_exit_3_sin_client_id():
    with patch("subprocess.run", return_value=_run(_CONFIG_COMPARTIDO)):
        assert pr.precheck("gdrive_tl") == 3


def test_exit_3_con_client_compartido_de_rclone():
    with patch("subprocess.run", return_value=_run(_CONFIG_CLIENT_COMPARTIDO)):
        assert pr.precheck("gdrive_tl") == 3


def test_exit_4_si_rclone_no_existe():
    with patch("subprocess.run", side_effect=FileNotFoundError):
        assert pr.precheck("gdrive_tl") == 4


def test_main_nunca_imprime_secretos(capsys):
    with patch("subprocess.run", return_value=_run(_CONFIG_PROPIO)):
        pr.main(["precheck_rclone.py", "gdrive_tl:"])
    out = capsys.readouterr().out
    assert "GOCSPX" not in out and "refresh_token" not in out and "ya29" not in out
