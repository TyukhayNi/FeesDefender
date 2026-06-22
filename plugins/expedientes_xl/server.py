"""Servidor MCP stdio `expedientes-xl` (wrapper fino sobre fsops).

Uso: python server.py <allowed_dir> [<allowed_dir> ...] [--max-b64-bytes N]
Cada tool delega en fsops; toda ruta se valida contra allowed_dirs.
"""
from __future__ import annotations

import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

try:  # importado como paquete (pytest: plugins.expedientes_xl.server)
    from . import fsops
except ImportError:  # ejecutado como script suelto (python server.py): su dir está en sys.path[0]
    import fsops

DEFAULT_MAX_B64 = 8 * 1024 * 1024  # 8 MiB


def build_server(allowed_dirs: list[Path], max_b64_bytes: int = DEFAULT_MAX_B64,
                 max_extract_bytes: int = fsops.DEFAULT_MAX_EXTRACT_BYTES) -> FastMCP:
    mcp = FastMCP("expedientes-xl")

    @mcp.tool()
    def hash_path(path: str) -> str:
        """SHA-256 (hex) de un fichero, calculado server-side."""
        return fsops.sha256_file(allowed_dirs, path)

    @mcp.tool()
    def copy_path(src: str, dst: str) -> str:
        """Copia un fichero (no destructivo). Devuelve la ruta destino."""
        return str(fsops.copy_file(allowed_dirs, src, dst))

    @mcp.tool()
    def copy_dir(src: str, dst: str) -> str:
        """Copia recursiva de un árbol. Devuelve la ruta destino."""
        return str(fsops.copy_tree(allowed_dirs, src, dst))

    @mcp.tool()
    def extract_archive(archive_path: str, dest_dir: str) -> list[str]:
        """Descomprime zip/tar en dest_dir. Devuelve los ficheros extraídos."""
        return [str(p) for p in fsops.extract_archive(allowed_dirs, archive_path, dest_dir, max_extract_bytes)]

    @mcp.tool()
    def write_file_base64(path: str, content_b64: str) -> int:
        """Escribe un binario desde base64 (tope configurado). Bytes escritos."""
        return fsops.write_base64(allowed_dirs, path, content_b64, max_b64_bytes)

    @mcp.tool()
    def append_text(path: str, text: str) -> str:
        """Anexa texto UTF-8 a un fichero (lo crea si falta)."""
        return str(fsops.append_text(allowed_dirs, path, text))

    @mcp.tool()
    def delete_path(path: str) -> str:
        """Borra fichero o árbol dentro del sandbox."""
        fsops.delete_path(allowed_dirs, path)
        return path

    return mcp


def _parse_argv(argv: list[str]) -> tuple[list[Path], int]:
    dirs: list[Path] = []
    max_b64 = DEFAULT_MAX_B64
    it = iter(argv)
    for a in it:
        if a == "--max-b64-bytes":
            max_b64 = int(next(it))
        else:
            dirs.append(Path(a))
    if not dirs:
        raise SystemExit("Uso: server.py <allowed_dir> [...] [--max-b64-bytes N]")
    return dirs, max_b64


def main() -> None:
    dirs, max_b64 = _parse_argv(sys.argv[1:])
    build_server(dirs, max_b64).run()


if __name__ == "__main__":
    main()
