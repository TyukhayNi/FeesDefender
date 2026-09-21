"""Barrera de EJECUCIÓN del gestor documental: ningún test alcanza el CRM real.

Mismo patrón y mismo fundamento que `tests/_barrera_codicert.py`, y aquí lo que hay
en juego es peor. Aquel cerraba el hallazgo H-13 de la R2 de F1: un barrido de texto
sobre los ficheros de test **no puede ver la forma ordinaria de llegar a la red** —
llamar a la API pública sin inyectar `cliente=`—, porque un test que hace eso no
escribe `import httpx`, no nombra la base de producción y no llama a nada
sospechoso: todos los checks del guard de texto pasan en verde mientras la llamada
alcanza la función real, que sí abre la conexión.

**La diferencia con Codicert es que `core/sudespacho_documentos.py` ESCRIBE.** Un
descuido allí es un GET de más contra un servicio de lectura; aquí es un documento
creado en el gestor documental de un expediente **real**, con su relación colgada, y
la suite corriendo en paralelo con doce workers. El §17.5 dice lo que cuesta
retirarlo: dos borrados, en orden, y verificando cada uno por lectura.

## Qué hace

Sustituye el *binding* del módulo —la única función que importa `httpx`, que las tres
puertas públicas (`subir_documento`, `descargar_documento`, `buscar_por_origen_id`)
resuelven con `cliente or` una llamada a ella— por uno que lanza. Cierra el paso
ANTES de que el `import httpx` llegue a ejecutarse, así que protege
independientemente de por qué camino se llegó: con `cliente=` olvidado, con un doble
mal construido, o con cualquier puerta pública futura que resuelva su transporte con
el mismo `or`.

## Qué NO hace

No sustituye al guard de texto de `test_guard_cosecha_sin_red_ni_escritura.py`, que
vigila que siga habiendo **una sola** puerta de red en el módulo. Son
complementarios: si apareciera un segundo `import httpx`, esta barrera —que sustituye
un único binding— dejaría de cubrir el módulo entero y nada lo avisaría. El guard de
texto es lo que avisa.
"""
from __future__ import annotations

from typing import Any

#: Nombre del atributo de `core.sudespacho_documentos` que esta barrera sustituye.
_ATRIBUTO_SUSTITUIDO = "_cliente_real"


class BarreraSudespachoViolada(AssertionError):
    """Un test intentó alcanzar el CRM real sin inyectar un doble.

    Hereda de `AssertionError` a propósito, igual que `BarreraCodicertViolada`: es un
    fallo del TEST (olvidó `cliente=`), no del código bajo prueba, y así el
    `except Exception` de `_peticion` no se lo traga —`SudespachoDocumentosError` es
    un `RuntimeError`, nunca un `AssertionError`—. Ese `except` existe justamente
    para traducir fallos de transporte, y sin esta herencia disfrazaría el descuido
    de «la red se cayó».
    """


def _sustituto_vetado() -> Any:
    """Ocupa el lugar del transporte real mientras la barrera está instalada."""
    raise BarreraSudespachoViolada(
        "la suite no puede abrir una conexión real al CRM sudespacho. Esta llamada "
        "no inyectó `cliente=`, así que `core.sudespacho_documentos` intentó "
        f"resolver su transporte por defecto (`{_ATRIBUTO_SUSTITUIDO}`, la ÚNICA "
        "puerta de red del módulo) y la barrera la ha bloqueado ANTES de que "
        "`httpx` se importara siquiera. Importa: este módulo ESCRIBE — un descuido "
        "aquí crea un documento en un expediente real. Inyecta un doble con "
        "`cliente=` (patrón en tests/test_sudespacho_documentos.py::FakeHTTP)."
    )


def instalar(monkeypatch) -> None:
    """Instala la barrera para un test. La llama la fixture `autouse` de `conftest`.

    Sustituye el *binding* del módulo, no una copia importada en otro sitio: las tres
    puertas públicas lo resuelven por nombre GLOBAL en el momento de la llamada, así
    que cambiar el atributo del módulo las cubre a las tres y a las que vengan.
    """
    from core import sudespacho_documentos

    monkeypatch.setattr(sudespacho_documentos, _ATRIBUTO_SUSTITUIDO,
                        _sustituto_vetado)
