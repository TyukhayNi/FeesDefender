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
