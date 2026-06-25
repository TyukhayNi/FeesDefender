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


def _carrier_outlook_plano(mid, de_cita, fecha_label, asunto_cita, cuerpo_cita):
    """Portador de TEXTO PLANO con bloque outlook_es (De:/Enviado:/Para:/Asunto:), SIN
    blockquote → estructural=False → promovible a media-reconstruida."""
    m = EmailMessage()
    m["Message-ID"] = mid
    m["Subject"] = "RV: " + asunto_cita
    m["Date"] = "Mon, 01 Jun 2026 10:00:00 +0200"
    m["From"] = "c@x"
    m["To"] = "d@x"
    cuerpo = (f"Te reenvio el correo de abajo.\n\n"
              f"De: Jaime <{de_cita}>\nEnviado: {fecha_label}\nPara: x@y\n"
              f"Asunto: {asunto_cita}\n{cuerpo_cita}\n")
    m.set_content(cuerpo)
    return m.as_bytes()


def test_layerb_outlook_plano_promueve_media_reconstruida(tmp_path):
    src = tmp_path / "03_Email"; out = tmp_path / "Emails"; src.mkdir()
    (src / "2026-06-01_carrier_plano.eml").write_bytes(_carrier_outlook_plano(
        "<carrier-plano@x>", "alguien@x.com", "1 de mayo de 2020", "Tibidabo",
        "contenido citado suficientemente largo para superar el floor de 24 chars"))
    rep = P.atomize_dir(src, out, case_dir=tmp_path)
    # Capa A: 1 portador; Capa B: 1 media-reconstruida
    mds = sorted((out / "mensajes").glob("*.md"))
    assert len(mds) == 2
    # Aislar el atom B por su contenido (no por nombre de fichero):
    b_mds = [p for p in mds if "confianza: media-reconstruida" in p.read_text(encoding="utf-8")]
    assert len(b_mds) == 1
    contenido_b = b_mds[0].read_text(encoding="utf-8")
    assert "confianza: media-reconstruida" in contenido_b
    assert "en_revision: true" in contenido_b
    # reconstruidos.md + reconstruidos.jsonl existen y listan el atom:
    assert (out / "_revision" / "reconstruidos.md").exists()
    assert (out / "_revision" / "reconstruidos.jsonl").exists()
    rec = (out / "_revision" / "reconstruidos.md").read_text(encoding="utf-8")
    assert "alguien@x.com" in rec and "2020-05-01" in rec
    jl = [l for l in (out / "_revision" / "reconstruidos.jsonl").read_text(
        encoding="utf-8").splitlines() if l.strip()]
    assert len(jl) == 1 and json.loads(jl[0])["de"] == "alguien@x.com"
    # Contadores:
    assert rep.reconstruidos_b == 1
    assert rep.reconstruidos_media == 1
    # Idempotencia: re-run no renumera ni duplica
    reg = json.loads((out / "_registro.json").read_text(encoding="utf-8"))
    P.atomize_dir(src, out, case_dir=tmp_path)
    reg2 = json.loads((out / "_registro.json").read_text(encoding="utf-8"))
    assert reg2["mensajes_fp"] == reg["mensajes_fp"]
    assert len(sorted((out / "mensajes").glob("*.md"))) == 2


def _eml_limpio(mid, de, fecha_rfc, asunto, cuerpo):
    """Mensaje limpio de Capa A (autor directo) cuyo cuerpo será luego citado por un portador."""
    m = EmailMessage()
    m["Message-ID"] = mid; m["Subject"] = asunto
    m["Date"] = fecha_rfc; m["From"] = de; m["To"] = "x@y"
    m.set_content(cuerpo)
    return m.as_bytes()


def test_layerb_media_reconstruida_dedup_contra_capa_a(tmp_path):
    # El cuerpo citado en el portador plano REPRODUCE el de un .eml limpio ya presente:
    cuerpo = "contenido identico citado suficientemente largo para superar el floor de 24 chars"
    src = tmp_path / "03_Email"; out = tmp_path / "Emails"; src.mkdir()
    (src / "2020-05-01_limpio.eml").write_bytes(_eml_limpio(
        "<limpio@x>", "alguien@x.com", "Fri, 01 May 2020 09:00:00 +0200", "Tibidabo", cuerpo))
    (src / "2026-06-01_carrier_plano.eml").write_bytes(_carrier_outlook_plano(
        "<carrier-plano@x>", "alguien@x.com", "1 de mayo de 2020", "Tibidabo", cuerpo))
    rep = P.atomize_dir(src, out, case_dir=tmp_path)
    mds = sorted((out / "mensajes").glob("*.md"))
    # NO se acuña un .md B nuevo: solo el .md de Capa A del mensaje limpio.
    b_mds = [p for p in mds if "confianza: media-reconstruida" in p.read_text(encoding="utf-8")]
    assert b_mds == [], "una cita que reproduce un .eml limpio NO debe acuñar un B nuevo"
    assert rep.upgrades >= 1   # el puente de fidelidad disparó (la cita es copia de un .eml limpio)


def _carrier_solo_capa_a(mid):
    """Portador SIN cita promovible: cuerpo de autor, sin bloque De:/Enviado: ni blockquote.
    Su único atom es Capa A (confianza alta), no debe ganar campos Layer B."""
    m = EmailMessage()
    m["Message-ID"] = mid; m["Subject"] = "Nota interna"
    m["Date"] = "Mon, 01 Jun 2026 10:00:00 +0200"; m["From"] = "c@x"; m["To"] = "d@x"
    m.set_content("Esta es una nota de autor sin citas ni cabeceras reenviadas.\nSaludos.\n")
    return m.as_bytes()


def test_capa_a_md_no_gana_campos_layer_b(tmp_path):
    src = tmp_path / "03_Email"; out = tmp_path / "Emails"; src.mkdir()
    (src / "2026-06-01_nota.eml").write_bytes(_carrier_solo_capa_a("<nota@x>"))
    P.atomize_dir(src, out, case_dir=tmp_path)
    mds = sorted((out / "mensajes").glob("*.md"))
    assert len(mds) == 1                                  # solo el atom de Capa A
    md = mds[0].read_text(encoding="utf-8")
    assert "capa: A" in md and "confianza: alta\n" in md
    # El frontmatter de Capa A NO gana campos de Layer B ni banner:
    for marca in ("reconstruido_desde_cita: true", "reconstruido_de:", "en_revision: true",
                  "fecha_inferida: true", "ambiguedad_profundidad: true", "fingerprint:",
                  "confianza: media-reconstruida", "> AUTORÍA POR VERIFICAR",
                  "> RECONSTRUIDO DESDE CITA", "> AUTORÍA POR RECONSTRUIR"):
        assert marca not in md, f"Capa A no debe contener: {marca!r}"


def test_capa_a_md_byte_identico_entre_corridas(tmp_path):
    # Mismo portador Capa A; el .md debe ser idéntico tras dos corridas (idempotencia + no churn).
    src = tmp_path / "03_Email"; out = tmp_path / "Emails"; src.mkdir()
    (src / "2026-06-01_nota.eml").write_bytes(_carrier_solo_capa_a("<nota@x>"))
    P.atomize_dir(src, out, case_dir=tmp_path)
    md1 = sorted((out / "mensajes").glob("*.md"))[0].read_bytes()
    P.atomize_dir(src, out, case_dir=tmp_path)
    md2 = sorted((out / "mensajes").glob("*.md"))[0].read_bytes()
    assert md1 == md2                                     # byte-idéntico entre corridas
