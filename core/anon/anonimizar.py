"""
Anonimizador de documentos judiciales v3.10
=========================================
- Etiquetas nominativas y contextuales genéricas
- Mapa JSON para deanonimización
- Modo revisión interactivo en CMD
- Detección de empresas vs personas físicas
- Soporte PDF (con OCR) y DOCX
- Validación de calidad
- Log de sesión

Cambios v3.2:
- aplicar_regex: matches sobre texto original + sustitución por offset inverso
- anonimizar_por_contexto: guarda contra re-procesar etiquetas ya insertadas
- anonimizar_mayusculas: guarda ampliada para interior de etiquetas [TIPO_N]
- Presidio: modelo catalán corregido (ca_core_news_sm); avisos explícitos si falla
- texto_a_markdown: filtro anti-ruido OCR para falsos encabezados ##
- revisar_interactivo [7]: rol personalizado usa registrar_dato()

Cambios v3.3:
- MapaEntidades.registrar: deduplicación de variantes parciales del mismo nombre
- texto_a_markdown: excluir líneas con ':' del bloque ## y ampliar RUIDO_OCR
- Presidio: threshold PERSON subido a 0.65 + filtro de fragmentos con minúsculas

Cambios v3.4:
- _TRAT, _ILMO, _NOMBRE: constantes compartidas definidas antes de
  INDICADORES_NO_ANONIMIZAR y PATRONES_CONTEXTO
- INDICADORES_NO_ANONIMIZAR: procurador y magistrado con separadores correctos;
  cubre Dna./Dña./Ilmo. Sr. D.
- PATRON_NO_ANONIMIZAR: usa _NOMBRE con lookahead negativo ante DNI/COL/etc.

Cambios v3.5:
- PATRONES_CONTEXTO: separador cambiado a colon obligatorio para partes procesales,
  eliminando capturas de texto narrativo (demandante/demandado en prosa)

Cambios v3.6:
- Eliminada detección automática del tipo de procedimiento (no es dato personal,
  causaba falsos positivos por palabras del cuerpo del texto)
- Eliminadas TIPOS_PROCEDIMIENTO y ETIQUETAS_COMUNES
- Nueva función pedir_tipo_procedimiento(): solicita texto libre al usuario,
  se usa únicamente como metadato en la cabecera del Markdown
- MapaEntidades ya no recibe etiquetas por tipo de procedimiento; usa
  ETIQUETAS_PARTE genéricas (PARTE_ACTORA, PARTE_DEMANDADA, PROCURADOR, etc.)
- Pipeline completamente determinista: sin detección automática susceptible
  de error por contenido del documento

Cambios v3.10:
- [GRUPO-1] extraer_texto_pdf: nueva función pagina_girada() que detecta
  páginas giradas 180° por dos señales: >40% de LTChar con ancho negativo
  (coordenadas invertidas por pdfminer) y >70% de grupos Y con ≤3 chars
  (fragmentación excesiva). Las páginas giradas se descartan completamente
  antes de llegar a las fases de anonimización, eliminando el 32% de
  falsos positivos del mapa (NOMBRE_24 a NOMBRE_50 en v3.9).
- [GRUPO-2] anonimizar_con_presidio: post-procesamiento de fragmentos PERSON
  para eliminar prefijos de contexto que Presidio captura junto al nombre
  ("Nombre Saydou", "Mirshojaei Nombre"). Lista de prefijos: NOMBRE, NOM,
  SEXE, FECHA, DATA, REPRESENTADO, INVESTIGAT, etc.
- [GRUPO-3] es_nombre_valido(): rechazo de fragmentos partidos por OCR
  mediante análisis de inicio/fin de cada palabra — palabras de 4+ chars
  que empiezan o terminan con 2 consonantes sin vocal y sin prefijo/sufijo
  español válido se consideran fragmentos cortados (LEGI, MPLIM, CCIÓ...).
- [GRUPO-3] PALABRAS_EXCLUIDAS: añadidos fragmentos de términos ya excluidos
  que aparecían como falsos positivos (LUSTRE, LEGI, PROCURA, CACIÓ, TARÓ,
  MATARÓ, MATARÓO, NOTIFI, DENUN, CIADO, TIFICA...).

Cambios v3.9:
- [FP-TELEFONO] Presidio: añadido filtro post-detección para PHONE_NUMBER que
  valida el número contra un patrón español real (6/7/8/9XXXXXXXX o +34...)
  y descarta referencias policiales, códigos de unidad funcional, NIGs
  fragmentados y fechas que Presidio clasificaba erróneamente como teléfono.
- [FP-NOMBRE] es_nombre_valido(): añadido filtro de coherencia léxica que
  rechaza secuencias con proporción de consonantes imposible en español
  (>80% consonantes en palabras de 4+ chars) para eliminar ruido OCR basura
  como "VI OL NHIN ITINN", "JUEJ IOY", "NI IDIC TV", etc.
- [FP-NOMBRE] PALABRAS_EXCLUIDAS: ampliada con términos procesales que
  aparecían etiquetados como nombre: CONDICION, DECANO, URGENTE, CAUSA,
  SOLICITUD, BLANES, PERSONA, PREMIUM, ORGANOS, ESCRITO, ACUSACION,
  SERVICIO, COMUN, DELEGADA, PROCEDA, NOTIFICAR, TRATARSE, ADJUNTA.
- [CONTEXTO] PATRONES_CONTEXTO: campos "Nombre del Procurador/Letrado/
  Representado" ahora anclan la captura al separador '.-:' o ':' y limitan
  el match a fin de línea (sin consumir texto del siguiente campo).
- [PROTEGIDOS] detectar_nombres_protegidos(): el patrón _NOMBRE ahora
  termina ante palabras funcionales comunes (En, Fecha, Nombre, echa,
  Clase, Y, a) que aparecían pegadas al nombre de operadores jurídicos
  produciendo entradas como "ELENA HORNOS TURÓN En".

Cambios v3.8:
- extraer_texto_pdf: añadida función iterar_elementos() con descenso recursivo
  a LTFigure para compatibilidad con PDFs de OCRmyPDF. OCRmyPDF incrusta el
  texto OCR en Form XObjects (LTFigure en pdfminer), no como LTTextBox en la
  página raíz. Sin este descenso, v3.7 veía el PDF como "sin capa de texto".

Cambios v3.7:
- extraer_texto_pdf: reescrita con extracción por coordenadas (LTTextBox/LTTextLine)
  en lugar de extract_text() que producía texto sin estructura en PDFs OCR.
  El nuevo extractor ordena líneas por posición vertical y horizontal, detecta
  párrafos por saltos de altura, filtra ruido OCR por ratio de legibilidad (<60%
  caracteres legibles), y separa páginas con encabezado [Página N].
  Resultado: .md legible con estructura preservada para los tres escenarios
  de uso: DOCX propios, documentos judiciales PDF, medios de prueba PDF.
"""

import sys
import re
import json
import os
import logging
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Excepciones del módulo: sustituyen los `sys.exit(1)` del original para que
# el orquestador (Streamlit / pipeline FeesDefender) pueda capturarlas en
# lugar de matar el proceso. Ver `core/anon/exceptions.py`.
from core.anon.exceptions import (
    DocxVacioError,
    FormatoNoSoportadoError,
    PDFSinTextoError,
)

# Nota: el wrap UTF-8 de stdout/stderr (Windows) que el módulo original
# aplicaba a nivel de import rompía Streamlit al importarse de forma
# embebida. Ahora vive solo dentro del bloque ``if __name__ == '__main__':``
# al final del fichero, donde sí es necesario para uso por línea de comando.


# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURACION DE LOG
# ══════════════════════════════════════════════════════════════════════════════

def configurar_log(carpeta: Path, acumular: bool = False) -> logging.Logger:
    """Configura el log.

    acumular=True: añade al log existente (modo pipeline, varios documentos).
    acumular=False: sobrescribe (modo individual, un solo documento).

    El log se guarda en la carpeta del expediente (subiendo desde carpeta del PDF)
    o junto al PDF si no se encuentra la estructura de expediente.
    """
    # Intentar guardar el log en la carpeta raíz del expediente
    log_path = carpeta / "anonimizador.log"
    carpeta_buscar = carpeta
    for _ in range(5):
        if (carpeta_buscar / "expediente.json").exists():
            log_path = carpeta_buscar / "anonimizador.log"
            break
        carpeta_buscar = carpeta_buscar.parent
    modo = "a" if acumular else "w"

    # Limpiar handlers existentes para evitar duplicados
    logger = logging.getLogger("anonimizador")
    for h in logger.handlers[:]:
        logger.removeHandler(h)
        h.close()

    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    fh = logging.FileHandler(log_path, encoding="utf-8", mode=modo)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    return logger


# ══════════════════════════════════════════════════════════════════════════════
# ETIQUETAS GENERICAS DE PARTES
# ══════════════════════════════════════════════════════════════════════════════
# Etiquetas fijas independientes del tipo de procedimiento.
# El tipo de procedimiento no es un dato personal y no condiciona
# la anonimización: se usa únicamente como metadato descriptivo en la
# cabecera del Markdown.

ETIQUETAS_PARTE = {
    "actor":      "PARTE_ACTORA",
    "demandado":  "PARTE_DEMANDADA",
    "procurador": "PROCURADOR",
    "letrado":    "LETRADO",
    "magistrado": "MAGISTRADO",
    "laj":        "LAJ",
    "perito":     "PERITO",
    "testigo":    "TESTIGO",
    "fiscal":     "FISCAL",
    "nombre":     "NOMBRE",
    "empresa":    "EMPRESA",
}

# Sufijos societarios para detectar empresas
SUFIJOS_EMPRESA = re.compile(
    r'\b(?:S\.?L\.?U?\.?|S\.?A\.?U?\.?|S\.?L\.?P\.?|S\.?L\.?L\.?|S\.?L\.?N\.?E\.?|'
    r'S\.?C\.?P\.?|C\.?B\.?|S\.?COOP\.?|S\.?A\.?T\.?|'
    r'SLU|SLP|SLL|SLNE|SAU|SCP|CB)\b',
    re.IGNORECASE
)


# ══════════════════════════════════════════════════════════════════════════════
# PALABRAS EXCLUIDAS DE DETECCION DE NOMBRES
# ══════════════════════════════════════════════════════════════════════════════

PALABRAS_EXCLUIDAS = {
    'JUZGADO','INSTRUCCION','CIVIL','PENAL','MERCANTIL','SOCIAL',
    'PROCEDIMIENTO','ORDINARIO','VERBAL','PREVIAS','DILIGENCIAS','ABREVIADO',
    'PARTE','DEMANDANTE','DEMANDADA','EJECUTANTE','EJECUTADA',
    # §4: variantes masculinas (faltaban; agravaban el bug §3 al no recortarse)
    'DEMANDADO','EJECUTADO','QUERELLADO','QUERELLANTE','INVESTIGADO',
    'ACUSADO','RECURRIDO','RECURRENTE','APELADO','APELANTE',
    'PROCURADOR','PROCURADORA','ABOGADO','ABOGADA','LETRADO','LETRADA',
    'MAGISTRADO','MAGISTRADA','JUEZ','JUEZA','SECRETARIO','SECRETARIA',
    'MINISTERIO','FISCAL','NOTARIO','NOTARIA','PERITO','PERITOS',
    'TRIBUNAL','AUDIENCIA','JUZGADOS','SALA','SECCION',
    'DECRETO','AUTO','SENTENCIA','PROVIDENCIA','RESOLUCION','DILIGENCIA',
    'HECHOS','FUNDAMENTOS','SUPLICO','FALLO','ANTECEDENTES','OTROSÍ','OTROSI',
    'PRIMERO','SEGUNDO','TERCERO','CUARTO','QUINTO','SEXTO',
    'ARTICULO','LEY','CODIGO','REGLAMENTO','DISPOSICION',
    'ESPANA','CATALUNA','BARCELONA','MADRID','VALENCIA','SEVILLA',
    'BANCO','SANTANDER','BBVA','CAIXABANK','SABADELL','IBERCAJA',
    'SL','SLU','SA','SAU','SLP','SLL','SLNE','CB','SCP',
    'LEC','LECR','CP','LOPJ','CE','LRJS','ET',
    'NIG','NIF','DNI','NIE','CIF','IBAN',
    'TEL','FAX','EMAIL','WEB','HTTP','HTTPS',
    'ADMINISTRACION','JUSTICIA','PODER','JUDICIAL',
    'CEDULA','NOTIFICACION','EMPLAZAMIENTO','CITACION',
    'REQUERIMIENTO','OFICIO','COMPARECENCIA','ORDENACION',
    'ACUERDO','RESOLUCION','PROVIDENCIA',
    'GRAN','VIA','CALLE','AVENIDA','PASEO','PLAZA','CARRER',
    'NUMERO','PISO','PLANTA','LOCAL','BAJO','IZQUIERDA','DERECHA',
    # v3.9: añadidos por falsos positivos en documentos judiciales
    'CONDICION','DECANO','URGENTE','CAUSA','SOLICITUD','PERSONA',
    'ORGANOS','ESCRITO','ACUSACION','SERVICIO','COMUN','DELEGADA',
    'PROCEDA','NOTIFICAR','TRATARSE','ADJUNTA','INTERESADAS',
    'CUMPLIMIENTO','EXHORTO','LIBERTAD','PRESO','BRIANS',
    'BLANES','LLORET','ALELLA','PREMIA','ANDREU','LLAVANERES',
    'PREMIUM','HOUSES','MARESME','PROPERTIES','DIAGONAL',
    # v3.10: fragmentos de términos excluidos partidos por OCR
    'LUSTRE','LEGI','PROCURA','CACIÓ','TARÓ','FICACIÓ',
    # v3.10b: títulos de documento y campos que no son nombres
    'CÉDULA','CEDULA','DENUNCIADO','DENUNCIANTE','DENUNCIAT','DENUNCIANT',
    'ETOTTE','IVION','UMPLIM','MPLIM','PENIT','ENCIAR','ATIFIC','ACIOMINI',
    'PASSATGE','MARFIL','PARTIR','DALT','PALOU','JAVA',
    'URGENTE','PRESO','CAUSA',
    'DENUN','CIADO','CIANTE','TIFICA','NOTIFI',
    'MATARÓ','MATARÓO','MATARO','DEMAT','ARÓ',
    'VIDENCIA','PROVI','ROVID',  # fragmentos de PROVIDENCIA cortada por OCR
    'ETOTTE','IVION','UMPLIM','NMIN','EXHO',  # ruido OCR persistente
    'MIRMOH','MIRMOL',  # fragmentos de Mirmohsen cortados por OCR
    'ADMINISTRACIIN','ADMINISTRACION','ADMINISTRACIO',
    'COOPERACION','COOPERACIÓ','COOPER',
    'JUSTICIA','JUSTÍCIA','CATALUNA','CATALUÑA',
    # v3.9: términos judiciales catalanes frecuentes en cédulas y exhortos
    'RECEPCIÓ','NOTIFICACIÓ','LLETRAT','LLETRADA','JUTJAT','JUTJATS',
    'PROCEDIMENT','ABREUJAT','SECCIO','SECCIÓ','NOM','COGNOM','COGNOMS',
    'LLOC','DATA','SEXE','PASSAPORT','INVESTIGAT','DIFUSIO','DIFUSIÓ',
    'ACTUACIÓ','ACTUACIO','REQUERIMENT','DEPENDÈNCIA','DEPENDENCIA',
    'CITACIÓ','CITACIO','TRASLLAT','OBJECTIU','ACOMPANYAMENT',
    'RESOLUCIÓ','RESOLUCIO','DILIGÈNCIA','JURISDICCIÓ','JURISDICCIO',
    'ESPECIALITAT','QUALITAT','IDENTIFICAT','MUNICIPI','LOCALITAT',
    'PROVÍNCIA','NACIONALITAT','NAIXEMENT','EXPEDICIO','EXPEDICIÓ',
    'ATESTAT','POLICIAL','MOSSOS','ESQUADRA','GENERALITAT','CATALUNYA',
    'ADMINISTRACIO','ADMINISTRACIÓ','JUSTÍCIA',
    'COLLEGI','PROCURADORS','ILUSTRE',
    # v3.10c: términos del ofici de requeriment catalán
    'DOMICILI','AUTORITAT','MOTIU','ACTUACIÓ','ACTUACIO',
    'DIFUSIO','DIFUSIÓ','CITACIÓ','CITACIO','TRASLLAT',
    'COGNOM','COGNOMS','COGNO','DADES','QUALITAT',
    'INVESTIGAT','EXPEDICIO','EXPEDICIÓ','POLICIAL',
    'OBSERVACIONS','COMPLEMENTARIES','ACOMPANYAMENT',
    'OBJECTIU','CENTRE','MENORS','PARADOR',
    # términos castellanos que escapaban
    'CASO','DOMICILIO','PARADOR','TELEFONO','OBSERVACIONES',
}


# ══════════════════════════════════════════════════════════════════════════════
# LISTA BLANCA — ENTIDADES QUE NO SE ANONIMIZAN
# ══════════════════════════════════════════════════════════════════════════════
#
# Los operadores juridicos que actuan en calidad de tales (jueces, LAJ,
# abogados, procuradores, notarios) y los datos identificativos del
# procedimiento no son datos personales en sentido RGPD cuando se refieren
# al ejercicio de funciones publicas o profesionales (art. 9 Ley 29/2021,
# doctrina AEPD). No se anonimizan.

# Prefijo de tratamiento: Don, Doña, Dña., Dna., D. (con punto opcional)
_TRAT = r'(?:d(?:on|o[nñ]a?|ña|na)\.?\s*|d\.\s*)?'
# Prefijo honorífico: Ilmo. Sr. / Ilma. Sra. (opcional, precede a magistrados)
_ILMO = r'(?:ilmo?s?\.?\s*sr[as]?\.?\s*)?'

# Patrón de nombre propio: 2-4 palabras en mayúsculas, sin dígitos.
# Lookahead negativo para no consumir palabras clave que siguen al nombre.
_STOP_KWORD = r'(?!\s+(?:DNI|NIE|NIF|CIF|COL|NUM|TEL|FAX|EMAIL|IBAN|NIG|REF|EXP)[\s\.\:])'
# v3.9: lookahead negativo ante palabras funcionales que aparecen tras nombre
# de operadores jurídicos en cédulas: "En Mataró", "Fecha resolución", etc.
_STOP_FUNC  = r'(?!\s+(?:En|Fecha|Nombre|Clase|echa|Y\s|a\s|\d))'
_WORD  = r'[A-ZÁÉÍÓÚÜÑ\-\']{2,}'
_WSTOP = _STOP_KWORD + _STOP_FUNC
_NOMBRE = r'(' + _WORD + r'(?:' + _WSTOP + r'\s+' + _WORD + r'){1,3})'

# Indicadores contextuales que preceden a un nombre NO anonimizable:

INDICADORES_NO_ANONIMIZAR = [
    # Juez / Magistrado — cubre: "Magistrado:", "Ilmo. Sr. D.", "Ilmo. Sr. Magistrado"
    r'(?:magistrado|magistrada|juez|jueza)[:/\s]+' + _ILMO + _TRAT,
    r'ilmo?s?\.?\s*sr[as]?\.?\s*(?:d(?:on|o[nñ]a?|ña|na)\.?\s*|d\.\s*)?(?:magistrado|magistrada|juez|jueza\s+)?',
    r'ilmo?s?\.?\s*sr[as]?\.?\s*d\.\s*',
    # LAJ
    r'(?:letrad[ao]\s+de\s+la\s+adm(?:inistración|inistracion)?\.?\s+de\s+justicia|laj|secretari[ao]\s+judicial)[:/\s]+' + _TRAT,
    # Procurador (operador juridico en ejercicio de su funcion)
    r'(?:procurador|procuradora)(?:\s+(?:de\s+(?:los?\s+)?tribunales))?[:/\s]+' + _TRAT,
    # Abogado en calidad profesional
    r'(?:abogado|abogada|letrado|letrada)\s+(?:del?\s+estado|de\s+la\s+(?:acusacion|defensa)|num(?:ero)?\.?\s*\d+)[:/\s]+' + _TRAT,
    # Notario
    r'(?:notario|notaria)[:/\s]+' + _TRAT,
    # Fiscal
    r'(?:fiscal|ministerio\s+fiscal)[:/\s]+' + _TRAT,
    # Nombre del organo judicial
    r'(?:juzgado\s+(?:de\s+)?(?:primera\s+instancia|instruccion|lo\s+(?:civil|penal|social|mercantil))|audiencia\s+(?:provincial|nacional)|tribunal\s+(?:superior|supremo|constitucional))',
]

PATRON_NO_ANONIMIZAR = re.compile(
    r'(?:' + '|'.join(INDICADORES_NO_ANONIMIZAR) + r')' + _NOMBRE,
    re.IGNORECASE
)

# Patrones de datos procedimentales que nunca se anonimizan
PATRONES_PROCEDIMENTALES = [
    # NIG
    r'\bNIG\s*[:\s]*\d{2}[\s.-]?\d{3,5}[\s.-]?\d[\s.-]?\d{4}[\s.-]?\d+\b',
    # Numero de procedimiento (ej: 963/2023, 357/2026-2G)
    r'\b\d{2,5}/\d{4}(?:[-\s][A-Z0-9]+)?\b',
    # Numero de folio/rollo
    r'\b(?:folio|fol\.|f\.)\s*\d+\b',
    # Numero de colegiado
    r'\b(?:col\.?|colegiado\s+n[uú]m\.?)\s*\d+\b',
    # Protocolo notarial
    r'\b(?:protocolo|prot\.?)\s+n[uú]m\.?\s*\d+\b',
]

# Conjunto dinamico de nombres de operadores juridicos detectados
# (se rellena durante el procesamiento)
_nombres_protegidos: set = set()


def detectar_nombres_protegidos(texto: str) -> set:
    """Detecta nombres de operadores juridicos que no deben anonimizarse."""
    protegidos = set()
    for m in PATRON_NO_ANONIMIZAR.finditer(texto):
        nombre = m.group(1).strip()
        # Limpiar palabras sobrantes al final
        palabras = nombre.split()
        while palabras and palabras[-1].upper() in PALABRAS_EXCLUIDAS:
            palabras.pop()
        nombre_limpio = " ".join(palabras).strip()
        if nombre_limpio and len(nombre_limpio) > 3:
            protegidos.add(nombre_limpio)
    return protegidos


def esta_protegido(fragmento: str, protegidos: set) -> bool:
    """Comprueba si un fragmento coincide con un nombre protegido."""
    fragmento_limpio = fragmento.strip()
    # Coincidencia exacta
    if fragmento_limpio in protegidos:
        return True
    # Coincidencia parcial (el fragmento es parte de un nombre protegido)
    for protegido in protegidos:
        if fragmento_limpio in protegido or protegido in fragmento_limpio:
            return True
    return False


# ══════════════════════════════════════════════════════════════════════════════
# EXTRACCION DE TEXTO
# ══════════════════════════════════════════════════════════════════════════════

def extraer_texto_pdf(ruta: Path, log) -> str:
    """Extrae texto de PDF preservando la estructura de líneas y párrafos.

    v3.8: OCRmyPDF incrusta el texto OCR directamente como LTChar dentro de
    LTFigure (Form XObjects), sin pasar por LTTextBox ni LTTextLine.
    Esta versión recoge todos los LTChar de forma recursiva y los agrupa
    en líneas de texto por posición Y (tolerancia 3pt), reconstruyendo los
    espacios entre palabras por salto horizontal entre caracteres.

    Filtros anti-ruido:
    1. Ratio de caracteres legibles < 65%: descarta cirílico u otros
       alfabetos no latinos (páginas giradas, sellos, etc.)
    2. Líneas de menos de 2 caracteres: descartadas.
    """
    from pdfminer.high_level import extract_pages
    from pdfminer.layout import LTChar
    from collections import defaultdict

    log.info(f"Extrayendo texto de PDF (modo LTChar v3.8): {ruta.name}")

    def recoger_chars(contenedor, chars):
        """Recoge recursivamente todos los LTChar del contenedor."""
        for elem in contenedor:
            if isinstance(elem, LTChar):
                chars.append(elem)
            elif hasattr(elem, '__iter__'):
                recoger_chars(elem, chars)

    def pagina_girada(chars) -> bool:
        """Detecta páginas de resguardo/exhorto giradas que generan ruido OCR.

        v3.10 rev2: OCRmyPDF corrige las coordenadas antes de escribir el PDF,
        por lo que el detector de ancho negativo (v3.10 original) no funciona.
        La señal real es la proporción chars/líneas:
        - Página normal: ~1300 chars, ~30 líneas → ratio ~43 chars/línea
        - Página girada (resguardo): ~200-700 chars, ~50-135 líneas → ratio <8
        Si chars < 800 y líneas > 50 (ratio < 10), la página es un resguardo
        girado y se descarta. Este umbral cubre las páginas 9,10,12,14,16,
        18,19,22,30 del PDF de prueba sin afectar a páginas normales.
        """
        if not chars:
            return False
        # Construir líneas para contar
        grupos_y = defaultdict(int)
        for c in chars:
            y_key = round(c.y0 / 3.0) * 3.0
            grupos_y[y_key] += 1
        n_lineas = len(grupos_y)
        n_chars = len(chars)
        # Señal principal: ratio chars/líneas bajo con muchas líneas
        if n_lineas > 50 and n_chars < 900:
            return True
        # Señal secundaria: fragmentación extrema (>75% grupos con <=2 chars)
        grupos_pequenos = sum(1 for n in grupos_y.values() if n <= 2)
        if n_lineas > 30 and grupos_pequenos / n_lineas > 0.75:
            return True
        return False

    def chars_a_lineas(chars, pagina_y1, tolerancia_y=3.0, tolerancia_x=8.0):
        """Agrupa LTChar en líneas por Y y reconstruye texto con espacios."""
        if not chars:
            return []
        grupos = defaultdict(list)
        for c in chars:
            y_key = round(c.y0 / tolerancia_y) * tolerancia_y
            grupos[y_key].append(c)
        resultado = []
        for y, grupo in sorted(grupos.items(), key=lambda x: -x[0]):
            grupo.sort(key=lambda c: c.x0)
            texto = ""
            x_prev = None
            for c in grupo:
                if x_prev is not None and c.x0 - x_prev > tolerancia_x:
                    texto += " "
                texto += c.get_text()
                x_prev = c.x1
            texto = texto.strip()
            # v3.10e: normalizar guiones de separación silábica OCR
            texto = re.sub(r'([A-ZÁÉÍÓÚÜÑ])[_-]([A-ZÁÉÍÓÚÜÑ])', r'\1\2', texto)
            if len(texto) < 2:
                continue
            # Filtro: ratio de caracteres legibles
            chars_leg = sum(
                1 for ch in texto
                if ch.isprintable() and (
                    ch.isascii() or ch in
                    'áéíóúüñàèìòùçÁÉÍÓÚÜÑÀÈÌÒÙÇ·ºª€'
                )
            )
            if chars_leg / len(texto) < 0.65:
                continue
            resultado.append((pagina_y1 - y, texto))
        return resultado

    paginas_texto = []
    total_chars = 0
    paginas_filtradas = 0

    for num_pagina, pagina in enumerate(extract_pages(str(ruta)), 1):
        chars = []
        recoger_chars(pagina, chars)

        # v3.10: descartar páginas giradas antes de extraer texto
        if pagina_girada(chars):
            paginas_filtradas += 1
            log.debug(f"Página {num_pagina} descartada: girada o fragmentada")
            continue

        lineas = chars_a_lineas(chars, pagina.y1)

        if not lineas:
            paginas_filtradas += 1
            continue

        # lineas ya viene ordenada top-down desde chars_a_lineas
        # Reconstruir texto con detección de párrafos por salto vertical
        texto_pagina = []
        y_ant = None
        ALTURA_LINEA = 14  # puntos, estimación conservadora

        for y, texto_linea in lineas:
            if y_ant is not None and (y - y_ant) > ALTURA_LINEA * 1.8:
                texto_pagina.append("")  # línea en blanco = nuevo párrafo
            texto_pagina.append(texto_linea)
            y_ant = y

        contenido = "\n".join(texto_pagina).strip()
        if contenido:
            paginas_texto.append(
                f"\n{'─'*55}\n[Página {num_pagina}]\n{'─'*55}\n{contenido}"
            )
            total_chars += len(contenido)

    if total_chars < 100:
        log.error("El PDF no tiene capa de texto. Aplica primero el OCR.")
        raise PDFSinTextoError(
            f"PDF sin capa de texto suficiente (<100 chars): {ruta.name}. "
            "Aplica OCR antes de anonimizar (core.anon.ocr.ocr_pdf)."
        )

    log.info(f"Texto extraido: {total_chars:,} caracteres en "
             f"{len(paginas_texto)} paginas "
             f"({paginas_filtradas} paginas sin texto legible descartadas)")
    return "\n".join(paginas_texto)


def extraer_texto_docx(ruta: Path, log) -> str:
    try:
        import docx
    except ImportError as e:
        log.error("Instala python-docx: pip install python-docx")
        raise ImportError(
            "python-docx no está instalado. Instálalo con `pip install python-docx`."
        ) from e
    log.info(f"Extrayendo texto de DOCX: {ruta.name}")
    doc = docx.Document(str(ruta))
    texto = "\n".join(p.text for p in doc.paragraphs)
    if not texto.strip():
        log.error("El DOCX parece estar vacio o escaneado.")
        raise DocxVacioError(
            f"DOCX vacío o solo con imágenes: {ruta.name}. "
            "Si es escaneado, conviértelo primero a PDF y aplica OCR."
        )
    log.info(f"Texto extraido: {len(texto):,} caracteres")
    return texto


def extraer_texto(ruta: Path, log) -> str:
    ext = ruta.suffix.lower()
    if ext == ".pdf":
        return extraer_texto_pdf(ruta, log)
    elif ext == ".docx":
        return extraer_texto_docx(ruta, log)
    else:
        log.error(f"Formato no soportado: {ext}. Usa PDF o DOCX.")
        raise FormatoNoSoportadoError(
            f"Extensión no soportada: {ext!r}. Formatos válidos: .pdf, .docx."
        )


# ══════════════════════════════════════════════════════════════════════════════
# TIPO DE PROCEDIMIENTO (metadato descriptivo, no condiciona la anonimización)
# ══════════════════════════════════════════════════════════════════════════════

# Tipos de procedimiento disponibles
TIPOS_PROCEDIMIENTO = [
    "Juicio Ordinario",
    "Juicio Verbal",
    "Monitorio",
    "Diligencias Preliminares",
    "Diligencias Previas",
    "Otro",
]

# Patrones para detección automática del tipo en el texto
PATRONES_TIPO_PROC = [
    (r'procedimiento\s+ordinario|juicio\s+ordinario',          "Juicio Ordinario"),
    (r'procedimiento\s+verbal|juicio\s+verbal',                "Juicio Verbal"),
    (r'proceso\s+monitorio|juicio\s+monitorio|monitorio',      "Monitorio"),
    (r'diligencias\s+preliminares',                            "Diligencias Preliminares"),
    (r'diligencias\s+previas',                                 "Diligencias Previas"),
]


def detectar_tipo_procedimiento(texto: str) -> str:
    """Detecta automáticamente el tipo de procedimiento del texto."""
    import re
    texto_lower = texto[:3000].lower()
    for patron, tipo in PATRONES_TIPO_PROC:
        if re.search(patron, texto_lower):
            return tipo
    return "Juicio Ordinario"  # defecto más frecuente


def pedir_tipo_procedimiento(texto: str = "") -> str:
    """Detecta el tipo de procedimiento y pide confirmación al usuario."""
    import msvcrt
    detectado = detectar_tipo_procedimiento(texto) if texto else "Juicio Ordinario"

    print()
    print("  Tipo de procedimiento detectado: " + detectado)
    sys.stdout.write("  ¿Correcto? [S=si, N=elegir otro, defecto S]: ")
    sys.stdout.flush()

    try:
        c = msvcrt.getwch().upper()
        print(c)
    except Exception:
        c = input().strip().upper() or "S"

    if c == "N":
        print()
        print("  Selecciona el tipo de procedimiento:")
        for i, t in enumerate(TIPOS_PROCEDIMIENTO, 1):
            print(f"    {i}. {t}")
        print()
        try:
            opcion = input("  Numero (1-6): ").strip()
            idx = int(opcion) - 1
            if 0 <= idx < len(TIPOS_PROCEDIMIENTO):
                seleccionado = TIPOS_PROCEDIMIENTO[idx]
                if seleccionado == "Otro":
                    seleccionado = input("  Introduce el tipo: ").strip() or detectado
                return seleccionado
        except Exception:
            pass
        return detectado

    return detectado


# ══════════════════════════════════════════════════════════════════════════════
# DETECCION DE ENTIDADES
# ══════════════════════════════════════════════════════════════════════════════

# Indicadores para extraer nombres con contexto procesal
# (_TRAT y _NOMBRE definidos en la sección LISTA BLANCA, más arriba)
# Indicadores para extraer nombres con contexto procesal
# (_TRAT, _ILMO y _NOMBRE definidos en la sección LISTA BLANCA, más arriba)
PATRONES_CONTEXTO = [
    # Partes procesales: exigen ':' como separador para evitar captura en prosa narrativa
    # ("El demandante suscribió..." NO activa; "Demandante: DON ..." SÍ activa)
    (r'(?:demandante|ejecutante|querellante|denunciante|perjudicado|arrendador|comprador|trabajador)\s*:\s*' + _TRAT + _NOMBRE, "actor"),
    (r'(?:demandado|ejecutado|querellado|denunciado|investigado|arrendatario|vendedor)\s*:\s*' + _TRAT + _NOMBRE, "demandado"),
    (r'(?:procurador|procuradora)(?:\s+(?:de\s+(?:los?\s+)?tribunales))?\s*:\s*' + _TRAT + _NOMBRE, "procurador"),
    (r'(?:abogado|abogada|letrado|letrada)\s*:\s*' + _TRAT + _NOMBRE, "letrado"),
    (r'(?:magistrado|magistrada|juez|jueza)\s*:\s*' + _ILMO + _TRAT + _NOMBRE, "magistrado"),
    (r'(?:letrada?\s+de\s+la\s+adm(?:inistración|inistracion)?\.?\s+de\s+justicia)\s*:\s*' + _TRAT + _NOMBRE, "laj"),
    (r'(?:perito\s+judicial)\s*:\s*' + _NOMBRE, "perito"),
    # Campos con etiqueta explícita — captura solo el valor tras '.-:' o ':'
    # hasta fin de línea para no consumir el campo siguiente
    (r'(?:nombre\s+del?\s+procurador)\s*[\.\-]*:\s*(' + _WORD + r'(?:\s+' + _WORD + r'){1,3})(?:\s*$|\s*\n)', "procurador"),
    (r'(?:nombre\s+del?\s+letrado)\s*[\.\-]*:\s*(' + _WORD + r'(?:\s+' + _WORD + r'){1,3})(?:\s*$|\s*\n)', "letrado"),
    (r'(?:nombre\s+del?\s+representado)\s*[\.\-]*:\s*(' + _WORD + r'(?:\s+' + _WORD + r'){1,3})(?:\s*$|\s*\n)', "demandado"),
    (r'(?:notificacion\s+al\s+procurador)\s*[\.\-]*\s+(' + _WORD + r'(?:\s+' + _WORD + r'){1,3})(?:\s*$|\s*[\.\-])', "procurador"),
    (r'(?:signat\s+per|firmado\s+por|fdo\.?)\s+' + _NOMBRE, "nombre"),
    (r'(?:fiscal)\s*:\s*' + _TRAT + _NOMBRE, "fiscal"),
    (r'(?:testigo)\s*:\s*' + _TRAT + _NOMBRE, "testigo"),
    # ── Equivalentes catalanes (cédulas, oficis de requeriment, exhortos) ──
    # Partes procesales en catalán
    (r'(?:demandant|querellant|denunciant|perjudicat)\s*:\s*' + _TRAT + _NOMBRE, "actor"),
    (r'(?:demandat|querellat|denunciat|investigat|acusat)\s*:\s*' + _TRAT + _NOMBRE, "demandado"),
    (r'(?:procurador|procuradora)(?:\s+dels?\s+tribunals)?\s*:\s*' + _TRAT + _NOMBRE, "procurador"),
    (r'(?:advocat|advocada|lletrat|lletrada)\s*:\s*' + _TRAT + _NOMBRE, "letrado"),
    (r'(?:jutge|jutgessa|magistrat|magistrada)\s*:\s*' + _ILMO + _TRAT + _NOMBRE, "magistrado"),
    (r'(?:lletrat?\s+de\s+l\'administraci[oó]\s+de\s+just[ií]cia|secretari\s+judicial)\s*:\s*' + _TRAT + _NOMBRE, "laj"),
    # Campos de cédula/ofici en catalán
    (r'(?:nom\s+del?\s+procurador)\s*[\.\-]*:\s*(' + _WORD + r'(?:\s+' + _WORD + r'){1,3})(?:\s*$|\s*\n)', "procurador"),
    (r'(?:nom\s+del?\s+lletrat)\s*[\.\-]*:\s*(' + _WORD + r'(?:\s+' + _WORD + r'){1,3})(?:\s*$|\s*\n)', "letrado"),
    (r'(?:nom\s+del?\s+representat)\s*[\.\-]*:\s*(' + _WORD + r'(?:\s+' + _WORD + r'){1,3})(?:\s*$|\s*\n)', "demandado"),
    (r'(?:notificaci[oó]\s+al\s+procurador)\s*[\.\-]*\s+(' + _WORD + r'(?:\s+' + _WORD + r'){1,3})(?:\s*$|\s*[\.\-])', "procurador"),
    # Campos del ofici de requeriment (NIP) en catalán
    (r'(?:1r\s+cognom|2n\s+cognom)\s*:\s*(' + _WORD + r'(?:\s+' + _WORD + r'){0,2})(?:\s*$|\s*\n)', "demandado"),
    (r'(?:nom\s+del\s+pare|nom\s+de\s+la\s+mare)\s*:\s*(' + _WORD + r'(?:\s+' + _WORD + r'){0,2})(?:\s*$|\s*\n)', "nombre"),
]

PATRON_NOMBRE_MAYUSCULAS = re.compile(
    r'\b([A-ZÁÉÍÓÚÜÑÀÈÌÒÙÇ]{2,}(?:\s+[A-ZÁÉÍÓÚÜÑÀÈÌÒÙÇ]{2,}){1,4})\b'
)

PATRONES_REGEX = [
    (r'\bES\s*\d{2}[\s]?\d{4}[\s]?\d{4}[\s]?\d{2}[\s]?\d{10}\b',    "IBAN"),
    (r'\b[A-Z]{2}\d{2}(?:[\s]?\d{4}){3,5}\b',                        "IBAN"),
    (r'\b\d{8}[A-ZÁÉÍÓÚÜÑ]\b',                                        "DNI"),
    (r'\b[XYZ]\d{7}[A-ZÁÉÍÓÚÜÑ]\b',                                   "NIE"),
    (r'\b[ABCDEFGHJKLMNPQRSUVW]\d{7}[0-9A-J]\b',                      "NIF"),
    (r'\b(?:\+34[\s.-]?)?[6789]\d{2}[\s.-]?\d{3}[\s.-]?\d{3}\b',     "TELEFONO"),
    (r'\b(?:\+34[\s.-]?)?9[0-9]{2}[\s.-]?\d{3}[\s.-]?\d{3}\b',       "TELEFONO"),
    (r'\b[\w.+-]+@[\w-]+\.[\w.]+\b',                                   "EMAIL"),
    (r'\b\d{20}\b',                                                     "CUENTA"),
    (r'\b\d{16,19}\b',                                                  "CUENTA"),
]


def _offsets_nombre_limpio(captura: str, nombre: str, base_start: int) -> tuple[int, int] | None:
    """Localiza el ``nombre`` ya limpiado dentro de la ``captura`` original.

    Devuelve ``(inicio_abs, fin_abs)`` o ``None`` si el nombre limpio no es un
    substring literal de la captura (entonces el caller usa el span completo).
    Resuelve el bug §3: tras ``limpiar_nombre`` el nombre puede ser más corto
    que el grupo capturado; usar ``m.end(1)`` borraría las palabras recortadas
    (p. ej. la siguiente parte procesal en documentos sin puntuación).
    """
    if not nombre:
        return None
    idx = captura.find(nombre)
    if idx == -1:
        return None
    return base_start + idx, base_start + idx + len(nombre)


def limpiar_nombre(nombre: str) -> str:
    """Limpia un nombre detectado."""
    nombre = nombre.strip()
    # Quitar palabras excluidas del final
    palabras = nombre.split()
    while palabras and palabras[-1].upper() in PALABRAS_EXCLUIDAS:
        palabras.pop()
    while palabras and palabras[0].upper() in PALABRAS_EXCLUIDAS:
        palabras.pop(0)
    return " ".join(palabras)


def es_empresa(nombre: str) -> bool:
    """Detecta si un nombre corresponde a una empresa."""
    return bool(SUFIJOS_EMPRESA.search(nombre))


def es_nombre_valido(nombre: str) -> bool:
    """Verifica que una secuencia de mayusculas sea un nombre valido.

    v3.9: filtro de coherencia léxica combinado para rechazar ruido OCR
    de páginas giradas (fragmentos como "JUEJ IOY", "NI IDIC TV", etc.):
    - Bigramas de consonantes imposibles en español/catalán
    - Proporción excesiva de palabras muy cortas (≤3 chars) en el nombre
    - Palabras largas sin vocal
    """
    palabras = nombre.split()
    if not palabras:
        return False
    if any(p.upper() in PALABRAS_EXCLUIDAS for p in palabras):
        return False
    if len(palabras) == 1 and len(palabras[0]) < 5:
        return False
    if all(len(p) <= 3 for p in palabras):
        return False

    # Bigramas de consonantes imposibles en español/catalán/nombres propios
    BIGRAMAS_IMPOSIBLES = {
        'HN','NH','NJ','NW','NN','HH','WN','WL','JJ','WW',
        'LN','LJ','VL','VN','VJ','BN','BJ','TJ','DJ','FJ',
        'GJ','PJ','KJ','ZJ','XJ','QJ','QN','QL','QW',
    }
    for p in palabras:
        p_upper = p.upper()
        for i in range(len(p_upper) - 1):
            if p_upper[i:i+2] in BIGRAMAS_IMPOSIBLES:
                return False

    # Palabras largas sin ninguna vocal → ruido OCR
    VOCALES = set('AEIOUÁÉÍÓÚÜaeiouáéíóúü')
    for p in palabras:
        if len(p) >= 4 and not any(c in VOCALES for c in p):
            return False

    # Si la mayoría de palabras son muy cortas (≤3) y hay muchas → ruido OCR
    # Nombres reales tienen al menos una palabra de 4+ chars
    cortas = sum(1 for p in palabras if len(p) <= 3)
    if len(palabras) >= 3 and cortas / len(palabras) >= 0.75:
        return False

    # v3.10: rechazar fragmentos partidos por OCR.
    # Un fragmento partido tiene palabras que empiezan o terminan con
    # 2+ consonantes seguidas sin vocal adyacente (ej: "LEGI", "CACIÓ" cortado,
    # "MPLIM", "CCIÓ"). Señal: palabra de 4+ chars donde los 2 primeros O los
    # 2 últimos chars son todos consonantes y no forman prefijo/sufijo español.
    VOCALES = set('AEIOUÁÉÍÓÚÜaeiouáéíóúü')
    # Prefijos consonánticos válidos en español/catalán y en nombres propios
    # internacionales frecuentes en documentos judiciales españoles
    PREFIJOS_VALIDOS = {
        'TR','PR','BR','CR','DR','FR','GR','PL','BL','CL','FL','GL','SL',
        'SH','KH','GH','ZH',  # nombres árabes/persas/chinos
        'VL','VN','DM','DH',  # nombres eslavos/iranios
        'KR','KL','KN','KW',  # nombres nórdicos/eslavos (Kristian, Klaus...)
        'WR','WL','WN',        # nombres galeses/ingleses
        'TH','PH',             # nombres griegos/anglosajones
        'CH','LL',             # dígrafos españoles (Chacón, Llorente...)
    }
    # Sufijos consonánticos válidos (incluyendo partículas y apellidos comunes)
    SUFIJOS_VALIDOS = {
        'ND','NT','RT','ST','LT','XT','PT','CT','NS','LS','RS','DS',
        'RD','LD','NK','SK','RK','LK','RM','LM','RN','LN',
        'VD','JD','AD','ED','ID','OD','UD',  # -ad/-ed final iraní/árabe
        'AN','EN','IN','ON','UN',             # partículas (-van, -den, etc.)
        'ER','AR','OR','IR','UR',             # apellidos en -er/-ar
        'EL','AL','IL','OL','UL',             # El-, Al- inicial/final
        'EV','OV','EZ',                       # apellidos eslavos/hispanos
        'ZA','HA','HR','HI','HE','SH',             # nombres persas/árabes (-za, -hr, -sh)
    }
    # Si todas las palabras son cortas (<=4 chars), al menos una debe
    # tener >=5 para ser un nombre real. Ruido OCR como "JUEJ IOY",
    # "RITA LE", "EST GADO" tiene todas las palabras muy cortas.
    # Excepción: nombres de una sola palabra de 4 chars son válidos (RITA).
    if len(palabras) >= 2 and all(len(p) <= 4 for p in palabras):
        return False

    for p in palabras:
        if len(p) < 5:  # palabras cortas (<=4): VAN, DER, DEL, IVA...
            continue
        inicio2 = p[:2].upper()
        fin2    = p[-2:].upper()
        inicio_ok = any(c in VOCALES for c in inicio2) or inicio2 in PREFIJOS_VALIDOS
        fin_ok    = any(c in VOCALES for c in fin2)    or fin2  in SUFIJOS_VALIDOS
        if not inicio_ok or not fin_ok:
            return False

    return True


# ══════════════════════════════════════════════════════════════════════════════
# MAPA DE ENTIDADES
# ══════════════════════════════════════════════════════════════════════════════

class MapaEntidades:
    """Gestiona el mapa nombre_real -> etiqueta."""

    def __init__(
        self,
        protegidos: set | None = None,
        *,
        mapa: dict | None = None,
        mapa_inverso: dict | None = None,
        contadores: dict | None = None,
    ):
        """Crea un mapa, opcionalmente pre-poblado.

        FeesDefender usa los argumentos opcionales para reconstruir un
        ``MapaEntidades`` existente desde ``_mapa_caso.json`` (mapa compartido
        por caso). Imprescindible cargar también ``contadores`` para evitar
        colisiones de etiquetas (si el mapa tenía 5 entidades pero los
        contadores arrancan en 0, el sexto registro intentaría volver a
        crear ``[NOMBRE]`` cuando ya existe).
        """
        self.mapa = dict(mapa) if mapa else {}                       # nombre_real -> etiqueta
        self.mapa_inverso = dict(mapa_inverso) if mapa_inverso else {}  # etiqueta -> nombre_real
        self.contadores = defaultdict(int, contadores or {})
        self.dudosos = []        # [(fragmento, contexto)]
        self.protegidos = set(protegidos) if protegidos else set()  # nombres que NO se anonimizan

    def _siguiente_etiqueta(self, tipo: str) -> str:
        self.contadores[tipo] += 1
        n = self.contadores[tipo]
        return f"[{tipo}_{n}]" if n > 1 else f"[{tipo}]"

    def registrar(self, nombre: str, tipo_rol: str) -> str:
        """Registra un nombre y devuelve su etiqueta.

        Corrección v3.3: antes de crear una entrada nueva, comprueba si el
        nombre es variante parcial de uno ya registrado (o viceversa), y en
        ese caso reutiliza la etiqueta existente para evitar duplicados como
        [NOMBRE] → "ANA GARCIA" y [NOMBRE_5] → "ANA GARCIA MARTINEZ".
        """
        nombre = limpiar_nombre(nombre)
        if not nombre or not es_nombre_valido(nombre):
            return nombre

        # Coincidencia exacta
        if nombre in self.mapa:
            return self.mapa[nombre]

        # Coincidencia parcial: el nombre nuevo es subconjunto de uno ya registrado
        # o contiene a uno ya registrado (misma persona, distinta forma de escritura)
        nombre_upper = nombre.upper()
        for registrado, etiqueta in self.mapa.items():
            reg_upper = registrado.upper()
            # Solo comparar cadenas que parecen nombres (no datos estructurados)
            if not re.match(r'^\[', registrado):
                if nombre_upper in reg_upper or reg_upper in nombre_upper:
                    # Usar la etiqueta del nombre más largo (más completo)
                    if len(nombre) > len(registrado):
                        # El nuevo es más largo: actualizar el mapa inverso
                        self.mapa[nombre] = etiqueta
                        self.mapa_inverso[etiqueta] = nombre  # reemplazar por versión más completa
                    else:
                        self.mapa[nombre] = etiqueta
                    return etiqueta

        # Determinar tipo de etiqueta
        if es_empresa(nombre):
            tipo_etiqueta = "EMPRESA"
        else:
            tipo_etiqueta = ETIQUETAS_PARTE.get(tipo_rol, "NOMBRE")

        etiqueta = self._siguiente_etiqueta(tipo_etiqueta)
        self.mapa[nombre] = etiqueta
        self.mapa_inverso[etiqueta] = nombre
        return etiqueta

    def registrar_dato(self, valor: str, tipo: str) -> str:
        """Registra un dato no nominal (DNI, IBAN, etc.)."""
        if valor in self.mapa:
            return self.mapa[valor]
        etiqueta = self._siguiente_etiqueta(tipo)
        self.mapa[valor] = etiqueta
        self.mapa_inverso[etiqueta] = valor
        return etiqueta

    def anadir_dudoso(self, fragmento: str, contexto: str):
        self.dudosos.append((fragmento, contexto))

    def exportar_json(self, ruta: Path):
        """Persiste el mapa con todos sus campos.

        Formato extendido respecto al original: incluye ``mapa_directo``,
        ``contadores`` y ``protegidos`` para permitir reconstrucción completa
        con ``cargar_json``. Sigue siendo compatible hacia atrás: cualquier
        consumidor del campo ``"mapa"`` (etiqueta → valor real) sigue
        funcionando sin cambios.
        """
        datos = {
            "generado":     datetime.now().isoformat(),
            "mapa":         self.mapa_inverso,                       # etiqueta → valor real (legacy)
            "mapa_directo": self.mapa,                                # valor real → etiqueta
            "contadores":   dict(self.contadores),
            "protegidos":   sorted(self.protegidos),
        }
        ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def cargar_json(cls, ruta: Path) -> "MapaEntidades":
        """Reconstruye un ``MapaEntidades`` desde un JSON exportado.

        Tolera ficheros antiguos del Anonimizador original (que solo tenían
        ``mapa``: etiqueta → valor): si falta ``mapa_directo``, se recalcula
        invirtiendo. Si faltan ``contadores`` se infieren a partir de los
        sufijos numéricos de las etiquetas existentes.
        """
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        mapa_inverso = datos.get("mapa") or {}
        mapa_directo = datos.get("mapa_directo") or {v: k for k, v in mapa_inverso.items()}

        contadores = datos.get("contadores")
        if contadores is None:
            # Inferir desde las etiquetas: [TIPO] → 1, [TIPO_N] → N
            contadores = defaultdict(int)
            patron = re.compile(r"^\[([A-Z_]+?)(?:_(\d+))?\]$")
            for etiqueta in mapa_inverso:
                m = patron.match(etiqueta)
                if not m:
                    continue
                tipo = m.group(1)
                n = int(m.group(2)) if m.group(2) else 1
                if n > contadores[tipo]:
                    contadores[tipo] = n

        return cls(
            protegidos=set(datos.get("protegidos", [])),
            mapa=mapa_directo,
            mapa_inverso=mapa_inverso,
            contadores=dict(contadores),
        )


# ══════════════════════════════════════════════════════════════════════════════
# ANONIMIZACION
# ══════════════════════════════════════════════════════════════════════════════

def anonimizar_con_presidio(texto: str, mapa: MapaEntidades, log) -> str:
    try:
        # FeesDefender 2026-05-07: motor cargado vía singleton.
        # El original creaba un AnalyzerEngine local en cada llamada (los
        # modelos spaCy de los 3 idiomas pesan ~1.5 GB y tardaban 20-40 s
        # en cargarse). Con el singleton de ``core.anon.nlp_engine``, la
        # primera llamada paga la carga y las siguientes son instantáneas.
        from core.anon.nlp_engine import get_analyzer

        log.info("Obteniendo motor Presidio (singleton)...")
        analyzer = get_analyzer()

        entidades = ["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "IBAN_CODE", "NRP"]

        resultados = analyzer.analyze(
            text=texto,
            language="es",
            entities=entidades,
            score_threshold=0.35,  # threshold bajo para datos estructurados
        )

        log.info(f"Presidio: {len(resultados)} entidades detectadas")

        # Reemplazar manualmente usando el mapa
        resultados_ordenados = sorted(resultados, key=lambda x: x.start, reverse=True)
        texto_lista = list(texto)

        for resultado in resultados_ordenados:
            fragmento = texto[resultado.start:resultado.end]
            # Saltar si el fragmento esta protegido
            if esta_protegido(fragmento, mapa.protegidos):
                continue
            if resultado.entity_type == "PERSON":
                # v3.3: score alto para PERSON
                if resultado.score < 0.65:
                    continue
                # v3.10: limpiar prefijos/sufijos de contexto ANTES de filtrar
                # por minúsculas, porque "Nombre Saydou Balde" tiene minúsculas
                # pero es un nombre válido precedido de contexto.
                _PREFIJOS_CONTEXTO = {
                    'NOMBRE', 'NOM', 'SEXE', 'SEXO', 'FECHA', 'DATA',
                    'TIPO', 'TIPUS', 'CLASE', 'CLASSE', 'RESULTADO',
                    'REPRESENTADO', 'REPRESENTAT', 'INVESTIGAT', 'INVESTIGADO',
                    'DIRECCIÓN', 'DIRECCION', 'ADREÇA', 'ADRESA',
                    'DEL', 'DE', 'LA', 'EL', 'LAS', 'LOS',
                }
                palabras_frag = fragmento.strip().split()
                # Quitar palabras del inicio/final que son prefijos de contexto
                while palabras_frag and palabras_frag[0].upper() in _PREFIJOS_CONTEXTO:
                    palabras_frag.pop(0)
                while palabras_frag and palabras_frag[-1].upper() in _PREFIJOS_CONTEXTO:
                    palabras_frag.pop()
                # Cortar en separador de campo; mantener partículas de apellido
                # compuesto (DE LORENZO, VAN DER, etc.) si la siguiente palabra
                # también empieza en mayúscula y no es un separador.
                _SEP_CAMPO = {
                    'NOMBRE','NOM','FECHA','DATA','DIRECCIÓN','DIRECCION',
                    'ADREÇA','TELEFONO','TELÉFONO','CLASE','CLASSE',
                }
                _PARTICULAS = {'DE','DEL','VAN','VON','DER','DI','DU','LA','LAS','LOS'}
                palabras_cortadas = []
                i = 0
                while i < len(palabras_frag):
                    pw = palabras_frag[i]
                    pw_up = pw.upper()
                    # Separador de campo → cortar aquí
                    if pw_up in _SEP_CAMPO:
                        break
                    # Partícula: mantener si la siguiente palabra es otro nombre
                    if pw_up in _PARTICULAS:
                        sig = palabras_frag[i+1] if i+1 < len(palabras_frag) else ''
                        sig_up = sig.upper() if sig else ''
                        if sig and sig[0].isupper() and sig_up not in _SEP_CAMPO and sig_up not in PALABRAS_EXCLUIDAS:
                            palabras_cortadas.append(pw)
                            i += 1
                            continue
                        else:
                            break
                    palabras_cortadas.append(pw)
                    i += 1
                if palabras_cortadas:
                    palabras_frag = palabras_cortadas
                # Cortar también en separadores de campo OCR
                texto_frag = " ".join(palabras_frag)
                for sep in ['Dirección', 'Direccion', 'Adreça', 'Telef', 'NIG', 'DNI',' С.', ' C.']:
                    if sep in texto_frag:
                        texto_frag = texto_frag[:texto_frag.index(sep)].strip()
                palabras_frag = texto_frag.split()
                fragmento_limpio = " ".join(palabras_frag).strip()
                if not fragmento_limpio:
                    continue
                # Ahora filtrar: si queda texto en minúsculas sin prefijo
                # que lo justifique, es texto narrativo → descartar
                if re.search(r'[a-záéíóúüñ]', fragmento_limpio):
                    # Excepción: nombres mixtos (Mirmohsen, Javad...) con
                    # al menos una palabra que empiece en mayúscula
                    palabras_limpias = fragmento_limpio.split()
                    if not any(p[0].isupper() for p in palabras_limpias if p):
                        continue  # todo en minúscula → narrativo
                # v3.10: validar con es_nombre_valido() para rechazar ruido
                # OCR que Presidio clasifica como PERSON (JUEJ IOY, ETOTTE IVA)
                if not es_nombre_valido(fragmento_limpio):
                    continue
                etiqueta = mapa.registrar(fragmento_limpio, "nombre")
            elif resultado.entity_type == "IBAN_CODE":
                etiqueta = mapa.registrar_dato(fragmento, "IBAN")
            elif resultado.entity_type == "EMAIL_ADDRESS":
                etiqueta = mapa.registrar_dato(fragmento, "EMAIL")
            elif resultado.entity_type == "PHONE_NUMBER":
                # v3.9: validar que es un número de teléfono español real.
                # Presidio confunde referencias policiales (792136/2023),
                # códigos de unidad funcional (0812143001), NIGs fragmentados
                # y fechas con números de teléfono.
                fragmento_limpio = re.sub(r'[\s.\-/]', '', fragmento)
                es_tel_valido = bool(re.fullmatch(
                    r'(?:\+34)?[6789]\d{8}',
                    fragmento_limpio
                ))
                if not es_tel_valido:
                    continue  # descartar falso positivo
                etiqueta = mapa.registrar_dato(fragmento, "TELEFONO")
            elif resultado.entity_type == "NRP":
                etiqueta = mapa.registrar_dato(fragmento, "DNI")
            else:
                etiqueta = f"[{resultado.entity_type}]"

            texto_lista[resultado.start:resultado.end] = list(etiqueta)

        return "".join(texto_lista)

    except ImportError:
        log.warning("Presidio no instalado. Fase 1 omitida. Instala: pip install presidio-analyzer presidio-anonymizer")
        return texto
    except Exception as e:
        log.warning(f"Presidio fallo inesperadamente (Fase 1 omitida): {e}")
        log.warning("Verifica que los modelos spaCy esten instalados: python -m spacy download es_core_news_lg")
        return texto


_PREFIJOS_NOMBRE_CTX = {
    'NOMBRE','NOM','SEXE','SEXO','FECHA','DATA','TIPO','TIPUS',
    'CLASE','CLASSE','RESULTADO','REPRESENTADO','REPRESENTAT',
    'INVESTIGAT','INVESTIGADO','DIRECCIÓN','DIRECCION','ADREÇA','ADRESA',
}

def limpiar_prefijos_nombre(nombre: str) -> str:
    """Elimina prefijos/sufijos de contexto del nombre capturado (v3.10e)."""
    palabras = nombre.strip().split()
    while palabras and palabras[0].upper() in _PREFIJOS_NOMBRE_CTX:
        palabras.pop(0)
    while palabras and palabras[-1].upper() in _PREFIJOS_NOMBRE_CTX:
        palabras.pop()
    return " ".join(palabras).strip()


def anonimizar_por_contexto(texto: str, mapa: MapaEntidades, log) -> str:
    """Detecta nombres segun contexto procesal, respetando protegidos.

    Corrección v3.2: antes de llamar a replace() se comprueba que el nombre
    a sustituir no sea ya una etiqueta (empieza por '['), evitando etiquetas
    anidadas cuando la Fase 1 ya procesó la misma entidad.
    v3.10e: aplicar limpiar_prefijos_nombre() para eliminar contexto capturado.
    """
    detectados = 0
    for patron_str, rol in PATRONES_CONTEXTO:
        patron = re.compile(patron_str, re.IGNORECASE | re.MULTILINE)
        for m in patron.finditer(texto):
            nombre = limpiar_prefijos_nombre(limpiar_nombre(m.group(1)))
            if not nombre or not es_nombre_valido(nombre):
                continue
            if esta_protegido(nombre, mapa.protegidos):
                continue
            # No re-procesar si ya es una etiqueta
            if nombre.startswith('[') and nombre.endswith(']'):
                continue
            etiqueta = mapa.registrar(nombre, rol)
            if etiqueta != nombre:
                # §3: recortar el span al nombre limpio (no al grupo completo)
                # para no borrar palabras que limpiar_nombre haya descartado.
                off = _offsets_nombre_limpio(m.group(1), nombre, m.start(1))
                ini, fin = off if off is not None else (m.start(1), m.end(1))
                texto = texto[:ini] + etiqueta + texto[fin:]
                # Reiniciar búsqueda desde el inicio tras modificar el texto
                break
            detectados += 1
        # Re-ejecutar el patrón si hubo modificaciones
        else:
            continue
        patron2 = re.compile(patron_str, re.IGNORECASE | re.MULTILINE)
        for m in patron2.finditer(texto):
            nombre = limpiar_nombre(m.group(1))
            if not nombre or not es_nombre_valido(nombre): continue
            if esta_protegido(nombre, mapa.protegidos): continue
            if nombre.startswith('[') and nombre.endswith(']'): continue
            etiqueta = mapa.registrar(nombre, rol)
            if etiqueta != nombre:
                off = _offsets_nombre_limpio(m.group(1), nombre, m.start(1))
                ini, fin = off if off is not None else (m.start(1), m.end(1))
                texto = texto[:ini] + etiqueta + texto[fin:]
                detectados += 1
    log.info(f"Deteccion contextual: {detectados} entidades")
    return texto


def anonimizar_mayusculas(texto: str, mapa: MapaEntidades, log) -> str:
    """Detecta secuencias de mayusculas, respetando protegidos.

    Corrección v3.2: la guarda contra etiquetas ya insertadas se amplía para
    cubrir etiquetas con sufijo numérico ([DEMANDANTE_2]) y subcadenas de
    etiquetas que el patron de mayúsculas podría capturar parcialmente.
    """

    def reemplazar(m):
        nombre = m.group(1).strip()
        if not es_nombre_valido(nombre):
            return nombre
        # Saltar si es o forma parte de una etiqueta ya insertada
        if nombre.startswith('[') and nombre.endswith(']'):
            return nombre
        if re.fullmatch(r'[A-Z_0-9]+', nombre):  # interior de etiqueta
            return nombre
        if esta_protegido(nombre, mapa.protegidos):
            return nombre
        etiqueta = mapa.registrar(nombre, "nombre")
        return etiqueta

    texto_nuevo = PATRON_NOMBRE_MAYUSCULAS.sub(reemplazar, texto)
    log.info("Deteccion mayusculas completada")
    return texto_nuevo


def aplicar_regex(texto: str, mapa: MapaEntidades, log) -> str:
    """Aplica patrones regex para datos estructurados.

    Corrección v3.2: los matches se recopilan sobre el texto *original* de cada
    pasada y se sustituyen por offset en orden inverso, evitando que las
    mutaciones sucesivas desplacen posiciones y dejen ocurrencias sin anonimizar.
    """
    detectados = 0
    for patron_str, tipo in PATRONES_REGEX:
        patron = re.compile(patron_str, re.IGNORECASE)
        # Recopilar todos los matches sobre el texto actual (inmutable en esta pasada)
        matches = [
            m for m in patron.finditer(texto)
            if not (m.group(0).startswith('[') and m.group(0).endswith(']'))
        ]
        # Sustituir en orden inverso para preservar offsets
        for m in reversed(matches):
            valor = m.group(0)
            # §19: el NIG (19 dígitos compactos) no es PII bancaria sino un
            # identificador procesal público. Si la captura CUENTA/IBAN viene
            # precedida del rótulo "NIG", no anonimizar.
            if tipo in ("CUENTA", "IBAN"):
                prefijo = texto[max(0, m.start() - 8):m.start()].upper()
                if "NIG" in prefijo:
                    continue
            etiqueta = mapa.registrar_dato(valor, tipo)
            texto = texto[:m.start()] + etiqueta + texto[m.end():]
            detectados += 1
    log.info(f"Regex: {detectados} entidades detectadas")
    return texto


# ══════════════════════════════════════════════════════════════════════════════
# MODO REVISION INTERACTIVO
# ══════════════════════════════════════════════════════════════════════════════

def revisar_interactivo(texto: str, mapa: MapaEntidades, log) -> str:
    """Muestra fragmentos dudosos y permite al usuario corregirlos.
    
    Mejoras v3.1:
    - Opcion [7] para introducir un rol personalizado
    - Propagacion automatica: si confirmas un fragmento, se sustituye
      en TODAS sus apariciones y se excluye de futuras preguntas
    """
    print("\n" + "="*55)
    print("  MODO REVISION")
    print("  Revisando fragmentos que podrian contener datos personales...")
    print("  Nota: al confirmar un fragmento se aplicara a todas sus")
    print("  apariciones en el documento automaticamente.")
    print("="*55)

    patron_sospechoso = re.compile(
        r'\b([A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?)\b'
    )

    # Recopilar todos los fragmentos unicos pendientes de revision
    fragmentos_pendientes = []
    vistos = set()
    for m in patron_sospechoso.finditer(texto):
        fragmento = m.group(1)
        if fragmento in vistos:
            continue
        vistos.add(fragmento)
        if fragmento in mapa.mapa:
            continue
        if esta_protegido(fragmento, mapa.protegidos):
            continue
        palabras = fragmento.split()
        if any(p.upper() in PALABRAS_EXCLUIDAS for p in palabras):
            continue
        fragmentos_pendientes.append(fragmento)

    total = len(fragmentos_pendientes)
    print(f"\n  Total de fragmentos a revisar: {total}")

    # Conjunto de fragmentos ya confirmados como NO personales (ignorar)
    ignorados = set()

    fragmentos_revisados = 0

    for i, fragmento in enumerate(fragmentos_pendientes, 1):
        # Si ya fue anonimizado en una iteracion anterior (propagacion)
        if fragmento in mapa.mapa:
            continue
        # Si es un operador juridico protegido
        if esta_protegido(fragmento, mapa.protegidos):
            continue
        # Si fue marcado como ignorado
        if fragmento in ignorados:
            continue

        # Contar apariciones en el texto actual
        n_apariciones = texto.count(fragmento)

        # Mostrar contexto de la primera aparicion
        pos = texto.find(fragmento)
        inicio = max(0, pos - 60)
        fin = min(len(texto), pos + len(fragmento) + 60)
        contexto = texto[inicio:fin].replace('\n', ' ')

        print(f"\n  [{i}/{total}] Fragmento: \"{fragmento}\"")
        print(f"  Apariciones en documento: {n_apariciones}")
        print(f"  Contexto: ...{contexto}...")
        print()
        print("  [1] Actor / Demandante / Denunciante")
        print("  [2] Demandado / Investigado / Denunciado")
        print("  [3] Procurador")
        print("  [4] Letrado / Abogado")
        print("  [5] Empresa / Persona juridica")
        print("  [6] No es un dato personal (ignorar siempre)")
        print("  [7] Rol personalizado")
        print("  [Enter] Saltar (no anonimizar ahora)")

        respuesta = input("  Seleccion: ").strip()

        roles_predefinidos = {
            "1": "actor",
            "2": "demandado",
            "3": "procurador",
            "4": "letrado",
            "5": "empresa",
        }

        if respuesta == "6":
            # Marcar como ignorado — no se volvera a preguntar
            ignorados.add(fragmento)
            print(f"  -> Ignorado (no se volvera a preguntar)")

        elif respuesta == "7":
            # Rol personalizado
            rol_custom = input("  Escribe el rol (ej: ARRENDADOR, VICTIMA, FIADOR): ").strip().upper()
            if rol_custom:
                # Corrección v3.2: usar registrar_dato para pasar por _siguiente_etiqueta
                # correctamente y evitar colisión si el mismo rol se usa más de una vez.
                etiqueta = mapa.registrar_dato(fragmento, rol_custom)
                # Propagar a todas las apariciones
                texto = texto.replace(fragmento, etiqueta)
                print(f"  -> Anonimizado como {etiqueta} ({n_apariciones} aparicion/es)")
                fragmentos_revisados += 1
            else:
                print("  -> Rol vacio. Fragmento saltado.")

        elif respuesta in roles_predefinidos:
            rol = roles_predefinidos[respuesta]
            etiqueta = mapa.registrar(fragmento, rol)
            # Propagar a TODAS las apariciones del documento
            texto = texto.replace(fragmento, etiqueta)
            print(f"  -> Anonimizado como {etiqueta} ({n_apariciones} aparicion/es sustituidas)")
            fragmentos_revisados += 1

        else:
            # Enter u opcion no reconocida: saltar sin registrar
            print("  -> Saltado")

    log.info(f"Revision interactiva: {fragmentos_revisados} fragmentos confirmados")
    print(f"\n  Revision completada.")
    print(f"  Fragmentos anonimizados: {fragmentos_revisados}")
    print(f"  Fragmentos ignorados:    {len(ignorados)}")
    return texto


# ══════════════════════════════════════════════════════════════════════════════
# VALIDACION DE CALIDAD
# ══════════════════════════════════════════════════════════════════════════════


def revisar_interactivo_con_captura(texto: str, mapa: MapaEntidades, log) -> tuple:
    """Como revisar_interactivo pero captura las decisiones del usuario."""
    fragmentos = []
    # Iterar directamente el mapa de entidades detectadas
    for etiqueta, valor_real in list(mapa.mapa.items()):
        if etiqueta not in texto:
            continue
        contexto = ""
        pos = texto.find(etiqueta)
        if pos >= 0:
            contexto = texto[max(0, pos-60):pos+len(etiqueta)+50].replace("\n", " ")
        print(f"\n  {etiqueta} → {valor_real!r}")
        print(f"  Contexto: ...{contexto}...")
        resp = input("  ¿Mantener anonimizado? (s/n, defecto s): ").strip().lower()
        decision = "confirmado" if resp != "n" else "rechazado"
        if resp == "n":
            texto = texto.replace(etiqueta, valor_real)
            del mapa.mapa[etiqueta]
            log.info(f"Revision: rechazado {etiqueta} = {valor_real!r}")
        else:
            log.info(f"Revision: confirmado {etiqueta} = {valor_real!r}")
        fragmentos.append({
            "etiqueta": etiqueta,
            "valor": valor_real,
            "decision": decision,
            "contexto": contexto[:100],
        })
    return texto, fragmentos


def guardar_dudas(fragmentos: list, ruta_pdf: Path, tipo_proc: str):
    """Añade las dudas de esta sesión al fichero central dudas_acumuladas.json."""
    if not fragmentos:
        return
    import json as _json
    from datetime import datetime

    # Buscar el fichero central subiendo desde la carpeta del PDF
    carpeta = ruta_pdf.parent
    ruta_dudas = None
    for _ in range(6):
        candidato = carpeta / "_herramientas" / "dudas_acumuladas.json"
        if candidato.exists():
            ruta_dudas = candidato
            break
        candidato2 = carpeta / "dudas_acumuladas.json"
        if candidato2.exists():
            ruta_dudas = candidato2
            break
        carpeta = carpeta.parent

    # Si no encontramos el fichero, intentar crearlo en _herramientas del Anonimizador
    if ruta_dudas is None:
        carpeta = ruta_pdf.parent
        for _ in range(6):
            candidato = carpeta / "_herramientas"
            if candidato.exists() and candidato.is_dir():
                ruta_dudas = candidato / "dudas_acumuladas.json"
                break
            carpeta = carpeta.parent

    if ruta_dudas is None:
        return  # No encontrado, ignorar silenciosamente

    # Cargar o crear
    if ruta_dudas.exists():
        try:
            datos = _json.loads(ruta_dudas.read_text(encoding="utf-8"))
        except Exception:
            datos = {"dudas": []}
    else:
        datos = {"dudas": []}

    # Añadir entradas de esta sesión
    ts = datetime.now().strftime("%d/%m/%Y %H:%M")
    expediente = ruta_pdf.parent.name
    for f in fragmentos:
        datos["dudas"].append({
            "fecha": ts,
            "expediente": expediente,
            "documento": ruta_pdf.name,
            "tipo_procedimiento": tipo_proc,
            "etiqueta": f["etiqueta"],
            "valor": f["valor"],
            "decision": f["decision"],
            "contexto": f["contexto"],
        })

    ruta_dudas.write_text(
        _json.dumps(datos, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def validar_calidad(texto_original: str, texto_anonimizado: str, mapa: MapaEntidades, log):
    """Genera un informe de calidad de la anonimizacion."""
    total_chars = len(texto_original)
    etiquetas_en_texto = re.findall(r'\[[A-Z_0-9]+\]', texto_anonimizado)
    n_etiquetas = len(etiquetas_en_texto)
    n_entidades_mapa = len(mapa.mapa)

    # Buscar posibles datos no anonimizados
    posibles_dni = re.findall(r'\b\d{8}[A-Z]\b', texto_anonimizado)
    posibles_iban = re.findall(r'\bES\s*\d{2}[\s]?\d{4}', texto_anonimizado)
    posibles_email = re.findall(r'\b[\w.+-]+@[\w-]+\.[\w.]+\b', texto_anonimizado)
    posibles_tel = re.findall(r'\b[6789]\d{8}\b', texto_anonimizado)

    print("\n" + "="*55)
    print("  INFORME DE CALIDAD")
    print("="*55)
    print(f"  Documento original:     {total_chars:,} caracteres")
    print(f"  Entidades en mapa:      {n_entidades_mapa}")
    print(f"  Etiquetas en texto:     {n_etiquetas}")
    print()

    alertas = []
    if posibles_dni:
        alertas.append(f"  ALERTA: {len(posibles_dni)} posible(s) DNI sin anonimizar: {posibles_dni[:3]}")
    if posibles_iban:
        alertas.append(f"  ALERTA: {len(posibles_iban)} posible(s) IBAN sin anonimizar")
    if posibles_email:
        alertas.append(f"  ALERTA: {len(posibles_email)} posible(s) email sin anonimizar: {posibles_email[:3]}")
    if posibles_tel:
        alertas.append(f"  ALERTA: {len(posibles_tel)} posible(s) telefono sin anonimizar: {posibles_tel[:3]}")

    if alertas:
        print("  *** POSIBLES DATOS NO ANONIMIZADOS ***")
        for a in alertas:
            print(a)
            log.warning(a)
    else:
        print("  No se detectaron datos estructurados sin anonimizar.")

    print("="*55)


# ══════════════════════════════════════════════════════════════════════════════
# CONVERSION A MARKDOWN
# ══════════════════════════════════════════════════════════════════════════════

def texto_a_markdown(texto: str, nombre_archivo: str, tipo_proc: str) -> str:
    lineas = texto.split('\n')
    md = []
    md.append(f"# {nombre_archivo}")
    md.append("")
    md.append(f"> **Documento anonimizado** | Tipo: {tipo_proc}")
    md.append(f"> Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    md.append("")

    # Palabras que en mayúsculas son ruido OCR habitual (no son títulos de sección)
    RUIDO_OCR = {
        'PDF', 'OCR', 'NIG', 'NIF', 'DNI', 'NIE', 'CIF', 'IBAN',
        'TEL', 'FAX', 'HTTP', 'HTTPS', 'WWW', 'EMAIL', 'CORREO',
        'SL', 'SLU', 'SA', 'SAU', 'SLP', 'CB', 'SCP',
        'LEC', 'LECR', 'CP', 'LOPJ', 'CE', 'ET', 'LRJS',
        'ART', 'NUM', 'COL', 'REF', 'EXP', 'NRO',
    }

    def es_ruido_ocr(s: str) -> bool:
        """Descarta líneas en mayúsculas que son artefactos OCR, no títulos."""
        palabras = s.split()
        # Línea de una sola palabra corta o código
        if len(palabras) == 1 and (len(palabras[0]) <= 4 or palabras[0] in RUIDO_OCR):
            return True
        # Línea con dígitos (números de folio, códigos de barras OCR)
        if re.search(r'\d', s):
            return True
        # Más de la mitad de palabras son palabras excluidas o acrónimos
        excluidas = sum(1 for p in palabras if p.upper() in PALABRAS_EXCLUIDAS or p in RUIDO_OCR)
        if palabras and excluidas / len(palabras) > 0.5:
            return True
        return False

    for linea in lineas:
        s = linea.strip()
        if not s:
            md.append("")
            continue

        if (s.isupper() and 5 < len(s) < 80 and
                not s.startswith('[') and s[-1] not in '.,:;' and
                ':' not in s and                               # <- excluir campos clave:valor
                not es_ruido_ocr(s)):                          # <- guarda anti-ruido
            md.append(f"## {s.title()}")

        elif any(s.upper().startswith(k) for k in [
            'HECHOS', 'FUNDAMENTOS', 'SUPLICO', 'OTROSI',
            'PRIMERO.-', 'SEGUNDO.-', 'TERCERO.-', 'CUARTO.-', 'QUINTO.-',
            'ANTECEDENTES', 'FALLO',
        ]):
            md.append(f"### {s}")

        elif ':' in s and len(s) < 120:
            partes = s.split(':', 1)
            if len(partes[0].strip()) < 40:
                md.append(f"**{partes[0].strip()}:** {partes[1].strip()}")
            else:
                md.append(s)
        else:
            md.append(s)

    return '\n'.join(md)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def procesar(ruta_archivo: str, tipo_forzado: str = None, revision_auto: str = None):
    ruta = Path(ruta_archivo)
    if not ruta.exists():
        print(f"ERROR: No se encuentra: {ruta_archivo}")
        sys.exit(1)

    acumular = len(sys.argv) >= 3 and bool(sys.argv[2])
    log = configurar_log(ruta.parent, acumular=acumular)
    log.info(f"{'='*55}")
    log.info(f"Inicio procesamiento: {ruta.name}")
    log.info(f"{'='*55}")

    # 1. Extraer texto
    texto_original = extraer_texto(ruta, log)

    # 2. Detectar nombres protegidos (operadores juridicos)
    protegidos = detectar_nombres_protegidos(texto_original)
    log.info(f"Nombres protegidos detectados: {len(protegidos)}")
    if protegidos:
        print(f"\n  Operadores juridicos detectados (NO se anonimizan):")
        for p in sorted(protegidos):
            print(f"    - {p}")

    # 3. Tipo de procedimiento (solo metadato descriptivo en la cabecera del .md)
    # - Si viene forzado con un nombre concreto: usar ese.
    # - Si viene "AUTO" o estamos en modo pipeline: detectar por contenido, sin preguntar.
    # - En modo manual: preguntar al usuario.
    es_pipeline = "--pipeline" in sys.argv
    if tipo_forzado and tipo_forzado != "AUTO":
        tipo_procedimiento = tipo_forzado
        print(f"\n  Tipo de procedimiento: {tipo_procedimiento}")
    elif tipo_forzado == "AUTO" or es_pipeline:
        tipo_procedimiento = detectar_tipo_procedimiento(texto_original)
        print(f"\n  Tipo de procedimiento detectado: {tipo_procedimiento}")
    else:
        tipo_procedimiento = pedir_tipo_procedimiento(texto_original)
    log.info(f"Tipo de procedimiento: {tipo_procedimiento}")

    # 4. Inicializar mapa
    mapa = MapaEntidades(protegidos=protegidos)

    # 5. Anonimizar
    texto = texto_original

    log.info("Fase 1: Presidio")
    texto = anonimizar_con_presidio(texto, mapa, log)

    log.info("Fase 2: Deteccion contextual")
    texto = anonimizar_por_contexto(texto, mapa, log)

    log.info("Fase 3: Regex")
    texto = aplicar_regex(texto, mapa, log)

    log.info("Fase 4: Deteccion mayusculas")
    texto = anonimizar_mayusculas(texto, mapa, log)

    # 6. Revision interactiva
    fragmentos_revisados = []
    if revision_auto is not None:
        # Modo pipeline: decision ya tomada al inicio
        hacer_revision = (revision_auto == "S")
    else:
        print("\n  ¿Deseas revisar fragmentos dudosos manualmente? (s/n)")
        hacer_revision = input("  Respuesta: ").strip().lower() == 's'
    if hacer_revision:
        texto, fragmentos_revisados = revisar_interactivo_con_captura(texto, mapa, log)
    guardar_dudas(fragmentos_revisados, ruta, tipo_procedimiento)

    # 7. Validacion de calidad
    validar_calidad(texto_original, texto, mapa, log)

    # 8. Generar Markdown
    log.info("Generando Markdown...")
    try:
        md = texto_a_markdown(texto, ruta.stem, tipo_procedimiento)
    except Exception as e:
        log.error(f"Error generando Markdown: {e}")
        md = texto  # fallback: guardar texto plano sin formato

    # 9. Guardar archivos — flush del log primero para liberar el handler
    # en Windows antes de escribir otros archivos en la misma carpeta
    for handler in log.handlers:
        try:
            handler.flush()
        except Exception:
            pass

    # Carpeta de salida: argumento explícito o junto al PDF
    if len(sys.argv) >= 3 and sys.argv[2]:
        carpeta_destino = Path(sys.argv[2])
        carpeta_destino.mkdir(parents=True, exist_ok=True)
    else:
        carpeta_destino = ruta.parent
    base = carpeta_destino / ruta.stem
    ruta_md = Path(f"{base}_anonimizado.md")
    ruta_mapa = Path(f"{base}_mapa.json")

    try:
        ruta_md.write_text(md, encoding="utf-8")
        log.info(f"Markdown: {ruta_md.name} ({len(md):,} caracteres)")
    except Exception as e:
        log.error(f"Error guardando Markdown: {e}")
        # Intentar con encoding latin-1 como fallback
        try:
            ruta_md.write_text(md.encode('utf-8', errors='replace').decode('utf-8'), encoding="utf-8")
            log.info(f"Markdown guardado con reemplazo de caracteres: {ruta_md.name}")
        except Exception as e2:
            log.error(f"Error guardando Markdown (fallback): {e2}")

    try:
        mapa.exportar_json(ruta_mapa)
        log.info(f"Mapa: {ruta_mapa.name} ({len(mapa.mapa)} entidades)")
    except Exception as e:
        log.error(f"Error guardando mapa JSON: {e}")

    if protegidos:
        log.info(f"Protegidos (no anonimizados): {', '.join(sorted(protegidos))}")
    log.info("Procesamiento completado.")

    print(f"\n  Archivos generados:")
    print(f"  - {ruta_md.name}")
    print(f"  - {ruta_mapa.name}")
    print(f"  - anonimizador.log")


# ══════════════════════════════════════════════════════════════════════════════
# API PURA EN MEMORIA (FeesDefender — Fase 1)
# ══════════════════════════════════════════════════════════════════════════════

def anonimizar_texto(
    texto: str,
    mapa: "MapaEntidades | None" = None,
    log: "logging.Logger | None" = None,
) -> "tuple[str, MapaEntidades]":
    """Aplica las 4 fases de anonimización sobre texto plano.

    Función pura: no toca el sistema de ficheros, no pide input al usuario,
    no llama a ``sys.exit``. Diseñada para uso embebido desde el pipeline
    de FeesDefender y desde tests.

    Si ``mapa`` es ``None``, crea uno nuevo con los nombres protegidos
    extraídos del propio texto. Si se pasa un mapa pre-poblado (caso de
    uso "mapa compartido por caso"), las nuevas entidades se acumulan
    respetando los contadores existentes — sin colisiones de etiquetas.

    Si Presidio no está instalado, la fase 1 se omite con un warning y
    las fases 2-4 (contextual, regex, mayúsculas) se ejecutan igualmente.

    Returns:
        Tupla ``(texto_anonimizado, mapa)``. El mapa puede usarse después
        con ``deanonimizar_texto`` para recuperar el original o persistirse
        con ``exportar_json``.
    """
    if mapa is None:
        protegidos = detectar_nombres_protegidos(texto)
        mapa = MapaEntidades(protegidos=protegidos)
    if log is None:
        log = logging.getLogger("anonimizador.embebido")
        if not log.handlers:
            log.addHandler(logging.NullHandler())

    texto = anonimizar_con_presidio(texto, mapa, log)
    texto = anonimizar_por_contexto(texto, mapa, log)
    texto = aplicar_regex(texto, mapa, log)
    texto = anonimizar_mayusculas(texto, mapa, log)
    return texto, mapa


if __name__ == '__main__':
    # Wrap UTF-8 de stdout/stderr solo en uso por línea de comando (Windows).
    # En uso embebido (Streamlit / pipeline / tests) no se ejecuta y no
    # interfiere con el sistema de logs de la aplicación host.
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

    if len(sys.argv) < 2:
        print("Uso: python anonimizar.py <archivo> [carpeta_destino] [tipo_proc] [revision]")
        sys.exit(1)

    # Argumentos:
    # sys.argv[1] = archivo PDF
    # sys.argv[2] = carpeta destino (opcional)
    # sys.argv[3] = tipo de procedimiento (opcional, "AUTO" = detectar)
    # sys.argv[4] = revision interactiva (opcional, "S" o "N")
    tipo_forzado  = sys.argv[3] if len(sys.argv) >= 4 else None
    revision_auto = sys.argv[4].upper() if len(sys.argv) >= 5 else None

    procesar(sys.argv[1], tipo_forzado=tipo_forzado, revision_auto=revision_auto)

    # En modo pipeline (flag --pipeline desde BAT/script) no esperar Enter: colgaria el pipeline
    if "--pipeline" not in sys.argv:
        try:
            input("\nPulsa Enter para cerrar...")
        except EOFError:
            pass
