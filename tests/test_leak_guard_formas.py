"""Tests del shape-detection del leak-guard (detección de PII por FORMA, no por valor).

Complementa la blocklist (valores enumerados) con detección de identificadores
estructurados de CUALQUIER caso: DNI, NIE, NIF, IBAN (bloqueo) y emails de tercero
(aviso). Reutiliza los patrones canónicos de `core/anon/anonimizar.py`.

Doctrina: docs/SEGURIDAD_DATOS.md — la blocklist es denylist (solo caza lo enumerado);
esto generaliza a expedientes que nadie ha listado aún.
"""
from __future__ import annotations

from scripts.precommit_leak_guard import escanear_formas


def test_dni_en_ruta_produccion_bloquea(tmp_path):
    (tmp_path / "dump.txt").write_text("DNI del titular: 12345678A firmado.", encoding="utf-8")
    bloqueos, avisos = escanear_formas(["dump.txt"], repo=tmp_path)
    assert any("12345678A" in b for b in bloqueos)


def test_nie_bloquea(tmp_path):
    (tmp_path / "dump.txt").write_text("NIE X1234567L del buscador.", encoding="utf-8")
    bloqueos, _ = escanear_formas(["dump.txt"], repo=tmp_path)
    assert any("X1234567L" in b for b in bloqueos)


def test_iban_bloquea(tmp_path):
    (tmp_path / "dump.txt").write_text("Cuenta ES9121000418450200051332 para el pago.", encoding="utf-8")
    bloqueos, _ = escanear_formas(["dump.txt"], repo=tmp_path)
    assert any("ES91" in b for b in bloqueos)


def test_formas_bajo_tests_no_bloquean(tmp_path):
    # tests/ es sintético por doctrina (principio 3): las fixtures del anonimizador
    # llevan DNIs/IBANs válidos por forma; no deben frenar el commit.
    d = tmp_path / "tests"
    d.mkdir()
    (d / "fixture.py").write_text("dni_falso = '12345678A'", encoding="utf-8")
    bloqueos, _ = escanear_formas(["tests/fixture.py"], repo=tmp_path)
    assert bloqueos == []


def test_anotacion_allow_exime_la_linea(tmp_path):
    (tmp_path / "health.py").write_text(
        "DNI_DEMO = '12345678A'  # leak-guard:allow (sintético)", encoding="utf-8"
    )
    bloqueos, _ = escanear_formas(["health.py"], repo=tmp_path)
    assert bloqueos == []


def test_allow_solo_exime_su_linea(tmp_path):
    (tmp_path / "mix.txt").write_text(
        "linea1 12345678A  # leak-guard:allow\nlinea2 87654321B sin exencion\n",
        encoding="utf-8",
    )
    bloqueos, _ = escanear_formas(["mix.txt"], repo=tmp_path)
    assert any("87654321B" in b for b in bloqueos)
    assert not any("12345678A" in b for b in bloqueos)


def test_formas_bajo_docs_no_bloquean(tmp_path):
    # docs/ es prosa curada con ejemplos sintéticos (doctrina: refs por W-XXXXX).
    d = tmp_path / "docs"
    d.mkdir()
    (d / "ejemplo.md").write_text("DNI de ejemplo: 12345678A", encoding="utf-8")
    bloqueos, _ = escanear_formas(["docs/ejemplo.md"], repo=tmp_path)
    assert bloqueos == []


def test_formas_bajo_claude_skills_no_bloquean(tmp_path):
    # assets de skills = ejemplos sintéticos, a menudo JSON (no admite anotación inline).
    d = tmp_path / ".claude" / "skills" / "x" / "assets"
    d.mkdir(parents=True)
    (d / "ej.json").write_text('{"dni": "00000001A"}', encoding="utf-8")
    bloqueos, _ = escanear_formas([".claude/skills/x/assets/ej.json"], repo=tmp_path)
    assert bloqueos == []


def test_ficheros_example_no_bloquean(tmp_path):
    (tmp_path / "config.yaml.example").write_text("dni_demo: 12345678A", encoding="utf-8")
    bloqueos, _ = escanear_formas(["config.yaml.example"], repo=tmp_path)
    assert bloqueos == []


def test_nif_empresa_no_bloquea(tmp_path):
    # NIF/CIF es dato público de registro mercantil, fuera del set bloqueante.
    (tmp_path / "dump.txt").write_text("Empresa con NIF B65824054 inscrita.", encoding="utf-8")
    bloqueos, _ = escanear_formas(["dump.txt"], repo=tmp_path)
    assert bloqueos == []


def test_email_de_tercero_avisa_no_bloquea(tmp_path):
    (tmp_path / "doc.md").write_text("Contacto: juan.perez@gmail.com para dudas.", encoding="utf-8")
    bloqueos, avisos = escanear_formas(["doc.md"], repo=tmp_path)
    assert bloqueos == []
    assert any("gmail.com" in a for a in avisos)


def test_email_inerte_no_avisa(tmp_path):
    (tmp_path / "doc.md").write_text(
        "Placeholders: persona@example.invalid y otro@foo.example", encoding="utf-8"
    )
    _, avisos = escanear_formas(["doc.md"], repo=tmp_path)
    assert avisos == []


def test_binario_se_ignora(tmp_path):
    (tmp_path / "blob.bin").write_bytes(b"\x00\x01 12345678A ES9121000418450200051332")
    bloqueos, avisos = escanear_formas(["blob.bin"], repo=tmp_path)
    assert bloqueos == []
    assert avisos == []
