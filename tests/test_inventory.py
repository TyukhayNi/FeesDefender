"""Tests del inventario."""

from __future__ import annotations

import importlib
import json


def test_inventory_scan_recoge_tambien_lo_que_no_sabe_leer(tmp_casos_root):
    """**Este test decía lo contrario hasta el 2026-09-26, y el cambio se declara aquí.**

    Se llamaba `…_filtra_extensiones` y exigía que un `ruido.bin` quedara fuera, en
    `skipped`: era la lista blanca de extensiones que decidía la población del inventario, y
    con ella la del catálogo de la sala. Eso es `MEJORAS #316`: en W-02Y2J6 dejó fuera siete
    notas de voz, zips, vCards y un vídeo, y en otros casos un `.pptx` y documentos sin
    extensión. Un fichero que el cliente mandó es prueba aunque el extractor no sepa leerlo;
    lo que no es documento lo aparta el registro de protocolo por ubicación
    (`test_316_…` y `test_inventory_clasifica_por_fuente`).
    """
    from core import case_manager, inventory
    importlib.reload(case_manager)
    importlib.reload(inventory)

    case_dir = case_manager.ensure_case("EV-2026-001")
    inp = case_dir / "00_Input"
    (inp / "documento.pdf").write_bytes(b"%PDF-1.4 dummy")
    (inp / "nota.txt").write_text("nota relevante", encoding="utf-8")
    (inp / "ruido.bin").write_bytes(b"\x00\x01")

    out = inventory.scan("EV-2026-001")
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    rels = {f["rel_path"] for f in data["files"]}
    assert rels == {"documento.pdf", "nota.txt", "ruido.bin"}
    assert "skipped" not in data, "ya no hay una población de segunda que nadie lee"


def test_316_el_inventario_recoge_audios_zips_vcards_y_lo_que_no_tiene_extension(tmp_casos_root):
    """`MEJORAS #316`, medido en W-02Y2J6 (audiencia previa el 14/10): siete notas de voz de
    WhatsApp, zips, vCards y un vídeo no llegaron a la sala de lectura, porque el inventario
    CLI los apartaba a `skipped` por extensión y el catálogo se construye con lo inventariado.
    En los 15 inventarios reales, la lista blanca dejó fuera también un `.pptx`, un `.m4a`,
    un `.numbers` y once documentos sin extensión. Lo que es protocolo lo dice el registro por
    ubicación, no la extensión."""
    from core import case_manager, inventory
    importlib.reload(case_manager)
    importlib.reload(inventory)

    case_dir = case_manager.ensure_case("EV-2026-316")
    inp = case_dir / "00_Input"
    lote = inp / "2026-09-25_whatsapp_03" / "Chat"
    lote.mkdir(parents=True)
    nombres = ["00000028-AUDIO-2025-03-22-17-11-57.opus", "export.zip", "contacto.vcf",
               "presentacion.pptx", "video.mp4", "documento_sin_extension"]
    for n in nombres:
        (lote / n).write_bytes(b"x")
    (inp / "_caso.md.bak_20260610T152854").write_text("copia", encoding="utf-8")

    data = json.loads(inventory.scan("EV-2026-316").read_text(encoding="utf-8"))
    rels = {f["rel_path"] for f in data["files"]}

    assert {f"2026-09-25_whatsapp_03/Chat/{n}" for n in nombres} <= rels, rels
    assert "_caso.md.bak_20260610T152854" not in rels, "protocolo por ubicación"


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
    # Los marcadores, donde los escriben sus productores (`MEJORAS #316`): hasta el
    # 2026-09-26 este test los ponía en `05_CRM/.pulled` y `01_Drive EV/.synced`, sitios
    # donde no escribe nadie —el pull v2 del CRM guarda su estado en `update_pull_state`—, y
    # quien los apartaba era la lista blanca de extensiones, no el registro de protocolo.
    (inp / "sudespacho_591").mkdir(exist_ok=True)
    (inp / "sudespacho_591" / ".pulled").write_text("{}", encoding="utf-8")

    # Espejo 01_Drive EV -> fuente canónica 'drive_ev'
    (inp / "01_Drive EV").mkdir(exist_ok=True)
    (inp / "01_Drive EV" / "factura.pdf").write_bytes(b"%PDF-1.4")
    (inp / "01_Drive EV" / ".pulled").write_text("{}", encoding="utf-8")

    # Carpeta de primer nivel no reconocida -> fallback unificado 'manual'
    (inp / "CarpetaRara").mkdir(exist_ok=True)
    (inp / "CarpetaRara" / "x.pdf").write_bytes(b"%PDF-1.4")
    # Y un marcador homónimo FUERA del sitio de su productor: es un fichero del cliente y
    # ENTRA (R1 del #408: sin él, este test no distinguía «protocolo por ubicación» de
    # «todo `.pulled` fuera»).
    (inp / "CarpetaRara" / ".pulled").write_text("{}", encoding="utf-8")

    # Raíz: manual
    (inp / "nota_arrastrada.txt").write_text("manual", encoding="utf-8")

    out = inventory.scan("EV-2026-002")
    data = json.loads(out.read_text(encoding="utf-8"))

    by_source = data["by_source"]
    assert by_source["crm"] == 1
    assert by_source["drive_ev"] == 1
    assert by_source["manual"] == 3  # nota suelta + CarpetaRara/x.pdf + CarpetaRara/.pulled

    # Los marcadores de los productores no aparecen
    paths = {f["rel_path"] for f in data["files"]}
    assert "sudespacho_591/.pulled" not in paths
    assert "01_Drive EV/.pulled" not in paths
    assert "CarpetaRara/.pulled" in paths

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
