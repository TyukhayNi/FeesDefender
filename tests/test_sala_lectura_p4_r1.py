"""Los cinco defectos de código que levantó la R1 adversarial sobre el diff de P4.

Acta: `docs/superpowers/specs/2026-09-14-p4-sala-lectura-sin-parada-r1-adversarial-review.md`.
Los siete hallazgos se adjudicaron **confirmados contra la fuente**; estos son los cinco que
exigen código (H-06 es del arnés, H-07 de la prosa).

**La frontera común a H-01, H-02 y H-03, que es lo que de verdad enseñó la ronda:** apliqué
`es_decision` a lo que se **escribe** y no a lo que se **lee**. Marcar el residuo `08` con
confianza 0.0 fija cómo NACE un pendiente, y no dice nada de los `08` que ya están en el
catálogo con confianza 1.0 —los pudo escribir el código base, o el propio camino LLM—, ni de
qué otros campos puede pisar un reintento. Tres caminos leían ese estado y los tres lo
malinterpretaban de forma distinta.
"""
from __future__ import annotations

import importlib

from core.config import UMBRAL_CONFIANZA_AUTOMOVE

PENDIENTE = "08. PENDIENTE DE CLASIFICAR"


def _reload():
    from core import case_manager, catalogo_documental, inventory, sala_lectura
    importlib.reload(case_manager)
    importlib.reload(inventory)
    importlib.reload(catalogo_documental)
    importlib.reload(sala_lectura)
    return case_manager, inventory, catalogo_documental, sala_lectura


def _caso(cm, inv, cat, docs, case_id="EV-2026-P4R1"):
    case_dir = cm.ensure_case(case_id)
    for sub, name, content in docs:
        p = case_dir / "00_Input" / sub / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    inv.scan(case_id)
    cat.build_catalog(case_id)
    return case_id, case_dir


def _worklist(case_dir, sl, filas: str):
    p = case_dir / "01_Procesado" / "_revisar" / sl.WORKLIST_NAME
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "| Hash | Origen | Fuente | Tipo | Fecha | Parte | Descripcion |\n"
        "|---|---|---|---|---|---|---|\n" + filas, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# H-01 (ALTO) — un `08` persistido con confianza alta queda congelado
# ---------------------------------------------------------------------------


def test_h01_un_08_con_confianza_alta_vuelve_a_ser_residuo(tmp_casos_root):
    """El estado que produjo el código BASE se normaliza solo, sin migración.

    Base aplicaba un `08` escrito en la worklist con confianza `1.0`. Con las guardas
    preguntando «tipo truthy + confianza ≥ umbral», ese documento: (a) `clasificar_caso` lo
    salta como «ya resuelto en una corrida previa», (b) `aplicar_clasificacion(solo_residuo)`
    lo respeta y no aplica la corrección, y (c) al no estar en el residuo **desaparece de la
    worklist** en la regeneración. Congelado, invisible y con `organizar` diciendo cero
    pendientes.

    La frontera: el centinela tiene que gobernar la **lectura** de lo persistido, no solo la
    escritura de lo nuevo.
    """
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso(cm, inv, cat, [("04_Manual", "ambiguo.pdf", "y")])
    entries = cat.load_catalog(case_id)
    # El estado heredado, tal cual lo dejaba base:
    entries[0].tipo_documental = PENDIENTE
    entries[0].confianza = 1.0
    cat.save_catalog(case_id, entries)
    h = entries[0].hash

    r = sl.clasificar_caso(case_id)
    assert r["n_residuo"] == 1, "un 08 heredado no se volvió a contar como residuo"

    worklist = case_dir / "01_Procesado" / "_revisar" / sl.WORKLIST_NAME
    assert h in worklist.read_text(encoding="utf-8"), (
        "el 08 heredado desapareció de la worklist: no hay forma de corregirlo")


def test_h01_la_correccion_de_un_08_heredado_se_aplica(tmp_casos_root):
    """Y con `solo_residuo=True`, que es lo que usa `organizar`."""
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso(cm, inv, cat, [("04_Manual", "ambiguo.pdf", "y")])
    entries = cat.load_catalog(case_id)
    entries[0].tipo_documental = PENDIENTE
    entries[0].confianza = 1.0
    cat.save_catalog(case_id, entries)
    h = entries[0].hash

    _worklist(case_dir, sl,
              f"| {h} | ambiguo.pdf | manual | 07. RECLAMACIONES | 2025-01-02 |  | burofax |\n")
    res = sl.aplicar_clasificacion(case_id, solo_residuo=True)

    assert res["n_aplicadas"] == 1, "la corrección de un 08 heredado no se aplicó"
    e = cat.load_catalog(case_id)[0]
    assert e.tipo_documental == "07. RECLAMACIONES"
    assert e.confianza >= UMBRAL_CONFIANZA_AUTOMOVE


# ---------------------------------------------------------------------------
# H-02 (ALTO) — el reintento pisa una fecha ya decidida
# ---------------------------------------------------------------------------


def test_h02_el_reintento_no_pisa_la_fecha_que_puso_el_letrado(tmp_casos_root):
    """Que el TIPO siga indeciso no autoriza a redecidir la FECHA.

    Regresión introducida al fechar el residuo (mutante M10): `clasificar_caso` escribía
    `fecha_doc`/`fecha_fuente` **incondicionalmente** en cada reintento. El letrado fechaba
    `2020-01-02` en la worklist, `aplicar` lo volcaba, y el `organizar` siguiente lo
    sustituía por la fecha del nombre del fichero — y materializaba la copia con ESA, de
    modo que el catálogo, el nombre y la cronología decían una fecha y la worklist otra.

    La frontera: la procedencia y la autoridad de cada campo se conservan por separado. La
    ausencia de decisión sobre el tipo no es ausencia de decisión sobre la fecha.
    """
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso(cm, inv, cat, [("04_Manual", "2025-03-20 sin pistas.pdf", "y")])
    sl.clasificar_caso(case_id)
    h = cat.load_catalog(case_id)[0].hash

    _worklist(case_dir, sl,
              f"| {h} | x | manual | {PENDIENTE} | 2020-01-02 |  | fecha revisada |\n")
    sl.aplicar_clasificacion(case_id)
    assert cat.load_catalog(case_id)[0].fecha_doc == "2020-01-02"

    sl.organizar(case_id)

    e = cat.load_catalog(case_id)[0]
    assert e.fecha_doc == "2020-01-02", (
        "organizar sustituyó la fecha del letrado por la inferida del nombre")
    nombres = [p.name for p in (case_dir / "01_Procesado" / "Sala lectura").rglob("*.pdf")]
    assert any(n.startswith("2020-01-02_") for n in nombres), nombres


def test_h02_un_pendiente_nuevo_si_recibe_su_fecha_inferida(tmp_casos_root):
    """El otro lado de la frontera: sin fecha decidida, se infiere (es lo que pide M10)."""
    cm, inv, cat, sl = _reload()
    case_id, _ = _caso(cm, inv, cat, [("04_Manual", "2025-03-20 sin pistas.pdf", "y")])
    sl.clasificar_caso(case_id)
    e = cat.load_catalog(case_id)[0]
    assert e.tipo_documental == PENDIENTE
    assert e.fecha_doc == "2025-03-20"


# ---------------------------------------------------------------------------
# H-03 (MEDIO) — la celda `08` bloquea una clasificación mejorada
# ---------------------------------------------------------------------------


def test_h03_rellenar_worklist_pisa_una_celda_que_dice_08(tmp_casos_root):
    """El selector ofrece el documento y el escritor rechazaba su respuesta.

    `_hashes_residuo` ya reconoce `08` como no decidido, pero `rellenar_worklist` trataba
    **cualquier** celda no vacía como intocable. Con un `08` escrito por el propio camino
    LLM, el documento se ofrecía en cada corrida y ninguna respuesta mejor podía entrar:
    `n_docs=1`, `n_celdas=0`, para siempre.

    La frontera: «celda presente» dejó de ser «decisión tomada» para el selector, y tenía
    que dejar de serlo también para el escritor. Lo que sí se sigue respetando es una
    categoría REAL escrita antes — eso lo fija el test de abajo.
    """
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso(cm, inv, cat, [("04_Manual", "ambiguo.pdf", "y")])
    sl.clasificar_caso(case_id)
    h = cat.load_catalog(case_id)[0].hash
    _worklist(case_dir, sl, f"| {h} | x | manual | {PENDIENTE} |  |  |  |\n")

    r = sl.rellenar_worklist(case_id, {h: {"Tipo": "07. RECLAMACIONES", "confianza": 1.0}})

    assert r["n_celdas"] >= 1, "la celda 08 bloqueó la clasificación mejorada"
    texto = (case_dir / "01_Procesado" / "_revisar" / sl.WORKLIST_NAME).read_text(
        encoding="utf-8")
    assert "07. RECLAMACIONES" in texto


def test_h03_una_categoria_real_ya_escrita_sigue_sin_pisarse(tmp_casos_root):
    """La otra mitad: lo que NO es `08` sigue siendo intocable (idempotencia)."""
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso(cm, inv, cat, [("04_Manual", "ambiguo.pdf", "y")])
    sl.clasificar_caso(case_id)
    h = cat.load_catalog(case_id)[0].hash
    _worklist(case_dir, sl, f"| {h} | x | manual | 01. ACTIVACIÓN |  |  |  |\n")

    r = sl.rellenar_worklist(case_id, {h: {"Tipo": "07. RECLAMACIONES", "confianza": 1.0}})

    assert r["n_celdas"] == 0
    texto = (case_dir / "01_Procesado" / "_revisar" / sl.WORKLIST_NAME).read_text(
        encoding="utf-8")
    assert "01. ACTIVACIÓN" in texto and "07. RECLAMACIONES" not in texto


# ---------------------------------------------------------------------------
# H-04 (MEDIO) — la parte explícita del nombre manda sobre la regla genérica
# ---------------------------------------------------------------------------


import pytest  # noqa: E402


@pytest.mark.parametrize("nombre, esperado", [
    # El canon es explícito: el `Anexo 2` DE LOS COMPRADORES no es la excepción de PBC.
    ("Anexo 2 compradores.pdf", "03. OFERTAS"),
    ("Anexo 1 comprador.pdf", "03. OFERTAS"),
    ("DNI comprador.pdf", "03. OFERTAS"),
    ("Pasaporte de los compradores.pdf", "03. OFERTAS"),
    # Y la parte vendedora, explícita, sigue en su lado.
    ("Anexo 2 vendedor.pdf", "06. PBC"),
    ("DNI vendedor.pdf", "01. ACTIVACIÓN"),
    # Sin parte en el nombre, el defecto es el vendedor (la mayoría): sin cambios.
    ("Anexo 2 titular real.pdf", "06. PBC"),
    ("DNI Mercedes Loyo.pdf", "01. ACTIVACIÓN"),
])
def test_h04_la_parte_escrita_en_el_nombre_gana(nombre, esperado):
    """Un valor por defecto para una parte DESCONOCIDA no puede prevalecer sobre una
    parte CONOCIDA.

    La tabla enruta al lado del vendedor porque es la mayoría, y eso es correcto mientras
    el nombre no diga nada. Cuando el nombre dice `comprador`, la regla genérica estaba
    ganándole a la señal — y en `Anexo 2 compradores.pdf` introducía un falso positivo
    **nuevo**, contra el ejemplo literal del runbook.

    Esto NO infiere la parte de un nombre opaco: solo respeta la que está escrita.
    """
    _, _, _, sl = _reload()
    assert sl._categoria_por_nombre(nombre) == esperado


def test_la_ficha_de_comprador_es_del_comprador():
    """Token propio, aserto propio: `ficha comprador` no puede apoyarse en `hoja de visita`.

    Los dos viven en la misma entrada de `03. OFERTAS` y un solo mutante que retirase ambos
    moría por cualquiera de ellos (R1/H-06)."""
    _, _, _, sl = _reload()
    assert sl._categoria_por_nombre("Ficha comprador firmada.pdf") == "03. OFERTAS"


def test_un_requerimiento_al_comprador_sigue_siendo_reclamacion():
    """La regla de parte se aplica SOLO a la familia de la identidad.

    Si valiera para toda la tabla, `requerimiento al comprador.pdf` dejaría de ser una
    reclamación por llevar la palabra «comprador» — la parte no cambia lo que un burofax
    ES. La frontera es que la parte decide el DESTINO de un documento de identidad, no la
    naturaleza de cualquier documento que la mencione."""
    _, _, _, sl = _reload()
    assert sl._categoria_por_nombre("requerimiento al comprador.pdf") == "07. RECLAMACIONES"
    assert sl._categoria_por_nombre("factura al comprador.pdf") == "05. FACTURACIÓN - FINANZAS"


# ---------------------------------------------------------------------------
# H-05 (MEDIO) — un sufijo léxico no es la continuación de un identificador
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("nombre, esperado", [
    ("Anexo 10.pdf", None),            # NO es el Anexo 1
    ("Anexo 20 titularidad.pdf", "01. ACTIVACIÓN"),   # NO es el Anexo 2; es titularidad
    ("Anexos 12.pdf", None),
    # Y los Anexos de verdad siguen casando, con y sin sufijo no numérico.
    ("Anexo 1.pdf", "06. PBC"),
    ("Anexo 2 titular real.pdf", "06. PBC"),
    ("Anexos 1 y 2.pdf", "06. PBC"),
])
def test_h05_los_anexos_10_y_20_no_son_los_anexos_1_y_2(nombre, esperado):
    """La política de sufijo abierto vale para el plural y la numeración de `oferta2` o
    `PBC1`, y NO para el identificador numérico de una excepción limitada a los Anexos 1
    y 2. La skill hermana ya lo distinguía con `[^0-9]`.

    La frontera: sufijo léxico y continuación de un identificador numérico no son la misma
    cosa, aunque la regex las trate igual.
    """
    _, _, _, sl = _reload()
    assert sl._categoria_por_nombre(nombre) == esperado


@pytest.mark.parametrize("nombre, esperado", [
    ("oferta2.pdf", "03. OFERTAS"),
    ("ofertas recibidas.pdf", "03. OFERTAS"),
    ("PBC1 JOSEP GIRBAU.pdf", "06. PBC"),
    ("facturas del mes.pdf", "05. FACTURACIÓN - FINANZAS"),
])
def test_h05_los_verdaderos_positivos_con_sufijo_se_conservan(nombre, esperado):
    """El remedio de H-05 no puede llevarse por delante lo que H-06 de la ronda anterior
    compró: `oferta2`, el plural y `PBC1` son verdaderos positivos medidos."""
    _, _, _, sl = _reload()
    assert sl._categoria_por_nombre(nombre) == esperado


# ---------------------------------------------------------------------------
# El superviviente declarado deja de estarlo: el aviso del CLI es el mecanismo
# que sustituye a la parada, no decoración.
# ---------------------------------------------------------------------------


def test_el_cli_organizar_dice_cuantos_pendientes_quedan_y_donde_corregirlos(tmp_casos_root):
    """Declarar este hueco «solo cambia TEXTO» no se sostenía, y la ronda tenía razón.

    Al retirar la parada, **este aviso es el único canal** por el que el letrado se entera
    de que queda trabajo: antes se lo decía el propio bloqueo. `n_pendientes` fija el dato
    en el core (M12) y no fijaba su comunicación. El test exige el conteo y la ruta de
    corrección, no la redacción.
    """
    from typer.testing import CliRunner
    cm, inv, cat, sl = _reload()
    case_id, _ = _caso(cm, inv, cat, [
        ("04_Manual", "Factura honorarios.pdf", "x"),
        ("04_Manual", "Documento sin pistas.pdf", "y"),
    ])
    import scripts.sala_lectura as cli
    importlib.reload(cli)
    # El aviso va a stderr; en esta versión de click/typer el runner ya los mezcla.
    res = CliRunner().invoke(cli.app, ["organizar", "--case", case_id])

    assert res.exit_code == 0, res.output
    assert "1" in res.output, res.output
    assert sl.WORKLIST_NAME in res.output, (
        f"el aviso no dice dónde corregir los pendientes:\n{res.output}")
