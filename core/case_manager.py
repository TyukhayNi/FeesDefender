"""Creación y registro de casos.

`ensure_case` es idempotente: si la carpeta existe, solo asegura que estén las
subcarpetas estándar. Nunca borra contenido del usuario.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from .config import CASO_SUBDIRS, INPUT_SUBDIRS, WHATSAPP_SUBDIRS, EMAIL_SUBDIRS, caso_path, settings
from .utils import now_iso, write_md


@dataclass
class ExpedienteLink:
    """Referencia a un expediente del CRM vinculado a este caso."""
    id: str                              # ID numérico en sudespacho
    element: str                         # "expedientes_judiciales" | "extrajudiciales"
    input_dir: str                       # subcarpeta en 00_Input (ej. "sudespacho_648")


@dataclass
class CaseMeta:
    case_id: str
    titulo: str
    referencia_crm: str | None = None    # "BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU"
    cliente: str | None = None
    contraparte: str | None = None
    jurisdiccion: str = "civil"
    organo: str | None = None
    cuantia: float | None = None
    drive_link: str | None = None
    drive_remote_path: str | None = None
    drive_ev_team_id: str | None = None   # Shared Drive ID de la carpeta E&V (gdrive_ev)
    drive_ev_folder_id: str | None = None  # Folder ID de la carpeta W-XXXXXX
    estado: str = "instruccion"          # instruccion | predemanda | demanda | recurso | archivado
    sudespacho_expedientes: list[dict] = None   # lista de ExpedienteLink serializados
    creado_en: str = ""
    actualizado_en: str = ""

    def __post_init__(self):
        if self.sudespacho_expedientes is None:
            self.sudespacho_expedientes = []


def _write_case_index(case_dir: Path, meta: CaseMeta) -> Path:
    index = case_dir / "00_Input" / "_caso.md"
    ref_line = f"- Referencia CRM: **{meta.referencia_crm}**\n" if meta.referencia_crm else ""
    exp_lines = ""
    if meta.sudespacho_expedientes:
        exp_lines = "\n## Expedientes sudespacho\n\n"
        for e in meta.sudespacho_expedientes:
            exp_lines += f"- `{e['element']}` ID {e['id']} → `00_Input/{e['input_dir']}/`\n"
    drive_ev_line = (
        f"- Drive E&V team: `{meta.drive_ev_team_id}` / folder: `{meta.drive_ev_folder_id}`\n"
        if meta.drive_ev_team_id or meta.drive_ev_folder_id else ""
    )
    body = (
        f"# {meta.titulo}\n\n"
        f"Caso `{meta.case_id}` — estado **{meta.estado}**.\n\n"
        f"{ref_line}"
        f"## Partes\n\n"
        f"- Cliente: {meta.cliente or '_(pendiente)_'}\n"
        f"- Contraparte: {meta.contraparte or '_(pendiente)_'}\n\n"
        f"## Sede\n\n"
        f"- Jurisdicción: {meta.jurisdiccion}\n"
        f"- Órgano: {meta.organo or '_(pendiente)_'}\n"
        f"- Cuantía: {meta.cuantia if meta.cuantia is not None else '_(pendiente)_'}\n\n"
        f"## Fuente documental\n\n"
        f"- Drive: {meta.drive_link or '_(sin enlace)_'}\n"
        f"- Remoto rclone: `{meta.drive_remote_path or '_(no configurado)_'}`\n"
        f"{drive_ev_line}"
        f"{exp_lines}\n"
        f"## Navegación\n\n"
        f"- [[scoring]]\n"
        f"- [[viabilidad]]\n"
        f"- [[hechos_atomicos]]\n"
        f"- [[contradicciones]]\n"
        f"- [[demanda]]\n"
    )
    fm = {
        "case_id": meta.case_id,
        "tipo": "caso_index",
        "fase": "00_Input",
        "fecha": meta.creado_en,
        "estado": meta.estado,
        "referencia_crm": meta.referencia_crm,
        "sudespacho_expedientes": meta.sudespacho_expedientes,
        "drive": meta.drive_remote_path,
        "meta": asdict(meta),
    }
    return write_md(index, fm, body)


def register_expediente(
    case_id: str,
    expediente_id: str,
    element: str,
) -> str:
    """Registra un expediente del CRM en el índice del caso.

    Añade la entrada a `sudespacho_expedientes` en `_caso.md` si no existe.
    Devuelve el nombre de la subcarpeta de ingesta: `sudespacho_{expediente_id}`.
    Es idempotente: si el expediente ya está registrado, no hace nada.
    """
    input_dir_name = f"sudespacho_{expediente_id}"
    index = caso_path(case_id) / "00_Input" / "_caso.md"

    if not index.exists():
        return input_dir_name  # ensure_case no se llamó aún — se registrará al crearlo

    import yaml as _yaml
    text = index.read_text(encoding="utf-8")

    # Extraer frontmatter existente
    if text.startswith("---"):
        _, fm_raw, _ = text.split("---", 2)
        fm = _yaml.safe_load(fm_raw) or {}
    else:
        fm = {}

    expedientes = fm.get("sudespacho_expedientes") or []
    ids_existentes = {str(e.get("id")) for e in expedientes if isinstance(e, dict)}

    if str(expediente_id) not in ids_existentes:
        expedientes.append({
            "id": str(expediente_id),
            "element": element,
            "input_dir": input_dir_name,
        })
        # Re-escribir el índice con el nuevo expediente
        meta_dict = (fm.get("meta") or {})
        meta_dict["sudespacho_expedientes"] = expedientes
        meta = CaseMeta(
            case_id=case_id,
            titulo=meta_dict.get("titulo", case_id),
            referencia_crm=meta_dict.get("referencia_crm"),
            cliente=meta_dict.get("cliente"),
            contraparte=meta_dict.get("contraparte"),
            jurisdiccion=meta_dict.get("jurisdiccion", "civil"),
            organo=meta_dict.get("organo"),
            cuantia=meta_dict.get("cuantia"),
            drive_link=meta_dict.get("drive_link"),
            drive_remote_path=meta_dict.get("drive_remote_path"),
            estado=meta_dict.get("estado", "instruccion"),
            sudespacho_expedientes=expedientes,
            creado_en=meta_dict.get("creado_en", ""),
            actualizado_en=now_iso(),
        )
        _write_case_index(caso_path(case_id), meta)

    return input_dir_name


def ensure_case(
    case_id: str,
    *,
    titulo: str | None = None,
    referencia_crm: str | None = None,
    cliente: str | None = None,
    contraparte: str | None = None,
    drive_link: str | None = None,
    drive_remote_path: str | None = None,
    cuantia: float | None = None,
    organo: str | None = None,
) -> Path:
    """Crea (o asegura) la estructura de un caso. Devuelve la ruta del caso."""
    case_dir = caso_path(case_id)
    case_dir.mkdir(parents=True, exist_ok=True)

    for sub in CASO_SUBDIRS:
        (case_dir / sub).mkdir(exist_ok=True)

    # Subcarpetas de intake dentro de 00_Input/ (niveles 2 y 3)
    for intake_sub in INPUT_SUBDIRS:
        (case_dir / "00_Input" / intake_sub).mkdir(exist_ok=True)
    for sub3 in WHATSAPP_SUBDIRS:
        (case_dir / "00_Input" / "02_Whatsapp" / sub3).mkdir(exist_ok=True)
    for sub3 in EMAIL_SUBDIRS:
        (case_dir / "00_Input" / "03_Email" / sub3).mkdir(exist_ok=True)

    index_path = case_dir / "00_Input" / "_caso.md"
    is_new = not index_path.exists()

    meta = CaseMeta(
        case_id=case_id,
        titulo=titulo or case_id,
        referencia_crm=referencia_crm,
        cliente=cliente,
        contraparte=contraparte,
        drive_link=drive_link,
        drive_remote_path=drive_remote_path,
        cuantia=cuantia,
        organo=organo,
        creado_en=now_iso() if is_new else "",
        actualizado_en=now_iso(),
    )

    if is_new:
        _write_case_index(case_dir, meta)

    return case_dir


def register_drive_ev(
    case_id: str,
    team_id: str,
    folder_id: str,
) -> None:
    """Registra los IDs del Drive E&V en el frontmatter de _caso.md.

    Almacena drive_ev_team_id y drive_ev_folder_id en el meta del índice.
    Idempotente: si los IDs ya coinciden, no hace nada.
    """
    import yaml as _yaml

    index = caso_path(case_id) / "00_Input" / "_caso.md"
    if not index.exists():
        return  # ensure_case no se llamó aún

    text = index.read_text(encoding="utf-8")
    if text.startswith("---"):
        _, fm_raw, _ = text.split("---", 2)
        fm = _yaml.safe_load(fm_raw) or {}
    else:
        fm = {}

    meta_dict = fm.get("meta") or {}

    # Idempotencia: si ya están los mismos IDs, no reescribir
    if (
        meta_dict.get("drive_ev_team_id") == team_id
        and meta_dict.get("drive_ev_folder_id") == folder_id
    ):
        return

    meta_dict["drive_ev_team_id"] = team_id
    meta_dict["drive_ev_folder_id"] = folder_id

    from dataclasses import fields as _dc_fields

    known = {f.name for f in _dc_fields(CaseMeta)}
    kwargs = {k: v for k, v in meta_dict.items() if k in known}
    kwargs.setdefault("case_id", case_id)
    kwargs.setdefault("titulo", case_id)
    kwargs["actualizado_en"] = now_iso()

    meta = CaseMeta(**kwargs)
    _write_case_index(caso_path(case_id), meta)


def get_drive_ev_ids(case_id: str) -> tuple[str | None, str | None]:
    """Devuelve ``(team_id, folder_id)`` del Drive E&V registrados en ``_caso.md``.

    Lee el frontmatter YAML del índice del caso. Devuelve ``(None, None)``
    si el caso no existe, no tiene índice o aún no tiene carpeta E&V vinculada.

    Args:
        case_id: Identificador del caso.

    Returns:
        Tupla ``(drive_ev_team_id, drive_ev_folder_id)``.
    """
    import yaml as _yaml

    index = caso_path(case_id) / "00_Input" / "_caso.md"
    if not index.exists():
        return None, None
    text = index.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None, None
    try:
        _, fm_raw, _ = text.split("---", 2)
        fm = _yaml.safe_load(fm_raw) or {}
    except Exception:
        return None, None
    meta = fm.get("meta") or {}
    return meta.get("drive_ev_team_id"), meta.get("drive_ev_folder_id")


def get_case_status(case_id: str) -> dict:
    """Comprueba el estado local del caso.

    Devuelve un dict con:
    - ``local_exists`` (bool): True si la carpeta existe en CASOS_ROOT.
    - ``expedientes`` (list[dict]): expedientes CRM registrados en ``_caso.md``
      (lista vacía si la carpeta no existe o el índice no tiene entradas).

    No lanza excepciones: en caso de error de lectura devuelve estado mínimo.
    """
    import yaml as _yaml

    case_dir = caso_path(case_id)
    local_exists = case_dir.exists()
    expedientes: list[dict] = []

    if local_exists:
        index = case_dir / "00_Input" / "_caso.md"
        if index.exists():
            try:
                text = index.read_text(encoding="utf-8")
                if text.startswith("---"):
                    _, fm_raw, _ = text.split("---", 2)
                    fm = _yaml.safe_load(fm_raw) or {}
                    expedientes = [
                        e for e in (fm.get("sudespacho_expedientes") or [])
                        if isinstance(e, dict)
                    ]
            except Exception:
                pass

    return {"local_exists": local_exists, "expedientes": expedientes}


def list_cases() -> list[str]:
    if not settings.casos_root.exists():
        return []
    return sorted(
        p.name for p in settings.casos_root.iterdir()
        if p.is_dir() and not p.name.startswith("_")
    )
