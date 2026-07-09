from core import abrir_caso
from core.utils import validate_case_id


def test_componer_case_id_formato_canonico():
    cid = abrir_caso.componer_case_id(
        codigo="BaRS11",
        direccion="Passeig Marítim, 30 - Castelldefels (08860)",
        w_code="W-02Z2NR",
        sufijo="Vuelta",
    )
    assert cid == "BaRS11 - Passeig Marítim, 30 - Castelldefels (08860) (W-02Z2NR) - Vuelta"
    # debe pasar la validación canónica del despacho
    assert validate_case_id(cid) == cid
