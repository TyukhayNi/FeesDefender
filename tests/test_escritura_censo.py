"""El trinquete del write-set — Plan 3A, Task 7. Censo (b) del §4 del plan.

Dos guards permanentes y un contador con techo:

1. **Producción entra por `mutex_sesion`**, no por `case_mutex.tomado`/`adquirir` en crudo.
   Sin esto, la reentrancia se puede rodear sin querer y dos etapas de la misma corrida
   sostendrían leases distintos sobre el mismo caso.
2. **El censo de escrituras que no pasan por la costura solo puede BAJAR.** No es una
   prohibición —hoy son casi todas— es un trinquete: 3B y 3C lo bajan, y nada lo sube.

**Lo que este censo NO prueba, dicho aquí y no en una nota al pie:** mide **llamadas**, no
flujo de datos. Un llamador que use la costura y luego escriba por su cuenta lo pasa. Eso
lo cierran las pruebas por fila del §25.4, no un contador — y por eso el criterio de salida
de 3A exige las dos cosas.
"""
from __future__ import annotations

import ast
import io
from pathlib import Path

import pytest

#: Los 11 productores que la tabla del §25 nombra. La lista es explícita a propósito: un
#: barrido de `core/**` crecería en silencio y el número dejaría de comparar lo mismo.
PRODUCTORES = (
    "core/case_manager.py", "core/intake_drive.py", "core/intake_manifest.py",
    "core/intake_log.py", "core/sync_sudespacho.py",
    "core/email_atomize/pipeline.py", "core/adjuntos_contenido/pipeline.py",
    "core/sala_maquina.py", "core/split_documental.py",
    "scripts/abrir_caso.py", "scripts/sala_maquina.py",
)

#: Las primitivas del barrido del §25.
PRIMITIVAS = frozenset({
    "write_text", "write_bytes", "mkdir", "unlink", "replace", "copy2", "copy",
    "dump", "append_event",
})

#: **Techo del censo, medido el 2026-08-26. Solo puede bajar.**
#:
#: 93 sitios de escritura en los 11 productores, y **cero** ficheros entrando por la
#: costura. Bajarlo es el trabajo de 3B (los derivados) y 3C (la poda). Si un cambio lo
#: sube, o es una escritura nueva sin costura —y entonces falta migrarla— o la lista de
#: productores creció y hay que decirlo, no absorberlo.
TECHO_CENSO = 93


def _nombre_llamado(n: ast.Call) -> str | None:
    f = n.func
    if isinstance(f, ast.Attribute):
        return f.attr
    if isinstance(f, ast.Name):
        return f.id
    return None


def _es_escritura(n: ast.Call) -> bool:
    nombre = _nombre_llamado(n)
    if nombre in PRIMITIVAS:
        return True
    if nombre == "open":
        modos = [a.value for a in n.args
                 if isinstance(a, ast.Constant) and isinstance(a.value, str)]
        return any("a" in m or "w" in m for m in modos)
    return False


def censar(ruta: str | Path) -> tuple[int, bool]:
    """`(sitios de escritura, entra por la costura)`.

    El import se detecta por **AST**, nunca por subcadena. Contarlo por texto es cómo se
    cuelan los falsos positivos: al escribir este censo la primera vez, `"casos.escritura"
    in texto` casó con un **comentario** en el que yo mismo nombraba el módulo, y el
    fichero salió declarado como migrado sin haberlo migrado. Es literalmente el defecto
    que R10/H10-10 castigó con `filelock` en este repo.
    """
    arbol = ast.parse(io.open(ruta, encoding="utf-8").read(), filename=str(ruta))
    sitios, usa_costura = 0, False
    for n in ast.walk(arbol):
        if isinstance(n, ast.ImportFrom):
            mod = n.module or ""
            if mod.endswith("casos.escritura"):
                usa_costura = True
            elif mod.endswith("casos") and any(a.name == "escritura" for a in n.names):
                usa_costura = True
        elif isinstance(n, ast.Import):
            if any(a.name.endswith("casos.escritura") for a in n.names):
                usa_costura = True
        elif isinstance(n, ast.Call) and _es_escritura(n):
            sitios += 1
    return sitios, usa_costura


# ------------------------------------------------------- el detector no es vacuo

def test_el_detector_encuentra_lo_que_dice_encontrar(tmp_path):
    """Prueba de que el censo MUERDE. Un guard sin esto es una intención.

    Se le da un fichero con una escritura de cada forma y se comprueba que las cuenta
    todas; y uno con solo lecturas, para que un detector que devolviera un número
    constante no pasara.
    """
    escribe = tmp_path / "escribe.py"
    escribe.write_text(
        "from pathlib import Path\n"
        "import json\n"
        "def f(p, d):\n"
        "    Path(p).write_text('x')\n"
        "    Path(p).write_bytes(b'x')\n"
        "    Path(p).mkdir()\n"
        "    Path(p).unlink()\n"
        "    json.dump(d, open(p, 'w'))\n"
        "    open(p, 'a').close()\n",
        encoding="utf-8")
    sitios, usa = censar(escribe)
    assert sitios == 7, f"el detector no ve todas las formas de escritura: {sitios}"
    assert usa is False

    lee = tmp_path / "lee.py"
    lee.write_text(
        "from pathlib import Path\n"
        "def f(p):\n"
        "    return Path(p).read_text() + open(p, 'r').read()\n",
        encoding="utf-8")
    assert censar(lee) == (0, False), "el detector cuenta lecturas como escrituras"


def test_el_detector_no_se_cree_un_comentario(tmp_path):
    """El falso positivo REAL que tuvo la primera versión de este censo.

    Un fichero que solo *nombra* la costura en un comentario o en una cadena no la usa.
    """
    f = tmp_path / "solo_la_menciona.py"
    f.write_text(
        "# este modulo no puede pasar por core.casos.escritura todavia\n"
        "DOC = 'ver core.casos.escritura'\n"
        "from pathlib import Path\n"
        "def g(p):\n"
        "    Path(p).write_text('x')\n",
        encoding="utf-8")
    sitios, usa = censar(f)
    assert sitios == 1
    assert usa is False, (
        "el detector se creyó un comentario: es el defecto que R10/H10-10 castigó con "
        "`filelock`, y en el que caí al escribir este mismo censo")


# ------------------------------------------------------------------ el trinquete

def test_el_censo_solo_baja():
    """El techo del §4(b). Si sube, o falta migrar algo o la lista creció en silencio."""
    detalle = {p: censar(p)[0] for p in PRODUCTORES}
    total = sum(detalle.values())
    assert total <= TECHO_CENSO, (
        f"el censo de escrituras fuera de la costura SUBIÓ a {total} (techo "
        f"{TECHO_CENSO}). Reparto: {detalle}. O hay una escritura nueva sin migrar, o la "
        f"lista de productores creció y eso se declara, no se absorbe")


def test_el_techo_no_esta_holgado():
    """Que el techo sea el número REAL, no uno cómodo.

    Un techo por encima del censo deja sitio para que entren escrituras nuevas sin que
    nadie se entere — que es exactamente lo contrario de un trinquete.
    """
    total = sum(censar(p)[0] for p in PRODUCTORES)
    assert total == TECHO_CENSO, (
        f"el censo real es {total} y el techo dice {TECHO_CENSO}: si acabas de migrar "
        f"algo, BAJA el techo en el mismo commit")


# ---------------------------------------------- produccion entra por mutex_sesion

def test_produccion_no_llama_a_la_primitiva_en_crudo():
    """Guard permanente: `case_mutex.tomado`/`adquirir` no se llaman fuera de su capa.

    `mutex_sesion` es la única que puede, porque es la que implementa la reentrancia. Si
    otro sitio adquiriera en crudo, el anidamiento dejaría de ser un no-op revalidado y
    volvería a ser un `CaseBusy` contra uno mismo — el defecto que el Task 1 cierra.
    """
    exentos = {"mutex_sesion.py", "case_mutex.py"}
    infractores = []
    for base in ("core", "scripts"):
        for p in sorted(Path(base).rglob("*.py")):
            if p.name in exentos:
                continue
            arbol = ast.parse(io.open(p, encoding="utf-8").read(), filename=str(p))
            for n in ast.walk(arbol):
                if isinstance(n, ast.Call) and _nombre_llamado(n) in ("tomado", "adquirir"):
                    infractores.append(f"{p.as_posix()}:{n.lineno}")
    assert not infractores, (
        "producción llama a la primitiva del mutex en crudo, saltándose la reentrancia:\n  "
        + "\n  ".join(infractores))


@pytest.mark.parametrize("entrypoint", ["scripts/abrir_caso.py", "scripts/sala_maquina.py"])
def test_los_entrypoints_cableados_siguen_adquiriendo(entrypoint):
    """Trinquete de lo ya cableado: quien adquiere hoy no puede dejar de hacerlo.

    Es la regresión que nadie nota, porque quitar el `with` no rompe ninguna prueba
    funcional: simplemente se deja de proteger. Por eso el guard es estructural.
    """
    arbol = ast.parse(io.open(entrypoint, encoding="utf-8").read(), filename=entrypoint)
    assert any(isinstance(n, ast.Call) and _nombre_llamado(n) == "sostenido"
               for n in ast.walk(arbol)), (
        f"{entrypoint} ya no adquiere el mutex: el cableado del Task 5 se perdió")
