from __future__ import annotations
import json
from email.message import EmailMessage
from core.email_atomize import pipeline as P


def _msg(mid, subject, body="cuerpo", fecha="Thu, 12 Jun 2026 10:00:00 +0200",
         attachments=None):
    m = EmailMessage()
    m["Message-ID"] = mid
    m["Subject"] = subject
    m["Date"] = fecha
    m["From"] = "Jaime <per01c@example.invalid>"
    m["To"] = "b@x"
    m.set_content(body)
    for fn, mime, data in attachments or []:
        maint, _, sub = mime.partition("/")
        m.add_attachment(data, maintype=maint, subtype=sub, filename=fn)
    return m.as_bytes()


def test_e2e_atomiza_a_directorio(tmp_path):
    src = tmp_path / "03_Email"
    out = tmp_path / "Emails"
    src.mkdir()
    # mensaje con adjunto
    (src / "2026-06-12_a.eml").write_bytes(
        _msg("<a@x>", "Oferta", attachments=[("contrato.pdf", "application/pdf", b"%PDF datos")])
    )
    # padre que embebe a <a@x> (duplicado por Message-ID) + su propio mensaje
    padre = EmailMessage()
    padre["Message-ID"] = "<padre@x>"; padre["Subject"] = "RV: Oferta"
    padre["Date"] = "Fri, 13 Jun 2026 09:00:00 +0200"; padre["From"] = "c@x"; padre["To"] = "d@x"
    padre.set_content("Te reenvío.")
    padre.add_attachment(
        _msg("<a@x>", "Oferta", attachments=[("contrato.pdf", "application/pdf", b"%PDF datos")]),
        maintype="message", subtype="rfc822", filename="a.eml")
    (src / "2026-06-13_padre.eml").write_bytes(padre.as_bytes())

    rep = P.atomize_dir(src, out)

    # 2 mensajes únicos: <a@x> (colapsado de suelto+embebido) y <padre@x>
    mds = sorted((out / "mensajes").glob("*.md"))
    assert len(mds) == 2
    # corpus tiene meta + 2 filas
    corpus = (out / "corpus.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(corpus) == 3
    # registro congelado presente
    reg = json.loads((out / "_registro.json").read_text(encoding="utf-8"))
    assert reg["_no_editar"] is True
    assert len(reg["mensajes"]) == 2
    # un adjunto único
    assert (out / "INDICE_ADJUNTOS.md").exists()
    assert (out / "CORREOS_LECTURA.md").exists()
    atts = list((out / "adjuntos").glob("*"))
    assert any(p.suffix == ".pdf" for p in atts)
    assert rep.mensajes == 2


def test_e2e_idempotente_no_renumera(tmp_path):
    src = tmp_path / "03_Email"; out = tmp_path / "Emails"; src.mkdir()
    (src / "2026-06-12_a.eml").write_bytes(_msg("<a@x>", "Uno"))
    P.atomize_dir(src, out)
    reg1 = json.loads((out / "_registro.json").read_text(encoding="utf-8"))
    # añadir un segundo .eml y re-correr
    (src / "2026-06-13_b.eml").write_bytes(_msg("<b@x>", "Dos"))
    P.atomize_dir(src, out)
    reg2 = json.loads((out / "_registro.json").read_text(encoding="utf-8"))
    # <a@x> conserva su MSG-id original
    assert reg1["mensajes"]["a@x"]["id"] == reg2["mensajes"]["a@x"]["id"] == "MSG-00001"
    assert reg2["mensajes"]["b@x"]["id"] == "MSG-00002"
