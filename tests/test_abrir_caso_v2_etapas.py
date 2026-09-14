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


@pytest.fixture(autouse=True)
def con_expediente_vinculado(monkeypatch):
    """Por defecto el caso TIENE expediente CRM: es la precondicion de la actuacion.

    Los tests que prueban su ausencia la pisan con su propio `monkeypatch`.
    """
    monkeypatch.setattr(ac.case_locator, "read_case_meta",
                        lambda _cd: {"sudespacho_expedientes": [
                            {"element": "extrajudiciales", "id": "644"}]})


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


def test_el_camino_REAL_pasa_los_argumentos_obligatorios(tmp_path, monkeypatch):
    """El control que faltaba: sin este test, el camino sin doble no se ejercita.

    Todos los tests de arriba inyectan `alta=...`, asi que `alta_actuacion` nunca se
    llamaba de verdad. Con eso, faltarle `elemento`, `exp_id`, `referencia_esperada` y
    `asunto` —los cuatro obligatorios— pasaba inadvertido: es el «doble que tapa la
    condicion», y es el defecto que R1/H-03 ya habia señalado.
    """
    from core import sudespacho_actuaciones as sa

    vistos = {}

    def _espia(*args, **kw):
        vistos.update(kw)
        vistos["posicionales"] = args
        return _ReciboFalso("verificada", act_id=920)

    monkeypatch.setattr(sa, "alta_actuacion", _espia)
    monkeypatch.setattr(ac.case_locator, "read_case_meta",
                        lambda _cd: {"sudespacho_expedientes": [
                            {"element": "extrajudiciales", "id": "644"}]})

    res = ac.etapa_actuacion(_Ident(), tmp_path, crm="api", firmante="Nikolai_Tyukhay")

    assert res.estado == "hecha", res.detalle
    faltan = [k for k in ("elemento", "exp_id", "referencia_esperada", "asunto")
              if k not in vistos and len(vistos.get("posicionales", ())) < 3]
    assert not faltan, f"la llamada real no pasa: {faltan}"
    # El asunto lleva el PREFIJO DE TARIFA que corresponde a quien firma —`SENIOR` a
    # 103,00 €/h—, no el username. Lo pone `asunto_canonico`, no esta etapa.
    assert vistos.get("asunto", "").startswith("SENIOR - "), vistos.get("asunto")
    assert vistos["posicionales"] == ("extrajudiciales", "644", "W-TEST01")


def test_sin_expediente_vinculado_la_actuacion_declara_pendiente(tmp_path, monkeypatch):
    # No hay a que colgar la actuacion. Es un pendiente, no un fallo: el alta puede
    # venir en la misma corrida o en otra.
    monkeypatch.setattr(ac.case_locator, "read_case_meta",
                        lambda _cd: {"sudespacho_expedientes": []})

    res = ac.etapa_actuacion(_Ident(), tmp_path, crm="api", firmante="Nikolai_Tyukhay")

    assert res.estado == "saltada"
    assert [p.codigo for p in res.pendientes] == ["actuacion_sin_expediente"]


# --------------------------------------------------------------------------
# Ramas de error: las senalo `diff-cover` y son justo donde la etapa decide si
# un fallo se declara o se traga. La respuesta por defecto es escribir el test.
# --------------------------------------------------------------------------

def test_crm_alta_traduce_una_excepcion_a_fallo(tmp_path):
    def _explota():
        raise RuntimeError("el CRM se cayo")

    res = ac.etapa_crm_alta(_Ident(), tmp_path, crm="api", alta=_explota)

    assert res.estado == "fallo"
    assert "se cayo" in res.detalle


def test_actuacion_traduce_una_excepcion_a_fallo(tmp_path):
    def _explota(**_kw):
        raise RuntimeError("boom")

    res = ac.etapa_actuacion(_Ident(), tmp_path, crm="api",
                             firmante="Nikolai_Tyukhay", alta=_explota)

    assert res.estado == "fallo"
    assert "boom" in res.detalle


def test_verificar_traduce_una_excepcion_a_fallo(tmp_path):
    def _explota(_cd):
        raise RuntimeError("el verificador reviento")

    res = ac.etapa_verificar(_Ident(), tmp_path, verificar=_explota)

    assert res.estado == "fallo"
    assert "reviento" in res.detalle


def test_si_el_recibo_no_se_puede_guardar_se_DICE(tmp_path, monkeypatch):
    # El efecto remoto SI ocurrio; lo que falla es poder reanudarlo. Callarlo
    # dejaria creer que un relanzamiento es seguro, y crearia otra actuacion.
    def _no_escribe(*_a, **_k):
        raise OSError("disco lleno")

    monkeypatch.setattr(ac, "_guardar_recibo", _no_escribe)

    res = ac.etapa_actuacion(_Ident(), tmp_path, crm="api", firmante="Nikolai_Tyukhay",
                             alta=lambda **kw: _ReciboFalso("verificada", act_id=930))

    assert res.estado == "fallo"
    assert "930" in res.detalle and "crearia otra" in res.detalle


# **RETIRADO el 2026-09-14: afirmaba una propiedad EQUIVOCADA.** Decia que un recibo
# corrupto «se ignora» y la etapa sigue. La R2 de Codex (H-02) lo puso por su nombre:
# un JSON roto NO acredita que no hubiera escritura, asi que ignorarlo era dar permiso
# para crear una segunda actuacion. Su sustituto, con la propiedad correcta, es
# `test_r2_h02_un_recibo_ILEGIBLE_no_da_permiso_para_crear_otra`.


def test_el_firmante_sale_del_yaml_cuando_no_se_pasa(tmp_path):
    (tmp_path / "00_Input").mkdir(parents=True, exist_ok=True)
    (tmp_path / "00_Input" / "_ficha_crm.yaml").write_text(
        "firmante: Nikolai_Tyukhay\n", encoding="utf-8")
    vistos = {}

    ac.etapa_actuacion(_Ident(), tmp_path, crm="api",
                       alta=lambda **kw: vistos.update(kw) or _ReciboFalso("verificada", 932))

    assert vistos["firmante"] == "Nikolai_Tyukhay"


def test_sin_yaml_no_hay_firmante_y_se_declara(tmp_path):
    res = ac.etapa_actuacion(_Ident(), tmp_path, crm="api")

    assert res.estado == "saltada"
    assert [p.codigo for p in res.pendientes] == ["actuacion_sin_firmante"]


# **RETIRADO el 2026-09-14 por la misma razon que el anterior** (R2/H-06): daba por
# buena la confusion entre «no hay ficha» y «la ficha no se puede leer». Sustituto:
# `test_r2_h06_un_yaml_INVALIDO_no_se_confunde_con_uno_ausente`.


def test_verificar_por_el_camino_REAL_llama_al_verificador(tmp_path, monkeypatch):
    """El mismo control que hizo falta en `actuacion`: sin esto, `_verificar_real`
    no se ejercita nunca porque todos los tests inyectan `verificar=`."""
    from core import verificar_apertura as va

    llamadas = []
    monkeypatch.setattr(va, "verificar",
                        lambda cd, fuentes=None:
                        llamadas.append((cd, fuentes)) or _InformeFalso([]))

    res = ac.etapa_verificar(_Ident(), tmp_path, crm="api")

    assert [c for c, _ in llamadas] == [tmp_path]
    # La R2 critico con razon que este test, escrito para cerrar el patron del doble
    # que tapa, seguia tapando: probaba que se llama e impedia ver que se llamaba SIN
    # fuentes. Ahora tambien mira eso.
    assert llamadas[0][1] is not None, "se llamo sin fuentes: ver R2/H-01"
    assert res.estado == "hecha"


def test_si_no_se_puede_leer_el_caso_no_hay_destino(tmp_path, monkeypatch):
    # `read_case_meta` puede lanzar (caso a medio crear). Eso no es «hay expediente»:
    # es «no lo se», y la actuacion declara pendiente en vez de inventarse un destino.
    def _explota(_cd):
        raise OSError("_caso.md ilegible")

    monkeypatch.setattr(ac.case_locator, "read_case_meta", _explota)

    res = ac.etapa_actuacion(_Ident(), tmp_path, crm="api", firmante="Nikolai_Tyukhay")

    assert res.estado == "saltada"
    assert [p.codigo for p in res.pendientes] == ["actuacion_sin_expediente"]


# --------------------------------------------------------------------------
# R2: los siete hallazgos. Cada test nombra el suyo.
# --------------------------------------------------------------------------

def test_r2_h01_la_verificacion_decisoria_SALE_A_LA_RED(tmp_path, monkeypatch):
    """R2/H-01. `va.verificar(cd)` sin fuentes usa `SinRed`, y con eso **las cinco
    comprobaciones de red salen en `fallo`** — lo dice el comentario de la propia
    funcion. Como dos de las tres decisorias son de red, con `--crm api` la etapa
    daria `fallo` SIEMPRE y la secuencia acabaria `bloqueado` en toda corrida real.
    Ningun test lo veia porque todos doblaban el verificador.
    """
    from core import verificar_apertura as va

    vistas = []
    monkeypatch.setattr(va, "verificar",
                        lambda cd, fuentes=None: vistas.append(fuentes) or _InformeFalso([]))

    ac.etapa_verificar(_Ident(), tmp_path, crm="api")

    assert vistas and vistas[0] is not None, (
        "la comprobacion decisoria se hizo SIN fuentes: con SinRed las de red fallan "
        "siempre y el bloqueo no significa nada")


def test_r2_h01_sin_autorizacion_no_sale_a_la_red(tmp_path, monkeypatch):
    # Con `skip` no hay nada que consultar en el CRM, y salir a la red costaria
    # tiempo y podria renovar tokens sin motivo.
    from core import verificar_apertura as va

    vistas = []
    monkeypatch.setattr(va, "verificar",
                        lambda cd, fuentes=None: vistas.append(fuentes) or _InformeFalso([]))

    ac.etapa_verificar(_Ident(), tmp_path, crm="skip")

    assert vistas == [None]


def test_r2_h02_un_recibo_ILEGIBLE_no_da_permiso_para_crear_otra(tmp_path):
    """R2/H-02. `None` significaba «no hay» y tambien «no lo pude interpretar», y lo
    segundo NO acredita que no hubiera escritura: puede haber una actuacion creada
    cuyo recibo se corrompio. Es la misma frontera que P8 remedio esta manana.
    """
    ac._recibo_path(tmp_path).parent.mkdir(parents=True, exist_ok=True)
    ac._recibo_path(tmp_path).write_text('{"campo_que_no_existe": 1}', encoding="utf-8")

    def _no_debe_llamarse(**_kw):
        pytest.fail("un recibo ilegible NO puede autorizar una actuacion nueva")

    res = ac.etapa_actuacion(_Ident(), tmp_path, crm="api", firmante="Nikolai_Tyukhay",
                             alta=_no_debe_llamarse)

    assert res.estado == "fallo"
    assert [p.codigo for p in res.pendientes] == ["actuacion_recibo_ilegible"]


def test_r2_h04_un_recibo_de_OTRO_expediente_no_vale_de_atajo(tmp_path):
    """R2/H-04. El atajo de `verificada` no miraba a que expediente pertenecia: un
    recibo copiado de otro caso daba por hecha una actuacion que aqui no existe."""
    ac._recibo_path(tmp_path).parent.mkdir(parents=True, exist_ok=True)
    ac._guardar_recibo(tmp_path, _ReciboFalso("verificada", act_id=950, exp_id="999"))

    res = ac.etapa_actuacion(_Ident(), tmp_path, crm="api", firmante="Nikolai_Tyukhay",
                             alta=lambda **kw: _ReciboFalso("verificada", act_id=951))

    assert res.estado != "saltada", "un recibo de otro expediente no acredita nada aqui"


def test_r2_h06_un_yaml_INVALIDO_no_se_confunde_con_uno_ausente(tmp_path):
    """R2/H-06. Misma frontera que H-02: que la ficha exista y no se pueda leer NO es
    lo mismo que no tenerla. Alguien la escribio creyendo que servia."""
    (tmp_path / "00_Input").mkdir(parents=True, exist_ok=True)
    (tmp_path / "00_Input" / "_ficha_crm.yaml").write_text(
        "esto: [no es, yaml valido\n", encoding="utf-8")

    res = ac.etapa_actuacion(_Ident(), tmp_path, crm="api")

    assert res.estado == "fallo"
    assert [p.codigo for p in res.pendientes] == ["ficha_crm_ilegible"]


def test_r2_h07_el_guard_exige_las_TRES_no_un_subconjunto(tmp_path):
    """R2/H-07. Con `<=` el conjunto podia quedarse con una de tres y seguir verde:
    dos comprobaciones dejarian de bloquear sin que nadie se enterase."""
    from core import verificar_apertura as va

    assert ac.COMPROBACIONES_DE_V2 == frozenset(
        {"crm_ficha", "crm_actuacion", "cuantia_coherente"})
    assert ac.COMPROBACIONES_DE_V2 <= set(va.IMPLEMENTADAS)


def test_r2_h05_el_recibo_es_PROTOCOLO_no_un_documento_del_expediente(tmp_path):
    """R2/H-05. Sin declararlo, la sala de maquina lo inventariaba con hash y
    extension JSON como si fuera un documento del caso del cliente."""
    from core.intake_control import es_fichero_de_protocolo

    assert es_fichero_de_protocolo(ac._recibo_path(tmp_path).name)
