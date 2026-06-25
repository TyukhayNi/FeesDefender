from core.whatsapp_atomize.adjuntos import construir_adjuntos
from core.whatsapp_atomize.ids import load_registro_wa


def test_dedup_por_sha_y_ausentes(tmp_path):
    reg = load_registro_wa(tmp_path)
    media = {"IMG-001.jpg": b"foto", "doc.pdf": b"pdf"}
    refs = ["IMG-001.jpg", "doc.pdf", "IMG-001.jpg", "falta.jpg", "<Media omitted>"]
    unicos, por_ref = construir_adjuntos(refs, media, reg)
    att_ids = {a.att_id for a in unicos}
    assert len(att_ids) == 2
    assert por_ref["falta.jpg"]["ausente"] is True
    assert por_ref["<Media omitted>"]["ausente"] is True
    assert por_ref["IMG-001.jpg"]["ausente"] is False
