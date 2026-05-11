"""Operaciones de relación en sudespacho.net para FeesDefender.

Endpoints confirmados el 2026-04-29 contra el tenant tnm.sudespacho.net:

    1. Buscar expediente extrajudicial por referencia_cliente (deduplicación)
       GET /autocompletar/buscar/elemento/extrajudiciales?term={term}&
       → [{id, label, value: "{exp_id}", data}]

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
)

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
_REST_CREATE_COLABORADOR = "/api/element_register/colaboradores"
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


def find_expediente_by_referencia(
    referencia_cliente: str,
    *,
    client: SudespachoLegacyClient | None = None,
) -> str | None:
    """Busca un expediente extrajudicial por su referencia_cliente (case_id).

    Útil para detectar duplicados antes de crear un nuevo expediente.

    Args:
        referencia_cliente: El case_id de FeesDefender (ej. "MaRS2 - ...").
            Coincide exactamente con campo_1740 del formulario.
        client: Cliente legacy reutilizable (opcional).

    Returns:
        ID del expediente si existe, None si no hay coincidencia.

    Example::

        exp_id = find_expediente_by_referencia("MaRS2 - Puerto Rico 2, ...")
        if exp_id:
            print(f"Ya existe: expediente #{exp_id}")
    """
    owns_client = client is None
    if owns_client:
        client = SudespachoLegacyClient()
    try:
        results = _autocomplete("extrajudiciales", referencia_cliente, client)
        if results:
            return str(results[0]["value"])
        return None
    except SudespachoLegacyError as exc:
        raise SudespachoRelationsError(str(exc)) from exc
    finally:
        if owns_client:
            try:
                client.__exit__(None, None, None)
            except Exception:
                pass


def find_expediente_judicial_by_referencia(
    referencia_cliente: str,
    *,
    client: SudespachoLegacyClient | None = None,
) -> str | None:
    """Busca un expediente judicial por su referencia_cliente (case_id).

    Útil para detectar duplicados antes de crear un nuevo expediente judicial.

    Args:
        referencia_cliente: El case_id de FeesDefender (ej. "MaRS2 - ...").
            Coincide con campo_867 del formulario judicial.
        client: Cliente legacy reutilizable (opcional).

    Returns:
        ID del expediente si existe, None si no hay coincidencia.

    Example::

        exp_id = find_expediente_judicial_by_referencia("MaRS2 - Puerto Rico 2, ...")
        if exp_id:
            print(f"Ya existe expediente judicial #{exp_id}")
    """
    owns_client = client is None
    if owns_client:
        client = SudespachoLegacyClient()
    try:
        results = _autocomplete("expedientes_judiciales", referencia_cliente, client)
        if results:
            return str(results[0]["value"])
        return None
    except SudespachoLegacyError as exc:
        raise SudespachoRelationsError(str(exc)) from exc
    finally:
        if owns_client:
            try:
                client.__exit__(None, None, None)
            except Exception:
                pass


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
        # 1. Buscar por email
        colab_id = find_colaborador_by_email(datos.email, client=client)
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
    """Garantiza que el colaborador existe en el CRM y está vinculado al expediente judicial.

    Mismo flujo que ensure_colaborador_vinculado() pero para expedientes judiciales.

    Args:
        exp_id: ID del expediente judicial.
        datos: Datos del colaborador.
        client: Cliente legacy reutilizable (opcional).

    Returns:
        Tupla (colab_id, created).
    """
    owns_client = client is None
    if owns_client:
        client = SudespachoLegacyClient()
    try:
        colab_id = find_colaborador_by_email(datos.email, client=client)
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


# ---------------------------------------------------------------------------
# Creación de tags en el grupo judicial (grupo 2)
# ---------------------------------------------------------------------------

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
            - ``True`` ⇔ ambas referencias son strings idénticos tras strip.
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

    # Comparación tolerante a espacios; sensible a mayúsculas/acentos (la
    # referencia_cliente del CRM debe coincidir exactamente con el case_id).
    if crm_ref is None or expected_referencia is None:
        match = False
    else:
        match = crm_ref.strip() == expected_referencia.strip()

    return {
        "expediente_id":       str(expediente_id),
        "element":             elem_canon,
        "crm_referencia":      crm_ref,
        "expected_referencia": expected_referencia,
        "match":               match,
        "crm_unreachable":     crm_unreachable,
        "found":               found,
    }
