"""4a no escribe. Se comprueba por AST y no por confianza.

Es la garantía que hace que a esta mitad le corresponda **una** ronda de revisión
adversarial en vez de dos: el presupuesto lo fija el radio de daño, y aquí el radio es
cero *por construcción*. Si una tarea futura necesita escribir, este guard se pone rojo —
y ese rojo es la señal de que lo que se está construyendo es 4b, con sus dos rondas.
"""
import ast
import pathlib

PAQUETE = pathlib.Path(__file__).resolve().parents[1] / "core" / "procedimiento"

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

#: `open(...)` en modo de escritura.
MODOS_ESCRITURA = frozenset({"w", "a", "x", "wb", "ab", "xb", "w+", "r+", "a+", "wt"})

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
            args = list(nodo.args[1:2]) + [k.value for k in nodo.keywords
                                           if k.arg == "mode"]
            for arg in args:
                if isinstance(arg, ast.Constant) and arg.value in MODOS_ESCRITURA:
                    malos.append(f"{nombre}:{nodo.lineno} open(mode={arg.value!r})")
    return malos


def test_ningun_modulo_de_4a_llama_a_algo_que_escriba():
    malos: list[str] = []
    for f in sorted(PAQUETE.glob("*.py")):
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
    """**Lo que este guard NO puede ver, dicho aquí y no en un comentario perdido.**

    Un AST no resuelve tipos, así que hay tres formas de escribir que se le escapan:

    1. `getattr(p, "write_" + "text")("x")` — el nombre construido en ejecución.
    2. Una librería de terceros que escriba por dentro (aquí no hay ninguna: el paquete
       solo importa `json`, `yaml`, `hashlib`, `re`, `unicodedata`, `os`, `stat`,
       `pathlib`, `dataclasses`, `enum` y módulos de `core`).
    3. `p.replace(x)` sobre un `str` con un solo argumento — se marcaría como escritura
       (falso positivo), y `os.replace(*args)` con desempaquetado — no se marcaría.

    La cobertura es por tanto **parcial y declarada**, no completa. Lo que la sostiene de
    verdad es que el paquete no pide ninguna capacidad de escritura al workspace
    (`test_4a_no_pide_capacidad_de_ESCRITURA_en_ningun_sitio`): sin `WRITE_CASE`, una
    escritura que se colara actuaría sin permiso y es el resolver quien tiene la última
    palabra.
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
    for f in sorted(PAQUETE.glob("*.py")):
        txt = f.read_text(encoding="utf-8")
        for cap in CAPS_DE_ESCRITURA:
            # El nombre puede aparecer en prosa explicando qué NO se pide; lo que se
            # busca es su uso como símbolo, `Capability.X`.
            if f"Capability.{cap}" in txt:
                malos.append(f"{f.name}: Capability.{cap}")
    assert not malos, f"4a pide capacidades que no necesita: {malos}"
