"""Tests del módulo sync_sudespacho — solo lógica pura, sin red.

Cubre:
- SudespachoConfig.from_env y headers (sin scheme y con scheme).
- Estabilidad de ENDPOINTS y DOC_FIELDS (no romper el contrato del módulo).
- Helpers internos: _extract_url_from_doc, _items, _extract_zip.
- Idempotencia del marcador en pull_expediente cuando ya existe `.sudespacho_pulled`.
"""

from __future__ import annotations

import io
import zipfile

import pytest

from core import case_manager
from core.sync_sudespacho import (
    DOC_FIELDS,
    ENDPOINTS,
    EXPEDIENTE_DEFAULT_PROPERTIES,
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
