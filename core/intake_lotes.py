# core/intake_lotes.py
"""Lotes de entrega en ``00_Input`` (MEJORAS #54, spec 2026-07-17 rev 2).

Canales de ENTREGA (``whatsapp``, ``email``, ``manual``, ``entrevista``): cada
intake es su propia subcarpeta ``00_Input/<AAAA-MM-DD>_<fuente>_<NN>/`` con un
``_manifiesto.yaml`` (albarán forense de la entrega — NO fuente de dedup, eso
es M9). Canales ESPEJO (``01_Drive EV``, ``05_CRM``): cajón fijo, aquí no se
tocan.
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from . import config
from .config import caso_path

MANIFIESTO_LOTE = "_manifiesto.yaml"

PATRON_LOTE = re.compile(
    r"^(\d{4}-\d{2}-\d{2})_(whatsapp|email|manual|entrevista)_(\d{2,})$"
)


def _lotes_existentes(case_dir: Path) -> set[str]:
    """Nombres de lote presentes en 00_Input/ Y en la bandeja _pendiente_checkin.

    El contador mira también la bandeja (spec §4): un intake sobre caso
    prestado se desvía ahí con su nombre de lote.
    """
    raices = [case_dir / "00_Input"]
    bandeja = case_dir / config.PENDIENTE_CHECKIN_SUBDIR
    if bandeja.is_dir():
        raices += [d / "00_Input" for d in bandeja.iterdir() if d.is_dir()]
    nombres: set[str] = set()
    for raiz in raices:
        if not raiz.is_dir():
            continue
        nombres |= {p.name for p in raiz.iterdir()
                    if p.is_dir() and PATRON_LOTE.match(p.name)}
    return nombres


def reservar_lote(case_id: str, fuente: str, origen: str,
                  *, hoy: date | None = None) -> Path:
    """Reserva (mkdir atómico) y devuelve el directorio del siguiente lote.

    Aplica el guard §6 vía ``dir_intake``: caso prestado/conflicto → el lote
    nace en la bandeja. La reserva es atómica: si el mkdir colisiona (dos
    sesiones concurrentes sobre un caso *disponible*), se prueba ``NN+1``.
    """
    if fuente not in config.FUENTES_LOTE:
        raise ValueError(
            f"Fuente de lote inválida: {fuente!r}. Válidas: {config.FUENTES_LOTE}. "
            "Los espejos (drive_ev, crm) no forman lotes."
        )
    from .case_manager import dir_intake  # import local: evita ciclo config↔case_manager

    fecha = (hoy or date.today()).isoformat()
    ocupados = _lotes_existentes(caso_path(case_id))
    nn = 1
    while True:
        nombre = f"{fecha}_{fuente}_{nn:02d}"
        if nombre in ocupados:
            nn += 1
            continue
        destino = dir_intake(case_id, f"00_Input/{nombre}", origen)
        try:
            destino.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            nn += 1
            continue
        return destino
