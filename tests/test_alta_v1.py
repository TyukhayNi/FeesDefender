"""El alta en modo `v1` — Plan 3A, Task 3 (`3A-alta`). Fronteras A1-A6.

Las filas #1, #2 y #3 del write-set del §25 son las **tres de clase estructura**, y no pueden
pasar por la costura como el resto: `ensure_case` crea la raíz **antes** de que exista un caso
que `CaseCatalog` pueda resolver ni un `_caso.md` que el guard pueda leer. Necesitan la puerta
propia que R14/H14-07 echaba en falta.

**Por qué un `modo` y no una función nueva:** el docstring de `ensure_case` la declara «la
ÚNICA puerta de alta del sistema». Añadir una segunda puerta para el alta de V1 sería crear
exactamente lo que esa frase existe para impedir.

**Y por qué el alta exige `id_go` explícito:** en el alta no hay `_caso.md` todavía, así que el
kwarg **es** la identidad canónica. Derivarla del nombre de la carpeta sería el CRÍTICO de R14
cometido en el único sitio donde todavía no hay metadato que lo desmienta.
"""
from __future__ import annotations

import pytest

AHORA = "2026-08-26T12:00:00Z"
W = "W-ALTA01"
CASE_ID = f"Ba001 - Calle Falsa 1 - ({W}) - honorarios"

#: Los seis de `CASO_SUBDIRS` que el §25 fila #1 deja fuera de V1: ninguno tiene productor
#: dentro de la primera vertical.
FUERA_DE_V1 = ("02_Analisis", "03_Decision", "04_Output predemanda",
               "05_Procedimiento", "06_Anonimizado", "07_AI cowork")

#: Lo que sí. `90_Notas personales` sigue eager y es **exención declarada**: ningún camino de
#: V1 lee ni escribe su contenido, y `core/config.py` ya lo documenta como deliberado.
MINIMO_V1 = ("00_Input", "01_Procesado", "90_Notas personales")


def reloj() -> str:
    return AHORA


@pytest.fixture
def raiz(tmp_path):
    return tmp_path / "locks"


@pytest.fixture(autouse=True)
def _reloj_del_sistema_fijo(monkeypatch):
    from core.casos import case_mutex
    monkeypatch.setattr(case_mutex, "_ahora_del_sistema",
                        lambda: case_mutex._instante(AHORA))


@pytest.fixture(autouse=True)
def _mapa_limpio():
    from core.casos import mutex_sesion
    with mutex_sesion._CANDADO:
        mutex_sesion._SESIONES.clear()
    yield
    with mutex_sesion._CANDADO:
        mutex_sesion._SESIONES.clear()


def ref_de(w=W):
    from core.casos.workspace_model import CaseRef
    return CaseRef(w_code=w)


# --------------------------------------------------------------------------- A1

def test_a1_v1_sin_id_go_aborta_aunque_el_nombre_lleve_el_w_code(tmp_casos_root, raiz):
    """A1 — el nombre de la carpeta NO es identidad, tampoco en el alta.

    `CASE_ID` lleva `(W-ALTA01)` dentro, así que una implementación que lo extrajera pasaría
    este test sin darse cuenta de que acaba de reintroducir H14-01 en el único punto donde
    no hay `meta.id_go` que la desmienta.
    """
    from core import case_manager
    from core.casos.workspace_model import IdentidadNoUtilizable

    with pytest.raises(IdentidadNoUtilizable):
        case_manager.ensure_case(CASE_ID, modo="v1", raiz_mutex=raiz)

    assert not (tmp_casos_root / CASE_ID).exists(), (
        "el alta abortó pero dejó la carpeta: un alta que falla no puede dejar rastro, "
        "que es el defecto que R6 encontró en `--force`")


# --------------------------------------------------------------------------- A2

def test_a2_v1_sin_mutex_sostenido_rechaza(tmp_casos_root, raiz):
    """A2 — `core/` exige, los entrypoints adquieren.

    El alta escribe la raíz y el `_caso.md` (filas #1 y #4). Sin mutex, dos procesos podrían
    darla de alta a la vez.
    """
    from core import case_manager
    from core.casos.workspace_model import EscrituraSinMutex

    with pytest.raises(EscrituraSinMutex):
        case_manager.ensure_case(CASE_ID, modo="v1", id_go=W, raiz_mutex=raiz)

    assert not (tmp_casos_root / CASE_ID).exists(), "un alta rechazada no deja carpeta"


# --------------------------------------------------------------------------- A3

def test_a3_v1_crea_solo_el_minimo(tmp_casos_root, raiz):
    """A3 — fila #1: `00_Input`, `01_Procesado`, `90_Notas personales` y la base `05_CRM`."""
    from core import case_manager
    from core.casos import mutex_sesion

    with mutex_sesion.sostenido(ref_de(), ahora_fn=reloj, raiz=raiz):
        case_dir = case_manager.ensure_case(CASE_ID, modo="v1", id_go=W, raiz_mutex=raiz)

    for sub in MINIMO_V1:
        assert (case_dir / sub).is_dir(), f"falta {sub}, que V1 sí necesita"
    assert (case_dir / "00_Input" / "05_CRM").is_dir(), "la base 05_CRM sigue eager (D7)"

    sobrantes = [s for s in FUERA_DE_V1 if (case_dir / s).exists()]
    assert not sobrantes, (
        f"V1 creó carpetas sin productor en la primera vertical: {sobrantes}. El §25 fila "
        f"#1 las deja fuera precisamente porque nadie escribe en ellas todavía")


# --------------------------------------------------------------------------- A4

def test_a4_v1_no_crea_la_subestructura_de_01_procesado(tmp_casos_root, raiz):
    """A4 — fila #2: sus productores son módulos DEPRECADOS.

    Medido en el §25: `Sala lectura` la produce `core/sala_lectura.py` (deprecado) y `MD`
    `core/markdown_generator.py` (pipeline legacy). Crear carpetas cuyo productor no existe
    es andamiaje que luego nadie retira.
    """
    from core import case_manager
    from core.casos import mutex_sesion

    with mutex_sesion.sostenido(ref_de(), ahora_fn=reloj, raiz=raiz):
        case_dir = case_manager.ensure_case(CASE_ID, modo="v1", id_go=W, raiz_mutex=raiz)

    for sub01 in ("Sala lectura", "MD", "_revisar"):
        assert not (case_dir / "01_Procesado" / sub01).exists(), (
            f"01_Procesado/{sub01} no tiene productor en V1")


# --------------------------------------------------------------------------- A5

def test_a5_v1_no_copia_las_plantillas_de_viabilidad(tmp_casos_root, raiz):
    """A5 — fila #3: la viabilidad es vertical diferida (V3)."""
    from core import case_manager
    from core.casos import mutex_sesion

    with mutex_sesion.sostenido(ref_de(), ahora_fn=reloj, raiz=raiz):
        case_dir = case_manager.ensure_case(
            CASE_ID, modo="v1", id_go=W, tipo_caso="honorarios_impagados", raiz_mutex=raiz)

    xlsx = list(case_dir.rglob("*.xlsx"))
    assert not xlsx, f"V1 copió plantillas de una vertical diferida: {xlsx}"


# --------------------------------------------------------------------------- A6

def test_a6_libre_no_se_regresa(tmp_casos_root):
    """A6 — el control de no regresión, y es el que protege al equipo.

    ~30 tests recargan `case_manager` y el alta en `libre` es la que usan Paola y Ana desde
    la UI. Si V1 le cambiara el comportamiento por defecto, el andamiaje de los casos reales
    dejaría de crearse sin que nadie lo hubiera pedido.
    """
    from core import case_manager
    from core.config import CASO_SUBDIRS

    case_dir = case_manager.ensure_case(CASE_ID, id_go=W)

    for sub in CASO_SUBDIRS:
        assert (case_dir / sub).is_dir(), f"`libre` dejó de crear {sub}"
    for sub01 in ("Sala lectura", "MD", "_revisar"):
        assert (case_dir / "01_Procesado" / sub01).is_dir(), (
            f"`libre` dejó de crear 01_Procesado/{sub01}")


def test_a6b_libre_no_exige_mutex_ni_id_go(tmp_casos_root):
    """A6-bis — la otra mitad de la no regresión: `libre` no adquiere obligaciones nuevas.

    Si el alta en `libre` empezara a exigir mutex, cualquier vía sin cablear —incluida la UI—
    pasaría de funcionar a abortar. Es el mismo trinquete que la frontera C1.
    """
    from core import case_manager

    case_dir = case_manager.ensure_case(CASE_ID)          # sin id_go, sin mutex, sin modo
    assert case_dir.is_dir()


# --------------------------------------------------------------------- A7 (R15)

def test_a7_v1_rechaza_un_id_go_que_discrepa_del_persistido(tmp_casos_root, raiz):
    """A7 — R15/H15-01, CRÍTICO: tener un mutex no es tener EL mutex del expediente.

    Medido antes del arreglo: con `meta.id_go = W-OLD01` persistido, el alta aceptaba
    `id_go=W-NEW01`, **reescribía el metadato** y devolvía el mismo directorio. Un proceso
    con el lock nuevo y otro con el viejo operaban la misma carpeta, los dos creyéndose
    protegidos — la falsa exclusión que la pieza entera existe para impedir.

    **Es la tercera aparición de la misma propiedad.** R14 la cerró en la costura (C0) y yo
    remedié *ese sitio* en vez de la propiedad: «todo camino que fije identidad comprueba
    concordancia». El alta es un camino que fija identidad.
    """
    from core import case_manager
    from core.casos import case_locator, mutex_sesion
    from core.casos.workspace_model import CaseRef, IdentidadDiscordante

    viejo = "Ba001 - Calle X - (W-OLD01) - honorarios"
    d = tmp_casos_root / viejo
    (d / "00_Input").mkdir(parents=True)
    import io as _io
    _io.open(d / "00_Input" / "_caso.md", "w", encoding="utf-8", newline="\n").write(
        "---\nmeta:\n  id_go: W-OLD01\n  estado_repositorio: disponible\n---\n")

    with mutex_sesion.sostenido(CaseRef(w_code="W-NEW01"), ahora_fn=reloj, raiz=raiz):
        with pytest.raises(IdentidadDiscordante):
            case_manager.ensure_case(viejo, modo="v1", id_go="W-NEW01", raiz_mutex=raiz)

    assert case_locator.read_case_meta(d).get("id_go") == "W-OLD01", (
        "el alta reescribió la identidad canónica del caso: en v1 `meta.id_go` no es un "
        "campo que el alta actualice")


def test_a7b_v1_rechaza_si_el_nombre_lleva_otro_w_code(tmp_casos_root, raiz):
    """A7-bis — la otra mitad: caso NUEVO cuyo nombre declara un W-code distinto.

    Sin esto se podría crear de cero una carpeta `(W-AAA01)` con `id_go=W-BBB01` dentro,
    o sea fabricar la discordancia que A7 detecta después.
    """
    from core import case_manager
    from core.casos import mutex_sesion
    from core.casos.workspace_model import CaseRef, IdentidadDiscordante

    nombre = "Ba001 - Calle Y - (W-AAA01) - honorarios"
    with mutex_sesion.sostenido(CaseRef(w_code="W-BBB01"), ahora_fn=reloj, raiz=raiz):
        with pytest.raises(IdentidadDiscordante):
            case_manager.ensure_case(nombre, modo="v1", id_go="W-BBB01", raiz_mutex=raiz)
    assert not (tmp_casos_root / nombre).exists(), "un alta rechazada no deja carpeta"


def test_a7c_v1_acepta_cuando_las_tres_concuerdan(tmp_casos_root, raiz):
    """A7-ter — control negativo, o A7 pasaría con un alta que rechaza todo."""
    from core import case_manager
    from core.casos import mutex_sesion
    from core.casos.workspace_model import CaseRef

    with mutex_sesion.sostenido(CaseRef(w_code=W), ahora_fn=reloj, raiz=raiz):
        case_dir = case_manager.ensure_case(CASE_ID, modo="v1", id_go=W, raiz_mutex=raiz)
    assert (case_dir / "00_Input").is_dir()
