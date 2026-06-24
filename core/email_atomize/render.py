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
    fm.append("---")
    return _GEN_MD + "\n".join(fm) + "\n\n" + m.cuerpo.strip() + "\n"


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


def render_indice_adjuntos(adjuntos: list[AdjuntoUnico]) -> str:
    out = [_GEN_VIEW, f"# Índice de adjuntos ({len(adjuntos)} únicos)\n",
           "| ATT | Nombre | Tipo | 1ª aparición | Mensajes |",
           "| --- | --- | --- | --- | --- |"]
    for a in sorted(adjuntos, key=lambda x: x.att_id):
        msgs = ", ".join(a.mensajes)
        out.append(f"| {a.att_id} | {a.nombre_original} | {a.tipo} | "
                   f"{a.primera_aparicion} | {msgs} |")
    return "\n".join(out) + "\n"
