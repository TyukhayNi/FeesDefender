from importlib import import_module
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
import pytest
import json as _json

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


def test_rc_activo_usa_post_no_get():
    # Bug real (sesion 2026-07-21, W-02VUDR): la RC API de rclone es
    # POST-only (confirmado con `curl` real contra rclone v1.73.5: GET a
    # /core/pid -> 404, POST -> 200). Con GET (el default de urlopen sin
    # `method`), _rc_activo() SIEMPRE devolvia False -> levantar_rcd_si_falta
    # nunca detectaba un rcd ya activo y agotaba el timeout de 10s.
    with patch("urllib.request.urlopen", return_value=_mock_response(b'{"pid": 123}')) as m:
        assert cmr._rc_activo() is True
        req = m.call_args[0][0]
        assert req.get_method() == "POST"


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


def test_validar_pares_lanza_si_hay_destino_duplicado():
    with pytest.raises(ValueError, match="destinos duplicados"):
        cmr.validar_pares([("a/x.pdf", "b/dup.pdf"), ("a/y.pdf", "b/dup.pdf")])


def test_validar_pares_ok_si_destinos_unicos():
    cmr.validar_pares([("a/x.pdf", "b/x.pdf"), ("a/y.pdf", "b/y.pdf")])  # no lanza


def test_copiar_manifiesto_aborta_antes_de_copiar_si_hay_colision():
    with patch("urllib.request.urlopen") as m:
        with pytest.raises(ValueError, match="destinos duplicados"):
            cmr.copiar_manifiesto("gdrive_tl:", [("a/x.pdf", "b/dup.pdf"), ("a/y.pdf", "b/dup.pdf")])
        m.assert_not_called()  # ningún fichero se copió


def test_copiar_manifiesto_escribe_progreso_jsonl(tmp_path):
    prog = tmp_path / "copia.jsonl"
    with patch("urllib.request.urlopen", return_value=_mock_response(b"{}")):
        ok, fallidos = cmr.copiar_manifiesto(
            "gdrive_tl:", [("a/x.pdf", "b/x.pdf"), ("a/y.pdf", "b/y.pdf")], progreso_path=prog)
    assert ok == ["b/x.pdf", "b/y.pdf"]
    lineas = [_json.loads(l) for l in prog.read_text(encoding="utf-8").splitlines()]
    assert [l["dst"] for l in lineas] == ["b/x.pdf", "b/y.pdf"]
    assert all(l["estado"] == "ok" for l in lineas)


def test_copiar_manifiesto_reanuda_salta_los_ya_ok(tmp_path):
    prog = tmp_path / "copia.jsonl"
    prog.write_text(_json.dumps({"dst": "b/x.pdf", "estado": "ok"}) + "\n", encoding="utf-8")
    llamadas = []

    def fake_urlopen(req, timeout=60):
        llamadas.append(req.data.decode("utf-8"))
        return _mock_response(b"{}")

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        ok, fallidos = cmr.copiar_manifiesto(
            "gdrive_tl:", [("a/x.pdf", "b/x.pdf"), ("a/y.pdf", "b/y.pdf")], progreso_path=prog)
    assert ok == ["b/x.pdf", "b/y.pdf"]           # x.pdf cuenta como ok (reanudado)
    assert all("x.pdf" not in c for c in llamadas)  # pero NO se volvió a copiar
    assert any("y.pdf" in c for c in llamadas)


def test_copiar_manifiesto_fallo_al_escribir_log_no_aborta_ni_reclasifica(tmp_path):
    # Revision Task 5 (Important): si la copia tiene exito pero ESCRIBIR el
    # log de progreso falla (PermissionError por antivirus/Drive-sync en
    # Windows, directorio padre inexistente, disco lleno), el dst YA copiado
    # no debe reclasificarse como fallido, y el fallo de I/O del log no debe
    # propagarse fuera de copiar_manifiesto (abortaria el resto del batch,
    # violando la invariante "un fallo individual no aborta el resto").
    prog = tmp_path / "copia.jsonl"
    with patch("urllib.request.urlopen", return_value=_mock_response(b"{}")):
        with patch.object(cmr, "_anota_progreso", side_effect=PermissionError("log bloqueado")):
            ok, fallidos = cmr.copiar_manifiesto(
                "gdrive_tl:", [("a/x.pdf", "b/x.pdf"), ("a/y.pdf", "b/y.pdf")], progreso_path=prog)
    assert ok == ["b/x.pdf", "b/y.pdf"]
    assert fallidos == []


def test_cargar_progreso_ignora_linea_json_no_objeto(tmp_path):
    # Minor 1: una linea JSON sintacticamente valida pero que no sea un
    # objeto (lista, numero...) no debe lanzar AttributeError al llamar
    # .get() sobre ella — se ignora como cualquier otra linea corrupta.
    prog = tmp_path / "copia.jsonl"
    prog.write_text(
        _json.dumps([1, 2, 3]) + "\n" + _json.dumps({"dst": "b/x.pdf", "estado": "ok"}) + "\n",
        encoding="utf-8",
    )
    assert cmr._cargar_progreso(prog) == {"b/x.pdf"}


def test_cargar_progreso_no_indexa_fallidos_se_reintentan(tmp_path):
    # Un dst marcado "fallido" en el log NO cuenta como ya-ok: la reanudacion
    # debe reintentarlo (solo "estado"=="ok" se indexa).
    prog = tmp_path / "copia.jsonl"
    prog.write_text(
        _json.dumps({"dst": "b/x.pdf", "estado": "fallido", "error": "boom"}) + "\n", encoding="utf-8")
    assert cmr._cargar_progreso(prog) == set()
