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
    """Archivos en subcarpetas de 00_Input/ heredan la fuente; los de la
    raíz se etiquetan como 'manual'."""
    from core import case_manager, inventory
    importlib.reload(case_manager)
    importlib.reload(inventory)

    case_dir = case_manager.ensure_case("EV-2026-002")
    inp = case_dir / "00_Input"

    # sudespacho/
    (inp / "sudespacho").mkdir(exist_ok=True)
    (inp / "sudespacho" / "demanda.pdf").write_bytes(b"%PDF-1.4")
    (inp / "sudespacho" / ".pulled").write_text("{}", encoding="utf-8")

    # drive/
    (inp / "drive").mkdir(exist_ok=True)
    (inp / "drive" / "factura.pdf").write_bytes(b"%PDF-1.4")
    (inp / "drive" / ".synced").write_text("{}", encoding="utf-8")

    # Raíz: manual
    (inp / "nota_arrastrada.txt").write_text("manual", encoding="utf-8")

    out = inventory.scan("EV-2026-002")
    data = json.loads(out.read_text(encoding="utf-8"))

    by_source = data["by_source"]
    assert by_source["sudespacho"] == 1
    assert by_source["drive"] == 1
    assert by_source["manual"] == 1

    # Los marcadores .pulled y .synced no aparecen
    paths = {f["rel_path"] for f in data["files"]}
    assert "sudespacho/.pulled" not in paths
    assert "drive/.synced" not in paths

    # Cada entrada lleva el campo source correcto
    for f in data["files"]:
        if f["rel_path"].startswith("sudespacho/"):
            assert f["source"] == "sudespacho"
        elif f["rel_path"].startswith("drive/"):
            assert f["source"] == "drive"
        elif "/" not in f["rel_path"]:
            assert f["source"] == "manual"
