"""Regresión sobre el corpus real de W-02VEKE (fixtures anonimizados).

Se usa **W-02VEKE** y no el piloto W-02MA0R del spec §11.3 porque el piloto **no tiene
sala de máquina corrida** (spec §2.4: «en el piloto no se puede correr todavía») y por
tanto no ejercita el selector, que es media pieza. W-02VEKE tiene 76 documentos del CRM,
sala de máquina corrida el 2026-09-08 y variedad real de `metodo`.

**El reparto 9/5/15/12/29 del piloto sigue SIN VALIDAR** y se declara así: este fixture no
lo sustituye. Y si los fixtures no están generados, estos tests **se saltan con su
motivo** — la cobertura queda ausente y declarada, nunca fingida. Los genera
`scratch/fixtures_w02veke.py`, que necesita el Drive montado.

**Los fixtures NO se versionan, y esto cambia lo que decía el plan** (su Tarea 7 mandaba
`git add tests/fixtures/procedimiento/`). Al generarlos por primera vez contra el corpus
real —2026-09-09, con el Drive por fin montado— se midió que la redacción por **denylist**
deja pasar **truncamientos**: el control de términos exactos daba 0 supervivientes de 82 y
un control por prefijo encontró **1**, un apellido de la blocklist abreviado en el nombre
de un fichero. Es el mismo defecto que la R1 encontró en mi propio plan (su H-23): el verde
de una denylist es ciego por construcción. Así que van a `.gitignore` y estos tests
**solo corren en una máquina con el Drive montado y los fixtures generados**. En CI y en
cualquier otro clon se saltan, y eso queda dicho aquí en vez de fingido.

Los tres llevan **control positivo**: sin él, «el selector resolvió todo el corpus»
pasaría también con un corpus vacío o con todo bloqueado, que es exactamente el defecto
que la R1 encontró en los tres tests de corpus de la rev. 1.
"""
import json
import pathlib

import pytest

from core.ocurrencias_crm import RegistroOcurrencias
from core.procedimiento import artefacto, universo
from core.sala_maquina import cobertura_desde_dicts

FIX = pathlib.Path(__file__).parent / "fixtures" / "procedimiento"
SM = "01_Procesado/02_Sala de máquina"

pytestmark = pytest.mark.skipif(
    not (FIX / "w02veke_cobertura.json").is_file(),
    reason="fixtures del corpus no generados (hace falta el Drive montado): "
           "correr scratch/fixtures_w02veke.py. La regresión queda SIN VERIFICAR")


@pytest.fixture()
def corpus():
    oc = json.loads((FIX / "w02veke_ocurrencias.json").read_text(encoding="utf-8"))
    cob = json.loads((FIX / "w02veke_cobertura.json").read_text(encoding="utf-8"))
    return oc, cob


def _expediente_mayoritario(oc) -> str:
    """El expediente CRM con más ocurrencias del corpus.

    **No vale `next(iter(...))`, y esto está medido:** W-02VEKE tiene **dos** expedientes
    del CRM enlazados —uno con 5 documentos y otro con 76— y el primero que sale del dict
    es el pequeño. El test de volumen le pedía 50 a una población de 5 y salía rojo
    culpando a `universo.leer`, que estaba filtrando por expediente exactamente como debe.
    """
    conteo: dict[str, int] = {}
    for v in oc["ocurrencias"].values():
        conteo[v["expediente_id"]] = conteo.get(v["expediente_id"], 0) + 1
    return max(conteo, key=lambda k: conteo[k])


def test_CONTROL_el_corpus_trae_lo_que_esta_pieza_debe_cubrir(corpus):
    """Sin este control, los dos de abajo pasarían sobre un corpus vacío.

    **El control mide LA MISMA población que el test, no el fichero entero.** Hasta el
    2026-09-09 afirmaba `len(ocurrencias) >= 50` sobre los dos expedientes juntos (81) y
    daba verde, mientras el test de universo medía uno solo (5): un control positivo que
    acredita una población distinta de la que se prueba **no es un control**, es un
    segundo test que da igual.
    """
    oc, cob = corpus
    assert len(oc.get("ocurrencias", {})) >= 50, "el corpus no tiene volumen real"
    exp = _expediente_mayoritario(oc)
    del_exp = [v for v in oc["ocurrencias"].values() if v["expediente_id"] == exp]
    assert len(del_exp) >= 50, (
        f"el expediente mayoritario ({exp}) trae {len(del_exp)} ocurrencias: es la "
        f"población que mide el test de universo, y no tiene volumen real")
    assert len(cob) >= 50
    metodos = {f["metodo"] for f in cob}
    assert {"pypdf", "ocr"} <= metodos, f"faltan métodos base: {sorted(metodos)}"
    assert len(metodos) >= 3, f"el corpus no tiene variedad: {sorted(metodos)}"
    # La rama de grupo de `elegir` solo se ejercita si hay bundles PARTIDOS. Sin este
    # control, el corpus podría quedarse sin ninguno y el test del selector mediría la
    # mitad del selector dando verde.
    padres = {f.get("parent_sha256") for f in cob if f.get("parent_slug")}
    assert len(padres) >= 3, (
        f"el corpus trae {len(padres)} bundle(s) partido(s): no basta para ejercitar la "
        f"rama de grupo del selector")


def test_el_selector_recibe_LA_COBERTURA_del_corpus_y_no_una_vacia(tmp_path, corpus):
    """**El defecto que la R1 encontró en este mismo test** (su H-16), y que es el mismo
    que la ronda anterior había señalado en los tests de corpus de la rev. 1: pasaba
    `artefacto.Cobertura()` **vacía** y `sin_cobertura_ok=True`, así que recorría solo la
    rama de override. La «mayoría resuelta» salía del *fallback*, no del selector, y el
    test seguía verde con los dos sets de métodos inutilizados.

    Ahora se construyen los índices con las filas del fixture, se materializan los
    artefactos que la cobertura declara, y se exige resultado **por clase**.
    """
    _, cob_filas = corpus
    (tmp_path / SM).mkdir(parents=True, exist_ok=True)
    (tmp_path / SM / "_cobertura.json").write_text(json.dumps(cob_filas),
                                                   encoding="utf-8")
    # Los artefactos que la cobertura declara, materializados: sin ellos el selector
    # bloquea con razón y el test volvería a medir el fallback.
    ocr = tmp_path / SM / "01_OCR"
    ocr.mkdir(parents=True, exist_ok=True)
    for f in cob_filas:
        slug = f.get("parent_slug") or f.get("slug")
        if f.get("metodo") in ("ocr", "ofimatica") and slug:
            (ocr / f"{slug}.pdf").write_bytes(b"%PDF-1.4")
    cob = artefacto.cargar(tmp_path)
    assert cob.por_sha or cob.grupos, "los índices salieron vacíos: el test no probaría nada"

    # **La clase ESPERADA por fila, no «la mayoría se resuelve».** Con la mayoría, el
    # mutante que vacía `METODOS_CON_ARTEFACTO` sobrevive: sus 15 filas pasan a bloqueo,
    # las otras 40 siguen en crudo, y 40 > 15 aprueba el test. Lo comprobé ejecutándolo.
    esperado_por_metodo = {
        "pypdf": artefacto.Clase.CRUDO,
        "nativo": artefacto.Clase.CRUDO,
        "vision": artefacto.Clase.CRUDO,
        "sin_soporte": artefacto.Clase.CRUDO,
        "ocr": artefacto.Clase.CONVERTIDO,
        "ofimatica": artefacto.Clase.CONVERTIDO,
    }
    # **Se pregunta por DOCUMENTOS FÍSICOS, no por filas de cobertura** (medido el
    # 2026-09-09 sobre el corpus real). Un bundle partido **no deja fila propia del
    # padre**: sus segmentos llevan el `rel_path` del PDF padre y su **propio** `sha256`.
    # Iterando las filas a pelo, el test llamaba con `(ruta del padre, sha del segmento)`
    # —un par que no existe en ningún disco— y las 14 filas de segmento bloqueaban con
    # toda la razón. El par que sí existe es `(ruta del padre, parent_sha256)`, que es
    # justo por donde `elegir` entra a `cob.grupos`.
    docs = []                        # (rel_path, sha, metodo, estado, etiqueta)
    grupos_vistos: set[str] = set()
    for fila in cobertura_desde_dicts(cob_filas):
        if fila.parent_slug:
            if fila.parent_sha256 in grupos_vistos:
                continue             # un representante por padre, no uno por segmento
            grupos_vistos.add(fila.parent_sha256)
            docs.append((fila.rel_path, fila.parent_sha256, fila.metodo, fila.estado,
                         f"bundle:{fila.parent_slug}"))
        else:
            docs.append((fila.rel_path, fila.sha256 or "", fila.metodo, fila.estado,
                         fila.slug))
    assert grupos_vistos, (
        "el corpus no trae ni un bundle partido: la rama de grupo de `elegir` no se "
        "ejercita y este test estaría midiendo medio selector")

    por_clase: dict[str, int] = {}
    desviaciones: list[str] = []
    for rel_path, sha, metodo, estado, etiqueta in docs:
        # se materializa el crudo para que la elección no dependa de su ausencia
        crudo = tmp_path / "00_Input" / rel_path
        crudo.parent.mkdir(parents=True, exist_ok=True)
        if not crudo.exists():
            crudo.write_bytes(b"x")
        e = artefacto.elegir(tmp_path, cob, raw_rel=f"00_Input/{rel_path}",
                             raw_sha256=sha, sin_cobertura_ok=False)
        clave = "bloqueo" if e.bloqueo else str(e.clase)
        por_clase[clave] = por_clase.get(clave, 0) + 1

        esperada = esperado_por_metodo.get(metodo)
        if esperada is None:                 # `duplicado`, `error`: su propio contrato
            continue
        if estado == "empty" and not str(rel_path).lower().endswith(".pdf"):
            continue                          # imagen sin texto: el original la representa
        if e.bloqueo or e.clase is not esperada:
            desviaciones.append(
                f"{etiqueta} ({metodo}/{estado}): esperaba {esperada}, "
                f"salió {clave} — {e.bloqueo[:70]}")

    assert por_clase, "no se evaluó ni un documento"
    assert not desviaciones, (
        f"{len(desviaciones)} documento(s) del corpus no dieron la clase que su método "
        f"exige (muestra: {desviaciones[:3]})")
    # Y que se ejerciten LAS DOS clases: con una sola, el test volvería a medir un camino.
    assert {"crudo", "convertido"} <= set(por_clase), (
        f"el corpus no ejercitó las dos clases del selector: {por_clase}")


def test_el_universo_del_corpus_separa_los_tres_conjuntos(corpus):
    oc, _ = corpus
    reg = RegistroOcurrencias.__new__(RegistroOcurrencias)
    reg.ocurrencias = oc["ocurrencias"]
    exp = _expediente_mayoritario(oc)
    c = universo.leer("CASO", exp, registro=reg,
                      pull_state={"documents_total_crm": None, "doc_ids": []})
    assert len(c.listadas) >= 50
    assert len(c.materializadas) <= len(c.listadas)
    assert set(c.solo_listadas) == set(c.listadas) - set(c.materializadas)


def test_el_universo_NO_mezcla_los_dos_expedientes_del_caso(corpus):
    """El corpus real trae dos expedientes CRM enlazados, y esa es su gracia: el filtro
    por expediente tiene aquí algo que filtrar. Sin este test, `universo.leer` podría
    devolver los 81 de golpe y el de arriba —que solo pide `>= 50`— lo aprobaría.
    """
    oc, _ = corpus
    reg = RegistroOcurrencias.__new__(RegistroOcurrencias)
    reg.ocurrencias = oc["ocurrencias"]
    exps = {v["expediente_id"] for v in oc["ocurrencias"].values()}
    assert len(exps) >= 2, f"el corpus ya no tiene dos expedientes: {exps}"

    total = 0
    for e in exps:
        c = universo.leer("CASO", e, registro=reg,
                          pull_state={"documents_total_crm": None, "doc_ids": []})
        esperadas = {k.split(":")[-1] for k, v in oc["ocurrencias"].items()
                     if v["expediente_id"] == e}
        assert set(c.listadas) == esperadas, (
            f"expediente {e}: el universo trae {len(c.listadas)} y le tocan "
            f"{len(esperadas)} — está mezclando expedientes")
        total += len(c.listadas)
    assert total == len(oc["ocurrencias"]), (
        "la suma por expediente no cuadra con el corpus: hay ocurrencias que no caen en "
        "ningún expediente, o alguna cae en dos")


def test_los_fixtures_no_llevan_PII_de_la_blocklist(corpus):
    """La comprobación corre contra la blocklist ENTERA, no contra una muestra elegida a
    mano, y **falla si la lista está vacía**: un grep de seis substrings no es prueba de
    anonimización, es el verde de un guard sin su blocklist."""
    import re
    import sys
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    from scripts.precommit_leak_guard import cargar_blocklist

    terminos = cargar_blocklist(pathlib.Path(__file__).resolve().parents[1])
    assert terminos, ("la blocklist está vacía: sin ella este test no comprueba nada y "
                      "no se puede acreditar la anonimización del fixture")
    texto = "".join(p.read_text(encoding="utf-8") for p in FIX.glob("*.json"))
    supervivientes = sorted({t for t in terminos if re.search(re.escape(t), texto, re.I)})
    assert not supervivientes, (
        f"{len(supervivientes)} término(s) de la blocklist sobreviven en los fixtures")
