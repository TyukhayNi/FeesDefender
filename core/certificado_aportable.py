"""El certificado que va al juzgado: el íntegro sin las páginas de condiciones.

F3 del envío certificado (spec §7.3, §7.4 y §9). De cada envío quedan tres artefactos,
los tres archivados: el **íntegro**, con su firma —lo archiva F2—; el **aportable**, un
documento DERIVADO, con otro nombre y sin firma; y su **manifiesto**, que dice qué se
retiró, de dónde y con qué huellas.

**El aportable es la IMAGEN de las páginas que se conservan**, con una capa de texto
invisible leída por OCR para que se pueda buscar y lo pueda leer una LLM (R2/H-01; la
capa de texto la pidió Nikolai el 2026-09-25). Hasta la R2 se copiaba la ESTRUCTURA de
las páginas conservadas, y arrastraba lo que compartían con las retiradas: primero el
formulario de las condiciones (R1/H-01), después patrones, fuentes, máscaras y metadatos
que ninguna página conservada dibujaba (R2/H-01, siete vías). Cada remedio cerraba una
vía y dejaba abierta la siguiente. La imagen cierra la frontera y no el ejemplo: **lo
que ninguna página conservada dibuja no está en el aportable**, y el OCR solo ve esos
píxeles.

Este módulo es puro: recibe bytes y devuelve bytes y datos. No sabe qué es un
expediente ni toca la red o el disco, y el OCR le llega como un puerto (`ocr`); de dónde
salen el certificado y los documentos enviados, y dónde se escribe, lo decide
`core/expedicion_certificada.py`.

Lo gobiernan mediciones del 2026-09-25 sobre tres certificados reales y los adjuntos
de dos de ellos (plan `docs/superpowers/plans/2026-09-25-codicert-f3.md`, M-1 a M-12).
Dos corrigen el spec: **el motor no compone las condiciones** —las trae el operador—,
así que su texto se lee de los adjuntos que salieron (M-9); y el requerimiento **sí
lleva importes** —la deuda reclamada—, así que el aviso de «sin cifras» saltaría
siempre y se rehace sobre las frases propias de las condiciones (M-2, M-6).
"""
from __future__ import annotations

import dataclasses
import difflib
import hashlib
import io
import re
import time
import unicodedata
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from core.certificado_lectura import _sin_ligaduras as sin_ligaduras
from core.certificado_lectura import paginas_de_acta_de_textos

_RE_ENTRADA = re.compile(r"^(?P<nombre>.+?)\s+(?P<huella>[0-9a-f]{6,64})$")
_RE_HEX = re.compile(r"^[0-9a-f]+$")
_FIN_FICHEROS = "la autenticidad de este documento"
_BLOQUE_FICHEROS = "FICHEROS ADJUNTOS"


class AportableError(RuntimeError):
    """No se puede producir un aportable seguro. Nunca se produce uno a medias."""


@dataclass(frozen=True)
class FicheroListado:
    """Un adjunto tal como lo lista el acta: nombre y huella (spec §7, M-5)."""

    nombre: str
    sha256: str


def _lector(datos: bytes, *, que: str):
    """Un `PdfReader` sobre los bytes. Un PDF ilegible es `AportableError`, no lo que
    lance pypdf."""
    from pypdf import PdfReader

    try:
        lector = PdfReader(io.BytesIO(datos))
        lector.pages  # noqa: B018 — obliga a leer el árbol de páginas aquí dentro
        return lector
    except Exception as exc:  # noqa: BLE001 — pypdf lanza de todo ante un PDF roto
        raise AportableError(
            f"{que}: no se puede leer como PDF ({type(exc).__name__}: {exc})") from exc


def _textos_pdf(datos: bytes, *, que: str) -> list[str]:
    """El texto de cada página. Un PDF ilegible es `AportableError`, no lo que lance pypdf."""
    lector = _lector(datos, que=que)
    try:
        return [p.extract_text() or "" for p in lector.pages]
    except Exception as exc:  # noqa: BLE001 — pypdf lanza de todo ante un PDF roto
        raise AportableError(
            f"{que}: no se puede leer como PDF ({type(exc).__name__}: {exc})") from exc


#: La cabecera de la lista dentro del bloque: «Nombre Huella digital (sha256)» (M-5).
_RE_CABECERA_LISTA = re.compile(r"^[ \t]*Nombre\s+Huella digital\b.*$", re.M)


def ficheros_listados_de_textos(textos: Sequence[str]) -> tuple[FicheroListado, ...]:
    """El bloque FICHEROS ADJUNTOS **del acta**, con cada huella reconstruida (M-5).

    La huella viene PARTIDA en dos líneas —46 caracteres en la del nombre y 18 en la
    siguiente— y ya costó un falso negativo en el W-04A6LI: se concatenan hasta 64.
    Una línea que no es ni entrada ni continuación **para** en vez de saltarse: un
    nombre partido en dos líneas, o un formato que nadie ha medido, no se adivina.

    **Qué bloque** (R1/H-03): solo cuenta el que está en una página del ACTA —la que lleva
    el sello temporal—, tiene que ser el único, la lista empieza en SU cabecera
    («Nombre Huella digital», después del rótulo) y **tiene que llegar a su línea de
    cierre**. Sin cierre la lista puede seguir en otra página, y dar por completa la
    mitad dejaría fuera un documento que salió.

    **Único se cuenta por BLOQUES, no por páginas** (R2/H-02): contar las páginas que
    llevan alguno dejaba pasar dos bloques completos en una misma página, y mandaba el
    primero. Es un cerco textual sobre el acta, no una autenticación: la huella de cada
    adjunto se comprueba después contra lo que se baja.
    """
    acta = set(paginas_de_acta_de_textos(textos))
    bloques = [n for n, t in enumerate(textos, 1) if n in acta
               for _ in range(sin_ligaduras(t or "").count(_BLOQUE_FICHEROS))]
    if not bloques:
        raise AportableError(
            "el certificado no trae el bloque FICHEROS ADJUNTOS en su acta: sin él no se "
            "puede comprobar qué documentos salieron.")
    if len(bloques) > 1:
        raise AportableError(
            f"el acta trae más de un bloque FICHEROS ADJUNTOS ({len(bloques)}, en las "
            f"páginas {sorted(set(bloques))}): no se adivina cuál es el que certifica.")
    tras = sin_ligaduras(textos[bloques[0] - 1]).split(_BLOQUE_FICHEROS, 1)[1]
    cabecera = _RE_CABECERA_LISTA.search(tras)
    if cabecera is None:
        raise AportableError(
            "el bloque FICHEROS ADJUNTOS no trae la cabecera «Nombre Huella digital»: no "
            "se sabe dónde empieza la lista.")
    lineas = [l.strip() for l in tras[cabecera.end():].splitlines() if l.strip()]
    salida: list[FicheroListado] = []
    n, cerrado = 0, False
    while n < len(lineas):
        if lineas[n].lower().startswith(_FIN_FICHEROS):
            cerrado = True
            break
        entrada = _RE_ENTRADA.match(lineas[n])
        if entrada is None:
            raise AportableError(
                "el bloque FICHEROS ADJUNTOS trae una línea que no es ni un fichero ni la "
                f"continuación de una huella: {lineas[n][:60]!r}. No se adivina.")
        huella = entrada.group("huella")
        n += 1
        while len(huella) < 64 and n < len(lineas) and _RE_HEX.match(lineas[n]):
            huella += lineas[n]
            n += 1
        if len(huella) != 64:
            raise AportableError(
                f"la huella de {entrada.group('nombre')!r} no suma 64 caracteres "
                f"hexadecimales sino {len(huella)}: no se reconstruye a medias.")
        salida.append(FicheroListado(nombre=entrada.group("nombre"), sha256=huella))
    if not cerrado:
        raise AportableError(
            "la lista de FICHEROS ADJUNTOS no llega a su línea de cierre en la página del "
            "acta: puede seguir en otra, y no se da por completa.")
    if not salida:
        raise AportableError("el bloque FICHEROS ADJUNTOS del acta está vacío.")
    return tuple(salida)


def ficheros_listados(pdf: bytes) -> tuple[FicheroListado, ...]:
    """`ficheros_listados_de_textos` sobre el PDF del certificado."""
    return ficheros_listados_de_textos(_textos_pdf(pdf, que="el certificado"))


# --- qué páginas son de condiciones ---------------------------------------------

#: El rótulo con que la plantilla abre la página de condiciones (spec §7.3). La palabra
#: «condiciones» sale también en el requerimiento («las condiciones adjuntas») y en la
#: factura («Condiciones de pago a la vista») (M-7): lo que distingue es la FRASE.
LITERAL_CONDICIONES = "CONFIDENCIAL - CONDICIONES"

_CABECERA_REPRODUCCION = re.compile(r"^[ \t]*C[óo]digo de env[íi]o:.*$", re.M)
_GUIONES = str.maketrans({"–": "-", "—": "-", "‐": "-",
                          "‑": "-", "−": "-"})


def _plano(texto: str) -> str:
    """Ligaduras deshechas, guiones unificados, sin tildes y en minúsculas."""
    t = sin_ligaduras(texto or "").translate(_GUIONES)
    t = unicodedata.normalize("NFKD", t)
    return "".join(c for c in t if not unicodedata.combining(c)).lower()


def normalizar_pagina(texto: str) -> str:
    """El texto de una página, listo para compararlo con el de otra (M-3).

    Quita la cabecera que Codicert pone a cada página de la reproducción —«Código de
    envío: … Página: N de M»—, que es lo único que distingue la copia del original: sin
    ella coinciden al 100 %.
    """
    sin_cabecera = _CABECERA_REPRODUCCION.sub("", sin_ligaduras(texto or ""))
    return " ".join(_plano(sin_cabecera).split())


#: El rótulo como FRASE: las dos palabras seguidas con el guion entre medias, con
#: cualquier espacio o salto de línea alrededor (R1/H-02).
_RE_ROTULO = re.compile(r"\bconfidencial\s*-\s*condiciones\b")
#: El rótulo como TÍTULO: la misma frase, pero abriendo una línea (R2/H-03). Puede venir
#: partida en varias —la extracción la parte—; lo que no puede es tener prosa delante.
_RE_TITULO = re.compile(r"^[ \t]*confidencial\s*-\s*condiciones\b", re.M)


def lleva_rotulo(texto: str) -> bool:
    """¿Lleva la página el rótulo de las condiciones, EN CUALQUIER SITIO? (M-7, R1/H-02)

    Es la RED: la usan las paradas sobre lo que se conserva, y ahí más vale ver de más.
    Hasta la R1 se exigía la línea entera, y un rótulo que la extracción partiera en dos
    no se reconocía. La frase con su guion es específica: la palabra «condiciones» suelta
    que midió M-7 —«las condiciones adjuntas», «Condiciones de pago a la vista»— no la
    forma. Qué página ABRE las condiciones lo dice `abre_condiciones`, no esto.
    """
    return bool(_RE_ROTULO.search(" ".join(_plano(texto).split())))


def abre_condiciones(texto: str) -> bool:
    """¿Abre la página las condiciones, con el rótulo como TÍTULO? (R2/H-03)

    Desde la R1 bastaba la frase en cualquier sitio, y un requerimiento que CITARA el
    título («El anexo se titula “CONFIDENCIAL - CONDICIONES”») se retiraba entero como si
    fuera condiciones. Un título abre una línea; una mención lleva prosa delante. La
    mención no se retira en silencio: la ve la red (`lleva_rotulo`) en la segunda parada,
    y para para que la mire una persona.
    """
    return bool(_RE_TITULO.search(_plano(texto)))


@dataclass(frozen=True)
class DocumentoEnviado:
    """Un adjunto tal como salió, bajado de Codicert (`GET /envios/{id}/adjuntos/…`)."""

    nombre: str
    contenido: bytes

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.contenido).hexdigest()


@dataclass(frozen=True)
class PaginaCondiciones:
    """Una página de condiciones: documento, página (numeración DEL DOCUMENTO) y texto."""

    documento: str
    pagina: int
    texto: str


def paginas_de_condiciones(
        documentos: Sequence[DocumentoEnviado]) -> tuple[PaginaCondiciones, ...]:
    """Las páginas de condiciones de los documentos enviados (spec §7.3, M-1, M-7).

    La regla: desde la primera página que lleva el rótulo como TÍTULO (`abre_condiciones`)
    **hasta el final de ese documento**. En el refundido medido las condiciones son el
    último bloque, y en el documento partido que pide el §7 (`ANEXO II.pdf`) son el
    documento entero: la misma regla vale para los dos.

    **Si el rótulo cae antes del final, se retira de más, nunca de menos.** Una página
    que no es de condiciones y queda dentro sale del aportable —se pierde prueba, que el
    íntegro conserva—; ninguna de condiciones puede quedar fuera de lo que se retira.
    El recorte avisa de esas páginas arrastradas.
    """
    salida: list[PaginaCondiciones] = []
    for doc in documentos:
        textos = _textos_pdf(doc.contenido, que=doc.nombre)
        inicio = next((n for n, t in enumerate(textos) if abre_condiciones(t)), None)
        if inicio is None:
            continue
        salida += [PaginaCondiciones(documento=doc.nombre, pagina=n + 1, texto=textos[n])
                   for n in range(inicio, len(textos))]
    return tuple(salida)


# --- el recorte -----------------------------------------------------------------

#: Similitud mínima para tener una página de la reproducción por COPIA de una página
#: de condiciones (M-3): original contra copia, 1,000 en las ocho parejas medidas; la
#: misma plantilla en otra expedición, 0,877-0,939; páginas distintas, 0,39 como
#: mucho. 0,98 deja margen a un ruido de extracción que no se ha visto y queda lejos de
#: lo que sí se ha visto.
UMBRAL_COPIA = 0.98

#: Por debajo de esto una página de condiciones no tiene texto con que casarla
#: —escaneada o en blanco— y no se puede garantizar que salga: se para.
MIN_CARACTERES = 40

#: Resolución de la imagen (M-11, medido el 2026-09-25 sobre los reales): a 200 ppp las
#: huellas del acta, en cuerpo pequeño, se leen a ojo, y el OCR lee lo mismo que a 150
#: (similitud con el texto original, 0,61-0,95 contra 0,66-0,95). Pesa ~545 KB por
#: página, contra ~362 a 150.
PPP = 200
CALIDAD_JPEG = 85


@dataclass(frozen=True)
class PaginaRetirada:
    """Una página que sale del aportable, en las TRES numeraciones (spec §7.3)."""

    pagina_certificado: int
    pagina_reproduccion: int
    documento: str
    pagina_documento: int
    similitud: float


@dataclass(frozen=True)
class Recorte:
    """Qué se conserva y qué se retira, con la IMAGEN de lo conservado (R2/H-01).

    Aún no es el aportable: le falta la capa de texto, que pone `aportable_de`. La imagen
    es determinista —mismos bytes en cada corrida— y es lo que compara quien vuelve a
    lanzar; el OCR no lo es.
    """

    imagen: bytes
    paginas_totales: int
    paginas_acta: tuple[int, ...]
    paginas_reproduccion: tuple[int, ...]
    retiradas: tuple[PaginaRetirada, ...]
    conservadas: tuple[int, ...]
    avisos: tuple[str, ...] = ()
    #: El texto normalizado de CADA página del íntegro (índice = página - 1): lo que la
    #: relectura compara con lo que el OCR lee en la imagen.
    normal: tuple[str, ...] = field(default=(), repr=False)


def _ratio(a: str, b: str) -> float:
    """Similitud 0..1 entre dos textos normalizados.

    `quick_ratio` es cota SUPERIOR y es barata: si no llega al umbral, el `ratio` de
    verdad tampoco. Un burofax admite 200 páginas (spec §1.4); sin el prefiltro serían
    200 comparaciones completas por cada página de condiciones.
    """
    m = difflib.SequenceMatcher(None, a, b, autojunk=False)
    cota = m.quick_ratio()
    return cota if cota < UMBRAL_COPIA else m.ratio()


def comprobar_reproduccion(certificado: bytes,
                           documentos: Sequence[DocumentoEnviado]) -> tuple[str, ...]:
    """El certificado reproduce EXACTAMENTE los documentos enviados, en orden (M-3, M-4).

    Sin esto, recortar un burofax con los documentos del correo descansaba en una
    PREMISA —que los dos canales llevaron lo mismo, como hace F1— y no en una
    comprobación (R1, sobre M-4): un burofax con otro segundo documento se recortaba
    igual, y lo que ese documento llevara salía entero. Se exige la misma cuenta de
    páginas y, página a página, la copia de cada una.

    **Cómo se compara depende de cuánto texto hay** (R2/H-05): con `MIN_CARACTERES` o más,
    por parecido (`UMBRAL_COPIA`); con menos, **letra a letra** —en tan poco texto el
    parecido no dice nada, y hasta la R2 no se comparaba: un «Recibo 40 EUR» sustituido
    por una quita pasaba—. Una página SIN texto (un escaneo) no se puede casar: su copia
    tiene que estar vacía también, y se devuelve un aviso que lo dice, en vez de darla por
    comprobada en silencio.
    """
    textos = _textos_pdf(certificado, que="el certificado")
    acta = set(paginas_de_acta_de_textos(textos))
    reproduccion = [t for n, t in enumerate(textos, 1) if n not in acta]
    paginas = [(d.nombre, k, t) for d in documentos
               for k, t in enumerate(_textos_pdf(d.contenido, que=d.nombre), 1)]
    if len(reproduccion) != len(paginas):
        raise AportableError(
            f"la reproducción del certificado tiene {len(reproduccion)} páginas y los "
            f"documentos enviados suman {len(paginas)}: el certificado no reproduce lo que "
            "se bajó, y no se recorta contra ello.")
    avisos: list[str] = []
    for k, (copia, (nombre, pagina, original)) in enumerate(zip(reproduccion, paginas), 1):
        objetivo, hecha = normalizar_pagina(original), normalizar_pagina(copia)
        if len(objetivo) >= MIN_CARACTERES:
            if _ratio(objetivo, hecha) < UMBRAL_COPIA:
                raise AportableError(
                    f"la página {k} de la reproducción no es la página {pagina} de "
                    f"{nombre!r}: el certificado no reproduce, en orden, los documentos "
                    "enviados, y no se recorta contra ellos.")
        elif objetivo != hecha:
            raise AportableError(
                f"la página {k} de la reproducción no es la página {pagina} de {nombre!r}: "
                "con tan poco texto no se compara por parecido, y no coincide letra a "
                "letra. El certificado no reproduce lo enviado, y no se recorta contra ello.")
        elif not objetivo:
            avisos.append(
                f"la página {pagina} de {nombre!r} no tiene texto: su copia —la {k} de la "
                "reproducción— solo se acredita por la cuenta de páginas. Compruébala a "
                "ojo en el íntegro.")
    return tuple(avisos)


def _mas_parecida(objetivo: str, candidatas: dict[int, str]) -> tuple[int | None, float]:
    """La página más parecida y su similitud EXACTA, para decir por qué no casó."""
    mejor, valor = None, 0.0
    for pagina, texto in candidatas.items():
        r = difflib.SequenceMatcher(None, objetivo, texto, autojunk=False).ratio()
        if r > valor:
            mejor, valor = pagina, r
    return mejor, valor


#: Las anotaciones medidas en los certificados reales (M-8): enlaces `/URI` y el widget
#: de la firma. La imagen no pinta ninguna; de cualquier OTRA se avisa, porque pudo
#: pintar algo que haga falta aportar.
_ANOTACIONES_MEDIDAS = frozenset({"/Link", "/Widget"})


def _tipos_de_anotacion(pagina) -> set[str]:
    anotaciones = pagina.get("/Annots")
    if anotaciones is None:
        return set()
    return {str(a.get_object().get("/Subtype")) for a in anotaciones.get_object()}


#: Fecha fija de la imagen: sin ella, dos corridas darían bytes distintos (M-8).
_FECHA_FIJA = time.gmtime(0)


def _rasterizar(certificado: bytes, paginas: Sequence[int]) -> bytes:
    """La IMAGEN de esas páginas (base 1), en su orden: un PDF con una imagen por página y
    nada más (R2/H-01).

    Se dibuja **sin anotaciones**: el widget de la firma pintaría un sello sin firma
    detrás (M-8). Una página cada vez —un burofax de 200 no cabe entero en memoria a esta
    resolución— y con una estructura mínima escrita aquí: la página, su contenido
    `q … cm /Im0 Do Q` y la imagen en JPEG. Es la que la relectura sabe reconocer, y es
    determinista: los mismos bytes en cada corrida.
    """
    import pypdfium2 as pdfium
    from pypdf import PdfWriter
    from pypdf.generic import (DecodedStreamObject, DictionaryObject, NameObject,
                               NumberObject)

    try:
        documento = pdfium.PdfDocument(certificado)
    except Exception as exc:  # noqa: BLE001 — pdfium lanza su propio error ante un PDF roto
        raise AportableError(
            f"el certificado no se puede dibujar ({type(exc).__name__}: {exc})") from exc
    escritor = PdfWriter()
    try:
        for numero in paginas:
            imagen = documento[numero - 1].render(
                scale=PPP / 72, draw_annots=False, may_draw_forms=False).to_pil()
            jpeg = io.BytesIO()
            imagen.convert("RGB").save(jpeg, format="JPEG", quality=CALIDAD_JPEG)
            ancho, alto = imagen.size
            flujo = DecodedStreamObject()
            flujo.set_data(jpeg.getvalue())
            flujo.update({
                NameObject("/Type"): NameObject("/XObject"),
                NameObject("/Subtype"): NameObject("/Image"),
                NameObject("/Width"): NumberObject(ancho),
                NameObject("/Height"): NumberObject(alto),
                NameObject("/ColorSpace"): NameObject("/DeviceRGB"),
                NameObject("/BitsPerComponent"): NumberObject(8),
                NameObject("/Filter"): NameObject("/DCTDecode"),
            })
            puntos = (ancho * 72 / PPP, alto * 72 / PPP)
            pagina = escritor.add_blank_page(width=puntos[0], height=puntos[1])
            pagina[NameObject("/Resources")] = DictionaryObject({
                NameObject("/XObject"): DictionaryObject(
                    {NameObject("/Im0"): escritor._add_object(flujo)})})
            contenido = DecodedStreamObject()
            contenido.set_data(f"q {puntos[0]:.4f} 0 0 {puntos[1]:.4f} 0 0 cm /Im0 Do Q"
                               .encode("ascii"))
            pagina[NameObject("/Contents")] = escritor._add_object(contenido)
    finally:
        documento.close()
    escritor.add_metadata({"/Producer": "FeesDefender",
                           "/CreationDate": time.strftime("D:%Y%m%d%H%M%SZ", _FECHA_FIJA)})
    buffer = io.BytesIO()
    escritor.write(buffer)
    return buffer.getvalue()


def recortar(certificado: bytes,
             condiciones: Sequence[PaginaCondiciones]) -> Recorte:
    """Qué sale del aportable, y la IMAGEN de lo que se queda.

    Dos paradas antes de dibujar nada (spec §7.3, reenunciado con M-3):

    1. **Una página de condiciones que no se localiza en la reproducción para.** Lo que
       no se sabe dónde está no se puede garantizar que haya salido.
    2. **Una página que se conserva y lleva el rótulo para**, sea de la reproducción o
       del acta, como título o como mención. Es la red de la primera por un instrumento
       independiente: el texto casado puede fallar de formas que el rótulo no, y al revés.

    La tercera —la relectura del resultado— la hace `aportable_de` sobre el aportable
    ya con su capa de texto (`verificar_aportable`).

    Se retira TODA página de la reproducción que sea copia de una de condiciones, no
    solo la primera: dos copias son dos páginas de condiciones.
    """
    if not condiciones:
        raise AportableError(
            "no hay páginas de condiciones que retirar. Un aportable sin nada retirado "
            "sería el íntegro sin su firma: si no hay condiciones, lo que se aporta es el "
            "íntegro.")
    for c in condiciones:
        if len(normalizar_pagina(c.texto)) < MIN_CARACTERES:
            raise AportableError(
                f"la página {c.pagina} de {c.documento!r} es de condiciones y no tiene "
                "texto con que localizarla (¿escaneada? ¿en blanco?). Lo que no se puede "
                "localizar no se puede garantizar que salga: se para.")
    lector = _lector(certificado, que="el certificado")
    try:
        textos = [p.extract_text() or "" for p in lector.pages]
    except Exception as exc:  # noqa: BLE001 — pypdf lanza de todo ante un PDF roto
        raise AportableError(
            f"el certificado no se puede leer como PDF ({type(exc).__name__}: {exc})"
        ) from exc
    total = len(textos)
    acta = paginas_de_acta_de_textos(textos)
    if not acta:
        raise AportableError(
            "el PDF no tiene páginas de acta —ninguna lleva el sello temporal en la "
            "cabecera—: no es un certificado de Codicert.")
    reproduccion = tuple(n for n in range(1, total + 1) if n not in acta)
    todas = tuple(normalizar_pagina(t) for t in textos)
    normal = {n: todas[n - 1] for n in reproduccion}

    retiradas: dict[int, PaginaRetirada] = {}
    for c in condiciones:
        objetivo = normalizar_pagina(c.texto)
        copias = [(n, r) for n, r in ((n, _ratio(objetivo, t)) for n, t in normal.items())
                  if r >= UMBRAL_COPIA]
        if not copias:
            donde, valor = _mas_parecida(objetivo, normal)
            raise AportableError(
                f"la página {c.pagina} de {c.documento!r} (condiciones) no aparece en la "
                f"reproducción del certificado: la más parecida es la {donde} del "
                f"certificado, con {valor:.2f}, y hace falta {UMBRAL_COPIA}. No se sabe "
                "dónde está, así que no se puede garantizar que salga: no se produce "
                "aportable.")
        for n, r in copias:
            previa = retiradas.get(n)
            if previa is None or r > previa.similitud:
                retiradas[n] = PaginaRetirada(
                    pagina_certificado=n, pagina_reproduccion=reproduccion.index(n) + 1,
                    documento=c.documento, pagina_documento=c.pagina,
                    similitud=round(r, 4))
    conservadas = tuple(n for n in range(1, total + 1) if n not in retiradas)

    for n in conservadas:
        if not lleva_rotulo(textos[n - 1]):
            continue
        donde = ("es del ACTA, que no se recorta: el asunto o el cuerpo de la "
                 "comunicación lo reproducen" if n in acta else
                 "y no casa con ninguna página de condiciones de lo que salió")
        if abre_condiciones(textos[n - 1]):
            raise AportableError(
                f"la página {n} del certificado se conserva y lleva el rótulo "
                f"«{LITERAL_CONDICIONES}» —{donde}—. No se produce aportable.")
        # R2/H-03: la frase con prosa delante es una MENCIÓN —una cita, o unas condiciones
        # con otro formato—. Ni se retira en silencio ni se deja pasar: se para y se dice.
        raise AportableError(
            f"la página {n} del certificado se conserva y menciona el rótulo "
            f"«{LITERAL_CONDICIONES}» en el texto, no como título —{donde}—: puede ser una "
            "cita o unas condiciones con otro formato. Revísala: no se produce aportable.")

    anotaciones = {n: _tipos_de_anotacion(lector.pages[n - 1]) - _ANOTACIONES_MEDIDAS
                   for n in conservadas}
    avisos = (_avisos_de_fuga({n: textos[n - 1] for n in conservadas}, condiciones)
              + _avisos_de_arrastre(condiciones)
              + [f"la página {n} del certificado llevaba anotaciones de tipo "
                 f"{', '.join(sorted(tipos))}, que el aportable no pinta: comprueba en el "
                 "íntegro que no pintaban nada que haga falta aportar."
                 for n, tipos in anotaciones.items() if tipos])
    return Recorte(imagen=_rasterizar(certificado, conservadas), paginas_totales=total,
                   paginas_acta=tuple(acta), paginas_reproduccion=reproduccion,
                   retiradas=tuple(retiradas[n] for n in sorted(retiradas)),
                   conservadas=conservadas, avisos=tuple(avisos), normal=todas)


# --- el aportable: la imagen con su capa de texto, y su relectura -----------------

def aportable_de(recorte: Recorte, *, ocr: Callable[[bytes], bytes]) -> bytes:
    """El aportable: la imagen del recorte con su capa de texto, y RELEÍDO.

    `ocr` recibe la imagen y devuelve el mismo PDF con una capa de texto invisible. Solo
    ve esos píxeles —no el íntegro—, así que su texto no puede salir de otra parte.
    **Sin capa de texto no hay aportable** (lo que Nikolai pidió es que se pueda leer): si
    el OCR falla, para. Y lo que vuelve se relee entero (`verificar_aportable`), porque
    es una herramienta externa y lo que devuelva no se da por bueno.
    """
    try:
        pdf = ocr(recorte.imagen)
    except Exception as exc:  # noqa: BLE001 — el OCR es externo: falle como falle, se para
        raise AportableError(
            f"no se pudo pasar el OCR sobre la imagen ({type(exc).__name__}: {exc}): sin su "
            "capa de texto no se entrega el aportable.") from exc
    verificar_aportable(pdf, recorte)
    return pdf


#: El PERFIL del aportable (R2/H-01): lo único que puede llevar dentro. Es una lista
#: BLANCA —lo que no está aquí, para—, porque la negra de la R1 («las huellas de lo que
#: solo usaban las retiradas») dejaba pasar todo lo que no estuviera en ella.
_CATALOGO = frozenset({"/Type", "/Pages", "/Metadata", "/Lang"})
_NODO_PAGINAS = frozenset({"/Type", "/Kids", "/Count", "/Parent"})
_PAGINA = frozenset({"/Type", "/Parent", "/MediaBox", "/CropBox", "/Rotate", "/Contents",
                     "/Resources"})
_RECURSOS_PAGINA = frozenset({"/ProcSet", "/XObject"})
_OPERADORES_PAGINA = frozenset({b"q", b"Q", b"cm", b"Do"})
#: La capa de texto: un formulario que solo ESCRIBE. Medido sobre OCRmyPDF 17.11: BT ET
#: J Q Td Tf Tj Tr Tz cm q w. Se admiten además los de texto y color de otras versiones
#: del OCR, y ninguno que pinte, dibuje otro objeto o meta una imagen.
_FORMULARIO_TEXTO = frozenset({"/Type", "/Subtype", "/BBox", "/FormType", "/Matrix",
                               "/Resources", "/Filter", "/DecodeParms", "/Length"})
_RECURSOS_TEXTO = frozenset({"/ProcSet", "/Font"})
_OPERADORES_TEXTO = frozenset({
    b"BT", b"ET", b"Tf", b"Tr", b"Tz", b"Tm", b"Td", b"TD", b"T*", b"TL", b"Tc", b"Tw",
    b"Ts", b"Tj", b"TJ", b"'", b'"', b"q", b"Q", b"cm", b"w", b"J", b"j", b"M", b"d",
    b"g", b"G", b"rg", b"RG", b"k", b"K", b"BMC", b"BDC", b"EMC"})
_MUESTRAN_TEXTO = frozenset({b"Tj", b"TJ", b"'", b'"'})
#: Modo de render 3: el texto no se pinta. Es el de la capa de un OCR.
_INVISIBLE = 3


def _fuera_de_perfil(que: str) -> AportableError:
    return AportableError(f"el aportable lleva {que}: no es de su perfil. No se entrega.")


def _admitir(valor, admitidos: set[int]) -> None:
    """Todo lo que cuelga de `valor`, admitido. Solo para lo que YA pasó su comprobación."""
    from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject

    pendientes = [valor]
    while pendientes:
        v = pendientes.pop()
        if isinstance(v, IndirectObject):
            if v.idnum in admitidos:
                continue
            admitidos.add(v.idnum)
            v = v.get_object()
        if isinstance(v, DictionaryObject):
            pendientes += [v.raw_get(k) for k in v]
        elif isinstance(v, ArrayObject):
            pendientes += list(v)


def _referencia(contenedor, clave: str, admitidos: set[int]) -> None:
    """Admite el objeto al que apunta `contenedor[clave]`, si es indirecto, sin bajar."""
    from pypdf.generic import IndirectObject

    crudo = contenedor.raw_get(clave)
    if isinstance(crudo, IndirectObject):
        admitidos.add(crudo.idnum)


def _operaciones(flujo, lector, *, que: str):
    from pypdf.generic import ContentStream

    try:
        if isinstance(flujo, ContentStream):
            return flujo.operations
        return ContentStream(flujo, lector).operations
    except Exception as exc:  # noqa: BLE001 — un contenido que pypdf no sabe leer
        raise _fuera_de_perfil(f"un contenido ilegible en {que} ({exc})") from exc


def _huella_imagen(imagen) -> tuple[dict, bytes]:
    """Lo que identifica una imagen: su diccionario —valores resueltos, sin la longitud:
    los números de objeto cambian de un fichero a otro— y sus bytes tal cual."""
    return ({str(k): str(imagen[k]) for k in imagen if k != "/Length"},
            bytes(getattr(imagen, "_data", b"")))


def _capa_de_texto(ref, lector, *, k: int, admitidos: set[int]) -> None:
    """Un formulario de la capa de texto: solo escribe texto, invisible, con fuentes que
    no dibujan (no Type3). Lo que pase, se admite con todo lo que cuelga de sus fuentes."""
    que = f"la capa de texto de la página {k}"
    forma = ref.get_object()
    ajenas = set(forma.keys()) - _FORMULARIO_TEXTO
    if ajenas:
        raise _fuera_de_perfil(f"«{min(ajenas)}» en {que}")
    recursos = forma.get("/Resources")
    recursos = recursos.get_object() if recursos is not None else {}
    ajenas = set(recursos.keys()) - _RECURSOS_TEXTO
    if ajenas:
        raise _fuera_de_perfil(f"el recurso «{min(ajenas)}» en {que}")
    fuentes = recursos.get("/Font")
    fuentes = fuentes.get_object() if fuentes is not None else {}
    for nombre in fuentes:
        fuente = fuentes[nombre].get_object()
        familia = [fuente] + [d.get_object() for d in fuente.get("/DescendantFonts") or []]
        if any(f.get("/Subtype") == "/Type3" or "/CharProcs" in f or "/Resources" in f
               for f in familia):
            raise _fuera_de_perfil(f"una fuente Type3 —que dibuja sus glifos— en {que}")
    modo, pila = 0, []
    for operandos, operador in _operaciones(forma, lector, que=que):
        if operador not in _OPERADORES_TEXTO:
            raise _fuera_de_perfil(
                f"el operador «{operador.decode('latin-1', 'replace')}» en {que}")
        if operador == b"q":
            pila.append(modo)
        elif operador == b"Q":
            modo = pila.pop() if pila else modo
        elif operador == b"Tr" and operandos:
            modo = int(operandos[0])
        elif operador in _MUESTRAN_TEXTO and modo != _INVISIBLE:
            raise AportableError(
                f"{que} se VE (modo de render {modo}): la del OCR es invisible, y una que "
                "se ve pintaría texto encima de la imagen. No se entrega.")
    admitidos.add(ref.idnum)
    _admitir(forma.raw_get("/Resources") if "/Resources" in forma else None, admitidos)
    for clave in forma:
        if clave != "/Resources":
            _admitir(forma.raw_get(clave), admitidos)


def _recorrer_pagina(pagina, lector, *, k: int, conservada: int, esperada, caja,
                     admitidos: set[int]) -> None:
    """Una página del aportable: su imagen es la del raster, su contenido solo la dibuja
    (y a la capa de texto), y no lleva nada más."""
    from pypdf.generic import IndirectObject

    ajenas = set(pagina.keys()) - _PAGINA
    if ajenas:
        raise _fuera_de_perfil(f"«{min(ajenas)}» en la página {k}")
    giro = int(pagina.get("/Rotate", 0) or 0)
    if giro % 360:
        raise AportableError(
            f"la página {k} del aportable está girada (/Rotate {giro}): la imagen ya sale "
            "derecha del íntegro. No se entrega.")
    for nombre in ("/MediaBox", "/CropBox"):
        if nombre in pagina and any(abs(float(a) - float(b)) > 0.01
                                    for a, b in zip(pagina[nombre], caja)):
            raise _fuera_de_perfil(f"una caja de página distinta de la de su imagen "
                                   f"({nombre}) en la página {k}")
    if "/Resources" not in pagina:
        raise _fuera_de_perfil(f"una página sin recursos propios (la {k})")
    recursos = pagina["/Resources"].get_object()
    ajenas = set(recursos.keys()) - _RECURSOS_PAGINA
    if ajenas:
        raise _fuera_de_perfil(f"el recurso «{min(ajenas)}» en la página {k}")
    xobjetos = recursos.get("/XObject")
    xobjetos = xobjetos.get_object() if xobjetos is not None else {}
    imagenes, formularios = [], []
    for nombre in xobjetos:
        ref = xobjetos.raw_get(nombre)
        if not isinstance(ref, IndirectObject):
            raise _fuera_de_perfil(f"un objeto directo como «{nombre}» en la página {k}")
        subtipo = ref.get_object().get("/Subtype")
        if subtipo == "/Image":
            imagenes.append(ref)
        elif subtipo == "/Form":
            formularios.append(ref)
        else:
            raise _fuera_de_perfil(f"un objeto {subtipo} como «{nombre}» en la página {k}")
    if len(imagenes) != 1:
        raise _fuera_de_perfil(f"{len(imagenes)} imágenes en la página {k}")
    if _huella_imagen(imagenes[0].get_object()) != esperada:
        raise AportableError(
            f"la imagen de la página {k} del aportable no es la de la página {conservada} "
            "del certificado, que es la que tocaba conservar. No se entrega.")
    _admitir(imagenes[0], admitidos)
    for ref in formularios:
        _capa_de_texto(ref, lector, k=k, admitidos=admitidos)
    nombres = set(xobjetos.keys())
    for operandos, operador in _operaciones(pagina.get_contents(), lector,
                                            que=f"la página {k}"):
        if operador not in _OPERADORES_PAGINA:
            raise _fuera_de_perfil(f"el operador «{operador.decode('latin-1', 'replace')}» "
                                   f"en el contenido de la página {k}")
        if operador == b"Do" and (not operandos or str(operandos[0]) not in nombres):
            raise _fuera_de_perfil(f"un «Do» a algo que no está en la página {k}")
    for clave in ("/Resources", "/MediaBox", "/CropBox", "/Rotate", "/Type"):
        if clave in pagina:
            _referencia(pagina, clave, admitidos)
    if "/XObject" in recursos:
        _referencia(recursos, "/XObject", admitidos)
    if "/ProcSet" in recursos:
        _admitir(recursos.raw_get("/ProcSet"), admitidos)
    _admitir(pagina.raw_get("/Contents"), admitidos)


def _recorrer_nodos(ref, admitidos: set[int]) -> None:
    """El árbol de páginas: sus nodos intermedios no llevan nada heredable (recursos,
    cajas, giro), que colaría en las páginas lo que ellas no dicen."""
    from pypdf.generic import IndirectObject

    pendientes = [ref]
    while pendientes:
        r = pendientes.pop()
        if isinstance(r, IndirectObject):
            if r.idnum in admitidos:
                continue
            admitidos.add(r.idnum)
        nodo = r.get_object()
        if nodo.get("/Type") != "/Pages":
            continue
        ajenas = set(nodo.keys()) - _NODO_PAGINAS
        if ajenas:
            raise _fuera_de_perfil(f"«{min(ajenas)}» en un nodo del árbol de páginas")
        _referencia(nodo, "/Kids", admitidos)
        pendientes += list(nodo["/Kids"])


def verificar_aportable(pdf: bytes, recorte: Recorte) -> None:
    """La tercera parada: se relee el aportable ENTERO —el fichero, no sus páginas
    visibles— contra su perfil y contra la imagen del recorte (R2/H-01).

    1. Tantas páginas como las conservadas.
    2. **El perfil**: cada página lleva su imagen —byte a byte la del raster, que el OCR
       no toca— y, como mucho, una capa de texto invisible; el catálogo, el árbol y los
       metadatos, lo mínimo. Y **ningún objeto del fichero puede quedar suelto**: todo
       tiene que colgar de algo admitido. La relectura de la R1 buscaba huellas de lo
       prohibido y aceptaba lo que no conocía; un stream reescrito con otros bytes la
       pasaba (R2/H-01).
    3. **Lo que el OCR lee**: ni el rótulo en ninguna página, ni una página que se parezca
       más a una retirada —o a su vecina— que a la que tocaba. Es el instrumento
       independiente del raster: si la imagen de otra página acabara en su sitio, el texto
       de la imagen lo diría.
    """
    lector = _lector(pdf, que="el aportable")
    if lector.is_encrypted:
        raise _fuera_de_perfil("cifrado")
    paginas = list(lector.pages)
    if len(paginas) != len(recorte.conservadas):
        raise AportableError(
            f"el aportable tiene {len(paginas)} páginas y debían ser "
            f"{len(recorte.conservadas)}. No se entrega.")
    raster = _lector(recorte.imagen, que="la imagen del recorte")
    esperadas, cajas = [], []
    for pagina in raster.pages:
        (imagen,) = [x.get_object() for x in pagina["/Resources"]["/XObject"].values()]
        esperadas.append(_huella_imagen(imagen))
        cajas.append([float(v) for v in pagina.mediabox])

    admitidos: set[int] = set()
    _referencia(lector.trailer, "/Root", admitidos)
    catalogo = lector.trailer["/Root"]
    ajenas = set(catalogo.keys()) - _CATALOGO
    if ajenas:
        raise _fuera_de_perfil(f"«{min(ajenas)}» en su catálogo")
    if "/Metadata" in catalogo:
        if lleva_rotulo(catalogo["/Metadata"].get_data().decode("utf-8", "replace")):
            raise AportableError(
                "los metadatos del aportable llevan el rótulo de las condiciones. No se "
                "entrega.")
        _admitir(catalogo.raw_get("/Metadata"), admitidos)
    if "/Info" in lector.trailer:
        info = lector.trailer["/Info"].get_object()
        if any(lleva_rotulo(str(v)) for v in info.values()):
            raise AportableError(
                "la información del aportable lleva el rótulo de las condiciones. No se "
                "entrega.")
        _admitir(lector.trailer.raw_get("/Info"), admitidos)
    _recorrer_nodos(catalogo.raw_get("/Pages"), admitidos)
    for k, (pagina, conservada) in enumerate(zip(paginas, recorte.conservadas), 1):
        _recorrer_pagina(pagina, lector, k=k, conservada=conservada,
                         esperada=esperadas[k - 1], caja=cajas[k - 1], admitidos=admitidos)
    _sin_sueltos(lector, admitidos)
    _lo_que_lee_el_ocr(paginas, recorte)


def _sin_sueltos(lector, admitidos: set[int]) -> None:
    """Ningún objeto del fichero fuera de lo admitido, cuelgue o no del árbol."""
    from pypdf.generic import DictionaryObject, StreamObject

    for num in range(1, int(lector.trailer["/Size"])):
        try:
            objeto = lector.get_object(num)
        except Exception:  # noqa: BLE001 — entradas libres del xref
            continue
        if objeto is None or num in admitidos:
            continue
        if isinstance(objeto, StreamObject) and objeto.get("/Type") in ("/XRef", "/ObjStm"):
            continue
        if isinstance(objeto, DictionaryObject):
            tipo = f"{objeto.get('/Type', '')} {objeto.get('/Subtype', '')}".strip()
            # Sin tipo, sus claves: `/Linearized` o `/Length` dicen más que «sin tipo».
            tipo = tipo or "sin tipo; claves " + " ".join(sorted(objeto.keys())[:5])
        else:
            tipo = type(objeto).__name__
        raise _fuera_de_perfil(
            f"el objeto {num} ({tipo}), que no cuelga de nada que el aportable admita")


def _similitud(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def _lo_que_lee_el_ocr(paginas, recorte: Recorte) -> None:
    """La capa de texto, página a página, contra el texto ORIGINAL del íntegro.

    Medido sobre los reales (M-12): el texto que el OCR lee en cada página se parece a su
    original 0,54-0,95, y a cualquier otra 0,29 como mucho; y lee el rótulo en las dos de
    condiciones y en ninguna más. No hay umbral que calibrar: basta con que la suya gane.
    """
    retiradas = {r.pagina_certificado for r in recorte.retiradas}
    for k, (pagina, n) in enumerate(zip(paginas, recorte.conservadas), 1):
        leido = normalizar_pagina(pagina.extract_text() or "")
        if lleva_rotulo(leido):
            raise AportableError(
                f"la página {k} del aportable lleva el rótulo de las condiciones en su capa "
                "de texto: el OCR lo lee en la imagen. No se entrega.")
        propio = recorte.normal[n - 1]
        if len(leido) < MIN_CARACTERES or len(propio) < MIN_CARACTERES:
            continue
        suya = _similitud(leido, propio)
        vecinas = {n - 1, n + 1} & set(range(1, recorte.paginas_totales + 1))
        for j in sorted(retiradas | vecinas):
            retirada = j in retiradas
            m = difflib.SequenceMatcher(None, leido, recorte.normal[j - 1], autojunk=False)
            if m.quick_ratio() < suya:
                continue
            otra = m.ratio()
            if otra > suya or (retirada and otra >= suya):
                raise AportableError(
                    f"la página {k} del aportable se parece más a la página {j} del "
                    f"certificado{', que se retira,' if retirada else ''} que a la {n}, que "
                    f"es la que tocaba conservar ({otra:.2f} contra {suya:.2f}). No se "
                    "entrega.")


# --- los avisos -----------------------------------------------------------------

#: Palabras por frase al buscar las condiciones en lo que se conserva (M-6). Con 8,
#: cero coincidencias en los tres certificados reales, acta incluida; con 5 o 6 saltan
#: el IBAN de la factura y «de la Oferta Vinculante Confidencial».
PALABRAS_AVISO = 8

_RE_PALABRA = re.compile(r"[a-z0-9]+(?:[.,%][a-z0-9]+)*%?")
_DESPEDIDA = ("sin", "otro", "particular")


def _palabras(texto: str) -> list[str]:
    sin_cabecera = _CABECERA_REPRODUCCION.sub("", sin_ligaduras(texto or ""))
    return _RE_PALABRA.findall(_plano(sin_cabecera))


def _cuerpos(condiciones: Sequence[PaginaCondiciones]) -> list[list[str]]:
    """Las palabras propias de las condiciones, UNA lista por documento: tras el rótulo y
    antes de SU despedida.

    Lo de antes del rótulo es membrete, requerido y referencia, y lo de después de «Sin
    otro particular», la despedida y la firma: las dos cosas las comparte con el
    requerimiento, y sin cortarlas el aviso saltaría en todo envío (M-6).

    **Por documento** (R1/H-06): con un solo corte sobre todas las palabras juntas, la
    despedida del primer documento dejaba fuera del aviso el cuerpo entero del segundo.
    """
    por_documento: dict[str, list[str]] = {}
    for c in condiciones:
        propias = _palabras(c.texto)
        # El rótulo, entre las palabras y no por líneas (R1/H-02): partido por la
        # extracción sigue siendo «confidencial» seguido de «condiciones».
        inicio = next((n + 2 for n in range(len(propias) - 1)
                       if propias[n:n + 2] == ["confidencial", "condiciones"]), 0)
        por_documento.setdefault(c.documento, []).extend(propias[inicio:])
    cuerpos = []
    for palabras in por_documento.values():
        fin = next((n for n in range(len(palabras) - len(_DESPEDIDA) + 1)
                    if tuple(palabras[n:n + len(_DESPEDIDA)]) == _DESPEDIDA), len(palabras))
        cuerpos.append(palabras[:fin])
    return cuerpos


def _frases(palabras: list[str]) -> set[tuple[str, ...]]:
    return {tuple(palabras[n:n + PALABRAS_AVISO])
            for n in range(len(palabras) - PALABRAS_AVISO + 1)}


def _avisos_de_fuga(conservadas: dict[int, str],
                    condiciones: Sequence[PaginaCondiciones]) -> list[str]:
    """¿Repite alguna página que se conserva frases de las condiciones? (spec §7.4)

    Es el aviso del §7.4 rehecho sobre lo medido: el spec pedía comprobar que el
    requerimiento no llevara cifras, y el requerimiento real lleva la deuda en euros
    (M-2), así que habría saltado siempre. Lo que distingue una fuga es el texto de las
    propias condiciones. **Aviso, no parada**, como dice el spec: nombra la página y la
    frase y decide una persona.
    """
    frases: set[tuple[str, ...]] = set()
    for cuerpo in _cuerpos(condiciones):
        frases |= _frases(cuerpo)
    avisos = []
    for pagina, texto in conservadas.items():
        comunes = frases & _frases(_palabras(texto))
        if comunes:
            avisos.append(
                f"la página {pagina} del certificado repite {len(comunes)} frase(s) de "
                f"las condiciones (p. ej. «{' '.join(min(comunes))}»): puede estar "
                "revelando su contenido. Revísala antes de aportar.")
    return avisos


def _avisos_de_arrastre(condiciones: Sequence[PaginaCondiciones]) -> list[str]:
    """Las páginas que salen por seguir a la de condiciones sin llevar el rótulo."""
    return [f"la página {c.pagina} de {c.documento!r} se retira por seguir a la de "
            "condiciones y no lleva el rótulo: comprueba que no es parte del "
            "requerimiento ni de la OVC, porque entonces el aportable pierde prueba."
            for c in condiciones if not lleva_rotulo(c.texto)]


# --- el manifiesto --------------------------------------------------------------

AVISO_FIRMA = (
    "El aportable es un documento DERIVADO y no conserva la firma electrónica del "
    "prestador: recortar páginas la rompe (spec §7.2), y con ella la presunción del art. "
    "326.4 LEC. La prueba custodiada es el certificado íntegro, con la huella que figura "
    "en este manifiesto.")

#: Qué es el aportable, dicho donde se archiva (R2/H-01).
FORMA_APORTABLE = (f"la imagen de cada página que se conserva, a {PPP} ppp, con una capa "
                   "de texto invisible leída por OCR")

AVISO_TEXTO = (
    "El texto del aportable lo ha leído un OCR sobre su imagen: sirve para buscarlo y "
    "leerlo, y puede tener errores de reconocimiento. El texto fiel es el del certificado "
    "íntegro.")


def manifiesto_de(recorte: Recorte, *, id_envio: str, canal: str, id_personalizado: str,
                  generado: str, integro_nombre: str, integro_sha256: str,
                  aportable_nombre: str, aportable_sha256: str, emisor: dict,
                  ficheros_acta: Sequence[FicheroListado],
                  documentos: Sequence[DocumentoEnviado],
                  avisos_extra: Sequence[str] = (),
                  destinatario: dict | None = None) -> dict:
    """El manifiesto del aportable (spec §7.4): qué se retiró, de dónde y con qué huellas.

    Las huellas van **tal como las lista el acta** (`acta.ficheros_listados`) y, aparte,
    las de los documentos con que se localizaron las condiciones: en un burofax el acta
    lista UN fichero fundido (M-4) y los documentos son los del correo. Las páginas
    retiradas van en las tres numeraciones del §7.3.

    La huella del aportable la da quien lo ESCRIBE (`aportable_sha256`): el OCR no es
    determinista y el recorte no sabe qué bytes saldrán. Lo que se sabe del
    `destinatario` va en su propia clave (R2/H-04): depende del CRM del día en que se
    generó, y no es identidad del aportable.
    """
    manifiesto = {
        "version": 2,
        "id_envio": id_envio,
        "canal": canal,
        "id_personalizado": id_personalizado,
        "generado": generado,
        "integro": {"fichero": integro_nombre, "sha256": integro_sha256,
                    "paginas": recorte.paginas_totales},
        "aportable": {"fichero": aportable_nombre, "sha256": aportable_sha256,
                      "paginas": len(recorte.conservadas), "forma": FORMA_APORTABLE},
        "emisor": dict(emisor),
        "acta": {"paginas": list(recorte.paginas_acta),
                 "ficheros_listados": [{"nombre": f.nombre, "sha256": f.sha256}
                                       for f in ficheros_acta]},
        "documentos_enviados": [{"nombre": d.nombre, "sha256": d.sha256}
                                for d in documentos],
        "reproduccion": {"paginas_certificado": list(recorte.paginas_reproduccion)},
        "retiradas": [dataclasses.asdict(r) for r in recorte.retiradas],
        "conservadas": list(recorte.conservadas),
        "firma": AVISO_FIRMA,
        "texto": AVISO_TEXTO,
        "avisos": [*avisos_extra, *recorte.avisos],
    }
    if destinatario is not None:
        manifiesto["destinatario"] = {"comprobado": bool(destinatario["comprobado"]),
                                      "avisos": list(destinatario["avisos"])}
    return manifiesto
