"""Cerebro de la ficha CRM completa (B1): modelo de entrada + carga del YAML.

Determinista, sin red: parsea ``00_Input/_ficha_crm.yaml`` a un ``FichaCRMInput``
con los DTOs de ``sudespacho_relations`` (que normalizan el teléfono, B3). El
orquestador (``scripts/crm_ficha.py``) ejecuta los efectos contra el CRM.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from core.sudespacho_relations import NuevoClienteContrario, NuevoColaborador

CLIENTE_PROPIO_DEFAULT = "EV_MMC_SPAIN"


@dataclass
class FichaCRMInput:
    contrario: NuevoClienteContrario | None = None
    colaboradores: list[NuevoColaborador] = field(default_factory=list)
    notas_html: str = ""
    cliente_propio: str = CLIENTE_PROPIO_DEFAULT


def _contrario_de(d: dict) -> NuevoClienteContrario:
    if not d.get("nombre"):
        raise ValueError("contrario sin 'nombre' en _ficha_crm.yaml")
    return NuevoClienteContrario(
        nombre=d.get("nombre", ""),
        apellido1=d.get("apellido1", ""),
        apellido2=d.get("apellido2", ""),
        email=d.get("email", ""),
        movil=str(d.get("movil", "")),
        nif=d.get("nif", ""),
        direccion=d.get("direccion", ""),
        poblacion=d.get("poblacion", ""),
        # Estos tres no se leian del YAML, y por eso nunca llegaban al CRM aunque
        # estuvieran escritos.
        cp=_escalar(d.get("cp"), "contrario.cp"),
        provincia=_escalar(d.get("provincia"), "contrario.provincia"),
        telefono=_escalar(d.get("telefono"), "contrario.telefono"),
    )


def _escalar(valor: object, campo: str) -> str:
    """Un escalar del YAML como cadena, sin corromperlo ni inventarlo.

    Dos defectos que R1 midio y que `str(...)` producia por si solo:

    - **H-08, el codigo postal en octal.** `cp: 01001` sin comillas lo resuelve PyYAML
      como el **entero octal 513**, y `str()` lo manda al CRM como `"513"`. El caso
      concreto de `08019` se salvaba solo porque tiene un `8` y un `9`, que no son
      digitos octales validos — o sea, por suerte. Un `int` en un campo que es una
      cadena con ceros a la izquierda **no se puede recuperar**: se rechaza y se dice.
    - **H-09, el nulo que viaja como texto.** `cp:` sin valor da `None`, y `str(None)`
      es `"None"`, que es *truthy* y viajaba al CRM tal cual. Una clave preparada y
      vacia significa «no hay dato».
    """
    if valor is None:
        return ""
    if isinstance(valor, bool) or isinstance(valor, int) or isinstance(valor, float):
        raise ValueError(
            f"{campo} vino del YAML como {type(valor).__name__} ({valor!r}). Un valor "
            "con ceros a la izquierda lo reinterpreta YAML (por ejemplo `01001` es el "
            "octal 513) y el dato original ya no se puede recuperar. Escribelo entre "
            "comillas: por ejemplo `cp: \'01001\'`."
        )
    return str(valor).strip()


def _colaborador_de(d: dict) -> NuevoColaborador:
    if not d.get("nombre"):
        raise ValueError("colaborador sin 'nombre' en _ficha_crm.yaml")
    return NuevoColaborador(
        nombre=d.get("nombre", ""),
        email=d.get("email", ""),
        movil=str(d.get("movil", "")),
        telefono=str(d.get("telefono", "")),
        nif=d.get("nif", ""),
    )


def cargar_ficha_yaml(path: Path) -> FichaCRMInput:
    """Carga ``_ficha_crm.yaml`` → ``FichaCRMInput``.

    Lanza ``FileNotFoundError`` si no existe y ``ValueError`` si el YAML no es un
    mapping o un contrario/colaborador no tiene ``nombre``.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"No existe _ficha_crm.yaml: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"_ficha_crm.yaml inválido: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("_ficha_crm.yaml debe ser un mapping YAML")

    contrario_raw = data.get("contrario")
    contrario = _contrario_de(contrario_raw) if isinstance(contrario_raw, dict) else None
    colaboradores = [
        _colaborador_de(c) for c in (data.get("colaboradores") or []) if isinstance(c, dict)
    ]
    return FichaCRMInput(
        contrario=contrario,
        colaboradores=colaboradores,
        notas_html=str(data.get("notas_html", "")),
        cliente_propio=str(data.get("cliente_propio") or CLIENTE_PROPIO_DEFAULT),
    )
