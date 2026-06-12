#!/usr/bin/env bash
# extract_texts.sh
# Extrae texto plano de los PDF y .doc del expediente al directorio _extraidos/.
# Uso: extract_texts.sh <CARPETA_EXPEDIENTE> [DIR_SALIDA]
# Si no se pasa DIR_SALIDA, usa <CARPETA_EXPEDIENTE>/_extraidos/

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Uso: $0 <CARPETA_EXPEDIENTE> [DIR_SALIDA]"
  exit 1
fi

SRC="$1"
DST="${2:-$SRC/_extraidos}"
mkdir -p "$DST"

# Verificar herramientas
command -v pdftotext >/dev/null || { echo "ERROR: pdftotext no disponible"; exit 2; }
command -v soffice   >/dev/null || { echo "WARN: soffice no disponible (los .doc no se convertirán)"; }

# PDFs con capa de texto
find "$SRC" -type f -iname "*.pdf" -print0 | while IFS= read -r -d '' f; do
  base="$(basename "$f" .pdf)"
  out="$DST/$base.txt"
  if [ -f "$out" ]; then
    continue
  fi
  echo "[pdf] $base"
  pdftotext -layout "$f" "$out" 2>/dev/null || true
  # Si el archivo extraído está vacío o casi vacío, intentar OCR si tesseract-spa está disponible
  if [ ! -s "$out" ] || [ "$(wc -c < "$out")" -lt 50 ]; then
    if command -v ocrmypdf >/dev/null && command -v tesseract >/dev/null; then
      if tesseract --list-langs 2>/dev/null | grep -q '^spa$'; then
        echo "  [ocr] $base"
        tmp="$DST/_ocr_$base.pdf"
        ocrmypdf -l spa --skip-text --output-type pdf "$f" "$tmp" 2>/dev/null && \
          pdftotext -layout "$tmp" "$out" 2>/dev/null && \
          rm -f "$tmp"
      else
        echo "  [skip-ocr] modelo spa no instalado para $base"
      fi
    fi
  fi
done

# .doc → .txt vía LibreOffice (si está disponible)
if command -v soffice >/dev/null; then
  find "$SRC" -type f -iname "*.doc" ! -iname "*.docx" -print0 | while IFS= read -r -d '' f; do
    base="$(basename "$f" .doc)"
    out="$DST/$base.txt"
    if [ -f "$out" ]; then
      continue
    fi
    echo "[doc] $base"
    soffice --headless --convert-to txt:Text --outdir "$DST" "$f" >/dev/null 2>&1 || true
  done
fi

# .docx → .txt vía pandoc o soffice
if command -v pandoc >/dev/null; then
  find "$SRC" -type f -iname "*.docx" -print0 | while IFS= read -r -d '' f; do
    base="$(basename "$f" .docx)"
    out="$DST/$base.txt"
    if [ -f "$out" ]; then
      continue
    fi
    echo "[docx] $base"
    pandoc "$f" -t plain -o "$out" 2>/dev/null || true
  done
fi

# Limpiar locks de LibreOffice
find "$DST" -maxdepth 1 -name ".~lock.*" -delete 2>/dev/null || true
find "$DST" -maxdepth 1 -name "*.tmp" -delete 2>/dev/null || true

echo "Listo. Salida en: $DST"
ls -la "$DST"
