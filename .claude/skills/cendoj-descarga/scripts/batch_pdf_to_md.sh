#!/usr/bin/env bash
# batch_pdf_to_md.sh — Conversión por lotes de PDFs de CENDOJ a Markdown.
#
# Bundleado en cendoj-descarga (Paso 8-bis). Para cada PDF del directorio de
# entrada extrae el texto con `pdftotext -layout` y lo parsea a `.md` con el
# helper `parse_pdf_to_md.py` (mismo directorio). El `.txt` intermedio se borra.
#
# Uso:  bash batch_pdf_to_md.sh <dir_pdfs> [<dir_salida>]
#       (dir_salida por defecto = dir_pdfs)

set -euo pipefail

PDF_DIR="${1:?Uso: batch_pdf_to_md.sh <dir_pdfs> [<dir_salida>]}"
OUTPUT_DIR="${2:-$PDF_DIR}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$OUTPUT_DIR"
shopt -s nullglob

n_ok=0
n_err=0
for pdf in "$PDF_DIR"/*.pdf; do
  base="$(basename "${pdf%.pdf}")"
  txt="${pdf%.pdf}.txt"
  md="${OUTPUT_DIR}/${base}.md"

  echo "📄 $base"
  if ! pdftotext -layout "$pdf" "$txt" 2>/dev/null; then
    echo "   ⚠️  no se pudo extraer texto (¿pdftotext instalado?)"
    n_err=$((n_err + 1))
    continue
  fi

  if python3 "$SCRIPT_DIR/parse_pdf_to_md.py" "$txt" "$md"; then
    n_ok=$((n_ok + 1))
  else
    echo "   ⚠️  fallo al parsear a MD"
    n_err=$((n_err + 1))
  fi
  rm -f "$txt"
done

echo "✅ Conversión completa: $n_ok ok, $n_err con incidencias. MDs en: $OUTPUT_DIR"
