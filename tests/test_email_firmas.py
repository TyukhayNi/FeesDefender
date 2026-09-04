"""Localizar la firma de un correo, sin fiarse del marcador.

Verdad de campo medida el 2026-09-04 sobre los 6 .eml de W-02Q38C: SOLO 3 traen el
marcador (`-- ` / «Enviado desde mi…»). Los otros 3 llevan la firma al final del cuerpo
sin marcador ninguno. Anclar en el marcador pierde la mitad EN SILENCIO.

Los esqueletos de abajo son los reales; los datos, inventados.
"""
import pytest

from core.email_firmas import (BloqueFirma, Consolidado, DatosFirma, PROCEDENCIA_CITADO,
                               PROCEDENCIA_DIRECTO, VEREDICTO_CONFLICTO,
                               VEREDICTO_ENCONTRADO, VEREDICTO_FIRMA_SIN_CAMPO,
                               atribuir, consolidar, desmarcar, extraer_bloques,
                               leer_campos, limpiar_telefono, localizar_bloques,
                               zonas_citadas)

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

# --- Plantilla corta para una tercera persona: mismo esqueleto minimo que corrobora
# solo con la marca sola en su linea (ver test_una_direccion_con_la_marca_corporativa_SI).
FIRMA_CARLA = """\
ENGEL&VÖLKERS
carla@engelvoelkers.com
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
    """H-02 (R1) + Hallazgo E (R2): `>` solo (sin nada detras) no debe fusionar la
    linea con la siguiente.

    `\\s` incluye el salto de linea, asi que `^\\s*>+\\s?` se comia el `\\n` cuando la
    linea de cita era exactamente `>`. La task siguiente cruza el numero de linea del
    bloque desmarcado con las zonas citadas del texto original: si `desmarcar` cambia
    el recuento de lineas, ese cruce se desalinea.

    El instrumento de medida importa: `splitlines()` NO cuenta el segmento vacio
    final (`''.splitlines() == []`, `'>'.splitlines() == ['>']`), asi que comparar
    `len(desmarcar(t).splitlines())` con `len(t.splitlines())` puede dar un falso
    desajuste que no es un defecto de `desmarcar` sino del instrumento. Lo que la
    task siguiente necesita de verdad es que el INDICE de cada linea se conserve
    (la linea i del original es la linea i del desmarcado), y eso lo mide
    `split("\\n")`, que si cuenta el segmento final. Ver docstring de `desmarcar`.
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
        # Los seis casos con los que el revisor midio el desajuste de splitlines():
        ">",
        "foo\n>",
        "foo\n> ",
        "foo\nbar\n>",
        ">\nfoo\n>",
        "> ",
        # CRLF: lo que traen los .eml reales.
        "foo\r\n>\r\nbar",
        ">\r\n> \r\nfoo",
        "foo\r\n>\r\n",
        # Tabulador tras la marca.
        "foo\n>\t\nbar",
        # Linea de solo espacios, sin marca (no deberia cambiar nada).
        "foo\n   \nbar",
        # Texto vacio.
        "",
    ])
    def test_desmarcar_conserva_el_indice_de_linea(self, texto):
        assert len(desmarcar(texto).split("\n")) == len(texto.split("\n"))


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

    def test_prosa_que_EMPIEZA_con_la_razon_social_NO_corrobora(self):
        """Hallazgo B (R2): la cola libre `.*$` de la razon social admitia prosa
        con tal de que EMPEZARA por "EV MMC SPAIN". Es la misma patologia del
        Hallazgo 1 de R1, solo que limitada al inicio de linea. La propiedad es
        que la razon social este SOLA en su linea (con forma juridica y
        puntuacion alrededor), no que la linea EMPIECE por ella."""
        cuerpo = ("EV MMC SPAIN es la empresa que gestiona la operacion, cualquier duda\n"
                  "escribele a ana@engelvoelkers.com\n")
        assert localizar_bloques(cuerpo, fichero="i5.eml") == []

    def test_razon_social_con_forma_juridica_SA_tambien_corrobora(self):
        """La forma juridica no es solo S.L.U.: S.A. y S.L. tambien son la razon
        social sola en su linea, no cola libre."""
        cuerpo = "EV MMC SPAIN, S.A.\nana@engelvoelkers.com\n"
        assert localizar_bloques(cuerpo, fichero="i6.eml")

    def test_etiqueta_de_telefono_sin_forma_de_telefono_NO_corrobora(self):
        """Hallazgo C (R2): la etiqueta de telefono no comprobaba que hubiera un
        telefono detras. La propiedad es que, tras la etiqueta, la linea tenga
        FORMA de telefono (digitos/espacios/+-.()*<> y una extension opcional) y
        nada mas -- no que la etiqueta simplemente aparezca."""
        cuerpo = ("Teléfono de atención al cliente 900 123 456, para dudas generales\n"
                  "puedes escribir tambien a ana@engelvoelkers.com\n")
        assert localizar_bloques(cuerpo, fichero="i7.eml") == []

    def test_etiqueta_de_telefono_con_extension_SI_corrobora(self):
        """La forma real medida en la plantilla de Madrid: etiqueta, telefono,
        y una extension opcional al final ("/ Ext. NNNN")."""
        cuerpo = "Tel. Fijo: +34 912 345 678 / Ext. 1234\nana@engelvoelkers.com\n"
        assert localizar_bloques(cuerpo, fichero="i8.eml")

    def test_la_marca_partida_en_dos_lineas_por_un_salto_NO_corrobora(self):
        """Hallazgo D (R2): el `\\s*` interno de la alternativa de marca incluye
        el salto de linea, asi que "ENGEL" y "VOLKERS" corroboraban estando en
        lineas distintas (separadas por una linea en blanco, que no tiene forma
        de firma real). El separador interno correcto es `[ \\t]*`, que no cruza
        lineas. El precio deliberado: una marca partida por el ajuste de longitud
        del cliente de correo deja de reconocerse -- se prefiere perder una firma
        legitima a inventar una (ver comentario junto a `_RE_CORROBORA`)."""
        cuerpo = "ENGEL &\n   \nVÖLKERS\nana@engelvoelkers.com\n"
        assert localizar_bloques(cuerpo, fichero="i9.eml") == []


class TestBloqueCitadoLineaALinea:
    """Hallazgo A (R2, Critical): `_RE_CORROBORA` corria sobre el texto SIN
    desmarcar, y sus alternativas exigen inicio de linea (^): un `>` inicial las
    rompe todas. Es una REGRESION del arreglo de R1 (Hallazgo 1) y anula el
    escenario que motiva el modulo entero (docstring de cabecera: en 2 de los 6
    correos medidos la firma viene en un reenvio o en un bloque CITADO, y
    `BloqueFirma.procedencia == "citado"` nunca podria producirse si esto no se
    localiza). La propiedad: `localizar_bloques` no puede depender de si el
    llamador le paso el texto ya desmarcado -- lo desmarca por su cuenta al
    entrar, y como `desmarcar` es idempotente, un llamador que ya desmarco no
    sufre nada."""

    def test_una_firma_citada_linea_a_linea_se_localiza(self):
        firma_citada = "\n".join("> " + ln for ln in FIRMA_BCN.splitlines())
        cuerpo = "> Te reenvio esto de abajo.\n>\n" + firma_citada
        bloques = localizar_bloques(cuerpo, fichero="l.eml")
        assert len(bloques) >= 1
        assert "Móvil:" in bloques[0].texto
        assert ">" not in bloques[0].texto, "el texto del bloque sale ya sin las marcas de cita"


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


class TestLaFirmaNoEsLaDelRemitente:
    """EL GUARD CENTRAL. Medido: en 2 de los 6 .eml de W-02Q38C la firma del cuerpo
    pertenece a otra persona. Atribuir por cabecera escribe el telefono de A en la
    ficha de B, en el CRM del cliente."""

    def test_la_atribucion_sale_del_email_de_DENTRO_del_bloque(self):
        """El caso del REENVIO: `From:` es una persona, la firma es de otra."""
        cuerpo = "Te reenvio lo que me manda ella.\n\n" + FIRMA_BCN
        bloques, sin_atribuir = extraer_bloques(cuerpo, fichero="a.eml")

        assert [b.email for b in bloques] == ["ana@engelvoelkers.com"]
        assert sin_atribuir == 0

    def test_el_From_NO_influye_en_la_atribucion(self):
        """`extraer_bloques` no recibe el `From:`: no puede equivocarse con el."""
        import inspect
        firma = inspect.signature(extraer_bloques)
        assert "from" not in " ".join(firma.parameters).lower(), (
            "si el remitente entra aqui, alguien acabara atribuyendo por el")

    def test_dos_firmas_distintas_en_un_correo_se_separan(self):
        """Y cada una se queda con SU email, no con el primero del texto."""
        cuerpo = FIRMA_BCN + "\n\n" + FIRMA_MAD
        bloques, _ = extraer_bloques(cuerpo, fichero="c.eml")
        assert {b.email for b in bloques} == {"ana@engelvoelkers.com",
                                              "berta@engelvoelkers.com"}

    def test_cada_bloque_lleva_el_email_QUE_ESTA_DENTRO_de_el(self):
        """La forma fuerte del anterior: no basta con que el CONJUNTO sea correcto,
        cada bloque tiene que llevar el suyo. Un mutante que asigne a todos el primer
        email del texto pasaria el test de conjunto si solo se mirase `set()`."""
        cuerpo = FIRMA_BCN + "\n\n" + FIRMA_MAD
        bloques, _ = extraer_bloques(cuerpo, fichero="c.eml")
        for b in bloques:
            assert b.email in b.texto.lower(), (
                f"el bloque en linea {b.linea} lleva un email que no esta en su texto")


class TestElBloqueConservaSuEmailAncla:
    """El defecto ESPEJO del que ya se arreglo en esta misma task: `atribuir`
    volvia a buscar un email DENTRO del texto del bloque, y ese texto es una
    ventana de lineas alrededor del ancla que puede contener MAS de una
    direccion -- la del ancla y la de una firma vecina.

    Un implementador anterior ya se topo con la variante HACIA ATRAS (dos firmas
    consecutivas, la ventana de la SEGUNDA arrastraba el email de la PRIMERA) y
    la parcheo cambiando "primer match" por "ultimo match". Eso cerro ese
    ejemplo y dejo abierto el espejo: dos firmas seguidas donde la SEGUNDA es
    compacta, y la ventana hacia ATRAS de la primera firma llega a incluir
    tambien la segunda dentro de su propio texto -- el "ultimo match" del
    bloque de la PRIMERA pasa a ser el de la SEGUNDA.

    La propiedad correcta: un bloque se identifica con el email que lo ANCLO en
    `localizar_bloques`, nunca con el que se encuentre buscando en su texto.
    """

    def test_el_caso_espejo_dos_firmas_seguidas_la_segunda_compacta(self):
        """Repro literal del defecto: con el bug vivo, los DOS bloques salian
        atribuidos a berta, incluido el de Ana."""
        cuerpo = (
            "ENGEL&VOLKERS\n"
            "*Ana Ejemplo*\n"
            "Asesora\n"
            "Telf: +34 93 111 22 33\n"
            "ana@engelvoelkers.com\n"
            "\n"
            "ENGEL&VOLKERS\n"
            "berta@engelvoelkers.com\n"
        )
        bloques, sin_atribuir = extraer_bloques(cuerpo, fichero="espejo.eml")

        assert sin_atribuir == 0
        assert len(bloques) == 2
        assert bloques[0].texto.startswith("ENGEL&VOLKERS\n*Ana Ejemplo*"), (
            "el bloque anclado en la linea de Ana tiene que ser el primero de la lista")
        assert bloques[0].email == "ana@engelvoelkers.com", (
            "la firma de Ana no puede llevar el email de Berta")
        assert bloques[1].email == "berta@engelvoelkers.com"

    def test_el_caso_hacia_atras_dos_firmas_consecutivas_la_de_arriba_completa(self):
        """El caso que el implementador anterior SI cerro (ver docstring de la
        clase): dos firmas consecutivas separadas por una linea en blanco, la
        de arriba completa (`FIRMA_BCN`). Sigue teniendo que quedar bien tras
        este arreglo."""
        cuerpo = FIRMA_BCN + "\n\n" + FIRMA_MAD
        bloques, sin_atribuir = extraer_bloques(cuerpo, fichero="atras.eml")

        assert sin_atribuir == 0
        assert len(bloques) == 2
        assert bloques[0].email == "ana@engelvoelkers.com"
        assert bloques[1].email == "berta@engelvoelkers.com"

    def test_tres_firmas_el_conjunto_de_emails_sale_completo_y_sin_repetidos(self):
        """La forma general y fuerte: con tres firmas de tres personas
        distintas, el conjunto de emails atribuidos tiene que ser EXACTAMENTE
        el de las tres, sin repetidos. Con el defecto vivo, dos o tres bloques
        comparten email (el de una ventana que se solapa con la vecina) y el
        conjunto sale corto.

        `FIRMA_CARLA` va PEGADA a `FIRMA_MAD` (sin linea en blanco entre
        medias) a proposito: es lo que hace que el email de Carla caiga DENTRO
        de la ventana hacia delante del bloque de Berta, y por tanto lo que
        deja este caso realmente rojo con el defecto vivo (confirmado antes de
        escribir el arreglo)."""
        cuerpo = FIRMA_BCN + "\n\n" + FIRMA_MAD + FIRMA_CARLA
        bloques, sin_atribuir = extraer_bloques(cuerpo, fichero="tres.eml")

        assert sin_atribuir == 0
        emails = [b.email for b in bloques]
        assert set(emails) == {
            "ana@engelvoelkers.com", "berta@engelvoelkers.com", "carla@engelvoelkers.com",
        }
        assert len(emails) == len(set(emails)), (
            "con el defecto vivo, dos o tres bloques comparten email y el conjunto sale corto")

    def test_tres_firmas_no_se_pierde_ninguna(self):
        """Que ademas de sin repetidos, no falte ninguna: tiene que haber al
        menos un bloque por cada uno de los tres emails."""
        cuerpo = FIRMA_BCN + "\n\n" + FIRMA_MAD + FIRMA_CARLA
        bloques, _ = extraer_bloques(cuerpo, fichero="tres2.eml")

        for email in ("ana@engelvoelkers.com", "berta@engelvoelkers.com",
                      "carla@engelvoelkers.com"):
            assert any(b.email == email for b in bloques), f"falta el bloque de {email}"


class TestZonasCitadas:

    def test_una_zona_citada_se_detecta(self):
        texto = "hola\n> citado\n> mas citado\nadios"
        assert zonas_citadas(texto) == [(1, 3)]

    def test_sin_citas_no_hay_zonas(self):
        assert zonas_citadas("hola\nadios") == []

    def test_dos_zonas_separadas(self):
        texto = "a\n> uno\nb\n> dos"
        assert zonas_citadas(texto) == [(1, 2), (3, 4)]

    def test_un_texto_sin_citas_que_acaba_en_salto_no_inventa_zona(self):
        assert zonas_citadas("hola\nadios\n") == []

    def test_una_cita_al_final_sin_salto_final_se_cuenta(self):
        assert zonas_citadas("hola\n> citado") == [(1, 2)]


class TestLaProcedenciaSeRegistra:
    """Un bloque citado es MAS ANTIGUO. La consolidacion (Task 8) lo usa para decidir
    cuando dos valores discrepan; aqui solo se registra con fidelidad."""

    @staticmethod
    def _citar(texto: str) -> str:
        return "\n".join("> " + ln for ln in texto.split("\n"))

    def test_una_firma_en_el_cuerpo_es_directa(self):
        bloques, _ = extraer_bloques("Hola.\n\n" + FIRMA_BCN, fichero="a.eml")
        assert bloques[0].procedencia == PROCEDENCIA_DIRECTO

    def test_una_firma_dentro_de_un_bloque_citado_es_citada(self):
        """El segundo caso real: la firma llega dentro del `> ` de la respuesta."""
        cuerpo = "Conforme, lo vemos manana.\n\n" + self._citar(FIRMA_BCN) + "\n"
        bloques, _ = extraer_bloques(cuerpo, fichero="b.eml")

        assert [b.email for b in bloques] == ["ana@engelvoelkers.com"]
        assert bloques[0].procedencia == PROCEDENCIA_CITADO

    def test_la_firma_citada_se_lee_DESMARCADA(self):
        bloques, _ = extraer_bloques(self._citar(FIRMA_BCN), fichero="c.eml")
        assert not bloques[0].texto.lstrip().startswith(">")
        assert "Movil:" in bloques[0].texto or "Telf:" in bloques[0].texto


class TestElCruceDeLineasSeAlinea:
    """[CORREGIDO] `zonas_citadas` cuenta sobre el ORIGINAL y `localizar_bloques`
    reporta `linea` sobre el DESMARCADO. `atribuir` cruza los dos, asi que las dos
    partes tienen que contar las lineas con la MISMA convencion.

    La garantia medida en la Task 5 es sobre `split("\\n")`: `splitlines()` no cuenta el
    segmento vacio final, y por eso un texto que acaba SIN salto de linea y cuya ultima
    linea es una marca de cita pelada desalinea los dos recuentos.
    """

    @staticmethod
    def _citar(texto: str) -> str:
        return "\n".join("> " + ln for ln in texto.split("\n"))

    def test_citada_en_un_texto_que_TERMINA_en_salto(self):
        cuerpo = "Hola.\n\n" + self._citar(FIRMA_BCN) + "\n"
        bloques, _ = extraer_bloques(cuerpo, fichero="d.eml")
        assert bloques and bloques[0].procedencia == PROCEDENCIA_CITADO

    def test_citada_en_un_texto_que_NO_termina_en_salto(self):
        cuerpo = ("Hola.\n\n" + self._citar(FIRMA_BCN)).rstrip("\n")
        bloques, _ = extraer_bloques(cuerpo, fichero="e.eml")
        assert bloques and bloques[0].procedencia == PROCEDENCIA_CITADO

    def test_una_cita_pelada_al_final_no_descoloca_la_procedencia(self):
        """El caso exacto que la Task 5 midio como problematico: ultima linea `>` sin
        salto final. Si las convenciones no coinciden, la firma directa de arriba se
        marcaria citada o al reves."""
        cuerpo = "Hola.\n\n" + FIRMA_BCN + "\n> "
        bloques, _ = extraer_bloques(cuerpo.rstrip(), fichero="f.eml")
        assert bloques and bloques[0].procedencia == PROCEDENCIA_DIRECTO

    def test_directa_arriba_y_citada_abajo_en_el_mismo_correo(self):
        """Dos bloques, uno de cada procedencia, en un solo texto. Si el cruce esta
        desplazado, uno de los dos sale mal."""
        cuerpo = FIRMA_MAD + "\n\n" + self._citar(FIRMA_BCN) + "\n"
        bloques, _ = extraer_bloques(cuerpo, fichero="g.eml")
        por_email = {b.email: b.procedencia for b in bloques}
        assert por_email.get("berta@engelvoelkers.com") == PROCEDENCIA_DIRECTO
        assert por_email.get("ana@engelvoelkers.com") == PROCEDENCIA_CITADO

    def test_el_cruce_no_esta_desplazado_en_uno(self):
        """Hallazgo propio (Step 6, mutacion 3): ninguno de los tests anteriores
        distingue `_en_zona_citada(b.linea - 1, zonas)` de la version desplazada
        `_en_zona_citada(b.linea, zonas)`, porque en todos ellos la zona citada es
        ANCHA (toda la firma citada) y el desplazamiento de una linea nunca cruza
        su frontera.

        Este test aisla el cruce en `atribuir()` directamente, sin pasar por
        `localizar_bloques`: una zona citada de UNA SOLA linea que coincide
        exactamente con `b.linea - 1` (0-indexado). Con el desplazamiento de +1,
        esa zona de una linea nunca se detectaria para NINGUN bloque real -- el
        desplazamiento quedaria sin verificar para siempre.
        """
        texto_original = "a\n> \nc\n"
        assert zonas_citadas(texto_original) == [(1, 2)]
        bloque = BloqueFirma(texto="ana@engelvoelkers.com", email="ana@engelvoelkers.com",
                             linea=2, fichero="x.eml")

        atribuidos, sin_atribuir = atribuir([bloque], texto_original=texto_original)

        assert sin_atribuir == 0
        assert atribuidos[0].procedencia == PROCEDENCIA_CITADO


class TestElInvarianteQueRETIRO_UN_VEREDICTO:
    """`sin_atribuir` vale SIEMPRE 0, y de eso depende una decision de diseno.

    El §6 del spec preveia un veredicto `NO_ATRIBUIBLE` para «hay firma y no se sabe de
    quien es». Se **retiro por inalcanzable**: el ancla de un bloque es su propia linea
    de email, y desde el arreglo de la atribucion el bloque **conserva** ese email, asi
    que no existe un bloque sin email que contar. Fabricar un caso artificial para
    justificar la constante habria sido peor que dejar codigo muerto.

    La rama defensiva de `atribuir` y su contador se quedan como **invariante**, y este
    test es lo que lo vigila.

    **Si este test se pone rojo, NO lo ajustes.** Significa que alguien anadio una
    segunda via de deteccion —bloques anclados solo en el marcador, como la firma
    institucional sin direccion personal que se midio en un .eml de W-02Q38C— y entonces
    ese caso SI necesita un veredicto propio en vez de desaparecer del recuento.
    """

    @pytest.mark.parametrize("cuerpo", [
        "Hola.\n\n" + FIRMA_BCN,
        FIRMA_MAD,
        FIRMA_BCN + "\n\n" + FIRMA_MAD,
        "\n".join("> " + ln for ln in FIRMA_BCN.split("\n")),
        "ENGEL&VÖLKERS\n*Ana Ejemplo*\nAsesora\nMóvil: 612 34 56 78\n",
        "Nada de nada.\n",
        "",
        "ana@engelvoelkers.com",
    ])
    def test_sin_atribuir_es_siempre_CERO(self, cuerpo):
        _, sin_atribuir = extraer_bloques(cuerpo, fichero="inv.eml")
        assert sin_atribuir == 0

    def test_un_bloque_construido_SIN_email_si_se_cuenta(self):
        """La rama defensiva no es decorativa: si algun dia llega un bloque sin email,
        se descarta y se CUENTA. Lo que el invariante de arriba afirma es que hoy
        `localizar_bloques` no puede producirlo, no que la rama no exista."""
        huerfano = BloqueFirma(texto="ENGEL&VÖLKERS\nsin direccion", email="",
                               linea=1, fichero="x.eml")
        atribuidos, sin_atribuir = atribuir([huerfano], texto_original="irrelevante")

        assert atribuidos == []
        assert sin_atribuir == 1


class TestLimpiarTelefono:
    """`normalize_es_phone` no quita letras ni asteriscos: hay que limpiar antes."""

    @pytest.mark.parametrize("crudo,esperado", [
        ("*612 34 56 78*", "612345678"),
        ("+34 93 111 22 33", "931112233"),
        ("612.34.56.78", "612345678"),
        ("<612345678>", "612345678"),
        ("+34 912 345 678 / Ext. 1234", "912345678"),
        ("912 345 678 / Ext. 1234", "912345678"),
        ("  612345678  ", "612345678"),
    ])
    def test_los_casos_medidos(self, crudo, esperado):
        assert limpiar_telefono(crudo) == esperado

    def test_la_extension_no_es_parte_del_numero(self):
        """El CRM exige 9 digitos; con la extension pegada da HTTP 400 ([APER-14])."""
        assert limpiar_telefono("+34 912 345 678 / Ext. 1234") == "912345678"

    def test_un_valor_sin_digitos_no_produce_un_telefono(self):
        assert limpiar_telefono("*") == ""
        assert limpiar_telefono("None") == ""
        assert limpiar_telefono("") == ""

    def test_un_numero_extranjero_no_se_mutila(self):
        """`normalize_es_phone` deja los `+33…` intactos salvo separadores."""
        assert limpiar_telefono("+33 1 23 45 67 89") == "+33123456789"


class TestLimpiarTelefonoValidaLaFormaYNoSoloElDigito:
    """Defecto grave (medido 2026-09-04): el guard final era `any(c.isdigit() for c
    in v)`, que acepta CUALQUIER cosa que contenga un digito -- una guarda inerte.
    La propiedad correcta es que el valor limpio TENGA que SER un telefono: solo
    digitos, o un `+` seguido de solo digitos (los extranjeros que
    `normalize_es_phone` conserva a proposito). Cualquier otra cosa es basura del
    parseo y tiene que devolver "": mejor no tener el telefono que escribir una
    cadena rara en la ficha del cliente."""

    @pytest.mark.parametrize("crudo", [
        "612345678",
        "+34 93 111 22 33",
        "*612 34 56 78*",
        "912 345 678 / Ext. 1234",
        "+33 1 23 45 67 89",
    ])
    def test_los_valores_que_SI_son_telefono_sobreviven(self, crudo):
        assert limpiar_telefono(crudo) != ""

    @pytest.mark.parametrize("basura", [
        "movil:612345678",     # el repro exacto del defecto: la etiqueta cuela entera
        "Ext. 1234",           # extension sin numero delante
        "atencion al cliente 900 123 456 para dudas",
        None,
        "-",
        "*",
        "",
        "piso 3 puerta 2",     # texto y digitos mezclados
    ])
    def test_la_basura_con_digitos_NO_produce_un_telefono(self, basura):
        assert limpiar_telefono(basura) == ""


class TestLimpiarTelefonoExigeNueveDigitosEnEspana:
    """Hallazgo A (revision tasks 7-8, Important): "solo digitos" no es lo mismo que
    "es un telefono". El CRM exige 9 digitos exactos para un numero espanol y devuelve
    HTTP 400 (`movil is incorrect`) con cualquier otra longitud -- medido con un fijo y
    un movil pegados (13 digitos) y con un movil truncado (7 digitos). El codigo que
    escribe en el CRM se traga el error a proposito (perder el vinculo de un expediente
    por no poder escribir un telefono seria peor que quedarse sin el), asi que un valor
    que el CRM rechaza NO da un error visible: falla en silencio. Proponer un valor que
    sabemos que va a ser rechazado es peor que no proponer ninguno.

    La propiedad: un valor ESPANOL limpio es valido si y solo si son EXACTAMENTE 9
    digitos. Los EXTRANJEROS son la excepcion deliberada -- `normalize_es_phone` los
    deja intactos salvo separadores, y su longitud la decide su pais, no esta regla:
    un valor que empieza por `+` y no es `+34` no se somete a los 9 digitos."""

    @pytest.mark.parametrize("crudo", [
        "912.345.678.1234",   # 13 digitos: un fijo y un movil pegados
        "912 345 678 1234",   # lo mismo con espacios en vez de puntos
        "6123456",            # 7 digitos: un movil truncado
    ])
    def test_una_longitud_espanola_que_no_son_9_digitos_no_produce_telefono(self, crudo):
        assert limpiar_telefono(crudo) == ""

    @pytest.mark.parametrize("crudo,esperado", [
        ("612345678", "612345678"),
        ("931112233", "931112233"),
        ("+34 93 111 22 33", "931112233"),
    ])
    def test_un_espanol_de_9_digitos_sobrevive(self, crudo, esperado):
        assert limpiar_telefono(crudo) == esperado

    def test_un_extranjero_no_se_somete_a_los_9_digitos(self):
        """`+33 1 23 45 67 89` da 11 digitos tras el `+` (33 de pais + 9 del numero) --
        a proposito distinto de 9, para que este test no pase por casualidad bajo una
        regla (equivocada) de "siempre 9 digitos". Ver tambien
        `TestLimpiarTelefono.test_un_numero_extranjero_no_se_mutila`, que ya fijaba
        este caso antes de este hallazgo."""
        assert limpiar_telefono("+33 1 23 45 67 89") == "+33123456789"

    def test_el_prefijo_de_pais_solo_sin_numero_detras_no_produce_telefono(self):
        assert limpiar_telefono("+34") == ""


class TestLeerLosCamposDeLaPlantillaDeBarcelona:

    @staticmethod
    def _datos():
        bloques, _ = extraer_bloques("Hola.\n\n" + FIRMA_BCN, fichero="a.eml")
        return leer_campos(bloques[0])

    def test_el_movil(self):
        assert self._datos().movil == "612345678"

    def test_el_fijo_va_a_telefono(self):
        assert self._datos().telefono == "931112233"

    def test_el_cargo_es_la_linea_tras_el_nombre_en_negrita(self):
        """No tiene etiqueta: se posiciona. Aqui el cargo NO va en negrita."""
        assert self._datos().cargo == "Asesora Inmobiliaria"

    def test_el_email_y_la_procedencia_viajan(self):
        d = self._datos()
        assert d.email == "ana@engelvoelkers.com"
        assert d.procedencia == PROCEDENCIA_DIRECTO
        assert (d.fichero, d.linea) == ("a.eml", d.linea) and d.linea >= 1


class TestLeerLosCamposDeLaPlantillaDeMadrid:

    @staticmethod
    def _datos():
        bloques, _ = extraer_bloques(FIRMA_MAD, fichero="b.eml")
        return leer_campos(bloques[0])

    def test_el_fijo_con_extension(self):
        assert self._datos().telefono == "912345678"

    def test_el_cargo_SI_va_en_negrita_en_esta_plantilla(self):
        assert self._datos().cargo == "Técnico de PBC."

    def test_NO_HAY_MOVIL_y_eso_no_es_lo_mismo_que_no_tenerlo(self):
        """La frontera del §6 del spec: esta plantilla corporativa simplemente no lo
        incluye. El campo sale vacio; QUIEN lo interprete es la Task 8."""
        assert self._datos().movil == ""

    def test_la_razon_social_no_se_confunde_con_el_cargo(self):
        assert "ENGEL" not in self._datos().cargo

    def test_la_direccion_no_se_confunde_con_el_cargo(self):
        assert "Calle" not in self._datos().cargo


class TestElCargoNoSeInventa:

    def test_sin_linea_en_negrita_no_hay_cargo(self):
        cuerpo = "ENGEL&VÖLKERS\nMóvil: 612 34 56 78\nana@engelvoelkers.com\n"
        bloques, _ = extraer_bloques(cuerpo, fichero="c.eml")
        assert leer_campos(bloques[0]).cargo == ""

    def test_un_telefono_tras_el_nombre_no_es_un_cargo(self):
        cuerpo = ("ENGEL&VÖLKERS\n*Ana Ejemplo*\nMóvil: 612 34 56 78\n"
                  "ana@engelvoelkers.com\n")
        bloques, _ = extraer_bloques(cuerpo, fichero="d.eml")
        d = leer_campos(bloques[0])
        assert d.cargo == ""
        assert d.movil == "612345678", "el telefono sigue leyendose"

    def test_un_email_tras_el_nombre_no_es_un_cargo(self):
        cuerpo = "ENGEL&VÖLKERS\n*Ana Ejemplo*\nana@engelvoelkers.com\nMóvil: 612345678\n"
        bloques, _ = extraer_bloques(cuerpo, fichero="e.eml")
        assert leer_campos(bloques[0]).cargo == ""

    def test_la_razon_social_tras_el_nombre_no_es_un_cargo(self):
        """Hallazgo propio (Step 8): en `FIRMA_MAD` la linea `ENGEL&VÖLKERS` nunca es
        la PRIMERA candidata (media `*Técnico de PBC.*` antes), asi que
        `test_la_razon_social_no_se_confunde_con_el_cargo` pasa aunque se borre el
        guard entero de `_RE_NO_ES_CARGO` -- no ejercita esta rama. Aqui la razon
        social es la linea inmediatamente siguiente al nombre."""
        cuerpo = "ENGEL&VÖLKERS\n*Ana Ejemplo*\nENGEL&VÖLKERS\nana@engelvoelkers.com\n"
        bloques, _ = extraer_bloques(cuerpo, fichero="i.eml")
        assert leer_campos(bloques[0]).cargo == ""

    def test_una_direccion_tras_el_nombre_no_es_un_cargo(self):
        """Mismo hallazgo, para la rama de direccion (`c/|calle|...` y `\\d{4,}`)."""
        cuerpo = ("ENGEL&VÖLKERS\n*Ana Ejemplo*\nCalle Falsa 34, 28001 Madrid\n"
                  "ana@engelvoelkers.com\n")
        bloques, _ = extraer_bloques(cuerpo, fichero="j.eml")
        assert leer_campos(bloques[0]).cargo == ""

    def test_una_URL_tras_el_nombre_no_es_un_cargo(self):
        """Hallazgo D (revision tasks 7-8, Minor): medido que `www.engelvoelkers.com`
        pasaba el filtro y se leia como cargo. Exclusion barata: una linea que
        parece una URL (contiene `www.` o `://`)."""
        cuerpo = ("ENGEL&VÖLKERS\n*Ana Ejemplo*\nwww.engelvoelkers.com\n"
                  "ana@engelvoelkers.com\n")
        bloques, _ = extraer_bloques(cuerpo, fichero="url.eml")
        assert leer_campos(bloques[0]).cargo == ""

    def test_un_horario_tras_el_nombre_no_es_un_cargo(self):
        """Hallazgo D: medido que `Lu-Vi 9:00-18:00` pasaba el filtro. `\\d{4,}`
        (digitos consecutivos) no lo atrapa: ninguna tirada de digitos seguidos
        llega a 4 ("9", "00", "18", "00"). Exclusion barata: una linea
        mayoritariamente digitos y signos (un horario, un codigo)."""
        cuerpo = ("ENGEL&VÖLKERS\n*Ana Ejemplo*\nLu-Vi 9:00-18:00\n"
                  "ana@engelvoelkers.com\n")
        bloques, _ = extraer_bloques(cuerpo, fichero="horario.eml")
        assert leer_campos(bloques[0]).cargo == ""


class TestElMovilNoSeConfundeConElFijo:
    """`Telf:` y `Tel. Fijo:` son fijo; `Móvil:` es movil. Un cruce mete un fijo en el
    campo `movil` del CRM, que es el que la UI muestra."""

    def test_Telf_es_fijo_no_movil(self):
        cuerpo = "ENGEL&VÖLKERS\nTelf: 931112233\nana@engelvoelkers.com\n"
        bloques, _ = extraer_bloques(cuerpo, fichero="f.eml")
        d = leer_campos(bloques[0])
        assert (d.telefono, d.movil) == ("931112233", "")

    def test_Movil_es_movil_no_fijo(self):
        cuerpo = "ENGEL&VÖLKERS\nMóvil: 612345678\nana@engelvoelkers.com\n"
        bloques, _ = extraer_bloques(cuerpo, fichero="g.eml")
        d = leer_campos(bloques[0])
        assert (d.movil, d.telefono) == ("612345678", "")

    def test_Movil_sin_tilde_tambien(self):
        cuerpo = "ENGEL&VÖLKERS\nMovil: 612345678\nana@engelvoelkers.com\n"
        bloques, _ = extraer_bloques(cuerpo, fichero="h.eml")
        assert leer_campos(bloques[0]).movil == "612345678"


class TestLaEtiquetaCompuestaTelefonoMovilEsMovil:
    """Defecto medido (2026-09-04): `Telefono movil:` / `Telefono Movil:` / `Tel.
    movil:` se clasificaban como FIJO. `_RE_FIJO` casa por su alternativa
    `tel[ée]fono`/`tel\\.` y `_RE_MOVIL` no llegaba a probarse porque estaba
    anclada a inicio de linea, y la linea empieza por "Telefono". La propiedad:
    una etiqueta que NOMBRA el movil es un movil, este donde este dentro de la
    etiqueta -- no es "probar movil antes que fijo" (eso ya se hacia y no
    bastaba, porque el ancla de _RE_MOVIL le impedia ver la linea).

    Cada caso comprueba TAMBIEN que el otro campo queda vacio: un cruce que
    rellene los dos es igual de malo que clasificar mal uno solo."""

    @pytest.mark.parametrize("etiqueta", [
        "Móvil:", "Movil:", "Mobile:", "Teléfono móvil:", "Telefono movil:",
        "Tel. móvil:", "Móv.:",
    ])
    def test_la_etiqueta_se_lee_como_movil_y_el_fijo_queda_vacio(self, etiqueta):
        cuerpo = f"ENGEL&VÖLKERS\n{etiqueta} 612 34 56 78\nana@engelvoelkers.com\n"
        bloques, _ = extraer_bloques(cuerpo, fichero="mv.eml")
        d = leer_campos(bloques[0])
        assert d.movil == "612345678", f"{etiqueta!r} deberia leerse como movil"
        assert d.telefono == "", f"{etiqueta!r} no puede rellenar tambien el fijo"

    @pytest.mark.parametrize("etiqueta", [
        "Telf:", "Teléfono:", "Tel.:", "Tel. Fijo:", "Phone:",
    ])
    def test_la_etiqueta_se_lee_como_fijo_y_el_movil_queda_vacio(self, etiqueta):
        cuerpo = f"ENGEL&VÖLKERS\n{etiqueta} 931112233\nana@engelvoelkers.com\n"
        bloques, _ = extraer_bloques(cuerpo, fichero="fj.eml")
        d = leer_campos(bloques[0])
        assert d.telefono == "931112233", f"{etiqueta!r} deberia leerse como fijo"
        assert d.movil == "", f"{etiqueta!r} no puede rellenar tambien el movil"


def _f(email="ana@engelvoelkers.com", movil="", telefono="", cargo="",
       procedencia=PROCEDENCIA_DIRECTO, fichero="x.eml", linea=1):
    return DatosFirma(email=email, movil=movil, telefono=telefono, cargo=cargo,
                      procedencia=procedencia, fichero=fichero, linea=linea)


class TestConsolidarLoBasico:

    def test_sin_firmas_no_hay_nadie(self):
        assert consolidar([]) == {}

    def test_una_firma_da_un_consolidado(self):
        c = consolidar([_f(movil="612345678")])
        assert set(c) == {"ana@engelvoelkers.com"}
        assert isinstance(c["ana@engelvoelkers.com"], Consolidado)

    def test_el_valor_encontrado_lleva_su_veredicto_y_su_fuente(self):
        c = consolidar([_f(movil="612345678", fichero="a.eml", linea=7)])["ana@engelvoelkers.com"]
        assert c.movil == "612345678"
        assert c.veredicto_movil == VEREDICTO_ENCONTRADO
        assert "a.eml:7" in c.fuentes

    def test_dos_personas_se_separan(self):
        c = consolidar([_f(movil="612345678"),
                        _f(email="berta@engelvoelkers.com", telefono="912345678")])
        assert set(c) == {"ana@engelvoelkers.com", "berta@engelvoelkers.com"}

    def test_el_email_se_normaliza_a_minusculas(self):
        c = consolidar([_f(email="Ana@EngelVoelkers.com", movil="612345678")])
        assert set(c) == {"ana@engelvoelkers.com"}


class TestDosBloquesQueDicenLoMISMO:
    """El caso normal: la plantilla de Barcelona repite la direccion, asi que un solo
    .eml da dos bloques con los mismos valores. Eso NO es un conflicto."""

    def test_dos_valores_iguales_no_son_conflicto(self):
        c = consolidar([_f(movil="612345678", linea=1),
                        _f(movil="612345678", linea=9)])["ana@engelvoelkers.com"]
        assert c.movil == "612345678"
        assert c.veredicto_movil == VEREDICTO_ENCONTRADO

    def test_uno_vacio_y_uno_con_valor_se_completan(self):
        c = consolidar([_f(movil="612345678"),
                        _f(telefono="931112233")])["ana@engelvoelkers.com"]
        assert (c.movil, c.telefono) == ("612345678", "931112233")


class TestElDirectoMandaSobreElCitado:
    """Un bloque citado es mas antiguo: si el consultor cambio de movil, el directo
    es el bueno. Esto NO es un conflicto, es una jerarquia."""

    def test_el_directo_gana(self):
        c = consolidar([_f(movil="600000000", procedencia=PROCEDENCIA_CITADO),
                        _f(movil="612345678", procedencia=PROCEDENCIA_DIRECTO)])
        assert c["ana@engelvoelkers.com"].movil == "612345678"

    def test_el_orden_en_que_llegan_no_cambia_el_resultado(self):
        c = consolidar([_f(movil="612345678", procedencia=PROCEDENCIA_DIRECTO),
                        _f(movil="600000000", procedencia=PROCEDENCIA_CITADO)])
        assert c["ana@engelvoelkers.com"].movil == "612345678"

    def test_si_SOLO_hay_citado_se_usa(self):
        """Que sea mas antiguo no lo hace falso: es lo unico que hay."""
        c = consolidar([_f(movil="600000000", procedencia=PROCEDENCIA_CITADO)])
        assert c["ana@engelvoelkers.com"].movil == "600000000"
        assert c["ana@engelvoelkers.com"].veredicto_movil == VEREDICTO_ENCONTRADO


class TestElConflictoFALLA_CERRADO:
    """Misma politica que el dedup del PR #272: ante lo que no puede comprobar, no
    escribe. Un movil mal elegido va a la ficha del cliente."""

    def test_dos_directos_distintos_son_CONFLICTO(self):
        c = consolidar([_f(movil="612345678", fichero="a.eml"),
                        _f(movil="600000000", fichero="b.eml")])["ana@engelvoelkers.com"]
        assert c.veredicto_movil == VEREDICTO_CONFLICTO

    def test_en_conflicto_NO_se_propone_valor(self):
        """Lo que importa: que el campo salga VACIO, no que el veredicto lo diga."""
        c = consolidar([_f(movil="612345678"), _f(movil="600000000")])["ana@engelvoelkers.com"]
        assert c.movil == "", "un valor propuesto en conflicto acaba en el CRM"

    def test_el_conflicto_de_un_campo_no_contamina_al_otro(self):
        c = consolidar([_f(movil="612345678", telefono="931112233"),
                        _f(movil="600000000", telefono="931112233")])["ana@engelvoelkers.com"]
        assert c.veredicto_movil == VEREDICTO_CONFLICTO
        assert c.veredicto_telefono == VEREDICTO_ENCONTRADO
        assert c.telefono == "931112233"

    def test_dos_citados_distintos_tambien_son_CONFLICTO(self):
        c = consolidar([_f(movil="612345678", procedencia=PROCEDENCIA_CITADO),
                        _f(movil="600000000", procedencia=PROCEDENCIA_CITADO)])
        assert c["ana@engelvoelkers.com"].veredicto_movil == VEREDICTO_CONFLICTO

    def test_el_conflicto_lista_TODAS_las_fuentes(self):
        """Para que Nikolai pueda ir a mirar los dos y decidir."""
        c = consolidar([_f(movil="612345678", fichero="a.eml", linea=3),
                        _f(movil="600000000", fichero="b.eml", linea=5)])["ana@engelvoelkers.com"]
        assert "a.eml:3" in c.fuentes and "b.eml:5" in c.fuentes


class TestElConflictoDeCargoEsPorContenidoNoPorFormato:
    """Hallazgo B (revision tasks 7-8, Important): el movil y el fijo llegan ya
    normalizados por `limpiar_telefono` antes de entrar en `_elegir`, pero el cargo no
    pasa por ninguna normalizacion -- asi que una diferencia TRIVIAL de formato entre
    dos informes del MISMO dato real se blanqueaba como si discreparan. Medido:
    `consolidar([firma(cargo="Asesora Inmobiliaria"), firma(cargo="asesora
    inmobiliaria")])` daba `cargo='', veredicto=CONFLICTO`.

    La propiedad: dos valores son "el mismo" si lo son UNA VEZ NORMALIZADOS PARA
    COMPARAR (sin distinguir mayusculas, con los espacios colapsados) -- y el valor
    que se PROPONE sigue siendo el ORIGINAL, nunca el normalizado: lo lee una persona
    en el informe, y "Asesora Inmobiliaria" se lee mejor que "asesora inmobiliaria"."""

    def test_una_diferencia_de_mayusculas_no_es_conflicto(self):
        c = consolidar([_f(cargo="Asesora Inmobiliaria"),
                        _f(cargo="asesora inmobiliaria")])["ana@engelvoelkers.com"]
        assert c.veredicto_cargo == VEREDICTO_ENCONTRADO
        assert c.cargo in ("Asesora Inmobiliaria", "asesora inmobiliaria"), (
            "el valor propuesto tiene que ser uno de los ORIGINALES, no vacio ni "
            "una tercera forma normalizada")

    def test_espacios_duplicados_tampoco_es_conflicto(self):
        c = consolidar([_f(cargo="Asesora  Inmobiliaria"),
                        _f(cargo="Asesora Inmobiliaria")])["ana@engelvoelkers.com"]
        assert c.veredicto_cargo == VEREDICTO_ENCONTRADO
        assert c.cargo != ""

    def test_dos_cargos_de_verdad_distintos_siguen_dando_CONFLICTO(self):
        """Sin este test, la normalizacion de la comparacion podria estar tragandose
        conflictos reales y nadie lo sabria."""
        c = consolidar([_f(cargo="Asesora Inmobiliaria"),
                        _f(cargo="Técnico de PBC")])["ana@engelvoelkers.com"]
        assert c.veredicto_cargo == VEREDICTO_CONFLICTO
        assert c.cargo == ""

    def test_dos_cargos_con_la_MISMA_primera_palabra_tambien_son_CONFLICTO(self):
        """La forma FUERTE del test anterior: si la normalizacion fuera tan agresiva
        que comparase solo la primera palabra (u otro resumen que descarte el resto),
        estos dos colapsarian -- los dos EMPIEZAN por "Asesora" y solo difieren en lo
        que viene despues. Sin este test, una normalizacion asi de agresiva pasaria
        el test anterior (primeras palabras ya distintas: "Asesora" / "Técnico") sin
        que nadie lo notase."""
        c = consolidar([_f(cargo="Asesora Inmobiliaria"),
                        _f(cargo="Asesora Comercial")])["ana@engelvoelkers.com"]
        assert c.veredicto_cargo == VEREDICTO_CONFLICTO
        assert c.cargo == ""


class TestFirmaSinCampoNoEsNoTiene:
    """La frontera del §6 del spec, y el aviso #3 del encargo."""

    def test_hay_firma_y_no_hay_movil_es_FIRMA_SIN_CAMPO(self):
        c = consolidar([_f(telefono="912345678")])["ana@engelvoelkers.com"]
        assert c.movil == ""
        assert c.veredicto_movil == VEREDICTO_FIRMA_SIN_CAMPO

    def test_FIRMA_SIN_CAMPO_no_es_el_mismo_veredicto_que_ENCONTRADO_vacio(self):
        """Si los dos colapsan en «sin dato», el informe afirma una ausencia que nadie
        comprobo. Son constantes distintas a proposito."""
        assert VEREDICTO_FIRMA_SIN_CAMPO != VEREDICTO_ENCONTRADO
        assert VEREDICTO_FIRMA_SIN_CAMPO != VEREDICTO_CONFLICTO

    def test_el_cargo_ausente_tambien_se_declara(self):
        c = consolidar([_f(movil="612345678")])["ana@engelvoelkers.com"]
        assert c.veredicto_cargo == VEREDICTO_FIRMA_SIN_CAMPO
