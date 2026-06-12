# -*- coding: utf-8 -*-
"""Registra los outputs de una skill procesal en el intake del expediente.

HELPER CANÓNICO (fuente única). Vive en ``.claude/skills/_shared/`` y se copia
byte a byte a ``scripts/`` de cada skill objetivo mediante
``scripts/sync_skill_helpers.py``. NO importa nada de ``core/`` para poder
ejecutarse dentro de un ``.skill`` empaquetado (también en móvil): solo stdlib.

Doble registro (decisión del despacho, igual en E&V y particulares):
  1. Manifiesto ``<destino>/_index.md`` — una tabla por subcarpeta de destino,
     append idempotente por fichero.
  2. Sección ``## Navegación`` de ``00_Input/_caso.md`` — wikilinks idempotentes.

Garantías:
  · Idempotente: re-ejecutar no duplica filas ni wikilinks.
  · Escritura atómica (temp + ``os.replace``) y UTF-8 sin BOM.
  · Nunca toca el frontmatter YAML de ``_caso.md`` (inserción por texto).
  · Guardia: rechaza escribir en ``90_Notas personales``.
  · Valida ``destino`` contra la estructura del expediente.
  · Sin ``_caso.md`` (modo ad-hoc): escribe solo el manifiesto y avisa por
    stderr; sale con código 0 (es un escenario esperado, no un error).

Uso:
  python registrar_outputs.py <case_dir> <outputs.json>

donde ``outputs.json`` es una lista de objetos:
  [{"fichero": "DEMANDA_W-XXXXXX.docx", "tipo": "demanda",
    "perspectiva": "actora", "destino": "05_Procedimiento",
    "fuentes": ["informe_viabilidad", "encargo"],
    "wikilink": "DEMANDA_W-XXXXXX", "estado": "borrador",
    "meta": {"roj": "", "ecli": ""}}]
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Estructura canónica del expediente (espejo de core.config.CASO_SUBDIRS).
# Se replica aquí a propósito: el helper es autónomo y no importa el core.
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

# Subcarpeta dedicada a jurisprudencia descargada (decisión #2 del plan v3).
SUBDESTINOS_EXTRA: tuple[str, ...] = (
    "05_Procedimiento/Jurisprudencia",
)

# Subcarpeta de notas personales: nunca registramos work-product aquí.
DESTINO_PROHIBIDO = "90_Notas personales"

DESTINOS_VALIDOS = set(CASO_SUBDIRS) | set(SUBDESTINOS_EXTRA)


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _manifest_header(destino: str) -> str:
    return (
        f"# {destino} — Índice de work-product\n\n"
        "> Generado/actualizado automáticamente al registrar outputs de una skill\n"
        "> procesal. Append idempotente por fichero; no editar a mano las filas.\n\n"
        "| Fichero | Tipo | Perspectiva | Fecha | Fuentes | Estado |\n"
        "|---|---|---|---|---|---|\n"
    )


def _fuentes_str(o: dict) -> str:
    """Serializa ``fuentes`` (+ ``meta``) a una celda de tabla.

    ``fuentes`` puede ser lista o cadena. Los pares de ``meta`` (p. ej. ROJ/ECLI
    de una sentencia) se anexan como ``clave=valor`` para no perder esa
    trazabilidad sin ampliar el esquema de columnas.
    """
    fuentes = o.get("fuentes", [])
    partes: list[str] = []
    if isinstance(fuentes, (list, tuple)):
        partes.extend(str(f) for f in fuentes if str(f).strip())
    elif fuentes:
        partes.append(str(fuentes))
    meta = o.get("meta") or {}
    if isinstance(meta, dict):
        partes.extend(f"{k}={v}" for k, v in meta.items() if str(v).strip())
    return "; ".join(partes)


def _validar_destino(destino: str) -> str:
    destino = (destino or "").strip().replace("\\", "/").rstrip("/")
    if not destino:
        raise ValueError("Cada output requiere 'destino' (subcarpeta del expediente).")
    if destino == DESTINO_PROHIBIDO or destino.startswith(DESTINO_PROHIBIDO + "/"):
        raise ValueError(
            f"Destino prohibido: {destino!r}. No se registra work-product en "
            f"'{DESTINO_PROHIBIDO}'."
        )
    if destino not in DESTINOS_VALIDOS:
        raise ValueError(
            f"Destino no válido: {destino!r}.\n"
            f"Válidos: {', '.join(sorted(DESTINOS_VALIDOS))}"
        )
    return destino


def update_manifest(case: Path, destino: str, outputs: list[dict]) -> Path:
    """Crea/actualiza ``<case>/<destino>/_index.md`` (idempotente por fichero)."""
    dest_dir = case / destino
    dest_dir.mkdir(parents=True, exist_ok=True)
    manifest = dest_dir / "_index.md"
    existing = manifest.read_text(encoding="utf-8") if manifest.exists() else _manifest_header(destino)

    lines = existing.splitlines()
    present = {
        ln.split("|")[1].strip().strip("`")
        for ln in lines
        if ln.startswith("| ") and "Fichero" not in ln and "---" not in ln
    }

    new_rows: list[str] = []
    for o in outputs:
        fich = o["fichero"]
        if fich in present:
            continue
        present.add(fich)
        new_rows.append(
            f"| `{fich}` | {o.get('tipo', '')} | {o.get('perspectiva', '')} | "
            f"{_today()} | {_fuentes_str(o)} | {o.get('estado', 'borrador')} |"
        )

    if new_rows:
        if not existing.endswith("\n"):
            existing += "\n"
        existing += "\n".join(new_rows) + "\n"
        _atomic_write(manifest, existing)
    return manifest


def _insertar_wikilinks(text: str, to_add: list[str]) -> str:
    """Inserta wikilinks en la sección ``## Navegación`` sin tocar el frontmatter."""
    bloque = "\n".join(to_add)
    if "## Navegación" in text or "## Navegacion" in text:
        marker = "## Navegación" if "## Navegación" in text else "## Navegacion"
        idx = text.index(marker) + len(marker)
        insert_at = text.find("\n", idx) + 1
        return text[:insert_at] + "\n" + bloque + "\n" + text[insert_at:]
    return text.rstrip() + "\n\n## Navegación\n\n" + bloque + "\n"


def update_caso_md(case: Path, outputs: list[dict]) -> Path | None:
    """Añade wikilinks a ``## Navegación`` de ``00_Input/_caso.md`` (atómico).

    Devuelve la ruta si existe el maestro, ``None`` si no (modo ad-hoc).
    """
    caso = case / "00_Input" / "_caso.md"
    if not caso.exists():
        return None
    text = caso.read_text(encoding="utf-8")
    wikilinks = [o.get("wikilink") or Path(o["fichero"]).stem for o in outputs]
    to_add = [f"- [[{w}]]" for w in wikilinks if f"[[{w}]]" not in text]
    if not to_add:
        return caso
    _atomic_write(caso, _insertar_wikilinks(text, to_add))
    return caso


def _atomic_write(path: Path, content: str) -> None:
    """Escritura atómica UTF-8 sin BOM: temp en el mismo dir + ``os.replace``."""
    tmp = path.parent / f".{path.name}.{os.getpid()}.tmp"
    try:
        tmp.write_text(content, encoding="utf-8")
        os.replace(tmp, path)
    except Exception:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise


def registrar(case_dir: str, outputs: list[dict]) -> int:
    case = Path(case_dir)
    if not outputs:
        print("[registrar_outputs] sin outputs que registrar.", file=sys.stderr)
        return 0

    # Validación previa (falla rápido y sin escribir nada si hay error de uso).
    for o in outputs:
        if not o.get("fichero"):
            raise ValueError("Cada output requiere 'fichero'.")
        o["destino"] = _validar_destino(o.get("destino", ""))

    # 1) Manifiestos por subcarpeta de destino.
    por_destino: dict[str, list[dict]] = {}
    for o in outputs:
        por_destino.setdefault(o["destino"], []).append(o)
    for destino, items in por_destino.items():
        man = update_manifest(case, destino, items)
        print(f"[registrar_outputs] manifiesto: {man}")

    # 2) Navegación del maestro (si existe).
    caso = update_caso_md(case, outputs)
    if caso is None:
        print(
            "[registrar_outputs] aviso: no existe 00_Input/_caso.md "
            "(modo ad-hoc). Registrado solo en los manifiestos.",
            file=sys.stderr,
        )
    else:
        print(f"[registrar_outputs] _caso.md: {caso}")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("Uso: python registrar_outputs.py <case_dir> <outputs.json>", file=sys.stderr)
        return 2
    with open(argv[2], encoding="utf-8") as fh:
        outputs = json.load(fh)
    if not isinstance(outputs, list):
        print("outputs.json debe ser una lista de objetos.", file=sys.stderr)
        return 2
    try:
        return registrar(argv[1], outputs)
    except ValueError as e:
        print(f"[registrar_outputs] error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
