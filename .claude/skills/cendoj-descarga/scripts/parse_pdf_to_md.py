# -*- coding: utf-8 -*-
"""Convierte el volcado de texto de una sentencia del CENDOJ a Markdown legible.

Bundleado en ``cendoj-descarga`` (Paso 8-bis). Solo stdlib, para poder ejecutarse
dentro de un ``.skill`` empaquetado. La entrada es el ``.txt`` que produce
``pdftotext -layout sentencia.pdf sentencia.txt``; la salida es un ``.md`` con
frontmatter YAML (ROJ, ECLI, tribunal, fecha, ponente) y las secciones Hechos,
Ratio decidendi y Fallo separadas por heurística sobre los encabezados estándar
del CGPJ.

Es *best-effort*: ante cualquier duda prevalece el PDF oficial. Si el ``.txt``
sale vacío o ilegible (encoding CIDFont propio de CENDOJ), el ``.md`` lo declara
y recomienda OCR en lugar de inventar contenido.

Uso:
  python parse_pdf_to_md.py <entrada.txt> <salida.md>
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# --- Extracción de metadatos de cabecera ------------------------------------

# Campos de la ficha de cabecera de CENDOJ. El valor se captura hasta fin de línea.
_CAMPOS = {
    "roj": r"Roj\s*:\s*(.+?)(?:\s*-\s*ECLI|\s*$)",
    "ecli": r"ECLI\s*:\s*(\S+)",
    "id_cendoj": r"Id\s+Cendoj\s*:\s*(\S+)",
    "organo": r"(?:Órgano|Organo)\s*:\s*(.+)",
    "sede": r"Sede\s*:\s*(.+)",
    "seccion": r"(?:Sección|Seccion)\s*:\s*(.+)",
    "fecha": r"Fecha\s*:\s*(.+)",
    "n_recurso": r"N[ºo°]?\s*de\s*Recurso\s*:\s*(.+)",
    "n_resolucion": r"N[ºo°]?\s*de\s*Resoluci[oó]n\s*:\s*(.+)",
    "ponente": r"Ponente\s*:\s*(.+)",
    "tipo": r"Tipo\s+de\s+Resoluci[oó]n\s*:\s*(.+)",
}


def _campo(texto: str, patron: str) -> str:
    m = re.search(patron, texto, flags=re.IGNORECASE)
    return m.group(1).strip() if m else ""


def extraer_metadatos(texto: str) -> dict[str, str]:
    """Lee la ficha de cabecera (primeras líneas del PDF de CENDOJ)."""
    cabecera = "\n".join(texto.splitlines()[:40])
    return {clave: _campo(cabecera, patron) for clave, patron in _CAMPOS.items()}


# --- Troceado en secciones ---------------------------------------------------

# Encabezados habituales, en orden de aparición. Cada sección va desde su marca
# hasta la marca de la siguiente.
_MARCAS = [
    ("hechos", r"ANTECEDENTES\s+DE\s+HECHO|HECHOS\s+PROBADOS|^\s*HECHOS\s*$|SUPUESTO\s+DE\s+HECHO"),
    ("ratio", r"(?:FUNDAMENTOS|RAZONAMIENTOS)\s+(?:DE\s+DERECHO|JUR[IÍ]DICOS)|FUNDAMENTACI[OÓ]N\s+JUR[IÍ]DICA"),
    ("fallo", r"^\s*(?:F\s*A\s*L\s*L\s*O|FALLO|FALLAMOS|PARTE\s+DISPOSITIVA|DISPONGO|ACUERDO)\s*$"),
]


def _buscar(texto: str, patron: str, desde: int = 0) -> int:
    m = re.search(patron, texto[desde:], flags=re.IGNORECASE | re.MULTILINE)
    return desde + m.start() if m else -1


def trocear_secciones(texto: str) -> dict[str, str]:
    """Devuelve {hechos, ratio, fallo}; cadena vacía si no se localiza la marca."""
    posiciones = []
    cursor = 0
    for clave, patron in _MARCAS:
        pos = _buscar(texto, patron, cursor)
        posiciones.append((clave, pos))
        if pos != -1:
            cursor = pos + 1
    # Calcular el corte de cada sección hasta el inicio de la siguiente localizada.
    secciones = {clave: "" for clave, _ in _MARCAS}
    encontradas = [(c, p) for c, p in posiciones if p != -1]
    for i, (clave, ini) in enumerate(encontradas):
        fin = encontradas[i + 1][1] if i + 1 < len(encontradas) else len(texto)
        secciones[clave] = texto[ini:fin].strip()
    return secciones


# --- Diagnóstico de encoding -------------------------------------------------

def texto_ilegible(texto: str) -> bool:
    """Heurística para el encoding CIDFont de CENDOJ: texto vacío o casi sin letras."""
    limpio = texto.strip()
    if len(limpio) < 200:
        return True
    letras = sum(1 for c in limpio if c.isalpha())
    return letras / max(len(limpio), 1) < 0.45


# --- Render ------------------------------------------------------------------

def _yaml_seguro(valor: str) -> str:
    """Escapa el valor para frontmatter YAML (entrecomilla si hay caracteres delicados)."""
    if valor and re.search(r'[:#\[\]{}",&*?|<>=!%@`]', valor):
        return '"' + valor.replace('"', '\\"') + '"'
    return valor


def construir_md(meta: dict[str, str], secciones: dict[str, str], aviso_encoding: bool) -> str:
    titulo = " — ".join(p for p in (meta.get("roj"), meta.get("organo")) if p) or "Resolución CENDOJ"
    fm = "\n".join(
        f"{k}: {_yaml_seguro(meta.get(k, ''))}"
        for k in ("roj", "ecli", "id_cendoj", "organo", "sede", "seccion", "fecha", "n_recurso", "n_resolucion", "ponente", "tipo")
    )
    partes = [
        "---", fm, "---", "",
        f"# {titulo}", "",
        "## Metadatos",
        f"- **ROJ:** {meta.get('roj') or '—'}",
        f"- **ECLI:** {meta.get('ecli') or '—'}",
        f"- **Órgano:** {meta.get('organo') or '—'}",
        f"- **Sede / Sección:** {meta.get('sede') or '—'} / {meta.get('seccion') or '—'}",
        f"- **Fecha:** {meta.get('fecha') or '—'}",
        f"- **Nº Resolución / Recurso:** {meta.get('n_resolucion') or '—'} / {meta.get('n_recurso') or '—'}",
        f"- **Ponente:** {meta.get('ponente') or '—'}",
        "",
    ]
    if aviso_encoding:
        partes += [
            "> ⚠️ **Texto no extraíble (encoding CIDFont).** El cuerpo no se ha podido",
            "> volcar de forma fiable. Identidad verificada por metadatos; para los",
            "> fundamentos, consultar el PDF oficial o aplicar OCR (`pdftoppm` + Tesseract).",
            "",
        ]
    else:
        partes += [
            "## Hechos", (secciones.get("hechos") or "_No localizado en el texto extraído._"), "",
            "## Ratio decidendi", (secciones.get("ratio") or "_No localizado en el texto extraído._"), "",
            "## Fallo", (secciones.get("fallo") or "_No localizado en el texto extraído._"), "",
        ]
    partes += [
        "---",
        "*Conversión automática PDF → Markdown (best-effort). Verificar el contenido en el PDF oficial si hay dudas.*",
        "",
    ]
    return "\n".join(partes)


def parse_pdf_to_md(txt_path: str, md_path: str) -> None:
    texto = Path(txt_path).read_text(encoding="utf-8", errors="replace")
    meta = extraer_metadatos(texto)
    aviso = texto_ilegible(texto)
    secciones = {} if aviso else trocear_secciones(texto)
    md = construir_md(meta, secciones, aviso)
    Path(md_path).write_text(md, encoding="utf-8")
    estado = "aviso de encoding" if aviso else "ok"
    print(f"[parse_pdf_to_md] {md_path} ({estado})")


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("Uso: python parse_pdf_to_md.py <entrada.txt> <salida.md>", file=sys.stderr)
        return 2
    entrada = argv[1]
    if not Path(entrada).is_file():
        print(f"[parse_pdf_to_md] no existe la entrada: {entrada}", file=sys.stderr)
        return 1
    parse_pdf_to_md(entrada, argv[2])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
