"""Tests del script de migración in situ de 05_CRM a buckets (D12-D13).

Cubre los tres requisitos de D14 para el script de migración:

- **Idempotencia**: re-ejecutar el plan tras aplicar no produce más movimientos.
- **Preservación de la cache OCR**: tras migrar, ``extractor.extract_all``
  hace *skip* de todos los documentos (no re-OCRiza) — se re-llavea el state
  por ``rel_path`` y los ``.txt`` quedan donde están (slug = stem).
- **Colisión de stem**: dos ficheros homónimos de ramas distintas que
  confluyen al mismo bucket → el segundo se sufija ``__1`` y su ``.txt`` se
  renombra (state re-llaveado), sin re-OCR.

Además: re-llave del manifest (físicos + alias-only) y refresco de
``by_carpeta`` en ``_caso.md``.
"""

from __future__ import annotations

import hashlib
import importlib
import json

import pytest


@pytest.fixture
def mods(tmp_casos_root):
    """Recarga los módulos core que cachean ``caso_path`` en import-time."""
    from core import case_manager, extractor, intake_manifest, inventory

    importlib.reload(case_manager)
    importlib.reload(intake_manifest)
    importlib.reload(inventory)
    importlib.reload(extractor)

    from scripts import migrate_05crm_buckets as mig
    importlib.reload(mig)

    return {
        "cm": case_manager,
        "extractor": extractor,
        "inventory": inventory,
        "mig": mig,
    }


# ---------------------------------------------------------------------------
# Helpers de construcción del caso sintético
# ---------------------------------------------------------------------------

def _write_crm_file(case_dir, rel_within_crm, content):
    p = case_dir / "00_Input" / "05_CRM" / rel_within_crm
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(content)
    return p


def _seed_extract_state(case_dir, entries):
    """entries: {input_rel: (content_bytes, slug)} → escribe state + .txt.

    Usa el formato real del extractor: ``{"extractor_version": N, "files": {…}}``.
    """
    from core.extractor import EXTRACTOR_VERSION

    raw = case_dir / "01_Procesado" / "raw_text"
    raw.mkdir(parents=True, exist_ok=True)
    files = {}
    for input_rel, (content, slug) in entries.items():
        sha = hashlib.sha256(content).hexdigest()
        files[input_rel] = {"source_sha256": sha, "method": "pdf_test", "chars": len(content)}
        (raw / f"{slug}.txt").write_text("texto extraido", encoding="utf-8")
    (raw / "_extract_state.json").write_text(
        json.dumps({"extractor_version": EXTRACTOR_VERSION, "files": files},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# 1. build_move_plan — mapeo rama → bucket (con fallback override)
# ---------------------------------------------------------------------------

def test_build_move_plan_mapea_ramas_a_buckets(mods, tmp_casos_root):
    cm, mig = mods["cm"], mods["mig"]
    case_id = "MIG-1"
    case_dir = cm.ensure_case(case_id)

    _write_crm_file(case_dir, "Civil/1ª Instancia/Declarativo/Demanda/demanda.pdf", b"A")
    _write_crm_file(case_dir, "Civil/Preliminares/Demanda/solicitud_dp.pdf", b"B")
    _write_crm_file(case_dir, "General/nota.pdf", b"C")
    _write_crm_file(case_dir, "99_Sin categoria/444/requerimiento.pdf", b"D")

    plan = mig.build_move_plan(case_id, {"444": "05_Diligencias_Preliminares"})

    dests = {mv.old_crm_rel: mv.new_crm_rel for mv in plan.moves}
    assert dests["Civil/1ª Instancia/Declarativo/Demanda/demanda.pdf"] == "01_Demanda/demanda.pdf"
    assert dests["Civil/Preliminares/Demanda/solicitud_dp.pdf"] == "05_Diligencias_Preliminares/solicitud_dp.pdf"
    assert dests["General/nota.pdf"] == "99_Otros/nota.pdf"
    # Fallback 444 con override → 05 (anti-sobrecaptura Preliminares)
    assert dests["99_Sin categoria/444/requerimiento.pdf"] == "05_Diligencias_Preliminares/requerimiento.pdf"
    assert plan.keeps == []


def test_build_move_plan_fallback_sin_override_se_conserva(mods, tmp_casos_root):
    cm, mig = mods["cm"], mods["mig"]
    case_id = "MIG-KEEP"
    case_dir = cm.ensure_case(case_id)
    _write_crm_file(case_dir, "99_Sin categoria/999/huerfano.pdf", b"X")

    plan = mig.build_move_plan(case_id, {})  # sin override

    assert plan.moves == []
    assert "99_Sin categoria/999/huerfano.pdf" in plan.keeps


# ---------------------------------------------------------------------------
# 2. apply — mueve, aplana, e idempotencia
# ---------------------------------------------------------------------------

def test_apply_mueve_a_buckets_y_es_idempotente(mods, tmp_casos_root):
    cm, mig = mods["cm"], mods["mig"]
    case_id = "MIG-2"
    case_dir = cm.ensure_case(case_id)
    crm = case_dir / "00_Input" / "05_CRM"

    _write_crm_file(case_dir, "Civil/1ª Instancia/Declarativo/Demanda/d.pdf", b"A")
    _write_crm_file(case_dir, "General/n.pdf", b"C")

    fb = {"444": "05_Diligencias_Preliminares"}
    plan = mig.build_move_plan(case_id, fb)
    mig.apply_move_plan(case_id, plan, fb)

    assert (crm / "01_Demanda" / "d.pdf").is_file()
    assert (crm / "99_Otros" / "n.pdf").is_file()
    # El árbol profundo desapareció (pruning de vacíos)
    assert not (crm / "Civil").exists()
    assert not (crm / "General").exists()

    # Idempotencia: segundo plan no mueve nada
    plan2 = mig.build_move_plan(case_id, fb)
    assert plan2.moves == []
    assert len(plan2.noops) == 2


# ---------------------------------------------------------------------------
# 3. Preservación de la cache OCR — extract_all hace skip de todo
# ---------------------------------------------------------------------------

def test_apply_preserva_cache_ocr_no_reocr(mods, tmp_casos_root):
    cm, mig, extractor = mods["cm"], mods["mig"], mods["extractor"]
    case_id = "MIG-OCR"
    case_dir = cm.ensure_case(case_id)

    content_a, content_b = b"%PDF demanda real", b"%PDF requerimiento real"
    _write_crm_file(case_dir, "Civil/1ª Instancia/Declarativo/Demanda/demanda.pdf", content_a)
    _write_crm_file(case_dir, "99_Sin categoria/444/requerimiento.pdf", content_b)

    # State + .txt pre-existentes (como si el pipeline ya hubiera OCRizado).
    _seed_extract_state(case_dir, {
        "05_CRM/Civil/1ª Instancia/Declarativo/Demanda/demanda.pdf": (content_a, "demanda"),
        "05_CRM/99_Sin categoria/444/requerimiento.pdf": (content_b, "requerimiento"),
    })

    fb = {"444": "05_Diligencias_Preliminares"}
    plan = mig.build_move_plan(case_id, fb)
    mig.apply_move_plan(case_id, plan, fb)

    # State re-llaveado a los nuevos rel_path; los .txt NO se movieron.
    state = json.loads(
        (case_dir / "01_Procesado" / "raw_text" / "_extract_state.json").read_text(encoding="utf-8")
    )
    files = state["files"]
    assert state["extractor_version"] == extractor.EXTRACTOR_VERSION
    assert "05_CRM/01_Demanda/demanda.pdf" in files
    assert "05_CRM/05_Diligencias_Preliminares/requerimiento.pdf" in files
    assert "05_CRM/Civil/1ª Instancia/Declarativo/Demanda/demanda.pdf" not in files
    raw = case_dir / "01_Procesado" / "raw_text"
    assert (raw / "demanda.txt").exists()
    assert (raw / "requerimiento.txt").exists()

    # Prueba fuerte: extract_all hace SKIP de todo (no re-OCR).
    results = extractor.extract_all(case_id)
    assert results, "extract_all no devolvió resultados"
    assert all(r.skipped for r in results), \
        f"se re-OCRizó algún doc: {[(r.rel_path, r.skipped) for r in results]}"


# ---------------------------------------------------------------------------
# 4. Re-llave del manifest (físicos + alias-only)
# ---------------------------------------------------------------------------

def test_apply_rellavea_manifest(mods, tmp_casos_root):
    cm, mig = mods["cm"], mods["mig"]
    case_id = "MIG-MAN"
    case_dir = cm.ensure_case(case_id)

    content = b"contrato"
    sha = hashlib.sha256(content).hexdigest()
    _write_crm_file(case_dir, "Civil/1ª Instancia/Declarativo/Demanda/contrato.pdf", content)

    manifest = {
        # físico en 05_CRM como alias (primary en Drive)
        sha: {
            "primary_path": "01_Drive EV/contrato.pdf",
            "aliases": [{
                "path": "05_CRM/Civil/1ª Instancia/Declarativo/Demanda/contrato.pdf",
                "source": "crm", "expediente_id": "444",
            }],
        },
        # alias-only (sin fichero físico) bajo una rama → 99_Otros por string
        "sha-ghost": {
            "primary_path": "01_Drive EV/ghost.pdf",
            "aliases": [{"path": "05_CRM/Civil/Apelacion/ghost.pdf", "source": "crm"}],
        },
    }
    (case_dir / "00_Input" / "_intake_hashes.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8",
    )

    fb = {"444": "05_Diligencias_Preliminares"}
    plan = mig.build_move_plan(case_id, fb)
    mig.apply_move_plan(case_id, plan, fb)

    data = json.loads((case_dir / "00_Input" / "_intake_hashes.json").read_text(encoding="utf-8"))
    assert data[sha]["aliases"][0]["path"] == "05_CRM/01_Demanda/contrato.pdf"
    # alias-only re-llaveado por string (Apelacion → 99_Otros), sin fichero
    assert data["sha-ghost"]["aliases"][0]["path"] == "05_CRM/99_Otros/ghost.pdf"


# ---------------------------------------------------------------------------
# 5. Colisión de stem entre ramas que confluyen al mismo bucket (D13)
# ---------------------------------------------------------------------------

def test_apply_colision_de_stem_sufija_sin_robar_txt(mods, tmp_casos_root):
    """Dos homónimos de ramas distintas → mismo bucket: el 2º se sufija ``__1``.

    En el pipeline real ambos stems "doc" comparten UN solo ``doc.txt`` (el
    extractor llavea por slug de stem). La migración NO renombra ese ``.txt``
    (sería robárselo al no-sufijado): el sufijado re-OCRiza solo él la próxima
    vez. Orden de proceso: 'Civil…' < 'General' → Civil conserva el nombre,
    General se sufija.
    """
    cm, mig = mods["cm"], mods["mig"]
    case_id = "MIG-COL"
    case_dir = cm.ensure_case(case_id)
    crm = case_dir / "00_Input" / "05_CRM"
    raw = case_dir / "01_Procesado" / "raw_text"

    from core.extractor import EXTRACTOR_VERSION

    c1, c2 = b"%PDF civil doc", b"%PDF general doc"
    _write_crm_file(case_dir, "Civil/1ª Instancia/Declarativo/doc.pdf", c1)
    _write_crm_file(case_dir, "General/doc.pdf", c2)
    # UN solo doc.txt compartido (realidad del extractor con stems iguales).
    raw.mkdir(parents=True, exist_ok=True)
    (raw / "doc.txt").write_text("texto", encoding="utf-8")
    (raw / "_extract_state.json").write_text(json.dumps({
        "extractor_version": EXTRACTOR_VERSION,
        "files": {
            "05_CRM/Civil/1ª Instancia/Declarativo/doc.pdf":
                {"source_sha256": hashlib.sha256(c1).hexdigest(), "method": "t", "chars": 1},
            "05_CRM/General/doc.pdf":
                {"source_sha256": hashlib.sha256(c2).hexdigest(), "method": "t", "chars": 1},
        },
    }), encoding="utf-8")

    fb = {"444": "05_Diligencias_Preliminares"}
    plan = mig.build_move_plan(case_id, fb)

    # Colisión detectada y resuelta con sufijo en el segundo (General).
    assert len(plan.collisions) == 1
    suffixed = [mv for mv in plan.moves if mv.suffixed]
    assert len(suffixed) == 1
    assert suffixed[0].old_crm_rel == "General/doc.pdf"
    assert suffixed[0].new_crm_rel == "99_Otros/doc__1.pdf"

    summary = mig.apply_move_plan(case_id, plan, fb)

    assert (crm / "99_Otros" / "doc.pdf").is_file()       # Civil, conserva nombre
    assert (crm / "99_Otros" / "doc__1.pdf").is_file()    # General, sufijado
    # El .txt NO se renombró (no se le roba al no-sufijado); doc__1.txt no existe.
    assert (raw / "doc.txt").exists()
    assert not (raw / "doc__1.txt").exists()
    assert summary["will_reocr"] == 1

    # state re-llaveado a los dos nuevos rel.
    new_files = json.loads((raw / "_extract_state.json").read_text(encoding="utf-8"))["files"]
    assert "05_CRM/99_Otros/doc.pdf" in new_files
    assert "05_CRM/99_Otros/doc__1.pdf" in new_files
    assert "05_CRM/General/doc.pdf" not in new_files


# ---------------------------------------------------------------------------
# 6. Refresco de by_carpeta en _caso.md
# ---------------------------------------------------------------------------

def test_apply_refresca_by_carpeta(mods, tmp_casos_root):
    cm, mig = mods["cm"], mods["mig"]
    case_id = "MIG-BC"
    case_dir = cm.ensure_case(case_id)

    cm.update_pull_state(
        case_id, "444",
        element="expedientes_judiciales",
        by_carpeta={
            "Civil/1ª Instancia/Declarativo/Demanda": 23,
            "Civil/Preliminares": 13,
            "General": 4,
            "99_Sin categoria/444": 18,
        },
    )
    # Un fichero para que haya algo que mover (si no, apply sale temprano).
    _write_crm_file(case_dir, "General/n.pdf", b"C")

    fb = {"444": "05_Diligencias_Preliminares"}
    plan = mig.build_move_plan(case_id, fb)
    mig.apply_move_plan(case_id, plan, fb)

    state = cm.read_pull_state(case_id, "444")
    assert state["by_carpeta"] == {
        "01_Demanda": 23,
        "05_Diligencias_Preliminares": 31,   # Preliminares(13) + fallback 444(18)
        "99_Otros": 4,
    }
