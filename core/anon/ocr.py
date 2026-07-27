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

import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from core.anon.exceptions import OCRError
from core.pdf_paginas import paginas_ciegas, perfilar_paginas


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

    # La API de ocrmypdf exige el input como primer argumento POSICIONAL
    # (`input_file_or_options`), no como kwarg; y `language` espera un iterable
    # de códigos (`["spa", "cat", "rus"]`), no la cadena "spa+cat+rus" (un str
    # se iteraría por caracteres). Ver docs/MEJORAS_FUTURAS.md §11.
    args: dict = {
        "language":     idiomas.split("+"),
        "deskew":       deskew,
        "rotate_pages": rotate_pages,
        "optimize":     optimize,
        "invalidate_digital_signatures": invalidate_digital_signatures,
        "progress_bar": False,
    }
    if redo_ocr:
        args["redo_ocr"] = True
        # ocrmypdf 17.x: "--redo-ocr is not currently compatible with --deskew,
        # --clean-final and --remove-background". Con el default `deskew=True`, el
        # modo redo reventaba en la validación de opciones antes de OCR-izar nada
        # — la segunda razón por la que era inalcanzable (MEJORAS #90).
        args["deskew"] = False
    else:
        args["skip_text"] = True

    try:
        result = ocrmypdf.ocr(str(ruta_entrada), str(ruta_salida), **args)
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


@dataclass
class ResultadoEscalera:
    """Qué peldaño resolvió el documento y si quedó texto ciego sin recuperar.

    `degradado=True` es el contrato con el llamador: se detectó texto escondido
    bajo un ráster y NO se pudo sacar. El documento debe marcarse ``low`` —
    nunca ``ok``— para que entre en la worklist de `_cobertura.md` y en el filtro
    de `reforzar`. Ese silencio es justo el fallo de `MEJORAS #90`.
    """

    ruta: Path
    peldano: str                                   # redo | paginas | sin_paginas_ciegas | fallido
    paginas_ocr: tuple[int, ...] = ()
    paginas_fallidas: tuple[int, ...] = ()
    degradado: bool = False
    nota: str = ""
    opciones: dict = field(default_factory=dict)


_ACROFORM_MARCA = "user fillable form"


def _es_cifrado(e: Exception) -> bool:
    """El PDF está cifrado: ningún peldaño lo abrirá. No insistir por página."""
    causa = type(e.__cause__).__name__ if e.__cause__ is not None else ""
    return "Encrypted" in causa or str(e).startswith("PDF cifrado")


def ocr_pdf_escalera(
    ruta_entrada: Path,
    ruta_salida: Path,
    *,
    conservador: bool = False,
    idiomas: str = "spa+cat+rus",
    on_progress: Callable[[str], None] | None = None,
    **opciones,
) -> ResultadoEscalera:
    """Escalera de OCR con degradación explícita (`docs/MEJORAS_FUTURAS.md` #90).

    El default histórico (``--skip-text``) salta la página entera en cuanto
    encuentra un objeto de texto: un escaneo con el pie de firma de LexNET encima
    pierde todo el cuerpo y, como el sello aporta caracteres, nadie lo nota.
    Cambiar la bandera no basta: los PDFs **AcroForm** (cuentas anuales del
    Registro, tasaciones) hacen que ocrmypdf **rechace** ``--redo-ocr``
    (*"This PDF has a user fillable form"*). De ahí la escalera:

    1. ``--redo-ocr`` sobre el documento entero.
    2. Si falla: aislar cada página ciega con pypdf —extraerla **quita el
       AcroForm**, que era el bloqueo— OCR-izarla con ``--redo-ocr`` y recomponer
       el documento. Las páginas no ciegas se copian sin reescribir su contenido.
    3. Si nada funciona: ``degradado=True``. Nunca ``--force-ocr``, que destruye
       la capa de texto real (abandonado tras VALERO, bitácora 2026-07-14).

    Validada a mano sobre 7 documentos de 3 casos antes de codificarla; en
    ninguno hizo falta el modo destructivo (ver `PLAN.md` [SIGUIENTE-OCR-CIEGO]).

    Args:
        conservador: Empieza directamente en el peldaño 2. Para documentos que
            YA traen capa de texto real: el peldaño 1 es aditivo (no pierde
            palabras) pero reescribe el texto de algunas páginas digitales, y
            donde las cifras son críticas eso no compensa.
        **opciones: se pasan tal cual a `ocr_pdf` (``deskew``, ``optimize``…).

    Raises:
        OCRError: el PDF no es procesable por ningún peldaño (cifrado, corrupto).
            Se propaga a propósito: es lo que activa la red de `--vision`.
    """
    entrada, salida = Path(ruta_entrada), Path(ruta_salida)
    comunes = dict(idiomas=idiomas, on_progress=on_progress, **opciones)
    perfil = perfilar_paginas(entrada)

    if conservador:
        motivo = "capa de texto real: se fuerza el peldaño 2 (no reescribe las páginas digitales)"
    else:
        try:
            devuelta = Path(ocr_pdf(entrada, salida, redo_ocr=_exige_redo(perfil), **comunes))
        except OCRError as e:
            if _es_cifrado(e):
                raise
            motivo = f"peldaño 1 (--redo-ocr) falló: {e}"
            if _ACROFORM_MARCA in str(e):
                motivo = "peldaño 1 (--redo-ocr) rechazado por AcroForm"
        else:
            if devuelta == salida and salida.exists():
                return ResultadoEscalera(salida, "redo", opciones=comunes)
            # rc=6 / PriorOcrFound: no hubo artefacto, así que tampoco recuperación.
            motivo = "peldaño 1 no regeneró el PDF (OCR previo detectado)"

    return _peldano_paginas(entrada, salida, motivo, perfil,
                            conservador=conservador, **comunes)


def _exige_redo(perfil: list) -> bool:
    """¿Hace falta el modo redo, o basta el `--skip-text` de siempre?

    Sin una sola letra embebida no hay nada que «rehacer»: los dos modos dan el
    mismo resultado, pero `--skip-text` conserva `--deskew` —que endereza el
    escaneo y mejora el reconocimiento— y el modo redo lo prohíbe. Así el cambio
    de motor no le cuesta calidad al escaneo limpio, que es el caso mayoritario:
    solo paga el peaje el documento que trae texto encima.
    """
    return any(p.chars > 0 for p in perfil)


def _peldano_paginas(entrada: Path, salida: Path, motivo: str,
                     perfil: list, *, conservador: bool,
                     on_progress=None, **comunes) -> ResultadoEscalera:
    """Peldaño 2: aísla las páginas ciegas, las OCR-iza y recompone el documento."""
    from pypdf import PdfReader, PdfWriter

    if not perfil:
        raise OCRError(f"ningún peldaño pudo procesar {entrada.name}; {motivo}")

    ciegas = paginas_ciegas(perfil)
    if not ciegas:
        # Nada que rescatar por esta vía. Si veníamos de un escaneado (no
        # conservador) el peldaño 1 falló y no hemos producido texto: eso sí es
        # degradación. Si el documento ya traía capa de texto, no lo es.
        return ResultadoEscalera(entrada, "sin_paginas_ciegas", degradado=not conservador,
                                 nota=f"sin páginas ciegas que aislar; {motivo}", opciones=comunes)

    lector = PdfReader(str(entrada))
    recuperadas: dict[int, object] = {}
    fallidas: list[int] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        for n in ciegas:
            suelta = tmpdir / f"{entrada.stem}__p{n}.pdf"
            escrita = tmpdir / f"{entrada.stem}__p{n}__ocr.pdf"
            try:
                w = PdfWriter()                       # writer nuevo = sin /AcroForm
                w.add_page(lector.pages[n - 1])
                with suelta.open("wb") as fh:
                    w.write(fh)
                if on_progress:
                    on_progress(f"OCR de la página ciega {n}: {entrada.name}")
                devuelta = Path(ocr_pdf(suelta, escrita, on_progress=on_progress,
                                        redo_ocr=_exige_redo([perfil[n - 1]]), **comunes))
                if devuelta != escrita or not escrita.exists():
                    raise OCRError("la página aislada no produjo PDF nuevo")
                recuperadas[n] = PdfReader(str(escrita)).pages[0]
            except Exception:
                fallidas.append(n)

        if not recuperadas:
            return ResultadoEscalera(entrada, "fallido", paginas_fallidas=tuple(fallidas),
                                     degradado=True, opciones=comunes,
                                     nota=(f"texto ciego NO recuperado en {len(fallidas)} "
                                           f"página(s); {motivo}"))

        salida.parent.mkdir(parents=True, exist_ok=True)
        escritor = PdfWriter()
        for i, pagina in enumerate(lector.pages, 1):
            escritor.add_page(recuperadas.get(i, pagina))
        with salida.open("wb") as fh:
            escritor.write(fh)

    nota = f"peldaño 2: {len(recuperadas)} página(s) ciega(s) re-OCR-izadas aparte; {motivo}"
    if fallidas:
        nota += f" · sin recuperar: {', '.join(str(n) for n in fallidas)}"
    return ResultadoEscalera(salida, "paginas", tuple(sorted(recuperadas)), tuple(fallidas),
                             degradado=bool(fallidas), nota=nota, opciones=comunes)


def ocr_disponible() -> bool:
    """``True`` si ocrmypdf está instalado en el entorno actual."""
    try:
        import ocrmypdf  # noqa: F401
    except ImportError:
        return False
    return True
