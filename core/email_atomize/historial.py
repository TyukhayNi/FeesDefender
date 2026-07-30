"""Historial citado no atribuible, localizable (`MEJORAS #105`, pieza 1 de `#109`).

Modulo PURO: no toca disco. Lo cablea `pipeline.atomize_dir`.

La regla que gobierna este modulo: NADA de lo que produce atribuye texto a un remitente. El
historial va verbatim y las anotaciones dicen solo «esta frase ya esta en la ficha X» o «esta
frase no esta en ningun otro sitio». Ahi esta la diferencia con la Capa B, que si atribuye y
por eso exige una cabecera parseable.

Spec: `docs/superpowers/specs/2026-07-30-historial-citado-localizable-design.md`.
"""
from __future__ import annotations

import re

from .inline import normaliza_cuerpo

# "Frase sustancial": la unidad sobre la que `MEJORAS #105` midio que el 90 % del texto
# recortado ya existia en otra ficha. No cambiar sin re-medir.
_MIN_PALABRAS = 8

# Marca de cita al PRINCIPIO de linea. Se quita ANTES de aplanar: si se aplanase primero, los
# `>` quedarian a mitad de cadena, `normaliza_cuerpo` (que tambien las quita solo al principio
# de linea) no las limpiaria, y ninguna frase del historial casaria con su gemela de una ficha
# -> el fichero saldria con «100 % exclusivas» siempre.
_RE_MARCA_CITA = re.compile(r"(?m)^\s*>+\s?")

# Fin de frase: puntuacion terminal seguida de espacio, o linea en blanco.
_RE_FIN_FRASE = re.compile(r"(?<=[.!?…])\s+|\n{2,}")

_CABECERA = (
    "<!-- GENERADO por core.email_atomize — NO editar a mano. -->\n"
    "# Historial citado de {portador} — SIN ATRIBUIR\n\n"
    "Historial que `cortar_autor` retiro del cuerpo de `{ficha}`, VERBATIM.\n"
    "**Nada de lo que hay aqui esta atribuido a un remitente.** El texto puede incluir bloques\n"
    "`De:`/`Enviado:` porque van dentro de la cita y se reproducen tal cual: son parte del texto\n"
    "citado, **no** una atribucion del motor. Si un mensaje de aqui tuviera cabecera atribuible,\n"
    "tendria su propia ficha; no la tiene.\n\n"
    "- frases sustanciales (>=8 palabras): {n_frases}\n"
    "- ya presentes en otra ficha: {n_dup}\n"
    "- **exclusivas de este fichero: {n_exc}**\n"
)


def frases_sustanciales(texto: str) -> list[str]:
    """Las frases de *texto* con >= 8 palabras, en orden y ya aplanadas a una linea.

    Devuelve el texto legible (sin marcas de cita, sin saltos), NO normalizado: estas frases se
    imprimen en el indice del `.historial.md`. La normalizacion es solo para comparar.
    """
    limpio = _RE_MARCA_CITA.sub("", texto or "")
    frases = []
    for bruto in _RE_FIN_FRASE.split(limpio):
        f = " ".join(bruto.split())
        if len(f.split()) >= _MIN_PALABRAS:
            frases.append(f)
    return frases


def indice_frases(mensajes: list) -> dict[str, list[str]]:
    """De frase NORMALIZADA al `MSG-id` de las fichas cuyo cuerpo la contiene.

    Se construye desde el cuerpo de todas las fichas publicadas (Capa A y B). Normaliza con
    `normaliza_cuerpo`, el mismo normalizador unico que gobierna los fingerprints.
    """
    idx: dict[str, list[str]] = {}
    for m in mensajes:
        for f in frases_sustanciales(m.cuerpo):
            k = normaliza_cuerpo(f)
            if not k:
                continue
            ids = idx.setdefault(k, [])
            if m.msg_id not in ids:
                ids.append(m.msg_id)
    return idx


def render_historial(*, portador_msg_id: str, nombre_ficha: str, resto_citado: str,
                     indice: dict[str, list[str]]) -> str:
    """El contenido del `<atom>.historial.md`: cabecera con recuentos, indice de frases y el
    texto retirado VERBATIM.

    El indice se excluye a si mismo: una frase presente solo en la ficha del propio portador NO
    cuenta como «ya presente en otra ficha».
    """
    frases = frases_sustanciales(resto_citado)
    filas, n_dup = [], 0
    for i, f in enumerate(frases, 1):
        otros = [x for x in indice.get(normaliza_cuerpo(f), []) if x != portador_msg_id]
        if otros:
            n_dup += 1
            filas.append(f"| {i} | duplicada | {', '.join(otros)} | {_celda(f)} |")
        else:
            filas.append(f"| {i} | **EXCLUSIVA** | — | {_celda(f)} |")
    partes = [_CABECERA.format(portador=portador_msg_id, ficha=nombre_ficha,
                               n_frases=len(frases), n_dup=n_dup,
                               n_exc=len(frases) - n_dup)]
    partes.append("\n## Indice de frases\n")
    partes.append("| # | estado | donde vive | frase |")
    partes.append("|---|---|---|---|")
    partes.extend(filas or ["| — | — | — | (ninguna frase de >=8 palabras) |"])
    partes.append("\n## Texto retirado (verbatim)\n")
    partes.append("```text")
    partes.append(resto_citado)
    partes.append("```")
    return "\n".join(partes) + "\n"


def _celda(f: str) -> str:
    """La frase, apta para una celda de tabla Markdown: sin `|` y acotada."""
    return f.replace("|", " ")[:120]
