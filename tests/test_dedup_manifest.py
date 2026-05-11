"""Tests dedicados v2 — paso 8 del refactor intake v2.

Módulo bajo test: ``core.intake_manifest`` (M9 — dedup cross-source SHA-256).

Cubre:

- Helpers de hashing (``compute_sha256`` / ``compute_sha256_bytes``).
- ``manifest_path`` no crea archivo.
- ``load`` resistente: manifest inexistente o corrupto → ``data = {}``.
- ``register`` — hash nuevo / duplicado misma ruta / duplicado ruta
  distinta / re-llamada / detalles extra de alias / validación /
  normalización backslash.
- ``reconcile`` — primary existe / primary perdido con alias / primary
  perdido sin alias.
- Context manager — save automático con cambios, NO save con excepción,
  NO save sin cambios.
- Atomicidad del ``save`` (sin temp files huérfanos).
- ``lookup`` + ``all_paths``.
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
def im(tmp_casos_root):
    """``core.intake_manifest`` recargado tras el reload de config."""
    from core import intake_manifest as _im

    importlib.reload(_im)
    return _im


@pytest.fixture
def cm(tmp_casos_root):
    from core import case_manager as _cm

    importlib.reload(_cm)
    return _cm


# ---------------------------------------------------------------------------
# 1. Helpers de hashing
# ---------------------------------------------------------------------------

def test_compute_sha256_bytes_matchea_hashlib(im):
    data = b"contenido de prueba"
    assert im.compute_sha256_bytes(data) == hashlib.sha256(data).hexdigest()


def test_compute_sha256_archivo_mayor_que_chunk(im, tmp_path):
    """Archivo > 64 KiB: valida que el bucle de chunking produce el hash correcto."""
    big = b"X" * (64 * 1024 + 17)   # 65553 bytes — fuerza al menos 2 chunks
    f = tmp_path / "big.bin"
    f.write_bytes(big)
    assert im.compute_sha256(f) == hashlib.sha256(big).hexdigest()


# ---------------------------------------------------------------------------
# 2. manifest_path
# ---------------------------------------------------------------------------

def test_manifest_path_no_crea_archivo(im, cm, tmp_casos_root):
    cm.ensure_case("MAN-1")
    path = im.manifest_path("MAN-1")
    assert path == tmp_casos_root / "MAN-1" / "00_Input" / "_intake_hashes.json"
    assert not path.exists()


# ---------------------------------------------------------------------------
# 3. load — resistencia a manifest inexistente o corrupto
# ---------------------------------------------------------------------------

def test_load_manifest_inexistente_da_dict_vacio(im, cm):
    cm.ensure_case("MAN-2")
    manifest = im.IntakeManifest("MAN-2")
    manifest.load()
    assert manifest.data == {}


def test_load_manifest_corrupto_da_dict_vacio_sin_error(im, cm):
    """JSON inválido (texto basura) → load() debe NO levantar y dejar data={}.

    El docstring del módulo lo exige: "Manifest corrupto: empezar vacío,
    dejar que reconcile() recupere".
    """
    cm.ensure_case("MAN-3")
    im.manifest_path("MAN-3").write_text("esto no es json válido { ][",
                                          encoding="utf-8")

    manifest = im.IntakeManifest("MAN-3")
    manifest.load()
    assert manifest.data == {}


def test_load_manifest_valido_recupera_entries(im, cm):
    cm.ensure_case("MAN-4")
    payload = {
        "sha-aaa": {"primary_path": "01_Drive EV/x.pdf", "aliases": []},
        "sha-bbb": {"primary_path": "04_Manual/y.pdf",  "aliases": []},
    }
    im.manifest_path("MAN-4").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8",
    )

    manifest = im.IntakeManifest("MAN-4")
    manifest.load()
    assert manifest.data == payload


# ---------------------------------------------------------------------------
# 4. register — hash nuevo
# ---------------------------------------------------------------------------

def test_register_hash_nuevo_devuelve_write(im, cm):
    cm.ensure_case("MAN-5")
    manifest = im.IntakeManifest("MAN-5")
    manifest.load()

    action, primary = manifest.register(
        "sha-1", "05_CRM/Civil/Apelacion/x.pdf", source="crm",
    )

    assert action == "write"
    assert primary == "05_CRM/Civil/Apelacion/x.pdf"
    entry = manifest.data["sha-1"]
    assert entry["primary_path"] == "05_CRM/Civil/Apelacion/x.pdf"
    assert entry["aliases"] == []
    assert manifest._dirty is True


# ---------------------------------------------------------------------------
# 5. register — hash duplicado
# ---------------------------------------------------------------------------

def test_register_duplicado_misma_ruta_es_noop(im, cm):
    """Misma ruta lógica → ("skip", primary), sin alias añadido."""
    cm.ensure_case("MAN-6")
    manifest = im.IntakeManifest("MAN-6")
    manifest.load()

    manifest.register("sha-1", "04_Manual/x.pdf", source="manual")
    manifest._dirty = False   # reset para verificar el noop

    action, primary = manifest.register(
        "sha-1", "04_Manual/x.pdf", source="manual",
    )

    assert action == "skip"
    assert primary == "04_Manual/x.pdf"
    assert manifest.data["sha-1"]["aliases"] == []
    assert manifest._dirty is False   # no se ha mutado nada


def test_register_duplicado_ruta_distinta_anade_alias(im, cm):
    """Mismo hash, ruta lógica distinta → alias añadido con metadatos."""
    cm.ensure_case("MAN-7")
    manifest = im.IntakeManifest("MAN-7")
    manifest.load()

    manifest.register("sha-1", "01_Drive EV/contrato.pdf", source="drive_ev")
    action, primary = manifest.register(
        "sha-1",
        "05_CRM/Civil/1ª Instancia/Declarativo/Demanda/contrato.pdf",
        source="crm",
        expediente_id="657",
        doc_id="40054",
    )

    assert action == "skip"
    assert primary == "01_Drive EV/contrato.pdf"
    aliases = manifest.data["sha-1"]["aliases"]
    assert len(aliases) == 1
    alias = aliases[0]
    assert alias["path"] == \
        "05_CRM/Civil/1ª Instancia/Declarativo/Demanda/contrato.pdf"
    assert alias["source"] == "crm"
    assert alias["expediente_id"] == "657"
    assert alias["doc_id"] == "40054"
    assert "added_at" in alias and alias["added_at"]


def test_register_alias_existente_no_se_duplica(im, cm):
    """Re-llamar register con misma ruta de alias ya presente no duplica."""
    cm.ensure_case("MAN-8")
    manifest = im.IntakeManifest("MAN-8")
    manifest.load()

    manifest.register("sha-1", "01_Drive EV/x.pdf", source="drive_ev")
    manifest.register("sha-1", "05_CRM/General/x.pdf", source="crm")
    manifest.register("sha-1", "05_CRM/General/x.pdf", source="crm")   # repetida

    aliases = manifest.data["sha-1"]["aliases"]
    assert len(aliases) == 1
    assert aliases[0]["path"] == "05_CRM/General/x.pdf"


# ---------------------------------------------------------------------------
# 6. register — validación y normalización
# ---------------------------------------------------------------------------

def test_register_sha_vacio_lanza_value_error(im, cm):
    cm.ensure_case("MAN-9")
    manifest = im.IntakeManifest("MAN-9")
    manifest.load()
    with pytest.raises(ValueError, match="sha256 requerido"):
        manifest.register("", "04_Manual/x.pdf", source="manual")


def test_register_rel_path_vacio_lanza_value_error(im, cm):
    cm.ensure_case("MAN-10")
    manifest = im.IntakeManifest("MAN-10")
    manifest.load()
    with pytest.raises(ValueError, match="relative_path requerido"):
        manifest.register("sha-x", "", source="manual")


def test_register_normaliza_backslash_a_forward_slash(im, cm):
    """Paths con ``\\`` se persisten como ``/`` (D11)."""
    cm.ensure_case("MAN-11")
    manifest = im.IntakeManifest("MAN-11")
    manifest.load()

    action, primary = manifest.register(
        "sha-1", "05_CRM\\Civil\\Apelacion\\x.pdf", source="crm",
    )
    assert action == "write"
    assert primary == "05_CRM/Civil/Apelacion/x.pdf"
    assert manifest.data["sha-1"]["primary_path"] == \
        "05_CRM/Civil/Apelacion/x.pdf"


# ---------------------------------------------------------------------------
# 7. reconcile — escenarios M9-Q4
# ---------------------------------------------------------------------------

def _write_under_input(case_id, rel_path, content, tmp_casos_root):
    """Crea un fichero físico bajo ``<case>/00_Input/<rel_path>``."""
    target = tmp_casos_root / case_id / "00_Input" / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return target


def test_reconcile_primary_existe_no_promueve(im, cm, tmp_casos_root):
    cm.ensure_case("MAN-12")
    _write_under_input("MAN-12", "01_Drive EV/x.pdf", b"data", tmp_casos_root)

    manifest = im.IntakeManifest("MAN-12")
    manifest.load()
    manifest.register("sha-1", "01_Drive EV/x.pdf", source="drive_ev")
    manifest._dirty = False  # reset para detectar mutación de reconcile

    promoted = manifest.reconcile()

    assert promoted == 0
    assert manifest.data["sha-1"]["primary_path"] == "01_Drive EV/x.pdf"
    assert manifest._dirty is False


def test_reconcile_primary_perdido_promueve_alias_presente(
    im, cm, tmp_casos_root,
):
    """M9-Q4: primary borrado del disco → alias con fichero presente se promueve."""
    cm.ensure_case("MAN-13")

    # Solo el alias existe físicamente; el primary se "perdió"
    _write_under_input(
        "MAN-13", "05_CRM/Civil/Apelacion/x.pdf", b"data", tmp_casos_root,
    )

    manifest = im.IntakeManifest("MAN-13")
    manifest.load()
    manifest.register("sha-1", "01_Drive EV/x.pdf", source="drive_ev")
    manifest.register(
        "sha-1", "05_CRM/Civil/Apelacion/x.pdf",
        source="crm", expediente_id="657",
    )

    promoted = manifest.reconcile()

    assert promoted == 1
    entry = manifest.data["sha-1"]
    assert entry["primary_path"] == "05_CRM/Civil/Apelacion/x.pdf"
    assert entry["aliases"] == []   # el alias promovido se removió de la lista
    assert manifest._dirty is True


def test_reconcile_primary_y_aliases_perdidos_conserva_entry(
    im, cm,
):
    """Sin ningún fichero presente → no promueve, entry se mantiene intacto.

    El siguiente pull puede re-descargar el documento y completar el primary.
    """
    cm.ensure_case("MAN-14")
    manifest = im.IntakeManifest("MAN-14")
    manifest.load()
    manifest.register("sha-1", "01_Drive EV/x.pdf", source="drive_ev")
    manifest.register("sha-1", "05_CRM/General/x.pdf", source="crm")
    manifest._dirty = False

    promoted = manifest.reconcile()

    assert promoted == 0
    entry = manifest.data["sha-1"]
    assert entry["primary_path"] == "01_Drive EV/x.pdf"
    assert len(entry["aliases"]) == 1
    assert manifest._dirty is False


# ---------------------------------------------------------------------------
# 8. Context manager — save automático
# ---------------------------------------------------------------------------

def test_context_manager_save_con_cambios(im, cm, tmp_casos_root):
    cm.ensure_case("MAN-15")
    with im.IntakeManifest("MAN-15") as manifest:
        manifest.register("sha-a", "04_Manual/a.pdf", source="manual")
        manifest.register("sha-b", "04_Manual/b.pdf", source="manual")

    # Reabrir: persistencia OK
    persisted = im.IntakeManifest("MAN-15")
    persisted.load()
    assert set(persisted.data.keys()) == {"sha-a", "sha-b"}


def test_context_manager_no_save_con_excepcion(im, cm, tmp_casos_root):
    """Si hay excepción dentro del ``with``, NO se guarda — preserva estado previo."""
    cm.ensure_case("MAN-16")

    # Estado previo en disco con 1 entry
    previous = {"sha-old": {"primary_path": "04_Manual/old.pdf", "aliases": []}}
    im.manifest_path("MAN-16").write_text(
        json.dumps(previous, ensure_ascii=False), encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="boom"):
        with im.IntakeManifest("MAN-16") as manifest:
            manifest.register("sha-new", "04_Manual/new.pdf", source="manual")
            raise RuntimeError("boom")

    # Re-leer: el "sha-new" NO se ha persistido; el "sha-old" sigue intacto
    persisted = im.IntakeManifest("MAN-16")
    persisted.load()
    assert persisted.data == previous


def test_context_manager_sin_cambios_no_crea_manifest(im, cm):
    """``with`` sin operaciones de escritura → no se crea el manifest en disco."""
    cm.ensure_case("MAN-17")
    with im.IntakeManifest("MAN-17") as manifest:
        # Solo lookup — no muta
        assert manifest.lookup("sha-inexistente") is None

    assert not im.manifest_path("MAN-17").exists()


# ---------------------------------------------------------------------------
# 9. Atomicidad de save
# ---------------------------------------------------------------------------

def test_save_no_deja_temp_files(im, cm, tmp_casos_root):
    cm.ensure_case("MAN-18")
    manifest = im.IntakeManifest("MAN-18")
    manifest.load()
    manifest.register("sha-1", "04_Manual/x.pdf", source="manual")
    manifest.save()

    input_dir = tmp_casos_root / "MAN-18" / "00_Input"
    temps = list(input_dir.glob("._intake_hashes.*.tmp"))
    assert temps == []
    assert im.manifest_path("MAN-18").is_file()


# ---------------------------------------------------------------------------
# 10. lookup + all_paths
# ---------------------------------------------------------------------------

def test_lookup_y_all_paths(im, cm):
    cm.ensure_case("MAN-19")
    manifest = im.IntakeManifest("MAN-19")
    manifest.load()

    manifest.register("sha-1", "01_Drive EV/x.pdf", source="drive_ev")
    manifest.register("sha-1", "05_CRM/General/x.pdf", source="crm")
    manifest.register("sha-2", "04_Manual/y.pdf", source="manual")

    # lookup devuelve el entry vivo, no copia defensiva (documentado)
    e1 = manifest.lookup("sha-1")
    assert e1 is not None
    assert e1["primary_path"] == "01_Drive EV/x.pdf"
    assert len(e1["aliases"]) == 1

    # Hash inexistente → None
    assert manifest.lookup("sha-no-existe") is None

    # all_paths combina primary + aliases, sin duplicados
    paths = manifest.all_paths()
    assert paths == {
        "01_Drive EV/x.pdf",
        "05_CRM/General/x.pdf",
        "04_Manual/y.pdf",
    }
