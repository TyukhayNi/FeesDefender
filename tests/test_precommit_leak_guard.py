"""Tests de la barrera local anti-fugas (scripts/precommit_leak_guard.py).

No usa PII real: la blocklist de prueba se fabrica en un repo temporal.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.precommit_leak_guard import cargar_blocklist, escanear


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Repo temporal con una replacements.txt sintética (literal + regex)."""
    saneado = tmp_path / "data" / "_saneado"
    saneado.mkdir(parents=True)
    (saneado / "replacements.txt").write_text(
        "Fulano Menganez==>PersonaX\n"
        "Alba==>PersonaY\n"
        r"regex:(?i)(?<![\w])Zutano\ Perez(?![\w@])==>PersonaZ" + "\n",
        encoding="utf-8",
    )
    return tmp_path


def _crea(repo: Path, rel: str, contenido: str) -> str:
    fp = repo / rel
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(contenido, encoding="utf-8")
    return rel


def test_blocklist_parsea_literal_y_regex(repo: Path):
    bl = cargar_blocklist(repo)
    assert "Fulano Menganez" in bl
    assert "Alba" in bl
    assert "Zutano Perez" in bl  # regex desenvuelto


def test_fichero_limpio_no_dispara(repo: Path):
    r = _crea(repo, "doc.md", "Reclamacion de honorarios W-02VND1, todo correcto.")
    assert escanear([r], repo) == []


def test_pii_literal_en_contenido_bloquea(repo: Path):
    r = _crea(repo, "nota.md", "Contrato firmado por Fulano Menganez el lunes.")
    problemas = escanear([r], repo)
    assert any("Fulano Menganez" in p for p in problemas)


def test_pii_regex_en_contenido_bloquea(repo: Path):
    r = _crea(repo, "acta.txt", "Declaro que Zutano Perez compareció.")
    problemas = escanear([r], repo)
    assert any("Zutano Perez" in p for p in problemas)


def test_limite_de_palabra_evita_falso_positivo(repo: Path):
    # 'Albacete' NO debe casar con el termino 'Alba'.
    r = _crea(repo, "viaje.md", "Fuimos a Albacete en verano.")
    assert escanear([r], repo) == []


def test_ruta_har_vetada_aunque_no_exista(repo: Path):
    problemas = escanear(["docs/captura/sesion.har"], repo)
    assert any("RUTA VETADA" in p for p in problemas)


def test_ruta_descubrimiento_vetada(repo: Path):
    r = _crea(repo, "docs/_descubrimiento/dump.json", "{}")
    problemas = escanear([r], repo)
    assert any("RUTA VETADA" in p for p in problemas)


def test_binario_no_se_escanea(repo: Path):
    fp = repo / "img.bin"
    fp.write_bytes(b"\x00\x01Fulano Menganez\x00")
    assert escanear(["img.bin"], repo) == []


def test_sin_blocklist_solo_rutas(tmp_path: Path):
    # Repo sin replacements.txt: no hay escaneo de PII, pero las rutas siguen vetadas.
    assert cargar_blocklist(tmp_path) == []
    r = _crea(tmp_path, "nota.md", "Fulano Menganez")
    assert escanear([r], tmp_path) == []  # sin blocklist, no dispara por contenido
    assert escanear(["x.har"], tmp_path)  # ruta sigue vetada
