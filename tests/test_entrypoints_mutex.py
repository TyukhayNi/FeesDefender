"""Los entrypoints adquieren el mutex — Plan 3A, Task 5. Fronteras E1-E5.

**Aquí es donde el mutex deja de ser un módulo probado y empieza a proteger algo.** Hasta
este task existía, tenía cuatro rondas de revisión adversarial y 17 mutantes, y **no lo
llamaba nadie**: la frase honesta era «construido», no «protegido».

El dolor que justificó la decisión D2 está medido y es literalmente E1: relanzar el
pipeline sobre un caso sin saber si la corrida anterior terminó.
"""
from __future__ import annotations

import ast
import io
from pathlib import Path

import pytest
from typer.testing import CliRunner

W = "W-ENTRY1"
CASE_ID = f"Ba001 - Calle Falsa 2 - ({W}) - honorarios"

runner = CliRunner()


# NO se fija el reloj del sistema en este fichero, y es deliberado. Los demás tests del
# mutex anclan `_ahora_del_sistema` para poder usar timestamps literales, pero aquí lo que
# se ejercita son los **entrypoints reales**, que pasan `now_iso_utc` — el reloj de verdad—.
# Anclar el del sistema y dejar que el CLI use el real hace que la cota simétrica de R13
# salte por desvío absurdo, y entonces el test falla por el montaje y no por el contrato.
# Lo aprendí aquí: los cuatro primeros fallos de este fichero eran míos, dos por esto.


@pytest.fixture(autouse=True)
def _mapa_limpio():
    from core.casos import mutex_sesion
    with mutex_sesion._CANDADO:
        mutex_sesion._SESIONES.clear()
    yield
    with mutex_sesion._CANDADO:
        mutex_sesion._SESIONES.clear()


def monta_caso(root, nombre=CASE_ID, id_go=W):
    d = root / nombre
    (d / "00_Input").mkdir(parents=True)
    lineas = ["---", "meta:"]
    if id_go is not None:
        lineas.append(f"  id_go: {id_go}")
    lineas += ["  estado_repositorio: disponible", "---", ""]
    io.open(d / "00_Input" / "_caso.md", "w", encoding="utf-8", newline="\n").write(
        "\n".join(lineas))
    return d


def _instantanea(raiz: Path) -> dict[str, int]:
    """Tamaño de cada fichero bajo `raiz`. Para acreditar CERO bytes escritos."""
    return {str(p.relative_to(raiz)): p.stat().st_size
            for p in sorted(raiz.rglob("*")) if p.is_file()}


# --------------------------------------------------------------------------- E1

def test_e1_sala_maquina_aborta_si_otro_proceso_tiene_el_caso(tmp_casos_root):
    """E1 — el dolor medido de D2, ahora con un abort limpio en vez de dos escritores.

    El lock se toma con la primitiva de bajo nivel a propósito: `adquirir` deja el fichero
    en disco **sin** registrar nada en el mapa de sesiones de este proceso, así que el CLI
    lo ve como lo que es —un titular ajeno vivo— y no se une a él por reentrancia.
    """
    from core.casos import case_mutex
    from scripts import sala_maquina as cli

    case_dir = monta_caso(tmp_casos_root)
    from core.utils import now_iso_utc
    case_mutex.adquirir(W, ahora=now_iso_utc())   # otro proceso tiene el caso

    antes = _instantanea(case_dir)
    res = runner.invoke(cli.app, ["apply", CASE_ID])

    assert res.exit_code == 2, (
        f"se esperaba abort con codigo 2 y salio {res.exit_code}: {res.output}")
    assert _instantanea(case_dir) == antes, (
        "el motor escribio con el caso tomado por otro: es exactamente el defecto que "
        "esta pieza existe para impedir")


def test_e1b_el_abort_dice_que_esta_ocupado_no_que_falta_el_caso(tmp_casos_root):
    """E1-bis — el mensaje tiene que ser accionable.

    «Caso no encontrado» y «otra corrida en curso» piden cosas opuestas: buscar un typo o
    esperar. Confundirlos es la clase de error que hace perder una tarde.
    """
    from core.casos import case_mutex
    from scripts import sala_maquina as cli

    from core.utils import now_iso_utc

    monta_caso(tmp_casos_root)
    case_mutex.adquirir(W, ahora=now_iso_utc())

    res = runner.invoke(cli.app, ["apply", CASE_ID])
    salida = (res.output or "").lower()
    assert "case_busy" in salida or "ocupado" in salida or "otro proceso" in salida, (
        f"el abort no dice que el caso este tomado: {res.output!r}")


# --------------------------------------------------------------------------- E2

def test_e2_sin_w_code_avisa_y_sigue(tmp_casos_root):
    """E2 — el trinquete: sin identidad no hay mutex, y se declara en vez de abortar.

    Cerrar en falso una vía que hoy funciona le rompe el día al equipo. El hueco se
    **dice** —queda contado— y se cierra con la migración, no con un abort sorpresa.
    """
    from scripts import sala_maquina as cli

    nombre = "carpeta legacy sin codigo"
    monta_caso(tmp_casos_root, nombre=nombre, id_go=None)

    res = runner.invoke(cli.app, ["plan", nombre])
    assert res.exit_code != 2 or "mutex" in (res.output or "").lower(), (
        f"un caso sin W-code no puede abortar en seco: {res.output!r}")


# --------------------------------------------------------------------------- E3

def test_e3_el_anidamiento_de_las_dos_capas_funciona(tmp_casos_root):
    """E3 — la razón de ser de `mutex_sesion`, comprobada de punta a punta.

    `abrir_caso` adquiere y `ensure_case` **exige**. Sin la capa reentrante, la segunda
    llamada chocaría con el lease de la primera —`adquirir` lanza `CaseBusy` ante un lease
    vivo incluido el propio— y el modo v1 se bloquearía contra sí mismo.
    """
    from core import case_manager
    from core.casos import mutex_sesion
    from core.casos.workspace_model import CaseRef
    from core.utils import now_iso_utc

    with mutex_sesion.sostenido(CaseRef(w_code=W), ahora_fn=now_iso_utc):
        # Esto es lo que hace `abrir_caso` dentro de su bloque: el alta se UNE.
        case_dir = case_manager.ensure_case(CASE_ID, modo="v1", id_go=W)
    assert (case_dir / "00_Input").is_dir()


# --------------------------------------------------------------------------- E4

@pytest.mark.parametrize("modulo", ["scripts/abrir_caso.py", "scripts/sala_maquina.py"])
def test_e4_los_entrypoints_pasan_el_reloj_con_offset(modulo):
    """E4 — guard permanente: `ahora_fn=now_iso_utc`, nunca `now_iso`.

    `case_mutex` rechaza a propósito un instante sin offset, porque uno naïve se lee en
    hora **local** y el lease se calcularía mal. El reloj mayoritario del repo es el
    naïve —43 usos frente a 5— así que la vía de error es «simplificar» a `now_iso` y que
    el mutex empiece a lanzar en producción.

    Se comprueba por **AST**, no por subcadena: `"now_iso_utc" in texto` pasaría con el
    nombre dentro de un comentario, que es literalmente lo que R10/H10-10 castigó con
    `filelock` — y en lo que yo caí al escribir el censo de esta misma tanda.
    """
    arbol = ast.parse(io.open(modulo, encoding="utf-8").read(), filename=modulo)
    relojes = []
    for n in ast.walk(arbol):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        nombre = f.attr if isinstance(f, ast.Attribute) else (
                 f.id if isinstance(f, ast.Name) else None)
        if nombre != "sostenido":
            continue
        for kw in n.keywords:
            if kw.arg == "ahora_fn":
                v = kw.value
                relojes.append(v.attr if isinstance(v, ast.Attribute) else
                               getattr(v, "id", ast.dump(v)))
    assert relojes, f"{modulo} no llama a `sostenido(...)`: el entrypoint no adquiere nada"
    assert all(r == "now_iso_utc" for r in relojes), (
        f"{modulo} pasa un reloj que no es `now_iso_utc`: {relojes}. Un instante naive se "
        f"lee en hora local y la primitiva lo rechaza a proposito")


# --------------------------------------------------------------------------- E5

def test_e5_ningun_modulo_de_core_adquiere_el_mutex():
    """E5 — la restricción de capas: `core/` **exige**, los entrypoints adquieren.

    Si un módulo del core adquiriese por su cuenta, el dueño de la secuencia de V1 dejaría
    de ser quien decide el alcance de la exclusión, y dos etapas de la misma corrida
    podrían sostener leases distintos sobre el mismo caso.

    `mutex_sesion` y `case_mutex` están exentos: son las dos capas que IMPLEMENTAN la
    adquisición. Excluir solo la primera fue un descuido mío que este test cazó.
    """
    infractores = []
    for p in sorted(Path("core").rglob("*.py")):
        if p.name in ("mutex_sesion.py", "case_mutex.py"):
            continue
        arbol = ast.parse(io.open(p, encoding="utf-8").read(), filename=str(p))
        for n in ast.walk(arbol):
            if not isinstance(n, ast.Call):
                continue
            f = n.func
            nombre = f.attr if isinstance(f, ast.Attribute) else (
                     f.id if isinstance(f, ast.Name) else None)
            if nombre in ("sostenido", "tomado", "adquirir"):
                infractores.append(f"{p.as_posix()}:{n.lineno} -> {nombre}()")
    assert not infractores, (
        "modulos de core/ que ADQUIEREN el mutex en vez de exigirlo:\n  "
        + "\n  ".join(infractores))


# --------------------------------------------------------------------------- E6

def test_e6_perder_el_mutex_a_mitad_no_saca_un_traceback(tmp_casos_root, monkeypatch):
    """E6 — `MutexPerdido` es un abort con mensaje, no una excepción sin gestionar.

    `CaseBusy` y `MutexPerdido` no significan lo mismo y no piden lo mismo: el primero dice
    «el motor no arrancó, espera»; el segundo, «arrancó y el lease se perdió a mitad, puede
    haber trabajo a medias». Sin esta rama, el segundo salía como traceback **al final de un
    OCR largo**, que es el peor momento para tener que interpretar una excepción.
    """
    from core.casos import mutex_sesion
    from core.casos.workspace_model import MutexPerdido
    from scripts import sala_maquina as cli

    monta_caso(tmp_casos_root)

    def pierde(*a, **kw):
        raise MutexPerdido(w_code=W, detalle="simulado: el lease se fue a mitad")
    monkeypatch.setattr(mutex_sesion, "sostenido", pierde)

    res = runner.invoke(cli.app, ["apply", CASE_ID])
    assert res.exit_code == 2, (
        f"se esperaba abort limpio con codigo 2, salio {res.exit_code}: {res.output!r}")
    assert res.exception is None or isinstance(res.exception, SystemExit), (
        f"salio una excepcion sin gestionar: {res.exception!r}")
    assert "a medias" in (res.output or ""), (
        f"el mensaje no avisa de que el resultado puede estar incompleto: {res.output!r}")
