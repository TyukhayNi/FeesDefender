import base64
import hashlib
import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from plugins.expedientes_xl import fsops


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


def test_copy_tree_recursivo(tmp_path):
    src = tmp_path / "arbol"
    (src / "a").mkdir(parents=True)
    (src / "a" / "f.txt").write_text("hola", encoding="utf-8")
    dst = tmp_path / "copia_arbol"
    out = fsops.copy_tree([tmp_path], str(src), str(dst))
    assert out == dst.resolve()
    assert (dst / "a" / "f.txt").read_text(encoding="utf-8") == "hola"


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


def test_delete_path_borra_dentro(tmp_path):
    f = tmp_path / "borrame.txt"
    f.write_text("x", encoding="utf-8")
    fsops.delete_path([tmp_path], str(f))
    assert f.exists() is False


def test_delete_path_rechaza_fuera(tmp_path):
    with pytest.raises(fsops.OutsideSandbox):
        fsops.delete_path([tmp_path], "C:\\Windows\\system32")


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


def test_delete_path_rechaza_raiz_sandbox(tmp_path):
    with pytest.raises(fsops.OutsideSandbox):
        fsops.delete_path([tmp_path], str(tmp_path))


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
