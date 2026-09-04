"""Una clave preparada y vacia en el YAML significa «no hay dato», no la cadena "None".

`str(None)` es "None", que es *truthy*, y `normalize_es_phone` no quita letras: la
devuelve intacta. Sin esto, completar la ficha de un colaborador escribe la cadena
literal "None" en un campo vacio del CRM del cliente.

Es el mismo H-09 que se cerro para cp/provincia/telefono del contrario en el PR #275 y
quedo abierto para el colaborador entero — y para contrario.movil.
"""
import pytest

from core.crm_ficha import cargar_ficha_yaml


def _carga(tmp_path, cuerpo: str):
    y = tmp_path / "_ficha_crm.yaml"
    y.write_text(cuerpo, encoding="utf-8")
    return cargar_ficha_yaml(y)


class TestNingunCampoDelColaboradorPuedeValerNone:

    @pytest.mark.parametrize("clave", ["email", "movil", "telefono", "nif"])
    def test_una_clave_vacia_es_cadena_vacia(self, tmp_path, clave):
        ficha = _carga(tmp_path, f"colaboradores:\n  - nombre: ANA\n    {clave}:\n")
        col = ficha.colaboradores[0]
        assert getattr(col, clave) == "", f"{clave} salio {getattr(col, clave)!r}"

    def test_todas_vacias_a_la_vez(self, tmp_path):
        ficha = _carga(
            tmp_path,
            "colaboradores:\n  - nombre: ANA\n    email:\n    movil:\n"
            "    telefono:\n    nif:\n",
        )
        col = ficha.colaboradores[0]
        assert (col.email, col.movil, col.telefono, col.nif) == ("", "", "", "")

    def test_el_valor_bueno_sobrevive(self, tmp_path):
        ficha = _carga(
            tmp_path,
            "colaboradores:\n  - nombre: ANA\n    email: ana@engelvoelkers.example\n"
            "    movil: '+34 612 345 678'\n    telefono: '912 345 678'\n",
        )
        col = ficha.colaboradores[0]
        assert col.email == "ana@engelvoelkers.example"
        assert col.movil == "612345678", "normalize_es_phone quita +34 y espacios"
        assert col.telefono == "912345678"

    def test_un_movil_sin_comillas_se_RECHAZA_en_vez_de_corromperse(self, tmp_path):
        """`movil: 0601234567` lo lee YAML como octal y el cero inicial se pierde.

        Desviacion del brief: el ejemplo original (`0612345678`) tiene un 8 y un 9,
        digitos invalidos en octal, asi que PyYAML lo deja como cadena y nunca
        corrompia nada — ni antes ni despues de este fix (comprobado contra el
        codigo pre-fix). Aqui todos los digitos son 0-7, que es lo que de verdad
        dispara el H-08 (el mismo octal que ya cubre `contrario.cp`).
        """
        with pytest.raises(ValueError, match="comillas"):
            _carga(tmp_path, "colaboradores:\n  - nombre: ANA\n    movil: 0601234567\n")


class TestElMovilDelContrarioTampoco:
    """La misma frontera para el contrario: `movil` se quedo fuera del arreglo de H-09."""

    def test_movil_vacio_es_cadena_vacia(self, tmp_path):
        ficha = _carga(tmp_path, "contrario:\n  nombre: ANA\n  movil:\n")
        assert ficha.contrario.movil == ""

    @pytest.mark.parametrize("clave", ["email", "direccion", "poblacion"])
    def test_las_otras_claves_de_texto_tampoco(self, tmp_path, clave):
        ficha = _carga(tmp_path, f"contrario:\n  nombre: ANA\n  {clave}:\n")
        assert getattr(ficha.contrario, clave) == ""

    def test_NINGUN_campo_de_texto_del_contrario_puede_valer_None(self, tmp_path):
        """La clase entera, no los campos que alguien se acordo de listar."""
        claves = ["apellido1", "apellido2", "email", "movil", "nif", "direccion",
                  "poblacion", "cp", "provincia", "telefono"]
        cuerpo = "contrario:\n  nombre: ANA\n" + "".join(f"  {k}:\n" for k in claves)
        c = _carga(tmp_path, cuerpo).contrario
        malos = [k for k in claves if getattr(c, k) != ""]
        assert malos == [], f"estos salieron con valor: {malos}"
