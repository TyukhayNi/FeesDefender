"""Operaciones de lectura/navegación con tiers y guardas Stream-aware."""
from __future__ import annotations

import os
import re as _re
import subprocess
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path

from . import audit, fsops
from .fsops import OutsideSandbox
from .guards import check_gdoc, guard_file, FileNotHydrated, GDocBloqueado
from .tiers import Tier, Zonas, check_read, classify
from .winio import long_path

_LONG_PATH_UMBRAL = 248


def _read_max() -> int:
    """Tope de lectura, leído por llamada (respeta monkeypatch.setenv)."""
    return int(os.environ.get("XL_READ_MAX_BYTES", "5000000"))


def _abrible(p: Path) -> str:
    r"""Ruta apta para open(): prefijo \\?\ solo cuando roza MAX_PATH."""
    s = str(p)
    return long_path(p) if len(s) >= _LONG_PATH_UMBRAL else s


def _abrir(allowed, zonas, oracle, path: str) -> Path:
    p = fsops.resolve_within(allowed, path)
    check_read(zonas, p)
    check_gdoc(p)
    guard_file(oracle, p)
    return p


def read_text(allowed, zonas, oracle, path: str,
              head: int | None = None, tail: int | None = None) -> str:
    """Lee texto UTF-8 (errors="replace") con tope XL_READ_MAX_BYTES.

    `head`/`tail` en líneas; 0 o negativo devuelve "". `tail` lee el FINAL
    real del fichero (seek desde el final, no el prefijo del cap); si el seek
    cae en mitad de una línea, esa primera línea parcial se descarta de forma
    natural al quedarse con las últimas N. Una lectura completa que supere el
    cap termina con una línea marcadora [TRUNCADO: ...] — sin silencios.
    """
    p = _abrir(allowed, zonas, oracle, path)
    if head is not None and head <= 0:
        return ""
    if tail is not None and tail <= 0:
        return ""
    cap = _read_max()
    if tail is not None:
        size = p.stat().st_size
        with open(_abrible(p), "rb") as fh:
            fh.seek(max(0, size - cap))
            data = fh.read()
        lineas = data.decode("utf-8", errors="replace").splitlines(keepends=True)
        return "".join(lineas[-tail:])
    with open(_abrible(p), "r", encoding="utf-8", errors="replace") as fh:
        texto = fh.read(cap)
        truncado = bool(fh.read(1))
    if head is not None:
        return "".join(texto.splitlines(keepends=True)[:head])
    if truncado:
        mostrados = len(texto.encode("utf-8", errors="replace"))
        texto += (f"\n[TRUNCADO: mostrados {mostrados} de {p.stat().st_size} bytes"
                  " — usa head/tail o sube XL_READ_MAX_BYTES]")
    return texto


def read_multiple(allowed, zonas, oracle, paths: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in paths:
        try:
            out[path] = read_text(allowed, zonas, oracle, path)
        except Exception as e:  # aislar: un fallo no tumba el lote
            out[path] = f"ERROR: {e}"
    return out


def get_metadata(allowed, zonas, oracle, path: str) -> dict:
    p = fsops.resolve_within(allowed, path)
    check_read(zonas, p)
    st = p.stat()
    return {
        "name": p.name,
        "size": st.st_size,
        "mtime": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(timespec="seconds"),
        "is_dir": p.is_dir(),
        "tier": int(classify(zonas, p)),
        "hydration": oracle.status(p) if not p.is_dir() else None,
    }


def list_dir(allowed, zonas, path: str, sizes: bool = False,
             max_entries: int = 500) -> list[dict]:
    p = fsops.resolve_within(allowed, path)
    check_read(zonas, p)
    out: list[dict] = []
    podados = 0
    for hijo in sorted(p.iterdir()):
        if classify(zonas, hijo) is Tier.PROHIBIDA:
            podados += 1
            continue
        if len(out) >= max_entries:
            out.append({"_truncado": True})
            break
        e: dict = {"name": hijo.name, "is_dir": hijo.is_dir()}
        if sizes and not hijo.is_dir():
            try:
                e["size"] = hijo.stat().st_size
            except OSError:
                e["size"] = None
        out.append(e)
    if podados:
        out.append({"_podados": podados})
    return out


def iter_tree(zonas: Zonas, root: Path, on_prune=None):
    """Generador de ficheros en árbol con poda Tier 0 topdown."""
    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        base = Path(dirpath)
        vivos = []
        for d in dirnames:
            if classify(zonas, base / d) is Tier.PROHIBIDA:
                if on_prune:
                    on_prune(base / d)
            else:
                vivos.append(d)
        dirnames[:] = vivos
        for f in filenames:
            yield base / f


def tree(allowed, zonas, path: str, max_depth: int = 8, max_entries: int = 2000) -> dict:
    """Árbol de ficheros relativo con poda Tier 0, limit profundidad y entradas.

    Retorna dict con claves:
    - entries: lista de rutas relativas (POSIX)
    - podados: número de directorios Tier 0 excluidos
    - truncado: True si se alcanzó max_entries
    - omitidos_profundidad: ficheros omitidos por superar max_depth (sin silencios)
    """
    p = fsops.resolve_within(allowed, path)
    check_read(zonas, p)
    entries: list[str] = []
    podados = 0
    omitidos_profundidad = 0
    truncado = False

    def _poda(_ruta):
        nonlocal podados
        podados += 1

    for f in iter_tree(zonas, p, on_prune=_poda):
        rel = f.relative_to(p)
        if len(rel.parts) > max_depth:
            omitidos_profundidad += 1
            continue
        if len(entries) >= max_entries:
            truncado = True
            break
        entries.append(rel.as_posix())
    return {"entries": entries, "podados": podados, "truncado": truncado,
            "omitidos_profundidad": omitidos_profundidad}


def search_name(allowed, zonas, path: str, patron: str, max_results: int = 200) -> list[str]:
    """Búsqueda por nombre de fichero (fnmatch case-insensitive) con poda Tier 0.

    Patrón: e.g. "*.txt", "doc_*" — case-insensitive.
    Retorna lista de rutas absolutas hasta max_results.
    """
    p = fsops.resolve_within(allowed, path)
    check_read(zonas, p)
    hits: list[str] = []
    for f in iter_tree(zonas, p):
        if fnmatch(f.name.lower(), patron.lower()):
            hits.append(str(f))
            if len(hits) >= max_results:
                break
    return hits


def search_content(allowed, zonas, oracle, path: str, consulta: str,
                   regex: bool = False, max_results: int = 200) -> dict:
    """Búsqueda de contenido grep con poda Tier 0, guardas hidratación y omisión COLD.

    Salta binarios (byte nulo en los primeros 8 KB) y ficheros .g*;
    los COLD/UNKNOWN por encima del umbral de fichero se OMITEN y se listan
    (sin silencios); los HOT se leen con errors="replace".

    Retorna dict:
    - matches: lista de {"path": str, "line": int, "text": str}
    - omitidos_cold: lista de rutas COLD/UNKNOWN omitidas (sin silencios)
    - podados: número de ficheros/dirs Tier 0 podados
    """
    p = fsops.resolve_within(allowed, path)
    check_read(zonas, p)
    patron = None
    if regex:
        try:
            patron = _re.compile(consulta)
        except _re.error as e:
            raise ValueError(f"regex inválida: {e}") from e
    matches: list[dict] = []
    omitidos: list[str] = []
    podados = 0

    def _poda(_r):
        nonlocal podados
        podados += 1

    for f in iter_tree(zonas, p, on_prune=_poda):
        if len(matches) >= max_results:
            break
        try:
            check_gdoc(f)
            guard_file(oracle, f)
        except GDocBloqueado:
            continue
        except FileNotHydrated:
            omitidos.append(str(f))
            continue
        try:
            # Detectar binarios: byte nulo en los primeros 8 KB
            with open(_abrible(f), "rb") as fh:
                if b"\x00" in fh.read(8192):
                    continue
            # Leer y buscar en contenido
            with open(_abrible(f), "r", encoding="utf-8", errors="replace") as fh:
                for n, linea in enumerate(fh, 1):
                    hit = patron.search(linea) if patron else (consulta in linea)
                    if hit:
                        matches.append({"path": str(f), "line": n,
                                        "text": linea.rstrip("\n")[:300]})
                        if len(matches) >= max_results:
                            break
        except OSError:
            continue
    return {"matches": matches, "omitidos_cold": omitidos, "podados": podados}


def _resolver_lnk_com(path: str) -> str:
    r"""Resuelve el TargetPath de un `.lnk` vía PowerShell COM (WScript.Shell).

    La ruta se pasa por variable de entorno (`$env:XL_LNK_PATH`) y NUNCA se
    interpola en el texto del comando: un `.lnk` es contenido de un tercero y su
    nombre podría contener metacaracteres/comillas de PowerShell (inyección de
    comandos, aguas arriba de las guardas de sandbox). Cualquier fallo del
    subproceso (timeout, OSError) se absorbe devolviendo "" (fail-closed).
    """
    ps = "(New-Object -ComObject WScript.Shell).CreateShortcut($env:XL_LNK_PATH).TargetPath"
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            env={**os.environ, "XL_LNK_PATH": str(path)},
            capture_output=True, encoding="utf-8", errors="replace", timeout=15)
    except (subprocess.TimeoutExpired, OSError):
        return ""
    return (r.stdout or "").strip()


def resolve_shortcut(allowed, zonas, path: str, _resolver_lnk=_resolver_lnk_com) -> dict:
    """Resuelve un `.lnk` y RE-VALIDA su destino contra sandbox y tiers.

    El destino de un atajo es contenido controlable por un tercero: nunca se
    confía en él sin pasar de nuevo por `resolve_within`/`classify`. Si cae
    fuera del sandbox o en Tier 0 (90_Notas personales), se devuelve
    `target=None` (Tier 0 nunca se filtra al modelo) y se registra en auditoría.
    Fail-closed: si el resolver lanza o devuelve vacío, se audita
    `resolucion_fallida` y se devuelve la forma None (ninguna excepción escapa).
    """
    p = fsops.resolve_within(allowed, path)
    check_read(zonas, p)
    try:
        target = _resolver_lnk(str(p))
    except Exception:
        audit.log_op("resolve_shortcut", str(p), "resolucion_fallida")
        return {"target": None, "dentro_sandbox": False, "tier": None}
    if not target:
        audit.log_op("resolve_shortcut", str(p), "resolucion_fallida")
        return {"target": None, "dentro_sandbox": False, "tier": None}
    try:
        t = fsops.resolve_within(allowed, target)
    except OutsideSandbox:
        audit.log_op("resolve_shortcut", str(p), "escape_bloqueado", motivo=target[:120])
        return {"target": None, "dentro_sandbox": False, "tier": None}
    tier = classify(zonas, t)
    if tier is Tier.PROHIBIDA:
        audit.log_op("resolve_shortcut", str(p), "tier0_bloqueado")
        return {"target": None, "dentro_sandbox": False, "tier": None}
    return {"target": str(t), "dentro_sandbox": True, "tier": int(tier)}
