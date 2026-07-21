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

COLS_CANON = [
    "sha256", "ruta_original", "nombre_canonico", "tipo", "fecha", "parte", "parent_id",
]


def _es_separador(celdas: list[str]) -> bool:
    return bool(celdas) and all(c and set(c) <= {"-", ":"} for c in celdas)


def parse_manifiesto(texto: str) -> list[dict]:
    """Una fila-dict por fila de datos. Claves de la cabecera (o `COLS_CANON`).
    Filas con nº de celdas != nº de columnas se saltan (tolerancia heredada; el
    endurecimiento estricto es el ítem 12, fuera de alcance)."""
    cols: list[str] | None = None
    filas: list[dict] = []
    for linea in texto.splitlines():
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
            continue
        filas.append(dict(zip(cols, celdas)))
    return filas
