"""Reconstrucción de líneas de texto desde los ``LTChar`` de pdfminer.

Helper compartido por ``anonimizar.extraer_texto_pdf`` y
``separar.extraer_primeras_lineas``. Ambos recogían recursivamente los
``LTChar`` de la página (incluido el descenso a ``LTFigure``, necesario para
los PDFs de OCRmyPDF) y los agrupaban en líneas por coordenada Y,
reconstruyendo los espacios entre palabras por salto horizontal. Estaba
duplicado en los dos módulos; se extrae aquí para que las dos rutas no
diverjan.

Las funciones devuelven líneas *crudas* (solo agrupadas y con el texto
reconstruido). Cada caller aplica después sus propios filtros: el
anonimizador filtra por legibilidad y normaliza guiones de OCR; el separador
solo se queda con las primeras N líneas de portada.
"""

from __future__ import annotations

from collections import defaultdict


def recoger_chars(contenedor, chars: list) -> None:
    """Recoge recursivamente todos los ``LTChar`` del contenedor.

    Desciende a cualquier elemento iterable (``LTTextBox``, ``LTTextLine``,
    ``LTFigure``…). El descenso a ``LTFigure`` es imprescindible para los PDFs
    de OCRmyPDF, que incrustan el texto OCR como ``LTChar`` dentro de Form
    XObjects en lugar de en ``LTTextBox`` a nivel de página.
    """
    from pdfminer.layout import LTChar

    for elem in contenedor:
        if isinstance(elem, LTChar):
            chars.append(elem)
        elif hasattr(elem, "__iter__"):
            recoger_chars(elem, chars)


def agrupar_en_lineas(chars, tol_y: float = 3.0, tol_x: float = 8.0):
    """Agrupa ``LTChar`` en líneas y reconstruye el texto de cada una.

    Agrupa por coordenada Y redondeada a ``tol_y`` puntos e inserta un espacio
    cuando el salto horizontal entre dos caracteres supera ``tol_x`` puntos.

    Devuelve una lista de tuplas ``(y, texto)`` ordenadas de arriba a abajo
    (mayor Y primero), con ``texto`` ya recortado (``strip``). NO aplica
    ningún filtro de longitud/legibilidad ni normalización: eso lo decide
    cada caller.
    """
    if not chars:
        return []

    grupos = defaultdict(list)
    for c in chars:
        grupos[round(c.y0 / tol_y) * tol_y].append(c)

    lineas = []
    for y, grupo in sorted(grupos.items(), key=lambda x: -x[0]):
        grupo.sort(key=lambda c: c.x0)
        texto = ""
        x_prev = None
        for c in grupo:
            if x_prev is not None and c.x0 - x_prev > tol_x:
                texto += " "
            texto += c.get_text()
            x_prev = c.x1
        lineas.append((y, texto.strip()))

    return lineas
