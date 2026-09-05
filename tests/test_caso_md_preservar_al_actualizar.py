"""`_write_case_index` sobre un `_caso.md` que ya existe CONSERVA lo que no es suyo.

Cierra `MEJORAS #146`: los registradores (`register_expediente`, `register_drive_ev`,
`cache_drive_folder_info`) reconstruian el fichero entero desde `CaseMeta`, y con ello se
perdian la nota del abogado en el cuerpo, las claves de frontmatter ajenas a las diez del
indice (`bucket_override`) y las claves de `meta` que el modelo no conoce.

Diseno: `docs/superpowers/specs/2026-09-05-caso-md-preservar-al-actualizar-design.md`, §5.
Medido por la R2 contra `origin/main` (2b32c32): MUEREN M1-M5, M10-bis, M10-ter, M11-M13 y
los M17-M22 de la R2; son POSITIVOS (pasan tambien en main) M6-M8, M10, M14, M15 y la mitad
del lock de M16. M14 y M15 no matan a main: matan a la REV. 1 del diseno (la deteccion
«nadie lo toco»), y estan para que no vuelva.
"""
from __future__ import annotations

import importlib

import pytest

from core.utils import read_md, write_md

CASE_ID = "EV-2026-PRESERVA"
NOTA = "\n\n## Nota del abogado\n\nLa reserva se firmo el 3 de marzo; el buscador no contesto.\n"
_ENC_EXPEDIENTES = "## Expedientes sudespacho"


def _cm():
    from core import case_manager
    importlib.reload(case_manager)
    return case_manager


def _alta(cm):
    case_dir = cm.ensure_case(CASE_ID, titulo="Caso de prueba")
    return case_dir / "00_Input" / "_caso.md"


def _anadir_nota(index):
    texto = index.read_text(encoding="utf-8")
    index.write_text(texto.rstrip("\n") + NOTA, encoding="utf-8")


def _mutar_fm(index, mutador):
    fm, body = read_md(index)
    mutador(fm)
    write_md(index, fm, body)


# Los tres registradores, como invocables sobre el case_id. `register_expediente` y
# `cache_drive_folder_info` son los otros dos llamadores de `_write_case_index` contados
# en el §1 del diseno; `ensure_case` no entra porque sobre un caso existente ya muta.
REGISTRADORES = {
    "register_expediente": lambda cm: cm.register_expediente(CASE_ID, "648", "extrajudiciales"),
    "register_drive_ev": lambda cm: cm.register_drive_ev(CASE_ID, "teamA", "folderB"),
    "cache_drive_folder_info": lambda cm: cm.cache_drive_folder_info(
        CASE_ID, "W-000001 - Inmueble", "0ADdrive"),
}


# ---------------------------------------------------------------------------
# M1-M3: la nota a mano sobrevive a cada registrador, byte a byte
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("registrador", sorted(REGISTRADORES))
def test_la_nota_del_abogado_sobrevive_al_registrador(tmp_casos_root, registrador):
    cm = _cm()
    index = _alta(cm)
    _anadir_nota(index)
    _, cuerpo_antes = read_md(index)

    REGISTRADORES[registrador](cm)

    fm, cuerpo_despues = read_md(index)
    assert "Nota del abogado" in cuerpo_despues
    # Fuera de los tres fragmentos del registrador (§3.3) el cuerpo es identico: se comparan
    # las lineas que no son ni la seccion de expedientes ni la linea de Drive E&V.
    def _sin_fragmentos(cuerpo: str) -> list[str]:
        fuera, en_seccion = [], False
        for ln in cuerpo.strip().split("\n"):
            if ln.strip() == _ENC_EXPEDIENTES:
                en_seccion = True
                continue
            if en_seccion and ln.startswith("## "):
                en_seccion = False
            if en_seccion or ln.startswith("- Drive E&V team:"):
                continue
            fuera.append(ln)
        return fuera
    assert _sin_fragmentos(cuerpo_despues) == _sin_fragmentos(cuerpo_antes)


def test_m2_la_nota_sobrevive_y_el_expediente_queda_registrado(tmp_casos_root):
    """Conservar el cuerpo no puede costar la actualizacion: las dos cosas a la vez."""
    cm = _cm()
    index = _alta(cm)
    _anadir_nota(index)

    cm.register_expediente(CASE_ID, "648", "extrajudiciales")

    fm, cuerpo = read_md(index)
    assert "Nota del abogado" in cuerpo
    ids_top = {str(e["id"]) for e in fm["sudespacho_expedientes"]}
    ids_meta = {str(e["id"]) for e in fm["meta"]["sudespacho_expedientes"]}
    assert ids_top == {"648"} == ids_meta
    assert cm.get_case_status(CASE_ID)["expedientes"][0]["id"] == "648"


# ---------------------------------------------------------------------------
# M4: una clave TOP-LEVEL ajena a las diez del indice sobrevive
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("registrador", sorted(REGISTRADORES))
def test_m4_bucket_override_sobrevive_al_registrador(tmp_casos_root, registrador):
    """`bucket_override` lo edita el abogado a mano (`case_manager.py:1174`) y hoy no
    sobrevive a un pull de Drive."""
    cm = _cm()
    index = _alta(cm)
    bucket = cm.CRM_BUCKET_DEMANDA          # un bucket VALIDO: `read_bucket_overrides` filtra
    _mutar_fm(index, lambda fm: fm.__setitem__("bucket_override", {"doc_7": bucket}))

    REGISTRADORES[registrador](cm)

    fm, _ = read_md(index)
    assert fm.get("bucket_override") == {"doc_7": bucket}
    assert cm.read_bucket_overrides(CASE_ID) == {"doc_7": bucket}


# ---------------------------------------------------------------------------
# M5: una clave ajena DENTRO de `meta` sobrevive
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("registrador", sorted(REGISTRADORES))
def test_m5_una_clave_de_meta_que_el_modelo_no_conoce_sobrevive(tmp_casos_root, registrador):
    cm = _cm()
    index = _alta(cm)
    _mutar_fm(index, lambda fm: fm["meta"].__setitem__("clave_de_otro_modulo", "valor"))

    REGISTRADORES[registrador](cm)

    fm, _ = read_md(index)
    assert fm["meta"].get("clave_de_otro_modulo") == "valor"


# ---------------------------------------------------------------------------
# M6 (positivo): el lock de checkout ya sobrevivia; que siga
# ---------------------------------------------------------------------------

def test_m6_el_lock_de_checkout_sobrevive_a_register_expediente(tmp_casos_root):
    cm = _cm()
    index = _alta(cm)

    def _prestar(fm):
        fm["meta"].update({
            "estado_repositorio": "prestado",
            "checkout_user": "ana",
            "checkout_nonce": "n0nce",
            "checkout_maquina": "PC-ANA",
        })
    _mutar_fm(index, _prestar)

    cm.register_expediente(CASE_ID, "648", "extrajudiciales")

    fm, _ = read_md(index)
    meta = fm["meta"]
    assert meta["estado_repositorio"] == "prestado"
    assert meta["checkout_user"] == "ana"
    assert meta["checkout_nonce"] == "n0nce"
    assert meta["checkout_maquina"] == "PC-ANA"


# ---------------------------------------------------------------------------
# M7 (positivo): un cuerpo INTACTO se regenera y sigue al dia
# ---------------------------------------------------------------------------

def test_m7_un_cuerpo_intacto_lista_el_expediente_nuevo(tmp_casos_root):
    """Conservar no puede significar congelar: sin edicion humana, el cuerpo es obra de la
    plantilla y debe reflejar lo registrado."""
    cm = _cm()
    index = _alta(cm)

    cm.register_expediente(CASE_ID, "648", "extrajudiciales")

    _, cuerpo = read_md(index)
    assert "ID 648" in cuerpo
    assert "00_Input/sudespacho_648/" in cuerpo


def test_m7_un_cuerpo_intacto_refleja_los_ids_de_drive(tmp_casos_root):
    cm = _cm()
    index = _alta(cm)

    cm.register_drive_ev(CASE_ID, "teamA", "folderB")

    _, cuerpo = read_md(index)
    assert "`teamA`" in cuerpo and "`folderB`" in cuerpo


def test_m2_bis_la_nota_sobrevive_Y_el_cuerpo_lista_el_expediente(tmp_casos_root):
    """Rev. 2 del diseno (§3.3): ya no hay «cuerpo tocado» que congelar. El registrador
    reescribe solo su seccion y la nota sigue donde estaba."""
    cm = _cm()
    index = _alta(cm)
    _anadir_nota(index)

    cm.register_expediente(CASE_ID, "648", "extrajudiciales")

    fm, cuerpo = read_md(index)
    assert "ID 648" in cuerpo
    assert "Nota del abogado" in cuerpo
    assert cuerpo.index(_ENC_EXPEDIENTES) < cuerpo.index("## Navegación") < cuerpo.index("Nota del abogado")


# ---------------------------------------------------------------------------
# M3: los wikilinks de `registrar_outputs` bajo `## Navegación` sobreviven
# ---------------------------------------------------------------------------

def test_m3_el_wikilink_de_registrar_outputs_sobrevive_y_el_expediente_aparece(tmp_casos_root):
    """`.claude/skills/_shared/registrar_outputs.py` inserta `- [[x]]` justo debajo de
    `## Navegación`. Con `556b8b2`, el siguiente registrador lo borraba (R1/H-04, sonda D10)."""
    cm = _cm()
    index = _alta(cm)
    texto = index.read_text(encoding="utf-8")
    marca = "## Navegación\n"
    i = texto.index(marca) + len(marca)
    index.write_text(texto[:i] + "\n- [[STS_1234_2026]]\n" + texto[i:], encoding="utf-8")

    cm.register_expediente(CASE_ID, "648", "extrajudiciales")

    _, cuerpo = read_md(index)
    assert "[[STS_1234_2026]]" in cuerpo
    assert "ID 648" in cuerpo
    assert cuerpo.count("## Navegación") == 1


# ---------------------------------------------------------------------------
# M5-bis: `proyeccion_local`, la clave ajena con consecuencia real
# ---------------------------------------------------------------------------

def test_m5_bis_la_copia_prestada_sigue_siendo_proyeccion_tras_un_pull(tmp_casos_root):
    """`case_locator._es_proyeccion_local` lee `meta.proyeccion_local`. Con `556b8b2` un
    `register_drive_ev` (cada pull de Drive) la borraba y la copia pasaba a ser un caso mas
    del catalogo (R1/H-10, sonda P4)."""
    from core.casos import case_locator
    cm = _cm()
    index = _alta(cm)
    _mutar_fm(index, lambda fm: fm["meta"].__setitem__("proyeccion_local", True))
    assert case_locator._es_proyeccion_local(index.parent.parent) is True

    cm.register_drive_ev(CASE_ID, "teamA", "folderB")

    assert case_locator._es_proyeccion_local(index.parent.parent) is True


# ---------------------------------------------------------------------------
# M10-bis: si la escritura del temporal falla, no queda temporal y el original esta integro
# ---------------------------------------------------------------------------

def test_m10_bis_si_write_md_lanza_no_queda_temporal_y_el_original_sigue(tmp_casos_root, monkeypatch):
    cm = _cm()
    index = _alta(cm)
    _anadir_nota(index)
    antes = index.read_bytes()

    def _explota(path, fm, body):
        path.write_text("basura", encoding="utf-8")
        raise OSError("disco lleno (simulado)")
    monkeypatch.setattr(cm, "write_md", _explota)

    with pytest.raises(OSError):
        cm.register_drive_ev(CASE_ID, "teamA", "folderB")

    assert index.read_bytes() == antes
    assert [p.name for p in index.parent.iterdir() if p.name.startswith("._caso.")] == []


def test_m10_ter_el_temporal_esta_excluido_del_merge_y_del_carveout():
    """R1/H-07: `._caso.<pid>.tmp` no estaba en `MERGE_EXCLUSIONS`, asi que un huerfano
    de `_atomic_write_caso_md` (y ahora de cada pull) era «contenido del expediente»."""
    import fnmatch
    from core import config
    from plugins.expedientes_xl.tiers import PROTOCOL_EDIT
    huerfano = "._caso.4242.tmp"
    assert any(fnmatch.fnmatch(huerfano, p) for p in config.MERGE_EXCLUSIONS)
    assert any(fnmatch.fnmatch(huerfano, p) for p in PROTOCOL_EDIT)


# ---------------------------------------------------------------------------
# M11: el estado D8 de `update_pull_state` sobrevive a `register_drive_ev`
# ---------------------------------------------------------------------------

def test_m11_el_pull_state_sobrevive_a_register_drive_ev(tmp_casos_root):
    """`update_pull_state` guarda `doc_ids`/`last_sync` SOLO en la lista top-level;
    `register_drive_ev` la reconstruia desde el espejo `meta` y lo perdia (R1/H-02, P5)."""
    cm = _cm()
    _alta(cm)
    cm.register_expediente(CASE_ID, "648", "extrajudiciales")
    cm.update_pull_state(CASE_ID, "648", last_sync="2026-09-05T10:00:00", doc_ids=["d1", "d2"])

    cm.register_drive_ev(CASE_ID, "teamA", "folderB")

    estado = cm.read_pull_state(CASE_ID, "648")
    assert estado is not None
    assert estado["doc_ids"] == ["d1", "d2"]
    assert estado["last_sync"] == "2026-09-05T10:00:00"
    # y el vinculo sigue visible para quien lee el indice
    assert cm.get_case_status(CASE_ID)["expedientes"][0]["id"] == "648"


def test_m11_bis_un_vinculo_creado_solo_por_update_pull_state_no_desaparece(tmp_casos_root):
    """P5b de la R1: entrada creada por `update_pull_state` sin `register_expediente` previo
    -> con `556b8b2` la lista quedaba vacia tras un pull de Drive."""
    cm = _cm()
    _alta(cm)
    cm.update_pull_state(CASE_ID, "649", element="extrajudiciales", doc_ids=["x"])

    cm.register_drive_ev(CASE_ID, "teamA", "folderB")

    ids = [e["id"] for e in cm.get_case_status(CASE_ID)["expedientes"]]
    assert ids == ["649"]


# ---------------------------------------------------------------------------
# M12: una entrada sin `input_dir` no aborta el registrador
# ---------------------------------------------------------------------------

def test_m12_una_entrada_sin_input_dir_no_aborta_y_se_pinta_con_el_default(tmp_casos_root):
    """`update_pull_state` crea entradas sin `input_dir`; la plantilla hacia `e['input_dir']`
    y el siguiente registrador moria con `KeyError` (R1/H-05, P5c)."""
    cm = _cm()
    index = _alta(cm)
    cm.update_pull_state(CASE_ID, "649", element="extrajudiciales")

    cm.register_expediente(CASE_ID, "650", "extrajudiciales")

    fm, cuerpo = read_md(index)
    assert {str(e["id"]) for e in fm["sudespacho_expedientes"]} == {"649", "650"}
    assert "`00_Input/sudespacho_649/`" in cuerpo
    assert "`00_Input/sudespacho_650/`" in cuerpo


# ---------------------------------------------------------------------------
# M13: un `_caso.md` truncado se reconstruye integro, no se congela corrupto
# ---------------------------------------------------------------------------

def test_m13_un_indice_truncado_se_reconstruye_con_un_solo_frontmatter(tmp_casos_root):
    cm = _cm()
    index = _alta(cm)
    texto = index.read_text(encoding="utf-8")
    index.write_text(texto[: len(texto) // 3], encoding="utf-8")   # sin cierre `---`

    cm.register_drive_ev(CASE_ID, "teamA", "folderB")

    texto = index.read_text(encoding="utf-8")
    fm, cuerpo = read_md(index)
    assert fm.get("case_id") == CASE_ID
    assert fm["meta"]["drive_ev_team_id"] == "teamA"
    assert "---" not in cuerpo
    assert texto.count("\n---\n") == 1          # un unico cierre de frontmatter


# ---------------------------------------------------------------------------
# M14: quitar un expediente por mutador de frontmatter -> el cuerpo deja de listarlo
# ---------------------------------------------------------------------------

def test_m14_un_expediente_retirado_del_frontmatter_desaparece_del_cuerpo(tmp_casos_root):
    """Sonda D3 de la R1: `remove_expediente_link` muta solo el frontmatter y el cuerpo
    queda listando lo desvinculado. La rev. 1 lo habria congelado asi para siempre."""
    cm = _cm()
    index = _alta(cm)
    cm.register_expediente(CASE_ID, "648", "extrajudiciales")
    cm.register_expediente(CASE_ID, "700", "expedientes_judiciales")

    def _quitar_648(fm):
        fm["sudespacho_expedientes"] = [e for e in fm["sudespacho_expedientes"] if str(e["id"]) != "648"]
        fm["meta"]["sudespacho_expedientes"] = list(fm["sudespacho_expedientes"])
    cm._atomic_write_caso_md(CASE_ID, _quitar_648)
    _, cuerpo = read_md(index)
    assert "ID 648" in cuerpo                 # rancio, como deja el mutador

    cm.register_drive_ev(CASE_ID, "teamA", "folderB")

    _, cuerpo = read_md(index)
    assert "ID 648" not in cuerpo
    assert "ID 700" in cuerpo


# ---------------------------------------------------------------------------
# M15: idempotencia de bytes
# ---------------------------------------------------------------------------

def test_m15_dos_actualizaciones_iguales_dejan_el_mismo_fichero(tmp_casos_root):
    cm = _cm()
    index = _alta(cm)
    _anadir_nota(index)
    _mutar_fm(index, lambda fm: fm.__setitem__("bucket_override", {"doc_7": "DEMANDA"}))

    cm.register_expediente(CASE_ID, "648", "extrajudiciales")
    primera = index.read_bytes()
    # La segunda llamada con el mismo id es un no-op declarado; se fuerza una reescritura
    # equivalente pasando por el sumidero con el MISMO meta.
    fm, _ = read_md(index)
    from dataclasses import fields as _f
    known = {f.name for f in _f(cm.CaseMeta)}
    meta = cm.CaseMeta(**{k: v for k, v in fm["meta"].items() if k in known})
    cm._write_case_index(index.parent.parent, meta)

    assert index.read_bytes() == primera


# ---------------------------------------------------------------------------
# M16 (positivo): clave ajena + None en un campo del lock -> ajena sigue, lock coalescido
# ---------------------------------------------------------------------------

def test_m16_clave_ajena_y_lock_en_None_coalescen_bien(tmp_casos_root):
    cm = _cm()
    index = _alta(cm)

    def _mutar(fm):
        fm["meta"]["clave_ajena"] = "valor-ajeno"
        fm["meta"]["estado_repositorio"] = None
    _mutar_fm(index, _mutar)

    cm.register_expediente(CASE_ID, "648", "extrajudiciales")

    fm, _ = read_md(index)
    assert fm["meta"]["clave_ajena"] == "valor-ajeno"     # esta mitad MATA a main (es M5)
    # El sumidero NO inventa valores: lo persistido (aqui `None`) es lo que queda; los
    # registradores ya lo pasaban asi a `CaseMeta` y el lector lo trata como ausente.
    assert fm["meta"]["estado_repositorio"] is None      # esta mitad es POSITIVA
    assert "checkout_user" in fm["meta"]


# ---------------------------------------------------------------------------
# R2 sobre el diff (2026-09-05): M17-M22
# ---------------------------------------------------------------------------

def test_m17_una_entrada_sin_id_no_se_duplica_en_cada_pull(tmp_casos_root):
    """R2/H-01: el espejo `meta` ES la lista fusionada, y los registradores parten de el;
    una entrada sin `id` volvia como «nueva» en cada pasada: 2 -> 4 -> 8 -> 16."""
    cm = _cm()
    index = _alta(cm)

    def _rara(fm):
        fm["sudespacho_expedientes"] = [{"element": "extrajudiciales"}]
        fm["meta"]["sudespacho_expedientes"] = [{"element": "extrajudiciales"}]
    _mutar_fm(index, _rara)

    for folder in ("f1", "f2", "f3"):
        cm.register_drive_ev(CASE_ID, "teamA", folder)
        cm.cache_drive_folder_info(CASE_ID, f"W-{folder}", "0AD")

    fm, cuerpo = read_md(index)
    assert len(fm["sudespacho_expedientes"]) == 1
    assert len(fm["meta"]["sudespacho_expedientes"]) == 1
    assert cuerpo.count("ID ?") == 1


def test_m18_un_encabezado_de_otro_nivel_tras_la_seccion_sobrevive(tmp_casos_root):
    """R2/H-02: la seccion (c) acababa en el siguiente `## `; un `# Notas` o un `### Detalle`
    a mano entre la seccion y `## Navegacion` se destruia."""
    cm = _cm()
    index = _alta(cm)
    cm.register_expediente(CASE_ID, "648", "extrajudiciales")
    texto = index.read_text(encoding="utf-8")
    marca = "## Navegación\n"
    i = texto.index(marca)
    extra = "### Detalle del abogado\n\nEsto lo escribi yo bajo un ###.\n\n# Notas nivel 1\n\nY esto bajo un # nivel 1.\n\n"
    index.write_text(texto[:i] + extra + texto[i:], encoding="utf-8")

    cm.register_drive_ev(CASE_ID, "teamA", "folderB")

    _, cuerpo = read_md(index)
    for frase in ("### Detalle del abogado", "Esto lo escribi yo bajo un ###.",
                  "# Notas nivel 1", "Y esto bajo un # nivel 1.", "ID 648", "`teamA`"):
        assert frase in cuerpo, frase
    assert cuerpo.count(_ENC_EXPEDIENTES) == 1


def test_m19_el_frontmatter_no_gana_anclas_yaml(tmp_casos_root):
    """R2/H-03: la misma lista en dos claves salia como `&id001` / `*id001`."""
    cm = _cm()
    index = _alta(cm)
    cm.register_expediente(CASE_ID, "648", "extrajudiciales")
    cm.register_drive_ev(CASE_ID, "teamA", "folderB")
    texto = index.read_text(encoding="utf-8")
    assert "&id" not in texto and "*id" not in texto


def test_m20_un_cuerpo_sin_frontmatter_se_conserva_y_gana_frontmatter(tmp_casos_root):
    """R2/H-07: un fichero que NO empieza por `---` es un cuerpo escrito, no un truncado."""
    cm = _cm()
    index = _alta(cm)
    index.write_text("# Titulo mio\n\nNota importante sin frontmatter.\n", encoding="utf-8")

    cm.register_drive_ev(CASE_ID, "teamA", "folderB")

    fm, cuerpo = read_md(index)
    assert fm.get("case_id") == CASE_ID
    assert fm["meta"]["drive_ev_team_id"] == "teamA"
    assert "Nota importante sin frontmatter." in cuerpo
    assert "# Titulo mio" in cuerpo


def test_m21_un_id_numerico_y_el_mismo_id_en_cadena_son_la_misma_entrada(tmp_casos_root):
    cm = _cm()
    index = _alta(cm)
    _mutar_fm(index, lambda fm: fm.__setitem__(
        "sudespacho_expedientes", [{"id": 648, "element": "extrajudiciales", "doc_ids": ["d"]}]))

    cm.register_expediente(CASE_ID, "648", "extrajudiciales")

    fm, _ = read_md(index)
    assert [str(e["id"]) for e in fm["sudespacho_expedientes"]] == ["648"]
    assert fm["sudespacho_expedientes"][0]["doc_ids"] == ["d"]


@pytest.mark.parametrize("registrador", ["register_expediente", "cache_drive_folder_info"])
def test_m22_el_truncado_se_reconstruye_con_los_otros_registradores(tmp_casos_root, registrador):
    cm = _cm()
    index = _alta(cm)
    texto = index.read_text(encoding="utf-8")
    index.write_text(texto[: len(texto) // 3], encoding="utf-8")

    REGISTRADORES[registrador](cm)

    fm, cuerpo = read_md(index)
    assert fm.get("case_id") == CASE_ID
    assert "---" not in cuerpo


# ---------------------------------------------------------------------------
# M8 (positivo): la CREACION no cambia
# ---------------------------------------------------------------------------

def test_m8_la_creacion_sigue_produciendo_las_diez_claves_y_la_plantilla(tmp_casos_root):
    cm = _cm()
    index = _alta(cm)

    fm, cuerpo = read_md(index)
    assert list(fm) == [
        "case_id", "tipo", "fase", "fecha", "estado", "ciudad", "referencia_crm",
        "sudespacho_expedientes", "drive", "meta",
    ]
    assert cuerpo.startswith("# Caso de prueba")
    assert "## Navegación" in cuerpo
    assert fm["meta"]["case_id"] == CASE_ID


# ---------------------------------------------------------------------------
# M10: la escritura atomica no deja temporales
# ---------------------------------------------------------------------------

def test_m10_no_queda_temporal_tras_actualizar(tmp_casos_root):
    cm = _cm()
    index = _alta(cm)
    _anadir_nota(index)

    cm.register_drive_ev(CASE_ID, "teamA", "folderB")

    residuo = [p.name for p in index.parent.iterdir() if p.name.startswith("._caso.")]
    assert residuo == []
    fm, _ = read_md(index)
    assert fm["meta"]["drive_ev_team_id"] == "teamA"
