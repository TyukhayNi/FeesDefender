"""CLI: python -m core.adjuntos_contenido <case_id> [--forzar]"""
from __future__ import annotations

import sys

from .pipeline import procesar_caso


def main(argv: list[str]) -> int:
    forzar = "--forzar" in argv
    casos = [a for a in argv if not a.startswith("--")]
    if not casos:
        print("uso: python -m core.adjuntos_contenido <case_id> [--forzar]")
        return 2
    rep = procesar_caso(casos[0], forzar=forzar)
    print(f"extraidos={rep.extraidos} omitidos={rep.omitidos} sin_texto={rep.sin_texto} "
          f"saltados={rep.saltados} podados={rep.podados} "
          f"pendientes_resumen={rep.pendientes_resumen} pendientes_vision={rep.pendientes_vision}")
    for e in rep.errores:
        print(f"  ERROR: {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
