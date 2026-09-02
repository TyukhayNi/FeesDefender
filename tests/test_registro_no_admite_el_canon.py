"""El registro de workspaces no admite el CANON como copia local (`MEJORAS #136`).

## El defecto, y por qué era de SITIO y no de comparación

El registro privado es la lista de **copias locales**. El canon no puede estar en él: es
la invariante que `es_copia_prestada` cita en su docstring para confiar en el registro, y
la que el diseño dual da por sentada al derivar «¿sobre qué copia se trabaja?».

Esa invariante **la aplicaba un solo lector** — `resolver_por_ruta` — y ninguno de los dos
escritores. Medido el 2026-09-02 (R21/H21-01), reproducido con sonda: `adoptar` apuntado a
la ruta del canon era **ACEPTADO**, y desde ese momento `es_copia_prestada` devolvía `True`
y `dir_intake` mandaba el intake al canon **sin desviar, con el caso prestado**.

Es alcanzable porque el canon **también** recibe `MANIFEST_CHECKOUT.json` mientras está
prestado (`cmd_checkout` lo sube al Drive, §3.3) — el mismo hecho con el que se descartó el
manifiesto como discriminante, sin cruzarlo con la adopción.

## Las cuatro puertas, y la que deliberadamente NO se puso

R21 recomendaba revalidar «al cargar **y** en `resolver_por_identidad`». Aquí se cierra en
la **frontera de lectura del registro** (G-C), que es por donde el resolver recibe las
entradas. Una segunda comprobación dentro del resolver **no podría ser falsa nunca**: sería
una guarda inerte, que es exactamente la clase de defecto que esta ronda vino a cerrar. Se
hace una vez, en el sitio, y se declara.

| Puerta | Dónde | Observable propio |
|---|---|---|
| G-A | `WorkspaceRegistry.alta` | lanza en vez de persistir |
| G-B | `verificar_adopcion` | motivo legible ANTES de la firma humana |
| G-C | `_leer`/`cargar`/`buscar` | descarta una entrada canónica ya persistida |
| G-D | el predicado: léxico + físico, fallando cerrado | junction y ruta irresoluble |
"""
from __future__ import annotations

import importlib
import json
import os
import subprocess
from pathlib import Path

import pytest

from core.casos import case_catalog, workspace_adopcion, workspace_registry
from core.casos.workspace_model import (CaseRef, WorkspaceUnderCatalogRoot)
from core.casos.workspace_registry import (SCHEMA_SOPORTADO, WorkspaceEntry,
                                           WorkspaceRegistry)

AHORA = "2026-09-02T10:00:00Z"
USUARIO = "Nikolai Tyukhay"
MAQUINA = "ESTA"
CASE = "BaXX1 - Prueba - (W-CANON1) - NEGATIVA_OFERTA"
REF = CaseRef(case_id=CASE, w_code="W-CANON1")


@pytest.fixture
def registro(tmp_path, monkeypatch):
    """El registro vive FUERA del catálogo, como exige su constructor."""
    raiz = tmp_path / "registro_privado"
    monkeypatch.setenv("FEESDEFENDER_WORKSPACE_REGISTRY", str(raiz))
    return WorkspaceRegistry(raiz, ahora=AHORA)


@pytest.fixture
def canon(tmp_casos_root):
    """El caso canónico, PRESTADO a este mismo usuario y máquina.

    Es el estado que hace alcanzable el defecto: el lock es mío, así que las cinco
    comprobaciones de `verificar_adopcion` que existían pasaban.
    """
    from core import case_manager as cm
    from core.config import caso_path
    importlib.reload(cm)
    cm.ensure_case(CASE, titulo="Caso canónico")
    ruta = caso_path(CASE)
    # El manifiesto que `cmd_checkout` deja EN LAS DOS COPIAS (§3.3).
    (ruta / "MANIFEST_CHECKOUT.json").write_text(
        json.dumps({"generado": AHORA, "n_ficheros": 0, "inventario": {}}),
        encoding="utf-8")
    cm.escribir_lock(CASE, user=USUARIO, timestamp=AHORA, nonce="n1", maquina=MAQUINA)
    return ruta


def _entrada(ruta: Path) -> WorkspaceEntry:
    return WorkspaceEntry(
        case_id=CASE, w_code="W-CANON1", canonical_ref=None, local_path=ruta,
        nonce="n1", maquina=MAQUINA, tipo="checkout", ultima_validacion=AHORA,
        schema=SCHEMA_SOPORTADO)


# --- G-A: la frontera que ESCRIBE --------------------------------------------

class TestAltaRechaza:

    def test_alta_rechaza_una_ruta_bajo_el_catalogo(self, canon, registro):
        """La puerta que faltaba. `alta` solo miraba si la ruta era de OTRO caso."""
        with pytest.raises(WorkspaceUnderCatalogRoot):
            registro.alta(_entrada(canon))

    def test_y_no_deja_nada_escrito(self, canon, registro):
        """Rechazar y persistir a medias sería peor que no rechazar."""
        with pytest.raises(WorkspaceUnderCatalogRoot):
            registro.alta(_entrada(canon))
        assert registro.cargar() == []

    def test_una_copia_FUERA_del_catalogo_se_sigue_admitiendo(self, canon, registro,
                                                              tmp_path):
        """La guarda tiene que poder ser falsa: si no, es inerte.

        Éste es el aserto que distingue un guard de un `return False` con adornos.
        """
        fuera = tmp_path / "Desktop" / CASE
        fuera.mkdir(parents=True)
        registro.alta(_entrada(fuera))
        assert [Path(e.local_path) for e in registro.cargar()] == [fuera]


# --- G-B: la puerta humana ----------------------------------------------------

class TestAdopcionRechaza:

    def test_verificar_adopcion_rechaza_el_canon(self, canon):
        """Y con un motivo legible: es lo que el humano lee antes de firmar."""
        v = workspace_adopcion.verificar_adopcion(
            canon, REF, usuario=USUARIO, maquina=MAQUINA, ahora=AHORA)
        assert not v.ok
        assert "catalogo" in v.motivo.lower() or "catálogo" in v.motivo.lower()

    def test_adoptar_el_canon_lanza_y_no_escribe_ni_entrada_ni_evento(
            self, canon, registro):
        """`adoptar` también emite `checkout_adoptado`: adoptar el canon lo escribía
        en el log del canon, prestado."""
        log = canon / "00_Input" / "_intake_log.jsonl"
        antes = log.read_text(encoding="utf-8") if log.is_file() else ""
        with pytest.raises(workspace_adopcion.AdopcionRechazada):
            workspace_adopcion.adoptar(canon, REF, registry=registro,
                                       usuario=USUARIO, maquina=MAQUINA, ahora=AHORA)
        despues = log.read_text(encoding="utf-8") if log.is_file() else ""
        assert registro.cargar() == []
        assert despues == antes, "adoptar rechazado no puede dejar evento en el canon"


# --- G-C: la frontera que LEE (cubre al resolver sin duplicar la guarda) ------

class TestLecturaDescarta:

    def _persistir_a_mano(self, registro, ruta: Path) -> None:
        """Fabrica el estado heredado: una entrada canónica YA en disco.

        Se escribe el JSON directamente, sin pasar por `alta`, porque `alta` es
        justamente la puerta que ahora lo impide. Es el registro de una máquina que
        adoptó el canon antes de este arreglo.
        """
        raiz = Path(os.environ["FEESDEFENDER_WORKSPACE_REGISTRY"])
        raiz.mkdir(parents=True, exist_ok=True)
        (raiz / "W-CANON1.json").write_text(
            json.dumps([_entrada(ruta).a_json()], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")

    def test_cargar_descarta_la_entrada_canonica_heredada(self, canon, registro):
        self._persistir_a_mano(registro, canon)
        assert registro.cargar() == []

    def test_buscar_tampoco_la_devuelve(self, canon, registro):
        """`buscar` lee por W-code sin pasar por `cargar`: su propia puerta."""
        self._persistir_a_mano(registro, canon)
        assert registro.buscar(REF) == []

    def test_el_resolver_no_la_ve(self, canon, registro):
        """Lo que de verdad importaba: el resolver deja de dar el canon como
        `LOCAL_CHECKOUT`. No hay guarda nueva en el resolver — la hereda de G-C."""
        from core.casos.workspace_resolver import CaseWorkspaceResolver
        from core.casos.workspace_model import LocalWorkspaceMissing
        self._persistir_a_mano(registro, canon)
        r = CaseWorkspaceResolver(case_catalog.CaseCatalog(), registro,
                                  usuario=USUARIO, maquina=MAQUINA, ahora=AHORA)
        with pytest.raises(LocalWorkspaceMissing):
            r.resolver_por_identidad(REF, drive_accesible=True)

    def test_es_copia_prestada_vuelve_a_ser_falsa(self, canon, registro):
        """La propiedad de punta a punta: el intake vuelve a desviar."""
        from core import case_manager as cm
        importlib.reload(cm)
        self._persistir_a_mano(registro, canon)
        assert cm.es_copia_prestada(CASE) is False
        destino = cm.dir_intake(CASE, "00_Input/03_Email", "email")
        assert "_pendiente_checkin" in str(destino)


# --- G-D: el predicado ---------------------------------------------------------

class TestPredicado:

    def test_ruta_relativa_al_catalogo_tambien_cae(self, tmp_casos_root, monkeypatch):
        """Sin `abspath`, una ruta relativa esquivaba la comparación de cadenas."""
        from core.config import settings
        monkeypatch.chdir(Path(settings.casos_root).parent)
        relativa = Path(Path(settings.casos_root).name) / CASE
        assert case_catalog.bajo_catalogo(relativa) is True

    def test_una_junction_al_catalogo_no_lo_saca_de_el(self, tmp_casos_root, tmp_path):
        """La comparación léxica sola da 'fuera' a algo que físicamente es el canon."""
        from core.config import settings
        enlace = tmp_path / "atajo"
        r = subprocess.run(["cmd", "/c", "mklink", "/J", str(enlace),
                            str(settings.casos_root)],
                           capture_output=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            pytest.skip(f"no se pudo crear la junction: {r.stdout} {r.stderr}")
        assert case_catalog.bajo_catalogo(enlace / CASE) is True

    def test_si_no_se_puede_resolver_donde_cae_se_RECHAZA(self, tmp_casos_root,
                                                          monkeypatch):
        """Falla cerrado. Antes devolvía `False` — o sea «adelante» — ante un error.

        Rama defensiva: se ejercita forzando el fallo, porque su disparador natural
        (rutas inválidas, MAX_PATH) es raro. Se declara como tal.
        """
        def _revienta(self, *a, **k):
            raise OSError("no se puede resolver")
        monkeypatch.setattr(Path, "resolve", _revienta)
        assert case_catalog.bajo_catalogo(Path("C:/cualquier/sitio")) is True

    def test_una_ruta_de_verdad_fuera_sigue_dando_False(self, tmp_casos_root, tmp_path):
        """El otro valor del predicado, para que no sea un `return True` con adornos."""
        fuera = tmp_path / "Desktop" / CASE
        fuera.mkdir(parents=True)
        assert case_catalog.bajo_catalogo(fuera) is False
