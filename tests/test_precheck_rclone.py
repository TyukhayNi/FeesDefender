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


def test_exit_5_si_rclone_TARDA_y_el_veredicto_lo_dice(capsys):
    """`MEJORAS #296`: con otra corrida de rclone en marcha, `config show` tardó 3,9-6,7 s en
    las aperturas del 2026-09-25, y el precheck juntaba el timeout con «no instalado» y
    «remote inexistente» en el mismo 4. Tardar no dice nada del client: código propio."""
    import subprocess
    with patch("subprocess.run",
               side_effect=subprocess.TimeoutExpired(cmd=["rclone"], timeout=15)):
        assert pr.main(["precheck_rclone.py", "gdrive_tl:"]) == 5
    assert "tard" in capsys.readouterr().out


def test_exit_4_si_el_remote_NO_EXISTE_aunque_rclone_salga_con_0(capsys):
    """Medido el 2026-09-26 con rclone real: `config show <remote inexistente>` sale con 0 y
    escribe `# couldn't find type of fs for "<remote>"`. El precheck lo tomaba por un remote
    sin client propio (3, «client compartido»): era otra causa con el nombre de otra."""
    salida = '[gdrive_tl]\n# couldn\'t find type of fs for "gdrive_tl"\n'
    with patch("subprocess.run", return_value=_run(salida, returncode=0)):
        assert pr.main(["precheck_rclone.py", "gdrive_tl:"]) == 4
    assert "no existe" in capsys.readouterr().out


def test_main_nunca_imprime_secretos(capsys):
    with patch("subprocess.run", return_value=_run(_CONFIG_PROPIO)):
        pr.main(["precheck_rclone.py", "gdrive_tl:"])
    out = capsys.readouterr().out
    assert "GOCSPX" not in out and "refresh_token" not in out and "ya29" not in out
