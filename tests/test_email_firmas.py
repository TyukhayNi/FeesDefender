"""Localizar la firma de un correo, sin fiarse del marcador.

Verdad de campo medida el 2026-09-04 sobre los 6 .eml de W-02Q38C: SOLO 3 traen el
marcador (`-- ` / «Enviado desde mi…»). Los otros 3 llevan la firma al final del cuerpo
sin marcador ninguno. Anclar en el marcador pierde la mitad EN SILENCIO.

Los esqueletos de abajo son los reales; los datos, inventados.
"""
import pytest

from core.email_firmas import BloqueFirma, desmarcar, localizar_bloques

# --- Plantilla «Barcelona»: nombre en negrita, cargo en linea suelta, Telf + Movil ---
FIRMA_BCN = """\
ENGEL&VÖLKERS
*Ana Ejemplo Ficticia*
Asesora Inmobiliaria

EV MMC SPAIN, S.L.U.
Avinguda Falsa, 12, planta baja
08301 Ciudad Inventada

Telf: +34 93 111 22 33

Móvil: *612 34 56 78*

ana@engelvoelkers.com
"""

# --- Plantilla «Madrid»: nombre y cargo en negrita, Tel. Fijo con extension, sin movil ---
FIRMA_MAD = """\
*Berta Ejemplo Ficticia *

*Técnico de PBC.*

ENGEL&VÖLKERS

*Calle Falsa 34 planta 5ª, Madrid 28001, España*
Tel. Fijo: +34 912 345 678 / Ext. 1234
Mailto: berta@engelvoelkers.com

Este correo electrónico así como cualquier anexo adjunto son confidenciales.
"""


class TestDesmarcar:

    def test_quita_las_marcas_de_cita(self):
        assert desmarcar("> hola\n> mundo") == "hola\nmundo"

    def test_quita_marcas_anidadas(self):
        assert desmarcar(">> hola") == "hola"

    def test_NO_quita_los_asteriscos_de_negrita(self):
        """La Task 7 los necesita para saber cual es la linea del nombre."""
        assert desmarcar("> *Ana*") == "*Ana*"

    def test_un_mayor_que_a_media_linea_no_se_toca(self):
        assert desmarcar("a > b") == "a > b"


class TestDesmarcarPreservaElNumeroDeLineas:
    """H-02: `>` solo (sin nada detras) no debe fusionar la linea con la siguiente.

    `\\s` incluye el salto de linea, asi que `^\\s*>+\\s?` se comia el `\\n` cuando la
    linea de cita era exactamente `>`. La task siguiente cruza el numero de linea del
    bloque desmarcado con las zonas citadas del texto original: si `desmarcar` cambia
    el recuento de lineas, ese cruce se desalinea.
    """

    @pytest.mark.parametrize("texto", [
        ">\nfoo\nbar",
        ">>\nfoo\nbar",
        "> \nfoo\nbar",
        ">\n\nfoo\nbar",
        "foo\n>\nbar\n>\nbaz",
        "> hola\n> mundo\n",
        ">> hola\n",
        "foo\n>>\n>\nbar",
    ])
    def test_desmarcar_no_cambia_el_numero_de_lineas(self, texto):
        assert len(desmarcar(texto).splitlines()) == len(texto.splitlines())


class TestElMarcadorNoEsNecesario:
    """El hallazgo H-01: 3 de 6 no lo traen."""

    def test_una_firma_SIN_marcador_se_encuentra(self):
        cuerpo = "Te paso el domicilio.\n\nSaludos.\n\n" + FIRMA_BCN
        bloques = localizar_bloques(cuerpo, fichero="a.eml")
        assert len(bloques) >= 1
        assert "Móvil:" in bloques[0].texto

    def test_una_firma_CON_marcador_se_encuentra(self):
        cuerpo = "Adjunto la oferta.\n\n-- \n" + FIRMA_BCN
        bloques = localizar_bloques(cuerpo, fichero="b.eml")
        assert len(bloques) >= 1
        assert "Móvil:" in bloques[0].texto

    @pytest.mark.parametrize("marcador", ["-- ", "--", "Enviado desde mi iPhone",
                                          "Sent from my iPad", "Obtener Outlook para Android"])
    def test_los_marcadores_conocidos_no_estorban(self, marcador):
        cuerpo = f"Texto.\n\n{marcador}\n" + FIRMA_BCN
        assert localizar_bloques(cuerpo, fichero="c.eml")

    def test_el_marcador_APRIETA_el_limite_superior(self):
        """Con marcador, la prosa que SI cabria en la ventana fija de 12 no entra.

        H-03: con `FIRMA_BCN` completa (13 lineas) la ventana fija ya coincide con el
        arranque de la firma, y el test pasaba aunque se borrara toda la logica del
        marcador (`previos = []`). Aqui la prosa esta dentro de la ventana de 12 lineas
        contando hacia atras desde el email SOLO gracias al marcador: sin el, la
        ventana fija por si sola alcanzaria la prosa.
        """
        cuerpo = "PROSA QUE NO ES FIRMA\n-- \nENGEL&VÖLKERS\nana@engelvoelkers.com\n"
        bloque = localizar_bloques(cuerpo, fichero="d.eml")[0]
        assert "PROSA QUE NO ES FIRMA" not in bloque.texto

    def test_el_marcador_no_entra_en_el_bloque(self):
        """H-04: cuando el marcador gana el max() frente a la ventana, el bloque
        empieza DESPUES del marcador, no en la propia linea `-- `.

        Con `FIRMA_BCN` completa (13 lineas) la ventana ya coincide con el arranque
        de la firma y nunca deja ver este defecto: hace falta un caso donde el
        marcador este mas cerca del email que la ventana fija, para que sea el
        marcador el que decida `inicio`.
        """
        cuerpo = "PROSA QUE NO ES FIRMA\n-- \nENGEL&VÖLKERS\nana@engelvoelkers.com\n"
        bloque = localizar_bloques(cuerpo, fichero="d2.eml")[0]
        assert not bloque.texto.lstrip().startswith("--")

    def test_sin_marcador_el_bloque_se_limita_a_una_ventana(self):
        """Sin marcador no se puede ser exacto, pero tampoco se arrastra el correo entero."""
        cuerpo = "LINEA MUY LEJANA\n" + ("\n" * 30) + FIRMA_BCN
        bloque = localizar_bloques(cuerpo, fichero="e.eml")[0]
        assert "LINEA MUY LEJANA" not in bloque.texto


class TestLaCorroboracionEsOBLIGATORIA:
    """Una direccion suelta en un texto no es una firma. Sin esta puerta, cualquier
    correo que MENCIONE a un consultor produciria una «firma» suya inventada."""

    def test_una_direccion_suelta_NO_es_una_firma(self):
        cuerpo = ("Hola, escribe a ana@engelvoelkers.com y que te lo confirme ella.\n"
                  "Un saludo.\n")
        assert localizar_bloques(cuerpo, fichero="f.eml") == []

    def test_una_direccion_con_la_marca_corporativa_SI(self):
        cuerpo = "ENGEL&VÖLKERS\nana@engelvoelkers.com\n"
        assert localizar_bloques(cuerpo, fichero="g.eml")

    def test_una_direccion_con_etiqueta_de_telefono_SI(self):
        cuerpo = "Móvil: 612 34 56 78\nana@engelvoelkers.com\n"
        assert localizar_bloques(cuerpo, fichero="h.eml")

    def test_una_direccion_de_OTRO_dominio_no_se_mira(self):
        """El colaborador es personal de E&V. Un tercero no entra por aqui."""
        cuerpo = "ENGEL&VÖLKERS\nMóvil: 612 34 56 78\nalguien@otraempresa.example\n"
        assert localizar_bloques(cuerpo, fichero="i.eml") == []

    def test_EV_MMC_SPAIN_sola_en_su_linea_SI(self):
        cuerpo = "EV MMC SPAIN, S.L.U.\nana@engelvoelkers.com\n"
        assert localizar_bloques(cuerpo, fichero="i2.eml")

    def test_mencion_de_la_marca_en_medio_de_una_frase_NO_corrobora(self):
        """H-01: el corpus entero es correspondencia SOBRE E&V, asi que la marca
        aparece en cualquier parte no es una puerta: casi todo la cumpliria.
        La propiedad correcta es que la ventana tenga FORMA de firma (marca en su
        propia linea), no que la marca aparezca en algun sitio de la ventana."""
        cuerpo = ("Hemos hablado con Engel & Völkers y nos dicen que escribas a "
                  "ana@engelvoelkers.com\n")
        assert localizar_bloques(cuerpo, fichero="i3.eml") == []

    def test_mencion_en_medio_de_frase_con_direccion_en_otra_linea_tampoco(self):
        cuerpo = ("Hemos hablado con Engel & Völkers sobre la operacion.\n"
                  "ana@engelvoelkers.com\n")
        assert localizar_bloques(cuerpo, fichero="i4.eml") == []


class TestLoQueDevuelve:

    def test_es_un_BloqueFirma_con_fichero_y_linea(self):
        cuerpo = "Hola.\n\n" + FIRMA_BCN
        bloque = localizar_bloques(cuerpo, fichero="j.eml")[0]
        assert isinstance(bloque, BloqueFirma)
        assert bloque.fichero == "j.eml"
        assert bloque.linea >= 1, "1-indexed, para poder citarlo en el informe"

    def test_la_plantilla_de_Madrid_tambien(self):
        bloque = localizar_bloques(FIRMA_MAD, fichero="k.eml")[0]
        assert "Tel. Fijo:" in bloque.texto
