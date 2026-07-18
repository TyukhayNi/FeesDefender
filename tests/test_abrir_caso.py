import hashlib

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


def test_plan_intake_fuente_de_lote_exige_lote():
    with pytest.raises(ValueError):
        abrir_caso.plan_intake([], [], "manual")           # sin lote → error


def test_plan_intake_lote_compone_dst():
    inv = [{"relpath": "a.pdf", "sha256": "s1", "size": 3}]
    plan = abrir_caso.plan_intake(inv, [], "manual", lote="2026-07-17_manual_01")
    assert plan.items[0].dst == "2026-07-17_manual_01/a.pdf"
    assert plan.categorias == ("2026-07-17_manual_01",)


def test_plan_intake_drive_ev_sigue_en_cajon_espejo():
    inv = [{"relpath": "w/doc.pdf", "sha256": "s1", "size": 3}]
    plan = abrir_caso.plan_intake(inv, [], "drive_ev")
    assert plan.items[0].dst == "01_Drive EV/w/doc.pdf"


def test_fuente_a_subdir_eliminado():
    assert not hasattr(abrir_caso, "FUENTE_A_SUBDIR")
    assert abrir_caso.FUENTES == ("drive_ev", "whatsapp", "email", "manual", "entrevista")


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


def test_crm_payload_extrajudicial_actora():
    ident = abrir_caso.resolver_identidad(
        **_ident(codigo="BaRS11", w_code="W-02Z2NR"),
        nombres_existentes=[], force=False,
    )
    dto = abrir_caso.crm_payload(ident, cuantia=15000.0)
    from core import sudespacho_create as sc
    assert isinstance(dto, sc.NuevoExpedienteExtrajudicial)
    assert dto.referencia_cliente == ident.case_id
    assert dto.cuantia == 15000.0
    assert dto.posicion == sc.POSICION_ACTOR           # actora → ACTOR
    # tags base del tipo de caso presentes
    assert dto.tags == sc.tag_defaults_for_tipo_caso("VUELTA")


def test_crm_payload_defensiva_mapea_demandado():
    ident = abrir_caso.resolver_identidad(
        **_ident(codigo="BaRS11", w_code="W-02Z2NR", tipo_caso="LAU_20"),
        nombres_existentes=[], force=False,
    )
    dto = abrir_caso.crm_payload(ident, cuantia=0.0)
    from core import sudespacho_create as sc
    assert dto.posicion == sc.POSICION_DEMANDADO


def test_plan_intake_sha_none_no_se_marca_dup():
    inventario = [_inv("foto.jpg", None, 100)]
    log_existente = [
        {"event": "pull_drive_ev", "details": {"files": [{"path": "01_Drive EV/x", "sha256": None}]}},
    ]
    plan = abrir_caso.plan_intake(inventario, log_existente, "drive_ev")
    item = plan.items[0]
    assert item.sha256 is None
    assert item.dup is False


def test_crm_payload_otros_mapea_actor():
    ident = abrir_caso.resolver_identidad(
        **_ident(codigo="BaRS11", w_code="W-02Z2NR", sufijo="Alta", tipo_caso="OTROS"),
        nombres_existentes=[], force=False,
    )
    dto = abrir_caso.crm_payload(ident, cuantia=0.0)
    from core import sudespacho_create as sc
    assert dto.posicion == sc.POSICION_ACTOR


def test_reconcile_dup_en_disco_no_es_extra():
    """§8 reentrancia: un dup ya depositado en pasadas previas sigue en disco
    y NO debe marcarse como extra (bug: reconcile solo miraba depositables)."""
    dep = abrir_caso.ItemIntake(relpath="a.pdf", dst="01_Drive EV/a.pdf", evento="pull_drive_ev",
                                 sha256="aaa", size=100, dup=False, zero=False)
    dup = abrir_caso.ItemIntake(relpath="b.pdf", dst="01_Drive EV/b.pdf", evento="pull_drive_ev",
                                 sha256="bbb", size=100, dup=True, zero=False)
    plan = abrir_caso.PlanIntake(items=(dep, dup), fuente="drive_ev")
    rec = abrir_caso.reconcile(plan, {"01_Drive EV/a.pdf": "aaa", "01_Drive EV/b.pdf": "bbb"})
    assert rec.ok is True
    assert rec.extras == ()


def test_reconcile_cero_byte_no_es_extra():
    """§9 skip, don't abort: en el front local el inventario en disco incluye
    los 0-byte, así que un 0-byte presente en disco NO debe marcarse extra
    (bug: esperados_en_disco los excluía)."""
    dep = abrir_caso.ItemIntake(relpath="a.pdf", dst="01_Drive EV/a.pdf", evento="pull_drive_ev",
                                 sha256="aaa", size=100, dup=False, zero=False)
    sha_vacio = hashlib.sha256(b"").hexdigest()
    cero = abrir_caso.ItemIntake(relpath="vacio.txt", dst="01_Drive EV/vacio.txt", evento="pull_drive_ev",
                                  sha256=sha_vacio, size=0, dup=False, zero=True)
    plan = abrir_caso.PlanIntake(items=(dep, cero), fuente="drive_ev")
    rec = abrir_caso.reconcile(plan, {
        "01_Drive EV/a.pdf": "aaa",
        "01_Drive EV/vacio.txt": sha_vacio,
    })
    assert rec.ok is True
    assert rec.extras == ()


def test_resolver_identidad_tipo_caso_desconocido_lanza():
    with pytest.raises(ValueError):
        abrir_caso.resolver_identidad(
            **_ident(tipo_caso="NO_EXISTE"),
            nombres_existentes=[], force=False,
        )


@pytest.mark.parametrize("codigo,direccion,w_code,sufijo", [
    ("BaRS11", "Passeig Marítim, 30 - Castelldefels (08860)", "W-02Z2NR", "Vuelta"),
    ("MaRS2", "Puerto Rico 2, 5º 2", "W-0470GM", "Negativa arras"),
    ("VaRS3", "Calle Mayor 1", "W-02TH0W", "Negativa escritura"),
    ("BaRS1", "Gran Via 1", "SIN REFERENCIA", "Otros"),
])
def test_descomponer_case_id_round_trip(codigo, direccion, w_code, sufijo):
    case_id = abrir_caso.componer_case_id(codigo=codigo, direccion=direccion, w_code=w_code, sufijo=sufijo)
    assert abrir_caso.descomponer_case_id(case_id) == (codigo, direccion, w_code, sufijo)


def test_descomponer_case_id_sin_wcode_lanza():
    with pytest.raises(ValueError):
        abrir_caso.descomponer_case_id("BaRS11 - Sin referencia - Vuelta")
