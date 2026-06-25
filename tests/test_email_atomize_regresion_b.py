from __future__ import annotations
from email.message import EmailMessage
from core.email_atomize import pipeline as P
from core.email_atomize import inline as I
from core.email_atomize.model import RegistroMensaje


def _gmail(mid, autor, de_cita, fecha_attr, cuerpo):
    m = EmailMessage()
    m["Message-ID"] = mid; m["Subject"] = "RV"; m["From"] = "c@x"; m["To"] = "d@x"
    m["Date"] = "Mon, 01 Jun 2026 10:00:00 +0200"
    m.set_content(autor)
    html = (f'<div>{autor}</div><div class="gmail_quote"><div class="gmail_attr">'
            f'El {fecha_attr}, Jaime &lt;{de_cita}&gt; escribió:</div>'
            f'<blockquote>{cuerpo}</blockquote></div>')
    m.add_alternative(html, subtype="html")
    return m.as_bytes()


def test_gmail_del_burgo_en_del_burgo_md(tmp_path):
    """Cita ESTRUCTURAL de PersonaUno → alta-reconstruida → aparece en del_burgo.md."""
    src = tmp_path / "03_Email"; out = tmp_path / "Emails"; src.mkdir()
    (tmp_path / "identidades.yaml").write_text(
        "personas:\n"
        "  - id: persona_uno\n"
        "    vigilada: true\n"
        "    direcciones: [ { email: per01a@example.invalid, estado: confirmada } ]\n",
        encoding="utf-8")
    (src / "a.eml").write_bytes(_gmail(
        "<c@x>", "Te reenvío.", "per01a@example.invalid", "1 de mayo de 2020",
        "contenido citado suficientemente largo para fingerprint PersonaUno"))
    P.atomize_dir(src, out, case_dir=tmp_path)
    db = (out / "_revision" / "del_burgo.md").read_text(encoding="utf-8")
    assert "per01a@example.invalid" in db


def test_headerless_no_inventa(tmp_path):
    """Cita sin cabecera parseable → NO se promueve nada (cero misatribución)."""
    src = tmp_path / "03_Email"; out = tmp_path / "Emails"; src.mkdir()
    m = EmailMessage()
    m["Message-ID"] = "<c@x>"; m["Subject"] = "x"; m["From"] = "c@x"; m["To"] = "d@x"
    m["Date"] = "Mon, 01 Jun 2026 10:00:00 +0200"
    m.set_content("Nota del autor.\n> cita sin cabecera parseable\n> mas cita\n")
    (src / "a.eml").write_bytes(m.as_bytes())
    P.atomize_dir(src, out)
    assert len(list((out / "mensajes").glob("*.md"))) == 1   # solo el portador


def test_fecha_posterior_nunca_alta():
    """Fecha de la cita POSTERIOR al portador → media + fecha_incoherente, NUNCA alta."""
    ra = RegistroMensaje(msg_id="MSG-1", fecha_iso="2026-06-01", de="c@x", cuerpo="x", capa="A")
    raw = _gmail("<c@x>", "x", "per01a@example.invalid", "1 de junio de 2027",
                 "cuerpo citado con fecha posterior al portador, imposible cronologicamente")
    res = I.reconstruir(ra, raw)
    assert all(s.de != "per01a@example.invalid" for s in res.candidatos)  # NO promovido
    assert any(p.de == "per01a@example.invalid" and "fecha_incoherente" in p.motivo
               for p in res.punteros)
