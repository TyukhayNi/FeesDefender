"""Tests dedicados v2 — paso 8 del refactor intake v2.

Funciones bajo test:

- ``core.case_manager.update_pull_state`` — escribe/actualiza el entry de
  pull state de un expediente en el frontmatter de ``_caso.md`` (schema
  D8). Es la única función que escribe el pull state; la atomicidad se
  delega a ``_atomic_write_caso_md`` (temp + ``os.replace``).
- ``core.case_manager.read_pull_state`` — lectura sin escritura.

Schema D8 del entry::

    {
        "id": "648",
        "element": "expedientes_judiciales" | "extrajudiciales",
        "linked_at": "2026-05-11T10:00:00",
        "last_sync": "2026-05-11T10:05:00",
        "documents_total_crm": 12,
        "doc_ids": ["40054", "40055", ...],
        "by_carpeta": {"Civil/.../Demanda": 3, "General": 1},
        "errors": ["...", ...]
    }

Garantías que verifican estos tests:

- Atomicidad: si ``os.replace`` falla, ``_caso.md`` queda intacto y el
  ``.tmp`` se limpia.
- Idempotencia parcial: re-llamadas conservan ``linked_at`` y dejan los
  campos no-pasados sin tocar.
- Sobrescritura controlada: ``errors``, ``doc_ids``, ``by_carpeta``
  reemplazan (D12 — el state es estado actual, el histórico vive en
  ``_intake_log.jsonl``).
"""

from __future__ import annotations

import importlib

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def cm(tmp_casos_root):
    from core import case_manager as _cm

    importlib.reload(_cm)
    return _cm


# ---------------------------------------------------------------------------
# 1. Creación de entry nuevo (schema D8 completo)
# ---------------------------------------------------------------------------

def test_update_crea_entry_nuevo_con_schema_d8(cm):
    cm.ensure_case("PS-1")
    entry = cm.update_pull_state(
        "PS-1", "648",
        element="expedientes_judiciales",
        last_sync="2026-05-11T10:05:00",
        documents_total_crm=12,
        doc_ids=["40054", "40055"],
        by_carpeta={"Civil/1ª Instancia/Declarativo/Demanda": 2},
        errors=["doc 40060 download failed"],
    )

    assert entry["id"] == "648"
    assert entry["element"] == "expedientes_judiciales"
    assert "linked_at" in entry and entry["linked_at"]
    assert entry["last_sync"] == "2026-05-11T10:05:00"
    assert entry["documents_total_crm"] == 12
    assert entry["doc_ids"] == ["40054", "40055"]
    assert entry["by_carpeta"] == {"Civil/1ª Instancia/Declarativo/Demanda": 2}
    assert entry["errors"] == ["doc 40060 download failed"]


def test_update_falla_sin_element_al_crear(cm):
    """Element es obligatorio para vincular un expediente nuevo."""
    cm.ensure_case("PS-2")
    with pytest.raises(ValueError, match="element requerido"):
        cm.update_pull_state("PS-2", "999", last_sync="2026-05-11T00:00:00")


def test_update_falla_si_caso_md_no_existe(cm, tmp_casos_root):
    """FileNotFoundError si _caso.md no existe (caso no creado via ensure_case)."""
    (tmp_casos_root / "PS-3").mkdir()
    # NO ensure_case → no hay _caso.md
    with pytest.raises(FileNotFoundError):
        cm.update_pull_state("PS-3", "1", element="expedientes_judiciales")


# ---------------------------------------------------------------------------
# 2. Idempotencia parcial y semántica de kwargs
# ---------------------------------------------------------------------------

def test_linked_at_no_se_sobrescribe(cm):
    """``linked_at`` es timestamp de primera vinculación — no muta en updates."""
    cm.ensure_case("PS-4")
    first = cm.update_pull_state("PS-4", "1", element="expedientes_judiciales")
    linked_first = first["linked_at"]

    # Pausa simbólica + update
    second = cm.update_pull_state(
        "PS-4", "1", last_sync="2026-05-11T11:00:00",
    )
    assert second["linked_at"] == linked_first


def test_element_se_actualiza_si_difiere(cm):
    """Si se pasa ``element`` explícito en update y difiere, se sobrescribe."""
    cm.ensure_case("PS-5")
    cm.update_pull_state("PS-5", "1", element="expedientes_judiciales")
    updated = cm.update_pull_state("PS-5", "1", element="extrajudiciales")
    assert updated["element"] == "extrajudiciales"


def test_kwarg_none_conserva_campo(cm):
    """``last_sync=None`` no debe borrar el ``last_sync`` previo."""
    cm.ensure_case("PS-6")
    cm.update_pull_state(
        "PS-6", "1",
        element="expedientes_judiciales",
        last_sync="2026-05-11T10:00:00",
        doc_ids=["a", "b"],
    )
    updated = cm.update_pull_state("PS-6", "1", documents_total_crm=99)
    assert updated["last_sync"] == "2026-05-11T10:00:00"
    assert updated["doc_ids"] == ["a", "b"]
    assert updated["documents_total_crm"] == 99


def test_errors_sobrescribe(cm):
    """D12: ``errors`` es estado actual del último pull, no histórico."""
    cm.ensure_case("PS-7")
    cm.update_pull_state(
        "PS-7", "1",
        element="expedientes_judiciales",
        errors=["err-1", "err-2"],
    )
    updated = cm.update_pull_state("PS-7", "1", errors=["err-3"])
    assert updated["errors"] == ["err-3"]


def test_errors_vacio_sobrescribe(cm):
    """Pasar ``errors=[]`` debe limpiar los errores anteriores."""
    cm.ensure_case("PS-8")
    cm.update_pull_state(
        "PS-8", "1",
        element="expedientes_judiciales",
        errors=["err-1"],
    )
    updated = cm.update_pull_state("PS-8", "1", errors=[])
    assert updated["errors"] == []


def test_doc_ids_sobrescribe(cm):
    cm.ensure_case("PS-9")
    cm.update_pull_state(
        "PS-9", "1",
        element="expedientes_judiciales",
        doc_ids=["a", "b", "c"],
    )
    updated = cm.update_pull_state("PS-9", "1", doc_ids=["x"])
    assert updated["doc_ids"] == ["x"]


def test_by_carpeta_sobrescribe(cm):
    cm.ensure_case("PS-10")
    cm.update_pull_state(
        "PS-10", "1",
        element="expedientes_judiciales",
        by_carpeta={"General": 1, "Civil/Apelacion": 2},
    )
    updated = cm.update_pull_state(
        "PS-10", "1",
        by_carpeta={"Penal/Ejecucion": 5},
    )
    assert updated["by_carpeta"] == {"Penal/Ejecucion": 5}


# ---------------------------------------------------------------------------
# 3. Atomicidad de la escritura
# ---------------------------------------------------------------------------

def test_no_deja_temp_file_tras_exito(cm, tmp_casos_root):
    """Tras un update exitoso no debe quedar ``._caso.<pid>.tmp`` en disco."""
    cm.ensure_case("PS-11")
    cm.update_pull_state("PS-11", "1", element="expedientes_judiciales")

    input_dir = tmp_casos_root / "PS-11" / "00_Input"
    temps = list(input_dir.glob("._caso.*.tmp"))
    assert temps == []


def test_replace_falla_caso_md_intacto_y_temp_limpiado(cm, tmp_casos_root, monkeypatch):
    """Simulación de crash entre escritura temp y ``os.replace``.

    Si ``os.replace`` lanza, el contenido original de ``_caso.md`` debe
    sobrevivir intacto y el fichero temporal debe haberse borrado.
    """
    cm.ensure_case("PS-12")
    # Estado inicial: vinculamos un expediente con datos concretos
    cm.update_pull_state(
        "PS-12", "1",
        element="expedientes_judiciales",
        last_sync="2026-05-11T10:00:00",
        doc_ids=["original"],
    )

    caso_md = tmp_casos_root / "PS-12" / "00_Input" / "_caso.md"
    original_bytes = caso_md.read_bytes()
    input_dir = caso_md.parent

    # Patch quirúrgico: solo falla os.replace dentro de case_manager
    def fake_replace(src, dst, *args, **kwargs):
        raise OSError("simulated crash between temp write and replace")

    monkeypatch.setattr("core.case_manager.os.replace", fake_replace)

    with pytest.raises(OSError, match="simulated crash"):
        cm.update_pull_state(
            "PS-12", "1",
            last_sync="2026-05-11T11:00:00",
            doc_ids=["MUTADO"],
        )

    # Garantía 1: el _caso.md original no se ha modificado
    assert caso_md.read_bytes() == original_bytes

    # Garantía 2: ningún fichero temporal queda en disco
    temps = list(input_dir.glob("._caso.*.tmp"))
    assert temps == [], f"Temp files no limpiados: {temps}"


# ---------------------------------------------------------------------------
# 4. read_pull_state
# ---------------------------------------------------------------------------

def test_read_pull_state_caso_inexistente(cm):
    """Caso no creado → None (no lanza)."""
    assert cm.read_pull_state("NO-EXISTE", "1") is None


def test_read_pull_state_expediente_no_vinculado(cm):
    """Caso existe pero sin entry para ese expediente → None."""
    cm.ensure_case("PS-13")
    assert cm.read_pull_state("PS-13", "999") is None


def test_read_pull_state_devuelve_entry(cm):
    cm.ensure_case("PS-14")
    cm.update_pull_state(
        "PS-14", "648",
        element="expedientes_judiciales",
        last_sync="2026-05-11T12:00:00",
        documents_total_crm=5,
    )
    entry = cm.read_pull_state("PS-14", "648")
    assert entry is not None
    assert entry["id"] == "648"
    assert entry["last_sync"] == "2026-05-11T12:00:00"
    assert entry["documents_total_crm"] == 5


# ---------------------------------------------------------------------------
# 5. Múltiples expedientes y normalización de IDs
# ---------------------------------------------------------------------------

def test_multiples_expedientes_independientes(cm):
    """Dos expedientes en el mismo caso no se contaminan entre sí."""
    cm.ensure_case("PS-15")
    cm.update_pull_state(
        "PS-15", "100",
        element="expedientes_judiciales",
        doc_ids=["a", "b"],
        errors=["err-100"],
    )
    cm.update_pull_state(
        "PS-15", "200",
        element="extrajudiciales",
        doc_ids=["x"],
        errors=[],
    )

    e100 = cm.read_pull_state("PS-15", "100")
    e200 = cm.read_pull_state("PS-15", "200")

    assert e100["doc_ids"] == ["a", "b"]
    assert e100["errors"] == ["err-100"]
    assert e100["element"] == "expedientes_judiciales"

    assert e200["doc_ids"] == ["x"]
    assert e200["errors"] == []
    assert e200["element"] == "extrajudiciales"


def test_expediente_id_int_y_str_son_equivalentes(cm):
    """``update_pull_state`` con int y posterior ``read_pull_state`` con str."""
    cm.ensure_case("PS-16")
    cm.update_pull_state(
        "PS-16", 648,                         # int al crear
        element="expedientes_judiciales",
        last_sync="2026-05-11T10:00:00",
    )
    entry_via_str = cm.read_pull_state("PS-16", "648")
    entry_via_int = cm.read_pull_state("PS-16", 648)

    assert entry_via_str is not None
    assert entry_via_int is not None
    assert entry_via_str["id"] == "648"
    assert entry_via_int["id"] == "648"
    # Y un update posterior con str debe alcanzar el mismo entry
    updated = cm.update_pull_state("PS-16", "648", documents_total_crm=42)
    assert updated["documents_total_crm"] == 42
