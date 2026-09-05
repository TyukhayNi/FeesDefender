"""Backend de sincronización contra la API de sudespacho.net.

Descarga los documentos del Gestor Documental (Gdocu) de un expediente al
`00_INPUT/` del caso local. Documentado contra el OpenAPI oficial publicado
en developers.sudespacho.net y en el host del tenant
(`/api/docs.json`).

Configuración (en `.env`):

    SUDESPACHO_BASE_URL=https://api-crm-commons-pro.sudespacho.biz
    SUDESPACHO_API_KEY=<api_key>
    SUDESPACHO_AUTH_HEADER=x-api-key           # NO Authorization (reservado a JWT de sesión web)
    SUDESPACHO_AUTH_SCHEME=                    # vacío: el valor del header es la propia key
    SUDESPACHO_ELEMENT=expedientes_judiciales  # también: expedientes_extrajudiciales
    SUDESPACHO_TIMEOUT_S=120

Modelo de la API
----------------
La API sudespacho.net no expone un endpoint dedicado tipo
`/expedientes/{id}/documentos`. El expediente se direcciona a través del
sistema genérico de "elementos":

    GET  /api/element_register/{element}/{id}?properties[]=…

donde `{element}` es el slug del tipo (`expedientes_judiciales`,
`expedientes_extrajudiciales`, `clientes_propios`, etc.).

Los documentos viven en el módulo Gdocu (Gestor Documental). Para
obtenerlos hay dos rutas:

1. **Zip masivo (recomendado):** se localiza la carpeta raíz Gdocu del
   expediente vía `/api/folders/gdocu/0?related_element=…&related_member=…`
   y se solicita el zip con `/api/documents/{folder_id}/zip/files`.
   Ese endpoint devuelve un `Documents` (campo `doc` con URL prefirmada) o
   directamente binario, según implementación. Ambos casos se manejan.

2. **Por documento individual (fallback):** se filtran documentos vía
   `GET /api/documents` (filterGroup) por `relatedRegisters` o `id_carpeta`,
   y se descarga cada uno con
   `GET /api/documents/presigned_urls/s3/download/{documentId}` o
   `GET /api/documents/{id}/downloadUri`.

Autenticación: API key en header `x-api-key`, sin esquema (el valor del
header es la clave literal). El header `Authorization` está reservado al
flujo JWT de sesión web del CRM y rechaza tokens de API key. Confirmado
empíricamente contra el tenant commons-pro el 2026-04-25 (ver docs/DEAD_ENDS.md).
El OpenAPI declara `Authorization`, pero ese declarativo
corresponde a la auth de sesión web, no a la API key.
"""

from __future__ import annotations

import io
import json
import os
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

import httpx

from .case_manager import (
    crm_branch_path,
    guard_escritura,
    is_legacy_intake_v1,
    read_bucket_overrides,
    update_pull_state,
)
from .config import CRM_SUBDIR, PENDIENTE_CHECKIN_SUBDIR, caso_path
from .intake_log import append_event as _log_event
from .intake_manifest import (
    IntakeManifest,
    compute_sha256,
    compute_sha256_bytes,
)
from .ocurrencias_crm import RegistroOcurrencias
from .utils import now_iso, slugify


class SudespachoError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

def _env(name: str, default: str | None = None) -> str | None:
    v = os.getenv(name, default)
    return v.strip() if isinstance(v, str) else v


@dataclass(frozen=True)
class SudespachoConfig:
    base_url: str
    api_key: str
    auth_header: str = "x-api-key"   # NO Authorization (es para JWT web)
    auth_scheme: str = ""            # vacío: API key como valor literal
    element: str = "expedientes_judiciales"
    timeout_s: int = 120

    @classmethod
    def from_env(cls) -> "SudespachoConfig":
        base = _env("SUDESPACHO_BASE_URL")
        key = _env("SUDESPACHO_API_KEY")
        if not base or not key:
            raise SudespachoError(
                "Faltan SUDESPACHO_BASE_URL o SUDESPACHO_API_KEY en .env. "
                "Obtén tu API key en sudespacho.net → Ajustes → API."
            )
        return cls(
            base_url=base.rstrip("/"),
            api_key=key,
            auth_header=_env("SUDESPACHO_AUTH_HEADER", "x-api-key") or "x-api-key",
            auth_scheme=_env("SUDESPACHO_AUTH_SCHEME", "") or "",
            element=_env("SUDESPACHO_ELEMENT", "expedientes_judiciales") or "expedientes_judiciales",
            timeout_s=int(_env("SUDESPACHO_TIMEOUT_S", "120") or "120"),
        )

    def headers(self) -> dict[str, str]:
        if self.auth_scheme:
            value = f"{self.auth_scheme} {self.api_key}"
        else:
            value = self.api_key
        return {
            self.auth_header: value,
            "Accept": "application/json, application/ld+json",
        }


# ---------------------------------------------------------------------------
# Endpoints (centralizados para revisión rápida)
# ---------------------------------------------------------------------------

ENDPOINTS = {
    # Health / sesión
    "online_current":      "/api/online/current",                # 204 si autenticado

    # Lectura del propio expediente como "elemento"
    "element_register":    "/api/element_register/{element}/{id}",

    # Listados generales con filterGroup (fallback de exploración)
    "documents_list":      "/api/documents",
    "document_item":       "/api/documents/{id}",

    # Gestor Documental (Gdocu)
    "folders":             "/api/folders/{element}/{parent}",    # element=gdocu, parent=0
    "documents_zip":       "/api/documents/{id}/zip/files",      # id = folder Gdocu

    # Descarga individual (alternativas legacy)
    "document_download_uri": "/api/documents/{id}/downloadUri",
    "presigned_download":    "/api/documents/presigned_urls/{service}/download/{documentId}",

    # ---- Nuevos endpoints REST (confirmados 2026-05-04, sin PHPSESSID) ----
    # Listado de documentos Gdocu de un expediente vía element_registries
    # Filtro: filterGroup associated + property=left.{element}.id
    "element_registries":    "/api/element_registries/{element}",

    # URL S3 prefirmada para descarga de un documento (TTL 600s)
    # Params: relatedElement, relatedId, direction=left
    "presigned_download_url": "/api/files/presigned_download_url/{doc_id}",
}

# Mapping de campos en la respuesta de Documents.
DOC_FIELDS = {
    "id":              "id",
    "filename":        "nombreoriginal",     # también: nombrefinal
    "filename_final":  "nombrefinal",
    "mime":            "mime",
    "size":            "tamano",
    "modified_at":     "fechamodificacion",
    "created_at":      "fechapublicacion",
    "category":        "categoria",
    "url":             "doc",                # URL prefirmada cuando aplica
    "id_folder":       "id_carpeta",
    "related":         "relatedRegisters",
    "type":            "tipo",
    "subject":         "asunto",
}

# Mapa MIME → extensión para documentos del CRM cuyo nombre no la trae
# (frecuente: los escritos suben sin extensión, p. ej. "ESCRITO CONTESTACION
# CRIO"). Sin esto el pull los guardaba como `.bin`, ilegibles para el pipeline.
_MIME_EXT: dict[str, str] = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/msword": ".doc",
    "application/rtf": ".rtf",
    "text/rtf": ".rtf",
    "application/vnd.oasis.opendocument.text": ".odt",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/tiff": ".tiff",
    "text/plain": ".txt",
    "message/rfc822": ".eml",
}


def _ext_from_mime(mime: str | None) -> str:
    """Extensión de archivo a partir del MIME. Fallback `.bin` si se desconoce."""
    if not mime:
        return ".bin"
    m = mime.split(";")[0].strip().lower()
    if m in _MIME_EXT:
        return _MIME_EXT[m]
    import mimetypes
    return mimetypes.guess_extension(m) or ".bin"


# Una extensión "real" es un punto seguido de 1-8 caracteres alfanuméricos.
# Cualquier otra cosa que `Path.suffix` capture (espacios, ':', nombres largos)
# es basura de un nombre del CRM sin extensión verdadera.
_VALID_EXT_RE = re.compile(r"^\.[A-Za-z0-9]{1,8}$")


def _safe_stem_ext(original: str, mime: str | None, doc_id: str) -> tuple[str, str]:
    """Deriva un ``(stem, ext)`` seguros para el sistema de ficheros de Windows.

    El nombre que llega del CRM puede no tener extensión real pero sí puntos
    intermedios (p. ej. ``dior_12_11.2024 09:30  NEUS GASCON``): en ese caso
    ``Path.suffix`` captura basura con caracteres ilegales en Windows
    (``\\ / : * ? " < > |``) que reventarían ``write_bytes`` con
    ``FileNotFoundError``. Solo se respeta la extensión del original si parece
    una extensión de verdad; en caso contrario el **nombre completo** se
    slugifica (preservando fechas/nombres) y la extensión se deriva del MIME.
    """
    p = Path(original)
    if _VALID_EXT_RE.match(p.suffix):
        stem = slugify(p.stem) or f"doc_{doc_id}"
        ext = p.suffix.lower()
    else:
        stem = slugify(p.name) or f"doc_{doc_id}"
        ext = _ext_from_mime(mime)
    return stem, ext


# Propiedades mínimas a solicitar al leer un expediente como elemento.
EXPEDIENTE_DEFAULT_PROPERTIES: tuple[str, ...] = (
    "id", "referencia", "asunto", "estado",
    "cliente", "contraparte",
    "fecha_apertura", "fecha_cierre",
    "importe_reclamado",
)


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------

@dataclass
class ExpedienteInfo:
    expediente_id: str
    element: str
    raw: dict[str, Any]

    @property
    def referencia(self) -> str | None:
        return self.raw.get("referencia") or self.raw.get("ref")

    @property
    def titulo(self) -> str | None:
        return self.raw.get("asunto") or self.raw.get("titulo")


@dataclass
class FolderInfo:
    folder_id: str
    name: str | None
    raw: dict[str, Any]


@dataclass
class DocumentInfo:
    doc_id: str
    filename: str
    mime: str | None
    size: int | None
    modified_at: str | None
    raw: dict[str, Any]


@dataclass
class GdocuDocInfo:
    """Documento del Gestor Documental obtenido vía API REST (element_registries/gdocu).

    A diferencia de DocumentInfo (que viene de /api/documents), este DTO
    se construye desde /api/element_registries/gdocu — confirmado 2026-05-04.

    Campos:
        doc_id          ID numérico del documento (str).
        filename        Nombre final del archivo (campo nombrefinal del CRM).
        id_carpeta      ID numérico de la carpeta Gdocu (str o None).
        id_carpeta_label  Etiqueta legible de la carpeta (ej. "CIVIL") o None.
        mime            MIME type o None.
        size            Tamaño en bytes o None.
        raw             Dict original devuelto por la API (para debug).
        modified_at     Fecha de modificación en el CRM (campo
                        ``fechamodificacion``, ISO-8601 con offset, ej.
                        ``2026-06-08T16:21:33.000+02:00``) o None. Requisito
                        de D9 (detector de conjunto): permite clusterizar los
                        documentos subidos en lote por timestamp idéntico.
    """
    doc_id: str
    filename: str
    id_carpeta: str | None
    id_carpeta_label: str | None
    mime: str | None
    size: int | None
    raw: dict[str, Any]
    modified_at: str | None = None


# ---------------------------------------------------------------------------
# Cliente
# ---------------------------------------------------------------------------

class SudespachoClient:
    def __init__(self, cfg: SudespachoConfig | None = None) -> None:
        self.cfg = cfg or SudespachoConfig.from_env()
        self._client = httpx.Client(
            base_url=self.cfg.base_url,
            timeout=self.cfg.timeout_s,
            headers=self.cfg.headers(),
            follow_redirects=True,
        )

    def __enter__(self) -> "SudespachoClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self._client.close()

    # --- helpers HTTP -----------------------------------------------------

    def _get(self, path: str, **params: Any) -> httpx.Response:
        try:
            r = self._client.get(path, params=params)
        except httpx.HTTPError as exc:
            raise SudespachoError(f"GET {path} falló: {exc}") from exc
        if r.status_code == 401:
            raise SudespachoError(
                f"Credencial rechazada (401) en {path}. Revisa SUDESPACHO_API_KEY."
            )
        return r

    def _get_json(self, path: str, **params: Any) -> Any:
        r = self._get(path, **params)
        if r.status_code == 204:
            return None
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise SudespachoError(
                f"GET {path} → HTTP {exc.response.status_code}: {exc.response.text[:300]}"
            ) from exc
        if not r.content:
            return None
        try:
            return r.json()
        except json.JSONDecodeError as exc:
            raise SudespachoError(
                f"GET {path} no devolvió JSON válido: {exc}"
            ) from exc

    @staticmethod
    def _items(payload: Any) -> list[dict]:
        """Extrae una colección de respuestas REST/Hydra heterogéneas."""
        if isinstance(payload, list):
            return [x for x in payload if isinstance(x, dict)]
        if isinstance(payload, dict):
            for k in ("hydra:member", "member", "data", "items", "results"):
                v = payload.get(k)
                if isinstance(v, list):
                    return [x for x in v if isinstance(x, dict)]
        return []

    # --- API pública ------------------------------------------------------

    def healthcheck(self) -> bool:
        """Valida credenciales contra `/api/documents?itemsPerPage=1`.

        La API key autentica pero `/api/online/current` está reservado al
        flujo de sesión web (devuelve 404 hydra:Error con API key incluso
        siendo válida). En su lugar pegamos contra `documents` con un
        itemsPerPage=1 para minimizar coste: cualquier respuesta distinta
        de 401/403 confirma que la credencial es buena.
        """
        try:
            r = self._client.get(
                ENDPOINTS["documents_list"],
                params={"itemsPerPage": 1, "page": 1},
            )
        except httpx.HTTPError:
            return False
        return r.status_code not in (401, 403)

    # ---- Expediente como elemento ---------------------------------------

    def get_expediente(
        self,
        expediente_id: str,
        *,
        element: str | None = None,
        properties: tuple[str, ...] | list[str] | None = None,
    ) -> ExpedienteInfo:
        """Lee un expediente desde /api/element_register/{element}/{id}.

        `properties[]` es obligatorio en la API; si no se pasa, se usa el
        set por defecto (`EXPEDIENTE_DEFAULT_PROPERTIES`). Para descubrir
        el catálogo real de propiedades del tenant ver
        `/api/view/config/{element}/fields`.
        """
        elem = element or self.cfg.element
        props = list(properties or EXPEDIENTE_DEFAULT_PROPERTIES)
        path = ENDPOINTS["element_register"].format(element=elem, id=expediente_id)
        # httpx serializa params={"properties[]": [...]} como repeat → properties[]=a&properties[]=b
        payload = self._get_json(path, **{"properties[]": props})
        if not isinstance(payload, dict):
            raise SudespachoError(
                f"Respuesta inesperada en {path}: tipo {type(payload).__name__}"
            )
        return ExpedienteInfo(expediente_id=str(expediente_id), element=elem, raw=payload)

    # ---- Documentos individuales: metadatos vía API nueva --------------

    def get_document_metadata(
        self,
        doc_id: str | int,
    ) -> dict[str, Any]:
        """Devuelve metadatos del documento (id_carpeta + label, categoria, etc.).

        Llama `GET /api/documents/{id}`. La API nueva responde con un shape
        custom: `{id, isPrimary, values: [{property: {name}, value, label?}]}`.
        Esta función aplana ese shape a un dict simple:

            {
                'id': '40020',
                'id_carpeta': '306',
                'id_carpeta_label': 'CIVIL',
                'nombreoriginal': 'CEDULA DE EMPLAZAMIENTO...',
                'categoria': 'CIVIL',
                ...
            }

        Si el documento no existe o la API responde con shape inesperado,
        devuelve un dict mínimo con `{'id': str(doc_id)}` para que el
        caller pueda hacer fallback.
        """
        path = ENDPOINTS["document_item"].format(id=doc_id)
        try:
            payload = self._get_json(path)
        except SudespachoError:
            return {"id": str(doc_id)}

        if not isinstance(payload, dict):
            return {"id": str(doc_id)}

        out: dict[str, Any] = {"id": str(payload.get("id", doc_id))}

        # Shape custom: {id, values: [{property: {name}, value, label?}, ...]}
        values = payload.get("values")
        if isinstance(values, list):
            for v in values:
                if not isinstance(v, dict):
                    continue
                name = (v.get("property") or {}).get("name") or v.get("name")
                if not name:
                    continue
                out[name] = v.get("value")
                if v.get("label"):
                    out[f"{name}_label"] = v.get("label")
        else:
            # Shape plano (fallback): claves directas
            for k in (
                "nombreoriginal", "nombrefinal", "id_carpeta",
                "categoria", "subcategoria", "mime", "tamano",
                "fechamodificacion", "fechapublicacion", "tipo",
            ):
                if k in payload:
                    out[k] = payload[k]
        return out

    # ---- Gdocu: localizar carpetas del expediente -----------------------

    def list_gdocu_folders(
        self,
        expediente_id: str,
        *,
        element: str | None = None,
        parent: str | int = 0,
    ) -> list[FolderInfo]:
        """Lista carpetas Gdocu vinculadas al expediente.

        Llama a `/api/folders/gdocu/{parent}?related_element={element}&related_member={id}`.
        Por defecto pide las del nivel raíz (`parent=0`).
        """
        elem = element or self.cfg.element
        path = ENDPOINTS["folders"].format(element="gdocu", parent=parent)
        payload = self._get_json(
            path,
            related_element=elem,
            related_member=str(expediente_id),
        )
        out: list[FolderInfo] = []
        for it in self._items(payload):
            fid = it.get("id") or it.get("@id")
            if isinstance(fid, str) and "/" in fid:  # caso Hydra IRI
                fid = fid.rsplit("/", 1)[-1]
            if fid is None:
                continue
            out.append(FolderInfo(
                folder_id=str(fid),
                name=it.get("nombre") or it.get("name"),
                raw=it,
            ))
        return out

    # ---- Gdocu: descarga zip masivo -------------------------------------

    def download_zip(self, folder_id: str, target_dir: Path) -> Path:
        """Descarga el zip de todos los archivos de una carpeta Gdocu y lo
        extrae en `target_dir`. Devuelve la ruta de la carpeta.

        El endpoint `/api/documents/{id}/zip/files` devuelve, según
        implementación: (a) binario zip directo, o (b) un objeto Documents
        cuyo campo `doc` contiene una URL prefirmada al zip. Manejamos
        ambos casos.
        """
        target_dir.mkdir(parents=True, exist_ok=True)
        path = ENDPOINTS["documents_zip"].format(id=folder_id)
        r = self._get(path)
        if r.status_code == 401:
            raise SudespachoError(f"401 en {path}. Credencial rechazada.")
        if r.status_code == 404:
            raise SudespachoError(
                f"Carpeta {folder_id} no encontrada (404) en {path}."
            )
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise SudespachoError(
                f"GET {path} → HTTP {exc.response.status_code}: "
                f"{exc.response.text[:300]}"
            ) from exc

        ctype = (r.headers.get("content-type") or "").lower()
        zip_bytes: bytes
        if "application/zip" in ctype or "octet-stream" in ctype:
            zip_bytes = r.content
        else:
            # Asumimos JSON/Documents con URL en `doc`
            try:
                payload = r.json()
            except json.JSONDecodeError as exc:
                raise SudespachoError(
                    f"Respuesta inesperada en {path}: ni zip ni JSON."
                ) from exc
            url = self._extract_url_from_doc(payload)
            if not url:
                raise SudespachoError(
                    f"GET {path} devolvió JSON sin URL descargable. Payload: "
                    f"{json.dumps(payload, ensure_ascii=False)[:300]}"
                )
            zip_bytes = self._download_url_raw(url)

        # Extraer en target_dir
        return self._extract_zip(zip_bytes, target_dir)

    @staticmethod
    def _extract_url_from_doc(payload: Any) -> str | None:
        if not isinstance(payload, dict):
            return None
        # Documents schema: campo `doc`. `downloadUri` usa `presignedDownloadUrl`.
        for key in (
            DOC_FIELDS["url"], "url",
            "presignedDownloadUrl", "presignedUrl", "presigned_url",
            "downloadUrl", "fileUrl",
        ):
            v = payload.get(key)
            if isinstance(v, str) and v.startswith(("http://", "https://")):
                return v
        return None

    def _download_url_raw(self, url: str) -> bytes:
        """Descarga una URL externa (típicamente S3 prefirmada) sin auth."""
        try:
            with httpx.Client(timeout=self.cfg.timeout_s, follow_redirects=True) as ext:
                r = ext.get(url)
                r.raise_for_status()
                return r.content
        except httpx.HTTPError as exc:
            raise SudespachoError(f"Descarga externa falló ({url[:80]}…): {exc}") from exc

    @staticmethod
    def _extract_zip(zip_bytes: bytes, target_dir: Path) -> Path:
        """Extrae un zip en `target_dir` aplanando subcarpetas a un único
        nivel y normalizando nombres con slugify para evitar colisiones de
        sistema de archivos.
        """
        try:
            zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
        except zipfile.BadZipFile as exc:
            # Fallback: guardar el binario tal cual para inspección
            dump = target_dir / "_descarga_bruta.bin"
            dump.write_bytes(zip_bytes)
            raise SudespachoError(
                f"La respuesta no es un ZIP válido: {exc}. Volcado en {dump}."
            ) from exc

        for info in zf.infolist():
            if info.is_dir():
                continue
            stem, ext = _safe_stem_ext(info.filename, None, "documento")
            target = target_dir / f"{stem}{ext}"
            i = 1
            while target.exists():
                target = target_dir / f"{stem}__{i}{ext}"
                i += 1
            with zf.open(info) as src, target.open("wb") as dst:
                dst.write(src.read())
        return target_dir

    # ---- Gdocu REST (sin PHPSESSID) — confirmados 2026-05-04 -----------

    def list_gdocu_docs_rest(
        self,
        expediente_id: str,
        *,
        element: str | None = None,
        items_per_page: int = 100,
    ) -> list[GdocuDocInfo]:
        """Lista los documentos del Gestor Documental de un expediente vía REST.

        Endpoint: GET /api/element_registries/gdocu
        Auth: solo x-api-key — SIN PHPSESSID. Confirmado 2026-05-04.

        Propiedades solicitadas (índices según nomenclatura del CRM):
            2  → nombrefinal  (nombre final del archivo)
            4  → mime
            9  → tamano       (tamaño en bytes)
            11 → id_carpeta   (carpeta Gdocu, con label si disponible)
            12 → fechamodificacion  (fecha de modificación en el CRM, D10)

        El índice del slot ``properties[N]`` es solo posición de array (el
        CRM lo resuelve por el NOMBRE de la propiedad, no por el número);
        ``fechamodificacion`` confirmada en vivo contra el 444
        (scripts/probe_gdocu_fecha.py).

        Args:
            expediente_id: ID del expediente en el CRM.
            element: Tipo de expediente (default: cfg.element).
            items_per_page: Número de resultados por página.

        Returns:
            Lista de GdocuDocInfo con filename, carpeta y metadatos.

        Raises:
            SudespachoError: si la llamada falla o la respuesta no es parseable.
        """
        elem = element or self.cfg.element

        base_params: dict[str, Any] = {
            "properties[2]":  "nombrefinal",
            "properties[4]":  "mime",
            "properties[9]":  "tamano",
            "properties[11]": "id_carpeta",
            "properties[12]": "fechamodificacion",
            "filterGroup[condition]":                                        "AND",
            "filterGroup[filterGroups][0][filters][0][operator]":            "associated",
            "filterGroup[filterGroups][0][filters][0][value]":               str(expediente_id),
            "filterGroup[filterGroups][0][filters][0][property]":            f"left.{elem}.id",
            "filterGroup[filterGroups][0][condition]":                       "AND",
            "itemsPerPage":   items_per_page,
            "return_totals":  "true",
        }

        path = ENDPOINTS["element_registries"].format(element="gdocu")
        results: list[GdocuDocInfo] = []
        page = 1

        while True:
            params = {**base_params, "page": page}
            payload = self._get_json(path, **params)
            members = self._items(payload)
            if not members:
                break

            for member in members:
                doc_id = str(member.get("id", "")).strip()
                if not doc_id:
                    continue

                # Aplanar array values → dict {nombre: {value, label?}}
                values_map: dict[str, dict[str, Any]] = {}
                for v in (member.get("values") or []):
                    if not isinstance(v, dict):
                        continue
                    prop_name = (v.get("property") or {}).get("name") or v.get("name")
                    if prop_name:
                        values_map[prop_name] = {
                            "value": v.get("value"),
                            "label": v.get("label"),
                        }

                filename = str(
                    values_map.get("nombrefinal", {}).get("value")
                    or f"doc_{doc_id}.bin"
                )
                id_carpeta_raw = values_map.get("id_carpeta", {}).get("value")
                id_carpeta = str(id_carpeta_raw) if id_carpeta_raw is not None else None
                id_carpeta_label = values_map.get("id_carpeta", {}).get("label") or None
                mime = values_map.get("mime", {}).get("value")
                size_raw = values_map.get("tamano", {}).get("value")
                try:
                    size: int | None = int(size_raw) if size_raw is not None else None
                except (ValueError, TypeError):
                    size = None
                modified_raw = values_map.get("fechamodificacion", {}).get("value")
                modified_at = str(modified_raw) if modified_raw else None

                results.append(GdocuDocInfo(
                    doc_id=doc_id,
                    filename=filename,
                    id_carpeta=id_carpeta,
                    id_carpeta_label=id_carpeta_label,
                    mime=mime,
                    size=size,
                    raw=member,
                    modified_at=modified_at,
                ))

            # Paginación: continuar si hay más páginas
            total = (
                int(payload.get("hydra:totalItems", 0))
                if isinstance(payload, dict) else 0
            )
            if len(results) >= total or len(members) < items_per_page:
                break
            page += 1

        return results

    def get_presigned_download_url(
        self,
        doc_id: str | int,
        expediente_id: str | int,
        *,
        element: str | None = None,
    ) -> str:
        """Obtiene la URL S3 prefirmada para descargar un documento vía REST.

        Endpoint: GET /api/documents/{id}/downloadUri
        Auth: solo x-api-key — SIN PHPSESSID. TTL de la URL S3: ~600 s;
        descargar inmediatamente.

        Historia (ver docs/DEAD_ENDS.md, `[CRITICO-PRESIGNED-DOWNLOAD-BUG]`):
        hasta 2026-05-04 la descarga se hacía vía
        ``/api/files/presigned_download_url/{doc_id}``. El backend del CRM
        redesplegó el módulo Upload (~2026-05-11) y ese endpoint —junto con
        ``/api/documents/presigned_urls/s3/download/{id}``— quedó roto
        server-side (400 "Unable to generate an IRI for ...DTO\\Download" /
        500 "controller not registered"). ``downloadUri`` sí sigue operativo
        y devuelve la URL S3 en el campo ``presignedDownloadUrl``. Confirmado
        empíricamente contra el expediente 649 el 2026-06-10
        (``scripts/diag_presigned_download.py``).

        Args:
            doc_id: ID del documento en el CRM.
            expediente_id: ID del expediente (se conserva por compatibilidad
                de firma con los call-sites; ``downloadUri`` solo necesita
                ``doc_id``).
            element: Tipo de expediente (idem; no usado por este endpoint).

        Returns:
            URL S3 prefirmada como string.

        Raises:
            SudespachoError: si la llamada falla o no se puede extraer la URL.
        """
        path = ENDPOINTS["document_download_uri"].format(id=doc_id)

        try:
            r = self._get(path)
            r.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise SudespachoError(
                f"downloadUri doc {doc_id} → HTTP {exc.response.status_code}: "
                f"{exc.response.text[:300]}"
            ) from exc

        # Respuesta esperada: JSON con `presignedDownloadUrl`. Conservamos
        # fallbacks (texto plano, otras claves) por robustez ante variaciones.
        try:
            payload = r.json()
        except Exception:
            payload = None

        if isinstance(payload, dict):
            url = self._extract_url_from_doc(payload)
            if url:
                return url
        if isinstance(payload, str) and payload.startswith("http"):
            return payload

        text = r.text.strip().strip('"')
        if text.startswith("http"):
            return text

        raise SudespachoError(
            f"downloadUri doc {doc_id}: no se pudo extraer URL S3. "
            f"Respuesta: {r.text[:300]}"
        )

    def download_document_rest(
        self,
        doc_id: str | int,
        expediente_id: str | int,
        target_path: Path,
        *,
        element: str | None = None,
    ) -> Path:
        """Descarga un documento al target_path usando el flujo REST (sin PHPSESSID).

        Pasos:
            1. GET /api/files/presigned_download_url/{doc_id} → URL S3 (TTL 600s)
            2. GET <S3_URL> (sin auth) → bytes → target_path

        Auth: solo x-api-key. Confirmado 2026-05-04.

        Args:
            doc_id: ID del documento.
            expediente_id: ID del expediente al que pertenece.
            target_path: Ruta de destino (los directorios padre se crean automáticamente).
            element: Tipo de expediente (default: cfg.element).

        Returns:
            target_path (ruta donde se escribió el archivo).

        Raises:
            SudespachoError: si no se puede obtener la URL o la descarga falla.
        """
        target_path.parent.mkdir(parents=True, exist_ok=True)
        url = self.get_presigned_download_url(doc_id, expediente_id, element=element)
        data = self._download_url_raw(url)
        target_path.write_bytes(data)
        return target_path

    # ---- Documentos: filtrado y descarga individual (legacy REST) --------

    def list_documents_by_expediente(
        self,
        expediente_id: str,
        *,
        element: str | None = None,
        properties: tuple[str, ...] | list[str] | None = None,
        items_per_page: int = 100,
    ) -> Iterator[DocumentInfo]:
        """Itera documentos vinculados al expediente vía filterGroup.

        Estrategia: filterGroup[filters][0][property]=relatedRegisters,
                    filterGroup[filters][0][operator]=associated,
                    filterGroup[filters][0][value][]=<element>:<id>:left
        """
        elem = element or self.cfg.element
        props = list(properties or (
            DOC_FIELDS["id"], DOC_FIELDS["filename"], DOC_FIELDS["filename_final"],
            DOC_FIELDS["mime"], DOC_FIELDS["size"], DOC_FIELDS["modified_at"],
            DOC_FIELDS["category"], DOC_FIELDS["id_folder"],
        ))

        page = 1
        related_token = f"{elem}:{expediente_id}:left"

        while True:
            params: dict[str, Any] = {
                "page": page,
                "itemsPerPage": items_per_page,
                "properties[]": props,
                "filterGroup[condition]": "AND",
                "filterGroup[filters][0][property]": "relatedRegisters",
                "filterGroup[filters][0][operator]": "associated",
                "filterGroup[filters][0][value][]": [related_token],
            }
            payload = self._get_json(ENDPOINTS["documents_list"], **params)
            items = self._items(payload)
            if not items:
                break
            for it in items:
                yield DocumentInfo(
                    doc_id=str(it.get(DOC_FIELDS["id"], "")),
                    filename=str(
                        it.get(DOC_FIELDS["filename"])
                        or it.get(DOC_FIELDS["filename_final"])
                        or "documento.bin"
                    ),
                    mime=it.get(DOC_FIELDS["mime"]),
                    size=it.get(DOC_FIELDS["size"]),
                    modified_at=it.get(DOC_FIELDS["modified_at"]),
                    raw=it,
                )
            if len(items) < items_per_page:
                break
            page += 1

    def download_document(self, doc_id: str, target_path: Path) -> Path:
        """Descarga un documento por id. Intenta primero presigned_urls/s3,
        luego /downloadUri. Devuelve la ruta del archivo escrito.
        """
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # 1) /api/documents/presigned_urls/s3/download/{documentId}
        path = ENDPOINTS["presigned_download"].format(service="s3", documentId=doc_id)
        url: str | None = None
        try:
            payload = self._get_json(path)
            if isinstance(payload, dict):
                url = payload.get("url") or self._extract_url_from_doc(payload)
        except SudespachoError:
            url = None

        # 2) Fallback: /api/documents/{id}/downloadUri (devuelve Documents con URL en `doc`)
        if not url:
            path2 = ENDPOINTS["document_download_uri"].format(id=doc_id)
            payload2 = self._get_json(path2)
            url = self._extract_url_from_doc(payload2)

        if not url:
            raise SudespachoError(
                f"No se pudo resolver URL de descarga del documento {doc_id}."
            )

        data = self._download_url_raw(url)
        target_path.write_bytes(data)
        return target_path


# ---------------------------------------------------------------------------
# Operación: pull de un expediente entero al 00_INPUT/ del caso
# ---------------------------------------------------------------------------

@dataclass
class PullResult:
    case_id: str
    expediente_id: str
    documents_total: int
    documents_downloaded: int
    bytes_downloaded: int
    target_dir: Path
    folders_processed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


_PULL_MARKER = ".pulled"


def _source_dir(expediente_id: str) -> str:
    """Nombre de la subcarpeta de ingesta para un expediente: sudespacho_{id}."""
    return f"sudespacho_{expediente_id}"


def pull_expediente(
    case_id: str,
    expediente_id: str,
    *,
    client: SudespachoClient | None = None,
    legacy_client: "SudespachoLegacyClient | None" = None,
    element: str | None = None,
    force: bool = False,
    incremental: bool = False,
) -> PullResult:
    """Descarga al `00_INPUT/sudespacho_{id}/` del caso todos los documentos
    del expediente.

    ⚠️ **LEGACY (2026-08-04). Para código nuevo usa :func:`pull_expediente_v2`.**
    El layout que escribe esta función —`00_Input/sudespacho_<id>/`— es el que
    :func:`is_legacy_intake_v1` declara **congelado**: en cuanto existe esa carpeta, el
    pull v2 y el intake judicial se bloquean, el árbol queda fuera de las fuentes que
    declara `organizar-sala-lectura` (`01_Drive EV`, `05_CRM`) y —lo caro— las
    escrituras **no pasan por el guard del caso prestado**, que solo existe en v2. Los
    tres CLI de sync (`pull`, `sync_all`, `scheduled_sync`) se migraron a v2 por eso
    (`MEJORAS #113`). Aquí sigue por `scripts/bulk_pull_expedientes.py`, que recorre el
    listado paginado del frontal heredado y todavía no se ha migrado.

    Convención de carpetas:

        data/CASOS/{case_id}/00_INPUT/
            _caso.md
            sudespacho_591/              ← extrajudicial 591
                .pulled                  ← marcador idempotencia (JSON con doc_ids)
                civil/
                demanda/
            sudespacho_648/              ← judicial 648
                .pulled
                civil/
                notificaciones/
            manual/                      ← docs añadidos a mano

    Modos de operación:
      force=False, incremental=False  →  skip si .pulled existe (pull inicial)
      force=False, incremental=True   →  descarga solo doc IDs nuevos
      force=True                      →  re-descarga todo

    Tras una descarga incremental exitosa, actualiza el array `doc_ids` en .pulled.

    Vías de descarga (en orden de preferencia):
      1. REST — list_gdocu_docs_rest + download_document_rest (sin PHPSESSID).
         Solo requiere x-api-key. Confirmado 2026-05-04.
      2. Legacy — list_doc_ids + download_document del frontal heredado PHP.
         Requiere PHPSESSID + @token + @refreshToken. Fallback si REST falla.
    """
    source_dir_name = _source_dir(str(expediente_id))
    input_root = caso_path(case_id) / "00_Input"
    target_dir = input_root / source_dir_name
    target_dir.mkdir(parents=True, exist_ok=True)

    marker = target_dir / _PULL_MARKER

    # Modo skip: ya descargado y no es incremental ni force
    if marker.exists() and not force and not incremental:
        existing = [p for p in target_dir.iterdir() if p.is_file() and p.name != _PULL_MARKER]
        existing = [p for p in target_dir.rglob("*") if p.is_file() and p.name != _PULL_MARKER]
        return PullResult(
            case_id=case_id,
            expediente_id=str(expediente_id),
            documents_total=len(existing),
            documents_downloaded=0,
            bytes_downloaded=sum(p.stat().st_size for p in existing),
            target_dir=target_dir,
            folders_processed=[],
            errors=[
                f"Ya descargado ({source_dir_name}/{_PULL_MARKER}). "
                f"Usa --incremental para actualizar o --force para re-descargar."
            ],
        )

    elem = element or "expedientes_judiciales"
    errors: list[str] = []
    bytes_before = _dir_size(target_dir)
    docs_processed: list[str] = []
    by_carpeta: dict[str, int] = {}
    already_pulled: set[str] = set()

    # Cliente API REST (primario — no requiere PHPSESSID para documentos).
    api_client = client
    owns_api = False
    if api_client is None:
        try:
            api_client = SudespachoClient()
            owns_api = True
        except SudespachoError:
            api_client = None  # API key no configurada → fallback legacy

    try:
        # ---------------------------------------------------------------
        # VÍA REST (preferida): list_gdocu_docs_rest + download_document_rest
        # Solo necesita x-api-key. Sin PHPSESSID. Confirmado 2026-05-04.
        # ---------------------------------------------------------------
        rest_doc_infos: list[GdocuDocInfo] | None = None
        if api_client is not None:
            try:
                rest_doc_infos = api_client.list_gdocu_docs_rest(
                    str(expediente_id), element=elem
                )
            except SudespachoError as exc:
                errors.append(
                    f"REST listing falló, usando fallback legacy: {exc}"
                )
                rest_doc_infos = None

        if rest_doc_infos is not None:
            # Incremental: filtrar IDs ya descargados
            if incremental and marker.exists():
                try:
                    pulled_data = json.loads(marker.read_text(encoding="utf-8"))
                    already_pulled = set(pulled_data.get("doc_ids", []))
                except (json.JSONDecodeError, OSError):
                    already_pulled = set()
                infos_to_download = [
                    d for d in rest_doc_infos if d.doc_id not in already_pulled
                ]
            else:
                infos_to_download = rest_doc_infos
                already_pulled = set()

            if not rest_doc_infos:
                errors.append(
                    f"El Gestor Documental del expediente {expediente_id} está vacío "
                    f"(o el elemento '{elem}' no es el correcto)."
                )

            for info in infos_to_download:
                # Carpeta destino: id_carpeta_label si disponible
                label = info.id_carpeta_label or info.id_carpeta or ""
                folder_slug = slugify(str(label)) if label else "_sin_carpeta"
                doc_dir = target_dir / folder_slug
                doc_dir.mkdir(parents=True, exist_ok=True)
                tmp = doc_dir / f"sudespacho_{info.doc_id}.tmp"

                try:
                    api_client.download_document_rest(  # type: ignore[union-attr]
                        info.doc_id, str(expediente_id), tmp, element=elem,
                    )
                except BaseException as exc:
                    # UNA limpieza para CUALQUIER interrupcion (R2/H-05 de MEJORAS #149): antes
                    # solo se limpiaba ante SudespachoError, y un OSError, un Ctrl-C o un kill
                    # a mitad de descarga dejaban `sudespacho_<id>.tmp` en el destino — un
                    # parcial que escribe este codigo, no el cliente, y que entraba en el
                    # inventario probatorio de la sala de maquina como si fuera un documento.
                    # Es un solo `unlink` a proposito: el censo de escrituras fuera de la
                    # costura (`tests/test_escritura_censo.py`) solo puede bajar.
                    tmp.unlink(missing_ok=True)
                    if not isinstance(exc, SudespachoError):
                        raise
                    errors.append(f"download REST doc {info.doc_id}: {exc}")
                    try:
                        if not any(doc_dir.iterdir()):
                            doc_dir.rmdir()
                    except OSError:
                        pass
                    continue

                # Renombrar con el nombre del archivo según el CRM
                original = info.filename or f"doc_{info.doc_id}.bin"
                stem, ext = _safe_stem_ext(original, info.mime, info.doc_id)
                final = doc_dir / f"{stem}{ext}"
                i = 1
                while final.exists() and final != tmp:
                    final = doc_dir / f"{stem}__{i}{ext}"
                    i += 1
                tmp.rename(final)
                docs_processed.append(info.doc_id)
                by_carpeta[folder_slug] = by_carpeta.get(folder_slug, 0) + 1

        else:
            # ---------------------------------------------------------------
            # FALLBACK LEGACY: requiere PHPSESSID + @token + @refreshToken
            # Se activa si la API REST no está disponible o falla.
            # ---------------------------------------------------------------
            from .sync_sudespacho_legacy import (
                SudespachoLegacyClient,
                SudespachoLegacyError,
            )

            owns_legacy = legacy_client is None
            try:
                legacy = legacy_client or SudespachoLegacyClient()
            except SudespachoLegacyError as exc:
                return PullResult(
                    case_id=case_id,
                    expediente_id=str(expediente_id),
                    documents_total=0,
                    documents_downloaded=0,
                    bytes_downloaded=0,
                    target_dir=target_dir,
                    errors=errors + [f"REST falló y cliente legacy no disponible: {exc}"],
                )

            try:
                try:
                    doc_ids = legacy.list_doc_ids(str(expediente_id), element=elem)
                except SudespachoLegacyError as exc:
                    return PullResult(
                        case_id=case_id,
                        expediente_id=str(expediente_id),
                        documents_total=0,
                        documents_downloaded=0,
                        bytes_downloaded=0,
                        target_dir=target_dir,
                        errors=errors + [f"list_doc_ids legacy: {exc}"],
                    )

                if not doc_ids:
                    errors.append(
                        f"El Gestor Documental del expediente {expediente_id} está vacío "
                        f"(o el elemento '{elem}' no es el correcto)."
                    )

                # Incremental: filtrar IDs ya descargados
                if incremental and marker.exists():
                    try:
                        pulled_data = json.loads(marker.read_text(encoding="utf-8"))
                        already_pulled = set(pulled_data.get("doc_ids", []))
                    except (json.JSONDecodeError, OSError):
                        already_pulled = set()
                    doc_ids_to_download = [
                        d for d in doc_ids if d not in already_pulled
                    ]
                else:
                    doc_ids_to_download = doc_ids
                    already_pulled = set()

                for doc_id in doc_ids_to_download:
                    # Carpeta destino: metadata vía API REST si disponible
                    folder_slug = "_sin_carpeta"
                    if api_client is not None:
                        try:
                            meta = api_client.get_document_metadata(doc_id)
                            label = (
                                meta.get("id_carpeta_label")
                                or meta.get("categoria")
                                or meta.get("carpeta_label")
                            )
                            if label:
                                folder_slug = slugify(str(label)) or "_sin_carpeta"
                        except SudespachoError as exc:
                            errors.append(f"meta legacy doc {doc_id}: {exc}")

                    doc_dir = target_dir / folder_slug
                    doc_dir.mkdir(parents=True, exist_ok=True)
                    tmp = doc_dir / f"sudespacho_{doc_id}.tmp"

                    try:
                        result = legacy.download_document(
                            doc_id, str(expediente_id), tmp, element=elem,
                        )
                    except SudespachoLegacyError as exc:
                        errors.append(f"download legacy doc {doc_id}: {exc}")
                        tmp.unlink(missing_ok=True)
                        try:
                            if not any(doc_dir.iterdir()):
                                doc_dir.rmdir()
                        except OSError:
                            pass
                        continue

                    original = result.filename_in_disposition or f"doc_{doc_id}.bin"
                    stem, ext = _safe_stem_ext(original, None, doc_id)
                    final = doc_dir / f"{stem}{ext}"
                    i = 1
                    while final.exists() and final != tmp:
                        final = doc_dir / f"{stem}__{i}{ext}"
                        i += 1
                    tmp.rename(final)
                    docs_processed.append(doc_id)
                    by_carpeta[folder_slug] = by_carpeta.get(folder_slug, 0) + 1

            finally:
                if owns_legacy:
                    legacy.__exit__(None, None, None)

        # Inventario final
        downloaded = [
            p for p in target_dir.rglob("*")
            if p.is_file() and p.name != _PULL_MARKER
        ]
        bytes_after = _dir_size(target_dir)

        # Actualizar marcador: merge de IDs previos + nuevos
        all_doc_ids = sorted(already_pulled | set(docs_processed))
        if all_doc_ids or docs_processed:
            marker.write_text(
                json.dumps(
                    {
                        "expediente_id": str(expediente_id),
                        "element": elem,
                        "doc_ids": all_doc_ids,
                        "by_carpeta": by_carpeta,
                        "last_sync": __import__("datetime").datetime.now().isoformat(
                            timespec="seconds"
                        ),
                        "errors": errors,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

        return PullResult(
            case_id=case_id,
            expediente_id=str(expediente_id),
            documents_total=len(downloaded),
            documents_downloaded=len(docs_processed),
            bytes_downloaded=bytes_after - bytes_before,
            target_dir=target_dir,
            folders_processed=sorted(by_carpeta.keys()),
            errors=errors,
        )
    finally:
        if owns_api and api_client is not None:
            api_client.__exit__(None, None, None)


# ---------------------------------------------------------------------------
# Pull v2 — refactor intake: 05_CRM/<rama>/ + dedup M9 + log M10 + estado D8
# ---------------------------------------------------------------------------
#
# Coexiste con pull_expediente() v1 — los CLIs y la UI siguen usando v1 hasta
# el paso 7 del refactor (project_intake_estructura_v2.md). v2 está pensado
# para casos nuevos; sobre casos legacy (sudespacho_*/ presente) se bloquea
# vía is_legacy_intake_v1() (D9).


@dataclass
class PullResultV2:
    """Resultado del pull v2 — alineado con el schema D8 del pull state.

    Diferencias respecto a PullResult (v1):
    - No hay `bytes_downloaded`: con dedup M9 la métrica relevante no es lo
      descargado por la red sino lo escrito a disco; eso lo cuenta
      `documents_written`.
    - `documents_total_crm` ≠ `documents_written` por el dedup M9.
    - `documents_overlap` cuenta los docs byte-idénticos a otro ya presente
      (otra fuente o rama) que, con `physical_complete=True`, se escriben
      físicamente igualmente para dejar `05_CRM` completo. Con el default
      (`physical_complete=False`) ese caso se contabiliza en
      `documents_skipped_dedup` y no se escribe.
    - `by_carpeta` mapea ruta canónica relativa a `00_Input/05_CRM/` (D11)
      → conteo lógico (incluye aliases del manifest, M9-Q3).
    - `kind_distribution` agrega los modos de resolución de
      `crm_branch_path` (id_mapping / label_heuristic / fallback).
    """
    case_id: str
    expediente_id: str
    element: str
    blocked_legacy_v1: bool = False
    documents_total_crm: int = 0
    documents_written: int = 0
    documents_skipped_dedup: int = 0
    documents_overlap: int = 0
    documents_failed: int = 0
    doc_ids: list[str] = field(default_factory=list)
    by_carpeta: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    kind_distribution: dict[str, int] = field(default_factory=dict)


#: Prefijo del aviso que `pull_expediente_v2` deposita en `errors` cuando el gestor
#: documental contesta y no tiene documentos. Vive aqui, junto a quien lo escribe.
_AVISO_GESTOR_VACIO = "El Gestor Documental del expediente"


def es_gestor_vacio(res: "PullResultV2") -> bool:
    """El gestor documental contesto y **no tiene documentos**. No es un error.

    **Por que vive aqui y no en el llamador.** Este modulo deposita ese aviso dentro de
    `errors` —contrato fijado a proposito por `tests/test_pull_expediente_v2.py:331`— y
    ademas deja `documents_total_crm` a 0 tanto si el gestor esta vacio como si el LISTADO
    fallo, porque en ese caso retorna antes de asignarlo. Un llamador que quisiera
    distinguir los dos casos tendria que replicar esa codificacion; si el mensaje cambia,
    lo que se rompe es este predicado y su test, no cada consumidor.

    Lo aprendio la R-B del Plan 5: un adaptador leyo los CAMPOS de `PullResultV2` y no su
    PRODUCTOR, concluyo que `errors` no vacio era fatal, y con eso un expediente sin
    documentos —lo normal en uno recien creado— abortaba la apertura entera.
    """
    errores = list(getattr(res, "errors", []) or [])
    if not errores:
        return False
    # Vacio confirmado: el aviso del gestor es el UNICO error. Con cualquier otro error
    # encima no se puede afirmar que el gestor contestara: manda el error.
    return all(e.startswith(_AVISO_GESTOR_VACIO) for e in errores)


def _resolve_name_collision(target: Path, sha: str) -> Path:
    """Defensa en profundidad ante colisión de nombre con hash distinto.

    Si `target` no existe, devuelve `target` tal cual.
    Si existe con el **mismo** hash, devuelve `target` (sobrescritura segura,
        es el mismo contenido).
    Si existe con hash distinto, busca el primer `target__N.<ext>` libre.

    En condiciones normales (manifest sincronizado), esta función nunca
    aplica el sufijo: el manifest detecta el dup antes de llegar aquí. Es
    fallback ante manifest perdido o intake mixto sin manifest.
    """
    if not target.exists():
        return target
    try:
        existing = compute_sha256(target)
    except OSError:
        existing = None
    if existing == sha:
        return target
    stem = target.stem
    suffix = target.suffix
    parent = target.parent
    i = 1
    while True:
        cand = parent / f"{stem}__{i}{suffix}"
        if not cand.exists():
            return cand
        i += 1


def pull_expediente_v2(
    case_id: str,
    expediente_id: str,
    *,
    element: str = "expedientes_judiciales",
    client: SudespachoClient | None = None,
    actor: str | None = None,
    only_doc_ids: set[str] | None = None,
    physical_complete: bool = False,
) -> PullResultV2:
    """Pull v2 de un expediente CRM al árbol ``00_Input/05_CRM/<rama>/`` del caso.

    Reescritura de :func:`pull_expediente` para el refactor intake v2
    (memoria persistente: ``project_intake_estructura_v2.md``). Diferencias
    clave respecto a v1:

    - Deposita los docs en la rama exacta del árbol del gestor documental
      vía :func:`crm_branch_path` (estrategia híbrida
      ``CARPETA_ID_TO_PATH`` + heurística por label + fallback
      ``99_Sin categoria/<expediente_id>/``).
    - Dedup cross-source SHA-256 vía :class:`IntakeManifest` (M9): un
      mismo doc que también llega de Drive E&V o email se persiste una sola
      vez como copia física, registrando aliases.
    - Estado del pull persistido en frontmatter de ``_caso.md`` vía
      :func:`update_pull_state` (D8), no en ``.pulled`` JSON suelto.
    - Eventos M10 emitidos a ``00_Input/_intake_log.jsonl`` (``pull_crm``
      al cierre, ``category_unknown`` por cada fallback,
      ``dedup_skipped`` por cada hash duplicado).
    - Bloqueo de casos legacy v1 (D9): si existe ``sudespacho_*/`` en
      ``00_Input/`` la función devuelve ``blocked_legacy_v1=True`` sin
      escribir nada. La UI debe mostrar mensaje de migración manual.

    Idempotencia: re-llamar es seguro y eficiente. El manifest M9 hace
    skip natural sobre los hashes ya presentes; no se necesita flag
    ``incremental`` ni ``force``.

    Args:
        case_id: ID del caso (debe existir y no ser legacy v1).
        expediente_id: ID del expediente CRM.
        element: ``"expedientes_judiciales"`` (default) | ``"extrajudiciales"``.
        client: ``SudespachoClient`` pre-construido. Si None, se construye
            uno desde ``.env``.
        actor: Override del actor para los eventos M10. Si None usa
            :func:`intake_log.get_actor`.
        only_doc_ids: si se indica, solo se descargan/depositan los documentos
            cuyo ``doc_id`` esté en el conjunto (intake acotado, p. ej.
            demanda+contestación). ``documents_total_crm`` sigue reflejando el
            total real del expediente en el CRM.
        physical_complete: si ``True``, deja ``05_CRM`` físicamente completo:
            un doc cuyo SHA ya existe en el manifest bajo OTRA ruta (otra
            fuente como Drive E&V, u otra rama) se escribe IGUALMENTE como
            copia física en su rama destino, en vez de saltarse. Cuenta en
            ``documents_overlap`` y emite ``cross_source_overlap``. El re-pull
            idempotente del mismo path (``rel_path == primary``) NO se escribe
            ni cuenta como overlap (es el mismo doc en su sitio). Con el
            default (``False``) el comportamiento es el dedup clásico (skip
            físico + ``dedup_skipped``).

    Returns:
        :class:`PullResultV2` con resumen del pull.
    """
    case_root = caso_path(case_id)
    input_root = case_root / "00_Input"
    crm_root = input_root / CRM_SUBDIR

    result = PullResultV2(
        case_id=case_id,
        expediente_id=str(expediente_id),
        element=element,
    )

    # 1. Bloqueo de casos legacy v1 (D9)
    if is_legacy_intake_v1(case_id):
        result.blocked_legacy_v1 = True
        result.errors.append(
            "Caso con estructura v1 (sudespacho_*/) — pull v2 bloqueado. "
            "Migración manual: borrar las carpetas sudespacho_*/ y volver a "
            "llamar a pull_expediente_v2()."
        )
        return result

    # 2. Cliente REST (sin PHPSESSID)
    api_client = client
    owns_client = False
    if api_client is None:
        try:
            api_client = SudespachoClient()
            owns_client = True
        except SudespachoError as exc:
            result.errors.append(f"No se pudo construir SudespachoClient: {exc}")
            return result

    try:
        # 3. Listado de docs vía REST
        try:
            docs = api_client.list_gdocu_docs_rest(
                str(expediente_id), element=element,
            )
        except SudespachoError as exc:
            result.errors.append(f"list_gdocu_docs_rest: {exc}")
            return result

        result.documents_total_crm = len(docs)

        if not docs:
            # Por la constante y no por literal: `es_gestor_vacio` reconoce este aviso
            # por su prefijo, y dos copias del mismo texto derivan.
            result.errors.append(
                f"{_AVISO_GESTOR_VACIO} {expediente_id} está vacío "
                f"(o el elemento '{element}' no es el correcto)."
            )

        # Registro de ocurrencias (spec vista procesal §2.1): se anota TODO lo que
        # el CRM enumera, **antes** del filtro acotado y antes de descargar nada.
        # Si se anotara dentro del bucle de descarga, el registro coincidiría con
        # `pull_state.doc_ids` aunque hubiera documentos del CRM invisibles, y la
        # puerta de integridad de la vista procesal no comprobaría nada (N2).
        ocurrencias = RegistroOcurrencias(case_id)
        ocurrencias.load()
        for info in docs:
            ocurrencias.registrar_listada(
                expediente_id=str(expediente_id),
                doc_id=info.doc_id,
                filename=info.filename,
                modified_at=info.modified_at,
                id_carpeta=info.id_carpeta,
            )
        # Se persiste ya: el universo de lo enumerado debe sobrevivir a un fallo
        # de descarga posterior.
        ocurrencias.save()

        # Intake acotado (Fase intake judicial): procesar solo los doc_ids
        # indicados, manteniendo documents_total_crm = total real del CRM.
        if only_doc_ids is not None:
            docs = [d for d in docs if d.doc_id in only_doc_ids]

        # Override local doc_id→bucket del letrado (D11) — leído una sola vez
        # para evitar I/O por-documento dentro del bucle.
        bucket_overrides = read_bucket_overrides(case_id)

        # Guard de escritura (DISEÑO_V2 §6): si el caso está prestado/conflicto,
        # las escrituras del pull se redirigen a _pendiente_checkin/crm/... (un
        # evento). El rel_path/manifest se mantienen en la ruta intencionada
        # (05_CRM/...): es donde CP10 dejará los ficheros al integrar la bandeja.
        _pull_guard = guard_escritura(case_id, f"00_Input/{CRM_SUBDIR}", "crm")
        _desviar_pull = _pull_guard.desviar

        def _target_efectivo(ft):
            if not _desviar_pull:
                return ft
            return case_root / PENDIENTE_CHECKIN_SUBDIR / "crm" / ft.relative_to(case_root)

        # 4. Manifest M9 + reconciliación al inicio (M9-Q4)
        with IntakeManifest(case_id) as manifest:
            manifest.reconcile()

            for info in docs:
                # 4.1 Resolver rama destino (override D11 → id → label → fallback)
                dest_dir, kind = crm_branch_path(
                    case_id,
                    id_carpeta=info.id_carpeta,
                    id_carpeta_label=info.id_carpeta_label,
                    expediente_id=str(expediente_id),
                    doc_id=info.doc_id,
                    overrides=bucket_overrides,
                )
                result.kind_distribution[kind] = (
                    result.kind_distribution.get(kind, 0) + 1
                )

                # Evento `category_unknown` cuando cae en fallback
                if kind == "fallback":
                    _log_event(
                        case_id, "category_unknown",
                        actor=actor,
                        details={
                            "expediente_id": str(expediente_id),
                            "doc_id": info.doc_id,
                            "id_carpeta": info.id_carpeta,
                            "id_carpeta_label": info.id_carpeta_label,
                        },
                    )

                # 4.2 Filename final dentro de la rama
                original = info.filename or f"doc_{info.doc_id}.bin"
                stem, ext = _safe_stem_ext(original, info.mime, info.doc_id)
                target_file = dest_dir / f"{stem}{ext}"

                # 4.3 Descargar bytes (necesitamos el contenido en memoria
                #     para hashear antes de escribir, M9-Q2)
                try:
                    url = api_client.get_presigned_download_url(
                        info.doc_id, str(expediente_id), element=element,
                    )
                    data = api_client._download_url_raw(url)
                except SudespachoError as exc:
                    result.errors.append(f"download doc {info.doc_id}: {exc}")
                    result.documents_failed += 1
                    continue

                # 4.4 SHA-256 + register en manifest
                sha = compute_sha256_bytes(data)

                # Resolver colisión de nombre antes de calcular el rel_path final
                final_target = _resolve_name_collision(target_file, sha)
                rel_path = final_target.relative_to(input_root).as_posix()

                action, primary_rel = manifest.register(
                    sha,
                    rel_path,
                    source="crm",
                    expediente_id=str(expediente_id),
                    doc_id=info.doc_id,
                )

                # Ruta donde el contenido de ESTE doc_id queda realmente accesible:
                # la propia si se escribe, la del primary si el dedup lo salta. Es
                # lo que permite que dos doc_id byte-idénticos (la TASA ORDINARIO
                # del piloto) resuelvan al mismo fichero sin perder su identidad.
                _ruta_registrada = rel_path if action == "write" else primary_rel

                if action == "write":
                    _wt = _target_efectivo(final_target)
                    _wt.parent.mkdir(parents=True, exist_ok=True)
                    _wt.write_bytes(data)
                    result.documents_written += 1
                elif physical_complete and rel_path != primary_rel:
                    # Solapamiento cross-source real: el SHA ya existe bajo otra
                    # ruta (otra fuente/rama). Con physical_complete escribimos
                    # la copia física igualmente para dejar 05_CRM completo.
                    # El alias ya lo registró manifest.register().
                    _wt = _target_efectivo(final_target)
                    _wt.parent.mkdir(parents=True, exist_ok=True)
                    _wt.write_bytes(data)
                    result.documents_overlap += 1
                    # La copia física propia sí se escribió: su ruta es la suya.
                    _ruta_registrada = rel_path
                    _log_event(
                        case_id, "cross_source_overlap",
                        actor=actor,
                        details={
                            "expediente_id": str(expediente_id),
                            "doc_id": info.doc_id,
                            "sha256": sha,
                            "primary_path": primary_rel,
                            "written_path": rel_path,
                        },
                    )
                else:
                    # Skip físico — primary_rel ya tiene el doc. Cubre el dedup
                    # clásico (physical_complete=False) y el re-pull idempotente
                    # del mismo path (rel_path == primary_rel), que no se cuenta
                    # como overlap porque es el mismo doc en su sitio.
                    result.documents_skipped_dedup += 1
                    _log_event(
                        case_id, "dedup_skipped",
                        actor=actor,
                        details={
                            "expediente_id": str(expediente_id),
                            "doc_id": info.doc_id,
                            "sha256": sha,
                            "primary_path": primary_rel,
                            "attempted_path": rel_path,
                        },
                    )

                # 4.4-bis El documento pasa de `listada` a `materializada`, con la
                #         ruta donde su contenido queda accesible y su SHA.
                ocurrencias.registrar_materializada(
                    expediente_id=str(expediente_id),
                    doc_id=info.doc_id,
                    path=_ruta_registrada,
                    sha256=sha,
                )

                # 4.5 by_carpeta cuenta la rama lógica destino del pull,
                #     no el primary_path físico (M9-Q3).
                rel_branch = dest_dir.relative_to(crm_root).as_posix()
                result.by_carpeta[rel_branch] = (
                    result.by_carpeta.get(rel_branch, 0) + 1
                )
                result.doc_ids.append(info.doc_id)

        # 4.6 Persistir el registro de ocurrencias con las materializaciones de
        #     esta corrida (las `listada` ya se guardaron antes de descargar).
        ocurrencias.save()

        # 5. Persistir pull state en frontmatter de _caso.md (D8)
        try:
            update_pull_state(
                case_id,
                str(expediente_id),
                element=element,
                last_sync=now_iso(),
                documents_total_crm=result.documents_total_crm,
                doc_ids=result.doc_ids,
                by_carpeta=result.by_carpeta,
                errors=result.errors,
            )
        except (FileNotFoundError, ValueError) as exc:
            result.errors.append(f"update_pull_state: {exc}")

        # 6. Evento de cierre `pull_crm` con resumen (M10)
        _log_event(
            case_id, "pull_crm",
            actor=actor,
            details={
                "expediente_id": str(expediente_id),
                "element": element,
                "documents_total_crm": result.documents_total_crm,
                "documents_written": result.documents_written,
                "documents_skipped_dedup": result.documents_skipped_dedup,
                "documents_overlap": result.documents_overlap,
                "documents_failed": result.documents_failed,
                "kind_distribution": result.kind_distribution,
                "errors_count": len(result.errors),
            },
        )

        return result
    finally:
        if owns_client and api_client is not None:
            api_client.__exit__(None, None, None)


def _dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for p in path.rglob("*"):
        if p.is_file():
            try:
                total += p.stat().st_size
            except OSError:
                pass
    return total
