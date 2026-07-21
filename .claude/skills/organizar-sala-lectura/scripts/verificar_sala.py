"""Fase verify de `organizar-sala-lectura`: contrasta el `_MANIFIESTO.md`
contra lo REALMENTE copiado en disco, con criterios duros — no resume bonito,
lista problemas. Self-contained (sin `core/`), determinista.

Motivo (sesión 2026-07-21, W-02VUDR, fusión de `HANDOFF_sala-lectura.md`
§3.2): dos discrepancias reales de conteo pasaron el reporte final sin que
nada las detectara automáticamente. Esta fase es la red de seguridad.
"""
from __future__ import annotations


def verificar(manifiesto_filas: list[dict], ficheros_en_disco: set[str]) -> list[str]:
    """Nunca arregla nada — solo detecta. `manifiesto_filas` son dicts con
    al menos `nombre_canonico`, `sha256`, `parent_id`. Devuelve la lista de
    problemas (vacía si todo cuadra)."""
    problemas: list[str] = []
    nombres_manifiesto = {f["nombre_canonico"] for f in manifiesto_filas}

    for fila in manifiesto_filas:
        nombre = fila["nombre_canonico"]
        if nombre not in ficheros_en_disco:
            problemas.append(f"{nombre}: fila en manifiesto pero no existe en disco")

    for nombre in ficheros_en_disco:
        if nombre not in nombres_manifiesto:
            problemas.append(f"{nombre}: fichero en disco sin fila en el manifiesto")

    shas_manifiesto = {f.get("sha256") for f in manifiesto_filas}
    for fila in manifiesto_filas:
        parent = fila.get("parent_id") or ""
        if not parent:
            continue
        # parent_id resuelve por sha256, por nombre_canonico exacto, o —
        # convención real de bundles desde v1.1 (ver SKILL.md "Documentos
        # compuestos") — por ser el nombre PELADO de la carpeta del bundle,
        # es decir prefijo de directorio de algún nombre_canonico.
        resuelve = (
            parent in shas_manifiesto
            or parent in nombres_manifiesto
            or any(n.startswith(parent + "/") for n in nombres_manifiesto)
        )
        if not resuelve:
            problemas.append(
                f"{fila['nombre_canonico']}: parent_id {parent!r} no resuelve "
                f"a ningún documento del manifiesto (anexo huérfano)"
            )
    return problemas
