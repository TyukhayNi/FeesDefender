"""Cerebro puro de `abrir-caso` (alta + intake + CRM en una pasada).

Cero I/O de disco o red: naming, política de colisión, plan de intake,
reconciliación por hash y construcción del payload CRM. Los orquestadores
(CLI local, skill Cowork) le dan los datos ya leídos y ejecutan los efectos.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from core import config
from core.utils import _CASE_ID_NEW_PARTES, exigir_sin_caracteres_de_ruta

SUBDIR_DRIVE_EV = "01_Drive EV"          # espejo: cajón fijo (spec §2)
FUENTES: tuple[str, ...] = ("drive_ev",) + config.FUENTES_LOTE
FUENTE_A_EVENTO = {
    "drive_ev": "pull_drive_ev", "manual": "upload_manual",
    "whatsapp": "upload_whatsapp", "email": "upload_email", "entrevista": "upload_entrevista",
}

# Ancla en la forma literal "(W-...)" para no confundir con un segmento de
# dirección entre paréntesis con pinta numérica, p.ej. "(08860)".
_W_CODE_EN_NOMBRE = re.compile(r"\((W-[A-Z0-9]+)\)")


def componer_case_id(*, codigo: str, direccion: str, w_code: str, sufijo: str) -> str:
    """Compone el case_id canónico: '<codigo> - <direccion> (<w_code>) - <sufijo>'.

    La dirección va pegada al paréntesis de la referencia, sin guion previo.

    **Y lo valida, que es lo que faltaba (`MEJORAS #148`).** Este docstring afirmaba
    «formato validado por core.utils.validate_case_id» y esa validación no ocurría en
    esta vía: los únicos llamadores de la guarda eran `core/anon/api.py` y
    `scripts/init_caso.py`, nunca el sitio que COMPONE el `case_id` a partir de lo que
    teclea el usuario. Medido el 2026-09-04 abriendo W-02JSVZ: con «s/n» en la dirección
    —grafía normal en finca rústica— el `/` actuó como separador de rutas, el alta creó
    **dos** carpetas anidadas con los 170 ficheros del pull dentro, imprimió
    `OK Caso abierto: …` y salió con código **0**. El `case_id` que imprimía no nombraba
    a ninguna carpeta, y el fallo no se veía hasta el comando siguiente, donde
    `resolve_ref` no puede reconstruir un caso partido en dos.

    Se valida **aquí** y no en cada llamador porque este es el punto único por el que
    pasan todas las vías de `abrir_caso`; y se validan los **tres** campos que se
    concatenan, no solo la dirección, porque los tres acaban siendo una ruta y el error
    tiene que nombrar al culpable.

    Lo que se exige es la **gramática de rutas**, no el formato canónico del `case_id`.
    La primera versión llamaba a `validate_case_id` entero y eso rompió cinco fixtures
    con códigos sintéticos (`BaTEST`, sin dígitos): una guarda más ancha que el defecto
    medido. El formato canónico se sigue comprobando donde toca, no aquí.
    """
    for campo, valor in (("--codigo-caso", codigo), ("--direccion", direccion),
                         ("--sufijo", sufijo)):
        exigir_sin_caracteres_de_ruta(valor, campo=campo)
    return f"{codigo} - {direccion} ({w_code}) - {sufijo}"


def descomponer_case_id(case_id: str) -> tuple[str, str, str, str]:
    """Inverso de ``componer_case_id``: (codigo, direccion, w_code, sufijo).

    Se apoya en la gramática canónica ``core.utils._CASE_ID_NEW_PARTES``, que
    acepta AMBAS referencias: ``(W-...)`` y ``(SIN REFERENCIA)`` (categoría
    OTROS — ver ``MEJORAS_FUTURAS.md §12``). La referencia se localiza por su
    forma literal entre paréntesis (no cualquier paréntesis), así una
    dirección con ``(08860)`` o con ` - ` interno se reconstruye bien.
    Lanza ``ValueError`` si el nombre no sigue esta gramática canónica.
    """
    m = _CASE_ID_NEW_PARTES.match(case_id.strip())
    if not m:
        raise ValueError(f"case_id no canónico: {case_id!r}")
    ref = m.group("ref")
    ref_inner = ref[1:-1]
    return m.group("prefijo"), m.group("direccion").strip(), ref_inner, m.group("categoria")


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


def plan_intake(inventario: list[dict], log_existente: list[dict], fuente: str,
                *, lote: str | None = None) -> PlanIntake:
    """Construye el plan de depósito (puro). Sin tocar bytes.

    inventario: [{"relpath": posix, "sha256": str|None, "size": int}, ...].
    ``drive_ev`` (espejo) deposita siempre en el cajón fijo SUBDIR_DRIVE_EV;
    las fuentes de entrega (config.FUENTES_LOTE) requieren ``lote=`` — cada
    entrega es su propia subcarpeta ``00_Input/<AAAA-MM-DD>_<fuente>_<NN>/``.
    """
    if fuente not in FUENTES:
        raise ValueError(f"Fuente desconocida: {fuente!r}. Válidas: {sorted(FUENTES)}")
    if fuente == "drive_ev":
        base = SUBDIR_DRIVE_EV
    else:
        if not lote:
            raise ValueError(f"La fuente de entrega {fuente!r} requiere lote=")
        base = lote
    evento = FUENTE_A_EVENTO[fuente]
    shas_previos = _shas_en_log(log_existente)

    items: list[ItemIntake] = []
    for entry in inventario:
        rel = entry["relpath"]
        sha = entry.get("sha256")
        size = int(entry.get("size", 0))
        items.append(ItemIntake(
            relpath=rel,
            dst=f"{base}/{rel}",
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
    faltantes/mismatches se comparan solo contra los depositables del plan;
    extras se comparan contra depositables ∪ dups (ver `esperados_en_disco`).
    """
    depositables = {i.dst: i.sha256 for i in plan.depositables}
    # ficheros que DEBEN estar en disco = TODOS los items del plan (depositables +
    # dups + 0-byte): en el front local el inventario en disco incluye los 0-byte,
    # así que un 0-byte presente NO es un extra (§9 "skip, don't abort" — los
    # 0-byte simplemente no se loguean, no se tratan como sobrantes). Un dup
    # presente en disco tampoco es un extra (reentrancia §8).
    esperados_en_disco = {i.dst for i in plan.items}
    faltantes = tuple(sorted(d for d in depositables if d not in hashes_destino))
    mismatches = tuple(sorted(
        d for d, s in depositables.items()
        if d in hashes_destino and s is not None and hashes_destino[d] != s
    ))
    extras = tuple(sorted(d for d in hashes_destino if d not in esperados_en_disco))
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

    tags: list[str] = []
    rojo = sc.tag_rojo_equipo(identidad.codigo)
    azul = sc.tag_azul_de_codigo(identidad.codigo)
    if rojo:
        tags.append(rojo)
    if azul:
        tags.append(azul)
    tags += sc.tag_defaults_for_tipo_caso(identidad.tipo_caso)

    return sc.NuevoExpedienteExtrajudicial(
        referencia_cliente=identidad.case_id,
        cuantia=cuantia,
        tags=tags,
        posicion=posicion_crm,
    )
