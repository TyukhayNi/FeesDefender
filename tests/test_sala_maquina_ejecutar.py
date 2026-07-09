from pathlib import Path
from core import sala_maquina as sm


def _pdf_con_texto(path: Path, extra: str = ""):
    """Escribe un PDF mínimo con capa de texto usng reportlab si está; si no, pypdf.

    `extra` permite variar el contenido para obtener sha256 distintos entre PDFs.
    """
    from reportlab.pdfgen import canvas          # dep de test (ya en el entorno docling)
    c = canvas.Canvas(str(path))
    # NOTA autorrevisión: el literal del plan (99 chars) queda por debajo del
    # umbral de `_texto_suficiente` (>=100 chars tras strip()) y el PDF se
    # trataría como escaneado — justo el caso que este test quiere excluir.
    # Se alarga el texto manteniendo la intención (PDF digital con texto real).
    c.drawString(72, 720, "Encargo de mediación firmado por el propietario. "
                          "Honorarios de intermediación del cinco por ciento "
                          "sobre el precio final." + extra)
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


def test_ejecutar_aisla_fallo_por_documento(tmp_path, monkeypatch):
    # spec §9: un fallo en un documento no aborta el lote — se registra en
    # cobertura y se sigue con el resto. Simula el gotcha real de los lock
    # files ~$ de Office que hacen fallar la reescritura del MD.
    case = tmp_path / "EV-2026-001"
    (case / "00_Input" / "01_Drive EV").mkdir(parents=True)
    src1 = case / "00_Input" / "01_Drive EV" / "primero.pdf"
    src2 = case / "00_Input" / "01_Drive EV" / "segundo.pdf"
    _pdf_con_texto(src1)
    _pdf_con_texto(src2)
    sha1, sha2 = sm_file_sha(src1), sm_file_sha(src2)

    real_write_md = sm.write_md

    def _flaky(path, meta, body):
        if "primero" in str(path):
            raise OSError("~$ lock de Office bloquea la reescritura")
        return real_write_md(path, meta, body)

    monkeypatch.setattr(sm, "write_md", _flaky)

    docs = [
        sm.DocPlan(rel_path="01_Drive EV/primero.pdf", sha256=sha1, ext=".pdf",
                   ruta="pdf", slug=f"primero__{sha1[:8]}"),
        sm.DocPlan(rel_path="01_Drive EV/segundo.pdf", sha256=sha2, ext=".pdf",
                   ruta="pdf", slug=f"segundo__{sha2[:8]}"),
    ]
    cob = sm.ejecutar(case, docs, case_id="EV-2026-001")

    # el segundo documento SÍ se procesa pese al fallo del primero
    md2 = case / "01_Procesado" / "02_Sala de máquina" / "03_MD" / f"segundo__{sha2[:8]}.md"
    assert md2.exists()
    assert len(cob) == 2
    by_slug = {c.slug: c for c in cob}
    assert by_slug[f"primero__{sha1[:8]}"].estado == "empty"
    assert "lock de Office" in by_slug[f"primero__{sha1[:8]}"].nota
    assert by_slug[f"segundo__{sha2[:8]}"].estado == "ok"


def test_ejecutar_cobertura_lleva_sha256_del_plan(tmp_path, monkeypatch):
    case = tmp_path / "EV-2026-001"
    (case / "00_Input" / "01_Drive EV").mkdir(parents=True)
    src = case / "00_Input" / "01_Drive EV" / "encargo.pdf"
    _pdf_con_texto(src)
    sha = sm_file_sha(src)
    monkeypatch.setattr(sm, "ocr_pdf", lambda *a, **k: (_ for _ in ()).throw(AssertionError()))
    docs = [sm.DocPlan(rel_path="01_Drive EV/encargo.pdf", sha256=sha, ext=".pdf",
                       ruta="pdf", slug=f"encargo__{sha[:8]}")]
    cob = sm.ejecutar(case, docs, case_id="EV-2026-001")
    assert cob[0].sha256 == sha


def test_apply_estado_y_log_solo_exitos_con_sha256(tmp_path, monkeypatch):
    import scripts.sala_maquina as cli

    case = tmp_path / "EV-2026-001"
    (case / "00_Input" / "01_Drive EV").mkdir(parents=True)
    src_ok = case / "00_Input" / "01_Drive EV" / "ok.pdf"
    src_fail = case / "00_Input" / "01_Drive EV" / "fail.pdf"
    _pdf_con_texto(src_ok, extra=" Documento correcto.")
    _pdf_con_texto(src_fail, extra=" Documento que fallará al escribir el MD.")
    sha_ok, sha_fail = sm_file_sha(src_ok), sm_file_sha(src_fail)
    assert sha_ok != sha_fail

    monkeypatch.setattr(cli, "caso_path", lambda cid: case)
    eventos = []
    monkeypatch.setattr(cli, "append_event",
                        lambda cid, ev, *, details=None: eventos.append((ev, details)))

    real_write_md = sm.write_md

    def _flaky(path, meta, body):
        if "fail__" in str(path):
            raise OSError("~$ lock de Office")
        return real_write_md(path, meta, body)

    monkeypatch.setattr(sm, "write_md", _flaky)

    cli.apply("EV-2026-001")

    # el evento de custodia lleva sha256 por fichero (spec §7/§10)
    assert len(eventos) == 1
    ev, details = eventos[0]
    assert ev == "procesado_sala_maquina"
    assert {f["sha256"] for f in details["files"]} == {sha_ok, sha_fail}

    # el estado idempotente cuenta SOLO los éxitos (ok/low), no los fallidos
    import json as _json
    state = sm._sala_maquina_dir(case) / "_sala_maquina_state.json"
    procesados = set(_json.loads(state.read_text(encoding="utf-8"))["procesados"])
    assert procesados == {sha_ok}


def test_inventariar_lista_00_input_con_sha(tmp_path):
    case = tmp_path / "EV-2026-001"
    (case / "00_Input" / "01_Drive EV").mkdir(parents=True)
    (case / "00_Input" / "01_Drive EV" / "a.pdf").write_bytes(b"%PDF-1.4 x")
    (case / "00_Input" / "_intake_log.jsonl").write_text("{}", encoding="utf-8")  # control: ignorar
    inv = sm.inventariar(case)
    assert len(inv) == 1
    assert inv[0]["rel_path"] == "01_Drive EV/a.pdf"
    assert len(inv[0]["sha256"]) == 64 and inv[0]["ext"] == ".pdf"
