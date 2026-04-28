"""Configuración de pytest: aísla el CASOS_ROOT en cada test."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


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
