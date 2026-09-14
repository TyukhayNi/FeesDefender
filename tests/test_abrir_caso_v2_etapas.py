"""Las tres etapas de V2, con sus efectos INYECTADOS.

Ninguna toca el CRM: cada etapa recibe su efecto por parametro, que es el mismo
patron de `etapa_sala_maquina(ident, *, correr=None)`.

Los dobles de aqui **validan lo que reciben**. R1 señalo que el de la rev. 1
admitia cualquier `**kw` y devolvia una cadena, con lo que ocultaba firma,
username y recibo: un doble que acepta todo no acredita nada.
"""

import dataclasses
import json

import pytest

import core.apertura_v1 as av1
import scripts.abrir_caso as ac
from scripts.abrir_caso import ResultadoAlta


class _Ident:
    case_id = "W-TEST01"
    w_code = "W-TEST01"
    direccion = "Calle Falsa 1"


@dataclasses.dataclass
class _ReciboFalso:
    """Espejo de `core.sudespacho_actuaciones.Recibo` para los dobles."""
    estado: str
    act_id: int | None = None
    paso: int = 6
    elemento: str = "extrajudiciales"
    exp_id: str = "644"
    motivo: str = ""


# --------------------------------------------------------------------------
# Etapa `crm_alta`
# --------------------------------------------------------------------------

def test_crm_alta_sin_autorizacion_no_llama_al_alta(tmp_path):
    def _explota():
        pytest.fail("con --crm skip no se puede tocar el CRM")

    res = ac.etapa_crm_alta(_Ident(), tmp_path, crm="skip", alta=_explota)

    assert res.estado == "saltada"
    assert [p.codigo for p in res.pendientes] == ["crm_no_autorizado"]


def test_crm_alta_creada_sale_hecha(tmp_path):
    res = ac.etapa_crm_alta(_Ident(), tmp_path, crm="api",
                            alta=lambda: ResultadoAlta("creado", "644", ""))

    assert res.estado == "hecha"
    assert "644" in res.detalle


def test_crm_alta_ya_vinculado_sale_saltada(tmp_path):
    res = ac.etapa_crm_alta(_Ident(), tmp_path, crm="api",
                            alta=lambda: ResultadoAlta("ya_vinculado", "640", ""))

    assert res.estado == "saltada"


def test_crm_alta_fallo_de_post_no_dice_vinculado(tmp_path):
    res = ac.etapa_crm_alta(_Ident(), tmp_path, crm="api",
                            alta=lambda: ResultadoAlta("fallo_post", None, "timeout"))

    assert res.estado == "fallo"
    assert "vinculado" not in res.detalle.lower()


def test_crm_alta_post_ok_sin_registro_local_conserva_el_id(tmp_path):
    # El caso del §5.2: hay un expediente CREADO que nadie vinculo. Perder su id
    # obligaria a buscarlo a mano en el CRM.
    res = ac.etapa_crm_alta(_Ident(), tmp_path, crm="api",
                            alta=lambda: ResultadoAlta("fallo_registro", "645", "disco"))

    assert res.estado == "fallo"
    assert "645" in res.detalle


# --------------------------------------------------------------------------
# Etapa `actuacion`
# --------------------------------------------------------------------------

def test_actuacion_sin_firmante_declara_pendiente(tmp_path):
    # El prefijo del asunto ES la tarifa (SENIOR 103 €/h, ABOGADO 77 €/h) y quien
    # firma no es quien opera. No se infiere JAMAS del actor de la UI.
    res = ac.etapa_actuacion(_Ident(), tmp_path, crm="api", firmante="")

    assert res.estado == "saltada"
    assert [p.codigo for p in res.pendientes] == ["actuacion_sin_firmante"]


def test_actuacion_sin_autorizacion_no_llama(tmp_path):
    def _explota(**_kw):
        pytest.fail("con --crm skip no se puede tocar el CRM")

    res = ac.etapa_actuacion(_Ident(), tmp_path, crm="skip",
                             firmante="Nikolai_Tyukhay", alta=_explota)

    assert res.estado == "saltada"
    assert [p.codigo for p in res.pendientes] == ["crm_no_autorizado"]


def test_relanzar_NO_crea_una_segunda_actuacion(tmp_path):
    # R1/H-03, reproducido por el revisor: sin `desde`, dos corridas dan 900 y 901.
    creadas = []

    def _alta(**kw):
        assert " " not in kw["firmante"], "al CRM va el username, no el nombre"
        if kw.get("desde") is None:
            creadas.append(900 + len(creadas))
        return _ReciboFalso("verificada", act_id=creadas[-1])

    ac.etapa_actuacion(_Ident(), tmp_path, crm="api",
                       firmante="Nikolai_Tyukhay", alta=_alta)
    ac.etapa_actuacion(_Ident(), tmp_path, crm="api",
                       firmante="Nikolai_Tyukhay", alta=_alta)

    assert creadas == [900], "la segunda corrida creo otra actuacion"


def test_un_recibo_incierto_NO_es_hecha(tmp_path):
    # `incierta` significa que no se sabe si el efecto ocurrio. Declararlo `hecha`
    # es exactamente la mentira que el §5.2 existe para impedir.
    res = ac.etapa_actuacion(_Ident(), tmp_path, crm="api", firmante="Nikolai_Tyukhay",
                             alta=lambda **kw: _ReciboFalso("incierta", act_id=None))

    assert res.estado == "fallo"
    assert [p.codigo for p in res.pendientes] == ["actuacion_incierta"]


def test_un_recibo_incompleto_se_reanuda_con_desde(tmp_path):
    vistos = []

    def _alta(**kw):
        vistos.append(kw.get("desde"))
        estado = "incompleta" if len(vistos) == 1 else "verificada"
        return _ReciboFalso(estado, act_id=910)

    ac.etapa_actuacion(_Ident(), tmp_path, crm="api",
                       firmante="Nikolai_Tyukhay", alta=_alta)
    ac.etapa_actuacion(_Ident(), tmp_path, crm="api",
                       firmante="Nikolai_Tyukhay", alta=_alta)

    assert vistos[0] is None
    assert vistos[1] is not None, "la reanudacion no paso `desde`"


def test_el_recibo_se_PERSISTE(tmp_path):
    # Un `Recibo` en memoria muere con el proceso, que es justo el caso que el §5.2
    # describe. Sin persistir no hay reentrada.
    ac.etapa_actuacion(_Ident(), tmp_path, crm="api", firmante="Nikolai_Tyukhay",
                       alta=lambda **kw: _ReciboFalso("verificada", act_id=911))

    guardado = json.loads(ac._recibo_path(tmp_path).read_text(encoding="utf-8"))
    assert guardado["act_id"] == 911


# --------------------------------------------------------------------------
# Etapa `verificar`
# --------------------------------------------------------------------------

class _InformeFalso:
    def __init__(self, filas):
        self.resultados = [
            _ResFalso(i, estado, detalle) for i, estado, detalle in filas]


@dataclasses.dataclass
class _ResFalso:
    id: str
    estado: str
    detalle: str = ""
    titulo: str = ""
    evidencia: tuple = ()


def test_un_fallo_de_V3_no_bloquea_V2(tmp_path):
    # Sala de lectura a medio montar: es V3. Visible como pendiente, nunca como
    # fallo de V2 (R1/H-07).
    informe = _InformeFalso([("artefactos_sala", "fallo", "faltan 4 de 4"),
                             ("cuantia_coherente", "ok", "")])

    res = ac.etapa_verificar(_Ident(), tmp_path, verificar=lambda _cd: informe)

    assert res.estado == "hecha"
    assert "verificacion:artefactos_sala" in [p.codigo for p in res.pendientes]


def test_un_fallo_de_V2_si_bloquea(tmp_path):
    informe = _InformeFalso([("cuantia_coherente", "fallo", "la cuantia no cuadra")])

    res = ac.etapa_verificar(_Ident(), tmp_path, verificar=lambda _cd: informe)

    assert res.estado == "fallo"


def test_sin_implementar_no_pasa_por_comprobacion_hecha(tmp_path):
    # Cuarto estado, que la rev. 1 del plan ignoraba. Ruta real: falta `openpyxl`.
    informe = _InformeFalso([("viabilidad_completa", "sin_implementar", "sin openpyxl")])

    res = ac.etapa_verificar(_Ident(), tmp_path, verificar=lambda _cd: informe)

    assert [p.codigo for p in res.pendientes] == ["verificacion:viabilidad_completa"]


def test_las_comprobaciones_de_v2_existen_de_verdad():
    # Si un nombre no existiera, el conjunto quedaria vacio y NINGUN fallo
    # bloquearia nunca. Es el mutante que la Task 0 del plan vino a evitar.
    from core import verificar_apertura as va

    assert ac.COMPROBACIONES_DE_V2 <= set(va.IMPLEMENTADAS)
    assert ac.COMPROBACIONES_DE_V2, "un conjunto vacio no bloquea nada"


def test_la_secuencia_v2_tiene_las_etapas_en_orden(tmp_path):
    etapas = ac._etapas_v2(_Ident(), tmp_path, folder_id="X", team_id="1", crm="skip")

    assert tuple(e.nombre for e in etapas) == ac.ETAPAS_V2
