"""El `_ficha_crm.yaml` se lee entero o no se lee (spec rev. 3 §3, Parte A).

`yaml.safe_load` se queda con la ÚLTIMA de dos claves repetidas y no avisa: una parte entera
desaparecía antes de que existiera el diccionario que las validaciones miran (R1/H-01). Y la
R2 midió que el primer lector propuesto dejaba escapar `TypeError` y `ParserError` donde
prometía `ValueError`, y de varias repetidas decía solo la primera (R2/H-04).
"""
import re

import pytest
import yaml

from core import crm_ficha as cf


def _yaml(tmp_path, texto):
    p = tmp_path / "_ficha_crm.yaml"
    p.write_text(texto, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Task 1 — lector sin pérdida (A.1)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("texto, clave, linea, primera", [
    ("contrario: {nombre: UNO}\ncontrario: {nombre: DOS}\n", "contrario", 2, 1),   # una parte entera
    ("contrario:\n  nombre: A\n  apellido1: X\n  apellido1: Y\n", "apellido1", 4, 3),
    ("colaboradores:\n  - {nombre: A, email: a@x.es, email: b@x.es}\n", "email", 2, 2),
])
def test_R1H01_una_clave_repetida_se_rechaza_con_su_linea(tmp_path, texto, clave, linea, primera):
    with pytest.raises(ValueError) as e:
        cf.leer_yaml_ficha(_yaml(tmp_path, texto))
    assert (f"línea {linea}: la clave {clave!r} está repetida (ya en la línea {primera})"
            in str(e.value))


def test_R2H04_dos_repetidas_salen_las_dos(tmp_path):
    with pytest.raises(ValueError) as e:
        cf.leer_yaml_ficha(_yaml(tmp_path, "a: 1\na: 2\nb: 1\nb: 2\n"))
    assert "línea 2: la clave 'a'" in str(e.value) and "línea 4: la clave 'b'" in str(e.value)


@pytest.mark.parametrize("texto, forma", [("? [a, b]\n: c\n", "una lista"),
                                          ("? {a: 1}\n: c\n", "un mapping")])
def test_R2H04_una_clave_que_no_es_texto_se_rechaza_con_su_linea(tmp_path, texto, forma):
    with pytest.raises(ValueError,
                       match=f"línea 1: una clave tiene que ser un texto, y aquí es {forma}"):
        cf.leer_yaml_ficha(_yaml(tmp_path, texto))


def test_los_alias_se_rechazan_con_su_linea(tmp_path):
    with pytest.raises(ValueError, match=r"línea 1: los alias"):
        cf.leer_yaml_ficha(_yaml(tmp_path, "a: &x {nombre: A}\ncontrario: *x\n"))


def test_R2_el_merge_SIN_alias_se_rechaza(tmp_path):
    """`{<<: {nombre: A}}` no lleva alias: lo para la comprobación del merge, no la de alias.

    La rev. 1 del plan lo probaba solo junto a un alias, con el comentario «un merge necesita un
    alias», que es falso: quitar la comprobación del merge habría dejado ese test en verde."""
    with pytest.raises(ValueError, match=r"línea 1: el merge"):
        cf.leer_yaml_ficha(_yaml(tmp_path, "contrario: {<<: {nombre: A}}\n"))


def test_el_merge_con_alias_tambien(tmp_path):
    with pytest.raises(ValueError, match="alias"):
        cf.leer_yaml_ficha(_yaml(tmp_path, "base: &b {nombre: A}\ncontrario: {<<: *b}\n"))


def test_R2H04_una_sintaxis_rota_sale_como_ValueError(tmp_path):
    with pytest.raises(ValueError, match="inválido"):
        cf.leer_yaml_ficha(_yaml(tmp_path, 'notas_html: ["*",\n'))


@pytest.mark.parametrize("texto", ["", "# solo un comentario\n"])
def test_documento_vacio_es_ficha_vacia(tmp_path, texto):
    assert cf.leer_yaml_ficha(_yaml(tmp_path, texto)) == {}


def test_un_yaml_normal_se_lee_igual_que_con_safe_load(tmp_path):     # control positivo
    texto = "contrario:\n  nombre: JUAN\n  nif: '00000000T'\nnotas_html: '<p>E&amp;V</p>'\n"
    assert cf.leer_yaml_ficha(_yaml(tmp_path, texto)) == yaml.safe_load(texto)


def test_si_no_existe_FileNotFoundError(tmp_path):
    with pytest.raises(FileNotFoundError):
        cf.leer_yaml_ficha(tmp_path / "no.yaml")
