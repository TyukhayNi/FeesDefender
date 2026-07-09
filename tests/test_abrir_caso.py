import pytest

from core import abrir_caso, config
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


def _ident(**kw):
    base = dict(codigo="BaRS11", direccion="Tibidabo 8", w_code="W-NUEVO1",
                sufijo="Vuelta", tipo_caso="VUELTA")
    base.update(kw)
    return base


def test_resolver_identidad_sin_colision():
    ident = abrir_caso.resolver_identidad(
        **_ident(), nombres_existentes=["BaRS1 - Otra (W-VIEJO1) - Vuelta"], force=False,
    )
    assert ident.case_id == "BaRS11 - Tibidabo 8 (W-NUEVO1) - Vuelta"
    assert ident.posicion == config.POSICION_ACTORA
    assert not ident.requiere_confirmacion
    assert not ident.w_code_duplicado


def test_resolver_identidad_wcode_duplicado_es_error():
    with pytest.raises(abrir_caso.ColisionCaso):
        abrir_caso.resolver_identidad(
            **_ident(w_code="W-02VND1"),
            nombres_existentes=["BaRS1 - Tibidabo 8 (W-02VND1) - Vuelta"],
            force=False,
        )


def test_resolver_identidad_wcode_duplicado_force_no_lanza():
    ident = abrir_caso.resolver_identidad(
        **_ident(w_code="W-02VND1"),
        nombres_existentes=["BaRS1 - Tibidabo 8 (W-02VND1) - Vuelta"],
        force=True,
    )
    assert ident.w_code_duplicado is True


def test_resolver_identidad_codigo_duplicado_requiere_confirmacion():
    ident = abrir_caso.resolver_identidad(
        **_ident(codigo="BaRS1"),
        nombres_existentes=["BaRS1 - Otra (W-VIEJO1) - Vuelta"],
        force=False,
    )
    assert ident.codigo_duplicado is True
    assert ident.requiere_confirmacion is True
    assert "BaRS1 - Otra (W-VIEJO1) - Vuelta" in ident.colisiones
