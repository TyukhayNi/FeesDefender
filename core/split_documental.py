"""Cerebro del split de bundles multi-documento en la Sala de máquina.

Corte primario por HOJA EN BLANCO (chars≈0 ∧ baja tinta); marcadores como
clasificador (separar.detectar_tipo) y fallback (separar.detectar_segmentos).
NO edita core/anon/: reutiliza separar.py como librería. Ver
docs/superpowers/specs/2026-07-14-split-sala-maquina-design.md.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from core.anon import separar
from core.anon.exceptions import PDFVacioError
from core.utils import file_sha256

_LOG = logging.getLogger("split_documental")
if not _LOG.handlers:
    _LOG.addHandler(logging.NullHandler())

# Umbrales del detector de blanco (calibrar contra el bundle real en F0, Task 8b).
UMBRAL_CHARS_BLANCO = 10       # < → candidata a blanco (cribado barato por chars OCR)
UMBRAL_TINTA_BLANCO = 0.008    # fracción de píxeles con tinta; < → blanco confirmado
_RENDER_SCALE = 2              # pypdfium2 → ~144 dpi
_UMBRAL_OSCURO = 200           # nivel de gris (0-255) por debajo del cual el píxel es "tinta"

# PROVISIONAL: la Task 6 rellena el catálogo E&V inyectado a separar.detectar_tipo.
TIPOS_EXTRA_EV: list[dict] = []


@dataclass
class Segmento:
    seg: int
    pagina_inicio: int
    pagina_fin: int
    tipo: str
    role: str = "documento"


@dataclass
class DocLogico:
    slug: str
    seg_sha256: str
    destino: str          # passthrough | split | merge
    tipo: str
    parent_slug: str
    parent_sha256: str
    role_in_bundle: str
    paginas: str | None
    fuentes: list[str] = field(default_factory=list)


def segmentar_por_blancos(total_pag: int, blancos: set[int]) -> list[tuple[int, int]]:
    """Puro: rangos (inicio, fin) 1-based inclusive EXCLUYENDO las páginas en blanco.

    Colapsa blancos consecutivos, iniciales y finales; nunca emite rangos vacíos.
    """
    rangos: list[tuple[int, int]] = []
    inicio: int | None = None
    for p in range(1, total_pag + 1):
        if p in blancos:
            if inicio is not None:
                rangos.append((inicio, p - 1))
                inicio = None
        else:
            if inicio is None:
                inicio = p
    if inicio is not None:
        rangos.append((inicio, total_pag))
    return rangos


def _primeras_lineas(texto_pagina: str, n: int = 5) -> list[str]:
    """Primeras N líneas útiles (>=3 chars) del texto de una página (para clasificar)."""
    out: list[str] = []
    for raw in (texto_pagina or "").splitlines():
        ln = raw.strip()
        if len(ln) >= 3:
            out.append(ln)
        if len(out) >= n:
            break
    return out


def clasificar(textos: list[str], inicio: int, fin: int, *, tipos_extra=None) -> str:
    """Etiqueta un segmento por los marcadores de su primera página (separar.detectar_tipo).

    Reutiliza los marcadores judiciales de separar.py + los E&V inyectados. Sin
    marcador reconocible → 'DOCUMENTO'.
    """
    if tipos_extra is None:
        tipos_extra = TIPOS_EXTRA_EV
    lineas = _primeras_lineas(textos[inicio - 1]) if 0 <= inicio - 1 < len(textos) else []
    tipo, _prio, _num = separar.detectar_tipo(lineas, tipos_extra=tipos_extra)
    return tipo or "DOCUMENTO"
