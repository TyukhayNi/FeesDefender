from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from core import case_manager
from core.casos import case_locator
from scripts import crm_ficha as cli


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

    r = CliRunner().invoke(cli.app, ["--case-id", "W-000AAA", "--yes"])
    assert r.exit_code == 0, r.output

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

    def test_todo_vinculado_dice_VERIFICADA(self, caso_con_ficha, monkeypatch):
        self._escrituras_en_verde(monkeypatch)
        monkeypatch.setattr("scripts.crm_ficha.get_relaciones", lambda el, i: {
            "clientes_propios": [{"id": "2"}],
            "clientes_contrarios": [{"id": "1099"}],
            "colaboradores": [{"id": "776"}],
        })
        r = CliRunner().invoke(cli.app, ["--case-id", "W-000AAA", "--yes"])
        assert r.exit_code == 0, r.output
        assert "VERIFICADA por lectura" in r.output
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
        assert "VERIFICADA por lectura" not in r.output


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
        assert "VERIFICADA por lectura" not in r.output

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
