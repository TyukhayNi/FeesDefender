"""La costura escribe donde el llamador ya resolvió (`MEJORAS #124`, alcance recortado).

## Qué se recortó, y por qué

Las rev. 1 y rev. 2 del plan de `#124` intentaban que la costura **resolviera** el
workspace por su cuenta: tabla cerrada de desenlaces del resolver, conducta preservada
para Streamlit, E2E, desbloqueo de la fila #5. Dos rondas adversariales (**R21** y **R24**)
devolvieron `NO-EJECUTABLE` con 20 hallazgos confirmados, y las dos coincidieron en que el
problema era el **alcance**, no el detalle. Decisión de Nikolai el 2026-09-02: recortar.

**Lo que queda es una sola propiedad:** `deposito()` acepta un `CaseWorkspace` **ya
resuelto por el llamador**, y escribe bajo su `working_root`. Quien resuelve es el
entrypoint, que es quien tiene el contexto —reloj, usuario, máquina, acceso a Drive— y
quien ya sabe tratar los errores del resolver. `scripts/sala_maquina.py` lo hace así desde
el Task 9 de la Fase 1: esto no inventa un patrón, extiende el que ya funciona.

Cierra **H18-01**: hasta hoy `deposito(ref, …)` no transportaba `working_root` y la costura
que 3A construyó **solo servía para el canon**.

## Las dos cosas que el diseño cuidadoso destapó, y que no estaban en ningún informe

1. **Una copia local NO tiene `_caso.md`** — está en `MERGE_EXCLUSIONS`. Así que tomar la
   identidad del árbol, como hace `_identidad()`, degradaría la comprobación de tres
   fuentes a dos justo sobre la copia: leería `meta.id_go` vacío y se quedaría con el
   nombre de la carpeta, que es lo que esa función existe para no hacer. **La identidad
   sale de `workspace.case_ref`**, que el resolver ya validó contra el canon.
2. **La bandeja solo existe en el canon.** Sobre una copia local no hay `_pendiente_checkin`
   que valga (`MEJORAS #96`), y el desvío se decide por `workspace.mode`, no por una
   segunda consulta al estado — que es lo que R24/H24-02 demostró imposible.

## Lo que este fichero NO prueba, declarado

No hay E2E: ningún entrypoint pasa todavía un workspace a `deposito()`. Eso es el paso
siguiente y **no** se declara hecho aquí.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.casos import escritura
from core.casos.workspace_model import (CaseRef, CaseWorkspace, WorkspaceMode)

AHORA = "2026-09-02T12:00:00Z"
CASE = "BaXX1 - Prueba - (W-DEPO01) - NEGATIVA_OFERTA"
REF = CaseRef(case_id=CASE, w_code="W-DEPO01")


@pytest.fixture
def canon(tmp_casos_root):
    """El expediente canónico, con su `_caso.md` y su `meta.id_go`."""
    import importlib

    from core import case_manager as cm
    from core.config import caso_path
    importlib.reload(cm)
    cm.ensure_case(CASE, titulo="Caso deposito")
    ruta = caso_path(CASE)
    p = ruta / "00_Input" / "_caso.md"
    txt = p.read_text(encoding="utf-8")
    if "id_go" not in txt:
        p.write_text(txt.replace("meta:", "meta:\n  id_go: W-DEPO01", 1), encoding="utf-8")
    return ruta


@pytest.fixture
def copia_local(tmp_path):
    """La copia de trabajo: SIN `_caso.md`, como la deja un checkout real."""
    d = tmp_path / "Desktop" / CASE
    (d / "00_Input").mkdir(parents=True)
    (d / "MANIFEST_CHECKOUT.json").write_text(
        json.dumps({"generado": AHORA, "n_ficheros": 0, "inventario": {}}),
        encoding="utf-8")
    return d


def _ws(modo: WorkspaceMode, raiz: Path | None) -> CaseWorkspace:
    return CaseWorkspace(
        case_ref=REF, mode=modo, working_root=raiz, canonical_ref=None,
        checkout_user=None, checkout_maquina=None, checkout_nonce=None,
        checkout_timestamp=None, validado_en=AHORA, procedencia="test")


# --- F1: los bytes caen donde el llamador resolvió ----------------------------

class TestEscribeEnElWorkspace:

    def test_un_checkout_local_recibe_los_bytes(self, canon, copia_local):
        d = escritura.deposito(REF, "00_Input/03_Email", "email", clase="contenido",
                               workspace=_ws(WorkspaceMode.LOCAL_CHECKOUT, copia_local))
        destino = d.escribir_texto("x.md", "hola")
        assert destino == copia_local / "00_Input/03_Email/x.md"
        assert destino.read_text(encoding="utf-8") == "hola"

    def test_y_el_canon_no_se_toca(self, canon, copia_local):
        from core.casos.case_catalog import CaseCatalog
        antes = sorted(p.name for p in canon.rglob("*"))
        d = escritura.deposito(REF, "00_Input/03_Email", "email", clase="contenido",
                               workspace=_ws(WorkspaceMode.LOCAL_CHECKOUT, copia_local))
        d.escribir_texto("x.md", "hola")
        assert sorted(p.name for p in canon.rglob("*")) == antes
        assert CaseCatalog() is not None          # el catalogo sigue resolviendo

    def test_un_scratch_tambien(self, canon, copia_local):
        d = escritura.deposito(REF, "00_Input", "manual", clase="contenido",
                               workspace=_ws(WorkspaceMode.LOCAL_SCRATCH, copia_local))
        assert d.escribir_bytes("y.bin", b"\x00").parent == copia_local / "00_Input"


# --- F2: sin workspace, la conducta es EXACTAMENTE la de hoy ------------------

class TestSinWorkspaceNoCambiaNada:

    def test_el_canon_sigue_siendo_el_destino(self, canon):
        """La ausencia del parámetro no puede cambiar una sola ruta."""
        d = escritura.deposito(REF, "00_Input/03_Email", "email", clase="contenido")
        assert d.escribir_texto("x.md", "hola") == canon / "00_Input/03_Email/x.md"


# --- F3: la identidad sale del workspace, no del árbol -------------------------

class TestIdentidad:

    def test_una_copia_local_SIN_caso_md_no_pierde_la_identidad(self, canon,
                                                                copia_local):
        """El punto que el diseño destapó: `_caso.md` no viaja en el checkout.

        Si la identidad se leyera del árbol, aquí no habría `meta.id_go` y la
        comprobación de tres fuentes degradaría al nombre de la carpeta.
        """
        assert not (copia_local / "00_Input" / "_caso.md").exists()
        d = escritura.deposito(REF, "00_Input", "email", clase="contenido", modo="libre",
                               workspace=_ws(WorkspaceMode.LOCAL_CHECKOUT, copia_local))
        assert d is not None

    def test_un_workspace_de_OTRO_caso_se_rechaza(self, canon, copia_local):
        """Dos identidades para una escritura es la puerta de los dos lockfiles."""
        otro = CaseWorkspace(
            case_ref=CaseRef(case_id="otro", w_code="W-OTRO01"),
            mode=WorkspaceMode.LOCAL_CHECKOUT, working_root=copia_local,
            canonical_ref=None, checkout_user=None, checkout_maquina=None,
            checkout_nonce=None, checkout_timestamp=None, validado_en=AHORA,
            procedencia="test")
        from core.casos.workspace_model import IdentidadDiscordante
        with pytest.raises(IdentidadDiscordante):
            escritura.deposito(REF, "00_Input", "email", clase="contenido",
                               workspace=otro)


# --- F4: sobre una copia local NO hay bandeja ---------------------------------

class TestLaBandejaEsDelCanon:

    def test_un_caso_prestado_no_desvia_sobre_la_copia(self, canon, copia_local):
        """`MEJORAS #96`: desviar sobre la copia es una bandeja dentro de la bandeja."""
        import importlib

        from core import case_manager as cm
        importlib.reload(cm)
        cm.escribir_lock(CASE, user="Nikolai", timestamp=AHORA, nonce="n",
                         maquina="ESTA")
        d = escritura.deposito(REF, "00_Input/03_Email", "email", clase="contenido",
                               workspace=_ws(WorkspaceMode.LOCAL_CHECKOUT, copia_local))
        assert d.desviada is False
        assert "_pendiente_checkin" not in str(d.escribir_texto("x.md", "hola"))

    def test_pero_sobre_el_CANON_sigue_desviando(self, canon):
        """La guarda tiene que poder ser verdadera: si no, es inerte."""
        import importlib

        from core import case_manager as cm
        importlib.reload(cm)
        cm.escribir_lock(CASE, user="Otro", timestamp=AHORA, nonce="n", maquina="OTRA")
        d = escritura.deposito(REF, "00_Input/03_Email", "email", clase="contenido",
                               workspace=_ws(WorkspaceMode.DRIVE_ACTIVE, canon))
        assert d.desviada is True


# --- F5: un modo bloqueado no entrega capacidad -------------------------------

class TestModoBloqueado:

    def test_un_workspace_bloqueado_se_rechaza(self, canon):
        """No tiene `working_root` por invariante; aceptarlo seria fingir una raíz."""
        bloqueado = _ws(WorkspaceMode.BLOCKED_FOREIGN_CHECKOUT, None)
        with pytest.raises(ValueError, match="bloquead"):
            escritura.deposito(REF, "00_Input", "email", clase="contenido",
                               workspace=bloqueado)
