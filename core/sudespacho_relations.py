"""Operaciones de relación en sudespacho.net para FeesDefender.

Endpoints confirmados el 2026-04-29 contra el tenant tnm.sudespacho.net:

    1. Buscar expediente (extra)judicial por referencia_cliente (deduplicación)
       Desde 2026-06-12 vía REST: GET /api/element_registries/{element} con
       filtro operator=like sobre la property de referencia (x-api-key, sin
       PHPSESSID). El autocomplete legacy devolvía body vacío contra el CRM
       real (DEAD_ENDS, "Frontal heredado"). Ver _rest_search_expedientes().

    2. Buscar colaborador por email/nombre
       GET /autocompletar/buscar/elemento/colaboradores?term={term}&
       → [{id, label, value: "{colab_id}", data}]

    3. Vincular cliente al expediente (confirmado 2026-04-29)
       POST /clientespropios/saveselect/elemento/clientes_propios
            /elemento_relacionado/extrajudiciales
            /miembro_relacionado/{exp_id}
            /direccion_relacionado/der
       Body: seleccionado[]={client_id} + numeroresultados_listado=5
             + documentos_adjuntos_seleccionados= + csrf_token + cc-num
       Response: JSON {"resultado": true, "acumulaDatos": {...}}
       NOTA: el endpoint es saveselect (NO select), sin /elemento_relacion/ al final.

    4. Vincular colaborador al expediente (confirmado 2026-04-29)
       POST /views/saveselect/elemento/colaboradores
            /elemento_relacionado/extrajudiciales
            /miembro_relacionado/{exp_id}
            /direccion_relacionado/der
       Body: seleccionado[]={colab_id} + numeroresultados_listado=5
             + documentos_adjuntos_seleccionados= + csrf_token + cc-num
       Response: JSON {"resultado": true, "acumulaDatos": {...}}

    5. Crear colaborador nuevo (legacy fallback)
       POST /views/saveadd/elemento/colaboradores
       Body: campo_1086__colaboradores={nombre}
             campo_1080__colaboradores={email}
             campo_1083__colaboradores={movil}
             + csrf_token + cc-num + permisos + ajax=true
       Response: {"resultado": true, "dato": "{colab_id}", ...}

    5b. Crear colaborador nuevo (REST-first, confirmado 2026-05-06 HAR judicial_648.har)
        POST https://api-crm-commons-pro.sudespacho.biz/api/element_register/colaboradores
        Auth: x-api-key (clave estática — migrado a x-api-key el 2026-05-06, Opción A)
        Body: {"nombre": "...", "email": "..."}
        Response: {"id": 780, "message": "Created!"}
        Idéntico al patrón de create_expediente_rest().

Mapping de campos para colaboradores (confirmado 2026-04-29 legacy + 2026-05-06 REST):
    campo_1086 → nombre        (REST: "nombre")
    campo_1080 → Email         (REST: "email")
    campo_1084 → Nacionalidad  (REST: "nacionalidad", select, "1" = Sin Asignar)
    campo_1085 → NIF/CIF       (REST: "nif_cif")     ← ojo: nif_cif, no nif
    campo_1083 → Móvil         (REST: "movil")
    campo_1090 → Teléfono 1    (REST: "telefono1")   ← ojo: telefono1, no telefono
    campo_1091 → Teléfono 2    (REST: "telefono2")
    campo_1079 → Dirección     (REST: "direccion")
    campo_1089 → Provincia     (REST: "provincia")
    campo_1088 → Población     (REST: "poblacion")
    campo_1078 → CP            (REST: "cp")
    campo_1087 → Notas         (REST: "notas")

Constantes fijas del tenant tnm:
    EV_MMC_SPAIN_ID = "2"   (B65824054 - EV MMC SPAIN, S.L.U.)
    ID 73 = DUPLICADO — nunca usar
"""

from __future__ import annotations

import logging
import math
import os
import re
import unicodedata
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any

import httpx

from .sync_sudespacho import SudespachoConfig
from .sync_sudespacho_legacy import (
    SudespachoLegacyClient,
    SudespachoLegacyError,
)
from .sudespacho_create import (
    GRUPOS_DEFAULT,
    USUARIOS_DEFAULT,
    _parse_values,
)
from .utils import normalize_es_phone

_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# ID del cliente EV MMC SPAIN, S.L.U. en clientes_propios (confirmado 2026-04-29)
EV_MMC_SPAIN_ID = "2"

_CC_NUM = "HubspotCollectedFormsWorkaround"

# REST API — vinculación de relaciones (confirmado 2026-05-06, tenant tnm)
# POST /api/relation_element/{element}/{exp_id}
# Auth: Authorization: Bearer <JWT>  (mismo token que create_expediente)
# Body: array JSON de strings "{dirección}.{slug}.{id}"
# Response: 201 "Created!" — idempotente (relaciones existentes no se duplican)
_REST_BASE = "https://api-crm-commons-pro.sudespacho.biz"
_REST_RELATION_PATH = "/api/relation_element/{element}/{exp_id}"
#: LECTURA de relaciones. NO es `relation_element` —esa ruta responde 405
#: `Allow: POST, PUT, DELETE`, medido el 2026-09-04— sino ésta. Ver `get_relaciones`.
_REST_RELATED_REGISTER_PATH = "/api/related_register/{element}/{exp_id}"
_REST_CREATE_COLABORADOR = "/api/element_register/colaboradores"
_REST_CREATE_CLIENTE_CONTRARIO = "/api/element_register/clientes_contrarios"
_REST_TIMEOUT = 30

# Rutas de los endpoints (sin el host)
_AUTOCOMPLETE_PATH = "/autocompletar/buscar/elemento/{element}"

_LINK_CLIENTE_PATH = (
    "/clientespropios/saveselect/elemento/clientes_propios"
    "/elemento_relacionado/extrajudiciales"
    "/miembro_relacionado/{exp_id}"
    "/direccion_relacionado/der"
)

_LINK_COLABORADOR_PATH = (
    "/views/saveselect/elemento/colaboradores"
    "/elemento_relacionado/extrajudiciales"
    "/miembro_relacionado/{exp_id}"
    "/direccion_relacionado/der"
)

_SAVEADD_COLABORADOR_PATH = "/views/saveadd/elemento/colaboradores"

# ---------------------------------------------------------------------------
# Rutas para expedientes JUDICIALES (confirmadas 2026-04-30 desde miembro/648)
# ---------------------------------------------------------------------------

_LINK_CLIENTE_JUDICIAL_PATH = (
    "/clientespropios/saveselect/elemento/clientes_propios"
    "/elemento_relacionado/expedientes_judiciales"
    "/miembro_relacionado/{exp_id}"
    "/direccion_relacionado/der"
)

_LINK_CONTRARIO_JUDICIAL_PATH = (
    "/clientescontrarios/saveselect/elemento/clientes_contrarios"
    "/elemento_relacionado/expedientes_judiciales"
    "/miembro_relacionado/{exp_id}"
    "/direccion_relacionado/der"
)

_LINK_PROCURADOR_JUDICIAL_PATH = (
    "/views/saveselect/elemento/procuradores_propios"
    "/elemento_relacionado/expedientes_judiciales"
    "/miembro_relacionado/{exp_id}"
    "/direccion_relacionado/der"
)

_LINK_COLABORADOR_JUDICIAL_PATH = (
    "/views/saveselect/elemento/colaboradores"
    "/elemento_relacionado/expedientes_judiciales"
    "/miembro_relacionado/{exp_id}"
    "/direccion_relacionado/der"
)

# Endpoint de creación de tags en el grupo judicial (grupo 2)
# Capturado 2026-04-30 desde /tags/view/elemento/tags/miembro/2
_SAVEADD_TAG_JUDICIAL_PATH = (
    "/tagsinput/saveadd/elemento/tags_input"
    "/elemento_relacionado/tags"
    "/miembro_relacionado/2"
    "/direccion_relacionado/der"
)


# ---------------------------------------------------------------------------
# Excepciones
# ---------------------------------------------------------------------------

class SudespachoRelationsError(RuntimeError):
    pass


class IdentidadSinComprobar(SudespachoRelationsError):
    """No se pudo consultar si la parte ya existe, asi que no se crea ni se vincula.

    R1/H-01: antes un 500 de la consulta se leia como «no existe» y se creaba una ficha
    duplicada. La politica, decidida por Nikolai el 2026-09-04, es **fallar cerrado**:
    si no se pudo mirar, se para y se dice que no se pudo mirar.
    """


class ConflictoDeIdentidad(SudespachoRelationsError):
    """El NIF y el email de una parte apuntan a fichas DISTINTAS del CRM.

    **Levanta a proposito, en vez de elegir una.** Decision de Nikolai del 2026-09-04:
    ante el conflicto la corrida para y pregunta. Fusionar dos personas en una ficha —o
    crear una tercera— es un dano en el CRM del cliente que nadie deshace despues, y un
    aviso impreso no detiene una escritura que ya se hizo.
    """


# ---------------------------------------------------------------------------
# DTO de colaborador
# ---------------------------------------------------------------------------

@dataclass
class NuevoColaborador:
    """Datos mínimos para crear un colaborador en sudespacho.

    El campo `nombre` es obligatorio y debe contener el nombre completo
    (el CRM no tiene campo separado para apellidos).
    El `email` es el identificador funcional para búsquedas de deduplicación.
    """
    nombre: str                          # campo_1086 — Nombre completo
    email: str = ""                      # campo_1080 — Email (clave de búsqueda)
    movil: str = ""                      # campo_1083 — Móvil
    telefono: str = ""                   # campo_1090 — Teléfono 1
    nif: str = ""                        # campo_1085 — NIF/CIF

    # Permisos (igual que en create_expediente)
    grupos: list[int] = field(default_factory=lambda: list(GRUPOS_DEFAULT))
    usuarios: list[int] = field(default_factory=lambda: list(USUARIOS_DEFAULT))

    def __post_init__(self) -> None:
        self.movil = normalize_es_phone(self.movil)
        self.telefono = normalize_es_phone(self.telefono)


@dataclass
class NuevoClienteContrario:
    """Datos mínimos para crear un cliente contrario (persona física) en sudespacho.

    A diferencia de NuevoColaborador, aquí el apellido va SEPARADO en dos campos
    (`1apellido`/`2apellido`) — confirmado 2026-07-17 vía el catálogo de propiedades
    reales de `clientes_contrarios` (ver docs/INTEGRACION_SUDESPACHO.md §10.6).
    """
    nombre: str                          # nombre(s)
    apellido1: str = ""                  # 1apellido
    apellido2: str = ""                  # 2apellido
    email: str = ""                      # clave de búsqueda alternativa al NIF
    movil: str = ""
    nif: str = ""                        # nif_cif
    direccion: str = ""
    poblacion: str = ""
    #: Los tres siguientes faltaban, asi que el CRM nunca los recibia: el `_ficha_crm.yaml`
    #: de W-02Q38C traia `cp` y `provincia` escritos y se descartaban en silencio al
    #: cargarlo, porque este DTO no tenia donde ponerlos. Y `telefono1` existe en el
    #: elemento `clientes_contrarios` del CRM pero no habia campo que lo alimentara.
    cp: str = ""                         # cp
    provincia: str = ""                  # Select: valor LITERAL del enum
    telefono: str = ""                   # telefono1

    def __post_init__(self) -> None:
        self.movil = normalize_es_phone(self.movil)
        self.telefono = normalize_es_phone(self.telefono)


# ---------------------------------------------------------------------------
# Búsquedas (autocomplete)
# ---------------------------------------------------------------------------

def _autocomplete(
    element: str,
    term: str,
    client: SudespachoLegacyClient,
) -> list[dict[str, Any]]:
    """Llama al endpoint de autocompletado y devuelve la lista de resultados.

    Args:
        element: Slug del elemento CRM (ej. "extrajudiciales", "colaboradores").
        term: Término de búsqueda.
        client: Cliente legacy autenticado.

    Returns:
        Lista de dicts con keys `id`, `label`, `value`, `data`.
        Lista vacía si no hay coincidencias.
    """
    path = _AUTOCOMPLETE_PATH.format(element=element)
    url = f"{path}?term={urllib.parse.quote(term)}&"
    try:
        r = client._client.get(url)
    except Exception as exc:
        raise SudespachoRelationsError(
            f"GET {url} falló: {exc}"
        ) from exc
    client._check_session(r, url)
    if r.status_code >= 400:
        raise SudespachoRelationsError(
            f"GET {url} → HTTP {r.status_code}"
        )
    try:
        return r.json()
    except Exception:
        return []


def normalize_referencia(s: str) -> str:
    """Normaliza una referencia de expediente para comparación tolerante.

    Colapsa espacios, quita acentos, lowercase. Útil para detectar duplicados
    cuando la referencia en el CRM difiere tipográficamente del case_id local
    (ej. doble espacio, mayúsculas, acentos).
    """
    if not s:
        return ""
    s = s.strip()
    s = re.sub(r"\s+", " ", s)
    nfkd = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    return s.lower()


_W_CODE_RE = re.compile(r"\b(W-[A-Za-z0-9]{5,8})\b", re.IGNORECASE)


def _extract_w_code(case_id: str) -> str | None:
    """Extrae el código W-XXXXXX de un case_id, o None si no tiene."""
    m = _W_CODE_RE.search(case_id)
    return m.group(1) if m else None


def wcode_match(ref_a: str | None, ref_b: str | None) -> bool:
    """True si ambas referencias contienen el MISMO W-code (case-insensitive).

    Ancla la identidad del inmueble en el W-code, no en el nombre completo: es
    tolerante a divergencias de sufijo entre Drive y CRM (p. ej. la misma finca
    dada de alta como ``… - Bad debt`` en local y ``… - Vuelta - COMPRADOR`` en
    el CRM). Devuelve ``False`` si a alguna de las dos le falta el W-code.

    Pensada como guard previo a descargar un expediente: si los W-codes NO
    coinciden, el ID tecleado pertenece a otra finca (caso del 649 → W-030LFT
    cuando se esperaba W-02MA0R).
    """
    wa = _extract_w_code(ref_a or "")
    wb = _extract_w_code(ref_b or "")
    if not wa or not wb:
        return False
    return wa.upper() == wb.upper()


def _match_in_results(
    results: list[dict[str, Any]],
    referencia_cliente: str,
) -> str | None:
    """Devuelve el ID del primer resultado cuya label matchee normalizada."""
    target = normalize_referencia(referencia_cliente)
    for r in results:
        if normalize_referencia(r.get("label", "")) == target:
            return str(r["value"])
    return None


def _rest_search_expedientes(element: str, referencia: str) -> list[dict[str, str]]:
    """Busca expedientes por referencia vía REST (filtro ``like`` sobre el W-code).

    Generaliza la búsqueda REST a cualquier elemento con la referencia indexada
    en :data:`_REFERENCIA_PROP_BY_ELEMENT` (judicial usa ``referencia_cliente``
    lowercase; extrajudicial ``Referencia_Cliente`` CamelCase — confirmado
    2026-05-06). Consulta ``GET /api/element_registries/{element}`` con
    ``x-api-key`` (sin PHPSESSID), el mismo endpoint que
    :func:`fetch_referencia_cliente`.

    Sustituye al autocomplete legacy (``_autocomplete``) para expedientes, que
    devuelve body vacío contra el CRM real (DEAD_ENDS, "Frontal heredado",
    2026-06-12). El operador ``contains`` da 404; ``like`` funciona.

    Args:
        element: Slug canónico (``"expedientes_judiciales"`` |
            ``"extrajudiciales"``).
        referencia: ``case_id`` o ``referencia_crm`` local. Si contiene W-code
            se filtra por él; si no, por el texto completo (fallback).

    Returns:
        Lista de ``{"id", "label"}`` (``label`` = referencia del CRM), con
        TODOS los candidatos cuya referencia contiene el término. Nunca lanza:
        si el ``element`` es desconocido, falta la API key, el CRM no responde
        o no hay coincidencias, devuelve ``[]``.
    """
    prop = _REFERENCIA_PROP_BY_ELEMENT.get(element)
    if prop is None:
        return []
    term = _extract_w_code(referencia) or (referencia or "").strip()
    if not term:
        return []
    url = f"{_REST_BASE}/api/element_registries/{element}"
    params: list[tuple[str, str]] = [
        ("properties[0]",                                       prop),
        ("filterGroup[condition]",                              "AND"),
        ("filterGroup[filterGroups][0][condition]",             "AND"),
        ("filterGroup[filterGroups][0][filters][0][operator]",  "like"),
        ("filterGroup[filterGroups][0][filters][0][value]",     term),
        ("filterGroup[filterGroups][0][filters][0][property]",  prop),
        ("itemsPerPage",                                        "50"),
        ("return_totals",                                       "true"),
    ]
    out: list[dict[str, str]] = []
    for it in _rest_get_items(url, params):
        ref = None
        for v in it.get("values", []) or []:
            if v.get("property", {}).get("name", "") == prop:
                ref = v.get("value")
        out.append({"id": str(it.get("id", "")), "label": str(ref or "")})
    return out


# ---------------------------------------------------------------------------
# Búsqueda para el combobox F2 §18.6 (texto libre + nº/serie del despacho)
# ---------------------------------------------------------------------------
#
# A diferencia de _rest_search_expedientes (dedup: extrae W-code, match exacto),
# el combobox busca por TEXTO LITERAL en varias properties con OR-like, y por el
# número interno del despacho (num_expediente/serie). Confirmado contra tenant
# tnm el 2026-06-12: like sobre referencia_cliente y referencia_procurador
# funciona; num_asunto (autos) está vacío y contrario no tiene ruta REST inversa
# (ver docs/DEAD_ENDS.md).

# Properties sobre las que el combobox hace OR-like (texto del usuario). Judicial
# añade referencia_procurador (lo que el procurador cita en su correo, p. ej.
# "P-2025/3447"); extrajudicial no tiene procurador.
_SEARCH_PROPS_BY_ELEMENT: dict[str, tuple[str, ...]] = {
    "expedientes_judiciales": ("referencia_cliente", "referencia_procurador"),
    "extrajudiciales":        ("Referencia_Cliente",),
}


def _rest_get_items(url: str, params: list[tuple[str, str]]) -> list[dict[str, Any]]:
    """GET REST element_registries → lista de items.

    Nunca lanza: devuelve ``[]`` ante api-key ausente, red caída, status != 200
    o JSON inválido. Centraliza el bloque HTTP+parseo de las búsquedas REST.
    """
    api_key = (os.getenv("SUDESPACHO_API_KEY") or "").strip()
    if not api_key:
        return []
    headers = {"x-api-key": api_key, "Accept": "application/json"}
    try:
        r = httpx.get(url, params=params, headers=headers, timeout=_REST_TIMEOUT)
    except Exception:  # noqa: BLE001 — red caída no debe romper el caller
        return []
    if r.status_code != 200:
        return []
    try:
        data = r.json()
    except Exception:  # noqa: BLE001
        return []
    return data.get("items") or data.get("hydra:member") or []


def _values_dict(item: dict) -> dict[str, Any]:
    """Aplana ``item["values"]`` a ``{property_name: value}``."""
    return {
        (v.get("property") or {}).get("name", ""): v.get("value")
        for v in item.get("values", []) or []
    }


def _label_expediente(vals: dict[str, Any]) -> str:
    """Etiqueta para la UI: nombre del caso, con la ref del procurador si la hay."""
    ref = str(vals.get("referencia_cliente") or vals.get("Referencia_Cliente") or "")
    proc = str(vals.get("referencia_procurador") or "")
    if ref and proc:
        return f"{ref}  ·  {proc}"
    return ref or proc


def _rest_search_por_texto(element: str, term: str, *, limit: int = 50) -> list[dict[str, str]]:
    """Busca expedientes por TEXTO LIBRE (literal) vía REST OR-like.

    Filtra ``like`` sobre el término literal en TODAS las properties buscables
    del elemento (``_SEARCH_PROPS_BY_ELEMENT``), combinadas con OR. Para el
    combobox de reasignación F2 §18.6.

    Returns:
        Lista ``[{"id","label"}]``. Nunca lanza: ``[]`` ante elemento
        desconocido / api-key ausente / término vacío / CRM no accesible.
    """
    elem = _normalize_element(element)
    props = _SEARCH_PROPS_BY_ELEMENT.get(elem) if elem else None
    if not props:
        return []
    term = (term or "").strip()
    if not term:
        return []

    url = f"{_REST_BASE}/api/element_registries/{elem}"
    params: list[tuple[str, str]] = [
        (f"properties[{i}]", p) for i, p in enumerate(props)
    ]
    params += [
        ("filterGroup[condition]", "AND"),
        ("filterGroup[filterGroups][0][condition]", "OR"),
    ]
    for i, p in enumerate(props):
        params += [
            (f"filterGroup[filterGroups][0][filters][{i}][operator]", "like"),
            (f"filterGroup[filterGroups][0][filters][{i}][value]", term),
            (f"filterGroup[filterGroups][0][filters][{i}][property]", p),
        ]
    params += [("itemsPerPage", str(limit)), ("return_totals", "true")]

    return [
        {"id": str(it.get("id", "")), "label": _label_expediente(_values_dict(it))}
        for it in _rest_get_items(url, params)
    ]


def _norm_serie_local(s: Any) -> str:
    """Normaliza una serie para comparar: sin espacios, minúscula.

    El CRM guarda el sufijo de subserie de forma inconsistente ('2023-n',
    '2022 - p'); el usuario teclea el año a secas. (Misma semántica que
    ``procurador_intake._norm_serie``, reimplementada aquí para evitar el ciclo
    de import procurador_intake ↔ sudespacho_relations.)
    """
    return re.sub(r"\s+", "", str(s)).lower()


def _rest_search_num_serie(num: str, serie: str, *, limit: int = 50) -> list[dict[str, str]]:
    """Busca expedientes JUDICIALES por nº interno del despacho (num/serie).

    El ``num_expediente`` se repite por serie (uno por año), así que se filtra
    ``equal num_expediente`` en servidor y se casa la serie en cliente
    (normalizada, por prefijo: el CRM guarda '2023-n', el usuario teclea '2023').
    Para el combobox F2.

    Returns:
        Lista ``[{"id","label"}]``. Nunca lanza ([] ante api-key ausente / CRM
        no accesible).
    """
    num = str(num).strip()
    if not num:
        return []
    url = f"{_REST_BASE}/api/element_registries/expedientes_judiciales"
    params: list[tuple[str, str]] = [
        ("properties[0]", "referencia_cliente"),
        ("properties[1]", "referencia_procurador"),
        ("properties[2]", "num_expediente"),
        ("properties[3]", "serie_expediente"),
        ("filterGroup[condition]", "AND"),
        ("filterGroup[filterGroups][0][condition]", "AND"),
        ("filterGroup[filterGroups][0][filters][0][operator]", "equal"),
        ("filterGroup[filterGroups][0][filters][0][value]", num),
        ("filterGroup[filterGroups][0][filters][0][property]", "num_expediente"),
        ("itemsPerPage", str(limit)),
        ("return_totals", "true"),
    ]
    target = _norm_serie_local(serie)
    out: list[dict[str, str]] = []
    for it in _rest_get_items(url, params):
        vals = _values_dict(it)
        crm_serie = _norm_serie_local(vals.get("serie_expediente", ""))
        if target and not crm_serie.startswith(target):
            continue
        out.append({"id": str(it.get("id", "")), "label": _label_expediente(vals)})
    return out


def _find_expediente_rest(element: str, referencia_cliente: str) -> str | None:
    """Devuelve el ID del expediente cuya referencia coincide EXACTAMENTE.

    Busca por REST (W-code, ``like``) y, entre los candidatos, devuelve el
    primero cuya referencia coincide con ``referencia_cliente`` tras
    normalización tolerante (espacios/acentos/case). ``None`` si ninguno
    coincide o el CRM no es accesible.
    """
    candidatos = _rest_search_expedientes(element, referencia_cliente)
    results = [{"label": c["label"], "value": c["id"]} for c in candidatos]
    return _match_in_results(results, referencia_cliente)


def find_expediente_by_referencia(
    referencia_cliente: str,
    *,
    client: SudespachoLegacyClient | None = None,
) -> str | None:
    """Busca un expediente extrajudicial por su referencia_cliente (case_id).

    Útil para detectar duplicados antes de crear un nuevo expediente.

    Desde 2026-06-12 usa REST (``element_registries/extrajudiciales`` con
    filtro ``like`` sobre el W-code, property ``Referencia_Cliente``), NO el
    autocomplete legacy, que devuelve body vacío contra el CRM real
    (DEAD_ENDS, "Frontal heredado"). Filtra por el W-code en servidor y, entre
    los candidatos, devuelve el que coincide EXACTAMENTE con la referencia tras
    normalización (espacios/acentos/case).

    Args:
        referencia_cliente: El case_id de FeesDefender (ej. "MaRS2 - ...").
            Coincide con campo_1740 del formulario / ``Referencia_Cliente``
            en el CRM.
        client: Ignorado — la búsqueda es REST. Se conserva por compatibilidad
            con llamadas existentes.

    Returns:
        ID del expediente si existe, None si no hay coincidencia o el CRM no
        es accesible. Nunca lanza.

    Example::

        exp_id = find_expediente_by_referencia("MaRS2 - Puerto Rico 2, ...")
        if exp_id:
            print(f"Ya existe: expediente #{exp_id}")
    """
    return _find_expediente_rest("extrajudiciales", referencia_cliente)


def find_expediente_judicial_by_referencia(
    referencia_cliente: str,
    *,
    client: SudespachoLegacyClient | None = None,
) -> str | None:
    """Busca un expediente judicial por su referencia_cliente (case_id).

    Útil para detectar duplicados antes de crear un nuevo expediente judicial.

    Desde 2026-06-12 usa REST (``element_registries/expedientes_judiciales``
    con filtro ``like`` sobre el W-code, property ``referencia_cliente``), NO
    el autocomplete legacy (DEAD_ENDS, "Frontal heredado"). Mismo mecanismo
    que :func:`list_expedientes_judiciales_candidatos`, pero devolviendo solo
    el candidato cuya referencia coincide EXACTAMENTE tras normalización
    (no la lista completa de candidatos del W-code).

    Args:
        referencia_cliente: El case_id de FeesDefender (ej. "MaRS2 - ...").
            Coincide con campo_867 del formulario judicial /
            ``referencia_cliente`` en el CRM.
        client: Ignorado — la búsqueda es REST. Se conserva por compatibilidad.

    Returns:
        ID del expediente si existe, None si no hay coincidencia o el CRM no
        es accesible. Nunca lanza.

    Example::

        exp_id = find_expediente_judicial_by_referencia("MaRS2 - Puerto Rico 2, ...")
        if exp_id:
            print(f"Ya existe expediente judicial #{exp_id}")
    """
    return _find_expediente_rest("expedientes_judiciales", referencia_cliente)


def list_expedientes_judiciales_candidatos(referencia: str) -> list[dict[str, str]]:
    """Lista expedientes JUDICIALES candidatos por el W-code de ``referencia``.

    A diferencia de :func:`find_expediente_judicial_by_referencia` —que exige
    coincidencia EXACTA de la referencia completa— aquí se devuelven TODOS los
    candidatos cuya referencia contiene el W-code, para que el letrado confirme
    cuál bajar. Resuelve el caso real de una finca con varios expedientes, o
    con el sufijo de la referencia distinto entre Drive (``… - Bad debt``) y
    CRM (``… - Vuelta - COMPRADOR``).

    Comparte el mecanismo REST (:func:`_rest_search_expedientes`,
    ``element_registries`` + filtro ``like``, x-api-key) con las funciones de
    dedup; aquí no se filtra por match exacto.

    Args:
        referencia: ``case_id`` o ``referencia_crm`` local. Si contiene W-code,
            se busca por él; si no, por el texto completo (fallback).

    Returns:
        Lista de ``{"id": str, "label": str}`` (posiblemente vacía). Nunca
        lanza: si falta la API key, el CRM no responde o no hay coincidencias,
        devuelve ``[]``.
    """
    return _rest_search_expedientes("expedientes_judiciales", referencia)


# ---------------------------------------------------------------------------
# Creación de colaborador — REST (sin PHPSESSID, confirmado 2026-05-06)
# ---------------------------------------------------------------------------

def _rest_post_colaborador(datos: "NuevoColaborador") -> str:
    """POST /api/element_register/colaboradores con x-api-key.

    Confirmado 2026-05-06 (HAR judicial_648.har, tenant tnm):
      - Auth: x-api-key (clave estática, no caduca) — migrado desde Bearer JWT el 2026-05-06
      - Body: {"nombre": "...", "email": "...", ...}
      - Response 201: {"id": N, "message": "Created!"}

    Args:
        datos: Datos del colaborador a crear.

    Returns:
        ID numérico del colaborador creado (str).

    Raises:
        SudespachoRelationsError: HTTP != 201 o error de red.
        ValueError: SUDESPACHO_API_KEY no configurado.
    """
    api_key = (os.getenv("SUDESPACHO_API_KEY") or "").strip()
    if not api_key:
        raise ValueError(
            "SUDESPACHO_API_KEY vacío en .env — ve a tnm.sudespacho.net → Ajustes → API"
        )

    payload: dict[str, str] = {"nombre": datos.nombre}
    if datos.email:
        payload["email"] = datos.email
    if datos.movil:
        payload["movil"] = datos.movil
    if datos.telefono:
        payload["telefono1"] = datos.telefono
    if datos.nif:
        payload["nif_cif"] = datos.nif

    url = f"{_REST_BASE}{_REST_CREATE_COLABORADOR}"
    headers = {
        "x-api-key":    api_key,
        "Content-Type": "application/json",
        "Accept":       "application/json",
    }

    try:
        r = httpx.post(url, json=payload, headers=headers, timeout=_REST_TIMEOUT)
    except httpx.HTTPError as exc:
        raise SudespachoRelationsError(
            f"REST POST {_REST_CREATE_COLABORADOR} falló: {exc}"
        ) from exc

    if r.status_code == 201:
        try:
            data = r.json()
            colab_id = str(data.get("id", ""))
            if colab_id and colab_id.isdigit():
                return colab_id
        except Exception:
            pass
        raise SudespachoRelationsError(
            f"REST POST {_REST_CREATE_COLABORADOR} devolvió 201 pero sin ID. "
            f"Body: {r.text[:300]}"
        )

    try:
        err = r.json()
        detail = err.get("detail") or err.get("hydra:description") or r.text[:300]
    except Exception:
        detail = r.text[:300]
    raise SudespachoRelationsError(
        f"REST POST {_REST_CREATE_COLABORADOR} → HTTP {r.status_code}: {detail}"
    )


#: Las properties de `colaboradores` que este modulo lee y escribe. El contrato lo
#: enumero el propio CRM el 2026-09-04 con una property inventada (§14.6): ccc, cp,
#: direccion, email, fax, iva, movil, nacionalidad, nif_cif, nombre, notas, poblacion,
#: provincia, telefono1, telefono2, telefono3, tipo, web. Aqui van solo las que el
#: despacho usa: pedirlas todas gastaria ancho sin ganar nada, y `nacionalidad` esta
#: marcada como cuarentena-PII en el atlas.
#:
#: NO hay property de CARGO. `tipo` es un Select con enum cerrado (Sin Asignar /
#: Colaborador / Perito / Tercero), asi que un puesto ahi corrompe la taxonomia; por
#: eso el cargo se extrae al informe y no se escribe (decision de Nikolai, 2026-09-04).
_PROPS_COLABORADOR: tuple[str, ...] = (
    "nombre", "email", "movil", "telefono1", "telefono2", "telefono3",
    "nif_cif", "direccion", "poblacion", "cp", "provincia", "id",
)


def get_colaborador(colab_id: str) -> dict[str, str]:
    """Ficha de un colaborador, aplanada a `{property: value}`.

    El GET plano da HTTP 500: `?properties=` es obligatorio (`[APER-26]`). Se pide el
    conjunto de _PROPS_COLABORADOR para tener visibilidad en round-trip GET -> merge
    -> PUT. El PUT es PARCIAL (verificado en vivo 2026-07-18 sobre extrajudiciales,
    INTEGRACION §10.7): preserva los campos omitidos.
    """
    api_key = (os.getenv("SUDESPACHO_API_KEY") or "").strip()
    if not api_key:
        raise ValueError("SUDESPACHO_API_KEY no configurada")

    url = (f"{_REST_BASE}{_REST_CREATE_COLABORADOR}/{colab_id}"
           f"?properties={','.join(_PROPS_COLABORADOR)}")
    r = httpx.get(url, headers={"x-api-key": api_key, "Accept": "application/json"},
                  timeout=_REST_TIMEOUT)
    if r.status_code != 200:
        raise SudespachoRelationsError(
            f"REST GET colaboradores/{colab_id} -> HTTP {r.status_code}")
    return _parse_values(r.json())


def update_colaborador(colab_id: str, cambios: dict) -> dict:
    """PUT sobre la ficha de un colaborador. Devuelve el registro tal como responde.

    PUT y no PATCH (PATCH da 405, §10.7). El llamador decide QUE va en `cambios`;
    esta funcion no filtra ni completa.
    """
    if not cambios:
        raise ValueError("update_colaborador: 'cambios' no puede estar vacío")

    api_key = (os.getenv("SUDESPACHO_API_KEY") or "").strip()
    if not api_key:
        raise ValueError("SUDESPACHO_API_KEY no configurada")

    url = f"{_REST_BASE}{_REST_CREATE_COLABORADOR}/{colab_id}"
    headers = {"x-api-key": api_key, "Content-Type": "application/json",
               "Accept": "application/json"}
    try:
        r = httpx.put(url, json=cambios, headers=headers, timeout=_REST_TIMEOUT)
    except httpx.HTTPError as exc:
        raise SudespachoRelationsError(
            f"REST PUT colaboradores/{colab_id} falló: {exc}") from exc

    if r.status_code == 200:
        try:
            return _parse_values(r.json())
        except Exception:  # noqa: BLE001 — cuerpo 200 no parseable
            return dict(cambios)

    try:
        detail = r.json().get("detail") or r.text[:300]
    except Exception:  # noqa: BLE001
        detail = r.text[:300]
    raise SudespachoRelationsError(
        f"REST PUT colaboradores/{colab_id} → HTTP {r.status_code}: {detail}")


# ---------------------------------------------------------------------------
# Creación de cliente contrario — REST (confirmado 2026-07-17, expediente 624)
# ---------------------------------------------------------------------------

def _rest_post_cliente_contrario(datos: "NuevoClienteContrario") -> str:
    """POST /api/element_register/clientes_contrarios con x-api-key.

    Mismo patrón que _rest_post_colaborador() — verificado en vivo 2026-07-17
    (expediente extrajudicial 624/W-02TH0W, contrario creado con id 1099).

    Args:
        datos: Datos del cliente contrario a crear.

    Returns:
        ID numérico del contrario creado (str).

    Raises:
        SudespachoRelationsError: HTTP != 201 o error de red.
        ValueError: SUDESPACHO_API_KEY no configurado.
    """
    api_key = (os.getenv("SUDESPACHO_API_KEY") or "").strip()
    if not api_key:
        raise ValueError(
            "SUDESPACHO_API_KEY vacío en .env — ve a tnm.sudespacho.net → Ajustes → API"
        )

    payload: dict[str, str] = {"nombre": datos.nombre}
    if datos.apellido1:
        payload["1apellido"] = datos.apellido1
    if datos.apellido2:
        payload["2apellido"] = datos.apellido2
    if datos.email:
        payload["email"] = datos.email
    if datos.movil:
        payload["movil"] = datos.movil
    if datos.nif:
        payload["nif_cif"] = datos.nif
    if datos.direccion:
        payload["direccion"] = datos.direccion
    if datos.poblacion:
        payload["poblacion"] = datos.poblacion
    if datos.cp:
        payload["cp"] = datos.cp
    if datos.telefono:
        payload["telefono1"] = datos.telefono
    if datos.provincia:
        # `provincia` es un Select: o se manda el literal del enum, o no se manda. Una
        # cadena que no case la descarta el CRM sin decir nada, y el campo queda vacio
        # pareciendo que se escribio.
        canonica = provincia_canonica(datos.provincia)
        if canonica:
            payload["provincia"] = canonica
        else:
            _log.warning(
                "provincia %r no casa con ninguna del enum del CRM: se omite en vez de "
                "mandar un valor que el Select descartaria en silencio", datos.provincia)

    url = f"{_REST_BASE}{_REST_CREATE_CLIENTE_CONTRARIO}"
    headers = {
        "x-api-key":    api_key,
        "Content-Type": "application/json",
        "Accept":       "application/json",
    }

    try:
        r = httpx.post(url, json=payload, headers=headers, timeout=_REST_TIMEOUT)
    except httpx.HTTPError as exc:
        raise SudespachoRelationsError(
            f"REST POST {_REST_CREATE_CLIENTE_CONTRARIO} falló: {exc}"
        ) from exc

    if r.status_code == 201:
        try:
            data = r.json()
            contrario_id = str(data.get("id", ""))
            if contrario_id and contrario_id.isdigit():
                return contrario_id
        except Exception:
            pass
        raise SudespachoRelationsError(
            f"REST POST {_REST_CREATE_CLIENTE_CONTRARIO} devolvió 201 pero sin ID. "
            f"Body: {r.text[:300]}"
        )

    try:
        err = r.json()
        detail = err.get("detail") or err.get("hydra:description") or r.text[:300]
    except Exception:
        detail = r.text[:300]
    raise SudespachoRelationsError(
        f"REST POST {_REST_CREATE_CLIENTE_CONTRARIO} → HTTP {r.status_code}: {detail}"
    )


def create_cliente_contrario(datos: "NuevoClienteContrario") -> str:
    """Crea un nuevo cliente contrario en sudespacho.net.

    A diferencia de create_colaborador(), NO hay fallback legacy: no existe
    endpoint saveadd confirmado para clientes_contrarios (solo REST, verificado
    en vivo 2026-07-17). Si REST falla, se propaga el error.

    Args:
        datos: Datos del contrario a crear.

    Returns:
        ID numérico del contrario creado (str).

    Raises:
        SudespachoRelationsError: si la creación falla.
        ValueError: SUDESPACHO_API_KEY no configurado.
    """
    return _rest_post_cliente_contrario(datos)


def update_cliente_contrario(contrario_id: str, cambios: dict) -> dict:
    """Actualiza campos de un cliente contrario existente vía PUT.

    A diferencia de `update_expediente()` (sudespacho_create.py, confirmado PUT
    PARCIAL en vivo 2026-07-18), no hay confirmación de si el PUT de
    `clientes_contrarios` es parcial o de reemplazo completo. Por prudencia el
    caller debe reenviar TODOS los campos que quiera conservar (nombre,
    1apellido, 2apellido, nif_cif, direccion, poblacion, email, movil...), no
    solo los que cambian — así el comportamiento es correcto sin importar cuál
    de los dos sea (confirmado en vivo 2026-07-22, expediente 674/W-02ZIIF).

    Args:
        contrario_id: ID del cliente contrario en el CRM (clientes_contrarios).
        cambios: Campos a escribir. No puede estar vacío.

    Returns:
        Dict aplanado {property: value} con el registro tal como responde el
        servidor (o `cambios` tal cual si la respuesta 200 no es JSON parseable).

    Raises:
        SudespachoRelationsError: si el PUT falla o el HTTP no es 200.
        ValueError: si `cambios` está vacío o SUDESPACHO_API_KEY no está configurado.
    """
    if not cambios:
        raise ValueError("update_cliente_contrario: 'cambios' no puede estar vacío")

    api_key = (os.getenv("SUDESPACHO_API_KEY") or "").strip()
    if not api_key:
        raise ValueError(
            "SUDESPACHO_API_KEY vacío en .env — ve a tnm.sudespacho.net → Ajustes → API"
        )

    url = f"{_REST_BASE}{_REST_CREATE_CLIENTE_CONTRARIO}/{contrario_id}"
    headers = {
        "x-api-key":    api_key,
        "Content-Type": "application/json",
        "Accept":       "application/json",
    }
    try:
        r = httpx.put(url, json=cambios, headers=headers, timeout=_REST_TIMEOUT)
    except httpx.HTTPError as exc:
        raise SudespachoRelationsError(
            f"REST PUT clientes_contrarios/{contrario_id} falló: {exc}"
        ) from exc

    if r.status_code == 200:
        try:
            return _parse_values(r.json())
        except Exception:
            return dict(cambios)

    try:
        detail = r.json().get("detail") or r.text[:300]
    except Exception:
        detail = r.text[:300]
    raise SudespachoRelationsError(
        f"REST PUT clientes_contrarios/{contrario_id} → HTTP {r.status_code}: {detail}"
    )


#: Propiedad que guarda el NIF, por elemento. El CRM no usa el mismo nombre en todos,
#: pero `colaboradores` SI usa el mismo que el contrario: se le preguntó al propio CRM
#: el 2026-09-04 con una property inventada y su 500 enumeró el contrato entero
#: (método del §14.6). Antes decía `nif` aquí, y como esa property NO EXISTE el CRM
#: devolvía 500 → `resolver_parte` marcaba el criterio `sin_comprobar` →
#: `_resolver_colaborador` abortaba el alta en cuanto la ficha traía un NIF. O sea: la
#: dedup por NIF del colaborador no ha funcionado nunca. El atlas ya lo decía bien;
#: era este dict el que lo contradecía.
_PROP_NIF = {
    "clientes_contrarios": "nif_cif",
    "clientes_propios": "nif_cif",
    "colaboradores": "nif_cif",
}


@dataclass(frozen=True)
class Consulta:
    """El resultado de preguntarle algo al CRM, **con si se pudo preguntar**.

    R1/H-01 y H-02: la version anterior devolvia una lista y colapsaba «no hay
    coincidencias» y «el CRM devolvio 500» en el mismo `[]`. Con eso, una caida de red
    durante una apertura hacia concluir «esta parte no existe» y se creaba una ficha
    duplicada, o «no hay expediente con este W-code» y se daba de alta otro. La
    proteccion desaparecia **en silencio y justo cuando fallaba algo**.
    """

    registros: list[dict] = field(default_factory=list)
    #: False cuando la consulta no se pudo completar. NO es «no hay resultados».
    ok: bool = True
    motivo: str = ""

    @property
    def ids(self) -> list[str]:
        return [i for i in (str(r.get("id") or "").strip() for r in self.registros) if i]


def _canonizar_documento(valor: str) -> str:
    """NIF/NIE/CIF sin separadores. Medido contra el tenant el 2026-09-04.

    Medido contra el tenant con una ficha real (cuyo documento NO se transcribe aqui):
    el CRM **si** normaliza caja y espacios envolventes —`nnnnnnnnx` y `" nnnnnnnnX "`
    encuentran la ficha— pero **no** los separadores: `nn.nnn.nnn-X` no encuentra nada.
    Se canoniza aqui igualmente para no depender de que el backend siga haciendolo.
    """
    return "".join(c for c in (valor or "") if c.isalnum()).upper()


def _buscar_registros(
    elemento: str,
    propiedad: str,
    valor: str,
    *,
    operador: str = "equal",
    limite: int = 5,
    properties: tuple[str, ...] = (),
) -> Consulta:
    """Busca registros de `elemento` filtrando por una propiedad. **Nunca lanza.**

    Generalizacion del filtro que ya usaba `find_cliente_contrario_by_nif`: mismo
    endpoint `element_registries` y misma gramatica `filterGroup`, pero con el elemento
    y la propiedad como parametros, que es lo que permite deduplicar por NIF **y** por
    email sin escribir la peticion cuatro veces.

    Operadores validos (los enumera el propio CRM en el 404 cuando se le da uno malo):
    equal, not-equal, not-associated, associated, like, not-like,
    greater-than-or-equal, less-than-or-equal, is-empty, is-not-empty, in, not-in,
    between, group-by. **`contains` NO existe** — es `like`.

    «Nunca lanza» aqui es un contrato, no una aspiracion: R1/H-07 midio que la version
    anterior **si** lanzaba `AttributeError` ante un `200` con un JSON de forma
    inesperada (una lista en vez de un objeto), porque el `try` solo envolvia
    `r.json()`. Ahora el parseo entero esta cubierto y una forma rara sale como
    `ok=False`, que es lo que un llamador puede tratar.

    Returns:
        Una `Consulta`. **Mira siempre `ok` antes que `registros`**: una lista vacia con
        `ok=False` significa «no pude mirar», y tratarla como ausencia es el defecto que
        este contrato existe para impedir.
    """
    valor = (valor or "").strip()
    if not valor:
        return Consulta()
    api_key = (os.getenv("SUDESPACHO_API_KEY") or "").strip()
    if not api_key:
        return Consulta(ok=False, motivo="SUDESPACHO_API_KEY no configurada")

    url = f"{_REST_BASE}/api/element_registries/{elemento}"
    params: list[tuple[str, str]] = [("properties[0]", propiedad)]
    for i, extra in enumerate(properties, start=1):
        params.append((f"properties[{i}]", extra))
    params += [
        ("filterGroup[condition]", "AND"),
        ("filterGroup[filterGroups][0][condition]", "AND"),
        ("filterGroup[filterGroups][0][filters][0][operator]", operador),
        ("filterGroup[filterGroups][0][filters][0][value]", valor),
        ("filterGroup[filterGroups][0][filters][0][property]", propiedad),
        ("itemsPerPage", str(limite)),
    ]
    headers = {"x-api-key": api_key, "Accept": "application/json"}
    try:
        r = httpx.get(url, params=params, headers=headers, timeout=_REST_TIMEOUT)
    except Exception as exc:  # noqa: BLE001 — red caida no debe romper al llamador
        return Consulta(ok=False, motivo=f"red: {exc!r}")
    if r.status_code != 200:
        return Consulta(ok=False, motivo=f"HTTP {r.status_code}")
    try:
        data = r.json()
        items = data.get("items") or data.get("hydra:member") or []
        return Consulta(registros=[i for i in items if isinstance(i, dict)])
    except Exception as exc:  # noqa: BLE001 — cuerpo con forma inesperada
        return Consulta(ok=False, motivo=f"cuerpo inesperado: {exc!r}")


@dataclass(frozen=True)
class ResolucionParte:
    """A que ficha del CRM corresponde una parte, y con cuanta certeza.

    Tres estados que **no se pueden colapsar** sin abrir un agujero:

    - `id` con valor: resuelta.
    - todo vacio: la parte no existe, y se puede crear con tranquilidad.
    - `conflicto`, `ambiguo` o `sin_comprobar`: **no se sabe**, y hay que parar.
    """

    id: str | None = None
    #: "nif" | "email" | None
    por: str | None = None
    #: (ids_por_nif, ids_por_email) cuando son disjuntos.
    conflicto: tuple[str, str] | None = None
    #: Un criterio devolvio VARIAS fichas: elegir una seria elegir por orden de llegada.
    ambiguo: tuple[str, ...] = ()
    #: Criterios que no se pudieron consultar. Vacio NO implica que no existan.
    sin_comprobar: tuple[str, ...] = ()

    @property
    def resuelta(self) -> bool:
        """True solo si se sabe con certeza a que ficha corresponde (o que no hay)."""
        return not (self.conflicto or self.ambiguo or self.sin_comprobar)


def resolver_parte(elemento: str, *, nif: str = "", email: str = "") -> ResolucionParte:
    """Identifica la ficha de una parte por NIF **o** email. No escribe nada.

    Vale igual para expedientes judiciales y extrajudiciales: los elementos de parte
    (`clientes_contrarios`, `colaboradores`, `clientes_propios`) son **los mismos** en
    las dos jurisdicciones — solo cambia el expediente padre.

    **El NIF manda** cuando ambos criterios apuntan a lo mismo o solo uno resuelve.

    **Todo lo demas para la corrida**, y cada caso por su razon (R1/H-01, H-03):

    - **Conflicto**: los dos criterios dan conjuntos DISJUNTOS de fichas. Elegir uno
      fusiona dos personas o parte una en dos.
    - **Ambiguo**: un criterio devuelve VARIAS fichas. La version anterior cogia
      `items[0]`, con lo que la identidad —y hasta la deteccion del conflicto—
      dependian del orden en que el servidor devolviera las filas. Se midio: con
      `[111, 222]` habia conflicto y con `[222, 111]` no lo habia, para el mismo estado
      del CRM.
    - **Sin comprobar**: la consulta fallo. No es ausencia.

    La comparacion es por **conjuntos**, no por primer elemento: si se solapan, la
    interseccion decide; si la interseccion tiene mas de una ficha, sigue siendo ambiguo.
    """
    prop_nif = _PROP_NIF.get(elemento, "nif_cif")
    nif_canon = _canonizar_documento(nif)

    sin: list[str] = []
    ambiguo: list[str] = []

    c_nif = _buscar_registros(elemento, prop_nif, nif_canon) if nif_canon else Consulta()
    c_mail = _buscar_registros(elemento, "email", (email or "").strip()) if (email or "").strip() else Consulta()

    if nif_canon and not c_nif.ok:
        sin.append(f"NIF ({c_nif.motivo})")
    if (email or "").strip() and not c_mail.ok:
        sin.append(f"email ({c_mail.motivo})")

    ids_nif = set(c_nif.ids)
    ids_mail = set(c_mail.ids)
    if len(ids_nif) > 1:
        ambiguo.extend(sorted(ids_nif))
    if len(ids_mail) > 1:
        ambiguo.extend(sorted(ids_mail))

    if sin or ambiguo:
        return ResolucionParte(sin_comprobar=tuple(sin), ambiguo=tuple(dict.fromkeys(ambiguo)))

    if ids_nif and ids_mail:
        comun = ids_nif & ids_mail
        if not comun:
            return ResolucionParte(
                conflicto=(sorted(ids_nif)[0], sorted(ids_mail)[0]))
        if len(comun) > 1:
            return ResolucionParte(ambiguo=tuple(sorted(comun)))
        return ResolucionParte(id=comun.pop(), por="nif")
    if ids_nif:
        return ResolucionParte(id=ids_nif.pop(), por="nif")
    if ids_mail:
        return ResolucionParte(id=ids_mail.pop(), por="email")
    return ResolucionParte()


def _exigir_identidad_cierta(r: ResolucionParte, *, elemento: str, nif: str, email: str) -> None:
    """Levanta si la identidad no se sabe con certeza. La politica es fallar CERRADO.

    Decision de Nikolai (2026-09-04): si no se puede comprobar, no se crea ni se
    vincula. Un duplicado en el CRM del cliente cuesta mas de deshacer que repetir la
    operacion cuando el CRM vuelva.
    """
    if r.conflicto:
        por_nif, por_email = r.conflicto
        raise ConflictoDeIdentidad(
            f"En {elemento}, el NIF {nif!r} apunta a la ficha {por_nif} y el email "
            f"{email!r} a la {por_email}. No se vincula ninguna ni se crea otra: "
            "resuelvelo en el CRM (fusiona las fichas o corrige el dato) y repite."
        )
    if r.ambiguo:
        raise ConflictoDeIdentidad(
            f"En {elemento}, la busqueda devolvio VARIAS fichas ({', '.join(r.ambiguo)}) "
            "para la misma parte. Elegir una seria elegirla por el orden en que el CRM "
            "devuelve las filas. Deduplica en el CRM y repite."
        )
    if r.sin_comprobar:
        raise IdentidadSinComprobar(
            f"No se pudo comprobar si esta parte ya existe en {elemento}: "
            f"{'; '.join(r.sin_comprobar)}. No se crea ni se vincula nada."
        )


#: La referencia del expediente NO se llama igual en las dos jurisdicciones. Medido el
#: 2026-09-04: pedirle `Referencia_Cliente` al judicial devuelve HTTP 500 enumerando sus
#: properties reales. Unificar los dos nombres rompe la busqueda judicial en silencio.
_PROP_REFERENCIA = {
    "extrajudiciales": "Referencia_Cliente",
    "expedientes_judiciales": "referencia_cliente",
}


@dataclass
class DuplicadosExpediente:
    """Lo que se encontro al buscar un expediente ya existente, por criterio.

    Cada lista lleva pares `(elemento, exp_id)`. **`bloquea` solo lo levanta el W-code**:
    los otros dos criterios producen falsos positivos legitimos y por eso avisan.
    """

    por_wcode: list[tuple[str, str]] = field(default_factory=list)
    por_direccion: list[tuple[str, str]] = field(default_factory=list)
    por_contrario: list[tuple[str, str]] = field(default_factory=list)
    #: Criterios que no se pudieron comprobar. «No pude mirar» no es «no hay», y por
    #: eso `bloquea` NO se puede leer solo: hay que mirar tambien esta lista.
    sin_comprobar: list[str] = field(default_factory=list)

    @property
    def bloquea(self) -> bool:
        return bool(self.por_wcode)

    @property
    def incierto(self) -> bool:
        """Algo no se pudo consultar. La politica del proyecto es fallar CERRADO."""
        return bool(self.sin_comprobar)

    @property
    def avisos(self) -> list[str]:
        salida: list[str] = []
        for etiqueta, hallados in (("direccion", self.por_direccion),
                                   ("contrario", self.por_contrario)):
            for elemento, exp_id in hallados:
                salida.append(f"mismo {etiqueta}: {elemento} #{exp_id}")
        return salida


def buscar_expedientes_duplicados(
    *,
    w_code: str,
    direccion: str = "",
    contrario_id: str | None = None,
) -> DuplicadosExpediente:
    """Busca expedientes que ya puedan ser este, en las DOS jurisdicciones.

    Encargo de Nikolai (2026-09-04) tras medir que `_alta_crm` solo miraba el `_caso.md`
    **local**: si el registro local se pierde, el alta crea un expediente duplicado en el
    CRM del cliente.

    Los tres criterios **no valen lo mismo**, y esa asimetria es la decision, no un
    detalle: el **W-code bloquea** porque identifica la operacion de E&V; **direccion y
    contrario avisan** porque una vuelta y una bad debt del mismo inmueble son dos
    expedientes correctos, igual que el mismo propietario en dos operaciones. Un
    bloqueo que salta siempre se contesta con `--force` por rutina y deja de proteger.

    No escribe nada y **no lanza**. Lo que no se pueda consultar cae en `sin_comprobar`,
    y el llamador debe tratarlo como «no se sabe», no como «no hay»: R1/H-02 midio que
    la version anterior dejaba esa lista **vacia** ante un 500 y devolvia `bloquea=False`
    — el criterio que debia bloquear fallaba ABIERTO justo cuando no habia podido mirar.
    """
    res = DuplicadosExpediente()
    w_code = (w_code or "").strip()
    direccion = (direccion or "").strip()

    for elemento, prop in _PROP_REFERENCIA.items():
        if w_code:
            c = _buscar_registros(elemento, prop, w_code, operador="like", limite=25)
            if not c.ok:
                res.sin_comprobar.append(f"W-code en {elemento} ({c.motivo})")
            for reg in c.registros:
                rid = str(reg.get("id") or "").strip()
                if not rid:
                    continue
                # R1/H-06: `like` casa por subcadena, asi que buscar `W-12345` trae
                # tambien `W-123456`, que es OTRA operacion. Se confirma el codigo exacto
                # contra la referencia devuelta con `wcode_match` — que ya existia en
                # este modulo y no se estaba usando. Si la referencia no viene, no se
                # puede confirmar: cuenta como sin comprobar, nunca como duplicado.
                ref = _referencia_de(reg, prop)
                if ref is None:
                    res.sin_comprobar.append(
                        f"{elemento} #{rid}: el CRM no devolvio su referencia, "
                        "no se puede confirmar que el W-code sea el mismo")
                elif wcode_match(ref, w_code):
                    res.por_wcode.append((elemento, rid))

        if direccion:
            c = _buscar_registros(elemento, prop, direccion, operador="like", limite=25)
            if not c.ok:
                res.sin_comprobar.append(f"direccion en {elemento} ({c.motivo})")
            for reg in c.registros:
                rid = str(reg.get("id") or "").strip()
                # Un mismo expediente casa por W-code y por direccion: no se cuenta dos
                # veces, y sobre todo no se degrada un bloqueo a aviso.
                if rid and (elemento, rid) not in res.por_wcode:
                    res.por_direccion.append((elemento, rid))

    if contrario_id:
        try:
            rel = get_relaciones("clientes_contrarios", contrario_id)
        except Exception as exc:  # noqa: BLE001 — un aviso que no se puede calcular
            res.sin_comprobar.append(f"contrario #{contrario_id} ({exc!r})")
        else:
            for elemento in _PROP_REFERENCIA:
                for v in rel.get(elemento, []):
                    rid = str(v.get("id") or "").strip()
                    if rid and (elemento, rid) not in res.por_wcode:
                        res.por_contrario.append((elemento, rid))
    return res


def _referencia_de(registro: dict, propiedad: str) -> str | None:
    """La referencia del expediente dentro de un registro de `element_registries`.

    El CRM devuelve `{"id": ..., "values": [{"property": {"name": ...}, "value": ...}]}`.
    Devuelve `None` si no viene: **ausencia de dato, no cadena vacia**, porque el
    llamador tiene que poder distinguir «la referencia no casa» de «no me la han dado».
    """
    for v in registro.get("values") or []:
        if not isinstance(v, dict):
            continue
        prop = v.get("property")
        nombre = prop.get("name") if isinstance(prop, dict) else prop
        if nombre == propiedad:
            valor = v.get("value")
            return valor if isinstance(valor, str) else None
    return None


#: Valores LITERALES del Select `provincia` de `clientes_contrarios`, leidos del CRM el
#: 2026-09-04 (`GET /api/view/enums/clientes_contrarios/provincia`, 52 entradas). Un
#: Select no acepta cualquier cadena, y la convencion del despacho es escribir las fichas
#: en MAYUSCULAS: mandar `BARCELONA` donde el enum dice `Barcelona` **pierde el dato sin
#: avisar**. Por eso se traduce, en vez de confiar en como se tecleo.
_PROVINCIAS = (
    "A Coruña", "Álava", "Albacete", "Alicante", "Almería", "Asturias", "Ávila",
    "Badajoz", "Baleares (Illes)", "Barcelona", "Burgos", "Cáceres", "Cádiz",
    "Cantabria", "Castellón", "Ceuta", "Ciudad Real", "Córdoba", "Cuenca", "Girona",
    "Granada", "Guadalajara", "Guipúzcoa", "Huelva", "Huesca", "Jaén", "La Rioja",
    "Las Palmas", "León", "Lleida", "Lugo", "Madrid", "Málaga", "Melilla", "Murcia",
    "Navarra", "Ourense", "Palencia", "Pontevedra", "Salamanca",
    "Santa Cruz de Tenerife", "Segovia", "Sevilla", "Soria", "Tarragona", "Teruel",
    "Toledo", "Valencia", "Valladolid", "Vizcaya", "Zamora", "Zaragoza",
)


def _sin_tildes_min(s: str) -> str:
    base = unicodedata.normalize("NFD", (s or "").strip().lower())
    return "".join(c for c in base if unicodedata.category(c) != "Mn")


def provincia_canonica(valor: str) -> str | None:
    """El literal del enum que corresponde a `valor`, o `None` si no hay ninguno.

    Tolera caja y tildes —`BARCELONA`, `barcelona` y `Barcelona` son la misma— porque es
    como se escribe de verdad en las fichas. Lo que **no** hace es inventar: si no casa
    con ninguna provincia devuelve `None`, y el llamador decide. Mandar al CRM una cadena
    que el Select no reconoce es perder el dato creyendo haberlo escrito.
    """
    aguja = _sin_tildes_min(valor)
    if not aguja:
        return None
    for prov in _PROVINCIAS:
        if _sin_tildes_min(prov) == aguja:
            return prov
    return None


def find_cliente_contrario_by_nif(nif: str) -> str | None:
    """Busca un cliente contrario en el CRM por NIF/CIF (búsqueda exacta).

    Usa REST (element_registries/clientes_contrarios) con filtro `equal` sobre
    `nif_cif` — no requiere PHPSESSID. Mismo mecanismo que _rest_search_expedientes.

    Args:
        nif: NIF/CIF del contrario.

    Returns:
        ID del contrario si existe, None si no hay NIF, no hay coincidencia,
        o el CRM no es accesible. Nunca lanza.
    """
    nif = (nif or "").strip()
    if not nif:
        return None
    api_key = (os.getenv("SUDESPACHO_API_KEY") or "").strip()
    if not api_key:
        return None

    url = f"{_REST_BASE}/api/element_registries/clientes_contrarios"
    params: list[tuple[str, str]] = [
        ("properties[0]", "nif_cif"),
        ("filterGroup[condition]", "AND"),
        ("filterGroup[filterGroups][0][condition]", "AND"),
        ("filterGroup[filterGroups][0][filters][0][operator]", "equal"),
        ("filterGroup[filterGroups][0][filters][0][value]", nif),
        ("filterGroup[filterGroups][0][filters][0][property]", "nif_cif"),
        ("itemsPerPage", "5"),
    ]
    headers = {"x-api-key": api_key, "Accept": "application/json"}
    try:
        r = httpx.get(url, params=params, headers=headers, timeout=_REST_TIMEOUT)
    except Exception:  # noqa: BLE001 — red caída no debe romper el caller
        return None
    if r.status_code != 200:
        return None
    try:
        data = r.json()
    except Exception:  # noqa: BLE001
        return None
    items = data.get("items") or data.get("hydra:member") or []
    if not items:
        return None
    return str(items[0].get("id", "")) or None


def link_contrario(exp_id: str, contrario_id: str) -> None:
    """Vincula un cliente contrario existente a un expediente EXTRAJUDICIAL.

    REST únicamente (confirmado en vivo 2026-07-17, expediente 624/W-02TH0W) —
    sin fallback legacy: no hay endpoint saveselect confirmado para esta
    combinación element+relación (a diferencia de clientes_propios/colaboradores
    en extrajudiciales, que sí tienen legacy). Ver docs/INTEGRACION_SUDESPACHO.md §10.6.

    Args:
        exp_id: ID del expediente extrajudicial.
        contrario_id: ID del cliente contrario en el CRM (clientes_contrarios).

    Raises:
        SudespachoRelationsError: si el vínculo falla.
        ValueError: SUDESPACHO_API_KEY no configurado.
    """
    _link_rest("extrajudiciales", exp_id, [f"right.clientes_contrarios.{contrario_id}"])


def ensure_contrario_vinculado(
    exp_id: str,
    datos: NuevoClienteContrario,
) -> tuple[str, bool]:
    """Garantiza que el contrario existe en el CRM y está vinculado al expediente.

    Mismo flujo que ensure_colaborador_vinculado() pero para clientes_contrarios
    en expedientes EXTRAJUDICIALES (confirmado en vivo 2026-07-17): busca por NIF,
    crea si no existe, vincula siempre.

    Args:
        exp_id: ID del expediente extrajudicial.
        datos: Datos del contrario (nombre + nif mínimos para deduplicar).

    Returns:
        Tupla (contrario_id, created) donde `created` es True si se creó nuevo.

    Raises:
        SudespachoRelationsError: si algún paso falla.
    """
    contrario_id, created = _resolver_o_crear_contrario(datos)
    link_contrario(exp_id, contrario_id)
    return contrario_id, created


def _resolver_o_crear_contrario(datos: NuevoClienteContrario) -> tuple[str, bool]:
    """La parte de identidad, compartida por las dos jurisdicciones.

    Deduplica por **NIF o email** —antes solo por NIF, asi que un contrario sin NIF
    generaba ficha nueva en cada caso— y **levanta** si los dos criterios discrepan.
    """
    r = resolver_parte("clientes_contrarios", nif=datos.nif, email=datos.email)
    _exigir_identidad_cierta(r, elemento="clientes_contrarios",
                             nif=datos.nif, email=datos.email)
    if r.id:
        _completar_contrario_existente(r.id, datos)
        return r.id, False
    return create_cliente_contrario(datos), True


#: Campos de la ficha que se COMPLETAN sobre un contrario que ya existe, con su nombre
#: de property en el CRM. Solo se rellena lo que esta VACIO en el CRM: la ficha local
#: aporta datos, no manda sobre lo que ya hay — otra sesion o la propia E&V pueden haber
#: corregido algo ahi y pisarlo seria destruir trabajo ajeno.
_COMPLETABLES_CONTRARIO = (
    ("email", "email"),
    ("movil", "movil"),
    ("direccion", "direccion"),
    ("poblacion", "poblacion"),
    ("cp", "cp"),
    ("telefono", "telefono1"),
)


def _completar_contrario_existente(contrario_id: str, datos: NuevoClienteContrario) -> None:
    """Rellena en el CRM los campos que la ficha trae y la ficha del CRM no tiene.

    **R1/H-07, y desmiente una afirmacion previa mia.** Anadir `cp`, `provincia` y
    `telefono` al DTO solo los hacia llegar en el camino de CREACION. Con el contrario ya
    existente —el caso normal en cuanto un caso se reabre o la parte aparece en dos
    operaciones— `ensure_contrario_vinculado` solo vinculaba, nunca actualizaba, y los
    tres campos seguian sin llegar. Los tests no lo cazaron porque llamaban directamente
    al POST, saltandose esta rama.

    No lanza: completar la ficha es un extra sobre el vinculo, y perder el vinculo por no
    poder escribir un codigo postal seria peor que quedarse sin el codigo postal. Lo que
    no se pueda hacer se registra.
    """
    cambios: dict[str, str] = {}
    try:
        actual = get_cliente_contrario(contrario_id)
    except Exception as exc:  # noqa: BLE001
        _log.warning("no se pudo leer el contrario %s para completarlo (%r): los datos "
                     "de la ficha que faltasen siguen sin llegar", contrario_id, exc)
        return

    for campo, prop in _COMPLETABLES_CONTRARIO:
        valor = (getattr(datos, campo, "") or "").strip()
        if valor and not (actual.get(prop) or "").strip():
            cambios[prop] = valor

    provincia = provincia_canonica(datos.provincia) if datos.provincia else None
    if provincia and not (actual.get("provincia") or "").strip():
        cambios["provincia"] = provincia

    if not cambios:
        return
    try:
        update_cliente_contrario(contrario_id, cambios)
        _log.info("contrario %s completado con %s", contrario_id, sorted(cambios))
    except Exception as exc:  # noqa: BLE001
        _log.warning("no se pudieron completar los campos %s del contrario %s (%r)",
                     sorted(cambios), contrario_id, exc)


def get_cliente_contrario(contrario_id: str) -> dict:
    """Ficha completa de un contrario, aplanada a `{property: value}`.

    Las properties se piden **al propio CRM** en vez de mantener una lista aqui: un 500
    con una property inventada las enumera todas (metodo del §14.6 de
    `INTEGRACION_SUDESPACHO.md`), pero eso gasta una peticion de mas por corrida, asi que
    se piden las que este modulo sabe leer y escribir.
    """
    api_key = (os.getenv("SUDESPACHO_API_KEY") or "").strip()
    if not api_key:
        raise ValueError("SUDESPACHO_API_KEY no configurada")

    props = ",".join([
        "nombre", "1apellido", "2apellido", "email", "movil", "nif_cif",
        "direccion", "poblacion", "cp", "provincia", "telefono1", "id",
    ])
    url = (f"{_REST_BASE}{_REST_CREATE_CLIENTE_CONTRARIO}/{contrario_id}"
           f"?properties={props}")
    r = httpx.get(url, headers={"x-api-key": api_key, "Accept": "application/json"},
                  timeout=_REST_TIMEOUT)
    if r.status_code != 200:
        raise SudespachoRelationsError(
            f"REST GET clientes_contrarios/{contrario_id} -> HTTP {r.status_code}")
    plano: dict[str, str] = {}
    for item in (r.json().get("values") or []):
        if not isinstance(item, dict):
            continue
        prop = item.get("property")
        nombre = prop.get("name") if isinstance(prop, dict) else prop
        if nombre:
            plano[nombre] = item.get("value")
    return plano


def ensure_contrario_vinculado_judicial(
    exp_id: str,
    datos: NuevoClienteContrario,
    *,
    client: SudespachoLegacyClient | None = None,
) -> tuple[str, bool]:
    """Igual que :func:`ensure_contrario_vinculado`, para expedientes JUDICIALES.

    No existia: en judicial solo habia `link_contrario_judicial(exp_id, contrario_id)`,
    que recibe un id ya creado, asi que **no habia deduplicacion ninguna** — el runbook
    lo declaraba como hueco (`[APER-49]`). El elemento `clientes_contrarios` es el
    MISMO en las dos jurisdicciones, asi que la identidad se resuelve igual y lo unico
    que cambia es el expediente al que se vincula.
    """
    contrario_id, created = _resolver_o_crear_contrario(datos)
    link_contrario_judicial(exp_id, contrario_id, client=client)
    return contrario_id, created


# ---------------------------------------------------------------------------
# Creación de colaborador
# ---------------------------------------------------------------------------

def _create_colaborador_legacy(
    datos: NuevoColaborador,
    client: SudespachoLegacyClient,
) -> str:
    """Crea un colaborador vía frontal heredado (PHPSESSID + CSRF).

    Usado como fallback cuando REST no está disponible.

    Args:
        datos: Datos del colaborador.
        client: Cliente legacy ya inicializado.

    Returns:
        ID numérico del colaborador creado (str).

    Raises:
        SudespachoRelationsError: si la creación falla o no devuelve ID.
    """
    csrf = client.get_csrf_token()

    form: list[tuple[str, str]] = [
        ("campo_1086__colaboradores", datos.nombre),
        ("campo_1080__colaboradores", datos.email),
        ("campo_1083__colaboradores", datos.movil),
        ("campo_1090__colaboradores", datos.telefono),
        ("campo_1085__colaboradores", datos.nif),
        # Resto de campos opcionales — vacíos por defecto
        ("campo_1084__colaboradores", "1"),   # Nacionalidad = Sin Asignar
        ("campo_1091__colaboradores", ""),
        ("campo_1081__colaboradores", ""),
        ("campo_1092__colaboradores", ""),
        ("campo_1094__colaboradores", ""),
        ("campo_1079__colaboradores", ""),
        ("campo_1089__colaboradores", ""),
        ("campo_1088__colaboradores", ""),
        ("campo_1078__colaboradores", ""),
        ("campo_1087__colaboradores", ""),
    ]
    for gid in datos.grupos:
        form.append(("permisos_grupos[]", str(gid)))
    for uid in datos.usuarios:
        form.append(("permisos_usuarios[]", str(uid)))
    form += [
        ("csrf_token", csrf),
        ("cc-num", _CC_NUM),
        ("ajax", "true"),
        ("csrf_token", csrf),
        ("validar_formatos_nacionales", "false"),
        ("csrf_token", csrf),
    ]

    try:
        response = client.post_form(_SAVEADD_COLABORADOR_PATH, form)
    except SudespachoLegacyError as exc:
        raise SudespachoRelationsError(
            f"POST {_SAVEADD_COLABORADOR_PATH} falló: {exc}"
        ) from exc

    colab_id = _extract_id(response)
    if not colab_id:
        raise SudespachoRelationsError(
            f"Colaborador creado pero no se pudo extraer su ID. "
            f"Respuesta: {str(response)[:400]}"
        )
    return colab_id


def create_colaborador(
    datos: NuevoColaborador,
    *,
    client: SudespachoLegacyClient | None = None,
) -> str:
    """Crea un nuevo colaborador en sudespacho.net.

    Estrategia REST-first (desde 2026-05-06):
      1. Intenta crear vía REST API (/api/element_register/colaboradores).
         Auth: JWT Bearer — NO requiere PHPSESSID ni CSRF.
         Confirmado con HAR judicial_648.har, tenant tnm.
      2. Si REST falla (JWT expirado/ausente o error de red), cae al frontal
         heredado (PHPSESSID + CSRF), que sigue operativo.

    Args:
        datos: Datos del colaborador a crear.
        client: Cliente legacy reutilizable (opcional; solo para fallback).

    Returns:
        ID numérico del colaborador creado (str).

    Raises:
        SudespachoRelationsError: si ambas vías fallan.
    """
    # 1. Intentar REST (sin PHPSESSID)
    try:
        return _rest_post_colaborador(datos)
    except (SudespachoRelationsError, ValueError) as rest_err:
        _log.warning(
            "REST create_colaborador falló (%s) — usando legacy como fallback",
            rest_err,
        )

    # 2. Fallback: legacy saveadd (requiere PHPSESSID)
    owns_client = client is None
    if owns_client:
        client = SudespachoLegacyClient()
    try:
        return _create_colaborador_legacy(datos, client)
    finally:
        if owns_client:
            try:
                client.__exit__(None, None, None)
            except Exception:
                pass


def _extract_id(response: Any) -> str | None:
    """Extrae el ID numérico del dict de respuesta JSON de saveadd/saveedit."""
    if not isinstance(response, dict):
        return None
    dato = response.get("dato")
    if dato is not None and str(dato).isdigit():
        return str(dato)
    for key in ("id", "miembro", "colaborador_id"):
        val = response.get(key)
        if val is not None and str(val).isdigit():
            return str(val)
    return None


# ---------------------------------------------------------------------------
# Vinculación de relaciones — REST (sin PHPSESSID, confirmado 2026-05-06)
# ---------------------------------------------------------------------------

def _link_rest(
    element: str,
    exp_id: str,
    relations: list[str],
) -> None:
    """POST /api/relation_element/{element}/{exp_id} con x-api-key.

    Confirmado 2026-05-06 en tenant tnm:
      - Auth: x-api-key (clave estática, no caduca) — migrado desde Bearer JWT el 2026-05-06
      - Body: array JSON  ["right.clientes_propios.2", ...]
      - Response 201 "Created!" en éxito
      - Idempotente: relaciones ya existentes devuelven 201 sin crear duplicados
      - Independiente de PHPSESSID

    Comportamiento con datos inválidos (documentado):
      - Direction inválida  → HTTP 500 (PHP exception sin validar)
      - Array vacío []      → HTTP 404 "It is necessary to include properties"
      - exp_id inexistente  → HTTP 201 (sin validación de FK server-side)

    Args:
        element: Slug del elemento receptor (ej. "extrajudiciales").
        exp_id: ID del expediente receptor.
        relations: Lista de strings con sintaxis "{dir}.{slug}.{id}".

    Raises:
        SudespachoRelationsError: HTTP != 201 o error de red.
        ValueError: SUDESPACHO_API_KEY no configurado.
    """
    api_key = (os.getenv("SUDESPACHO_API_KEY") or "").strip()
    if not api_key:
        raise ValueError(
            "SUDESPACHO_API_KEY vacío en .env — ve a tnm.sudespacho.net → Ajustes → API"
        )

    url = f"{_REST_BASE}{_REST_RELATION_PATH.format(element=element, exp_id=exp_id)}"
    headers = {
        "x-api-key":    api_key,
        "Content-Type": "application/json",
        "Accept":       "application/json",
    }

    try:
        r = httpx.post(url, json=relations, headers=headers, timeout=_REST_TIMEOUT)
    except httpx.HTTPError as exc:
        raise SudespachoRelationsError(
            f"REST POST relation_element/{element}/{exp_id} falló: {exc}"
        ) from exc

    if r.status_code == 201:
        return

    raise SudespachoRelationsError(
        f"REST POST relation_element/{element}/{exp_id} "
        f"→ HTTP {r.status_code}: {r.text[:200]}"
    )


def get_relaciones(element: str, exp_id: str) -> dict[str, list[dict[str, Any]]]:
    """LEE las relaciones de un expediente. `{elemento_hijo: [{id, ...valores}]}`.

    Descubierto sondeando el tenant tnm el 2026-09-04 (exp 634). Cierra el hueco que
    `INTEGRACION_SUDESPACHO.md` daba por insalvable —«no hay ruta REST de LECTURA de
    relaciones, el vínculo solo se verifica por UI»—: eso es cierto de
    ``relation_element`` (405 `Allow: POST, PUT, DELETE`, medido) y **falso de la API**,
    porque la lectura vive en ``related_register``, que el spec declara como
    "Retrieves the collection of RelatedRegister resources".

    **La trampa del formato, medida y no supuesta.** El servidor devuelve, por bloque,
    ``registries`` llaveado por id; pero la lista de la clave ``N`` **arrastra todos los
    registros anteriores**, así que la clave con más vínculos trae la colección entera.
    Aplanar las entradas cuenta 6 colaboradores donde hay 3 y triplica al primero. El
    registro que corresponde a una clave es **el que casa por ``id``** — no ``[-1]``,
    que acierta solo mientras el arrastre ponga el propio al final.

    Args:
        element: Slug del elemento padre (ej. "extrajudiciales").
        exp_id: ID del expediente padre.

    Returns:
        `{elemento_hijo: [{id, ...valores}]}` con **solo los hijos que el servidor
        devuelve**, que son los que tienen algún vínculo. Un `{}` significa «este
        expediente no tiene ninguna relación», y **no** permite distinguir «X es
        relacionable y no tiene ninguna» de «X no es relacionable»: para eso hace falta
        `GET /api/view/config/{element}/relations`, que da el esquema. Un bloque vacío
        sí se respeta si el servidor lo manda.

        Los valores se copian **tal cual**, incluidos `False`, `0` y `""`: esta capa lee,
        no decide qué campo es relevante. Filtrar es cosa de quien presenta.

    Raises:
        SudespachoRelationsError: HTTP != 200, error de red, o **cuerpo con una forma
            que no case con el contrato**. Esto último es deliberado: una forma
            inesperada tiene que llegar al llamador como «no pude leer», nunca como
            «no hay vínculos». Confundir las dos es el defecto que esta función existe
            para que `crm_ficha` no cometa.
        ValueError: SUDESPACHO_API_KEY no configurado.
    """
    api_key = (os.getenv("SUDESPACHO_API_KEY") or "").strip()
    if not api_key:
        raise ValueError(
            "SUDESPACHO_API_KEY vacío en .env — ve a tnm.sudespacho.net → Ajustes → API"
        )

    url = f"{_REST_BASE}{_REST_RELATED_REGISTER_PATH.format(element=element, exp_id=exp_id)}"
    headers = {"x-api-key": api_key, "Accept": "application/json"}

    try:
        r = httpx.get(url, headers=headers, timeout=_REST_TIMEOUT)
    except httpx.HTTPError as exc:
        raise SudespachoRelationsError(
            f"REST GET related_register/{element}/{exp_id} falló: {exc}"
        ) from exc

    if r.status_code != 200:
        raise SudespachoRelationsError(
            f"REST GET related_register/{element}/{exp_id} "
            f"→ HTTP {r.status_code}: {r.text[:200]}"
        )

    try:
        bloques = r.json()
    except Exception as exc:  # pragma: no cover - defensivo
        raise SudespachoRelationsError(
            f"REST GET related_register/{element}/{exp_id}: 200 sin JSON válido"
        ) from exc

    def _mal(que: str) -> SudespachoRelationsError:
        return SudespachoRelationsError(
            f"REST GET related_register/{element}/{exp_id}: cuerpo inesperado — {que}. "
            "Se levanta en vez de devolver vacío: «no pude leer» no es «no hay vínculos»."
        )

    if bloques is None or not isinstance(bloques, list):
        raise _mal(f"la raíz es {type(bloques).__name__}, se esperaba una lista de bloques")

    salida: dict[str, list[dict[str, Any]]] = {}
    for i, bloque in enumerate(bloques):
        if not isinstance(bloque, dict):
            raise _mal(f"el bloque {i} es {type(bloque).__name__}, no un objeto")
        hijo = bloque.get("element")
        if not hijo or not isinstance(hijo, str):
            raise _mal(f"el bloque {i} no nombra su `element`")
        registries = bloque.get("registries")
        if registries is None:
            registries = {}
        if not isinstance(registries, dict):
            # Una lista VACIA parece inofensiva y es la misma forma desconocida que una
            # llena: si se acepta por vacía, el fallo depende de la cardinalidad.
            raise _mal(f"`registries` de {hijo!r} es {type(registries).__name__}, no un objeto")

        vinculos: list[dict[str, Any]] = []
        for rid, entradas in registries.items():
            if entradas is None:
                entradas = []
            if not isinstance(entradas, list):
                raise _mal(f"`registries[{rid!r}]` de {hijo!r} no es una lista")
            vinculos.append(_registro_de_la_clave(rid, entradas))

        # Acumular, NO asignar: dos bloques con el mismo `element` sobrescribían al
        # primero y afirmaban cero vínculos donde había uno.
        salida.setdefault(hijo, []).extend(vinculos)
    return salida


def _registro_de_la_clave(rid: str, entradas: Any) -> dict[str, Any]:
    """El registro que corresponde a la clave `rid`, aplanado a `{id, ...valores}`.

    Casa por `id` en vez de tomar el último: la acumulación del servidor es un
    artefacto observado, no un contrato. Si ninguna entrada casa, se devuelve el id
    a secas — **nunca** los valores de un registro ajeno, que sería inventar el vínculo.
    """
    for entrada in entradas or []:
        if not isinstance(entrada, dict) or str(entrada.get("id")) != str(rid):
            continue
        plano: dict[str, Any] = {"id": str(rid)}
        for v in (entrada.get("values") or []):
            if not isinstance(v, dict):
                continue
            prop = v.get("property")
            nombre = prop.get("name") if isinstance(prop, dict) else prop
            # `if nombre and valor` borraba False, 0 y "" — y con ellos la diferencia
            # entre «campo vacío» y «campo ausente». Esta capa copia; no juzga.
            if nombre:
                plano[nombre] = v.get("value")
        return plano
    return {"id": str(rid)}


def _link_rest_or_legacy(
    rest_element: str,
    exp_id: str,
    rest_relations: list[str],
    legacy_path_tpl: str,
    legacy_related_id: str,
    client: SudespachoLegacyClient,
) -> None:
    """REST-first con fallback legacy para operaciones de vinculación.

    1. Intenta REST (Bearer JWT, sin PHPSESSID).
    2. Si falla (JWT expirado/ausente), usa legacy saveselect (PHPSESSID).

    Args:
        rest_element: Slug del elemento en la URL REST (ej. "extrajudiciales").
        exp_id: ID del expediente.
        rest_relations: Lista de relaciones para el body REST.
        legacy_path_tpl: Path template del endpoint saveselect legacy.
        legacy_related_id: ID del elemento a vincular (para el form legacy).
        client: Cliente legacy ya inicializado (para el fallback).
    """
    try:
        _link_rest(rest_element, exp_id, rest_relations)
        return
    except (SudespachoRelationsError, ValueError) as rest_err:
        _log.warning(
            "REST relation_element falló (%s) — usando legacy saveselect como fallback",
            rest_err,
        )
    # Fallback: legacy saveselect (requiere PHPSESSID)
    _link_element(legacy_path_tpl, exp_id, legacy_related_id, client)


# ---------------------------------------------------------------------------
# Vinculación de relaciones — Legacy (saveselect, requiere PHPSESSID)
# ---------------------------------------------------------------------------

def _link_element(
    path_template: str,
    exp_id: str,
    related_id: str,
    client: SudespachoLegacyClient,
) -> None:
    """Lógica común para vincular un elemento a un expediente extrajudicial.

    Usa el endpoint saveselect (confirmado 2026-04-29). Devuelve JSON:
        {"resultado": true, "info": "...", "acumulaDatos": {...}}
    Se considera éxito si HTTP 2xx y resultado == true.

    Args:
        path_template: Plantilla del path con {exp_id}.
        exp_id: ID del expediente extrajudicial.
        related_id: ID del elemento a vincular (cliente, colaborador...).
        client: Cliente legacy autenticado.

    Raises:
        SudespachoRelationsError: si el POST falla o resultado != true.
    """
    csrf = client.get_csrf_token()
    path = path_template.format(exp_id=exp_id)

    form: list[tuple[str, str]] = [
        ("seleccionado[]", related_id),
        ("numeroresultados_listado", "5"),
        ("documentos_adjuntos_seleccionados", ""),
        ("csrf_token", csrf),
        ("cc-num", _CC_NUM),
    ]

    try:
        r = client._post_form(path, form)
    except SudespachoLegacyError as exc:
        raise SudespachoRelationsError(
            f"POST {path} falló: {exc}"
        ) from exc

    if r.status_code >= 400:
        raise SudespachoRelationsError(
            f"POST {path} → HTTP {r.status_code}. "
            "Verifica que el expediente y el elemento existen en el CRM."
        )

    # El endpoint saveselect devuelve JSON con resultado:true en caso de éxito
    try:
        data = r.json()
        if not data.get("resultado"):
            raise SudespachoRelationsError(
                f"saveselect devolvió resultado=false para {path}. "
                f"Respuesta: {str(data)[:200]}"
            )
    except SudespachoRelationsError:
        raise
    except Exception:
        # Si no es JSON parseable pero HTTP fue 2xx, asumimos éxito
        pass


def link_ev_mmc(
    exp_id: str,
    *,
    cliente_propio_id: str = EV_MMC_SPAIN_ID,
    client: SudespachoLegacyClient | None = None,
) -> None:
    """Vincula un cliente propio E&V como parte del expediente extrajudicial.

    REST-first (confirmado 2026-05-06): usa POST /api/relation_element/
    sin PHPSESSID. Fallback a saveselect legacy si JWT no disponible.
    Operación idempotente: relaciones ya existentes devuelven 201 sin duplicar.

    Args:
        exp_id: ID del expediente extrajudicial.
        cliente_propio_id: ID en tabla clientes_propios. Por defecto
            EV_MMC_SPAIN_ID ("2"). Para vincular ENGEL & VÖLKERS SPAIN
            usar "27" (ver `core.config.CLIENTES_PROPIOS_EV`).
        client: Cliente legacy reutilizable (opcional; solo para fallback).

    Raises:
        SudespachoRelationsError: si el vínculo falla en ambas vías.
    """
    owns_client = client is None
    if owns_client:
        client = SudespachoLegacyClient()
    try:
        _link_rest_or_legacy(
            "extrajudiciales", exp_id,
            [f"right.clientes_propios.{cliente_propio_id}"],
            _LINK_CLIENTE_PATH, cliente_propio_id, client,
        )
    finally:
        if owns_client:
            try:
                client.__exit__(None, None, None)
            except Exception:
                pass


def link_colaborador(
    exp_id: str,
    colab_id: str,
    *,
    client: SudespachoLegacyClient | None = None,
) -> None:
    """Vincula un colaborador existente al expediente.

    REST-first (confirmado 2026-05-06): usa POST /api/relation_element/
    sin PHPSESSID. Fallback a saveselect legacy si JWT no disponible.

    Args:
        exp_id: ID del expediente extrajudicial.
        colab_id: ID del colaborador en el CRM.
        client: Cliente legacy reutilizable (opcional; solo para fallback).

    Raises:
        SudespachoRelationsError: si el vínculo falla en ambas vías.
    """
    owns_client = client is None
    if owns_client:
        client = SudespachoLegacyClient()
    try:
        _link_rest_or_legacy(
            "extrajudiciales", exp_id,
            [f"right.colaboradores.{colab_id}"],
            _LINK_COLABORADOR_PATH, colab_id, client,
        )
    finally:
        if owns_client:
            try:
                client.__exit__(None, None, None)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Función de alto nivel: ensure_colaborador_vinculado
# ---------------------------------------------------------------------------

def _resolver_colaborador(
    datos: NuevoColaborador,
    *,
    client: SudespachoLegacyClient | None = None,
) -> str | None:
    """La ficha del colaborador, o `None` si no existe. Levanta si no se sabe.

    Compartida por las dos jurisdicciones: R1/H-05 midio que
    `ensure_colaborador_vinculado_judicial` seguia siendo **email-only** y no pasaba por
    aqui, asi que en judicial ni deduplicaba por NIF ni detectaba el conflicto. Anadir
    el contrario judicial y olvidar el colaborador judicial es el mismo error de
    siempre: cerrar una propiedad para un rol no la cierra para los demas.
    """
    r = resolver_parte("colaboradores", nif=datos.nif, email=datos.email)

    # Conflicto y ambiguedad no los arregla ningun respaldo: son estados en los que el
    # CRM SI respondio y lo que dijo no identifica a una sola ficha.
    if r.conflicto or r.ambiguo:
        _exigir_identidad_cierta(r, elemento="colaboradores",
                                 nif=datos.nif, email=datos.email)

    # El respaldo por listado completo es una VIA ALTERNATIVA legitima, no un parche:
    # `element_registries/colaboradores` puede no exponer `email` como filtrable en
    # todos los tenants, y hay un camino legacy que funciona sin `x-api-key`.
    #
    # Pero **solo cubre el criterio EMAIL**. R1/H-04: antes corria tambien cuando la
    # consulta del NIF habia fallado, y entonces vinculaba por email una ficha distinta
    # de la que el NIF senalaba — el respaldo tapaba el criterio caido. Por eso un NIF
    # sin comprobar levanta aunque el email si se pudiera mirar.
    if any(s.startswith("NIF") for s in r.sin_comprobar):
        raise IdentidadSinComprobar(
            f"No se pudo comprobar el NIF {datos.nif!r} en colaboradores: "
            f"{'; '.join(s for s in r.sin_comprobar if s.startswith('NIF'))}. "
            "El respaldo por email no cubre ese criterio, asi que no se crea ni se "
            "vincula nada."
        )

    if r.id:
        return r.id
    if datos.email:
        return find_colaborador_by_email(datos.email, client=client)

    # Sin email no queda via alguna: si el criterio que faltaba era ese, no se sabe.
    if r.sin_comprobar:
        raise IdentidadSinComprobar(
            f"No se pudo comprobar si este colaborador ya existe: "
            f"{'; '.join(r.sin_comprobar)}. No se crea ni se vincula nada."
        )
    return None


def ensure_colaborador_vinculado(
    exp_id: str,
    datos: NuevoColaborador,
    *,
    client: SudespachoLegacyClient | None = None,
) -> tuple[str, bool]:
    """Garantiza que el colaborador existe en el CRM y está vinculado al expediente.

    Flujo:
        1. Busca el colaborador por email en el CRM.
        2. Si no existe → lo crea.
        3. Lo vincula al expediente (independientemente de si ya existía).

    Args:
        exp_id: ID del expediente extrajudicial.
        datos: Datos del colaborador (nombre + email mínimos).
        client: Cliente legacy reutilizable (opcional).

    Returns:
        Tupla (colab_id, created) donde `created` es True si se creó nuevo.

    Raises:
        SudespachoRelationsError: si algún paso falla.

    Example::

        colab_id, created = ensure_colaborador_vinculado(
            "600",
            NuevoColaborador(
                nombre="Maria Garcia",
                email="maria.garcia@engelvoelkers.com",
                movil="+34 600 123 456",
            )
        )
        if created:
            print(f"Colaborador creado: {colab_id}")
        else:
            print(f"Colaborador ya existía: {colab_id}")
    """
    owns_client = client is None
    if owns_client:
        client = SudespachoLegacyClient()
    try:
        # 1. Resolver por email O por NIF (antes solo por email, asi que el mismo
        #    consultor con dos direcciones daba dos fichas).
        colab_id = _resolver_colaborador(datos, client=client)
        created = False

        # 2. Crear si no existe
        if colab_id is None:
            colab_id = create_colaborador(datos, client=client)
            created = True

        # 3. Vincular al expediente
        link_colaborador(exp_id, colab_id, client=client)

        return colab_id, created

    finally:
        if owns_client:
            try:
                client.__exit__(None, None, None)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Relaciones para expedientes JUDICIALES
# ---------------------------------------------------------------------------

def link_ev_mmc_judicial(
    exp_id: str,
    *,
    cliente_propio_id: str = EV_MMC_SPAIN_ID,
    client: SudespachoLegacyClient | None = None,
) -> None:
    """Vincula un cliente propio E&V como parte del expediente judicial.

    REST-first (confirmado 2026-05-06). Fallback a saveselect legacy.

    Args:
        exp_id: ID del expediente judicial.
        cliente_propio_id: ID en tabla clientes_propios. Por defecto
            EV_MMC_SPAIN_ID ("2"). Para vincular ENGEL & VÖLKERS SPAIN
            usar "27" (ver `core.config.CLIENTES_PROPIOS_EV`).
        client: Cliente legacy reutilizable (opcional; solo para fallback).
    """
    owns_client = client is None
    if owns_client:
        client = SudespachoLegacyClient()
    try:
        _link_rest_or_legacy(
            "expedientes_judiciales", exp_id,
            [f"right.clientes_propios.{cliente_propio_id}"],
            _LINK_CLIENTE_JUDICIAL_PATH, cliente_propio_id, client,
        )
    finally:
        if owns_client:
            try:
                client.__exit__(None, None, None)
            except Exception:
                pass


def link_contrario_judicial(
    exp_id: str,
    contrario_id: str,
    *,
    client: SudespachoLegacyClient | None = None,
) -> None:
    """Vincula un cliente contrario al expediente judicial.

    REST-first (confirmado 2026-05-06). Fallback a saveselect legacy.

    Args:
        exp_id: ID del expediente judicial.
        contrario_id: ID del cliente contrario en el CRM (clientes_contrarios).
        client: Cliente legacy reutilizable (opcional; solo para fallback).
    """
    owns_client = client is None
    if owns_client:
        client = SudespachoLegacyClient()
    try:
        _link_rest_or_legacy(
            "expedientes_judiciales", exp_id,
            [f"right.clientes_contrarios.{contrario_id}"],
            _LINK_CONTRARIO_JUDICIAL_PATH, contrario_id, client,
        )
    finally:
        if owns_client:
            try:
                client.__exit__(None, None, None)
            except Exception:
                pass


def link_procurador_judicial(
    exp_id: str,
    procurador_id: str,
    *,
    client: SudespachoLegacyClient | None = None,
) -> None:
    """Vincula un procurador propio al expediente judicial.

    REST-first (confirmado 2026-05-06). Fallback a saveselect legacy.

    Args:
        exp_id: ID del expediente judicial.
        procurador_id: ID del procurador en el CRM (procuradores_propios).
        client: Cliente legacy reutilizable (opcional; solo para fallback).
    """
    owns_client = client is None
    if owns_client:
        client = SudespachoLegacyClient()
    try:
        _link_rest_or_legacy(
            "expedientes_judiciales", exp_id,
            [f"right.procuradores_propios.{procurador_id}"],
            _LINK_PROCURADOR_JUDICIAL_PATH, procurador_id, client,
        )
    finally:
        if owns_client:
            try:
                client.__exit__(None, None, None)
            except Exception:
                pass


def link_colaborador_judicial(
    exp_id: str,
    colab_id: str,
    *,
    client: SudespachoLegacyClient | None = None,
) -> None:
    """Vincula un colaborador existente al expediente judicial.

    REST-first (confirmado 2026-05-06). Fallback a saveselect legacy.

    Args:
        exp_id: ID del expediente judicial.
        colab_id: ID del colaborador en el CRM.
        client: Cliente legacy reutilizable (opcional; solo para fallback).
    """
    owns_client = client is None
    if owns_client:
        client = SudespachoLegacyClient()
    try:
        _link_rest_or_legacy(
            "expedientes_judiciales", exp_id,
            [f"right.colaboradores.{colab_id}"],
            _LINK_COLABORADOR_JUDICIAL_PATH, colab_id, client,
        )
    finally:
        if owns_client:
            try:
                client.__exit__(None, None, None)
            except Exception:
                pass


def ensure_colaborador_vinculado_judicial(
    exp_id: str,
    datos: NuevoColaborador,
    *,
    client: SudespachoLegacyClient | None = None,
) -> tuple[str, bool]:
    """Igual que :func:`ensure_colaborador_vinculado`, para expedientes JUDICIALES.

    Pasa por `_resolver_colaborador`, o sea por NIF **y** email con su politica de
    conflicto. Antes era email-only (R1/H-05) y contradecia la premisa del cambio: la
    identidad de una parte no depende del tipo de expediente al que se vincule.
    """
    owns_client = client is None
    if owns_client:
        client = SudespachoLegacyClient()
    try:
        colab_id = _resolver_colaborador(datos, client=client)
        created = False
        if colab_id is None:
            colab_id = create_colaborador(datos, client=client)
            created = True
        link_colaborador_judicial(exp_id, colab_id, client=client)
        return colab_id, created
    finally:
        if owns_client:
            try:
                client.__exit__(None, None, None)
            except Exception:
                pass

def create_tag_judicial(
    nombre: str,
    color_hex: str,
    *,
    client: SudespachoLegacyClient | None = None,
) -> str:
    """Crea un nuevo tag en el grupo judicial (miembro/2) de sudespacho.

    Necesario para añadir tags de ciudad (Madrid, Barcelona, etc.) que
    faltan en el grupo judicial. Los IDs resultantes deben añadirse
    como constantes J_TAG_* en sudespacho_create.py.

    Args:
        nombre: Nombre del tag (ej. "MADRID").
        color_hex: Color hexadecimal CON almohadilla (ej. "#5b9bd1").
        client: Cliente legacy reutilizable (opcional).

    Returns:
        ID numérico del tag creado (str).

    Raises:
        SudespachoRelationsError: si la creación falla.

    Example::

        tag_id = create_tag_judicial("MADRID", "#5b9bd1")
        # → "302"  (ID asignado por el servidor)
        # Añadir a sudespacho_create.py:
        #   J_TAG_AZUL_MADRID = f"#5b9bd1___{tag_id}"
    """
    owns_client = client is None
    if owns_client:
        client = SudespachoLegacyClient()
    try:
        csrf = client.get_csrf_token()

        form: list[tuple[str, str]] = [
            ("campo_2424__tags_input", nombre),
            ("campo_2422__tags_input", color_hex),
        ]
        for gid in GRUPOS_DEFAULT:
            form.append(("permisos_grupos[]", str(gid)))
        for uid in USUARIOS_DEFAULT:
            form.append(("permisos_usuarios[]", str(uid)))
        form += [
            ("csrf_token", csrf),
            ("cc-num", _CC_NUM),
            ("ajax", "true"),
            ("csrf_token", csrf),
            ("validar_formatos_nacionales", "false"),
            ("csrf_token", csrf),
        ]

        try:
            response = client.post_form(_SAVEADD_TAG_JUDICIAL_PATH, form)
        except SudespachoLegacyError as exc:
            raise SudespachoRelationsError(
                f"POST {_SAVEADD_TAG_JUDICIAL_PATH} falló: {exc}"
            ) from exc

        tag_id = _extract_id(response)
        if not tag_id:
            raise SudespachoRelationsError(
                f"Tag '{nombre}' creado pero no se pudo extraer su ID. "
                f"Respuesta: {str(response)[:400]}"
            )
        return tag_id

    finally:
        if owns_client:
            try:
                client.__exit__(None, None, None)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Búsqueda de colaboradores — REST API (2026-05-04: migrado desde PHP legacy)
# ---------------------------------------------------------------------------
#
# DEAD END — POST /views/menu/elemento/colaboradores (PHP legacy):
#   Requiere PHPSESSID válido. El login SPA no crea PHPSESSID (confirmado
#   2026-05-04). El servidor PHP expira la sesión tras ~24 min de inactividad
#   y no hay mecanismo automatizable para renovarla sin login PHP legacy.
#   Por tanto, toda búsqueda de colaboradores usa ahora la REST API.
#
# Endpoint REST (confirmado 2026-05-04, sin PHPSESSID):
#   GET /api/element_registries/colaboradores
#       ?page=1&itemsPerPage=500&properties[]=nombre&properties[]=email
#   Auth: x-api-key
#   Nota: el endpoint NO filtra server-side por término; filtrado en cliente.
#   Total colaboradores tenant tnm: ~765.

_PATH_COLAB_LIST = "/views/menu/elemento/colaboradores"  # conservado para link/create


def _list_colaboradores_rest(
    *,
    cfg: SudespachoConfig | None = None,
) -> list[dict[str, str]]:
    """Obtiene todos los colaboradores del CRM vía REST API (sin PHPSESSID).

    Usa GET /api/element_registries/colaboradores paginado (500/página).
    El filtrado se realiza en cliente porque el endpoint no soporta búsqueda
    server-side.

    Args:
        cfg: Configuración REST (opcional; si None, carga desde .env).

    Returns:
        Lista de dicts {id, label, email}.

    Raises:
        SudespachoRelationsError: si el endpoint falla o devuelve error HTTP.
    """
    if cfg is None:
        cfg = SudespachoConfig.from_env()

    PAGE_SIZE = 500
    base_url  = f"{cfg.base_url}/api/element_registries/colaboradores"
    headers   = {cfg.auth_header: cfg.api_key}

    def _fetch_page(page: int) -> list[dict]:
        """Descarga una página y devuelve sus miembros crudos."""
        try:
            r = httpx.get(
                base_url,
                params={
                    "page":         page,
                    "itemsPerPage": PAGE_SIZE,
                    "properties[]": ["nombre", "email"],
                },
                headers=headers,
                timeout=cfg.timeout_s,
            )
        except httpx.HTTPError as exc:
            raise SudespachoRelationsError(
                f"REST GET colaboradores (página {page}) falló: {exc}"
            ) from exc
        if r.status_code != 200:
            raise SudespachoRelationsError(
                f"REST GET colaboradores p{page} → HTTP {r.status_code}: {r.text[:300]}"
            )
        return r.json()

    def _parse_members(members: list[dict]) -> list[dict[str, str]]:
        """Convierte miembros crudos en dicts {id, label, email}."""
        out = []
        for member in members:
            colab_id = str(member.get("id", ""))
            nombre = email = ""
            for val in member.get("values", []):
                prop_name = val.get("property", {}).get("name", "")
                if prop_name == "nombre":
                    nombre = val.get("value", "") or ""
                elif prop_name == "email":
                    email = val.get("value", "") or ""
            if not nombre:
                continue
            out.append({
                "id":    colab_id,
                "label": nombre + (f"  ·  {email}" if email else ""),
                "email": email,
            })
        return out

    # Página 1: determina el total y ya aporta los primeros registros.
    data_p1  = _fetch_page(1)
    total    = data_p1.get("hydra:totalItems", 0)
    members1 = data_p1.get("hydra:member", [])
    results  = _parse_members(members1)

    num_pages = math.ceil(total / PAGE_SIZE) if total else 1
    remaining = list(range(2, num_pages + 1))

    if remaining:
        # Descarga las páginas restantes en paralelo (máx. 8 hilos).
        pages_data: dict[int, list[dict]] = {}
        with ThreadPoolExecutor(max_workers=min(8, len(remaining))) as pool:
            future_to_page = {pool.submit(_fetch_page, p): p for p in remaining}
            for future in as_completed(future_to_page):
                p = future_to_page[future]
                data = future.result()   # propaga SudespachoRelationsError si hay fallo
                pages_data[p] = data.get("hydra:member", [])

        # Añadir en orden para mantener estabilidad del resultado.
        for p in remaining:
            results.extend(_parse_members(pages_data[p]))

    return results


def _search_colaboradores_html(
    term: str,
    client: SudespachoLegacyClient,
) -> list[dict[str, str]]:
    """POST al listado de colaboradores con cadBusqueda y parsea la tabla HTML.

    Returns:
        Lista de dicts {id, label, email}.
    """
    csrf = client.get_csrf_token()
    form: list[tuple[str, str]] = [
        ("cadBusqueda",                                        term),
        ("csrf_token",                                         csrf),
        ("ubicacion",                                          ""),
        ("idlistado_bsq_list_colaboradores",                   ""),
        # Sin paginación: pedimos hasta 1000 resultados para no perder
        # colaboradores cuando cadBusqueda="" (la página por defecto es ~20).
        ("numeroresultados_listado_bsq_list_colaboradores",    "1000"),
    ]
    try:
        r = client._post_form(_PATH_COLAB_LIST, form)
    except SudespachoLegacyError as exc:
        raise SudespachoRelationsError(
            f"POST {_PATH_COLAB_LIST} falló: {exc}"
        ) from exc

    html = r.text
    results: list[dict[str, str]] = []
    for row_m in _ROW_RE.finditer(html):
        colab_id = row_m.group(1)
        cells = _TD_RE.findall(row_m.group(0))
        if len(cells) < 6:
            continue
        name  = _TAG_RE.sub("", cells[3]).strip()
        email = _TAG_RE.sub("", cells[5]).strip()
        if not name:
            continue
        results.append({
            "id":    colab_id,
            "label": name + (f"  ·  {email}" if email else ""),
            "email": email,
        })
    return results


def find_colaborador_by_email(
    email: str,
    *,
    client: SudespachoLegacyClient | None = None,
) -> str | None:
    """Busca un colaborador en el CRM por su dirección de email (búsqueda exacta).

    Usa la REST API (/api/element_registries/colaboradores) — no requiere PHPSESSID.
    El parámetro `client` se conserva por compatibilidad con llamadas existentes
    pero ya no se usa en la búsqueda.

    Args:
        email: Email del colaborador.
        client: Ignorado (conservado por compatibilidad).

    Returns:
        ID del colaborador si existe, None si no se encuentra.
    """
    if not email:
        return None
    try:
        all_colabs = _list_colaboradores_rest()
    except SudespachoRelationsError:
        raise
    email_lower = email.strip().lower()
    for c in all_colabs:
        if c["email"].lower() == email_lower:
            return c["id"]
    return None


def load_all_colaboradores(
    *,
    client: SudespachoLegacyClient | None = None,
) -> list[dict[str, str]]:
    """Carga todos los colaboradores del CRM sin filtro.

    Usa la REST API (/api/element_registries/colaboradores) — no requiere PHPSESSID.
    El parámetro `client` se conserva por compatibilidad.

    Returns:
        Lista completa de dicts {id, label, email}.
    """
    try:
        return _list_colaboradores_rest()
    except SudespachoRelationsError:
        raise


def search_colaboradores_for_ui(
    term: str,
    *,
    client: SudespachoLegacyClient | None = None,
) -> list[dict[str, str]]:
    """Busca colaboradores en el CRM para autosugerencia en la UI.

    Usa la REST API — no requiere PHPSESSID. Carga todos los colaboradores
    y filtra en cliente (el endpoint no soporta búsqueda server-side).

    Args:
        term: Nombre o email parcial (mínimo 2 caracteres).
        client: Ignorado (conservado por compatibilidad).

    Returns:
        Lista de dicts {id, label, email} con los resultados que contengan
        `term` (insensible a mayúsculas) en nombre o email.

    Raises:
        SudespachoRelationsError: si el endpoint REST falla.

    Example::

        results = search_colaboradores_for_ui("joaquin")
        # → [{"id": "762", "label": "JOAQUIN ALAPONT  ·  joaquin.alapont@engelvoelkers.com",
        #      "email": "joaquin.alapont@engelvoelkers.com"}, ...]
    """
    if not term or len(term) < 2:
        return []
    try:
        all_colabs = _list_colaboradores_rest()
    except SudespachoRelationsError:
        raise
    term_lower = term.strip().lower()
    return [c for c in all_colabs if term_lower in c["label"].lower()]


# ---------------------------------------------------------------------------
# Verificación de coherencia local ↔ CRM (validación preventiva)
# ---------------------------------------------------------------------------
#
# Origen del módulo (2026-05-11): incidencia BaRR3 — el caso local
# "BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU" tenía registrado en
# `_caso.md` el expediente CRM ID 648 cuando el expediente real de Roser es
# 649. ID 648 era un expediente de prueba creado durante el desarrollo el
# 2026-04-26 (HAR `judicial_648.har`, "Pull real expediente 648: 5 docs"); el
# vínculo se quedó colgando en `_caso.md` aunque el caso real se creó
# después. Esta función expone una validación tardía que el caller (UI o
# CLI) invoca tras `register_expediente` para detectar el mismatch antes de
# que el pull descargue documentos contaminados.
#
# Diseño: nunca lanza excepciones. El CRM puede estar caído, la API key
# puede no estar configurada o el expediente puede haber sido borrado — en
# todos esos casos el resultado pone `crm_unreachable=True` o `found=False`
# y el caller decide la severidad (warning visible en UI, log forense
# vía `intake_log`, no aborta el flujo).

# Propiedades a pedir al CRM según el slug del elemento. La propiedad que
# guarda la "referencia que el cliente puso en el formulario" es:
#   - judicial:       `referencia_cliente` (lowercase, confirmado 2026-05-06)
#   - extrajudicial:  `Referencia_Cliente` (CamelCase, confirmado 2026-05-06)
_REFERENCIA_PROP_BY_ELEMENT: dict[str, str] = {
    "expedientes_judiciales": "referencia_cliente",
    "extrajudiciales":        "Referencia_Cliente",
}

# Alias frecuentes que aparecen en frontmatter / CLI legacy.
_ELEMENT_ALIASES: dict[str, str] = {
    "judiciales":              "expedientes_judiciales",
    "expedientes_judiciales":  "expedientes_judiciales",
    "extrajudiciales":         "extrajudiciales",
    "expedientes_extrajudiciales": "extrajudiciales",
}


def _normalize_element(element: str) -> str | None:
    """Normaliza el slug del elemento a la forma canónica del CRM REST."""
    if not element:
        return None
    return _ELEMENT_ALIASES.get(element.strip())


def fetch_referencia_cliente(
    expediente_id: str | int,
    element: str,
) -> tuple[str | None, bool]:
    """Lee la propiedad ``referencia_cliente`` del expediente en el CRM.

    Estrategia:

    1. ``GET /api/element_registries/{element}`` con filtro
       ``property=id, operator=equal, value=<expediente_id>`` y
       ``properties[]=referencia_cliente`` (o ``Referencia_Cliente`` para
       extrajudicial).
    2. Si el endpoint no acepta filtrar por ``id``, devuelve ``(None, False)``
       y el caller debe caer al modo "barrido por serie" (no implementado
       aquí porque exigiría conocer el año del expediente — la UI lo conoce
       en otros sitios, lo introducimos cuando aparezca necesidad).

    Args:
        expediente_id: ID numérico del expediente en el CRM.
        element: Slug del elemento (``"expedientes_judiciales"`` |
            ``"extrajudiciales"`` o alias listados en ``_ELEMENT_ALIASES``).

    Returns:
        Tupla ``(referencia, crm_unreachable)``.

        - ``referencia`` (``str | None``): valor de ``referencia_cliente`` si
          se ha podido leer; ``None`` si el expediente no se ha encontrado o
          el CRM no es accesible.
        - ``crm_unreachable`` (``bool``): ``True`` si la API key falta o la
          llamada HTTP falla (excepción de red, status != 200). Permite al
          caller distinguir "no encontrado" de "no se pudo consultar".

    Nunca lanza excepciones — los errores se reflejan en el booleano.
    """
    elem = _normalize_element(element)
    if elem is None or elem not in _REFERENCIA_PROP_BY_ELEMENT:
        return None, True

    api_key = (os.getenv("SUDESPACHO_API_KEY") or "").strip()
    if not api_key:
        return None, True

    prop = _REFERENCIA_PROP_BY_ELEMENT[elem]
    url = f"{_REST_BASE}/api/element_registries/{elem}"
    params: list[tuple[str, str]] = [
        ("properties[0]", prop),
        ("filterGroup[condition]",                                          "AND"),
        ("filterGroup[filterGroups][0][condition]",                         "AND"),
        ("filterGroup[filterGroups][0][filters][0][operator]",              "equal"),
        ("filterGroup[filterGroups][0][filters][0][value]",                 str(expediente_id)),
        ("filterGroup[filterGroups][0][filters][0][property]",              "id"),
        ("itemsPerPage",                                                     "10"),
        ("return_totals",                                                    "true"),
    ]
    headers = {"x-api-key": api_key, "Accept": "application/json"}

    try:
        r = httpx.get(url, params=params, headers=headers, timeout=_REST_TIMEOUT)
    except Exception:  # noqa: BLE001 — defensivo: red caída no debe romper el caller
        return None, True

    if r.status_code != 200:
        return None, True

    try:
        data = r.json()
    except Exception:  # noqa: BLE001
        return None, True

    items = data.get("items") or data.get("hydra:member") or []
    target = str(expediente_id)
    for item in items:
        if str(item.get("id", "")) != target:
            continue
        for v in item.get("values", []) or []:
            if v.get("property", {}).get("name", "") == prop:
                value = v.get("value")
                if value is None:
                    return None, False
                return str(value), False
        # ID encontrado pero sin la propiedad → expediente sin referencia
        return None, False

    # ID no aparece entre los items → expediente inexistente (no error)
    return None, False


def verify_expediente_referencia(
    expediente_id: str | int,
    element: str,
    *,
    expected_referencia: str | None,
) -> dict:
    """Compara la ``referencia_cliente`` del CRM con la esperada localmente.

    Pensada para invocarse tras ``register_expediente`` (UI o CLI). Caller
    decide la severidad (warning visible, log forense, etc.).

    Args:
        expediente_id: ID numérico del expediente en el CRM.
        element: Slug del elemento o alias (``"judiciales"``,
            ``"expedientes_judiciales"``, ``"extrajudiciales"``, etc.).
        expected_referencia: Valor que debería tener ``referencia_cliente``
            en el CRM (típicamente el ``case_id`` o ``meta.referencia_crm``
            del caso local). ``None`` si no se conoce (en ese caso ``match``
            queda en ``False`` salvo que el CRM también devuelva ``None``).

    Returns:
        Dict con:
            ``expediente_id`` (str), ``element`` (str canónico),
            ``crm_referencia`` (str | None), ``expected_referencia`` (str | None),
            ``match`` (bool), ``crm_unreachable`` (bool), ``found`` (bool).

        Semántica de ``match``:
            - ``True`` ⇔ ambas referencias coinciden tras normalización
              (espacios colapsados, sin acentos, lowercase).
            - ``False`` en cualquier otro caso (incluido ``crm_unreachable``
              y ``found=False``).

        Semántica de ``found``:
            - ``True`` si el CRM ha devuelto el expediente (aunque la
              propiedad ``referencia_cliente`` esté vacía).
            - ``False`` si el expediente no se ha localizado o el CRM no es
              accesible.

    Nunca lanza excepciones.
    """
    elem_canon = _normalize_element(element) or element
    crm_ref, crm_unreachable = fetch_referencia_cliente(expediente_id, element)

    # ``found`` se aproxima como "el CRM contestó y devolvió referencia". La
    # implementación actual de ``fetch_referencia_cliente`` no distingue
    # "no encontrado" de "encontrado sin referencia" — ambos devuelven
    # ``(None, False)``. La distinción no es relevante para el contrato
    # público de esta función: lo que importa es si la referencia coincide.
    found = (not crm_unreachable) and (crm_ref is not None)

    # Comparación normalizada: colapsa espacios, quita acentos, lowercase.
    if crm_ref is None or expected_referencia is None:
        match = False
    else:
        match = normalize_referencia(crm_ref) == normalize_referencia(expected_referencia)

    return {
        "expediente_id":       str(expediente_id),
        "element":             elem_canon,
        "crm_referencia":      crm_ref,
        "expected_referencia": expected_referencia,
        "match":               match,
        "crm_unreachable":     crm_unreachable,
        "found":               found,
    }
