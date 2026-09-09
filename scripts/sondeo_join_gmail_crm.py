"""Sondeo: de los correos de un buzón de Gmail, ¿cuáles están en el CRM y relacionados?

**Solo lectura, en los dos extremos. No escribe en Gmail ni en el CRM.**

## Qué contesta

Recorre el camino exacto de producción —`core.gmail_source.fetch_emails` calcula el
`email_id`, que **es** el Message-ID RFC— y para cada correo pregunta al CRM:

1. ¿tiene fila en la tabla `mail`? (y en cuántas cuentas)
2. ¿con qué está relacionado?

Sirve para dos cosas distintas:

- **Diagnóstico:** medir la frontera «lo que el CRM conoce» frente a «lo que hay en el
  buzón». Medido el 2026-09-07 sobre 32 correos de `procesal@`: 23 con fila y **los 23
  relacionados** con su `expedientes_judiciales`; 9 sin fila. O sea **indexado ⟺ alguien lo
  relacionó a mano** — lo hace Ana desde su Roundcube, y `id_creador` lo confirma.
- **Semilla del arnés de evaluación de F1** (`MEJORAS #179`): los correos ya relacionados
  son un set etiquetado **por la persona cuyo criterio es el patrón**, y se renueva a
  diario. Con `--csv` sale el par `(Message-ID, expediente)` para cotejarlo contra lo que
  proponga el matcher. **Ojo al sesgo, que está medido:** solo cubre lo que se archivó; los
  pendientes —9 de 32, uno de ellos en SPAM— no tienen etiqueta, y son los raros.

## Uso

    python -m scripts.sondeo_join_gmail_crm                          # procesal@, 4 días
    python -m scripts.sondeo_join_gmail_crm --dias 30 --max 200
    python -m scripts.sondeo_join_gmail_crm --cuenta otra@dominio
    python -m scripts.sondeo_join_gmail_crm --csv > /ruta/FUERA/del/repo.csv

Requiere el token OAuth de lectura de Gmail en `~/.gmail-mcp/tokens/` (el mismo que usa
`core.gmail_source`), así que corre en el PC, no en la nube.

## Higiene

La SALIDA contiene Message-ID, remitentes, asuntos e ids de expediente: **es dato de
cliente**. No se commitea, no se pega en el chat ni en la bitácora, y el `--csv` va a una
ruta **fuera del árbol del repo**. El script en sí no contiene ninguno.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts._sondeo_crm import (  # noqa: E402
    cliente_rest, control_positivo, filas_mail_por_uid, resolver_env,
)

CUENTA_POR_DEFECTO = "procesal@tyukhay.legal"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cuenta", default=CUENTA_POR_DEFECTO, help=f"buzón (default {CUENTA_POR_DEFECTO})")
    ap.add_argument("--dias", type=int, default=4, help="ventana en días (default 4)")
    ap.add_argument("--max", type=int, default=60, help="tope de correos (default 60)")
    ap.add_argument("--csv", action="store_true",
                    help="salida CSV (message_id, cuentas, elemento, miembro) para el arnés de F1")
    args = ap.parse_args(argv)

    env = resolver_env(ROOT)
    if not args.csv:
        print(f".env: {env.descripcion}")
    if env.cargado is None:
        print("Sin .env no hay `x-api-key`.", file=sys.stderr)
        return 2

    from core.gmail_source import fetch_emails
    from core.procurador_relate import buscar_relaciones

    correos = fetch_emails(account=args.cuenta,
                           query=f"in:anywhere newer_than:{args.dias}d",
                           max_results=args.max)

    escritor = csv.writer(sys.stdout) if args.csv else None
    if escritor:
        escritor.writerow(["message_id", "cuentas", "elemento", "miembro", "asunto"])

    con_fila = sin_fila = ilegible = 0
    relaciones_vistas: list[object] = []
    with cliente_rest() as t:
        for e in sorted(correos, key=lambda c: c.date or "", reverse=True):
            filas = filas_mail_por_uid(t, e.email_id)
            asunto = (e.subject or "")[:44]
            if filas is None:
                ilegible += 1
                if not escritor:
                    print(f"  ILEGIBLE  (no se pudo preguntar)          | {asunto}")
                continue
            if not filas:
                sin_fila += 1
                if not escritor:
                    print(f"  sin fila `mail`                          | {asunto}")
                continue
            con_fila += 1
            ctas = sorted({str(f.get("cuenta") or "") for f in filas})
            pares: set = set()
            for cuenta in ctas:
                rel = buscar_relaciones(e.email_id, account=cuenta, transport=t)
                if not rel.error:
                    pares |= rel.pares
            relaciones_vistas.append(pares)
            if escritor:
                for elem, miembro in sorted(pares) or [("", "")]:
                    escritor.writerow([e.email_id, "|".join(ctas), elem, miembro, e.subject or ""])
            else:
                print(f"  ctas={','.join(ctas):<8} {sorted(pares) or '(sin relaciones)'}"
                      f"  | {asunto}")

    if escritor:
        return 0
    total = con_fila + sin_fila + ilegible
    print(f"\ncorreos leídos de {args.cuenta}: {total}")
    print(f"  con fila en `mail`: {con_fila}   sin fila: {sin_fila}   ilegibles: {ilegible}")
    print(f"CONTROL: el sondeo vio al menos una relación -> "
          f"{'SÍ, mide' if control_positivo(relaciones_vistas) else 'NO — un cero aquí puede ser el instrumento'}")
    if sin_fila and not con_fila:
        print("NOTA: cero con fila y varios sin ella suele ser un token de Gmail de otra cuenta,")
        print("      no un CRM vacío. Compruébalo antes de concluir nada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
