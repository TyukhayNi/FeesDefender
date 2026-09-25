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


# --- R1/H-04: limpiar la referencia no puede ligarla a OTROS bytes --------------------
#
# La referencia se limpia de marcas invisibles (MEJORAS #236), pero el nombre en disco se
# resuelve primero TAL COMO LO CITÓ el chat, después limpio, y el limpio solo si identifica
# un único fichero. Si no, el adjunto queda ausente en vez de ligarse a bytes ajenos.


def test_R1_H04_con_los_dos_ficheros_elige_el_que_cito_el_chat(tmp_path):
    reg = load_registro_wa(tmp_path)
    media = {"foto.jpg": b"OTRO", "\u200efoto.jpg": b"ORIGINAL"}
    unicos, por_ref = construir_adjuntos(["foto.jpg"], media, reg,
                                         crudos={"foto.jpg": "\u200efoto.jpg"})
    assert [a.data for a in unicos] == [b"ORIGINAL"]
    assert unicos[0].nombre_original == "\u200efoto.jpg", "nombra los bytes elegidos"
    assert por_ref["foto.jpg"]["ausente"] is False


def test_R1_H04_si_solo_existe_el_marcado_se_encuentra(tmp_path):
    reg = load_registro_wa(tmp_path)
    unicos, por_ref = construir_adjuntos(["foto.jpg"], {"\u200efoto.jpg": b"ORIGINAL"}, reg,
                                         crudos={"foto.jpg": "\u200efoto.jpg"})
    assert por_ref["foto.jpg"]["ausente"] is False and unicos[0].data == b"ORIGINAL"


def test_R1_H04_el_caso_real_la_marca_solo_en_el_chat_sigue_casando(tmp_path):
    """Control positivo: lo medido en W-02V48N —la marca en el texto del chat y el fichero
    sin ella— es el caso normal y tiene que seguir casando."""
    reg = load_registro_wa(tmp_path)
    unicos, por_ref = construir_adjuntos(["IMG-1.jpg"], {"IMG-1.jpg": b"foto"}, reg,
                                         crudos={"IMG-1.jpg": "\u200eIMG-1.jpg"})
    assert por_ref["IMG-1.jpg"]["ausente"] is False and unicos[0].data == b"foto"


def test_R1_H04_dos_candidatos_limpios_quedan_AUSENTES_y_no_ligados_a_uno(tmp_path):
    reg = load_registro_wa(tmp_path)
    media = {"\u200ffoto.jpg": b"UNO", "\u202afoto.jpg": b"OTRO"}
    unicos, por_ref = construir_adjuntos(["foto.jpg"], media, reg,
                                         crudos={"foto.jpg": "foto.jpg"})
    assert por_ref["foto.jpg"]["ausente"] is True and unicos == []
