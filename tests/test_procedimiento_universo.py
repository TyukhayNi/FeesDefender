"""I4: universo, materialización y descargas de la última corrida son TRES cosas."""
import pytest

from core.ocurrencias_crm import RegistroOcurrencias
from core.procedimiento import universo


def _registro(filas):
    """Doble del registro con `revisiones` reales, para no depender de su constructor."""
    reg = RegistroOcurrencias.__new__(RegistroOcurrencias)
    reg.ocurrencias = {
        f"crm:540:{d}": {"source": "crm", "expediente_id": "540", "doc_id": d,
                         "revisiones": [{"estado": estado, "filename": f"{d}.pdf",
                                         "modified_at": "2026-01-01T00:00:00+01:00",
                                         "id_carpeta": "307",
                                         "path": (f"05_CRM/99_Otros/{d}.pdf"
                                                  if estado == "materializada" else None),
                                         "sha256": (f"SHA{d}" if estado == "materializada"
                                                    else None)}]}
        for d, estado in filas.items()
    }
    return reg


def test_el_intake_ACOTADO_no_produce_ni_una_incoherencia():
    """**El defecto que mató la rev. 1.** 76 enumerados, 2 bajados: es el régimen normal
    del intake judicial acotado (spec §1.1), no un error. Una puerta que exija
    `listadas ⊆ descargadas` bloquearía los otros 74 y haría la pieza inservible en el
    expediente para el que se diseñó.
    """
    filas = {str(i): ("materializada" if i in (1, 2) else "listada")
             for i in range(1, 77)}
    c = universo.leer("CASO", "540", registro=_registro(filas),
                      pull_state={"documents_total_crm": 76, "doc_ids": ["1", "2"]})
    assert len(c.listadas) == 76
    assert len(c.materializadas) == 2
    assert c.descargadas == frozenset({"1", "2"})
    assert universo.incoherencias(c) == (), (
        f"el régimen acotado se reportó como incoherente: {universo.incoherencias(c)}")


def test_una_descargada_que_no_esta_en_el_universo_SI_es_incoherente():
    """Al revés sí es un problema: el pull dice haber bajado algo que el registro no
    enumera, así que uno de los dos está rancio."""
    c = universo.leer("CASO", "540", registro=_registro({"1": "materializada"}),
                      pull_state={"documents_total_crm": 1, "doc_ids": ["1", "99"]})
    assert any("99" in x for x in universo.incoherencias(c))


def test_una_descargada_sin_materializar_es_incoherente():
    """El pull dice que la bajó y el registro dice que no está en disco."""
    c = universo.leer("CASO", "540", registro=_registro({"1": "listada"}),
                      pull_state={"documents_total_crm": 1, "doc_ids": ["1"]})
    assert any("1" in x for x in universo.incoherencias(c))


def test_un_total_del_CRM_que_no_cuadra_con_el_universo_se_reporta():
    c = universo.leer("CASO", "540", registro=_registro({"1": "listada"}),
                      pull_state={"documents_total_crm": 9, "doc_ids": []})
    assert any("9" in x for x in universo.incoherencias(c))


def test_un_pull_state_AUSENTE_no_se_lee_como_cero_descargas():
    """`None` es «no lo sé», no «no bajó nada». Confundirlos haría que un caso sin
    `_caso.md` pareciera coherente."""
    c = universo.leer("CASO", "540", registro=_registro({"1": "materializada"}),
                      pull_state=None)
    assert c.descargadas is None
    assert c.total_crm is None
    assert any("pull_state" in x.lower() for x in universo.incoherencias(c))


def test_un_registro_AUSENTE_es_UniversoError_y_no_un_universo_vacio():
    """`RegistroOcurrencias.load()` devuelve vacío si el fichero no está —contrato
    legítimo para su productor— y la vista NO puede aceptarlo (spec §5.1): un universo
    vacío diría «este expediente no tiene documentos», que es indistinguible de
    «todavía no se ha hecho el pull».
    """
    reg = RegistroOcurrencias.__new__(RegistroOcurrencias)
    reg.ocurrencias = {}
    with pytest.raises(universo.UniversoError) as exc:
        universo.leer("CASO", "540", registro=reg,
                      pull_state={"documents_total_crm": 3, "doc_ids": []})
    assert "sync_sudespacho" in str(exc.value)


def test_ocurrencias_de_OTRO_expediente_no_se_mezclan():
    reg = _registro({"1": "materializada"})
    reg.ocurrencias["crm:999:7"] = {
        "source": "crm", "expediente_id": "999", "doc_id": "7",
        "revisiones": [{"estado": "materializada", "filename": "x.pdf",
                        "modified_at": "x", "id_carpeta": "1",
                        "path": "05_CRM/99_Otros/x.pdf", "sha256": "S"}]}
    c = universo.leer("CASO", "540", registro=reg,
                      pull_state={"documents_total_crm": 1, "doc_ids": ["1"]})
    assert set(c.listadas) == {"1"}


def test_solo_listadas_es_exactamente_la_diferencia():
    c = universo.leer("CASO", "540",
                      registro=_registro({"1": "materializada", "2": "listada",
                                          "3": "listada"}),
                      pull_state={"documents_total_crm": 3, "doc_ids": ["1"]})
    assert set(c.solo_listadas) == {"2", "3"}
    assert set(c.solo_listadas) == set(c.listadas) - set(c.materializadas)


def test_los_errores_del_ultimo_pull_se_reportan():
    """Un pull que dejó errores puede haber dejado el universo incompleto, y eso hay que
    verlo: la rev. 1 no consultaba `errors` en ningún sitio."""
    c = universo.leer("CASO", "540", registro=_registro({"1": "materializada"}),
                      pull_state={"documents_total_crm": 1, "doc_ids": ["1"],
                                  "errors": ["timeout en gdocu"]})
    assert any("timeout en gdocu" in x for x in universo.incoherencias(c))


# ------------------------------------------------------------- R1/H-06 y H-17

def test_leer_EXIGE_la_raiz_autorizada_y_no_vuelve_al_catalogo():
    """R1/H-06: sin raiz, `RegistroOcurrencias` y `read_pull_state` resuelven por
    `case_locator` contra CASOS_ROOT. Se autorizaba una raiz y se leia otra, asi que en un
    checkout con el mismo identificador la vista mezclaba lo local con el canon. Falla
    CERRADO: es mas facil olvidar pasarla que darse cuenta de que se leyo mal."""
    with pytest.raises(universo.UniversoError) as exc:
        universo.leer("CASO", "540")
    assert "raíz autorizada" in str(exc.value)


def test_leer_lee_el_registro_DE_LA_RAIZ_que_se_le_da(tmp_path):
    """La prueba de que la raiz manda: dos arboles con el mismo case_id y distinto
    contenido devuelven universos distintos."""
    import json
    for nombre, doc in (("local", "LOCAL"), ("canon", "CANON")):
        base = tmp_path / nombre / "00_Input"
        base.mkdir(parents=True)
        (base / "_ocurrencias_crm.json").write_text(json.dumps({
            "version": 1, "generado": "2026-09-09T00:00:00",
            "ocurrencias": {f"crm:540:{doc}": {
                "source": "crm", "expediente_id": "540", "doc_id": doc,
                "revisiones": [{"estado": "listada", "filename": "x.pdf",
                                "modified_at": "x", "id_carpeta": "1",
                                "path": None, "sha256": None,
                                "registrada_en": "2026-09-09T00:00:00"}]}}}),
            encoding="utf-8")
    a = universo.leer("CASO", "540", raiz=tmp_path / "local", pull_state=None)
    b = universo.leer("CASO", "540", raiz=tmp_path / "canon", pull_state=None)
    assert set(a.listadas) == {"LOCAL"}
    assert set(b.listadas) == {"CANON"}


def test_un_materializado_que_NO_esta_en_disco_se_reporta(tmp_path):
    """R1/H-17: `materializadas` filtra por ESTADO del registro y no hace I/O. Un crudo
    borrado deja el registro y D8 cuadrando entre si."""
    c = universo.leer("CASO", "540", raiz=tmp_path,
                      registro=_registro({"1": "materializada"}),
                      pull_state={"documents_total_crm": 1, "doc_ids": ["1"]})
    assert c.ausentes_verificado is True
    assert c.ausentes_en_disco == ("1",)
    assert any("raíz autorizada" in x for x in universo.incoherencias(c))


def test_un_materializado_que_SI_esta_en_disco_no_se_reporta(tmp_path):
    (tmp_path / "00_Input/05_CRM/99_Otros").mkdir(parents=True)
    (tmp_path / "00_Input/05_CRM/99_Otros/1.pdf").write_bytes(b"x")
    c = universo.leer("CASO", "540", raiz=tmp_path,
                      registro=_registro({"1": "materializada"}),
                      pull_state={"documents_total_crm": 1, "doc_ids": ["1"]})
    assert c.ausentes_en_disco == ()
    assert universo.incoherencias(c) == ()


def test_no_haber_mirado_el_disco_NO_es_una_incoherencia(tmp_path):
    """«No lo mire» es cobertura ausente, no un desacuerdo entre fuentes. Meterlo en
    `incoherencias` hacia falso el `completo` en cuanto alguien inyectaba los lectores,
    que es la senal de que estaba en el sitio equivocado."""
    c = universo.leer("CASO", "540", registro=_registro({"1": "materializada"}),
                      pull_state={"documents_total_crm": 1, "doc_ids": ["1"]})
    assert c.ausentes_verificado is False
    assert universo.incoherencias(c) == ()


def test_los_campos_de_RegistroOcurrencias_no_han_cambiado():
    """`_registro_bajo` construye el registro por `__new__` porque su `__init__` resuelve
    la ruta por el catalogo y lanza en un checkout. Eso obliga a fijar a mano los campos
    que el constructor pone, y este test ata esa lista: si `RegistroOcurrencias` gana uno,
    aqui sale rojo en vez de fabricarse un objeto a medias mas adelante."""
    import inspect

    import re

    fuente = inspect.getsource(RegistroOcurrencias.__init__)
    # `self.<campo>` seguido de `=` o de una anotacion `:`; un split a mano se queda los
    # dos puntos de `self.ocurrencias: dict[...] = {}`.
    puestos = set(re.findall(r"self\.(\w+)\s*[:=]", fuente))
    assert puestos == {"case_id", "path", "ocurrencias", "_dirty"}, (
        f"`RegistroOcurrencias.__init__` fija ahora {sorted(puestos)}: actualiza "
        f"`universo._registro_bajo`")
