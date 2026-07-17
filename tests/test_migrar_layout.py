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
