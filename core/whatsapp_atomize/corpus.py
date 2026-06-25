"""Índice de máquina corpus.jsonl (1 línea/mensaje + meta inicial)."""
from __future__ import annotations

import json

from .model import RegistroMensajeWA

_META = {
    "_README": "Generado por core.whatsapp_atomize — NO editar. Saltar líneas con _README/_tipo.",
    "_tipo": "corpus_whatsapp",
    "_no_editar": True,
}


def _fila(m: RegistroMensajeWA) -> dict:
    return {
        "msg_id": m.msg_id,
        "fingerprint": m.fingerprint,
        "chat_id": m.chat_id,
        "fecha": m.fecha_iso,
        "hora": m.hora,
        "autor_export": m.autor_export,
        "persona_id": m.persona_id,
        "rol": m.rol,
        "texto": m.texto,
        "es_sistema": m.es_sistema,
        "es_reenviado": m.es_reenviado,
        "adjunto": (m.adjunto.__dict__ if m.adjunto is not None else None),
        "contiene_enterrado": m.contiene_enterrado,
        "en_revision": m.en_revision,
        "responde_a": m.responde_a,
    }


def corpus_jsonl_wa(mensajes: list[RegistroMensajeWA]) -> str:
    lineas = [json.dumps(_META, ensure_ascii=False)]
    for m in sorted(mensajes, key=lambda x: (x.fecha_iso, x.hora, x.msg_id)):
        lineas.append(json.dumps(_fila(m), ensure_ascii=False))
    return "\n".join(lineas) + "\n"
