"""Servidor MCP stdio `email-export` — expone ``export_label`` como tool MCP.

Diferencia clave respecto a ``expedientes-xl``: este server SÍ importa ``core/``
(corre en el PC del abogado donde vive el repo y los tokens OAuth). No es
auto-contenido por diseño; ver README para prerrequisitos.

Uso:
    python server.py [--repo-root <ruta>]

Si --repo-root se omite, se asume que el repo está en el directorio padre del
script (``plugins/email_export_mcp/server.py`` → raíz = ``../..``).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

from mcp.server.fastmcp import FastMCP

_HERE = Path(__file__).resolve().parent
_REPO_ROOT_DEFAULT = _HERE.parents[1]


def _ensure_core_importable(repo_root: Path) -> None:
    root_str = str(repo_root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


def _import_core() -> tuple[Callable, Callable, Callable]:
    from core.casos.case_locator import resolve_ref  # noqa: PLC0415
    from core.email_export import email_dest_dir, export_label  # noqa: PLC0415
    return resolve_ref, email_dest_dir, export_label


def build_server(
    repo_root: Path | None = None,
    *,
    _resolve_ref: Callable | None = None,
    _email_dest_dir: Callable | None = None,
    _export_label: Callable | None = None,
) -> FastMCP:
    """Construye el servidor MCP.

    Los parámetros ``_resolve_ref``, ``_email_dest_dir``, ``_export_label`` son
    puntos de inyección para tests. En producción se omiten y se importan de core.
    """
    if _resolve_ref is None:
        if repo_root is None:
            repo_root = _REPO_ROOT_DEFAULT
        _ensure_core_importable(repo_root)
        _resolve_ref, _email_dest_dir, _export_label = _import_core()

    mcp = FastMCP("email-export")

    @mcp.tool()
    def export_label_emails(
        ref: str,
        account: str,
        label: str,
        extraer_adjuntos: bool = False,
        workers: int = 8,
        force: bool = False,
    ) -> str:
        """Exporta todos los mensajes de una etiqueta Gmail al expediente como .eml fieles.

        Parámetros:
            ref: case_id canónico o W-code (p.ej. "W-02VND1"). Se resuelve al nombre
                de carpeta canónico del expediente.
            account: cuenta Gmail con la etiqueta (p.ej.
                "nikolai.tyukhay@engelvoelkers.com"). Los casos E&V usan la cuenta
                @engelvoelkers; con otra cuenta ``labels().list`` devolverá vacío.
            label: nombre exacto de la etiqueta Gmail (p.ej.
                "01. CONTING/01. EXTRAJUD/BaRS1 - [inmueble] - (W-02VND1)").
            extraer_adjuntos: si True, extrae los adjuntos a subcarpeta fechada.
                Por defecto False (estructura plana: un .eml por mensaje).
            workers: hilos paralelos de descarga (default 8).
            force: si True, re-descarga aunque el mensaje ya esté en el índice.
        """
        case_id = _resolve_ref(ref)
        dest_dir = _email_dest_dir(case_id)

        report = _export_label(
            account,
            label,
            dest_dir,
            case_id=case_id,
            extract_attachments=extraer_adjuntos,
            max_workers=workers,
            force=force,
        )

        lines = [
            report.resumen(),
            f"destino: {dest_dir}",
            f"traza_forense: {report.intake_logged}",
        ]
        if report.errors:
            lines.append(f"errores ({len(report.errors)}): " + "; ".join(report.errors[:5]))
        return "\n".join(lines)

    return mcp


def main() -> None:
    import argparse  # noqa: PLC0415
    parser = argparse.ArgumentParser(description="MCP server: export_label_emails")
    parser.add_argument("--repo-root", type=Path, default=None,
                        help="Raíz del repo FeesDefender (default: detectado automáticamente)")
    args = parser.parse_args()
    build_server(repo_root=args.repo_root).run()


if __name__ == "__main__":
    main()
