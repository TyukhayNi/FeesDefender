"""Utilidades transversales: hashing, slugify, frontmatter YAML, lectura segura."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from slugify import slugify as _slugify


def file_sha256(path: Path, chunk_size: int = 65536) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def slugify(value: str, max_length: int = 80) -> str:
    """Slugify amigable para nombres de archivo Markdown."""
    return _slugify(value, max_length=max_length, lowercase=True, separator="_")


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


# Caracteres prohibidos en rutas de Windows
_WIN_FORBIDDEN = re.compile(r'[\\/:*?"<>|]')

# Formato nuevo: BaRR3 - Dirección (W-XXXXXX) - Tipo
# Categoría OTROS no proviene de captación inmobiliaria → su referencia es
# "(SIN REFERENCIA)" en lugar de "(W-XXXXXX)". Ver MEJORAS_FUTURAS.md §12.
# Formato heredado (tests/desarrollo): EV-2026-001
_CASE_ID_NEW = re.compile(
    r"^[A-Z][a-zA-Z][A-Z]{2}\d+\s+-\s+.+"
    r"\((?:W-[A-Z0-9]+|SIN\s+REFERENCIA)\)"
    r"\s+-\s+.+$"
)
_CASE_ID_LEGACY = re.compile(r"^[A-Z]{2,6}-\d{4}-\d{3}$")


def validate_case_id(case_id: str) -> str:
    """Valida y devuelve el case_id. Lanza ValueError si no es válido.

    Formatos aceptados:
      · Nuevo:    BaRR3 - Dirección, nº (W-030LFT) - Art 20 LAU
      · Heredado: EV-2026-001  (para tests y casos de desarrollo)
    """
    if not case_id or not case_id.strip():
        raise ValueError("El case_id no puede estar vacío.")
    if _WIN_FORBIDDEN.search(case_id):
        raise ValueError(
            f"El case_id contiene caracteres no permitidos en rutas Windows "
            f"(\\ / : * ? \" < > |): {case_id!r}"
        )
    case_id = case_id.strip()
    if _CASE_ID_NEW.match(case_id) or _CASE_ID_LEGACY.match(case_id):
        return case_id
    raise ValueError(
        f"Formato de case_id no reconocido: {case_id!r}\n"
        f"Usa el formato CRM: 'BaRR3 - Calle Nº (W-XXXXXX) - Art XX LAU'\n"
        f"o el formato heredado: 'EV-2026-001'"
    )


# --- Frontmatter ------------------------------------------------------------

_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def build_frontmatter(meta: dict[str, Any]) -> str:
    body = yaml.safe_dump(
        meta,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    ).strip()
    return f"---\n{body}\n---\n"


def write_md(path: Path, meta: dict[str, Any], body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = build_frontmatter(meta) + "\n" + body.strip() + "\n"
    path.write_text(content, encoding="utf-8")
    return path


def read_md(path: Path) -> tuple[dict[str, Any], str]:
    """Devuelve (frontmatter, cuerpo). Si no hay frontmatter, devuelve ({}, texto)."""
    text = path.read_text(encoding="utf-8")
    m = _FM_RE.match(text)
    if not m:
        return {}, text
    meta = yaml.safe_load(m.group(1)) or {}
    body = text[m.end():]
    return meta, body
