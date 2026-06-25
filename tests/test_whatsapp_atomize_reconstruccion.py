from core.whatsapp_atomize.reconstruccion import es_reenviado, detectar_enterrado


def test_reenviado_marcador():
    assert es_reenviado("‎Reenviado") is True
    assert es_reenviado("Forwarded") is True
    assert es_reenviado("hola que tal") is False


def test_email_pegado_recupera_autor():
    # Cabecera al INICIO del mensaje (caso soportado en v1, pass-through del body-scan).
    texto = "El 14 may 2024, a las 10:00, Juan <juan@ej.com> escribió:\n\nContenido"
    anc = detectar_enterrado(texto)
    assert anc is not None and anc.de == "juan@ej.com"


def test_reenviado_puro_sin_cabecera_no_inventa_autor():
    assert detectar_enterrado("‎Reenviado\nUn texto cualquiera sin direccion") is None


def test_preambulo_conversacional_no_soportado_v1():
    # LÍMITE v1: un preámbulo humano antes de la cabecera bloquea la detección (pass-through
    # puro, sin reposicionar la ventana → preserva la acotación-a-la-cabeza de G2). El caso
    # "os reenvío esto: + email pegado" se difiere a mejora futura (spec §16).
    texto = ("Mira lo que me mandaron:\n\n"
             "El 14 may 2024, a las 10:00, Juan <juan@ej.com> escribió:\n\nContenido")
    assert detectar_enterrado(texto) is None
