from __future__ import annotations
import importlib.util
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
HELPER = ROOT / ".claude" / "skills" / "organizar-sala-lectura" / "scripts" / "manifiesto_a_catalogo.py"


def _load():
    spec = importlib.util.spec_from_file_location("manifiesto_a_catalogo", HELPER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_MANIF = """<!-- GENERADO — NO EDITAR A MANO -->
| sha256 | ruta_original | nombre_canonico | tipo | fecha | parte | parent_id |
|---|---|---|---|---|---|---|
| aaaa | 01_Drive EV/Catastro.pdf | 2024-04-26_catastro.pdf | 08. PENDIENTE DE CLASIFICAR | 2024-04-26 | propietario |  |
| bbbb | 04_Manual/RESPUESTA_RESOLUCION.pdf | 2025-07-22_requerimiento.pdf | 07. RECLAMACIONES | 2025-07-22 | propietario |  |
"""


def test_deriva_catalogo_yaml(tmp_path):
    mod = _load()
    (tmp_path / "_MANIFIESTO.md").write_text(_MANIF, encoding="utf-8")
    out = mod.derivar(tmp_path / "_MANIFIESTO.md", tmp_path / "indice_documental.yaml")
    data = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert len(data) == 2
    e0 = {d["hash"]: d for d in data}["aaaa"]
    assert e0["nombre_original"] == "Catastro.pdf"
    assert e0["fuente"] == "drive_ev"
    assert e0["tipo_documental"] == "08. PENDIENTE DE CLASIFICAR"
    assert e0["fecha_doc"] == "2024-04-26"
    assert e0["parte"] == "propietario"
    assert e0["estado"] == "original"


def test_campos_coinciden_con_CatalogEntry():
    """Anti-drift: los campos que emite el helper existen en core.CatalogEntry."""
    import dataclasses
    from core.catalogo_documental import CatalogEntry
    mod = _load()
    validos = {f.name for f in dataclasses.fields(CatalogEntry)}
    assert set(mod.CAMPOS_EMITIDOS) <= validos


def test_fuente_skill_sin_drift_con_core():
    """Anti-drift: la resolución de fuente del helper coincide con core.intake_lotes.fuente_de."""
    from core.intake_lotes import fuente_de
    mod = _load()
    casos = ["01_Drive EV/a.pdf", "05_CRM/b.pdf", "2026-07-17_email_01/c.eml",
             "2026-07-17_whatsapp_02/rol/chat/_chat.txt", "02_Whatsapp/r/c/_chat.txt",
             "06_Entrevistas/g.mp4", "raiz.pdf", "Rara/x.pdf"]
    for c in casos:
        assert mod._fuente(c) == fuente_de(c), c


def test_idempotente(tmp_path):
    mod = _load()
    (tmp_path / "_MANIFIESTO.md").write_text(_MANIF, encoding="utf-8")
    o = tmp_path / "indice_documental.yaml"
    mod.derivar(tmp_path / "_MANIFIESTO.md", o)
    a = o.read_text(encoding="utf-8")
    mod.derivar(tmp_path / "_MANIFIESTO.md", o)
    assert o.read_text(encoding="utf-8") == a
