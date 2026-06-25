from __future__ import annotations
from datetime import datetime
from core.email_atomize import entregas as E


def _out_con_set(tmp_path):
    out = tmp_path / "Emails"
    (out / "mensajes").mkdir(parents=True)
    (out / "mensajes" / "m1.md").write_text("uno", encoding="utf-8")
    (out / "vistas").mkdir()
    (out / "vistas" / "dossier_del_burgo.md").write_text("dossier", encoding="utf-8")
    (out / "corpus.jsonl").write_text('{"x":1}\n', encoding="utf-8")
    (out / "CORREOS_LECTURA.md").write_text("lectura", encoding="utf-8")
    return out


def test_sella_copia_y_manifiesto(tmp_path):
    out = _out_con_set(tmp_path)
    dest = E.sellar(out, "entrega instructora", commit="abc123",
                    ahora=datetime(2026, 6, 25, 9, 0, 0))
    assert dest.name == "2026-06-25_entrega-instructora"
    assert dest.parent == out / "_entregas"
    # set entregable copiado congelado
    assert (dest / "mensajes" / "m1.md").read_text(encoding="utf-8") == "uno"
    assert (dest / "vistas" / "dossier_del_burgo.md").exists()
    assert (dest / "corpus.jsonl").exists()
    # _SELLO.md con metadatos + sha256 por fichero
    sello = (dest / "_SELLO.md").read_text(encoding="utf-8")
    assert "commit_motor: abc123" in sello
    assert "mensajes/m1.md" in sello
    # sha256 de "uno"
    import hashlib
    assert hashlib.sha256(b"uno").hexdigest() in sello


def test_append_only_segunda_entrega_no_pisa(tmp_path):
    out = _out_con_set(tmp_path)
    d1 = E.sellar(out, "x", commit="c", ahora=datetime(2026, 6, 25, 9, 0, 0))
    d2 = E.sellar(out, "x", commit="c", ahora=datetime(2026, 6, 25, 9, 0, 0))
    assert d1 != d2
    assert d1.exists() and d2.exists()
    assert d2.name == "2026-06-25_x_2"
