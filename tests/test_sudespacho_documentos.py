"""Subida al gestor documental del CRM: los tres pasos del §17.1, verificados."""
from __future__ import annotations

import hashlib

import pytest

from core import sudespacho_documentos as doc


class _Resp:
    def __init__(self, status, cuerpo=None, content=b""):
        self.status_code, self._json, self.content = status, cuerpo, content

    def json(self):
        if self._json is None:
            raise ValueError("no es JSON")
        return self._json


class FakeHTTP:
    """Doble del cliente HTTP. Mapea (metodo, sufijo) -> (status, json, content)."""

    def __init__(self, guion):
        self.guion, self.llamadas = guion, []

    def request(self, metodo, url, **kw):
        self.llamadas.append((metodo, url, kw))
        for (m, sufijo), r in self.guion.items():
            if m == metodo and url.endswith(sufijo):
                return _Resp(*r)
        raise AssertionError(f"sin guion para {metodo} {url}")


BYTES = b"%PDF-1.4 contenido"
SHA = hashlib.sha256(BYTES).hexdigest()


def _guion_feliz(content=BYTES):
    return {
        ("GET", "/api/files/presigned_upload_url"):
            (200, {"action": "upload", "fileIdentifier": "uuid-1",
                   "url": "https://s3.example/subir"}),
        ("PUT", "/subir"): (200, None),
        ("POST", "/api/documents"): (201, {"message": "Resource has been created",
                                           "id": "42990"}),
        ("GET", "/api/documents/42990/downloadUri"):
            (200, {"presignedDownloadUrl": "https://s3.example/bajar"}),
        ("GET", "/bajar"): (200, None, content),
    }


def test_los_tres_pasos_en_orden_y_con_el_contrato_del_17_1(monkeypatch):
    monkeypatch.setenv("SUDESPACHO_API_KEY", "clave-de-prueba")
    http = FakeHTTP(_guion_feliz())
    r = doc.subir_documento(BYTES, nombrefinal="CERT - W-1-006a.pdf",
                            mime="application/pdf",
                            related="extrajudiciales:123:left", cliente=http)
    assert r.doc_id == "42990" and r.origen_id == "uuid-1" and r.sha256 == SHA
    metodos = [m for m, _, _ in http.llamadas]
    assert metodos[:3] == ["GET", "PUT", "POST"]
    cuerpo = http.llamadas[2][2]["json"]
    assert cuerpo["origen"] == "fuploaders3"
    assert cuerpo["origen_id"] == "uuid-1"           # NO "fileIdentifier" (§17.1)
    assert "fileIdentifier" not in cuerpo
    assert cuerpo["tamano"] == len(BYTES)
    assert isinstance(cuerpo["id_carpeta"], int)      # int, no string (§17.1)
    assert cuerpo["relatedRegisters"] == ["extrajudiciales:123:left"]


def test_el_PUT_a_S3_va_SIN_la_clave_del_CRM(monkeypatch):
    monkeypatch.setenv("SUDESPACHO_API_KEY", "clave-de-prueba")
    http = FakeHTTP(_guion_feliz())
    doc.subir_documento(BYTES, nombrefinal="x.pdf", mime="application/pdf",
                        related="extrajudiciales:123:left", cliente=http)
    _, _, kw_put = http.llamadas[1]
    assert "x-api-key" not in {k.lower() for k in (kw_put.get("headers") or {})}


def test_el_201_NO_acredita_nada_si_los_bytes_vuelven_distintos(monkeypatch):
    """§17.1: «que el POST devuelva 201 no acredita que el binario esté bien»."""
    monkeypatch.setenv("SUDESPACHO_API_KEY", "clave-de-prueba")
    http = FakeHTTP(_guion_feliz(content=b"%PDF-1.4 OTRA COSA"))
    with pytest.raises(doc.SudespachoDocumentosError, match="sha256|no coinciden"):
        doc.subir_documento(BYTES, nombrefinal="x.pdf", mime="application/pdf",
                            related="extrajudiciales:123:left", cliente=http)


def test_NUNCA_usa_el_endpoint_multiple(monkeypatch):
    """§17.2: `POST /api/documents/multiple` devuelve 201 y no crea nada."""
    monkeypatch.setenv("SUDESPACHO_API_KEY", "clave-de-prueba")
    http = FakeHTTP(_guion_feliz())
    doc.subir_documento(BYTES, nombrefinal="x.pdf", mime="application/pdf",
                        related="extrajudiciales:123:left", cliente=http)
    assert not any(url.endswith("/documents/multiple") for _, url, _ in http.llamadas)


def test_el_origen_id_se_entrega_al_gancho_ANTES_del_POST(monkeypatch):
    """Sin esto, un timeout en el paso 3 deja un documento irrecuperable.

    El `origen_id` es lo único que permite reencontrar por clave de contenido lo
    que quedó creado (§17.4). Anotarlo DESPUÉS del POST no sirve de nada: el caso
    que hay que cubrir es justamente que el POST no devuelva.
    """
    monkeypatch.setenv("SUDESPACHO_API_KEY", "clave-de-prueba")
    orden = []
    http = FakeHTTP(_guion_feliz())
    original = http.request

    def espia(metodo, url, **kw):
        if url.endswith("/api/documents"):
            orden.append("POST")
        return original(metodo, url, **kw)

    http.request = espia
    doc.subir_documento(BYTES, nombrefinal="x.pdf", mime="application/pdf",
                        related="extrajudiciales:123:left", cliente=http,
                        al_reservar=lambda oid: orden.append(f"reservado:{oid}"))
    assert orden == ["reservado:uuid-1", "POST"]


def test_sin_api_key_no_se_intenta_nada(monkeypatch):
    monkeypatch.delenv("SUDESPACHO_API_KEY", raising=False)
    http = FakeHTTP({})
    with pytest.raises(doc.SudespachoDocumentosError, match="SUDESPACHO_API_KEY"):
        doc.subir_documento(BYTES, nombrefinal="x.pdf", mime="application/pdf",
                            related="extrajudiciales:123:left", cliente=http)
    assert http.llamadas == []


def test_un_POST_sin_id_avisa_de_que_el_documento_PUDO_QUEDAR_CREADO(monkeypatch):
    """No se relanza a ciegas: así se duplica (§17.4)."""
    monkeypatch.setenv("SUDESPACHO_API_KEY", "clave-de-prueba")
    guion = _guion_feliz()
    guion[("POST", "/api/documents")] = (201, {"message": "ok"})
    with pytest.raises(doc.SudespachoDocumentosError, match="PUDO HABER QUEDADO"):
        doc.subir_documento(BYTES, nombrefinal="x.pdf", mime="application/pdf",
                            related="extrajudiciales:123:left",
                            cliente=FakeHTTP(guion))


def test_buscar_por_origen_id_usa_related_register_y_NO_el_listado(monkeypatch):
    """§17.4: `related_register` es inmediato; el listado filtrado tiene latencia."""
    monkeypatch.setenv("SUDESPACHO_API_KEY", "clave-de-prueba")
    http = FakeHTTP({
        ("GET", "/api/related_register/extrajudiciales/123"):
            (200, {"gdocu": [{"id": "42990"}, {"id": "42991"}]}),
        ("GET", "/api/element_register/gdocu/42990"):
            (200, [{"property": {"name": "origen_id"}, "value": "otro-uuid"}]),
        ("GET", "/api/element_register/gdocu/42991"):
            (200, [{"property": {"name": "origen_id"}, "value": "uuid-1"}]),
    })
    assert doc.buscar_por_origen_id("uuid-1", element="extrajudiciales",
                                    exp_id="123", cliente=http) == "42991"
    assert not any("element_registries" in url for _, url, _ in http.llamadas)


def test_buscar_por_origen_id_acepta_las_DOS_formas_de_la_relectura(monkeypatch):
    """§17.4-bis: `element_register/gdocu/{id}` devuelve una LISTA, y el de
    expediente un `Register` con `values.hydra:member`. Un parser único revienta."""
    monkeypatch.setenv("SUDESPACHO_API_KEY", "clave-de-prueba")
    http = FakeHTTP({
        ("GET", "/api/related_register/extrajudiciales/123"):
            (200, {"gdocu": [{"id": "42990"}]}),
        ("GET", "/api/element_register/gdocu/42990"):
            (200, {"values": {"hydra:member": [
                {"property": {"name": "origen_id"}, "value": "uuid-1"}]}}),
    })
    assert doc.buscar_por_origen_id("uuid-1", element="extrajudiciales",
                                    exp_id="123", cliente=http) == "42990"


def test_buscar_devuelve_None_cuando_no_esta(monkeypatch):
    monkeypatch.setenv("SUDESPACHO_API_KEY", "clave-de-prueba")
    http = FakeHTTP({("GET", "/api/related_register/extrajudiciales/123"):
                     (200, {"gdocu": []})})
    assert doc.buscar_por_origen_id("uuid-1", element="extrajudiciales",
                                    exp_id="123", cliente=http) is None


def test_un_fallo_de_transporte_sale_con_el_tipo_del_modulo(monkeypatch):
    """El contrato: no se escapa el tipo crudo de la librería de red."""
    monkeypatch.setenv("SUDESPACHO_API_KEY", "clave-de-prueba")

    class Caido:
        def request(self, metodo, url, **kw):
            raise TimeoutError("la red")

    with pytest.raises(doc.SudespachoDocumentosError, match="transporte"):
        doc.subir_documento(BYTES, nombrefinal="x.pdf", mime="application/pdf",
                            related="extrajudiciales:123:left", cliente=Caido())
