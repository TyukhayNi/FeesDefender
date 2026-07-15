"""Tests del cerebro del split (core/split_documental)."""
from __future__ import annotations

from pathlib import Path

import pytest

from tests._pdf_fixtures import build_pdf


def test_build_pdf_pagina_en_blanco_sin_texto(tmp_path: Path):
    # 3 páginas: texto, BLANCA ([]), texto
    pdf = build_pdf(tmp_path / "b.pdf", [["CEDULA DE EMPLAZAMIENTO", "Juzgado"], [], ["FACTURA", "Total 100"]])
    from pypdf import PdfReader
    with PdfReader(str(pdf)) as r:
        assert len(r.pages) == 3
        assert len((r.pages[1].extract_text() or "").strip()) < 10  # la blanca ~0 chars
        assert "CEDULA" in (r.pages[0].extract_text() or "").upper()


from core.split_documental import Segmento, DocLogico, segmentar_por_blancos


def test_segmentar_colapsa_blancos_y_bordes():
    # 8 págs, blancas en {3, 6, 7}. Blancos iniciales/finales/consecutivos no crean vacíos.
    assert segmentar_por_blancos(8, {3, 6, 7}) == [(1, 2), (4, 5), (8, 8)]


def test_segmentar_sin_blancos_un_solo_rango():
    assert segmentar_por_blancos(5, set()) == [(1, 5)]


def test_segmentar_todo_blanco_vacio():
    assert segmentar_por_blancos(3, {1, 2, 3}) == []


from core.split_documental import _primeras_lineas, clasificar


def test_primeras_lineas_filtra_cortas_y_limita():
    txt = "CEDULA DE EMPLAZAMIENTO\nab\nJuzgado de Instancia\nlinea3\nlinea4\nlinea5\nlinea6"
    out = _primeras_lineas(txt, n=3)
    assert out == ["CEDULA DE EMPLAZAMIENTO", "Juzgado de Instancia", "linea3"]  # 'ab' (<3) fuera


def test_clasificar_usa_marcador_judicial():
    textos = ["CÉDULA DE EMPLAZAMIENTO\nJuzgado", "otra pagina"]
    assert clasificar(textos, 1, 1) == "CEDULA_EMPLAZAMIENTO"


def test_clasificar_sin_marcador_devuelve_documento():
    textos = ["texto anodino sin marcadores reconocibles"]
    assert clasificar(textos, 1, 1) == "DOCUMENTO"


import pytest as _pytest
from core.split_documental import TIPOS_EXTRA_EV


@_pytest.mark.parametrize("linea,esperado", [
    ("PREVENCIÓN DE BLANQUEO DE CAPITALES", "DOC_PBC"),
    ("CONTRATO DE ARRAS PENITENCIALES", "DOC_ARRAS"),
    ("DOCUMENTO DE RESERVA", "DOC_RESERVA"),
])
def test_marcadores_ev_clasifican(linea, esperado):
    assert clasificar([linea], 1, 1) == esperado


def test_tipos_extra_ev_no_vacio():
    assert len(TIPOS_EXTRA_EV) >= 3


from core.split_documental import cobertura_tinta, paginas_en_blanco, _texto_por_pagina


def test_cobertura_tinta_blanca_vs_texto(tmp_path):
    pdf = build_pdf(tmp_path / "t.pdf", [["MUCHO TEXTO EN ESTA PAGINA " * 5], []])
    tinta_texto = cobertura_tinta(pdf, 1)
    tinta_blanca = cobertura_tinta(pdf, 2)
    assert tinta_blanca < tinta_texto
    assert tinta_blanca < 0.008  # la blanca por debajo del umbral


def test_paginas_en_blanco_detecta_la_delimitadora(tmp_path):
    # La página de contenido real tiene >10 chars: la reja barata de caracteres
    # (UMBRAL_CHARS_BLANCO) la excluye sin rasterizar. Solo la hoja en blanco (~0 chars)
    # llega al detector de tinta. Un contenido de 1 palabra sería un caso irreal.
    pdf = build_pdf(tmp_path / "b.pdf", [["CEDULA DE EMPLAZAMIENTO"], [], ["FACTURA", "Total 100"]])
    textos = _texto_por_pagina(pdf)
    assert paginas_en_blanco(pdf, textos) == {2}


from core.split_documental import detectar


def test_detectar_por_blancos(tmp_path):
    pdf = build_pdf(tmp_path / "j.pdf", [
        ["CEDULA DE EMPLAZAMIENTO"], [],
        ["A U T O", "AUTO Nº 12"], [],
        ["FACTURA", "Invoice"],
    ])
    segmentos, blancos = detectar(pdf)
    assert blancos == {2, 4}
    assert [(s.pagina_inicio, s.pagina_fin) for s in segmentos] == [(1, 1), (3, 3), (5, 5)]
    assert segmentos[0].tipo == "CEDULA_EMPLAZAMIENTO"
    assert segmentos[2].tipo == "DOC_FACTURA"


def test_detectar_sin_blancos_fallback_marcadores(tmp_path):
    # Sin páginas en blanco → fallback por marcadores (separar.detectar_segmentos).
    # Ambos tipos son NO absorbibles (CEDULA_EMPLAZAMIENTO y AUTO, prio 10, fuera de
    # TIPOS_ABSORBE_SIN_NUMERO), así que el fallback los separa en 2 segmentos.
    # (DOC_FACTURA sí se absorbe sin nº de doc → no serviría para probar el fallback.)
    pdf = build_pdf(tmp_path / "n.pdf", [
        ["CÉDULA DE EMPLAZAMIENTO", "cuerpo"],
        ["A U T O", "AUTO Nº 12"],
    ])
    segmentos, blancos = detectar(pdf)
    assert blancos == set()
    assert len(segmentos) >= 2


def test_detectar_documento_unico_passthrough(tmp_path):
    pdf = build_pdf(tmp_path / "u.pdf", [["FACTURA", "una sola factura", "Total 50"]])
    segmentos, blancos = detectar(pdf)
    assert len(segmentos) == 1
    assert segmentos[0].pagina_inicio == 1 and segmentos[0].pagina_fin == 1
    assert segmentos[0].tipo == "DOC_FACTURA"


def test_detectar_pdf_vacio_lanza_pdfvacioerror(tmp_path):
    from core.split_documental import detectar
    from core.anon.exceptions import PDFVacioError
    from pypdf import PdfWriter
    vacio = tmp_path / "vacio.pdf"
    with open(vacio, "wb") as fh:
        PdfWriter().write(fh)   # PDF sin páginas
    with pytest.raises(PDFVacioError):
        detectar(vacio)


from core.split_documental import (
    construir_manifiesto, escribir_manifiesto, leer_manifiesto, validar_manifiesto,
)


def test_construir_y_roundtrip_manifiesto(tmp_path):
    segs = [Segmento(1, 1, 4, "CEDULA_EMPLAZAMIENTO"), Segmento(2, 6, 12, "AUTO")]
    man = construir_manifiesto("01_Drive EV/bundle.pdf", "a1b2c3d4" * 8, segs, {5})
    assert man["segmentos"][0]["pp"] == "1-4"
    assert man["delimitadores"] == [5]
    escribir_manifiesto(tmp_path, man)
    assert (tmp_path / "_segmentacion.json").exists()
    assert (tmp_path / "_segmentacion.md").exists()
    assert leer_manifiesto(tmp_path)["segmentos"][1]["tipo"] == "AUTO"


def test_validar_rechaza_rango_invalido():
    man = {"segmentos": [{"seg": 1, "pp": "1-4", "tipo": "X", "role": "documento"},
                         {"seg": 2, "pp": "3-9", "tipo": "Y", "role": "documento"}]}
    with pytest.raises(ValueError, match="solap"):
        validar_manifiesto(man, total_pag=20)


def test_validar_rechaza_fuera_de_rango():
    man = {"segmentos": [{"seg": 1, "pp": "1-40", "tipo": "X", "role": "documento"}]}
    with pytest.raises(ValueError, match="fuera de rango"):
        validar_manifiesto(man, total_pag=20)


from core.split_documental import materializar


def test_materializar_corta_y_devuelve_doclogicos(tmp_path):
    # Página 5 con contenido >=10 chars ("FACTURA" solo son 7): con una sola
    # palabra corta, detectar() la trataría como BLANCA (chars<10 ∧ tinta baja,
    # mismo trampa de página-de-una-palabra ya corregida en Tasks 7/8) y
    # colapsaría a 2 segmentos en vez de 3.
    pdf = build_pdf(tmp_path / "j.pdf", [
        ["CEDULA DE EMPLAZAMIENTO"], [], ["A U T O", "AUTO Nº 12"], [], ["FACTURA", "Total 100"],
    ])
    from core.split_documental import detectar
    segs, blancos = detectar(pdf)
    man = construir_manifiesto("01_Drive EV/j.pdf", "d" * 64, segs, blancos)
    carpeta = tmp_path / "02_Documentos" / "bundle-slug"
    docs = materializar(pdf, man, carpeta, parent_slug="bundle-slug",
                        parent_sha256="d" * 64, bundle_rel_path="01_Drive EV/j.pdf")
    assert len(docs) == 3
    # Un PDF por segmento con nombre = seg_slug + índice de segmentación
    pdfs = sorted(carpeta.glob("*.pdf"))
    assert len(pdfs) == 3
    assert (carpeta / "indice.json").exists()
    import json as _json
    indice = _json.loads((carpeta / "indice.json").read_text(encoding="utf-8"))
    nombres_indice = {d["archivo"] for d in indice["documentos"]}
    nombres_reales = {p.name for p in pdfs}
    assert nombres_indice == nombres_reales  # el índice referencia los ficheros que existen (no el nombre temporal de separar_pdf)
    d0 = docs[0]
    assert d0.destino == "split"
    assert d0.parent_slug == "bundle-slug"
    assert d0.role_in_bundle == "documento"
    assert d0.paginas == "1-1"
    assert len(d0.seg_sha256) == 64
    assert d0.slug.endswith(d0.seg_sha256[:8])
    assert d0.fuentes == ["01_Drive EV/j.pdf"]


def test_split_documental_es_evento_valido():
    from core.intake_log import INTAKE_EVENTS
    assert "split_documental" in INTAKE_EVENTS
