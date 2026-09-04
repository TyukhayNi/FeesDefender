"""Los espejos MD se resuelven de verdad: un caso MIXTO, no tres rodajas.

Punto 4 de los aprendizajes en codigo. La divergencia que costo 140 enlaces muertos nacio
de que dos funciones construian la ruta del directorio de espejos por separado. El arreglo
declaro la ruta una vez (`_MD_SUBDIR`), y me plantee ademas un guard por *grep* que
impidiera volver a escribirla a mano.

**Decision (Codex, 2026-09-05, consultado por encargo expreso de Nikolai): guard de
COMPORTAMIENTO, no de texto.** Un grep se dispara con los comentarios que explican el
defecto viejo —hay varios, y uno cita el literal— y se queda rancio si el directorio cambia
de nombre. Su motivo, literal: «El defecto fue de comportamiento y tuvo impacto real;
merece una regresion, pero no un grep fragil.»

Y senalo lo que a mis tests de ayer les faltaba, que es el motivo de que este exista:
cubrian el bundle partido y el caso SIN espejo, pero **no el espejo canonico**, y
«el caso sin espejo no cubre los 176 falsos negativos» — el defecto real era justo el
contrario: los espejos existian y la funcion decia que no habia. Asi que la propiedad se
fija sobre un caso con los TRES estados a la vez.
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


@pytest.fixture
def caso_mixto(tmp_casos_root):
    """Un caso con los tres estados de espejo a la vez.

    - `ambiguo canonico.pdf` -> solo `<slug>.md`
    - `ambiguo partido.pdf`  -> solo `<slug>__d01_*.md` y `__d02_*.md`
    - `ambiguo ciego.pdf`    -> ningun espejo
    """
    from core.utils import output_slug

    cm, inv, cat, sl = _reload()
    case_id = "EV-2026-TEST"
    case_dir = cm.ensure_case(case_id)
    for nombre, contenido in (("ambiguo canonico.pdf", b"%PDF-1"),
                              ("ambiguo partido.pdf", b"%PDF-2"),
                              ("ambiguo ciego.pdf", b"%PDF-3")):
        p = case_dir / "00_Input" / "01_Drive EV" / nombre
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(contenido)
    inv.scan(case_id)
    cat.build_catalog(case_id)
    sl.clasificar_caso(case_id)

    por_nombre = {e.nombre_original: e for e in cat.load_catalog(case_id)}
    # **La ruta va LITERAL, no por `sl._MD_SUBDIR`.** Primera version de este fixture usaba
    # la constante del modulo bajo prueba, y el mutante SOBREVIVIO: al apuntar la constante
    # al motor jubilado, el fixture la seguia y los cuatro tests pasaban igual. Un arnes
    # anclado a lo que examina no puede detectar que lo examinado se mueva — es el mismo
    # defecto que ayer anote de `_crear_md_del_residuo` y que repeti aqui.
    #
    # Este literal es el contrato con la SALA DE MAQUINA (`core/sala_maquina.py`
    # `_sala_maquina_dir` + `03_MD`), no con la sala de lectura. Si algun dia cambia, este
    # test debe fallar y obligar a cambiarlo a mano: eso es lo que se quiere.
    d = case_dir / "01_Procesado" / "02_Sala de máquina" / "03_MD"
    d.mkdir(parents=True, exist_ok=True)

    canon = por_nombre["ambiguo canonico.pdf"]
    (d / f"{output_slug(canon.ruta_relativa, canon.hash)}.md").write_text(
        "TEXTO-CANONICO", encoding="utf-8")

    part = por_nombre["ambiguo partido.pdf"]
    slug_p = output_slug(part.ruta_relativa, part.hash)
    (d / f"{slug_p}__d01_DOC_A.md").write_text("TEXTO-SEG-A", encoding="utf-8")
    (d / f"{slug_p}__d02_DOC_B.md").write_text("TEXTO-SEG-B", encoding="utf-8")

    return {"case_id": case_id, "case_dir": case_dir, "sl": sl, "cat": cat,
            "por_nombre": por_nombre}


def test_md_paths_resuelve_los_tres_estados(caso_mixto):
    """La funcion de CONSULTA reconoce el canonico, los segmentos, y la ausencia."""
    sl, case_id, por = caso_mixto["sl"], caso_mixto["case_id"], caso_mixto["por_nombre"]

    canon = sl._md_paths(case_id, por["ambiguo canonico.pdf"])
    part = sl._md_paths(case_id, por["ambiguo partido.pdf"])
    ciego = sl._md_paths(case_id, por["ambiguo ciego.pdf"])

    assert [p.read_text(encoding="utf-8") for p in canon] == ["TEXTO-CANONICO"], (
        "el espejo CANONICO no se reconoce: es el falso negativo que costo la tarde")
    assert [p.read_text(encoding="utf-8") for p in part] == ["TEXTO-SEG-A", "TEXTO-SEG-B"]
    assert ciego == []


def test_todo_href_ver_texto_del_indice_resuelve_en_disco(caso_mixto):
    """Genericamente: TODO enlace publicado existe. No uno; todos los que salgan."""
    sl, case_id, case_dir = caso_mixto["sl"], caso_mixto["case_id"], caso_mixto["case_dir"]
    sl.render_indices(case_id)

    indice = case_dir / "01_Procesado" / "Sala lectura" / "INDICE.md"
    hrefs = re.findall(r"\[ver texto\]\(([^)]+)\)", indice.read_text(encoding="utf-8"))

    assert len(hrefs) == 2, (
        f"esperados 2 enlaces (canonico + partido), publicados {len(hrefs)}: {hrefs}")
    for href in hrefs:
        destino = (indice.parent / href).resolve()
        assert destino.is_file(), f"enlace muerto: {href}"


def test_el_ciego_no_recibe_enlace_y_los_otros_dos_si(caso_mixto):
    """El hermano: «todos los enlaces resuelven» tambien lo cumple no publicar ninguno."""
    sl, case_id, case_dir = caso_mixto["sl"], caso_mixto["case_id"], caso_mixto["case_dir"]
    sl.render_indices(case_id)

    texto = (case_dir / "01_Procesado" / "Sala lectura" / "INDICE.md").read_text(
        encoding="utf-8")
    por_linea = {}
    for linea in texto.splitlines():
        for nombre in ("ambiguo canonico.pdf", "ambiguo partido.pdf", "ambiguo ciego.pdf"):
            if f"[{nombre}]" in linea:
                por_linea[nombre] = "[ver texto]" in linea

    assert por_linea == {
        "ambiguo canonico.pdf": True,
        "ambiguo partido.pdf": True,
        "ambiguo ciego.pdf": False,
    }, por_linea


def test_la_consulta_y_el_indice_coinciden_sobre_los_mismos_documentos(caso_mixto):
    """Y la costura: lo que el indice enlaza es lo que la consulta puede leer.

    Es la propiedad que se rompio de verdad — no «la ruta es esta», sino que las dos
    funciones que la usan coincidan. Divergieron y nadie lo vio.
    """
    sl, case_id = caso_mixto["sl"], caso_mixto["case_id"]

    con_texto = {d["nombre_original"] for d in sl.preparar_residuo(case_id)}
    sin_texto = {d["nombre_original"] for d in sl.residuo_sin_texto(case_id)}

    assert con_texto == {"ambiguo canonico.pdf", "ambiguo partido.pdf"}
    assert sin_texto == {"ambiguo ciego.pdf"}
    assert con_texto.isdisjoint(sin_texto), "un documento no puede estar en los dos"
