"""Tests del inventario."""

from __future__ import annotations

import importlib
import json


def test_inventory_scan_filtra_extensiones(tmp_casos_root):
    from core import case_manager, inventory
    importlib.reload(case_manager)
    importlib.reload(inventory)

    case_dir = case_manager.ensure_case("EV-2026-001")
    inp = case_dir / "00_Input"
    (inp / "documento.pdf").write_bytes(b"%PDF-1.4 dummy")
    (inp / "nota.txt").write_text("nota relevante", encoding="utf-8")
    (inp / "ruido.bin").write_bytes(b"\x00\x01")  # debe descartarse

    out = inventory.scan("EV-2026-001")
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    rels = {f["rel_path"] for f in data["files"]}
    assert "documento.pdf" in rels
    assert "nota.txt" in rels
    assert "ruido.bin" not in rels
    assert "ruido.bin" in data["skipped"]


def test_inventory_clasifica_por_fuente(tmp_casos_root):
    """Archivos en cajones/espejos canónicos de 00_Input/ resuelven a la fuente
    canónica vía intake_lotes.fuente_de (MEJORAS #54 T11); los de la raíz, o
    bajo una carpeta de primer nivel no reconocida, se etiquetan 'manual'."""
    from core import case_manager, inventory
    importlib.reload(case_manager)
    importlib.reload(inventory)

    case_dir = case_manager.ensure_case("EV-2026-002")
    inp = case_dir / "00_Input"

    # Espejo 05_CRM -> fuente canónica 'crm'
    (inp / "05_CRM").mkdir(exist_ok=True)
    (inp / "05_CRM" / "demanda.pdf").write_bytes(b"%PDF-1.4")
    (inp / "05_CRM" / ".pulled").write_text("{}", encoding="utf-8")

    # Espejo 01_Drive EV -> fuente canónica 'drive_ev'
    (inp / "01_Drive EV").mkdir(exist_ok=True)
    (inp / "01_Drive EV" / "factura.pdf").write_bytes(b"%PDF-1.4")
    (inp / "01_Drive EV" / ".synced").write_text("{}", encoding="utf-8")

    # Carpeta de primer nivel no reconocida -> fallback unificado 'manual'
    (inp / "CarpetaRara").mkdir(exist_ok=True)
    (inp / "CarpetaRara" / "x.pdf").write_bytes(b"%PDF-1.4")

    # Raíz: manual
    (inp / "nota_arrastrada.txt").write_text("manual", encoding="utf-8")

    out = inventory.scan("EV-2026-002")
    data = json.loads(out.read_text(encoding="utf-8"))

    by_source = data["by_source"]
    assert by_source["crm"] == 1
    assert by_source["drive_ev"] == 1
    assert by_source["manual"] == 2  # nota suelta + CarpetaRara/x.pdf

    # Los marcadores .pulled y .synced no aparecen
    paths = {f["rel_path"] for f in data["files"]}
    assert "05_CRM/.pulled" not in paths
    assert "01_Drive EV/.synced" not in paths

    # Cada entrada lleva el campo source correcto
    for f in data["files"]:
        if f["rel_path"].startswith("05_CRM/"):
            assert f["source"] == "crm"
        elif f["rel_path"].startswith("01_Drive EV/"):
            assert f["source"] == "drive_ev"
        elif f["rel_path"].startswith("CarpetaRara/"):
            assert f["source"] == "manual"
        elif "/" not in f["rel_path"]:
            assert f["source"] == "manual"
