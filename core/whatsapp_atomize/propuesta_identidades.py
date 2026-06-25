"""Reúne autores + muestras de un caso para que Claude-en-sesión proponga identidades.yaml.

Lectura pura (sin escribir, sin API). El gate y la persistencia los hace el letrado.
"""
from __future__ import annotations

from core.config import caso_path
from core.whatsapp_export import parse_chat

from .pipeline import descubrir_chats

_MAX_MUESTRAS = 5


def preparar_propuesta(case_id: str) -> list[dict]:
    case_dir = caso_path(case_id)
    muestras: dict[str, list[str]] = {}
    for chat_dir in descubrir_chats(case_dir):
        texto = (chat_dir / "_chat.txt").read_text(encoding="utf-8")
        for m in parse_chat(texto):
            if m.es_sistema or not m.autor:
                continue
            buf = muestras.setdefault(m.autor, [])
            if len(buf) < _MAX_MUESTRAS and m.texto.strip():
                buf.append(m.texto.strip()[:120])
    return [{"autor_export": a, "muestras": s} for a, s in sorted(muestras.items())]
