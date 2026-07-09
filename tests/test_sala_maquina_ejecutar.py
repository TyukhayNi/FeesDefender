from pathlib import Path
from core import sala_maquina as sm


def _pdf_con_texto(path: Path):
    """Escribe un PDF mínimo con capa de texto usng reportlab si está; si no, pypdf."""
    from reportlab.pdfgen import canvas          # dep de test (ya en el entorno docling)
    c = canvas.Canvas(str(path))
    # NOTA autorrevisión: el literal del plan (99 chars) queda por debajo del
    # umbral de `_texto_suficiente` (>=100 chars tras strip()) y el PDF se
    # trataría como escaneado — justo el caso que este test quiere excluir.
    # Se alarga el texto manteniendo la intención (PDF digital con texto real).
    c.drawString(72, 720, "Encargo de mediación firmado por el propietario. "
                          "Honorarios de intermediación del cinco por ciento "
                          "sobre el precio final.")
    c.showPage()
    c.save()


def test_ejecutar_pdf_digital_escribe_md_sin_ocr(tmp_path, monkeypatch):
    case = tmp_path / "EV-2026-001"
    (case / "00_Input" / "01_Drive EV").mkdir(parents=True)
    src = case / "00_Input" / "01_Drive EV" / "encargo.pdf"
    _pdf_con_texto(src)
    sha = sm_file_sha(src)
    # ocr_pdf NO debe llamarse para un PDF digital
    def _boom(*a, **k):
        raise AssertionError("no debe OCR-izar un PDF con capa de texto")
    monkeypatch.setattr(sm, "ocr_pdf", _boom)

    plan = [sm.DocPlan(rel_path="01_Drive EV/encargo.pdf", sha256=sha, ext=".pdf",
                       ruta="pdf", slug=f"encargo__{sha[:8]}")]
    cob = sm.ejecutar(case, plan, case_id="EV-2026-001")

    md = case / "01_Procesado" / "02_Sala de máquina" / "03_MD" / f"encargo__{sha[:8]}.md"
    assert md.exists()
    assert "Honorarios" in md.read_text(encoding="utf-8")
    assert cob[0].metodo == "pypdf" and cob[0].estado == "ok" and cob[0].ocr is False


def sm_file_sha(p: Path) -> str:
    from core.utils import file_sha256
    return file_sha256(p)


def test_ejecutar_pdf_escaneado_llama_ocr_y_persiste(tmp_path, monkeypatch):
    case = tmp_path / "EV-2026-001"
    (case / "00_Input" / "01_Drive EV").mkdir(parents=True)
    src = case / "00_Input" / "01_Drive EV" / "escaneado.pdf"
    src.write_bytes(b"%PDF-1.4\n% escaneado sin capa de texto\n")
    sha = sm_file_sha(src)

    ocr_dir = case / "01_Procesado" / "02_Sala de máquina" / "01_OCR"

    def _fake_ocr(entrada, salida, **k):
        Path(salida).parent.mkdir(parents=True, exist_ok=True)
        Path(salida).write_bytes(b"%PDF buscable con texto")
        return Path(salida)

    # pypdf del original = poco texto (escaneado); del PDF buscable = texto útil.
    def _fake_pypdf(path):
        return "Contrato de arras penitenciales entre las partes. " * 4 \
            if "01_OCR" in str(path) else ""

    monkeypatch.setattr(sm, "ocr_pdf", _fake_ocr)
    monkeypatch.setattr(sm, "_try_pypdf", _fake_pypdf)
    monkeypatch.setattr(sm, "_pdf_num_paginas", lambda p: 1)

    plan = [sm.DocPlan(rel_path="01_Drive EV/escaneado.pdf", sha256=sha, ext=".pdf",
                       ruta="pdf", slug=f"escaneado__{sha[:8]}")]
    cob = sm.ejecutar(case, plan, case_id="EV-2026-001")

    assert (ocr_dir / f"escaneado__{sha[:8]}.pdf").exists()   # PDF buscable persistido
    md = case / "01_Procesado" / "02_Sala de máquina" / "03_MD" / f"escaneado__{sha[:8]}.md"
    assert "arras" in md.read_text(encoding="utf-8")
    assert cob[0].metodo == "ocr" and cob[0].ocr is True and cob[0].estado == "ok"
