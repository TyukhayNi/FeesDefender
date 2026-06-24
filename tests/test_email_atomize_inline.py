from __future__ import annotations
from core.email_atomize import inline as I


# ---------------------------------------------------------------------------
# T4 — normalizador + fingerprint
# ---------------------------------------------------------------------------

def test_normaliza_quita_marcas_firma_acentos():
    a = I.normaliza_cuerpo("> Hola  ESTÁ\n> aquí\n-- \nfirma irrelevante")
    b = I.normaliza_cuerpo("hola esta aqui")
    assert a == b


def test_fingerprint_reproducible_y_prefijo():
    anc = I.Anclaje(de="x@y.com", fecha_iso="2020-01-02", asunto="RE: Hola")
    fp1 = I.fingerprint_b(anc, I.normaliza_cuerpo("cuerpo suficientemente largo aqui"))
    fp2 = I.fingerprint_b(anc, I.normaliza_cuerpo("cuerpo suficientemente largo aqui"))
    assert fp1 == fp2 and fp1.startswith("fp:") and len(fp1) == 3 + 24


def test_fingerprint_dia_granular_absorbe_tz():
    cuerpo = I.normaliza_cuerpo("texto identico de cuerpo bastante largo")
    a1 = I.Anclaje(de="x@y.com", fecha_iso="2020-01-02", asunto="Hola")
    a2 = I.Anclaje(de="x@y.com", fecha_iso="2020-01-02", asunto="Hola")
    assert I.fingerprint_b(a1, cuerpo) == I.fingerprint_b(a2, cuerpo)


def test_fingerprint_floor_no_colapsa_cuerpos_cortos():
    assert I.es_cuerpo_colapsable(I.normaliza_cuerpo("ok")) is False
    assert I.es_cuerpo_colapsable(I.normaliza_cuerpo("a" * 30)) is True


# ---------------------------------------------------------------------------
# T5 — parseo de anclaje (sender/date, ES+CA)
# ---------------------------------------------------------------------------

def test_anclaje_outlook_bilingue():
    blk = ("De: PersonaUno <per01a@example.invalid>\nEnviado: lunes, 3 de febrero de 2020 18:42\n"
           "Para: x@y\nAsunto: RE: Tibidabo")
    anc = I.parsear_anclaje(blk, "outlook_es")
    assert anc.de == "per01a@example.invalid" and anc.fecha_iso == "2020-02-03" and "Tibidabo" in anc.asunto


def test_anclaje_apple_addr_y_fecha():
    blk = "El 3 feb 2020, a las 18:42, Jaime <per01c@example.invalid> escribió:"
    anc = I.parsear_anclaje(blk, "apple_es")
    assert anc.de == "per01c@example.invalid" and anc.fecha_iso == "2020-02-03"


def test_anclaje_catalan_date():
    blk = "El 12 de març de 2021, a les 9:00, Toni <per03@example.invalid> va escriure:"
    anc = I.parsear_anclaje(blk, "apple_es")
    assert anc.de == "per03@example.invalid" and anc.fecha_iso == "2021-03-12"


def test_anclaje_display_name_sin_addr_no_inventa():
    anc = I.parsear_anclaje("De: PersonaUno\nEnviado: 3 feb 2020\nAsunto: x", "outlook_es")
    assert anc.de == "" and "Jaime" in anc.de_nombre  # nombre sí, dirección NO inventada


def test_anclaje_sin_fecha_parseable():
    anc = I.parsear_anclaje("De: x@y.com\nAsunto: z\nPara: w", "outlook_es")
    assert anc.de == "x@y.com" and anc.fecha_iso == "0000-00-00"


# ---------------------------------------------------------------------------
# T6 — segmentación texto plano
# ---------------------------------------------------------------------------

def test_seg_plain_un_outlook():
    s = I.segmentar_texto("Mi nota.\nDe: Y <y@z.com>\nEnviado: 1 ene 2020\nAsunto: Z\nPara: w\n> cuerpo citado")
    assert s.autor.startswith("Mi nota")
    assert len(s.ancestros) == 1 and s.ancestros[0].estilo == "outlook_es"


def test_seg_plain_multimarcador_orden_documental():
    txt = ("Top.\n"
           "El 2 feb 2020, a las 9:00, A <a@x> escribió:\n"
           "> uno\n"
           "-----Mensaje original-----\nDe: B <b@x>\nAsunto: q\nEnviado: 1 feb 2020\n")
    s = I.segmentar_texto(txt)
    assert [a.estilo for a in s.ancestros] == ["apple_es", "fwd_line"]


def test_seg_plain_quote_gt_depth():
    s = I.segmentar_texto("Hola\n> n1\n>> n2\n>> n2b\n> n1b")
    profs = sorted({a.profundidad for a in s.ancestros})
    assert profs and max(profs) >= 2 and all(a.estructural for a in s.ancestros)


def test_seg_stray_de_no_segmenta():
    s = I.segmentar_texto("Te escribo. De: acuerdo con lo que dices sobre el asunto.")
    assert s.ancestros == []


def test_seg_plain_intercalada_no_segmenta():
    s = I.segmentar_texto("> pregunta uno\nrespuesta del autor entre citas\n> pregunta dos\n")
    assert s.respuesta_intercalada is True and s.ancestros == []


# ---------------------------------------------------------------------------
# T7 — segmentación HTML + intercalada HTML + conservación de tokens
# ---------------------------------------------------------------------------

def test_seg_html_gmail_quote():
    html = ('<div>Mi respuesta</div>'
            '<div class="gmail_quote"><div class="gmail_attr">El 2 feb 2020, A &lt;a@x&gt; escribió:</div>'
            '<blockquote>cuerpo citado</blockquote></div>')
    s = I.segmentar_html(html)
    assert "Mi respuesta" in s.autor
    assert len(s.ancestros) == 1 and "a@x" in (s.ancestros[0].anclaje_texto or "")
    assert s.ancestros[0].estructural is True


def test_seg_html_anidado_profundidad():
    html = '<div>top</div><blockquote>n1<blockquote>n2<blockquote>n3</blockquote></blockquote></blockquote>'
    s = I.segmentar_html(html)
    assert max(a.profundidad for a in s.ancestros) >= 3


def test_seg_html_intercalada_no_segmenta():
    html = ('<div>resp 1</div><blockquote>p1</blockquote>'
            '<div>resp 2 del autor entre citas</div><blockquote>p2</blockquote>')
    s = I.segmentar_html(html)
    assert s.respuesta_intercalada is True and s.ancestros == []


def test_seg_html_token_conservacion_no_inventa():
    s = I.segmentar_html("<blockquote>" + "x " * 5 + "</blockquote>")
    assert isinstance(s.respuesta_intercalada, bool)


# ---------------------------------------------------------------------------
# T8 — clasificación de confianza + guardas anti-misatribución
# ---------------------------------------------------------------------------

def test_clasifica_alta_reconstruida_requiere_todo():
    anc = I.Anclaje(de="a@x.com", fecha_iso="2020-01-01")
    conf, motivo = I.clasificar(anc, "2020-02-01", estructural=True, ambigua=False)
    assert conf == "alta-reconstruida"


def test_clasifica_fecha_posterior_al_portador_no_alta():
    anc = I.Anclaje(de="a@x.com", fecha_iso="2020-03-01")
    conf, motivo = I.clasificar(anc, "2020-02-01", estructural=True, ambigua=False)
    assert conf == "media" and "fecha_incoherente" in motivo


def test_clasifica_headerless_es_baja_sin_remitente():
    conf, motivo = I.clasificar(None, "2020-02-01", estructural=False, ambigua=False)
    assert conf == "baja"


def test_clasifica_sin_estructura_o_ambigua_demota_a_media():
    anc = I.Anclaje(de="a@x.com", fecha_iso="2020-01-01")
    assert I.clasificar(anc, "2020-02-01", estructural=False, ambigua=False)[0] == "media"
    assert I.clasificar(anc, "2020-02-01", estructural=True, ambigua=True)[0] == "media"


def test_clasifica_email_invalido_no_promueve():
    anc = I.Anclaje(de="no-es-email", fecha_iso="2020-01-01")
    assert I.clasificar(anc, "2020-02-01", estructural=True, ambigua=False)[0] in ("media", "baja")
