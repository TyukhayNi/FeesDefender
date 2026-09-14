"""Crear una actuación en el CRM sudespacho, encapsulando la receta verificada (`MEJORAS #209`).

**Por qué existe este módulo.** El backlog lo dice en una línea: «crear actuaciones en el CRM
no tiene helper: la receta vive en prosa y se reescribe a mano cada vez». Y la frontera que el
propio `#209` enuncia es más grande que el caso: *el contrato del CRM se documenta y no se
encapsula*, así que cada operación nueva se reescribe contra la prosa y hereda sus olvidos.

**La receta son SEIS pasos y ninguno es opcional** (`docs/INTEGRACION_SUDESPACHO.md §15.6`,
verificada de punta a punta el 2026-09-10 sobre W-02VEKE):

1. Aprender el `id_predefinido` de una instancia real — **no inventarlo**.
2. `profesional_asignado` es el **username**, no el id de `empleados`.
3. Resolver el expediente por su **elemento**, no por el número a secas, y contrastarlo.
4. POST de la actuación.
5. POST de vinculación — **sin él la actuación queda huérfana y el paso 4 devuelve 201 igual**.
6. Verificar releyendo **del lado del expediente**: el `GET` por id de la actuación devuelve
   **404 aunque exista**.

**Lo que este módulo NO hace:** aplicar la tarifa de usuario (es el botón de `§15.4`, solo UI)
y escribir `tipo_actuacion` (va vacío en las 20 instancias reales).

**Cómo se prueba sin tocar el CRM:** todas las funciones aceptan `client=`. Sin él construyen
uno con la `x-api-key` del entorno; con él, los tests inyectan un doble. Ningún test de este
módulo llama al tenant.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

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
_PREFIJO_POR_FIRMANTE = {
    "Nikolai_Tyukhay": "SENIOR",
    "ana.velastegui": "ABOGADO",
}

_PREFIJOS = tuple(sorted(set(_PREFIJO_POR_FIRMANTE.values())))
#: Campos del POST que materializan una decisión ya validada: `extra` no los toca.
_CAMPOS_DECIDIDOS = frozenset({"Subject", "profesional_asignado", "id_predefinido"})
#: Un prefijo al principio del asunto, tolerando caja y espacios de más.
_RE_PREFIJO = re.compile(r"^\s*(" + "|".join(_PREFIJOS) + r")\s*-\s*", re.I)


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

    Levanta `CuerpoIlegible`, que es del módulo: quien captura `ActuacionError` lo captura.
    """
    try:
        data = resp.json()
    except Exception as exc:  # noqa: BLE001 — cualquier cuerpo que no se pueda interpretar
        raise CuerpoIlegible(f"respuesta con cuerpo ilegible: {exc!r}") from exc
    if not isinstance(data, dict):
        return []
    return [i for i in (data.get("items") or data.get("hydra:member") or [])
            if isinstance(i, dict)]


def _values(item: dict) -> dict[str, Any]:
    return {(v.get("property") or {}).get("name", ""): v.get("value")
            for v in item.get("values", []) or []}


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
    - `sin_filas` — no hay instancias que mirar. No se ha aprendido nada, y tampoco refutado.
    - `sin_comprobar` — la consulta no se pudo hacer. **No es ausencia.**

    Colapsar los tres últimos en «no hay id» lleva a inventar un entero, que es exactamente lo
    que el paso 1 de la receta existe para impedir.
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
    if not filas:
        return IdPredefinido("sin_filas", motivo=f"ninguna actuación casa {asunto!r}")
    for f in filas:
        bruto = _values(f).get("id_predefinido")
        if bruto not in (None, "", 0):
            try:
                return IdPredefinido("aprendido", valor=int(bruto))
            except (TypeError, ValueError):
                continue
    return IdPredefinido("no_aplica", motivo="las instancias reales traen el campo vacío")


# ---------------------------------------------------------------------------
# Paso 2 — el profesional es el USERNAME
# ---------------------------------------------------------------------------


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
    duracion_s: int | None = None, extra: dict | None = None, client=None,
) -> str:
    """Paso 4: `POST element_register/actuaciones`. Devuelve el id creado.

    `duracion` va en `HH:MM:SS`; `facturar`/`obligacion` como booleanos; `Prioridad` es
    obligatoria. `id_predefinido` **se omite** cuando no aplica: no se manda vacío ni cero.
    """
    c = _cliente(client)
    cuerpo: dict[str, Any] = {
        "Subject": asunto,
        "profesional_asignado": resolver_profesional(profesional),
        "Estado": "Planificado",
        "Prioridad": "Normal",
        "facturar": True,
        "obligacion": False,
    }
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
    invasores = sorted(set(extra or {}) & _CAMPOS_DECIDIDOS)
    if invasores:
        raise ValueError(
            f"`extra` intenta sobrescribir campos ya validados: {', '.join(invasores)}. "
            "Esos los decide la propia función (el prefijo es la tarifa, el profesional es un "
            "username y el id_predefinido se aprende): pásalos por sus parámetros.")
    cuerpo.update(extra or {})

    r = c.post("/api/element_register/actuaciones", json=cuerpo)
    if getattr(r, "status_code", 0) != 201:
        raise ActuacionError(
            f"POST actuaciones → HTTP {r.status_code}: {getattr(r, 'text', '')[:200]}")
    act_id = str((r.json() or {}).get("id") or "").strip()
    if not act_id:
        raise ActuacionError("POST actuaciones devolvió 201 sin id: no hay recibo que reanudar")
    return act_id


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


def alta_actuacion(
    elemento: str, exp_id: str, referencia_esperada: str, *,
    asunto: str, firmante: str, duracion_s: int | None = None,
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
    destino = resolver_destino(elemento, exp_id, referencia_esperada, client=client)

    # **Reanudar es reanudar, no crear.** `incierta` significa «el POST pudo crear algo y no sé
    # el id»: su `act_id` es `None` por definición, así que caía al camino de creación sin
    # decir nada — justo lo que el diseño prohíbe, y en el único estado donde la API no podía
    # protegerse. La prohibición vivía en el docstring y no en el código.
    if desde is not None:
        if desde.estado == "incierta" or not desde.act_id:
            raise ActuacionError(
                f"no se reanuda un recibo en estado {desde.estado!r}: puede haber una "
                "actuación creada cuyo id no conocemos. Búscala en el CRM y concilia a mano; "
                "reintentar aquí crearía una segunda.")
        if desde.elemento and (desde.elemento, desde.exp_id) != (destino.elemento, destino.exp_id):
            raise ActuacionError(
                f"el recibo es de {desde.elemento}/{desde.exp_id} y se está reanudando sobre "
                f"{destino.elemento}/{destino.exp_id}: acreditar el destino no acredita el "
                "objeto que se le vincula. No se escribe nada.")

    act_id = desde.act_id if desde else None
    if act_id is None:
        # **El asunto que se aprende es el que se va a escribir.** Se consultaba el crudo y se
        # escribía el canónico: con `like` y sin prefijo, una consulta casa las filas `SENIOR`
        # **y** las `ABOGADO`, así que se aprendía la plantilla de la otra tarifa. El docstring
        # del propio paso 1 lo advierte, y su único llamador lo incumplía.
        #
        # Y la validación va FUERA del `try` que clasifica los fallos del POST: un firmante
        # vacío salía como «puede haberse creado una actuación: concilia a mano» **sin haber
        # tocado el CRM**. El diseño §4.3 dice que para y lo dice; paraba y decía otra cosa.
        canonico = asunto_canonico(asunto, firmante=firmante)
        resolver_profesional(firmante)

        pre = aprender_id_predefinido(canonico, client=client)
        # **Las cuatro salidas del paso 1 las consume alguien.** `alta_actuacion` leía solo
        # `pre.valor`, así que «no pude mirar el catálogo» era indistinguible de «no aplica» —
        # en un módulo cuya política declarada es fallar cerrado ante lo no comprobado.
        if pre.estado == "sin_comprobar":
            return Recibo("incompleta", paso=1, elemento=destino.elemento,
                          exp_id=destino.exp_id, motivo=(
                              f"no se pudo comprobar el id_predefinido de {canonico!r} "
                              f"({pre.motivo}). No se escribe sin saberlo."))
        try:
            act_id = crear_actuacion(
                canonico, profesional=firmante, id_predefinido=pre.valor,
                duracion_s=duracion_s, extra=extra, client=client,
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

    if not verificar_actuacion_vinculada(destino.elemento, destino.exp_id, act_id,
                                         client=client):
        return Recibo("incompleta", paso=5, motivo=(
            f"la actuación {act_id} se creó y se vinculó, pero no aparece del lado del "
            "expediente. Reanuda con desde=<este recibo>; no repitas el alta."), **recibo)
    return Recibo("verificada", paso=6, **recibo)
