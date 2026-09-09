"""F3 — escritura en el CRM: relacionar un correo entrante con un expediente y subir
sus adjuntos al gestor documental.

Cliente REST del módulo **`MailRoundcube`** de `api-crm-commons`, con la `x-api-key` que
`core/` ya usa. **No hace falta la sesión del webmail** (ni webview, ni `dataHash`, ni
credenciales IMAP): el contrato completo y su medición están en
``docs/INTEGRACION_SUDESPACHO.md §10.10`` y el diseño en la rev. 3 del spec F3.

La regla que gobierna este módulo, y de la que sale casi toda su forma:

    **Ningún `ok` sale de un código de estado.**

`POST /api/mail/relate/attachments` devuelve ``{"status": "success"}`` aunque no haga
nada —comprobado con los tres parámetros vacíos—, y `relate/selected` devuelve 200
también cuando el miembro destino no existe. Un cliente que se fíe del status archiva en
falso, y un archivado en falso es peor que un error: nadie lo audita. Por eso cada
escritura se confirma **releyendo** (relaciones vía ``findRelations``; documentos vía el
censo del gestor documental) y el resultado lleva ``verificado`` como campo propio,
distinto de ``ok``.

Solo lectura de PII: nada de lo que pasa por aquí se registra ni se envía al LLM.
"""

from __future__ import annotations

import base64
import logging
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

logger = logging.getLogger("feesdefender.procurador_relate")

# El CRM exige estos dos parámetros presentes en el relate (son el resto de la firma del
# plugin de Roundcube). Medido el 2026-09-07: vacíos funcionan. Es comportamiento
# observado, no contrato prometido — spec F3 rev.3 §8.1.
_COOKIES_VACIAS = ""
_DATAHASH_VACIO = ""

# La cuenta 0 es `noreply@sudespacho.net`: `findRelations` la rechaza con 400.
_CUENTA_NO_VALIDA = {"0", "", "None"}


# ---------------------------------------------------------------------------
# Tipos
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Adjunto:
    """Un adjunto tal como lo devuelve el relate. El ``att_id`` no preexiste."""
    att_id: str
    nombre_archivo: str


@dataclass(frozen=True)
class Relaciones:
    """Relaciones previas de un correo. ``error`` != None ⇒ no se pudo leer."""
    pares: set[tuple[str, int]] = field(default_factory=set)
    error: str | None = None

    def esta_relacionado_con(self, element: str, miembro: int) -> bool:
        return (element, int(miembro)) in self.pares


@dataclass(frozen=True)
class RelateResult:
    ok: bool
    verificado: bool
    mail_id: str | None = None
    adjuntos: list[Adjunto] = field(default_factory=list)
    ya_estaba: bool = False
    error: str | None = None


@dataclass(frozen=True)
class AdjuntarResult:
    ok: bool
    verificado: bool
    subidos: list[str] = field(default_factory=list)
    #: Ya estaban en el gestor documental: cuentan como archivados, no como subidos.
    ya_presentes: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass(frozen=True)
class ResultadoParcial:
    """El desenlace de UNA de las dos escrituras del archivado, con sus tres hechos.

    Los tres estados son distintos y ninguno se deduce de los otros dos (R1/H-06):

    - ``intentado=False`` — **no se escribió.** Si además trae ``error``, es que no se
      llegó a intentar y ahí está el motivo.
    - ``intentado=True, ok=False`` — **se intentó y falló**, y el efecto es
      **desconocido**: un timeout puede haber escrito. No es lo mismo que no intentarlo,
      y por eso son campos separados y no un booleano.
    - ``ok=True`` — se escribió. ``verificado`` dice si se **confirmó por relectura**,
      que es lo único que acredita el efecto: ningún `ok` sale de un código de estado.
    """

    intentado: bool = False
    ok: bool = False
    verificado: bool = False
    error: str | None = None


NO_INTENTADO = ResultadoParcial()


@dataclass(frozen=True)
class ArchivoResult:
    """Resultado del archivado, con la relación y los documentos POR SEPARADO.

    **No hay un `verificado` plano, y su ausencia es deliberada** (R1/H-06). Lo había, y
    se componía con el del adjuntar —``verificado=res.verificado``—, así que el positivo
    de la relación quedaba sobrescrito: una relación escrita y confirmada cuyo adjunto
    fallaba salía como `verificado=False`, y un fallo de emparejamiento salía como
    `verificado=True` **con cero documentos**. No significaba nada estable, y F6 consume
    esta traza para distinguir exactamente eso.

    ``ok`` es el archivado **como un todo**: relación escrita y documentos resueltos.
    """

    ok: bool
    relacion: ResultadoParcial = NO_INTENTADO
    documentos: ResultadoParcial = NO_INTENTADO
    mail_id: str | None = None
    subidos: list[str] = field(default_factory=list)
    #: Ya estaban en el gestor documental. Cuentan como archivados, no como subidos, y
    #: se conservan porque el §7 del spec los exige en la traza (antes se descartaban).
    ya_presentes: list[str] = field(default_factory=list)
    ya_estaba: bool = False
    a_revision: bool = False
    motivo: str | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Transporte
# ---------------------------------------------------------------------------

@contextmanager
def _transporte(transport: Any):
    """Cede un cliente con la interfaz de ``httpx.Client`` (``.get``/``.post``).

    En tests se inyecta un fake; en producción se abre un ``SudespachoClient`` (que ya
    lleva la ``x-api-key``) y se cierra al salir.
    """
    if transport is not None:
        yield transport
        return
    from .sync_sudespacho import SudespachoClient  # perezoso: no acoplar los tests
    client = SudespachoClient()
    try:
        yield client._client
    finally:
        try:
            client.__exit__(None, None, None)
        except Exception:  # pragma: no cover — cierre best-effort
            pass


def _con_angulos(message_id: str) -> str:
    """Forma en que el CRM almacena el ``uid``. Para `findRelations` da igual."""
    mid = (message_id or "").strip()
    return mid if mid.startswith("<") else f"<{mid}>"


def _items(payload: Any) -> list[dict]:
    """`element_registries` responde con ``items``; otras rutas, con ``hydra:member``."""
    if not isinstance(payload, dict):
        return []
    return payload.get("items") or payload.get("hydra:member") or []


def _valores(item: dict) -> dict[str, Any]:
    return {
        (v.get("property") or {}).get("name"): v.get("value")
        for v in item.get("values", [])
    }


# ---------------------------------------------------------------------------
# Lectura
# ---------------------------------------------------------------------------

def buscar_relaciones(message_id: str, *, account: str, transport: Any = None) -> Relaciones:
    """Relaciones previas del correo, por ``GET /api/mail/findRelations/{base64}``.

    El Message-ID va **codificado en base64 en la ruta** y la cuenta como query. El
    ``account`` no es un filtro de permisos: **determina el buzón donde se busca**, así
    que con la cuenta equivocada un correo relacionado se ve como no relacionado.

    Nunca lanza: un fallo se devuelve en ``error`` para que la bandeja degrade.
    """
    ruta = base64.b64encode(_normaliza(message_id).encode()).decode()
    with _transporte(transport) as t:
        r = t.get(f"/api/mail/findRelations/{ruta}", params={"account": str(account)})
    if r.status_code != 200:
        return Relaciones(error=f"findRelations → HTTP {r.status_code}: {(r.text or '')[:200]}")
    try:
        data = r.json()
    except Exception as exc:  # pragma: no cover — respuesta no-JSON
        return Relaciones(error=f"findRelations no devolvió JSON: {exc}")
    if not isinstance(data, dict):
        return Relaciones()  # [] = sin relaciones
    pares: set[tuple[str, int]] = set()
    for elemento, bloque in data.items():
        for clave, rel in ((bloque or {}).get("relacionados") or {}).items():
            miembro = (rel or {}).get("miembro", (rel or {}).get("id", clave))
            try:
                pares.add((elemento, int(miembro)))
            except (TypeError, ValueError):
                logger.warning("relación con miembro no numérico: %r", miembro)
    return Relaciones(pares=pares)


def _normaliza(message_id: str) -> str:
    return (message_id or "").strip()


def filtrar_ya_asignados(message_ids: Sequence[str], *, account: str,
                         transport: Any = None) -> set[str]:
    """Los del lote que **ya** están asignados a algún elemento (anti-duplicado).

    Una sola llamada para todo el lote. ``messageIds`` viaja como **array** aquí (a
    diferencia de ``tiene_adjuntos``, que lo toma como cadena), y ``account`` es
    obligatorio: sin él el CRM responde 400. Lo destapó el intento de campo del
    2026-09-07 — el 400 inicial solo nombraba `messageIds` porque **un error enumera
    lo que falta en esa llamada, no todo lo que el endpoint exige**.

    Ve solo lo que el CRM tiene indexado en su tabla ``mail``: para un correo recién
    llegado devuelve «no asignado» porque **no lo conoce**, no porque esté libre. Ese
    es el límite de toda esta vía (§2.8 del spec).
    """
    ids = [m for m in message_ids if m]
    if not ids:
        return set()
    with _transporte(transport) as t:
        r = t.post("/api/mail/findAssigned",
                   json={"messageIds": ids, "account": str(account)})
    if r.status_code != 200:
        logger.warning("findAssigned → HTTP %s; se trata como «ninguno asignado»", r.status_code)
        return set()
    data = r.json()
    return set(data) if isinstance(data, list) else set()


def tiene_adjuntos(message_id: str, *, account: str, transport: Any = None) -> bool:
    """¿El correo trae algo adjunto? ``messageIds`` va como **cadena**.

    Cuenta también los **inline** (logo de firma), así que un ``True`` no significa que
    haya nada archivable: para eso vale la lista que devuelve el relate.
    """
    with _transporte(transport) as t:
        r = t.post("/api/mail/attachments",
                   json={"messageIds": _normaliza(message_id), "account": str(account)})
    if r.status_code != 200:
        return False
    return bool((r.json() or {}).get("hasAttachments"))


def resolver_cuenta(message_id: str, *, transport: Any = None) -> str | None:
    """La cuenta del buzón donde el CRM indexó el correo — **por lectura**.

    El campo ``uid`` del elemento ``mail`` ES el Message-ID RFC, así que el registro se
    localiza filtrando por él y su campo ``cuenta`` es el ``account`` que piden el resto
    de operaciones. Devuelve ``None`` si no aparece o si la cuenta no es utilizable:
    **el llamante manda el correo a revisión, nunca adivina iterando cuentas.**
    """
    uid = _con_angulos(message_id)
    params = [
        ("properties[0]", "uid"), ("properties[1]", "cuenta"),
        ("filterGroup[condition]", "AND"),
        ("filterGroup[filterGroups][0][condition]", "AND"),
        ("filterGroup[filterGroups][0][filters][0][operator]", "equal"),
        ("filterGroup[filterGroups][0][filters][0][value]", uid),
        ("filterGroup[filterGroups][0][filters][0][property]", "uid"),
        ("itemsPerPage", "5"),
    ]
    with _transporte(transport) as t:
        r = t.get("/api/element_registries/mail", params=params)
    if r.status_code != 200:
        return None
    cuentas = {
        str(_valores(item).get("cuenta") or "")
        for item in _items(r.json())
    } - _CUENTA_NO_VALIDA
    if len(cuentas) != 1:
        # Cero: no indexado (o ilegible). Varias: el correo está en más de un buzón y
        # elegir «el primero» decide a ciegas qué buzón se lee y se verifica. Medido el
        # 2026-09-07: 0 de 12 Message-ID tienen más de un registro, así que hoy no pasa
        # — pero el código no puede depender de que siga sin pasar (R1/H-05).
        return None
    return cuentas.pop()


def _censo_gestor_documental(t: Any, element: str, miembro: int) -> list[str] | None:
    """Nombres de los documentos colgados del elemento, o ``None`` si no se pudo leer.

    La distinción importa: con un fallo de lectura tratado como «no hay documentos», un
    documento que ya estuviera con el nombre pedido se contaría como subido por nosotros
    (R1/H-02). Ante una lectura imposible el resultado es **indeterminado**, no éxito.
    """
    params = [
        ("properties[0]", "nombrefinal"), ("properties[1]", "id_carpeta"),
        ("itemsPerPage", "100"),
        ("filterGroup[condition]", "AND"),
        ("filterGroup[filterGroups][0][condition]", "AND"),
        ("filterGroup[filterGroups][0][filters][0][operator]", "associated"),
        ("filterGroup[filterGroups][0][filters][0][value]", str(miembro)),
        ("filterGroup[filterGroups][0][filters][0][property]", f"left.{element}.id"),
        ("return_totals", "true"),
    ]
    r = t.get("/api/element_registries/gdocu", params=params)
    if r.status_code != 200:
        return None
    try:
        payload = r.json()
    except Exception:
        return None
    if not isinstance(payload, dict) or ("items" not in payload and "hydra:member" not in payload):
        return None  # esquema no reconocido: `_items` lo daría por vacío
    return [str(_valores(i).get("nombrefinal") or "") for i in _items(payload)]


# ---------------------------------------------------------------------------
# Escritura
# ---------------------------------------------------------------------------

def relacionar(message_id: str, element: str, miembros: Sequence[int], *,
               account: str, transport: Any = None) -> RelateResult:
    """Relaciona el correo con el/los miembros del elemento. Idempotente.

    Devuelve el ``mail_id`` del correo en el CRM y sus adjuntos archivables, que es lo
    que consume ``adjuntar`` — **no preexisten**, los produce esta llamada.

    Verifica **releyendo**: el 200 del CRM no prueba nada (un miembro inexistente
    también responde 200 y no escribe).
    """
    miembros = [int(m) for m in miembros]
    with _transporte(transport) as t:
        previas = _leer_relaciones(t, message_id, account)
        if previas.error is None and all(previas.esta_relacionado_con(element, m) for m in miembros):
            return RelateResult(ok=True, verificado=True, ya_estaba=True)

        mail_id, adjuntos, error = _post_relate(t, message_id, element, miembros)
        if error:
            return RelateResult(ok=False, verificado=False, error=error)

        despues = _leer_relaciones(t, message_id, account)

    if despues.error is not None:
        return RelateResult(ok=False, verificado=False, mail_id=mail_id, adjuntos=adjuntos,
                            error=f"escritura sin verificar: {despues.error}")
    if not all(despues.esta_relacionado_con(element, m) for m in miembros):
        return RelateResult(
            ok=False, verificado=False, mail_id=mail_id, adjuntos=adjuntos,
            error=("el CRM respondió 200 pero la relectura no lo verifica "
                   f"({element}:{miembros} ausente); ¿existe el miembro?"))
    return RelateResult(ok=True, verificado=True, mail_id=mail_id, adjuntos=adjuntos)


def _post_relate(t: Any, message_id: str, element: str,
                 miembros: Sequence[int]) -> tuple[str | None, list[Adjunto], str | None]:
    """El POST del relate. Devuelve ``(mail_id, adjuntos, error)``.

    Es **idempotente en la relación** y su respuesta trae el manifiesto de adjuntos
    archivables, así que también sirve para recuperar los ``att_id`` de un correo que ya
    estaba relacionado — que es la única vía conocida de obtenerlos (spec §8, y lo que
    hace posible reanudar el adjuntar tras una muerte a medias).
    """
    cuerpo = {
        "messageIds": _normaliza(message_id),
        "relatedMembers": [int(m) for m in miembros],
        # SIN el sufijo `->izq` del plugin: con él, el CRM devuelve 500.
        "relatedElement": element,
        "cookies": _COOKIES_VACIAS,
        "dataHash": _DATAHASH_VACIO,
    }
    r = t.post("/api/mail/relate/selected", json=cuerpo)
    if r.status_code != 200:
        return None, [], f"relate → HTTP {r.status_code}: {(r.text or '')[:200]}"
    mail_id, adjuntos = _extraer_mail_y_adjuntos(r.json())
    return mail_id, adjuntos, None


def _leer_relaciones(t: Any, message_id: str, account: str) -> Relaciones:
    """`buscar_relaciones` reutilizando un transporte ya abierto."""
    return buscar_relaciones(message_id, account=account, transport=t)


def _extraer_mail_y_adjuntos(payload: Any) -> tuple[str | None, list[Adjunto]]:
    """``acumulaDatos.mailadjunto[mail_id] = [{id, nombre_archivo, enlace}]``."""
    acumula = ((payload or {}).get("acumulaDatos") or {}).get("mailadjunto") or {}
    for mail_id, lista in acumula.items():
        return str(mail_id), [
            Adjunto(str(a.get("id")), str(a.get("nombre_archivo") or ""))
            for a in (lista or [])
        ]
    return None, []


def adjuntar(element: str, miembro: int, mail_id: str,
             seleccion: Sequence[tuple[Adjunto, str]], *,
             folder_id: str, message_id: str, transport: Any = None) -> AdjuntarResult:
    """Sube al gestor documental **solo** los adjuntos de ``seleccion``.

    ``seleccion`` son pares ``(Adjunto, nombre_final)``; el nombre final es el que F4
    compone y con el que el CRM guarda el documento.

    **`ok` sale del censo, no del status.** El CRM contesta ``success`` con los
    parámetros vacíos, así que se cuentan los documentos del elemento antes y después y
    se exige que aparezcan los nombres pedidos.
    """
    if not seleccion:
        return AdjuntarResult(ok=True, verificado=True, subidos=[])

    nombres_pedidos = [nombre for _, nombre in seleccion]
    with _transporte(transport) as t:
        censo_antes = _censo_gestor_documental(t, element, miembro)
        if censo_antes is None:
            return AdjuntarResult(
                ok=False, verificado=False,
                error="no se pudo leer el censo del gestor documental antes de subir; "
                      "sin él, un documento preexistente pasaría por subido")
        antes = set(censo_antes)

        # Lo que ya está no se re-sube: la idempotencia del adjuntar no está probada y
        # re-postear podría duplicar el documento (spec §8.2).
        pendientes = [(a, n) for a, n in seleccion if n not in antes]
        ya_presentes = [n for n in nombres_pedidos if n in antes]
        if not pendientes:
            return AdjuntarResult(ok=True, verificado=True, subidos=[],
                                  ya_presentes=ya_presentes)

        cuerpo = {
            "datosRelacionados": {element: [int(miembro)]},
            "datosAdjuntos": {
                "seleccionado_adjunto": {str(mail_id): [a.att_id for a, _ in pendientes]},
                "nombre_adjunto": {str(mail_id): {a.att_id: n for a, n in pendientes}},
            },
            "folderId": str(folder_id),
            "messageIds": _normaliza(message_id),
        }
        r = t.post("/api/mail/relate/attachments", json=cuerpo)
        if r.status_code != 200:
            return AdjuntarResult(ok=False, verificado=False,
                                  error=f"adjuntar → HTTP {r.status_code}")

        censo_despues = _censo_gestor_documental(t, element, miembro)

    if censo_despues is None:
        return AdjuntarResult(
            ok=False, verificado=False,
            error="el CRM respondió «success» pero el censo posterior no se pudo leer: "
                  "efecto INDETERMINADO, no reintentar sin reconciliar")
    nuevos = set(censo_despues) - antes
    subidos = [n for _, n in pendientes if n in nuevos]
    if len(subidos) != len(pendientes):
        faltan = [n for _, n in pendientes if n not in subidos]
        return AdjuntarResult(
            ok=False, verificado=False, subidos=subidos, ya_presentes=ya_presentes,
            error=("el CRM respondió «success» pero el gestor documental no lo confirma; "
                   f"sin rastro de {len(faltan)} de {len(pendientes)}"))
    return AdjuntarResult(ok=True, verificado=True, subidos=subidos,
                          ya_presentes=ya_presentes)


# ---------------------------------------------------------------------------
# Orquestador
# ---------------------------------------------------------------------------

def archivar(message_id: str, element: str, miembro: int, *,
             adjuntos: Iterable[tuple[str, str]] = (),
             folder_id: str = "1", account: str | None = None,
             transport: Any = None) -> ArchivoResult:
    """Archiva un correo confirmado: relaciona y sube los adjuntos elegidos.

    ``adjuntos`` son pares ``(nombre_original, nombre_final)`` que produce F4. El
    ``att_id`` real solo se conoce **después** del relate, así que el join se hace por
    ``nombre_original`` **con guardarraíl**: si un nombre no casa, o si el correo trae
    dos adjuntos con el mismo nombre, el caso va a revisión — **nunca se adivina**, que
    subiría el documento equivocado al expediente de un cliente.
    """
    pedidos = list(adjuntos)
    with _transporte(transport) as t:
        cuenta = account or resolver_cuenta(message_id, transport=t)
        if not cuenta:
            return ArchivoResult(
                ok=False, a_revision=True,
                relacion=ResultadoParcial(error="cuenta sin resolver"),
                documentos=ResultadoParcial(error="cuenta sin resolver"),
                motivo="no se pudo resolver la cuenta del correo en el CRM "
                       "(¿no indexado todavía?); no se archiva a ciegas")

        rel = relacionar(message_id, element, [miembro], account=cuenta, transport=t)
        if not rel.ok:
            return ArchivoResult(
                ok=False, mail_id=rel.mail_id, error=rel.error,
                relacion=ResultadoParcial(intentado=True, ok=False,
                                          verificado=rel.verificado, error=rel.error))
        if not pedidos:
            # Nada que subir **porque no se pidió nada**. Que eso sea legítimo o sea el
            # inventario ausente lo decide el llamante: `archivar` no puede saberlo, y
            # tratarlo como «nada que subir» es el camino silencioso de H-01. La guarda
            # vive en el orquestador (spec §9.1).
            return ArchivoResult(
                ok=True, mail_id=rel.mail_id, ya_estaba=rel.ya_estaba,
                relacion=ResultadoParcial(intentado=True, ok=True, verificado=True),
                documentos=ResultadoParcial(error="no se pidió ningún adjunto"))

        mail_id, disponibles = rel.mail_id, rel.adjuntos
        if rel.ya_estaba:
            # «Ya relacionado» NO es «ya archivado» (R1/H-01): si el proceso murió entre
            # el relate y el adjuntar, la relación existe y los documentos no. Se pide el
            # manifiesto otra vez —el relate es idempotente— y el adjuntar decide, por
            # censo, qué falta de verdad.
            mail_id, disponibles, error = _post_relate(t, message_id, element, [miembro])
            if error:
                return ArchivoResult(
                    ok=False, ya_estaba=True, mail_id=None, error=error,
                    relacion=ResultadoParcial(intentado=True, ok=True, verificado=True),
                    documentos=ResultadoParcial(
                        error=f"sin manifiesto, no se intentó subir nada: {error}"))

        seleccion, problema = _emparejar(disponibles, pedidos)
        if problema:
            return ArchivoResult(
                ok=False, mail_id=mail_id, ya_estaba=rel.ya_estaba,
                a_revision=True, motivo=problema,
                relacion=ResultadoParcial(intentado=True, ok=True, verificado=True),
                documentos=ResultadoParcial(error=problema))

        res = adjuntar(element, miembro, mail_id or "", seleccion,
                       folder_id=folder_id, message_id=message_id, transport=t)

    return ArchivoResult(
        ok=res.ok, mail_id=mail_id, subidos=res.subidos,
        ya_presentes=res.ya_presentes, ya_estaba=rel.ya_estaba, error=res.error,
        relacion=ResultadoParcial(intentado=True, ok=True, verificado=True),
        documentos=ResultadoParcial(intentado=True, ok=res.ok,
                                    verificado=res.verificado, error=res.error))


def _emparejar(disponibles: Sequence[Adjunto],
               pedidos: Sequence[tuple[str, str]]) -> tuple[list[tuple[Adjunto, str]], str | None]:
    """Join F4↔relate por ``nombre_archivo``, con guardarraíl.

    Devuelve ``(selección, None)`` o ``([], motivo)``. Cualquier ambigüedad para el
    proceso: no hay forma segura de saber cuál de dos adjuntos homónimos quiso F4.
    """
    por_nombre: dict[str, list[Adjunto]] = {}
    for a in disponibles:
        por_nombre.setdefault(a.nombre_archivo, []).append(a)

    seleccion: list[tuple[Adjunto, str]] = []
    for original, final in pedidos:
        candidatos = por_nombre.get(original, [])
        if not candidatos:
            return [], (f"el adjunto {original!r} no está entre los que devolvió el relate "
                        f"({[a.nombre_archivo for a in disponibles]}); a revisión")
        if len(candidatos) > 1:
            return [], (f"el correo trae {len(candidatos)} adjuntos llamados {original!r}: "
                        "el join por nombre es ambiguo; a revisión")
        seleccion.append((candidatos[0], final))
    return seleccion, None
