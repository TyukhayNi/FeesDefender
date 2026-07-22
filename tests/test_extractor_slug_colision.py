"""Regresión #47: colisión de slug en `raw_text/` y `MD/` (stem-only).

Dos ficheros de origen con el mismo *stem* pero distinto contenido (caso real:
los cuatro `_chat.txt` de WhatsApp de W-02VND1) colapsaban al mismo
`{slug}.txt`/`{slug}.md` y se pisaban en silencio, perdiendo prueba. El nombre
de salida debe ser libre de colisiones: slug del stem + sufijo SHA-8 del origen.
Copias byte-idénticas (mismo SHA) comparten nombre a propósito (dedup).
"""

from __future__ import annotations

import importlib


def _reload():
    from core import case_manager, extractor, inventory, markdown_generator
    importlib.reload(inventory)
    importlib.reload(extractor)
    importlib.reload(markdown_generator)
    importlib.reload(case_manager)
    return case_manager, inventory, extractor, markdown_generator


def test_output_slug_distingue_por_contenido():
    from core.utils import output_slug

    a = output_slug("02_Whatsapp/identidades_vigiladas/_chat.txt", "a" * 64)
    b = output_slug("02_Whatsapp/PersonaOcho/_chat.txt", "b" * 64)
    assert a != b  # mismo stem, distinto contenido → nombres distintos

    # Copias byte-idénticas (mismo SHA) → mismo nombre (dedup deliberado).
    c = output_slug("01_Drive EV/nota.pdf", "c" * 64)
    d = output_slug("03_Email/_enlaces/nota.pdf", "c" * 64)
    assert c == d

    # Sin SHA: degrada al slug del stem (compatibilidad).
    assert output_slug("x/nota.pdf", "") == "nota"


def test_extract_all_no_colisiona_mismo_stem(tmp_casos_root):
    case_manager, inventory, extractor, _ = _reload()
    case_dir = case_manager.ensure_case("EV-2026-TEST")
    inp = case_dir / "00_Input"
    (inp / "a").mkdir(parents=True, exist_ok=True)
    (inp / "b").mkdir(parents=True, exist_ok=True)
    (inp / "a" / "_chat.txt").write_text("conversacion con PersonaUno", encoding="utf-8")
    (inp / "b" / "_chat.txt").write_text("conversacion distinta con PersonaOcho", encoding="utf-8")
    inventory.scan("EV-2026-TEST")

    res = extractor.extract_all("EV-2026-TEST")
    outputs = {r.output_path for r in res}
    assert len(outputs) == 2  # dos .txt distintos, ninguno pisado

    textos = [p.read_text(encoding="utf-8") for p in outputs]
    assert any("PersonaUno" in t for t in textos)
    assert any("PersonaOcho" in t for t in textos)


def test_build_md_no_colisiona_mismo_stem(tmp_casos_root):
    case_manager, inventory, extractor, markdown_generator = _reload()
    case_dir = case_manager.ensure_case("EV-2026-TEST")
    inp = case_dir / "00_Input"
    (inp / "a").mkdir(parents=True, exist_ok=True)
    (inp / "b").mkdir(parents=True, exist_ok=True)
    (inp / "a" / "_chat.txt").write_text("hilo PersonaUno", encoding="utf-8")
    (inp / "b" / "_chat.txt").write_text("hilo PersonaOcho diferente", encoding="utf-8")
    inventory.scan("EV-2026-TEST")
    res = extractor.extract_all("EV-2026-TEST")

    mds = set(markdown_generator.build("EV-2026-TEST", res))
    assert len(mds) == 2  # dos .md distintos

    cuerpos = [p.read_text(encoding="utf-8") for p in mds]
    assert any("PersonaUno" in c for c in cuerpos)
    assert any("PersonaOcho" in c for c in cuerpos)


def test_extract_all_migra_cache_legacy_sin_reocr(tmp_casos_root):
    """Stem INEQUÍVOCO con `.txt` de naming antiguo en disco: `extract_all` lo
    renombra al nombre nuevo (sufijo SHA) y hace SKIP — preserva el OCR caro."""
    import hashlib
    import json

    case_manager, inventory, extractor, _ = _reload()
    case_dir = case_manager.ensure_case("EV-2026-TEST")
    (case_dir / "00_Input" / "informe.pdf").write_bytes(b"%PDF informe real")
    inventory.scan("EV-2026-TEST")
    sha = hashlib.sha256(b"%PDF informe real").hexdigest()

    raw = case_dir / "01_Procesado" / "raw_text"
    raw.mkdir(parents=True, exist_ok=True)
    (raw / "informe.txt").write_text("TEXTO OCR CARO", encoding="utf-8")  # nombre viejo
    (raw / "_extract_state.json").write_text(json.dumps({
        "extractor_version": extractor.EXTRACTOR_VERSION,
        "files": {"informe.pdf": {"source_sha256": sha, "method": "docling", "chars": 14}},
    }, ensure_ascii=False), encoding="utf-8")

    res = extractor.extract_all("EV-2026-TEST")
    assert len(res) == 1
    assert res[0].skipped is True  # NO re-OCR
    assert res[0].output_path.read_text(encoding="utf-8") == "TEXTO OCR CARO"
    assert not (raw / "informe.txt").exists()  # migrado, no duplicado


def test_extract_all_colision_legacy_recupera_contenido(tmp_casos_root):
    """Con un único `.txt` antiguo AMBIGUO (dos `_chat.txt` → un `chat.txt`),
    `extract_all` no confía en él: re-extrae ambos y recupera el contenido real
    de cada uno (el chat perdido vuelve)."""
    import hashlib
    import json

    case_manager, inventory, extractor, _ = _reload()
    case_dir = case_manager.ensure_case("EV-2026-TEST")
    inp = case_dir / "00_Input"
    (inp / "a").mkdir(parents=True, exist_ok=True)
    (inp / "b").mkdir(parents=True, exist_ok=True)
    ca, cb = "chat con PersonaUno", "chat con PersonaOcho distinto"
    (inp / "a" / "_chat.txt").write_text(ca, encoding="utf-8")
    (inp / "b" / "_chat.txt").write_text(cb, encoding="utf-8")
    inventory.scan("EV-2026-TEST")

    raw = case_dir / "01_Procesado" / "raw_text"
    raw.mkdir(parents=True, exist_ok=True)
    (raw / "chat.txt").write_text(cb, encoding="utf-8")  # solo sobrevivió uno
    (raw / "_extract_state.json").write_text(json.dumps({
        "extractor_version": extractor.EXTRACTOR_VERSION,
        "files": {
            "a/_chat.txt": {"source_sha256": hashlib.sha256(ca.encode()).hexdigest(),
                            "method": "raw", "chars": len(ca)},
            "b/_chat.txt": {"source_sha256": hashlib.sha256(cb.encode()).hexdigest(),
                            "method": "raw", "chars": len(cb)},
        },
    }, ensure_ascii=False), encoding="utf-8")

    res = extractor.extract_all("EV-2026-TEST")
    by_rel = {r.rel_path: r for r in res}
    assert by_rel["a/_chat.txt"].output_path.read_text(encoding="utf-8") == ca
    assert by_rel["b/_chat.txt"].output_path.read_text(encoding="utf-8") == cb
    assert by_rel["a/_chat.txt"].output_path != by_rel["b/_chat.txt"].output_path


def test_sala_lectura_md_path_usa_sufijo_sha():
    """`_md_path` debe apuntar al nombre real generado (con sufijo SHA), no al
    stem desnudo, para no romper el enlace cuando dos docs comparten stem."""
    from core import sala_lectura
    from core.catalogo_documental import CatalogEntry
    from core.utils import output_slug

    rel = "02_Whatsapp/identidades_vigiladas/_chat.txt"
    e = CatalogEntry(
        id_doc="d1", ruta_relativa=rel, nombre_original="_chat.txt",
        hash="deadbeefcafe1234",
    )
    p = sala_lectura._md_path("EV-2026-TEST", e)
    assert p.name == output_slug(rel, e.hash) + ".md"
    # El enlace relativo del índice usa el mismo nombre.
    assert sala_lectura._link_md(e) == f"../MD/{output_slug(rel, e.hash)}.md"
