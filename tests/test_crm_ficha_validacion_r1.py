"""Las fronteras que R1 encontro abiertas en el validador y en los campos del contrario.

Doce hallazgos, doce confirmados. Casi todos son la misma familia: **el validador daba
por acreditado algo que no lo estaba**, o al reves, **hacia desaparecer del recuento** un
dato que deberia haber salido. Las dos formas producen un informe que se lee como «0
problemas» siendo falso, que es justo lo que esta pieza existe para impedir.

Los dobles de aqui reproducen lo que los primeros tests NO reproducian (R1/H-01, H-10):
el **frontmatter real** de un espejo de la sala de maquina, `_caso.md` como fichero de
control, y valores con caracteres que rompen los limites.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.crm_ficha_validacion import (
    ENCONTRADO,
    NO_BUSCABLE,
    NO_ENCONTRADO,
    SIN_COMPROBAR,
    Dato,
    corpus_legible,
    cuerpo_del_espejo,
    datos_de_ficha,
    es_fichero_de_control,
    validar,
)


def _d(campo, valor, clase="texto"):
    return Dato(campo=campo, valor=valor, clase=clase)


def _espejo(source_path: str, cuerpo: str) -> str:
    """Un espejo con la forma REAL que produce la sala de maquina: frontmatter + cuerpo."""
    return (
        "---\n"
        "case_id: BaRS11 - Falsa 1 (W-000AAA) - Vuelta\n"
        "tipo: documento_procesado\n"
        f"source_path: {source_path}\n"
        "extractor: pypdf\n"
        "---\n\n"
        + cuerpo
    )


# ===========================================================================
# H-01: el frontmatter NO es documental — acreditaba por el nombre del fichero
# ===========================================================================

class TestElNombreDelFicheroNoEsPrueba:

    def test_un_dato_que_solo_esta_en_el_frontmatter_NO_se_encuentra(self):
        """El caso real: ficheros llamados `DNI ALBERTO FRONTAL.pdf`.

        El OCR de un DNI escaneado suele venir vacio, pero su `source_path` lleva el
        nombre —y a veces el documento— en el propio nombre del PDF. Buscar sobre el
        texto completo probaba como se llama el fichero, no lo que dice.
        """
        corpus = {"dni.md": _espejo(
            "01_Drive EV/DNI ANA LOPEZ 12345678Z.pdf",
            "(el OCR no devolvio texto util)")}

        [nif] = validar([_d("contrario.nif", "12345678Z", "documento")], corpus,
                        ilegibles=("otro.pdf",))
        [nombre] = validar([_d("contrario.nombre", "ANA LOPEZ")], corpus,
                           ilegibles=("otro.pdf",))

        assert nif.veredicto == SIN_COMPROBAR
        assert nombre.veredicto == SIN_COMPROBAR

    def test_el_mismo_dato_en_el_CUERPO_si_se_encuentra(self):
        corpus = {"arras.md": _espejo("01_Drive EV/arras.pdf",
                                      "Interviene ANA LOPEZ, con NIF 12345678Z.")}
        [h] = validar([_d("contrario.nif", "12345678Z", "documento")], corpus, ilegibles=())
        assert h.veredicto == ENCONTRADO

    @pytest.mark.parametrize("texto, esperado", [
        ("---\na: 1\n---\n\ncuerpo", "cuerpo"),
        ("sin frontmatter", "sin frontmatter"),
        ("---\na: 1\nsin cierre", "---\na: 1\nsin cierre"),
        ("", ""),
    ])
    def test_el_recorte_del_frontmatter_no_se_come_el_cuerpo(self, texto, esperado):
        assert cuerpo_del_espejo(texto).strip() == esperado.strip()


# ===========================================================================
# H-02 y H-06: el corpus se clasifica por NATURALEZA, no por extension
# ===========================================================================

class TestQueEsDocumentalYQueEsControl:

    def test_caso_md_es_control_aunque_sea_md(self):
        """`_caso.md` lleva contraparte y ciudad: acreditaria la ficha consigo misma."""
        assert es_fichero_de_control("_caso.md")
        legibles, ilegibles = corpus_legible(
            [{"slug": "caso", "rel_path": "_caso.md", "estado": "ok"}])
        assert not legibles and not ilegibles

    def test_un_json_documental_SI_es_corpus(self):
        """Excluir por extension dejaba fuera prueba de verdad."""
        assert not es_fichero_de_control("01_Drive EV/evidencia.json")
        legibles, _ = corpus_legible(
            [{"slug": "ev", "rel_path": "01_Drive EV/evidencia.json", "estado": "ok"}])
        assert legibles == ("ev",)

    def test_un_json_documental_ILEGIBLE_cuenta_como_no_mirado(self):
        _, ilegibles = corpus_legible(
            [{"slug": "ev", "rel_path": "01_Drive EV/evidencia.json", "estado": "empty"}])
        assert ilegibles == ("01_Drive EV/evidencia.json",)

    @pytest.mark.parametrize("estado", ["", "raro", "pendiente", "error"])
    def test_un_estado_DESCONOCIDO_es_ilegible_no_invisible(self, estado):
        """Caer fuera de las dos listas es como se convierte un «no lo se» en «no hay»."""
        legibles, ilegibles = corpus_legible(
            [{"slug": "x", "rel_path": "01_Drive EV/x.pdf", "estado": estado}])
        assert not legibles and ilegibles == ("01_Drive EV/x.pdf",)

    def test_una_fila_que_no_se_entiende_tambien_cuenta(self):
        legibles, ilegibles = corpus_legible(["no soy un dict"])
        assert not legibles and len(ilegibles) == 1

    def test_el_control_se_reconoce_sin_distinguir_caja(self):
        assert es_fichero_de_control("_CASO.MD")

    @pytest.mark.parametrize("rel", ["sub/_caso.md", "sub\\_ficha_crm.yaml",
                                     "2026-09-05_email_01/adjuntos/_ficha_crm.yaml",
                                     # R2/H-04: los cinco nombres «de fuera de 00_Input» que el
                                     # diff conservaba por basename escondian adjuntos homonimos
                                     "2026-09-05_email_01/adjuntos/_cobertura.json",
                                     "2026-09-05_email_01/adjuntos/_cobertura.md",
                                     "2026-09-05_email_01/adjuntos/_sala_maquina_state.json",
                                     "2026-09-05_email_01/adjuntos/_registro.json",
                                     "2026-09-05_email_01/adjuntos/_tiempos.jsonl"])
    def test_t13_el_homonimo_fuera_de_su_sitio_es_documental_y_si_esta_ilegible_cuenta(self, rel):
        """MEJORAS #149 (rev. 2 §3.3, H-08): un adjunto llamado como un fichero de protocolo
        NO es de control; si esta ilegible cuenta como ilegible. Antes se saltaba, y un
        `SIN_COMPROBAR` pasaba a `NO_ENCONTRADO` porque el documento no mirado desaparecia
        del recuento."""
        assert not es_fichero_de_control(rel)
        legibles, ilegibles = corpus_legible(
            [{"slug": "adj", "rel_path": rel, "estado": "low"}])
        assert not legibles and ilegibles == (rel,)


# ===========================================================================
# H-03 y H-04: los patrones exigen limites por los DOS lados
# ===========================================================================

class TestLosLimitesDelPatron:

    @pytest.mark.parametrize("valor, texto", [
        ("12345678Z", "documento X12345678Z del otro"),   # limite izquierdo
        ("12345678Z", "el 12345678ZA de alguien"),        # limite derecho
    ])
    def test_un_documento_no_casa_DENTRO_de_otro(self, valor, texto):
        [h] = validar([_d("contrario.nif", valor, "documento")], {"d.md": texto},
                      ilegibles=())
        assert h.veredicto == NO_ENCONTRADO

    @pytest.mark.parametrize("corto", ["Z", "12", "ABC"])
    def test_un_documento_demasiado_corto_NO_SE_BUSCA(self, corto):
        """`Z` acreditaba contra `LOPEZ`. No es que no case: es que no identifica."""
        [h] = validar([_d("contrario.nif", corto, "documento")],
                      {"d.md": "LOPEZ 12 ABCDEF"}, ilegibles=())
        assert h.veredicto == NO_BUSCABLE

    def test_un_nombre_no_casa_dentro_de_otro_nombre(self):
        [h] = validar([_d("contrario.nombre", "ANA LOPEZ")],
                      {"d.md": "MARIANA LOPEZA, mayor de edad"}, ilegibles=())
        assert h.veredicto == NO_ENCONTRADO

    def test_un_email_no_casa_dentro_de_otro(self):
        [h] = validar([_d("c.email", "ana+caso@example.com", "email")],
                      {"d.md": "De: xana+caso@example.com.es"}, ilegibles=())
        assert h.veredicto == NO_ENCONTRADO

    def test_el_email_exacto_si(self):
        [h] = validar([_d("c.email", "ana+caso@example.com", "email")],
                      {"d.md": "De: ana+caso@example.com (Ana)"}, ilegibles=())
        assert h.veredicto == ENCONTRADO

    @pytest.mark.parametrize("en_documento", [
        "+34600111222", "+34 600 111 222", "600111222", "600-111-222"])
    def test_el_telefono_se_encuentra_con_el_prefijo_PEGADO(self, en_documento):
        [h] = validar([_d("c.movil", "600111222", "telefono")],
                      {"d.md": f"Tel {en_documento}"}, ilegibles=())
        assert h.veredicto == ENCONTRADO

    def test_un_telefono_extranjero_no_casa_con_uno_espanol_distinto(self):
        """Truncar a los 9 ultimos hacia casar `+442079460958` con otro numero."""
        [h] = validar([_d("c.movil", "+442079460958", "telefono")],
                      {"d.md": "Tel +34 079 460 958"}, ilegibles=())
        assert h.veredicto == NO_ENCONTRADO

    def test_un_telefono_corto_no_se_busca(self):
        [h] = validar([_d("c.movil", "12345678", "telefono")],
                      {"d.md": "el numero 12345678 esta aqui"}, ilegibles=())
        assert h.veredicto == NO_BUSCABLE


# ===========================================================================
# H-11: un dato mal formado no es un problema del corpus
# ===========================================================================

def test_no_buscable_no_arrastra_la_lista_de_ilegibles():
    """Decia «no se pudo mirar en estos documentos» y no listaba ninguno."""
    [h] = validar([_d("c.movil", "123", "telefono")], {"d.md": "texto"},
                  ilegibles=("DNI.pdf",))
    assert h.veredicto == NO_BUSCABLE
    assert h.ilegibles == (), "un dato mal formado no tiene que ver con el OCR"


# ===========================================================================
# H-05: TODOS los campos de la ficha entran en el denominador
# ===========================================================================

class TestNingunCampoDesaparece:

    @staticmethod
    def _ficha(tmp_path):
        from core.crm_ficha import cargar_ficha_yaml
        y = tmp_path / "_ficha_crm.yaml"
        y.write_text(
            "contrario:\n  nombre: ANA LOPEZ\n  apellido1: LOPEZ\n  apellido2: RUIZ\n"
            "  nif: 12345678Z\n  email: a@b.example\n  movil: '600111222'\n"
            "  telefono: '931112233'\n  direccion: CALLE FALSA 1\n"
            "  poblacion: BARCELONA\n  cp: '08019'\n  provincia: Barcelona\n",
            encoding="utf-8")
        return cargar_ficha_yaml(y)

    def test_los_once_campos_del_contrario_se_validan(self, tmp_path):
        campos = {d.campo for d in datos_de_ficha(self._ficha(tmp_path))}
        for c in ("nombre", "apellido1", "apellido2", "nif", "email", "movil",
                  "telefono", "direccion", "poblacion", "cp", "provincia"):
            assert f"contrario.{c}" in campos, f"contrario.{c} desaparecio del recuento"

    def test_los_de_una_palabra_se_validan_pero_no_acreditan(self, tmp_path):
        por_campo = {d.campo: d for d in datos_de_ficha(self._ficha(tmp_path))}
        assert not por_campo["contrario.apellido1"].discriminante
        assert not por_campo["contrario.poblacion"].discriminante
        assert por_campo["contrario.nombre"].discriminante
        assert por_campo["contrario.nif"].discriminante


# ===========================================================================
# H-08 y H-09: el YAML no corrompe ni inventa
# ===========================================================================

class TestElYAMLNoPuedeCorromperUnDato:

    @staticmethod
    def _carga(tmp_path, linea):
        from core.crm_ficha import cargar_ficha_yaml
        y = tmp_path / "_ficha_crm.yaml"
        y.write_text(f"contrario:\n  nombre: ANA\n  {linea}\n", encoding="utf-8")
        return cargar_ficha_yaml(y)

    def test_un_cp_sin_comillas_se_RECHAZA_en_vez_de_corromperse(self, tmp_path):
        """`cp: 01001` lo lee YAML como el octal 513, y el dato ya no se recupera."""
        with pytest.raises(ValueError, match="comillas"):
            self._carga(tmp_path, "cp: 01001")

    def test_el_cp_entre_comillas_sobrevive(self, tmp_path):
        assert self._carga(tmp_path, "cp: '01001'").contrario.cp == "01001"

    @pytest.mark.parametrize("linea", ["cp:", "telefono:", "provincia:"])
    def test_una_clave_vacia_es_AUSENCIA_no_la_cadena_None(self, tmp_path, linea):
        c = self._carga(tmp_path, linea).contrario
        assert c.cp == "" and c.telefono == "" and c.provincia == ""


# ===========================================================================
# H-07: los campos llegan al contrario que YA EXISTE
# ===========================================================================

class TestElContrarioExistenteSeCOMPLETA:
    """Anadirlos al DTO solo los hacia llegar al CREAR. El caso normal es que exista."""

    @staticmethod
    def _datos():
        from core.sudespacho_relations import NuevoClienteContrario
        return NuevoClienteContrario(nombre="ANA", nif="12345678Z", cp="08019",
                                     provincia="BARCELONA", telefono="931112233")

    def test_lo_que_falta_en_el_CRM_se_rellena(self):
        from core.sudespacho_relations import (ResolucionParte,
                                               ensure_contrario_vinculado)
        actualizar = MagicMock()
        with patch("core.sudespacho_relations.resolver_parte",
                   return_value=ResolucionParte(id="1108", por="nif")), \
             patch("core.sudespacho_relations.get_cliente_contrario",
                   return_value={"nombre": "ANA", "cp": "", "provincia": "",
                                 "telefono1": ""}), \
             patch("core.sudespacho_relations.update_cliente_contrario", actualizar), \
             patch("core.sudespacho_relations.link_contrario", MagicMock()):
            cid, creado = ensure_contrario_vinculado("634", self._datos())

        assert (cid, creado) == ("1108", False)
        cambios = actualizar.call_args.args[1]
        assert cambios["cp"] == "08019"
        assert cambios["telefono1"] == "931112233"
        assert cambios["provincia"] == "Barcelona", "debe ir el literal del enum"

    def test_lo_que_el_CRM_YA_tiene_no_se_pisa(self):
        """La ficha local aporta datos; no manda sobre lo que otro corrigio alli."""
        from core.sudespacho_relations import (ResolucionParte,
                                               ensure_contrario_vinculado)
        actualizar = MagicMock()
        with patch("core.sudespacho_relations.resolver_parte",
                   return_value=ResolucionParte(id="1108", por="nif")), \
             patch("core.sudespacho_relations.get_cliente_contrario",
                   return_value={"cp": "08028", "provincia": "Barcelona",
                                 "telefono1": "930000000"}), \
             patch("core.sudespacho_relations.update_cliente_contrario", actualizar), \
             patch("core.sudespacho_relations.link_contrario", MagicMock()):
            ensure_contrario_vinculado("634", self._datos())

        actualizar.assert_not_called()

    def test_si_no_se_puede_LEER_la_ficha_no_se_pierde_el_VINCULO(self):
        """Completar es un extra: perder el vinculo por un CP seria peor."""
        from core.sudespacho_relations import (ResolucionParte,
                                               ensure_contrario_vinculado)
        vincular = MagicMock()
        with patch("core.sudespacho_relations.resolver_parte",
                   return_value=ResolucionParte(id="1108", por="nif")), \
             patch("core.sudespacho_relations.get_cliente_contrario",
                   side_effect=RuntimeError("500")), \
             patch("core.sudespacho_relations.link_contrario", vincular):
            cid, creado = ensure_contrario_vinculado("634", self._datos())

        assert (cid, creado) == ("1108", False)
        vincular.assert_called_once()
