import base64
import hashlib
import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from plugins.expedientes_xl import fsops
from plugins.expedientes_xl.tiers import TierViolation, Zonas


class FakeOracle:
    def status(self, p):
        return "HOT"

    def subtree_cold_stats(self, p):
        return (0, 1)


def _zonas(tmp_path):
    return Zonas(rw_roots=(tmp_path,))


def test_resolve_within_acepta_ruta_dentro(tmp_path):
    allowed = [tmp_path]
    target = tmp_path / "sub" / "f.txt"
    assert fsops.resolve_within(allowed, str(target)) == target.resolve()


def test_resolve_within_rechaza_traversal(tmp_path):
    allowed = [tmp_path]
    fuera = tmp_path / ".." / "escape.txt"
    with pytest.raises(fsops.OutsideSandbox):
        fsops.resolve_within(allowed, str(fuera))


def test_resolve_within_rechaza_absoluta_fuera(tmp_path):
    allowed = [tmp_path]
    with pytest.raises(fsops.OutsideSandbox):
        fsops.resolve_within(allowed, "C:\\Windows\\system32\\x")


def test_sha256_file_coincide_con_hashlib(tmp_path):
    f = tmp_path / "x.bin"
    data = b"contenido binario \x00\x01\x02" * 1000
    f.write_bytes(data)
    esperado = hashlib.sha256(data).hexdigest()
    assert fsops.sha256_file([tmp_path], str(f)) == esperado


def test_sha256_file_rechaza_fuera_de_sandbox(tmp_path):
    with pytest.raises(fsops.OutsideSandbox):
        fsops.sha256_file([tmp_path], "C:\\Windows\\notepad.exe")


def test_copy_file_copia_no_destructivo(tmp_path):
    src = tmp_path / "orig.bin"
    src.write_bytes(b"\x00\x01datos")
    dst = tmp_path / "dest" / "copia.bin"
    out = fsops.copy_file([tmp_path], str(src), str(dst))
    assert out == dst.resolve()
    assert dst.read_bytes() == b"\x00\x01datos"
    assert src.exists()  # no destructivo


def test_copy_file_rechaza_destino_fuera(tmp_path):
    src = tmp_path / "orig.bin"
    src.write_bytes(b"x")
    with pytest.raises(fsops.OutsideSandbox):
        fsops.copy_file([tmp_path], str(src), str(tmp_path / ".." / "fuera.bin"))


def test_copy_tree_v2_recursivo(tmp_path):
    z = _zonas(tmp_path)
    src = tmp_path / "arbol"
    (src / "a").mkdir(parents=True)
    (src / "a" / "f.txt").write_text("hola", encoding="utf-8")
    dst = tmp_path / "copia_arbol"
    out = fsops.copy_tree_v2([tmp_path], z, FakeOracle(), str(src), str(dst))
    assert out == [dst.resolve() / "a" / "f.txt"]
    assert (dst / "a" / "f.txt").read_text(encoding="utf-8") == "hola"


def test_copy_tree_v2_rechaza_destino_fuera(tmp_path):
    z = _zonas(tmp_path)
    src = tmp_path / "arbol"
    (src).mkdir(parents=True)
    (src / "f.txt").write_text("hola", encoding="utf-8")
    with pytest.raises(fsops.OutsideSandbox):
        fsops.copy_tree_v2(
            [tmp_path], z, FakeOracle(), str(src), str(tmp_path / ".." / "fuera")
        )


def test_write_text_file_atomico(tmp_path):
    z = _zonas(tmp_path)
    f = tmp_path / "01_Procesado" / "nota.md"
    fsops.write_text_file([tmp_path], z, str(f), "hola")
    assert f.read_text(encoding="utf-8") == "hola"


def test_write_text_file_respeta_00input(tmp_path):
    z = _zonas(tmp_path)
    f = tmp_path / "00_Input" / "depositado.txt"
    fsops.write_text_file([tmp_path], z, str(f), "v1")       # crear-nuevo: ok
    with pytest.raises(TierViolation):
        fsops.write_text_file([tmp_path], z, str(f), "v2")   # sobrescribir: no


def test_edit_text_file_unica_aparicion(tmp_path):
    z = _zonas(tmp_path)
    f = tmp_path / "doc.md"
    f.write_text("a b a", encoding="utf-8")
    with pytest.raises(ValueError):
        fsops.edit_text_file([tmp_path], z, str(f), "a", "z")   # 2 apariciones
    fsops.edit_text_file([tmp_path], z, str(f), "b", "z")
    assert f.read_text(encoding="utf-8") == "a z a"


def test_edit_text_file_rechaza_inexistente(tmp_path):
    z = _zonas(tmp_path)
    f = tmp_path / "no_existe.md"
    with pytest.raises(FileNotFoundError):
        fsops.edit_text_file([tmp_path], z, str(f), "a", "z")


def test_copy_file_v2_sobrescribe_via_tmp_y_replace(tmp_path):
    z = _zonas(tmp_path)
    src = tmp_path / "orig.bin"
    src.write_bytes(b"nuevo")
    dst = tmp_path / "dest.bin"
    dst.write_bytes(b"viejo")
    out = fsops.copy_file_v2([tmp_path], z, str(src), str(dst))
    assert out == dst.resolve()
    assert dst.read_bytes() == b"nuevo"


def test_copy_tree_v2_poda_y_aborta(tmp_path):
    z = _zonas(tmp_path)
    src = tmp_path / "src"
    (src / "90_Notas personales").mkdir(parents=True)
    (src / "doc.txt").write_text("x", encoding="utf-8")
    (src / "90_Notas personales" / "s.txt").write_text("p", encoding="utf-8")
    dst = tmp_path / "dst"
    copiados = fsops.copy_tree_v2([tmp_path], z, FakeOracle(), str(src), str(dst))
    assert (dst / "doc.txt").exists()
    assert not (dst / "90_Notas personales").exists()          # podado
    # destino que cae en 00_Input existente -> aborto TOTAL sin copiar nada
    dst2 = tmp_path / "00_Input"
    (dst2).mkdir()
    (dst2 / "doc.txt").write_text("orig", encoding="utf-8")
    with pytest.raises(TierViolation):
        fsops.copy_tree_v2([tmp_path], z, FakeOracle(), str(src), str(dst2))
    assert (dst2 / "doc.txt").read_text(encoding="utf-8") == "orig"  # intacto


def test_copy_tree_v2_aborto_multifichero_no_copia_nada(tmp_path):
    """Si UN destino viola Tier 1, NINGÚN fichero (ni los válidos) se copia."""
    z = _zonas(tmp_path)
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.txt").write_text("a", encoding="utf-8")
    (src / "b.txt").write_text("b", encoding="utf-8")
    dst = tmp_path / "00_Input"
    dst.mkdir()
    (dst / "b.txt").write_text("orig", encoding="utf-8")  # sobrescribir en Tier 1: violación
    with pytest.raises(TierViolation):
        fsops.copy_tree_v2([tmp_path], z, FakeOracle(), str(src), str(dst))
    assert not (dst / "a.txt").exists()  # el válido TAMPOCO se copió (dos pasadas)
    assert (dst / "b.txt").read_text(encoding="utf-8") == "orig"


def test_copy_tree_v2_aborta_arbol_frio(tmp_path, monkeypatch):
    from plugins.expedientes_xl.guards import FileNotHydrated

    class ColdOracle:
        def status(self, p):
            return "COLD"

        def subtree_cold_stats(self, p):
            return (100, 100)

    monkeypatch.setenv("XL_TREE_MAX_COLD", "50")
    z = _zonas(tmp_path)
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.txt").write_text("a", encoding="utf-8")
    dst = tmp_path / "dst"
    with pytest.raises(FileNotHydrated):
        fsops.copy_tree_v2([tmp_path], z, ColdOracle(), str(src), str(dst))
    assert not dst.exists()  # nada copiado


def test_copy_file_v2_rechaza_origen_tier0(tmp_path):
    z = _zonas(tmp_path)
    src = tmp_path / "90_Notas personales" / "s.txt"
    src.parent.mkdir(parents=True)
    src.write_text("privado", encoding="utf-8")
    with pytest.raises(TierViolation):
        fsops.copy_file_v2([tmp_path], z, str(src), str(tmp_path / "out.txt"))
    assert not (tmp_path / "out.txt").exists()


def test_copy_file_v2_rechaza_destino_backup(tmp_path):
    z = _zonas(tmp_path)
    src = tmp_path / "orig.txt"
    src.write_text("x", encoding="utf-8")
    dst = tmp_path / "Otros ordenadores" / "copia.txt"
    with pytest.raises(TierViolation):
        fsops.copy_file_v2([tmp_path], z, str(src), str(dst))
    assert not dst.exists()


def test_copy_file_v2_rechaza_gsheet(tmp_path):
    from plugins.expedientes_xl.guards import GDocBloqueado

    z = _zonas(tmp_path)
    src = tmp_path / "hoja.gsheet"
    src.write_text("{}", encoding="utf-8")
    with pytest.raises(GDocBloqueado):
        fsops.copy_file_v2([tmp_path], z, str(src), str(tmp_path / "copia.gsheet"))
    assert not (tmp_path / "copia.gsheet").exists()


def test_copy_tree_v2_omite_gdoc_y_lo_audita(tmp_path, monkeypatch):
    import json

    audit_log = tmp_path / "xl_audit.jsonl"
    monkeypatch.setenv("XL_AUDIT_PATH", str(audit_log))
    z = _zonas(tmp_path)
    src = tmp_path / "src"
    src.mkdir()
    (src / "doc.txt").write_text("x", encoding="utf-8")
    (src / "hoja.gsheet").write_text("{}", encoding="utf-8")
    dst = tmp_path / "dst"
    copiados = fsops.copy_tree_v2([tmp_path], z, FakeOracle(), str(src), str(dst))
    assert (dst / "doc.txt").exists()
    assert not (dst / "hoja.gsheet").exists()          # stub omitido, no viaja
    assert copiados == [dst.resolve() / "doc.txt"]
    eventos = [json.loads(l) for l in audit_log.read_text(encoding="utf-8").splitlines()]
    assert any(
        e["op"] == "copy_tree_v2" and e["resultado"] == "omitido_gdoc"
        and e["ruta"].endswith("hoja.gsheet")
        for e in eventos
    )  # sin silencios: la omisión queda auditada


def _zip_bytes(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


def test_extract_archive_extrae_estructura(tmp_path):
    archive = tmp_path / "e.zip"
    archive.write_bytes(_zip_bytes({"a/f.txt": b"uno", "g.txt": b"dos"}))
    dest = tmp_path / "out"
    out = fsops.extract_archive([tmp_path], str(archive), str(dest))
    assert (dest / "a" / "f.txt").read_bytes() == b"uno"
    assert (dest / "g.txt").read_bytes() == b"dos"
    assert sorted(p.name for p in out) == ["f.txt", "g.txt"]


def test_extract_archive_descarta_miembro_traversal(tmp_path):
    archive = tmp_path / "mal.zip"
    archive.write_bytes(_zip_bytes({"../escape.txt": b"malo", "ok.txt": b"bien"}))
    dest = tmp_path / "out"
    out = fsops.extract_archive([tmp_path], str(archive), str(dest))
    assert (tmp_path / "escape.txt").exists() is False  # no escapó
    assert (dest / "ok.txt").read_bytes() == b"bien"
    assert [p.name for p in out] == ["ok.txt"]


def test_write_base64_escribe_binario(tmp_path):
    data = b"\x89PNG\r\n\x1a\n binario"
    b64 = base64.b64encode(data).decode("ascii")
    dst = tmp_path / "img.png"
    n = fsops.write_base64([tmp_path], str(dst), b64, max_bytes=1000)
    assert n == len(data)
    assert dst.read_bytes() == data


def test_write_base64_rechaza_sobre_tope(tmp_path):
    data = b"x" * 200
    b64 = base64.b64encode(data).decode("ascii")
    with pytest.raises(fsops.TooLarge):
        fsops.write_base64([tmp_path], str(tmp_path / "big.bin"), b64, max_bytes=100)


def test_append_text_crea_y_anexa(tmp_path):
    dst = tmp_path / "log.jsonl"
    fsops.append_text([tmp_path], str(dst), '{"a":1}\n')
    fsops.append_text([tmp_path], str(dst), '{"b":2}\n')
    assert dst.read_text(encoding="utf-8") == '{"a":1}\n{"b":2}\n'


def test_append_text_rechaza_fuera(tmp_path):
    with pytest.raises(fsops.OutsideSandbox):
        fsops.append_text([tmp_path], str(tmp_path / ".." / "x.txt"), "y")


def _tar_bytes(entries: dict[str, bytes]) -> bytes:
    import io as _io
    buf = _io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        for name, data in entries.items():
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            tf.addfile(info, _io.BytesIO(data))
    return buf.getvalue()


def test_extract_archive_tar_extrae(tmp_path):
    archive = tmp_path / "e.tar"
    archive.write_bytes(_tar_bytes({"a/f.txt": b"uno", "g.txt": b"dos"}))
    dest = tmp_path / "out"
    out = fsops.extract_archive([tmp_path], str(archive), str(dest))
    assert (dest / "a" / "f.txt").read_bytes() == b"uno"
    assert sorted(p.name for p in out) == ["f.txt", "g.txt"]


def test_extract_archive_tar_descarta_traversal(tmp_path):
    archive = tmp_path / "mal.tar"
    archive.write_bytes(_tar_bytes({"../escape.txt": b"malo", "ok.txt": b"bien"}))
    dest = tmp_path / "out"
    out = fsops.extract_archive([tmp_path], str(archive), str(dest))
    assert (tmp_path / "escape.txt").exists() is False
    assert [p.name for p in out] == ["ok.txt"]


def test_extract_archive_zip_bomb_supera_tope(tmp_path):
    archive = tmp_path / "bomb.zip"
    archive.write_bytes(_zip_bytes({"big.bin": b"A" * 5000}))
    dest = tmp_path / "out"
    with pytest.raises(fsops.TooLarge):
        fsops.extract_archive([tmp_path], str(archive), str(dest), max_total_bytes=1000)


def test_extract_archive_member_filter_omite_sin_abortar_el_resto(tmp_path):
    archive = tmp_path / "e.zip"
    archive.write_bytes(_zip_bytes({"a.txt": b"uno", "b.txt": b"dos"}))
    dest = tmp_path / "out"
    omitidos = []

    def _filtro(name, _dest):
        if name == "a.txt":
            omitidos.append(name)
            return False
        return True

    out = fsops.extract_archive([tmp_path], str(archive), str(dest), member_filter=_filtro)
    assert omitidos == ["a.txt"]
    assert not (dest / "a.txt").exists()
    assert (dest / "b.txt").read_bytes() == b"dos"
    assert [p.name for p in out] == ["b.txt"]


def test_extract_archive_no_es_archivo(tmp_path):
    f = tmp_path / "plano.txt"
    f.write_text("no soy archivo", encoding="utf-8")
    with pytest.raises(ValueError):
        fsops.extract_archive([tmp_path], str(f), str(tmp_path / "out"))


def test_resolve_within_rechaza_nulo(tmp_path):
    with pytest.raises(fsops.OutsideSandbox):
        fsops.resolve_within([tmp_path], str(tmp_path / "f\x00.txt"))


def test_resolve_within_multi_allowed_dir(tmp_path):
    a = tmp_path / "A"
    b = tmp_path / "B"
    a.mkdir()
    b.mkdir()
    target = b / "x.txt"
    assert fsops.resolve_within([a, b], str(target)) == target.resolve()


def test_write_base64_acepta_wrapped(tmp_path):
    import base64 as _b64
    data = b"binario de prueba" * 10
    wrapped = "\n".join(
        _b64.b64encode(data).decode("ascii")[i : i + 8]
        for i in range(0, len(_b64.b64encode(data).decode("ascii")), 8)
    )
    dst = tmp_path / "w.bin"
    n = fsops.write_base64([tmp_path], str(dst), wrapped, max_bytes=10000)
    assert n == len(data)
    assert dst.read_bytes() == data


def test_write_base64_frontera_exacta(tmp_path):
    import base64 as _b64
    data = b"x" * 100
    b64 = _b64.b64encode(data).decode("ascii")
    # exactamente en el tope: permitido
    assert fsops.write_base64([tmp_path], str(tmp_path / "ok.bin"), b64, max_bytes=100) == 100
    # uno por encima: rechazado
    data2 = b"x" * 101
    b64_2 = _b64.b64encode(data2).decode("ascii")
    with pytest.raises(fsops.TooLarge):
        fsops.write_base64([tmp_path], str(tmp_path / "no.bin"), b64_2, max_bytes=100)


def test_hash_tree_mapea_relpath_posix_a_sha(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "a.txt").write_bytes(b"hola")
    (tmp_path / "sub" / "b.txt").write_bytes(b"mundo")
    out = fsops.hash_tree([tmp_path], str(tmp_path))
    assert out == {
        "a.txt": hashlib.sha256(b"hola").hexdigest(),
        "sub/b.txt": hashlib.sha256(b"mundo").hexdigest(),
    }


def test_hash_tree_salta_directorios_y_root_inexistente(tmp_path):
    vacio = tmp_path / "vacia"
    vacio.mkdir()
    assert fsops.hash_tree([tmp_path], str(vacio)) == {}


def test_hash_tree_rechaza_fuera_de_sandbox(tmp_path):
    with pytest.raises(fsops.OutsideSandbox):
        fsops.hash_tree([tmp_path], "C:\\Windows")


def _make_zip(path, names_to_bytes):
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in names_to_bytes.items():
            zf.writestr(name, data)


def test_extract_strip_top_level_quita_wrapper(tmp_path):
    z = tmp_path / "export.zip"
    _make_zip(z, {"Wrapper/ACTIVACION/hoja.pdf": b"A", "Wrapper/oferta.pdf": b"B"})
    dest = tmp_path / "out"
    extracted = fsops.extract_archive([tmp_path], str(z), str(dest), strip_top_level=True)
    rels = sorted(p.relative_to(dest.resolve()).as_posix() for p in extracted)
    assert rels == ["ACTIVACION/hoja.pdf", "oferta.pdf"]


def test_extract_sin_strip_conserva_wrapper(tmp_path):
    z = tmp_path / "export.zip"
    _make_zip(z, {"Wrapper/ACTIVACION/hoja.pdf": b"A"})
    dest = tmp_path / "out"
    extracted = fsops.extract_archive([tmp_path], str(z), str(dest))
    rels = [p.relative_to(dest.resolve()).as_posix() for p in extracted]
    assert rels == ["Wrapper/ACTIVACION/hoja.pdf"]


def test_extract_strip_no_actua_con_multiples_raices(tmp_path):
    z = tmp_path / "export.zip"
    _make_zip(z, {"A/x.pdf": b"1", "B/y.pdf": b"2"})
    dest = tmp_path / "out"
    extracted = fsops.extract_archive([tmp_path], str(z), str(dest), strip_top_level=True)
    rels = sorted(p.relative_to(dest.resolve()).as_posix() for p in extracted)
    assert rels == ["A/x.pdf", "B/y.pdf"]  # sin único wrapper → no se toca


def test_extract_strip_no_actua_con_fichero_en_raiz(tmp_path):
    z = tmp_path / "export.zip"
    _make_zip(z, {"suelto.pdf": b"1", "Wrapper/x.pdf": b"2"})
    dest = tmp_path / "out"
    extracted = fsops.extract_archive([tmp_path], str(z), str(dest), strip_top_level=True)
    rels = sorted(p.relative_to(dest.resolve()).as_posix() for p in extracted)
    assert rels == ["Wrapper/x.pdf", "suelto.pdf"]  # hay fichero en raíz → no hay wrapper único


def test_extract_strip_top_level_sigue_rechazando_traversal(tmp_path):
    z = tmp_path / "malicioso.zip"
    _make_zip(z, {"Wrapper/ok.txt": b"ok", "Wrapper/../escape.txt": b"bad"})
    dest = tmp_path / "out"
    extracted = fsops.extract_archive([tmp_path], str(z), str(dest), strip_top_level=True)
    rels = sorted(p.relative_to(dest.resolve()).as_posix() for p in extracted)
    assert rels == ["ok.txt"]                      # el miembro con .. se descarta
    assert not (tmp_path / "escape.txt").exists()  # nada escapó del sandbox


def test_hash_tree_salta_symlinks(tmp_path):
    (tmp_path / "real.txt").write_bytes(b"real")
    secreto = tmp_path.parent / "secreto_fuera.txt"
    secreto.write_bytes(b"secreto")
    link = tmp_path / "link.txt"
    try:
        link.symlink_to(secreto)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks no disponibles (Windows sin privilegio)")
    out = fsops.hash_tree([tmp_path], str(tmp_path))
    assert "link.txt" not in out          # el symlink no se hashea/lista
    assert out == {"real.txt": hashlib.sha256(b"real").hexdigest()}
