"""Utilidades transversales: hashing, slugify, frontmatter YAML, lectura segura."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
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


_TEL_SEPARADORES = re.compile(r"[\s.\-/()]+")


def normalize_es_phone(raw: str) -> str:
    """Normaliza un teléfono español a 9 dígitos para el CRM sudespacho.

    El CRM rechaza `+34`, `0034` y espacios (`HTTP 400 movil is incorrect`);
    hay que enviar solo los 9 dígitos. Conservador: quita separadores y el
    prefijo de país español, pero NO valida longitud (eso lo hace el CRM) ni
    toca números extranjeros (`+33…` se dejan intactos salvo separadores).

    Idempotente: ``normalize_es_phone(normalize_es_phone(x)) == normalize_es_phone(x)``.
    """
    if not raw:
        return raw
    s = _TEL_SEPARADORES.sub("", raw)
    if s.startswith("+34"):
        s = s[3:]
    elif s.startswith("0034"):
        s = s[4:]
    elif s.startswith("34") and len(s) == 11:
        s = s[2:]
    return s


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


def now_iso_utc() -> str:
    """Timestamp ISO-8601 en UTC con sufijo ``Z`` (p. ej. ``2026-07-07T09:45:12Z``).

    El sistema de biblioteca (checkout/checkin) exige timestamps completos con
    zona para nombrar artefactos sin colisión intra-día y para el lock
    (DISEÑO_V2 §8). ``now_iso()`` (naïve, hora local) se mantiene para el resto
    del proyecto; este helper es el que usan el protocolo y los nombres de
    ``AUDITLOG_MERGE_*``, ``_snapshot/*`` y ``MANIFEST_BORRADO_*``.
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ts_compacto(iso_utc: str | None = None) -> str:
    """Compacta un timestamp ISO-UTC a ``AAAA-MM-DDTHHMMZ`` para nombres de fichero.

    Windows no admite ``:`` en nombres de fichero, así que los artefactos con
    marca temporal (``AUDITLOG_MERGE_<TS>.jsonl``, ``_snapshot/<TS>/``) usan la
    forma compacta sin segundos-con-dos-puntos. Si no se pasa ``iso_utc`` usa el
    instante actual.
    """
    src = iso_utc or now_iso_utc()
    # "2026-07-07T09:45:12Z" -> "2026-07-07T0945Z"
    fecha, _, resto = src.partition("T")
    hora = resto.rstrip("Z").replace(":", "")
    hhmm = hora[:4] if len(hora) >= 4 else hora
    return f"{fecha}T{hhmm}Z"


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


def exigir_sin_caracteres_de_ruta(valor: str, *, campo: str) -> str:
    """Devuelve `valor` si puede ser un nombre de carpeta; si no, lanza `ValueError`.

    Es la mitad de `validate_case_id` que **no** habla de formato canónico, extraída para
    que la use quien compone un `case_id` a partir de campos del usuario (`MEJORAS #148`).
    Se separó a propósito: la guarda que hacía falta era la de la **gramática de rutas**, y
    exigir además el formato canónico rompía cinco fixtures con códigos sintéticos
    (`BaTEST`) — una guarda más ancha que el defecto medido.
    """
    if _WIN_FORBIDDEN.search(valor or ""):
        raise ValueError(
            f"{campo} contiene caracteres que no pueden estar en una carpeta de Windows "
            f'(\\ / : * ? " < > |): {valor!r}. Un `/` se comporta como separador de rutas '
            "y partiría el expediente en dos carpetas anidadas."
        )
    return valor


def exigir_componente_de_ruta(valor: str, *, campo: str) -> str:
    """Devuelve `valor` si puede ser **un** componente de carpeta; si no, lanza `ValueError`.

    Es la gramática de rutas completa, y se compone sobre
    `exigir_sin_caracteres_de_ruta` en vez de duplicarla: **no vacío**, sin
    `\\ / : * ? " < > |`, y no `.` ni `..`.

    **El «no vacío» está aquí por un hallazgo de la R1 adversarial (H-02).** El 2026-09-04
    extraje `exigir_sin_caracteres_de_ruta` de `validate_case_id` y **dejé atrás su
    comprobación de vacío**, que sigue abajo en esta misma función. Reutilizar solo la mitad
    extraída hacía que `ensure_case("")` pasara toda la validación —`buscar("")` devuelve la
    propia raíz y `is_relative_to` incluye la igualdad— y **convirtiera `CASOS_ROOT` en un
    expediente**, con sus nueve subcarpetas y su `_caso.md` dentro. Una extracción parcial
    que perdió una propiedad, y el sitio donde se recupera es este.

    Lo que NO comprueba: el formato canónico del `case_id`. Eso se midió el 2026-09-04 como
    una guarda **más ancha que el defecto** — rompió cinco fixtures con códigos sintéticos.
    """
    if not (valor or "").strip():
        raise ValueError(f"{campo} no puede estar vacío.")
    exigir_sin_caracteres_de_ruta(valor, campo=campo)
    if valor.strip() in (".", ".."):
        raise ValueError(
            f"{campo} no puede ser {valor.strip()!r}: no nombra una carpeta, "
            "nombra una posición relativa.")
    return valor


def validate_case_id(case_id: str) -> str:
    """Valida y devuelve el case_id. Lanza ValueError si no es válido.

    Formatos aceptados:
      · Nuevo:    BaRR3 - Dirección, nº (W-030LFT) - Art 20 LAU
      · Heredado: EV-2026-001  (para tests y casos de desarrollo)
    """
    if not case_id or not case_id.strip():
        raise ValueError("El case_id no puede estar vacío.")
    exigir_sin_caracteres_de_ruta(case_id, campo="El case_id")
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
