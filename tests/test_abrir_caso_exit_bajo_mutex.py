"""Nadie termina el proceso mientras se sostiene el mutex del caso (`MEJORAS #142`).

**La propiedad, y por qué es de `typer.Exit` y no de cualquier excepción.** El `finally` de
`core.casos.case_mutex.tomado` **lanza** `MutexPerdido` si el bloque sale limpio y solo lo
**anota** si hay una excepción en vuelo. Eso está bien para un fallo genuino —el error del
cuerpo manda y la pérdida no se evapora, que es lo que R12/H12-04 diseñó—, pero con un
`typer.Exit` en vuelo falla dos veces:

- un `Exit(0)` es una terminación **con éxito** disfrazada de excepción, así que se anota
  una pérdida de exclusión sobre un éxito: la mentira que el mecanismo existe para evitar;
- y en cualquier `Exit`, Typer descarta el traceback al formatear la salida, con lo que la
  nota queda **invisible** incluso cuando el fallo es real.

Medido el 2026-09-03: había **nueve** salidas así, ocho en las funciones que el modo
`libre` invoca desde dentro del bloque y una —el `--dry-run`— literalmente dentro.

Este guard vigila la **frontera**, no los nueve ejemplos: mira el bloque y **también** las
funciones que se invocan desde él, así que el próximo `typer.Exit` que alguien ponga ahí
pone esto rojo sin que nadie tenga que acordarse.
"""
import ast
import inspect
import textwrap

import pytest

from scripts import abrir_caso as cli

#: Lo que `main` invoca desde DENTRO del bloque de mutex. Si mañana se invoca algo más,
#: se añade aquí — y el test de abajo comprueba que la lista no está vacía ni miente.
INVOCADAS_BAJO_MUTEX = (
    "_despachar_intake", "_intake_drive_ev", "_intake_manual", "_intake_whatsapp",
    "_intake_email", "_intake_generico", "_alta_crm", "_depositar_manual",
    "registrar_cierre_v1", "secuencia_v1", "etapa_drive", "etapa_crm",
    "etapa_sala_maquina",
)


def _arbol():
    return ast.parse(pathlib_read())


def pathlib_read():
    import pathlib
    return pathlib.Path(inspect.getsourcefile(cli)).read_text(encoding="utf-8")


def _exits(nodo):
    return [n for n in ast.walk(nodo)
            if isinstance(n, ast.Raise) and "Exit" in ast.dump(n)]


def test_ningun_exit_dentro_del_bloque_de_mutex():
    """El `--dry-run` era el peor: un `Exit(0)` bajo exclusión."""
    main = next(n for n in ast.walk(_arbol())
                if isinstance(n, ast.FunctionDef) and n.name == "main")
    withs = [w for w in ast.walk(main) if isinstance(w, ast.With)]
    assert withs, "el cuerpo de main ya no tiene el bloque de mutex: revisar este guard"
    dentro = [e.lineno for w in withs for e in _exits(w)]
    assert dentro == [], (
        f"hay typer.Exit dentro del bloque de mutex, lineas {dentro}: una terminacion "
        "del proceso ahi dentro convierte una perdida del lease en una nota que Typer "
        "descarta. Marca y sal FUERA del bloque, o lanza AbortarApertura.")


@pytest.mark.parametrize("nombre", INVOCADAS_BAJO_MUTEX)
def test_ninguna_funcion_invocada_bajo_el_mutex_termina_el_proceso(nombre):
    """La mitad que se me olvidó al remediar la rama `v1`: ocho de las nueve salidas no
    estaban en el bloque sino en las funciones que el bloque llama."""
    fn = next((n for n in ast.walk(_arbol())
               if isinstance(n, ast.FunctionDef) and n.name == nombre), None)
    if fn is None:
        pytest.skip(f"{nombre} ya no existe en el modulo")
    dentro = [e.lineno for e in _exits(fn)]
    assert dentro == [], (
        f"{nombre} lanza typer.Exit (lineas {dentro}) y se invoca sosteniendo el mutex: "
        "usa AbortarApertura y deja que el entrypoint decida terminar el proceso.")


def test_este_guard_no_esta_vacio():
    """Hermano de los guards de este repo: si la lista quedara vacía o los nombres no
    existieran, los parametrizados de arriba pasarían sin mirar nada."""
    arbol = _arbol()
    definidas = {n.name for n in ast.walk(arbol) if isinstance(n, ast.FunctionDef)}
    vivas = [n for n in INVOCADAS_BAJO_MUTEX if n in definidas]
    assert len(vivas) >= 10, (
        f"solo {len(vivas)} de las {len(INVOCADAS_BAJO_MUTEX)} funciones vigiladas existen; "
        "el guard esta mirando nombres que ya no estan")


def test_abortar_apertura_lleva_el_codigo_y_no_termina_el_proceso():
    """`AbortarApertura` es la alternativa: dice el código y NO decide terminar."""
    exc = cli.AbortarApertura(1)
    assert exc.codigo == 1
    assert not isinstance(exc, SystemExit), (
        "AbortarApertura no puede ser un SystemExit: entonces seria lo mismo que el "
        "typer.Exit que viene a sustituir")
