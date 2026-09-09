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
