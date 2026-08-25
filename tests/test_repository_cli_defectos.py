"""Task 6 de la Fase 0 — los defectos del frontal, reproducidos. **Aquí no se arregla ninguno.**

Siete y no ocho: el octavo (`_integrar_bandeja` devolvía `(0,0)` con un `lsjson` ilegible
y el checkin liberaba el lock) lo cerró el PR #160, y su caracterización **verde** vive
en `tests/test_repository_cli_checkin.py`.

Cada test lleva `xfail(strict=True, raises=AssertionError)`. Eso obliga a una disciplina
que no es opcional: **las precondiciones del montaje lanzan `RuntimeError`**, no
`assert`. Si una precondición usara `assert`, el `xfail` se daría por satisfecho con ella
y el test pasaría a verde sin haber probado nunca el defecto — un `xfail` que no
demuestra nada es peor que no tenerlo.

Si alguno de estos `xfail` deja de fallar (`XPASS`), **para y repórtalo**: significa que
el defecto se arregló o que nunca existió, y hay que corregir el recuento del §12 de la
SPEC, que es donde vive.

    python -m pytest tests/test_repository_cli_defectos.py -q -rxX

Esperado: **6 xfailed, 0 xpassed**. Eran siete hasta el 2026-08-25, cuando
A-2c se arregló junto con `MEJORAS #93-B` (ver la nota en su sitio).
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pytest

from tests._dobles import EjecutorActor, FakeRclone

CASO_MD_CUERPO = "# Caso W-TEST99\n\nDatos canónicos que NO se deben perder.\n"
CASE_ID = "BaRS9 - Prueba - (W-TEST99) - Vuelta"
LOG_PREVIO = b'{"event":"upload_manual"}\n'
NONCE_A = "aaaaaaaaaaaaaaaa"
NONCE_B = "bbbbbbbbbbbbbbbb"


# ---------------------------------------------------------------------------
# Montaje
# ---------------------------------------------------------------------------

def caso_md(estado: str = "disponible", **lock) -> bytes:
    from core.utils import build_frontmatter
    meta = {"id_go": "W-TEST99", "tipo_caso": "VUELTA", "ciudad": "Barcelona",
            "estado_repositorio": estado}
    meta.update(lock)
    return (build_frontmatter({"meta": meta}) + "\n" + CASO_MD_CUERPO).encode("utf-8")


def meta_de(data: bytes, tmp_path: Path) -> dict:
    from core.utils import read_md
    p = tmp_path / "_leido.md"
    p.write_bytes(data)
    fm, _ = read_md(p)
    return (fm or {}).get("meta") or {}


def montar_local(tmp_path: Path, contenido: dict[str, bytes], *,
                 base: dict[str, bytes], extra_manifest: dict | None = None,
                 nombre: str = "local") -> Path:
    raiz = tmp_path / nombre
    raiz.mkdir(parents=True, exist_ok=True)
    for rel, data in contenido.items():
        p = raiz / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    inv = {rel: {"hash": hashlib.md5(d).hexdigest(), "size": len(d)}
           for rel, d in base.items()}
    manifest = {"generado": "2026-07-29T10:00:00Z", "n_ficheros": len(inv),
                "inventario": inv}
    manifest.update(extra_manifest or {})
    (raiz / "MANIFEST_CHECKOUT.json").write_text(json.dumps(manifest), encoding="utf-8")
    return raiz


@pytest.fixture
def cli(tmp_path):
    from scripts import repository_cli
    (tmp_path / "work").mkdir(exist_ok=True)
    return repository_cli


def _entorno(cli, ejecutor, tmp_path, *, sub="work", nonce="n0nc3n0nc3n0nc31",
             usuario="tester"):
    from tests._dobles import entorno_de_prueba
    d = tmp_path / sub
    d.mkdir(parents=True, exist_ok=True)
    return entorno_de_prueba(cli, ejecutor, work_dir=d, nonce=nonce, usuario=usuario)


def args_checkout(local: Path, **kw) -> argparse.Namespace:
    base = dict(case_id=CASE_ID, local=str(local), remote_path="", folder_id=None,
                remote="r", team_drive="T", user="tester", dry_run=False, notas=None)
    base.update(kw)
    return argparse.Namespace(**base)


def args_checkin(local: Path, **kw) -> argparse.Namespace:
    base = dict(case_id=CASE_ID, local=str(local), remote_path="", folder_id=None,
                remote="r", team_drive="T", user="tester", dry_run=False,
                wcode="W-TEST99", yes=True)
    base.update(kw)
    return argparse.Namespace(**base)


def _subs(fake) -> list[str]:
    return [c[1] for c in fake.cmds]


def eventos(drive: dict[str, bytes], event: str) -> list[dict]:
    texto = drive["00_Input/_intake_log.jsonl"].decode("utf-8", errors="replace")
    todos = [json.loads(ln) for ln in texto.splitlines()
             if ln.strip() and ln.lstrip().startswith("{")]
    return [e for e in todos if e.get("event") == event]


def liberado(drive: dict[str, bytes], tmp_path: Path) -> bool:
    return "ultimo_checkin_timestamp" in meta_de(drive["00_Input/_caso.md"], tmp_path)


# ---------------------------------------------------------------------------
# A-1 · los dos defectos de CARRERA DE LOCK
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="A-1: el write-then-verify no impide dos titulares — A relee "
                          "su propio nonce porque su push pisó el de B")
def test_defecto_doble_titular(cli, tmp_path):
    """Dos checkouts concurrentes acaban AMBOS creyéndose titulares.

    Interleaving, con el hook armado en la operación 1 de A (su pull del CP0) y
    disparando **después** de ella, que es la mitad del hallazgo: si disparase antes, B
    escribiría `prestado`, A lo leería y abortaría bien — el defecto no se reproduce.

    `cmd_checkout` es monolítico (no se puede pausar a B tras su propio CP0), así que el
    hook ejecuta el **flujo completo** de B. Luego A sigue: pisa el lock de B con el
    suyo, espera, relee y encuentra **su** nonce, así que se cree ganador y copia.
    """
    drive = {"00_Input/_caso.md": caso_md("disponible"), "00_Input/doc.pdf": b"contenido"}
    if meta_de(drive["00_Input/_caso.md"], tmp_path)["estado_repositorio"] != "disponible":
        raise RuntimeError("precondición: el caso debe partir de `disponible`")

    fake = FakeRclone(drive, raiz_local=tmp_path)
    entorno_a = _entorno(cli, EjecutorActor(fake, "A"), tmp_path, sub="work_a",
                         nonce=NONCE_A, usuario="A")
    entorno_b = _entorno(cli, EjecutorActor(fake, "B"), tmp_path, sub="work_b",
                         nonce=NONCE_B, usuario="B")
    rc_b: list[int] = []

    fake.armar(1, lambda n, cmd, d: rc_b.append(
        cli.cmd_checkout(args_checkout(tmp_path / "local_b", user="B"),
                         entorno=entorno_b)))

    rc_a = cli.cmd_checkout(args_checkout(tmp_path / "local_a", user="A"),
                            entorno=entorno_a)

    # --- precondiciones: sin este interleaving el test no probaría nada.
    if rc_b != [0]:
        raise RuntimeError(f"precondición: B debía completar su checkout, dio {rc_b}")
    actores = [a for a, _ in fake.traza_actores]
    if actores[0] != "A":
        raise RuntimeError("precondición: la primera operación tiene que ser el CP0 de A")
    if "B" not in actores:
        raise RuntimeError("precondición: el hook no ejecutó el flujo de B")
    ultimo_b = max(i for i, a in enumerate(actores) if a == "B")
    if "A" not in actores[ultimo_b + 1:]:
        raise RuntimeError("precondición: A no continuó tras B; no hay entrelazado")

    # --- el aserto normativo, y es el único `assert` del test.
    assert not (rc_a == 0 and rc_b[0] == 0), (
        "dos titulares simultáneos: A y B completaron el checkout del mismo caso. "
        f"lock final = {meta_de(drive['00_Input/_caso.md'], tmp_path).get('checkout_user')!r}"
    )


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="A-1: el rollback del checkout cancela el lock sin comprobar "
                          "que siga siendo el propio (falta un guard LOCK_NOT_MINE)")
def test_defecto_rollback_cancela_un_lock_ajeno(cli, tmp_path):
    """A revierte y deja `disponible` un lock que ya era de B.

    El hook instala el lock de B **después** de que A verifique el suyo (operación 3, la
    relectura del nonce) y **antes** de que el `copy` de A falle. A entra entonces en su
    rollback y hace `aplicar_lock_cancelado` + push sobre lo que hay, que ya no es suyo.

    **Desviación consciente del enunciado del plan**, que pide demostrar que «B leyó
    `disponible` antes»: en este entrelazado eso es imposible, porque cuando el hook
    dispara A ya escribió `prestado`, así que un B que leyera de verdad vería `prestado`
    y no entraría. La causalidad que sí se puede establecer —y la que se establece como
    precondición— es la otra mitad: A verificó su propio nonce, el lock pasó a ser de B,
    y el push del rollback de A lo pisó. La frase del plan describe el defecto de
    *doble titular* (el test de arriba), donde B sí lee `disponible`.
    """
    drive = {"00_Input/_caso.md": caso_md("disponible"), "00_Input/doc.pdf": b"contenido"}
    fake = FakeRclone(drive, raiz_local=tmp_path,
                      resultados={("copy", 1): (1, "", "boom")})
    visto: dict[str, object] = {}

    def instalar_lock_de_b(n, cmd, d):
        visto["antes"] = meta_de(d.leer("00_Input/_caso.md"), tmp_path)
        d.escribir("00_Input/_caso.md",
                   caso_md("prestado", checkout_user="B", checkout_nonce=NONCE_B))

    fake.armar(3, instalar_lock_de_b)     # 1 pull CP0 · 2 push lock · 3 relectura

    rc_a = cli.cmd_checkout(args_checkout(tmp_path / "local_a", user="A"),
                            entorno=_entorno(cli, fake, tmp_path, nonce=NONCE_A,
                                             usuario="A"))

    # --- precondiciones de causalidad.
    if visto.get("antes", {}).get("checkout_nonce") != NONCE_A:
        raise RuntimeError("precondición: A debía haber verificado su PROPIO nonce "
                           f"antes de que el hook entrara (vio {visto.get('antes')})")
    if rc_a == 0:
        raise RuntimeError("precondición: el `copy` de A tenía que fallar para que "
                           "entrase el rollback")

    # --- aserto normativo único.
    meta = meta_de(drive["00_Input/_caso.md"], tmp_path)
    assert meta.get("checkout_user") == "B", (
        "el rollback de A pisó el lock de B: el caso quedó "
        f"{meta.get('estado_repositorio')!r} con checkout_user="
        f"{meta.get('checkout_user')!r}. A debería haber abortado con LOCK_NOT_MINE.")


# ---------------------------------------------------------------------------
# A-2 · los tres defectos del ORDEN Y EL CIERRE del checkin
# ---------------------------------------------------------------------------

def _montar_checkin_con_bandeja(tmp_path):
    """Caso verde con algo que subir y un fichero en la bandeja."""
    bandeja = "_pendiente_checkin/pipeline/01_Procesado/informe.md"
    drive = {"00_Input/_caso.md": caso_md("prestado", checkout_user="tester",
                                          checkout_nonce=NONCE_A),
             "00_Input/_intake_log.jsonl": LOG_PREVIO,
             "00_Input/doc.pdf": b"BASE",
             bandeja: b"escrito durante el prestamo"}
    local = montar_local(tmp_path, {"00_Input/doc.pdf": b"LOCAL"},
                         base={"00_Input/doc.pdf": b"BASE"})
    return drive, local, bandeja


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="A-2: la bandeja se integra al FINAL, después de verificar y "
                          "de registrar el evento; lo integrado nunca se verifica")
def test_defecto_orden_del_checkin(cli, tmp_path):
    """Se exige integrar bandeja → verificar → evento → liberar. Hoy va al revés.

    Importa porque lo que entra por la bandeja **no pasa por el `check`**: se mueve al
    árbol del caso después de que la verificación por hash ya terminó, así que el
    checkin certifica un contenido que no es el que queda en el Drive.
    """
    drive, local, _ = _montar_checkin_con_bandeja(tmp_path)
    fake = FakeRclone(drive, raiz_local=tmp_path)

    rc_ = cli.cmd_checkin(args_checkin(local), entorno=_entorno(cli, fake, tmp_path))

    subs = _subs(fake)
    if rc_ != 0:
        raise RuntimeError(f"precondición: el camino tenía que salir verde, dio {rc_}")
    if "check" not in subs:
        raise RuntimeError("precondición: hacía falta algo que subir para que haya check")
    lsjsons = [i for i, s in enumerate(subs) if s == "lsjson"]
    if len(lsjsons) < 2:
        raise RuntimeError(f"precondición: faltó el lsjson de la bandeja: {subs}")

    i_bandeja, i_check = lsjsons[1], subs.index("check")
    assert i_bandeja < i_check, (
        f"la bandeja se integra en la posición {i_bandeja} y la verificación en la "
        f"{i_check}: lo que entra por la bandeja se sube sin verificar. Traza: {subs}")


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="A-2: un `moveto` fallido al integrar la bandeja solo imprime "
                          "un aviso y el checkin libera el lock igual")
def test_defecto_moveto_de_bandeja_fallido_libera_el_lock(cli, tmp_path):
    """Queda contenido sin integrar y el caso se marca `disponible` de todas formas.

    El fallo se guioniza con `resultados` y **no** con `fallos_sub`: el rc real de un
    `moveto` de origen ausente es **1**, y el canal heredado lo aplanaría a 3.
    Producción solo mira `!= 0`, así que el `xfail` saldría igual — pero un doble que
    miente sobre el código de salida contamina la Fase 2.
    """
    drive, local, bandeja = _montar_checkin_con_bandeja(tmp_path)
    # Sin borrados en el plan, el único `moveto` es el de la bandeja.
    fake = FakeRclone(drive, raiz_local=tmp_path,
                      resultados={("moveto", 1): (1, "", "source not found")})

    rc_ = cli.cmd_checkin(args_checkin(local), entorno=_entorno(cli, fake, tmp_path))

    if "moveto" not in _subs(fake):
        raise RuntimeError("precondición: no se emitió el moveto de la bandeja")
    if bandeja not in drive:
        raise RuntimeError("precondición: el moveto guionizado no debía mover nada")

    assert not liberado(drive, tmp_path), (
        f"quedó contenido sin integrar ({bandeja}) y el lock se liberó igual; "
        f"rc={rc_}, estado="
        f"{meta_de(drive['00_Input/_caso.md'], tmp_path)['estado_repositorio']!r}")


# A-2c — RETIRADO el 2026-08-25: el defecto está ARREGLADO.
#
# `test_defecto_checkin_reentrante_duplica_el_evento` vivía aquí. `cmd_checkin` valida
# ahora la transición ANTES de registrar el evento, así que un checkin reentrante ya no
# duplica el `case_checkin` ni revienta con un traceback (`MEJORAS #93-B`).
#
# Su caracterización **verde** vive en `tests/test_checkin_reentrante.py`, que es el
# mismo trato que recibió el octavo defecto cuando lo cerró el PR #160: el escenario no
# se pierde, cambia de fichero porque cambia de naturaleza.


# ---------------------------------------------------------------------------
# B0-2 · los dos defectos del LOG CANÓNICO
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="B0-2: `_append_evento_drive` reescribe el log entero desde "
                          "las líneas decodificadas, así que no es append-only en bytes")
def test_defecto_el_log_canonico_se_reescribe_y_se_corrompe(cli, tmp_path):
    """El log dice ser append-only y en realidad se regenera, perdiendo bytes.

    Se siembra un log con dos cosas que un fichero real puede tener y que el ciclo
    pull→decodificar→splitlines→join destruye: una **línea en blanco** intermedia y un
    byte **no UTF-8** (`\\xff`, que `errors="replace"` convierte en U+FFFD). Tampoco
    tiene salto final. Para un registro de custodia esto importa: los bytes que se
    firmaron no son los que quedan.
    """
    log_original = b'{"event":"a"}\n\n{"event":"\xff"}'
    drive = {"00_Input/_caso.md": caso_md("prestado", checkout_user="tester",
                                          checkout_nonce=NONCE_A),
             "00_Input/_intake_log.jsonl": log_original,
             "00_Input/doc.pdf": b"BASE"}
    local = montar_local(tmp_path, {"00_Input/doc.pdf": b"LOCAL"},
                         base={"00_Input/doc.pdf": b"BASE"})
    fake = FakeRclone(drive, raiz_local=tmp_path)

    rc_ = cli.cmd_checkin(args_checkin(local), entorno=_entorno(cli, fake, tmp_path))

    if rc_ != 0:
        raise RuntimeError(f"precondición: el checkin debía llegar al append (rc={rc_})")
    if drive["00_Input/_intake_log.jsonl"] == log_original:
        raise RuntimeError("precondición: el log no se tocó; no se llegó a escribirlo")

    assert drive["00_Input/_intake_log.jsonl"].startswith(log_original), (
        "los bytes preexistentes del log NO sobrevivieron intactos.\n"
        f"  antes:   {log_original!r}\n"
        f"  después: {drive['00_Input/_intake_log.jsonl'][:len(log_original) + 20]!r}")


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="B0-2: `_leer_manifest` solo devuelve data['inventario'], así "
                          "que el baseline del log del MANIFEST se ignora por completo")
def test_defecto_el_baseline_del_log_no_se_usa(cli, tmp_path):
    """El `MANIFEST_CHECKOUT.json` puede llevar baseline del log y nadie lo lee.

    **Emplazamiento cerrado:** los campos viven en el `MANIFEST_CHECKOUT.json`, que ya se
    escribe en local **y** se sube al Drive, no en el `work_dir` temporal (que no se
    comunica al checkin y muere con el proceso: eso cerraría el aserto, no el defecto).

    El manifest se **siembra** ya con `log_hash`/`log_lineas`, como precondición
    verificada: la Fase 0 no puede hacer que `cmd_checkout` los emita —sería cambio de
    comportamiento, prohibido— así que exigir primero que los genere dejaría el `xfail`
    satisfecho por el primer aserto, sin demostrar ni recuperación ni uso.

    Fuera de alcance: qué hacer con un manifest legacy **sin** baseline (bloquear o
    admitir compatibilidad) se decide en la Fase 2.
    """
    log_drive = b'{"event":"a"}\n{"event":"b"}\n{"event":"MODIFICADO POR OTRO"}\n'
    drive = {"00_Input/_caso.md": caso_md("prestado", checkout_user="tester",
                                          checkout_nonce=NONCE_A),
             "00_Input/_intake_log.jsonl": log_drive,
             "00_Input/doc.pdf": b"BASE"}
    # Baseline que NO cuadra con el log del Drive: 2 líneas y otro hash.
    local = montar_local(
        tmp_path, {"00_Input/doc.pdf": b"LOCAL"}, base={"00_Input/doc.pdf": b"BASE"},
        extra_manifest={"log_hash": hashlib.md5(b'{"event":"a"}\n{"event":"b"}\n').hexdigest(),
                        "log_lineas": 2})

    manifest = json.loads((local / "MANIFEST_CHECKOUT.json").read_text(encoding="utf-8"))
    if "log_hash" not in manifest or manifest.get("log_lineas") != 2:
        raise RuntimeError("precondición: el manifest sembrado no lleva el baseline del log")
    if manifest["log_hash"] == hashlib.md5(log_drive).hexdigest():
        raise RuntimeError("precondición: el baseline tenía que divergir del log del Drive")

    fake = FakeRclone(drive, raiz_local=tmp_path)
    rc_ = cli.cmd_checkin(args_checkin(local), entorno=_entorno(cli, fake, tmp_path))

    assert not liberado(drive, tmp_path), (
        f"el log del Drive divergía del baseline del MANIFEST (3 líneas frente a 2) y el "
        f"checkin cerró el ciclo sin enterarse: rc={rc_}, lock liberado. El baseline se "
        f"escribió, se subió y nadie lo leyó.")
