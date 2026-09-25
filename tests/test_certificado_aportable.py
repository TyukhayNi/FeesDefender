"""El aportable: el certificado íntegro sin las páginas que reproducen las condiciones."""
from __future__ import annotations

import hashlib
import io

import pytest

pytest.importorskip("reportlab", reason="hace falta para fabricar los certificados")
pytest.importorskip("pypdfium2", reason="el aportable es la IMAGEN del certificado (R2/H-01)")

from core import certificado_aportable as apo  # noqa: E402
from tests import _certificado_sintetico as s  # noqa: E402


# --- el bloque FICHEROS ADJUNTOS -----------------------------------------------

def test_la_huella_PARTIDA_en_dos_lineas_se_reconstruye():
    """M-5: 46 + 18 caracteres. Sin reconstruirla, ningún regex de 64 la encuentra."""
    r, f = s.refundido(), s.factura()
    listados = apo.ficheros_listados(s.certificado([r, f]))
    assert [x.nombre for x in listados] == ["OVC REFUNDIDA.pdf", "FACTURA 0000001.pdf"]
    assert listados[0].sha256 == hashlib.sha256(r.contenido).hexdigest()
    assert listados[1].sha256 == hashlib.sha256(f.contenido).hexdigest()


def test_el_burofax_lista_UN_fichero_el_fundido():
    """M-4: el burofax funde los adjuntos en un PDF de nombre UUID."""
    listados = apo.ficheros_listados(s.certificado([s.refundido(), s.factura()],
                                                   burofax=True))
    assert len(listados) == 1 and listados[0].nombre.endswith(".pdf")


def test_una_linea_que_no_es_ni_fichero_ni_huella_PARA():
    """Un nombre partido en dos líneas, o un formato nuevo, no se adivina."""
    texto = s.pagina_ficheros("006x", [("A.pdf", b"a")]).replace(
        "La autenticidad", "una linea que nadie ha medido\nLa autenticidad")
    with pytest.raises(apo.AportableError, match="no es ni un fichero"):
        apo.ficheros_listados_de_textos([texto])


def test_una_huella_CORTA_no_se_da_por_buena():
    texto = s.pagina_ficheros("006x", [("A.pdf", b"a")])
    cortado = "\n".join(l for l in texto.splitlines() if len(l) != 18)
    with pytest.raises(apo.AportableError, match="64"):
        apo.ficheros_listados_de_textos([cortado])


def test_sin_bloque_FICHEROS_se_dice_no_se_devuelve_vacio():
    with pytest.raises(apo.AportableError, match="FICHEROS ADJUNTOS"):
        apo.ficheros_listados_de_textos(["una página cualquiera"])


def test_H03_un_bloque_FUERA_del_acta_no_cuenta():
    """R1/H-03: el parser tomaba el primer «FICHEROS ADJUNTOS» del PDF, estuviera o no en
    el acta: una página de la reproducción que lo imitara suplantaba la lista."""
    falso = s.pagina_ficheros("006x", [("FALSO.pdf", b"falso")]).replace(s.MARCA_ACTA, "")
    real = s.pagina_ficheros("006x", [("A.pdf", b"a")])
    assert [x.nombre for x in apo.ficheros_listados_de_textos([falso, real])] == ["A.pdf"]


def test_H03_una_lista_SIN_su_cierre_no_se_da_por_completa():
    """Sin la línea de cierre la lista puede seguir en otra página: se para."""
    texto = s.pagina_ficheros("006x", [("A.pdf", b"a")])
    sin_cierre = "\n".join(l for l in texto.splitlines() if not l.startswith("La autenticidad"))
    with pytest.raises(apo.AportableError, match="cierre"):
        apo.ficheros_listados_de_textos([sin_cierre])


def test_H03_dos_bloques_en_el_acta_paran():
    uno = s.pagina_ficheros("006x", [("A.pdf", b"a")])
    otro = s.pagina_ficheros("006x", [("B.pdf", b"b")])
    with pytest.raises(apo.AportableError, match="más de un"):
        apo.ficheros_listados_de_textos([uno, otro])


def test_H03_la_lista_empieza_en_SU_cabecera_no_en_un_Huella_digital_anterior():
    """No se ancla a cualquier «Huella digital» de la página: solo a la cabecera de la
    lista, «Nombre Huella digital», DESPUÉS del rótulo FICHEROS ADJUNTOS."""
    texto = s.pagina_ficheros("006x", [("A.pdf", b"a")])
    trampa = texto.replace("CERTIFICADO DE CONTENIDO",
                           "Huella digital de otra cosa\nFALSO.pdf " + "0" * 46 + "\n" + "0" * 18
                           + "\nCERTIFICADO DE CONTENIDO")
    assert [x.nombre for x in apo.ficheros_listados_de_textos([trampa])] == ["A.pdf"]


def test_R2_H02_dos_bloques_en_la_MISMA_pagina_del_acta_paran():
    """R2/H-02: la unicidad se contaba por PÁGINAS con bloque, no por bloques: dos bloques
    completos en una misma página del acta pasaban, y mandaba el primero —el falso—."""
    falso = s.pagina_ficheros("006", [("FALSO.pdf", b"falso")])
    real = s.pagina_ficheros("006", [("REAL.pdf", b"real")])
    with pytest.raises(apo.AportableError, match="más de un"):
        apo.ficheros_listados_de_textos([falso + "\n" + real])


def test_un_PDF_roto_es_AportableError_no_la_excepcion_de_pypdf():
    with pytest.raises(apo.AportableError, match="PDF"):
        apo.ficheros_listados(b"esto no es un PDF")


# --- qué páginas son de condiciones ----------------------------------------------

def _doc(adjunto: s.Adjunto) -> apo.DocumentoEnviado:
    return apo.DocumentoEnviado(nombre=adjunto.nombre, contenido=adjunto.contenido)


def test_en_el_refundido_las_condiciones_son_la_TERCERA_pagina():
    """M-1: requerimiento, OVC y condiciones en un solo PDF; las condiciones, al final."""
    paginas = apo.paginas_de_condiciones([_doc(s.refundido()), _doc(s.factura())])
    assert [(p.documento, p.pagina) for p in paginas] == [("OVC REFUNDIDA.pdf", 3)]


def test_en_el_documento_PARTIDO_que_pide_el_spec_son_el_documento_entero():
    anexo = s.Adjunto("ANEXO II.pdf", (s.CONDICIONES,))
    requerimiento = s.Adjunto("A.pdf", (s.REQUERIMIENTO, s.OVC))
    paginas = apo.paginas_de_condiciones([_doc(requerimiento), _doc(anexo)])
    assert [(p.documento, p.pagina) for p in paginas] == [("ANEXO II.pdf", 1)]


def test_la_palabra_condiciones_SUELTA_no_es_el_rotulo():
    """M-7: sale en el requerimiento («las condiciones adjuntas») y en la factura
    («Condiciones de pago a la vista»). Casar por subcadena retiraría las dos."""
    assert "condiciones adjuntas" in s.REQUERIMIENTO
    assert "Condiciones de pago" in s.FACTURA
    assert apo.paginas_de_condiciones([_doc(s.factura()),
                                       _doc(s.Adjunto("A.pdf", (s.REQUERIMIENTO,)))]) == ()


def test_el_rotulo_tolera_caja_espacios_y_raya_tipografica():
    assert apo.lleva_rotulo("x\n  confidencial  -  condiciones  \ny")
    assert apo.lleva_rotulo("x\nCONFIDENCIAL \u2013 CONDICIONES\ny")
    # Hasta la R1 esto era `not`: se exigía la LÍNEA entera. H-02 enseñó que esa regla deja
    # fuera un rótulo partido por la extracción, y un rótulo más largo es, con más razón,
    # la cabecera de unas condiciones: se reconoce. Retirar de más, nunca de menos.
    assert apo.lleva_rotulo("x\nCONFIDENCIAL - CONDICIONES ECONÓMICAS DE PAGO\ny")


def test_H02_el_rotulo_PARTIDO_o_sin_espacios_se_reconoce():
    """R1/H-02: la extracción puede partir el rótulo en dos líneas o pegar el guion."""
    assert apo.lleva_rotulo("x\nCONFIDENCIAL -\nCONDICIONES\ny")
    assert apo.lleva_rotulo("x\nCONFIDENCIAL\n-\nCONDICIONES\ny")
    assert apo.lleva_rotulo("x\nCONFIDENCIAL-CONDICIONES\ny")


def test_H02_la_frase_sigue_sin_casar_con_las_palabras_SUELTAS():
    """El control del otro lado (M-7): el requerimiento real lleva «Oferta Vinculante
    Confidencial» y «las condiciones adjuntas» en la MISMA página, y no es el rótulo."""
    assert "Oferta Vinculante Confidencial" in s.REQUERIMIENTO
    assert "condiciones adjuntas" in s.REQUERIMIENTO
    assert apo.lleva_rotulo(s.REQUERIMIENTO) is False
    assert apo.lleva_rotulo("confidencial.\nCondiciones de pago a la vista") is False


def test_H02_un_SEGUNDO_documento_con_el_rotulo_partido_tambien_sale():
    """La sonda del revisor: el primer documento lleva el rótulo, así que la parada
    global por ausencia no salta, y el segundo —con el rótulo partido por la
    extracción— salía entero en el aportable, sin aviso, en los dos canales."""
    otras = s.Adjunto("OTRAS CONDICIONES.pdf", (
        "EV MMC Spain, S.L.U.\nCONFIDENCIAL -\nCONDICIONES\n"
        "Se ofrece una quita del setenta por ciento sobre la deuda reclamada si se paga\n"
        "en un solo plazo antes de fin de mes.",))
    r, f = s.refundido(), s.factura()
    condiciones = _condiciones(r, otras, f)
    assert [(c.documento, c.pagina) for c in condiciones] == [
        ("OVC REFUNDIDA.pdf", 3), ("OTRAS CONDICIONES.pdf", 1)]
    recorte, pdf = _aportable(s.certificado([r, otras, f]), condiciones)
    assert [x.pagina_certificado for x in recorte.retiradas] == [5, 6]
    assert not any("quita" in t for t in _textos(pdf))


def test_lo_que_SIGUE_al_rotulo_en_el_mismo_documento_tambien_sale():
    """Retirar de más, nunca de menos: si el rótulo no cae al final, sale lo que siga."""
    raro = s.Adjunto("RARO.pdf", (s.REQUERIMIENTO, s.CONDICIONES, "segunda hoja de pagos"))
    paginas = apo.paginas_de_condiciones([_doc(raro)])
    assert [p.pagina for p in paginas] == [2, 3]


#: La sonda del revisor en la R2 (H-03): el requerimiento CITA el título en su prosa.
_CITA = "\nEl anexo se titula «CONFIDENCIAL - CONDICIONES»."


def test_R2_H03_el_titulo_abre_las_condiciones_y_la_mencion_en_prosa_NO():
    """R2/H-03: desde la R1 bastaba la frase en cualquier sitio, y citar el título en el
    requerimiento retiraba el requerimiento entero como si fuera condiciones."""
    assert apo.abre_condiciones(s.CONDICIONES)
    assert apo.abre_condiciones("x\nCONFIDENCIAL -\nCONDICIONES\ny")     # partido: título
    assert apo.abre_condiciones("x\n  CONFIDENCIAL-CONDICIONES\ny")
    assert not apo.abre_condiciones(s.REQUERIMIENTO + _CITA)
    assert apo.lleva_rotulo(s.REQUERIMIENTO + _CITA)            # la red sigue viéndola


def test_R2_H03_citar_el_titulo_NO_retira_el_requerimiento():
    r = s.Adjunto("OVC REFUNDIDA.pdf", (s.REQUERIMIENTO + _CITA, s.OVC, s.CONDICIONES))
    assert [c.pagina for c in apo.paginas_de_condiciones([_doc(r)])] == [3]


def test_R2_H03_la_mencion_en_una_pagina_que_se_CONSERVA_para_y_dice_que_es_mencion():
    """Parar para revisión, no retirarla en silencio ni dejarla pasar: la red de la
    segunda parada la ve, y el mensaje dice que es una mención y no un título."""
    r = s.Adjunto("OVC REFUNDIDA.pdf", (s.REQUERIMIENTO + _CITA, s.OVC, s.CONDICIONES))
    f = s.factura()
    with pytest.raises(apo.AportableError, match="menciona el rótulo"):
        apo.recortar(s.certificado([r, f]), _condiciones(r, f))


def test_la_normalizacion_quita_la_cabecera_de_codicert():
    """M-3: sin la cabecera, original y copia coinciden al 100 %."""
    copia = "Código de envío: 006x Página: 7 de 8\n" + s.CONDICIONES
    assert apo.normalizar_pagina(copia) == apo.normalizar_pagina(s.CONDICIONES)


def test_la_huella_de_un_documento_enviado_es_la_de_sus_bytes():
    d = apo.DocumentoEnviado(nombre="x.pdf", contenido=b"abc")
    assert d.sha256 == hashlib.sha256(b"abc").hexdigest()


# --- el recorte ------------------------------------------------------------------

def _condiciones(*adjuntos):
    return apo.paginas_de_condiciones([_doc(a) for a in adjuntos])


def _textos(pdf):
    from pypdf import PdfReader
    return [p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages]


def _aportable(cert, condiciones, **ocr):
    """El aportable entero —la imagen y su capa de texto—, con el OCR honesto de los tests:
    el que lee la IMAGEN (`s.ocr_fiel`), no lo que el código cree haber conservado."""
    recorte = apo.recortar(cert, condiciones)
    return recorte, apo.aportable_de(recorte, ocr=s.ocr_fiel(cert, **ocr))


def test_retira_la_pagina_de_condiciones_y_conserva_todo_lo_demas():
    """El caso medido (M-1): acta 1-2, reproducción 3-6, condiciones en la 5."""
    r, f = s.refundido(), s.factura()
    recorte, pdf = _aportable(s.certificado([r, f]), _condiciones(r, f))
    assert recorte.paginas_acta == (1, 2)
    assert recorte.paginas_reproduccion == (3, 4, 5, 6)
    assert [x.pagina_certificado for x in recorte.retiradas] == [5]
    assert recorte.conservadas == (1, 2, 3, 4, 6)
    textos = _textos(pdf)
    assert len(textos) == 5
    assert not any(apo.lleva_rotulo(t) for t in textos)
    assert "Factura A/R" in textos[-1]          # la factura es prueba y se queda


def test_la_retirada_se_nombra_en_las_TRES_numeraciones():
    """Spec §7.3: página del documento, de la reproducción y del certificado."""
    r, f = s.refundido(), s.factura()
    (x,) = apo.recortar(s.certificado([r, f]), _condiciones(r, f)).retiradas
    assert (x.pagina_certificado, x.pagina_reproduccion) == (5, 3)
    assert (x.documento, x.pagina_documento) == ("OVC REFUNDIDA.pdf", 3)
    assert x.similitud >= apo.UMBRAL_COPIA


def test_el_BUROFAX_se_recorta_con_los_documentos_del_correo():
    """M-4: el fundido es la concatenación de los adjuntos del correo."""
    r, f = s.refundido(), s.factura()
    recorte = apo.recortar(s.certificado([r, f], burofax=True), _condiciones(r, f))
    assert [x.pagina_certificado for x in recorte.retiradas] == [5]


def test_PARADA_1_si_las_condiciones_no_aparecen_no_hay_aportable():
    """Spec §7.3: si las páginas de condiciones no se localizan TODAS, se para."""
    r, f = s.refundido(), s.factura()
    sin_ellas = s.certificado([r, f], reproduccion=[s.REQUERIMIENTO, s.OVC, s.FACTURA])
    with pytest.raises(apo.AportableError, match="no aparece en la reproducción"):
        apo.recortar(sin_ellas, _condiciones(r, f))


def test_la_MISMA_plantilla_de_OTRA_expedicion_no_se_toma_por_copia():
    """M-3: 0,877-0,939 entre expediciones distintas; el umbral está en 0,98.

    Un certificado que reproduce las condiciones de OTRO requerido no acredita las
    nuestras, y tomarlas por copia retiraría una página ajena dejando las nuestras sin
    localizar.
    """
    r, f = s.refundido(), s.factura()
    cert = s.certificado([r, f], reproduccion=[s.REQUERIMIENTO, s.OVC,
                                               s.CONDICIONES_DE_OTRA, s.FACTURA])
    with pytest.raises(apo.AportableError, match="no aparece"):
        apo.recortar(cert, _condiciones(r, f))


def test_PARADA_2_una_pagina_que_se_conserva_con_el_rotulo_para():
    """La red de la primera parada, por un instrumento independiente."""
    r, f = s.refundido(), s.factura()
    duplicada = "CONFIDENCIAL - CONDICIONES\nuna hoja que nadie mandó así"
    cert = s.certificado([r, f], reproduccion=[s.REQUERIMIENTO, s.OVC, s.CONDICIONES,
                                               duplicada, s.FACTURA])
    # El mensaje de ESTA parada —antes de escribir nada—, no el de la relectura, que
    # también diría «lleva el rótulo» y taparía que la red se hubiera caído.
    with pytest.raises(apo.AportableError, match="se conserva y lleva el rótulo"):
        apo.recortar(cert, _condiciones(r, f))


def test_PARADA_2_tambien_si_el_rotulo_esta_en_el_ACTA_que_no_se_recorta():
    """El acta reproduce asunto y cuerpo, y el acta no se recorta (spec §7.4, J-05)."""
    r, f = s.refundido(), s.factura()
    cert = s.certificado([r, f], acta_extra="Asunto:\nCONFIDENCIAL - CONDICIONES")
    with pytest.raises(apo.AportableError, match="ACTA"):
        apo.recortar(cert, _condiciones(r, f))


def test_una_pagina_de_condiciones_SIN_TEXTO_para():
    """Escaneada o en blanco: lo que no se puede localizar no se garantiza que salga."""
    vacia = apo.PaginaCondiciones(documento="ESCANEO.pdf", pagina=1, texto="  ")
    with pytest.raises(apo.AportableError, match="no tiene texto"):
        apo.recortar(s.certificado([s.refundido()]), [vacia])


def test_sin_condiciones_que_retirar_NO_se_produce_un_integro_sin_firma():
    with pytest.raises(apo.AportableError, match="íntegro"):
        apo.recortar(s.certificado([s.refundido()]), [])


def test_un_PDF_que_no_es_un_certificado_se_dice():
    r = s.refundido()
    with pytest.raises(apo.AportableError, match="no es un certificado"):
        apo.recortar(s.pdf([s.REQUERIMIENTO, s.CONDICIONES]), _condiciones(r))


def test_las_condiciones_DUPLICADAS_salen_las_dos():
    """Dos copias de la misma página en la reproducción: las dos son condiciones."""
    r, f = s.refundido(), s.factura()
    cert = s.certificado([r, f], reproduccion=[s.REQUERIMIENTO, s.OVC, s.CONDICIONES,
                                               s.CONDICIONES, s.FACTURA])
    recorte = apo.recortar(cert, _condiciones(r, f))
    assert [x.pagina_certificado for x in recorte.retiradas] == [5, 6]


def test_el_aportable_NO_lleva_el_widget_de_la_firma():
    """M-8: dejarlo pintaría un sello de firma sin firma detrás."""
    from pypdf import PdfReader

    r, f = s.refundido(), s.factura()
    for con_padre in (False, True):
        cert = s.con_firma(s.certificado([r, f]), con_padre=con_padre)
        assert PdfReader(io.BytesIO(cert)).pages[0].get("/Annots") is not None
        aportable = PdfReader(io.BytesIO(_aportable(cert, _condiciones(r, f))[1]))
        assert aportable.pages[0].get("/Annots") is None, con_padre
        assert aportable.trailer["/Root"].get("/AcroForm") is None


def test_R2_el_sello_de_firma_NO_se_pinta_en_la_imagen_aunque_su_apariencia_pinte():
    """M-8 sobre la imagen: rasterizar dibuja lo que se ve, y un widget con apariencia se ve
    en un visor. En los reales la apariencia no pinta nada (medido el 2026-09-25); aquí sí
    —un recuadro negro—, y aun así la página 1 del aportable es la del íntegro SIN él."""
    r, f = s.refundido(), s.factura()
    cert = s.con_firma(s.certificado([r, f]), visible=True)
    con, sin = s.render(cert, 1, anotaciones=True), s.render(cert, 1)
    assert s.distancia(con, sin) > 2, "control: el sello sintético SÍ pinta en un visor"
    (primera, *_) = s.imagenes(_aportable(cert, _condiciones(r, f))[1])
    assert s.distancia(primera, sin) < 1 < s.distancia(primera, con)


def test_R2_otra_anotacion_que_PINTA_no_se_pinta_y_se_AVISA():
    """Cualquier otra anotación con apariencia —aquí un sello `/Stamp`— se vería en un
    visor, y la imagen no la pinta: se dice, porque pudo pintar algo que haga falta."""
    r, f = s.refundido(), s.factura()
    cert = s.con_anotacion_visible(s.certificado([r, f]), pagina=3)
    con, sin = s.render(cert, 3, anotaciones=True), s.render(cert, 3)
    assert s.distancia(con, sin) > 2, "control: el sello SÍ pinta en un visor"
    recorte, pdf = _aportable(cert, _condiciones(r, f))
    tercera = s.imagenes(pdf)[2]
    assert s.distancia(tercera, sin) < 1 < s.distancia(tercera, con)
    assert any("página 3" in a and "/Stamp" in a for a in recorte.avisos), recorte.avisos


def test_el_recorte_es_DETERMINISTA():
    """M-8: la IMAGEN sale con los mismos bytes en dos corridas. Es lo que sostiene la
    idempotencia: el OCR no es determinista (fechas e identificadores propios), así que lo
    que se compara al volver a lanzar es la imagen (R2/H-01)."""
    r, f = s.refundido(), s.factura()
    cert = s.con_firma(s.certificado([r, f]))
    a = apo.recortar(cert, _condiciones(r, f))
    b = apo.recortar(cert, _condiciones(r, f))
    assert a.imagen == b.imagen and a.imagen.startswith(b"%PDF")


# --- R1, sobre M-4: el certificado reproduce lo que se bajó, o no se recorta ------

def test_la_reproduccion_EXACTA_de_los_documentos_pasa_en_los_dos_canales():
    """M-3 y M-4: en los reales, la reproducción es la concatenación exacta, en orden."""
    r, f = s.refundido(), s.factura()
    apo.comprobar_reproduccion(s.certificado([r, f]), [_doc(r), _doc(f)])
    apo.comprobar_reproduccion(s.certificado([r, f], burofax=True), [_doc(r), _doc(f)])


def test_un_burofax_con_OTRO_segundo_documento_para():
    """La sonda del revisor sobre M-4: cambia el segundo adjunto del burofax y conserva
    las condiciones, y F3 producía el aportable. La premisa estaba protegida por cómo
    construye F1, no comprobada por resultado."""
    r, f = s.refundido(), s.factura()
    otro = s.Adjunto("OTRA FACTURA.pdf",
                     ("Factura distinta, de otro expediente, con otros importes y conceptos",))
    cert = s.certificado([r, otro], burofax=True)
    with pytest.raises(apo.AportableError, match="no reproduce"):
        apo.comprobar_reproduccion(cert, [_doc(r), _doc(f)])


def test_una_pagina_de_MAS_en_la_reproduccion_para():
    r, f = s.refundido(), s.factura()
    cert = s.certificado([r, f], reproduccion=[s.REQUERIMIENTO, s.OVC, s.CONDICIONES,
                                               s.FACTURA, "una hoja que no salió en ningún documento"])
    with pytest.raises(apo.AportableError, match="páginas"):
        apo.comprobar_reproduccion(cert, [_doc(r), _doc(f)])


def test_una_pagina_SIN_texto_solo_la_acredita_la_cuenta():
    """Un escaneo no se casa por texto (spec §7.3): cuenta en el total, no se compara —y
    desde la R2 (H-05) se DICE, en vez de darla por comprobada en silencio—."""
    r, escaneo = s.refundido(), s.Adjunto("ESCANEO.pdf", ("",))
    avisos = apo.comprobar_reproduccion(s.certificado([r, escaneo]), [_doc(r), _doc(escaneo)])
    assert any("'ESCANEO.pdf'" in a and "no tiene texto" in a for a in avisos), avisos


def test_R2_H05_una_pagina_CORTA_sustituida_por_otra_para():
    """R2/H-05, la sonda del revisor: por debajo de 40 caracteres no se comparaba nada, y
    un «Recibo 40 EUR» sustituido por una quita pasaba la comprobación."""
    r, corto = s.refundido(), s.Adjunto("CORTO.pdf", ("Recibo 40 EUR",))
    cert = s.certificado([r, corto], reproduccion=[
        s.REQUERIMIENTO, s.OVC, s.CONDICIONES,
        "Quita confidencial del setenta por ciento a cambio de pago inmediato."])
    with pytest.raises(apo.AportableError, match="letra a letra"):
        apo.comprobar_reproduccion(cert, [_doc(r), _doc(corto)])


def test_R2_H05_una_pagina_corta_IDENTICA_pasa():
    r, corto = s.refundido(), s.Adjunto("CORTO.pdf", ("Recibo 40 EUR",))
    assert apo.comprobar_reproduccion(s.certificado([r, corto]), [_doc(r), _doc(corto)]) == ()


def test_R2_H05_una_copia_con_texto_de_un_original_SIN_texto_para():
    r, blanco = s.refundido(), s.Adjunto("BLANCO.pdf", ("",))
    cert = s.certificado([r, blanco], reproduccion=[s.REQUERIMIENTO, s.OVC, s.CONDICIONES,
                                                    "Quita del 70 %"])
    with pytest.raises(apo.AportableError, match="letra a letra"):
        apo.comprobar_reproduccion(cert, [_doc(r), _doc(blanco)])


# --- R1/H-01 y R2/H-01: lo que viaja DENTRO del PDF, no solo lo que se ve --------

def _objetos_pagina(pdf) -> int:
    """Cuántos objetos `/Type /Page` hay en el FICHERO, cuelguen o no del árbol."""
    from pypdf import PdfReader
    from pypdf.generic import DictionaryObject

    lector, cuenta = PdfReader(io.BytesIO(pdf)), 0
    for num in range(1, int(lector.trailer["/Size"])):
        try:
            objeto = lector.get_object(num)
        except Exception:  # noqa: BLE001 — entradas libres del xref
            continue
        cuenta += isinstance(objeto, DictionaryObject) and objeto.get("/Type") == "/Page"
    return cuenta


def test_H01_el_aportable_NO_arrastra_el_formulario_de_las_condiciones():
    """R1/H-01, y MEDIDO sobre los certificados reales, no solo en la sonda del revisor.

    Cada página de la reproducción dibuja un Form XObject (`q /TPL2 Do Q`) y los
    formularios de TODAS viven en un `/Resources` compartido. Copiar las páginas
    conservadas copiaba ese diccionario, y con él el formulario de la página retirada:
    invisible en el aportable y recuperable de su estructura con el texto entero de las
    condiciones. Lo llevaban los dos aportables del humo del 2026-09-25.
    """
    r, f = s.refundido(), s.factura()
    cert = s.con_formularios(s.certificado([r, f]))
    assert s.formularios_con_rotulo(cert), "control: el íntegro SÍ lo lleva"
    _, pdf = _aportable(cert, _condiciones(r, f))
    assert s.formularios_con_rotulo(pdf) == []
    textos = _textos(pdf)
    assert len(textos) == 5 and "Factura A/R" in textos[-1]   # lo conservado se sigue viendo


def test_H01_un_enlace_a_la_pagina_retirada_NO_la_mete_dentro():
    """La sonda del revisor: un `/Link` con `/Dest` a la página retirada arrastraba su objeto."""
    from pypdf import PdfReader

    r, f = s.refundido(), s.factura()
    cert = s.con_enlace_a(s.certificado([r, f]), desde=3, hacia=5)
    assert _objetos_pagina(cert) == 6
    recorte, pdf = _aportable(cert, _condiciones(r, f))
    assert _objetos_pagina(pdf) == len(recorte.conservadas) == 5
    assert all(p.get("/Annots") is None for p in PdfReader(io.BytesIO(pdf)).pages)


@pytest.mark.parametrize("via", s.VIAS_DE_FUGA)
def test_R2_H01_lo_que_la_pagina_conservada_NO_dibuja_no_viaja(via):
    """R2/H-01, las siete sondas del revisor: las condiciones en un recurso que la página
    conservada COMPARTE con la retirada sin dibujarlo —patrón, sombreado, fuente Type3,
    máscara, máscara de imagen, metadatos de un formulario, `/Contents` en un array
    indirecto—. Con el aportable estructural viajaban dentro de los siete, sin rótulo ni
    aviso: la poda solo miraba `Do`, y cerrar una vía dejaba abierta la siguiente.

    La imagen cierra la FRONTERA y no el ejemplo: lo que ninguna página conservada dibuja
    no está en el aportable, venga por la vía que venga.
    """
    cert = s.con_fuga(via)
    assert b"Pago fraccionado" in s.alcanzable_desde(cert, 3), "control: la sonda funciona"
    r, f = s.refundido(), s.factura()
    _, pdf = _aportable(cert, _condiciones(r, f))
    for marca in (b"CONFIDENCIAL - CONDICIONES", b"Pago fraccionado"):
        assert marca not in pdf and marca not in s.carga(pdf), (via, marca)


def test_R2_H01_catalogo_acciones_y_metadatos_del_integro_no_viajan():
    """El control del revisor sobre la raíz: marcadores en la estructura, los nombres, los
    marcadores, las acciones y los metadatos del catálogo, en el `/Info` y en claves de
    página. La imagen no los lee; la prueba es que no están."""
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject, TextStringObject

    r, f = s.refundido(), s.factura()
    w = PdfWriter(clone_from=PdfReader(io.BytesIO(s.certificado([r, f]))))
    marca = "MARCA-DE-LA-RAIZ-47389"
    meta = DecodedStreamObject()
    meta.set_data(marca.encode())
    meta.update({NameObject("/Type"): NameObject("/Metadata"),
                 NameObject("/Subtype"): NameObject("/XML")})
    ref_meta = w._add_object(meta)
    for clave in ("/StructTreeRoot", "/Names", "/Outlines", "/OpenAction", "/AA"):
        w._root_object[NameObject(clave)] = DictionaryObject(
            {NameObject("/Marca"): TextStringObject(marca)})
    w._root_object[NameObject("/Metadata")] = ref_meta
    w.add_metadata({"/Subject": marca})
    for clave in ("/Metadata", "/AA", "/PieceInfo", "/Thumb"):
        w.pages[2][NameObject(clave)] = ref_meta
    buffer = io.BytesIO()
    w.write(buffer)
    cert = buffer.getvalue()
    _, pdf = _aportable(cert, _condiciones(r, f))
    assert marca.encode() not in pdf and marca.encode() not in s.carga(pdf)


def test_R2_H01_una_imagen_en_linea_de_la_pagina_retirada_no_viaja():
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import DecodedStreamObject, NameObject

    r, f = s.refundido(), s.factura()
    w = PdfWriter(clone_from=PdfReader(io.BytesIO(s.certificado([r, f]))))
    en_linea = b"\nq BI /W 1 /H 1 /CS /RGB /BPC 8 ID \x18\x27\x36 EI Q\n"
    contenido = DecodedStreamObject()
    contenido.set_data(w.pages[4].get_contents().get_data() + en_linea)
    w.pages[4][NameObject("/Contents")] = w._add_object(contenido)
    buffer = io.BytesIO()
    w.write(buffer)
    _, pdf = _aportable(buffer.getvalue(), _condiciones(r, f))
    assert en_linea not in s.carga(pdf)


def test_R2_H01_un_formulario_de_condiciones_ANIDADO_en_otro_no_viaja():
    """Los dos controles del revisor sobre la recursión: el formulario de las condiciones
    dentro de otro exclusivo, y además colgado de un formulario que la conservada dibuja."""
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import (ArrayObject, DecodedStreamObject, DictionaryObject,
                               FloatObject, NameObject)

    r, f = s.refundido(), s.factura()
    w = PdfWriter(clone_from=PdfReader(io.BytesIO(s.con_formularios(s.certificado([r, f])))))
    xo = w.pages[2]["/Resources"]["/XObject"]
    secreto = xo.raw_get("/TPL2")
    exterior = DecodedStreamObject()
    exterior.set_data(b"q /Inner Do Q")
    exterior.update({NameObject("/Type"): NameObject("/XObject"),
                     NameObject("/Subtype"): NameObject("/Form"),
                     NameObject("/BBox"): ArrayObject([FloatObject(0), FloatObject(0),
                                                       FloatObject(595), FloatObject(842)]),
                     NameObject("/Resources"): DictionaryObject({NameObject("/XObject"):
                         DictionaryObject({NameObject("/Inner"): secreto})})})
    xo[NameObject("/TPL2")] = w._add_object(exterior)
    xo["/TPL0"]["/Resources"][NameObject("/XObject")] = DictionaryObject(
        {NameObject("/NoUsado"): secreto})
    buffer = io.BytesIO()
    w.write(buffer)
    cert = buffer.getvalue()
    assert s.formularios_con_rotulo(cert), "control: el íntegro SÍ lo lleva"
    _, pdf = _aportable(cert, _condiciones(r, f))
    assert s.formularios_con_rotulo(pdf) == [] and b"Pago fraccionado" not in s.carga(pdf)


# --- R2/H-01: la imagen es la de lo que se conserva, y solo eso ------------------

def test_R2_cada_pagina_del_aportable_es_la_IMAGEN_de_la_que_se_conserva():
    """Por los píxeles y con un render propio, no con el del código que se prueba: la
    imagen k es la página conservada k —no otra—, y la imagen no lleva texto propio."""
    r, f = s.refundido(), s.factura()
    cert = s.certificado([r, f])
    recorte = apo.recortar(cert, _condiciones(r, f))
    renders = {j: s.render(cert, j) for j in range(1, 7)}
    hechas = s.imagenes(recorte.imagen)
    assert len(hechas) == len(recorte.conservadas) == 5
    for imagen, n in zip(hechas, recorte.conservadas):
        propia = s.distancia(imagen, renders[n])
        otra = min(s.distancia(imagen, renders[j]) for j in renders if j != n)
        assert propia < 1 < otra, (n, propia, otra)
    assert all(not t.strip() for t in _textos(recorte.imagen))


# --- R2/H-01: la relectura del FICHERO, contra un perfil admitido -----------------

def _limpio():
    r, f = s.refundido(), s.factura()
    cert = s.certificado([r, f])
    recorte, pdf = _aportable(cert, _condiciones(r, f))
    return cert, recorte, pdf


def _retocar(pdf: bytes, cambio) -> bytes:
    """El aportable con `cambio(escritor)` aplicado: salidas FUERA del perfil, a propósito."""
    from pypdf import PdfReader, PdfWriter

    escritor = PdfWriter(clone_from=PdfReader(io.BytesIO(pdf)))
    cambio(escritor)
    buffer = io.BytesIO()
    escritor.write(buffer)
    return buffer.getvalue()


def test_R2_la_relectura_ACEPTA_el_aportable_limpio():
    """El control del otro lado: un verificador que lo rechazara todo pasaría los demás."""
    _, recorte, pdf = _limpio()
    apo.verificar_aportable(pdf, recorte)


def test_R2_H01_un_objeto_SUELTO_con_las_condiciones_para():
    """La sonda de la reescritura (R2/H-01): el formulario de las condiciones, con un
    comentario que le cambia la huella, metido SUELTO en una salida limpia. La relectura de
    la R1 lo aceptaba porque buscaba huellas conocidas; ahora todo objeto del fichero tiene
    que colgar de algo que el perfil admite."""
    from pypdf import PdfReader

    _, recorte, pdf = _limpio()
    origen = PdfReader(io.BytesIO(s.con_formularios(s.certificado([s.refundido(), s.factura()]))))
    prohibido = origen.pages[4]["/Resources"]["/XObject"]["/TPL2"]

    def meter(escritor):
        copia = prohibido.clone(escritor)
        copia.set_data(prohibido.get_data() + b"\n% reserializado sin cambio visual\n")

    malo = _retocar(pdf, meter)
    assert s.formularios_con_rotulo(malo), "control: el formulario está dentro"
    with pytest.raises(apo.AportableError, match="no cuelga de nada"):
        apo.verificar_aportable(malo, recorte)


def test_R2_un_objeto_de_PAGINA_suelto_para():
    """El enlace de la R1 (H-01) metía un objeto de página fuera del árbol: no se cuenta
    como página del aportable, pero está dentro del fichero."""
    from pypdf.generic import DictionaryObject, NameObject

    _, recorte, pdf = _limpio()
    malo = _retocar(pdf, lambda w: w._add_object(
        DictionaryObject({NameObject("/Type"): NameObject("/Page")})))
    with pytest.raises(apo.AportableError, match="no cuelga de nada"):
        apo.verificar_aportable(malo, recorte)


def test_R2_una_ANOTACION_en_el_aportable_para():
    from pypdf.generic import ArrayObject, DictionaryObject, NameObject

    def anotar(w):
        w.pages[0][NameObject("/Annots")] = ArrayObject([w._add_object(DictionaryObject({
            NameObject("/Type"): NameObject("/Annot"),
            NameObject("/Subtype"): NameObject("/Link")}))])

    _, recorte, pdf = _limpio()
    with pytest.raises(apo.AportableError, match="/Annots"):
        apo.verificar_aportable(_retocar(pdf, anotar), recorte)


@pytest.mark.parametrize("clave", ["/OpenAction", "/AcroForm", "/Names"])
def test_R2_una_clave_ajena_en_el_CATALOGO_para(clave):
    from pypdf.generic import DictionaryObject, NameObject

    def poner(w):
        w._root_object[NameObject(clave)] = DictionaryObject()

    _, recorte, pdf = _limpio()
    with pytest.raises(apo.AportableError, match="catálogo"):
        apo.verificar_aportable(_retocar(pdf, poner), recorte)


def test_R2_una_capa_de_texto_VISIBLE_para():
    """La capa del OCR es invisible (modo de render 3): una que se ve pintaría texto
    encima de la imagen, y el aportable dejaría de ser la imagen del certificado."""
    _, recorte, _ = _limpio()
    visible = s.con_capa_de_texto(recorte.imagen, ["texto"] * 5, modo=0)
    with pytest.raises(apo.AportableError, match="se VE"):
        apo.verificar_aportable(visible, recorte)


def test_R2_una_capa_de_texto_que_PINTA_para():
    _, recorte, _ = _limpio()
    pinta = s.con_capa_de_texto(recorte.imagen, ["texto"] * 5, operadores=b"0 0 100 100 re f")
    with pytest.raises(apo.AportableError, match="operador"):
        apo.verificar_aportable(pinta, recorte)


def test_R2_una_fuente_Type3_en_la_capa_de_texto_para():
    """Una Type3 DIBUJA sus glifos con contenido propio: por ahí viajaba la sonda `font`."""
    _, recorte, _ = _limpio()
    con_type3 = s.con_capa_de_texto(recorte.imagen, ["texto"] * 5, fuente="/Type3")
    with pytest.raises(apo.AportableError, match="Type3"):
        apo.verificar_aportable(con_type3, recorte)


def test_R2_una_imagen_que_NO_es_la_de_la_imagen_producida_para():
    """Las imágenes del aportable son, byte a byte, las del raster: el OCR no las toca."""
    from pypdf.generic import NameObject

    def cruzar(w):
        uno, dos = (w.pages[k]["/Resources"]["/XObject"] for k in (0, 1))
        (a,), (b,) = ([k for k in x if x[k].get_object().get("/Subtype") == "/Image"]
                      for x in (uno, dos))
        uno[NameObject(a)], dos[NameObject(b)] = dos.raw_get(b), uno.raw_get(a)

    _, recorte, pdf = _limpio()
    with pytest.raises(apo.AportableError, match="la imagen de la página 1"):
        apo.verificar_aportable(_retocar(pdf, cruzar), recorte)


def test_R2_un_contenido_de_pagina_que_PINTA_para():
    """La página solo dibuja su imagen y su capa de texto: nada más en su contenido."""
    def pintar(w):
        contenido = w.pages[0]["/Contents"].get_object()
        contenido.set_data(b"0 0 100 100 re f\n" + contenido.get_data())

    _, recorte, pdf = _limpio()
    with pytest.raises(apo.AportableError, match="contenido de la página 1"):
        apo.verificar_aportable(_retocar(pdf, pintar), recorte)


def test_R2_una_imagen_de_MAS_en_una_pagina_para():
    from pypdf.generic import NameObject

    def duplicar(w):
        xo = w.pages[0]["/Resources"]["/XObject"]
        otra = next(k for k in w.pages[1]["/Resources"]["/XObject"]
                    if w.pages[1]["/Resources"]["/XObject"][k].get("/Subtype") == "/Image")
        xo[NameObject("/Im9")] = w.pages[1]["/Resources"]["/XObject"].raw_get(otra)

    _, recorte, pdf = _limpio()
    with pytest.raises(apo.AportableError, match="2 imágenes en la página 1"):
        apo.verificar_aportable(_retocar(pdf, duplicar), recorte)


def test_R2_un_nodo_del_arbol_con_RECURSOS_heredables_para():
    """Un `/Resources` en el nodo de páginas lo heredan las páginas que no lo digan: por
    ahí se colaría en ellas lo que no llevan."""
    from pypdf.generic import DictionaryObject, NameObject

    def heredar(w):
        w._root_object["/Pages"].get_object()[NameObject("/Resources")] = DictionaryObject()

    _, recorte, pdf = _limpio()
    with pytest.raises(apo.AportableError, match="nodo del árbol"):
        apo.verificar_aportable(_retocar(pdf, heredar), recorte)


def test_R2_una_caja_de_pagina_distinta_de_la_de_su_imagen_para():
    from pypdf.generic import ArrayObject, FloatObject, NameObject

    def agrandar(w):
        w.pages[0][NameObject("/MediaBox")] = ArrayObject(
            [FloatObject(0), FloatObject(0), FloatObject(700), FloatObject(900)])

    _, recorte, pdf = _limpio()
    with pytest.raises(apo.AportableError, match="caja de página"):
        apo.verificar_aportable(_retocar(pdf, agrandar), recorte)


@pytest.mark.parametrize("donde", ["info", "xmp"])
def test_R2_el_rotulo_en_los_METADATOS_del_aportable_para(donde):
    from pypdf.generic import DecodedStreamObject, NameObject

    def poner(w):
        if donde == "info":
            w.add_metadata({"/Subject": "CONFIDENCIAL - CONDICIONES"})
            return
        meta = DecodedStreamObject()
        meta.set_data(b"<x:xmpmeta>CONFIDENCIAL - CONDICIONES</x:xmpmeta>")
        meta.update({NameObject("/Type"): NameObject("/Metadata"),
                     NameObject("/Subtype"): NameObject("/XML")})
        w._root_object[NameObject("/Metadata")] = w._add_object(meta)

    _, recorte, pdf = _limpio()
    with pytest.raises(apo.AportableError, match="rótulo de las condiciones"):
        apo.verificar_aportable(_retocar(pdf, poner), recorte)


def test_R2_una_pagina_GIRADA_para():
    from pypdf.generic import NameObject, NumberObject

    def girar(w):
        w.pages[0][NameObject("/Rotate")] = NumberObject(90)

    _, recorte, pdf = _limpio()
    with pytest.raises(apo.AportableError, match="gira"):
        apo.verificar_aportable(_retocar(pdf, girar), recorte)


# --- R2/H-01: la capa de texto, y lo que el OCR lee en ella ------------------------

def _con_raster_de(monkeypatch, sustituciones: dict[int, int]):
    """Un error de índices forzado: la imagen de la página `a` en el sitio de la `b`."""
    real = apo._rasterizar
    monkeypatch.setattr(apo, "_rasterizar", lambda cert, paginas: real(
        cert, [sustituciones.get(n, n) for n in paginas]))


def test_R2_si_el_OCR_lee_el_ROTULO_en_el_aportable_para(monkeypatch):
    """La red de la capa de texto: si la imagen de la página retirada acaba dentro —aquí,
    un error de índices que se fuerza—, el OCR lee su rótulo."""
    r, f = s.refundido(), s.factura()
    cert = s.certificado([r, f])
    _con_raster_de(monkeypatch, {4: 5})
    recorte = apo.recortar(cert, _condiciones(r, f))
    with pytest.raises(apo.AportableError, match="lleva el rótulo"):
        apo.aportable_de(recorte, ocr=s.ocr_fiel(cert))


def test_H07_la_relectura_para_una_COPIA_de_las_condiciones_aunque_el_OCR_no_lea_el_rotulo(
        monkeypatch):
    """R1/H-07 sobre la imagen: cada comprobación, su test. Si el OCR no lee el rótulo, la
    página se sigue pareciendo más a la retirada que a la que tocaba. La imagen retirada va
    a la página 1, que NO es vecina de la 5: así esto lo para la comparación con las
    retiradas y no la de las vecinas, que tiene su propio test."""
    r, f = s.refundido(), s.factura()
    cert = s.certificado([r, f])
    _con_raster_de(monkeypatch, {1: 5})
    recorte = apo.recortar(cert, _condiciones(r, f))
    with pytest.raises(apo.AportableError, match="página 5 del certificado, que se retira"):
        apo.aportable_de(recorte, ocr=s.ocr_fiel(cert, lee_rotulo=False))


def test_H07_misma_cuenta_de_paginas_pero_una_EQUIVOCADA_para(monkeypatch):
    """R1/H-07: una página conservada en el sitio de otra —la cuenta es la misma—. Ahora lo
    ve el texto que el OCR lee en la imagen: se parece más a la vecina que a la suya."""
    r, f = s.refundido(), s.factura()
    cert = s.certificado([r, f])
    _con_raster_de(monkeypatch, {3: 4, 4: 3})
    recorte = apo.recortar(cert, _condiciones(r, f))
    with pytest.raises(apo.AportableError, match="se parece más a la página 4"):
        apo.aportable_de(recorte, ocr=s.ocr_fiel(cert))


def test_H07_la_relectura_para_el_ROTULO_aunque_el_texto_no_case():
    """El OCR lee el rótulo en una página que por lo demás es la que tocaba."""
    r, f = s.refundido(), s.factura()
    cert = s.certificado([r, f])
    recorte = apo.recortar(cert, _condiciones(r, f))
    with pytest.raises(apo.AportableError, match="lleva el rótulo"):
        apo.aportable_de(recorte, ocr=s.ocr_fiel(cert, extra={3: "CONFIDENCIAL - CONDICIONES"}))


def test_PARADA_3_se_verifica_el_resultado_no_la_aritmetica():
    """Si lo que vuelve del OCR no es el aportable —aquí, el íntegro entero—, no se entrega."""
    r, f = s.refundido(), s.factura()
    cert = s.certificado([r, f])
    recorte = apo.recortar(cert, _condiciones(r, f))
    with pytest.raises(apo.AportableError, match="páginas y debían ser"):
        apo.aportable_de(recorte, ocr=lambda imagen: cert)


def test_R2_si_el_OCR_FALLA_no_hay_aportable():
    """Sin capa de texto no se entrega: es lo que hace legible el aportable (Nikolai,
    2026-09-25), y una imagen muda no es lo que se pidió."""
    r, f = s.refundido(), s.factura()
    recorte = apo.recortar(s.certificado([r, f]), _condiciones(r, f))

    def roto(imagen):
        raise RuntimeError("tesseract no está instalado")

    with pytest.raises(apo.AportableError, match="OCR"):
        apo.aportable_de(recorte, ocr=roto)


# --- los avisos ------------------------------------------------------------------

def test_sobre_lo_MEDIDO_no_hay_avisos():
    """M-6: el caso limpio no avisa. Un aviso que salta siempre no avisa de nada."""
    r, f = s.refundido(), s.factura()
    assert apo.recortar(s.certificado([r, f]), _condiciones(r, f)).avisos == ()


def test_AVISA_si_el_requerimiento_repite_una_frase_de_las_condiciones():
    """Spec §7.4, rehecho con M-2 y M-6: la fuga se reconoce por el texto de las
    condiciones, no por las cifras — el requerimiento real lleva la deuda en euros."""
    fuga = s.REQUERIMIENTO + ("\nLes proponemos que el primer 50% entre los dias 1 y 5 del "
                              "mes siguiente")
    r = s.Adjunto("OVC REFUNDIDA.pdf", (fuga, s.OVC, s.CONDICIONES))
    f = s.factura()
    avisos = apo.recortar(s.certificado([r, f]), _condiciones(r, f)).avisos
    assert len(avisos) == 1 and "página 3" in avisos[0] and "frase" in avisos[0]


def test_la_deuda_en_euros_del_requerimiento_NO_avisa():
    """M-2: 1.234,56 EUR en el requerimiento y en la factura son la deuda, no la oferta."""
    r, f = s.refundido(), s.factura()
    assert "1.234,56 EUR" in s.REQUERIMIENTO and "1.234,56" in s.FACTURA
    avisos = apo.recortar(s.certificado([r, f]), _condiciones(r, f)).avisos
    assert not any("EUR" in a or "€" in a for a in avisos)


@pytest.mark.parametrize("palabras", [5, 6])
def test_con_5_o_6_palabras_el_aviso_saltaria_en_FALSO(monkeypatch, palabras):
    """M-6, y es el control de la calibración: los sintéticos llevan las dos fuentes de
    falso positivo medidas —la cuenta repetida en la factura y «de la Oferta Vinculante
    Confidencial» en el requerimiento—, así que con menos de 8 palabras el caso limpio
    avisaría. Si esto deja de avisar con 5 o 6, el fixture ya no reproduce lo medido y
    `test_sobre_lo_MEDIDO_no_hay_avisos` ya no protege el umbral."""
    monkeypatch.setattr(apo, "PALABRAS_AVISO", palabras)
    r, f = s.refundido(), s.factura()
    assert apo.recortar(s.certificado([r, f]), _condiciones(r, f)).avisos != ()


def test_la_despedida_y_el_membrete_compartidos_NO_avisan():
    """Lo de antes del rótulo y lo de después de «Sin otro particular» lo comparten el
    requerimiento y las condiciones; sin cortarlo, el aviso saltaría en todo envío."""
    r, f = s.refundido(), s.factura()
    assert "Sin otro particular" in s.OVC and "Sin otro particular" in s.CONDICIONES
    assert apo.recortar(s.certificado([r, f]), _condiciones(r, f)).avisos == ()


def test_H06_la_despedida_del_PRIMER_documento_no_corta_las_frases_del_SEGUNDO():
    """R1/H-06: el corte de «Sin otro particular» era UNO sobre todas las palabras
    juntas, así que la despedida del primer documento dejaba fuera del aviso todo lo que
    viniera después. Un segundo documento de condiciones cuya frase reproduce el acta
    —que no se recorta— salía sin aviso."""
    frase = "Se ofrece una quita del setenta por ciento sobre la deuda si se paga de una vez."
    otras = s.Adjunto("ANEXO QUITA.pdf",
                      (f"CONFIDENCIAL - CONDICIONES\n{frase}\nSin otro particular, atentamente",))
    r, f = s.refundido(), s.factura()
    cert = s.certificado([r, otras, f], acta_extra="Asunto:\n" + frase)
    avisos = apo.recortar(cert, _condiciones(r, otras, f)).avisos
    assert any(a.startswith("la página 1 del certificado repite") for a in avisos), avisos


def test_AVISA_de_una_pagina_arrastrada_sin_rotulo():
    """Retirar de más tiene un coste —se pierde prueba— y se dice."""
    raro = s.Adjunto("RARO.pdf", (s.REQUERIMIENTO, s.CONDICIONES,
                                  "segunda hoja: detalle de los pagos y de su calendario"))
    recorte = apo.recortar(s.certificado([raro]), _condiciones(raro))
    assert [x.pagina_certificado for x in recorte.retiradas] == [4, 5]
    assert any("página 3 de 'RARO.pdf'" in a and "no lleva el rótulo" in a
               for a in recorte.avisos)


# --- el manifiesto ---------------------------------------------------------------

def _manifiesto(**cambios):
    import json

    r, f = s.refundido(), s.factura()
    cert = s.certificado([r, f])
    recorte = apo.recortar(cert, _condiciones(r, f))
    kw = dict(id_envio="006sint", canal="electronico", id_personalizado="W-000AAA - OVC",
              generado="2026-09-25T10:00:00+00:00", integro_nombre="X - W-000AAA-006sint.pdf",
              integro_sha256=hashlib.sha256(cert).hexdigest(),
              aportable_nombre="X - W-000AAA-006sint - APORTABLE.pdf",
              aportable_sha256="a" * 64,
              emisor={"razon_social": "EV MMC SPAIN, S.L.U.", "usuario": "madrid.bd",
                      "verificado": True},
              ficheros_acta=apo.ficheros_listados(cert),
              documentos=[_doc(r), _doc(f)])
    kw.update(cambios)
    m = apo.manifiesto_de(recorte, **kw)
    json.dumps(m, ensure_ascii=False)       # serializable, o revienta aquí
    return m, recorte, cert


def test_el_manifiesto_trae_lo_que_pide_el_spec():
    """Spec §7.4: código de envío, sha256 del íntegro, huellas tal como las lista el
    acta, páginas conservadas y retiradas, y el emisor verificado."""
    m, recorte, cert = _manifiesto()
    assert m["id_envio"] == "006sint"
    assert m["integro"]["sha256"] == hashlib.sha256(cert).hexdigest()
    # La huella del fichero ESCRITO: el OCR no es determinista y el recorte ya no sabe
    # cuál saldrá (R2/H-01); la da quien lo escribe.
    assert m["aportable"]["sha256"] == "a" * 64
    assert [x["nombre"] for x in m["acta"]["ficheros_listados"]] == [
        "OVC REFUNDIDA.pdf", "FACTURA 0000001.pdf"]
    assert m["conservadas"] == [1, 2, 3, 4, 6]
    (retirada,) = m["retiradas"]
    assert retirada["pagina_certificado"] == 5 and retirada["pagina_documento"] == 3
    assert m["emisor"]["verificado"] is True


def test_el_manifiesto_dice_que_el_aportable_NO_lleva_firma():
    m, _, _ = _manifiesto()
    assert "no conserva la firma" in m["firma"] and "326.4" in m["firma"]


def test_el_manifiesto_lleva_los_avisos_del_recorte_y_los_de_fuera():
    """Los de fuera son, desde la R2, los de la comprobación de la reproducción (H-05): el
    sobre conjunto va aparte, en `destinatario` (H-04)."""
    m, _, _ = _manifiesto(avisos_extra=["la página 1 de 'X.pdf' no tiene texto"])
    assert any("no tiene texto" in a for a in m["avisos"])


def test_R2_H04_lo_del_destinatario_va_APARTE_de_los_avisos_del_aportable():
    """R2/H-04: el aviso del destinatario depende del CRM del día —de si respondió, de
    cómo se llaman hoy las partes—, y metido entre los avisos del aportable hacía que una
    caída del CRM volviera «distinto» un manifiesto idéntico. Va en su propia clave."""
    aviso = "⚠ sobre conjunto: acredita entrega EN EL DOMICILIO, no a cada uno"
    m, _, _ = _manifiesto(destinatario={"comprobado": True, "avisos": [aviso]})
    assert m["destinatario"] == {"comprobado": True, "avisos": [aviso]}
    assert aviso not in m["avisos"]
    assert "destinatario" not in _manifiesto()[0]       # el correo no lo lleva


def test_R2_el_manifiesto_dice_que_el_aportable_es_IMAGEN_con_texto_OCR():
    """Lo que el aportable ES, dicho donde se archiva: la imagen de lo conservado y un texto
    leído por OCR, que puede equivocarse. El texto fiel es el del íntegro."""
    m, _, _ = _manifiesto()
    assert "imagen" in m["aportable"]["forma"] and "OCR" in m["aportable"]["forma"]
    assert "OCR" in m["texto"] and "íntegro" in m["texto"]
    assert m["version"] == 2


def test_el_manifiesto_documenta_los_documentos_con_su_huella():
    m, _, _ = _manifiesto()
    r = s.refundido()
    assert {"nombre": r.nombre,
            "sha256": hashlib.sha256(r.contenido).hexdigest()} in m["documentos_enviados"]
