"""
Separador de PDFs de expedientes judiciales v1.0
=================================================
Divide un PDF de expediente judicial en documentos individuales,
detectando automáticamente los límites entre documentos por marcadores
textuales y generando un PDF por tipo documental.

Uso:
    python separar.py "ruta/al/expediente.pdf"

Genera una subcarpeta con el mismo nombre que el PDF conteniendo
un PDF por cada documento detectado, nombrado con su tipo y número.

Diseñado para expedientes del Tribunal de Instancia de Barcelona
y juzgados civiles catalanes, con soporte para documentos en
español, catalán e inglés (documentación adjunta internacional).
"""
# -*- coding: utf-8 -*-
# Nota: el wrap UTF-8 que el original aplicaba a nivel de import rompía
# Streamlit al importar el módulo. Ahora vive solo dentro del bloque
# ``if __name__ == '__main__':`` al final del fichero.

import sys
import re
import json
import logging
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Callable

from core.anon.exceptions import PDFVacioError


# ══════════════════════════════════════════════════════════════════════════════
# TIPOS DE DOCUMENTO Y SUS MARCADORES
# ══════════════════════════════════════════════════════════════════════════════
#
# Cada entrada define:
#   - tipo:      nombre del tipo documental (usado en el nombre del archivo)
#   - prioridad: si varias reglas coinciden, gana la de mayor prioridad
#   - marcadores: palabras/frases que, en las primeras líneas de una página,
#                 indican que ESA página es el inicio de un nuevo documento
#   - exige_inicio: si True, el marcador debe estar en las primeras 3 líneas
#                   (portada del documento). Si False, basta con que aparezca
#                   en cualquier lugar de las primeras 5 líneas.

TIPOS_DOCUMENTO = [
    {
        "tipo": "CEDULA_EMPLAZAMIENTO",
        "prioridad": 10,
        "marcadores": [
            "CÉDULA DE EMPLAZAMIENTO", "CEDULA DE EMPLAZAMIENTO",
            "CÉDULA DE NOTIFICACIÓN", "CEDULA DE NOTIFICACION",
        ],
        "exige_inicio": True,
    },
    {
        "tipo": "SENTENCIA",
        "prioridad": 11,
        "marcadores": [
            # Cabeceras oficiales
            "SENTENCIA Nº", "SENTENCIA N.", "SENTENCIA NUM",
            "S E N T E N C I A",  # espaciado tipico
            "EN NOMBRE DEL REY", "EN NOM DEL REI",
            "EN NOMBRE DE S.M.",
            # Paginas internas tipicas de sentencia (dan la misma señal)
            "FUNDAMENTOS DE DERECHO", "FONAMENTS DE DRET",
            "ANTECEDENTES DE HECHO", "ANTECEDENTS DE FET",
            "PARTE DISPOSITIVA",
            "F A L L O", "FALLAMOS", "DICTO LA SIGUIENTE SENTENCIA",
            "HA DICTADO LA SIGUIENTE SENTENCIA",
            "PRONUNCIO LA SIGUIENTE SENTENCIA",
            "VISTOS PARA SENTENCIA",
        ],
        "exige_inicio": False,
    },
    {
        "tipo": "DECRETO",
        "prioridad": 10,
        "marcadores": ["DECRETO", "DILIGENCIA DE ORDENACIÓN", "DILIGENCIA DE ORDENACION"],
        "exige_inicio": True,
    },
    {
        "tipo": "AUTO",
        "prioridad": 10,
        # AUTO solo matchea con formatos especificos de cabecera oficial,
        # para evitar falsos positivos con "autos" (plural) en texto corrido
        # (ej: "quedaron los autos vistos para sentencia").
        "marcadores": [
            "A U T O",  # espaciado oficial
            "AUTO Nº", "AUTO N.", "AUTO NUM",
            "AUTO DE ADMISIÓN", "AUTO DE ADMISION",
            "AUTO DE ACLARACIÓN", "AUTO DE ACLARACION",
            "AUTO DE MEDIDAS",
            "PROVIDENCIA",
        ],
        "exige_inicio": True,
    },
    {
        "tipo": "CONTESTACION",
        "prioridad": 9,
        "marcadores": [
            "CONTESTACIÓN A LA DEMANDA", "CONTESTACION A LA DEMANDA",
            "CONTESTO A LA DEMANDA", "CONTESTO LA DEMANDA",
            "CONTESTANDO A LA DEMANDA",
        ],
        "exige_inicio": True,  # solo en cabecera, no en texto corrido de sentencia
    },
    {
        "tipo": "OPOSICION",
        "prioridad": 9,
        "marcadores": [
            "FORMULO OPOSICIÓN", "FORMULO OPOSICION",
            "OPOSICIÓN AL JUICIO", "OPOSICION AL JUICIO",
            "ME OPONGO A LA DEMANDA", "ME OPONGO A LA RECLAMACION",
        ],
        "exige_inicio": True,
    },
    {
        "tipo": "DEMANDA",
        "prioridad": 9,
        "marcadores": [
            # Encabezamientos directos al juzgado (solo en escritos de parte)
            "A LA SECCIÓN CIVIL", "A LA SECCION CIVIL",
            "ALA SECCION", "AL JUZGADO DE PRIMERA INSTANCIA",
            "AL JUZGADO DE INSTANCIA", "AL TRIBUNAL DE INSTANCIA",
            # Marcadores inequívocos de escrito de demanda
            "DEMANDA DE JUICIO ORDINARIO", "DEMANDA DE JUICIO VERBAL",
            "FORMULO DEMANDA", "PRESENTE DEMANDA",
            # Suplico / Otrosi (solo en escritos de parte)
            "SUPLICO AL JUZGADO", "SUPLICO AL TRIBUNAL",
            "OTROSI DIGO",
        ],
        "exige_inicio": False,
    },
    {
        "tipo": "DOC_PODER_NOTARIAL",
        "prioridad": 8,
        "marcadores": [
            "ESCRITURA DE PODER", "PODER NOTARIAL", "NOTARIO",
            "COPIA SIMPLE", "ES COPIA", "ACTA NOTARIAL",
        ],
        "exige_inicio": False,
    },
    {
        "tipo": "DOC_CONTRATO",
        "prioridad": 7,
        "marcadores": [
            "ENCARGO DE PRESTACION DE SERVICIOS", "ENCARGO DE PRESTACIÓN",
            "CONTRATO DE ARRENDAMIENTO", "CONTRACTE DE LLOGUER",
            "CONTRATO DE COMPRAVENTA", "CONTRATO DE SERVICIOS",
            "OFERTA DE ARRENDAMIENTO", "RESIDENTIAL LEASING AGREEMENT",
            "LEASING AGREEMENT",
        ],
        "exige_inicio": True,  # solo cuando es portada; evita matches en menciones
    },
    {
        "tipo": "DOC_FACTURA",
        "prioridad": 7,
        "marcadores": ["FACTURA", "INVOICE", "FACTURA A/R", "FACTURA RECTIFICATIVA"],
        "exige_inicio": True,
    },
    {
        "tipo": "DOC_EMAIL",
        "prioridad": 6,
        "marcadores": ["GMAIL", "OUTLOOK", "YOUR PROPERTY SEARCH", "RESERVA -"],
        "exige_inicio": False,
    },
    {
        "tipo": "DOC_EXTRACTO_BANCARIO",
        "prioridad": 6,
        "marcadores": [
            "ACCOUNT ACTIVITY", "ACTIVIDAD DE LA CUENTA",
            "STATEMENT", "EXTRACTO", "CAPITAL ONE", "VENTURE X",
            "TRANSFER CONFIRMATION", "TRANSFER DETAILS",
            "BANK STATEMENT",
        ],
        "exige_inicio": False,
    },
    {
        "tipo": "DOC_INFORME",
        "prioridad": 5,
        "marcadores": ["INFORME", "DICTAMEN", "PERITAJE"],
        "exige_inicio": True,
    },
    {
        "tipo": "DOC_TRADUCCION",
        "prioridad": 4,
        "marcadores": ["DEEPL", "TRADUCCIÓN", "TRADUCCION", "TRANSLATION"],
        "exige_inicio": False,
    },
    {
        "tipo": "DOC_ANEXO",
        "prioridad": 3,
        "marcadores": ["ANNEX", "ANEXO", "APPENDIX"],
        "exige_inicio": False,
    },
    {
        "tipo": "DOC_REGISTRO_AUDITORIA",
        "prioridad": 5,
        "marcadores": ["REGISTRO DE AUDITORIA", "REGISTRO DE AUDITORÍA", "AUDIT TRAIL"],
        "exige_inicio": False,
    },
]

# Patrón para detectar numeración de documentos ("DOC 1", "DOC. 2", "Documento nº 3")
PATRON_NUM_DOC = re.compile(
    r'\bDOC(?:UMENTO)?\s*[NnºN°\.]*\s*(\d+)\b',
    re.IGNORECASE
)

# FeesDefender 2026-07-22: fallback ADITIVO — no modifica PATRON_NUM_DOC ni el
# bucle que lo usa; core/anon/ es congelado (CLAUDE.md), así que esto se añade
# al lado, no se toca lo existente. Cubre portadas tipo "Documento anexo n.º 2"
# donde una palabra calificadora ("anexo", "contrato"...) separa el marcador
# DOC del número — PATRON_NUM_DOC nunca las matchea porque su clase de
# caracteres solo tolera símbolos (Nº/n°/.) entre DOC y el dígito, no palabras.
# Bug real: W-02ZIIF (2026-07-22) — un PDF judicial reordenado colapsó 10
# documentos en 1 porque num_doc quedaba siempre None en estas portadas y la
# absorción de TIPOS_SUPER_ABSORBENTES se comía cada "Documento anexo n.º N".
_CALIFICADORES_PORTADA = r'(?:ANEXO|ANNEX|APPENDIX|CONTRATO|FACTURA|INFORME|TRADUCCI[OÓ]N)'
PATRON_NUM_DOC_FRAGMENTADO = re.compile(
    rf'\bDOC(?:UMENTO)?\b\s*(?:{_CALIFICADORES_PORTADA}\s*)?[NnºN°\.]*\s*(\d+)\b',
    re.IGNORECASE
)


# ══════════════════════════════════════════════════════════════════════════════
# EXTRACCIÓN DE TEXTO
# ══════════════════════════════════════════════════════════════════════════════

def extraer_primeras_lineas(pagina, n=5, tol_y=3.0, tol_x=8.0):
    """Extrae las primeras N líneas de texto de una página via LTChar.

    La recogida de ``LTChar`` y la agrupación en líneas viven en
    ``core.anon.pdf_lineas`` (compartido con ``anonimizar.extraer_texto_pdf``).
    Aquí solo nos quedamos con las primeras N líneas de portada de longitud
    suficiente (>= 3 caracteres) para alimentar a ``detectar_tipo``.
    """
    from core.anon.pdf_lineas import agrupar_en_lineas, recoger_chars

    chars: list = []
    recoger_chars(pagina, chars)
    if not chars:
        return []

    lineas = []
    for _y, texto in agrupar_en_lineas(chars, tol_y, tol_x):
        if len(texto) >= 3:
            lineas.append(texto)
        if len(lineas) >= n:
            break

    return lineas


# ══════════════════════════════════════════════════════════════════════════════
# DETECCIÓN DE TIPO DE DOCUMENTO
# ══════════════════════════════════════════════════════════════════════════════

def detectar_tipo(lineas, tipos_extra=None):
    """
    Determina el tipo documental de una página a partir de sus primeras líneas.
    Devuelve (tipo, prioridad, num_doc) o (None, 0, None).
    """
    if not lineas:
        return None, 0, None

    texto_completo = " ".join(lineas).upper()
    texto_inicio   = " ".join(lineas[:3]).upper()
    # Para exige_inicio: texto que solo contiene las lineas cortas (<= 8 palabras)
    # de las primeras 3. Evita matches en texto corrido donde el marcador aparece
    # embebido en parrafos largos.
    texto_inicio_titulo = " ".join(
        l for l in lineas[:3] if len(l.split()) <= 8
    ).upper()

    # Buscar número de documento explícito solo en líneas cortas de portada.
    # Una portada tiene la forma "DOC 1", "DOC 5  34", "DOC 6  36".
    # Las citas dentro del texto ("Se acompaña como Documento n° 5...") están
    # en líneas largas (>6 palabras) y no son portadas.
    num_doc = None
    for linea_portada in lineas[:3]:
        palabras_linea = linea_portada.strip().split()
        if len(palabras_linea) <= 5:  # línea corta → posible portada
            m = PATRON_NUM_DOC.search(linea_portada)
            if m:
                num_doc = int(m.group(1))
                break

    if num_doc is None:
        # Fallback: el marcador y el número pueden quedar repartidos en líneas
        # reconstruidas distintas (portada a dos líneas, o interlineado
        # irregular de origen que fragmenta lo que visualmente es una sola
        # línea). Unimos las líneas cortas de portada y probamos el patrón
        # tolerante a calificador. Solo se activa si el bucle de arriba
        # (comportamiento original, intacto) no encontró nada.
        lineas_cortas_portada = [
            l for l in lineas[:3] if len(l.strip().split()) <= 5
        ]
        if lineas_cortas_portada:
            m = PATRON_NUM_DOC_FRAGMENTADO.search(" ".join(lineas_cortas_portada))
            if m:
                num_doc = int(m.group(1))

    mejor_tipo = None
    mejor_prio = 0

    # Tipos donde el marcador solo vale si aparece como titulo (linea corta <=8 palabras)
    # para evitar que menciones en texto corrido de sentencias o demandas disparen el tipo.
    TIPOS_SOLO_TITULO = {
        'DOC_CONTRATO', 'DOC_FACTURA', 'DOC_INFORME', 'DOC_ANEXO',
        'DOC_TRADUCCION',
    }

    for defn in TIPOS_DOCUMENTO + (tipos_extra or []):
        if defn["tipo"] in TIPOS_SOLO_TITULO:
            texto_buscar = texto_inicio_titulo
        elif defn["exige_inicio"]:
            texto_buscar = texto_inicio
        else:
            texto_buscar = texto_completo
        for marcador in defn["marcadores"]:
            if marcador.upper() in texto_buscar:
                if defn["prioridad"] > mejor_prio:
                    mejor_tipo = defn["tipo"]
                    mejor_prio = defn["prioridad"]
                break

    return mejor_tipo, mejor_prio, num_doc


# ══════════════════════════════════════════════════════════════════════════════
# DETECCIÓN DE LÍMITES ENTRE DOCUMENTOS
# ══════════════════════════════════════════════════════════════════════════════

# Tipos que se agrupan en bloque cuando aparecen en páginas consecutivas
# (una tarjeta de crédito puede tener 50 páginas, son un solo documento)
TIPOS_AGRUPABLES = {
    'DOC_EXTRACTO_BANCARIO', 'DOC_EMAIL', 'DOC_TRADUCCION',
    'DOC_PODER_NOTARIAL', 'DOC_INFORME', 'DOC_REGISTRO_AUDITORIA',
    'DOC_ANEXO', 'DEMANDA',
}

# Tipos que, cuando no tienen número de documento explícito (num_doc=None),
# se consideran parte del documento anterior en lugar de iniciar uno nuevo.
# Esto evita que menciones a "contrato" o "factura" dentro de la demanda
# la fragmenten en múltiples segmentos.
TIPOS_ABSORBE_SIN_NUMERO = {
    'DOC_CONTRATO', 'DOC_FACTURA', 'DOC_EMAIL', 'DOC_ANEXO', 'DOC_TRADUCCION',
}

# Tipos que, cuando están ACTIVOS como segmento actual, absorben cualquier
# marcador sin número de documento explícito. Se aplica a "escritos/resoluciones
# que se procesan como documento único" — la demanda absorbe los paragraphs de
# hechos que mencionan "contrato", "notario"; una sentencia absorbe las menciones
# dentro del fallo o de los antecedentes; etc.
TIPOS_SUPER_ABSORBENTES = {
    'DEMANDA', 'SENTENCIA', 'CONTESTACION', 'OPOSICION',
}

# Número máximo de páginas sin marcador antes de cerrar un segmento agrupable
MAX_PAGINAS_SIN_MARCADOR = 60


def detectar_segmentos(ruta_pdf, log, *, on_page: "Callable[[int, int], None] | None" = None, tipos_extra=None):
    """
    Recorre el PDF página a página y detecta dónde empieza cada documento.

    v1.1: Agrupación inteligente — páginas consecutivas del mismo tipo
    se fusionan en un único segmento. Esto evita que un extracto bancario
    de 50 páginas genere 50 archivos distintos.

    Lógica de inicio de nuevo segmento:
    1. Se detecta un tipo documental distinto al actual → nuevo segmento
    2. Se detecta el mismo tipo pero con número de documento diferente → nuevo
    3. Se detecta el mismo tipo agrupable → continuar el segmento actual
    4. Página sin marcador → continuar el segmento actual (hasta MAX páginas)

    FeesDefender 2026-05-07: añadido callback ``on_page(num_pag, total_pag)``
    opcional para reportar progreso en UI sin acoplar a Streamlit.
    """
    from contextlib import closing

    from pdfminer.high_level import extract_pages
    from pypdf import PdfReader

    log.info(f"Analizando estructura: {ruta_pdf.name}")

    # pypdf lee el PDF a memoria, pero usamos el context manager para cerrar
    # de forma explícita y no depender del GC (en Windows un handle abierto
    # bloquea el origen y rompe cualquier mover/borrar posterior).
    with PdfReader(str(ruta_pdf)) as reader:
        total_pag = len(reader.pages)

    # Primera pasada: etiquetar cada página.
    # ``extract_pages`` es un generador que mantiene el PDF ABIERTO hasta
    # agotarlo; si el bucle se interrumpe por una excepción, en Windows el
    # origen queda bloqueado. ``closing`` cierra el generador (y su handle)
    # también en la ruta de error.
    etiquetas = []  # [(num_pag, tipo, num_doc, lineas)]
    with closing(extract_pages(str(ruta_pdf))) as paginas:
        for num_pag, pagina in enumerate(paginas, 1):
            lineas = extraer_primeras_lineas(pagina, n=5)
            tipo, prio, num_doc = detectar_tipo(lineas, tipos_extra=tipos_extra)
            etiquetas.append((num_pag, tipo, num_doc, lineas))
            if on_page is not None:
                on_page(num_pag, total_pag)

    # Segunda pasada: construir segmentos agrupando páginas consecutivas
    segmentos = []
    seg_actual = None

    for num_pag, tipo, num_doc, lineas in etiquetas:

        if tipo is None:
            # Página sin marcador: continuar segmento actual si existe
            if seg_actual is not None:
                seg_actual["paginas_sin_marcador"] += 1
                if seg_actual["paginas_sin_marcador"] > MAX_PAGINAS_SIN_MARCADOR:
                    # Demasiadas páginas sin marcador → cerrar
                    seg_actual["pagina_fin"] = num_pag - 1
                    segmentos.append(seg_actual)
                    seg_actual = None
            continue

        # Hay marcador: decidir si abrir nuevo segmento o continuar
        abrir_nuevo = True

        if seg_actual is not None:
            mismo_tipo   = (tipo == seg_actual["tipo"])
            agrupable    = (tipo in TIPOS_AGRUPABLES)
            sin_numero   = (num_doc is None)
            absorbe      = (tipo in TIPOS_ABSORBE_SIN_NUMERO)
            num_distinto = (num_doc is not None and
                           seg_actual["num_doc"] is not None and
                           num_doc != seg_actual["num_doc"])

            if mismo_tipo and agrupable and not num_distinto:
                # Misma categoría agrupable → continuar
                seg_actual["paginas_sin_marcador"] = 0
                abrir_nuevo = False
            elif sin_numero and absorbe:
                # Tipo absorbible sin número explícito → continuar segmento actual
                # (evita fragmentar la demanda cuando menciona "contrato"/"factura")
                seg_actual["paginas_sin_marcador"] = 0
                abrir_nuevo = False
            elif seg_actual["tipo"] in TIPOS_SUPER_ABSORBENTES and sin_numero:
                # DEMANDA (super-absorbente) activa: cualquier marcador nuevo
                # SIN num_doc explícito en portada se considera parte de los
                # hechos. Evita que párrafos numerados (hechos 43, 73, 141...)
                # o menciones a "notario", "informe", "auto" fragmenten la
                # demanda en múltiples documentos.
                seg_actual["paginas_sin_marcador"] = 0
                abrir_nuevo = False

        if abrir_nuevo:
            if seg_actual is not None:
                seg_actual["pagina_fin"] = num_pag - 1
                segmentos.append(seg_actual)
                log.info(f"  Pág {seg_actual['pagina_inicio']:3d}-{seg_actual['pagina_fin']:3d}: "
                         f"[{seg_actual['tipo']}] {seg_actual['lineas_inicio'][0][:50]}")

            seg_actual = {
                "tipo":                tipo,
                "num_doc":             num_doc,
                "pagina_inicio":       num_pag,
                "pagina_fin":          None,
                "lineas_inicio":       lineas[:2],
                "paginas_sin_marcador": 0,
            }

    # Cerrar el último segmento
    if seg_actual is not None:
        seg_actual["pagina_fin"] = total_pag
        segmentos.append(seg_actual)
        log.info(f"  Pág {seg_actual['pagina_inicio']:3d}-{seg_actual['pagina_fin']:3d}: "
                 f"[{seg_actual['tipo']}] {seg_actual['lineas_inicio'][0][:50]}")

    # Página 1-N anteriores al primer segmento → documentos procesales sin marcador
    if segmentos and segmentos[0]["pagina_inicio"] > 1:
        # Caso especial: si el primer segmento detectado es un escrito principal
        # (SENTENCIA, DEMANDA, CONTESTACION, OPOSICION) SE FUSIONAN todas las
        # páginas anteriores con él. Las páginas sin marcador previas son siempre
        # parte del cuerpo del mismo escrito (cabecera administrativa o cuerpo
        # de la demanda/sentencia que solo tiene marcador cerca del final).
        primer_seg = segmentos[0]
        paginas_cabecera = primer_seg["pagina_inicio"] - 1
        if primer_seg["tipo"] in TIPOS_SUPER_ABSORBENTES:
            primer_seg["pagina_inicio"] = 1
            log.info(f"  Pág   1-{paginas_cabecera}: absorbidas por cuerpo de "
                     f"[{primer_seg['tipo']}]")
        else:
            seg_cabecera = {
                "tipo":          "ACTUACION_PROCESAL",
                "num_doc":       1,
                "pagina_inicio": 1,
                "pagina_fin":    segmentos[0]["pagina_inicio"] - 1,
                "lineas_inicio": [],
                "paginas_sin_marcador": 0,
            }
            segmentos.insert(0, seg_cabecera)
            log.info(f"  Pág   1-{seg_cabecera['pagina_fin']:3d}: [ACTUACION_PROCESAL] "
                     f"(cédula/decreto/auto sin marcador explícito)")

    # Limpiar campo interno antes de devolver
    for seg in segmentos:
        seg.pop("paginas_sin_marcador", None)

    # Post-proceso: renumerar por tipo si no tienen número
    contadores = defaultdict(int)
    for seg in segmentos:
        contadores[seg["tipo"]] += 1
        if seg["num_doc"] is None:
            seg["num_doc"] = contadores[seg["tipo"]]

    log.info(f"Segmentos finales: {len(segmentos)}")
    return segmentos


# ══════════════════════════════════════════════════════════════════════════════
# GENERACIÓN DE ARCHIVOS
# ══════════════════════════════════════════════════════════════════════════════

def nombre_archivo(segmento, indice):
    """Genera el nombre de archivo para un segmento."""
    tipo = segmento["tipo"]
    num  = segmento["num_doc"] or indice
    return f"{indice:02d}_{tipo}_{num:02d}.pdf"


def separar_pdf(ruta_pdf, segmentos, carpeta_salida, log):
    """Genera un PDF por segmento en la carpeta de salida.

    Escritura defensiva:
    - Cada PDF se escribe a un temporal ``.tmp`` y se promueve con ``replace``
      (atómico). Si ``writer.write`` falla a mitad, no queda un PDF truncado
      con su nombre definitivo.
    - Si un segmento no abarca ninguna página (``fin <= inicio``) se lanza
      ``PDFVacioError`` en vez de emitir un PDF vacío.
    - Ante cualquier error se borra el conjunto parcial ya escrito, para no
      dejar PDFs sueltos sin su ``indice.json``.
    """
    from pypdf import PdfReader, PdfWriter

    resultados = []
    escritos: list[Path] = []   # rutas finales ya promovidas (para limpiar en error)
    tmp: Path | None = None
    try:
        with PdfReader(str(ruta_pdf)) as reader:
            total_pags = len(reader.pages)

            for i, seg in enumerate(segmentos, 1):
                inicio = seg["pagina_inicio"] - 1  # 0-indexed
                fin    = min(seg["pagina_fin"], total_pags)  # 0-indexed exclusive

                if fin <= inicio:
                    # Segmento sin páginas reales (p. ej. PDF de 0 págs o rango
                    # degenerado). No emitir un PDF vacío.
                    raise PDFVacioError(
                        f"Segmento {i} [{seg['tipo']}] no abarca ninguna página "
                        f"(rango {seg['pagina_inicio']}-{seg['pagina_fin']} sobre "
                        f"{total_pags} págs): {ruta_pdf.name}"
                    )

                writer = PdfWriter()
                for p in range(inicio, fin):
                    writer.add_page(reader.pages[p])

                nombre = nombre_archivo(seg, i)
                ruta_salida = carpeta_salida / nombre
                tmp = carpeta_salida / (nombre + ".tmp")

                # Escritura atómica: temporal + replace.
                with open(tmp, "wb") as f:
                    writer.write(f)
                tmp.replace(ruta_salida)
                tmp = None
                escritos.append(ruta_salida)

                n_pags = fin - inicio
                log.info(f"  {nombre}: págs {seg['pagina_inicio']}-{seg['pagina_fin']} ({n_pags} pág{'s' if n_pags>1 else ''})")
                resultados.append({
                    "archivo": nombre,
                    "tipo": seg["tipo"],
                    "paginas": f"{seg['pagina_inicio']}-{seg['pagina_fin']}",
                    "n_paginas": n_pags,
                })
    except Exception:
        # Limpieza: no dejar un temporal truncado ni un set parcial de PDFs
        # sin su indice.json.
        if tmp is not None:
            tmp.unlink(missing_ok=True)
        for r in escritos:
            r.unlink(missing_ok=True)
        raise

    return resultados


# ══════════════════════════════════════════════════════════════════════════════
# ÍNDICE
# ══════════════════════════════════════════════════════════════════════════════

def generar_indice(resultados, ruta_pdf, carpeta_salida, log):
    """Genera un fichero índice JSON y un resumen en texto."""
    indice = {
        "generado": datetime.now().isoformat(),
        "fuente": ruta_pdf.name,
        "documentos": resultados,
    }

    ruta_json = carpeta_salida / "indice.json"
    ruta_json.write_text(
        json.dumps(indice, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    # También un resumen legible en txt
    lineas = [
        f"ÍNDICE DE DOCUMENTOS — {ruta_pdf.name}",
        f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        f"Total documentos: {len(resultados)}",
        "─" * 55,
    ]
    for r in resultados:
        lineas.append(f"  {r['archivo']:<45} págs {r['paginas']} ({r['n_paginas']}p)")

    ruta_txt = carpeta_salida / "indice.txt"
    ruta_txt.write_text("\n".join(lineas), encoding="utf-8")

    log.info(f"Índice generado: {ruta_json.name}")


# ══════════════════════════════════════════════════════════════════════════════
# API PÚBLICA NO INTERACTIVA (FeesDefender — Fase 2)
# ══════════════════════════════════════════════════════════════════════════════

def separar_pdf_pipeline(
    ruta_pdf: Path,
    carpeta_salida: Path,
    log: logging.Logger | None = None,
    *,
    on_page: Callable[[int, int], None] | None = None,
) -> list[dict]:
    """Separa un PDF de expediente en documentos individuales sin interacción.

    Wrapper público de la triada ``detectar_segmentos`` + ``separar_pdf`` +
    ``generar_indice``. Sin menú CMD, sin ``sys.argv``, sin ``input()``.
    Diseñado para uso embebido desde la fachada del módulo y desde tests.

    Si el PDF no contiene marcadores reconocibles (escaneo limpio, sentencia
    sin portada estandarizada, etc.), el PDF se trata como **documento
    único** con tipo ``DOCUMENTO`` y se separa en una sola pieza, replicando
    el fallback gracious de ``procesar()`` (L.718-731 del original).

    Args:
        ruta_pdf: PDF de expediente a separar.
        carpeta_salida: Carpeta donde escribir los PDFs por documento, el
            ``indice.json`` y el ``indice.txt``. Se crea si falta.
        log: Logger opcional. Si ``None``, se usa un logger silencioso
            interno para no romper el patrón embebido.
        on_page: Callback opcional ``(num_pag, total_pag)`` para reportar
            progreso del análisis estructural en UI.

    Returns:
        Lista de dicts con la estructura del original ``separar_pdf``:
        ``{"archivo": str, "tipo": str, "paginas": str, "n_paginas": int}``.
        Lista no vacía garantizada (al menos un documento).
    """
    if log is None:
        log = logging.getLogger("separador.embebido")
        if not log.handlers:
            log.addHandler(logging.NullHandler())

    ruta_pdf = Path(ruta_pdf)
    carpeta_salida = Path(carpeta_salida)
    carpeta_salida.mkdir(parents=True, exist_ok=True)

    segmentos = detectar_segmentos(ruta_pdf, log, on_page=on_page)

    if not segmentos:
        # Fallback gracious: PDF sin marcadores → documento único.
        from pypdf import PdfReader
        with PdfReader(str(ruta_pdf)) as reader:
            total_pag = len(reader.pages)
        if total_pag == 0:
            # PDF de 0 páginas: sin esta guarda se generaba un segmento '1-0'
            # → range(0, 0) → un PDF vacío registrado como documento real.
            raise PDFVacioError(
                f"PDF sin páginas (0 págs): {ruta_pdf.name}. "
                "No se puede separar ni emitir ningún documento."
            )
        log.info(f"Sin marcadores detectados. Documento único ({total_pag} págs).")
        segmentos = [{
            "tipo":          "DOCUMENTO",
            "num_doc":       1,
            "pagina_inicio": 1,
            "pagina_fin":    total_pag,
            "lineas_inicio": [],
        }]

    resultados = separar_pdf(ruta_pdf, segmentos, carpeta_salida, log)
    generar_indice(resultados, ruta_pdf, carpeta_salida, log)
    return resultados


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def revisar_segmentos_interactivo(segmentos, ruta_pdf):
    """
    Muestra la propuesta de separación y permite al usuario modificarla.
    Devuelve la lista de segmentos modificada, o None si cancela.
    """
    TIPOS_DISPONIBLES = [
        "ACTUACION_PROCESAL", "DEMANDA", "CONTESTACION", "OPOSICION",
        "SENTENCIA", "AUTO", "DECRETO", "CEDULA_EMPLAZAMIENTO",
        "DOC_PODER_NOTARIAL", "DOC_CONTRATO", "DOC_FACTURA",
        "DOC_EMAIL", "DOC_EXTRACTO_BANCARIO", "DOC_INFORME",
        "DOC_REGISTRO_AUDITORIA", "DOC_TRADUCCION", "DOC_ANEXO",
    ]

    while True:
        # Mostrar propuesta actual
        print()
        print("  ====================================================")
        print("  REVISION DE SEPARACION")
        print("  ====================================================")
        print(f"  PDF: {ruta_pdf.name}")
        print()
        for i, seg in enumerate(segmentos, 1):
            npags = seg['pagina_fin'] - seg['pagina_inicio'] + 1
            ndoc  = f"nº{seg['num_doc']}" if seg['num_doc'] else "   "
            print(f"  {i:2d}. {seg['tipo']:<30} {ndoc:<5} págs {seg['pagina_inicio']}-{seg['pagina_fin']} ({npags}p)")
        print()
        print("  Opciones:")
        print("    C  - Continuar con esta separacion")
        print("    F  - Fusionar dos segmentos consecutivos")
        print("    E  - Eliminar un segmento")
        print("    T  - Cambiar el tipo de un segmento")
        print("    U  - Tratar como documento unico (sin separar)")
        print("    X  - Cancelar")
        print()

        opcion = input("  Opcion: ").strip().upper()

        if opcion == "C":
            return segmentos

        elif opcion == "X":
            return None

        elif opcion == "U":
            # Documento único: un solo segmento con el PDF completo
            tipo = input("  Tipo del documento unico (Enter=DEMANDA): ").strip() or "DEMANDA"
            seg_unico = {
                "tipo": tipo,
                "num_doc": 1,
                "pagina_inicio": segmentos[0]["pagina_inicio"],
                "pagina_fin": segmentos[-1]["pagina_fin"],
                "lineas_inicio": segmentos[0]["lineas_inicio"],
            }
            print(f"  -> Tratando como documento unico: {tipo}")
            return [seg_unico]

        elif opcion == "F":
            try:
                n = int(input("  Fusionar segmento numero: ").strip())
                if n < 1 or n >= len(segmentos):
                    print(f"  ERROR: introduce un numero entre 1 y {len(segmentos)-1}")
                    continue
                # Fusionar n con n+1
                a = segmentos[n - 1]
                b = segmentos[n]
                a["pagina_fin"] = b["pagina_fin"]
                segmentos.pop(n)
                # Renumerar
                contadores = {}
                for seg in segmentos:
                    t = seg["tipo"]
                    contadores[t] = contadores.get(t, 0) + 1
                    seg["num_doc"] = contadores[t]
                print(f"  -> Segmentos {n} y {n+1} fusionados")
            except (ValueError, IndexError):
                print("  ERROR: numero invalido")

        elif opcion == "E":
            try:
                n = int(input("  Eliminar segmento numero: ").strip())
                if n < 1 or n > len(segmentos):
                    print(f"  ERROR: introduce un numero entre 1 y {len(segmentos)}")
                    continue
                eliminado = segmentos.pop(n - 1)
                print(f"  -> Eliminado: {eliminado['tipo']} págs {eliminado['pagina_inicio']}-{eliminado['pagina_fin']}")
                if not segmentos:
                    print("  ERROR: no quedan segmentos. Operacion cancelada.")
                    return None
            except (ValueError, IndexError):
                print("  ERROR: numero invalido")

        elif opcion == "T":
            try:
                n = int(input("  Cambiar tipo del segmento numero: ").strip())
                if n < 1 or n > len(segmentos):
                    print(f"  ERROR: introduce un numero entre 1 y {len(segmentos)}")
                    continue
                print("  Tipos disponibles:")
                for i, t in enumerate(TIPOS_DISPONIBLES, 1):
                    print(f"    {i:2d}. {t}")
                idx = int(input("  Numero de tipo: ").strip()) - 1
                if 0 <= idx < len(TIPOS_DISPONIBLES):
                    segmentos[n-1]["tipo"] = TIPOS_DISPONIBLES[idx]
                    print(f"  -> Tipo cambiado a: {TIPOS_DISPONIBLES[idx]}")
                else:
                    print("  ERROR: numero invalido")
            except (ValueError, IndexError):
                print("  ERROR: numero invalido")

        else:
            print("  Opcion no reconocida. Usa C, F, E, T, U o X.")


def procesar(ruta_archivo):
    ruta = Path(ruta_archivo)
    if not ruta.exists():
        print(f"ERROR: No se encuentra: {ruta_archivo}")
        sys.exit(1)

    # Configurar log
    # Carpeta de salida: argumento explícito o subcarpeta junto al PDF
    if len(sys.argv) >= 3 and sys.argv[2]:
        carpeta_salida = Path(sys.argv[2])
    else:
        carpeta_salida = ruta.parent / ruta.stem
    carpeta_salida.mkdir(parents=True, exist_ok=True)

    log_path = carpeta_salida / "separador.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8", mode="w"),
            logging.StreamHandler(sys.stdout),
        ]
    )
    log = logging.getLogger("separador")

    log.info("=" * 55)
    log.info(f"Separador de expedientes judiciales v1.0")
    log.info(f"Archivo: {ruta.name}")
    log.info("=" * 55)

    # 1. Detectar segmentos
    segmentos = detectar_segmentos(ruta, log)

    if not segmentos:
        # Ningun marcador detectado → tratar el PDF como documento unico.
        # Esto es el caso habitual de sentencias o escritos sin portada con
        # marcadores claros; mejor que fallar.
        from pypdf import PdfReader
        with PdfReader(str(ruta)) as reader:
            total_pag = len(reader.pages)
        if total_pag == 0:
            print(f"ERROR: el PDF no tiene páginas: {ruta.name}")
            sys.exit(1)
        log.info(f"Sin marcadores detectados. Tratando como documento unico ({total_pag}p)")
        segmentos = [{
            "tipo":          "DOCUMENTO",
            "num_doc":       1,
            "pagina_inicio": 1,
            "pagina_fin":    total_pag,
            "lineas_inicio": [],
        }]

    # 2. Mostrar resumen y pedir confirmación
    print(f"\n  Documentos detectados: {len(segmentos)}")
    print(f"  Carpeta de salida: {carpeta_salida}\n")
    for i, seg in enumerate(segmentos, 1):
        npags = seg['pagina_fin'] - seg['pagina_inicio'] + 1
        ndoc  = f"nº{seg['num_doc']}" if seg['num_doc'] else ""
        print(f"  {i:2d}. {seg['tipo']:<30} {ndoc:<6} págs {seg['pagina_inicio']}-{seg['pagina_fin']} ({npags}p)")

    # En modo pipeline (3er argumento = --sin-confirmacion) omitir revisión
    sin_confirmacion = len(sys.argv) >= 4 and sys.argv[3] == "--sin-confirmacion"
    if not sin_confirmacion:
        segmentos = revisar_segmentos_interactivo(segmentos, ruta)
        if segmentos is None:
            print("  Operación cancelada.")
            sys.exit(0)

    # 3. Separar
    log.info("Generando PDFs...")
    resultados = separar_pdf(ruta, segmentos, carpeta_salida, log)

    # 4. Índice
    generar_indice(resultados, ruta, carpeta_salida, log)

    log.info(f"Completado. {len(resultados)} archivos en: {carpeta_salida}")
    print(f"\n  ✓ {len(resultados)} documentos generados en:")
    print(f"    {carpeta_salida}")


if __name__ == '__main__':
    # UTF-8 wrap solo en uso CLI (Windows). En uso embebido (Streamlit /
    # pipeline / tests) este bloque no se ejecuta.
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    if len(sys.argv) < 2:
        print("Uso: python separar.py \"ruta/al/expediente.pdf\" [carpeta_destino] [--sin-confirmacion]")
        sys.exit(1)

    procesar(sys.argv[1])

    # En modo pipeline (flag --sin-confirmacion) no esperar Enter: colgaria el pipeline
    if "--sin-confirmacion" not in sys.argv:
        try:
            input("\nPulsa Enter para cerrar...")
        except EOFError:
            pass
