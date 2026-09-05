from pathlib import Path

import yaml

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
    # catálogo documental (Finding 2): forma real de CatalogEntry/save_catalog
    # (core/catalogo_documental.py) — un doc en cajón de entrega + un espejo.
    cat_path = config.caso_path(case_id) / "01_Procesado" / "indice_documental.yaml"
    cat_path.write_text(yaml.dump([
        {"id_doc": "abc123", "ruta_relativa": "04_Manual/2026-01-10_demanda.pdf",
         "nombre_original": "2026-01-10_demanda.pdf", "tipo_documental": None,
         "fecha_doc": None, "parte": None, "fuente": "manual", "estado": "original",
         "hash": "", "fecha_indexado": "", "parent_id": None, "orden_en_bundle": None,
         "descripcion": None, "fecha_fuente": None, "confianza": None,
         "nombre_canonico": None, "ruta_sala_lectura": None},
        {"id_doc": "def456", "ruta_relativa": "01_Drive EV/w/doc.pdf",
         "nombre_original": "doc.pdf", "tipo_documental": None, "fecha_doc": None,
         "parte": None, "fuente": "drive_ev", "estado": "original", "hash": "",
         "fecha_indexado": "", "parent_id": None, "orden_en_bundle": None,
         "descripcion": None, "fecha_fuente": None, "confianza": None,
         "nombre_canonico": None, "ruta_sala_lectura": None},
    ], allow_unicode=True, default_flow_style=False, sort_keys=False),
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
    # remapeo del catálogo documental (Finding 2): la entrada de entrega
    # remapea y su ruta nueva existe en disco; el espejo queda intacto; el
    # YAML sigue siendo válido y con el mismo número de entradas.
    catalogo = yaml.safe_load(cat_path.read_text(encoding="utf-8"))
    assert len(catalogo) == 2
    entry_manual = next(e for e in catalogo if e["id_doc"] == "abc123")
    entry_espejo = next(e for e in catalogo if e["id_doc"] == "def456")
    assert entry_manual["ruta_relativa"] == nuevo_rel
    assert (base / entry_manual["ruta_relativa"]).is_file()
    assert entry_espejo["ruta_relativa"] == "01_Drive EV/w/doc.pdf"


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


def test_migracion_no_borra_duplicado_de_control_si_falla_despues(tmp_casos_root, monkeypatch):
    """Finding 1: el borrado del fichero de control duplicado (``03_Email``, ya
    consolidado en la raíz) se aplaza a fase 2. Si un cajón procesado DESPUÉS
    falla, el duplicado debe seguir intacto en su cajón original — con el bug,
    se borraba en el momento de detectarlo (fase 1), antes de saber si el
    resto de la migración completaría, y el rollback nunca podía restaurarlo."""
    import pytest

    from core import case_manager, config
    from core.intake_lotes import PATRON_LOTE
    import scripts.migrar_layout_intake as mli

    case_id = "EV-MIG-004"
    case_manager.ensure_case(case_id, titulo="mig")
    base = config.caso_path(case_id) / "00_Input"
    for rel, b in {
        "03_Email/2026-02-01_asunto.eml": b"e",
        "03_Email/_exported_ids.json": b"{}",   # duplicado del ya consolidado
        "04_Manual/2026-01-10_demanda.pdf": b"m",
    }.items():
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b)
    # ya consolidado en la raíz: dispara la rama "duplicado, NO mover"
    (base / "_exported_ids.json").write_text("{}", encoding="utf-8")

    original_move = mli.shutil.move

    def move_que_falla_en_manual(src, dst):
        if "04_Manual" in str(src):
            raise OSError("fichero bloqueado (simulado)")
        return original_move(src, dst)

    monkeypatch.setattr(mli.shutil, "move", move_que_falla_en_manual)

    with pytest.raises(RuntimeError):
        mli.migrar(case_id, dry_run=False)

    # el duplicado NUNCA se borró: sigue en su cajón original, intacto
    dup = base / "03_Email" / "_exported_ids.json"
    assert dup.is_file()
    assert dup.read_text(encoding="utf-8") == "{}"
    # la raíz tampoco cambió
    assert (base / "_exported_ids.json").read_text(encoding="utf-8") == "{}"
    # rollback completo: ningún lote huérfano, todo vuelve a su cajón
    lotes = [d for d in base.iterdir() if d.is_dir() and PATRON_LOTE.match(d.name)]
    assert lotes == []
    assert (base / "03_Email" / "2026-02-01_asunto.eml").is_file()
    assert (base / "04_Manual" / "2026-01-10_demanda.pdf").is_file()


# ── MEJORAS #149 (rev. 2 §3.4): la migración no borra lo que no acaba de comparar ────────────
#
# T4, T5, T5b, T5c y T6 del diseño. El estado de canal legacy (`03_Email/_exported_ids.json`,
# directamente bajo el cajón) se identifica por (directorio, nombre); el homónimo ANIDADO es un
# adjunto y viaja al lote con su entrada en el `mapping` M9.

def _caso_legacy_email(tmp_casos_root, case_id, *, ficheros, raiz=None):
    import json

    from core import case_manager, config

    case_manager.ensure_case(case_id, titulo="mig-149")
    base = config.caso_path(case_id) / "00_Input"
    for rel, b in ficheros.items():
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b)
    if raiz is not None:
        (base / "_exported_ids.json").write_bytes(raiz)
    (base / "_intake_hashes.json").write_text(json.dumps({
        "sha-adj": {"primary_path": "03_Email/hilo/_exported_ids.json", "aliases": []}}),
        encoding="utf-8")
    return base


def _arbol(base):
    import hashlib
    return {p.relative_to(base).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in base.rglob("*") if p.is_file()}


def test_t4_duplicado_identico_se_borra_en_fase_2_y_la_raiz_sigue(tmp_casos_root):
    from scripts.migrar_layout_intake import migrar

    base = _caso_legacy_email(tmp_casos_root, "EV-149-T4", ficheros={
        "03_Email/2026-02-01_asunto.eml": b"e",
        "03_Email/_exported_ids.json": b'{"a": [1]}',
    }, raiz=b'{"a": [1]}')
    informe = {}
    migrar("EV-149-T4", dry_run=False, informe=informe)
    assert not (base / "03_Email" / "_exported_ids.json").exists()
    assert (base / "_exported_ids.json").read_bytes() == b'{"a": [1]}'
    assert informe["duplicados_borrados"] == ["03_Email/_exported_ids.json"]
    assert informe["no_borrados"] == []


def test_t5_duplicado_distinto_aborta_el_plan_sin_mover_nada_tambien_en_dry_run(tmp_casos_root):
    import pytest

    from scripts.migrar_layout_intake import EstadoDeCanalDivergenteError, migrar

    base = _caso_legacy_email(tmp_casos_root, "EV-149-T5", ficheros={
        "03_Email/2026-02-01_asunto.eml": b"e",
        "03_Email/_exported_ids.json": b'{"a": [1]}',
        "04_Manual/doc.pdf": b"m",
    }, raiz=b'{"a": [1, 2]}')
    antes = _arbol(base)
    for dry in (True, False):
        with pytest.raises(EstadoDeCanalDivergenteError) as exc:
            migrar("EV-149-T5", dry_run=dry)
        msg = str(exc.value)
        assert "03_Email/_exported_ids.json" in msg and "00_Input/_exported_ids.json" in msg
        assert _arbol(base) == antes            # byte a byte como estaba, en los dos modos
    assert not [d for d in base.iterdir() if d.is_dir() and d.name[:4].isdigit()]  # sin lotes


def test_t5b_la_raiz_aparece_entre_el_plan_y_la_fase_1_aborta_y_revierte(tmp_casos_root,
                                                                        monkeypatch):
    import shutil

    import pytest

    from scripts import migrar_layout_intake as mli

    base = _caso_legacy_email(tmp_casos_root, "EV-149-T5B", ficheros={
        "03_Email/2026-02-01_asunto.eml": b"e",
        "03_Email/_exported_ids.json": b'{"a": [1]}',
    })                                          # raíz AUSENTE en el plan → «mover»
    antes = _arbol(base)
    original = shutil.move

    def move_que_hace_aparecer_la_raiz(src, dst):
        # un email_export concurrente escribe el estado de canal en la raíz durante la fase 1
        (base / "_exported_ids.json").write_bytes(b'{"a": [9]}')
        return original(src, dst)

    monkeypatch.setattr(shutil, "move", move_que_hace_aparecer_la_raiz)
    with pytest.raises(RuntimeError, match="apareci"):
        mli.migrar("EV-149-T5B", dry_run=False)
    despues = _arbol(base)
    despues.pop("_exported_ids.json")          # lo escribió el «concurrente», no la migración
    assert despues == antes                     # todo lo movido volvió; nada borrado
    assert (base / "03_Email" / "_exported_ids.json").read_bytes() == b'{"a": [1]}'


def test_t5c_la_raiz_cambia_antes_del_unlink_no_se_borra_y_se_reporta(tmp_casos_root,
                                                                      monkeypatch):
    import shutil

    from scripts import migrar_layout_intake as mli

    base = _caso_legacy_email(tmp_casos_root, "EV-149-T5C", ficheros={
        "03_Email/2026-02-01_asunto.eml": b"e",
        "03_Email/_exported_ids.json": b'{"a": [1]}',
    }, raiz=b'{"a": [1]}')                      # idénticos en el plan → «duplicado»
    original = shutil.move

    def move_que_cambia_la_raiz(src, dst):
        (base / "_exported_ids.json").write_bytes(b'{"a": [1, 2]}')   # añadió ids
        return original(src, dst)

    monkeypatch.setattr(shutil, "move", move_que_cambia_la_raiz)
    informe = {}
    plan = mli.migrar("EV-149-T5C", dry_run=False, informe=informe)
    assert plan                                                # la migración terminó
    assert (base / "03_Email" / "_exported_ids.json").read_bytes() == b'{"a": [1]}'  # no borrado
    assert (base / "_exported_ids.json").read_bytes() == b'{"a": [1, 2]}'
    assert informe["duplicados_borrados"] == []
    assert [n["fichero"] for n in informe["no_borrados"]] == ["03_Email/_exported_ids.json"]
    lote = base / plan[0].lote
    assert (lote / "2026-02-01_asunto.eml").is_file() and (lote / "_manifiesto.yaml").is_file()


def test_t6_el_homonimo_anidado_va_al_lote_y_entra_en_el_mapping_m9(tmp_casos_root):
    import json

    from scripts.migrar_layout_intake import migrar

    base = _caso_legacy_email(tmp_casos_root, "EV-149-T6", ficheros={
        "03_Email/2026-02-01_asunto.eml": b"e",
        "03_Email/hilo/_exported_ids.json": b"adjunto del cliente",
        "03_Email/_exported_ids.json": b"{}",
    })
    plan = migrar("EV-149-T6", dry_run=False)
    lote = base / plan[0].lote
    assert (lote / "hilo" / "_exported_ids.json").read_bytes() == b"adjunto del cliente"
    assert (base / "_exported_ids.json").read_bytes() == b"{}"        # el de canal, a la raíz
    assert "03_Email/hilo/_exported_ids.json" in plan[0].mapping
    m9 = json.loads((base / "_intake_hashes.json").read_text(encoding="utf-8"))
    assert m9["sha-adj"]["primary_path"] == f"{plan[0].lote}/hilo/_exported_ids.json"
    assert (base / m9["sha-adj"]["primary_path"]).is_file()
    # y el albarán del lote lo lista como documento
    from core.intake_lotes import leer_manifiesto
    assert any(i["relpath"] == "hilo/_exported_ids.json" for i in leer_manifiesto(lote)["items"])
