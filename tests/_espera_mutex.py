"""Espera acotada por CONDICIÓN para los tests del renovador del mutex por caso.

Existe porque tres ficheros de test esperaban al latido con el mismo bucle escrito a
mano —`for _ in range(150): time.sleep(0.02)`, o sea tres segundos— sin ninguna relación
escrita con el periodo con el que `tomado()` programa su renovador
(`lease / _FRACCION_LATIDO`). En `test_RENUEVA_mientras_el_cuerpo_corre` ese periodo es
**un segundo**: el presupuesto era 3x el suceso que esperaba y nadie lo había dicho en
ningún sitio. Aquí el presupuesto se **deriva** de la constante de producción, así que
sigue a quien la cambie.

## Lo que un plazo de pared NO puede probar, y por eso aquí es generoso

Un sistema operativo con la máquina saturada no promete cuándo despierta un hilo, así
que un plazo de reloj no acredita puntualidad: solo produce rojos que no significan
nada, y la regla de las dos semillas de este repo no puede permitirse ninguno. La mitad
**temporal** de la propiedad —que el renovador despierta más de una vez por lease, de
modo que un latido perdido no agota el lease— se mide sin reloj, contra la constante, en
`test_case_mutex.py::TestElGestorRenueva::test_el_renovador_DESPIERTA_dos_veces_por_lease`.
Lo que se espera aquí es solo que el **mecanismo** ocurra.

## Lo medido el 2026-09-07, que descarta la explicación fácil

Linux, 24 procesos ocupados sobre 4 CPUs (6x de sobresuscripción), 8 corridas: el primer
latido llega a **1,00-1,03 s** de su periodo de 1 s —nunca tarde— y el presupuesto del
bucle viejo **crece** con la carga (3,05 s en reposo, 3,77-4,09 s saturado). O sea que
«el hilo de renovación no llega a tiempo» no explica el rojo: bajo carga el margen
mejora, no empeora.

Lo que sí lo explica es que el renovador **muera**, y de eso el bucle viejo no decía ni
palabra: su mensaje era «el renovador no latió en 3 s», acusando al reloj de un fallo que
no era del reloj. Medido por inyección el mismo día — un solo `os.replace` fallido del
`.lock` produce **exactamente** ese rojo, con la causa real (`PermissionError`) enterrada
en `sesion._causa`. El mecanismo es `MEJORAS #145`: en Windows el `read_text` de un
lector y el `os.replace` del renovador chocan, y `tomado` trata cualquier excepción de
`renovar` como pérdida de titularidad. Por eso `esperar()` mira `sesion.perdido()` y
nombra la causa.
"""
from __future__ import annotations

import threading
import time

#: Cuántos latidos se le conceden a la condición antes de darla por incumplida. Veinte
#: y no tres: con el latido llegando a 1,03 s de su periodo de 1 s bajo 6x de carga,
#: hacen falta **veinte veces** su plazo para que esto se ponga rojo, y a esa distancia
#: el culpable ya no puede ser el planificador. Lo que se pierde por ser generoso —la
#: puntualidad— se prueba aparte y sin reloj.
LATIDOS_DE_GRACIA = 20

#: Tope para que el hilo del renovador llegue a su PRIMERA espera. No es un latido: es
#: arrancar un `threading.Thread`, que ocurre en microsegundos o no ocurre.
ARRANQUE_DEL_HILO = 10.0

#: Cadencia del sondeo. La condición se consulta en memoria, así que no cuesta disco —y
#: no leer el `.lock` en un bucle es justamente el punto (`MEJORAS #145`).
_CADENCIA = 0.01


def periodo_de_latido(lease_seconds: int) -> float:
    """El periodo REAL con el que `tomado()` programa su renovador.

    Se lee de la constante de producción a propósito: si `_FRACCION_LATIDO` cambia, el
    presupuesto de los tests la sigue sin que nadie tenga que acordarse.
    """
    from core.casos import case_mutex

    return lease_seconds / case_mutex._FRACCION_LATIDO


def _causa(sesion) -> str:
    """Solo el TIPO de la causa, nunca su texto (la regla de R13/H13-05).

    Un `OSError` de escritura lleva la ruta en su mensaje, y este mensaje acaba en el log
    de una suite, que es el material que se pega en un PR.
    """
    if sesion._causa is None:
        return "el lease caducó o la titularidad cambió (sin excepción detrás)"
    return type(sesion._causa).__name__


def esperar(condicion, *, lease_seconds: int, motivo: str, sesion=None) -> float:
    """Espera a que `condicion()` sea cierta. Devuelve los segundos que tardó.

    `sesion` es opcional y sirve para **no esperar en balde**: si el renovador murió, la
    condición ya no se va a cumplir, y el rojo tiene que nombrar la causa que el hilo
    registró en vez del plazo agotado. Un test cuya condición ES `sesion.perdido()` no lo
    pasa, obviamente.
    """
    periodo = periodo_de_latido(lease_seconds)
    plazo = LATIDOS_DE_GRACIA * periodo
    t0 = time.monotonic()
    while True:
        if condicion():
            return time.monotonic() - t0
        if sesion is not None and sesion.perdido():
            raise AssertionError(
                f"{motivo}: el renovador MURIÓ tras {time.monotonic() - t0:.2f} s — "
                f"causa registrada por el hilo: {_causa(sesion)}")
        if time.monotonic() - t0 >= plazo:
            raise AssertionError(
                f"{motivo}: no se cumplió en {plazo:.1f} s "
                f"({LATIDOS_DE_GRACIA} latidos de {periodo:.2f} s). A esta distancia del "
                f"periodo el planificador no es una explicación")
        time.sleep(_CADENCIA)


class _EventoQueAnotaSuEspera(threading.Event):
    """Un `threading.Event` normal que apunta con qué plazo se le espera."""

    def __init__(self, esperas: list, primera: threading.Event) -> None:
        super().__init__()
        self._esperas = esperas
        self._primera = primera

    def wait(self, timeout=None):                # noqa: D102 - contrato de `Event`
        self._esperas.append(timeout)
        self._primera.set()
        return super().wait(timeout)


class ThreadingQueAnotaEsperas:
    """`threading` con su `Event` instrumentado; todo lo demás, el módulo real.

    Sustituye a `case_mutex.threading` —el atributo del módulo, no el `threading`
    global— para poder leer **el plazo con el que el renovador se va a dormir** sin
    esperar a que despierte. Es la costura que hace la puntualidad medible sin reloj: el
    `Event` de parada es exactamente lo que `tomado()` espera entre latidos.
    """

    def __init__(self) -> None:
        self.esperas: list = []
        self.primera_espera = threading.Event()

    def __getattr__(self, nombre):
        return getattr(threading, nombre)

    def Event(self):                             # noqa: N802 - imita `threading.Event`
        return _EventoQueAnotaSuEspera(self.esperas, self.primera_espera)
