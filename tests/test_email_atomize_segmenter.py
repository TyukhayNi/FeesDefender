from __future__ import annotations
from core.email_atomize import _segmenter as S
from core.email_atomize import bodies as B
from email.message import EmailMessage


def test_cortar_autor_top_posting_devuelve_resto():
    txt = ("Mi respuesta breve.\n\n"
           "El 11 jun 2026, a las 9:00, Jaime <j@x> escribió:\n"
           "> cita larga\n> mas cita\n")
    autor, resto, inter = S.cortar_autor(txt)
    assert autor == "Mi respuesta breve."
    assert resto is not None and "cita larga" in resto
    assert inter is False


def test_cortar_autor_intercalada_no_corta():
    txt = "> p1\nresp autor 1\n> p2\nresp autor 2\n"
    autor, resto, inter = S.cortar_autor(txt)
    assert inter is True
    assert resto is None
    assert "resp autor 1" in autor and "p2" in autor


def test_cortar_autor_sin_cita():
    autor, resto, inter = S.cortar_autor("Solo texto del autor.")
    assert autor == "Solo texto del autor." and resto is None and inter is False


def test_bodies_default_byte_identico():
    m = EmailMessage()
    m["Message-ID"] = "<a@x>"; m["Subject"] = "X"; m["From"] = "a@x"; m["To"] = "b@x"
    m.set_content("Respuesta.\n\nEl 1 ene 2020, a las 8:00, Y <y@x> escribió:\n> cita\n")
    c = B.extraer_cuerpo(m.as_bytes())
    assert c.texto == "Respuesta."
    assert c.cuerpo_recortado_cita is True


def test_bodies_conservar_resto_expone_base_y_split():
    m = EmailMessage()
    m["Message-ID"] = "<a@x>"; m["Subject"] = "X"; m["From"] = "a@x"; m["To"] = "b@x"
    m.set_content("Respuesta.\n\nEl 1 ene 2020, a las 8:00, Y <y@x> escribió:\n> cita\n")
    c = B.extraer_cuerpo(m.as_bytes(), conservar_resto=True)
    assert c.texto == "Respuesta."
    assert c.base_sin_recortar is not None and "cita" in c.base_sin_recortar
    assert c.resto_citado is not None and "cita" in c.resto_citado
