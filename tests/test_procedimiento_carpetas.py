"""Las cinco carpetas de fase son un set CERRADO y un solo sitio las nombra."""
import importlib.util
import pathlib

import pytest

from core.procedimiento import carpetas


def test_son_exactamente_cinco_y_en_orden():
    assert carpetas.CARPETAS_FASE == (
        "01_Monitorio - Demanda y documentos",
        "02_Monitorio - Oposicion y documentos",
        "03_Ordinario - Demanda y documentos",
        "04_Ordinario - Contestacion y documentos",
        "05_Otros escritos",
    )


def test_el_cajon_de_otros_es_la_quinta():
    assert carpetas.CARPETA_OTROS == "05_Otros escritos"
    assert carpetas.CARPETA_OTROS in carpetas.CARPETAS_FASE


def test_las_cuatro_primeras_llevan_escrito_rector():
    assert carpetas.CARPETAS_CON_RECTOR == carpetas.CARPETAS_FASE[:4]
    assert carpetas.CARPETA_OTROS not in carpetas.CARPETAS_CON_RECTOR


@pytest.mark.parametrize("nombre", list(carpetas.CARPETAS_FASE))
def test_reconoce_las_cinco(nombre):
    assert carpetas.es_carpeta_fase(nombre) is True


@pytest.mark.parametrize("nombre", [
    "Jurisprudencia",                      # subcarpeta legítima, pero NO de fase
    "01_Monitorio",                        # prefijo, no el nombre completo
    "06_Otra cosa",
    "",
    "05_Otros escritos/sub",               # una ruta no es una carpeta de fase
    "05_OTROS ESCRITOS",                   # el set es sensible a la grafía exacta
    " 05_Otros escritos",                  # ni con espacio delante
])
def test_rechaza_lo_que_no_es_carpeta_de_fase(nombre):
    assert carpetas.es_carpeta_fase(nombre) is False


def test_las_cinco_carpetas_NO_estan_todavia_en_registrar_outputs():
    """**El estado de hoy, escrito como test y no como ausencia.**

    Ampliar `SUBDESTINOS_EXTRA` amplía dónde puede escribir un helper que escribe, y eso
    contradecía la restricción de 4a de no escribir nada — lo destapó la R1 (su H-01) y
    Nikolai decidió el 2026-09-09 sacarlo a su propia pieza. Este test fija el estado
    intermedio para que nadie lo lea como un olvido, y **se pondrá rojo** cuando esa pieza
    entre: ese rojo es la señal de que hay que retirarlo y poner el de no-drift.
    """
    ruta = (pathlib.Path(__file__).resolve().parents[1]
            / ".claude" / "skills" / "_shared" / "registrar_outputs.py")
    spec = importlib.util.spec_from_file_location("registrar_outputs_shared", ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    de_fase = {f"05_Procedimiento/{c}" for c in carpetas.CARPETAS_FASE}
    assert not (de_fase & set(mod.SUBDESTINOS_EXTRA)), (
        "las carpetas de fase ya están en el helper: retira este test y restaura el de "
        "no-drift, que vive en la pieza de `destinos-de-fase`")
    assert "05_Procedimiento/Jurisprudencia" in mod.SUBDESTINOS_EXTRA, (
        "y Jurisprudencia sigue ahí: esto no es una limpieza del helper")
