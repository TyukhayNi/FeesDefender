"""El cableado de la secuencia detras de `--modo v1`.

Plan: docs/superpowers/plans/2026-09-03-apertura-v1-plan5-cableado.md §3.
"""
import json

import pytest

from core import apertura_v1 as av1
from core import intake_log
from scripts import abrir_caso as cli


class _Ident:
    case_id = "C"
    w_code = "W-000000"


def test_f13_el_evento_de_cierre_esta_en_el_set_cerrado():
    """F13. `INTAKE_EVENTS` es cerrado: un nombre fuera del set es un evento imposible de
    emitir, y el fallo no aparece hasta que alguien intenta emitirlo."""
    assert "apertura_v1_terminada" in intake_log.INTAKE_EVENTS


def test_el_evento_de_cierre_lleva_el_estado_y_los_pendientes(tmp_path):
    case_dir = tmp_path / "caso"
    (case_dir / "00_Input").mkdir(parents=True)

    resultado = av1.ResultadoV1(
        estado=av1.EstadoV1.PREPARADO_CON_PENDIENTES,
        etapas=(av1.EtapaResultado(nombre="drive", estado="hecha", detalle="3 ficheros"),),
        pendientes=(av1.PENDIENTE_FUENTES_V3,),
        parada=None,
    )

    cli.registrar_cierre_v1(case_dir, _Ident(), resultado)

    log = case_dir / "00_Input" / "_intake_log.jsonl"
    lineas = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines() if l]
    ev = [l for l in lineas if l["event"] == "apertura_v1_terminada"][-1]
    assert ev["details"]["estado"] == "preparado_con_pendientes"
    assert ev["details"]["pendientes"] == ["fuentes_v3_sin_consultar"]
    assert ev["details"]["etapas"] == [{"nombre": "drive", "estado": "hecha"}]
