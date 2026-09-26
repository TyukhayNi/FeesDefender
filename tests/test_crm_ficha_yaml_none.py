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


#: Identidades SINTÉTICAS para las fixtures de este fichero. Desde la Task 3 de crm_ficha (plan
#: rev. 2, spec rev. 3 §3 A.4) toda parte lleva NIF o email; estas fixtures prueban el nulo de
#: OTRAS claves, y la identidad es solo lo que las hace válidas salvo en su propiedad.
_NIF = "nif: '00000000T'"
_EMAIL = "email: ana@engelvoelkers.example"


class TestNingunCampoDelColaboradorPuedeValerNone:

    @pytest.mark.parametrize("clave", ["email", "movil", "telefono", "nif"])
    def test_una_clave_vacia_es_cadena_vacia(self, tmp_path, clave):
        # Migrado (Task 3): la identidad va por la OTRA clave, para no tocar la vacía.
        identidad = _NIF if clave == "email" else _EMAIL
        ficha = _carga(tmp_path,
                       f"colaboradores:\n  - nombre: ANA\n    {identidad}\n    {clave}:\n")
        col = ficha.colaboradores[0]
        assert getattr(col, clave) == "", f"{clave} salio {getattr(col, clave)!r}"

    @pytest.mark.parametrize("identidad, vacias", [
        (_EMAIL, ("movil", "telefono", "nif")),
        (_NIF, ("email", "movil", "telefono")),
    ])
    def test_todas_vacias_a_la_vez(self, tmp_path, identidad, vacias):
        """Migrado en DOS pasos, y se dice. Sin NIF ni email, la parte no tiene identidad y
        hasta la Task 7 no hay `id_crm`: aquí van dos casos, y cada campo sale vacío en al menos
        uno junto a los otros dos que no son la identidad. La Task 7 lo devuelve a las cuatro
        claves vacías A LA VEZ, con `id_crm`."""
        ficha = _carga(tmp_path, "colaboradores:\n  - nombre: ANA\n    " + identidad + "\n"
                       + "".join(f"    {k}:\n" for k in vacias))
        col = ficha.colaboradores[0]
        assert tuple(getattr(col, k) for k in vacias) == ("", "", "")

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
        # Migrado (Task 3, de precisión): con email, el `raises` salta SOLO por el octal.
        with pytest.raises(ValueError, match="comillas"):
            _carga(tmp_path, f"colaboradores:\n  - nombre: ANA\n    {_EMAIL}\n"
                             "    movil: 0601234567\n")


class TestElMovilDelContrarioTampoco:
    """La misma frontera para el contrario: `movil` se quedo fuera del arreglo de H-09."""

    def test_movil_vacio_es_cadena_vacia(self, tmp_path):
        ficha = _carga(tmp_path, f"contrario:\n  nombre: ANA\n  {_NIF}\n  movil:\n")
        assert ficha.contrario.movil == ""

    @pytest.mark.parametrize("clave", ["email", "direccion", "poblacion"])
    def test_las_otras_claves_de_texto_tampoco(self, tmp_path, clave):
        ficha = _carga(tmp_path, f"contrario:\n  nombre: ANA\n  {_NIF}\n  {clave}:\n")
        assert getattr(ficha.contrario, clave) == ""

    @pytest.mark.parametrize("identidad", [_NIF, _EMAIL])
    def test_NINGUN_campo_de_texto_del_contrario_puede_valer_None(self, tmp_path, identidad):
        """La clase entera, no los campos que alguien se acordo de listar.

        Migrado en DOS pasos, y se dice: sin NIF ni email la parte no tiene identidad y hasta la
        Task 7 no hay `id_crm`. Aquí, dos casos —identidad por NIF con las otras nueve vacías,
        el email incluido; por email con las otras nueve vacías, el NIF incluido—; la Task 7 lo
        devuelve a las diez vacías a la vez, con `id_crm`."""
        todas = ["apellido1", "apellido2", "email", "movil", "nif", "direccion",
                 "poblacion", "cp", "provincia", "telefono"]
        claves = [k for k in todas if not identidad.startswith(f"{k}:")]
        cuerpo = (f"contrario:\n  nombre: ANA\n  {identidad}\n"
                  + "".join(f"  {k}:\n" for k in claves))
        c = _carga(tmp_path, cuerpo).contrario
        malos = [k for k in claves if getattr(c, k) != ""]
        assert malos == [], f"estos salieron con valor: {malos}"


class TestNotasHtmlSinNoneLiteral:
    """H-09 para notas_html: quedó fuera del arreglo de campos en PR #275."""

    def test_notas_html_vacio_es_cadena_vacia_no_none(self, tmp_path):
        ficha = _carga(tmp_path, "notas_html:\n")
        assert ficha.notas_html == "", f"esperaba '', obtuve {ficha.notas_html!r}"

    def test_notas_html_con_contenido_sobrevive(self, tmp_path):
        ficha = _carga(tmp_path, "notas_html: '<p>Abogado de la parte contraria</p>'\n")
        assert ficha.notas_html == "<p>Abogado de la parte contraria</p>"

    def test_notas_html_ausente_es_cadena_vacia(self, tmp_path):
        ficha = _carga(tmp_path, f"contrario:\n  nombre: ANA\n  {_NIF}\n")
        assert ficha.notas_html == ""


class TestClientePropioConPorDefecto:
    """cliente_propio: si viene None, cae al default; si viene valor, se respeta."""

    def test_cliente_propio_ausente_toma_default(self, tmp_path):
        from core.crm_ficha import CLIENTE_PROPIO_DEFAULT
        ficha = _carga(tmp_path, f"contrario:\n  nombre: ANA\n  {_NIF}\n")
        assert ficha.cliente_propio == CLIENTE_PROPIO_DEFAULT

    def test_cliente_propio_vacio_toma_default(self, tmp_path):
        from core.crm_ficha import CLIENTE_PROPIO_DEFAULT
        ficha = _carga(tmp_path, "cliente_propio:\n")
        assert ficha.cliente_propio == CLIENTE_PROPIO_DEFAULT

    def test_cliente_propio_con_valor_se_respeta(self, tmp_path):
        """Migrado en la Task 2 de crm_ficha (plan rev. 2): `OTRO_CLIENTE` ya no es declarable
        —el catálogo `CLIENTES_PROPIOS_EV` es cerrado—, así que la propiedad «lo declarado se
        respeta y no cae al defecto» se prueba con la clave real que no es la predeterminada."""
        ficha = _carga(tmp_path, "cliente_propio: 'ENGEL_VOLKERS_SPAIN'\n")
        assert ficha.cliente_propio == "ENGEL_VOLKERS_SPAIN"
