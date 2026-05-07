"""Excepciones del módulo de anonimización.

Sustituyen a los `sys.exit(1)` del Anonimizador original. Permiten que el
orquestador (`core/anon/api.py`) capture errores y degrade elegantemente
en lugar de matar el proceso de Streamlit o el pipeline.
"""


class AnonError(Exception):
    """Error genérico del módulo anon/."""


class PDFSinTextoError(AnonError):
    """El PDF de entrada no tiene capa de texto suficiente.

    Se lanza cuando `extraer_texto_pdf` detecta < 100 caracteres tras
    aplicar todos los filtros (páginas giradas, ratio legibilidad).
    Solución habitual: aplicar OCR previamente con `core.anon.ocr.ocr_pdf`.
    """


class DocxVacioError(AnonError):
    """El DOCX está vacío o solo contiene imágenes."""


class FormatoNoSoportadoError(AnonError):
    """Extensión de archivo no soportada por el extractor."""


class OCRError(AnonError):
    """Fallo no recuperable de ocrmypdf."""
