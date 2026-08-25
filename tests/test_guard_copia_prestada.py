"""El guard de escritura decide por DÓNDE escribe, no solo por el estado (`MEJORAS #96`).

## El defecto, y por qué es de sitio y no de implementación

`guard_escritura` decide leyendo el `estado_repositorio` del `_caso.md` **local**. Si ese
fichero dice `prestado`, toda escritura de intake se desvía a
`_pendiente_checkin/<origen>/…`, que está **fuera de `00_Input`** — y `00_Input` es
justamente lo que `sala_maquina.inventariar()` recorre. Consecuencia medida el 2026-07-27
sobre `W-02MA0R`: se depositan documentos nuevos, la sala de máquina **no ve ni uno**, la
de lectura tampoco, y la corrida se reporta como correcta. El pipeline se rompe en
silencio.

El propósito del guard (DISEÑO_V2 §6) es proteger **el Drive**: que el pipeline no pise un
caso que otro tiene prestado. Sobre una **copia local prestada** desviar no protege de
nada — esa copia entera ya es «pendiente de checkin» por definición, y el merge de tres
vías sube sus altas como `COPY_LOCAL`. Es una bandeja dentro de la bandeja.

## El discriminante, y el que NO vale — que es la parte que costó

El primer intento fue **la presencia de `MANIFEST_CHECKOUT.json`**: parecía la marca
inequívoca de copia prestada, la escribe el propio `cmd_checkout` y el checkin la lee como
baseline. **Es falso, y abría un agujero de autorización.** `cmd_checkout` sube además una
copia del manifiesto **al Drive** (`repository_cli.py`, «debe sobrevivir a la muerte del
Desktop, §3.3»), así que mientras un caso está prestado el fichero está en **las dos
copias**. Un guard que discriminara por él quedaría desactivado precisamente **sobre el
canon y precisamente mientras está prestado**, que es el único momento en que hace falta.

Lo que sí discrimina es el **registro privado de workspaces** (Fase 1): la lista de qué
copias locales conoce **esta** máquina. El canon nunca está ahí —el resolver rechaza
registrar una ruta bajo el catálogo (`WORKSPACE_UNDER_CATALOG_ROOT`)— y una copia local sí,
en cuanto se registra al prestarla o se **adopta** por la puerta del §15.

**Consecuencia declarada:** un checkout **anterior al registro y sin adoptar** sigue
desviando. Es deliberado: el sistema no adivina sobre qué copia está: o consta, o no. La vía
de desbloqueo existe y es explícita (`workspace_adopcion`, Task 8b).
"""
from __future__ import annotations

import importlib
import json

import pytest

from core import case_manager

CASE_ID = "EV-2026-001"
AHORA = "2026-08-25T12:00:00Z"


@pytest.fixture(autouse=True)
def _reload(tmp_casos_root):
    from core import config as cfg
    importlib.reload(cfg)
    importlib.reload(case_manager)


@pytest.fixture
def registro(tmp_path, monkeypatch):
    """Registro privado en `tmp_path`, FUERA de `CASOS_ROOT` (lo exige la clase)."""
    raiz = tmp_path / "registro_privado"
    monkeypatch.setenv("FEESDEFENDER_WORKSPACE_REGISTRY", str(raiz))
    from core.casos.workspace_registry import WorkspaceRegistry
    return WorkspaceRegistry(raiz, ahora=AHORA)


def _caso_prestado(case_id: str = CASE_ID) -> str:
    case_manager.ensure_case(case_id, titulo="Caso guard")
    case_manager.escribir_lock(case_id, user="Nikolai Tyukhay",
                               timestamp=AHORA, nonce="n")
    return case_id


def _con_manifiesto(case_id: str) -> None:
    """El `MANIFEST_CHECKOUT.json` que `cmd_checkout` deja **en las dos copias**."""
    from core.config import caso_path
    (caso_path(case_id) / "MANIFEST_CHECKOUT.json").write_text(
        json.dumps({"generado": AHORA, "n_ficheros": 0, "inventario": {}}),
        encoding="utf-8")


def _registrar_como_copia_local(registro, case_id: str, tipo: str = "checkout") -> None:
    from core.config import caso_path
    from core.casos.workspace_registry import SCHEMA_SOPORTADO, WorkspaceEntry
    registro.alta(WorkspaceEntry(
        case_id=case_id, w_code="W-GUARD1", canonical_ref=None,
        local_path=caso_path(case_id), nonce="n", maquina="ESTA",
        tipo=tipo, ultima_validacion=AHORA, schema=SCHEMA_SOPORTADO))


class TestSobreElCanon:
    """Donde el guard SÍ protege. Es la mitad que no se toca, y la que casi rompo."""

    def test_prestado_CON_manifiesto_sigue_desviando(self, tmp_casos_root, registro):
        """El hallazgo que mató al primer discriminante.

        `cmd_checkout` sube el manifiesto al Drive (§3.3), así que este es el estado
        REAL del canon mientras un caso está prestado. Un guard que discriminara por la
        presencia del fichero quedaría desactivado aquí — sobre la copia canónica y
        justo mientras otro la tiene tomada.
        """
        _caso_prestado()
        _con_manifiesto(CASE_ID)
        decision = case_manager.guard_escritura(CASE_ID, "00_Input/nuevo.pdf", "intake")
        assert decision.desviar is True, (
            "el guard se desactivó sobre el CANON de un caso prestado: el manifiesto "
            "está en las dos copias y no discrimina nada")

    def test_prestado_sin_manifiesto_desvia(self, tmp_casos_root, registro):
        _caso_prestado()
        decision = case_manager.guard_escritura(CASE_ID, "00_Input/nuevo.pdf", "intake")
        assert decision.desviar is True

    def test_el_conflicto_tambien_desvia(self, tmp_casos_root, registro):
        from core.config import caso_path
        from core.utils import read_md, write_md
        _caso_prestado()
        p = caso_path(CASE_ID) / "00_Input" / "_caso.md"
        fm, cuerpo = read_md(p)
        fm["meta"]["estado_repositorio"] = "conflicto"
        write_md(p, fm, cuerpo)
        decision = case_manager.guard_escritura(CASE_ID, "00_Input/nuevo.pdf", "intake")
        assert decision.desviar is True


class TestSobreLaCopiaLocalRegISTRADA:
    """Donde el guard no protege de nada y sí rompe el pipeline."""

    def test_NO_desvia(self, tmp_casos_root, registro):
        _caso_prestado()
        _con_manifiesto(CASE_ID)
        _registrar_como_copia_local(registro, CASE_ID)
        decision = case_manager.guard_escritura(CASE_ID, "00_Input/nuevo.pdf", "intake")
        assert decision.desviar is False, (
            "el guard desvió sobre una copia local registrada: los documentos caen "
            "fuera de 00_Input y la sala de máquina no los ve (MEJORAS #96)")

    def test_dir_intake_devuelve_el_arbol_vivo(self, tmp_casos_root, registro):
        from core.config import caso_path
        _caso_prestado()
        _registrar_como_copia_local(registro, CASE_ID)
        destino = case_manager.dir_intake(CASE_ID, "00_Input/01_Drive EV", "intake")
        assert "_pendiente_checkin" not in destino.as_posix(), (
            f"el intake apunta a la bandeja en una copia registrada: {destino}")
        assert destino == caso_path(CASE_ID) / "00_Input/01_Drive EV"

    def test_no_emite_evento_de_desvio(self, tmp_casos_root, registro):
        """Un desvío que no ocurre no se registra: el log no puede narrar ficción."""
        from core.intake_log import read_events
        _caso_prestado()
        _registrar_como_copia_local(registro, CASE_ID)
        case_manager.guard_escritura(CASE_ID, "00_Input/nuevo.pdf", "intake")
        assert [e for e in read_events(CASE_ID) if e["event"] == "pendiente_checkin"] == []

    def test_un_scratch_registrado_tambien_cuenta(self, tmp_casos_root, registro):
        """`local_scratch` es la otra forma de copia local del §5.2."""
        _caso_prestado()
        _registrar_como_copia_local(registro, CASE_ID, tipo="scratch")
        decision = case_manager.guard_escritura(CASE_ID, "00_Input/nuevo.pdf", "intake")
        assert decision.desviar is False


class TestFallaCerrado:
    """Ante la duda, desviar: el lado seguro es el que protege el canon."""

    def test_un_registro_ilegible_NO_desactiva_el_guard(self, tmp_casos_root, registro,
                                                        monkeypatch):
        """`RegistryUnreadable` no puede leerse como «no es copia local, adelante».

        Es la misma regla que el registro aplica a sí mismo (falla cerrado, R7/H7-02):
        «no puedo saberlo» no es «no lo es».
        """
        from core.casos import workspace_registry as wr
        _caso_prestado()
        _registrar_como_copia_local(registro, CASE_ID)

        def _revienta(self):
            raise wr.RegistryUnreadable(detalle="ilegible")

        monkeypatch.setattr(wr.WorkspaceRegistry, "cargar", _revienta)
        decision = case_manager.guard_escritura(CASE_ID, "00_Input/nuevo.pdf", "intake")
        assert decision.desviar is True, (
            "un registro ilegible desactivó el guard: 'no puedo saberlo' se leyó como "
            "'no es el canon'")

    def test_un_caso_que_no_existe_no_revienta(self, tmp_casos_root, registro):
        """El guard no puede convertirse en una vía nueva de excepción."""
        decision = case_manager.guard_escritura("NO-EXISTE", "00_Input/x.pdf", "intake")
        assert decision.desviar is False        # caso ausente ⇒ estado `disponible`
