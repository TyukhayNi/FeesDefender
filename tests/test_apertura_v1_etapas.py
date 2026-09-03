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


class _IdentFalsa:
    def __init__(self, case_id="C"):
        self.case_id = case_id
        self.w_code = "W-000000"


def _meta(element="extrajudiciales", **extra):
    link = {"id": "648", "input_dir": "sudespacho_648"}
    if element is not None:
        link["element"] = element
    link.update(extra)
    return {"sudespacho_expedientes": [link]}


class _Res:
    def __init__(self, **kw):
        self.blocked_legacy_v1 = kw.get("blocked_legacy_v1", False)
        self.documents_total_crm = kw.get("documents_total_crm", 5)
        self.documents_written = kw.get("documents_written", 5)
        self.documents_failed = kw.get("documents_failed", 0)
        self.errors = kw.get("errors", [])


def test_f7_el_element_sale_del_link_y_nunca_del_default():
    """F7. El default de `pull_expediente_v2` es JUDICIAL (`core/sync_sudespacho.py:1356`)."""
    visto = {}

    def pull(case_id, expediente_id, *, element):
        visto.update(expediente_id=expediente_id, element=element)
        return _Res()

    r = cli.etapa_crm(_IdentFalsa(), Path("."), leer_meta=lambda _d: _meta(), pull=pull)
    assert r.estado == "hecha"
    assert visto == {"expediente_id": "648", "element": "extrajudiciales"}


def test_f8_un_link_sin_element_es_fallo_y_no_se_adivina():
    r = cli.etapa_crm(_IdentFalsa(), Path("."), leer_meta=lambda _d: _meta(element=None),
                      pull=lambda *a, **k: pytest.fail("no debe pullar sin rama"))
    assert r.estado == "fallo"
    assert "element" in r.detalle


def test_f21_un_element_fuera_del_vocabulario_es_fallo():
    """F21. Aceptar cualquier cadena deja pasar un typo hasta la API."""
    r = cli.etapa_crm(_IdentFalsa(), Path("."),
                      leer_meta=lambda _d: _meta(element="extrajudicial"),
                      pull=lambda *a, **k: pytest.fail("no debe pullar"))
    assert r.estado == "fallo"
    assert "extrajudicial" in r.detalle


def test_f22_un_element_judicial_aborta_en_v1():
    """F22. El cruce INVERSO del criterio 38, que es el peligroso: la rama judicial sigue
    bloqueada hasta que exista adaptador verificado."""
    r = cli.etapa_crm(_IdentFalsa(), Path("."),
                      leer_meta=lambda _d: _meta(element="expedientes_judiciales"),
                      pull=lambda *a, **k: pytest.fail("no debe pullar la rama judicial"))
    assert r.estado == "fallo"
    assert "judicial" in r.detalle


def test_f9_un_caso_sin_expediente_registrado_es_saltada_con_pendiente():
    r = cli.etapa_crm(_IdentFalsa(), Path("."),
                      leer_meta=lambda _d: {"sudespacho_expedientes": []},
                      pull=lambda *a, **k: pytest.fail("no debe pullar"))
    assert r.estado == "saltada"
    assert [p.codigo for p in r.pendientes] == ["crm_sin_expediente"]


@pytest.mark.parametrize("kw,estado,codigo", [
    ({"errors": ["list_gdocu_docs_rest: 500"]}, "fallo", None),
    ({"blocked_legacy_v1": True}, "fallo", None),
    ({"documents_failed": 2}, "hecha", "crm_documentos_fallidos"),
    ({"documents_total_crm": 0, "documents_written": 0}, "saltada", "crm_gestor_vacio"),
    ({}, "hecha", None),
])
def test_f17_f20_el_resultado_del_pull_gobierna_la_etapa(kw, estado, codigo):
    """HA-04. `pull_expediente_v2` NO lanza: lo dice todo por retorno. Leer solo la
    ausencia de excepcion es incumplir «verificar por resultado, nunca por status»."""
    r = cli.etapa_crm(_IdentFalsa(), Path("."), leer_meta=lambda _d: _meta(),
                      pull=lambda *a, **k: _Res(**kw))
    assert r.estado == estado
    assert [p.codigo for p in r.pendientes] == ([codigo] if codigo else [])


def test_crm_que_revienta_es_fallo():
    def explota(*a, **k):
        raise RuntimeError("PHPSESSID caducada")
    r = cli.etapa_crm(_IdentFalsa(), Path("."), leer_meta=lambda _d: _meta(), pull=explota)
    assert r.estado == "fallo"
    assert "PHPSESSID" in r.detalle


def test_un_caso_md_ilegible_es_fallo():
    def revienta(_d):
        raise OSError("permiso denegado")
    r = cli.etapa_crm(_IdentFalsa(), Path("."), leer_meta=revienta,
                      pull=lambda *a, **k: pytest.fail("no debe pullar"))
    assert r.estado == "fallo"
    assert "_caso.md" in r.detalle


@pytest.mark.parametrize("status,estado,hay_pendiente", [
    ("ok", "hecha", False),
    (None, "hecha", False),      # F12: no se ejecuto != quedo pendiente
    ("parcial", "hecha", True),  # F10
])
def test_f10_f12_el_status_de_atomizacion_gobierna_el_pendiente(status, estado,
                                                                hay_pendiente):
    r = cli.etapa_sala_maquina(_IdentFalsa(), correr=lambda: status)
    assert r.estado == estado
    assert bool(r.pendientes) is hay_pendiente


def test_f11_atomizacion_en_fallo_bloquea_la_etapa():
    """F11. D4: `fallo` de atomizacion deja V1 `bloqueado`."""
    r = cli.etapa_sala_maquina(_IdentFalsa(), correr=lambda: "fallo")
    assert r.estado == "fallo"


def test_un_typer_exit_no_cero_del_ocr_es_fallo():
    import typer

    def revienta():
        raise typer.Exit(code=2)

    r = cli.etapa_sala_maquina(_IdentFalsa(), correr=revienta)
    assert r.estado == "fallo"
    assert "2" in r.detalle


def test_un_typer_exit_cero_no_es_fallo():
    import typer

    def sale_limpio():
        raise typer.Exit(code=0)

    r = cli.etapa_sala_maquina(_IdentFalsa(), correr=sale_limpio)
    assert r.estado == "hecha"


def test_una_excepcion_del_ocr_es_fallo():
    def explota():
        raise RuntimeError("ocrmypdf no esta instalado")

    r = cli.etapa_sala_maquina(_IdentFalsa(), correr=explota)
    assert r.estado == "fallo"
    assert "ocrmypdf" in r.detalle
