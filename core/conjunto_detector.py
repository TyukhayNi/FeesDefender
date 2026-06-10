"""Detector de conjunto (D9): reagrupa cabecera + prueba subidas en lote al CRM.

Problema. La prueba documental de un asunto se sube al Gestor Documental del
CRM en lote (un mismo ``fechamodificacion``) y numerada con la convención del
despacho ``D NN -`` (la actora; el demandado NO numera así — confirmado contra
el expediente 444). A veces alguna pieza queda mal archivada en una carpeta
distinta de la de su cabecera, rompiendo la unidad probatoria.

Estrategia (pura, sin tocar el CRM remoto):

1. **Clúster** por ``modified_at`` idéntico (subida en lote).
2. **∩ patrón** ``D\\s*\\d+\\s*-`` (admite sub-índice ``D 22-C``): un clúster es
   candidato a lote si contiene ≥1 pieza con ese marcador.
3. **Ancla a la cabecera**: la cabecera es el doc del lote SIN marcador de
   prueba (el *odd-one-out*). En el 444 la cabecera es
   ``ORDINARIO - VUELTA VENDEDOR - VALLDAURA.doc`` — NO se llama "DEMANDA", así
   que el keyword procesal es solo desempate secundario, no el detector primario.
4. **Bucket** = el de la cabecera (vía ``case_manager.resolve_bucket``). Sin
   cabecera pero con bucket unánime entre los miembros → ese bucket.
5. **Baja confianza → pendiente_revision, sin adivinar**: cabecera no resoluble
   y miembros repartidos en buckets distintos.

Persistencia. En esta tanda el detector SOLO **emite propuestas** (eventos
``conjunto_detectado`` / ``pendiente_revision``). La persistencia de la relación
cabecera↔anexo como ``parent_id``/``orden_en_bundle`` se difiere a
``[SIGUIENTE-CATALOGO-DOCUMENTAL]`` (``indice_documental.yaml`` aún no existe;
MEJORAS_FUTURAS #29).
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable

from core.case_manager import resolve_bucket
from core.sync_sudespacho import GdocuDocInfo

# Numeración de prueba del despacho: "D 02 -", "D17 -", "D 08-A -", "D 11-".
# \bD seguido (con espacio opcional) de dígitos, sub-índice opcional (letra)
# y un guion separador. re.IGNORECASE por robustez OCR.
_EVIDENCE_FULL_RE = re.compile(r"\bD\s*\d+[\s\w]*-", re.IGNORECASE)

# Keywords de cabecera procesal — desempate SECUNDARIO cuando hay >1 doc sin
# marcador de prueba en el lote. No es el detector primario (la cabecera real
# del 444 no contiene ninguno de estos términos).
_HEADER_KEYWORDS = (
    "demanda", "contestacion", "contestación", "ordinario", "monitorio",
    "reconvencion", "reconvención", "solicitud", "peticion inicial",
    "petición inicial", "oposicion", "oposición",
)

# Tipo del resolver carpeta→bucket: (id_carpeta, id_carpeta_label) -> (bucket, kind)
BucketResolver = Callable[..., "tuple[str | None, str]"]


@dataclass(frozen=True)
class BundleProposal:
    """Propuesta de lote cabecera+prueba detectado por D9.

    Atributos:
        timestamp:        ``modified_at`` compartido del lote.
        header_doc_id:    doc_id de la cabecera, o None si no se identificó.
        bucket:           bucket destino propuesto (anclado a la cabecera o por
                          consenso unánime), o None si indeterminable.
        member_doc_ids:   todos los doc_id del lote.
        evidence_doc_ids: los que casan el patrón de prueba ``D NN``.
        misfiled_doc_ids: miembros cuya carpeta resuelve a un bucket distinto
                          del propuesto (prueba mal archivada).
        confidence:       ``"alta"`` | ``"baja"``. Baja → pendiente_revision.
        reason:           explicación legible de la decisión.
    """
    timestamp: str
    header_doc_id: str | None
    bucket: str | None
    member_doc_ids: tuple[str, ...]
    evidence_doc_ids: tuple[str, ...]
    misfiled_doc_ids: tuple[str, ...]
    confidence: str
    reason: str


def is_evidence_marker(filename: str) -> bool:
    """True si el nombre lleva la numeración de prueba del despacho ``D NN -``.

    Acepta sub-índices (``D 08-A``, ``D 22-C``), ausencia de espacio tras la D
    (``D17``) o antes del guion (``D 11-``). Exige un guion separador para no
    confundir con palabras que empiezan por D + dígito espurio.
    """
    if not filename:
        return False
    return _EVIDENCE_FULL_RE.search(filename) is not None


def _looks_like_header(filename: str) -> bool:
    low = filename.lower()
    return any(kw in low for kw in _HEADER_KEYWORDS)


def detect_bundles(
    docs: list[GdocuDocInfo],
    *,
    resolver: BucketResolver = resolve_bucket,
    min_size: int = 2,
) -> list[BundleProposal]:
    """Detecta lotes cabecera+prueba en una lista de documentos del CRM.

    Args:
        docs: documentos del expediente (con ``modified_at`` poblado — D10).
        resolver: función carpeta→bucket; default ``case_manager.resolve_bucket``.
        min_size: tamaño mínimo de clúster para considerarlo lote.

    Returns:
        Lista de ``BundleProposal``, ordenada por timestamp.
    """
    # 1. Clúster por timestamp idéntico (ignorando docs sin fecha).
    clusters: dict[str, list[GdocuDocInfo]] = defaultdict(list)
    for d in docs:
        if d.modified_at:
            clusters[d.modified_at].append(d)

    proposals: list[BundleProposal] = []
    for ts in sorted(clusters):
        members = clusters[ts]
        if len(members) < min_size:
            continue

        evidence = [d for d in members if is_evidence_marker(d.filename)]
        if not evidence:                       # 2. ∩ patrón D NN
            continue
        non_evidence = [d for d in members if d not in evidence]

        # 3. Cabecera = odd-one-out sin marcador; desempate por keyword.
        header: GdocuDocInfo | None = None
        if len(non_evidence) == 1:
            header = non_evidence[0]
        elif len(non_evidence) > 1:
            kw = [d for d in non_evidence if _looks_like_header(d.filename)]
            if len(kw) == 1:
                header = kw[0]

        # 4. Bucket: de la cabecera, o consenso unánime de los miembros.
        member_buckets = {resolver(d.id_carpeta, d.id_carpeta_label)[0] for d in members}
        known = {b for b in member_buckets if b is not None}

        bucket: str | None = None
        anchored = False
        if header is not None:
            bucket = resolver(header.id_carpeta, header.id_carpeta_label)[0]
            anchored = bucket is not None
        if bucket is None and len(known) == 1:
            bucket = next(iter(known))         # consenso unánime
            anchored = True

        # 5. Confianza + misfiled.
        if anchored and bucket is not None:
            confidence = "alta"
            misfiled = tuple(
                d.doc_id for d in members
                if resolver(d.id_carpeta, d.id_carpeta_label)[0] not in (bucket, None)
            )
            if header is not None:
                reason = (
                    f"Lote de {len(members)} docs (subida {ts}); cabecera "
                    f"'{header.filename}' → {bucket}"
                    + (f"; {len(misfiled)} prueba(s) mal archivada(s)" if misfiled else "")
                )
            else:
                reason = (
                    f"Lote de {len(members)} docs (subida {ts}); sin cabecera "
                    f"identificada, bucket por consenso unánime → {bucket}"
                )
        else:
            confidence = "baja"
            misfiled = ()
            reason = (
                f"Lote de {len(members)} docs (subida {ts}) sin cabecera resoluble "
                f"y miembros en buckets dispares {sorted(known)} — revisión letrado"
            )

        proposals.append(BundleProposal(
            timestamp=ts,
            header_doc_id=header.doc_id if header is not None else None,
            bucket=bucket,
            member_doc_ids=tuple(d.doc_id for d in members),
            evidence_doc_ids=tuple(d.doc_id for d in evidence),
            misfiled_doc_ids=misfiled,
            confidence=confidence,
            reason=reason,
        ))

    return proposals


def log_bundle_proposals(case_id: str, proposals: list[BundleProposal]) -> int:
    """Emite las propuestas del detector al log de intake del caso (M10).

    Alta confianza → evento ``conjunto_detectado``. Baja → ``pendiente_revision``
    con ``details.motivo = "conjunto_baja_confianza"`` (sin adivinar el destino).
    NO persiste ``parent_id`` (diferido a ``[SIGUIENTE-CATALOGO-DOCUMENTAL]``).

    Returns:
        Número de eventos escritos.
    """
    from core import intake_log  # import perezoso: respeta reloads de config en tests

    for p in proposals:
        details = {
            "timestamp": p.timestamp,
            "header_doc_id": p.header_doc_id,
            "bucket": p.bucket,
            "member_doc_ids": list(p.member_doc_ids),
            "evidence_doc_ids": list(p.evidence_doc_ids),
            "misfiled_doc_ids": list(p.misfiled_doc_ids),
            "reason": p.reason,
        }
        if p.confidence == "alta":
            intake_log.append_event(case_id, "conjunto_detectado", details=details)
        else:
            details["motivo"] = "conjunto_baja_confianza"
            intake_log.append_event(case_id, "pendiente_revision", details=details)

    return len(proposals)
