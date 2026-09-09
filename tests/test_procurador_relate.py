"""F3 — cliente REST del módulo de correo del CRM (`core.procurador_relate`).

Sin red: un transporte fake con la interfaz de ``httpx.Client`` (``.get``/``.post``)
captura las peticiones y devuelve respuestas canned **con la forma real medida** el
2026-09-07 (spec F3 rev. 3 §2), incluida la ruta anidada
``acumulaDatos.mailadjunto[mail_id]``.

El caso que gobierna este fichero es
``test_adjuntar_con_success_pero_censo_sin_cambios_no_es_ok``: el CRM devuelve
``{"status":"success"}`` haga lo que haga, así que un cliente que se fíe del status
archiva en falso y nadie se entera.
"""

from __future__ import annotations

import base64
import json

import pytest

from core.procurador_relate import (
    Adjunto,
    adjuntar,
    archivar,
    buscar_relaciones,
    filtrar_ya_asignados,
    relacionar,
    resolver_cuenta,
    tiene_adjuntos,
)

MSG = "<abc123@dominio.example>"
MSG_PELADO = "abc123@dominio.example"


# --------------------------------------------------------------------------
# Transporte fake — interfaz de httpx.Client
# --------------------------------------------------------------------------

class _Resp:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload) if payload is not None else ""

    def json(self):
        return self._payload


class FakeTransport:
    """Captura ``(método, path, params|json)`` y responde por ruta.

    ``rutas`` mapea un fragmento de path → callable(params_o_body) -> _Resp, o
    directamente un payload. Lo que no esté mapeado devuelve 404, para que un test
    que llame a algo inesperado se entere.
    """

    def __init__(self, **rutas):
        self.rutas = rutas
        self.llamadas: list[tuple[str, str, object]] = []

    def _resolver(self, metodo, path, carga):
        self.llamadas.append((metodo, path, carga))
        for fragmento, respuesta in self.rutas.items():
            if fragmento in path:
                if callable(respuesta):
                    return respuesta(carga)
                return _Resp(respuesta)
        return _Resp({"detail": f"sin ruta fake para {path}"}, status_code=404)

    def get(self, path, params=None):
        return self._resolver("GET", path, params)

    def post(self, path, json=None):
        return self._resolver("POST", path, json)

    def cuerpos(self, fragmento):
        """Cuerpos enviados a los paths que contienen ``fragmento``."""
        return [c for _, p, c in self.llamadas if fragmento in p]


def secuencia(*payloads):
    """Respuestas sucesivas para una misma ruta.

    Hace falta siempre que una ruta se consulte **antes y después** de escribir: el
    pre-chequeo de idempotencia y la verificación por relectura llaman las dos a
    ``findRelations``, y un payload fijo confundiría «ya estaba» con «lo escribí yo».
    La última respuesta se repite si se piden más.
    """
    restantes = list(payloads)

    def _servir(_carga):
        p = restantes.pop(0) if len(restantes) > 1 else restantes[0]
        return _Resp(p)

    return _servir


SIN_RELACION: list = []
CON_636 = {"extrajudiciales": {"nombre": "Extrajudiciales",
                               "relacionados": {"636": {"id": 636, "miembro": 636,
                                                        "elemento": "extrajudiciales"}}}}


def _relate_ok(mail_id="464001", adjuntos=(("183615", "auto.pdf"), ("183616", "cedula.pdf"))):
    """Respuesta del relate con la forma real: acumulaDatos.mailadjunto[mail_id]."""
    return {
        "acumulaDatos": {
            "mailadjunto": {
                mail_id: [
                    {"id": att, "nombre_archivo": nombre, "enlace": "https://s3.example/x"}
                    for att, nombre in adjuntos
                ]
            }
        }
    }


def _gdocu(nombres):
    """Censo del gestor documental: element_registries devuelve items/values."""
    return {
        "totalItems": float(len(nombres)),
        "items": [
            {"id": 1000 + i, "values": [{"property": {"name": "nombrefinal"}, "value": n}]}
            for i, n in enumerate(nombres)
        ],
    }


def _mail_registry(cuenta="20", uid=MSG):
    return {
        "totalItems": 1.0,
        "items": [{
            "id": 464001,
            "values": [
                {"property": {"name": "uid"}, "value": uid},
                {"property": {"name": "cuenta"}, "value": cuenta},
            ],
        }],
    }


# --------------------------------------------------------------------------
# buscar_relaciones — findRelations
# --------------------------------------------------------------------------

def test_buscar_relaciones_codifica_el_message_id_en_base64_en_la_ruta():
    t = FakeTransport(findRelations={"extrajudiciales": {
        "nombre": "Extrajudiciales",
        "relacionados": {"636": {"id": 636, "miembro": 636, "elemento": "extrajudiciales"}}}})

    buscar_relaciones(MSG, account="20", transport=t)

    _, path, params = t.llamadas[0]
    esperado = base64.b64encode(MSG.encode()).decode()
    assert esperado in path, f"el Message-ID debe ir en base64 en la ruta; path={path}"
    assert params == {"account": "20"}


def test_buscar_relaciones_devuelve_los_pares_elemento_miembro():
    t = FakeTransport(findRelations={"extrajudiciales": {
        "nombre": "Extrajudiciales",
        "relacionados": {"636": {"id": 636, "miembro": 636, "elemento": "extrajudiciales"}}}})

    rel = buscar_relaciones(MSG, account="20", transport=t)

    assert rel.pares == {("extrajudiciales", 636)}
    assert rel.esta_relacionado_con("extrajudiciales", 636)
    assert not rel.esta_relacionado_con("expedientes_judiciales", 636)


def test_buscar_relaciones_sin_relaciones_devuelve_conjunto_vacio():
    t = FakeTransport(findRelations=[])
    rel = buscar_relaciones(MSG, account="20", transport=t)
    assert rel.pares == set()


def test_buscar_relaciones_acepta_el_message_id_sin_angulos():
    """`gmail_source` guarda el Message-ID pelado; el CRM acepta las dos formas."""
    t = FakeTransport(findRelations=[])
    buscar_relaciones(MSG_PELADO, account="20", transport=t)
    _, path, _ = t.llamadas[0]
    assert base64.b64encode(MSG_PELADO.encode()).decode() in path


def test_buscar_relaciones_con_http_400_no_lanza_y_marca_el_fallo():
    """Cuenta inválida → 400. La tarjeta degrada, no rompe el runner."""
    t = FakeTransport(findRelations=lambda _: _Resp({"detail": "account is empty"}, 400))
    rel = buscar_relaciones(MSG, account="0", transport=t)
    assert rel.error is not None
    assert rel.pares == set()


# --------------------------------------------------------------------------
# filtrar_ya_asignados — anti-duplicado en lote
# --------------------------------------------------------------------------

def test_filtrar_ya_asignados_manda_un_array_y_devuelve_los_ya_archivados():
    otro = "<zzz@dominio.example>"
    t = FakeTransport(findAssigned=[MSG])

    ya = filtrar_ya_asignados([MSG, otro], account="20", transport=t)

    assert ya == {MSG}
    assert t.cuerpos("findAssigned")[0]["messageIds"] == [MSG, otro], \
        "findAssigned toma un ARRAY (a diferencia de attachments, que toma string)"


def test_filtrar_ya_asignados_exige_account_como_el_resto():
    """Medido en campo el 2026-09-07: sin `account` el CRM responde 400.

    El primer contrato que escribí lo omitía porque el 400 inicial solo nombraba
    `messageIds`. Un error que enumera parámetros enumera **los que faltan en esa
    llamada**, no todos los que el endpoint exige.
    """
    t = FakeTransport(findAssigned=[])
    filtrar_ya_asignados([MSG], account="20", transport=t)
    assert t.cuerpos("findAssigned")[0]["account"] == "20"


def test_filtrar_ya_asignados_con_lote_vacio_no_llama_al_crm():
    t = FakeTransport(findAssigned=[])
    assert filtrar_ya_asignados([], account="20", transport=t) == set()
    assert t.llamadas == []


# --------------------------------------------------------------------------
# tiene_adjuntos
# --------------------------------------------------------------------------

def test_tiene_adjuntos_manda_message_ids_como_cadena():
    t = FakeTransport(**{"mail/attachments": {"status": "success", "hasAttachments": True, "errors": []}})
    assert tiene_adjuntos(MSG, account="20", transport=t) is True
    assert t.cuerpos("mail/attachments")[0]["messageIds"] == MSG


# --------------------------------------------------------------------------
# resolver_cuenta — por lectura, no por configuración
# --------------------------------------------------------------------------

def test_resolver_cuenta_lee_el_campo_cuenta_del_elemento_mail():
    t = FakeTransport(element_registries=_mail_registry(cuenta="20"))
    assert resolver_cuenta(MSG, transport=t) == "20"


def test_resolver_cuenta_ignora_la_cuenta_0_que_el_crm_rechaza():
    """La cuenta 0 (noreply) da 400 en findRelations: no vale como respuesta."""
    t = FakeTransport(element_registries=_mail_registry(cuenta="0"))
    assert resolver_cuenta(MSG, transport=t) is None


def test_resolver_cuenta_sin_registro_devuelve_none_en_vez_de_adivinar():
    t = FakeTransport(element_registries={"totalItems": 0.0, "items": []})
    assert resolver_cuenta(MSG, transport=t) is None


# --------------------------------------------------------------------------
# relacionar — relate/selected
# --------------------------------------------------------------------------

def test_relacionar_envia_relatedelement_sin_el_sufijo_izq_del_plugin():
    """Con `->izq` el CRM devuelve 500: ese sufijo es del plugin, no de la API."""
    t = FakeTransport(**{"relate/selected": _relate_ok(),
                         "findRelations": secuencia(SIN_RELACION, CON_636)})

    relacionar(MSG, "extrajudiciales", [636], account="20", transport=t)

    cuerpo = t.cuerpos("relate/selected")[0]
    assert cuerpo["relatedElement"] == "extrajudiciales"
    assert "->" not in cuerpo["relatedElement"]


def test_relacionar_extrae_el_mail_id_y_los_adjuntos_de_la_ruta_anidada():
    t = FakeTransport(**{"relate/selected": _relate_ok(),
                         "findRelations": secuencia(SIN_RELACION, CON_636)})

    res = relacionar(MSG, "extrajudiciales", [636], account="20", transport=t)

    assert res.ok and res.verificado
    assert res.mail_id == "464001"
    assert res.adjuntos == [Adjunto("183615", "auto.pdf"), Adjunto("183616", "cedula.pdf")]


def test_relacionar_manda_cookies_y_datahash_porque_el_crm_los_exige_presentes():
    t = FakeTransport(**{"relate/selected": _relate_ok(),
                         "findRelations": secuencia(SIN_RELACION, CON_636)})

    relacionar(MSG, "extrajudiciales", [636], account="20", transport=t)

    cuerpo = t.cuerpos("relate/selected")[0]
    assert "cookies" in cuerpo and "dataHash" in cuerpo


def test_relacionar_con_200_pero_relectura_que_no_confirma_no_es_ok():
    """El 200 no prueba la escritura: un miembro inexistente también devuelve 200."""
    t = FakeTransport(**{"relate/selected": _relate_ok(), "findRelations": []})

    res = relacionar(MSG, "extrajudiciales", [636], account="20", transport=t)

    assert res.ok is False
    assert res.verificado is False
    assert "verific" in (res.error or "").lower()


def test_relacionar_ya_relacionado_no_vuelve_a_postear():
    t = FakeTransport(**{"findRelations": CON_636, "relate/selected": _relate_ok()})

    res = relacionar(MSG, "extrajudiciales", [636], account="20", transport=t)

    assert res.ok and res.ya_estaba
    assert t.cuerpos("relate/selected") == [], "no debe re-relacionar lo ya relacionado"


# --------------------------------------------------------------------------
# adjuntar — relate/attachments, la guarda inerte
# --------------------------------------------------------------------------

def test_adjuntar_con_success_pero_censo_sin_cambios_no_es_ok():
    """EL caso del fichero. `relate/attachments` devuelve success pase lo que pase."""
    t = FakeTransport(**{"relate/attachments": {"status": "success", "errors": []},
                         "element_registries/gdocu": _gdocu([])})

    res = adjuntar("extrajudiciales", 636, "464001",
                   [(Adjunto("183615", "auto.pdf"), "2026-09-07 - Auto - x.pdf")],
                   folder_id="1", message_id=MSG, transport=t)

    assert res.ok is False, "un success sin documento nuevo NO es un archivado"
    assert res.verificado is False
    assert res.subidos == []


def test_adjuntar_ok_cuando_el_censo_confirma_el_documento():
    nombre = "2026-09-07 - Auto - nombramiento administrador.pdf"
    censos = iter([_gdocu([]), _gdocu([nombre])])
    t = FakeTransport(**{"relate/attachments": {"status": "success", "errors": []},
                         "element_registries/gdocu": lambda _: _Resp(next(censos))})

    res = adjuntar("extrajudiciales", 636, "464001",
                   [(Adjunto("183615", "auto.pdf"), nombre)],
                   folder_id="1", message_id=MSG, transport=t)

    assert res.ok and res.verificado
    assert res.subidos == [nombre]


def test_adjuntar_solo_manda_los_seleccionados():
    nombre = "elegido.pdf"
    censos = iter([_gdocu([]), _gdocu([nombre])])
    t = FakeTransport(**{"relate/attachments": {"status": "success", "errors": []},
                         "element_registries/gdocu": lambda _: _Resp(next(censos))})

    adjuntar("extrajudiciales", 636, "464001",
             [(Adjunto("183615", "auto.pdf"), nombre)],
             folder_id="1", message_id=MSG, transport=t)

    cuerpo = t.cuerpos("relate/attachments")[0]
    assert cuerpo["datosAdjuntos"]["seleccionado_adjunto"]["464001"] == ["183615"]
    assert cuerpo["datosAdjuntos"]["nombre_adjunto"]["464001"] == {"183615": nombre}
    assert cuerpo["datosRelacionados"] == {"extrajudiciales": [636]}
    assert cuerpo["folderId"] == "1"


def test_adjuntar_sin_adjuntos_seleccionados_no_llama_al_crm():
    t = FakeTransport(**{"relate/attachments": {"status": "success"}})
    res = adjuntar("extrajudiciales", 636, "464001", [], folder_id="1",
                   message_id=MSG, transport=t)
    assert res.ok and res.subidos == []
    assert t.cuerpos("relate/attachments") == []


def test_adjuntar_censo_con_documento_distinto_del_pedido_no_cuenta():
    """Si aparece un documento pero no el que pedimos, no está archivado lo nuestro."""
    censos = iter([_gdocu([]), _gdocu(["otra cosa.pdf"])])
    t = FakeTransport(**{"relate/attachments": {"status": "success", "errors": []},
                         "element_registries/gdocu": lambda _: _Resp(next(censos))})

    res = adjuntar("extrajudiciales", 636, "464001",
                   [(Adjunto("183615", "auto.pdf"), "el mio.pdf")],
                   folder_id="1", message_id=MSG, transport=t)

    assert res.ok is False
    assert res.subidos == []


# --------------------------------------------------------------------------
# archivar — orquestador
# --------------------------------------------------------------------------

def test_archivar_sin_cuenta_resoluble_va_a_revision_y_no_escribe():
    t = FakeTransport(element_registries={"totalItems": 0.0, "items": []})

    res = archivar(MSG, "extrajudiciales", 636, adjuntos=[], folder_id="1", transport=t)

    assert res.ok is False
    assert res.a_revision is True
    assert t.cuerpos("relate/selected") == []


def test_archivar_encadena_relate_y_adjuntar_con_los_ids_del_relate():
    nombre = "2026-09-07 - Auto - x.pdf"
    censos = iter([_gdocu([]), _gdocu([nombre])])

    def por_ruta(carga):
        return _Resp(next(censos))

    t = FakeTransport(**{
        "element_registries/mail": _mail_registry(cuenta="20"),
        "element_registries/gdocu": por_ruta,
        "findRelations": secuencia(SIN_RELACION, CON_636),
        "relate/selected": _relate_ok(adjuntos=(("183615", "auto.pdf"),)),
        "relate/attachments": {"status": "success", "errors": []},
    })

    res = archivar(MSG, "extrajudiciales", 636,
                   adjuntos=[("auto.pdf", nombre)], folder_id="1", transport=t)

    # MIGRADO con el reshape de H-06: donde había un `verificado` plano —que en
    # realidad era el del ADJUNTAR— ahora se exigen LOS DOS. Es una aserción más
    # ESTRICTA, no relajada: antes un fallo de la relación quedaba tapado.
    assert res.ok and res.relacion.verificado and res.documentos.verificado
    assert res.mail_id == "464001"
    cuerpo = t.cuerpos("relate/attachments")[0]
    assert cuerpo["datosAdjuntos"]["seleccionado_adjunto"]["464001"] == ["183615"], \
        "el att_id sale del relate, no de F4"


def test_archivar_con_nombre_de_adjunto_que_no_casa_va_a_revision_sin_adivinar():
    """El join F4↔relate es por nombre_archivo: si no casa, se para (spec §10)."""
    t = FakeTransport(**{
        "element_registries/mail": _mail_registry(cuenta="20"),
        "element_registries/gdocu": _gdocu([]),
        "findRelations": secuencia(SIN_RELACION, CON_636),
        "relate/selected": _relate_ok(adjuntos=(("183615", "auto.pdf"),)),
        "relate/attachments": {"status": "success", "errors": []},
    })

    res = archivar(MSG, "extrajudiciales", 636,
                   adjuntos=[("NO-EXISTE.pdf", "x.pdf")], folder_id="1", transport=t)

    assert res.a_revision is True
    assert t.cuerpos("relate/attachments") == [], "no adjuntar a ciegas si el join es ambiguo"


def test_archivar_con_nombres_duplicados_en_el_correo_va_a_revision():
    """Dos adjuntos con el mismo nombre hacen el join por nombre ambiguo."""
    t = FakeTransport(**{
        "element_registries/mail": _mail_registry(cuenta="20"),
        "element_registries/gdocu": _gdocu([]),
        "findRelations": secuencia(SIN_RELACION, CON_636),
        "relate/selected": _relate_ok(adjuntos=(("1", "doc.pdf"), ("2", "doc.pdf"))),
        "relate/attachments": {"status": "success", "errors": []},
    })

    res = archivar(MSG, "extrajudiciales", 636,
                   adjuntos=[("doc.pdf", "renombrado.pdf")], folder_id="1", transport=t)

    assert res.a_revision is True
    assert t.cuerpos("relate/attachments") == []


# ---------------------------------------------------------------------------
# Remediaciones de la R1 adversarial (2026-09-07)
# ---------------------------------------------------------------------------

def test_h01_reanudacion_correo_ya_relacionado_pero_con_documentos_sin_subir():
    """H-01: «ya relacionado» NO es «ya archivado».

    Si el proceso muere entre el relate y el adjuntar, al volver el correo consta
    relacionado y los documentos no están. Darlo por archivado los pierde para
    siempre, en silencio, que es el peor modo de fallo posible aquí.
    """
    nombre = "2026-09-07 - Auto - x.pdf"
    censos = iter([_gdocu([]), _gdocu([nombre])])
    t = FakeTransport(**{
        "element_registries/mail": _mail_registry(cuenta="20"),
        "element_registries/gdocu": lambda _: _Resp(next(censos)),
        "findRelations": CON_636,                       # ya estaba relacionado
        "relate/selected": _relate_ok(adjuntos=(("183615", "auto.pdf"),)),
        "relate/attachments": {"status": "success", "errors": []},
    })

    res = archivar(MSG, "extrajudiciales", 636,
                   adjuntos=[("auto.pdf", nombre)], folder_id="1", transport=t)

    assert res.ya_estaba, "la relación previa se reconoce"
    # MIGRADO con el reshape de H-06, y aquí gana precisión de verdad: este es el
    # test de la REANUDACIÓN —relación ya hecha, documentos pendientes—, así que
    # poder afirmar los dos hechos por separado es justo lo que el caso quería
    # decir y un booleano único no podía.
    assert res.ok and res.relacion.verificado and res.documentos.verificado
    assert res.subidos == [nombre], "y aun así se completan los documentos que faltaban"


def test_h01_ya_relacionado_y_documento_ya_presente_no_re_sube():
    """La otra mitad: si el documento ya está, no se vuelve a subir (duplicaría)."""
    nombre = "ya-esta.pdf"
    t = FakeTransport(**{
        "element_registries/mail": _mail_registry(cuenta="20"),
        "element_registries/gdocu": _gdocu([nombre]),
        "findRelations": CON_636,
        "relate/selected": _relate_ok(adjuntos=(("183615", "auto.pdf"),)),
        "relate/attachments": {"status": "success", "errors": []},
    })

    res = archivar(MSG, "extrajudiciales", 636,
                   adjuntos=[("auto.pdf", nombre)], folder_id="1", transport=t)

    assert res.ok and res.ya_estaba
    assert t.cuerpos("relate/attachments") == [], "no re-subir lo que ya está"


def test_h02_censo_ilegible_no_es_censo_vacio():
    """H-02: si la lectura del censo falla, un documento preexistente parecería nuevo.

    Con `antes` ilegible tratado como `[]`, cualquier documento que ya estuviera con
    el nombre pedido se contaría como subido por nosotros. Ante una lectura que no se
    puede hacer, el resultado es indeterminado, no éxito.
    """
    nombre = "x.pdf"
    respuestas = iter([_Resp({"detail": "boom"}, 500), _Resp(_gdocu([nombre]))])
    t = FakeTransport(**{
        "relate/attachments": {"status": "success", "errors": []},
        "element_registries/gdocu": lambda _: next(respuestas),
    })

    res = adjuntar("extrajudiciales", 636, "464001",
                   [(Adjunto("183615", "auto.pdf"), nombre)],
                   folder_id="1", message_id=MSG, transport=t)

    assert res.ok is False
    assert res.verificado is False
    assert "censo" in (res.error or "").lower() or "leer" in (res.error or "").lower()


def test_h05_varios_registros_mail_para_un_message_id_van_a_revision():
    """H-05: medido 0 de 12 hoy, pero el diseño no puede elegir «el primero» a ciegas.

    Si el CRM llegara a indexar el mismo correo en varias cuentas, la que se elija
    determina qué buzón se lee y se verifica. Ante ambigüedad, revisión.
    """
    dos = {"totalItems": 2.0, "items": [
        {"id": 1, "values": [{"property": {"name": "uid"}, "value": MSG},
                             {"property": {"name": "cuenta"}, "value": "20"}]},
        {"id": 2, "values": [{"property": {"name": "uid"}, "value": MSG},
                             {"property": {"name": "cuenta"}, "value": "15"}]},
    ]}
    t = FakeTransport(**{"element_registries/mail": dos})
    assert resolver_cuenta(MSG, transport=t) is None


def test_h02_censo_posterior_ilegible_es_indeterminado_no_exito():
    """La otra mitad de H-02, que el arnés de mutación destapó.

    Si la lectura de después falla, el POST ya salió: el efecto es **desconocido**.
    Ni éxito (podría no haber subido) ni un fallo que invite a reintentar (podría
    haber subido, y reintentar duplicaría). Se dice indeterminado y se reconcilia.
    """
    respuestas = iter([_Resp(_gdocu([])), _Resp({"detail": "boom"}, 500)])
    t = FakeTransport(**{
        "relate/attachments": {"status": "success", "errors": []},
        "element_registries/gdocu": lambda _: next(respuestas),
    })

    res = adjuntar("extrajudiciales", 636, "464001",
                   [(Adjunto("183615", "auto.pdf"), "x.pdf")],
                   folder_id="1", message_id=MSG, transport=t)

    assert res.ok is False and res.verificado is False
    assert "indetermin" in (res.error or "").lower()
    assert "reintentar" in (res.error or "").lower(), \
        "el mensaje tiene que decir explícitamente que NO se reintente a ciegas"


# ---------------------------------------------------------------------------
# Judicial — medido en vivo el 2026-09-07 contra el judicial de prueba 683
# ---------------------------------------------------------------------------

CON_683_JUD = {"expedientes_judiciales": {
    "nombre": "Expedientes Judiciales",
    "relacionados": {"683": {"id": 683, "miembro": 683,
                             "elemento": "expedientes_judiciales"}}}}


def test_judicial_usa_el_slug_sin_sufijo_igual_que_extrajudicial():
    """`expedientes_judiciales->izq` y el alias `judiciales` dan 500 en REST (medido)."""
    t = FakeTransport(**{"relate/selected": _relate_ok(),
                         "findRelations": secuencia(SIN_RELACION, CON_683_JUD)})

    res = relacionar(MSG, "expedientes_judiciales", [683], account="15", transport=t)

    assert res.ok and res.verificado
    assert t.cuerpos("relate/selected")[0]["relatedElement"] == "expedientes_judiciales"


def test_la_idempotencia_es_por_PAR_no_por_estar_relacionado_con_algo():
    """Un correo ya relacionado con OTRO expediente sí debe relacionarse con este.

    Medido en vivo: el correo constaba en el extrajudicial 636 y el relate contra el
    judicial 683 escribió igual. Si el pre-chequeo mirase «¿tiene alguna relación?» en
    vez de «¿tiene ESTA?», habría contestado «ya estaba» y no habría archivado nada —
    y un correo puede pertenecer a dos asuntos a la vez.
    """
    ya_con_otro = {"extrajudiciales": {"relacionados": {"636": {"miembro": 636}}}}
    ambos = {"extrajudiciales": {"relacionados": {"636": {"miembro": 636}}},
             "expedientes_judiciales": {"relacionados": {"683": {"miembro": 683}}}}
    t = FakeTransport(**{"relate/selected": _relate_ok(),
                         "findRelations": secuencia(ya_con_otro, ambos)})

    res = relacionar(MSG, "expedientes_judiciales", [683], account="15", transport=t)

    assert res.ya_estaba is False, "una relación con OTRO elemento no es esta relación"
    assert res.ok and res.verificado
    assert len(t.cuerpos("relate/selected")) == 1, "tiene que postear"


def test_el_censo_del_gestor_filtra_por_el_elemento_correcto():
    """`left.{element}.id`: con judicial no puede colarse el censo del extrajudicial."""
    censos = iter([_gdocu([]), _gdocu(["x.pdf"])])
    t = FakeTransport(**{"relate/attachments": {"status": "success", "errors": []},
                         "element_registries/gdocu": lambda _: _Resp(next(censos))})

    adjuntar("expedientes_judiciales", 683, "464006",
             [(Adjunto("1", "a.pdf"), "x.pdf")],
             folder_id="312", message_id=MSG, transport=t)

    params = dict(t.llamadas[0][2])
    assert params["filterGroup[filterGroups][0][filters][0][property]"] == \
        "left.expedientes_judiciales.id"
    assert params["filterGroup[filterGroups][0][filters][0][value]"] == "683"


# --------------------------------------------------------------------------
# H-06 (R1 adversarial) — los TRES hechos del archivado, por separado
#
# `archivar` componía su resultado así:
#
#     ArchivoResult(ok=res.ok, verificado=res.verificado, ...)   # res = el ADJUNTAR
#
# así que el `verificado` de la relación quedaba **sobrescrito** por el de los
# documentos. Consecuencias medidas en el código: relación verificada + adjunto que
# falla ⇒ `verificado=False`, y el positivo de la relación **se borra**; y un fallo de
# emparejamiento ⇒ `verificado=True` **con cero documentos**. Es decir, `verificado`
# no significaba nada estable.
#
# F6 —el control de calidad— consume esta traza y tiene que poder distinguir
# «no escribí» / «escribí y no lo confirmé» / «escribí y lo confirmé», y hacerlo
# **por separado** para la relación y para los documentos. Ninguno de los tests de
# `archivar` de arriba ejercitaba el caso mixto: este bloque tapa ese agujero.
# --------------------------------------------------------------------------

def _archivar_con(relate_ok=True, adjuntar_status=200, censo_final=None, nombre="x.pdf"):
    """Escenario de `archivar` con el relate verificable y el adjuntar parametrizado."""
    censos = iter([_gdocu([]), _gdocu(censo_final if censo_final is not None else [])])
    t = FakeTransport(**{
        "element_registries/mail": _mail_registry(cuenta="20"),
        "element_registries/gdocu": lambda _: _Resp(next(censos)),
        "findRelations": secuencia(SIN_RELACION, CON_636 if relate_ok else SIN_RELACION),
        "relate/selected": _relate_ok(adjuntos=(("183615", "auto.pdf"),)),
        "relate/attachments": (lambda _c: _Resp({"status": "success", "errors": []},
                                                adjuntar_status)),
    })
    res = archivar(MSG, "extrajudiciales", 636,
                   adjuntos=[("auto.pdf", nombre)], folder_id="1", transport=t)
    return res, t


def test_h06_la_relacion_verificada_SOBREVIVE_a_un_adjuntar_fallido():
    """EL caso de H-06, y el que no tenía test.

    El relate escribió y se confirmó por relectura; el adjuntar murió con HTTP 500.
    El archivado, como un todo, ha fallado —falta el documento— pero **la relación
    existe en el CRM** y eso no puede perderse: quien reconcilie después necesita
    saber que no tiene que volver a relacionar.
    """
    res, _ = _archivar_con(adjuntar_status=500)

    assert res.ok is False, "falta el documento: el archivado no está completo"
    assert res.relacion.ok is True and res.relacion.verificado is True, \
        "la relación se escribió y se verificó: ese hecho no se borra"
    assert res.documentos.intentado is True and res.documentos.ok is False


def test_h06_un_fallo_de_emparejamiento_no_afirma_que_se_intentaran_los_documentos():
    """Antes daba `verificado=True` con cero documentos, que es peor que un False:
    afirmaba una verificación que nadie hizo."""
    t = FakeTransport(**{
        "element_registries/mail": _mail_registry(cuenta="20"),
        "findRelations": secuencia(SIN_RELACION, CON_636),
        "relate/selected": _relate_ok(adjuntos=(("183615", "auto.pdf"),)),
    })
    res = archivar(MSG, "extrajudiciales", 636,
                   adjuntos=[("NO-ESTA-EN-EL-MANIFIESTO.pdf", "y.pdf")],
                   folder_id="1", transport=t)

    assert res.a_revision is True
    assert res.relacion.verificado is True, "la relación sí se hizo y se verificó"
    assert res.documentos.intentado is False, \
        "no se intentó subir nada: no se puede afirmar ni éxito ni fallo"


def test_h06_ya_presentes_llega_al_resultado_del_archivado():
    """`AdjuntarResult.ya_presentes` se descartaba al componer, aunque el §7 del spec
    diga que se registra. Un documento que ya estaba cuenta como archivado y hay que
    poder distinguirlo de uno que subimos nosotros.

    Ojo al montaje: el nombre tiene que estar en el censo **PREVIO**. Una primera
    versión de este test lo puso solo en el posterior y falló por eso — que es el
    montaje de «lo subimos nosotros», justo el caso contrario.
    """
    nombre = "ya-estaba.pdf"
    t = FakeTransport(**{
        "element_registries/mail": _mail_registry(cuenta="20"),
        "element_registries/gdocu": _gdocu([nombre]),
        "findRelations": secuencia(SIN_RELACION, CON_636),
        "relate/selected": _relate_ok(adjuntos=(("183615", "auto.pdf"),)),
        "relate/attachments": {"status": "success", "errors": []},
    })
    res = archivar(MSG, "extrajudiciales", 636,
                   adjuntos=[("auto.pdf", nombre)], folder_id="1", transport=t)

    assert res.ya_presentes == [nombre]
    assert res.subidos == [], "no lo subimos nosotros"
    assert t.cuerpos("relate/attachments") == [], "y no se re-postea"


def test_h06_sin_cuenta_resoluble_no_se_intenta_ni_relacion_ni_documentos():
    """«No escribí» tiene que ser distinguible de «escribí y falló»: un intento que
    falla puede haber dejado efecto (escritura incierta), y uno que no ocurrió, no."""
    t = FakeTransport(**{"element_registries/mail": {"totalItems": 0.0, "items": []}})

    res = archivar(MSG, "extrajudiciales", 636, adjuntos=[], folder_id="1", transport=t)

    assert res.a_revision is True
    assert res.relacion.intentado is False
    assert res.documentos.intentado is False


def test_h06_el_verificado_PLANO_ya_no_existe():
    """Guard de forma: mientras exista un `verificado` de nivel superior, alguien lo
    leerá y volverá a colapsar los dos hechos. La ambigüedad se quita del tipo."""
    res, _ = _archivar_con()

    assert not hasattr(res, "verificado"), \
        "el `verificado` plano no significaba nada estable: no debe volver"


def test_h06_un_relate_que_NO_se_verifica_no_declara_la_relacion_escrita():
    """Hueco encontrado por el arnés de mutación, no por lectura.

    Ningún test exigía que un relate fallido dejara `relacion.ok=False`. Con el
    mutante que lo pone en `True`, la suite seguía verde — y eso es peor que el
    colapso que H-06 denunciaba: F6 leería que la relación existe cuando el CRM
    devolvió 200 y la relectura no la encontró (un miembro inexistente hace
    exactamente eso, y está medido).
    """
    t = FakeTransport(**{
        "element_registries/mail": _mail_registry(cuenta="20"),
        # la relectura NO confirma: el 200 del CRM no escribió nada
        "findRelations": secuencia(SIN_RELACION, SIN_RELACION),
        "relate/selected": _relate_ok(adjuntos=(("183615", "auto.pdf"),)),
    })

    res = archivar(MSG, "extrajudiciales", 636,
                   adjuntos=[("auto.pdf", "x.pdf")], folder_id="1", transport=t)

    assert res.ok is False
    assert res.relacion.intentado is True, "se posteó: el efecto es desconocido"
    assert res.relacion.ok is False, "sin relectura que lo confirme, NO se declara escrita"
    assert res.documentos.intentado is False, "no se llegó a los documentos"
    assert t.cuerpos("relate/attachments") == []
