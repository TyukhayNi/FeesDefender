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
   `test_expedicion_*.py`, sus dobles y sus helpers) importa `httpx` por su
   cuenta. Puede levantar un cliente real sin nombrar `_cliente_real` y sin
   escribir la URL de producción como literal —por ejemplo, resolviendo la base
   con el propio `_base_de(...)` del módulo y pasándola a un `httpx.Client`
   construido a mano—. Es el otro lado de la frontera del check 2, que solo
   mira el NOMBRE de la función, no la librería de transporte.
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

Hallazgo de revisión (2026-09-21): el censo de "ficheros de la superficie
Codicert" vivía en `_ficheros_de_test()` como un `glob("test_*.py")` NO
recursivo, anclado al prefijo `test_`. Por construcción nunca podía ver
`tests/_dobles/fake_codicert.py` —vive en una subcarpeta y no empieza por
`test_`—, que es precisamente el doble que inyectan los diez ficheros
vigilados. Un `import httpx` metido ahí (p. ej. «que el doble a veces pegue al
sandbox para una prueba de humo») pasaba en verde: un guard que vigila menos
ficheros de los que cree. El censo ahora es por PERTENENCIA real —nombre o
contenido mencionan `codicert` o `expedicion_certificada`—, recursivo bajo
`tests/`, y el propio guard se comprueba a sí mismo (más abajo) para no volver
a encogerse en silencio.
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

# Ámbito de Codicert: por NOMBRE de fichero o por CONTENIDO, nunca por prefijo
# `test_` ni por lista fija. `codicert` cubre el transporte (`core/codicert.py`)
# y su doble (`tests/_dobles/fake_codicert.py`); `expedicion_certificada` es el
# módulo del criterio del despacho (`core/expedicion_certificada.py`) que los
# `test_expedicion_*.py` importan sin nombrar «codicert» en su propio texto.
_TERMINOS_AMBITO = ("codicert", "expedicion_certificada")


def _ficheros_de_test() -> list[Path]:
    """Todo `.py` bajo `tests/` (recursivo) que pertenece al ámbito de Codicert.

    Pertenencia por CONTENIDO o NOMBRE reales, no por el prefijo `test_` ni por
    la profundidad bajo `tests/`: cualquier fichero —test, doble o helper, a
    cualquier nivel— cuyo nombre o cuyo texto mencionen (sin distinguir
    mayúsculas) `codicert` o `expedicion_certificada` cae bajo vigilancia. Así
    entra `tests/_dobles/fake_codicert.py` —el doble que un `glob("test_*.py")`
    no recursivo nunca alcanzaba— y quedan fuera, por no mencionarlos, los
    tests de otros módulos del repositorio que importan `httpx` por su cuenta
    y de forma legítima (CRM, sudespacho...: los hay, y no son de este ámbito).
    Se autoexcluye por nombre.
    """
    censo: list[Path] = []
    for f in sorted((RAIZ / "tests").rglob("*.py")):
        if f.name == _ESTE_FICHERO:
            continue
        if any(termino in f.name.lower() for termino in _TERMINOS_AMBITO):
            censo.append(f)
            continue
        txt = f.read_text(encoding="utf-8", errors="replace").lower()
        if any(termino in txt for termino in _TERMINOS_AMBITO):
            censo.append(f)
    return censo


def test_solo_hay_una_puerta_de_red_en_el_modulo():
    """`import httpx` / `from httpx import ...` aparece UNA vez: en `_cliente_real`.

    Hallazgo de revisión (2026-09-21): esto comparaba antes con
    `fuente.count("import httpx") == 1`, un conteo de subcadena literal con dos
    defectos. Falso negativo: no veía `from httpx import request as _r` —una
    segunda puerta de red real— porque no es la grafía exacta `import httpx`.
    Falso positivo: un comentario o docstring que simplemente CITE el texto
    vigilado, sin ser una importación, también suma al conteo y tira el guard
    sin que exista puerta nueva. El mismo regex `_IMPORT_HTTPX` que ya usan los
    otros tres checks resuelve las dos cosas a la vez: reconoce ambas grafías y
    solo cuenta líneas donde `import`/`from` es lo primero que hay en la línea,
    nunca apariciones sueltas del texto dentro de una frase.
    """
    fuente = (RAIZ / "core" / "codicert.py").read_text(encoding="utf-8")
    apariciones = _IMPORT_HTTPX.findall(fuente)
    assert len(apariciones) == 1, f"httpx se importa fuera de `_cliente_real`: {apariciones}"


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

    Alcance por PERTENENCIA real (`_ficheros_de_test()`: nombre o contenido
    mencionan `codicert`/`expedicion_certificada`), no por convención de
    nombre ni por lista fija: así cubre también los dobles
    (`tests/_dobles/fake_codicert.py`) y los helpers, que un `glob` anclado a
    `test_*.py` y no recursivo dejaba fuera —y que es donde de hecho inyectan
    el cliente los diez ficheros vigilados.
    """
    malos = {}
    for f in _ficheros_de_test():
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


def test_el_censo_incluye_los_dobles_y_no_se_vacia_en_silencio():
    """Contrato del propio censo: nunca vacío ni corto, y siempre ve al doble.

    Un censo por contenido puede romperse en silencio —una excepción tragada,
    un cambio de convención en los dobles— y devolver una lista corta o vacía
    sin que ningún test lo note; entonces los otros tres checks de este guard
    dejarían de vigilar nada y seguirían en verde, que es exactamente el
    defecto que tenía el censo por prefijo (ver el hallazgo de revisión del
    docstring del módulo). Por eso el guard se comprueba a sí mismo: tiene que
    ver, como mínimo, a los diez ficheros vigilados y a
    `tests/_dobles/fake_codicert.py`.
    """
    censo = _ficheros_de_test()
    relativos = {f.relative_to(RAIZ / "tests") for f in censo}
    assert len(censo) >= 11, f"censo sospechosamente corto: {sorted(relativos)}"
    assert Path("_dobles") / "fake_codicert.py" in relativos, (
        "el censo no incluye tests/_dobles/fake_codicert.py: el guard ha "
        "vuelto a perder de vista el doble que inyectan los tests vigilados"
    )
