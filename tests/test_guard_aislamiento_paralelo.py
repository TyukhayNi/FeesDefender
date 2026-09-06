"""Guard del aislamiento en paralelo: **ningún test escribe en el árbol de producción.**

## De qué defecto sale esto, y por qué la regla es la que es

La suite pasó a correr con `-n auto` (2026-09-06). El autor lo validó con que el conteo
cuadrara —4.656 antes, 4.656 después— y concluyó que la suite era segura en paralelo. Dos
rondas adversariales desmontaron esa inferencia en dos escalones, y el segundo es el que
explica la forma de este fichero:

- **R1 (H-01):** `pytest tests/test_guard_localizador.py -n 4` daba 3 rojos. Aquellos tests
  escribían sondas (`core/_zz_guard_probe_*.py`) **dentro del árbol de producción real**, y
  seis parametrizaciones compartían el mismo nombre de fichero. Peor que el rojo fue el
  **verde** que el revisor también reprodujo: un test pasando sin analizar su propio caso,
  porque leyó la sonda de otro worker y el número coincidió.
- **Remedio del autor:** marcar ese fichero con `xdist_group` y pasar `--dist loadgroup`.
- **R2 (H-01):** insuficiente. Agrupar a los **escritores** no protege de los **lectores**:
  cualquier test de otro fichero que escanee `core/` puede enumerar una sonda y abrirla
  después de que el escritor la haya borrado. El revisor lo reprodujo forzando esa
  intercalación (`FileNotFoundError` en `test_entrypoints_mutex.py`).

**Remediar el ejemplo era agrupar. Remediar la frontera es que nadie escriba.** Los dos
tests que escribían eran pruebas de mutación *del contador*, no del árbol: no necesitaban
el `core/` vivo para nada. Con la raíz del escáner parametrizada montan su sonda en
`tmp_path` y el problema **deja de existir** en vez de quedar administrado.

## Por qué no hay escotilla de grupo

La versión anterior de este guard decía «quien escriba, que declare `xdist_group`». Esta
dice **que no escriba**. Es más fuerte, tiene menos piezas y elimina de paso tres defectos
que R2 encontró en la maquinaria de la escotilla: un `_declara_grupo_xdist` que aceptaba
`unused = pytest.mark.xdist_group` —una referencia suelta que no marca ningún test—, y un
guard de lanzadores que pasaba si la cadena `--dist loadgroup` aparecía en cualquier parte
del fichero, aunque el comando que lanzaba pytest no la llevara.

Censo del 2026-09-06 con el detector reforzado: **0 escritores de 265 ficheros
coleccionables.** Si algún día uno los necesita de verdad, se reintroducen la marca **y**
el flag a la vez, con la medición que lo justifique. Añadir la maquinaria hoy, para nadie,
sería anticipación — y anticipar es lo que dejó las tres piezas defectuosas de arriba.

## Lo que este guard NO promete

Que la suite sea segura en paralelo. Prueba **una** condición necesaria y no cubre otras
vías de estado compartido: variables de entorno del proceso, cachés de librerías externas
(R2 midió que la de `tldextract` y la de Hypothesis son compartidas y que `--basetemp` no
las confina), puertos, o servicios. Decirlo aquí es parte del guard: quien lo lea no debe
creer que cubre más.
"""

from __future__ import annotations

import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

#: Métodos de `pathlib.Path` (y de `os`/`shutil`) que MUTAN el sistema de ficheros.
_METODOS_QUE_ESCRIBEN = frozenset(
    {"write_text", "write_bytes", "mkdir", "unlink", "touch", "rmdir", "rename",
     "replace", "symlink_to", "hardlink_to", "chmod", "makedirs", "removedirs",
     "rmtree", "copy", "copy2", "copyfile", "copytree", "move"}
)

#: Nombres que, por convención de este repo, sostienen la raíz del REPOSITORIO.
_NOMBRES_DE_RAIZ = frozenset({"ROOT", "RAIZ", "REPO", "PROJECT_ROOT"})

#: Atributos que sostienen la raíz del repo cuando se leen de la configuración.
#: `project_root` entra porque `tests/test_case_mutex_r11.py` escribía por ahí y la primera
#: versión de este detector NO lo veía (R2 de Codex, H-02).
_ATRIBUTOS_DE_RAIZ = frozenset({"project_root", "repo_root", "ROOT", "RAIZ"})

#: Primer tramo de una ruta RELATIVA que cae dentro del árbol versionado. Los tests corren
#: con el cwd en la raíz, así que `Path("core/x.py").write_text(...)` escribe en producción
#: sin mencionar ninguna raíz.
_TRAMOS_DE_PRODUCCION = frozenset({"core", "scripts", "docs", "data", ".claude"})

#: Modos de `open()` que escriben.
_MODOS_QUE_ESCRIBEN = ("w", "a", "x", "+")


def ficheros_de_test_coleccionados() -> list[Path]:
    """Lo que pytest colecciona de verdad: `test_*.py` **y** `*_test.py`, **recursivo**.

    R2 (H-02) señaló que la versión anterior usaba `glob("test_*.py")` sobre el primer
    nivel: hoy los 265 ficheros son planos y empiezan por `test_`, así que no perdía
    ninguno, pero la enumeración no era la de pytest y un subdirectorio futuro habría
    quedado fuera **sin que nada avisara**. Un guard cuya población no coincide con la
    real es un guard que encoge solo.

    Los arneses `tests/_mutantes_*.py` también escriben en `core/` —mutan a propósito— pero
    pytest **no los colecciona**, así que nunca corren dentro de un worker y no pueden
    colisionar con nadie. Se ejecutan a mano y con el árbol limpio.
    """
    return sorted(set(list((RAIZ / "tests").rglob("test_*.py"))
                      + list((RAIZ / "tests").rglob("*_test.py"))))


def _arraigada(nodo: ast.AST, derivadas: set[str]) -> bool:
    """Si una EXPRESIÓN apunta dentro del árbol del repositorio.

    Recursiva a propósito: la primera versión solo miraba `Name`, así que
    `(ROOT / "core" / "x.py").write_text(...)` —sin variable intermedia— pasaba de largo.
    R2 contó **cinco de seis** formas ordinarias que se le escapaban.
    """
    if isinstance(nodo, ast.Name):
        return nodo.id in _NOMBRES_DE_RAIZ or nodo.id in derivadas
    if isinstance(nodo, ast.Attribute):
        return nodo.attr in _ATRIBUTOS_DE_RAIZ
    if isinstance(nodo, ast.BinOp) and isinstance(nodo.op, ast.Div):
        return _arraigada(nodo.left, derivadas)
    if isinstance(nodo, ast.Call):
        if isinstance(nodo.func, ast.Attribute) and nodo.func.attr == "joinpath":
            return _arraigada(nodo.func.value, derivadas)
        if isinstance(nodo.func, ast.Name) and nodo.func.id == "Path" and nodo.args:
            primero = nodo.args[0]
            if isinstance(primero, ast.Constant) and isinstance(primero.value, str):
                cabeza = primero.value.replace("\\", "/").lstrip("./").split("/")[0]
                return cabeza in _TRAMOS_DE_PRODUCCION
            return _arraigada(primero, derivadas)
    return False


def _nombres_derivados(arbol: ast.AST) -> set[str]:
    """Variables que sostienen una ruta del repo. **Punto fijo**, no una pasada.

    Sin iterar, `a = ROOT / "core"` seguido de `b = a / "x.py"` dejaba `b` fuera: el alias
    transitivo era una de las formas que R2 midió que se escapaban.
    """
    derivadas: set[str] = set()
    for _ in range(10):  # converge en 2-3; el tope evita un bucle si algo patológico
        antes = len(derivadas)
        for nodo in ast.walk(arbol):
            objetivos, valor = [], None
            if isinstance(nodo, ast.Assign):
                objetivos, valor = nodo.targets, nodo.value
            elif isinstance(nodo, ast.AnnAssign) and nodo.value is not None:
                objetivos, valor = [nodo.target], nodo.value
            if valor is not None and _arraigada(valor, derivadas):
                derivadas.update(t.id for t in objetivos if isinstance(t, ast.Name))
        if len(derivadas) == antes:
            break
    return derivadas


def _abre_para_escribir(llamada: ast.Call) -> bool:
    """Si un `open(...)`/`.open(...)` lleva modo de escritura. Sin modo, es lectura."""
    modos = [a.value for a in llamada.args
             if isinstance(a, ast.Constant) and isinstance(a.value, str)]
    modos += [k.value.value for k in llamada.keywords
              if k.arg == "mode" and isinstance(k.value, ast.Constant)]
    return any(any(c in str(m) for c in _MODOS_QUE_ESCRIBEN) for m in modos)


def escribe_en_el_arbol_de_produccion(fuente: str) -> list[str]:
    """Líneas donde algo del árbol del REPOSITORIO recibe una escritura.

    Por AST y no por `grep`, y eso no es preciosismo: la escritura real que destapó todo
    esto era `fake = ROOT / "core" / "x.py"` y luego `fake.write_text(...)`. Un grep de
    `ROOT.*write_text` **no la ve** — lo comprobé escribiendo primero ese grep y creyéndome
    su silencio.

    ## Lo que este detector NO ve, y hay que decirlo

    No es un analizador interprocedimental, y construirlo sería un proyecto. **Se le
    escapa** una escritura a través de un helper que recibe la ruta como parámetro, una
    ruta armada dinámicamente (`ROOT / variable`), y cualquier cosa que pase por un
    subproceso. La promesa es **las formas ordinarias**, no la universalidad: prometer más
    sería dar una confianza que no compra, que es justo lo que R2 castigó en su versión
    anterior.
    """
    arbol = ast.parse(fuente)
    derivadas = _nombres_derivados(arbol)
    hallazgos: list[str] = []

    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call):
            continue
        f = nodo.func
        if isinstance(f, ast.Attribute) and _arraigada(f.value, derivadas):
            if f.attr in _METODOS_QUE_ESCRIBEN:
                hallazgos.append(f"linea {nodo.lineno}: .{f.attr}()")
            elif f.attr == "open" and _abre_para_escribir(nodo):
                hallazgos.append(f"linea {nodo.lineno}: .open(modo de escritura)")
        elif isinstance(f, ast.Attribute) and f.attr in _METODOS_QUE_ESCRIBEN:
            if any(_arraigada(a, derivadas) for a in nodo.args):
                hallazgos.append(f"linea {nodo.lineno}: {f.attr}(<ruta del repo>)")
        elif isinstance(f, ast.Name) and f.id == "open" and nodo.args:
            if _arraigada(nodo.args[0], derivadas) and _abre_para_escribir(nodo):
                hallazgos.append(f"linea {nodo.lineno}: open(<ruta del repo>, escritura)")

    return sorted(set(hallazgos))


def test_ningun_test_escribe_en_el_arbol_de_produccion() -> None:
    """La regla, sin escotilla: **nadie escribe en el árbol compartido.**"""
    escritores = {}
    for fichero in ficheros_de_test_coleccionados():
        hallazgos = escribe_en_el_arbol_de_produccion(
            fichero.read_text(encoding="utf-8", errors="replace"))
        if hallazgos:
            escritores[fichero.name] = hallazgos

    assert not escritores, (
        "estos tests escriben en el árbol de producción, que es compartido por todos los "
        "workers de `-n auto`:\n"
        + "\n".join(f"  {n}: {', '.join(ls)}" for n, ls in sorted(escritores.items()))
        + "\n\nNo lo arregles con `xdist_group`: agrupar protege de los otros ESCRITORES y "
          "no de los LECTORES que escanean el mismo árbol (medido, R2/H-01). Monta un "
          "árbol sintético en `tmp_path` y pásaselo a la función bajo prueba — así lo hace "
          "`tests/test_guard_localizador.py::_arbol_sintetico`."
    )


def test_el_detector_ve_las_formas_ordinarias_de_escribir() -> None:
    """Prueba de mutación del detector: si no detecta, el guard de arriba pasa por vacío.

    Las nueve formas son las seis que R2 midió que se escapaban, más tres que encontré al
    ampliarlo. Sin este test, renombrar `ROOT` dejaría el guard verde para siempre.
    """
    base = "from pathlib import Path\nimport os\nROOT = Path()\n"
    formas = {
        "variable intermedia": "p = ROOT/'core'/'x.py'\np.write_text('x')\n",
        "sobre la expresión": "(ROOT/'core'/'x.py').write_text('x')\n",
        "alias transitivo": "a = ROOT/'core'\nb = a/'x.py'\nb.write_text('x')\n",
        "asignación anotada": "p: Path = ROOT/'core'/'x.py'\np.write_text('x')\n",
        "joinpath": "p = ROOT.joinpath('core','x.py')\np.write_text('x')\n",
        "open en modo escritura": "p = ROOT/'core'/'x.py'\np.open('w')\n",
        "ruta relativa al cwd": "Path('core/x.py').write_text('x')\n",
        "raíz desde la config": "d = Path(config.settings.project_root)/'x'\nd.mkdir()\n",
        "os.mkdir": "os.mkdir(ROOT/'core'/'z')\n",
    }
    ciegas = [n for n, src in formas.items()
              if not escribe_en_el_arbol_de_produccion(base + src)]
    assert not ciegas, f"el detector NO ve estas formas de escribir: {ciegas}"


def test_el_detector_no_denuncia_lo_correcto() -> None:
    """La otra dirección. Un guard que denuncia de más se desactiva en una semana, y
    entonces no protege nada — R2 lo demostró con el guard del `.gitignore` (H-07)."""
    correctos = {
        "tmp_path": "def t(tmp_path):\n    (tmp_path/'core'/'x.py').write_text('x')\n",
        "lectura": "from pathlib import Path\nROOT=Path()\n"
                   "(ROOT/'core'/'x.py').read_text()\n",
        "open sin modo": "from pathlib import Path\nROOT=Path()\n"
                         "(ROOT/'core'/'x.py').open()\n",
        "ruta ajena": "from pathlib import Path\nPath('/otro/sitio/x.py').write_text('x')\n",
    }
    falsos = [n for n, src in correctos.items()
              if escribe_en_el_arbol_de_produccion(src)]
    assert not falsos, f"el detector denuncia cosas correctas: {falsos}"


def test_la_poblacion_es_la_que_pytest_colecciona() -> None:
    """El guard mira todos los ficheros que pytest colecciona, no un subconjunto.

    R2 (H-02) señaló que la enumeración anterior era `glob` de primer nivel: correcta hoy
    por casualidad —los 265 ficheros son planos— e incorrecta el día que alguien cree
    `tests/unidad/test_x.py`. Un guard cuya población no es la real encoge en silencio.
    """
    ficheros = ficheros_de_test_coleccionados()
    assert len(ficheros) > 200, f"solo {len(ficheros)} ficheros: la enumeración se rompió"
    nombres = {f.name for f in ficheros}
    assert "test_guard_localizador.py" in nombres
    assert not any(f.name.startswith("_mutantes_") for f in ficheros), (
        "los arneses de mutación NO los colecciona pytest y no deben entrar en el censo")
