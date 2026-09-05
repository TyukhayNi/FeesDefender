"""Vía A de `MEJORAS #147` (acción 11 de la fila 21): un fichero, un espejo.

Contrato bajo prueba:
- D1  `plan()` marca `duplicado_de` en toda copia con el mismo `sha256` que un fichero ANTERIOR
      del inventario; el primero es el titular; shas distintos no se marcan.
- D2  `ejecutar()` con dos copias byte-idénticas en carpetas distintas: UN espejo (el del titular),
      DOS filas de custodia; la copia sale con método `duplicado`, sin procesarse (el extractor
      corre una sola vez), y su nota dice dónde está el espejo; el titular anota «también en …».
- D3  La copia hereda el PEOR estado del titular (un titular `empty` no puede tener una copia `ok`).
- D4  Copia de un bundle: la nota apunta al slug del bundle y dice cuántos documentos lógicos.
- D5  Si el titular no dejó filas (situación que no debería darse), la copia se procesa como un
      documento más: nunca se colapsa contra nada.
- D6  El preview del CLI cuenta los duplicados aparte y NO los suma a las rutas.
- D7  `fusionar_cobertura` conserva las dos filas (identidad por `rel_path`), como siempre.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from core import sala_maquina as sm
from core.utils import file_sha256

TEXTO = ("Encargo de mediación firmado por el propietario. Honorarios de intermediación "
         "del cinco por ciento sobre el precio final de la operación. ")


def _pdf_con_texto(path: Path, texto: str = TEXTO) -> None:
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(str(path))
    c.drawString(72, 720, texto)
    c.showPage()
    c.save()


def _caso_con_copias(tmp_path: Path):
    """El escenario medido en W-02Q38C: el mismo PDF en `ARRAS/` y en `OFERTAS/…`."""
    case = tmp_path / "EV-2026-001"
    a = case / "00_Input" / "01_Drive EV" / "ARRAS"
    b = case / "00_Input" / "01_Drive EV" / "OFERTAS" / "OFERTA 1"
    a.mkdir(parents=True)
    b.mkdir(parents=True)
    _pdf_con_texto(a / "Certificado titularidad.pdf")
    (b / "Certificado titularidad bancaria.pdf").write_bytes((a / "Certificado titularidad.pdf").read_bytes())
    return case


def _sin_ocr(*_a, **_k):
    raise AssertionError("un PDF con capa de texto no debe OCR-izarse")


# ── D1 ─────────────────────────────────────────────────────────────────────────────────

def test_d1_plan_marca_la_copia_y_no_el_titular(tmp_path):
    case = _caso_con_copias(tmp_path)
    p = sm.plan(sm.inventariar(case), set())
    assert [d.rel_path for d in p] == ["01_Drive EV/ARRAS/Certificado titularidad.pdf",
                                       "01_Drive EV/OFERTAS/OFERTA 1/Certificado titularidad bancaria.pdf"]
    assert p[0].duplicado_de == ""
    assert p[1].duplicado_de == p[0].rel_path
    assert p[0].sha256 == p[1].sha256 and p[0].slug != p[1].slug


def test_d1_shas_distintos_no_se_marcan(tmp_path):
    case = _caso_con_copias(tmp_path)
    otro = case / "00_Input" / "01_Drive EV" / "ARRAS" / "otro.pdf"
    _pdf_con_texto(otro, TEXTO + "distinto")
    p = sm.plan(sm.inventariar(case), set())
    marcados = [d.rel_path for d in p if d.duplicado_de]
    assert marcados == ["01_Drive EV/OFERTAS/OFERTA 1/Certificado titularidad bancaria.pdf"]


def test_d1_la_copia_hereda_el_skip_del_titular(tmp_path):
    case = _caso_con_copias(tmp_path)
    inv = sm.inventariar(case)
    p = sm.plan(inv, {inv[0]["sha256"]})
    assert all(d.skip for d in p), "mismo sha ⇒ mismo skip: ninguna se reprocesa"


# ── D2 / D3 / D4 / D5 ──────────────────────────────────────────────────────────────────

def test_d2_un_espejo_dos_filas_y_el_extractor_corre_una_vez(tmp_path, monkeypatch):
    case = _caso_con_copias(tmp_path)
    monkeypatch.setattr(sm, "ocr_pdf_escalera", _sin_ocr)
    llamadas = []
    original = sm._try_pypdf

    def _contando(p):
        llamadas.append(Path(p).name)
        return original(p)
    monkeypatch.setattr(sm, "_try_pypdf", _contando)

    p = sm.plan(sm.inventariar(case), set())
    cob = sm.ejecutar(case, p, case_id="EV-2026-001")

    titular, copia = p
    md_dir = case / "01_Procesado" / "02_Sala de máquina" / "03_MD"
    assert sorted(x.name for x in md_dir.glob("*.md")) == [f"{titular.slug}.md"], "UN espejo"
    assert len(cob) == 2, "DOS filas de custodia"
    por_rel = {c.rel_path: c for c in cob}
    f_cop = por_rel[copia.rel_path]
    assert f_cop.metodo == sm.METODO_DUPLICADO and f_cop.sha256 == copia.sha256
    assert f_cop.estado == "ok" and f_cop.chars == 0 and f_cop.ocr is False
    assert titular.rel_path in f_cop.nota and f"03_MD/{titular.slug}" in f_cop.nota
    f_tit = por_rel[titular.rel_path]
    assert f_tit.metodo == "pypdf" and "también en " + copia.rel_path in f_tit.nota
    assert llamadas.count("Certificado titularidad bancaria.pdf") == 0, "la copia no se extrae"


def test_d2_el_render_de_cobertura_muestra_las_dos_procedencias(tmp_path, monkeypatch):
    case = _caso_con_copias(tmp_path)
    monkeypatch.setattr(sm, "ocr_pdf_escalera", _sin_ocr)
    cob = sm.ejecutar(case, sm.plan(sm.inventariar(case), set()), case_id="EV-2026-001")
    md = sm.render_cobertura(cob)
    assert "duplicado" in md and "también en" in md
    assert "0 de 2 documentos requieren tu revisión" in md


def test_d3_la_copia_hereda_el_peor_estado_del_titular(tmp_path, monkeypatch):
    case = _caso_con_copias(tmp_path)
    # el titular sale `empty` (la escalera no recupera nada)
    monkeypatch.setattr(sm, "_try_pypdf", lambda p: "")
    monkeypatch.setattr(sm, "_pdf_num_paginas", lambda p: 1)

    def _ocr_vacio(entrada, salida, **_k):
        raise RuntimeError("ocrmypdf ausente")
    monkeypatch.setattr(sm, "ocr_pdf_escalera", _ocr_vacio)
    cob = sm.ejecutar(case, sm.plan(sm.inventariar(case), set()), case_id="EV-2026-001")
    estados = {c.metodo: c.estado for c in cob}
    assert estados["ocr"] == "empty"
    assert estados[sm.METODO_DUPLICADO] == "empty", "la copia no puede salir `ok` con el titular `empty`"


def test_d4_copia_de_un_bundle_apunta_al_bundle(tmp_path, monkeypatch):
    from tests._pdf_fixtures import build_pdf
    case = tmp_path / "EV-2026-001"
    (case / "00_Input" / "01_Drive EV" / "A").mkdir(parents=True)
    (case / "00_Input" / "01_Drive EV" / "B").mkdir(parents=True)
    paginas = [
        ["CEDULA DE EMPLAZAMIENTO", "Juzgado de Primera Instancia numero cinco de Barcelona",
         "En la villa de Barcelona se emplaza a la parte demandada para comparecer",
         "en el plazo legalmente establecido conforme a la Ley de Enjuiciamiento Civil."],
        [],
        ["FACTURA por servicios de mediacion inmobiliaria efectivamente prestados",
         "Se detallan a continuacion los conceptos facturados y el importe total",
         "correspondiente a la operacion de intermediacion realizada por la agencia",
         "con el desglose de la base imponible y el impuesto sobre el valor anadido."],
    ]
    src = build_pdf(case / "00_Input" / "01_Drive EV" / "A" / "bundle.pdf", paginas)
    (case / "00_Input" / "01_Drive EV" / "B" / "bundle copia.pdf").write_bytes(Path(src).read_bytes())
    monkeypatch.setattr(sm, "ocr_pdf_escalera", _sin_ocr)
    monkeypatch.setattr(sm, "append_event", lambda *a, **k: None)
    p = sm.plan(sm.inventariar(case), set())
    cob = sm.ejecutar(case, p, case_id="EV-2026-001")
    copia = [c for c in cob if c.metodo == sm.METODO_DUPLICADO]
    segmentos = [c for c in cob if c.parent_slug]
    if len(segmentos) < 2:
        pytest.skip("el detector no segmentó el bundle en este entorno; D4 necesita ≥2 documentos lógicos")
    assert len(copia) == 1
    assert f"03_MD/{p[0].slug}" in copia[0].nota and f"({len(segmentos)} documentos lógicos)" in copia[0].nota
    assert all("también en " + p[1].rel_path in s.nota for s in segmentos)


def test_d5_sin_filas_del_titular_la_copia_se_procesa(tmp_path, monkeypatch):
    """Nunca colapsar contra nada: si el titular no dejó filas, la copia es un documento más."""
    case = _caso_con_copias(tmp_path)
    monkeypatch.setattr(sm, "ocr_pdf_escalera", _sin_ocr)
    p = sm.plan(sm.inventariar(case), set())
    solo_copia = [p[1]]                     # el titular no está en la corrida
    cob = sm.ejecutar(case, solo_copia, case_id="EV-2026-001")
    assert len(cob) == 1 and cob[0].metodo == "pypdf" and cob[0].estado == "ok"
    assert (case / "01_Procesado" / "02_Sala de máquina" / "03_MD" / f"{p[1].slug}.md").exists()


# ── D6 / D7 ────────────────────────────────────────────────────────────────────────────

def test_d6_el_preview_cuenta_los_duplicados_aparte(tmp_path, monkeypatch, capsys):
    import scripts.sala_maquina as cli
    case = _caso_con_copias(tmp_path)
    monkeypatch.setattr(cli, "caso_path", lambda cid: case)
    monkeypatch.setattr(cli, "append_event", lambda destino, ev, *, details=None, case_id=None: None)
    monkeypatch.setattr(sm, "append_event", lambda destino, ev, *, details=None, case_id=None: None)
    monkeypatch.setattr(cli, "_atomizar_correo", lambda cid, cd: None)
    monkeypatch.setattr(cli.case_locator, "resolve_ref", lambda ref: ref)
    cli.plan("W-TEST99")
    out = capsys.readouterr().out
    assert "pdf: 1" in out, out
    assert "duplicados: 1" in out, out


def test_d8_la_copia_no_consume_intentos_del_titular(tmp_path, monkeypatch):
    """Un titular que falla gasta UN intento por corrida, no dos: la copia comparte el sha y no
    se procesa, así que no puede contar. Sin esto `MAX_INTENTOS` (3) se agotaba en dos corridas."""
    import scripts.sala_maquina as cli
    case = _caso_con_copias(tmp_path)
    monkeypatch.setattr(cli, "caso_path", lambda cid: case)
    monkeypatch.setattr(cli, "append_event", lambda destino, ev, *, details=None, case_id=None: None)
    monkeypatch.setattr(sm, "append_event", lambda destino, ev, *, details=None, case_id=None: None)
    monkeypatch.setattr(cli, "_atomizar_correo", lambda cid, cd: None)
    monkeypatch.setattr(cli.case_locator, "resolve_ref", lambda ref: ref)
    monkeypatch.setattr(sm, "_try_pypdf", lambda p: "")
    monkeypatch.setattr(sm, "_pdf_num_paginas", lambda p: 1)

    def _ocr_falla(entrada, salida, **_k):
        raise RuntimeError("ocrmypdf ausente")
    monkeypatch.setattr(sm, "ocr_pdf_escalera", _ocr_falla)

    cli.apply("W-TEST99")
    sha = sm.inventariar(case)[0]["sha256"]
    intentos = cli._intentos_previos(case)
    assert intentos == {sha: 1}, intentos
    cli.apply("W-TEST99")
    assert cli._intentos_previos(case) == {sha: 2}


def _cli(monkeypatch, case):
    import scripts.sala_maquina as cli
    monkeypatch.setattr(cli, "caso_path", lambda cid: case)
    monkeypatch.setattr(cli, "append_event", lambda destino, ev, *, details=None, case_id=None: None)
    monkeypatch.setattr(sm, "append_event", lambda destino, ev, *, details=None, case_id=None: None)
    monkeypatch.setattr(cli, "_atomizar_correo", lambda cid, cd: None)
    monkeypatch.setattr(cli.case_locator, "resolve_ref", lambda ref: ref)
    return cli


# ── R1 de Codex: D9-D15 ────────────────────────────────────────────────────────────────

def test_d9_el_titular_es_quien_sabe_extraer_no_el_primero(tmp_path, monkeypatch):
    """R1/H-01: un DOCX sin extensión en `A/` (sin_soporte) y sus mismos bytes en `B/x.docx`
    (nativo). El titular tiene que ser la copia que sabe extraer, y el texto tiene que salir."""
    from docx import Document
    case = tmp_path / "EV-2026-001"
    (case / "00_Input" / "A").mkdir(parents=True)
    (case / "00_Input" / "B").mkdir(parents=True)
    d = Document()
    d.add_paragraph("Encargo firmado por las partes con honorarios de intermediacion. " * 10)
    d.save(case / "00_Input" / "B" / "encargo.docx")
    (case / "00_Input" / "A" / "encargo").write_bytes((case / "00_Input" / "B" / "encargo.docx").read_bytes())
    p = sm.plan(sm.inventariar(case), set())
    por_rel = {x.rel_path: x for x in p}
    assert por_rel["B/encargo.docx"].duplicado_de == ""
    assert por_rel["A/encargo"].duplicado_de == "B/encargo.docx"
    cob = sm.ejecutar(case, p, case_id="EV-2026-001")
    estados = {c.rel_path: (c.metodo, c.estado) for c in cob}
    assert estados["B/encargo.docx"] == ("nativo", "ok")
    assert estados["A/encargo"][0] == sm.METODO_DUPLICADO
    assert list((case / "01_Procesado" / "02_Sala de máquina" / "03_MD").glob("*.md"))


def test_d9b_titular_sin_soporte_en_la_corrida_no_cancela_la_copia(tmp_path, monkeypatch):
    """Y si aun así el titular acaba `sin_soporte` (todas sus filas), la copia se procesa."""
    case = _caso_con_copias(tmp_path)
    monkeypatch.setattr(sm, "ocr_pdf_escalera", _sin_ocr)
    p = sm.plan(sm.inventariar(case), set())
    from dataclasses import replace
    p[0] = replace(p[0], ruta="sin_soporte")       # el titular no sabe extraer
    cob = sm.ejecutar(case, p, case_id="EV-2026-001")
    assert [c.metodo for c in cob] == ["sin_soporte", "pypdf"]
    assert cob[1].estado == "ok"


def test_d10_el_validador_crm_no_pide_espejo_a_la_copia():
    """R1/H-02: la copia no es legible ni ilegible para `corpus_legible`: su texto está en el
    espejo del titular, que entra por su propia fila."""
    from core.crm_ficha_validacion import corpus_legible
    filas = [
        {"rel_path": "A/cert.pdf", "slug": "cert__aaaa1111", "estado": "ok", "metodo": "pypdf"},
        {"rel_path": "B/cert bancario.pdf", "slug": "cert_bancario__aaaa1111", "estado": "ok",
         "metodo": "duplicado", "alias_de": "cert__aaaa1111"},
        {"rel_path": "C/escaneo.pdf", "slug": "escaneo__bbbb2222", "estado": "empty", "metodo": "ocr"},
    ]
    legibles, ilegibles = corpus_legible(filas)
    assert legibles == ("cert__aaaa1111",)
    assert ilegibles == ("C/escaneo.pdf",)


def test_d11_reconciliar_alias_tras_reprocesar_al_titular(tmp_path, monkeypatch):
    """R1/H-04: `apply` deja titular y copia `low`; `apply --solo <titular>` lo pasa a `ok`.
    La copia tiene que seguirle (estado y `alias_de`) y el titular recuperar «también en»."""
    case = _caso_con_copias(tmp_path)
    cli = _cli(monkeypatch, case)
    monkeypatch.setattr(sm, "ocr_pdf_escalera", _sin_ocr)
    real = sm._calidad
    monkeypatch.setattr(sm, "_calidad", lambda *a: ("low", "sonda"))
    cli.apply("W-TEST99")
    assert [c.estado for c in cli._cobertura_previa(case)] == ["low", "low"]
    monkeypatch.setattr(sm, "_calidad", real)
    p = sm.plan(sm.inventariar(case), set())
    cli.apply("W-TEST99", solo=[p[0].rel_path])
    cob = cli._cobertura_previa(case)
    por_rel = {c.rel_path: c for c in cob}
    assert por_rel[p[0].rel_path].estado == "ok" and "también en " + p[1].rel_path in por_rel[p[0].rel_path].nota
    assert por_rel[p[1].rel_path].estado == "ok" and por_rel[p[1].rel_path].metodo == sm.METODO_DUPLICADO
    assert por_rel[p[1].rel_path].alias_de == p[0].slug


def test_d11b_reconciliar_alias_es_puro_e_idempotente():
    tit = sm.DocCobertura("cert__aaaa1111", "A/cert.pdf", "pypdf", "low", 500, False, "", "a" * 64)
    cop = sm.DocCobertura("cert_b__aaaa1111", "B/cert b.pdf", sm.METODO_DUPLICADO, "ok", 0, False, "copia", "a" * 64)
    out = sm.reconciliar_alias([tit, cop])
    assert out[1].estado == "low" and out[1].alias_de == "cert__aaaa1111"
    assert out[0].nota.count("también en B/cert b.pdf") == 1
    sm.reconciliar_alias(out)
    assert out[0].nota.count("también en B/cert b.pdf") == 1, "idempotente"
    # un alias sin productoras se deja como está (no hay contra qué reconciliar)
    huerfano = sm.DocCobertura("x__cccc3333", "C/x.pdf", sm.METODO_DUPLICADO, "ok", 0, False, "copia", "c" * 64)
    assert sm.reconciliar_alias([huerfano])[0].estado == "ok"


@pytest.mark.parametrize("mismo_nombre", [False, True])
def test_d12_solo_copia_no_reabre_la_doble_extraccion(tmp_path, monkeypatch, mismo_nombre):
    """R1/H-05: tras un `apply`, `apply --solo <copia>` encuentra el espejo del titular en disco
    y emite alias: ni segundo MD (stems distintos) ni reescritura del compartido (mismo stem)."""
    case = _caso_con_copias(tmp_path)
    cli = _cli(monkeypatch, case)
    monkeypatch.setattr(sm, "ocr_pdf_escalera", _sin_ocr)
    if mismo_nombre:
        b = case / "00_Input" / "01_Drive EV" / "OFERTAS" / "OFERTA 1" / "Certificado titularidad bancaria.pdf"
        b.rename(b.with_name("Certificado titularidad.pdf"))
    p = sm.plan(sm.inventariar(case), set())
    cli.apply("W-TEST99")
    md_dir = case / "01_Procesado" / "02_Sala de máquina" / "03_MD"
    antes = {x.name: x.read_bytes() for x in md_dir.glob("*.md")}
    cli.apply("W-TEST99", solo=[p[1].rel_path])
    despues = {x.name: x.read_bytes() for x in md_dir.glob("*.md")}
    assert despues == antes, "ni un MD nuevo ni uno reescrito"
    cob = cli._cobertura_previa(case)
    assert sorted(c.metodo for c in cob) == [sm.METODO_DUPLICADO, "pypdf"]
    assert all(c.estado == "ok" for c in cob)


def test_d13_la_titularidad_es_durable(tmp_path, monkeypatch):
    """R1/H-06: una carpeta nueva que ordena ANTES con los mismos bytes no le quita el espejo
    al titular de ayer (con `--force` incluido); y dos productoras legadas siguen siendo dos."""
    case = _caso_con_copias(tmp_path)
    cli = _cli(monkeypatch, case)
    monkeypatch.setattr(sm, "ocr_pdf_escalera", _sin_ocr)
    cli.apply("W-TEST99")
    antes = sm.plan(sm.inventariar(case), set())
    nuevo = case / "00_Input" / "00_antes" / "nuevo.pdf"
    nuevo.parent.mkdir(parents=True)
    nuevo.write_bytes((case / "00_Input" / antes[0].rel_path).read_bytes())
    cli.apply("W-TEST99", force=True)
    cob = cli._cobertura_previa(case)
    por_rel = {c.rel_path: c for c in cob}
    assert por_rel[antes[0].rel_path].metodo == "pypdf", "el titular de ayer sigue siéndolo"
    assert por_rel["00_antes/nuevo.pdf"].metodo == sm.METODO_DUPLICADO
    md_dir = case / "01_Procesado" / "02_Sala de máquina" / "03_MD"
    assert [x.name for x in md_dir.glob("*.md")] == [f"{antes[0].slug}.md"], "un solo espejo activo"
    # dos productoras legadas: ninguna se degrada a alias
    p = sm.plan(sm.inventariar(case), set(), productores_previos=frozenset({"A/x.pdf", "B/y.pdf"}))
    inv = [{"rel_path": "A/x.pdf", "sha256": "f" * 64, "ext": ".pdf"},
           {"rel_path": "B/y.pdf", "sha256": "f" * 64, "ext": ".pdf"},
           {"rel_path": "C/z.pdf", "sha256": "f" * 64, "ext": ".pdf"}]
    p = sm.plan(inv, set(), productores_previos=frozenset({"A/x.pdf", "B/y.pdf"}))
    assert [d.duplicado_de for d in p] == ["", "", "A/x.pdf"]


def test_d14_la_nota_apunta_a_rutas_que_existen(tmp_path, monkeypatch):
    """R1/H-07: `03_MD/<slug>.md` para el suelto (con extensión, y existe)."""
    case = _caso_con_copias(tmp_path)
    monkeypatch.setattr(sm, "ocr_pdf_escalera", _sin_ocr)
    cob = sm.ejecutar(case, sm.plan(sm.inventariar(case), set()), case_id="EV-2026-001")
    copia = next(c for c in cob if c.metodo == sm.METODO_DUPLICADO)
    ruta = copia.nota.split("espejo único en ")[1].split(" ")[0]
    assert ruta.endswith(".md")
    assert (case / "01_Procesado" / "02_Sala de máquina" / ruta).exists(), ruta
    assert copia.alias_de == next(c for c in cob if c.metodo == "pypdf").slug


def test_d15_mutantes_del_revisor():
    """M1: el peor estado entre VARIAS filas; M2: mismo slug también es alias."""
    filas = [sm.DocCobertura("b__aa", "A/b.pdf", "pypdf", "ok", 5, False, "", "a" * 64, parent_slug="b__aa"),
             sm.DocCobertura("b__aa__d02", "A/b.pdf", "pypdf", "low", 5, False, "", "a" * 64, parent_slug="b__aa")]
    assert sm._peor_estado(filas) == "low"
    d = sm.DocPlan("B/b.pdf", "a" * 64, ".pdf", "pdf", "b__aa", duplicado_de="A/b.pdf")
    fila = sm._fila_duplicado(d, filas)
    assert fila.estado == "low" and fila.alias_de == "b__aa" and "2 documentos lógicos" in fila.nota


def test_d15b_mismo_nombre_mismo_slug_tambien_es_alias(tmp_path, monkeypatch):
    case = _caso_con_copias(tmp_path)
    b = case / "00_Input" / "01_Drive EV" / "OFERTAS" / "OFERTA 1" / "Certificado titularidad bancaria.pdf"
    b.rename(b.with_name("Certificado titularidad.pdf"))
    monkeypatch.setattr(sm, "ocr_pdf_escalera", _sin_ocr)
    escritos = []
    original = sm._escribir_md

    def _contando(*a, **k):
        escritos.append(a[2])
        return original(*a, **k)
    monkeypatch.setattr(sm, "_escribir_md", _contando)
    llamadas = []
    cob = sm.ejecutar(case, sm.plan(sm.inventariar(case), set()), case_id="EV-2026-001",
                      on_documento=lambda d, ms, filas: llamadas.append((d.rel_path, ms, len(filas))))
    assert len(escritos) == 1, "el espejo compartido se escribe UNA vez"
    assert sorted(c.metodo for c in cob) == [sm.METODO_DUPLICADO, "pypdf"]
    assert len(llamadas) == 2 and any(ms == 0 and n == 1 for _r, ms, n in llamadas), "M3: el gancho ve la copia"


def test_d7_fusionar_conserva_las_dos_filas():
    tit = sm.DocCobertura("cert__aaaa1111", "01_Drive EV/ARRAS/cert.pdf", "pypdf", "ok", 500, False,
                          "también en 01_Drive EV/OFERTAS/cert.pdf (mismo sha256)", "a" * 64)
    cop = sm.DocCobertura("cert__aaaa1111", "01_Drive EV/OFERTAS/cert.pdf", sm.METODO_DUPLICADO, "ok", 0,
                          False, "copia byte-idéntica de 01_Drive EV/ARRAS/cert.pdf", "a" * 64)
    out = sm.fusionar_cobertura([], [tit, cop])
    assert len(out) == 2
    out2 = sm.fusionar_cobertura(out, [tit, cop])
    assert len(out2) == 2
