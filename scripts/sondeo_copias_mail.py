"""Sondeo: ¿cuántas filas `mail` tiene un mismo Message-ID en el CRM, y en qué cuentas?

**Solo lectura. No escribe nada en el CRM.**

## Qué contesta, y por qué importa

`procesal@` no está configurado en Roundcube: reenvía a cuatro buzones personales que sí lo
están. **Cada persona que relaciona un correo desde SU Roundcube crea SU fila `mail`**, así
que un mismo Message-ID puede tener hasta cuatro filas, con relaciones distintas cada una.

Eso rompe dos supuestos que el código dio por buenos durante meses:

- **`uid` no es único**, así que un filtro `uid=<id>` puede devolver varias filas y
  `core.procurador_relate.resolver_cuenta` devuelve `None` — que **no** significa «no
  indexado».
- **`findRelations` da una vista POR COPIA** mientras la relación que escribe el relate es
  **global** (`INTEGRACION_SUDESPACHO §10.10`).

Medido el 2026-09-07 con este sondeo: **6,3 %** de los Message-ID tiene más de una copia
(203 con dos, 17 con tres, 15 con cuatro, sobre 3.710 muestreados).

⚠️ **El tamaño de la muestra cambia la respuesta, y un 0 % NO es prueba de nada.** Medido el
2026-09-08 con este mismo script: **2 páginas → 0,0 %**; 8 páginas → 6,3 %. La muestra va
ordenada por `uid`, así que las páginas bajas caen en una región de Message-ID sin copias
múltiples. Por eso el sondeo imprime siempre un **CONTROL**: si no ha visto ni un solo uid
con varias copias, su cero no acredita nada y lo dice. Amplía `--paginas` antes de concluir.

## Uso

    python -m scripts.sondeo_copias_mail                      # censo, 8 páginas de 500
    python -m scripts.sondeo_copias_mail --paginas 20         # muestra más grande
    python -m scripts.sondeo_copias_mail --uid '<x@ejemplo.invalid>'   # detalle de UNO, con relaciones

## Higiene

La SALIDA contiene Message-ID reales, y con `--uid` también ids de expediente: es dato de
cliente. **No se commitea, no se pega en el chat ni en la bitácora, no se guarda en el
árbol del repo.** El script en sí no contiene ninguno.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts._sondeo_crm import (  # noqa: E402
    cliente_rest, control_positivo, distribucion_copias, filas_mail_por_uid, resolver_env,
)


def censo(t, paginas: int, por_pagina: int) -> None:
    """Distribución de copias por Message-ID sobre una muestra ordenada por `uid`."""
    from core.procurador_relate import _items, _valores

    pares: list[tuple[str, str]] = []
    for pagina in range(1, paginas + 1):
        params = [
            ("properties[0]", "uid"), ("properties[1]", "cuenta"),
            ("itemsPerPage", str(por_pagina)), ("page", str(pagina)),
            ("order[uid]", "asc"),
        ]
        r = t.get("/api/element_registries/mail", params=params)
        if r.status_code != 200:
            print(f"  página {pagina}: HTTP {r.status_code} — se para aquí")
            break
        filas = [_valores(i) for i in _items(r.json())]
        if not filas:
            print(f"  página {pagina}: vacía — se para aquí")
            break
        pares += [(str(v.get("uid") or ""), str(v.get("cuenta") or "")) for v in filas]
        print(f"  página {pagina}: {len(filas)} filas (acumuladas {len(pares)})")

    dist, interior = distribucion_copias(pares)
    total = len(interior)
    if not total:
        print("\nla muestra no tiene interior: amplía --paginas")
        return
    print(f"\nMessage-ID en el interior de la muestra: {total}"
          f"   (se descartan los 2 bordes: sus copias pueden caer fuera)")
    for n in sorted(dist):
        print(f"  {n} cuenta(s): {dist[n]:6}   {100 * dist[n] / total:5.1f} %")
    multi = sum(v for k, v in dist.items() if k > 1)
    print(f"\nCON MÁS DE UNA COPIA: {multi} de {total}  ({100 * multi / total:.1f} %)")
    if multi:
        print("CONTROL: el sondeo vio uids con varias copias -> SÍ, mide")
    else:
        print("CONTROL: NO ha visto ni un uid con varias copias.")
        print("  Este 0 % no acredita nada: puede ser la región de `uid` que tocó la muestra,")
        print(f"  o puede ser el instrumento. El 2026-09-07, con 8 páginas, salió 6,3 %;")
        print(f"  llevas {paginas}. Amplía --paginas antes de concluir que la multicopia no ocurre.")


def detalle(t, uid: str) -> None:
    """Las copias de UN Message-ID, y las relaciones que cada una ve."""
    from core.procurador_relate import buscar_relaciones

    filas = filas_mail_por_uid(t, uid)
    if filas is None:
        print("  no se pudo leer la tabla `mail` (HTTP != 200): estado INDETERMINADO,")
        print("  que no es lo mismo que «no hay filas».")
        return
    ctas = sorted({str(f.get("cuenta") or "") for f in filas})
    print(f"  filas={len(filas)}   cuentas={ctas}")
    vistos = []
    for cuenta in ctas:
        rel = buscar_relaciones(uid, account=cuenta, transport=t)
        if rel.error:
            print(f"    cta {cuenta:>3}: ERROR {rel.error[:70]}")
            continue
        vistos.append(rel.pares)
        print(f"    cta {cuenta:>3}: {sorted(rel.pares) or '(sin relaciones en esta copia)'}")
    print(f"  CONTROL: alguna copia devolvió relaciones -> "
          f"{'SÍ, mide' if control_positivo(vistos) else 'NO — no se puede concluir «sin relacionar»'}")
    if len(ctas) > 1:
        print("  NOTA: la relación del relate es GLOBAL; que una copia no la vea no significa")
        print("        que no esté (INTEGRACION_SUDESPACHO §10.10).")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--uid", help="Message-ID concreto; con o sin <>. Sin esto, hace el censo.")
    ap.add_argument("--paginas", type=int, default=8, help="páginas del censo (default 8)")
    ap.add_argument("--por-pagina", type=int, default=500, help="filas por página (default 500)")
    args = ap.parse_args(argv)

    env = resolver_env(ROOT)
    print(f".env: {env.descripcion}")
    if env.cargado is None:
        print("Sin .env no hay `x-api-key`. Aborta antes de dar un error de red confuso.")
        return 2

    with cliente_rest() as t:
        if args.uid:
            print(f"\n=== detalle de {args.uid} ===")
            detalle(t, args.uid)
        else:
            print(f"\n=== censo de copias ({args.paginas} x {args.por_pagina}) ===")
            censo(t, args.paginas, args.por_pagina)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
