"""Adjuntos: dedup por sha256 (contenido, no nombre) + filtro decorativo + ficha.

Decorativo (no se indexa, queda embebido en el .eml): imagen recurrente (mismo sha en
muchos mensajes = logo/firma) Y pequeña. Único + sustancial → adjunto con ficha.
"""
from __future__ import annotations

from collections import Counter

from core.email_export import split_eml
from core.intake_manifest import compute_sha256_bytes

_FIRMA_MAX_BYTES = 50 * 1024
_RECURRENCIA_MIN = 5


def _sha(data: bytes) -> str:
    return compute_sha256_bytes(data)


def contar_apariciones(raws: list[bytes]) -> Counter:
    """Cuenta, sobre todos los mensajes, cuántas veces aparece cada sha256 de adjunto."""
    cont: Counter = Counter()
    for raw in raws:
        _eml, adjuntos = split_eml(raw)
        for _fn, _mime, data in adjuntos:
            cont[_sha(data)] += 1
    return cont


def es_decorativo(data: bytes, mime: str, apariciones: dict) -> bool:
    if not mime.startswith("image/"):
        return False
    recurrente = apariciones.get(_sha(data), 0) >= _RECURRENCIA_MIN
    pequena = len(data) < _FIRMA_MAX_BYTES
    return recurrente and pequena
