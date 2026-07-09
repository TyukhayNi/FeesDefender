"""Operaciones PURAS de Google Drive v3.

Sin dependencia de `mcp` ni de `core/`: cada función recibe un `service` ya
construido (googleapiclient) e implementa una operación de lectura. Testeable
con un `service` fake inyectado. Todas las lecturas abarcan unidades
compartidas (corpora=allDrives, includeItemsFromAllDrives, supportsAllDrives).
"""
from __future__ import annotations

import hashlib
from pathlib import Path

FILE_FIELDS = (
    "id, name, mimeType, size, modifiedTime, createdTime, parents, driveId, "
    "webViewLink, sha256Checksum, trashed, owners(emailAddress)"
)
PERM_FIELDS = (
    "permissions(id, type, role, emailAddress, domain, displayName, deleted)"
)

GOOGLE_NATIVE_PREFIX = "application/vnd.google-apps."
_EXPORT_TEXT = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
    "application/vnd.google-apps.presentation": "text/plain",
}
_EXPORT_PDF = {
    "application/vnd.google-apps.document": "application/pdf",
    "application/vnd.google-apps.spreadsheet": "application/pdf",
    "application/vnd.google-apps.presentation": "application/pdf",
    "application/vnd.google-apps.drawing": "application/pdf",
}
_EXPORT_OFFICE = {
    "application/vnd.google-apps.document":
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.google-apps.spreadsheet":
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.google-apps.presentation":
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}
_TEXTUAL_MIMES = {"application/json", "application/xml", "application/rtf", "text/csv"}


def list_shared_drives(service, *, page_size: int = 100) -> list[dict]:
    drives: list[dict] = []
    page_token = None
    while True:
        params = {"pageSize": min(page_size, 100),
                  "fields": "nextPageToken, drives(id, name)"}
        if page_token:
            params["pageToken"] = page_token
        resp = service.drives().list(**params).execute()
        drives.extend(resp.get("drives", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return drives


def search_files(service, query: str, *, page_size: int = 50,
                 drive_id: str | None = None, order_by: str | None = None,
                 max_results: int | None = None) -> list[dict]:
    files: list[dict] = []
    page_token = None
    while True:
        params = {
            "q": query,
            "pageSize": min(page_size, 1000),
            "fields": f"nextPageToken, files({FILE_FIELDS})",
            "includeItemsFromAllDrives": True,
            "supportsAllDrives": True,
            "spaces": "drive",
        }
        if drive_id:
            params["corpora"] = "drive"
            params["driveId"] = drive_id
        else:
            params["corpora"] = "allDrives"
        if order_by:
            params["orderBy"] = order_by
        if page_token:
            params["pageToken"] = page_token
        resp = service.files().list(**params).execute()
        files.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token or (max_results and len(files) >= max_results):
            break
    return files[:max_results] if max_results else files


def list_recent_files(service, *, page_size: int = 20) -> list[dict]:
    resp = service.files().list(
        pageSize=min(page_size, 1000),
        orderBy="modifiedTime desc",
        q="trashed = false",
        fields=f"files({FILE_FIELDS})",
        includeItemsFromAllDrives=True,
        supportsAllDrives=True,
        corpora="allDrives",
        spaces="drive",
    ).execute()
    return resp.get("files", [])


def about_get(service, *,
              fields: str = "user(displayName, emailAddress), storageQuota") -> dict:
    return service.about().get(fields=fields).execute()


def get_file_metadata(service, file_id: str, *, fields: str | None = None) -> dict:
    return service.files().get(
        fileId=file_id,
        fields=fields or FILE_FIELDS,
        supportsAllDrives=True,
    ).execute()


def get_file_permissions(service, file_id: str) -> list[dict]:
    perms: list[dict] = []
    page_token = None
    while True:
        params = {
            "fileId": file_id,
            "supportsAllDrives": True,
            "pageSize": 100,
            "fields": f"nextPageToken, {PERM_FIELDS}",
        }
        if page_token:
            params["pageToken"] = page_token
        resp = service.permissions().list(**params).execute()
        perms.extend(resp.get("permissions", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return perms


def read_file_content(service, file_id: str, *, max_bytes: int = 5_000_000) -> dict:
    """Devuelve el TEXTO de un fichero: Doc nativo exportado a texto, o fichero
    de texto plano. Los binarios se rechazan (usa download_file_content)."""
    meta = get_file_metadata(service, file_id, fields="id, name, mimeType, size")
    mime = meta.get("mimeType", "")
    name = meta.get("name", "")
    if mime.startswith(GOOGLE_NATIVE_PREFIX):
        export_mime = _EXPORT_TEXT.get(mime)
        if not export_mime:
            raise ValueError(
                f"El Doc nativo {mime!r} no es exportable a texto; "
                f"usa download_file_content."
            )
        data = service.files().export_media(fileId=file_id, mimeType=export_mime).execute()
    else:
        if not (mime.startswith("text/") or mime in _TEXTUAL_MIMES):
            raise ValueError(
                f"El fichero {mime!r} no es de texto; usa download_file_content."
            )
        size = int(meta.get("size") or 0)
        if max_bytes and size > max_bytes:
            raise ValueError(f"{size} bytes supera max_bytes ({max_bytes}).")
        data = service.files().get_media(fileId=file_id, supportsAllDrives=True).execute()
    if isinstance(data, (bytes, bytearray)):
        if max_bytes and len(data) > max_bytes:
            raise ValueError(f"{len(data)} bytes supera max_bytes ({max_bytes}).")
        text = bytes(data).decode("utf-8", "replace")
    else:
        text = str(data)
    return {"id": file_id, "name": name, "mime_type": mime, "text": text}


def download_file_content(service, file_id: str, dest_path: str, *,
                          max_bytes: int = 100_000_000,
                          keep_editable: bool = False) -> dict:
    """Descarga a `dest_path` (ruta absoluta ya saneada por el server). Doc
    nativo → export (default PDF; keep_editable → Office). Devuelve path,
    bytes y sha256 del artefacto realmente guardado."""
    meta = get_file_metadata(
        service, file_id, fields="id, name, mimeType, size, sha256Checksum"
    )
    mime = meta.get("mimeType", "")
    if mime.startswith(GOOGLE_NATIVE_PREFIX):
        table = _EXPORT_OFFICE if keep_editable else _EXPORT_PDF
        export_mime = table.get(mime)
        if not export_mime:
            raise ValueError(f"El Doc nativo {mime!r} no tiene export soportado.")
        data = service.files().export_media(fileId=file_id, mimeType=export_mime).execute()
    else:
        size = int(meta.get("size") or 0)
        if max_bytes and size > max_bytes:
            raise ValueError(f"{size} bytes supera max_bytes ({max_bytes}).")
        data = service.files().get_media(fileId=file_id, supportsAllDrives=True).execute()
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("La API no devolvió bytes al descargar.")
    if max_bytes and len(data) > max_bytes:
        raise ValueError(f"{len(data)} bytes supera max_bytes ({max_bytes}).")
    dest = Path(dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return {
        "path": str(dest),
        "bytes": len(data),
        "mime_type": mime,
        "sha256": hashlib.sha256(bytes(data)).hexdigest(),
    }
