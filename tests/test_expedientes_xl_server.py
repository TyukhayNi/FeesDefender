import asyncio
import hashlib

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
