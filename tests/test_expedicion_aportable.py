"""`preparar_aportables`: el aportable llega junto al íntegro, o no llega y se dice por qué."""
from __future__ import annotations

import dataclasses
import json
from datetime import datetime, timezone

import pytest

pytest.importorskip("reportlab", reason="hace falta para fabricar los certificados")

from core import certificado_lectura  # noqa: E402
from core import expedicion_certificada as exp  # noqa: E402
from tests import _certificado_sintetico as s  # noqa: E402

W = "W-000AAA"
ID = f"{W} - OVC"


class FakeTransporte:
    """Codicert con dos envíos de una expedición: un correo y un burofax."""

    def __init__(self, envios, certificados, adjuntos, historicos=None):
        self._envios, self._c, self._a = envios, certificados, adjuntos
        self._h = historicos or {}
        self.adjuntos_pedidos: list[tuple[str, str]] = []

    def listar(self, **filtros):
        return list(self._envios)

    def estados(self, id_envio):
        tipo = next(e["tipo"] for e in self._envios if e["id"] == id_envio)
        culmina = 20 if tipo == "c" else 19
        return self._h.get(id_envio, [{"codigo": culmina, "titulo": "",
                                       "fecha": "2026-09-12T23:03:43+02:00",
                                       "detalle": None}])

    def certificado(self, id_envio):
        return self._c[id_envio]

    def descargar_adjunto(self, id_envio, nombre):
        self.adjuntos_pedidos.append((id_envio, nombre))
        return self._a[(id_envio, nombre)]


def _envio(id_envio, tipo, destinatario="destino@ejemplo.es", asunto="OFERTA VINCULANTE"):
    return {"id": id_envio, "tipo": tipo, "asunto": asunto, "destinatarios": destinatario,
            "id_personalizado": ID, "fecha": "2026-09-10T18:26:08+02:00"}


def _escenario(tmp_path, *, adjuntos=None, partes=None, destinatario_burofax="ANA LOPEZ",
               historicos=None, archivar=("006c", "006b")):
    """Correo `006c` + burofax `006b` de la misma expedición, con los íntegros archivados."""
    adjuntos = adjuntos or [s.refundido(), s.factura()]
    certs = {"006c": s.certificado(adjuntos, id_envio="006c"),
             "006b": s.certificado(adjuntos, id_envio="006b", burofax=True)}
    envios = [_envio("006c", "c"), _envio("006b", "b", destinatario=destinatario_burofax)]
    bajables = {("006c", a.nombre): a.contenido for a in adjuntos}
    t = FakeTransporte(envios, certs, bajables, historicos)
    carpeta = tmp_path / "caso" / "04_Output predemanda" / "Certificados"
    carpeta.mkdir(parents=True)
    for id_envio in archivar:
        (carpeta / exp.nombre_canonico("OFERTA VINCULANTE", W, id_envio)).write_bytes(
            certs[id_envio])
    entorno = exp.EntornoExpedicion(
        codicert=t, partes_de=partes or (lambda w: [{"nombre": "ANA", "1apellido": "LOPEZ"}]),
        ahora=lambda: datetime(2026, 9, 25, tzinfo=timezone.utc),
        raiz=tmp_path, plaza="Madrid", entorno="produccion", usuario="madrid.bd",
        carpeta_certificados=lambda w: carpeta,
        leer_emisor=certificado_lectura.leer_emisor)
    return entorno, t, carpeta


def _por_id(resultados):
    return {r.id_envio: r for r in resultados}


def test_produce_el_aportable_y_el_manifiesto_junto_a_cada_integro(tmp_path):
    entorno, _, carpeta = _escenario(tmp_path)
    r = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=entorno))
    for id_envio in ("006c", "006b"):
        assert r[id_envio].estado == exp.PRODUCIDO, r[id_envio].motivo
        assert r[id_envio].ruta_aportable.parent == carpeta
        assert r[id_envio].ruta_aportable.name.endswith(" - APORTABLE.pdf")
        assert r[id_envio].retiradas == (5,)
        m = json.loads(r[id_envio].ruta_manifiesto.read_text(encoding="utf-8"))
        assert m["id_envio"] == id_envio and m["retiradas"][0]["pagina_certificado"] == 5
        assert m["emisor"] == {"razon_social": "EV MMC SPAIN, S.L.U.",
                               "usuario": "madrid.bd", "verificado": True}


def test_el_INTEGRO_no_se_toca(tmp_path):
    entorno, _, carpeta = _escenario(tmp_path)
    integro = carpeta / exp.nombre_canonico("OFERTA VINCULANTE", W, "006c")
    antes = integro.read_bytes()
    exp.preparar_aportables(W, "OVC", entorno_exp=entorno)
    assert integro.read_bytes() == antes


def test_los_documentos_salen_del_CORREO_verificados_contra_su_acta(tmp_path):
    """M-4/M-5: el burofax no dice dónde acaba cada documento; el correo sí."""
    entorno, t, _ = _escenario(tmp_path)
    exp.preparar_aportables(W, "OVC", entorno_exp=entorno)
    assert {e for e, _ in t.adjuntos_pedidos} == {"006c"}


def test_un_adjunto_con_OTRA_huella_para_todo(tmp_path):
    """Lo que se baja tiene que ser lo que el acta dice que salió."""
    entorno, t, _ = _escenario(tmp_path)
    t._a[("006c", "OVC REFUNDIDA.pdf")] = s.pdf(["otra cosa"])
    with pytest.raises(exp.ExpedicionError, match="huella"):
        exp.preparar_aportables(W, "OVC", entorno_exp=entorno)


def test_sin_entrega_electronica_se_para_y_se_dice(tmp_path):
    """Un burofax solo no dice dónde acaba cada documento (M-4): no se adivina."""
    entorno, t, _ = _escenario(tmp_path)
    t._envios = [e for e in t._envios if e["tipo"] == "b"]
    with pytest.raises(exp.ExpedicionError, match="electrónic"):
        exp.preparar_aportables(W, "OVC", entorno_exp=entorno)


def test_si_NINGUN_documento_lleva_el_rotulo_F3_no_decide_por_ti(tmp_path):
    """Nunca se certifica que el íntegro sea aportable: eso lo decide una persona."""
    entorno, _, _ = _escenario(tmp_path, adjuntos=[s.Adjunto("A.pdf", (s.REQUERIMIENTO,)),
                                                    s.factura()])
    with pytest.raises(exp.ExpedicionError, match="lo decide una persona"):
        exp.preparar_aportables(W, "OVC", entorno_exp=entorno)


def test_volver_a_lanzar_NO_duplica_ni_pisa(tmp_path):
    """M-8: el recorte es determinista, así que se compara por contenido."""
    entorno, _, _ = _escenario(tmp_path)
    exp.preparar_aportables(W, "OVC", entorno_exp=entorno)
    r = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=entorno))
    assert r["006c"].estado == exp.YA_ESTABA and r["006b"].estado == exp.YA_ESTABA


def test_un_aportable_DISTINTO_ya_escrito_no_se_pisa(tmp_path):
    entorno, _, carpeta = _escenario(tmp_path)
    integro = carpeta / exp.nombre_canonico("OFERTA VINCULANTE", W, "006c")
    exp.ruta_aportable(integro).write_bytes(b"%PDF-1.4 otro")
    r = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=entorno))
    assert r["006c"].estado == exp.PARADO and "no se pisa" in r["006c"].motivo
    assert exp.ruta_aportable(integro).read_bytes() == b"%PDF-1.4 otro"


def test_un_manifiesto_que_falta_se_repone(tmp_path):
    """Una corrida que murió entre los dos ficheros no deja el aportable sin manifiesto."""
    entorno, _, carpeta = _escenario(tmp_path)
    exp.preparar_aportables(W, "OVC", entorno_exp=entorno)
    integro = carpeta / exp.nombre_canonico("OFERTA VINCULANTE", W, "006c")
    exp.ruta_manifiesto(integro).unlink()
    r = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=entorno))
    assert r["006c"].estado == exp.YA_ESTABA and exp.ruta_manifiesto(integro).is_file()


def test_sin_integro_archivado_se_dice_que_hay_que_cosechar(tmp_path):
    entorno, _, _ = _escenario(tmp_path, archivar=("006c",))
    r = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=entorno))
    assert r["006b"].estado == exp.SIN_COSECHAR and "cosechar" in r["006b"].motivo


def test_lo_que_aun_puede_mejorar_se_declara_pendiente(tmp_path):
    entorno, _, _ = _escenario(tmp_path, historicos={"006b": [
        {"codigo": 17, "titulo": "", "fecha": "2026-09-11T10:00:00+02:00", "detalle": None}]})
    r = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=entorno))
    assert r["006b"].estado == exp.PENDIENTE and r["006c"].estado == exp.PRODUCIDO


def test_un_integro_de_OTRO_emisor_para_ese_envio(tmp_path):
    """Art. 17.2: el íntegro del expediente pudo cambiar desde la cosecha."""
    entorno, _, carpeta = _escenario(tmp_path)
    ajeno = s.certificado([s.refundido(), s.factura()], id_envio="006c",
                          emisor="INMOBILIARIA RIVAL, S.L.")
    (carpeta / exp.nombre_canonico("OFERTA VINCULANTE", W, "006c")).write_bytes(ajeno)
    r = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=entorno))
    assert r["006c"].estado == exp.PARADO and "emisor" in r["006c"].motivo
    assert r["006b"].estado == exp.PRODUCIDO


def test_el_SOBRE_CONJUNTO_viaja_al_manifiesto(tmp_path):
    """Spec §5 regla 3: el aviso va en el plan Y en el manifiesto del certificado."""
    partes = lambda w: [{"nombre": "ANA", "1apellido": "LOPEZ"},  # noqa: E731
                        {"nombre": "LUIS", "1apellido": "PEREZ"}]
    entorno, _, _ = _escenario(tmp_path, partes=partes,
                               destinatario_burofax="ANA LOPEZ Y LUIS PEREZ")
    r = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=entorno))
    m = json.loads(r["006b"].ruta_manifiesto.read_text(encoding="utf-8"))
    assert exp.AVISO_SOBRE_CONJUNTO in m["avisos"]
    m_correo = json.loads(r["006c"].ruta_manifiesto.read_text(encoding="utf-8"))
    assert exp.AVISO_SOBRE_CONJUNTO not in m_correo["avisos"]


def test_una_razon_social_con_Y_dentro_NO_es_un_sobre_conjunto(tmp_path):
    partes = lambda w: [{"nombre": "GARCIA Y ASOCIADOS, S.L."}]  # noqa: E731
    entorno, _, _ = _escenario(tmp_path, partes=partes,
                               destinatario_burofax="GARCIA Y ASOCIADOS, S.L.")
    r = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=entorno))
    m = json.loads(r["006b"].ruta_manifiesto.read_text(encoding="utf-8"))
    assert exp.AVISO_SOBRE_CONJUNTO not in m["avisos"]


def test_si_el_CRM_no_responde_se_avisa_en_vez_de_callar(tmp_path):
    def sin_crm(w):
        raise exp.ExpedicionError("el caso no está indexado")

    entorno, _, _ = _escenario(tmp_path, partes=sin_crm)
    r = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=entorno))
    assert r["006b"].estado == exp.PRODUCIDO
    assert any("no se pudo comprobar si el sobre" in a for a in r["006b"].avisos)


def test_una_parada_del_recorte_es_de_ESE_envio_no_de_todos(tmp_path):
    entorno, t, _ = _escenario(tmp_path)
    t._c["006b"] = s.certificado([s.refundido(), s.factura()], id_envio="006b",
                                 burofax=True,
                                 reproduccion=[s.REQUERIMIENTO, s.OVC, s.FACTURA])
    carpeta = entorno.carpeta_certificados(W)
    (carpeta / exp.nombre_canonico("OFERTA VINCULANTE", W, "006b")).write_bytes(t._c["006b"])
    r = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=entorno))
    assert r["006b"].estado == exp.PARADO and "no aparece" in r["006b"].motivo
    assert r["006c"].estado == exp.PRODUCIDO


def test_sin_los_puertos_de_F2_se_para_en_vez_de_escribir_en_el_arbol_real(tmp_path):
    entorno, _, _ = _escenario(tmp_path)
    with pytest.raises(exp.ExpedicionError, match="carpeta_certificados"):
        exp.preparar_aportables(W, "OVC", entorno_exp=dataclasses.replace(
            entorno, carpeta_certificados=None))
