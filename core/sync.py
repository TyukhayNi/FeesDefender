"""Sincronización de documentación desde un remoto rclone.

Wrapper fino: ejecuta `rclone copy <remote_path> <case>/00_INPUT/drive
--skip-links`. No mueve ni borra nada en el remoto. Si rclone no está
disponible, lanza `SyncError` con instrucciones legibles.

Convención: cada backend de ingesta escribe en su propia subcarpeta
dentro de `00_INPUT/` para preservar trazabilidad de origen y permitir
idempotencia por fuente. Aquí: `00_INPUT/drive/`.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import caso_path, settings


class SyncError(RuntimeError):
    pass


@dataclass
class SyncResult:
    case_id: str
    remote_path: str
    files_copied: int
    bytes_copied: int
    stdout: str
    stderr: str


_SOURCE_DIR = "drive"
_SYNC_MARKER = ".synced"


def _check_binary() -> str:
    binary = shutil.which(settings.rclone_binary) or settings.rclone_binary
    try:
        subprocess.run([binary, "version"], capture_output=True, check=True, timeout=10)
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise SyncError(
            f"rclone no disponible ({binary}). Instala rclone y configura el remoto "
            f"`{settings.rclone_remote}` con `rclone config`."
        ) from exc
    return binary


def pull(case_id: str, *, remote_path: str, dry_run: bool = False) -> SyncResult:
    """Sincroniza el remoto al `00_INPUT/drive/` del caso."""
    binary = _check_binary()
    target = caso_path(case_id) / "00_INPUT" / _SOURCE_DIR
    target.mkdir(parents=True, exist_ok=True)

    cmd = [
        binary, "copy", remote_path, str(target),
        "--skip-links", "--ignore-checksum", "--stats", "0",
        "--use-mmap", "--transfers", "4",
    ]
    if dry_run:
        cmd.append("--dry-run")

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=600)
    except subprocess.CalledProcessError as exc:
        raise SyncError(f"rclone falló: {exc.stderr.strip()}") from exc
    except subprocess.TimeoutExpired as exc:
        raise SyncError("rclone superó el timeout (10 min). Revisa conectividad.") from exc

    files = sum(
        1 for p in target.rglob("*")
        if p.is_file() and p.name not in (_SYNC_MARKER, "_inventory.json")
    )
    size = sum(p.stat().st_size for p in target.rglob("*") if p.is_file())

    if not dry_run and files > 0:
        # Marcador con metadatos de la última sync
        from datetime import datetime
        (target / _SYNC_MARKER).write_text(
            f'{{"remote": "{remote_path}", "synced_at": "{datetime.now().isoformat()}", '
            f'"files": {files}}}',
            encoding="utf-8",
        )

    return SyncResult(
        case_id=case_id,
        remote_path=remote_path,
        files_copied=files,
        bytes_copied=size,
        stdout=proc.stdout,
        stderr=proc.stderr,
    )
