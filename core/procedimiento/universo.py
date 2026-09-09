"""Los tres conjuntos del CRM y sus puertas (invariante I4).

La rev. 1 de este plan conflató dos de ellos y el efecto fue doble: en el régimen de
intake **acotado** —2 documentos bajados de 76, que es el normal en el intake judicial—
habría bloqueado los otros 74; y con ``doc_ids`` vacío se saltaba el cruce entero y las
`solo_listadas` no aparecían por ningún lado. O sea: inservible y a la vez silencioso.

    listadas        el UNIVERSO: todo lo que el CRM enumeró
    materializadas  además está en disco
    descargadas     lo que bajó LA ÚLTIMA CORRIDA (``pull_state.doc_ids``, D8)

La prueba de la tercera, verificada el 2026-09-09: ``core/case_manager.py:1638`` dice
literalmente «``doc_ids``: IDs numéricos de los documentos **descargados**», y
``core/sync_sudespacho.py:1669`` hace el ``append`` **dentro** del bucle de descarga,
después del filtro ``only_doc_ids``. Por eso ``documents_total_crm`` puede superar a
``len(descargadas)`` sin que nada esté mal.
"""
from __future__ import annotations

from dataclasses import dataclass


class UniversoError(Exception):
    """No se puede establecer el universo del expediente. Falla CERRADO."""


@dataclass(frozen=True)
class Conjuntos:
    expediente_id: str
    listadas: dict[str, dict]
    materializadas: dict[str, dict]
    #: ``None`` = no se pudo leer el ``pull_state``. NO es «no bajó nada».
    descargadas: frozenset[str] | None
    total_crm: int | None
    errores_pull: tuple[str, ...] = ()

    @property
    def solo_listadas(self) -> dict[str, dict]:
        """Enumeradas por el CRM y NO en disco. El hueco del intake acotado."""
        return {d: r for d, r in self.listadas.items() if d not in self.materializadas}


def leer(case_id: str, expediente_id: str, *, registro=None,
         pull_state: dict | None = ...) -> Conjuntos:
    """Los tres conjuntos. ``registro`` y ``pull_state`` se inyectan en los tests.

    El centinela de ``pull_state`` es ``...`` y no ``None`` a propósito: ``None`` es un
    valor legítimo que significa «no hay estado de pull», y hace falta poder pasarlo.
    """
    expediente_id = str(expediente_id).strip()

    if registro is None:
        from core.ocurrencias_crm import RegistroOcurrencias
        registro = RegistroOcurrencias(case_id)
        registro.load()
    if pull_state is ...:
        from core.case_manager import read_pull_state
        pull_state = read_pull_state(case_id, expediente_id)

    listadas = registro.listadas(expediente_id)
    materializadas = registro.materializadas(expediente_id)

    if not listadas:
        raise UniversoError(
            f"el registro de ocurrencias no enumera ni un documento del expediente "
            f"{expediente_id!r}. Un universo vacío es indistinguible de «todavía no se ha "
            f"hecho el pull», y la vista no puede decidir sobre esa ambigüedad: corre "
            f"`sync_sudespacho intake-judicial` (o `pull`) y vuelve")

    ps = pull_state or {}
    descargadas = (frozenset(str(d) for d in ps["doc_ids"])
                   if isinstance(ps.get("doc_ids"), list) else None)
    total = ps.get("documents_total_crm")
    return Conjuntos(
        expediente_id=expediente_id,
        listadas=listadas,
        materializadas=materializadas,
        descargadas=descargadas,
        total_crm=total if isinstance(total, int) else None,
        errores_pull=tuple(str(e) for e in (ps.get("errors") or [])),
    )


def incoherencias(c: Conjuntos) -> tuple[str, ...]:
    """Lo que no cuadra entre los tres conjuntos. **Vacío = coherente, no completo.**

    Lo que NO es una incoherencia: que haya ``listadas`` sin materializar. Eso es el
    régimen acotado y es normal (spec §1.1).
    """
    out: list[str] = []

    if c.descargadas is None:
        out.append(
            "no se pudo leer el `pull_state` del expediente: sin él no se puede cruzar lo "
            "que el CRM enumeró con lo que la última corrida bajó. No se asume que no bajó "
            "nada")
    else:
        fuera = sorted(c.descargadas - set(c.listadas))
        if fuera:
            out.append(
                f"el `pull_state` dice haber descargado doc_id que el registro no enumera: "
                f"{fuera}. Uno de los dos está rancio; regenera el pull")
        sin_disco = sorted(c.descargadas & set(c.solo_listadas))
        if sin_disco:
            out.append(
                f"el `pull_state` dice haber descargado {sin_disco} y el registro los "
                f"tiene solo como `listada`: el fichero no está en disco")

    if c.total_crm is not None and c.total_crm != len(c.listadas):
        out.append(
            f"el `pull_state` dice {c.total_crm} documentos en el CRM y el registro "
            f"enumera {len(c.listadas)}: el universo puede estar incompleto")

    if c.errores_pull:
        out.append(
            f"la última corrida del pull dejó {len(c.errores_pull)} error(es), así que el "
            f"universo puede no estar completo: {list(c.errores_pull[:3])}")

    return tuple(out)
