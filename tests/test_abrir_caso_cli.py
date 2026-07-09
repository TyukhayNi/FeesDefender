import hashlib
from pathlib import Path

from scripts import abrir_caso as cli


def test_hash_tree_local(tmp_path: Path):
    root = tmp_path / "01_Drive EV"
    (root / "sub").mkdir(parents=True)
    (root / "a.txt").write_bytes(b"hola")
    (root / "sub" / "b.txt").write_bytes(b"mundo")

    hashes = cli.hash_tree_local(root, prefijo="01_Drive EV")

    assert hashes["01_Drive EV/a.txt"] == hashlib.sha256(b"hola").hexdigest()
    assert hashes["01_Drive EV/sub/b.txt"] == hashlib.sha256(b"mundo").hexdigest()
    assert len(hashes) == 2
