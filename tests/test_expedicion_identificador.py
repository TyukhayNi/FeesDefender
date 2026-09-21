"""La gramática `<W-code> - <TIPO>`, que ya está en uso en producción."""
from __future__ import annotations

import pytest

from core import expedicion_certificada as exp


def test_la_primera_expedicion_no_lleva_ordinal():
    assert exp.componer_id("W-04AKM2", "OVC") == "W-04AKM2 - OVC"


def test_la_segunda_expedicion_del_mismo_tipo_lo_lleva():
    assert exp.componer_id("W-04AKM2", "REQ", ordinal=2) == "W-04AKM2 - REQ 2"


def test_nunca_pasa_de_veinte_caracteres():
    assert len(exp.componer_id("W-04AKM2", "REQ", ordinal=99)) <= 20


def test_un_tipo_inventado_se_rechaza():
    with pytest.raises(exp.ExpedicionError):
        exp.componer_id("W-04AKM2", "LOQUESEA")


def test_el_requerimiento_y_la_ovc_del_mismo_expediente_NO_colisionan():
    assert exp.componer_id("W-04AKM2", "REQ") != exp.componer_id("W-04AKM2", "OVC")


def test_un_w_code_largo_que_no_cabria_se_rechaza_en_vez_de_truncarse():
    with pytest.raises(exp.ExpedicionError):
        exp.componer_id("W-0123456789ABCDEF", "REQ", ordinal=10)
