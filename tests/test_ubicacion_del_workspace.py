"""**Dónde** puede estar la raíz de un workspace. Una propiedad, sin identidad.

## Por qué esto es un fichero aparte

`MEJORAS #124` recibió cuatro rondas adversariales y **ninguna volvió limpia**. El patrón
que dejaron medido: cada arreglo de la invariante modo/raíz rompía la regla de identidad, y
al revés. La causa no era el cuidado, era la **forma**: las dos propiedades vivían en una
función que compartía `canon_dir`, así que no se podían mover por separado.

Al partirlas aparece lo que el acoplamiento escondía: **la ubicación no necesita saber qué
caso es.**

- Un modo **local** exige que la raíz esté **FUERA** del catálogo.
- Un modo **`drive_active`** exige que esté **DENTRO**.

Las dos se contestan con `(modo, raíz, raíz del catálogo)`. Ni `meta.id_go`, ni
`CaseCatalog.localizar`, ni la petición. La versión acoplada preguntaba «¿es *el* canon de
*este* caso?», que **sí** necesita identidad — y de ahí venía el nudo.

## Lo que esta propiedad NO dice, y vive en el fichero de al lado

Que la raíz de un `drive_active` sea **el expediente correcto** es identidad, no ubicación:
lo prueba `test_identidad_del_workspace.py`. Aquí solo se responde «dentro o fuera».

## La frontera, enunciada una vez

> Un modo local escribe fuera del catálogo; `drive_active`, dentro. Y **«no puedo
> determinarlo» cuenta como dentro**, porque quien autoriza lee «no lo sé» como «no».
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from core.casos import case_catalog, ubicacion
from core.casos.workspace_model import CaseRef, CaseWorkspace, WorkspaceMode

AHORA = "2026-09-02T12:00:00Z"
REF = CaseRef(case_id="Caso cualquiera", w_code="W-UBICA1")


def _ws(modo: WorkspaceMode, raiz: Path) -> CaseWorkspace:
    return CaseWorkspace(
        case_ref=REF, mode=modo, working_root=raiz, canonical_ref=None,
        checkout_user=None, checkout_maquina=None, checkout_nonce=None,
        checkout_timestamp=None, validado_en=AHORA, procedencia="test")


class TestLocalEscribeFUERA:

    def test_una_copia_fuera_del_catalogo_pasa(self, tmp_casos_root, tmp_path):
        fuera = tmp_path / "Desktop" / "Caso"
        fuera.mkdir(parents=True)
        ubicacion.exigir_coherente(_ws(WorkspaceMode.LOCAL_CHECKOUT, fuera))

    def test_el_propio_canon_se_rechaza(self, tmp_casos_root):
        raiz = Path(str(tmp_casos_root)) / "Caso"
        raiz.mkdir(parents=True)
        with pytest.raises(ubicacion.UbicacionIncoherente, match="local"):
            ubicacion.exigir_coherente(_ws(WorkspaceMode.LOCAL_CHECKOUT, raiz))

    def test_el_canon_de_OTRO_caso_tambien(self, tmp_casos_root):
        """R26/H26-01: lo que la version acoplada dejaba pasar.

        Preguntaba «¿es el canon de ESTE caso?», asi que la carpeta de OTRO expediente
        pasaba — y se escribia en el sin desviar, con ese otro prestado a otra maquina.
        """
        otro = Path(str(tmp_casos_root)) / "Otro caso"
        otro.mkdir(parents=True)
        with pytest.raises(ubicacion.UbicacionIncoherente):
            ubicacion.exigir_coherente(_ws(WorkspaceMode.LOCAL_CHECKOUT, otro))

    def test_un_DESCENDIENTE_del_catalogo_tambien(self, tmp_casos_root):
        hondo = Path(str(tmp_casos_root)) / "Caso" / "01_Procesado" / "sub"
        hondo.mkdir(parents=True)
        with pytest.raises(ubicacion.UbicacionIncoherente):
            ubicacion.exigir_coherente(_ws(WorkspaceMode.LOCAL_SCRATCH, hondo))

    def test_y_una_junction_que_apunta_dentro(self, tmp_casos_root, tmp_path):
        """Lexicamente esta fuera; fisicamente es el catalogo."""
        enlace = tmp_path / "atajo"
        r = subprocess.run(["cmd", "/c", "mklink", "/J", str(enlace),
                            str(tmp_casos_root)],
                           capture_output=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            pytest.skip("no se pudo crear la junction")
        with pytest.raises(ubicacion.UbicacionIncoherente):
            ubicacion.exigir_coherente(_ws(WorkspaceMode.LOCAL_CHECKOUT, enlace / "C"))


class TestDriveActiveEscribeDENTRO:

    def test_una_raiz_del_catalogo_pasa(self, tmp_casos_root):
        raiz = Path(str(tmp_casos_root)) / "Caso"
        raiz.mkdir(parents=True)
        ubicacion.exigir_coherente(_ws(WorkspaceMode.DRIVE_ACTIVE, raiz))

    def test_una_raiz_de_fuera_se_rechaza(self, tmp_casos_root, tmp_path):
        fuera = tmp_path / "Desktop" / "Caso"
        fuera.mkdir(parents=True)
        with pytest.raises(ubicacion.UbicacionIncoherente, match="drive_active"):
            ubicacion.exigir_coherente(_ws(WorkspaceMode.DRIVE_ACTIVE, fuera))


class TestFallaCerrado:

    def test_lo_INDETERMINADO_se_rechaza_en_los_DOS_modos(self, tmp_casos_root,
                                                          tmp_path, monkeypatch):
        """«No puedo determinarlo» no es «cae fuera» ni «cae dentro»: es que no.

        Es la MISMA polaridad en los dos modos, y por eso es una sola frontera y no dos.
        """
        monkeypatch.setattr(case_catalog, "_dentro_fisicamente", lambda c, r: None)
        fuera = tmp_path / "Desktop" / "Caso"
        fuera.mkdir(parents=True)
        with pytest.raises(ubicacion.UbicacionIncoherente):
            ubicacion.exigir_coherente(_ws(WorkspaceMode.LOCAL_CHECKOUT, fuera))
        with pytest.raises(ubicacion.UbicacionIncoherente):
            ubicacion.exigir_coherente(_ws(WorkspaceMode.DRIVE_ACTIVE, fuera))


class TestModoBloqueado:

    def test_no_tiene_ubicacion_que_comprobar(self, tmp_casos_root):
        """Sin raiz no hay pregunta. Se rechaza antes, y con otro error."""
        bloqueado = CaseWorkspace(
            case_ref=REF, mode=WorkspaceMode.BLOCKED_FOREIGN_CHECKOUT,
            working_root=None, canonical_ref=None, checkout_user=None,
            checkout_maquina=None, checkout_nonce=None, checkout_timestamp=None,
            validado_en=AHORA, procedencia="test")
        with pytest.raises(ValueError, match="bloquead"):
            ubicacion.exigir_coherente(bloqueado)


class TestLaFuenteDelCatalogo:

    def test_es_la_que_el_CATALOGO_usa_y_no_otra(self, tmp_casos_root, tmp_path,
                                                 monkeypatch):
        """R25/H25-03: comparar contra `settings.casos_root` rompio dos tests buenos.

        El catalogo resuelve por `case_locator._root()`, y eso es lo que los tests y el
        override del §7.3 parchean. Si esta funcion mirara otra fuente, un expediente
        canonico caeria «fuera» en cuanto las dos divergieran.
        """
        from core.casos import case_locator
        otra_raiz = tmp_path / "OTRO_CATALOGO"
        (otra_raiz / "Caso").mkdir(parents=True)
        monkeypatch.setattr(case_locator, "_root", lambda: otra_raiz)
        # Ahora «el catalogo» es `otra_raiz`, asi que su caso es DENTRO...
        ubicacion.exigir_coherente(_ws(WorkspaceMode.DRIVE_ACTIVE, otra_raiz / "Caso"))
        # ...y lo que era el catalogo antes pasa a estar FUERA.
        viejo = Path(str(tmp_casos_root)) / "Caso"
        viejo.mkdir(parents=True, exist_ok=True)
        ubicacion.exigir_coherente(_ws(WorkspaceMode.LOCAL_CHECKOUT, viejo))


class TestPorLaPUERTA:
    """Los mismos casos, pero comprobados donde la propiedad vive.

    Venian de `test_escritura_sobre_workspace.py`, ejercitados a traves de `deposito()`.
    Probar una propiedad a traves de su consumidor es lo que hacia que un mutante de
    ubicacion matara tests de identidad: el consumidor toca las dos.
    """

    def test_deposito_rechaza_un_LOCAL_sobre_el_canon(self, tmp_casos_root, tmp_path):
        """La integracion sigue cubierta: la costura propaga el rechazo."""
        from core.casos import escritura
        from core import case_manager as cm
        from core.config import caso_path
        import importlib
        importlib.reload(cm)
        nombre = "BaXX9 - Ubi - (W-UBIDEP) - NEGATIVA_OFERTA"
        cm.ensure_case(nombre, titulo=nombre)
        canon = caso_path(nombre)
        ref = CaseRef(case_id=nombre, w_code="W-UBIDEP")
        ws = CaseWorkspace(
            case_ref=ref, mode=WorkspaceMode.LOCAL_CHECKOUT, working_root=canon,
            canonical_ref=None, checkout_user=None, checkout_maquina=None,
            checkout_nonce=None, checkout_timestamp=None, validado_en=AHORA,
            procedencia="test")
        with pytest.raises(ubicacion.UbicacionIncoherente):
            escritura.deposito(ref, "00_Input", "x", clase="contenido", workspace=ws)

