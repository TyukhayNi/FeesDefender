"""`MEJORAS #209` — crear una actuación en el CRM deja de reescribirse a mano contra la prosa.

La receta está medida y verificada de punta a punta (`INTEGRACION_SUDESPACHO.md §15.6`,
2026-09-10, W-02VEKE): seis pasos, ninguno opcional. La frontera que el propio `#209` enuncia:
*el contrato del CRM se documenta y no se encapsula*, así que cada operación nueva se reescribe.

**Ningún test de aquí llama al CRM.** El cliente HTTP se inyecta.

Diseño: `docs/superpowers/specs/2026-09-14-p6-ficha-crm-y-actuaciones-design.md` §4.
"""
from __future__ import annotations

import json

import pytest

from core import sudespacho_actuaciones as act


# ---------------------------------------------------------------------------
# Dobles del transporte: un cliente que responde lo que se le diga
# ---------------------------------------------------------------------------


class _Resp:
    def __init__(self, status=200, payload=None, text=""):
        self.status_code = status
        self._payload = payload if payload is not None else {}
        self.text = text or json.dumps(self._payload)

    def json(self):
        return self._payload


class _Cliente:
    """Registra cada petición y devuelve las respuestas programadas, en orden."""

    def __init__(self, gets=(), posts=()):
        self.gets = list(gets)
        self.posts = list(posts)
        self.peticiones: list[tuple[str, str]] = []

    def get(self, url, **kw):
        self.peticiones.append(("GET", url))
        r = self.gets.pop(0) if self.gets else _Resp(200, {"items": []})
        if isinstance(r, Exception):
            raise r
        return r

    def post(self, url, **kw):
        self.peticiones.append(("POST", url))
        r = self.posts.pop(0) if self.posts else _Resp(201, {"id": 1})
        if isinstance(r, Exception):
            raise r
        return r


def _fila(**props):
    return {"id": "1", "values": [{"property": {"name": k}, "value": v}
                                  for k, v in props.items()]}


# ---------------------------------------------------------------------------
# Paso 1 — CUATRO salidas, no dos
# ---------------------------------------------------------------------------


def test_aprende_el_id_de_una_instancia_real():
    c = _Cliente(gets=[_Resp(200, {"items": [_fila(Subject="TA - CONTROL DICTADO SENTENCIA",
                                                   id_predefinido=84)]})])
    r = act.aprender_id_predefinido("TA - CONTROL DICTADO SENTENCIA", client=c)
    assert (r.estado, r.valor) == ("aprendido", 84)


def test_filas_con_el_campo_vacio_significan_que_NO_nace_de_plantilla():
    """`[APER-72]` lo midió sobre 20 actuaciones reales: el campo viene VACÍO en todas.

    Esas actuaciones no nacen de plantilla, así que el campo **se omite en el POST**.
    Buscarlo y no encontrarlo es el resultado correcto, no un fallo de la consulta: el paso 1
    sirve para no inventar el entero, no para exigir que exista.
    """
    c = _Cliente(gets=[_Resp(200, {"items": [
        _fila(Subject="SENIOR - EXTRAJUDICIAL - REVISION VIABILIDAD", id_predefinido=""),
        _fila(Subject="SENIOR - EXTRAJUDICIAL - REVISION VIABILIDAD"),
    ]})])
    r = act.aprender_id_predefinido("SENIOR - EXTRAJUDICIAL - REVISION VIABILIDAD", client=c)
    assert r.estado == "no_aplica" and r.valor is None


def test_cero_filas_no_es_lo_mismo_que_filas_sin_campo():
    """Sin instancias que mirar no se ha aprendido nada — y tampoco se ha refutado nada."""
    c = _Cliente(gets=[_Resp(200, {"items": []})])
    r = act.aprender_id_predefinido("ASUNTO QUE NO EXISTE", client=c)
    assert r.estado == "sin_filas" and r.valor is None


def test_una_consulta_fallida_no_es_ausencia():
    """La cuarta salida, y la que más cuesta cuando falta: «no pude mirar»."""
    c = _Cliente(gets=[_Resp(500, {}, text="boom")])
    r = act.aprender_id_predefinido("X", client=c)
    assert r.estado == "sin_comprobar" and r.valor is None


def test_una_excepcion_de_red_tampoco_es_ausencia():
    c = _Cliente(gets=[RuntimeError("red caída")])
    r = act.aprender_id_predefinido("X", client=c)
    assert r.estado == "sin_comprobar"


# ---------------------------------------------------------------------------
# Paso 3 — el destino se acredita ANTES de escribir (R1/H-06)
# ---------------------------------------------------------------------------


def test_un_expediente_de_OTRO_caso_con_el_mismo_numero_no_se_acredita():
    """**Cada elemento numera aparte.** En W-02VEKE, `464` es de `extrajudiciales` y `540` de
    `expedientes_judiciales`, y `GET expedientes_judiciales/464` devuelve un expediente de
    **otro caso**, con 200 y todo.

    Y la verificación del paso 6 no lo caza, porque usa la misma dirección que la escritura:
    verificar la llegada no verifica la intención.
    """
    c = _Cliente(gets=[_Resp(200, {"items": [_fila(referencia_cliente="OTRO (W-0XXXXX) - x")]})])
    with pytest.raises(act.DestinoNoAcreditado):
        act.resolver_destino("expedientes_judiciales", "464",
                             "BaRS10 - Calle (W-02VEKE) - Negativa", client=c)


def test_el_destino_correcto_se_acredita_con_su_evidencia():
    c = _Cliente(gets=[_Resp(200, {"items": [
        _fila(referencia_cliente="BaRS10 - Calle (W-02VEKE) - Negativa")]})])
    d = act.resolver_destino("expedientes_judiciales", "540",
                             "BaRS10 - Calle (W-02VEKE) - Negativa", client=c)
    assert d.exp_id == "540" and "W-02VEKE" in d.evidencia


def test_un_destino_que_no_se_puede_leer_tampoco_se_acredita():
    """«No pude comprobar el destino» no autoriza a escribir en él."""
    c = _Cliente(gets=[_Resp(500, {})])
    with pytest.raises(act.DestinoNoAcreditado):
        act.resolver_destino("extrajudiciales", "464", "BaRS10 (W-02VEKE)", client=c)


def test_acreditar_el_destino_no_escribe_nada():
    c = _Cliente(gets=[_Resp(200, {"items": [_fila(Referencia_Cliente="X (W-02VEKE)")]})])
    act.resolver_destino("extrajudiciales", "464", "X (W-02VEKE)", client=c)
    assert all(m == "GET" for m, _ in c.peticiones), c.peticiones


# ---------------------------------------------------------------------------
# Pasos 4-6 — el recibo reanudable (R1/H-04)
# ---------------------------------------------------------------------------


_DESTINO = ("extrajudiciales", "464", "BaRS10 (W-02VEKE)")


def _gets_destino_ok(*resto):
    """Los GET que `alta_actuacion` hace ANTES de los que le pase cada test.

    Son dos y el orden importa: el del paso 3 (acreditar el destino) y el del paso 1
    (aprender el `id_predefinido`). Contar solo el primero hacía que el GET de la
    verificación del paso 6 se comiera la respuesta del paso 1 — y con eso
    `test_no_declara_exito_sin_la_verificacion_del_paso_6` pasaba por la razón equivocada.
    """
    return [
        _Resp(200, {"items": [_fila(Referencia_Cliente="BaRS10 (W-02VEKE)")]}),  # paso 3
        _Resp(200, {"items": []}),                                               # paso 1
        *resto,
    ]


def _gets_reanudando(*resto):
    """Al reanudar **no** se llama al paso 1: el id ya existe y no se aprende nada."""
    return [_Resp(200, {"items": [_fila(Referencia_Cliente="BaRS10 (W-02VEKE)")]}), *resto]


def test_si_el_vinculo_falla_el_recibo_conserva_el_id_creado():
    """**Una verificación negativa NO es ausencia de escritura.**

    Sin el id en el recibo, el reintento repite el alta entera: el POST nuevo crea M, M se
    vincula, y N queda huérfana en el CRM sin que nadie lo sepa.
    """
    c = _Cliente(
        gets=_gets_destino_ok(_Resp(200, {"items": []})),
        posts=[_Resp(201, {"id": "N"}), _Resp(500, {}, text="no vinculó")],
    )
    r = act.alta_actuacion(*_DESTINO, asunto="X", firmante="Nikolai_Tyukhay", client=c)
    assert r.estado == "incompleta"
    assert r.act_id == "N"
    assert r.paso == 4


def test_reanudar_desde_el_recibo_no_crea_otra_actuacion():
    c1 = _Cliente(gets=_gets_destino_ok(), posts=[_Resp(201, {"id": "N"}), _Resp(500, {})])
    r1 = act.alta_actuacion(*_DESTINO, asunto="X", firmante="Nikolai_Tyukhay", client=c1)

    c2 = _Cliente(
        gets=_gets_reanudando(_Resp(200, {"items": [{"id": "N"}]})),
        posts=[_Resp(201, {})],
    )
    r2 = act.alta_actuacion(*_DESTINO, asunto="X", firmante="Nikolai_Tyukhay",
                            desde=r1, client=c2)

    assert r2.estado == "verificada"
    assert sum(1 for m, u in c2.peticiones if m == "POST" and "element_register" in u) == 0, (
        "creó otra actuación al reanudar")


def test_un_post_sin_recibo_deja_el_estado_INCIERTO():
    """Un timeout durante el POST deja hasta el id en duda: no se reintenta a ciegas."""
    c = _Cliente(gets=_gets_destino_ok(), posts=[RuntimeError("timeout")])
    r = act.alta_actuacion(*_DESTINO, asunto="X", firmante="Nikolai_Tyukhay", client=c)
    assert r.estado == "incierta" and r.act_id is None


def test_no_declara_exito_sin_la_verificacion_del_paso_6():
    """El POST del paso 5 devuelve 201 igual aunque la actuación quede huérfana.

    Y un `GET` por id de la actuación devuelve **404 aunque exista**: la única comprobación
    que prueba algo es releer del lado del expediente.
    """
    c = _Cliente(
        gets=_gets_destino_ok(_Resp(200, {"items": []})),   # no aparece del lado del exp.
        posts=[_Resp(201, {"id": "N"}), _Resp(201, {})],
    )
    r = act.alta_actuacion(*_DESTINO, asunto="X", firmante="Nikolai_Tyukhay", client=c)
    assert r.estado != "verificada"
    assert r.act_id == "N"


def test_el_camino_feliz_verifica_del_lado_del_expediente():
    c = _Cliente(
        gets=_gets_destino_ok(_Resp(200, {"items": [{"id": "N"}]})),
        posts=[_Resp(201, {"id": "N"}), _Resp(201, {})],
    )
    r = act.alta_actuacion(*_DESTINO, asunto="X", firmante="Nikolai_Tyukhay", client=c)
    assert (r.estado, r.act_id, r.paso) == ("verificada", "N", 6)


def test_un_destino_no_acreditado_no_llega_a_crear_nada():
    c = _Cliente(gets=[_Resp(200, {"items": [_fila(Referencia_Cliente="OTRO (W-0XXXXX)")]})])
    with pytest.raises(act.DestinoNoAcreditado):
        act.alta_actuacion(*_DESTINO, asunto="X", firmante="Nikolai_Tyukhay", client=c)
    assert not [m for m, _ in c.peticiones if m == "POST"]


# ---------------------------------------------------------------------------
# El asunto canónico: el prefijo ES la tarifa ([APER-72], R1/H-05)
# ---------------------------------------------------------------------------


def test_el_asunto_exige_el_firmante():
    """`SENIOR - …` factura a 103,00 €/h y `ABOGADO - …` a 77,00, medido sobre 20 reales.

    Un defecto aquí **factura al cliente la tarifa de otro**, así que no hay defecto.
    """
    with pytest.raises(ValueError):
        act.asunto_canonico("EXTRAJUDICIAL - REVISION VIABILIDAD", firmante="")


def test_el_firmante_decide_el_prefijo_y_no_quien_opera():
    """Ana puede tramitar una revisión que firma Nikolai (R1/H-05): el actor de la UI
    identifica a quien opera, no a quien firma."""
    a = act.asunto_canonico("EXTRAJUDICIAL - REVISION VIABILIDAD", firmante="Nikolai_Tyukhay")
    assert a.startswith("SENIOR - ")
    assert a.endswith("EXTRAJUDICIAL - REVISION VIABILIDAD")


def test_un_firmante_desconocido_no_elige_tarifa_por_su_cuenta():
    with pytest.raises(ValueError):
        act.asunto_canonico("EXTRAJUDICIAL - REVISION VIABILIDAD", firmante="quien.sea")


def test_un_asunto_que_ya_trae_prefijo_no_se_prefija_dos_veces():
    a = act.asunto_canonico("SENIOR - EXTRAJUDICIAL - REVISION VIABILIDAD",
                            firmante="Nikolai_Tyukhay")
    assert a.count("SENIOR - ") == 1


def test_un_asunto_con_el_prefijo_de_OTRO_se_rechaza():
    """Copiar el prefijo equivocado es el defecto que `[APER-72]` midió. No se corrige en
    silencio: se para, porque quien lo escribió puede tener razón y el firmante estar mal."""
    with pytest.raises(ValueError):
        act.asunto_canonico("ABOGADO - EXTRAJUDICIAL - REVISION VIABILIDAD",
                            firmante="Nikolai_Tyukhay")


# ---------------------------------------------------------------------------
# La duración: qué fichero y qué ventana (R1/H-07)
# ---------------------------------------------------------------------------


def _ronda(tmp_path, iniciada, terminada):
    from core import apertura_v1_estado as est
    d = tmp_path / "00_Input"
    d.mkdir(parents=True, exist_ok=True)
    payload = {"ronda_id": "r1", "iniciada": iniciada}
    if terminada:
        payload["terminada"] = terminada
    (d / "_apertura_v1.json").write_text(json.dumps(payload), encoding="utf-8")
    assert est.leer(tmp_path) is not None, "el fichero no es el que lee el core"
    return tmp_path


def test_la_duracion_sale_de_la_ronda_v1(tmp_path):
    """El fichero es `_apertura_v1.json`, **no `estado.json`** — ese nombre venía del handoff
    y no existe en el árbol."""
    d = _ronda(tmp_path, "2026-09-14T10:00:00Z", "2026-09-14T10:01:30Z")
    assert act.duracion_desde_ronda(d) == 90


def test_una_ronda_sin_cerrar_dice_None_y_no_supone_cero(tmp_path):
    d = _ronda(tmp_path, "2026-09-14T10:00:00Z", None)
    assert act.duracion_desde_ronda(d) is None


def test_sin_ronda_tampoco_se_inventa(tmp_path):
    assert act.duracion_desde_ronda(tmp_path) is None


def test_extremos_invertidos_se_rechazan(tmp_path):
    """Una resta que sale negativa no es una duración: es un dato roto."""
    d = _ronda(tmp_path, "2026-09-14T10:01:30Z", "2026-09-14T10:00:00Z")
    with pytest.raises(ValueError):
        act.duracion_desde_ronda(d)


def test_una_fecha_ilegible_se_rechaza_en_vez_de_valer_cero(tmp_path):
    d = _ronda(tmp_path, "ayer por la tarde", "2026-09-14T10:00:00Z")
    with pytest.raises(ValueError):
        act.duracion_desde_ronda(d)
