"""Tests para scripts.migrate_to_city_structure — Fase 4."""
from __future__ import annotations

import csv
import importlib
import json
from pathlib import Path

import pytest


@pytest.fixture
def root(tmp_path, monkeypatch):
    r = tmp_path / "CASOS"
    r.mkdir()
    monkeypatch.setenv("CASOS_ROOT", str(r))
    from core import config as cfg
    importlib.reload(cfg)
    yield r


def _create_flat_case(root: Path, name: str) -> Path:
    """Crea un caso flat mínimo con _caso.md."""
    d = root / name
    d.mkdir(parents=True)
    inp = d / "00_Input"
    inp.mkdir()
    index = inp / "_caso.md"
    index.write_text(
        f"---\ncase_id: {name}\ntipo: caso_index\nciudad: null\nmeta:\n  ciudad: null\n---\n# {name}\n",
        encoding="utf-8",
    )
    return d


# ---------------------------------------------------------------------------
# plan
# ---------------------------------------------------------------------------

class TestPlan:
    def test_genera_csv(self, root):
        from typer.testing import CliRunner
        from scripts.migrate_to_city_structure import app

        _create_flat_case(root, "BaRR3 - Roser")
        _create_flat_case(root, "MaRS2 - Puerto Rico")

        runner = CliRunner()
        result = runner.invoke(app, ["plan"])
        assert result.exit_code == 0
        assert "2 expediente" in result.output

        csvs = list((root / "_audit").glob("migration_plan_*.csv"))
        assert len(csvs) == 1
        with csvs[0].open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 2
        names = {r["expediente"] for r in rows}
        assert "BaRR3 - Roser" in names
        assert "MaRS2 - Puerto Rico" in names

    def test_detecta_ciudades(self, root):
        from typer.testing import CliRunner
        from scripts.migrate_to_city_structure import app

        _create_flat_case(root, "BaRR3 - Roser")
        _create_flat_case(root, "SaRS1 - Castelar")

        runner = CliRunner()
        runner.invoke(app, ["plan"])

        csvs = list((root / "_audit").glob("migration_plan_*.csv"))
        with csvs[0].open(encoding="utf-8-sig", newline="") as f:
            rows = {r["expediente"]: r for r in csv.DictReader(f)}
        assert rows["BaRR3 - Roser"]["ciudad_detectada"] == "Barcelona"
        assert rows["SaRS1 - Castelar"]["ciudad_detectada"] == "Santander"

    def test_prefijo_no_reconocido(self, root):
        from typer.testing import CliRunner
        from scripts.migrate_to_city_structure import app

        _create_flat_case(root, "CASO-RARO-123")
        runner = CliRunner()
        runner.invoke(app, ["plan"])

        csvs = list((root / "_audit").glob("migration_plan_*.csv"))
        with csvs[0].open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        assert rows[0]["ciudad_final"] == "_Sin clasificar"
        assert rows[0]["observaciones"] == "prefijo no reconocido"

    def test_sin_casos_flat(self, root):
        from typer.testing import CliRunner
        from scripts.migrate_to_city_structure import app

        runner = CliRunner()
        result = runner.invoke(app, ["plan"])
        assert result.exit_code == 0
        assert "Nada que planificar" in result.output


# ---------------------------------------------------------------------------
# apply
# ---------------------------------------------------------------------------

def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


class TestApply:
    def test_migracion_completa(self, root):
        from typer.testing import CliRunner
        from scripts.migrate_to_city_structure import app

        _create_flat_case(root, "BaRR3 - Roser")
        _create_flat_case(root, "MaRS2 - Puerto Rico")

        csv_path = root / "_audit" / "plan.csv"
        csv_path.parent.mkdir(exist_ok=True)
        _write_csv(csv_path, [
            {"expediente": "BaRR3 - Roser", "prefijo": "BaRR3",
             "ciudad_detectada": "Barcelona", "ciudad_final": "Barcelona",
             "accion": "mover", "observaciones": ""},
            {"expediente": "MaRS2 - Puerto Rico", "prefijo": "MaRS2",
             "ciudad_detectada": "Madrid", "ciudad_final": "Madrid",
             "accion": "mover", "observaciones": ""},
        ])

        runner = CliRunner()
        result = runner.invoke(app, ["apply", str(csv_path)], input="MIGRAR\n")
        assert result.exit_code == 0
        assert "2 movidos" in result.output
        assert (root / "Barcelona" / "BaRR3 - Roser").is_dir()
        assert (root / "Madrid" / "MaRS2 - Puerto Rico").is_dir()
        assert not (root / "BaRR3 - Roser").exists()
        assert not (root / "MaRS2 - Puerto Rico").exists()

    def test_idempotencia(self, root):
        from typer.testing import CliRunner
        from scripts.migrate_to_city_structure import app

        _create_flat_case(root, "BaRR3 - Roser")
        csv_path = root / "_audit" / "plan.csv"
        csv_path.parent.mkdir(exist_ok=True)
        _write_csv(csv_path, [
            {"expediente": "BaRR3 - Roser", "prefijo": "BaRR3",
             "ciudad_detectada": "Barcelona", "ciudad_final": "Barcelona",
             "accion": "mover", "observaciones": ""},
        ])

        runner = CliRunner()
        runner.invoke(app, ["apply", str(csv_path)], input="MIGRAR\n")
        result = runner.invoke(app, ["apply", str(csv_path)], input="MIGRAR\n")
        assert result.exit_code == 0
        assert "ya en Barcelona" in result.output
        assert "0 movidos" in result.output

    def test_cancelacion(self, root):
        from typer.testing import CliRunner
        from scripts.migrate_to_city_structure import app

        _create_flat_case(root, "BaRR3 - Roser")
        csv_path = root / "_audit" / "plan.csv"
        csv_path.parent.mkdir(exist_ok=True)
        _write_csv(csv_path, [
            {"expediente": "BaRR3 - Roser", "prefijo": "BaRR3",
             "ciudad_detectada": "Barcelona", "ciudad_final": "Barcelona",
             "accion": "mover", "observaciones": ""},
        ])

        runner = CliRunner()
        result = runner.invoke(app, ["apply", str(csv_path)], input="NO\n")
        assert "Cancelado" in result.output
        assert (root / "BaRR3 - Roser").is_dir()

    def test_snapshot_preflight(self, root):
        from typer.testing import CliRunner
        from scripts.migrate_to_city_structure import app

        _create_flat_case(root, "BaRR3 - Roser")
        csv_path = root / "_audit" / "plan.csv"
        csv_path.parent.mkdir(exist_ok=True)
        _write_csv(csv_path, [
            {"expediente": "BaRR3 - Roser", "prefijo": "BaRR3",
             "ciudad_detectada": "Barcelona", "ciudad_final": "Barcelona",
             "accion": "mover", "observaciones": ""},
        ])

        runner = CliRunner()
        runner.invoke(app, ["apply", str(csv_path)], input="MIGRAR\n")

        snapshots = list((root / "_audit").glob("snapshot_pre_migration_*.json"))
        assert len(snapshots) == 1
        data = json.loads(snapshots[0].read_text(encoding="utf-8"))
        assert len(data["cases"]) == 1
        assert data["cases"][0]["name"] == "BaRR3 - Roser"

    def test_accion_omitir(self, root):
        from typer.testing import CliRunner
        from scripts.migrate_to_city_structure import app

        _create_flat_case(root, "BaRR3 - Roser")
        csv_path = root / "_audit" / "plan.csv"
        csv_path.parent.mkdir(exist_ok=True)
        _write_csv(csv_path, [
            {"expediente": "BaRR3 - Roser", "prefijo": "BaRR3",
             "ciudad_detectada": "Barcelona", "ciudad_final": "Barcelona",
             "accion": "omitir", "observaciones": ""},
        ])

        runner = CliRunner()
        result = runner.invoke(app, ["apply", str(csv_path)], input="MIGRAR\n")
        assert "0 movimiento" in result.output
        assert (root / "BaRR3 - Roser").is_dir()
