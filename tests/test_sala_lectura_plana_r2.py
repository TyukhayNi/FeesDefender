"""Los tres hallazgos que sobrevivieron a la primera remediación de la sala plana.

Vienen de la R1 que la sesión hermana corrió sobre **su** implementación del mismo
mecanismo (`_sin_colision`, con `__<sha6>` y asignación por orden de llegada). Su objeto
no es el mío, pero tres de sus cinco hallazgos atacan el mecanismo y **se reproducían en
mi código ya remediado**:

* **su H-01, la mitad que no cubría mi asignación por hash** — `old.unlink()` no
  comprobaba si otra fila de la misma corrida ya ocupaba ese destino **según el
  filesystem**. En Windows `Manual/` y `manual/` son la misma carpeta, así que comparar
  las cadenas dice que son dos. Lo reprodujo migrando, sin reordenar nada.
* **su H-02, hashes vacíos** — el dueño de una ruta reservada era `hash or ""`, luego
  todas las filas sin hash tenían el mismo dueño y una podía tomar la ruta de otra.
* **el extra de «borrar antes de copiar»** — anterior a los dos diffs, pero la migración
  del layout lo activa sobre el expediente entero de golpe (26 documentos en W-02YZO4).
  Reproducido allí inyectando un `OSError` en `shutil.copy2`.

Acta con su informe literal:
`docs/superpowers/plans/2026-09-10-sala-lectura-plana-r2-hermana-adversarial-review.md`.
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


def _caso(case_manager, inventory, catalogo, docs, case_id="EV-2026-R2"):
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


# --- La ruta se compara como la ve el filesystem -------------------------------


def test_una_ruta_vieja_que_solo_difiere_en_MAYUSCULAS_no_se_borra(tmp_casos_root):
    """El destino nuevo de una fila era la ruta vieja de otra, con otra capitalización.

    En Windows y en el Drive del despacho son el mismo fichero. Comparando cadenas, el
    `unlink` de la segunda fila borraba la copia que la primera acababa de escribir.
    """
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso(cm, inv, cat, [
        ("01_Drive EV", "a.pdf", b"%PDF-A"),
        ("03_Email", "b.pdf", b"%PDF-B"),
    ])
    _fijar(cat, case_id, {"a.pdf": "uno", "b.pdf": "dos"})
    sl.poblar_sala_lectura(case_id)
    entries = cat.load_catalog(case_id)
    destino_a = next(e.ruta_sala_lectura for e in entries if e.nombre_original == "a.pdf")

    # La fila B declara como ruta vieja la de A, escrita con otra capitalización: es la
    # forma que toma el solapamiento al migrar del layout por fuente.
    for e in entries:
        if e.nombre_original == "b.pdf":
            e.ruta_sala_lectura = destino_a.replace("Sala lectura", "SALA LECTURA")
    cat.save_catalog(case_id, entries)

    sl.poblar_sala_lectura(case_id)

    copia_a = case_dir / "01_Procesado" / destino_a
    assert copia_a.exists(), "el unlink de otra fila borró la copia de A"
    assert copia_a.read_bytes() == b"%PDF-A"
    for e in cat.load_catalog(case_id):
        p = case_dir / "01_Procesado" / e.ruta_sala_lectura
        assert p.exists(), f"{e.nombre_original} apunta a una ruta inexistente"


def test_clave_ruta_iguala_separadores_y_capitalizacion(tmp_casos_root):
    _, _, _, sl = _reload()
    assert sl.clave_ruta("Sala lectura/Manual/x.pdf") == sl.clave_ruta("Sala lectura\\manual\\x.pdf")
    assert sl.clave_ruta("Sala lectura/a.pdf") != sl.clave_ruta("Sala lectura/b.pdf")


# --- Dos filas sin hash no son el mismo dueño ---------------------------------


def test_una_fila_sin_hash_no_toma_la_ruta_reservada_por_otra_sin_hash(tmp_casos_root):
    """El dueño de una reserva era `hash or ""`: todas las filas sin hash lo compartían."""
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso(cm, inv, cat, [
        ("01_Drive EV", "a.pdf", b"%PDF-A"),
        ("03_Email", "b.pdf", b"%PDF-B"),
    ])
    _fijar(cat, case_id, {"a.pdf": "mismo", "b.pdf": "mismo"})
    entries = cat.load_catalog(case_id)
    for e in entries:
        e.hash = ""
    cat.save_catalog(case_id, entries)
    sl.poblar_sala_lectura(case_id)
    ruta_a = next(e.ruta_sala_lectura for e in cat.load_catalog(case_id)
                  if e.nombre_original == "a.pdf")

    # Se retira la fuente de A: sale del plan por `MISSING_SRC` y su copia sigue en disco.
    (case_dir / "00_Input" / "01_Drive EV" / "a.pdf").unlink()
    res = sl.poblar_sala_lectura(case_id)

    assert res["acciones"].get("MISSING_SRC") == 1
    copia_a = case_dir / "01_Procesado" / ruta_a
    assert copia_a.exists() and copia_a.read_bytes() == b"%PDF-A", (
        "una fila sin hash tomó la ruta reservada por otra sin hash")


def test_clave_dueno_distingue_filas_sin_hash_y_agrupa_las_deduplicadas(tmp_casos_root):
    _, _, cat, sl = _reload()
    from core.catalogo_documental import CatalogEntry

    def fila(ruta, hash_):
        return CatalogEntry(id_doc=ruta, ruta_relativa=ruta, nombre_original=ruta, hash=hash_)

    # Sin hash: dueños distintos, para que ninguna tome la ruta de la otra.
    assert sl.clave_dueno(fila("a.pdf", "")) != sl.clave_dueno(fila("b.pdf", ""))
    # Con hash: mismo dueño, para que el representante del dedup pueda tomar la ruta
    # que su gemela reservó. Esa parte NO puede romperse al arreglar la de arriba.
    assert sl.clave_dueno(fila("a.pdf", "abc123")) == sl.clave_dueno(fila("b.pdf", "abc123"))


# --- Copiar antes de borrar ----------------------------------------------------


def test_un_fallo_de_copia_no_deja_la_copia_vieja_borrada(tmp_casos_root, monkeypatch):
    """`old.unlink()` iba ANTES del `copy2`, y la migración lo activa en masa."""
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso(cm, inv, cat, [("01_Drive EV", "a.pdf", b"%PDF-A")])
    _fijar(cat, case_id, {"a.pdf": "uno"})
    # Estado del layout viejo: la copia vive bajo `Drive E&V/`.
    nombre = "2025-02-27_activacion_uno.pdf"
    viejo_rel = f"Sala lectura/Drive E&V/{nombre}"
    viejo = case_dir / "01_Procesado" / viejo_rel
    viejo.parent.mkdir(parents=True, exist_ok=True)
    viejo.write_bytes(b"%PDF-A")
    entries = cat.load_catalog(case_id)
    entries[0].ruta_sala_lectura = viejo_rel
    cat.save_catalog(case_id, entries)

    def copia_que_falla(src, dst, *a, **k):
        raise OSError("fallo de copia simulado")

    monkeypatch.setattr(sl.shutil, "copy2", copia_que_falla)
    with pytest.raises(OSError):
        sl.poblar_sala_lectura(case_id)

    assert viejo.exists(), "la copia vieja se borró y la nueva no se llegó a escribir"
    assert viejo.read_bytes() == b"%PDF-A"
    # Y el catálogo sigue apuntando a algo que existe.
    assert cat.load_catalog(case_id)[0].ruta_sala_lectura == viejo_rel


def test_la_migracion_normal_sigue_retirando_la_copia_vieja(tmp_casos_root):
    """Control positivo de lo anterior: copiar antes de borrar no deja las dos copias."""
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso(cm, inv, cat, [("01_Drive EV", "a.pdf", b"%PDF-A")])
    _fijar(cat, case_id, {"a.pdf": "uno"})
    nombre = "2025-02-27_activacion_uno.pdf"
    viejo_rel = f"Sala lectura/Drive E&V/{nombre}"
    viejo = case_dir / "01_Procesado" / viejo_rel
    viejo.parent.mkdir(parents=True, exist_ok=True)
    viejo.write_bytes(b"%PDF-A")
    entries = cat.load_catalog(case_id)
    entries[0].ruta_sala_lectura = viejo_rel
    cat.save_catalog(case_id, entries)

    res = sl.poblar_sala_lectura(case_id)

    assert res["acciones"].get("MOVED") == 1
    assert not viejo.exists()
    assert len(_ficheros(case_dir)) == 1
    assert (_sala(case_dir) / nombre).read_bytes() == b"%PDF-A"


# --- El ordinal es el ÚLTIMO recurso, no el primero ---------------------------


def test_un_pelado_ocupado_cae_al_sha8_y_no_a_un_ordinal(tmp_casos_root):
    """Si el nombre pelado está reservado, el fallback sale del documento, no del conjunto.

    Un `_2` depende de quién más esté en la corrida —y por tanto se mueve— mientras el
    `__<sha8>` sale del propio documento. Es la misma razón por la que el discriminante
    dejó de ser un ordinal.

    El estado que hace falta —una fila EN el catálogo pero FUERA del plan— se monta
    retirando su fuente **sin reconstruir** el catálogo: `build_catalog` parte de lo que
    hay en `00_Input`, así que una reconstrucción la borraría y no habría reserva.
    """
    cm, inv, cat, sl = _reload()
    case_id, case_dir = _caso(cm, inv, cat, [
        ("01_Drive EV", "a.pdf", b"%PDF-A"),
        ("03_Email", "b.pdf", b"%PDF-B"),
    ])
    _fijar(cat, case_id, {"a.pdf": "uno", "b.pdf": "dos"})
    sl.poblar_sala_lectura(case_id)
    pelado = "Sala lectura/2025-02-27_activacion_uno.pdf"
    assert [e.ruta_sala_lectura for e in cat.load_catalog(case_id)
            if e.nombre_original == "a.pdf"] == [pelado]

    # A pierde su fuente (sin reconstruir: su fila sigue en el catálogo con su copia), y
    # B pasa a tener la MISMA descripción, así que su grupo no colisiona y pediría ese
    # pelado, que es justo el que A tiene reservado.
    (case_dir / "00_Input" / "01_Drive EV" / "a.pdf").unlink()
    entries = cat.load_catalog(case_id)
    for e in entries:
        if e.nombre_original == "b.pdf":
            e.descripcion = "uno"
    cat.save_catalog(case_id, entries)

    res = sl.poblar_sala_lectura(case_id)

    assert res["acciones"].get("MISSING_SRC") == 1
    fila_b = next(e for e in cat.load_catalog(case_id) if e.nombre_original == "b.pdf")
    assert f"__{fila_b.hash[:8]}" in fila_b.ruta_sala_lectura, fila_b.ruta_sala_lectura
    assert not fila_b.ruta_sala_lectura.endswith("_2.pdf"), fila_b.ruta_sala_lectura
    # Y la copia de A, que ya no tiene fuente, sigue intacta bajo su nombre pelado.
    copia_a = case_dir / "01_Procesado" / pelado
    assert copia_a.exists() and copia_a.read_bytes() == b"%PDF-A"
