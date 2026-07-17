import asyncio
import base64
import hashlib
import zipfile
from pathlib import Path

import pytest

pytest.importorskip("mcp")  # el server importa mcp.server.fastmcp; skip si no está

from plugins.expedientes_xl import server as srv
from plugins.expedientes_xl.tiers import Zonas


class FakeOracle:
    def status(self, p):
        return "HOT"

    def subtree_cold_stats(self, p):
        return (0, 1)


def _srv(tmp_path, oracle=None, **kwargs):
    return srv.build_server(Zonas(rw_roots=(tmp_path,)), oracle or FakeOracle(), **kwargs)


def test_server_registra_todas_las_tools(tmp_path):
    mcp = _srv(tmp_path, max_b64_bytes=1000)
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
    }


def test_delete_path_retirado(tmp_path):
    """`delete_path` se retira de la superficie: sin borrado (spec §2)."""
    mcp = _srv(tmp_path)
    nombres = {t.name for t in asyncio.run(mcp.list_tools())}
    assert "delete_path" not in nombres


def test_hash_tree_tool_devuelve_dict_esperado(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "a.txt").write_bytes(b"hola")
    (tmp_path / "sub" / "b.txt").write_bytes(b"mundo")

    mcp = _srv(tmp_path, max_b64_bytes=1000)

    async def _call():
        return await mcp.call_tool("hash_tree", {"root": str(tmp_path)})

    _content, out = asyncio.run(_call())
    assert out == {
        "a.txt": hashlib.sha256(b"hola").hexdigest(),
        "sub/b.txt": hashlib.sha256(b"mundo").hexdigest(),
    }


def test_hash_tree_poda_tier0(tmp_path):
    (tmp_path / "90_Notas personales").mkdir()
    (tmp_path / "90_Notas personales" / "secreto.txt").write_bytes(b"priv")
    (tmp_path / "a.txt").write_bytes(b"hola")
    mcp = _srv(tmp_path)

    async def _call():
        return await mcp.call_tool("hash_tree", {"root": str(tmp_path)})

    _content, out = asyncio.run(_call())
    assert out == {"a.txt": hashlib.sha256(b"hola").hexdigest()}


def test_hash_tree_aborta_arbol_frio(tmp_path, monkeypatch):
    monkeypatch.setenv("XL_TREE_MAX_COLD", "0")

    class ColdOracle:
        def status(self, p):
            return "COLD"

        def subtree_cold_stats(self, p):
            return (5, 5)

    (tmp_path / "a.txt").write_bytes(b"hola")
    mcp = _srv(tmp_path, oracle=ColdOracle())

    async def _call():
        return await mcp.call_tool("hash_tree", {"root": str(tmp_path)})

    with pytest.raises(Exception, match="ERROR_TREE_NOT_HYDRATED"):
        asyncio.run(_call())


def test_hash_path_rechaza_tier0(tmp_path):
    secreto = tmp_path / "90_Notas personales" / "s.txt"
    secreto.parent.mkdir(parents=True)
    secreto.write_bytes(b"x")
    mcp = _srv(tmp_path)

    async def _call():
        return await mcp.call_tool("hash_path", {"path": str(secreto)})

    with pytest.raises(Exception, match="Zona prohibida"):
        asyncio.run(_call())


def test_extract_archive_tool_strip_top_level_quita_wrapper(tmp_path):
    archive = tmp_path / "export.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("Wrapper/ACTIVACION/hoja.pdf", b"A")
        zf.writestr("Wrapper/oferta.pdf", b"B")
    dest = tmp_path / "out"

    mcp = _srv(tmp_path, max_b64_bytes=1000)

    async def _call():
        return await mcp.call_tool(
            "extract_archive",
            {"archive_path": str(archive), "dest_dir": str(dest), "strip_top_level": True},
        )

    _content, structured = asyncio.run(_call())
    rels = sorted(
        Path(p).relative_to(dest.resolve()).as_posix() for p in structured["extraidos"]
    )
    assert rels == ["ACTIVACION/hoja.pdf", "oferta.pdf"]
    assert structured["omitidos"] == []


def test_extract_archive_omite_miembro_tier1_existente(tmp_path):
    """Miembro que sobrescribiría algo ya depositado en 00_Input: se omite y se lista."""
    (tmp_path / "00_Input").mkdir()
    (tmp_path / "00_Input" / "doc.txt").write_text("orig", encoding="utf-8")
    archive = tmp_path / "e.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("doc.txt", b"nuevo")
        zf.writestr("otro.txt", b"ok")
    dest = tmp_path / "00_Input"

    mcp = _srv(tmp_path)

    async def _call():
        return await mcp.call_tool(
            "extract_archive", {"archive_path": str(archive), "dest_dir": str(dest)}
        )

    _content, structured = asyncio.run(_call())
    assert structured["omitidos"] == ["doc.txt"]
    assert (dest / "doc.txt").read_text(encoding="utf-8") == "orig"  # intacto
    assert (dest / "otro.txt").read_bytes() == b"ok"                # el resto SÍ se extrae


def test_extract_archive_rechaza_origen_tier0(tmp_path):
    """El zip de ORIGEN también respeta Tier 0: ni lectura (regla dura CLAUDE.md)."""
    notas = tmp_path / "90_Notas personales"
    notas.mkdir()
    archive = notas / "privado.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("x.txt", b"secreto")
    dest = tmp_path / "out"
    mcp = _srv(tmp_path)

    async def _call():
        return await mcp.call_tool(
            "extract_archive", {"archive_path": str(archive), "dest_dir": str(dest)}
        )

    with pytest.raises(Exception, match="Zona prohibida"):
        asyncio.run(_call())
    assert not dest.exists()


def test_write_base64_respeta_zonas(tmp_path):
    mcp = _srv(tmp_path)
    destino = str(tmp_path / "00_Input" / "n.bin")
    b64 = base64.b64encode(b"bytes").decode()

    async def _write():
        return await mcp.call_tool(
            "write_file_base64", {"path": destino, "content_b64": b64}
        )

    asyncio.run(_write())
    assert (tmp_path / "00_Input" / "n.bin").read_bytes() == b"bytes"  # crear-nuevo ok
    with pytest.raises(Exception, match="forense-inmutable"):          # sobrescribir no
        asyncio.run(_write())


def test_append_text_crea_y_anexa_a_log_de_protocolo(tmp_path):
    mcp = _srv(tmp_path)
    log = str(tmp_path / "00_Input" / "_intake_log.jsonl")

    async def _call(texto):
        return await mcp.call_tool("append_text", {"path": log, "text": texto})

    asyncio.run(_call('{"a":1}\n'))
    asyncio.run(_call('{"b":2}\n'))
    assert (tmp_path / "00_Input" / "_intake_log.jsonl").read_text(
        encoding="utf-8"
    ) == '{"a":1}\n{"b":2}\n'


def test_append_text_rechaza_fichero_no_protocolo_ya_depositado(tmp_path):
    mcp = _srv(tmp_path)
    destino = str(tmp_path / "00_Input" / "depositado.txt")

    async def _call(texto):
        return await mcp.call_tool("append_text", {"path": destino, "text": texto})

    asyncio.run(_call("v1"))  # crear-nuevo bajo 00_Input: permitido
    with pytest.raises(Exception, match="forense-inmutable"):
        asyncio.run(_call("v2"))  # no es fichero de protocolo ni pide append=True casando patrón


def test_copy_path_tool_delega_en_copy_file_v2(tmp_path):
    src = tmp_path / "orig.bin"
    src.write_bytes(b"datos")
    dst = tmp_path / "dest" / "copia.bin"
    mcp = _srv(tmp_path)

    async def _call():
        return await mcp.call_tool("copy_path", {"src": str(src), "dst": str(dst)})

    asyncio.run(_call())
    assert dst.read_bytes() == b"datos"
    assert src.exists()  # no destructivo


def test_copy_dir_tool_poda_tier0_y_devuelve_copiados(tmp_path):
    src = tmp_path / "arbol"
    (src / "90_Notas personales").mkdir(parents=True)
    (src / "90_Notas personales" / "s.txt").write_text("priv", encoding="utf-8")
    (src / "doc.txt").write_text("x", encoding="utf-8")
    dst = tmp_path / "copia"
    mcp = _srv(tmp_path)

    async def _call():
        return await mcp.call_tool("copy_dir", {"src": str(src), "dst": str(dst)})

    _content, structured = asyncio.run(_call())
    assert (dst / "doc.txt").exists()
    assert not (dst / "90_Notas personales").exists()  # podado, nunca copiado
    assert structured["copiados"] == [str((dst / "doc.txt").resolve())]


def test_copy_dir_tool_aborta_si_destino_viola_tier1(tmp_path):
    src = tmp_path / "arbol"
    src.mkdir()
    (src / "a.txt").write_text("a", encoding="utf-8")
    (src / "doc.txt").write_text("nuevo", encoding="utf-8")
    dst = tmp_path / "00_Input"
    dst.mkdir()
    (dst / "doc.txt").write_text("orig", encoding="utf-8")
    mcp = _srv(tmp_path)

    async def _call():
        return await mcp.call_tool("copy_dir", {"src": str(src), "dst": str(dst)})

    with pytest.raises(Exception, match="forense-inmutable"):
        asyncio.run(_call())
    assert (dst / "doc.txt").read_text(encoding="utf-8") == "orig"  # intacto
    assert not (dst / "a.txt").exists()  # aborto TOTAL: ni el válido se copió


def test_operacion_pesada_responde_ante_timeout(tmp_path, monkeypatch):
    """El canal MCP nunca queda colgado: ante timeout, error legible (spec §3.2)."""
    import time

    monkeypatch.setenv("XL_OP_TIMEOUT", "0.05")

    class SlowOracle(FakeOracle):
        def subtree_cold_stats(self, p):
            time.sleep(0.3)
            return (0, 1)

    src = tmp_path / "arbol"
    src.mkdir()
    (src / "f.txt").write_text("x", encoding="utf-8")
    mcp = _srv(tmp_path, oracle=SlowOracle())

    async def _call():
        return await mcp.call_tool(
            "copy_dir", {"src": str(src), "dst": str(tmp_path / "dst")}
        )

    with pytest.raises(Exception, match="segundo plano"):
        asyncio.run(_call())


def test_parse_argv_rw_ro_repetibles_y_max_b64(tmp_path):
    a = tmp_path / "A"
    b = tmp_path / "B"
    a.mkdir()
    b.mkdir()
    zonas, max_b64 = srv._parse_argv(
        ["--rw", str(a), "--ro", str(b), "--max-b64-bytes", "123"]
    )
    assert zonas.rw_roots == (a,)
    assert zonas.ro_roots == (b,)
    assert max_b64 == 123


def test_parse_argv_legacy_posicional_es_rw(tmp_path):
    zonas, max_b64 = srv._parse_argv([str(tmp_path)])
    assert zonas.rw_roots == (tmp_path,)
    assert zonas.ro_roots == ()
    assert max_b64 == srv.DEFAULT_MAX_B64


def test_parse_argv_exige_al_menos_una_raiz():
    with pytest.raises(SystemExit):
        srv._parse_argv([])
