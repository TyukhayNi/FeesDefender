"""Perfilado por página de un PDF: cuánto texto trae y qué ráster esconde.

SSOT del discriminante de **página ciega** (`docs/MEJORAS_FUTURAS.md` #90): una
página que lleva un escaneo a página completa y, encima, solo una capa de texto
mínima —el pie de firma de LexNET, un sello del juzgado, una cabecera de fax—.
Esa página engaña a `--skip-text` (que la salta entera) y a `ocr_quality` (que
promedia sobre el documento), y el cuerpo escaneado se pierde en silencio.

Tres consumidores comparten este discriminante, y deben compartirlo para no
divergir:

* `scripts/detectar_ocr_ciego` — cribado read-only sobre casos ya procesados.
* `core.anon.ocr.ocr_pdf_escalera` — peldaño 2: qué páginas aislar y re-OCR-izar.
* `core.sala_maquina` — enrutado y calidad por página.

Nada aquí descomprime imágenes: el tamaño del ráster se lee del diccionario del
XObject (`/Width` × `/Height`), que es metadato.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# Un escaneo A4 a 100 dpi ya son ~970k px; por debajo de esto es un logo o una firma.
MIN_PX_RASTER = 600_000
# Por encima de esto la página tiene cuerpo real, no solo un sello.
MAX_CHARS_SELLO = 400

_NORM_RE = re.compile(r"[\W\d_]+", re.UNICODE)


@dataclass(frozen=True)
class PaginaPerfil:
    """Perfil de una página. `numero` es 1-indexed (como lo lee un humano)."""

    numero: int
    chars: int
    raster_px: int
    texto_norm: str = ""   # texto normalizado (recortado): delata la firma repetida


def max_raster_px(pagina) -> int:
    """Píxeles del ráster más grande de la página, SIN descomprimir la imagen."""
    try:
        recursos = pagina.get("/Resources")
        if recursos is None:
            return 0
        xobjects = recursos.get_object().get("/XObject")
        if xobjects is None:
            return 0
        mayor = 0
        for ref in xobjects.get_object().values():
            try:
                obj = ref.get_object()
                if obj.get("/Subtype") == "/Image":
                    mayor = max(mayor, int(obj.get("/Width", 0)) * int(obj.get("/Height", 0)))
            except Exception:
                continue
        return mayor
    except Exception:
        return 0


def perfilar_paginas(pdf: Path) -> list[PaginaPerfil]:
    """Perfil página a página. Lista vacía si el PDF no se puede abrir."""
    try:
        from pypdf import PdfReader
    except ImportError:  # pragma: no cover - dependencia del proyecto
        return []
    try:
        paginas = PdfReader(str(pdf)).pages
    except Exception:
        return []

    perfil: list[PaginaPerfil] = []
    for i, pagina in enumerate(paginas, 1):
        try:
            texto = pagina.extract_text() or ""
        except Exception:
            texto = ""
        perfil.append(PaginaPerfil(
            numero=i,
            chars=len(texto.strip()),
            raster_px=max_raster_px(pagina),
            texto_norm=_NORM_RE.sub("", texto).lower()[:300],
        ))
    return perfil


def tiene_rasteres(pdf: Path, *, min_px: int = MIN_PX_RASTER) -> bool:
    """¿Alguna página lleva un ráster a página completa?

    Gate barato del perfilado: solo lee metadato, sin extraer texto. Un PDF
    nativo (el caso común) no tiene nada ciego que buscar, y así no paga una
    segunda pasada de `extract_text` por página.
    """
    try:
        from pypdf import PdfReader

        return any(max_raster_px(p) >= min_px for p in PdfReader(str(pdf)).pages)
    except Exception:
        return False


def paginas_ciegas(perfil: list[PaginaPerfil], *,
                   max_chars: int = MAX_CHARS_SELLO,
                   min_px: int = MIN_PX_RASTER) -> list[int]:
    """Números (1-indexed) de las páginas con ráster grande y texto de sello."""
    return [p.numero for p in perfil if p.raster_px >= min_px and p.chars < max_chars]


def firmas_repetidas(perfil: list[PaginaPerfil], paginas: list[int]) -> int:
    """Cuántas de `paginas` repiten literalmente el texto de otra: la huella del sello."""
    normas = [perfil[i - 1].texto_norm for i in paginas]
    return sum(1 for n in normas if n and normas.count(n) > 1)


def tiene_acroform(pdf: Path) -> bool:
    """`True` si el PDF trae formulario rellenable — ocrmypdf rechaza `--redo-ocr`."""
    try:
        from pypdf import PdfReader

        raiz = PdfReader(str(pdf)).trailer.get("/Root") or {}
        return "/AcroForm" in raiz
    except Exception:
        return False
