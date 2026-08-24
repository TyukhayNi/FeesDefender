"""Paso 4 del Task 6: los detectores de ausencia preguntan por el caso, explicitamente.

Un **detector de ausencia** es un llamador que usa la ruta del fallback PARA SABER si
algo esta, y sigue por otra rama si no. Con `caso_path` devolviendo una ruta inventada,
dos preguntas distintas daban el mismo `False`:

    index = caso_path(cid) / "00_Input" / "_caso.md"
    if not index.exists():        # <- ¿el caso no existe, o el caso existe sin _caso.md?
        return <algo blando>

Esa confusion no es teorica: dos de estos sitios llevan el comentario
`# ensure_case no se llamo aun`, o sea que su autor estaba razonando sobre el CASO
mientras el codigo preguntaba por el FICHERO.

Son **33 sitios en 17 ficheros** (medido). Migrarlos es lo que desbloquea el paso 5:
al invertir el default de `caso_path`, un detector sin guarda pasa de retornar con
gracia a LANZAR.

## Lo que estos tests fijan

Que el comportamiento observable **no cambia** —siguen devolviendo lo blando— y que
ahora distinguen las dos causas. Lo segundo se comprueba con el caso a medias: existe
la carpeta, falta el `_caso.md`.
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


def _a_medias(root):
    """El caso existe pero sin `_caso.md`: la segunda mitad de la distincion."""
    (root / CASO / "00_Input").mkdir(parents=True)
    return root / CASO


# --------------------------------------------------------------------------
# Las dos causas, sobre los diez detectores de `case_manager`
# --------------------------------------------------------------------------

@pytest.mark.parametrize("fn,esperado", [
    ("get_drive_ev_ids", (None, None)),
    ("get_cached_drive_folder_info", (None, None)),
    ("read_bucket_overrides", {}),
])
class TestCasoAusenteFrenteACasoAMedias:
    def test_caso_ausente_devuelve_lo_blando(self, root, fn, esperado):
        import core.case_manager as cm
        assert getattr(cm, fn)("NO-EXISTE") == esperado

    def test_caso_a_medias_devuelve_lo_mismo(self, root, fn, esperado):
        """Misma respuesta, causa distinta. Antes eran indistinguibles."""
        import core.case_manager as cm
        _a_medias(root)
        assert getattr(cm, fn)(CASO) == esperado


class TestLosQueNoDevuelvenValor:
    def test_register_drive_ev_sobre_un_caso_ausente_no_revienta(self, root):
        import core.case_manager as cm
        cm.register_drive_ev("NO-EXISTE", team_id="T", folder_id="F")

    def test_register_expediente_sobre_un_caso_ausente_da_el_defecto(self, root):
        import core.case_manager as cm
        assert cm.register_expediente(
            "NO-EXISTE", "648", "expediente") == "sudespacho_648"

    def test_is_legacy_intake_v1_sobre_un_caso_ausente_es_False(self, root):
        import core.case_manager as cm
        assert cm.is_legacy_intake_v1("NO-EXISTE") is False


# --------------------------------------------------------------------------
# Y ninguno crea nada por el camino
# --------------------------------------------------------------------------

def test_ningun_detector_materializa_el_caso_que_no_existe(root):
    """El criterio de salida (2) de la Fase 1, sobre los detectores.

    Preguntar si un caso existe no puede crearlo. Con el fallback la ruta era
    inventada y nadie la materializaba por accidente, pero eso era suerte del
    codigo, no una propiedad contratada.
    """
    import core.case_manager as cm
    antes = sorted(p.name for p in root.iterdir())
    for fn in ("get_drive_ev_ids", "get_cached_drive_folder_info",
               "read_bucket_overrides", "is_legacy_intake_v1"):
        getattr(cm, fn)("NO-EXISTE")
    cm.read_pull_state("NO-EXISTE", 648)
    assert sorted(p.name for p in root.iterdir()) == antes


class TestReadPullState:
    """Firma propia (`case_id`, `expediente_id`) y valor blando `None`, no `{}`."""

    def test_caso_ausente_devuelve_None(self, root):
        import core.case_manager as cm
        assert cm.read_pull_state("NO-EXISTE", 648) is None

    def test_caso_a_medias_devuelve_None(self, root):
        import core.case_manager as cm
        _a_medias(root)
        assert cm.read_pull_state(CASO, 648) is None


# --------------------------------------------------------------------------
# El test que de verdad muerde: simular la inversion del paso 5
# --------------------------------------------------------------------------
#
# Los tests de arriba son red de REGRESION: pasan antes y despues de migrar,
# porque la migracion no cambia el comportamiento observable de hoy. Eso los hace
# necesarios pero flojos — no distinguen un detector migrado de uno sin migrar.
#
# Este si. Parchea el localizador para que se comporte como en el paso 5 —lanzar
# ante un caso ausente— y exige que los detectores SIGAN devolviendo lo blando. Un
# detector sin guarda propaga la excepcion y muere aqui.


@pytest.fixture
def localizador_estricto(root, monkeypatch):
    """`caso_path` como quedara tras el paso 5: lanza en vez de inventar la ruta."""
    from core.casos import case_locator
    from core.casos.workspace_model import LocalWorkspaceMissing

    real = case_locator.buscar

    def _estricto(case_id):
        d = real(case_id)
        if d is None:
            raise LocalWorkspaceMissing(detalle="simulacion del paso 5")
        return d

    monkeypatch.setattr(case_locator, "path_for", _estricto)
    import core.config as cfg
    monkeypatch.setattr(cfg, "caso_path", _estricto)
    import core.case_manager as cm
    monkeypatch.setattr(cm, "caso_path", _estricto)
    yield


class TestSobrevivenALaInversion:
    """Cada uno de los diez, con el localizador ya estricto."""

    @pytest.mark.parametrize("fn,esperado", [
        ("get_drive_ev_ids", (None, None)),
        ("get_cached_drive_folder_info", (None, None)),
        ("read_bucket_overrides", {}),
    ])
    def test_devuelven_lo_blando_y_no_propagan(self, localizador_estricto, fn, esperado):
        import core.case_manager as cm
        assert getattr(cm, fn)("NO-EXISTE") == esperado

    def test_read_pull_state_no_propaga(self, localizador_estricto):
        import core.case_manager as cm
        assert cm.read_pull_state("NO-EXISTE", 648) is None

    def test_is_legacy_intake_v1_no_propaga(self, localizador_estricto):
        import core.case_manager as cm
        assert cm.is_legacy_intake_v1("NO-EXISTE") is False

    def test_register_expediente_no_propaga(self, localizador_estricto):
        import core.case_manager as cm
        assert cm.register_expediente(
            "NO-EXISTE", "648", "expediente") == "sudespacho_648"

    def test_register_drive_ev_no_propaga(self, localizador_estricto):
        import core.case_manager as cm
        cm.register_drive_ev("NO-EXISTE", team_id="T", folder_id="F")
