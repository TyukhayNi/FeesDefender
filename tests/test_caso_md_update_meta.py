"""`update_meta` fija la cuantía en `_caso.md` sin poder destruir el cuerpo (`MEJORAS #227`).

La cuantía se conoce al leer el encargo, pero el alta en el CRM va **al final** de la
apertura, así que `--cuantia` acababa en el CRM y no en el índice local, que se quedaba en
`- Cuantía: _(pendiente)_`. `ensure_case` no puede reponerlo: su contrato es crear.

El primer intento (PR #338, **cerrado**) **localizaba** la línea a sustituir dentro del
cuerpo Markdown. Dos rondas adversariales encontraron **seis** formas de romper esa misma
propiedad, y el coste de equivocarse es una nota del letrado destruida. Éste no localiza:
**compara**. Si el cuerpo es exactamente el que `_cuerpo_del_indice` produciría para la
`meta` del frontmatter, se reescribe entero; si difiere en cualquier cosa, no se toca **ni
un byte** y se declara.

**Por qué tantos asertos sobre bytes y no sobre cadenas.** La R1 de este diseño midió que
`write_md` hace `body.strip()` y traduce los saltos de línea: «conservar el cuerpo»
pasándolo otra vez por el escritor le quitaba los espacios finales a la nota del letrado.
Un test sobre `str` no ve ninguna de las dos cosas.

Diseño: `docs/superpowers/specs/2026-09-11-cuantia-en-caso-md-comparar-no-localizar-design.md`.
"""
from __future__ import annotations

import hashlib
import importlib
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def cm(tmp_casos_root):
    from core import case_manager
    importlib.reload(case_manager)
    return case_manager


def _index(cm, case_id: str) -> Path:
    from core.casos.case_locator import buscar
    return buscar(case_id) / "00_Input" / "_caso.md"


def _caso(cm, case_id="EV-227-TEST", **kw):
    kw.setdefault("titulo", "Caso de prueba")
    cm.ensure_case(case_id, **kw)
    return _index(cm, case_id)


def _partes(index: Path) -> tuple[bytes, bytes]:
    """`(bloque de frontmatter, cuerpo)` en bytes, **con un partidor independiente**.

    No usa `_partir_indice` de producción a propósito: si el oráculo del test comparte la
    frontera con el código que vigila, un error de frontera queda invisible — que es
    exactamente lo que pasó con el regex compartido (R2/H2-01). Éste parte por la línea del
    cierre, escrito aparte.
    """
    crudo = index.read_bytes()
    lineas = crudo.split(b"\n")
    assert lineas and lineas[0].strip() == b"---", "el fichero de la prueba no empieza por ---"
    i = next(j for j in range(1, len(lineas)) if lineas[j].strip() == b"---")
    fin = min(len(b"\n".join(lineas[:i + 1])) + 1, len(crudo))
    return crudo[:fin], crudo[fin:]


def _fm(index: Path) -> dict:
    return yaml.safe_load(_partes(index)[0].decode("utf-8").split("---", 2)[1])


def _sha(index: Path) -> str:
    return hashlib.sha256(index.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Conservación del cuerpo — el corazón de la pieza
# ---------------------------------------------------------------------------

def test_reescribe_el_cuerpo_cuando_es_canonico(cm):
    index = _caso(cm)
    assert "- Cuantía: _(pendiente)_" in index.read_text(encoding="utf-8")

    informe = cm.update_meta("EV-227-TEST", cuantia=73140.5)

    assert informe["cuerpo"] == "reescrito"
    assert informe["frontmatter"] == ["cuantia"]
    assert informe["motivo"] is None
    assert "- Cuantía: 73140.5" in index.read_text(encoding="utf-8")
    assert _fm(index)["meta"]["cuantia"] == 73140.5


def test_con_una_nota_del_letrado_el_cuerpo_queda_IDENTICO_EN_BYTES(cm):
    """El aserto es sobre bytes, y esa palabra es el test entero.

    La nota lleva **espacios finales** y una **línea indentada** a propósito: son las dos
    cosas que `write_md` destruye (`body.strip()`) y que un aserto sobre `str` normalizado
    no vería (R1/H-01).
    """
    index = _caso(cm)
    texto = index.read_text(encoding="utf-8")
    nota = ("## Notas del letrado\n\n"
            "    - Cuantía: comprobar la oferta, NO BORRAR\n"
            "- pendiente de hablar con el consultor   \n\n")
    index.write_text(texto.replace("## Navegación", nota + "## Navegación"), encoding="utf-8")
    cuerpo_antes = _partes(index)[1]

    informe = cm.update_meta("EV-227-TEST", cuantia=73140.5)

    assert informe["cuerpo"] == "conservado"
    assert informe["motivo"], "conservar sin decir por qué es mentir por omisión"
    assert _partes(index)[1] == cuerpo_antes, "el cuerpo cambió de bytes"
    assert _fm(index)["meta"]["cuantia"] == 73140.5, "la cuantía tiene que llegar al frontmatter"
    assert "- Cuantía: _(pendiente)_" in index.read_text(encoding="utf-8")


def test_un_cuerpo_en_CRLF_sigue_en_CRLF(cm):
    """La otra mitad de H-01: `write_text` traduce los saltos a los de la plataforma."""
    index = _caso(cm)
    fm_b, cuerpo_b = _partes(index)
    cuerpo_crlf = cuerpo_b.replace(b"\n", b"\r\n").replace(
        b"## Navegaci\xc3\xb3n", b"## Nota\r\n\r\n- ojo\r\n\r\n## Navegaci\xc3\xb3n")
    index.write_bytes(fm_b + cuerpo_crlf)

    informe = cm.update_meta("EV-227-TEST", cuantia=1.0)

    assert informe["cuerpo"] == "conservado"
    assert _partes(index)[1] == cuerpo_crlf, "los finales de línea del cuerpo cambiaron"


def test_un_solo_espacio_de_mas_ya_no_es_canonico(cm):
    """El control fino: la comparación es exacta, no aproximada."""
    index = _caso(cm)
    fm_b, cuerpo_b = _partes(index)
    index.write_bytes(fm_b + cuerpo_b.replace(b"## Partes", b"## Partes "))
    cuerpo_antes = _partes(index)[1]

    informe = cm.update_meta("EV-227-TEST", cuantia=5.0)

    assert informe["cuerpo"] == "conservado"
    assert _partes(index)[1] == cuerpo_antes


def test_un_indice_sin_frontmatter_NO_SE_ESCRIBE(cm):
    """Se mira el ÁRBOL, no el tipo de la excepción (R2/H2-08 del intento retirado)."""
    index = _caso(cm)
    index.write_text("# Sin frontmatter\n\nnota del letrado\n", encoding="utf-8")
    antes = _sha(index)

    informe = cm.update_meta("EV-227-TEST", cuantia=9.0)

    assert informe["cuerpo"] == "sin tocar"
    assert informe["frontmatter"] == []
    assert informe["motivo"]
    assert _sha(index) == antes, "escribió sobre un índice que no sabe leer"


def test_un_frontmatter_con_YAML_invalido_NO_SE_ESCRIBE(cm):
    index = _caso(cm)
    index.write_text("---\na: [sin cerrar\n---\n\n# T\n", encoding="utf-8")
    antes = _sha(index)

    informe = cm.update_meta("EV-227-TEST", cuantia=9.0)

    assert informe["cuerpo"] == "sin tocar"
    assert _sha(index) == antes


def test_un_meta_que_no_reconstruye_CaseMeta_NO_SE_ESCRIBE(cm):
    """Sin `meta_previa` no hay con qué comparar, así que no se toca nada (R1/H-08)."""
    index = _caso(cm)
    fm_b, cuerpo_b = _partes(index)
    fm = yaml.safe_load(fm_b.decode("utf-8").split("---", 2)[1])
    del fm["meta"]["case_id"]          # `CaseMeta` lo exige
    index.write_bytes(("---\n" + yaml.safe_dump(fm, allow_unicode=True) + "---\n").encode()
                      + cuerpo_b)
    antes = _sha(index)

    informe = cm.update_meta("EV-227-TEST", cuantia=9.0)

    assert informe["cuerpo"] == "sin tocar"
    assert _sha(index) == antes


def test_una_clave_ajena_en_meta_no_impide_comparar(cm):
    """El espejo del frontmatter conserva claves que `CaseMeta` no conoce: se FILTRAN."""
    index = _caso(cm)
    fm_b, cuerpo_b = _partes(index)
    fm = yaml.safe_load(fm_b.decode("utf-8").split("---", 2)[1])
    fm["meta"]["clave_de_otro"] = "NO BORRAR"
    index.write_bytes(("---\n" + yaml.safe_dump(fm, allow_unicode=True) + "---\n").encode()
                      + cuerpo_b)

    informe = cm.update_meta("EV-227-TEST", cuantia=7.0)

    assert informe["cuerpo"] == "reescrito", "una clave ajena no debería impedir la comparación"
    assert _fm(index)["meta"]["clave_de_otro"] == "NO BORRAR"


# ---------------------------------------------------------------------------
# Frontmatter — se escriben las claves propias y NADA más
# ---------------------------------------------------------------------------

def test_solo_toca_sus_claves_del_frontmatter(cm, monkeypatch):
    """Comparación de dicts COMPLETA, no de las claves que se me ocurran.

    El reloj va FIJO y distinto del de la creación: sin eso, `actualizado_en` coincide con
    el de `ensure_case` por resolución de segundos y el test pasa **por suerte**, sin
    acreditar que el sello se escribe (R1/H-06).
    """
    index = _caso(cm, drive_link="https://drive/x", drive_remote_path="ev:/x")
    cm.register_expediente("EV-227-TEST", "648", "expedientes_judiciales")
    cm.register_drive_ev("EV-227-TEST", "T1", "F1")
    fm_b, _ = _partes(index)
    fm = yaml.safe_load(fm_b.decode("utf-8").split("---", 2)[1])
    fm["bucket_override"] = {"algo": "ajeno"}
    index.write_bytes(("---\n" + yaml.safe_dump(fm, allow_unicode=True) + "---\n").encode()
                      + _partes(index)[1])
    antes = _fm(index)

    # El reloj se fija DESPUES de crear, y a un valor distinto: si se fijara antes, el sello
    # de `ensure_case` y el de `update_meta` serian el mismo y el test pasaria sin acreditar
    # que el sello se escribe. Lo mismo pasa sin fijarlo: `now_iso` tiene resolucion de
    # segundos y las dos llamadas caen en el mismo (medido, R1/H-06).
    monkeypatch.setattr(cm, "now_iso", lambda: "2027-01-01T00:00:00+01:00")
    cm.update_meta("EV-227-TEST", cuantia=42.0)

    despues = _fm(index)
    assert despues["bucket_override"] == {"algo": "ajeno"}
    assert set(despues) == set(antes), "aparecieron o desaparecieron claves superiores"
    for clave in set(antes) - {"meta"}:
        assert despues[clave] == antes[clave], f"cambió la clave superior {clave!r}"
    cambiadas = {k for k in set(antes["meta"]) | set(despues["meta"])
                 if antes["meta"].get(k) != despues["meta"].get(k)}
    assert cambiadas == {"cuantia", "actualizado_en"}, cambiadas


def test_NO_revierte_lo_que_update_pull_state_escribio(cm):
    """El escenario de R1/H-02, que mata el diseño de la rev. 1.

    `update_pull_state` escribe en la lista SUPERIOR y deja el espejo de `meta` como
    estaba. Reutilizar `_fusionar_expedientes` —que aplica el espejo ENCIMA— revertía el
    `element`, en silencio y fuera de la lista blanca.
    """
    _caso(cm)
    cm.register_expediente("EV-227-TEST", "10", "expedientes_judiciales")
    cm.update_pull_state("EV-227-TEST", "10", element="extrajudiciales", last_sync="2026-09-11")
    index = _index(cm, "EV-227-TEST")
    superior_antes = _fm(index)["sudespacho_expedientes"]
    assert superior_antes[0]["element"] == "extrajudiciales", "la premisa del test se cayó"

    # El espejo se captura ANTES. La primera versión lo comparaba contra otra lectura de
    # DESPUÉS, así que no conocía el valor previo: una mutación que copiara la lista
    # superior al espejo —un cambio fuera de la lista blanca— dejaba el test verde
    # (R2/H2-05.1, medido con los 213 tests del módulo en verde).
    espejo_antes = _fm(index)["meta"]["sudespacho_expedientes"]
    assert espejo_antes[0]["element"] == "expedientes_judiciales", (
        "la premisa del test se cayó: el espejo tenía que estar RANCIO")

    cm.update_meta("EV-227-TEST", cuantia=11.0)

    fm = _fm(index)
    assert fm["sudespacho_expedientes"] == superior_antes, "revirtió la lista superior"
    assert fm["meta"]["sudespacho_expedientes"] == espejo_antes, (
        "tocó el espejo de `meta`, que no está en la lista blanca")
    assert fm["sudespacho_expedientes"][0]["last_sync"] == "2026-09-11"


def test_referencia_crm_llega_a_sus_DOS_hogares(cm):
    index = _caso(cm)

    cm.update_meta("EV-227-TEST", referencia_crm="BaRR3 - X (W-0) - Y")

    fm = _fm(index)
    assert fm["meta"]["referencia_crm"] == "BaRR3 - X (W-0) - Y"
    assert fm["referencia_crm"] == "BaRR3 - X (W-0) - Y", "el hogar superior se quedó atrás"


def test_los_hogares_superiores_estan_todos_enumerados(cm):
    """El guard de la enumeración: si `_frontmatter_del_indice` gana un hogar nuevo para un
    campo de la lista blanca y nadie lo enumera, esto se pone rojo."""
    meta = cm.CaseMeta(case_id="X", titulo="T")
    superiores = set(cm._frontmatter_del_indice(meta, [])) - {"meta"}
    hogares = superiores & cm.CAMPOS_ACTUALIZABLES
    assert hogares == set(cm._HOGARES_SUPERIORES), (
        f"campos de la lista blanca con hogar superior: {sorted(hogares)}; "
        f"enumerados: {sorted(cm._HOGARES_SUPERIORES)}")


# ---------------------------------------------------------------------------
# Contrato de entrada
# ---------------------------------------------------------------------------

def test_un_campo_fuera_de_la_lista_blanca_se_rechaza_SIN_ESCRIBIR(cm):
    index = _caso(cm)
    antes = _sha(index)

    with pytest.raises(ValueError) as exc:
        cm.update_meta("EV-227-TEST", direccion="Calle Falsa 1")

    assert "direccion" in str(exc.value)
    assert "ensure_case" in str(exc.value), "el error tiene que decir cuál ES su hogar"
    assert _sha(index) == antes, "escribió antes de validar"


def test_llamar_sin_campos_es_un_error_del_llamante(cm):
    index = _caso(cm)
    antes = _sha(index)
    with pytest.raises(ValueError):
        cm.update_meta("EV-227-TEST")
    assert _sha(index) == antes


def test_una_clave_con_None_SE_ESCRIBE_y_una_ausente_no_se_toca(cm):
    """Las dos mitades de R2/H2-06: «el flag no vino» y «el flag vino con cero» son cosas
    distintas, y un default no es una orden de escribir."""
    index = _caso(cm)
    cm.update_meta("EV-227-TEST", cuantia=73140.5)

    cm.update_meta("EV-227-TEST", referencia_crm="R")       # sin `cuantia`
    assert _fm(index)["meta"]["cuantia"] == 73140.5, "una clave ausente pisó el valor"

    cm.update_meta("EV-227-TEST", cuantia=None)             # `None` SÍ se escribe
    assert _fm(index)["meta"]["cuantia"] is None


def test_un_caso_que_no_existe_levanta(cm):
    with pytest.raises(FileNotFoundError):
        cm.update_meta("EV-227-NO-EXISTE", cuantia=1.0)


# ---------------------------------------------------------------------------
# Idempotencia
# ---------------------------------------------------------------------------

def test_dos_llamadas_iguales_dejan_el_fichero_IDENTICO(cm, monkeypatch):
    """Con el reloj FIJO, porque `now_iso` tiene resolución de segundos y dos llamadas
    seguidas coinciden **por suerte** (R1/H-06).

    Y el aserto no se queda en la idempotencia: compara la **primera** salida contra lo que
    el generador produce. Sin eso, un generador que metiera `actualizado_en` en el cuerpo
    pasaría este test con el texto indebido dentro, porque la segunda pasada ya no sería
    canónica y se conservaría entera.
    """
    monkeypatch.setattr(cm, "now_iso", lambda: "2026-09-11T00:00:00+02:00")
    index = _caso(cm)

    cm.update_meta("EV-227-TEST", cuantia=73140.5)
    primera = index.read_bytes()
    cm.update_meta("EV-227-TEST", cuantia=73140.5)

    assert index.read_bytes() == primera, "la segunda pasada cambió el fichero"


def test_al_reescribir_SOLO_cambia_lo_que_renderiza_el_campo(cm):
    """El teorema del §2.1, con un oráculo que NO es el generador.

    Comparar el cuerpo escrito contra `_cuerpo_del_indice` es **tautológico**: un generador
    que metiera texto de más se validaría a sí mismo. Medido — un mutante que añade
    `<!-- actualizado_en -->` al cuerpo sobrevivía a esa comparación **y** al test de
    idempotencia, porque las dos pasadas lo producen igual.

    El oráculo bueno es el cuerpo **anterior**: la única línea que puede cambiar es la que
    renderiza el campo que se escribió.
    """
    index = _caso(cm)
    antes = _partes(index)[1].decode("utf-8").splitlines()

    cm.update_meta("EV-227-TEST", cuantia=73140.5)

    despues = _partes(index)[1].decode("utf-8").splitlines()
    # Comparación SECUENCIAL, no por pertenencia: el delta por `in` ignora orden y
    # multiplicidad, y un mutante que borrara una línea en blanco repetida lo pasaba con
    # los 213 tests en verde (R2/H2-05.2). Lo que se exige es que la secuencia entera sea
    # la anterior con esa única línea sustituida.
    esperado = ["- Cuantía: 73140.5" if l == "- Cuantía: _(pendiente)_" else l for l in antes]
    assert despues == esperado, (
        "el cuerpo no es el de antes con la línea de la cuantía sustituida")
    assert antes != esperado, "la premisa se cayó: la línea de cuantía no estaba"


# ---------------------------------------------------------------------------
# `R2/H2-01` y `R2/H2-02` — la frontera, que era una heurística disfrazada
# ---------------------------------------------------------------------------

def test_un_frontmatter_VACIO_no_se_traga_el_cuerpo(cm):
    """El ALTO de la R2, con el fichero exacto que lo reprodujo.

    La primera versión compartía el regex de `read_md`. Ante `---\\n---\\n` ese patrón **no
    puede** casar el cierre inmediato —necesita un salto entre apertura y cierre que no sea
    el mismo— y **salta al siguiente `---` del fichero**: una nota que estaba en el cuerpo
    entraba como YAML y desaparecía al serializar. Medido, con la nota destruida.
    """
    index = _caso(cm)
    entrada = (b"---\n"
               b"---\n"
               b"meta: {case_id: EV-227-TEST, titulo: T}\n"
               b"# NOTA DEL LETRADO NO BORRAR\n"
               b"---\n"
               b"Texto libre\n")
    index.write_bytes(entrada)

    informe = cm.update_meta("EV-227-TEST", cuantia=42.0)

    assert index.read_bytes() == entrada, "el fichero cambió: la nota estaba en el cuerpo"
    assert informe["cuerpo"] == "sin tocar", informe
    assert b"NOTA DEL LETRADO NO BORRAR" in index.read_bytes()


def test_los_blancos_que_hay_justo_tras_el_cierre_son_del_CUERPO(cm):
    """`R2/H2-02`: el `\\s*` del regex se los comía y la cabecera nueva los sustituía."""
    index = _caso(cm)
    fm_b, _ = _partes(index)
    entrada = fm_b + b"\n  \nNOTA DEL LETRADO\n"
    index.write_bytes(entrada)

    informe = cm.update_meta("EV-227-TEST", cuantia=1.0)

    assert informe["cuerpo"] == "conservado"
    assert _partes(index)[1] == b"\n  \nNOTA DEL LETRADO\n", (
        "se comió los blancos que había justo detrás del cierre")


def test_un_frontmatter_sin_cerrar_no_se_escribe(cm):
    index = _caso(cm)
    index.write_bytes(b"---\nmeta:\n  case_id: X\n\nsin cierre\n")
    antes = _sha(index)

    informe = cm.update_meta("EV-227-TEST", cuantia=1.0)

    assert informe["cuerpo"] == "sin tocar"
    assert _sha(index) == antes
