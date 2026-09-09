"""Regresión sobre el corpus real de W-02VEKE (fixtures anonimizados).

Se usa **W-02VEKE** y no el piloto W-02MA0R del spec §11.3 porque el piloto **no tiene
sala de máquina corrida** (spec §2.4: «en el piloto no se puede correr todavía») y por
tanto no ejercita el selector, que es media pieza. W-02VEKE tiene 76 documentos del CRM,
sala de máquina corrida el 2026-09-08 y variedad real de `metodo`.

**El reparto 9/5/15/12/29 del piloto sigue SIN VALIDAR** y se declara así: este fixture no
lo sustituye. Y si los fixtures no están generados, estos tests **se saltan con su
motivo** — la cobertura queda ausente y declarada, nunca fingida. Los genera
`scratch/fixtures_w02veke.py`, que necesita el Drive montado.

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

pytestmark = pytest.mark.skipif(
    not (FIX / "w02veke_cobertura.json").is_file(),
    reason="fixtures del corpus no generados (hace falta el Drive montado): "
           "correr scratch/fixtures_w02veke.py. La regresión queda SIN VERIFICAR")


@pytest.fixture()
def corpus():
    oc = json.loads((FIX / "w02veke_ocurrencias.json").read_text(encoding="utf-8"))
    cob = json.loads((FIX / "w02veke_cobertura.json").read_text(encoding="utf-8"))
    return oc, cob


def test_CONTROL_el_corpus_trae_lo_que_esta_pieza_debe_cubrir(corpus):
    """Sin este control, los dos de abajo pasarían sobre un corpus vacío."""
    oc, cob = corpus
    assert len(oc.get("ocurrencias", {})) >= 50, "el corpus no tiene volumen real"
    assert len(cob) >= 50
    metodos = {f["metodo"] for f in cob}
    assert {"pypdf", "ocr"} <= metodos, f"faltan métodos base: {sorted(metodos)}"
    assert len(metodos) >= 3, f"el corpus no tiene variedad: {sorted(metodos)}"


def test_el_selector_resuelve_TODO_el_corpus_y_con_MAYORIA_resuelta(tmp_path, corpus):
    """Bloquear es una respuesta válida; petar no. Y **la mayoría debe resolverse**: un
    selector que bloquea todo pasaría el primer aserto y sería inútil — es el test que la
    rev. 1 tenía y que la R1 señaló como aprobable con todos los métodos inutilizables.
    """
    _, cob = corpus
    resueltos = bloqueados = 0
    for fila in cobertura_desde_dicts(cob):
        e = artefacto.elegir(tmp_path, artefacto.Cobertura(),
                             raw_rel=f"00_Input/{fila.rel_path}",
                             raw_sha256=fila.sha256 or "",
                             sin_cobertura_ok=True)
        assert e.bloqueo or e.clase, f"ni elección ni bloqueo para {fila.slug}"
        resueltos += not e.bloqueo
        bloqueados += bool(e.bloqueo)
    assert resueltos > bloqueados, (
        f"el selector bloqueó más de lo que resolvió ({bloqueados} vs {resueltos}): "
        f"pasaría el test sin servir para nada")


def test_el_universo_del_corpus_separa_los_tres_conjuntos(corpus):
    oc, _ = corpus
    reg = RegistroOcurrencias.__new__(RegistroOcurrencias)
    reg.ocurrencias = oc["ocurrencias"]
    exp = next(iter(oc["ocurrencias"].values()))["expediente_id"]
    c = universo.leer("CASO", exp, registro=reg,
                      pull_state={"documents_total_crm": None, "doc_ids": []})
    assert len(c.listadas) >= 50
    assert len(c.materializadas) <= len(c.listadas)
    assert set(c.solo_listadas) == set(c.listadas) - set(c.materializadas)


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
