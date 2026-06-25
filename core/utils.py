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


def output_slug(rel_path: str, sha256: str = "") -> str:
    """Nombre de salida (sin extensión) libre de colisiones para `raw_text/`/`MD/`.

    El slug del *stem* solo no basta: dos documentos distintos con el mismo
    nombre base (p. ej. los `_chat.txt` de varias conversaciones de WhatsApp)
    colapsan al mismo fichero y se pisan en silencio (#47). Se sufija con los
    primeros 8 caracteres del SHA-256 del origen: distinto contenido → nombre
    distinto; copias byte-idénticas (mismo SHA) → mismo nombre (dedup
    deliberado). Sin SHA, degrada al slug del stem (compatibilidad)."""
    stem_slug = slugify(Path(rel_path).stem)
    if not sha256:
        return stem_slug
    return f"{stem_slug}__{sha256[:8]}"


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


# Formato nuevo descompuesto en grupos, para neutralizar el segmento de
# dirección (el único tramo con PII). El prefijo, la referencia y la categoría
# son estructurales y no se tocan. La dirección es todo lo que va entre
# "<prefijo> - " y la referencia "(W-XXXXXX)"/"(SIN REFERENCIA)" (captura
# perezosa: el primer paréntesis de referencia cierra el tramo).
_CASE_ID_NEW_PARTES = re.compile(
    r"^(?P<prefijo>[A-Z][a-zA-Z][A-Z]{2}\d+)\s+-\s+"
    r"(?P<direccion>.+?)\s*"
    r"(?P<ref>\((?:W-[A-Z0-9]+|SIN\s+REFERENCIA)\))\s+-\s+"
    r"(?P<categoria>.+)$"
)


def neutralizar_case_id(case_id: str) -> str:
    """Sustituye el segmento de dirección del ``case_id`` por ``[DIRECCION]``.

    El ``case_id`` del despacho (formato nuevo
    ``<prefijo> - <dirección> (<ref>) - <categoría>``) lleva incrustado el
    domicilio literal del caso. Ese valor viaja en el frontmatter de los ``.md``
    de ``06_Anonimizado/``, que pueden entregarse a un LLM externo (flujo H6):
    sin esta neutralización, el modelo leería la dirección PII como contexto,
    rompiendo el pilar de confidencialidad del proyecto (MEJORAS_FUTURAS.md §23).

    Conserva prefijo, referencia y categoría (no son PII) y la estructura, de
    modo que el resultado sigue siendo un ``case_id`` válido para
    ``validate_case_id``. El formato heredado (``EV-2026-001``) o cualquier
    cadena no reconocida se devuelve sin tocar (no contienen dirección).
    """
    if not case_id:
        return case_id
    m = _CASE_ID_NEW_PARTES.match(case_id.strip())
    if not m:
        return case_id
    return (
        f"{m.group('prefijo')} - [DIRECCION] "
        f"{m.group('ref')} - {m.group('categoria')}"
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
