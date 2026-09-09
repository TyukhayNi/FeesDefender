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


def test_registrar_outputs_admite_las_cinco_sin_drift():
    """Las dos listas viven en sitios distintos por una razón —el `.skill` empaquetado no
    tiene `core/`, así que importarlo rompería la skill en el servidor— y este test las
    ata: si alguien añade una carpeta de fase y no toca el helper, el escrito se
    registraría fuera de su fase.
    """
    ruta = (pathlib.Path(__file__).resolve().parents[1]
            / ".claude" / "skills" / "_shared" / "registrar_outputs.py")
    spec = importlib.util.spec_from_file_location("registrar_outputs_shared", ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    esperadas = {f"05_Procedimiento/{c}" for c in carpetas.CARPETAS_FASE}
    assert esperadas <= set(mod.SUBDESTINOS_EXTRA), (
        "faltan carpetas de fase en SUBDESTINOS_EXTRA: "
        f"{sorted(esperadas - set(mod.SUBDESTINOS_EXTRA))}")
    assert esperadas <= mod.DESTINOS_VALIDOS
