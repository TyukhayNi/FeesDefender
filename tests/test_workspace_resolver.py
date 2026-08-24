"""`CaseWorkspaceResolver` — el bibliotecario (Fase 1, Task 7).

Es la pieza que responde la pregunta con la que arranco todo el diseño: **¿sobre qué
copia se trabaja, y qué está permitido en ella?** Las otras tres solo le dan datos:

    CaseCatalog        que existe en el canon, y que dice el canon de ello
    WorkspaceRegistry  que copias locales conoce ESTA maquina
    CaseWorkspaceResolver  -> decide, o bloquea

Implementa la matriz del **§7** paso por paso: §7.1 la entrada por ruta explicita
(`--case-dir`), §7.2 la entrada por identificador.

## Lo que estos tests vigilan de verdad

Dos cosas distintas, y conviene no confundirlas:

1. **La matriz** — un camino por fila del §7.2 y del §7.1. Son los escenarios.
2. **La pureza** (R7/H7-11) — que el reloj y la identidad se INYECTEN de verdad. Un
   constructor puede aceptar los tres argumentos y luego llamar a `datetime.now()`
   por dentro; los tests de escenario pasan igual. Por eso hay tres pruebas que no
   miran resultados sino **procedencia**: globales parcheados para que lancen,
   determinismo con entrada identica, y variacion aislada por inyeccion.
"""
from __future__ import annotations

import importlib
import textwrap

import pytest


AHORA = "2026-08-24T12:00:00Z"
YO = "nikolai"
ESTA = "ESTA-MAQUINA"
CASO = "BaRS9 - Prueba - (W-TEST99) - Vuelta"


@pytest.fixture
def root(tmp_path, monkeypatch):
    r = tmp_path / "CASOS"
    r.mkdir()
    monkeypatch.setenv("CASOS_ROOT", str(r))
    from core import config as cfg
    importlib.reload(cfg)
    from core.casos import case_locator
    monkeypatch.setattr(case_locator, "_root", lambda: r)
    yield r


def _canon(root, *, estado=None, titular=None, maquina=None, nonce=None,
           w_code="W-TEST99", nombre=CASO):
    """Un caso en el catalogo, con el lock que se le indique."""
    d = root / nombre / "00_Input"
    d.mkdir(parents=True, exist_ok=True)
    meta = {"id_go": w_code}
    if estado:
        meta["estado_repositorio"] = estado
    if titular:
        meta["checkout_user"] = titular
    if maquina:
        meta["checkout_maquina"] = maquina
    if nonce:
        meta["checkout_nonce"] = nonce
    if estado == "prestado":
        meta.setdefault("checkout_timestamp", AHORA)
    cuerpo = "\n".join(f"  {k}: {v}" for k, v in meta.items())
    (d / "_caso.md").write_text(
        textwrap.dedent(f"---\nmeta:\n{cuerpo}\n---\n"), encoding="utf-8")
    return root / nombre


def _resolver(tmp_path, *, usuario=YO, maquina=ESTA, ahora=AHORA):
    from core.casos.case_catalog import CaseCatalog
    from core.casos.workspace_registry import WorkspaceRegistry
    from core.casos.workspace_resolver import CaseWorkspaceResolver
    return CaseWorkspaceResolver(
        CaseCatalog(),
        WorkspaceRegistry(tmp_path / "registro", ahora=ahora),
        usuario=usuario, maquina=maquina, ahora=ahora)


def _entrada_local(tmp_path, *, nonce="n1", maquina=ESTA, tipo="checkout",
                   w_code="W-TEST99", sufijo=""):
    from core.casos.workspace_registry import SCHEMA_SOPORTADO, WorkspaceEntry
    local = tmp_path / f"local{sufijo}" / CASO
    (local / "00_Input").mkdir(parents=True, exist_ok=True)
    return WorkspaceEntry(
        case_id=CASO, w_code=w_code, canonical_ref=None, local_path=local,
        nonce=nonce, maquina=maquina, tipo=tipo, ultima_validacion=AHORA,
        schema=SCHEMA_SOPORTADO)


# ==========================================================================
# §7.2 — entrada por identificador
# ==========================================================================

class TestPorIdentidad:

    def test_disponible_da_drive_active(self, root, tmp_path):
        """§7.2.4 — nadie lo tiene: se trabaja en el canon."""
        from core.casos.workspace_model import CaseRef, WorkspaceMode
        _canon(root, estado="disponible")
        ws = _resolver(tmp_path).resolver_por_identidad(
            CaseRef(w_code="W-TEST99"), drive_accesible=True)
        assert ws.mode == WorkspaceMode.DRIVE_ACTIVE
        assert ws.working_root == root / CASO

    def test_prestado_por_MI_con_nonce_que_casa_da_local_checkout(self, root, tmp_path):
        """§7.2.5-6 — el prestamo es mio y el registro lo confirma."""
        from core.casos.workspace_model import CaseRef, WorkspaceMode
        _canon(root, estado="prestado", titular=YO, maquina=ESTA, nonce="n1")
        r = _resolver(tmp_path)
        r.registry.alta(_entrada_local(tmp_path, nonce="n1"))
        ws = r.resolver_por_identidad(CaseRef(w_code="W-TEST99"), drive_accesible=True)
        assert ws.mode == WorkspaceMode.LOCAL_CHECKOUT
        assert ws.working_root == tmp_path / "local" / CASO

    def test_prestado_por_OTRA_maquina_bloquea(self, root, tmp_path):
        """§7.2.7 — lo tiene otro: no se toca."""
        from core.casos.workspace_model import CaseLocked, CaseRef
        _canon(root, estado="prestado", titular="otro", maquina="OTRA", nonce="n9")
        with pytest.raises(CaseLocked):
            _resolver(tmp_path).resolver_por_identidad(
                CaseRef(w_code="W-TEST99"), drive_accesible=True)

    def test_el_bloqueo_dice_QUIEN_y_CUANDO_pero_no_la_ruta(self, root, tmp_path):
        """§16 + §10: el mensaje sirve para llamar al titular, no para husmear."""
        from core.casos.workspace_model import CaseLocked, CaseRef
        _canon(root, estado="prestado", titular="otro", maquina="OTRA", nonce="n9")
        with pytest.raises(CaseLocked) as exc:
            _resolver(tmp_path).resolver_por_identidad(
                CaseRef(w_code="W-TEST99"), drive_accesible=True)
        texto = str(exc.value)
        assert "otro" in texto and "OTRA" in texto
        assert str(root) not in texto and str(tmp_path) not in texto

    def test_prestado_por_MI_con_nonce_DISTINTO_es_LockMismatch(self, root, tmp_path):
        """§7.2.7 — el lock dice mi nombre pero no es mi prestamo."""
        from core.casos.workspace_model import CaseRef, LockMismatch
        _canon(root, estado="prestado", titular=YO, maquina=ESTA, nonce="n1")
        r = _resolver(tmp_path)
        r.registry.alta(_entrada_local(tmp_path, nonce="OTRO-NONCE"))
        with pytest.raises(LockMismatch):
            r.resolver_por_identidad(CaseRef(w_code="W-TEST99"), drive_accesible=True)

    def test_prestado_por_MI_SIN_entrada_de_registro_no_se_adopta_solo(self, root, tmp_path):
        """§15 — un checkout que esta maquina no registro exige adopcion explicita."""
        from core.casos.workspace_model import CaseRef, LocalWorkspaceMissing
        _canon(root, estado="prestado", titular=YO, maquina=ESTA, nonce="n1")
        with pytest.raises(LocalWorkspaceMissing):
            _resolver(tmp_path).resolver_por_identidad(
                CaseRef(w_code="W-TEST99"), drive_accesible=True)

    def test_conflicto_con_drive_accesible_bloquea(self, root, tmp_path):
        """§7.2.8 — el canon dice conflicto, y eso bloquea antes que nada."""
        from core.casos.workspace_model import CaseConflict, CaseRef
        _canon(root, estado="conflicto")
        with pytest.raises(CaseConflict):
            _resolver(tmp_path).resolver_por_identidad(
                CaseRef(w_code="W-TEST99"), drive_accesible=True)

    def test_OFFLINE_el_conflicto_no_se_ve_y_eso_es_correcto(self, root, tmp_path):
        """Mi primer test exigia que el conflicto bloqueara tambien offline, y
        estaba mal: el §7.2 lee el estado compartido en el paso (3) **si Drive
        esta accesible**, y comprueba el conflicto en el (8). Sin Drive no hay
        canon que leer, asi que no hay conflicto que ver — se cae a (9)-(10).

        No es un agujero: el §7.1 cierra por el otro lado exigiendo que **el
        checkin revalide el nonce contra Drive**. El conflicto aflora al publicar,
        que es cuando importa. Lo que NO puede pasar es publicar sin revalidar, y
        de eso responde el checkin, no el resolver offline.
        """
        from core.casos.workspace_model import (Capability, CaseRef)
        _canon(root, estado="conflicto")
        r = _resolver(tmp_path)
        r.registry.alta(_entrada_local(tmp_path, nonce="n1"))
        ws = r.resolver_por_identidad(CaseRef(w_code="W-TEST99"),
                                      drive_accesible=False)
        # Se permite seguir trabajando en local, pero NO publicar: la garantia
        # que sustituye a la comprobacion que no se pudo hacer.
        assert not ws.permite(Capability.MUTATE_CANONICAL)

    def test_drive_inaccesible_con_UN_checkout_da_local_sin_mutar_el_canon(self, root, tmp_path):
        """§7.2.9 — se puede trabajar offline, pero no publicar."""
        from core.casos.workspace_model import Capability, CaseRef, WorkspaceMode
        _canon(root, estado="prestado", titular=YO, maquina=ESTA, nonce="n1")
        r = _resolver(tmp_path)
        r.registry.alta(_entrada_local(tmp_path, nonce="n1"))
        ws = r.resolver_por_identidad(CaseRef(w_code="W-TEST99"), drive_accesible=False)
        assert ws.mode == WorkspaceMode.LOCAL_CHECKOUT
        # `CHECKIN`, no `MUTATE_CANONICAL`: este modo nunca tuvo la segunda, asi
        # que afirmarlo pasaba con el mecanismo desactivado (lo cazo la mutacion).
        assert not ws.permite(Capability.CHECKIN)
        assert ws.permite(Capability.WRITE_CASE)

    def test_drive_inaccesible_con_DOS_candidatos_es_ambiguo(self, root, tmp_path):
        """§7.2.10 — sin canon al que preguntar, dos copias no se desempatan solas.

        **El caso existe en el catalogo a proposito.** Sin el, la resolucion cae por
        `_solo_local` y la ambiguedad la levanta OTRA guarda — el test pasaba igual
        con la del camino offline desactivada, y eso lo cazo la mutacion.
        """
        from core.casos.workspace_model import AmbiguousCase, CaseRef
        _canon(root, estado="prestado", titular=YO, maquina=ESTA, nonce="n1")
        r = _resolver(tmp_path)
        r.registry.alta(_entrada_local(tmp_path, nonce="n1", sufijo="_a"))
        r.registry.alta(_entrada_local(tmp_path, nonce="n2", sufijo="_b"))
        with pytest.raises(AmbiguousCase):
            r.resolver_por_identidad(CaseRef(w_code="W-TEST99"), drive_accesible=False)

    def test_drive_inaccesible_y_SIN_candidato_aborta(self, root, tmp_path):
        from core.casos.workspace_model import CaseRef, RuntimeCannotAccessWorkspace
        _canon(root, estado="disponible")
        with pytest.raises(RuntimeCannotAccessWorkspace):
            _resolver(tmp_path).resolver_por_identidad(
                CaseRef(w_code="W-TEST99"), drive_accesible=False)

    def test_un_scratch_se_resuelve_por_su_identidad(self, root, tmp_path):
        """§7.2 final — un scratch conocido por el registro es resoluble."""
        from core.casos.workspace_model import CaseRef, WorkspaceMode
        r = _resolver(tmp_path)
        r.registry.alta(_entrada_local(tmp_path, tipo="scratch", nonce="s1"))
        ws = r.resolver_por_identidad(CaseRef(w_code="W-TEST99"), drive_accesible=True)
        assert ws.mode == WorkspaceMode.LOCAL_SCRATCH

    def test_un_scratch_que_choca_con_un_caso_publicado_exige_case_dir(self, root, tmp_path):
        from core.casos.workspace_model import AmbiguousCase, CaseRef
        _canon(root, estado="disponible")
        r = _resolver(tmp_path)
        r.registry.alta(_entrada_local(tmp_path, tipo="scratch", nonce="s1"))
        with pytest.raises(AmbiguousCase):
            r.resolver_por_identidad(CaseRef(w_code="W-TEST99"), drive_accesible=True)


# ==========================================================================
# §7.1 — entrada por ruta explicita
# ==========================================================================

class TestPorRuta:

    def test_una_ruta_bajo_casos_root_se_rechaza(self, root, tmp_path):
        """§5.1 — un checkout dentro de la biblioteca mezcla copia y original."""
        from core.casos.workspace_model import WorkspaceUnderCatalogRoot
        dentro = root / "copia-de-trabajo"
        (dentro / "00_Input").mkdir(parents=True)
        with pytest.raises(WorkspaceUnderCatalogRoot):
            _resolver(tmp_path).resolver_por_ruta(dentro, drive_accesible=True)

    def test_una_ruta_que_no_existe_se_rechaza(self, root, tmp_path):
        """La ruta esta REGISTRADA pero ya no existe en disco.

        Con una ruta sin registrar el test pasaba igual —lo rechazaba la guarda
        del registro, no la de existencia— y la mutacion lo cazo. Registrarla
        primero aisla la frontera: lo unico que falla es que la carpeta no esta.
        """
        import shutil
        from core.casos.workspace_model import LocalWorkspaceMissing
        r = _resolver(tmp_path)
        e = _entrada_local(tmp_path, nonce="n1")
        r.registry.alta(e)
        shutil.rmtree(e.local_path)          # registrada, pero borrada del disco
        with pytest.raises(LocalWorkspaceMissing):
            r.resolver_por_ruta(e.local_path, drive_accesible=True)

    def test_una_ruta_registrada_como_scratch_da_local_scratch(self, root, tmp_path):
        from core.casos.workspace_model import WorkspaceMode
        r = _resolver(tmp_path)
        e = _entrada_local(tmp_path, tipo="scratch", nonce="s1")
        r.registry.alta(e)
        ws = r.resolver_por_ruta(e.local_path, drive_accesible=True)
        assert ws.mode == WorkspaceMode.LOCAL_SCRATCH

    def test_una_ruta_desconocida_por_el_registro_aborta(self, root, tmp_path):
        """§7.1.7 — sin entrada, identidad y registro se contradicen."""
        from core.casos.workspace_model import LocalWorkspaceMissing
        suelta = tmp_path / "suelta" / CASO
        (suelta / "00_Input").mkdir(parents=True)
        with pytest.raises(LocalWorkspaceMissing):
            _resolver(tmp_path).resolver_por_ruta(suelta, drive_accesible=True)

    def test_offline_por_ruta_no_puede_mutar_el_canon(self, root, tmp_path):
        """§7.1.5 — el trabajo offline se permite; publicar, no."""
        from core.casos.workspace_model import Capability
        _canon(root, estado="prestado", titular=YO, maquina=ESTA, nonce="n1")
        r = _resolver(tmp_path)
        e = _entrada_local(tmp_path, nonce="n1")
        r.registry.alta(e)
        ws = r.resolver_por_ruta(e.local_path, drive_accesible=False)
        assert not ws.permite(Capability.CHECKIN)
        assert ws.permite(Capability.WRITE_CASE)


# ==========================================================================
# El diagnostico: bloquear devolviendo, en vez de lanzar
# ==========================================================================

class TestDiagnostico:
    def test_con_diagnostico_devuelve_el_modo_bloqueado_en_vez_de_lanzar(self, root, tmp_path):
        """La excepcion del contrato: un llamador que quiere PINTAR el estado."""
        from core.casos.workspace_model import CaseRef, WorkspaceMode
        _canon(root, estado="prestado", titular="otro", maquina="OTRA", nonce="n9")
        ws = _resolver(tmp_path).resolver_por_identidad(
            CaseRef(w_code="W-TEST99"), drive_accesible=True, diagnostico=True)
        assert ws.mode == WorkspaceMode.BLOCKED_FOREIGN_CHECKOUT

    def test_el_modo_bloqueado_no_concede_nada_mutante(self, root, tmp_path):
        from core.casos.workspace_model import Capability, CaseRef
        _canon(root, estado="prestado", titular="otro", maquina="OTRA", nonce="n9")
        ws = _resolver(tmp_path).resolver_por_identidad(
            CaseRef(w_code="W-TEST99"), drive_accesible=True, diagnostico=True)
        for cap in (Capability.WRITE_CASE, Capability.INGEST,
                    Capability.MUTATE_CANONICAL):
            assert not ws.permite(cap)


# ==========================================================================
# La PUREZA (R7/H7-11) — no se enuncia, se contrata
# ==========================================================================

class TestPureza:

    def test_no_consulta_el_reloj_ni_la_identidad_globales(self, root, tmp_path, monkeypatch):
        """Los tres globales, parcheados para que LANCEN.

        Un constructor puede aceptar `usuario`, `maquina` y `ahora` y luego
        ignorarlos llamando a `datetime.now()` por dentro; los tests de escenario
        pasan igual. Este es el unico que lo caza.
        """
        import datetime as _dt
        import getpass
        import socket

        def _prohibido(*a, **k):
            raise AssertionError("el resolver consulto un global en vez de su inyeccion")

        monkeypatch.setattr(getpass, "getuser", _prohibido)
        monkeypatch.setattr(socket, "gethostname", _prohibido)

        class _RelojProhibido(_dt.datetime):
            @classmethod
            def now(cls, tz=None):
                _prohibido()

            @classmethod
            def utcnow(cls):
                _prohibido()

        monkeypatch.setattr(_dt, "datetime", _RelojProhibido)

        from core.casos.workspace_model import CaseRef
        _canon(root, estado="disponible")
        _resolver(tmp_path).resolver_por_identidad(
            CaseRef(w_code="W-TEST99"), drive_accesible=True)

    def test_la_misma_entrada_da_el_mismo_workspace(self, root, tmp_path):
        """Determinismo: dos resoluciones identicas son iguales campo a campo."""
        import dataclasses
        from core.casos.workspace_model import CaseRef
        _canon(root, estado="disponible")
        a = _resolver(tmp_path).resolver_por_identidad(
            CaseRef(w_code="W-TEST99"), drive_accesible=True)
        b = _resolver(tmp_path).resolver_por_identidad(
            CaseRef(w_code="W-TEST99"), drive_accesible=True)
        assert dataclasses.asdict(a) == dataclasses.asdict(b)

    def test_variar_SOLO_el_reloj_cambia_SOLO_lo_que_depende_de_el(self, root, tmp_path):
        """Si `ahora` no llegara al valor, `validado_en` seria igual con relojes
        distintos — y eso es exactamente el constructor que acepta e ignora."""
        from core.casos.workspace_model import CaseRef
        _canon(root, estado="disponible")
        a = _resolver(tmp_path, ahora="2026-01-01T00:00:00Z").resolver_por_identidad(
            CaseRef(w_code="W-TEST99"), drive_accesible=True)
        b = _resolver(tmp_path, ahora="2026-12-31T23:59:59Z").resolver_por_identidad(
            CaseRef(w_code="W-TEST99"), drive_accesible=True)
        assert a.validado_en != b.validado_en
        assert a.mode == b.mode
        assert a.working_root == b.working_root
