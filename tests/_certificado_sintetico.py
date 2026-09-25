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


def con_firma(datos: bytes, *, con_padre: bool = False) -> bytes:
    """Le pone al PDF un campo de firma con su widget en la página 1, como los reales (M-8).

    `con_padre=True` separa el campo del widget (el widget lleva `/Parent` y el `/FT`
    está en el campo): los reales los fusionan, pero el recorte no puede depender de eso.
    """
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import (ArrayObject, DictionaryObject, FloatObject, NameObject,
                               NumberObject, TextStringObject)

    escritor = PdfWriter(clone_from=PdfReader(io.BytesIO(datos)))
    widget = DictionaryObject({
        NameObject("/Type"): NameObject("/Annot"),
        NameObject("/Subtype"): NameObject("/Widget"),
        NameObject("/Rect"): ArrayObject([FloatObject(380), FloatObject(30),
                                          FloatObject(560), FloatObject(110)]),
        NameObject("/F"): NumberObject(4),
    })
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
