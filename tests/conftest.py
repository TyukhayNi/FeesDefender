"""Configuración de pytest: aísla el CASOS_ROOT en cada test.

Marcador ``slow``: tests que requieren el motor NLP real (Presidio + spaCy),
OCR real (tesseract) o procesamiento PDF pesado de ``core/anon/``. Se omiten
por defecto (verja de cierre rápida ~segundos) y se ejecutan con ``--runslow``.
El script ``scripts/session_close`` activa ``--runslow`` automáticamente cuando
el commit toca ``core/anon/``.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--runslow",
        action="store_true",
        default=False,
        help="Ejecuta también los tests marcados @pytest.mark.slow "
        "(motor NLP/OCR real; ~3-4 min).",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "slow: test lento (Presidio/spaCy/OCR real). Omitido salvo --runslow.",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--runslow"):
        return
    skip_slow = pytest.mark.skip(reason="lento — usar --runslow para ejecutarlo")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)


def restaurar_config_si_secuestrada(antes: str, antes_env: str | None) -> None:
    """Devuelve `core.config` a `antes`, o lanza diciendo por qué no puede.

    Función y no cuerpo de la fixture para que se pueda **probar**: una fixture de
    teardown solo se ejerce corriendo otro test después, y eso con `pytest-randomly`
    no es una prueba, es una casualidad.

    **Restaura también `CASOS_ROOT`, y eso NO es redundante con `monkeypatch`.**
    Lo primero que escribí daba por hecho que `monkeypatch` se desmonta antes que esta
    fixture —«se monta después, luego se desmonta antes»— y **la medición lo desmintió
    en el primer test**: el entorno seguía apuntando al `tmp_path` cuando el guard
    miraba. Reponer el valor de entrada aquí hace la restauración **independiente del
    orden de desmontaje**, que es la única forma de que un guard `autouse` valga para
    ficheros que aún no existen. El `undo()` posterior de `monkeypatch` repone el mismo
    valor: es idempotente, no una segunda política.
    """
    import importlib

    from core import config as cfg

    # El ENTORNO se repone SIEMPRE, aunque el módulo no haya cambiado. La primera
    # versión salía por aquí en cuanto `cfg.settings` coincidía, y R8/H8-06 lo midió:
    # un test que ensucia `CASOS_ROOT` **sin recargar** `core.config` dejaba el entorno
    # sucio y el módulo intacto, o sea el guard verde y una bomba armada para el
    # siguiente test que sí recargara. Mirar solo el módulo es mirar el síntoma.
    if os.environ.get("CASOS_ROOT") != antes_env:
        if antes_env is None:
            os.environ.pop("CASOS_ROOT", None)
        else:
            os.environ["CASOS_ROOT"] = antes_env

    if str(cfg.settings.casos_root) == antes:
        return
    importlib.reload(cfg)
    if str(cfg.settings.casos_root) != antes:
        raise AssertionError(
            f"`core.config` quedó secuestrado y ni reponer `CASOS_ROOT` + `reload` lo "
            f"devuelve: {_huella_de_raiz(antes)} -> {_huella_de_raiz(cfg.settings.casos_root)}. La raíz se "
            f"está fijando por una vía que esta restauración no ve, así que la fuga "
            f"sobrevive al test y contaminará a los siguientes según el orden que toque")


def _huella_de_raiz(ruta) -> str:
    """Nombre final + huella corta. **Nunca** la ruta absoluta ni un tramo interno (§16).

    El backstop se dispara en un log de suite o de CI, que es justo el material que se
    pega en un PR para diagnosticar. La ruta entera revelaría usuario, unidad y
    estructura de carpetas del despacho sin añadir nada al diagnóstico (R8/H8-07).

    **Y «los dos últimos componentes» no bastaba**, que fue mi primer arreglo: en
    `…/servidor/SECRETO/CASOS` el penúltimo tramo ES un tramo interno, y el canario del
    test lo cazó. La huella resuelve la tensión real —el nombre final casi siempre es
    `CASOS` en las dos rutas, así que sin algo más el mensaje no distinguiría un
    `tmp_path` muerto de la raíz buena— sin revelar de dónde sale.
    """
    import hashlib
    from pathlib import Path

    texto = str(ruta)
    digest = hashlib.sha256(texto.encode("utf-8")).hexdigest()[:8]
    return f"{Path(texto).name}#{digest}"


@pytest.fixture(autouse=True)
def _core_config_no_se_queda_secuestrado():
    """Nadie deja `core.config` apuntando al `tmp_path` de su test. **Autouse.**

    ## El defecto, medido dos veces

    Un test que hace `monkeypatch.setenv("CASOS_ROOT", …)` + `importlib.reload(core.config)`
    deshace la variable de entorno al salir —eso lo hace `monkeypatch`— pero **no** el
    `reload`: el módulo se queda apuntando a un `tmp_path` muerto para todo lo que corra
    después. Mientras nadie consultaba el catálogo daba igual.

    - **65º cierre (2026-08-25).** El Task 9 fue el primero en preguntarle al catálogo y
      pisó la mina: con la semilla 777, `test_repository_checkout` dejaba un `EV-2026-001`
      **prestado** en su `tmp_path` y ocho tests de sala de máquina —mismo `case_id`
      genérico— se encontraban el caso ajeno con lock. Se arregló **la fixture de
      conftest** (`tmp_casos_root`), que era una de las fuentes.
    - **Task 10 (2026-08-25).** Sonda de teardown sobre la suite entera: **223 tests en
      17 módulos** seguían fugando. Arreglar `tmp_casos_root` había tapado un pozo de
      diecisiete.

    ## Por qué aquí y no fichero a fichero

    Porque el arreglo por fichero es el que ya se hizo una vez y dejó dieciséis. La
    restauración es **simétrica del `reload`** y no depende de qué fixture lo provocó:
    si al salir del test `casos_root` no es el de la entrada, se repone la variable de
    entorno y se recarga.

    **No depende del orden de desmontaje**, y ese detalle costó una hipótesis: di por
    hecho que `monkeypatch` se desmonta antes que esta fixture y el primer test lo
    desmintió — al mirar, `CASOS_ROOT` seguía apuntando al `tmp_path`. Ver
    `restaurar_config_si_secuestrada`.

    Barata: el `reload` solo ocurre en los tests que de verdad tocaron la raíz.
    """
    from core import config as cfg

    antes = str(cfg.settings.casos_root)
    antes_env = os.environ.get("CASOS_ROOT")
    yield
    restaurar_config_si_secuestrada(antes, antes_env)


@pytest.fixture(autouse=True)
def _barrera_frontal(tmp_path, monkeypatch):
    """Barrera de la Fase 0, `autouse` en TODA la suite: ver `tests/_barrera.py`.

    Es de scope **función** y no de sesión a propósito: una fixture de sesión se monta
    en el setup del primer test —después de la colección— y no puede proteger un efecto
    de import. `autouse` porque un helper opt-in que el autor olvide llamar no es una
    barrera; `tmp_casos_root` (abajo) sigue siendo opt-in porque prepara datos, no
    protege nada.
    """
    from tests import _barrera

    _barrera.instalar(monkeypatch, raiz_local=tmp_path)


@pytest.fixture
def tmp_casos_root(tmp_path, monkeypatch):
    """Un `CASOS_ROOT` aislado. **Restaura `core.config` al salir.**

    `monkeypatch.setenv` deshace la variable de entorno, pero el `reload` de la
    entrada NO se deshacía solo: el módulo quedaba apuntando al `tmp_path` de ese
    test para todo lo que corriera después. Mientras nadie consultaba el catálogo
    daba igual; en cuanto `sala_maquina` empezó a preguntar por el caso (Fase 1
    dual, Task 9) la fuga se volvió un rojo dependiente del orden: con la semilla
    777, `test_repository_checkout` dejaba un `EV-2026-001` **prestado** en su
    tmp_path y ocho tests de sala de máquina —que usan ese mismo case_id— se
    encontraban el caso ajeno con lock y abortaban.

    El `reload` de salida corre DESPUÉS de que monkeypatch restaure el entorno,
    así que `core.config` vuelve al `CASOS_ROOT` real.
    """
    root = tmp_path / "CASOS"
    root.mkdir()
    monkeypatch.setenv("CASOS_ROOT", str(root))
    # Reimportar settings para que tome el nuevo CASOS_ROOT
    import importlib

    from core import config as cfg

    importlib.reload(cfg)
    try:
        yield Path(root)
    finally:
        monkeypatch.undo()          # devuelve CASOS_ROOT al valor real…
        importlib.reload(cfg)       # …y ahora sí el módulo lo relee
