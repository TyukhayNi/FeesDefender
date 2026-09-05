"""Tests del módulo intake_manual — sin dependencias externas.

Cubre:

- save_file: guarda en la ruta correcta (``04_Manual/``), crea la carpeta
  si no existe, sobreescribe si ya existe (idempotencia), rechaza nombres
  con rutas.
- extract_zip: extrae archivos planos y con subdirectorios, ignora entradas
  con path traversal, lanza BadZipFile con contenido inválido.
- list_files: devuelve lista vacía si no hay carpeta, lista archivos
  ordenados, excluye archivos de control.
- FileNotFoundError si el caso no existe al llamar save_file / extract_zip.
- ensure_case crea ``04_Manual`` automáticamente.

Histórico: tests heredados de ``test_intake_demanda``, adaptados al
refactor intake v2 (destino ``04_Manual/`` en lugar de
``05_Demanda judicial/``).
"""

from __future__ import annotations

import importlib

import io
import zipfile

import pytest

from core import case_manager
from core.intake_manual import extract_zip, list_files, save_file


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
def caso_man(tmp_casos_root):
    """Caso de prueba con estructura completa."""
    importlib.reload(case_manager)
    case_manager.ensure_case("MAN-2026-001", titulo="Caso intake manual test")
    return "MAN-2026-001"


# ---------------------------------------------------------------------------
# save_file
# ---------------------------------------------------------------------------

class TestSaveFile:
    def test_guarda_en_ruta_correcta(self, caso_man, tmp_casos_root):
        from core.intake_lotes import PATRON_LOTE
        dest = save_file(caso_man, "demanda.pdf", b"%PDF-test")
        assert dest.exists()
        assert dest.name == "demanda.pdf"
        assert PATRON_LOTE.match(dest.parent.name).group(2) == "manual"
        assert dest.read_bytes() == b"%PDF-test"

    def test_sin_lote_abre_uno_propio_por_llamada(self, caso_man, tmp_casos_root):
        d1 = save_file(caso_man, "auto.pdf", b"contenido")
        d2 = save_file(caso_man, "otro.pdf", b"contenido-2")
        assert d1.exists() and d2.exists()
        assert d1.parent != d2.parent

    def test_sobreescribe_si_existe_en_mismo_lote(self, caso_man, tmp_casos_root):
        from core.intake_manual import abrir_lote_manual
        lote = abrir_lote_manual(caso_man)
        save_file(caso_man, "doc.pdf", b"v1", lote=lote)
        save_file(caso_man, "doc.pdf", b"v2-actualizado", lote=lote)
        dest = lote / "doc.pdf"
        assert dest.read_bytes() == b"v2-actualizado"

    def test_multiples_archivos(self, caso_man, tmp_casos_root):
        save_file(caso_man, "demanda.pdf", b"pdf")
        save_file(caso_man, "auto_admision.pdf", b"pdf2")
        save_file(caso_man, "notificacion.docx", b"docx")
        archivos = list_files(caso_man)
        nombres = [p.name for p in archivos]
        assert "demanda.pdf" in nombres
        assert "auto_admision.pdf" in nombres
        assert "notificacion.docx" in nombres

    def test_error_caso_no_existe(self, tmp_casos_root):
        with pytest.raises(FileNotFoundError, match="no existe"):
            save_file("CASO-INEXISTENTE", "demanda.pdf", b"datos")

    def test_error_nombre_con_ruta(self, caso_man, tmp_casos_root):
        with pytest.raises(ValueError, match="no válido"):
            save_file(caso_man, "../escape.pdf", b"datos")

    def test_error_nombre_vacio(self, caso_man, tmp_casos_root):
        with pytest.raises(ValueError, match="no válido"):
            save_file(caso_man, "", b"datos")


# ---------------------------------------------------------------------------
# list_files
# ---------------------------------------------------------------------------

class TestListFiles:
    def test_vacio_si_sin_carpeta(self, tmp_casos_root):
        importlib.reload(case_manager)
        case_manager.ensure_case("SIN-MANUAL", titulo="Sin manual")
        manual_dir = tmp_casos_root / "SIN-MANUAL" / "00_Input" / "04_Manual"
        if manual_dir.exists():
            import shutil
            shutil.rmtree(manual_dir)
        assert list_files("SIN-MANUAL") == []

    def test_vacio_si_caso_sin_archivos(self, caso_man):
        assert list_files(caso_man) == []

    def test_lista_ordenada_dentro_del_mismo_lote(self, caso_man, tmp_casos_root):
        from core.intake_manual import abrir_lote_manual
        lote = abrir_lote_manual(caso_man)
        save_file(caso_man, "z_ultimo.pdf", b"z", lote=lote)
        save_file(caso_man, "a_primero.pdf", b"a", lote=lote)
        save_file(caso_man, "m_medio.pdf", b"m", lote=lote)
        nombres = [p.name for p in list_files(caso_man)]
        assert nombres == sorted(nombres)

    def test_en_el_cajon_legacy_los_homonimos_de_control_son_documentos(self, caso_man,
                                                                       tmp_casos_root):
        """MEJORAS #149: ningún escritor pone `.pulled`, `_inventory.json` ni `.synced` en
        `04_Manual/`; un fichero así llamado ahí es un documento del cliente y se lista.
        Hasta el 2026-09-05 se excluían por basename. Lo que SÍ queda fuera es el
        `_manifiesto.yaml` de la raíz de un lote, que `save_file` escribe."""
        dest = save_file(caso_man, "real.pdf", b"pdf")
        manual_dir = tmp_casos_root / caso_man / "00_Input" / "04_Manual"
        manual_dir.mkdir(parents=True, exist_ok=True)
        (manual_dir / ".pulled").write_text("{}", encoding="utf-8")
        (manual_dir / "_inventory.json").write_text("{}", encoding="utf-8")
        (manual_dir / ".synced").write_text("", encoding="utf-8")
        nombres = sorted(p.name for p in list_files(caso_man))
        assert nombres == [".pulled", ".synced", "_inventory.json", "real.pdf"]
        assert (dest.parent / "_manifiesto.yaml").is_file()   # existe y no se listó


# ---------------------------------------------------------------------------
# extract_zip
# ---------------------------------------------------------------------------

class TestExtractZip:
    def test_extrae_archivos_planos(self, caso_man, tmp_casos_root):
        content = _make_zip({
            "demanda.pdf": b"%PDF-1",
            "anexo_1.docx": b"PK...",
        })
        extracted = extract_zip(caso_man, content)
        nombres = [p.name for p in extracted]
        assert "demanda.pdf" in nombres
        assert "anexo_1.docx" in nombres
        assert len(extracted) == 2

    def test_preserva_subdirectorios(self, caso_man, tmp_casos_root):
        from core.intake_manual import abrir_lote_manual
        lote = abrir_lote_manual(caso_man)
        content = _make_zip({
            "carpeta/auto_admision.pdf": b"auto",
            "carpeta/subcarpeta/diligencia.pdf": b"diligencia",
        })
        extracted = extract_zip(caso_man, content, lote=lote)
        rutas_rel = [str(p.relative_to(lote)) for p in extracted]
        assert any("carpeta" in r for r in rutas_rel)
        assert len(extracted) == 2

    def test_contenido_correcto(self, caso_man, tmp_casos_root):
        content = _make_zip({"demanda.pdf": b"contenido-real"})
        extracted = extract_zip(caso_man, content)
        assert extracted[0].read_bytes() == b"contenido-real"

    def test_ignora_path_traversal(self, caso_man, tmp_casos_root):
        # Entrada maliciosa con ../
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("../escape.txt", b"malicioso")
            zf.writestr("valido.pdf", b"ok")
        content = buf.getvalue()
        extracted = extract_zip(caso_man, content)
        nombres = [p.name for p in extracted]
        assert "escape.txt" not in nombres
        assert "valido.pdf" in nombres

    def test_sobreescribe_existente_en_mismo_lote(self, caso_man, tmp_casos_root):
        from core.intake_manual import abrir_lote_manual
        lote = abrir_lote_manual(caso_man)
        save_file(caso_man, "doc.pdf", b"v1", lote=lote)
        content = _make_zip({"doc.pdf": b"v2-desde-zip"})
        extract_zip(caso_man, content, lote=lote)
        dest = lote / "doc.pdf"
        assert dest.read_bytes() == b"v2-desde-zip"

    def test_error_zip_invalido(self, caso_man):
        with pytest.raises(zipfile.BadZipFile):
            extract_zip(caso_man, b"esto no es un zip")

    def test_error_caso_no_existe(self, tmp_casos_root):
        content = _make_zip({"f.pdf": b"x"})
        with pytest.raises(FileNotFoundError, match="no existe"):
            extract_zip("CASO-INEXISTENTE", content)

    def test_zip_vacio(self, caso_man):
        content = _make_zip({})
        extracted = extract_zip(caso_man, content)
        assert extracted == []

    def test_devuelve_lista_ordenada(self, caso_man, tmp_casos_root):
        content = _make_zip({
            "z.pdf": b"z",
            "a.pdf": b"a",
            "m.pdf": b"m",
        })
        extracted = extract_zip(caso_man, content)
        nombres = [p.name for p in extracted]
        assert nombres == sorted(nombres)


# ---------------------------------------------------------------------------
# save_file / extract_zip por lote (MEJORAS #54 T6) + save_file_en_lote (CLI)
# ---------------------------------------------------------------------------

class TestSaveFileEnLote:
    def test_save_file_sin_lote_abre_lote_propio(self, caso_man, tmp_casos_root):
        from core import intake_lotes, intake_manual
        dest = intake_manual.save_file(caso_man, "demanda.pdf", b"pdf")
        lote = dest.parent
        assert intake_lotes.PATRON_LOTE.match(lote.name).group(2) == "manual"
        man = intake_lotes.leer_manifiesto(lote)
        assert man["items"][0]["relpath"] == "demanda.pdf"

    def test_dos_save_file_al_mismo_lote(self, caso_man, tmp_casos_root):
        from core import intake_lotes, intake_manual
        lote = intake_manual.abrir_lote_manual(caso_man)
        d1 = intake_manual.save_file(caso_man, "a.pdf", b"a", lote=lote)
        d2 = intake_manual.save_file(caso_man, "b.pdf", b"b", lote=lote)
        assert d1.parent == d2.parent == lote
        rels = {i["relpath"] for i in intake_lotes.leer_manifiesto(lote)["items"]}
        assert rels == {"a.pdf", "b.pdf"}

    def test_duplicado_se_copia_y_anota(self, caso_man, tmp_casos_root):
        from core import intake_lotes, intake_manual
        intake_manual.save_file(caso_man, "a.pdf", b"mismo")
        d2 = intake_manual.save_file(caso_man, "copia.pdf", b"mismo")
        assert d2.exists()                                 # se copia igual (§6)
        man = intake_lotes.leer_manifiesto(d2.parent)
        item = next(i for i in man["items"] if i["relpath"] == "copia.pdf")
        assert "duplicado_de" in item

    def test_extract_zip_en_lote(self, caso_man, tmp_casos_root):
        from core import intake_lotes, intake_manual
        paths = intake_manual.extract_zip(caso_man, _make_zip({"x/a.pdf": b"a"}))
        lote = paths[0].parent.parent                       # <lote>/x/a.pdf
        assert intake_lotes.PATRON_LOTE.match(lote.name)
        assert intake_lotes.leer_manifiesto(lote)["items"][0]["relpath"] == "x/a.pdf"

    def test_list_files_ve_lotes_y_legacy(self, caso_man, tmp_casos_root):
        from core import config, intake_manual
        intake_manual.save_file(caso_man, "nuevo.pdf", b"n")
        legacy = config.caso_path(caso_man) / "00_Input" / "04_Manual"
        legacy.mkdir(parents=True, exist_ok=True)
        (legacy / "viejo.pdf").write_bytes(b"v")
        nombres = {p.name for p in intake_manual.list_files(caso_man)}
        assert {"nuevo.pdf", "viejo.pdf"} <= nombres

    # -- save_file_en_lote (CLI de Task 9; añadido aquí per contrato T6) ----

    def test_save_file_en_lote_con_subdirs_y_registra(self, caso_man, tmp_casos_root):
        from core import intake_lotes, intake_manual
        lote = intake_manual.abrir_lote_manual(caso_man)
        dest = intake_manual.save_file_en_lote(caso_man, lote, "sub/dir/f.pdf", b"contenido")
        assert dest == lote / "sub" / "dir" / "f.pdf"
        assert dest.read_bytes() == b"contenido"
        man = intake_lotes.leer_manifiesto(lote)
        assert man["items"][0]["relpath"] == "sub/dir/f.pdf"

    def test_save_file_en_lote_rechaza_dotdot(self, caso_man, tmp_casos_root):
        from core import intake_manual
        lote = intake_manual.abrir_lote_manual(caso_man)
        with pytest.raises(ValueError):
            intake_manual.save_file_en_lote(caso_man, lote, "../escape.pdf", b"x")

    def test_save_file_en_lote_rechaza_ruta_absoluta(self, caso_man, tmp_casos_root):
        import os

        from core import intake_manual
        lote = intake_manual.abrir_lote_manual(caso_man)
        abs_rel = os.path.abspath("escape.pdf")
        with pytest.raises(ValueError):
            intake_manual.save_file_en_lote(caso_man, lote, abs_rel, b"x")


# ---------------------------------------------------------------------------
# Integración con ensure_case
# ---------------------------------------------------------------------------

class TestEnsureCaseNoCreaCajonesDeEntrega:
    def test_ensure_case_no_crea_cajones_de_entrega(self, tmp_casos_root):
        importlib.reload(case_manager)
        case_manager.ensure_case("NUEVO-MAN", titulo="Nuevo manual")
        input_dir = tmp_casos_root / "NUEVO-MAN" / "00_Input"
        for cajon in ("01_Drive EV", "02_Whatsapp", "03_Email",
                      "04_Manual", "06_Entrevistas"):
            assert not (input_dir / cajon).exists(), f"{cajon} debe ser lazy"
        # La base 05_CRM sigue eager (D7) y el protocolo de la raíz existe.
        assert (input_dir / "05_CRM").is_dir()
        assert (input_dir / "_caso.md").is_file()
