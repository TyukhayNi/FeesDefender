"""Una corrida con cero acciones sobre material que SI existe no puede felicitarse.

Punto que la R1 adversarial dejo abierto (su remedio «(d)»): hoy `organizar` ya no puede
cantar exito sobre una sala vacia, pero **por construccion** —siempre cataloga—, no porque
nadie lo compruebe. Esto es el cinturon.

Y la parte que importa: un catalogo vacio tiene DOS causas y solo una es un defecto.
Confundirlas seria repetir el error del punto 2 en otro sitio.

  1. el inventario vio ficheros y el catalogo salio vacio  -> DEFECTO, aborta
  2. `00_Input` esta de verdad vacio                        -> legitimo, se declara

Hasta el 2026-09-26 habia una tercera, «hay ficheros pero ninguno con extension
relevante», y era `MEJORAS #316`: la lista blanca de extensiones del inventario dejaba
fuera de la sala audios, zips, vCards, planos y documentos sin extension.
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


def test_los_planos_y_lo_que_no_se_sabe_leer_ENTRAN_en_la_sala(tmp_casos_root):
    """**Este test decía lo contrario hasta el 2026-09-26, y el cambio se declara aquí.**

    Se llamaba `…sin_extension_relevante_NO_abortan_pero_se_declaran` y exigía que un caso con
    solo planos (`.gml`, `.dxf`) se declarase «sin material catalogable». Era la lista blanca
    de extensiones del inventario, y es `MEJORAS #316`: W-02JSVZ tiene 54 `.gml` topográficos
    de E&V que nunca llegaron a la sala, y W-02Y2J6 siete notas de voz. Ahora son documentos:
    entran con `08. PENDIENTE DE CLASIFICAR` y el aviso de pendientes los cuenta.
    """
    cm, inv, cat, sl = _reload()
    case_id, _ = _caso(cm, [
        ("01_Drive EV/TOPOGRAFICO", "parcela.gml", b"<gml/>"),
        ("01_Drive EV/TOPOGRAFICO", "planta.dxf", b"dxf"),
    ])

    res = sl.organizar(case_id)

    assert res["sin_material"] is False, res
    assert res["n_pendientes"] == 2, res
    assert res["acciones"], "los dos planos tienen que estar en la sala"


def test_el_caso_normal_sigue_sin_declarar_sin_material(tmp_casos_root):
    """Y con material catalogable, `sin_material` tiene que ser False.

    Sin esta asercion, un `sin_material=True` constante pasaria los tres de arriba.
    """
    cm, inv, cat, sl = _reload()
    case_id, _ = _caso(cm, [("01_Drive EV", "Factura honorarios.pdf", b"%PDF-1")])

    res = sl.organizar(case_id)

    assert res.get("sin_material") is False
    assert res["n_pendientes"] == 0
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
