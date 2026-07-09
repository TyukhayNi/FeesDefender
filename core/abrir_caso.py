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


class ColisionCaso(Exception):
    """El W-code ya existe en la ciudad (mismo caso) y no se forzó --force."""


@dataclass(frozen=True)
class Identidad:
    codigo: str
    direccion: str
    w_code: str
    sufijo: str
    case_id: str
    posicion: str
    w_code_duplicado: bool
    codigo_duplicado: bool
    requiere_confirmacion: bool
    colisiones: tuple[str, ...]


def _codigo_de(nombre: str) -> str:
    return nombre.split(" - ", 1)[0].strip()


def _w_code_de(nombre: str) -> str | None:
    m = _W_CODE_EN_NOMBRE.search(nombre)
    return m.group(1) if m else None


def resolver_identidad(
    *,
    codigo: str,
    direccion: str,
    w_code: str,
    sufijo: str,
    tipo_caso: str,
    nombres_existentes: list[str],
    force: bool,
) -> Identidad:
    """Compone el case_id y evalúa la política de colisión (D2 `ask`).

    - w_code duplicado en la ciudad ⇒ ColisionCaso (salvo force).
    - codigo duplicado + w_code nuevo ⇒ requiere_confirmacion=True (el
      orquestador para y pregunta).
    """
    posicion = config.posicion_de_tipo(tipo_caso)  # ValueError si tipo desconocido
    case_id = componer_case_id(codigo=codigo, direccion=direccion, w_code=w_code, sufijo=sufijo)

    colisiones_w = [n for n in nombres_existentes if _w_code_de(n) == w_code]
    colisiones_cod = [n for n in nombres_existentes if _codigo_de(n) == codigo]

    w_dup = bool(colisiones_w)
    cod_dup = bool(colisiones_cod)

    if w_dup and not force:
        raise ColisionCaso(
            f"El W-code {w_code} ya existe en la ciudad: {colisiones_w}. "
            f"Usa --force para forzar."
        )

    requiere_confirmacion = cod_dup and not w_dup

    return Identidad(
        codigo=codigo, direccion=direccion, w_code=w_code, sufijo=sufijo,
        case_id=case_id, posicion=posicion,
        w_code_duplicado=w_dup, codigo_duplicado=cod_dup,
        requiere_confirmacion=requiere_confirmacion,
        colisiones=tuple(dict.fromkeys(colisiones_w + colisiones_cod)),
    )
