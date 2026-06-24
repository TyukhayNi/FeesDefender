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
