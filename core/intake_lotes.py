# core/intake_lotes.py
"""Lotes de entrega en ``00_Input`` (MEJORAS #54, spec 2026-07-17 rev 2).

Canales de ENTREGA (``whatsapp``, ``email``, ``manual``, ``entrevista``): cada
intake es su propia subcarpeta ``00_Input/<AAAA-MM-DD>_<fuente>_<NN>/`` con un
``_manifiesto.yaml`` (albarán forense de la entrega — NO fuente de dedup, eso
es M9). Canales ESPEJO (``01_Drive EV``, ``05_CRM``): cajón fijo, aquí no se
tocan.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

import yaml

from . import config
from .config import caso_path
from .intake_manifest import compute_sha256

MANIFIESTO_LOTE = "_manifiesto.yaml"

PATRON_LOTE = re.compile(
    r"^(\d{4}-\d{2}-\d{2})_(whatsapp|email|manual|entrevista)_(\d{2,})$"
)


def _lotes_existentes(case_dir: Path) -> set[str]:
    """Nombres de lote presentes en 00_Input/ Y en la bandeja _pendiente_checkin.

    El contador mira también la bandeja (spec §4): un intake sobre caso
    prestado se desvía ahí con su nombre de lote.
    """
    raices = [case_dir / "00_Input"]
    bandeja = case_dir / config.PENDIENTE_CHECKIN_SUBDIR
    if bandeja.is_dir():
        raices += [d / "00_Input" for d in bandeja.iterdir() if d.is_dir()]
    nombres: set[str] = set()
    for raiz in raices:
        if not raiz.is_dir():
            continue
        nombres |= {p.name for p in raiz.iterdir()
                    if p.is_dir() and PATRON_LOTE.match(p.name)}
    return nombres


def reservar_lote(case_id: str, fuente: str, origen: str,
                  *, hoy: date | None = None) -> Path:
    """Reserva (mkdir atómico) y devuelve el directorio del siguiente lote.

    Aplica el guard §6 vía ``dir_intake``: caso prestado/conflicto → el lote
    nace en la bandeja. La reserva es atómica: si el mkdir colisiona (dos
    sesiones concurrentes sobre un caso *disponible*), se prueba ``NN+1``.
    """
    if fuente not in config.FUENTES_LOTE:
        raise ValueError(
            f"Fuente de lote inválida: {fuente!r}. Válidas: {config.FUENTES_LOTE}. "
            "Los espejos (drive_ev, crm) no forman lotes."
        )
    from .case_manager import dir_intake  # import local: evita ciclo config↔case_manager

    fecha = (hoy or date.today()).isoformat()
    ocupados = _lotes_existentes(caso_path(case_id))
    nn = 1
    while True:
        nombre = f"{fecha}_{fuente}_{nn:02d}"
        if nombre in ocupados:
            nn += 1
            continue
        destino = dir_intake(case_id, f"00_Input/{nombre}", origen)
        try:
            destino.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            nn += 1
            continue
        return destino


_TIPOS_POR_EXT = {
    ".pdf": "pdf",
    ".jpg": "imagen", ".jpeg": "imagen", ".png": "imagen", ".tiff": "imagen",
    ".tif": "imagen", ".heic": "imagen", ".webp": "imagen", ".gif": "imagen",
    ".mp4": "video", ".mov": "video", ".avi": "video", ".webm": "video", ".3gp": "video",
    ".opus": "audio", ".ogg": "audio", ".m4a": "audio", ".aac": "audio",
    ".mp3": "audio", ".wav": "audio",
    ".docx": "docx", ".doc": "docx", ".odt": "docx", ".rtf": "docx",
    ".txt": "txt", ".md": "txt",
    ".eml": "eml", ".msg": "eml",
}


def clasificar_tipo_contenido(nombre: str) -> str:
    """Eje TIPO (spec §5) — por extensión. Vocabulario propio, NO el de procedencia."""
    n = Path(nombre).name
    if n == "_chat.txt":
        return "whatsapp"
    return _TIPOS_POR_EXT.get(Path(n).suffix.lower(), "otros")


@dataclass
class ItemManifiesto:
    """Una fila del albarán del lote. ``relpath`` es POSIX relativo al lote."""
    relpath: str
    sha256: str
    size: int
    tipo_contenido: str
    message_id: str | None = None      # solo ítems .eml (spec §5)
    duplicado_de: str | None = None    # anotación; el fichero SE COPIA igual (§6)


def _item_a_dict(item: ItemManifiesto) -> dict:
    return {k: v for k, v in asdict(item).items() if v is not None}


def escribir_manifiesto(lote_dir: Path, *, fuente: str, fecha_intake: str,
                        origen: str, items: list[ItemManifiesto],
                        fecha_intake_estimada: bool = False) -> Path:
    data: dict = {"fuente": fuente, "fecha_intake": fecha_intake, "origen": origen}
    if fecha_intake_estimada:
        data["fecha_intake_estimada"] = True
    data["items"] = [_item_a_dict(i) for i in sorted(items, key=lambda i: i.relpath)]
    path = Path(lote_dir) / MANIFIESTO_LOTE
    path.write_text(
        yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    return path


def leer_manifiesto(lote_dir: Path) -> dict | None:
    path = Path(lote_dir) / MANIFIESTO_LOTE
    if not path.is_file():
        return None
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None


def anexar_items(lote_dir: Path, items: list[ItemManifiesto], *, origen: str) -> Path:
    """Fusiona ítems en el manifiesto (crea si falta; el nuevo gana por relpath)."""
    lote_dir = Path(lote_dir)
    data = leer_manifiesto(lote_dir)
    if data is None:
        m = PATRON_LOTE.match(lote_dir.name)
        if m is None:
            raise ValueError(f"No es un directorio de lote: {lote_dir.name!r}")
        data = {"fuente": m.group(2), "fecha_intake": m.group(1),
                "origen": origen, "items": []}
    por_rel = {i.get("relpath"): i for i in data.get("items", [])}
    for item in items:
        por_rel[item.relpath] = _item_a_dict(item)
    data["items"] = [por_rel[k] for k in sorted(por_rel)]
    path = Path(lote_dir) / MANIFIESTO_LOTE
    path.write_text(
        yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    return path


def items_desde_disco(lote_dir: Path, *,
                      message_id_de: dict[str, str] | None = None,
                      duplicados: dict[str, str] | None = None) -> list[ItemManifiesto]:
    """Inventaría el lote para el albarán, excluyendo control y el propio manifiesto."""
    lote_dir = Path(lote_dir)
    message_id_de = message_id_de or {}
    duplicados = duplicados or {}
    items: list[ItemManifiesto] = []
    for p in sorted(lote_dir.rglob("*")):
        if not p.is_file():
            continue
        if p.name in config.INTAKE_CONTROL_FILES or p.name == MANIFIESTO_LOTE:
            continue
        rel = p.relative_to(lote_dir).as_posix()
        items.append(ItemManifiesto(
            relpath=rel, sha256=compute_sha256(p), size=p.stat().st_size,
            tipo_contenido=clasificar_tipo_contenido(p.name),
            message_id=message_id_de.get(rel), duplicado_de=duplicados.get(rel),
        ))
    return items
