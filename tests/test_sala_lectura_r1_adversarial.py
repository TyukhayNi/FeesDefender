"""Los 8 hallazgos MIOS de la R1 adversarial de Codex (2026-09-04) sobre la sala de lectura.

Cada test es el escenario que el revisor reprodujo, y los ocho estaban rojos antes de
remediarlos. Viven aparte de `test_sala_lectura.py` para que se vea de donde salieron: son
la voz del revisor convertida en guard, no casos que se me ocurrieran a mi.

Informe literal y adjudicacion: acta hermana de la R1 en `docs/superpowers/`.
"""
from __future__ import annotations

import importlib
import re
from pathlib import Path

import pytest


def _reload():
    from core import case_manager, catalogo_documental, inventory, sala_lectura
    importlib.reload(case_manager)
    importlib.reload(inventory)
    importlib.reload(catalogo_documental)
    importlib.reload(sala_lectura)
    return case_manager, inventory, catalogo_documental, sala_lectura


def _caso_con_docs(case_manager, inventory, catalogo, docs):
    case_id = "EV-2026-TEST"
    case_dir = case_manager.ensure_case(case_id)
    for sub, name, content in docs:
        p = case_dir / "00_Input" / sub / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content)
    inventory.scan(case_id)
    catalogo.build_catalog(case_id)
    return case_id, case_dir


def _md_dir(case_dir: Path) -> Path:
    d = case_dir / "01_Procesado" / "02_Sala de maquina" / "03_MD"
    return d


def _sm_md_dir(case_dir: Path) -> Path:
    # El nombre real lleva tilde; se construye desde el core para no duplicar el literal.
    from core import sala_lectura as sl
    return case_dir.joinpath(*sl._MD_SUBDIR)


def _worklist_path(case_dir: Path, sl) -> Path:
    return case_dir / "01_Procesado" / "_revisar" / sl.WORKLIST_NAME


def _filas(path: Path) -> list[list[str]]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        celdas = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(celdas) != 7 or celdas[0] == "Hash" or set(celdas[0]) <= {"-"}:
            continue
        out.append(celdas)
    return out


def _escribir_fila(path: Path, hash_: str, celdas_nuevas: dict[int, str]) -> None:
    lineas = path.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lineas):
        celdas = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(celdas) != 7 or celdas[0] != hash_:
            continue
        for idx, val in celdas_nuevas.items():
            celdas[idx] = val
        lineas[i] = "| " + " | ".join(celdas) + " |"
        path.write_text("\n".join(lineas) + "\n", encoding="utf-8")
        return
    raise AssertionError(f"no habia fila para {hash_}")


def _residuo(cat, case_id, nombre):
    return [x for x in cat.load_catalog(case_id)
            if not x.tipo_documental and x.nombre_original == nombre][0]


# ---------------------------------------------------------------------------
# ALTO — organizar no incorporaba documentos nuevos si ya habia catalogo
# ---------------------------------------------------------------------------

def test_organizar_incorpora_documentos_nuevos_con_catalogo_ya_poblado(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("01_Drive EV", "Factura honorarios.pdf", b"%PDF-1"),
    ])
    sl.organizar(case_id)

    (case_dir / "00_Input" / "01_Drive EV" / "Requerimiento de pago.pdf").write_bytes(b"%PDF-2")
    sl.organizar(case_id)

    nombres = {e.nombre_original for e in cat.load_catalog(case_id)}
    assert "Requerimiento de pago.pdf" in nombres, "la prueba nueva no entro al catalogo"


# ---------------------------------------------------------------------------
# ALTO — una fila obsoleta pisaba una clasificacion ya resuelta
# ---------------------------------------------------------------------------

def test_una_fila_obsoleta_no_pisa_una_clasificacion_ya_resuelta(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("01_Drive EV", "ambiguo.pdf", b"%PDF-1"),
    ])
    sl.clasificar_caso(case_id)
    h = _filas(_worklist_path(case_dir, sl))[0][0]
    _escribir_fila(_worklist_path(case_dir, sl), h,
                   {3: "07. RECLAMACIONES", 5: "propietario", 6: "Fila vieja"})

    entries = cat.load_catalog(case_id)
    for e in entries:
        if e.hash == h:
            e.tipo_documental, e.confianza = "06. PBC", 1.0
    cat.save_catalog(case_id, entries)

    sl.organizar(case_id)

    vigente = {e.hash: e for e in cat.load_catalog(case_id)}[h]
    assert vigente.tipo_documental == "06. PBC", "la fila obsoleta piso la decision vigente"


# ---------------------------------------------------------------------------
# MEDIO — un MD canonico obsoleto tapaba los segmentos actuales
# ---------------------------------------------------------------------------

def test_un_md_canonico_obsoleto_no_tapa_los_segmentos_actuales(tmp_casos_root):
    from core.utils import output_slug

    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("01_Drive EV", "ambiguo.pdf", b"%PDF-1"),
    ])
    sl.clasificar_caso(case_id)
    e = _residuo(cat, case_id, "ambiguo.pdf")
    d = _sm_md_dir(case_dir)
    d.mkdir(parents=True, exist_ok=True)
    slug = output_slug(e.ruta_relativa, e.hash)
    (d / f"{slug}.md").write_text("OBSOLETO passthrough", encoding="utf-8")
    (d / f"{slug}__d01_DOC_A.md").write_text("ACTUAL-A", encoding="utf-8")
    (d / f"{slug}__d02_DOC_B.md").write_text("ACTUAL-B", encoding="utf-8")

    docs = sl.preparar_residuo(case_id)

    assert len(docs) == 1
    assert "ACTUAL-A" in docs[0]["md_text"]
    assert "ACTUAL-B" in docs[0]["md_text"]
    assert "OBSOLETO" not in docs[0]["md_text"], "prefirio el canonico obsoleto"


# ---------------------------------------------------------------------------
# MEDIO — el enlace del indice apuntaba a un MD inexistente
# ---------------------------------------------------------------------------

def test_el_indice_no_publica_enlaces_muertos(tmp_casos_root):
    from core.utils import output_slug

    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("01_Drive EV", "Factura honorarios.pdf", b"%PDF-1"),
    ])
    e = cat.load_catalog(case_id)[0]
    d = _sm_md_dir(case_dir)
    d.mkdir(parents=True, exist_ok=True)
    # Bundle partido: NO existe el canonico, solo el segmento.
    (d / f"{output_slug(e.ruta_relativa, e.hash)}__d01_DOC_A.md").write_text(
        "segmento", encoding="utf-8")

    sl.render_indices(case_id)

    indice = case_dir / "01_Procesado" / "Sala lectura" / "INDICE.md"
    hrefs = re.findall(r"\[ver texto\]\(([^)]+)\)", indice.read_text(encoding="utf-8"))
    assert hrefs, "el indice no publico ningun enlace de texto"
    for href in hrefs:
        assert (indice.parent / href).resolve().is_file(), f"enlace muerto: {href}"


def test_sin_ningun_md_el_indice_no_inventa_un_enlace(tmp_casos_root):
    """El mutante hermano: si no hay texto, la respuesta es NO enlazar, no enlazar a la nada."""
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("01_Drive EV", "Factura honorarios.pdf", b"%PDF-1"),
    ])
    sl.render_indices(case_id)

    indice = case_dir / "01_Procesado" / "Sala lectura" / "INDICE.md"
    assert "[ver texto]" not in indice.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# MEDIO — un Tipo invalido volvia el documento invisible
# ---------------------------------------------------------------------------

def test_un_tipo_invalido_sigue_siendo_preparable(tmp_casos_root):
    from core.utils import output_slug

    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("01_Drive EV", "ambiguo.pdf", b"%PDF-1"),
    ])
    sl.clasificar_caso(case_id)
    e = _residuo(cat, case_id, "ambiguo.pdf")
    d = _sm_md_dir(case_dir)
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{output_slug(e.ruta_relativa, e.hash)}.md").write_text("texto", encoding="utf-8")
    _escribir_fila(_worklist_path(case_dir, sl), e.hash, {3: "TIPO INVENTADO"})

    docs = sl.preparar_residuo(case_id)

    assert len(docs) == 1, "un Tipo invalido lo volvio invisible para el siguiente ciclo"


# ---------------------------------------------------------------------------
# MEDIO — una Fecha vaciada a proposito se reponia (familia del H-09)
# ---------------------------------------------------------------------------

def test_una_fecha_vaciada_a_proposito_se_conserva(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("01_Drive EV", "ambiguo.pdf", b"%PDF-1"),
    ])
    sl.clasificar_caso(case_id)
    wl = _worklist_path(case_dir, sl)
    fila = _filas(wl)[0]
    assert fila[4], "la fixture necesita una fecha inferida que borrar"
    _escribir_fila(wl, fila[0], {4: ""})

    sl.clasificar_caso(case_id)

    assert _filas(wl)[0][4] == "", "repuso la fecha que se habia borrado a proposito"


# ---------------------------------------------------------------------------
# BAJO — el glob no exigia la gramatica ni ordenaba por numero
# ---------------------------------------------------------------------------

def test_el_glob_de_segmentos_exige_gramatica_y_ordena_por_numero(tmp_casos_root):
    from core.utils import output_slug

    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("01_Drive EV", "ambiguo.pdf", b"%PDF-1"),
    ])
    sl.clasificar_caso(case_id)
    e = _residuo(cat, case_id, "ambiguo.pdf")
    d = _sm_md_dir(case_dir)
    d.mkdir(parents=True, exist_ok=True)
    slug = output_slug(e.ruta_relativa, e.hash)
    (d / f"{slug}__d99_DOC.md").write_text("noventa y nueve", encoding="utf-8")
    (d / f"{slug}__d100_DOC.md").write_text("cien", encoding="utf-8")
    (d / f"{slug}__draft_notes.md").write_text("NO ES UN SEGMENTO", encoding="utf-8")

    nombres = [p.name for p in sl._md_paths(case_id, e)]

    assert nombres == [f"{slug}__d99_DOC.md", f"{slug}__d100_DOC.md"], nombres


# ---------------------------------------------------------------------------
# ALTO — la CLI imprimia solo el primer segmento
# ---------------------------------------------------------------------------

def test_la_cli_preparar_residuo_lista_todos_los_segmentos(tmp_casos_root):
    from typer.testing import CliRunner

    from core.utils import output_slug

    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("01_Drive EV", "ambiguo.pdf", b"%PDF-1"),
    ])
    sl.clasificar_caso(case_id)
    e = _residuo(cat, case_id, "ambiguo.pdf")
    d = _sm_md_dir(case_dir)
    d.mkdir(parents=True, exist_ok=True)
    slug = output_slug(e.ruta_relativa, e.hash)
    (d / f"{slug}__d01_DOC_A.md").write_text("A", encoding="utf-8")
    (d / f"{slug}__d02_DOC_B.md").write_text("B", encoding="utf-8")

    from scripts import sala_lectura as cli
    importlib.reload(cli)
    r = CliRunner().invoke(cli.app, ["preparar-residuo", "--case", case_id])

    assert r.exit_code == 0, r.output
    assert f"{slug}__d01_DOC_A.md" in r.output
    assert f"{slug}__d02_DOC_B.md" in r.output, "la CLI oculto el segundo segmento"
