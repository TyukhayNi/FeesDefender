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
