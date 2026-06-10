"""Tests del orquestador intake judicial (demanda + contestación).

Función bajo test: ``core.judicial_intake.intake_demanda_contestacion``.
Verifica la composición: listar → clasificar → pull acotado (solo los 2 docs)
→ marcar pendientes → log. Las primitivas (clasificador, pull_expediente_v2,
intake_log) ya están testeadas por separado.
"""

from __future__ import annotations

import importlib

import pytest


# ---------------------------------------------------------------------------
# Fixtures (mismo patrón que test_pull_expediente_v2.py)
# ---------------------------------------------------------------------------

@pytest.fixture
def modules(tmp_casos_root):
    from core import (
        case_manager,
        intake_log,
        intake_manifest,
        judicial_intake,
        sync_sudespacho,
    )

    importlib.reload(case_manager)
    importlib.reload(intake_log)
    importlib.reload(intake_manifest)
    # sync_sudespacho NO se recarga (ver docstring de test_pull_expediente_v2).
    importlib.reload(judicial_intake)   # re-liga is_legacy_intake_v1 / _log_event

    return {
        "case_manager": case_manager,
        "intake_log": intake_log,
        "judicial_intake": judicial_intake,
        "sync_sudespacho": sync_sudespacho,
    }


@pytest.fixture(autouse=True)
def _reset_actor_singleton():
    from core import intake_log as _il
    _il.set_actor(None)
    yield
    _il.set_actor(None)


class FakeClient:
    def __init__(self, docs, content=None):
        self._docs = docs
        self._content = content or {}
        self.list_calls = []

    def list_gdocu_docs_rest(self, exp_id, element="expedientes_judiciales"):
        self.list_calls.append((str(exp_id), element))
        return self._docs

    def get_presigned_download_url(self, doc_id, exp_id, element="expedientes_judiciales"):
        return f"https://fake-s3.example/{doc_id}"

    def _download_url_raw(self, url):
        return self._content.get(url.rsplit("/", 1)[-1], b"%PDF-1.4 x")


def _doc(modules, doc_id, filename, *, id_carpeta=None, label=None):
    GdocuDocInfo = modules["sync_sudespacho"].GdocuDocInfo
    return GdocuDocInfo(
        doc_id=str(doc_id), filename=filename,
        id_carpeta=id_carpeta, id_carpeta_label=label,
        mime="application/pdf", size=None, raw={},
    )


def _events(modules, case_id, event=None):
    evs = modules["intake_log"].read_events(case_id)
    return [e for e in evs if event is None or e["event"] == event]


# ---------------------------------------------------------------------------
# 1. Happy path — demanda + contestación claras, ruido ignorado
# ---------------------------------------------------------------------------

def test_intake_happy_path(modules, tmp_casos_root):
    ji = modules["judicial_intake"]
    modules["case_manager"].ensure_case("JUD-1")

    docs = [
        _doc(modules, "40022", "02_DEMANDA_01.pdf", id_carpeta="307"),
        _doc(modules, "40405", "OPOSICION_DEMANDA_-_ARTICULO_20_LAU.pdf", id_carpeta="1"),
        _doc(modules, "41289", "FRA PROCU ORDINARIO.pdf", id_carpeta="1"),
    ]
    client = FakeClient(docs, content={
        "40022": b"%PDF demanda", "40405": b"%PDF oposicion",
    })

    res = ji.intake_demanda_contestacion("JUD-1", "649", client=client)

    assert res.blocked_legacy_v1 is False
    assert res.demanda_doc_id == "40022"
    assert res.contestacion_doc_id == "40405"
    assert res.pendientes == []
    # Solo se pullan los 2 seleccionados, NO el ruido (FRA PROCU).
    assert res.pull is not None
    assert res.pull.documents_total_crm == 3   # total real del CRM
    assert res.pull.documents_written == 2
    assert set(res.pull.doc_ids) == {"40022", "40405"}

    # Eventos
    assert len(_events(modules, "JUD-1", "intake_judicial")) == 1
    assert len(_events(modules, "JUD-1", "pull_crm")) == 1
    assert _events(modules, "JUD-1", "pendiente_revision") == []


# ---------------------------------------------------------------------------
# 2. Contestación ambigua → demanda se pulla, contestación a revisión
# ---------------------------------------------------------------------------

def test_intake_contestacion_ambigua_pendiente(modules, tmp_casos_root):
    ji = modules["judicial_intake"]
    modules["case_manager"].ensure_case("JUD-2")

    docs = [
        _doc(modules, "40022", "02_DEMANDA_01.pdf", id_carpeta="307"),
        _doc(modules, "40625", "OPOSICION_DEMANDA_CALLE_ROSER_-_ARTICULO_20_LAU.pdf", id_carpeta="1"),
        _doc(modules, "40405", "OPOSICION_DEMANDA_-_ARTICULO_20_LAU.docx", id_carpeta="1"),
    ]
    client = FakeClient(docs, content={"40022": b"%PDF demanda"})

    res = ji.intake_demanda_contestacion("JUD-2", "649", client=client)

    assert res.demanda_doc_id == "40022"
    assert res.contestacion_doc_id is None
    assert res.pendientes == ["contestacion"]
    # Solo la demanda se pulla.
    assert res.pull.documents_written == 1
    assert res.pull.doc_ids == ["40022"]

    pend = _events(modules, "JUD-2", "pendiente_revision")
    assert len(pend) == 1
    assert pend[0]["details"]["role"] == "contestacion"
    assert {c["doc_id"] for c in pend[0]["details"]["candidates"]} == {"40625", "40405"}

    sumario = _events(modules, "JUD-2", "intake_judicial")[0]
    assert sumario["details"]["pendientes"] == ["contestacion"]


# ---------------------------------------------------------------------------
# 3. Caso legacy v1 → bloqueado, sin tocar el CRM
# ---------------------------------------------------------------------------

def test_intake_bloquea_legacy_v1(modules, tmp_casos_root):
    ji = modules["judicial_intake"]
    modules["case_manager"].ensure_case("JUD-3")
    # Crear estructura v1 (sudespacho_*/) que dispara el guard D9.
    (tmp_casos_root / "JUD-3" / "00_Input" / "sudespacho_649").mkdir(parents=True)

    client = FakeClient([])
    res = ji.intake_demanda_contestacion("JUD-3", "649", client=client)

    assert res.blocked_legacy_v1 is True
    assert res.pull is None
    assert client.list_calls == []   # no se llamó al CRM


# ---------------------------------------------------------------------------
# 4. Nada clasificable → ambos roles a revisión, sin pull
# ---------------------------------------------------------------------------

def test_intake_nada_clasificable(modules, tmp_casos_root):
    ji = modules["judicial_intake"]
    modules["case_manager"].ensure_case("JUD-4")

    docs = [
        _doc(modules, "41289", "FRA PROCU ORDINARIO.pdf", id_carpeta="1"),
        _doc(modules, "40020", "CEDULA DE EMPLAZAMIENTO.pdf", id_carpeta="1"),
    ]
    client = FakeClient(docs)
    res = ji.intake_demanda_contestacion("JUD-4", "649", client=client)

    assert res.demanda_doc_id is None
    assert res.contestacion_doc_id is None
    assert sorted(res.pendientes) == ["contestacion", "demanda"]
    assert res.pull is None
    assert len(_events(modules, "JUD-4", "pendiente_revision")) == 2
