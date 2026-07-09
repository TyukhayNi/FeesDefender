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


def _inv(relpath, sha, size):
    return {"relpath": relpath, "sha256": sha, "size": size}


def test_plan_intake_mapea_drive_ev_y_marca_dup_y_cero():
    inventario = [
        _inv("ACTIVACION/hoja.pdf", "aaa", 100),
        _inv("OFERTAS/oferta.pdf", "bbb", 200),   # duplicado (ya en log)
        _inv("vacio.txt", "e3b0c4", 0),           # 0-byte
    ]
    # log con un evento previo cuyo fichero tenía sha "bbb"
    log_existente = [
        {"event": "pull_drive_ev", "details": {"files": [{"path": "01_Drive EV/x", "sha256": "bbb"}]}},
    ]
    plan = abrir_caso.plan_intake(inventario, log_existente, "drive_ev")

    assert plan.fuente == "drive_ev"
    by_rel = {i.relpath: i for i in plan.items}
    assert by_rel["ACTIVACION/hoja.pdf"].dst == "01_Drive EV/ACTIVACION/hoja.pdf"
    assert by_rel["ACTIVACION/hoja.pdf"].evento == "pull_drive_ev"
    assert by_rel["OFERTAS/oferta.pdf"].dup is True
    assert by_rel["vacio.txt"].zero is True

    # depositables = ni dup ni 0-byte
    assert {i.relpath for i in plan.depositables} == {"ACTIVACION/hoja.pdf"}
    assert plan.con_sha == [{"path": "01_Drive EV/ACTIVACION/hoja.pdf", "sha256": "aaa"}]
    assert plan.categorias == ("01_Drive EV",)


def test_plan_intake_fuente_desconocida():
    with pytest.raises(ValueError):
        abrir_caso.plan_intake([], [], "inexistente")


def _plan_una(dst="01_Drive EV/ACTIVACION/hoja.pdf", sha="aaa"):
    item = abrir_caso.ItemIntake(relpath="ACTIVACION/hoja.pdf", dst=dst, evento="pull_drive_ev",
                                 sha256=sha, size=100, dup=False, zero=False)
    return abrir_caso.PlanIntake(items=(item,), fuente="drive_ev")


def test_reconcile_ok():
    plan = _plan_una()
    rec = abrir_caso.reconcile(plan, {"01_Drive EV/ACTIVACION/hoja.pdf": "aaa"})
    assert rec.ok is True
    assert rec.faltantes == () and rec.mismatches == () and rec.extras == ()


def test_reconcile_mismatch_y_faltante_y_extra():
    plan = _plan_una()
    rec = abrir_caso.reconcile(plan, {"01_Drive EV/ACTIVACION/hoja.pdf": "ZZZ",
                                      "01_Drive EV/extra.pdf": "qqq"})
    assert rec.ok is False
    assert "01_Drive EV/ACTIVACION/hoja.pdf" in rec.mismatches
    assert "01_Drive EV/extra.pdf" in rec.extras

    rec2 = abrir_caso.reconcile(plan, {})
    assert rec2.ok is False
    assert "01_Drive EV/ACTIVACION/hoja.pdf" in rec2.faltantes
