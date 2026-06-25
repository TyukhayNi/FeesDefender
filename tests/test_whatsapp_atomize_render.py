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


def test_indice_enlace_robusto_a_espacios_y_parentesis():
    # Bug destapado por la corrida real (chats "PersonaUno (suiza)" etc.): un destino
    # de enlace markdown con espacios sin <...> es inválido en CommonMark. Debe ir envuelto.
    from core.whatsapp_atomize.render import render_indice
    md = render_indice({"PersonaUno (suiza)": 16})
    assert "(<PersonaUno (suiza)__LECTURA.md>)" in md


def test_indice_adjuntos_lista_fichas():
    from core.email_atomize.model import AdjuntoUnico
    from core.whatsapp_atomize.render import render_indice_adjuntos
    adj = [AdjuntoUnico(att_id="ATT-00001", sha256="abc123", nombre_original="foto.jpg")]
    md = render_indice_adjuntos(adj)
    assert "ATT-00001" in md and "foto.jpg" in md and "abc123" in md


def test_cronologia_cross_chat_ordenada():
    from core.whatsapp_atomize.render import render_cronologia
    msgs = [
        RegistroMensajeWA(msg_id="MSG-00002", chat_id="chatB", fecha_iso="2024-10-31",
                          hora="0900", autor_export="Ana", texto="b"),
        RegistroMensajeWA(msg_id="MSG-00001", chat_id="chatA", fecha_iso="2024-10-30",
                          hora="1000", autor_export="Juan", texto="a"),
    ]
    md = render_cronologia(msgs)
    assert md.index("MSG-00001") < md.index("MSG-00002")  # ordenado por fecha
    assert "chatA" in md and "chatB" in md
    assert "NO editar" in md


def test_lectura_enlaza_ficha_adjunto():
    from core.email_atomize.model import AdjuntoRef
    msgs = [RegistroMensajeWA(msg_id="MSG-00001", fecha_iso="2024-10-30", hora="1000",
                              autor_export="Juan", texto="foto",
                              adjunto=AdjuntoRef(nombre="f.jpg"))]
    por_ref = {"f.jpg": {"att_id": "ATT-00001", "ausente": False}}
    md = render_chat_lectura("chat-x", msgs, [], por_ref)
    assert "INDICE_ADJUNTOS.md" in md and "ATT-00001" in md
    # un adjunto ausente NO debe enlazar
    msgs2 = [RegistroMensajeWA(msg_id="MSG-00002", fecha_iso="2024-10-30", hora="1001",
                               autor_export="Ana", texto="x",
                               adjunto=AdjuntoRef(nombre="falta.jpg"))]
    md2 = render_chat_lectura("chat-x", msgs2, [], {"falta.jpg": {"att_id": None, "ausente": True}})
    assert "(ausente)" in md2
