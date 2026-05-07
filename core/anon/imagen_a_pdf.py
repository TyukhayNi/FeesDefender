"""Conversión de imágenes a PDF.

Adaptado del original de Expedientes Seguros para uso embebido. Cambios:

- ``sys.exit(1)`` → ``raise ImportError`` (uso embebido no debe matar el
  proceso del orquestador).
- ``ImageOps.exif_transpose`` aplicado tras ``Image.open`` para respetar
  la orientación EXIF de fotos de móvil. Sin esto, una foto JPEG con
  orientación EXIF se incorpora con la orientación nativa del bitmap (no
  la visual) y luego confunde al detector de páginas giradas v3.10 del
  Anonimizador (``anonimizar.py::pagina_girada``).
- DPI parametrizable (default 200, igual que el original).
- Soporte HEIC/HEIF mantenido vía ``pillow-heif``.
"""

from __future__ import annotations

from pathlib import Path


def convertir(
    ruta_imagen: Path | str,
    ruta_pdf: Path | str,
    *,
    dpi: int = 200,
) -> Path:
    """Convierte una imagen (JPG/PNG/TIFF/BMP/HEIC/HEIF) a PDF.

    Args:
        ruta_imagen: imagen de entrada.
        ruta_pdf: PDF destino. Se crea su carpeta si no existe.
        dpi: resolución del PDF resultante. 200 dpi es suficiente para que
            Tesseract lea el OCR posterior con calidad.

    Returns:
        Ruta absoluta del PDF generado.

    Raises:
        ImportError: Pillow o pillow-heif (este último solo para HEIC/HEIF)
            no instalados.
    """
    try:
        from PIL import Image, ImageOps
    except ImportError as e:
        raise ImportError(
            "Pillow no está instalado. Instálalo con `pip install Pillow`."
        ) from e

    ruta_imagen = Path(ruta_imagen)
    ruta_pdf = Path(ruta_pdf)
    ext = ruta_imagen.suffix.lower()

    # Soporte HEIC/HEIF (típico iPhone)
    if ext in ('.heic', '.heif'):
        try:
            from pillow_heif import register_heif_opener
            register_heif_opener()
        except ImportError as e:
            raise ImportError(
                "pillow-heif no está instalado. Necesario para imágenes "
                "HEIC/HEIF. Instálalo con `pip install pillow-heif`."
            ) from e

    img = Image.open(ruta_imagen)

    # Respetar orientación EXIF (clave en fotos hechas con móvil).
    img = ImageOps.exif_transpose(img)

    # Convertir a RGB si es necesario (PNG con transparencia, etc.)
    if img.mode in ('RGBA', 'LA', 'P'):
        fondo = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        fondo.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
        img = fondo
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    # TIFF multipágina y similares
    frames = []
    try:
        while True:
            frames.append(img.copy())
            img.seek(img.tell() + 1)
    except EOFError:
        pass

    ruta_pdf.parent.mkdir(parents=True, exist_ok=True)

    if frames:
        frames[0].save(
            ruta_pdf, 'PDF', resolution=dpi,
            save_all=True, append_images=frames[1:],
        )
    else:
        img.save(ruta_pdf, 'PDF', resolution=dpi)

    return ruta_pdf.resolve()


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print("Uso: python -m core.anon.imagen_a_pdf <imagen> <salida.pdf> [dpi]")
        sys.exit(1)
    dpi = int(sys.argv[3]) if len(sys.argv) > 3 else 200
    out = convertir(sys.argv[1], sys.argv[2], dpi=dpi)
    print(f"OK: {out}")
