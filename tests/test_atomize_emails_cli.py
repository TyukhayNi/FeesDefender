from __future__ import annotations
from email.message import EmailMessage
import scripts.atomize_emails as cli


def _eml(mid, subj):
    m = EmailMessage(); m["Message-ID"] = mid; m["Subject"] = subj
    m["Date"] = "Thu, 12 Jun 2026 10:00:00 +0200"; m["From"] = "a@x"; m["To"] = "b@x"
    m.set_content("c"); return m.as_bytes()


def test_cli_con_src_y_out_explicitos(tmp_path, capsys):
    src = tmp_path / "03_Email"; out = tmp_path / "Emails"; src.mkdir()
    (src / "2026-06-12_a.eml").write_bytes(_eml("<a@x>", "Uno"))
    rc = cli.main(["--src", str(src), "--out", str(out)])
    assert rc == 0
    assert (out / "mensajes").is_dir()
    assert list((out / "mensajes").glob("*.md"))
    captured = capsys.readouterr().out
    assert "mensajes" in captured.lower()


def test_cli_entrega_invoca_sellar(monkeypatch, tmp_path, capsys):
    import scripts.atomize_emails as CLI
    from core.email_atomize import pipeline as P
    from core.email_atomize.pipeline import AtomizeReport

    llamadas = {}

    def fake_atomize_case(ref):
        return AtomizeReport(mensajes=1, notas=["vista rota: persona 'x' no existe"])

    def fake_out_dir(ref):
        return tmp_path / "Emails"

    def fake_sellar(out_dir, descr):
        llamadas["out_dir"] = out_dir
        llamadas["descr"] = descr
        return tmp_path / "Emails" / "_entregas" / "2026-06-25_x"

    monkeypatch.setattr(P, "atomize_case", fake_atomize_case)
    monkeypatch.setattr(P, "emails_out_dir", fake_out_dir)
    monkeypatch.setattr(P, "sellar_entrega", fake_sellar)

    rc = CLI.main(["--ref", "W-02VND1", "--entrega", "entrega instructora"])
    assert rc == 0
    assert llamadas["descr"] == "entrega instructora"
    assert llamadas["out_dir"] == tmp_path / "Emails"
    cap = capsys.readouterr()
    assert "Entrega sellada" in cap.out
    assert "NOTA" in cap.err and "no existe" in cap.err   # report.notas surfaced en stderr
