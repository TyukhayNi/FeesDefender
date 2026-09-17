"""El criterio del despacho para expedir una comunicación certificada.

Spec: `docs/superpowers/specs/2026-09-17-envio-certificado-codicert-design.md`.
El transporte vive en `core/codicert.py` y no sabe qué es un expediente.
"""
from __future__ import annotations


class ExpedicionError(RuntimeError):
    """El plan no se puede construir o el envío no se puede ejecutar."""


TIPOS_COMUNICACION: tuple[str, ...] = ("REQ", "OVC")
MAX_ID = 20  # límite del campo `id_personalizado` en cuatro de los cinco productos


def componer_id(w_code: str, tipo: str, ordinal: int = 1) -> str:
    """`W-04AKM2 - OVC`, y `W-04AKM2 - REQ 2` desde la segunda expedición del tipo.

    La convención no se inventa: es la que ya usan los envíos vivos, y el equipo la lee
    en el portal. Sin el tipo dentro, la OVC que sale quince días después del
    requerimiento se confundiría con él y no saldría (spec §3).
    """
    if tipo not in TIPOS_COMUNICACION:
        raise ExpedicionError(f"tipo {tipo!r}; son {TIPOS_COMUNICACION}")
    if ordinal < 1:
        raise ExpedicionError(f"ordinal {ordinal}: empieza en 1")
    ident = f"{w_code} - {tipo}" + ("" if ordinal == 1 else f" {ordinal}")
    if len(ident) > MAX_ID:
        raise ExpedicionError(
            f"el identificador {ident!r} son {len(ident)} caracteres y el máximo es {MAX_ID}")
    return ident
