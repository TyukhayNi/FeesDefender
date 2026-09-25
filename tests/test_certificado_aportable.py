"""El aportable: el certificado íntegro sin las páginas que reproducen las condiciones."""
from __future__ import annotations

import hashlib

import pytest

pytest.importorskip("reportlab", reason="hace falta para fabricar los certificados")

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
    assert not apo.lleva_rotulo("x\nCONFIDENCIAL - CONDICIONES ECONÓMICAS DE PAGO\ny")


def test_lo_que_SIGUE_al_rotulo_en_el_mismo_documento_tambien_sale():
    """Retirar de más, nunca de menos: si el rótulo no cae al final, sale lo que siga."""
    raro = s.Adjunto("RARO.pdf", (s.REQUERIMIENTO, s.CONDICIONES, "segunda hoja de pagos"))
    paginas = apo.paginas_de_condiciones([_doc(raro)])
    assert [p.pagina for p in paginas] == [2, 3]


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
    import io

    from pypdf import PdfReader
    return [p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages]


def test_retira_la_pagina_de_condiciones_y_conserva_todo_lo_demas():
    """El caso medido (M-1): acta 1-2, reproducción 3-6, condiciones en la 5."""
    r, f = s.refundido(), s.factura()
    recorte = apo.recortar(s.certificado([r, f]), _condiciones(r, f))
    assert recorte.paginas_acta == (1, 2)
    assert recorte.paginas_reproduccion == (3, 4, 5, 6)
    assert [x.pagina_certificado for x in recorte.retiradas] == [5]
    assert recorte.conservadas == (1, 2, 3, 4, 6)
    textos = _textos(recorte.pdf)
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
    with pytest.raises(apo.AportableError, match="lleva el rótulo"):
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
    import io

    from pypdf import PdfReader

    r, f = s.refundido(), s.factura()
    for con_padre in (False, True):
        cert = s.con_firma(s.certificado([r, f]), con_padre=con_padre)
        assert PdfReader(io.BytesIO(cert)).pages[0].get("/Annots") is not None
        aportable = PdfReader(io.BytesIO(apo.recortar(cert, _condiciones(r, f)).pdf))
        assert aportable.pages[0].get("/Annots") is None, con_padre
        assert aportable.trailer["/Root"].get("/AcroForm") is None


def test_el_recorte_es_DETERMINISTA():
    """M-8: mismos bytes en dos corridas. Es lo que sostiene la idempotencia."""
    r, f = s.refundido(), s.factura()
    cert = s.con_firma(s.certificado([r, f]))
    a = apo.recortar(cert, _condiciones(r, f))
    b = apo.recortar(cert, _condiciones(r, f))
    assert a.pdf == b.pdf and a.sha256 == b.sha256 == hashlib.sha256(a.pdf).hexdigest()


def test_PARADA_3_se_verifica_el_resultado_no_la_aritmetica(monkeypatch):
    """Si el PDF producido no es el que tocaba, no se entrega (verificar por resultado)."""
    r, f = s.refundido(), s.factura()
    cert = s.certificado([r, f])
    monkeypatch.setattr(apo, "_sin_paginas", lambda lector, conservadas: cert)
    with pytest.raises(apo.AportableError, match="aportable"):
        apo.recortar(cert, _condiciones(r, f))
