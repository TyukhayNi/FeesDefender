"""Tests del detector de conjunto (D9).

Reagrupa cabecera + prueba documental subidas en lote al CRM:
- clúster por ``modified_at`` (timestamp de modificación) idéntico
- ∩ patrón de numeración de prueba del despacho ``D\\s*\\d+\\s*-``
- ancla el lote a su cabecera (el doc del lote SIN patrón D NN) → bucket
- baja confianza → pendiente_revision, sin adivinar

Estructura empírica de referencia: expediente 444 (BaRS6), lote de demanda
(carpeta 307 → 01_Demanda): 20 docs ``D NN`` + 1 cabecera
``ORDINARIO - VUELTA VENDEDOR - VALLDAURA.doc`` (sin D NN), todos con el
mismo timestamp. La cabecera NO se llama "DEMANDA": se detecta como el
odd-one-out sin patrón de prueba.
"""
from __future__ import annotations

import pytest

from core.conjunto_detector import (
    BundleProposal,
    detect_bundles,
    is_evidence_marker,
    log_bundle_proposals,
)
from core.sync_sudespacho import GdocuDocInfo


def _doc(doc_id: str, filename: str, id_carpeta: str | None, ts: str | None) -> GdocuDocInfo:
    return GdocuDocInfo(
        doc_id=doc_id,
        filename=filename,
        id_carpeta=id_carpeta,
        id_carpeta_label=None,
        mime="application/pdf",
        size=1000,
        raw={},
        modified_at=ts,
    )


# ---- is_evidence_marker ---------------------------------------------------

@pytest.mark.parametrize("filename, expected", [
    ("D 02 - ENCARGO DE VENTA.pdf", True),
    ("D 08-A - CRM - COMPRADOR.pdf", True),       # sub-índice con letra
    ("D 08-B -  LEAD IDEALISTA.pdf", True),
    ("D 11- CRM - FICHA COMPRADOR.pdf", True),    # sin espacio antes del guion
    ("D17 - REQUERIMIENTO.pdf", True),            # sin espacio tras la D
    ("D 22-C - prueba.pdf", True),
    ("ORDINARIO - VUELTA VENDEDOR - VALLDAURA.doc", False),
    ("DECRETO ADMISION.pdf", False),              # empieza por D pero sin dígito
    ("DEMANDA EJECUTIVA.pdf", False),
    ("CONTESTACION.pdf", False),
])
def test_is_evidence_marker(filename, expected):
    assert is_evidence_marker(filename) is expected


# ---- detect_bundles: caso canónico (cabecera + prueba, coherente) ---------

TS1 = "2024-12-04T15:02:04.000+01:00"
TS2 = "2024-05-03T14:27:03.000+02:00"


def test_lote_con_cabecera_clara_alta_confianza():
    docs = [
        _doc("100", "ORDINARIO - VUELTA VENDEDOR.doc", "307", TS1),  # cabecera
        _doc("101", "D 02 - ENCARGO.pdf", "307", TS1),
        _doc("102", "D 03 - DNI.pdf", "307", TS1),
        _doc("103", "D 04 - NOTA SIMPLE.pdf", "307", TS1),
    ]
    props = detect_bundles(docs)
    assert len(props) == 1
    p = props[0]
    assert isinstance(p, BundleProposal)
    assert p.timestamp == TS1
    assert p.header_doc_id == "100"
    assert p.bucket == "01_Demanda"           # 307 → Declarativo/Demanda
    assert p.confidence == "alta"
    assert set(p.member_doc_ids) == {"100", "101", "102", "103"}
    assert set(p.evidence_doc_ids) == {"101", "102", "103"}
    assert p.misfiled_doc_ids == ()


def test_lote_con_prueba_mal_archivada_detecta_misfiled():
    """Una prueba en carpeta distinta a la cabecera → marcada como misfiled."""
    docs = [
        _doc("200", "ORDINARIO - VUELTA.doc", "307", TS1),     # cabecera → 01_Demanda
        _doc("201", "D 02 - ENCARGO.pdf", "307", TS1),
        _doc("202", "D 03 - DNI.pdf", "1", TS1),               # mal archivada (General→99_Otros)
    ]
    props = detect_bundles(docs)
    assert len(props) == 1
    p = props[0]
    assert p.bucket == "01_Demanda"
    assert p.confidence == "alta"
    assert p.misfiled_doc_ids == ("202",)


def test_lote_sin_cabecera_pero_bucket_unanime_alta():
    """Todos prueba (sin cabecera), misma carpeta → bucket por consenso, alta."""
    docs = [
        _doc("300", "D 02 - ENCARGO.pdf", "380", TS2),
        _doc("301", "D 03 - DNI.pdf", "380", TS2),
        _doc("302", "D 04 - NOTA.pdf", "380", TS2),
    ]
    props = detect_bundles(docs)
    assert len(props) == 1
    p = props[0]
    assert p.header_doc_id is None
    assert p.bucket == "05_Diligencias_Preliminares"   # 380 → Preliminares
    assert p.confidence == "alta"


def test_lote_sin_cabecera_buckets_dispares_baja():
    """Prueba dispersa en buckets distintos, sin cabecera → baja confianza."""
    docs = [
        _doc("400", "D 02 - ENCARGO.pdf", "307", TS1),   # → 01_Demanda
        _doc("401", "D 03 - DNI.pdf", "308", TS1),       # → 02_Contestacion
    ]
    props = detect_bundles(docs)
    assert len(props) == 1
    p = props[0]
    assert p.bucket is None
    assert p.confidence == "baja"


def test_cluster_sin_patron_D_no_es_lote():
    """Timestamp idéntico pero sin ningún doc con patrón D NN → no es lote."""
    docs = [
        _doc("500", "ESCRITO TRAMITE.pdf", "1", TS1),
        _doc("501", "PROVIDENCIA.pdf", "1", TS1),
    ]
    assert detect_bundles(docs) == []


def test_timestamps_distintos_no_se_agrupan():
    docs = [
        _doc("600", "ORDINARIO.doc", "307", TS1),
        _doc("601", "D 02 - ENCARGO.pdf", "307", TS2),   # otro timestamp
    ]
    # Ningún cluster alcanza un lote (cada timestamp tiene 1 doc).
    assert detect_bundles(docs) == []


def test_documentos_sin_timestamp_se_ignoran():
    docs = [
        _doc("700", "ORDINARIO.doc", "307", None),
        _doc("701", "D 02 - ENCARGO.pdf", "307", None),
        _doc("702", "D 03 - DNI.pdf", "307", ""),
    ]
    assert detect_bundles(docs) == []


def test_cabecera_ambigua_por_keyword():
    """Dos docs sin D NN en el lote → cabecera = la que casa keyword procesal."""
    docs = [
        _doc("800", "DEMANDA ORDINARIO.pdf", "307", TS1),   # keyword cabecera
        _doc("801", "INDICE DE DOCUMENTOS.pdf", "307", TS1),  # no keyword
        _doc("802", "D 02 - ENCARGO.pdf", "307", TS1),
        _doc("803", "D 03 - DNI.pdf", "307", TS1),
    ]
    props = detect_bundles(docs)
    assert len(props) == 1
    assert props[0].header_doc_id == "800"
    assert props[0].confidence == "alta"


# ---- log_bundle_proposals -------------------------------------------------

def test_log_bundle_proposals_emite_eventos(tmp_casos_root):
    import importlib
    from core import config as cfg
    from core import case_manager as cm
    from core import intake_log as il
    from core import conjunto_detector as cd
    importlib.reload(cfg)
    importlib.reload(cm)
    importlib.reload(il)
    importlib.reload(cd)
    cm.ensure_case("CASO1")

    proposals = [
        BundleProposal(
            timestamp=TS1, header_doc_id="100", bucket="01_Demanda",
            member_doc_ids=("100", "101"), evidence_doc_ids=("101",),
            misfiled_doc_ids=(), confidence="alta", reason="cabecera clara",
        ),
        BundleProposal(
            timestamp=TS2, header_doc_id=None, bucket=None,
            member_doc_ids=("400", "401"), evidence_doc_ids=("400", "401"),
            misfiled_doc_ids=(), confidence="baja", reason="buckets dispares",
        ),
    ]
    cd.log_bundle_proposals("CASO1", proposals)
    events = il.read_events("CASO1")
    kinds = [e["event"] for e in events]
    assert "conjunto_detectado" in kinds
    assert "pendiente_revision" in kinds
    pend = next(e for e in events if e["event"] == "pendiente_revision")
    assert pend["details"]["motivo"] == "conjunto_baja_confianza"
