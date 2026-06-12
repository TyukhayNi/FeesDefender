# -*- coding: utf-8 -*-
"""F7 — empaquetado .skill + e2e de registro en ambos escenarios (E&V y particular).

- ``package_skill``: produce un ``.skill`` con ``<skill>/SKILL.md`` en la raíz,
  excluye ``node_modules/`` y los datos de ``logs/`` (solo README).
- e2e: en un expediente E&V (core ``ensure_case``) y en uno de particular
  (scaffolder común), generar/registrar un escrito deja el manifiesto
  ``05_Procedimiento/_index.md`` y el wikilink en ``## Navegación`` de ``_caso.md``,
  **sin tocar el frontmatter**.
"""
from __future__ import annotations

import importlib.util
import zipfile
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SHARED = _REPO / ".claude" / "skills" / "_shared"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pkg = _load(_REPO / "scripts" / "package_skill.py", "package_skill_mod")
scaffold_caso = _load(_SHARED / "scaffold_caso.py", "scaffold_caso_e2e")
ro = _load(_SHARED / "registrar_outputs.py", "registrar_outputs_e2e")


def _demanda(fichero="DEMANDA.docx"):
    return {"fichero": fichero, "tipo": "demanda", "perspectiva": "actora",
            "destino": "05_Procedimiento", "fuentes": ["preparacion"], "estado": "borrador"}


# --- empaquetado -------------------------------------------------------------

def test_package_escritos_produce_skill(tmp_path):
    destino = pkg.package(_REPO / ".claude" / "skills" / "escritos-judiciales", tmp_path)
    assert destino.exists() and destino.suffix == ".skill"
    names = zipfile.ZipFile(destino).namelist()
    assert "escritos-judiciales/SKILL.md" in names
    assert "escritos-judiciales/scripts/registrar_outputs.py" in names


def test_package_juicio_excluye_node_modules_y_logs(tmp_path):
    juicio = _REPO / ".claude" / "skills" / "preparacion-juicio-oral"
    if not juicio.exists():
        return  # aún no versionada en este checkout
    names = zipfile.ZipFile(pkg.package(juicio, tmp_path)).namelist()
    assert not any("node_modules" in n for n in names)
    assert not any("__pycache__" in n for n in names)
    # De logs/ solo viaja el README.
    logs = [n for n in names if "/logs/" in n]
    assert all(n.endswith("/logs/README.md") for n in logs)


# --- e2e particular ----------------------------------------------------------

def test_e2e_particular(tmp_path):
    base = scaffold_caso.scaffold(tmp_path / "part", titulo="Asunto P", case_id="REF-P")
    ro.registrar(str(base), [_demanda("DEMANDA_REF-P.docx")])
    idx = (base / "05_Procedimiento" / "_index.md").read_text(encoding="utf-8")
    assert "DEMANDA_REF-P.docx" in idx
    assert "[[DEMANDA_REF-P]]" in (base / "00_Input" / "_caso.md").read_text(encoding="utf-8")


# --- e2e E&V (core) ----------------------------------------------------------

def test_e2e_ev_no_toca_frontmatter(tmp_casos_root):
    from core import case_manager as cm

    case = cm.ensure_case("EV-2026-099", titulo="Asunto E&V", cliente="EV MMC SPAIN")
    caso_md = case / "00_Input" / "_caso.md"
    antes_fm = caso_md.read_text(encoding="utf-8").split("---", 2)[1]

    ro.registrar(str(case), [_demanda("DEMANDA_EV-2026-099.docx")])

    texto = caso_md.read_text(encoding="utf-8")
    despues_fm = texto.split("---", 2)[1]
    assert antes_fm == despues_fm                      # frontmatter intacto
    assert "[[DEMANDA_EV-2026-099]]" in texto          # wikilink añadido
    assert (case / "05_Procedimiento" / "_index.md").exists()
