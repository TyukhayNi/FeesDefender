"""La politica de duplicados del CRM al dar de alta un expediente. **Una, y aqui.**

Diseno: `docs/superpowers/specs/2026-09-05-alta-ui-politica-compartida-design.md` §3.1.

Hasta el 2026-09-05 la CLI (`scripts/abrir_caso.py::_alta_crm`) y el formulario «Nuevo
caso» de `streamlit_app.py` daban de alta en el CRM del cliente con reglas DISTINTAS: la
CLI buscaba por W-code en las dos jurisdicciones y fallaba cerrado; el formulario buscaba
por referencia exacta, seguia adelante si no podia consultar y ofrecia un boton «Confirmar
de todos modos» que creaba el duplicado. Es el mismo defecto que `MEJORAS #153` —la regla
en el envoltorio y el otro llamador la rodea— y el remedio es el mismo: la regla sale del
envoltorio y va donde los dos la comparten.

Este modulo **no habla con el CRM y no escribe nada**: recibe lo que
`sudespacho_relations.buscar_expedientes_duplicados` encontro y devuelve una decision. Los
dos llamadores la consumen; ninguno la reimplementa.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .sudespacho_relations import DuplicadosExpediente, _normalize_element

#: Las tres acciones posibles. Cadenas y no un Enum para que el formulario y la CLI las
#: comparen sin importar nada mas.
CREAR = "crear"
VINCULAR = "vincular"
BLOQUEAR = "bloquear"

#: Prefijo de los avisos que dejan escrito lo que se dio por bueno a ciegas (regla 3 del
#: §3.1). Los llamadores lo usan para distinguir esos avisos de los de direccion/contrario.
SIN_COMPROBAR = "SIN COMPROBAR: "


@dataclass(frozen=True)
class DecisionAltaCRM:
    """Lo que hay que hacer con el CRM antes de crear un expediente, y por que.

    - `crear`: no hay expediente con este W-code (o se forzo). `avisos` puede traer
      coincidencias de direccion/contrario, que no bloquean.
    - `vincular`: el W-code YA esta en el CRM. `candidatos` trae todos los `(elemento, id)`
      hallados; el llamador vincula UNO al caso local y no crea otro.
    - `bloquear`: no se pudo consultar algo y no se forzo. `sin_comprobar` dice que.
    """

    accion: str
    #: `(elemento, exp_id)` hallados por W-code, en el orden en que llegaron.
    candidatos: tuple[tuple[str, str], ...] = ()
    #: Direccion/contrario coincidentes; forzado, ademas lo no comprobado con `SIN_COMPROBAR`.
    avisos: tuple[str, ...] = ()
    #: Lo que el CRM no dejo mirar. Se conserva en las tres acciones: es un hecho, no
    #: una consecuencia de la decision.
    sin_comprobar: tuple[str, ...] = ()
    #: Una frase para el operador. Sin nombres de flags ni de widgets: la frase es la
    #: misma en la CLI y en el formulario.
    motivo: str = ""


def decidir(dup: DuplicadosExpediente, *, forzar: bool) -> DecisionAltaCRM:
    """Aplica las tres reglas del §3.1, **en este orden y sin excepciones**.

    1. `dup.por_wcode` no vacio -> `vincular`. Tiene prioridad sobre la incertidumbre: si
       el W-code ya esta en el CRM, crear otro es el dano que esto evita, se haya podido
       consultar el resto o no.
    2. `dup.incierto` y no `forzar` -> `bloquear`, con la lista literal de lo no comprobado.
    3. En otro caso -> `crear`. Si venia incierto y se forzo, cada criterio no comprobado
       se anade a `avisos` con el prefijo `SIN_COMPROBAR`, para que quede en pantalla (CLI o
       formulario) que se dio por bueno a ciegas; ningun registro durable lo recibe hoy.

    Es una funcion pura: la misma entrada da la misma decision en la CLI y en la UI.
    """
    # Sin repetidos (R1/H-07): el mismo `(elemento, id)` dos veces en `por_wcode` salia
    # como dos candidatos y la CLI imprimia «#648, #648».
    candidatos = tuple(dict.fromkeys((str(el), str(i)) for el, i in dup.por_wcode))
    sin_comprobar = tuple(str(s) for s in dup.sin_comprobar)
    avisos = tuple(dup.avisos)

    if candidatos:
        donde = ", ".join(f"{el} #{i}" for el, i in candidatos)
        return DecisionAltaCRM(
            accion=VINCULAR,
            candidatos=candidatos,
            avisos=avisos,
            sin_comprobar=sin_comprobar,
            motivo=(f"El CRM ya tiene {len(candidatos)} expediente(s) con este id GO: {donde}. "
                    "No se crea otro: se vincula el existente al caso local."),
        )

    if sin_comprobar and not forzar:
        return DecisionAltaCRM(
            accion=BLOQUEAR,
            avisos=avisos,
            sin_comprobar=sin_comprobar,
            motivo=("No se pudo comprobar si este expediente ya existe en el CRM, asi que "
                    "no se da de alta: crearlo a ciegas puede duplicarlo."),
        )

    if sin_comprobar:
        avisos = avisos + tuple(f"{SIN_COMPROBAR}{s}" for s in sin_comprobar)
        motivo = ("Se da de alta SIN haber podido comprobar todos los criterios de "
                  "duplicado; queda escrito cuales.")
    elif avisos:
        motivo = ("No hay expediente con este id GO en el CRM; hay coincidencias de "
                  "direccion o contrario que no bloquean.")
    else:
        motivo = "No hay expediente con este id GO en el CRM."
    return DecisionAltaCRM(
        accion=CREAR, avisos=avisos, sin_comprobar=sin_comprobar, motivo=motivo)


# ---------------------------------------------------------------------------
# Reutilizar el expediente ya vinculado al caso local (§3.2.2)
# ---------------------------------------------------------------------------

def elemento_canonico(elemento: Any) -> str | None:
    """Slug canonico del CRM (`extrajudiciales` | `expedientes_judiciales`) o `None`.

    El frontmatter de `_caso.md` guarda alias (`judiciales`) segun quien registro el
    expediente; el CRM solo conoce el canonico. Se delega en la tabla de
    `sudespacho_relations` en vez de copiarla: dos tablas divergen.
    """
    if not isinstance(elemento, str):
        return None
    return _normalize_element(elemento)


def expediente_local_para_alta(
    expedientes: Iterable[Any], elemento_preferido: str,
) -> dict | None:
    """El expediente ya registrado en `_caso.md` que el alta debe REUTILIZAR, o `None`.

    Prefiere el del `elemento_preferido` (el que eligio el radio del formulario). Si no
    lo hay pero el caso tiene expediente de la OTRA jurisdiccion, devuelve ese: el
    formulario nunca crea un segundo expediente para un W-code que ya tiene uno —si de
    verdad hacen falta dos, se decide en el CRM—, y sin esto un «vincular» de la otra
    jurisdiccion volveria a caer en la politica y a pedir vincular, en bucle.

    Solo cuenta una entrada con `id` y con elemento reconocible: un `dict` a medias o una
    entrada de otro elemento no es un expediente que se pueda completar.
    """
    preferido = elemento_canonico(elemento_preferido)
    validas: list[tuple[str, dict]] = []
    for e in expedientes:
        if not isinstance(e, dict):
            continue
        canon = elemento_canonico(e.get("element"))
        if canon is None or not str(e.get("id") or "").strip():
            continue
        validas.append((canon, e))
    for canon, e in validas:
        if canon == preferido:
            return e
    return validas[0][1] if validas else None
