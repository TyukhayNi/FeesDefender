"""Preflight, publicación por generación y guard bidireccional de la Sala de máquina.

Spec: 2026-08-01-identidad-segmento-bundle-design.md §4, §7 y §7.1 (rev. 4).
"""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
import typer

import scripts.sala_maquina as cli
from core import sala_maquina as sm
from core import split_documental as split
from tests._pdf_fixtures import build_pdf


def _caso(tmp_path, monkeypatch):
    """Caso mínimo cableado al CLI (idiom del repo: se doblan las dependencias externas).

    Las DOS ligaduras de `append_event`, no una: `core/sala_maquina.py` lo importa por su
    cuenta y `_split_o_md` lo llama, así que doblar solo el del CLI dejaba los tests
    escribiendo `<CASOS_ROOT real>/W-TEST99/00_Input/_intake_log.jsonl` — en el Drive, en
    cada corrida de la suite — contra la primera restricción del plan.
    """
    case_dir = tmp_path / "BaRS9 - Prueba - (W-TEST99) - Negativa oferta aceptada"
    (case_dir / "00_Input" / "01_Drive EV").mkdir(parents=True)
    monkeypatch.setattr(cli, "caso_path", lambda cid: case_dir)
    monkeypatch.setattr(cli, "append_event", lambda cid, ev, *, details=None: None)
    monkeypatch.setattr(sm, "append_event", lambda cid, ev, *, details=None: None)
    monkeypatch.setattr(cli, "_atomizar_correo", lambda cid, cd: None)
    monkeypatch.setattr(cli.case_locator, "resolve_ref", lambda ref: ref)
    return case_dir


def _bundle(case_dir, nombre="bundle.pdf"):
    """Bundle DIGITAL de 3 documentos lógicos separados por hoja en blanco.

    Texto largo a propósito (mismo motivo que `_bundle_digital` en
    `test_split_sala_maquina_e2e.py`): `_texto_suficiente` exige >=100 chars y >=40
    char/pág, y con líneas cortas el motor lo tomaría por escaneado y llamaría a OCRmyPDF
    de verdad.
    """
    return build_pdf(case_dir / "00_Input" / "01_Drive EV" / nombre, [
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


def _manifiesto_de(case_dir, rel_path):
    """Carpeta y slug del bundle, resueltos como los resuelve el motor."""
    from core.utils import file_sha256, output_slug
    src = case_dir / "00_Input" / rel_path
    slug = output_slug(rel_path, file_sha256(src))
    return sm.carpeta_bundle_de(case_dir, slug), slug


# --- Tarea 4: preflight ------------------------------------------------------

def test_preflight_para_la_corrida_antes_de_escribir_el_primer_bundle(tmp_path, monkeypatch):
    """El manifiesto inválido del SEGUNDO bundle no puede llegar con el primero publicado.

    `validar_manifiesto` corre dentro de `_split_o_md`, documento a documento: sin
    preflight, el primer bundle ya escribió su generación y con `--force` (previa=[]) sus
    filas se pierden al persistir la cobertura.
    """
    case_dir = _caso(tmp_path, monkeypatch)
    _bundle(case_dir, "a.pdf")
    _bundle(case_dir, "z.pdf")
    cli.plan("W-TEST99")                       # deja los dos manifiestos propuestos
    carpeta_z, _ = _manifiesto_de(case_dir, "01_Drive EV/z.pdf")
    man = split.leer_manifiesto(carpeta_z)
    man["segmentos"][0]["doc_id"] = "../fuera"      # el letrado (o un script) lo rompe
    split.escribir_manifiesto(carpeta_z, man)

    with pytest.raises(typer.Exit) as exc:
        cli.apply("W-TEST99")

    assert exc.value.exit_code == 2
    sm_dir = sm._sala_maquina_dir(case_dir)
    assert not (sm_dir / "03_MD").exists(), "el primer bundle no puede haber escrito"
    assert not (sm_dir / "_cobertura.json").exists()


def test_preflight_veta_la_permutacion_con_la_cobertura_como_baseline(tmp_path, monkeypatch):
    case_dir = _caso(tmp_path, monkeypatch)
    _bundle(case_dir, "a.pdf")
    cli.plan("W-TEST99")
    carpeta, slug = _manifiesto_de(case_dir, "01_Drive EV/a.pdf")
    man = split.leer_manifiesto(carpeta)
    pps = [e["pp"] for e in man["segmentos"]]
    cli._guardar_cobertura(case_dir, [
        sm.DocCobertura(f"{slug}__{e['doc_id']}_{e['tipo']}", "01_Drive EV/a.pdf", "pypdf",
                        "ok", parent_slug=slug, paginas=pp, doc_id=e["doc_id"])
        for e, pp in zip(man["segmentos"], pps)])
    man["segmentos"][0]["pp"], man["segmentos"][1]["pp"] = pps[1], pps[0]   # permutación
    split.escribir_manifiesto(carpeta, man)

    with pytest.raises(typer.Exit) as exc:
        cli.apply("W-TEST99")

    assert exc.value.exit_code == 2


def test_preflight_no_mira_los_documentos_saltados(tmp_path, monkeypatch):
    """Un manifiesto legacy de un bundle que esta corrida NO procesa no bloquea nada."""
    case_dir = _caso(tmp_path, monkeypatch)
    _bundle(case_dir, "a.pdf")
    carpeta, _ = _manifiesto_de(case_dir, "01_Drive EV/a.pdf")
    carpeta.mkdir(parents=True, exist_ok=True)
    split.escribir_manifiesto(carpeta, {
        "fuente": "01_Drive EV/a.pdf", "bundle_sha256": "a" * 64, "delimitadores": [],
        "segmentos": [{"seg": 1, "pp": "1-1", "tipo": "X", "role": "documento"}]})
    docs = sm.plan(sm.inventariar(case_dir), estado_previo=set())
    saltados = [replace(d, skip=True) for d in docs]

    sm.preflight_manifiestos(case_dir, saltados, [])        # no lanza

    with pytest.raises(split.ManifestValidationError, match="retrofit"):
        sm.preflight_manifiestos(case_dir, docs, [])


def test_preflight_convierte_un_json_corrupto_en_salida_2(tmp_path, monkeypatch):
    """El fichero que el letrado edita a mano se rompe: eso es salida 2, no traceback."""
    case_dir = _caso(tmp_path, monkeypatch)
    _bundle(case_dir, "a.pdf")
    cli.plan("W-TEST99")
    carpeta, _ = _manifiesto_de(case_dir, "01_Drive EV/a.pdf")
    (carpeta / "_segmentacion.json").write_text('{"segmentos": [', encoding="utf-8")

    with pytest.raises(typer.Exit) as exc:
        cli.apply("W-TEST99")

    assert exc.value.exit_code == 2
