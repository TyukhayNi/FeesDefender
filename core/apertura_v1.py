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
from collections.abc import Callable, Sequence


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


#: Vocabulario cerrado del resultado de una etapa. `saltada` NO es `hecha`: significa
#: que la etapa decidio, con razon declarada, que no habia nada que hacer.
ESTADOS_ETAPA = ("hecha", "saltada", "fallo")


class EtapaDesconocida(ValueError):
    """`hasta` nombra una etapa que no esta en la secuencia."""


@dataclasses.dataclass(frozen=True)
class EtapaResultado:
    nombre: str
    estado: str
    detalle: str
    pendientes: tuple[Pendiente, ...] = ()

    def __post_init__(self):
        if self.estado not in ESTADOS_ETAPA:
            raise ValueError(
                f"estado de etapa fuera del vocabulario: {self.estado!r}; "
                f"validos: {ESTADOS_ETAPA}")


@dataclasses.dataclass(frozen=True)
class Etapa:
    nombre: str
    correr: Callable[[], EtapaResultado]


@dataclasses.dataclass(frozen=True)
class ResultadoV1:
    estado: str
    etapas: tuple[EtapaResultado, ...]
    pendientes: tuple[Pendiente, ...]
    parada: str | None


def secuenciar(etapas: Sequence[Etapa], *, hasta: str | None = None) -> ResultadoV1:
    """Corre las etapas en orden. Para tras `hasta`, y para en el primer `fallo`.

    `hasta` se valida ANTES de correr nada: un nombre mal escrito no puede convertirse
    en «no pares», porque entonces el operador pidio parar y la secuencia siguio.
    """
    nombres = [e.nombre for e in etapas]
    if hasta is not None and hasta not in nombres:
        raise EtapaDesconocida(
            f"--hasta {hasta!r} no es una etapa de V1; validas: {nombres}")

    hechas: list[EtapaResultado] = []
    pendientes: list[Pendiente] = [PENDIENTE_FUENTES_V3]
    hubo_fallo = False
    parada: str | None = None

    for etapa in etapas:
        res = etapa.correr()
        hechas.append(res)
        pendientes.extend(res.pendientes)
        if res.estado == "fallo":
            hubo_fallo = True
            break
        if hasta is not None and etapa.nombre == hasta:
            parada = etapa.nombre
            break

    return ResultadoV1(
        estado=estado_de(pendientes, hubo_fallo=hubo_fallo),
        etapas=tuple(hechas),
        pendientes=tuple(pendientes),
        parada=parada,
    )
