"""Tests unitarios para las funciones REST de sudespacho_create.

Cubre:
- _tag_id_from_token()
- _tags_to_rest()
- _build_rest_payload_extrajudicial()
- _build_rest_payload_judicial()
- create_expediente_rest() y create_expediente_judicial_rest() con httpx mockeado
- create_expediente() estrategia REST-first (fallback a legacy si REST falla)
- create_expediente_judicial() estrategia REST-first

No hace llamadas reales al CRM. Todo el I/O de red está interceptado con
pytest-mock / unittest.mock.
"""

from __future__ import annotations

import json
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from core.sudespacho_create import (
    # Constantes / helpers
    TAG_VERDE_NEGATIVA_ARRAS,
    TAG_LILA_POSIBILIDAD_50,
    TAG_ROJO_MaRS6,
    TAG_SENTINEL,
    POSICION_ACTOR,
    POSICION_DEMANDADO,
    MATERIA_CIVIL,
    SUBTIPO_EXTRAJUDICIAL,
    TIPO_PROC_JUICIO_VERBAL,
    # DTOs
    NuevoExpedienteExtrajudicial,
    NuevoExpedienteJudicial,
    # Funciones REST
    _tag_id_from_token,
    _tags_to_rest,
    _build_rest_payload_extrajudicial,
    _build_rest_payload_judicial,
    create_expediente_rest,
    create_expediente_judicial_rest,
    # Funciones orquestadoras
    create_expediente,
    create_expediente_judicial,
    # Errores
    SudespachoCreateError,
)


# ---------------------------------------------------------------------------
# Fixtures comunes
# ---------------------------------------------------------------------------

@pytest.fixture
def datos_extrajudicial() -> NuevoExpedienteExtrajudicial:
    return NuevoExpedienteExtrajudicial(
        referencia_cliente="MaRS6 - Gran Vía 1 - (W-001TEST) - Negativa arras",
        fecha_apertura=date(2026, 5, 6),
        materia=MATERIA_CIVIL,
        subtipo=SUBTIPO_EXTRAJUDICIAL,
        cuantia=10000.0,
        costas=0.0,
        intereses=0.0,
        responsable="Nikolai_Tyukhay",
        posicion=POSICION_ACTOR,
        tags=[TAG_ROJO_MaRS6, TAG_VERDE_NEGATIVA_ARRAS, TAG_LILA_POSIBILIDAD_50, TAG_SENTINEL],
    )


@pytest.fixture
def datos_judicial() -> NuevoExpedienteJudicial:
    return NuevoExpedienteJudicial(
        referencia_cliente="MaRS6 - Gran Vía 1 - (W-001TEST) - Negativa arras",
        fecha_apertura=date(2026, 5, 6),
        tipo_asunto=MATERIA_CIVIL,
        tipo_procedimiento=TIPO_PROC_JUICIO_VERBAL,
        cuantia=10000.0,
        costas=0.0,
        intereses=0.0,
        abogado_principal="Nikolai_Tyukhay",
        posicion=POSICION_ACTOR,
        tags=[TAG_ROJO_MaRS6, TAG_VERDE_NEGATIVA_ARRAS, TAG_LILA_POSIBILIDAD_50, TAG_SENTINEL],
    )


# ---------------------------------------------------------------------------
# _tag_id_from_token
# ---------------------------------------------------------------------------

class TestTagIdFromToken:
    def test_formato_completo(self):
        assert _tag_id_from_token("#528800___214") == "214"

    def test_solo_numero(self):
        """Si ya es un ID numérico, se devuelve tal cual."""
        assert _tag_id_from_token("214") == "214"

    def test_color_con_varios_guiones_bajos(self):
        """El split debe usar ___ (triple) exactamente."""
        assert _tag_id_from_token("#a32929___130") == "130"

    def test_lila(self):
        assert _tag_id_from_token("#5229a3___286") == "286"


# ---------------------------------------------------------------------------
# _tags_to_rest
# ---------------------------------------------------------------------------

class TestTagsToRest:
    def test_convierte_tokens(self):
        tags = [TAG_ROJO_MaRS6, TAG_VERDE_NEGATIVA_ARRAS, TAG_SENTINEL]
        result = _tags_to_rest(tags)
        assert result == ["130", "127"]

    def test_filtra_sentinel(self):
        result = _tags_to_rest([TAG_SENTINEL])
        assert result == []

    def test_filtra_vacios(self):
        result = _tags_to_rest(["", TAG_ROJO_MaRS6, ""])
        assert result == ["130"]

    def test_lista_vacia(self):
        assert _tags_to_rest([]) == []

    def test_sin_sentinel(self):
        """Lista sin sentinel también funciona (es opcional en REST)."""
        result = _tags_to_rest([TAG_ROJO_MaRS6, TAG_LILA_POSIBILIDAD_50])
        assert result == ["130", "286"]


# ---------------------------------------------------------------------------
# _build_rest_payload_extrajudicial
# ---------------------------------------------------------------------------

class TestBuildRestPayloadExtrajudicial:
    def test_campos_obligatorios_presentes(self, datos_extrajudicial):
        p = _build_rest_payload_extrajudicial(datos_extrajudicial)
        for campo in ("Referencia_Cliente", "Fecha_alta", "Tipo_Asunto",
                      "Tipo_Procedimiento", "cuantia", "costas", "intereses",
                      "total", "Profesional", "tags"):
            assert campo in p, f"Falta campo '{campo}'"

    def test_fecha_formato_iso(self, datos_extrajudicial):
        p = _build_rest_payload_extrajudicial(datos_extrajudicial)
        assert p["Fecha_alta"] == "2026-05-06"

    def test_cuantia_entero(self, datos_extrajudicial):
        p = _build_rest_payload_extrajudicial(datos_extrajudicial)
        assert p["cuantia"] == 10000
        assert isinstance(p["cuantia"], int)

    def test_total_suma(self, datos_extrajudicial):
        p = _build_rest_payload_extrajudicial(datos_extrajudicial)
        assert p["total"] == 10000.0

    def test_tags_convertidos(self, datos_extrajudicial):
        p = _build_rest_payload_extrajudicial(datos_extrajudicial)
        # Sentinel filtrado; solo IDs numéricos
        assert TAG_SENTINEL not in p["tags"]
        assert "130" in p["tags"]   # TAG_ROJO_MaRS6
        assert "127" in p["tags"]   # TAG_VERDE_NEGATIVA_ARRAS

    def test_serie_expediente_es_anno(self, datos_extrajudicial):
        p = _build_rest_payload_extrajudicial(datos_extrajudicial)
        assert p["serie_expediente"] == "2026"

    def test_numero_expediente_es_cero(self, datos_extrajudicial):
        p = _build_rest_payload_extrajudicial(datos_extrajudicial)
        assert p["Numero_Expediente"] == "0"


# ---------------------------------------------------------------------------
# _build_rest_payload_judicial
# ---------------------------------------------------------------------------

class TestBuildRestPayloadJudicial:
    def test_campos_obligatorios_presentes(self, datos_judicial):
        p = _build_rest_payload_judicial(datos_judicial)
        for campo in ("referencia_cliente", "fecha_alta", "tipo_asunto",
                      "tipo_procedimiento", "cuantia", "costas", "intereses",
                      "total", "profesional_asignado", "tags"):
            assert campo in p, f"Falta campo '{campo}'"

    def test_nombres_en_minusculas(self, datos_judicial):
        """Judicial usa lowercase (diferente de extrajudicial que es CamelCase)."""
        p = _build_rest_payload_judicial(datos_judicial)
        assert "referencia_cliente" in p
        assert "Referencia_Cliente" not in p

    def test_fecha_formato_iso(self, datos_judicial):
        p = _build_rest_payload_judicial(datos_judicial)
        assert p["fecha_alta"] == "2026-05-06"

    def test_total_suma(self, datos_judicial):
        p = _build_rest_payload_judicial(datos_judicial)
        assert p["total"] == 10000.0

    def test_tags_convertidos(self, datos_judicial):
        p = _build_rest_payload_judicial(datos_judicial)
        assert TAG_SENTINEL not in p["tags"]
        assert "130" in p["tags"]


# ---------------------------------------------------------------------------
# create_expediente_rest (mock httpx)
# ---------------------------------------------------------------------------

class TestCreateExpedienteRest:
    def test_devuelve_id_cuando_201(self, datos_extrajudicial, monkeypatch):
        monkeypatch.setenv("SUDESPACHO_API_KEY", "test-api-key")

        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"id": 599, "message": "Created!"}

        with patch("core.sudespacho_create.httpx.post", return_value=mock_resp) as mock_post:
            eid = create_expediente_rest(datos_extrajudicial)

        assert eid == "599"
        call_kwargs = mock_post.call_args
        assert "x-api-key" in call_kwargs.kwargs["headers"]
        assert call_kwargs.kwargs["headers"]["x-api-key"] == "test-api-key"

    def test_lanza_error_si_no_jwt(self, datos_extrajudicial, monkeypatch):
        monkeypatch.delenv("SUDESPACHO_API_KEY", raising=False)
        with pytest.raises(ValueError, match="SUDESPACHO_API_KEY"):
            create_expediente_rest(datos_extrajudicial)

    def test_lanza_error_si_no_201(self, datos_extrajudicial, monkeypatch):
        monkeypatch.setenv("SUDESPACHO_API_KEY", "test-api-key")

        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.text = "Bad Request"

        with patch("core.sudespacho_create.httpx.post", return_value=mock_resp):
            with pytest.raises(SudespachoCreateError):
                create_expediente_rest(datos_extrajudicial)

    def test_url_endpoint_correcto(self, datos_extrajudicial, monkeypatch):
        monkeypatch.setenv("SUDESPACHO_API_KEY", "test-api-key")

        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"id": 600}

        with patch("core.sudespacho_create.httpx.post", return_value=mock_resp) as mock_post:
            create_expediente_rest(datos_extrajudicial)

        url_llamado = mock_post.call_args.args[0]
        assert "api-crm-commons-pro.sudespacho.biz" in url_llamado
        assert "extrajudiciales" in url_llamado


# ---------------------------------------------------------------------------
# create_expediente_judicial_rest (mock httpx)
# ---------------------------------------------------------------------------

class TestCreateExpedienteJudicialRest:
    def test_devuelve_id_cuando_201(self, datos_judicial, monkeypatch):
        monkeypatch.setenv("SUDESPACHO_API_KEY", "test-api-key")

        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"id": 700, "message": "Created!"}

        with patch("core.sudespacho_create.httpx.post", return_value=mock_resp) as mock_post:
            eid = create_expediente_judicial_rest(datos_judicial)

        assert eid == "700"
        url_llamado = mock_post.call_args.args[0]
        assert "expedientes_judiciales" in url_llamado

    def test_lanza_error_si_no_201(self, datos_judicial, monkeypatch):
        monkeypatch.setenv("SUDESPACHO_API_KEY", "test-api-key")

        mock_resp = MagicMock()
        mock_resp.status_code = 422
        mock_resp.text = "Unprocessable"

        with patch("core.sudespacho_create.httpx.post", return_value=mock_resp):
            with pytest.raises(SudespachoCreateError):
                create_expediente_judicial_rest(datos_judicial)


# ---------------------------------------------------------------------------
# create_expediente — estrategia REST-first con fallback
# ---------------------------------------------------------------------------

class TestCreateExpedienteRestFirst:
    def test_usa_rest_si_jwt_disponible(self, datos_extrajudicial, monkeypatch):
        monkeypatch.setenv("SUDESPACHO_API_KEY", "test-api-key")

        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"id": 601}

        with patch("core.sudespacho_create.httpx.post", return_value=mock_resp):
            eid = create_expediente(datos_extrajudicial)

        assert eid == "601"

    def test_fallback_a_legacy_si_rest_falla(self, datos_extrajudicial, monkeypatch):
        """Si REST lanza excepción, debe intentarse la vía legacy."""
        monkeypatch.setenv("SUDESPACHO_API_KEY", "test-api-key")

        with patch("core.sudespacho_create.httpx.post", side_effect=Exception("network error")):
            with patch("core.sudespacho_create.SudespachoLegacyClient") as MockClient:
                mock_client = MagicMock()
                MockClient.return_value = mock_client
                mock_client.__enter__ = MagicMock(return_value=mock_client)
                mock_client.__exit__ = MagicMock(return_value=False)
                mock_client.get_csrf_token.return_value = "csrf-abc"
                mock_client.post_form.return_value = {"id": "602"}

                with patch("core.sudespacho_create.extract_id_from_response", return_value="602"):
                    eid = create_expediente(datos_extrajudicial)

        assert eid == "602"


# ---------------------------------------------------------------------------
# create_expediente_judicial — estrategia REST-first con fallback
# ---------------------------------------------------------------------------

class TestCreateExpedienteJudicialRestFirst:
    def test_usa_rest_si_jwt_disponible(self, datos_judicial, monkeypatch):
        monkeypatch.setenv("SUDESPACHO_API_KEY", "test-api-key")

        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"id": 701}

        with patch("core.sudespacho_create.httpx.post", return_value=mock_resp):
            eid = create_expediente_judicial(datos_judicial)

        assert eid == "701"

    def test_fallback_a_legacy_si_rest_falla(self, datos_judicial, monkeypatch):
        monkeypatch.setenv("SUDESPACHO_API_KEY", "test-api-key")

        with patch("core.sudespacho_create.httpx.post", side_effect=Exception("network error")):
            with patch("core.sudespacho_create.SudespachoLegacyClient") as MockClient:
                mock_client = MagicMock()
                MockClient.return_value = mock_client
                mock_client.__enter__ = MagicMock(return_value=mock_client)
                mock_client.__exit__ = MagicMock(return_value=False)
                mock_client.get_csrf_token.return_value = "csrf-abc"
                mock_client.post_form.return_value = {"id": "702"}

                with patch("core.sudespacho_create.extract_id_from_response", return_value="702"):
                    eid = create_expediente_judicial(datos_judicial)

        assert eid == "702"

