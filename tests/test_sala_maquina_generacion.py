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


# --- Tarea 5: publicación por generación -------------------------------------

def _tres(sm_dir, carpeta, slug):
    return sm._rutas_de(sm_dir, carpeta, slug)


def _sembrar(sm_dir, carpeta, slug, texto):
    for p in _tres(sm_dir, carpeta, slug):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(texto, encoding="utf-8")


def _staging_con(carpeta, slug, texto="nuevo"):
    staging = carpeta / split.STAGING
    staging.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "md", "txt"):
        (staging / f"{slug}.{ext}").write_text(texto, encoding="utf-8")
    return staging


def test_publicar_archiva_la_generacion_anterior_como_conjunto(tmp_path):
    """Las tres representaciones viajan juntas: no se publica media generación."""
    case_dir = tmp_path / "caso"
    sm_dir = sm._sala_maquina_dir(case_dir)
    carpeta = sm_dir / "02_Documentos" / "b"
    _sembrar(sm_dir, carpeta, "b__d01_A", "viejo")
    staging = _staging_con(carpeta, "b__d01_A")

    archivados = sm.publicar_segmentos(case_dir, sm_dir, carpeta,
                                       publicaciones=[("b__d01_A", "")], retirados=[],
                                       sello="2026-08-02_101010")

    pdf, md, txt = _tres(sm_dir, carpeta, "b__d01_A")
    assert [p.read_text(encoding="utf-8") for p in (pdf, md, txt)] == ["nuevo"] * 3
    viejo = case_dir / sm.VERSIONES_ANTERIORES / "reproceso_2026-08-02_101010"
    assert sorted(p.name for p in viejo.iterdir()) == ["b__d01_A.md", "b__d01_A.pdf",
                                                       "b__d01_A.txt"]
    assert len(archivados) == 3
    assert not staging.exists(), "el staging se retira al publicar"


def test_publicar_archiva_tambien_el_slug_previo_cuando_cambia_el_tipo(tmp_path):
    """Mismo doc_id, TIPO distinto ⇒ slug distinto: el renombrado es detectable."""
    case_dir = tmp_path / "caso"
    sm_dir = sm._sala_maquina_dir(case_dir)
    carpeta = sm_dir / "02_Documentos" / "b"
    _sembrar(sm_dir, carpeta, "b__d01_DOC_A", "viejo")
    _staging_con(carpeta, "b__d01_DOC_B")

    sm.publicar_segmentos(case_dir, sm_dir, carpeta,
                          publicaciones=[("b__d01_DOC_B", "b__d01_DOC_A")], retirados=[],
                          sello="2026-08-02_101010")

    assert not _tres(sm_dir, carpeta, "b__d01_DOC_A")[0].exists(), "quedó el slug viejo"
    assert _tres(sm_dir, carpeta, "b__d01_DOC_B")[0].read_text(encoding="utf-8") == "nuevo"
    viejo = case_dir / sm.VERSIONES_ANTERIORES / "reproceso_2026-08-02_101010"
    assert len(list(viejo.iterdir())) == 3


def test_publicar_archiva_la_generacion_del_esquema_viejo(tmp_path):
    """Sin esto, `--force` sobre un bundle legacy deja los slugs con sha al lado.

    Y esos huérfanos no son inertes: no tienen fila, el guard los ve y aborta con salida
    3 — inutilizando la única vía de escape que la pieza A ofrece para un manifiesto
    legacy mientras la pieza B siga bloqueada.
    """
    case_dir = tmp_path / "caso"
    sm_dir = sm._sala_maquina_dir(case_dir)
    carpeta = sm_dir / "02_Documentos" / "b"
    _sembrar(sm_dir, carpeta, "b__seg01_A__aabbccdd", "viejo")     # esquema viejo
    _staging_con(carpeta, "b__d01_A")

    sm.publicar_segmentos(case_dir, sm_dir, carpeta, publicaciones=[("b__d01_A", "")],
                          retirados=[], sello="2026-08-02_101010")

    assert sorted(p.name for p in carpeta.glob("*.pdf")) == ["b__d01_A.pdf"]
    viejo = case_dir / sm.VERSIONES_ANTERIORES / "reproceso_2026-08-02_101010"
    assert sorted(p.name for p in viejo.iterdir()) == [
        "b__seg01_A__aabbccdd.md", "b__seg01_A__aabbccdd.pdf", "b__seg01_A__aabbccdd.txt"]


def test_el_staging_residual_no_se_publica_sin_filtrar(tmp_path):
    """Un residuo que `rmtree(ignore_errors=True)` no pudo borrar no es de esta corrida.

    Y los `.md`/`.txt` rancios aterrizaban en la carpeta del bundle, donde no vive ninguna
    representación legítima y donde ningún guard los miraba nunca.
    """
    case_dir = tmp_path / "caso"
    sm_dir = sm._sala_maquina_dir(case_dir)
    carpeta = sm_dir / "02_Documentos" / "b"
    staging = _staging_con(carpeta, "b__d01_A")
    (staging / "indice.json").write_text("{}", encoding="utf-8")
    for nombre in ("b__d09_RANCIO.md", "b__d09_RANCIO.txt", "b__d09_RANCIO.pdf"):
        (staging / nombre).write_text("residuo de una corrida abortada", encoding="utf-8")

    sm.publicar_segmentos(case_dir, sm_dir, carpeta, publicaciones=[("b__d01_A", "")],
                          retirados=[], sello="2026-08-02_101010")

    assert sorted(p.name for p in carpeta.iterdir()) == ["b__d01_A.pdf", "indice.json"]
    archivo = case_dir / sm.VERSIONES_ANTERIORES / "reproceso_2026-08-02_101010"
    assert sorted(p.name for p in archivo.iterdir()) == [
        "b__d09_RANCIO.md", "b__d09_RANCIO.pdf", "b__d09_RANCIO.txt"]


def test_si_el_archivado_falla_no_se_publica_ninguna(tmp_path, monkeypatch):
    """El conjunto manda: un archivado a medias deja la generación nueva SIN publicar."""
    case_dir = tmp_path / "caso"
    sm_dir = sm._sala_maquina_dir(case_dir)
    carpeta = sm_dir / "02_Documentos" / "b"
    _sembrar(sm_dir, carpeta, "b__d01_A", "viejo")
    staging = _staging_con(carpeta, "b__d01_A")

    real = Path.replace

    def _falla_en_el_md(self, destino):
        if self.suffix == ".md" and sm.VERSIONES_ANTERIORES in str(destino):
            raise OSError("disco lleno")
        return real(self, destino)

    monkeypatch.setattr(Path, "replace", _falla_en_el_md)

    with pytest.raises(OSError):
        sm.publicar_segmentos(case_dir, sm_dir, carpeta,
                              publicaciones=[("b__d01_A", "")], retirados=[],
                              sello="2026-08-02_101010")

    # Sin `monkeypatch.undo()`: revertiría también los dobles del caso, y estas
    # comprobaciones solo leen (el parche está en `replace`, no en `read_text`).
    assert (staging / "b__d01_A.pdf").read_text(encoding="utf-8") == "nuevo", \
        "la generación nueva sigue en staging, sin publicar"
    assert _tres(sm_dir, carpeta, "b__d01_A")[1].read_text(encoding="utf-8") == "viejo"


# --- Tarea 6: el registro no manda sobre el trabajo ya publicado ---------------

def test_un_fallo_al_registrar_el_evento_no_tira_las_filas(tmp_path, monkeypatch):
    """§7.2: hoy la excepción sube a `ejecutar` y se pierden las filas de TODOS los
    segmentos del bundle — el trabajo ya está en disco y el registro lo negaría.

    Y no es un fallo de laboratorio: `append_event` escribe en `_intake_log.jsonl`, que
    vive en el Drive; un fichero bloqueado por el cliente de sincronización basta.
    """
    case_dir = _caso(tmp_path, monkeypatch)
    _bundle(case_dir, "a.pdf")

    def _revienta(case_id, evento, *, details=None):
        raise OSError("log bloqueado por otro proceso")
    monkeypatch.setattr(sm, "append_event", _revienta)

    docs = sm.plan(sm.inventariar(case_dir), estado_previo=set())
    cob = sm.ejecutar(case_dir, docs, case_id="W-TEST99")

    segmentos = [c for c in cob if c.doc_id]
    assert len(segmentos) == 3, "se perdieron las filas por un fallo de log"
    assert all("evento split_documental no registrado" in c.nota for c in segmentos), \
        "el fallo del registro debe quedar declarado en la cobertura"
    sm_dir = sm._sala_maquina_dir(case_dir)
    carpeta, _ = _manifiesto_de(case_dir, "01_Drive EV/a.pdf")
    assert len(list(carpeta.glob("*.pdf"))) == 3, "y el trabajo publicado sigue publicado"


def test_un_bundle_que_deja_de_serlo_retira_su_generacion(tmp_path, monkeypatch):
    """El `B0` de la ronda 1 (H-01), de punta a punta.

    Un reproceso en el que `detectar` ya no ve el bundle —diez chars de ruido en la hoja
    en blanco bastan, o un fallo del detector que degrada a propósito— dejaba los N PDF de
    segmento sin fila: con `--force` el guard abortaba con salida 3 y relanzar no cambiaba
    nada; sin `--force` las N filas viejas convivían con la nueva. Ahora la generación se
    archiva entera y la corrida cierra en 0 con UNA sola fila para ese `rel_path`.
    """
    case_dir = _caso(tmp_path, monkeypatch)
    _bundle(case_dir, "a.pdf")
    cli.apply("W-TEST99")                                  # generación de bundle: 3 segmentos
    sm_dir = sm._sala_maquina_dir(case_dir)
    carpeta, slug = _manifiesto_de(case_dir, "01_Drive EV/a.pdf")
    assert len(list(carpeta.glob("*.pdf"))) == 3

    def _revienta(*a, **k):
        raise RuntimeError("PDF ilegible para el detector")
    monkeypatch.setattr(sm.split, "detectar", _revienta)

    cli.apply("W-TEST99", force=True)                      # no debe lanzar typer.Exit

    filas = json.loads((sm_dir / "_cobertura.json").read_text(encoding="utf-8"))
    de_este = [f for f in filas if f["rel_path"] == "01_Drive EV/a.pdf"]
    assert len(de_este) == 1 and not de_este[0]["doc_id"], "sobrevivieron filas de segmento"
    assert not carpeta.exists(), "la carpeta del bundle debe quedar retirada"
    archivados = sorted((case_dir / sm.VERSIONES_ANTERIORES).glob("reproceso_*/*"))
    assert len(archivados) >= 9 + 2, "3 segmentos × 3 representaciones + índice + manifiesto"
    assert (sm_dir / "03_MD" / f"{slug}.md").exists(), "el MD suelto del passthrough"
