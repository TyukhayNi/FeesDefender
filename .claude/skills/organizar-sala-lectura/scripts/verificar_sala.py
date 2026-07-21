"""Fase verify de `organizar-sala-lectura`: contrasta el `_MANIFIESTO.md`
contra lo REALMENTE copiado en disco, con criterios duros — no resume bonito,
lista problemas. Self-contained (sin `core/`), determinista.

Motivo (sesión 2026-07-21, W-02VUDR, fusión de `HANDOFF_sala-lectura.md`
§3.2): dos discrepancias reales de conteo pasaron el reporte final sin que
nada las detectara automáticamente. Esta fase es la red de seguridad.

Motivo del chequeo de fecha (misma sesión, hallazgo posterior): 7 binarios
opacos quedaron en `0000-00-00` pese a que su espejo MD en sala de máquina
ya tenía texto extraído con fecha inequívoca (p.ej. un burofax certificado
con "Fecha y hora del envío: 08/04/2025"). `texto_espejo_md()` existe desde
la v1.9 pero su consulta era opcional en el procedimiento — nada la
verificaba después. El propósito de la sala de lectura es el timeline;
`0000-00-00` sin motivo lo rompe.
"""
from __future__ import annotations

_CHARS_MINIMOS_SOSPECHOSO = 200


def verificar(
    manifiesto_filas: list[dict],
    ficheros_en_disco: set[str],
    cobertura_filas: list[dict] | None = None,
) -> list[str]:
    """Nunca arregla nada — solo detecta. `manifiesto_filas` son dicts con
    al menos `nombre_canonico`, `sha256`, `parent_id`; si incluyen `fecha` y
    se pasa `cobertura_filas` (filas de `_cobertura.json` de sala de
    máquina), también se contrasta fecha `0000-00-00` contra texto ya
    extraído disponible. Devuelve la lista de problemas (vacía si todo
    cuadra)."""
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

    if cobertura_filas:
        # Un bundle multi-documento spliteado (core/sala_maquina.py) tiene N
        # filas de cobertura para el mismo origen, cada una con `sha256` del
        # SEGMENTO y el hash del fichero de origen en `parent_sha256` --
        # exactamente igual que texto_espejo_md() ya resuelve. Con varios
        # segmentos del mismo origen, nos quedamos con el de más chars.
        chars_ok_por_origen: dict[str, int] = {}
        for c in cobertura_filas:
            if c.get("estado") not in ("ok", "low"):
                continue
            origen = c.get("parent_sha256") or c.get("sha256")
            chars = c.get("chars") or 0
            if chars > chars_ok_por_origen.get(origen, -1):
                chars_ok_por_origen[origen] = chars
        for fila in manifiesto_filas:
            if fila.get("fecha") != "0000-00-00":
                continue
            chars = chars_ok_por_origen.get(fila.get("sha256"))
            if chars is not None and chars >= _CHARS_MINIMOS_SOSPECHOSO:
                problemas.append(
                    f"{fila['nombre_canonico']}: fecha 0000-00-00 pero hay texto "
                    f"extraído ({chars} chars) en sala de máquina -- revisar si "
                    f"contiene una fecha real antes de dar por bueno el 0000-00-00"
                )
    return problemas
