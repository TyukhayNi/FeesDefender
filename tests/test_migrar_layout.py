from pathlib import Path

from core import migrar_layout as ml


def _cajon(tmp_path, nombre, ficheros):
    d = tmp_path / "00_Input" / nombre
    for rel, contenido in ficheros.items():
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(contenido)
    return d


def test_estimar_fecha_prefiere_la_mas_antigua_de_nombres(tmp_path):
    d = _cajon(tmp_path, "04_Manual",
                {"2026-03-05_demanda.pdf": b"a", "2026-01-10_encargo.pdf": b"b"})
    assert ml.estimar_fecha(d) == "2026-01-10"


def test_plan_migracion_solo_cajones_de_entrega(tmp_path):
    _cajon(tmp_path, "04_Manual", {"a.pdf": b"a"})
    _cajon(tmp_path, "01_Drive EV", {"w/doc.pdf": b"d"})      # espejo: NO se toca
    _cajon(tmp_path, "05_CRM", {"General/x.pdf": b"x"})       # espejo: NO se toca
    _cajon(tmp_path, "02_Whatsapp", {})                       # vacío: sin lote
    plan = ml.plan_migracion(tmp_path / "00_Input")
    assert [m.cajon for m in plan] == ["04_Manual"]
    mov = plan[0]
    assert mov.fuente == "manual"
    assert mov.lote.endswith("_manual_01")
    assert mov.mapping == {"04_Manual/a.pdf": f"{mov.lote}/a.pdf"}


def test_remap_paths_m9():
    data = {"sha1": {"primary_path": "04_Manual/a.pdf",
                     "aliases": [{"path": "03_Email/x/a.pdf", "source": "email"}]}}
    mapping = {"04_Manual/a.pdf": "2026-01-10_manual_01/a.pdf",
               "03_Email/x/a.pdf": "2026-01-10_email_01/x/a.pdf"}
    out, n = ml.remap_paths(data, mapping)
    assert out["sha1"]["primary_path"] == "2026-01-10_manual_01/a.pdf"
    assert out["sha1"]["aliases"][0]["path"] == "2026-01-10_email_01/x/a.pdf"
    assert n == 2


def test_remap_cobertura_por_rel_path():
    rows = [{"rel_path": "04_Manual/a.pdf", "slug": "a_12345678", "estado": "ok"},
            {"rel_path": "01_Drive EV/w/doc.pdf", "slug": "doc_87654321", "estado": "ok"}]
    out, n = ml.remap_cobertura(rows, {"04_Manual/a.pdf": "2026-01-10_manual_01/a.pdf"})
    assert out[0]["rel_path"] == "2026-01-10_manual_01/a.pdf"
    assert out[1]["rel_path"] == "01_Drive EV/w/doc.pdf"      # espejo intacto
    assert n == 1


def test_remap_paths_m9_espejo_intacto():
    data = {"sha1": {"primary_path": "01_Drive EV/w/doc.pdf", "aliases": []}}
    mapping = {"04_Manual/a.pdf": "2026-01-10_manual_01/a.pdf"}
    out, n = ml.remap_paths(data, mapping)
    assert out["sha1"]["primary_path"] == "01_Drive EV/w/doc.pdf"  # espejo intacto
    assert n == 0


def test_remap_catalogo_sin_prefijo():
    """Formato real emitido por catalogo_documental: ruta_relativa sin '00_Input/'
    (`FileEntry.rel_path` es relativo a 00_Input/, ver core/inventory.py)."""
    entries = [
        {"id_doc": "abc123", "ruta_relativa": "04_Manual/a.pdf",
         "nombre_original": "a.pdf", "fuente": "manual"},
        {"id_doc": "def456", "ruta_relativa": "01_Drive EV/w/doc.pdf",
         "nombre_original": "doc.pdf", "fuente": "drive_ev"},   # espejo: NO se toca
    ]
    mapping = {"04_Manual/a.pdf": "2026-01-10_manual_01/a.pdf"}
    out, n = ml.remap_catalogo(entries, mapping)
    assert out[0]["ruta_relativa"] == "2026-01-10_manual_01/a.pdf"
    assert out[1]["ruta_relativa"] == "01_Drive EV/w/doc.pdf"      # espejo intacto
    assert n == 1


def test_remap_catalogo_con_prefijo_00_input():
    """Tolerancia al formato con prefijo '00_Input/' (§7.4c): se preserva el
    prefijo en la ruta reescrita."""
    entries = [
        {"id_doc": "abc123", "ruta_relativa": "00_Input/04_Manual/a.pdf",
         "nombre_original": "a.pdf", "fuente": "manual"},
        {"id_doc": "def456", "ruta_relativa": "00_Input/01_Drive EV/w/doc.pdf",
         "nombre_original": "doc.pdf", "fuente": "drive_ev"},   # espejo: NO se toca
    ]
    mapping = {"04_Manual/a.pdf": "2026-01-10_manual_01/a.pdf"}
    out, n = ml.remap_catalogo(entries, mapping)
    assert out[0]["ruta_relativa"] == "00_Input/2026-01-10_manual_01/a.pdf"
    assert out[1]["ruta_relativa"] == "00_Input/01_Drive EV/w/doc.pdf"  # espejo intacto
    assert n == 1


# ---------------------------------------------------------------------------
# T14: migración bajo demanda (integración disco real + CLI) — spec §7/§9.4
# ---------------------------------------------------------------------------

def test_migracion_integral_espejos_intactos_y_remapeo(tmp_casos_root):
    import json

    from core import case_manager, config
    from core.intake_lotes import PATRON_LOTE, leer_manifiesto
    from scripts.migrar_layout_intake import migrar

    case_id = "EV-MIG-001"
    case_manager.ensure_case(case_id, titulo="mig")
    base = config.caso_path(case_id) / "00_Input"
    # entrega (4 cajones) + espejos poblados
    for rel, b in {
        "02_Whatsapp/03_Otros/chat/_chat.txt": b"c",
        "03_Email/2026-02-01_asunto.eml": b"e",
        "03_Email/_exported_ids.json": b"{}",
        "04_Manual/2026-01-10_demanda.pdf": b"m",
        "06_Entrevistas/grabacion.mp4": b"g",
        "01_Drive EV/w/doc.pdf": b"d",
        "05_CRM/General/x.pdf": b"x",
    }.items():
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b)
    # registros aguas abajo
    (base / "_intake_hashes.json").write_text(json.dumps({
        "sha-m": {"primary_path": "04_Manual/2026-01-10_demanda.pdf", "aliases": []}}),
        encoding="utf-8")
    maq = config.caso_path(case_id) / "01_Procesado" / "02_Sala de máquina"
    maq.mkdir(parents=True)
    (maq / "_cobertura.json").write_text(json.dumps(
        [{"rel_path": "04_Manual/2026-01-10_demanda.pdf", "slug": "s", "estado": "ok"}]),
        encoding="utf-8")

    migrar(case_id, dry_run=False)

    # espejos y protocolo intactos
    assert (base / "01_Drive EV" / "w" / "doc.pdf").is_file()
    assert (base / "05_CRM" / "General" / "x.pdf").is_file()
    assert (base / "_caso.md").is_file()
    # los 4 cajones envueltos en lotes sintéticos con manifiesto estimado
    lotes = [d for d in base.iterdir() if d.is_dir() and PATRON_LOTE.match(d.name)]
    assert {PATRON_LOTE.match(d.name).group(2) for d in lotes} \
        == {"whatsapp", "email", "manual", "entrevista"}
    lote_manual = next(d for d in lotes if "_manual_" in d.name)
    assert lote_manual.name.startswith("2026-01-10")          # fecha del nombre de fichero
    assert leer_manifiesto(lote_manual)["fecha_intake_estimada"] is True
    # cajón vacío pero NO borrado; índice de canal movido a la raíz
    assert (base / "04_Manual").is_dir()
    assert not any((base / "04_Manual").iterdir())
    assert (base / "_exported_ids.json").is_file()
    # conserva subcarpetas de rol (Finding 4): el fichero anidado del whatsapp
    # aterriza en su misma ruta relativa dentro del lote, no aplanado
    lote_whatsapp = next(d for d in lotes if "_whatsapp_" in d.name)
    nested = lote_whatsapp / "03_Otros" / "chat" / "_chat.txt"
    assert nested.is_file()
    items_whatsapp = leer_manifiesto(lote_whatsapp)["items"]
    assert any(i["relpath"] == "03_Otros/chat/_chat.txt" for i in items_whatsapp)
    # remapeo round-trip (§9.4): M9 y cobertura casan con el disco nuevo
    m9 = json.loads((base / "_intake_hashes.json").read_text(encoding="utf-8"))
    nuevo_rel = m9["sha-m"]["primary_path"]
    assert nuevo_rel.startswith("2026-01-10_manual_01/") and (base / nuevo_rel).is_file()
    cob = json.loads((maq / "_cobertura.json").read_text(encoding="utf-8"))
    assert cob[0]["rel_path"] == nuevo_rel


def test_migracion_aborta_con_caso_prestado(tmp_casos_root):
    import pytest

    from core import case_manager
    from scripts.migrar_layout_intake import CasoPrestadoError, migrar

    case_id = "EV-MIG-002"
    case_manager.ensure_case(case_id, titulo="mig")
    case_manager.escribir_lock(case_id, user="Nikolai Tyukhay",
                               timestamp="2026-07-17T09:00:00Z", nonce="n")
    with pytest.raises(CasoPrestadoError):
        migrar(case_id, dry_run=False)


def test_migracion_revierte_si_falla_un_movimiento_a_mitad(tmp_casos_root, monkeypatch):
    """Finding 1: si el segundo cajón falla a mitad de los movimientos físicos,
    TODO se revierte — el primer cajón vuelve a su sitio y M9/cobertura quedan
    intactos (nunca apuntando a rutas que ya no existen). Sin esto, re-ejecutar
    la migración no repara nada porque el cajón vaciado ya no produce plan."""
    import json

    import pytest

    from core import case_manager, config
    from core.intake_lotes import PATRON_LOTE
    import scripts.migrar_layout_intake as mli

    case_id = "EV-MIG-003"
    case_manager.ensure_case(case_id, titulo="mig")
    base = config.caso_path(case_id) / "00_Input"
    for rel, b in {
        "02_Whatsapp/chat.txt": b"c",
        "04_Manual/2026-01-10_demanda.pdf": b"m",
    }.items():
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b)
    (base / "_intake_hashes.json").write_text(json.dumps({
        "sha-m": {"primary_path": "04_Manual/2026-01-10_demanda.pdf", "aliases": []}}),
        encoding="utf-8")
    maq = config.caso_path(case_id) / "01_Procesado" / "02_Sala de máquina"
    maq.mkdir(parents=True)
    (maq / "_cobertura.json").write_text(json.dumps(
        [{"rel_path": "04_Manual/2026-01-10_demanda.pdf", "slug": "s", "estado": "ok"}]),
        encoding="utf-8")
    m9_antes = (base / "_intake_hashes.json").read_text(encoding="utf-8")
    cob_antes = (maq / "_cobertura.json").read_text(encoding="utf-8")

    original_move = mli.shutil.move
    llamadas = {"n": 0}

    def move_que_falla_en_segundo_cajon(src, dst):
        llamadas["n"] += 1
        # Solo la 2ª llamada (1er movimiento del cajón manual) falla. Las
        # llamadas posteriores son el propio rollback revirtiendo hechos[0] —
        # deben completar de verdad o el test no comprobaría nada real.
        if llamadas["n"] == 2:
            raise OSError("fichero bloqueado (simulado)")
        return original_move(src, dst)

    monkeypatch.setattr(mli.shutil, "move", move_que_falla_en_segundo_cajon)

    with pytest.raises(RuntimeError):
        mli.migrar(case_id, dry_run=False)

    # 1er cajón revertido a su sitio original; ningún lote huérfano
    assert (base / "02_Whatsapp" / "chat.txt").is_file()
    assert (base / "04_Manual" / "2026-01-10_demanda.pdf").is_file()
    lotes = [d for d in base.iterdir() if d.is_dir() and PATRON_LOTE.match(d.name)]
    assert lotes == []

    # M9 y cobertura SIN TOCAR (fase 2 nunca corrió)
    assert (base / "_intake_hashes.json").read_text(encoding="utf-8") == m9_antes
    assert (maq / "_cobertura.json").read_text(encoding="utf-8") == cob_antes

    # ningún evento emitido
    log_path = base / "_intake_log.jsonl"
    assert not log_path.is_file() or "migracion_layout_intake" not in log_path.read_text(
        encoding="utf-8")
