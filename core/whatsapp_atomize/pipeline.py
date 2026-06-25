"""Orquestación: 00_Input/02_Whatsapp/**/_chat.txt → 01_Procesado/Whatsapp/.

Nunca toca 00_Input. Idempotente por fingerprint congelado en _registro.json.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from core.config import caso_path
from core.email_atomize.model import AdjuntoRef
from core.whatsapp_export import parse_chat

from . import corpus as corpus_mod
from . import render as render_mod
from .adjuntos import construir_adjuntos
from .ids import fingerprint, load_registro_wa
from .identidades import cargar_identidades_wa
from .model import AtomEnterrado, RegistroMensajeWA
from .reconstruccion import detectar_enterrado, es_reenviado

_WHATSAPP_IN = ("00_Input", "02_Whatsapp")
_OUT = ("01_Procesado", "Whatsapp")


def descubrir_chats(case_dir: Path) -> list[Path]:
    """Carpetas bajo 00_Input/02_Whatsapp que contienen un _chat.txt."""
    base = case_dir.joinpath(*_WHATSAPP_IN)
    if not base.exists():
        return []
    return sorted({p.parent for p in base.rglob("_chat.txt")}, key=lambda x: x.name)


def _hora_hhmm(ts) -> str:
    return f"{ts.hour:02d}{ts.minute:02d}" if ts is not None else ""


def _leer_media(chat_dir: Path) -> dict[str, bytes]:
    media: dict[str, bytes] = {}
    for p in chat_dir.iterdir():
        if p.is_file() and p.name not in ("_chat.txt",) and not p.name.startswith("_"):
            media[p.name] = p.read_bytes()
    return media


def atomize_whatsapp_case(case_id: str) -> dict:
    case_dir = caso_path(case_id)
    out_dir = case_dir.joinpath(*_OUT)
    ent_dir = out_dir / "enterrados"
    out_dir.mkdir(parents=True, exist_ok=True)
    registro = load_registro_wa(out_dir)
    mapa_ids = cargar_identidades_wa(case_dir)

    todos_msgs: list[RegistroMensajeWA] = []
    todos_ent: list[AtomEnterrado] = []
    chats_meta: dict[str, int] = {}
    por_ref_global: dict[str, dict] = {}
    adjuntos_unicos: dict[str, object] = {}  # sha256 -> AdjuntoUnico (dedup global entre chats)

    for chat_dir in descubrir_chats(case_dir):
        chat_id = chat_dir.name
        texto = (chat_dir / "_chat.txt").read_text(encoding="utf-8")
        registro.registrar_chat(chat_id, hashlib.sha256(texto.encode("utf-8")).hexdigest())
        media = _leer_media(chat_dir)
        wmsgs = parse_chat(texto)
        refs = [m.adjunto_ref for m in wmsgs if m.adjunto_ref]
        unicos_chat, por_ref = construir_adjuntos(refs, media, registro)
        por_ref_global.update(por_ref)
        for u in unicos_chat:
            adjuntos_unicos.setdefault(u.sha256, u)  # primera aparición gana (dedup global)

        registros_chat: list[RegistroMensajeWA] = []
        for w in wmsgs:
            ts_iso = w.timestamp.isoformat() if w.timestamp else "0000-00-00"
            fp = fingerprint(ts_iso, w.autor or "", w.texto)
            ident = mapa_ids.get((w.autor or "").strip().lower())
            r = RegistroMensajeWA(
                msg_id=registro.msg_id_for_fp(fp),
                fingerprint=fp,
                chat_id=chat_id,
                fecha_iso=(w.timestamp.date().isoformat() if w.timestamp else "0000-00-00"),
                hora=_hora_hhmm(w.timestamp),
                autor_export=w.autor or "",
                persona_id=(ident[0] if ident else ""),
                rol=(ident[2] if ident else ""),
                de_confianza=("identidades" if ident else ""),
                texto=w.texto,
                es_sistema=w.es_sistema,
                es_reenviado=es_reenviado(w.texto),
                adjunto=(AdjuntoRef(nombre=w.adjunto_ref) if w.adjunto_ref else None),
            )
            anc = detectar_enterrado(w.texto)
            if anc is not None and anc.de:
                r.contiene_enterrado = True
                r.en_revision = True
                key = f"{r.msg_id}|{anc.de}|{anc.fecha_iso}"
                todos_ent.append(AtomEnterrado(
                    enterrado_id=registro.ent_id_for(key),
                    portador_msg_id=r.msg_id, de=anc.de, de_nombre=anc.de_nombre,
                    fecha_iso=anc.fecha_iso, extracto=w.texto[:400]))
            registros_chat.append(r)

        chats_meta[chat_id] = len(registros_chat)
        todos_msgs.extend(registros_chat)

        ent_chat = [a for a in todos_ent if a.portador_msg_id in {r.msg_id for r in registros_chat}]
        (out_dir / f"{chat_id}__LECTURA.md").write_text(
            render_mod.render_chat_lectura(chat_id, registros_chat, ent_chat, por_ref),
            encoding="utf-8")

    if todos_ent:
        ent_dir.mkdir(parents=True, exist_ok=True)
        for a in todos_ent:
            (ent_dir / f"{a.enterrado_id}.md").write_text(render_mod.render_enterrado(a), encoding="utf-8")

    (out_dir / "INDICE.md").write_text(render_mod.render_indice(chats_meta), encoding="utf-8")
    (out_dir / "INDICE_ADJUNTOS.md").write_text(
        render_mod.render_indice_adjuntos(list(adjuntos_unicos.values())), encoding="utf-8")
    (out_dir / "CRONOLOGIA.md").write_text(
        render_mod.render_cronologia(todos_msgs), encoding="utf-8")
    (out_dir / "corpus.jsonl").write_text(corpus_mod.corpus_jsonl_wa(todos_msgs), encoding="utf-8")
    registro.save()

    return {"chats": len(chats_meta), "mensajes": len(todos_msgs),
            "enterrados": len(todos_ent), "adjuntos": len(adjuntos_unicos)}
