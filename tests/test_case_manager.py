"""Smoke tests del case_manager."""

from __future__ import annotations

import importlib

from core.config import CASO_SUBDIRS


def test_ensure_case_crea_estructura(tmp_casos_root):
    from core import case_manager
    importlib.reload(case_manager)

    case_dir = case_manager.ensure_case(
        "EV-2026-TEST",
        titulo="Caso de prueba",
        cliente="[CLIENTE_1]",
        contraparte="[CONTRAPARTE_1]",
    )
    assert case_dir.exists()
    for sub in CASO_SUBDIRS:
        assert (case_dir / sub).is_dir(), f"Falta subcarpeta {sub}"
    assert (case_dir / "00_Input" / "_caso.md").exists()


def test_ensure_case_idempotente(tmp_casos_root):
    from core import case_manager
    importlib.reload(case_manager)

    case_manager.ensure_case("EV-2026-TEST")
    # Crear un archivo de usuario que NO debe ser sobrescrito
    user_file = (tmp_casos_root / "EV-2026-TEST" / "90_Notas personales" / "mi_nota.md")
    user_file.write_text("contenido del abogado", encoding="utf-8")

    case_manager.ensure_case("EV-2026-TEST")  # segunda llamada
    assert user_file.read_text(encoding="utf-8") == "contenido del abogado"


def test_list_cases(tmp_casos_root):
    from core import case_manager
    importlib.reload(case_manager)

    case_manager.ensure_case("EV-2026-001")
    case_manager.ensure_case("EV-2026-002")
    cases = case_manager.list_cases()
    assert "EV-2026-001" in cases
    assert "EV-2026-002" in cases
    # _PLANTILLA empieza con _ → debe quedar fuera
    assert not any(c.startswith("_") for c in cases)
