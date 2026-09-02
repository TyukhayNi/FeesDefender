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

## El workspace aporta el DESTINO, nunca la identidad — y escribí lo contrario

La primera versión de este fichero decía que la identidad salía de `workspace.case_ref`,
«que el resolver ya validó contra el canon». **Es falso**, y R25/H25-01 lo midió: el
resolver conserva el `CaseRef` **pedido** sin enriquecerlo, y `CaseCatalog.localizar` cae a
`case_id` sin contrastar `meta.id_go`. Con eso, una petición con un W-code falso sobre el
canon real era **aceptada por la vía nueva y rechazada por la vieja**: mi cambio abría una
puerta que el código ya tenía cerrada, y tomaba el mutex del namespace equivocado.

Lo cierto es más simple: **el `case_ref` de un workspace es la PETICIÓN, no la PRUEBA.** La
prueba es `meta.id_go` del canon y sigue estando en el catálogo. Que la copia local no
lleve `_caso.md` (`MERGE_EXCLUSIONS`) cambia dónde caen los bytes, no dónde vive la prueba.

Así que hay **una sola regla de identidad** para las dos vías, y el workspace solo decide
la raíz de escritura.

## Y dos cosas más que el diseño destapó

1. **La bandeja solo existe en el canon.** Sobre una copia local no hay
   `_pendiente_checkin` que valga (`MEJORAS #96`), y el desvío se decide por
   `workspace.mode` — no por una segunda consulta al estado, que es lo que R24/H24-02
   demostró imposible.
2. **El modo y la raíz no eran una invariante.** `CaseWorkspace` es un valor público y
   admite un `LOCAL_CHECKOUT` apuntando al canon, con lo que el bypass del guard se
   concedía sobre el propio expediente canónico (R25/H25-03). Se exige aquí, que es donde
   el bypass se concede.

## Lo que este fichero NO prueba, declarado

No hay E2E de `apply`/`reforzar` **en este fichero**: eso vive en
`test_sala_maquina_por_la_costura.py`, con un depósito espía, porque R25/H25-06 midió que
sin él los mutantes del cableado sobreviven.
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


def _hash_arbol(raiz: Path) -> str:
    """Hash del arbol: rutas Y contenidos. Comparar nombres no ve un `append`."""
    import hashlib
    h = hashlib.sha256()
    for f in sorted(p for p in raiz.rglob("*") if p.is_file()):
        h.update(str(f.relative_to(raiz)).encode("utf-8"))
        h.update(f.read_bytes())
    return h.hexdigest()


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
        """Por HASH del arbol, no por nombres de fichero.

        La primera version comparaba `sorted(p.name for p in canon.rglob("*"))`, que no
        ve un `append` a un fichero que ya existia; y remataba con
        `assert CaseCatalog() is not None`, un aserto que **no puede ser falso** si el
        constructor retorna (R25/H25-08). Los dos los escribi yo, y son la clase que
        llevo la sesion entera cazando.
        """
        antes = _hash_arbol(canon)
        d = escritura.deposito(REF, "00_Input/03_Email", "email", clase="contenido",
                               workspace=_ws(WorkspaceMode.LOCAL_CHECKOUT, copia_local))
        d.escribir_texto("x.md", "hola")
        assert _hash_arbol(canon) == antes

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

    def test_una_copia_local_SIN_caso_md_conserva_la_identidad_CANONICA(
            self, canon, copia_local):
        """`_caso.md` no viaja en el checkout, y la prueba de identidad sigue en el canon.

        La primera version afirmaba lo contrario —que la identidad salia del workspace— y
        eso abria la puerta que R25/H25-01 midio. El aserto tambien era flojo
        (`d is not None` sobre una funcion que devuelve o lanza): ahora se comprueba el
        W-code concreto que la costura resolvio.
        """
        assert not (copia_local / "00_Input" / "_caso.md").exists()
        w, raiz, motivo = escritura._identidad_de_workspace(
            REF, _ws(WorkspaceMode.LOCAL_CHECKOUT, copia_local))
        assert (w, raiz, motivo) == ("W-DEPO01", copia_local, None)

    def test_un_W_code_que_NO_es_el_del_canon_se_rechaza(self, canon, copia_local):
        """R25/H25-01: la via nueva aceptaba lo que la historica rechazaba."""
        from core.casos.workspace_model import IdentidadDiscordante
        falsa = CaseRef(case_id=CASE, w_code="W-FALSO1")
        ws = CaseWorkspace(
            case_ref=falsa, mode=WorkspaceMode.LOCAL_CHECKOUT, working_root=copia_local,
            canonical_ref=None, checkout_user=None, checkout_maquina=None,
            checkout_nonce=None, checkout_timestamp=None, validado_en=AHORA,
            procedencia="test")
        with pytest.raises(IdentidadDiscordante):
            escritura.deposito(falsa, "00_Input", "email", clase="contenido",
                               workspace=ws)

    def test_pedir_solo_por_case_id_NO_pierde_el_W_code(self, canon, copia_local):
        """R25/H25-02: mi via devolvia `None` donde la historica da el W-code."""
        solo_id = CaseRef(case_id=CASE)
        ws = CaseWorkspace(
            case_ref=solo_id, mode=WorkspaceMode.LOCAL_CHECKOUT,
            working_root=copia_local, canonical_ref=None, checkout_user=None,
            checkout_maquina=None, checkout_nonce=None, checkout_timestamp=None,
            validado_en=AHORA, procedencia="test")
        assert escritura._identidad_de_workspace(solo_id, ws)[0] == "W-DEPO01"

    def test_un_W_code_con_gramatica_invalida_no_da_namespace(self, canon, copia_local):
        """La rama que el mutante de R25/H25-08 sobrevivio: `_w_code_valido` sin efecto."""
        ws = _ws(WorkspaceMode.LOCAL_SCRATCH, copia_local)
        w, _raiz, motivo = escritura._identidad_de_workspace(
            CaseRef(case_id="sin-w-code-en-el-nombre"), ws)
        assert w == "W-DEPO01" and motivo is None

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

class TestModoYRaizConcuerdan:
    """R25/H25-03: `CaseWorkspace` no exige que el modo case con la raiz."""

    def test_un_modo_LOCAL_apuntando_al_canon_se_rechaza(self, canon):
        """Sin esto, un valor construido a mano se salta el guard sobre el canon."""
        with pytest.raises(ValueError, match="local"):
            escritura.deposito(REF, "00_Input", "email", clase="contenido",
                               workspace=_ws(WorkspaceMode.LOCAL_CHECKOUT, canon))

    def test_un_DRIVE_ACTIVE_fuera_del_catalogo_tambien(self, canon, copia_local):
        with pytest.raises(ValueError, match="drive_active"):
            escritura.deposito(REF, "00_Input", "email", clase="contenido",
                               workspace=_ws(WorkspaceMode.DRIVE_ACTIVE, copia_local))

    def test_pero_la_combinacion_correcta_pasa(self, canon, copia_local):
        """La guarda tiene que poder ser falsa en las dos direcciones."""
        assert escritura.deposito(REF, "00_Input", "e", clase="contenido",
                                  workspace=_ws(WorkspaceMode.DRIVE_ACTIVE, canon))
        assert escritura.deposito(REF, "00_Input", "e", clase="contenido",
                                  workspace=_ws(WorkspaceMode.LOCAL_CHECKOUT,
                                                copia_local))


class TestModoBloqueado:

    def test_un_workspace_bloqueado_se_rechaza(self, canon):
        """No tiene `working_root` por invariante; aceptarlo seria fingir una raíz."""
        bloqueado = _ws(WorkspaceMode.BLOCKED_FOREIGN_CHECKOUT, None)
        with pytest.raises(ValueError, match="bloquead"):
            escritura.deposito(REF, "00_Input", "email", clase="contenido",
                               workspace=bloqueado)
