"""La ficha de acceso: se pide una vez, se conserva con su vencimiento."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from core import codicert
from tests._dobles.fake_codicert import FakeCliente


def test_acceso_devuelve_ficha_y_vencimiento():
    cliente = FakeCliente({("POST", "/usuarios/acceso"): (200, {
        "estado": "OK",
        "datos": {"ficha": "a" * 64, "fecha_vencimiento": "2026-09-18T10:30:31+02:00"},
    })})
    ficha = codicert.acceso("u", "c", entorno="sandbox", cliente=cliente)
    assert ficha.token == "a" * 64
    assert ficha.vence == datetime(2026, 9, 18, 10, 30, 31, tzinfo=timezone(timedelta(hours=2)))


def test_acceso_con_credenciales_malas_levanta_auth_error():
    cliente = FakeCliente({("POST", "/usuarios/acceso"): (400, {
        "estado": "KO", "mensaje": "No se pudo iniciar la sesión, compruebe su usuario y contraseña",
        "datos": [],
    })})
    with pytest.raises(codicert.CodicertAuthError):
        codicert.acceso("u", "mala", entorno="sandbox", cliente=cliente)


def test_la_clave_NUNCA_aparece_en_el_error():
    cliente = FakeCliente({("POST", "/usuarios/acceso"): (400, {"estado": "KO", "mensaje": "no"})})
    with pytest.raises(codicert.CodicertAuthError) as exc:
        codicert.acceso("u", "SECRETO-QUE-NO-DEBE-SALIR", entorno="sandbox", cliente=cliente)
    assert "SECRETO-QUE-NO-DEBE-SALIR" not in str(exc.value)


def test_caducada_es_true_cuando_el_reloj_pasa_el_vencimiento():
    ficha = codicert.Ficha(token="x", vence=datetime(2026, 9, 18, 10, 0, tzinfo=timezone.utc))
    assert ficha.caducada(ahora=datetime(2026, 9, 18, 10, 1, tzinfo=timezone.utc)) is True
    assert ficha.caducada(ahora=datetime(2026, 9, 18, 9, 59, tzinfo=timezone.utc)) is False


def test_el_acceso_va_a_la_base_del_entorno_pedido():
    cliente = FakeCliente({("POST", "/usuarios/acceso"): (200, {
        "estado": "OK", "datos": {"ficha": "t", "fecha_vencimiento": "2026-09-18T10:00:00+02:00"}})})
    codicert.acceso("u", "c", entorno="produccion", cliente=cliente)
    assert cliente.llamadas[0][1].startswith("https://ws.codicert.io/v2")


class _RespuestaCuerpoCorrupto:
    """Respuesta ad hoc cuyo `.json()` explota, como un cuerpo corrupto de verdad.

    El doble compartido (`FakeCliente`/`_Respuesta`) devuelve JSON ya construido y
    no puede fallar al parsear, así que este caso necesita su propia respuesta
    mínima en vez de tocar el doble compartido.
    """

    status_code = 502  # NO 500: el blindaje que se corrige solo cubría ese estado

    def json(self):
        raise json.JSONDecodeError("cuerpo corrupto", "", 0)


class _ClienteCuerpoCorrupto:
    """Cliente ad hoc que siempre responde con `_RespuestaCuerpoCorrupto`."""

    def request(self, metodo, url, **kw):
        return _RespuestaCuerpoCorrupto()


def test_acceso_con_cuerpo_no_json_en_un_502_no_propaga_json_decode_error():
    """Hallazgo de revisión: `r.json() if r.status_code != 500 else {}` solo blindaba
    el 500. Un 502 de un proxy —o un cuerpo corrupto con cualquier otro estado— debe
    seguir levantando `CodicertAuthError`, nunca el `JSONDecodeError` crudo de
    `r.json()`: el contrato del módulo es fallar solo con `CodicertError`/
    `CodicertAuthError`."""
    with pytest.raises(codicert.CodicertAuthError):
        codicert.acceso("u", "c", entorno="sandbox", cliente=_ClienteCuerpoCorrupto())


def test_acceso_con_entorno_desconocido_levanta_codicert_error():
    """`credenciales()` ya valida `entorno not in BASES` con `CodicertError`;
    `acceso()` indexaba `BASES[entorno]` directo y daba un `KeyError` crudo.
    Consistencia con la convención ya establecida."""
    with pytest.raises(codicert.CodicertError):
        codicert.acceso("u", "c", entorno="preproduccion", cliente=FakeCliente({}))
