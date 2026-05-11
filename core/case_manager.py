"""Creación y registro de casos.

`ensure_case` es idempotente: si la carpeta existe, solo asegura que estén las
subcarpetas estándar. Nunca borra contenido del usuario.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import unicodedata
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any, Callable, Iterator

from .config import (
    CARPETA_ID_TO_PATH,
    CASO_SUBDIRS,
    CRM_FALLBACK_PATH,
    CRM_SUBDIR,
    CRM_TREE,
    EMAIL_SUBDIRS,
    INFORME_VIABILIDAD_TIPOS,
    INPUT_SUBDIRS,
    WHATSAPP_SUBDIRS,
    caso_path,
    settings,
)
from .utils import now_iso, read_md, write_md

logger = logging.getLogger(__name__)

# Plantillas de viabilidad (paso 7a). Generadas con
# `python -m scripts.render_plantillas all` desde los YAML canónicos en
# `data/_plantillas/`.
_PLANTILLAS_DIR = settings.project_root / "data" / "_plantillas"
_INFORME_TEMPLATE = _PLANTILLAS_DIR / "informe_viabilidad.xlsx"
_CUESTIONARIO_TEMPLATE = _PLANTILLAS_DIR / "cuestionario_viabilidad.xlsx"

# Caracteres prohibidos en nombres de fichero en Windows
_FORBIDDEN_FILENAME_CHARS = '/\\:*?"<>|'


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
    direccion: str | None = None         # v2: dirección del inmueble (refactor intake v2)
    id_go: str | None = None             # v2: ID GO de Engel & Völkers (p. ej. "BCN-OS-012905")
    tipo_caso: str | None = None         # v2 paso 7: clave de TIPOS_CASO_ALL (NEGATIVA_OFERTA, BAD_DEBT, …)
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
            drive_ev_team_id=meta_dict.get("drive_ev_team_id"),
            drive_ev_folder_id=meta_dict.get("drive_ev_folder_id"),
            direccion=meta_dict.get("direccion"),
            id_go=meta_dict.get("id_go"),
            tipo_caso=meta_dict.get("tipo_caso"),
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
    direccion: str | None = None,
    id_go: str | None = None,
    tipo_caso: str | None = None,
) -> Path:
    """Crea (o asegura) la estructura de un caso. Devuelve la ruta del caso.

    Idempotente. Nunca sobrescribe contenido del usuario.

    Refactor intake v2 — paso 7a (informe renombrado en sesión 7, 2026-05-11):
    - Crea todas las ramas de ``CRM_TREE`` bajo ``00_Input/05_CRM/`` (D1 eager).
    - Copia ``data/_plantillas/informe_viabilidad.xlsx`` a
      ``02_Analisis/<nombre>`` (siempre). El ``<nombre>`` lo decide
      ``_compose_informe_filename``: ``Informe viabilidad - <case_id>.xlsx``
      si el case_id sigue el formato CRM nuevo, ``_informe_viabilidad.xlsx``
      como fallback para casos legacy.
    - Si ``tipo_caso ∈ INFORME_VIABILIDAD_TIPOS`` copia además
      ``data/_plantillas/cuestionario_viabilidad.xlsx`` a
      ``02_Analisis/_cuestionario_viabilidad.xlsx``.
    - Pre-rellena REF (``<equipo> - <direccion> (<id_go>)``) y FECHA en el
      informe SOLO cuando se acaba de copiar — preserva trabajo del abogado
      en llamadas posteriores. REF se rellena solo si los tres componentes
      están disponibles (D-7a-2).
    - ``tipo_caso``, ``direccion`` e ``id_go`` se persisten en ``_caso.md``.
      Si el caso ya existe y el kwarg difiere del frontmatter, se actualiza
      vía ``_atomic_write_caso_md`` (D-7a-4).

    Args:
        case_id: Identificador del caso.
        tipo_caso: Clave de ``TIPOS_CASO_ALL``. Gobierna la copia condicional
            del cuestionario de viabilidad.
        direccion, id_go: Persisten en ``_caso.md.meta`` y se usan para
            componer REF del informe.
        (resto): metadatos del caso, opcionales.
    """
    case_dir = caso_path(case_id)
    case_dir.mkdir(parents=True, exist_ok=True)

    # Subcarpetas estándar (nivel 1)
    for sub in CASO_SUBDIRS:
        (case_dir / sub).mkdir(exist_ok=True)

    # Subcarpetas de intake (niveles 2 y 3)
    for intake_sub in INPUT_SUBDIRS:
        (case_dir / "00_Input" / intake_sub).mkdir(exist_ok=True)
    for sub3 in WHATSAPP_SUBDIRS:
        (case_dir / "00_Input" / "02_Whatsapp" / sub3).mkdir(exist_ok=True)
    for sub3 in EMAIL_SUBDIRS:
        (case_dir / "00_Input" / "03_Email" / sub3).mkdir(exist_ok=True)

    # Árbol CRM completo (D1 — eager, todas las ramas para todos los casos)
    _ensure_crm_tree_dirs(case_dir)

    index_path = case_dir / "00_Input" / "_caso.md"
    is_new = not index_path.exists()

    if is_new:
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
            direccion=direccion,
            id_go=id_go,
            tipo_caso=tipo_caso,
            creado_en=now_iso(),
            actualizado_en=now_iso(),
        )
        _write_case_index(case_dir, meta)
        tipo_caso_eff = tipo_caso
        direccion_eff = direccion
        id_go_eff = id_go
    else:
        # Caso existente: resolver valores efectivos vía coalesce kwarg → persisted.
        try:
            fm, _ = read_md(index_path)
            persisted = (fm.get("meta") or {}) if isinstance(fm, dict) else {}
        except Exception:
            persisted = {}

        tipo_caso_eff = tipo_caso if tipo_caso is not None else persisted.get("tipo_caso")
        direccion_eff = direccion if direccion is not None else persisted.get("direccion")
        id_go_eff = id_go if id_go is not None else persisted.get("id_go")

        # Reescribir frontmatter solo si algún kwarg explícito difiere del persistido (D-7a-4).
        needs_update = (
            (tipo_caso is not None and persisted.get("tipo_caso") != tipo_caso_eff)
            or (direccion is not None and persisted.get("direccion") != direccion_eff)
            or (id_go is not None and persisted.get("id_go") != id_go_eff)
        )
        if needs_update:
            def _mutate(fm_in: dict) -> dict:
                meta_in = fm_in.get("meta") or {}
                if tipo_caso is not None:
                    meta_in["tipo_caso"] = tipo_caso_eff
                if direccion is not None:
                    meta_in["direccion"] = direccion_eff
                if id_go is not None:
                    meta_in["id_go"] = id_go_eff
                fm_in["meta"] = meta_in
                return fm_in
            _atomic_write_caso_md(case_id, _mutate)

    # Copia idempotente de plantillas de viabilidad.
    # Nombre del informe: ``Informe viabilidad - <case_id>.xlsx`` si el
    # case_id sigue el formato CRM nuevo; ``_informe_viabilidad.xlsx`` si
    # no (fallback). Detalle en ``_compose_informe_filename``.
    analisis_dir = case_dir / "02_Analisis"
    informe_filename = _compose_informe_filename(case_id)
    informe_dest = analisis_dir / informe_filename
    informe_copiado = _copy_plantilla(_INFORME_TEMPLATE, informe_dest)

    if tipo_caso_eff in INFORME_VIABILIDAD_TIPOS:
        cuestionario_dest = analisis_dir / "_cuestionario_viabilidad.xlsx"
        _copy_plantilla(_CUESTIONARIO_TEMPLATE, cuestionario_dest)

    # Pre-rellenar SOLO si acabamos de copiar el informe — preserva trabajo previo.
    if informe_copiado:
        equipo = _parse_equipo_from_case_id(case_id)
        _prerellenar_informe(
            informe_dest,
            equipo=equipo,
            direccion=direccion_eff,
            id_go=id_go_eff,
        )

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


# ---------------------------------------------------------------------------
# Refactor intake v2 — helpers
# ---------------------------------------------------------------------------
#
# Estrategia y decisiones cerradas: project_intake_estructura_v2.md (memoria)
# + docs/INTEGRACION_SUDESPACHO.md §13.
#
# Casos antiguos (BaRR3, MaRS15) están congelados (D9): el sync v2 debe llamar
# a `is_legacy_intake_v1()` antes de operar y bloquear con mensaje claro.


def _normalize_label(s: str | None) -> str:
    """Normalización tolerante (M4-Q3).

    Lowercase, elimina acentos, strip. Útil para casar `id_carpeta_label`
    devuelto por `/api/element_registries/gdocu` con los nombres del árbol
    local (CRM_TREE) sin sensibilidad a capitalización ni acentos.
    """
    if not s:
        return ""
    nfkd = unicodedata.normalize("NFKD", s)
    ascii_s = nfkd.encode("ascii", "ignore").decode("ascii")
    return ascii_s.strip().lower()


def _walk_crm_tree(
    tree: dict[str, dict],
    prefix: str = "",
) -> Iterator[tuple[str, str]]:
    """Recorre CRM_TREE en DFS devolviendo (nombre_nodo, ruta_completa).

    Las rutas usan separador "/" (D11). Incluye nodos intermedios y hojas.
    """
    for name, children in tree.items():
        full = f"{prefix}/{name}" if prefix else name
        yield (name, full)
        if isinstance(children, dict) and children:
            yield from _walk_crm_tree(children, full)


def _find_branches_by_label(label: str) -> list[str]:
    """Devuelve todas las rutas del árbol cuyo nombre normalizado coincide.

    Recolecta todos los nodos (intermedios + hojas) cuyo nombre normalizado
    es igual al `label` normalizado. La heurística solo aplica si len == 1
    (ambigüedad → fallback).
    """
    target = _normalize_label(label)
    if not target:
        return []
    matches: list[str] = []
    for name, full_path in _walk_crm_tree(CRM_TREE):
        if _normalize_label(name) == target:
            matches.append(full_path)
    return matches


def crm_branch_path(
    case_id: str,
    *,
    id_carpeta: str | int | None = None,
    id_carpeta_label: str | None = None,
    expediente_id: str | int | None = None,
) -> tuple[Path, str]:
    """Resuelve la ruta destino dentro de ``00_Input/05_CRM/`` para un documento del CRM.

    Estrategia híbrida (M4 + M5; ver §13.4 de docs/INTEGRACION_SUDESPACHO.md):

    1. Lookup directo en ``CARPETA_ID_TO_PATH`` por ``id_carpeta``.
    2. Heurística por ``id_carpeta_label`` si la coincidencia en
       ``CRM_TREE`` es única (ambigüedad → fallback).
    3. Fallback ``05_CRM/99_Sin categoria/<expediente_id>/``. El caller debe
       escribir un evento ``category_unknown`` en ``_intake_log.jsonl`` (M10)
       cuando ``kind == "fallback"`` para descubrimiento progresivo de IDs.

    Args:
        case_id: ID del caso.
        id_carpeta: ID numérico devuelto por ``/api/element_registries/gdocu``
            (acepta string o int — se normaliza con ``str().strip()``).
        id_carpeta_label: label leaf-only del mismo endpoint (puede venir vacío).
        expediente_id: ID del expediente CRM, usado solo para el fallback.

    Returns:
        Tupla ``(path, kind)`` donde ``kind`` ∈ ``{"id_mapping",
        "label_heuristic", "fallback"}``. El path siempre está bajo
        ``<casos_root>/<case_id>/00_Input/05_CRM/``.
    """
    base = caso_path(case_id) / "00_Input" / CRM_SUBDIR

    # 1. Lookup directo por ID
    if id_carpeta is not None:
        key = str(id_carpeta).strip()
        if key in CARPETA_ID_TO_PATH:
            return base / CARPETA_ID_TO_PATH[key], "id_mapping"

    # 2. Heurística por label — solo si hay un único candidato
    if id_carpeta_label:
        candidates = _find_branches_by_label(id_carpeta_label)
        if len(candidates) == 1:
            return base / candidates[0], "label_heuristic"

    # 3. Fallback
    fallback = base / CRM_FALLBACK_PATH
    if expediente_id is not None:
        fallback = fallback / str(expediente_id)
    return fallback, "fallback"


def is_legacy_intake_v1(case_id: str) -> bool:
    """Detecta si el caso tiene estructura v1 de intake CRM (D9).

    Devuelve True si existe alguna subcarpeta ``00_Input/sudespacho_*/``.
    Casos v1 están congelados — el pull v2 debe bloquearse con mensaje claro
    en UI (BaRR3, MaRS15). Migración manual: borrar ``sudespacho_*/`` +
    ``force-pull`` v2.
    """
    input_dir = caso_path(case_id) / "00_Input"
    if not input_dir.exists():
        return False
    for child in input_dir.iterdir():
        if child.is_dir() and child.name.startswith("sudespacho_"):
            return True
    return False


def _atomic_write_caso_md(
    case_id: str,
    mutator: Callable[[dict], dict | None],
) -> Path:
    """Escritura atómica del frontmatter de _caso.md (D10).

    Lee ``fm + body``, aplica ``mutator(fm)`` y escribe a un archivo temporal
    dentro del mismo directorio; cierra la operación con ``os.replace``. Sin
    lock, sin versionado. La idempotencia es responsabilidad del mutator.

    Args:
        case_id: ID del caso. ``_caso.md`` debe existir.
        mutator: callable que recibe el frontmatter parseado (dict). Puede
            mutar in-place o devolver un dict nuevo; si devuelve ``None`` se
            asume mutación in-place.

    Returns:
        Path al archivo escrito.

    Raises:
        FileNotFoundError: si ``_caso.md`` no existe.
    """
    index = caso_path(case_id) / "00_Input" / "_caso.md"
    if not index.exists():
        raise FileNotFoundError(f"_caso.md no existe para el caso {case_id!r}")

    fm, body = read_md(index)
    new_fm = mutator(fm)
    if new_fm is not None:
        fm = new_fm

    # Stamp de actualización en meta — consistente con register_expediente y
    # register_drive_ev. No tocamos meta si el mutator no la creó.
    if isinstance(fm.get("meta"), dict):
        fm["meta"]["actualizado_en"] = now_iso()

    # Temp en el mismo directorio para que os.replace sea atómico (Windows + POSIX).
    # PID en el nombre evita colisiones si hubiera procesos concurrentes.
    tmp_path = index.parent / f"._caso.{os.getpid()}.tmp"
    try:
        write_md(tmp_path, fm, body)
        os.replace(tmp_path, index)
    except Exception:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise
    return index


def _find_expediente_entry(
    expedientes: list[Any],
    expediente_id: str | int,
) -> tuple[int, dict | None]:
    """Localiza un entry de expediente por ID dentro de la lista del frontmatter.

    Devuelve ``(idx, entry)`` o ``(-1, None)`` si no existe.
    """
    target = str(expediente_id)
    for idx, e in enumerate(expedientes):
        if isinstance(e, dict) and str(e.get("id")) == target:
            return idx, e
    return -1, None


def read_pull_state(
    case_id: str,
    expediente_id: str | int,
) -> dict | None:
    """Devuelve el estado del pull para un expediente concreto (M3 / D8).

    Lee ``sudespacho_expedientes`` del frontmatter de ``_caso.md`` y busca el
    entry cuyo ``id`` coincide con ``expediente_id``. Devuelve ``None`` si el
    caso no existe, no tiene índice, o el expediente no está vinculado.

    Schema D8 del entry: ``{id, element, linked_at, last_sync,
    documents_total_crm, doc_ids, by_carpeta, errors}``.
    """
    index = caso_path(case_id) / "00_Input" / "_caso.md"
    if not index.exists():
        return None
    try:
        fm, _ = read_md(index)
    except Exception:
        return None
    expedientes = fm.get("sudespacho_expedientes") or []
    _, entry = _find_expediente_entry(expedientes, expediente_id)
    return entry


def update_pull_state(
    case_id: str,
    expediente_id: str | int,
    *,
    element: str | None = None,
    last_sync: str | None = None,
    documents_total_crm: int | None = None,
    doc_ids: list[Any] | None = None,
    by_carpeta: dict[str, Any] | None = None,
    errors: list[Any] | None = None,
) -> dict:
    """Crea o actualiza el entry de pull state para un expediente (M3 / D8).

    Schema D8 del entry: ``{id, element, linked_at, last_sync,
    documents_total_crm, doc_ids, by_carpeta, errors}``.

    Semántica:
    - ``linked_at`` se fija en la primera escritura y no se sobrescribe.
    - Cualquier kwarg con valor ``None`` se ignora (campo se conserva).
    - ``errors`` sobrescribe (D12: el state es estado actual; el histórico
      forense vive en ``_intake_log.jsonl`` vía M10).
    - ``element`` es obligatorio al crear el entry. Si se proporciona en una
      actualización, sobrescribe el valor existente.

    Args:
        case_id: ID del caso. ``_caso.md`` debe existir.
        expediente_id: ID numérico del expediente CRM (string o int).
        element: ``"expedientes_judiciales"`` | ``"extrajudiciales"``.
        last_sync: timestamp ISO-8601 del último pull.
        documents_total_crm: total de documentos vistos en el CRM
            (puede superar a ``len(doc_ids)`` por dedup M9).
        doc_ids: IDs numéricos de los documentos descargados.
        by_carpeta: dict ``{ruta_local_canónica: count}`` (D11). Los counts
            incluyen aliases del manifest M9.
        errors: lista de errores del último pull. Sobrescribe el campo.

    Returns:
        El entry final tras la actualización.

    Raises:
        FileNotFoundError: si ``_caso.md`` no existe.
        ValueError: si el entry es nuevo y no se proporciona ``element``.
    """
    target_id = str(expediente_id)
    captured: dict[str, Any] = {}

    def _mutate(fm: dict) -> dict:
        expedientes = fm.get("sudespacho_expedientes")
        if not isinstance(expedientes, list):
            expedientes = []
            fm["sudespacho_expedientes"] = expedientes

        idx, entry = _find_expediente_entry(expedientes, target_id)
        is_new = entry is None
        if entry is None:
            entry = {"id": target_id}

        if is_new:
            if not element:
                raise ValueError(
                    f"element requerido al vincular un expediente nuevo "
                    f"(case={case_id!r}, expediente={target_id!r})"
                )
            entry["element"] = element
            entry["linked_at"] = now_iso()
            entry.setdefault("doc_ids", [])
            entry.setdefault("by_carpeta", {})
            entry.setdefault("errors", [])
        elif element is not None and entry.get("element") != element:
            entry["element"] = element

        if last_sync is not None:
            entry["last_sync"] = last_sync
        if documents_total_crm is not None:
            entry["documents_total_crm"] = documents_total_crm
        if doc_ids is not None:
            entry["doc_ids"] = list(doc_ids)
        if by_carpeta is not None:
            entry["by_carpeta"] = dict(by_carpeta)
        if errors is not None:
            entry["errors"] = list(errors)

        if is_new:
            expedientes.append(entry)
        else:
            expedientes[idx] = entry

        captured["entry"] = entry
        return fm

    _atomic_write_caso_md(case_id, _mutate)
    return captured["entry"]


# ---------------------------------------------------------------------------
# Refactor intake v2 — paso 7a: scaffolding del caso (CRM_TREE + plantillas)
# ---------------------------------------------------------------------------
#
# Helpers privados que dan soporte a `ensure_case` v2. Decisiones D-7a-1 a
# D-7a-7 cerradas con el usuario en sesión 2026-05-11.


# Coincide con el prefijo de equipo del case_id nuevo:
# `BaRR3 - Dirección (W-XXXXXX) - Tipo` → "BaRR3".
_EQUIPO_RE = re.compile(r"^[A-Z][a-zA-Z][A-Z]{2}\d+$")


def _parse_equipo_from_case_id(case_id: str) -> str | None:
    """Extrae el token de equipo del case_id si sigue el formato CRM nuevo.

    Devuelve ``None`` si el case_id usa el formato heredado (``EV-2026-001``)
    o si el primer token no encaja con el patrón de equipo (dos letras +
    dos letras + dígitos, p. ej. ``BaRR3``, ``MaRS15``).
    """
    if not case_id:
        return None
    token = case_id.split(" - ", 1)[0].strip()
    return token if _EQUIPO_RE.match(token) else None


def _sanitize_filename_segment(s: str) -> str:
    """Sustituye los caracteres prohibidos en nombres de fichero Windows.

    Reemplaza ``/ \\ : * ? " < > |`` por espacios. No toca acentos ni
    caracteres válidos del case_id (`(`, `)`, `,`, `º`, etc.).
    """
    for ch in _FORBIDDEN_FILENAME_CHARS:
        s = s.replace(ch, " ")
    return s.strip()


def _compose_informe_filename(case_id: str) -> str:
    """Compone el nombre del fichero del informe de viabilidad.

    Política (decisión del usuario, sesión 7 del 2026-05-11):

    - Si ``case_id`` sigue el formato CRM nuevo (``<equipo> - <dirección>
      (<id_go>) - <sufijo>``, detectado por ``_parse_equipo_from_case_id``):
      ``"Informe viabilidad - <case_id>.xlsx"``. El case_id ya contiene
      equipo + dirección + ID GO + tipo, por lo que sirve como sufijo
      directo del nombre.
    - Si ``case_id`` no sigue el formato nuevo (legacy ``EV-2026-001``):
      ``"_informe_viabilidad.xlsx"`` (fallback con underscore inicial).
      Mantiene ordenación arriba en el explorador y evita nombres
      truncados con datos vacíos.

    El nombre se sanea de caracteres prohibidos en Windows (``/ \\ : * ?
    " < > |``) por defensa, aunque en la práctica el case_id no debería
    contenerlos.
    """
    if _parse_equipo_from_case_id(case_id) is None:
        return "_informe_viabilidad.xlsx"
    sanitized = _sanitize_filename_segment(case_id)
    return f"Informe viabilidad - {sanitized}.xlsx"


def _ensure_crm_tree_dirs(case_dir: Path) -> None:
    """Crea todas las ramas de ``CRM_TREE`` bajo ``00_Input/05_CRM/`` (D1 eager).

    Recorrido recursivo (``_walk_crm_tree``); ``mkdir(exist_ok=True)`` en
    cada nodo. Coste trivial; la uniformidad simplifica el downstream
    (pull, anonimizador, UI).
    """
    base = case_dir / "00_Input" / CRM_SUBDIR
    base.mkdir(parents=True, exist_ok=True)
    for _name, full_path in _walk_crm_tree(CRM_TREE):
        (base / full_path).mkdir(parents=True, exist_ok=True)


def _copy_plantilla(origen: Path, destino: Path) -> bool:
    """Copia una plantilla al destino con idempotencia estricta.

    - Si ``destino`` ya existe → NO sobrescribe (preserva trabajo del
      abogado) y devuelve ``False``.
    - Si ``origen`` no existe → log warning y devuelve ``False`` (no
      aborta ensure_case; podría faltar tras un checkout parcial o un
      mount intermitente de la unidad de red).
    - En otro caso, copia con ``shutil.copy2`` (preserva metadatos) y
      devuelve ``True``.
    """
    if destino.exists():
        return False
    if not origen.exists():
        logger.warning("Plantilla no encontrada, se omite copia: %s", origen)
        return False
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(origen, destino)
    return True


def _find_label_row(
    ws: Any,
    label: str,
    *,
    column: int = 2,
    max_rows: int = 200,
) -> int | None:
    """Localiza la primera fila cuya celda en ``column`` matchea ``label``.

    Las celdas concretas donde el render escribe REF/FECHA no son
    estables (dependen del orden de los bloques en el YAML). Localizar
    por etiqueta es resistente a cambios futuros del template.
    """
    for row in range(1, max_rows + 1):
        value = ws.cell(row=row, column=column).value
        if value is not None and str(value).strip() == label:
            return row
    return None


def _prerellenar_informe(
    informe_path: Path,
    *,
    equipo: str | None,
    direccion: str | None,
    id_go: str | None,
) -> None:
    """Pre-rellena REF y FECHA en el informe de viabilidad recién copiado.

    Localiza ``REF`` y ``FECHA`` en columna B de la hoja ``OPERACION`` y
    escribe el valor en la columna C de la misma fila. REF se rellena
    SOLO si los tres componentes están presentes (D-7a-2) — sin
    placeholders. FECHA siempre se rellena con la fecha actual.

    Silencioso ante errores de openpyxl: un informe corrupto no debe
    abortar la creación del caso.
    """
    try:
        from openpyxl import load_workbook
    except ImportError:
        logger.warning("openpyxl no disponible; se omite pre-relleno del informe")
        return

    try:
        wb = load_workbook(informe_path)
    except Exception as exc:
        logger.warning("No se pudo abrir informe para pre-relleno (%s): %s", informe_path, exc)
        return

    if "OPERACION" not in wb.sheetnames:
        logger.warning("Hoja 'OPERACION' no encontrada en %s", informe_path)
        return
    ws = wb["OPERACION"]

    ref_row = _find_label_row(ws, "REF")
    if ref_row is not None and equipo and direccion and id_go:
        ws.cell(row=ref_row, column=3, value=f"{equipo} - {direccion} ({id_go})")

    fecha_row = _find_label_row(ws, "FECHA")
    if fecha_row is not None:
        cell = ws.cell(row=fecha_row, column=3, value=date.today())
        cell.number_format = "dd/mm/yyyy"

    try:
        wb.save(informe_path)
    except Exception as exc:
        logger.warning("No se pudo guardar informe tras pre-relleno (%s): %s", informe_path, exc)
