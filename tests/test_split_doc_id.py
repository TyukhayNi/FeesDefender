"""Identidad persistente del segmento de bundle: `doc_id`, ledger y slug sin sha.

Spec: docs/superpowers/specs/2026-08-01-identidad-segmento-bundle-design.md §3 (rev. 4).
"""
from __future__ import annotations

import pytest

from core import split_documental as split
from core.split_documental import ManifestValidationError
from tests._pdf_fixtures import build_pdf


def test_slug_no_depende_del_contenido():
    """Mismo (parent, doc_id, tipo) → mismo slug, cambien o no los bytes del segmento.

    El defecto en una línea: el slug llevaba el sha del PDF ya recortado, un artefacto
    DERIVADO, así que re-OCR-izar renombraba todos los artefactos del segmento y el
    reproceso añadía una generación al lado en vez de sustituirla.
    """
    a = split._slug_seg("bundle__aabbccdd", "d01", "DOC_ARRAS")
    b = split._slug_seg("bundle__aabbccdd", "d01", "DOC_ARRAS")
    assert a == b == "bundle__aabbccdd__d01_DOC_ARRAS"


@pytest.mark.parametrize("malo", ["../fuera", "d1", "D01", "d 01", "d01/x", "d01.pdf",
                                  "", "1", None, 7, "d01\n", "d١٢"])
def test_doc_id_no_canonico_se_rechaza(malo):
    """El formato es cerrado porque el `doc_id` es un campo EDITABLE que entra en una ruta.

    Los dos últimos son del hallazgo H-24, medidos: con `re.match(r"^d\\d{2,}$")` el `$`
    casaba antes del salto final (`"d01\\n"` pasaba y reventaba como OSError DENTRO de
    `materializar`) y `\\d` aceptaba dígitos árabes (`"d١٢"`, con `int(...) == 12`).
    """
    with pytest.raises(ManifestValidationError):
        split.validar_doc_id(malo)


def test_siguiente_doc_id_es_monotonico_y_crece_de_ancho():
    assert split.siguiente_doc_id("d01") == "d02"
    assert split.siguiente_doc_id("d09") == "d10"
    assert split.siguiente_doc_id("d99") == "d100"


def test_construir_manifiesto_acuna_doc_ids_y_abre_el_ledger():
    segs = [split.Segmento(1, 1, 4, "CEDULA_EMPLAZAMIENTO"), split.Segmento(2, 6, 12, "AUTO")]
    man = split.construir_manifiesto("01_Drive EV/b.pdf", "a" * 64, segs, {5})
    assert [e["doc_id"] for e in man["segmentos"]] == ["d01", "d02"]
    assert man["next_doc_id"] == "d03"
    assert man["retirados"] == []


def test_el_espejo_md_ensena_el_doc_id_y_pide_no_tocarlo(tmp_path):
    """El `.md` es lo que el letrado lee y edita: si no ve el `doc_id`, lo reasignará."""
    segs = [split.Segmento(1, 1, 4, "CEDULA_EMPLAZAMIENTO")]
    split.escribir_manifiesto(
        tmp_path, split.construir_manifiesto("01_Drive EV/b.pdf", "a" * 64, segs, set()))
    txt = (tmp_path / "_segmentacion.md").read_text(encoding="utf-8")
    assert "doc_id" in txt and "d01" in txt
    assert "NO toques" in txt


def test_destino_en_bundle_rechaza_una_ruta_que_se_sale(tmp_path):
    """§3.1: además del formato, el destino final se contiene.

    Y lo que NO hace, medido (H-08): con el prefijo `parent_slug__` delante, un doc_id
    `..\\..\\fuera` resuelve DENTRO de la carpeta —el prefijo absorbe el primer `..`— y
    la contención no lo caza. A ese lo para el formato canónico. Este test ejerce una
    forma que de verdad escapa, para no pasar por la razón equivocada.
    """
    carpeta = tmp_path / "02_Documentos" / "bundle"
    with pytest.raises(ManifestValidationError):
        split._destino_en_bundle(carpeta / ".." / "otro.pdf", carpeta)
    with pytest.raises(ManifestValidationError):
        split._destino_en_bundle(carpeta / "bundle__d01/../../fuera_X.pdf", carpeta)
    absorbida = carpeta / "bundle__..\\..\\fuera_X.pdf"
    assert split._destino_en_bundle(absorbida, carpeta) == absorbida


def test_materializar_rechaza_doc_id_no_canonico_antes_de_tocar_el_disco(tmp_path):
    """Traversal, en Windows real: no aparece NADA fuera de la carpeta del bundle.

    La 2ª revisión adversarial lo ejecutó sobre la rev. 2 del spec: un `doc_id` con
    separadores escribía fuera del bundle porque `materializar` armaba `destino_pdf` sin
    validar nada.
    """
    pdf = build_pdf(tmp_path / "j.pdf",
                    [["CEDULA DE EMPLAZAMIENTO"], [], ["FACTURA", "Total 100"]])
    man = {"fuente": "01_Drive EV/j.pdf", "bundle_sha256": "d" * 64,
           "segmentos": [{"seg": 1, "doc_id": "..\\..\\fuera", "pp": "1-1",
                          "tipo": "X", "role": "documento"}],
           "delimitadores": [2], "next_doc_id": "d02", "retirados": []}
    carpeta = tmp_path / "02_Documentos" / "bundle-slug"
    antes = sorted(p.name for p in tmp_path.iterdir())

    with pytest.raises(ManifestValidationError):
        split.materializar(pdf, man, carpeta, parent_slug="bundle-slug",
                           parent_sha256="d" * 64, bundle_rel_path="01_Drive EV/j.pdf")

    assert sorted(p.name for p in tmp_path.iterdir()) == antes, "escribió fuera del bundle"
    assert not carpeta.exists(), "la validación debe ir ANTES incluso del mkdir"
