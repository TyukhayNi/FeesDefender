"""Parser compartido de la tabla del `_MANIFIESTO.md` — stdlib puro (sin `core/`
ni `yaml`). Lo consumen `manifiesto_a_catalogo.py`, `verificar_sala.py` e
`indices_desde_manifiesto.py`, para que las tres herramientas lean la MISMA
tabla igual (backlog robustez-velocidad, ítems 7 y 8): el agente que clasifica
no debe además ensamblar a mano el parseo que lo verifica.

Parseo por CABECERA: los nombres de columna se toman de la fila de cabecera del
propio manifiesto, así que añadir columnas (p. ej. `categoria`,
`subcategoria_crm`) no rompe manifiestos viejos de 7 columnas. Sin cabecera
reconocible, se asume el orden canónico de 7 columnas.
"""
from __future__ import annotations

import re

COLS_CANON = [
    "sha256", "ruta_original", "nombre_canonico", "tipo", "fecha", "parte", "parent_id",
]

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MD5_RE = re.compile(r"^md5:[0-9a-f]{32}$")


def _es_separador(celdas: list[str]) -> bool:
    return bool(celdas) and all(c and set(c) <= {"-", ":"} for c in celdas)


def sha_valido(valor: str) -> bool:
    """`True` si el valor de la columna sha256 es un sha256 real (64 hex), un
    `md5:<32 hex>` (Modo 3 degradado, ítem 13), o vacío (placeholder tolerado)."""
    v = (valor or "").strip()
    return v == "" or bool(_SHA256_RE.match(v)) or bool(_MD5_RE.match(v))


def parse_manifiesto(texto: str, *, estricto: bool = False) -> list[dict]:
    """Una fila-dict por fila de datos. Claves de la cabecera (o `COLS_CANON`).
    Con `estricto=True`, una línea candidata (empieza por `|`, no cabecera, no
    separador) cuyo nº de celdas != nº de columnas lanza `ValueError` (ítem 12:
    ninguna fila desaparece del catálogo en silencio). Sin `estricto` (default)
    esas filas se saltan — comportamiento heredado, no rompe manifiestos viejos."""
    cols: list[str] | None = None
    filas: list[dict] = []
    rechazadas: list[str] = []
    for i, linea in enumerate(texto.splitlines(), 1):
        s = linea.strip()
        if not s.startswith("|"):
            continue
        celdas = [c.strip() for c in s.strip("|").split("|")]
        if _es_separador(celdas):
            continue
        if celdas and celdas[0] == "sha256":
            cols = celdas
            continue
        if cols is None:
            cols = COLS_CANON
        if len(celdas) != len(cols):
            rechazadas.append(f"  línea {i}: {len(celdas)} celdas, se esperaban {len(cols)}: {s}")
            continue
        filas.append(dict(zip(cols, celdas)))
    if estricto and rechazadas:
        raise ValueError(
            "fila(s) malformada(s) en el _MANIFIESTO.md (nº de columnas incorrecto) — "
            "se perderían del catálogo en silencio:\n" + "\n".join(rechazadas))
    return filas


# --- `## No copiados` (MEJORAS #316) ------------------------------------------------
#
# Cada fichero de `00_Input` da cuenta de sí con una fila —por su ruta, o por su sha256 si es
# copia de otro— o con una línea `excluido` en esta sección. Las líneas `duplicado` son para
# quien lee: el duplicado lo prueba el sha256, no la frase (R1/H-04 y H-09 del #408). Hasta el
# 2026-09-26 la sección era texto libre —cinco formatos distintos en los manifiestos reales, y
# ficheros enteros que no aparecían en ninguno—, así que nadie podía comprobar que la sala de
# lectura hubiera dado cuenta de todo.
_CABECERA_NO_COPIADOS = re.compile(r"^##\s+No copiados\b", re.IGNORECASE)
_LINEA_NO_COPIADO = re.compile(
    r"^\s*-\s+(?P<motivo>duplicado(?:, saltado)?|excluido):\s+`(?P<ruta>[^`]+)`"
    r"\s+—\s+(?P<detalle>\S.*?)\s*$")
#: Un `duplicado` dice de qué: `— de `lo que se conserva`` (R1/H-05 del #408). Los 47 de los
#: manifiestos reales lo cumplen.
_DETALLE_DE_DUPLICADO = re.compile(r"de\s+`[^`]+`")


def parse_no_copiados(texto: str, *, estricto: bool = False) -> list[dict]:
    """Las declaraciones de `## No copiados`: `{motivo, ruta, detalle}` por línea.

    Formato cerrado: ``- duplicado: `ruta_original` — de `lo que se conserva` `` o
    ``- excluido: `ruta_original` — motivo``. Se acepta el alias ``duplicado, saltado``, que
    es como lo escribieron los manifiestos anteriores. Una viñeta de la sección que no casa
    con el formato —prosa que nombra varios ficheros, una línea sin motivo, un `duplicado`
    que no dice de qué— **no se puede cruzar con nada**: con `estricto=True` es un
    `ValueError`, y sin él se ignora.

    La sección llega hasta el siguiente encabezado de nivel 1 o 2: un `###` es subsección
    suya, como en Markdown. El texto sin viñeta es comentario —los manifiestos reales ponen
    rótulos como «Excluidos:»— y no declara nada, así que no puede sacar a nadie de la verja:
    la fuente que nombre sigue sin dar cuenta de sí (R1/H-05 del #408).
    """
    dentro = False
    fuera: list[dict] = []
    rechazadas: list[str] = []
    for i, linea in enumerate(texto.splitlines(), 1):
        if re.match(r"^#{1,2}\s", linea):
            dentro = bool(_CABECERA_NO_COPIADOS.match(linea))
            continue
        s = linea.strip()
        if not dentro or not s.startswith("-"):
            continue
        m = _LINEA_NO_COPIADO.match(linea)
        if not m or (m.group("motivo").startswith("duplicado")
                     and not _DETALLE_DE_DUPLICADO.match(m.group("detalle"))):
            rechazadas.append(f"  línea {i}: {s}")
            continue
        fuera.append({
            "motivo": "duplicado" if m.group("motivo").startswith("duplicado") else "excluido",
            "ruta": m.group("ruta").strip(),
            "detalle": m.group("detalle"),
        })
    if estricto and rechazadas:
        raise ValueError(
            "línea(s) de «## No copiados» fuera del formato "
            "`- duplicado|excluido: `ruta` — motivo` — no se pueden cruzar con nada:\n"
            + "\n".join(rechazadas))
    return fuera
