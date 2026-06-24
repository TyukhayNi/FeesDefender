"""Dedup de avistamientos a mensajes atómicos.

Fase 1: clave de identidad = Message-ID; sin Message-ID, sha256 del raw (cada copia
distinta cuenta como un mensaje — la huella inline llega en Fase 2). Conserva la copia de
MAYOR FIDELIDAD (más bytes = MIME más completo) y registra TODAS las procedencias.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from core.intake_manifest import compute_sha256_bytes
from .extract import Avistamiento


@dataclass
class MensajeColapsado:
    message_id: str
    raw: bytes
    eml_origen: str
    profundidad: int
    ruta_anidacion: list[str]
    procedencia: list[dict] = field(default_factory=list)


def _clave(av: Avistamiento) -> str:
    return av.message_id or "sha256:" + compute_sha256_bytes(av.raw)


def colapsar(avistamientos: list[Avistamiento]) -> list[MensajeColapsado]:
    por_clave: dict[str, MensajeColapsado] = {}
    for av in avistamientos:
        clave = _clave(av)
        proc = {
            "eml_origen": av.eml_origen,
            "profundidad": av.profundidad,
            "ruta_anidacion": list(av.ruta_anidacion),
        }
        existente = por_clave.get(clave)
        if existente is None:
            por_clave[clave] = MensajeColapsado(
                message_id=av.message_id, raw=av.raw, eml_origen=av.eml_origen,
                profundidad=av.profundidad, ruta_anidacion=list(av.ruta_anidacion),
                procedencia=[proc],
            )
            continue
        existente.procedencia.append(proc)
        # mayor fidelidad = más bytes; si gana, también adopta su origen/profundidad/ruta
        if len(av.raw) > len(existente.raw):
            existente.raw = av.raw
            existente.eml_origen = av.eml_origen
            existente.profundidad = av.profundidad
            existente.ruta_anidacion = list(av.ruta_anidacion)
    return list(por_clave.values())
