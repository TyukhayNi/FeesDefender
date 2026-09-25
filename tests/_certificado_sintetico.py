"""Certificados de Codicert SINTÉTICOS, con la anatomía medida (plan F3, M-1 a M-8).

Nada de aquí sale de un certificado real: los textos son inventados y reproducen solo
la ESTRUCTURA medida —la marca del acta, la cabecera de cada página de la
reproducción, el bloque FICHEROS con la huella partida en dos líneas, el campo de
firma con su widget en la página 1—, que es lo que el recorte usa.
"""
from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass

MARCA_ACTA = ("Este certificado contiene un sello temporal y se encuentra firmado "
              "digitalmente con un certificado reconocido.")


def _cabecera(requerido: str, direccion: str, nif: str, w_code: str) -> str:
    """Membrete, requerido y referencia: lo que las tres páginas del refundido comparten."""
    return (f"EV MMC Spain, S.L.U.\n{requerido}\n{direccion}\n{nif}\n"
            f"REF: {direccion} {w_code} - OFERTA VINCULANTE")


_POR_DEFECTO = dict(requerido="Inmobiliaria Ejemplo Uno S.L.",
                    direccion="Calle Inventada 1, 28001 Madrid", nif="B00000001",
                    w_code="W-000AAA")


def requerimiento(**kw) -> str:
    """El requerimiento. Lleva a propósito las dos cosas que M-2 y M-6 midieron en los
    reales: la deuda en euros y la fórmula «de la Oferta Vinculante Confidencial», que
    comparte con las condiciones y hace saltar en falso un aviso de 5 palabras."""
    d = {**_POR_DEFECTO, **kw}
    return f"""{_cabecera(**d)}
En Madrid, a 01.09.2026.
Les requerimos el pago de los honorarios devengados, adeudando a la fecha
de esta comunicacion la cantidad de 1.234,56 EUR (en adelante, los Honorarios).
Les remitimos para su recepcion las condiciones adjuntas, y la Agencia podra
iniciar un proceso judicial con el mismo objeto de la Oferta Vinculante Confidencial."""


def ovc(**kw) -> str:
    """La OVC. Acaba con la misma palabra que las condiciones antes de «Sin otro
    particular» («pago»), así que sin cortar la despedida compartirían una frase de 8."""
    d = {**_POR_DEFECTO, **kw}
    return f"""{_cabecera(**d)}
OFERTA VINCULANTE CONFIDENCIAL Y PROPUESTA DE NEGOCIACION DIRECTA
La presente oferta vinculante confidencial podra aceptarse en el plazo de
UN MES desde su primera recepcion, conforme a la LO 1/2025.
Las condiciones adjuntas detallan la forma de pago.
Sin otro particular, atentamente
NIKOLAI TYUKHAY
ABOGADO"""


def condiciones(*, fecha: str = "01.09.2026", **kw) -> str:
    d = {**_POR_DEFECTO, **kw}
    return f"""{_cabecera(**d)}
CONFIDENCIAL - CONDICIONES
En Madrid, a {fecha}.
Pago fraccionado de los Honorarios sin intereses. Se abonara en DOS plazos:
a. El primer 50% entre los dias 1 y 5 del mes siguiente a la primera recepcion
de la Oferta Vinculante Confidencial.
b. El segundo 50% entre los dias 20 y 25 del mismo mes siguiente.
Cuenta de pago: deberan efectuar los pagos en la siguiente cuenta bancaria:
CUENTA: ES00 0000 0000 0000 0000 0000
Aceptacion: la oferta se considerara aceptada si la Agencia recibe el primer pago.
Sin otro particular, atentamente
NIKOLAI TYUKHAY
ABOGADO"""


REQUERIMIENTO, OVC, CONDICIONES = requerimiento(), ovc(), condiciones()

#: Las mismas condiciones, de OTRA expedición: otro requerido, otra dirección, otra
#: referencia y otra fecha. Es lo que dio 0,877 en producción (M-3).
CONDICIONES_DE_OTRA = condiciones(requerido="Sociedad Distinta Dos S.L.",
                                  direccion="Avenida Ficticia 99, 46001 Valencia",
                                  nif="B99999999", w_code="W-999ZZZ", fecha="15.08.2026")

#: La factura. Repite la cuenta de las condiciones (M-6: seis palabras en común, que
#: hacen saltar en falso un aviso de 5 o 6) y lleva «Condiciones de pago» (M-7).
FACTURA = """Factura A/R
N documento 0000001
Base 1.020,30
IVA 21 % 214,26
Total EUR 1.234,56
Condiciones de pago a la vista
IBAN ES00 0000 0000 0000 0000 0000
SWIFT BBVAESMMXXX"""


def pdf(paginas: list[str]) -> bytes:
    """Un PDF con una página por cadena y capa de texto.

    `invariant=1`: sin fecha ni identificador aleatorio, así que el mismo texto da los
    mismos bytes y la misma huella — lo que necesita el bloque FICHEROS.
    """
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, invariant=1)
    for texto in paginas:
        y = 800
        for linea in texto.splitlines():
            c.drawString(40, y, linea)
            y -= 14
        c.showPage()
    c.save()
    return buffer.getvalue()


@dataclass(frozen=True)
class Adjunto:
    """Un documento enviado: su nombre y el texto de cada página."""

    nombre: str
    paginas: tuple[str, ...]

    @property
    def contenido(self) -> bytes:
        return pdf(list(self.paginas))


def pagina_emisor(id_envio: str, *, emisor: str, usuario: str, receptor: str,
                  tipo: str) -> str:
    """La página 1 del acta, con los dos bloques que lee `certificado_lectura`."""
    return f"""{MARCA_ACTA}
Código de envío: {id_envio} Página: 1 de 9
COMUNICACIÓN CERTIFICADA
DATOS DE EMISOR Y RECEPTOR
1. Datos del emisor.
Nombre y apellidos/Razón social: {emisor}
CIF: B00000000
2. Datos del receptor.
Enviado a: {receptor}
DATOS DE LA COMUNICACIÓN:
Tipo de envío: {tipo}
CERTIFICADO
Madrid, a 17 de septiembre de 2026
Servicios de MailCertificado S.L. certifica que todos los datos contenidos en el
presente documento corresponden al envio {id_envio} del usuario dado de alta en la
web www.codicert.io con nombre de usuario {usuario}."""


def pagina_ficheros(id_envio: str, listados: list[tuple[str, bytes]]) -> str:
    """La página del acta con el bloque FICHEROS ADJUNTOS: la huella PARTIDA 46 + 18 (M-5)."""
    lineas = [MARCA_ACTA, f"Código de envío: {id_envio} Página: 2 de 9",
              "CERTIFICADO DE CONTENIDO", "FICHEROS ADJUNTOS",
              "Nombre Huella digital (sha256)"]
    for nombre, contenido in listados:
        h = hashlib.sha256(contenido).hexdigest()
        lineas += [f"{nombre} {h[:46]}", h[46:]]
    lineas.append("La autenticidad de este documento puede ser comprobada escaneando el QR")
    return "\n".join(lineas)


def certificado(adjuntos: list[Adjunto], *, id_envio: str = "006sint",
                burofax: bool = False, emisor: str = "EV MMC SPAIN, S.L.U.",
                usuario: str = "madrid.bd", receptor: str = "destino@ejemplo.es",
                reproduccion: list[str] | None = None, acta_extra: str = "") -> bytes:
    """Un certificado sintético: acta (emisor + FICHEROS) y la reproducción de los adjuntos.

    La reproducción son las páginas de los adjuntos EN ORDEN, cada una con la cabecera
    que Codicert le pone (M-3). Con `burofax=True` el acta lista UN fichero de nombre
    UUID, el fundido (M-4). `reproduccion=` la sustituye, para fabricar certificados
    que NO casan con lo enviado; `acta_extra`, texto añadido a la página 1 del acta.
    """
    paginas_doc = [p for a in adjuntos for p in a.paginas]
    if burofax:
        listados = [("9c0dd000-00e0-00e0-00c0-00a00f0000c0.pdf", pdf(paginas_doc))]
        tipo = "Burofax"
    else:
        listados = [(a.nombre, a.contenido) for a in adjuntos]
        tipo = "Entrega Electrónica Certificada"
    acta = [pagina_emisor(id_envio, emisor=emisor, usuario=usuario, receptor=receptor,
                          tipo=tipo) + ("\n" + acta_extra if acta_extra else ""),
            pagina_ficheros(id_envio, listados)]
    cuerpo = paginas_doc if reproduccion is None else reproduccion
    total = len(acta) + len(cuerpo)
    repro = [f"Código de envío: {id_envio} Página: {len(acta) + n} de {total}\n{texto}"
             for n, texto in enumerate(cuerpo, 1)]
    return pdf(acta + repro)


def con_firma(datos: bytes, *, con_padre: bool = False, visible: bool = False) -> bytes:
    """Le pone al PDF un campo de firma con su widget en la página 1, como los reales (M-8).

    `con_padre=True` separa el campo del widget (el widget lleva `/Parent` y el `/FT`
    está en el campo): los reales los fusionan, pero el recorte no puede depender de eso.
    `visible=True` le da una apariencia que PINTA —un recuadro negro—: en los reales no
    pinta nada (medido el 2026-09-25), pero el aportable no puede depender de eso.
    """
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import (ArrayObject, DecodedStreamObject, DictionaryObject,
                               FloatObject, NameObject, NumberObject, TextStringObject)

    escritor = PdfWriter(clone_from=PdfReader(io.BytesIO(datos)))
    widget = DictionaryObject({
        NameObject("/Type"): NameObject("/Annot"),
        NameObject("/Subtype"): NameObject("/Widget"),
        NameObject("/Rect"): ArrayObject([FloatObject(380), FloatObject(30),
                                          FloatObject(560), FloatObject(110)]),
        NameObject("/F"): NumberObject(4),
    })
    if visible:
        apariencia = DecodedStreamObject()
        apariencia.set_data(b"0 g 0 0 180 80 re f")
        apariencia.update({
            NameObject("/Type"): NameObject("/XObject"),
            NameObject("/Subtype"): NameObject("/Form"),
            NameObject("/BBox"): ArrayObject([FloatObject(0), FloatObject(0),
                                              FloatObject(180), FloatObject(80)]),
        })
        widget[NameObject("/AP")] = DictionaryObject(
            {NameObject("/N"): escritor._add_object(apariencia)})
    if con_padre:
        campo = DictionaryObject({NameObject("/FT"): NameObject("/Sig"),
                                  NameObject("/T"): TextStringObject("Signature")})
        ref_campo = escritor._add_object(campo)
        widget[NameObject("/Parent")] = ref_campo
        ref_widget = escritor._add_object(widget)
        campo[NameObject("/Kids")] = ArrayObject([ref_widget])
        campos = ArrayObject([ref_campo])
    else:
        widget[NameObject("/FT")] = NameObject("/Sig")
        widget[NameObject("/T")] = TextStringObject("Signature")
        ref_widget = escritor._add_object(widget)
        campos = ArrayObject([ref_widget])
    escritor.pages[0][NameObject("/Annots")] = ArrayObject([ref_widget])
    escritor._root_object[NameObject("/AcroForm")] = DictionaryObject({
        NameObject("/Fields"): campos, NameObject("/SigFlags"): NumberObject(3)})
    buffer = io.BytesIO()
    escritor.write(buffer)
    return buffer.getvalue()


def con_formularios(datos: bytes) -> bytes:
    """El certificado con la anatomía REAL de la reproducción (H-01 de la R1, medido).

    En los certificados reales cada página de la reproducción es un contenido mínimo
    (`q /TPLn Do Q`) que dibuja un Form XObject, y los formularios de TODAS las páginas
    viven en UN diccionario `/Resources` que comparten todas. Copiar una página copia ese
    diccionario entero: con él viajaría el formulario de la página retirada, invisible en
    el aportable y recuperable de su estructura. Medido sobre `006catetonk`: la página 7
    dibuja `/TPL2`, y `/TPL2` está en los recursos de las ocho.
    """
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import (ArrayObject, DecodedStreamObject, DictionaryObject,
                               FloatObject, NameObject)

    lector = PdfReader(io.BytesIO(datos))
    escritor = PdfWriter()
    paginas = [escritor.add_page(p) for p in lector.pages]
    acta = {n for n, p in enumerate(lector.pages) if "sello temporal" in (p.extract_text() or "")}
    formularios: dict[int, str] = {}
    compartido_xo = DictionaryObject()
    for n, pagina in enumerate(paginas):
        if n in acta:
            continue
        forma = DecodedStreamObject()
        forma.set_data(pagina.get_contents().get_data())
        forma.update({
            NameObject("/Type"): NameObject("/XObject"),
            NameObject("/Subtype"): NameObject("/Form"),
            NameObject("/BBox"): ArrayObject([FloatObject(0), FloatObject(0),
                                              FloatObject(595), FloatObject(842)]),
            NameObject("/Resources"): pagina["/Resources"],
        })
        nombre = f"/TPL{len(formularios)}"
        compartido_xo[NameObject(nombre)] = escritor._add_object(forma)
        formularios[n] = nombre
    base = paginas[0]["/Resources"].get_object()
    compartido = DictionaryObject({NameObject(k): v for k, v in base.items()})
    compartido[NameObject("/XObject")] = compartido_xo
    referencia = escritor._add_object(compartido)
    for n, pagina in enumerate(paginas):
        if n in formularios:
            contenido = DecodedStreamObject()
            contenido.set_data(f"q {formularios[n]} Do Q".encode())
            pagina[NameObject("/Contents")] = escritor._add_object(contenido)
        pagina[NameObject("/Resources")] = referencia
    buffer = io.BytesIO()
    escritor.write(buffer)
    return buffer.getvalue()


def con_enlace_a(datos: bytes, *, desde: int, hacia: int) -> bytes:
    """Un `/Link` con `/Dest` desde la página `desde` a la página `hacia` (base 1).

    Es la sonda del revisor en H-01: la anotación referencia el OBJETO de la página
    destino, y copiarla arrastra esa página entera dentro del PDF aunque no esté en su
    árbol de páginas.
    """
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import (ArrayObject, DictionaryObject, FloatObject, NameObject,
                               NullObject)

    escritor = PdfWriter(clone_from=PdfReader(io.BytesIO(datos)))
    destino = escritor.pages[hacia - 1].indirect_reference
    enlace = DictionaryObject({
        NameObject("/Type"): NameObject("/Annot"),
        NameObject("/Subtype"): NameObject("/Link"),
        NameObject("/Rect"): ArrayObject([FloatObject(40), FloatObject(40),
                                          FloatObject(200), FloatObject(60)]),
        NameObject("/Dest"): ArrayObject([destino, NameObject("/XYZ"), NullObject(),
                                          NullObject(), NullObject()]),
    })
    pagina = escritor.pages[desde - 1]
    pagina[NameObject("/Annots")] = ArrayObject([escritor._add_object(enlace)])
    buffer = io.BytesIO()
    escritor.write(buffer)
    return buffer.getvalue()


def formularios_con_rotulo(datos: bytes) -> list[str]:
    """Los Form XObjects del PDF que, dibujados aparte, llevan el rótulo de condiciones.

    Recorre TODOS los objetos del fichero, no solo los que cuelgan de las páginas: lo que
    importa es qué hay dentro del PDF, no qué se ve. Cada formulario se CLONA —con sus
    propios recursos y fuentes— y se dibuja en una página en blanco, para que su texto se
    pueda extraer; añadirlo sin clonar deja las fuentes fuera y el texto sale ilegible.
    """
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject, StreamObject

    from core.certificado_aportable import lleva_rotulo

    lector = PdfReader(io.BytesIO(datos))
    hallados = []
    for num in range(1, int(lector.trailer["/Size"])):
        try:
            objeto = lector.get_object(num)
        except Exception:  # noqa: BLE001 — entradas libres del xref
            continue
        if not (isinstance(objeto, StreamObject) and objeto.get("/Subtype") == "/Form"):
            continue
        escritor = PdfWriter()
        pagina = escritor.add_blank_page(width=595, height=842)
        clon = objeto.clone(escritor)
        referencia = clon.indirect_reference or escritor._add_object(clon)
        pagina[NameObject("/Resources")] = DictionaryObject({NameObject("/XObject"): DictionaryObject(
            {NameObject("/X"): referencia})})
        contenido = DecodedStreamObject()
        contenido.set_data(b"q /X Do Q")
        pagina[NameObject("/Contents")] = escritor._add_object(contenido)
        buffer = io.BytesIO()
        escritor.write(buffer)
        texto = PdfReader(io.BytesIO(buffer.getvalue())).pages[0].extract_text() or ""
        if lleva_rotulo(texto):
            hallados.append(f"objeto {num}")
    return hallados


def refundido() -> Adjunto:
    """El refundido medido (M-1): requerimiento, OVC y condiciones en un solo PDF."""
    return Adjunto("OVC REFUNDIDA.pdf", (REQUERIMIENTO, OVC, CONDICIONES))


def factura() -> Adjunto:
    return Adjunto("FACTURA 0000001.pdf", (FACTURA,))


# --- R2/H-01: el aportable es IMAGEN ---------------------------------------------

def render(pdf: bytes, pagina: int, *, anotaciones: bool = False, ancho: int | None = None):
    """La página `pagina` (base 1) dibujada a la resolución del aportable.

    Por su cuenta, sin pasar por el código que se prueba: es lo que permite decir si la
    imagen k del aportable es la página que tocaba, y no la que el código cree. Con
    `anotaciones=True`, como la vería un visor: PDFium solo pinta un widget con los
    formularios inicializados, y el resto de anotaciones con `draw_annots` (medido el
    2026-09-25).

    `ancho=` la dibuja EXACTAMENTE a ese ancho en píxeles: pypdfium2 calcula el tamaño con
    `ceil(puntos × escala)`, y PDFium da los puntos en float32, así que sin margen se suma
    un píxel y la página se redibuja reescalada (medido el 2026-09-25, R3, M-15).
    """
    import pypdfium2 as pdfium

    from core.certificado_aportable import PPP

    doc = pdfium.PdfDocument(pdf)
    if anotaciones:
        doc.init_forms()
    hoja = doc[pagina - 1]
    escala = PPP / 72 if ancho is None else ancho / hoja.get_width() * (1 - 1e-5)
    return hoja.render(scale=escala, draw_annots=anotaciones,
                       may_draw_forms=anotaciones).to_pil().convert("RGB")


def con_anotacion_visible(datos: bytes, *, pagina: int, subtipo: str = "/Stamp") -> bytes:
    """Una anotación que PINTA —un recuadro negro— en la página `pagina` (base 1)."""
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import (ArrayObject, DecodedStreamObject, DictionaryObject,
                               FloatObject, NameObject, NumberObject)

    escritor = PdfWriter(clone_from=PdfReader(io.BytesIO(datos)))
    apariencia = DecodedStreamObject()
    apariencia.set_data(b"0 g 0 0 180 80 re f")
    apariencia.update({
        NameObject("/Type"): NameObject("/XObject"),
        NameObject("/Subtype"): NameObject("/Form"),
        NameObject("/BBox"): ArrayObject([FloatObject(0), FloatObject(0),
                                          FloatObject(180), FloatObject(80)]),
    })
    anotacion = DictionaryObject({
        NameObject("/Type"): NameObject("/Annot"),
        NameObject("/Subtype"): NameObject(subtipo),
        NameObject("/Rect"): ArrayObject([FloatObject(380), FloatObject(30),
                                          FloatObject(560), FloatObject(110)]),
        NameObject("/F"): NumberObject(4),
        NameObject("/AP"): DictionaryObject({NameObject("/N"): escritor._add_object(apariencia)}),
    })
    escritor.pages[pagina - 1][NameObject("/Annots")] = ArrayObject(
        [escritor._add_object(anotacion)])
    buffer = io.BytesIO()
    escritor.write(buffer)
    return buffer.getvalue()


def imagenes(pdf: bytes) -> list:
    """La imagen de cada página del PDF, decodificada. Exige UNA por página."""
    from PIL import Image
    from pypdf import PdfReader

    salida = []
    for pagina in PdfReader(io.BytesIO(pdf)).pages:
        xobjetos = pagina["/Resources"].get_object()["/XObject"].get_object()
        (imagen,) = [x.get_object() for x in xobjetos.values()
                     if x.get_object().get("/Subtype") == "/Image"]
        salida.append(Image.open(io.BytesIO(imagen._data)).convert("RGB"))
    return salida


def distancia(a, b) -> float:
    """Diferencia media por canal entre dos imágenes del mismo tamaño (0 = iguales)."""
    from PIL import ImageChops, ImageStat

    return sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / 3


def _escapar(linea: str) -> bytes:
    crudo = linea.encode("cp1252", errors="replace")
    return crudo.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def con_capa_de_texto(pdf: bytes, textos, *, modo: int = 3, fuente: str = "/Type1",
                      operadores: bytes = b"") -> bytes:
    """El PDF con una capa de texto por página, como la deja un OCR: un formulario que
    escribe el texto en modo de render `modo` (3 = invisible) con una fuente estándar, y
    que la página dibuja delante de su imagen.

    `fuente` y `operadores` existen para fabricar capas FUERA del perfil del aportable
    —una fuente Type3, que dibuja; operadores que pintan— y ver que la relectura las para.
    """
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import (ArrayObject, DecodedStreamObject, DictionaryObject,
                               FloatObject, NameObject)

    escritor = PdfWriter(clone_from=PdfReader(io.BytesIO(pdf)))
    datos_fuente = {NameObject("/Type"): NameObject("/Font"),
                    NameObject("/Subtype"): NameObject(fuente),
                    NameObject("/BaseFont"): NameObject("/Helvetica"),
                    NameObject("/Encoding"): NameObject("/WinAnsiEncoding")}
    ref_fuente = escritor._add_object(DictionaryObject(datos_fuente))
    for pagina, texto in zip(escritor.pages, textos):
        alto = float(pagina.mediabox.height)
        lineas = [f"BT {modo} Tr /F1 10 Tf 40 {alto - 40:.0f} Td".encode()]
        lineas += [b"(" + _escapar(linea) + b") Tj 0 -12 Td" for linea in texto.splitlines()]
        lineas += [b"ET", operadores]
        forma = DecodedStreamObject()
        forma.set_data(b"\n".join(lineas))
        forma.update({
            NameObject("/Type"): NameObject("/XObject"),
            NameObject("/Subtype"): NameObject("/Form"),
            NameObject("/BBox"): ArrayObject([FloatObject(0), FloatObject(0),
                                              FloatObject(float(pagina.mediabox.width)),
                                              FloatObject(alto)]),
            NameObject("/Resources"): DictionaryObject({NameObject("/Font"): DictionaryObject(
                {NameObject("/F1"): ref_fuente})}),
        })
        recursos = pagina["/Resources"].get_object()
        recursos["/XObject"].get_object()[NameObject("/OCR")] = escritor._add_object(forma)
        # Como OCRmyPDF: declara los conjuntos de procedimientos de la página.
        recursos[NameObject("/ProcSet")] = ArrayObject(
            [NameObject("/PDF"), NameObject("/ImageC"), NameObject("/Text")])
        # El contenido se reescribe EN SU SITIO: uno nuevo dejaría el viejo huérfano dentro
        # del fichero, y la relectura —con razón— para ante un objeto que no cuelga de nada.
        contenido = pagina["/Contents"].get_object()
        contenido.set_data(b"q /OCR Do Q\n" + contenido.get_data())
    buffer = io.BytesIO()
    escritor.write(buffer)
    return buffer.getvalue()


_RE_ROTULO_OCR = __import__("re").compile(r"(?i)confidencial\s*-\s*condiciones")


@__import__("functools").lru_cache(maxsize=64)
def _candidatas(cert: bytes, ppp: int) -> tuple:
    """Miniatura, texto y número de cada página del certificado, a una resolución. Se
    guarda por certificado y resolución: los tests repiten los mismos, y lo que se prueba
    —el recorte— se ejecuta entero cada vez."""
    from pypdf import PdfReader

    textos = [p.extract_text() or "" for p in PdfReader(io.BytesIO(cert)).pages]
    return tuple((render(cert, n).reduce(8), t, n) for n, t in enumerate(textos, 1))


def lineas_de(texto: str, tamano: tuple[int, int]) -> tuple:
    """Las líneas de un texto repartidas por la imagen, de arriba abajo, como las
    devolvería un OCR: una por renglón, en píxeles, con el origen arriba a la izquierda."""
    from core.certificado_aportable import Linea

    ancho, alto = tamano
    renglones = [" ".join(l.split()) for l in texto.splitlines() if l.split()]
    paso = max(1, (alto - 4) // max(1, len(renglones)))
    return tuple(Linea(r, 2, 2 + i * paso, ancho - 2, 2 + i * paso + max(1, paso - 1))
                 for i, r in enumerate(renglones))


def ocr_fiel(*certificados: bytes, lee_rotulo: bool = True, extra: dict | None = None,
             estricto: bool = True):
    """Un OCR de mentira que LEE LA IMAGEN, y no los índices del código que se prueba.

    El puerto recibe la imagen de UNA página y devuelve sus líneas. Este doble la casa,
    por sus píxeles, con la página de los certificados que dibuja, y devuelve las líneas
    de ESA página. Así un error de índices en el recorte se ve en el texto, como con un
    OCR de verdad; un doble que devolviera el texto de lo que el código CREE haber
    conservado aprobaría justo ese error. `lee_rotulo=False` lo lee todo menos el rótulo
    —el OCR que falla ahí— y `extra={n: texto}` añade `texto` a lo que lee en la imagen
    de la página n (base 1) del certificado: así se fabrica lo que un OCR de verdad leería
    en un ESCANEO, cuyo texto no está en el PDF (R3, §2).

    Se casa sobre miniaturas (1/8): el ruido del JPEG se promedia y lo que distingue una
    página de otra —dónde hay texto— se queda. Si la mejor no gana con holgura, revienta:
    un doble que adivina es peor que ninguno. Dos candidatas cuyo texto normalizado es el
    mismo —la misma página de la reproducción en dos certificados de una expedición, que
    solo cambian en la cabecera— no son ambigüedad. `estricto=False` se queda con la más
    cercana sin exigir holgura: es el de la orquestación, donde el acta del correo y la del
    burofax solo cambian en su código y lo que se prueba es CUÁNDO se pasa el OCR.
    """
    from PIL import Image

    from core.certificado_aportable import PPP, normalizar_pagina

    candidatas = [c for cert in certificados for c in _candidatas(cert, PPP)]

    def ocr(jpeg: bytes) -> tuple:
        imagen = Image.open(io.BytesIO(jpeg)).convert("RGB")
        mini = imagen.reduce(8)
        orden = sorted(((distancia(mini, c), t, n) for c, t, n in candidatas
                        if c.size == mini.size), key=lambda x: x[0])
        if not orden or orden[0][0] > 1.0 or estricto and any(
                d < 2 * orden[0][0] + 0.5
                and normalizar_pagina(t) != normalizar_pagina(orden[0][1])
                for d, t, _ in orden[1:]):
            raise AssertionError(f"el OCR de mentira no sabe qué página es: "
                                 f"{[round(d, 2) for d, _, _ in orden[:3]]}")
        _, texto, n = orden[0]
        if not lee_rotulo:
            texto = _RE_ROTULO_OCR.sub("C0NF1DENC1AL - C0ND1C10NES", texto)
        if extra and n in extra:
            texto += "\n" + extra[n]
        return lineas_de(texto, imagen.size)

    return ocr


def certificado_con_escaneo(texto_escaneado: str) -> tuple[bytes, list]:
    """Un certificado con una página ESCANEADA —su imagen lleva `texto_escaneado` y el PDF no
    lleva texto—, portado de la sonda del revisor en la R3 (§2): acta, escaneo y las
    condiciones, que se retiran. Devuelve el certificado y las condiciones con que se recorta.

    La relectura por TEXTO no ve lo que el escaneo muestra, porque el PDF no lo lleva; solo
    lo ve un OCR sobre sus píxeles.
    """
    import pypdfium2 as pdfium
    from pypdf import PdfWriter
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    from core.certificado_aportable import PaginaCondiciones

    doc = pdfium.PdfDocument(pdf([texto_escaneado]))
    imagen = doc[0].render(scale=2).to_pil().convert("RGB")
    doc.close()
    escaneo = io.BytesIO()
    lienzo = canvas.Canvas(escaneo, pagesize=(595.2756, 841.8898), invariant=1)
    lienzo.drawImage(ImageReader(imagen), 0, 0, width=595.2756, height=841.8898)
    lienzo.showPage()
    lienzo.save()
    escritor = PdfWriter()
    for parte in (pdf([MARCA_ACTA + "\nActa de la prueba del escaneo."]), escaneo.getvalue(),
                  pdf([CONDICIONES])):
        escritor.append(io.BytesIO(parte))
    salida = io.BytesIO()
    escritor.write(salida)
    return salida.getvalue(), [PaginaCondiciones("CONDICIONES.pdf", 1, CONDICIONES)]


def ocr_que_lee(texto: str):
    """Un OCR que lee SIEMPRE `texto`, sea cual sea la imagen: el que se equivoca de página."""
    from PIL import Image

    def ocr(jpeg: bytes) -> tuple:
        return lineas_de(texto, Image.open(io.BytesIO(jpeg)).size)

    return ocr


def carga(pdf: bytes) -> bytes:
    """Los datos DECODIFICADOS de todos los streams del fichero, cuelguen o no de algo."""
    from pypdf import PdfReader
    from pypdf.generic import StreamObject

    lector, trozos = PdfReader(io.BytesIO(pdf)), []
    for num in range(1, int(lector.trailer["/Size"])):
        try:
            objeto = lector.get_object(num)
        except Exception:  # noqa: BLE001 — entradas libres del xref
            continue
        if isinstance(objeto, StreamObject):
            try:
                trozos.append(objeto.get_data())
            except Exception:  # noqa: BLE001 — un filtro que pypdf no decodifica
                trozos.append(bytes(getattr(objeto, "_data", b"")))
    return b"\n".join(trozos)


def alcanzable_desde(pdf: bytes, pagina: int) -> bytes:
    """Los streams que se alcanzan desde la página (base 1) sin subir a `/Parent`, decodificados.

    Es el control de las sondas: prueba que las condiciones están AL ALCANCE de la página
    que se conserva, que es lo que las metía en el aportable estructural.
    """
    from pypdf import PdfReader
    from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject, StreamObject

    lector = PdfReader(io.BytesIO(pdf))
    vistos, trozos = set(), []

    def recorrer(valor) -> None:
        if isinstance(valor, IndirectObject):
            if valor.idnum in vistos:
                return
            vistos.add(valor.idnum)
            valor = valor.get_object()
        if isinstance(valor, StreamObject):
            trozos.append(valor.get_data())
        if isinstance(valor, DictionaryObject):
            for clave, v in valor.items():
                if clave != "/Parent":
                    recorrer(v)
        elif isinstance(valor, ArrayObject):
            for v in valor:
                recorrer(v)

    recorrer(lector.pages[pagina - 1].indirect_reference)
    return b"\n".join(trozos)


#: Las vías de la R2/H-01: por dónde viajaban las condiciones en el aportable estructural.
VIAS_DE_FUGA = ("pattern", "shading", "font", "smask", "image_smask", "metadata",
                "contents_array")


def con_fuga(via: str) -> bytes:
    """El certificado de las sondas de la R2 (H-01): las condiciones dentro de un recurso
    que la página conservada (la 3) COMPARTE con la retirada (la 5) sin dibujarlo.

    Portadas de las sondas del revisor (acta R2, §2). Con el aportable estructural los
    siete aportables llevaban dentro el contenido de las condiciones, sin rótulo en sus
    páginas ni aviso: la poda solo miraba `Do`. Con la imagen, lo que no se dibuja no está.
    """
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import ArrayObject as A
    from pypdf.generic import DecodedStreamObject
    from pypdf.generic import DictionaryObject as D
    from pypdf.generic import NameObject as N
    from pypdf.generic import NumberObject as I

    w = PdfWriter(clone_from=PdfReader(io.BytesIO(certificado([refundido(), factura()]))))

    def flujo(datos: bytes, **claves):
        st = DecodedStreamObject()
        st.set_data(datos)
        for k, v in claves.items():
            st[N("/" + k)] = v
        return w._add_object(st)

    conservada, retirada = w.pages[2], w.pages[4]
    original = retirada.get_contents().get_data()
    caja = A([I(0), I(0), I(595), I(842)])
    recursos = D(dict(conservada["/Resources"].get_object()))
    op = b""
    if via == "pattern":
        patron = flujo(original, Type=N("/Pattern"), PatternType=I(1), PaintType=I(1),
                       TilingType=I(1), BBox=caja, XStep=I(595), YStep=I(842),
                       Resources=retirada["/Resources"])
        recursos[N("/Pattern")] = D({N("/Secret"): patron})
        op = b"q /Pattern cs /Secret scn 0 0 595 842 re f Q"
    elif via == "shading":
        # Función PostScript válida: lo económico viaja en sus comentarios.
        datos = (b"{\n" + b"\n".join(b"% " + l for l in original.splitlines())
                 + b"\npop pop 0 0 0 }")
        funcion = flujo(datos, FunctionType=I(4), Domain=A([I(0), I(1), I(0), I(1)]),
                        Range=A([I(0), I(1)] * 3))
        recursos[N("/Shading")] = D({N("/Secret"): D({
            N("/ShadingType"): I(1), N("/ColorSpace"): N("/DeviceRGB"),
            N("/Function"): funcion})})
        op = b"q /Secret sh Q"
    elif via == "font":
        glifo = flujo(b"600 0 d0\n" + original)
        fuente = D({N("/Type"): N("/Font"), N("/Subtype"): N("/Type3"),
                    N("/FontBBox"): caja, N("/FontMatrix"): A([I(1), I(0), I(0), I(1), I(0), I(0)]),
                    N("/CharProcs"): D({N("/A"): glifo}), N("/Resources"): retirada["/Resources"],
                    N("/Encoding"): D({N("/Type"): N("/Encoding"),
                                       N("/Differences"): A([I(65), N("/A")])}),
                    N("/FirstChar"): I(65), N("/LastChar"): I(65), N("/Widths"): A([I(600)])})
        recursos[N("/Font")] = D(dict(recursos["/Font"].get_object()))
        recursos["/Font"][N("/Secret")] = w._add_object(fuente)
        op = b"BT /Secret 1 Tf (A) Tj ET"
    elif via == "smask":
        forma = flujo(original, Type=N("/XObject"), Subtype=N("/Form"), BBox=caja,
                      Resources=retirada["/Resources"])
        forma.get_object()[N("/Group")] = D({N("/S"): N("/Transparency"),
                                             N("/CS"): N("/DeviceGray")})
        recursos[N("/ExtGState")] = D({N("/Secret"): D({
            N("/Type"): N("/ExtGState"),
            N("/SMask"): D({N("/S"): N("/Luminosity"), N("/G"): forma})})})
        op = b"q /Secret gs 0 0 100 100 re f Q"
    elif via == "image_smask":
        # La máscara lleva los bytes de las condiciones como muestras de imagen; la imagen
        # exterior, inocua, la dibujan las dos páginas.
        mascara = flujo(original, Type=N("/XObject"), Subtype=N("/Image"),
                        Width=I(len(original)), Height=I(1), ColorSpace=N("/DeviceGray"),
                        BitsPerComponent=I(8))
        imagen = flujo(b"\xff" * len(original), Type=N("/XObject"), Subtype=N("/Image"),
                       Width=I(len(original)), Height=I(1), ColorSpace=N("/DeviceGray"),
                       BitsPerComponent=I(8), SMask=mascara)
        recursos[N("/XObject")] = D({N("/Secret"): imagen})
        op = b"q /Secret Do Q"
        conservada[N("/Contents")] = flujo(conservada.get_contents().get_data() + b"\n" + op)
    elif via == "metadata":
        # Metadatos en un formulario que la CONSERVADA sí dibuja: al catálogo y a la página
        # no llegan, a sus formularios sí.
        meta = flujo(('<x:xmpmeta xmlns:x="adobe:ns:meta/">' + CONDICIONES
                      + "</x:xmpmeta>").encode(), Type=N("/Metadata"), Subtype=N("/XML"))
        propia = flujo(conservada.get_contents().get_data(), Type=N("/XObject"),
                       Subtype=N("/Form"), BBox=caja, Resources=conservada["/Resources"],
                       Metadata=meta)
        recursos[N("/XObject")] = D({N("/Keep"): propia})
        conservada[N("/Contents")] = flujo(b"q /Keep Do Q")
        retirada[N("/Metadata")] = meta
    elif via == "contents_array":
        # El contenido retirado en un array INDIRECTO, y el stream al alcance de la
        # conservada desde un recurso que no invoca.
        secreto = retirada.raw_get("/Contents")
        retirada[N("/Contents")] = w._add_object(A([secreto]))
        recursos[N("/Pattern")] = D({N("/Stored"): secreto})
    else:
        raise ValueError(via)
    conservada[N("/Resources")] = recursos
    retirada[N("/Resources")] = recursos
    if op:
        retirada[N("/Contents")] = flujo(original + b"\n" + op)
    buffer = io.BytesIO()
    w.write(buffer)
    return buffer.getvalue()
