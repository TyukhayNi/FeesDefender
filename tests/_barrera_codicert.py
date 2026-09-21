"""Barrera de EJECUCIÓN de Codicert: ningún test abre la conexión real, olvide o no `cliente=`.

Hallazgo H-13 (alto, acotado; revisión adversarial r2) sobre
`tests/test_guard_codicert_sin_red.py`: ese guard es un barrido de TEXTO -- busca, en los
ficheros de test, la cadena que invoca a `_cliente_real`, la importación de `httpx` y la base
de producción -- y por construcción **no puede ver la forma ordinaria de llegar a la red**:
llamar a la API pública sin inyectar `cliente=`. `core/codicert.py` resuelve ese parámetro con
`cliente or` una llamada a `_cliente_real` -- sin argumentos -- en `acceso`, `enviar_burofax`,
`enviar_eec` y `_get`; un test que escriba `codicert.acceso('u', 'c', entorno='sandbox')` sin
`cliente=` no escribe esa llamada, no importa `httpx` y no nombra la base de producción -- los
cuatro checks del guard pasan en verde -- y sin embargo la llamada alcanza la función real, que
sí importa `httpx` y sí abre la conexión. El revisor lo demostró sustituyendo esa función por
una excepción centinela.

**Nota para quien lea o edite este fichero:** deliberadamente NO se escribe aquí, en ningún
sitio, el nombre de esa función seguido de paréntesis (ni pegado ni con espacio de por medio):
`test_guard_codicert_sin_red.py::test_ningun_test_llama_al_cliente_real` vigila justo esa
grafía en TODO fichero de este ámbito, y este fichero -- por nombrar "codicert" -- cae bajo su
censo. Escribirla aquí sería un FALSO POSITIVO de ese guard (esta prosa no llama a nada), y la
propia razón de ser de esta barrera es no depender de un barrido de texto: sustituir el nombre
por una descripción no la debilita.

## Por qué un barrido de texto no es una barrera

Un barrido de texto comprueba el FICHERO DE TEST, nunca la EJECUCIÓN: puede correr al final
de la suite y decir "ningún test *escribió* tal cosa", pero no puede impedir que una llamada
que sí ocurrió, en un test que no escribió nada sospechoso, abra la conexión. Para eso hace
falta interceptar el propio PUNTO DE EJECUCIÓN -- la función que de verdad toca la red --
ANTES de que cualquier test pueda llamarla, no examinar el texto de los tests después.

## El patrón, tomado de `tests/_barrera.py` (Fase 0, rclone/Drive)

Esa barrera sustituye el *binding del módulo* (`repository_cli.subprocess`) por un proxy que
lanza antes de crear un proceso real, instalado por una fixture `autouse` de scope FUNCIÓN en
`conftest.py` -- antes de la colección no hay fixture que valga, así que tiene que ser previo
a cada test, no a la sesión. Aquí el punto de ejecución es distinto (una función, no un
módulo entero) pero la forma es la misma: sustituir el *binding* real por uno que lanza, con
una fixture `autouse` de función.

`core/codicert.py` ya declara la superficie mínima: la función que esta barrera sustituye es
la ÚNICA que importa `httpx` en todo el módulo (guardado por
`test_guard_codicert_sin_red.py::test_solo_hay_una_puerta_de_red_en_el_modulo`). Sustituir su
binding en `core.codicert` por uno que lanza cierra el paso ANTES de que el `import httpx`
original llegue a ejecutarse -- la función sustituta ni siquiera lo intenta -- así que la
barrera protege independientemente de por qué camino se llegó hasta ahí: con `cliente=`
olvidado, con un doble mal construido, o con cualquier vía futura que añada una llamada
pública nueva a este módulo y también resuelva su transporte con el mismo `or`.

## Qué NO hace esta barrera

No sustituye a `test_guard_codicert_sin_red.py`: ese guard sigue vigilando que nadie escriba
`import httpx` fuera de esta única función, ni la nombre a mano. Los dos son complementarios
-- uno vigila el TEXTO que se escribe, el otro impide la EJECUCIÓN que ese texto pudiera
autorizar por descuido -- y el hallazgo H-13 es precisamente que el primero, solo, deja un
hueco que el segundo cierra.
"""
from __future__ import annotations

from typing import Any

#: El nombre del atributo que esta barrera sustituye en `core.codicert`. Se guarda como dato
#: -- nunca escrito como llamada en este fichero -- para que `instalar` y los mensajes de
#: error compartan la misma cadena sin que aparezca la grafía que vigila el guard de texto.
_ATRIBUTO_SUSTITUIDO = "_cliente_real"


def _sustituto_vetado() -> Any:
    """Ocupa el lugar del transporte real mientras la barrera está instalada.

    No llama a la función original ni importa `httpx`: lanza antes de que exista ninguna
    posibilidad de abrir una conexión. Cualquier llamador de `acceso`/`enviar_burofax`/
    `enviar_eec`/`_get` (los cuatro sitios que resuelven su transporte con `cliente or` una
    llamada a este atributo) que no haya inyectado su propio `cliente=` cae aquí.
    """
    raise BarreraCodicertViolada(
        f"la suite no puede abrir una conexión real a Codicert. Esta llamada no inyectó "
        f"`cliente=`, así que `core.codicert` intentó resolver su transporte por defecto "
        f"(`{_ATRIBUTO_SUSTITUIDO}`, la ÚNICA puerta de red del módulo -- ver su docstring) "
        "y esta barrera la ha bloqueado ANTES de que `httpx` se importara siquiera. Inyecta "
        "un doble (`tests/_dobles/fake_codicert.py::FakeCliente`, o uno propio) con "
        "`cliente=` en la llamada."
    )


class BarreraCodicertViolada(AssertionError):
    """Un test intentó alcanzar la red real de Codicert sin inyectar un doble.

    Hereda de `AssertionError` a propósito, igual que `tests/_barrera.py::BarreraViolada`:
    es un fallo del TEST (olvidó `cliente=`), no del código bajo prueba, y así ningún
    `except Exception` de `core/codicert.py` se lo traga por accidente -- `CodicertError` y
    sus subclases son `RuntimeError`, nunca `AssertionError`.
    """


def instalar(monkeypatch) -> None:
    """Instala la barrera para un test. La llama la fixture `autouse` de `conftest.py`.

    Sustituye el *binding* del módulo (`core.codicert`, atributo `_ATRIBUTO_SUSTITUIDO`), no
    una copia importada en otro sitio: las cuatro funciones públicas que lo usan (`acceso`,
    `enviar_burofax`, `enviar_eec`, `_get`) lo resuelven por nombre GLOBAL en el momento de
    la llamada, así que sustituir el nombre en el módulo basta -- no hace falta tocarlas una
    a una, y no hay una copia local que se quede apuntando a la función real.

    Scope función y `autouse`, igual que `tests/_barrera.py::instalar` desde
    `_barrera_frontal`: una fixture de sesión se monta DESPUÉS de la colección y no puede
    proteger un test que importe y llame en su propio cuerpo antes de que la sesión exista;
    un helper opt-in que el autor olvide invocar no es una barrera, es una sugerencia.
    """
    from core import codicert

    monkeypatch.setattr(codicert, _ATRIBUTO_SUSTITUIDO, _sustituto_vetado)
