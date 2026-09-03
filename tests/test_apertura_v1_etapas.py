"""Los adaptadores de las etapas de V1: traducen una llamada real a `EtapaResultado`.

Plan: docs/superpowers/plans/2026-09-03-apertura-v1-plan5-cableado.md §3.
"""
from pathlib import Path

import pytest

from core import apertura_v1 as av1
from core.intake_drive import DriveIntakeResult
from scripts import abrir_caso as cli


def _drive_result(**kw):
    base = dict(case_id="C", team_id="T", folder_id="F", target_dir=Path("."),
                files_after=3, skipped=False, rclone_returncode=0, errors=[])
    base.update(kw)
    return DriveIntakeResult(**base)


def test_f15_la_etapa_pasa_por_la_custodia_y_no_por_el_pull_a_pelo():
    """F15. `_intake_drive_ev` hashea el destino efectivo, reconcilia y registra los bytes
    parciales de un pull fallido. Llamar a `pull_drive_ev` directamente deroga las tres."""
    visto = {}

    def intake(ident, case_dir, folder_id, team_id, *, dry_run, force):
        visto.update(folder_id=folder_id, team_id=team_id, force=force)
        return _drive_result()

    r = cli.etapa_drive(None, Path("."), folder_id="F", team_id="T", intake=intake)
    assert r.estado == "hecha"
    assert visto["folder_id"] == "F"
    assert visto["team_id"] == "T"


def test_f16_en_v1_el_pull_consulta_en_cada_ronda():
    """F16. La spec llama al skip por `.pulled` «falso punto fijo»."""
    visto = {}

    def intake(ident, case_dir, folder_id, team_id, *, dry_run, force):
        visto["force"] = force
        return _drive_result()

    cli.etapa_drive(None, Path("."), folder_id="F", team_id="T", intake=intake)
    assert visto["force"] is True


def test_f6_un_skipped_en_v1_es_fallo_porque_la_consulta_no_se_hizo():
    """F6, reformulada por HA-03. Con `force=True`, `skipped` no puede ser True; si lo es,
    alguien devolvio el marcador al camino y la ronda no consulto Drive."""
    r = cli.etapa_drive(None, Path("."), folder_id="F", team_id="T",
                        intake=lambda *a, **k: _drive_result(skipped=True))
    assert r.estado == "fallo"
    assert "consulta remota" in r.detalle


def test_drive_con_errores_es_fallo():
    r = cli.etapa_drive(None, Path("."), folder_id="F", team_id="T",
                        intake=lambda *a, **k: _drive_result(errors=["rclone: exit 3"]))
    assert r.estado == "fallo"
    assert "exit 3" in r.detalle


def test_drive_con_returncode_no_cero_es_fallo():
    r = cli.etapa_drive(None, Path("."), folder_id="F", team_id="T",
                        intake=lambda *a, **k: _drive_result(rclone_returncode=3))
    assert r.estado == "fallo"


def test_drive_que_revienta_es_fallo_y_no_propaga():
    def explota(*a, **k):
        raise RuntimeError("token caducado")
    r = cli.etapa_drive(None, Path("."), folder_id="F", team_id="T", intake=explota)
    assert r.estado == "fallo"
    assert "token caducado" in r.detalle
