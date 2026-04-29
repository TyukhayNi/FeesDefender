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

    5. Crear colaborador nuevo
       POST /views/saveadd/elemento/colaboradores
       Body: campo_1086__colaboradores={nombre}
             campo_1080__colaboradores={email}
             campo_1083__colaboradores={movil}
             + csrf_token + cc-num + permisos + ajax=true
       Response: {"resultado": true, "dato": "{colab_id}", ...}

Mapping de campos para colaboradores (confirmado 2026-04-29):
    campo_1086 → Nombre (obligatorio)
    campo_1080 → Email
    campo_1084 → Nacionalidad (select, "1" = Sin Asignar)
    campo_1085 → NIF/CIF
    campo_1083 → Móvil
    campo_1090 → Teléfono 1
    campo_1091 → Teléfono 2
    campo_1079 → Dirección
    campo_1089 → Provincia
    campo_1088 → Población
    campo_1078 → CP
    campo_1087 → Notas

Constantes fijas del tenant tnm:
    EV_MMC_SPAIN_ID = "2"   (B65824054 - EV MMC SPAIN, S.L.U.)
    ID 73 = DUPLICADO — nunca usar
"""

from __future__ import annotations

import urllib.parse
from dataclasses import dataclass, field
from typing import Any

from .sync_sudespacho_legacy import (
    SudespachoLegacyClient,
    SudespachoLegacyError,
)
from .sudespacho_create import (
    GRUPOS_DEFAULT,
    USUARIOS_DEFAULT,
)


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# ID del cliente EV MMC SPAIN, S.L.U. en clientes_propios (confirmado 2026-04-29)
EV_MMC_SPAIN_ID = "2"

_CC_NUM = "HubspotCollectedFormsWorkaround"

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


def find_colaborador_by_email(
    email: str,
    *,
    client: SudespachoLegacyClient | None = None,
) -> str | None:
    """Busca un colaborador en el CRM por su dirección de email.

    Args:
        email: Email del colaborador (ej. "maria.garcia@engelvoelkers.com").
        client: Cliente legacy reutilizable (opcional).

    Returns:
        ID del colaborador si existe, None si no se encuentra.

    Note:
        El autocomplete busca también por nombre; si el email es parcialmente
        único puede haber falsos positivos. Se devuelve el primer resultado.
        Verificar con el nombre si hay ambigüedad.
    """
    if not email:
        return None
    owns_client = client is None
    if owns_client:
        client = SudespachoLegacyClient()
    try:
        results = _autocomplete("colaboradores", email, client)
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
# Creación de colaborador
# ---------------------------------------------------------------------------

def create_colaborador(
    datos: NuevoColaborador,
    *,
    client: SudespachoLegacyClient | None = None,
) -> str:
    """Crea un nuevo colaborador en sudespacho.net.

    Endpoint: POST /views/saveadd/elemento/colaboradores
    Response JSON: {"resultado": true, "dato": "{id}"}

    Args:
        datos: Datos del colaborador a crear.
        client: Cliente legacy reutilizable (opcional).

    Returns:
        ID numérico del colaborador creado (str).

    Raises:
        SudespachoRelationsError: si la creación falla o no devuelve ID.
    """
    owns_client = client is None
    if owns_client:
        client = SudespachoLegacyClient()
    try:
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

        # Extraer ID de la respuesta
        colab_id = _extract_id(response)
        if not colab_id:
            raise SudespachoRelationsError(
                f"Colaborador creado pero no se pudo extraer su ID. "
                f"Respuesta: {str(response)[:400]}"
            )
        return colab_id

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
# Vinculación de relaciones
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
    client: SudespachoLegacyClient | None = None,
) -> None:
    """Vincula EV MMC SPAIN, S.L.U. (ID=2) como cliente del expediente.

    Operación idempotente en la práctica: si ya está vinculado el CRM
    simplemente no añade un duplicado.

    Args:
        exp_id: ID del expediente extrajudicial.
        client: Cliente legacy reutilizable (opcional).

    Raises:
        SudespachoRelationsError: si el vínculo falla.
    """
    owns_client = client is None
    if owns_client:
        client = SudespachoLegacyClient()
    try:
        _link_element(_LINK_CLIENTE_PATH, exp_id, EV_MMC_SPAIN_ID, client)
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

    Args:
        exp_id: ID del expediente extrajudicial.
        colab_id: ID del colaborador en el CRM.
        client: Cliente legacy reutilizable (opcional).

    Raises:
        SudespachoRelationsError: si el vínculo falla.
    """
    owns_client = client is None
    if owns_client:
        client = SudespachoLegacyClient()
    try:
        _link_element(_LINK_COLABORADOR_PATH, exp_id, colab_id, client)
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
