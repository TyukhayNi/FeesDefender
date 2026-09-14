"""R3 de P6 — las siete fronteras que la tercera ronda dejó abiertas.

Los nueve hallazgos de la R3 (`…-p6-ficha-crm-y-actuaciones-r3-adversarial-review.md`) son
ejemplos de **siete** fronteras, no nueve defectos sueltos. Cada bloque de abajo prueba la
frontera, no el ejemplo que el informe describía — que es justo lo que falló en la R2:
remediar los quince casos uno a uno habría dejado el dieciséis.

Adjudicación: `docs/superpowers/specs/2026-09-14-p6-ficha-crm-y-actuaciones-design.md` §8.
"""
from __future__ import annotations

import pytest

from core import sudespacho_actuaciones as sa
from core.sudespacho_actuaciones import (
    ActuacionError, CuerpoIlegible, Recibo, alta_actuacion, aprender_id_predefinido,
)
from tests.test_sudespacho_actuaciones_r2 import _Cliente, _Resp, _fila

FIRMANTE = "Nikolai_Tyukhay"


def _destino_ok():
    """El GET del paso 3: la fila 464 declara el W-code que se le va a pedir."""
    return _Resp(200, {"items": [_fila("464", **{"Referencia_Cliente": "W-ABCDE1"})]})


def _verificacion_ok(act_id="1"):
    """El GET del paso 6: la actuación creada aparece del lado del expediente.

    Se encola explícitamente porque el doble, agotada su cola, devuelve `{"items": []}` — y
    eso es un paso 6 que dice «no está». Dejarlo al fallback haría que un test sobre el paso 1
    fallara por el paso 6 y se leyera como defecto del paso 1.
    """
    return _Resp(200, {"items": [{"id": act_id, "values": []}]})


def _alta(cliente, **kw):
    return alta_actuacion("extrajudiciales", "464", "W-ABCDE1",
                          asunto="X", firmante=FIRMANTE, client=cliente, **kw)


# ---------------------------------------------------------------------------
# Frontera A — decodificar no es interpretar, y tras ESCRIBIR siempre hay recibo
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("cuerpo", [
    {"items": 1},                 # un entero donde debería ir la lista
    {"hydra:member": True},       # un booleano
    {"items": "texto"},           # iterable, pero no de filas: antes daba [] en silencio
    {"items": {"id": "1"}},       # un objeto suelto
])
def test_un_cuerpo_json_con_forma_imposible_sale_como_CuerpoIlegible(cuerpo):
    """`r.json()` no lanzando NO acredita que el cuerpo tenga la forma esperada.

    R3/H-01: el `try` cubría solo `resp.json()`, así que un JSON válido con `items` no-lista
    reventaba DESPUÉS, al iterar, con `TypeError` — que no es `CuerpoIlegible` y por tanto
    nadie captura. `{"items": "texto"}` era peor: devolvía `[]` en silencio, y una lista
    vacía significa «no hay», que es una afirmación sobre el CRM que nadie hizo.
    """
    with pytest.raises(CuerpoIlegible):
        sa._items(_Resp(200, cuerpo))


def test_una_fila_con_values_nulos_no_revienta_al_leerla():
    """R3/H-01: `values: [null]` daba `AttributeError` al aprender. Un `null` es dato del
    CRM, no un fallo del programa: se ignora la entrada ilegible y se leen las demás."""
    assert sa._values({"values": [None, {"property": {"name": "a"}, "value": "1"}]}) == {"a": "1"}


def test_tras_vincular_SIEMPRE_vuelve_un_recibo_aunque_verificar_reviente(monkeypatch):
    """**La invariante de la pieza entera**: en cuanto se ha escrito en el CRM, el llamador
    recibe el `act_id` pase lo que pase.

    R3/H-01: la llamada del paso 6 estaba fuera de todo `try`, así que una excepción
    inesperada atravesaba `alta_actuacion` **después de vincular**. La respuesta natural a una
    excepción es repetir el alta, y eso deja una actuación huérfana en el expediente del
    cliente. Se prueba inyectando el fallo en el helper, no en el transporte: la garantía es
    del orquestador y no puede depender de que el helper siga capturando bien.
    """
    def revienta(*a, **kw):
        raise RuntimeError("cualquier cosa inesperada")

    monkeypatch.setattr(sa, "verificar_actuacion_vinculada", revienta)
    c = _Cliente(gets=[_destino_ok(), _Resp(200, {"items": [_fila("9", Subject="X",
                                                                 id_predefinido=84)]})])
    r = _alta(c)
    assert r.act_id, "el llamador tiene que recibir el id de lo que se acaba de crear"
    assert r.estado == "incompleta" and r.paso == 5
    assert "no se pudo verificar" in r.motivo.lower()


# ---------------------------------------------------------------------------
# Frontera B — un contexto ausente no desactiva la comprobación que ese contexto permite
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("elemento, exp_id, patron", [
    ("", "", "no dice a qué expediente"),       # no acredita nada
    ("", "999", "acreditar el destino"),        # acredita a medias, y no cuadra
    ("judiciales", "", "acreditar el destino"),
])
def test_un_recibo_que_no_acredita_su_expediente_no_reanuda_ni_escribe(elemento, exp_id, patron):
    """R3/H-02: la guarda de identidad estaba condicionada a `desde.elemento`, que es `""`
    por defecto. Un recibo construido con los valores por defecto **se saltaba la guarda que
    su propia ausencia debería haber disparado** y vinculaba una actuación ajena.

    Se prueban los tres huecos, no el que el informe describía: acreditar nada, y acreditar a
    medias por cada lado. Una guarda que solo cubre un hueco deja los otros dos.
    """
    c = _Cliente(gets=[_destino_ok()])
    with pytest.raises(ActuacionError, match=patron):
        _alta(c, desde=Recibo("incompleta", act_id="AJENA", paso=4,
                              elemento=elemento, exp_id=exp_id))
    assert c.posts_hechos == [], "no se escribe nada cuando el recibo no acredita su destino"


def test_un_recibo_en_un_estado_que_no_existe_no_reanuda_ni_escribe():
    """R3/H-02: el vocabulario de estados no se comprobaba, así que `"inventado"` pasaba las
    dos guardas —no es `incierta` y tiene `act_id`— y escribía."""
    c = _Cliente(gets=[_destino_ok()])
    with pytest.raises(ActuacionError, match="estado"):
        _alta(c, desde=Recibo("inventado", act_id="AJENA", paso=4,
                              elemento="extrajudiciales", exp_id="464"))
    assert c.posts_hechos == []


def test_un_recibo_con_un_paso_imposible_no_reanuda_ni_escribe():
    """R3/H-02: `paso=-9` describía un recorrido que no existe y se aceptaba igual."""
    c = _Cliente(gets=[_destino_ok()])
    with pytest.raises(ActuacionError, match="paso"):
        _alta(c, desde=Recibo("incompleta", act_id="A1", paso=-9,
                              elemento="extrajudiciales", exp_id="464"))
    assert c.posts_hechos == []


# ---------------------------------------------------------------------------
# Frontera C — estados de conocimiento distintos no se colapsan,
#              y un motivo no afirma lo que nadie vio
# ---------------------------------------------------------------------------


def test_un_id_predefinido_ilegible_no_se_declara_no_aplica():
    """R3/H-03: un valor no convertible caía en `no_aplica` con el motivo «las instancias
    reales traen el campo vacío» — una afirmación sobre lo observado que era **falsa**.
    Haber mirado y no entender lo que hay es un tercer estado."""
    c = _Cliente(gets=[_Resp(200, {"items": [_fila("9", Subject="X", id_predefinido="basura")]})])
    pre = aprender_id_predefinido("X", client=c)
    assert pre.estado == "no_interpretable"
    assert "vacío" not in pre.motivo, "no se afirma haber visto un campo vacío"
    assert "basura" in pre.motivo


def test_el_recibo_final_distingue_sin_filas_de_no_aplica():
    """R3/H-03: los dos terminaban en un POST idéntico y un recibo `verificada` sin rastro.
    Son estados de conocimiento distintos sobre el catálogo y el recibo debe conservarlos."""
    # El asunto que se consulta es el CANÓNICO, no el crudo: la fila que simula «hay
    # instancias y traen el campo vacío» tiene que llevar ese mismo asunto o cae en
    # `sin_filas` y el test mediría otra cosa.
    canonico = sa.asunto_canonico("X", firmante=FIRMANTE)

    def recibo_con(filas):
        c = _Cliente(gets=[_destino_ok(), _Resp(200, {"items": filas}), _verificacion_ok()])
        return _alta(c)

    sin_filas = recibo_con([])
    no_aplica = recibo_con([_fila("9", Subject=canonico, id_predefinido="")])
    assert sin_filas.estado == no_aplica.estado == "verificada"
    assert sin_filas.motivo != no_aplica.motivo
    assert "sin_filas" in sin_filas.motivo and "no_aplica" in no_aplica.motivo


def test_no_poder_comprobar_el_catalogo_no_escribe():
    """El estado de fallar cerrado sigue siendo el que era: sin saber el id, no se escribe."""
    c = _Cliente(gets=[_destino_ok(), _Resp(500, {})])
    r = _alta(c)
    assert c.posts_hechos == []
    assert r.estado == "no_intentada"


# ---------------------------------------------------------------------------
# Frontera D — la evidencia recibida debe ser de la operación que se ejecuta
# ---------------------------------------------------------------------------


def test_solo_se_aprende_de_la_fila_cuyo_asunto_es_EXACTAMENTE_el_pedido():
    """R3/H-04: el filtro es `like`, así que `SENIOR - X` trae también `SENIOR - X AMPLIADA`.
    Se tomaba el primer entero de cualquier fila, y **permutar el orden cambiaba el id**: la
    plantilla aprendida dependía del orden de la respuesta. El propio docstring del paso 1
    exige el asunto literal; su código no lo comprobaba."""
    filas = [_fila("1", Subject="X AMPLIADA", id_predefinido=99),
             _fila("2", Subject="X", id_predefinido=84)]
    for orden in (filas, list(reversed(filas))):
        pre = aprender_id_predefinido("X", client=_Cliente(gets=[_Resp(200, {"items": orden})]))
        assert pre.estado == "aprendido" and pre.valor == 84


def test_si_ninguna_fila_es_el_asunto_pedido_no_se_aprende_nada():
    """Traer variantes no es traer el asunto: no se hereda el id de una plantilla vecina."""
    c = _Cliente(gets=[_Resp(200, {"items": [_fila("1", Subject="X AMPLIADA",
                                                   id_predefinido=99)]})])
    pre = aprender_id_predefinido("X", client=c)
    assert pre.estado == "sin_filas"
    assert pre.valor is None


# ---------------------------------------------------------------------------
# Frontera F — «no lo intenté» es un estado, no una variante de «lo intenté y no sé»
# ---------------------------------------------------------------------------


def test_el_recibo_de_no_haber_escrito_SE_puede_reanudar():
    """R3/H-06 — **el estado que creó mi propio remedio.**

    Al fallar el paso 1 se devolvía `incompleta` sin `act_id`; reanudarlo chocaba con la
    guarda de `incierta`/sin-id y levantaba «puede haber una actuación creada cuyo id no
    conocemos: búscala en el CRM». **No se había escrito nada.** Mandaba a un humano a
    conciliar a mano un efecto inexistente, y dejaba el recibo en un callejón sin salida.
    """
    c = _Cliente(gets=[_destino_ok(), _Resp(500, {})])
    primero = _alta(c)
    assert primero.estado == "no_intentada" and c.posts_hechos == []

    c2 = _Cliente(gets=[_destino_ok(), _Resp(200, {"items": [_fila("9", Subject="X",
                                                                  id_predefinido=84)]}),
                        _verificacion_ok()])
    segundo = _alta(c2, desde=primero)
    assert segundo.estado == "verificada" and segundo.act_id
    assert len([u for u in c2.posts_hechos if "element_register/actuaciones" in u]) == 1


def test_un_recibo_incierto_sigue_sin_poder_reanudarse():
    """La guarda que sí era correcta no se debilita al añadir el estado nuevo."""
    c = _Cliente(gets=[_destino_ok()])
    with pytest.raises(ActuacionError, match="segunda"):
        _alta(c, desde=Recibo("incierta", paso=4, elemento="extrajudiciales", exp_id="464"))
    assert c.posts_hechos == []


# ---------------------------------------------------------------------------
# Frontera G — validar y transmitir son fases distintas
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Lo que encontró la corrida EN VIVO, que ningún doble podía encontrar
# ---------------------------------------------------------------------------


def test_la_actuacion_nace_con_fecha_y_con_tarifa():
    """En vivo salió con `fecha_alta` vacía y `precio_hora = 0,00`, mientras las 40 reales
    muestreadas traían las dos. Una actuación sin fecha no se factura; una a cero no cobra —
    y las dos **parecen completas** en el listado, que es lo que las hace caras.

    El precio sale de la MISMA fila que el prefijo: el asunto decía `SENIOR - …`, que ES la
    tarifa de 103 €/h, y el precio decía cero. Dos datos sobre lo mismo, en desacuerdo.
    """
    c = _Cliente(gets=[_destino_ok(), _Resp(200, {"items": []}), _verificacion_ok()])
    _alta(c)
    cuerpo = [kw for m, u, kw in c.peticiones
              if m == "POST" and "element_register/actuaciones" in u][0]["json"]
    assert cuerpo["fecha_alta"], "una actuación sin fecha de alta no se puede facturar"
    assert cuerpo["precio_hora"] == sa._PRECIO_POR_FIRMANTE[FIRMANTE]
    assert cuerpo["Subject"].startswith(sa._PREFIJO_POR_FIRMANTE[FIRMANTE])


def test_un_firmante_sin_tarifa_no_factura_por_defecto():
    """La tabla no tiene defecto, por la misma razón que no lo tiene la de prefijos: elegir
    una tarifa por defecto factura al cliente la de otro."""
    with pytest.raises(ValueError, match="tarifa"):
        sa._precio_de("pepe.desconocido")


def test_el_vencimiento_se_AGENDA_ademas_de_escribirse():
    """`fecha_vencimiento` es un campo que nadie mira: lo que avisa es el evento. El paso 7
    crea el evento en `calendario` y lo cuelga de la actuación."""
    c = _Cliente(gets=[_destino_ok(), _Resp(200, {"items": []}), _verificacion_ok()],
                 posts=[_Resp(201, {"id": "1"}),        # la actuación
                        _Resp(201, {}),                 # el vínculo con el expediente
                        _Resp(201, {"id": "77"}),       # el evento
                        _Resp(201, {})])                # el vínculo del evento
    r = _alta(c, vence="2026-10-01 09:00:00")
    assert r.estado == "verificada" and r.paso == 7
    assert "/api/element_register/calendario" in c.posts_hechos
    assert f"/api/relation_element/actuaciones/{r.act_id}" in c.posts_hechos
    cuerpo_act = [kw for m, u, kw in c.peticiones
                  if m == "POST" and "element_register/actuaciones" in u][0]["json"]
    assert cuerpo_act["fecha_vencimiento"] == "2026-10-01 09:00:00"


def test_sin_vencimiento_no_se_agenda_nada():
    """No toda actuación vence, y agendar un compromiso que nadie pidió es inventarlo."""
    c = _Cliente(gets=[_destino_ok(), _Resp(200, {"items": []}), _verificacion_ok()])
    r = _alta(c)
    assert r.paso == 6
    assert not any("calendario" in u for u in c.posts_hechos)


def test_si_el_evento_falla_la_actuacion_NO_se_pierde():
    """**La invariante del paso 6, una vez más.** La actuación ya está creada, vinculada y
    verificada: un fallo al agendar no puede llevarse el recibo, porque el llamador repetiría
    el alta y crearía una segunda actuación por un evento que no se pudo poner."""
    c = _Cliente(gets=[_destino_ok(), _Resp(200, {"items": []}), _verificacion_ok()],
                 posts=[_Resp(201, {"id": "1"}), _Resp(201, {}), _Resp(500, {})])
    r = _alta(c, vence="2026-10-01 09:00:00")
    assert r.act_id == "1", "el llamador conserva el id de lo que ya existe"
    assert r.estado == "incompleta" and r.paso == 7
    assert "no repitas el alta" in r.motivo.lower()


@pytest.mark.parametrize("inicio, fin, patron", [
    ("2026-10-01 09:00:00", "2026-09-01 09:00:00", "antes de empezar"),
    ("", "2026-10-01 09:00:00", "inicio y fin"),
    ("2026-10-01 09:00:00", "", "inicio y fin"),
])
def test_un_evento_imposible_para_antes_de_escribir(inicio, fin, patron):
    c = _Cliente()
    with pytest.raises(ValueError, match=patron):
        sa.crear_evento_calendario("X", inicio=inicio, fin=fin,
                                   profesional=FIRMANTE, client=c)
    assert c.posts_hechos == []


def test_el_tipo_del_evento_esta_en_el_enum_del_CRM():
    """El enum de `calendario` lo declara el atlas y se verificó en vivo."""
    c = _Cliente()
    with pytest.raises(ValueError, match="Tipo"):
        sa.crear_evento_calendario("X", inicio="2026-10-01 09:00:00",
                                   fin="2026-10-01 10:00:00", profesional=FIRMANTE,
                                   tipo="Inventado", client=c)
    assert c.posts_hechos == []


def test_la_prioridad_que_se_manda_esta_en_el_enum_del_CRM():
    """**Lo encontró la corrida EN VIVO, y ningún doble podía encontrarlo.**

    El payload mandaba `Prioridad: "Normal"`, un valor que no existe: el enum del CRM es
    `Alta · Media · Baja`, consta así en `INTEGRACION_SUDESPACHO.md` §15.6 —el SSOT— y se
    verificó en vivo con `GET /api/view/enums/actuaciones/Prioridad`. El tenant devolvía
    `HTTP 404: The value: <Normal> sent for the property: Prioridad is incorrect`.

    Los dobles aceptan cualquier cosa que se les mande, así que este defecto es invisible
    para ellos **por construcción**: el doble acredita qué decide el código ante una
    respuesta, nunca que el payload sea aceptable. De ahí que la prueba de aceptación de esta
    pieza sea correrla contra el CRM real, y no una ronda más de lectura.
    """
    assert sa._PRIORIDAD_POR_DEFECTO in sa._PRIORIDADES
    c = _Cliente(gets=[_destino_ok(), _Resp(200, {"items": []}), _verificacion_ok()])
    _alta(c)
    cuerpo = [kw for m, u, kw in c.peticiones
              if m == "POST" and "element_register/actuaciones" in u][0]["json"]
    assert cuerpo["Prioridad"] in sa._PRIORIDADES
    assert cuerpo["Estado"] in sa._ESTADOS_ACTUACION


@pytest.mark.parametrize("campo, valor", [
    ("Prioridad", "Normal"),        # el valor exacto que el tenant rechazó
    ("Prioridad", ""),
    ("Estado", "Pendiente"),
])
def test_un_valor_fuera_del_enum_para_antes_de_escribir(campo, valor):
    """Misma frontera que `extra`: validar y transmitir son fases distintas.

    Un valor fuera del enum es un defecto del payload y se ve **sin preguntarle al CRM**. Si
    se descubre por el rechazo del POST, el recibo sale `incierta` —«puede haberse creado una
    actuación, concilia a mano»— por algo que nunca pudo crearse. Es lo que pasó en la corrida
    en vivo del 2026-09-14.
    """
    c = _Cliente(gets=[_destino_ok(), _Resp(200, {"items": []}), _verificacion_ok()])
    with pytest.raises(ValueError, match=campo):
        _alta(c, extra={campo: valor})
    assert c.posts_hechos == []


@pytest.mark.parametrize("campo", ["Subject", "profesional_asignado", "id_predefinido"])
def test_un_extra_invalido_para_ANTES_de_escribir_y_no_insinua_que_pudo_crear(campo):
    """R3/H-07: el rechazo de `extra` ocurre antes del POST, pero vivía dentro del `try` que
    clasifica los fallos del POST. Un `ValueError` de validación salía como «el POST no dio
    recibo: puede haberse creado una actuación… concilia a mano», con **cero** escrituras.

    Es la misma frontera que ya se cerró para el firmante en la R2, un caso más allá: la
    clasificación de «resultado incierto» empieza cuando puede haber existido un POST.
    """
    c = _Cliente(gets=[_destino_ok(), _Resp(200, {"items": [_fila("9", Subject="X",
                                                                 id_predefinido=84)]})])
    with pytest.raises(ValueError, match="sobrescribir"):
        _alta(c, extra={campo: "loquesea"})
    assert c.posts_hechos == [], "no se escribió nada: no hay nada que conciliar"


def test_el_evento_se_ata_a_su_actuacion_COMO_LO_HACE_LA_UI():
    """Medido el 2026-09-14 comparando dos eventos reales del tenant.

    El creado desde la UI (20234) lleva `miembro=<act_id>` + `elemento='actuaciones'` y **no**
    tiene relación con la actuación. El que creaba esta función (20235) tenía la relación y
    `miembro` vacío. Los dos «funcionan» en el sentido de que existe una conexión, pero solo
    uno aparece donde el despacho lo busca: el panel de la actuación.

    Se replica la forma de la UI porque quien lea el dato mañana lo va a comparar con lo que ve
    en pantalla, no con lo que yo decidí que era equivalente.
    """
    c = _Cliente(gets=[_destino_ok(), _Resp(200, {"items": []}), _verificacion_ok()],
                 posts=[_Resp(201, {"id": "1"}), _Resp(201, {}),
                        _Resp(201, {"id": "77"}), _Resp(201, {})])
    r = _alta(c, vence="2026-10-01 09:00:00")
    cuerpo = [kw for m, u, kw in c.peticiones
              if m == "POST" and "element_register/calendario" in u][0]["json"]
    assert cuerpo["miembro"] == int(r.act_id)
    assert cuerpo["elemento"] == "actuaciones"
    assert cuerpo["Tipo"] == "Vencimiento"
    assert cuerpo["profesional_asignado"] == FIRMANTE


# ---------------------------------------------------------------------------
# Recordatorios e invitados: PHP serializado, con la forma REAL del tenant
# ---------------------------------------------------------------------------


def test_el_serializador_php_reproduce_cadenas_REALES_del_tenant():
    """Las tres cadenas de abajo están copiadas de registros vivos del CRM (eventos 17646,
    17642 y 20183, leídos el 2026-09-14). Probar contra ellas es lo único que acredita el
    formato: un serializador «que parece PHP» puede producir algo que el CRM guarda y luego
    no sabe leer, y eso no se ve hasta que alguien abre el evento.
    """
    assert sa._php(["x"]) == 'a:1:{i:0;s:1:"x";}'
    assert sa._php({"a": 1}) == 'a:1:{s:1:"a";i:1;}'
    # evento 17646, recordatorio de correo a 7 días
    assert sa._php([{"tipo": "correo_electronico", "cuanto": 7, "tiempo": "day"}]) == (
        'a:1:{i:0;a:3:{s:4:"tipo";s:18:"correo_electronico";s:6:"cuanto";i:7;'
        's:6:"tiempo";s:3:"day";}}')
    # evento 17642, ventana emergente a 1 minuto
    assert sa._php([{"tipo": "ventana_emergente", "cuanto": 1, "tiempo": "minute"}]) == (
        'a:1:{i:0;a:3:{s:4:"tipo";s:17:"ventana_emergente";s:6:"cuanto";i:1;'
        's:6:"tiempo";s:6:"minute";}}')
    # evento 20183, un invitado: clave == valor
    assert sa._invitados_php(["paola.barreto@tyukhay.legal"]) == (
        'a:1:{s:27:"paola.barreto@tyukhay.legal";s:27:"paola.barreto@tyukhay.legal";}')


def test_la_longitud_del_serializador_va_en_BYTES_no_en_caracteres():
    """PHP cuenta bytes. Un invitado con tilde en el dominio o el nombre rompería la cadena si
    se contaran caracteres, y el CRM la guardaría igual: el defecto se vería al leerla."""
    assert sa._php("ñ") == 's:2:"ñ";'
    assert sa._php("añb") == 's:4:"añb";'


def test_el_evento_lleva_recordatorios_e_invitados_si_se_piden():
    c = _Cliente(gets=[_destino_ok(), _Resp(200, {"items": []}), _verificacion_ok()],
                 posts=[_Resp(201, {"id": "1"}), _Resp(201, {}),
                        _Resp(201, {"id": "77"}), _Resp(201, {})])
    _alta(c, vence="2026-10-01 09:00:00",
          recordatorios=[{"tipo": "correo_electronico", "cuanto": 7, "tiempo": "day"}],
          invitados=["ana.velastegui@tyukhay.legal"])
    cuerpo = [kw for m, u, kw in c.peticiones
              if m == "POST" and "element_register/calendario" in u][0]["json"]
    assert cuerpo["recordatorios"].startswith("a:1:{i:0;a:3:")
    assert "ana.velastegui@tyukhay.legal" in cuerpo["invitadosexternal"]


def test_sin_recordatorios_ni_invitados_van_los_arrays_VACIOS_no_ausentes():
    """`a:0:{}` es lo que escribe la UI. Omitir el campo y mandar el array vacío no son lo
    mismo para quien lo lea después: uno dice «no hay», el otro «nadie lo tocó»."""
    c = _Cliente(gets=[_destino_ok(), _Resp(200, {"items": []}), _verificacion_ok()],
                 posts=[_Resp(201, {"id": "1"}), _Resp(201, {}),
                        _Resp(201, {"id": "77"}), _Resp(201, {})])
    _alta(c, vence="2026-10-01 09:00:00")
    cuerpo = [kw for m, u, kw in c.peticiones
              if m == "POST" and "element_register/calendario" in u][0]["json"]
    assert cuerpo["recordatorios"] == "a:0:{}"
    assert cuerpo["invitadosexternal"] == "a:0:{}"


@pytest.mark.parametrize("malo, patron", [
    ({"tipo": "sms", "cuanto": 7, "tiempo": "day"}, "tipo"),
    ({"tipo": "correo_electronico", "cuanto": 7, "tiempo": "fortnight"}, "tiempo"),
    ({"tipo": "correo_electronico", "cuanto": "siete", "tiempo": "day"}, "cuanto"),
])
def test_un_recordatorio_con_forma_imposible_para_antes_de_escribir(malo, patron):
    """Los valores válidos aquí son los **observados** en 500 eventos reales, no un enum que el
    CRM declare: estos viven dentro del blob serializado y no hay endpoint que los liste. Se
    valida contra lo medido y se dice que es lo medido — que no es lo mismo que una garantía.
    """
    c = _Cliente()
    with pytest.raises(ValueError, match=patron):
        sa.crear_evento_calendario("X", inicio="2026-10-01 09:00:00", fin="2026-10-01 10:00:00",
                                   profesional=FIRMANTE, recordatorios=[malo], client=c)
    assert c.posts_hechos == []


def test_la_descripcion_es_un_CAMPO_y_el_seguimiento_un_ELEMENTO():
    """Dos cosas distintas que la UI pone una debajo de la otra. `Description` es lo que la
    actuación **es**; un seguimiento es algo que alguien **anotó después**, con su autor, y
    vive en su propio elemento colgado de la actuación."""
    c = _Cliente(gets=[_destino_ok(), _Resp(200, {"items": []}), _verificacion_ok(),
                       _Resp(200, [{"element": "seguimientos", "registries": {"5": {}}}])],
                 posts=[_Resp(201, {"id": "1"}), _Resp(201, {}),
                        _Resp(201, {"id": "5"}), _Resp(201, {})])
    r = _alta(c, descripcion="PROBANDO", seguimientos=["nota con & y <"])
    assert r.estado == "verificada", "con la relación acreditada, el alta se completa"
    act = [kw for m, u, kw in c.peticiones
           if m == "POST" and "element_register/actuaciones" in u][0]["json"]
    assert act["Description"] == "PROBANDO"
    seg = [kw for m, u, kw in c.peticiones
           if m == "POST" and "element_register/seguimientos" in u][0]["json"]
    assert seg["notas"] == "<p>nota con &amp; y &lt;</p>", "el HTML se escapa antes de envolver"
    assert "/api/relation_element/actuaciones/1" in c.posts_hechos


def test_un_201_de_la_relacion_NO_acredita_que_el_seguimiento_quedara_colgado():
    """**Medido en vivo el 2026-09-14 y es el corazón de esta pieza.** El POST de la relación
    devuelve `201` y al releer la actuación el seguimiento **no está**. Verificar por status
    habría devuelto «hecho» sobre una nota que nadie va a ver nunca.
    """
    c = _Cliente(gets=[_destino_ok(), _Resp(200, {"items": []}), _verificacion_ok(),
                       _Resp(200, [{"element": "calendario", "registries": {"9": {}}}])],
                 posts=[_Resp(201, {"id": "1"}), _Resp(201, {}),
                        _Resp(201, {"id": "5"}), _Resp(201, {})])
    r = _alta(c, seguimientos=["x"])
    assert r.estado == "incompleta" and r.act_id == "1"
    assert "no repitas el alta" in r.motivo.lower()


def test_un_seguimiento_que_falla_NO_se_lleva_la_actuacion():
    c = _Cliente(gets=[_destino_ok(), _Resp(200, {"items": []}), _verificacion_ok()],
                 posts=[_Resp(201, {"id": "1"}), _Resp(201, {}), _Resp(500, {})])
    r = _alta(c, seguimientos=["x"])
    assert r.act_id == "1" and r.estado == "incompleta"
    assert "no repitas el alta" in r.motivo.lower()


def test_un_seguimiento_vacio_no_anota_nada():
    c = _Cliente()
    with pytest.raises(ValueError, match="notas"):
        sa.crear_seguimiento("1", "   ", client=c)
    assert c.posts_hechos == []


def test_la_terna_de_facturacion_va_ENTERA_o_no_va():
    """**Las tres cosas juntas o ninguna**, y lo dice el dato real: hay 10 actuaciones del
    despacho con `facturar=1` y `tipo_facturacion=duracion` cuyo `precio_hora` es `0,00` —
    declaradas facturables por duración y facturando cero—, frente a 27 con la terna completa.

    Sin `tipo_facturacion` el CRM no sabe por qué eje cobrar, así que poner solo la tarifa no
    cobra. Es la casilla «Facturar por duración» de la UI.
    """
    c = _Cliente(gets=[_destino_ok(), _Resp(200, {"items": []}), _verificacion_ok()])
    _alta(c)
    cuerpo = [kw for m, u, kw in c.peticiones
              if m == "POST" and "element_register/actuaciones" in u][0]["json"]
    assert cuerpo["facturar"] is True
    assert cuerpo["tipo_facturacion"] == "duracion"
    assert cuerpo["precio_hora"] == sa._PRECIO_POR_FIRMANTE[FIRMANTE]


def test_una_actuacion_no_facturable_no_declara_eje_de_facturacion():
    c = _Cliente(gets=[_destino_ok(), _Resp(200, {"items": []}), _verificacion_ok()])
    _alta(c, facturar=False)
    cuerpo = [kw for m, u, kw in c.peticiones
              if m == "POST" and "element_register/actuaciones" in u][0]["json"]
    assert cuerpo["facturar"] is False
    assert cuerpo["tipo_facturacion"] == "", "sin facturar, el eje no dice nada"


def test_facturar_por_unidades_es_el_OTRO_eje():
    c = _Cliente(gets=[_destino_ok(), _Resp(200, {"items": []}), _verificacion_ok()])
    _alta(c, tipo_facturacion="precio", unidades=3, precio_unidad="150.00")
    cuerpo = [kw for m, u, kw in c.peticiones
              if m == "POST" and "element_register/actuaciones" in u][0]["json"]
    assert cuerpo["tipo_facturacion"] == "precio"
    assert cuerpo["unidades"] == 3 and cuerpo["precio_unidad"] == "150.00"
    assert "total" not in cuerpo, "el total lo calcula el CRM, no se escribe"


def test_un_eje_de_facturacion_inventado_para_antes_de_escribir():
    c = _Cliente(gets=[_destino_ok(), _Resp(200, {"items": []}), _verificacion_ok()])
    with pytest.raises(ValueError, match="tipo_facturacion"):
        _alta(c, tipo_facturacion="por_las_buenas")
    assert c.posts_hechos == []


def test_el_evento_lleva_EL_MISMO_asunto_que_su_actuacion():
    """**Una propiedad de seguridad, no de estilo.** Medido en vivo el 2026-09-14: con
    `miembro` puesto, el CRM sincroniza el `Subject` del evento **sobre el de la actuación**.
    Se probó con un título propio (`"VENCE — …"`) y tres actuaciones reales acabaron
    renombradas; hubo que repararlas a mano.

    Y el daño potencial no es cosmético: **el prefijo del asunto ES la tarifa** (`SENIOR` son
    103 €/h y `ABOGADO` 77). Un título de evento que no empiece por el prefijo correcto puede
    cambiar lo que se le factura al cliente. La UI le pone el mismo título, y por eso allí la
    sincronización es inocua.
    """
    c = _Cliente(gets=[_destino_ok(), _Resp(200, {"items": []}), _verificacion_ok()],
                 posts=[_Resp(201, {"id": "1"}), _Resp(201, {}),
                        _Resp(201, {"id": "77"}), _Resp(201, {})])
    _alta(c, vence="2026-10-01 09:00:00")
    act = [kw for m, u, kw in c.peticiones
           if m == "POST" and "element_register/actuaciones" in u][0]["json"]
    ev = [kw for m, u, kw in c.peticiones
          if m == "POST" and "element_register/calendario" in u][0]["json"]
    assert ev["Subject"] == act["Subject"], (
        "un Subject distinto en el evento RENOMBRA la actuación, y el prefijo es la tarifa")


@pytest.mark.parametrize("tiempo", ["day", "minute", "month", "hour", "year"])
def test_los_cinco_tiempos_del_desplegable_se_aceptan(tiempo):
    """La UI ofrece cinco: Minutos · Horas · Días · Meses · Años. El barrido de los 2.309
    eventos con recordatorio del tenant acredita la grafía de tres (`day`, `minute`, `month`).
    `hour` y `year` no aparecían en ningún dato: se escribieron por API en dos sondas y **la UI
    los pintó** como «3 horas antes» y «3 años antes» (2026-09-14). Se separan en el módulo
    porque las dos vías no valen lo mismo, y una grafía mala **no da error**: el recordatorio
    se guarda y no salta nunca."""
    sa._validar_recordatorios([{"tipo": "correo_electronico", "cuanto": 1, "tiempo": tiempo}])


def test_las_dos_fuentes_del_vocabulario_se_declaran_por_separado():
    """Los cinco están acreditados, por dos vías que **no valen lo mismo**. El barrido prueba
    que la grafía existe en datos viejos; la confirmación por UI prueba que el CRM **entiende**
    un valor escrito por API — que es más fuerte. Separarlas conserva cuánta confianza merece
    cada valor, en un campo donde equivocarse no da error: el recordatorio simplemente no salta.
    """
    assert set(sa._REC_TIEMPOS_EN_DATOS) == {"day", "minute", "month"}
    assert set(sa._REC_TIEMPOS_CONFIRMADOS_UI) == {"hour", "year"}
    assert not (set(sa._REC_TIEMPOS_EN_DATOS) & set(sa._REC_TIEMPOS_CONFIRMADOS_UI))


# ---------------------------------------------------------------------------
# Cerrar la actuación: de Planificado a Hecho
# ---------------------------------------------------------------------------


def _releida(coincide=True, act_id="21393"):
    """La relectura del paso de verificación, **como la haría el servidor**.

    `_estado_es` consulta filtrando por `Estado` y busca el id entre los resultados —no filtra
    por `id`, porque sobre `actuaciones` ese filtro devuelve vacío (medido)—. Así que el doble
    tiene que devolver la fila **solo si el estado coincide**: un doble que ignora el filtro
    devuelve la fila siempre y hace que el test apruebe lo contrario de lo que dice probar.
    """
    return _Resp(200, {"items": [{"id": act_id, "values": []}] if coincide else []})


def test_cerrar_una_actuacion_le_pone_estado_y_FECHA_DE_FIN():
    """Las dos cosas van juntas: de las actuaciones reales en `Hecho`, la fecha de fin viene
    poblada. Una actuación cerrada sin fecha no dice cuándo se hizo, que es lo que se factura.
    """
    c = _Cliente(gets=[_releida()], posts=[])
    sa.cerrar_actuacion("21393", duracion_s=1200, client=c)
    cuerpo = [kw for m, u, kw in c.peticiones if m == "PUT"][0]["json"]
    assert cuerpo["Estado"] == "Hecho"
    assert cuerpo["fecha_fin"], "una actuación hecha sin fecha de fin no dice cuándo se hizo"
    assert cuerpo["duracion"] == "00:20:00"


def test_un_200_del_PUT_no_acredita_que_quedara_HECHA():
    """**La regla dura de este CRM, y en esta misma pieza ya mordió**: un `POST` de relación
    devolvía 201 sin crear nada. Aquí el `PUT` devuelve 200 y la relectura dice `Planificado`:
    no se da por cerrada."""
    c = _Cliente(gets=[_releida(coincide=False)])
    with pytest.raises(ActuacionError, match="verificar por resultado"):
        sa.cerrar_actuacion("21393", client=c)


def test_si_no_se_puede_releer_tampoco_se_da_por_cerrada():
    """No poder comprobar NO es haber comprobado."""
    c = _Cliente(gets=[_Resp(500, {})])
    with pytest.raises(ActuacionError):
        sa.cerrar_actuacion("21393", client=c)


def test_una_actuacion_no_facturable_tampoco_declara_tarifa():
    """Si no se factura, no hay tarifa que declarar. Dos campos diciendo cosas distintas sobre
    lo mismo es exactamente el defecto que esta pieza ya pagó una vez."""
    c = _Cliente(gets=[_destino_ok(), _Resp(200, {"items": []}), _verificacion_ok()])
    _alta(c, facturar=False)
    cuerpo = [kw for m, u, kw in c.peticiones
              if m == "POST" and "element_register/actuaciones" in u][0]["json"]
    assert cuerpo["facturar"] is False
    assert cuerpo["precio_hora"] == "0.00"
    assert cuerpo["tipo_facturacion"] == ""
