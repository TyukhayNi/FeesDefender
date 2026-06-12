# -*- coding: utf-8 -*-
"""Scaffolding canónico de expediente: árbol ``CASO_SUBDIRS`` + ``_caso.md`` mínimo.

HELPER CANÓNICO (fuente única) en ``.claude/skills/_shared/``, copiado byte a byte
a cada skill por ``scripts/sync_skill_helpers.py``. Stdlib pura: ejecutable dentro
de un ``.skill`` empaquetado (también en móvil), sin importar ``core/``.

Es el **único** camino de apertura para expedientes de particulares (escenario B
del plan): produce exactamente el mismo árbol que el core E&V
(``core.case_manager.ensure_case``) y un ``_caso.md`` con la misma estructura de
secciones, pero **mínimo** —``tipo_expediente: particular``, sin campos E&V—. La
no divergencia con el core se garantiza con ``tests/test_scaffold_particular.py``
(``CASO_SUBDIRS`` aquí == ``core.config.CASO_SUBDIRS``).

Uso programático:
  from scaffold_caso import scaffold, CASO_SUBDIRS
  scaffold(base_dir, titulo="...", tipo_expediente="particular", cliente="...", ...)

Uso CLI:
  python scaffold_caso.py <base_dir> --titulo "..." [--cliente ...] [--contraparte ...]
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Espejo de core.config.CASO_SUBDIRS. Replicado a propósito (autonomía del
# helper). Un test garantiza que no diverge del core.
CASO_SUBDIRS: tuple[str, ...] = (
    "00_Input",
    "01_Procesado",
    "02_Analisis",
    "03_Decision",
    "04_Output predemanda",
    "05_Procedimiento",
    "06_Anonimizado",
    "07_AI cowork",
    "90_Notas personales",
)


def _campo(valor: str | float | None) -> str:
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        return "_(pendiente)_"
    return str(valor)


def construir_caso_md(
    *,
    case_id: str,
    titulo: str,
    tipo_expediente: str,
    cliente: str | None,
    contraparte: str | None,
    organo: str | None,
    cuantia: str | None,
    estado: str,
    fecha: str,
) -> str:
    """Devuelve el contenido del ``_caso.md`` mínimo (frontmatter YAML + cuerpo).

    El frontmatter se escribe a mano (líneas ``clave: valor``, YAML válido) para
    no depender de PyYAML en entornos empaquetados. Es legible por
    ``core.utils.read_md``.
    """
    fm = (
        "---\n"
        f"case_id: {case_id}\n"
        "tipo: caso_index\n"
        f"tipo_expediente: {tipo_expediente}\n"
        f"fecha: {fecha}\n"
        f"estado: {estado}\n"
        "---\n"
    )
    body = (
        f"# {titulo}\n\n"
        f"Caso `{case_id}` — estado **{estado}**.\n\n"
        "## Partes\n\n"
        f"- Cliente: {_campo(cliente)}\n"
        f"- Contraparte: {_campo(contraparte)}\n\n"
        "## Sede\n\n"
        "- Jurisdicción: civil\n"
        f"- Órgano: {_campo(organo)}\n"
        f"- Cuantía: {_campo(cuantia)}\n\n"
        "## Navegación\n"
    )
    return fm + "\n" + body


def scaffold(
    base_dir: str | Path,
    *,
    titulo: str,
    case_id: str | None = None,
    tipo_expediente: str = "particular",
    cliente: str | None = None,
    contraparte: str | None = None,
    organo: str | None = None,
    cuantia: str | None = None,
    estado: str = "instruccion",
    fecha: str | None = None,
) -> Path:
    """Crea ``CASO_SUBDIRS`` bajo ``base_dir`` y ``00_Input/_caso.md`` (mínimo).

    Idempotente: no recrea carpetas existentes ni sobrescribe un ``_caso.md`` ya
    presente. Devuelve la ruta del expediente.
    """
    base = Path(base_dir).expanduser().resolve()
    for sub in CASO_SUBDIRS:
        (base / sub).mkdir(parents=True, exist_ok=True)

    caso = base / "00_Input" / "_caso.md"
    if not caso.exists():
        contenido = construir_caso_md(
            case_id=case_id or titulo,
            titulo=titulo,
            tipo_expediente=tipo_expediente,
            cliente=cliente,
            contraparte=contraparte,
            organo=organo,
            cuantia=cuantia,
            estado=estado,
            fecha=fecha or datetime.now().strftime("%Y-%m-%d"),
        )
        caso.write_text(contenido, encoding="utf-8")
    return base


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Crea el árbol CASO_SUBDIRS y un _caso.md mínimo.")
    p.add_argument("base_dir", help="Ruta donde se crea el expediente.")
    p.add_argument("--titulo", required=True)
    p.add_argument("--case-id", default=None)
    p.add_argument("--tipo-expediente", default="particular")
    p.add_argument("--cliente", default=None)
    p.add_argument("--contraparte", default=None)
    p.add_argument("--organo", default=None)
    p.add_argument("--cuantia", default=None)
    args = p.parse_args(argv)
    base = scaffold(
        args.base_dir,
        titulo=args.titulo,
        case_id=args.case_id,
        tipo_expediente=args.tipo_expediente,
        cliente=args.cliente,
        contraparte=args.contraparte,
        organo=args.organo,
        cuantia=args.cuantia,
    )
    print(f"[scaffold_caso] expediente creado en: {base}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
