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


def test_layerb_enviado_el_promueve_media_reconstruida(tmp_path):
    src = tmp_path / "03_Email"; out = tmp_path / "Emails"; src.mkdir()
    m = EmailMessage()
    m["Message-ID"] = "<carrier-el@x>"; m["Subject"] = "RV: Tibidabo"
    m["Date"] = "Mon, 01 Jun 2026 10:00:00 +0200"; m["From"] = "c@x"; m["To"] = "d@x"
    m.set_content("Te reenvio:\n\n-----Mensaje original-----\nDe: Jaime <alguien@x.com>\n"
                  "Enviado el: viernes, 4 de octubre de 2024 11:40\nPara: x@y\nAsunto: Tibidabo\n"
                  "contenido citado suficientemente largo para superar el floor de 24 chars\n")
    (src / "2026-06-01_carrier_el.eml").write_bytes(m.as_bytes())
    rep = P.atomize_dir(src, out, case_dir=tmp_path)
    b_mds = [p for p in (out/"mensajes").glob("*.md")
             if "confianza: media-reconstruida" in p.read_text(encoding="utf-8")]
    assert len(b_mds) == 1, "el bloque 'Enviado el:' con remitente válido debe promover ahora"
    assert rep.reconstruidos_media == 1
    md = b_mds[0].read_text(encoding="utf-8")
    assert "alguien@x.com" in md and "2024-10-04" in md


def test_layerb_remitente_apellido_coma_promueve(tmp_path):
    src = tmp_path / "03_Email"; out = tmp_path / "Emails"; src.mkdir()
    m = EmailMessage()
    m["Message-ID"] = "<carrier-coma@x>"; m["Subject"] = "RV: offer letter"
    m["Date"] = "Mon, 01 Jun 2026 10:00:00 +0200"; m["From"] = "c@x"; m["To"] = "d@x"
    m.set_content("Te reenvio:\n\n-----Mensaje original-----\n"
                  "De: PersonaCuatro, Eva <persona.cuatro@engelvoelkers.com>\n"
                  "Enviado el: lunes, 7 de julio de 2025 19:44\nPara: x@y\nAsunto: Re: offer letter\n"
                  "contenido citado suficientemente largo para superar el floor de 24 chars\n")
    (src / "2026-06-01_coma.eml").write_bytes(m.as_bytes())
    rep = P.atomize_dir(src, out, case_dir=tmp_path)
    b = [p for p in (out/"mensajes").glob("*.md")
         if "confianza: media-reconstruida" in p.read_text(encoding="utf-8")]
    assert len(b) == 1
    md = b[0].read_text(encoding="utf-8")
    assert "de: persona.cuatro@engelvoelkers.com" in md and "2025-07-07" in md


# ---------------------------------------------------------------------------
# Body-scan de remitente desde el cuerpo de la cita (it. 2) — glue (spec §5 15-18)
# ---------------------------------------------------------------------------

def _carrier_html_apple_en_cuerpo(mid, autor, attr_line, cuerpo_cita):
    """Portador HTML: anclaje previo = prosa; atribución Apple = 1ª línea del blockquote.
    El de NO está en el anclaje → lo levanta el body-scan → media-reconstruida (atribucion_cuerpo)."""
    m = EmailMessage()
    m["Message-ID"] = mid; m["Subject"] = "RV: Tibidabo"
    m["Date"] = "Mon, 01 Jun 2026 10:00:00 +0200"; m["From"] = "c@x"; m["To"] = "d@x"
    m.set_content(autor)
    html = (f"<div>{autor}</div>"
            f"<blockquote>{attr_line}<br>{cuerpo_cita}</blockquote>")
    m.add_alternative(html, subtype="html")
    return m.as_bytes()


def test_layerb_bodyscan_apple_promueve_media_reconstruida(tmp_path):
    # §5.15 — pipeline completo, portador forma (a) Apple en el cuerpo → atom B media-reconstruida
    # con de correcto; corpus.jsonl con motivo=atribucion_cuerpo; aparece en reconstruidos.md.
    src = tmp_path / "03_Email"; out = tmp_path / "Emails"; src.mkdir()
    attr = "El 27 may 2024, a las 10:49, Isabel &lt;persona.cinco@engelvoelkers.com&gt; escribió:"
    (src / "2026-06-01_apple_body.eml").write_bytes(_carrier_html_apple_en_cuerpo(
        "<carrier-apple-body@x>", "Te reenvío esto.", attr,
        "contenido citado suficientemente largo para superar el floor de 24 chars"))
    rep = P.atomize_dir(src, out, case_dir=tmp_path)
    b_mds = [p for p in (out / "mensajes").glob("*.md")
             if "confianza: media-reconstruida" in p.read_text(encoding="utf-8")]
    assert len(b_mds) == 1, "la atribución Apple del cuerpo debe promover a media-reconstruida"
    md = b_mds[0].read_text(encoding="utf-8")
    assert "de: persona.cinco@engelvoelkers.com" in md and "2024-05-27" in md
    assert "en_revision: true" in md
    assert rep.reconstruidos_media == 1
    # Trazabilidad del media-reconstruida: lista en reconstruidos.md + reconstruidos.jsonl,
    # y el atom B aparece en corpus.jsonl con su de/confianza (el motivo atribucion_cuerpo se
    # afirma a nivel Segmento — ver test unitario; el schema de corpus/reconstruidos no lo expone).
    rec = (out / "_revision" / "reconstruidos.md").read_text(encoding="utf-8")
    assert "persona.cinco@engelvoelkers.com" in rec
    jl = [json.loads(l) for l in (out / "_revision" / "reconstruidos.jsonl").read_text(
        encoding="utf-8").splitlines() if l.strip()]
    assert any(r["de"] == "persona.cinco@engelvoelkers.com" for r in jl)
    corpus = (out / "corpus.jsonl")
    if corpus.exists():
        lineas = [json.loads(l) for l in corpus.read_text(encoding="utf-8").splitlines()
                  if l.strip() and not l.startswith('{"_README"')]
        b_recs = [r for r in lineas if r.get("de") == "persona.cinco@engelvoelkers.com"]
        assert b_recs and all(r.get("confianza") == "media-reconstruida" for r in b_recs), \
            "el atom B body-lifted aparece en corpus.jsonl como media-reconstruida"


def test_layerb_bodyscan_idempotente_277_capaA_byte_identico(tmp_path):
    # §5.17 — dos corridas: 0 renumerados, fp estables (Capa A byte-idéntica para los portadores).
    src = tmp_path / "03_Email"; out = tmp_path / "Emails"; src.mkdir()
    attr = "El 27 may 2024, a las 10:49, Isabel &lt;persona.cinco@engelvoelkers.com&gt; escribió:"
    (src / "2026-06-01_apple_body.eml").write_bytes(_carrier_html_apple_en_cuerpo(
        "<carrier-apple-body@x>", "Te reenvío esto.", attr,
        "contenido citado suficientemente largo para superar el floor de 24 chars"))
    P.atomize_dir(src, out, case_dir=tmp_path)
    md_a1 = [p for p in (out / "mensajes").glob("*.md")
             if "capa: A" in p.read_text(encoding="utf-8")]
    bytes_a1 = {p.name: p.read_bytes() for p in md_a1}
    reg = json.loads((out / "_registro.json").read_text(encoding="utf-8"))
    P.atomize_dir(src, out, case_dir=tmp_path)
    reg2 = json.loads((out / "_registro.json").read_text(encoding="utf-8"))
    assert reg2["mensajes_fp"] == reg["mensajes_fp"], "fp estables entre corridas"
    md_a2 = [p for p in (out / "mensajes").glob("*.md")
             if "capa: A" in p.read_text(encoding="utf-8")]
    bytes_a2 = {p.name: p.read_bytes() for p in md_a2}
    assert bytes_a1 == bytes_a2, "Capa A byte-idéntica entre corridas (cero churn)"


def _carrier_html_anchor_completo(mid, de_cita, fecha_attr, cuerpo_cita):
    """Portador HTML con gmail_attr que YA lleva de+fecha en el anclaje (NO levantada del cuerpo).
    Debe seguir alta-reconstruida: el graft solo topa lo levantado del cuerpo (§5.18)."""
    m = EmailMessage()
    m["Message-ID"] = mid; m["Subject"] = "RV: Tibidabo"
    m["Date"] = "Mon, 01 Jun 2026 10:00:00 +0200"; m["From"] = "c@x"; m["To"] = "d@x"
    m.set_content("Te reenvío.")
    html = (f'<div>Te reenvío.</div><div class="gmail_quote">'
            f'<div class="gmail_attr">El {fecha_attr}, Jaime &lt;{de_cita}&gt; escribió:</div>'
            f'<blockquote>{cuerpo_cita}</blockquote></div>')
    m.add_alternative(html, subtype="html")
    return m.as_bytes()


def test_layerb_regresion_estructural_anchor_completo_sigue_alta(tmp_path):
    # §5.18 — REGRESIÓN del peldaño alto: estructural + cabecera completa en anclaje_texto
    # (NO levantada del cuerpo) sigue alta-reconstruida. El graft solo topa lo del cuerpo.
    src = tmp_path / "03_Email"; out = tmp_path / "Emails"; src.mkdir()
    (src / "2026-06-01_anchor.eml").write_bytes(_carrier_html_anchor_completo(
        "<carrier-anchor@x>", "per01a@example.invalid", "1 de mayo de 2020",
        "contenido citado suficientemente largo para superar el floor de 24 chars"))
    P.atomize_dir(src, out, case_dir=tmp_path)
    a_mds = [p for p in (out / "mensajes").glob("*.md")
             if "confianza: alta-reconstruida" in p.read_text(encoding="utf-8")]
    assert len(a_mds) == 1, "el anchor completo estructural debe seguir alta-reconstruida"
    md = a_mds[0].read_text(encoding="utf-8")
    assert "de: per01a@example.invalid" in md
    assert "atribucion_cuerpo" not in md, "no es atribucion_cuerpo: el de vino del anclaje"


# ---------------------------------------------------------------------------
# it.3 — interior reenviado + parse c′ a nivel pipeline (dedup, idempotencia, Capa A byte-idéntica)
# ---------------------------------------------------------------------------

def _carrier_con_interior(mid, attr, bq, frm="persona.seis@engelvoelkers.com", fecha="Thu, 24 Jul 2025 10:00:00 +0200"):
    m = EmailMessage()
    m["Message-ID"] = mid; m["Subject"] = "Fwd: [PAIS_EXTRANJERO] docs"; m["Date"] = fecha
    m["From"] = frm; m["To"] = "nikolai@x"
    m.set_content("Os reenvío lo de Jaime.")
    html = (f'<div>Os reenvío.</div><div class="gmail_quote">'
            f'<div class="gmail_attr">{attr}</div><blockquote>{bq}</blockquote></div>')
    m.add_alternative(html, subtype="html")
    return m.as_bytes()


_BQ_PER01_WRAP = (
    "---------- Forwarded message ---------<br>"
    "De:<br>PersonaUno<br>&lt;<br>per01a@example.invalid<br>&gt;<br>"
    "Date: mié, 23 jul 2025 a las 12:37<br>Subject: [PAIS_EXTRANJERO] docs<br>"
    "To: Eva &lt;<br>persona.cuatro@engelvoelkers.com<br>&gt;<br>"
    "Os passo els documents de [PAIS_EXTRANJERO] amb prou substancia per al cos del missatge.")
_BQ_PER01_INLINE = (
    "---------- Forwarded message ---------<br>"
    "De: PersonaUno &lt;per01a@example.invalid&gt;<br>"
    "Date: mié, 23 jul 2025 a las 12:37<br>Subject: [PAIS_EXTRANJERO] docs<br>"
    "To: Eva &lt;persona.cuatro@engelvoelkers.com&gt;<br>"
    "Os passo els documents de [PAIS_EXTRANJERO] amb prou substancia per al cos del missatge.")


def test_layerb_interior_dedup_multi_portador(tmp_path):
    # el MISMO interior c′ (PersonaUno "[PAIS_EXTRANJERO] docs") citado en 2 portadores con wrap distinto
    # → UN solo atom B (mismo fingerprint), con procedencia len>=2. Poda consistente entre wraps.
    src = tmp_path / "03_Email"; out = tmp_path / "Emails"; src.mkdir()
    (src / "2025-07-24_a.eml").write_bytes(_carrier_con_interior(
        "<a@x>", "El mié, 23 jul 2025 a las 13:00, PersonaSeis &lt;persona.seis@engelvoelkers.com&gt; escribió:",
        _BQ_PER01_WRAP))
    (src / "2025-07-24_b.eml").write_bytes(_carrier_con_interior(
        "<b@x>", "El mié, 23 jul 2025 a las 14:00, Eva &lt;persona.cuatro@engelvoelkers.com&gt; escribió:",
        _BQ_PER01_INLINE, frm="persona.cuatro@engelvoelkers.com"))
    P.atomize_dir(src, out, case_dir=tmp_path)
    corpus = [json.loads(l) for l in (out / "corpus.jsonl").read_text(encoding="utf-8").splitlines()
              if l.strip() and not l.startswith("#")]
    interiores = [d for d in corpus if d.get("de") == "per01a@example.invalid"
                  and (d.get("asunto") or "").startswith("[PAIS_EXTRANJERO]")]
    assert len(interiores) == 1, "el mismo interior c′ en 2 portadores → UN solo atom B (dedup por fp)"
    assert len(interiores[0].get("procedencia") or []) >= 2, "con >=2 procedencias"
    assert interiores[0]["confianza"] == "media-reconstruida"


def test_layerb_interior_idempotente_y_capaA_byte_identico(tmp_path):
    import hashlib
    src = tmp_path / "03_Email"; out = tmp_path / "Emails"; src.mkdir()
    bq = (
        "Sent from Gmail Mobile<br>---------- Mensaje reenviado ---------<br>"
        "De:<br>PersonaCuatro, Eva<br>&lt;<br>persona.cuatro@engelvoelkers.com<br>&gt;<br>"
        "Fecha: El lun, 7 jul 2025 a las 19:44<br>Asunto: Re: offer letter TIBIDABO 8<br>"
        "Para: Consulado de [PAIS_EXTRANJERO] &lt;<br>contacto@org-qa.example<br>&gt;<br>"
        "Estimada PersonaSiete, adjunto remito la Contraoferta con sustancia suficiente.")
    (src / "2025-07-23_c.eml").write_bytes(_carrier_con_interior(
        "<c@x>", "On Wed, 23 Jul 2025 at 17:09, PersonaCuatro, Eva &lt;persona.cuatro@engelvoelkers.com&gt; wrote:",
        bq, frm="persona.cuatro@engelvoelkers.com", fecha="Wed, 23 Jul 2025 17:24:00 +0200"))

    def capa_a_hashes():
        h = {}
        for p in (out / "mensajes").glob("*.md"):
            t = p.read_text(encoding="utf-8")
            if "capa: A" in t:
                h[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
        return h

    P.atomize_dir(src, out, case_dir=tmp_path)
    # el interior Eva 7-jul (Contraoferta) emergió como atom B media-reconstruida net-new
    corpus = [json.loads(l) for l in (out / "corpus.jsonl").read_text(encoding="utf-8").splitlines()
              if l.strip() and not l.startswith("#")]
    inte = [d for d in corpus if (d.get("fecha") or "")[:10] == "2025-07-07"
            and d.get("de") == "persona.cuatro@engelvoelkers.com"]
    assert inte and inte[0]["confianza"] == "media-reconstruida"
    before = capa_a_hashes()
    reg1 = json.loads((out / "_registro.json").read_text(encoding="utf-8"))
    P.atomize_dir(src, out, case_dir=tmp_path)            # 2ª corrida
    after = capa_a_hashes()
    reg2 = json.loads((out / "_registro.json").read_text(encoding="utf-8"))
    assert before == after, "Capa A byte-idéntica entre corridas (el interior no la toca)"
    assert reg1["mensajes_fp"] == reg2["mensajes_fp"], "fp estables: re-ejecutar no renumera"
