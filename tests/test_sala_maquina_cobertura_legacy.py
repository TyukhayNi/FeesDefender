"""Cobertura previa en casos SIN `_cobertura.json` (corridas anteriores a #84).

Encontrado el 2026-07-30 al ejecutar D1 (`MEJORAS #90`) sobre W-02XOR7: el caso tiene
`_cobertura.md` con 169 filas y `_sala_maquina_state.json`, pero NO `_cobertura.json` —
se procesó antes de que ese fichero existiera. `_cobertura_previa` devolvía `[]`, así que
cualquier corrida incremental fusionaba contra vacío y `_escribir_cobertura_md`
REESCRIBÍA el `.md` con solo el delta: 169 filas de cadena de custodia reducidas a 2, en
silencio y sin error. Es la variante-migración del bug de VALERO, y no la introduce
`--solo`: la activa. `apply` normal tenía el mismo agujero.

El detector ya resolvía esto (`detectar_ocr_ciego.filas_ok` reconstruye desde el
frontmatter de `03_MD/`); lo que faltaba era la simetría en el lado que PERSISTE.

Honestidad de la reconstrucción: el frontmatter que escribe `_escribir_md` guarda
`source_path`, `extractor`, `chars`, `ocr` y `ocr_quality`, pero **no** el `sha256` del
origen ni los campos de bundle (`parent_*`, `role`, `paginas`). Las filas reconstruidas
salen por tanto con sha vacío y una nota que lo declara: preservar el registro no es
inventar los datos que no están.
"""
from __future__ import annotations

import json

import pytest

import scripts.sala_maquina as cli
from core import sala_maquina as sm


def _escribir_md_legacy(case_dir, slug, *, rel_path, metodo, estado, chars, ocr=False):
    """Un MD tal y como lo dejó una corrida vieja, con su frontmatter real."""
    md_dir = sm._sala_maquina_dir(case_dir) / "03_MD"
    md_dir.mkdir(parents=True, exist_ok=True)
    cuerpo = "x" * chars
    (md_dir / f"{slug}.md").write_text(
        "---\n"
        f"case_id: BaRS8\ntipo: documento_procesado\nfase: 01_Procesado\n"
        f"source_path: {rel_path}\nextractor: {metodo}\nchars: {chars}\n"
        f"ocr: {'true' if ocr else 'false'}\nocr_quality: {estado}\n"
        "---\n\n" + cuerpo,
        encoding="utf-8")


@pytest.fixture
def caso_legacy(tmp_path, monkeypatch):
    """Caso con MD y estado, SIN `_cobertura.json` (el retrato de W-02XOR7)."""
    case_dir = tmp_path / "BaRS8 - Prueba - (W-TEST88) - Negativa oferta aceptada"
    (case_dir / "00_Input" / "01_Drive EV").mkdir(parents=True)
    (case_dir / "00_Input" / "01_Drive EV" / "expose.pdf").write_bytes(b"%PDF-1.4 expose")
    (case_dir / "00_Input" / "01_Drive EV" / "informe.pdf").write_bytes(b"%PDF-1.4 informe")

    _escribir_md_legacy(case_dir, "expose__aaaaaaaa",
                        rel_path="01_Drive EV/expose.pdf", metodo="pypdf",
                        estado="ok", chars=9786)
    _escribir_md_legacy(case_dir, "informe__bbbbbbbb",
                        rel_path="01_Drive EV/informe.pdf", metodo="ocr",
                        estado="ok", chars=8912, ocr=True)

    monkeypatch.setattr(cli, "caso_path", lambda cid: case_dir)
    monkeypatch.setattr(cli, "append_event", lambda cid, ev, *, details=None: None)
    monkeypatch.setattr(cli, "_atomizar_correo", lambda cid, cd: None)
    return case_dir


def test_cobertura_previa_reconstruye_desde_los_md_si_falta_el_json(caso_legacy):
    """Sin `_cobertura.json`, las filas salen del frontmatter en vez de perderse."""
    cob = cli._cobertura_previa(caso_legacy)

    por_rel = {c.rel_path: c for c in cob}
    assert set(por_rel) == {"01_Drive EV/expose.pdf", "01_Drive EV/informe.pdf"}
    assert por_rel["01_Drive EV/expose.pdf"].chars == 9786
    assert por_rel["01_Drive EV/expose.pdf"].metodo == "pypdf"
    assert por_rel["01_Drive EV/expose.pdf"].estado == "ok"
    assert por_rel["01_Drive EV/informe.pdf"].ocr is True


def test_la_fila_reconstruida_declara_que_lo_es_y_no_finge_sha(caso_legacy):
    """El frontmatter no guarda el sha del origen: la fila lo dice en vez de inventarlo."""
    cob = cli._cobertura_previa(caso_legacy)

    fila = next(c for c in cob if c.rel_path == "01_Drive EV/expose.pdf")
    assert fila.sha256 == ""
    assert "reconstruida" in fila.nota.lower()


def test_el_json_gana_al_md_cuando_existe(caso_legacy):
    """Con `_cobertura.json` presente NO se reconstruye: el registro manda sobre la vista."""
    cli._guardar_cobertura(caso_legacy, [
        sm.DocCobertura(slug="expose__aaaaaaaa", rel_path="01_Drive EV/expose.pdf",
                        metodo="pypdf", estado="ok", chars=1, sha256="c" * 64)])

    cob = cli._cobertura_previa(caso_legacy)

    assert len(cob) == 1
    assert cob[0].chars == 1
    assert cob[0].sha256 == "c" * 64


def test_el_acotado_no_borra_el_registro_de_los_demas_en_un_caso_legacy(caso_legacy,
                                                                       monkeypatch):
    """El defecto que motivó todo esto, sobre el caso completo.

    Antes: 2 filas reconstruibles → `previa=[]` → el `.md` quedaba con 1 fila y la otra
    desaparecía. En W-02XOR7 eso eran 169 filas reducidas a 2.
    """
    nueva = sm.DocCobertura(slug="expose__aaaaaaaa", rel_path="01_Drive EV/expose.pdf",
                            metodo="ocr", estado="ok", chars=13_732, ocr=True,
                            sha256="d" * 64)
    monkeypatch.setattr(cli.sm, "ejecutar", lambda *a, **k: [nueva])

    cli.apply("W-TEST88", solo=["01_Drive EV/expose.pdf"])

    guardada = json.loads(
        (sm._sala_maquina_dir(caso_legacy) / cli._COBERTURA).read_text(encoding="utf-8"))
    por_rel = {c["rel_path"]: c for c in guardada}
    assert "01_Drive EV/informe.pdf" in por_rel, "se perdió el registro del no pedido"
    assert por_rel["01_Drive EV/informe.pdf"]["chars"] == 8912
    assert por_rel["01_Drive EV/expose.pdf"]["chars"] == 13_732, "no entró la medición nueva"

    md = (caso_legacy / "01_Procesado" / "_revisar" / "_cobertura.md").read_text(
        encoding="utf-8")
    assert "informe.pdf" in md, "la vista humana perdió la fila del no pedido"
