"""Tests del catálogo de ciudades — :mod:`core.ciudades`.

Cubre Fase 0 del plan ``docs/superpowers/plans/PLAN_SUBDIVISION_CIUDADES.md``:

- Catálogo canónico inmutable.
- Mappings tag azul por contexto (extrajudicial / judicial).
- Mappings equipos por ciudad por contexto (anidado y plano).
- ``ciudad_de_equipo`` — derivación código → ciudad (única fuente de
  verdad), incluyendo códigos asimétricos extra-only / judicial-only.
- ``es_carpeta_de_sistema`` — regla del guion bajo.
- Coherencia cross-context.
"""
from __future__ import annotations

import pytest

from core.ciudades import (
    CIUDADES,
    TAG_AZUL_CIUDAD_EXTRAJUDICIAL,
    TAG_AZUL_CIUDAD_JUDICIAL,
    EQUIPOS_POR_CIUDAD_EXTRAJUDICIAL,
    EQUIPOS_POR_CIUDAD_JUDICIAL,
    EQUIPOS_EXTRAJUDICIAL,
    EQUIPOS_JUDICIAL,
    ciudad_de_equipo,
    es_carpeta_de_sistema,
)


# ---------------------------------------------------------------------------
# Catálogo canónico
# ---------------------------------------------------------------------------

CIUDADES_CANONICAS = (
    "Barcelona",
    "Bilbao",
    "Madrid",
    "San Sebastián",
    "Santander",
    "Sevilla",
    "Valencia",
)


def test_catalogo_canonico_exacto_y_ordenado() -> None:
    """``CIUDADES`` debe contener exactamente las 7 ciudades canónicas en
    el orden alfabético español (San Sebastián entre Madrid y Santander)."""
    assert CIUDADES == CIUDADES_CANONICAS


def test_catalogo_es_tupla_inmutable() -> None:
    """``CIUDADES`` se expone como tupla para que no se mute en runtime."""
    assert isinstance(CIUDADES, tuple)


def test_ortografia_san_sebastian_con_tilde() -> None:
    """Ortografía oficial: 'San Sebastián' con tilde (no 'San Sebastian').
    Sirve para defender la decisión #3 del plan."""
    assert "San Sebastián" in CIUDADES
    assert "San Sebastian" not in CIUDADES


# ---------------------------------------------------------------------------
# Tag azul ciudad CRM — por contexto
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "mapping",
    [TAG_AZUL_CIUDAD_EXTRAJUDICIAL, TAG_AZUL_CIUDAD_JUDICIAL],
    ids=["extrajudicial", "judicial"],
)
def test_tag_azul_cubre_las_7_ciudades(mapping: dict[str, str]) -> None:
    """Las 7 ciudades canónicas son claves del mapping en ambos contextos
    y todos los valores son strings no vacíos (tag CRM)."""
    assert set(mapping.keys()) == set(CIUDADES_CANONICAS)
    for ciudad, tag in mapping.items():
        assert isinstance(tag, str) and tag, f"Tag vacío para {ciudad!r}"


# ---------------------------------------------------------------------------
# Equipos por ciudad — por contexto
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "anidado",
    [EQUIPOS_POR_CIUDAD_EXTRAJUDICIAL, EQUIPOS_POR_CIUDAD_JUDICIAL],
    ids=["extrajudicial", "judicial"],
)
def test_equipos_por_ciudad_cubre_las_7_ciudades(
    anidado: dict[str, dict[str, str]],
) -> None:
    """Cada contexto define equipos para las 7 ciudades canónicas (al menos
    un equipo por ciudad)."""
    assert set(anidado.keys()) == set(CIUDADES_CANONICAS)
    for ciudad, equipos in anidado.items():
        assert equipos, f"Ciudad {ciudad!r} sin equipos en el catálogo"


def test_equipos_planos_derivan_de_los_anidados_extrajudicial() -> None:
    esperado = {
        label: tag
        for equipos in EQUIPOS_POR_CIUDAD_EXTRAJUDICIAL.values()
        for label, tag in equipos.items()
    }
    assert EQUIPOS_EXTRAJUDICIAL == esperado


def test_equipos_planos_derivan_de_los_anidados_judicial() -> None:
    esperado = {
        label: tag
        for equipos in EQUIPOS_POR_CIUDAD_JUDICIAL.values()
        for label, tag in equipos.items()
    }
    assert EQUIPOS_JUDICIAL == esperado


# ---------------------------------------------------------------------------
# ciudad_de_equipo — códigos vivos hoy
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("codigo", "ciudad"),
    [
        # Los 6 expedientes vivos en CASOS_ROOT al 2026-05-12.
        ("BaRR3",  "Barcelona"),
        ("MaRS2",  "Madrid"),
        ("MaRS15", "Madrid"),
        ("MaRR2",  "Madrid"),
        ("SeRS6",  "Sevilla"),
        ("SaRS1",  "Santander"),
    ],
)
def test_ciudad_de_equipo_codigos_vivos(codigo: str, ciudad: str) -> None:
    assert ciudad_de_equipo(codigo) == ciudad


# ---------------------------------------------------------------------------
# ciudad_de_equipo — muestreo del resto de ciudades
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("codigo", "ciudad"),
    [
        # Una muestra por ciudad que no tiene caso vivo.
        ("BiRS1", "Bilbao"),
        ("SSRR1", "San Sebastián"),
        ("VaCR1", "Valencia"),
    ],
)
def test_ciudad_de_equipo_muestreo_resto(codigo: str, ciudad: str) -> None:
    assert ciudad_de_equipo(codigo) == ciudad


# ---------------------------------------------------------------------------
# ciudad_de_equipo — códigos asimétricos
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("codigo", "ciudad"),
    [
        # Sólo extrajudicial (no aparecen en _J_EQUIPOS_POR_CIUDAD).
        ("BaCR2",  "Barcelona"),
        ("BaCS10", "Barcelona"),
        # Sólo judicial (no aparecen en _EQUIPOS_POR_CIUDAD).
        ("BaCS2",  "Barcelona"),
        ("VaCS1",  "Valencia"),
    ],
)
def test_ciudad_de_equipo_codigos_asimetricos(codigo: str, ciudad: str) -> None:
    """La unión cross-context (extra ∪ judicial) no pierde códigos que
    sólo existen en uno de los dos contextos."""
    assert ciudad_de_equipo(codigo) == ciudad


# ---------------------------------------------------------------------------
# ciudad_de_equipo — entradas inválidas / inexistentes
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("codigo", ["", "XXXX", "no_existe", "BaRR999"])
def test_ciudad_de_equipo_entrada_invalida_devuelve_none(codigo: str) -> None:
    """Política permisiva: códigos vacíos o inexistentes devuelven ``None``,
    no levantan."""
    assert ciudad_de_equipo(codigo) is None


# ---------------------------------------------------------------------------
# Coherencia cross-context
# ---------------------------------------------------------------------------

def _codigo_corto(label: str) -> str:
    """Reproduce la extracción que hace `core.ciudades._extraer_codigo`."""
    return label.split(" ", 1)[0].strip()


def test_coherencia_cross_context_mismo_codigo_misma_ciudad() -> None:
    """Cada código que aparece en ambos contextos (extra y judicial) debe
    mapear a la misma ciudad. Esta propiedad es la que permite tener una
    única función ``ciudad_de_equipo``."""
    extra_index: dict[str, str] = {
        _codigo_corto(label): ciudad
        for ciudad, equipos in EQUIPOS_POR_CIUDAD_EXTRAJUDICIAL.items()
        for label in equipos
    }
    jud_index: dict[str, str] = {
        _codigo_corto(label): ciudad
        for ciudad, equipos in EQUIPOS_POR_CIUDAD_JUDICIAL.items()
        for label in equipos
    }
    comunes = set(extra_index) & set(jud_index)
    assert comunes, "Debería haber códigos comunes a ambos contextos"
    for codigo in comunes:
        assert extra_index[codigo] == jud_index[codigo], (
            f"Código {codigo!r} mapea a {extra_index[codigo]!r} en extra y "
            f"a {jud_index[codigo]!r} en judicial."
        )


# ---------------------------------------------------------------------------
# es_carpeta_de_sistema — regla del guion bajo
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "nombre",
    ["_PLANTILLA", "_audit", "_Sin clasificar", "_", "__init__"],
)
def test_es_carpeta_de_sistema_true(nombre: str) -> None:
    assert es_carpeta_de_sistema(nombre) is True


@pytest.mark.parametrize(
    "nombre",
    [
        "Barcelona",
        "BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU",
        "",  # cadena vacía no es carpeta de sistema (ni siquiera es carpeta)
    ],
)
def test_es_carpeta_de_sistema_false(nombre: str) -> None:
    assert es_carpeta_de_sistema(nombre) is False
