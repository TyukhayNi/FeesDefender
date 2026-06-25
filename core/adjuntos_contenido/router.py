from __future__ import annotations

from pathlib import Path

from core.extractor import ExtractionError, _extract_one

from .model import Extraccion

# Imagen por debajo de este tamaño = probable firma/icono/emoji → omitida.
IMG_DECORATIVA_MAX = 50 * 1024
_EXT_IMAGEN = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff"}
_EXT_OMITIDO = {".emz", ".zip"}


def extraer(ruta: Path, mime: str) -> Extraccion:
    """Enruta un adjunto a extracción de texto, cola de visión u omitido.

    Nunca lanza: un tipo no soportado se marca `omitido`."""
    ext = ruta.suffix.lower()

    # La extensión manda sobre el MIME: un .emz/.zip puede llegar con un
    # image/* engañoso (p. ej. image/x-emf) y debe omitirse, no ir a visión.
    if ext in _EXT_OMITIDO:
        return Extraccion(texto="", metodo="omitido", ok=True, confianza="omitido",
                          motivo=f"tipo no procesado ({ext})")

    if mime.startswith("image/") or ext in _EXT_IMAGEN:
        if ruta.stat().st_size < IMG_DECORATIVA_MAX:
            return Extraccion(texto="", metodo="omitido", ok=True, confianza="omitido",
                              motivo="imagen decorativa (<50KB)")
        return Extraccion(texto="", metodo="vision", ok=True, confianza="por-verificar",
                          vision_estado="pendiente")

    try:
        texto, metodo = _extract_one(ruta)
    except ExtractionError:
        return Extraccion(texto="", metodo="omitido", ok=True, confianza="omitido",
                          motivo=f"sin extractor ({ext})")

    if metodo == "sin_texto" or not texto.strip():
        return Extraccion(texto="", metodo="sin_texto", ok=False, confianza="omitido",
                          motivo="PDF escaneado sin texto / OCR no disponible")

    confianza = "por-verificar" if metodo == "docling" else "alta"
    return Extraccion(texto=texto, metodo=metodo, ok=True, confianza=confianza)
