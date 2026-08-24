"""Los constructores de rutas y la estrictez — lo que la suite ensenio (Task 6).

Un **constructor de rutas** es un helper que toma `case_id`, compone una subruta y la
devuelve: `log_path`, `_revisar_dir`, `_drive_ev_dir`, `manifest_path`... Con el
fallback no decidian nada, PROPAGABAN una ruta inventada a su llamador.

## Por que estos tests estan en `xfail` y no en verde

Intente migrarlos a `localizar()` en el paso 3 y **estaba mal de raiz**. La suite lo
dijo con 18 fallos en 3 ficheros, y el diagnostico fue mio, no de los tests:

`tests/test_local_organizer.py` hace `monkeypatch.setattr(org, "caso_path", ...)`
porque monta el caso FUERA de `CASOS_ROOT` — que es exactamente el escenario
`local_scratch` / `--case-dir` que todo este diseno existe para soportar. Parchear el
binding de modulo es un seam legitimo. Mi migracion importaba `localizar` DENTRO de la
funcion, asi que se saltaba el parche por completo. Mis propias guardas con `buscar()`
tenian el mismo defecto, y habrian disparado la rama elegante contra un caso que si
existe.

Y al diagnosticarlo aparecio lo de fondo: **migrar los constructores era trabajo
redundante.** Al invertir el default de `caso_path` en el paso 5 heredan la estrictez
gratis, y por el seam correcto. El conjunto minimo de cambios es el alta
(`destino_de_alta`), los detectores (`buscar`) y la inversion. Los constructores no se
tocan.

Asi que la propiedad que estos tests fijan es real y sigue siendo el objetivo — solo
que llega en el **paso 5**. Van en `xfail(strict=True)` por la regla del plan: un
`xfail` que empieza a pasar rompe la suite, y es la alarma de que la inversion llego.
"""
from __future__ import annotations

import importlib

import pytest


@pytest.fixture
def root(tmp_path, monkeypatch):
    r = tmp_path / "CASOS"
    r.mkdir()
    monkeypatch.setenv("CASOS_ROOT", str(r))
    from core import config as cfg
    importlib.reload(cfg)
    yield r


CASO = "BaRS9 - Prueba - (W-TEST99) - Vuelta"


def _caso(root):
    (root / CASO / "00_Input").mkdir(parents=True)
    return root / CASO


# --------------------------------------------------- el constructor es estricto

class TestLosConstructoresExigenElCaso:
    # `log_path(case_id)` se RETIRO en el Task 8 (B0-1), asi que los dos tests que
    # vivian aqui —que era estricto y que devolvia la ruta— se quedaron sin sujeto.
    # No se borran en silencio: su propiedad sobrevive en otro sitio y con otra
    # forma. `log_path_de(case_dir)` no puede ser estricto sobre un `case_id`
    # porque ya no recibe uno, que es justo el punto del task: la ruta del log
    # sale del arbol donde estan los bytes, no del catalogo.
    #
    # Lo que fijaban se prueba ahora en `tests/test_intake_log_workspace.py`:
    # `TestLogPathSeRetira` y `TestNoFabricaExpedientes`.

    def test_revisar_dir_de_un_caso_ausente_LANZA(self, root):
        from core.casos.workspace_model import LocalWorkspaceMissing
        from core.sala_lectura import _revisar_dir
        with pytest.raises(LocalWorkspaceMissing):
            _revisar_dir("NO-EXISTE")

    def test_drive_ev_dir_de_un_caso_ausente_LANZA(self, root):
        from core.casos.workspace_model import LocalWorkspaceMissing
        from core.local_organizer import _drive_ev_dir
        with pytest.raises(LocalWorkspaceMissing):
            _drive_ev_dir("NO-EXISTE")

    def test_ninguno_crea_nada_al_lanzar(self, root):
        """Se prueba con `_revisar_dir`: `log_path` se retiro en el Task 8."""
        from core.casos.workspace_model import LocalWorkspaceMissing
        from core.sala_lectura import _revisar_dir
        antes = sorted(p.name for p in root.iterdir())
        with pytest.raises(LocalWorkspaceMissing):
            _revisar_dir("NO-EXISTE")
        assert sorted(p.name for p in root.iterdir()) == antes


# ------------------------------------- los llamadores conservan su rama elegante

class TestLosLlamadoresBlandosNoSeRompen:
    def test_read_events_de_un_caso_ausente_sigue_devolviendo_vacio(self, root):
        """Regresion: la rama elegante sobrevive, ahora explicita."""
        from core.intake_log import read_events
        assert read_events("NO-EXISTE") == []

    def test_read_events_de_un_caso_SIN_log_tambien_devuelve_vacio(self, root):
        """La otra mitad de la distincion: el caso existe, el log no."""
        from core.intake_log import read_events
        _caso(root)
        assert read_events(CASO) == []

    def test_filas_worklist_de_un_caso_ausente_sigue_devolviendo_vacio(self, root):
        from core.sala_lectura import _filas_worklist
        assert _filas_worklist("NO-EXISTE") == []

    def test_build_anon_index_de_un_caso_ausente_no_revienta(self, root):
        from core.local_organizer import _build_anon_index
        r = _build_anon_index("NO-EXISTE")
        assert r == {"por_sha": {}, "por_slug": {}}

    def test_listar_documentos_de_un_caso_ausente_sigue_devolviendo_vacio(self, root):
        from core.local_organizer import _listar_documentos
        assert _listar_documentos("NO-EXISTE") == []
