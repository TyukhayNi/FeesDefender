from pathlib import Path

import pytest

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
