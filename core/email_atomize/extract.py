"""Capa A (determinista): avistamientos de mensaje atómico desde los .eml.

Cada ``.eml`` aporta su mensaje principal (profundidad 0) + cada ``message/rfc822``
embebido, recursivo a hojas (profundidad 1, 2, …). Reutiliza el rebanado byte-fiel de
``core.email_export``. El dedup por Message-ID y la fusión de procedencias los hace
``dedup.py``; aquí solo se enumeran los avistamientos.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from core.email_export import iter_nested_originals, message_id_of


@dataclass
class Avistamiento:
    raw: bytes
    message_id: str
    eml_origen: str
    profundidad: int
    ruta_anidacion: list[str] = field(default_factory=list)


def _ruta_de(raw: bytes, eml_origen: str) -> dict[str, list[str]]:
    """Mapa Message-ID hijo → cadena de ancestros (Message-IDs), por avistamiento.

    Reconstruye la cadena desde el rebanado recursivo: cada anidado conoce su padre
    inmediato (``iter_nested_originals`` devuelve ``(bytes, parent_mid)``); encadenamos
    por padre hasta la raíz.
    """
    padre_de: dict[str, str] = {}
    for child, parent_mid in iter_nested_originals(raw):
        cmid = message_id_of(child)
        if cmid:
            padre_de[cmid] = parent_mid
    cadenas: dict[str, list[str]] = {}
    for cmid in padre_de:
        cadena: list[str] = []
        cur = padre_de.get(cmid, "")
        visto: set[str] = set()
        while cur and cur not in visto:
            cadena.append(cur)
            visto.add(cur)
            cur = padre_de.get(cur, "")
        cadenas[cmid] = list(reversed(cadena))
    return cadenas


def iter_avistamientos(emails_dir: Path | str) -> Iterator[Avistamiento]:
    base = Path(emails_dir)
    for eml in sorted(base.glob("*.eml")):
        try:
            raw = eml.read_bytes()
        except OSError:
            continue
        yield Avistamiento(
            raw=raw, message_id=message_id_of(raw), eml_origen=eml.name, profundidad=0
        )
        if b"message/rfc822" not in raw:
            continue
        cadenas = _ruta_de(raw, eml.name)
        for child, _parent_mid in iter_nested_originals(raw):
            cmid = message_id_of(child)
            ruta = cadenas.get(cmid, [])
            yield Avistamiento(
                raw=child, message_id=cmid, eml_origen=eml.name,
                profundidad=max(1, len(ruta)), ruta_anidacion=ruta,
            )
