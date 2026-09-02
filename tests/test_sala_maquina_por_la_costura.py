"""`sala_maquina` es el PRIMER cliente de producción de la costura (`MEJORAS #124`).

## Por qué este fichero existe, y qué NO demuestra

R24/H24-09 marcó que un censo de llamadores con suelo `>= 1` se satisface con **código
muerto**. La respuesta no es un censo mejor: es un cliente real. `sala_maquina` lo es
porque ya resuelve el workspace (Task 9 de la Fase 1) y ya sostiene el mutex.

**Lo que este cableado NO hace, dicho antes de que parezca que sí:** no mueve un solo byte
de sitio. `sala_maquina` ya escribía en `ws.working_root`, así que el destino no cambia.
Lo que gana es pasar por la puerta —contención de la base y declaración del mutex— y lo
que gana el proyecto es que la puerta deje de no tener clientes.

**Lo que sigue sin cablear, declarado:** `_registrar_tiempos` y `_escribir_cobertura_md`,
que escriben en otras bases. No se migran aquí para que el diff sea revisable.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.sala_maquina as cli
from core.casos import escritura


@pytest.fixture
def caso(tmp_casos_root):
    import importlib

    from core import case_manager as cm
    from core.config import caso_path
    importlib.reload(cm)
    nombre = "BaXX1 - Prueba - (W-SMCOST) - NEGATIVA_OFERTA"
    cm.ensure_case(nombre, titulo="Sala por la costura")
    ruta = caso_path(nombre)
    p = ruta / "00_Input" / "_caso.md"
    txt = p.read_text(encoding="utf-8")
    # `ensure_case` escribe `id_go: null`. La version anterior hacia
    # `if "id_go" not in txt` -- la cadena SI estaba -- y el valor real nunca entraba, asi
    # que los 26 tests pasaban por el NOMBRE de la carpeta y no por el metadato que sus
    # docstrings dicen probar. Un mutante que anulaba `read_case_meta` los dejaba los 26
    # verdes (R26/H26-04). Ahora se sustituye el valor de verdad.
    lineas = []
    puesto = False
    for ln in txt.replace("\r\n", "\n").split("\n"):
        if not puesto and ln.strip().startswith("id_go:"):
            lineas.append(ln.split("id_go:")[0] + "id_go: W-SMCOST")
            puesto = True
        else:
            lineas.append(ln)
    if not puesto:
        lineas = txt.replace("meta:", "meta:\n  id_go: W-SMCOST", 1).split("\n")
    p.write_text("\n".join(lineas), encoding="utf-8")
    assert "id_go: W-SMCOST" in p.read_text(encoding="utf-8")   # la fixture se comprueba
    return nombre, ruta


def _ws_de(ruta: Path, w_code: str = "W-SMCOST"):
    from core.casos.workspace_model import CaseRef, CaseWorkspace, WorkspaceMode
    return CaseWorkspace(
        case_ref=CaseRef(case_id=ruta.name, w_code=w_code),
        mode=WorkspaceMode.DRIVE_ACTIVE, working_root=ruta, canonical_ref=None,
        checkout_user=None, checkout_maquina=None, checkout_nonce=None,
        checkout_timestamp=None, validado_en="2026-09-02T12:00:00Z", procedencia="test")


class TestPasaPorLaCostura:

    def test_deposito_sala_llama_a_la_costura_CON_el_workspace(self, caso, monkeypatch):
        """El observable es que la costura se USA y con qué, no que exista.

        Un `assert` que no pueda ser falso aquí sería peor que no tener test: diría que
        hay un cliente de producción sin comprobar que lo sea.
        """
        _, ruta = caso
        ws = _ws_de(ruta)
        vistos = []
        real = escritura.deposito

        def espia(*a, **k):
            vistos.append(k.get("workspace"))
            return real(*a, **k)

        monkeypatch.setattr(escritura, "deposito", espia)
        cli._deposito_sala(ws)
        assert vistos == [ws], (
            "`_deposito_sala` no paso el workspace a la costura: sin el, `deposito` "
            "resuelve el canon por su cuenta, que es el H18-01 que esto cierra")

    def test_y_el_fichero_cae_exactamente_donde_caia(self, caso):
        """Cero cambio de conducta: el primer cliente no puede mover nada de sitio."""
        _, ruta = caso
        esperado = ruta / "01_Procesado" / "02_Sala de máquina" / cli._STATE
        cli._guardar_estado(ruta, {"sha1"}, dep=cli._deposito_sala(_ws_de(ruta)))
        assert esperado.is_file()
        assert json.loads(esperado.read_text(encoding="utf-8"))["procesados"] == ["sha1"]

    def test_sin_deposito_sigue_funcionando_igual(self, caso):
        """La vía directa se conserva: los tests existentes la usan."""
        _, ruta = caso
        cli._guardar_estado(ruta, {"sha2"})
        f = ruta / "01_Procesado" / "02_Sala de máquina" / cli._STATE
        assert json.loads(f.read_text(encoding="utf-8"))["procesados"] == ["sha2"]

    def test_la_cobertura_tambien(self, caso):
        import core.sala_maquina as sm
        _, ruta = caso
        cob = [sm.DocCobertura(slug="d", rel_path="00_Input/d.pdf",
                               metodo="pypdf", estado="ok", chars=10)]
        cli._guardar_cobertura(ruta, cob, dep=cli._deposito_sala(_ws_de(ruta)))
        assert (ruta / "01_Procesado" / "02_Sala de máquina" / cli._COBERTURA).is_file()


class TestElDepositoLlevaElWorkspace:

    def test_deposito_sala_construye_con_el_workspace(self, caso):
        """Si no llevara el workspace, la costura resolveria el canon por su cuenta:
        justo el H18-01 que este trabajo cierra."""
        _, ruta = caso
        d = cli._deposito_sala(_ws_de(ruta))
        assert d is not None
        assert d.clase == "derivado"

    def test_un_workspace_sin_W_code_toma_el_del_CANON(self, caso):
        """UNA conducta, no dos.

        La primera version asertaba `d is None or d.motivo_sin_mutex is not None`, que
        acepta dos contratos incompatibles y pasa con cualquiera de los dos
        (R25/H25-08). Con la identidad resuelta contra el canon, la conducta es una: el
        W-code lo pone el `meta.id_go`, aunque el workspace no lo traiga.
        """
        _, ruta = caso
        d = cli._deposito_sala(_ws_de(ruta, w_code=None))
        # El motivo que queda es el del MUTEX —este test no lo sostiene—, y NO uno de
        # identidad. Distinguirlos es el contrato: «identidad resuelta, mutex ausente» es
        # correcto; «identidad no utilizable» era el defecto de R25/H25-02.
        assert d is not None
        assert "mutex del caso" in d.motivo_sin_mutex
        assert "identidad" not in d.motivo_sin_mutex


class _DepositoEspia:
    """Registra lo que se le escribe. Sustituye a la capacidad real en el comando."""

    def __init__(self, real):
        self._real = real
        self.escrituras = []

    def escribir_texto(self, rel, contenido, **k):
        self.escrituras.append(rel)
        return self._real.escribir_texto(rel, contenido, **k)

    def escribir_bytes(self, rel, contenido):
        self.escrituras.append(rel)
        return self._real.escribir_bytes(rel, contenido)

    def dir_para(self, rel="."):
        return self._real.dir_para(rel)


class TestElCableadoDeLosCOMANDOS:
    """R25/H25-06: sin esto, los mutantes del cableado SOBREVIVEN.

    El revisor mutó los cuatro `dep=_dep_sala` a llamadas directas y **toda** la familia
    `test_sala_maquina*` siguió verde. La razón es que la vía directa y la capacidad
    apuntan hoy a la misma ruta, así que un aserto de existencia no distingue una de otra.

    Lo que sí distingue: un **espía** que exige que la persistencia atraviese el objeto, y
    un **canario** que hace explotar la vía directa. Con los dos, la ruta compartida deja
    de esconder cuál se usó.
    """

    def _canario(self, monkeypatch):
        """La vía directa pasa a ser un error: si se usa, el test se entera."""
        def _revienta(*a, **k):
            raise AssertionError(
                "la escritura fue por la via DIRECTA, no por la capacidad: el cableado "
                "de `dep=` se ha perdido")
        monkeypatch.setattr(cli.sm, "_sala_maquina_dir", _revienta)

    def test_guardar_estado_atraviesa_la_capacidad(self, caso, monkeypatch):
        _, ruta = caso
        espia = _DepositoEspia(cli._deposito_sala(_ws_de(ruta)))
        self._canario(monkeypatch)
        cli._guardar_estado(ruta, {"sha"}, intentos={}, hashes={}, dep=espia)
        assert espia.escrituras == [cli._STATE]

    def test_guardar_cobertura_atraviesa_la_capacidad(self, caso, monkeypatch):
        import core.sala_maquina as sm
        _, ruta = caso
        espia = _DepositoEspia(cli._deposito_sala(_ws_de(ruta)))
        self._canario(monkeypatch)
        cli._guardar_cobertura(ruta, [sm.DocCobertura(
            slug="d", rel_path="00_Input/d.pdf", metodo="pypdf", estado="ok")], dep=espia)
        assert espia.escrituras == [cli._COBERTURA]

    def test_y_el_canario_MUERDE_si_se_usa_la_via_directa(self, caso, monkeypatch):
        """El canario tiene que poder disparar: si no, los dos tests de arriba pasan
        por casualidad y no por contrato."""
        _, ruta = caso
        self._canario(monkeypatch)
        with pytest.raises(AssertionError, match="via DIRECTA"):
            cli._guardar_estado(ruta, {"sha"}, intentos={}, hashes={})


class TestLaNormalizacionLF:
    """R25/H25-07: un cambio de conducta que NO había declarado.

    La vía directa usaba `Path.write_text(..., encoding="utf-8")`, que en Windows escribe
    **CRLF**. `Deposito.escribir_texto` fuerza `newline="\n"`. La ruta y el JSON parseado
    son idénticos, pero **los bytes no**, y con ellos el hash — que es justo lo que el
    checkin compara.

    Se declara como intencional —LF es lo que el repo exige en todas partes— y se contrata
    con un aserto de bytes, para que «sin cambio de conducta» deje de ser ambiguo.
    """

    def test_la_capacidad_escribe_LF(self, caso):
        _, ruta = caso
        cli._guardar_estado(ruta, {"sha"}, intentos={}, hashes={},
                            dep=cli._deposito_sala(_ws_de(ruta)))
        crudo = (ruta / "01_Procesado" / "02_Sala de máquina" / cli._STATE).read_bytes()
        assert b"\r\n" not in crudo


class TestElCOMANDO:
    """El unico test que muerde el cableado de verdad (R25/H25-06).

    Los de arriba llaman a los *helpers*. Mute los cuatro `dep=_dep_sala` a `dep=None` y
    **los diez pasaron**: la via directa y la capacidad apuntan hoy a la misma ruta, asi
    que ningun aserto sobre el fichero distingue una de otra.

    Lo que distingue es ejecutar el COMANDO con la capacidad espiada. Si el cableado se
    pierde, el espia no ve nada y esto se pone rojo.
    """

    def test_apply_persiste_ATRAVESANDO_la_capacidad(self, tmp_path, monkeypatch):
        import core.sala_maquina as sm
        from tests.test_sala_maquina_ejecutar import _pdf_con_texto

        case = tmp_path / "EV-2026-001"
        (case / "00_Input" / "01_Drive EV").mkdir(parents=True)
        _pdf_con_texto(case / "00_Input" / "01_Drive EV" / "doc.pdf")
        monkeypatch.setattr(cli, "caso_path", lambda cid: case)
        monkeypatch.setattr(cli, "append_event",
                            lambda *a, **k: None)

        espiados = []
        real = cli._deposito_sala

        def _espia(ws):
            d = _DepositoEspia(real(ws))
            espiados.append(d)
            return d

        monkeypatch.setattr(cli, "_deposito_sala", _espia)
        cli.apply("EV-2026-001")

        assert espiados, "`apply` no construyo la capacidad: el cableado se perdio"
        escrito = [r for d in espiados for r in d.escrituras]
        assert cli._STATE in escrito, (
            "`apply` no persistio el estado por la capacidad; si el mutante "
            "`dep=None` sobrevive, este test no esta mordiendo")
        assert cli._COBERTURA in escrito

