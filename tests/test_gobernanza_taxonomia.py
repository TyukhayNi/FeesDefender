"""Guard de gobernanza — la taxonomía de casos y la estructura de carpetas son
canónicas en :mod:`core.config` (Fase 2 de ``docs/GOBERNANZA_FUENTES_VERDAD.md``).

Este test **ancla el código como fuente de verdad única**. Si alguien cambia la
taxonomía en ``core/config.py`` (añade, quita o renombra un tipo de caso) o la
lista de subcarpetas del expediente, este test se rompe y obliga a actualizarlo
conscientemente — y, con él, los espejos documentales que necesitan la taxonomía
inline (listados en el mapa de dependencias de ``docs/ARQUITECTURA.md``: la
referencia CRM ``docs/INTEGRACION_SUDESPACHO.md`` §8 y las skills LLM
``engel-volkers`` / ``preparacion-audiencia-previa`` / ``triaje-viabilidad``,
que corren en servidor y no pueden importar ``config``).

**Por qué NO escanea los ``.md`` buscando la taxonomía:** se midió el repo y las
cadenas viven legítimamente en varios sitios — las skills LLM la necesitan inline
y la bitácora de ``STATUS.md`` menciona tipos de caso en prosa histórica
("regresión ``BAD_DEBT``", "tipo ``NEGATIVA_OFERTA``"). Un escáner daría falsos
positivos sobre contenido legítimo. El anclaje en código es el enforcement
robusto y de mantenimiento nulo; la completitud de los espejos se mantiene a mano
guiada por el mapa de dependencias.
"""
from __future__ import annotations

from core import config


# Modelo canónico esperado (debe coincidir con core/config.py). Cambiar aquí SOLO
# junto con el cambio en config.py — ese acoplamiento deliberado es el guard.
_ACTORA = {
    "BAD_DEBT",
    "NEGATIVA_OFERTA",
    "NEGATIVA_ARRAS",
    "NEGATIVA_ESCRITURA",
    "NEGATIVA_CONTRATO_ARRENDAMIENTO",
    "VUELTA",
    "INCUMPLIMIENTO_EXCLUSIVA",
}
_DEFENSIVA = {
    "RESPONSABILIDAD_PROFESIONAL",
    "DEVOLUCION_RESERVA",
    "LAU_20",
    "DEVOLUCION_HONORARIOS",
}
_OTROS = {"OTROS"}

_CASO_SUBDIRS = (
    "00_Input",
    "01_Procesado",
    "02_Analisis",
    "03_Decision",
    "04_Output predemanda",
    "05_Procedimiento",
    "06_Anonimizado",
    "07_AI cowork",
    "90_Notas personales",
)


def test_tipos_actora_canonicos():
    assert set(config.TIPOS_CASO_ACTORA) == _ACTORA


def test_tipos_defensiva_canonicos():
    # Este es el guard que habría cazado el drift de STATUS ("3 tipos" cuando el
    # código ya tenía 4, faltaba DEVOLUCION_HONORARIOS).
    assert set(config.TIPOS_CASO_DEFENSIVA) == _DEFENSIVA


def test_tipos_otros_canonicos():
    assert set(config.TIPOS_CASO_OTROS) == _OTROS


def test_union_all_sin_solapes():
    esperado = _ACTORA | _DEFENSIVA | _OTROS
    assert set(config.TIPOS_CASO_ALL) == esperado
    # La unión no puede perder entradas por claves repetidas entre grupos.
    assert len(config.TIPOS_CASO_ALL) == len(_ACTORA) + len(_DEFENSIVA) + len(_OTROS)


def test_cada_entrada_tiene_tag_y_descripcion():
    for tipo, valor in config.TIPOS_CASO_ALL.items():
        assert isinstance(valor, tuple) and len(valor) == 2, tipo
        tag, descripcion = valor
        assert tag.strip() and descripcion.strip(), tipo


def test_tags_crm_unicos():
    tags = [tag for tag, _ in config.TIPOS_CASO_ALL.values()]
    assert len(tags) == len(set(tags)), "tags CRM duplicados en la taxonomía"


def test_posicion_de_tipo_coherente():
    for tipo in _ACTORA:
        assert config.posicion_de_tipo(tipo) == config.POSICION_ACTORA, tipo
    for tipo in _DEFENSIVA:
        assert config.posicion_de_tipo(tipo) == config.POSICION_DEFENSIVA, tipo
    for tipo in _OTROS:
        assert config.posicion_de_tipo(tipo) == config.POSICION_OTROS, tipo


def test_caso_subdirs_canonicos():
    # Guarda la estructura de carpetas del expediente (nombres tipo oración).
    assert tuple(config.CASO_SUBDIRS) == _CASO_SUBDIRS
