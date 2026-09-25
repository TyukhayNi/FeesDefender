"""El certificado que va al juzgado: el íntegro sin las páginas de condiciones.

F3 del envío certificado (spec §7.3, §7.4 y §9). De cada envío quedan tres artefactos,
los tres archivados: el **íntegro**, con su firma —lo archiva F2—; el **aportable**, un
documento DERIVADO, con otro nombre y sin firma; y su **manifiesto**, que dice qué se
retiró, de dónde y con qué huellas.

Este módulo es puro: recibe bytes y devuelve bytes y datos. No sabe qué es un
expediente ni toca la red o el disco; de dónde salen el certificado y los documentos
enviados, y dónde se escribe, lo decide `core/expedicion_certificada.py`.

Lo gobiernan mediciones del 2026-09-25 sobre tres certificados reales y los adjuntos
de dos de ellos (plan `docs/superpowers/plans/2026-09-25-codicert-f3.md`, M-1 a M-10).
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
from collections.abc import Sequence
from dataclasses import dataclass

from core.certificado_lectura import _sin_ligaduras as sin_ligaduras
from core.certificado_lectura import paginas_de_acta_de_textos

_RE_ENTRADA = re.compile(r"^(?P<nombre>.+?)\s+(?P<huella>[0-9a-f]{6,64})$")
_RE_HEX = re.compile(r"^[0-9a-f]+$")
_FIN_FICHEROS = "la autenticidad de este documento"


class AportableError(RuntimeError):
    """No se puede producir un aportable seguro. Nunca se produce uno a medias."""


@dataclass(frozen=True)
class FicheroListado:
    """Un adjunto tal como lo lista el acta: nombre y huella (spec §7, M-5)."""

    nombre: str
    sha256: str


def _textos_pdf(datos: bytes, *, que: str) -> list[str]:
    """El texto de cada página. Un PDF ilegible es `AportableError`, no lo que lance pypdf."""
    from pypdf import PdfReader

    try:
        return [p.extract_text() or "" for p in PdfReader(io.BytesIO(datos)).pages]
    except Exception as exc:  # noqa: BLE001 — pypdf lanza de todo ante un PDF roto
        raise AportableError(
            f"{que}: no se puede leer como PDF ({type(exc).__name__}: {exc})") from exc


def ficheros_listados_de_textos(textos: Sequence[str]) -> tuple[FicheroListado, ...]:
    """El bloque FICHEROS ADJUNTOS del acta, con cada huella reconstruida (M-5).

    La huella viene PARTIDA en dos líneas —46 caracteres en la del nombre y 18 en la
    siguiente— y ya costó un falso negativo en el W-04A6LI: se concatenan hasta 64.
    Una línea que no es ni entrada ni continuación **para** en vez de saltarse: un
    nombre partido en dos líneas, o un formato que nadie ha medido, no se adivina.
    """
    for texto in textos:
        plano = sin_ligaduras(texto or "")
        if "FICHEROS ADJUNTOS" not in plano:
            continue
        _, _, cola = plano.partition("Huella digital")
        lineas = [l.strip() for l in cola.splitlines()[1:] if l.strip()]
        salida: list[FicheroListado] = []
        n = 0
        while n < len(lineas):
            if lineas[n].lower().startswith(_FIN_FICHEROS):
                break
            entrada = _RE_ENTRADA.match(lineas[n])
            if entrada is None:
                raise AportableError(
                    "el bloque FICHEROS ADJUNTOS trae una línea que no es ni un fichero "
                    f"ni la continuación de una huella: {lineas[n][:60]!r}. No se adivina.")
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
        if not salida:
            raise AportableError("el bloque FICHEROS ADJUNTOS del acta está vacío.")
        return tuple(salida)
    raise AportableError(
        "el certificado no trae el bloque FICHEROS ADJUNTOS: sin él no se puede "
        "comprobar qué documentos salieron.")


def ficheros_listados(pdf: bytes) -> tuple[FicheroListado, ...]:
    """`ficheros_listados_de_textos` sobre el PDF del certificado."""
    return ficheros_listados_de_textos(_textos_pdf(pdf, que="el certificado"))


# --- qué páginas son de condiciones ---------------------------------------------

#: El rótulo con que la plantilla abre la página de condiciones (spec §7.3). Se busca
#: como LÍNEA ENTERA (M-7): la palabra «condiciones» sale también en el requerimiento
#: («las condiciones adjuntas») y en la factura («Condiciones de pago a la vista»).
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


_ROTULO = " ".join(_plano(LITERAL_CONDICIONES).split())


def lleva_rotulo(texto: str) -> bool:
    """¿Alguna LÍNEA de la página es, entera, el rótulo de las condiciones? (M-7)"""
    return any(" ".join(_plano(linea).split()) == _ROTULO
               for linea in sin_ligaduras(texto or "").splitlines())


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

    La regla: desde la primera página que lleva el rótulo como línea entera **hasta el
    final de ese documento**. En el refundido medido las condiciones son el último
    bloque, y en el documento partido que pide el §7 (`ANEXO II.pdf`) son el documento
    entero: la misma regla vale para los dos.

    **Si el rótulo cae antes del final, se retira de más, nunca de menos.** Una página
    que no es de condiciones y queda dentro sale del aportable —se pierde prueba, que el
    íntegro conserva—; ninguna de condiciones puede quedar fuera de lo que se retira.
    El recorte avisa de esas páginas arrastradas.
    """
    salida: list[PaginaCondiciones] = []
    for doc in documentos:
        textos = _textos_pdf(doc.contenido, que=doc.nombre)
        inicio = next((n for n, t in enumerate(textos) if lleva_rotulo(t)), None)
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
    """El aportable ya producido y verificado, con lo que hace falta para el manifiesto."""

    pdf: bytes
    paginas_totales: int
    paginas_acta: tuple[int, ...]
    paginas_reproduccion: tuple[int, ...]
    retiradas: tuple[PaginaRetirada, ...]
    conservadas: tuple[int, ...]
    avisos: tuple[str, ...] = ()

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.pdf).hexdigest()


def _ratio(a: str, b: str) -> float:
    """Similitud 0..1 entre dos textos normalizados.

    `quick_ratio` es cota SUPERIOR y es barata: si no llega al umbral, el `ratio` de
    verdad tampoco. Un burofax admite 200 páginas (spec §1.4); sin el prefiltro serían
    200 comparaciones completas por cada página de condiciones.
    """
    m = difflib.SequenceMatcher(None, a, b, autojunk=False)
    cota = m.quick_ratio()
    return cota if cota < UMBRAL_COPIA else m.ratio()


def _mas_parecida(objetivo: str, candidatas: dict[int, str]) -> tuple[int | None, float]:
    """La página más parecida y su similitud EXACTA, para decir por qué no casó."""
    mejor, valor = None, 0.0
    for pagina, texto in candidatas.items():
        r = difflib.SequenceMatcher(None, objetivo, texto, autojunk=False).ratio()
        if r > valor:
            mejor, valor = pagina, r
    return mejor, valor


def _es_widget_de_firma(anotacion) -> bool:
    """¿Es el widget del campo de firma? Fusionado con el campo o colgando de él (M-8)."""
    if anotacion.get("/Subtype") != "/Widget":
        return False
    tipo = anotacion.get("/FT")
    if tipo is None and anotacion.get("/Parent") is not None:
        tipo = anotacion["/Parent"].get_object().get("/FT")
    return tipo == "/Sig"


def _sin_firma(pagina) -> None:
    """Quita de la página el widget de la firma, que el aportable ya no tiene (M-8).

    Recortar rompe la firma (spec §7.2) y el `/AcroForm` no viaja; el widget sí, y
    seguiría pintando un sello de firma sin firma detrás. Presentar como firmado un
    documento que no lo está es justo lo que el nombre `APORTABLE` y el manifiesto
    existen para no hacer.
    """
    from pypdf.generic import ArrayObject, NameObject

    anotaciones = pagina.get("/Annots")
    if anotaciones is None:
        return
    quedan = ArrayObject(a for a in anotaciones.get_object()
                         if not _es_widget_de_firma(a.get_object()))
    if quedan:
        pagina[NameObject("/Annots")] = quedan
    else:
        del pagina["/Annots"]


def _sin_paginas(lector, conservadas: Sequence[int]) -> bytes:
    """Un PDF nuevo con las páginas conservadas, en su orden y sin el widget de firma."""
    from pypdf import PdfWriter

    escritor = PdfWriter()
    for numero in conservadas:
        pagina = lector.pages[numero - 1]
        _sin_firma(pagina)
        escritor.add_page(pagina)
    buffer = io.BytesIO()
    escritor.write(buffer)
    return buffer.getvalue()


def _verificar(pdf: bytes, *, esperadas: Sequence[str],
               condiciones: Sequence[PaginaCondiciones]) -> None:
    """Se relee lo producido: exactamente las páginas conservadas, sin rastro de condiciones.

    Es la tercera parada y no depende de las otras dos: comprueba el RESULTADO, no la
    aritmética que lo produjo. Las tres numeraciones del §7.3 son exactamente donde se
    cuela un error de uno.
    """
    hechas = _textos_pdf(pdf, que="el aportable producido")
    if len(hechas) != len(esperadas):
        raise AportableError(
            f"el aportable producido tiene {len(hechas)} páginas y debían ser "
            f"{len(esperadas)}. No se entrega.")
    objetivos = [normalizar_pagina(c.texto) for c in condiciones]
    for n, (hecha, esperada) in enumerate(zip(hechas, esperadas), 1):
        normal = normalizar_pagina(hecha)
        if normal != normalizar_pagina(esperada):
            raise AportableError(
                f"la página {n} del aportable no es la que tocaba conservar: la cuenta de "
                "páginas falló. No se entrega.")
        if lleva_rotulo(hecha) or any(_ratio(o, normal) >= UMBRAL_COPIA
                                      for o in objetivos):
            raise AportableError(
                f"la página {n} del aportable reproduce las condiciones. No se entrega.")


#: Palabras por frase al buscar las condiciones en lo que se conserva (M-6). Con 8,
#: cero coincidencias en los tres certificados reales, acta incluida; con 5 o 6 saltan
#: el IBAN de la factura y «de la Oferta Vinculante Confidencial».
PALABRAS_AVISO = 8

_RE_PALABRA = re.compile(r"[a-z0-9]+(?:[.,%][a-z0-9]+)*%?")
_DESPEDIDA = ("sin", "otro", "particular")


def _palabras(texto: str) -> list[str]:
    sin_cabecera = _CABECERA_REPRODUCCION.sub("", sin_ligaduras(texto or ""))
    return _RE_PALABRA.findall(_plano(sin_cabecera))


def _cuerpo(condiciones: Sequence[PaginaCondiciones]) -> list[str]:
    """Las palabras propias de las condiciones: tras el rótulo y antes de la despedida.

    Lo de antes del rótulo es membrete, requerido y referencia, y lo de después de «Sin
    otro particular», la despedida y la firma: las dos cosas las comparte con el
    requerimiento, y sin cortarlas el aviso saltaría en todo envío (M-6).
    """
    palabras: list[str] = []
    for c in condiciones:
        lineas = sin_ligaduras(c.texto).splitlines()
        inicio = next((n + 1 for n, l in enumerate(lineas)
                       if " ".join(_plano(l).split()) == _ROTULO), 0)
        palabras += _palabras("\n".join(lineas[inicio:]))
    for n in range(len(palabras) - len(_DESPEDIDA) + 1):
        if tuple(palabras[n:n + len(_DESPEDIDA)]) == _DESPEDIDA:
            return palabras[:n]
    return palabras


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
    frases = _frases(_cuerpo(condiciones))
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


def recortar(certificado: bytes,
             condiciones: Sequence[PaginaCondiciones]) -> Recorte:
    """El aportable: el certificado sin las páginas que reproducen las condiciones.

    Tres paradas, las tres antes de entregar nada (spec §7.3, reenunciado con M-3):

    1. **Una página de condiciones que no se localiza en la reproducción para.** Lo que
       no se sabe dónde está no se puede garantizar que haya salido.
    2. **Una página que se conserva y lleva el rótulo para**, sea de la reproducción o
       del acta. Es la red de la primera por un instrumento independiente: el texto
       casado puede fallar de formas que el rótulo no, y al revés.
    3. **El resultado se relee** (`_verificar`).

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
    from pypdf import PdfReader

    try:
        lector = PdfReader(io.BytesIO(certificado))
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
    normal = {n: normalizar_pagina(textos[n - 1]) for n in reproduccion}

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
        if lleva_rotulo(textos[n - 1]):
            donde = ("es del ACTA, que no se recorta: el asunto o el cuerpo de la "
                     "comunicación lo reproducen" if n in acta else
                     "y no casa con ninguna página de condiciones de lo que salió")
            raise AportableError(
                f"la página {n} del certificado se conserva y lleva el rótulo "
                f"«{LITERAL_CONDICIONES}» —{donde}—. No se produce aportable.")

    pdf = _sin_paginas(lector, conservadas)
    _verificar(pdf, esperadas=[textos[n - 1] for n in conservadas],
               condiciones=condiciones)
    avisos = (_avisos_de_fuga({n: textos[n - 1] for n in conservadas}, condiciones)
              + _avisos_de_arrastre(condiciones))
    return Recorte(pdf=pdf, paginas_totales=total, paginas_acta=tuple(acta),
                   paginas_reproduccion=reproduccion,
                   retiradas=tuple(retiradas[n] for n in sorted(retiradas)),
                   conservadas=conservadas, avisos=tuple(avisos))


# --- el manifiesto --------------------------------------------------------------

AVISO_FIRMA = (
    "El aportable es un documento DERIVADO y no conserva la firma electrónica del "
    "prestador: recortar páginas la rompe (spec §7.2), y con ella la presunción del art. "
    "326.4 LEC. La prueba custodiada es el certificado íntegro, con la huella que figura "
    "en este manifiesto.")


def manifiesto_de(recorte: Recorte, *, id_envio: str, canal: str, id_personalizado: str,
                  generado: str, integro_nombre: str, integro_sha256: str,
                  aportable_nombre: str, emisor: dict,
                  ficheros_acta: Sequence[FicheroListado],
                  documentos: Sequence[DocumentoEnviado],
                  avisos_extra: Sequence[str] = ()) -> dict:
    """El manifiesto del aportable (spec §7.4): qué se retiró, de dónde y con qué huellas.

    Las huellas van **tal como las lista el acta** (`acta.ficheros_listados`) y, aparte,
    las de los documentos con que se localizaron las condiciones: en un burofax el acta
    lista UN fichero fundido (M-4) y los documentos son los del correo. Las páginas
    retiradas van en las tres numeraciones del §7.3.
    """
    return {
        "version": 1,
        "id_envio": id_envio,
        "canal": canal,
        "id_personalizado": id_personalizado,
        "generado": generado,
        "integro": {"fichero": integro_nombre, "sha256": integro_sha256,
                    "paginas": recorte.paginas_totales},
        "aportable": {"fichero": aportable_nombre, "sha256": recorte.sha256,
                      "paginas": len(recorte.conservadas)},
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
        "avisos": [*recorte.avisos, *avisos_extra],
    }
