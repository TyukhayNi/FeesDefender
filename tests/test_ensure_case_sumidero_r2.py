"""Los hallazgos de la R2 adversarial sobre el diff del sumidero (2026-09-05).

Tres de los seis eran defectos MIOS introducidos por el propio arreglo, y el primero es una
regresion que habria bloqueado el primer alta en una maquina nueva. Viven aparte para que se
vea de donde salieron.

Informe literal y adjudicacion: acta de la R2 en `docs/superpowers/`.
"""
from __future__ import annotations

import importlib
import subprocess

import pytest


def _cm():
    from core import case_manager
    importlib.reload(case_manager)
    return case_manager


# ---------------------------------------------------------------------------
# H-01 (ALTO) — la contencion fisica impedia crear la raiz en el primer alta
# ---------------------------------------------------------------------------

def test_un_alta_puede_crear_su_propia_raiz(tmp_path, monkeypatch):
    """La primera version subia al primer ancestro EXISTENTE sin tope, asi que con
    `CASOS_ROOT` todavia sin crear comparaba el PADRE de la raiz contra la raiz y acusaba de
    escapar por un enlace inexistente. Un alta que crea su raiz es legitima y es, de hecho,
    la primera alta de cualquier maquina nueva.
    """
    from core.casos import case_locator

    raiz = tmp_path / "padre" / "missing"
    (tmp_path / "padre").mkdir()
    assert not raiz.exists()
    monkeypatch.setattr(case_locator, "_root", lambda: raiz)

    cm = _cm()
    case_dir = cm.ensure_case("EV-2026-001")

    assert case_dir.is_dir()
    assert (case_dir / "00_Input" / "_caso.md").is_file()
    assert raiz.is_dir(), "no creo la raiz que faltaba"


def test_y_seguir_rechazando_el_enlace_cuando_la_raiz_SI_existe(tmp_casos_root, tmp_path):
    """El hermano imprescindible: arreglar H-01 no puede desactivar la contencion fisica."""
    from core.casos import case_locator

    cm = _cm()
    raiz = case_locator._root()
    fuera = tmp_path / "FUERA_R2"
    fuera.mkdir()
    enlace = raiz / "EnlaceR2"
    rc = subprocess.run(["cmd", "/c", "mklink", "/J", str(enlace), str(fuera)],
                        capture_output=True, text=True)
    if rc.returncode != 0:
        pytest.skip(f"no se pudo crear la junction: {rc.stderr.strip()}")

    with pytest.raises(ValueError):
        cm.ensure_case("EnlaceR2")

    assert list(fuera.iterdir()) == [], "escribio fuera de la raiz"


# ---------------------------------------------------------------------------
# H-02 (MEDIO) — `_bajo` rechaza a los hijos de una raiz anclada
# ---------------------------------------------------------------------------

def test_la_contencion_acepta_los_hijos_de_una_raiz_anclada():
    """`case_mutex._bajo` hace `startswith(r + os.sep)`, asi que con la raiz terminando ya en
    separador (`C:\\` o un recurso UNC) pedia dos separadores seguidos y rechazaba a TODOS sus
    descendientes. `_contenido_en` usa `commonpath` y no tiene ese caso especial.
    """
    from pathlib import Path

    from core.case_manager import _contenido_en

    assert _contenido_en(Path("C:/CASOS/EV-2026-001"), Path("C:/")) is True
    assert _contenido_en(Path("//server/share/CASOS/EV"), Path("//server/share/")) is True
    # Y lo que SI tiene que rechazar, para que el arreglo no se vuelva permisivo:
    assert _contenido_en(Path("D:/CASOS/EV"), Path("C:/CASOS")) is False
    assert _contenido_en(Path("C:/CASOS_x/EV"), Path("C:/CASOS")) is False


# ---------------------------------------------------------------------------
# H-03 (MEDIO) — un nombre con espacio final dejaba andamiaje parcial
# ---------------------------------------------------------------------------

def test_un_case_id_con_espacio_final_ABORTA_sin_dejar_nada(tmp_casos_root):
    """Windows recorta los espacios al crear, asi que `'foo '` creaba `foo` y reventaba al
    crear `foo /00_Input`: el nombre pedido y el creado eran distintos y nadie los comparaba.
    """
    from core.casos import case_locator

    cm = _cm()
    raiz = case_locator._root()
    antes = sorted(p.name for p in raiz.iterdir())

    with pytest.raises(ValueError):
        cm.ensure_case("EV-2026-001 ")

    assert sorted(p.name for p in raiz.iterdir()) == antes, "dejo andamiaje parcial"


def test_un_case_id_con_caracteres_de_control_ABORTA(tmp_casos_root):
    cm = _cm()
    with pytest.raises(ValueError):
        cm.ensure_case("EV-2026\x01-001")


def test_los_case_id_reales_siguen_pasando_tras_las_reglas_nuevas(tmp_casos_root):
    """Medido el 2026-09-05: ninguno de los 27 casos reales lleva espacios al borde ni
    controles. Si esto se pone rojo, las reglas nuevas se han vuelto mas anchas que el
    defecto."""
    cm = _cm()
    for case_id in ("BaRS10 - Passeig Marítim, 30 - Castelldefels (08860) (W-02Z2NR) - Vuelta",
                    "BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU",
                    "BaRS8 - Santes Creus 15 - Montcada i Reixac (W-02XOR7) - Negativa oferta"):
        assert cm.ensure_case(case_id).is_dir()
