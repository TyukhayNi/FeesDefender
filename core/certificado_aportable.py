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

**Y el fichero lo COMPONE este motor** (R3): el OCR devuelve líneas —texto y caja— y
nada más, y el aportable se escribe aquí, byte a byte, con una forma fija. Hasta la R3 el
PDF lo escribía el OCR y la relectura lo admitía por una lista blanca, y un fichero ajeno
tiene más sitios donde llevar algo que los que una lista enumera: revisiones anteriores,
objetos de otra generación, datos auxiliares de una fuente (R3/H-01, H-02). La relectura
ya no admite: **recompone** el fichero con la imagen del recorte y el texto que lleva, y
exige los mismos bytes.

Este módulo es puro: recibe bytes y devuelve bytes y datos. No sabe qué es un
expediente ni toca la red o el disco, y el OCR le llega como un puerto (`ocr`); de dónde
salen el certificado y los documentos enviados, y dónde se escribe, lo decide
`core/expedicion_certificada.py`.

Lo gobiernan mediciones del 2026-09-25 sobre tres certificados reales y los adjuntos
de dos de ellos (plan `docs/superpowers/plans/2026-09-25-codicert-f3.md`, M-1 a M-15).
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


def _con_caja(texto: str) -> str:
    """Ligaduras deshechas, guiones unificados y sin tildes, con sus mayúsculas."""
    t = sin_ligaduras(texto or "").translate(_GUIONES)
    t = unicodedata.normalize("NFKD", t)
    return "".join(c for c in t if not unicodedata.combining(c))


def _plano(texto: str) -> str:
    """Ligaduras deshechas, guiones unificados, sin tildes y en minúsculas."""
    return _con_caja(texto).lower()


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
#: El rótulo como TÍTULO (R2/H-03, R3/H-05): la frase abriendo una línea —puede venir
#: partida en varias— y, en la línea donde acaba, NADA EN MINÚSCULA detrás.
_RE_TITULO = re.compile(r"^[ \t]*confidencial\s*-\s*condiciones\b(?P<resto>[^\n]*)",
                        re.M | re.I)


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
    """¿Abre la página las condiciones, con el rótulo como TÍTULO? (R2/H-03, R3/H-05)

    Desde la R1 bastaba la frase en cualquier sitio, y un requerimiento que CITARA el
    título («El anexo se titula “CONFIDENCIAL - CONDICIONES”») se retiraba entero como si
    fuera condiciones. La R2 exigió que la frase abriera una línea, y una cita que la
    extracción partiera justo delante del rótulo («El anexo se titula» / «CONFIDENCIAL -
    CONDICIONES y se adjunta…») volvía a abrirlas (R3/H-05). Un título no lleva prosa
    delante **ni detrás**: lo que le sigue en su línea no tiene minúsculas —«ECONÓMICAS
    DE PAGO» sí vale, «y se adjunta» no—. Los dos rótulos reales van solos en su línea
    (M-14). La mención no se retira en silencio: para (`paginas_de_condiciones`, y la
    segunda parada de `recortar` en lo que no pasa por ahí).
    """
    return any(not any(c.islower() for c in m.group("resto"))
               for m in _RE_TITULO.finditer(_con_caja(texto)))


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

    **Y una página que menciona el rótulo sin que sea su título, ANTES de él, para**
    (R3/H-05): es una cita o unas condiciones con otro formato, y ni se retira en silencio
    ni se deja pasar. Lo que va detrás del título sale con él, mencione lo que mencione.
    """
    salida: list[PaginaCondiciones] = []
    for doc in documentos:
        textos = _textos_pdf(doc.contenido, que=doc.nombre)
        inicio = next((n for n, t in enumerate(textos) if abre_condiciones(t)), len(textos))
        for n in range(inicio):
            if lleva_rotulo(textos[n]):
                raise AportableError(
                    f"la página {n + 1} de {doc.nombre!r} menciona el rótulo "
                    f"«{LITERAL_CONDICIONES}» sin que sea su título —con prosa delante, o "
                    "con texto en minúscula detrás en la misma línea—: puede ser una cita o "
                    "unas condiciones con otro formato. Ni se retira en silencio ni se deja "
                    "pasar: revísala. No se produce aportable.")
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
#: página, contra ~362 a 150. **Tiene que dividir a 7.200** —200 y 72 lo hacen—: así cada
#: píxel son centésimas de punto exactas en el aportable (`_cp`).
PPP = 200
CALIDAD_JPEG = 85

#: Reducción de las miniaturas con que se casan páginas (M-13): 1/8 promedia el ruido del
#: JPEG y deja lo que distingue una página de otra, dónde hay tinta.
ESCALA_MINIATURA = 8


@dataclass(frozen=True)
class PaginaRetirada:
    """Una página que sale del aportable, en las TRES numeraciones (spec §7.3)."""

    pagina_certificado: int
    pagina_reproduccion: int
    documento: str
    pagina_documento: int
    similitud: float


@dataclass(frozen=True)
class ImagenDePagina:
    """La imagen de una página que se conserva: su JPEG y su tamaño en píxeles."""

    jpeg: bytes = field(repr=False)
    ancho: int
    alto: int


@dataclass(frozen=True)
class Recorte:
    """Qué se conserva y qué se retira, con la IMAGEN de lo conservado (R2/H-01).

    Aún no es el aportable: le falta la capa de texto, que lee el OCR y compone
    `aportable_de`. Las imágenes son deterministas —mismos bytes en cada corrida— y son
    las que la relectura usa para recomponer el aportable (R3).
    """

    imagenes: tuple[ImagenDePagina, ...]
    paginas_totales: int
    paginas_acta: tuple[int, ...]
    paginas_reproduccion: tuple[int, ...]
    retiradas: tuple[PaginaRetirada, ...]
    conservadas: tuple[int, ...]
    avisos: tuple[str, ...] = ()
    #: El texto normalizado de CADA página del íntegro (índice = página - 1): con él se
    #: compara lo que el OCR lee en cada imagen.
    normal: tuple[str, ...] = field(default=(), repr=False)
    #: La miniatura de CADA página del íntegro, dibujada aparte de las imágenes
    #: (`_miniaturas`): contra ellas se casa lo que el aportable dibuja (R3/H-04).
    miniaturas: tuple = field(default=(), repr=False, compare=False)
    #: Las páginas de condiciones con que se recortó: sus frases son las que se buscan en
    #: lo que el OCR lee (R3, el escaneo).
    condiciones: tuple[PaginaCondiciones, ...] = field(default=(), repr=False)


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


def _documento_pdfium(datos: bytes, *, que: str):
    """El PDF abierto con PDFium. Uno que no se puede abrir es `AportableError`."""
    import pypdfium2 as pdfium

    try:
        return pdfium.PdfDocument(datos)
    except Exception as exc:  # noqa: BLE001 — pdfium lanza su propio error ante un PDF roto
        raise AportableError(
            f"{que} no se puede dibujar ({type(exc).__name__}: {exc})") from exc


def _dibujar(hoja, *, escala: float):
    """Una página dibujada por PDFium, en RGB y **sin anotaciones ni formularios**: el
    widget de la firma pintaría un sello sin firma detrás (M-8)."""
    return hoja.render(scale=escala, draw_annots=False,
                       may_draw_forms=False).to_pil().convert("RGB")


def _miniatura(imagen):
    return imagen.convert("RGB").reduce(ESCALA_MINIATURA)


def _rasterizar(certificado: bytes, paginas: Sequence[int]) -> tuple[ImagenDePagina, ...]:
    """La IMAGEN de esas páginas (base 1), en su orden: un JPEG por página (R2/H-01).

    Una página cada vez —un burofax de 200 no cabe entero en memoria a esta resolución—.
    Es determinista: los mismos bytes en cada corrida (M-8).
    """
    documento = _documento_pdfium(certificado, que="el certificado")
    imagenes = []
    try:
        for numero in paginas:
            imagen = _dibujar(documento[numero - 1], escala=PPP / 72)
            jpeg = io.BytesIO()
            imagen.save(jpeg, format="JPEG", quality=CALIDAD_JPEG)
            imagenes.append(ImagenDePagina(jpeg=jpeg.getvalue(), ancho=imagen.width,
                                           alto=imagen.height))
    finally:
        documento.close()
    return tuple(imagenes)


def _miniaturas(certificado: bytes) -> tuple:
    """La miniatura de CADA página del íntegro, dibujada aparte de `_rasterizar` (R3/H-04).

    Es el instrumento independiente de la imagen: si `_rasterizar` pusiera una página en
    el sitio de otra, la relectura lo ve porque casa lo que el aportable DIBUJA contra
    estas, que no salen de él.
    """
    documento = _documento_pdfium(certificado, que="el certificado")
    try:
        return tuple(_miniatura(_dibujar(documento[n], escala=PPP / 72))
                     for n in range(len(documento)))
    finally:
        documento.close()


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
    ya compuesto (`verificar_aportable`).

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
    return Recorte(imagenes=_rasterizar(certificado, conservadas), paginas_totales=total,
                   paginas_acta=tuple(acta), paginas_reproduccion=reproduccion,
                   retiradas=tuple(retiradas[n] for n in sorted(retiradas)),
                   conservadas=conservadas, avisos=tuple(avisos), normal=todas,
                   miniaturas=_miniaturas(certificado), condiciones=tuple(condiciones))


# --- el aportable: lo compone este motor ----------------------------------------

@dataclass(frozen=True)
class Linea:
    """Un renglón leído por el OCR: su texto y su caja, en píxeles de la imagen, con el
    origen arriba a la izquierda —como los da Tesseract—.

    Es TODO lo que el OCR entrega (R3/H-04, «acotar su salida»): el aportable lo compone el
    motor con esto, y nada del OCR —su PDF, su estructura, sus metadatos— llega a él.
    """

    texto: str
    x0: int
    y0: int
    x1: int
    y1: int


@dataclass(frozen=True)
class Aportable:
    """El aportable compuesto y releído, con los avisos de lo que el OCR lee en él."""

    pdf: bytes = field(repr=False)
    avisos: tuple[str, ...] = ()


def _cp(pixeles: int) -> int:
    """Píxeles de la imagen a centésimas de punto: exactas, porque `PPP` divide a 7.200."""
    centesimas, resto = divmod(round(pixeles) * 7200, PPP)
    if resto:
        raise ValueError(f"{PPP} ppp no da centésimas de punto exactas: PPP tiene que "
                         "dividir a 7.200")
    return centesimas


def _num(centesimas: int) -> str:
    """Un número del aportable: centésimas de punto con sus dos decimales, sin coma flotante."""
    return f"{centesimas // 100}.{centesimas % 100:02d}"


def _texto_canonico(texto: str) -> str:
    """Lo que se escribe de un renglón: ligaduras y formas compatibles deshechas (NFKC),
    controles y separadores raros como espacios, los espacios juntos en uno, y lo que no
    cabe en WinAnsi como «?» —el castellano cabe entero—.

    Es IDEMPOTENTE —aplicado a su salida la deja igual—, y eso es lo que permite a la
    relectura recomponer el fichero con el texto que lee de él.
    """
    t = unicodedata.normalize("NFKC", texto or "")
    t = "".join(" " if unicodedata.category(c)[0] in "CZ" else c for c in t)
    return " ".join(t.split()).encode("cp1252", errors="replace").decode("cp1252")


@dataclass(frozen=True)
class _Renglon:
    """Un renglón tal como se escribe: su texto canónico y, en centésimas de punto, dónde
    empieza, su línea base y su cuerpo."""

    texto: str
    x: int
    y: int
    cuerpo: int


def _renglones(lineas: Sequence[Linea], imagen: ImagenDePagina, *,
               k: int) -> tuple[_Renglon, ...]:
    """Las líneas del OCR como renglones: cada una en su sitio, a la altura de su caja. Una
    que no cae en la imagen para; una que se queda sin texto no se escribe."""
    salida = []
    for linea in lineas:
        if not (0 <= linea.x0 < linea.x1 <= imagen.ancho
                and 0 <= linea.y0 < linea.y1 <= imagen.alto):
            raise AportableError(
                f"el OCR devolvió una línea fuera de la imagen de la página {k} del "
                f"aportable ({linea.x0}, {linea.y0}, {linea.x1}, {linea.y1} en "
                f"{imagen.ancho}×{imagen.alto}): no se compone con lo que no cae en ella.")
        texto = _texto_canonico(linea.texto)
        if texto:
            salida.append(_Renglon(texto, x=_cp(linea.x0), y=_cp(imagen.alto - linea.y1),
                                   cuerpo=_cp(linea.y1 - linea.y0)))
    return tuple(salida)


def _contenido(imagen: ImagenDePagina, renglones: Sequence[_Renglon]) -> bytes:
    """El contenido de una página: la imagen a página completa y, encima, un renglón de
    texto INVISIBLE —modo de render 3— por línea leída, en Helvetica, que es una de las
    catorce estándar y no lleva programa de fuente."""
    ancho, alto = _num(_cp(imagen.ancho)), _num(_cp(imagen.alto))
    partes = [f"q {ancho} 0 0 {alto} 0 0 cm /Im0 Do Q\nBT 3 Tr\n".encode("ascii")]
    partes += [f"/F1 {_num(r.cuerpo)} Tf 1 0 0 1 {_num(r.x)} {_num(r.y)} Tm "
               f"<{r.texto.encode('cp1252').hex()}> Tj\n".encode("ascii") for r in renglones]
    partes.append(b"ET\n")
    return b"".join(partes)


_CATALOGO = b"<< /Type /Catalog /Pages 2 0 R >>"
_FUENTE = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"


def _flujo(diccionario: str, datos: bytes) -> bytes:
    return (f"<< {diccionario}/Length {len(datos)} >>\nstream\n".encode("ascii") + datos
            + b"\nendstream")


def _componer(imagenes: Sequence[ImagenDePagina],
              renglones: Sequence[Sequence[_Renglon]]) -> bytes:
    """El aportable, byte a byte: catálogo, árbol de páginas, la fuente, y por cada página
    su diccionario, su contenido (`_contenido`) y su imagen. Nada más: ni metadatos, ni
    revisiones, ni objetos que no se usen, ni compresión que dependa de la versión de una
    biblioteca. La misma entrada da los mismos bytes.

    Un renglón que cae fuera de su página, o cuyo texto no es canónico, para: el motor no
    lo escribe así, y la relectura compone con lo que lee —recomponer un texto raro daría
    los mismos bytes raros—.
    """
    objetos: list[bytes] = [_CATALOGO, b"", _FUENTE]
    hojas: list[int] = []
    for k, (imagen, suyos) in enumerate(zip(imagenes, renglones, strict=True), 1):
        ancho, alto = _cp(imagen.ancho), _cp(imagen.alto)
        for r in suyos:
            if not (0 <= r.x < ancho and 0 <= r.y < alto and r.cuerpo > 0
                    and r.y + r.cuerpo <= alto):
                raise AportableError(
                    f"el aportable lleva una línea de texto fuera de la página {k}: no la "
                    "compuso este motor. No se entrega.")
            if not r.texto or _texto_canonico(r.texto) != r.texto:
                raise AportableError(
                    f"el aportable lleva en la página {k} un texto que no compuso este motor "
                    f"({r.texto[:40]!r}): no es la forma en que escribe lo que el OCR lee. "
                    "No se entrega.")
        numero = len(objetos) + 1
        hojas.append(numero)
        objetos.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {_num(ancho)} {_num(alto)}] "
            f"/Resources << /XObject << /Im0 {numero + 2} 0 R >> /Font << /F1 3 0 R >> >> "
            f"/Contents {numero + 1} 0 R >>".encode("ascii"))
        objetos.append(_flujo("", _contenido(imagen, suyos)))
        objetos.append(_flujo(
            f"/Type /XObject /Subtype /Image /Width {imagen.ancho} /Height {imagen.alto} "
            "/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode ", imagen.jpeg))
    objetos[1] = (f"<< /Type /Pages /Kids [{' '.join(f'{n} 0 R' for n in hojas)}] "
                  f"/Count {len(hojas)} >>").encode("ascii")
    salida = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    posiciones = []
    for numero, objeto in enumerate(objetos, 1):
        posiciones.append(len(salida))
        salida += f"{numero} 0 obj\n".encode("ascii") + objeto + b"\nendobj\n"
    xref = len(salida)
    salida += f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n".encode("ascii")
    salida += b"".join(f"{p:010d} 00000 n \n".encode("ascii") for p in posiciones)
    salida += (f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\n"
               f"startxref\n{xref}\n%%EOF\n").encode("ascii")
    return bytes(salida)


def aportable_de(recorte: Recorte, *, ocr: Callable[[bytes], Sequence[Linea]]) -> Aportable:
    """El aportable: la imagen de cada página que se conserva con su texto, COMPUESTO aquí
    y releído (R3).

    `ocr` recibe el JPEG de UNA página y devuelve las líneas que lee (`Linea`). Solo ve
    esos píxeles —no el íntegro—, y lo que devuelve no llega al aportable más que como
    renglones que escribe este motor (R3/H-01, H-02). **Sin capa de texto no hay
    aportable** (lo que Nikolai pidió es que se pueda leer): si el OCR falla, para. Y el
    resultado se relee entero (`verificar_aportable`), con los avisos de lo que el OCR lee.
    """
    renglones = []
    for k, (imagen, n) in enumerate(zip(recorte.imagenes, recorte.conservadas), 1):
        try:
            lineas = ocr(imagen.jpeg)
        except Exception as exc:  # noqa: BLE001 — el OCR es externo: falle como falle, se para
            raise AportableError(
                f"no se pudo pasar el OCR sobre la imagen de la página {k} del aportable "
                f"(la {n} del certificado) ({type(exc).__name__}: {exc}): sin su capa de "
                "texto no se entrega el aportable.") from exc
        if not isinstance(lineas, (list, tuple)) or not all(
                isinstance(l, Linea) and isinstance(l.texto, str) for l in lineas):
            raise AportableError(
                f"el OCR no devolvió líneas para la página {k} del aportable (devolvió "
                f"{type(lineas).__name__}): no se compone con lo que no se sabe qué es.")
        renglones.append(_renglones(lineas, imagen, k=k))
    pdf = _componer(recorte.imagenes, renglones)
    return Aportable(pdf=pdf, avisos=verificar_aportable(pdf, recorte))


# --- la relectura: se recompone, se dibuja y se lee ---------------------------------

#: El contenido que escribe `_contenido`, y nada más: si una página lleva otra cosa, no la
#: compuso este motor. Los números no se fijan aquí; los fija la recomposición.
_RE_CONTENIDO = re.compile(
    rb"q \d+\.\d\d 0 0 \d+\.\d\d 0 0 cm /Im0 Do Q\nBT 3 Tr\n"
    rb"(?P<renglones>(?:/F1 \d+\.\d\d Tf 1 0 0 1 \d+\.\d\d \d+\.\d\d Tm "
    rb"<(?:[0-9a-f]{2})+> Tj\n)*)ET\n")
_RE_RENGLON = re.compile(
    rb"/F1 (\d+)\.(\d\d) Tf 1 0 0 1 (\d+)\.(\d\d) (\d+)\.(\d\d) Tm <((?:[0-9a-f]{2})+)> Tj\n")


def _centesimas(enteros: bytes, decimales: bytes) -> int:
    return int(enteros) * 100 + int(decimales)


def _leer_renglones(pdf: bytes, recorte: Recorte) -> tuple[tuple[_Renglon, ...], ...]:
    """Los renglones de cada página del aportable, leídos de su contenido. Un contenido que
    no tiene la forma que escribe `_contenido` para: no lo compuso este motor."""
    from pypdf.generic import StreamObject

    lector = _lector(pdf, que="el aportable")
    if lector.is_encrypted:
        raise AportableError("el aportable está cifrado, y este motor no cifra. No se entrega.")
    paginas = list(lector.pages)
    if len(paginas) != len(recorte.conservadas):
        raise AportableError(
            f"el aportable tiene {len(paginas)} páginas y debían ser "
            f"{len(recorte.conservadas)}. No se entrega.")
    salida = []
    for k, pagina in enumerate(paginas, 1):
        forma = AportableError(
            f"la página {k} del aportable no tiene la forma que compone este motor: su "
            "contenido no es solo la imagen y un renglón invisible por línea leída. No se "
            "entrega.")
        try:
            flujo = pagina["/Contents"].get_object()
            datos = flujo.get_data() if isinstance(flujo, StreamObject) else None
        except Exception:  # noqa: BLE001 — un contenido que pypdf no sabe leer
            datos = None
        coincide = _RE_CONTENIDO.fullmatch(datos) if datos is not None else None
        if coincide is None:
            raise forma
        suyos = []
        for r in _RE_RENGLON.finditer(coincide.group("renglones")):
            try:
                texto = bytes.fromhex(r[7].decode("ascii")).decode("cp1252")
            except (UnicodeDecodeError, ValueError):
                raise forma from None
            suyos.append(_Renglon(texto, x=_centesimas(r[3], r[4]),
                                  y=_centesimas(r[5], r[6]), cuerpo=_centesimas(r[1], r[2])))
        salida.append(tuple(suyos))
    return tuple(salida)


#: Diferencia máxima, en niveles de 0 a 255, entre la miniatura de lo que una página del
#: aportable DIBUJA y la de su imagen (M-15): 0 en los sintéticos y en los dos reales; una
#: página que no dibuja su imagen, 85 como poco.
UMBRAL_DIBUJO = 8

#: Distancia máxima de lo que dibuja una página a la miniatura de la que se conserva
#: (M-15): 0,52 como mucho en los reales, 0,15 en los sintéticos. No separa por sí sola —en
#: un sintético con una hoja casi en blanco, la más cercana de las DEMÁS está a 1,31—: lo
#: que separa es que ninguna otra esté más cerca. Esto es el techo de cordura.
UMBRAL_MINIATURA = 2.0

#: Similitud mínima entre lo que el OCR lee en una página y su texto original (M-13): en
#: los reales, 0,56 como poco con la propia y 0,31 como mucho con otra. No distingue
#: páginas —eso lo hace la imagen—: dice que el texto es de ESA página, y no una marca o
#: nada.
UMBRAL_OCR = 0.30


#: Para dibujar una página del aportable a su tamaño EXACTO (M-15). pypdfium2 calcula el
#: tamaño con `ceil(puntos × escala)`, y PDFium da los puntos en float32: 421,2 pt salen
#: 421,20001220703125, un error relativo de ~3·10⁻⁸ que convertía una imagen de 1.170 px
#: en una de 1.171, redibujada reescalada. El margen tiene que ser mayor que ese error y
#: menor que un píxel: 10⁻⁵ lo es para cualquier página de menos de 100.000 px. El dibujo
#: no cambia: PDFium ajusta la página al tamaño entero que se le pide.
_CASI_UNO = 1 - 1e-5


def _distancia(a, b) -> float:
    """Diferencia media por canal entre dos imágenes del mismo tamaño (0 = iguales)."""
    from PIL import ImageChops, ImageStat

    return sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / 3


def _diferencia(a, b) -> int:
    """La mayor diferencia de un canal en un píxel, entre dos imágenes del mismo tamaño."""
    from PIL import ImageChops

    return max(alto for _, alto in ImageChops.difference(a, b).getextrema())


def verificar_aportable(pdf: bytes, recorte: Recorte) -> tuple[str, ...]:
    """La tercera parada: se relee el aportable, y lo que se relee es el FICHERO (R3/H-01).

    1. **Se recompone.** Se leen sus renglones, se vuelve a componer con la imagen del
       recorte y tiene que dar los mismos bytes. La R2 admitía el fichero de un tercero por
       una lista blanca, y admitía revisiones anteriores, objetos de otra generación y datos
       colgados de una fuente que la lista no enumeraba (R3/H-01, H-02): ahora no se
       enumera nada, porque nada de más cabe en los mismos bytes.
    2. **Ninguna página lleva el rótulo** en su texto.
    3. **Cada página DIBUJA su imagen tal cual** (R3/H-03) —se dibuja el fichero, no se
       miran sus recursos— y **lo que dibuja se parece más a la página que tocaba conservar
       que a cualquier otra del íntegro** (R3/H-04: la R2 solo miraba las retiradas y las
       vecinas, y por texto).
    4. **Cada página con texto trae el suyo** (R3/H-04): sin él, o con uno que no se le
       parece, no se entrega.

    Lo que NO acredita, y se dice: que cada palabra del texto salga de los píxeles. Eso
    descansa en que el OCR solo recibe esos píxeles; aquí se comprueba que el texto se
    parece al de la página y no lleva el rótulo.

    Devuelve los avisos de lo que el OCR lee en una imagen y su texto no dice: un escaneo
    que muestra frases de las condiciones.
    """
    renglones = _leer_renglones(pdf, recorte)
    if _componer(recorte.imagenes, renglones) != pdf:
        raise AportableError(
            "el aportable no es, byte a byte, el que compone este motor con la imagen del "
            "recorte y el texto que lleva: tiene algo más, o algo distinto. No se entrega.")
    leidos = {n: "\n".join(r.texto for r in suyos)
              for n, suyos in zip(recorte.conservadas, renglones)}
    for k, n in enumerate(recorte.conservadas, 1):
        if lleva_rotulo(leidos[n]):
            raise AportableError(
                f"la página {k} del aportable lleva el rótulo de las condiciones en su capa "
                "de texto: el OCR lo lee en la imagen. No se entrega.")
    _comprobar_dibujo(pdf, recorte)
    _comprobar_lectura(leidos, recorte)
    return tuple(_avisos_de_lo_leido(leidos, recorte))


def _comprobar_dibujo(pdf: bytes, recorte: Recorte) -> None:
    """Lo que cada página del aportable DIBUJA es su imagen, y esa imagen es la de la página
    que se conserva (R3/H-03, H-04)."""
    from PIL import Image

    retiradas = {r.pagina_certificado for r in recorte.retiradas}
    documento = _documento_pdfium(pdf, que="el aportable")
    try:
        for k, (imagen, n) in enumerate(zip(recorte.imagenes, recorte.conservadas), 1):
            hoja = documento[k - 1]
            dibujada = _dibujar(hoja, escala=imagen.ancho / hoja.get_width() * _CASI_UNO)
            guardada = Image.open(io.BytesIO(imagen.jpeg)).convert("RGB")
            mini = _miniatura(dibujada)
            if dibujada.size != guardada.size or _diferencia(
                    mini, _miniatura(guardada)) > UMBRAL_DIBUJO:
                raise AportableError(
                    f"la página {k} del aportable no dibuja su imagen tal cual —entera, "
                    "derecha y sin nada encima—. No se entrega.")
            distancias = {j: _distancia(mini, m) for j, m in enumerate(recorte.miniaturas, 1)
                          if m.size == mini.size}
            propia = distancias.get(n, float("inf"))
            # Primero la más cercana: si es otra, el mensaje dice QUÉ página es la imagen,
            # que es lo que hace falta saber ante un error de índices.
            cercana = min((j for j in distancias if j != n),
                          key=lambda j: (distancias[j], j), default=None)
            if cercana is not None and distancias[cercana] < propia:
                raise AportableError(
                    f"la página {k} del aportable se parece más a la página {cercana} del "
                    f"certificado{', que se retira,' if cercana in retiradas else ''} que a "
                    f"la {n}, que es la que tocaba conservar ({distancias[cercana]:.2f} "
                    f"contra {propia:.2f}). No se entrega.")
            if propia > UMBRAL_MINIATURA:
                raise AportableError(
                    f"lo que dibuja la página {k} del aportable no se parece a la página {n} "
                    f"del certificado, que es la que tocaba conservar ({propia:.2f}, y hace "
                    f"falta {UMBRAL_MINIATURA} como mucho). No se entrega.")
            empate = min((j for j in retiradas if distancias.get(j, float("inf"))
                          <= propia), default=None)
            if empate is not None:
                raise AportableError(
                    f"la página {k} del aportable se parece a la página {empate} del "
                    f"certificado, que se retira, tanto como a la {n}, que es la que tocaba "
                    f"conservar ({propia:.2f}). No se entrega.")
    finally:
        documento.close()


def _comprobar_lectura(leidos: dict[int, str], recorte: Recorte) -> None:
    """Cada página cuyo original tiene texto trae el suyo: la R2 admitía un aportable sin
    capa de texto, o con una hecha solo de una marca (R3/H-04)."""
    for k, n in enumerate(recorte.conservadas, 1):
        propio = recorte.normal[n - 1]
        if len(propio) < MIN_CARACTERES:
            continue
        leido = normalizar_pagina(leidos[n])
        if not leido:
            raise AportableError(
                f"la página {k} del aportable no tiene texto leído por el OCR, y la {n} del "
                "certificado sí lo tiene: sin su capa de texto no se entrega.")
        m = difflib.SequenceMatcher(None, leido, propio, autojunk=False)
        parecido = m.quick_ratio()
        if parecido >= UMBRAL_OCR:
            parecido = m.ratio()
        if parecido < UMBRAL_OCR:
            raise AportableError(
                f"el texto que el OCR lee en la página {k} del aportable no se parece al de "
                f"la página {n} del certificado ({parecido:.2f}, y hace falta {UMBRAL_OCR}): "
                "no es su texto. No se entrega.")


def _avisos_de_lo_leido(leidos: dict[int, str], recorte: Recorte) -> list[str]:
    """¿Muestra alguna imagen frases de las condiciones que su texto no lleva? (R3, §2)

    Es el aviso del §7.4 sobre lo que el OCR lee: una página conservada ESCANEADA no tiene
    texto con que avisar, y su imagen puede reproducir las condiciones. Lo que el texto ya
    repite lo avisa el recorte; aquí sale lo que solo está en los píxeles. Aviso, no parada,
    como el del §7.4: nombra la página y la frase y decide una persona.
    """
    frases: set[tuple[str, ...]] = set()
    for cuerpo in _cuerpos(recorte.condiciones):
        frases |= _frases(cuerpo)
    avisos = []
    for n, texto in leidos.items():
        vistas = (frases & _frases(_palabras(texto))) - _frases(_palabras(recorte.normal[n - 1]))
        if vistas:
            avisos.append(
                f"la página {n} del certificado muestra en su imagen {len(vistas)} frase(s) "
                f"de las condiciones que su texto no lleva (p. ej. «{' '.join(min(vistas))}»): "
                "el OCR las lee en los píxeles —¿un escaneo?—. Revísala antes de aportar.")
    return avisos


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

#: Qué es el aportable, dicho donde se archiva (R2/H-01, R3).
FORMA_APORTABLE = (f"la imagen de cada página que se conserva, a {PPP} ppp, con una capa "
                   "de texto invisible leída por OCR: un renglón por línea leída, compuesto "
                   "por FeesDefender")

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

    La huella del aportable la da quien lo ESCRIBE (`aportable_sha256`): el recorte no
    sabe qué líneas leerá el OCR. Lo que se sabe del `destinatario` va en su propia clave
    (R2/H-04): depende del CRM del día en que se generó, y no es identidad del aportable.
    Versión 3 desde la R3: el aportable lo compone el motor, y uno de la versión 2 —el
    que escribía OCRmyPDF— no se relee con estas reglas.
    """
    manifiesto = {
        "version": 3,
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
