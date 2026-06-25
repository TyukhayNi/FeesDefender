"""Capa de caso: entrega sellada (_entregas/). Snapshot congelado + manifiesto de hashes.

Diseño: spec §5.3. Acción manual; append-only (cada sello = entrega distinta, NO idempotente).
"""
from __future__ import annotations

import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from core.email_export import _slug_descripcion
from core.intake_manifest import compute_sha256_bytes

SET_ENTREGABLE = ["mensajes", "adjuntos", "vistas",
                  "corpus.jsonl", "CORREOS_LECTURA.md", "INDICE_ADJUNTOS.md"]


def _git_commit() -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                           encoding="utf-8", errors="replace")
        return r.stdout.strip() if r.returncode == 0 else "desconocido"
    except Exception:  # noqa: BLE001 — git ausente / no es repo
        return "desconocido"


def _destino_unico(base: Path) -> Path:
    if not base.exists():
        return base
    n = 2
    while (cand := base.with_name(f"{base.name}_{n}")).exists():
        n += 1
    return cand


def sellar(out_dir, descr: str, *, commit: str | None = None,
           ahora: datetime | None = None) -> Path:
    """Copia congelada del SET_ENTREGABLE a _entregas/<fecha>_<slug>/ + _SELLO.md (sha256)."""
    out = Path(out_dir)
    ahora = ahora or datetime.now()
    commit = commit if commit is not None else _git_commit()
    # _slug_descripcion ya saca un slug no vacío; "entrega" es red de seguridad. replace _→- para legibilidad del nombre de carpeta.
    slug = (_slug_descripcion(descr) or "entrega").replace("_", "-")
    dest = _destino_unico(out / "_entregas" / f"{ahora.strftime('%Y-%m-%d')}_{slug}")
    dest.mkdir(parents=True)
    for item in SET_ENTREGABLE:
        src = out / item
        if not src.exists():
            continue
        if src.is_dir():
            shutil.copytree(src, dest / item)
        else:
            shutil.copy2(src, dest / item)
    filas = []
    for p in sorted(dest.rglob("*")):
        if p.is_file() and p.name != "_SELLO.md":
            filas.append((p.relative_to(dest).as_posix(), compute_sha256_bytes(p.read_bytes())))
    sello = [
        "# SELLO DE ENTREGA — GENERADO por core.email_atomize. NO editar.\n",
        f"- descripcion: {descr}",
        f"- fecha: {ahora.isoformat(timespec='seconds')}",
        f"- commit_motor: {commit}",
        f"- n_ficheros: {len(filas)}\n",
        "| Fichero | sha256 |",
        "| --- | --- |",
    ]
    sello += [f"| {rel} | {h} |" for rel, h in filas]
    (dest / "_SELLO.md").write_text("\n".join(sello) + "\n", encoding="utf-8")
    return dest
