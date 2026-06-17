"""Glue de ingesta de exports de WhatsApp → ``00_Input/02_Whatsapp/`` (Fase A).

Capa de pegamento entre la UI y el parser puro.  NO depende de Streamlit
(recibe bytes + nombre).  Deposita el contenido del export verbatim, conserva
el zip original como artefacto de procedencia, registra en ``IntakeManifest``
(dedup por hash de zip) y emite el evento ``upload_whatsapp``.
"""
from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .config import WHATSAPP_SUBDIRS, caso_path, settings
from .whatsapp_export import parse_chat, referencias_adjuntos

_WHATSAPP_SUBDIR = "02_Whatsapp"
_AUDIO_EXTS = frozenset({".opus", ".ogg", ".m4a", ".aac", ".mp3"})
_ORIGINAL_ZIP_NAME = "_export_original.zip"


@dataclass
class ChatPreview:
    """Resumen de un export para la previsualización en la UI (sin escribir)."""

    chat_name: str
    n_mensajes: int
    rango_fechas: tuple[datetime, datetime] | None
    adjuntos_referenciados: list[str]
    adjuntos_presentes: list[str]
    adjuntos_faltantes: list[str]
    audios: list[str]


@dataclass
class DepositResult:
    """Resultado de depositar un export en el caso."""

    chat_dir: Path
    preview: ChatPreview
    files_written: list[Path] = field(default_factory=list)
    skipped_dedup: bool = False


def _sanitize_name(nombre: str) -> str:
    """Saneo del nombre del chat para usarlo como carpeta."""
    base = nombre
    if base.lower().endswith(".zip"):
        base = base[:-4]
    base = base.replace("\\", "_").replace("/", "_")
    for ch in ':*?"<>|':
        base = base.replace(ch, "_")
    base = base.replace("..", "_").strip().strip(".")
    return base or "chat"


def _read_members(content: bytes) -> dict[str, bytes]:
    """Lee un zip en memoria → {nombre_saneado: bytes}.  Saneo anti path-traversal."""
    members: dict[str, bytes] = {}
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        for info in zf.infolist():
            if info.filename.endswith("/"):
                continue
            parts = Path(info.filename).parts
            if any(p in ("..", "") or Path(p).is_absolute() for p in parts):
                continue
            members[Path(info.filename).name] = zf.read(info)
    return members


def _find_chat_txt(members: dict[str, bytes]) -> tuple[str, str]:
    """Localiza el ``.txt`` del chat y lo decodifica.  Lanza ValueError si no hay."""
    if "_chat.txt" in members:
        name = "_chat.txt"
    else:
        txts = [n for n in members if n.lower().endswith(".txt")]
        if not txts:
            raise ValueError(
                "El export no contiene ningún _chat.txt (.txt) — "
                "no parece una exportación de WhatsApp."
            )
        name = sorted(txts)[0]
    return name, members[name].decode("utf-8", errors="replace")


def analyze(content: bytes, *, zip_name: str) -> ChatPreview:
    """Analiza un export (.zip) en memoria SIN escribir nada.  Para la UI."""
    members = _read_members(content)
    chat_txt_name, texto = _find_chat_txt(members)

    msgs = parse_chat(texto)
    refs = referencias_adjuntos(msgs)

    presentes = sorted(n for n in members if n != chat_txt_name)
    presentes_set = set(presentes)
    faltantes = [r for r in refs if r not in presentes_set]
    audios = [n for n in presentes if Path(n).suffix.lower() in _AUDIO_EXTS]

    timestamps = [m.timestamp for m in msgs if m.timestamp is not None]
    rango = (min(timestamps), max(timestamps)) if timestamps else None

    return ChatPreview(
        chat_name=_sanitize_name(zip_name),
        n_mensajes=len(msgs),
        rango_fechas=rango,
        adjuntos_referenciados=refs,
        adjuntos_presentes=presentes,
        adjuntos_faltantes=faltantes,
        audios=audios,
    )
