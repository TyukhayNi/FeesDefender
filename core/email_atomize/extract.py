"""Capa A (determinista): avistamientos de mensaje atómico desde los .eml.

Cada ``.eml`` aporta su mensaje principal (profundidad 0) + cada ``message/rfc822``
embebido, recursivo a hojas (profundidad 1, 2, …). Reutiliza el rebanado byte-fiel de
``core.email_export``. El dedup por Message-ID y la fusión de procedencias los hace
``dedup.py``; aquí solo se enumeran los avistamientos.
"""
from __future__ import annotations

import os
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
    fuente: str = ""


@dataclass
class EnumStats:
    """Lo que la enumeración enumeró, leyó y no pudo leer (spec §4.3).

    `fallos` mezcla a propósito fichero-ilegible y directorio-ilegible: los dos son
    fallos TRANSITORIOS de la misma clase (sobre `G:` casi siempre es Drive sin
    hidratar) y los dos hacen incompleta la foto, que es lo que gobierna la decisión de
    publicar.
    """
    enumerados: int = 0
    leidos: int = 0
    fallos: list[str] = field(default_factory=list)


def enumerar_rutas_eml(base: Path | str, stats: EnumStats | None = None) -> list[Path]:
    """Rutas de los `.eml` bajo *base*, RECURSIVO y en orden determinista.

    Recursivo desde `MEJORAS #98`: `--extraer-adjuntos` deja el `.eml` de todo mensaje
    con adjuntos en una subcarpeta, y con `glob` esos mensajes eran invisibles sin error.

    Se usa `os.walk(onerror=...)` y no `Path.rglob` porque `rglob` **silencia** los
    errores de directorio: un directorio ilegible desaparecería igual que antes
    desaparecían las subcarpetas. Sensible a mayúsculas (`.eml`, no `.EML`) a propósito:
    el conteo del CLI mide lo mismo que esto, y los dos han de coincidir.
    """
    base = Path(base)

    def _onerror(exc: OSError) -> None:
        if stats is not None:
            stats.fallos.append(f"{getattr(exc, 'filename', base)}: {exc}")

    rutas: list[Path] = []
    for dirpath, _dirnames, filenames in os.walk(base, onerror=_onerror):
        d = Path(dirpath)
        rutas.extend(d / n for n in filenames if n.endswith(".eml"))
    return sorted(rutas)


def _ruta_de(raw: bytes) -> dict[str, list[str]]:
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


def iter_avistamientos(emails_dir: Path | str, *,
                       stats: EnumStats | None = None) -> Iterator[Avistamiento]:
    base = Path(emails_dir)
    for eml in enumerar_rutas_eml(base, stats):
        if stats is not None:
            stats.enumerados += 1
        try:
            raw = eml.read_bytes()
        except OSError as exc:
            # NO se traga en silencio (spec §1.3): un .eml presente pero ilegible hacía
            # que el motor viera menos mensajes de los que hay y su poda borrara fichas
            # cuyo mensaje no había desaparecido.
            if stats is not None:
                stats.fallos.append(f"{eml.relative_to(base).as_posix()}: {exc}")
            continue
        if stats is not None:
            stats.leidos += 1
        # Ruta relativa, no `eml.name`: con subcarpetas el nombre deja de ser único.
        # POSIX para que el valor sea estable entre máquinas (se persiste en el
        # frontmatter y en `_registro.json`). Para un .eml de nivel superior la ruta
        # relativa ES el nombre → byte-identidad de todo lo existente (spec §4.2).
        origen = eml.relative_to(base).as_posix()
        yield Avistamiento(
            raw=raw, message_id=message_id_of(raw), eml_origen=origen, profundidad=0,
            fuente=base.name,
        )
        if b"message/rfc822" not in raw:
            continue
        cadenas = _ruta_de(raw)
        for child, _parent_mid in iter_nested_originals(raw):
            cmid = message_id_of(child)
            ruta = cadenas.get(cmid, [])
            yield Avistamiento(
                raw=child, message_id=cmid, eml_origen=origen,
                profundidad=max(1, len(ruta)), ruta_anidacion=ruta, fuente=base.name,
            )
