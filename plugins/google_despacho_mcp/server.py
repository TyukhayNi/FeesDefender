#!/usr/bin/env python3
"""Servidor MCP `google-despacho` — F1: LECTURA de Drive multicuenta.

Doble restricción (calcada de Gmail-despacho): scope OAuth drive.readonly +
solo se registran tools de LECTURA. Ninguna operación de escritura/borrado/
permisos existe en F1.

Selección de cuenta: las tools aceptan `account` (email). En búsquedas/listados
se puede omitir para consultar TODAS las cuentas conectadas (cada resultado se
etiqueta con su cuenta). Las tools por-fichero exigen `account` explícito.

download_file_content escribe a disco (confinable con GOOGLE_DESPACHO_DL_ROOT);
nunca devuelve bytes por el modelo.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Callable, Optional

from mcp.server.fastmcp import FastMCP

# Import dual-modo: como paquete (tests) o standalone (Claude Desktop).
try:
    from . import drive_ops, google_auth
except ImportError:  # ejecución directa: python server.py
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import drive_ops  # type: ignore  # noqa: E402
    import google_auth  # type: ignore  # noqa: E402


def _resolve_accounts(account: Optional[str], lister: Callable[[], list[str]]) -> list[str]:
    if account:
        return [account]
    accounts = lister()
    if not accounts:
        raise RuntimeError(
            "No hay cuentas conectadas. Añade alguna con: "
            "python plugins/google_despacho_mcp/google_cli.py add"
        )
    return accounts


def _resolve_dest(dest_path: str) -> str:
    """Resuelve y valida la ruta de descarga; si GOOGLE_DESPACHO_DL_ROOT está
    definida, el destino debe quedar dentro de esa raíz. Se resuelven symlinks/
    junctions (realpath) antes de comparar, para que un enlace dentro de la raíz
    no permita escapar de ella."""
    dest = os.path.realpath(os.path.expanduser(dest_path))
    root = os.environ.get("GOOGLE_DESPACHO_DL_ROOT")
    if root:
        root_abs = os.path.realpath(os.path.expanduser(root))
        try:
            inside = os.path.commonpath([root_abs, dest]) == root_abs
        except ValueError:
            inside = False  # p.ej. unidades distintas en Windows
        if not inside:
            raise ValueError(f"Destino fuera de GOOGLE_DESPACHO_DL_ROOT ({root_abs}): {dest}")
    return dest


def _resolve_upload(local_path: str) -> str:
    """Resuelve y valida la ruta de ORIGEN de una subida. Si
    GOOGLE_DESPACHO_UPLOAD_ROOT está definida, el origen debe quedar dentro de esa
    raíz (realpath contra symlink-escape). El fichero debe existir."""
    src = os.path.realpath(os.path.expanduser(local_path))
    if not os.path.isfile(src):
        raise FileNotFoundError(f"No existe el fichero a subir: {src}")
    root = os.environ.get("GOOGLE_DESPACHO_UPLOAD_ROOT")
    if root:
        root_abs = os.path.realpath(os.path.expanduser(root))
        try:
            inside = os.path.commonpath([root_abs, src]) == root_abs
        except ValueError:
            inside = False  # unidades distintas en Windows
        if not inside:
            raise ValueError(f"Origen fuera de GOOGLE_DESPACHO_UPLOAD_ROOT ({root_abs}): {src}")
    return src


INTERNAL_DOMAINS = {"tyukhay.legal", "engelvoelkers.com"}
_ALLOWED_PERM_TYPES = {"anyone", "user", "group", "domain"}


def _guard_external_share(*, perm_type: str, role: str,
                          email_address: Optional[str], domain: Optional[str],
                          allow_external: bool) -> None:
    """Guardarraíl §5. Lanza ValueError si role=owner (siempre prohibido), si el
    perm_type es desconocido (fail-closed), o si la compartición es externa sin
    allow_external. Normaliza type/role (strip+lower) para no depender de que Drive
    rechace enums mal escritos."""
    if (role or "").strip().lower() == "owner":
        raise ValueError("role=owner nunca se concede automáticamente por el MCP.")
    ptype = (perm_type or "").strip().lower()
    if ptype not in _ALLOWED_PERM_TYPES:
        raise ValueError(f"perm_type desconocido: {perm_type!r} "
                         f"(esperado uno de {sorted(_ALLOWED_PERM_TYPES)}).")
    external = False
    if ptype == "anyone":
        external = True
    elif ptype in ("user", "group"):
        dom = (email_address or "").strip().rsplit("@", 1)[-1].lower()
        external = dom not in INTERNAL_DOMAINS
    elif ptype == "domain":
        external = (domain or "").strip().lower() not in INTERNAL_DOMAINS
    if external and not allow_external:
        raise ValueError(
            "Compartición EXTERNA bloqueada (type/dominio ajeno a "
            f"{sorted(INTERNAL_DOMAINS)}). Repite con allow_external=true si es a "
            "conciencia.")


def build_server(
    *,
    service_factory: Callable[[str], object] | None = None,
    account_lister: Callable[[], list[str]] | None = None,
) -> FastMCP:
    """Construye el servidor. `service_factory`/`account_lister` son puntos de
    inyección para tests; en producción se toman de google_auth."""
    if service_factory is None:
        service_factory = google_auth.build_service
    if account_lister is None:
        account_lister = google_auth.list_account_emails

    mcp = FastMCP("google-despacho")

    @mcp.tool()
    def list_accounts() -> list[str]:
        """Lista las cuentas de Google conectadas a este servidor."""
        return account_lister()

    @mcp.tool()
    def list_shared_drives(account: Optional[str] = None) -> dict:
        """Lista las unidades compartidas accesibles por cada cuenta."""
        out: dict[str, list[dict]] = {}
        for acc in _resolve_accounts(account, account_lister):
            out[acc] = drive_ops.list_shared_drives(service_factory(acc))
        return out

    @mcp.tool()
    def search_files(
        query: str,
        account: Optional[str] = None,
        drive_id: Optional[str] = None,
        max_results: int = 50,
    ) -> list[dict]:
        """Busca ficheros con la sintaxis de query de Drive v3 (abarca unidades
        compartidas). `query` p.ej. "name contains 'arras' and trashed = false".
        Omite `account` para buscar en TODAS las cuentas. `drive_id` acota a una
        unidad compartida concreta."""
        results: list[dict] = []
        for acc in _resolve_accounts(account, account_lister):
            found = drive_ops.search_files(
                service_factory(acc), query, drive_id=drive_id, max_results=max_results
            )
            results.extend({**f, "account": acc} for f in found)
        return results

    @mcp.tool()
    def list_recent_files(account: Optional[str] = None, max_results: int = 20) -> list[dict]:
        """Ficheros modificados recientemente (por cuenta)."""
        results: list[dict] = []
        for acc in _resolve_accounts(account, account_lister):
            found = drive_ops.list_recent_files(service_factory(acc), page_size=max_results)
            results.extend({**f, "account": acc} for f in found)
        return results

    @mcp.tool()
    def get_file_metadata(file_id: str, account: str) -> dict:
        """Metadatos de un fichero (incluye sha256Checksum si es binario)."""
        return drive_ops.get_file_metadata(service_factory(account), file_id)

    @mcp.tool()
    def get_file_permissions(file_id: str, account: str) -> list[dict]:
        """Lista los permisos (ACL) de un fichero: type/role/emailAddress/domain."""
        return drive_ops.get_file_permissions(service_factory(account), file_id)

    @mcp.tool()
    def read_file_content(file_id: str, account: str, max_bytes: int = 5_000_000) -> dict:
        """Devuelve el TEXTO de un Doc nativo (exportado) o de un fichero de
        texto. Los binarios se rechazan: usa download_file_content."""
        return drive_ops.read_file_content(service_factory(account), file_id, max_bytes=max_bytes)

    @mcp.tool()
    def download_file_content(
        file_id: str,
        account: str,
        dest_path: str,
        max_bytes: int = 100_000_000,
        keep_editable: bool = False,
    ) -> dict:
        """Descarga un fichero a disco local (Doc nativo → PDF por defecto;
        keep_editable → Office). Confinable con GOOGLE_DESPACHO_DL_ROOT. Nunca
        devuelve los bytes por el modelo; devuelve ruta, tamaño y sha256."""
        dest = _resolve_dest(dest_path)
        return drive_ops.download_file_content(
            service_factory(account), file_id, dest,
            max_bytes=max_bytes, keep_editable=keep_editable,
        )

    @mcp.tool()
    def about_get(account: str) -> dict:
        """Info de la cuenta y cuota de almacenamiento (about.get)."""
        return drive_ops.about_get(service_factory(account))

    @mcp.tool()
    def create_file(name: str, parent_id: str, text: str, account: str,
                    mime_type: str = "text/plain") -> dict:
        """Crea un fichero de TEXTO (contenido del modelo: logs, notas, .md) en la
        carpeta `parent_id`. Para ficheros binarios/grandes usa upload_file.
        Devuelve id, nombre, sha256 y web_view_link."""
        return drive_ops.create_file(
            service_factory(account), name=name, parent_id=parent_id,
            text=text, mime_type=mime_type)

    @mcp.tool()
    def upload_file(local_path: str, parent_id: str, account: str,
                    name: Optional[str] = None) -> dict:
        """Sube un fichero desde una ruta LOCAL (confinada por
        GOOGLE_DESPACHO_UPLOAD_ROOT) a la carpeta `parent_id`. Los bytes NO pasan
        por el modelo. Devuelve id, nombre, sha256 y web_view_link."""
        src = _resolve_upload(local_path)
        return drive_ops.upload_file(
            service_factory(account), local_path=src, parent_id=parent_id, name=name)

    @mcp.tool()
    def create_folder(name: str, parent_id: str, account: str) -> dict:
        """Crea una carpeta bajo `parent_id`. Para estructura anidada idempotente
        usa ensure_folder_path."""
        return drive_ops.create_folder(service_factory(account), name=name, parent_id=parent_id)

    @mcp.tool()
    def ensure_folder_path(path: str, parent_id: str, account: str) -> dict:
        """Crea los segmentos de `path` (p. ej. '01_Procesado/Sala lectura') que no
        existan bajo `parent_id` y devuelve el id de la carpeta final. IDEMPOTENTE:
        no duplica carpetas existentes (Drive permite duplicados; esto lo evita)."""
        return drive_ops.ensure_folder_path(service_factory(account), path=path, parent_id=parent_id)

    @mcp.tool()
    def update_file_content(file_id: str, account: str,
                            text: Optional[str] = None,
                            local_path: Optional[str] = None) -> dict:
        """Reemplaza el contenido de un fichero (mismo id). Pasa `text` (contenido
        del modelo) O `local_path` (ruta local confinada por UPLOAD-root), no ambos.
        Devuelve id, nombre, sha256 y web_view_link."""
        src = _resolve_upload(local_path) if local_path else None
        return drive_ops.update_file_content(
            service_factory(account), file_id, text=text, local_path=src)

    @mcp.tool()
    def update_file_metadata(file_id: str, name: str, account: str) -> dict:
        """Renombra un fichero. Devuelve id, nombre y web_view_link."""
        return drive_ops.update_file_metadata(service_factory(account), file_id, name=name)

    @mcp.tool()
    def move_file(file_id: str, dst_folder_id: str, account: str) -> dict:
        """Mueve un fichero a otra carpeta (addParents/removeParents)."""
        return drive_ops.move_file(service_factory(account), file_id, dst_folder_id=dst_folder_id)

    @mcp.tool()
    def copy_file(file_id: str, dst_folder_id: str, account: str,
                  new_name: Optional[str] = None) -> dict:
        """Copia un fichero a otra carpeta (files.copy interno de Drive), con
        renombrado opcional."""
        return drive_ops.copy_file(service_factory(account), file_id,
                                   dst_folder_id=dst_folder_id, new_name=new_name)

    @mcp.tool()
    def delete_file(file_id: str, account: str, permanent: bool = False) -> dict:
        """Envía un fichero a la PAPELERA (por defecto, reversible con restore_file).
        permanent=True lo borra IRREVERSIBLEMENTE."""
        return drive_ops.delete_file(service_factory(account), file_id, permanent=permanent)

    @mcp.tool()
    def restore_file(file_id: str, account: str) -> dict:
        """Saca un fichero de la papelera."""
        return drive_ops.restore_file(service_factory(account), file_id)

    @mcp.tool()
    def export_to_drive(file_id: str, account: str, format: str = "pdf",
                        dst_folder_id: Optional[str] = None,
                        new_name: Optional[str] = None) -> dict:
        """Exporta un Doc nativo a PDF (default) u Office ('office') y GUARDA el
        resultado en Drive (server-side; sin bytes por el modelo). Destino por
        defecto = la carpeta del origen. Devuelve id, nombre, sha256 y web_view_link."""
        return drive_ops.export_to_drive(
            service_factory(account), file_id, format=format,
            dst_folder_id=dst_folder_id, new_name=new_name)

    @mcp.tool()
    def append_text(file_id: str, text: str, account: str) -> dict:
        """Añade texto al final de un fichero de TEXTO existente (p. ej.
        _intake_log.jsonl). Read-modify-write server-side. Devuelve id, nombre y
        sha256 del resultado."""
        return drive_ops.append_text(service_factory(account), file_id, text)

    @mcp.tool()
    def create_shortcut(target_id: str, dst_folder_id: str, account: str,
                        name: Optional[str] = None) -> dict:
        """Crea un acceso directo a `target_id` en `dst_folder_id`: enlaza un doc en
        varias carpetas sin duplicar bytes (fuente única)."""
        return drive_ops.create_shortcut(
            service_factory(account), target_id=target_id,
            dst_folder_id=dst_folder_id, name=name)

    @mcp.tool()
    def create_permission(file_id: str, perm_type: str, role: str, account: str,
                          email_address: Optional[str] = None,
                          domain: Optional[str] = None,
                          allow_external: bool = False,
                          send_notification_email: bool = False) -> dict:
        """Concede un permiso (ACL). perm_type: user|group|domain|anyone;
        role: reader|commenter|writer (owner PROHIBIDO). Compartir con externos
        (anyone o dominio ajeno a tyukhay.legal/engelvoelkers.com) exige
        allow_external=true. No envía email de aviso salvo send_notification_email."""
        ptype = (perm_type or "").strip().lower()
        nrole = (role or "").strip().lower()
        _guard_external_share(perm_type=ptype, role=nrole,
                              email_address=email_address, domain=domain,
                              allow_external=allow_external)
        return drive_ops.create_permission(
            service_factory(account), file_id, perm_type=ptype, role=nrole,
            email_address=email_address, domain=domain,
            send_notification_email=send_notification_email)

    @mcp.tool()
    def update_permission(file_id: str, permission_id: str, role: str,
                          account: str, allow_external: bool = False) -> dict:
        """Cambia el rol de un permiso existente. owner PROHIBIDO. Si el permiso es
        EXTERNO (anyone o dominio ajeno), escalar su rol exige allow_external=true."""
        svc = service_factory(account)
        existing = drive_ops.get_permission(svc, file_id, permission_id)
        nrole = (role or "").strip().lower()
        _guard_external_share(
            perm_type=existing.get("type", ""), role=nrole,
            email_address=existing.get("emailAddress"),
            domain=existing.get("domain"), allow_external=allow_external)
        return drive_ops.update_permission(svc, file_id, permission_id, role=nrole)

    @mcp.tool()
    def delete_permission(file_id: str, permission_id: str, account: str) -> dict:
        """Revoca un permiso (ACL) de un fichero."""
        return drive_ops.delete_permission(service_factory(account), file_id, permission_id)

    @mcp.tool()
    def list_folder(folder_id: str, account: str, max_results: int = 200) -> list[dict]:
        """Lista los hijos DIRECTOS de una carpeta (navegación tipo explorador, sin
        escribir queries). No recursivo."""
        return drive_ops.list_folder(service_factory(account), folder_id, page_size=max_results)

    @mcp.tool()
    def list_trash(account: str, max_results: int = 100) -> list[dict]:
        """Lista los ficheros en la papelera de la cuenta (recuperables con
        restore_file)."""
        return drive_ops.list_trash(service_factory(account), page_size=max_results)

    @mcp.tool()
    def get_folder_path(folder_id: str, account: str) -> dict:
        """Miga de pan / ruta completa de una carpeta (raíz→hoja)."""
        return drive_ops.get_folder_path(service_factory(account), folder_id)

    return mcp


def main() -> None:
    build_server().run()


if __name__ == "__main__":
    main()
