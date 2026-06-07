"""Tests del skip incremental del extractor y del markdown.

Regresión de `[IDEA-SKIP-INCREMENTAL-EXTRACCION]` tareas 2 y 3: la
extracción (OCR, el paso caro) debe saltar lo que no ha cambiado por hash
de origen, y el markdown debe regenerar solo lo realmente reextraído.
"""

from __future__ import annotations

import importlib


def _reload():
    from core import case_manager, extractor, inventory, markdown_generator
    importlib.reload(inventory)
    importlib.reload(extractor)
    importlib.reload(markdown_generator)
    importlib.reload(case_manager)
    return case_manager, inventory, extractor, markdown_generator


def test_extract_all_salta_lo_no_cambiado(tmp_casos_root):
    case_manager, inventory, extractor, _ = _reload()

    case_dir = case_manager.ensure_case("EV-2026-TEST")
    doc = case_dir / "00_Input" / "nota.txt"
    doc.write_text("contenido original", encoding="utf-8")
    inventory.scan("EV-2026-TEST")

    # 1ª pasada: se extrae de verdad.
    r1 = extractor.extract_all("EV-2026-TEST")
    assert len(r1) == 1
    assert r1[0].skipped is False

    # 2ª pasada sin cambios en el origen: se salta, reutilizando el .txt.
    r2 = extractor.extract_all("EV-2026-TEST")
    assert len(r2) == 1
    assert r2[0].skipped is True
    assert r2[0].chars == r1[0].chars
    assert r2[0].method == r1[0].method

    # Modificar el origen invalida el cache → reextrae.
    doc.write_text("contenido modificado y mas largo", encoding="utf-8")
    inventory.scan("EV-2026-TEST")
    r3 = extractor.extract_all("EV-2026-TEST")
    assert r3[0].skipped is False

    # force=True ignora el skip aunque no haya cambios.
    r4 = extractor.extract_all("EV-2026-TEST", force=True)
    assert r4[0].skipped is False


def test_extract_all_invalida_cache_al_cambiar_version(tmp_casos_root):
    case_manager, inventory, extractor, _ = _reload()

    case_dir = case_manager.ensure_case("EV-2026-TEST")
    (case_dir / "00_Input" / "nota.txt").write_text("hola", encoding="utf-8")
    inventory.scan("EV-2026-TEST")

    extractor.extract_all("EV-2026-TEST")  # genera estado
    # Subir la versión del extractor invalida el cache → reextrae.
    extractor.EXTRACTOR_VERSION += 1
    r = extractor.extract_all("EV-2026-TEST")
    assert r[0].skipped is False


def test_build_solo_regenera_lo_reextraido(tmp_casos_root):
    case_manager, _, extractor, markdown_generator = _reload()
    from core.extractor import ExtractionResult

    case_dir = case_manager.ensure_case("EV-2026-TEST")
    raw = case_dir / "01_Procesado" / "raw_text"
    raw.mkdir(parents=True, exist_ok=True)
    txt = raw / "nota.txt"
    txt.write_text("texto extraido", encoding="utf-8")

    res = ExtractionResult(
        rel_path="nota.txt", output_path=txt, chars=14, method="raw", skipped=False,
    )
    paths = markdown_generator.build("EV-2026-TEST", [res])
    md = paths[0]
    assert md.exists()
    mtime_inicial = md.stat().st_mtime_ns

    # 2ª build con skipped=True y .md existente → NO se reescribe.
    res_skip = ExtractionResult(
        rel_path="nota.txt", output_path=txt, chars=14, method="raw", skipped=True,
    )
    markdown_generator.build("EV-2026-TEST", [res_skip])
    assert md.stat().st_mtime_ns == mtime_inicial

    # Pero si el .md no existe, lo regenera aunque skipped=True.
    md.unlink()
    markdown_generator.build("EV-2026-TEST", [res_skip])
    assert md.exists()
