from importlib import import_module
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / ".claude/skills/organizar-sala-lectura/scripts"))
idx = import_module("indices_desde_manifiesto")

_MANIF = """<!-- GENERADO — NO EDITAR A MANO -->
| sha256 | ruta_original | nombre_canonico | tipo | fecha | parte | parent_id | categoria | subcategoria_crm |
|---|---|---|---|---|---|---|---|---|
| a | sudespacho_1/civil/auto.pdf | 2025-03-01_auto.pdf | pdf | 2025-03-01 | propietario |  | 07. RECLAMACIONES | civil |
| b | sudespacho_1/demanda/dda.pdf | 2025-05-10_demanda.pdf | pdf | 2025-05-10 | propietario |  | 07. RECLAMACIONES | demanda |
| c | 03_Email/corr.eml | 2025-06-01_correo.eml | eml | 2025-06-01 | propietario |  | 07. RECLAMACIONES |  |
| d | 01_Drive EV/encargo.pdf | 2024-01-01_encargo.pdf | pdf | 2024-01-01 | propietario |  | 01. ACTIVACIÓN |  |
| e | 01_Drive EV/sin_fecha.pdf | 0000-00-00_sinfecha.pdf | pdf | 0000-00-00 | propietario |  | 01. ACTIVACIÓN |  |
"""


def _filas():
    import manifiesto_parser
    return manifiesto_parser.parse_manifiesto(_MANIF)


_MANIF_7COL = """<!-- GENERADO — NO EDITAR A MANO -->
| sha256 | ruta_original | nombre_canonico | tipo | fecha | parte | parent_id |
|---|---|---|---|---|---|---|
| f | 04_Manual/burofax.pdf | 2025-07-22_certificacion_envio.pdf | 07. RECLAMACIONES | 2025-07-22 |  |  |
| g | 01_Drive EV/nota_simple.pdf | 2021-00-00_nota_simple.pdf | 01. ACTIVACIÓN | 2021-00-00 | vendedor |  |
"""


def test_indice_cae_a_tipo_si_falta_columna_categoria():
    """Manifiestos de 7 columnas (previos a `categoria`) guardan la categoría E&V
    en `tipo` — regresión W-02VND1 2026-07-23: sin este fallback, TODO caía en
    "08. PENDIENTE DE CLASIFICAR" pese a tener categoría real."""
    import manifiesto_parser
    filas = manifiesto_parser.parse_manifiesto(_MANIF_7COL)
    txt = idx.construir_indice(filas)
    assert "## 07. RECLAMACIONES" in txt
    assert "## 01. ACTIVACIÓN" in txt
    assert "## 08. PENDIENTE DE CLASIFICAR" not in txt


def test_indice_agrupa_por_categoria_y_ordena_fecha_desc():
    txt = idx.construir_indice(_filas())
    assert "## 01. ACTIVACIÓN" in txt
    assert "## 07. RECLAMACIONES" in txt
    # Dentro de ACTIVACIÓN, 2024-01-01 (con fecha) va ANTES que 0000-00-00 (incierta, al final).
    act = txt.split("## 01. ACTIVACIÓN", 1)[1].split("## ", 1)[0]
    assert act.index("2024-01-01_encargo") < act.index("0000-00-00_sinfecha")


def test_reclamaciones_subagrupa_por_subcategoria_crm():
    txt = idx.construir_indice(_filas())
    rec = txt.split("## 07. RECLAMACIONES", 1)[1]
    assert "### civil" in rec
    assert "### demanda" in rec
    assert "### correspondencia" in rec  # el .eml sin subcategoria


def test_cronologia_orden_ascendente_incierta_al_final():
    txt = idx.construir_cronologia(_filas())
    assert txt.index("2024-01-01_encargo") < txt.index("2025-06-01_correo")
    assert txt.index("2025-06-01_correo") < txt.index("0000-00-00_sinfecha")


def test_derivar_escribe_ambos_ficheros_idempotente(tmp_path):
    (tmp_path / "_MANIFIESTO.md").write_text(_MANIF, encoding="utf-8")
    i1, c1 = idx.derivar(tmp_path / "_MANIFIESTO.md", tmp_path)
    a, b = i1.read_text(encoding="utf-8"), c1.read_text(encoding="utf-8")
    idx.derivar(tmp_path / "_MANIFIESTO.md", tmp_path)
    assert i1.read_text(encoding="utf-8") == a
    assert c1.read_text(encoding="utf-8") == b
    assert a.startswith("<!-- GENERADO — NO EDITAR A MANO -->")
