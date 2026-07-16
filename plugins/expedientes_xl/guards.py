"""Guardas Stream-aware (spec §6.2, §6.4): fail-closed ante COLD/UNKNOWN grande,
bloqueo de extensiones nativas de Google (lectura FS = ERROR_INVALID_FUNCTION)."""
from __future__ import annotations

import os
from pathlib import Path

_GDOC_EXTS = {".gdoc", ".gsheet", ".gslides", ".gdraw", ".gform", ".gtable", ".gmap"}


class GDocBloqueado(Exception):
    """Documento nativo de Google: ilegible por FS; exportar vía google-despacho."""


class FileNotHydrated(Exception):
    def __init__(self, mensaje: str, omitidos: list[str]):
        super().__init__(mensaje)
        self.omitidos = omitidos


def _mb(nombre: str, defecto: str) -> float:
    return float(os.environ.get(nombre, defecto))


def check_gdoc(path: Path) -> None:
    if path.suffix.lower() in _GDOC_EXTS:
        raise GDocBloqueado(
            f"{path.name}: documento nativo de Google — el montaje no puede leerlo; "
            "usa google-despacho (export_to_drive / read_file_content)")


def guard_file(oracle, path: Path) -> None:
    umbral = _mb("XL_HYDRATION_MAX_FILE_MB", "10") * 1024 * 1024
    try:
        tam = path.stat().st_size
    except OSError:
        return  # inexistente: lo dirá la operación
    if tam <= umbral:
        return
    estado = oracle.status(path)
    if estado != "HOT":
        raise FileNotHydrated(
            f"ERROR_FILE_NOT_HYDRATED: {path} ({tam} B, estado={estado}). "
            "Fija la carpeta 'Disponible sin conexión' en Drive o autoriza la descarga.",
            omitidos=[str(path)])


def guard_tree(oracle, root: Path) -> None:
    max_cold = int(_mb("XL_TREE_MAX_COLD", "50"))
    max_bytes = _mb("XL_TREE_MAX_MB", "150") * 1024 * 1024
    stats = oracle.subtree_cold_stats(root)
    if stats is not None:
        n_cold, n_total = stats
        if n_cold > max_cold:
            raise FileNotHydrated(
                f"ERROR_TREE_NOT_HYDRATED: {root}: {n_cold} ficheros COLD de {n_total} "
                f"(umbral {max_cold}). Hidrata el árbol antes (pin offline).",
                omitidos=[str(root)])
        return
    # oráculo caído: fail-closed si el árbol es grande (tamaño LÓGICO, stat no hidrata)
    total = 0
    for r, _d, files in os.walk(root):
        for f in files:
            try:
                total += os.stat(os.path.join(r, f)).st_size
            except OSError:
                continue
        if total > max_bytes:
            raise FileNotHydrated(
                f"ERROR_TREE_UNKNOWN: {root}: oráculo no disponible y árbol > "
                f"{max_bytes/1e6:.0f} MB — abortado fail-closed.",
                omitidos=[str(root)])
