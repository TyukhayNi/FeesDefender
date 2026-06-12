# -*- coding: utf-8 -*-
"""Garantiza que los helpers canónicos no divergen de sus copias en las skills.

Los helpers de ``_shared/*.py`` se copian a la carpeta ``scripts/`` de cada
skill para que el ``.skill`` empaquetado sea autónomo. Aquí verificamos dos
cosas, sin acoplarlas entre sí:

- ``test_helpers_sin_drift``: guarda el árbol REAL committeado — las copias
  deben estar sincronizadas con su fuente. Solo lee (``check()`` no tiene
  efectos secundarios), por lo que es determinista e independiente del orden.
- ``test_sync_repara_drift_y_es_idempotente``: ejercita ``sync()`` sobre un
  **clon temporal** del repo (fixture ``sandbox``), nunca sobre el working tree
  real. Inyecta drift artificial, comprueba que ``sync()`` lo repara y que
  re-ejecutarlo es idempotente.

Antes, el test de idempotencia llamaba a ``sync.sync()`` directamente sobre el
working tree: reescribía ficheros del repo (efecto secundario persistente) y,
si había drift transitorio durante el desarrollo, "lo arreglaba" antes de que
``test_helpers_sin_drift`` lo viera. El resultado de la suite dependía del orden
de ejecución (intermitente bajo ``pytest-randomly``). El sandbox elimina el
efecto secundario y el acoplamiento por estado global.
"""
from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

import pytest

_SYNC = Path(__file__).resolve().parents[1] / "scripts" / "sync_skill_helpers.py"


def _load():
    spec = importlib.util.spec_from_file_location("sync_skill_helpers", _SYNC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """Clon temporal de ``_shared`` + targets; el módulo opera ahí, no en el repo.

    Replica byte a byte la fuente canónica y el contenido actual de cada
    carpeta ``scripts/`` objetivo dentro de ``tmp_path``, y redirige las
    constantes de ruta del módulo (``_REPO`` / ``_SHARED``) al clon. Es
    function-scoped: cada test recibe un sandbox propio, así que no comparten
    estado mutable y el working tree real nunca se toca.
    """
    mod = _load()
    repo = tmp_path / "repo"
    shared = repo / ".claude" / "skills" / "_shared"
    shared.mkdir(parents=True)
    for p in mod._SHARED.glob("*.py"):
        shutil.copy2(p, shared / p.name)

    # Replica cada target existente conservando su contenido real (incluido el
    # posible drift). Crea el skill padre aunque scripts/ aún no exista, para
    # que ``_target_dirs()`` en el sandbox devuelva el mismo conjunto que en el
    # árbol real.
    for rel in mod._TARGETS:
        real_scripts = mod._REPO / rel
        if real_scripts.parent.exists():  # el skill padre existe
            sb_scripts = repo / rel
            sb_scripts.parent.mkdir(parents=True, exist_ok=True)
            if real_scripts.exists():
                shutil.copytree(real_scripts, sb_scripts)

    monkeypatch.setattr(mod, "_REPO", repo)
    monkeypatch.setattr(mod, "_SHARED", shared)
    return mod


def test_helpers_sin_drift():
    """El árbol real committeado debe tener las copias sincronizadas.

    Read-only: no muta nada, por lo que es determinista e independiente del
    orden respecto al resto de tests.
    """
    sync = _load()
    drift = sync.check()
    assert drift == [], (
        "Copias de helpers desincronizadas. Ejecuta "
        "`python scripts/sync_skill_helpers.py`.\n" + "\n".join(drift)
    )


def test_sync_repara_drift_y_es_idempotente(sandbox):
    """``sync()`` repara el drift y re-ejecutarlo no reintroduce cambios.

    Todo ocurre dentro del sandbox; el working tree real no se modifica.
    """
    sync = sandbox
    dirs = sync._target_dirs()
    helpers = sync._shared_helpers()
    assert dirs, "el sandbox debe replicar al menos un target"
    assert helpers, "debe existir al menos un helper canónico"

    # Inyecta drift artificial: corrompe una copia y, si hay más de un helper,
    # borra otra.
    corrupt = dirs[0] / helpers[0].name
    corrupt.write_bytes(b"DRIFT ARTIFICIAL\n")
    if len(helpers) > 1:
        (dirs[0] / helpers[-1].name).unlink(missing_ok=True)
    assert sync.check() != [], "el drift inyectado debería detectarse"

    # sync() repara el drift...
    sync.sync()
    assert sync.check() == []

    # ...y es idempotente: re-ejecutarlo no vuelve a desincronizar.
    sync.sync()
    assert sync.check() == []
