"""Un fichero de control nuevo en `00_Input` se declara en TODOS los registros.

Remedia la frontera de la R-B (L4-06/L4-07/L5-01), no sus ejemplos: el defecto no era
que faltara `_apertura_v1.json` en dos listas, era que **nadie comprueba** que un fichero
de protocolo esté declarado en las cuatro superficies que clasifican `00_Input`. Este
guard itera sobre lo que el módulo declara, así que el siguiente fichero de control que
alguien añada ahí lo obliga a declararlo o pone esto rojo.
"""
import fnmatch

import pytest

from core import config
from core import apertura_v1_estado as est


def _casa(nombre: str, patrones) -> bool:
    return any(fnmatch.fnmatch(nombre, p) for p in patrones)


@pytest.mark.parametrize("nombre", est.FICHEROS_CONTROL)
def test_esta_en_el_registro_canonico_de_control(nombre):
    """`config.INTAKE_CONTROL_FILES` es el hogar único (su propio comentario lo dice)."""
    assert nombre in config.INTAKE_CONTROL_FILES


@pytest.mark.parametrize("nombre", est.FICHEROS_CONTROL)
def test_el_inventario_de_la_sala_de_maquina_no_lo_toma_por_documento(nombre):
    """Si esto falla, el OCR lo inventaría y saldría en `_cobertura` como `sin_soporte`
    — en la MISMA corrida que lo escribió, porque la secuencia lo abre antes del OCR."""
    from core import sala_maquina as sm
    assert sm._es_control(nombre) is True


@pytest.mark.parametrize("nombre", est.FICHEROS_CONTROL)
def test_el_merge_del_checkin_no_lo_trata_como_contenido(nombre):
    """Si esto falla, un checkin da CONFLICT sobre un fichero de control, o empuja el
    estado de una copia al canon."""
    assert _casa(nombre, config.MERGE_EXCLUSIONS)


@pytest.mark.parametrize("nombre", est.FICHEROS_CONTROL)
def test_el_carveout_del_plugin_permite_reescribirlo(nombre):
    """El plugin `expedientes-xl` prohíbe sobrescribir en `00_Input` salvo protocolo."""
    from plugins.expedientes_xl.tiers import PROTOCOL_APPEND, PROTOCOL_EDIT
    assert _casa(nombre, tuple(PROTOCOL_EDIT) + tuple(PROTOCOL_APPEND))


def test_los_temporales_de_la_escritura_atomica_tampoco_son_documento():
    """Un huérfano de `mkstemp` no puede acabar en el inventario de prueba solo porque
    el proceso muriera entre el temporal y el `os.replace`."""
    from core import sala_maquina as sm
    huerfano = est.PREFIJOS_CONTROL[0] + "abc123.tmp"
    assert sm._es_control(huerfano) is True
    assert _casa(huerfano, config.MERGE_EXCLUSIONS)


def test_el_guard_no_esta_vacio():
    """Hermano de los guards de este repo: si `FICHEROS_CONTROL` quedara vacío, los
    parametrizados de arriba pasarían sin comprobar nada."""
    assert est.FICHEROS_CONTROL, "sin ficheros declarados, este guard es decorativo"
    assert est.PREFIJOS_CONTROL
