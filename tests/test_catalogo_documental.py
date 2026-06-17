"""Tests del catálogo documental y del scaffolding de sala de lectura."""

from __future__ import annotations

import importlib


def _reload():
    from core import case_manager, catalogo_documental, inventory
    importlib.reload(case_manager)
    importlib.reload(inventory)
    importlib.reload(catalogo_documental)
    return case_manager, inventory, catalogo_documental


def test_build_catalog_genera_yaml_con_esquema_correcto(tmp_casos_root):
    case_manager, inventory, catalogo = _reload()

    case_dir = case_manager.ensure_case("EV-2026-TEST")
    doc = case_dir / "00_Input" / "01_Drive EV" / "contrato.pdf"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_bytes(b"%PDF-fake-content")
    inventory.scan("EV-2026-TEST")

    path = catalogo.build_catalog("EV-2026-TEST")

    assert path.name == "indice_documental.yaml"
    assert path.exists()

    entries = catalogo.load_catalog("EV-2026-TEST")
    assert len(entries) == 1
    e = entries[0]
    assert e.ruta_relativa == "01_Drive EV/contrato.pdf"
    assert e.nombre_original == "contrato.pdf"
    assert e.fuente == "drive_ev"
    assert e.estado == "original"
    assert e.hash
    assert e.id_doc == e.hash[:12]
    assert e.fecha_indexado
    assert e.parent_id is None
    assert e.orden_en_bundle is None


def test_build_catalog_mapea_fuentes(tmp_casos_root):
    case_manager, inventory, catalogo = _reload()

    case_dir = case_manager.ensure_case("EV-2026-TEST")
    for sub, name in [
        ("01_Drive EV", "doc1.txt"),
        ("05_CRM/01_Demanda", "doc2.txt"),
        ("02_Whatsapp/00_Consultor propietario", "chat.txt"),
    ]:
        p = case_dir / "00_Input" / sub / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"contenido {name}", encoding="utf-8")
    inventory.scan("EV-2026-TEST")

    catalogo.build_catalog("EV-2026-TEST")
    entries = catalogo.load_catalog("EV-2026-TEST")
    fuentes = {e.nombre_original: e.fuente for e in entries}

    assert fuentes["doc1.txt"] == "drive_ev"
    assert fuentes["doc2.txt"] == "crm"
    assert fuentes["chat.txt"] == "whatsapp"


def test_build_catalog_idempotente(tmp_casos_root):
    case_manager, inventory, catalogo = _reload()

    case_dir = case_manager.ensure_case("EV-2026-TEST")
    (case_dir / "00_Input" / "nota.txt").write_text("hola", encoding="utf-8")
    inventory.scan("EV-2026-TEST")

    catalogo.build_catalog("EV-2026-TEST")
    entries1 = catalogo.load_catalog("EV-2026-TEST")
    ts1 = entries1[0].fecha_indexado

    catalogo.build_catalog("EV-2026-TEST")
    entries2 = catalogo.load_catalog("EV-2026-TEST")

    assert len(entries2) == 1
    assert entries2[0].fecha_indexado == ts1


def test_load_catalog_sin_archivo(tmp_casos_root):
    case_manager, _, catalogo = _reload()

    case_manager.ensure_case("EV-2026-TEST")
    entries = catalogo.load_catalog("EV-2026-TEST")
    assert entries == []


# --- Task 2: Scaffolding Sala lectura / MD / _revisar ---


def test_ensure_case_crea_subdirs_sala_lectura(tmp_casos_root):
    case_manager, _, _ = _reload()

    case_dir = case_manager.ensure_case("EV-2026-TEST")
    procesado = case_dir / "01_Procesado"

    assert (procesado / "Sala lectura").is_dir()
    assert (procesado / "MD").is_dir()
    assert (procesado / "_revisar").is_dir()


def test_ensure_case_subdirs_idempotente(tmp_casos_root):
    case_manager, _, _ = _reload()

    case_manager.ensure_case("EV-2026-TEST")
    case_dir = case_manager.ensure_case("EV-2026-TEST")
    procesado = case_dir / "01_Procesado"

    assert (procesado / "Sala lectura").is_dir()
    assert (procesado / "MD").is_dir()
    assert (procesado / "_revisar").is_dir()


# --- Task 3: Grifo de MD en claro a 01_Procesado/MD/ ---


def test_markdown_build_escribe_en_md_subdir(tmp_casos_root):
    from core import case_manager, markdown_generator
    from core.extractor import ExtractionResult
    importlib.reload(case_manager)
    importlib.reload(markdown_generator)

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

    assert md.parent.name == "MD"
    assert md.parent.parent.name == "01_Procesado"
    assert md.name == "nota.md"
    assert md.exists()
    assert not (case_dir / "01_Procesado" / "nota.md").exists()
