"""Cerebro puro de `abrir-caso` (alta + intake + CRM en una pasada).

Cero I/O de disco o red: naming, política de colisión, plan de intake,
reconciliación por hash y construcción del payload CRM. Los orquestadores
(CLI local, skill Cowork) le dan los datos ya leídos y ejecutan los efectos.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from core import config

FUENTE_A_SUBDIR = {
    "drive_ev": "01_Drive EV", "manual": "04_Manual",
    "whatsapp": "02_Whatsapp", "email": "03_Email", "entrevista": "06_Entrevistas",
}
FUENTE_A_EVENTO = {
    "drive_ev": "pull_drive_ev", "manual": "upload_manual",
    "whatsapp": "upload_whatsapp", "email": "upload_email", "entrevista": "upload_entrevista",
}

# Ancla en la forma literal "(W-...)" para no confundir con un segmento de
# dirección entre paréntesis con pinta numérica, p.ej. "(08860)".
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
    tipo_caso: str
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
        case_id=case_id, posicion=posicion, tipo_caso=tipo_caso,
        w_code_duplicado=w_dup, codigo_duplicado=cod_dup,
        requiere_confirmacion=requiere_confirmacion,
        colisiones=tuple(dict.fromkeys(colisiones_w + colisiones_cod)),
    )


@dataclass(frozen=True)
class ItemIntake:
    relpath: str
    dst: str
    evento: str
    sha256: str | None
    size: int
    dup: bool
    zero: bool


@dataclass(frozen=True)
class PlanIntake:
    items: tuple[ItemIntake, ...]
    fuente: str

    @property
    def depositables(self) -> tuple[ItemIntake, ...]:
        return tuple(i for i in self.items if not i.dup and not i.zero)

    @property
    def con_sha(self) -> list[dict]:
        return [{"path": i.dst, "sha256": i.sha256} for i in self.depositables]

    @property
    def categorias(self) -> tuple[str, ...]:
        out: list[str] = []
        for i in self.depositables:
            partes = i.dst.split("/")
            base = partes[0]
            if base not in out:
                out.append(base)
        return tuple(out)


def _shas_en_log(log_existente: list[dict]) -> set[str]:
    shas: set[str] = set()
    for ev in log_existente:
        for f in (ev.get("details") or {}).get("files") or []:
            s = f.get("sha256")
            if s:
                shas.add(s)
    return shas


def plan_intake(inventario: list[dict], log_existente: list[dict], fuente: str) -> PlanIntake:
    """Construye el plan de depósito (puro). Sin tocar bytes.

    inventario: [{"relpath": posix, "sha256": str|None, "size": int}, ...].
    """
    if fuente not in FUENTE_A_SUBDIR:
        raise ValueError(f"Fuente desconocida: {fuente!r}. Válidas: {sorted(FUENTE_A_SUBDIR)}")
    subdir = FUENTE_A_SUBDIR[fuente]
    evento = FUENTE_A_EVENTO[fuente]
    shas_previos = _shas_en_log(log_existente)

    items: list[ItemIntake] = []
    for entry in inventario:
        rel = entry["relpath"]
        sha = entry.get("sha256")
        size = int(entry.get("size", 0))
        items.append(ItemIntake(
            relpath=rel,
            dst=f"{subdir}/{rel}",
            evento=evento,
            sha256=sha,
            size=size,
            dup=bool(sha) and sha in shas_previos,
            zero=size == 0,
        ))
    return PlanIntake(items=tuple(items), fuente=fuente)


@dataclass(frozen=True)
class Reconciliacion:
    ok: bool
    faltantes: tuple[str, ...]
    mismatches: tuple[str, ...]
    extras: tuple[str, ...]


def reconcile(plan: PlanIntake, hashes_destino: dict[str, str]) -> Reconciliacion:
    """Verifica el depósito contra el plan (puro).

    hashes_destino: {relpath_desde_00_Input: sha256} de lo realmente en disco.
    Compara solo los depositables del plan.
    """
    esperados = {i.dst: i.sha256 for i in plan.depositables}
    faltantes = tuple(sorted(d for d in esperados if d not in hashes_destino))
    mismatches = tuple(sorted(
        d for d, s in esperados.items()
        if d in hashes_destino and s is not None and hashes_destino[d] != s
    ))
    extras = tuple(sorted(d for d in hashes_destino if d not in esperados))
    ok = not (faltantes or mismatches or extras)
    return Reconciliacion(ok=ok, faltantes=faltantes, mismatches=mismatches, extras=extras)


def crm_payload(identidad: Identidad, *, cuantia: float = 0.0):
    """Construye el DTO NuevoExpedienteExtrajudicial para sudespacho.

    Import local de sudespacho_create para no arrastrar sus deps de red al
    importar el cerebro.
    """
    from core import sudespacho_create as sc

    posicion_crm = {
        config.POSICION_ACTORA: sc.POSICION_ACTOR,
        config.POSICION_DEFENSIVA: sc.POSICION_DEMANDADO,
        config.POSICION_OTROS: sc.POSICION_ACTOR,
    }[identidad.posicion]

    return sc.NuevoExpedienteExtrajudicial(
        referencia_cliente=identidad.case_id,
        cuantia=cuantia,
        tags=sc.tag_defaults_for_tipo_caso(identidad.tipo_caso),
        posicion=posicion_crm,
    )
