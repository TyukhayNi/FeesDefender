"""Detector de contaminación cruzada: material de OTROS expedientes en el intake.

Capa PURA (no toca disco, no muta nada): recibe los mensajes ya atomizados y el
W-code del caso, y devuelve los avistamientos de W-codes ajenos en asuntos y
nombres de adjunto. AVISA, nunca excluye: en un expediente probatorio, descartar
en silencio es peor que arrastrar ruido — la decisión de borrar es del letrado.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# W-code suelto (sin paréntesis, a diferencia de `abrir_caso._W_CODE_EN_NOMBRE`): así
# se caza tanto en "W-028QTL_demanda.pdf" como en un asunto. El lookbehind evita
# falsos positivos con una `w` pegada a texto ("New-02...").
#
# `{4,}` es DELIBERADAMENTE permisivo: todos los W-codes observados llevan 6
# alfanuméricos, y ceñirse a `{6}` daría menos falsos positivos — pero aquí el falso
# NEGATIVO es el caro (contaminación que pasa inadvertida, que es justo lo que este
# detector existe para cazar), mientras el falso positivo solo cuesta ojear una línea.
_RE_W_CODE = re.compile(r"(?<![A-Za-z0-9])W-([A-Z0-9]{4,})", re.IGNORECASE)


# El W-code del PROPIO caso sí va anclado en "(W-...)", como en el case_id canónico.
# Duplicado a propósito de `abrir_caso._W_CODE_EN_NOMBRE` (una línea) para no invertir
# la dependencia: el motor de atomización no debe importar el orquestador de alta.
_RE_W_CODE_PROPIO = re.compile(r"\((W-[A-Z0-9]+)\)")


def w_code_de_carpeta(nombre: str) -> str:
    """El W-code de un nombre de carpeta de caso, o "" si no lo lleva.

    Devuelve "" para `(SIN REFERENCIA)` (categoría OTROS) y para cualquier layout no
    canónico — y `detectar_cruce` con "" calla, que es lo correcto: sin referencia
    propia no se puede decidir qué es ajeno.
    """
    m = _RE_W_CODE_PROPIO.search(nombre or "")
    return m.group(1) if m else ""


def _w_codes_en(texto: str) -> list[str]:
    """W-codes normalizados a mayúsculas, en orden de aparición y sin repetir."""
    vistos: dict[str, None] = {}
    for m in _RE_W_CODE.finditer(texto or ""):
        vistos.setdefault(f"W-{m.group(1).upper()}", None)
    return list(vistos)


@dataclass(frozen=True)
class Hallazgo:
    """Un W-code ajeno avistado en un mensaje."""

    w_code: str = ""
    msg_id: str = ""
    donde: str = ""       # "asunto" | "adjunto"
    detalle: str = ""     # el texto donde se avistó (nombre de fichero o asunto)


#: Prefijo de la nota de contaminación. Público a propósito: `hay_contaminacion` lo
#: reconoce por él, y dos copias del mismo texto derivan.
PREFIJO_NOTA = "posible contaminación cruzada: "

_MAX_MSGS_EN_NOTA = 5


def resumir(hallazgos: list[Hallazgo]) -> list[str]:
    """Una nota por W-code ajeno, contando MENSAJES contaminados (no avistamientos):
    lo que el letrado necesita saber es cuántos correos tiene que mirar.

    Orden determinista (primera aparición), para que dos corridas den la misma nota.
    """
    por_code: dict[str, dict[str, None]] = {}
    for h in hallazgos:
        por_code.setdefault(h.w_code, {}).setdefault(h.msg_id, None)
    notas: list[str] = []
    for w_code, msgs in por_code.items():
        ids = list(msgs)
        muestra = ", ".join(ids[:_MAX_MSGS_EN_NOTA])
        resto = len(ids) - _MAX_MSGS_EN_NOTA
        if resto > 0:
            muestra += f" +{resto} más"
        plural = "mensaje" if len(ids) == 1 else "mensajes"
        notas.append(
            f"{PREFIJO_NOTA}{w_code} en {len(ids)} {plural} ({muestra})")
    return notas


def hay_contaminacion(notas) -> bool:
    """¿Alguna de estas notas denuncia contaminación cruzada?

    **Vive aquí, junto a quien escribe la nota.** `report.notas` es una bolsa mixta —hay
    vistas rotas, historiales no escritos, poda omitida— y el consumidor que quisiera
    distinguir la contaminación tendría que replicar el prefijo. Si el texto cambia, lo
    que se rompe es este predicado y su test, no cada llamador.

    Lo pidió la R-C del Plan 5 (HC-04): el status de la atomización solo miraba
    `publicado` y `errores`, así que una contaminación detectada devolvía `ok`, el OCR
    seguía y la apertura declaraba la etapa hecha sin pendiente alguno.
    """
    return any(str(n).startswith(PREFIJO_NOTA) for n in (notas or ()))


def detectar_cruce(mensajes, *, w_code_propio: str) -> list[Hallazgo]:
    """W-codes de otros expedientes avistados en el asunto o en los nombres de adjunto.

    NO mira el cuerpo a propósito: el letrado referencia otros casos en su propia
    correspondencia con normalidad, así que el cuerpo daría ruido en vez de señal.
    Un asunto o un nombre de fichero que traiga otra referencia es, en cambio, indicio
    fuerte de que ese documento no pertenece a este expediente.
    """
    propio = (w_code_propio or "").strip().upper()
    if not propio:
        return []              # sin referencia propia no hay "ajeno" que medir
    hallazgos: list[Hallazgo] = []
    for m in mensajes:
        sitios = [("asunto", m.asunto)] + [("adjunto", a.nombre) for a in m.adjuntos]
        for donde, texto in sitios:
            for w in _w_codes_en(texto):
                if w != propio:
                    hallazgos.append(Hallazgo(
                        w_code=w, msg_id=m.msg_id, donde=donde, detalle=texto))
    return hallazgos
