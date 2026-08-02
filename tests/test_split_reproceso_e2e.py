"""El defecto de punta a punta: reprocesar un bundle SUSTITUYE, no añade.

Es el test que el spec (§8.1) declara que «falla hoy»: dos materializaciones del mismo
bundle con bytes distintos dejaban 2N artefactos y 2N filas.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.sala_maquina as cli
from core import sala_maquina as sm
from core.anon.ocr import ResultadoEscalera
from core.utils import file_sha256, output_slug
from tests._pdf_fixtures import build_pdf


@pytest.fixture
def caso(tmp_path, monkeypatch):
    case_dir = tmp_path / "BaRS9 - Prueba - (W-TEST99) - Negativa oferta aceptada"
    (case_dir / "00_Input" / "01_Drive EV").mkdir(parents=True)
    # Origen "escaneado": PDF real (pypdf lo lee sin reventar) pero con texto MUY por
    # debajo de `_texto_suficiente` → el motor baja a la escalera de OCR, que aquí va
    # doblada. Sin dependencia de OCRmyPDF.
    build_pdf(case_dir / "00_Input" / "01_Drive EV" / "bundle.pdf", [["Escaneado"]])
    monkeypatch.setattr(cli, "caso_path", lambda cid: case_dir)
    monkeypatch.setattr(cli, "append_event", lambda cid, ev, *, details=None: None)
    monkeypatch.setattr(cli, "_atomizar_correo", lambda cid, cd: None)
    monkeypatch.setattr(cli.case_locator, "resolve_ref", lambda ref: ref)
    monkeypatch.setattr(sm, "append_event", lambda cid, ev, *, details=None: None)
    return case_dir


def _escalera_que_reescribe(corrida: dict):
    """Doble de la escalera: cada corrida produce un buscable con los MISMOS documentos
    lógicos y BYTES DISTINTOS — exactamente lo que hace un re-OCR."""
    def _fake(entrada, salida, **kw):
        salida = Path(salida)
        salida.parent.mkdir(parents=True, exist_ok=True)
        n = corrida["n"]
        build_pdf(salida, [
            ["CEDULA DE EMPLAZAMIENTO",
             "Juzgado de Primera Instancia numero cinco de la ciudad de Barcelona",
             f"En la villa de Barcelona se emplaza a la parte demandada (pase {n})"], [],
            ["A U T O numero doce dictado por el juzgado en las presentes actuaciones",
             "Vistos los antecedentes de hecho y los fundamentos de derecho aplicables",
             f"este tribunal acuerda lo que se detalla a continuacion (pase {n})"], [],
            ["FACTURA por servicios de mediacion inmobiliaria efectivamente prestados",
             "Se detallan a continuacion los conceptos facturados y el importe total",
             f"con el desglose de la base imponible y el impuesto (pase {n})"],
        ])
        return ResultadoEscalera(salida, "redo")
    return _fake


def test_reprocesar_sustituye_en_vez_de_anadir(caso, monkeypatch):
    corrida = {"n": 1}
    monkeypatch.setattr(sm, "ocr_pdf_escalera", _escalera_que_reescribe(corrida))

    cli.apply("W-TEST99")
    corrida["n"] = 2
    cli.apply("W-TEST99", force=True)

    sm_dir = sm._sala_maquina_dir(caso)
    rel = "01_Drive EV/bundle.pdf"
    src = caso / "00_Input" / rel
    parent = output_slug(rel, file_sha256(src))
    carpeta = sm_dir / "02_Documentos" / parent

    pdfs = sorted(p.name for p in carpeta.glob("*.pdf"))
    mds = sorted(p.name for p in (sm_dir / "03_MD").glob(f"{parent}__*.md"))
    txts = sorted(p.name for p in (sm_dir / "raw_text").glob(f"{parent}__*.txt"))
    assert len(pdfs) == 3, f"una generación por documento lógico, no dos: {pdfs}"
    assert len(mds) == 3 and len(txts) == 3

    filas = json.loads((sm_dir / "_cobertura.json").read_text(encoding="utf-8"))
    segmentos = [f for f in filas if f["rel_path"] == rel and f["doc_id"]]
    assert len(segmentos) == 3, "la cobertura acumuló dos generaciones"
    assert sorted(f["doc_id"] for f in segmentos) == ["d01", "d02", "d03"]

    # Los tres hashes coherentes: la fila declara los bytes que hay en disco.
    for f in segmentos:
        assert file_sha256(carpeta / f"{f['slug']}.pdf") == f["sha256"]
        assert (sm_dir / "03_MD" / f"{f['slug']}.md").exists()
        assert (sm_dir / "raw_text" / f"{f['slug']}.txt").exists()

    # Y la generación anterior está archivada entera, no borrada.
    archivos = sorted((caso / sm.VERSIONES_ANTERIORES).glob("reproceso_*/*"))
    assert len(archivos) == 9, f"9 = 3 documentos × 3 representaciones; hay {len(archivos)}"

    # El reproceso SÍ escribió: el MD nuevo trae el texto del segundo pase.
    md = next((sm_dir / "03_MD").glob(f"{parent}__d01_*.md")).read_text(encoding="utf-8")
    assert "pase 2" in md
