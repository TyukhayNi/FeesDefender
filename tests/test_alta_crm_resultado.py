"""`_alta_crm` dice CUAL de sus desenlaces ocurrio.

R1/H-02, literal: «el helper devuelve `None` si el caso ya estaba vinculado, si se
declina el alta, si el POST lanza una excepcion, si falla el registro local y
tambien despues de un alta correcta». La rev. 1 del plan traducia LOS CINCO a
`saltada` con el detalle «el caso ya tiene expediente CRM vinculado» — es decir,
**un timeout se describia como si la vinculacion existiera**.

Los efectos se doblan con `monkeypatch`: ninguno de estos tests toca el CRM.
"""

import pytest

import scripts.abrir_caso as cli


class _Ident:
    case_id = "W-TEST01"
    w_code = "W-TEST01"
    direccion = "Calle Falsa 1"


@pytest.fixture
def sin_vinculo(monkeypatch):
    """Un caso sin expediente CRM previo y sin duplicados en el CRM."""
    monkeypatch.setattr(cli.case_manager, "get_case_status",
                        lambda _cid: {"expedientes": []})
    monkeypatch.setattr(cli.alta_crm_politica, "expediente_local_para_alta",
                        lambda *_a, **_k: None)
    monkeypatch.setattr(cli.sudespacho_relations, "buscar_expedientes_duplicados",
                        lambda **_k: [])
    monkeypatch.setattr(cli.alta_crm_politica, "decidir",
                        lambda *_a, **_k: cli.alta_crm_politica.DecisionAltaCRM(
                            accion=cli.alta_crm_politica.CREAR))
    monkeypatch.setattr(cli.brain, "crm_payload",
                        lambda *_a, **_k: _PayloadFalso())
    return monkeypatch


class _PayloadFalso:
    referencia_cliente = "REF"
    posicion = "Actor"
    tags: list[str] = []
    cuantia = 0.0


def test_alta_correcta_devuelve_creado_con_su_id(sin_vinculo, monkeypatch):
    monkeypatch.setattr(cli.sudespacho_create, "create_expediente", lambda _p: "644")
    monkeypatch.setattr(cli.case_manager, "register_expediente", lambda *_a: None)

    r = cli._alta_crm(_Ident(), cuantia=None, crm_mode="api", yes=True)

    assert (r.estado, r.exp_id) == ("creado", "644")


def test_ya_vinculado_se_distingue_de_creado(monkeypatch):
    monkeypatch.setattr(cli.case_manager, "get_case_status",
                        lambda _cid: {"expedientes": [{"element": "extrajudiciales",
                                                       "id": "640"}]})
    monkeypatch.setattr(cli.alta_crm_politica, "expediente_local_para_alta",
                        lambda *_a, **_k: {"element": "extrajudiciales", "id": "640"})

    r = cli._alta_crm(_Ident(), cuantia=None, crm_mode="api", yes=True)

    assert r.estado == "ya_vinculado"
    assert r.exp_id == "640"


def test_un_timeout_del_POST_no_se_describe_como_ya_vinculado(sin_vinculo, monkeypatch):
    # El defecto exacto que midio R1/H-02.
    def _timeout(_p):
        raise TimeoutError("el CRM no respondio")

    monkeypatch.setattr(cli.sudespacho_create, "create_expediente", _timeout)

    r = cli._alta_crm(_Ident(), cuantia=None, crm_mode="api", yes=True)

    assert r.estado == "fallo_post"
    assert "vinculado" not in (r.detalle or "").lower()


def test_fallo_al_registrar_en_local_conserva_el_id(sin_vinculo, monkeypatch):
    # El caso peor del §5.2: el POST hizo commit y el vinculo local no se escribio.
    # Perder el id obligaria a buscar el expediente a mano en el CRM.
    def _explota(*_a):
        raise OSError("disco")

    monkeypatch.setattr(cli.sudespacho_create, "create_expediente", lambda _p: "645")
    monkeypatch.setattr(cli.case_manager, "register_expediente", _explota)

    r = cli._alta_crm(_Ident(), cuantia=None, crm_mode="api", yes=True)

    assert r.estado == "fallo_registro"
    assert r.exp_id == "645", "el id del expediente CREADO no se puede perder"


def test_declinar_el_gate_se_distingue_de_un_fallo(sin_vinculo, monkeypatch):
    monkeypatch.setattr(cli.typer, "confirm", lambda *_a, **_k: False)
    monkeypatch.setattr(cli.sudespacho_create, "create_expediente",
                        lambda _p: pytest.fail("declinado no puede alcanzar el POST"))

    r = cli._alta_crm(_Ident(), cuantia=None, crm_mode="api", yes=False)

    assert r.estado == "declinado"


def test_crm_skip_ni_siquiera_consulta(monkeypatch):
    monkeypatch.setattr(cli.case_manager, "get_case_status",
                        lambda _cid: pytest.fail("con skip no se consulta nada"))

    r = cli._alta_crm(_Ident(), cuantia=None, crm_mode="skip", yes=True)

    assert r.estado == "omitido"
