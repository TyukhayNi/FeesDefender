"""Glue de ingesta de exports de WhatsApp → ``00_Input/<lote>/`` (MEJORAS #54).

Capa de pegamento entre la UI y el parser puro.  NO depende de Streamlit
(recibe bytes + nombre).  Deposita el contenido del export verbatim (el
``_chat.txt`` + todos los media + el zip original) en su propio lote de
entrega (``core.intake_lotes``), registra en ``IntakeManifest`` (dedup por
hash de zip = idempotencia de canal) y emite el evento ``upload_whatsapp``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from . import intake_log, intake_lotes
from .config import WHATSAPP_SUBDIRS, caso_path, settings
from .intake_manifest import IntakeManifest, compute_sha256_bytes
from .intake_utils import safe_zip_members, sanitize_filename
from .whatsapp_export import filter_by_date_range, parse_chat, referencias_adjuntos

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
    return sanitize_filename(base, mode="folder", fallback="chat")


def _read_members(content: bytes) -> dict[str, bytes]:
    """Lee un zip en memoria → {nombre_saneado: bytes}.  Saneo anti path-traversal."""
    return safe_zip_members(content)


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


def deposit_export(
    case_id: str,
    rol_subdir: str,
    content: bytes,
    *,
    zip_name: str,
    date_range: tuple[datetime | None, datetime | None] | None = None,
) -> DepositResult:
    """Deposita un export de WhatsApp en ``00_Input/<lote>/<rol>/<chat>/``.

    Verbatim: escribe el ``_chat.txt`` + todos los media + el zip original,
    con un ``_manifiesto.yaml`` del lote (MEJORAS #54). El lote se reserva vía
    ``intake_lotes.reservar_lote`` (aplica el guard de escritura §6: caso
    prestado/conflicto → el lote nace en ``_pendiente_checkin/whatsapp/...``).

    Idempotencia de CANAL (no confundir con dedup §6): si ese export es
    byte-idéntico a uno ya importado, no se abre lote nuevo — se devuelve
    ``skipped_dedup=True`` con ``chat_dir`` apuntando al depósito previo.
    Dentro de un lote nuevo, cada ítem que ya existía en otro lote (M9) se
    COPIA igualmente y se anota con ``duplicado_de`` (§6).

    Registra cada fichero en el manifest M9 y emite el evento
    ``upload_whatsapp``.
    """
    if rol_subdir not in WHATSAPP_SUBDIRS:
        raise ValueError(
            f"rol_subdir inválido: {rol_subdir!r}. "
            f"Válidos: {WHATSAPP_SUBDIRS}"
        )
    case_dir = caso_path(case_id)
    if not case_dir.exists():
        raise FileNotFoundError(
            f"El caso '{case_id}' no existe en {settings.casos_root}. "
            "Llama a ensure_case() antes de deposit_export()."
        )

    preview = analyze(content, zip_name=zip_name)
    zip_sha = compute_sha256_bytes(content)
    members = _read_members(content)
    chat_txt_name, texto = _find_chat_txt(members)

    files_written: list[Path] = []
    with IntakeManifest(case_id) as manifest:
        previo = manifest.lookup(zip_sha)
        if previo is not None:
            # Idempotencia de CANAL (no dedup cross-lote §6): el mismo export
            # byte-idéntico ya entró; no se abre lote nuevo.
            prev_dir = case_dir / "00_Input" / Path(previo["primary_path"]).parent
            return DepositResult(
                chat_dir=prev_dir, preview=preview, skipped_dedup=True
            )

        lote_dir = intake_lotes.reservar_lote(case_id, "whatsapp", "whatsapp")
        lote = lote_dir.name
        chat_dir = lote_dir / rol_subdir / preview.chat_name
        chat_dir.mkdir(parents=True, exist_ok=True)
        rel_base = f"{lote}/{rol_subdir}/{preview.chat_name}"
        items: list[intake_lotes.ItemManifiesto] = []

        def _escribe(name: str, data: bytes, **extra) -> None:
            sha = compute_sha256_bytes(data)
            # duplicado_de ANTES de register (register crearía el entry propio)
            dup = manifest.duplicado_de_para(sha, len(data))
            dest = chat_dir / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)          # el duplicado SE COPIA igual (§6)
            files_written.append(dest)
            manifest.register(
                sha, f"{rel_base}/{name}", source="whatsapp",
                chat=preview.chat_name, **extra,
            )
            items.append(intake_lotes.ItemManifiesto(
                relpath=f"{rol_subdir}/{preview.chat_name}/{name}",
                sha256=sha, size=len(data),
                tipo_contenido=intake_lotes.clasificar_tipo_contenido(name),
                duplicado_de=dup,
            ))

        for name, data in members.items():
            _escribe(name, data)
        _escribe(_ORIGINAL_ZIP_NAME, content, es_zip_origen=True)

        if date_range is not None:
            desde, hasta = date_range
            recortados = filter_by_date_range(parse_chat(texto), desde, hasta)
            lineas = [
                f"[{m.timestamp}] {m.autor or '(sistema)'}: {m.texto}"
                for m in recortados
            ]
            _escribe("_chat_recortado.txt", "\n".join(lineas).encode("utf-8"))

        intake_lotes.escribir_manifiesto(
            lote_dir, fuente="whatsapp", fecha_intake=lote[:10],
            origen="whatsapp_intake", items=items,
        )

    intake_log.append_event(
        case_id,
        "upload_whatsapp",
        details={
            "chat": preview.chat_name,
            "rol": rol_subdir,
            "lote": lote,
            "n_mensajes": preview.n_mensajes,
            "adjuntos_presentes": len(preview.adjuntos_presentes),
            "adjuntos_faltantes": preview.adjuntos_faltantes,
            "audios": len(preview.audios),
            "zip_sha256": zip_sha,
        },
    )

    return DepositResult(
        chat_dir=chat_dir,
        preview=preview,
        files_written=files_written,
        skipped_dedup=False,
    )
