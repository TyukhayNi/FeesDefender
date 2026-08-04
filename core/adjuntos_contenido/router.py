from __future__ import annotations

from pathlib import Path

from core import extractor
from core.extractor import _extract_one

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

    # PDF → el motor de la SALA DE MÁQUINA, no el extractor viejo (`MEJORAS #87`). Antes
    # bajaba por `_extract_one`: pypdf, y Docling solo si ≤30 páginas, así que un
    # escaneado largo daba `sin_texto` (cero texto) y uno con pie de LexNET salía por
    # pypdf con el cuerpo perdido. Import perezoso: `sala_maquina` arrastra el split y el
    # log, y no hace falta para un `.docx`.
    if ext == ".pdf" or mime == "application/pdf":
        from core.sala_maquina import texto_de_pdf
        r = texto_de_pdf(ruta)
        if not r.texto.strip():
            return Extraccion(texto="", metodo="sin_texto", ok=False, confianza="omitido",
                              motivo=r.nota or "PDF sin texto recuperable")
        # La confianza sale de la CALIDAD, no del nombre del motor. Con la regla vieja
        # (`alta` si no fue Docling) un escaneado con el cuerpo perdido se etiquetaba
        # `alta`: la etiqueta mentía justo en el caso de `MEJORAS #90`.
        return Extraccion(texto=r.texto, metodo=r.metodo, ok=True,
                          confianza="alta" if r.estado == "ok" else "por-verificar",
                          motivo=r.nota, ocr=r.ocr)

    try:
        texto, metodo = _extract_one(ruta)
    # Cualificado por módulo (no `from ... import ExtractionError`): si un test recarga
    # `core.extractor` (importlib.reload), la clase capturada debe ser la vigente, no
    # una referencia vieja atada al importar — si no, la excepción se escaparía.
    except extractor.ExtractionError:
        return Extraccion(texto="", metodo="omitido", ok=True, confianza="omitido",
                          motivo=f"sin extractor ({ext})")

    if metodo == "sin_texto" or not texto.strip():
        return Extraccion(texto="", metodo="sin_texto", ok=False, confianza="omitido",
                          motivo="PDF escaneado sin texto / OCR no disponible")

    confianza = "por-verificar" if metodo == "docling" else "alta"
    return Extraccion(texto=texto, metodo=metodo, ok=True, confianza=confianza)
