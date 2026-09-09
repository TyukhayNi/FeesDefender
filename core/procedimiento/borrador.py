"""Propone ``orden`` y ``descripción`` para un mapa nuevo. **Nunca la carpeta.**

Spec §0: la asignación documento → fase es del letrado, y esa decisión no se automatiza.
Lo que sí se puede quitar de en medio es la mecánica: en un expediente de 76 documentos,
escribir a mano 76 pares ``orden``/``descripción`` es lo que hace que la pieza no se use.
La rev. 1 dejó esto fuera **sin declararlo** (spec §2.5), y la R1 lo señaló (H-18).

Sale como texto. Esta mitad no escribe en el expediente.
"""
from __future__ import annotations

import re
import unicodedata

import yaml

#: ``D 02-A - Contrato.pdf`` → ``D-02A``. El número de documento que el CRM ya trae en el
#: nombre es la mejor propuesta de ``orden`` que existe: es la que usó el procurador al
#: aportarlo, así que coincide con la numeración del pleito.
_RE_NUM_DOC = re.compile(r"^\s*D\s*[-_ ]?\s*(\d{1,3})\s*[-_ ]?\s*([A-Za-z])?\b")

#: Tope del slug de la descripción: 50 caracteres, como el canon de la sala de lectura.
_MAX_DESC = 50


def _slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:_MAX_DESC].strip("_")


def _propuesta(doc_id: str, rev: dict, i: int) -> dict:
    nombre = str(rev.get("filename") or "")
    m = _RE_NUM_DOC.match(nombre)
    if m:
        orden = f"D-{int(m.group(1)):02d}{(m.group(2) or '').upper()}"
        resto = nombre[m.end():]
    else:
        orden = f"{i:02d}"
        resto = nombre
    resto = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", resto)      # se quita la extensión
    resto = resto.lstrip(" -_")
    return {
        "doc_id": str(doc_id),
        "orden": orden,
        "descripcion": _slug(resto) or f"documento_{i:02d}",
        "fichero": nombre,
        "lote": rev.get("modified_at") or "",
        "en_disco": bool(rev.get("path")),
    }


def _clave_orden(doc_id: str) -> tuple[int, str]:
    """Ordena por doc_id numérico cuando lo es, y alfabéticamente si no.

    Un `int(doc_id)` a pelo revienta con un id no numérico, y el CRM no promete que lo
    sean.
    """
    return (int(doc_id), "") if doc_id.isdigit() else (10**9, doc_id)


def proponer(c) -> str:
    """YAML de partida: ``carpetas`` VACÍAS y una propuesta por documento del universo."""
    propuestas = [
        _propuesta(d, r, i)
        for i, (d, r) in enumerate(
            sorted(c.listadas.items(), key=lambda kv: _clave_orden(kv[0])), 1)
    ]
    cuerpo = {
        "version": 1,
        "expediente_crm": c.expediente_id,
        "carpetas": {},
        "sin_asignar": propuestas,
    }
    cabecera = (
        "# BORRADOR del mapa procesal — generado por `procedimiento borrador-mapa`.\n"
        "#\n"
        "# `carpetas` está VACÍO a propósito: la asignación documento -> fase es tuya.\n"
        "# Mueve cada entrada de `sin_asignar` a la carpeta que le toque, dejando\n"
        "# `origen: crm`, `doc_id`, `orden` y `descripcion`. `orden` y `descripcion` son\n"
        "# propuestas: cámbialas si no te cuadran.\n"
        "#\n"
        "# `en_disco: false` significa que el CRM lo enumera y este caso NO lo bajó. Si lo\n"
        "# necesitas en la vista, bájalo antes con `sync_sudespacho intake-judicial --full`.\n"
        "#\n"
        "# Mientras quede algo en `sin_asignar`, el informe no dirá «completo».\n")
    return cabecera + yaml.safe_dump(cuerpo, allow_unicode=True, sort_keys=False)
