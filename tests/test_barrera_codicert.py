"""La barrera de ejecución de Codicert (`tests/_barrera_codicert.py`) es COMPROBABLE.

Hallazgo H-13 (alto, acotado; revisión adversarial r2): `test_guard_codicert_sin_red.py`
es un barrido de TEXTO -- busca, en los ficheros de test, la llamada al transporte real, la
importación de `httpx` y la base de producción -- y no ve la forma ordinaria de llegar a la
red: llamar a la API pública SIN inyectar `cliente=`. Un test que escriba
`codicert.acceso('usuario-falso', 'clave-falsa', entorno='sandbox')` no escribe ninguna de
esas tres cosas y aun así alcanzaría la puerta real. El revisor lo demostró sustituyendo el
transporte real por una excepción centinela; estos tests son esa misma comprobación, hecha
permanente.

Lo que fijan, y por qué cada uno existe:

1. **EL CONTROL QUE ACREDITA EL ARREGLO.** Llamar a la API pública sin `cliente=` se
   bloquea ANTES de abrir ninguna conexión. Si este test pasara SIN la barrera instalada,
   el arreglo no valdría -- por eso `test_barrera_frontal_esta_realmente_instalada` (abajo)
   comprueba que, en efecto, está activa por defecto.
2. **Las cuatro puertas, no solo una.** `acceso`, `enviar_burofax`, `enviar_eec` y las
   lecturas que pasan por `_get` (`credito`, entre ellas) resuelven el transporte por el
   mismo camino: si alguna quedara sin cubrir, sería la MISMA vía que abrió H-13.
3. **Control positivo.** Un doble SÍ inyectado tiene que seguir funcionando -- sin este
   test, una barrera que bloqueara TODO, doble incluido, parecería estar funcionando.
4. **Está puesta por defecto**, sin que cada test tenga que acordarse de instalarla: la
   fixture `autouse` de `conftest.py` ya la activó antes de que estos tests arrancaran, y
   eso es justo lo que hace que sea una barrera y no una utilidad opt-in.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from core import codicert
from tests._barrera_codicert import BarreraCodicertViolada
from tests._dobles.fake_codicert import FakeCliente


def _ficha_falsa() -> codicert.Ficha:
    return codicert.Ficha(token="t" * 10, vence=datetime(2099, 1, 1, tzinfo=timezone.utc))


# ---------------------------------------------------------------------------------
# 1. El control que acredita el arreglo
# ---------------------------------------------------------------------------------

def test_llamar_sin_cliente_se_bloquea_antes_de_abrir_conexion():
    """Sin `cliente=`, `acceso` cae en el mismo `or` que las otras tres funciones
    públicas del módulo -- y con eso, en la puerta que esta barrera cierra."""
    with pytest.raises(BarreraCodicertViolada):
        codicert.acceso("usuario-falso", "clave-falsa", entorno="sandbox")


# ---------------------------------------------------------------------------------
# 2. Las cuatro puertas
# ---------------------------------------------------------------------------------

def test_enviar_burofax_sin_cliente_tambien_se_bloquea():
    with pytest.raises(BarreraCodicertViolada):
        codicert.enviar_burofax(
            _ficha_falsa(), destinatario={}, adjuntos=[], asunto="a", cuerpo="c",
            id_personalizado="W-1 - REQ", entorno="sandbox")


def test_enviar_eec_sin_cliente_tambien_se_bloquea():
    with pytest.raises(BarreraCodicertViolada):
        codicert.enviar_eec(
            _ficha_falsa(), destinatarios=[], adjuntos=[], asunto="a", cuerpo="c",
            tipo_entrega="correo", id_personalizado="W-1 - REQ", entorno="sandbox")


def test_una_lectura_por_get_sin_cliente_tambien_se_bloquea():
    """`credito` es una de las cinco lecturas que pasan por `_get`; basta una para
    probar que la puerta común también está cubierta."""
    with pytest.raises(BarreraCodicertViolada):
        codicert.credito(_ficha_falsa(), entorno="sandbox")


# ---------------------------------------------------------------------------------
# 3. Control positivo
# ---------------------------------------------------------------------------------

def test_un_cliente_inyectado_SI_pasa():
    """Sin este control, una barrera que bloqueara TODO -- también un doble
    inyectado -- parecería estar funcionando."""
    cliente = FakeCliente({("POST", "/usuarios/acceso"): (200, {
        "estado": "OK",
        "datos": {"ficha": "a" * 64, "fecha_vencimiento": "2099-01-01T00:00:00+00:00"},
    })})
    ficha = codicert.acceso("u", "c", entorno="sandbox", cliente=cliente)
    assert ficha.token == "a" * 64


# ---------------------------------------------------------------------------------
# 4. Instalada por defecto
# ---------------------------------------------------------------------------------

def test_barrera_frontal_esta_realmente_instalada():
    """El `_cliente_real` que ve el módulo YA NO es el original: lo sustituyó la
    fixture `autouse` de `conftest.py` antes de que este test arrancara. Sin esto,
    `test_llamar_sin_cliente_se_bloquea_antes_de_abrir_conexion` podría estar en
    verde por una razón completamente distinta (una excepción de red real, por
    ejemplo) en vez de por la barrera."""
    from tests import _barrera_codicert

    assert codicert._cliente_real is _barrera_codicert._sustituto_vetado
