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
    recorte = apo.recortar(s.certificado([r, otras, f]), condiciones)
    assert [x.pagina_certificado for x in recorte.retiradas] == [5, 6]
    assert not any("quita" in t for t in _textos(recorte.pdf))


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


# --- R1/H-01: lo que viaja DENTRO del PDF, no solo lo que se ve ------------------

def _objetos_pagina(pdf) -> int:
    """Cuántos objetos `/Type /Page` hay en el FICHERO, cuelguen o no del árbol."""
    import io

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
    recorte = apo.recortar(cert, _condiciones(r, f))
    assert s.formularios_con_rotulo(recorte.pdf) == []
    textos = _textos(recorte.pdf)
    assert len(textos) == 5 and "Factura A/R" in textos[-1]   # lo conservado se sigue viendo


def test_H01_un_enlace_a_la_pagina_retirada_NO_la_mete_dentro():
    """La sonda del revisor: un `/Link` con `/Dest` a la página retirada arrastraba su objeto."""
    import io

    from pypdf import PdfReader

    r, f = s.refundido(), s.factura()
    cert = s.con_enlace_a(s.certificado([r, f]), desde=3, hacia=5)
    assert _objetos_pagina(cert) == 6
    recorte = apo.recortar(cert, _condiciones(r, f))
    assert _objetos_pagina(recorte.pdf) == len(recorte.conservadas) == 5
    assert all(p.get("/Annots") is None for p in PdfReader(io.BytesIO(recorte.pdf)).pages)


def test_H01_la_relectura_del_GRAFO_para_si_algo_se_cuela(monkeypatch):
    """Control positivo: si la poda no hace su trabajo, la relectura del grafo para.

    La relectura no puede depender de la poda —sería comprobar la aritmética con la
    aritmética—: recalcula en el original qué objetos USABAN solo las páginas retiradas y
    exige que ninguno esté en el fichero producido.
    """
    r, f = s.refundido(), s.factura()
    cert = s.con_formularios(s.certificado([r, f]))
    monkeypatch.setattr(apo, "_podar", lambda pagina, lector: set())
    with pytest.raises(apo.AportableError, match="arrastra"):
        apo.recortar(cert, _condiciones(r, f))


def test_H01_la_relectura_del_grafo_cuenta_las_PAGINAS_del_fichero(monkeypatch):
    """El otro lado del control: el enlace sin podar mete un objeto de página de más."""
    r, f = s.refundido(), s.factura()
    cert = s.con_enlace_a(s.certificado([r, f]), desde=3, hacia=5)
    monkeypatch.setattr(apo, "_podar", lambda pagina, lector: set())
    with pytest.raises(apo.AportableError, match="objetos de página"):
        apo.recortar(cert, _condiciones(r, f))


def test_PARADA_3_se_verifica_el_resultado_no_la_aritmetica(monkeypatch):
    """Si el PDF producido no es el que tocaba, no se entrega (verificar por resultado)."""
    r, f = s.refundido(), s.factura()
    cert = s.certificado([r, f])
    monkeypatch.setattr(apo, "_sin_paginas", lambda lector, conservadas: cert)
    with pytest.raises(apo.AportableError, match="aportable"):
        apo.recortar(cert, _condiciones(r, f))


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
    assert m["aportable"]["sha256"] == recorte.sha256
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
    m, _, _ = _manifiesto(avisos_extra=["⚠ sobre conjunto: acredita entrega EN EL "
                                        "DOMICILIO, no a cada uno"])
    assert any("sobre conjunto" in a for a in m["avisos"])


def test_el_manifiesto_documenta_los_documentos_con_su_huella():
    m, _, _ = _manifiesto()
    r = s.refundido()
    assert {"nombre": r.nombre,
            "sha256": hashlib.sha256(r.contenido).hexdigest()} in m["documentos_enviados"]
