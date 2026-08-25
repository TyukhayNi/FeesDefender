"""Dos procesos que compiten DE VERDAD por la misma adquisición.

## Por qué este fichero se escribió dos veces

La primera versión dejaba que el padre terminara de adquirir **antes** de lanzar al
hijo. Cuando el hijo arrancaba, la sección crítica `leer → decidir → escribir` del padre
ya había terminado: no había dos adquisiciones compitiendo, así que lo que se
comprobaba era «un lock ya escrito produce `CaseBusy`», no exclusión mutua.

El revisor de R10 lo ejecutó **con la exclusión entera eliminada** y salió verde
(`PERDEDOR` y luego `GANADOR`, las dos salidas que el test esperaba). Una implementación
sin ningún guard —dos procesos leen ausencia, ambos deciden libre, ambos escriben—
habría pasado.

Aquí los dos contendientes esperan en una **barrera común** y se sueltan a la vez, y el
`Step 3` del Task 8 exige que el mutante que quita el guard **mate** este test. Si
sobrevive, el test no prueba la exclusión.
"""
from __future__ import annotations

import subprocess
import sys
import textwrap
import time
from pathlib import Path

RAIZ_REPO = Path(__file__).resolve().parents[1]
AHORA = "2026-08-25T12:00:00Z"
W = "W-CONC01"

#: Repeticiones de la carrera. Una ventana de carrera se abre por probabilidad, no
#: siempre: con una sola pasada, un mutante puede sobrevivir por suerte.
RONDAS = 12

HIJO = textwrap.dedent('''
    import sys, time
    sys.path.insert(0, {repo!r})
    from pathlib import Path
    from core.casos.case_mutex import adquirir
    from core.casos.workspace_model import CaseBusy

    Path({listo!r}).write_text("x", encoding="utf-8")     # «estoy cargado»
    salida = Path({salida!r})
    while not salida.exists():                             # barrera comun
        time.sleep(0.002)
    try:
        adquirir({w!r}, ahora={ahora!r}, raiz={raiz!r}, lease_seconds=600)
        print("GANADOR")
    except CaseBusy:
        print("PERDEDOR")
''')


def _lanzar(tmp_path: Path, raiz: Path, n: int):
    guion = HIJO.format(repo=str(RAIZ_REPO), w=W, ahora=AHORA, raiz=str(raiz),
                        listo=str(tmp_path / f"listo_{n}"),
                        salida=str(tmp_path / "salida"))
    return subprocess.Popen([sys.executable, "-c", guion], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, encoding="utf-8", errors="replace")


def _esperar_en_la_barrera(tmp_path: Path, cuantos: int) -> None:
    """Sin esto no hay carrera: el primero en arrancar gana por ventaja de arranque."""
    for _ in range(1500):
        if all((tmp_path / f"listo_{n}").exists() for n in range(1, cuantos + 1)):
            return
        time.sleep(0.01)
    raise AssertionError("los hijos no llegaron a la barrera")


def _correr_carrera(base: Path, ronda: int, cuantos: int) -> list[str]:
    tmp_path = base / f"ronda_{ronda}"
    tmp_path.mkdir(parents=True)
    raiz = tmp_path / "locks"
    hijos = [_lanzar(tmp_path, raiz, n) for n in range(1, cuantos + 1)]
    _esperar_en_la_barrera(tmp_path, cuantos)
    (tmp_path / "salida").write_text("ya", encoding="utf-8")
    salidas = []
    for h in hijos:
        out, err = h.communicate(timeout=60)
        assert h.returncode == 0, f"un hijo reventó:\n{err[-800:]}"
        salidas.append(out.strip())
    return sorted(salidas)


def test_de_dos_procesos_que_COMPITEN_gana_exactamente_uno(tmp_path):
    """`['GANADOR', 'GANADOR']` significa que la exclusión no existe."""
    for ronda in range(RONDAS):
        salidas = _correr_carrera(tmp_path, ronda, 2)
        assert salidas == ["GANADOR", "PERDEDOR"], (
            f"ronda {ronda}: dos procesos compitieron y el resultado fue {salidas}")


def test_un_proceso_solo_SI_entra(tmp_path):
    """Control negativo: sin él, «no dejar entrar nunca» pasaría el test de arriba."""
    assert _correr_carrera(tmp_path, 0, 1) == ["GANADOR"]
