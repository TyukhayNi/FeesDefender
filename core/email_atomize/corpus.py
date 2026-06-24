"""Índice de máquina ``corpus.jsonl`` (1 línea/mensaje + registro meta inicial)."""
from __future__ import annotations

import json

from .model import RegistroMensaje

_META = {
    "_README": "Generado por core.email_atomize — NO editar. Índice de máquina; "
               "el lector debe saltar líneas con _README/_tipo.",
    "_tipo": "corpus",
    "_no_editar": True,
}


def _nombre_md_lazy(m: RegistroMensaje) -> str:
    from .render import nombre_md
    return nombre_md(m)


def _fila(m: RegistroMensaje) -> dict:
    return {
        "msg_id": m.msg_id,
        "rfc_message_id": m.rfc_message_id,
        "in_reply_to": m.in_reply_to,
        "hilo": m.hilo,
        "fecha": m.fecha_tz or m.fecha_iso,
        "de": m.de,
        "de_nombre": m.de_nombre,
        "para": m.para,
        "cc": m.cc,
        "asunto": m.asunto,
        "capa": m.capa,
        "confianza": m.confianza,
        "profundidad": m.profundidad,
        "ruta_anidacion": m.ruta_anidacion,
        "procedencia": m.procedencia,
        "adjuntos": [a.__dict__ for a in m.adjuntos],
        "idioma": m.idioma,
        "sha256": m.sha256,
        "fuente": m.fuente,
        "ruta_md": "mensajes/" + _nombre_md_lazy(m),
    }


def corpus_jsonl(mensajes: list[RegistroMensaje]) -> str:
    lineas = [json.dumps(_META, ensure_ascii=False)]
    for m in sorted(mensajes, key=lambda x: (x.fecha_iso, x.hora, x.msg_id)):
        lineas.append(json.dumps(_fila(m), ensure_ascii=False))
    return "\n".join(lineas) + "\n"
