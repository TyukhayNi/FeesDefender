"""`preparar_aportables`: el aportable llega junto al íntegro, o no llega y se dice por qué."""
from __future__ import annotations

import dataclasses
import hashlib
import io
import json
from datetime import datetime, timezone

import pytest

pytest.importorskip("reportlab", reason="hace falta para fabricar los certificados")
pytest.importorskip("pypdfium2", reason="el aportable es la IMAGEN del certificado (R2/H-01)")

from core import certificado_lectura  # noqa: E402
from core import expedicion_certificada as exp  # noqa: E402
from tests import _certificado_sintetico as s  # noqa: E402

W = "W-000AAA"
ID = f"{W} - OVC"


@pytest.fixture(autouse=True)
def _resolucion_de_prueba(request, monkeypatch):
    """La orquestación no depende de la resolución de la imagen —los píxeles los prueba el
    módulo puro, a la de verdad—: aquí se baja a 72 ppp para no pagar 200 en cada una de
    sus corridas. El test lento del OCR real se queda con la de verdad, que es la que lee."""
    if request.node.get_closest_marker("slow") is None:
        from core import certificado_aportable as apo

        monkeypatch.setattr(apo, "PPP", 72)


class OcrContado:
    """El puerto de OCR de la orquestación: lee cada página con el OCR honesto de los tests
    (`s.ocr_fiel`) y cuenta cuántas le pasan. Desde la R3 un aportable sin texto NO se
    entrega (H-04), así que el doble ya no puede devolver nada; lo que el OCR lee lo prueba
    el módulo puro, y aquí importa CUÁNDO se pasa."""

    def __init__(self, ocr):
        self.llamadas = 0
        self._ocr = ocr

    def __call__(self, jpeg: bytes):
        self.llamadas += 1
        return self._ocr(jpeg)


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
               historicos=None, archivar=("006c", "006b"), ocr=None):
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
    # El acta del correo y la del burofax solo cambian en su código: el doble no exige
    # distinguirlas (`estricto=False`), porque aquí se prueba cuándo se pasa, no qué lee.
    entorno = exp.EntornoExpedicion(
        codicert=t, partes_de=partes or (lambda w: [{"nombre": "ANA", "1apellido": "LOPEZ"}]),
        ahora=lambda: datetime(2026, 9, 25, tzinfo=timezone.utc),
        raiz=tmp_path, plaza="Madrid", entorno="produccion", usuario="madrid.bd",
        carpeta_certificados=lambda w: carpeta,
        leer_emisor=certificado_lectura.leer_emisor,
        ocr=ocr or OcrContado(s.ocr_fiel(*certs.values(), estricto=False)))
    return entorno, t, carpeta


def _avisos_del_manifiesto(m: dict) -> list[str]:
    """Todos los avisos que viajan con el aportable: los suyos y los del destinatario, que
    desde la R2 (H-04) van aparte."""
    return [*m["avisos"], *m.get("destinatario", {}).get("avisos", [])]


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
        # R1, §5: se dice QUÉ se comprobó del emisor, no un «verificado» genérico.
        assert m["emisor"] == {"razon_social": "EV MMC SPAIN, S.L.U.",
                               "usuario": "madrid.bd", "razon_social_verificada": True,
                               "usuario_verificado": True}
        # R2/H-01: la huella es la del fichero ESCRITO, que es imagen con su capa de texto;
        # versión 3 desde la R3, cuando el aportable lo pasa a componer el motor.
        escrito = r[id_envio].ruta_aportable.read_bytes()
        assert m["aportable"]["sha256"] == hashlib.sha256(escrito).hexdigest()
        assert m["version"] == 3 and "imagen" in m["aportable"]["forma"]


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
    """M-8, rehecho con la R2 y la R3: el aportable que ya está se RELEE —se recompone con la
    imagen de hoy y el texto que lleva— y no se vuelve a pasar el OCR, que es lo caro (de
    1,4 a 10,9 s por página real, M-13). El OCR va por página: cinco conservadas por envío."""
    entorno, _, carpeta = _escenario(tmp_path)
    exp.preparar_aportables(W, "OVC", entorno_exp=entorno)
    antes = {p.name: p.read_bytes() for p in carpeta.iterdir()}
    llamadas = entorno.ocr.llamadas
    r = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=entorno))
    assert r["006c"].estado == exp.YA_ESTABA and r["006b"].estado == exp.YA_ESTABA
    assert entorno.ocr.llamadas == llamadas == 10
    assert {p.name: p.read_bytes() for p in carpeta.iterdir()} == antes


def test_un_aportable_DISTINTO_ya_escrito_no_se_pisa(tmp_path):
    entorno, _, carpeta = _escenario(tmp_path)
    integro = carpeta / exp.nombre_canonico("OFERTA VINCULANTE", W, "006c")
    exp.ruta_aportable(integro).write_bytes(b"%PDF-1.4 otro")
    r = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=entorno))
    assert r["006c"].estado == exp.PARADO and "no se pisa" in r["006c"].motivo
    assert exp.ruta_aportable(integro).read_bytes() == b"%PDF-1.4 otro"


def test_un_manifiesto_que_falta_se_repone(tmp_path):
    """Una corrida que murió entre los dos ficheros no deja el aportable sin manifiesto. El
    que se repone describe el aportable que YA está —releído—, con su huella."""
    entorno, _, carpeta = _escenario(tmp_path)
    exp.preparar_aportables(W, "OVC", entorno_exp=entorno)
    integro = carpeta / exp.nombre_canonico("OFERTA VINCULANTE", W, "006c")
    exp.ruta_manifiesto(integro).unlink()
    r = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=entorno))
    assert r["006c"].estado == exp.YA_ESTABA and exp.ruta_manifiesto(integro).is_file()
    m = json.loads(exp.ruta_manifiesto(integro).read_text(encoding="utf-8"))
    assert m["aportable"]["sha256"] == hashlib.sha256(
        exp.ruta_aportable(integro).read_bytes()).hexdigest()


def test_R2_un_aportable_ya_escrito_se_RELEE_antes_de_darlo_por_bueno(tmp_path):
    """Un PDF con el nombre del aportable que no es la imagen de ESTE íntegro —aquí, el
    aportable de otro certificado— no pasa por «ya estaba»: no se pisa y se dice."""
    entorno, _, carpeta = _escenario(tmp_path)
    exp.preparar_aportables(W, "OVC", entorno_exp=entorno)
    correo, burofax = (exp.ruta_aportable(carpeta / exp.nombre_canonico("OFERTA VINCULANTE", W, e))
                       for e in ("006c", "006b"))
    for m in carpeta.glob("* - MANIFIESTO.json"):
        m.unlink()
    ajeno = burofax.read_bytes()
    correo.write_bytes(ajeno)
    r = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=entorno))
    assert r["006c"].estado == exp.PARADO and "no se pisa" in r["006c"].motivo
    assert correo.read_bytes() == ajeno


def _integro_006c(carpeta):
    return carpeta / exp.nombre_canonico("OFERTA VINCULANTE", W, "006c")


def test_H04_un_manifiesto_que_NO_corresponde_ni_se_acepta_ni_se_pisa(tmp_path):
    """R1/H-04: con el aportable ya escrito, un manifiesto adulterado pasaba por
    `YA_ESTABA` y se quedaba con la huella falsa."""
    entorno, _, carpeta = _escenario(tmp_path)
    exp.preparar_aportables(W, "OVC", entorno_exp=entorno)
    manifiesto = exp.ruta_manifiesto(_integro_006c(carpeta))
    m = json.loads(manifiesto.read_text(encoding="utf-8"))
    m["integro"]["sha256"] = "0" * 64
    adulterado = json.dumps(m, ensure_ascii=False, indent=2) + "\n"
    manifiesto.write_text(adulterado, encoding="utf-8")
    r = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=entorno))
    assert r["006c"].estado == exp.PARADO and "manifiesto" in r["006c"].motivo
    assert manifiesto.read_text(encoding="utf-8") == adulterado


def test_H04_un_manifiesto_HUERFANO_que_no_corresponde_no_se_pisa(tmp_path):
    """Sin aportable, el manifiesto que hubiera se sobrescribía sin mirarlo."""
    entorno, _, carpeta = _escenario(tmp_path)
    manifiesto = exp.ruta_manifiesto(_integro_006c(carpeta))
    manifiesto.write_text('{"version": 1, "id_envio": "otro"}\n', encoding="utf-8")
    r = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=entorno))
    assert r["006c"].estado == exp.PARADO and "manifiesto" in r["006c"].motivo
    assert manifiesto.read_text(encoding="utf-8") == '{"version": 1, "id_envio": "otro"}\n'
    assert not exp.ruta_aportable(_integro_006c(carpeta)).exists()


def test_R3_un_manifiesto_HUERFANO_que_corresponde_REPONE_su_aportable(tmp_path):
    """La R2 paraba aquí: el PDF lo escribía OCRmyPDF, no daba dos veces los mismos bytes y
    un aportable repuesto no casaba con el manifiesto. Desde la R3 lo compone el motor con
    las líneas que el OCR lee —el mismo OCR sobre la misma imagen da las mismas líneas: 18
    de 18 páginas reales, M-13—, así que se repone si sale con la huella que el manifiesto
    dice, y el manifiesto no se toca."""
    entorno, _, carpeta = _escenario(tmp_path)
    exp.preparar_aportables(W, "OVC", entorno_exp=entorno)
    integro = _integro_006c(carpeta)
    manifiesto, aportable = exp.ruta_manifiesto(integro), exp.ruta_aportable(integro)
    antes_m, antes_a = manifiesto.read_bytes(), aportable.read_bytes()
    aportable.unlink()
    r = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=entorno))
    assert r["006c"].estado == exp.PRODUCIDO, r["006c"].motivo
    assert aportable.read_bytes() == antes_a and manifiesto.read_bytes() == antes_m
    assert r["006b"].estado == exp.YA_ESTABA


def test_R3_un_manifiesto_HUERFANO_cuyo_aportable_saldria_DISTINTO_para(tmp_path):
    """Si hoy el OCR lee otra cosa —otra versión de Tesseract—, el aportable no tendría la
    huella del manifiesto: ni se escribe ni se pisa el manifiesto, y se dice."""
    entorno, _, carpeta = _escenario(tmp_path)
    exp.preparar_aportables(W, "OVC", entorno_exp=entorno)
    integro = _integro_006c(carpeta)
    manifiesto, aportable = exp.ruta_manifiesto(integro), exp.ruta_aportable(integro)
    antes = manifiesto.read_bytes()
    aportable.unlink()
    fiel = entorno.ocr

    def otro_ocr(jpeg):
        return tuple(dataclasses.replace(l, texto=l.texto + " x") for l in fiel(jpeg))

    r = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=dataclasses.replace(
        entorno, ocr=otro_ocr)))
    assert r["006c"].estado == exp.PARADO and "no corresponde" in r["006c"].motivo
    assert manifiesto.read_bytes() == antes and not aportable.exists()


def test_R3_H05_una_MENCION_del_rotulo_en_un_documento_para_todo(tmp_path):
    """R3/H-05 en la orquestación: la mención antes del título para en
    `paginas_de_condiciones`, y los documentos son los de TODOS los envíos, así que para la
    expedición entera, como `ExpedicionError` y con su motivo —no como un error sin cazar—."""
    mencion = s.REQUERIMIENTO + "\nEl anexo se titula\nCONFIDENCIAL - CONDICIONES y se adjunta."
    adjuntos = [s.Adjunto("OVC REFUNDIDA.pdf", (mencion, s.OVC, s.CONDICIONES)), s.factura()]
    entorno, _, carpeta = _escenario(tmp_path, adjuntos=adjuntos)
    with pytest.raises(exp.ExpedicionError, match="menciona el rótulo"):
        exp.preparar_aportables(W, "OVC", entorno_exp=entorno)
    assert not list(carpeta.glob("* - APORTABLE.pdf"))


def test_R3_los_avisos_de_lo_que_el_OCR_LEE_viajan_al_manifiesto(tmp_path):
    """El aviso del escaneo (R3, §2) va al manifiesto con los demás, y es el mismo al volver
    a lanzar: se calcula de lo que el aportable lleva, no de una corrida del OCR."""
    adjuntos = [s.refundido(), s.Adjunto("BLANCO.pdf", ("",)), s.factura()]
    certs = [s.certificado(adjuntos, id_envio="006c"),
             s.certificado(adjuntos, id_envio="006b", burofax=True)]
    frase = "el primer 50% entre los dias 1 y 5 del mes siguiente a la primera recepcion"
    ocr = OcrContado(s.ocr_fiel(*certs, estricto=False, extra={6: frase}))
    entorno, _, _ = _escenario(tmp_path, adjuntos=adjuntos, ocr=ocr)
    r = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=entorno))
    m = json.loads(r["006c"].ruta_manifiesto.read_text(encoding="utf-8"))
    assert any("página 6 del certificado muestra en su imagen" in a for a in m["avisos"])
    otra = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=entorno))
    assert otra["006c"].estado == exp.YA_ESTABA, otra["006c"].motivo


def test_el_manifiesto_dice_QUE_se_comprobo_del_emisor(tmp_path):
    """R1, §5: con `verificar_plaza=False` la cuenta no se compara, y el manifiesto decía
    igualmente `verificado: true`. Afirmaba más de lo que se comprobó."""
    entorno, _, carpeta = _escenario(tmp_path)
    exp.preparar_aportables(W, "OVC", entorno_exp=entorno, verificar_plaza=False)
    m = json.loads(exp.ruta_manifiesto(_integro_006c(carpeta)).read_text(encoding="utf-8"))
    assert m["emisor"]["razon_social_verificada"] is True
    assert m["emisor"]["usuario_verificado"] is False


def test_sin_integro_archivado_se_dice_que_hay_que_cosechar(tmp_path):
    entorno, _, _ = _escenario(tmp_path, archivar=("006c",))
    r = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=entorno))
    assert r["006b"].estado == exp.SIN_COSECHAR and "cosechar" in r["006b"].motivo


def test_lo_que_aun_puede_mejorar_se_declara_pendiente(tmp_path):
    entorno, _, _ = _escenario(tmp_path, historicos={"006b": [
        {"codigo": 17, "titulo": "", "fecha": "2026-09-11T10:00:00+02:00", "detalle": None}]})
    r = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=entorno))
    assert r["006b"].estado == exp.PENDIENTE and r["006c"].estado == exp.PRODUCIDO


def test_lo_estancado_se_declara_pendiente_con_SU_motivo(tmp_path):
    """M-21: el aportable decía de todo lo no cosechable que «puede mejorar». Un burofax en
    17 desde hace 55 días no mejorará: se dice lo que es."""
    entorno, _, _ = _escenario(tmp_path, historicos={"006b": [
        {"codigo": 17, "titulo": "", "fecha": "2026-08-01T10:00:00+02:00", "detalle": None}]})
    r = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=entorno))
    assert r["006b"].estado == exp.PENDIENTE
    assert exp.QUE_SIGNIFICA[exp.ESTANCADO] in r["006b"].motivo
    assert exp.QUE_SIGNIFICA[exp.PUEDE_MEJORAR] not in r["006b"].motivo


def test_lo_que_aun_puede_mejorar_lo_dice_en_su_motivo(tmp_path):
    entorno, _, _ = _escenario(tmp_path, historicos={"006b": [
        {"codigo": 17, "titulo": "", "fecha": "2026-09-11T10:00:00+02:00", "detalle": None}]})
    r = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=entorno))
    assert exp.QUE_SIGNIFICA[exp.PUEDE_MEJORAR] in r["006b"].motivo


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
    """Spec §5 regla 3: el aviso va en el plan Y en el manifiesto del certificado —desde la
    R2, en su clave `destinatario` (H-04)—."""
    partes = lambda w: [{"nombre": "ANA", "1apellido": "LOPEZ"},  # noqa: E731
                        {"nombre": "LUIS", "1apellido": "PEREZ"}]
    entorno, _, _ = _escenario(tmp_path, partes=partes,
                               destinatario_burofax="ANA LOPEZ Y LUIS PEREZ")
    r = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=entorno))
    m = json.loads(r["006b"].ruta_manifiesto.read_text(encoding="utf-8"))
    assert m["destinatario"] == {"comprobado": True, "avisos": [exp.AVISO_SOBRE_CONJUNTO]}
    m_correo = json.loads(r["006c"].ruta_manifiesto.read_text(encoding="utf-8"))
    assert exp.AVISO_SOBRE_CONJUNTO not in _avisos_del_manifiesto(m_correo)


def test_una_razon_social_con_Y_dentro_NO_es_un_sobre_conjunto(tmp_path):
    partes = lambda w: [{"nombre": "GARCIA Y ASOCIADOS, S.L."}]  # noqa: E731
    entorno, _, _ = _escenario(tmp_path, partes=partes,
                               destinatario_burofax="GARCIA Y ASOCIADOS, S.L.")
    r = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=entorno))
    m = json.loads(r["006b"].ruta_manifiesto.read_text(encoding="utf-8"))
    assert exp.AVISO_SOBRE_CONJUNTO not in _avisos_del_manifiesto(m)


def test_H05_sobre_conjunto_con_una_razon_social_que_LLEVA_Y(tmp_path):
    """R1/H-05: partir por « Y » rompía el nombre de la sociedad y el aviso no salía."""
    partes = lambda w: [{"nombre": "GARCIA Y ASOCIADOS, S.L."},  # noqa: E731
                        {"nombre": "ANA", "1apellido": "LOPEZ"}]
    entorno, _, _ = _escenario(tmp_path, partes=partes,
                               destinatario_burofax="GARCIA Y ASOCIADOS, S.L. Y ANA LOPEZ")
    r = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=entorno))
    m = json.loads(r["006b"].ruta_manifiesto.read_text(encoding="utf-8"))
    assert exp.AVISO_SOBRE_CONJUNTO in _avisos_del_manifiesto(m)


def test_R2_H06_un_destinatario_que_se_lee_como_UNA_parte_o_como_VARIAS_avisa(tmp_path):
    """R2/H-06, la sonda del revisor: si el nombre casa entero con una parte y TAMBIÉN se lee
    como dos, no se sabe a quién fue; la coincidencia íntegra callaba la otra lectura."""
    entorno, _, _ = _escenario(tmp_path)
    envio = next(e for e in exp.refrescar(W, "OVC", entorno_exp=entorno).envios
                 if e.canal == "burofax")
    ambiguo = dataclasses.replace(envio, destinatario="ANA Y LUIS")
    assert exp._atribucion_burofax(ambiguo, [{"nombre": "ANA"}, {"nombre": "LUIS"},
                                             {"nombre": "ANA Y LUIS"}]) == \
        exp.AVISO_DESTINATARIO_AMBIGUO
    # Los dos controles del otro lado: cada lectura, sola, sigue diciendo lo suyo.
    assert exp._atribucion_burofax(ambiguo, [{"nombre": "ANA Y LUIS"}]) is None
    assert exp._atribucion_burofax(ambiguo, [{"nombre": "ANA"}, {"nombre": "LUIS"}]) == \
        exp.AVISO_SOBRE_CONJUNTO
    # Y una entrega electrónica no tiene sobre: no se le atribuye nada.
    correo = dataclasses.replace(ambiguo, tipo="c")
    assert correo.canal == "electronico"
    assert exp._atribucion_burofax(correo, [{"nombre": "ANA"}, {"nombre": "LUIS"}]) is None


def test_R2_H07_la_cobertura_con_nombres_que_SE_SOLAPAN_no_explota(monkeypatch):
    """R2/H-07, la sonda del revisor: siete nombres que son prefijos unos de otros y un
    destinatario de 18 segmentos con un final que no casa hacían 250.904 llamadas. Se
    cuenta TRABAJO, como hizo el revisor, y no milisegundos: una versión que repita
    subproblemas pasa de mil llamadas enseguida y el test falla en vez de colgarse. Con
    200 segmentos responde, y la respuesta es la misma."""
    real, llamadas = exp._cubre, [0]

    def contada(*args, **kwargs):
        llamadas[0] += 1
        if llamadas[0] > 1000:
            raise AssertionError("la cobertura repite subproblemas: más de 1.000 llamadas")
        return real(*args, **kwargs)

    monkeypatch.setattr(exp, "_cubre", contada)
    nombres = {" y ".join(["ana"] * k) for k in range(1, 8)}
    assert exp._cubre(" y ".join(["ana"] * 18) + " y nadie", nombres) == -1
    assert exp._cubre(" y ".join(["ana"] * 200), nombres) == 200
    assert exp._cubre("ana y ana", {"ana", "ana y ana"}) == 2
    assert exp._cubre("ana y luis", {"ana"}) == -1


def test_H05_un_destinatario_que_no_casa_con_las_partes_AVISA_de_la_incertidumbre(tmp_path):
    """La comparación es con las partes de HOY: si no casan, no se afirma nada y se dice."""
    entorno, _, _ = _escenario(tmp_path, destinatario_burofax="PEDRO GOMEZ RUIZ")
    r = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=entorno))
    assert any("no se puede atribuir" in a for a in r["006b"].avisos), r["006b"].avisos
    assert exp.AVISO_SOBRE_CONJUNTO not in r["006b"].avisos


def test_si_el_CRM_no_responde_se_avisa_en_vez_de_callar(tmp_path):
    def sin_crm(w):
        raise exp.ExpedicionError("el caso no está indexado")

    entorno, _, _ = _escenario(tmp_path, partes=sin_crm)
    r = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=entorno))
    assert r["006b"].estado == exp.PRODUCIDO
    assert any("no se pudo comprobar si el sobre" in a for a in r["006b"].avisos)
    m = json.loads(r["006b"].ruta_manifiesto.read_text(encoding="utf-8"))
    assert m["destinatario"]["comprobado"] is False


def _crm_caido(w):
    raise RuntimeError("CRM temporalmente no disponible")


def test_R2_H04_una_segunda_corrida_con_el_CRM_CAIDO_no_para(tmp_path):
    """R2/H-04, la sonda del revisor: primera corrida con el CRM respondiendo, segunda con el
    CRM caído, mismos certificados y mismos PDF. El burofax quedaba PARADO por «avisos
    distintos»: la caída cambiaba el texto de un aviso, y el aviso era parte de la
    identidad del manifiesto. Lo que se comprobó al generarlo vale; hoy solo se dice que
    no se pudo volver a comprobar."""
    entorno, _, _ = _escenario(tmp_path)
    primera = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=entorno))
    antes = primera["006b"].ruta_manifiesto.read_bytes()
    segunda = _por_id(exp.preparar_aportables(
        W, "OVC", entorno_exp=dataclasses.replace(entorno, partes_de=_crm_caido)))
    assert segunda["006b"].estado == exp.YA_ESTABA, segunda["006b"].motivo
    assert segunda["006c"].estado == exp.YA_ESTABA
    assert primera["006b"].ruta_manifiesto.read_bytes() == antes
    assert any("no se ha podido volver a comprobar" in a for a in segunda["006b"].avisos)


def test_R2_H04_si_HOY_el_destinatario_AVISA_y_el_manifiesto_no_se_para(tmp_path):
    """El cambio de atribución que SÍ importa (R2/H-04, «definir qué cambios sustantivos
    requieren revisión»): el manifiesto no avisa de nada y hoy la comprobación sí. El
    aportable se acompañaría de un manifiesto que calla un aviso: se para para que lo
    mire una persona, y nada se pisa."""
    entorno, _, _ = _escenario(tmp_path)
    primera = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=entorno))
    antes = primera["006b"].ruta_manifiesto.read_bytes()
    otras = dataclasses.replace(entorno, partes_de=lambda w: [{"nombre": "PEDRO"}])
    segunda = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=otras))
    assert segunda["006b"].estado == exp.PARADO and "revísalo" in segunda["006b"].motivo
    assert primera["006b"].ruta_manifiesto.read_bytes() == antes
    assert segunda["006c"].estado == exp.YA_ESTABA


def test_R2_H04_si_el_manifiesto_YA_avisaba_otra_lectura_de_hoy_no_para(tmp_path):
    """Al revés no: si el manifiesto ya avisaba —aquí, porque el CRM no respondió al
    generarlo— su aviso ya dice lo que hace falta, y hoy solo se cuenta la diferencia."""
    entorno, _, _ = _escenario(tmp_path, partes=_crm_caido)
    exp.preparar_aportables(W, "OVC", entorno_exp=entorno)
    con_crm = dataclasses.replace(
        entorno, partes_de=lambda w: [{"nombre": "ANA", "1apellido": "LOPEZ"}])
    r = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=con_crm))
    assert r["006b"].estado == exp.YA_ESTABA
    assert any("no se pudo comprobar si el sobre" in a for a in r["006b"].avisos)
    assert any("hoy la comprobación del destinatario" in a for a in r["006b"].avisos)


def test_R2_H04_si_el_manifiesto_avisaba_y_HOY_TAMBIEN_avisa_no_para(tmp_path):
    """Los dos avisan —el manifiesto, porque el CRM no respondió al generarlo; hoy, porque el
    destinatario no se puede atribuir—: los dos acaban en lo mismo, la entrega en el
    domicilio. Vale el manifiesto y se cuenta la diferencia."""
    entorno, _, _ = _escenario(tmp_path, partes=_crm_caido)
    exp.preparar_aportables(W, "OVC", entorno_exp=entorno)
    otras = dataclasses.replace(entorno, partes_de=lambda w: [{"nombre": "PEDRO"}])
    r = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=otras))
    assert r["006b"].estado == exp.YA_ESTABA, r["006b"].motivo
    assert any("hoy la comprobación del destinatario" in a for a in r["006b"].avisos)


def test_R2_si_ESCRIBIR_falla_no_queda_un_fichero_a_medias(tmp_path, monkeypatch):
    """`_escribir_atomico`: temporal en el mismo directorio y `os.replace`. Si el reemplazo
    falla, el temporal se borra y el error sube: ni aportable a medias ni basura al lado."""
    entorno, _, carpeta = _escenario(tmp_path, archivar=("006c",))

    def falla(origen, destino):
        raise OSError("disco lleno")

    monkeypatch.setattr(exp.os, "replace", falla)
    with pytest.raises(OSError, match="disco lleno"):
        exp.preparar_aportables(W, "OVC", entorno_exp=entorno)
    assert not list(carpeta.glob("*.tmp")) and not list(carpeta.glob("* - APORTABLE.pdf"))


def test_un_integro_ILEGIBLE_para_ese_envio(tmp_path):
    def ilegible(pdf):
        raise certificado_lectura.CertificadoIlegibleError("no es un certificado")

    entorno, _, _ = _escenario(tmp_path)
    r = _por_id(exp.preparar_aportables(
        W, "OVC", entorno_exp=dataclasses.replace(entorno, leer_emisor=ilegible)))
    assert r["006c"].estado == exp.PARADO and "íntegro ilegible" in r["006c"].motivo


def test_R2_un_manifiesto_que_NO_ES_JSON_ni_se_acepta_ni_se_pisa(tmp_path):
    entorno, _, carpeta = _escenario(tmp_path)
    exp.preparar_aportables(W, "OVC", entorno_exp=entorno)
    manifiesto = exp.ruta_manifiesto(_integro_006c(carpeta))
    manifiesto.write_text("{esto no es json", encoding="utf-8")
    r = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=entorno))
    assert r["006c"].estado == exp.PARADO and "no corresponde" in r["006c"].motivo
    assert manifiesto.read_text(encoding="utf-8") == "{esto no es json"


def test_sin_envios_en_la_ventana_se_para_y_se_dice(tmp_path):
    """Un censo vacío no es una ausencia (spec §5.2): no se da por hecho que no haya nada."""
    entorno, t, _ = _escenario(tmp_path)
    t._envios = []
    with pytest.raises(exp.ExpedicionError, match="sin envíos"):
        exp.preparar_aportables(W, "OVC", entorno_exp=entorno)


def test_un_acta_electronica_sin_bloque_FICHEROS_para_todo(tmp_path):
    """Sin la lista del acta no hay contra qué verificar lo que se baja: para, y lo dice."""
    entorno, t, _ = _escenario(tmp_path)
    t._c["006c"] = s.pdf(["una página cualquiera, sin acta ni lista"])
    with pytest.raises(exp.ExpedicionError, match="FICHEROS ADJUNTOS"):
        exp.preparar_aportables(W, "OVC", entorno_exp=entorno)


#: Una salida TSV de Tesseract 5 con la forma medida (M-13): el nivel 4 es la línea, con su
#: caja; el 5, cada palabra; y hay filas de estructura (1-3) y palabras vacías.
_TSV = "\n".join("\t".join(map(str, fila)) for fila in [
    ("level", "page_num", "block_num", "par_num", "line_num", "word_num", "left", "top",
     "width", "height", "conf", "text"),
    (1, 1, 0, 0, 0, 0, 0, 0, 1654, 2339, -1, ""),
    (2, 1, 1, 0, 0, 0, 100, 200, 900, 90, -1, ""),
    (3, 1, 1, 1, 0, 0, 100, 200, 900, 90, -1, ""),
    (4, 1, 1, 1, 1, 0, 100, 200, 600, 40, -1, ""),
    (5, 1, 1, 1, 1, 1, 100, 200, 180, 40, 96.2, "Pago"),
    (5, 1, 1, 1, 1, 2, 300, 202, 400, 38, 95.1, "fraccionado"),
    (4, 1, 1, 1, 2, 0, 100, 250, 900, 40, -1, ""),
    (5, 1, 1, 1, 2, 1, 100, 250, 90, 40, 91.0, "de"),
    (5, 1, 1, 1, 2, 2, 200, 250, 100, 40, 95.0, " "),
    (5, 1, 1, 1, 2, 3, 310, 250, 250, 40, 93.3, "Honorarios"),
    (4, 1, 2, 1, 1, 0, 100, 900, 50, 40, -1, ""),
    (5, 1, 2, 1, 1, 1, 100, 900, 50, 40, 12.0, ""),
]) + "\n"


def test_R3_el_adaptador_agrupa_las_PALABRAS_de_Tesseract_en_LINEAS():
    """El puerto devuelve líneas con la caja del nivel 4 y las palabras del 5 en su orden;
    las palabras vacías no cuentan y una línea sin palabras no sale."""
    from core.certificado_aportable import Linea

    assert exp._lineas_de_tsv(_TSV) == (Linea("Pago fraccionado", 100, 200, 700, 240),
                                        Linea("de Honorarios", 100, 250, 1000, 290))


def test_R3_el_adaptador_dice_el_CODIGO_de_error_de_Tesseract(monkeypatch):
    """Un código distinto de 0 es un fallo, con lo que Tesseract dijo por `stderr`."""
    import subprocess

    monkeypatch.setattr(exp, "_binario_tesseract", lambda: "tesseract")
    monkeypatch.setattr(exp.subprocess, "run", lambda args, **kw: subprocess.CompletedProcess(
        args, 1, "", "Error opening data file spa.traineddata"))
    with pytest.raises(RuntimeError, match="código 1.*spa.traineddata"):
        exp._ocr_tesseract(b"\xff\xd8")


def test_R3_sin_Tesseract_se_dice_donde_se_ha_buscado(monkeypatch, tmp_path):
    monkeypatch.setattr(exp.shutil, "which", lambda nombre: None)
    monkeypatch.setattr(exp, "_TESSERACT_WINDOWS", tmp_path / "no-esta" / "tesseract.exe")
    with pytest.raises(RuntimeError, match="no se encuentra Tesseract"):
        exp._binario_tesseract()


def test_R2_sin_el_puerto_de_OCR_se_para(tmp_path):
    entorno, _, _ = _escenario(tmp_path)
    with pytest.raises(exp.ExpedicionError, match="`ocr`"):
        exp.preparar_aportables(W, "OVC", entorno_exp=dataclasses.replace(entorno, ocr=None))


def test_R2_si_el_OCR_FALLA_ese_envio_para_y_no_se_escribe_nada(tmp_path):
    def roto(imagen):
        raise RuntimeError("tesseract no está instalado")

    entorno, _, carpeta = _escenario(tmp_path, ocr=roto)
    r = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=entorno))
    assert r["006c"].estado == r["006b"].estado == exp.PARADO
    assert "no se pudo pasar el OCR" in r["006c"].motivo
    assert not list(carpeta.glob("* - APORTABLE.pdf"))
    assert not list(carpeta.glob("* - MANIFIESTO.json"))


def test_R2_el_aportable_ESCRITO_lleva_la_capa_de_texto_del_OCR(tmp_path):
    """Lo que pidió Nikolai el 2026-09-25: que una LLM lo pueda leer. Con el OCR honesto de
    los tests, el aportable que queda en el expediente se lee, y sin las condiciones."""
    from pypdf import PdfReader

    adjuntos = [s.refundido(), s.factura()]
    ocr = OcrContado(s.ocr_fiel(s.certificado(adjuntos, id_envio="006c")))
    entorno, _, _ = _escenario(tmp_path, archivar=("006c",), ocr=ocr)
    r = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=entorno))
    assert r["006c"].estado == exp.PRODUCIDO, r["006c"].motivo
    textos = [p.extract_text() or "" for p in
              PdfReader(io.BytesIO(r["006c"].ruta_aportable.read_bytes())).pages]
    assert "Factura A/R" in textos[-1] and not any("CONFIDENCIAL - CONDICIONES" in t
                                                   for t in textos)


def _sin_tesseract() -> bool:
    try:
        exp._binario_tesseract()
    except RuntimeError:
        return True
    return False


@pytest.mark.slow
def test_R3_el_OCR_REAL_deja_un_aportable_que_la_relectura_admite():
    """El adaptador de verdad —Tesseract, directo— sobre un certificado sintético: lo que
    lee casa con cada página, el aportable que se compone se relee byte a byte, se lee lo
    que se conserva y no las condiciones. Lento: lo corre `--runslow`."""
    from pypdf import PdfReader

    from core import certificado_aportable as apo

    if _sin_tesseract():
        pytest.skip("sin Tesseract")
    r, f = s.refundido(), s.factura()
    condiciones = apo.paginas_de_condiciones(
        [apo.DocumentoEnviado(a.nombre, a.contenido) for a in (r, f)])
    recorte = apo.recortar(s.certificado([r, f]), condiciones)
    hecho = apo.aportable_de(recorte, ocr=exp._ocr_tesseract)
    assert apo.verificar_aportable(hecho.pdf, recorte) == hecho.avisos == ()
    textos = [p.extract_text() or "" for p in PdfReader(io.BytesIO(hecho.pdf)).pages]
    assert len(textos) == 5 and "factura" in textos[-1].lower()
    assert not any(apo.lleva_rotulo(t) for t in textos)
    # Determinista: la misma imagen, las mismas líneas (M-13), el mismo fichero.
    assert apo.aportable_de(recorte, ocr=exp._ocr_tesseract).pdf == hecho.pdf


@pytest.mark.slow
def test_R3_el_OCR_REAL_lee_un_ESCANEO_con_las_condiciones_y_AVISA():
    """La sonda del revisor en la R3 (§2), con el OCR de verdad: una página conservada
    ESCANEADA —sin texto en el PDF— reproduce un fragmento de las condiciones sin su rótulo.
    El texto no la ve; el OCR sí, y el aportable sale con el aviso que nombra la página."""
    from core import certificado_aportable as apo

    if _sin_tesseract():
        pytest.skip("sin Tesseract")
    fragmento = ("Pago fraccionado de los Honorarios sin intereses. Se abonara en DOS plazos:\n"
                 "a. El primer 50% entre los dias 1 y 5 del mes siguiente a la primera "
                 "recepcion\nde la Oferta Vinculante Confidencial.")
    cert, condiciones = s.certificado_con_escaneo(fragmento)
    recorte = apo.recortar(cert, condiciones)
    assert recorte.conservadas == (1, 2) and recorte.normal[1] == ""
    hecho = apo.aportable_de(recorte, ocr=exp._ocr_tesseract)
    assert any("página 2 del certificado muestra en su imagen" in a for a in hecho.avisos), \
        hecho.avisos


def test_R2_H05_el_aviso_de_una_pagina_SIN_texto_viaja_al_manifiesto(tmp_path):
    adjuntos = [s.refundido(), s.Adjunto("BLANCO.pdf", ("",)), s.factura()]
    entorno, _, _ = _escenario(tmp_path, adjuntos=adjuntos)
    r = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=entorno))
    m = json.loads(r["006c"].ruta_manifiesto.read_text(encoding="utf-8"))
    assert any("'BLANCO.pdf'" in a and "no tiene texto" in a for a in m["avisos"])
    assert any("no tiene texto" in a for a in r["006c"].avisos)


def test_una_parada_del_recorte_es_de_ESE_envio_no_de_todos(tmp_path):
    entorno, t, _ = _escenario(tmp_path)
    t._c["006b"] = s.certificado([s.refundido(), s.factura()], id_envio="006b",
                                 burofax=True,
                                 reproduccion=[s.REQUERIMIENTO, s.OVC, s.FACTURA])
    carpeta = entorno.carpeta_certificados(W)
    (carpeta / exp.nombre_canonico("OFERTA VINCULANTE", W, "006b")).write_bytes(t._c["006b"])
    r = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=entorno))
    # Desde la R1 este certificado —sin la página de condiciones— lo para ANTES la
    # comprobación de que reproduce lo enviado (M-4); el «no aparece» de `recortar` sigue
    # siendo la última red y lo prueba `test_PARADA_1_…` en el módulo puro. Lo que este
    # test protege no cambia: la parada de UN envío no para a los demás.
    assert r["006b"].estado == exp.PARADO and "no reproduce" in r["006b"].motivo
    assert r["006c"].estado == exp.PRODUCIDO


def test_un_certificado_que_NO_reproduce_lo_enviado_para_ESE_envio(tmp_path):
    """R1, sobre M-4: el burofax lleva otro segundo documento que el correo."""
    entorno, t, carpeta = _escenario(tmp_path)
    otro = s.Adjunto("OTRA FACTURA.pdf",
                     ("Factura distinta, de otro expediente, con otros importes y conceptos",))
    t._c["006b"] = s.certificado([s.refundido(), otro], id_envio="006b", burofax=True)
    (carpeta / exp.nombre_canonico("OFERTA VINCULANTE", W, "006b")).write_bytes(t._c["006b"])
    r = _por_id(exp.preparar_aportables(W, "OVC", entorno_exp=entorno))
    assert r["006b"].estado == exp.PARADO and "no reproduce" in r["006b"].motivo
    assert r["006c"].estado == exp.PRODUCIDO


def test_sin_los_puertos_de_F2_se_para_en_vez_de_escribir_en_el_arbol_real(tmp_path):
    entorno, _, _ = _escenario(tmp_path)
    with pytest.raises(exp.ExpedicionError, match="carpeta_certificados"):
        exp.preparar_aportables(W, "OVC", entorno_exp=dataclasses.replace(
            entorno, carpeta_certificados=None))
