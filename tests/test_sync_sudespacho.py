"""Tests del módulo sync_sudespacho — solo lógica pura, sin red.

Cubre:
- SudespachoConfig.from_env y headers (sin scheme y con scheme).
- Estabilidad de ENDPOINTS y DOC_FIELDS (no romper el contrato del módulo).
- Helpers internos: _extract_url_from_doc, _items, _extract_zip.
- Idempotencia del marcador en pull_expediente cuando ya existe `.sudespacho_pulled`.
- Nuevos métodos REST: list_gdocu_docs_rest, get_presigned_download_url,
  download_document_rest (confirmados 2026-05-04, sin PHPSESSID).
- pull_expediente: vía REST preferente y fallback legacy.
"""

from __future__ import annotations

import io
import json
import zipfile

import pytest

from core import case_manager
from core.sync_sudespacho import (
    DOC_FIELDS,
    ENDPOINTS,
    EXPEDIENTE_DEFAULT_PROPERTIES,
    GdocuDocInfo,
    SudespachoClient,
    SudespachoConfig,
    SudespachoError,
    pull_expediente,
)


# ---- Configuración --------------------------------------------------------

def test_config_from_env_defaults(monkeypatch):
    monkeypatch.setenv("SUDESPACHO_BASE_URL", "https://api-crm-commons-pro.sudespacho.biz")
    monkeypatch.setenv("SUDESPACHO_API_KEY", "fake-key-123")
    monkeypatch.delenv("SUDESPACHO_AUTH_HEADER", raising=False)
    monkeypatch.delenv("SUDESPACHO_AUTH_SCHEME", raising=False)
    monkeypatch.delenv("SUDESPACHO_ELEMENT", raising=False)
    monkeypatch.delenv("SUDESPACHO_TIMEOUT_S", raising=False)

    cfg = SudespachoConfig.from_env()
    assert cfg.base_url == "https://api-crm-commons-pro.sudespacho.biz"
    assert cfg.api_key == "fake-key-123"
    assert cfg.auth_header == "x-api-key"   # confirmado empíricamente
    assert cfg.auth_scheme == ""
    assert cfg.element == "expedientes_judiciales"
    assert cfg.timeout_s == 120


def test_config_headers_sin_scheme():
    """Por defecto la API key va como valor literal del header x-api-key."""
    cfg = SudespachoConfig(base_url="https://x", api_key="abc")
    h = cfg.headers()
    assert h["x-api-key"] == "abc"
    assert "application/json" in h["Accept"]


def test_config_headers_con_scheme_explicito():
    """Si el tenant requiere prefijo (Bearer, Token, etc.) se respeta."""
    cfg = SudespachoConfig(
        base_url="https://x", api_key="abc",
        auth_header="Authorization", auth_scheme="Bearer",
    )
    h = cfg.headers()
    assert h["Authorization"] == "Bearer abc"


def test_config_falla_sin_envvars(monkeypatch):
    monkeypatch.delenv("SUDESPACHO_BASE_URL", raising=False)
    monkeypatch.delenv("SUDESPACHO_API_KEY", raising=False)
    with pytest.raises(SudespachoError):
        SudespachoConfig.from_env()


# ---- Endpoints estables ---------------------------------------------------

def test_endpoints_canonicos():
    assert ENDPOINTS["element_register"] == "/api/element_register/{element}/{id}"
    assert ENDPOINTS["folders"] == "/api/folders/{element}/{parent}"
    assert ENDPOINTS["documents_zip"] == "/api/documents/{id}/zip/files"
    assert ENDPOINTS["online_current"] == "/api/online/current"
    assert ENDPOINTS["presigned_download"] == \
        "/api/documents/presigned_urls/{service}/download/{documentId}"


def test_doc_fields_canonicos():
    assert DOC_FIELDS["filename"] == "nombreoriginal"
    assert DOC_FIELDS["mime"] == "mime"
    assert DOC_FIELDS["size"] == "tamano"
    assert DOC_FIELDS["url"] == "doc"
    assert DOC_FIELDS["related"] == "relatedRegisters"


def test_default_properties_no_vacio():
    assert "id" in EXPEDIENTE_DEFAULT_PROPERTIES
    assert len(EXPEDIENTE_DEFAULT_PROPERTIES) >= 3


# ---- Helpers internos -----------------------------------------------------

def test_extract_url_from_doc_campo_doc():
    payload = {"id": "1", "doc": "https://s3.example.com/abc.zip?sig=xyz"}
    assert SudespachoClient._extract_url_from_doc(payload) == \
        "https://s3.example.com/abc.zip?sig=xyz"


def test_extract_url_from_doc_campo_url():
    payload = {"url": "https://example.com/file"}
    assert SudespachoClient._extract_url_from_doc(payload) == "https://example.com/file"


def test_extract_url_from_doc_no_url():
    assert SudespachoClient._extract_url_from_doc({"id": "1", "doc": "no-es-url"}) is None
    assert SudespachoClient._extract_url_from_doc(None) is None
    assert SudespachoClient._extract_url_from_doc([1, 2]) is None


# ---- Aplanado de metadatos del documento ---------------------------------

def _make_client_no_init() -> SudespachoClient:
    """Crea un SudespachoClient sin abrir conexión real (para tests del aplanador)."""
    inst = SudespachoClient.__new__(SudespachoClient)
    return inst


def test_get_document_metadata_aplana_shape_custom(monkeypatch):
    """El shape custom {id, values:[{property:{name}, value, label?}]} se aplana
    a un dict con claves directas y `_label` cuando existe."""
    client = _make_client_no_init()

    # Mock _get_json para devolver el shape custom de la API real
    def fake_get_json(self, path, **params):
        return {
            "id": "40020",
            "isPrimary": False,
            "values": [
                {
                    "property": {"name": "id_carpeta"},
                    "value": "306",
                    "label": "CIVIL",
                },
                {
                    "property": {"name": "nombreoriginal"},
                    "value": "CEDULA DE EMPLAZAMIENTO.pdf",
                },
                {
                    "property": {"name": "categoria"},
                    "value": "CIVIL",
                },
                {
                    "property": {"name": "tamano"},
                    "value": 2048,
                },
            ],
        }

    monkeypatch.setattr(SudespachoClient, "_get_json", fake_get_json)

    out = client.get_document_metadata("40020")
    assert out["id"] == "40020"
    assert out["id_carpeta"] == "306"
    assert out["id_carpeta_label"] == "CIVIL"
    assert out["nombreoriginal"] == "CEDULA DE EMPLAZAMIENTO.pdf"
    assert out["categoria"] == "CIVIL"
    assert out["tamano"] == 2048


def test_get_document_metadata_shape_plano(monkeypatch):
    """Si la API devuelve un shape plano (sin values), también funciona."""
    client = _make_client_no_init()

    def fake_get_json(self, path, **params):
        return {
            "id": 40020,
            "nombreoriginal": "doc.pdf",
            "id_carpeta": 306,
            "categoria": "CIVIL",
            "tamano": 1024,
        }

    monkeypatch.setattr(SudespachoClient, "_get_json", fake_get_json)

    out = client.get_document_metadata(40020)
    assert out["id"] == "40020"
    assert out["nombreoriginal"] == "doc.pdf"
    assert out["id_carpeta"] == 306
    assert out["categoria"] == "CIVIL"


def test_get_document_metadata_falla_devuelve_minimo(monkeypatch):
    """Si la API responde con error, devuelve dict mínimo {id} para que
    el caller pueda hacer fallback."""
    client = _make_client_no_init()

    def fake_get_json(self, path, **params):
        raise SudespachoError("404 Not Found")

    monkeypatch.setattr(SudespachoClient, "_get_json", fake_get_json)
    out = client.get_document_metadata("99999")
    assert out == {"id": "99999"}


def test_items_listas_y_hydra():
    assert SudespachoClient._items([{"a": 1}, {"b": 2}, "ruido"]) == [{"a": 1}, {"b": 2}]
    assert SudespachoClient._items({"hydra:member": [{"x": 1}]}) == [{"x": 1}]
    assert SudespachoClient._items({"data": [{"x": 1}]}) == [{"x": 1}]
    assert SudespachoClient._items({"otra_clave": [{"x": 1}]}) == []
    assert SudespachoClient._items("foo") == []


# ---- Extracción de zip ----------------------------------------------------

def _make_zip(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


def test_extract_zip_aplana_y_normaliza(tmp_path):
    z = _make_zip({
        "Nota de Encargo.pdf": b"%PDF dummy",
        "subcarpeta/Email Importante.eml": b"From: x",
        "subcarpeta/otra/Factura 001.pdf": b"%PDF dummy",
    })
    SudespachoClient._extract_zip(z, tmp_path)
    files = sorted(p.name for p in tmp_path.iterdir() if p.is_file())
    assert "nota_de_encargo.pdf" in files
    assert "email_importante.eml" in files
    assert "factura_001.pdf" in files


def test_extract_zip_evita_colisiones(tmp_path):
    z = _make_zip({
        "informe.pdf": b"a",
        "INFORME.pdf": b"b",
        "InForMe.pdf": b"c",
    })
    SudespachoClient._extract_zip(z, tmp_path)
    files = sorted(p.name for p in tmp_path.iterdir() if p.is_file())
    assert "informe.pdf" in files
    assert any("informe__" in f for f in files)


def test_extract_zip_invalido_vuelca_y_lanza(tmp_path):
    with pytest.raises(SudespachoError):
        SudespachoClient._extract_zip(b"no es un zip", tmp_path)
    assert (tmp_path / "_descarga_bruta.bin").exists()


# ---- Idempotencia del pull -----------------------------------------------

def test_pull_expediente_marcador_idempotente(tmp_casos_root):
    """Si el marcador .pulled existe en sudespacho_{id}/, pull_expediente
    devuelve sin hacer llamada de red (modo skip)."""
    case_manager.ensure_case("EV-2026-099")
    # Arquitectura multi-expediente: marker en 00_Input/sudespacho_{id}/.pulled
    target_dir = tmp_casos_root / "EV-2026-099" / "00_Input" / "sudespacho_123"
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "doc1.pdf").write_bytes(b"x" * 10)
    (target_dir / ".pulled").write_text(
        '{"doc_ids": ["doc1"], "last_sync": "2026-04-28T00:00:00"}',
        encoding="utf-8",
    )

    # El marcador corta la ejecución antes de cualquier llamada de red.
    result = pull_expediente("EV-2026-099", "123")
    assert result.documents_downloaded == 0
    assert result.documents_total >= 1
    assert any("Ya descargado" in e for e in result.errors)


# ---- Nuevos endpoints REST (confirmados 2026-05-04) -----------------------

def test_endpoints_rest_canonicos():
    """Los dos nuevos endpoints REST deben estar en el dict ENDPOINTS."""
    assert ENDPOINTS["element_registries"] == "/api/element_registries/{element}"
    assert ENDPOINTS["presigned_download_url"] == \
        "/api/files/presigned_download_url/{doc_id}"


# ---- list_gdocu_docs_rest -------------------------------------------------

def _make_client_rest() -> SudespachoClient:
    """SudespachoClient sin conexión real (para tests de parseo)."""
    return SudespachoClient.__new__(SudespachoClient)


_HYDRA_GDOCU_PAYLOAD = {
    "hydra:totalItems": 2,
    "hydra:member": [
        {
            "id": 40054,
            "values": [
                {"property": {"name": "nombrefinal"}, "value": "Demanda.pdf"},
                {"property": {"name": "id_carpeta"}, "value": "306", "label": "CIVIL"},
                {"property": {"name": "mime"},        "value": "application/pdf"},
                {"property": {"name": "tamano"},      "value": 102400},
            ],
        },
        {
            "id": 40055,
            "values": [
                {"property": {"name": "nombrefinal"}, "value": "Cedula_Emplazamiento.pdf"},
                {"property": {"name": "id_carpeta"}, "value": "306", "label": "CIVIL"},
                {"property": {"name": "mime"},        "value": "application/pdf"},
                {"property": {"name": "tamano"},      "value": 51200},
            ],
        },
    ],
}


def test_list_gdocu_docs_rest_parsea_respuesta_hydra(monkeypatch):
    """Parsea correctamente la respuesta hydra:member con el shape de values."""
    client = _make_client_rest()
    call_count = {"n": 0}

    def fake_get_json(self, path, **params):
        call_count["n"] += 1
        # Solo devolvemos resultados en la primera página para evitar bucle
        if params.get("page", 1) == 1:
            return _HYDRA_GDOCU_PAYLOAD
        return {"hydra:totalItems": 2, "hydra:member": []}

    monkeypatch.setattr(SudespachoClient, "_get_json", fake_get_json)
    monkeypatch.setattr(
        SudespachoClient, "cfg",
        SudespachoConfig(base_url="https://x", api_key="k"),
        raising=False,
    )

    docs = client.list_gdocu_docs_rest("648")

    assert len(docs) == 2
    assert call_count["n"] == 1   # una sola página (totalItems == len(member))

    d0 = docs[0]
    assert d0.doc_id == "40054"
    assert d0.filename == "Demanda.pdf"
    assert d0.id_carpeta == "306"
    assert d0.id_carpeta_label == "CIVIL"
    assert d0.mime == "application/pdf"
    assert d0.size == 102400

    d1 = docs[1]
    assert d1.doc_id == "40055"
    assert d1.filename == "Cedula_Emplazamiento.pdf"


def test_list_gdocu_docs_rest_respuesta_vacia(monkeypatch):
    """Respuesta con hydra:member vacío → lista vacía."""
    client = _make_client_rest()

    def fake_get_json(self, path, **params):
        return {"hydra:totalItems": 0, "hydra:member": []}

    monkeypatch.setattr(SudespachoClient, "_get_json", fake_get_json)
    monkeypatch.setattr(
        SudespachoClient, "cfg",
        SudespachoConfig(base_url="https://x", api_key="k"),
        raising=False,
    )

    docs = client.list_gdocu_docs_rest("648")
    assert docs == []


def test_list_gdocu_docs_rest_sin_carpeta_label(monkeypatch):
    """Si id_carpeta no tiene label, id_carpeta_label es None."""
    client = _make_client_rest()

    def fake_get_json(self, path, **params):
        return {
            "hydra:totalItems": 1,
            "hydra:member": [
                {
                    "id": 40060,
                    "values": [
                        {"property": {"name": "nombrefinal"}, "value": "doc.pdf"},
                        {"property": {"name": "id_carpeta"}, "value": "99"},
                        # Sin campo "label"
                    ],
                }
            ],
        }

    monkeypatch.setattr(SudespachoClient, "_get_json", fake_get_json)
    monkeypatch.setattr(
        SudespachoClient, "cfg",
        SudespachoConfig(base_url="https://x", api_key="k"),
        raising=False,
    )

    docs = client.list_gdocu_docs_rest("648")
    assert len(docs) == 1
    assert docs[0].id_carpeta == "99"
    assert docs[0].id_carpeta_label is None


def test_list_gdocu_docs_rest_usa_element_correcto(monkeypatch):
    """El filterGroup[property] debe incluir el element configurado."""
    client = _make_client_rest()
    captured_params = {}

    def fake_get_json(self, path, **params):
        captured_params.update(params)
        return {"hydra:totalItems": 0, "hydra:member": []}

    monkeypatch.setattr(SudespachoClient, "_get_json", fake_get_json)
    monkeypatch.setattr(
        SudespachoClient, "cfg",
        SudespachoConfig(base_url="https://x", api_key="k", element="expedientes_judiciales"),
        raising=False,
    )

    client.list_gdocu_docs_rest("648", element="expedientes_judiciales")
    prop_key = "filterGroup[filterGroups][0][filters][0][property]"
    assert captured_params.get(prop_key) == "left.expedientes_judiciales.id"
    value_key = "filterGroup[filterGroups][0][filters][0][value]"
    assert captured_params.get(value_key) == "648"


# ---- get_presigned_download_url ------------------------------------------

class _FakeHTTPResponse:
    """Simulacro mínimo de httpx.Response para tests."""
    def __init__(self, status_code: int, text: str, content_type: str = "text/plain"):
        self.status_code = status_code
        self.text = text
        self.content = text.encode()
        self.headers = {"content-type": content_type}
        self.request = type("R", (), {"url": "https://fake"})()

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx
            raise httpx.HTTPStatusError(
                "error", request=self.request, response=self
            )

    def json(self):
        import json as _json
        return _json.loads(self.text)


def test_get_presigned_download_url_respuesta_texto(monkeypatch):
    """Si el endpoint devuelve la URL directamente como texto plano."""
    client = _make_client_rest()
    s3_url = "https://api-crm-tmp.s3.eu-west-1.amazonaws.com/uuid/doc.pdf?X-Amz-Expires=600"

    def fake_get(self, path, **params):
        return _FakeHTTPResponse(200, s3_url)

    monkeypatch.setattr(SudespachoClient, "_get", fake_get)
    monkeypatch.setattr(
        SudespachoClient, "cfg",
        SudespachoConfig(base_url="https://x", api_key="k"),
        raising=False,
    )

    url = client.get_presigned_download_url("40054", "648")
    assert url == s3_url


def test_get_presigned_download_url_respuesta_json(monkeypatch):
    """Si el endpoint devuelve JSON {"url": "..."}."""
    client = _make_client_rest()
    s3_url = "https://s3.example.com/file.pdf"

    def fake_get(self, path, **params):
        return _FakeHTTPResponse(200, f'{{"url": "{s3_url}"}}', "application/json")

    monkeypatch.setattr(SudespachoClient, "_get", fake_get)
    monkeypatch.setattr(
        SudespachoClient, "cfg",
        SudespachoConfig(base_url="https://x", api_key="k"),
        raising=False,
    )

    url = client.get_presigned_download_url("40054", "648")
    assert url == s3_url


def test_get_presigned_download_url_json_entrecomillado(monkeypatch):
    """La URL puede venir como string JSON entrecomillado: '"https://..."'."""
    client = _make_client_rest()
    s3_url = "https://s3.example.com/doc.pdf"

    def fake_get(self, path, **params):
        return _FakeHTTPResponse(200, f'"{s3_url}"', "application/json")

    monkeypatch.setattr(SudespachoClient, "_get", fake_get)
    monkeypatch.setattr(
        SudespachoClient, "cfg",
        SudespachoConfig(base_url="https://x", api_key="k"),
        raising=False,
    )

    url = client.get_presigned_download_url("40054", "648")
    assert url == s3_url


def test_get_presigned_download_url_http_error(monkeypatch):
    """Si el servidor devuelve 404, debe lanzar SudespachoError."""
    client = _make_client_rest()

    def fake_get(self, path, **params):
        return _FakeHTTPResponse(404, "Not Found")

    monkeypatch.setattr(SudespachoClient, "_get", fake_get)
    monkeypatch.setattr(
        SudespachoClient, "cfg",
        SudespachoConfig(base_url="https://x", api_key="k"),
        raising=False,
    )

    with pytest.raises(SudespachoError, match="404"):
        client.get_presigned_download_url("40054", "648")


def test_get_presigned_download_url_sin_url_en_json(monkeypatch):
    """Si el JSON no contiene URL reconocible, debe lanzar SudespachoError."""
    client = _make_client_rest()

    def fake_get(self, path, **params):
        return _FakeHTTPResponse(200, '{"status": "ok"}', "application/json")

    monkeypatch.setattr(SudespachoClient, "_get", fake_get)
    monkeypatch.setattr(
        SudespachoClient, "cfg",
        SudespachoConfig(base_url="https://x", api_key="k"),
        raising=False,
    )

    with pytest.raises(SudespachoError):
        client.get_presigned_download_url("40054", "648")


# ---- download_document_rest -----------------------------------------------

def test_download_document_rest_escribe_archivo(tmp_path, monkeypatch):
    """download_document_rest llama a get_presigned_download_url y escribe los bytes."""
    client = _make_client_rest()
    fake_bytes = b"%PDF-1.4 dummy content"
    s3_url = "https://s3.example.com/doc.pdf"

    monkeypatch.setattr(
        SudespachoClient, "get_presigned_download_url",
        lambda self, doc_id, exp_id, **kw: s3_url,
    )
    monkeypatch.setattr(
        SudespachoClient, "_download_url_raw",
        lambda self, url: fake_bytes,
    )
    monkeypatch.setattr(
        SudespachoClient, "cfg",
        SudespachoConfig(base_url="https://x", api_key="k"),
        raising=False,
    )

    dest = tmp_path / "civil" / "demanda.pdf"
    result = client.download_document_rest("40054", "648", dest)

    assert result == dest
    assert dest.exists()
    assert dest.read_bytes() == fake_bytes


def test_download_document_rest_crea_directorios(tmp_path, monkeypatch):
    """Se crean los directorios padre si no existen."""
    client = _make_client_rest()

    monkeypatch.setattr(
        SudespachoClient, "get_presigned_download_url",
        lambda self, doc_id, exp_id, **kw: "https://s3.example.com/f.pdf",
    )
    monkeypatch.setattr(
        SudespachoClient, "_download_url_raw",
        lambda self, url: b"data",
    )
    monkeypatch.setattr(
        SudespachoClient, "cfg",
        SudespachoConfig(base_url="https://x", api_key="k"),
        raising=False,
    )

    dest = tmp_path / "a" / "b" / "c" / "doc.pdf"
    client.download_document_rest("1", "648", dest)
    assert dest.exists()


# ---- pull_expediente — vía REST -------------------------------------------

def test_pull_expediente_usa_rest_cuando_disponible(tmp_casos_root, monkeypatch):
    """pull_expediente descarga via REST si SudespachoClient está disponible.
    El cliente legacy NO debe instanciarse en este caso.
    """
    case_manager.ensure_case("EV-REST-001")
    fake_bytes = b"%PDF REST content"
    s3_url = "https://s3.example.com/demanda.pdf"

    # Simular list_gdocu_docs_rest con un documento
    gdocu_doc = GdocuDocInfo(
        doc_id="40054",
        filename="Demanda.pdf",
        id_carpeta="306",
        id_carpeta_label="civil",
        mime="application/pdf",
        size=len(fake_bytes),
        raw={},
    )
    monkeypatch.setattr(
        SudespachoClient, "list_gdocu_docs_rest",
        lambda self, exp_id, **kw: [gdocu_doc],
    )
    monkeypatch.setattr(
        SudespachoClient, "download_document_rest",
        lambda self, doc_id, exp_id, target_path, **kw: (
            target_path.parent.mkdir(parents=True, exist_ok=True)
            or target_path.write_bytes(fake_bytes)
            or target_path
        ),
    )

    # Asegurarse de que SudespachoClient.__init__ no falla (mockeamos from_env)
    monkeypatch.setattr(
        SudespachoConfig, "from_env",
        classmethod(lambda cls: SudespachoConfig(base_url="https://x", api_key="k")),
    )

    # El cliente legacy NO debe instanciarse
    legacy_called = {"n": 0}

    def fail_if_called(*a, **kw):
        legacy_called["n"] += 1
        raise AssertionError("El cliente legacy no debería instanciarse en la vía REST")

    import core.sync_sudespacho as _mod
    original_client = _mod.SudespachoClient
    try:
        result = pull_expediente("EV-REST-001", "648")
    finally:
        pass

    assert result.documents_downloaded == 1
    assert result.documents_total == 1
    assert not result.errors
    assert "civil" in result.folders_processed

    # Verificar que el archivo se escribió y se renombró correctamente
    target_dir = tmp_casos_root / "EV-REST-001" / "00_Input" / "sudespacho_648"
    assert (target_dir / ".pulled").exists()
    pulled = json.loads((target_dir / ".pulled").read_text())
    assert "40054" in pulled["doc_ids"]


def test_pull_expediente_rest_falla_usa_legacy(tmp_casos_root, monkeypatch):
    """Si list_gdocu_docs_rest lanza SudespachoError, se usa el fallback legacy."""
    from unittest.mock import MagicMock, patch

    case_manager.ensure_case("EV-LEGACY-001")
    fake_bytes = b"legacy content"

    # REST falla
    monkeypatch.setattr(
        SudespachoClient, "list_gdocu_docs_rest",
        lambda self, exp_id, **kw: (_ for _ in ()).throw(
            SudespachoError("REST no disponible")
        ),
    )
    monkeypatch.setattr(
        SudespachoConfig, "from_env",
        classmethod(lambda cls: SudespachoConfig(base_url="https://x", api_key="k")),
    )

    # Mock del cliente legacy
    from core.sync_sudespacho_legacy import (
        LegacyDownloadResult,
        SudespachoLegacyClient,
        SudespachoLegacyConfig,
    )
    from pathlib import Path as _Path

    def fake_legacy_init(self, cfg=None):
        self.cfg = SudespachoLegacyConfig(
            host="tnm.sudespacho.net", phpsessid="x", jwt_token="y"
        )

    def fake_list_doc_ids(self, exp_id, element="expedientes_judiciales"):
        return ["40054"]

    def fake_download_document(self, doc_id, exp_id, target_path, element="expedientes_judiciales"):
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(fake_bytes)
        return LegacyDownloadResult(
            doc_id=str(doc_id),
            target_path=target_path,
            bytes_written=len(fake_bytes),
            filename_in_disposition="Demanda.pdf",
            method="s3",
        )

    monkeypatch.setattr(SudespachoLegacyClient, "__init__", fake_legacy_init)
    monkeypatch.setattr(SudespachoLegacyClient, "list_doc_ids", fake_list_doc_ids)
    monkeypatch.setattr(SudespachoLegacyClient, "download_document", fake_download_document)
    monkeypatch.setattr(SudespachoLegacyClient, "__exit__", lambda self, *a: None)

    result = pull_expediente("EV-LEGACY-001", "648")

    assert result.documents_downloaded == 1
    # El error de REST debe quedar registrado pero no impide la descarga
    assert any("REST" in e for e in result.errors)
