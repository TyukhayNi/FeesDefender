# -*- coding: utf-8 -*-
"""Tests del helper canónico de registro ``.claude/skills/_shared/registrar_outputs.py``.

Cubre (plan v3 §14): idempotencia, _caso.md ausente, creación de Navegación,
rechazo de ``90_Notas personales``, destino inválido, escritura atómica UTF-8,
subcarpeta de jurisprudencia, wikilink por defecto y serialización de meta.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_HELPER = (
    Path(__file__).resolve().parents[1]
    / ".claude" / "skills" / "_shared" / "registrar_outputs.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("registrar_outputs_shared", _HELPER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ro = _load()


# --- helpers de fixture -----------------------------------------------------

def _case_con_caso_md(tmp_path: Path) -> Path:
    case = tmp_path / "W-EJEMPLO"
    (case / "00_Input").mkdir(parents=True)
    (case / "00_Input" / "_caso.md").write_text(
        "---\n"
        "case_id: W-EJEMPLO\n"
        "tipo: caso_index\n"
        "---\n\n"
        "# W-EJEMPLO\n\n"
        "## Navegación\n\n"
        "- [[viabilidad]]\n",
        encoding="utf-8",
    )
    return case


def _out(fichero="DEMANDA_W-EJEMPLO.docx", **kw):
    base = {
        "fichero": fichero,
        "tipo": "demanda",
        "perspectiva": "actora",
        "destino": "05_Procedimiento",
        "fuentes": ["informe_viabilidad", "encargo"],
        "estado": "borrador",
    }
    base.update(kw)
    return base


# --- tests ------------------------------------------------------------------

def test_registro_basico_crea_manifiesto_y_navegacion(tmp_path):
    case = _case_con_caso_md(tmp_path)
    assert ro.registrar(str(case), [_out()]) == 0

    manifest = case / "05_Procedimiento" / "_index.md"
    assert manifest.exists()
    texto = manifest.read_text(encoding="utf-8")
    assert "DEMANDA_W-EJEMPLO.docx" in texto
    assert "| demanda |" in texto
    assert "informe_viabilidad; encargo" in texto

    caso = (case / "00_Input" / "_caso.md").read_text(encoding="utf-8")
    assert "[[DEMANDA_W-EJEMPLO]]" in caso  # wikilink = stem por defecto
    assert "[[viabilidad]]" in caso          # preexistente intacto


def test_idempotente_no_duplica(tmp_path):
    case = _case_con_caso_md(tmp_path)
    ro.registrar(str(case), [_out()])
    ro.registrar(str(case), [_out()])  # segunda vez

    manifest = (case / "05_Procedimiento" / "_index.md").read_text(encoding="utf-8")
    assert manifest.count("DEMANDA_W-EJEMPLO.docx") == 1
    caso = (case / "00_Input" / "_caso.md").read_text(encoding="utf-8")
    assert caso.count("[[DEMANDA_W-EJEMPLO]]") == 1


def test_caso_md_ausente_modo_adhoc(tmp_path, capsys):
    case = tmp_path / "carpeta_suelta"
    case.mkdir()
    rc = ro.registrar(str(case), [_out()])
    assert rc == 0  # no es error: es modo ad-hoc
    assert (case / "05_Procedimiento" / "_index.md").exists()
    err = capsys.readouterr().err
    assert "ad-hoc" in err


def test_crea_navegacion_si_falta(tmp_path):
    case = tmp_path / "W-SIN-NAV"
    (case / "00_Input").mkdir(parents=True)
    (case / "00_Input" / "_caso.md").write_text(
        "---\ncase_id: W-SIN-NAV\n---\n\n# W-SIN-NAV\n\nCuerpo sin navegación.\n",
        encoding="utf-8",
    )
    ro.registrar(str(case), [_out()])
    caso = (case / "00_Input" / "_caso.md").read_text(encoding="utf-8")
    assert "## Navegación" in caso
    assert "[[DEMANDA_W-EJEMPLO]]" in caso


def test_rechaza_destino_90(tmp_path):
    case = _case_con_caso_md(tmp_path)
    with pytest.raises(ValueError, match="prohibido"):
        ro.registrar(str(case), [_out(destino="90_Notas personales")])
    # No debe haber escrito nada en 90.
    assert not (case / "90_Notas personales").exists()


def test_rechaza_destino_invalido(tmp_path):
    case = _case_con_caso_md(tmp_path)
    with pytest.raises(ValueError, match="no válido"):
        ro.registrar(str(case), [_out(destino="99_Inventado")])


def test_jurisprudencia_subcarpeta(tmp_path):
    case = _case_con_caso_md(tmp_path)
    out = _out(
        fichero="STS_1234_2025.pdf",
        tipo="jurisprudencia",
        perspectiva="",
        destino="05_Procedimiento/Jurisprudencia",
        fuentes=["ROJ: STS 1234/2025"],
        meta={"ecli": "ECLI:ES:TS:2025:1234"},
    )
    ro.registrar(str(case), [out])
    manifest = case / "05_Procedimiento" / "Jurisprudencia" / "_index.md"
    assert manifest.exists()
    texto = manifest.read_text(encoding="utf-8")
    assert "STS_1234_2025.pdf" in texto
    assert "ROJ: STS 1234/2025" in texto
    assert "ecli=ECLI:ES:TS:2025:1234" in texto


def test_no_toca_frontmatter(tmp_path):
    case = _case_con_caso_md(tmp_path)
    antes = (case / "00_Input" / "_caso.md").read_text(encoding="utf-8")
    fm_antes = antes.split("---", 2)[1]
    ro.registrar(str(case), [_out()])
    despues = (case / "00_Input" / "_caso.md").read_text(encoding="utf-8")
    fm_despues = despues.split("---", 2)[1]
    assert fm_antes == fm_despues


def test_escritura_utf8_sin_bom(tmp_path):
    case = _case_con_caso_md(tmp_path)
    ro.registrar(str(case), [_out(fichero="DEMANDA_ÑOÑO.docx")])
    raw = (case / "05_Procedimiento" / "_index.md").read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")  # sin BOM
    assert "ÑOÑO".encode("utf-8") in raw


def test_falta_fichero_es_error(tmp_path):
    case = _case_con_caso_md(tmp_path)
    with pytest.raises(ValueError, match="fichero"):
        ro.registrar(str(case), [{"tipo": "demanda", "destino": "05_Procedimiento"}])


def test_main_argv_incorrecto():
    assert ro.main(["registrar_outputs.py"]) == 2
