"""Render humano: chat numerado (.md), atoms enterrados, índices."""
from __future__ import annotations

from .model import AtomEnterrado, RegistroMensajeWA

_GEN = "<!-- Generado por core.whatsapp_atomize — NO editar a mano. -->\n\n"


def _autor_visible(m: RegistroMensajeWA) -> str:
    if m.rol:
        return f"{m.autor_export} [{m.rol}]"
    return m.autor_export or "(sistema)"


def render_chat_lectura(chat_id, mensajes, enterrados, por_ref) -> str:
    lineas = [_GEN, f"# Chat: {chat_id}\n"]
    ent_por_portador: dict[str, list] = {}
    for a in enterrados:
        ent_por_portador.setdefault(a.portador_msg_id, []).append(a)
    for m in mensajes:
        marca = " · 🔁 reenviado" if m.es_reenviado else ""
        adj = ""
        if m.adjunto is not None:
            info = por_ref.get(m.adjunto.nombre, {})
            adj = f" · 📎 {m.adjunto.nombre}" + (" (ausente)" if info.get("ausente") else "")
        cab = f"**{m.msg_id}** · {m.fecha_iso} {m.hora} · {_autor_visible(m)}{marca}{adj}"
        lineas.append(cab)
        lineas.append(f"\n{m.texto.strip()}\n")
        for a in ent_por_portador.get(m.msg_id, []):
            lineas.append(f"> ↪ enterrado promovido: [{a.enterrado_id}](enterrados/{a.enterrado_id}.md)\n")
    return "\n".join(lineas) + "\n"


def render_enterrado(a: AtomEnterrado) -> str:
    banner = ("> AUTORÍA POR VERIFICAR — reconstruida de un mensaje pegado en el chat; "
              "WhatsApp no garantiza el origen.\n\n")
    fm = [
        f"# {a.enterrado_id}",
        f"- Portador: {a.portador_msg_id}",
        f"- De: {a.de_nombre or ''} <{a.de}>",
        f"- Fecha: {a.fecha_iso}",
        f"- Confianza: {a.confianza}",
    ]
    return _GEN + "\n".join(fm) + "\n\n" + banner + (a.extracto or "").strip() + "\n"


def render_indice(chats: dict[str, int]) -> str:
    """chats: {chat_id: n_mensajes}."""
    lineas = [_GEN, "# Índice de chats de WhatsApp\n"]
    for chat_id, n in sorted(chats.items()):
        lineas.append(f"- **{chat_id}** — {n} mensajes — [{chat_id}__LECTURA.md]({chat_id}__LECTURA.md)")
    return "\n".join(lineas) + "\n"


def render_indice_adjuntos(adjuntos) -> str:
    """Ficha de cada adjunto único (dedup por sha256)."""
    lineas = [_GEN, "# Índice de adjuntos\n"]
    for a in sorted(adjuntos, key=lambda x: x.att_id):
        lineas.append(f"- **{a.att_id}** · `{a.nombre_original}` · sha256 `{a.sha256}`")
    return "\n".join(lineas) + "\n"
