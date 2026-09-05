"""MEJORAS #149 — un fichero es de protocolo por DÓNDE está, no por cómo se llama.

Diseño: `docs/superpowers/specs/2026-09-05-ficheros-de-protocolo-por-ubicacion-design.md`
rev. 2. Los números T* son los de su §5. Los positivos (T8, T10, T12) comprueban que lo que el
repo escribe queda fuera del inventario probatorio; los negativos (T9, T11) que un homónimo
del cliente en cualquier otro sitio ENTRA. T7 no lee el registro: EJECUTA cada escritor del
repo sobre un caso temporal y exige que el inventario de la sala de máquina salga vacío.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

from core.intake_control import (
    DIRECTORIOS,
    ENTREGA,
    PATRON_LOTE,
    RAIZ,
    RAIZ_PREFIJOS,
    es_fichero_de_protocolo,
    nombres_registrados,
)

REPO = Path(__file__).resolve().parent.parent
LOTE = "2026-09-05_email_01"


# ── T8 (+): lo que el repo escribe, donde lo escribe ───────────────────────────────────────

@pytest.mark.parametrize("rel", sorted(RAIZ))
def test_t8_raiz_es_protocolo(rel):
    assert es_fichero_de_protocolo(rel) is True


@pytest.mark.parametrize("rel", [
    f"{LOTE}/_manifiesto.yaml", "01_Drive EV/.pulled", "sudespacho_648/.pulled",
    "drive/.synced", "03_Email/_exported_ids.json", "03_Email/_resolved_links.json",
])
def test_t8_entrega_en_su_directorio_es_protocolo(rel):
    assert es_fichero_de_protocolo(rel) is True


# ── T9 (−): el mismo nombre en otro sitio es documento ─────────────────────────────────────

@pytest.mark.parametrize("rel", [
    "CarpetaRara/_manifiesto.yaml",      # cambia respecto a hoy, y es lo querido
    "01_Drive EV/_manifiesto.yaml",      # ídem
    "01_Drive EV/.synced",               # ídem: `.synced` lo escribe core/sync en `drive/`
    f"{LOTE}/.pulled",                   # ídem: ningún escritor lo pone en un lote
    "04_Manual/_inventory.json",         # ídem
    "01_Drive EV/OFERTAS/.pulled",
    "01_Drive EV/.Oferta firmada.pdf",   # ficheros de E&V con punto inicial existen
    "_nota_suelta.pdf",                  # `_` inicial en la raíz sin estar en RAIZ: manual
    f"{LOTE}/x/_manifiesto.yaml",        # T2: el manifiesto ANIDADO es documento
    f"{LOTE}/adjuntos/_ficha_crm.yaml",  # T1: el adjunto homónimo
    "01_Drive EV/_inventory.json",       # fichero de E&V homónimo: entra en el ledger
    "sub/_caso.md", "a/b/_caso.md",
])
def test_t9_homonimo_fuera_de_su_sitio_es_documento(rel):
    assert es_fichero_de_protocolo(rel) is False


# ── T10: temporales de escritura atómica, solo en la raíz ──────────────────────────────────

@pytest.mark.parametrize("nombre", [
    "_caso.md", "._caso.4242.tmp", ".apertura_v1.x.tmp", "._intake_hashes.4242.tmp",
    "._intake_hashes.json.4242.tmp", "._ocurrencias_crm.json.4242.tmp",
])
def test_t10_temporales_en_la_raiz_son_protocolo_y_a_profundidad_3_no(nombre):
    assert es_fichero_de_protocolo(nombre) is True
    assert es_fichero_de_protocolo(f"a/b/{nombre}") is False


def test_t10_los_prefijos_son_los_que_los_escritores_usan_de_verdad():
    """Los prefijos del registro se contrastan con el CÓDIGO de cada escritor, no con
    su docstring (R1/H-05 del diseño)."""
    fuentes = {
        ".apertura_v1.": REPO / "core" / "apertura_v1_estado.py",
        "._caso.": REPO / "core" / "case_manager.py",
        "._intake_hashes.": REPO / "core" / "intake_manifest.py",
        "._ocurrencias_crm.json.": REPO / "core" / "ocurrencias_crm.py",
    }
    assert set(fuentes) == set(RAIZ_PREFIJOS)
    for pre, fichero in fuentes.items():
        txt = fichero.read_text(encoding="utf-8")
        literal = pre if pre != "._ocurrencias_crm.json." else '._{_FILENAME}.'
        assert literal in txt, f"{fichero.name} ya no escribe temporales con prefijo {pre!r}"


# ── T11: rutas que no son relativas sanas ──────────────────────────────────────────────────

@pytest.mark.parametrize("rel", ["../_caso.md", "C:/x/_caso.md", "/tmp/_caso.md", "",
                                 "a/../_caso.md",
                                 # `..` DENTRO de un directorio de protocolo: la ruta resuelve
                                 # a `01_Drive EV/oferta.pdf`, un documento. Sin la guarda
                                 # de `..` el prefijo `_organizado/` casaba y lo escondía —
                                 # el mutante «`..` aceptado» sobrevivió a los casos de arriba.
                                 "01_Drive EV/_organizado/../oferta.pdf"])
def test_t11_ruta_no_relativa_no_es_protocolo(rel):
    assert es_fichero_de_protocolo(rel) is False


def test_t11_separador_windows_equivale_al_posix():
    assert es_fichero_de_protocolo("01_Drive EV\\.pulled") is True
    assert es_fichero_de_protocolo("./_caso.md") is True


def test_nombre_y_directorio_sin_distinguir_mayusculas():
    """La rev. 2 decía «el directorio, tal como lo escribe el repo». La R2 (H-03) lo refutó
    con el escritor real en Windows: la identidad que cuenta es la física."""
    assert es_fichero_de_protocolo("_CASO.MD") is True          # mismo fichero en Windows
    assert es_fichero_de_protocolo("01_drive ev/.pulled") is True   # misma carpeta en Windows


# ── T12: directorios derivados enteros ─────────────────────────────────────────────────────

def test_t12_organizado_entero_es_protocolo():
    assert DIRECTORIOS == ("01_Drive EV/_organizado",)
    assert es_fichero_de_protocolo("01_Drive EV/_organizado/_audit.jsonl") is True
    assert es_fichero_de_protocolo("01_Drive EV/_organizado/Ofertas/copia.pdf") is True
    assert es_fichero_de_protocolo("01_Drive EV/_organizado") is False  # el dir en sí no es fichero


# ── El registro por nombre que queda es DERIVADO y nadie clasifica con él (T14) ────────────

def test_config_deriva_del_registro():
    from core import config
    assert config.INTAKE_CONTROL_FILES == nombres_registrados()
    assert config.INTAKE_CONTROL_PREFIXES == RAIZ_PREFIJOS
    assert {"_intake_hashes.json", "_manifiesto.yaml", "_ficha_crm.yaml",
            "_ocurrencias_crm.json", "_caso.md", "_intake_log.jsonl"} <= nombres_registrados()


def test_t14_ningun_modulo_de_produccion_clasifica_por_nombre():
    """`git grep` en Python: los únicos lectores de `INTAKE_CONTROL_FILES` /
    `INTAKE_CONTROL_PREFIXES` en producción son `core/config.py` (que los define). Un alias
    por basename que sobreviva «para los guards» es el proxy que causó la reversión del
    2026-09-04."""
    import ast

    nombres = {"INTAKE_CONTROL_FILES", "INTAKE_CONTROL_PREFIXES", "CONTROL_FILES",
               "_CONTROL_FILES"}

    def _lee(arbol: ast.AST) -> bool:
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Name) and nodo.id in nombres:
                return True
            if isinstance(nodo, ast.Attribute) and nodo.attr in nombres:
                return True
            if isinstance(nodo, ast.ImportFrom) and any(a.name in nombres for a in nodo.names):
                return True
        return False

    lectores = []
    raices = [REPO / "core", REPO / "scripts", REPO / "plugins", REPO / "streamlit_app.py"]
    for raiz in raices:
        ficheros = [raiz] if raiz.is_file() else raiz.rglob("*.py")
        for f in ficheros:
            if "__pycache__" in f.parts:
                continue
            # por AST, no por texto: un comentario que cite el nombre no es un lector
            if _lee(ast.parse(f.read_text(encoding="utf-8", errors="replace"))):
                lectores.append(f.relative_to(REPO).as_posix())
    # `migrate_05crm_buckets` tiene su propio `_CONTROL_FILES` de tres nombres: script puntual
    # fuera del alcance del diseño (§3.5), y no lee el registro.
    assert set(lectores) <= {"core/config.py", "scripts/migrate_05crm_buckets.py"}, lectores


def test_los_alias_por_basename_ya_no_existen():
    from core import intake_drive, intake_manual, inventory
    assert not hasattr(intake_drive, "CONTROL_FILES")
    assert not hasattr(inventory, "_CONTROL_FILES")
    assert not hasattr(intake_manual, "_CONTROL_FILES")


def test_patron_lote_es_el_de_intake_lotes():
    from core import intake_lotes
    assert intake_lotes.PATRON_LOTE is PATRON_LOTE
    assert any(pat is PATRON_LOTE for pat, _ in ENTREGA)


# ── T1 y T3: contra un caso real en disco, por los cuatro consumidores ─────────────────────

def _caso(case_id: str):
    from core import case_manager, config
    case_dir = case_manager.ensure_case(case_id, titulo="protocolo por ubicación")
    return case_dir, config.caso_path(case_id) / "00_Input"


def test_t1_el_adjunto_homonimo_entra_y_el_de_la_raiz_no(tmp_casos_root):
    from core import inventory, intake_lotes, sala_maquina
    from scripts.abrir_caso import hash_tree_local

    case_dir, inp = _caso("EV-149-T1")
    lote = inp / LOTE
    (lote / "adjuntos").mkdir(parents=True)
    (lote / "adjuntos" / "_ficha_crm.yaml").write_text("adjunto: del cliente\n", encoding="utf-8")
    (lote / "2026-09-01_asunto.eml").write_bytes(b"From: a@example.invalid\n\nhola")
    (inp / "_ficha_crm.yaml").write_text("ficha: del despacho\n", encoding="utf-8")
    drive = inp / "01_Drive EV"
    (drive / "sub").mkdir(parents=True)
    (drive / "sub" / "_ficha_crm.yaml").write_text("de E&V\n", encoding="utf-8")
    (drive / ".pulled").write_text("{}", encoding="utf-8")

    adjunto = f"{LOTE}/adjuntos/_ficha_crm.yaml"
    # inventory.scan: `.yaml` no es extensión relevante → va a `skipped`, pero NO desaparece
    data = json.loads(inventory.scan("EV-149-T1").read_text(encoding="utf-8"))
    vistos = {f["rel_path"] for f in data["files"]} | set(data["skipped"])
    assert adjunto in vistos and "_ficha_crm.yaml" not in vistos
    # albarán del lote
    assert "adjuntos/_ficha_crm.yaml" in {i.relpath for i in intake_lotes.items_desde_disco(lote)}
    # inventario probatorio de la sala de máquina
    rels = {d["rel_path"] for d in sala_maquina.inventariar(case_dir)}
    assert adjunto in rels and "_ficha_crm.yaml" not in rels
    assert "01_Drive EV/sub/_ficha_crm.yaml" in rels and "01_Drive EV/.pulled" not in rels
    # ledger forense del pull
    hashes = hash_tree_local(drive, prefijo="01_Drive EV")
    assert "01_Drive EV/sub/_ficha_crm.yaml" in hashes and "01_Drive EV/.pulled" not in hashes


def test_t3_inventario_literal_con_los_cuatro_de_149_en_la_raiz(tmp_casos_root):
    """El oráculo es el conjunto LITERAL de rutas documentales del fixture, no «ninguno es de
    protocolo según la función bajo prueba» (R1/H-11 del diseño: eso era circular)."""
    from core import intake_lotes, sala_maquina

    case_dir, inp = _caso("EV-149-T3")
    lote = inp / LOTE
    lote.mkdir()
    (lote / "2026-09-01_asunto.eml").write_bytes(b"x")
    intake_lotes.escribir_manifiesto(lote, fuente="email", fecha_intake="2026-09-05",
                                     origen="test", items=intake_lotes.items_desde_disco(lote))
    for nombre in ("_intake_hashes.json", "_ficha_crm.yaml", "_ocurrencias_crm.json",
                   "_inventory.json"):
        (inp / nombre).write_text("{}", encoding="utf-8")
    assert (inp / "_caso.md").is_file()          # lo escribió ensure_case
    assert (lote / "_manifiesto.yaml").is_file()

    rels = {d["rel_path"] for d in sala_maquina.inventariar(case_dir)}
    assert rels == {f"{LOTE}/2026-09-01_asunto.eml"}


# ── T7: EJECUTAR cada escritor del repo y exigir inventario vacío ──────────────────────────

def _escribir_todo_el_protocolo(case_id: str, case_dir: Path, inp: Path) -> None:
    from core import apertura_v1_estado, email_export, intake_drive, intake_log, intake_lotes
    from core import inventory, sync
    from core.intake_manifest import IntakeManifest
    from core.ocurrencias_crm import RegistroOcurrencias

    intake_log.append_event(case_id, "upload_manual", details={"test": "t7"})  # _intake_log.jsonl
    IntakeManifest(case_id).save()                                      # _intake_hashes.json
    RegistroOcurrencias(case_id).save()                                 # _ocurrencias_crm.json
    apertura_v1_estado.abrir(case_dir, ronda_id="r1", ahora="2026-09-05T10:00:00")
    lote = inp / LOTE
    lote.mkdir(exist_ok=True)
    intake_lotes.escribir_manifiesto(lote, fuente="email", fecha_intake="2026-09-05",
                                     origen="test", items=[])          # <lote>/_manifiesto.yaml
    email_export._save_export_index(inp, {})                            # _exported_ids.json
    email_export._save_resolved_links(inp, {})                          # _resolved_links.json
    (inp / "_ficha_crm.yaml").write_text("contraparte: X\n", encoding="utf-8")  # §9 runbook
    drive = inp / "01_Drive EV"
    drive.mkdir(exist_ok=True)
    (drive / intake_drive._PULL_MARKER).write_text("{}", encoding="utf-8")   # marcador pull
    (inp / "drive").mkdir(exist_ok=True)
    (inp / "drive" / sync._SYNC_MARKER).write_text("{}", encoding="utf-8")   # marcador sync
    inventory.scan(case_id)                                             # _inventory.json


def test_t7_todo_lo_que_el_repo_escribe_queda_fuera_del_inventario(tmp_casos_root):
    from core import sala_maquina

    case_dir, inp = _caso("EV-149-T7")
    _escribir_todo_el_protocolo("EV-149-T7", case_dir, inp)
    escritos = sorted(p.relative_to(inp).as_posix() for p in inp.rglob("*") if p.is_file())
    assert len(escritos) >= 10, escritos     # el fixture escribió de verdad
    assert sala_maquina.inventariar(case_dir) == []


def test_t7_un_fallo_entre_el_temporal_y_el_replace_no_deja_documento(tmp_casos_root, monkeypatch):
    """Los tres escritores atómicos de la raíz limpian su temporal al fallar, y si no
    pudieran (muerte del proceso) el nombre del huérfano está en `RAIZ_PREFIJOS` (T10). Aquí
    se inyecta el fallo en `os.replace` y se exige que, pase lo que pase con el temporal, el
    inventario probatorio siga vacío."""
    from core import apertura_v1_estado, sala_maquina
    from core.intake_manifest import IntakeManifest
    from core.ocurrencias_crm import RegistroOcurrencias

    case_dir, inp = _caso("EV-149-T7b")

    def replace_que_muere(src, dst, *a, **k):
        raise OSError("disco lleno (inyectado)")

    monkeypatch.setattr(os, "replace", replace_que_muere)
    for escritor in (
        lambda: IntakeManifest("EV-149-T7b").save(),
        lambda: RegistroOcurrencias("EV-149-T7b").save(),
        lambda: apertura_v1_estado.abrir(case_dir, ronda_id="r", ahora="2026-09-05T10:00:00"),
    ):
        with pytest.raises(Exception):
            escritor()
    monkeypatch.undo()
    # y un huérfano que sí quedara en disco, con el prefijo real de cada escritor:
    for pre in RAIZ_PREFIJOS:
        (inp / f"{pre}4242.tmp").write_text("", encoding="utf-8")
    assert sala_maquina.inventariar(case_dir) == []


# ── R2 de MEJORAS #149 sobre el diff: H-03 (caja del directorio) y H-05 (temporal real) ───────

def test_r2_h03_el_directorio_tampoco_distingue_mayusculas():
    """La rev. 2 comparaba el directorio tal como lo escribe el repo. En Windows, si existe
    `01_drive ev/`, el escritor que pide `01_Drive EV/.pulled` escribe DENTRO de aquélla y
    `rglob` devuelve la caja almacenada: el marcador recién escrito pasaba por documento."""
    assert es_fichero_de_protocolo("01_drive ev/.pulled") is True
    assert es_fichero_de_protocolo("03_email/_exported_ids.json") is True
    assert es_fichero_de_protocolo("01_DRIVE EV/_ORGANIZADO/copia.pdf") is True
    assert es_fichero_de_protocolo("2026-09-05_EMAIL_01/_manifiesto.yaml") is False  # PATRON_LOTE es literal: ese lote no lo escribe nadie


def test_r2_h03_el_marcador_del_pull_en_carpeta_preexistente_con_otra_caja_no_es_documento(tmp_casos_root):
    """Reproducción del revisor con el escritor REAL: se precrea `01_drive ev/` y el pull
    escribe su marcador pidiendo `01_Drive EV/.pulled`. En Windows es la misma carpeta."""
    from core import intake_drive, sala_maquina

    case_dir, inp = _caso("EV-149-H03")
    (inp / "01_drive ev").mkdir()
    marker = inp / "01_Drive EV" / intake_drive._PULL_MARKER
    marker.parent.mkdir(exist_ok=True)               # en Windows resuelve a `01_drive ev/`
    marker.write_text("{}", encoding="utf-8")
    fisicos = sorted(p.relative_to(inp).as_posix() for p in inp.rglob("*") if p.is_file()
                     and p.name == intake_drive._PULL_MARKER)
    assert fisicos, "el marcador no se escribió"
    assert sala_maquina.inventariar(case_dir) == []


def test_r2_h05_una_descarga_interrumpida_no_deja_su_temporal(tmp_casos_root, monkeypatch):
    """`sync_sudespacho.pull_expediente` escribe `sudespacho_<id>.tmp` en el destino y lo
    renombra al terminar. Solo lo limpiaba ante `SudespachoError`; un `OSError`, un Ctrl-C o
    un kill a mitad lo dejaban en `00_Input/sudespacho_<n>/<carpeta>/` y el parcial —escrito
    por el repo, no por el cliente— entraba en el inventario probatorio."""
    from core import case_manager, sala_maquina, sync_sudespacho
    from core.sync_sudespacho import GdocuDocInfo, SudespachoClient, SudespachoConfig

    case_dir = case_manager.ensure_case("EV-149-H05")
    doc = GdocuDocInfo(doc_id="17", filename="Demanda.pdf", id_carpeta="306",
                       id_carpeta_label="civil", mime="application/pdf", size=3, raw={})
    monkeypatch.setattr(SudespachoClient, "list_gdocu_docs_rest", lambda self, exp_id, **kw: [doc])

    def descarga_que_muere(self, doc_id, exp_id, target_path, **kw):
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(b"par")               # bytes parciales…
        raise OSError("conexión cortada a mitad (inyectado)")   # …y muere sin SudespachoError

    monkeypatch.setattr(SudespachoClient, "download_document_rest", descarga_que_muere)
    monkeypatch.setattr(SudespachoConfig, "from_env",
                        classmethod(lambda cls: SudespachoConfig(base_url="https://x", api_key="k")))
    with pytest.raises(OSError):
        sync_sudespacho.pull_expediente("EV-149-H05", "648")
    temporales = [p for p in (case_dir / "00_Input").rglob("*.tmp")]
    assert temporales == []
    assert sala_maquina.inventariar(case_dir) == []
