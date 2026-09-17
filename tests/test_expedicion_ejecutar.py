"""La puerta humana: sin confirmación válida no sale nada, y un plan rancio se rechaza."""
from __future__ import annotations

import datetime as dt
import json
from decimal import Decimal

import pytest

from core import expedicion_certificada as exp

ANA = {"nombre": "ANA LOPEZ", "direccion": "C Mayor 1", "poblacion": "Madrid",
       "provincia": "Madrid", "cp": "28001", "email": "ana@x.es", "movil": "665130883"}
MAR = {"nombre": "MAR GIL", "direccion": "Av Sur 9", "poblacion": "Sevilla",
       "provincia": "Sevilla", "cp": "41001", "email": "mar@x.es", "movil": "688222333"}


class _CodicertFalso:
    """Doble del transporte. Cuenta lo que se manda y no toca la red."""

    def __init__(self, credito=Decimal("100"), listado=()):
        self.credito_ = credito
        self.listado = list(listado)
        self.enviados: list[tuple[str, str]] = []
        self._contador = 0  # cada envío real tiene su propio IdEnvio, nunca repetido

    def credito(self): return self.credito_
    def listar(self, **_): return list(self.listado)

    def enviar_burofax(self, **kw):
        self._contador += 1
        self.enviados.append(("burofax", kw["id_personalizado"])); return f"B{self._contador}"

    def enviar_eec(self, **kw):
        self._contador += 1
        self.enviados.append((kw["tipo_entrega"], kw["id_personalizado"])); return f"E{self._contador}"


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
    bloquear el envío en vez de arriesgar un duplicado."""
    cod = _CodicertFalso()
    ent = _entorno(tmp_path, cod)
    exp.RegistroIntencion(tmp_path / "_codicert_intencion.jsonl").anotar(
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
    """
    cod = _CodicertFalso()
    ent = _entorno(tmp_path, cod, partes=(ANA, MAR))
    plan = exp.planificar("W-04AKM2", "OVC", _doc(tmp_path), entorno_exp=ent, plaza="Madrid")
    assert len(plan.envios) == 6  # 2 partes x (correo + sms + burofax), domicilios distintos

    reg = exp.RegistroIntencion(tmp_path / "_codicert_intencion.jsonl", ahora=ent.ahora)
    ya_hechos = plan.envios[:2]          # "envíos 1 y 2": ya se mandaron y están en la plataforma
    ids_plataforma = []
    for numero, e in enumerate(ya_hechos, start=1):
        clave = reg.anotar(plan.id_personalizado, e.canal, e.etiqueta)
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
    mandaron 2 de 6"."""
    cod = _CodicertFalso()
    ent = _entorno(tmp_path, cod, partes=(ANA, MAR))
    plan = exp.planificar("W-04AKM2", "OVC", _doc(tmp_path), entorno_exp=ent, plaza="Madrid")
    reg = exp.RegistroIntencion(tmp_path / "_codicert_intencion.jsonl", ahora=ent.ahora)
    ids_plataforma = []
    for numero, e in enumerate(plan.envios, start=1):
        clave = reg.anotar(plan.id_personalizado, e.canal, e.etiqueta)
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
