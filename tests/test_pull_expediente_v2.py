"""Tests dedicados v2 — paso 8 del refactor intake v2.

Función bajo test: ``core.sync_sudespacho.pull_expediente_v2``.

Es el módulo de integración: orquesta ``crm_branch_path`` (resolución
de rama), ``IntakeManifest`` (dedup M9), ``intake_log`` (M10),
``update_pull_state`` (D8) y el guard ``is_legacy_intake_v1`` (D9).
Las primitivas ya están testeadas por separado; aquí verificamos
composición.

Mocking — convención de este fichero:

- ``FakeSudespachoClient`` duck-typed con los 3 métodos que invoca
  ``pull_expediente_v2`` (``list_gdocu_docs_rest``,
  ``get_presigned_download_url``, ``_download_url_raw``). Se pasa vía el
  parámetro ``client=`` de la función — no necesitamos monkeypatchar
  ``SudespachoConfig.from_env`` ni reusar el patrón ``__new__`` de
  ``test_sync_sudespacho.py`` porque la firma acepta cliente externo.
- El fake registra las llamadas que recibe para asserts de "X NO se
  llamó cuando lo legacy estaba bloqueado", etc.
"""

from __future__ import annotations

import hashlib
import importlib
import json

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def modules(tmp_casos_root):
    """Recarga case_manager + intake_log + intake_manifest (NO sync_sudespacho).

    ``sync_sudespacho`` NO debe recargarse: ``test_sync_sudespacho.py``
    importa ``SudespachoError`` / ``SudespachoClient`` / ``pull_expediente``
    al top del fichero, y un reload aquí dejaría esas referencias
    desincronizadas con las versiones nuevas del módulo (rompiendo
    ``pytest.raises(SudespachoError)`` y los ``monkeypatch.setattr`` sobre
    métodos de ``SudespachoClient``).

    No es necesario recargarlo igualmente: las funciones internas de
    ``pull_expediente_v2`` resuelven ``caso_path``, ``IntakeManifest``,
    etc. vía las globals de los módulos recargados, así que el
    ``casos_root`` del tmp se propaga sin tocar este módulo.
    """
    from core import case_manager, intake_log, intake_manifest, sync_sudespacho

    importlib.reload(case_manager)
    importlib.reload(intake_log)
    importlib.reload(intake_manifest)
    # sync_sudespacho NO se recarga — ver docstring

    return {
        "case_manager": case_manager,
        "intake_log": intake_log,
        "intake_manifest": intake_manifest,
        "sync_sudespacho": sync_sudespacho,
    }


@pytest.fixture(autouse=True)
def _reset_actor_singleton():
    from core import intake_log as _il
    _il.set_actor(None)
    yield
    _il.set_actor(None)


# ---------------------------------------------------------------------------
# Fake client — duck-typed
# ---------------------------------------------------------------------------

class FakeSudespachoClient:
    """Cliente fake que satisface la API que invoca ``pull_expediente_v2``."""

    def __init__(
        self,
        docs=None,
        docs_content=None,
        list_error=None,
        download_errors=None,
    ):
        self._docs = docs or []
        self._content = docs_content or {}
        self._list_error = list_error
        self._download_errors = download_errors or set()
        self.list_calls = []
        self.url_calls = []
        self.download_calls = []

    def list_gdocu_docs_rest(self, exp_id, element="expedientes_judiciales"):
        self.list_calls.append((str(exp_id), element))
        if self._list_error is not None:
            raise self._list_error
        return self._docs

    def get_presigned_download_url(
        self, doc_id, exp_id, element="expedientes_judiciales",
    ):
        self.url_calls.append((str(doc_id), str(exp_id)))
        if str(doc_id) in self._download_errors:
            from core.sync_sudespacho import SudespachoError
            raise SudespachoError(f"presigned failed for doc {doc_id}")
        return f"https://fake-s3.example/{doc_id}"

    def _download_url_raw(self, url):
        self.download_calls.append(url)
        doc_id = url.rsplit("/", 1)[-1]
        return self._content.get(doc_id, b"")


def _make_doc(modules, doc_id, *, filename, id_carpeta=None, id_carpeta_label=None):
    """Construye un ``GdocuDocInfo`` con los campos mínimos del fake."""
    GdocuDocInfo = modules["sync_sudespacho"].GdocuDocInfo
    return GdocuDocInfo(
        doc_id=str(doc_id),
        filename=filename,
        id_carpeta=id_carpeta,
        id_carpeta_label=id_carpeta_label,
        mime="application/pdf",
        size=None,
        raw={},
    )


def _read_log_events(modules, case_id):
    return modules["intake_log"].read_events(case_id)


# ---------------------------------------------------------------------------
# 1. Happy path — un doc con id_carpeta canónico
# ---------------------------------------------------------------------------

def test_pull_v2_un_doc_con_id_canonico_se_escribe_y_loggea(
    modules, tmp_casos_root,
):
    cm = modules["case_manager"]
    ss = modules["sync_sudespacho"]
    cm.ensure_case("PV2-1")

    content = b"%PDF-1.4 demo content"
    doc = _make_doc(modules, "40054", filename="Demanda.pdf",
                    id_carpeta="307", id_carpeta_label="DEMANDA")
    client = FakeSudespachoClient(
        docs=[doc], docs_content={"40054": content},
    )

    result = ss.pull_expediente_v2(
        "PV2-1", "648", client=client, actor="Nikolai Tyukhay",
    )

    # Resultado agregado
    assert result.blocked_legacy_v1 is False
    assert result.documents_total_crm == 1
    assert result.documents_written == 1
    assert result.documents_skipped_dedup == 0
    assert result.documents_failed == 0
    assert result.doc_ids == ["40054"]
    assert result.kind_distribution == {"id_mapping": 1}
    assert result.errors == []

    # Fichero físico en la rama esperada
    expected_dir = (
        tmp_casos_root / "PV2-1" / "00_Input" / "05_CRM"
        / "Civil" / "1ª Instancia" / "Declarativo" / "Demanda"
    )
    files = list(expected_dir.glob("*.pdf"))
    assert len(files) == 1
    assert files[0].read_bytes() == content

    # by_carpeta usa ruta canónica relativa a 05_CRM
    assert result.by_carpeta == {"Civil/1ª Instancia/Declarativo/Demanda": 1}

    # Evento pull_crm con resumen
    events = _read_log_events(modules, "PV2-1")
    pull_events = [e for e in events if e["event"] == "pull_crm"]
    assert len(pull_events) == 1
    pull = pull_events[0]
    assert pull["actor"] == "Nikolai Tyukhay"
    assert pull["details"]["documents_written"] == 1
    assert pull["details"]["kind_distribution"] == {"id_mapping": 1}


# ---------------------------------------------------------------------------
# 1b. Extensión derivada del MIME cuando el nombre del CRM no la trae
# ---------------------------------------------------------------------------

def test_pull_v2_extension_desde_mime_cuando_falta_en_nombre(modules, tmp_casos_root):
    """Doc del CRM sin extensión en el nombre (p. ej. 'ESCRITO CONTESTACION
    CRIO') se deposita con la extensión derivada del MIME, no como .bin."""
    cm = modules["case_manager"]
    ss = modules["sync_sudespacho"]
    cm.ensure_case("PV2-EXT")

    # _make_doc fija mime="application/pdf"; filename SIN extensión.
    doc = _make_doc(modules, "33640", filename="ESCRITO CONTESTACION CRIO",
                    id_carpeta="1")
    client = FakeSudespachoClient(
        docs=[doc], docs_content={"33640": b"%PDF-1.4 contestacion"},
    )

    result = ss.pull_expediente_v2("PV2-EXT", "444", client=client)

    assert result.documents_written == 1
    crm = tmp_casos_root / "PV2-EXT" / "00_Input" / "05_CRM"
    pdfs = list(crm.rglob("*.pdf"))
    assert len(pdfs) == 1
    assert pdfs[0].name == "escrito_contestacion_crio.pdf"
    assert not list(crm.rglob("*.bin"))


# ---------------------------------------------------------------------------
# 2. Dos docs en ramas distintas
# ---------------------------------------------------------------------------

def test_pull_v2_dos_docs_en_ramas_distintas(modules, tmp_casos_root):
    cm = modules["case_manager"]
    ss = modules["sync_sudespacho"]
    cm.ensure_case("PV2-2")

    doc_a = _make_doc(modules, "1001", filename="Demanda.pdf", id_carpeta="307")
    doc_b = _make_doc(modules, "1002", filename="Nota.pdf",    id_carpeta="1")
    client = FakeSudespachoClient(
        docs=[doc_a, doc_b],
        docs_content={"1001": b"%PDF demanda", "1002": b"%PDF nota"},
    )

    result = ss.pull_expediente_v2("PV2-2", "648", client=client)

    assert result.documents_written == 2
    assert result.kind_distribution == {"id_mapping": 2}
    assert set(result.by_carpeta.keys()) == {
        "Civil/1ª Instancia/Declarativo/Demanda",
        "General",
    }
    assert all(v == 1 for v in result.by_carpeta.values())


# ---------------------------------------------------------------------------
# 3. Fallback — id desconocido + label desconocido
# ---------------------------------------------------------------------------

def test_pull_v2_fallback_emite_category_unknown(modules, tmp_casos_root):
    cm = modules["case_manager"]
    ss = modules["sync_sudespacho"]
    cm.ensure_case("PV2-3")

    doc = _make_doc(
        modules, "5001",
        filename="Extraño.pdf",
        id_carpeta="9999",            # no está en CARPETA_ID_TO_PATH
        id_carpeta_label="ZZZ",       # no está en CRM_TREE
    )
    client = FakeSudespachoClient(
        docs=[doc], docs_content={"5001": b"%PDF extranho"},
    )

    result = ss.pull_expediente_v2(
        "PV2-3", "777", client=client, actor="Karen Paola Barreto",
    )

    assert result.documents_written == 1
    assert result.kind_distribution == {"fallback": 1}
    # Fichero cae en 99_Sin categoria/777
    fallback_dir = (
        tmp_casos_root / "PV2-3" / "00_Input" / "05_CRM"
        / "99_Sin categoria" / "777"
    )
    assert any(fallback_dir.glob("*.pdf"))

    # Evento category_unknown con los datos del doc
    events = _read_log_events(modules, "PV2-3")
    cu_events = [e for e in events if e["event"] == "category_unknown"]
    assert len(cu_events) == 1
    cu = cu_events[0]
    assert cu["actor"] == "Karen Paola Barreto"
    assert cu["details"]["expediente_id"] == "777"
    assert cu["details"]["doc_id"] == "5001"
    assert cu["details"]["id_carpeta"] == "9999"
    assert cu["details"]["id_carpeta_label"] == "ZZZ"


# ---------------------------------------------------------------------------
# 4. Bloqueo legacy v1
# ---------------------------------------------------------------------------

def test_pull_v2_bloquea_caso_legacy_v1(modules, tmp_casos_root):
    cm = modules["case_manager"]
    ss = modules["sync_sudespacho"]
    cm.ensure_case("PV2-4")
    # Marca el caso como legacy v1 plantando una subcarpeta sudespacho_*
    (tmp_casos_root / "PV2-4" / "00_Input" / "sudespacho_999").mkdir()

    client = FakeSudespachoClient()
    result = ss.pull_expediente_v2("PV2-4", "999", client=client)

    assert result.blocked_legacy_v1 is True
    assert result.documents_total_crm == 0
    assert result.documents_written == 0
    assert any("v1" in e for e in result.errors)
    # El cliente NO se llamó
    assert client.list_calls == []
    assert client.url_calls == []
    assert client.download_calls == []


# ---------------------------------------------------------------------------
# 5. Cliente devuelve lista vacía
# ---------------------------------------------------------------------------

def test_pull_v2_cliente_devuelve_vacio_emite_pull_crm_igual(modules):
    cm = modules["case_manager"]
    ss = modules["sync_sudespacho"]
    cm.ensure_case("PV2-5")

    client = FakeSudespachoClient(docs=[])
    result = ss.pull_expediente_v2("PV2-5", "648", client=client)

    assert result.documents_total_crm == 0
    assert result.documents_written == 0
    assert result.documents_skipped_dedup == 0
    # Hay un error informativo ("expediente vacío")
    assert result.errors and any("vacío" in e or "vacio" in e for e in result.errors)
    # El log pull_crm se emite igual (cierre del pull, incluso vacío)
    events = _read_log_events(modules, "PV2-5")
    assert any(e["event"] == "pull_crm" for e in events)


# ---------------------------------------------------------------------------
# 6. Dedup — hash ya presente en manifest pre-existente
# ---------------------------------------------------------------------------

def test_pull_v2_hash_en_manifest_emite_dedup_skipped(modules, tmp_casos_root):
    cm = modules["case_manager"]
    ss = modules["sync_sudespacho"]
    im = modules["intake_manifest"]
    cm.ensure_case("PV2-6")

    # Pre-escribir el manifest con el sha del contenido que devolverá el fake
    content = b"contenido identico - mismo sha"
    sha = hashlib.sha256(content).hexdigest()
    preexisting = {
        sha: {
            "primary_path": "01_Drive EV/contrato.pdf",
            "aliases": [],
        }
    }
    im.manifest_path("PV2-6").write_text(
        json.dumps(preexisting, ensure_ascii=False), encoding="utf-8",
    )

    doc = _make_doc(modules, "2001", filename="contrato.pdf", id_carpeta="307")
    client = FakeSudespachoClient(docs=[doc], docs_content={"2001": content})

    result = ss.pull_expediente_v2("PV2-6", "648", client=client)

    assert result.documents_written == 0
    assert result.documents_skipped_dedup == 1
    # El fichero físico NO se escribió en la rama CRM destino
    crm_demanda = (
        tmp_casos_root / "PV2-6" / "00_Input" / "05_CRM"
        / "Civil" / "1ª Instancia" / "Declarativo" / "Demanda"
    )
    assert list(crm_demanda.glob("*.pdf")) == []

    # Evento dedup_skipped
    events = _read_log_events(modules, "PV2-6")
    ded_events = [e for e in events if e["event"] == "dedup_skipped"]
    assert len(ded_events) == 1
    ded = ded_events[0]
    assert ded["details"]["sha256"] == sha
    assert ded["details"]["primary_path"] == "01_Drive EV/contrato.pdf"


# ---------------------------------------------------------------------------
# 6b. physical_complete=True — overlap cross-source: se escribe igualmente
# ---------------------------------------------------------------------------

def test_pull_v2_physical_complete_escribe_overlap_y_loggea(modules, tmp_casos_root):
    """Con ``physical_complete=True``, un doc cuyo SHA ya está en el manifest
    bajo otra fuente (p. ej. Drive E&V) se escribe IGUALMENTE en su rama CRM:
    ``05_CRM`` queda físicamente completo. Cuenta como ``documents_overlap``,
    emite ``cross_source_overlap`` y el alias queda registrado."""
    cm = modules["case_manager"]
    ss = modules["sync_sudespacho"]
    im = modules["intake_manifest"]
    cm.ensure_case("PV2-OVL")

    # El SHA ya existe en el manifest, primary en Drive E&V (otra fuente).
    content = b"contrato identico cross-source"
    sha = hashlib.sha256(content).hexdigest()
    im.manifest_path("PV2-OVL").write_text(
        json.dumps(
            {sha: {"primary_path": "01_Drive EV/contrato.pdf", "aliases": []}},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    doc = _make_doc(modules, "8001", filename="contrato.pdf", id_carpeta="307")
    client = FakeSudespachoClient(docs=[doc], docs_content={"8001": content})

    result = ss.pull_expediente_v2(
        "PV2-OVL", "648", client=client, physical_complete=True,
        actor="Nikolai Tyukhay",
    )

    # No se "salta": se escribe como overlap.
    assert result.documents_written == 0
    assert result.documents_skipped_dedup == 0
    assert result.documents_overlap == 1

    # El fichero físico SÍ está en la rama CRM destino.
    crm_demanda = (
        tmp_casos_root / "PV2-OVL" / "00_Input" / "05_CRM"
        / "Civil" / "1ª Instancia" / "Declarativo" / "Demanda"
    )
    pdfs = list(crm_demanda.glob("*.pdf"))
    assert len(pdfs) == 1
    assert pdfs[0].read_bytes() == content

    # Evento cross_source_overlap con primary y written.
    events = _read_log_events(modules, "PV2-OVL")
    ovl = [e for e in events if e["event"] == "cross_source_overlap"]
    assert len(ovl) == 1
    assert ovl[0]["actor"] == "Nikolai Tyukhay"
    assert ovl[0]["details"]["sha256"] == sha
    assert ovl[0]["details"]["primary_path"] == "01_Drive EV/contrato.pdf"
    assert ovl[0]["details"]["written_path"].endswith("contrato.pdf")
    assert ovl[0]["details"]["doc_id"] == "8001"
    # NO se emite dedup_skipped en este modo.
    assert [e for e in events if e["event"] == "dedup_skipped"] == []

    # El alias quedó registrado en el manifest.
    with im.IntakeManifest("PV2-OVL") as manifest:
        entry = manifest.lookup(sha)
    assert entry["primary_path"] == "01_Drive EV/contrato.pdf"
    alias_paths = {a["path"] for a in entry["aliases"]}
    assert any(p.endswith("contrato.pdf") for p in alias_paths)

    # pull_crm reporta documents_overlap.
    pull = [e for e in events if e["event"] == "pull_crm"][0]
    assert pull["details"]["documents_overlap"] == 1


def test_pull_v2_physical_complete_false_sigue_saltando(modules, tmp_casos_root):
    """Regresión: con el default (``physical_complete=False``), el mismo
    escenario sigue produciendo skip físico (``dedup_skipped``), no overlap."""
    cm = modules["case_manager"]
    ss = modules["sync_sudespacho"]
    im = modules["intake_manifest"]
    cm.ensure_case("PV2-NOOVL")

    content = b"contrato identico cross-source"
    sha = hashlib.sha256(content).hexdigest()
    im.manifest_path("PV2-NOOVL").write_text(
        json.dumps(
            {sha: {"primary_path": "01_Drive EV/contrato.pdf", "aliases": []}},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    doc = _make_doc(modules, "8002", filename="contrato.pdf", id_carpeta="307")
    client = FakeSudespachoClient(docs=[doc], docs_content={"8002": content})

    result = ss.pull_expediente_v2("PV2-NOOVL", "648", client=client)

    assert result.documents_written == 0
    assert result.documents_skipped_dedup == 1
    assert result.documents_overlap == 0
    crm_demanda = (
        tmp_casos_root / "PV2-NOOVL" / "00_Input" / "05_CRM"
        / "Civil" / "1ª Instancia" / "Declarativo" / "Demanda"
    )
    assert list(crm_demanda.glob("*.pdf")) == []
    events = _read_log_events(modules, "PV2-NOOVL")
    assert len([e for e in events if e["event"] == "dedup_skipped"]) == 1
    assert [e for e in events if e["event"] == "cross_source_overlap"] == []


# ---------------------------------------------------------------------------
# 7. Idempotencia — segundo run, sobrescritura de documents_total_crm
# ---------------------------------------------------------------------------

def test_pull_v2_idempotencia_segundo_run_dedup_y_total_crm_sobrescribe(
    modules,
):
    cm = modules["case_manager"]
    ss = modules["sync_sudespacho"]
    cm.ensure_case("PV2-7")

    content = b"%PDF idempotente"
    doc = _make_doc(modules, "3001", filename="x.pdf", id_carpeta="1")
    client = FakeSudespachoClient(docs=[doc], docs_content={"3001": content})

    # Run 1 — escribe
    r1 = ss.pull_expediente_v2("PV2-7", "648", client=client)
    assert r1.documents_written == 1
    assert r1.documents_skipped_dedup == 0

    # Run 2 — el mismo doc viene del CRM otra vez (mismo sha) → dedup
    r2 = ss.pull_expediente_v2("PV2-7", "648", client=client)
    assert r2.documents_written == 0
    assert r2.documents_skipped_dedup == 1

    # documents_total_crm sobrescribe (no acumula): tras 2 runs, sigue siendo
    # el del último run = 1 doc visto en el CRM (D12 — el state es foto del
    # último pull, el histórico vive en _intake_log.jsonl).
    state = cm.read_pull_state("PV2-7", "648")
    assert state is not None
    assert state["documents_total_crm"] == 1

    # En el log conviven los 2 eventos pull_crm — uno por run
    events = _read_log_events(modules, "PV2-7")
    pull_events = [e for e in events if e["event"] == "pull_crm"]
    assert len(pull_events) == 2


# ---------------------------------------------------------------------------
# 8. update_pull_state — schema D8 tras el pull
# ---------------------------------------------------------------------------

def test_pull_v2_actualiza_pull_state_con_schema_d8(modules):
    cm = modules["case_manager"]
    ss = modules["sync_sudespacho"]
    cm.ensure_case("PV2-8")

    doc = _make_doc(modules, "4001", filename="y.pdf", id_carpeta="307")
    client = FakeSudespachoClient(docs=[doc], docs_content={"4001": b"%PDF y"})

    ss.pull_expediente_v2(
        "PV2-8", "648", client=client, element="expedientes_judiciales",
    )

    state = cm.read_pull_state("PV2-8", "648")
    assert state is not None
    assert state["id"] == "648"
    assert state["element"] == "expedientes_judiciales"
    assert state["doc_ids"] == ["4001"]
    assert state["documents_total_crm"] == 1
    assert state["by_carpeta"] == {"Civil/1ª Instancia/Declarativo/Demanda": 1}
    assert state["errors"] == []
    assert "linked_at" in state and state["linked_at"]
    assert "last_sync" in state and state["last_sync"]


# ---------------------------------------------------------------------------
# 9. Actor override
# ---------------------------------------------------------------------------

def test_pull_v2_actor_override_se_aplica_a_eventos_log(modules):
    cm = modules["case_manager"]
    ss = modules["sync_sudespacho"]
    il = modules["intake_log"]
    cm.ensure_case("PV2-9")
    # El singleton apunta a Nikolai, pero el override debe ganar
    il.set_actor("Nikolai Tyukhay")

    doc = _make_doc(modules, "6001", filename="z.pdf", id_carpeta="9999")  # fallback
    client = FakeSudespachoClient(docs=[doc], docs_content={"6001": b"%PDF z"})

    ss.pull_expediente_v2(
        "PV2-9", "777", client=client, actor="Marta Reynares",
    )

    events = _read_log_events(modules, "PV2-9")
    # Todos los eventos emitidos por pull_expediente_v2 deben llevar el override
    relevant = [e for e in events if e["event"] in {"category_unknown", "pull_crm"}]
    assert relevant, "Esperábamos al menos category_unknown y pull_crm"
    for e in relevant:
        assert e["actor"] == "Marta Reynares"

    # El singleton NO ha cambiado tras el pull
    assert il.get_actor() == "Nikolai Tyukhay"


# ---------------------------------------------------------------------------
# 10. list_gdocu_docs_rest lanza — short-circuit
# ---------------------------------------------------------------------------

def test_pull_v2_list_gdocu_falla_no_intenta_descargas(modules):
    ss = modules["sync_sudespacho"]
    cm = modules["case_manager"]
    cm.ensure_case("PV2-10")

    client = FakeSudespachoClient(
        list_error=ss.SudespachoError("503 backend down"),
    )
    result = ss.pull_expediente_v2("PV2-10", "648", client=client)

    assert result.documents_written == 0
    assert result.documents_total_crm == 0
    assert any("503" in e or "list_gdocu_docs_rest" in e for e in result.errors)
    # No se intentó ninguna descarga
    assert client.url_calls == []
    assert client.download_calls == []


# ---------------------------------------------------------------------------
# 11. Descarga falla en 1 de 2 docs
# ---------------------------------------------------------------------------

def test_pull_v2_download_falla_un_doc_otro_se_procesa(modules):
    ss = modules["sync_sudespacho"]
    cm = modules["case_manager"]
    cm.ensure_case("PV2-11")

    doc_ok   = _make_doc(modules, "7001", filename="ok.pdf",  id_carpeta="307")
    doc_fail = _make_doc(modules, "7002", filename="bad.pdf", id_carpeta="307")
    client = FakeSudespachoClient(
        docs=[doc_ok, doc_fail],
        docs_content={"7001": b"%PDF ok"},
        download_errors={"7002"},
    )

    result = ss.pull_expediente_v2("PV2-11", "648", client=client)

    assert result.documents_total_crm == 2
    assert result.documents_written == 1
    assert result.documents_failed == 1
    # El doc OK queda en doc_ids, el fallido no
    assert result.doc_ids == ["7001"]
    # Hay un error específico del doc fallado
    assert any("7002" in e for e in result.errors)
