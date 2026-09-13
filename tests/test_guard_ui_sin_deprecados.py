"""Guard permanente: la UI de Streamlit no importa modulos declarados DEPRECADO.

## Por que la frontera es esta y no «el boton de la sala de lectura»

El caso que lo motiva es uno: `streamlit_app.py` importaba `core.sala_lectura`, cuya
**primera linea** dice `[DEPRECADO 2026-06-18] … queda SUPERSEDIDO por la skill … No
ampliar`. Un test que dijera «`streamlit_app.py` no importa `core.sala_lectura`» cerraria
ese ejemplo y dejaria la propiedad abierta: el dia que se depreque otro modulo que la UI
usa, nadie se entera. Es el defecto medido de
[[feedback-remediar-la-frontera-no-el-ejemplo]] — remediar el caso que el informe describe
y no la propiedad de la que es ejemplo.

La propiedad que se fija aqui:

    **Lo que `streamlit_app.py` importa de `core/` no puede estar declarado DEPRECADO.**

Se escribe asi a proposito, sin nombrar ningun modulo: el censo lo hace el propio guard
leyendo las docstrings, de forma que deprecar un modulo **basta** para que su uso en la
UI se ponga rojo, sin tocar este fichero.

## Por que importa que sea la UI y no cualquier llamador

`core/sala_lectura.py` sigue teniendo un llamador legitimo —el CLI
`scripts/sala_lectura.py`, que el runbook §7 llama «el disparo rapido en local»— y ese no
se toca: quien lo dispara sabe lo que dispara. La UI es distinta porque **Paola y Ana no
tocan codigo** (`CLAUDE.md` §«Usuarios del sistema»): no pueden leer una docstring antes
de pulsar un boton, asi que un camino muerto detras de la UI es un camino muerto que se
dispara sin saberlo. Por eso el guard mira `streamlit_app.py` y no `core/` entero.

## Que cuenta como «declarado DEPRECADO»

El marcador `[DEPRECADO` en la **docstring del modulo** — que es donde el repo lo pone y
donde lo lee quien abre el fichero. No se mira el cuerpo: un `# DEPRECADO` suelto en un
comentario a mitad de fichero no declara nada sobre el modulo.

## Aislamiento

Este fichero **no escribe en el arbol de produccion**: la comprobacion real solo LEE
`streamlit_app.py` y `core/`, y las pruebas del detector montan su arbol sintetico en
`tmp_path`. Es la regla sin escotilla de `CLAUDE.md` §Tests, y la razon por la que las dos
raices son parametros de las funciones en vez de constantes del modulo.
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: Marcador canonico. `core/sala_lectura.py` abre con `[DEPRECADO 2026-06-18]`.
MARCADOR = "[DEPRECADO"


def modulos_core_importados(ui_path: Path) -> set[str]:
    """Modulos de `core` que importa `ui_path`, con nombre punteado.

    Recorre el arbol **entero** con `ast.walk`, no solo el nivel superior: el import que
    motivo este guard estaba **dentro** de un `if st.button(...)`, o sea a cuatro niveles
    de profundidad. Un escaner que solo mirase la cabecera del fichero habria dado verde
    sobre el defecto vivo.

    Las tres formas que el repo usa se normalizan al modulo, no al simbolo:

    - `import core.x` / `import core.x as y`  -> ``core.x``
    - `from core import x`                    -> ``core.x``
    - `from core.x import y`                  -> ``core.x`` (y ``core.x.y``, que el
      resolutor descartara si `y` resulta ser un simbolo y no un submodulo)
    """
    arbol = ast.parse(ui_path.read_text(encoding="utf-8"), filename=str(ui_path))
    encontrados: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                if alias.name == "core" or alias.name.startswith("core."):
                    encontrados.add(alias.name)
        elif isinstance(nodo, ast.ImportFrom):
            # `from . import x` (nodo.level > 0) no alcanza a `core/` desde la raiz.
            if nodo.level or not nodo.module:
                continue
            if nodo.module != "core" and not nodo.module.startswith("core."):
                continue
            if nodo.module != "core":
                encontrados.add(nodo.module)
            for alias in nodo.names:
                if alias.name != "*":
                    encontrados.add(f"{nodo.module}.{alias.name}")
    return encontrados


def _fichero_del_modulo(raiz_repo: Path, punteado: str) -> Path | None:
    """Ruta del `.py` de un modulo punteado, o `None` si no es un modulo.

    `from core.config import TAXONOMIA_EV` produce el candidato `core.config.TAXONOMIA_EV`,
    que no es un modulo: devolver `None` es como se descartan los simbolos sin tener que
    importar nada. **Importar** el modulo para preguntarle su `__doc__` seria el camino
    corto y es el equivocado: arrastraria las dependencias de media UI a un guard.
    """
    partes = punteado.split(".")
    modulo = raiz_repo.joinpath(*partes).with_suffix(".py")
    if modulo.is_file():
        return modulo
    paquete = raiz_repo.joinpath(*partes, "__init__.py")
    return paquete if paquete.is_file() else None


def declaracion_de_deprecado(doc: str) -> str | None:
    """La linea de declaracion si la docstring **declara** el modulo deprecado.

    El criterio es POSICIONAL: el marcador abre la primera linea no vacia. No basta con
    que aparezca, y la diferencia no es teorica — `core/sala_lectura_estado.py` cita
    `[DEPRECADO 2026-06-18]` al explicar de que camino viene, y un detector que buscara
    la mencion lo marcaria a el. Declarar es abrir el modulo diciendolo; citar es hablar
    de otro. El repo lo escribe asi: `core/sala_lectura.py` empieza, literalmente, por el
    marcador, y el runbook §7 lo describe como «en la primera linea de su propio modulo».
    """
    for linea in (doc or "").splitlines():
        if not linea.strip():
            continue
        return linea.strip() if linea.lstrip().startswith(MARCADOR) else None
    return None


def deprecados_entre(raiz_repo: Path, punteados: set[str]) -> dict[str, str]:
    """De los modulos dados, los que se declaran DEPRECADO -> su linea de declaracion."""
    hallados: dict[str, str] = {}
    for punteado in sorted(punteados):
        fichero = _fichero_del_modulo(raiz_repo, punteado)
        if fichero is None:
            continue
        doc = ast.get_docstring(ast.parse(fichero.read_text(encoding="utf-8"))) or ""
        linea = declaracion_de_deprecado(doc)
        if linea is not None:
            hallados[punteado] = linea
    return hallados


# ---------------------------------------------------------------------------
# La comprobacion real (solo lectura sobre el arbol del repo)
# ---------------------------------------------------------------------------


def test_la_ui_no_importa_modulos_deprecados() -> None:
    ruta_ui = ROOT / "streamlit_app.py"
    hallados = deprecados_entre(ROOT, modulos_core_importados(ruta_ui))
    assert not hallados, (
        "streamlit_app.py importa modulo(s) declarados DEPRECADO:\n"
        + "\n".join(f"  - {m}: {linea}" for m, linea in hallados.items())
        + "\n\nLa UI la usan Paola y Ana, que no tocan codigo: no pueden leer la "
        "docstring antes de pulsar el boton. Si el camino sigue haciendo falta, el "
        "sitio es el CLI (`python -m scripts.<modulo>`), no un boton."
    )


# ---------------------------------------------------------------------------
# Controles del detector — arbol sintetico en tmp_path, nunca en el de produccion
# ---------------------------------------------------------------------------


def _repo_sintetico(tmp_path: Path, *, docstring_core: str, fuente_ui: str) -> Path:
    """Un repo de mentira con un `core/probe.py` y un `app.py` que lo usa.

    **El parametro se llama `fuente_ui` y no `ui` a proposito.** El guard de aislamiento
    (`test_guard_aislamiento_paralelo`) reune por AST las variables que sostienen una ruta
    del repo, y lo hace **por nombre y sin ambitos** —su docstring declara que no es un
    analizador interprocedimental—. Con `ui = ROOT / "streamlit_app.py"` en la
    comprobacion real, un `write_text(ui, ...)` de aqui abajo se leia como una escritura
    en produccion. El detector acierta al sospechar; quien tiene que quitar la ambiguedad
    es este fichero.
    """
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "core" / "probe.py").write_text(
        f'"""{docstring_core}"""\n', encoding="utf-8")
    (tmp_path / "app.py").write_text(fuente_ui, encoding="utf-8")
    return tmp_path


def test_control_positivo_un_modulo_deprecado_se_senala(tmp_path: Path) -> None:
    """El instrumento tiene que poder dar el OTRO valor.

    Un guard que solo se ha visto verde no ha probado nada: es
    [[feedback-guarda-inerte-comprobar-el-otro-valor]]. Este es el caso que lo pone rojo.
    """
    repo = _repo_sintetico(
        tmp_path,
        docstring_core="[DEPRECADO 2026-01-01] superado por otra cosa. No ampliar.",
        fuente_ui="from core import probe\nprobe.hacer()\n",
    )
    hallados = deprecados_entre(repo, modulos_core_importados(repo / "app.py"))
    assert "core.probe" in hallados
    assert "[DEPRECADO 2026-01-01]" in hallados["core.probe"]


def test_control_negativo_un_modulo_vivo_no_se_senala(tmp_path: Path) -> None:
    repo = _repo_sintetico(
        tmp_path,
        docstring_core="Modulo vivo y corriente.",
        fuente_ui="from core import probe\nprobe.hacer()\n",
    )
    assert deprecados_entre(repo, modulos_core_importados(repo / "app.py")) == {}


def test_el_import_dentro_de_una_funcion_tambien_cuenta(tmp_path: Path) -> None:
    """El caso REAL: el import vivia dentro de un `if st.button(...)`, no en la cabecera.

    Sin `ast.walk` este guard habria dado verde sobre el defecto que vino a cerrar.
    """
    repo = _repo_sintetico(
        tmp_path,
        docstring_core="[DEPRECADO 2026-01-01] no ampliar.",
        fuente_ui=(
            "import streamlit as st\n"
            "def pinta():\n"
            "    with st.expander('x'):\n"
            "        if st.button('y'):\n"
            "            from core import probe\n"
            "            probe.hacer()\n"
        ),
    )
    assert "core.probe" in deprecados_entre(
        repo, modulos_core_importados(repo / "app.py"))


def test_un_simbolo_importado_de_un_modulo_vivo_no_rompe_el_resolutor(
    tmp_path: Path,
) -> None:
    """`from core.probe import COSA` propone `core.probe.COSA`, que no es un modulo.

    Tiene que descartarse en silencio y dejar `core.probe` evaluado por su docstring.
    """
    repo = _repo_sintetico(
        tmp_path,
        docstring_core="[DEPRECADO 2026-01-01] no ampliar.",
        fuente_ui="from core.probe import COSA\nprint(COSA)\n",
    )
    hallados = deprecados_entre(repo, modulos_core_importados(repo / "app.py"))
    assert list(hallados) == ["core.probe"]


def test_citar_el_marcador_no_es_declararlo(tmp_path: Path) -> None:
    """**Declarar** y **citar** no son lo mismo, y el guard lo aprendio en carne propia.

    `core/sala_lectura_estado.py` nacio en este mismo diff, explica en su docstring *por
    que* existe —«el boton llamaba a un modulo que se declara `[DEPRECADO 2026-06-18]`…»—
    y la primera version de este detector lo marco como deprecado. Un falso positivo que
    solo se quita mutilando una explicacion correcta es un detector mal apuntado.

    El criterio real del repo es posicional: la declaracion **abre** la docstring.
    `core/sala_lectura.py` empieza, literalmente, por `[DEPRECADO 2026-06-18]`, y asi lo
    describe tambien el runbook §7 («en la primera linea de su propio modulo»).
    """
    repo = _repo_sintetico(
        tmp_path,
        docstring_core=(
            "Modulo vivo que explica su origen.\n\n"
            "Sustituye al camino que se declara [DEPRECADO 2026-06-18] y no se amplia."
        ),
        fuente_ui="from core import probe\n",
    )
    assert deprecados_entre(repo, modulos_core_importados(repo / "app.py")) == {}


def test_mencionar_el_marcador_en_la_primera_linea_tampoco_es_declararlo(
    tmp_path: Path,
) -> None:
    """El marcador tiene que **abrir** la linea, no aparecer en ella.

    Este caso existe por un mutante que sobrevivio al arnes: cambiar `startswith` por
    `in` deja pasar toda la primera version del detector salvo esto. La frase es la que
    escribiria cualquier sustituto al presentarse.
    """
    repo = _repo_sintetico(
        tmp_path,
        docstring_core="Adaptador del motor [DEPRECADO 2026-06-18], al que sustituye.",
        fuente_ui="from core import probe\n",
    )
    assert deprecados_entre(repo, modulos_core_importados(repo / "app.py")) == {}


def test_un_marcador_en_el_cuerpo_no_declara_el_modulo(tmp_path: Path) -> None:
    """Un `# [DEPRECADO ...]` en un comentario suelto no depreca el modulo.

    Se mira la docstring y solo la docstring: si no, cualquier mencion del marcador
    —esta misma linea, sin ir mas lejos— deprecaria su fichero.
    """
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "core" / "probe.py").write_text(
        '"""Modulo vivo."""\n# [DEPRECADO 2026-01-01] esta funcion de aqui abajo\n'
        "def vieja():\n    pass\n",
        encoding="utf-8",
    )
    (tmp_path / "app.py").write_text("from core import probe\n", encoding="utf-8")
    assert deprecados_entre(tmp_path, modulos_core_importados(tmp_path / "app.py")) == {}
