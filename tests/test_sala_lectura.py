"""Tests de la sala de lectura (F4–F6)."""
from __future__ import annotations

import importlib
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
    """Crea un caso con `docs` = [(subcarpeta, nombre, contenido_bytes_o_str)] y
    devuelve (case_id, case_dir) con inventario y catálogo ya construidos."""
    case_id = "EV-2026-TEST"
    case_dir = case_manager.ensure_case(case_id)
    for sub, name, content in docs:
        p = case_dir / "00_Input" / sub / name
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            p.write_bytes(content)
        else:
            p.write_text(content, encoding="utf-8")
    inventory.scan(case_id)
    catalogo.build_catalog(case_id)
    return case_id, case_dir


# --- Task 1: Extender CatalogEntry y hacer load_catalog tolerante ---


def test_catalog_entry_campos_nuevos_por_defecto(tmp_casos_root):
    from core import case_manager as cm, inventory as inv, catalogo_documental as cat
    importlib.reload(cm); importlib.reload(inv); importlib.reload(cat)
    case_id, _ = _caso_con_docs(cm, inv, cat, [("01_Drive EV", "x.txt", "hola")])
    e = cat.load_catalog(case_id)[0]
    assert e.descripcion is None
    assert e.fecha_fuente is None
    assert e.confianza is None
    assert e.nombre_canonico is None
    assert e.ruta_sala_lectura is None


def test_load_catalog_tolera_claves_desconocidas(tmp_casos_root):
    from core import case_manager as cm, inventory as inv, catalogo_documental as cat
    importlib.reload(cm); importlib.reload(inv); importlib.reload(cat)
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [("01_Drive EV", "x.txt", "hola")])
    import yaml
    path = case_dir / "01_Procesado" / "indice_documental.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data[0]["campo_de_otra_version"] = "ignorar"
    path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    entries = cat.load_catalog(case_id)  # no debe lanzar
    assert len(entries) == 1


# --- Task 2: save_catalog ---


def test_save_catalog_roundtrip(tmp_casos_root):
    from core import case_manager as cm, inventory as inv, catalogo_documental as cat
    importlib.reload(cm); importlib.reload(inv); importlib.reload(cat)
    case_id, _ = _caso_con_docs(cm, inv, cat, [("01_Drive EV", "x.txt", "hola")])
    entries = cat.load_catalog(case_id)
    entries[0].tipo_documental = "05. FACTURACIÓN - FINANZAS"
    entries[0].confianza = 0.9
    cat.save_catalog(case_id, entries)
    reloaded = cat.load_catalog(case_id)
    assert reloaded[0].tipo_documental == "05. FACTURACIÓN - FINANZAS"
    assert reloaded[0].confianza == 0.9


# --- Task 3: reglas deterministas — categoría por keyword e imagen ---


@pytest.mark.parametrize("nombre, esperado", [
    ("Factura honorarios 2025.pdf", "05. FACTURACIÓN - FINANZAS"),
    ("Burofax requerimiento de pago.pdf", "07. RECLAMACIONES"),
    ("Hoja de encargo en exclusiva.pdf", "01. ACTIVACIÓN"),
    ("Oferta del comprador.pdf", "03. OFERTAS"),
    ("Contrato de arras penitenciales.pdf", "04. ARRAS - ARRENDAMIENTOS"),
    ("Nota simple registral.pdf", "06. PBC"),
    ("Documento sin pistas.pdf", None),
])
def test_clasificar_por_keyword(nombre, esperado):
    from core import sala_lectura
    importlib.reload(sala_lectura)
    assert sala_lectura._categoria_por_nombre(nombre) == esperado


def test_categoria_imagen():
    from core import sala_lectura
    importlib.reload(sala_lectura)
    assert sala_lectura._es_imagen(".jpg") is True
    assert sala_lectura._es_imagen(".pdf") is False


def test_clasificar_tolera_guiones_bajos():
    from core import sala_lectura
    importlib.reload(sala_lectura)
    assert sala_lectura._categoria_por_nombre("justificante_de_pago_2025.pdf") == "05. FACTURACIÓN - FINANZAS"


# --- Task 4: fecha determinista — patrón en nombre ---


def test_fecha_desde_nombre_iso():
    from core import sala_lectura
    importlib.reload(sala_lectura)
    assert sala_lectura._fecha_desde_nombre("2025-07-12 oferta.pdf") == ("2025-07-12", "contenido")
    assert sala_lectura._fecha_desde_nombre("oferta 12-07-2025.pdf") == ("2025-07-12", "contenido")
    assert sala_lectura._fecha_desde_nombre("sin fecha.pdf") == (None, None)


# --- Task 5: clasificar_caso ---


def test_clasificar_caso_deterministas_y_residuo(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("01_Drive EV", "Factura honorarios.pdf", b"%PDF-1"),
        ("01_Drive EV", "Documento ambiguo.pdf", b"%PDF-2"),
        ("01_Drive EV", "foto fachada.jpg", b"\xff\xd8\xff\xe0jpg"),
    ])
    resumen = sl.clasificar_caso(case_id)

    entries = {e.nombre_original: e for e in cat.load_catalog(case_id)}
    assert entries["Factura honorarios.pdf"].tipo_documental == "05. FACTURACIÓN - FINANZAS"
    assert entries["foto fachada.jpg"].tipo_documental == "00. FOTOS"
    assert entries["Documento ambiguo.pdf"].tipo_documental is None

    worklist = case_dir / "01_Procesado" / "_revisar" / "_clasificar.md"
    assert worklist.exists()
    contenido = worklist.read_text(encoding="utf-8")
    assert "Documento ambiguo.pdf" in contenido
    assert "Factura honorarios.pdf" not in contenido
    assert resumen["n_residuo"] == 1
    assert resumen["n_deterministas"] == 2


# --- Task 6: aplicar_clasificacion ---


def test_aplicar_clasificacion_vuelca_worklist(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("01_Drive EV", "Documento ambiguo.pdf", b"%PDF-2"),
    ])
    sl.clasificar_caso(case_id)
    h = cat.load_catalog(case_id)[0].hash

    worklist = case_dir / "01_Procesado" / "_revisar" / "_clasificar.md"
    filas = [
        "# Worklist", "",
        "| Hash | Origen | Fuente | Tipo | Fecha | Parte | Descripcion |",
        "|---|---|---|---|---|---|---|",
        f"| {h} | Documento ambiguo.pdf | drive_ev | 01. ACTIVACIÓN | 2025-03-01 | propietario | Acuerdo marco |",
        "",
    ]
    worklist.write_text("\n".join(filas), encoding="utf-8")

    res = sl.aplicar_clasificacion(case_id)
    e = cat.load_catalog(case_id)[0]
    assert e.tipo_documental == "01. ACTIVACIÓN"
    assert e.fecha_doc == "2025-03-01"
    assert e.parte == "propietario"
    assert e.descripcion == "Acuerdo marco"
    assert e.confianza == 1.0
    assert res["n_aplicadas"] == 1


def test_aplicar_ignora_filas_sin_tipo_o_tipo_invalido(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("01_Drive EV", "ambiguo.pdf", b"%PDF-2"),
    ])
    sl.clasificar_caso(case_id)
    h = cat.load_catalog(case_id)[0].hash
    worklist = case_dir / "01_Procesado" / "_revisar" / "_clasificar.md"
    filas = [
        "| Hash | Origen | Fuente | Tipo | Fecha | Parte | Descripcion |",
        "|---|---|---|---|---|---|---|",
        f"| {h} | ambiguo.pdf | drive_ev | TIPO INVENTADO | 2025-03-01 |  |  |",
    ]
    worklist.write_text("\n".join(filas), encoding="utf-8")
    res = sl.aplicar_clasificacion(case_id)
    assert cat.load_catalog(case_id)[0].tipo_documental is None
    assert res["n_aplicadas"] == 0


# --- Task 7: render_indices ---


def test_render_indices(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("01_Drive EV", "Factura.pdf", b"%PDF-1"),
        ("05_CRM/01_Demanda", "Burofax.pdf", b"%PDF-2"),
    ])
    sl.clasificar_caso(case_id)  # ambas casan por keyword
    paths = sl.render_indices(case_id)

    indice = case_dir / "01_Procesado" / "Sala lectura" / "INDICE.md"
    crono = case_dir / "01_Procesado" / "Sala lectura" / "CRONOLOGIA.md"
    assert indice in paths and crono in paths
    txt_i = indice.read_text(encoding="utf-8")
    assert "no editar a mano" in txt_i.lower()
    assert "drive_ev" in txt_i.lower() or "drive e&v" in txt_i.lower()
    assert "Factura.pdf" in txt_i
    txt_c = crono.read_text(encoding="utf-8")
    assert "Burofax.pdf" in txt_c


# --- Task 8: _nombre_canonico ---


def test_nombre_canonico():
    from core import sala_lectura as sl
    importlib.reload(sl)
    from core.catalogo_documental import CatalogEntry
    e = CatalogEntry(
        id_doc="abc", ruta_relativa="01_Drive EV/x.pdf", nombre_original="x.pdf",
        tipo_documental="01. ACTIVACIÓN", fecha_doc="2025-07-12",
        descripcion="Hoja de captación firmada", hash="abc123",
    )
    nombre = sl._nombre_canonico(e)
    assert nombre.startswith("2025-07-12_activacion_")
    assert nombre.endswith(".pdf")

    e2 = CatalogEntry(id_doc="d", ruta_relativa="a/y.pdf", nombre_original="y.pdf", hash="d")
    # Sin tipo/fecha/desc -> fallback: fecha 0000-00-00, tipo 'doc', desc del stem original.
    n2 = sl._nombre_canonico(e2)
    assert n2.startswith("0000-00-00_doc_")
    assert n2.endswith(".pdf")


# --- Task 9: poblar_sala_lectura ---


def test_poblar_sala_lectura_copia_idempotente(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("01_Drive EV", "Factura honorarios.pdf", b"%PDF-FACTURA"),
    ])
    sl.clasificar_caso(case_id)
    r1 = sl.poblar_sala_lectura(case_id)

    sala = case_dir / "01_Procesado" / "Sala lectura" / "Drive E&V"
    copias = list(sala.glob("*.pdf"))
    assert len(copias) == 1
    assert copias[0].read_bytes() == b"%PDF-FACTURA"
    assert (case_dir / "00_Input" / "01_Drive EV" / "Factura honorarios.pdf").exists()
    assert cat.load_catalog(case_id)[0].ruta_sala_lectura is not None

    r2 = sl.poblar_sala_lectura(case_id)
    assert len(list(sala.glob("*.pdf"))) == 1
    assert r2["acciones"].get("SKIP_UNCHANGED", 0) >= 1


def test_poblar_dedup_por_hash(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("01_Drive EV", "Factura.pdf", b"%PDF-IGUAL"),
        ("05_CRM/01_Demanda", "Factura copia.pdf", b"%PDF-IGUAL"),
    ])
    sl.clasificar_caso(case_id)
    sl.poblar_sala_lectura(case_id)
    todas = list((case_dir / "01_Procesado" / "Sala lectura").rglob("*.pdf"))
    assert len(todas) == 1


# --- Task 10: bundles CRM con degradación ---


def test_poblar_con_bundles_crm(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    from core.sync_sudespacho import GdocuDocInfo
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("05_CRM/01_Demanda", "ORDINARIO VUELTA VENDEDOR.pdf", b"%PDF-CAB"),
        ("05_CRM/01_Demanda", "D 01 - encargo.pdf", b"%PDF-D1"),
        ("05_CRM/01_Demanda", "D 02 - oferta.pdf", b"%PDF-D2"),
    ])
    sl.clasificar_caso(case_id)
    ts = "2025-01-01T10:00:00+01:00"
    crm_docs = [
        GdocuDocInfo("1", "ORDINARIO VUELTA VENDEDOR.pdf", "307", "Demanda",
                     "application/pdf", 1, {}, ts),
        GdocuDocInfo("2", "D 01 - encargo.pdf", "307", "Demanda",
                     "application/pdf", 1, {}, ts),
        GdocuDocInfo("3", "D 02 - oferta.pdf", "307", "Demanda",
                     "application/pdf", 1, {}, ts),
    ]
    sl.poblar_sala_lectura(case_id, crm_docs=crm_docs)

    crm_dir = case_dir / "01_Procesado" / "Sala lectura" / "CRM"
    bundles = [p for p in crm_dir.iterdir() if p.is_dir()]
    assert len(bundles) == 1
    adjuntos = bundles[0] / "adjuntos"
    assert adjuntos.is_dir()
    assert len(list(adjuntos.glob("*.pdf"))) == 2
    entries = {e.nombre_original: e for e in cat.load_catalog(case_id)}
    assert entries["D 01 - encargo.pdf"].parent_id is not None


def test_poblar_sin_crm_docs_degrada_a_plano(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("05_CRM/01_Demanda", "D 01 - encargo.pdf", b"%PDF-D1"),
    ])
    sl.clasificar_caso(case_id)
    sl.poblar_sala_lectura(case_id)  # sin crm_docs
    crm_dir = case_dir / "01_Procesado" / "Sala lectura" / "CRM"
    assert any(crm_dir.glob("*.pdf"))  # copia plana, sin subcarpeta de bundle


def test_cli_organizar_se_detiene_con_residuo(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("01_Drive EV", "ambiguo.pdf", b"%PDF-2"),
    ])
    res = sl.organizar(case_id)
    assert res["detenido_por_residuo"] is True
    assert res["n_residuo"] == 1
    assert not (case_dir / "01_Procesado" / "Sala lectura" / "Drive E&V").exists()


def test_organizar_completo_sin_residuo(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("01_Drive EV", "Factura honorarios.pdf", b"%PDF-1"),
    ])
    res = sl.organizar(case_id)
    assert res["detenido_por_residuo"] is False
    assert (case_dir / "01_Procesado" / "Sala lectura" / "INDICE.md").exists()
    assert any((case_dir / "01_Procesado" / "Sala lectura" / "Drive E&V").glob("*.pdf"))


def test_poblar_bundles_idempotente(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    from core.sync_sudespacho import GdocuDocInfo
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("05_CRM/01_Demanda", "ORDINARIO VUELTA VENDEDOR.pdf", b"%PDF-CAB"),
        ("05_CRM/01_Demanda", "D 01 - encargo.pdf", b"%PDF-D1"),
        ("05_CRM/01_Demanda", "D 02 - oferta.pdf", b"%PDF-D2"),
    ])
    sl.clasificar_caso(case_id)
    ts = "2025-01-01T10:00:00+01:00"
    crm_docs = [
        GdocuDocInfo("1", "ORDINARIO VUELTA VENDEDOR.pdf", "307", "Demanda", "application/pdf", 1, {}, ts),
        GdocuDocInfo("2", "D 01 - encargo.pdf", "307", "Demanda", "application/pdf", 1, {}, ts),
        GdocuDocInfo("3", "D 02 - oferta.pdf", "307", "Demanda", "application/pdf", 1, {}, ts),
    ]
    sl.poblar_sala_lectura(case_id, crm_docs=crm_docs)
    assert all(e.nombre_canonico for e in cat.load_catalog(case_id))
    snap1 = {e.nombre_original: (e.parent_id, e.orden_en_bundle, e.ruta_sala_lectura)
             for e in cat.load_catalog(case_id)}
    r2 = sl.poblar_sala_lectura(case_id, crm_docs=crm_docs)
    snap2 = {e.nombre_original: (e.parent_id, e.orden_en_bundle, e.ruta_sala_lectura)
             for e in cat.load_catalog(case_id)}
    assert snap1 == snap2  # parent_id/orden/ruta estables entre corridas
    # 2ª corrida no recopia
    assert r2["acciones"].get("COPY", 0) == 0


# --- MEJORAS #37: clasificar_residuo_llm (autorrelleno LLM del residuo) ---


def _crear_md_del_residuo(case_id, cat, sl, texto="Texto extraído del documento."):
    """Crea 01_Procesado/MD/<slug>.md para cada entrada del residuo (sin tipo)."""
    creados = {}
    for e in cat.load_catalog(case_id):
        if e.tipo_documental:
            continue
        md = sl._md_path(case_id, e)
        md.parent.mkdir(parents=True, exist_ok=True)
        md.write_text(texto, encoding="utf-8")
        creados[e.hash] = md
    return creados


def _worklist_path(case_dir, sl):
    return case_dir / "01_Procesado" / "_revisar" / sl.WORKLIST_NAME


def test_clasificar_residuo_llm_rellena_residuo(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("01_Drive EV", "Documento ambiguo.pdf", b"%PDF-2"),
    ])
    sl.clasificar_caso(case_id)
    _crear_md_del_residuo(case_id, cat, sl)
    h = cat.load_catalog(case_id)[0].hash

    llamadas = []

    def fake_chat_fn(doc):
        llamadas.append(doc)
        return {"tipo": "01. ACTIVACIÓN", "fecha": "2025-03-01",
                "parte": "propietario", "descripcion": "Acuerdo marco",
                "confianza": 0.95}

    res = sl.clasificar_residuo_llm(case_id, chat_fn=fake_chat_fn)
    assert res["n_docs"] == 1
    assert res["n_celdas"] >= 1
    # el chat_fn recibió el material esperado (incl. texto del MD)
    assert llamadas[0]["hash"] == h
    assert "Texto extraído" in llamadas[0]["md_text"]

    # la worklist tiene Tipo/Parte/Descripcion rellenos; aplicar lo vuelca al catálogo
    res_ap = sl.aplicar_clasificacion(case_id)
    assert res_ap["n_aplicadas"] == 1
    e = cat.load_catalog(case_id)[0]
    assert e.tipo_documental == "01. ACTIVACIÓN"
    assert e.parte == "propietario"
    assert e.descripcion == "Acuerdo marco"


def test_clasificar_residuo_llm_baja_confianza_no_rellena(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("01_Drive EV", "Documento ambiguo.pdf", b"%PDF-2"),
    ])
    sl.clasificar_caso(case_id)
    _crear_md_del_residuo(case_id, cat, sl)

    def fake_chat_fn(doc):
        return {"tipo": "01. ACTIVACIÓN", "confianza": 0.3}  # por debajo del umbral

    res = sl.clasificar_residuo_llm(case_id, chat_fn=fake_chat_fn)
    assert res["n_baja_confianza"] == 1
    assert res["n_celdas"] == 0
    # sigue en residuo: aplicar no clasifica nada
    assert sl.aplicar_clasificacion(case_id)["n_aplicadas"] == 0
    assert cat.load_catalog(case_id)[0].tipo_documental is None


def test_clasificar_residuo_llm_idempotente(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("01_Drive EV", "Documento ambiguo.pdf", b"%PDF-2"),
    ])
    sl.clasificar_caso(case_id)
    _crear_md_del_residuo(case_id, cat, sl)

    contador = {"n": 0}

    def fake_chat_fn(doc):
        contador["n"] += 1
        return {"tipo": "06. PBC", "confianza": 0.9}

    sl.clasificar_residuo_llm(case_id, chat_fn=fake_chat_fn)
    contenido1 = _worklist_path(case_dir, sl).read_text(encoding="utf-8")
    llamadas_tras_1 = contador["n"]

    # 2ª corrida: la fila ya tiene Tipo → deja de ser residuo → chat_fn no se llama
    res2 = sl.clasificar_residuo_llm(case_id, chat_fn=fake_chat_fn)
    contenido2 = _worklist_path(case_dir, sl).read_text(encoding="utf-8")
    assert res2["n_docs"] == 0
    assert contador["n"] == llamadas_tras_1  # no se vuelve a llamar
    assert contenido1 == contenido2  # worklist estable


def test_rellenar_worklist_no_pisa_celdas_rellenas(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("01_Drive EV", "ambiguo.pdf", b"%PDF-2"),
    ])
    sl.clasificar_caso(case_id)
    h = cat.load_catalog(case_id)[0].hash
    # worklist con Parte ya puesta por un humano, Tipo aún vacío
    filas = [
        "| Hash | Origen | Fuente | Tipo | Fecha | Parte | Descripcion |",
        "|---|---|---|---|---|---|---|",
        f"| {h} | ambiguo.pdf | drive_ev |  | 2025-01-01 | buscador |  |",
    ]
    _worklist_path(case_dir, sl).write_text("\n".join(filas), encoding="utf-8")

    res = sl.rellenar_worklist(case_id, {h: {
        "Tipo": "06. PBC", "Parte": "propietario",
        "Descripcion": "Nota simple", "confianza": 0.9}})
    contenido = _worklist_path(case_dir, sl).read_text(encoding="utf-8")
    assert "06. PBC" in contenido          # Tipo vacío → se rellena
    assert "| buscador |" in contenido     # Parte humana → NO se pisa
    assert "propietario" not in contenido
    assert "Nota simple" in contenido      # Descripcion vacía → se rellena
    assert res["n_celdas"] == 2


def test_rellenar_worklist_tipo_y_parte_invalidos_no_se_escriben(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("01_Drive EV", "ambiguo.pdf", b"%PDF-2"),
    ])
    sl.clasificar_caso(case_id)
    h = cat.load_catalog(case_id)[0].hash
    filas = [
        "| Hash | Origen | Fuente | Tipo | Fecha | Parte | Descripcion |",
        "|---|---|---|---|---|---|---|",
        f"| {h} | ambiguo.pdf | drive_ev |  |  |  |  |",
    ]
    _worklist_path(case_dir, sl).write_text("\n".join(filas), encoding="utf-8")

    sl.rellenar_worklist(case_id, {h: {
        "Tipo": "TIPO INVENTADO", "Parte": "vendedor",
        "Descripcion": "ok", "confianza": 0.99}})
    contenido = _worklist_path(case_dir, sl).read_text(encoding="utf-8")
    assert "TIPO INVENTADO" not in contenido
    assert "vendedor" not in contenido
    assert "ok" in contenido  # la descripción válida sí se escribe


def test_clasificar_residuo_llm_omite_doc_sin_md(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("01_Drive EV", "Documento ambiguo.pdf", b"%PDF-2"),
    ])
    sl.clasificar_caso(case_id)
    # NO se crea el MD → no hay texto que leer

    def fake_chat_fn(doc):  # no debería llamarse
        raise AssertionError("no debe clasificar sin texto")

    res = sl.clasificar_residuo_llm(case_id, chat_fn=fake_chat_fn)
    assert res["n_docs"] == 0
    assert res["n_sin_texto"] == 1


def test_clasificar_residuo_llm_requiere_chat_fn(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    case_id, _ = _caso_con_docs(cm, inv, cat, [
        ("01_Drive EV", "ambiguo.pdf", b"%PDF-2"),
    ])
    sl.clasificar_caso(case_id)
    with pytest.raises(ValueError):
        sl.clasificar_residuo_llm(case_id)  # sin chat_fn → no hay default de pago


def test_make_llm_cloud_chat_fn_construye_mensajes(monkeypatch, tmp_casos_root):
    cm, inv, cat, sl = _reload()
    capturado = {}

    def fake_chat_json(messages, *, config=None, json_schema=None, **kw):
        capturado["messages"] = messages
        capturado["schema"] = json_schema
        return {"tipo": "05. FACTURACIÓN - FINANZAS", "fecha": "2025-02-02",
                "parte": "tercero", "descripcion": "Factura", "confianza": 0.9}

    monkeypatch.setattr("core.llm_cloud.chat_json", fake_chat_json)
    chat_fn = sl.make_llm_cloud_chat_fn()
    out = chat_fn({"hash": "abc", "nombre_original": "f.pdf", "fuente": "manual",
                   "fecha_pista": "", "md_text": "honorarios de la operación"})
    assert out["tipo"] == "05. FACTURACIÓN - FINANZAS"
    assert capturado["messages"][0]["role"] == "system"
    assert "honorarios" in capturado["messages"][1]["content"]
    assert capturado["schema"] is not None


# --- Fix de cableado: build_catalog (prerrequisito de la sala de lectura) ---


def test_clasificar_caso_sin_catalogo_es_trampa_y_build_catalog_la_resuelve(tmp_casos_root):
    """Antes del fix: nadie poblaba el catálogo, así que clasificar_caso sobre un
    catálogo vacío escribía una worklist vacía silenciosamente. build_catalog es
    el eslabón que faltaba."""
    cm, inv, cat, sl = _reload()
    case_id = "EV-2026-TEST"
    case_dir = cm.ensure_case(case_id)
    for name in ("Factura honorarios.pdf", "Documento ambiguo.pdf"):
        p = case_dir / "00_Input" / "01_Drive EV" / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"%PDF-x")
    inv.scan(case_id)

    # Sin build_catalog: catálogo vacío → clasificar no ve nada (la trampa)
    assert cat.load_catalog(case_id) == []
    trampa = sl.clasificar_caso(case_id)
    assert trampa["n_total"] == 0 and trampa["n_residuo"] == 0

    # Con build_catalog: el catálogo se puebla y clasificar ya produce residuo
    cat.build_catalog(case_id)
    assert len(cat.load_catalog(case_id)) == 2
    res = sl.clasificar_caso(case_id)
    assert res["n_total"] == 2
    assert res["n_deterministas"] == 1   # "Factura honorarios" → FACTURACIÓN
    assert res["n_residuo"] == 1         # "Documento ambiguo" → residuo


def _setup_case_cli(case_id="EV-2026-TEST", docs=("Factura honorarios.pdf", "Documento ambiguo.pdf")):
    """Crea un caso con docs en 00_Input SIN construir el catálogo (para los
    tests de CLI; no usa _reload para no alterar los bindings del app typer)."""
    from core import case_manager
    case_dir = case_manager.ensure_case(case_id)
    for name in docs:
        p = case_dir / "00_Input" / "01_Drive EV" / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"%PDF-x")
    return case_id, case_dir


def test_cli_catalogo_construye_indice(tmp_casos_root):
    from typer.testing import CliRunner
    from scripts.sala_lectura import app
    from core import catalogo_documental as cat

    case_id, _ = _setup_case_cli()
    result = CliRunner().invoke(app, ["catalogo", "--case", case_id])
    assert result.exit_code == 0
    assert "entradas" in result.output
    assert len(cat.load_catalog(case_id)) == 2


def test_cli_clasificar_autoconstruye_catalogo_vacio(tmp_casos_root):
    """La guarda del CLI: clasificar con catálogo vacío lo construye antes en vez
    de escribir [] y una worklist vacía."""
    from typer.testing import CliRunner
    from scripts.sala_lectura import app
    from core import catalogo_documental as cat

    case_id, _ = _setup_case_cli()
    assert cat.load_catalog(case_id) == []
    result = CliRunner().invoke(app, ["clasificar", "--case", case_id])
    assert result.exit_code == 0
    assert "Catálogo vacío" in result.output
    assert len(cat.load_catalog(case_id)) == 2
    assert "Residuo: 1" in result.output
