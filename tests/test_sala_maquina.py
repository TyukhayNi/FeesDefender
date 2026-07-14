from pathlib import Path

import pytest

from core import intake_log
from core import sala_maquina as sm


def test_clasificar_ruta_por_extension():
    assert sm.clasificar_ruta(".pdf") == "pdf"
    assert sm.clasificar_ruta(".PDF") == "pdf"
    assert sm.clasificar_ruta(".jpg") == "imagen"
    assert sm.clasificar_ruta(".heic") == "imagen"
    assert sm.clasificar_ruta(".eml") == "nativo"
    assert sm.clasificar_ruta(".txt") == "nativo"
    assert sm.clasificar_ruta(".docx") == "nativo"
    assert sm.clasificar_ruta(".mp4") == "sin_soporte"


def test_extensiones_nativas_sin_doble_fuente_de_verdad():
    # _EXTS_NATIVO (lo que clasificar_ruta enruta como "nativo") debe coincidir
    # EXACTAMENTE con las extensiones que _extraer_nativo sabe manejar. Si alguien
    # añade una a una lista y olvida la otra, un documento nativo saldría como texto
    # vacío ("" -> empty), indistinguible de un sin-texto real: fallo silencioso.
    manejadas = set(sm._NATIVO_EXTRACTORES) | sm._NATIVO_TEXTO_PLANO
    assert sm._EXTS_NATIVO == manejadas


def test_ocr_quality_texto_limpio_es_ok():
    texto = ("El arrendatario reclama la devolución de los honorarios de "
             "intermediación conforme al artículo veinte de la Ley de "
             "Arrendamientos Urbanos. " * 5)
    estado, motivo = sm.ocr_quality(texto, n_pags=1)
    assert estado == "ok"
    assert motivo == ""


def test_ocr_quality_vacio_es_empty():
    estado, _ = sm.ocr_quality("   ", n_pags=3)
    assert estado == "empty"


def test_ocr_quality_gibberish_es_low():
    # Muchos chars, pero tokens sin vocales / no léxicos (OCR ruidoso).
    basura = "xkq zzt brrr wgh nkk xcv " * 40
    estado, motivo = sm.ocr_quality(basura, n_pags=1)
    assert estado == "low"
    assert "gibberish" in motivo


def test_ocr_quality_baja_densidad_es_low():
    # Texto legible pero muy poco para 10 páginas (escaneado semivacío).
    # NOTA autorrevisión: el literal del plan ("Firmado en Barcelona. Conforme.",
    # 31 chars) cae por debajo de _MIN_CHARS=40 y da "empty" en vez de "low"
    # (contradice su propio docstring/intención). Se alarga el texto manteniendo
    # la intención (legible, pero insuficiente para 10 páginas) sin tocar los
    # umbrales de la implementación.
    estado, _ = sm.ocr_quality(
        "Firmado en Barcelona a fecha indicada. Todo conforme, sin observaciones adicionales.",
        n_pags=10,
    )
    assert estado == "low"


def test_plan_enruta_y_marca_skip():
    inventario = [
        {"rel_path": "01_Drive EV/encargo.pdf", "sha256": "aaaa1111", "ext": ".pdf"},
        {"rel_path": "03_Email/hilo.eml", "sha256": "bbbb2222", "ext": ".eml"},
        {"rel_path": "01_Drive EV/foto.heic", "sha256": "cccc3333", "ext": ".heic"},
        {"rel_path": "01_Drive EV/video.mp4", "sha256": "dddd4444", "ext": ".mp4"},
    ]
    plan = sm.plan(inventario, estado_previo={"bbbb2222"})
    by_sha = {d.sha256: d for d in plan}
    assert by_sha["aaaa1111"].ruta == "pdf"
    assert by_sha["aaaa1111"].slug == "encargo__aaaa1111"
    assert by_sha["bbbb2222"].skip is True          # ya procesado
    assert by_sha["cccc3333"].ruta == "imagen"
    assert by_sha["dddd4444"].ruta == "sin_soporte"
    assert by_sha["aaaa1111"].skip is False


def test_plan_excluye_90_notas_personales():
    inventario = [
        {"rel_path": "90_Notas personales/borrador.pdf", "sha256": "e1", "ext": ".pdf"},
        {"rel_path": "01_Drive EV/ok.pdf", "sha256": "e2", "ext": ".pdf"},
    ]
    plan = sm.plan(inventario, estado_previo=set())
    assert [d.sha256 for d in plan] == ["e2"]


def test_render_cobertura_marca_generado_y_ordena_dudosos_primero():
    cob = [
        sm.DocCobertura(slug="a__1", rel_path="x/a.pdf", metodo="pypdf", estado="ok", chars=1200),
        sm.DocCobertura(slug="b__2", rel_path="x/b.pdf", metodo="ocr", estado="empty",
                        chars=0, ocr=True, nota="sin texto o residual"),
    ]
    md = sm.render_cobertura(cob)
    assert md.startswith("<!-- GENERADO — NO EDITAR A MANO -->")
    # los dudosos (no-ok) van primero para que salten a la vista
    assert md.index("b__2") < md.index("a__1")
    assert "empty" in md and "sin texto" in md


def test_destino_seguro_rechaza_00_input_y_notas():
    case = Path("C:/casos/EV-2026-001")
    with pytest.raises(ValueError):
        sm.destino_seguro(case / "00_Input" / "x.md", case)
    with pytest.raises(ValueError):
        sm.destino_seguro(case / "90_Notas personales" / "x.md", case)


def test_destino_seguro_admite_sala_maquina():
    case = Path("C:/casos/EV-2026-001")
    dst = case / "01_Procesado" / "02_Sala de máquina" / "03_MD" / "x.md"
    assert sm.destino_seguro(dst, case) == dst


def test_evento_procesado_sala_maquina_registrado():
    assert "procesado_sala_maquina" in intake_log.INTAKE_EVENTS


def test_render_cobertura_sanea_pipe_en_nota_sin_romper_columnas():
    # Una nota con "|" (p.ej. un mensaje de excepción de OCR) no debe añadir
    # una columna extra a la fila de la tabla Markdown.
    cob = [
        sm.DocCobertura(slug="a__1", rel_path="x/a.pdf", metodo="ocr", estado="empty",
                        chars=0, ocr=True, nota="OCR falló: rc=16 | firmado"),
    ]
    md = sm.render_cobertura(cob)
    header = next(l for l in md.splitlines() if l.startswith("| documento"))
    fila = next(l for l in md.splitlines() if l.startswith("| a__1"))
    assert len(fila.split("|")) == len(header.split("|"))
    assert "rc=16 / firmado" in fila


# --- Cluster A / A1: cobertura acumulativa (fusión + serialización) ----------

def test_fusionar_cobertura_nueva_gana_por_slug():
    # La cobertura debe acumular entre corridas (simétrica con el estado): una
    # entrada nueva del mismo slug pisa a la previa; las previas no re-tocadas se
    # conservan; las nuevas no vistas se añaden. Sin duplicados.
    previa = [
        sm.DocCobertura(slug="a__1", rel_path="x/a.pdf", metodo="ocr", estado="empty",
                        chars=0, ocr=True, nota="OCR falló", sha256="a1"),
        sm.DocCobertura(slug="b__2", rel_path="x/b.pdf", metodo="pypdf", estado="ok",
                        chars=1200, sha256="b2"),
    ]
    nueva = [
        sm.DocCobertura(slug="a__1", rel_path="x/a.pdf", metodo="ocr", estado="ok",
                        chars=900, ocr=True, nota="reforzado con vision", sha256="a1"),
        sm.DocCobertura(slug="c__3", rel_path="x/c.pdf", metodo="nativo", estado="ok",
                        chars=300, sha256="c3"),
    ]
    fus = sm.fusionar_cobertura(previa, nueva)
    by = {c.slug: c for c in fus}
    assert set(by) == {"a__1", "b__2", "c__3"}
    assert len(fus) == 3                                # sin duplicados
    assert by["a__1"].estado == "ok"                    # la nueva gana
    assert by["a__1"].nota == "reforzado con vision"
    assert by["b__2"].estado == "ok"                    # la previa no re-tocada se conserva
    assert by["c__3"].chars == 300                      # nueva añadida


def test_fusionar_cobertura_preserva_orden_previas_luego_nuevas():
    previa = [sm.DocCobertura(slug="b__2", rel_path="b", metodo="pypdf", estado="ok")]
    nueva = [sm.DocCobertura(slug="a__1", rel_path="a", metodo="ocr", estado="empty")]
    fus = sm.fusionar_cobertura(previa, nueva)
    assert [c.slug for c in fus] == ["b__2", "a__1"]    # estable, no re-ordena


def test_fusionar_cobertura_conserva_dos_rutas_mismo_slug():
    # Dos ficheros byte-idénticos con el mismo stem en carpetas distintas comparten
    # slug (output_slug = stem+sha8, sin carpeta): p. ej. el mismo encargo llega por
    # Drive y como adjunto de correo. Son DOS filas de custodia (rel_path distinta);
    # la fusión NO debe colapsarlas → se indexa por rel_path, no por slug.
    a = sm.DocCobertura(slug="contrato__deadbeef", rel_path="01_Drive EV/contrato.pdf",
                        metodo="pypdf", estado="ok", chars=500, sha256="deadbeef")
    b = sm.DocCobertura(slug="contrato__deadbeef", rel_path="03_Email/contrato.pdf",
                        metodo="pypdf", estado="ok", chars=500, sha256="deadbeef")
    fus = sm.fusionar_cobertura([], [a, b])
    assert {c.rel_path for c in fus} == {"01_Drive EV/contrato.pdf", "03_Email/contrato.pdf"}
    assert len(fus) == 2


def test_cobertura_serializacion_round_trip():
    cob = [
        sm.DocCobertura(slug="a__1", rel_path="x/a.pdf", metodo="ocr", estado="empty",
                        chars=0, ocr=True, nota="x", sha256="deadbeef"),
        sm.DocCobertura(slug="b__2", rel_path="x/b.pdf", metodo="nativo", estado="ok",
                        chars=300),
    ]
    ds = sm.cobertura_a_dicts(cob)
    assert isinstance(ds, list) and all(isinstance(d, dict) for d in ds)
    assert sm.cobertura_desde_dicts(ds) == cob          # igualdad de dataclass


def test_cobertura_desde_dicts_tolera_claves_extra_y_faltantes():
    # Robustez ante evolución del esquema: ignora claves futuras y usa defaults
    # para opcionales ausentes (no revienta al leer un _cobertura.json de otra versión).
    ds = [{"slug": "a__1", "rel_path": "x/a.pdf", "metodo": "ocr", "estado": "empty",
           "campo_futuro": 123}]
    cob = sm.cobertura_desde_dicts(ds)
    assert cob[0].slug == "a__1"
    assert cob[0].chars == 0 and cob[0].ocr is False and cob[0].nota == ""


# --- Cluster A / A2: detección de visión cableada ----------------------------

def test_vision_cableada_detecta_stub_y_monkeypatch(monkeypatch):
    assert sm.vision_cableada() is False                 # stub por defecto = no cableado
    monkeypatch.setattr(sm, "_transcribir_vision", lambda imgs: "texto transcrito")
    assert sm.vision_cableada() is True                  # inyectado = cableado
