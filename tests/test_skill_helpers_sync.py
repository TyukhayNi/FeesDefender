# -*- coding: utf-8 -*-
"""Garantiza que los helpers canónicos no divergen de sus copias en las skills.

El helper ``_shared/registrar_outputs.py`` (y los que se añadan) se copian a la
carpeta ``scripts/`` de cada skill para que el ``.skill`` empaquetado sea
autónomo. Este test ejecuta el sincronizador en modo ``--check`` y falla si
alguna copia difiere byte a byte de la fuente.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_SYNC = Path(__file__).resolve().parents[1] / "scripts" / "sync_skill_helpers.py"


def _load():
    spec = importlib.util.spec_from_file_location("sync_skill_helpers", _SYNC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_helpers_sin_drift():
    sync = _load()
    drift = sync.check()
    assert drift == [], (
        "Copias de helpers desincronizadas. Ejecuta "
        "`python scripts/sync_skill_helpers.py`.\n" + "\n".join(drift)
    )


def test_sync_es_idempotente():
    sync = _load()
    sync.sync()
    assert sync.check() == []
