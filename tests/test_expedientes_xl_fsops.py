import base64
import hashlib
import io
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
