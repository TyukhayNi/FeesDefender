"""Los dos endpoints de envío y la cabecera que el contrato exige."""
from __future__ import annotations

import base64
import datetime as dt

import pytest

from core import codicert
from tests._dobles.fake_codicert import FakeCliente

FICHA = codicert.Ficha(token="t" * 64, vence=dt.datetime.max.replace(tzinfo=dt.timezone.utc))


def _pdf(tmp_path, nombre="A.pdf", datos=b"%PDF-1.4 falso"):
    f = tmp_path / nombre
    f.write_bytes(datos)
    return f


def test_adjunto_codifica_en_base64_y_declara_pdf(tmp_path):
    a = codicert.adjunto(_pdf(tmp_path))
    assert a["nombre"] == "A.pdf"
    assert a["mime"] == "application/pdf"
    assert base64.b64decode(a["datos"]) == b"%PDF-1.4 falso"


def test_burofax_manda_la_cabecera_x_json_ficheros(tmp_path):
    cliente = FakeCliente({("POST", "/envios/burofax"): (200, {"estado": "OK", "datos": {"id": "006x"}})})
    codicert.enviar_burofax(
        FICHA, destinatario={"nombre": "X", "pais": "España"}, adjuntos=[codicert.adjunto(_pdf(tmp_path))],
        asunto="A", cuerpo="C", id_personalizado="W-1 - REQ", entorno="sandbox", cliente=cliente)
    _, _, kw = cliente.llamadas[0]
    assert kw["headers"]["x-json-ficheros"] == "1"
    assert kw["headers"]["Authorization"] == f"Bearer {FICHA.token}"


def test_burofax_devuelve_el_id_de_envio(tmp_path):
    cliente = FakeCliente({("POST", "/envios/burofax"): (200, {"estado": "OK", "datos": {"id": "006ar9bel3n"}})})
    assert codicert.enviar_burofax(
        FICHA, destinatario={"nombre": "X", "pais": "España"}, adjuntos=[codicert.adjunto(_pdf(tmp_path))],
        asunto="A", cuerpo="C", id_personalizado="W-1 - REQ", entorno="sandbox",
        cliente=cliente) == "006ar9bel3n"


def test_el_422_llega_desglosado_campo_a_campo(tmp_path):
    cliente = FakeCliente({("POST", "/envios/burofax"): (422, {
        "estado": "KO", "mensaje": "Revise los datos e intente nuevamente",
        "datos": {"asunto": "El campo asunto es obligatorio"}})})
    with pytest.raises(codicert.CodicertDatosInvalidosError) as exc:
        codicert.enviar_burofax(
            FICHA, destinatario={"nombre": "X"}, adjuntos=[codicert.adjunto(_pdf(tmp_path))],
            asunto="", cuerpo="C", id_personalizado="W-1 - REQ", entorno="sandbox", cliente=cliente)
    assert exc.value.campos == {"asunto": "El campo asunto es obligatorio"}


def test_eec_lleva_el_tipo_de_entrega_pedido(tmp_path):
    cliente = FakeCliente({("POST", "/envios/entrega-electronica-certificada"):
                           (200, {"estado": "OK", "datos": {"id": "046x"}})})
    codicert.enviar_eec(
        FICHA, destinatarios=[{"correo": "a@b.c"}], adjuntos=[codicert.adjunto(_pdf(tmp_path))],
        asunto="A", cuerpo="<p>C</p>", tipo_entrega="sms", id_personalizado="W-1 - OVC",
        entorno="sandbox", cliente=cliente)
    assert cliente.llamadas[0][2]["json"]["tipo_entrega"] == "sms"


def test_eec_rechaza_un_tipo_de_entrega_inventado(tmp_path):
    with pytest.raises(codicert.CodicertError):
        codicert.enviar_eec(
            FICHA, destinatarios=[{"correo": "a@b.c"}], adjuntos=[], asunto="A", cuerpo="C",
            tipo_entrega="paloma", id_personalizado="W-1 - OVC", entorno="sandbox",
            cliente=FakeCliente({}))
