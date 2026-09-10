"""Los nueve hallazgos de la R1 adversarial sobre la sala plana, uno por test.

Informe: `docs/superpowers/plans/2026-09-10-sala-lectura-plana-r1-adversarial-review.md`
(veredicto NO-SHIP, 12 hallazgos, dos de los ALTOS reproducidos ejecutando).

Aquí van solo los que se remedian en el diff. Los cuatro que se confirman como
**preexistentes** y quedan fuera de alcance —H-04 (una ruta existente se acepta sin
mirar sus bytes), H-05 (el dedup no repara referencias y la reconstrucción deja
huérfanos), H-10 (no hay transacción ni exclusión entre corridas) y la mitad de H-11
que es la sobrescritura de un fichero sin fila— viven en `docs/MEJORAS_FUTURAS.md`, con
su disparador. No se prueban como si estuvieran arreglados.
"""
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


def _caso(case_manager, inventory, catalogo, docs, case_id="EV-2026-R1"):
    case_dir = case_manager.ensure_case(case_id)
    for sub, name, content in docs:
        p = case_dir / "00_Input" / sub / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content)
    inventory.scan(case_id)
    catalogo.build_catalog(case_id)
    return case_id, case_dir


def _fijar(catalogo, case_id, por_nombre, *, tipo="01. ACTIVACIÓN", fecha="2025-02-27"):
    entries = catalogo.load_catalog(case_id)
    for e in entries:
        if e.nombre_original in por_nombre:
            e.tipo_documental = tipo
            e.fecha_doc = fecha
            e.descripcion = por_nombre[e.nombre_original]
            e.confianza = 1.0
    catalogo.save_catalog(case_id, entries)


def _sala(case_dir):
    return case_dir / "01_Procesado" / "Sala lectura"


def _ficheros(case_dir):
    return sorted(p for p in _sala(case_dir).rglob("*")
                  if p.is_file() and p.name not in ("INDICE.md", "CRONOLOGIA.md"))


def _por_hash(catalogo, case_id):
    return {e.hash: e for e in catalogo.load_catalog(case_id)}


# --- H-01: el sufijo generado choca con un nombre natural ---------------------


def test_h01_el_sufijo_generado_no_pisa_un_nombre_natural(tmp_casos_root):
    """Descripciones `mismo`, `mismo` y `mismo_2` producían dos rutas finales iguales.

    El razonamiento por grupo no lo veía: `a`+`b` forman un grupo y `c` otro, y el
    `_2` que el primero generaba era exactamente el nombre natural del segundo.
    """
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso(cm, inv, cat, [
        ("01_Drive EV", "a.pdf", b"%PDF-A"),
        ("03_Email", "b.pdf", b"%PDF-B"),
        ("04_Manual", "c.pdf", b"%PDF-C"),
    ])
    _fijar(cat, case_id, {"a.pdf": "mismo", "b.pdf": "mismo", "c.pdf": "mismo_2"})
    sl.poblar_sala_lectura(case_id)

    ficheros = _ficheros(case_dir)
    assert len(ficheros) == 3, [p.name for p in ficheros]
    assert {p.read_bytes() for p in ficheros} == {b"%PDF-A", b"%PDF-B", b"%PDF-C"}
    rutas = [e.ruta_sala_lectura for e in cat.load_catalog(case_id)]
    assert len(set(rutas)) == 3
    # Y cada fila apunta a SUS bytes, no solo el conjunto cuadrando.
    for e in cat.load_catalog(case_id):
        copia = case_dir / "01_Procesado" / e.ruta_sala_lectura
        origen = case_dir / "00_Input" / e.ruta_relativa
        assert copia.read_bytes() == origen.read_bytes(), e.nombre_original


# --- H-02: reasignación de citas y traslados que se borran entre sí -----------


def test_h02_un_hash_menor_que_llega_despues_no_mueve_los_nombres_ya_citados(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso(cm, inv, cat, [
        ("01_Drive EV", "a.pdf", b"%PDF-A"),
        ("03_Email", "b.pdf", b"%PDF-B"),
    ])
    _fijar(cat, case_id, {"a.pdf": "mismo", "b.pdf": "mismo"})
    sl.poblar_sala_lectura(case_id)
    antes = {e.hash: e.ruta_sala_lectura for e in cat.load_catalog(case_id)}

    # Entra un tercero al mismo grupo. Se prueban VARIOS bytes para no depender de que
    # el hash del añadido caiga por encima o por debajo de los dos que ya estaban.
    for i, payload in enumerate((b"%PDF-C", b"%PDF-D", b"%PDF-E")):
        p = case_dir / "00_Input" / "04_Manual" / f"c{i}.pdf"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(payload)
    inv.scan(case_id)
    cat.build_catalog(case_id)
    _fijar(cat, case_id, {f"c{i}.pdf": "mismo" for i in range(3)})
    res = sl.poblar_sala_lectura(case_id)

    despues = {e.hash: e.ruta_sala_lectura for e in cat.load_catalog(case_id)}
    # Los dos que ya estaban conservan su ruta: ninguna cita se muda de documento.
    for h, ruta in antes.items():
        assert despues[h] == ruta, f"la cita de {h[:8]} cambió de {ruta} a {despues[h]}"
    assert len(_ficheros(case_dir)) == 5
    assert res["acciones"].get("MOVED", 0) == 0


def test_h02_una_fila_sin_fuente_conserva_su_copia_y_su_nombre(tmp_casos_root):
    """Al salir del plan por `MISSING_SRC` dejaba su nombre libre y otro lo tomaba."""
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso(cm, inv, cat, [
        ("01_Drive EV", "a.pdf", b"%PDF-A"),
        ("03_Email", "b.pdf", b"%PDF-B"),
    ])
    _fijar(cat, case_id, {"a.pdf": "mismo", "b.pdf": "mismo"})
    sl.poblar_sala_lectura(case_id)
    por_hash = _por_hash(cat, case_id)
    fila_a = next(e for e in por_hash.values() if e.nombre_original == "a.pdf")
    copia_a = case_dir / "01_Procesado" / fila_a.ruta_sala_lectura

    (case_dir / "00_Input" / "01_Drive EV" / "a.pdf").unlink()
    res = sl.poblar_sala_lectura(case_id)

    assert res["acciones"].get("MISSING_SRC") == 1
    assert copia_a.exists(), "la copia válida de la fila sin fuente se ha perdido"
    assert copia_a.read_bytes() == b"%PDF-A", "otra fila ha ocupado su nombre"
    rutas = [e.ruta_sala_lectura for e in cat.load_catalog(case_id) if e.ruta_sala_lectura]
    assert len(set(rutas)) == len(rutas)


# --- H-03: filas sin hash ------------------------------------------------------


def test_h03_dos_filas_sin_hash_no_comparten_casilla(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso(cm, inv, cat, [
        ("01_Drive EV", "a.pdf", b"%PDF-A"),
        ("03_Email", "b.pdf", b"%PDF-B"),
    ])
    _fijar(cat, case_id, {"a.pdf": "uno", "b.pdf": "dos"})
    entries = cat.load_catalog(case_id)
    for e in entries:
        e.hash = ""          # el modelo y el cargador lo admiten
    cat.save_catalog(case_id, entries)

    sl.poblar_sala_lectura(case_id)

    ficheros = _ficheros(case_dir)
    assert len(ficheros) == 2, [p.name for p in ficheros]
    assert {p.read_bytes() for p in ficheros} == {b"%PDF-A", b"%PDF-B"}
    rutas = [e.ruta_sala_lectura for e in cat.load_catalog(case_id)]
    assert len(set(rutas)) == 2


def test_h03_filas_sin_hash_que_colisionan_de_nombre_tambien_se_separan(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso(cm, inv, cat, [
        ("01_Drive EV", "a.pdf", b"%PDF-A"),
        ("03_Email", "b.pdf", b"%PDF-B"),
    ])
    _fijar(cat, case_id, {"a.pdf": "igual", "b.pdf": "igual"})
    entries = cat.load_catalog(case_id)
    for e in entries:
        e.hash = ""
    cat.save_catalog(case_id, entries)

    sl.poblar_sala_lectura(case_id)

    ficheros = _ficheros(case_dir)
    assert len(ficheros) == 2, [p.name for p in ficheros]
    assert {p.read_bytes() for p in ficheros} == {b"%PDF-A", b"%PDF-B"}


# --- H-06 / H-07 / H-08: la poda ----------------------------------------------


def test_h06_la_poda_no_sigue_ni_borra_un_enlace(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso(cm, inv, cat, [("01_Drive EV", "a.pdf", b"%PDF-A")])
    _fijar(cat, case_id, {"a.pdf": "uno"})
    fuera = case_dir / "01_Procesado" / "fuera_de_la_sala"
    (fuera / "vacio").mkdir(parents=True)
    (fuera / "con_dato").mkdir()
    (fuera / "con_dato" / "documento.txt").write_text("dato", encoding="utf-8")
    sala = _sala(case_dir)
    sala.mkdir(parents=True, exist_ok=True)
    enlace = sala / "enlace"
    try:
        enlace.symlink_to(fuera, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("este entorno no permite crear enlaces simbólicos")

    sl.poblar_sala_lectura(case_id)

    assert enlace.exists(), "la poda borró el enlace"
    assert (fuera / "vacio").is_dir(), "la poda entró por el enlace y borró fuera"
    assert (fuera / "con_dato" / "documento.txt").exists()


def test_h07_la_poda_respeta_el_subarbol_de_plan(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso(cm, inv, cat, [("01_Drive EV", "a.pdf", b"%PDF-A")])
    _fijar(cat, case_id, {"a.pdf": "uno"})
    hondo = _sala(case_dir) / "_plan" / "lote" / "pendiente"
    hondo.mkdir(parents=True)

    sl.poblar_sala_lectura(case_id)

    assert hondo.is_dir(), "se filtraba el nombre del directorio, no su subárbol"


def test_h08_un_error_de_poda_se_dice_en_vez_de_tragarse(tmp_casos_root, monkeypatch):
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso(cm, inv, cat, [("01_Drive EV", "a.pdf", b"%PDF-A")])
    _fijar(cat, case_id, {"a.pdf": "uno"})
    (_sala(case_dir) / "sin_permiso").mkdir(parents=True)

    real_rmdir = Path.rmdir

    def rmdir_que_falla(self):
        if self.name == "sin_permiso":
            raise PermissionError(13, "denegado")
        return real_rmdir(self)

    monkeypatch.setattr(Path, "rmdir", rmdir_que_falla)
    res = sl.poblar_sala_lectura(case_id)

    assert res["problemas_poda"], "un PermissionError de la poda salía en silencio"
    assert any("sin_permiso" in p for p in res["problemas_poda"])


def test_la_poda_sigue_retirando_el_cascaron_por_fuente(tmp_casos_root):
    """Control positivo: los tres arreglos de arriba no han desactivado la poda."""
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso(cm, inv, cat, [("01_Drive EV", "a.pdf", b"%PDF-A")])
    _fijar(cat, case_id, {"a.pdf": "uno"})
    (_sala(case_dir) / "Drive E&V").mkdir(parents=True)

    sl.poblar_sala_lectura(case_id)

    assert not (_sala(case_dir) / "Drive E&V").exists()


# --- H-09: metadatos de bundle ------------------------------------------------


def test_h09_una_corrida_sin_crm_docs_no_borra_el_padre_ya_registrado(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso(cm, inv, cat, [("05_CRM/01_Demanda", "d.pdf", b"%PDF-D")])
    _fijar(cat, case_id, {"d.pdf": "uno"})
    entries = cat.load_catalog(case_id)
    entries[0].parent_id = "padre_existente"
    entries[0].orden_en_bundle = 7
    cat.save_catalog(case_id, entries)

    sl.poblar_sala_lectura(case_id)          # sin crm_docs: no se detecta bundle

    e = cat.load_catalog(case_id)[0]
    assert (e.parent_id, e.orden_en_bundle) == ("padre_existente", 7)


# --- H-11: un directorio ocupando el destino ----------------------------------


def test_h11_un_directorio_en_el_destino_no_se_acepta_como_copia(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso(cm, inv, cat, [("01_Drive EV", "a.pdf", b"%PDF-A")])
    _fijar(cat, case_id, {"a.pdf": "uno"})
    estorbo = _sala(case_dir) / "2025-02-27_activacion_uno.pdf"
    estorbo.mkdir(parents=True)

    res = sl.poblar_sala_lectura(case_id)

    assert res["acciones"].get("DST_OCUPADO_POR_DIRECTORIO") == 1
    assert not (estorbo / "a.pdf").exists(), "copy2 metió el fichero dentro del directorio"
    assert cat.load_catalog(case_id)[0].ruta_sala_lectura is None


def test_un_fichero_sin_fila_en_el_destino_se_sobrescribe_pero_se_dice(tmp_casos_root):
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso(cm, inv, cat, [("01_Drive EV", "a.pdf", b"%PDF-A")])
    _fijar(cat, case_id, {"a.pdf": "uno"})
    intruso = _sala(case_dir) / "2025-02-27_activacion_uno.pdf"
    intruso.parent.mkdir(parents=True, exist_ok=True)
    intruso.write_bytes(b"SIN FILA EN EL CATALOGO")

    res = sl.poblar_sala_lectura(case_id)

    assert res["acciones"].get("SOBRESCRITO_SIN_FILA") == 1
    assert intruso.read_bytes() == b"%PDF-A"


# --- H-12: el nombre exacto, que es lo que mata al mutante --------------------


def test_h12_el_nombre_de_cada_documento_es_su_sha8(tmp_casos_root):
    """Fija la correspondencia hash→fichero, no solo el conjunto de nombres.

    Los seis tests de `test_sala_lectura_plana.py` seguían verdes con un mutante que
    ordenaba los hashes al revés (E6 del informe): comprobaban conjuntos y estabilidad,
    no quién se llevaba cada nombre. Con `__<sha8>` para todos los del grupo, la
    correspondencia es comprobable documento a documento y el mutante muere.
    """
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso(cm, inv, cat, [
        ("01_Drive EV", "a.pdf", b"%PDF-A"),
        ("03_Email", "b.pdf", b"%PDF-B"),
    ])
    _fijar(cat, case_id, {"a.pdf": "mismo", "b.pdf": "mismo"})
    sl.poblar_sala_lectura(case_id)

    for e in cat.load_catalog(case_id):
        esperado = f"2025-02-27_activacion_mismo__{e.hash[:8]}.pdf"
        assert Path(e.ruta_sala_lectura).name == esperado, e.nombre_original
        copia = case_dir / "01_Procesado" / e.ruta_sala_lectura
        assert copia.read_bytes() == (case_dir / "00_Input" / e.ruta_relativa).read_bytes()


def test_un_documento_solo_conserva_el_nombre_pelado(tmp_casos_root):
    """El `__<sha8>` es para los grupos colisionados; sin colisión no ensucia nada."""
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso(cm, inv, cat, [("01_Drive EV", "a.pdf", b"%PDF-A")])
    _fijar(cat, case_id, {"a.pdf": "solo"})
    sl.poblar_sala_lectura(case_id)

    assert (_sala(case_dir) / "2025-02-27_activacion_solo.pdf").is_file()


def test_el_resumen_cuenta_ficheros_escritos_y_no_copias_intentadas(tmp_casos_root):
    """`COPY: 31` con 15 ficheros en disco fue el síntoma de W-048UOL (2026-09-10)."""
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso(cm, inv, cat, [
        ("01_Drive EV", "a.pdf", b"%PDF-A"),
        ("03_Email", "b.pdf", b"%PDF-B"),
        ("04_Manual", "c.pdf", b"%PDF-C"),
    ])
    _fijar(cat, case_id, {"a.pdf": "x", "b.pdf": "x", "c.pdf": "x"})
    res = sl.poblar_sala_lectura(case_id)

    assert res["n_en_sala"] == len(_ficheros(case_dir)) == 3
