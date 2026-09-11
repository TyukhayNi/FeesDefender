"""`case_manager.update_meta` — el actualizador que `ensure_case` no es (`MEJORAS #227`).

`ensure_case` solo fija campos cuando **crea** el índice: sobre un caso existente acepta
los kwargs y no escribe nada, en silencio. Es la tercera vez que ese patrón hace daño
—`#184` la referencia del CRM, `#192` el campo, `#227` la cuantía—, y las tres veces hubo
que editar `_caso.md` a mano, bajo el mutex.

Lo que estos tests fijan no es «la cuantía se escribe»: es la **frontera**. `update_meta`
toca solo los campos que el llamador nombra, y nada más. Todo lo demás —la nota del
abogado en el cuerpo, las claves que el modelo no conoce, los wikilinks, las secciones
ajenas— sigue donde estaba, que es la propiedad que `MEJORAS #146` compró y que no se
puede perder al añadir un actualizador encima.

Árbol sintético en `tmp_path`, nunca el de producción.
"""
import pytest
import yaml

from core import case_manager
from core.casos import case_locator
from core.utils import write_md

CASE_ID = "BaRS3 - Calle de Prueba 1 (W-TEST01) - Vuelta"


@pytest.fixture
def caso(tmp_path, monkeypatch):
    """Un caso recién creado por la vía sancionada, en un árbol sintético."""
    root = tmp_path / "CASOS"
    root.mkdir()
    monkeypatch.setattr(case_locator, "_root", lambda: root)
    case_manager.ensure_case(CASE_ID, ciudad="Barcelona", tipo_caso="VUELTA")
    return case_locator.path_for(CASE_ID) / "00_Input" / "_caso.md"


def _leer(index):
    txt = index.read_text(encoding="utf-8")
    _, fm_txt, cuerpo = txt.split("---", 2)
    return yaml.safe_load(fm_txt), cuerpo


def test_la_cuantia_llega_al_frontmatter_y_al_cuerpo(caso):
    """El caso de `MEJORAS #227`: la cuantía se conoce al leer el encargo, no al alta."""
    informe = case_manager.update_meta(CASE_ID, cuantia=73140.0)

    fm, cuerpo = _leer(caso)
    assert fm["meta"]["cuantia"] == 73140.0
    assert "- Cuantía: 73140.0" in cuerpo
    assert "- Cuantía: _(pendiente)_" not in cuerpo
    assert informe["cuerpo"] == ["cuantia"] and informe["sin_linea"] == []


def test_ensure_case_sigue_sin_poder_reponerla(caso):
    """El control positivo de la pieza: la vía vieja **no** escribe, y hay que verlo.

    Si este test se pusiera verde por sí solo, significaría que `ensure_case` cambió de
    comportamiento y que `update_meta` sobra. Mientras siga rojo, la pieza está
    justificada.
    """
    case_manager.ensure_case(CASE_ID, cuantia=73140.0)
    fm, cuerpo = _leer(caso)
    assert fm["meta"]["cuantia"] is None
    assert "- Cuantía: _(pendiente)_" in cuerpo


def test_la_referencia_crm_tambien_y_en_las_dos_claves(caso):
    """`MEJORAS #184`: la referencia vive en el frontmatter de primer nivel Y en `meta`."""
    case_manager.update_meta(CASE_ID, referencia_crm="BaRS3 - Ref (W-TEST01) - Vuelta")

    fm, cuerpo = _leer(caso)
    assert fm["referencia_crm"] == "BaRS3 - Ref (W-TEST01) - Vuelta"
    assert fm["meta"]["referencia_crm"] == "BaRS3 - Ref (W-TEST01) - Vuelta"
    assert "- Referencia CRM: **BaRS3 - Ref (W-TEST01) - Vuelta**" in cuerpo
    # La línea NO existía (el caso se creó sin referencia): hubo que insertarla, que es
    # exactamente el caso de `MEJORAS #184`.
    assert cuerpo.index("- Referencia CRM:") < cuerpo.index("## Partes")


def test_no_pisa_la_nota_escrita_a_mano(caso):
    """La propiedad de `MEJORAS #146`, que un actualizador nuevo no puede perder."""
    txt = caso.read_text(encoding="utf-8")
    NOTA = "\n## Notas del letrado\n\nOjo con el plazo. [[hechos_atomicos]]\n"
    caso.write_text(txt + NOTA, encoding="utf-8")

    case_manager.update_meta(CASE_ID, cuantia=1234.5)

    cuerpo = caso.read_text(encoding="utf-8")
    assert "## Notas del letrado" in cuerpo
    assert "Ojo con el plazo. [[hechos_atomicos]]" in cuerpo
    assert "- Cuantía: 1234.5" in cuerpo


def test_conserva_las_claves_ajenas_del_frontmatter(caso):
    """`bucket_override` y compañía: lo que el modelo no conoce se queda."""
    fm, cuerpo = _leer(caso)
    fm["bucket_override"] = {"Escritos": "05_Procedimiento"}
    write_md(caso, fm, cuerpo)

    case_manager.update_meta(CASE_ID, cuantia=999.0)

    fm2, _ = _leer(caso)
    assert fm2["bucket_override"] == {"Escritos": "05_Procedimiento"}


def test_varios_campos_en_una_llamada(caso):
    informe = case_manager.update_meta(
        CASE_ID, cuantia=100.0, contraparte="EMPRESA DEUDORA SL", organo="JPI 5 Barcelona")

    _, cuerpo = _leer(caso)
    assert "- Cuantía: 100.0" in cuerpo
    assert "- Contraparte: EMPRESA DEUDORA SL" in cuerpo
    assert "- Órgano: JPI 5 Barcelona" in cuerpo
    assert sorted(informe["cuerpo"]) == ["contraparte", "cuantia", "organo"]


def test_un_campo_que_no_es_de_casemeta_duele_aqui(caso):
    """Un typo tiene que reventar, no aparecer como un dato que nunca se escribió."""
    with pytest.raises(KeyError, match="cuantiaa"):
        case_manager.update_meta(CASE_ID, cuantiaa=1.0)


def test_sin_campos_tambien_duele(caso):
    with pytest.raises(KeyError, match="nada que actualizar"):
        case_manager.update_meta(CASE_ID)


def test_un_caso_que_no_existe_no_se_crea(tmp_path, monkeypatch):
    """`update_meta` actualiza; crear es de `ensure_case`. Y lo dice, no lo calla."""
    root = tmp_path / "CASOS"
    root.mkdir()
    monkeypatch.setattr(case_locator, "_root", lambda: root)
    with pytest.raises(FileNotFoundError):
        case_manager.update_meta("BaRS3 - No Existe (W-NADA0) - Vuelta", cuantia=1.0)


def test_un_cuerpo_sin_la_seccion_lo_DICE_en_vez_de_adivinar(caso):
    """La frontera del informe: insertar a ciegas en un cuerpo ajeno es adivinar dónde.

    El dato queda en el frontmatter y el llamador **se entera** de que no llegó al
    cuerpo. Un `True` de vuelta habría sido el «OK que describe el paso y no el
    expediente».
    """
    fm, _ = _leer(caso)
    write_md(caso, fm, "# Solo un titulo, sin secciones\n")

    informe = case_manager.update_meta(CASE_ID, cuantia=5.0)

    assert informe["sin_linea"] == ["cuantia"]
    assert informe["cuerpo"] == [] and informe["insertadas"] == []
    fm2, cuerpo = _leer(caso)
    assert fm2["meta"]["cuantia"] == 5.0, "el frontmatter sí se escribe"
    assert "Cuantía" not in cuerpo
    assert "# Solo un titulo, sin secciones" in cuerpo


def test_una_seccion_sin_la_linea_la_INSERTA_donde_toca(caso):
    """Si la sección está pero la línea no, se pone al final de su bloque de items."""
    fm, cuerpo = _leer(caso)
    write_md(caso, fm, cuerpo.replace("- Cuantía: _(pendiente)_\n", ""))

    informe = case_manager.update_meta(CASE_ID, cuantia=42.0)

    assert informe["insertadas"] == ["cuantia"]
    _, cuerpo2 = _leer(caso)
    sede = cuerpo2.split("## Sede", 1)[1].split("## ", 1)[0]
    assert "- Cuantía: 42.0" in sede, f"no quedó bajo ## Sede: {sede!r}"


def test_un_valor_None_vuelve_a_pendiente(caso):
    """Poner a `None` es una actualización legítima: borra el dato y lo dice en el cuerpo."""
    case_manager.update_meta(CASE_ID, cuantia=7.0)
    case_manager.update_meta(CASE_ID, cuantia=None)

    fm, cuerpo = _leer(caso)
    assert fm["meta"]["cuantia"] is None
    assert "- Cuantía: _(pendiente)_" in cuerpo


def test_no_toca_el_lock_de_checkout(caso):
    """El índice de un caso PRESTADO no puede perder su lock al actualizar un campo.

    Es el mismo cuidado que `register_expediente` documenta: reescribir el índice sin
    conservar `estado_repositorio`/`checkout_*` desharía un checkout vivo.
    """
    case_manager.escribir_lock(CASE_ID, user="nikolai", timestamp="2026-09-11T08:00:00+02:00",
                               nonce="abc123", maquina="PC-TEST")
    antes, _ = _leer(caso)

    case_manager.update_meta(CASE_ID, cuantia=11.0)

    despues, _ = _leer(caso)
    for campo in ("estado_repositorio", "checkout_user", "checkout_nonce",
                  "checkout_maquina", "checkout_timestamp"):
        assert despues["meta"][campo] == antes["meta"][campo], f"se perdió {campo}"
    assert despues["meta"]["estado_repositorio"] == "prestado"
