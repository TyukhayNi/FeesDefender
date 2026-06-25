from __future__ import annotations
import json
from email.message import EmailMessage
from core.email_atomize import pipeline as P


def _carrier_gmail(mid, autor, de_cita, fecha_attr, asunto_cita, cuerpo_cita):
    """Portador con cita ESTRUCTURAL (gmail_quote HTML) → promovible a alta-reconstruida."""
    m = EmailMessage()
    m["Message-ID"] = mid
    m["Subject"] = "RV: " + asunto_cita
    m["Date"] = "Mon, 01 Jun 2026 10:00:00 +0200"
    m["From"] = "c@x"
    m["To"] = "d@x"
    m.set_content(autor)
    html = (f"<div>{autor}</div><div class=\"gmail_quote\">"
            f"<div class=\"gmail_attr\">El {fecha_attr}, Jaime &lt;{de_cita}&gt; escribió:</div>"
            f"<blockquote>{cuerpo_cita}</blockquote></div>")
    m.add_alternative(html, subtype="html")
    return m.as_bytes()


def test_layerb_promueve_y_no_renumera_capaA(tmp_path):
    src = tmp_path / "03_Email"; out = tmp_path / "Emails"; src.mkdir()
    (tmp_path / "identidades.yaml").write_text(
        "personas:\n"
        "  - id: persona_uno\n"
        "    vigilada: true\n"
        "    direcciones: [ { email: per01a@example.invalid, estado: confirmada } ]\n",
        encoding="utf-8")
    (src / "2026-06-01_carrier.eml").write_bytes(_carrier_gmail(
        "<carrier@x>", "Te reenvío.", "per01a@example.invalid", "1 de mayo de 2020", "Tibidabo",
        "contenido citado suficientemente largo para superar el floor de 24"))
    rep = P.atomize_dir(src, out, case_dir=tmp_path)
    # Capa A: 1 portador; Capa B: 1 reconstruida (PersonaUno)
    mds = sorted((out / "mensajes").glob("*.md"))
    assert len(mds) == 2
    reg = json.loads((out / "_registro.json").read_text(encoding="utf-8"))
    assert reg["version"] == 2 and len(reg["mensajes_fp"]) == 1     # 1 fp-keyed B
    assert (out / "_revision" / "del_burgo.md").exists()
    db = (out / "_revision" / "del_burgo.md").read_text(encoding="utf-8")
    assert "per01a@example.invalid" in db
    assert rep.reconstruidos_b == 1
    # idempotencia: re-run no renumera ni duplica
    P.atomize_dir(src, out, case_dir=tmp_path)
    reg2 = json.loads((out / "_registro.json").read_text(encoding="utf-8"))
    assert reg2["mensajes_fp"] == reg["mensajes_fp"]
    assert len(sorted((out / "mensajes").glob("*.md"))) == 2


def test_layerb_headerless_no_promueve_va_a_cola(tmp_path):
    src = tmp_path / "03_Email"; out = tmp_path / "Emails"; src.mkdir()
    m = EmailMessage(); m["Message-ID"] = "<c@x>"; m["Subject"] = "x"
    m["Date"] = "Mon, 01 Jun 2026 10:00:00 +0200"; m["From"] = "c@x"; m["To"] = "d@x"
    m.set_content("Mi nota.\n> cita sin cabecera parseable\n> mas cita\n")
    (src / "2026-06-01_c.eml").write_bytes(m.as_bytes())
    P.atomize_dir(src, out)
    assert len(sorted((out / "mensajes").glob("*.md"))) == 1   # no se promueve nada
    assert (out / "_revision" / "cola.md").exists()
    assert "MSG-00001" in (out / "_revision" / "cola.md").read_text(encoding="utf-8")
