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
