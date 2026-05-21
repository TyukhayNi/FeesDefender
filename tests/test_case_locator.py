"""Tests para core.casos.case_locator — Fase 1 subdivisión por ciudades."""
from __future__ import annotations

import importlib
from pathlib import Path

import pytest


@pytest.fixture
def root(tmp_path, monkeypatch):
    """CASOS_ROOT aislado en tmp_path."""
    r = tmp_path / "CASOS"
    r.mkdir()
    monkeypatch.setenv("CASOS_ROOT", str(r))
    from core import config as cfg
    importlib.reload(cfg)
    yield r


# ---------------------------------------------------------------------------
# path_for — layout flat (legacy)
# ---------------------------------------------------------------------------

class TestPathForFlat:
    def test_caso_existente(self, root):
        from core.casos.case_locator import path_for
        (root / "BaRR3 - Roser").mkdir()
        assert path_for("BaRR3 - Roser") == root / "BaRR3 - Roser"

    def test_caso_inexistente_devuelve_flat(self, root):
        from core.casos.case_locator import path_for
        result = path_for("NO-EXISTE")
        assert result == root / "NO-EXISTE"
        assert not result.exists()

    def test_ignora_carpeta_sistema(self, root):
        from core.casos.case_locator import path_for
        (root / "_PLANTILLA").mkdir()
        result = path_for("_PLANTILLA")
        assert result == root / "_PLANTILLA"


# ---------------------------------------------------------------------------
# path_for — layout por ciudades
# ---------------------------------------------------------------------------

class TestPathForCiudad:
    def test_caso_en_barcelona(self, root):
        from core.casos.case_locator import path_for
        (root / "Barcelona" / "BaRR3 - Roser").mkdir(parents=True)
        assert path_for("BaRR3 - Roser") == root / "Barcelona" / "BaRR3 - Roser"

    def test_caso_en_sin_clasificar(self, root):
        from core.casos.case_locator import path_for
        (root / "_Sin clasificar" / "CASO-X").mkdir(parents=True)
        assert path_for("CASO-X") == root / "_Sin clasificar" / "CASO-X"

    def test_flat_tiene_prioridad_sobre_ciudad(self, root):
        from core.casos.case_locator import path_for
        (root / "BaRR3 - Roser").mkdir()
        (root / "Barcelona" / "BaRR3 - Roser").mkdir(parents=True)
        assert path_for("BaRR3 - Roser") == root / "BaRR3 - Roser"


# ---------------------------------------------------------------------------
# path_for_ciudad
# ---------------------------------------------------------------------------

class TestPathForCiudadExplicita:
    def test_compone_ruta(self, root):
        from core.casos.case_locator import path_for_ciudad
        result = path_for_ciudad("BaRR3 - Roser", "Barcelona")
        assert result == root / "Barcelona" / "BaRR3 - Roser"
        assert not result.exists()

    def test_sin_clasificar(self, root):
        from core.casos.case_locator import path_for_ciudad
        result = path_for_ciudad("CASO-X", "_Sin clasificar")
        assert result == root / "_Sin clasificar" / "CASO-X"


# ---------------------------------------------------------------------------
# list_cases
# ---------------------------------------------------------------------------

class TestListCases:
    def test_flat_solo(self, root):
        from core.casos.case_locator import list_cases
        (root / "BaRR3 - Roser").mkdir()
        (root / "MaRS2 - Puerto Rico").mkdir()
        (root / "_PLANTILLA").mkdir()
        result = [p.name for p in list_cases()]
        assert result == ["BaRR3 - Roser", "MaRS2 - Puerto Rico"]

    def test_ciudad_solo(self, root):
        from core.casos.case_locator import list_cases
        (root / "Barcelona" / "BaRR3 - Roser").mkdir(parents=True)
        (root / "Madrid" / "MaRS2 - Puerto Rico").mkdir(parents=True)
        result = [p.name for p in list_cases()]
        assert result == ["BaRR3 - Roser", "MaRS2 - Puerto Rico"]

    def test_mixto_flat_y_ciudad(self, root):
        from core.casos.case_locator import list_cases
        (root / "SaRS1 - Castelar").mkdir()
        (root / "Barcelona" / "BaRR3 - Roser").mkdir(parents=True)
        result = [p.name for p in list_cases()]
        assert "BaRR3 - Roser" in result
        assert "SaRS1 - Castelar" in result

    def test_sin_duplicados(self, root):
        from core.casos.case_locator import list_cases
        (root / "BaRR3 - Roser").mkdir()
        (root / "Barcelona" / "BaRR3 - Roser").mkdir(parents=True)
        names = [p.name for p in list_cases()]
        assert names.count("BaRR3 - Roser") == 1

    def test_filtro_por_ciudad(self, root):
        from core.casos.case_locator import list_cases
        (root / "Barcelona" / "BaRR3 - Roser").mkdir(parents=True)
        (root / "Madrid" / "MaRS2 - Puerto Rico").mkdir(parents=True)
        result = [p.name for p in list_cases(ciudad="Barcelona")]
        assert result == ["BaRR3 - Roser"]

    def test_filtro_ciudad_inexistente(self, root):
        from core.casos.case_locator import list_cases
        result = list(list_cases(ciudad="Bilbao"))
        assert result == []

    def test_root_inexistente(self, root, monkeypatch):
        import shutil
        shutil.rmtree(root)
        from core.casos.case_locator import list_cases
        result = list(list_cases())
        assert result == []

    def test_no_incluye_carpetas_ciudad_como_caso(self, root):
        from core.casos.case_locator import list_cases
        (root / "Barcelona").mkdir()
        (root / "Madrid").mkdir()
        (root / "SaRS1 - Castelar").mkdir()
        names = [p.name for p in list_cases()]
        assert "Barcelona" not in names
        assert "Madrid" not in names
        assert "SaRS1 - Castelar" in names


# ---------------------------------------------------------------------------
# all_cities_present
# ---------------------------------------------------------------------------

class TestAllCitiesPresent:
    def test_vacio(self, root):
        from core.casos.case_locator import all_cities_present
        assert all_cities_present() == []

    def test_con_ciudades(self, root):
        from core.casos.case_locator import all_cities_present
        (root / "Barcelona" / "BaRR3").mkdir(parents=True)
        (root / "Madrid" / "MaRS2").mkdir(parents=True)
        (root / "Sevilla").mkdir()
        result = all_cities_present()
        assert "Barcelona" in result
        assert "Madrid" in result
        assert "Sevilla" not in result

    def test_sin_clasificar(self, root):
        from core.casos.case_locator import all_cities_present
        (root / "_Sin clasificar" / "CASO-X").mkdir(parents=True)
        assert "_Sin clasificar" in all_cities_present()


# ---------------------------------------------------------------------------
# move_to_city — Fase 3
# ---------------------------------------------------------------------------

class TestMoveToCity:
    def test_mover_flat_a_ciudad(self, root):
        from core.case_manager import ensure_case
        from core.casos.case_locator import move_to_city
        ensure_case("BaRR3 - Roser")
        dest = move_to_city("BaRR3 - Roser", "Barcelona",
                            "reasignación correcta", "nikolai")
        assert dest == root / "Barcelona" / "BaRR3 - Roser"
        assert dest.is_dir()
        assert not (root / "BaRR3 - Roser").exists()

    def test_mover_entre_ciudades(self, root):
        from core.case_manager import ensure_case
        from core.casos.case_locator import move_to_city
        ensure_case("CASO-X", ciudad="Madrid")
        dest = move_to_city("CASO-X", "Barcelona",
                            "reubicación del caso", "nikolai")
        assert dest == root / "Barcelona" / "CASO-X"
        assert not (root / "Madrid" / "CASO-X").exists()

    def test_actualiza_metadata_ciudad(self, root):
        from core.case_manager import ensure_case
        from core.casos.case_locator import move_to_city
        import yaml
        ensure_case("BaRR3 - Roser", ciudad="Sevilla")
        move_to_city("BaRR3 - Roser", "Barcelona",
                     "corrección de ciudad", "nikolai")
        index = root / "Barcelona" / "BaRR3 - Roser" / "00_Input" / "_caso.md"
        text = index.read_text(encoding="utf-8")
        _, fm_raw, _ = text.split("---", 2)
        fm = yaml.safe_load(fm_raw)
        assert fm["ciudad"] == "Barcelona"

    def test_escribe_audit_log(self, root):
        from core.case_manager import ensure_case
        from core.casos.case_locator import move_to_city
        import json
        ensure_case("BaRR3 - Roser")
        move_to_city("BaRR3 - Roser", "Barcelona",
                     "reasignación correcta", "nikolai")
        log = root / "_audit" / "relocations.jsonl"
        assert log.exists()
        entry = json.loads(log.read_text(encoding="utf-8").strip())
        assert entry["operacion"] == "reasignar_ciudad"
        assert entry["ciudad_destino"] == "Barcelona"
        assert entry["usuario"] == "nikolai"

    def test_motivo_corto_rechazado(self, root):
        from core.case_manager import ensure_case
        from core.casos.case_locator import move_to_city
        ensure_case("BaRR3 - Roser")
        with pytest.raises(ValueError, match="10 caracteres"):
            move_to_city("BaRR3 - Roser", "Barcelona", "corto", "nikolai")

    def test_caso_inexistente(self, root):
        from core.casos.case_locator import move_to_city
        with pytest.raises(FileNotFoundError):
            move_to_city("NO-EXISTE", "Barcelona",
                         "motivo suficiente", "nikolai")

    def test_rollback_si_falla_metadata(self, root, monkeypatch):
        from core.case_manager import ensure_case
        from core.casos import case_locator
        ensure_case("BaRR3 - Roser")
        original = case_locator._update_ciudad_metadata
        def _boom(*a, **kw):
            raise OSError("simulación de fallo")
        monkeypatch.setattr(case_locator, "_update_ciudad_metadata", _boom)
        with pytest.raises(OSError):
            case_locator.move_to_city("BaRR3 - Roser", "Barcelona",
                                      "motivo suficiente", "nikolai")
        assert (root / "BaRR3 - Roser").is_dir()
        assert not (root / "Barcelona" / "BaRR3 - Roser").exists()

    def test_mismo_destino_noop(self, root):
        from core.case_manager import ensure_case
        from core.casos.case_locator import move_to_city
        ensure_case("BaRR3 - Roser", ciudad="Barcelona")
        dest = move_to_city("BaRR3 - Roser", "Barcelona",
                            "ya estaba aquí", "nikolai")
        assert dest == root / "Barcelona" / "BaRR3 - Roser"
        assert dest.is_dir()


# ---------------------------------------------------------------------------
# Fase 2 — campo ciudad en ensure_case
# ---------------------------------------------------------------------------

class TestEnsureCaseConCiudad:
    def test_caso_nuevo_con_ciudad_crea_bajo_ciudad(self, root):
        from core.case_manager import ensure_case
        path = ensure_case("BaRR3 - Roser", ciudad="Barcelona")
        assert path == root / "Barcelona" / "BaRR3 - Roser"
        assert path.is_dir()
        assert (path / "00_Input" / "_caso.md").exists()

    def test_caso_nuevo_sin_ciudad_crea_flat(self, root):
        from core.case_manager import ensure_case
        path = ensure_case("BaRR3 - Roser")
        assert path == root / "BaRR3 - Roser"
        assert path.is_dir()

    def test_ciudad_persistida_en_frontmatter(self, root):
        from core.case_manager import ensure_case
        import yaml
        ensure_case("BaRR3 - Roser", ciudad="Barcelona")
        index = root / "Barcelona" / "BaRR3 - Roser" / "00_Input" / "_caso.md"
        text = index.read_text(encoding="utf-8")
        _, fm_raw, _ = text.split("---", 2)
        fm = yaml.safe_load(fm_raw)
        assert fm["ciudad"] == "Barcelona"
        assert fm["meta"]["ciudad"] == "Barcelona"

    def test_caso_existente_no_se_mueve(self, root):
        from core.case_manager import ensure_case
        path1 = ensure_case("BaRR3 - Roser")
        assert path1 == root / "BaRR3 - Roser"
        path2 = ensure_case("BaRR3 - Roser", ciudad="Barcelona")
        assert path2 == root / "BaRR3 - Roser"
        assert not (root / "Barcelona" / "BaRR3 - Roser").exists()

    def test_caso_existente_actualiza_ciudad_en_metadata(self, root):
        from core.case_manager import ensure_case
        import yaml
        ensure_case("BaRR3 - Roser")
        ensure_case("BaRR3 - Roser", ciudad="Barcelona")
        index = root / "BaRR3 - Roser" / "00_Input" / "_caso.md"
        text = index.read_text(encoding="utf-8")
        _, fm_raw, _ = text.split("---", 2)
        fm = yaml.safe_load(fm_raw)
        assert fm["ciudad"] == "Barcelona"
        assert fm["meta"]["ciudad"] == "Barcelona"

    def test_locator_encuentra_caso_en_ciudad(self, root):
        from core.case_manager import ensure_case
        from core.casos.case_locator import path_for
        ensure_case("BaRR3 - Roser", ciudad="Barcelona")
        assert path_for("BaRR3 - Roser") == root / "Barcelona" / "BaRR3 - Roser"

    def test_idempotencia_con_ciudad(self, root):
        from core.case_manager import ensure_case
        p1 = ensure_case("BaRR3 - Roser", ciudad="Barcelona")
        p2 = ensure_case("BaRR3 - Roser", ciudad="Barcelona")
        assert p1 == p2

    def test_caso_nuevo_ciudad_sin_clasificar(self, root):
        from core.case_manager import ensure_case
        path = ensure_case("CASO-X", ciudad="_Sin clasificar")
        assert path == root / "_Sin clasificar" / "CASO-X"
        assert path.is_dir()


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

class TestAppendAuditLog:
    def test_crea_directorio_y_fichero(self, root):
        from core.casos.case_locator import append_audit_log
        import json
        append_audit_log({"operacion": "test", "case_id": "X"})
        log = root / "_audit" / "relocations.jsonl"
        assert log.exists()
        entry = json.loads(log.read_text(encoding="utf-8").strip())
        assert entry["operacion"] == "test"
        assert "ts" in entry

    def test_append_no_sobrescribe(self, root):
        from core.casos.case_locator import append_audit_log
        append_audit_log({"operacion": "a"})
        append_audit_log({"operacion": "b"})
        log = root / "_audit" / "relocations.jsonl"
        lines = log.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2


# ---------------------------------------------------------------------------
# Integración con caso_path de config.py
# ---------------------------------------------------------------------------

class TestCasoPathDelegaAlLocator:
    def test_flat(self, root):
        from core.config import caso_path
        (root / "BaRR3 - Roser").mkdir()
        assert caso_path("BaRR3 - Roser") == root / "BaRR3 - Roser"

    def test_ciudad(self, root):
        from core.config import caso_path
        (root / "Barcelona" / "BaRR3 - Roser").mkdir(parents=True)
        assert caso_path("BaRR3 - Roser") == root / "Barcelona" / "BaRR3 - Roser"


# ---------------------------------------------------------------------------
# Integración con list_cases de case_manager.py
# ---------------------------------------------------------------------------

class TestCaseManagerListCases:
    def test_flat(self, root):
        from core.case_manager import list_cases
        (root / "BaRR3 - Roser").mkdir()
        (root / "_PLANTILLA").mkdir()
        assert list_cases() == ["BaRR3 - Roser"]

    def test_ciudad(self, root):
        from core.case_manager import list_cases
        (root / "Barcelona" / "BaRR3 - Roser").mkdir(parents=True)
        assert list_cases() == ["BaRR3 - Roser"]
