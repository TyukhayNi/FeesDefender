"""Servidor MCP stdio `expedientes-xl` (wrapper sobre fsops/tiers/guards/oracle).

Uso: python server.py [--rw DIR]... [--ro DIR]... [--max-b64-bytes N]
(posicional legacy = `--rw`). Cada tool valida zonas (tiers.py) y guardas
Stream-aware (guards.py) antes de delegar en fsops/readops; las mutaciones
quedan auditadas (audit.py). `delete_path` NO existe: sin borrado (spec §2).
"""
from __future__ import annotations

import concurrent.futures
import os
import sys
import threading
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

try:  # importado como paquete (pytest: plugins.expedientes_xl.server)
    from . import audit, fsops, guards, readops, tiers
    from . import oracle as oracle_module
except ImportError:  # ejecutado como script suelto (python server.py): su dir está en sys.path[0]
    import audit
    import fsops
    import guards
    import readops
    import tiers
    import oracle as oracle_module

Zonas = tiers.Zonas  # re-exportado: tests/llamadores usan server.Zonas o tiers.Zonas indistintamente

DEFAULT_MAX_B64 = 8 * 1024 * 1024  # 8 MiB


def build_server(zonas: Zonas, oracle, max_b64_bytes: int = DEFAULT_MAX_B64,
                 max_extract_bytes: int = fsops.DEFAULT_MAX_EXTRACT_BYTES) -> FastMCP:
    mcp = FastMCP("expedientes-xl")
    allowed = list(zonas.rw_roots) + list(zonas.ro_roots)
    io_cap = threading.BoundedSemaphore(int(os.environ.get("XL_IO_CAP", "2")))

    def _heavy(fn):
        """Corre `fn` en un hilo daemon acotado por `io_cap`.

        El canal MCP responde con `future.result(timeout=XL_OP_TIMEOUT)` aunque
        la E/S siga en marcha (timeout-que-responde, spec §3.2): la
        cancelación-que-aborta-E/S queda V2. El hilo es daemon para no bloquear
        el cierre del proceso si la operación sigue viva en segundo plano.
        """
        future: concurrent.futures.Future = concurrent.futures.Future()

        def _target() -> None:
            with io_cap:
                try:
                    future.set_result(fn())
                except BaseException as exc:  # noqa: BLE001 - propagar tal cual al llamante
                    future.set_exception(exc)

        threading.Thread(target=_target, daemon=True).start()
        timeout = float(os.environ.get("XL_OP_TIMEOUT", "120"))
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            raise TimeoutError(
                "operación sigue en curso en segundo plano; reintenta o hidrata primero"
            ) from None

    @mcp.tool()
    def hash_path(path: str) -> str:
        """SHA-256 (hex) de un fichero, calculado server-side."""
        p = fsops.resolve_within(allowed, path)
        tiers.check_read(zonas, p)
        guards.guard_file(oracle, p)
        return fsops.sha256_file(allowed, path)

    @mcp.tool()
    def hash_tree(root: str) -> dict[str, str]:
        """SHA-256 recursivo (poda 90_Notas personales; aborta árbol frío grande).

        `iter_tree` poda por DIRECTORIO; un symlink-fichero suelto que apunte a
        Tier 0 se cuela como fichero normal. Por eso cada hallazgo re-valida su
        ruta RESUELTA (symlinks colapsados) contra `classify`: si el destino real
        cae en Tier 0 se omite (poda-y-cuenta, nunca aborta el resto del árbol) y
        queda auditado.
        """
        def _impl() -> dict[str, str]:
            p = fsops.resolve_within(allowed, root)
            tiers.check_read(zonas, p)
            guards.guard_tree(oracle, p)
            out: dict[str, str] = {}
            for f in readops.iter_tree(zonas, p):
                if tiers.classify(zonas, f.resolve()) is tiers.Tier.PROHIBIDA:
                    audit.log_op("hash_tree", str(f), "podado_symlink_tier0")
                    continue
                out[f.relative_to(p).as_posix()] = fsops.sha256_file(allowed, str(f))
            return out
        return _heavy(_impl)

    @mcp.tool()
    def copy_path(src: str, dst: str) -> str:
        """Copia un fichero (no destructivo; zonas+`.g*`+hidratación en ambos extremos). Ruta destino."""
        src_p = fsops.resolve_within(allowed, src)
        tiers.check_read(zonas, src_p)
        guards.guard_file(oracle, src_p)  # una copia lee bytes del origen (spec §6.2)
        out = fsops.copy_file_v2(allowed, zonas, src, dst)
        audit.log_op("copy_path", str(out), "ok")
        return str(out)

    @mcp.tool()
    def copy_dir(src: str, dst: str) -> dict[str, list[str]]:
        """Copia recursiva (poda Tier 0; ABORTA todo si algún destino viola zonas)."""
        def _impl() -> dict[str, list[str]]:
            out = fsops.copy_tree_v2(allowed, zonas, oracle, src, dst)
            audit.log_op("copy_dir", str(dst), "ok", n=len(out))
            return {"copiados": [str(p) for p in out]}
        return _heavy(_impl)

    @mcp.tool()
    def extract_archive(archive_path: str, dest_dir: str,
                        strip_top_level: bool = False) -> dict[str, list[str]]:
        """Descomprime zip/tar en dest_dir.

        `strip_top_level` quita el wrapper único. Cada MIEMBRO se valida contra
        zonas antes de volcar bytes: el que caiga en Tier 0 o Tier 1-existente
        (fuera del carve-out de protocolo) se OMITE (nunca aborta el resto del
        archivo) y queda listado en "omitidos", con su propio evento de auditoría.
        """
        def _impl() -> dict[str, list[str]]:
            archive_p = fsops.resolve_within(allowed, archive_path)
            tiers.check_read(zonas, archive_p)  # el ORIGEN también: Tier 0 nunca se lee
            guards.guard_file(oracle, archive_p)
            omitidos: list[str] = []

            def _permitido(name: str, dest: Path) -> bool:
                try:
                    tiers.check_write(zonas, dest, exists=dest.exists())
                except tiers.TierViolation:
                    omitidos.append(name)
                    audit.log_op("extract_archive", str(dest), "omitido_zona")
                    return False
                return True

            extraidos = fsops.extract_archive(
                allowed, archive_path, dest_dir, max_extract_bytes,
                strip_top_level=strip_top_level, member_filter=_permitido)
            audit.log_op("extract_archive", str(dest_dir), "ok", n=len(extraidos))
            return {"extraidos": [str(p) for p in extraidos], "omitidos": omitidos}
        return _heavy(_impl)

    @mcp.tool()
    def write_file_base64(path: str, content_b64: str) -> int:
        """Escribe un binario desde base64 (respeta zonas; tope configurado). Bytes escritos."""
        p = fsops.resolve_within(allowed, path)
        tiers.check_write(zonas, p, exists=p.exists())
        n = fsops.write_base64(allowed, path, content_b64, max_b64_bytes)
        audit.log_op("write_file_base64", str(p), "ok", bytes=n)
        return n

    @mcp.tool()
    def append_text(path: str, text: str) -> str:
        """Anexa texto UTF-8 a un fichero (lo crea si falta; respeta zonas/protocolo)."""
        p = fsops.resolve_within(allowed, path)
        tiers.check_write(zonas, p, exists=p.exists(), append=True)
        dst = fsops.append_text(allowed, path, text)
        audit.log_op("append_text", str(dst), "ok", bytes=len(text.encode("utf-8")))
        return str(dst)

    @mcp.tool()
    def read_text(path: str, head: int | None = None, tail: int | None = None) -> str:
        """Lee texto UTF-8 con tope de tamaño; `head`/`tail` acotan por líneas."""
        return readops.read_text(allowed, zonas, oracle, path, head=head, tail=tail)

    @mcp.tool()
    def read_multiple(paths: list[str]) -> dict[str, str]:
        """Lee varios ficheros de texto; un fallo individual no tumba el lote."""
        return readops.read_multiple(allowed, zonas, oracle, paths)

    @mcp.tool()
    def list_dir(path: str, sizes: bool = False) -> list[dict]:
        """Lista el contenido de un directorio, podando Tier 0."""
        return readops.list_dir(allowed, zonas, path, sizes=sizes)

    @mcp.tool()
    def tree(path: str, max_depth: int = 8) -> dict[str, Any]:
        """Árbol de ficheros relativo con poda Tier 0 y límites de profundidad/entradas."""
        def _impl() -> dict[str, Any]:
            return readops.tree(allowed, zonas, path, max_depth=max_depth)
        return _heavy(_impl)

    @mcp.tool()
    def get_metadata(path: str) -> dict[str, Any]:
        """Metadatos (tamaño, mtime, tier, hidratación) de un fichero o directorio."""
        return readops.get_metadata(allowed, zonas, oracle, path)

    @mcp.tool()
    def search_name(path: str, patron: str) -> list[str]:
        """Búsqueda por nombre de fichero (fnmatch case-insensitive), podando Tier 0."""
        return readops.search_name(allowed, zonas, path, patron)

    @mcp.tool()
    def search_content(path: str, consulta: str, regex: bool = False) -> dict[str, Any]:
        """Búsqueda de contenido (grep) con poda Tier 0 y guardas de hidratación."""
        def _impl() -> dict[str, Any]:
            return readops.search_content(allowed, zonas, oracle, path, consulta, regex=regex)
        return _heavy(_impl)

    @mcp.tool()
    def create_dir(path: str) -> str:
        """Crea un directorio (con sus padres) respetando zonas."""
        p = fsops.resolve_within(allowed, path)
        tiers.check_write(zonas, p, exists=False)
        p.mkdir(parents=True, exist_ok=True)
        audit.log_op("create_dir", str(p), "ok")
        return str(p)

    @mcp.tool()
    def write_text(path: str, text: str) -> str:
        """Escribe texto UTF-8 de forma atómica, respetando zonas."""
        dst = fsops.write_text_file(allowed, zonas, path, text)
        audit.log_op("write_text", str(dst), "ok", bytes=len(text.encode("utf-8")))
        return str(dst)

    @mcp.tool()
    def edit_text(path: str, old: str, new: str) -> str:
        """Reemplaza una única aparición exacta de texto en un fichero, atómico."""
        dst = fsops.edit_text_file(allowed, zonas, path, old, new)
        audit.log_op("edit_text", str(dst), "ok")
        return str(dst)

    @mcp.tool()
    def resolve_shortcut(path: str) -> dict[str, Any]:
        """Resuelve un `.lnk` y re-valida su destino contra sandbox y tiers."""
        return readops.resolve_shortcut(allowed, zonas, path)

    @mcp.tool()
    def hydration_status(path: str) -> dict[str, str]:
        """Estado de hidratación (HOT/COLD/UNKNOWN) de una ruta."""
        p = fsops.resolve_within(allowed, path)
        tiers.check_read(zonas, p)
        return {"status": oracle.status(p)}

    return mcp


def _parse_argv(argv: list[str]) -> tuple[Zonas, int]:
    rw: list[Path] = []
    ro: list[Path] = []
    max_b64 = DEFAULT_MAX_B64
    it = iter(argv)
    for a in it:
        if a == "--rw":
            rw.append(Path(next(it)))
        elif a == "--ro":
            ro.append(Path(next(it)))
        elif a == "--max-b64-bytes":
            max_b64 = int(next(it))
        else:
            rw.append(Path(a))  # legacy posicional
    if not rw and not ro:
        raise SystemExit("Uso: server.py [--rw DIR]... [--ro DIR]... [--max-b64-bytes N]")
    return Zonas(rw_roots=tuple(rw), ro_roots=tuple(ro)), max_b64


def main() -> None:
    zonas, max_b64 = _parse_argv(sys.argv[1:])
    all_roots = list(zonas.rw_roots) + list(zonas.ro_roots)
    roots = {str(r): r for r in all_roots}
    drivefs_dir = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Google" / "DriveFS"
    dbs, caches = oracle_module.descubrir_cuentas(drivefs_dir, roots)
    orc = oracle_module.Oracle(dbs, caches)
    build_server(zonas, orc, max_b64).run()


if __name__ == "__main__":
    main()
