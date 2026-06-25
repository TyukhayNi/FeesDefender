"""Regresiones de endurecimiento Layer B — hallazgos de la revisión adversarial.

Cada test fija una vía de MISATRIBUCIÓN (o pérdida de idempotencia) que la revisión confirmó.
"""
from __future__ import annotations
from email.message import EmailMessage
from core.email_atomize import inline as I
from core.email_atomize import pipeline as P
from core.email_atomize.model import RegistroMensaje


def _ra(**kw):
    base = dict(msg_id="MSG-00042", rfc_message_id="p@x", fecha_iso="2026-06-01",
                asunto="Asunto", de="c@x", cuerpo="autor", capa="A", confianza="alta")
    base.update(kw)
    return RegistroMensaje(**base)


def _eml_html(html, plain="base"):
    m = EmailMessage()
    m["Message-ID"] = "<carrier@x>"; m["Subject"] = "RV"; m["From"] = "c@x"; m["To"] = "d@x"
    m["Date"] = "Mon, 01 Jun 2026 10:00:00 +0200"
    m.set_content(plain)
    m.add_alternative(html, subtype="html")
    return m.as_bytes()


def _eml_gmail(de_cita, fecha_attr, cuerpo, autor="x"):
    html = (f'<div>{autor}</div><div class="gmail_quote"><div class="gmail_attr">'
            f'El {fecha_attr}, Jaime &lt;{de_cita}&gt; escribió:</div>'
            f'<blockquote>{cuerpo}</blockquote></div>')
    return _eml_html(html, plain=autor)


def _eml_simple(mid, subj):
    m = EmailMessage(); m["Message-ID"] = mid; m["Subject"] = subj
    m["Date"] = "Thu, 12 Jun 2026 10:00:00 +0200"; m["From"] = "a@x"; m["To"] = "b@x"
    m.set_content("c"); return m.as_bytes()


# --- MISATRIBUCIÓN (prime directive) ---

def test_stacked_forwards_no_promueve_alta():
    """Un blockquote con VARIAS cabeceras From: apiladas → ambiguo → media, nunca alta."""
    html = ("<blockquote>From: a@x.com\nSent: 3 de febrero de 2020\nSubject: X\nbody A\n"
            "From: b@y.com\nSent: 1 de febrero de 2020\nSubject: Y\nbody B</blockquote>")
    res = I.reconstruir(_ra(fecha_iso="2026-06-01"), _eml_html(html))
    assert all(s.confianza != "alta-reconstruida" for s in res.candidatos)


def test_blockquote_addr_suelta_sin_atribucion_no_atribuye():
    """Un <addr> suelto en una cita SIN estructura de atribución no fabrica remitente."""
    html = "<blockquote>Texto citado, escríbeme a contacto &lt;c@x.com&gt; cuando puedas</blockquote>"
    res = I.reconstruir(_ra(), _eml_html(html))
    assert all(s.de != "c@x.com" for s in res.candidatos)
    assert all(p.de != "c@x.com" for p in res.punteros)


def test_prosa_from_dispersa_no_promueve():
    """'From:'/'Date:' dispersos entre prosa (no bloque contiguo) no llegan a alta."""
    html = ("<blockquote>Hola, según lo hablado From: jefe@x.com te confirmo; "
            "Date: cuando quieras pasamos por ahí</blockquote>")
    res = I.reconstruir(_ra(), _eml_html(html))
    assert all(s.confianza != "alta-reconstruida" for s in res.candidatos)


def test_candidato_outlook_capped_media():
    """per01b@example.invalid (candidato) NUNCA llega a alta; va a revisión."""
    res = I.reconstruir(_ra(fecha_iso="2026-06-01"),
                        _eml_gmail("per01b@example.invalid", "1 de mayo de 2020",
                                   "cuerpo largo de prueba suficiente para fingerprint"))
    assert all(s.de != "per01b@example.invalid" for s in res.candidatos)
    assert any(p.de == "per01b@example.invalid" and "candidata" in p.motivo
               for p in res.punteros)


def test_fecha_numerica_ambigua_no_alta():
    """Fecha numérica ambigua (dd/mm ambos ≤12) no se trata como verificada → media."""
    res = I.reconstruir(_ra(fecha_iso="2026-06-01"),
                        _eml_gmail("a@x.com", "03/02/2020",
                                   "cuerpo largo de prueba suficiente para el test"))
    assert all(s.de != "a@x.com" for s in res.candidatos)


def test_gmail_legitimo_sigue_promoviendo():
    """No-regresión: una atribución gmail limpia con fecha ES SÍ promueve."""
    res = I.reconstruir(_ra(fecha_iso="2026-06-01"),
                        _eml_gmail("per01a@example.invalid", "1 de mayo de 2020",
                                   "contenido citado suficientemente largo para promocion"))
    assert any(s.de == "per01a@example.invalid" and s.confianza == "alta-reconstruida"
               for s in res.candidatos)


# --- IDEMPOTENCIA ---

def test_prune_orphan_md(tmp_path):
    """Un .md huérfano en mensajes/ (de una corrida previa) se elimina al re-correr."""
    src = tmp_path / "03_Email"; out = tmp_path / "Emails"; src.mkdir()
    (src / "a.eml").write_bytes(_eml_simple("<a@x>", "Uno"))
    P.atomize_dir(src, out)
    orphan = out / "mensajes" / "9999-99-99_huerfano_MSG-99999.md"
    orphan.write_text("x", encoding="utf-8")
    P.atomize_dir(src, out)
    assert not orphan.exists()
