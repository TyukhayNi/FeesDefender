from __future__ import annotations
from email.message import EmailMessage
from core.email_atomize import bodies as B


def _con_partes(plain: str | None, html: str | None) -> bytes:
    m = EmailMessage()
    m["Message-ID"] = "<a@x>"
    m["Subject"] = "X"
    m["From"] = "a@x"
    m["To"] = "b@x"
    if plain is not None:
        m.set_content(plain)
    if html is not None:
        if plain is None:
            m.set_content("x")  # base
        m.add_alternative(html, subtype="html")
    return m.as_bytes()


def test_prefiere_text_plain():
    raw = _con_partes("texto plano del autor", "<p>HTML que ignoramos</p>")
    cuerpo = B.extraer_cuerpo(raw)
    assert "texto plano del autor" in cuerpo.texto
    assert "HTML" not in cuerpo.texto
    assert cuerpo.formato_original == "plain"


def test_html_solo_se_convierte_a_texto():
    raw = _con_partes(None, "<p>Hola <b>mundo</b></p>")
    cuerpo = B.extraer_cuerpo(raw)
    assert "Hola" in cuerpo.texto and "mundo" in cuerpo.texto
    assert "<p>" not in cuerpo.texto


def test_recorta_cola_citada_top_posting():
    plano = (
        "Mi respuesta breve.\n\n"
        "El 11 jun 2026, a las 9:00, Jaime <j@x> escribió:\n"
        "> texto citado largo\n> mas cita\n"
    )
    raw = _con_partes(plano, None)
    cuerpo = B.extraer_cuerpo(raw)
    assert "Mi respuesta breve." in cuerpo.texto
    assert "texto citado largo" not in cuerpo.texto
    assert cuerpo.cuerpo_recortado_cita is True


def test_respuesta_intercalada_no_se_recorta():
    plano = (
        "> pregunta uno\n"
        "respuesta uno del autor\n"
        "> pregunta dos\n"
        "respuesta dos del autor\n"
    )
    raw = _con_partes(plano, None)
    cuerpo = B.extraer_cuerpo(raw)
    assert "respuesta uno del autor" in cuerpo.texto
    assert "pregunta dos" in cuerpo.texto  # se conserva íntegro
    assert cuerpo.respuesta_intercalada is True
