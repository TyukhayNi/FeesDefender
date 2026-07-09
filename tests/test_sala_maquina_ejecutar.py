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


# --- FASE F2 -----------------------------------------------------------------

def test_ejecutar_nativo_eml_y_txt_producen_md(tmp_path):
    # Task 10: ruta nativa reutiliza los helpers SANOS de extractor por extensión.
    case = tmp_path / "EV-2026-001"
    (case / "00_Input" / "03_Email").mkdir(parents=True)
    (case / "00_Input" / "04_Manual").mkdir(parents=True)

    eml = case / "00_Input" / "03_Email" / "hilo.eml"
    eml.write_bytes(
        b"From: propietario@example.com\r\n"
        b"To: agencia@example.com\r\n"
        b"Subject: Encargo de mediacion\r\n"
        b"Date: Mon, 1 Jun 2026 10:00:00 +0200\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n\r\n"
        b"Confirmamos el encargo de mediacion inmobiliaria firmado ayer por el propietario."
    )
    txt = case / "00_Input" / "04_Manual" / "notas.txt"
    txt.write_text(
        "Reunion con el buscador para revisar las condiciones del contrato de arras.",
        encoding="utf-8",
    )
    sha_eml, sha_txt = sm_file_sha(eml), sm_file_sha(txt)

    docs = [
        sm.DocPlan(rel_path="03_Email/hilo.eml", sha256=sha_eml, ext=".eml",
                   ruta="nativo", slug=f"hilo__{sha_eml[:8]}"),
        sm.DocPlan(rel_path="04_Manual/notas.txt", sha256=sha_txt, ext=".txt",
                   ruta="nativo", slug=f"notas__{sha_txt[:8]}"),
    ]
    cob = sm.ejecutar(case, docs, case_id="EV-2026-001")

    sm_dir = case / "01_Procesado" / "02_Sala de máquina"
    md_eml = sm_dir / "03_MD" / f"hilo__{sha_eml[:8]}.md"
    md_txt = sm_dir / "03_MD" / f"notas__{sha_txt[:8]}.md"
    assert "mediacion" in md_eml.read_text(encoding="utf-8")
    assert "arras" in md_txt.read_text(encoding="utf-8")

    by_slug = {c.slug: c for c in cob}
    assert by_slug[f"hilo__{sha_eml[:8]}"].metodo == "nativo"
    assert by_slug[f"hilo__{sha_eml[:8]}"].ocr is False
    assert by_slug[f"notas__{sha_txt[:8]}"].metodo == "nativo"
    # nativo no toca 01_OCR/
    assert not (sm_dir / "01_OCR").exists()


def test_ejecutar_imagen_convierte_y_ocr(tmp_path, monkeypatch):
    # Task 11: imagen -> PDF intermedio (imagen_a_pdf) -> mismo camino OCR.
    from PIL import Image

    case = tmp_path / "EV-2026-001"
    (case / "00_Input" / "01_Drive EV").mkdir(parents=True)
    src = case / "00_Input" / "01_Drive EV" / "foto.png"
    Image.new("RGB", (50, 50), (0, 128, 255)).save(src)
    sha = sm_file_sha(src)

    def _fake_ocr(entrada, salida, **k):
        Path(salida).parent.mkdir(parents=True, exist_ok=True)
        Path(salida).write_bytes(b"%PDF buscable con texto")
        return Path(salida)

    def _fake_pypdf(path):
        return "Fotografia del inmueble objeto de la mediacion inmobiliaria. " * 3 \
            if "01_OCR" in str(path) else ""

    monkeypatch.setattr(sm, "ocr_pdf", _fake_ocr)
    monkeypatch.setattr(sm, "_try_pypdf", _fake_pypdf)
    monkeypatch.setattr(sm, "_pdf_num_paginas", lambda p: 1)

    docs = [sm.DocPlan(rel_path="01_Drive EV/foto.png", sha256=sha, ext=".png",
                       ruta="imagen", slug=f"foto__{sha[:8]}")]
    cob = sm.ejecutar(case, docs, case_id="EV-2026-001")

    ocr_dir = case / "01_Procesado" / "02_Sala de máquina" / "01_OCR"
    assert (ocr_dir / f"foto__{sha[:8]}.pdf").exists()
    md = case / "01_Procesado" / "02_Sala de máquina" / "03_MD" / f"foto__{sha[:8]}.md"
    assert "inmobiliaria" in md.read_text(encoding="utf-8")
    assert cob[0].metodo == "ocr" and cob[0].ocr is True and cob[0].estado == "ok"
    # el intermedio de imagen_a_pdf NO queda persistido en 01_OCR (solo el buscable)
    assert list(ocr_dir.glob("*__imagen.pdf")) == []


def test_ejecutar_imagen_conversion_fallida_es_sin_soporte(tmp_path, monkeypatch):
    # .heic corrupto/ilegible: la conversión falla -> sin_soporte, sin llamar a OCR.
    case = tmp_path / "EV-2026-001"
    (case / "00_Input" / "01_Drive EV").mkdir(parents=True)
    src = case / "00_Input" / "01_Drive EV" / "foto.heic"
    src.write_bytes(b"no es una imagen real")
    sha = sm_file_sha(src)

    def _boom(*a, **k):
        raise AssertionError("no debe OCR-izar si la conversion a PDF fallo")
    monkeypatch.setattr(sm, "ocr_pdf", _boom)

    docs = [sm.DocPlan(rel_path="01_Drive EV/foto.heic", sha256=sha, ext=".heic",
                       ruta="imagen", slug=f"foto__{sha[:8]}")]
    cob = sm.ejecutar(case, docs, case_id="EV-2026-001")

    assert cob[0].metodo == "sin_soporte" and cob[0].estado == "sin_soporte"
    assert "convers" in cob[0].nota.lower()


def test_ejecutar_vision_refuerza_documento_empty(tmp_path, monkeypatch):
    # Task 12: con --vision, un doc empty se refuerza con la transcripcion mockeada.
    case = tmp_path / "EV-2026-001"
    (case / "00_Input" / "01_Drive EV").mkdir(parents=True)
    src = case / "00_Input" / "01_Drive EV" / "escaneado.pdf"
    src.write_bytes(b"%PDF-1.4\n% escaneado sin capa de texto\n")
    sha = sm_file_sha(src)

    def _fake_ocr(entrada, salida, **k):
        Path(salida).parent.mkdir(parents=True, exist_ok=True)
        Path(salida).write_bytes(b"%PDF buscable pero vacio")
        return Path(salida)

    transcrito = ("Encargo de mediacion firmado por el propietario, "
                  "segun se lee en la imagen de la pagina. " * 2)

    monkeypatch.setattr(sm, "ocr_pdf", _fake_ocr)
    monkeypatch.setattr(sm, "_try_pypdf", lambda p: "")           # OCR no sacó nada -> empty
    monkeypatch.setattr(sm, "_pdf_num_paginas", lambda p: 1)
    monkeypatch.setattr(sm, "_renderizar_paginas", lambda p: ["pagina-fake"])
    monkeypatch.setattr(sm, "_transcribir_vision", lambda imgs: transcrito)

    docs = [sm.DocPlan(rel_path="01_Drive EV/escaneado.pdf", sha256=sha, ext=".pdf",
                       ruta="pdf", slug=f"escaneado__{sha[:8]}")]
    cob = sm.ejecutar(case, docs, case_id="EV-2026-001", vision=True)

    md = case / "01_Procesado" / "02_Sala de máquina" / "03_MD" / f"escaneado__{sha[:8]}.md"
    assert "Encargo de mediacion" in md.read_text(encoding="utf-8")
    assert cob[0].estado in ("ok", "low")   # mejoró respecto a empty


def test_ejecutar_sin_vision_no_llama_transcribir(tmp_path, monkeypatch):
    # --vision es off por defecto: un doc empty se queda empty, sin tocar vision.
    case = tmp_path / "EV-2026-001"
    (case / "00_Input" / "01_Drive EV").mkdir(parents=True)
    src = case / "00_Input" / "01_Drive EV" / "escaneado.pdf"
    src.write_bytes(b"%PDF-1.4\n% escaneado sin capa de texto\n")
    sha = sm_file_sha(src)

    def _fake_ocr(entrada, salida, **k):
        Path(salida).parent.mkdir(parents=True, exist_ok=True)
        Path(salida).write_bytes(b"%PDF buscable pero vacio")
        return Path(salida)

    def _boom(imgs):
        raise AssertionError("vision no debe llamarse si vision=False")

    monkeypatch.setattr(sm, "ocr_pdf", _fake_ocr)
    monkeypatch.setattr(sm, "_try_pypdf", lambda p: "")
    monkeypatch.setattr(sm, "_pdf_num_paginas", lambda p: 1)
    monkeypatch.setattr(sm, "_transcribir_vision", _boom)

    docs = [sm.DocPlan(rel_path="01_Drive EV/escaneado.pdf", sha256=sha, ext=".pdf",
                       ruta="pdf", slug=f"escaneado__{sha[:8]}")]
    cob = sm.ejecutar(case, docs, case_id="EV-2026-001")  # vision=False (default)

    assert cob[0].estado == "empty"

