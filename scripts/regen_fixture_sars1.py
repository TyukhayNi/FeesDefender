"""Regenera (y diffea) el fixture gold-standard de regresión SaRS1.

Herramienta de desarrollo para el flujo de mejoras del motor `core/anon/`.
Cuando una mejora cambia *intencionalmente* la salida del anonimizador, el
test `tests/test_anon_regresion_SaRS1.py` se pone en rojo. Este script:

1. Re-ejecuta el motor sobre las 4 piezas split de SaRS1 (input local).
2. Escribe el output a un directorio temporal.
3. Diffea contra `tests/fixtures/anon/SaRS1/expected/` y muestra QUÉ cambia.
4. Con `--promote`, copia el output nuevo sobre `expected/` (tras tu revisión).

El fixture contiene PII real y está en `.gitignore`: este script trabaja
SIEMPRE en local, nunca sube nada. Sin `--promote` es solo lectura/diff.

Uso:
    python -m scripts.regen_fixture_sars1            # diff (no toca el fixture)
    python -m scripts.regen_fixture_sars1 --promote  # promueve tras revisar el diff
"""

from __future__ import annotations

import difflib
import json
import re
import shutil
import sys
from pathlib import Path

import typer

ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "anon" / "SaRS1"
INPUT_SPLIT_DIR = FIXTURE_DIR / "input" / "_split"
EXPECTED_DIR = FIXTURE_DIR / "expected"

CASE_ID = "SaRS1 - Castelar, 37-39, Santander - (SIN REFERENCIA) - Otros"
PIEZAS = [
    ("Demanda_Std_1_ocr/01_CEDULA_EMPLAZAMIENTO_01.pdf", "01_cedula_emplazamiento_01.md"),
    ("Demanda_Std_1_ocr/02_DECRETO_01.pdf", "02_decreto_01.md"),
    ("Demanda_Std_1_ocr/03_DEMANDA_01.pdf", "03_demanda_01.md"),
    ("Demanda_Std_2_ocr/01_DOC_ANEXO_01.pdf", "01_doc_anexo_01.md"),
]

_FECHA_RE = re.compile(r"^fecha:\s*.+$", re.MULTILINE)

app = typer.Typer(add_completion=False, help="Regenera/diffea el fixture SaRS1.")


def _norm(texto: str) -> str:
    return _FECHA_RE.sub("fecha: <FECHA>", texto)


def _generar(out_dir: Path) -> Path:
    """Ejecuta el motor sobre las 4 piezas y escribe a out_dir/06_Anonimizado/."""
    import core.anon.api as api_mod
    import core.anon.mapa_caso as mapa_mod
    from core.anon.api import anonimizar_documento
    from core.anon.mapa_caso import MapaEntidades, guardar_mapa_caso

    (out_dir / "06_Anonimizado").mkdir(parents=True, exist_ok=True)
    orig_api, orig_mapa = api_mod.caso_path, mapa_mod.caso_path
    api_mod.caso_path = lambda cid: out_dir
    mapa_mod.caso_path = lambda cid: out_dir
    try:
        mapa = MapaEntidades()
        for pdf_rel, md_esp in PIEZAS:
            res = anonimizar_documento(
                case_id=CASE_ID,
                ruta_origen=INPUT_SPLIT_DIR / pdf_rel,
                tipo_proc="Juicio Ordinario",
                mapa_caso=mapa,
                politica="REPROCESAR",
            )
            if not res["ok"]:
                raise RuntimeError(f"Motor falló en {pdf_rel}: {res.get('error')}")
        guardar_mapa_caso(CASE_ID, mapa)
    finally:
        api_mod.caso_path, mapa_mod.caso_path = orig_api, orig_mapa
    return out_dir / "06_Anonimizado"


@app.command()
def main(promote: bool = typer.Option(False, "--promote", help="Copia el output nuevo sobre expected/.")) -> None:
    if not INPUT_SPLIT_DIR.is_dir() or not EXPECTED_DIR.is_dir():
        typer.echo("✗ Fixture SaRS1 no presente localmente. Nada que regenerar.")
        raise typer.Exit(1)

    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="regen_sars1_"))
    gen_dir = _generar(tmp)

    archivos = [md for _, md in PIEZAS] + ["_mapa_caso.json"]
    hubo_cambios = False
    for nombre in archivos:
        gen = gen_dir / nombre
        ref = EXPECTED_DIR / nombre
        gen_txt = _norm(gen.read_text(encoding="utf-8")) if gen.exists() else ""
        ref_txt = _norm(ref.read_text(encoding="utf-8")) if ref.exists() else ""
        if nombre.endswith(".json"):
            # Comparar solo las entradas estables del mapa (igual que el test
            # de regresión): mapa/mapa_directo/contadores/protegidos. Descarta
            # campos volátiles como "generado" (timestamp).
            def _estable(raw: str) -> str:
                d = json.loads(raw or "{}")
                return json.dumps({
                    "mapa": dict(d.get("mapa", {})),
                    "mapa_directo": dict(d.get("mapa_directo", {})),
                    "contadores": dict(d.get("contadores", {})),
                    "protegidos": sorted(d.get("protegidos", [])),
                }, ensure_ascii=False, indent=2, sort_keys=True)
            gen_txt, ref_txt = _estable(gen_txt), _estable(ref_txt)
        if gen_txt == ref_txt:
            typer.echo(f"  = {nombre} (sin cambios)")
            continue
        hubo_cambios = True
        diff = difflib.unified_diff(
            ref_txt.splitlines(), gen_txt.splitlines(),
            fromfile=f"expected/{nombre}", tofile=f"nuevo/{nombre}", lineterm="",
        )
        typer.echo(f"\n  ≠ {nombre}:")
        for ln in diff:
            typer.echo("    " + ln)

    if not hubo_cambios:
        typer.echo("\nSin diferencias: el fixture ya refleja la salida actual del motor.")
        shutil.rmtree(tmp, ignore_errors=True)
        return

    if promote:
        for nombre in archivos:
            gen = gen_dir / nombre
            if gen.exists():
                shutil.copy2(gen, EXPECTED_DIR / nombre)
        typer.echo(f"\n✅ Fixture promovido a {EXPECTED_DIR}")
    else:
        typer.echo("\n(diff only) Revisa el diff. Si solo cambia lo intencional, "
                   "vuelve a lanzar con --promote.")
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    app()
