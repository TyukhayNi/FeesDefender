"""Crear una actuación en el CRM sudespacho, encapsulando la receta verificada (`MEJORAS #209`).

**Por qué existe este módulo.** El backlog lo dice en una línea: «crear actuaciones en el CRM
no tiene helper: la receta vive en prosa y se reescribe a mano cada vez». Y la frontera que el
propio `#209` enuncia es más grande que el caso: *el contrato del CRM se documenta y no se
encapsula*, así que cada operación nueva se reescribe contra la prosa y hereda sus olvidos.

**La receta son SEIS pasos obligatorios y un séptimo condicional** (`docs/INTEGRACION_SUDESPACHO.md §15.6`,
verificada de punta a punta el 2026-09-10 sobre W-02VEKE, y en vivo otra vez el 2026-09-14 sobre el 636):

1. Aprender el `id_predefinido` de una instancia real — **no inventarlo**.
2. `profesional_asignado` es el **username**, no el id de `empleados`.
3. Resolver el expediente por su **elemento**, no por el número a secas, y contrastarlo.
4. POST de la actuación.
5. POST de vinculación — **sin él la actuación queda huérfana y el paso 4 devuelve 201 igual**.
6. Verificar releyendo **del lado del expediente**: el `GET` por id de la actuación devuelve
   **404 aunque exista**.
7. **Si la actuación vence, agendar el evento** (`calendario`, `Tipo: Vencimiento`). Añadido el
   2026-09-14: `fecha_vencimiento` es un campo que nadie mira, y una fecha límite que no avisa
   no es una fecha límite.

**Lo que este módulo NO hace:** escribir `tipo_actuacion` (va vacío en las 20 instancias reales).

**Y la tarifa SÍ la escribe, desde el 2026-09-14.** Este docstring decía que no —«es el botón de
`§15.4`, solo UI»— y era verdad a medias: lo que no se puede resolver por API es la *tarifa
confidencial del usuario*; el campo `precio_hora` se escribe sin problema, y la cifra está medida
en `[APER-72]`. Dejarlo sin escribir producía actuaciones con `SENIOR - …` en el asunto y `0,00`
en el precio: **completas de aspecto y facturando cero**.

**Cómo se prueba sin tocar el CRM:** todas las funciones aceptan `client=`. Sin él construyen
uno con la `x-api-key` del entorno; con él, los tests inyectan un doble. Ningún test de este
módulo llama al tenant.

**Y por qué eso NO basta, dicho aquí porque cuesta dinero.** Un doble acepta cualquier payload,
así que acredita **qué decide el código ante una respuesta** y nunca **que el payload sea
aceptable**. La corrida en vivo del 2026-09-14 —tres rondas adversariales después, con 5.600
tests verdes— encontró en una sola ejecución tres defectos que ningún doble podía ver:
`Prioridad: "Normal"` (valor inexistente, HTTP 404), `fecha_alta` vacía y `precio_hora` a cero.
La prueba de aceptación de esta pieza es correrla contra el CRM, no una ronda más de lectura.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from html import escape as _escapar

_REST_BASE = "https://api-crm-commons-pro.sudespacho.biz"
_TIMEOUT = 30.0

#: La property de referencia **no se llama igual en las dos jurisdicciones**, y unificarlas
#: rompe la búsqueda judicial en silencio: pedirle `Referencia_Cliente` al judicial devuelve
#: HTTP 500 enumerando sus properties reales (medido el 2026-09-04).
_PROP_REFERENCIA = {
    "extrajudiciales": "Referencia_Cliente",
    "expedientes_judiciales": "referencia_cliente",
}

#: Username del CRM → prefijo del `Subject`. **El prefijo ES la tarifa** (`[APER-72]`, medido
#: sobre 20 actuaciones reales del despacho): `SENIOR - …` factura a 103,00 €/h y `ABOGADO - …`
#: a 77,00. Copiar el prefijo equivocado factura al cliente la tarifa de otro, así que esta
#: tabla **no tiene defecto**: un username que no esté aquí levanta.
#:
#: La forma canónica de cada asunto vive en `docs/MANUAL_DESPACHO.md`; aquí solo está quién
#: firma con qué prefijo.
#: **El prefijo y el precio salen de la MISMA fila**, y eso es el remedio de un defecto medido
#: en vivo el 2026-09-14: la actuación creada llevaba `SENIOR - …` —que ES la tarifa de 103 €/h—
#: y `precio_hora = 0,00`. Los dos datos decían cosas distintas sobre lo mismo, y el que se
#: factura era el que estaba a cero. Una actuación así parece completa y no cobra nada.
#:
#: `§15.4` decía «la tarifa es solo por UI», y es cierto a medias: lo que no se puede resolver
#: por API es la **tarifa confidencial del usuario** que aplica el botón. El campo `precio_hora`
#: sí se escribe (verificado con un `PUT` en vivo sobre la 21393), y la cifra no hay que
#: resolverla: está medida en `[APER-72]` sobre 20 actuaciones reales.
_FIRMANTES = {
    "Nikolai_Tyukhay": ("SENIOR", "103.00"),
    "ana.velastegui": ("ABOGADO", "77.00"),
}

_PREFIJO_POR_FIRMANTE = {u: p for u, (p, _) in _FIRMANTES.items()}
_PRECIO_POR_FIRMANTE = {u: c for u, (_, c) in _FIRMANTES.items()}

_PREFIJOS = tuple(sorted(set(_PREFIJO_POR_FIRMANTE.values())))
#: Campos del POST que materializan una decisión ya validada: `extra` no los toca.
_CAMPOS_DECIDIDOS = frozenset({"Subject", "profesional_asignado", "id_predefinido"})

#: Los estados que un `Recibo` puede tener. **Cerrado a propósito** (R3/H-02): sin vocabulario,
#: un `Recibo("inventado", act_id=…)` pasaba las guardas —no es `incierta` y tiene id— y
#: vinculaba. Una guarda que enumera lo prohibido deja pasar todo lo que no se le ocurrió.
_ESTADOS_RECIBO = frozenset({"no_intentada", "incierta", "incompleta", "verificada"})

#: Los pasos de la receta, más el 0 de «no se llegó a empezar». Son SIETE desde el
#: 2026-09-14: el 7 agenda el vencimiento, porque una fecha límite escrita en un campo que
#: nadie mira no avisa a nadie. Ampliar el vocabulario es seguro aquí y esto se comprobó:
#: `alta_actuacion` no tiene todavía ningún llamador de producción.
_PASOS = frozenset(range(0, 8))

#: Enums de `actuaciones`, **verificados en vivo** con `GET /api/view/enums/actuaciones/{prop}`
#: el 2026-09-14 y recogidos en `INTEGRACION_SUDESPACHO.md §15.6`. Los dos están marcados
#: `protected` por el CRM.
#:
#: **Esto lo encontró la corrida en vivo y ningún doble podía encontrarlo.** El payload mandaba
#: `Prioridad: "Normal"`, que no existe: el tenant devolvió
#: `HTTP 404 — The value: <Normal> sent for the property: Prioridad is incorrect`. Un doble
#: acepta lo que se le mande, así que acredita **qué decide el código ante una respuesta** y
#: nunca **que el payload sea aceptable**. Son dos cosas distintas y solo una se prueba en seco.
_PRIORIDADES = ("Alta", "Media", "Baja")
_ESTADOS_ACTUACION = ("Planificado", "Hecho")

#: `Alta` porque es lo que hace la casa: 36 de 40 actuaciones reales muestreadas el 2026-09-14
#: lo llevan (1 `Media`, 3 vacías). No es una preferencia mía: es la convención observada.
_PRIORIDAD_POR_DEFECTO = "Alta"

#: Campos con vocabulario cerrado. Se validan **antes** del POST, como `extra`: un valor fuera
#: del enum es un defecto del payload y se ve sin preguntarle al CRM. Descubrirlo por el
#: rechazo del POST produce un recibo `incierta` —«puede haberse creado, concilia a mano»— por
#: algo que nunca pudo crearse.
#: Las dos casillas de facturación de la UI son **un solo campo**, `tipo_facturacion`:
#: «Facturar por duración» = `duracion` (duración × `precio_hora`) y «Facturar por precio» =
#: `precio` (`unidades` × `precio_unidad`). Medido sobre 300 actuaciones reales el 2026-09-14:
#: `''` (180) · `duracion` (99) · `precio` (21).
#:
#: El cruce con `facturar` sobre 300 filas reales: 27 tienen la terna coherente
#: (`facturar=1` + `duracion` + tarifa) y **10** están a `facturar=1` + `duracion` con
#: `precio_hora` a `0,00`. **Esas diez NO son dinero perdido** —lo aclaró Nikolai: son
#: actuaciones que se cerraron sin hacer—, y la distinción importa porque yo las había
#: anotado como defecto. Lo que sí se sigue de ahí es la regla de esta función: **las tres
#: cosas van juntas o no va ninguna**, porque sin `tipo_facturacion` el CRM no sabe por qué
#: eje cobrar y la tarifa puesta no cobra.
_TIPOS_FACTURACION = ("duracion", "precio", "")

_ENUMS = {"Prioridad": _PRIORIDADES, "Estado": _ESTADOS_ACTUACION,
          "tipo_facturacion": _TIPOS_FACTURACION}


#: Un prefijo al principio del asunto, tolerando caja y espacios de más.
_RE_PREFIJO = re.compile(r"^\s*(" + "|".join(_PREFIJOS) + r")\s*-\s*", re.I)


def _validar_facturacion(tipo_facturacion: str) -> None:
    """El eje de facturación, comprobado **antes** de escribir.

    Vivía dentro de `crear_actuacion`, o sea dentro del `try` que clasifica los fallos del
    POST, así que un eje inventado salía como recibo `incierta` —«puede haberse creado una
    actuación»— con cero escrituras. **Es la frontera G otra vez**, en un campo añadido el
    mismo día que se cerró: la lección no se aplica sola a lo que se escribe después.
    """
    if tipo_facturacion not in _TIPOS_FACTURACION:
        raise ValueError(
            f"tipo_facturacion={tipo_facturacion!r} no es ninguno de los observados "
            f"({' · '.join(t or '(vacio)' for t in _TIPOS_FACTURACION)})")


def _validar_extra(extra: dict | None) -> None:
    """`extra` no puede pisar lo que la función decide. Levanta `ValueError` si lo intenta.

    **Vive aparte para poder llamarse ANTES de escribir** (R3/H-07). Estaba dentro de
    `crear_actuacion`, o sea dentro del `try` que clasifica los fallos del POST, así que un
    `extra` inválido salía como «el POST no dio recibo: puede haberse creado una actuación,
    concilia a mano» **con cero escrituras**: mandaba a un humano a buscar un efecto que no
    existía. Es la misma frontera que la R2 ya cerró para el firmante, un caso más allá —
    validar y transmitir son fases distintas, y la incertidumbre sobre el efecto solo empieza
    cuando ha podido haber efecto.
    """
    invasores = sorted(set(extra or {}) & _CAMPOS_DECIDIDOS)
    if invasores:
        raise ValueError(
            f"`extra` intenta sobrescribir campos ya validados: {', '.join(invasores)}. "
            "Esos los decide la propia función (el prefijo es la tarifa, el profesional es un "
            "username y el id_predefinido se aprende): pásalos por sus parámetros.")
    for campo, permitidos in _ENUMS.items():
        if campo in (extra or {}) and extra[campo] not in permitidos:
            raise ValueError(
                f"{campo}={extra[campo]!r} no está en el enum del CRM "
                f"({' · '.join(permitidos)}). El tenant lo rechaza con un HTTP 404 y el "
                "recibo saldría 'incierta' por algo que nunca pudo crearse.")


class ActuacionError(RuntimeError):
    """Algo del camino de la actuación no se pudo completar."""


class DestinoNoAcreditado(ActuacionError):
    """El expediente de destino no es —o no se pudo comprobar que sea— el que se esperaba.

    Es un error propio y no un `ActuacionError` cualquiera porque su remedio es distinto: aquí
    **no hay nada que reintentar**, hay que mirar qué par `(elemento, id)` se está usando.
    """


# ---------------------------------------------------------------------------
# Transporte
# ---------------------------------------------------------------------------


def _cliente(client=None):
    if client is not None:
        return client
    api_key = (os.getenv("SUDESPACHO_API_KEY") or "").strip()
    if not api_key:
        raise ValueError(
            "SUDESPACHO_API_KEY vacío en .env — ve a tnm.sudespacho.net → Ajustes → API")
    return httpx.Client(
        base_url=_REST_BASE, timeout=_TIMEOUT,
        headers={"x-api-key": api_key, "Accept": "application/json",
                 "Content-Type": "application/json"})


class CuerpoIlegible(ActuacionError):
    """Un `200` cuyo cuerpo no se puede interpretar. **No es una lista vacía.**"""


def _items(resp) -> list[dict]:
    """Las filas de un `element_registries`, con las dos formas que devuelve el CRM.

    Cuál llega **la elige la cabecera `Accept`**: `application/json` exacto da `items`;
    `ld+json`, `*/*` o ninguna dan `hydra:member`. No es una forma sustituyendo a otra
    (`INTEGRACION_SUDESPACHO.md §15.6`), así que se aceptan las dos.

    **El parseo entero va cubierto, y esto ya se pagó una vez en el módulo hermano.**
    `sudespacho_relations._buscar_registros` documenta que una ronda anterior midió que su
    `try` «solo envolvía `r.json()`» y que ahora cubre el parseo completo. Aquí se repitió el
    defecto: un `200` con cuerpo no-JSON levantaba desde dentro de `_items`, la excepción
    atravesaba `alta_actuacion` —que no envuelve el paso 6— y el llamador recibía una
    excepción **en vez del recibo con el `act_id`**, justo después de escribir en el CRM. La
    respuesta natural a una excepción es repetir el alta, y eso deja una actuación huérfana.

    **Y esta frase fue falsa durante una ronda entera.** La R2 la escribió afirmando el
    parseo cubierto cuando el `try` seguía envolviendo solo `resp.json()`; la R3 lo midió
    (`{"items": 1}` → `TypeError`). Un comentario que afirma una propiedad es justo donde
    nadie vuelve a mirar, así que queda dicho: lo que cubre el `try` es lo que se lee abajo,
    no lo que promete este párrafo.

    Levanta `CuerpoIlegible`, que es del módulo: quien captura `ActuacionError` lo captura.
    """
    try:
        data = resp.json()
        if not isinstance(data, dict):
            return []
        crudo = data.get("items") or data.get("hydra:member") or []
        # **Que `json()` no lance NO acredita la forma.** R3/H-01: el `try` cubría solo la
        # decodificación, así que `{"items": 1}` reventaba DESPUÉS, al iterar, con un
        # `TypeError` que nadie captura — y lo hacía tras escribir en el CRM. Peor era
        # `{"items": "texto"}`: iterable, ninguna fila, y salía `[]` **en silencio**, que
        # significa «el CRM dice que no hay» — una afirmación que nadie había hecho.
        if not isinstance(crudo, list):
            raise TypeError(
                f"'items'/'hydra:member' no es una lista sino {type(crudo).__name__}")
        return [i for i in crudo if isinstance(i, dict)]
    except Exception as exc:  # noqa: BLE001 — cualquier cuerpo que no se pueda interpretar
        raise CuerpoIlegible(f"respuesta con cuerpo ilegible: {exc!r}") from exc


def _values(item: dict) -> dict[str, Any]:
    # `values: [null]` es dato del CRM, no un fallo del programa: la entrada ilegible se
    # ignora y las demás se leen (R3/H-01, que lo midió como `AttributeError` al aprender).
    return {(v.get("property") or {}).get("name", ""): v.get("value")
            for v in (item.get("values") or []) if isinstance(v, dict)}


# ---------------------------------------------------------------------------
# Paso 1 — el `id_predefinido`, con sus CUATRO salidas
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IdPredefinido:
    """Qué se sabe del `id_predefinido` de un asunto. **Cuatro estados, no dos.**

    - `aprendido` — una instancia real lo declara; va al POST.
    - `no_aplica` — **hay filas y todas traen el campo vacío**: esas actuaciones no nacen de
      plantilla y el campo **se omite**. `[APER-72]` lo midió sobre 20 instancias reales de
      `SENIOR - EXTRAJUDICIAL - REVISION VIABILIDAD`. Buscarlo y no encontrarlo es el
      resultado correcto, no un fallo: el paso 1 sirve para **no inventarlo**.
    - `sin_filas` — no hay instancias **de ese asunto exacto** que mirar. No se ha aprendido
      nada, y tampoco refutado. Incluye el caso en que el filtro `like` devolvió variantes:
      heredar su id sería inventarlo (R3/H-04).
    - `no_interpretable` — hay instancias y el campo trae algo que no es un entero. Se miró y
      no se entendió, que no es ni «no aplica» ni «no pude mirar» (R3/H-03).
    - `sin_comprobar` — la consulta no se pudo hacer. **No es ausencia.**

    Colapsar los cuatro últimos en «no hay id» lleva a inventar un entero, que es exactamente
    lo que el paso 1 de la receta existe para impedir. Y el motivo de cada uno **describe lo
    que se vio**: la R3 encontró un `no_aplica` que afirmaba haber visto el campo vacío sin
    haberlo visto, y una afirmación falsa en un motivo es peor que no tener motivo.
    """

    estado: str
    valor: int | None = None
    motivo: str = ""


def aprender_id_predefinido(asunto: str, *, client=None) -> IdPredefinido:
    """Paso 1: lee el `id_predefinido` de actuaciones ya creadas con ese asunto.

    El catálogo de predefinidas **no se expone como elemento REST**, así que se aprende de
    instancias reales. Filtra por el asunto **literal** del catálogo del manual: una variante
    histórica puede usar otro id, y una aproximación devolvería el de otra plantilla.
    """
    c = _cliente(client)
    params = {
        "page": 1, "itemsPerPage": 10,
        "properties[0]": "Subject", "properties[1]": "id_predefinido",
        "filterGroup[condition]": "AND",
        "filterGroup[filterGroups][0][condition]": "AND",
        "filterGroup[filterGroups][0][filters][0][operator]": "like",
        "filterGroup[filterGroups][0][filters][0][property]": "Subject",
        "filterGroup[filterGroups][0][filters][0][value]": asunto,
    }
    try:
        r = c.get("/api/element_registries/actuaciones", params=params)
    except Exception as exc:  # noqa: BLE001 — una red caída no es «no hay id»
        return IdPredefinido("sin_comprobar", motivo=f"red: {exc!r}")
    if getattr(r, "status_code", 0) != 200:
        return IdPredefinido("sin_comprobar", motivo=f"HTTP {r.status_code}")

    try:
        filas = _items(r)
    except CuerpoIlegible as exc:
        return IdPredefinido("sin_comprobar", motivo=str(exc))
    # **La evidencia tiene que ser de la operación que se va a ejecutar.** R3/H-04: el filtro
    # es `like`, así que pedir `SENIOR - X` trae también `SENIOR - X AMPLIADA`; se tomaba el
    # primer entero de CUALQUIER fila, y permutar el orden de la respuesta cambiaba el id
    # aprendido. El docstring de arriba ya exigía el asunto literal — el código no lo miraba.
    pedido = (asunto or "").strip()
    propias = [f for f in filas if str(_values(f).get("Subject") or "").strip() == pedido]
    if not propias:
        return IdPredefinido("sin_filas", motivo=(
            f"ninguna de las {len(filas)} fila(s) que devolvió el filtro tiene el asunto "
            f"{pedido!r} exacto: heredar el id de una variante sería inventarlo"))

    ilegibles: list[str] = []
    for f in propias:
        bruto = _values(f).get("id_predefinido")
        if bruto in (None, "", 0):
            continue
        try:
            return IdPredefinido("aprendido", valor=int(bruto))
        except (TypeError, ValueError):
            ilegibles.append(repr(bruto))
    # **Haber mirado y no entender lo que hay es un tercer estado.** R3/H-03: un valor no
    # convertible caía en `no_aplica` con el motivo «las instancias reales traen el campo
    # vacío» — una afirmación sobre lo observado que era falsa. Se declara lo que se vio.
    if ilegibles:
        return IdPredefinido("no_interpretable", motivo=(
            f"{len(propias)} fila(s) con ese asunto y el campo trae {', '.join(ilegibles)}, "
            "que no es un entero: no se escribe un id que no se ha podido leer"))
    return IdPredefinido("no_aplica", motivo=(
        f"las {len(propias)} instancia(s) reales de {pedido!r} traen el campo vacío"))


# ---------------------------------------------------------------------------
# Paso 2 — el profesional es el USERNAME
# ---------------------------------------------------------------------------


def _precio_de(firmante: str) -> str:
    """La tarifa del firmante, de la MISMA fila que decide su prefijo.

    Levanta si no está en la tabla, igual que `asunto_canonico`: elegir una tarifa por defecto
    factura al cliente la de otro, y ese es justo el error que la tabla existe para impedir.
    """
    f = (firmante or "").strip()
    if f not in _PRECIO_POR_FIRMANTE:
        raise ValueError(
            f"firmante {f!r} no está en la tabla de tarifas "
            f"({', '.join(sorted(_PRECIO_POR_FIRMANTE))}): el precio/hora NO se elige por "
            "defecto, porque eso factura al cliente la tarifa de otro. Añádelo con la suya.")
    return _PRECIO_POR_FIRMANTE[f]


def resolver_profesional(username: str) -> str:
    """Paso 2: `profesional_asignado` es el **username** (`Nikolai_Tyukhay`), no el id.

    El id de `empleados` —Ana es el 8— **no vale aquí**. La función existe para que el nombre
    del parámetro diga qué se espera; no consulta nada.
    """
    u = (username or "").strip()
    if not u:
        raise ValueError("profesional_asignado vacío: es el username del CRM, no el id")
    if u.isdigit():
        raise ValueError(
            f"profesional_asignado={u!r} parece un id de empleado; aquí va el USERNAME "
            "(p. ej. 'Nikolai_Tyukhay')")
    return u


# ---------------------------------------------------------------------------
# Paso 3 — el destino se acredita antes de escribir
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Destino:
    elemento: str
    exp_id: str
    #: Lo que se leyó del expediente y permitió acreditarlo. Va al log, no a la decisión.
    evidencia: str


def resolver_destino(
    elemento: str, exp_id: str, referencia_esperada: str, *, client=None,
) -> Destino:
    """Paso 3: contrasta que `(elemento, exp_id)` es el expediente que se cree, **antes** de
    escribir.

    **Cada elemento numera aparte.** En W-02VEKE, `464` es de `extrajudiciales` y `540` de
    `expedientes_judiciales`, y `GET expedientes_judiciales/464` devuelve un expediente de
    **otro caso**, con 200 y todo. Pasar el par no acredita a qué caso pertenece, y
    `_link_rest` documenta devolver **201 sobre un expediente inexistente**.

    Y esto no lo puede cazar el paso 6, porque usa la misma dirección que la escritura:
    **verificar la llegada no verifica la intención.**

    Se compara por W-code, que es lo que identifica el caso; el resto de la referencia cambia
    de forma entre fuentes. No poder leer el expediente **tampoco acredita**: se levanta.
    """
    prop = _PROP_REFERENCIA.get(elemento)
    if not prop:
        raise DestinoNoAcreditado(
            f"elemento {elemento!r} desconocido: no se sabe cómo se llama su referencia")
    c = _cliente(client)
    params = {
        "properties[0]": prop,
        "filterGroup[condition]": "AND",
        "filterGroup[filterGroups][0][condition]": "AND",
        "filterGroup[filterGroups][0][filters][0][operator]": "equal",
        "filterGroup[filterGroups][0][filters][0][property]": "id",
        "filterGroup[filterGroups][0][filters][0][value]": str(exp_id),
    }
    try:
        r = c.get(f"/api/element_registries/{elemento}", params=params)
    except Exception as exc:  # noqa: BLE001
        raise DestinoNoAcreditado(
            f"no se pudo leer {elemento}/{exp_id} para acreditarlo: {exc!r}. "
            "No se escribe nada.") from exc
    if getattr(r, "status_code", 0) != 200:
        raise DestinoNoAcreditado(
            f"no se pudo leer {elemento}/{exp_id} (HTTP {r.status_code}). No se escribe nada.")

    try:
        filas = _items(r)
    except CuerpoIlegible as exc:
        raise DestinoNoAcreditado(
            f"no se pudo interpretar la respuesta de {elemento}/{exp_id} ({exc}). "
            "No se escribe nada.") from exc
    if not filas:
        raise DestinoNoAcreditado(f"{elemento}/{exp_id} no devolvió ninguna fila")

    # **La fila que se lee es la que se pidió.** El filtro va por `id`, pero leer `filas[0]`
    # sin comprobarlo acredita el destino con la referencia de OTRO expediente si el filtro no
    # muerde o si el CRM devuelve más de una fila — en la función cuyo cometido entero es
    # «verificar por resultado, nunca por status».
    propia = [f for f in filas if str(f.get("id") or "").strip() == str(exp_id)]
    if not propia:
        raise DestinoNoAcreditado(
            f"{elemento}/{exp_id}: la consulta devolvió {len(filas)} fila(s) y ninguna tiene "
            f"ese id ({[str(f.get('id')) for f in filas]}). No se escribe nada.")
    leida = str(_values(propia[0]).get(prop) or "")

    # **El W-code se compara ENTERO, con el helper del módulo hermano.** La regex propia
    # capturaba 5-6 caracteres sin fronteras, así que `W-ABCDEF1` y `W-ABCDEF2` colapsaban en
    # el mismo código y acreditaban el mismo destino. `wcode_match` admite 5-8 con fronteras y
    # compara el código PRINCIPAL, así que una referencia leída que solo menciona el esperado
    # de pasada tampoco acredita. El plan ya mandaba usarlo; escribir una regex nueva teniendo
    # el helper delante fue el defecto.
    from core.sudespacho_relations import wcode_match

    if not wcode_match(referencia_esperada, leida):
        raise DestinoNoAcreditado(
            f"{elemento}/{exp_id} tiene la referencia {leida!r} y se esperaba "
            f"{referencia_esperada!r}: cada elemento numera aparte y este par apunta a otro "
            "caso. No se escribe nada.")
    return Destino(elemento=elemento, exp_id=str(exp_id), evidencia=leida)


# ---------------------------------------------------------------------------
# El asunto canónico — el prefijo ES la tarifa
# ---------------------------------------------------------------------------


def asunto_canonico(base: str, *, firmante: str) -> str:
    """El `Subject` con el prefijo de **quien firma**, que es lo que fija la tarifa.

    `[APER-72]`, medido sobre 20 actuaciones reales: `SENIOR - EXTRAJUDICIAL - REVISION
    VIABILIDAD` factura a **103,00 €/h** y las `ABOGADO - …` a **77,00**. Copiar el prefijo
    equivocado **factura al cliente la tarifa de otro**, así que esta función **no tiene
    defecto**: sin firmante, levanta.

    **Y el firmante no se infiere de quien opera** (R1/H-05): Ana puede tramitar una revisión
    que firma Nikolai, y el actor de la UI identifica a quien teclea. Es una entrada humana
    explícita — el campo `firmante:` del `_ficha_crm.yaml`.

    Un `base` que ya trae el prefijo **de ese mismo firmante** se deja como está; si trae el de
    otro, se levanta en vez de corregirlo en silencio: quien lo escribió puede tener razón y
    ser el firmante lo que está mal, y esa diferencia la tiene que ver una persona.
    """
    f = (firmante or "").strip()
    if not f:
        raise ValueError(
            "asunto_canonico exige 'firmante': el prefijo del Subject ES la tarifa "
            "(SENIOR 103,00 €/h vs ABOGADO 77,00) y elegirlo por defecto factura al cliente "
            "la tarifa de otro. No se infiere de quien opera.")
    prefijo = _PREFIJO_POR_FIRMANTE.get(f)
    if not prefijo:
        raise ValueError(
            f"firmante {f!r} no está en la tabla de prefijos ({', '.join(sorted(_PREFIJO_POR_FIRMANTE))}): "
            "añádelo con su tarifa en vez de dejar que se elija una por defecto")

    texto = (base or "").strip()
    # **La detección tolera las variantes de formato.** Exigir `"ABOGADO - "` literal dejaba
    # pasar `ABOGADO  -  X`, y el resultado era un asunto DOBLE (`SENIOR - ABOGADO  -  X`) en
    # vez de la revisión humana que el runbook exige. Reconocer un valor estructurado obliga a
    # decidir qué se hace con sus variantes ANTES de aplicar la política.
    m = _RE_PREFIJO.match(texto)
    if m:
        hallado = m.group(1).upper()
        if hallado != prefijo:
            raise ValueError(
                f"el asunto ya lleva el prefijo {hallado!r} y el firmante {f!r} factura como "
                f"{prefijo!r}. No se corrige en silencio: revisa cuál de los dos está mal.")
        # El catálogo es mayúsculas y el prefijo es la tarifa: no se conserva la caja de entrada.
        return f"{prefijo} - {texto[m.end():].strip()}"
    return f"{prefijo} - {texto}"


# ---------------------------------------------------------------------------
# La duración — qué fichero y qué ventana
# ---------------------------------------------------------------------------


def _fecha(valor: str, *, campo: str) -> datetime:
    try:
        return datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{campo}={valor!r} no es una fecha ISO legible") from exc


def duracion_desde_ronda(case_dir: Path) -> int | None:
    """Segundos entre `iniciada` y `terminada` de la ronda V1, o `None` si no cerró.

    **Qué fichero, porque el handoff se equivocaba:** `00_Input/_apertura_v1.json`, no
    `estado.json` — ese nombre no existe en el árbol. Y **el evento `apertura_v1_terminada`
    del log NO lleva las fechas** (sus `details` son `estado`, `parada`, `pendientes`,
    `etapas`), así que un consumidor del log no puede derivar esto (R1/H-07).

    **Y qué ventana mide, que es lo que hay que saber antes de facturarla:** la ronda V1 es
    Drive → CRM → sala de máquina. **No incluye la revisión de viabilidad posterior**, que es
    donde está el trabajo del letrado. Una resta correcta sobre la ventana equivocada sigue
    dando una duración equivocada. El marcador además se reemplaza al abrir otra ronda: esto
    no es un histórico.

    `None` cuando no hay ronda o no cerró — **declarado, no supuesto como cero**. Una fecha
    ilegible o unos extremos invertidos levantan: una resta negativa no es una duración.
    """
    from core import apertura_v1_estado as est

    ronda = est.leer(Path(case_dir))
    if ronda is None or not ronda.terminada:
        return None
    ini = _fecha(ronda.iniciada, campo="iniciada")
    fin = _fecha(ronda.terminada, campo="terminada")
    # **Zona en los DOS extremos** (diseño §4.4). `fromisoformat` admite fechas ingenuas, así
    # que dos sin zona restaban y devolvían un número; y una mezclada levantaba `TypeError` de
    # Python en vez de un error de dato legible. Poder restar dos representaciones temporales
    # no acredita una duración entre instantes.
    sin_zona = [c for c, v in (("iniciada", ini), ("terminada", fin)) if v.tzinfo is None]
    if sin_zona:
        raise ValueError(
            f"{' y '.join(sin_zona)} sin zona horaria: no se puede saber a qué instante "
            "corresponde, así que la resta no sería una duración")
    seg = (fin - ini).total_seconds()
    if seg < 0:
        raise ValueError(
            f"la ronda acaba ({ronda.terminada}) antes de empezar ({ronda.iniciada}): "
            "no es una duración, es un dato roto")
    return int(seg)


# ---------------------------------------------------------------------------
# Pasos 4-6 y el recibo
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Recibo:
    """Qué quedó escrito en el CRM, para poder REANUDAR en vez de repetir.

    **Una verificación negativa no es ausencia de escritura** (R1/H-04). Si el paso 4 crea la
    actuación N y el paso 5 falla, repetir el alta entera crea M, M se vincula y **N queda
    huérfana** — el POST de creación no está acreditado como idempotente, y la idempotencia
    documentada de `relation_element` solo evita repetir *el mismo vínculo*.

    Tres estados terminales:

    - `verificada` — los seis pasos, comprobado del lado del expediente.
    - `incompleta` — hay efecto en el CRM y se conoce el id: **se reanuda con `desde=`**.
      Reintentar el alta completa en este estado **está prohibido**.
    - `incierta` — el POST no dio recibo (un timeout deja hasta el id en duda). Se declara y
      se concilia a mano; no se reintenta a ciegas.
    """

    estado: str
    act_id: str | None = None
    paso: int = 0
    #: A qué expediente pertenece `act_id`. **Acreditar el destino no acredita el objeto que se
    #: le vincula**: son dos identidades, y sin esto reanudar con el recibo equivocado vincula
    #: una actuación ajena — y el paso 6 la da por verificada, porque sí aparece del lado de
    #: ESE expediente.
    elemento: str = ""
    exp_id: str = ""
    motivo: str = ""


def crear_actuacion(
    asunto: str, *, profesional: str, id_predefinido: int | None = None,
    duracion_s: int | None = None, fecha: str | None = None,
    vence: str | None = None, descripcion: str = "",
    facturar: bool = True, tipo_facturacion: str = "duracion",
    unidades: int | None = None, precio_unidad: str | None = None,
    extra: dict | None = None, client=None,
) -> str:
    """Paso 4: `POST element_register/actuaciones`. Devuelve el id creado.

    `duracion` va en `HH:MM:SS`; `facturar`/`obligacion` como booleanos; `Prioridad` es
    obligatoria. `id_predefinido` **se omite** cuando no aplica: no se manda vacío ni cero.

    **`fecha` y `precio_hora` los pone esta función, y eso lo compró una corrida en vivo.** La
    actuación creada el 2026-09-14 salió con `fecha_alta` vacía y `precio_hora = 0,00` mientras
    las 40 reales muestreadas traían las dos. Una actuación sin fecha no se puede facturar y una
    a cero no cobra: las dos parecen completas en el listado. `fecha` por defecto es **hoy**,
    que es lo que significa dar de alta una actuación ahora.

    `vence` (`fecha_vencimiento`, `DateTime`) es opcional y **no tiene defecto**: no toda
    actuación vence, y poner una fecha límite que nadie pidió es inventar un compromiso.
    """
    _validar_facturacion(tipo_facturacion)
    c = _cliente(client)
    cuerpo: dict[str, Any] = {
        "Subject": asunto,
        "profesional_asignado": resolver_profesional(profesional),
        "Estado": _ESTADOS_ACTUACION[0],
        "Prioridad": _PRIORIDAD_POR_DEFECTO,
        "facturar": bool(facturar),
        "obligacion": False,
        # **Sin `tipo_facturacion` la tarifa no se aplica.** Es la casilla «Facturar por
        # duración» de la UI, y sin ella una actuación con `facturar=1` y `precio_hora` puesto
        # sigue sin cobrar: el CRM no sabe por qué eje facturarla. Los tres campos van juntos.
        "tipo_facturacion": tipo_facturacion if facturar else "",
        "fecha_alta": fecha or datetime.now().strftime("%Y-%m-%d"),
        # **La terna entera o nada.** Si no se factura, no se declara tarifa: dos campos
        # diciendo cosas distintas sobre lo mismo es el defecto que esta pieza ya pagó una vez
        # (`SENIOR - …` en el asunto y `0,00` en el precio).
        "precio_hora": _precio_de(profesional) if facturar else "0.00",
    }
    if vence:
        cuerpo["fecha_vencimiento"] = vence
    if descripcion:
        cuerpo["Description"] = descripcion
    # Facturación por unidades: el otro eje. `unidades` × `precio_unidad`, y entonces la
    # duración no manda. `total` lo calcula el CRM: no se escribe desde aquí.
    if unidades is not None:
        cuerpo["unidades"] = int(unidades)
    if precio_unidad is not None:
        cuerpo["precio_unidad"] = str(precio_unidad)
    if id_predefinido is not None:
        cuerpo["id_predefinido"] = int(id_predefinido)
    if duracion_s is not None:
        h, resto = divmod(int(duracion_s), 3600)
        m, s = divmod(resto, 60)
        cuerpo["duracion"] = f"{h:02d}:{m:02d}:{s:02d}"
    # **`extra` no puede pisar lo que se acaba de validar.** Iba detrás de la construcción,
    # así que permitía sustituir `Subject`, `profesional_asignado` e `id_predefinido` — y con
    # eso se eluden a la vez el prefijo del firmante (que ES la tarifa), la prohibición de
    # pasar un id numérico de empleado y la evidencia del paso 1. La frontera: la validación
    # se aplica al objeto FINAL que cruza la frontera de escritura, no a un borrador que luego
    # se puede sobrescribir. Los extras legítimos —`fecha_vencimiento`— siguen entrando.
    _validar_extra(extra)
    cuerpo.update(extra or {})

    r = c.post("/api/element_register/actuaciones", json=cuerpo)
    if getattr(r, "status_code", 0) != 201:
        raise ActuacionError(
            f"POST actuaciones → HTTP {r.status_code}: {getattr(r, 'text', '')[:200]}")
    act_id = str((r.json() or {}).get("id") or "").strip()
    if not act_id:
        raise ActuacionError("POST actuaciones devolvió 201 sin id: no hay recibo que reanudar")
    return act_id


def cerrar_actuacion(act_id: str, *, fecha_fin: str | None = None,
                     duracion_s: int | None = None, client=None) -> None:
    """Pasa una actuación de `Planificado` a `Hecho`. **Y le pone su fecha de fin.**

    Las dos cosas van juntas porque así están en los datos: de las actuaciones reales en
    `Hecho`, la fecha de fin viene poblada (3 de 4 en la muestra del 2026-09-14), y una
    actuación cerrada sin fecha no dice cuándo se hizo — que es justo lo que se factura.
    `fecha_fin` por defecto es **hoy**.

    **Verifica por lectura, no por status.** El `PUT` de este CRM devuelve 200 con soltura;
    lo que acredita el cambio es releer el registro. Es la regla dura del §14.6 y en esta
    misma pieza ya mordió: un `POST` de relación devolvía 201 sin crear nada.
    """
    cuerpo: dict[str, Any] = {
        "Estado": "Hecho",
        "fecha_fin": fecha_fin or datetime.now().strftime("%Y-%m-%d"),
    }
    if duracion_s is not None:
        h, resto = divmod(int(duracion_s), 3600)
        m, sg = divmod(resto, 60)
        cuerpo["duracion"] = f"{h:02d}:{m:02d}:{sg:02d}"

    c = _cliente(client)
    r = c.put(f"/api/element_register/actuaciones/{act_id}", json=cuerpo)
    if getattr(r, "status_code", 0) != 200:
        raise ActuacionError(
            f"PUT actuaciones/{act_id} → HTTP {r.status_code}: "
            f"{getattr(r, 'text', '')[:200]}")
    if not _estado_es(act_id, "Hecho", client=c):
        raise ActuacionError(
            f"el PUT sobre la actuación {act_id} devolvió 200 y al releerla NO está en "
            "'Hecho'. No se da por cerrada: verificar por resultado, nunca por status.")


def _estado_es(act_id: str, esperado: str, *, client) -> bool:
    """¿Está la actuación en ese estado? Releyéndola, que es lo único que lo acredita."""
    try:
        r = client.get("/api/element_registries/actuaciones", params={
            "properties[0]": "Estado",
            "filterGroup[condition]": "AND",
            "filterGroup[filterGroups][0][condition]": "AND",
            "filterGroup[filterGroups][0][filters][0][operator]": "equal",
            "filterGroup[filterGroups][0][filters][0][property]": "Estado",
            "filterGroup[filterGroups][0][filters][0][value]": esperado,
        })
        if getattr(r, "status_code", 0) != 200:
            return False
        return any(str(f.get("id") or "") == str(act_id) for f in _items(r))
    except Exception:  # noqa: BLE001 — no poder comprobar NO es haber comprobado
        return False


def vincular_actuacion(elemento: str, exp_id: str, act_id: str, *, client=None) -> None:
    """Paso 5: `POST relation_element`. **Sin esto la actuación queda huérfana.**

    Y el POST del paso 4 devuelve 201 igual: el status no distingue una actuación colgada de
    una perdida. `relatedElement`/`relatedId` en la creación **no vinculan** — se ignoran en
    silencio (`[APER-24]`).
    """
    c = _cliente(client)
    r = c.post(f"/api/relation_element/{elemento}/{exp_id}",
               json=[f"right.actuaciones.{act_id}"])
    if getattr(r, "status_code", 0) != 201:
        raise ActuacionError(
            f"POST relation_element/{elemento}/{exp_id} → HTTP {r.status_code}: "
            f"{getattr(r, 'text', '')[:200]}")


def verificar_actuacion_vinculada(
    elemento: str, exp_id: str, act_id: str, *, client=None,
) -> bool:
    """Paso 6: relee **del lado del expediente**, que es lo único que prueba el vínculo.

    Un `GET element_registries/actuaciones` filtrando por el `id` de la actuación devuelve
    **404 aunque la actuación exista**: no sirve como comprobación.
    """
    c = _cliente(client)
    params = {
        "properties[0]": "Subject",
        "filterGroup[condition]": "AND",
        "filterGroup[filterGroups][0][condition]": "AND",
        "filterGroup[filterGroups][0][filters][0][operator]": "associated",
        "filterGroup[filterGroups][0][filters][0][property]": f"left.{elemento}.id",
        "filterGroup[filterGroups][0][filters][0][value]": str(exp_id),
    }
    try:
        r = c.get("/api/element_registries/actuaciones", params=params)
    except Exception:  # noqa: BLE001 — no poder verificar NO es haber verificado
        return False
    if getattr(r, "status_code", 0) != 200:
        return False
    try:
        return any(str(i.get("id") or "") == str(act_id) for i in _items(r))
    except CuerpoIlegible:
        return False        # no poder verificar NO es haber verificado


#: Enum `Tipo` del elemento `calendario`, del atlas (`CRM_SUDESPACHO_ATLAS.md`, §calendario) y
#: verificado en vivo. `Vencimiento` es el que corresponde a una fecha límite de una actuación.
_TIPOS_EVENTO = ("Aviso", "Evento", "Llamada", "Recordatorio", "Señalamiento", "Vencimiento")

#: Vocabulario de `recordatorios`. **No es un enum declarado**: vive dentro de un blob
#: serializado y ningún endpoint lo lista — se comprobó, y `/api/view/enums/calendario/
#: recordatorios` da 500, `/api/lists` devuelve `[]` y el campo sale como `TextArea` pelado.
#:
#: Los cinco valores están acreditados, pero **por dos vías que no valen lo mismo**, y la
#: distinción se conserva porque dice cuánta confianza merece cada uno:
#:
#: - `_EN_DATOS` — aparecen en el barrido de los **2.309** eventos con recordatorio del tenant
#:   (2026-09-14): `day` (284), `minute` (67), `month` (2). Acredita que la grafía **existe**.
#: - `_CONFIRMADOS_UI` — `hour` y `year` **no aparecían en ningún dato**. Se escribieron por
#:   API en dos actuaciones sonda y **la UI los pintó** como «3 horas antes» y «3 años antes».
#:   Eso es más fuerte que el barrido: prueba que el CRM **entiende** el valor, no solo que
#:   alguien lo guardó alguna vez.
#:
#: Se hizo así porque equivocarse aquí es **silencioso**: una grafía mala se serializa, se
#: guarda sin error y el recordatorio no salta nunca.
_REC_TIPOS = ("correo_electronico", "ventana_emergente")
_REC_TIEMPOS_EN_DATOS = ("day", "minute", "month")
_REC_TIEMPOS_CONFIRMADOS_UI = ("hour", "year")
_REC_TIEMPOS = _REC_TIEMPOS_EN_DATOS + _REC_TIEMPOS_CONFIRMADOS_UI


def _php(valor) -> str:
    """Serializa a la forma de PHP, que es lo que guardan `recordatorios` e `invitadosexternal`.

    Solo cubre lo que estos dos campos necesitan —cadenas, enteros, listas y diccionarios—,
    porque un serializador general aquí sería código que nadie ejerce.

    **La longitud va en BYTES.** PHP cuenta bytes, no caracteres: con una tilde en un email o
    en un nombre, contar caracteres produce una cadena que el CRM **guarda igual** y luego no
    sabe releer. El defecto no se ve al escribir.
    """
    if isinstance(valor, bool):     # antes que int: en Python `bool` es `int`
        return "b:" + ("1" if valor else "0") + ";"
    if isinstance(valor, int):
        return f"i:{valor};"
    if isinstance(valor, str):
        return f's:{len(valor.encode("utf-8"))}:"{valor}";'
    if isinstance(valor, (list, tuple)):
        cuerpo = "".join(f"i:{i};{_php(v)}" for i, v in enumerate(valor))
        return f"a:{len(valor)}:{{{cuerpo}}}"
    if isinstance(valor, dict):
        cuerpo = "".join(f"{_php(k)}{_php(v)}" for k, v in valor.items())
        return f"a:{len(valor)}:{{{cuerpo}}}"
    raise TypeError(f"no sé serializar {type(valor).__name__} a PHP")


def _html_de(texto: str) -> str:
    """Texto plano → HTML mínimo. Ya-HTML se deja intacto.

    Se **escapa** antes de envolver: una nota con `&` o `<` mandada cruda rompe el marcado
    del editor, y el defecto solo se ve al abrir el registro.
    """
    t = (texto or "").strip()
    if t.startswith("<"):
        return t
    return "".join(f"<p>{_escapar(l)}</p>" for l in t.splitlines() if l.strip())


def _invitados_php(emails) -> str:
    """Los invitados van como array asociativo **clave = valor = email**.

    No es una elección: es la forma que tienen los eventos reales del tenant (20183, 20031).
    """
    return _php({e: e for e in emails})


def _validar_recordatorios(recordatorios) -> None:
    for i, r in enumerate(recordatorios or []):
        if not isinstance(r, dict):
            raise ValueError(f"recordatorio[{i}] no es un diccionario: {r!r}")
        if r.get("tipo") not in _REC_TIPOS:
            raise ValueError(
                f"recordatorio[{i}]: tipo={r.get('tipo')!r} no es ninguno de los observados "
                f"({' · '.join(_REC_TIPOS)})")
        if r.get("tiempo") not in _REC_TIEMPOS:
            raise ValueError(
                f"recordatorio[{i}]: tiempo={r.get('tiempo')!r} no es ninguno de los "
                f"observados ({' · '.join(_REC_TIEMPOS)})")
        if not isinstance(r.get("cuanto"), int) or isinstance(r.get("cuanto"), bool):
            raise ValueError(
                f"recordatorio[{i}]: cuanto={r.get('cuanto')!r} tiene que ser un entero")


def crear_evento_calendario(
    asunto: str, *, inicio: str, fin: str, profesional: str,
    tipo: str = "Vencimiento", descripcion: str = "",
    recordatorios=None, invitados=None,
    de_actuacion: str | None = None, client=None,
) -> str:
    """Crea un evento en el `calendario` del CRM y devuelve su id.

    **`calendario` es un elemento normal** cuyo *parent* puede ser `actuaciones`
    (`CRM_SUDESPACHO_ATLAS.md` §calendario), así que se crea con la misma receta que todo lo
    demás y se cuelga de la actuación con `relation_element`. No hace falta el host de
    calendario (`api-calendar-commons-pro…`), que es otra cosa: ese sirve notificaciones y
    salas, no el alta del evento.

    `inicio` y `fin` son `DateTime`; si `fin` es anterior a `inicio` se levanta **antes** de
    escribir — un evento que termina antes de empezar no es un evento, y descubrirlo por el
    rechazo del POST produce la incertidumbre sobre el efecto que esta pieza evita.
    """
    if tipo not in _TIPOS_EVENTO:
        raise ValueError(
            f"Tipo={tipo!r} no está en el enum de `calendario` ({' · '.join(_TIPOS_EVENTO)})")
    if not (inicio or "").strip() or not (fin or "").strip():
        raise ValueError("un evento necesita inicio y fin: sin ellos no se puede agendar")
    if str(fin) < str(inicio):
        raise ValueError(
            f"el evento termina ({fin}) antes de empezar ({inicio}): no se escribe nada")
    _validar_recordatorios(recordatorios)

    c = _cliente(client)
    cuerpo = {
        "Subject": asunto,
        "Tipo": tipo,
        "Estado": _ESTADOS_ACTUACION[0],
        "Prioridad": _PRIORIDAD_POR_DEFECTO,
        "StartTime": inicio,
        "EndTime": fin,
        "profesional_asignado": resolver_profesional(profesional),
        "IsAllDayEvent": False,
        # **El array vacío se manda, no se omite.** `a:0:{}` es lo que escribe la UI, y
        # para quien lea el registro después «no hay ninguno» y «nadie tocó el campo» no
        # son lo mismo.
        "recordatorios": _php(list(recordatorios or [])),
        "invitadosexternal": _invitados_php(invitados or []),
    }
    if descripcion:
        cuerpo["Description"] = descripcion
    # **La UI ata el evento a su actuación por CAMPO, no por relación** — medido el 2026-09-14
    # comparando el evento 20234 (creado desde la UI) con el 20235 (creado por esta función):
    # el de la UI lleva `miembro=<act_id>` + `elemento='actuaciones'` y **no** tiene relación con
    # la actuación; el mío tenía la relación y `miembro` vacío. Los dos «funcionan», pero solo
    # uno se ve donde el despacho lo busca, que es el panel de la actuación. Se replica el de
    # la UI: quien lea esto mañana compara con lo que ve en pantalla, no con lo que yo decidí.
    if de_actuacion:
        cuerpo["miembro"] = int(de_actuacion)
        cuerpo["elemento"] = "actuaciones"
    r = c.post("/api/element_register/calendario", json=cuerpo)
    if getattr(r, "status_code", 0) != 201:
        raise ActuacionError(
            f"POST calendario → HTTP {r.status_code}: {getattr(r, 'text', '')[:200]}")
    ev_id = str((r.json() or {}).get("id") or "").strip()
    if not ev_id:
        raise ActuacionError("POST calendario devolvió 201 sin id: no hay recibo que reanudar")
    return ev_id


def vincular_evento(act_id: str, ev_id: str, *, client=None) -> None:
    """Cuelga el evento de la actuación. **Sin esto el evento queda suelto en la agenda.**

    Misma forma que el vínculo del paso 5 (`right.<hijo>.<id>` sobre el padre), que es la que
    `INTEGRACION_SUDESPACHO.md` §17.5 documenta y la que usa el resto de la pieza.
    """
    c = _cliente(client)
    r = c.post(f"/api/relation_element/actuaciones/{act_id}", json=[f"right.calendario.{ev_id}"])
    if getattr(r, "status_code", 0) not in (200, 201):
        raise ActuacionError(
            f"POST relación actuación {act_id} ↔ evento {ev_id} → HTTP {r.status_code}")


def crear_seguimiento(act_id: str, notas: str, *, asunto: str = "",
                      persona: str = "", client=None) -> str:
    """Añade un seguimiento —lo que la UI llama «Comentario»— a una actuación.

    **`seguimientos` es un elemento aparte, no un campo.** Su *parent* es `actuaciones`
    (`CRM_SUDESPACHO_ATLAS.md`), así que se crea y se cuelga con la misma receta de siempre. No
    confundirlo con `Description`, que sí es un campo de la actuación: la descripción es lo que
    la actuación **es**, y un seguimiento es algo que alguien **anotó después**, con su autor.

    `notas` es `EditorHtmlSimple`: el CRM guarda HTML. Un texto plano se envuelve en `<p>` y se
    escapa, porque mandarlo crudo deja que un `&` o un `<` de una nota rompan el marcado — y eso
    no se ve hasta que alguien abre el seguimiento.

    **Advertencia medida:** en el tenant hay **2** seguimientos en total (2026-09-14). Es un
    elemento poco usado, así que su contrato está menos acreditado que el resto de esta pieza.
    """
    if not (notas or "").strip():
        raise ValueError("un seguimiento sin notas no anota nada")
    cuerpo: dict[str, Any] = {"notas": _html_de(notas)}
    if asunto:
        cuerpo["asunto"] = asunto
    if persona:
        cuerpo["personaasignada"] = resolver_profesional(persona)
    c = _cliente(client)
    r = c.post("/api/element_register/seguimientos", json=cuerpo)
    if getattr(r, "status_code", 0) != 201:
        raise ActuacionError(
            f"POST seguimientos → HTTP {r.status_code}: {getattr(r, 'text', '')[:200]}")
    seg = str((r.json() or {}).get("id") or "").strip()
    if not seg:
        raise ActuacionError("POST seguimientos devolvió 201 sin id")
    # **Y aquí el status MIENTE, medido el 2026-09-14.** El `POST` de la relación devuelve
    # `201` y la relación **no aparece** al releer: `related_register/actuaciones/{id}` sigue
    # listando solo `extrajudiciales` y `calendario`. Se probaron las tres formas
    # (`right.` sobre la actuación, `right.` y `left.` desde el seguimiento) — dos dan 404 y la
    # tercera da 201 sin efecto. Es literalmente el caso que `DEAD_ENDS` recoge como «con
    # `right.` sobre el parent: 201 y nada».
    #
    # Así que esta función **verifica por resultado** y levanta si no lo consigue. Devolver el
    # id con un «ya está» apoyado en el 201 sería exactamente el defecto contra el que existe
    # el paso 6 de esta receta. El seguimiento creado **no se borra**: queda con su id en el
    # mensaje, para poder colgarlo a mano o recuperarlo.
    c.post(f"/api/relation_element/actuaciones/{act_id}", json=[f"right.seguimientos.{seg}"])
    if not _seguimiento_colgado(act_id, seg, client=c):
        raise ActuacionError(
            f"el seguimiento {seg} se CREÓ y no se pudo colgar de la actuación {act_id}: el "
            "POST de la relación devuelve 201 y al releer no está. La forma de atar un "
            "seguimiento a su actuación NO está acreditada (ver INTEGRACION §15.10). "
            f"Cuélgalo a mano desde la UI; el contenido está a salvo en el seguimiento {seg}.")
    return seg


def _seguimiento_colgado(act_id: str, seg: str, *, client) -> bool:
    """¿Consta el seguimiento entre las relaciones de la actuación? **Por lectura, no por status.**"""
    try:
        r = client.get(f"/api/related_register/actuaciones/{act_id}")
        if getattr(r, "status_code", 0) != 200:
            return False
        for bloque in (r.json() or []):
            if bloque.get("element") == "seguimientos" and seg in (bloque.get("registries") or {}):
                return True
    except Exception:  # noqa: BLE001 — no poder comprobar NO es haber comprobado
        return False
    return False


def _act_id_reanudable(desde: Recibo, destino) -> str | None:
    """Qué se puede reanudar de `desde`, o por qué no se puede. Levanta si no se puede.

    Devuelve el `act_id` a reanudar, o `None` cuando el recibo acredita que **no se escribió
    nada** y por tanto empezar de cero es seguro.

    **El contrato entero del recibo vive aquí, en un sitio.** R3/H-02 midió que estaba
    repartido en dos `if` del orquestador y que los dos se podían esquivar:

    - la guarda de identidad estaba condicionada a `desde.elemento`, que es `""` por defecto,
      así que un recibo construido con los valores por defecto **se saltaba justo la guarda
      que su ausencia debía disparar** — y vinculaba una actuación ajena a un expediente;
    - el estado no se comprobaba contra ningún vocabulario, así que `"inventado"` pasaba por
      no ser `incierta`. Una guarda que enumera lo prohibido deja pasar lo que no se le
      ocurrió; la que enumera lo permitido, no.
    """
    if desde.estado not in _ESTADOS_RECIBO:
        raise ActuacionError(
            f"recibo en un estado que no existe: {desde.estado!r}. Los válidos son "
            f"{', '.join(sorted(_ESTADOS_RECIBO))}. No se escribe nada.")
    if desde.paso not in _PASOS:
        raise ActuacionError(
            f"recibo con paso {desde.paso!r}, que no es ninguno de los seis de la receta: "
            "describe un recorrido que no existe. No se escribe nada.")
    if (desde.elemento or desde.exp_id) and \
            (desde.elemento, desde.exp_id) != (destino.elemento, destino.exp_id):
        raise ActuacionError(
            f"el recibo es de {desde.elemento}/{desde.exp_id} y se está reanudando sobre "
            f"{destino.elemento}/{destino.exp_id}: acreditar el destino no acredita el "
            "objeto que se le vincula. No se escribe nada.")

    # `no_intentada` significa exactamente «no se escribió»: reintentar entero es seguro **por
    # definición del estado**, y es lo que lo distingue de `incierta` (R3/H-06).
    if desde.estado == "no_intentada":
        return None

    # **El orden entre dos negativas no es indiferente: decide qué va a hacer quien lo lea.**
    # Ante un recibo `incierta`, «no dice a qué expediente» manda a arreglar lo accesorio; lo
    # que hay que oír es que puede haber una actuación suelta y sin id. Lo destapó el test de
    # la R2 al ponerse rojo con la ordenación contraria.
    if desde.estado == "incierta" or not desde.act_id:
        raise ActuacionError(
            f"no se reanuda un recibo en estado {desde.estado!r}: puede haber una "
            "actuación creada cuyo id no conocemos. Búscala en el CRM y concilia a mano; "
            "reintentar aquí crearía una segunda.")
    if not (desde.elemento and desde.exp_id):
        raise ActuacionError(
            "el recibo no dice a qué expediente pertenece su actuación, así que reanudarlo "
            "vincularía un id ajeno al destino que se acaba de acreditar. No se escribe nada.")
    return desde.act_id


def alta_actuacion(
    elemento: str, exp_id: str, referencia_esperada: str, *,
    asunto: str, firmante: str, duracion_s: int | None = None,
    vence: str | None = None, agenda: bool = True,
    recordatorios=None, invitados=None,
    descripcion: str = "", seguimientos=None,
    facturar: bool = True, tipo_facturacion: str = "duracion",
    unidades: int | None = None, precio_unidad: str | None = None,
    extra: dict | None = None, desde: Recibo | None = None, client=None,
) -> Recibo:
    """Los seis pasos, con recibo reanudable.

    `desde` reanuda sobre una actuación **ya creada**: se salta el paso 4 y se retoma el
    vínculo. Es la única forma correcta de reintentar un `Recibo` en estado `incompleta`;
    repetir el alta entera crearía una segunda actuación y dejaría la primera huérfana.

    El destino se acredita **siempre**, también al reanudar: es barato y es lo que impide
    escribir en el expediente de otro caso.

    **Esta función existe para encadenar, no para aplanar.** La R2 encontró seis defectos con
    una sola frontera detrás: *cada helper distingue estados que su único llamador colapsa*.
    Cada bloque de abajo conserva una distinción que antes se perdía aquí — el estado del paso
    1, el asunto que de verdad se escribe, la validación frente al fallo de red, y a qué
    expediente pertenece la actuación que se reanuda.
    """
    # **La validación va delante de todo lo que escribe.** Un `extra` inválido no puede
    # llegar a clasificarse como «el POST quizá creó algo» (R3/H-07).
    _validar_extra(extra)
    _validar_facturacion(tipo_facturacion)
    # El asunto canónico se calcula **antes de la bifurcación** porque lo necesitan los dos
    # caminos —crear y agendar— y porque valida el firmante sin haber tocado el CRM.
    canonico = asunto_canonico(asunto, firmante=firmante)
    resolver_profesional(firmante)

    destino = resolver_destino(elemento, exp_id, referencia_esperada, client=client)
    act_id = _act_id_reanudable(desde, destino) if desde is not None else None
    nota_paso1 = "reanudada: el paso 1 no se repite" if act_id else ""
    if act_id is None:
        # **El asunto que se aprende es el que se va a escribir.** Se consultaba el crudo y se
        # escribía el canónico: con `like` y sin prefijo, una consulta casa las filas `SENIOR`
        # **y** las `ABOGADO`, así que se aprendía la plantilla de la otra tarifa. El docstring
        # del propio paso 1 lo advierte, y su único llamador lo incumplía.
        #
        # Y la validación va FUERA del `try` que clasifica los fallos del POST: un firmante
        # vacío salía como «puede haberse creado una actuación: concilia a mano» **sin haber
        # tocado el CRM**. El diseño §4.3 dice que para y lo dice; paraba y decía otra cosa.
        pre = aprender_id_predefinido(canonico, client=client)
        # **Las salidas del paso 1 las consume alguien, y cada una dice otra cosa.**
        # `alta_actuacion` leía solo `pre.valor`, así que «no pude mirar el catálogo» era
        # indistinguible de «no aplica» — en un módulo cuya política declarada es fallar
        # cerrado ante lo no comprobado. La R3 midió que el remedio solo salvó una de las
        # cuatro: `sin_filas` y `no_aplica` seguían produciendo el mismo POST y el mismo
        # recibo, sin dejar en él **cuál de los dos** fue.
        #
        # Y el estado de parada es `no_intentada`, no `incompleta` (R3/H-06): `incompleta`
        # significa «existe algo escrito y falta rematarlo», así que reanudar aquel recibo
        # chocaba con la guarda del id y mandaba a conciliar a mano **un efecto inexistente**.
        # Es el modo de fallo de esta pieza —un remedio que crea el estado que el código
        # bloquea después— y van tres veces.
        if pre.estado in ("sin_comprobar", "no_interpretable"):
            return Recibo("no_intentada", paso=1, elemento=destino.elemento,
                          exp_id=destino.exp_id, motivo=(
                              f"no se pudo establecer el id_predefinido de {canonico!r} "
                              f"[{pre.estado}]: {pre.motivo}. NO se ha escrito nada; se puede "
                              "reintentar entero."))
        nota_paso1 = f"id_predefinido [{pre.estado}]: {pre.motivo or pre.valor}"
        try:
            act_id = crear_actuacion(
                canonico, profesional=firmante, id_predefinido=pre.valor,
                duracion_s=duracion_s, vence=vence, descripcion=descripcion,
                facturar=facturar, tipo_facturacion=tipo_facturacion,
                unidades=unidades, precio_unidad=precio_unidad,
                extra=extra, client=client,
            )
        except ActuacionError as exc:
            return Recibo("incierta", paso=4, elemento=destino.elemento,
                          exp_id=destino.exp_id, motivo=str(exc))
        except Exception as exc:  # noqa: BLE001 — sin respuesta, hasta el id está en duda
            return Recibo("incierta", paso=4, elemento=destino.elemento,
                          exp_id=destino.exp_id, motivo=(
                              f"el POST no dio recibo ({exc!r}): puede haberse creado una "
                              "actuación. NO se reintenta a ciegas; concilia a mano."))

    recibo = dict(act_id=act_id, elemento=destino.elemento, exp_id=destino.exp_id)
    try:
        vincular_actuacion(destino.elemento, destino.exp_id, act_id, client=client)
    except Exception as exc:  # noqa: BLE001
        return Recibo("incompleta", paso=4, motivo=(
            f"la actuación {act_id} EXISTE y no quedó vinculada ({exc!r}). "
            "Reanuda con desde=<este recibo>; no repitas el alta."), **recibo)

    # **En cuanto se ha escrito, el llamador recibe el `act_id` pase lo que pase.** R3/H-01:
    # esta llamada estaba fuera de todo `try`, así que una excepción inesperada del paso 6
    # atravesaba `alta_actuacion` **después de vincular** y el llamador se quedaba sin el id
    # de lo que acababa de crear. La respuesta natural a una excepción es repetir el alta, y
    # eso deja una actuación huérfana en el expediente de un cliente. La garantía es del
    # orquestador y no puede delegarse en que el helper siga capturando bien.
    try:
        vinculada = verificar_actuacion_vinculada(destino.elemento, destino.exp_id, act_id,
                                                  client=client)
    except Exception as exc:  # noqa: BLE001
        return Recibo("incompleta", paso=5, motivo=(
            f"la actuación {act_id} se creó y se vinculó, y no se pudo verificar del lado "
            f"del expediente ({exc!r}). Reanuda con desde=<este recibo>; no repitas el alta. "
            f"[{nota_paso1}]"), **recibo)
    if not vinculada:
        return Recibo("incompleta", paso=5, motivo=(
            f"la actuación {act_id} se creó y se vinculó, pero no aparece del lado del "
            f"expediente. Reanuda con desde=<este recibo>; no repitas el alta. "
            f"[{nota_paso1}]"), **recibo)
    # Los seguimientos van DESPUÉS de verificar y su fallo **no se lleva el recibo**: la
    # actuación ya existe. Un comentario que no se pudo anotar no justifica repetir el alta.
    for nota in (seguimientos or []):
        try:
            crear_seguimiento(act_id, nota, persona=firmante, client=client)
        except Exception as exc:  # noqa: BLE001
            return Recibo("incompleta", paso=6, motivo=(
                f"la actuación {act_id} está COMPLETA y un seguimiento no se pudo anotar "
                f"({exc!r}). Anótalo a mano; NO repitas el alta. [{nota_paso1}]"), **recibo)

    # **Paso 7 — la fecha límite se agenda, o no es una fecha límite.** Escribir
    # `fecha_vencimiento` en la actuación la deja en un campo que nadie mira: lo que avisa es el
    # evento del calendario. Va DESPUÉS de verificar, y su fallo **no se lleva el recibo**: la
    # actuación ya existe, está vinculada y verificada, y repetir el alta por un evento que no
    # se pudo agendar crearía una segunda. Misma invariante que el paso 6.
    if vence and agenda:
        try:
            # **El evento lleva el MISMO asunto que la actuación, y no es cosmética.**
            # Medido el 2026-09-14: con `miembro` puesto, el CRM **sincroniza el Subject del
            # evento sobre el de la actuación**. Con un título propio —se probó
            # `"VENCE — {asunto}"`— la actuación acabó llamándose así, y **el prefijo del
            # asunto ES la tarifa**: un título de evento que no empiece por el prefijo correcto
            # puede cambiar lo que se le factura al cliente. La UI le pone el mismo título, y
            # por eso allí la sincronización es inocua.
            ev = crear_evento_calendario(
                canonico,
                inicio=vence, fin=vence, profesional=firmante,
                tipo="Vencimiento", descripcion=f"Actuación {act_id} de {elemento}/{exp_id}",
                recordatorios=recordatorios, invitados=invitados,
                de_actuacion=act_id, client=client)
            vincular_evento(act_id, ev, client=client)
        except Exception as exc:  # noqa: BLE001
            return Recibo("incompleta", paso=7, motivo=(
                f"la actuación {act_id} está COMPLETA (creada, vinculada y verificada) y su "
                f"vencimiento {vence} no se pudo agendar ({exc!r}). Agenda el evento a mano; "
                f"NO repitas el alta. [{nota_paso1}]"), **recibo)
        return Recibo("verificada", paso=7,
                      motivo=f"{nota_paso1} · vence {vence}, evento {ev}", **recibo)
    return Recibo("verificada", paso=6, motivo=nota_paso1, **recibo)
