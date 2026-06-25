"""Fase 2 de contenido de adjuntos: extracción de texto fiel + cola de resumen/visión."""
from __future__ import annotations

from .model import AdjuntoDescubierto, ContenidoReport, Extraccion
from .pipeline import procesar_caso, procesar_dir
from .resumen import Resumidor, ResumidorNoop, aplicar_resumenes, aplicar_resumenes_dir

__all__ = [
    "AdjuntoDescubierto", "ContenidoReport", "Extraccion",
    "procesar_caso", "procesar_dir",
    "Resumidor", "ResumidorNoop", "aplicar_resumenes", "aplicar_resumenes_dir",
]
