"""El frontal: lo que el humano lee antes de gastar, y la precedencia del entorno."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal
from pathlib import Path

from core import expedicion_certificada as exp
from scripts import codicert as cli


def _plan(tmp_path):
    envios = [exp.EnvioPrevisto("burofax", {"nombre": "ANA LOPEZ Y LUIS PEREZ"},
                                "ANA LOPEZ Y LUIS PEREZ · C Mayor 1, Madrid  "
                                "⚠ sobre conjunto: acredita entrega EN EL DOMICILIO, no a cada uno"),
              exp.EnvioPrevisto("correo", {"correo": "ana@x.es"}, "ANA LOPEZ · ana@x.es")]
    return exp.Plan(w_code="W-04AKM2", tipo="OVC", id_personalizado="W-04AKM2 - OVC",
                    plaza="Madrid", entorno="sandbox", envios=envios,
                    ausencias=["LUIS PEREZ: sin canal SMS (el CRM no tiene un móvil español)"],
                    coste=Decimal("17.7647"), credito=Decimal("398.1388"),
                    documentos=[tmp_path / "A.pdf"], documentos_sha256=["abc"],
                    asunto="Comunicación certificada · expediente W-04AKM2",
                    cuerpo="<p>…</p>", digest="d1")


def test_el_plan_enseña_entorno_emisor_coste_y_credito(tmp_path):
    texto = cli.render_plan(_plan(tmp_path))
    for esperado in ("SANDBOX", "W-04AKM2 - OVC", "17.7647", "398.1388", "Madrid"):
        assert esperado in texto


def test_el_plan_enseña_las_ausencias_y_el_aviso_del_sobre_conjunto(tmp_path):
    texto = cli.render_plan(_plan(tmp_path))
    assert "sin canal SMS" in texto
    assert "no a cada uno" in texto


def test_el_plan_enseña_el_digest_que_habra_que_confirmar(tmp_path):
    assert "d1" in cli.render_plan(_plan(tmp_path))


def test_el_plan_enseña_el_texto_que_leera_el_requerido(tmp_path):
    texto = cli.render_plan(_plan(tmp_path))
    assert "Comunicación certificada · expediente W-04AKM2" in texto


def test_produccion_exige_la_orden_aunque_la_variable_lo_diga(monkeypatch):
    monkeypatch.setenv("CODICERT_ENTORNO", "produccion")
    assert cli.entorno_de(argumento=None) == "sandbox"
    assert cli.entorno_de(argumento="produccion") == "produccion"


def test_un_entorno_inventado_se_rechaza():
    import pytest
    with pytest.raises(SystemExit):
        cli.entorno_de(argumento="preproduccion")
