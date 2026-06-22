import hashlib
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
