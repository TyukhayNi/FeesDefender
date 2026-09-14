"""Los hallazgos de la R2 sobre el diff de P6 — dos revisores independientes, los dos NO-SHIP.

Actas: `…-r2-adversarial-review.md` (Codex, 11 hallazgos) y `…-r2b-adversarial-review.md`
(subagente vía `superpowers:requesting-code-review`, 13). Coinciden en cinco.

**La frontera común, y es una sola:** *cada helper distingue estados que su único llamador
colapsa.* Los helpers se escribieron con cuidado —cuatro salidas en el paso 1, firmante frente
a operador, validación frente a fallo de red, un payload validado— y `alta_actuacion` los
aplana. Remediar los quince casos uno a uno habría dejado el dieciséis.
"""
from __future__ import annotations

import json

import pytest

from core import sudespacho_actuaciones as act


class _Resp:
    def __init__(self, status=200, payload=None, text="", crudo=None):
        self.status_code = status
        self._payload = payload if payload is not None else {}
        self._crudo = crudo
        self.text = text or json.dumps(self._payload)

    def json(self):
        if self._crudo is not None:          # un 200 cuyo cuerpo NO es JSON
            raise ValueError("Expecting value: line 1 column 1 (char 0)")
        return self._payload


class _Cliente:
    def __init__(self, gets=(), posts=()):
        self.gets, self.posts = list(gets), list(posts)
        self.peticiones: list[tuple[str, str, dict]] = []

    def get(self, url, **kw):
        self.peticiones.append(("GET", url, kw))
        r = self.gets.pop(0) if self.gets else _Resp(200, {"items": []})
        if isinstance(r, Exception):
            raise r
        return r

    def post(self, url, **kw):
        self.peticiones.append(("POST", url, kw))
        r = self.posts.pop(0) if self.posts else _Resp(201, {"id": 1})
        if isinstance(r, Exception):
            raise r
        return r

    @property
    def posts_hechos(self):
        return [u for m, u, _ in self.peticiones if m == "POST"]


def _fila(fid="1", **props):
    return {"id": fid, "values": [{"property": {"name": k}, "value": v}
                                  for k, v in props.items()]}


_DESTINO = ("extrajudiciales", "464", "BaRS10 (W-02VEKE)")


def _gets_ok(*resto):
    return [_Resp(200, {"items": [_fila("464", Referencia_Cliente="BaRS10 (W-02VEKE)")]}),
            _Resp(200, {"items": []}), *resto]


# ---------------------------------------------------------------------------
# El recibo no se pierde: un cuerpo ilegible NO puede escapar tras escribir
# ---------------------------------------------------------------------------


def test_un_cuerpo_no_json_en_el_paso_6_no_pierde_el_recibo():
    """**El crítico de la R2.** `_items` hacía `resp.json()` FUERA del `try`.

    Un `200` con cuerpo ilegible levantaba, la excepción atravesaba `alta_actuacion` entera
    —que no envuelve el paso 6— y el llamador recibía una excepción **en vez del recibo con el
    `act_id`**, justo después de haber escrito en el CRM. La respuesta natural a una excepción
    es repetir el alta: el escenario huérfano que el `Recibo` existe para impedir.

    Y es **el mismo defecto que el módulo hermano documenta como ya pagado**:
    `sudespacho_relations._buscar_registros` dice que una ronda anterior midió que «el `try`
    solo envolvía `r.json()`» y que ahora el parseo entero está cubierto.
    """
    c = _Cliente(gets=_gets_ok(_Resp(200, crudo="<html>no soy json</html>")),
                 posts=[_Resp(201, {"id": "N"}), _Resp(201, {})])
    r = act.alta_actuacion(*_DESTINO, asunto="X", firmante="Nikolai_Tyukhay", client=c)

    assert r.act_id == "N", "se perdió el id de una actuación YA creada"
    assert r.estado == "incompleta"


def test_un_cuerpo_no_json_en_el_paso_1_no_es_ausencia():
    """La misma raíz: `aprender_id_predefinido` levantaba en vez de decir «no pude mirar»."""
    c = _Cliente(gets=[_Resp(200, crudo="<html>")])
    assert act.aprender_id_predefinido("X", client=c).estado == "sin_comprobar"


def test_un_cuerpo_no_json_al_acreditar_el_destino_levanta_el_error_DEL_MODULO():
    """Un `ValueError` de parseo no lo captura quien captura `DestinoNoAcreditado`."""
    c = _Cliente(gets=[_Resp(200, crudo="<html>")])
    with pytest.raises(act.DestinoNoAcreditado):
        act.resolver_destino("extrajudiciales", "464", "X (W-02VEKE)", client=c)


# ---------------------------------------------------------------------------
# El destino: identidad exacta, y la fila que se lee es la que se pidió
# ---------------------------------------------------------------------------


def test_el_destino_se_acredita_con_LA_FILA_pedida_no_con_la_primera():
    """Si el filtro por `id` no muerde, `filas[0]` puede ser otro expediente.

    La función leía la primera fila sin comprobar que su `id` fuese el pedido — en la función
    cuyo cometido entero es «verificar por resultado, nunca por status».
    """
    c = _Cliente(gets=[_Resp(200, {"items": [
        _fila("999", Referencia_Cliente="BaRS10 (W-02VEKE)"),
        _fila("464", Referencia_Cliente="OTRO CASO (W-0AAAAA)"),
    ]})])
    with pytest.raises(act.DestinoNoAcreditado):
        act.resolver_destino("extrajudiciales", "464", "BaRS10 (W-02VEKE)", client=c)


@pytest.mark.parametrize("leida", [
    "OTRO (W-02VEKE9)",                  # el W-code truncado colapsaba con W-02VEKE
    "W-0XXXXX (relacionado W-02VEKE)",   # coincidencia secundaria, el principal es otro
])
def test_el_w_code_se_compara_ENTERO_y_como_principal(leida):
    """La regex propia capturaba 5-6 caracteres sin fronteras, así que `W-ABCDEF1` y
    `W-ABCDEF2` colapsaban en el mismo código.

    Y había un `wcode_match` en el módulo hermano que lo hace bien — el propio plan mandaba
    usarlo. **Escribir una regex nueva teniendo el helper delante** es la frontera: un
    identificador no se compara con una subcadena.
    """
    c = _Cliente(gets=[_Resp(200, {"items": [_fila("464", Referencia_Cliente=leida)]})])
    with pytest.raises(act.DestinoNoAcreditado):
        act.resolver_destino("extrajudiciales", "464", "BaRS10 (W-02VEKE)", client=c)


# ---------------------------------------------------------------------------
# El recibo: reanudar es reanudar, no crear
# ---------------------------------------------------------------------------


def test_reanudar_un_recibo_INCIERTO_no_crea_otra_actuacion():
    """`incierta` significa «el POST pudo crear algo y no sé el id». Su `act_id` es `None`, así
    que caía al camino de creación **sin decir nada** — justo lo que el diseño prohíbe.

    La prohibición vivía en el docstring y no en el código: un contrato que solo existe en
    prosa no es un contrato.
    """
    r0 = act.Recibo("incierta", act_id=None, paso=4, motivo="timeout")
    c = _Cliente(gets=_gets_ok(), posts=[_Resp(201, {"id": "M"})])
    with pytest.raises(act.ActuacionError) as exc:
        act.alta_actuacion(*_DESTINO, asunto="X", firmante="Nikolai_Tyukhay",
                           desde=r0, client=c)
    assert "concilia" in str(exc.value).lower()
    assert c.posts_hechos == [], "creó una actuación reanudando un recibo incierto"


def test_reanudar_con_el_recibo_de_OTRO_expediente_se_rechaza():
    """Acreditar el destino no acredita el objeto que se le vincula: son dos identidades.

    Sin esto, reanudar con el recibo equivocado vincula una actuación ajena — y el paso 6 la
    da por **verificada**, porque sí aparece del lado de ese expediente.
    """
    r0 = act.Recibo("incompleta", act_id="N", paso=4, elemento="extrajudiciales",
                    exp_id="999", motivo="")
    c = _Cliente(gets=_gets_ok(), posts=[_Resp(201, {})])
    with pytest.raises(act.ActuacionError):
        act.alta_actuacion(*_DESTINO, asunto="X", firmante="Nikolai_Tyukhay",
                           desde=r0, client=c)


def test_un_recibo_incompleto_del_MISMO_expediente_si_reanuda():
    """El otro lado de la frontera: lo que sí es reanudable, reanuda."""
    r0 = act.Recibo("incompleta", act_id="N", paso=4, elemento="extrajudiciales",
                    exp_id="464", motivo="")
    c = _Cliente(gets=[_Resp(200, {"items": [_fila("464", Referencia_Cliente="BaRS10 (W-02VEKE)")]}),
                       _Resp(200, {"items": [{"id": "N"}]})],
                 posts=[_Resp(201, {})])
    r = act.alta_actuacion(*_DESTINO, asunto="X", firmante="Nikolai_Tyukhay",
                           desde=r0, client=c)
    assert r.estado == "verificada"
    assert not [u for u in c.posts_hechos if "element_register" in u]


# ---------------------------------------------------------------------------
# El orquestador deja de colapsar lo que los helpers distinguen
# ---------------------------------------------------------------------------


def test_el_paso_1_consulta_el_asunto_QUE_SE_VA_A_ESCRIBIR():
    """Se aprendía el `id_predefinido` del asunto **crudo** y se escribía el **canónico**.

    Con `like` y sin prefijo, una consulta de `EXTRAJUDICIAL - REVISION VIABILIDAD` casa las
    filas `SENIOR - …` **y** las `ABOGADO - …`: se aprende la plantilla de la otra tarifa. El
    docstring del propio paso 1 advierte que «una aproximación devolvería el de otra
    plantilla», y su único llamador lo incumplía.
    """
    c = _Cliente(gets=_gets_ok(_Resp(200, {"items": [{"id": "N"}]})),
                 posts=[_Resp(201, {"id": "N"}), _Resp(201, {})])
    act.alta_actuacion(*_DESTINO, asunto="EXTRAJUDICIAL - REVISION VIABILIDAD",
                       firmante="ana.velastegui", client=c)

    consultas = [kw.get("params", {}) for m, u, kw in c.peticiones
                 if m == "GET" and "actuaciones" in u]
    assert consultas, "no se consultó el paso 1"
    pedido = str(consultas[0].get("filterGroup[filterGroups][0][filters][0][value]"))
    assert pedido.startswith("ABOGADO - "), (
        f"el paso 1 consultó {pedido!r} y el paso 4 escribe el canónico")


def test_no_poder_mirar_el_catalogo_NO_sigue_adelante():
    """Las cuatro salidas del paso 1 estaban probadas sobre la función y ninguna sobre la
    decisión: `alta_actuacion` leía `pre.valor` y nunca `pre.estado`, así que «no pude mirar»
    era indistinguible de «no aplica» — en un módulo cuya política es fallar cerrado.

    Es la pieza construida que nadie encadena.
    """
    c = _Cliente(gets=[_Resp(200, {"items": [_fila("464", Referencia_Cliente="BaRS10 (W-02VEKE)")]}),
                       _Resp(500, {})],
                 posts=[_Resp(201, {"id": "N"})])
    r = act.alta_actuacion(*_DESTINO, asunto="X", firmante="Nikolai_Tyukhay", client=c)
    assert r.estado != "verificada"
    assert c.posts_hechos == [], "escribió sin haber podido comprobar el catálogo"


@pytest.mark.parametrize("firmante, etiqueta", [
    ("", "vacío"),
    ("pepe.desconocido", "fuera de la tabla"),
])
def test_un_error_de_VALIDACION_no_se_disfraza_de_escritura_incierta(firmante, etiqueta):
    """`asunto_canonico` y `resolver_profesional` se evaluaban DENTRO del `try` que clasifica
    los fallos del POST, así que un `ValueError` salía como «puede haberse creado una
    actuación: concilia a mano» **sin haber tocado el CRM**.

    El diseño §4.3 dice que sin firmante el helper «para y lo dice». Paraba y decía otra cosa,
    y mandaba a conciliar un CRM intacto.
    """
    c = _Cliente(gets=_gets_ok())
    with pytest.raises(ValueError):
        act.alta_actuacion(*_DESTINO, asunto="X", firmante=firmante, client=c)
    assert c.posts_hechos == [], etiqueta


def test_extra_no_puede_sobrescribir_lo_que_se_acaba_de_validar():
    """`cuerpo.update(extra or {})` iba DESPUÉS de validar, así que permitía reemplazar
    `Subject`, `profesional_asignado` e `id_predefinido`.

    Con eso se eluden a la vez el prefijo del firmante —que **es la tarifa**—, la prohibición
    de pasar un id numérico de empleado y la evidencia del paso 1. La frontera: la validación
    se aplica al objeto **final** que cruza la frontera de escritura, no a un borrador que
    luego se puede pisar.
    """
    with pytest.raises(ValueError):
        act.crear_actuacion("SENIOR - X", profesional="Nikolai_Tyukhay",
                            extra={"Subject": "ABOGADO - X"},
                            client=_Cliente(posts=[_Resp(201, {"id": "N"})]))


def test_extra_sigue_admitiendo_los_campos_legitimos():
    """El remedio no puede llevarse por delante lo que `extra` existe para permitir."""
    c = _Cliente(posts=[_Resp(201, {"id": "N"})])
    act.crear_actuacion("SENIOR - X", profesional="Nikolai_Tyukhay",
                        extra={"fecha_vencimiento": "2026-11-10T00:00:00.000+01:00"},
                        client=c)
    cuerpo = [kw["json"] for m, u, kw in c.peticiones if m == "POST"][0]
    assert cuerpo["fecha_vencimiento"] == "2026-11-10T00:00:00.000+01:00"
    assert cuerpo["Subject"] == "SENIOR - X"


# ---------------------------------------------------------------------------
# El asunto y la duración: variantes de formato que evitaban la política
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("base", [
    "ABOGADO  -  X",     # espacios duplicados
    "abogado - X",       # minúsculas
    "  ABOGADO - X",     # sangrado
])
def test_un_prefijo_contradictorio_se_detecta_aunque_varie_el_formato(base):
    """Exigir `"ABOGADO - "` literal dejaba pasar `ABOGADO  -  X`, y el resultado era un asunto
    DOBLE (`SENIOR - ABOGADO  -  X`) en vez de la revisión humana que el runbook exige.

    Reconocer un valor estructurado exige decidir qué se hace con sus variantes de formato
    **antes** de aplicar la política.
    """
    with pytest.raises(ValueError):
        act.asunto_canonico(base, firmante="Nikolai_Tyukhay")


def test_el_prefijo_propio_se_normaliza_a_mayusculas():
    """El catálogo es mayúsculas y el prefijo es la tarifa: conservar la caja de entrada
    dejaba `senior - …` en el CRM."""
    assert act.asunto_canonico("senior - EXTRAJUDICIAL - X",
                               firmante="Nikolai_Tyukhay").startswith("SENIOR - ")


@pytest.mark.parametrize("ini, fin, etiqueta", [
    ("2026-09-14T10:00:00", "2026-09-14T10:01:30", "las dos sin zona"),
    ("2026-09-14T10:00:00Z", "2026-09-14T10:01:30", "una con zona y otra sin"),
])
def test_la_duracion_exige_zona_en_LOS_DOS_extremos(tmp_path, ini, fin, etiqueta):
    """El diseño §4.4 exige rechazar las fechas sin zona. `fromisoformat` las admite, así que
    dos fechas ingenuas devolvían un número; y una mezclada levantaba `TypeError` de Python en
    vez del error de dato legible.

    Poder restar dos representaciones temporales no acredita una duración entre instantes.
    """
    d = tmp_path / "00_Input"
    d.mkdir(parents=True)
    (d / "_apertura_v1.json").write_text(
        json.dumps({"ronda_id": "r1", "iniciada": ini, "terminada": fin}), encoding="utf-8")
    with pytest.raises(ValueError):
        act.duracion_desde_ronda(tmp_path)
