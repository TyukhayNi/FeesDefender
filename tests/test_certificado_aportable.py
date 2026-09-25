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
