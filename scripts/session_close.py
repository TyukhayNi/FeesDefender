#!/usr/bin/env python3
"""
FeesDefender — Verificación de tests pre-commit
=================================================
Ejecutar como parte del cierre de sesión desde PowerShell:

    cd "G:\\Unidades compartidas\\DESPACHO - PRODUCCION\\Base datos expedientes"
    python -m scripts.session_close && git add -A && git commit -m "<mensaje>"

El mensaje de commit lo proporciona Claude en el chat antes de que el usuario
ejecute esta línea. El resto del protocolo de cierre (STATUS.md, DEAD_ENDS.md,
memoria) lo gestiona Claude directamente. Ver STATUS.md sección "Cierre de sesión".
"""

import subprocess
import sys
from sys import executable as PYTHON
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    print("FeesDefender — pytest pre-commit")
    print("─" * 40)
    result = subprocess.run(
        [PYTHON, "-m", "pytest", "-q", "--tb=short"],
        cwd=ROOT,
    )
    if result.returncode != 0:
        print("\n❌  Tests fallando — commit abortado.")
        sys.exit(1)
    print("\n✅  Tests OK — puedes continuar con git add / commit.")


if __name__ == "__main__":
    main()
