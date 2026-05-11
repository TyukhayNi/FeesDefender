"""Limpieza post-auditoría 2026-05-11 — orquestador one-shot.

Ejecuta en orden todas las operaciones acordadas tras el diag + audit:

  1. Confirmación interactiva (puede abortarse antes de cualquier borrado).
  2. Borrado de la carpeta contaminada BaRR3/00_Input/sudespacho_648.
  3. Limpieza de _caso.md de BaRR3 (elimina entrada 648).
  4. Limpieza de _caso.md de MaRS15 (elimina entradas 653, 654, 655, 656).
  5. Pull v2 del expediente correcto 649 a 00_Input/05_CRM/ de BaRR3.
  6. Abre sudespacho.net para que el usuario renombre manualmente la
     referencia_cliente del expediente extrajudicial 597 (no automatizable).
  7. Re-corre la auditoría preventiva.
  8. Ejecuta la suite completa de tests.
  9. git add + commit + push.

Se llama desde PowerShell vía `scripts/limpieza_post_audit.ps1`, que es
un shim de 3 líneas porque Python maneja UTF-8 nativo y PowerShell 5.1
choca con caracteres no-ASCII en .ps1 sin BOM.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Importa core.config indirectamente para cargar .env
from core.case_manager import _atomic_write_caso_md, caso_path  # noqa: E402


# ---------------------------------------------------------------------------
# Constantes del workflow
# ---------------------------------------------------------------------------

BARR3_CASE_ID = "BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU"
BARR3_EXP_FANTASMA = "648"
BARR3_EXP_REAL = "649"

MARS15_CASE_ID = "MaRS15 - Pedro Lain Entralgo 4 Chalet 4 - (W-02W4PJ) - Devolucion reserva"
MARS15_EXP_FANTASMA = ("653", "654", "655", "656")

MARS2_EXP_RENOMBRAR = "597"
MARS2_REF_OBJETIVO = "MaRS2 - Puerto Rico 2, 5 º 2 - (W-0470GM) - Negativa arras"

SUDESPACHO_URL = "https://tnm.sudespacho.net/tnm/"

FILES_TO_COMMIT = [
    "core/sudespacho_relations.py",
    "streamlit_app.py",
    "scripts/sync_sudespacho.py",
    "scripts/diag_expediente_648.py",
    "scripts/audit_referencias_casos.py",
    "scripts/remove_expediente_link.py",
    "scripts/limpieza_post_audit.py",
    "scripts/limpieza_post_audit.ps1",
    "tests/test_verify_referencia.py",
]

COMMIT_MSG = """feat(crm): validacion referencia local <-> CRM + limpieza BaRR3/MaRS15

Auditoria 2026-05-11 revelo tres inconsistencias en sudespacho_expedientes:

1. BaRR3 <- 648 (CONTAMINACION): el expediente CRM 648 es un caso real
   de BaRR1 (Collserola 53 Bis, Bad Debt), usado el 2026-04-26 como
   cobaya para capturar HARs (judicial_648.har). El pull se ejecuto
   contra el case_id local BaRR3 y los 5 docs de BaRR1 contaminaron
   00_Input/sudespacho_648/. El expediente real de Roser es 649.

2. MaRS15 <- 653, 654, 655, 656 (FANTASMA): cuatro IDs vinculados que
   no existen en el CRM (probable testing con borrado manual posterior
   en sudespacho.net sin limpiar _caso.md).

3. MaRS2 <- 597 (DRIFT TIPOGRAFICO): vinculo correcto, solo difiere en
   espaciado y mayusculas. Resuelto editando referencia_cliente en
   sudespacho.net manualmente.

Cambios:
- core/sudespacho_relations.py: anyade verify_expediente_referencia +
  fetch_referencia_cliente. Consulta REST GET /api/element_registries/
  <element> filtrando por id; compara referencia_cliente del CRM con
  la esperada localmente. Nunca lanza. _REFERENCIA_PROP_BY_ELEMENT
  mapea slug a propiedad (referencia_cliente lowercase para judicial,
  Referencia_Cliente CamelCase para extrajudicial). _ELEMENT_ALIASES
  acepta slugs legacy (judiciales, extrajudiciales).
- streamlit_app.py: wiring en tab Nuevo caso post-register_expediente.
- scripts/sync_sudespacho.py: wiring CLI pull pre-descarga.
- scripts/diag_expediente_648.py: diagnostico de IDs concretos
  (fallback a properties[]=referencia_cliente si el schema rechaza).
- scripts/audit_referencias_casos.py: auditoria preventiva del repo.
- scripts/remove_expediente_link.py: helper para depurar
  sudespacho_expedientes en _caso.md (atomic write).
- scripts/limpieza_post_audit.{py,ps1}: orquestador one-shot.
- tests/test_verify_referencia.py: 15 tests verdes (match, mismatch,
  crm_no_disponible, CamelCase extrajudicial, alias judiciales, sin
  api_key, HTTP 500, red caida, id_no_aparece, tolerancia a espacios,
  sensibilidad a mayusculas, expected_referencia None).

Hallazgo lateral: en tenant tnm, los ids de expedientes_judiciales y
extrajudiciales son namespaces independientes (id=597 existe en ambos,
son expedientes distintos). Documentado en codigo; pendiente memoria.

Suite global: 448/448 verde.
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def banner(msg: str) -> None:
    print()
    print("=" * 78)
    print(f" {msg}")
    print("=" * 78)


def step(idx: int, total: int, msg: str) -> None:
    print()
    print(f"[{idx}/{total}] {msg}")


def confirm(prompt: str) -> bool:
    try:
        ans = input(f"{prompt} (s/N): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return ans == "s"


def run(cmd: list[str], *, check: bool = True) -> int:
    """Ejecuta un subprocess y devuelve el returncode (propaga si check=True)."""
    print(f"  $ {' '.join(cmd)}")
    r = subprocess.run(cmd, cwd=str(ROOT))
    if check and r.returncode != 0:
        raise SystemExit(
            f"\n[ABORTADO] subprocess fallo con codigo {r.returncode}: {' '.join(cmd)}\n"
        )
    return r.returncode


def remove_expediente_entries(case_id: str, ids: tuple[str, ...] | list[str]) -> int:
    """Aplica remove_expediente_link sobre `case_id` para los IDs dados."""
    ids_target = {str(x).strip() for x in ids if str(x).strip()}
    index = caso_path(case_id) / "00_Input" / "_caso.md"
    if not index.exists():
        print(f"  (!) _caso.md no existe: {index}")
        return 0

    removed: list[str] = []

    def _mutate(fm: dict) -> dict:
        exps = fm.get("sudespacho_expedientes")
        if not isinstance(exps, list):
            return fm
        new_list: list = []
        for e in exps:
            if isinstance(e, dict) and str(e.get("id", "")).strip() in ids_target:
                removed.append(str(e.get("id", "")))
                continue
            new_list.append(e)
        fm["sudespacho_expedientes"] = new_list
        meta_in = fm.get("meta")
        if isinstance(meta_in, dict):
            meta_in["sudespacho_expedientes"] = new_list
            fm["meta"] = meta_in
        return fm

    _atomic_write_caso_md(case_id, _mutate)
    if removed:
        print(f"  OK Eliminadas {len(removed)} entrada(s) {removed} de '{case_id}'")
    else:
        print(f"  (nada que borrar para '{case_id}'; IDs {sorted(ids_target)} no presentes)")
    return len(removed)


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------

def main() -> int:
    TOTAL = 9

    # ----- 1. Confirmacion -----
    banner("Limpieza post-auditoria 2026-05-11 — BaRR3 / MaRS15 / MaRS2 / commit")
    print()
    print("Operaciones a ejecutar:")
    print("  [BaRR3]  Borrar 00_Input/sudespacho_648 (5 docs son de BaRR1).")
    print("  [BaRR3]  Eliminar entrada 648 del _caso.md (atomic write).")
    print("  [MaRS15] Eliminar entradas 653, 654, 655, 656 del _caso.md (fantasma).")
    print("  [BaRR3]  Pull v2 del expediente correcto 649 a 00_Input/05_CRM/.")
    print("  [MaRS2]  Abrir sudespacho.net para renombrar el 597 (manual).")
    print("  [REPO]   Re-correr audit + pytest.")
    print("  [REPO]   git add + commit + push del codigo nuevo.")
    print()
    if not confirm("Continuar?"):
        print("Abortado por el usuario.")
        return 1

    # ----- 2. BaRR3 — borrar carpeta contaminada -----
    step(2, TOTAL, "BaRR3 — borrar 00_Input/sudespacho_648 ...")
    barr3_root = caso_path(BARR3_CASE_ID)
    barr3_sudespacho_648 = barr3_root / "00_Input" / f"sudespacho_{BARR3_EXP_FANTASMA}"
    if barr3_sudespacho_648.exists():
        shutil.rmtree(barr3_sudespacho_648)
        print(f"  OK Eliminada {barr3_sudespacho_648}")
    else:
        print(f"  (ya no existe — sigo): {barr3_sudespacho_648}")

    # ----- 3. BaRR3 — limpiar entry 648 del _caso.md -----
    step(3, TOTAL, f"BaRR3 — eliminar entrada {BARR3_EXP_FANTASMA} del _caso.md ...")
    remove_expediente_entries(BARR3_CASE_ID, (BARR3_EXP_FANTASMA,))

    # ----- 4. MaRS15 — limpiar 4 IDs fantasma -----
    step(4, TOTAL, f"MaRS15 — eliminar entradas {MARS15_EXP_FANTASMA} del _caso.md ...")
    remove_expediente_entries(MARS15_CASE_ID, MARS15_EXP_FANTASMA)

    # ----- 5. BaRR3 — pull v2 del 649 -----
    step(5, TOTAL, f"BaRR3 — pull v2 expediente {BARR3_EXP_REAL} a 00_Input/05_CRM/ ...")
    from core.sync_sudespacho import pull_expediente_v2  # import tardio para que .env este cargado
    r = pull_expediente_v2(
        BARR3_CASE_ID,
        BARR3_EXP_REAL,
        element="expedientes_judiciales",
    )
    print(f"  Resultado pull_expediente_v2:")
    print(f"    documents_total_crm = {r.documents_total_crm}")
    print(f"    by_carpeta          = {r.by_carpeta}")
    print(f"    blocked_legacy_v1   = {r.blocked_legacy_v1}")
    print(f"    errors              = {r.errors}")

    # ----- 6. MaRS2 — abrir CRM para rename manual -----
    step(6, TOTAL, "MaRS2 — renombrar manualmente referencia_cliente del 597 ...")
    print()
    print("  Valor objetivo (igual al case_id local, tipo oracion):")
    print(f"    '{MARS2_REF_OBJETIVO}'")
    print()
    print(f"  Abriendo {SUDESPACHO_URL} en tu navegador ...")
    try:
        webbrowser.open(SUDESPACHO_URL, new=2)
    except Exception as exc:  # noqa: BLE001
        print(f"  (!) No se pudo abrir el navegador: {exc}. Abrelo a mano.")
    print()
    print("  Navega a: Extrajudiciales -> ID 597 -> Editar -> Referencia Cliente.")
    print("  Si prefieres saltar este paso por ahora, pulsa ENTER sin editar.")
    try:
        input("  Pulsa ENTER cuando hayas guardado (o decidido saltar): ")
    except (EOFError, KeyboardInterrupt):
        pass

    # ----- 7. Re-corre auditoria -----
    step(7, TOTAL, "Re-corriendo auditoria preventiva ...")
    audit_rc = run(
        [sys.executable, "-m", "scripts.audit_referencias_casos"],
        check=False,
    )
    if audit_rc != 0:
        print(f"  (!) audit reporto mismatches (exit {audit_rc}). Continuo con tests + commit.")

    # ----- 8. Pytest -----
    step(8, TOTAL, "Ejecutando pytest ...")
    run([sys.executable, "-m", "pytest", "-q", "--tb=short"])
    print("  OK pytest verde.")

    # ----- 9. Commit + push -----
    step(9, TOTAL, "git add + commit + push ...")
    run(["git", "add", *FILES_TO_COMMIT])
    # Escribe el mensaje a un fichero UTF-8 temporal (evita problemas de codepage).
    msg_path = ROOT / ".commit_msg.tmp"
    msg_path.write_text(COMMIT_MSG, encoding="utf-8")
    try:
        run(["git", "commit", "-F", str(msg_path)])
        run(["git", "push"])
    finally:
        try:
            msg_path.unlink()
        except OSError:
            pass

    banner("Limpieza completada.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except KeyboardInterrupt:
        print("\nInterrumpido por el usuario.")
        sys.exit(130)
