"""Sostener el mutex del caso desde un CLI: un solo sitio (MEJORAS #126, fila #17).

Diseño: `docs/superpowers/specs/2026-09-05-mutex-en-los-entrypoints-de-intake-design.md`
(rev. 2). Hasta el 2026-09-05 había tres copias casi iguales de «adquirir el mutex desde un
entrypoint» (`abrir_caso`, `sala_maquina`, `migrar_layout_intake`) y cinco subcomandos que
escribían en el árbol del caso sin pedirlo (`export_label_emails`, `atomize_emails`,
`sync_sudespacho pull|intake_judicial|sync_all`). La regla la sostenía a mano quien ejecutaba.

**La frontera:** todo entrypoint que escriba bajo el árbol de un caso con W-code sostiene el
mutex de ese caso desde ANTES de la primera escritura hasta la última, y aborta limpio (código 2,
cero bytes) si otro proceso lo tiene. Sin W-code no hay namespace: se avisa y se sigue
(trinquete E2 de `tests/test_entrypoints_mutex.py`).

**Lo que el mutex NO da:** exclusión, no cancelación. `case_mutex` no preempta código a mitad;
si el lease se pierde durante una escritura, el motor la termina y la pérdida se conoce al salir.

Vive en `scripts/` y no en `core/` a propósito: `core/` EXIGE el mutex y nunca lo adquiere
(guard E5). Usa `mutex_sesion.sostenido` y nunca la primitiva (`case_mutex.tomado`/`adquirir`
están prohibidos en producción fuera de sus capas: `tests/test_escritura_censo.py`).
"""
from __future__ import annotations

import contextlib
from collections.abc import Callable, Iterator
from pathlib import Path

AVISO_SIN_W_CODE = (
    "[aviso] este caso no declara W-code, así que {que} NO va bajo el mutex: otro proceso de "
    "esta máquina podría estar escribiendo el mismo expediente")
AVISO_ALTA = (
    "[aviso] este comando CREA el caso: sin identidad no hay mutex que sostener. La vía canónica "
    "de alta es `abrir_caso`, que sí lo sostiene (MEJORAS #126)")
AVISO_FUERA_DE_CASO = (
    "[aviso] el destino no cae bajo ningún caso del catálogo: no hay mutex que sostener")


class CasoOcupado(RuntimeError):
    """Otro proceso de esta máquina sostiene el mutex del caso: el CLI no arranca y no escribe
    un byte. Cada CLI lo convierte en su código de salida 2."""


class MutexPerdidoEnCli(RuntimeError):
    """El lease se perdió DURANTE el trabajo (lease vencido, reloj movido, lock borrado): puede
    haber trabajo a medio publicar. El mensaje nombra qué artefactos revisar."""


def _leer_id_go(case_dir: Path) -> str | None:
    from core.utils import read_md
    try:
        fm, _ = read_md(case_dir / "00_Input" / "_caso.md")
    except (OSError, ValueError):
        return None
    meta = fm.get("meta") if isinstance(fm, dict) else None
    w = (meta or {}).get("id_go") if isinstance(meta, dict) else None
    w = str(w).strip() if w else ""
    return w or None


def w_code_de(ref_o_case_id: str) -> str | None:
    """`meta.id_go` del `_caso.md` del caso al que resuelve `ref_o_case_id`.

    PRIMERO `resolve_ref` (R1/H-03: un W-code pasado como `--ref` no es un nombre de carpeta y
    `caso_path` no lo encuentra), DESPUÉS `_caso.md`. `None` si el caso no existe o no declara
    `id_go`. Nunca deriva la identidad del nombre de la carpeta.
    """
    from core.casos.case_locator import buscar, resolve_ref
    case_id = resolve_ref(ref_o_case_id)
    case_dir = buscar(case_id)
    if case_dir is None:
        return None
    return _leer_id_go(Path(case_dir))


def w_code_de_ruta(ruta: Path | str) -> str | None:
    """Para `--src/--out` (R1/H-04): si `ruta` cae bajo un caso del catálogo (algún ancestro
    con `00_Input/_caso.md` dentro de `CASOS_ROOT`), su `meta.id_go`; si no, `None`. Un destino
    dentro de un caso es una escritura en ese caso aunque el CLI no lo nombre."""
    from core.config import settings
    try:
        p = Path(ruta).resolve()
        raiz = Path(settings.casos_root).resolve()
    except OSError:
        return None
    try:
        p.relative_to(raiz)
    except ValueError:
        return None
    for cand in (p, *p.parents):
        if cand == raiz:
            break
        if (cand / "00_Input" / "_caso.md").is_file():
            return _leer_id_go(cand)
    return None


@contextlib.contextmanager
def sostener(w_code: str | None, *, avisar: Callable[[str], None], que: str,
             aviso_sin_w_code: str | None = None) -> Iterator[object | None]:
    """Sostiene el mutex de `w_code` durante el bloque.

    - `w_code is None` → `avisar(...)` (el texto canónico, o `aviso_sin_w_code` si el llamador
      sabe POR QUÉ no hay identidad: alta, destino externo) y `yield None`.
    - `CaseBusy` → `CasoOcupado` con el mensaje de la primitiva (quién, desde cuándo).
    - `MutexPerdido` → `MutexPerdidoEnCli`, nombrando `que` como lo que hay que revisar.
    - `ahora_fn=now_iso_utc` SIEMPRE: la primitiva rechaza un instante sin offset (guard E4).
    """
    from core.casos import mutex_sesion
    from core.casos.workspace_model import CaseBusy, CaseRef, MutexPerdido
    from core.utils import now_iso_utc

    if not w_code:
        avisar(aviso_sin_w_code or AVISO_SIN_W_CODE.format(que=que))
        yield None
        return
    try:
        with mutex_sesion.sostenido(CaseRef(w_code=w_code), ahora_fn=now_iso_utc) as sesion:
            yield sesion
    except CaseBusy as exc:
        raise CasoOcupado(f"{exc} — {que} no ha empezado: cero bytes escritos") from exc
    except MutexPerdido as exc:
        raise MutexPerdidoEnCli(
            f"{exc}. El mutex se perdió DURANTE {que}, así que el resultado puede estar a "
            f"medias: revisa lo escrito en esta corrida antes de fiarte, y comprueba si otro "
            f"proceso entró.") from exc
