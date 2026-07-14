from pathlib import Path

import pytest

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


def test_ejecutar_ocr_sin_regenerar_no_afirma_custodia(tmp_path, monkeypatch):
    # IMPORTANTE 2: ocr_pdf devuelve la ENTRADA (rc=6, el PDF ya tenía texto) SIN
    # crear el buscable en 01_OCR/. No se debe afirmar custodia inexistente:
    # metodo != "ocr", ocr=False, y la nota deja constancia. Sin excepción.
    case = tmp_path / "EV-2026-001"
    (case / "00_Input" / "01_Drive EV").mkdir(parents=True)
    src = case / "00_Input" / "01_Drive EV" / "con_texto_previo.pdf"
    src.write_bytes(b"%PDF-1.4\n% ya tiene capa de texto\n")
    sha = sm_file_sha(src)

    ocr_dir = case / "01_Procesado" / "02_Sala de máquina" / "01_OCR"

    def _fake_ocr_prior(entrada, salida, **k):
        # simula rc=6 / PriorOcrFoundError: devuelve la entrada, NO crea la salida
        return Path(entrada)

    # 1ª llamada (en ejecutar, sobre src) = texto insuficiente -> entra a la rama OCR;
    # 2ª llamada (en _ocr_y_extraer, sobre el buscable=src) = texto de la capa previa.
    llamadas = {"n": 0}

    def _fake_pypdf(path):
        llamadas["n"] += 1
        if llamadas["n"] == 1:
            return "corto"                       # < 100 chars -> _texto_suficiente False
        return "Contrato de mediacion inmobiliaria entre las partes firmantes. " * 3

    monkeypatch.setattr(sm, "ocr_pdf", _fake_ocr_prior)
    monkeypatch.setattr(sm, "_try_pypdf", _fake_pypdf)
    monkeypatch.setattr(sm, "_pdf_num_paginas", lambda p: 1)

    plan = [sm.DocPlan(rel_path="01_Drive EV/con_texto_previo.pdf", sha256=sha, ext=".pdf",
                       ruta="pdf", slug=f"prev__{sha[:8]}")]
    cob = sm.ejecutar(case, plan, case_id="EV-2026-001")

    # NO se creó artefacto de custodia en 01_OCR/
    assert not (ocr_dir / f"prev__{sha[:8]}.pdf").exists()
    # el MD sí se escribe (el texto de la capa previa se extrae igualmente)
    md = case / "01_Procesado" / "02_Sala de máquina" / "03_MD" / f"prev__{sha[:8]}.md"
    assert "mediacion" in md.read_text(encoding="utf-8")
    # no se miente: metodo no afirma custodia OCR, ocr=False, y la nota lo explica
    assert cob[0].metodo != "ocr"
    assert cob[0].ocr is False
    assert "01_OCR" in cob[0].nota


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


def test_apply_force_no_arrastra_estado_resuelto_obsoleto(tmp_path, monkeypatch):
    # IMPORTANTE 1: con --force, si un documento antes resuelto FALLA ahora (p. ej.
    # tras cambiar el motor OCR), su sha NO debe sobrevivir en el estado por la union
    # con el estado stale en disco. --force no saltó nada: el estado nuevo refleja
    # SOLO los exitos de esta corrida.
    import scripts.sala_maquina as cli

    case = tmp_path / "EV-2026-001"
    (case / "00_Input" / "01_Drive EV").mkdir(parents=True)
    src = case / "00_Input" / "01_Drive EV" / "doc.pdf"
    _pdf_con_texto(src)
    sha = sm_file_sha(src)

    # estado previo: sha ya marcado "resuelto" en una corrida anterior
    cli._guardar_estado(case, {sha})

    monkeypatch.setattr(cli, "caso_path", lambda cid: case)
    monkeypatch.setattr(cli, "append_event", lambda *a, **k: None)
    # ejecutar devuelve el doc como FALLIDO ahora (empty) — no exito
    monkeypatch.setattr(cli.sm, "ejecutar", lambda *a, **k: [
        sm.DocCobertura(f"doc__{sha[:8]}", "01_Drive EV/doc.pdf", "ocr", "empty",
                        0, True, "OCR falló: motor nuevo", sha),
    ])

    cli.apply("EV-2026-001", force=True)

    import json as _json
    state = sm._sala_maquina_dir(case) / "_sala_maquina_state.json"
    procesados = set(_json.loads(state.read_text(encoding="utf-8"))["procesados"])
    assert sha not in procesados   # el fallo bajo --force NO deja el sha resuelto


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


def test_ejecutar_vision_refuerza_pdf_digital_gibberish(tmp_path, monkeypatch):
    # Task 12: la rama pypdf-digital TAMBIÉN pasa por el gate de visión. Un PDF con
    # capa de texto suficiente (pasa _texto_suficiente por longitud/densidad) pero
    # gibberish (ocr_quality -> low) + vision=True se refuerza. ocr_pdf NO se llama
    # (es un PDF digital: nunca se OCR-iza).
    case = tmp_path / "EV-2026-001"
    (case / "00_Input" / "01_Drive EV").mkdir(parents=True)
    src = case / "00_Input" / "01_Drive EV" / "digital_ruidoso.pdf"
    src.write_bytes(b"%PDF-1.4\n% da igual: _try_pypdf esta mockeado\n")
    sha = sm_file_sha(src)

    gibberish = "xkq zzt brrr wgh nkk xcv " * 40  # >=100 chars, densidad alta, low
    transcrito = ("Encargo de mediacion inmobiliaria firmado por el propietario "
                  "el dia indicado, con honorarios pactados. " * 3)

    def _boom_ocr(*a, **k):
        raise AssertionError("no debe OCR-izar un PDF con capa de texto suficiente")

    monkeypatch.setattr(sm, "ocr_pdf", _boom_ocr)
    monkeypatch.setattr(sm, "_try_pypdf", lambda p: gibberish)
    monkeypatch.setattr(sm, "_pdf_num_paginas", lambda p: 1)
    monkeypatch.setattr(sm, "_renderizar_paginas", lambda p: ["pagina-fake"])
    monkeypatch.setattr(sm, "_transcribir_vision", lambda imgs: transcrito)

    docs = [sm.DocPlan(rel_path="01_Drive EV/digital_ruidoso.pdf", sha256=sha, ext=".pdf",
                       ruta="pdf", slug=f"digital__{sha[:8]}")]
    cob = sm.ejecutar(case, docs, case_id="EV-2026-001", vision=True)

    md = case / "01_Procesado" / "02_Sala de máquina" / "03_MD" / f"digital__{sha[:8]}.md"
    contenido = md.read_text(encoding="utf-8")
    assert "Encargo de mediacion" in contenido      # el MD quedó reforzado con la transcripción
    assert cob[0].metodo == "pypdf" and cob[0].ocr is False
    # el refuerzo no bastó (sigue gibberish): la cobertura deja constancia de que
    # SÍ se intentó visión (distingue 'no intentado' de 'intentado y no bastó').
    assert cob[0].estado == "low"
    assert "sigue dudoso" in cob[0].nota


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


# --- Cluster A / A1: cobertura acumulativa (CLI apply) -----------------------

def test_apply_incremental_acumula_cobertura(tmp_path, monkeypatch):
    # Bug de VALERO: una 2ª corrida incremental machacaba _cobertura.md con solo
    # el delta, perdiendo las filas anteriores. Tras el fix, conviven.
    import scripts.sala_maquina as cli
    case = tmp_path / "EV-2026-001"
    drive = case / "00_Input" / "01_Drive EV"
    drive.mkdir(parents=True)
    _pdf_con_texto(drive / "uno.pdf", extra=" Documento uno.")
    _pdf_con_texto(drive / "dos.pdf", extra=" Documento dos distinto.")
    monkeypatch.setattr(cli, "caso_path", lambda cid: case)
    monkeypatch.setattr(cli, "append_event", lambda *a, **k: None)

    cli.apply("EV-2026-001")                       # 1ª corrida: uno + dos

    cobertura = case / "01_Procesado" / "_revisar" / "_cobertura.md"
    md1 = cobertura.read_text(encoding="utf-8")
    assert "uno__" in md1 and "dos__" in md1

    _pdf_con_texto(drive / "tres.pdf", extra=" Documento tres tardío.")
    cli.apply("EV-2026-001")                       # 2ª corrida incremental: solo tres

    md2 = cobertura.read_text(encoding="utf-8")
    assert "uno__" in md2 and "dos__" in md2 and "tres__" in md2


def test_apply_force_cobertura_es_snapshot_fresco(tmp_path, monkeypatch):
    # Con --force, la cobertura refleja SOLO el inventario actual (foto fresca),
    # simétrico con el estado: nada se saltó, la corrida es autoritativa.
    import scripts.sala_maquina as cli
    case = tmp_path / "EV-2026-001"
    drive = case / "00_Input" / "01_Drive EV"
    drive.mkdir(parents=True)
    _pdf_con_texto(drive / "uno.pdf", extra=" Uno.")
    monkeypatch.setattr(cli, "caso_path", lambda cid: case)
    monkeypatch.setattr(cli, "append_event", lambda *a, **k: None)

    cli.apply("EV-2026-001")

    (drive / "uno.pdf").unlink()
    _pdf_con_texto(drive / "dos.pdf", extra=" Dos distinto.")
    cli.apply("EV-2026-001", force=True)

    md = (case / "01_Procesado" / "_revisar" / "_cobertura.md").read_text(encoding="utf-8")
    assert "dos__" in md and "uno__" not in md

    # el estado estructurado (_cobertura.json) también es foto fresca: force NO
    # fusiona con lo previo (si lo hiciera, 'uno' — ya borrado — quedaría stale).
    import json as _json
    cj = sm._sala_maquina_dir(case) / "_cobertura.json"
    rel = {d["rel_path"] for d in _json.loads(cj.read_text(encoding="utf-8"))}
    assert rel == {"01_Drive EV/dos.pdf"}


# --- Cluster A / A2: --vision fail-loud (CLI apply) ---------------------------

def test_apply_vision_sin_cablear_aborta_sin_procesar(tmp_path, monkeypatch):
    import typer
    import scripts.sala_maquina as cli
    case = tmp_path / "EV-2026-001"
    (case / "00_Input" / "01_Drive EV").mkdir(parents=True)
    _pdf_con_texto(case / "00_Input" / "01_Drive EV" / "uno.pdf", extra=" Uno.")
    monkeypatch.setattr(cli, "caso_path", lambda cid: case)
    monkeypatch.setattr(cli, "append_event", lambda *a, **k: None)

    def _boom(*a, **k):
        raise AssertionError("no debe procesar si --vision no está cableado")
    monkeypatch.setattr(cli.sm, "ejecutar", _boom)

    with pytest.raises(typer.Exit):
        cli.apply("EV-2026-001", vision=True)

    # abortó en el preflight: no se escribió cobertura
    assert not (case / "01_Procesado" / "_revisar" / "_cobertura.md").exists()


# --- Cluster A / A3: comando reforzar ----------------------------------------

def test_reforzar_reprocesa_solo_dudosos_con_vision(tmp_path, monkeypatch):
    import scripts.sala_maquina as cli
    case = tmp_path / "EV-2026-001"
    drive = case / "00_Input" / "01_Drive EV"
    drive.mkdir(parents=True)
    _pdf_con_texto(drive / "bueno.pdf", extra=" Documento bueno con texto de sobra.")
    escan = drive / "escaneado.pdf"
    escan.write_bytes(b"%PDF-1.4\n% escaneado sin capa de texto\n")
    sha_bueno = sm_file_sha(drive / "bueno.pdf")

    monkeypatch.setattr(cli, "caso_path", lambda cid: case)
    monkeypatch.setattr(cli, "append_event", lambda *a, **k: None)

    def _fake_ocr(entrada, salida, **k):
        Path(salida).parent.mkdir(parents=True, exist_ok=True)
        Path(salida).write_bytes(b"%PDF buscable vacio")
        return Path(salida)

    real_pypdf = sm._try_pypdf

    def _pypdf(path):
        if "01_OCR" in str(path):
            return ""                       # el buscable del escaneado sale vacío -> empty
        return real_pypdf(path)

    monkeypatch.setattr(sm, "ocr_pdf", _fake_ocr)
    monkeypatch.setattr(sm, "_try_pypdf", _pypdf)
    monkeypatch.setattr(sm, "_pdf_num_paginas", lambda p: 1)

    cli.apply("EV-2026-001")                 # bueno=ok, escaneado=empty

    # verifico el estado de partida: escaneado dudoso
    prev = {c.rel_path: c for c in cli._cobertura_previa(case)}
    assert prev["01_Drive EV/escaneado.pdf"].estado == "empty"
    assert prev["01_Drive EV/bueno.pdf"].estado == "ok"

    # cableo la visión y refuerzo
    transcrito = ("Encargo de mediacion firmado por el propietario segun la imagen "
                  "de la pagina escaneada, con honorarios pactados. " * 2)
    monkeypatch.setattr(sm, "_renderizar_paginas", lambda p: ["pagina-fake"])
    monkeypatch.setattr(sm, "_transcribir_vision", lambda imgs: transcrito)

    # bueno.pdf (ok) NO debe re-procesarse: si se toca su MD, boom
    real_write_md = sm.write_md

    def _guard_write(path, meta, body):
        if f"bueno__{sha_bueno[:8]}" in str(path):
            raise AssertionError("reforzar no debe re-tocar un documento 'ok'")
        return real_write_md(path, meta, body)

    monkeypatch.setattr(sm, "write_md", _guard_write)

    cli.reforzar("EV-2026-001")

    post = {c.rel_path: c for c in cli._cobertura_previa(case)}
    assert post["01_Drive EV/escaneado.pdf"].estado in ("ok", "low")   # mejoró
    assert post["01_Drive EV/bueno.pdf"].estado == "ok"                # conservado


def test_reforzar_sin_vision_cableada_aborta(tmp_path, monkeypatch):
    import typer
    import scripts.sala_maquina as cli
    case = tmp_path / "EV-2026-001"
    (case / "00_Input" / "01_Drive EV").mkdir(parents=True)
    monkeypatch.setattr(cli, "caso_path", lambda cid: case)
    with pytest.raises(typer.Exit):
        cli.reforzar("EV-2026-001")


# --- Revisión adversarial: hallazgos confirmados -----------------------------

def test_apply_dos_copias_identicas_conserva_ambas_rutas(tmp_path, monkeypatch):
    # Hallazgo cobertura: el mismo PDF byte-idéntico en dos carpetas (Drive +
    # adjunto de correo) comparte slug; la cobertura debe registrar AMBAS rutas
    # (dos filas de custodia), no colapsarlas a una.
    import json as _json
    import shutil
    import scripts.sala_maquina as cli
    case = tmp_path / "EV-2026-001"
    (case / "00_Input" / "01_Drive EV").mkdir(parents=True)
    (case / "00_Input" / "03_Email").mkdir(parents=True)
    origen = case / "00_Input" / "01_Drive EV" / "contrato.pdf"
    _pdf_con_texto(origen, extra=" Copia idéntica en dos carpetas.")
    shutil.copyfile(origen, case / "00_Input" / "03_Email" / "contrato.pdf")   # bytes idénticos

    monkeypatch.setattr(cli, "caso_path", lambda cid: case)
    monkeypatch.setattr(cli, "append_event", lambda *a, **k: None)
    cli.apply("EV-2026-001")

    cj = sm._sala_maquina_dir(case) / "_cobertura.json"
    rel = {d["rel_path"] for d in _json.loads(cj.read_text(encoding="utf-8"))}
    assert rel == {"01_Drive EV/contrato.pdf", "03_Email/contrato.pdf"}


def test_ejecutar_ocr_excepcion_con_vision_rescata(tmp_path, monkeypatch):
    # Hallazgo reforzar: un PDF que OCRmyPDF rechaza (cifrado/corrupto) pero que
    # pypdfium2 SÍ renderiza debe rescatarse con visión cuando vision=True, en vez
    # de quedarse empty sin haber intentado la visión.
    case = tmp_path / "EV-2026-001"
    (case / "00_Input" / "01_Drive EV").mkdir(parents=True)
    src = case / "00_Input" / "01_Drive EV" / "cifrado.pdf"
    src.write_bytes(b"%PDF-1.4\n% escaneado que OCR rechaza\n")
    sha = sm_file_sha(src)

    def _ocr_boom(entrada, salida, **k):
        raise RuntimeError("PDF cifrado: OCRmyPDF rc=8")
    transcrito = ("Encargo de mediacion firmado por el propietario, honorarios "
                  "pactados del cinco por ciento sobre el precio. " * 3)
    monkeypatch.setattr(sm, "ocr_pdf", _ocr_boom)
    monkeypatch.setattr(sm, "_try_pypdf", lambda p: "")
    monkeypatch.setattr(sm, "_pdf_num_paginas", lambda p: 1)
    monkeypatch.setattr(sm, "_renderizar_paginas", lambda p: ["pagina-fake"])
    monkeypatch.setattr(sm, "_transcribir_vision", lambda imgs: transcrito)

    docs = [sm.DocPlan(rel_path="01_Drive EV/cifrado.pdf", sha256=sha, ext=".pdf",
                       ruta="pdf", slug=f"cifrado__{sha[:8]}")]
    cob = sm.ejecutar(case, docs, case_id="EV-2026-001", vision=True)

    md = case / "01_Procesado" / "02_Sala de máquina" / "03_MD" / f"cifrado__{sha[:8]}.md"
    assert "Encargo de mediacion" in md.read_text(encoding="utf-8")
    assert cob[0].estado in ("ok", "low")
    assert cob[0].metodo == "vision"


def test_ejecutar_ocr_excepcion_sin_vision_queda_empty(tmp_path, monkeypatch):
    # Sin --vision, un PDF que OCR rechaza queda empty (no se intenta visión).
    case = tmp_path / "EV-2026-001"
    (case / "00_Input" / "01_Drive EV").mkdir(parents=True)
    src = case / "00_Input" / "01_Drive EV" / "cifrado.pdf"
    src.write_bytes(b"%PDF-1.4\n% escaneado que OCR rechaza\n")
    sha = sm_file_sha(src)

    def _ocr_boom(entrada, salida, **k):
        raise RuntimeError("PDF cifrado")
    def _vision_boom(imgs):
        raise AssertionError("no debe intentar visión sin vision=True")
    monkeypatch.setattr(sm, "ocr_pdf", _ocr_boom)
    monkeypatch.setattr(sm, "_try_pypdf", lambda p: "")
    monkeypatch.setattr(sm, "_pdf_num_paginas", lambda p: 1)
    monkeypatch.setattr(sm, "_transcribir_vision", _vision_boom)

    docs = [sm.DocPlan(rel_path="01_Drive EV/cifrado.pdf", sha256=sha, ext=".pdf",
                       ruta="pdf", slug=f"cifrado__{sha[:8]}")]
    cob = sm.ejecutar(case, docs, case_id="EV-2026-001")   # vision=False

    assert cob[0].metodo == "ocr" and cob[0].estado == "empty"
    assert "OCR falló" in cob[0].nota


def test_reforzar_fuentes_desaparecidas_no_emite_evento(tmp_path, monkeypatch):
    # Hallazgo reforzar (baja): si las fuentes dudosas ya no están en 00_Input, el
    # plan filtrado queda vacío; reforzar NO debe reescribir ni emitir un evento
    # forense count=0 en el log de custodia.
    import scripts.sala_maquina as cli
    case = tmp_path / "EV-2026-001"
    drive = case / "00_Input" / "01_Drive EV"
    drive.mkdir(parents=True)
    escan = drive / "escaneado.pdf"
    escan.write_bytes(b"%PDF-1.4\n% escaneado sin capa\n")

    def _fake_ocr(entrada, salida, **k):
        Path(salida).parent.mkdir(parents=True, exist_ok=True)
        Path(salida).write_bytes(b"%PDF buscable vacio")
        return Path(salida)
    real_pypdf = sm._try_pypdf
    monkeypatch.setattr(sm, "ocr_pdf", _fake_ocr)
    monkeypatch.setattr(sm, "_try_pypdf", lambda p: "" if "01_OCR" in str(p) else real_pypdf(p))
    monkeypatch.setattr(sm, "_pdf_num_paginas", lambda p: 1)

    monkeypatch.setattr(cli, "caso_path", lambda cid: case)
    eventos = []
    monkeypatch.setattr(cli, "append_event",
                        lambda cid, ev, *, details=None: eventos.append(ev))
    cli.apply("EV-2026-001")                     # escaneado = empty (reforzable)
    eventos.clear()

    escan.unlink()                               # desaparece la fuente
    monkeypatch.setattr(sm, "_renderizar_paginas", lambda p: ["fake"])
    monkeypatch.setattr(sm, "_transcribir_vision", lambda imgs: "texto")
    cli.reforzar("EV-2026-001")

    assert eventos == []                         # sin evento forense para un lote vacío


def test_reforzar_excluye_dudoso_nativo_no_reforzable(tmp_path, monkeypatch):
    # Hallazgo tests: un dudoso NO reforzable (nativo empty, sin páginas que
    # renderizar) no debe entrar en objetivos → reforzar no lo re-procesa.
    import scripts.sala_maquina as cli
    case = tmp_path / "EV-2026-001"
    manual = case / "00_Input" / "04_Manual"
    manual.mkdir(parents=True)
    (manual / "vacio.txt").write_text("", encoding="utf-8")   # nativo → empty

    monkeypatch.setattr(cli, "caso_path", lambda cid: case)
    eventos = []
    monkeypatch.setattr(cli, "append_event",
                        lambda cid, ev, *, details=None: eventos.append(ev))
    cli.apply("EV-2026-001")                     # nativo empty
    eventos.clear()

    monkeypatch.setattr(sm, "_renderizar_paginas", lambda p: ["fake"])
    monkeypatch.setattr(sm, "_transcribir_vision", lambda imgs: "texto")
    # si el nativo entrara en objetivos, ejecutar lo re-procesaría; no debe.
    cli.reforzar("EV-2026-001")

    assert eventos == []                         # 0 objetivos reforzables → sin evento


def test_ejecutar_vision_cableada_falla_en_doc_aisla_lote(tmp_path, monkeypatch):
    # A2 (fallo blando): visión cableada pero que LANZA en runtime en un doc →
    # nota blanda, el lote sigue, el doc NO se marca 'error' (aislamiento §9).
    case = tmp_path / "EV-2026-001"
    (case / "00_Input" / "01_Drive EV").mkdir(parents=True)
    src = case / "00_Input" / "01_Drive EV" / "escaneado.pdf"
    src.write_bytes(b"%PDF-1.4\n% escaneado sin capa\n")
    sha = sm_file_sha(src)

    def _fake_ocr(entrada, salida, **k):
        Path(salida).parent.mkdir(parents=True, exist_ok=True)
        Path(salida).write_bytes(b"%PDF buscable vacio")
        return Path(salida)
    def _vision_boom(imgs):
        raise RuntimeError("timeout del modelo de visión")
    monkeypatch.setattr(sm, "ocr_pdf", _fake_ocr)
    monkeypatch.setattr(sm, "_try_pypdf", lambda p: "")
    monkeypatch.setattr(sm, "_pdf_num_paginas", lambda p: 1)
    monkeypatch.setattr(sm, "_renderizar_paginas", lambda p: ["pagina-fake"])
    monkeypatch.setattr(sm, "_transcribir_vision", _vision_boom)

    docs = [sm.DocPlan(rel_path="01_Drive EV/escaneado.pdf", sha256=sha, ext=".pdf",
                       ruta="pdf", slug=f"escaneado__{sha[:8]}")]
    cob = sm.ejecutar(case, docs, case_id="EV-2026-001", vision=True)

    assert cob[0].metodo == "ocr"                # no se tumbó a 'error'
    assert cob[0].estado == "empty"
    assert "vision" in cob[0].nota.lower()       # constancia del intento fallido


def test_ejecutar_no_toca_00_input_ni_notas_personales(tmp_path):
    # Task 13: guard e2e — 00_Input/ (incl. 90_Notas personales/) sale intacto.
    case = tmp_path / "EV-2026-001"
    (case / "00_Input" / "01_Drive EV").mkdir(parents=True)
    (case / "00_Input" / "90_Notas personales").mkdir(parents=True)
    src = case / "00_Input" / "01_Drive EV" / "encargo.pdf"
    _pdf_con_texto(src)
    (case / "00_Input" / "90_Notas personales" / "privado.txt").write_text(
        "nota privada del abogado", encoding="utf-8"
    )

    def _snapshot(root: Path) -> dict:
        return {
            str(p.relative_to(root)): (p.stat().st_mtime_ns, p.stat().st_size)
            for p in sorted(root.rglob("*")) if p.is_file()
        }

    input_root = case / "00_Input"
    antes = _snapshot(input_root)

    inventario = sm.inventariar(case)
    docs = sm.plan(inventario, estado_previo=set())
    assert all("90_Notas personales" not in d.rel_path for d in docs)  # excluido, Task 3

    sm.ejecutar(case, docs, case_id="EV-2026-001")

    despues = _snapshot(input_root)
    assert antes == despues
