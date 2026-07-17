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
        "read_text",
        "read_multiple",
        "list_dir",
        "tree",
        "get_metadata",
        "search_name",
        "search_content",
        "create_dir",
        "write_text",
        "edit_text",
        "resolve_shortcut",
        "hydration_status",
    }


def test_tools_nuevas_registradas(tmp_path):
    srv_mcp = _srv(tmp_path)
    nombres = {t.name for t in asyncio.run(srv_mcp.list_tools())}
    esperadas = {"read_text", "read_multiple", "list_dir", "tree", "get_metadata",
                 "search_name", "search_content", "create_dir", "write_text",
                 "edit_text", "resolve_shortcut", "hydration_status"}
    assert esperadas <= nombres


def test_read_text_via_tool(tmp_path):
    (tmp_path / "d.txt").write_text("hola\n", encoding="utf-8")
    srv_mcp = _srv(tmp_path)
    res = asyncio.run(srv_mcp.call_tool("read_text", {"path": str(tmp_path / "d.txt")}))
    assert "hola" in str(res)


def test_read_multiple_via_tool(tmp_path):
    (tmp_path / "a.txt").write_text("uno", encoding="utf-8")
    (tmp_path / "b.txt").write_text("dos", encoding="utf-8")
    mcp = _srv(tmp_path)

    async def _call():
        return await mcp.call_tool(
            "read_multiple", {"paths": [str(tmp_path / "a.txt"), str(tmp_path / "b.txt")]}
        )

    _content, out = asyncio.run(_call())
    assert out[str(tmp_path / "a.txt")] == "uno"
    assert out[str(tmp_path / "b.txt")] == "dos"


def test_list_dir_via_tool(tmp_path):
    (tmp_path / "x.txt").write_bytes(b"12345")
    mcp = _srv(tmp_path)

    async def _call():
        return await mcp.call_tool("list_dir", {"path": str(tmp_path), "sizes": True})

    _content, structured = asyncio.run(_call())
    out = structured["result"]  # tool devuelve list[dict]: MCP envuelve listas top-level en {"result": [...]}
    entrada = next(e for e in out if e.get("name") == "x.txt")
    assert entrada["size"] == 5


def test_list_dir_via_tool_poda_tier0(tmp_path):
    (tmp_path / "90_Notas personales").mkdir()
    (tmp_path / "90_Notas personales" / "s.txt").write_text("priv", encoding="utf-8")
    mcp = _srv(tmp_path)

    async def _call():
        return await mcp.call_tool("list_dir", {"path": str(tmp_path)})

    _content, structured = asyncio.run(_call())
    nombres = [e["name"] for e in structured["result"] if "name" in e]
    assert "90_Notas personales" not in nombres


def test_tree_tool_pasa_dict_completo(tmp_path):
    """El tool `tree` no reformatea el dict de readops: pasa TODAS sus claves,
    incluida `omitidos_profundidad` (añadida tras el plan original)."""
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    mcp = _srv(tmp_path)

    async def _call():
        return await mcp.call_tool("tree", {"path": str(tmp_path)})

    _content, out = asyncio.run(_call())
    assert set(out.keys()) == {"entries", "podados", "truncado", "omitidos_profundidad"}
    assert out["entries"] == ["a.txt"]
    assert out["omitidos_profundidad"] == 0


def test_get_metadata_via_tool(tmp_path):
    (tmp_path / "00_Input").mkdir()
    f = tmp_path / "00_Input" / "doc.txt"
    f.write_text("hola", encoding="utf-8")
    mcp = _srv(tmp_path)

    async def _call():
        return await mcp.call_tool("get_metadata", {"path": str(f)})

    _content, out = asyncio.run(_call())
    assert out["name"] == "doc.txt"
    assert out["tier"] == 1  # 00_Input -> FORENSE
    assert out["hydration"] == "HOT"  # FakeOracle


def test_search_name_via_tool(tmp_path):
    (tmp_path / "doc.txt").write_text("x", encoding="utf-8")
    (tmp_path / "otro.bin").write_bytes(b"y")
    mcp = _srv(tmp_path)

    async def _call():
        return await mcp.call_tool("search_name", {"path": str(tmp_path), "patron": "*.txt"})

    _content, structured = asyncio.run(_call())
    out = structured["result"]  # tool devuelve list[str]: MCP envuelve listas top-level en {"result": [...]}
    assert any(h.endswith("doc.txt") for h in out)
    assert not any(h.endswith("otro.bin") for h in out)


def test_search_content_via_tool(tmp_path):
    (tmp_path / "doc.txt").write_text("linea uno\nbuscado aqui\n", encoding="utf-8")
    mcp = _srv(tmp_path)

    async def _call():
        return await mcp.call_tool(
            "search_content", {"path": str(tmp_path), "consulta": "buscado"}
        )

    _content, out = asyncio.run(_call())
    assert out["matches"][0]["line"] == 2
    assert out["podados"] == 0


def test_search_content_no_sigue_symlink_a_tier0(tmp_path):
    """Un symlink-fichero en el workspace que apunte DENTRO de 90_Notas
    personales no debe filtrar su CONTENIDO al modelo: `iter_tree` poda por
    DIRECTORIO (no ve el symlink suelto), así que `search_content` re-valida
    la ruta RESUELTA antes de abrir/leer (mismo vector que ya cerraba
    `hash_tree`, ahora también en `search_content` vía
    `iter_tree(reclasificar_resueltos=True)`)."""
    notas = tmp_path / "90_Notas personales"
    notas.mkdir()
    secreto = notas / "secreto.txt"
    secreto.write_text("PALABRA_CLAVE_SECRETA\n", encoding="utf-8")
    enlace = tmp_path / "enlace.txt"
    try:
        enlace.symlink_to(secreto)
    except OSError as e:
        pytest.skip(f"symlink no soportado en este entorno (requiere admin en Windows): {e}")
    (tmp_path / "a.txt").write_text("PALABRA_CLAVE_SECRETA en claro\n", encoding="utf-8")
    mcp = _srv(tmp_path)

    async def _call():
        return await mcp.call_tool(
            "search_content", {"path": str(tmp_path), "consulta": "PALABRA_CLAVE_SECRETA"}
        )

    _content, out = asyncio.run(_call())
    rutas = {m["path"] for m in out["matches"]}
    assert str(enlace) not in rutas               # el symlink NUNCA se abre/lee
    assert str(tmp_path / "a.txt") in rutas        # el fichero legítimo sí matchea


def test_create_dir_via_tool(tmp_path):
    mcp = _srv(tmp_path)
    nuevo = tmp_path / "00_Input" / "sub"

    async def _call():
        return await mcp.call_tool("create_dir", {"path": str(nuevo)})

    asyncio.run(_call())
    assert nuevo.is_dir()


def test_create_dir_via_tool_rechaza_tier0(tmp_path):
    mcp = _srv(tmp_path)
    nuevo = tmp_path / "90_Notas personales" / "sub"

    async def _call():
        return await mcp.call_tool("create_dir", {"path": str(nuevo)})

    with pytest.raises(Exception, match="Zona prohibida"):
        asyncio.run(_call())


def test_write_text_via_tool(tmp_path):
    mcp = _srv(tmp_path)
    destino = tmp_path / "nota.txt"

    async def _call():
        return await mcp.call_tool("write_text", {"path": str(destino), "text": "hola"})

    asyncio.run(_call())
    assert destino.read_text(encoding="utf-8") == "hola"


def test_write_text_via_tool_rechaza_sobrescribir_00_input(tmp_path):
    mcp = _srv(tmp_path)
    destino = tmp_path / "00_Input" / "depositado.txt"
    destino.parent.mkdir(parents=True)
    destino.write_text("orig", encoding="utf-8")

    async def _call():
        return await mcp.call_tool("write_text", {"path": str(destino), "text": "nuevo"})

    with pytest.raises(Exception, match="forense-inmutable"):
        asyncio.run(_call())


def test_edit_text_via_tool(tmp_path):
    destino = tmp_path / "nota.txt"
    destino.write_text("hola mundo", encoding="utf-8")
    mcp = _srv(tmp_path)

    async def _call():
        return await mcp.call_tool(
            "edit_text", {"path": str(destino), "old": "mundo", "new": "claude"}
        )

    asyncio.run(_call())
    assert destino.read_text(encoding="utf-8") == "hola claude"


def test_resolve_shortcut_via_tool_fail_closed(tmp_path):
    """Sin resolver inyectable desde el tool MCP: un `.lnk` inválido resuelve
    en vacío (fail-closed), tal y como hace `_resolver_lnk_com` real."""
    lnk = tmp_path / "atajo.lnk"
    lnk.write_bytes(b"no es un lnk valido")
    mcp = _srv(tmp_path)

    async def _call():
        return await mcp.call_tool("resolve_shortcut", {"path": str(lnk)})

    _content, out = asyncio.run(_call())
    assert out["target"] is None
    assert out["dentro_sandbox"] is False


def test_hydration_status_via_tool(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("x", encoding="utf-8")
    mcp = _srv(tmp_path)  # FakeOracle.status siempre "HOT"

    async def _call():
        return await mcp.call_tool("hydration_status", {"path": str(f)})

    _content, out = asyncio.run(_call())
    assert out == {"status": "HOT"}


def test_hydration_status_via_tool_rechaza_tier0(tmp_path):
    secreto = tmp_path / "90_Notas personales" / "s.txt"
    secreto.parent.mkdir(parents=True)
    secreto.write_text("x", encoding="utf-8")
    mcp = _srv(tmp_path)

    async def _call():
        return await mcp.call_tool("hydration_status", {"path": str(secreto)})

    with pytest.raises(Exception, match="Zona prohibida"):
        asyncio.run(_call())


def test_copy_path_rechaza_origen_frio_grande(tmp_path, monkeypatch):
    """Guarda de hidratación en `copy_path` (controller review Task 14): una
    copia lee bytes del origen, así que un COLD por encima del umbral se
    rechaza en vez de intentar copiarlo (spec §6.2)."""
    monkeypatch.setenv("XL_HYDRATION_MAX_FILE_MB", "0")

    class ColdOracle(FakeOracle):
        def status(self, p):
            return "COLD"

    src = tmp_path / "orig.bin"
    src.write_bytes(b"datos")
    dst = tmp_path / "dest" / "copia.bin"
    mcp = _srv(tmp_path, oracle=ColdOracle())

    async def _call():
        return await mcp.call_tool("copy_path", {"src": str(src), "dst": str(dst)})

    with pytest.raises(Exception, match="ERROR_FILE_NOT_HYDRATED"):
        asyncio.run(_call())
    assert not dst.exists()


def test_hash_tree_poda_symlink_a_tier0(tmp_path):
    """Un symlink en el workspace que apunte DENTRO de 90_Notas personales no
    se cuela: `iter_tree` poda por directorio, así que un symlink-fichero
    suelto se re-valida por ruta resuelta (controller review Task 14)."""
    notas = tmp_path / "90_Notas personales"
    notas.mkdir()
    secreto = notas / "secreto.txt"
    secreto.write_bytes(b"priv")
    enlace = tmp_path / "enlace.txt"
    try:
        enlace.symlink_to(secreto)
    except OSError as e:
        pytest.skip(f"symlink no soportado en este entorno (requiere admin en Windows): {e}")
    (tmp_path / "a.txt").write_bytes(b"hola")
    mcp = _srv(tmp_path)

    async def _call():
        return await mcp.call_tool("hash_tree", {"root": str(tmp_path)})

    _content, out = asyncio.run(_call())
    assert out == {"a.txt": hashlib.sha256(b"hola").hexdigest()}


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


def test_parse_argv_rw_ro_roots_correctos():
    """Contrato de argv que consume `run_server.bat` (fix de la comilla escapada).

    `--rw "G:\\"` bajo el parseo de argv de MSVCRT/Python colapsa la secuencia
    `\\"` en una comilla escapada: el token `"G:\\"` se fusiona con el
    siguiente y `H:` desaparece de `sys.argv`. El wrapper se corrige a raíces
    SIN comillas (`--rw G:\\ --ro H:\\`); este test fija el contrato de
    `_parse_argv` para ese argv ya tokenizado correctamente por el shell, de
    modo que una regresión de intención (volver a poner comillas) quede
    atrapada aunque el `.bat` en sí no sea testeable con pytest.
    """
    zonas, max_b64 = srv._parse_argv(["--rw", "G:\\", "--ro", "H:\\"])
    assert zonas.rw_roots == (Path("G:\\"),)
    assert zonas.ro_roots == (Path("H:\\"),)
    assert max_b64 == srv.DEFAULT_MAX_B64


def test_parse_argv_legacy_posicional_es_rw(tmp_path):
    zonas, max_b64 = srv._parse_argv([str(tmp_path)])
    assert zonas.rw_roots == (tmp_path,)
    assert zonas.ro_roots == ()
    assert max_b64 == srv.DEFAULT_MAX_B64


def test_parse_argv_exige_al_menos_una_raiz():
    with pytest.raises(SystemExit):
        srv._parse_argv([])
