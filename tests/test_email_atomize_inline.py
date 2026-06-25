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


def test_anclaje_apellido_coma_nombre_extrae_addr():
    # Display-name "Apellido, Nombre" rompía parseaddr por la coma → de="". Debe extraer el <addr>.
    blk = ("De: PersonaCuatro, Eva <persona.cuatro@engelvoelkers.com>\n"
           "Enviado: 7 de julio de 2025\nPara: x@y\nAsunto: Re: offer letter")
    anc = I.parsear_anclaje(blk, "outlook_es")
    assert anc.de == "persona.cuatro@engelvoelkers.com"
    assert "PersonaCuatro, Eva" in anc.de_nombre and anc.fecha_iso == "2025-07-07"


def test_anclaje_sin_coma_sigue_igual():
    blk = "De: Eva <eva@x.com>\nEnviado: 7 de julio de 2025\nPara: w\nAsunto: z"
    anc = I.parsear_anclaje(blk, "outlook_es")
    assert anc.de == "eva@x.com" and anc.de_nombre == "Eva"


def test_anclaje_addr_desnuda_sigue_igual():
    blk = "De: eva@x.com\nEnviado: 7 de julio de 2025\nPara: w\nAsunto: z"
    anc = I.parsear_anclaje(blk, "outlook_es")
    assert anc.de == "eva@x.com"


def test_anclaje_sin_fecha_parseable():
    anc = I.parsear_anclaje("De: x@y.com\nAsunto: z\nPara: w", "outlook_es")
    assert anc.de == "x@y.com" and anc.fecha_iso == "0000-00-00"


def test_anclaje_outlook_enviado_el_parsea_fecha():
    # Outlook ES real usa "Enviado el:" (no "Enviado:") — debe parsear la fecha igual.
    blk = ("De: PersonaTres <per03@example.invalid>\nEnviado el: viernes, 4 de octubre de 2024 11:40\n"
           "Para: x@y\nAsunto: RV: Tibidabo")
    anc = I.parsear_anclaje(blk, "outlook_es")
    assert anc.de == "per03@example.invalid" and anc.fecha_iso == "2024-10-04" and "Tibidabo" in anc.asunto


def test_anclaje_enviat_el_catalan_parsea_fecha():
    blk = "De: Toni <per03@example.invalid>\nEnviat el: 3 de febrer de 2020\nPara: y@z\nAsunto: x"
    anc = I.parsear_anclaje(blk, "outlook_es")
    assert anc.de == "per03@example.invalid" and anc.fecha_iso == "2020-02-03"


def test_anclaje_enviado_sin_el_sigue_parseando():
    # Regresión: el caso sin " el" sigue funcionando idéntico.
    blk = "De: X <x@y.com>\nEnviado: lunes, 3 de febrero de 2020 18:42\nPara: w\nAsunto: z"
    anc = I.parsear_anclaje(blk, "outlook_es")
    assert anc.de == "x@y.com" and anc.fecha_iso == "2020-02-03"


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


def test_seg_anclaje_no_se_trunca_con_enviado_el():
    # El bloque "Enviado el:" NO debe cortar la acumulación del anclaje: Enviado/Para/Asunto
    # deben quedar dentro del anclaje del segmento (regresión de la cascada).
    txt = ("Mi nota.\n-----Mensaje original-----\nDe: Antoni <per03@example.invalid>\n"
           "Enviado el: viernes, 4 de octubre de 2024 11:40\nPara: x@y\nAsunto: Z\ncuerpo citado")
    s = I.segmentar_texto(txt)
    assert len(s.ancestros) == 1 and s.ancestros[0].estilo == "fwd_line"
    anc = I.parsear_anclaje(s.ancestros[0].anclaje_texto or "", s.ancestros[0].estilo)
    assert anc.de == "per03@example.invalid" and anc.fecha_iso == "2024-10-04" and "Z" in anc.asunto


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
    # No estructural pero completo y no ambiguo → ahora PROMUEVE a media-reconstruida (nuevo peldaño).
    assert I.clasificar(anc, "2020-02-01", estructural=False, ambigua=False)[0] == "media-reconstruida"
    # Ambigua (varias cabeceras apiladas levantadas del cuerpo) → sigue topada a media (no promueve).
    assert I.clasificar(anc, "2020-02-01", estructural=True, ambigua=True)[0] == "media"


def test_clasifica_email_invalido_no_promueve():
    anc = I.Anclaje(de="no-es-email", fecha_iso="2020-01-01")
    assert I.clasificar(anc, "2020-02-01", estructural=True, ambigua=False)[0] in ("media", "baja")


def test_clasifica_media_reconstruida_no_estructural_con_email_y_fecha():
    # No estructural pero con remitente válido + fecha coherente + no ambigua + no discrepancia
    # → PROMUEVE a media-reconstruida (nuevo peldaño).
    anc = I.Anclaje(de="a@x.com", fecha_iso="2020-01-01")
    conf, motivo = I.clasificar(anc, "2020-02-01", estructural=False, ambigua=False)
    assert conf == "media-reconstruida" and motivo == "no_estructural"


def test_clasifica_media_reconstruida_solo_nombre_no_promueve():
    # Display name sin <addr> → email inválido → NO promueve (queda en media/baja).
    anc = I.Anclaje(de="", de_nombre="PersonaUno", fecha_iso="2020-01-01")
    conf, _ = I.clasificar(anc, "2020-02-01", estructural=False, ambigua=False)
    assert conf in ("media", "baja") and conf != "media-reconstruida"


def test_clasifica_media_reconstruida_sin_fecha_no_promueve():
    # Email válido pero sin fecha coherente → NO promueve.
    anc = I.Anclaje(de="a@x.com", fecha_iso="0000-00-00")
    conf, _ = I.clasificar(anc, "2020-02-01", estructural=False, ambigua=False)
    assert conf in ("media", "baja") and conf != "media-reconstruida"


def test_clasifica_estructural_completo_sigue_alta_reconstruida():
    # Regresión del peldaño alto: estructural + email + fecha → alta-reconstruida (sin cambio).
    anc = I.Anclaje(de="a@x.com", fecha_iso="2020-01-01")
    conf, _ = I.clasificar(anc, "2020-02-01", estructural=True, ambigua=False)
    assert conf == "alta-reconstruida"


def test_clasifica_no_estructural_pero_ambigua_no_promueve():
    # estructural=False + ambigua=True (varias cabeceras apiladas) → media, NUNCA media-reconstruida.
    anc = I.Anclaje(de="a@x.com", fecha_iso="2020-01-01")
    conf, _ = I.clasificar(anc, "2020-02-01", estructural=False, ambigua=True)
    assert conf == "media" and conf != "media-reconstruida"


# ---------------------------------------------------------------------------
# T9 — orquestador reconstruir + indice Capa A + watched-list
# ---------------------------------------------------------------------------
from email.message import EmailMessage
from core.email_atomize.model import RegistroMensaje


def _ra(**kw):
    base = dict(msg_id="MSG-00042", rfc_message_id="p@x", fecha_iso="2026-06-01",
                asunto="Asunto", de="c@x", cuerpo="autor", capa="A", confianza="alta")
    base.update(kw)
    return RegistroMensaje(**base)


def _eml_cita_gmail(autor, de_cita, fecha_attr, cuerpo_cita):
    m = EmailMessage()
    m["Message-ID"] = "<carrier@x>"; m["Subject"] = "RV"; m["From"] = "c@x"; m["To"] = "d@x"
    m["Date"] = "Mon, 01 Jun 2026 10:00:00 +0200"
    m.set_content(autor)
    html = (f'<div>{autor}</div><div class="gmail_quote">'
            f'<div class="gmail_attr">El {fecha_attr}, Jaime &lt;{de_cita}&gt; escribió:</div>'
            f'<blockquote>{cuerpo_cita}</blockquote></div>')
    m.add_alternative(html, subtype="html")
    return m.as_bytes()


def test_reconstruir_promueve_del_burgo_inline():
    # Ruta genérica (sin identidades inyectadas): PersonaUno no está vigilado ni es candidato,
    # por lo que una cita estructural con fecha+email válidos SÍ promociona a alta-reconstruida.
    raw = _eml_cita_gmail("Te reenvío.", "per01a@example.invalid", "1 de mayo de 2020",
                          "contenido suficientemente largo para fingerprint y promocion")
    res = I.reconstruir(_ra(fecha_iso="2026-06-01"), raw)
    altas = [s for s in res.candidatos if s.confianza == "alta-reconstruida"]
    assert any(s.de == "per01a@example.invalid" for s in altas)


def test_reconstruir_watched_va_a_del_burgo_queue():
    from core.email_atomize.identidades import Identidades
    ident = Identidades(vigiladas=frozenset({"per01a@example.invalid"}))
    raw = _eml_cita_gmail("x", "per01a@example.invalid", "1 de mayo de 2020",
                          "cuerpo largo de prueba suficiente para todo")
    res = I.reconstruir(_ra(), raw, ident)
    db = [s for s in res.candidatos if s.de == "per01a@example.invalid"]
    assert db and db[0].en_revision is True   # doble control sobre identidad vigilada


def test_indice_layer_a_resuelve_por_cuerpo_sha():
    m = _ra(cuerpo="cuerpo identico bastante largo para superar el floor", de="z@x",
            fecha_iso="2020-05-01", asunto="t")
    idx = I.indice_layer_a([m])
    assert idx.por_cuerpo_sha(I.normaliza_cuerpo(m.cuerpo)) == "MSG-00042"


def _eml_carrier_plano(de_cita, fecha_label, asunto_cita, cuerpo_cita):
    # .eml de TEXTO PLANO con bloque outlook_es (De:/Enviado:/Para:/Asunto:) NO estructural.
    m = EmailMessage()
    m["Message-ID"] = "<carrier-plano@x>"; m["Subject"] = "RV"; m["From"] = "c@x"; m["To"] = "d@x"
    m["Date"] = "Mon, 01 Jun 2026 10:00:00 +0200"
    cuerpo = (f"Te reenvio esto abajo.\n\n"
              f"De: Jaime <{de_cita}>\nEnviado: {fecha_label}\nPara: x@y\nAsunto: {asunto_cita}\n"
              f"{cuerpo_cita}\n")
    m.set_content(cuerpo)
    return m.as_bytes()


def test_reconstruir_media_reconstruida_va_a_candidatos_y_en_revision():
    raw = _eml_carrier_plano("alguien@x.com", "1 de mayo de 2020", "Tibidabo",
                             "contenido citado suficientemente largo para superar el floor de 24")
    res = I.reconstruir(_ra(fecha_iso="2026-06-01"), raw)
    medias = [s for s in res.candidatos if s.confianza == "media-reconstruida"]
    assert medias, "media-reconstruida debe enrutarse a candidatos, no a punteros"
    assert medias[0].de == "alguien@x.com"
    assert medias[0].en_revision is True   # los media-reconstruida SIEMPRE entran en revisión
    # No queda como puntero de cola:
    assert not any(getattr(p, "confianza", "") == "media-reconstruida" for p in res.punteros)


def test_reconstruir_dos_cabeceras_apiladas_no_promueve():
    # Spec §8 test 6: dos bloques De:/Enviado: apilados levantados del cuerpo → ambigua=True
    # → NO va a candidatos (queda en punteros/cola), NO se fabrica remitente.
    m = EmailMessage()
    m["Message-ID"] = "<carrier-apilado@x>"; m["Subject"] = "RV"; m["From"] = "c@x"; m["To"] = "d@x"
    m["Date"] = "Mon, 01 Jun 2026 10:00:00 +0200"
    cuerpo = ("Reenvio esto:\n\n"
              "De: Uno <uno@x.com>\nEnviado: 1 de mayo de 2020\nPara: x@y\nAsunto: A\n"
              "De: Dos <dos@x.com>\nEnviado: 2 de mayo de 2020\nPara: x@y\nAsunto: B\n"
              "cuerpo citado suficientemente largo para superar el floor de 24 chars\n")
    m.set_content(cuerpo)
    res = I.reconstruir(_ra(fecha_iso="2026-06-01"), m.as_bytes())
    assert not any(getattr(s, "confianza", "") == "media-reconstruida" for s in res.candidatos)
