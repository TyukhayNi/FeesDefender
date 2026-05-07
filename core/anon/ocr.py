"""Wrapper Python sobre OCRmyPDF.

El Anonimizador original invocaba ocrmypdf como subprocess
(``procesar_carpeta.py`` L.164-170, comando exacto: ``python -m ocrmypdf -l
spa+cat+rus --skip-text --deskew --optimize 1 --rotate-pages
--invalidate-digital-signatures``). Aquí usamos la API Python directa
para evitar el coste de ``capture_output=True`` (que bloquea hasta el final
y no emite progreso) y poder propagar excepciones tipadas.

Códigos de retorno relevantes de OCRmyPDF (no documentados en el código del
proyecto origen, vienen de la librería):

* ``0``  éxito.
* ``2``  argumentos inválidos.
* ``6``  PDF ya tenía texto y se usó ``--skip-text`` — esto es ÉXITO en la
         práctica aunque el rc no sea 0.
* ``8``  PDF corrupto / no es PDF.
* ``15`` PDF protegido / cifrado.
* ``16`` PDF firmado digitalmente y no se pasó ``--invalidate-digital-signatures``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from core.anon.exceptions import OCRError


def ocr_pdf(
    ruta_entrada: Path,
    ruta_salida: Path,
    *,
    idiomas: str = "spa+cat+rus",
    redo_ocr: bool = False,
    rotate_pages: bool = True,
    deskew: bool = True,
    optimize: int = 1,
    invalidate_digital_signatures: bool = True,
    on_progress: Callable[[str], None] | None = None,
) -> Path:
    """Aplica OCR a un PDF y devuelve la ruta del PDF resultante.

    Args:
        ruta_entrada: PDF de origen.
        ruta_salida: PDF destino. Si difiere de origen, se crea su carpeta.
        idiomas: Códigos Tesseract separados por ``+``. Default ``spa+cat+rus``
            (cubre el grueso del despacho: español, catalán y ruso).
        redo_ocr: Si ``True``, borra el OCR previo y lo rehace. Útil cuando
            el OCR original es de baja calidad (ej. fax del juzgado).
        rotate_pages: Detecta y corrige páginas giradas durante el OCR.
        deskew: Corrige inclinación de páginas escaneadas.
        optimize: Nivel de optimización del PDF resultante (0-3).
        invalidate_digital_signatures: Sin esto, ocrmypdf rechaza PDFs
            firmados digitalmente con rc=16. Imprescindible para docs
            judiciales firmados.
        on_progress: Callback opcional para reportar progreso en UI.

    Returns:
        Ruta del PDF con OCR aplicado. Si el PDF de origen ya tenía capa
        de texto y ``redo_ocr=False``, devuelve la ruta de origen sin
        copiarla (rc=6 = "no había nada que hacer").

    Raises:
        OCRError: ocrmypdf falla por motivo no recuperable (PDF cifrado,
            corrupto, etc.).
        ImportError: ocrmypdf no instalado en el entorno.
    """
    try:
        import ocrmypdf
    except ImportError as e:
        raise ImportError(
            "ocrmypdf no está instalado. Instálalo con `pip install ocrmypdf`. "
            "Requiere también Tesseract 5.x con paquetes spa, cat, rus."
        ) from e

    ruta_entrada = Path(ruta_entrada)
    ruta_salida = Path(ruta_salida)

    if not ruta_entrada.exists():
        raise OCRError(f"PDF de entrada no existe: {ruta_entrada}")

    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    if on_progress:
        on_progress(f"Iniciando OCR: {ruta_entrada.name}")

    args: dict = {
        "input_file":   str(ruta_entrada),
        "output_file":  str(ruta_salida),
        "language":     idiomas,
        "deskew":       deskew,
        "rotate_pages": rotate_pages,
        "optimize":     optimize,
        "invalidate_digital_signatures": invalidate_digital_signatures,
        "progress_bar": False,
    }
    if redo_ocr:
        args["redo_ocr"] = True
    else:
        args["skip_text"] = True

    try:
        result = ocrmypdf.ocr(**args)
        # ExitCode IntEnum: 0 (OK) y 6 (PRIOR_OCR_FOUND_SKIP) se aceptan
        rc = int(result) if result is not None else 0
        if rc not in (0, 6):
            raise OCRError(f"ocrmypdf terminó con rc={rc}")
        if on_progress:
            on_progress(f"OCR completado: {ruta_salida.name if rc == 0 else ruta_entrada.name}")
        return ruta_salida if rc == 0 else ruta_entrada
    except ocrmypdf.exceptions.PriorOcrFoundError:
        # PDF ya tenía OCR y no se pidió redo → éxito, devolvemos el original
        if on_progress:
            on_progress(f"PDF ya tenía OCR previo: {ruta_entrada.name}")
        return ruta_entrada
    except ocrmypdf.exceptions.EncryptedPdfError as e:
        raise OCRError(f"PDF cifrado: {ruta_entrada.name}") from e
    except ocrmypdf.exceptions.InputFileError as e:
        raise OCRError(f"PDF inválido: {ruta_entrada.name} ({e})") from e
    except OCRError:
        raise
    except Exception as e:
        raise OCRError(f"Fallo no recuperable de ocrmypdf: {e}") from e


def ocr_disponible() -> bool:
    """``True`` si ocrmypdf está instalado en el entorno actual."""
    try:
        import ocrmypdf  # noqa: F401
    except ImportError:
        return False
    return True
