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
    monkeypatch.setattr(pipeline.case_manager, "ensure_case", lambda *a, **k: None)
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


def test_pipeline_construye_catalogo(tmp_casos_root, monkeypatch):
    """El pipeline (re)construye el catálogo tras inventory.scan. Antes, nadie
    llamaba a build_catalog → indice_documental.yaml quedaba en [] y la sala de
    lectura producía una worklist vacía silenciosamente."""
    from core import pipeline
    importlib.reload(pipeline)

    calls = {"build_catalog": 0}

    def fake_build_catalog(case_id):
        calls["build_catalog"] += 1
        return "ruta/indice_documental.yaml"

    monkeypatch.setattr(pipeline.catalogo_documental, "build_catalog", fake_build_catalog)
    monkeypatch.setattr(pipeline.catalogo_documental, "load_catalog", lambda c: [object(), object()])
    monkeypatch.setattr(pipeline.case_manager, "ensure_case", lambda *a, **k: None)
    monkeypatch.setattr(pipeline.inventory, "scan", lambda *a, **k: 0)
    monkeypatch.setattr(pipeline.extractor, "extract_all", lambda *a, **k: [])
    monkeypatch.setattr(pipeline.markdown_generator, "build", lambda *a, **k: [])
    monkeypatch.setattr(pipeline.scorer, "score", lambda *a, **k: None)
    monkeypatch.setattr(pipeline.viability, "analyze", lambda *a, **k: None)
    monkeypatch.setattr(pipeline.linker, "crosslink", lambda *a, **k: 0)

    pr = pipeline.run("EV-2026-TEST", do_sync=False, do_demanda=False)

    by_name = {s.name: s for s in pr.steps}
    assert "catalogo.build" in by_name
    assert by_name["catalogo.build"].ok
    assert calls["build_catalog"] == 1
    assert by_name["catalogo.build"].artifact == "2 docs"
