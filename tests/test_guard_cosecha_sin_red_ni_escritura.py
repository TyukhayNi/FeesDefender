"""Los dos guards de F2: nadie alcanza el CRM real, nadie escribe en el árbol real.

Son dos riesgos distintos y ninguno lo cubría F1:

1. **Red.** `core/sudespacho_documentos.py` resuelve su transporte con `cliente or`
   una llamada al cliente real, igual que `core/codicert.py`. Un test que olvide
   `cliente=` alcanza el CRM de producción — y este módulo **escribe**, así que el
   descuido no es «un GET de más»: es un documento creado en un expediente real.
   Es el hallazgo H-13 de la R2 de F1 en su versión cara, así que se cierra con el
   mismo patrón: una BARRERA de ejecución, no un barrido de texto.
2. **Disco.** `cosechar` es la primera función del proyecto que escribe PDFs en el
   árbol de un caso. La regla de `CLAUDE.md` §Tests no tiene escotilla, y el único
   camino por el que un test podría romperla es construir `EntornoExpedicion` sin
   `carpeta_certificados`, cayendo en el default que resuelve contra `CASOS_ROOT`.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent
_ESTE_FICHERO = Path(__file__).name


# --- 1. Red ----------------------------------------------------------------

def test_la_BARRERA_muerde_cuando_se_olvida_el_cliente(monkeypatch):
    """El control que hace de esto un instrumento: se le da el otro valor.

    Se llama a la API pública SIN `cliente=`, que es la forma ordinaria de llegar a
    la red y la que un barrido de texto no puede ver. Con la barrera instalada por
    la fixture `autouse`, la llamada tiene que morir ANTES de importar `httpx`.

    **La clave sintética no es decorado** (hallazgo H-08 de la R1): sin ella, el
    control depende de que la máquina tenga `SUDESPACHO_API_KEY` puesta. En este PC
    la tiene y el test pasaba; en una limpia —o en CI— muere en `_api_key()` **sin
    llegar a tocar la barrera**, así que el control quedaba verde sin probar nada
    allí donde más falta hace. Ninguna credencial real interviene.
    """
    from core import sudespacho_documentos as doc
    from tests import _barrera_sudespacho_documentos as barrera

    monkeypatch.setenv("SUDESPACHO_API_KEY", "clave-sintetica-de-guard")
    with pytest.raises(barrera.BarreraSudespachoViolada):
        doc.descargar_documento("42990")


def test_sin_API_KEY_se_para_ANTES_de_la_red_y_ese_orden_es_el_bueno(monkeypatch):
    """El otro lado de H-08, que conviene fijar como comportamiento y no como azar.

    Con la variable ausente, la llamada muere en la comprobación de la clave y no
    llega al transporte. Es lo correcto —no se intenta nada sin credencial— pero
    significa que ese camino **no ejerce la barrera**, y por eso el control de
    arriba tiene que fijar una clave. Escrito aquí para que quien lea los dos sepa
    que la diferencia es deliberada.
    """
    from core import sudespacho_documentos as doc

    monkeypatch.delenv("SUDESPACHO_API_KEY", raising=False)
    with pytest.raises(doc.SudespachoDocumentosError, match="SUDESPACHO_API_KEY"):
        doc.descargar_documento("42990")


def test_solo_hay_una_puerta_de_red_en_el_modulo():
    """Misma disciplina que `core/codicert.py`: un único sitio que importe httpx.

    Si apareciera un segundo `import httpx`, la barrera —que sustituye un solo
    binding— dejaría de cubrir el módulo entero sin que nada lo avisara.
    """
    fuente = (RAIZ.parent / "core" / "sudespacho_documentos.py").read_text(
        encoding="utf-8")
    assert fuente.count("import httpx") == 1


def _ficheros_del_gestor() -> list[Path]:
    """Ficheros de test que mencionan el módulo del gestor documental."""
    return [f for f in sorted(RAIZ.rglob("*.py"))
            if f.name != _ESTE_FICHERO
            and "sudespacho_documentos" in f.read_text(encoding="utf-8",
                                                       errors="replace")]


def test_el_censo_del_gestor_no_esta_vacio():
    """El guard se comprueba a sí mismo: un censo vacío pasaría siempre."""
    assert _ficheros_del_gestor(), "el censo del gestor documental está vacío"


def _importa_httpx(fuente: str) -> bool:
    """¿El fichero IMPORTA httpx, de verdad?

    Por AST y no por `"import httpx" in texto`, y la diferencia no es estética: la
    primera versión de este guard dio rojo sobre `_barrera_sudespacho_documentos.py`,
    cuyo docstring **explica** que la barrera cierra el paso «antes de que el
    `import httpx` llegue a ejecutarse». Un guard que confunde la prosa que describe
    un riesgo con el riesgo mismo empuja a excluir el fichero por su nombre — y así
    el único fichero excluido acaba siendo justo el que más conviene vigilar.
    """
    for nodo in ast.walk(ast.parse(fuente)):
        if isinstance(nodo, ast.Import):
            if any(a.name.split(".")[0] == "httpx" for a in nodo.names):
                return True
        elif isinstance(nodo, ast.ImportFrom):
            if (nodo.module or "").split(".")[0] == "httpx":
                return True
    return False


def test_ningun_test_del_gestor_importa_httpx_por_su_cuenta():
    """El hueco que la barrera NO puede cerrar, y por eso hace falta este check.

    La barrera sustituye el binding DEL MÓDULO: cubre a quien llegue a la red *por*
    `core.sudespacho_documentos`. Un test que importara `httpx` directamente y
    llamara al CRM por su cuenta la rodearía entera. Son dos controles distintos
    sobre el mismo riesgo, y ninguno sustituye al otro.
    """
    malos = {f.name for f in _ficheros_del_gestor()
             if _importa_httpx(f.read_text(encoding="utf-8", errors="replace"))}
    assert not malos, f"importan httpx directamente: {sorted(malos)}"


def test_el_detector_de_import_distingue_el_CODIGO_de_la_PROSA():
    """El otro valor del propio detector, que es lo que lo hace fiable."""
    assert _importa_httpx("import httpx\n")
    assert _importa_httpx("from httpx import Client\n")
    assert not _importa_httpx('"""habla de import httpx en su docstring."""\n')
    assert not _importa_httpx('x = "import httpx"\n')


# --- 2. Disco --------------------------------------------------------------

def _ficheros_de_cosecha() -> list[Path]:
    """Los tests que ejercitan `cosechar`, por nombre o por contenido."""
    censo = []
    for f in sorted(RAIZ.rglob("*.py")):
        if f.name == _ESTE_FICHERO:
            continue
        txt = f.read_text(encoding="utf-8", errors="replace")
        if "cosechar(" in txt or "CertificadoCosechado" in txt:
            censo.append(f)
    return censo


def test_el_censo_no_esta_vacio():
    """Un guard sobre cero ficheros pasa siempre y no prueba nada."""
    assert _ficheros_de_cosecha(), "no se encontró ningún test de cosecha que vigilar"


def _entornos_sin_carpeta(fuente: str) -> list[int]:
    """Líneas donde se construye `EntornoExpedicion` sin `carpeta_certificados`."""
    return [n.lineno for n in ast.walk(ast.parse(fuente))
            if isinstance(n, ast.Call)
            and getattr(n.func, "attr", None) == "EntornoExpedicion"
            and "carpeta_certificados" not in {k.arg for k in n.keywords}]


def test_ningun_test_de_cosecha_construye_el_entorno_sin_carpeta():
    """Y si lo hace, es a propósito y lo dice: la marca `# entorno-sin-cosecha`.

    Hay un caso legítimo —el test que comprueba que `cosechar` PARA ante un entorno
    de F1 sin los puertos de escritura—, y una excepción silenciosa sería
    indistinguible de un olvido. Se declara en la línea.
    """
    fallos = []
    for fichero in _ficheros_de_cosecha():
        lineas = fichero.read_text(encoding="utf-8").splitlines()
        for numero in _entornos_sin_carpeta("\n".join(lineas)):
            # la marca puede ir en la línea de apertura o en cualquiera de la llamada
            ventana = "\n".join(lineas[numero - 1:numero + 6])
            if "entorno-sin-cosecha" not in ventana:
                fallos.append(f"{fichero.name}:{numero}")
    assert not fallos, (
        "estos `EntornoExpedicion` de tests de cosecha no fijan "
        f"`carpeta_certificados` y escribirían en CASOS_ROOT: {fallos}. Si es "
        "deliberado, márcalo con `# entorno-sin-cosecha` y su porqué.")


def test_el_guard_de_disco_MUERDE_sobre_una_sonda(tmp_path):
    """El otro valor, también para este: se le presenta código con el defecto."""
    con_defecto = "exp.EntornoExpedicion(codicert=None, raiz=None)\n"
    sin_defecto = "exp.EntornoExpedicion(codicert=None, carpeta_certificados=f)\n"
    assert _entornos_sin_carpeta(con_defecto) == [1]
    assert _entornos_sin_carpeta(sin_defecto) == []
