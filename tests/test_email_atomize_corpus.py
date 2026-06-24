from __future__ import annotations
import json
from core.email_atomize.model import RegistroMensaje, AdjuntoUnico
from core.email_atomize import corpus as C
from core.email_atomize import render as R


def _msg(msg_id="MSG-00001", fecha="2026-06-12", asunto="Asunto", **kw):
    base = dict(
        msg_id=msg_id, rfc_message_id="a@x", in_reply_to="", hilo="a@x",
        fecha_iso=fecha, hora="1030", fecha_tz=f"{fecha}T10:30:00+02:00",
        de="per01c@example.invalid", de_nombre="Jaime", para=["b@x"], cc=[], cco=[],
        asunto=asunto, eml_origen="x.eml", profundidad=0, ruta_anidacion=[],
        procedencia=[], capa="A", confianza="alta", auth={}, sha256="deadbeef",
        adjuntos=[], idioma="es", formato_original="plain", emisor_dispositivo="",
        etiquetas=[], fuente="email", cuerpo="cuerpo", cuerpo_recortado_cita=False,
        respuesta_intercalada=False, charset_recuperado=False, mojibake_marcado=False,
        raw=b"raw",
    )
    base.update(kw)
    return RegistroMensaje(**base)


def test_corpus_jsonl_primera_linea_meta_y_una_por_mensaje():
    out = C.corpus_jsonl([_msg(), _msg(msg_id="MSG-00002")])
    lineas = out.strip().splitlines()
    meta = json.loads(lineas[0])
    assert meta["_no_editar"] is True and meta["_tipo"] == "corpus"
    fila = json.loads(lineas[1])
    assert fila["msg_id"] == "MSG-00001"
    assert fila["fuente"] == "email"
    assert "cuerpo" not in fila            # corpus es índice, no vuelca el cuerpo
    assert len(lineas) == 3                # meta + 2 mensajes


def test_correos_lectura_cronologico_con_anclas():
    doc = R.render_correos_lectura([
        _msg(msg_id="MSG-00002", fecha="2026-06-13", asunto="Segundo"),
        _msg(msg_id="MSG-00001", fecha="2026-06-12", asunto="Primero"),
    ])
    assert doc.index("Primero") < doc.index("Segundo")   # orden cronológico
    assert "Ref. MSG-00001" in doc
    assert "GENERADO" in doc.splitlines()[0] or "generado" in doc.lower()


def test_indice_adjuntos_lista_unicos():
    att = AdjuntoUnico(att_id="ATT-00001", sha256="cafe", nombre_original="contrato.pdf",
                       tipo="application/pdf", data=b"%PDF", primera_aparicion="2026-06-12",
                       mensajes=["MSG-00001", "MSG-00002"], etiquetas=[])
    doc = R.render_indice_adjuntos([att])
    assert "ATT-00001" in doc and "contrato.pdf" in doc
    assert "MSG-00001" in doc
