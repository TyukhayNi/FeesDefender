"""La puerta humana: sin confirmación válida no sale nada, y un plan rancio se rechaza."""
from __future__ import annotations

import base64
import dataclasses
import datetime as dt
import json
from decimal import Decimal

import pytest

from core import expedicion_certificada as exp

# H-06: campos separados como los devuelve `clientes_contrarios` de verdad (docs/
# CRM_SUDESPACHO_ATLAS.md § clientes_contrarios), no el nombre completo embutido en
# "nombre". Este fichero no asierta sobre el contenido de "nombre" -- ver
# tests/test_expedicion_plan.py y tests/test_expedicion_ficha_postal.py para eso --
# pero las fixtures deben reflejar la forma real igualmente.
ANA = {"nombre": "ANA", "1apellido": "LOPEZ", "2apellido": "", "direccion": "C Mayor 1",
       "poblacion": "Madrid", "provincia": "Madrid", "cp": "28001", "email": "ana@x.es",
       "movil": "665130883"}
MAR = {"nombre": "MAR", "1apellido": "GIL", "2apellido": "", "direccion": "Av Sur 9",
       "poblacion": "Sevilla", "provincia": "Sevilla", "cp": "41001", "email": "mar@x.es",
       "movil": "688222333"}


class _CodicertFalso:
    """Doble del transporte. Cuenta lo que se manda y no toca la red.

    `destinatarios` y `adjuntos` (hallazgos H-01/H-02, revisión adversarial r2):
    antes el doble solo contaba canal e id_personalizado -- suficiente para los
    tests de reanudación, pero ciego a QUIÉN recibió de verdad o QUÉ adjunto
    viajó de verdad. Sin eso no se puede probar que un destinatario mutado tras
    aprobar el plan no se manda, ni que el PDF que sale es el que se hasheó y
    no uno sustituido durante `listar()`. Es aditivo: no cambia la forma de
    `enviados`, que los tests de reanudación ya usan.
    """

    def __init__(self, credito=Decimal("100"), listado=()):
        self.credito_ = credito
        self.listado = list(listado)
        self.enviados: list[tuple[str, str]] = []
        self.destinatarios: list[dict] = []   # el destinatario real de cada envío, en orden
        self.adjuntos: list[list[dict]] = []  # los adjuntos reales de cada envío, en orden
        self._contador = 0  # cada envío real tiene su propio IdEnvio, nunca repetido

    def credito(self): return self.credito_
    def listar(self, **_): return list(self.listado)

    def enviar_burofax(self, **kw):
        self._contador += 1
        self.enviados.append(("burofax", kw["id_personalizado"]))
        self.destinatarios.append(kw["destinatario"])
        self.adjuntos.append(kw["adjuntos"])
        return f"B{self._contador}"

    def enviar_eec(self, **kw):
        self._contador += 1
        self.enviados.append((kw["tipo_entrega"], kw["id_personalizado"]))
        self.destinatarios.append(kw["destinatarios"][0])
        self.adjuntos.append(kw["adjuntos"])
        return f"E{self._contador}"


def _entorno(tmp_path, cod=None, partes=(ANA,), plaza="Madrid", entorno="sandbox"):
    return exp.EntornoExpedicion(
        codicert=cod or _CodicertFalso(),
        partes_de=lambda _w: list(partes),
        ahora=lambda: dt.datetime(2026, 9, 17, 12, 0, tzinfo=dt.timezone.utc),
        raiz=tmp_path,
        plaza=plaza,
        entorno=entorno)


def _doc(tmp_path):
    d = tmp_path / "A.pdf"; d.write_bytes(b"%PDF A")
    return [d]


def test_planificar_resuelve_identificador_coste_y_ausencias(tmp_path):
    plan = exp.planificar("W-04AKM2", "OVC", _doc(tmp_path), entorno_exp=_entorno(tmp_path),
                          plaza="Madrid")
    assert plan.id_personalizado == "W-04AKM2 - OVC"
    assert plan.coste == exp.coste_de(plan.envios)
    assert len(plan.envios) == 3


def test_ejecutar_sin_confirmacion_NO_manda_nada(tmp_path):
    cod = _CodicertFalso()
    ent = _entorno(tmp_path, cod)
    plan = exp.planificar("W-04AKM2", "OVC", _doc(tmp_path), entorno_exp=ent, plaza="Madrid")
    with pytest.raises(exp.ExpedicionError):
        exp.ejecutar(plan, exp.Confirmacion(digest="digest-que-no-es"), entorno_exp=ent)
    assert cod.enviados == []


def test_ejecutar_con_la_confirmacion_del_plan_manda_los_tres(tmp_path):
    cod = _CodicertFalso()
    ent = _entorno(tmp_path, cod)
    plan = exp.planificar("W-04AKM2", "OVC", _doc(tmp_path), entorno_exp=ent, plaza="Madrid")
    exp.ejecutar(plan, exp.Confirmacion(digest=plan.digest), entorno_exp=ent)
    assert sorted(c for c, _ in cod.enviados) == ["burofax", "correo", "sms"]
    assert {i for _, i in cod.enviados} == {"W-04AKM2 - OVC"}


def test_un_plan_rancio_se_rechaza_si_el_CRM_cambio(tmp_path):
    cod = _CodicertFalso()
    ent = _entorno(tmp_path, cod)
    plan = exp.planificar("W-04AKM2", "OVC", _doc(tmp_path), entorno_exp=ent, plaza="Madrid")
    otro = exp.EntornoExpedicion(codicert=cod, ahora=ent.ahora, raiz=ent.raiz,
                                 plaza=ent.plaza, entorno=ent.entorno,
                                 partes_de=lambda _w: [{**ANA, "direccion": "OTRA CALLE 9"}])
    with pytest.raises(exp.ExpedicionError) as e:
        exp.ejecutar(plan, exp.Confirmacion(digest=plan.digest), entorno_exp=otro)
    assert "cambiado" in str(e.value).lower()
    assert cod.enviados == []


def test_no_repite_lo_que_la_plataforma_ya_tiene_y_el_registro_NO_explica(tmp_path):
    """La plataforma ya tiene un envío con este id_personalizado y el registro local
    (vacío) no sabe nada de él: pudo expedirse desde otra máquina o desde el portal.
    La ausencia no se puede sostener sobre algo inmediato, así que se para y se declara
    SIN VERIFICAR -- ya NO es el "ya existe... no se repite" incondicional de antes,
    que no distinguía "explicado" de "sin explicar" (hallazgo 3; firma viva de
    `RegistroIntencion.ids_hechos_de`, que no existía cuando se escribió este test)."""
    cod = _CodicertFalso(listado=[{"id": "x", "id_personalizado": "W-04AKM2 - OVC"}])
    ent = _entorno(tmp_path, cod)
    plan = exp.planificar("W-04AKM2", "OVC", _doc(tmp_path), entorno_exp=ent, plaza="Madrid")
    with pytest.raises(exp.ExpedicionError) as e:
        exp.ejecutar(plan, exp.Confirmacion(digest=plan.digest), entorno_exp=ent)
    assert "sin verificar" in str(e.value).lower()
    assert cod.enviados == []


def test_sin_credito_suficiente_el_plan_nace_NO_ejecutable(tmp_path):
    ent = _entorno(tmp_path, _CodicertFalso(credito=Decimal("1")))
    plan = exp.planificar("W-04AKM2", "OVC", _doc(tmp_path), entorno_exp=ent, plaza="Madrid")
    assert plan.ejecutable is False
    with pytest.raises(exp.ExpedicionError):
        exp.ejecutar(plan, exp.Confirmacion(digest=plan.digest), entorno_exp=ent)


def test_un_pendiente_de_otro_expediente_no_bloquea_este(tmp_path):
    """`exigir_sin_pendientes` se acota al `id_personalizado` que se ejecuta (spec §4.3):
    un pendiente anotado para OTRO expediente no debe impedir esta expedición.

    Firma viva de `RegistroIntencion.exigir_sin_pendientes(id_personalizado=None)`: el
    brief del task traía `registro.exigir_sin_pendientes()` sin acotar, desactualizado
    tras las rondas de revisión que movieron esta firma.
    """
    cod = _CodicertFalso()
    ent = _entorno(tmp_path, cod)
    exp.RegistroIntencion(tmp_path / "_codicert_intencion.jsonl").anotar(
        "W-OTRO - REQ", "burofax", "alguien")
    plan = exp.planificar("W-04AKM2", "OVC", _doc(tmp_path), entorno_exp=ent, plaza="Madrid")
    ids = exp.ejecutar(plan, exp.Confirmacion(digest=plan.digest), entorno_exp=ent)
    assert len(ids) == 3


def test_un_pendiente_del_MISMO_expediente_si_bloquea(tmp_path):
    """El mismo mecanismo, pero con el pendiente anotado para ESTA expedición: sí debe
    bloquear el envío en vez de arriesgar un duplicado.

    El `RegistroIntencion` sembrado a mano lleva `entorno`/`usuario` iguales a los de
    `ent` (hallazgo H-04): sin ellos, la anotación pertenecería a un entorno/cuenta
    DISTINTO del que usa `ejecutar` y no bloquearía nada -- justo el defecto que
    H-04 corrige, no lo que este test quiere probar.
    """
    cod = _CodicertFalso()
    ent = _entorno(tmp_path, cod)
    exp.RegistroIntencion(tmp_path / "_codicert_intencion.jsonl",
                          entorno=ent.entorno, usuario=ent.usuario).anotar(
        "W-04AKM2 - OVC", "burofax", "alguien")
    plan = exp.planificar("W-04AKM2", "OVC", _doc(tmp_path), entorno_exp=ent, plaza="Madrid")
    with pytest.raises(exp.ExpedicionError):
        exp.ejecutar(plan, exp.Confirmacion(digest=plan.digest), entorno_exp=ent)
    assert cod.enviados == []


# ---------------------------------------------------------------------------------
# Hallazgo 1 (crítico): la replanificación debe rehashear el documento desde disco,
# nunca comparar `plan.documentos_sha256` contra sí mismo.
# ---------------------------------------------------------------------------------

def test_replanificacion_rehashea_el_documento_no_reusa_el_del_plan(tmp_path):
    """Si el PDF se sobrescribe en su misma ruta entre planificar y ejecutar, ejecutar
    debe detectarlo re-hasheando desde disco. Comparar `plan.documentos_sha256` (el
    valor ya guardado en el plan) contra sí mismo nunca puede diferir: la línea que
    arma los adjuntos sí relee el fichero, así que hoy se manda un documento distinto
    del que el humano leyó."""
    cod = _CodicertFalso()
    ent = _entorno(tmp_path, cod)
    doc = _doc(tmp_path)
    plan = exp.planificar("W-04AKM2", "OVC", doc, entorno_exp=ent, plaza="Madrid")
    doc[0].write_bytes(b"%PDF OTRO CONTENIDO, SOBRESCRITO TRAS APROBAR EL PLAN")
    with pytest.raises(exp.ExpedicionError) as e:
        exp.ejecutar(plan, exp.Confirmacion(digest=plan.digest), entorno_exp=ent)
    assert "cambiado" in str(e.value).lower()
    assert cod.enviados == []


def test_documento_desaparecido_para_la_ejecucion_con_mensaje_claro(tmp_path):
    """Si el documento ya no existe en su ruta al ejecutar, debe pararse con un mensaje
    claro y `ExpedicionError` -- no con un `FileNotFoundError` crudo al construir los
    adjuntos, varias líneas más abajo."""
    cod = _CodicertFalso()
    ent = _entorno(tmp_path, cod)
    doc = _doc(tmp_path)
    plan = exp.planificar("W-04AKM2", "OVC", doc, entorno_exp=ent, plaza="Madrid")
    doc[0].unlink()
    with pytest.raises(exp.ExpedicionError) as e:
        exp.ejecutar(plan, exp.Confirmacion(digest=plan.digest), entorno_exp=ent)
    mensaje = str(e.value).lower()
    assert "ya no existe" in mensaje
    assert doc[0].name.lower() in mensaje
    assert cod.enviados == []


# ---------------------------------------------------------------------------------
# Hallazgo 2 (crítico): `plaza` y `entorno` deben entrar en el digest, y `ejecutar`
# debe comprobar que el entorno con el que se le llama es el que produjo el plan.
# ---------------------------------------------------------------------------------

def test_dos_planes_iguales_salvo_el_entorno_tienen_digest_distinto(tmp_path):
    """Dos planes idénticos salvo por entorno="sandbox" frente a "produccion" NO deben
    compartir digest: si lo hicieran, una confirmación leída para uno autorizaría, sin
    que nadie lo notara, el otro -- cobrando y notificando de verdad."""
    ent = _entorno(tmp_path)
    doc = _doc(tmp_path)
    sandbox = exp.planificar("W-04AKM2", "OVC", doc, entorno_exp=ent, plaza="Madrid",
                             entorno="sandbox")
    produccion = exp.planificar("W-04AKM2", "OVC", doc, entorno_exp=ent, plaza="Madrid",
                                entorno="produccion")
    assert sandbox.digest != produccion.digest


def test_dos_planes_iguales_salvo_la_plaza_tienen_digest_distinto(tmp_path):
    ent = _entorno(tmp_path)
    doc = _doc(tmp_path)
    madrid = exp.planificar("W-04AKM2", "OVC", doc, entorno_exp=ent, plaza="Madrid")
    valencia = exp.planificar("W-04AKM2", "OVC", doc, entorno_exp=ent, plaza="Valencia")
    assert madrid.digest != valencia.digest


def test_ejecutar_para_si_el_entorno_de_llamada_no_coincide_con_el_del_plan(tmp_path):
    """El plan se aprobó para Madrid/sandbox. Si `ejecutar` se invoca con un
    `EntornoExpedicion` que dice producción, debe pararse y decirlo explícitamente --
    hoy esa inconsistencia es estructuralmente indetectable, porque `ejecutar` nunca
    lee `plan.entorno` ni `plan.plaza`."""
    cod = _CodicertFalso()
    ent_planificacion = _entorno(tmp_path, cod, plaza="Madrid", entorno="sandbox")
    plan = exp.planificar("W-04AKM2", "OVC", _doc(tmp_path), entorno_exp=ent_planificacion,
                          plaza="Madrid", entorno="sandbox")
    ent_ejecucion = _entorno(tmp_path, cod, plaza="Madrid", entorno="produccion")
    with pytest.raises(exp.ExpedicionError) as e:
        exp.ejecutar(plan, exp.Confirmacion(digest=plan.digest), entorno_exp=ent_ejecucion)
    assert "entorno" in str(e.value).lower()
    assert cod.enviados == []


# ---------------------------------------------------------------------------------
# Hallazgo 3 (crítico): un fallo a mitad de expedición debe poder reanudarse
# completando lo que falta, nunca repitiendo lo hecho ni bloqueando en bloque.
# ---------------------------------------------------------------------------------

def test_tras_fallo_a_mitad_la_segunda_ejecucion_completa_solo_lo_que_falta(tmp_path):
    """Simula el estado que deja un fallo a mitad de la expedición de seis envíos: los
    dos primeros quedan HECHOS y en la plataforma; los otros cuatro nunca se
    intentaron. Se siembra el registro y el listado directamente (en vez de forzar una
    excepción real dentro de `ejecutar`) porque una anotación EN VUELO sin cerrar ya
    tiene su propia red -- incondicional -- en `test_un_pendiente_del_MISMO_expediente
    _si_bloquea`, y mezclar los dos escenarios en un solo test confundiría cuál red
    detecta cuál fallo.

    Una segunda ejecución debe mandar EXACTAMENTE los cuatro que faltan: ni repetir los
    dos ya hechos (la plataforma solo debe crecer en 4, no en 6) ni quedarse callada.

    El `reg` sembrado lleva `entorno`/`usuario` de `ent` y anota con `e.destinatario`,
    no `e.etiqueta` (hallazgo H-04): son los mismos dos campos que `ejecutar` usa para
    decidir qué cuenta como cerrado, y sembrar con otros distintos simularía el propio
    defecto que H-04 corrige en vez de un fallo a mitad de camino dentro del MISMO
    entorno/cuenta.
    """
    cod = _CodicertFalso()
    ent = _entorno(tmp_path, cod, partes=(ANA, MAR))
    plan = exp.planificar("W-04AKM2", "OVC", _doc(tmp_path), entorno_exp=ent, plaza="Madrid")
    assert len(plan.envios) == 6  # 2 partes x (correo + sms + burofax), domicilios distintos

    reg = exp.RegistroIntencion(tmp_path / "_codicert_intencion.jsonl",
                                entorno=ent.entorno, usuario=ent.usuario, ahora=ent.ahora)
    ya_hechos = plan.envios[:2]          # "envíos 1 y 2": ya se mandaron y están en la plataforma
    ids_plataforma = []
    for numero, e in enumerate(ya_hechos, start=1):
        clave = reg.anotar(plan.id_personalizado, e.canal, e.destinatario)
        id_envio = f"ID-{numero}"
        reg.cerrar(clave, id_envio)
        ids_plataforma.append(id_envio)
    cod.listado = [{"id": i, "id_personalizado": plan.id_personalizado} for i in ids_plataforma]

    ids = exp.ejecutar(plan, exp.Confirmacion(digest=plan.digest), entorno_exp=ent)

    assert len(ids) == 4
    assert sorted(c for c, _ in cod.enviados) == ["burofax", "burofax", "correo", "sms"]
    assert all(idp == plan.id_personalizado for _, idp in cod.enviados)
    # El registro local ahora explica los seis, no solo los dos sembrados.
    assert len(reg.ids_hechos_de(plan.id_personalizado)) == 6


def test_expedicion_ya_completa_lo_dice_sin_error_generico(tmp_path):
    """Si los seis envíos ya están hechos y la plataforma los explica en su totalidad,
    el mensaje debe decir que la expedición YA ESTÁ COMPLETA -- no el "ya existe... no
    se repite" genérico de antes, que no distinguía "ya se mandaron los 6" de "se
    mandaron 2 de 6".

    Mismo motivo que en el test anterior para sembrar con `entorno`/`usuario` de `ent`
    y con `e.destinatario` (hallazgo H-04): tienen que casar con lo que `ejecutar`
    usa, o esto dejaría de probar "ya completa" y pasaría a probar, sin querer, el
    propio defecto de H-04.
    """
    cod = _CodicertFalso()
    ent = _entorno(tmp_path, cod, partes=(ANA, MAR))
    plan = exp.planificar("W-04AKM2", "OVC", _doc(tmp_path), entorno_exp=ent, plaza="Madrid")
    reg = exp.RegistroIntencion(tmp_path / "_codicert_intencion.jsonl",
                                entorno=ent.entorno, usuario=ent.usuario, ahora=ent.ahora)
    ids_plataforma = []
    for numero, e in enumerate(plan.envios, start=1):
        clave = reg.anotar(plan.id_personalizado, e.canal, e.destinatario)
        id_envio = f"ID-{numero}"
        reg.cerrar(clave, id_envio)
        ids_plataforma.append(id_envio)
    cod.listado = [{"id": i, "id_personalizado": plan.id_personalizado} for i in ids_plataforma]

    with pytest.raises(exp.ExpedicionError) as e:
        exp.ejecutar(plan, exp.Confirmacion(digest=plan.digest), entorno_exp=ent)
    assert "completa" in str(e.value).lower()
    assert cod.enviados == []


# ---------------------------------------------------------------------------------
# Hallazgo 4 (importante): `EntornoExpedicion.ahora` está declarado y nunca se usa;
# `RegistroIntencion` debe recibir el reloj inyectado en vez de leer el suyo propio.
# ---------------------------------------------------------------------------------

def test_registro_usa_el_reloj_inyectado_no_el_reloj_real(tmp_path):
    """El docstring de `EntornoExpedicion.ahora` afirma que todo lo no determinista
    entra por ahí. Si `RegistroIntencion` sigue generando su propio timestamp con
    `datetime.now()` directo, esto no se puede asertar y la doctrina del puerto único
    queda de boquilla."""
    reloj = dt.datetime(2020, 1, 1, 9, 30, tzinfo=dt.timezone.utc)
    ruta = tmp_path / "i.jsonl"
    reg = exp.RegistroIntencion(ruta, ahora=lambda: reloj)
    reg.anotar("W-1 - REQ", "burofax", "ANA")
    fila = json.loads(ruta.read_text(encoding="utf-8").splitlines()[0])
    assert fila["timestamp"] == reloj.isoformat()


def test_ejecutar_conecta_el_reloj_del_entorno_al_registro(tmp_path):
    """No basta con que `RegistroIntencion` ACEPTE un reloj: `ejecutar` tiene que
    pasarle `entorno_exp.ahora`, si no la conexión no existe en producción."""
    cod = _CodicertFalso()
    reloj_fijo = dt.datetime(2026, 9, 17, 8, 0, tzinfo=dt.timezone.utc)
    ent = exp.EntornoExpedicion(codicert=cod, partes_de=lambda _w: [ANA],
                                ahora=lambda: reloj_fijo, raiz=tmp_path,
                                plaza="Madrid", entorno="sandbox")
    plan = exp.planificar("W-04AKM2", "OVC", _doc(tmp_path), entorno_exp=ent, plaza="Madrid")
    exp.ejecutar(plan, exp.Confirmacion(digest=plan.digest), entorno_exp=ent)
    filas = [json.loads(l) for l in
             (tmp_path / "_codicert_intencion.jsonl").read_text(encoding="utf-8").splitlines()]
    anotaciones = [f for f in filas if f.get("estado") == "en_vuelo"]
    assert anotaciones and all(f["timestamp"] == reloj_fijo.isoformat() for f in anotaciones)


# ---------------------------------------------------------------------------------
# Hallazgo 5 (importante): el crédito se captura en planificar y debe releerse en
# ejecutar, antes de mandar nada.
# ---------------------------------------------------------------------------------

def test_ejecutar_relee_el_credito_en_vivo_antes_de_gastar(tmp_path):
    """`plan.credito` se congela en planificar. Si baja para cuando se ejecuta (otra
    expedición consumió saldo mientras tanto), ejecutar debe leerlo de nuevo y
    pararse -- no fiarse del valor de hace rato, que ya nace `plan.ejecutable`."""
    cod = _CodicertFalso(credito=Decimal("100"))
    ent = _entorno(tmp_path, cod)
    plan = exp.planificar("W-04AKM2", "OVC", _doc(tmp_path), entorno_exp=ent, plaza="Madrid")
    assert plan.ejecutable is True
    cod.credito_ = Decimal("0.01")  # otra expedición gastó el saldo mientras tanto
    with pytest.raises(exp.ExpedicionError) as e:
        exp.ejecutar(plan, exp.Confirmacion(digest=plan.digest), entorno_exp=ent)
    assert "crédito" in str(e.value).lower()
    assert cod.enviados == []


# ---------------------------------------------------------------------------------
# H-01 (alto, estructural; revisión adversarial r2). `_digest_de` sellaba expediente,
# tipo, plaza, entorno, documentos y destinatarios, pero dejaba fuera el ORDINAL del
# identificador, el asunto, el cuerpo, el coste y la cuenta emisora. Y `frozen=True`
# en `Plan` no inmoviliza las listas ni los diccionarios que contiene: mutar
# `plan.envios[i].destinatario` después de aprobar seguía surtiendo efecto porque
# `ejecutar` recalculaba el digest con los destinatarios frescos del CRM pero mandaba
# los de `plan.envios`, sin comprobar que fueran los mismos.
# ---------------------------------------------------------------------------------

def test_H01_confirmar_un_ordinal_no_autoriza_ejecutar_otro_ordinal(tmp_path):
    """Modo de fallo 1: dos planes que solo difieren en el ORDINAL (mismo w_code,
    tipo, plaza, entorno, destinatarios y documento) no deben compartir digest. Antes
    lo compartían: la confirmación que un humano leyó y aprobó para "W-04AKM2 - REQ"
    (ordinal 1, sin sufijo) autorizaba, sin que nadie lo notara, ejecutar
    "W-04AKM2 - REQ 2" (ordinal 2) -- un segundo envío real con identificador
    distinto, nunca leído ni aprobado. La vía es pública: --ordinal, sin tocar nada
    por dentro del plan."""
    cod = _CodicertFalso()
    ent = _entorno(tmp_path, cod)
    doc = _doc(tmp_path)
    plan_1 = exp.planificar("W-04AKM2", "REQ", doc, entorno_exp=ent, plaza="Madrid", ordinal=1)
    plan_2 = exp.planificar("W-04AKM2", "REQ", doc, entorno_exp=ent, plaza="Madrid", ordinal=2)

    assert plan_1.id_personalizado != plan_2.id_personalizado  # por construcción
    assert plan_1.digest != plan_2.digest, (
        "dos planes con distinto ordinal comparten digest: la confirmación de uno "
        "autorizaría ejecutar el otro")

    with pytest.raises(exp.ExpedicionError):
        exp.ejecutar(plan_2, exp.Confirmacion(digest=plan_1.digest), entorno_exp=ent)
    assert cod.enviados == []


def test_H01_mutar_el_destinatario_tras_aprobar_no_desvia_el_envio(tmp_path):
    """Modo de fallo 2: `EnvioPrevisto` es `frozen`, pero su `destinatario` es un
    `dict` corriente -- `frozen=True` no impide mutarlo por dentro. Modificar
    `plan.envios[i].destinatario['correo']` DESPUÉS de aprobar el plan no debe desviar
    el envío: el CRM sigue teniendo el correo original, y es a ESE al que hay que ser
    fiel, no al plan que alguien pudo tocar entre medias."""
    cod = _CodicertFalso()
    ent = _entorno(tmp_path, cod)
    plan = exp.planificar("W-04AKM2", "OVC", _doc(tmp_path), entorno_exp=ent, plaza="Madrid")
    confirmacion = exp.Confirmacion(digest=plan.digest)

    envio_correo = next(e for e in plan.envios if e.canal == "correo")
    correo_original = envio_correo.destinatario["correo"]
    envio_correo.destinatario["correo"] = "atacante@evil.example"

    exp.ejecutar(plan, confirmacion, entorno_exp=ent)

    correos_mandados = [dest.get("correo") for (canal, _), dest
                        in zip(cod.enviados, cod.destinatarios) if canal == "correo"]
    assert "atacante@evil.example" not in correos_mandados
    assert correos_mandados == [correo_original]


def test_H01_sustituir_asunto_cuerpo_y_coste_no_burla_la_confirmacion(tmp_path):
    """Modo de fallo 3: `dataclasses.replace` produce un `Plan` NUEVO que conserva el
    `digest` del original -- `frozen=True` protege la instancia, no impide construir
    una copia modificada con el mismo sello, porque `replace` copia los campos no
    tocados tal cual. Sustituir asunto y cuerpo, y poner el coste a un céntimo, no
    debe poder ejecutarse con la confirmación leída para el plan ORIGINAL cuando el
    crédito real solo alcanza para ese céntimo."""
    cod = _CodicertFalso(credito=Decimal("0.01"))  # no alcanza para el coste real (~17,76 €)
    ent = _entorno(tmp_path, cod)
    plan = exp.planificar("W-04AKM2", "OVC", _doc(tmp_path), entorno_exp=ent, plaza="Madrid")
    confirmacion = exp.Confirmacion(digest=plan.digest)

    plan_manipulado = dataclasses.replace(
        plan, asunto="Asunto que el humano nunca leyó",
        cuerpo="<p>Cuerpo que el humano nunca leyó</p>", coste=Decimal("0.01"))
    assert plan_manipulado.digest == plan.digest  # el campo se copia tal cual, sin recalcular

    with pytest.raises(exp.ExpedicionError):
        exp.ejecutar(plan_manipulado, confirmacion, entorno_exp=ent)
    assert cod.enviados == []


def test_H01_cambiar_la_cuenta_emisora_no_burla_la_confirmacion(tmp_path):
    """Modo de fallo 4: cambiar la cuenta emisora resuelta, manteniendo plaza y
    entorno, tampoco debe poder ejecutar una confirmación pensada para OTRO emisor --
    el sello y la comprobación de entorno tienen que cubrir también QUIÉN manda, no
    solo desde dónde y contra qué."""
    cod = _CodicertFalso()
    ent_planificacion = exp.EntornoExpedicion(
        codicert=cod, partes_de=lambda _w: [ANA],
        ahora=lambda: dt.datetime(2026, 9, 17, 12, 0, tzinfo=dt.timezone.utc),
        raiz=tmp_path, plaza="Madrid", entorno="sandbox", usuario="BD-MADRID-1")
    plan = exp.planificar("W-04AKM2", "OVC", _doc(tmp_path), entorno_exp=ent_planificacion,
                          plaza="Madrid")
    confirmacion = exp.Confirmacion(digest=plan.digest)

    ent_otro_emisor = exp.EntornoExpedicion(
        codicert=cod, partes_de=lambda _w: [ANA], ahora=ent_planificacion.ahora,
        raiz=tmp_path, plaza="Madrid", entorno="sandbox", usuario="BD-OTRO-EMISOR")

    with pytest.raises(exp.ExpedicionError) as e:
        exp.ejecutar(plan, confirmacion, entorno_exp=ent_otro_emisor)
    assert "entorno" in str(e.value).lower()
    assert cod.enviados == []


# ---------------------------------------------------------------------------------
# H-02 (alto, acotado; revisión adversarial r2). El PDF se rehasheaba para comprobar
# su huella y, más abajo -- después de paginar el listado remoto, una ventana larga
# --, se releía la MISMA ruta para construir el adjunto. Un documento sobrescrito
# durante esa ventana pasaba el hash validado contra el contenido viejo y salía con
# el nuevo.
# ---------------------------------------------------------------------------------

def test_H02_el_documento_no_se_relee_tras_validar_su_huella(tmp_path):
    """Se aprueba el PDF A. El doble de `listar()` -- la consulta remota que pagina
    entre la validación y el envío -- sobrescribe la ruta con el PDF B en cuanto se le
    llama, simulando exactamente la ventana que describe el hallazgo. El adjunto que
    de verdad viaja en la llamada de envío debe seguir siendo A: leído una sola vez,
    con esos mismos bytes hasheados y adjuntados, sin volver a abrir la ruta."""
    doc = _doc(tmp_path)
    original = doc[0].read_bytes()
    sustituto = b"%PDF SUSTITUIDO DURANTE LA VENTANA DE listar()"

    class _CodicertQueSustituyeDuranteElListado(_CodicertFalso):
        def listar(self, **_):
            doc[0].write_bytes(sustituto)
            return list(self.listado)

    cod = _CodicertQueSustituyeDuranteElListado()
    ent = _entorno(tmp_path, cod)
    plan = exp.planificar("W-04AKM2", "OVC", doc, entorno_exp=ent, plaza="Madrid")
    confirmacion = exp.Confirmacion(digest=plan.digest)

    exp.ejecutar(plan, confirmacion, entorno_exp=ent)

    assert doc[0].read_bytes() == sustituto  # la sustitución sí ocurrió
    primer_adjunto = cod.adjuntos[0][0]
    bytes_mandados = base64.b64decode(primer_adjunto["datos"])
    assert bytes_mandados == original
    assert bytes_mandados != sustituto


# ---------------------------------------------------------------------------------
# H-03 (alto, acotado; revisión adversarial r2). Los pares ya cerrados del registro
# local solo se consultaban DENTRO de la rama que se ejecuta cuando el listado remoto
# muestra algo (`if ids_en_plataforma:`). Un listado vacío -- latencia, paginación, un
# fallo transitorio -- tomaba la rama `else: pendientes = list(envios_ahora)` SIN
# consultar `pares_cerrados` ni una sola vez, aunque el registro local tuviera la
# evidencia inmediata de que ya se había mandado.
# ---------------------------------------------------------------------------------

def test_H03_listado_remoto_vacio_no_reactiva_cierres_ya_hechos(tmp_path):
    """Primera ejecución: manda y cierra los tres envíos. Segunda ejecución: el
    listado remoto vuelve VACÍO (se simula no sembrando `cod.listado`, que
    `_CodicertFalso` deja en `()` por defecto -- exactamente lo que devolvería una
    consulta que no refleja todavía esta expedición). Reejecutar el MISMO plan no
    debe mandar nada más: los cierres locales cuentan también con censo negativo."""
    cod = _CodicertFalso()
    ent = _entorno(tmp_path, cod)
    plan = exp.planificar("W-04AKM2", "OVC", _doc(tmp_path), entorno_exp=ent, plaza="Madrid")
    exp.ejecutar(plan, exp.Confirmacion(digest=plan.digest), entorno_exp=ent)
    assert len(cod.enviados) == 3
    cod.enviados = []

    assert cod.listado == []  # el listado remoto sigue vacío: no se sembró

    with pytest.raises(exp.ExpedicionError) as e:
        exp.ejecutar(plan, exp.Confirmacion(digest=plan.digest), entorno_exp=ent)
    assert "completa" in str(e.value).lower()
    assert cod.enviados == []  # nada se manda por segunda vez


# ---------------------------------------------------------------------------------
# H-04 (alto, estructural; revisión adversarial r2). El registro de intención no
# identificaba el ENTORNO ni la CUENTA emisora -- todos comparten el mismo fichero
# bajo el directorio de trabajo --, y la huella de cada envío se calculaba sobre la
# ETIQUETA de presentación, que en el burofax ni siquiera incluye el código postal,
# la provincia o la persona de atención. Tres modos de fallo cubiertos: cierres de
# SANDBOX completando una expedición de PRODUCCIÓN en el mismo directorio; un cambio
# de código postal que seguía dando "ya está completa" con el domicilio viejo; y un
# registro en formato antiguo (sin entorno/cuenta) que no se puede sostener de quién
# es, así que para y lo declara en vez de adivinar.
# ---------------------------------------------------------------------------------

def test_H04_cierres_de_sandbox_no_completan_produccion(tmp_path):
    """Se expiden los tres canales de "W-04AKM2 - OVC" en SANDBOX, los tres cerrados.
    En el MISMO directorio se arranca la MISMA expedición en PRODUCCIÓN y se
    interrumpe tras cerrar solo el primer envío (correo): se siembra ese único cierre
    -- en el entorno "produccion" -- y el listado remoto de producción lo refleja.
    Reanudar en producción debe mandar los DOS que faltan ahí -- no los tres de
    sandbox, que no pertenecen a este entorno --, nunca declarar "ya está completa"."""
    cod = _CodicertFalso()

    ent_sandbox = _entorno(tmp_path, cod, entorno="sandbox")
    plan_sandbox = exp.planificar("W-04AKM2", "OVC", _doc(tmp_path), entorno_exp=ent_sandbox,
                                  plaza="Madrid", entorno="sandbox")
    exp.ejecutar(plan_sandbox, exp.Confirmacion(digest=plan_sandbox.digest), entorno_exp=ent_sandbox)
    assert len(cod.enviados) == 3
    cod.enviados = []  # a partir de aquí solo se cuentan los envíos de producción

    ent_prod = _entorno(tmp_path, cod, entorno="produccion")
    plan_prod = exp.planificar("W-04AKM2", "OVC", _doc(tmp_path), entorno_exp=ent_prod,
                               plaza="Madrid", entorno="produccion")
    reg_prod = exp.RegistroIntencion(tmp_path / "_codicert_intencion.jsonl",
                                     entorno="produccion", usuario=ent_prod.usuario,
                                     ahora=ent_prod.ahora)
    primero = plan_prod.envios[0]
    clave = reg_prod.anotar(plan_prod.id_personalizado, primero.canal, primero.destinatario)
    reg_prod.cerrar(clave, "PROD-1")
    cod.listado = [{"id": "PROD-1", "id_personalizado": plan_prod.id_personalizado}]

    ids = exp.ejecutar(plan_prod, exp.Confirmacion(digest=plan_prod.digest), entorno_exp=ent_prod)

    assert len(ids) == 2
    assert sorted(c for c, _ in cod.enviados) == sorted(
        c for c in ("burofax", "correo", "sms") if c != primero.canal)


def test_H04_contenido_distinto_del_destinatario_no_se_da_por_completo(tmp_path):
    """Se expiden los tres canales con el código postal "28001". Antes de la segunda
    ejecución, el CRM corrige el código postal a "28099": la ETIQUETA del burofax
    (nombre · dirección, población) no incluye el cp, así que la huella vieja -- si
    se calcula sobre la etiqueta -- no distingue el domicilio corregido del viejo.
    Aprobar el plan con el cp nuevo debe mandar el burofax otra vez, a la dirección
    correcta -- nunca darlo por completo con el cp viejo."""
    cod = _CodicertFalso()
    ent = _entorno(tmp_path, cod)
    doc = _doc(tmp_path)
    plan_1 = exp.planificar("W-04AKM2", "OVC", doc, entorno_exp=ent, plaza="Madrid")
    ids_1 = exp.ejecutar(plan_1, exp.Confirmacion(digest=plan_1.digest), entorno_exp=ent)
    assert len(ids_1) == 3
    cod.listado = [{"id": i, "id_personalizado": plan_1.id_personalizado} for i in ids_1]
    cod.enviados = []

    ana_cp_nuevo = {**ANA, "cp": "28099"}
    ent_2 = _entorno(tmp_path, cod, partes=(ana_cp_nuevo,))
    plan_2 = exp.planificar("W-04AKM2", "OVC", doc, entorno_exp=ent_2, plaza="Madrid")

    ids_2 = exp.ejecutar(plan_2, exp.Confirmacion(digest=plan_2.digest), entorno_exp=ent_2)

    assert len(ids_2) == 1
    assert cod.enviados == [("burofax", plan_2.id_personalizado)]
    assert cod.destinatarios[-1]["cp"] == "28099"


def test_H04_formato_antiguo_sin_entorno_para_y_declara(tmp_path):
    """Una fila en el formato ANTERIOR a H-04 -- sin `entorno` ni `usuario` -- no se
    puede sostener como de este entorno ni de otro: no cuenta como hecho, no se
    ignora en silencio. `ejecutar` debe pararse y declararlo, no adivinar."""
    cod = _CodicertFalso()
    ent = _entorno(tmp_path, cod)
    plan = exp.planificar("W-04AKM2", "OVC", _doc(tmp_path), entorno_exp=ent, plaza="Madrid")

    ruta = tmp_path / "_codicert_intencion.jsonl"
    fila_vieja = json.dumps({"clave": "clave-vieja", "id_personalizado": plan.id_personalizado,
                             "canal": "burofax", "destinatario_huella": "abc123abc123",
                             "timestamp": "2026-09-01T00:00:00+00:00", "estado": "en_vuelo"})
    ruta.write_text(fila_vieja + "\n", encoding="utf-8", newline="\n")

    with pytest.raises(exp.ExpedicionError) as e:
        exp.ejecutar(plan, exp.Confirmacion(digest=plan.digest), entorno_exp=ent)
    assert "formato antiguo" in str(e.value).lower()
    assert cod.enviados == []
