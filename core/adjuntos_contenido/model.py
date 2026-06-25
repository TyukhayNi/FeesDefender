from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AdjuntoDescubierto:
    att_id: str
    sha256: str
    tipo: str
    nombre_original: str
    mensajes: list[str]
    base: str
    ruta_binario: Path
    ruta_sidecar: Path


@dataclass
class Extraccion:
    texto: str
    metodo: str
    ok: bool
    confianza: str
    vision_estado: str = "n/a"
    motivo: str = ""


@dataclass
class ContenidoReport:
    extraidos: int = 0
    omitidos: int = 0
    sin_texto: int = 0
    saltados: int = 0
    podados: int = 0
    pendientes_resumen: int = 0
    pendientes_vision: int = 0
    errores: list[str] = field(default_factory=list)
