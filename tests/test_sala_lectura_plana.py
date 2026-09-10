"""La sala de lectura es PLANA, y una colisión de nombre no pisa un documento.

Dos defectos que el backlog tenía escritos y sin cerrar, medidos los dos en vivo
en W-02YZO4 (2026-09-10):

* **`MEJORAS #67.c`** — `poblar_sala_lectura` escribía `Sala lectura/<fuente>/`,
  cuando la estructura canónica de la skill `organizar-sala-lectura` v1.3 es
  **plana**: la categoría vive en `INDICE.md`, no en carpetas. El workaround era
  aplanar a mano, y se deshacía en el siguiente `organizar`.
* **`MEJORAS #67.b` / `#36`** — dos documentos DISTINTOS que derivan el mismo
  `nombre_canonico` colisionaban y el segundo `shutil.copy2` **sobrescribía** al
  primero sin dejar rastro. El dedup por hash no protege: solo cubre bytes
  idénticos. Su disparador declarado era «la primera colisión observada en un caso
  real»: en W-02YZO4 fueron **cinco** correos del mismo día con la misma
  descripción colapsando en un fichero, y **tres** documentos que el Drive y el
  correo traen con bytes distintos (la copia del Drive pesa unos cientos de bytes
  más) y que por tanto el dedup no une.

Los dos defectos se cruzan, y por eso van en el mismo fichero: en el layout por
fuente la colisión entre `Drive E&V/` y `Email/` estaba **tapada** por las
carpetas. Aplanar sin guarda de unicidad convierte tres documentos en uno.
"""
from __future__ import annotations

import importlib

import yaml


def _reload():
    from core import case_manager, catalogo_documental, inventory, sala_lectura
    importlib.reload(case_manager)
    importlib.reload(inventory)
    importlib.reload(catalogo_documental)
    importlib.reload(sala_lectura)
    return case_manager, inventory, catalogo_documental, sala_lectura


def _caso_con_docs(case_manager, inventory, catalogo, docs, case_id="EV-2026-PLANA"):
    case_dir = case_manager.ensure_case(case_id)
    for sub, name, content in docs:
        p = case_dir / "00_Input" / sub / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
    inventory.scan(case_id)
    catalogo.build_catalog(case_id)
    return case_id, case_dir


def _fijar(catalogo, case_id, por_nombre):
    """Fija tipo/fecha/descripción por nombre original, como haría la worklist."""
    entries = catalogo.load_catalog(case_id)
    for e in entries:
        if e.nombre_original in por_nombre:
            tipo, fecha, desc = por_nombre[e.nombre_original]
            e.tipo_documental = tipo
            e.fecha_doc = fecha
            e.descripcion = desc
            e.confianza = 1.0
    catalogo.save_catalog(case_id, entries)


def _sala(case_dir):
    return case_dir / "01_Procesado" / "Sala lectura"


def _ficheros(case_dir):
    """Documentos de la sala (sin los índices generados)."""
    return sorted(
        p for p in _sala(case_dir).rglob("*")
        if p.is_file() and p.name not in ("INDICE.md", "CRONOLOGIA.md")
    )


# --- MEJORAS #67.c: estructura plana ------------------------------------------


def test_poblar_escribe_plano_sin_carpeta_por_fuente(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("01_Drive EV", "encargo.pdf", b"%PDF-ENCARGO"),
        ("03_Email", "hilo.pdf", b"%PDF-HILO"),
    ])
    _fijar(cat, case_id, {
        "encargo.pdf": ("01. ACTIVACIÓN", "2025-02-26", "encargo_en_exclusiva"),
        "hilo.pdf": ("07. RECLAMACIONES", "2025-12-16", "correo_del_consultor"),
    })
    sl.poblar_sala_lectura(case_id)

    # Los dos documentos, en la RAÍZ de la sala.
    assert (_sala(case_dir) / "2025-02-26_activacion_encargo_en_exclusiva.pdf").is_file()
    assert (_sala(case_dir) / "2025-12-16_reclamacion_correo_del_consultor.pdf").is_file()
    # Y ninguna carpeta por fuente.
    subdirs = [p.name for p in _sala(case_dir).iterdir() if p.is_dir()]
    assert subdirs == [], subdirs


def test_bundle_abre_subcarpeta_pero_no_carpeta_por_fuente(tmp_casos_root):
    """Un compuesto sigue abriendo subcarpeta: es la excepción que fija la skill."""
    cm, inv, cat, sl = _reload()
    from core.sync_sudespacho import GdocuDocInfo
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("05_CRM/01_Demanda", "ORDINARIO VUELTA VENDEDOR.pdf", b"%PDF-CAB"),
        ("05_CRM/01_Demanda", "D 01 - encargo.pdf", b"%PDF-D1"),
    ])
    sl.clasificar_caso(case_id)
    ts = "2025-01-01T10:00:00+01:00"
    crm_docs = [
        GdocuDocInfo("1", "ORDINARIO VUELTA VENDEDOR.pdf", "307", "Demanda",
                     "application/pdf", 1, {}, ts),
        GdocuDocInfo("2", "D 01 - encargo.pdf", "307", "Demanda",
                     "application/pdf", 1, {}, ts),
    ]
    sl.poblar_sala_lectura(case_id, crm_docs=crm_docs)

    assert not (_sala(case_dir) / "CRM").exists()
    bundles = [p for p in _sala(case_dir).iterdir() if p.is_dir()]
    assert len(bundles) == 1
    assert (bundles[0] / "adjuntos").is_dir()


def test_poblar_migra_el_layout_viejo_por_fuente(tmp_casos_root):
    """Un caso poblado con el layout anterior se aplana solo en la corrida siguiente."""
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("01_Drive EV", "encargo.pdf", b"%PDF-ENCARGO"),
    ])
    _fijar(cat, case_id, {
        "encargo.pdf": ("01. ACTIVACIÓN", "2025-02-26", "encargo_en_exclusiva"),
    })
    # Simula la corrida vieja: fichero bajo `Drive E&V/` y `ruta_sala_lectura` apuntándolo.
    nombre = "2025-02-26_activacion_encargo_en_exclusiva.pdf"
    viejo_rel = f"Sala lectura/Drive E&V/{nombre}"
    viejo = case_dir / "01_Procesado" / viejo_rel
    viejo.parent.mkdir(parents=True, exist_ok=True)
    viejo.write_bytes(b"%PDF-ENCARGO")
    entries = cat.load_catalog(case_id)
    entries[0].ruta_sala_lectura = viejo_rel
    entries[0].nombre_canonico = nombre
    cat.save_catalog(case_id, entries)

    res = sl.poblar_sala_lectura(case_id)

    assert res["acciones"].get("MOVED", 0) == 1
    assert (_sala(case_dir) / nombre).is_file()
    assert not viejo.exists()
    # La carpeta de fuente no se queda como cascarón vacío.
    assert not (_sala(case_dir) / "Drive E&V").exists()


# --- MEJORAS #67.b / #36: guarda de colisión ----------------------------------


def test_colision_de_nombre_canonico_conserva_LOS_DOS_documentos(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        # Mismo documento por dos rutas, con bytes distintos: el dedup por hash NO
        # los une, y el nombre canónico sale idéntico. Es el caso de W-02YZO4.
        ("01_Drive EV", "NOTA SIMPLE.pdf", b"%PDF-NOTA-DRIVE"),
        ("03_Email", "nota simple.pdf", b"%PDF-NOTA-CORREO-distinto"),
    ])
    _fijar(cat, case_id, {
        "NOTA SIMPLE.pdf": ("01. ACTIVACIÓN", "2025-02-27", "nota_simple_registral"),
        "nota simple.pdf": ("01. ACTIVACIÓN", "2025-02-27", "nota_simple_registral"),
    })
    sl.poblar_sala_lectura(case_id)

    ficheros = _ficheros(case_dir)
    assert len(ficheros) == 2, [p.name for p in ficheros]
    # Los dos contenidos siguen ahí: ninguno pisó al otro.
    assert {p.read_bytes() for p in ficheros} == {
        b"%PDF-NOTA-DRIVE", b"%PDF-NOTA-CORREO-distinto",
    }
    # Uno conserva el nombre canónico y el otro lleva el sufijo `_2` de la skill.
    nombres = sorted(p.name for p in ficheros)
    assert nombres == [
        "2025-02-27_activacion_nota_simple_registral.pdf",
        "2025-02-27_activacion_nota_simple_registral_2.pdf",
    ], nombres
    # Y el catálogo dice dónde está cada uno, sin dos filas apuntando al mismo sitio.
    rutas = [e.ruta_sala_lectura for e in cat.load_catalog(case_id)]
    assert len(set(rutas)) == len(rutas) == 2


def test_colision_triple_numera_2_y_3(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("01_Drive EV", "a.pdf", b"%PDF-A"),
        ("03_Email", "b.pdf", b"%PDF-B"),
        ("04_Manual", "c.pdf", b"%PDF-C"),
    ])
    _fijar(cat, case_id, {
        n: ("07. RECLAMACIONES", "2025-12-23", "correo_interno")
        for n in ("a.pdf", "b.pdf", "c.pdf")
    })
    sl.poblar_sala_lectura(case_id)

    nombres = sorted(p.name for p in _ficheros(case_dir))
    assert nombres == [
        "2025-12-23_reclamacion_correo_interno.pdf",
        "2025-12-23_reclamacion_correo_interno_2.pdf",
        "2025-12-23_reclamacion_correo_interno_3.pdf",
    ], nombres
    assert {p.read_bytes() for p in _ficheros(case_dir)} == {b"%PDF-A", b"%PDF-B", b"%PDF-C"}


def test_la_desambiguacion_no_depende_del_orden_del_catalogo(tmp_casos_root):
    """Quién se queda el nombre pelado lo decide el hash, no el orden de las filas.

    Si dependiera del orden, una reconstrucción del catálogo que reordenara las filas
    intercambiaría los nombres de dos documentos entre corridas: el `_2` de ayer sería
    el pelado de hoy. Nadie perdería bytes, pero una cita del letrado a
    `…_2.pdf` apuntaría a otro documento.
    """
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("01_Drive EV", "a.pdf", b"%PDF-A"),
        ("03_Email", "b.pdf", b"%PDF-B"),
    ])
    _fijar(cat, case_id, {
        "a.pdf": ("01. ACTIVACIÓN", "2025-02-27", "mismo_nombre"),
        "b.pdf": ("01. ACTIVACIÓN", "2025-02-27", "mismo_nombre"),
    })
    sl.poblar_sala_lectura(case_id)
    # Sin esto el test pasaría ya ANTES del arreglo, y por la razón equivocada: en el
    # layout por fuente los dos ficheros caen en carpetas distintas, no colisionan, y
    # sus rutas son estables porque nadie tuvo que desambiguar nada.
    assert len({p.parent for p in _ficheros(case_dir)}) == 1
    antes = {e.hash: e.ruta_sala_lectura for e in cat.load_catalog(case_id)}

    # Se invierte el orden de las filas del catálogo en disco y se vuelve a poblar.
    path = case_dir / "01_Procesado" / "indice_documental.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    path.write_text(yaml.dump(list(reversed(data)), allow_unicode=True, sort_keys=False),
                    encoding="utf-8")
    res = sl.poblar_sala_lectura(case_id)

    despues = {e.hash: e.ruta_sala_lectura for e in cat.load_catalog(case_id)}
    assert despues == antes
    assert res["acciones"].get("MOVED", 0) == 0
    assert len(_ficheros(case_dir)) == 2
