"""El informe: lo que el letrado ve. Y la garantía de que 4a no escribe."""
import hashlib
import json

import pytest

from core.ocurrencias_crm import RegistroOcurrencias
from core.procedimiento import artefacto, borrador, mapa, universo, vista

CARP = "05_Otros escritos"
SM = "01_Procesado/02_Sala de máquina"


@pytest.fixture()
def caso(tmp_path):
    cuerpo = b"%PDF-1.4 decreto"
    sha = hashlib.sha256(cuerpo).hexdigest()
    (tmp_path / "00_Input/05_CRM/99_Otros").mkdir(parents=True)
    (tmp_path / "00_Input/05_CRM/99_Otros/decreto.pdf").write_bytes(cuerpo)
    (tmp_path / SM).mkdir(parents=True)
    (tmp_path / SM / "_cobertura.json").write_text(json.dumps(
        [{"slug": "decreto", "rel_path": "05_CRM/99_Otros/decreto.pdf",
          "metodo": "pypdf", "estado": "ok", "sha256": sha}]), encoding="utf-8")
    (tmp_path / "05_Procedimiento").mkdir(parents=True)
    (tmp_path / "05_Procedimiento" / mapa.MAPA_FILENAME).write_text(
        "version: 1\nexpediente_crm: '540'\ncarpetas:\n"
        f'  "{CARP}":\n'
        "    - {origen: crm, doc_id: '1', orden: '00', descripcion: decreto_admision}\n",
        encoding="utf-8")
    return tmp_path, sha


def _conjuntos(sha, extra=None):
    reg = RegistroOcurrencias.__new__(RegistroOcurrencias)
    reg.ocurrencias = {"crm:540:1": {
        "source": "crm", "expediente_id": "540", "doc_id": "1",
        "revisiones": [{"estado": "materializada", "filename": "decreto.pdf",
                        "modified_at": "2026-01-01T00:00:00+01:00", "id_carpeta": "306",
                        "path": "05_CRM/99_Otros/decreto.pdf", "sha256": sha}]}}
    if extra:
        reg.ocurrencias.update(extra)
    return universo.leer("CASO", "540", registro=reg,
                         pull_state={"documents_total_crm": len(reg.ocurrencias),
                                     "doc_ids": ["1"]})


def _mapa_con(raiz, cuerpo: str):
    (raiz / "05_Procedimiento" / mapa.MAPA_FILENAME).write_text(
        "version: 1\nexpediente_crm: '540'\ncarpetas:\n"
        f'  "{CARP}":\n{cuerpo}', encoding="utf-8")
    return mapa.cargar(raiz)


def test_el_informe_dice_donde_va_cada_documento(caso):
    raiz, sha = caso
    inf = vista.construir(raiz, "CASO", "540", m=mapa.cargar(raiz),
                            c=_conjuntos(sha), cob=artefacto.cargar(raiz))
    assert inf.bloqueos == ()
    assert inf.completo is True
    (fila,) = inf.filas
    assert fila.carpeta == CARP
    assert fila.destino == "00_decreto_admision.pdf"
    assert fila.clase == artefacto.Clase.CRUDO
    assert fila.calidad == "ok"
    assert inf.por_carpeta[CARP][0] is fila


def test_construir_el_informe_NO_escribe_NADA(caso):
    """La garantía de esta mitad, comprobada por censo del árbol y no por promesa."""
    raiz, sha = caso

    def censo():
        return {str(p.relative_to(raiz)): (p.stat().st_mtime_ns, p.stat().st_size)
                for p in raiz.rglob("*") if p.is_file()}

    antes = censo()
    vista.construir(raiz, "CASO", "540", m=mapa.cargar(raiz), c=_conjuntos(sha),
                      cob=artefacto.cargar(raiz))
    assert censo() == antes, "el informe tocó el árbol del caso"


def test_lo_no_asignado_se_mide_contra_el_UNIVERSO_no_contra_lo_bajado(caso):
    """I4 aplicado al informe: un documento que el CRM enumera y el caso no bajó **sale
    en `sin_asignar`**, no desaparece. La rev. 1 lo calculaba sobre `materializadas` y
    los ocultaba."""
    raiz, sha = caso
    extra = {"crm:540:9": {
        "source": "crm", "expediente_id": "540", "doc_id": "9",
        "revisiones": [{"estado": "listada", "filename": "otro.pdf",
                        "modified_at": "2026-02-01T00:00:00+01:00", "id_carpeta": "306",
                        "path": None, "sha256": None}]}}
    inf = vista.construir(raiz, "CASO", "540", m=mapa.cargar(raiz),
                            c=_conjuntos(sha, extra), cob=artefacto.cargar(raiz))
    assert "9" in inf.solo_listadas
    assert any(x.startswith("9 ") for x in inf.sin_asignar)
    assert any("no descargado" in x for x in inf.sin_asignar)
    assert inf.completo is False, "un documento sin asignar no puede dar «completo»"


def test_un_documento_del_mapa_que_esta_solo_LISTADO_bloquea_con_su_remedio(caso):
    raiz, sha = caso
    m = _mapa_con(raiz, "    - {origen: crm, doc_id: '9', orden: '00', descripcion: otro}\n")
    extra = {"crm:540:9": {
        "source": "crm", "expediente_id": "540", "doc_id": "9",
        "revisiones": [{"estado": "listada", "filename": "otro.pdf",
                        "modified_at": "x", "id_carpeta": "306",
                        "path": None, "sha256": None}]}}
    inf = vista.construir(raiz, "CASO", "540", m=m, c=_conjuntos(sha, extra),
                            cob=artefacto.cargar(raiz))
    txt = "\n".join(inf.bloqueos)
    assert "listada" in txt and "--full" in txt


def test_el_eco_saca_un_docid_de_lo_no_asignado(caso):
    raiz, sha = caso
    (raiz / "05_Procedimiento" / CARP).mkdir(parents=True)
    (raiz / "05_Procedimiento" / CARP / "DEMANDA.docx").write_bytes(b"propia")
    m = _mapa_con(raiz,
                  "    - {origen: despacho, fichero: DEMANDA.docx, eco_crm: '1'}\n")
    inf = vista.construir(raiz, "CASO", "540", m=m, c=_conjuntos(sha),
                            cob=artefacto.cargar(raiz))
    assert inf.sin_asignar == ()
    assert inf.bloqueos == ()
    assert inf.filas[0].origen == "despacho"


def test_un_eco_a_un_docid_INEXISTENTE_bloquea(caso):
    """La puerta 7-bis del spec, que la rev. 1 no tenía: un eco es una afirmación sobre
    el CRM y puede ser falsa, y una falsa ocultaba un documento real."""
    raiz, sha = caso
    (raiz / "05_Procedimiento" / CARP).mkdir(parents=True)
    (raiz / "05_Procedimiento" / CARP / "DEMANDA.docx").write_bytes(b"propia")
    m = _mapa_con(raiz,
                  "    - {origen: despacho, fichero: DEMANDA.docx, eco_crm: '404'}\n")
    inf = vista.construir(raiz, "CASO", "540", m=m, c=_conjuntos(sha),
                            cob=artefacto.cargar(raiz))
    assert any("404" in b for b in inf.bloqueos)


def test_un_despacho_que_no_esta_en_su_carpeta_bloquea(caso):
    raiz, sha = caso
    m = _mapa_con(raiz, "    - {origen: despacho, fichero: NO_ESTA.docx}\n")
    inf = vista.construir(raiz, "CASO", "540", m=m, c=_conjuntos(sha),
                            cob=artefacto.cargar(raiz))
    assert any("NO_ESTA.docx" in b for b in inf.bloqueos)


def test_un_mapa_de_OTRO_expediente_bloquea_y_no_construye_nada(caso):
    raiz, sha = caso
    inf = vista.construir(raiz, "CASO", "999", m=mapa.cargar(raiz), c=_conjuntos(sha),
                            cob=artefacto.cargar(raiz))
    assert inf.filas == ()
    assert any("540" in b and "999" in b for b in inf.bloqueos)


def test_el_borrador_propone_orden_y_descripcion_y_NUNCA_la_carpeta(caso):
    """Spec §0: la asignación es del letrado. El borrador le ahorra la mecánica —los 76
    `orden` y `descripción`— y le deja la decisión."""
    import yaml
    raiz, sha = caso
    d = yaml.safe_load(borrador.proponer(_conjuntos(sha)))
    assert d["version"] == 1 and d["expediente_crm"] == "540"
    assert d["carpetas"] == {}, "el borrador NO asigna carpetas"
    (prop,) = d["sin_asignar"]
    assert prop["doc_id"] == "1"
    assert prop["orden"] and prop["descripcion"]
    assert "decreto" in prop["descripcion"]
    assert prop["en_disco"] is True


def test_el_borrador_marca_lo_que_el_caso_NO_bajo(caso):
    raiz, sha = caso
    import yaml
    extra = {"crm:540:9": {
        "source": "crm", "expediente_id": "540", "doc_id": "9",
        "revisiones": [{"estado": "listada", "filename": "D 04 - Chat.pdf",
                        "modified_at": "x", "id_carpeta": "306",
                        "path": None, "sha256": None}]}}
    d = yaml.safe_load(borrador.proponer(_conjuntos(sha, extra)))
    por_id = {p["doc_id"]: p for p in d["sin_asignar"]}
    assert por_id["9"]["en_disco"] is False
    assert por_id["9"]["orden"] == "D-04", (
        "el numero de documento del nombre del CRM es la mejor propuesta de `orden`")
    assert por_id["9"]["descripcion"] == "chat"


def test_el_borrador_es_YAML_que_el_cargador_acepta_al_repartirlo(caso, tmp_path):
    """Un borrador que el propio cargador rechaza no sirve de nada. Se comprueba moviendo
    sus propuestas a una carpeta, que es lo que hará el letrado."""
    import yaml
    raiz, sha = caso
    d = yaml.safe_load(borrador.proponer(_conjuntos(sha)))
    d["carpetas"] = {CARP: [{"origen": "crm", "doc_id": p["doc_id"],
                             "orden": p["orden"], "descripcion": p["descripcion"]}
                            for p in d["sin_asignar"]]}
    d["sin_asignar"] = []
    destino = tmp_path / "otro"
    (destino / "05_Procedimiento").mkdir(parents=True)
    (destino / "05_Procedimiento" / mapa.MAPA_FILENAME).write_text(
        yaml.safe_dump(d, allow_unicode=True), encoding="utf-8")
    m = mapa.cargar(destino)
    assert len(m.entradas) == 1
    assert m.entradas[0].carpeta == CARP


def test_proponer_NO_escribe_nada(caso):
    raiz, sha = caso
    antes = {str(p.relative_to(raiz)) for p in raiz.rglob("*") if p.is_file()}
    borrador.proponer(_conjuntos(sha))
    assert {str(p.relative_to(raiz)) for p in raiz.rglob("*") if p.is_file()} == antes


# ---------------------------------------------------------------- R1/H-12
def test_completo_es_FALSO_si_el_universo_es_incoherente(caso):
    """El CLI podia imprimir «el pull_state dice 99 documentos y el registro enumera 1» y
    a la vez «completo: si», saliendo con 0. Una automatizacion lo habria tomado por
    completitud sin conocer los otros 98."""
    raiz, sha = caso
    c = _conjuntos(sha)
    inc = ("el `pull_state` dice 99 documentos en el CRM y el registro enumera 1",)
    inf = vista.construir(raiz, "CASO", "540", m=mapa.cargar(raiz), c=c,
                          cob=artefacto.cargar(raiz), incoherencias=inc)
    assert inf.sin_asignar == () and inf.bloqueos == ()
    assert inf.incoherencias == inc
    assert inf.completo is False, (
        "«todas las filas que conozco tienen carpeta» no es «conozco todo lo que hay»")


def test_completo_sigue_siendo_cierto_sin_incoherencias(caso):
    """El otro valor: la puerta nueva no puede dejar `completo` siempre en falso."""
    raiz, sha = caso
    inf = vista.construir(raiz, "CASO", "540", m=mapa.cargar(raiz), c=_conjuntos(sha),
                          cob=artefacto.cargar(raiz), incoherencias=())
    assert inf.completo is True
