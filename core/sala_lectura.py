"""Sala de lectura de 01_Procesado (F4–F6).

Clasificador/fechador híbrido + copiador organizado + render de índices.
El catálogo `indice_documental.yaml` es la única fuente de verdad. El residuo
ambiguo del clasificador se vuelca a `01_Procesado/_revisar/_clasificar.md`
(worklist) que Claude rellena en sesión leyendo los `MD/` en claro.

Excepción RGPD temporal autorizada por Nikolai (spec
2026-06-17-sala-lectura-f4f6-design.md §2).
"""
from __future__ import annotations

import re
from pathlib import Path

from core.config import TAXONOMIA_EV, UMBRAL_CONFIANZA_AUTOMOVE, caso_path
from core.local_organizer import _exif_o_mtime, _sanitize

# Categoría → tokens del nombre de fichero (orden de prioridad de la tupla).
# Las primeras que casen ganan; el orden de TAXONOMIA fija desempates.
_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("07. RECLAMACIONES", ("burofax", "requerimiento", "reclamacion", "reclamación", "ovc", "incumplimiento")),
    ("05. FACTURACIÓN - FINANZAS", ("factura", "honorarios", "abono", "minuta", "justificante de pago")),
    ("06. PBC", ("dni", "nie", "pasaporte", "nota simple", "titularidad", "pbc", "blanqueo")),
    ("04. ARRAS - ARRENDAMIENTOS", ("arras", "reserva", "señal", "arrendamiento", "alquiler")),
    ("03. OFERTAS", ("oferta", "contraoferta")),
    ("01. ACTIVACIÓN", ("encargo", "captacion", "captación", "exclusiva", "expose", "exposé", "hoja de visita")),
]

_IMG_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".gif", ".bmp", ".tiff", ".tif"}


def _es_imagen(ext: str) -> bool:
    return ext.lower() in _IMG_EXTS


def _categoria_por_nombre(nombre: str) -> str | None:
    low = nombre.lower()
    for categoria, tokens in _KEYWORDS:
        if any(t in low for t in tokens):
            return categoria
    return None
