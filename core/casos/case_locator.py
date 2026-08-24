"""Localización de expedientes con tolerancia a layout flat y por ciudades.

Única puerta de entrada para resolver rutas de expedientes. Tolera dos layouts:

- **Flat (legacy):** ``CASOS_ROOT/<case_id>/``
- **Por ciudades:** ``CASOS_ROOT/<Ciudad>/<case_id>/``

Plan: ``docs/superpowers/plans/PLAN_SUBDIVISION_CIUDADES.md`` (Fase 1).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator

from core.ciudades import CIUDADES, es_carpeta_de_sistema

_FALLBACK_CITY = "_Sin clasificar"
_CITY_NAMES: frozenset[str] = frozenset(CIUDADES) | {_FALLBACK_CITY}


def _root() -> Path:
    from core.config import settings
    return settings.casos_root


def path_for(case_id: str) -> Path:
    """Devuelve la ruta a un expediente, buscando en flat y luego por ciudades.

    Si el expediente no existe en ninguna ubicación, devuelve la ruta flat
    (compatible con creación de casos nuevos).
    """
    root = _root()
    flat = root / case_id
    if flat.is_dir():
        return flat
    for city in sorted(CIUDADES):
        candidate = root / city / case_id
        if candidate.is_dir():
            return candidate
    candidate = root / _FALLBACK_CITY / case_id
    if candidate.is_dir():
        return candidate
    return flat


# ---------------------------------------------------------------------------
# Las TRES intenciones (Fase 1, Task 6) — R7/H7-01
# ---------------------------------------------------------------------------
#
# `path_for` servia a tres preguntas distintas con una sola respuesta, y por eso
# no habia forma de arreglarlo con un booleano: `strict=True` rompe el alta,
# `strict=False` conserva el expediente fantasma. Las preguntas son:
#
#   - «damelo, que tiene que estar»      -> localizar(): LANZA si falta
#   - «esta?»                            -> buscar(): devuelve None
#   - «donde lo creo»                    -> destino_de_alta(): faltar es lo normal
#
# Separarlas por NOMBRE es lo que las hace auditables: un `grep` dice quien
# espera que el caso exista y quien no, cosa que un flag no permite.


_RE_W_CODE = re.compile(r"\((W-[A-Za-z0-9]+)\)")


def _w_code_de(case_id: str) -> str | None:
    """El W-code del `case_id`, o `None`. **Nunca el `case_id` entero.**

    El error tiene que decir DE QUE caso habla, o deja de ser diagnosticable —y eso
    lo pedia un test que ya existia (`test_pull_falla_si_caso_no_existe`). Pero un
    `case_id` es `BaXXX - <direccion> - (W-XXXXX) - <tipo>`: lleva la direccion del
    inmueble dentro, o sea PII, y el §16 prohibe que aparezca en un mensaje. Se
    extrae solo el W-code, que identifica sin exponer.

    Si no hay W-code el error no lleva identificador: preferible a filtrar una
    cadena arbitraria. Los casos reales siempre lo llevan, por convencion de nombre.
    """
    m = _RE_W_CODE.search(case_id or "")
    return m.group(1) if m else None


def localizar(case_id: str) -> Path:
    """La ruta de un caso que **debe** existir. Lanza `LocalWorkspaceMissing` si no.

    Es la puerta de todo lector y de todo escritor de un caso ya abierto. No crea
    nada, ni siquiera al fallar.
    """
    encontrada = buscar(case_id)
    if encontrada is None:
        from .workspace_model import LocalWorkspaceMissing
        raise LocalWorkspaceMissing(
            w_code=_w_code_de(case_id),
            detalle="el caso no existe en ningun layout del catalogo")
    return encontrada


def buscar(case_id: str) -> Path | None:
    """La ruta del caso, o `None` si no existe. **No lanza y no crea nada.**

    Existe por los detectores de ausencia: los que preguntan si el caso esta y
    siguen por otra rama si no. Sin ella, migrarlos a `localizar()` cambiaria un
    error legible por una traza sin salida.

    Y hace explicita una pregunta que hoy se confunde con otra: con el fallback,
    «el caso no existe» y «el fichero que buscaba dentro del caso no existe» dan
    el mismo `False`.
    """
    root = _root()
    flat = root / case_id
    if flat.is_dir():
        return flat
    for city in sorted(CIUDADES):
        candidate = root / city / case_id
        if candidate.is_dir():
            return candidate
    candidate = root / _FALLBACK_CITY / case_id
    if candidate.is_dir():
        return candidate
    return None


def destino_de_alta(case_id: str) -> Path:
    """Donde se materializa un caso. Que no exista es su caso NORMAL.

    **Nombrar no es crear:** devuelve la ruta y no toca el disco. Crear es del
    llamador (`case_manager.ensure_case`), que es el unico que debe usar esto.

    Si el caso YA existe devuelve **su** ubicacion, no la ruta flat. Esa regla no
    es cosmetica: devolver siempre la flat haria que un alta sobre un caso que ya
    vive en su ciudad creara un duplicado plano al lado — el defecto CRITICO que
    R6 encontro en el `--force` del `--modo v1`, una carpeta sombra con el W-code
    duplicado.
    """
    return buscar(case_id) or (_root() / case_id)


def _id_go_of(case_dir: Path) -> str | None:
    """Lee ``meta.id_go`` (el W-code) del ``_caso.md`` de un caso, o ``None``."""
    import yaml

    caso_md = case_dir / "00_Input" / "_caso.md"
    if not caso_md.is_file():
        return None
    try:
        text = caso_md.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        fm = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return None
    meta = fm.get("meta") if isinstance(fm, dict) else None
    if isinstance(meta, dict) and meta.get("id_go"):
        return str(meta["id_go"]).strip()
    return None


def read_case_meta(case_dir: Path) -> dict:
    """Lee el dict ``meta`` del frontmatter de ``00_Input/_caso.md``.

    Devuelve ``{}`` si el fichero no existe, no tiene frontmatter válido, o el
    YAML está corrupto. No lanza (mismo criterio tolerante que ``_id_go_of``).
    """
    import yaml

    caso_md = case_dir / "00_Input" / "_caso.md"
    if not caso_md.is_file():
        return {}
    try:
        text = caso_md.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    try:
        fm = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return {}
    meta = fm.get("meta") if isinstance(fm, dict) else None
    return meta if isinstance(meta, dict) else {}


def resolve_ref(ref: str) -> str:
    """Resuelve una referencia al ``case_id`` canónico (nombre de la carpeta).

    Acepta el ``case_id`` exacto (nombre de carpeta) o el **W-code** (``meta.id_go``
    del ``_caso.md``). Si hay un caso cuyo nombre coincide con ``ref``, lo devuelve;
    si no, busca un caso cuyo ``id_go`` sea ``ref`` y devuelve su nombre canónico. Si
    no encuentra nada, devuelve ``ref`` tal cual (creación de casos nuevos / fallback).
    """
    ref = (ref or "").strip()
    if not ref:
        return ref
    cases = list(list_cases())
    # Coincidencia exacta por nombre, pero solo si es un caso REAL (tiene _caso.md):
    # así una carpeta fantasma (creada por error, sin _caso.md) no eclipsa al caso real.
    for case_dir in cases:
        if case_dir.name == ref and (case_dir / "00_Input" / "_caso.md").is_file():
            return ref
    # W-code (meta.id_go) → nombre de carpeta canónico.
    for case_dir in cases:
        if _id_go_of(case_dir) == ref:
            return case_dir.name
    return ref


def path_for_ciudad(case_id: str, ciudad: str) -> Path:
    """Calcula la ruta esperada de un expediente en una ciudad concreta.

    No comprueba existencia — uso principal: creación de casos nuevos
    y migración.
    """
    return _root() / ciudad / case_id


def move_to_city(
    case_id: str,
    ciudad_destino: str,
    motivo: str,
    usuario: str,
) -> Path:
    """Mueve un expediente a una carpeta de ciudad.

    Ejecuta atómicamente:
    1. Mover carpeta.
    2. Actualizar metadato ``ciudad`` en ``_caso.md``.
    3. Escribir audit log.

    Si falla el paso 2 o 3, revierte el movimiento de carpeta.

    Raises:
        ValueError: motivo menor de 10 caracteres.
        FileNotFoundError: caso no encontrado.
    """
    import shutil

    if len((motivo or "").strip()) < 10:
        raise ValueError("El motivo debe tener al menos 10 caracteres.")

    src = path_for(case_id)
    if not src.is_dir():
        raise FileNotFoundError(f"Caso '{case_id}' no encontrado.")

    dest = path_for_ciudad(case_id, ciudad_destino)
    if src == dest:
        return dest

    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dest))

    try:
        _update_ciudad_metadata(dest, ciudad_destino)
        append_audit_log({
            "operacion": "reasignar_ciudad",
            "case_id": case_id,
            "ciudad_origen": src.parent.name if src.parent != _root() else "(raíz)",
            "ciudad_destino": ciudad_destino,
            "motivo": motivo.strip(),
            "usuario": usuario,
        })
    except Exception:
        shutil.move(str(dest), str(src))
        raise

    return dest


def _update_ciudad_metadata(case_dir: Path, ciudad: str) -> None:
    """Actualiza el campo ``ciudad`` en el frontmatter de ``_caso.md``."""
    import yaml

    index = case_dir / "00_Input" / "_caso.md"
    if not index.exists():
        return
    text = index.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return
    parts = text.split("---", 2)
    if len(parts) < 3:
        return
    fm = yaml.safe_load(parts[1]) or {}
    fm["ciudad"] = ciudad
    meta = fm.get("meta")
    if isinstance(meta, dict):
        meta["ciudad"] = ciudad
    new_text = "---\n" + yaml.dump(fm, allow_unicode=True, default_flow_style=False) + "---" + parts[2]
    index.write_text(new_text, encoding="utf-8")


def list_cases(ciudad: str | None = None) -> Iterator[Path]:
    """Itera directorios de expedientes.

    Sin argumento: devuelve todos (flat + por ciudades).
    Con ``ciudad``: solo los de esa ciudad.
    """
    root = _root()
    if not root.is_dir():
        return
    if ciudad is not None:
        city_dir = root / ciudad
        if city_dir.is_dir():
            yield from sorted(
                (p for p in city_dir.iterdir() if p.is_dir()),
                key=lambda p: p.name,
            )
        return

    seen: set[str] = set()
    for p in sorted(root.iterdir(), key=lambda p: p.name):
        if not p.is_dir():
            continue
        if es_carpeta_de_sistema(p.name):
            continue
        if p.name in _CITY_NAMES:
            for child in sorted(p.iterdir(), key=lambda c: c.name):
                if child.is_dir() and child.name not in seen:
                    seen.add(child.name)
                    yield child
        else:
            if p.name not in seen:
                seen.add(p.name)
                yield p


def all_cities_present() -> list[str]:
    """Devuelve las ciudades que tienen al menos un expediente."""
    root = _root()
    result: list[str] = []
    for city in sorted(_CITY_NAMES):
        city_dir = root / city
        if city_dir.is_dir() and any(c.is_dir() for c in city_dir.iterdir()):
            result.append(city)
    return result


def append_audit_log(entry: dict) -> None:
    """Añade una entrada JSONL al log de auditoría ``_audit/relocations.jsonl``."""
    import json
    from datetime import datetime, timezone

    audit_dir = _root() / "_audit"
    audit_dir.mkdir(exist_ok=True)
    log_path = audit_dir / "relocations.jsonl"
    entry.setdefault("ts", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
