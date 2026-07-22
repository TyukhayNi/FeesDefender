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
