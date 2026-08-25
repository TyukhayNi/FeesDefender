"""El guard que impide que un test deje `core.config` apuntando a su `tmp_path`.

## Por qué existe, con las dos mediciones

El patrón `monkeypatch.setenv("CASOS_ROOT", …)` + `importlib.reload(core.config)` es
**asimétrico**: `monkeypatch` deshace el entorno al salir del test, el `reload` no se
deshace solo. El módulo se queda apuntando a un `tmp_path` muerto para todo lo que
corra después.

- **65º cierre (2026-08-25).** El Task 9 fue el primero en preguntarle al catálogo y
  pisó la mina: con la semilla **777** la suite sacó ocho fallos que con la 31337 no
  existían, todos `CASE_LOCKED` sobre un `EV-2026-001` **prestado** que otro fichero
  había dejado en su `tmp_path`. Sin la segunda semilla, ese PR se mergeaba.
- **Task 10 (2026-08-25).** Se arregló entonces la fixture `tmp_casos_root`, que era
  **una** de las fuentes. Una sonda de teardown sobre la suite entera midió que
  seguían fugando **223 tests en 17 módulos**. Tapar un pozo de diecisiete no es tapar
  la fuga: por eso el guard es `autouse` en `conftest` y no un arreglo por fichero.

## Lo que este fichero prueba, y lo que no

Prueba la **lógica** de restauración, que es la parte falsable, incluido el backstop
que lanza cuando la restauración no basta.

Lo que no prueba es el **efecto agregado sobre la suite** —que con el guard puesto la
sonda cuente cero—, porque eso solo se ve corriendo las 3.500 pruebas. Se verificó por
medición y se declara así, no como si un test lo cubriera.
"""
from __future__ import annotations

import importlib
import os

import pytest

from tests.conftest import restaurar_config_si_secuestrada


def _casos_root() -> str:
    from core import config as cfg
    return str(cfg.settings.casos_root)


def test_sin_secuestro_no_hace_nada():
    antes = _casos_root()
    restaurar_config_si_secuestrada(antes, os.environ.get("CASOS_ROOT"))
    assert _casos_root() == antes


def test_restaura_el_secuestro_tipico(tmp_path):
    """El caso exacto del 65º: setenv + reload, y el entorno YA devuelto al salir."""
    from core import config as cfg

    antes = _casos_root()
    antes_env = os.environ.get("CASOS_ROOT")
    mp = pytest.MonkeyPatch()
    mp.setenv("CASOS_ROOT", str(tmp_path / "CASOS"))
    importlib.reload(cfg)
    assert _casos_root() != antes, "el montaje no llegó a secuestrar nada"

    mp.undo()                                          # lo que hace `monkeypatch`…
    restaurar_config_si_secuestrada(antes, antes_env)  # …y lo que el guard añade
    assert _casos_root() == antes


def test_restaura_aunque_el_entorno_SIGA_sucio(tmp_path):
    """La mitad que no es redundante con `monkeypatch`, y la que la medición exigió.

    Aquí el `undo()` **no** ha corrido todavía: es la situación real que se encontró
    al instalar el guard, porque el orden de desmontaje no era el que yo suponía. Si
    la restauración solo recargara, el `reload` releería el `CASOS_ROOT` sucio y
    devolvería exactamente el mismo secuestro — verde y sin arreglar nada.
    """
    from core import config as cfg

    antes = _casos_root()
    antes_env = os.environ.get("CASOS_ROOT")
    mp = pytest.MonkeyPatch()
    mp.setenv("CASOS_ROOT", str(tmp_path / "CASOS"))
    importlib.reload(cfg)
    try:
        restaurar_config_si_secuestrada(antes, antes_env)   # SIN undo previo
        assert _casos_root() == antes
        assert os.environ.get("CASOS_ROOT") == antes_env
    finally:
        mp.undo()
        importlib.reload(cfg)


def test_si_la_restauracion_NO_basta_lanza_en_vez_de_callar(tmp_path, monkeypatch):
    """El backstop. Se ejerce forzando que el `reload` no surta efecto.

    La alternativa cómoda era restaurar y seguir sin comprobar: eso dejaría viva
    cualquier fuga que llegue por una vía distinta de `CASOS_ROOT` —una raíz fijada
    desde un `.env`, o `settings` sustituido a mano— y el guard verde. Un detector que
    informa de que todo está bien cuando no lo está es peor que no tenerlo.

    El mutante es el `reload` inerte y no un montaje realista **a propósito**: hoy no
    conozco una vía real que evada la restauración, y fabricar una para el test sería
    probar el escenario que sé montar en vez del que quiero contratar. Lo que este
    test garantiza es que la rama **no está muerta**.
    """
    from core import config as cfg

    antes = _casos_root()
    antes_env = os.environ.get("CASOS_ROOT")
    mp = pytest.MonkeyPatch()
    mp.setenv("CASOS_ROOT", str(tmp_path / "OTRA"))
    importlib.reload(cfg)
    try:
        monkeypatch.setattr(importlib, "reload", lambda modulo: modulo)
        with pytest.raises(AssertionError, match="secuestrado"):
            restaurar_config_si_secuestrada(antes, antes_env)
    finally:
        monkeypatch.undo()
        mp.undo()
        importlib.reload(cfg)
    assert _casos_root() == antes


def test_repone_el_ENTORNO_aunque_el_modulo_no_haya_cambiado(tmp_path):
    """R8/H8-06: la bomba armada que el guard no veía.

    Un test que ensucia `CASOS_ROOT` **sin recargar** `core.config` deja el módulo
    intacto — así que la comprobación por módulo salía por la rama de «nada que
    hacer»— y el entorno sucio. El siguiente test que recargue hereda la raíz ajena,
    y el guard que debía impedirlo habría estado verde todo el rato.
    """
    antes = _casos_root()
    antes_env = os.environ.get("CASOS_ROOT")
    sucio = str(tmp_path / "SUCIO")
    os.environ["CASOS_ROOT"] = sucio          # a mano: sin monkeypatch y SIN reload
    try:
        assert _casos_root() == antes, "el montaje no debía tocar el módulo"
        restaurar_config_si_secuestrada(antes, antes_env)
        assert os.environ.get("CASOS_ROOT") == antes_env, (
            "el entorno quedó sucio: la restauración solo miró el módulo")
    finally:
        if antes_env is None:
            os.environ.pop("CASOS_ROOT", None)
        else:
            os.environ["CASOS_ROOT"] = antes_env
    assert _casos_root() == antes


def test_el_backstop_NO_vuelca_la_ruta_absoluta(tmp_path, monkeypatch):
    """R8/H8-07: §16 también rige los mensajes que acaban pegados en un PR.

    El backstop se dispara en un log de suite o de CI, que es justo el material que se
    comparte para diagnosticar. La ruta entera revela usuario, unidad y estructura de
    carpetas del despacho sin añadir nada al diagnóstico: para distinguir un `tmp_path`
    muerto de la raíz real bastan la cola y el hecho de que difieran.

    Canarios en las tres formas de ruta que el §16 vigila —Windows, UNC y POSIX—, y no
    solo la del sistema donde corre la suite: el canario de R7/H7-12 cazaba 3 de 8 casos
    justo por probar una sola forma.
    """
    from core import config as cfg

    antes = _casos_root()
    antes_env = os.environ.get("CASOS_ROOT")
    canarios = {
        "windows": tmp_path / "Usuarios" / "SECRETO-WIN" / "CASOS",
        "unc": tmp_path / "servidor" / "SECRETO-UNC" / "CASOS",
        "posix": tmp_path / "mnt" / "SECRETO-POSIX" / "CASOS",
    }
    for nombre, raiz in canarios.items():
        mp = pytest.MonkeyPatch()
        mp.setenv("CASOS_ROOT", str(raiz))
        importlib.reload(cfg)
        try:
            monkeypatch.setattr(importlib, "reload", lambda modulo: modulo)
            with pytest.raises(AssertionError) as exc:
                restaurar_config_si_secuestrada(antes, antes_env)
        finally:
            monkeypatch.undo()
            mp.undo()
            importlib.reload(cfg)
        mensaje = str(exc.value)
        assert str(raiz) not in mensaje, (
            f"[{nombre}] el backstop volcó la ruta absoluta: {mensaje}")
        assert f"SECRETO-{nombre.upper()}" not in mensaje, (
            f"[{nombre}] el backstop filtró un componente intermedio de la ruta")
        assert "CASOS" in mensaje, (
            f"[{nombre}] el backstop dejó de ser diagnosticable: no dice ni la cola")
    assert _casos_root() == antes


def test_el_guard_esta_instalado_y_es_autouse():
    """Un guard opt-in que el autor del próximo fichero olvide llamar no es un guard.

    Se comprueba sobre la fixture real, no sobre el texto del fichero: renombrarla o
    quitarle el `autouse` deja este test rojo.
    """
    from tests import conftest

    fixture = conftest._core_config_no_se_queda_secuestrado
    # pytest 8 expone el marcador como `_fixture_function_marker`; las versiones
    # anteriores lo colgaban del propio callable como `_pytestfixturefunction`. Se
    # miran las dos para que el guard no muera de un salto de versión.
    marca = (getattr(fixture, "_fixture_function_marker", None)
             or getattr(fixture, "_pytestfixturefunction", None))
    assert marca is not None, "no es una fixture de pytest"
    assert marca.autouse is True, "la fixture existe pero NO es autouse"
