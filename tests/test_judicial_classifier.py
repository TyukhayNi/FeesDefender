"""Tests del clasificador demanda/contestación (Fase 1 intake judicial).

Source-locked: las aserciones usan nombres de fichero REALES del expediente
649 (BaRR3). El clasificador no inventa tipologías; ancla a `filename` +
`id_carpeta_label` del CRM y, ante ambigüedad, marca `[PENDIENTE revisión
letrado]` en vez de adivinar.
"""

from __future__ import annotations

from core.judicial_classifier import (
    ROLE_CONTESTACION,
    ROLE_DEMANDA,
    classify,
)
from core.sync_sudespacho import GdocuDocInfo


def _doc(doc_id: str, filename: str, label: str | None = None) -> GdocuDocInfo:
    return GdocuDocInfo(
        doc_id=doc_id,
        filename=filename,
        id_carpeta=None,
        id_carpeta_label=label,
        mime=None,
        size=None,
        raw={},
    )


# ---- Casos claros ---------------------------------------------------------

def test_demanda_clara():
    res = classify([_doc("40022", "02_DEMANDA_01.pdf")])
    assert res.demanda.status == "ok"
    assert res.demanda.selected.doc_id == "40022"
    assert res.demanda.selected.role == ROLE_DEMANDA


def test_oposicion_es_contestacion_no_demanda():
    """'OPOSICION_DEMANDA' contiene 'demanda' pero es la contestación."""
    res = classify([_doc("40625", "OPOSICION_DEMANDA_CALLE_ROSER_-_ARTICULO_20_LAU.pdf")])
    assert res.contestacion.status == "ok"
    assert res.contestacion.selected.doc_id == "40625"
    assert res.demanda.status == "none"   # no debe contarse como demanda


# ---- Ruido que NO debe clasificarse --------------------------------------

def test_diligencia_contestada_no_es_contestacion():
    """'DIOR-POR CONTESTADA LA DDA' es una diligencia, no la contestación."""
    res = classify([_doc("40798", "DIOR-POR CONTESTADA LA DDA+CITA AUD PREVIA 13-1-27.pdf")])
    assert res.contestacion.status == "none"
    assert res.demanda.status == "none"


def test_justificante_presentacion_no_es_contestacion():
    """'JUSTIF PROCU-PTACION CONTESTA DDA' es un justificante de presentación."""
    res = classify([_doc("40659", "JUSTIF PROCU-PTACION CONTESTA DDA.pdf")])
    assert res.contestacion.status == "none"
    assert res.demanda.status == "none"


def test_documentos_prueba_no_clasifican():
    docs = [
        _doc("40570", "D 09 - CHAT WHATSAPP HYDEN - CONSULTORA.pdf"),
        _doc("40404", "D 16 - SENTENCIA - BARCELONA - 10.pdf"),
        _doc("40021", "01_ACTUACION_PROCESAL_01.pdf"),
        _doc("40020", "CEDULA DE EMPLAZAMIENTO - Seccion Civil.pdf"),
    ]
    res = classify(docs)
    assert res.demanda.status == "none"
    assert res.contestacion.status == "none"


# ---- Colapso de duplicados .pdf/.docx ------------------------------------

def test_colapsa_pdf_docx_mismo_nombre():
    """El mismo documento en .pdf y .docx colapsa a uno solo, prefiriendo .pdf."""
    docs = [
        _doc("40575", "OPOSICION_DEMANDA_CALLE_ROSER_-_ARTICULO_20_LAU.docx"),
        _doc("40625", "OPOSICION_DEMANDA_CALLE_ROSER_-_ARTICULO_20_LAU.pdf"),
    ]
    res = classify(docs)
    assert res.contestacion.status == "ok"
    assert res.contestacion.selected.doc_id == "40625"   # el .pdf
    assert res.contestacion.selected.ext == ".pdf"


# ---- Ambigüedad → PENDIENTE revisión letrado -----------------------------

def test_multiples_candidatos_distintos_pendiente():
    """Dos contestaciones con nombre distinto → ambiguo, sin adivinar."""
    docs = [
        _doc("40625", "OPOSICION_DEMANDA_CALLE_ROSER_-_ARTICULO_20_LAU.pdf"),
        _doc("40405", "OPOSICION_DEMANDA_-_ARTICULO_20_LAU.docx"),
    ]
    res = classify(docs)
    assert res.contestacion.status == "ambiguous"
    assert res.contestacion.selected is None
    assert {c.doc_id for c in res.contestacion.candidates} == {"40625", "40405"}
    assert res.pendientes  # hay al menos un rol pendiente de revisión


def test_cero_candidatos_status_none():
    res = classify([_doc("41289", "FRA PROCU ORDINARIO.pdf")])
    assert res.demanda.status == "none"
    assert res.contestacion.status == "none"


# ---- Demanda por tipo de procedimiento (aprendizajes del exp. 444) --------

def test_demanda_juicio_ordinario():
    """La demanda suele titularse por el juicio: 'ORDINARIO - ...'."""
    res = classify([_doc("31287", "ORDINARIO - VUELTA VENDEDOR - VALLDAURA.pdf")])
    assert res.demanda.status == "ok"
    assert res.demanda.selected.doc_id == "31287"


def test_escrito_alegaciones_no_es_demanda():
    """'ESCRTIO ALEGACIONES - PRESENTADA DEMANDA' es alegaciones, no la demanda."""
    res = classify([
        _doc("33279", "ESCRTIO_ALEGACIONES_-_PRESENTADA_DEMANDA__SOLICITAR_DEVOLUCION_CAUCION.pdf"),
    ])
    assert res.demanda.status == "none"


def test_justificante_just_escr_no_es_contestacion():
    """'JUST ESCR - CONTESTACION NULIDAD' es un justificante, no la contestación."""
    res = classify([_doc("34386", "JUST ESCR - CONTESTACION NULIDAD PRESENT.pdf")])
    assert res.contestacion.status == "none"


# ---- Etiqueta de carpeta como señal (doc escaneado sin nombre útil) ------

def test_label_carpeta_no_dispara_clasificacion():
    """La etiqueta de carpeta NO clasifica por sí sola.

    En el CRM real las carpetas 'DEMANDA'/'OPOSICION' contienen toda la prueba
    del expediente, no solo la pieza procesal. Un doc con nombre inútil en esas
    carpetas NO debe auto-clasificarse — va a revisión del letrado.
    """
    res = classify([_doc("99999", "2026_0000357_OR5_scan.pdf", label="Demanda")])
    assert res.demanda.status == "none"
    res2 = classify([_doc("88888", "D 09 - CHAT WHATSAPP.pdf", label="OPOSICION")])
    assert res2.contestacion.status == "none"


# ---- Regresión sobre el listado completo del expediente 649 --------------

# Etiquetas de carpeta REALES del expediente 649 (capturadas en el e2e del
# 2026-06-10). Nota: 40020/40021/40022 están en carpeta "DEMANDA" y casi toda
# la prueba (D01-D16) en "OPOSICION" — por eso la etiqueta NO puede disparar la
# clasificación. Este fixture blinda esa regresión.
_DOCS_649 = [
    _doc("41289", "FRA PROCU ORDINARIO.pdf", "DOCUMENTOS"),
    _doc("40923", "DIOR-NVA FECHA AUD 11 ENE 27, 10:15 HS.pdf", "DECLARATIVO"),
    _doc("40801", "ESCR CRIO-PIDE SUSPENSION Y NVO SEÑALAMIENTO.pdf"),
    _doc("40800", "NOTIFICACION AUD 13 ENE 27 EXP 591-25.pdf"),
    _doc("40798", "DIOR-POR CONTESTADA LA DDA+CITA AUD PREVIA 13-1-27.pdf"),
    _doc("40659", "JUSTIF PROCU-PTACION CONTESTA DDA.pdf"),
    _doc("40625", "OPOSICION_DEMANDA_CALLE_ROSER_-_ARTICULO_20_LAU.pdf", "OPOSICION"),
    _doc("40575", "OPOSICION_DEMANDA_CALLE_ROSER_-_ARTICULO_20_LAU.docx", "OPOSICION"),
    _doc("40574", "D 12 - CONTRATO ARRENDAMIENTO FIRMADO.pdf", "OPOSICION"),
    _doc("40572", "D 11 - OFERTA FIRMADA.pdf", "OPOSICION"),
    _doc("40568", "D 08 - CADENA EMAILS PATRICIA - CONYUGE ACTOR.pdf", "OPOSICION"),
    _doc("40407", "D 14 - SENTENCIA - VALENCIA - 29.pdf", "OPOSICION"),
    _doc("40405", "OPOSICION_DEMANDA_-_ARTICULO_20_LAU.docx", "CIVIL"),
    _doc("40404", "D 16 - SENTENCIA - BARCELONA - 10.pdf", "OPOSICION"),
    _doc("40193", "DIOR-POR APERSONADO PROCU.pdf"),
    _doc("40058", "JUST PROCU-ESCR DE PERSONACION.pdf"),
    _doc("40022", "02_DEMANDA_01.pdf", "DEMANDA"),
    _doc("40021", "01_ACTUACION_PROCESAL_01.pdf", "DEMANDA"),
    _doc("40020", "CEDULA DE EMPLAZAMIENTO - Seccion Civil.pdf", "DEMANDA"),
]


def test_regresion_649():
    res = classify(_DOCS_649)
    # Demanda: única por NOMBRE (40021/40020 están en carpeta DEMANDA pero su
    # nombre no es de demanda → no se cuelan).
    assert res.demanda.status == "ok"
    assert res.demanda.selected.doc_id == "40022"
    # Contestación: 2 candidatos distintos por nombre (.pdf colapsa con su
    # .docx). La prueba D01-D16 en carpeta OPOSICION NO se cuela. → pendiente.
    assert res.contestacion.status == "ambiguous"
    assert {c.doc_id for c in res.contestacion.candidates} == {"40625", "40405"}
