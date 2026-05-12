"""Tests de la categoría 'Otros casos' + clientes propios E&V.

Cubre:

- TIPOS_CASO_OTROS bien fusionado en TIPOS_CASO_ALL.
- posicion_de_tipo("OTROS") devuelve POSICION_OTROS.
- tag_crm("OTROS") devuelve "OTROS".
- TAGS_CRM_VALIDOS contiene "OTROS".
- CLIENTES_PROPIOS_EV mapea EV_MMC_SPAIN→"2" y ENGEL_VOLKERS_SPAIN→"27".
- cliente_propio_id / cliente_propio_label happy + error.
- tag_defaults_for_tipo_caso("OTROS") devuelve [] (sin tags por defecto;
  el abogado los añade manualmente cuando diagnostica el caso).
- tag_defaults_for_tipo_caso_judicial("OTROS") devuelve [] análogamente.
- link_ev_mmc / link_ev_mmc_judicial aceptan cliente_propio_id distinto al
  default (parametrización para el selector de Otros casos).
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from core import config
from core.config import (
    CLIENTE_PROPIO_DEFAULT,
    CLIENTES_PROPIOS_EV,
    POSICION_ACTORA,
    POSICION_DEFENSIVA,
    POSICION_OTROS,
    TAGS_CRM_VALIDOS,
    TIPOS_CASO_ACTORA,
    TIPOS_CASO_ALL,
    TIPOS_CASO_DEFENSIVA,
    TIPOS_CASO_OTROS,
    cliente_propio_id,
    cliente_propio_label,
    posicion_de_tipo,
    tag_crm,
)


# ---------------------------------------------------------------------------
# Taxonomía OTROS
# ---------------------------------------------------------------------------

class TestTiposCasoOtros:
    def test_otros_presente_en_taxonomia(self) -> None:
        assert "OTROS" in TIPOS_CASO_OTROS
        assert "OTROS" in TIPOS_CASO_ALL

    def test_otros_no_solapa_con_actora_ni_defensiva(self) -> None:
        assert "OTROS" not in TIPOS_CASO_ACTORA
        assert "OTROS" not in TIPOS_CASO_DEFENSIVA

    def test_tipos_caso_all_es_union_de_los_tres(self) -> None:
        esperado = len(TIPOS_CASO_ACTORA) + len(TIPOS_CASO_DEFENSIVA) + len(TIPOS_CASO_OTROS)
        assert len(TIPOS_CASO_ALL) == esperado

    def test_posicion_de_otros(self) -> None:
        assert posicion_de_tipo("OTROS") == POSICION_OTROS
        assert POSICION_OTROS != POSICION_ACTORA
        assert POSICION_OTROS != POSICION_DEFENSIVA

    def test_posicion_de_tipo_actora_y_defensiva_no_se_rompe(self) -> None:
        # Regresión: añadir OTROS no debe romper la clasificación previa.
        assert posicion_de_tipo("BAD_DEBT") == POSICION_ACTORA
        assert posicion_de_tipo("LAU_20") == POSICION_DEFENSIVA

    def test_posicion_desconocida_lanza(self) -> None:
        with pytest.raises(ValueError):
            posicion_de_tipo("FOO_BAR_INEXISTENTE")

    def test_tag_crm_otros(self) -> None:
        assert tag_crm("OTROS") == "OTROS"

    def test_tags_crm_validos_incluye_otros(self) -> None:
        assert "OTROS" in TAGS_CRM_VALIDOS


# ---------------------------------------------------------------------------
# Clientes propios E&V
# ---------------------------------------------------------------------------

class TestClientesPropiosEV:
    def test_ev_mmc_spain_id(self) -> None:
        assert cliente_propio_id("EV_MMC_SPAIN") == "2"

    def test_engel_volkers_spain_id(self) -> None:
        assert cliente_propio_id("ENGEL_VOLKERS_SPAIN") == "27"

    def test_label_ev_mmc(self) -> None:
        assert cliente_propio_label("EV_MMC_SPAIN") == "EV MMC SPAIN, S.L.U."

    def test_label_engel_volkers(self) -> None:
        assert "ENGEL" in cliente_propio_label("ENGEL_VOLKERS_SPAIN")
        assert "VÖLKERS" in cliente_propio_label("ENGEL_VOLKERS_SPAIN")

    def test_clave_desconocida_lanza(self) -> None:
        with pytest.raises(ValueError):
            cliente_propio_id("CLIENTE_FANTASMA")
        with pytest.raises(ValueError):
            cliente_propio_label("CLIENTE_FANTASMA")

    def test_default_es_ev_mmc(self) -> None:
        # El default histórico se preserva: honorarios → EV MMC SPAIN.
        assert CLIENTE_PROPIO_DEFAULT == "EV_MMC_SPAIN"
        assert cliente_propio_id(CLIENTE_PROPIO_DEFAULT) == "2"

    def test_mapping_completo(self) -> None:
        # Sanity check estructural — exactamente las dos sociedades del grupo.
        assert set(CLIENTES_PROPIOS_EV.keys()) == {"EV_MMC_SPAIN", "ENGEL_VOLKERS_SPAIN"}


# ---------------------------------------------------------------------------
# tag_defaults_for_tipo_caso con OTROS
# ---------------------------------------------------------------------------

class TestTagDefaultsOtros:
    def test_extrajudicial_otros_sin_tags_por_defecto(self) -> None:
        from core.sudespacho_create import tag_defaults_for_tipo_caso

        # OTROS no tiene tag de asunto en _TIPO_A_TAG_VERDE y POSICION_OTROS
        # no presupone tag de valoración → lista vacía.
        assert tag_defaults_for_tipo_caso("OTROS") == []

    def test_judicial_otros_sin_tags_por_defecto(self) -> None:
        from core.sudespacho_create import tag_defaults_for_tipo_caso_judicial

        assert tag_defaults_for_tipo_caso_judicial("OTROS") == []

    def test_extrajudicial_bad_debt_sigue_funcionando(self) -> None:
        # Regresión: el resto de tipos no se ha visto afectado.
        from core.sudespacho_create import tag_defaults_for_tipo_caso

        tags = tag_defaults_for_tipo_caso("BAD_DEBT")
        assert len(tags) == 2  # [verde_asunto, lila_valoracion]


# ---------------------------------------------------------------------------
# link_ev_mmc / link_ev_mmc_judicial — parametrización por cliente_propio_id
# ---------------------------------------------------------------------------

class TestLinkEvMmcParametrizado:
    def test_link_extrajudicial_acepta_id_27(self) -> None:
        """Verifica que el argumento cliente_propio_id se propaga al payload."""
        from core import sudespacho_relations as sr

        called: dict[str, object] = {}

        def fake_link(element, exp_id, payload, legacy_path, legacy_id, client):
            called["payload"] = payload
            called["legacy_id"] = legacy_id

        with patch.object(sr, "_link_rest_or_legacy", side_effect=fake_link), \
             patch.object(sr, "SudespachoLegacyClient"):
            sr.link_ev_mmc("12345", cliente_propio_id="27")

        assert called["payload"] == ["right.clientes_propios.27"]
        assert called["legacy_id"] == "27"

    def test_link_judicial_acepta_id_27(self) -> None:
        from core import sudespacho_relations as sr

        called: dict[str, object] = {}

        def fake_link(element, exp_id, payload, legacy_path, legacy_id, client):
            called["payload"] = payload
            called["legacy_id"] = legacy_id

        with patch.object(sr, "_link_rest_or_legacy", side_effect=fake_link), \
             patch.object(sr, "SudespachoLegacyClient"):
            sr.link_ev_mmc_judicial("12345", cliente_propio_id="27")

        assert called["payload"] == ["right.clientes_propios.27"]
        assert called["legacy_id"] == "27"

    def test_link_extrajudicial_default_es_ev_mmc(self) -> None:
        """Sin argumento explícito sigue vinculando EV MMC (ID=2)."""
        from core import sudespacho_relations as sr

        called: dict[str, object] = {}

        def fake_link(element, exp_id, payload, legacy_path, legacy_id, client):
            called["payload"] = payload
            called["legacy_id"] = legacy_id

        with patch.object(sr, "_link_rest_or_legacy", side_effect=fake_link), \
             patch.object(sr, "SudespachoLegacyClient"):
            sr.link_ev_mmc("12345")

        assert called["payload"] == ["right.clientes_propios.2"]
        assert called["legacy_id"] == "2"

    def test_link_judicial_default_es_ev_mmc(self) -> None:
        from core import sudespacho_relations as sr

        called: dict[str, object] = {}

        def fake_link(element, exp_id, payload, legacy_path, legacy_id, client):
            called["payload"] = payload
            called["legacy_id"] = legacy_id

        with patch.object(sr, "_link_rest_or_legacy", side_effect=fake_link), \
             patch.object(sr, "SudespachoLegacyClient"):
            sr.link_ev_mmc_judicial("12345")

        assert called["payload"] == ["right.clientes_propios.2"]
        assert called["legacy_id"] == "2"


# ---------------------------------------------------------------------------
# Nuevo tipo: DEVOLUCION_HONORARIOS (defensivo, cajón general no-LAU)
# ---------------------------------------------------------------------------

class TestDevolucionHonorarios:
    """Cobertura del tipo DEVOLUCION_HONORARIOS.

    Es la contraparte general de LAU_20 para reclamaciones de devolución de
    honorarios fuera del art. 20.1 LAU (compraventa, intermediación mercantil,
    encargos no residenciales). La infraestructura CRM (tags judicial y
    extrajudicial, NOTA, mapeos _TIPO_A_TAG_VERDE) ya estaba tendida desde el
    descubrimiento de tags 2026-04-28.
    """

    def test_presente_en_taxonomia(self) -> None:
        assert "DEVOLUCION_HONORARIOS" in TIPOS_CASO_DEFENSIVA
        assert "DEVOLUCION_HONORARIOS" in TIPOS_CASO_ALL
        assert "DEVOLUCION_HONORARIOS" not in TIPOS_CASO_ACTORA
        assert "DEVOLUCION_HONORARIOS" not in TIPOS_CASO_OTROS

    def test_posicion_es_defensiva(self) -> None:
        assert posicion_de_tipo("DEVOLUCION_HONORARIOS") == POSICION_DEFENSIVA

    def test_tag_crm(self) -> None:
        assert tag_crm("DEVOLUCION_HONORARIOS") == "DEVOLUCION HONORARIOS"
        assert "DEVOLUCION HONORARIOS" in TAGS_CRM_VALIDOS

    def test_tag_defaults_extrajudicial(self) -> None:
        """Defensivo → [verde_asunto, lila_riesgo_posible]."""
        from core.sudespacho_create import tag_defaults_for_tipo_caso

        tags = tag_defaults_for_tipo_caso("DEVOLUCION_HONORARIOS")
        assert len(tags) == 2  # verde + lila
        # Verde de asunto = TAG_VERDE_DEVOLUCION_HONORARIOS (#528800___126)
        assert tags[0] == "#528800___126"

    def test_tag_defaults_judicial(self) -> None:
        from core.sudespacho_create import tag_defaults_for_tipo_caso_judicial

        tags = tag_defaults_for_tipo_caso_judicial("DEVOLUCION_HONORARIOS")
        assert len(tags) == 2  # verde + lila
        # Verde de asunto judicial = J_TAG_VERDE_DEVOLUCION_HONORARIOS (#528800___55)
        assert tags[0] == "#528800___55"

    def test_nota_existe(self) -> None:
        """NOTA_DEVOLUCION_HONORARIOS está disponible en sudespacho_create."""
        from core import sudespacho_create as _sc

        assert hasattr(_sc, "NOTA_DEVOLUCION_HONORARIOS")
        assert "devolución" in _sc.NOTA_DEVOLUCION_HONORARIOS.lower()
        assert "honorarios" in _sc.NOTA_DEVOLUCION_HONORARIOS.lower()

    def test_fuera_de_informe_viabilidad(self) -> None:
        """Coherente con LAU_20 y DEVOLUCION_RESERVA: defensivos quedan fuera."""
        assert "DEVOLUCION_HONORARIOS" not in config.INFORME_VIABILIDAD_TIPOS
        # Sanity: el resto de defensivos análogos también queda fuera
        assert "LAU_20" not in config.INFORME_VIABILIDAD_TIPOS
        assert "DEVOLUCION_RESERVA" not in config.INFORME_VIABILIDAD_TIPOS

    def test_descripcion_distingue_de_lau_20(self) -> None:
        """La descripción debe explicitar que es el cajón fuera del art. 20.1 LAU."""
        _, descripcion = TIPOS_CASO_DEFENSIVA["DEVOLUCION_HONORARIOS"]
        # Mención explícita al art. 20.1 LAU (delimita el alcance frente a LAU_20)
        assert "20.1" in descripcion or "LAU" in descripcion
