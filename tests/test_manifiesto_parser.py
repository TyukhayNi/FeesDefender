from importlib import import_module
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / ".claude/skills/organizar-sala-lectura/scripts"))
mp = import_module("manifiesto_parser")

_MANIF_7COL = """<!-- GENERADO — NO EDITAR A MANO -->
| sha256 | ruta_original | nombre_canonico | tipo | fecha | parte | parent_id |
|---|---|---|---|---|---|---|
| aaaa | 01_Drive EV/Catastro.pdf | 2024-04-26_catastro.pdf | 08. PENDIENTE DE CLASIFICAR | 2024-04-26 | propietario |  |
| bbbb | 04_Manual/req.pdf | 2025-07-22_requerimiento.pdf | 07. RECLAMACIONES | 2025-07-22 | propietario |  |
"""

_MANIF_9COL = """<!-- GENERADO — NO EDITAR A MANO -->
| sha256 | ruta_original | nombre_canonico | tipo | fecha | parte | parent_id | categoria | subcategoria_crm |
|---|---|---|---|---|---|---|---|---|
| aaaa | sudespacho_1/civil/x.pdf | 2025-01-01_x.pdf | pdf | 2025-01-01 | propietario |  | 07. RECLAMACIONES | civil |
"""


def test_parsea_7_columnas_por_cabecera():
    filas = mp.parse_manifiesto(_MANIF_7COL)
    assert len(filas) == 2
    assert filas[0]["sha256"] == "aaaa"
    assert filas[0]["nombre_canonico"] == "2024-04-26_catastro.pdf"
    assert filas[0]["parent_id"] == ""


def test_parsea_columnas_extra_por_cabecera():
    filas = mp.parse_manifiesto(_MANIF_9COL)
    assert len(filas) == 1
    assert filas[0]["categoria"] == "07. RECLAMACIONES"
    assert filas[0]["subcategoria_crm"] == "civil"


def test_salta_cabecera_y_separador():
    filas = mp.parse_manifiesto(_MANIF_7COL)
    assert all(f["sha256"] not in ("sha256", "---") for f in filas)


def test_sin_cabecera_usa_cols_canon():
    texto = "| ccc | a/b.pdf | 2025-05-05_b.pdf | pdf | 2025-05-05 | comprador |  |"
    filas = mp.parse_manifiesto(texto)
    assert filas[0]["ruta_original"] == "a/b.pdf"
    assert list(filas[0].keys()) == mp.COLS_CANON


_MANIF_MALFORMADO = """<!-- GENERADO — NO EDITAR A MANO -->
| sha256 | ruta_original | nombre_canonico | tipo | fecha | parte | parent_id |
|---|---|---|---|---|---|---|
| aaaa | 01_Drive EV/ok.pdf | 2024-04-26_ok.pdf | pdf | 2024-04-26 | propietario |  |
| falta_columnas | 01_Drive EV/mala.pdf | 2024-05-01_mala.pdf |
"""


def test_estricto_lanza_si_hay_fila_malformada():
    with pytest.raises(ValueError, match="fila.*malformada|columnas"):
        mp.parse_manifiesto(_MANIF_MALFORMADO, estricto=True)


def test_estricto_ok_si_todas_las_filas_cuadran():
    filas = mp.parse_manifiesto(_MANIF_7COL, estricto=True)
    assert len(filas) == 2


def test_no_estricto_sigue_siendo_tolerante():
    # Sin estricto, la fila mala se salta en silencio (comportamiento heredado).
    filas = mp.parse_manifiesto(_MANIF_MALFORMADO)
    assert len(filas) == 1


def test_sha_valido_acepta_sha256_md5_y_vacio():
    assert mp.sha_valido("a" * 64)
    assert mp.sha_valido("md5:" + "b" * 32)
    assert mp.sha_valido("")
    assert not mp.sha_valido("aaaa")
    assert not mp.sha_valido("md5:zzzz")
