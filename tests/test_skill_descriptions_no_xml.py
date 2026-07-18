# tests/test_skill_descriptions_no_xml.py
"""Cowork/claude.ai rechaza importar una skill cuya `description` contenga etiquetas
tipo XML (`<...>`): «SKILL.md description cannot contain XML tags». El PR #54 metió
placeholders con ángulos (`<fuente>`, `<AAAA-MM-DD>_<fuente>_<NN>`, `<caso>`) en las
descriptions de intake y rompió la importación en vivo. Este test fija el invariante
para todas las skills del despacho — el validador local no lo cubría.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

_SKILLS = Path(__file__).resolve().parents[1] / ".claude" / "skills"
_GENERICAS = {"docx", "pdf", "xlsx", "pptx"}
_TAG = re.compile(r"<[^>\s][^>]*>")


def _skill_dirs() -> list[Path]:
    return [
        d for d in sorted(_SKILLS.iterdir())
        if d.is_dir() and not d.name.startswith("_")
        and d.name not in _GENERICAS and (d / "SKILL.md").exists()
    ]


def test_ninguna_description_contiene_etiquetas_xml():
    ofensores: dict[str, list[str]] = {}
    for d in _skill_dirs():
        texto = (d / "SKILL.md").read_text(encoding="utf-8")
        if not texto.startswith("---"):
            continue
        fm = yaml.safe_load(texto.split("---", 2)[1]) or {}
        tags = _TAG.findall(str(fm.get("description", "")))
        if tags:
            ofensores[d.name] = sorted(set(tags))
    assert not ofensores, f"descriptions con etiquetas XML (Cowork las rechaza): {ofensores}"


def test_validador_avisa_de_etiquetas_xml_en_description(tmp_path):
    """El validador local debe pillar lo que Cowork rechaza, para verlo antes de
    empaquetar en vez de al importar."""
    import scripts.validate_skills as vs

    skill = tmp_path / "mi-skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        '---\n'
        'name: mi-skill\n'
        'description: "Procesa el <fuente> del expediente."\n'
        'license: "X"\n'
        'metadata:\n'
        '  rol: input\n'
        '  naturaleza: atomica\n'
        '  version: "1.0"\n'
        '---\n'
        'cuerpo\n',
        encoding="utf-8",
    )
    avisos = vs.validar_skill(skill, vs._canonical_helpers(), vs._operacion_dirs())
    assert any("XML" in a for a in avisos), avisos
