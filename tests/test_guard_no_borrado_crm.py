"""Guarda dura: FeesDefender NO puede borrar en el CRM sudespacho por API.

Hoy no borra, pero **por casualidad**: nadie escribió el código. Esto lo convierte en
garantía. Es la misma «regla dura NO-BORRADO» que la spec del MCP sudespacho ya fija
(`docs/superpowers/specs/2026-07-13-mcp-sudespacho-design.md`), aplicada al código que
ya habla con el CRM — para que valga antes de que ese plugin exista.

Tres decisiones de diseño, cada una por un falso resultado que evita:

1. **Alcance por contenido, no por lista de ficheros.** Un módulo entra en la guarda
   si menciona el CRM (`sudespacho`, `api-crm`, `/api/element…`). Así
   `plugins/google_despacho_mcp/drive_ops.py`, que borra ficheros de **Google Drive**
   con `.delete()` legítimamente, queda fuera — y un módulo nuevo que hable con el CRM
   entra solo, sin tocar este test.
2. **No basta el verbo `DELETE`.** Este CRM borra también con POST:
   `POST /api/element_register/bulk-deletion/{element}` y
   `POST /api/taxes/bulk/delete/{ids}` (verificado contra `/api/docs.json`, 2026-08-03).
3. **`ast`, no grep.** `core/crm_atlas.py` tiene `HTTP_METHODS = (…, "delete")` para
   **parsear** el spec, y varios docstrings mencionan DELETE para documentar que no se
   usa. Un grep los marcaría. Aquí se ignoran docstrings y solo se miran llamadas
   reales y literales de método en mayúsculas.

⚠️ Alcance: protege el código de este repo. **No** protege de un script ad-hoc ni de
una clave filtrada; para eso hay que quitar `Delete` en los permisos del usuario API
(hoy ON en 123 de 198 elementos — ver `REFERENCIA_SUDESPACHO_API_PERMISOS.md §3`).
"""

from __future__ import annotations

import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIRECTORIOS = ("core", "scripts", "plugins")

MARCAS_CRM = ("sudespacho", "api-crm", "/api/element", "/api/relation_element")
RUTAS_QUE_BORRAN = ("bulk-deletion", "bulk/delete")


def _ficheros_py() -> list[Path]:
    salida: list[Path] = []
    for d in DIRECTORIOS:
        salida += sorted(RAIZ.joinpath(d).rglob("*.py"))
    return [f for f in salida if "__pycache__" not in f.parts]


def _ids_de_docstrings(arbol: ast.AST) -> set[int]:
    ids: set[int] = set()
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        cuerpo = getattr(nodo, "body", None) or []
        if (
            cuerpo
            and isinstance(cuerpo[0], ast.Expr)
            and isinstance(cuerpo[0].value, ast.Constant)
            and isinstance(cuerpo[0].value.value, str)
        ):
            ids.add(id(cuerpo[0].value))
    return ids


def _literales(arbol: ast.AST) -> list[ast.Constant]:
    docstrings = _ids_de_docstrings(arbol)
    return [
        n
        for n in ast.walk(arbol)
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstrings
    ]


def habla_con_el_crm(fuente: str) -> bool:
    """True si el módulo menciona el CRM en código (no en docstrings)."""
    arbol = ast.parse(fuente)
    return any(
        marca in n.value.lower() for n in _literales(arbol) for marca in MARCAS_CRM
    )


def infracciones(fuente: str, etiqueta: str) -> list[str]:
    """Infracciones de la regla de no-borrado. Vacío si el módulo no toca el CRM."""
    if not habla_con_el_crm(fuente):
        return []
    arbol = ast.parse(fuente)
    fallos: list[str] = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Attribute) and nodo.attr == "delete":
            fallos.append(f"{etiqueta}: llamada a `.delete(` (línea {nodo.lineno})")
    for n in _literales(arbol):
        if "DELETE" in n.value:
            fallos.append(f"{etiqueta}: literal 'DELETE' (línea {n.lineno})")
        for ruta in RUTAS_QUE_BORRAN:
            if ruta in n.value.lower():
                fallos.append(f"{etiqueta}: ruta de borrado {ruta!r} (línea {n.lineno})")
    return fallos


def test_ningun_modulo_del_crm_borra():
    fallos: list[str] = []
    for fichero in _ficheros_py():
        fallos += infracciones(
            fichero.read_text(encoding="utf-8"), fichero.relative_to(RAIZ).as_posix()
        )
    assert fallos == [], "FeesDefender no debe poder borrar en el CRM:\n  - " + "\n  - ".join(fallos)


def test_el_alcance_excluye_lo_que_no_es_el_crm():
    """Drive borra ficheros legítimamente: no puede caer en la guarda del CRM."""
    drive = RAIZ / "plugins" / "google_despacho_mcp" / "drive_ops.py"
    if drive.exists():
        fuente = drive.read_text(encoding="utf-8")
        assert not habla_con_el_crm(fuente), "drive_ops no debería mencionar el CRM"
        assert infracciones(fuente, "drive_ops.py") == []
    # y el cliente del CRM sí está dentro del alcance
    crm = RAIZ / "core" / "sync_sudespacho.py"
    assert habla_con_el_crm(crm.read_text(encoding="utf-8"))


def test_la_guarda_detecta_un_borrado_si_alguien_lo_introduce():
    """Verificación por mutación: si el defecto reaparece, esto debe cazarlo."""
    crm = '"""m."""\nBASE = "https://api-crm-commons-pro.sudespacho.biz"\n'
    assert infracciones(crm + 'r = cli.request("DELETE", u)\n', "x.py")
    assert infracciones(crm + "r = cli.delete(u)\n", "x.py")
    assert infracciones(crm + 'cli.post("/api/element_register/bulk-deletion/x")\n', "x.py")
    assert infracciones(crm + 'cli.post("/api/taxes/bulk/delete/1")\n', "x.py")
    # lo que NO debe cazar
    assert infracciones('"""No usamos DELETE."""\nX = "sudespacho"\n', "x.py") == []
    assert infracciones('svc.files().delete(id=1)\nY = "drive"\n', "x.py") == []
    assert infracciones(crm + 'METODOS = ("get", "post", "delete")\n', "x.py") == []
