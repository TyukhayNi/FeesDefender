"""Tests del registro de ocurrencias del CRM (`core.ocurrencias_crm`).

Pieza 2 de la vista procesal (spec `2026-07-27-vista-procesal-05-procedimiento-design.md`
§2.1). Cubre los dos hallazgos que motivaron el registro:

- **H1** — el manifiesto de intake (indexado por SHA) **no puede representar** dos
  documentos distintos del CRM con el mismo contenido y la misma ruta. Ocurre en
  vivo: `TASA ORDINARIO` presentada dos veces (`doc_id` 39526 y 38060) comparte
  SHA y `primary_path`, así que no se crea alias y ningún ID queda persistido.
- **N2** — con intake acotado (`only_doc_ids`) la puerta de integridad es **vacua**
  si el registro se escribe en el mismo bucle que descarga: registro y
  `pull_state.doc_ids` cuadran aunque haya documentos del CRM invisibles. De ahí
  el estado `listada`, que se anota ANTES del filtro.
- **N1** — una clave lógica no puede guardar a la vez la revisión vigente y la
  anterior. De ahí las revisiones, con la última como activa.

Datos SIEMPRE sintéticos: el repo es público.
"""

from __future__ import annotations

import json

import pytest


@pytest.fixture
def oc(tmp_casos_root):
    from core import ocurrencias_crm as _oc
    return _oc


@pytest.fixture
def caso(tmp_casos_root):
    """Caso sintético con `00_Input/` creado."""
    d = tmp_casos_root / "CASO-OC"
    (d / "00_Input").mkdir(parents=True)
    return "CASO-OC"


# ---------------------------------------------------------------------------
# 1. Carga y contrato básico
# ---------------------------------------------------------------------------

def test_registro_inexistente_carga_vacio_sin_error(oc, caso):
    r = oc.RegistroOcurrencias(caso)
    r.load()
    assert r.ocurrencias == {}


def test_registrar_listada_deja_la_revision_sin_ruta_ni_sha(oc, caso):
    """Al listar solo hay metadatos del CRM: la ruta y el SHA llegan al bajar."""
    r = oc.RegistroOcurrencias(caso)
    r.load()
    r.registrar_listada(expediente_id="487", doc_id="36797",
                        filename="ORDINARIO.doc", modified_at="2025-12-03T09:38:03+01:00",
                        id_carpeta="307")
    rev = r.activa("487", "36797")
    assert rev["estado"] == oc.ESTADO_LISTADA
    assert rev["filename"] == "ORDINARIO.doc"
    assert rev["id_carpeta"] == "307"
    assert rev.get("path") is None and rev.get("sha256") is None


def test_registrar_materializada_completa_la_revision_activa(oc, caso):
    r = oc.RegistroOcurrencias(caso)
    r.load()
    r.registrar_listada(expediente_id="487", doc_id="36797", filename="ORDINARIO.doc",
                        modified_at="2025-12-03T09:38:03+01:00", id_carpeta="307")
    r.registrar_materializada(expediente_id="487", doc_id="36797",
                              path="05_CRM/01_Demanda/ordinario.doc", sha256="a" * 64)
    rev = r.activa("487", "36797")
    assert rev["estado"] == oc.ESTADO_MATERIALIZADA
    assert rev["path"] == "05_CRM/01_Demanda/ordinario.doc"
    assert rev["sha256"] == "a" * 64
    assert r.resolver("487", "36797") == ("a" * 64, "05_CRM/01_Demanda/ordinario.doc")


def test_resolver_devuelve_none_si_solo_esta_listada(oc, caso):
    """Listada != disponible en disco: la vista procesal no puede copiarla."""
    r = oc.RegistroOcurrencias(caso)
    r.load()
    r.registrar_listada(expediente_id="487", doc_id="41219", filename="JUSTIF.pdf",
                        modified_at=None, id_carpeta=None)
    assert r.resolver("487", "41219") is None


def test_round_trip_por_disco(oc, caso):
    r = oc.RegistroOcurrencias(caso)
    r.load()
    r.registrar_listada(expediente_id="487", doc_id="36797", filename="A.pdf",
                        modified_at="2025-12-03T09:38:03+01:00", id_carpeta="307")
    r.registrar_materializada(expediente_id="487", doc_id="36797",
                              path="05_CRM/01_Demanda/a.pdf", sha256="b" * 64)
    ruta = r.save()
    assert ruta.is_file()

    r2 = oc.RegistroOcurrencias(caso)
    r2.load()
    assert r2.resolver("487", "36797") == ("b" * 64, "05_CRM/01_Demanda/a.pdf")


# ---------------------------------------------------------------------------
# 2. H1 — dos doc_id con el mismo SHA y la misma ruta (la tasa del piloto)
# ---------------------------------------------------------------------------

def test_dos_doc_id_con_mismo_sha_y_misma_ruta_son_dos_ocurrencias(oc, caso):
    """El caso que el manifiesto de intake NO puede representar.

    `TASA ORDINARIO` presentada dos veces: mismo contenido, mismo fichero en
    disco, dos documentos distintos del pleito.
    """
    r = oc.RegistroOcurrencias(caso)
    r.load()
    for doc_id, lote in (("38060", "2026-02-11T12:37:11+01:00"),
                         ("39526", "2026-03-23T16:38:23+01:00")):
        r.registrar_listada(expediente_id="487", doc_id=doc_id,
                            filename="TASA ORDINARIO", modified_at=lote, id_carpeta="306")
        r.registrar_materializada(expediente_id="487", doc_id=doc_id,
                                  path="05_CRM/99_Otros/tasa_ordinario.pdf",
                                  sha256="c" * 64)

    assert len(r.materializadas("487")) == 2
    # Ambas resuelven al mismo fichero, y eso es legítimo.
    assert r.resolver("487", "38060") == r.resolver("487", "39526")
    # Y conservan su propia fecha de lote, que es lo que las distingue.
    assert r.activa("487", "38060")["modified_at"] != r.activa("487", "39526")["modified_at"]


# ---------------------------------------------------------------------------
# 3. Ámbito por expediente (un caso admite varios)
# ---------------------------------------------------------------------------

def test_dos_expedientes_del_mismo_caso_no_se_mezclan(oc, caso):
    r = oc.RegistroOcurrencias(caso)
    r.load()
    r.registrar_listada(expediente_id="487", doc_id="1", filename="a.pdf",
                        modified_at=None, id_carpeta=None)
    r.registrar_listada(expediente_id="649", doc_id="2", filename="b.pdf",
                        modified_at=None, id_carpeta=None)
    assert set(r.listadas("487")) == {"1"}
    assert set(r.listadas("649")) == {"2"}
    assert r.resolver("649", "1") is None


def test_mismo_doc_id_en_dos_expedientes_son_ocurrencias_distintas(oc, caso):
    r = oc.RegistroOcurrencias(caso)
    r.load()
    r.registrar_listada(expediente_id="487", doc_id="100", filename="del-487.pdf",
                        modified_at=None, id_carpeta=None)
    r.registrar_listada(expediente_id="649", doc_id="100", filename="del-649.pdf",
                        modified_at=None, id_carpeta=None)
    assert r.activa("487", "100")["filename"] == "del-487.pdf"
    assert r.activa("649", "100")["filename"] == "del-649.pdf"


# ---------------------------------------------------------------------------
# 4. N1 — revisiones: la anterior se conserva, no se sobrescribe
# ---------------------------------------------------------------------------

def test_relistar_con_la_misma_fecha_no_crea_revision(oc, caso):
    """Idempotencia: re-ejecutar el pull no debe inflar el histórico."""
    r = oc.RegistroOcurrencias(caso)
    r.load()
    for _ in range(3):
        r.registrar_listada(expediente_id="487", doc_id="36797", filename="A.pdf",
                            modified_at="2025-12-03T09:38:03+01:00", id_carpeta="307")
    assert len(r.revisiones("487", "36797")) == 1


def test_cambio_de_modified_at_crea_revision_y_la_anterior_queda_superseded(oc, caso):
    r = oc.RegistroOcurrencias(caso)
    r.load()
    r.registrar_listada(expediente_id="487", doc_id="36797", filename="A.pdf",
                        modified_at="2025-12-03T09:38:03+01:00", id_carpeta="307")
    r.registrar_materializada(expediente_id="487", doc_id="36797",
                              path="05_CRM/01_Demanda/a.pdf", sha256="d" * 64)
    r.registrar_listada(expediente_id="487", doc_id="36797", filename="A.pdf",
                        modified_at="2026-01-15T10:00:00+01:00", id_carpeta="307")

    revs = r.revisiones("487", "36797")
    assert len(revs) == 2
    assert revs[0]["estado"] == oc.ESTADO_SUPERSEDED     # la vieja, con su sha intacto
    assert revs[0]["sha256"] == "d" * 64
    assert r.activa("487", "36797")["modified_at"] == "2026-01-15T10:00:00+01:00"


def test_cambio_de_sha_sin_cambio_de_fecha_tambien_crea_revision(oc, caso):
    """El CRM puede reemplazar el contenido sin tocar la fecha."""
    r = oc.RegistroOcurrencias(caso)
    r.load()
    r.registrar_listada(expediente_id="487", doc_id="36797", filename="A.pdf",
                        modified_at="2025-12-03T09:38:03+01:00", id_carpeta="307")
    r.registrar_materializada(expediente_id="487", doc_id="36797",
                              path="05_CRM/01_Demanda/a.pdf", sha256="e" * 64)
    r.registrar_materializada(expediente_id="487", doc_id="36797",
                              path="05_CRM/01_Demanda/a.pdf", sha256="f" * 64)
    revs = r.revisiones("487", "36797")
    assert len(revs) == 2
    assert revs[0]["sha256"] == "e" * 64 and revs[0]["estado"] == oc.ESTADO_SUPERSEDED
    assert r.resolver("487", "36797") == ("f" * 64, "05_CRM/01_Demanda/a.pdf")


def test_re_materializar_con_el_mismo_sha_es_no_op(oc, caso):
    r = oc.RegistroOcurrencias(caso)
    r.load()
    r.registrar_listada(expediente_id="487", doc_id="1", filename="a.pdf",
                        modified_at=None, id_carpeta=None)
    for _ in range(3):
        r.registrar_materializada(expediente_id="487", doc_id="1",
                                  path="05_CRM/99_Otros/a.pdf", sha256="0" * 64)
    assert len(r.revisiones("487", "1")) == 1


# ---------------------------------------------------------------------------
# 5. N2 — listadas vs materializadas: lo que hace la puerta de integridad útil
# ---------------------------------------------------------------------------

def test_listadas_incluye_las_no_descargadas(oc, caso):
    """El intake acotado baja 2 de 3; la tercera SIGUE siendo visible."""
    r = oc.RegistroOcurrencias(caso)
    r.load()
    for doc_id in ("1", "2", "3"):
        r.registrar_listada(expediente_id="487", doc_id=doc_id, filename=f"{doc_id}.pdf",
                            modified_at=None, id_carpeta=None)
    for doc_id in ("1", "2"):
        r.registrar_materializada(expediente_id="487", doc_id=doc_id,
                                  path=f"05_CRM/99_Otros/{doc_id}.pdf", sha256=doc_id * 64)

    assert set(r.listadas("487")) == {"1", "2", "3"}
    assert set(r.materializadas("487")) == {"1", "2"}
    assert set(r.solo_listadas("487")) == {"3"}


def test_materializar_sin_listar_antes_es_error(oc, caso):
    """Invariante del contrato: nada se materializa sin haberse listado.

    Si el pull pudiera materializar sin listar, volvería el agujero de N2 por la
    puerta de atrás.
    """
    r = oc.RegistroOcurrencias(caso)
    r.load()
    with pytest.raises(oc.OcurrenciaDesconocidaError):
        r.registrar_materializada(expediente_id="487", doc_id="404",
                                  path="05_CRM/99_Otros/x.pdf", sha256="9" * 64)


# ---------------------------------------------------------------------------
# 6. Integridad de la carga: un error NUNCA se convierte en «cero documentos»
# ---------------------------------------------------------------------------

def _escribir_crudo(tmp_casos_root, texto: str) -> None:
    (tmp_casos_root / "CASO-OC" / "00_Input" / "_ocurrencias_crm.json").write_text(
        texto, encoding="utf-8")


def test_registro_corrupto_lanza_no_devuelve_vacio(oc, caso, tmp_casos_root):
    _escribir_crudo(tmp_casos_root, "{esto no es json")
    r = oc.RegistroOcurrencias(caso)
    with pytest.raises(oc.RegistroInvalidoError, match="ilegible"):
        r.load()


def test_version_desconocida_lanza(oc, caso, tmp_casos_root):
    _escribir_crudo(tmp_casos_root, json.dumps({"version": 99, "ocurrencias": {}}))
    r = oc.RegistroOcurrencias(caso)
    with pytest.raises(oc.RegistroInvalidoError, match="[Vv]ersi"):
        r.load()


def test_estructura_no_dict_lanza(oc, caso, tmp_casos_root):
    _escribir_crudo(tmp_casos_root, json.dumps([1, 2, 3]))
    r = oc.RegistroOcurrencias(caso)
    with pytest.raises(oc.RegistroInvalidoError):
        r.load()


def test_ocurrencia_sin_revisiones_lanza(oc, caso, tmp_casos_root):
    _escribir_crudo(tmp_casos_root, json.dumps({
        "version": 1,
        "ocurrencias": {"crm:487:1": {"source": "crm", "expediente_id": "487",
                                      "doc_id": "1", "revisiones": []}},
    }))
    r = oc.RegistroOcurrencias(caso)
    with pytest.raises(oc.RegistroInvalidoError, match="revisiones"):
        r.load()


def test_save_es_atomico_y_no_deja_temporales(oc, caso, tmp_casos_root):
    r = oc.RegistroOcurrencias(caso)
    r.load()
    r.registrar_listada(expediente_id="487", doc_id="1", filename="a.pdf",
                        modified_at=None, id_carpeta=None)
    r.save()
    r.save()
    entrada = tmp_casos_root / "CASO-OC" / "00_Input"
    assert [p.name for p in entrada.iterdir() if p.name.startswith("._")] == []
    # Y el resultado sigue siendo JSON válido y recargable.
    oc.RegistroOcurrencias(caso).load()
