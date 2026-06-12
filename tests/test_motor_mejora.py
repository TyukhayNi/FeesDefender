# -*- coding: utf-8 -*-
"""Tests de scripts/motor_mejora.py (F12): umbral, agregación y propuestas ancladas."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_MOTOR = Path(__file__).resolve().parents[1] / "scripts" / "motor_mejora.py"


def _load():
    spec = importlib.util.spec_from_file_location("motor_mejora_mod", _MOTOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mm = _load()


def _seed(store: Path, skill: str, n_posts: int):
    d = store / skill
    d.mkdir(parents=True)
    # uso.jsonl con n refs
    with open(d / "uso.jsonl", "w", encoding="utf-8") as fh:
        for i in range(1, n_posts + 1):
            fh.write(json.dumps({"skill": skill, "ref": f"W-{i}", "accion": "generar"}) + "\n")
    # posts: dos comparten alegación; varios inadmitidos
    alegaciones = ["falta de legitimación pasiva", "falta de legitimación pasiva",
                   "prescripción", "caducidad", "litispendencia"]
    for i in range(1, n_posts + 1):
        post = {"ref": f"W-{i}", "metricas": {
            "resultado": "inadmitido" if i <= 3 else "estimado",
            "alegacion_no_prevista": alegaciones[(i - 1) % len(alegaciones)],
            "valoracion": 2}}
        (d / f"W-{i}_post.jsonl").write_text(json.dumps(post) + "\n", encoding="utf-8")
    # un delta con muchas reescrituras
    (d / "W-1_delta.md").write_text(
        "# Delta\n\n- Resumen: 1 añadidos · 0 suprimidos · 4 reescritos\n", encoding="utf-8")


def test_no_genera_bajo_umbral(tmp_path, monkeypatch):
    monkeypatch.setenv("FEESDEFENDER_SKILL_LOGS", str(tmp_path / "store"))
    _seed(tmp_path / "store", "escritos-judiciales", 2)
    destino, listo = mm.ejecutar("escritos-judiciales", umbral=5)
    assert destino is None and listo is False


def test_genera_informe_con_propuestas_ancladas(tmp_path, monkeypatch):
    monkeypatch.setenv("FEESDEFENDER_SKILL_LOGS", str(tmp_path / "store"))
    _seed(tmp_path / "store", "escritos-judiciales", 5)
    destino, listo = mm.ejecutar("escritos-judiciales", umbral=5)
    assert listo is True and destino is not None
    texto = destino.read_text(encoding="utf-8")
    assert destino.name == "MEJORAS_escritos-judiciales.md"
    # Alegación recurrente anclada a refs.
    assert "falta de legitimación pasiva" in texto
    assert "W-1" in texto and "W-2" in texto
    # Delta muy reescrito → propuesta de plantilla.
    assert "W-1_delta.md" in texto
    assert "4 párrafos reescritos" in texto
    # Resultados adversos dominantes → propuesta de revisión de criterio.
    assert "Revisar criterio" in texto
    # Valoración media baja.
    assert "Valoración media baja" in texto


def test_force_genera_aunque_no_haya_umbral(tmp_path, monkeypatch):
    monkeypatch.setenv("FEESDEFENDER_SKILL_LOGS", str(tmp_path / "store"))
    _seed(tmp_path / "store", "cendoj-descarga", 1)
    destino, listo = mm.ejecutar("cendoj-descarga", umbral=5, force=True)
    assert destino is not None and listo is False
    assert "aún no" in destino.read_text(encoding="utf-8")
