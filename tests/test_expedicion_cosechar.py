"""`cosechar`: el certificado llega al expediente y al CRM, o no llega y se dice."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import pytest

from core import expedicion_certificada as exp

CERT = b"%PDF-1.4 certificado de prueba"
SHA = hashlib.sha256(CERT).hexdigest()


class FakeTransporte:
    def __init__(self, listado, historicos, certificados):
        self._l, self._h, self._c = listado, historicos, certificados
        self.certificados_pedidos: list[str] = []

    def listar(self, **filtros):
        return list(self._l)

    def estados(self, id_envio):
        return list(self._h.get(id_envio, []))

    def certificado(self, id_envio):
        self.certificados_pedidos.append(id_envio)
        return self._c[id_envio]


class FakeGestor:
    """Doble de `core.sudespacho_documentos`. Registra lo subido."""

    def __init__(self, ya=None):
        self.subidos: list[dict] = []
        self.ya = ya or {}

    def subir(self, contenido, *, nombrefinal, mime, related, al_reservar=None):
        if al_reservar:
            al_reservar(f"uuid-{len(self.subidos)}")
        self.subidos.append({"nombrefinal": nombrefinal, "related": related,
                             "sha256": hashlib.sha256(contenido).hexdigest()})
        return exp.DocumentoEnCrm(doc_id=f"doc{len(self.subidos)}",
                                  origen_id=f"uuid-{len(self.subidos) - 1}",
                                  nombrefinal=nombrefinal,
                                  sha256=hashlib.sha256(contenido).hexdigest())

    def buscar_por_origen_id(self, origen_id, *, element, exp_id):
        return self.ya.get(origen_id)


def _entorno(tmp_path, transporte, gestor, emisor="EV MMC SPAIN, S.L.U."):
    destino = tmp_path / "caso" / "04_Output predemanda" / "Certificados"
    return exp.EntornoExpedicion(
        codicert=transporte, partes_de=lambda w: [],
        ahora=lambda: datetime(2026, 9, 21, tzinfo=timezone.utc),
        raiz=tmp_path, plaza="Madrid", entorno="produccion", usuario="madrid.bd",
        carpeta_certificados=lambda w: destino,
        gestor=gestor, exp_crm=lambda w: ("extrajudiciales", "123"),
        leer_emisor=lambda pdf: exp.EmisorLeido(razon_social=emisor,
                                                usuario="madrid.bd"))


def _ev(id_envio, tipo="c", asunto="REQUERIMIENTO"):
    return {"id": id_envio, "tipo": tipo, "asunto": asunto,
            "destinatarios": "x@y.es", "id_personalizado": "W-04AKM2 - OVC",
            "fecha": "2026-09-10T18:26:08+02:00",
            "estado": {"codigo": 20, "titulo": "Leído",
                       "fecha": "2026-09-12T23:03:43+02:00", "detalle": None}}


def _h20():
    return [{"codigo": 20, "titulo": "Leído",
             "fecha": "2026-09-12T23:03:43+02:00", "detalle": None}]


def test_baja_verifica_archiva_y_sube(tmp_path):
    t = FakeTransporte([_ev("006a")], {"006a": _h20()}, {"006a": CERT})
    g = FakeGestor()
    r = exp.cosechar("W-04AKM2", "OVC", entorno_exp=_entorno(tmp_path, t, g))
    assert len(r) == 1 and r[0].sha256 == SHA and r[0].doc_id == "doc1"
    assert r[0].ruta_local.is_file() and r[0].ruta_local.read_bytes() == CERT
    assert g.subidos[0]["related"] == "extrajudiciales:123:left"


def test_el_nombre_canonico_es_ASUNTO_REF_CODIGO(tmp_path):
    """La convención medida: `RESPUESTA REQUERIMIENTO - W-04A6LI-006casm113n.pdf`."""
    t = FakeTransporte([_ev("006a", asunto="RESPUESTA REQUERIMIENTO")],
                       {"006a": _h20()}, {"006a": CERT})
    g = FakeGestor()
    r = exp.cosechar("W-04AKM2", "OVC", entorno_exp=_entorno(tmp_path, t, g))
    assert r[0].ruta_local.name == "RESPUESTA REQUERIMIENTO - W-04AKM2-006a.pdf"


def test_el_asunto_se_SANEA_para_que_sea_un_nombre_de_fichero(tmp_path):
    """M-8: hay identificadores en producción con `/` dentro (`W-02XE7E/W-046HM4`).

    Sin sanear, `Path` interpretaría la barra como separador y el certificado
    acabaría en una subcarpeta inventada — o reventaría en Windows.
    """
    t = FakeTransporte([_ev("006a", asunto="W-02XE7E/W-046HM4: aviso")],
                       {"006a": _h20()}, {"006a": CERT})
    g = FakeGestor()
    r = exp.cosechar("W-04AKM2", "OVC", entorno_exp=_entorno(tmp_path, t, g))
    assert "/" not in r[0].ruta_local.name and ":" not in r[0].ruta_local.name
    assert r[0].ruta_local.parent.name == "Certificados"


def test_un_asunto_VACIO_no_produce_un_nombre_degenerado(tmp_path):
    t = FakeTransporte([_ev("006a", asunto="")], {"006a": _h20()}, {"006a": CERT})
    g = FakeGestor()
    r = exp.cosechar("W-04AKM2", "OVC", entorno_exp=_entorno(tmp_path, t, g))
    assert r[0].ruta_local.name == "CERTIFICADO - W-04AKM2-006a.pdf"


def test_un_emisor_DISTINTO_para_la_cosecha_y_no_sube_nada(tmp_path):
    """Art. 17.2: si el certificado no lo firma nuestro emisor, no es nuestra prueba."""
    t = FakeTransporte([_ev("006a")], {"006a": _h20()}, {"006a": CERT})
    g = FakeGestor()
    entorno = _entorno(tmp_path, t, g, emisor="INMOBILIARIA RIVAL, S.L.")
    with pytest.raises(exp.ExpedicionError, match="emisor"):
        exp.cosechar("W-04AKM2", "OVC", entorno_exp=entorno)
    assert g.subidos == []


def test_un_emisor_distinto_NO_deja_el_PDF_escrito_en_el_expediente(tmp_path):
    """Verificar ANTES de escribir: un certificado ajeno no entra ni en disco."""
    t = FakeTransporte([_ev("006a")], {"006a": _h20()}, {"006a": CERT})
    entorno = _entorno(tmp_path, t, FakeGestor(), emisor="INMOBILIARIA RIVAL, S.L.")
    with pytest.raises(exp.ExpedicionError):
        exp.cosechar("W-04AKM2", "OVC", entorno_exp=entorno)
    assert list(tmp_path.glob("**/*.pdf")) == []


def test_NO_cosecha_lo_que_aun_puede_mejorar(tmp_path):
    """Un 21 puede volverse 20. El certificado de hoy ocuparía el sitio del bueno."""
    t = FakeTransporte([_ev("006a")], {"006a": [
        {"codigo": 21, "titulo": "", "fecha": "2026-09-11T19:00:23+02:00",
         "detalle": None}]}, {"006a": CERT})
    g = FakeGestor()
    r = exp.cosechar("W-04AKM2", "OVC", entorno_exp=_entorno(tmp_path, t, g))
    assert r == [] and g.subidos == [] and t.certificados_pedidos == []


def _h(*pares):
    return [{"codigo": c, "titulo": "", "fecha": f, "detalle": None} for c, f in pares]


def test_con_incluir_pendientes_SI_baja_lo_provisional(tmp_path):
    """El caso que destapó el humo del 2026-09-21, y no era hipotético.

    El envío real `006catf83zx` lleva estados [17, 14, 21]: **entregado y nunca
    leído**. Con el criterio por defecto no es cosechable —el 21 puede volverse 20—
    así que su certificado quedaría fuera del expediente hasta que caducase, y no
    está medido cuánto tarda eso. Era uno de los tres envíos de una expedición viva.
    """
    t = FakeTransporte([_ev("006a")],
                       {"006a": _h((17, "2026-09-11T10:00:00+02:00"),
                                   (21, "2026-09-11T19:00:23+02:00"))},
                       {"006a": CERT})
    g = FakeGestor()
    entorno = _entorno(tmp_path, t, g)
    assert exp.cosechar("W-04AKM2", "OVC", entorno_exp=entorno) == []
    r = exp.cosechar("W-04AKM2", "OVC", entorno_exp=entorno, incluir_pendientes=True)
    assert len(r) == 1 and r[0].provisional is True


def test_el_provisional_lleva_su_ESTADO_en_el_nombre(tmp_path):
    """Para que no ocupe el sitio del definitivo, que es por qué se excluía."""
    t = FakeTransporte([_ev("006a")],
                       {"006a": _h((21, "2026-09-11T19:00:23+02:00"))},
                       {"006a": CERT})
    r = exp.cosechar("W-04AKM2", "OVC", entorno_exp=_entorno(tmp_path, t, FakeGestor()),
                     incluir_pendientes=True)
    assert r[0].ruta_local.name == "REQUERIMIENTO - W-04AKM2-006a (estado 21).pdf"


def test_el_provisional_NO_bloquea_al_definitivo_que_llegue_despues(tmp_path):
    """La prueba de que las dos claves del registro no se pisan.

    Se cosecha el provisional en 21, el envío avanza a 20, y el definitivo tiene
    que poder cosecharse igualmente — con su nombre canónico, sin sufijo.
    """
    historicos = {"006a": _h((21, "2026-09-11T19:00:23+02:00"))}
    t = FakeTransporte([_ev("006a")], historicos, {"006a": CERT})
    g = FakeGestor()
    entorno = _entorno(tmp_path, t, g)
    exp.cosechar("W-04AKM2", "OVC", entorno_exp=entorno, incluir_pendientes=True)

    historicos["006a"] = _h((21, "2026-09-11T19:00:23+02:00"),
                            (20, "2026-09-12T23:03:43+02:00"))
    r = exp.cosechar("W-04AKM2", "OVC", entorno_exp=entorno)
    assert len(r) == 1 and r[0].provisional is False
    assert r[0].ruta_local.name == "REQUERIMIENTO - W-04AKM2-006a.pdf"
    assert len(g.subidos) == 2       # el provisional y el definitivo, ambos


def test_el_provisional_tambien_es_idempotente(tmp_path):
    t = FakeTransporte([_ev("006a")],
                       {"006a": _h((21, "2026-09-11T19:00:23+02:00"))},
                       {"006a": CERT})
    g = FakeGestor()
    entorno = _entorno(tmp_path, t, g)
    exp.cosechar("W-04AKM2", "OVC", entorno_exp=entorno, incluir_pendientes=True)
    segunda = exp.cosechar("W-04AKM2", "OVC", entorno_exp=entorno,
                           incluir_pendientes=True)
    assert len(g.subidos) == 1 and segunda[0].ya_estaba is True


def test_el_provisional_tambien_verifica_el_emisor(tmp_path):
    """La puerta del art. 17.2 no se relaja por bajar un provisional."""
    t = FakeTransporte([_ev("006a")],
                       {"006a": _h((21, "2026-09-11T19:00:23+02:00"))},
                       {"006a": CERT})
    entorno = _entorno(tmp_path, t, FakeGestor(), emisor="INMOBILIARIA RIVAL, S.L.")
    with pytest.raises(exp.ExpedicionError, match="emisor"):
        exp.cosechar("W-04AKM2", "OVC", entorno_exp=entorno, incluir_pendientes=True)


def test_es_IDEMPOTENTE_por_el_registro_local(tmp_path):
    """Dos cosechas seguidas suben una sola vez. La segunda lo dice."""
    t = FakeTransporte([_ev("006a")], {"006a": _h20()}, {"006a": CERT})
    g = FakeGestor()
    entorno = _entorno(tmp_path, t, g)
    exp.cosechar("W-04AKM2", "OVC", entorno_exp=entorno)
    segunda = exp.cosechar("W-04AKM2", "OVC", entorno_exp=entorno)
    assert len(g.subidos) == 1
    assert segunda[0].ya_estaba is True


def test_si_el_PDF_local_desaparecio_se_DICE_en_vez_de_devolver_una_ruta_muerta(tmp_path):
    """El registro acredita el CRM, no el disco: son dos sitios y se desincronizan.

    Si alguien borra el PDF del expediente, la segunda cosecha veía «hecho» en el
    registro y devolvía la ruta tal cual — una ruta a un fichero que no existe, sin
    una palabra. El operador creería tener el certificado en el expediente cuando
    solo está en el CRM.
    """
    t = FakeTransporte([_ev("006a")], {"006a": _h20()}, {"006a": CERT})
    entorno = _entorno(tmp_path, t, FakeGestor())
    primera = exp.cosechar("W-04AKM2", "OVC", entorno_exp=entorno)
    assert primera[0].local_presente is True

    primera[0].ruta_local.unlink()
    segunda = exp.cosechar("W-04AKM2", "OVC", entorno_exp=entorno)
    assert segunda[0].ya_estaba is True
    assert segunda[0].local_presente is False


def test_la_segunda_cosecha_NI_SIQUIERA_baja_el_certificado(tmp_path):
    """La guarda muerde antes del GET: no se gasta una descarga en lo ya hecho."""
    t = FakeTransporte([_ev("006a")], {"006a": _h20()}, {"006a": CERT})
    entorno = _entorno(tmp_path, t, FakeGestor())
    exp.cosechar("W-04AKM2", "OVC", entorno_exp=entorno)
    exp.cosechar("W-04AKM2", "OVC", entorno_exp=entorno)
    assert t.certificados_pedidos == ["006a"]


def test_MUTANTE_una_idempotencia_por_el_LISTADO_no_sirve(tmp_path):
    """Control de que la guarda mira el registro local y no un censo remoto.

    Se borra el registro dejando el documento en el CRM: si la guarda consultara un
    censo del gestor, seguiría diciendo «ya está». Como mira el registro local —que
    es lo que el §17.4 autoriza a sostener— vuelve a subir, y ESO es lo correcto:
    sin registro no se puede sostener la ausencia... ni la presencia.
    """
    t = FakeTransporte([_ev("006a")], {"006a": _h20()}, {"006a": CERT})
    g = FakeGestor()
    entorno = _entorno(tmp_path, t, g)
    exp.cosechar("W-04AKM2", "OVC", entorno_exp=entorno)
    (tmp_path / "_codicert_cosecha.jsonl").unlink()
    exp.cosechar("W-04AKM2", "OVC", entorno_exp=entorno)
    assert len(g.subidos) == 2


def test_una_reserva_ABIERTA_para_la_cosecha_de_ESE_envio(tmp_path):
    """El caso del timeout: no se reintenta solo, se pide humano (§5.2)."""
    reg = exp.RegistroCosecha(tmp_path / "_codicert_cosecha.jsonl",
                              entorno="produccion", usuario="madrid.bd",
                              ahora=lambda: datetime(2026, 9, 20, tzinfo=timezone.utc))
    reg.reservar("006a", "uuid-huerfano")
    t = FakeTransporte([_ev("006a")], {"006a": _h20()}, {"006a": CERT})
    g = FakeGestor()
    with pytest.raises(exp.ExpedicionError, match="SIN VERIFICAR|uuid-huerfano"):
        exp.cosechar("W-04AKM2", "OVC", entorno_exp=_entorno(tmp_path, t, g))
    assert g.subidos == []


def test_la_reserva_abierta_se_resuelve_sola_si_el_documento_SI_esta(tmp_path):
    """Buscar por `origen_id` es inmediato: si el documento existe, se cierra."""
    reg = exp.RegistroCosecha(tmp_path / "_codicert_cosecha.jsonl",
                              entorno="produccion", usuario="madrid.bd",
                              ahora=lambda: datetime(2026, 9, 20, tzinfo=timezone.utc))
    reg.reservar("006a", "uuid-huerfano")
    t = FakeTransporte([_ev("006a")], {"006a": _h20()}, {"006a": CERT})
    g = FakeGestor(ya={"uuid-huerfano": "doc-ya-estaba"})
    r = exp.cosechar("W-04AKM2", "OVC", entorno_exp=_entorno(tmp_path, t, g))
    assert g.subidos == [] and r[0].doc_id == "doc-ya-estaba" and r[0].ya_estaba


def test_escribe_solo_bajo_la_carpeta_que_le_dan(tmp_path):
    """La regla sin escotilla: ningún test escribe en el árbol de producción."""
    t = FakeTransporte([_ev("006a")], {"006a": _h20()}, {"006a": CERT})
    r = exp.cosechar("W-04AKM2", "OVC",
                     entorno_exp=_entorno(tmp_path, t, FakeGestor()))
    assert tmp_path in r[0].ruta_local.parents


def test_un_entorno_SIN_los_puertos_de_escritura_para_antes_de_nada(tmp_path):
    """Un `EntornoExpedicion` de F1 no puede cosechar por accidente contra el árbol real."""
    t = FakeTransporte([_ev("006a")], {"006a": _h20()}, {"006a": CERT})
    de_f1 = exp.EntornoExpedicion(  # entorno-sin-cosecha: ESE es el caso bajo prueba
        codicert=t, partes_de=lambda w: [],
        ahora=lambda: datetime(2026, 9, 21, tzinfo=timezone.utc),
        raiz=tmp_path, plaza="Madrid", entorno="produccion", usuario="madrid.bd")
    with pytest.raises(exp.ExpedicionError, match="carpeta_certificados"):
        exp.cosechar("W-04AKM2", "OVC", entorno_exp=de_f1)
