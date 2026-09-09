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

    #: `doc_id` que el registro da por materializados y cuyo fichero **no está** bajo la
    #: raíz autorizada. Vacío no significa «todos verificados»: significa que los que se
    #: comprobaron estaban. Ver `ausentes_verificado`.
    ausentes_en_disco: tuple[str, ...] = ()
    #: ¿Se llegó a mirar el disco? `False` cuando `leer` no recibió raíz (tests que
    #: inyectan). Distinguirlo evita leer un `ausentes_en_disco` vacío como una garantía.
    ausentes_verificado: bool = False

    @property
    def solo_listadas(self) -> dict[str, dict]:
        """Enumeradas por el CRM y **sin materializar según el registro**.

        Ojo con el nombre, porque la R1 lo señaló (su H-17): `materializadas` es un
        **estado del registro**, no una comprobación de I/O — `RegistroOcurrencias`
        filtra por `estado` y no toca el disco. Un crudo borrado deja el registro y D8
        cuadrando entre sí. La comprobación física es `ausentes_en_disco`, y se hace en
        `leer` cuando hay raíz.
        """
        return {d: r for d, r in self.listadas.items() if d not in self.materializadas}


def _registro_bajo(raiz, case_id: str):
    """El registro de ocurrencias **de la raíz autorizada**, no del catálogo.

    `RegistroOcurrencias(case_id)` resuelve su propia ruta con `registro_path` →
    `caso_path` → `case_locator`, que vuelve a `CASOS_ROOT`. Así que se construye y se le
    **redirige `path`** antes de `load()`: se reutiliza su parser y su validación —que es
    lo que no hay que duplicar— y se sustituye solo la resolución de la ruta, que es lo
    que estaba mal (R1/H-06).
    """
    from core.ocurrencias_crm import RegistroOcurrencias

    from .sede import contener

    # No se puede usar el constructor: `__init__` llama a `registro_path(case_id)`, que
    # resuelve por `case_locator` y **lanza** si el caso no está en el catálogo — que es
    # justo el caso de un checkout o un scratch. Se construye a mano con los cuatro campos
    # que `__init__` fija, y `test_los_campos_de_RegistroOcurrencias_no_han_cambiado` ata
    # esa lista: si el constructor gana un campo, ese test se pone rojo en vez de que aquí
    # se fabrique un objeto a medias.
    reg = RegistroOcurrencias.__new__(RegistroOcurrencias)
    reg.case_id = case_id
    reg.path = contener(raiz, "00_Input", "_ocurrencias_crm.json")
    reg.ocurrencias = {}
    reg._dirty = False
    reg.load()
    return reg


def _pull_state_bajo(raiz, expediente_id: str) -> dict | None:
    """El `pull_state` (D8) **de la raíz autorizada**.

    Reproduce el cuerpo de `case_manager.read_pull_state` reutilizando sus dos helpers
    —`read_md` y `_find_expediente_entry`— y cambiando solo de dónde sale la base. La
    original arranca con `buscar(case_id)`, o sea `CASOS_ROOT`.
    """
    from core.case_manager import _find_expediente_entry
    from core.utils import read_md

    from .sede import contener

    index = contener(raiz, "00_Input", "_caso.md")
    if not index.exists():
        return None
    try:
        fm, _ = read_md(index)
    except Exception:
        return None
    _, entry = _find_expediente_entry(fm.get("sudespacho_expedientes") or [],
                                      expediente_id)
    return entry


def leer(case_id: str, expediente_id: str, *, raiz=None, registro=None,
         pull_state: dict | None = ...) -> Conjuntos:
    """Los tres conjuntos, leídos **de la raíz autorizada**.

    ``raiz`` es obligatoria salvo que se inyecten los dos lectores, y eso es deliberado:
    sin ella los lectores volvían a `CASOS_ROOT` por su cuenta, así que se autorizaba una
    raíz y se leía otra — en un checkout con el mismo identificador, la vista mezclaba
    mapa y bytes locales con ocurrencias y D8 del canon (R1/H-06). Falla **cerrado**: es
    más fácil olvidar pasar la raíz que darse cuenta de que se leyó del sitio equivocado.

    El centinela de ``pull_state`` es ``...`` y no ``None`` a propósito: ``None`` es un
    valor legítimo que significa «no hay estado de pull», y hace falta poder pasarlo.
    """
    expediente_id = str(expediente_id).strip()

    if registro is None:
        if raiz is None:
            raise UniversoError(
                "`leer` necesita la raíz autorizada para saber de dónde lee el registro "
                "de ocurrencias: sin ella volvería al catálogo, y la raíz autorizada "
                "puede ser un checkout con el mismo identificador y otros datos")
        registro = _registro_bajo(raiz, case_id)
    if pull_state is ...:
        if raiz is None:
            raise UniversoError(
                "`leer` necesita la raíz autorizada para leer el `pull_state`: la "
                "original arranca en `CASOS_ROOT`")
        pull_state = _pull_state_bajo(raiz, expediente_id)

    listadas = registro.listadas(expediente_id)
    materializadas = registro.materializadas(expediente_id)

    if not listadas:
        raise UniversoError(
            f"el registro de ocurrencias no enumera ni un documento del expediente "
            f"{expediente_id!r}. Un universo vacío es indistinguible de «todavía no se ha "
            f"hecho el pull», y la vista no puede decidir sobre esa ambigüedad: corre "
            f"`sync_sudespacho intake-judicial` (o `pull`) y vuelve")

    # R1/H-17: `materializadas` dice lo que el REGISTRO cree, no lo que hay en disco. Con
    # raiz se comprueba; sin ella se dice que no se comprobo, en vez de callarlo.
    ausentes: tuple[str, ...] = ()
    verificado = False
    if raiz is not None:
        from .sede import SedeError, contener
        faltan = []
        for d, rev in sorted(materializadas.items()):
            ruta = rev.get("path")
            if not ruta:
                faltan.append(d)
                continue
            try:
                if not contener(raiz, "00_Input", str(ruta)).is_file():
                    faltan.append(d)
            except SedeError:
                faltan.append(d)
        ausentes, verificado = tuple(faltan), True

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
        ausentes_en_disco=ausentes,
        ausentes_verificado=verificado,
    )


def incoherencias(c: Conjuntos) -> tuple[str, ...]:
    """Lo que no cuadra entre los tres conjuntos. **Vacío = coherente, no completo.**

    Dos cosas que NO son incoherencias, y conviene separarlas:

    * Que haya ``listadas`` sin materializar. Eso es el régimen acotado y es normal
      (spec §1.1).
    * Que no se haya comprobado el disco (``ausentes_verificado`` en `False`). Una
      incoherencia es un **desacuerdo entre dos fuentes**; «no lo miré» es **cobertura
      ausente**, que es otra cosa y va por su propio canal — el informe la reporta. Meter
      la cobertura ausente aquí hacía que `completo` fuera falso en cuanto alguien
      inyectara los lectores, que es la señal de que estaba en el sitio equivocado.
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

    if c.ausentes_en_disco:
        out.append(
            f"el registro da por materializados {len(c.ausentes_en_disco)} documento(s) "
            f"cuyo fichero NO está bajo la raíz autorizada: "
            f"{list(c.ausentes_en_disco[:5])}. `materializada` es un estado del registro, "
            f"no una comprobación de disco")

    if c.errores_pull:
        out.append(
            f"la última corrida del pull dejó {len(c.errores_pull)} error(es), así que el "
            f"universo puede no estar completo: {list(c.errores_pull[:3])}")

    return tuple(out)
