"""Render de las salidas humanas: .md por mensaje, CORREOS_LECTURA.md, INDICE_ADJUNTOS.md."""
from __future__ import annotations

import json

from core.email_export import _slug_descripcion
from .model import RegistroMensaje, AdjuntoUnico

_GEN_MD = "# GENERADO por core.email_atomize — NO editar (fuente de verdad regenerable).\n"


def nombre_md(m: RegistroMensaje) -> str:
    slug = _slug_descripcion(m.asunto)
    hora = m.hora or "0000"
    return f"{m.fecha_iso}_{hora}_{slug}_{m.msg_id}.md"


def _yaml_lista(nombre: str, valores: list[str]) -> str:
    if not valores:
        return f"{nombre}: []"
    items = "\n".join(f"  - {json.dumps(v, ensure_ascii=False)}" for v in valores)
    return f"{nombre}:\n{items}"


def render_md(m: RegistroMensaje) -> str:
    fm: list[str] = ["---"]
    fm.append(f"msg_id: {m.msg_id}")
    fm.append(f"rfc_message_id: {m.rfc_message_id}")
    fm.append(f"in_reply_to: {m.in_reply_to}")
    fm.append(f"hilo: {m.hilo}")
    fm.append(f"fecha: {m.fecha_tz or m.fecha_iso}")
    fm.append(f"de: {m.de}")
    fm.append(f"de_nombre: {json.dumps(m.de_nombre, ensure_ascii=False)}")
    fm.append(_yaml_lista("para", m.para))
    fm.append(_yaml_lista("cc", m.cc))
    if m.cco:
        fm.append(_yaml_lista("cco", m.cco))
    fm.append(f"asunto: {json.dumps(m.asunto, ensure_ascii=False)}")
    fm.append(f"eml_origen: {json.dumps(m.eml_origen, ensure_ascii=False)}")
    fm.append(f"profundidad: {m.profundidad}")
    fm.append(_yaml_lista("ruta_anidacion", m.ruta_anidacion))
    fm.append(f"procedencia: {json.dumps(m.procedencia, ensure_ascii=False)}")
    fm.append(f"capa: {m.capa}")
    fm.append(f"confianza: {m.confianza}")
    fm.append(f"auth: {json.dumps(m.auth, ensure_ascii=False)}")
    fm.append(f"sha256: {m.sha256}")
    fm.append(f"adjuntos: {json.dumps([a.__dict__ for a in m.adjuntos], ensure_ascii=False)}")
    fm.append(f"idioma: {m.idioma}")
    fm.append(f"formato_original: {m.formato_original}")
    if m.emisor_dispositivo:
        fm.append(f"emisor_dispositivo: {json.dumps(m.emisor_dispositivo, ensure_ascii=False)}")
    fm.append(_yaml_lista("etiquetas", m.etiquetas))
    fm.append(f"fuente: {m.fuente}")
    if m.cuerpo_recortado_cita:
        fm.append("cuerpo_recortado_cita: true")
    if m.respuesta_intercalada:
        fm.append("respuesta_intercalada: true")
    if m.charset_recuperado:
        fm.append("charset_recuperado: true")
    if m.mojibake_marcado:
        fm.append("mojibake: true")
    # --- Layer B ---
    if m.reconstruido_desde_cita:
        fm.append("reconstruido_desde_cita: true")
    if m.reconstruido_de:
        fm.append(f"reconstruido_de: {m.reconstruido_de}")
    if m.fecha_inferida:
        fm.append("fecha_inferida: true")
    if m.ambiguedad_profundidad:
        fm.append("ambiguedad_profundidad: true")
    if m.en_revision:
        fm.append("en_revision: true")
    if m.fingerprint:
        fm.append(f"fingerprint: {m.fingerprint}")
    fm.append("---")
    banner = ""
    if m.capa == "B":
        banner = ("> RECONSTRUIDO DESDE CITA — remitente verificado por cabecera inline\n\n"
                  if m.confianza == "alta-reconstruida"
                  else "> AUTORÍA POR RECONSTRUIR — sin verificar\n\n")
    return _GEN_MD + "\n".join(fm) + "\n\n" + banner + m.cuerpo.strip() + "\n"


_GEN_VIEW = "<!-- GENERADO por core.email_atomize — NO editar a mano. -->\n"


def _ancla(msg_id: str) -> str:
    return msg_id.lower()


def render_correos_lectura(mensajes: list[RegistroMensaje]) -> str:
    ms = sorted(mensajes, key=lambda x: (x.fecha_iso, x.hora, x.msg_id))
    out = [_GEN_VIEW, f"# Correos — lectura ({len(ms)} mensajes)\n", "## Índice\n"]
    for m in ms:
        out.append(f"- [{m.fecha_iso} {m.hora} — {m.asunto or '(sin asunto)'}]"
                   f"(#{_ancla(m.msg_id)})")
    out.append("\n---\n")
    for m in ms:
        out.append(f'<a id="{_ancla(m.msg_id)}"></a>')
        out.append(f"### {m.fecha_iso} · {m.hora} — {m.asunto or '(sin asunto)'}\n")
        if m.capa == "B":
            out.append(f"**De (reconstruido):** {m.de_nombre or m.de} <{m.de}>  ")
            out.append("_Mensaje recuperado de una cita; remitente verificado por cabecera "
                       f"(Ref. {m.reconstruido_de or '—'})_  ")
        else:
            out.append(f"**De:** {m.de_nombre or m.de} <{m.de}>  ")
        out.append(f"**Para:** {', '.join(m.para) or '—'}  ")
        if m.cc:
            out.append(f"**CC:** {', '.join(m.cc)}  ")
        if m.cco:
            out.append(f"**CCO:** {', '.join(m.cco)}  ")
        if m.adjuntos:
            nombres = ", ".join(a.nombre for a in m.adjuntos)
            out.append(f"**Adjuntos:** {nombres}  ")
        if m.emisor_dispositivo and "iphone" in m.emisor_dispositivo.lower():
            out.append("_Enviado desde iPhone_  ")
        out.append("")
        out.append(m.cuerpo.strip())
        out.append(f"\n<sub>Ref. {m.msg_id}</sub>\n")
        out.append("\n---\n")
    return "\n".join(out) + "\n"


def render_revision(mensajes_b: list[RegistroMensaje], punteros: list, watched=None,
                    upgrades: list | None = None) -> dict:
    """Colas de revisión Layer B: ``cola.md`` (punteros media/baja), ``casi_duplicados.md``
    (upgrades de fidelidad: cita inline resuelta a una copia limpia de Capa A), ``del_burgo.md``
    (autoría vigilada). Regenerado cada corrida (determinista → idempotente)."""
    if watched is None:
        from . import inline
        watched = inline.IDENTIDADES_VIGILADAS
    upgrades = upgrades or []

    cola = [_GEN_VIEW, "# Cola de revisión Layer B (media/baja)\n",
            "| Portador | Estilo | Prof | Confianza | Motivo | De | Extracto |",
            "| --- | --- | --- | --- | --- | --- | --- |"]
    for p in punteros:
        ext = (p.extracto or "").replace("|", " ").replace("\n", " ").strip()[:120]
        cola.append(f"| {p.portador_msg_id} | {p.estilo} | {p.profundidad} | {p.confianza} | "
                    f"{p.motivo} | {p.de} | {ext} |")

    casi = [_GEN_VIEW, "# Casi-duplicados / upgrades de fidelidad Layer B\n",
            "Citas inline resueltas a una copia LIMPIA de Capa A (no se acuña mensaje nuevo; "
            "el .md de Capa A NO se muta). La verdad del puente vive en `_registro.json` "
            "(`alias`/`mensajes_fp`).\n",
            "| Mensaje Capa A | Citado en | Profundidad | Fingerprint |",
            "| --- | --- | --- | --- |"]
    for u in upgrades:
        casi.append(f"| {u.get('msg_a')} | {u.get('citado_en')} | {u.get('profundidad')} | "
                    f"{u.get('fingerprint')} |")

    db = [_GEN_VIEW, "# Autoría vigilada (PersonaUno) — revisión probatoria\n",
          "Toda cita atribuida a una identidad vigilada: promovidas (mensaje B propio) y "
          "las que quedaron en revisión (media/baja). Cada una, a verificar contra la fuente.\n",
          "| Ref | De | Fecha | Confianza | Portador | Estado |",
          "| --- | --- | --- | --- | --- | --- |"]
    for m in mensajes_b:
        if m.de in watched:
            db.append(f"| {m.msg_id} | {m.de} | {m.fecha_iso} | {m.confianza} | "
                      f"{m.reconstruido_de} | promovido |")
    for p in punteros:
        if p.de in watched:
            db.append(f"| (cita) | {p.de} | {p.fecha_iso} | {p.confianza} | "
                      f"{p.portador_msg_id} | revisar |")

    return {"cola.md": "\n".join(cola) + "\n",
            "casi_duplicados.md": "\n".join(casi) + "\n",
            "del_burgo.md": "\n".join(db) + "\n"}


def render_indice_adjuntos(adjuntos: list[AdjuntoUnico]) -> str:
    out = [_GEN_VIEW, f"# Índice de adjuntos ({len(adjuntos)} únicos)\n",
           "| ATT | Nombre | Tipo | 1ª aparición | Mensajes |",
           "| --- | --- | --- | --- | --- |"]
    for a in sorted(adjuntos, key=lambda x: x.att_id):
        msgs = ", ".join(a.mensajes)
        out.append(f"| {a.att_id} | {a.nombre_original} | {a.tipo} | "
                   f"{a.primera_aparicion} | {msgs} |")
    return "\n".join(out) + "\n"
