from __future__ import annotations
from core.email_atomize.model import RegistroMensaje, AdjuntoRef
from core.email_atomize import render as R


def _msg(**kw) -> RegistroMensaje:
    base = dict(
        msg_id="MSG-00001", rfc_message_id="a@x", in_reply_to="", hilo="a@x",
        fecha_iso="2026-06-12", hora="1030", fecha_tz="2026-06-12T10:30:00+02:00",
        de="per01c@example.invalid", de_nombre="PersonaUno", para=["b@x"], cc=[], cco=[],
        asunto="Oferta Tibidabo", eml_origen="2026-06-12_oferta.eml", profundidad=0,
        ruta_anidacion=[], procedencia=[{"eml_origen": "2026-06-12_oferta.eml",
                                         "profundidad": 0, "ruta_anidacion": []}],
        capa="A", confianza="alta", auth={"dkim": "pass"}, sha256="deadbeef",
        adjuntos=[], idioma="es", formato_original="plain", emisor_dispositivo="",
        etiquetas=[], fuente="email", cuerpo="Texto del autor.",
        cuerpo_recortado_cita=False, respuesta_intercalada=False,
        charset_recuperado=False, mojibake_marcado=False, raw=b"raw",
    )
    base.update(kw)
    return RegistroMensaje(**base)


def test_nombre_fichero_mensaje():
    assert R.nombre_md(_msg()) == "2026-06-12_1030_oferta_tibidabo_MSG-00001.md"


def test_render_md_tiene_frontmatter_y_cuerpo():
    md = R.render_md(_msg(adjuntos=[AdjuntoRef(att_id="ATT-00003", msg_id_anidado=None,
                                               nombre="contrato.pdf", tipo="application/pdf",
                                               sha256="cafe")]))
    assert md.startswith("# GENERADO")
    assert "msg_id: MSG-00001" in md
    assert "rfc_message_id: a@x" in md
    assert "fuente: email" in md
    assert "ATT-00003" in md
    assert "Texto del autor." in md


def test_render_marca_flags_solo_si_true():
    md_sin = R.render_md(_msg())
    assert "respuesta_intercalada" not in md_sin
    md_con = R.render_md(_msg(respuesta_intercalada=True, mojibake_marcado=True))
    assert "respuesta_intercalada: true" in md_con
    assert "mojibake: true" in md_con


def _mb(confianza):
    # Helper de capa B reconstruida — reutilizado por Tasks 3, 4 y 5.
    return RegistroMensaje(
        msg_id="MSG-09001", capa="B", confianza=confianza, de="a@x.com", de_nombre="Ana",
        fecha_iso="2020-05-01", asunto="Tibidabo", cuerpo="cuerpo del mensaje reconstruido",
        reconstruido_desde_cita=True, reconstruido_de="MSG-00007", en_revision=True,
        fingerprint="fp:abc123", fuente="email")


def test_render_md_banner_media_reconstruida():
    md = R.render_md(_mb("media-reconstruida"))
    assert "> AUTORÍA POR VERIFICAR — reconstruida de una cita; remitente por cabecera, sin autenticar" in md
    assert "AUTORÍA POR RECONSTRUIR" not in md          # ya no usa la rama genérica antigua
    assert "RECONSTRUIDO DESDE CITA" not in md          # ni la de alta


def test_render_md_banner_alta_reconstruida_sin_cambio():
    md = R.render_md(_mb("alta-reconstruida"))
    assert "> RECONSTRUIDO DESDE CITA — remitente verificado por cabecera inline" in md
    assert "AUTORÍA POR VERIFICAR" not in md


def test_render_lectura_de_media_reconstruida_por_verificar():
    vista = R.render_correos_lectura([_mb("media-reconstruida")])
    assert "**De (reconstruido, por verificar):**" in vista
    assert "sin autenticar" in vista or "sin verificar" in vista
    # No usa el rótulo de alta (verificado por cabecera) para un media-reconstruida:
    assert "remitente verificado por cabecera" not in vista


def test_render_lectura_de_alta_reconstruida_sin_cambio():
    vista = R.render_correos_lectura([_mb("alta-reconstruida")])
    assert "**De (reconstruido):**" in vista
    assert "remitente verificado por cabecera" in vista
