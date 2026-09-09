"""4a no escribe. Se comprueba por AST y no por confianza.

Es la garantía que hace que a esta mitad le corresponda **una** ronda de revisión
adversarial en vez de dos: el presupuesto lo fija el radio de daño, y aquí el radio es
cero *por construcción*. Si una tarea futura necesita escribir, este guard se pone rojo —
y ese rojo es la señal de que lo que se está construyendo es 4b, con sus dos rondas.
"""
import ast
import pathlib

import pytest

_RAIZ = pathlib.Path(__file__).resolve().parents[1]
PAQUETE = _RAIZ / "core" / "procedimiento"

#: **Todos** los ficheros que forman la pieza, no solo el paquete. La R1 anadio un
#: escritor a `scripts/procedimiento.py` y sobrevivio porque el glob no lo miraba: el
#: entrypoint del usuario no lo revisaba nadie.
def _ficheros_de_4a() -> list[pathlib.Path]:
    return sorted(PAQUETE.glob("*.py")) + [_RAIZ / "scripts" / "procedimiento.py"]

#: Nombres cuya sola presencia significa «esto escribe».
PROHIBIDOS = frozenset({
    "write_text", "write_bytes", "mkdir", "touch", "unlink", "rmdir",
    "rename", "chmod", "copy", "copy2", "copyfile", "copytree", "move", "rmtree",
    "makedirs", "remove", "removedirs", "symlink_to", "hardlink_to",
})

#: Nombres que **no se pueden decidir por el nombre**: `replace` es `os.replace` y
#: `Path.replace` (escriben), pero también `str.replace` y `dataclasses.replace` (no).
#: Se aplica una heurística por FORMA de la llamada, y el hueco que queda se declara en
#: `test_el_hueco_del_guard_esta_DECLARADO`. No se marca `replace` a secas porque
#: producía cuatro falsos positivos sobre `str.replace` y `dataclasses.replace`, y un
#: guard que grita en verde acaba desactivado.
AMBIGUOS = frozenset({"replace"})

#: Un modo escribe si lleva `w`, `a`, `x` o `+`. Se decide por CARACTER y no por una
#: lista de permutaciones, que siempre estara incompleta: la R1 enumero `wb+` y `at`
#: entre las que faltaban, y la enumeracion no puede cubrir todas las combinaciones
#: validas de Python.
_CHARS_ESCRITURA = frozenset("wax+")


def _es_modo_escritura(valor) -> bool:
    return isinstance(valor, str) and bool(_CHARS_ESCRITURA & set(valor))

#: Capacidades que esta mitad no necesita y por tanto no debe pedir.
CAPS_DE_ESCRITURA = ("WRITE_CASE", "MUTATE_CANONICAL", "GENERATE_DERIVATIVES", "INGEST")


def _escrituras(fuente: str, nombre: str) -> list[str]:
    malos: list[str] = []
    arbol = ast.parse(fuente, filename=nombre)
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call):
            continue
        llamado = (nodo.func.attr if isinstance(nodo.func, ast.Attribute)
                   else getattr(nodo.func, "id", ""))
        if llamado in PROHIBIDOS:
            malos.append(f"{nombre}:{nodo.lineno} {llamado}()")
        elif llamado in AMBIGUOS:
            # `os.replace(a, b)` cualificado: seguro que escribe.
            receptor = (getattr(nodo.func.value, "id", "")
                        if isinstance(nodo.func, ast.Attribute) else "")
            # `Path.replace(destino)`: UN posicional y ningún keyword. `str.replace(a, b)`
            # lleva dos posicionales; `dataclasses.replace(obj, k=v)` lleva keywords.
            forma_de_path = len(nodo.args) == 1 and not nodo.keywords
            if receptor in ("os", "shutil") or forma_de_path:
                malos.append(f"{nombre}:{nodo.lineno} {llamado}() [escritura de ruta]")
        if llamado == "open":
            # **Qué argumento lleva el modo depende de QUIÉN es `open`.** El builtin
            # `open(path, "w")` lo lleva en `args[1]`; el método `Path(x).open("w")` lo
            # lleva en `args[0]`, porque la ruta es el receptor. Mirar solo `args[1]`
            # dejaba pasar la segunda forma, y la R1 la EJECUTÓ: escribía un fichero al
            # importar el paquete y los 120 tests seguían verdes. Mirar los dos sin
            # distinguir es igual de malo al revés — `open("w")` abre un fichero LLAMADO
            # `w` y se marcaría como escritura.
            es_metodo = isinstance(nodo.func, ast.Attribute)
            posicionales = nodo.args[0:1] if es_metodo else nodo.args[1:2]
            args = list(posicionales) + [k.value for k in nodo.keywords
                                         if k.arg == "mode"]
            for arg in args:
                if isinstance(arg, ast.Constant) and _es_modo_escritura(arg.value):
                    malos.append(f"{nombre}:{nodo.lineno} open(mode={arg.value!r})")
    return malos


def test_ningun_modulo_de_4a_llama_a_algo_que_escriba():
    malos: list[str] = []
    for f in _ficheros_de_4a():
        malos += _escrituras(f.read_text(encoding="utf-8"), f.name)
    assert not malos, (
        "4a es la mitad que SOLO LEE y aquí hay llamadas que escriben: " + repr(malos))


def test_el_guard_CAZA_una_escritura_de_verdad():
    """Control positivo: sin esto, el test de arriba pasaría también con la lista de
    prohibidos mal escrita, con un `ast.walk` que no recorre, o con un paquete vacío."""
    sonda = ("import pathlib, shutil\n"
             "pathlib.Path('x').write_text('y')\n"
             "pathlib.Path('d').mkdir()\n"
             "shutil.copy2('a', 'b')\n"
             "open('z', 'w')\n")
    encontrados = _escrituras(sonda, "sonda.py")
    assert len(encontrados) == 4, encontrados
    assert any("write_text" in x for x in encontrados)
    assert any("mkdir" in x for x in encontrados)
    assert any("copy2" in x for x in encontrados)
    assert any("open(mode='w')" in x for x in encontrados)


def test_el_guard_caza_el_open_DE_METODO_que_la_R1_ejecuto():
    """**El hueco que la R1 demostró ejecutándolo.** `Path(x).open("w")` lleva el modo en
    el PRIMER argumento porque la ruta es el receptor; el guard miraba el segundo, así que
    esa escritura creaba un fichero al importar el paquete con los 120 tests en verde.
    """
    sonda = ("import pathlib\n"
             "with pathlib.Path('x').open('w') as fh:\n"
             "    fh.write('y')\n")
    encontrados = _escrituras(sonda, "sonda.py")
    assert any("open(mode='w')" in x for x in encontrados), encontrados


@pytest.mark.parametrize("modo", ["w", "a", "x", "wb", "ab", "xb", "w+", "r+", "a+",
                                  "wt", "wb+", "at", "x+b", "+r"])
def test_el_guard_caza_TODOS_los_modos_que_escriben(modo):
    """Por CARÁCTER y no por enumeración: la R1 nombró `wb+` y `at` entre las que
    faltaban, y una lista de permutaciones siempre va a estar incompleta."""
    assert _escrituras(f"p.open({modo!r})\n", "s.py"), modo
    assert _escrituras(f"open('f', {modo!r})\n", "s.py"), modo


@pytest.mark.parametrize("modo", ["r", "rb", "rt"])
def test_el_guard_no_marca_los_modos_de_solo_lectura(modo):
    assert _escrituras(f"p.open({modo!r})\n", "s.py") == []
    assert _escrituras(f"open('f', {modo!r})\n", "s.py") == []


def test_el_guard_mira_TAMBIEN_el_CLI():
    """La R1 añadió un escritor a `scripts/procedimiento.py` y sobrevivió: el glob solo
    miraba `core/procedimiento/*.py`, así que el entrypoint del usuario no lo revisaba
    nadie."""
    rutas = [str(f) for f in _ficheros_de_4a()]
    esperado = str(pathlib.Path("scripts") / "procedimiento.py")
    assert any(r.endswith(esperado) for r in rutas), rutas


def test_el_guard_NO_se_queja_de_una_lectura():
    """Y el otro valor del instrumento: leer no puede dar positivo."""
    sonda = ("import pathlib, json\n"
             "json.loads(pathlib.Path('x').read_text())\n"
             "pathlib.Path('y').read_bytes()\n"
             "pathlib.Path('z').is_file()\n"
             "open('w')\n")
    assert _escrituras(sonda, "sonda.py") == []


def test_el_paquete_tiene_modulos_que_examinar():
    """Si el glob no encontrara nada, el primer test pasaría vacío y no diría nada."""
    modulos = sorted(p.name for p in PAQUETE.glob("*.py"))
    assert len(modulos) >= 7, modulos
    assert "sede.py" in modulos and "vista.py" in modulos


def test_el_guard_caza_las_dos_formas_de_replace_que_SI_escriben():
    sonda = ("import os\n"
             "os.replace('a', 'b')\n"
             "p.replace(destino)\n")
    encontrados = _escrituras(sonda, "sonda.py")
    assert len(encontrados) == 2, encontrados


def test_el_guard_NO_marca_los_replace_que_no_escriben():
    sonda = ("import dataclasses\n"
             "'a-b'.replace('-', '_')\n"
             "dataclasses.replace(entrada, logical_key='x')\n"
             "str(x).replace(chr(92), '/')\n")
    assert _escrituras(sonda, "sonda.py") == []


def test_el_hueco_del_guard_esta_DECLARADO():
    """**Lo que este guard NO puede ver. Es un inventario de CLASES, no una lista cerrada.**

    La versión anterior de este docstring enumeraba tres excepciones y se leía como
    completa. No lo era: la R1 demostró **ejecutando** que `Path(x).open("w")` se colaba
    —el modo va en el primer argumento y el guard miraba el segundo—, y que un escritor
    añadido al CLI sobrevivía porque el glob no lo miraba. Las dos están arregladas; lo
    que no se puede arreglar es la naturaleza del instrumento, y eso es lo que va aquí.

    **Un AST no resuelve tipos ni sigue valores.** Las clases de escritura que se le
    escapan, con el ejemplo de la R1 donde lo hay:

    1. **Nombre construido en ejecución:** `getattr(p, "write_" + "text")("x")`.
    2. **Flujo de datos:** el modo en una variable, en una expresión o por `**kwargs`; una
       función importada con alias o guardada en variable. No se sigue el valor.
    3. **Sumideros no enumerados:** `os.open` con flags de creación, `os.truncate`,
       métodos de escritura sobre un *handle* ya abierto.
    4. **Streams:** `json.dump(..., fh)` o `yaml.safe_dump(..., stream=fh)` escriben sin
       que aparezca ningún nombre de la denylist.
    5. **Efectos transitivos:** una función de otro módulo que escriba por dentro. Permitir
       el prefijo `core` **no audita su implementación**, y hay un caso real y pertinente:
       `WorkspaceRegistry`, en la cadena que la fachada invoca, **renombra** un registro
       corrupto al leerlo (R1/H-05). O sea que la cadena de 4a sí puede producir una
       escritura, fuera del expediente.
    6. **`replace`:** `p.replace(target='x')` por keyword no se detecta. En cambio
       `os.replace(*args)` **sí** se detecta — el docstring anterior decía lo contrario, y
       era falso.

    **Y una corrección que importa más que todas las anteriores.** El docstring decía que
    lo que «sostenía de verdad» la garantía era no pedir `WRITE_CASE`. **Eso es falso:**
    `CaseWorkspace.exigir` es una comprobación explícita del propio código, no un control
    del sistema operativo sobre `open`. No pedir la capacidad significa que una escritura
    que se colara actuaría **sin declararlo**, no que no pudiera ocurrir. Confundir un
    permiso no solicitado con una imposibilidad técnica es justo el tipo de garantía
    imaginaria que esta revisión existe para deshacer.

    **Lo que este guard sí acredita, y es lo único que se le puede pedir:** que ninguna de
    las formas *sintácticas ordinarias* de escribir aparezca en los ficheros de 4a. Para
    la propiedad completa haría falta instrumentar efectos en ejecución — un *audit hook*
    sobre `open`, que es lo que la R1 usó — y eso es una pieza propia.
    """
    import ast as _ast

    evasion = "getattr(p, 'write' + '_text')('x')\n"
    assert _escrituras(evasion, "evasion.py") == [], (
        "si esto empieza a cazarse, actualiza el hueco declarado")

    # Y el inventario de imports, que es lo que hace verificable el punto 2.
    externos = set()
    for f in sorted(PAQUETE.glob("*.py")):
        for nodo in _ast.walk(_ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(nodo, _ast.Import):
                externos |= {a.name.split(".")[0] for a in nodo.names}
            elif isinstance(nodo, _ast.ImportFrom) and nodo.module and nodo.level == 0:
                externos.add(nodo.module.split(".")[0])
    permitidos = {"json", "yaml", "hashlib", "re", "unicodedata", "os", "stat",
                  "pathlib", "dataclasses", "enum", "core", "getpass", "socket",
                  "__future__"}
    assert externos <= permitidos, (
        f"imports nuevos que el hueco declarado no cubre: {sorted(externos - permitidos)}")


def test_4a_no_pide_capacidad_de_ESCRITURA_en_ningun_sitio():
    """La otra mitad de la garantía: aunque el código no escribiera, pedir `WRITE_CASE`
    sería pedir un permiso que no necesita — y el permiso concedido es lo que 4b usará."""
    malos = []
    for f in _ficheros_de_4a():
        txt = f.read_text(encoding="utf-8")
        for cap in CAPS_DE_ESCRITURA:
            # El nombre puede aparecer en prosa explicando qué NO se pide; lo que se
            # busca es su uso como símbolo, `Capability.X`.
            if f"Capability.{cap}" in txt:
                malos.append(f"{f.name}: Capability.{cap}")
    assert not malos, f"4a pide capacidades que no necesita: {malos}"
