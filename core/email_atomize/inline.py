"""Layer B — reconstrucción de autoría enterrada en reenvíos/citas INLINE.

Diseño detallado y aprobado en ``docs/superpowers/specs/2026-06-25-email-atomize-layerb-design.md``.
Directriz primaria: **cero misatribución** — un remitente se afirma solo desde un bloque de
cabecera inline parseable; todo lo más débil va a la cola de revisión. Módulo puro (sin I/O).
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field

from core.email_export import _slug_descripcion

# Identidades vigiladas (hook Fase 3; vacío en Fase 2 = no-op). Para identidades.yaml:
#   PersonaUno = {per01a@example.invalid, per01c@example.invalid}; per01b@example.invalid = CANDIDATO (tope media,
#   no se confirma aquí); ignacio@despacho-ab.example = parte relacionada, persona DISTINTA.
IDENTIDADES_VIGILADAS: set[str] = set()

_MIN_CUERPO = 24   # cuerpos normalizados < 24 chars nunca dirigen colapso/upgrade


@dataclass
class Anclaje:
    de: str = ""
    de_nombre: str = ""
    fecha_iso: str = "0000-00-00"
    fecha_dt: object | None = None
    asunto: str = ""


# ---------------------------------------------------------------------------
# Normalizador único + fingerprint (DD §5)
# ---------------------------------------------------------------------------

_RE_QUOTE_MARK = re.compile(r"(?m)^\s*>+\s?")
_RE_SIG = re.compile(
    r"(?im)^(?:--\s?$|enviado desde mi.*|sent from my.*|obtener outlook.*|get outlook.*)"
)
_RE_WS = re.compile(r"\s+")


def normaliza_cuerpo(texto: str) -> str:
    """El ÚNICO normalizador de cuerpo (lo usan fingerprint_a y fingerprint_b)."""
    t = _RE_QUOTE_MARK.sub("", texto or "")
    m = _RE_SIG.search(t)
    if m:
        t = t[: m.start()]
    t = _RE_WS.sub(" ", t)
    t = unicodedata.normalize("NFKC", t).casefold()
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode("ascii")
    return t.strip()


def es_cuerpo_colapsable(cuerpo_norm: str) -> bool:
    """Solo cuerpos con sustancia (≥24 chars) pueden dirigir colapso/upgrade de fidelidad."""
    return len(cuerpo_norm) >= _MIN_CUERPO


def _material(remitente: str, fecha_iso: str, asunto: str, cuerpo_norm: str) -> str:
    fecha_dia = fecha_iso if fecha_iso and fecha_iso != "0000-00-00" else ""
    cuerpo_sha = hashlib.sha256(cuerpo_norm.encode("utf-8")).hexdigest()
    return "\x1f".join([(remitente or "").strip().lower(), fecha_dia,
                        _slug_descripcion(asunto or ""), cuerpo_sha])


def fingerprint_b(anc: Anclaje | None, cuerpo_norm: str) -> str:
    """Identidad de contenido de un segmento citado. Día-granular (absorbe jitter tz)."""
    remitente = anc.de if anc else ""
    fecha = anc.fecha_iso if anc else "0000-00-00"
    asunto = anc.asunto if anc else ""
    material = _material(remitente, fecha, asunto, cuerpo_norm)
    return "fp:" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


def fingerprint_a(m) -> str:
    """Mismo algoritmo sobre un mensaje de Capa A (para el puente del upgrade)."""
    material = _material(m.de, m.fecha_iso, m.asunto, normaliza_cuerpo(m.cuerpo))
    return "fp:" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


def cuerpo_sha_de(cuerpo_norm: str) -> str:
    return hashlib.sha256(cuerpo_norm.encode("utf-8")).hexdigest()
