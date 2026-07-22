from __future__ import annotations
import json
from core.email_atomize.model import RegistroMensaje, AdjuntoRef
from core.email_atomize import render as R


def _msg(**kw) -> RegistroMensaje:
    base = dict(
        msg_id="MSG-00001", rfc_message_id="a@x", in_reply_to="", hilo="a@x",
        fecha_iso="2026-06-12", hora="1030", fecha_tz="2026-06-12T10:30:00+02:00",
        de="per01c@example.invalid", de_nombre="PersonaUno", para=["b@x"], cc=[], cco=[],
        asunto="Oferta [inmueble]", eml_origen="2026-06-12_oferta.eml", profundidad=0,
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
    assert R.nombre_md(_msg()) == "2026-06-12_1030_oferta_inmueble_MSG-00001.md"


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
        fecha_iso="2020-05-01", asunto="[inmueble]", cuerpo="cuerpo del mensaje reconstruido",
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


def test_render_revision_emite_reconstruidos_md_y_jsonl():
    mb_media = _mb("media-reconstruida")
    mb_alta = RegistroMensaje(
        msg_id="MSG-09002", capa="B", confianza="alta-reconstruida", de="b@x.com",
        fecha_iso="2020-06-01", asunto="Otro", cuerpo="otro cuerpo",
        reconstruido_desde_cita=True, reconstruido_de="MSG-00008", fingerprint="fp:def456")
    d = R.render_revision([mb_media, mb_alta], [], watched=None)
    # Mantiene las claves existentes + las dos nuevas:
    assert set(d) == {"cola.md", "casi_duplicados.md", "identidades_vigiladas.md",
                      "reconstruidos.md", "reconstruidos.jsonl"}
    rec = d["reconstruidos.md"]
    # Lista SOLO los media-reconstruida, con sus columnas:
    assert "MSG-09001" in rec and "a@x.com" in rec and "2020-05-01" in rec
    assert "[inmueble]" in rec and "MSG-00007" in rec
    # NO incluye el alta-reconstruida:
    assert "MSG-09002" not in rec
    # El espejo .jsonl: una línea JSON parseable por cada media-reconstruida, y solo esos:
    lineas = [l for l in d["reconstruidos.jsonl"].splitlines() if l.strip()]
    assert len(lineas) == 1
    fila = json.loads(lineas[0])
    assert fila["msg_id"] == "MSG-09001" and fila["de"] == "a@x.com"
    assert fila["fecha_iso"] == "2020-05-01" and fila["reconstruido_de"] == "MSG-00007"
    assert fila["fingerprint"] == "fp:abc123"
