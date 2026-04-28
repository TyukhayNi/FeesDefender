"""Inventario de archivos en `00_Input/`.

Genera `_inventory.json` con metadatos por archivo (tamaño, hash, mime básico,
fecha mtime, fuente) para alimentar las fases siguientes del pipeline.

Convención de fuentes: cada subcarpeta directa de `00_Input/` representa
una fuente de ingestión (`sudespacho/`, `drive/`, `email/`, `whatsapp/`,
`manual/`, ...). Los archivos sueltos en la raíz de `00_Input/` se
clasifican como `manual`. La ruta relativa preserva la fuente.
"""

from __future__ import annotations

import json
import mimetypes
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from .config import caso_path
from .utils import file_sha256


@dataclass
class FileEntry:
    rel_path: str
    name: str
    ext: str
    size: int
    mtime: str
    mime: str | None
    sha256: str
    source: str  # 'sudespacho', 'drive', 'email', 'whatsapp', 'manual', ...


# Tipos relevantes para el pipeline jurídico
_RELEVANT_EXTS = {
    ".pdf", ".docx", ".doc", ".odt",
    ".txt", ".rtf", ".md",
    ".xlsx", ".xls", ".csv",
    ".eml", ".msg",
    ".jpg", ".jpeg", ".png", ".tiff", ".tif",
    ".html", ".htm",
}

# Archivos de control que el inventario debe ignorar a cualquier nivel.
_CONTROL_FILES = {"_inventory.json", ".pulled", ".synced"}


def _source_of(rel_parts: tuple[str, ...]) -> str:
    """Determina la fuente a partir de la ruta relativa al 00_Input/.

    Si está en una subcarpeta directa, esa es la fuente. Si está en la
    raíz, se considera 'manual' (drag-and-drop del abogado).
    """
    if len(rel_parts) >= 2:
        return rel_parts[0]
    return "manual"


def _entry(root: Path, path: Path) -> FileEntry:
    rel_parts = path.relative_to(root).parts
    rel = path.relative_to(root).as_posix()
    mime, _ = mimetypes.guess_type(path.name)
    return FileEntry(
        rel_path=rel,
        name=path.name,
        ext=path.suffix.lower(),
        size=path.stat().st_size,
        mtime=datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
        mime=mime,
        sha256=file_sha256(path),
        source=_source_of(rel_parts),
    )


def scan(case_id: str) -> Path:
    """Recorre 00_Input/, escribe _inventory.json y devuelve su ruta."""
    input_dir = caso_path(case_id) / "00_Input"
    if not input_dir.exists():
        raise FileNotFoundError(f"No existe {input_dir}")

    entries: list[FileEntry] = []
    skipped: list[str] = []

    for path in sorted(input_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.name in _CONTROL_FILES:
            continue
        if path.name.startswith("_caso"):
            continue
        if path.suffix.lower() not in _RELEVANT_EXTS:
            skipped.append(path.relative_to(input_dir).as_posix())
            continue
        entries.append(_entry(input_dir, path))

    # Conteo por fuente — útil para observabilidad
    by_source: dict[str, int] = {}
    for e in entries:
        by_source[e.source] = by_source.get(e.source, 0) + 1

    payload = {
        "case_id": case_id,
        "scanned_at": datetime.now().isoformat(timespec="seconds"),
        "count": len(entries),
        "by_source": by_source,
        "skipped": skipped,
        "files": [asdict(e) for e in entries],
    }
    out = input_dir / "_inventory.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def load(case_id: str) -> dict:
    inv = caso_path(case_id) / "00_Input" / "_inventory.json"
    if not inv.exists():
        raise FileNotFoundError(f"Inventario no generado: {inv}")
    return json.loads(inv.read_text(encoding="utf-8"))
