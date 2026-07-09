"""Cerebro puro de `abrir-caso` (alta + intake + CRM en una pasada).

Cero I/O de disco o red: naming, política de colisión, plan de intake,
reconciliación por hash y construcción del payload CRM. Los orquestadores
(CLI local, skill Cowork) le dan los datos ya leídos y ejecutan los efectos.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from core import config

FUENTE_A_SUBDIR = {
    "drive_ev": "01_Drive EV", "manual": "04_Manual",
    "whatsapp": "02_Whatsapp", "email": "03_Email", "entrevista": "06_Entrevistas",
}
FUENTE_A_EVENTO = {
    "drive_ev": "pull_drive_ev", "manual": "upload_manual",
    "whatsapp": "upload_whatsapp", "email": "upload_email", "entrevista": "upload_entrevista",
}

_W_CODE_EN_NOMBRE = re.compile(r"\((W-[A-Z0-9]+)\)")


def componer_case_id(*, codigo: str, direccion: str, w_code: str, sufijo: str) -> str:
    """Compone el case_id canónico: '<codigo> - <direccion> (<w_code>) - <sufijo>'.

    Formato validado por core.utils.validate_case_id (regex _CASE_ID_NEW):
    la dirección va pegada al paréntesis de la referencia, sin guion previo.
    """
    return f"{codigo} - {direccion} ({w_code}) - {sufijo}"
