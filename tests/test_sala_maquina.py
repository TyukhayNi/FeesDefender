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


def test_sniff_ext_por_contenido_pdf():
    assert sm._sniff_ext_por_contenido(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3") == ".pdf"


def test_sniff_ext_por_contenido_jpeg():
    assert sm._sniff_ext_por_contenido(b"\xff\xd8\xff\xe0\x00\x10JFIF") == ".jpg"


def test_sniff_ext_por_contenido_png():
    assert sm._sniff_ext_por_contenido(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR") == ".png"


def test_sniff_ext_por_contenido_desconocido_devuelve_none():
    assert sm._sniff_ext_por_contenido(b"cualquier texto plano sin firma") is None


def test_sniff_ext_por_contenido_bytes_vacios_devuelve_none():
    assert sm._sniff_ext_por_contenido(b"") is None


def test_inventariar_detecta_extension_por_contenido_cuando_falta(tmp_path: Path):
    """Ficheros de Drive sin extensión (típico: captura/foto compartida directo,
    sin 'Guardar como') no deben caer en sin_soporte si el contenido es legible.
    Caso real: 'Señal 3000 €' y 'DNI ... jpg' (sin punto), W-02TH0W, 2026-07-17."""
    case_dir = tmp_path / "caso"
    origen = case_dir / "00_Input" / "01_Drive EV"
    origen.mkdir(parents=True)
    (origen / "Señal 3000 €").write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 50)

    inventario = sm.inventariar(case_dir)

    assert len(inventario) == 1
    assert inventario[0]["ext"] == ".jpg"


def test_inventariar_no_toca_extension_ya_reconocida(tmp_path: Path):
    """Un fichero con extensión correcta no dispara el sniff (ni falta falta)."""
    case_dir = tmp_path / "caso"
    origen = case_dir / "00_Input"
    origen.mkdir(parents=True)
    (origen / "documento.pdf").write_bytes(b"%PDF-1.4\ncontenido")

    inventario = sm.inventariar(case_dir)

    assert inventario[0]["ext"] == ".pdf"


def test_inventariar_contenido_irreconocible_mantiene_sin_soporte(tmp_path: Path):
    """Si ni el nombre ni el contenido dan pistas, se queda sin_soporte (sin
    fallo silencioso: sigue apareciendo, solo que sin extensión corregida)."""
    case_dir = tmp_path / "caso"
    origen = case_dir / "00_Input"
    origen.mkdir(parents=True)
    (origen / "misterioso").write_bytes(b"datos binarios sin firma conocida")

    inventario = sm.inventariar(case_dir)

    assert inventario[0]["ext"] == ""
    assert sm.clasificar_ruta(inventario[0]["ext"]) == "sin_soporte"


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


# --- Task 13B: cobertura por documento lógico (no colapsar segmentos) --------

def test_fusionar_por_doc_id_colapsa_el_cambio_de_tipo():
    """Cambiar el TIPO de un segmento deja UNA fila, no dos (spec §6).

    La rev. 2 del spec daba el cambio de TIPO por inocuo. No lo era: el destino nuevo no
    existe, así que la regla «si el destino existe, archivar» no se dispara y la fusión
    por slug conservaba dos filas del MISMO doc_id.
    """
    from core.sala_maquina import DocCobertura, fusionar_cobertura
    vieja = DocCobertura("b__d01_DOC_A", "01_Drive EV/b.pdf", "pypdf", "ok", 100, False,
                         "", "a" * 64, parent_slug="b", paginas="1-3", tipo="DOC_A",
                         doc_id="d01")
    nueva = DocCobertura("b__d01_DOC_B", "01_Drive EV/b.pdf", "pypdf", "ok", 120, False,
                         "", "c" * 64, parent_slug="b", paginas="1-3", tipo="DOC_B",
                         doc_id="d01")

    out = fusionar_cobertura([vieja], [nueva])

    assert [c.slug for c in out] == ["b__d01_DOC_B"]


def test_fusionar_sin_doc_id_sigue_indexando_por_slug():
    """Los documentos sueltos (y las filas reconstruidas del MD) no tienen doc_id."""
    from core.sala_maquina import DocCobertura, fusionar_cobertura
    a = DocCobertura("encargo__aabbccdd", "01_Drive EV/encargo.pdf", "pypdf", "ok")
    b = DocCobertura("factura__eeff0011", "01_Drive EV/factura.pdf", "pypdf", "ok")

    assert len(fusionar_cobertura([a], [b])) == 2


def test_la_corrida_es_autoritativa_sobre_lo_que_reprocesa():
    """Cambiar la clave no basta: una fusión que solo AÑADE no puede sustituir (H-05).

    La fila reconstruida del MD sale con `doc_id=""` porque el frontmatter no lo guarda;
    la fila fresca del mismo documento lógico lleva `doc_id`. Con claves distintas
    quedaban DOS filas con el mismo slug, una de ellas con sha vacío — la clase de
    defecto que esta pieza existe para eliminar, entrando por la reconstrucción.
    """
    from core.sala_maquina import DocCobertura, fusionar_cobertura
    reconstruida = DocCobertura("b__d01_DOC_ARRAS", "01_Drive EV/b.pdf", "pypdf", "ok",
                                nota="fila reconstruida del MD (sin _cobertura.json)")
    fresca = DocCobertura("b__d01_DOC_ARRAS", "01_Drive EV/b.pdf", "ocr", "ok", 120, True,
                          "", "c" * 64, parent_slug="b", paginas="1-3", tipo="DOC_ARRAS",
                          doc_id="d01")

    out = fusionar_cobertura([reconstruida], [fresca],
                             rel_paths_reprocesados={"01_Drive EV/b.pdf"})

    assert len(out) == 1 and out[0].sha256 == "c" * 64


def test_lo_no_reprocesado_se_conserva_intacto():
    """Una corrida acotada sigue siendo acotada: la autoridad es por `rel_path` tocado."""
    from core.sala_maquina import DocCobertura, fusionar_cobertura
    otro = DocCobertura("informe__bbbbbbbb", "01_Drive EV/informe.pdf", "ocr", "ok", 8912)
    nueva = DocCobertura("b__d01_A", "01_Drive EV/b.pdf", "ocr", "ok", 10, True, "",
                         "c" * 64, parent_slug="b", doc_id="d01")

    out = fusionar_cobertura([otro], [nueva], rel_paths_reprocesados={"01_Drive EV/b.pdf"})

    assert {c.rel_path for c in out} == {"01_Drive EV/informe.pdf", "01_Drive EV/b.pdf"}


def test_sin_conjunto_autoritativo_se_comporta_como_antes():
    """Compatibilidad: `reforzar` y los llamadores viejos no pasan el conjunto."""
    from core.sala_maquina import DocCobertura, fusionar_cobertura
    vieja = DocCobertura("b__d01_A", "01_Drive EV/b.pdf", "pypdf", "ok", doc_id="d01")
    otra = DocCobertura("b__d02_B", "01_Drive EV/b.pdf", "pypdf", "ok", doc_id="d02")

    assert len(fusionar_cobertura([vieja], [otra])) == 2


def test_fusionar_cobertura_conserva_n_segmentos_mismo_bundle():
    # 3 segmentos del MISMO bundle (mismo rel_path) con slug propio NO deben colapsar.
    from core.sala_maquina import DocCobertura, fusionar_cobertura
    segs = [DocCobertura(f"b__seg{i:02d}_X__{i:08x}", "01_Drive EV/b.pdf", "pypdf", "ok",
                         100, False, "", f"{i:064x}", parent_sha256="B" * 64, parent_slug="b")
            for i in (1, 2, 3)]
    out = fusionar_cobertura([], segs)
    assert len(out) == 3   # antes colapsaba a 1 (indexado solo por rel_path)
