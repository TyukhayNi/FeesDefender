# tests/test_sync_taxonomia_skills.py
from __future__ import annotations
import importlib


def test_genera_taxonomia_con_las_8_categorias(tmp_path, monkeypatch):
    import scripts.sync_taxonomia_skills as sync
    importlib.reload(sync)
    from core.config import TAXONOMIA_EV

    out = tmp_path / "taxonomia_ev.md"
    sync.generar(out)
    texto = out.read_text(encoding="utf-8")
    for cat in TAXONOMIA_EV:
        assert cat in texto                      # las 8 categorías del canon
    assert "POR PARTE" in texto                  # enrutado PBC del canon
    assert "guiones_bajos" in texto              # naming del canon
    assert "GENERADO" in texto.upper()           # cabecera no-editar


def test_idempotente(tmp_path):
    import scripts.sync_taxonomia_skills as sync
    out = tmp_path / "t.md"
    sync.generar(out)
    a = out.read_text(encoding="utf-8")
    sync.generar(out)
    assert out.read_text(encoding="utf-8") == a  # misma salida, sin drift
