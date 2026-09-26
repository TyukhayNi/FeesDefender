from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from core import case_manager
from core.casos import case_locator
from core.sudespacho_relations import ConflictoDeIdentidad, SudespachoRelationsError
from scripts import crm_ficha as cli


class LecturaNoDeclarada(BaseException):
    """Una lectura del CRM que el test no declaró. Fuera de `Exception` a propósito, como
    `FugaDeRedEnTest`: el CLI trata una lectura caída como «SIN VERIFICAR» con salida 0, y un
    `KeyError` del doble se colaría por ahí con el test en verde (R2/H-05)."""


def _declara_fichas(monkeypatch, contrarios=None, colaboradores=None):
    """Qué devuelve el CRM al LEER cada parte por id: la lectura final (spec rev. 3 §4 B.2) y,
    desde la Task 7, la fase previa. Es preparación del doble, no un aserto: cada test que llega
    a esas lecturas dice qué ficha hay detrás de cada id, y un id no declarado MATA el test."""
    for nombre, tabla in (("get_cliente_contrario", dict(contrarios or {})),
                          ("get_colaborador", dict(colaboradores or {}))):
        def _get(i, _t=tabla, _n=nombre):
            if str(i) not in _t:
                raise LecturaNoDeclarada(f"{_n}({i!r}) no está declarado en este test")
            return dict(_t[str(i)])
        monkeypatch.setattr(f"scripts.crm_ficha.{nombre}", _get)


def _declara_resolucion(monkeypatch, contrarios=None, colaboradores=None):
    """Qué ficha EXISTE ya para cada parte: la fase previa (spec rev. 3 §3 A.4). `{clave: id}`,
    con la clave `id_crm`, `nif` o `email` de la parte, por ese orden; `None` = no existe y se
    creará; una excepción, la que levanta la resolución (un conflicto, una consulta caída). Una
    parte no declarada MATA el test, como en `_declara_fichas`."""
    for nombre, tabla in (("resolver_contrario_existente", dict(contrarios or {})),
                          ("resolver_colaborador_existente", dict(colaboradores or {}))):
        def _res(dto, *a, _t=tabla, _n=nombre, **k):
            clave = dto.id_crm or dto.nif or dto.email
            if clave not in _t:
                raise LecturaNoDeclarada(f"{_n}({clave!r}) no está declarado en este test")
            if isinstance(_t[clave], BaseException):
                raise _t[clave]
            return _t[clave]
        monkeypatch.setattr(f"scripts.crm_ficha.{nombre}", _res)


#: Las claves de identidad de la fixture `caso_con_ficha`.
_JUAN = "00000000T"
_ANA = "ana@engelvoelkers.example"

#: Las fichas del CRM coherentes con la fixture `caso_con_ficha`, el móvil incluido: sin él, la
#: lectura añadiría una discrepancia que el test no pretende (R2, §3 de su acta).
_JUAN_1099 = {"nombre": "JUAN", "1apellido": "PEREZ", "nif_cif": "00000000T",
              "movil": "600111222"}
_ANA_776 = {"nombre": "ANA", "email": "ana@engelvoelkers.example"}


@pytest.fixture
def caso_con_ficha(tmp_path, monkeypatch):
    """CASOS_ROOT en tmp, un caso con expediente extrajudicial registrado y un _ficha_crm.yaml."""
    root = tmp_path / "CASOS"
    root.mkdir()
    monkeypatch.setattr(case_locator, "_root", lambda: root)

    case_id = "BaRS11 - Falsa 1 (W-000AAA) - Vuelta"
    case_manager.ensure_case(
        case_id, titulo=case_id, referencia_crm=case_id,
        tipo_caso="VUELTA", ciudad="Barcelona", direccion="Falsa 1", id_go="W-000AAA",
    )
    case_manager.register_expediente(case_id, "606", "extrajudiciales")

    ficha = case_locator.path_for(case_id) / "00_Input" / "_ficha_crm.yaml"
    ficha.write_text(
        "contrario:\n  nombre: JUAN\n  apellido1: PEREZ\n  nif: 00000000T\n"
        "  movil: '+34 600 111 222'\n"
        "colaboradores:\n  - nombre: ANA\n    email: ana@engelvoelkers.example\n"
        "notas_html: '<p>Vuelta</p>'\n",
        encoding="utf-8",
    )
    return case_id


def test_crm_ficha_orquesta_todo(caso_con_ficha, monkeypatch):
    link_ev = MagicMock()
    ensure_c = MagicMock(return_value=("1099", True))
    ensure_col = MagicMock(return_value=("776", False))
    upd = MagicMock(return_value={"Numero_Expediente": "49", "Notas": "<p>Vuelta</p>"})
    monkeypatch.setattr("scripts.crm_ficha.link_ev_mmc", link_ev)
    monkeypatch.setattr("scripts.crm_ficha.ensure_contrario_vinculado", ensure_c)
    monkeypatch.setattr("scripts.crm_ficha.ensure_colaborador_vinculado", ensure_col)
    monkeypatch.setattr("scripts.crm_ficha.update_expediente", upd)
    # GET de verificación: devuelve algo plausible, con las Notas que el CLI escribe
    monkeypatch.setattr("scripts.crm_ficha.get_expediente",
                        MagicMock(return_value={"Numero_Expediente": "49",
                                                "Notas": "<p>Vuelta</p>"}))
    # La guarda de red obliga a declarar la lectura: sin esto el test moriria.
    monkeypatch.setattr("scripts.crm_ficha.get_relaciones",
                        MagicMock(return_value={"clientes_propios": [{"id": "2"}],
                                                "clientes_contrarios": [{"id": "1099"}],
                                                "colaboradores": [{"id": "776"}]}))
    _declara_fichas(monkeypatch, contrarios={"1099": _JUAN_1099},
                    colaboradores={"776": _ANA_776})
    # La fase previa (Task 7), coherente con lo que dicen los `ensure_*`: JUAN se crea (no
    # existía), ANA ya existía como 776.
    _declara_resolucion(monkeypatch, contrarios={_JUAN: None}, colaboradores={_ANA: "776"})

    r = CliRunner().invoke(cli.app, ["--case-id", "W-000AAA", "--yes"])
    assert r.exit_code == 0, r.output
    # Un positivo exige la certificación ENTERA (R2/H-05): con salida 0 sola, una lectura
    # que degradase a «SIN VERIFICAR» dejaba este test verde.
    assert cli.EXITO_VERIFICADA in r.output and cli.SIN_VERIFICAR not in r.output

    link_ev.assert_called_once_with("606", cliente_propio_id="2")
    assert ensure_c.call_args.args[0] == "606"          # exp_id
    assert ensure_c.call_args.args[1].apellido1 == "PEREZ"
    assert ensure_col.call_args.args[0] == "606"
    assert upd.call_args.args[0] == "606"
    assert upd.call_args.args[1] == {"Notas": "<p>Vuelta</p>"}


def test_crm_ficha_dry_run_no_escribe(caso_con_ficha, monkeypatch):
    link_ev = MagicMock()
    monkeypatch.setattr("scripts.crm_ficha.link_ev_mmc", link_ev)
    monkeypatch.setattr("scripts.crm_ficha.update_expediente", MagicMock())
    r = CliRunner().invoke(cli.app, ["--case-id", "W-000AAA", "--dry-run"])
    assert r.exit_code == 0, r.output
    link_ev.assert_not_called()


def test_crm_ficha_sin_yaml_falla(caso_con_ficha, monkeypatch):
    # Borrar el yaml
    (case_locator.path_for(caso_con_ficha) / "00_Input" / "_ficha_crm.yaml").unlink()
    r = CliRunner().invoke(cli.app, ["--case-id", "W-000AAA", "--yes"])
    assert r.exit_code != 0
    assert "_ficha_crm.yaml" in r.output


def test_crm_ficha_sin_expediente_falla(tmp_path, monkeypatch):
    root = tmp_path / "CASOS"; root.mkdir()
    monkeypatch.setattr(case_locator, "_root", lambda: root)
    case_id = "BaRS11 - Falsa 2 (W-000BBB) - Vuelta"
    case_manager.ensure_case(case_id, titulo=case_id, referencia_crm=case_id,
                             tipo_caso="VUELTA", ciudad="Barcelona", direccion="Falsa 2", id_go="W-000BBB")
    (case_locator.path_for(case_id) / "00_Input" / "_ficha_crm.yaml").write_text(
        "notas_html: x\n", encoding="utf-8")
    r = CliRunner().invoke(cli.app, ["--case-id", "W-000BBB", "--yes"])
    assert r.exit_code != 0
    assert "expediente" in r.output.lower()


def test_crm_ficha_cliente_propio_engel_volkers_vincula_id_27(tmp_path, monkeypatch):
    """_ficha_crm.yaml con cliente_propio: ENGEL_VOLKERS_SPAIN debe vincular id 27, no el default (id 2)."""
    root = tmp_path / "CASOS"; root.mkdir()
    monkeypatch.setattr(case_locator, "_root", lambda: root)
    case_id = "BaRS11 - Falsa 3 (W-000CCC) - Otros"
    case_manager.ensure_case(
        case_id, titulo=case_id, referencia_crm=case_id,
        tipo_caso="OTROS", ciudad="Barcelona", direccion="Falsa 3", id_go="W-000CCC",
    )
    case_manager.register_expediente(case_id, "607", "extrajudiciales")
    ficha = case_locator.path_for(case_id) / "00_Input" / "_ficha_crm.yaml"
    ficha.write_text("cliente_propio: ENGEL_VOLKERS_SPAIN\nnotas_html: x\n", encoding="utf-8")

    link_ev = MagicMock()
    monkeypatch.setattr("scripts.crm_ficha.link_ev_mmc", link_ev)
    monkeypatch.setattr("scripts.crm_ficha.update_expediente", MagicMock(return_value={}))
    monkeypatch.setattr("scripts.crm_ficha.get_expediente",
                        MagicMock(return_value={"Numero_Expediente": "1", "Notas": "x"}))
    monkeypatch.setattr("scripts.crm_ficha.get_relaciones",
                        MagicMock(return_value={"clientes_propios": [{"id": "27"}]}))
    _declara_fichas(monkeypatch)      # no hay partes: un GET por id aquí mataría el test

    r = CliRunner().invoke(cli.app, ["--case-id", "W-000CCC", "--yes"])
    assert r.exit_code == 0, r.output
    link_ev.assert_called_once_with("607", cliente_propio_id="27")


def test_crm_ficha_falla_limpio_si_writer_revienta_mid_run(caso_con_ficha, monkeypatch):
    """Si un writer revienta a mitad del secuenciado (tras link_ev_mmc OK), debe fallar
    limpio (spec §7.4: tolerancia a caída como _alta_crm — avisa, no revienta), no dejar
    burbujear la excepción cruda ni imprimir un traceback."""
    # Tras H-03 el CLI audita lo ya escrito antes de rendirse, asi que tambien lee.
    monkeypatch.setattr("scripts.crm_ficha.get_relaciones",
                        MagicMock(return_value={"clientes_propios": [{"id": "2"}]}))
    # La fase previa (Task 7): las dos partes se crearían, así que no hay ficha que leer.
    _declara_resolucion(monkeypatch, contrarios={_JUAN: None}, colaboradores={_ANA: None})
    link_ev = MagicMock()
    ensure_c = MagicMock(side_effect=RuntimeError("boom"))
    monkeypatch.setattr("scripts.crm_ficha.link_ev_mmc", link_ev)
    monkeypatch.setattr("scripts.crm_ficha.ensure_contrario_vinculado", ensure_c)

    r = CliRunner().invoke(cli.app, ["--case-id", "W-000AAA", "--yes"])

    assert r.exit_code != 0
    assert r.exception is None or isinstance(r.exception, SystemExit)
    assert "Traceback" not in r.output
    link_ev.assert_called_once()
    assert "[ERROR]" in r.output
    assert "re-ejecutar" in r.output.lower() and "dedup" in r.output.lower()


def test_crm_ficha_cliente_propio_desconocido_falla_sin_escribir(tmp_path, monkeypatch):
    """Un cliente_propio no mapeado debe fallar limpio (sin traceback) y no vincular el default."""
    root = tmp_path / "CASOS"; root.mkdir()
    monkeypatch.setattr(case_locator, "_root", lambda: root)
    case_id = "BaRS11 - Falsa 4 (W-000DDD) - Otros"
    case_manager.ensure_case(
        case_id, titulo=case_id, referencia_crm=case_id,
        tipo_caso="OTROS", ciudad="Barcelona", direccion="Falsa 4", id_go="W-000DDD",
    )
    case_manager.register_expediente(case_id, "608", "extrajudiciales")
    ficha = case_locator.path_for(case_id) / "00_Input" / "_ficha_crm.yaml"
    ficha.write_text("cliente_propio: NO_EXISTE\nnotas_html: x\n", encoding="utf-8")

    link_ev = MagicMock()
    monkeypatch.setattr("scripts.crm_ficha.link_ev_mmc", link_ev)
    monkeypatch.setattr("scripts.crm_ficha.update_expediente", MagicMock())

    r = CliRunner().invoke(cli.app, ["--case-id", "W-000DDD", "--yes"])
    assert r.exit_code != 0
    assert "Traceback" not in r.output  # falla limpia, no una excepción sin capturar
    assert "cliente_propio desconocido" in r.output.lower()
    link_ev.assert_not_called()


# ---------------------------------------------------------------------------
# Guarda de red. Este fichero ejerce un CLI que escribe en el CRM real, y la
# `SUDESPACHO_API_KEY` vive en el entorno de USUARIO de Windows (el `.env` la tiene
# vacia a proposito), asi que un test que olvide un mock golpea el tenant de verdad.
#
# La primera version de esta guarda no mordia, y R1/H-04 lo midio: parcheaba solo
# `get_relaciones` y levantaba `AssertionError`, que el `except Exception` del CLI
# convertia en un aviso y en salida 0. Una guarda cuyo grito se traga el codigo que
# vigila no es una guarda. Dos correcciones, y las dos son de frontera:
#
#   1. Se corta LA RED (`httpx`), no una funcion concreta. La funcion era un ejemplo;
#      la clase es «cualquier salida HTTP desde este fichero».
#   2. Levanta algo derivado de `BaseException`, que ningun `except Exception` atrapa.
#      Asi el test muere en vez de pasar por la razon equivocada.
# ---------------------------------------------------------------------------

class FugaDeRedEnTest(BaseException):
    """No hereda de Exception a proposito: ningun `except Exception` puede tragarsela."""


@pytest.fixture(autouse=True)
def _sin_red(monkeypatch):
    def _prohibido(metodo):
        def _f(*a, **k):
            destino = a[0] if a else k.get("url", "?")
            raise FugaDeRedEnTest(
                f"httpx.{metodo} salio a la red en un test ({destino!r}); "
                "mockea la funcion del CLI que la usa"
            )
        return _f

    for metodo in ("get", "post", "put", "delete", "patch", "request"):
        monkeypatch.setattr(f"httpx.{metodo}", _prohibido(metodo))


# ---------------------------------------------------------------------------
# Verificacion POR RESULTADO de los vinculos (2026-09-04)
#
# Hasta hoy el CLI remataba con «verificar partes visualmente en el CRM» porque
# `INTEGRACION_SUDESPACHO.md` daba por hecho que la API no sabe leer relaciones.
# Si sabe: `GET /api/related_register/{element}/{id}`.
# ---------------------------------------------------------------------------

class TestVerificacionPorLectura:
    """El 201 no prueba el vinculo; la lectura si, y debe mandar sobre el status."""

    @staticmethod
    def _escrituras_en_verde(monkeypatch):
        monkeypatch.setattr("scripts.crm_ficha.link_ev_mmc", MagicMock())
        monkeypatch.setattr("scripts.crm_ficha.ensure_contrario_vinculado",
                            MagicMock(return_value=("1099", False)))
        monkeypatch.setattr("scripts.crm_ficha.ensure_colaborador_vinculado",
                            MagicMock(return_value=("776", False)))
        monkeypatch.setattr("scripts.crm_ficha.update_expediente", MagicMock(return_value={}))
        # Devuelve las Notas escritas: si no, la verificacion nueva las marca FALTA
        # (y con razon — ese es justo el defecto H-01 que se acaba de cerrar).
        monkeypatch.setattr("scripts.crm_ficha.get_expediente",
                            MagicMock(return_value={"Numero_Expediente": "49",
                                                    "Notas": "<p>Vuelta</p>"}))
        _declara_fichas(monkeypatch, contrarios={"1099": _JUAN_1099},
                        colaboradores={"776": _ANA_776})
        _declara_resolucion(monkeypatch, contrarios={_JUAN: "1099"},
                            colaboradores={_ANA: "776"})

    def test_todo_vinculado_dice_VERIFICADA(self, caso_con_ficha, monkeypatch):
        self._escrituras_en_verde(monkeypatch)
        monkeypatch.setattr("scripts.crm_ficha.get_relaciones", lambda el, i: {
            "clientes_propios": [{"id": "2"}],
            "clientes_contrarios": [{"id": "1099"}],
            "colaboradores": [{"id": "776"}],
        })
        r = CliRunner().invoke(cli.app, ["--case-id", "W-000AAA", "--yes"])
        assert r.exit_code == 0, r.output
        # El literal del contrato nuevo, desde la constante del módulo (Task 6).
        assert cli.EXITO_VERIFICADA in r.output
        assert cli.SIN_VERIFICAR not in r.output
        assert "visualmente" not in r.output
        # Las TRES relaciones se listan. Sin esto el test es una asercion debil: un
        # `esperado` al que le falte el cliente propio seguiria diciendo VERIFICADA.
        assert "[ok] clientes_propios id=2" in r.output
        assert "[ok] clientes_contrarios id=1099" in r.output
        assert "[ok] colaboradores id=776" in r.output
        assert "FALTA" not in r.output

    def test_un_vinculo_ausente_TUMBA_la_corrida(self, caso_con_ficha, monkeypatch):
        """La escritura dijo OK por su 201; la lectura dice que no esta. Manda la lectura."""
        self._escrituras_en_verde(monkeypatch)
        monkeypatch.setattr("scripts.crm_ficha.get_relaciones", lambda el, i: {
            "clientes_propios": [{"id": "2"}],
            "clientes_contrarios": [{"id": "1099"}],
            "colaboradores": [],                      # el 776 no llego
        })
        r = CliRunner().invoke(cli.app, ["--case-id", "W-000AAA", "--yes"])
        assert r.exit_code == 1, r.output
        assert "[FALTA] colaboradores id=776" in r.output
        assert "DESMIENTE" in r.output
        assert "VERIFICADA" not in r.output

    def test_el_cliente_propio_tambien_se_verifica(self, caso_con_ficha, monkeypatch):
        """Es el unico vinculo que no devuelve id: si no se comprueba, nadie lo mira."""
        self._escrituras_en_verde(monkeypatch)
        monkeypatch.setattr("scripts.crm_ficha.get_relaciones", lambda el, i: {
            "clientes_propios": [],                   # EV MMC no quedo vinculado
            "clientes_contrarios": [{"id": "1099"}],
            "colaboradores": [{"id": "776"}],
        })
        r = CliRunner().invoke(cli.app, ["--case-id", "W-000AAA", "--yes"])
        assert r.exit_code == 1, r.output
        assert "[FALTA] clientes_propios id=2" in r.output

    def test_lectura_caida_es_SIN_VERIFICAR_no_fallo(self, caso_con_ficha, monkeypatch):
        """Un revisor que no corre no refuta: se declara la cobertura ausente."""
        self._escrituras_en_verde(monkeypatch)

        def _boom(el, i):
            raise RuntimeError("sin cupo")
        monkeypatch.setattr("scripts.crm_ficha.get_relaciones", _boom)

        r = CliRunner().invoke(cli.app, ["--case-id", "W-000AAA", "--yes"])
        assert r.exit_code == 0, r.output
        assert "SIN VERIFICAR" in r.output
        # El negativo contra la CONSTANTE: contra un literal copiado, cambiar el texto de
        # éxito lo habría vaciado en silencio (§9 del plan, frontera 3).
        assert cli.EXITO_VERIFICADA not in r.output


class TestLaGuardaDeRedMuerde:
    """Un guard sin prueba de que muerde no es un guard — y este no mordia (R1/H-04).

    Estos tests son la prueba de mutacion de la propia guarda: si alguien la debilita
    —vuelve a `Exception`, o vuelve a cubrir un solo verbo— aqui se ve.

    **Ninguno usa la red como oraculo.** La primera version de este bloque llamaba a
    `httpx.post` contra el host real esperando que la guarda lo cortara; con la guarda
    debilitada la llamada SALIA DE VERDAD, devolvia un 404 sin lanzar, y el test pasaba
    — usando como prueba justo lo que pretendia impedir. Se comprueba contra un host
    inexistente y por el TIPO de lo que levanta.
    """

    #: No resuelve, asi que si la guarda no corta, httpx lanza ConnectError. Nunca sale
    #: trafico a un servicio real, ni siquiera con la guarda rota.
    _URL = "http://guarda-de-red.invalid/api/loquesea"

    def test_no_hereda_de_Exception(self):
        """La razon de ser del tipo, fijada por un test y no por un comentario."""
        assert issubclass(FugaDeRedEnTest, BaseException)
        assert not issubclass(FugaDeRedEnTest, Exception)

    def test_no_la_atrapa_un_except_Exception(self):
        """Lo que el CLI hace con lo que la guarda levanta: nada. Debe morir el test."""
        import httpx

        atrapada = False
        try:
            try:
                httpx.get(self._URL)
            except Exception:          # noqa: BLE001 — es el punto del test
                atrapada = True
        except FugaDeRedEnTest:
            pass
        assert not atrapada, "un `except Exception` se tragó la alarma: la guarda es inerte"

    @pytest.mark.parametrize("verbo", ["get", "post", "put", "delete", "patch", "request"])
    def test_la_guarda_corta_todos_los_verbos(self, verbo):
        """La clase es «cualquier salida HTTP», no `httpx.get`.

        El CLI escribe con POST y PUT: cubrir solo la lectura dejaria fuera justo las
        llamadas que modifican el CRM real.
        """
        import httpx

        fn = getattr(httpx, verbo)
        args = ("GET", self._URL) if verbo == "request" else (self._URL,)
        with pytest.raises(FugaDeRedEnTest):
            fn(*args)

    def test_una_salida_no_declarada_MATA_el_test(self, caso_con_ficha, monkeypatch):
        """Escenario completo: un test olvida mockear `get_expediente`.

        Antes esto terminaba en salida 0 con un aviso y el test pasaba por la razon
        equivocada. Ahora la corrida entera muere.
        """
        monkeypatch.setattr("scripts.crm_ficha.link_ev_mmc", MagicMock())
        monkeypatch.setattr("scripts.crm_ficha.ensure_contrario_vinculado",
                            MagicMock(return_value=("1099", False)))
        monkeypatch.setattr("scripts.crm_ficha.ensure_colaborador_vinculado",
                            MagicMock(return_value=("776", False)))
        monkeypatch.setattr("scripts.crm_ficha.update_expediente", MagicMock(return_value={}))
        # `get_expediente` y `get_relaciones` SIN mockear, a proposito.

        # Escapa del propio CliRunner: `invoke` captura Exception, no BaseException.
        # Es mas fuerte de lo que se pidio — no hay nivel donde el aviso se coma la
        # alarma y el test acabe en verde.
        with pytest.raises(FugaDeRedEnTest):
            CliRunner().invoke(cli.app, ["--case-id", "W-000AAA", "--yes"])


class TestVerificarTODOLoQueLaCorridaEscribe:
    """R1/H-01..H-03. La frontera no es «las relaciones»: es TODO lo que se escribio.

    Verificar solo los vinculos dejaba las Notas fuera y aun asi imprimia VERIFICADA
    — el mismo falso OK que esta verificacion existe para eliminar, un nivel mas abajo.
    """

    @staticmethod
    def _base(monkeypatch, *, notas_leidas="<p>Vuelta</p>", colab=("776", False)):
        monkeypatch.setattr("scripts.crm_ficha.link_ev_mmc", MagicMock())
        monkeypatch.setattr("scripts.crm_ficha.ensure_contrario_vinculado",
                            MagicMock(return_value=("1099", False)))
        monkeypatch.setattr("scripts.crm_ficha.ensure_colaborador_vinculado",
                            MagicMock(return_value=colab))
        monkeypatch.setattr("scripts.crm_ficha.update_expediente", MagicMock(return_value={}))
        rec = {"Numero_Expediente": "49"}
        if notas_leidas is not None:
            rec["Notas"] = notas_leidas
        monkeypatch.setattr("scripts.crm_ficha.get_expediente", MagicMock(return_value=rec))
        # El 776 es la ficha de ANA. En `test_dos_partes_que_colapsan_…` las DOS partes caen en
        # él: no existe una ficha coherente con las dos, y el doble dice cuál devolvió el CRM
        # en vez de fabricar dos (R2, §3 de su acta).
        _declara_fichas(monkeypatch, contrarios={"1099": _JUAN_1099},
                        colaboradores={"776": _ANA_776})
        # La fase previa (Task 7). BEA —solo en `test_dos_partes_que_colapsan_…`— NO existía:
        # el colapso lo simula el `ensure_*` doblado, que devuelve el 776 a las dos. Si la fase
        # previa la resolviera también al 776, la pararía antes de escribir (bien hecho, y es
        # otra propiedad), y este bloque dejaría de probar la cardinalidad de la verificación.
        _declara_resolucion(monkeypatch, contrarios={_JUAN: "1099"},
                            colaboradores={_ANA: "776", "bea@engelvoelkers.example": None})

    def test_notas_que_el_CRM_no_guardo_TUMBAN_la_corrida(self, caso_con_ficha, monkeypatch):
        """El PUT devolvio 200 y el contenido no cambio. Manda la lectura."""
        self._base(monkeypatch, notas_leidas="<p>lo de ANTES</p>")
        monkeypatch.setattr("scripts.crm_ficha.get_relaciones", lambda el, i: {
            "clientes_propios": [{"id": "2"}],
            "clientes_contrarios": [{"id": "1099"}],
            "colaboradores": [{"id": "776"}],
        })
        r = CliRunner().invoke(cli.app, ["--case-id", "W-000AAA", "--yes"])
        assert r.exit_code == 1, r.output
        assert "[FALTA] Notas" in r.output
        assert "VERIFICADA" not in r.output

    def test_notas_no_leibles_son_SIN_VERIFICAR_no_VERIFICADA(self, caso_con_ficha, monkeypatch):
        """Si el GET del expediente cae, las Notas quedan sin comprobar — y se dice."""
        self._base(monkeypatch)
        monkeypatch.setattr("scripts.crm_ficha.get_expediente",
                            MagicMock(side_effect=RuntimeError("500")))
        monkeypatch.setattr("scripts.crm_ficha.get_relaciones", lambda el, i: {
            "clientes_propios": [{"id": "2"}],
            "clientes_contrarios": [{"id": "1099"}],
            "colaboradores": [{"id": "776"}],
        })
        r = CliRunner().invoke(cli.app, ["--case-id", "W-000AAA", "--yes"])
        assert r.exit_code == 0, r.output
        assert "SIN VERIFICAR: Notas" in r.output
        assert cli.EXITO_VERIFICADA not in r.output      # el negativo, contra la constante

    def test_dos_partes_que_colapsan_al_mismo_id_no_se_dan_por_buenas(
            self, caso_con_ficha, monkeypatch):
        """R1/H-02: `presentes` era un conjunto, asi que un vinculo satisfacia a dos.

        Se compara CARDINALIDAD: la corrida escribio dos colaboradores (ambos con id
        776 por una dedup erronea) y la lectura solo ve uno.
        """
        ficha = case_locator.path_for(caso_con_ficha) / "00_Input" / "_ficha_crm.yaml"
        ficha.write_text(
            "contrario:\n  nombre: JUAN\n  apellido1: PEREZ\n  nif: 00000000T\n"
            "colaboradores:\n"
            "  - nombre: ANA\n    email: ana@engelvoelkers.example\n"
            "  - nombre: BEA\n    email: bea@engelvoelkers.example\n"
            "notas_html: '<p>Vuelta</p>'\n",
            encoding="utf-8",
        )
        self._base(monkeypatch)
        monkeypatch.setattr("scripts.crm_ficha.get_relaciones", lambda el, i: {
            "clientes_propios": [{"id": "2"}],
            "clientes_contrarios": [{"id": "1099"}],
            "colaboradores": [{"id": "776"}],          # uno solo para las DOS
        })
        r = CliRunner().invoke(cli.app, ["--case-id", "W-000AAA", "--yes"])
        assert r.exit_code == 1, r.output
        assert "la corrida escribió 2, la lectura ve 1" in r.output

    def test_un_fallo_a_mitad_AUDITA_lo_ya_escrito(self, caso_con_ficha, monkeypatch):
        """R1/H-03: se salia con 1 sin contrastar las escrituras ya impresas como OK.

        Es justo cuando mas importa saber en que estado quedo la ficha.
        """
        self._base(monkeypatch)
        monkeypatch.setattr("scripts.crm_ficha.ensure_colaborador_vinculado",
                            MagicMock(side_effect=RuntimeError("caido")))
        monkeypatch.setattr("scripts.crm_ficha.get_relaciones", lambda el, i: {
            "clientes_propios": [{"id": "2"}],
            "clientes_contrarios": [{"id": "1099"}],
        })
        r = CliRunner().invoke(cli.app, ["--case-id", "W-000AAA", "--yes"])
        assert r.exit_code == 1, r.output
        assert "Estado de lo que sí se llegó a escribir" in r.output
        assert "[ok] clientes_contrarios id=1099" in r.output


# ---------------------------------------------------------------------------
# MEJORAS #150: el CRM DESESCAPA las entidades HTML al guardar
#
# Medido el 2026-09-04 sobre el expediente 637: la ficha entera entro y la
# verificacion declaro `[FALTA] Notas` con exit 1. Las 16 unicas diferencias
# entre lo escrito (5158 chars) y lo guardado (5142) eran cuatro `&amp;` que el
# CRM devuelve como `&`. Un rojo sobre un exito, y en casi toda ficha de este
# cliente, que es como se desactiva solo el unico guardian que verifica por
# resultado.
# ---------------------------------------------------------------------------

class TestElCRMDesescapaLasEntidadesHTML:
    """La igualdad byte a byte confundia normalizacion del servidor con perdida."""

    @staticmethod
    def _con_notas(caso_con_ficha, monkeypatch, *, escritas: str, devueltas: str):
        ficha = case_locator.path_for(caso_con_ficha) / "00_Input" / "_ficha_crm.yaml"
        ficha.write_text(
            "contrario:\n  nombre: JUAN\n  apellido1: PEREZ\n  nif: 00000000T\n"
            "colaboradores: []\n"
            f"notas_html: {escritas!r}\n",
            encoding="utf-8",
        )
        monkeypatch.setattr("scripts.crm_ficha.link_ev_mmc", MagicMock())
        monkeypatch.setattr("scripts.crm_ficha.ensure_contrario_vinculado",
                            MagicMock(return_value=("1099", False)))
        monkeypatch.setattr("scripts.crm_ficha.update_expediente", MagicMock(return_value={}))
        monkeypatch.setattr("scripts.crm_ficha.get_expediente",
                            MagicMock(return_value={"Numero_Expediente": "49",
                                                    "Notas": devueltas}))
        monkeypatch.setattr("scripts.crm_ficha.get_relaciones", lambda el, i: {
            "clientes_propios": [{"id": "2"}],
            "clientes_contrarios": [{"id": "1099"}],
            "colaboradores": [],
        })
        _declara_fichas(monkeypatch, contrarios={"1099": _JUAN_1099})
        _declara_resolucion(monkeypatch, contrarios={_JUAN: "1099"})

    def test_una_entidad_desescapada_por_el_servidor_verifica_ok(
            self, caso_con_ficha, monkeypatch):
        """El caso medido: se escribio `&amp;` y el CRM devuelve `&`. Entro entero."""
        self._con_notas(
            caso_con_ficha, monkeypatch,
            escritas="<p>E&amp;V y pitch&amp;putt</p>",
            devueltas="<p>E&V y pitch&putt</p>",
        )
        r = CliRunner().invoke(cli.app, ["--case-id", "W-000AAA", "--yes"])
        assert r.exit_code == 0, r.output
        assert cli.EXITO_VERIFICADA in r.output and cli.SIN_VERIFICAR not in r.output
        assert "[ok] Notas" in r.output
        assert "FALTA" not in r.output
        assert "DESMIENTE" not in r.output

    def test_unas_notas_TRUNCADAS_por_el_servidor_siguen_faltando(
            self, caso_con_ficha, monkeypatch):
        """El segundo mutante, y el que importa: normalizar no puede volverse permisivo.

        Si el arreglo se hace con un `in`/`startswith` en vez de una igualdad sobre
        texto ya desescapado, este test sobrevive y se pierde justo la cobertura por la
        que la verificacion existe.
        """
        self._con_notas(
            caso_con_ficha, monkeypatch,
            escritas="<p>E&amp;V y un parrafo largo que el servidor recorta</p>",
            devueltas="<p>E&V y un parrafo largo",
        )
        r = CliRunner().invoke(cli.app, ["--case-id", "W-000AAA", "--yes"])
        assert r.exit_code == 1, r.output
        assert "[FALTA] Notas" in r.output
        assert "DESMIENTE" in r.output


def test_el_cli_vincula_TODOS_los_contrarios_no_solo_el_primero(caso_con_ficha, monkeypatch):
    """`[APER-63]`: una reclamación formulada por dos firmantes —un matrimonio— exigía una
    segunda llamada a mano.

    **Este test existe porque el arnés lo pidió.** El mutante que reduce el bucle del CLI a
    `ficha.contrarios[:1]` sobrevivía: los tests del lector prueban que el YAML se lee entero,
    y ninguno probaba que el CLI los *vincule* todos. Leer N y vincular 1 es exactamente la
    pieza construida que nadie encadena.
    """
    ficha = case_locator.path_for(caso_con_ficha) / "00_Input" / "_ficha_crm.yaml"
    ficha.write_text(
        "contrario:\n"
        "  - nombre: JUAN\n    apellido1: PEREZ\n    nif: 00000000T\n"
        "  - nombre: MARIA\n    apellido1: LOPEZ\n    nif: 11111111H\n"
        "notas_html: '<p>Vuelta</p>'\n",
        encoding="utf-8",
    )
    ensure_c = MagicMock(side_effect=[("1099", True), ("1100", True)])
    monkeypatch.setattr("scripts.crm_ficha.link_ev_mmc", MagicMock())
    monkeypatch.setattr("scripts.crm_ficha.ensure_contrario_vinculado", ensure_c)
    monkeypatch.setattr("scripts.crm_ficha.ensure_colaborador_vinculado", MagicMock())
    monkeypatch.setattr("scripts.crm_ficha.update_expediente",
                        MagicMock(return_value={"Notas": "<p>Vuelta</p>"}))
    monkeypatch.setattr("scripts.crm_ficha.get_expediente",
                        MagicMock(return_value={"Notas": "<p>Vuelta</p>"}))
    monkeypatch.setattr("scripts.crm_ficha.get_relaciones",
                        MagicMock(return_value={"clientes_propios": [{"id": "2"}],
                                                "clientes_contrarios": [{"id": "1099"},
                                                                        {"id": "1100"}],
                                                "colaboradores": []}))
    _declara_fichas(monkeypatch, contrarios={
        "1099": _JUAN_1099,
        "1100": {"nombre": "MARIA", "1apellido": "LOPEZ", "nif_cif": "11111111H"}})
    # La fase previa (Task 7): las dos se crean, como dice el `ensure_c` doblado.
    _declara_resolucion(monkeypatch, contrarios={_JUAN: None, "11111111H": None})

    r = CliRunner().invoke(cli.app, ["--case-id", "W-000AAA", "--yes"])
    assert r.exit_code == 0, r.output
    assert cli.EXITO_VERIFICADA in r.output and cli.SIN_VERIFICAR not in r.output
    assert ensure_c.call_count == 2, f"vinculó {ensure_c.call_count} contrario(s), no 2"
    assert [c.args[1].apellido1 for c in ensure_c.call_args_list] == ["PEREZ", "LOPEZ"]


def test_el_plan_del_cli_enumera_los_dos_contrarios(caso_con_ficha, monkeypatch):
    """Y el dry-run los dice: el letrado tiene que ver a quién va a vincular antes de que se
    escriba."""
    ficha = case_locator.path_for(caso_con_ficha) / "00_Input" / "_ficha_crm.yaml"
    ficha.write_text(                       # con NIF desde la Task 3 de crm_ficha
        "contrario:\n"
        "  - nombre: JUAN\n    apellido1: PEREZ\n    nif: 00000000T\n"
        "  - nombre: MARIA\n    apellido1: LOPEZ\n    nif: 11111111H\n",
        encoding="utf-8",
    )
    r = CliRunner().invoke(cli.app, ["--case-id", "W-000AAA", "--dry-run"])
    assert r.exit_code == 0, r.output
    assert "PEREZ" in r.output and "LOPEZ" in r.output, r.output


# ---------------------------------------------------------------------------
# Task 6 del plan rev. 2 — la verificación por IGUALDAD, de vínculos y de datos
# (spec rev. 3 §4 B.1-B.4)
# ---------------------------------------------------------------------------

def _escrituras(monkeypatch, *, ensure_c=None, ensure_col=None, fichas_c=None, fichas_col=None,
                res_c=None, res_col=None):
    """Escrituras en verde sobre `caso_con_ficha` (JUAN → 1099, ANA → 776), la lectura de fichas
    y la resolución de la fase previa declaradas. Cada test cambia solo lo que su propiedad
    necesita."""
    _declara_resolucion(monkeypatch,
                        contrarios=res_c if res_c is not None else {_JUAN: "1099"},
                        colaboradores=res_col if res_col is not None else {_ANA: "776"})
    monkeypatch.setattr("scripts.crm_ficha.link_ev_mmc", MagicMock())
    monkeypatch.setattr("scripts.crm_ficha.ensure_contrario_vinculado",
                        ensure_c or MagicMock(return_value=("1099", False)))
    monkeypatch.setattr("scripts.crm_ficha.ensure_colaborador_vinculado",
                        ensure_col or MagicMock(return_value=("776", False)))
    monkeypatch.setattr("scripts.crm_ficha.update_expediente", MagicMock(return_value={}))
    monkeypatch.setattr("scripts.crm_ficha.get_expediente",
                        MagicMock(return_value={"Numero_Expediente": "49",
                                                "Notas": "<p>Vuelta</p>"}))
    _declara_fichas(monkeypatch,
                    contrarios=fichas_c if fichas_c is not None else {"1099": _JUAN_1099},
                    colaboradores=fichas_col if fichas_col is not None else {"776": _ANA_776})


def _relaciones(monkeypatch, contrarios=("1099",), colaboradores=("776",)):
    monkeypatch.setattr("scripts.crm_ficha.get_relaciones", lambda el, i: {
        "clientes_propios": [{"id": "2"}],
        "clientes_contrarios": [{"id": c} for c in contrarios],
        "colaboradores": [{"id": c} for c in colaboradores],
    })


def _corre():
    return CliRunner().invoke(cli.app, ["--case-id", "W-000AAA", "--yes"])


class TestElYAMLEsLaListaCompleta:
    """`#288`: el 653 salió VERIFICADA con cuatro colaboradores declarados y seis vinculados. El
    YAML es la lista COMPLETA de partes (Nikolai, 2026-09-25): lo que sobra es un fallo."""

    def test_R288_el_653_un_colaborador_de_mas_TUMBA_la_corrida(self, caso_con_ficha,
                                                                monkeypatch):
        _escrituras(monkeypatch)
        _relaciones(monkeypatch, colaboradores=("776", "624"))
        r = _corre()
        assert r.exit_code == 1, r.output
        assert "[SOBRA] colaboradores id=624" in r.output
        assert "no declara" in r.output and "crm_ficha no desvincula" in r.output
        assert cli.EXITO_VERIFICADA not in r.output

    def test_falta_y_sobra_a_la_vez(self, caso_con_ficha, monkeypatch):
        _escrituras(monkeypatch)
        _relaciones(monkeypatch, colaboradores=("624",))
        r = _corre()
        assert r.exit_code == 1, r.output
        assert "[FALTA] colaboradores id=776" in r.output
        assert "[SOBRA] colaboradores id=624" in r.output


class TestLosDatosDeLaFicha:
    """`#283` (R1/H-03): una igualdad de ids exacta certificaba una ficha cuyos datos no se habían
    escrito. La lectura final relee cada parte y compara lo que el YAML declara."""

    def test_R1H03_w030a13_relanzado_con_el_apellido_vacio_da_DATO(self, caso_con_ficha,
                                                                   monkeypatch):
        """Relanzar W-030A13 con el YAML corregido: la ficha 1128 se resuelve por NIF, no se
        completa (el apellido no es completable) y los ids cuadran. Antes decía VERIFICADA."""
        _escrituras(monkeypatch, ensure_c=MagicMock(return_value=("1128", False)),
                    fichas_c={"1128": {**_JUAN_1099, "1apellido": ""}}, res_c={_JUAN: "1128"})
        _relaciones(monkeypatch, contrarios=("1128",))
        r = _corre()
        assert r.exit_code == 1, r.output
        assert "[DATO] clientes_contrarios id=1128 1apellido: vacío en el CRM" in r.output
        assert "crm_ficha no pisa" in r.output
        assert cli.EXITO_VERIFICADA not in r.output

    def test_un_colaborador_con_un_dato_distinto_da_DATO(self, caso_con_ficha, monkeypatch):
        """El rol colaborador también se audita: cerrar una propiedad para un rol no la cierra
        para los demás.

        Desde la Task 7, un dato distinto en una ficha que YA existía lo para la fase previa,
        antes de escribir. Para probar la lectura FINAL, ANA se crea aquí (la fase previa no la
        encuentra) y es el CRM el que guarda otro email: lo que solo se sabe después de escribir."""
        _escrituras(monkeypatch,
                    ensure_col=MagicMock(return_value=("776", True)), res_col={_ANA: None},
                    fichas_col={"776": {**_ANA_776, "email": "otra@engelvoelkers.example"}})
        _relaciones(monkeypatch)
        r = _corre()
        assert r.exit_code == 1, r.output
        assert ("[DATO] colaboradores id=776 email: distinto (CRM 'otra@engelvoelkers.example', "
                "YAML 'ana@engelvoelkers.example')") in r.output

    def test_una_ficha_que_no_se_puede_leer_es_SIN_VERIFICAR(self, caso_con_ficha, monkeypatch):
        """La lectura FINAL caída. Desde la Task 7, una ficha existente que no se puede leer la
        para la fase previa, así que JUAN se crea aquí y la fase previa no tiene nada que leer."""
        _escrituras(monkeypatch, ensure_c=MagicMock(return_value=("1099", True)),
                    res_c={_JUAN: None})
        _relaciones(monkeypatch)

        def _caida(i):
            raise RuntimeError("HTTP 500")
        monkeypatch.setattr("scripts.crm_ficha.get_cliente_contrario", _caida)
        r = _corre()
        assert r.exit_code == 0, r.output
        assert f"{cli.SIN_VERIFICAR}: datos de clientes_contrarios id=1099" in r.output
        assert cli.EXITO_VERIFICADA not in r.output

    def test_un_fallo_conocido_gana_a_un_SIN_VERIFICAR(self, caso_con_ficha, monkeypatch):
        # ANA se crea (Task 7): la lectura caída tiene que ser la FINAL, no la de la fase previa.
        _escrituras(monkeypatch, ensure_col=MagicMock(return_value=("776", True)),
                    res_col={_ANA: None})
        _relaciones(monkeypatch, colaboradores=("776", "624"))

        def _caida(i):
            raise RuntimeError("HTTP 500")
        monkeypatch.setattr("scripts.crm_ficha.get_colaborador", _caida)
        r = _corre()
        assert r.exit_code == 1, r.output
        assert "[SOBRA] colaboradores id=624" in r.output
        assert cli.SIN_VERIFICAR in r.output
        assert cli.EXITO_VERIFICADA not in r.output


class TestLaParcial:
    """B.4: tras una escritura fallida, las partes sin resolver no tienen id, y sus vínculos de
    una corrida anterior saldrían como sobrantes sin serlo."""

    def test_la_parcial_no_emite_sobrantes(self, caso_con_ficha, monkeypatch):
        _escrituras(monkeypatch, ensure_col=MagicMock(side_effect=RuntimeError("caido")))
        _relaciones(monkeypatch, colaboradores=("999",))
        r = _corre()
        assert r.exit_code == 1, r.output
        assert "sobrantes: sin comprobar" in r.output
        assert "[SOBRA]" not in r.output


class TestLaGuardaDeFichasMuerde:
    """Como la guarda de red: una guarda sin prueba de que muerde no es una guarda."""

    def test_no_hereda_de_Exception(self):
        assert issubclass(LecturaNoDeclarada, BaseException)
        assert not issubclass(LecturaNoDeclarada, Exception)

    def test_una_ficha_no_declarada_MATA_el_test(self, caso_con_ficha, monkeypatch):
        _escrituras(monkeypatch, fichas_col={})       # el 776 NO se declara, a propósito
        _relaciones(monkeypatch)
        with pytest.raises(LecturaNoDeclarada):
            _corre()


# ---------------------------------------------------------------------------
# Task 7 del plan rev. 2 — la fase previa de solo lectura y la vía `id_crm`
# (spec rev. 3 §3 A.4; R2/H-01, H-06, H-08)
# ---------------------------------------------------------------------------

def _writers(monkeypatch):
    """Los cuatro writers del CLI, doblados y espiados."""
    w = {"link_ev_mmc": MagicMock(),
         "ensure_contrario_vinculado": MagicMock(return_value=("1099", False)),
         "ensure_colaborador_vinculado": MagicMock(return_value=("776", False)),
         "update_expediente": MagicMock(return_value={})}
    for nombre, doble in w.items():
        monkeypatch.setattr(f"scripts.crm_ficha.{nombre}", doble)
    return w


def _ningun_writer(w):
    for nombre, doble in w.items():
        assert not doble.called, f"{nombre} se llamó: la fase previa tenía que parar ANTES"


def _yaml_caso(caso, texto):
    (case_locator.path_for(caso) / "00_Input" / "_ficha_crm.yaml").write_text(
        texto, encoding="utf-8")


class TestLaFasePrevia:
    """Ninguna escritura sobre una ficha que el YAML contradice. La corrida nunca pisa, así que
    ese dato no lo puede arreglar ella, y escribir antes dejaría un vínculo y unos completados
    sobre una ficha que el propio YAML desmiente —y `crm_ficha` no desvincula—."""

    def test_R2H01_un_dato_distinto_en_una_ficha_existente_no_deja_escribir_NADA(
            self, caso_con_ficha, monkeypatch):
        w = _writers(monkeypatch)
        _declara_resolucion(monkeypatch, contrarios={_JUAN: "1099"}, colaboradores={_ANA: None})
        _declara_fichas(monkeypatch, contrarios={"1099": {**_JUAN_1099, "1apellido": "LOPEZ"}})
        r = _corre()
        assert r.exit_code == 1, r.output
        assert "clientes_contrarios id=1099 1apellido: distinto (CRM 'LOPEZ', YAML 'PEREZ')" in r.output
        assert "no se escribe NADA" in r.output
        _ningun_writer(w)

    def test_por_id_contradicho_por_su_nif_no_deja_escribir(self, caso_con_ficha, monkeypatch):
        """R2/H-01: comparar solo el nombre dejaba vincular una ficha cuyo NIF declarado la
        contradice. Aquí se comparan TODOS los datos declarados."""
        _yaml_caso(caso_con_ficha, "contrario: {nombre: JUAN, apellido1: PEREZ, "
                                   "nif: '11111111H', id_crm: '1128'}\n")
        w = _writers(monkeypatch)
        _declara_resolucion(monkeypatch, contrarios={"1128": "1128"})
        _declara_fichas(monkeypatch, contrarios={"1128": {"nombre": "JUAN", "1apellido": "LOPEZ",
                                                          "nif_cif": "22222222J"}})
        r = _corre()
        assert r.exit_code == 1, r.output
        assert "clientes_contrarios id=1128 1apellido: distinto" in r.output
        assert "clientes_contrarios id=1128 nif_cif: distinto" in r.output
        _ningun_writer(w)

    def test_la_segunda_parte_invalida_para_tambien_la_primera(self, caso_con_ficha,
                                                               monkeypatch):
        _yaml_caso(caso_con_ficha, "contrario:\n"
                                   "  - {nombre: JUAN, apellido1: PEREZ, nif: 00000000T}\n"
                                   "  - {nombre: MARIA, apellido1: LOPEZ, nif: 11111111H}\n")
        w = _writers(monkeypatch)
        _declara_resolucion(monkeypatch, contrarios={_JUAN: None, "11111111H": "1100"})
        _declara_fichas(monkeypatch, contrarios={"1100": {"nombre": "MARIA", "1apellido": "GOMEZ",
                                                          "nif_cif": "11111111H"}})
        r = _corre()
        assert r.exit_code == 1, r.output
        _ningun_writer(w)          # tampoco JUAN, que era nuevo y válido

    @pytest.mark.parametrize("caida", [
        SudespachoRelationsError("REST GET clientes_contrarios/1099 -> HTTP 404"),
        RuntimeError("red caída"),
    ])
    def test_una_ficha_que_no_se_puede_leer_no_deja_escribir(self, caso_con_ficha, monkeypatch,
                                                             caida):
        w = _writers(monkeypatch)
        _declara_resolucion(monkeypatch, contrarios={_JUAN: "1099"}, colaboradores={_ANA: None})

        def _get(i):
            raise caida
        monkeypatch.setattr("scripts.crm_ficha.get_cliente_contrario", _get)
        r = _corre()
        assert r.exit_code == 1, r.output
        assert "no se pudo leer la ficha" in r.output
        _ningun_writer(w)

    def test_por_id_una_ficha_sin_nombre_no_deja_escribir(self, caso_con_ficha, monkeypatch):
        _yaml_caso(caso_con_ficha, "contrario: {nombre: JUAN, id_crm: '1128'}\n")
        w = _writers(monkeypatch)
        _declara_resolucion(monkeypatch, contrarios={"1128": "1128"})
        _declara_fichas(monkeypatch, contrarios={"1128": {}})
        r = _corre()
        assert r.exit_code == 1, r.output
        assert "no existe o no tiene nombre" in r.output
        _ningun_writer(w)

    def test_un_conflicto_de_identidad_no_deja_escribir(self, caso_con_ficha, monkeypatch):
        w = _writers(monkeypatch)
        _declara_resolucion(monkeypatch, colaboradores={_ANA: None}, contrarios={
            _JUAN: ConflictoDeIdentidad("En clientes_contrarios, el NIF apunta a la ficha 1 y el "
                                        "email a la 2")})
        r = _corre()
        assert r.exit_code == 1, r.output
        assert "el NIF apunta a la ficha 1 y el email a la 2" in r.output
        _ningun_writer(w)

    def test_un_colaborador_por_id_se_vincula_sin_buscar(self, caso_con_ficha, monkeypatch):
        """La vía `id_crm` en el CLI: la fase previa lee ESA ficha, y `ensure_*` recibe el id en
        el DTO (la rama del core, que no busca ni crea, la prueba `test_crm_ficha_id_crm.py`)."""
        _yaml_caso(caso_con_ficha, "contrario: {nombre: JUAN, apellido1: PEREZ, nif: 00000000T}\n"
                                   "colaboradores:\n  - {nombre: ANA, id_crm: '776'}\n")
        w = _writers(monkeypatch)
        monkeypatch.setattr("scripts.crm_ficha.get_expediente",
                            MagicMock(return_value={"Numero_Expediente": "49"}))
        _declara_resolucion(monkeypatch, contrarios={_JUAN: "1099"}, colaboradores={"776": "776"})
        _declara_fichas(monkeypatch, contrarios={"1099": _JUAN_1099},
                        colaboradores={"776": {"nombre": "ANA"}})
        _relaciones(monkeypatch)
        r = _corre()
        assert r.exit_code == 0, r.output
        assert cli.EXITO_VERIFICADA in r.output
        assert w["ensure_colaborador_vinculado"].call_args.args[1].id_crm == "776"

    def test_R2H08_dry_run_con_id_crm_no_lee_el_CRM(self, caso_con_ficha, monkeypatch):
        """`--dry-run` sigue sin leer el CRM, tampoco para validar un `id_crm` (spec §5)."""
        _yaml_caso(caso_con_ficha, "contrario: {nombre: JUAN, id_crm: '1128'}\n")

        def _prohibido(*a, **k):
            raise LecturaNoDeclarada("el --dry-run leyó el CRM")
        for nombre in ("resolver_contrario_existente", "resolver_colaborador_existente",
                       "get_cliente_contrario", "get_colaborador", "get_relaciones",
                       "get_expediente"):
            monkeypatch.setattr(f"scripts.crm_ficha.{nombre}", _prohibido)
        r = CliRunner().invoke(cli.app, ["--case-id", "W-000AAA", "--dry-run"])
        assert r.exit_code == 0, r.output
        assert "id_crm 1128" in r.output
