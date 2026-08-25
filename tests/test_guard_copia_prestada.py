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

## Por qué hoy no muerde siempre, que es lo que lo hace traicionero

El checkout **no baja** el `_caso.md` (está en `MERGE_EXCLUSIONS`), así que en una copia
recién prestada el campo falta, `estado_de_fm` devuelve `disponible` por defecto y el guard
queda inerte. En cuanto alguien copia el `_caso.md` del Drive a local —lo que hay que hacer
para conservar el pull state— el guard se activa y rompe el pipeline. Dos comportamientos
opuestos según un fichero que el protocolo dice que **no es autoridad del lock en local**.

## El discriminante, y por qué este y no otro

`MANIFEST_CHECKOUT.json` en la raíz de la copia. Es la marca **inequívoca** de copia
prestada, ya existe, la escribe el propio `cmd_checkout` y el checkin la lee para el merge
de tres vías. La alternativa —pasar un flag explícito desde cada CLI— exige tocar todos los
llamadores y deja el default en el lado inseguro: quien olvide pasarlo vuelve a romper el
pipeline en silencio.
"""
from __future__ import annotations

import importlib
import json

import pytest

from core import case_manager

CASE_ID = "EV-2026-001"


@pytest.fixture(autouse=True)
def _reload(tmp_casos_root):
    from core import config as cfg
    importlib.reload(cfg)
    importlib.reload(case_manager)


def _caso_prestado(case_id: str = CASE_ID) -> str:
    """Un caso cuyo `_caso.md` dice `prestado`. Sin manifiesto: es el canon."""
    case_manager.ensure_case(case_id, titulo="Caso guard")
    case_manager.escribir_lock(case_id, user="Nikolai Tyukhay",
                               timestamp="2026-08-25T09:45:12Z", nonce="n")
    return case_id


def _marcar_como_copia_prestada(case_id: str) -> None:
    """Deja el `MANIFEST_CHECKOUT.json` que `cmd_checkout` escribe en la copia local."""
    from core.config import caso_path
    (caso_path(case_id) / "MANIFEST_CHECKOUT.json").write_text(
        json.dumps({"case_id": case_id, "nonce": "n", "inventario": {}}),
        encoding="utf-8")


class TestSobreLaCopiaPrestada:
    """Donde el guard no protege de nada y sí rompe el pipeline."""

    def test_NO_desvia_a_la_bandeja(self, tmp_casos_root):
        _caso_prestado()
        _marcar_como_copia_prestada(CASE_ID)
        decision = case_manager.guard_escritura(CASE_ID, "00_Input/nuevo.pdf", "intake")
        assert decision.desviar is False, (
            "el guard desvió sobre una copia local prestada: los documentos caen fuera "
            "de 00_Input y la sala de máquina no los ve (MEJORAS #96)")

    def test_dir_intake_devuelve_el_arbol_vivo(self, tmp_casos_root):
        """La envoltura que usan de verdad los puntos de intake."""
        from core.config import caso_path
        _caso_prestado()
        _marcar_como_copia_prestada(CASE_ID)
        destino = case_manager.dir_intake(CASE_ID, "00_Input/01_Drive EV", "intake")
        assert "_pendiente_checkin" not in destino.as_posix(), (
            f"el intake apunta a la bandeja en una copia prestada: {destino}")
        assert destino == caso_path(CASE_ID) / "00_Input/01_Drive EV"

    def test_no_emite_evento_de_desvio(self, tmp_casos_root):
        """Un desvío que no ocurre no se registra: el log no puede narrar ficción."""
        from core.intake_log import read_events
        _caso_prestado()
        _marcar_como_copia_prestada(CASE_ID)
        case_manager.guard_escritura(CASE_ID, "00_Input/nuevo.pdf", "intake")
        assert [e for e in read_events(CASE_ID) if e["event"] == "pendiente_checkin"] == []


class TestSobreElCanonNoCambiaNada:
    """El control negativo. Sin él, «no desvía nunca» pasaría los tests de arriba.

    El guard existe para el Drive y ahí sigue igual: es la mitad que **no** se toca, y
    probarla es lo que distingue el arreglo de una desactivación.
    """

    def test_prestado_SIN_manifiesto_sigue_desviando(self, tmp_casos_root):
        _caso_prestado()
        decision = case_manager.guard_escritura(CASE_ID, "00_Input/nuevo.pdf", "intake")
        assert decision.desviar is True, (
            "sobre el canon prestado el guard TIENE que desviar; si no, este arreglo "
            "no es un arreglo, es apagar el guard")

    def test_disponible_escribe_normal_con_o_sin_manifiesto(self, tmp_casos_root):
        case_manager.ensure_case(CASE_ID, titulo="Caso guard")
        _marcar_como_copia_prestada(CASE_ID)
        decision = case_manager.guard_escritura(CASE_ID, "00_Input/nuevo.pdf", "intake")
        assert decision.desviar is False

    def test_el_conflicto_tambien_desvia_en_el_canon(self, tmp_casos_root):
        """`conflicto` es el otro estado que desvía, y no puede quedar fuera."""
        from core.config import caso_path
        from core.utils import read_md, write_md
        _caso_prestado()
        p = caso_path(CASE_ID) / "00_Input" / "_caso.md"
        fm, cuerpo = read_md(p)
        fm["meta"]["estado_repositorio"] = "conflicto"
        write_md(p, fm, cuerpo)
        decision = case_manager.guard_escritura(CASE_ID, "00_Input/nuevo.pdf", "intake")
        assert decision.desviar is True
