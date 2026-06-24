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
