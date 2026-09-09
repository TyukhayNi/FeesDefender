"""I5: clase y estado son ejes distintos, el bundle es un grupo, y la cadena se verifica."""
import hashlib
import json

import pytest

from core.procedimiento import artefacto

SM = "01_Procesado/02_Sala de máquina"


def _arbol(tmp_path, filas, *, ocr=()):
    (tmp_path / SM).mkdir(parents=True, exist_ok=True)
    (tmp_path / SM / "_cobertura.json").write_text(json.dumps(filas), encoding="utf-8")
    if ocr:
        (tmp_path / SM / "01_OCR").mkdir(parents=True, exist_ok=True)
        for slug in ocr:
            (tmp_path / SM / "01_OCR" / f"{slug}.pdf").write_bytes(b"%PDF-1.4")
    return tmp_path


def _crudo(tmp_path, rel, cuerpo=b"%PDF-1.4 crudo"):
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(cuerpo)
    return hashlib.sha256(cuerpo).hexdigest()


def test_pdf_con_texto_lo_representa_el_crudo(tmp_path):
    sha = _crudo(tmp_path, "00_Input/05_CRM/01_Demanda/d.pdf")
    raiz = _arbol(tmp_path, [{"slug": "d", "rel_path": "05_CRM/01_Demanda/d.pdf",
                              "metodo": "pypdf", "estado": "ok", "sha256": sha}])
    e = artefacto.elegir(raiz, artefacto.cargar(raiz),
                         raw_rel="00_Input/05_CRM/01_Demanda/d.pdf", raw_sha256=sha,
                         sin_cobertura_ok=False)
    assert e.clase is artefacto.Clase.CRUDO
    assert e.rel == "00_Input/05_CRM/01_Demanda/d.pdf"
    assert e.ext == "pdf" and e.calidad == "ok" and e.bloqueo == ""


def test_un_BUNDLE_resuelve_al_artefacto_DEL_PADRE_con_la_peor_calidad(tmp_path):
    """El defecto más caro del selector de la rev. 1: el OCR está en
    `01_OCR/<parent_slug>.pdf` y las filas son de segmento. Derivar la ruta del slug del
    segmento apunta a un fichero que no existe, así que bloqueaba teniendo el PDF íntegro
    al lado.
    """
    sha = _crudo(tmp_path, "00_Input/05_CRM/99_Otros/bundle.pdf")
    raiz = _arbol(tmp_path, [
        {"slug": "bundle__a", "rel_path": "05_CRM/99_Otros/bundle.pdf", "metodo": "ocr",
         "estado": "ok", "sha256": "SEG_A", "parent_slug": "bundle",
         "parent_sha256": sha},
        {"slug": "bundle__b", "rel_path": "05_CRM/99_Otros/bundle.pdf", "metodo": "ocr",
         "estado": "low", "sha256": "SEG_B", "parent_slug": "bundle",
         "parent_sha256": sha},
    ], ocr=["bundle"])
    e = artefacto.elegir(raiz, artefacto.cargar(raiz),
                         raw_rel="00_Input/05_CRM/99_Otros/bundle.pdf", raw_sha256=sha,
                         sin_cobertura_ok=False)
    assert e.bloqueo == "", f"bloqueó teniendo el PDF del padre al lado: {e.bloqueo}"
    assert e.clase is artefacto.Clase.CONVERTIDO
    assert e.rel == f"{SM}/01_OCR/bundle.pdf"
    assert e.calidad == "low", "la calidad de un bundle es la PEOR de sus segmentos"
    assert any("2 segmento" in a for a in e.avisos)


def test_un_bundle_SIN_su_artefacto_bloquea_nombrando_el_padre(tmp_path):
    sha = _crudo(tmp_path, "00_Input/05_CRM/99_Otros/bundle.pdf")
    raiz = _arbol(tmp_path, [
        {"slug": "bundle__a", "rel_path": "05_CRM/99_Otros/bundle.pdf", "metodo": "ocr",
         "estado": "ok", "sha256": "SEG_A", "parent_slug": "bundle",
         "parent_sha256": sha}])
    e = artefacto.elegir(raiz, artefacto.cargar(raiz),
                         raw_rel="00_Input/05_CRM/99_Otros/bundle.pdf", raw_sha256=sha,
                         sin_cobertura_ok=False)
    assert e.bloqueo != "" and "bundle.pdf" in e.bloqueo
    assert e.clase is artefacto.Clase.SIN_REPRESENTANTE


def test_un_DUPLICADO_se_resuelve_por_su_titular(tmp_path):
    """`metodo: duplicado` (MEJORAS #147) dice «este fichero existe aquí y su espejo es
    el del titular». La rev. 1 lo mandaba a «desconocido → bloqueo»."""
    sha = _crudo(tmp_path, "00_Input/01_Drive EV/copia.pdf")
    raiz = _arbol(tmp_path, [
        {"slug": "titular", "rel_path": "05_CRM/01_Demanda/orig.pdf", "metodo": "ocr",
         "estado": "ok", "sha256": "OTRO_SHA"},
        {"slug": "copia", "rel_path": "01_Drive EV/copia.pdf", "metodo": "duplicado",
         "estado": "ok", "sha256": sha, "alias_de": "titular"},
    ], ocr=["titular"])
    e = artefacto.elegir(raiz, artefacto.cargar(raiz),
                         raw_rel="00_Input/01_Drive EV/copia.pdf", raw_sha256=sha,
                         sin_cobertura_ok=False)
    assert e.bloqueo == ""
    assert e.rel == f"{SM}/01_OCR/titular.pdf"
    assert any("titular" in a for a in e.avisos)


def test_un_duplicado_SIN_alias_de_bloquea(tmp_path):
    sha = _crudo(tmp_path, "00_Input/01_Drive EV/copia.pdf")
    raiz = _arbol(tmp_path, [
        {"slug": "copia", "rel_path": "01_Drive EV/copia.pdf", "metodo": "duplicado",
         "estado": "ok", "sha256": sha}])
    e = artefacto.elegir(raiz, artefacto.cargar(raiz),
                         raw_rel="00_Input/01_Drive EV/copia.pdf", raw_sha256=sha,
                         sin_cobertura_ok=False)
    assert "alias_de" in e.bloqueo


def test_un_metodo_ERROR_bloquea_diciendo_QUE_paso(tmp_path):
    """`metodo: error` es un documento que reventó al procesarse. Bloquea, pero no como
    «desconocido»: el remedio es distinto."""
    sha = _crudo(tmp_path, "00_Input/05_CRM/99_Otros/roto.pdf")
    raiz = _arbol(tmp_path, [{"slug": "roto", "rel_path": "05_CRM/99_Otros/roto.pdf",
                              "metodo": "error", "estado": "empty", "sha256": sha,
                              "nota": "fallo al procesar: PdfReadError"}])
    e = artefacto.elegir(raiz, artefacto.cargar(raiz),
                         raw_rel="00_Input/05_CRM/99_Otros/roto.pdf", raw_sha256=sha,
                         sin_cobertura_ok=False)
    assert e.bloqueo != ""
    assert "sala de máquina" in e.bloqueo
    assert "PdfReadError" in e.bloqueo, "el bloqueo debe llevar el motivo real"


def test_ofimatica_representa_el_PDF_convertido_y_CAMBIA_de_extension(tmp_path):
    sha = _crudo(tmp_path, "00_Input/05_CRM/01_Demanda/dem.doc", b"doc binario")
    raiz = _arbol(tmp_path, [{"slug": "dem", "rel_path": "05_CRM/01_Demanda/dem.doc",
                              "metodo": "ofimatica", "estado": "ok", "sha256": sha}],
                  ocr=["dem"])
    e = artefacto.elegir(raiz, artefacto.cargar(raiz),
                         raw_rel="00_Input/05_CRM/01_Demanda/dem.doc", raw_sha256=sha,
                         sin_cobertura_ok=False)
    assert e.clase is artefacto.Clase.CONVERTIDO
    assert e.ext == "pdf"
    assert e.rel == f"{SM}/01_OCR/dem.pdf"


def test_el_OCR_declarado_y_AUSENTE_bloquea_sin_degradar_al_crudo(tmp_path):
    sha = _crudo(tmp_path, "00_Input/05_CRM/99_Otros/esc.pdf")
    raiz = _arbol(tmp_path, [{"slug": "ausente", "rel_path": "05_CRM/99_Otros/esc.pdf",
                              "metodo": "ocr", "estado": "ok", "sha256": sha}])
    e = artefacto.elegir(raiz, artefacto.cargar(raiz),
                         raw_rel="00_Input/05_CRM/99_Otros/esc.pdf", raw_sha256=sha,
                         sin_cobertura_ok=False)
    assert e.bloqueo != "" and "01_OCR" in e.bloqueo
    assert e.clase is artefacto.Clase.SIN_REPRESENTANTE


def test_el_SHA_del_crudo_se_CRUZA_con_la_cobertura(tmp_path):
    """La rev. 1 solo miraba que el fichero existiera: con el crudo sustituido, reportaba
    la clase y la calidad de los bytes viejos."""
    _crudo(tmp_path, "00_Input/05_CRM/01_Demanda/d.pdf", b"AHORA OTRO CONTENIDO")
    raiz = _arbol(tmp_path, [{"slug": "d", "rel_path": "05_CRM/01_Demanda/d.pdf",
                              "metodo": "pypdf", "estado": "ok", "sha256": "SHA_VIEJO"}])
    e = artefacto.elegir(raiz, artefacto.cargar(raiz),
                         raw_rel="00_Input/05_CRM/01_Demanda/d.pdf",
                         raw_sha256=hashlib.sha256(b"AHORA OTRO CONTENIDO").hexdigest(),
                         sin_cobertura_ok=False)
    assert e.bloqueo != ""
    assert "cobertura" in e.bloqueo.lower()


def test_sin_cobertura_bloquea_y_el_override_deja_constancia(tmp_path):
    sha = _crudo(tmp_path, "00_Input/05_CRM/01_Demanda/d.pdf")
    raiz = _arbol(tmp_path, [])
    cob = artefacto.cargar(raiz)
    e = artefacto.elegir(raiz, cob, raw_rel="00_Input/05_CRM/01_Demanda/d.pdf",
                         raw_sha256=sha, sin_cobertura_ok=False)
    assert e.bloqueo != ""
    e2 = artefacto.elegir(raiz, cob, raw_rel="00_Input/05_CRM/01_Demanda/d.pdf",
                          raw_sha256=sha, sin_cobertura_ok=True)
    assert e2.bloqueo == "" and e2.clase is artefacto.Clase.CRUDO
    assert any("override" in a.lower() for a in e2.avisos)


def test_sin_soporte_lo_representa_el_crudo_con_aviso(tmp_path):
    sha = _crudo(tmp_path, "00_Input/05_CRM/99_Otros/v.mkv", b"video")
    raiz = _arbol(tmp_path, [{"slug": "v", "rel_path": "05_CRM/99_Otros/v.mkv",
                              "metodo": "sin_soporte", "estado": "sin_soporte",
                              "sha256": sha}])
    e = artefacto.elegir(raiz, artefacto.cargar(raiz),
                         raw_rel="00_Input/05_CRM/99_Otros/v.mkv", raw_sha256=sha,
                         sin_cobertura_ok=False)
    assert e.clase is artefacto.Clase.CRUDO and e.bloqueo == ""
    assert any("sin_soporte" in a for a in e.avisos)


def test_vision_deja_MD_pero_no_PDF_de_custodia(tmp_path):
    sha = _crudo(tmp_path, "00_Input/05_CRM/99_Otros/f.pdf")
    raiz = _arbol(tmp_path, [{"slug": "f", "rel_path": "05_CRM/99_Otros/f.pdf",
                              "metodo": "vision", "estado": "ok", "sha256": sha,
                              "ocr": False}])
    e = artefacto.elegir(raiz, artefacto.cargar(raiz),
                         raw_rel="00_Input/05_CRM/99_Otros/f.pdf", raw_sha256=sha,
                         sin_cobertura_ok=False)
    assert e.clase is artefacto.Clase.CRUDO
    assert any("visi" in a.lower() for a in e.avisos)


def test_una_imagen_sin_texto_la_representa_el_original(tmp_path):
    """Una foto de algo, no de una página: el PDF no aporta nada (spec §2.4)."""
    sha = _crudo(tmp_path, "00_Input/01_Drive EV/foto.jpg", b"\xff\xd8jpeg")
    raiz = _arbol(tmp_path, [{"slug": "foto", "rel_path": "01_Drive EV/foto.jpg",
                              "metodo": "ocr", "estado": "empty", "sha256": sha}])
    e = artefacto.elegir(raiz, artefacto.cargar(raiz),
                         raw_rel="00_Input/01_Drive EV/foto.jpg", raw_sha256=sha,
                         sin_cobertura_ok=False)
    assert e.clase is artefacto.Clase.CRUDO and e.ext == "jpg"
    assert e.bloqueo == ""


def test_el_orden_de_los_estados_es_el_de_sala_de_maquina():
    """No se inventa un orden propio: `_peor_estado` del módulo usa este."""
    assert artefacto.ORDEN_ESTADO == ("empty", "sin_soporte", "low", "ok")


def test_un_metodo_desconocido_bloquea_en_vez_de_adivinar(tmp_path):
    sha = _crudo(tmp_path, "00_Input/05_CRM/99_Otros/x.pdf")
    raiz = _arbol(tmp_path, [{"slug": "x", "rel_path": "05_CRM/99_Otros/x.pdf",
                              "metodo": "teletransporte", "estado": "ok",
                              "sha256": sha}])
    e = artefacto.elegir(raiz, artefacto.cargar(raiz),
                         raw_rel="00_Input/05_CRM/99_Otros/x.pdf", raw_sha256=sha,
                         sin_cobertura_ok=False)
    assert "teletransporte" in e.bloqueo


def test_una_cobertura_corrupta_LANZA_y_no_se_lee_como_vacia(tmp_path):
    (tmp_path / SM).mkdir(parents=True)
    (tmp_path / SM / "_cobertura.json").write_text("{{{", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        artefacto.cargar(tmp_path)


def test_una_cobertura_ausente_es_vacia_y_eso_NO_es_un_error(tmp_path):
    assert artefacto.cargar(tmp_path).por_sha == {}


def test_el_grupo_de_bundle_NO_depende_del_orden_de_las_filas(tmp_path):
    """La rev. 1 conservaba «la primera en caso de empate», así que invertir dos filas
    cambiaba la decisión."""
    sha = _crudo(tmp_path, "00_Input/05_CRM/99_Otros/b.pdf")
    filas = [
        {"slug": "b__1", "rel_path": "05_CRM/99_Otros/b.pdf", "metodo": "ocr",
         "estado": "low", "sha256": "S1", "parent_slug": "b", "parent_sha256": sha},
        {"slug": "b__2", "rel_path": "05_CRM/99_Otros/b.pdf", "metodo": "ocr",
         "estado": "ok", "sha256": "S2", "parent_slug": "b", "parent_sha256": sha},
    ]
    a = artefacto.cargar(_arbol(tmp_path, filas, ocr=["b"])).grupos[sha]
    b = artefacto.cargar(_arbol(tmp_path, list(reversed(filas)), ocr=["b"])).grupos[sha]
    assert a == b
    assert a.peor_estado == "low"
