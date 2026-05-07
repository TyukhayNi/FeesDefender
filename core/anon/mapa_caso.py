"""Gestión del mapa de entidades compartido por caso.

Persistido en `06_Anonimizado/_mapa_caso.json` (nomenclatura del proyecto:
`06_Anonimizado/` antes de `07_AI cowork/`).

A diferencia del Anonimizador original — que mantenía un `_mapa.json` por
documento independiente —, FeesDefender unifica el mapa a nivel de caso:
si el documento 1 etiqueta a "Ivan Petrov" como `[NOMBRE]`, el documento 2
del mismo caso mantiene esa misma etiqueta para esa persona.
"""

from __future__ import annotations

from pathlib import Path

from core.case_manager import caso_path
from core.anon.anonimizar import MapaEntidades

# La carpeta canónica de output anonimizado en FeesDefender.
# IMPORTANTE: el código usa "06_Anonimizado" (tipo oración, sin espacio inicial).
SUBDIR_ANONIMIZADO = "06_Anonimizado"
MAPA_FILENAME = "_mapa_caso.json"


def ruta_mapa_caso(case_id: str) -> Path:
    """Ruta absoluta del `_mapa_caso.json` de un caso. No lo crea."""
    return caso_path(case_id) / SUBDIR_ANONIMIZADO / MAPA_FILENAME


def cargar_mapa_caso(case_id: str) -> MapaEntidades:
    """Carga el mapa compartido del caso.

    Si no existe (caso nuevo o nunca anonimizado), devuelve un `MapaEntidades`
    vacío listo para usar.
    """
    ruta = ruta_mapa_caso(case_id)
    if ruta.exists():
        return MapaEntidades.cargar_json(ruta)
    return MapaEntidades()


def guardar_mapa_caso(case_id: str, mapa: MapaEntidades) -> Path:
    """Persiste el mapa del caso. Crea la subcarpeta si falta."""
    ruta = ruta_mapa_caso(case_id)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    mapa.exportar_json(ruta)
    return ruta
