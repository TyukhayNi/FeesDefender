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


def test_burofax_sin_datos_en_el_cuerpo_no_revienta_con_keyerror(tmp_path):
    """Hallazgo de revisión: un `200 + {"estado": "OK"}` sin `datos` hacía que
    `_id_de` propagara un `KeyError` crudo — y para entonces la llamada HTTP ya se
    había hecho: el burofax pudo haber salido y costado 16,97 € sin que quien llama
    se quedara con el `IdEnvio` para reencontrarlo."""
    cliente = FakeCliente({("POST", "/envios/burofax"): (200, {"estado": "OK"})})
    with pytest.raises(codicert.CodicertError) as exc:
        codicert.enviar_burofax(
            FICHA, destinatario={"nombre": "X", "pais": "España"},
            adjuntos=[codicert.adjunto(_pdf(tmp_path))],
            asunto="A", cuerpo="C", id_personalizado="W-1 - REQ", entorno="sandbox",
            cliente=cliente)
    mensaje = str(exc.value).lower()
    assert "pudo" in mensaje and "salido" in mensaje, mensaje
    assert "portal" in mensaje, mensaje
    assert "reintent" in mensaje, mensaje


def test_burofax_con_datos_sin_id_no_revienta_con_keyerror(tmp_path):
    """Misma variante del hallazgo: `datos` presente pero vacío, sin `id`."""
    cliente = FakeCliente({("POST", "/envios/burofax"): (200, {"estado": "OK", "datos": {}})})
    with pytest.raises(codicert.CodicertError) as exc:
        codicert.enviar_burofax(
            FICHA, destinatario={"nombre": "X", "pais": "España"},
            adjuntos=[codicert.adjunto(_pdf(tmp_path))],
            asunto="A", cuerpo="C", id_personalizado="W-1 - REQ", entorno="sandbox",
            cliente=cliente)
    mensaje = str(exc.value).lower()
    assert "pudo" in mensaje and "salido" in mensaje, mensaje
    assert "portal" in mensaje, mensaje
    assert "reintent" in mensaje, mensaje


def test_burofax_con_entorno_desconocido_levanta_codicert_error_sin_tocar_la_red(tmp_path):
    """Hallazgo de revisión: `enviar_burofax` indexaba `BASES[entorno]` sin
    comprobar y reventaba con `KeyError` ante un entorno inventado. La comprobación
    debe llegar antes de tocar la red: el doble no tiene guion, así que una llamada
    a `request()` también haría fallar el test (con otra excepción)."""
    cliente = FakeCliente({})
    with pytest.raises(codicert.CodicertError):
        codicert.enviar_burofax(
            FICHA, destinatario={"nombre": "X", "pais": "España"},
            adjuntos=[codicert.adjunto(_pdf(tmp_path))],
            asunto="A", cuerpo="C", id_personalizado="W-1 - REQ", entorno="preproduccion",
            cliente=cliente)
    assert cliente.llamadas == []


def test_eec_con_entorno_desconocido_levanta_codicert_error_sin_tocar_la_red(tmp_path):
    """Mismo hallazgo en `enviar_eec`. La comprobación del entorno va también antes
    de resolver el cliente, igual que la de `tipo_entrega` ya iba antes de la red."""
    cliente = FakeCliente({})
    with pytest.raises(codicert.CodicertError):
        codicert.enviar_eec(
            FICHA, destinatarios=[{"correo": "a@b.c"}],
            adjuntos=[codicert.adjunto(_pdf(tmp_path))],
            asunto="A", cuerpo="C", tipo_entrega="sms", id_personalizado="W-1 - OVC",
            entorno="preproduccion", cliente=cliente)
    assert cliente.llamadas == []


# ---------------------------------------------------------------------------------
# H-11 (revisión adversarial r2): dos de los seis caminos del hallazgo viven en
# `enviar_burofax` -- el peor de los tres pares, porque es un POST que puede costar
# dinero: el mensaje del fallo de transporte debe conservar el carácter incierto
# del envío, igual que ya hace `_id_de` para el sobre sin `datos.id`.
# ---------------------------------------------------------------------------------

class _ClienteFalloTransporte:
    """Cliente ad hoc cuyo `request()` levanta un fallo de transporte -- como un
    timeout real (`httpx.ReadTimeout` y semejantes) antes de que exista respuesta.

    `TimeoutError` (builtin) y no `httpx.ReadTimeout`: este fichero cae bajo el
    censo de `test_guard_codicert_sin_red.py`, que prohíbe importar `httpx` aquí.
    """

    def request(self, metodo, url, **kw):
        raise TimeoutError("tiempo de espera agotado")


def test_burofax_con_fallo_de_transporte_no_propaga_el_tipo_crudo(tmp_path):
    """Hallazgo de revisión H-11: un cliente que levanta una excepción de
    transporte la propagaba con su tipo crudo. Con un POST que puede costar
    dinero, el mensaje debe avisar de que la comunicación PUDO HABER SALIDO antes
    de mandar a comprobar el portal -- no cabe reintentar a ciegas."""
    with pytest.raises(codicert.CodicertError) as exc:
        codicert.enviar_burofax(
            FICHA, destinatario={"nombre": "X", "pais": "España"},
            adjuntos=[codicert.adjunto(_pdf(tmp_path))],
            asunto="A", cuerpo="C", id_personalizado="W-1 - REQ", entorno="sandbox",
            cliente=_ClienteFalloTransporte())
    mensaje = str(exc.value).lower()
    assert "pudo" in mensaje and "salido" in mensaje, mensaje
    assert "portal" in mensaje, mensaje


def test_burofax_con_json_lista_no_revienta_con_attributeerror(tmp_path):
    """Hallazgo de revisión H-11: un cuerpo JSON `[]` (una lista, no un objeto)
    hacía que `cuerpo.get("estado")` reventara con `AttributeError` crudo --
    las listas no tienen `.get`."""
    cliente = FakeCliente({("POST", "/envios/burofax"): (200, [])})
    with pytest.raises(codicert.CodicertError):
        codicert.enviar_burofax(
            FICHA, destinatario={"nombre": "X", "pais": "España"},
            adjuntos=[codicert.adjunto(_pdf(tmp_path))],
            asunto="A", cuerpo="C", id_personalizado="W-1 - REQ", entorno="sandbox",
            cliente=cliente)
