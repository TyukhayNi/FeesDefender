"""`ensure_case` valida en el sumidero: contenido, localizable y sin carpeta parcial.

Cierra `MEJORAS #153` (la UI compone el `case_id` y una direccion con `s/n` parte la carpeta)
y `MEJORAS #154` (el override del formulario escapa de `CASOS_ROOT`), poniendo la guarda en el
sumidero del alta en vez de en cada compositor.

Diseno y adjudicacion de la R1 adversarial:
`docs/superpowers/specs/2026-09-05-validar-en-el-sumidero-design.md` (rev. 2).

Los nueve mutantes del §6 de ese diseno. Los tres ultimos son POSITIVOS: sin ellos, endurecer
la guarda de mas pasaria inadvertido, que es lo que costo cinco fixtures el 2026-09-04.
"""
from __future__ import annotations

import importlib
import subprocess

import pytest


def _cm():
    from core import case_manager
    importlib.reload(case_manager)
    return case_manager


def _hijos(p):
    return sorted(x.name for x in p.iterdir()) if p.is_dir() else []


# ---------------------------------------------------------------------------
# (a) El case_id es un componente de ruta valido
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("case_id", [
    "BaRS8 - Castell De Rosanes s/n 08530 La Garriga (W-02JSVZ) - BD",   # el caso medido
    r"..\..\escape",
    "..",
    ".",
    "sub/dir",
])
def test_un_case_id_que_no_es_un_componente_ABORTA(tmp_casos_root, case_id):
    cm = _cm()
    with pytest.raises(ValueError):
        cm.ensure_case(case_id)


def test_el_case_id_vacio_no_convierte_la_raiz_en_un_expediente(tmp_casos_root):
    """H-02 de la R1: `buscar('')` devuelve la propia raiz y `is_relative_to` incluye la
    igualdad, asi que las dos mitades de la rev. 1 lo aceptaban y creaban las nueve
    subcarpetas y el `_caso.md` EN LA RAIZ.

    Causa: al extraer `exigir_sin_caracteres_de_ruta` de `validate_case_id` se dejo atras
    su comprobacion de vacio. Una extraccion parcial que perdio una propiedad.
    """
    from core.casos import case_locator

    cm = _cm()
    raiz = case_locator._root()
    antes = _hijos(raiz)

    with pytest.raises(ValueError):
        cm.ensure_case("")

    assert _hijos(raiz) == antes, "el alta vacia toco la raiz"
    assert not (raiz / "00_Input").exists(), "convirtio CASOS_ROOT en un expediente"
    assert not (raiz / "00_Input" / "_caso.md").exists()


def test_el_aborto_no_deja_carpeta_parcial(tmp_casos_root):
    """Lo caro del defecto original no fue el error: fue que dejo 170 ficheros en una ruta
    sombra. La guarda tiene que morder ANTES del `mkdir`."""
    from core.casos import case_locator

    cm = _cm()
    raiz = case_locator._root()
    antes = _hijos(raiz)

    with pytest.raises(ValueError):
        cm.ensure_case("BaRS8 - Calle s/n (W-000AAA) - BD")

    assert _hijos(raiz) == antes, f"quedo andamiaje: {set(_hijos(raiz)) - set(antes)}"


# ---------------------------------------------------------------------------
# (b) La ciudad tiene que ser LOCALIZABLE, no solo un componente
# ---------------------------------------------------------------------------

def test_una_ciudad_con_subruta_ABORTA(tmp_casos_root):
    """H-03: pasa la gramatica del ID, cae DENTRO de la raiz, y crea un caso que
    `buscar` no encuentra — y un segundo alta genera un duplicado."""
    cm = _cm()
    with pytest.raises(ValueError):
        cm.ensure_case("EV-2026-001", ciudad="Barcelona/subcarpeta")


def test_una_ciudad_desconocida_de_un_componente_ABORTA(tmp_casos_root):
    """Contencion y localizacion son propiedades distintas: esta ciudad esta contenida
    y aun asi el caso resultante seria invisible para `buscar`."""
    cm = _cm()
    with pytest.raises(ValueError):
        cm.ensure_case("EV-2026-001", ciudad="Kuala Lumpur")


def test_todo_alta_con_exito_es_LOCALIZABLE(tmp_casos_root):
    """La propiedad que las dos de arriba protegen, afirmada en positivo."""
    from core.casos import case_locator

    cm = _cm()
    cm.ensure_case("EV-2026-001", ciudad="Barcelona")

    assert case_locator.buscar("EV-2026-001") is not None, (
        "el alta creo un caso que el localizador no encuentra")


# ---------------------------------------------------------------------------
# (c) Contencion: el destino cae bajo la raiz
# ---------------------------------------------------------------------------

def test_un_destino_fuera_de_la_raiz_ABORTA_y_no_escribe_fuera(tmp_casos_root, tmp_path):
    """El mutante que la rev. 1 NO tenia (H-05) y que Codex exigio para la ronda 2: un
    `case_id` que pasa la gramatica y cuyo destino sale de la raiz por una junction.

    Muere si se quita la mitad (c), y SOLO si se quita (c): la gramatica lo acepta.
    """
    from core.casos import case_locator

    cm = _cm()
    raiz = case_locator._root()
    fuera = tmp_path / "FUERA"
    fuera.mkdir()

    # Junction en el PROPIO caso: `raiz/Enlace` -> `fuera`.
    enlace = raiz / "Enlace"
    rc = subprocess.run(["cmd", "/c", "mklink", "/J", str(enlace), str(fuera)],
                        capture_output=True, text=True)
    if rc.returncode != 0:
        pytest.skip(f"no se pudo crear la junction: {rc.stderr.strip()}")

    with pytest.raises(ValueError):
        cm.ensure_case("Enlace")

    assert _hijos(fuera) == [], f"escribio fuera de la raiz: {_hijos(fuera)}"


# ---------------------------------------------------------------------------
# Los POSITIVOS: endurecer de mas tambien es un defecto
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("case_id", [
    "BaRS10 - Passeig Marítim, 30 - Castelldefels (08860) (W-02Z2NR) - Vuelta",
    "BaRR3 - Roger de Flor 204, pr. 1ª - (W-02THLJ) - LAU 20",
    "MaRS2 - Puerto Rico 2, 5º 2 (W-0470GM) - Negativa arras",
    "EV-2026-001",
])
def test_los_case_id_reales_del_catalogo_SIGUEN_pasando(tmp_casos_root, case_id):
    """Medido el 2026-09-05: los 27 casos reales son un solo componente sin caracter
    prohibido. Si este test se pone rojo, la guarda se ha vuelto mas ancha que el defecto
    — que es exactamente lo que paso el 2026-09-04 y rompio cinco fixtures."""
    cm = _cm()
    case_dir = cm.ensure_case(case_id)
    assert case_dir.is_dir()
    assert (case_dir / "00_Input").is_dir()


def test_la_ciudad_de_fallback_sigue_pasando(tmp_casos_root):
    """`_Sin clasificar` esta en `_CITY_NAMES` y lo usa la migracion: no puede romperse."""
    cm = _cm()
    case_dir = cm.ensure_case("EV-2026-002", ciudad="_Sin clasificar")
    assert case_dir.is_dir()


def test_un_caso_que_ya_existe_bajo_su_ciudad_sigue_pasando(tmp_casos_root):
    """La contencion se cumple dos niveles por debajo de la raiz, no solo uno."""
    cm = _cm()
    primero = cm.ensure_case("EV-2026-003", ciudad="Sevilla")
    segundo = cm.ensure_case("EV-2026-003")
    assert primero == segundo, "el segundo alta fabrico una carpeta sombra"
