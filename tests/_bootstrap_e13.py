"""Bootstrap de un hijo de E13 (`tests/test_entrypoints_mutex.py`): dos procesos REALES sobre
el mismo caso, con contención de verdad (MEJORAS #126, diseño rev. 2 §4).

Un `subprocess` no hereda los monkeypatches del test (R1/H-08), así que cada hijo arranca por
aquí: fija el entorno ANTES de importar `core`, sustituye el motor por uno que anuncia `READY`
y espera la barrera `SUELTA` (sin dormir a ciegas), y llama al `main` real del CLI.

    python tests/_bootstrap_e13.py <casos_root> <registro_locks> <ready> <suelta> <ref>
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path


def main(argv: list[str]) -> int:
    casos_root, registro, ready, suelta, ref = argv[1:6]
    os.environ["CASOS_ROOT"] = casos_root
    os.environ["FEESDEFENDER_WORKSPACE_REGISTRY"] = registro
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    from core.email_atomize import pipeline as P
    from scripts import atomize_emails as cli

    class _Informe:
        publicado = True                      # el que gana TERMINA con 0 (R2/H-05)
        notas = ["motor sustituido por el bootstrap de E13"]
        errores: list[str] = []

        @staticmethod
        def resumen() -> str:
            return "E13: motor sustituido, informe publicado"

    def motor(case_id: str):
        Path(ready).write_text(str(os.getpid()), encoding="utf-8")   # «tengo el mutex y estoy dentro»
        limite = time.monotonic() + 60
        while not Path(suelta).exists():
            if time.monotonic() > limite:
                raise TimeoutError("E13: nadie soltó la barrera")
            time.sleep(0.05)
        return _Informe()

    P.atomize_case = motor
    P.emails_out_dir = lambda case_id: Path(casos_root) / "no-importa"
    return cli.main(["--ref", ref])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
