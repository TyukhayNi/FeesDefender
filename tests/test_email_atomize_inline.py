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


# --- _parse_apple compartido: liga el remitente a la UNIDAD de atribución Apple.
#     Cierra la misatribución por <addr> extraviado en el path HTML/alta (parsear_anclaje). ---
def test_parse_apple_addr_extraviado_no_roba_remitente():
    # Stray <addr> ANTES de la atribución Apple → no debe ser el remitente.
    blk = ("Aviso legal. Contacto: dpo <dpo@bufete.com>.\n"
           "El 27 may 2024, a las 10:49, PersonaCinco <persona.cinco@engelvoelkers.com> escribió:")
    anc = I._parse_apple(blk)
    assert anc is not None and anc.de == "persona.cinco@engelvoelkers.com"


def test_parse_apple_dos_addr_en_unidad_es_ambiguo():
    # Remitente + destinatario en la propia atribución → ambiguo → sin remitente.
    blk = "El 4 oct 2024, Isabel <isabel@x.com> para Bob <bob@y.com> escribió:"
    anc = I._parse_apple(blk)
    assert anc is None or anc.de == ""


def test_parse_apple_limpio_sin_cambio():
    # Caso limpio (1 addr en la unidad) → de correcto (regresión: no romper los alta existentes).
    anc = I._parse_apple("El 1 de mayo de 2020, Jaime <per01a@example.invalid> escribió:")
    assert anc is not None and anc.de == "per01a@example.invalid"


def test_parse_apple_solo_nombre_sin_addr():
    anc = I._parse_apple("El 1 may 2020, PersonaUno escribió:")
    assert anc is None or anc.de == ""


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


# ---------------------------------------------------------------------------
# T10 — body-scan de remitente desde el CUERPO de la cita (it. 2)
#       Función pura _atribucion_en_cuerpo (spec §5 tests 1-10). Prime directive:
#       cero misatribución — un remitente solo se afirma desde un <addr> literal.
# ---------------------------------------------------------------------------

def test_bodyscan_a_apple_en_linea():
    # §5.1 — (a) Apple, <addr> en la misma línea.
    texto = ("El 27 may 2024, a las 10:49, PersonaCinco <persona.cinco@engelvoelkers.com> escribió:\n"
             "cuerpo citado suficientemente largo para superar el floor")
    anc = I._atribucion_en_cuerpo(texto)
    assert anc is not None
    assert anc.de == "persona.cinco@engelvoelkers.com" and anc.fecha_iso == "2024-05-27"


def test_bodyscan_b_addr_envuelto():
    # §5.2 — (b) <addr> envuelto en <\n...\n>; _RE_ADDR ya lo des-envuelve.
    texto = ("El 4 oct 2024, a las 11:48, PersonaCuatro, Eva <\n"
             "persona.cuatro@engelvoelkers.com\n"
             "> escribió:\n"
             "cuerpo citado suficientemente largo para superar el floor")
    anc = I._atribucion_en_cuerpo(texto)
    assert anc is not None
    assert anc.de == "persona.cuatro@engelvoelkers.com" and anc.fecha_iso == "2024-10-04"


def test_bodyscan_c_bloque_envuelto_con_intro():
    # §5.3 — (c) bloque De:/Fecha:/Para:/Asunto: con valores envueltos, tras intro de reenvío.
    # de = el del De: (envuelto), NUNCA el <addr> del Para:.
    texto = ("Inicio del mensaje reenviado:\n\n"
             "De:\n"
             "per03@example.invalid\n"
             "Fecha:\n"
             "27 de mayo de 2024, 10:38:07 CEST\n"
             'Para: "PersonaCinco, Isabel" <persona.cinco@engelvoelkers.com>\n'
             "Asunto: x")
    anc = I._atribucion_en_cuerpo(texto)
    assert anc is not None
    assert anc.de == "per03@example.invalid", "debe coger el De:, NUNCA el <addr> del Para:"
    assert anc.fecha_iso == "2024-05-27"


def test_bodyscan_g5_robo_destinatario_solo_nombre_de():
    # §5.4 — G5: De: solo-nombre (sin <addr>), Para: con <addr> → None (jamás roba el Para:).
    texto = ("Inicio del mensaje reenviado:\n\n"
             "De: PersonaCinco\n"
             "Fecha: 27 de mayo de 2024\n"
             "Para: Toni <per03@example.invalid>\n"
             "Asunto: x")
    anc = I._atribucion_en_cuerpo(texto)
    assert anc is None, "De: sin <addr> propio + Para: con <addr> → cola, NUNCA el addr del Para"


def test_bodyscan_g3_apilamiento_envuelto():
    # §5.5 — G3 (fix fallo latente veredicto 1): dos bloques De:\nvalor envueltos apilados → None.
    # _RE_DE_LABEL_ANY debe VER los De: aunque el valor vaya envuelto en la línea siguiente.
    texto = ("De:\n"
             "uno@x.com\n"
             "Fecha:\n"
             "1 de mayo de 2024\n"
             "De:\n"
             "dos@x.com\n"
             "Fecha:\n"
             "2 de mayo de 2024\n"
             "cuerpo")
    anc = I._atribucion_en_cuerpo(texto)
    assert anc is None, "dos De: envueltos apilados → AMBIGUO → cola"


def test_bodyscan_g3_conteo_apple_correcto():
    # §5.6 — fix bug conteo D1: UNA forma (a) bien formada NO se descarta (recupera);
    # DOS atribuciones Apple apiladas → None.
    una = ("El 27 may 2024, a las 10:49, Isabel <persona.cinco@engelvoelkers.com> escribió:\n"
           "cuerpo citado suficientemente largo")
    anc1 = I._atribucion_en_cuerpo(una)
    assert anc1 is not None and anc1.de == "persona.cinco@engelvoelkers.com", \
        "UNA forma (a) bien formada debe recuperar, no caer por conteo"
    dos = ("El 27 may 2024, a las 10:49, Isabel <persona.cinco@engelvoelkers.com> escribió:\n"
           "El 28 may 2024, a las 11:00, Toni <per03@example.invalid> escribió:\n"
           "cuerpo")
    anc2 = I._atribucion_en_cuerpo(dos)
    assert anc2 is None, "dos atribuciones Apple apiladas → AMBIGUO → cola"


def test_bodyscan_g4_dos_addr_en_linea_apple():
    # §5.7 — G4 (ADVERSARIAL 2): remitente + destinatario en la MISMA línea Apple → None.
    texto = ("El 27 may 2024, a las 10:49, Isabel <persona.cinco@engelvoelkers.com> a Toni "
             "<per03@example.invalid> escribió:\n"
             "cuerpo")
    anc = I._atribucion_en_cuerpo(texto)
    assert anc is None, "dos <addr> en la línea de atribución Apple → cola (no se puede ligar el de)"


def test_bodyscan_g2_ventana_atribucion_tardia():
    # §5.8 — G2: atribución válida más allá de la ventana del inicio (precedida de prosa larga) → None.
    prosa = "\n".join(f"linea de prosa numero {i} sin atribucion" for i in range(20))
    texto = (prosa + "\n"
             "El 27 may 2024, a las 10:49, Isabel <persona.cinco@engelvoelkers.com> escribió:\n"
             "cuerpo")
    anc = I._atribucion_en_cuerpo(texto)
    assert anc is None, "atribución fuera de la ventana del inicio → cola (no se escanea el cuerpo entero)"


def test_bodyscan_g1_los_48_sin_addr():
    # §5.9 — G1: bloque con De: solo-nombre, sin <addr> en NINGUNA etiqueta → None (los 48).
    texto = ("De: PersonaCinco\n"
             "Fecha: 27 de mayo de 2024\n"
             "Para: Toni Angeri\n"
             "Asunto: x\n"
             "cuerpo")
    anc = I._atribucion_en_cuerpo(texto)
    assert anc is None, "sin <addr> literal en ninguna etiqueta → cola (prime directive)"


def test_bodyscan_sin_estructura_prosa_suelta():
    # §5.10 — email suelto en prosa, sin El…/escribió: ni De: → None (aunque haya un <addr>).
    texto = ("Hola, te paso mi correo <persona.cinco@engelvoelkers.com> por si lo necesitas.\n"
             "Un saludo y hablamos pronto.")
    anc = I._atribucion_en_cuerpo(texto)
    assert anc is None, "prosa suelta sin estructura de atribución → cola"


def test_bodyscan_g4_addr_extraviado_antes_de_atribucion_apple():
    # Un <addr> suelto (pie/aviso legal) ANTES de una atribución Apple terminal NO debe robar el remitente.
    txt = ("Aviso legal. Contacto: dpo <dpo@bufete.com>\n"
           "El 27 may 2024, a las 10:49, PersonaCinco <persona.cinco@engelvoelkers.com> escribió:")
    anc = I._atribucion_en_cuerpo(txt)
    assert anc is not None and anc.de == "persona.cinco@engelvoelkers.com"


def test_bodyscan_g4_addr_extraviado_con_addr_envuelto():
    # Igual pero con el <addr> del remitente envuelto (forma b): debe seguir recuperando al remitente real.
    txt = ("> firma vieja: soporte <soporte@otra.com>\n"
           "El 4 oct 2024, a las 11:48, PersonaCuatro, Eva <\npersona.cuatro@engelvoelkers.com\n> escribió:")
    anc = I._atribucion_en_cuerpo(txt)
    assert anc is not None and anc.de == "persona.cuatro@engelvoelkers.com"


def test_bodyscan_g4_dos_addr_en_la_unidad_apple_es_ambiguo():
    # Dos <addr> DENTRO de la unidad de atribución (remitente+cc) → ambiguo → None.
    txt = "El 4 oct 2024, Eva <eva@x.com> con copia a Bob <bob@y.com> escribió:"
    assert I._atribucion_en_cuerpo(txt) is None


# ---------------------------------------------------------------------------
# T10 (integración) — enganche del body-scan en reconstruir (spec §5 tests 11-14)
# ---------------------------------------------------------------------------

def _eml_html_apple_en_cuerpo(autor, attr_line, cuerpo_cita):
    """Portador HTML: anclaje previo es PROSA; la atribución Apple es la 1ª línea del blockquote."""
    m = EmailMessage()
    m["Message-ID"] = "<carrier-apple-body@x>"; m["Subject"] = "RV"
    m["From"] = "c@x"; m["To"] = "d@x"
    m["Date"] = "Mon, 01 Jun 2026 10:00:00 +0200"
    m.set_content(autor)
    html = (f'<div>{autor}</div>'
            f'<blockquote>{attr_line}<br>{cuerpo_cita}</blockquote>')
    m.add_alternative(html, subtype="html")
    return m.as_bytes()


def test_reconstruir_bodyscan_apple_en_blockquote_topa_media():
    # §5.11 — (a) Apple DENTRO del blockquote, anclaje previo es prosa → media-reconstruida
    # (atribucion_cuerpo), NO sube a alta pese a ser estructural. Verifica el graft de confianza.
    attr = "El 27 may 2024, a las 10:49, Isabel &lt;persona.cinco@engelvoelkers.com&gt; escribió:"
    raw = _eml_html_apple_en_cuerpo(
        "Te reenvío esto.", attr,
        "contenido citado suficientemente largo para superar el floor de 24 chars")
    res = I.reconstruir(_ra(fecha_iso="2026-06-01"), raw)
    rec = [s for s in res.candidatos if s.de == "persona.cinco@engelvoelkers.com"]
    assert rec, "el body-scan debe recuperar el de Apple del interior del blockquote"
    assert rec[0].confianza == "media-reconstruida", "NO sube a alta pese a ser estructural"
    assert rec[0].motivo == "atribucion_cuerpo"
    assert rec[0].en_revision is True


def test_reconstruir_bodyscan_trigger_por_disyuncion_solo_fecha():
    # §5.12 — anclaje estructural que parseó SOLO fecha (de="", anc is not None) + <addr> en el
    # cuerpo → body-scan dispara y recupera el de (recall hole de un trigger 'anc is None' solo).
    m = EmailMessage()
    m["Message-ID"] = "<carrier-disy@x>"; m["Subject"] = "RV"
    m["From"] = "c@x"; m["To"] = "d@x"
    m["Date"] = "Mon, 01 Jun 2026 10:00:00 +0200"
    m.set_content("Te reenvío.")
    # gmail_attr con SOLO fecha (sin <addr>): anc is not None pero de="". El <addr> real va dentro.
    html = ('<div>Te reenvío.</div><div class="gmail_quote">'
            '<div class="gmail_attr">El 27 may 2024 escribió:</div>'
            '<blockquote>El 27 may 2024, a las 10:49, Isabel '
            '&lt;persona.cinco@engelvoelkers.com&gt; escribió:<br>'
            'contenido citado suficientemente largo para superar el floor</blockquote></div>')
    m.add_alternative(html, subtype="html")
    res = I.reconstruir(_ra(fecha_iso="2026-06-01"), m.as_bytes())
    rec = [s for s in res.candidatos if s.de == "persona.cinco@engelvoelkers.com"]
    assert rec, "trigger por disyunción (anc con solo fecha) debe disparar el body-scan"


def test_reconstruir_prioridad_anchor_gmail_attr_con_de_gana():
    # §5.13 — gmail_attr con de válido + atribución en el cuerpo → gana el anchor, body-scan NO se
    # invoca → la cita estructural sube a alta-reconstruida con el de del anchor (no el del cuerpo).
    m = EmailMessage()
    m["Message-ID"] = "<carrier-prio@x>"; m["Subject"] = "RV"
    m["From"] = "c@x"; m["To"] = "d@x"
    m["Date"] = "Mon, 01 Jun 2026 10:00:00 +0200"
    m.set_content("Te reenvío.")
    html = ('<div>Te reenvío.</div><div class="gmail_quote">'
            '<div class="gmail_attr">El 1 may 2020, Jaime &lt;per01a@example.invalid&gt; escribió:</div>'
            '<blockquote>El 27 may 2024, a las 10:49, Otro '
            '&lt;otro@x.com&gt; escribió:<br>'
            'contenido citado suficientemente largo para superar el floor</blockquote></div>')
    m.add_alternative(html, subtype="html")
    res = I.reconstruir(_ra(fecha_iso="2026-06-01"), m.as_bytes())
    altas = [s for s in res.candidatos if s.confianza == "alta-reconstruida"]
    assert any(s.de == "per01a@example.invalid" for s in altas), "gana el anchor gmail_attr (alta)"
    assert not any(s.de == "otro@x.com" for s in res.candidatos), "el de del cuerpo NO se usa"


def test_reconstruir_bodyscan_g3_dos_cabeceras_envueltas_no_promueve():
    # §5.14 — dos cabeceras De: envueltas apiladas en el cuerpo → no promueve (punteros).
    m = EmailMessage()
    m["Message-ID"] = "<carrier-g3body@x>"; m["Subject"] = "RV"
    m["From"] = "c@x"; m["To"] = "d@x"
    m["Date"] = "Mon, 01 Jun 2026 10:00:00 +0200"
    m.set_content("Te reenvío.")
    html = ('<div>Te reenvío.</div>'
            '<blockquote>De:<br>uno@x.com<br>Fecha:<br>1 de mayo de 2024<br>'
            'De:<br>dos@x.com<br>Fecha:<br>2 de mayo de 2024<br>'
            'cuerpo citado suficientemente largo para superar el floor</blockquote>')
    m.add_alternative(html, subtype="html")
    res = I.reconstruir(_ra(fecha_iso="2026-06-01"), m.as_bytes())
    assert not any(getattr(s, "confianza", "") in ("media-reconstruida", "alta-reconstruida")
                   and getattr(s, "de", "") in ("uno@x.com", "dos@x.com")
                   for s in res.candidatos), "dos cabeceras envueltas apiladas → cola, no promueve"


def test_reconstruir_html_anchor_addr_extraviado_no_misatribuye():
    # Path HTML dominante (gmail_attr → parsear_anclaje → _parse_apple): un <addr> extraviado
    # (pie/aviso legal) ANTES de la atribución Apple NO debe robar el remitente, ni siquiera en alta.
    m = EmailMessage(); m["Message-ID"] = "<c@x>"; m["Subject"] = "RV"; m["From"] = "c@x"; m["To"] = "d@x"
    m["Date"] = "Mon, 01 Jun 2026 10:00:00 +0200"; m.set_content("autor")
    html = ('<div>Te respondo.</div><div class="gmail_quote">'
            '<div class="gmail_attr">Aviso legal. Contacto: dpo &lt;dpo@bufete.com&gt;. '
            'El 27 may 2024, a las 10:49, PersonaCinco &lt;persona.cinco@engelvoelkers.com&gt; escribió:</div>'
            '<blockquote>Cuerpo original con sustancia suficiente para colapsar el segmento.</blockquote></div>')
    m.add_alternative(html, subtype="html")
    res = I.reconstruir(_ra(fecha_iso="2026-06-01"), m.as_bytes())
    malos = [s for s in res.candidatos if s.de == "dpo@bufete.com"]
    assert not malos, "no debe atribuir el <addr> extraviado del pie como remitente"
