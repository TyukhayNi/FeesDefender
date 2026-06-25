from core.whatsapp_atomize.model import RegistroMensajeWA, AtomEnterrado, SegmentoEnterradoWA


def test_registro_mensaje_wa_defaults():
    m = RegistroMensajeWA()
    assert m.msg_id == ""
    assert m.fecha_iso == "0000-00-00"
    assert m.es_reenviado is False
    assert m.en_revision is False
    assert m.adjunto is None


def test_atom_enterrado_defaults_en_revision():
    a = AtomEnterrado(portador_msg_id="MSG-00001", de="x@y.com")
    assert a.en_revision is True
    assert a.confianza == "media"


def test_segmento_enterrado_wa():
    s = SegmentoEnterradoWA(portador_msg_id="MSG-00002", motivo="sin_cabecera")
    assert s.portador_msg_id == "MSG-00002"
