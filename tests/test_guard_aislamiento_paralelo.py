"""Guard del aislamiento en paralelo: quien escribe en el arbol de produccion se declara.

## De que defecto sale esto

La suite pasa a correr con `-n auto` (2026-09-06). El autor valido el cambio con que el
conteo cuadrara —4.656 antes, 4.656 despues— y **cero tests serializados**, y concluyo que
la suite era segura en paralelo. La R1 adversarial de Codex (H-01) demostro que esa
inferencia no se seguia del hecho:

    pytest tests/test_guard_localizador.py -n 4    ->  3 rojos

Aquellos tests escriben sondas (`core/_zz_guard_probe_*.py`) **dentro del arbol de
produccion real**, y otros del mismo fichero **escanean `core/` entero**. Las tres
corridas verdes de la suite completa lo fueron por **suerte de reparto**.

**Y el rojo no era lo peor.** El revisor tambien reprodujo el VERDE: un test pasando sin
llegar a analizar su propio caso, porque leyo la sonda que otro worker habia dejado y el
numero coincidio. Un conteo idéntico no lo detecta. Por eso la validacion «mismo numero de
tests» es necesaria y no suficiente, y por eso este guard existe.

## Las dos mitades, porque una sin la otra no vale

1. **Todo fichero de test que escriba en el arbol de produccion lleva `xdist_group`**, para
   que xdist lo mantenga en un solo worker.
2. **Todo sitio que lance `-n auto` pasa `--dist loadgroup`.** Sin ese flag las marcas del
   punto 1 **no hacen absolutamente nada** y xdist reparte igual. Es el caso clasico de
   guarda inerte: la marca esta escrita, se lee bien, y no muerde. Comprobarlo cuesta un
   `in` y es la diferencia entre una defensa y su decorado.

## Lo que este guard NO promete

Que la suite sea segura en paralelo. Prueba **una** condicion necesaria —nadie escribe en
el arbol compartido sin declararlo— y no cubre otras vias de estado compartido: cachés de
librerias externas, variables de entorno del proceso, o servicios. La caché de `tldextract`
apareció en esa misma revision como un compartido real que ni `--basetemp` ni las fixtures
confinan. Decirlo aqui es parte del guard: quien lo lea no debe creer que cubre mas.
"""

from __future__ import annotations

import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

#: Metodos de `pathlib.Path` que MUTAN el sistema de ficheros.
_METODOS_QUE_ESCRIBEN = frozenset(
    {"write_text", "write_bytes", "mkdir", "unlink", "touch", "rmdir", "rename",
     "replace", "symlink_to", "hardlink_to", "chmod"}
)

#: Nombres que, por convencion de este repo, sostienen la raiz del REPOSITORIO (no un
#: `tmp_path`). Escribir sobre algo derivado de aqui es tocar el arbol compartido.
_NOMBRES_DE_RAIZ = frozenset({"ROOT", "RAIZ", "REPO", "PROJECT_ROOT"})

#: Sitios que lanzan la suite completa. Si uno pasa `-n auto` sin `--dist loadgroup`,
#: las marcas de grupo quedan inertes.
_LANZADORES = (
    "scripts/session_close.py",
    ".claude/commands/tests.md",
    ".claude/commands/status.md",
    "CLAUDE.md",
)


def _ficheros_de_test_coleccionados() -> list[Path]:
    """Solo `test_*.py`: es lo que `pyproject.toml` hace coleccionar a pytest.

    Los arneses `tests/_mutantes_*.py` tambien escriben en `core/` —mutan a proposito—
    pero pytest **no los colecciona**, asi que nunca corren dentro de un worker y no
    pueden colisionar con nadie. Se ejecutan a mano y con el arbol limpio.
    """
    return sorted(p for p in (RAIZ / "tests").glob("test_*.py"))


def _escribe_en_el_arbol_de_produccion(fuente: str) -> list[str]:
    """Lineas donde una ruta derivada de la raiz del REPO recibe una escritura.

    Por AST y no por `grep`, y eso no es preciosismo: la escritura real de
    `test_guard_localizador.py` es `fake = ROOT / "core" / "x.py"` y luego
    `fake.write_text(...)`. Un grep de `ROOT.*write_text` **no la ve** — lo comprobe
    escribiendo primero ese grep y creyendome su silencio.
    """
    arbol = ast.parse(fuente)

    derivadas: set[str] = set()
    for nodo in ast.walk(arbol):
        if not (isinstance(nodo, ast.Assign) and isinstance(nodo.value, ast.BinOp)
                and isinstance(nodo.value.op, ast.Div)):
            continue
        izquierda = nodo.value
        while isinstance(izquierda, ast.BinOp):
            izquierda = izquierda.left
        if isinstance(izquierda, ast.Name) and izquierda.id in _NOMBRES_DE_RAIZ:
            derivadas.update(t.id for t in nodo.targets if isinstance(t, ast.Name))

    hallazgos = []
    for nodo in ast.walk(arbol):
        if (isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute)
                and nodo.func.attr in _METODOS_QUE_ESCRIBEN
                and isinstance(nodo.func.value, ast.Name)
                and nodo.func.value.id in derivadas):
            hallazgos.append(f"linea {nodo.lineno}: "
                             f"{nodo.func.value.id}.{nodo.func.attr}()")
    return hallazgos


def _declara_grupo_xdist(fuente: str) -> bool:
    """`pytestmark = pytest.mark.xdist_group(...)` a nivel de modulo, o la marca en algun
    decorador. Se busca en el texto del AST y no con `in` sobre la fuente para no contar
    una mencion dentro de un comentario o un docstring — que es justo como un guard
    empieza a pasar por vacio."""
    arbol = ast.parse(fuente)
    for nodo in ast.walk(arbol):
        if (isinstance(nodo, ast.Attribute) and nodo.attr == "xdist_group"
                and isinstance(nodo.value, ast.Attribute) and nodo.value.attr == "mark"):
            return True
    return False


def test_quien_escribe_en_el_arbol_de_produccion_declara_su_grupo() -> None:
    """Mitad 1: nadie escribe en el arbol compartido sin pedir un worker propio."""
    sin_declarar = {}
    for fichero in _ficheros_de_test_coleccionados():
        fuente = fichero.read_text(encoding="utf-8", errors="replace")
        escrituras = _escribe_en_el_arbol_de_produccion(fuente)
        if escrituras and not _declara_grupo_xdist(fuente):
            sin_declarar[fichero.name] = escrituras

    assert not sin_declarar, (
        "estos ficheros escriben en el arbol de produccion y NO declaran "
        "`pytestmark = pytest.mark.xdist_group(...)`, asi que bajo `-n auto` sus tests se "
        "reparten entre workers y comparten esos ficheros:\n"
        + "\n".join(f"  {n}: {', '.join(ls)}" for n, ls in sorted(sin_declarar.items()))
        + "\n\nNo basta con renombrar la sonda por worker si algun test ESCANEA el arbol "
          "entero: ahi el compartido es el directorio, no el nombre."
    )


def test_el_guard_ve_de_verdad_a_quien_escribe() -> None:
    """Prueba de mutacion del guard anterior: si su detector no detecta, no vale.

    Sin esto, `test_quien_escribe_en_el_arbol_de_produccion_declara_su_grupo` podria estar
    en verde porque el AST **nunca casa** —por ejemplo si alguien renombra `ROOT`— y no
    porque todo el mundo se declare. Es la misma polaridad que `test_guard_localizador`
    aplica a su propio contador.
    """
    sintetico = (
        "from pathlib import Path\n"
        "ROOT = Path(__file__).resolve().parents[1]\n"
        "def test_x():\n"
        "    sonda = ROOT / 'core' / '_zz.py'\n"
        "    sonda.write_text('x', encoding='utf-8')\n"
    )
    assert _escribe_en_el_arbol_de_produccion(sintetico), (
        "el detector no ve una escritura evidente sobre `ROOT / ...`: el guard de arriba "
        "estaria pasando por vacio")
    assert not _declara_grupo_xdist(sintetico)
    assert _declara_grupo_xdist(
        sintetico + "import pytest\npytestmark = pytest.mark.xdist_group(name='g')\n")


def test_el_detector_no_confunde_tmp_path_con_el_arbol_real() -> None:
    """La otra direccion: escribir en `tmp_path` es correcto y no debe denunciarse.

    Un guard que denuncia de mas se desactiva en una semana, y entonces no protege nada.
    """
    correcto = (
        "def test_y(tmp_path):\n"
        "    destino = tmp_path / 'core' / 'x.py'\n"
        "    destino.write_text('x', encoding='utf-8')\n"
    )
    assert not _escribe_en_el_arbol_de_produccion(correcto)


def _argumentos_de_orden(ruta: Path) -> list[str]:
    """Los tokens que de verdad se le pasan a pytest, **sin la prosa que habla de ellos**.

    **Esto era un `in` sobre el texto entero y el guard salio DECORADO, medido el
    2026-09-06.** Retirar `--dist loadgroup` de la lista de argumentos de
    `session_close.py` no ponia rojo el test, porque la cadena seguia apareciendo en el
    **comentario** que explica por que el flag hace falta. El guard pasaba gracias a su
    propia documentacion. Y lo caro: dos funciones mas arriba yo mismo habia escrito que
    no se busca con `in` sobre la fuente «para no contar una mencion dentro de un
    comentario — que es justo como un guard empieza a pasar por vacio».

    - `.py`: por **AST**, quedandose con las cadenas que son elementos de una lista o
      argumentos de una llamada. Los comentarios `#` no existen en el AST, asi que la
      prosa desaparece por construccion en vez de por una lista de exclusiones.
    - `.md`: solo lo que va **dentro de un bloque de codigo** con vallas.
    """
    texto = ruta.read_text(encoding="utf-8", errors="replace")
    if ruta.suffix == ".py":
        tokens: list[str] = []
        for nodo in ast.walk(ast.parse(texto)):
            if isinstance(nodo, ast.List):
                elementos = nodo.elts
            elif isinstance(nodo, ast.Call):
                elementos = list(nodo.args)
            else:
                continue
            tokens += [e.value for e in elementos
                       if isinstance(e, ast.Constant) and isinstance(e.value, str)]
        return tokens

    dentro = False
    lineas: list[str] = []
    for linea in texto.splitlines():
        if linea.lstrip().startswith("```"):
            dentro = not dentro
            continue
        if dentro:
            lineas.append(linea)
    return lineas


def test_todo_lanzador_de_n_auto_pasa_dist_loadgroup() -> None:
    """Mitad 2: la marca sin el flag es decorado.

    `xdist_group` **no hace nada** salvo que la linea de ordenes lleve `--dist loadgroup`.
    Un fichero puede estar perfectamente marcado y repartirse igual, y el sintoma seria un
    rojo intermitente —o un verde por sonda ajena— que nadie ata a este flag.
    """
    sin_flag = []
    for rel in _LANZADORES:
        ruta = RAIZ / rel
        if not ruta.exists():
            continue
        piezas = _argumentos_de_orden(ruta)
        unido = " ".join(piezas)
        lanza_en_paralelo = "-n auto" in unido or ("-n" in piezas and "auto" in piezas)
        pasa_el_grupo = ("--dist loadgroup" in unido
                         or ("--dist" in piezas and "loadgroup" in piezas))
        if lanza_en_paralelo and not pasa_el_grupo:
            sin_flag.append(rel)

    assert not sin_flag, (
        "estos sitios lanzan la suite con `-n auto` y NO pasan `--dist loadgroup`, asi que "
        "las marcas `xdist_group` quedan inertes ahi:\n"
        + "\n".join(f"  {r}" for r in sin_flag)
    )
