from __future__ import annotations
import json
from core.email_atomize import ids


def test_msg_id_congela_por_message_id(tmp_path):
    reg = ids.load_registro(tmp_path)
    a = reg.msg_id_for("<m1@x>", sha="sha_a")
    b = reg.msg_id_for("<m2@x>", sha="sha_b")
    assert a == "MSG-00001"
    assert b == "MSG-00002"
    # mismo Message-ID -> mismo id (congelado), aunque cambie el sha (upgrade fidelidad)
    assert reg.msg_id_for("<m1@x>", sha="sha_a_v2") == "MSG-00001"


def test_att_id_congela_por_sha(tmp_path):
    reg = ids.load_registro(tmp_path)
    assert reg.att_id_for("shaPDF") == "ATT-00001"
    assert reg.att_id_for("shaJPG") == "ATT-00002"
    assert reg.att_id_for("shaPDF") == "ATT-00001"  # mismo contenido -> mismo id


def test_registro_persiste_y_no_renumera(tmp_path):
    reg = ids.load_registro(tmp_path)
    reg.msg_id_for("<m1@x>", sha="sha_a")
    reg.att_id_for("shaPDF")
    reg.marcar_procesado("2024-01-01_uno.eml")
    reg.save()

    reg2 = ids.load_registro(tmp_path)
    # tras recargar, un nuevo mensaje toma el SIGUIENTE libre, no renumera
    assert reg2.msg_id_for("<m2@x>", sha="sha_b") == "MSG-00002"
    assert reg2.att_id_for("shaJPG") == "ATT-00002"
    assert "2024-01-01_uno.eml" in reg2.procesados
    # el JSON tiene cabecera no-editar
    data = json.loads((tmp_path / "_registro.json").read_text(encoding="utf-8"))
    assert data["_no_editar"] is True
    assert "_README" in data
