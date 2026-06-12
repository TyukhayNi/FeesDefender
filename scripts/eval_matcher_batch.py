"""Evaluación por lotes del matcher F1 contra correos reales de procuradores.

READ-ONLY: solo consulta el CRM (busca expedientes), nunca escribe.

Uso (con workaround de env var):
    $env:LLM_CLOUD_API_KEY = [System.Environment]::GetEnvironmentVariable("LLM_CLOUD_API_KEY","User")
    python -m scripts.eval_matcher_batch

Lee scripts/intake_batch_dataset.json, corre extract_signals + match_expediente
por cada correo, compara contra la verdad-terreno (gt_*), imprime tabla resumen
y métricas, y vuelca resultados a data/_aprendizaje/intake_eval_<fecha>.json.

NOTA: el dataset y los resultados llevan PII real (correos de procuradores,
contrarios) → gitignored. Se regeneran vía gmail-ro (ver docstring del dataset).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from core.procurador_intake import (
    extract_signals,
    is_procurador_email,
    match_expediente,
)
from core.sync_sudespacho import SudespachoClient

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "scripts" / "intake_batch_dataset.json"
OUT_DIR = ROOT / "data" / "_aprendizaje"


def _su_ref_num_serie_ok(signals, em) -> bool:
    """¿El num/serie extraído coincide con la verdad-terreno?

    serie es string en formato CRM ('2025', '2023-n'); gt_serie puede venir como
    int o string → comparar normalizado a minúscula.
    """
    if em.get("gt_num") is None:
        return signals.num_expediente is None
    return (
        signals.num_expediente == em.get("gt_num")
        and str(signals.serie_expediente).lower() == str(em.get("gt_serie")).lower()
    )


def _trunc(s, n=42):
    s = (s or "").replace("\n", " ").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def main() -> int:
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    emails = data["emails"]

    results = []
    print(f"\nEvaluando {len(emails)} correos reales...\n")

    # Un único cliente CRM compartido (read-only)
    with SudespachoClient() as sudo:
        for i, em in enumerate(emails, 1):
            from_addr = em["from"]
            t0 = time.monotonic()
            row = {
                "id": em["id"],
                "from": from_addr,
                "subject": em["subject"],
                "gt_su_ref": em.get("gt_su_ref"),
                "gt_ruido": em.get("gt_ruido", False),
                "gt_nota": em.get("gt_nota", ""),
                "is_proc": is_procurador_email(from_addr),
            }
            try:
                sig = extract_signals(em["subject"], em["body"])
                row["su_ref"] = sig.su_ref
                row["num"] = sig.num_expediente
                row["serie"] = sig.serie_expediente
                row["tipo_actuacion"] = sig.tipo_actuacion
                row["es_ruido"] = sig.es_ruido
                row["su_ref_ok"] = _su_ref_num_serie_ok(sig, em)

                match = match_expediente(sig, sudo_client=sudo)
                row["confianza"] = match.confianza
                row["expediente_id"] = match.expediente_id
                row["senales"] = match.senales_usadas
                row["err"] = None
            except Exception as exc:  # noqa: BLE001
                row["err"] = f"{type(exc).__name__}: {exc}"
                row["confianza"] = "ERROR"
                row["su_ref_ok"] = False
            row["ms"] = round((time.monotonic() - t0) * 1000)
            results.append(row)
            print(
                f"[{i:2d}/{len(emails)}] {row['confianza']:8s} "
                f"su_ref={str(row.get('su_ref')):11s} "
                f"(gt={str(row['gt_su_ref'])}) exp={row.get('expediente_id')} "
                f"{_trunc(from_addr,28)}"
            )

    # --- Tabla resumen ---
    print("\n" + "=" * 120)
    print("TABLA RESUMEN")
    print("=" * 120)
    hdr = f"{'#':>2} {'remitente':28} {'su_ref':11} {'num/serie':10} {'exp_id':7} {'confianza':9} {'señales OK':12}"
    print(hdr)
    print("-" * 120)
    for i, r in enumerate(results, 1):
        ns = f"{r.get('num')}/{r.get('serie')}" if r.get("num") else "-"
        sok = "✓ su_ref" if r.get("su_ref_ok") else ("(ruido)" if r["gt_ruido"] else "✗ su_ref")
        print(
            f"{i:>2} {_trunc(r['from'],28):28} {str(r.get('su_ref')):11.11} "
            f"{ns:10} {str(r.get('expediente_id') or '-'):7} {r['confianza']:9} {sok:12}"
        )
        if r.get("err"):
            print(f"     !! {r['err']}")

    # --- Métricas ---
    n = len(results)
    alta = sum(1 for r in results if r["confianza"] == "alta")
    dudosa = sum(1 for r in results if r["confianza"] == "dudosa")
    ninguna = sum(1 for r in results if r["confianza"] == "ninguna")
    error = sum(1 for r in results if r["confianza"] == "ERROR")

    # Correos que SÍ debían matchear (no ruido) vs los que no
    archivables = [r for r in results if not r["gt_ruido"]]
    ruido_gt = [r for r in results if r["gt_ruido"]]

    su_ref_ok = sum(1 for r in archivables if r.get("su_ref_ok"))
    alta_en_archivables = sum(1 for r in archivables if r["confianza"] == "alta")
    # Aciertos de ruido: el matcher NO debe dar alta a un correo-ruido
    ruido_no_alta = sum(1 for r in ruido_gt if r["confianza"] != "alta")

    def pct(a, b):
        return f"{100*a/b:.1f}%" if b else "n/a"

    print("\n" + "=" * 120)
    print("MÉTRICAS")
    print("=" * 120)
    print(f"Total correos:                {n}")
    print(f"  ALTA:                       {alta:2d}  ({pct(alta, n)})")
    print(f"  DUDOSA:                     {dudosa:2d}  ({pct(dudosa, n)})")
    print(f"  NINGUNA:                    {ninguna:2d}  ({pct(ninguna, n)})")
    if error:
        print(f"  ERROR:                      {error:2d}  ({pct(error, n)})")
    print(f"\nCorreos archivables (no ruido): {len(archivables)}")
    print(f"  su_ref extraída correcta:   {su_ref_ok}/{len(archivables)}  ({pct(su_ref_ok, len(archivables))})")
    print(f"  match ALTA:                 {alta_en_archivables}/{len(archivables)}  ({pct(alta_en_archivables, len(archivables))})")
    print(f"\nCorreos ruido/sin-ref (gt):     {len(ruido_gt)}")
    print(f"  NO clasificados como ALTA:  {ruido_no_alta}/{len(ruido_gt)}  ({pct(ruido_no_alta, len(ruido_gt))})")

    # --- Persistir ---
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "intake_eval_2026-06-12.json"
    out.write_text(
        json.dumps(
            {
                "fecha": "2026-06-12",
                "modelo": "mistral-small-3.2-24b-instruct-2506",
                "n": n,
                "alta": alta, "dudosa": dudosa, "ninguna": ninguna, "error": error,
                "su_ref_ok_archivables": su_ref_ok,
                "n_archivables": len(archivables),
                "resultados": results,
            },
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nResultados → {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
