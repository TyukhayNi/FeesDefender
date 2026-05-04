"""Tests del módulo intake_demanda — sin dependencias externas.

Cubre:
- save_file: guarda en la ruta correcta, crea la carpeta si no existe,
  sobreescribe si ya existe (idempotencia), rechaza nombres con rutas.
- extract_zip: extrae archivos planos y con subdirectorios, ignora entradas
  con path traversal, lanza BadZipFile con contenido inválido.
- list_files: devuelve lista vacía si no hay carpeta, lista archivos ordenados,
  excluye archivos de control.
- FileNotFoundError si el caso no existe al llamar save_file / extract_zip.
- ensure_case crea 05_Demanda judicial automáticamente.
"""

from __future__ import annotations

import importlib

import io
import zipfile

import pytest

from core import case_manager
from core.intake_demanda import extract_zip, list_files, save_file


# ---------------------------------------------------------------------------
# Helpers de test
# ---------------------------------------------------------------------------

def _make_zip(files: dict[str, bytes]) -> bytes:
    """Construye un ZIP en memoria con los archivos indicados {nombre: contenido}."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reload_config(tmp_casos_root, monkeypatch):
    """Aísla CASOS_ROOT y recarga módulos afectados en cada test."""
    from core import config as cfg
    importlib.reload(cfg)
    importlib.reload(case_manager)


@pytest.fixture
def caso_dem(tmp_casos_root):
    """Caso de prueba con estructura completa."""
    importlib.reload(case_manager)
    case_manager.ensure_case("DEM-2026-001", titulo="Caso demanda judicial test")
    return "DEM-2026-001"


# ---------------------------------------------------------------------------
# save_file
# ---------------------------------------------------------------------------

class TestSaveFile:
    def test_guarda_en_ruta_correcta(self, caso_dem, tmp_casos_root):
        dest = save_file(caso_dem, "demanda.pdf", b"%PDF-test")
        assert dest.exists()
        assert dest.name == "demanda.pdf"
        assert dest.parent.name == "05_Demanda judicial"
        assert dest.read_bytes() == b"%PDF-test"

    def test_crea_directorio_si_no_existe(self, caso_dem, tmp_casos_root):
        # La carpeta se crea aunque ensure_case no haya sido llamado con el nuevo subdir
        demanda_dir = tmp_casos_root / caso_dem / "00_Input" / "05_Demanda judicial"
        # Eliminar la carpeta si existe para probar que save_file la recrea
        if demanda_dir.exists():
            import shutil
            shutil.rmtree(demanda_dir)
        save_file(caso_dem, "auto.pdf", b"contenido")
        assert demanda_dir.exists()

    def test_sobreescribe_si_existe(self, caso_dem, tmp_casos_root):
        save_file(caso_dem, "doc.pdf", b"v1")
        save_file(caso_dem, "doc.pdf", b"v2-actualizado")
        dest = tmp_casos_root / caso_dem / "00_Input" / "05_Demanda judicial" / "doc.pdf"
        assert dest.read_bytes() == b"v2-actualizado"

    def test_multiples_archivos(self, caso_dem, tmp_casos_root):
        save_file(caso_dem, "demanda.pdf", b"pdf")
        save_file(caso_dem, "auto_admision.pdf", b"pdf2")
        save_file(caso_dem, "notificacion.docx", b"docx")
        archivos = list_files(caso_dem)
        nombres = [p.name for p in archivos]
        assert "demanda.pdf" in nombres
        assert "auto_admision.pdf" in nombres
        assert "notificacion.docx" in nombres

    def test_error_caso_no_existe(self, tmp_casos_root):
        with pytest.raises(FileNotFoundError, match="no existe"):
            save_file("CASO-INEXISTENTE", "demanda.pdf", b"datos")

    def test_error_nombre_con_ruta(self, caso_dem, tmp_casos_root):
        with pytest.raises(ValueError, match="no válido"):
            save_file(caso_dem, "../escape.pdf", b"datos")

    def test_error_nombre_vacio(self, caso_dem, tmp_casos_root):
        with pytest.raises(ValueError, match="no válido"):
            save_file(caso_dem, "", b"datos")


# ---------------------------------------------------------------------------
# list_files
# ---------------------------------------------------------------------------

class TestListFiles:
    def test_vacio_si_sin_carpeta(self, tmp_casos_root):
        # Caso sin carpeta 05_Demanda judicial
        importlib.reload(case_manager)
        case_manager.ensure_case("SIN-DEMANDA", titulo="Sin demanda")
        demanda_dir = tmp_casos_root / "SIN-DEMANDA" / "00_Input" / "05_Demanda judicial"
        if demanda_dir.exists():
            import shutil
            shutil.rmtree(demanda_dir)
        assert list_files("SIN-DEMANDA") == []

    def test_vacio_si_caso_sin_archivos(self, caso_dem):
        assert list_files(caso_dem) == []

    def test_lista_ordenada(self, caso_dem, tmp_casos_root):
        save_file(caso_dem, "z_ultimo.pdf", b"z")
        save_file(caso_dem, "a_primero.pdf", b"a")
        save_file(caso_dem, "m_medio.pdf", b"m")
        nombres = [p.name for p in list_files(caso_dem)]
        assert nombres == sorted(nombres)

    def test_excluye_archivos_de_control(self, caso_dem, tmp_casos_root):
        save_file(caso_dem, "real.pdf", b"pdf")
        demanda_dir = tmp_casos_root / caso_dem / "00_Input" / "05_Demanda judicial"
        # Crear archivos de control manualmente
        (demanda_dir / ".pulled").write_text("{}", encoding="utf-8")
        (demanda_dir / "_inventory.json").write_text("{}", encoding="utf-8")
        (demanda_dir / ".synced").write_text("", encoding="utf-8")
        archivos = list_files(caso_dem)
        nombres = [p.name for p in archivos]
        assert nombres == ["real.pdf"]


# ---------------------------------------------------------------------------
# extract_zip
# ---------------------------------------------------------------------------

class TestExtractZip:
    def test_extrae_archivos_planos(self, caso_dem, tmp_casos_root):
        content = _make_zip({
            "demanda.pdf": b"%PDF-1",
            "anexo_1.docx": b"PK...",
        })
        extracted = extract_zip(caso_dem, content)
        nombres = [p.name for p in extracted]
        assert "demanda.pdf" in nombres
        assert "anexo_1.docx" in nombres
        assert len(extracted) == 2

    def test_preserva_subdirectorios(self, caso_dem, tmp_casos_root):
        content = _make_zip({
            "carpeta/auto_admision.pdf": b"auto",
            "carpeta/subcarpeta/diligencia.pdf": b"diligencia",
        })
        extracted = extract_zip(caso_dem, content)
        rutas_rel = [
            str(p.relative_to(tmp_casos_root / caso_dem / "00_Input" / "05_Demanda judicial"))
            for p in extracted
        ]
        assert any("carpeta" in r for r in rutas_rel)
        assert len(extracted) == 2

    def test_contenido_correcto(self, caso_dem, tmp_casos_root):
        content = _make_zip({"demanda.pdf": b"contenido-real"})
        extracted = extract_zip(caso_dem, content)
        assert extracted[0].read_bytes() == b"contenido-real"

    def test_ignora_path_traversal(self, caso_dem, tmp_casos_root):
        # Entrada maliciosa con ../
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("../escape.txt", b"malicioso")
            zf.writestr("valido.pdf", b"ok")
        content = buf.getvalue()
        extracted = extract_zip(caso_dem, content)
        nombres = [p.name for p in extracted]
        assert "escape.txt" not in nombres
        assert "valido.pdf" in nombres

    def test_sobreescribe_existente(self, caso_dem, tmp_casos_root):
        save_file(caso_dem, "doc.pdf", b"v1")
        content = _make_zip({"doc.pdf": b"v2-desde-zip"})
        extract_zip(caso_dem, content)
        dest = tmp_casos_root / caso_dem / "00_Input" / "05_Demanda judicial" / "doc.pdf"
        assert dest.read_bytes() == b"v2-desde-zip"

    def test_error_zip_invalido(self, caso_dem):
        with pytest.raises(zipfile.BadZipFile):
            extract_zip(caso_dem, b"esto no es un zip")

    def test_error_caso_no_existe(self, tmp_casos_root):
        content = _make_zip({"f.pdf": b"x"})
        with pytest.raises(FileNotFoundError, match="no existe"):
            extract_zip("CASO-INEXISTENTE", content)

    def test_zip_vacio(self, caso_dem):
        content = _make_zip({})
        extracted = extract_zip(caso_dem, content)
        assert extracted == []

    def test_devuelve_lista_ordenada(self, caso_dem, tmp_casos_root):
        content = _make_zip({
            "z.pdf": b"z",
            "a.pdf": b"a",
            "m.pdf": b"m",
        })
        extracted = extract_zip(caso_dem, content)
        nombres = [p.name for p in extracted]
        assert nombres == sorted(nombres)


# ---------------------------------------------------------------------------
# Integración con ensure_case
# ---------------------------------------------------------------------------

class TestEnsureCaseCrea05:
    def test_ensure_case_crea_carpeta_demanda(self, tmp_casos_root):
        importlib.reload(case_manager)
        case_manager.ensure_case("NUEVO-J", titulo="Nuevo judicial")
        demanda_dir = tmp_casos_root / "NUEVO-J" / "00_Input" / "05_Demanda judicial"
        assert demanda_dir.exists(), "ensure_case debe crear 05_Demanda judicial"
