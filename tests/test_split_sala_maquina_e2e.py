"""E2E: un bundle digital multi-doc produce N MD (documentos lógicos), no 1 gigante.

Fixture DIGITAL (con capa de texto suficiente): `_texto_suficiente` exige ≥100
chars y ≥40 char/pág, así que cada documento del bundle lleva varias líneas —
la Sala de máquina lo lee por pypdf SIN OCR y el split corta por las hojas en
blanco intercaladas (pypdfium2 para el cribado de tinta). Sin dependencia de
OCRmyPDF; marcado `slow` por el render de páginas.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tests._pdf_fixtures import build_pdf

pytestmark = pytest.mark.slow


def _bundle_digital(dirpath: Path) -> Path:
    # PDF CON capa de texto (digital): 3 documentos separados por 2 hojas en blanco.
    # Texto suficiente por página (≥40 char/pág) para que NO caiga a OCR.
    return build_pdf(dirpath / "00_Input" / "01_Drive EV" / "bundle.pdf", [
        ["CEDULA DE EMPLAZAMIENTO",
         "Juzgado de Primera Instancia numero cinco de la ciudad de Barcelona",
         "En la villa de Barcelona se emplaza a la parte demandada para comparecer",
         "en el plazo legalmente establecido conforme a la Ley de Enjuiciamiento Civil."],
        [],
        ["A U T O numero doce dictado por el juzgado en las presentes actuaciones",
         "Vistos los antecedentes de hecho y los fundamentos de derecho aplicables",
         "este tribunal acuerda lo que a continuacion se detalla en la parte dispositiva",
         "con expresa mencion de los recursos que caben contra la presente resolucion."],
        [],
        ["FACTURA por servicios de mediacion inmobiliaria efectivamente prestados",
         "Se detallan a continuacion los conceptos facturados y el importe total",
         "correspondiente a la operacion de intermediacion realizada por la agencia",
         "con el desglose de la base imponible y el impuesto sobre el valor anadido."],
    ])


def test_bundle_digital_se_parte_en_n_md(tmp_path, monkeypatch):
    import core.config as config
    case_dir = tmp_path / "W-TEST01"
    (case_dir / "00_Input" / "01_Drive EV").mkdir(parents=True)
    _bundle_digital(case_dir)
    monkeypatch.setattr(config, "caso_path", lambda cid: case_dir)

    from core import sala_maquina as sm
    docs = sm.plan(sm.inventariar(case_dir), set())
    cob = sm.ejecutar(case_dir, docs, case_id="W-TEST01")

    # 3 documentos lógicos, no 1 bundle
    seg_rows = [c for c in cob if c.parent_slug]
    assert len(seg_rows) == 3
    md_dir = case_dir / "01_Procesado" / "02_Sala de máquina" / "03_MD"
    assert len(list(md_dir.glob("*.md"))) == 3
    docs_dir = case_dir / "01_Procesado" / "02_Sala de máquina" / "02_Documentos"
    assert len(list(docs_dir.rglob("*.pdf"))) == 3


def test_segmento_lleva_sha_fisico_y_skip_lo_respeta(tmp_path, monkeypatch):
    import core.config as config
    from core import sala_maquina as sm
    case_dir = tmp_path / "W-TEST03"
    (case_dir / "00_Input" / "01_Drive EV").mkdir(parents=True)
    _bundle_digital(case_dir)
    monkeypatch.setattr(config, "caso_path", lambda cid: case_dir)
    inv = sm.inventariar(case_dir)
    bundle_sha = inv[0]["sha256"]
    cob = sm.ejecutar(case_dir, sm.plan(inv, set()), case_id="W-TEST03")
    # cada segmento apunta al sha FÍSICO del bundle (clave del estado)
    assert [c.parent_sha256 for c in cob if c.parent_slug] == [bundle_sha] * 3
    # con ese sha en estado_previo, el bundle se salta ENTERO (no se re-parte)
    assert all(d.skip for d in sm.plan(inv, {bundle_sha}))


def test_manifiesto_editado_se_respeta(tmp_path, monkeypatch):
    import core.config as config
    from core import sala_maquina as sm, split_documental as split
    case_dir = tmp_path / "W-TEST02"
    (case_dir / "00_Input" / "01_Drive EV").mkdir(parents=True)
    _bundle_digital(case_dir)
    monkeypatch.setattr(config, "caso_path", lambda cid: case_dir)

    docs = sm.plan(sm.inventariar(case_dir), set())
    d = next(x for x in docs if x.ruta == "pdf")
    carpeta = case_dir / "01_Procesado" / "02_Sala de máquina" / "02_Documentos" / d.slug
    carpeta.mkdir(parents=True)
    # Manifiesto editado a mano: FUSIONA los 3 en 2 (letrado juntó cédula+auto).
    split.escribir_manifiesto(carpeta, {
        "fuente": d.rel_path, "bundle_sha256": d.sha256,
        "segmentos": [{"seg": 1, "pp": "1-3", "tipo": "EXPEDIENTE", "role": "documento"},
                      {"seg": 2, "pp": "5-5", "tipo": "DOC_FACTURA", "role": "documento"}],
        "delimitadores": [4]})
    cob = sm.ejecutar(case_dir, docs, case_id="W-TEST02")
    seg_rows = [c for c in cob if c.parent_slug]
    assert len(seg_rows) == 2   # respeta la fusión del letrado, no re-detecta 3
