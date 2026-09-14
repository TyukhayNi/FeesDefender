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
_RE_WCODE = re.compile(r"W-[0-9A-Z]{5,6}", re.I)


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


def _items(resp) -> list[dict]:
    """Las filas de un `element_registries`, con las dos formas que devuelve el CRM.

    Cuál llega **la elige la cabecera `Accept`**: `application/json` exacto da `items`;
    `ld+json`, `*/*` o ninguna dan `hydra:member`. No es una forma sustituyendo a otra
    (`INTEGRACION_SUDESPACHO.md §15.6`), así que se aceptan las dos.
    """
    data = resp.json()
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

    filas = _items(r)
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

    filas = _items(r)
    if not filas:
        raise DestinoNoAcreditado(f"{elemento}/{exp_id} no devolvió ninguna fila")
    leida = str(_values(filas[0]).get(prop) or "")

    esperados = {m.upper() for m in _RE_WCODE.findall(referencia_esperada or "")}
    leidos = {m.upper() for m in _RE_WCODE.findall(leida)}
    if not esperados or not leidos or not (esperados & leidos):
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
    for p in _PREFIJOS:
        if texto.upper().startswith(f"{p} - "):
            if p != prefijo:
                raise ValueError(
                    f"el asunto ya lleva el prefijo {p!r} y el firmante {f!r} factura como "
                    f"{prefijo!r}. No se corrige en silencio: revisa cuál de los dos está mal.")
            return texto
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
    return any(str(i.get("id") or "") == str(act_id) for i in _items(r))


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
    """
    destino = resolver_destino(elemento, exp_id, referencia_esperada, client=client)

    act_id = desde.act_id if (desde and desde.act_id) else None
    if act_id is None:
        pre = aprender_id_predefinido(asunto, client=client)
        try:
            act_id = crear_actuacion(
                asunto_canonico(asunto, firmante=firmante),
                profesional=firmante,
                id_predefinido=pre.valor,
                duracion_s=duracion_s,
                extra=extra,
                client=client,
            )
        except ActuacionError as exc:
            return Recibo("incierta", paso=4, motivo=str(exc))
        except Exception as exc:  # noqa: BLE001 — sin respuesta, hasta el id está en duda
            return Recibo("incierta", paso=4, motivo=(
                f"el POST no dio recibo ({exc!r}): puede haberse creado una actuación. "
                "NO se reintenta a ciegas; concilia a mano."))

    try:
        vincular_actuacion(destino.elemento, destino.exp_id, act_id, client=client)
    except Exception as exc:  # noqa: BLE001
        return Recibo("incompleta", act_id=act_id, paso=4, motivo=(
            f"la actuación {act_id} EXISTE y no quedó vinculada ({exc!r}). "
            "Reanuda con desde=<este recibo>; no repitas el alta."))

    if not verificar_actuacion_vinculada(destino.elemento, destino.exp_id, act_id,
                                         client=client):
        return Recibo("incompleta", act_id=act_id, paso=5, motivo=(
            f"la actuación {act_id} se creó y se vinculó, pero no aparece del lado del "
            "expediente. Reanuda con desde=<este recibo>; no repitas el alta."))
    return Recibo("verificada", act_id=act_id, paso=6)
