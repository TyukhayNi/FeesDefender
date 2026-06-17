"""Tests de la sala de lectura (F4–F6)."""
from __future__ import annotations

import importlib
from pathlib import Path

import pytest


def _reload():
    from core import case_manager, catalogo_documental, inventory, sala_lectura
    importlib.reload(case_manager)
    importlib.reload(inventory)
    importlib.reload(catalogo_documental)
    importlib.reload(sala_lectura)
    return case_manager, inventory, catalogo_documental, sala_lectura


def _caso_con_docs(case_manager, inventory, catalogo, docs):
    """Crea un caso con `docs` = [(subcarpeta, nombre, contenido_bytes_o_str)] y
    devuelve (case_id, case_dir) con inventario y catálogo ya construidos."""
    case_id = "EV-2026-TEST"
    case_dir = case_manager.ensure_case(case_id)
    for sub, name, content in docs:
        p = case_dir / "00_Input" / sub / name
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            p.write_bytes(content)
        else:
            p.write_text(content, encoding="utf-8")
    inventory.scan(case_id)
    catalogo.build_catalog(case_id)
    return case_id, case_dir


# --- Task 1: Extender CatalogEntry y hacer load_catalog tolerante ---


def test_catalog_entry_campos_nuevos_por_defecto(tmp_casos_root):
    from core import case_manager as cm, inventory as inv, catalogo_documental as cat
    importlib.reload(cm); importlib.reload(inv); importlib.reload(cat)
    case_id, _ = _caso_con_docs(cm, inv, cat, [("01_Drive EV", "x.txt", "hola")])
    e = cat.load_catalog(case_id)[0]
    assert e.descripcion is None
    assert e.fecha_fuente is None
    assert e.confianza is None
    assert e.nombre_canonico is None
    assert e.ruta_sala_lectura is None


def test_load_catalog_tolera_claves_desconocidas(tmp_casos_root):
    from core import case_manager as cm, inventory as inv, catalogo_documental as cat
    importlib.reload(cm); importlib.reload(inv); importlib.reload(cat)
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [("01_Drive EV", "x.txt", "hola")])
    import yaml
    path = case_dir / "01_Procesado" / "indice_documental.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data[0]["campo_de_otra_version"] = "ignorar"
    path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    entries = cat.load_catalog(case_id)  # no debe lanzar
    assert len(entries) == 1


# --- Task 2: save_catalog ---


def test_save_catalog_roundtrip(tmp_casos_root):
    from core import case_manager as cm, inventory as inv, catalogo_documental as cat
    importlib.reload(cm); importlib.reload(inv); importlib.reload(cat)
    case_id, _ = _caso_con_docs(cm, inv, cat, [("01_Drive EV", "x.txt", "hola")])
    entries = cat.load_catalog(case_id)
    entries[0].tipo_documental = "05. FACTURACIÓN - FINANZAS"
    entries[0].confianza = 0.9
    cat.save_catalog(case_id, entries)
    reloaded = cat.load_catalog(case_id)
    assert reloaded[0].tipo_documental == "05. FACTURACIÓN - FINANZAS"
    assert reloaded[0].confianza == 0.9


# --- Task 3: reglas deterministas — categoría por keyword e imagen ---


@pytest.mark.parametrize("nombre, esperado", [
    ("Factura honorarios 2025.pdf", "05. FACTURACIÓN - FINANZAS"),
    ("Burofax requerimiento de pago.pdf", "07. RECLAMACIONES"),
    ("Hoja de encargo en exclusiva.pdf", "01. ACTIVACIÓN"),
    ("Oferta del comprador.pdf", "03. OFERTAS"),
    ("Contrato de arras penitenciales.pdf", "04. ARRAS - ARRENDAMIENTOS"),
    ("Nota simple registral.pdf", "06. PBC"),
    ("Documento sin pistas.pdf", None),
])
def test_clasificar_por_keyword(nombre, esperado):
    from core import sala_lectura
    importlib.reload(sala_lectura)
    assert sala_lectura._categoria_por_nombre(nombre) == esperado


def test_categoria_imagen():
    from core import sala_lectura
    importlib.reload(sala_lectura)
    assert sala_lectura._es_imagen(".jpg") is True
    assert sala_lectura._es_imagen(".pdf") is False


def test_clasificar_tolera_guiones_bajos():
    from core import sala_lectura
    importlib.reload(sala_lectura)
    assert sala_lectura._categoria_por_nombre("justificante_de_pago_2025.pdf") == "05. FACTURACIÓN - FINANZAS"


# --- Task 4: fecha determinista — patrón en nombre ---


def test_fecha_desde_nombre_iso():
    from core import sala_lectura
    importlib.reload(sala_lectura)
    assert sala_lectura._fecha_desde_nombre("2025-07-12 oferta.pdf") == ("2025-07-12", "contenido")
    assert sala_lectura._fecha_desde_nombre("oferta 12-07-2025.pdf") == ("2025-07-12", "contenido")
    assert sala_lectura._fecha_desde_nombre("sin fecha.pdf") == (None, None)
