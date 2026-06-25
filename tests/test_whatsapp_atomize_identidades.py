import textwrap

from core.whatsapp_atomize.identidades import cargar_identidades_wa


def _escribir_yaml(case_dir):
    (case_dir / "identidades.yaml").write_text(textwrap.dedent("""
        personas:
          - id: prop
            nombre: Juan Propietario
            rol: propietario
            direcciones:
              - {email: juan@ej.com, estado: confirmada}
            identificadores:
              - {valor: "+34600111222", estado: confirmada}
              - {valor: "Juan", estado: candidata}
    """), encoding="utf-8")


def test_resuelve_por_identificador(tmp_path):
    _escribir_yaml(tmp_path)
    mapa = cargar_identidades_wa(tmp_path)
    assert mapa["+34600111222"] == ("prop", "Juan Propietario", "propietario")
    assert mapa["juan"] == ("prop", "Juan Propietario", "propietario")  # normaliza a lower


def test_sin_yaml_mapa_vacio(tmp_path):
    assert cargar_identidades_wa(tmp_path) == {}


def test_email_atomize_ignora_identificadores(tmp_path):
    """No-regresión: el cargador de email no peta con el campo nuevo."""
    _escribir_yaml(tmp_path)
    from core.email_atomize.identidades import cargar_identidades
    ids = cargar_identidades(tmp_path)
    assert ids.persona_de("juan@ej.com") == "prop"   # lee direcciones, ignora identificadores
