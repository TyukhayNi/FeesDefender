"""`[APER-63]` — la ficha lee **un** contrario, y una reclamación puede tener dos firmantes.

`core/crm_ficha.py` hacía `data.get("contrario")` y construía uno solo, así que una
reclamación formulada por un matrimonio exigía una segunda llamada a mano
(`ensure_contrario_vinculado`) y comprobarla con `get_relaciones`.

**Y la semántica que faltaba (R1/H-08):** el lector devolvía `contrario=None` por igual para
`null`, para `[]` y para `[«esto no es un mapping»]`. Copiar el patrón de `colaboradores`
—filtrar lo que no sea `dict`— convertiría una lista con un elemento inválido en «cero
contrarios» **en silencio**, y validar mientras se itera escribiría el primero antes de
descubrir que el segundo está roto. **Un elemento inválido no es una parte ausente.**

Diseño: `docs/superpowers/specs/2026-09-14-p6-ficha-crm-y-actuaciones-design.md` §3.
"""
from __future__ import annotations

import pytest
import yaml

from core import crm_ficha


def _escribir(tmp_path, data: dict):
    p = tmp_path / "_ficha_crm.yaml"
    p.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return p


def test_una_lista_de_dos_contrarios_produce_dos(tmp_path):
    """El caso de `[APER-63]`: dos firmantes del encargo."""
    d = crm_ficha.cargar_ficha_yaml(_escribir(tmp_path, {"contrario": [
        {"nombre": "PRIMERA PARTE", "nif": "1234567K"},
        {"nombre": "SEGUNDA PARTE", "nif": "7654321M"},
    ]}))
    assert [c.nombre for c in d.contrarios] == ["PRIMERA PARTE", "SEGUNDA PARTE"]


def test_un_mapping_suelto_sigue_valiendo(tmp_path):
    """Compatibilidad: los `_ficha_crm.yaml` existentes llevan un mapping. No se migra nada."""
    d = crm_ficha.cargar_ficha_yaml(_escribir(tmp_path, {"contrario": {"nombre": "UNA PARTE"}}))
    assert [c.nombre for c in d.contrarios] == ["UNA PARTE"]
    assert d.contrario is not None and d.contrario.nombre == "UNA PARTE"


@pytest.mark.parametrize("valor, etiqueta", [
    (None, "null explícito"),
    ([], "lista vacía"),
])
def test_null_y_lista_vacia_significan_lo_mismo_que_ausente(tmp_path, valor, etiqueta):
    """Las tres formas de decir «no hay contrario» dicen lo mismo, y eso sí es legítimo."""
    d = crm_ficha.cargar_ficha_yaml(_escribir(tmp_path, {"contrario": valor}))
    assert d.contrarios == [], etiqueta
    assert d.contrario is None, etiqueta


def test_la_clave_ausente_tambien(tmp_path):
    d = crm_ficha.cargar_ficha_yaml(_escribir(tmp_path, {"notas_html": "x"}))
    assert d.contrarios == [] and d.contrario is None


def test_un_elemento_invalido_aborta_con_su_indice(tmp_path):
    """**Un elemento inválido no es una parte ausente.**

    Filtrarlo lo convertiría en «cero contrarios» en silencio, y la ficha se completaría
    dejando fuera a una parte sin que nadie lo dijera.
    """
    with pytest.raises(ValueError) as exc:
        crm_ficha.cargar_ficha_yaml(_escribir(tmp_path, {"contrario": [
            {"nombre": "PRIMERA PARTE"}, "esto-no-es-un-mapping",
        ]}))
    assert "1" in str(exc.value), str(exc.value)


def test_se_valida_la_coleccion_ENTERA_antes_de_construir_nada(tmp_path):
    """Con el primero válido y el segundo roto, no se construye el primero.

    Validar mientras se itera escribiría la primera parte antes de descubrir que la segunda
    está mal, y entonces el fallo dejaría la ficha a medias.
    """
    with pytest.raises(ValueError):
        crm_ficha.cargar_ficha_yaml(_escribir(tmp_path, {"contrario": [
            {"nombre": "PRIMERA PARTE"}, {"sin_nombre": "x"},
        ]}))


def test_una_forma_que_no_es_ni_mapping_ni_lista_se_rechaza(tmp_path):
    with pytest.raises(ValueError) as exc:
        crm_ficha.cargar_ficha_yaml(_escribir(tmp_path, {"contrario": "una cadena suelta"}))
    assert "mapping" in str(exc.value).lower() or "lista" in str(exc.value).lower()


def test_el_orden_del_fichero_se_conserva(tmp_path):
    """Quién es el primer firmante lo decide el letrado al escribir el YAML, no el lector."""
    d = crm_ficha.cargar_ficha_yaml(_escribir(tmp_path, {"contrario": [
        {"nombre": "TERCERA"}, {"nombre": "PRIMERA"}, {"nombre": "SEGUNDA"},
    ]}))
    assert [c.nombre for c in d.contrarios] == ["TERCERA", "PRIMERA", "SEGUNDA"]


def test_el_firmante_se_lee_del_yaml(tmp_path):
    """`[APER-72]`: el prefijo del asunto ES la tarifa, y quien opera no es quien firma.

    Por eso el firmante es una entrada humana explícita y no se infiere del actor de la UI.
    """
    d = crm_ficha.cargar_ficha_yaml(_escribir(tmp_path, {"firmante": "Nikolai_Tyukhay"}))
    assert d.firmante == "Nikolai_Tyukhay"


def test_sin_firmante_el_campo_queda_vacio_y_no_se_inventa(tmp_path):
    d = crm_ficha.cargar_ficha_yaml(_escribir(tmp_path, {"notas_html": "x"}))
    assert d.firmante == ""
