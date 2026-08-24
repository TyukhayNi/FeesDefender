"""Tests del orquestador del pipeline."""

from __future__ import annotations

import importlib


def test_extract_all_se_ejecuta_una_sola_vez(tmp_casos_root, monkeypatch):
    """Regresión: el pipeline llamaba a `extractor.extract_all` dos veces por
    corrida (paso de extracción + de nuevo dentro del paso de markdown),
    duplicando el OCR —el único paso caro—. Debe ejecutarse exactamente una
    vez y el paso de markdown reutilizar ese mismo resultado.
    """
    from core import pipeline
    importlib.reload(pipeline)

    sentinel = ["resultado-de-extraccion"]
    calls = {"extract_all": 0, "build_args": []}

    def fake_extract_all(case_id):
        calls["extract_all"] += 1
        return sentinel

    def fake_build(case_id, results):
        calls["build_args"].append(results)
        return []

    monkeypatch.setattr(pipeline.extractor, "extract_all", fake_extract_all)
    monkeypatch.setattr(pipeline.markdown_generator, "build", fake_build)
    # Neutralizar el resto de pasos: no son objeto de este test.
    def _ensure_case_fiel(case_id, *a, **k):
        # El real CREA el caso, y `_write_log` cuenta con ello un par de lineas
        # despues. Un doble que no crea rompe esa invariante y hace fallar al
        # llamador por una razon que no es suya (Task 6, paso 5).
        (tmp_casos_root / case_id / "00_Input").mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(pipeline.case_manager, "ensure_case", _ensure_case_fiel)
    monkeypatch.setattr(pipeline.inventory, "scan", lambda *a, **k: 0)
    monkeypatch.setattr(pipeline.scorer, "score", lambda *a, **k: None)
    monkeypatch.setattr(pipeline.viability, "analyze", lambda *a, **k: None)
    monkeypatch.setattr(pipeline.linker, "crosslink", lambda *a, **k: 0)

    pr = pipeline.run("EV-2026-TEST", do_sync=False, do_demanda=False)

    # 1) El OCR/extracción se ejecuta una sola vez.
    assert calls["extract_all"] == 1
    # 2) El paso de markdown reutiliza EXACTAMENTE el mismo resultado.
    assert calls["build_args"] == [sentinel]
    # 3) Ni la extracción ni el markdown fallaron.
    by_name = {s.name: s for s in pr.steps}
    assert by_name["extractor.extract_all"].ok
    assert by_name["markdown_generator.build"].ok


def test_pipeline_no_construye_catalogo(tmp_casos_root, monkeypatch):
    """El paso catalogo.build fue eliminado del pipeline (deprecación camino de sala del motor,
    2026-06-18). El catálogo lo deriva ahora la skill organizar-sala-lectura. Regresión:
    confirma que el paso NO vuelve a aparecer en pipeline.run."""
    from core import pipeline
    importlib.reload(pipeline)
    def _ensure_case_fiel(case_id, *a, **k):
        # El real CREA el caso, y `_write_log` cuenta con ello un par de lineas
        # despues. Un doble que no crea rompe esa invariante y hace fallar al
        # llamador por una razon que no es suya (Task 6, paso 5).
        (tmp_casos_root / case_id / "00_Input").mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(pipeline.case_manager, "ensure_case", _ensure_case_fiel)
    monkeypatch.setattr(pipeline.inventory, "scan", lambda *a, **k: 0)
    monkeypatch.setattr(pipeline.extractor, "extract_all", lambda *a, **k: [])
    monkeypatch.setattr(pipeline.markdown_generator, "build", lambda *a, **k: [])
    monkeypatch.setattr(pipeline.scorer, "score", lambda *a, **k: None)
    monkeypatch.setattr(pipeline.viability, "analyze", lambda *a, **k: None)
    monkeypatch.setattr(pipeline.linker, "crosslink", lambda *a, **k: 0)
    pr = pipeline.run("EV-2026-TEST", do_sync=False, do_demanda=False)
    assert "catalogo.build" not in {s.name for s in pr.steps}
