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


# ---------------------------------------------------------------------------
# Relaciones para expedientes JUDICIALES
# ---------------------------------------------------------------------------

def link_ev_mmc_judicial(
    exp_id: str,
    *,
    client: SudespachoLegacyClient | None = None,
) -> None:
    """Vincula EV MMC SPAIN, S.L.U. (ID=2) como cliente del expediente judicial.

    Args:
        exp_id: ID del expediente judicial.
        client: Cliente legacy reutilizable (opcional).
    """
    owns_client = client is None
    if owns_client:
        client = SudespachoLegacyClient()
    try:
        _link_element(_LINK_CLIENTE_JUDICIAL_PATH, exp_id, EV_MMC_SPAIN_ID, client)
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

    Args:
        exp_id: ID del expediente judicial.
        contrario_id: ID del cliente contrario en el CRM (clientes_contrarios).
        client: Cliente legacy reutilizable (opcional).
    """
    owns_client = client is None
    if owns_client:
        client = SudespachoLegacyClient()
    try:
        _link_element(_LINK_CONTRARIO_JUDICIAL_PATH, exp_id, contrario_id, client)
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

    Args:
        exp_id: ID del expediente judicial.
        procurador_id: ID del procurador en el CRM (procuradores_propios).
        client: Cliente legacy reutilizable (opcional).
    """
    owns_client = client is None
    if owns_client:
        client = SudespachoLegacyClient()
    try:
        _link_element(_LINK_PROCURADOR_JUDICIAL_PATH, exp_id, procurador_id, client)
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

    Args:
        exp_id: ID del expediente judicial.
        colab_id: ID del colaborador en el CRM.
        client: Cliente legacy reutilizable (opcional).
    """
    owns_client = client is None
    if owns_client:
        client = SudespachoLegacyClient()
    try:
        _link_element(_LINK_COLABORADOR_JUDICIAL_PATH, exp_id, colab_id, client)
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
# Búsqueda de colaboradores — endpoint real: POST /views/menu/elemento/colaboradores
# ---------------------------------------------------------------------------
#
# DEAD END documentado: GET /autocompletar/buscar/elemento/colaboradores?term=...
# devuelve siempre body vacío (HTTP 200, len=0) aunque existan colaboradores.
# Confirmado 2026-05-04 contra tenant tnm. Usar _search_colaboradores_html().
#
# Estructura HTML de la tabla (confirmada 2026-05-04):
#   <tr id="fila_colaboradores_{id}">
#     <td>[0] Co</td> <td>[1]</td> <td>[2]</td>
#     <td>[3] NOMBRE COMPLETO</td>
#     <td>[4]</td>
#     <td>[5] email@engelvoelkers.com</td>
#     ...
#   </tr>

import re as _re_colab

_ROW_RE    = _re_colab.compile(r'id="fila_colaboradores_(\d+)".*?</tr>', _re_colab.DOTALL | _re_colab.IGNORECASE)
_TD_RE     = _re_colab.compile(r'<td[^>]*>(.*?)</td>',                   _re_colab.DOTALL | _re_colab.IGNORECASE)
_TAG_RE    = _re_colab.compile(r'<[^>]+>')

_PATH_COLAB_LIST = "/views/menu/elemento/colaboradores"


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

    Usa POST /views/menu/elemento/colaboradores con cadBusqueda=email y
    devuelve el ID del primer resultado cuyo email coincida exactamente.

    Args:
        email: Email del colaborador.
        client: Cliente legacy reutilizable (opcional).

    Returns:
        ID del colaborador si existe, None si no se encuentra.
    """
    if not email:
        return None
    owns_client = client is None
    if owns_client:
        client = SudespachoLegacyClient()
    try:
        results = _search_colaboradores_html(email, client)
        email_lower = email.strip().lower()
        for r in results:
            if r["email"].lower() == email_lower:
                return r["id"]
        return None
    except SudespachoRelationsError:
        raise
    finally:
        if owns_client:
            try:
                client.__exit__(None, None, None)
            except Exception:
                pass


def load_all_colaboradores(
    *,
    client: SudespachoLegacyClient | None = None,
) -> list[dict[str, str]]:
    """Carga todos los colaboradores del CRM sin filtro.

    Útil para pre-cargar la lista completa en la UI y hacer filtrado local.
    Usa POST /views/menu/elemento/colaboradores con cadBusqueda vacío.

    Returns:
        Lista completa de dicts {id, label, email}.
    """
    owns_client = client is None
    if owns_client:
        client = SudespachoLegacyClient()
    try:
        return _search_colaboradores_html("", client)
    except SudespachoLegacyError as exc:
        raise SudespachoRelationsError(str(exc)) from exc
    finally:
        if owns_client:
            try:
                client.__exit__(None, None, None)
            except Exception:
                pass


def search_colaboradores_for_ui(
    term: str,
    *,
    client: SudespachoLegacyClient | None = None,
) -> list[dict[str, str]]:
    """Busca colaboradores en el CRM para autosugerencia en la UI.

    Usa POST /views/menu/elemento/colaboradores con cadBusqueda=term.
    El CRM filtra por nombre y email sobre todos los campos visibles del listado.

    Args:
        term: Nombre o email parcial (mínimo 2 caracteres).
        client: Cliente legacy reutilizable (opcional).

    Returns:
        Lista de dicts {id, label, email}.

    Raises:
        SudespachoRelationsError: si el endpoint falla.

    Example::

        results = search_colaboradores_for_ui("joaquin")
        # → [{"id": "762", "label": "JOAQUIN ALAPONT  ·  joaquin.alapont@engelvoelkers.com",
        #      "email": "joaquin.alapont@engelvoelkers.com"}, ...]
    """
    if not term or len(term) < 2:
        return []

    owns_client = client is None
    if owns_client:
        client = SudespachoLegacyClient()
    try:
        return _search_colaboradores_html(term, client)
    except SudespachoLegacyError as exc:
        raise SudespachoRelationsError(str(exc)) from exc
    finally:
        if owns_client:
            try:
                client.__exit__(None, None, None)
            except Exception:
                pass
