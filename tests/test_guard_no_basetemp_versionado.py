"""Guard: ningun `--basetemp` de pytest entra versionado en el repo.

**Por que existe.** El 2026-09-02, al mergear `origin/main` en la rama de un
cierre, aparecieron **232 ficheros bajo `.mut_tmp/`** en el arbol de `main`:
el `--basetemp` de una corrida de pruebas de mutacion, commiteado por error y
sin entrada en `.gitignore` (entro con el PR #255). Eran fixtures sinteticos
(`W-CANON1`, `W-TEST99`) —verificado contra la blocklist de saneado, 0
coincidencias en los 232—, asi que no hubo fuga; pero la proxima vez el
`basetemp` puede haber corrido sobre un caso real.

**La convencion ya existia y nada la hacia cumplir.** `AGENTS.md` §Codex pide
`--basetemp` **fuera del arbol** desde el 2026-08-01, y dos handoffs repiten la
instruccion. Un `.gitignore` que nombre `.mut_tmp` no basta: la siguiente sesion
elige otro nombre (`.mt`, `.tmp2`, `_bt`). Lo que se puede reconocer no es el
nombre del directorio sino la **firma que pytest deja dentro**.

**Las dos firmas, y por que hacen falta las dos.** pytest crea, bajo el
`basetemp`, un directorio numerado por test (`test_<nombre>0`, `...1`) y un
centinela `test_<nombre>current` que apunta al ultimo. Medido sobre el incidente:
el centinela caza 113 de los 232 y el numerado 119 — **ninguna de las dos sola
los caza todos**, porque el centinela vive en la raiz del basetemp y los ficheros
de datos viven dentro de los numerados. Falsos positivos sobre los 1.359
ficheros trackeados del repo, excluido `.mut_tmp`: **0**, por eso el guard no
necesita eximir a `tests/` (una exencion seria un hueco, no una comodidad).
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: Centinela que pytest deja en la raiz del basetemp: `test_<nombre>current`.
CENTINELA = re.compile(r"^test_.*current$")

#: Directorio numerado por test que pytest crea dentro del basetemp.
NUMERADO = re.compile(r"^test_.+\d+$")


def _trackeados() -> list[str]:
    r = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    return [ln for ln in r.stdout.splitlines() if ln]


def _ofensores(trackeados: list[str]) -> dict[str, list[str]]:
    """Agrupa por directorio raiz los paths con firma de basetemp de pytest."""
    fuera: dict[str, list[str]] = {}
    for p in trackeados:
        for seg in p.split("/"):
            if CENTINELA.match(seg) or NUMERADO.match(seg):
                fuera.setdefault(p.split("/")[0], []).append(p)
                break
    return fuera


def test_no_hay_basetemp_de_pytest_versionado():
    """G — ningun fichero trackeado lleva la firma de un basetemp de pytest.

    Habria cazado el `.mut_tmp/` del PR #255: 232 ficheros de andamio en `main`.
    """
    fuera = _ofensores(_trackeados())
    if fuera:
        detalle = "\n".join(
            f"  {raiz}/ — {len(ps)} fichero(s), p. ej. {ps[0]}"
            for raiz, ps in sorted(fuera.items()))
        raise AssertionError(
            "Hay un `--basetemp` de pytest versionado en el repo:\n"
            f"{detalle}\n\n"
            "Retiralo del indice (`git rm -r --cached <raiz>`), anadelo a "
            "`.gitignore` y corre pytest con `--basetemp` FUERA del arbol, como "
            "pide `AGENTS.md`. Si el basetemp corrio sobre un caso real, revisa "
            "antes `docs/SEGURIDAD_DATOS.md`: puede llevar PII.")


def test_las_dos_firmas_reconocen_lo_que_dejo_pytest():
    """Las dos firmas del guard no son decorativas: cada una caza lo que la otra no.

    Sin este test, un cambio que dejara solo una de las dos regex seguiria en
    verde sobre un repo limpio, y el guard quedaria medio ciego sin avisar.
    """
    raiz_basetemp = "_bt/test_algo_que_falla0/00_Input/_caso.md"
    centinela = "_bt/test_algo_que_fallacurrent"

    assert _ofensores([centinela]), "el centinela `*current` debe disparar"
    assert _ofensores([raiz_basetemp]), "el directorio numerado debe disparar"

    # Y ninguna de las dos dispara sobre nombres legitimos del repo.
    limpios = [
        "tests/test_guard_no_basetemp_versionado.py",
        "tests/fixtures/test_data/documento.pdf",
        "core/repository_checkout.py",
        "docs/bitacora/2026.md",
    ]
    assert not _ofensores(limpios), f"falso positivo: {_ofensores(limpios)}"
