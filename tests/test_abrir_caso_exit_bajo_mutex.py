"""Nadie termina el proceso mientras se sostiene el mutex del caso (`MEJORAS #142`).

**La propiedad, y por qué es de la TERMINACIÓN y no de cualquier excepción.** El `finally` de
`core.casos.case_mutex.tomado` **lanza** `MutexPerdido` si el bloque sale limpio y solo lo
**anota** si hay una excepción en vuelo. Eso está bien para un fallo genuino —el error del
cuerpo manda y la pérdida no se evapora, que es lo que R12/H12-04 diseñó—, pero con una
terminación del proceso en vuelo falla dos veces:

- un `Exit(0)` es una terminación **con éxito** disfrazada de excepción, así que se anota
  una pérdida de exclusión sobre un éxito: la mentira que el mecanismo existe para evitar;
- y en cualquier `Exit`/`Abort`, Typer descarta el traceback al formatear la salida, con lo
  que la nota queda **invisible** incluso cuando el fallo es real.

Peor aún, `os._exit` no ejecuta ni el `finally`: no libera el lock ni diagnostica nada.

Medido el 2026-09-03: había **nueve** salidas así, ocho en funciones que el modo `libre`
invoca desde dentro del bloque y una —el `--dry-run`— literalmente dentro.

## Dos cosas que este guard aprendió de su propia revisión

La primera versión **mantenía la lista de funciones vigiladas a mano** y solo reconocía
`typer.Exit`. La ronda de revisión midió las dos consecuencias con mutaciones en memoria:
un `sys.exit(77)` o un `raise typer.Abort()` dentro de `_alta_crm` dejaban el guard en
**verde**, y la lista de 13 nombres se había quedado corta frente a las 17 funciones que el
bloque alcanza de verdad —además de tolerar tres nombres muertos como `skip`—.

Así que ahora:

- **el cierre de funciones se DERIVA** del cuerpo del `with` por recorrido transitivo, en
  vez de escribirse a mano. Una lista a mano es una lista que se queda corta;
- **se reconocen todas las formas de terminar**, como `raise` y como llamada;
- **un nombre que no existe FALLA**, no se salta.
"""
import ast
import inspect
import pathlib

import pytest

from scripts import abrir_caso as cli

#: Terminaciones prohibidas bajo el mutex, por su nombre cualificado o simple.
#: `os._exit` está a propósito: es la peor de todas, porque no ejecuta el `finally` que
#: libera el lock ni el que diagnostica la pérdida.
TERMINACIONES = frozenset({
    "sys.exit", "os._exit", "exit", "quit",
    "typer.Exit", "typer.Abort", "click.Abort", "click.exceptions.Exit",
    "Exit", "Abort", "SystemExit",
})


def _fuente() -> str:
    return pathlib.Path(inspect.getsourcefile(cli)).read_text(encoding="utf-8")


def _arbol(fuente: str | None = None):
    return ast.parse(fuente if fuente is not None else _fuente())


def _cualificado(nodo) -> str | None:
    """`sys.exit` para un `Attribute`, `Exit` para un `Name`. `None` si no es ninguno."""
    if isinstance(nodo, ast.Name):
        return nodo.id
    if isinstance(nodo, ast.Attribute):
        base = _cualificado(nodo.value)
        return f"{base}.{nodo.attr}" if base else nodo.attr
    return None


def _es_terminacion(nombre: str | None) -> bool:
    if not nombre:
        return False
    # Se mira el cualificado y también el último segmento: `typer.Exit` y un `Exit`
    # importado directamente son la misma cosa para esta propiedad.
    return nombre in TERMINACIONES or nombre.rsplit(".", 1)[-1] in TERMINACIONES


def terminaciones_en(nodo) -> list[tuple[int, str]]:
    """Todas las terminaciones del proceso dentro de `nodo`, como `raise` y como llamada."""
    hallazgos: list[tuple[int, str]] = []
    for n in ast.walk(nodo):
        if isinstance(n, ast.Raise) and n.exc is not None:
            objetivo = n.exc.func if isinstance(n.exc, ast.Call) else n.exc
            nombre = _cualificado(objetivo)
            if _es_terminacion(nombre):
                hallazgos.append((n.lineno, f"raise {nombre}"))
        elif isinstance(n, ast.Call):
            nombre = _cualificado(n.func)
            if _es_terminacion(nombre):
                hallazgos.append((n.lineno, f"{nombre}()"))
    return hallazgos


def _definidas(arbol) -> dict[str, ast.FunctionDef]:
    return {n.name: n for n in ast.walk(arbol)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def _llamadas_locales(nodo, definidas) -> set[str]:
    nombres = set()
    for n in ast.walk(nodo):
        if isinstance(n, ast.Call):
            nombre = _cualificado(n.func)
            if nombre in definidas:
                nombres.add(nombre)
    return nombres


def cierre_bajo_mutex(fuente: str | None = None) -> tuple[list, set[str]]:
    """Los `with` de `main` y el cierre TRANSITIVO de funciones locales que alcanzan.

    Derivado, no escrito a mano: es la corrección del hallazgo HD-02 de su revisión.
    """
    arbol = _arbol(fuente)
    definidas = _definidas(arbol)
    main = definidas["main"]
    withs = [w for w in ast.walk(main) if isinstance(w, ast.With)]

    pendientes = set()
    for w in withs:
        for hijo in w.body:
            pendientes |= _llamadas_locales(hijo, definidas)

    vistas: set[str] = set()
    while pendientes:
        nombre = pendientes.pop()
        if nombre in vistas:
            continue
        vistas.add(nombre)
        pendientes |= _llamadas_locales(definidas[nombre], definidas) - vistas
    return withs, vistas


def test_ninguna_terminacion_dentro_del_bloque_de_mutex():
    """El `--dry-run` era el peor de los nueve: un `Exit(0)` bajo exclusión."""
    withs, _ = cierre_bajo_mutex()
    assert withs, "el cuerpo de main ya no tiene el bloque de mutex: revisar este guard"
    dentro = [h for w in withs for h in terminaciones_en(w)]
    assert dentro == [], (
        f"hay terminaciones del proceso dentro del bloque de mutex: {dentro}. Una "
        "terminación ahí dentro convierte una pérdida del lease en una nota que Typer "
        "descarta. Marca y sal FUERA del bloque, o lanza AbortarApertura.")


def test_ninguna_funcion_alcanzada_bajo_el_mutex_termina_el_proceso():
    """La mitad que se me olvidó al remediar la rama `v1`: ocho de las nueve salidas no
    estaban en el bloque sino en las funciones que el bloque alcanza —algunas a dos y tres
    saltos, que es justo lo que una lista a mano no cubre."""
    _, alcanzadas = cierre_bajo_mutex()
    arbol = _arbol()
    definidas = _definidas(arbol)

    culpables = {}
    for nombre in sorted(alcanzadas):
        hallazgos = terminaciones_en(definidas[nombre])
        if hallazgos:
            culpables[nombre] = hallazgos
    assert culpables == {}, (
        f"estas funciones se alcanzan sosteniendo el mutex y terminan el proceso: "
        f"{culpables}. Usa AbortarApertura y deja que el entrypoint decida.")


def test_el_cierre_derivado_no_esta_vacio_ni_es_trivial():
    """Si el recorrido devolviera poco, los dos tests de arriba pasarían sin mirar nada.
    El umbral no es un número de conveniencia: la revisión midió **17** funciones
    alcanzadas, y bajar de quince significa que el recorrido se rompió."""
    withs, alcanzadas = cierre_bajo_mutex()
    assert withs, "sin bloque de mutex no hay nada que vigilar"
    assert len(alcanzadas) >= 15, (
        f"el cierre transitivo devolvio solo {len(alcanzadas)} funciones "
        f"({sorted(alcanzadas)}): el recorrido esta roto o el cuerpo del `with` cambio")
    # Y que alcance de verdad las que están a más de un salto.
    for esperada in ("_intake_drive_ev", "_alta_crm", "hash_tree_local", "etapa_crm"):
        assert esperada in alcanzadas, (
            f"{esperada} deberia alcanzarse desde el bloque y el recorrido no la ve")


@pytest.mark.parametrize("forma", [
    "raise typer.Exit(code=0)",
    "raise typer.Abort()",
    "__import__('sys').exit(77)",
    "raise SystemExit(77)",
])
def test_el_guard_MUERDE_cada_forma_de_terminar(forma):
    """Prueba negativa del propio guard, y existe porque su primera versión solo
    reconocía `typer.Exit`: un `sys.exit` o un `Abort` la dejaban en verde. Dos mutantes
    de la misma forma no son dos mutantes.

    Se muta el fuente **en memoria**, sin tocar el fichero.
    """
    fuente = _fuente()
    ancla = "    lote = intake_manual.abrir_lote_manual("   # dentro de `_intake_manual`
    assert ancla in fuente
    mutado = fuente.replace(ancla, f"    {forma}\n{ancla}", 1)

    _, alcanzadas = cierre_bajo_mutex(mutado)
    assert "_intake_manual" in alcanzadas, "la funcion mutada ya no se alcanza"
    definidas = _definidas(_arbol(mutado))
    assert terminaciones_en(definidas["_intake_manual"]), (
        f"el guard NO ve {forma!r}: deja verde exactamente la regresion que dice impedir")


def test_un_nombre_inexistente_FALLA_y_no_se_salta():
    """HD-02: la versión anterior convertía un nombre muerto en `pytest.skip`, así que el
    guard podía perder superficie sin ponerse rojo. Ahora el cierre es derivado, y si
    `main` desapareciera el recorrido debe romperse con estruendo."""
    with pytest.raises(KeyError):
        cierre_bajo_mutex("def otra_cosa():\n    pass\n")


def test_abortar_apertura_lleva_el_codigo_y_no_termina_el_proceso():
    exc = cli.AbortarApertura(1)
    assert exc.codigo == 1
    assert not isinstance(exc, SystemExit), (
        "AbortarApertura no puede ser un SystemExit: seria lo mismo que el typer.Exit "
        "que viene a sustituir")


def test_hd03_la_nota_de_perdida_LLEGA_al_operador(tmp_path, monkeypatch):
    """HD-03. Rescatar `__notes__` no tenía prueba de comportamiento: solo se comprobaba
    el campo `codigo` de la excepción. Y la nota es el punto entero — Typer descarta el
    traceback, así que sin este `[AVISO]` la pérdida de exclusión sigue invisible."""
    from typer.testing import CliRunner

    from core.casos import case_locator

    root = tmp_path / "CASOS"
    root.mkdir()
    monkeypatch.setattr(case_locator, "_root", lambda: root)

    def _revienta_con_nota(*a, **k):
        exc = cli.AbortarApertura(1)
        # Lo que hace el `finally` de `case_mutex.tomado` cuando pierde el lease con una
        # excepcion en vuelo: anotar en vez de lanzar.
        exc.add_note("[mutex] ademas, el mutex se perdio durante la operacion: OSError")
        raise exc

    monkeypatch.setattr(cli, "_despachar_intake", _revienta_con_nota)
    monkeypatch.setattr(cli.case_manager, "ensure_case",
                        lambda case_id, *a, **k: (root / case_id / "00_Input").mkdir(
                            parents=True, exist_ok=True))

    res = CliRunner().invoke(cli.app, [
        "--crm", "skip", "--fuente", "manual", "--src", str(tmp_path),
        "--w-code", "W-TEST01", "--ciudad", "Barcelona", "--tipo-caso", "BAD_DEBT",
        "--codigo-caso", "BaTEST", "--sufijo", "Bad debt", "--direccion", "Calle Falsa 1",
        "--yes",
    ])

    assert res.exit_code == 1, res.output
    assert "[AVISO]" in res.output, res.output
    assert "el mutex se perdio" in res.output, (
        "la nota del mutex no llego al operador: sigue invisible, que era el defecto")


def test_hd04_el_diagnostico_de_identidad_sigue_teniendo_precedencia(tmp_path, monkeypatch):
    """HD-04. Sacar la validación del lock no autorizaba a reordenar lo que el operador
    lee: con la fuente y la identidad mal a la vez, el fallo de identidad es el más
    fundamental de los dos y debe seguir siendo el que se dice."""
    from typer.testing import CliRunner

    from core.casos import case_locator

    root = tmp_path / "CASOS"
    root.mkdir()
    monkeypatch.setattr(case_locator, "_root", lambda: root)

    res = CliRunner().invoke(cli.app, ["--crm", "skip", "--fuente", "manual"])

    assert res.exit_code == 1, res.output
    assert "flags de identidad" in res.output, res.output
    assert "--src" not in res.output, (
        "se adelanto la validacion de fuente por delante de la de identidad: el operador "
        "recibe el diagnostico menos fundamental de los dos")
