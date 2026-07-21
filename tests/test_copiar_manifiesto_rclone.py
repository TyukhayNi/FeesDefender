from importlib import import_module
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / ".claude/skills/organizar-sala-lectura/scripts"))
cmr = import_module("copiar_manifiesto_rclone")


def _mock_response(payload: bytes):
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = payload
    return cm


def test_copiar_renombrar_envia_srcfs_srcremote_dstfs_dstremote():
    with patch("urllib.request.urlopen", return_value=_mock_response(b"{}")) as m:
        cmr.copiar_renombrar("gdrive_tl:", "a/origen.pdf", "b/destino.pdf")
        req = m.call_args[0][0]
        import json
        body = json.loads(req.data)
        assert body == {
            "srcFs": "gdrive_tl:", "srcRemote": "a/origen.pdf",
            "dstFs": "gdrive_tl:", "dstRemote": "b/destino.pdf",
        }


def test_copiar_manifiesto_no_aborta_si_uno_falla():
    def fake_urlopen(req, timeout=60):
        body = req.data.decode("utf-8")
        if "falla.pdf" in body:
            raise RuntimeError("500 error simulado")
        return _mock_response(b"{}")
    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        ok, fallidos = cmr.copiar_manifiesto("gdrive_tl:", [
            ("a/ok1.pdf", "b/ok1.pdf"),
            ("a/falla.pdf", "b/falla.pdf"),
            ("a/ok2.pdf", "b/ok2.pdf"),
        ])
    assert ok == ["b/ok1.pdf", "b/ok2.pdf"]
    assert len(fallidos) == 1 and fallidos[0][0] == "b/falla.pdf"
