"""Inventario AST de los llamadores del localizador de casos (Fase 1, Task 6, Step 0).

Es a la vez **la lista de trabajo de la migración** y **el insumo del guard** que
impide que la escotilla legacy crezca. Por eso vive versionado en el repo y no en un
scratchpad: un inventario que se recalcula a mano no puede ser la base de un guard.

## Por qué AST y no `grep`

Porque `grep` no mide llamadas. La R7 (hallazgo **H7-14**) pilló que el plan decía «los
llaman 80 ficheros», y ese 80 es el número de ficheros que **mencionan** la subcadena:
imports, comentarios, docstrings y 25 ficheros de test incluidos. Contando nodos
`ast.Call` la superficie real es de **43 ficheros de producción**. La diferencia no es
cosmética: era el doble del trabajo estimado, y una estimación mala en el task de más
riesgo del plan.

## Las tres intenciones

El Task 6 separa lo que un booleano `strict` mezclaba (R7/H7-01):

- `localizar()` — lo que debe existir; **lanza** si falta.
- `buscar()` — preguntar si existe; devuelve `None`.
- `destino_de_alta()` — nombrar el destino de un alta; su caso normal es que no exista.

Este script **propone** una intención por sitio de llamada mirando qué hace el código con
la ruta. Es una **heurística deliberadamente conservadora**: lo que no distingue con
claridad va a `REVISAR` en vez de a un cubo cómodo. La clasificación final la firma una
persona; lo que el script garantiza es que **ningún sitio se queda fuera de la lista**.

Uso:

    .\\.venv\\Scripts\\python.exe -m scripts.inventario_localizador
    .\\.venv\\Scripts\\python.exe -m scripts.inventario_localizador --json
"""
from __future__ import annotations

import argparse
import ast
import io
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

#: Los dos símbolos que resuelven la ruta de un caso.
SIMBOLOS = ("path_for", "caso_path")

#: Raíces de producción y de test. `streamlit_app.py` es producción y vive en la raíz.
RAICES_PRODUCCION = ("core", "scripts")
SUELTOS_PRODUCCION = ("streamlit_app.py",)
RAICES_TEST = ("tests",)

#: Ventana de líneas que se mira tras la llamada para proponer la intención.
_VENTANA = 12

# Lo que delata cada intención. Conservador a propósito: si hay señales de dos
# intenciones, el sitio va a REVISAR y lo firma una persona.
_ESCRIBE = (".mkdir(", ".write_text(", ".write_bytes(", ".touch(", "shutil.copy",
            "shutil.move", "shutil.rmtree", "os.replace", "ensure_dir")
_PREGUNTA_NEGADA = ("if not ", "is None", "== False")
_COMPRUEBA = (".exists()", ".is_dir()", ".is_file()")

LOCALIZAR = "localizar"
BUSCAR = "buscar"
DESTINO = "destino_de_alta"
REVISAR = "REVISAR"


@dataclass(frozen=True)
class Sitio:
    """Un sitio de llamada, con la intención que se le propone."""

    fichero: str
    linea: int
    simbolo: str
    ambito: str          # "produccion" | "test"
    propuesta: str       # LOCALIZAR | BUSCAR | DESTINO | REVISAR
    motivo: str


class _Visitante(ast.NodeVisitor):
    """Recoge las llamadas y **la funcion que las envuelve**.

    La envolvente hace falta porque la senal de `destino_de_alta` es estar DENTRO de
    `ensure_case`, y una ventana que empieza en la linea de la llamada no ve nunca su
    propio `def`. Lo pillo un test del inventario antes de que su salida se usara
    para nada, que es exactamente para lo que estaba escrito ese test.
    """

    def __init__(self) -> None:
        self.llamadas: list[tuple[str, int, str]] = []
        self._pila: list[str] = []

    def _funcion(self, node):
        self._pila.append(node.name)
        self.generic_visit(node)
        self._pila.pop()

    visit_FunctionDef = _funcion
    visit_AsyncFunctionDef = _funcion

    def visit_Call(self, node: ast.Call) -> None:
        f = node.func
        nombre = f.id if isinstance(f, ast.Name) else (
            f.attr if isinstance(f, ast.Attribute) else None)
        if nombre in SIMBOLOS:
            self.llamadas.append(
                (nombre, node.lineno, self._pila[-1] if self._pila else ""))
        self.generic_visit(node)



def _es_definicion(linea: str) -> bool:
    return linea.lstrip().startswith("def ") and any(
        f"def {s}" in linea for s in SIMBOLOS)


def _proponer(ventana: str, envolvente: str = "") -> tuple[str, str]:
    """Propone una intención para un sitio, o REVISAR. Nunca adivina en silencio."""
    escribe = any(t in ventana for t in _ESCRIBE)
    comprueba = any(t in ventana for t in _COMPRUEBA)
    negada = any(t in ventana for t in _PREGUNTA_NEGADA)

    if envolvente == "ensure_case":
        # SOLO la funcion envolvente, que sale del AST. La clausula anterior
        # aceptaba tambien `"ensure_case" in ventana`, y eso clasificaba como
        # puerta de alta tres sitios de `case_manager` que viven en
        # `register_expediente` y `register_drive_ev` y solo la MENCIONAN en un
        # comentario. Un falso positivo en un cubo confiado es peor que un cubo
        # REVISAR grande: el segundo pide una lectura, el primero deja el
        # fallback donde no toca y nadie vuelve a mirarlo.
        return DESTINO, "esta dentro de ensure_case: es la puerta de alta"
    if comprueba and negada and not escribe:
        return BUSCAR, "comprueba la ausencia y sigue: detector con rama elegante"
    if escribe and not comprueba:
        return LOCALIZAR, "escribe sin comprobar: exige que el caso exista"
    if comprueba and not escribe and not negada:
        return LOCALIZAR, "lee un caso que da por existente"
    if escribe and comprueba:
        return REVISAR, "escribe Y comprueba: la intencion no es inequivoca"
    return REVISAR, "ni escribe ni comprueba en la ventana: hay que leerlo"


def _ficheros(raiz_repo: Path) -> list[tuple[Path, str]]:
    salida: list[tuple[Path, str]] = []
    for d in RAICES_PRODUCCION:
        salida += [(p, "produccion") for p in sorted((raiz_repo / d).rglob("*.py"))]
    for f in SUELTOS_PRODUCCION:
        if (raiz_repo / f).is_file():
            salida.append((raiz_repo / f, "produccion"))
    for d in RAICES_TEST:
        salida += [(p, "test") for p in sorted((raiz_repo / d).rglob("*.py"))]
    return [(p, a) for p, a in salida if "__pycache__" not in p.parts]


def inventariar(raiz_repo: Path) -> list[Sitio]:
    """Todos los sitios de llamada a `path_for`/`caso_path`, con intención propuesta."""
    sitios: list[Sitio] = []
    for ruta, ambito in _ficheros(raiz_repo):
        texto = io.open(ruta, encoding="utf-8", errors="replace").read()
        if not any(s in texto for s in SIMBOLOS):
            continue
        try:
            arbol = ast.parse(texto)
        except SyntaxError:
            continue                       # fichero no parseable: no es un llamador
        v = _Visitante()
        v.visit(arbol)
        if not v.llamadas:
            continue
        lineas = texto.split("\n")
        rel = ruta.relative_to(raiz_repo).as_posix()
        for simbolo, lineno, envolvente in v.llamadas:
            i = lineno - 1
            if i < len(lineas) and _es_definicion(lineas[i]):
                continue
            ventana = "\n".join(lineas[i:i + _VENTANA])
            propuesta, motivo = _proponer(ventana, envolvente)
            sitios.append(Sitio(rel, lineno, simbolo, ambito, propuesta, motivo))
    return sitios


def resumen(sitios: list[Sitio]) -> dict:
    prod = [s for s in sitios if s.ambito == "produccion"]
    return {
        "llamadas_total": len(sitios),
        "llamadas_produccion": len(prod),
        "ficheros_total": len({s.fichero for s in sitios}),
        "ficheros_produccion": len({s.fichero for s in prod}),
        "por_propuesta": {
            b: len([s for s in prod if s.propuesta == b])
            for b in (LOCALIZAR, BUSCAR, DESTINO, REVISAR)
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true", help="volcado completo en JSON")
    args = ap.parse_args(argv)

    raiz = Path(__file__).resolve().parents[1]
    sitios = inventariar(raiz)
    r = resumen(sitios)

    if args.json:
        print(json.dumps({"resumen": r, "sitios": [asdict(s) for s in sitios]},
                         ensure_ascii=False, indent=2))
        return 0

    print(f"{r['llamadas_total']} llamadas en {r['ficheros_total']} ficheros "
          f"({r['llamadas_produccion']} en {r['ficheros_produccion']} de produccion)\n")
    print("Intencion propuesta para los sitios de PRODUCCION:")
    for cubo, n in r["por_propuesta"].items():
        print(f"  {n:>3}  {cubo}")
    print("\nLos de REVISAR no son un residuo: son los que una persona debe leer.")
    print("La heuristica manda a REVISAR lo dudoso en vez de repartirlo por comodidad.\n")
    for s in sitios:
        if s.ambito == "produccion" and s.propuesta == REVISAR:
            print(f"  {s.fichero}:{s.linea}  ({s.simbolo})  — {s.motivo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
