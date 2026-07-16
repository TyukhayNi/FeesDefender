"""Operaciones de lectura/navegación con tiers y guardas Stream-aware."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from . import fsops
from .guards import check_gdoc, guard_file
from .tiers import Tier, Zonas, check_read, classify

_READ_MAX = int(os.environ.get("XL_READ_MAX_BYTES", "5000000"))


def _abrir(allowed, zonas, oracle, path: str) -> Path:
    p = fsops.resolve_within(allowed, path)
    check_read(zonas, p)
    check_gdoc(p)
    guard_file(oracle, p)
    return p


def read_text(allowed, zonas, oracle, path: str,
              head: int | None = None, tail: int | None = None) -> str:
    p = _abrir(allowed, zonas, oracle, path)
    with open(p, "r", encoding="utf-8", errors="replace") as fh:
        texto = fh.read(_READ_MAX)
    if head is not None:
        return "".join(texto.splitlines(keepends=True)[:head])
    if tail is not None:
        return "".join(texto.splitlines(keepends=True)[-tail:])
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
