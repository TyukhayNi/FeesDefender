from __future__ import annotations

import pytest

from core.email_atomize import identidades as ID


_YAML_PILOTO = """
version: 1
caso: "W-02VND1"
personas:
  - id: persona_uno
    nombre: "PersonaUno"
    vigilada: true
    rol: "tesis: administrador de hecho"
    direcciones:
      - { email: per01a@example.invalid,            estado: confirmada }
      - { email: per01c@example.invalid,                 estado: confirmada }
      - { email: per01b@example.invalid,  estado: candidata }
  - id: persona_dos
    nombre: "PersonaDos"
    vigilada: false
    direcciones:
      - { email: ignacio@despacho-ab.example, estado: confirmada }
    notas: "PERSONA DISTINTA — nunca fundir."
"""


def test_carga_piloto_sets_derivados(tmp_path):
    (tmp_path / "identidades.yaml").write_text(_YAML_PILOTO, encoding="utf-8")
    ident = ID.cargar_identidades(tmp_path)
    # vigiladas = confirmadas de personas vigiladas (email en minúsculas)
    assert ident.vigiladas == frozenset({"per01a@example.invalid", "per01c@example.invalid"})
    # candidatas = estado candidata
    assert ident.candidatas == frozenset({"per01b@example.invalid"})
    # Ignacio NO es vigilado → su email no entra en vigiladas
    assert "ignacio@despacho-ab.example" not in ident.vigiladas


def test_unificacion_y_persona_distinta(tmp_path):
    (tmp_path / "identidades.yaml").write_text(_YAML_PILOTO, encoding="utf-8")
    ident = ID.cargar_identidades(tmp_path)
    # unificación: las 3 direcciones cuelgan de la misma persona
    assert ident.persona_de("per01a@example.invalid") == "persona_uno"
    assert ident.persona_de("per01c@example.invalid") == "persona_uno"
    assert ident.persona_de("per01b@example.invalid") == "persona_uno"
    # persona DISTINTA: nunca se funde con PersonaUno
    assert ident.persona_de("ignacio@despacho-ab.example") == "persona_dos"
    assert ident.estado_de("per01b@example.invalid") == "candidata"


def test_sin_fichero_es_generico(tmp_path):
    ident = ID.cargar_identidades(tmp_path)   # no hay identidades.yaml
    assert ident.vigiladas == frozenset()
    assert ident.candidatas == frozenset()
    assert ident.persona_de("per01a@example.invalid") is None


def test_email_en_dos_personas_es_error(tmp_path):
    yml = """
personas:
  - id: a
    vigilada: false
    direcciones: [ { email: x@y.com, estado: confirmada } ]
  - id: b
    vigilada: false
    direcciones: [ { email: x@y.com, estado: confirmada } ]
"""
    (tmp_path / "identidades.yaml").write_text(yml, encoding="utf-8")
    with pytest.raises(ValueError):
        ID.cargar_identidades(tmp_path)


def test_estado_invalido_es_error(tmp_path):
    yml = """
personas:
  - id: a
    vigilada: true
    direcciones: [ { email: x@y.com, estado: dudosa } ]
"""
    (tmp_path / "identidades.yaml").write_text(yml, encoding="utf-8")
    with pytest.raises(ValueError):
        ID.cargar_identidades(tmp_path)
