from core.whatsapp_atomize.ids import fingerprint, load_registro_wa


def test_fingerprint_estable():
    a = fingerprint("2024-10-30T10:00", "Juan", "hola")
    b = fingerprint("2024-10-30T10:00", "Juan", "hola")
    assert a == b and len(a) == 64  # sha256 hex


def test_ids_congelados_idempotentes(tmp_path):
    reg = load_registro_wa(tmp_path)
    fp = fingerprint("2024-10-30T10:00", "Juan", "hola")
    id1 = reg.msg_id_for_fp(fp)
    id2 = reg.msg_id_for_fp(fp)            # misma fp → mismo id
    assert id1 == id2 == "MSG-00001"
    id_nuevo = reg.msg_id_for_fp(fingerprint("2024-10-30T10:01", "Ana", "ok"))
    assert id_nuevo == "MSG-00002"
    reg.save()
    reg2 = load_registro_wa(tmp_path)
    assert reg2.msg_id_for_fp(fp) == "MSG-00001"


def test_att_id_por_sha(tmp_path):
    reg = load_registro_wa(tmp_path)
    assert reg.att_id_for("abc") == "ATT-00001"
    assert reg.att_id_for("abc") == "ATT-00001"
    assert reg.att_id_for("def") == "ATT-00002"
