"""Una corrida con cero acciones sobre material que SI existe no puede felicitarse.

Punto que la R1 adversarial dejo abierto (su remedio «(d)»): hoy `organizar` ya no puede
cantar exito sobre una sala vacia, pero **por construccion** —siempre cataloga—, no porque
nadie lo compruebe. Esto es el cinturon.

Y la parte que importa: un catalogo vacio tiene TRES causas y solo una es un defecto.
Confundirlas seria repetir el error del punto 2 en otro sitio.

  1. el inventario vio ficheros y el catalogo salio vacio  -> DEFECTO, aborta
  2. hay ficheros pero ninguno con extension relevante     -> legitimo, se declara
  3. `00_Input` esta de verdad vacio                        -> legitimo, se declara
"""
from __future__ import annotations

import importlib

import pytest


def _reload():
    from core import case_manager, catalogo_documental, inventory, sala_lectura
    importlib.reload(case_manager)
    importlib.reload(inventory)
    importlib.reload(catalogo_documental)
    importlib.reload(sala_lectura)
    return case_manager, inventory, catalogo_documental, sala_lectura


def _caso(cm, docs):
    case_id = "EV-2026-TEST"
    case_dir = cm.ensure_case(case_id)
    for sub, name, content in docs:
        p = case_dir / "00_Input" / sub / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content)
    return case_id, case_dir


def test_catalogo_vacio_con_material_en_el_inventario_ABORTA(tmp_casos_root, monkeypatch):
    """Causa 1: inconsistencia interna. Es la unica que es un defecto."""
    cm, inv, cat, sl = _reload()
    case_id, _ = _caso(cm, [("01_Drive EV", "Factura honorarios.pdf", b"%PDF-1")])

    # El inventario si ve el fichero; el catalogo se queda vacio.
    monkeypatch.setattr(sl.catalogo_documental, "build_catalog", lambda *_a, **_k: None)

    with pytest.raises(RuntimeError) as exc:
        sl.organizar(case_id)

    assert "inventario" in str(exc.value).lower(), str(exc.value)


def test_un_00_input_de_verdad_vacio_NO_aborta(tmp_casos_root):
    """Causa 3, y el mutante hermano: el guard no puede volverse un falso rojo."""
    cm, inv, cat, sl = _reload()
    case_id, _ = _caso(cm, [])

    res = sl.organizar(case_id)

    assert res["sin_material"] is True
    assert res.get("motivo") == "input_vacio"


def test_ficheros_sin_extension_relevante_NO_abortan_pero_se_declaran(tmp_casos_root):
    """Causa 2: hay material y no es catalogable. No es un defecto, pero tampoco un exito."""
    cm, inv, cat, sl = _reload()
    case_id, _ = _caso(cm, [
        ("01_Drive EV/TOPOGRAFICO", "parcela.gml", b"<gml/>"),
        ("01_Drive EV/TOPOGRAFICO", "planta.dxf", b"dxf"),
    ])

    res = sl.organizar(case_id)

    assert res["sin_material"] is True
    assert res.get("motivo") == "sin_extension_relevante"
    assert res.get("n_omitidos") == 2, res


def test_el_caso_normal_sigue_sin_declarar_sin_material(tmp_casos_root):
    """Y con material catalogable, `sin_material` tiene que ser False.

    Sin esta asercion, un `sin_material=True` constante pasaria los tres de arriba.
    """
    cm, inv, cat, sl = _reload()
    case_id, _ = _caso(cm, [("01_Drive EV", "Factura honorarios.pdf", b"%PDF-1")])

    res = sl.organizar(case_id)

    assert res.get("sin_material") is False
    assert res["detenido_por_residuo"] is False
    assert res["acciones"], "con un documento catalogable la sala no puede quedar vacia"


def test_la_cli_no_dice_organizada_cuando_no_habia_material(tmp_casos_root):
    from typer.testing import CliRunner

    cm, inv, cat, sl = _reload()
    case_id, _ = _caso(cm, [])

    from scripts import sala_lectura as cli
    importlib.reload(cli)
    r = CliRunner().invoke(cli.app, ["organizar", "--case", case_id])

    assert "organizada" not in r.output.lower(), r.output
    assert "Acciones: {}" not in r.output, r.output
