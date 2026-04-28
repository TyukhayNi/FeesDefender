#!/usr/bin/env python3
"""
FeesDefender — Cierre de sesión
================================
Ejecutar al final de cada sesión productiva desde PowerShell:

    cd "G:\\Unidades compartidas\\DESPACHO - PRODUCCION\\Base datos expedientes"
    python -m scripts.session_close

Pasos automatizados:
    1. pytest -q  (aborta si hay fallos)
    2. git diff --stat  (muestra cambios de la sesión)
    3. Actualiza "Última actualización" en STATUS.md
    4. Propone y ejecuta git commit (con confirmación)
    5. Recuerda actualizar DEAD_ENDS.md si hubo callejones nuevos
"""

import subprocess
import sys
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATUS_MD = ROOT / "STATUS.md"
DEAD_ENDS_MD = ROOT / "docs" / "DEAD_ENDS.md"


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _run(args: list[str], capture: bool = True) -> tuple[str, int]:
    """Ejecuta un comando en el directorio raíz del proyecto."""
    result = subprocess.run(
        args,
        capture_output=capture,
        text=True,
        cwd=ROOT,
    )
    return (result.stdout or "").strip(), result.returncode


def _ask(prompt: str, default: str = "") -> str:
    try:
        value = input(prompt).strip()
        return value if value else default
    except (EOFError, KeyboardInterrupt):
        return default


def _header(title: str) -> None:
    print(f"\n{'─' * 55}")
    print(f"  {title}")
    print('─' * 55)


# ──────────────────────────────────────────────
# Pasos
# ──────────────────────────────────────────────

def step_tests() -> bool:
    _header("1 / 5 · Tests")
    print("Ejecutando pytest -q …\n")
    _, rc = _run(["pytest", "-q", "--tb=short"], capture=False)
    if rc != 0:
        print("\n❌  Tests fallando. Resolver antes de cerrar la sesión.")
        return False
    print("\n✅  Todos los tests pasan.")
    return True


def step_diff() -> bool:
    _header("2 / 5 · Cambios en esta sesión")
    stat, _ = _run(["git", "diff", "--stat", "HEAD"])
    short, _ = _run(["git", "status", "--short"])
    if stat:
        print(stat)
    elif short:
        print(short)
    else:
        print("  (sin cambios respecto al último commit)")
    return True


def step_status_md() -> bool:
    _header("3 / 5 · Actualizar STATUS.md")
    if not STATUS_MD.exists():
        print(f"  ⚠️  No se encontró {STATUS_MD}")
        return False

    today = date.today().strftime("%Y-%m-%d")
    summary = _ask(f"Resumen de la sesión en 2-4 palabras [{today}]: ")
    if not summary:
        summary = "sesión sin resumen"

    content = STATUS_MD.read_text(encoding="utf-8")
    new_line = f"**Última actualización:** {today} ({summary})"
    updated = re.sub(
        r"\*\*Última actualización:\*\*.*",
        new_line,
        content,
        count=1,
    )
    if updated == content:
        print("  ⚠️  No se encontró el patrón 'Última actualización' en STATUS.md.")
        print(f"  Añade manualmente: {new_line}")
    else:
        STATUS_MD.write_text(updated, encoding="utf-8")
        print(f"  ✅  STATUS.md → {new_line}")
    return True


def step_commit() -> bool:
    _header("4 / 5 · Commit")

    short, _ = _run(["git", "status", "--short"])
    if not short:
        print("  Nada que commitear.")
        return True

    print("Archivos con cambios:")
    print(short)

    print("\nConvención: tipo(scope): descripción")
    print("  Tipos: feat · fix · test · docs · chore · prompt · data")
    print("  Scopes frecuentes: sudespacho_create · sync_sudespacho · case_manager ·")
    print("    pipeline · scorer · viability · demanda · streamlit · docs · tests · config")
    msg = _ask("\nMensaje de commit (Enter para saltar): ")
    if not msg:
        print("  Commit omitido. Recuerda hacerlo manualmente.")
        return True

    _, rc1 = _run(["git", "add", "-A"], capture=False)
    if rc1 != 0:
        print("  ❌  git add falló.")
        return False

    _, rc2 = _run(["git", "commit", "-m", msg], capture=False)
    if rc2 != 0:
        print("  ❌  git commit falló.")
        return False

    print("  ✅  Commit realizado. El hook post-commit hace el push automáticamente.")
    return True


def step_reminders() -> None:
    _header("5 / 5 · Recordatorios finales")

    # Dead ends
    print("¿Se descubrió algún callejón sin salida en esta sesión?")
    print(f"  → Si es así, añadirlo a docs/DEAD_ENDS.md")
    new_dead_end = _ask("  ¿Añadir entrada a DEAD_ENDS.md ahora? (s/N): ")
    if new_dead_end.lower() == "s":
        title = _ask("  Título corto: ")
        tried = _ask("  Qué se intentó: ")
        result = _ask("  Resultado: ")
        conclusion = _ask("  Conclusión: ")
        entry = (
            f"\n\n### {title}\n"
            f"- **Intentado:** {tried}\n"
            f"- **Resultado:** {result}\n"
            f"- **Confirmado:** {date.today().strftime('%Y-%m-%d')}\n"
            f"- **Conclusión:** {conclusion}\n"
        )
        with open(DEAD_ENDS_MD, "a", encoding="utf-8") as f:
            f.write(entry)
        print(f"  ✅  Entrada añadida a {DEAD_ENDS_MD.name}")

    # Dependencias
    print("\n¿Hay ficheros que deberían actualizarse por dependencia?")
    print("  → Consultar tabla en docs/ARQUITECTURA.md sección 'Mapa de dependencias'")

    # Instrucciones Cowork
    print("\nSi los cambios de esta sesión son significativos, actualiza las")
    print("  instrucciones del proyecto Cowork para que reflejen el nuevo STATUS.md.")

    print("\n✅  Sesión cerrada.")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main() -> None:
    print("=" * 55)
    print("  FeesDefender — Cierre de sesión")
    print("=" * 55)

    if not step_tests():
        sys.exit(1)

    step_diff()
    step_status_md()
    step_commit()
    step_reminders()


if __name__ == "__main__":
    main()
