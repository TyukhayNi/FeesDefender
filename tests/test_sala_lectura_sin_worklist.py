"""R2/H-04: «no hay residuo» y «la worklist no se ha generado» tambien son distintos.

El cuarto estado, y me lo habia dejado. `_filas_worklist` devuelve `[]` cuando el fichero no
existe, asi que los dos metodos de residuo salen vacios y la CLI afirmaba «todo el catalogo
esta clasificado» con documentos SIN clasificar dentro — un hecho falso, y con salida 0.

Es el mismo defecto que ese comando acaba de arreglar, un estado mas alla: remedie tres ramas y
la cuarta seguia mintiendo. Los tests que escribi no lo cazaban porque TODOS llamaban a
`clasificar_caso` antes, o sea que fabricaban la worklist sin darse cuenta de que era el
supuesto que faltaba.
"""
from __future__ import annotations

import importlib

import pytest
from typer.testing import CliRunner


def _mods():
    from core import case_manager, catalogo_documental, inventory, sala_lectura
    for m in (case_manager, inventory, catalogo_documental, sala_lectura):
        importlib.reload(m)
    return case_manager, inventory, catalogo_documental, sala_lectura


def _cli():
    from scripts import sala_lectura as cli
    importlib.reload(cli)
    return cli


def _caso_catalogado_sin_clasificar(cm, inv, cat):
    """Alta + documento ambiguo + inventario + catalogo, y NADA mas: sin `clasificar_caso`."""
    case_id = "EV-2026-TEST"
    case_dir = cm.ensure_case(case_id)
    p = case_dir / "00_Input" / "01_Drive EV" / "ambiguo.pdf"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"%PDF-1")
    inv.scan(case_id)
    cat.build_catalog(case_id)
    return case_id, case_dir


def test_sin_worklist_la_cli_no_afirma_que_todo_esta_clasificado(tmp_casos_root):
    cm, inv, cat, sl = _mods()
    case_id, case_dir = _caso_catalogado_sin_clasificar(cm, inv, cat)

    sin_tipo = [e for e in cat.load_catalog(case_id) if not e.tipo_documental]
    assert sin_tipo, "la fixture necesita un documento sin clasificar"
    assert not (sl._revisar_dir(case_id) / sl.WORKLIST_NAME).exists()

    r = CliRunner().invoke(_cli().app, ["preparar-residuo", "--case", case_id])

    assert "todo el catálogo está clasificado" not in r.output, r.output
    assert r.exit_code != 0, "afirmo un hecho falso y ademas salio con 0"
    assert "clasificar" in r.output, "no orienta al comando que falta"


def test_con_la_worklist_generada_y_sin_residuo_si_puede_decirlo(tmp_casos_root):
    """El hermano: el estado legitimo de «no hay residuo» tiene que seguir existiendo.

    Sin esta asercion, un aviso permanente pasaria el test de arriba y romperia la rama buena.
    """
    cm, inv, cat, sl = _mods()
    case_id = "EV-2026-TEST"
    case_dir = cm.ensure_case(case_id)
    p = case_dir / "00_Input" / "01_Drive EV" / "Factura honorarios.pdf"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"%PDF-1")
    inv.scan(case_id)
    cat.build_catalog(case_id)
    sl.clasificar_caso(case_id)          # el determinista lo resuelve: cero residuo

    r = CliRunner().invoke(_cli().app, ["preparar-residuo", "--case", case_id])

    assert r.exit_code == 0, r.output
    assert "Sin residuo" in r.output, r.output


def test_con_worklist_RANCIA_tampoco_afirma_que_todo_esta_clasificado(tmp_casos_root):
    """El quinto estado, que el revisor anoto por LECTURA y no ejecuto (R2, nota de H-04).

    Los dos metodos de residuo hacen `if e is None: continue` sobre el catalogo, asi que una
    fila de worklist cuyo hash ya no existe se descarta EN SILENCIO. Con la worklist presente
    pero rancia —el material de `00_Input` cambio despues— las dos listas salen vacias y
    `hay_worklist` es `True`: la primera remediacion de H-04 volvia a afirmar el hecho falso.

    Es la leccion del corolario de `CLAUDE.md`: remedie el EJEMPLO que el informe describia
    («la worklist no se ha generado») y no la PROPIEDAD de la que era ejemplo («la afirmacion
    se deriva del catalogo, no de que las listas salgan vacias»). Este test fija la propiedad.
    """
    cm, inv, cat, sl = _mods()
    case_id = "EV-2026-TEST"
    case_dir = cm.ensure_case(case_id)
    doc = case_dir / "00_Input" / "01_Drive EV" / "ambiguo.pdf"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_bytes(b"%PDF-VERSION-1")
    inv.scan(case_id)
    cat.build_catalog(case_id)
    sl.clasificar_caso(case_id)                      # worklist con el hash VIEJO

    worklist = sl._revisar_dir(case_id) / sl.WORKLIST_NAME
    assert worklist.exists(), "la fixture necesita una worklist generada"
    hashes_viejos = {f["Hash"] for f in sl._filas_worklist(case_id)}
    assert hashes_viejos, "la worklist tiene que traer al menos una fila de residuo"

    # El material cambia: mismo nombre, contenido distinto -> hash distinto.
    doc.write_bytes(b"%PDF-VERSION-2-DISTINTA")
    inv.scan(case_id)
    cat.build_catalog(case_id)

    hashes_nuevos = {e.hash for e in cat.load_catalog(case_id)}
    assert hashes_viejos.isdisjoint(hashes_nuevos), (
        "la fixture no ha conseguido dejar la worklist rancia")
    assert worklist.exists(), "la worklist sigue en disco: eso es lo que enganaba"
    assert sl.preparar_residuo(case_id) == []
    assert sl.residuo_sin_texto(case_id) == []
    assert [e for e in cat.load_catalog(case_id) if not e.tipo_documental], (
        "y sin embargo hay documentos sin clasificar")

    r = CliRunner().invoke(_cli().app, ["preparar-residuo", "--case", case_id])

    assert "todo el catálogo está clasificado" not in r.output, r.output
    assert r.exit_code != 0, "afirmo un hecho falso y ademas salio con 0"
    assert "rancios" in r.output, (
        "no distingue la causa: con la worklist presente el consejo no puede ser "
        "«corre clasificar» sin decir por que la anterior no sirve")
