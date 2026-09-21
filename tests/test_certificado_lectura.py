"""Leer el emisor de un certificado de Codicert (art. 17.2), sin salirse del acta."""
from __future__ import annotations

import pytest

from core import certificado_lectura as cert

# Página 1 tal como la extrae `pypdf` de un certificado real (medido el 2026-09-21
# sobre 006catetonk). La «fi» ligada de «certificado»/«confianza» está reproducida a
# propósito: es lo que devuelve el extractor y el parser tiene que tragarla.
PAGINA_1 = """Este certiﬁcado contiene un sello temporal y se encuentra ﬁrmado digitalmente con un certiﬁcado reconocido.
Código de envío: 006catetonk Página: 1 de 8
Servicios de MailCertiﬁcado S.L., CIF B85804532, www.codicert.io
COMUNICACIÓN CERTIFICADA
DATOS DE EMISOR Y RECEPTOR
1. Datos del emisor.
Nombre y apellidos/Razón social: EV MMC SPAIN, S.L.U.
CIF: B12345678
2. Datos del receptor.
Enviado a: destino@ejemplo.es
DATOS DE LA COMUNICACIÓN:
Fecha y hora del envío: 10/09/2026 18:26:08 (CEST)
CERTIFICADO
Madrid, a 17 de septiembre de 2026
Servicios de MailCertiﬁcado S.L. certiﬁca que todos los datos contenidos en el presente documento corresponden al
Entrega Electrónica Certiﬁcada con identiﬁcador: 006catetonk del usuario dado de alta en la web www.codicert.io
con nombre de usuario madrid.bd.
"""


def test_lee_la_razon_social_del_bloque_del_emisor():
    e = cert.emisor_de_texto(PAGINA_1)
    assert e.razon_social == "EV MMC SPAIN, S.L.U."


def test_lee_el_usuario_CON_el_punto_del_dominio_y_SIN_el_de_la_frase():
    """M-4: el literal acaba en `madrid.bd.` — el punto final es de la frase.

    Un patrón que corte en el primer punto devuelve `madrid` y la comprobación
    contra `madrid.bd` falla; uno que se lo trague entero devuelve `madrid.bd.` y
    falla igual. Costó un falso resultado al medirlo.
    """
    assert cert.emisor_de_texto(PAGINA_1).usuario == "madrid.bd"


def test_CONTROL_NEGATIVO_un_certificado_ajeno_que_nos_MENCIONA_no_pasa():
    """M-3, y es el test que justifica todo este módulo.

    `EV MMC SPAIN` aparece NUEVE veces en un certificado real y solo UNA en el
    bloque del emisor: las otras ocho están en la reproducción del requerimiento,
    que nombra a E&V sin parar. Una verificación por búsqueda global daría
    «emisor correcto» sobre el certificado de OTRO remitente que nos cite — que es
    exactamente el documento que un tercero podría aportar.
    """
    ajeno = PAGINA_1.replace(
        "Nombre y apellidos/Razón social: EV MMC SPAIN, S.L.U.",
        "Nombre y apellidos/Razón social: INMOBILIARIA RIVAL, S.L.")
    ajeno += "\nEV MMC SPAIN, S.L.U. reclama honorarios a mi cliente.\n" * 8
    e = cert.emisor_de_texto(ajeno)
    assert e.razon_social == "INMOBILIARIA RIVAL, S.L."
    assert not cert.es_emisor_esperado(e, razon_social="EV MMC SPAIN, S.L.U.")


def test_el_control_positivo_del_mismo_instrumento():
    """Que muerda no basta: tiene que dejar pasar lo bueno."""
    assert cert.es_emisor_esperado(cert.emisor_de_texto(PAGINA_1),
                                   razon_social="EV MMC SPAIN, S.L.U.")


def test_la_comparacion_tolera_mayusculas_acentos_y_puntuacion():
    """Lo que varía sin cambiar la identidad: caja, tildes y signos."""
    for variante in ("ev mmc spain, s.l.u.", "EV MMC SPAIN S L U",
                     "Ev Mmc Spain, S.L.U."):
        e = cert.EmisorCertificado(razon_social=variante, usuario=None)
        assert cert.es_emisor_esperado(e, razon_social="EV MMC SPAIN, S.L.U."), variante


def test_y_NO_tolera_que_falten_los_SEPARADORES():
    """La otra dirección, que es la que decide si el control sirve de algo.

    `SLU` y `S.L.U.` son secuencias de tokens distintas, y normalizar hasta juntarlas
    obligaría a borrar TODOS los espacios — con lo que `EVMMCSPAINSLU` también casaría,
    y con él cualquier razón social que contenga las mismas letras seguidas. Un control
    de identidad del emisor se debilita al hacerlo más tolerante, no se mejora: se
    prefiere un falso negativo ruidoso, que un humano resuelve mirando el certificado,
    a un falso positivo silencioso que da por nuestro un certificado ajeno.
    """
    e = cert.EmisorCertificado(razon_social="EV MMC SPAIN SLU", usuario=None)
    assert not cert.es_emisor_esperado(e, razon_social="EV MMC SPAIN, S.L.U.")


def test_tambien_comprueba_el_usuario_cuando_se_le_pide():
    e = cert.emisor_de_texto(PAGINA_1)
    assert cert.es_emisor_esperado(e, razon_social="EV MMC SPAIN, S.L.U.",
                                   usuario="madrid.bd")
    assert not cert.es_emisor_esperado(e, razon_social="EV MMC SPAIN, S.L.U.",
                                       usuario="valencia.bd")


def test_un_usuario_ILEGIBLE_no_pasa_la_comprobacion_de_plaza():
    """Ausencia no es coincidencia: si no se lee la cuenta, no se acredita."""
    e = cert.EmisorCertificado(razon_social="EV MMC SPAIN, S.L.U.", usuario=None)
    assert cert.es_emisor_esperado(e, razon_social="EV MMC SPAIN, S.L.U.")
    assert not cert.es_emisor_esperado(e, razon_social="EV MMC SPAIN, S.L.U.",
                                       usuario="madrid.bd")


def test_sin_bloque_de_emisor_NO_devuelve_vacio_sino_que_LANZA():
    """Un certificado del que no se puede leer el emisor no está «sin emisor»:
    está sin verificar, y eso para la cosecha (art. 17.2)."""
    with pytest.raises(cert.CertificadoIlegibleError, match="Datos del emisor"):
        cert.emisor_de_texto("un PDF cualquiera sin la estructura del acta")


def test_las_paginas_del_acta_se_reconocen_por_el_sello_temporal():
    """M-6/spec §7.2: el discriminante vale para burofax y entrega electrónica."""
    paginas = ["Este certiﬁcado contiene un sello temporal y se encuentra ﬁrmado",
               "Este certiﬁcado contiene un sello temporal y se encuentra ﬁrmado",
               "reproducción del documento", "más reproducción"]
    assert cert.paginas_de_acta_de_textos(paginas) == (1, 2)
