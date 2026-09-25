"""Tests del parser puro de exports de WhatsApp (core.whatsapp_export)."""
from __future__ import annotations

from datetime import datetime

from core.whatsapp_export import WhatsAppMessage, parse_chat


class TestParseAndroidBasico:
    def test_mensaje_simple(self):
        texto = "8/1/24, 10:32 - Juan Pérez: Hola, ¿qué tal?"
        msgs = parse_chat(texto)
        assert len(msgs) == 1
        m = msgs[0]
        assert isinstance(m, WhatsAppMessage)
        assert m.autor == "Juan Pérez"
        assert m.texto == "Hola, ¿qué tal?"
        assert m.es_sistema is False
        assert m.adjunto_ref is None
        assert m.timestamp == datetime(2024, 1, 8, 10, 32)

    def test_varios_mensajes(self):
        texto = (
            "8/1/24, 10:32 - Juan: Hola\n"
            "8/1/24, 10:33 - Ana López: Buenas\n"
        )
        msgs = parse_chat(texto)
        assert [m.autor for m in msgs] == ["Juan", "Ana López"]
        assert [m.texto for m in msgs] == ["Hola", "Buenas"]

    def test_anio_cuatro_cifras_y_segundos(self):
        texto = "8/1/2024, 10:32:05 - Juan: Hola"
        msgs = parse_chat(texto)
        assert msgs[0].timestamp == datetime(2024, 1, 8, 10, 32, 5)


class TestParseIosMultilineaSistema:
    def test_formato_ios_corchetes(self):
        texto = "[8/1/24 10:32:05] Juan Pérez: Hola desde iPhone"
        msgs = parse_chat(texto)
        assert len(msgs) == 1
        assert msgs[0].autor == "Juan Pérez"
        assert msgs[0].texto == "Hola desde iPhone"
        assert msgs[0].timestamp == datetime(2024, 1, 8, 10, 32, 5)

    def test_ios_con_marca_lrm_invisible(self):
        texto = "‎[8/1/24 10:32:05] Juan: Hola"
        msgs = parse_chat(texto)
        assert len(msgs) == 1
        assert msgs[0].autor == "Juan"

    def test_mensaje_multilinea(self):
        texto = (
            "8/1/24, 10:32 - Juan: Primera línea\n"
            "segunda línea del mismo mensaje\n"
            "tercera línea\n"
            "8/1/24, 10:33 - Ana: Otro mensaje"
        )
        msgs = parse_chat(texto)
        assert len(msgs) == 2
        assert msgs[0].texto == "Primera línea\nsegunda línea del mismo mensaje\ntercera línea"
        assert msgs[1].texto == "Otro mensaje"

    def test_mensaje_de_sistema(self):
        texto = (
            "8/1/24, 9:00 - Los mensajes y las llamadas están cifrados de "
            "extremo a extremo."
        )
        msgs = parse_chat(texto)
        assert len(msgs) == 1
        assert msgs[0].autor is None
        assert msgs[0].es_sistema is True

    def test_hora_12h_pm(self):
        texto = "8/1/24, 1:05 p. m. - Juan: Tarde"
        msgs = parse_chat(texto)
        assert msgs[0].timestamp == datetime(2024, 1, 8, 13, 5)


from core.whatsapp_export import filter_by_date_range, referencias_adjuntos


class TestAdjuntosYFiltro:
    def test_adjunto_android(self):
        texto = "8/1/24, 10:32 - Juan: IMG-20240108-WA0001.jpg (archivo adjunto)"
        msgs = parse_chat(texto)
        assert msgs[0].adjunto_ref == "IMG-20240108-WA0001.jpg"

    def test_adjunto_ios(self):
        texto = "[8/1/24 10:32:05] Juan: ‎<adjunto: 00000042-PHOTO-2024.jpg>"
        msgs = parse_chat(texto)
        assert msgs[0].adjunto_ref == "00000042-PHOTO-2024.jpg"

    def test_adjunto_ios_documento_con_preambulo(self):
        # iOS exporta los DOCUMENTOS con preámbulo (nombre + páginas) antes del
        # tag <adjunto: ...>, que por tanto NO va al inicio de la línea. Las fotos
        # sí empiezan por el tag. El parser debe localizarlo igualmente.
        texto = (
            "[11/10/24, 11:05:02] Toni: T_11_202405243584_V01_TAS.PDF • "
            "‎34 páginas ‎<adjunto: 00000017-T_11_202405243584_V01_TAS.pdf>"
        )
        msgs = parse_chat(texto)
        assert msgs[0].adjunto_ref == "00000017-T_11_202405243584_V01_TAS.pdf"

    def test_adjunto_con_caption_multilinea(self):
        texto = (
            "8/1/24, 10:32 - Juan: IMG-20240108-WA0001.jpg (archivo adjunto)\n"
            "Mira esta foto"
        )
        msgs = parse_chat(texto)
        assert msgs[0].adjunto_ref == "IMG-20240108-WA0001.jpg"
        assert msgs[0].texto.endswith("Mira esta foto")

    def test_media_omitted_android(self):
        texto = "8/1/24, 10:32 - Juan: <Media omitted>"
        msgs = parse_chat(texto)
        assert msgs[0].adjunto_ref == "<Media omitted>"

    def test_multimedia_omitido_es(self):
        texto = "8/1/24, 10:32 - Juan: Multimedia omitido"
        msgs = parse_chat(texto)
        assert msgs[0].adjunto_ref == "<Media omitted>"

    def test_archivo_adjunto_bare_ios(self):
        texto = "[8/1/24 10:32:05] Juan: ‎<archivo adjunto>"
        msgs = parse_chat(texto)
        assert msgs[0].adjunto_ref == "<archivo adjunto>"

    def test_referencias_adjuntos(self):
        texto = (
            "8/1/24, 10:32 - Juan: IMG-1.jpg (archivo adjunto)\n"
            "8/1/24, 10:33 - Juan: Hola\n"
            "8/1/24, 10:34 - Juan: DOC-2.pdf (archivo adjunto)"
        )
        assert referencias_adjuntos(parse_chat(texto)) == ["IMG-1.jpg", "DOC-2.pdf"]

    def test_filter_by_date_range(self):
        texto = (
            "8/1/24, 10:00 - Juan: A\n"
            "9/1/24, 10:00 - Juan: B\n"
            "10/1/24, 10:00 - Juan: C"
        )
        msgs = parse_chat(texto)
        out = filter_by_date_range(
            msgs, desde=datetime(2024, 1, 9), hasta=datetime(2024, 1, 9, 23, 59)
        )
        assert [m.texto for m in out] == ["B"]


class TestMarcasInvisiblesEnAdjuntos:
    """MEJORAS #236: la marca de dirección (U+200E y familia) que el export pone delante o
    detrás del NOMBRE del adjunto viajaba dentro de la referencia, y así no casaba nunca con
    el fichero en disco (W-02V48N: 0 de 39; W-0462E1: 30 «faltantes» con los 30 en el lote).
    `str.strip()` no la quita: no es espacio en blanco."""

    def test_ios_con_la_marca_dentro_del_tag(self):
        texto = "[8/1/24 10:32:05] Juan: \u200e<adjunto: \u200eIMG-20240310-WA0000.jpg>"
        assert parse_chat(texto)[0].adjunto_ref == "IMG-20240310-WA0000.jpg"

    def test_android_con_la_marca_delante_del_nombre(self):
        texto = "8/1/24, 10:32 - Pablo: \u200ePTT-20260409-WA0001.opus (archivo adjunto)"
        assert parse_chat(texto)[0].adjunto_ref == "PTT-20260409-WA0001.opus"

    def test_la_marca_al_final_tambien_sale(self):
        texto = "[8/1/24 10:32:05] Juan: <adjunto: IMG-1.jpg\u200f>"
        assert parse_chat(texto)[0].adjunto_ref == "IMG-1.jpg"

    def test_el_bom_delante_del_nombre_sale(self):
        texto = "[8/1/24 10:32:05] Juan: <adjunto: \ufeffDOC 1.pdf>"
        assert parse_chat(texto)[0].adjunto_ref == "DOC 1.pdf"

    def test_marcas_y_espacios_alternados_salen_todos(self):
        texto = "[8/1/24 10:32:05] Juan: <adjunto: \u200e \u200eIMG-1.jpg \u200f >"
        assert parse_chat(texto)[0].adjunto_ref == "IMG-1.jpg"

    def test_por_dentro_el_nombre_es_el_que_es(self):
        # Solo los BORDES: un carácter raro en medio del nombre forma parte de él, y
        # quitarlo haría que la referencia dejara de casar con un fichero que sí existe.
        texto = "[8/1/24 10:32:05] Juan: <adjunto: a\u200eb.jpg>"
        assert parse_chat(texto)[0].adjunto_ref == "a\u200eb.jpg"

    def test_referencias_limpias_en_los_dos_dialectos(self):
        texto = (
            "[8/1/24 10:32:05] Juan: \u200e<adjunto: \u200eIMG-1.jpg>\n"
            "[8/1/24 10:33:05] Juan: \u200ePTT-2.opus (archivo adjunto)"
        )
        assert referencias_adjuntos(parse_chat(texto)) == ["IMG-1.jpg", "PTT-2.opus"]

# ---------------------------------------------------------------------------
# elegir_chat — UNA regla de «fichero de chat» para todo el canal (MEJORAS #285)
# ---------------------------------------------------------------------------
from core.whatsapp_export import CHAT_TXT, elegir_chat

_IOS = "[8/1/24 10:32:05] Ana: hola"
_AND = "8/1/24, 10:32 - Pablo: hola"


class TestElegirChat:
    """El intake aceptaba cualquier `.txt` y el atomizador solo `_chat.txt`: el chat de un
    export Android en español (`Chat de WhatsApp con <contacto>.txt`) se depositaba y se
    quedaba fuera de la atomización (W-0462E1: 173 mensajes)."""

    def test_prefiere_chat_txt_aunque_haya_otros_txt(self):
        assert elegir_chat({CHAT_TXT: _IOS, "Acta.txt": "texto libre"}) == CHAT_TXT

    def test_chat_txt_se_elige_aunque_no_se_interprete(self):
        # Como hasta ahora: un `_chat.txt` es el chat aunque el parser no lo entienda.
        assert elegir_chat({CHAT_TXT: "x"}) == CHAT_TXT

    def test_android_por_contenido_y_no_por_orden(self):
        # «Acta.txt» va antes por orden alfabético y NO es una conversación: es un adjunto.
        textos = {"Acta.txt": "texto libre", "Chat de WhatsApp con Pablo.txt": _AND}
        assert elegir_chat(textos) == "Chat de WhatsApp con Pablo.txt"

    def test_si_ninguno_se_interpreta_el_primero_por_orden(self):
        # Custodia antes que parser: el intake no deja de depositar por no entender.
        assert elegir_chat({"b.txt": "x", "a.txt": "y"}) == "a.txt"

    def test_la_extension_no_distingue_mayusculas(self):
        assert elegir_chat({"CHAT.TXT": _AND}) == "CHAT.TXT"

    def test_un_derivado_nuestro_no_es_candidato(self):
        assert elegir_chat({"_chat_recortado.txt": _AND, "foto.jpg": ""}) is None

    def test_sin_txt_no_hay_chat(self):
        assert elegir_chat({}) is None
        assert elegir_chat({"foto.jpg": "x"}) is None

    def test_R1_H01_un_nombre_con_guion_bajo_no_es_un_derivado(self):
        """R1/H-01: excluir todo lo que empieza por `_` rechazaba un export cuyo chat se
        llamara `_conversacion.txt`. Derivados nuestros solo son los que el canal escribe."""
        assert elegir_chat({"_conversacion.txt": _AND}) == "_conversacion.txt"

    def test_R1_H02_un_adjunto_interpretable_no_le_gana_al_chat_que_cita_los_ficheros(self):
        """R1/H-02: con un `.txt` adjunto que se interpreta, el primero por orden ganaba.
        El chat del export es el que cita los ficheros que vienen en el export."""
        textos = {"Acta.txt": "8/1/24, 09:00 - Otro: Acta",
                  "Chat de WhatsApp con Ana.txt": "8/1/24, 10:00 - Ana: IMG.jpg (archivo adjunto)"}
        presentes = [*textos, "IMG.jpg"]
        assert elegir_chat(textos, presentes) == "Chat de WhatsApp con Ana.txt"

    def test_R1_H02_un_export_reenviado_que_el_chat_cita_no_es_el_chat(self):
        largo = "\n".join(f"8/1/24, 09:{i:02d} - X: m{i}" for i in range(10))
        textos = {"A reenviado.txt": largo,
                  "Chat de WhatsApp con Pablo.txt":
                      "8/1/24, 10:00 - Pablo: A reenviado.txt (archivo adjunto)"}
        assert elegir_chat(textos, textos) == "Chat de WhatsApp con Pablo.txt"

    def test_R1_H02_sin_ficheros_citados_gana_la_conversacion_mas_larga(self):
        textos = {"Acta.txt": "8/1/24, 09:00 - Otro: Acta",
                  "Chat de WhatsApp con Ana.txt":
                      "8/1/24, 10:00 - Ana: uno\n8/1/24, 10:01 - Ana: dos\n8/1/24, 10:02 - Eva: tres"}
        assert elegir_chat(textos) == "Chat de WhatsApp con Ana.txt"

    def test_R1_H03_sin_custodia_un_txt_que_no_es_conversacion_no_es_chat(self):
        """La regla 3 es del intake —no dejar de depositar—; el atomizador no la usa."""
        assert elegir_chat({"notas.txt": "nota libre"}, custodia=False) is None
        assert elegir_chat({"notas.txt": "nota libre"}) == "notas.txt"
