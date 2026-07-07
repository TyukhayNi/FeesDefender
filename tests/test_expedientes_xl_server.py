import asyncio

import pytest

pytest.importorskip("mcp")  # el server importa mcp.server.fastmcp; skip si no está

from plugins.expedientes_xl import server as srv


def test_server_registra_todas_las_tools(tmp_path):
    mcp = srv.build_server([tmp_path], max_b64_bytes=1000)
    tools = asyncio.run(mcp.list_tools())
    nombres = {t.name for t in tools}
    assert nombres == {
        "hash_path",
        "copy_path",
        "copy_dir",
        "extract_archive",
        "write_file_base64",
        "append_text",
        "delete_path",
    }
