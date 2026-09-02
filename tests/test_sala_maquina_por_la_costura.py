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
    if "id_go" not in txt:
        p.write_text(txt.replace("meta:", "meta:\n  id_go: W-SMCOST", 1), encoding="utf-8")
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

    def test_un_workspace_sin_W_code_no_rompe_la_corrida(self, caso):
        """Sin namespace no hay mutex, y eso se declara — no se aborta.

        Es el mismo trinquete que `_bajo_mutex`: cerrar en falso una vía que hoy
        funciona le rompe el día al equipo.
        """
        _, ruta = caso
        d = cli._deposito_sala(_ws_de(ruta, w_code=None))
        assert d is None or d.motivo_sin_mutex is not None
