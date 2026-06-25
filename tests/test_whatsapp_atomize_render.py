from core.whatsapp_atomize.model import RegistroMensajeWA, AtomEnterrado
from core.whatsapp_atomize.render import render_chat_lectura, render_enterrado


def test_chat_lectura_numerado_con_autor_resuelto():
    msgs = [
        RegistroMensajeWA(msg_id="MSG-00001", fecha_iso="2024-10-30", hora="1000",
                          autor_export="+34600", rol="propietario", texto="Hola"),
        RegistroMensajeWA(msg_id="MSG-00002", fecha_iso="2024-10-30", hora="1001",
                          autor_export="Ana", texto="Reenviado", es_reenviado=True),
    ]
    md = render_chat_lectura("chat-x", msgs, [], {})
    assert "MSG-00001" in md and "MSG-00002" in md
    assert "propietario" in md
    assert "reenviado" in md.lower()
    assert "NO editar" in md  # cabecera de generado


def test_enterrado_lleva_banner_por_verificar():
    a = AtomEnterrado(enterrado_id="ENT-00001", portador_msg_id="MSG-00002",
                      de="juan@ej.com", fecha_iso="2024-05-14", extracto="...")
    md = render_enterrado(a)
    assert "AUTORÍA POR VERIFICAR" in md
    assert "juan@ej.com" in md
    assert "MSG-00002" in md


def test_indice_adjuntos_lista_fichas():
    from core.email_atomize.model import AdjuntoUnico
    from core.whatsapp_atomize.render import render_indice_adjuntos
    adj = [AdjuntoUnico(att_id="ATT-00001", sha256="abc123", nombre_original="foto.jpg")]
    md = render_indice_adjuntos(adj)
    assert "ATT-00001" in md and "foto.jpg" in md and "abc123" in md
