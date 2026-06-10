"""Clasificador demanda/contestación sobre documentos del Gestor Documental.

Fase 1 del intake judicial automático. Toma la salida de
``SudespachoClient.list_gdocu_docs_rest`` (lista de ``GdocuDocInfo``) y marca
qué documento es la **demanda** y cuál la **contestación** del expediente.

Principios (source-locked, ver PLAN.md `[SIGUIENTE-INTAKE-JUDICIAL-AUTO]`):

- La clasificación se ancla al ``filename`` REAL del CRM. No se inventan
  tipologías ni se infiere del contenido. El ``id_carpeta_label`` se conserva
  para mostrarlo en la revisión pero **no** dispara la clasificación: las
  carpetas "DEMANDA"/"OPOSICION" del CRM contienen toda la prueba del
  expediente, no solo la pieza procesal (confirmado contra el exp. 649).
- Heurística por expresiones regulares como única capa de decisión. Existe un
  hook ``llm_fn`` inyectable para desempatar ambigüedades, pero el camino por
  defecto es 100 % heurístico (decisión del despacho: ningún nombre de fichero
  —que puede contener PII— sale a un proveedor externo; ver ``llm_local``).
- Casos límite —0 coincidencias, múltiples candidatos distintos, documento
  escaneado sin nombre útil— se marcan ``[PENDIENTE revisión letrado]``
  (``status="none"`` / ``"ambiguous"``), nunca se adivina.

Robustez ante duplicados: un mismo documento subido en ``.pdf`` y ``.docx``
(mismo nombre base) colapsa a un único candidato, prefiriendo el ``.pdf`` (la
versión presentada). Solo cuando quedan candidatos con nombres realmente
distintos se considera ambiguo.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

ROLE_DEMANDA = "demanda"
ROLE_CONTESTACION = "contestacion"


# ---------------------------------------------------------------------------
# Normalización
# ---------------------------------------------------------------------------

def _norm(s: str | None) -> str:
    """Normaliza para matching: sin acentos, minúsculas, separadores → espacio.

    ``"OPOSICION_DEMANDA-ART.20"`` → ``"oposicion demanda art 20"``. Permite
    casar tokens sin sensibilidad a mayúsculas, acentos ni separadores
    (``_``, ``-``, ``.``).
    """
    if not s:
        return ""
    nfkd = unicodedata.normalize("NFKD", s)
    ascii_s = nfkd.encode("ascii", "ignore").decode("ascii").lower()
    ascii_s = re.sub(r"[_\-.]+", " ", ascii_s)
    return re.sub(r"\s+", " ", ascii_s).strip()


# Marcadores que indican que el documento NO es la pieza procesal en sí, sino
# una diligencia, notificación, justificante, etc. Cualquiera de estos veta la
# clasificación (anclado a la nomenclatura real del CRM tnm).
_NEG_COMUN: tuple[str, ...] = (
    "dior",            # diligencia de ordenación
    "notificac",       # notificación
    "cedula",          # cédula de emplazamiento
    "emplazamiento",
    "justif", "justificante", "just escr",  # justificante de presentación procurador
    "ptacion", "presentacion",
    "apersonad", "personacion",
    "diligencia", "providencia", "decreto",
    "factura", "minuta", "fra ",
)

# Marcadores POSITIVOS de demanda: la palabra "demanda" o el nombre del tipo de
# procedimiento (la demanda suele titularse por el juicio: "ORDINARIO ...",
# "VERBAL ...", petición inicial de "MONITORIO ..."). Confirmado contra el
# expediente 444, donde la demanda es "ORDINARIO - VUELTA VENDEDOR - VALLDAURA".
_DEMANDA_POS: tuple[str, ...] = ("demanda", "ordinario", "verbal", "monitorio")

# Tokens que, presentes en el nombre, descartan que sea la DEMANDA
# (es la contestación/oposición/reconvención, un escrito de alegaciones, etc.).
_NEG_DEMANDA: tuple[str, ...] = _NEG_COMUN + (
    "oposicion", "contestacion", "contestada", "contesta dda", "contesta demanda",
    "alegacion", "ampliacion", "reconvencion",
)


def _is_demanda(norm: str) -> bool:
    if not any(pos in norm for pos in _DEMANDA_POS):
        return False
    return not any(neg in norm for neg in _NEG_DEMANDA)


def _is_contestacion(norm: str) -> bool:
    if any(neg in norm for neg in _NEG_COMUN):
        return False
    if "contestacion" in norm:
        return True
    if "oposicion" in norm and ("demanda" in norm or "monitorio" in norm):
        return True
    return False


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------

@dataclass
class DocCandidate:
    doc_id: str
    filename: str
    id_carpeta_label: str | None
    ext: str
    role: str


@dataclass
class RoleResult:
    role: str
    selected: DocCandidate | None
    status: str                         # "ok" | "none" | "ambiguous"
    candidates: list[DocCandidate] = field(default_factory=list)
    reason: str = ""


@dataclass
class ClassificationResult:
    demanda: RoleResult
    contestacion: RoleResult

    @property
    def pendientes(self) -> list[RoleResult]:
        """Roles que requieren revisión del letrado (no resueltos limpiamente)."""
        return [r for r in (self.demanda, self.contestacion) if r.status != "ok"]


# ---------------------------------------------------------------------------
# Colapso de duplicados + resolución por rol
# ---------------------------------------------------------------------------

def _ext_rank(ext: str) -> int:
    """Preferencia de formato: .pdf (presentado) < .docx/.doc < resto."""
    e = ext.lower()
    if e == ".pdf":
        return 0
    if e in (".docx", ".doc"):
        return 1
    return 2


def _int_or_zero(s: str) -> int:
    try:
        return int(s)
    except (ValueError, TypeError):
        return 0


def _collapse(cands: list[DocCandidate]) -> list[DocCandidate]:
    """Colapsa candidatos con el mismo nombre base (sin extensión).

    Dentro de cada grupo se prefiere el .pdf y, a igualdad de formato, el
    doc_id mayor (más reciente). Devuelve un representante por nombre base.
    """
    groups: dict[str, list[DocCandidate]] = {}
    for c in cands:
        key = _norm(Path(c.filename).stem)
        groups.setdefault(key, []).append(c)
    out: list[DocCandidate] = []
    for group in groups.values():
        group.sort(key=lambda c: (_ext_rank(c.ext), -_int_or_zero(c.doc_id)))
        out.append(group[0])
    return out


def _resolve_role(
    role: str,
    raw: list[DocCandidate],
    llm_fn: Callable[[str, list[DocCandidate]], str | None] | None,
) -> RoleResult:
    if not raw:
        return RoleResult(role, None, "none", [], "sin candidatos por nombre")
    collapsed = _collapse(raw)
    if len(collapsed) == 1:
        return RoleResult(role, collapsed[0], "ok", collapsed, "candidato único")
    # Múltiples candidatos distintos → desempate opcional por LLM.
    if llm_fn is not None:
        pick = llm_fn(role, collapsed)
        chosen = next((c for c in collapsed if c.doc_id == pick), None)
        if chosen is not None:
            return RoleResult(role, chosen, "ok", collapsed, "desempate LLM")
    return RoleResult(
        role, None, "ambiguous", collapsed,
        f"{len(collapsed)} candidatos distintos — revisión letrado",
    )


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def classify(
    docs: list[Any],
    *,
    llm_fn: Callable[[str, list[DocCandidate]], str | None] | None = None,
) -> ClassificationResult:
    """Clasifica la lista de documentos del CRM en demanda y contestación.

    Args:
        docs: lista de ``GdocuDocInfo`` (o cualquier objeto con ``doc_id``,
            ``filename``, ``id_carpeta_label``).
        llm_fn: callback opcional de desempate ``(role, candidates) -> doc_id``.
            Si es ``None`` (default), la ambigüedad se marca para revisión del
            letrado sin adivinar.

    Returns:
        ``ClassificationResult`` con un ``RoleResult`` por rol.
    """
    dem: list[DocCandidate] = []
    con: list[DocCandidate] = []

    for d in docs:
        filename = getattr(d, "filename", "") or ""
        label = getattr(d, "id_carpeta_label", None)
        norm_name = _norm(Path(filename).stem)
        ext = Path(filename).suffix.lower()

        # El disparador es SOLO el nombre de fichero. El ``id_carpeta_label``
        # NO se usa como disparador: en el CRM real, las carpetas "DEMANDA" y
        # "OPOSICION" contienen TODA la prueba del expediente (D01-D16, etc.),
        # no solo la pieza procesal — usarlo dispararía decenas de falsos
        # positivos (confirmado contra el expediente 649, 2026-06-10). Se
        # conserva en el candidato solo para mostrarlo en la revisión.
        if _is_demanda(norm_name):
            dem.append(DocCandidate(
                doc_id=str(getattr(d, "doc_id", "")),
                filename=filename, id_carpeta_label=label, ext=ext,
                role=ROLE_DEMANDA,
            ))
        if _is_contestacion(norm_name):
            con.append(DocCandidate(
                doc_id=str(getattr(d, "doc_id", "")),
                filename=filename, id_carpeta_label=label, ext=ext,
                role=ROLE_CONTESTACION,
            ))

    return ClassificationResult(
        demanda=_resolve_role(ROLE_DEMANDA, dem, llm_fn),
        contestacion=_resolve_role(ROLE_CONTESTACION, con, llm_fn),
    )
