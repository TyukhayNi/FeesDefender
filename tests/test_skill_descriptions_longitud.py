# tests/test_skill_descriptions_longitud.py
"""Cowork/claude.ai rechaza importar una skill cuya `description` pase de 1024
caracteres. Le pasó a `engel-volkers` el 2026-09-14: 1410 caracteres, y el fallo
no apareció al empaquetar sino al importar, con los tres `.skill` ya entregados.

`scripts/validate_skills.py:94` **ya medía** este límite — y lo emitía como *aviso*,
que es un grito que nadie tenía que escuchar. Su aviso hermano, el de las etiquetas
XML, sí tiene test duro (`test_skill_descriptions_no_xml.py`) porque rompió una
importación en el PR #54. Misma consecuencia, mismo bloque de código, y solo uno
vigilado: se remedió el ejemplo y no la frontera —«lo que hace que Cowork rechace
la importación»—. Este test cierra la otra mitad.

El límite se cuenta en CARACTERES, no en bytes: `organizar-sala-lectura` se importó
con 1022 caracteres / 1031 bytes UTF-8 (medido el 2026-09-14 contra el espejo de lo
instalado).
"""
from __future__ import annotations

from pathlib import Path

import yaml

_SKILLS = Path(__file__).resolve().parents[1] / ".claude" / "skills"
_GENERICAS = {"docx", "pdf", "xlsx", "pptx"}  # de Anthropic: no las mantenemos nosotros
_LIMITE = 1024


def _skill_dirs() -> list[Path]:
    return [
        d for d in sorted(_SKILLS.iterdir())
        if d.is_dir() and not d.name.startswith("_")
        and d.name not in _GENERICAS and (d / "SKILL.md").exists()
    ]


def _description(texto: str) -> str:
    if not texto.startswith("---"):
        return ""
    fm = yaml.safe_load(texto.split("---", 2)[1]) or {}
    return str(fm.get("description", ""))


def test_ninguna_description_supera_el_limite_de_cowork():
    ofensores = {}
    for d in _skill_dirs():
        n = len(_description((d / "SKILL.md").read_text(encoding="utf-8")))
        if n > _LIMITE:
            ofensores[d.name] = f"{n} chars (+{n - _LIMITE})"
    assert not ofensores, (
        f"descriptions > {_LIMITE} caracteres; Cowork rechaza su importación: {ofensores}"
    )


def test_el_limite_se_cuenta_en_caracteres_no_en_bytes():
    """Una description de 1024 caracteres con tildes pasa de 1024 bytes UTF-8 y aun
    así se importa. Si alguien 'arregla' el guard midiendo bytes, este test lo para."""
    desc = "á" * _LIMITE
    assert len(desc) == _LIMITE
    assert len(desc.encode("utf-8")) > _LIMITE


def test_validador_avisa_de_description_demasiado_larga(tmp_path):
    """El validador local debe pillar lo que Cowork rechaza, para verlo antes de
    empaquetar en vez de al importar."""
    import scripts.validate_skills as vs

    skill = tmp_path / "mi-skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\n"
        "name: mi-skill\n"
        f'description: "{"x" * (_LIMITE + 1)}"\n'
        'license: "X"\n'
        "metadata:\n"
        "  rol: input\n"
        "  naturaleza: atomica\n"
        '  version: "1.0"\n'
        "---\n"
        "cuerpo\n",
        encoding="utf-8",
    )
    avisos = vs.validar_skill(skill, vs._canonical_helpers(), vs._operacion_dirs())
    assert any(str(_LIMITE) in a and "description" in a for a in avisos), avisos


def test_validador_no_avisa_cuando_la_description_cabe(tmp_path):
    """Control: el aviso anterior no puede ser un grito constante — si lo fuera, no
    distinguiría la skill que Cowork rechaza de la que acepta."""
    import scripts.validate_skills as vs

    skill = tmp_path / "otra-skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\n"
        "name: otra-skill\n"
        f'description: "{"x" * _LIMITE}"\n'
        'license: "X"\n'
        "metadata:\n"
        "  rol: input\n"
        "  naturaleza: atomica\n"
        '  version: "1.0"\n'
        "---\n"
        "cuerpo\n",
        encoding="utf-8",
    )
    avisos = vs.validar_skill(skill, vs._canonical_helpers(), vs._operacion_dirs())
    assert not any("> 1024" in a for a in avisos), avisos
