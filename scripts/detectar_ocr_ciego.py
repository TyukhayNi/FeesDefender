"""Detector de «OCR ciego bajo el sello» (paso 0 de `docs/MEJORAS_FUTURAS.md` #90).

Criba, SIN escribir nada en el expediente, los documentos que la Sala de máquina
marcó `ok` pero cuyo cuerpo pudo perderse: un PDF con capa de texto (aunque sea
solo el pie de firma de LexNET) hace que `--skip-text` salte la página entera,
y `ocr_quality`, que promedia sobre el documento, no lo nota.

Uso:
  python -m scripts.detectar_ocr_ciego caso  "<case_id|W-code>"
  python -m scripts.detectar_ocr_ciego todos [--salida informe.md]

Es un CRIBADO, no un veredicto: marca candidatos a revisar. La medición honesta
de cuánto texto falta exige re-OCR-izar el documento y comparar (ver #90).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import typer

from core import pdf_paginas
from core import sala_maquina as sm
from core.casos import case_locator
from core.config import caso_path, settings

app = typer.Typer(add_completion=False)

# El discriminante vive en `core.pdf_paginas`, que es donde lo consumen también el
# motor (peldaño 2 de la escalera) y la calidad por página. Compartirlo es el
# punto: si el cribado y el motor divergieran, el detector dejaría de describir
# lo que el motor hace.
MIN_PX_RASTER = pdf_paginas.MIN_PX_RASTER
MAX_CHARS_PAGINA = pdf_paginas.MAX_CHARS_SELLO

_W_RE = re.compile(r"\((W-[A-Z0-9]+)\)")


@dataclass
class Perfil:
    n_pags: int
    chars_fuente: int
    paginas_saltadas: list[int]
    firma_repetida: int
    acroform: bool


def perfilar(pdf: Path) -> Perfil | None:
    """Perfil por página del PDF fuente. `None` si no se puede abrir."""
    perfil = pdf_paginas.perfilar_paginas(pdf)
    if not perfil:
        return None
    saltadas = pdf_paginas.paginas_ciegas(perfil)
    return Perfil(
        n_pags=len(perfil),
        chars_fuente=sum(p.chars for p in perfil),
        paginas_saltadas=saltadas,
        firma_repetida=pdf_paginas.firmas_repetidas(perfil, saltadas),
        acroform=pdf_paginas.tiene_acroform(pdf),
    )


def filas_ok(case_dir: Path) -> list[dict]:
    """Documentos `ok` por `pypdf`/`ocr`, desde `_cobertura.json`.

    Si el caso no tiene `_cobertura.json` (corridas anteriores a que existiera ese
    fichero — ver #84), se reconstruye desde el frontmatter de `03_MD/`, que
    `_escribir_md` sí persiste con `extractor` y `ocr_quality`.
    """
    sm_dir = sm._sala_maquina_dir(case_dir)
    cobertura = sm_dir / "_cobertura.json"
    if cobertura.exists():
        filas = json.loads(cobertura.read_text(encoding="utf-8"))
        return [f for f in filas
                if f.get("estado") == "ok" and f.get("metodo") in ("pypdf", "ocr")]

    reconstruidas: list[dict] = []
    for md in sorted((sm_dir / "03_MD").glob("*.md")):
        meta = _frontmatter(md)
        if meta.get("extractor") in ("pypdf", "ocr") and meta.get("ocr_quality") == "ok":
            reconstruidas.append({"slug": md.stem, "rel_path": meta.get("source_path", ""),
                                  "metodo": meta.get("extractor")})
    return reconstruidas


def _frontmatter(md: Path) -> dict:
    """Frontmatter YAML del MD, sin cargar el cuerpo (que puede ser enorme)."""
    meta: dict = {}
    try:
        with md.open("r", encoding="utf-8", errors="replace") as fh:
            if fh.readline().strip() != "---":
                return meta
            for _ in range(40):
                linea = fh.readline()
                if not linea or linea.strip() == "---":
                    break
                if ":" in linea:
                    clave, _, valor = linea.partition(":")
                    meta[clave.strip()] = valor.strip().strip('"')
    except Exception:
        pass
    return meta


def analizar_caso(case_dir: Path) -> tuple[list[tuple[dict, Perfil]], dict]:
    """Candidatos del caso + conteos de lo descartado y por qué.

    Discriminante clave: solo puede haber pérdida por `--skip-text` si el PDF
    FUENTE ya traía capa de texto. Con 0 chars el documento fue por la ruta OCR y
    se OCR-izó entero — marcarlo sería un falso positivo (verificado: DNIs y
    capturas que la primera versión del detector marcaba no perdían nada).
    """
    candidatos: list[tuple[dict, Perfil]] = []
    descartes = {"sin_capa_de_texto": 0, "no_pdf": 0, "ilegible": 0}
    for fila in filas_ok(case_dir):
        fuente = case_dir / "00_Input" / fila.get("rel_path", "")
        if fuente.suffix.lower() != ".pdf" or not fuente.exists():
            descartes["no_pdf"] += 1
            continue
        perfil = perfilar(fuente)
        if perfil is None:
            descartes["ilegible"] += 1
            continue
        if perfil.chars_fuente == 0:
            descartes["sin_capa_de_texto"] += 1
            continue
        if perfil.paginas_saltadas:
            candidatos.append((fila, perfil))
    return candidatos, descartes


def _render(nombre: str, candidatos: list[tuple[dict, Perfil]], descartes: dict,
            total: int) -> list[str]:
    lineas = [f"## {nombre} — **{len(candidatos)}** candidatos (de {total} `ok`; "
              f"{descartes['sin_capa_de_texto']} sin capa de texto en origen, "
              f"{descartes['no_pdf']} no-PDF, {descartes['ilegible']} ilegibles)", ""]
    if not candidatos:
        return lineas
    lineas += ["| documento | origen | págs | págs que `--skip-text` salta | firma repetida | chars origen | AcroForm |",
               "|---|---|---|---|---|---|---|"]
    for fila, p in sorted(candidatos, key=lambda x: -len(x[1].paginas_saltadas)):
        pags = ",".join(str(i) for i in p.paginas_saltadas[:12])
        if len(p.paginas_saltadas) > 12:
            pags += ",…"
        lineas.append(f"| {fila['slug']} | {fila.get('rel_path', '')} | {p.n_pags} | "
                      f"{len(p.paginas_saltadas)} ({pags}) | {p.firma_repetida} | "
                      f"{p.chars_fuente} | {'SÍ' if p.acroform else '—'} |")
    return lineas + [""]


@app.command()
def caso(case_id: str):
    """Criba un expediente concreto."""
    case_id = case_locator.resolve_ref(case_id)
    from core.casos.case_locator import buscar
    case_dir = buscar(case_id)
    if case_dir is None or not sm._sala_maquina_dir(case_dir).exists():
        typer.echo(f"[ERROR] {case_id}: la Sala de máquina no se ha ejecutado.", err=True)
        raise typer.Exit(code=1)
    candidatos, descartes = analizar_caso(case_dir)
    total = len(filas_ok(case_dir))
    typer.echo("\n".join(_render(case_id, candidatos, descartes, total)))


@app.command()
def todos(salida: Path = typer.Option(None, help="Escribe el informe Markdown aquí "
                                                "(fuera del repo: puede citar nombres de fichero).")):
    """Criba todos los expedientes que ya tengan Sala de máquina."""
    raiz = settings.casos_root
    casos = [c for ciudad in sorted(p for p in raiz.iterdir()
                                    if p.is_dir() and not p.name.startswith("_"))
             for c in sorted(p for p in ciudad.iterdir() if p.is_dir())
             if sm._sala_maquina_dir(c).exists()]

    lineas = ["# Detector de OCR ciego bajo el sello (MEJORAS #90)", "",
              "Cribado, no veredicto: medir la pérdida real exige re-OCR-izar y comparar.", ""]
    resumen = [f"| caso | `ok` | candidatos |", "|---|---|---|"]
    for case_dir in casos:
        m = _W_RE.search(case_dir.name)
        nombre = m.group(1) if m else case_dir.name
        typer.echo(f"[{nombre}] analizando…", err=True)
        candidatos, descartes = analizar_caso(case_dir)
        total = len(filas_ok(case_dir))
        resumen.append(f"| {nombre} | {total} | **{len(candidatos)}** |")
        lineas += _render(nombre, candidatos, descartes, total)
    lineas[3:3] = ["## Resumen", ""] + resumen + [""]

    texto = "\n".join(lineas) + "\n"
    if salida:
        salida.write_text(texto, encoding="utf-8")
        typer.echo(f"Informe escrito en {salida}")
    else:
        typer.echo(texto)


if __name__ == "__main__":
    app()
