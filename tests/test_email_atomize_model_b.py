from __future__ import annotations
from core.email_atomize.model import RegistroMensaje, SegmentoEnterrado


def test_registro_mensaje_campos_b_por_defecto():
    m = RegistroMensaje(msg_id="MSG-1")
    assert m.fingerprint == "" and m.reconstruido_desde_cita is False
    assert m.fecha_inferida is False and m.ambiguedad_profundidad is False
    assert m.en_revision is False and m.reconstruido_de == ""


def test_segmento_enterrado_defaults():
    s = SegmentoEnterrado(portador_msg_id="MSG-1", estilo="outlook_es", profundidad=1)
    assert s.de == "" and s.confianza == "" and s.fecha_iso == "0000-00-00"
