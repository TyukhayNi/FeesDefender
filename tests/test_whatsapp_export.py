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
