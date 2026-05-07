"""Módulo de anonimización judicial absorbido desde Expedientes Seguros.

Punto de entrada del módulo. Re-exporta la API pública estable. El resto
del core debe importar desde aquí (no desde los módulos internos).

Estado actual:
    - Fase 1 (núcleo puro): API en memoria + mapa compartido por caso.
    - Fase 2 (separar + OCR + I/O): pipelines no interactivos sobre PDFs.
    - Fase 3 (fachada): ``anonimizar_documento`` / ``anonimizar_caso``
      con I/O sobre carpetas del caso — pendiente.

Nomenclatura del proyecto FeesDefender (importante):
    06_Anonimizado/   ← output del anonimizador (MD limpios + _mapa_caso.json)
    07_AI cowork/     ← logs auxiliares y zona de trabajo con LLMs externos
"""

from core.anon.anonimizar import (
    MapaEntidades,
    anonimizar_texto,
    detectar_nombres_protegidos,
)
from core.anon.api import (
    anonimizar_caso,
    anonimizar_documento,
)
from core.anon.deanonimizar import deanonimizar_texto
from core.anon.exceptions import (
    AnonError,
    DocxVacioError,
    FormatoNoSoportadoError,
    OCRError,
    PDFSinTextoError,
)
from core.anon.imagen_a_pdf import convertir as imagen_a_pdf
from core.anon.mapa_caso import (
    cargar_mapa_caso,
    guardar_mapa_caso,
    ruta_mapa_caso,
)
from core.anon.nlp_engine import warmup as warmup_nlp
from core.anon.ocr import ocr_disponible, ocr_pdf
from core.anon.renombrar import renombrar_carpeta
from core.anon.separar import separar_pdf_pipeline

__all__ = [
    # Fachada de alto nivel (Fase 3) — uso normal del resto del core
    "anonimizar_caso",
    "anonimizar_documento",
    # Anonimización en memoria
    "anonimizar_texto",
    "deanonimizar_texto",
    "MapaEntidades",
    "detectar_nombres_protegidos",
    # Mapa compartido por caso
    "cargar_mapa_caso",
    "guardar_mapa_caso",
    "ruta_mapa_caso",
    # Pipelines I/O (Fase 2)
    "separar_pdf_pipeline",
    "ocr_pdf",
    "ocr_disponible",
    "imagen_a_pdf",
    "renombrar_carpeta",
    "warmup_nlp",
    # Excepciones
    "AnonError",
    "PDFSinTextoError",
    "DocxVacioError",
    "FormatoNoSoportadoError",
    "OCRError",
]
