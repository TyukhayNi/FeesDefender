from __future__ import annotations

import re

_GEN = ("# GENERADO por core.adjuntos_contenido — texto fiel determinista; "
        "el RESUMEN puede ser de IA (marcado).")
_RESUMEN_PENDIENTE = "_(pendiente; capa LLM en sesión)_"
_TEXTO_VACIO = "_(sin texto extraído)_"


def render_contenido(*, att_id: str, nombre_original: str, tipo: str, sha256: str,
                     metodo: str, caracteres: int, confianza: str, resumen_estado: str,
                     vision_estado: str, mensajes: list[str], resumen: str | None,
                     texto: str) -> str:
    ocr = "true" if metodo == "docling" else "false"
    resumen_body = resumen.strip() if (resumen and resumen.strip()) else _RESUMEN_PENDIENTE
    texto_body = texto if texto.strip() else _TEXTO_VACIO
    return (
        "---\n"
        f"{_GEN}\n"
        f"att_id: {att_id}\n"
        f"nombre_original: {nombre_original}\n"
        f"tipo: {tipo}\n"
        f"sha256: {sha256}\n"
        f"metodo_extraccion: {metodo}\n"
        f"ocr_aplicado: {ocr}\n"
        f"caracteres: {caracteres}\n"
        f"confianza: {confianza}\n"
        f"resumen_estado: {resumen_estado}\n"
        f"vision_estado: {vision_estado}\n"
        f"mensajes: [{', '.join(mensajes)}]\n"
        "---\n\n"
        "## Resumen\n\n"
        f"{resumen_body}\n\n"
        "## Texto\n\n"
        f"{texto_body}\n"
    )


def _sanea_resumen(texto: str) -> str:
    """Demota cualquier encabezado markdown del resumen a texto plano.

    Un resumen es texto libre (potencialmente de un LLM); sin esto, un resumen
    que contuviera la línea ``## Texto`` o ``## Resumen`` inyectaría un marcador
    estructural y corrompería el documento (el texto fiel se preserva igualmente,
    pero el .md quedaría malformado)."""
    return "\n".join(
        re.sub(r"^\s*#{1,6}\s+", "", linea) for linea in texto.splitlines()
    ).strip()


def reemplazar_resumen(md: str, nuevo_resumen: str) -> str:
    """Sustituye el cuerpo de `## Resumen` preservando el resto byte a byte."""
    nuevo = _sanea_resumen(nuevo_resumen)
    patron = re.compile(r"(## Resumen\n\n).*?(\n\n## Texto)", re.DOTALL)
    return patron.sub(lambda m: m.group(1) + nuevo + m.group(2), md, count=1)


def set_frontmatter(md: str, clave: str, valor: str) -> str:
    patron = re.compile(rf"(?m)^({re.escape(clave)}: ).*$")
    return patron.sub(rf"\g<1>{valor}", md, count=1)


def parsear_contenido(md: str) -> tuple[dict, str, str]:
    """Devuelve (frontmatter, cuerpo_resumen, cuerpo_texto)."""
    partes = md.split("---\n", 2)
    fm_block = partes[1] if len(partes) >= 3 else ""
    cuerpo = partes[2] if len(partes) >= 3 else md
    fm: dict = {}
    for linea in fm_block.splitlines():
        if linea.startswith("#") or ": " not in linea:
            continue
        clave, valor = linea.split(": ", 1)
        fm[clave.strip()] = valor.strip()
    resumen_body, texto_body = "", ""
    if "## Texto" in cuerpo:
        antes, despues = cuerpo.split("## Texto", 1)
        texto_body = despues.strip()
    else:
        antes = cuerpo
    if "## Resumen" in antes:
        resumen_body = antes.split("## Resumen", 1)[1].strip()
    return fm, resumen_body, texto_body
