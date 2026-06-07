"""Configuración de pytest: aísla el CASOS_ROOT en cada test.

Marcador ``slow``: tests que requieren el motor NLP real (Presidio + spaCy),
OCR real (tesseract) o procesamiento PDF pesado de ``core/anon/``. Se omiten
por defecto (verja de cierre rápida ~segundos) y se ejecutan con ``--runslow``.
El script ``scripts/session_close`` activa ``--runslow`` automáticamente cuando
el commit toca ``core/anon/``.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--runslow",
        action="store_true",
        default=False,
        help="Ejecuta también los tests marcados @pytest.mark.slow "
        "(motor NLP/OCR real; ~3-4 min).",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "slow: test lento (Presidio/spaCy/OCR real). Omitido salvo --runslow.",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--runslow"):
        return
    skip_slow = pytest.mark.skip(reason="lento — usar --runslow para ejecutarlo")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)


@pytest.fixture
def tmp_casos_root(tmp_path, monkeypatch):
    root = tmp_path / "CASOS"
    root.mkdir()
    monkeypatch.setenv("CASOS_ROOT", str(root))
    # Reimportar settings para que tome el nuevo CASOS_ROOT
    import importlib

    from core import config as cfg

    importlib.reload(cfg)
    yield Path(root)
