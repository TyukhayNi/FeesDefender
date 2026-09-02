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

## Las puertas, tras R22

La primera version puso el rechazo en `alta` y en `verificar_adopcion` —los dos sitios
donde estaba el ejemplo— y **se dejo `revalidar`**, que tambien reemplaza `local_path` y
escribe. Es el mismo error que el defecto original, cometido al arreglarlo. Ahora el
rechazo vive en `_escribir`, que es la frontera por la que pasa toda entrada a disco.

Y el filtro de lectura ocultaba tambien lo **indeterminado**, con lo que una entrada
legitima desaparecia del fichero en la siguiente reescritura: el arreglo perdia datos
(R22/H22-04). Por eso la clasificacion tiene **tres** estados y no un booleano.

| Puerta | Donde | Observable propio |
|---|---|---|
| G-A | `WorkspaceRegistry._escribir` | lanza en vez de persistir, sea quien sea el escritor |
| G-B | `verificar_adopcion` | motivo legible ANTES de la firma humana |
| G-C | `_visibles` en `cargar`/`buscar` | oculta lo canonico heredado, NUNCA lo indeterminado |
| G-D | `clasificar_bajo` | componentes de ruta + identidad fisica del directorio |
| G-E | `CaseWorkspaceResolver._sin_canonicos` | cubre el registro INYECTADO (R22/H22-05) |
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


def _indeterminada_solo(objetivo: Path):
    """Hace INDETERMINADA la clasificacion de `objetivo` y solo la de `objetivo`.

    Un parche global tambien afecta a la entrada que el test da de alta despues, y
    entonces el test muere por la guarda de escritura y no por lo que dice medir.
    """
    real = case_catalog._dentro_fisicamente

    def _falso(candidata, raiz):
        if os.path.normcase(str(candidata)) == os.path.normcase(str(objetivo)):
            return None
        return real(candidata, raiz)

    return _falso


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

    def test_si_no_se_puede_determinar_donde_cae_se_RECHAZA(self, tmp_casos_root,
                                                            monkeypatch):
        """Falla cerrado. Antes devolvia `False` -- o sea «adelante» -- ante un error.

        Se induce el fallo en `os.stat`, que es lo que el codigo usa de verdad. La
        version anterior de este test parcheaba `Path.resolve`, y cuando la comparacion
        fisica paso a `samestat` el parche dejo de tocar nada: **un test puede quedarse
        apuntando a una implementacion que ya no existe y seguir verde por otra via**.
        Aqui se puso rojo, que es la senal correcta.
        """
        real = os.stat

        def _revienta(ruta, *a, **k):
            if "denegado" in str(ruta):
                raise PermissionError("no se puede determinar")
            return real(ruta, *a, **k)

        monkeypatch.setattr(os, "stat", _revienta)
        assert case_catalog.bajo_catalogo(Path("C:/denegado/sitio")) is True

    def test_una_ruta_de_verdad_fuera_sigue_dando_False(self, tmp_casos_root, tmp_path):
        """El otro valor del predicado, para que no sea un `return True` con adornos."""
        fuera = tmp_path / "Desktop" / CASE
        fuera.mkdir(parents=True)
        assert case_catalog.bajo_catalogo(fuera) is False


# --- Lo que R22 dejo sin contratar -------------------------------------------

#: El prefijo extendido de Windows, construido y no escrito: cualquier literal con
#: barras invertidas se degrada al pasar por una tuberia de shell, y ya lo hizo una vez.
_EXT = chr(92) * 2 + "?" + chr(92)


class TestFormasEquivalentesDeRuta:
    """Dos formas de escribir la MISMA carpeta no pueden clasificarse distinto.

    Es la propiedad, y R22 la rompio por dos sitios (H22-01, H22-06). Antes se comparaban
    cadenas normalizadas; ahora, componentes de ruta mas identidad fisica del directorio.
    """

    def test_el_prefijo_extendido_clasifica_igual_que_la_ruta_normal(self,
                                                                     tmp_casos_root):
        from core.config import settings
        dentro = Path(settings.casos_root) / CASE
        dentro.mkdir(parents=True, exist_ok=True)
        extendida = Path(_EXT + str(dentro))
        # Precondicion SIN `assert`: si no fueran el mismo directorio, el test no
        # probaria lo que dice.
        if not os.path.samefile(str(dentro), str(extendida)):
            pytest.skip("este host no trata el prefijo extendido como la misma carpeta")
        assert case_catalog.bajo_catalogo(extendida) is True

    def test_un_catalogo_en_la_raiz_del_volumen_reconoce_a_sus_hijos(self):
        """Con la raiz de un volumen, el viejo `r + os.sep` buscaba un prefijo imposible.

        Se llama a `clasificar_bajo` con la raiz explicita en vez de mover
        `settings.casos_root`, que es un dataclass CONGELADO: parchearlo revienta al
        deshacer el parche, no al ponerlo.
        """
        assert case_catalog.clasificar_bajo(
            Path("C:" + chr(92)), Path("C:" + chr(92))) == case_catalog.DENTRO
        assert case_catalog.clasificar_bajo(
            Path("C:" + chr(92) + "tmp"), Path("C:" + chr(92))) == case_catalog.DENTRO

    def test_un_hermano_con_el_mismo_prefijo_sigue_estando_fuera(self, tmp_casos_root):
        """El falso positivo que la comparacion por componentes tiene que evitar."""
        raiz = Path(str(tmp_casos_root))
        hermano = raiz.parent / (raiz.name + "_x")
        hermano.mkdir(parents=True, exist_ok=True)
        assert case_catalog.bajo_catalogo(hermano) is False


class TestTresEstados:
    """DENTRO / FUERA / INDETERMINADO: los consumidores tienen polaridades opuestas."""

    def test_indeterminado_cuenta_como_DENTRO_para_quien_autoriza(self, tmp_casos_root,
                                                                  monkeypatch):
        monkeypatch.setattr(case_catalog, "_dentro_fisicamente", lambda c, r: None)
        assert case_catalog.bajo_catalogo(Path("C:/lo/que/sea")) is True

    def test_pero_NO_se_oculta_al_leer_el_registro(self, tmp_casos_root, registro,
                                                   tmp_path, monkeypatch):
        """La mitad que costo una perdida de datos (R22/H22-04).

        Ocultar lo indeterminado hacia desaparecer una entrada legitima, y con ella los
        bytes en la siguiente reescritura.
        """
        fuera = tmp_path / "Desktop" / CASE
        fuera.mkdir(parents=True)
        registro.alta(_entrada(fuera))
        monkeypatch.setattr(case_catalog, "_dentro_fisicamente",
                            _indeterminada_solo(fuera))
        assert [Path(e.local_path) for e in registro.cargar()] == [fuera]

    def test_y_una_reescritura_posterior_no_la_borra(self, tmp_casos_root, registro,
                                                     tmp_path, monkeypatch):
        """El defecto entero: ocultar + reescribir desde lo oculto = borrar.

        El parche es SELECTIVO. Uno global haria indeterminada tambien la entrada nueva,
        y `_escribir` la rechazaria: el test moriria por la guarda en vez de por lo que
        dice medir. Un mutante mal apuntado y un test mal apuntado son el mismo error.
        """
        fuera = tmp_path / "Desktop" / CASE
        fuera.mkdir(parents=True)
        registro.alta(_entrada(fuera))
        otra = tmp_path / "Desktop" / "otro"
        otra.mkdir(parents=True)
        monkeypatch.setattr(case_catalog, "_dentro_fisicamente",
                            _indeterminada_solo(fuera))
        registro.alta(WorkspaceEntry(
            case_id=CASE, w_code="W-CANON1", canonical_ref=None, local_path=otra,
            nonce="n2", maquina=MAQUINA, tipo="checkout", ultima_validacion=AHORA,
            schema=SCHEMA_SOPORTADO))
        crudo = (Path(os.environ["FEESDEFENDER_WORKSPACE_REGISTRY"])
                 / "W-CANON1.json").read_text(encoding="utf-8")
        assert fuera.name in crudo, (
            "la entrada indeterminada desaparecio del fichero: ocultar al leer y "
            "reescribir desde lo oculto es borrar")


class TestTodosLosEscritores:
    """La frontera es `_escribir`, no la lista de llamadores que yo recordara."""

    def test_revalidar_tampoco_puede_meter_el_canon(self, canon, registro, tmp_path):
        """R22/H22-02: el segundo escritor que la primera version olvido."""
        fuera = tmp_path / "Desktop" / CASE
        fuera.mkdir(parents=True)
        registro.alta(_entrada(fuera))
        with pytest.raises(WorkspaceUnderCatalogRoot):
            registro.revalidar(REF, local_path=canon)

    def test_y_el_rechazo_no_altera_el_json_previo(self, canon, registro, tmp_path):
        fichero = Path(os.environ["FEESDEFENDER_WORKSPACE_REGISTRY"]) / "W-CANON1.json"
        fuera = tmp_path / "Desktop" / CASE
        fuera.mkdir(parents=True)
        registro.alta(_entrada(fuera))
        antes = fichero.read_text(encoding="utf-8")
        with pytest.raises(WorkspaceUnderCatalogRoot):
            registro.revalidar(REF, local_path=canon)
        assert fichero.read_text(encoding="utf-8") == antes


class TestRaizDelRegistro:
    """R22/H22-03: el constructor tenia su propia definicion, y divergia."""

    def test_una_raiz_relativa_bajo_el_catalogo_se_rechaza(self, tmp_casos_root,
                                                           monkeypatch):
        from core.config import settings
        monkeypatch.chdir(Path(settings.casos_root).parent)
        relativa = Path(Path(settings.casos_root).name) / "registro"
        with pytest.raises(WorkspaceUnderCatalogRoot):
            WorkspaceRegistry(relativa, ahora=AHORA)

    def test_una_junction_que_apunta_al_catalogo_tambien(self, tmp_casos_root, tmp_path):
        from core.config import settings
        enlace = tmp_path / "reg_atajo"
        r = subprocess.run(["cmd", "/c", "mklink", "/J", str(enlace),
                            str(settings.casos_root)],
                           capture_output=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            pytest.skip("no se pudo crear la junction")
        with pytest.raises(WorkspaceUnderCatalogRoot):
            WorkspaceRegistry(enlace / "registro", ahora=AHORA)

    def test_una_raiz_legitima_se_sigue_admitiendo(self, tmp_casos_root, tmp_path):
        """La guarda tiene que poder ser falsa."""
        assert WorkspaceRegistry(tmp_path / "reg_ok", ahora=AHORA) is not None


class TestElSeamInyectado:
    """R22/H22-05: descarte esta guarda por «inerte» y el seam publicado la activa."""

    def test_un_registro_inyectado_no_cuela_el_canon(self, canon, tmp_path):
        from core.casos.workspace_resolver import CaseWorkspaceResolver
        from core.casos.workspace_model import LocalWorkspaceMissing

        class RegistroFalso:
            def buscar(self, ref):
                return [_entrada(canon)]

            def cargar(self):
                return [_entrada(canon)]

        r = CaseWorkspaceResolver(case_catalog.CaseCatalog(), RegistroFalso(),
                                  usuario=USUARIO, maquina=MAQUINA, ahora=AHORA)
        with pytest.raises(LocalWorkspaceMissing):
            r.resolver_por_identidad(REF, drive_accesible=True)
