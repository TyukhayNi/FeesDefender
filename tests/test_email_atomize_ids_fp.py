from __future__ import annotations
import json
from core.email_atomize import ids


def test_fp_id_congela_y_es_independiente_de_msg(tmp_path):
    reg = ids.load_registro(tmp_path)
    reg.msg_id_for("<a@x>", sha="sha_a")          # Layer A: MSG-00001
    a = reg.msg_id_for_fp("fp:deadbeef", cuerpo_sha="cs1")
    b = reg.msg_id_for_fp("fp:cafef00d", cuerpo_sha="cs2")
    assert a == "MSG-00002" and b == "MSG-00003"  # comparten el contador msg
    assert reg.msg_id_for_fp("fp:deadbeef", cuerpo_sha="cs1") == "MSG-00002"  # congelado


def test_alias_resuelve_mid_a_fp(tmp_path):
    reg = ids.load_registro(tmp_path)
    reg.msg_id_for_fp("fp:deadbeef", cuerpo_sha="cs1")
    reg.registrar_alias("clean-mid@x", "fp:deadbeef")
    assert reg.resolver_alias("clean-mid@x") == "fp:deadbeef"
    assert reg.resolver_alias("desconocido@x") is None


def test_persistencia_v2_y_loader_tolera_v1(tmp_path):
    reg = ids.load_registro(tmp_path)
    reg.msg_id_for("<a@x>", sha="sha_a")
    reg.msg_id_for_fp("fp:deadbeef", cuerpo_sha="cs1")
    reg.registrar_alias("clean-mid@x", "fp:deadbeef")
    reg.save()
    data = json.loads((tmp_path / "_registro.json").read_text(encoding="utf-8"))
    assert data["version"] == 2 and "mensajes_fp" in data and "alias" in data
    # un registro v1 (sin mensajes_fp/alias) carga sin romper
    (tmp_path / "_registro.json").write_text(json.dumps(
        {"version": 1, "mensajes": {"x@x": {"id": "MSG-00001", "sha256": "s"}},
         "adjuntos": {}, "eml_procesados": [], "_contadores": {"msg": 1, "att": 0}}),
        encoding="utf-8")
    reg2 = ids.load_registro(tmp_path)
    assert reg2.msg_id_for_fp("fp:new", cuerpo_sha="cs") == "MSG-00002"  # sigue el contador
