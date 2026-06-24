"""Autoridad ÚNICA del corte autor/cita.

Lo usan tanto ``bodies._limpia_cita`` (Capa A) como Layer B (``inline``), garantizando que
no haya dos definiciones distintas de "lo que escribió el autor". El algoritmo es el de la
Fase 1 (``bodies._limpia_cita``), ampliado para devolver TAMBIÉN el resto citado recortado.
"""
from __future__ import annotations

import re

# Encabezados de cita típicos (es/en) que marcan el inicio de la cola citada.
_RE_CITA_HDR = re.compile(
    r"^\s*(el .+escribi[oó]:|on .+wrote:|-{2,}\s*(mensaje original|original message"
    r"|forwarded message|reenviado).*|de\s*:.*\n.*(enviado|asunto)\s*:)",
    re.IGNORECASE | re.MULTILINE,
)


def _es_linea_citada(linea: str) -> bool:
    return linea.lstrip().startswith(">")


def cortar_autor(texto: str) -> tuple[str, str | None, bool]:
    """``(autor, resto_citado|None, intercalada)``.

    ``resto_citado`` es la cola citada recortada (texto desde el punto de corte al final), o
    ``None`` si no se recortó nada. ``intercalada`` = el autor escribió entre/después de la
    cita → no se recorta y ``resto_citado`` es ``None`` (se conserva íntegro en ``autor``).
    """
    lineas = texto.splitlines()
    quoted_idx = [i for i, l in enumerate(lineas) if _es_linea_citada(l)]
    if not quoted_idx:
        # Encabezado de cita sin '>' (reenvíos): recortar desde ahí.
        m = _RE_CITA_HDR.search(texto)
        if m and m.start() > 0:
            return texto[: m.start()].rstrip(), texto[m.start():], False
        return texto.strip(), None, False
    primera = quoted_idx[0]
    autor_despues = any(
        l.strip() and not _es_linea_citada(l) and not _RE_CITA_HDR.match(l)
        for l in lineas[primera + 1:]
    )
    if autor_despues:
        return texto.strip(), None, True  # intercalada: no recortar
    corte = primera
    m = _RE_CITA_HDR.search(texto)
    if m:
        pre = texto[: m.start()].count("\n")
        corte = min(corte, pre)
    autor = "\n".join(lineas[:corte]).rstrip()
    resto = "\n".join(lineas[corte:])
    return autor, (resto if resto.strip() else None), False
