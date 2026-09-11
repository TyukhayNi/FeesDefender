"""`case_manager.update_meta` — el actualizador que `ensure_case` no es (`MEJORAS #227`).

`ensure_case` **no repone `cuantia` ni `referencia_crm`** sobre un caso existente: los
acepta como kwargs y no escribe nada, en silencio. Hubo que editar `_caso.md` a mano,
bajo el mutex.

Ojo con generalizarlo, porque yo lo generalicé mal y la R1 me lo corrigió (H-07): `ensure_case`
**sí** actualiza `tipo_caso`, `direccion`, `id_go` y `ciudad` en un caso existente, y su
propio docstring lo dice. El defecto es de esos dos campos, no de la función entera. Y la
otra cita que traía esta cabecera también era falsa: el `MEJORAS #184` real habla de la
cobertura de los sondeos de correo, no de la referencia del CRM.

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
    """Test de CONSERVACIÓN, no control positivo — la R1 me corrigió el color.

    Que este test **pase** es lo que acredita que la vía vieja no repone la cuantía, y
    con ello que `update_meta` hace falta. Si algún día se pusiera **rojo**, sería que
    `ensure_case` cambió de comportamiento y que esta pieza sobra. La versión anterior
    de este docstring decía justo lo contrario (H-07 de la R1): un test que pasa no
    puede describirse como «mientras siga rojo».
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


# ===========================================================================
# Lo que la R1 de Codex rompió (2026-09-11)
# ===========================================================================
#
# El revisor tumbó la primera versión de `update_meta` con escenarios que estos
# tests no tenían. El más caro, H-01, destruía una nota del abogado — justo lo que
# `MEJORAS #146` protege— y mi `test_no_pisa_la_nota_escrita_a_mano` no lo veía
# porque puse la nota SIN un prefijo que coincidiera: el control positivo medía otra
# población.


def test_no_pisa_una_nota_QUE_EMPIEZA_IGUAL_que_la_linea(caso):
    """H-01 de la R1, ALTO. Era una destrucción de datos, no un caso de borde.

    Escenario literal del revisor: el abogado escribe en su sección

        - Cuantía: comprobar oferta, NO BORRAR

    y la versión anterior la reemplazaba por `- Cuantía: 42` —porque buscaba el
    prefijo en TODO el cuerpo y se quedaba con la primera coincidencia— dejando
    además la línea real de `## Sede` en `_(pendiente)_`. El informe decía
    `cuerpo=['cuantia']`: un «OK» sobre un expediente mutilado.
    """
    fm, cuerpo = _leer(caso)
    write_md(caso, fm, "# Notas\n- Cuantía: comprobar oferta, NO BORRAR\n\n" + cuerpo)

    informe = case_manager.update_meta(CASE_ID, cuantia=42.0)

    _, cuerpo2 = _leer(caso)
    assert "- Cuantía: comprobar oferta, NO BORRAR" in cuerpo2, "destruyó la nota"
    sede = cuerpo2.split("## Sede", 1)[1].split("\n## ", 1)[0]
    assert "- Cuantía: 42.0" in sede, "no actualizó la línea que sí es suya"
    assert informe["cuerpo"] == ["cuantia"]


def test_no_confunde_un_encabezado_dentro_de_un_bloque_de_codigo(caso):
    """H-02 de la R1: un `## Sede` dentro de ```md es un ejemplo, no una sección.

    El revisor metió una cerca con `## Sede` dentro y la inserción cayó **en el
    ejemplo**, dejando la sección real sin el dato — con `insertadas` en el informe.
    """
    fm, cuerpo = _leer(caso)
    ejemplo = "# Guía\n\n```md\n## Sede\n- Cuantía: EJEMPLO\n```\n\n"
    write_md(caso, fm, ejemplo + cuerpo)

    case_manager.update_meta(CASE_ID, cuantia=42.0)

    _, cuerpo2 = _leer(caso)
    assert "- Cuantía: EJEMPLO" in cuerpo2, "escribió dentro del bloque de código"
    real = cuerpo2.split("```", 2)[2]
    assert "- Cuantía: 42.0" in real, "no actualizó la sección real"


def test_dos_secciones_con_el_mismo_nombre_son_AMBIGUAS_y_no_se_adivina(caso):
    """H-02 de la R1: elegir la primera candidata es adivinar.

    El revisor construyó `## Sede` (histórica) y `## Sede` (vigente) y el dato fue a
    la primera sin que nadie lo dijera. Ahora el campo sale en `ambiguas`, el cuerpo
    no se toca, y el frontmatter sí se escribe: el llamador se entera.
    """
    fm, _ = _leer(caso)
    write_md(caso, fm, "## Sede\n\nEjemplo histórico\n\n## Sede\n\nSede vigente\n")

    informe = case_manager.update_meta(CASE_ID, cuantia=42.0)

    assert informe["ambiguas"] == ["cuantia"]
    assert informe["cuerpo"] == [] and informe["insertadas"] == []
    fm2, cuerpo = _leer(caso)
    assert fm2["meta"]["cuantia"] == 42.0, "el frontmatter sí se escribe"
    assert "42.0" not in cuerpo


def test_dos_lineas_del_mismo_campo_en_la_seccion_tambien_son_ambiguas(caso):
    """La otra mitad de la misma frontera: dos candidatas dentro del ámbito."""
    fm, cuerpo = _leer(caso)
    write_md(caso, fm, cuerpo.replace("- Cuantía: _(pendiente)_",
                                      "- Cuantía: _(pendiente)_\n- Cuantía: otra"))

    informe = case_manager.update_meta(CASE_ID, cuantia=42.0)

    assert informe["ambiguas"] == ["cuantia"]
    _, cuerpo2 = _leer(caso)
    assert "- Cuantía: otra" in cuerpo2


@pytest.mark.parametrize("campo, valor", [
    ("estado", "archivado"),
    ("titulo", "Otro título"),
    ("sudespacho_expedientes", [{"id": "20"}]),
    ("drive_ev_folder_id", "NEW"),
    ("checkout_nonce", "robado"),
    ("drive_remote_path", "otro:remoto"),
])
def test_los_campos_con_otro_dueno_se_RECHAZAN_y_se_dice_adonde_ir(caso, campo, valor):
    """H-03 de la R1: aceptarlos dejaba el índice incoherente sin decir nada.

    Medido por el revisor: `estado='archivado'` cambiaba el frontmatter y el cuerpo
    seguía diciendo `estado **instruccion**`; y `sudespacho_expedientes` en `meta` sin
    tocar la lista de primer nivel, que es **la que lee `get_case_status`**.

    La frontera no se arregla ampliando el alcance de este actualizador —eso lo
    convertiría en el reconstructor que `MEJORAS #146` retiró—, sino rechazando lo que
    no mantiene. Y rechazar **nombrando la vía sancionada** es lo que distingue una
    frontera de un hueco.
    """
    with pytest.raises(KeyError) as exc:
        case_manager.update_meta(CASE_ID, **{campo: valor})
    assert campo in str(exc.value)
    assert "update_meta no mantiene" in str(exc.value)


def test_un_indice_sin_frontmatter_legible_PARA_en_vez_de_normalizarlo(caso):
    """H-04 de la R1: normalizar un fichero roto lo convierte en otro fichero.

    El revisor pasó un `_caso.md` truncado —sin el cierre del frontmatter— y la
    versión anterior escribía un frontmatter NUEVO y dejaba el original **como
    cuerpo**, sin el lock y sin avisar. Un actualizador que no puede leer lo que
    actualiza para.
    """
    caso.write_text("---\ncase_id: C\nmeta:\n  checkout_nonce: N\n", encoding="utf-8")

    with pytest.raises(ValueError, match="frontmatter legible"):
        case_manager.update_meta(CASE_ID, cuantia=42.0)

    assert "checkout_nonce: N" in caso.read_text(encoding="utf-8"), "tocó el fichero roto"


def test_un_meta_que_no_es_un_mapa_tambien_para(caso):
    """La hermana de la anterior: `meta` con una forma que no es la suya."""
    caso.write_text("---\ncase_id: C\nmeta:\n  - una\n  - lista\n---\n\n# Cuerpo\n",
                    encoding="utf-8")

    with pytest.raises(ValueError, match="no es un mapa"):
        case_manager.update_meta(CASE_ID, cuantia=42.0)
