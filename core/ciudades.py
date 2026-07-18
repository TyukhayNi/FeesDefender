"""Catálogo único de ciudades, equipos y reglas de carpeta de sistema.

Única fuente de verdad para:

- Las 7 ciudades canónicas (ortografía con tilde).
- Los equipos por ciudad, en sus dos contextos CRM (extrajudicial / judicial).
- La derivación código_equipo → ciudad (vía :func:`ciudad_de_equipo`).
- La convención "una carpeta cuyo nombre empieza por ``_`` es de sistema"
  (vía :func:`es_carpeta_de_sistema`).

Sin idioma de UI: el placeholder de los ``st.selectbox`` lo antepone quien
consume las constantes.

Plan: ``docs/superpowers/plans/PLAN_SUBDIVISION_CIUDADES.md`` (Fase 0, sesión 16, 2026-05-12).
"""
from __future__ import annotations

from core import sudespacho_create as _sc


# ---------------------------------------------------------------------------
# Catálogo canónico de ciudades
# ---------------------------------------------------------------------------

CIUDADES: tuple[str, ...] = (
    "Barcelona",
    "Bilbao",
    "Madrid",
    "San Sebastián",
    "Santander",
    "Sevilla",
    "Valencia",
)
"""Catálogo canónico inmutable. Ortografía oficial (San Sebastián con tilde)."""


# ---------------------------------------------------------------------------
# Tag azul CRM por ciudad — por contexto (extrajudicial / judicial)
# ---------------------------------------------------------------------------

TAG_AZUL_CIUDAD_EXTRAJUDICIAL: dict[str, str] = {
    "Barcelona":     _sc.TAG_AZUL_BARCELONA,
    "Bilbao":        _sc.TAG_AZUL_BILBAO,
    "Madrid":        _sc.TAG_AZUL_MADRID,
    "San Sebastián": _sc.TAG_AZUL_SAN_SEBASTIAN,
    "Santander":     _sc.TAG_AZUL_SANTANDER,
    "Sevilla":       _sc.TAG_AZUL_SEVILLA,
    "Valencia":      _sc.TAG_AZUL_VALENCIA,
}

TAG_AZUL_CIUDAD_JUDICIAL: dict[str, str] = {
    "Barcelona":     _sc.J_TAG_AZUL_CIUDAD_BARCELONA,
    "Bilbao":        _sc.J_TAG_AZUL_CIUDAD_BILBAO,
    "Madrid":        _sc.J_TAG_AZUL_CIUDAD_MADRID,
    "San Sebastián": _sc.J_TAG_AZUL_CIUDAD_SAN_SEBASTIAN,
    "Santander":     _sc.J_TAG_AZUL_CIUDAD_SANTANDER,
    "Sevilla":       _sc.J_TAG_AZUL_CIUDAD_SEVILLA,
    "Valencia":      _sc.J_TAG_AZUL_CIUDAD_VALENCIA,
}


# ---------------------------------------------------------------------------
# Equipos por ciudad — contexto extrajudicial
# ---------------------------------------------------------------------------

EQUIPOS_POR_CIUDAD_EXTRAJUDICIAL: dict[str, dict[str, str]] = {
    "Barcelona": {
        "BaRR1  — BCN Residential Rentals 1":  _sc.TAG_ROJO_BaRR1,
        "BaRR2  — BCN Residential Rentals 2":  _sc.TAG_ROJO_BaRR2,
        "BaRR3  — BCN Residential Rentals 3":  _sc.TAG_ROJO_BaRR3,
        "BaRR4  — BCN Residential Rentals 4":  _sc.TAG_ROJO_BaRR4,
        "BaRR10 — BCN Residential Rentals 10": _sc.TAG_ROJO_BaRR10,
        "BaRS1  — BCN Residential Sales 1":    _sc.TAG_ROJO_BaRS1,
        "BaRS2  — BCN Residential Sales 2":    _sc.TAG_ROJO_BaRS2,
        "BaRS3  — BCN Residential Sales 3":    _sc.TAG_ROJO_BaRS3,
        "BaRS4  — BCN Residential Sales 4":    _sc.TAG_ROJO_BaRS4,
        "BaRS5  — BCN Residential Sales 5":    _sc.TAG_ROJO_BaRS5,
        "BaRS6  — BCN Residential Sales 6":    _sc.TAG_ROJO_BaRS6,
        "BaRS7  — BCN Residential Sales 7":    _sc.TAG_ROJO_BaRS7,
        "BaRS8  — BCN Residential Sales 8":    _sc.TAG_ROJO_BaRS8,
        "BaRS9  — BCN Residential Sales 9":    _sc.TAG_ROJO_BaRS9,
        "BaRS10 — BCN Residential Sales 10":   _sc.TAG_ROJO_BaRS10,
        "BaRS11 — BCN Residential Sales 11":   _sc.TAG_ROJO_BaRS11,
        "BaRS12 — BCN Residential Sales 12":   _sc.TAG_ROJO_BaRS12,
        "BaCR1  — BCN Commercial Rentals 1":   _sc.TAG_ROJO_BaCR1,
        "BaCR2  — BCN Commercial Rentals 2":   _sc.TAG_ROJO_BaCR2,
        "BaCR10 — BCN Commercial Rentals 10":  _sc.TAG_ROJO_BaCR10,
        "BaCS1  — BCN Commercial Sales 1":     _sc.TAG_ROJO_BaCS1,
        "BaCS10 — BCN Commercial Sales 10":    _sc.TAG_ROJO_BaCS10,
        "BaPD1  — BCN (Pendiente) 1":          _sc.TAG_ROJO_BaPD1,
    },
    "Bilbao": {
        "BiRS1  — Bilbao Residential Sales 1": _sc.TAG_ROJO_BiRS1,
        "BiRS2  — Bilbao Residential Sales 2": _sc.TAG_ROJO_BiRS2,
    },
    "Madrid": {
        "MaRR1  — MAD Residential Rentals 1":  _sc.TAG_ROJO_MaRR1,
        "MaRR2  — MAD Residential Rentals 2":  _sc.TAG_ROJO_MaRR2,
        "MaRR3  — MAD Residential Rentals 3":  _sc.TAG_ROJO_MaRR3,
        "MaRS1  — MAD Residential Sales 1":    _sc.TAG_ROJO_MaRS1,
        "MaRS2  — MAD Residential Sales 2":    _sc.TAG_ROJO_MaRS2,
        "MaRS3  — MAD Residential Sales 3":    _sc.TAG_ROJO_MaRS3,
        "MaRS4  — MAD Residential Sales 4":    _sc.TAG_ROJO_MaRS4,
        "MaRS5  — MAD Residential Sales 5":    _sc.TAG_ROJO_MaRS5,
        "MaRS6  — MAD Residential Sales 6":    _sc.TAG_ROJO_MaRS6,
        "MaRS7  — MAD Residential Sales 7":    _sc.TAG_ROJO_MaRS7,
        "MaRS8  — MAD Residential Sales 8":    _sc.TAG_ROJO_MaRS8,
        "MaRS9  — MAD Residential Sales 9":    _sc.TAG_ROJO_MaRS9,
        "MaRS10 — MAD Residential Sales 10":   _sc.TAG_ROJO_MaRS10,
        "MaRS11 — MAD Residential Sales 11":   _sc.TAG_ROJO_MaRS11,
        "MaRS12 — MAD Residential Sales 12":   _sc.TAG_ROJO_MaRS12,
        "MaRS13 — MAD Residential Sales 13":   _sc.TAG_ROJO_MaRS13,
        "MaRS14 — MAD Residential Sales 14":   _sc.TAG_ROJO_MaRS14,
        "MaRS15 — MAD Residential Sales 15":   _sc.TAG_ROJO_MaRS15,
        "MaPD1  — MAD (Pendiente) 1":          _sc.TAG_ROJO_MaPD1,
    },
    "San Sebastián": {
        "SSRR1  — San Sebastián Residential Rentals 1": _sc.TAG_ROJO_SSRR1,
        "SSRS1  — San Sebastián Residential Sales 1":   _sc.TAG_ROJO_SSRS1,
    },
    "Santander": {
        "SaRS1  — Santander Residential Sales 1": _sc.TAG_ROJO_SaRS1,
    },
    "Sevilla": {
        "SeRS1  — Sevilla Residential Sales 1":  _sc.TAG_ROJO_SeRS1,
        "SeRS6  — Sevilla Residential Sales 6":  _sc.TAG_ROJO_SeRS6,
    },
    "Valencia": {
        "VaCR1  — Valencia Commercial Rentals 1":  _sc.TAG_ROJO_VaCR1,
        "VaCR2  — Valencia Commercial Rentals 2":  _sc.TAG_ROJO_VaCR2,
        "VaPD1  — Valencia (pendiente) 1":         _sc.TAG_ROJO_VaPD1,
        "VaRR1  — Valencia Residential Rentals 1": _sc.TAG_ROJO_VaRR1,
        "VaRR3  — Valencia Residential Rentals 3": _sc.TAG_ROJO_VaRR3,
        "VaRS1  — Valencia Residential Sales 1":   _sc.TAG_ROJO_VaRS1,
        "VaRS2  — Valencia Residential Sales 2":   _sc.TAG_ROJO_VaRS2,
        "VaRS3  — Valencia Residential Sales 3":   _sc.TAG_ROJO_VaRS3,
        "VaRS4  — Valencia Residential Sales 4":   _sc.TAG_ROJO_VaRS4,
        "VaRS5  — Valencia Residential Sales 5":   _sc.TAG_ROJO_VaRS5,
    },
}

EQUIPOS_EXTRAJUDICIAL: dict[str, str] = {
    k: v for equipos in EQUIPOS_POR_CIUDAD_EXTRAJUDICIAL.values() for k, v in equipos.items()
}
"""Plano: ``label_equipo → tag_rojo``. Derivado de :data:`EQUIPOS_POR_CIUDAD_EXTRAJUDICIAL`."""


# ---------------------------------------------------------------------------
# Equipos por ciudad — contexto judicial
# ---------------------------------------------------------------------------

EQUIPOS_POR_CIUDAD_JUDICIAL: dict[str, dict[str, str]] = {
    "Barcelona": {
        "BaRR1  — BCN Residential Rentals 1":  _sc.J_TAG_ROJO_BaRR1,
        "BaRR2  — BCN Residential Rentals 2":  _sc.J_TAG_ROJO_BaRR2,
        "BaRR3  — BCN Residential Rentals 3":  _sc.J_TAG_ROJO_BaRR3,
        "BaRR4  — BCN Residential Rentals 4":  _sc.J_TAG_ROJO_BaRR4,
        "BaRR10 — BCN Residential Rentals 10": _sc.J_TAG_AZUL_BaRR10,
        "BaRS1  — BCN Residential Sales 1":    _sc.J_TAG_ROJO_BaRS1,
        "BaRS2  — BCN Residential Sales 2":    _sc.J_TAG_ROJO_BaRS2,
        "BaRS3  — BCN Residential Sales 3":    _sc.J_TAG_ROJO_BaRS3,
        "BaRS4  — BCN Residential Sales 4":    _sc.J_TAG_AZUL_BaRS4,
        "BaRS5  — BCN Residential Sales 5":    _sc.J_TAG_ROJO_BaRS5,
        "BaRS6  — BCN Residential Sales 6":    _sc.J_TAG_ROJO_BaRS6,
        "BaRS7  — BCN Residential Sales 7":    _sc.J_TAG_ROJO_BaRS7,
        "BaRS8  — BCN Residential Sales 8":    _sc.J_TAG_ROJO_BaRS8,
        "BaRS9  — BCN Residential Sales 9":    _sc.J_TAG_ROJO_BaRS9,
        "BaRS10 — BCN Residential Sales 10":   _sc.J_TAG_ROJO_BaRS10,
        "BaRS11 — BCN Residential Sales 11":   _sc.J_TAG_ROJO_BaRS11,
        "BaRS12 — BCN Residential Sales 12":   _sc.J_TAG_ROJO_BaRS12,
        "BaCR1  — BCN Commercial Rentals 1":   _sc.J_TAG_ROJO_BaCR1,
        "BaCR10 — BCN Commercial Rentals 10":  _sc.J_TAG_ROJO_BaCR10,
        "BaCS1  — BCN Commercial Sales 1":     _sc.J_TAG_ROJO_BaCS1,
        "BaCS2  — BCN Commercial Sales 2":     _sc.J_TAG_AZUL_BaCS2,
        "BaPD1  — BCN (pendiente) 1":          _sc.J_TAG_ROJO_BaPD1,
    },
    "Bilbao": {
        "BiRS1  — Bilbao Residential Sales 1": _sc.J_TAG_ROJO_BiRS1,
        "BiRS2  — Bilbao Residential Sales 2": _sc.J_TAG_ROJO_BiRS2,
    },
    "Madrid": {
        "MaRR1  — MAD Residential Rentals 1":  _sc.J_TAG_ROJO_MaRR1,
        "MaRR2  — MAD Residential Rentals 2":  _sc.J_TAG_AZUL_MaRR2,
        "MaRR3  — MAD Residential Rentals 3":  _sc.J_TAG_ROJO_MaRR3,
        "MaRS1  — MAD Residential Sales 1":    _sc.J_TAG_ROJO_MaRS1,
        "MaRS2  — MAD Residential Sales 2":    _sc.J_TAG_ROJO_MaRS2,
        "MaRS3  — MAD Residential Sales 3":    _sc.J_TAG_ROJO_MaRS3,
        "MaRS4  — MAD Residential Sales 4":    _sc.J_TAG_ROJO_MaRS4,
        "MaRS5  — MAD Residential Sales 5":    _sc.J_TAG_ROJO_MaRS5,
        "MaRS6  — MAD Residential Sales 6":    _sc.J_TAG_ROJO_MaRS6,
        "MaRS7  — MAD Residential Sales 7":    _sc.J_TAG_ROJO_MaRS7,
        "MaRS8  — MAD Residential Sales 8":    _sc.J_TAG_ROJO_MaRS8,
        "MaRS9  — MAD Residential Sales 9":    _sc.J_TAG_ROJO_MaRS9,
        "MaRS10 — MAD Residential Sales 10":   _sc.J_TAG_ROJO_MaRS10,
        "MaRS11 — MAD Residential Sales 11":   _sc.J_TAG_ROJO_MaRS11,
        "MaRS12 — MAD Residential Sales 12":   _sc.J_TAG_ROJO_MaRS12,
        "MaRS13 — MAD Residential Sales 13":   _sc.J_TAG_ROJO_MaRS13,
        "MaRS14 — MAD Residential Sales 14":   _sc.J_TAG_ROJO_MaRS14,
        "MaRS15 — MAD Residential Sales 15":   _sc.J_TAG_ROJO_MaRS15,
        "MaPD1  — MAD (pendiente) 1":          _sc.J_TAG_ROJO_MaPD1,
    },
    "San Sebastián": {
        "SSRR1  — San Sebastián Residential Rentals 1": _sc.J_TAG_ROJO_SSRR1,
        "SSRS1  — San Sebastián Residential Sales 1":   _sc.J_TAG_ROJO_SSRS1,
    },
    "Santander": {
        "SaRS1  — Santander Residential Sales 1": _sc.J_TAG_ROJO_SaRS1,
    },
    "Sevilla": {
        "SeRS1  — Sevilla Residential Sales 1":  _sc.J_TAG_ROJO_SeRS1,
        "SeRS6  — Sevilla Residential Sales 6":  _sc.J_TAG_ROJO_SeRS6,
    },
    "Valencia": {
        "VaCR1  — Valencia Commercial Rentals 1":  _sc.J_TAG_ROJO_VaCR1,
        "VaCR2  — Valencia Commercial Rentals 2":  _sc.J_TAG_ROJO_VaCR2,
        "VaCS1  — Valencia Commercial Sales 1":    _sc.J_TAG_AZUL_VaCS1,
        "VaPD1  — Valencia (pendiente) 1":         _sc.J_TAG_ROJO_VaPD1,
        "VaRR1  — Valencia Residential Rentals 1": _sc.J_TAG_ROJO_VaRR1,
        "VaRR3  — Valencia Residential Rentals 3": _sc.J_TAG_ROJO_VaRR3,
        "VaRS1  — Valencia Residential Sales 1":   _sc.J_TAG_ROJO_VaRS1,
        "VaRS2  — Valencia Residential Sales 2":   _sc.J_TAG_ROJO_VaRS2,
        "VaRS3  — Valencia Residential Sales 3":   _sc.J_TAG_ROJO_VaRS3,
        "VaRS4  — Valencia Residential Sales 4":   _sc.J_TAG_ROJO_VaRS4,
        "VaRS5  — Valencia Residential Sales 5":   _sc.J_TAG_ROJO_VaRS5,
    },
}

EQUIPOS_JUDICIAL: dict[str, str] = {
    k: v for equipos in EQUIPOS_POR_CIUDAD_JUDICIAL.values() for k, v in equipos.items()
}
"""Plano: ``label_equipo → tag``. Derivado de :data:`EQUIPOS_POR_CIUDAD_JUDICIAL`."""


# ---------------------------------------------------------------------------
# Derivación código → ciudad (única fuente de verdad)
# ---------------------------------------------------------------------------

def _extraer_codigo(label: str) -> str:
    """Extrae el código corto (``BaRR3``) del label completo
    (``"BaRR3  — BCN Residential Rentals 3"``). El código es lo que precede
    al primer espacio en blanco del label tras eliminar trailing whitespace
    del propio código.
    """
    return label.split(" ", 1)[0].strip()


def _construir_codigo_a_ciudad() -> dict[str, str]:
    """Une los dos contextos (extra+judicial) en un único mapping
    código→ciudad. Asserta coherencia: si un código aparece en ambos
    contextos, debe mapear a la misma ciudad.
    """
    out: dict[str, str] = {}
    for fuente in (EQUIPOS_POR_CIUDAD_EXTRAJUDICIAL, EQUIPOS_POR_CIUDAD_JUDICIAL):
        for ciudad, equipos in fuente.items():
            for label in equipos.keys():
                codigo = _extraer_codigo(label)
                previo = out.get(codigo)
                if previo is not None and previo != ciudad:
                    raise AssertionError(
                        f"Incoherencia en catálogo ciudades: código {codigo!r} "
                        f"aparece en ciudades {previo!r} y {ciudad!r}."
                    )
                out[codigo] = ciudad
    return out


_CODIGO_A_CIUDAD: dict[str, str] = _construir_codigo_a_ciudad()


def ciudad_de_equipo(codigo: str) -> str | None:
    """Devuelve la ciudad a la que pertenece un código de equipo.

    Parámetros
    ----------
    codigo:
        Código corto del equipo (por ejemplo ``"BaRR3"``, ``"MaRS15"``).
        No debe llevar el sufijo descriptivo del label de UI.

    Devuelve
    --------
    El nombre canónico de la ciudad, o ``None`` si el código no existe en
    el catálogo (incluido el caso de cadena vacía).

    Ejemplos
    --------
    >>> ciudad_de_equipo("BaRR3")
    'Barcelona'
    >>> ciudad_de_equipo("SaRS1")
    'Santander'
    >>> ciudad_de_equipo("XXXX") is None
    True
    """
    if not codigo:
        return None
    return _CODIGO_A_CIUDAD.get(codigo)


# ---------------------------------------------------------------------------
# Convención de carpeta de sistema
# ---------------------------------------------------------------------------

def es_carpeta_de_sistema(nombre: str) -> bool:
    """Convención del proyecto: cualquier carpeta cuyo nombre empieza por
    ``_`` es de sistema (``_PLANTILLA``, ``_audit``, ``_Sin clasificar``).
    Las ciudades del catálogo no llevan guion bajo, por lo que jamás
    colisionan con esta regla.
    """
    return bool(nombre) and nombre.startswith("_")
