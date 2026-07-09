import asyncio
import hashlib
import zipfile
from pathlib import Path

import pytest

pytest.importorskip("mcp")  # el server importa mcp.server.fastmcp; skip si no está

from plugins.expedientes_xl import server as srv


def test_server_registra_todas_las_tools(tmp_path):
    mcp = srv.build_server([tmp_path], max_b64_bytes=1000)
    tools = asyncio.run(mcp.list_tools())
    nombres = {t.name for t in tools}
    assert nombres == {
        "hash_path",
        "hash_tree",
        "copy_path",
        "copy_dir",
        "extract_archive",
        "write_file_base64",
        "append_text",
        "delete_path",
    }


def test_hash_tree_tool_devuelve_dict_esperado(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "a.txt").write_bytes(b"hola")
    (tmp_path / "sub" / "b.txt").write_bytes(b"mundo")

    mcp = srv.build_server([tmp_path], max_b64_bytes=1000)

    async def _call():
        return await mcp.call_tool("hash_tree", {"root": str(tmp_path)})

    _content, out = asyncio.run(_call())
    assert out == {
        "a.txt": hashlib.sha256(b"hola").hexdigest(),
        "sub/b.txt": hashlib.sha256(b"mundo").hexdigest(),
    }


def test_extract_archive_tool_strip_top_level_quita_wrapper(tmp_path):
    archive = tmp_path / "export.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("Wrapper/ACTIVACION/hoja.pdf", b"A")
        zf.writestr("Wrapper/oferta.pdf", b"B")
    dest = tmp_path / "out"

    mcp = srv.build_server([tmp_path], max_b64_bytes=1000)

    async def _call():
        return await mcp.call_tool(
            "extract_archive",
            {"archive_path": str(archive), "dest_dir": str(dest), "strip_top_level": True},
        )

    _content, structured = asyncio.run(_call())
    rels = sorted(Path(p).relative_to(dest.resolve()).as_posix() for p in structured["result"])
    assert rels == ["ACTIVACION/hoja.pdf", "oferta.pdf"]
