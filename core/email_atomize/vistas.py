"""Capa de caso: vistas temáticas (vistas.yaml). Artefacto de SOLO-LECTURA: no muta ningún .md.

Diseño: spec §4.2, §5.2. ``render_vistas`` es función pura sobre la lista de RegistroMensaje
en memoria; devuelve ({fichero: contenido}, notas). Una vista inválida se omite con nota.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .identidades import Identidades
from .inline import _fold, normaliza_cuerpo
from .model import RegistroMensaje

_GEN = "<!-- GENERADO por core.email_atomize — NO editar a mano. -->\n"


@dataclass
class DefVista:
    id: str
    titulo: str = ""
    tipo: str = ""
    persona: str = ""
    palabras_clave: list[str] = field(default_factory=list)
    incluye_msg: list[str] = field(default_factory=list)
    excluye_msg: list[str] = field(default_factory=list)
    desde: str = ""
    hasta: str = ""


def cargar_vistas(case_dir: Path | str) -> list[DefVista]:
    """Lee <case_dir>/vistas.yaml. Sin fichero → [] (no se genera ninguna vista)."""
    path = Path(case_dir) / "vistas.yaml"
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    defs: list[DefVista] = []
    for raw in data.get("vistas", []) or []:
        defs.append(DefVista(
            id=str(raw.get("id") or ""), titulo=str(raw.get("titulo") or ""),
            tipo=str(raw.get("tipo") or ""), persona=str(raw.get("persona") or ""),
            palabras_clave=list(raw.get("palabras_clave") or []),
            incluye_msg=list(raw.get("incluye_msg") or []),
            excluye_msg=list(raw.get("excluye_msg") or []),
            desde=str(raw.get("desde") or ""), hasta=str(raw.get("hasta") or "")))
    return defs


def _orden(m: RegistroMensaje):
    return (m.fecha_iso, m.hora, m.msg_id)


def _seleccion_persona(mensajes, identidades, d):
    """Devuelve [(mensaje, rol, estado_dir)] o None si la persona no existe."""
    p = identidades.persona(d.persona)
    if p is None:
        return None
    emails = p.emails()
    filas = []
    for m in mensajes:
        autor = (m.de or "").lower() in emails
        dest = any(v in emails for v in m.para) or any(v in emails for v in m.cc)
        if not (autor or dest):
            continue
        if autor:
            email_match = (m.de or "").lower()
        else:
            email_match = next((v for v in list(m.para) + list(m.cc) if v in emails), "")
        filas.append((m, "autor" if autor else "destinatario",
                      identidades.estado_de(email_match)))
    filas.sort(key=lambda t: _orden(t[0]))
    return filas


def _seleccion_tematica(mensajes, d):
    kw = [_fold(k) for k in d.palabras_clave if k]
    inc, exc = set(d.incluye_msg), set(d.excluye_msg)
    out = []
    for m in mensajes:
        if m.msg_id in exc:          # excluye gana siempre
            continue
        if m.msg_id in inc:          # incluye fuerza dentro (bypassa keyword y rango)
            out.append(m)
            continue
        if d.desde and m.fecha_iso < d.desde:
            continue
        if d.hasta and m.fecha_iso > d.hasta:
            continue
        texto = _fold(m.asunto or "") + " " + normaliza_cuerpo(m.cuerpo or "")
        if kw and any(k in texto for k in kw):
            out.append(m)
    out.sort(key=_orden)
    return out


def _celda(s: str) -> str:
    return (s or "").replace("|", " ").replace("\n", " ").strip()


def _render_persona(d, p, filas):
    out = [_GEN, f"# {d.titulo or d.id} ({len(filas)} mensajes)\n",
           f"_Persona: {p.nombre} · vigilada: {'sí' if p.vigilada else 'no'} · "
           f"direcciones: {', '.join(sorted(p.emails()))}_\n",
           "| Fecha | Hora | Asunto | Ref | Rol | De | Capa | Confianza | Estado dir | Portador |",
           "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for m, rol, estado in filas:
        out.append(f"| {m.fecha_iso} | {m.hora or '----'} | {_celda(m.asunto) or '(sin asunto)'} "
                   f"| {m.msg_id} | {rol} | {m.de} | {m.capa} | {m.confianza} | {estado or '—'} "
                   f"| {m.reconstruido_de or '—'} |")
    return "\n".join(out) + "\n"


def _render_tematica(d, mensajes):
    out = [_GEN, f"# {d.titulo or d.id} ({len(mensajes)} mensajes)\n",
           f"_Palabras clave: {', '.join(d.palabras_clave) or '—'}_\n",
           "| Fecha | Hora | Asunto | Ref | De | Capa | Confianza |",
           "| --- | --- | --- | --- | --- | --- | --- |"]
    for m in mensajes:
        out.append(f"| {m.fecha_iso} | {m.hora or '----'} | {_celda(m.asunto) or '(sin asunto)'} "
                   f"| {m.msg_id} | {m.de} | {m.capa} | {m.confianza} |")
    return "\n".join(out) + "\n"


def render_vistas(mensajes, identidades: Identidades, defs: list[DefVista]):
    """({fichero: contenido}, notas). No toca disco. Vista inválida → omitida + nota."""
    salidas: dict[str, str] = {}
    notas: list[str] = []
    for d in defs:
        if not d.id:
            notas.append("vista sin 'id' omitida")
            continue
        if d.tipo == "persona":
            filas = _seleccion_persona(mensajes, identidades, d)
            if filas is None:
                notas.append(f"vista {d.id}: persona {d.persona!r} no existe en identidades.yaml")
                continue
            salidas[f"{d.id}.md"] = _render_persona(d, identidades.persona(d.persona), filas)
        elif d.tipo == "tematica":
            salidas[f"{d.id}.md"] = _render_tematica(d, _seleccion_tematica(mensajes, d))
        else:
            notas.append(f"vista {d.id}: tipo desconocido {d.tipo!r}")
    return salidas, notas
