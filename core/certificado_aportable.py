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

import io
import re
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
