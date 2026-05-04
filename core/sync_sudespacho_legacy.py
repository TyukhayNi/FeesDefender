"""Cliente del frontal heredado de sudespacho.net (CRM PHP/Symfony tradicional).

Justificación
-------------
La API REST nueva (`api-crm-commons-pro.sudespacho.biz`) **no expone** un
endpoint para listar los documentos de un expediente. La única superficie
del Gestor Documental que sí lo hace es el frontal heredado del propio
tenant (p. ej. `tnm.sudespacho.net`), que utiliza autenticación por cookie
de sesión PHP (`PHPSESSID`) y un token CSRF (`csrf_token`) inyectado en el
HTML de cualquier página.

Flujo de descarga (decodificado contra el JS legacy):

  1. POST  /gdocu/list/elemento/gdocu/elemento_relacionado/{element}/
           miembro_relacionado/{exp_id}/direccion_relacionado/der
     → devuelve HTML con `id="fila_gdocu_<doc_id>"` para cada documento.
     Extraemos los `doc_id` por regex.

  2. POST  /gestordocumental/predownloadfile/elemento_relacionado/{element}/
           miembro_relacionado/{exp_id}/direccion_relacionado/der
     body: csrf_token + id={doc_id}
     → JSON `{resultado, metodo: 's3'|'s3old'|'cloud', ...}`.

  3. POST  /gestordocumental/descargaficheros3/id_docu/{doc_id}/
           elemento_relacionado/{element}/miembro_relacionado/{exp_id}/
           direccion_relacionado/der
     body: csrf_token
     → JSON `{resultado, url: "<URL S3 prefirmada (5 min)>"}`.

  4. GET   <URL S3>  → binario. El nombre original viene en
     `response-content-disposition`.

Configuración (en `.env`):

    SUDESPACHO_LEGACY_HOST=tnm.sudespacho.net
    SUDESPACHO_LEGACY_PHPSESSID=<valor de la cookie PHPSESSID>
    SUDESPACHO_LEGACY_TIMEOUT_S=120

Cómo obtener el `PHPSESSID`:

    1. Inicia sesión en https://<tu_subdominio>.sudespacho.net.
    2. Abre DevTools → Application → Storage → Cookies →
       `https://<tu_subdominio>.sudespacho.net`.
    3. Copia el `Value` de la cookie `PHPSESSID`.
    4. Pégalo en `SUDESPACHO_LEGACY_PHPSESSID` (sin comillas).

La cookie expira al cerrar sesión o por inactividad. Si una llamada falla
con 401/302 a /login, refresca el valor en `.env`. Mejora futura: implementar
flujo de login automático con usuario/contraseña.
"""

from __future__ import annotations

import json
import os
import re
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

import httpx


class SudespachoLegacyError(RuntimeError):
    pass


def _env(name: str, default: str | None = None) -> str | None:
    v = os.getenv(name, default)
    return v.strip() if isinstance(v, str) else v


# ---------------------------------------------------------------------------
# Detección de sesión expirada y renovación automática de JWT
# ---------------------------------------------------------------------------

# Cadena que aparece en el <title> de la landing de E-plan cuando la sesión
# no está autenticada (HTTP 200 pero no es el CRM).
_EPLAN_MARKER = "E-plan - sudespacho.net"

# Endpoint estándar de Symfony (gesdinet/jwt-refresh-token-bundle).
# Configurable via .env: SUDESPACHO_LEGACY_JWT_REFRESH_PATH
_DEFAULT_JWT_REFRESH_PATH = "/api/token/refresh"


def _is_eplan_landing(r: httpx.Response) -> bool:
    """Devuelve True si la respuesta es la landing de E-plan (sesión no autenticada).

    El servidor devuelve HTTP 200 con la página de marketing de E-plan cuando
    el @token JWT ha expirado y no hay sesión válida. No lanza 401/302.
    Solo se inspecciona el inicio del body para no parsear documentos HTML grandes.
    """
    return r.status_code == 200 and _EPLAN_MARKER in r.text[:2000]


def _update_env_field(
    field: str,
    value: str,
    _env_path: "Path | None" = None,
) -> None:
    """Actualiza (o añade) un campo clave=valor en el .env del proyecto.

    También actualiza os.environ para que el proceso actual vea el nuevo valor
    sin necesidad de reiniciar (importante para SudespachoLegacyConfig.from_env()
    en sucesivas instanciaciones dentro de la misma sesión Streamlit).

    Si el campo no existe en .env se añade al final. Si el valor es idéntico
    al actual no escribe el fichero (evita tocar mtime innecesariamente).

    Args:
        _env_path: ruta al .env; si None, se usa <project_root>/.env.
                   Parámetro privado para facilitar tests unitarios.
    """
    env_path = _env_path or (Path(__file__).resolve().parent.parent / ".env")
    if not env_path.exists():
        return
    try:
        text = env_path.read_text(encoding="utf-8")
        pattern = re.compile(rf"^({re.escape(field)}\s*=\s*)(.*)$", re.MULTILINE)
        if pattern.search(text):
            updated = pattern.sub(rf"\g<1>{value}", text)
        else:
            # Campo no existe → añadirlo al final
            updated = text.rstrip("\n") + f"\n{field}={value}\n"
        if updated != text:
            env_path.write_text(updated, encoding="utf-8")
        # Actualizar el entorno del proceso actual
        os.environ[field] = value
    except Exception:
        pass


_API_CRM_HOST = "https://api-crm-commons-pro.sudespacho.biz"
_JWT_REFRESH_PATH = "/api/user/refresh"   # GET con ?refresh_token=<rt> + Authorization: Bearer <jwt>


def _jwt_expires_in_secs(jwt_str: str) -> int | None:
    """Decodifica el payload del JWT (sin verificar firma) y devuelve los segundos
    hasta expiración. Devuelve None si el token no es un JWT válido.
    Un valor negativo indica que ya ha expirado.
    """
    import base64 as _b64
    try:
        parts = jwt_str.split(".")
        if len(parts) != 3:
            return None
        payload_b64 = parts[1]
        # Añadir padding si falta
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(_b64.urlsafe_b64decode(payload_b64))
        exp = payload.get("exp")
        if exp is None:
            return None
        import time as _time
        return int(exp - _time.time())
    except Exception:
        return None


def _try_refresh_jwt(current_jwt: str, refresh_token: str) -> str | None:
    """Renueva el @token JWT usando el endpoint del CRM.

    Endpoint: GET https://api-crm-commons-pro.sudespacho.biz/api/user/refresh
              ?refresh_token=<@refreshToken>
    Header: Authorization: Bearer <@token-aún-vigente>

    IMPORTANTE: este endpoint requiere que el @token actual sea aún válido (no
    expirado). Está diseñado para renovación PROACTIVA (ej. < 5 min para expirar).
    Si el @token ya expiró, devuelve None y el usuario debe reiniciar sesión.

    Si la renovación tiene éxito, actualiza SUDESPACHO_LEGACY_JWT (y
    SUDESPACHO_LEGACY_REFRESH_TOKEN si el servidor devuelve uno nuevo) tanto
    en .env como en os.environ.

    Args:
        current_jwt: Valor actual del @token (debe ser vigente).
        refresh_token: Valor del @refreshToken almacenado en .env.

    Returns:
        Nuevo @token si la renovación fue exitosa; None si falló.
    """
    if not refresh_token or not current_jwt:
        return None

    try:
        import urllib.parse as _up
        path = f"{_JWT_REFRESH_PATH}?refresh_token={_up.quote(refresh_token)}"
        with httpx.Client(
            base_url=_API_CRM_HOST,
            timeout=20,
            follow_redirects=False,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Authorization": f"Bearer {current_jwt}",
                "Accept": "application/json",
            },
        ) as c:
            r = c.get(path)
        if r.status_code >= 400:
            return None
        try:
            data = r.json()
        except Exception:
            return None
        # El API devuelve {"@token": "<nuevo_jwt>", "@refreshToken": "<nuevo_rt>"}
        # o posiblemente {"token": ..., "refresh_token": ...}
        new_token: str | None = (
            data.get("@token")
            or data.get("token")
            or data.get("jwt")
            or data.get("access_token")
        )
        new_refresh: str | None = (
            data.get("@refreshToken")
            or data.get("refresh_token")
        )
        if new_token:
            _update_env_field("SUDESPACHO_LEGACY_JWT", new_token)
            if new_refresh and new_refresh != refresh_token:
                _update_env_field("SUDESPACHO_LEGACY_REFRESH_TOKEN", new_refresh)
        return new_token or None
    except Exception:
        return None


def _get_phpsessid_from_chrome(host: str) -> tuple[str | None, str | None]:
    """Intenta leer PHPSESSID del perfil de Chrome en el sistema local.

    En Windows, browser_cookie3 requiere permisos de Admin para descifrar
    las cookies de Chrome (DPAPI), por lo que falla en uso normal.
    Esta función queda como stub — la renovación se hace desde la UI Streamlit
    (botón «🔄 Renovar sesión CRM» en el sidebar) o manualmente en .env.

    Returns:
        (None, motivo)  siempre — la renovación automática no está disponible.
    """
    return None, (
        "Renovación automática deshabilitada en Windows (requiere Admin). "
        "Usa el botón «🔄 Renovar sesión CRM» en el sidebar de Streamlit."
    )


def _update_env_phpsessid(new_value: str) -> None:
    """Actualiza SUDESPACHO_LEGACY_PHPSESSID en el .env y en os.environ."""
    _update_env_field("SUDESPACHO_LEGACY_PHPSESSID", new_value)


def renovar_phpsessid_desde_chrome() -> tuple[bool, str]:
    """Intenta renovar PHPSESSID desde Chrome y actualiza el .env.

    Devuelve (True, nuevo_valor) si tuvo éxito, (False, motivo_error) si no.
    Pensado para ser llamado desde el botón «🔄 Renovar sesión CRM» de la UI.
    """
    host = _env("SUDESPACHO_LEGACY_HOST") or "tnm.sudespacho.net"
    value, error = _get_phpsessid_from_chrome(host)
    if value:
        return True, value
    return False, (error or "Error desconocido")


# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SudespachoLegacyConfig:
    host: str                # ej. tnm.sudespacho.net (sin esquema)
    phpsessid: str
    jwt_token: str = ""      # cookie @token (TTL 1h) — requerida desde 2026-05
    refresh_token: str = ""  # cookie @refreshToken (long-lived)
    timeout_s: int = 120

    @classmethod
    def from_env(cls) -> "SudespachoLegacyConfig":
        host = _env("SUDESPACHO_LEGACY_HOST")
        if not host:
            raise SudespachoLegacyError(
                "Falta SUDESPACHO_LEGACY_HOST en .env."
            )
        host = host.replace("https://", "").replace("http://", "").rstrip("/")

        phpsessid = _env("SUDESPACHO_LEGACY_PHPSESSID") or ""
        if not phpsessid:
            raise SudespachoLegacyError(
                "Falta SUDESPACHO_LEGACY_PHPSESSID en .env. "
                "Usa el botón «🔄 Renovar sesión CRM» en Streamlit."
            )
        return cls(
            host=host,
            phpsessid=phpsessid,
            jwt_token=_env("SUDESPACHO_LEGACY_JWT") or "",
            refresh_token=_env("SUDESPACHO_LEGACY_REFRESH_TOKEN") or "",
            timeout_s=int(_env("SUDESPACHO_LEGACY_TIMEOUT_S", "120") or "120"),
        )

    @property
    def base_url(self) -> str:
        return f"https://{self.host}"


# ---------------------------------------------------------------------------
# Endpoints (centralizados)
# ---------------------------------------------------------------------------

ENDPOINTS = {
    # Listado de documentos del Gestor Documental de un elemento dado
    "gdocu_list":     "/gdocu/list/elemento/gdocu/elemento_relacionado/{element}/miembro_relacionado/{id}/direccion_relacionado/der",
    # Pre-descarga: indica método (s3 / cloud / s3old)
    "predownload":    "/gestordocumental/predownloadfile/elemento_relacionado/{element}/miembro_relacionado/{id}/direccion_relacionado/der",
    # URL prefirmada S3
    "download_s3":    "/gestordocumental/descargaficheros3/id_docu/{doc_id}/elemento_relacionado/{element}/miembro_relacionado/{id}/direccion_relacionado/der",
    # Fallback: descarga directa del frontal (stream desde el servidor)
    "download_legacy":"/gestordocumental/descargafichero/id/{doc_id}/",
    # Listado paginado de elementos (expedientes_judiciales, clientes_propios, ...)
    "elements_list":  "/{element_url}/list/elemento/{element}",
}

# Regex para extraer IDs del HTML del listado
_ROW_ID_RE = re.compile(r'id="fila_gdocu_(\d+)"')

# Regex para extraer expedientes del listado: id + bloque HTML de la fila
# Formato: <tr id="fila_expedientes_judiciales_<id>" ...> ... </tr>
_EXP_ROW_RE = re.compile(
    r'<tr[^>]*id="fila_(?P<element>[a-z_]+)_(?P<id>\d+)"[^>]*>(?P<body>.*?)</tr>',
    re.DOTALL,
)

# Última página: aparece en el listado como `pagina(<N>, 'list_<element>')`
_LAST_PAGE_RE = re.compile(r"pagina\((\d+)\s*,\s*'list_[a-z_]+'\)")

# Regex para extraer csrf_token de cualquier página HTML del frontal.
# El CRM ha ido cambiando cómo lo inyecta:
#   v1 (original): var csrf_token = 'TOKEN';          (JS inline, comilla simple)
#   v2 (≥2026-05): var csrf_token = "TOKEN";          (JS inline, comilla doble)
#   v3 (≥2026-05): <script src="...?csrf_token=TOKEN"> (URL param en src de script)
# Captura en grupo 1 la primera coincidencia que encuentre.
_CSRF_RE = re.compile(
    r"(?:"
    r"var\s+csrf_token\s*=\s*['\"]([0-9a-f]{32})['\"]"   # v1 + v2: JS inline
    r"|"
    r"csrf_token=([0-9a-f]{32})"                           # v3: URL param en script src
    r")"
)


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------

@dataclass
class LegacyDocInfo:
    doc_id: str
    raw_html_row: str | None = None  # opcional, para debug


@dataclass
class LegacyDownloadResult:
    doc_id: str
    target_path: Path
    bytes_written: int
    filename_in_disposition: str | None
    method: str  # 's3' | 'cloud' | 'legacy'


@dataclass
class ExpedienteListEntry:
    """Una fila del listado de expedientes_judiciales (u otro elemento).

    Los campos `cliente`, `contraparte`, `referencia_cliente`, etc. se
    extraen del HTML server-rendered. Pueden venir vacíos si el tenant
    tiene la columna oculta o sin valor.
    """
    expediente_id: str
    element: str
    fecha_alta: str | None
    posicion_procesal: str | None       # 'Actor' | 'Demandado' | None
    num_expediente: str | None          # ej. "29"
    serie_expediente: str | None        # ej. "2026"
    referencia_cliente: str | None
    cliente: str | None                 # ej. "EV MMC SPAIN, S.L.U."
    contraparte: str | None
    raw_text: str | None = None         # texto plano de la fila, para debug


# ---------------------------------------------------------------------------
# Cliente
# ---------------------------------------------------------------------------

class SudespachoLegacyClient:
    """Cliente para el frontal heredado del CRM. Mantiene cookie de sesión
    PHP y CSRF token; obtiene el CSRF la primera vez navegando a la home.
    """

    def __init__(self, cfg: SudespachoLegacyConfig | None = None) -> None:
        self.cfg = cfg or SudespachoLegacyConfig.from_env()
        self._csrf_token: str | None = None
        # Bandera anti-bucle: True si ya se intentó renovar el JWT en esta sesión.
        self._jwt_refresh_attempted: bool = False
        self._client = httpx.Client(
            base_url=self.cfg.base_url,
            timeout=self.cfg.timeout_s,
            # Tres cookies requeridas desde 2026-05 (servidor sudespacho).
            # PHPSESSID: sesión PHP. @token: JWT 1h. @refreshToken: long-lived.
            # Nota: httpx envía el nombre tal cual; el servidor espera "@token"
            # (el navegador lo muestra como "%40token" en document.cookie).
            cookies={
                k: v for k, v in {
                    "PHPSESSID":      self.cfg.phpsessid,
                    "@token":         self.cfg.jwt_token,
                    "@refreshToken":  self.cfg.refresh_token,
                }.items() if v
            },
            follow_redirects=False,  # detectar 302 a /login
            headers={
                # User-Agent de Chrome real — Cloudflare bloquea UAs de bot
                # sirviendo la landing page E-plan aunque PHPSESSID sea válido.
                # Confirmado 2026-05-04: FeesGuard/0.1 → landing; Chrome UA → CRM.
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            },
        )

    def __enter__(self) -> "SudespachoLegacyClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self._client.close()

    # --- helpers privados ------------------------------------------------

    def _check_session(self, r: httpx.Response, path: str) -> None:
        """Detecta sesión expirada: 302 a /login o cualquier 401."""
        if r.status_code in (301, 302):
            loc = r.headers.get("location", "")
            if "login" in loc.lower() or "auth" in loc.lower():
                raise SudespachoLegacyError(
                    f"Sesión expirada (redirección a {loc}). "
                    "Refresca SUDESPACHO_LEGACY_PHPSESSID en .env."
                )
        if r.status_code == 401:
            raise SudespachoLegacyError(
                f"401 en {path}. Cookie de sesión inválida. Refresca PHPSESSID."
            )

    def _proactive_refresh_if_needed(self) -> bool:
        """Renueva proactivamente el JWT si le quedan menos de 5 minutos.

        Debe llamarse al inicio de operaciones de larga duración o al obtener
        el CSRF token. No hace nada si el JWT tiene más de 5 min de vida o
        si ya se intentó renovar en esta sesión.

        Returns:
            True si el JWT fue renovado con éxito.
        """
        if self._jwt_refresh_attempted or not self.cfg.jwt_token:
            return False
        secs_left = _jwt_expires_in_secs(self.cfg.jwt_token)
        if secs_left is None or secs_left > 300:   # >5 min → no hace falta
            return False
        self._jwt_refresh_attempted = True
        new_token = _try_refresh_jwt(self.cfg.jwt_token, self.cfg.refresh_token)
        if not new_token:
            return False
        self._client.cookies["@token"] = new_token
        self._csrf_token = None
        return True

    def _check_and_refresh_if_needed(self, r: httpx.Response) -> bool:
        """Detecta landing E-plan. En ese caso el @token ya ha expirado y no
        es posible renovarlo automáticamente (el endpoint de refresh requiere
        un JWT todavía vigente). Registra el intento para evitar bucles.

        Returns:
            False siempre (no puede renovar tras expiración — uso informativo).
        """
        if not _is_eplan_landing(r):
            return False
        self._jwt_refresh_attempted = True   # marcar para evitar bucles
        return False

    def _try_renew_php_session(self, path: str) -> "httpx.Response | None":
        """Intenta renovar la sesión PHP eliminando el PHPSESSID expirado.

        Cuando el PHPSESSID del servidor ha expirado (garbage-collected por
        inactividad), el PHP puede crear una nueva sesión si recibe un @token
        válido sin PHPSESSID. El nuevo PHPSESSID llega en Set-Cookie y httpx
        lo guarda automáticamente en su cookie jar.

        Si la respuesta ya no es E-plan y contiene csrf_token, la sesión se
        renovó con éxito. En ese caso guarda el nuevo PHPSESSID en .env.

        Returns:
            La respuesta si contiene csrf_token, None si sigue siendo E-plan
            o si se produjo un error.
        """
        try:
            # Crear cliente temporal sin PHPSESSID para forzar nueva sesión
            temp_cookies = {
                k: v for k, v in {
                    "@token":        self.cfg.jwt_token,
                    "@refreshToken": self.cfg.refresh_token,
                }.items() if v
            }
            with httpx.Client(
                base_url=self.cfg.base_url,
                timeout=self.cfg.timeout_s,
                cookies=temp_cookies,
                follow_redirects=True,
                headers=dict(self._client.headers),
            ) as tmp:
                r = tmp.get(path)
                if r.status_code >= 400 or _is_eplan_landing(r):
                    return None
                m = _CSRF_RE.search(r.text)
                if not m:
                    return None
                # Nueva sesión establecida — extraer PHPSESSID de las cookies
                new_phpsessid = tmp.cookies.get("PHPSESSID")
                if new_phpsessid:
                    _update_env_field("SUDESPACHO_LEGACY_PHPSESSID", new_phpsessid)
                    self._client.cookies["PHPSESSID"] = new_phpsessid
                # Copiar todas las cookies de la sesión temporal al cliente principal
                for name, val in tmp.cookies.items():
                    self._client.cookies[name] = val
                self._csrf_token = m.group(1) or m.group(2)
                return r
        except Exception:
            return None

    def _get_csrf_token(self) -> str:
        if self._csrf_token:
            return self._csrf_token
        # Renovación proactiva: si el JWT expira en < 5 min, renovar antes de usarlo
        self._proactive_refresh_if_needed()
        # GET / devuelve la landing page de E-plan (no ejecuta JS), sin token.
        # Usamos una URL de CRM autenticado que sabemos que contiene el token.
        # Orden de preferencia: colaboradores → expedientes → raíz con redirect.
        _candidates = [
            "/views/menu/elemento/colaboradores",
            "/views/menu/elemento/expedientes_judiciales",
            "/views/menu/elemento/extrajudiciales",
        ]
        r = None
        for _path in _candidates:
            try:
                r = self._client.get(_path, follow_redirects=True)
            except Exception:
                continue
            self._check_session(r, _path)
            if r.status_code >= 400:
                continue
            # Si detectamos landing E-plan, primero intentar renovar JWT proactivo;
            # si el JWT es válido pero la sesión PHP expiró, intentar nueva sesión.
            if _is_eplan_landing(r):
                self._check_and_refresh_if_needed(r)
                # Intento 1: ¿el @token sigue vigente? Intentar nueva sesión PHP.
                if self.cfg.jwt_token and (_jwt_expires_in_secs(self.cfg.jwt_token) or -1) > 0:
                    r2 = self._try_renew_php_session(_path)
                    if r2 is not None and self._csrf_token:
                        return self._csrf_token
                # Intento 2: JWT renovado recientemente — reintentar con sesión principal
                try:
                    r = self._client.get(_path, follow_redirects=True)
                except Exception:
                    continue
                if r.status_code >= 400:
                    continue
            m = _CSRF_RE.search(r.text)
            if m:
                # Grupo 1 → JS inline (v1/v2), Grupo 2 → URL param en script src (v3)
                self._csrf_token = m.group(1) or m.group(2)
                return self._csrf_token
        # Ningún candidato funcionó — diagnóstico con el último response
        _preview = (r.text[:400].replace("\n", " ").replace("\r", "") if r is not None else "sin respuesta")
        # Diagnóstico específico: ¿es la landing de E-plan?
        _is_eplan = r is not None and _is_eplan_landing(r)
        if _is_eplan:
            raise SudespachoLegacyError(
                "Sesión CRM expirada — el servidor devuelve la landing de E-plan. "
                "El @token JWT ha caducado y no se puede renovar automáticamente. "
                "Solución: inicia sesión en https://tnm.sudespacho.net en Chrome y "
                "usa el botón «🔄 Renovar sesión CRM» en el sidebar de Streamlit "
                "para pegar las nuevas cookies en .env."
            )
        raise SudespachoLegacyError(
            f"No se encontró csrf_token en ninguna página CRM. "
            f"Última URL: {r.url if r is not None else 'N/A'} | "
            f"HTTP {r.status_code if r is not None else 'N/A'} | "
            f"HTML inicio: {_preview}"
        )

    def _post_form(
        self,
        path: str,
        body: "dict[str, str] | list[tuple[str, str]]",
    ) -> httpx.Response:
        encoded = urllib.parse.urlencode(body)
        try:
            r = self._client.post(
                path,
                content=encoded,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "X-Requested-With": "XMLHttpRequest",
                    "Accept": "application/json, text/html;q=0.5",
                },
            )
        except httpx.HTTPError as exc:
            raise SudespachoLegacyError(f"POST {path} falló: {exc}") from exc
        self._check_session(r, path)
        return r

    @staticmethod
    def _parse_json_loose(r: httpx.Response) -> dict[str, Any]:
        """El frontal devuelve JSON con Content-Type text/html. Intentamos parsear
        igualmente; si la respuesta es HTML completo, error."""
        text = r.text.strip()
        if not text:
            raise SudespachoLegacyError(f"Respuesta vacía en {r.request.url}")
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            preview = text[:200]
            raise SudespachoLegacyError(
                f"Respuesta no es JSON parseable. Inicio: {preview}"
            ) from exc

    # --- API pública ------------------------------------------------------

    @property
    def host(self) -> str:
        """Host del tenant sin esquema (ej. 'tnm.sudespacho.net')."""
        return self.cfg.host

    def get_csrf_token(self) -> str:
        """Devuelve el CSRF token activo de la sesión (obteniéndolo si aún no se cacheó).

        Wrapper público de _get_csrf_token(). Útil para módulos externos
        (ej. sudespacho_create.py) que necesitan el token para construir
        el body de una request antes de llamar a post_form().
        """
        return self._get_csrf_token()

    def post_form(
        self,
        path: str,
        form_data: "list[tuple[str, str]]",
    ) -> Any:
        """Envía un POST form-urlencoded y devuelve el JSON de respuesta parseado.

        A diferencia de _post_form(), acepta una lista de tuplas para
        permitir claves repetidas (ej. tags, csrf_token enviado varias veces).
        La URL puede ser un path relativo ("/extrajudiciales/...") o una
        URL completa ("https://tnm.sudespacho.net/..."); en el segundo caso
        se extrae el path automáticamente.

        Args:
            path: Path relativo o URL completa del endpoint.
            form_data: Lista de tuplas (campo, valor).

        Returns:
            dict con el JSON de respuesta.

        Raises:
            SudespachoLegacyError: si hay error HTTP o la sesión expiró.
        """
        # Normalizar: si es URL completa extraer solo el path
        if path.startswith("http://") or path.startswith("https://"):
            parsed = urllib.parse.urlparse(path)
            path = parsed.path
            if parsed.query:
                path = f"{path}?{parsed.query}"

        r = self._post_form(path, form_data)
        if r.status_code >= 400:
            raise SudespachoLegacyError(
                f"POST {path} → HTTP {r.status_code}: {r.text[:400]}"
            )
        return self._parse_json_loose(r)

    def healthcheck(self) -> bool:
        """Valida que la cookie de sesión es válida obteniendo el CSRF."""
        try:
            self._get_csrf_token()
            return True
        except SudespachoLegacyError:
            return False

    # ---- Listado paginado de expedientes (para bulk pull) ---------------

    @staticmethod
    def _strip_html(html: str) -> str:
        """Elimina tags HTML y colapsa whitespace. Para parsear celdas."""
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"&nbsp;", " ", text)
        text = re.sub(r"&amp;", "&", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def _parse_row(element: str, exp_id: str, body_html: str) -> ExpedienteListEntry:
        """Parsea una fila del listado. La estructura varía levemente entre
        rows (la columna 'Posición procesal' a veces está vacía). Extraemos
        celdas <td> y mapeamos heurísticamente.
        """
        # Extraer todas las celdas <td>
        cells = []
        for m in re.finditer(r"<td[^>]*>(.*?)</td>", body_html, re.DOTALL):
            cells.append(SudespachoLegacyClient._strip_html(m.group(1)))

        # Las primeras 2-3 celdas son iconos/checkboxes; las útiles empiezan
        # con la fecha. Buscamos por patrón.
        text_cells = [c for c in cells if c]  # ignora cells vacías

        fecha_alta = None
        posicion = None
        num_exp = None
        serie = None
        referencia = None
        cliente = None
        contraparte = None

        # Localizar fecha (primer dd-mm-yyyy)
        date_re = re.compile(r"\b\d{2}-\d{2}-\d{4}\b")
        for c in text_cells:
            m = date_re.search(c)
            if m:
                fecha_alta = m.group(0)
                break

        # Posición procesal: alguna celda dice exactamente Actor o Demandado
        for c in text_cells:
            if c.strip() in ("Actor", "Demandado", "Demandante"):
                posicion = c.strip()
                break

        # Num expediente y serie: dos celdas numéricas pequeñas adyacentes
        # Suelen ser la 4ª y 5ª celda no vacía
        nums = [c for c in text_cells if re.fullmatch(r"\d{1,5}", c)]
        if len(nums) >= 2:
            num_exp, serie = nums[0], nums[1]

        # Cliente: primera celda con marcador societario (S.L./S.A./S.L.U./S.L.P.).
        # Contraparte: la siguiente celda no trivial tras la del cliente,
        # sea sociedad o persona física. Esto refleja el orden de columnas
        # del listado: ... | Referencia | Cliente | Contraparte | Tags.
        empresa_re = re.compile(r"\b(?:S\.L\.U\.|S\.L\.|S\.A\.|S\.L\.P\.)\b")
        cliente_idx = -1
        for i, c in enumerate(text_cells):
            if empresa_re.search(c):
                cliente = c
                cliente_idx = i
                break
        if cliente_idx >= 0:
            for c in text_cells[cliente_idx + 1:]:
                stripped = c.strip()
                if len(stripped) < 3:
                    continue
                if re.fullmatch(r"\d{1,5}", stripped):
                    continue
                if re.fullmatch(r"\d{2}-\d{2}-\d{4}", stripped):
                    continue
                if stripped in ("Actor", "Demandado", "Demandante"):
                    continue
                # Personas físicas en MAYÚSCULAS, sociedades, o cualquier
                # texto largo que no parezca una etiqueta de tag (≥ 5 chars
                # y con espacios/coma).
                if (stripped.isupper()
                        or empresa_re.search(stripped)
                        or ("," in stripped and len(stripped) >= 5)
                        or (" " in stripped and len(stripped) >= 8)):
                    contraparte = stripped
                    break

        # Referencia (patrón común "BaRR3 - ... - BD" o similar)
        for c in text_cells:
            if re.search(r"^[A-Z][a-z]+\d+\s*-\s*", c) or re.search(r"\(W-[A-Z0-9]+\)", c):
                referencia = c
                break

        raw = " | ".join(text_cells[:10])
        return ExpedienteListEntry(
            expediente_id=exp_id,
            element=element,
            fecha_alta=fecha_alta,
            posicion_procesal=posicion,
            num_expediente=num_exp,
            serie_expediente=serie,
            referencia_cliente=referencia,
            cliente=cliente,
            contraparte=contraparte,
            raw_text=raw,
        )

    def _build_list_body(self, page: int, num_results: int = 50) -> str:
        """Construye el form-encoded body mínimo para el listado.

        Inspeccionado contra el JS `get_datos_where`: la mayoría de campos
        pueden ir vacíos. Mantenemos los esenciales (page, csrf, ajax,
        orden, numeroresultados, pestana_listado).
        """
        csrf = self._get_csrf_token()
        params = [
            ("ubicacion", ""),
            ("cadBusqueda", ""),
            ("ajax", "true"),
            ("page", str(page)),
            ("orden_campo", "fecha_alta"),
            ("orden_sentido", "desc"),
            ("pestana_listado", "despacho--1"),
            ("id_carpeta", ""),
            ("id_carpeta_imap", ""),
            ("fechable", ""),
            ("numeroresultados", str(num_results)),
            ("busquedaListadoDashboard", ""),
            ("carpeta", ""),
            ("carpeta_imap", "cuenta_0"),
            ("idlistado", ""),
            ("imprimir", ""),
            ("existeform", "true"),
            ("listar_usuarios_online", ""),
            ("calendario_vista", ""),
            ("calendario_fecha", ""),
            ("edicionmultiple", ""),
            ("accesoempresa", ""),
            ("profesional_imputacion", ""),
            ("fecha_desde_imputacion", ""),
            ("fecha_hasta_imputacion", ""),
            ("varios_alta_masiva", ""),
            ("calendario_eventos_usuario", ""),
            ("tlfvirtual", ""),
            ("csrf_token", csrf),
        ]
        return urllib.parse.urlencode(params)

    def list_expedientes_page(
        self,
        page: int,
        *,
        element: str = "expedientes_judiciales",
        element_url: str | None = None,
        num_results: int = 50,
    ) -> tuple[list[ExpedienteListEntry], int]:
        """Devuelve (entries, last_page) de una página del listado.

        `element_url` es el segmento de URL del frontal; si no se indica
        se asume que coincide con `element` quitando el guión bajo
        (`expedientes_judiciales` → `expedientesjudiciales`).
        """
        url_seg = element_url or element.replace("_", "")
        path = f"/{url_seg}/list/elemento/{element}"
        body = self._build_list_body(page, num_results=num_results)

        try:
            r = self._client.post(
                path,
                content=body,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "X-Requested-With": "XMLHttpRequest",
                    "Accept": "application/json",
                },
            )
        except httpx.HTTPError as exc:
            raise SudespachoLegacyError(f"POST {path} falló: {exc}") from exc
        self._check_session(r, path)
        if r.status_code >= 400:
            raise SudespachoLegacyError(
                f"POST {path} → HTTP {r.status_code}: {r.text[:300]}"
            )

        try:
            payload = json.loads(r.text)
        except json.JSONDecodeError as exc:
            raise SudespachoLegacyError(
                f"Listado no devolvió JSON. Inicio: {r.text[:200]}"
            ) from exc
        if not payload.get("resultado"):
            raise SudespachoLegacyError(
                f"Listado rechazado: {payload!r}"
            )
        info_html = payload.get("info", "")

        # Parsear filas
        entries: list[ExpedienteListEntry] = []
        seen_ids: set[str] = set()
        for m in _EXP_ROW_RE.finditer(info_html):
            elem = m.group("element")
            if elem != element:
                continue
            exp_id = m.group("id")
            if exp_id in seen_ids:
                continue
            seen_ids.add(exp_id)
            entries.append(self._parse_row(elem, exp_id, m.group("body")))

        # Última página: buscar el mayor N en pagina(N, ...)
        last_page = max(
            (int(m.group(1)) for m in _LAST_PAGE_RE.finditer(info_html)),
            default=page,
        )

        return entries, last_page

    def iter_all_expedientes(
        self,
        *,
        element: str = "expedientes_judiciales",
        element_url: str | None = None,
        num_results: int = 50,
        cliente_filter: str | None = None,
        max_pages: int | None = None,
    ) -> "Iterator[ExpedienteListEntry]":
        """Itera todos los expedientes paginando.

        `cliente_filter`: si se pasa, solo emite expedientes cuyo campo
        `cliente` contenga ese substring (case-insensitive). Útil para
        filtrar por "EV MMC SPAIN, S.L.U." sin tener que conocer el ID
        interno del cliente en el CRM.
        """
        page = 1
        last_page = 1
        match_lower = (cliente_filter or "").strip().lower()
        while True:
            if max_pages is not None and page > max_pages:
                break
            entries, last_page = self.list_expedientes_page(
                page, element=element, element_url=element_url,
                num_results=num_results,
            )
            for e in entries:
                if match_lower:
                    cli_text = (e.cliente or "").lower()
                    if match_lower not in cli_text:
                        continue
                yield e
            if page >= last_page:
                break
            page += 1

    def list_doc_ids(
        self,
        expediente_id: str | int,
        *,
        element: str = "expedientes_judiciales",
    ) -> list[str]:
        """Devuelve los IDs de documentos del Gestor Documental del expediente.

        Hace POST al endpoint de listado y extrae por regex los `data-id`
        de cada fila (`id="fila_gdocu_<doc_id>"`).
        """
        # Asegura que tenemos CSRF (el endpoint a veces lo requiere)
        self._get_csrf_token()
        path = ENDPOINTS["gdocu_list"].format(element=element, id=expediente_id)
        # El frontal acepta este POST sin body o con body vacío; dejamos vacío
        r = self._post_form(path, {})
        if r.status_code >= 400:
            raise SudespachoLegacyError(
                f"POST {path} → HTTP {r.status_code}: {r.text[:300]}"
            )
        ids = sorted(set(_ROW_ID_RE.findall(r.text)))
        return ids

    def get_download_url(
        self,
        doc_id: str | int,
        expediente_id: str | int,
        *,
        element: str = "expedientes_judiciales",
    ) -> tuple[str, str]:
        """Resuelve la URL S3 prefirmada del documento. Devuelve (metodo, url).

        Si la pre-descarga indica método != 's3', usa el fallback legacy
        (descargafichero) y devuelve ('legacy', None) para que el caller
        haga GET directo a ese endpoint del frontal.
        """
        csrf = self._get_csrf_token()

        # 1) Predownload: averigua el método
        path1 = ENDPOINTS["predownload"].format(element=element, id=expediente_id)
        r1 = self._post_form(path1, {"csrf_token": csrf, "id": str(doc_id)})
        if r1.status_code >= 400:
            raise SudespachoLegacyError(
                f"predownload → HTTP {r1.status_code}: {r1.text[:300]}"
            )
        data1 = self._parse_json_loose(r1)
        if not data1.get("resultado"):
            raise SudespachoLegacyError(
                f"predownload doc {doc_id}: rechazado. info: {data1.get('info')!r}"
            )
        metodo = data1.get("metodo", "")

        if metodo == "s3":
            path2 = ENDPOINTS["download_s3"].format(
                doc_id=doc_id, element=element, id=expediente_id,
            )
            r2 = self._post_form(path2, {"csrf_token": csrf})
            if r2.status_code >= 400:
                raise SudespachoLegacyError(
                    f"download_s3 → HTTP {r2.status_code}: {r2.text[:300]}"
                )
            data2 = self._parse_json_loose(r2)
            if not data2.get("resultado") or not data2.get("url"):
                raise SudespachoLegacyError(
                    f"download_s3 doc {doc_id}: sin URL. payload: {data2}"
                )
            return ("s3", str(data2["url"]))

        # Otros métodos: 'cloud' (URL ya en data1.url) o 's3old' / fallback.
        if metodo == "cloud" and data1.get("url"):
            return ("cloud", str(data1["url"]))

        # Fallback: descarga directa del frontal heredado (stream PHP).
        return ("legacy", "")

    def download_document(
        self,
        doc_id: str | int,
        expediente_id: str | int,
        target_path: Path,
        *,
        element: str = "expedientes_judiciales",
    ) -> LegacyDownloadResult:
        """Descarga un documento al `target_path`. Crea directorios padre si
        no existen. Si el método es 's3' o 'cloud' descarga la URL prefirmada
        sin auth; si es 'legacy' hace GET con cookie de sesión al endpoint
        descargafichero.
        """
        target_path.parent.mkdir(parents=True, exist_ok=True)
        method, url = self.get_download_url(doc_id, expediente_id, element=element)

        filename_in_disposition: str | None = None

        if method in ("s3", "cloud"):
            # GET externo sin auth (presigned o cloud público)
            try:
                with httpx.Client(timeout=self.cfg.timeout_s, follow_redirects=True) as ext:
                    r = ext.get(url)
                    r.raise_for_status()
                    data = r.content
                    cd = r.headers.get("content-disposition") or ""
                    filename_in_disposition = _extract_filename(cd)
            except httpx.HTTPError as exc:
                raise SudespachoLegacyError(
                    f"Descarga externa doc {doc_id} falló: {exc}"
                ) from exc
        else:
            # Fallback legacy: requiere la cookie de sesión
            path = ENDPOINTS["download_legacy"].format(doc_id=doc_id)
            try:
                r = self._client.get(path, follow_redirects=True)
                self._check_session(r, path)
                r.raise_for_status()
                data = r.content
                cd = r.headers.get("content-disposition") or ""
                filename_in_disposition = _extract_filename(cd)
            except httpx.HTTPError as exc:
                raise SudespachoLegacyError(
                    f"Descarga legacy doc {doc_id} falló: {exc}"
                ) from exc

        target_path.write_bytes(data)
        return LegacyDownloadResult(
            doc_id=str(doc_id),
            target_path=target_path,
            bytes_written=len(data),
            filename_in_disposition=filename_in_disposition,
            method=method,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FILENAME_RE = re.compile(
    r'filename\*?\s*=\s*(?:UTF-8\'\')?"?([^";]+)"?',
    re.IGNORECASE,
)


def _extract_filename(content_disposition: str) -> str | None:
    """Extrae filename de un header Content-Disposition.

    Maneja:
        - filename="foo.pdf"
        - filename=foo.pdf
        - filename*=UTF-8''foo%20bar.pdf  (RFC 5987)
    """
    if not content_disposition:
        return None
    m = _FILENAME_RE.search(content_disposition)
    if not m:
        return None
    name = m.group(1).strip().strip('"')
    # URL-decode si venía codificado (RFC 5987)
    try:
        name = urllib.parse.unquote(name)
    except Exception:
        pass
    return name or None
