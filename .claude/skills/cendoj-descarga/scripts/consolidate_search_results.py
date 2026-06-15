# -*- coding: utf-8 -*-
"""Genera el índice consolidado de una búsqueda en CENDOJ.

Bundleado en ``cendoj-descarga`` (Paso 9). Recorre los PDFs de un directorio,
extrae sus metadatos oficiales (con ``pdftotext`` sobre la primera página) y
escribe un único Markdown ``00_INDICE_busqueda-CENDOJ_<tema>_<fecha>.md`` con
tabla resumen, andamiaje de clasificación por uso y tabla de verificación.

La clasificación (favorable / doctrinal / adversa / descartar) NO la decide el
script: deja todos los documentos bajo «Sin clasificar» para que el letrado los
mueva. Solo stdlib + ``pdftotext`` (poppler) en el ``PATH``.

Uso:
  python consolidate_search_results.py --pdf-dir <dir> --output-file <salida.md>
                                       [--tema "..."] [--fecha AAAA-MM-DD]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

# Reutiliza la extracción de cabecera del helper hermano (mismo directorio).
try:
    from parse_pdf_to_md import extraer_metadatos
except ImportError:  # pragma: no cover - solo si se ejecuta fuera de scripts/
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from parse_pdf_to_md import extraer_metadatos


def _primera_pagina(pdf_path: Path) -> str:
    """Texto de la primera página vía pdftotext. Cadena vacía si falla o no está."""
    try:
        res = subprocess.run(
            ["pdftotext", "-layout", "-l", "1", str(pdf_path), "-"],
            capture_output=True, encoding="utf-8", errors="replace",
        )
        return res.stdout or ""
    except (FileNotFoundError, OSError):
        return ""


def _estado_subida(size_kb: float) -> str:
    """Mapea el tamaño al modo de subida a Drive documentado en el Paso 7."""
    if size_kb < 150:
        return "✅ auto"
    if size_kb < 300:
        return "🟡 hybrid"
    return "⚠️ manual"


def recopilar(pdf_dir: Path) -> list[dict]:
    documentos = []
    for pdf in sorted(pdf_dir.glob("*.pdf")):
        size_kb = pdf.stat().st_size / 1024
        meta = extraer_metadatos(_primera_pagina(pdf))
        md_hermano = pdf.with_suffix(".md").name
        documentos.append({
            "pdf": pdf.name,
            "md": md_hermano if (pdf_dir / md_hermano).exists() else "",
            "roj": meta.get("roj") or "—",
            "ecli": meta.get("ecli") or "—",
            "tribunal": " ".join(p for p in (meta.get("organo"), meta.get("sede")) if p) or "—",
            "seccion": meta.get("seccion") or "—",
            "fecha": meta.get("fecha") or "—",
            "ponente": meta.get("ponente") or "—",
            "size_kb": round(size_kb),
            "estado": _estado_subida(size_kb),
            "ilegible": not bool((meta.get("roj") or meta.get("ecli"))),
        })
    return documentos


def _fila_resumen(i: int, d: dict) -> str:
    trib = d["tribunal"] + (f", Sec. {d['seccion']}" if d["seccion"] != "—" else "")
    return f"| {i} | {trib} | {d['fecha']} | {d['roj']} | {d['ecli']} | {d['ponente']} | {d['size_kb']} KB | {d['estado']} |"


def _fila_verif(i: int, d: dict) -> str:
    meta_ok = "✅" if not d["ilegible"] else "⚠️"
    enc = "⚠️ revisar (CIDFont?)" if d["ilegible"] else "OK"
    return f"| {i}. {d['roj']} | {meta_ok} | {enc} | _pendiente_ | _pendiente_ | — |"


def _enlace(d: dict) -> str:
    pdf = f"[PDF](./{d['pdf']})"
    md = f" | [MD](./{d['md']})" if d["md"] else ""
    return f"- **{d['roj']}** ({d['fecha']}) — {pdf}{md}"


def construir_md(documentos: list[dict], tema: str, fecha: str) -> str:
    n = len(documentos)
    con_md = sum(1 for d in documentos if d["md"])
    L = [
        f"# Búsqueda CENDOJ — {tema}",
        f"**Fecha búsqueda:** {fecha}",
        "**Órgano/Sección:** _completar_ | **Período:** _completar_ | **Criterios:** _completar_",
        "",
        "## Resumen ejecutivo",
        f"- Documentos localizados: {n}",
        f"- Descargados: {n}",
        f"- En conversión MD: {con_md}",
        "",
        "## Tabla resumen",
        "| Nº | Tribunal | Fecha | ROJ | ECLI | Ponente | Tamaño | Subida |",
        "|----|----------|-------|-----|------|---------|--------|--------|",
    ]
    L += [_fila_resumen(i, d) for i, d in enumerate(documentos, 1)]
    L += [
        "",
        "## Clasificación por uso",
        "_El letrado mueve cada documento a la categoría que corresponda tras leer el PDF._",
        "",
        "### ✅ Favorable",
        "_(ninguno asignado)_",
        "",
        "### 📚 Doctrinal",
        "_(ninguno asignado)_",
        "",
        "### ⚠️ Adversa",
        "_(ninguno asignado)_",
        "",
        "### ❌ Descartar",
        "_(ninguno asignado)_",
        "",
        "### ⏳ Sin clasificar",
    ]
    L += [_enlace(d) for d in documentos]
    L += [
        "",
        "## Verificación de contenido",
        "| Documento | Metadatos | Encoding | Materia | Vigencia | Notas |",
        "|-----------|-----------|----------|---------|----------|-------|",
    ]
    L += [_fila_verif(i, d) for i, d in enumerate(documentos, 1)]
    L += [
        "",
        "## Referencias base privada vs CENDOJ",
        "| Referencia privada | ROJ CENDOJ | ECLI | Notas |",
        "|--------------------|-----------|------|-------|",
        "| _completar_ | — | — | — |",
        "",
    ]
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Consolida una búsqueda CENDOJ en un índice Markdown.")
    p.add_argument("--pdf-dir", required=True)
    p.add_argument("--output-file", required=True)
    p.add_argument("--tema", default="(sin tema)")
    p.add_argument("--fecha", default="(sin fecha)")
    # Aceptado por compatibilidad con la invocación documentada; el script no sube a Drive.
    p.add_argument("--case-folder-id", default=None)
    args = p.parse_args(argv)

    pdf_dir = Path(args.pdf_dir)
    if not pdf_dir.is_dir():
        print(f"[consolidate] no es un directorio: {pdf_dir}", file=sys.stderr)
        return 1
    documentos = recopilar(pdf_dir)
    if not documentos:
        print(f"[consolidate] sin PDFs en {pdf_dir}", file=sys.stderr)
    md = construir_md(documentos, args.tema, args.fecha)
    Path(args.output_file).write_text(md, encoding="utf-8")
    print(f"[consolidate] {args.output_file} ({len(documentos)} documentos)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
