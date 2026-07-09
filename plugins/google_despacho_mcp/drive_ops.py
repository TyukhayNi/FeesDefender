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
