from pathlib import Path

from core.extractor import _extract_one


def test_extract_rtf(tmp_path: Path):
    p = tmp_path / "burofax.rtf"
    p.write_text(r"{\rtf1\ansi\deff0 Hola \b mundo\b0 burofax\par}", encoding="ascii")
    texto, metodo = _extract_one(p)
    assert metodo == "rtf"
    assert "Hola" in texto and "mundo" in texto and "burofax" in texto
