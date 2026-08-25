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


@pytest.fixture(autouse=True)
def _barrera_frontal(tmp_path, monkeypatch):
    """Barrera de la Fase 0, `autouse` en TODA la suite: ver `tests/_barrera.py`.

    Es de scope **función** y no de sesión a propósito: una fixture de sesión se monta
    en el setup del primer test —después de la colección— y no puede proteger un efecto
    de import. `autouse` porque un helper opt-in que el autor olvide llamar no es una
    barrera; `tmp_casos_root` (abajo) sigue siendo opt-in porque prepara datos, no
    protege nada.
    """
    from tests import _barrera

    _barrera.instalar(monkeypatch, raiz_local=tmp_path)


@pytest.fixture
def tmp_casos_root(tmp_path, monkeypatch):
    """Un `CASOS_ROOT` aislado. **Restaura `core.config` al salir.**

    `monkeypatch.setenv` deshace la variable de entorno, pero el `reload` de la
    entrada NO se deshacía solo: el módulo quedaba apuntando al `tmp_path` de ese
    test para todo lo que corriera después. Mientras nadie consultaba el catálogo
    daba igual; en cuanto `sala_maquina` empezó a preguntar por el caso (Fase 1
    dual, Task 9) la fuga se volvió un rojo dependiente del orden: con la semilla
    777, `test_repository_checkout` dejaba un `EV-2026-001` **prestado** en su
    tmp_path y ocho tests de sala de máquina —que usan ese mismo case_id— se
    encontraban el caso ajeno con lock y abortaban.

    El `reload` de salida corre DESPUÉS de que monkeypatch restaure el entorno,
    así que `core.config` vuelve al `CASOS_ROOT` real.
    """
    root = tmp_path / "CASOS"
    root.mkdir()
    monkeypatch.setenv("CASOS_ROOT", str(root))
    # Reimportar settings para que tome el nuevo CASOS_ROOT
    import importlib

    from core import config as cfg

    importlib.reload(cfg)
    try:
        yield Path(root)
    finally:
        monkeypatch.undo()          # devuelve CASOS_ROOT al valor real…
        importlib.reload(cfg)       # …y ahora sí el módulo lo relee
