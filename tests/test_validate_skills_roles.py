# tests/test_validate_skills_roles.py
"""Red anti-regresión de la taxonomía de roles de skills (decisión 2026-07-18).

El eje `rol` nació desde la óptica del trabajo jurídico; el ecosistema creció una
familia de skills de PIPELINE DE DATOS (entrada → procesado) que no cabía en los
4 roles originales. Se añadieron `input` (entrada de datos crudos, simétrico de
`output`) y `procesado` (transforma intake en artefactos internos). Estos tests
fijan ese vocabulario para que nadie lo retire por descuido — el validador es
modo aviso y no lo protege ningún gate.
"""
from __future__ import annotations


def test_input_y_procesado_son_roles_validos():
    import scripts.validate_skills as vs

    assert "input" in vs._ROLES
    assert "procesado" in vs._ROLES


def test_skills_del_pipeline_de_datos_declaran_rol_reconocido():
    """Las skills del pipeline de datos del expediente —entrada (`input`) y
    procesado (`procesado`)— no deben disparar el aviso `metadata.rol=... no
    válido` del validador. Cubre las 2 skills de entrada y las 2 reclasificadas
    a `procesado` en 2026-07-18."""
    import scripts.validate_skills as vs

    helpers = vs._canonical_helpers()
    operacion = vs._operacion_dirs()
    for nombre in (
        "intake-expediente",
        "exportar-correos-etiqueta",
        "organizar-sala-maquina",
        "organizar-sala-lectura",
    ):
        skill_dir = vs._SKILLS / nombre
        avisos = vs.validar_skill(skill_dir, helpers, operacion)
        rol_invalido = [a for a in avisos if "rol=" in a and "no válido" in a]
        assert not rol_invalido, f"{nombre}: {rol_invalido}"
