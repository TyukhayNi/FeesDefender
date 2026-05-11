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
    _get_next_num_expediente_judicial,
    _get_next_num_expediente_extrajudicial,
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
    """Tests del builder REST extrajudicial.

    Desde 2026-05-11 el builder llama a ``_get_next_num_expediente_extrajudicial``
    para calcular max+1 antes del POST (el endpoint REST auto-asigna de forma
    intermitente y a veces deja ``Numero_Expediente=0``). Mockeamos esa función
    para que cada test sea hermético respecto a la red.
    """

    @pytest.fixture(autouse=True)
    def _mock_next_num(self):
        """Por defecto la query falla (None) → mantiene Numero_Expediente='0'.
        Los tests que quieran probar la rama exitosa hacen su propio patch."""
        with patch(
            "core.sudespacho_create._get_next_num_expediente_extrajudicial",
            return_value=None,
        ):
            yield

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

    # -------------------------------------------------------------------
    # Tests de Numero_Expediente — bug corregido 2026-05-11
    # -------------------------------------------------------------------

    def test_numero_expediente_mantiene_cero_si_query_falla(self, datos_extrajudicial):
        """Si _get_next_num_expediente_extrajudicial devuelve None (sin API key,
        timeout, etc.), Numero_Expediente se mantiene en '0' — comportamiento
        previo al fix; el servidor podría auto-asignar o no, pero no empeoramos."""
        p = _build_rest_payload_extrajudicial(datos_extrajudicial)
        assert p["Numero_Expediente"] == "0"

    def test_numero_expediente_se_calcula_si_query_exitosa(self, datos_extrajudicial):
        """Si la consulta CRM devuelve max+1, ese valor reemplaza el '0' inicial."""
        with patch(
            "core.sudespacho_create._get_next_num_expediente_extrajudicial",
            return_value=51,
        ):
            p = _build_rest_payload_extrajudicial(datos_extrajudicial)
        assert p["Numero_Expediente"] == "51"

    def test_numero_expediente_no_es_cero_cuando_query_exitosa(self, datos_extrajudicial):
        """Regresión del bug: cuando la query funciona, Numero_Expediente NUNCA
        debe ser '0' (causa expediente con número 0 en el CRM — ID 605 de 2026)."""
        with patch(
            "core.sudespacho_create._get_next_num_expediente_extrajudicial",
            return_value=1,
        ):
            p = _build_rest_payload_extrajudicial(datos_extrajudicial)
        assert p["Numero_Expediente"] != "0"


# ---------------------------------------------------------------------------
# _build_rest_payload_judicial
# ---------------------------------------------------------------------------

class TestBuildRestPayloadJudicial:
    def test_campos_obligatorios_presentes(self, datos_judicial):
        with patch("core.sudespacho_create._get_next_num_expediente_judicial", return_value=None):
            p = _build_rest_payload_judicial(datos_judicial)
        for campo in ("referencia_cliente", "fecha_alta", "tipo_asunto",
                      "tipo_procedimiento", "cuantia", "costas", "intereses",
                      "total", "profesional_asignado", "tags"):
            assert campo in p, f"Falta campo '{campo}'"

    def test_nombres_en_minusculas(self, datos_judicial):
        """Judicial usa lowercase (diferente de extrajudicial que es CamelCase)."""
        with patch("core.sudespacho_create._get_next_num_expediente_judicial", return_value=None):
            p = _build_rest_payload_judicial(datos_judicial)
        assert "referencia_cliente" in p
        assert "Referencia_Cliente" not in p

    def test_fecha_formato_iso(self, datos_judicial):
        with patch("core.sudespacho_create._get_next_num_expediente_judicial", return_value=None):
            p = _build_rest_payload_judicial(datos_judicial)
        assert p["fecha_alta"] == "2026-05-06"

    def test_total_suma(self, datos_judicial):
        with patch("core.sudespacho_create._get_next_num_expediente_judicial", return_value=None):
            p = _build_rest_payload_judicial(datos_judicial)
        assert p["total"] == 10000.0

    def test_tags_convertidos(self, datos_judicial):
        with patch("core.sudespacho_create._get_next_num_expediente_judicial", return_value=None):
            p = _build_rest_payload_judicial(datos_judicial)
        assert TAG_SENTINEL not in p["tags"]
        assert "130" in p["tags"]

    # -------------------------------------------------------------------
    # Tests de num_expediente — bug corregido 2026-05-07
    # -------------------------------------------------------------------

    def test_num_expediente_incluido_cuando_query_exitosa(self, datos_judicial):
        """Si _get_next_num_expediente_judicial devuelve un número, debe estar en el payload."""
        with patch("core.sudespacho_create._get_next_num_expediente_judicial", return_value=5):
            p = _build_rest_payload_judicial(datos_judicial)
        assert "num_expediente" in p
        assert p["num_expediente"] == "5"

    def test_num_expediente_omitido_cuando_query_falla(self, datos_judicial):
        """Si la consulta al CRM falla (devuelve None), num_expediente se omite del payload
        para que el servidor intente auto-asignar (en lugar de almacenar 0 literalmente)."""
        with patch("core.sudespacho_create._get_next_num_expediente_judicial", return_value=None):
            p = _build_rest_payload_judicial(datos_judicial)
        assert "num_expediente" not in p

    def test_num_expediente_no_es_cero_literal(self, datos_judicial):
        """Regresión: el payload judicial NUNCA debe incluir num_expediente='0' — eso
        causaba que el expediente quedara con número 0 en el CRM (bug 2026-05-07)."""
        with patch("core.sudespacho_create._get_next_num_expediente_judicial", return_value=1):
            p = _build_rest_payload_judicial(datos_judicial)
        # Si la query devuelve un número, nunca debe ser la cadena "0"
        if "num_expediente" in p:
            assert p["num_expediente"] != "0", (
                "num_expediente no puede ser '0' — causa bug de número correlativo ausente"
            )

    def test_serie_expediente_es_anno(self, datos_judicial):
        with patch("core.sudespacho_create._get_next_num_expediente_judicial", return_value=None):
            p = _build_rest_payload_judicial(datos_judicial)
        assert p["serie_expediente"] == "2026"


# ---------------------------------------------------------------------------
# _get_next_num_expediente_judicial
# ---------------------------------------------------------------------------

class TestGetNextNumExpedienteJudicial:
    """Tests para la función que consulta el siguiente número correlativo judicial.

    Esta función corrige el bug por el que el endpoint REST judicial almacenaba
    num_expediente=0 literalmente en lugar de asignar el número correlativo.

    Bugs corregidos en v2 (2026-05-07):
      - properties[] es requerido por el endpoint (sin ellos → HTTP 500)
      - Operador correcto es "equal" (no "eq" → HTTP 404)
      - Clave de respuesta es "totalItems" (no "hydra:totalItems")
      - Estrategia: max(num_expediente)+1 en lugar de count+1 para evitar saltos
    """

    # Respuesta real del endpoint: {"totalItems": N, "items": [{id, values:[{property:{name}, value}]}]}
    @staticmethod
    def _make_items(*num_expediente_values):
        """Construye la lista items con los valores de num_expediente dados."""
        items = []
        for v in num_expediente_values:
            items.append({
                "id": "999",
                "values": [{
                    "property": {"name": "num_expediente"},
                    "value": str(v) if v is not None else "",
                }]
            })
        return items

    def test_devuelve_max_mas_uno_cuando_200(self, monkeypatch):
        """Devuelve max(num_expediente)+1, no count+1, para evitar saltos."""
        monkeypatch.setenv("SUDESPACHO_API_KEY", "test-api-key")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        # 3 expedientes: nums 10, 12, 33 → siguiente debe ser 34
        mock_resp.json.return_value = {
            "totalItems": 3,
            "items": self._make_items(10, 12, 33),
        }

        with patch("core.sudespacho_create.httpx.get", return_value=mock_resp):
            result = _get_next_num_expediente_judicial(2026)

        assert result == 34

    def test_devuelve_uno_cuando_no_hay_expedientes(self, monkeypatch):
        """Primer expediente del año → items vacío → max=0 → devuelve 1."""
        monkeypatch.setenv("SUDESPACHO_API_KEY", "test-api-key")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"totalItems": 0, "items": []}

        with patch("core.sudespacho_create.httpx.get", return_value=mock_resp):
            result = _get_next_num_expediente_judicial(2026)

        assert result == 1

    def test_ignora_items_con_num_vacio(self, monkeypatch):
        """Items con num_expediente vacío (ej. creados antes del fix) no cuentan."""
        monkeypatch.setenv("SUDESPACHO_API_KEY", "test-api-key")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        # 3 expedientes: nums 5, "", 7 → ignora el vacío → max=7 → devuelve 8
        mock_resp.json.return_value = {
            "totalItems": 3,
            "items": self._make_items(5, None, 7),
        }

        with patch("core.sudespacho_create.httpx.get", return_value=mock_resp):
            result = _get_next_num_expediente_judicial(2026)

        assert result == 8

    def test_devuelve_none_cuando_api_error(self, monkeypatch):
        """Si la API devuelve error HTTP, retorna None (no lanza excepción)."""
        monkeypatch.setenv("SUDESPACHO_API_KEY", "test-api-key")

        mock_resp = MagicMock()
        mock_resp.status_code = 500

        with patch("core.sudespacho_create.httpx.get", return_value=mock_resp):
            result = _get_next_num_expediente_judicial(2026)

        assert result is None

    def test_devuelve_none_cuando_sin_api_key(self, monkeypatch):
        """Sin SUDESPACHO_API_KEY configurado, retorna None sin lanzar excepción."""
        monkeypatch.delenv("SUDESPACHO_API_KEY", raising=False)
        result = _get_next_num_expediente_judicial(2026)
        assert result is None

    def test_devuelve_none_cuando_red_falla(self, monkeypatch):
        """Si la petición HTTP falla (timeout, etc.), retorna None."""
        monkeypatch.setenv("SUDESPACHO_API_KEY", "test-api-key")

        import httpx as httpx_module
        with patch("core.sudespacho_create.httpx.get",
                   side_effect=httpx_module.HTTPError("timeout")):
            result = _get_next_num_expediente_judicial(2026)

        assert result is None

    def test_usa_filtro_y_operador_correcto(self, monkeypatch):
        """Verifica que la consulta usa serie_expediente, operator=equal y properties[]."""
        monkeypatch.setenv("SUDESPACHO_API_KEY", "test-api-key")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"totalItems": 1, "items": self._make_items(3)}

        with patch("core.sudespacho_create.httpx.get", return_value=mock_resp) as mock_get:
            _get_next_num_expediente_judicial(2025)

        call_kwargs = mock_get.call_args
        params = call_kwargs.kwargs.get("params", call_kwargs.args[1] if len(call_kwargs.args) > 1 else [])
        params_str = str(params)
        assert "2025" in params_str
        assert "serie_expediente" in params_str
        assert "equal" in params_str          # operador correcto (no "eq")
        assert "num_expediente" in params_str  # properties[] incluido


# ---------------------------------------------------------------------------
# _get_next_num_expediente_extrajudicial
# ---------------------------------------------------------------------------

class TestGetNextNumExpedienteExtrajudicial:
    """Tests del cálculo del siguiente correlativo extrajudicial (fix 2026-05-11).

    Patrón idéntico al judicial pero contra ``/api/element_registries/extrajudiciales``
    y propiedad ``Numero_Expediente`` (CamelCase). Necesario porque el endpoint
    extrajudicial auto-asigna de forma intermitente (caso real: ID 605 quedó
    en 0; ID 606 se asignó correctamente a 49).
    """

    @staticmethod
    def _make_items(*numero_expediente_values):
        """Items con la propiedad ``Numero_Expediente`` (CamelCase, no lowercase)."""
        items = []
        for v in numero_expediente_values:
            items.append({
                "id": "999",
                "values": [{
                    "property": {"name": "Numero_Expediente"},
                    "value": str(v) if v is not None else "",
                }]
            })
        return items

    def test_devuelve_max_mas_uno_cuando_200(self, monkeypatch):
        """Devuelve max+1, no count+1 (evita saltos cuando hay registros en blanco)."""
        monkeypatch.setenv("SUDESPACHO_API_KEY", "test-api-key")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "totalItems": 3,
            "items": self._make_items(10, 12, 33),
        }

        with patch("core.sudespacho_create.httpx.get", return_value=mock_resp):
            result = _get_next_num_expediente_extrajudicial(2026)

        assert result == 34

    def test_devuelve_uno_cuando_no_hay_expedientes(self, monkeypatch):
        """Primer expediente del año → items vacío → max=0 → devuelve 1."""
        monkeypatch.setenv("SUDESPACHO_API_KEY", "test-api-key")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"totalItems": 0, "items": []}

        with patch("core.sudespacho_create.httpx.get", return_value=mock_resp):
            result = _get_next_num_expediente_extrajudicial(2026)

        assert result == 1

    def test_ignora_items_con_num_vacio_o_cero(self, monkeypatch):
        """Items con Numero_Expediente vacío o '0' (los anteriores al fix) no
        cuentan para el max. Es exactamente el caso del ID 605 de 2026."""
        monkeypatch.setenv("SUDESPACHO_API_KEY", "test-api-key")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        # 4 expedientes: nums 5, "", "0", 7 → ignora vacío y "0" → max=7 → devuelve 8
        mock_resp.json.return_value = {
            "totalItems": 4,
            "items": self._make_items(5, None, 0, 7),
        }

        with patch("core.sudespacho_create.httpx.get", return_value=mock_resp):
            result = _get_next_num_expediente_extrajudicial(2026)

        # "0" tras .isdigit() pasa la comprobación pero max(0, anterior) no afecta.
        # El resultado funcional sigue siendo max real ignorando vacíos.
        assert result == 8

    def test_devuelve_none_cuando_api_error(self, monkeypatch):
        """Si la API devuelve error HTTP, retorna None (no lanza excepción)."""
        monkeypatch.setenv("SUDESPACHO_API_KEY", "test-api-key")

        mock_resp = MagicMock()
        mock_resp.status_code = 500

        with patch("core.sudespacho_create.httpx.get", return_value=mock_resp):
            result = _get_next_num_expediente_extrajudicial(2026)

        assert result is None

    def test_devuelve_none_cuando_sin_api_key(self, monkeypatch):
        """Sin SUDESPACHO_API_KEY configurado, retorna None sin lanzar excepción."""
        monkeypatch.delenv("SUDESPACHO_API_KEY", raising=False)
        result = _get_next_num_expediente_extrajudicial(2026)
        assert result is None

    def test_devuelve_none_cuando_red_falla(self, monkeypatch):
        """Si la petición HTTP falla (timeout, etc.), retorna None."""
        monkeypatch.setenv("SUDESPACHO_API_KEY", "test-api-key")

        import httpx as httpx_module
        with patch("core.sudespacho_create.httpx.get",
                   side_effect=httpx_module.HTTPError("timeout")):
            result = _get_next_num_expediente_extrajudicial(2026)

        assert result is None

    def test_usa_filtro_y_operador_correcto(self, monkeypatch):
        """Verifica que la consulta usa serie_expediente, operator=equal y properties[]
        con la propiedad CamelCase Numero_Expediente (no lowercase como judicial)."""
        monkeypatch.setenv("SUDESPACHO_API_KEY", "test-api-key")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"totalItems": 1, "items": self._make_items(3)}

        with patch("core.sudespacho_create.httpx.get", return_value=mock_resp) as mock_get:
            _get_next_num_expediente_extrajudicial(2025)

        call_kwargs = mock_get.call_args
        params = call_kwargs.kwargs.get("params", call_kwargs.args[1] if len(call_kwargs.args) > 1 else [])
        params_str = str(params)
        assert "2025" in params_str
        assert "serie_expediente" in params_str
        assert "equal" in params_str               # operador correcto (no "eq")
        assert "Numero_Expediente" in params_str   # CamelCase (no lowercase)
        # Endpoint correcto
        url_arg = mock_get.call_args.args[0]
        assert "extrajudiciales" in url_arg
        assert "expedientes_judiciales" not in url_arg


# ---------------------------------------------------------------------------
# create_expediente_rest (mock httpx)
# ---------------------------------------------------------------------------

class TestCreateExpedienteRest:
    """create_expediente_rest llama internamente a _build_rest_payload_extrajudicial,
    que desde 2026-05-11 hace un GET al CRM para obtener max+1. Mockeamos esa
    llamada para aislar el POST del GET interno."""

    @pytest.fixture(autouse=True)
    def _mock_next_num(self):
        with patch(
            "core.sudespacho_create._get_next_num_expediente_extrajudicial",
            return_value=1,
        ):
            yield

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

        # Mockear _get_next_num_expediente_judicial para aislar el POST del GET interno
        with patch("core.sudespacho_create._get_next_num_expediente_judicial", return_value=1):
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

        with patch("core.sudespacho_create._get_next_num_expediente_judicial", return_value=1):
            with patch("core.sudespacho_create.httpx.post", return_value=mock_resp):
                with pytest.raises(SudespachoCreateError):
                    create_expediente_judicial_rest(datos_judicial)


# ---------------------------------------------------------------------------
# create_expediente — estrategia REST-first con fallback
# ---------------------------------------------------------------------------

class TestCreateExpedienteRestFirst:
    """Igual que TestCreateExpedienteRest, aislamos el GET interno del cálculo
    de Numero_Expediente para no hacer red real durante los tests."""

    @pytest.fixture(autouse=True)
    def _mock_next_num(self):
        with patch(
            "core.sudespacho_create._get_next_num_expediente_extrajudicial",
            return_value=1,
        ):
            yield

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

        with patch("core.sudespacho_create._get_next_num_expediente_judicial", return_value=1):
            with patch("core.sudespacho_create.httpx.post", return_value=mock_resp):
                eid = create_expediente_judicial(datos_judicial)

        assert eid == "701"

    def test_fallback_a_legacy_si_rest_falla(self, datos_judicial, monkeypatch):
        monkeypatch.setenv("SUDESPACHO_API_KEY", "test-api-key")

        with patch("core.sudespacho_create._get_next_num_expediente_judicial", return_value=1):
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

