"""Orquestador del intake judicial automático (demanda + contestación).

Fase 1→2 de ``[SIGUIENTE-INTAKE-JUDICIAL-AUTO]`` (PLAN.md). Dado un caso y el
ID de su expediente judicial en el CRM:

1. Lista los documentos del Gestor Documental (``list_gdocu_docs_rest``).
2. Clasifica cuál es la demanda y cuál la contestación
   (:mod:`core.judicial_classifier`, heurística source-locked).
3. Descarga y deposita **solo** esos dos documentos en el árbol
   ``00_Input/05_CRM/<rama>/`` reutilizando :func:`pull_expediente_v2`
   (dedup M9 + log M10 + routing ``crm_branch_path`` + estado D8). No toca el
   resto del expediente.
4. Marca ``pendiente_revision`` los roles no resueltos limpiamente (0 / varios
   candidatos), sin adivinar.

El encadenado con el pipeline (anon → MD → frontier) lo hace el caller (CLI /
UI), igual que el comando ``pull --run-pipeline``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .case_manager import is_legacy_intake_v1
from .intake_log import append_event as _log_event
from .judicial_classifier import ClassificationResult, RoleResult, classify
from .sync_sudespacho import (
    PullResultV2,
    SudespachoClient,
    SudespachoError,
    pull_expediente_v2,
)


@dataclass
class IntakeJudicialResult:
    case_id: str
    expediente_id: str
    element: str
    blocked_legacy_v1: bool = False
    classification: ClassificationResult | None = None
    demanda_doc_id: str | None = None
    contestacion_doc_id: str | None = None
    pendientes: list[str] = field(default_factory=list)   # roles para revisión
    pull: PullResultV2 | None = None
    errors: list[str] = field(default_factory=list)


def _role_detail(rr: RoleResult) -> dict:
    return {
        "role": rr.role,
        "status": rr.status,
        "reason": rr.reason,
        "selected_doc_id": rr.selected.doc_id if rr.selected else None,
        "candidates": [
            {"doc_id": c.doc_id, "filename": c.filename,
             "id_carpeta_label": c.id_carpeta_label}
            for c in rr.candidates
        ],
    }


def intake_demanda_contestacion(
    case_id: str,
    expediente_id: str,
    *,
    element: str = "expedientes_judiciales",
    client: SudespachoClient | None = None,
    actor: str | None = None,
    llm_fn=None,
) -> IntakeJudicialResult:
    """Localiza, clasifica y deposita demanda + contestación del expediente.

    Args:
        case_id: ID del caso (no debe ser legacy v1).
        expediente_id: ID del expediente judicial en el CRM.
        element: tipo de expediente (default ``expedientes_judiciales``).
        client: ``SudespachoClient`` pre-construido; si None se crea desde
            ``.env`` y se cierra al terminar.
        actor: override del actor para los eventos M10.
        llm_fn: hook de desempate para el clasificador. Default None
            (heurística pura; la ambigüedad va a revisión del letrado).

    Returns:
        :class:`IntakeJudicialResult`.
    """
    result = IntakeJudicialResult(
        case_id=case_id, expediente_id=str(expediente_id), element=element,
    )

    # 1. Bloqueo de casos legacy v1 (D9) — mismo criterio que pull_expediente_v2.
    if is_legacy_intake_v1(case_id):
        result.blocked_legacy_v1 = True
        result.errors.append(
            "Caso con estructura v1 (sudespacho_*/) — intake v2 bloqueado. "
            "Migración manual: borrar las carpetas sudespacho_*/ y reintentar."
        )
        return result

    # 2. Cliente REST.
    api_client = client
    owns_client = False
    if api_client is None:
        try:
            api_client = SudespachoClient()
            owns_client = True
        except SudespachoError as exc:
            result.errors.append(f"No se pudo construir SudespachoClient: {exc}")
            return result

    try:
        # 3. Listado de documentos del expediente.
        try:
            docs = api_client.list_gdocu_docs_rest(
                str(expediente_id), element=element,
            )
        except SudespachoError as exc:
            result.errors.append(f"list_gdocu_docs_rest: {exc}")
            return result

        if not docs:
            result.errors.append(
                f"El Gestor Documental del expediente {expediente_id} está vacío "
                f"(o el elemento '{element}' no es el correcto)."
            )

        # 4. Clasificación demanda / contestación.
        clasif = classify(docs, llm_fn=llm_fn)
        result.classification = clasif
        if clasif.demanda.selected:
            result.demanda_doc_id = clasif.demanda.selected.doc_id
        if clasif.contestacion.selected:
            result.contestacion_doc_id = clasif.contestacion.selected.doc_id

        # 5. Marcar roles no resueltos → revisión letrado.
        for rr in (clasif.demanda, clasif.contestacion):
            if rr.status != "ok":
                result.pendientes.append(rr.role)
                _log_event(
                    case_id, "pendiente_revision",
                    actor=actor,
                    details={"expediente_id": str(expediente_id), **_role_detail(rr)},
                )

        # 6. Descargar+depositar solo demanda+contestación resueltas.
        selected = {
            d for d in (result.demanda_doc_id, result.contestacion_doc_id) if d
        }
        if selected:
            try:
                result.pull = pull_expediente_v2(
                    case_id, str(expediente_id),
                    element=element,
                    client=api_client,
                    actor=actor,
                    only_doc_ids=selected,
                )
                result.errors.extend(result.pull.errors)
            except SudespachoError as exc:
                result.errors.append(f"pull demanda+contestación: {exc}")

        # 7. Evento resumen del intake judicial (M10).
        _log_event(
            case_id, "intake_judicial",
            actor=actor,
            details={
                "expediente_id": str(expediente_id),
                "element": element,
                "demanda_doc_id": result.demanda_doc_id,
                "contestacion_doc_id": result.contestacion_doc_id,
                "pendientes": result.pendientes,
                "documents_written": result.pull.documents_written if result.pull else 0,
                "documents_skipped_dedup": (
                    result.pull.documents_skipped_dedup if result.pull else 0
                ),
                "errors_count": len(result.errors),
            },
        )

        return result
    finally:
        if owns_client and api_client is not None:
            api_client.__exit__(None, None, None)
