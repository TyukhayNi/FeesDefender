"""Operaciones de lectura/navegación con tiers y guardas Stream-aware."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from . import fsops
from .guards import check_gdoc, guard_file
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
