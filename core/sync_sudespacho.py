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
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

import httpx

from .config import caso_path
from .utils import slugify


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

    # Descarga individual (alternativas)
    "document_download_uri": "/api/documents/{id}/downloadUri",
    "presigned_download":    "/api/documents/presigned_urls/{service}/download/{documentId}",
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
        # Documents schema: campo `doc`
        for key in (DOC_FIELDS["url"], "url", "downloadUrl", "fileUrl"):
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
            original = Path(info.filename)
            stem = slugify(original.stem) or "documento"
            ext = original.suffix or ".bin"
            target = target_dir / f"{stem}{ext}"
            i = 1
            while target.exists():
                target = target_dir / f"{stem}__{i}{ext}"
                i += 1
            with zf.open(info) as src, target.open("wb") as dst:
                dst.write(src.read())
        return target_dir

    # ---- Documentos: filtrado y descarga individual ---------------------

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
    """
    from .sync_sudespacho_legacy import (
        SudespachoLegacyClient,
        SudespachoLegacyError,
    )

    source_dir_name = _source_dir(str(expediente_id))
    input_root = caso_path(case_id) / "00_INPUT"
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
            errors=[f"Cliente legacy no disponible: {exc}"],
        )

    elem = element or "expedientes_judiciales"
    errors: list[str] = []
    bytes_before = _dir_size(target_dir)
    docs_processed: list[str] = []
    by_carpeta: dict[str, int] = {}

    # Cliente API nuevo (opcional) para enriquecer con id_carpeta_label.
    # Si no está configurado o falla, los documentos van a la raíz de
    # 00_INPUT/sudespacho/ sin agrupación por carpeta.
    api_client = client
    owns_api = False
    if api_client is None:
        try:
            api_client = SudespachoClient()
            owns_api = True
        except SudespachoError:
            api_client = None  # API key no configurada → flat fallback

    try:
        # 1) Listar IDs de documentos del expediente vía frontal heredado
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
                errors=[f"list_doc_ids: {exc}"],
            )

        if not doc_ids:
            errors.append(
                f"El Gestor Documental del expediente {expediente_id} está vacío "
                f"(o el elemento '{elem}' no es el correcto)."
            )

        # Incremental: filtrar solo doc IDs no descargados previamente
        if incremental and marker.exists():
            try:
                pulled_data = json.loads(marker.read_text(encoding="utf-8"))
                already_pulled = set(pulled_data.get("doc_ids", []))
            except (json.JSONDecodeError, OSError):
                already_pulled = set()
            doc_ids_to_download = [d for d in doc_ids if d not in already_pulled]
        else:
            doc_ids_to_download = doc_ids
            already_pulled = set()

        # 2) Por cada documento: metadata (carpeta) + descarga + rename
        for doc_id in doc_ids_to_download:
            # Resolver carpeta destino según id_carpeta del documento
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
                    errors.append(f"meta doc {doc_id}: {exc}")

            doc_dir = target_dir / folder_slug
            doc_dir.mkdir(parents=True, exist_ok=True)
            tmp = doc_dir / f"sudespacho_{doc_id}.tmp"

            try:
                result = legacy.download_document(
                    doc_id, str(expediente_id), tmp, element=elem,
                )
            except SudespachoLegacyError as exc:
                errors.append(f"download doc {doc_id}: {exc}")
                if tmp.exists():
                    tmp.unlink(missing_ok=True)
                # Limpia carpeta si quedó vacía
                try:
                    if not any(doc_dir.iterdir()):
                        doc_dir.rmdir()
                except OSError:
                    pass
                continue

            # Renombrar al nombre original normalizado, dentro de su carpeta
            original = result.filename_in_disposition or f"doc_{doc_id}.bin"
            stem = slugify(Path(original).stem) or f"doc_{doc_id}"
            ext = Path(original).suffix or ".bin"
            final = doc_dir / f"{stem}{ext}"
            i = 1
            while final.exists() and final != tmp:
                final = doc_dir / f"{stem}__{i}{ext}"
                i += 1
            tmp.rename(final)
            docs_processed.append(doc_id)
            by_carpeta[folder_slug] = by_carpeta.get(folder_slug, 0) + 1

        # 3) Inventario final (cuenta archivos en TODA la subjerarquía)
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
                        "last_sync": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
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
        if owns_legacy:
            legacy.__exit__(None, None, None)
        if owns_api and api_client is not None:
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
