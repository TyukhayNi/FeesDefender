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
    fuente: str = ""


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
                procedencia=[proc], fuente=av.fuente,
            )
            continue
        existente.procedencia.append(proc)
        if _desplaza(av, existente):
            existente.raw = av.raw
            existente.eml_origen = av.eml_origen
            existente.profundidad = av.profundidad
            existente.ruta_anidacion = list(av.ruta_anidacion)
            existente.fuente = av.fuente
    return list(por_clave.values())


def _hondura(origen: str) -> int:
    """Cuántas carpetas por debajo de la fuente vive el `.eml` (0 = nivel superior).

    OJO: es la hondura de la RUTA, no `Avistamiento.profundidad`, que cuenta anidamiento
    MIME (`message/rfc822`). Son dos cosas distintas y aquí decide la primera.
    """
    return origen.count("/")


def _desplaza(av: Avistamiento, existente: MensajeColapsado) -> bool:
    """¿`av` debe sustituir al canónico actual?

    Fidelidad primero: más bytes = MIME más completo (regla original, intacta). A
    IGUALDAD de bytes solo desplaza si `av` está **estrictamente menos enterrado**: la
    copia de nivel superior gana a la de subcarpeta, y si están a la misma hondura NO se
    desplaza — se queda el primero que llegó, exactamente como hoy.

    Por qué así y no comparando rutas: comparar cadenas movería canónicos existentes por
    dos vías verificadas. (1) El orden de enumeración solo está garantizado DENTRO de cada
    fuente; el pipeline concatena fuentes en el orden recibido, así que la secuencia global
    de orígenes no es monótona. (2) En Windows `sorted(Path)` y `sorted(str)` discrepan con
    mayúsculas (`a.eml` vs `Z.eml`). Al decidir solo por hondura, en todo caso actual
    —donde no hay ni un `.eml` en subcarpeta, luego todas las honduras son 0— el resultado
    es idéntico al de hoy por construcción, y el layout mixto queda determinista (spec §4.2).
    """
    if len(av.raw) != len(existente.raw):
        return len(av.raw) > len(existente.raw)
    return _hondura(av.eml_origen) < _hondura(existente.eml_origen)
