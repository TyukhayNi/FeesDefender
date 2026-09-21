"""Guard permanente: ningún test de la suite habla de verdad con Codicert.

La superficie de red de `core/codicert.py` es UNA sola función: `_cliente_real()`.
Todo lo demás (`acceso`, `enviar_burofax`, `enviar_eec`, `_get`...) recibe el
cliente inyectado por quien llama. Mientras eso sea cierto, ningún test necesita
tocar `httpx` ni la base real para probar nada: le basta un doble.

Cuatro formas, no una, de que ese contrato se rompa; de ahí los cuatro checks:

1. `core/codicert.py` deja de tener a `_cliente_real` como única puerta (alguien
   mete un `import httpx` de más, fuera de esa función).
2. Un test llama a `_cliente_real()` él mismo, en vez de inyectar un doble.
3. Un test de la superficie Codicert/expedición (`test_codicert_*.py`,
   `test_expedicion_*.py`) importa `httpx` por su cuenta. Puede levantar un
   cliente real sin nombrar `_cliente_real` y sin escribir la URL de producción
   como literal —por ejemplo, resolviendo la base con el propio `_base_de(...)`
   del módulo y pasándola a un `httpx.Client` construido a mano—. Es el otro
   lado de la frontera del check 2, que solo mira el NOMBRE de la función, no
   la librería de transporte.
4. Cualquier test de la suite nombra la base de producción Y ADEMÁS puede
   marcarla con `httpx` en ese mismo fichero: la combinación que la convierte
   en una petición real.

   El literal solo, sin más, NO basta como condición: `test_codicert_token.py`
   (`test_el_acceso_va_a_la_base_del_entorno_pedido`) nombra hoy
   `https://ws.codicert.io/v2` a propósito, para comprobar contra un
   `FakeCliente` inyectado que `acceso()` elige la base del entorno pedido —
   nunca importa `httpx` ni toca la red. Se comprobó al escribir este guard:
   un primer borrador que prohibía el literal sin más marcaba ese test como
   `malo` siendo correcto e inocuo (falso positivo, no una alarma real). Por
   eso el check 4 exige las dos señales a la vez —literal Y `httpx` en el
   mismo fichero—, nunca el literal solo.

El propio fichero nombra las cadenas que vigila (`_cliente_real(`, `import
httpx`, la base de producción), así que se autoexcluye de sus propios barridos
—si no, se autodetectaría por su docstring—.
"""
from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
_ESTE_FICHERO = Path(__file__).name

BASE_PRODUCCION = "ws.codicert.io"

# `import httpx` / `from httpx import ...`, con o sin sangría (dentro de una
# función), en su propia línea. No persigue alias ofuscados (`__import__`,
# `importlib.import_module`): no son una vía evidente, y el guard no inventa
# vigilancia para lo que no puede pasar por descuido.
_IMPORT_HTTPX = re.compile(r"^[ \t]*(?:import\s+httpx\b|from\s+httpx\b)", re.MULTILINE)


def _ficheros_de_test(patron: str = "test_*.py") -> list[Path]:
    """`tests/<patron>`, excluyendo este propio guard."""
    return sorted(f for f in (RAIZ / "tests").glob(patron) if f.name != _ESTE_FICHERO)


def test_solo_hay_una_puerta_de_red_en_el_modulo():
    """`import httpx` aparece UNA vez en `core/codicert.py`: dentro de `_cliente_real`."""
    fuente = (RAIZ / "core" / "codicert.py").read_text(encoding="utf-8")
    assert fuente.count("import httpx") == 1, "httpx se importa fuera de `_cliente_real`"


def test_ningun_test_llama_al_cliente_real():
    """Ningún test construye el cliente real: todos inyectan un doble."""
    malos = {}
    for f in _ficheros_de_test():
        txt = f.read_text(encoding="utf-8", errors="replace")
        if re.search(r"_cliente_real\s*\(", txt):
            malos[f.name] = "construye el cliente HTTP real"
    assert not malos, malos


def test_ningun_test_de_codicert_importa_httpx_directamente():
    """La superficie Codicert/expedición no importa `httpx`: solo `_cliente_real` lo hace.

    Alcance por convención de nombre (`test_codicert_*.py`, `test_expedicion_*.py`),
    no por lista fija de ficheros: un fichero nuevo que siga la convención queda
    cubierto sin tocar este guard.
    """
    malos = {}
    for patron in ("test_codicert_*.py", "test_expedicion_*.py"):
        for f in _ficheros_de_test(patron):
            txt = f.read_text(encoding="utf-8", errors="replace")
            if _IMPORT_HTTPX.search(txt):
                malos[f.name] = "importa httpx directamente"
    assert not malos, malos


def test_ningun_test_nombra_la_base_de_produccion_pudiendo_marcarla():
    """Nombrar la base de producción solo es señal de riesgo si el fichero puede marcarla.

    Ver el punto 4 del docstring del módulo: exige el literal Y `httpx` en el
    mismo fichero, precisamente para no marcar como `malo` el uso legítimo de
    `test_codicert_token.py` contra un doble inyectado.
    """
    malos = {}
    for f in _ficheros_de_test():
        txt = f.read_text(encoding="utf-8", errors="replace")
        if BASE_PRODUCCION in txt and _IMPORT_HTTPX.search(txt):
            malos[f.name] = "nombra la base de producción y puede marcarla por red"
    assert not malos, malos
