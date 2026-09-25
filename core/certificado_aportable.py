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

import hashlib
import io
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

from core.certificado_lectura import _sin_ligaduras as sin_ligaduras

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
