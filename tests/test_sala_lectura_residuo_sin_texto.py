"""«No hay residuo» y «hay residuo y no pude leerlo» son hechos DISTINTOS.

Aprendizaje del 2026-09-04, medido en carne propia abriendo W-02JSVZ:
`preparar-residuo` respondia «Sin residuo con texto extraido. Nada que preparar» con
**99 documentos en residuo y 176 espejos MD en disco**. La frase era literalmente cierta
—no habia residuo *con texto*— y me mando a investigar el sitio equivocado durante un buen
rato. La causa raiz (la ruta MD) se arreglo en `MEJORAS #151`, pero **el mensaje seguiria
siendo indistinguible** el dia que la sala de maquina no se haya corrido todavia.

Es la familia de [[feedback-no-lo-se-no-es-no-hay]]: toda funcion que responda «no hay»
tiene que poder responder «no pude mirar». Aqui hay tres estados y antes habia uno.
"""
from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from typer.testing import CliRunner


def _reload():
    from core import case_manager, catalogo_documental, inventory, sala_lectura
    importlib.reload(case_manager)
    importlib.reload(inventory)
    importlib.reload(catalogo_documental)
    importlib.reload(sala_lectura)
    return case_manager, inventory, catalogo_documental, sala_lectura


def _caso(cm, inv, cat, docs):
    case_id = "EV-2026-TEST"
    case_dir = cm.ensure_case(case_id)
    for sub, name, content in docs:
        p = case_dir / "00_Input" / sub / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content)
    inv.scan(case_id)
    cat.build_catalog(case_id)
    return case_id, case_dir


def _md_dir(case_dir: Path) -> Path:
    from core import sala_lectura as sl
    return case_dir.joinpath(*sl._MD_SUBDIR)


def _escribir_md(case_dir, sl, cat, case_id, nombre):
    from core.utils import output_slug
    e = [x for x in cat.load_catalog(case_id)
         if not x.tipo_documental and x.nombre_original == nombre][0]
    d = _md_dir(case_dir)
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{output_slug(e.ruta_relativa, e.hash)}.md").write_text("texto", encoding="utf-8")
    return e


# ---------------------------------------------------------------------------
# El core sabe distinguir los tres estados
# ---------------------------------------------------------------------------

def test_sin_residuo_es_distinto_de_residuo_sin_texto(tmp_casos_root):
    """El core tiene que poder decir CUAL de los dos hechos es."""
    cm, inv, cat, sl = _reload()

    # (a) Sin residuo: el clasificador determinista resolvio el unico documento.
    case_id, case_dir = _caso(cm, inv, cat, [
        ("01_Drive EV", "Factura honorarios.pdf", b"%PDF-1"),
    ])
    sl.clasificar_caso(case_id)
    assert sl.preparar_residuo(case_id) == []
    assert sl.residuo_sin_texto(case_id) == [], "no hay residuo: nada puede faltar de texto"


def test_residuo_sin_texto_se_declara_en_vez_de_callarse(tmp_casos_root):
    """El caso que me costo la tarde: hay residuo y NO hay espejos."""
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso(cm, inv, cat, [
        ("01_Drive EV", "ambiguo.pdf", b"%PDF-1"),
    ])
    sl.clasificar_caso(case_id)

    assert sl.preparar_residuo(case_id) == []
    sin_texto = sl.residuo_sin_texto(case_id)
    assert len(sin_texto) == 1, "el residuo sin texto quedo invisible"


def test_el_residuo_parcialmente_legible_declara_lo_que_se_salta(tmp_casos_root):
    """El defecto en miniatura: se clasifican 1 y el otro se salta EN SILENCIO.

    Es lo que paso con 88 de 99 en W-02JSVZ: la lista salio y nadie supo que 11
    faltaban.
    """
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso(cm, inv, cat, [
        ("01_Drive EV", "ambiguo uno.pdf", b"%PDF-1"),
        ("01_Drive EV", "ambiguo dos.pdf", b"%PDF-2"),
    ])
    sl.clasificar_caso(case_id)
    _escribir_md(case_dir, sl, cat, case_id, "ambiguo uno.pdf")

    docs = sl.preparar_residuo(case_id)
    sin_texto = sl.residuo_sin_texto(case_id)

    assert len(docs) == 1
    assert len(sin_texto) == 1, "el documento saltado no se declara en ningun sitio"


# ---------------------------------------------------------------------------
# Y la CLI lo dice con palabras distintas
# ---------------------------------------------------------------------------

def _cli():
    from scripts import sala_lectura as cli
    importlib.reload(cli)
    return cli


def test_la_cli_no_usa_la_misma_frase_para_los_dos_hechos(tmp_casos_root):
    """El mutante central: si las dos salidas son iguales, el arreglo no sirve."""
    cm, inv, cat, sl = _reload()

    # (a) sin residuo
    case_id, _ = _caso(cm, inv, cat, [
        ("01_Drive EV", "Factura honorarios.pdf", b"%PDF-1"),
    ])
    sl.clasificar_caso(case_id)
    salida_sin_residuo = CliRunner().invoke(
        _cli().app, ["preparar-residuo", "--case", case_id]).output

    # (b) con residuo y sin espejos — otro caso, para no arrastrar estado
    from core.casos import case_locator
    otro = "EV-2026-OTRO"
    case_dir2 = cm.ensure_case(otro)
    p = case_dir2 / "00_Input" / "01_Drive EV" / "ambiguo.pdf"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"%PDF-9")
    inv.scan(otro)
    cat.build_catalog(otro)
    sl.clasificar_caso(otro)
    salida_con_residuo = CliRunner().invoke(
        _cli().app, ["preparar-residuo", "--case", otro]).output

    assert salida_sin_residuo != salida_con_residuo, (
        "la CLI da la MISMA respuesta a «no hay» y a «no pude mirar»")
    assert "1" in salida_con_residuo, "no dice cuantos hay en residuo"
    assert "sala de m" in salida_con_residuo.lower(), (
        "no orienta hacia la causa (la sala de maquina no corrida)")


def test_los_codigos_de_salida_distinguen_los_dos_hechos(tmp_casos_root):
    """Y no solo el texto: «no pude mirar» es un ESTADO ENCADENABLE, no un aviso.

    Fija la decision a proposito: quien haga `preparar-residuo && aplicar` con residuo
    ilegible tiene que PARAR. «Nada que preparar» con salida 0 es la version enganosa.
    """
    cm, inv, cat, sl = _reload()

    sin_residuo, _ = _caso(cm, inv, cat, [
        ("01_Drive EV", "Factura honorarios.pdf", b"%PDF-1"),
    ])
    sl.clasificar_caso(sin_residuo)
    r_ok = CliRunner().invoke(_cli().app, ["preparar-residuo", "--case", sin_residuo])

    otro = "EV-2026-OTRO"
    d = cm.ensure_case(otro) / "00_Input" / "01_Drive EV" / "ambiguo.pdf"
    d.parent.mkdir(parents=True, exist_ok=True)
    d.write_bytes(b"%PDF-9")
    inv.scan(otro)
    cat.build_catalog(otro)
    sl.clasificar_caso(otro)
    r_ciego = CliRunner().invoke(_cli().app, ["preparar-residuo", "--case", otro])

    assert r_ok.exit_code == 0, r_ok.output
    assert r_ciego.exit_code != 0, (
        "residuo ilegible sale con 0: encadenar `&& aplicar` seguiria adelante")


def test_la_cli_avisa_de_los_que_se_salta_aunque_liste_alguno(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso(cm, inv, cat, [
        ("01_Drive EV", "ambiguo uno.pdf", b"%PDF-1"),
        ("01_Drive EV", "ambiguo dos.pdf", b"%PDF-2"),
    ])
    sl.clasificar_caso(case_id)
    _escribir_md(case_dir, sl, cat, case_id, "ambiguo uno.pdf")

    r = CliRunner().invoke(_cli().app, ["preparar-residuo", "--case", case_id])

    assert r.exit_code == 0, r.output
    assert "sin texto" in r.output.lower() or "sin espejo" in r.output.lower(), (
        "listo 1 y se salto 1 sin decirlo: " + r.output)
