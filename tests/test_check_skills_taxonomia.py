# tests/test_check_skills_taxonomia.py
from __future__ import annotations
import importlib


def test_detecta_drift_de_taxonomia(tmp_path, monkeypatch):
    import scripts.check_skills as cs
    importlib.reload(cs)
    import scripts.sync_taxonomia_skills as sync

    destino = tmp_path / "taxonomia_ev.md"
    sync.generar(destino)
    # Sin drift: la copia coincide con lo que generaría el canon
    assert cs.taxonomia_drift([destino]) == []
    # Con drift: alguien editó la copia a mano
    destino.write_text(destino.read_text(encoding="utf-8") + "\nDRIFT\n", encoding="utf-8")
    assert destino.name in " ".join(cs.taxonomia_drift([destino]))
