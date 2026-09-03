"""Secuenciador de la primera vertical de apertura (V1) — Plan 5.

**Que hace y que no.** Conoce el ORDEN de las etapas de V1, el punto de parada, la
maquina de estados del §24 D4 y la forma del informe. No sabe que es Drive, ni el CRM,
ni el OCR: recibe las etapas como invocables. Por eso se prueba entero sin disco, sin
red y sin OCR, que es la razon de que viva en `core/` y no en el entrypoint.

**La regla que impide mentir.** El §21.3 ordena que V1 nunca termine `completo`. Eso NO
se implementa devolviendo la constante: se implementa arrancando la lista de pendientes
con `PENDIENTE_FUENTES_V3` dentro. Asi el estado es una consecuencia de los datos, y un
test puede comprobar la propiedad en vez de creerse el docstring.
"""
from __future__ import annotations

import dataclasses
from collections.abc import Sequence


class EstadoV1:
    """Los tres estados del §13. Clase-espacio-de-nombres, no enum: el valor viaja a
    un evento JSONL y a la pantalla, y ahi es una cadena."""

    COMPLETO = "completo"
    PREPARADO_CON_PENDIENTES = "preparado_con_pendientes"
    BLOQUEADO = "bloqueado"


@dataclasses.dataclass(frozen=True)
class Pendiente:
    """Algo que V1 no pudo cerrar y que hay que decir en voz alta."""

    codigo: str
    detalle: str


#: Permanente en toda ejecucion V1: Gmail y LeadHub son fuentes de V3 (spec §21.3).
PENDIENTE_FUENTES_V3 = Pendiente(
    codigo="fuentes_v3_sin_consultar",
    detalle="V1 no descubre correo en Gmail ni consulta LeadHub: ambas son de V3. "
            "Si el material de este caso sigue sin depositar, no esta aqui.",
)


def estado_de(pendientes: Sequence[Pendiente], *, hubo_fallo: bool) -> str:
    """Regla pura del §24 D4. `completo` es alcanzable aqui a proposito: quien lo
    impide en V1 es el pendiente permanente, no esta funcion."""
    if hubo_fallo:
        return EstadoV1.BLOQUEADO
    if pendientes:
        return EstadoV1.PREPARADO_CON_PENDIENTES
    return EstadoV1.COMPLETO
