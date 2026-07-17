# tests/test_expedientes_xl_integracion.py
"""E2E del servidor consolidado sobre un arbol de caso simulado."""
import asyncio
import pytest

pytest.importorskip("mcp")  # el server importa mcp.server.fastmcp; skip si no está

from plugins.expedientes_xl.server import build_server
from plugins.expedientes_xl.tiers import Zonas

class Orac:
    def __init__(self): self.cold = set()
    def status(self, p): return "COLD" if p.name in self.cold else "HOT"
    def subtree_cold_stats(self, p): return (len(self.cold), 10)

@pytest.fixture
def mundo(tmp_path):
    g = tmp_path / "G"; h = tmp_path / "H"
    caso = g / "Unidades compartidas" / "EXPEDIENTES" / "CASOS" / "Caso1"
    (caso / "00_Input" / "03_Email").mkdir(parents=True)
    (caso / "90_Notas personales").mkdir()
    (caso / "01_Procesado").mkdir()
    # mismo nombre que un fichero ya depositado: fuerza el aborto del punto 6
    (caso / "01_Procesado" / "m.eml").write_text("copia", encoding="utf-8")
    (caso / "00_Input" / "_caso.md").write_text("---\nestado: x\n---\n", encoding="utf-8")
    (caso / "00_Input" / "03_Email" / "m.eml").write_text("mail", encoding="utf-8")
    (caso / "90_Notas personales" / "priv.md").write_text("secreto", encoding="utf-8")
    (h / "Mi unidad").mkdir(parents=True)
    (h / "Mi unidad" / "doc.txt").write_text("ev", encoding="utf-8")
    zonas = Zonas(rw_roots=(g,), ro_roots=(h,))
    return build_server(zonas, Orac()), g, h, caso

def _call(srv, tool, **args):
    return asyncio.run(srv.call_tool(tool, args))

def test_e2e(mundo):
    srv, g, h, caso = mundo
    # 1. leer H: (ro) OK; escribir H: NO
    assert "ev" in str(_call(srv, "read_text", path=str(h / "Mi unidad" / "doc.txt")))
    with pytest.raises(Exception, match="solo-lectura"):
        _call(srv, "write_text", path=str(h / "Mi unidad" / "x.txt"), text="no")
    # 2. tree del caso NO expone 90_Notas
    t = str(_call(srv, "tree", path=str(caso)))
    assert "priv.md" not in t and "m.eml" in t
    # 3. search_content no lee Tier 0
    s = str(_call(srv, "search_content", path=str(caso), consulta="secreto"))
    assert "priv.md" not in s
    # 4. intake: crear-nuevo bajo 00_Input ok; sobrescribir no
    nuevo = caso / "00_Input" / "04_Manual" / "n.pdf"
    _call(srv, "write_text", path=str(nuevo), text="pdfsimulado")
    with pytest.raises(Exception, match="forense-inmutable"):
        _call(srv, "write_text", path=str(nuevo), text="v2")
    # 5. carve-out: editar _caso.md ok
    _call(srv, "edit_text", path=str(caso / "00_Input" / "_caso.md"),
          old="estado: x", new="estado: prestado")
    # 6. copy_dir cuyo destino PISA un fichero ya depositado en 00_Input -> aborto
    #    total ANTES de copiar nada (01_Procesado contiene m.eml, que ya existe en
    #    00_Input/03_Email). Crear-nuevo bajo 00_Input sí es legal; pisar, no.
    with pytest.raises(Exception, match="forense-inmutable"):
        _call(srv, "copy_dir", src=str(caso / "01_Procesado"),
              dst=str(caso / "00_Input" / "03_Email"))
    assert (caso / "00_Input" / "03_Email" / "m.eml").read_text(encoding="utf-8") == "mail"
