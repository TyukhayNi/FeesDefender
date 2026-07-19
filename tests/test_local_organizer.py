"""Tests del organizador local — Sprint 2.

Mockean Ollama via monkeypatch sobre ``core.llm_local`` (health_check, warmup,
complete_json) para no depender de un servicio corriendo. Aíslan tanto el
``CASOS_ROOT`` (parcheando ``caso_path``) como la carpeta de aprendizaje
despacho-wide (parcheando ``_aprendizaje_dir``) para no tocar el repo.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core import local_organizer as org
from core.utils import file_sha256, slugify, write_md


# ---------------------------------------------------------------------------
# Infraestructura de fixtures
# ---------------------------------------------------------------------------

class _FakeOllama:
    def __init__(self, responder):
        self.calls: list[str] = []
        self._responder = responder

    def complete_json(self, prompt: str, **kwargs) -> dict:
        self.calls.append(prompt)
        return self._responder(prompt)


def _nombre_en_prompt(prompt: str) -> str:
    for line in prompt.splitlines():
        if line.startswith("Nombre de fichero original"):
            return line.split(":", 1)[1].strip()
    return ""


def _crear_doc(drive: Path, anon: Path, nombre: str, *, cuerpo: str | None) -> str:
    """Crea un documento de entrada y (opcionalmente) su .md anonimizado.

    Devuelve el SHA-256 del documento de entrada.
    """
    src = drive / nombre
    src.write_bytes(f"contenido binario de {nombre}".encode("utf-8"))
    sha = file_sha256(src)
    if cuerpo is not None:
        slug = slugify(Path(nombre).stem)
        write_md(
            anon / f"{slug}.md",
            {"case_id": "X", "origen": nombre, "origen_sha256": sha, "slug": slug},
            cuerpo,
        )
    return sha


@pytest.fixture
def case(tmp_path, monkeypatch):
    """Monta un caso aislado y devuelve un helper de configuración."""
    case_id = "BaRS1 - [inmueble] - (W-02VND1) - Vuelta"
    case_dir = tmp_path / "caso"
    drive = case_dir / "00_Input" / org.DRIVE_EV_SUBDIR
    anon = case_dir / org.ANONIMIZADO_SUBDIR
    drive.mkdir(parents=True)
    anon.mkdir(parents=True)

    monkeypatch.setattr(org, "caso_path", lambda cid: case_dir)
    monkeypatch.setattr(org, "_aprendizaje_dir", lambda: tmp_path / "aprendizaje")
    monkeypatch.setattr(org.llm_local, "health_check", lambda: True)
    monkeypatch.setattr(org.llm_local, "warmup", lambda: None)

    class Ctx:
        def __init__(self):
            self.case_id = case_id
            self.case_dir = case_dir
            self.drive = drive
            self.anon = anon
            self.fake: _FakeOllama | None = None

        def set_ollama(self, responder):
            self.fake = _FakeOllama(responder)
            monkeypatch.setattr(org.llm_local, "complete_json", self.fake.complete_json)
            return self.fake

        def doc(self, nombre, cuerpo="Contrato de encargo en exclusiva."):
            return _crear_doc(self.drive, self.anon, nombre, cuerpo=cuerpo)

    return Ctx()


def _resp_activacion(prompt: str) -> dict:
    return {
        "categoria": "01. ACTIVACIÓN",
        "confianza": 0.95,
        "nombre_propuesto": "Hoja de captacion",
        "fecha_detectada": "2025-07-12",
        "fecha_fuente": "contenido",
        "subgrupo_sugerido": None,
        "descripcion_oneline": "Encargo en exclusiva",
        "justificacion_breve": "Hoja de encargo firmada",
    }


# ---------------------------------------------------------------------------
# Plan
# ---------------------------------------------------------------------------

def test_plan_creates_two_files(case):
    case.set_ollama(_resp_activacion)
    case.doc("encargo.pdf")

    res = org.planificar(case.case_id)

    prop = Path(res["plan_propuesto"])
    reorg = Path(res["plan_reorganizacion"])
    assert prop.exists() and reorg.exists()

    filas_prop = org._parse_plan_md(prop.read_text(encoding="utf-8"))
    filas_reorg = org._parse_plan_md(reorg.read_text(encoding="utf-8"))
    assert filas_prop == filas_reorg
    assert len(filas_prop) == 1
    assert filas_prop[0]["Categoría"] == "01. ACTIVACIÓN"


def test_missing_anonymized_marked_pending(case):
    fake = case.set_ollama(_resp_activacion)
    case.doc("encargo.pdf")                       # anonimizado
    case.doc("sin_ocr.pdf", cuerpo=None)          # SIN anonimizar

    res = org.planificar(case.case_id)
    filas = org._parse_plan_md(Path(res["plan_propuesto"]).read_text(encoding="utf-8"))
    por_origen = {f["Origen"]: f for f in filas}

    assert por_origen["sin_ocr.pdf"]["Estado"] == "OCR_PENDIENTE"
    assert por_origen["sin_ocr.pdf"]["Categoría"] == "08. PENDIENTE DE CLASIFICAR"
    # Ollama solo se invocó para el documento anonimizado.
    assert len(fake.calls) == 1
    assert "encargo.pdf" in fake.calls[0]


def test_image_skip_ollama(case):
    fake = case.set_ollama(_resp_activacion)
    case.doc("encargo.pdf")
    case.doc("foto1.jpg", cuerpo=None)

    res = org.planificar(case.case_id)
    filas = org._parse_plan_md(Path(res["plan_propuesto"]).read_text(encoding="utf-8"))
    por_origen = {f["Origen"]: f for f in filas}

    assert por_origen["foto1.jpg"]["Categoría"] == "00. FOTOS"
    # La imagen no pasa por Ollama; solo el pdf.
    assert len(fake.calls) == 1


# ---------------------------------------------------------------------------
# Execute
# ---------------------------------------------------------------------------

def test_execute_creates_organizado_tree(case):
    case.set_ollama(_resp_activacion)
    case.doc("encargo.pdf")
    org.planificar(case.case_id)

    res = org.ejecutar_plan(case.case_id)
    organizado = Path(res["organizado_dir"])

    assert (organizado / "01. ACTIVACIÓN").is_dir()
    assert (organizado / org.INDICE_FILE).exists()
    assert (organizado / "01. ACTIVACIÓN" / org.README_FILE).exists()


def test_execute_copies_with_renaming(case):
    case.set_ollama(_resp_activacion)
    sha = case.doc("encargo.pdf")
    org.planificar(case.case_id)
    res = org.ejecutar_plan(case.case_id)

    copias = list((Path(res["organizado_dir"]) / "01. ACTIVACIÓN").glob("*.pdf"))
    assert len(copias) == 1
    copia = copias[0]
    assert copia.name == "01 Hoja de captacion.pdf"
    assert file_sha256(copia) == sha


def test_execute_idempotent(case):
    case.set_ollama(_resp_activacion)
    case.doc("encargo.pdf")
    org.planificar(case.case_id)

    org.ejecutar_plan(case.case_id)
    res2 = org.ejecutar_plan(case.case_id)

    assert res2["acciones"] == {"SKIP_UNCHANGED": 1}


def test_correction_detected_and_logged(case):
    case.set_ollama(_resp_activacion)
    case.doc("encargo.pdf", cuerpo="Contrato de encargo en exclusiva.")
    res = org.planificar(case.case_id)

    reorg = Path(res["plan_reorganizacion"])
    texto = reorg.read_text(encoding="utf-8").replace("01. ACTIVACIÓN", "07. RECLAMACIONES")
    reorg.write_text(texto, encoding="utf-8")

    org.ejecutar_plan(case.case_id)

    import json
    corr_path = org._correcciones_path()
    assert corr_path.exists()
    entradas = [json.loads(l) for l in corr_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(entradas) == 1
    assert entradas[0]["propuesta"]["categoria"] == "01. ACTIVACIÓN"
    assert entradas[0]["decision"]["categoria"] == "07. RECLAMACIONES"


def test_subcarpetas_se_activan_por_volumen(case):
    def responder(prompt: str) -> dict:
        nombre = _nombre_en_prompt(prompt)
        base = {
            "categoria": "03. OFERTAS",
            "confianza": 0.9,
            "nombre_propuesto": f"Oferta {nombre}",
            "fecha_detectada": None,
            "fecha_fuente": "desconocida",
            "descripcion_oneline": "Oferta de buscador",
            "justificacion_breve": "Hoja de oferta",
        }
        base["subgrupo_sugerido"] = "Buscador A" if nombre in ("of0.pdf", "of1.pdf") else None
        return base

    case.set_ollama(responder)
    for i in range(6):
        case.doc(f"of{i}.pdf")

    org.planificar(case.case_id)
    res = org.ejecutar_plan(case.case_id)
    organizado = Path(res["organizado_dir"])

    assert (organizado / "03. OFERTAS" / "Buscador A").is_dir()


def test_refresh_skips_existing_sha(case):
    fake = case.set_ollama(_resp_activacion)
    case.doc("encargo.pdf")
    org.planificar(case.case_id)
    org.ejecutar_plan(case.case_id)

    # Documento nuevo tras el primer ciclo.
    case.doc("oferta_nueva.pdf")
    fake.calls.clear()
    res = org.refrescar(case.case_id)

    assert res["n_nuevos"] == 1
    # Solo se reclasifica el nuevo, no el ya auditado.
    assert len(fake.calls) == 1
    assert "oferta_nueva.pdf" in fake.calls[0]


def test_rebuild_clean_slate(case):
    case.set_ollama(_resp_activacion)
    case.doc("encargo.pdf")
    org.planificar(case.case_id)
    org.ejecutar_plan(case.case_id)

    res = org.reconstruir(case.case_id)
    copias = list((Path(res["organizado_dir"]) / "01. ACTIVACIÓN").glob("*.pdf"))
    assert len(copias) == 1


# ---------------------------------------------------------------------------
# Invariante de anonimización: _organizado/ es ignorado por el motor anon
# ---------------------------------------------------------------------------

def test_organizado_ignored_by_anonimizador(case, monkeypatch):
    case.set_ollama(_resp_activacion)
    case.doc("encargo.pdf")
    org.planificar(case.case_id)
    org.ejecutar_plan(case.case_id)

    # El motor de anonimización no debe ver nada bajo _organizado/.
    from core.anon import api as anon_api
    monkeypatch.setattr(anon_api, "caso_path", lambda cid: case.case_dir)

    input_root = case.case_dir / "00_Input"
    docs = anon_api._listar_documentos(case.case_id)
    assert all(org.ORGANIZADO_SUBDIR not in d.relative_to(input_root).parts for d in docs)
    # Sanity: el original sí se ve; la copia organizada no.
    assert any(d.name == "encargo.pdf" for d in docs)


# ---------------------------------------------------------------------------
# Precondiciones (semáforo de la UI)
# ---------------------------------------------------------------------------

def test_precondiciones_todo_ok(case):
    case.set_ollama(_resp_activacion)
    case.doc("encargo.pdf")

    pre = org.estado_precondiciones(case.case_id)

    assert pre.drive_ok and pre.anon_ok and pre.ollama_ok
    assert pre.n_docs == 1
    assert pre.listo_para_planificar
    assert not pre.plan_existe


def test_precondiciones_sin_documentos(case, monkeypatch):
    # Drive vacío: ni siquiera se debe consultar a Ollama.
    llamado = {"health": False}
    monkeypatch.setattr(
        org.llm_local, "health_check",
        lambda: llamado.__setitem__("health", True) or True,
    )

    pre = org.estado_precondiciones(case.case_id)

    assert not pre.drive_ok
    assert pre.n_docs == 0
    assert not pre.ollama_ok          # no se evalúa si falta el Drive
    assert not pre.listo_para_planificar
    assert llamado["health"] is False  # health_check NO se invocó


def test_precondiciones_sin_anonimizado(case):
    case.set_ollama(_resp_activacion)
    case.doc("sin_ocr.pdf", cuerpo=None)  # documento sin .md anonimizado

    pre = org.estado_precondiciones(case.case_id)

    assert pre.drive_ok and pre.n_docs == 1
    assert not pre.anon_ok
    assert not pre.listo_para_planificar


def test_precondiciones_ollama_caido(case, monkeypatch):
    case.set_ollama(_resp_activacion)
    case.doc("encargo.pdf")
    monkeypatch.setattr(org.llm_local, "health_check", lambda: False)

    pre = org.estado_precondiciones(case.case_id)

    assert pre.drive_ok and pre.anon_ok
    assert not pre.ollama_ok
    assert not pre.listo_para_planificar


def test_precondiciones_plan_existe_tras_planificar(case):
    case.set_ollama(_resp_activacion)
    case.doc("encargo.pdf")
    assert not org.estado_precondiciones(case.case_id).plan_existe

    org.planificar(case.case_id)

    assert org.estado_precondiciones(case.case_id).plan_existe
