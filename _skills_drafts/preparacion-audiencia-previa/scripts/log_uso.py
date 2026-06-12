# -*- coding: utf-8 -*-
"""Shim de compatibilidad: delega en el helper canónico ``registrar_uso.py``.

Antes esta skill tenía su propio logger; con la Parte II del plan v3 la
telemetría se unifica en ``_shared/registrar_uso.py`` (bundleado en este
``scripts/``), que escribe en el store central ``data/_skill_logs/<skill>/``.
Este módulo conserva la API antigua (``log`` / ``log_to``) para no romper
ninguna invocación previa, pero reenvía al helper común.
"""
from __future__ import annotations

import registrar_uso as _ru

SKILL = "preparacion-audiencia-previa"


def log(entry: dict, file: str = "uso.jsonl") -> None:
    """API antigua: recibe un dict de evento. Se mapea al esquema canónico."""
    ref = entry.get("ref", "")
    accion = entry.get("accion", "")
    archivos = entry.get("archivos")
    metricas = {k: v for k, v in entry.items() if k not in ("ref", "accion", "archivos")}
    _ru.log(SKILL, ref, accion, archivos=archivos, metricas=metricas)


def log_to(ref: str, fase: str, entry: dict) -> None:
    accion = entry.get("accion", "checklist")
    _ru.log(SKILL, ref, accion, fase=fase, metricas=entry)


if __name__ == "__main__":
    log({"accion": "smoke-test", "ref": "SMOKE"})
    print("ok")
