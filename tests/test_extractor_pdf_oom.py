"""Estrategia de extracción de PDF: pypdf-first para capa de texto, Docling/OCR
solo para escaneados con guarda de páginas.

Regresión del OOM/segfault de RapidOCR (Docling) visto en BaRS1 (Atles de
plànols.pdf, 128 págs CON capa de texto): se OCR-izaban PDFs que no lo
necesitaban y el bad_alloc de C++ —no capturable por try/except— mataba todo
`extract_all`.
"""
from __future__ import annotations

import importlib
from pathlib import Path


def _ext():
    from core import extractor
    importlib.reload(extractor)
    return extractor


def test_texto_suficiente_heuristica():
    ext = _ext()
    assert ext._texto_suficiente("x" * 200, 1) is True
    assert ext._texto_suficiente("", 1) is False          # escaneado: vacío
    assert ext._texto_suficiente("corto", 1) is False     # < 100 chars
    # densidad baja (mucha página, poco texto) → no basta
    assert ext._texto_suficiente("x" * 150, 100) is False
    # Atles de plànols: 53407 chars / 128 págs ~ 417/pág → basta
    assert ext._texto_suficiente("x" * 53407, 128) is True


def test_pdf_con_capa_de_texto_usa_pypdf_y_no_llama_docling(monkeypatch):
    ext = _ext()
    monkeypatch.setattr(ext, "_try_pypdf", lambda p: "T" * 6000)
    monkeypatch.setattr(ext, "_pdf_num_paginas", lambda p: 128)

    def _boom(p):
        raise AssertionError("Docling/OCR NO debe llamarse para PDF con texto")

    monkeypatch.setattr(ext, "_try_docling", _boom)
    text, method = ext._extract_one(Path("Atles de planols.pdf"))
    assert method == "pypdf"
    assert len(text) == 6000


def test_pdf_escaneado_corto_cae_a_docling(monkeypatch):
    ext = _ext()
    monkeypatch.setattr(ext, "_try_pypdf", lambda p: "")     # sin capa de texto
    monkeypatch.setattr(ext, "_pdf_num_paginas", lambda p: 5)
    monkeypatch.setattr(ext, "_try_docling", lambda p: "TEXTO OCR")
    text, method = ext._extract_one(Path("Oferta 17M.pdf"))
    assert method == "docling"
    assert text == "TEXTO OCR"


def test_pdf_escaneado_demasiado_largo_no_ocr_y_no_crashea(monkeypatch):
    ext = _ext()
    monkeypatch.setattr(ext, "_try_pypdf", lambda p: "")
    monkeypatch.setattr(ext, "_pdf_num_paginas", lambda p: 200)  # > MAX_OCR_PAGINAS

    def _boom(p):
        raise AssertionError("No se debe OCR-izar un escaneado de 200 págs")

    monkeypatch.setattr(ext, "_try_docling", _boom)
    text, method = ext._extract_one(Path("escaneado_enorme.pdf"))
    assert method == "sin_texto"
    assert text == ""
