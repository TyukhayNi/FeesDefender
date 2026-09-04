"""El `_ficha_crm.yaml` se teclea a mano: esto comprueba que sus datos ESTAN en la documental.

Encargo de Nikolai (2026-09-04), punto 3. **Validar, no generar**: el problema no es
teclear, es teclear mal sin que nadie lo note. Un NIF con un digito cambiado lo acepta el
CRM tal cual, y a partir de ahi la deduplicacion por NIF —construida en el PR #272— falla
por la razon mas tonta: el dato de partida es falso.

**La frontera que gobierna el modulo, y no es teorica.** Medido sobre W-02Q38C: de los 58
documentos de la sala de maquina, los **cinco** con OCR vacio o pobre son *los DNI* — o
sea, justo donde vive el NIF. Un validador que diga «NIF no encontrado» ahi estaria
mintiendo: la verdad es «no pude mirar donde estaria». Tres veredictos, no dos:

- `ENCONTRADO`   — aparece en un documento legible, y se dice en cual.
- `NO_ENCONTRADO`— no aparece, y **todo** el corpus era legible.
- `SIN_COMPROBAR`— no aparece, pero hay documentos que no se pudieron leer.

Es la misma distincion que la ronda R1 del PR #272 cobro cinco veces: colapsar «no lo se»
en «no hay» produce un informe que dice «0 problemas» siendo falso.
"""

from __future__ import annotations

import pytest

from core.crm_ficha_validacion import (
    ENCONTRADO,
    NO_ENCONTRADO,
    SIN_COMPROBAR,
    Dato,
    corpus_legible,
    datos_de_ficha,
    validar,
)


def _d(campo, valor, clase="texto"):
    return Dato(campo=campo, valor=valor, clase=clase)


# ---------------------------------------------------------------------------
# Los tres veredictos
# ---------------------------------------------------------------------------

class TestLosTresVeredictos:

    def test_encontrado_dice_en_que_documento(self):
        corpus = {"encargo.md": "Firmado por ANA LOPEZ con NIF 12345678Z.",
                  "otro.md": "nada relevante"}
        [h] = validar([_d("contrario.nif", "12345678Z", "documento")], corpus, ilegibles=())

        assert h.veredicto == ENCONTRADO
        assert h.documentos == ("encargo.md",)

    def test_no_encontrado_solo_si_TODO_era_legible(self):
        corpus = {"encargo.md": "Firmado por ANA LOPEZ."}
        [h] = validar([_d("contrario.nif", "12345678Z", "documento")], corpus, ilegibles=())

        assert h.veredicto == NO_ENCONTRADO

    def test_con_ilegibles_es_SIN_COMPROBAR_no_NO_ENCONTRADO(self):
        """El caso real: el NIF vive en un DNI escaneado que el OCR no pudo leer."""
        corpus = {"encargo.md": "Firmado por ANA LOPEZ."}
        [h] = validar([_d("contrario.nif", "12345678Z", "documento")],
                      corpus, ilegibles=("DNI FRONTAL.pdf", "DNI POSTERIOR.pdf"))

        assert h.veredicto == SIN_COMPROBAR
        assert "DNI FRONTAL.pdf" in h.ilegibles

    def test_un_dato_QUE_SI_aparece_no_se_degrada_por_haber_ilegibles(self):
        """Los ilegibles solo afectan a lo que no se encontro."""
        corpus = {"encargo.md": "NIF 12345678Z"}
        [h] = validar([_d("contrario.nif", "12345678Z", "documento")],
                      corpus, ilegibles=("DNI.pdf",))
        assert h.veredicto == ENCONTRADO


# ---------------------------------------------------------------------------
# Normalizacion: el documento y el YAML no escriben igual
# ---------------------------------------------------------------------------

class TestElDocumentoNoEscribeComoElYAML:

    @pytest.mark.parametrize("en_el_documento", [
        "12345678Z", "12345678z", "12.345.678-Z", "12 345 678 Z", "NIF: 12.345.678Z",
    ])
    def test_el_nif_se_encuentra_con_separadores_y_caja(self, en_el_documento):
        [h] = validar([_d("contrario.nif", "12345678Z", "documento")],
                      {"doc.md": f"Interviene {en_el_documento} en el acto"}, ilegibles=())
        assert h.veredicto == ENCONTRADO

    def test_un_nif_DISTINTO_no_cuela_por_la_normalizacion(self):
        """La tolerancia no puede llegar a dar por bueno otro documento."""
        [h] = validar([_d("contrario.nif", "12345678Z", "documento")],
                      {"doc.md": "NIF 12345679Z"}, ilegibles=())
        assert h.veredicto == NO_ENCONTRADO

    @pytest.mark.parametrize("en_el_documento", [
        "ana.lopez@ev.com", "ANA.LOPEZ@EV.COM", "Ana.Lopez@Ev.Com"])
    def test_el_email_ignora_la_caja(self, en_el_documento):
        [h] = validar([_d("colaborador.email", "ana.lopez@ev.com", "email")],
                      {"correo.md": f"De: {en_el_documento}"}, ilegibles=())
        assert h.veredicto == ENCONTRADO

    @pytest.mark.parametrize("en_el_documento", [
        "600111222", "+34 600 111 222", "600 11 12 22", "Tel. 600-111-222"])
    def test_el_telefono_se_encuentra_con_cualquier_formato(self, en_el_documento):
        [h] = validar([_d("contrario.movil", "600111222", "telefono")],
                      {"doc.md": f"Contacto: {en_el_documento}"}, ilegibles=())
        assert h.veredicto == ENCONTRADO

    @pytest.mark.parametrize("en_el_documento", [
        "MARIA GARCIA", "María García", "maria garcia", "María  García"])
    def test_el_nombre_ignora_tildes_caja_y_espacios_de_mas(self, en_el_documento):
        [h] = validar([_d("contrario.nombre", "MARIA GARCIA", "texto")],
                      {"doc.md": f"Dona {en_el_documento}, mayor de edad"}, ilegibles=())
        assert h.veredicto == ENCONTRADO


# ---------------------------------------------------------------------------
# El corpus: que se mira y, sobre todo, que NO
# ---------------------------------------------------------------------------

class TestElCorpusNoPuedeIncluirseASiMismo:
    """Si el corpus incluye el `_ficha_crm.yaml`, el validador se valida a si mismo.

    Y no es hipotetico: `_ficha_crm.yaml` figura en la cobertura de W-02Q38C como
    `sin_soporte`, o sea que esta en el inventario de la sala de maquina. Un corpus
    construido sin cuidado lo mete, todos los datos salen ENCONTRADOS, y el informe
    dice «0 problemas» habiendose leido a si mismo.
    """

    def test_el_propio_yaml_queda_fuera(self):
        entradas = [
            {"slug": "encargo", "rel_path": "01_Drive EV/encargo.pdf", "estado": "ok"},
            {"slug": "ficha", "rel_path": "_ficha_crm.yaml", "estado": "sin_soporte"},
        ]
        legibles, ilegibles = corpus_legible(entradas)
        assert "encargo" in legibles
        assert "ficha" not in legibles
        assert not any("ficha" in i for i in ilegibles), (
            "el YAML no es un documento ilegible: es un fichero de control")

    @pytest.mark.parametrize("rel_path", [
        "_ficha_crm.yaml", "_exported_ids.json", "_intake_hashes.json",
        "2026-08-14_email_01/_manifiesto.yaml", "_ocurrencias_crm.json",
    ])
    def test_los_ficheros_de_CONTROL_no_son_corpus_ni_cuentan_como_ilegibles(self, rel_path):
        legibles, ilegibles = corpus_legible(
            [{"slug": "x", "rel_path": rel_path, "estado": "sin_soporte"}])
        assert not legibles and not ilegibles

    def test_un_documento_REAL_sin_soporte_SI_es_ilegible(self):
        """Un `.doc` que no se pudo convertir es «no pude mirar», no «no relevante»."""
        legibles, ilegibles = corpus_legible(
            [{"slug": "demanda", "rel_path": "01_Drive EV/demanda.doc",
              "estado": "sin_soporte"}])
        assert not legibles and ilegibles == ("01_Drive EV/demanda.doc",)

    @pytest.mark.parametrize("estado", ["low", "empty"])
    def test_low_y_empty_son_ilegibles(self, estado):
        legibles, ilegibles = corpus_legible(
            [{"slug": "dni", "rel_path": "01_Drive EV/DNI.pdf", "estado": estado}])
        assert not legibles and ilegibles == ("01_Drive EV/DNI.pdf",)


# ---------------------------------------------------------------------------
# Que datos se extraen de la ficha
# ---------------------------------------------------------------------------

class TestQueDatosSeValidan:

    @staticmethod
    def _ficha():
        from core.crm_ficha import cargar_ficha_yaml
        return cargar_ficha_yaml

    def test_extrae_los_campos_del_contrario_y_los_colaboradores(self, tmp_path):
        from core.crm_ficha import cargar_ficha_yaml

        y = tmp_path / "_ficha_crm.yaml"
        y.write_text(
            "contrario:\n  nombre: ANA LOPEZ\n  apellido1: LOPEZ\n  nif: 12345678Z\n"
            "  email: ana@ev.example\n  movil: '+34 600 111 222'\n"
            "colaboradores:\n  - nombre: BEA RUIZ\n    email: bea@ev.example\n"
            "notas_html: '<p>x</p>'\n", encoding="utf-8")

        datos = datos_de_ficha(cargar_ficha_yaml(y))
        campos = {d.campo for d in datos}

        assert "contrario.nif" in campos
        assert "contrario.nombre" in campos
        assert "contrario.email" in campos
        assert "colaboradores[0].nombre" in campos
        # `notas_html` es narrativo del despacho, no un dato que deba estar en la
        # documental: validarlo daria un NO_ENCONTRADO permanente y ruidoso.
        assert not any(c.startswith("notas") for c in campos)

    def test_las_clases_dirigen_la_normalizacion(self, tmp_path):
        from core.crm_ficha import cargar_ficha_yaml

        y = tmp_path / "_ficha_crm.yaml"
        y.write_text(
            "contrario:\n  nombre: ANA\n  nif: 12345678Z\n  email: a@b.example\n"
            "  movil: '600111222'\n", encoding="utf-8")
        por_campo = {d.campo: d.clase for d in datos_de_ficha(cargar_ficha_yaml(y))}

        assert por_campo["contrario.nif"] == "documento"
        assert por_campo["contrario.email"] == "email"
        assert por_campo["contrario.movil"] == "telefono"
        assert por_campo["contrario.nombre"] == "texto"

    def test_los_campos_vacios_no_se_validan(self, tmp_path):
        """Un campo que la ficha no trae no es un dato ausente de la documental."""
        from core.crm_ficha import cargar_ficha_yaml

        y = tmp_path / "_ficha_crm.yaml"
        y.write_text("contrario:\n  nombre: ANA\n  nif: ''\n", encoding="utf-8")
        campos = {d.campo for d in datos_de_ficha(cargar_ficha_yaml(y))}
        assert "contrario.nif" not in campos


class TestLaPuntuacionNoPuedeEsconderUnDato:
    """Un `SIN_COMPROBAR` falso entrena a ignorar el informe entero.

    Caso REAL, medido sobre W-02Q38C: la ficha dice `PASSEIG GARCÍA FARIA 81, ÁTICO` y
    el correo dice `Passeig García Faria 81 , ático`, con espacio antes de la coma. La
    primera version partia por espacios, dejaba el token `81,` y no casaba: el validador
    daba SIN_COMPROBAR sobre un dato que estaba a la vista en dos documentos.
    """

    @pytest.mark.parametrize("en_el_documento", [
        "Passeig García Faria 81 , ático",       # el texto real del expediente
        "PASSEIG GARCIA FARIA 81, ATICO",
        "Passeig Garcia Faria 81 - atico",
        "Passeig  García   Faria  81,ático",
    ])
    def test_la_direccion_se_encuentra_pese_a_la_puntuacion(self, en_el_documento):
        [h] = validar([_d("contrario.direccion", "PASSEIG GARCÍA FARIA 81, ÁTICO")],
                      {"correo.md": f"Domicilio: {en_el_documento} (Barcelona)"},
                      ilegibles=("DNI.pdf",))
        assert h.veredicto == ENCONTRADO, "un SIN_COMPROBAR falso sobre un dato visible"

    def test_la_tolerancia_no_llega_a_cambiar_el_NUMERO(self):
        """Flexible con los separadores, no con el contenido."""
        [h] = validar([_d("contrario.direccion", "PASSEIG GARCÍA FARIA 81, ÁTICO")],
                      {"correo.md": "Passeig García Faria 82 , ático"}, ilegibles=())
        assert h.veredicto == NO_ENCONTRADO

    def test_tampoco_casa_si_falta_una_palabra(self):
        [h] = validar([_d("contrario.direccion", "PASSEIG GARCÍA FARIA 81, ÁTICO")],
                      {"correo.md": "Passeig Faria 81, ático"}, ilegibles=())
        assert h.veredicto == NO_ENCONTRADO


class TestUnDatoDeUnaPalabraNoAcredita:
    """Encontrar `MARTINEZ` no prueba nada: puede ser el apellido de otra parte.

    Medido sobre W-02Q38C: `MARTINEZ` sale en diez lineas del expediente **y es el
    apellido del comprador**, no el del contrario; `BARCELONA` como poblacion aparece en
    34 documentos. Contar esos aciertos como verificacion infla el informe con
    coincidencias que no acreditan nada.
    """

    def test_un_apellido_suelto_encuentra_pero_no_acredita(self):
        [h] = validar([_d("contrario.apellido1", "MARTINEZ")],
                      {"reserva.md": "D. DAVID MARTINEZ SALAS, mayor de edad"}, ilegibles=())
        assert h.veredicto == ENCONTRADO
        assert h.acredita is False

    def test_una_poblacion_tampoco(self):
        [h] = validar([_d("contrario.poblacion", "BARCELONA")],
                      {"arras.md": "en BARCELONA a 7 de mayo"}, ilegibles=())
        assert h.ok and not h.acredita

    def test_un_nombre_COMPLETO_si_acredita(self):
        [h] = validar([_d("contrario.nombre", "ALBERTO CAMPRUBI CORDAL")],
                      {"arras.md": "D. ALBERTO CAMPRUBI CORDAL, mayor de edad"},
                      ilegibles=())
        assert h.acredita is True

    @pytest.mark.parametrize("clase", ["documento", "email", "telefono"])
    def test_un_identificador_acredita_aunque_sea_una_sola_palabra(self, clase):
        """Un NIF es una palabra y sí identifica: la regla es de entropía, no de forma."""
        valores = {"documento": "12345678Z", "email": "a@b.example",
                   "telefono": "600111222"}
        [h] = validar([_d("contrario.x", valores[clase], clase)],
                      {"doc.md": f"dato {valores[clase]} aqui"}, ilegibles=())
        assert h.acredita is True

    def test_los_apellidos_sueltos_ya_no_se_validan(self, tmp_path):
        from core.crm_ficha import cargar_ficha_yaml

        y = tmp_path / "_ficha_crm.yaml"
        y.write_text("contrario:\n  nombre: ALBERTO CAMPRUBI CORDAL\n"
                     "  apellido1: CAMPRUBI\n  apellido2: CORDAL\n", encoding="utf-8")
        campos = {d.campo for d in datos_de_ficha(cargar_ficha_yaml(y))}

        assert "contrario.nombre" in campos
        assert "contrario.apellido1" not in campos
        assert "contrario.apellido2" not in campos
