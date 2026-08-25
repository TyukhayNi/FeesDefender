"""Task 5 de la Fase 0 — **Tabla A**: caracterización de los caminos de FALLO.

La rev. 2 del plan mezclaba caracterización con expectativas normativas y eso hacía la
tabla inasertable. Aquí va **solo la Tabla A**: lo que el frontal hace HOY ante cada
fallo inyectado, en verde y sin cambiar nada. Las expectativas que hoy NO se cumplen
viven como `xfail` en `tests/test_repository_cli_defectos.py` (Task 6).

Cubre en particular **los dos únicos retornos de `run_rclone` que el frontal no
examina** —el `lsjson` del CP1 y el `rmdirs` de la bandeja—, porque un retorno que nadie
mira es exactamente donde un cambio futuro pasa inadvertido.

**Hecho, no intención:** el ROJO del semáforo es **inalcanzable** por orquestación —
`cmd_checkin` retorna en el `if copia_fallo` **antes** de llamar a
`clasificar_semaforo`—. Se fija como hecho al final; la rama roja del helper puro ya la
cubren sus propios tests.

Ningún fallo se arregla aquí. Si una fila no se comporta como dice, es un bug vivo: para
y repórtalo.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pytest

from tests._dobles import FakeRclone

CASO_MD_CUERPO = "# Caso W-TEST99\n\nDatos canónicos que NO se deben perder.\n"
CASE_ID = "BaRS9 - Prueba - (W-TEST99) - Vuelta"
LOG_PREVIO = b'{"event":"upload_manual"}\n'


# ---------------------------------------------------------------------------
# Montaje (helpers locales, como en las Tasks 3-4)
# ---------------------------------------------------------------------------

def caso_md(estado: str = "prestado", **lock) -> bytes:
    from core.utils import build_frontmatter
    meta = {"id_go": "W-TEST99", "tipo_caso": "VUELTA", "ciudad": "Barcelona",
            "estado_repositorio": estado, "checkout_user": "tester",
            "checkout_nonce": "abcdef0123456789"}
    meta.update(lock)
    return (build_frontmatter({"meta": meta}) + "\n" + CASO_MD_CUERPO).encode("utf-8")


def meta_de(data: bytes, tmp_path: Path) -> dict:
    from core.utils import read_md
    p = tmp_path / "_leido.md"
    p.write_bytes(data)
    fm, _ = read_md(p)
    return (fm or {}).get("meta") or {}


def drive_de(contenido: dict[str, bytes], *, estado: str = "prestado") -> dict[str, bytes]:
    drive = {"00_Input/_caso.md": caso_md(estado),
             "00_Input/_intake_log.jsonl": LOG_PREVIO}
    drive.update(contenido)
    return drive


def montar_local(tmp_path: Path, contenido: dict[str, bytes], *,
                 base: dict[str, bytes] | None,
                 manifest_crudo: str | None = None) -> Path:
    """Árbol local + `MANIFEST_CHECKOUT.json`.

    `base=None` no escribe manifest. `manifest_crudo` escribe ese texto literal, para
    poder sembrar un JSON corrupto sin que el helper lo sanee.
    """
    raiz = tmp_path / "local"
    raiz.mkdir(parents=True, exist_ok=True)
    for rel, data in contenido.items():
        p = raiz / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    if manifest_crudo is not None:
        (raiz / "MANIFEST_CHECKOUT.json").write_text(manifest_crudo, encoding="utf-8")
    elif base is not None:
        inv = {rel: {"hash": hashlib.md5(d).hexdigest(), "size": len(d)}
               for rel, d in base.items()}
        (raiz / "MANIFEST_CHECKOUT.json").write_text(
            json.dumps({"generado": "2026-07-29T10:00:00Z",
                        "n_ficheros": len(inv), "inventario": inv}),
            encoding="utf-8")
    return raiz


@pytest.fixture
def cli(tmp_path):
    from scripts import repository_cli
    (tmp_path / "work").mkdir(exist_ok=True)
    return repository_cli


def _entorno(cli, fake, tmp_path):
    from tests._dobles import entorno_de_prueba
    return entorno_de_prueba(cli, fake, work_dir=tmp_path / "work", usuario="tester")


def args_checkin(local: Path, **kw) -> argparse.Namespace:
    base = dict(case_id=CASE_ID, local=str(local), remote_path="", folder_id=None,
                remote="r", team_drive="T", user="tester", dry_run=False,
                wcode="W-TEST99", yes=True)
    base.update(kw)
    return argparse.Namespace(**base)


def _correr(cli, tmp_path, drive, local, *, fake=None, **kw):
    fake = fake if fake is not None else FakeRclone(drive, raiz_local=tmp_path)
    rc_ = cli.cmd_checkin(args_checkin(local, **kw), entorno=_entorno(cli, fake, tmp_path))
    return rc_, fake


def _subs(fake) -> list[str]:
    return [c[1] for c in fake.cmds]


def estado_de(drive: dict[str, bytes], tmp_path: Path) -> str:
    return meta_de(drive["00_Input/_caso.md"], tmp_path)["estado_repositorio"]


def liberado(drive: dict[str, bytes], tmp_path: Path) -> bool:
    return "ultimo_checkin_timestamp" in meta_de(drive["00_Input/_caso.md"], tmp_path)


# ---------------------------------------------------------------------------
# Filas 1-2 · `_leer_manifest`: la degradación a merge de 2 VÍAS es silenciosa
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("manifest_crudo, base, caso", [
    (None, None, "ausente"),
    ("{ esto no es JSON", None, "corrupto"),
    ('{"generado": "x"}', None, "sin_clave_inventario"),
], ids=["ausente", "json_corrupto", "sin_inventario"])
def test_baseline_ilegible_degrada_a_dos_vias_en_silencio(cli, tmp_path, capsys,
                                                          manifest_crudo, base, caso):
    """Sin baseline el merge cae a 2 vías **sin avisar**, y eso convierte una subida
    limpia en un CONFLICTO.

    Lo predije al revés y el test lo corrigió, que es para lo que está. Con baseline,
    `doc.pdf` es «solo cambió local» (caso 2) y sube. **Sin** baseline, la tabla de 3
    vías no puede saber quién cambió: pasa por «creado distinto en local y en Drive»
    (caso 4) y devuelve `CONFLICT`. Así que perder el baseline no es
    silencioso-y-permisivo —no pisa nada— sino silencioso-**y-bloqueante**: el caso
    queda en `conflicto`, sin subir, y el operador no recibe ni una palabra sobre la
    causa real, que es el manifest.

    El caso «sin clave `inventario`» está aquí porque `_leer_manifest` devuelve **solo**
    `data["inventario"]`: un manifest con campos extra o de otra versión degrada igual.
    Ese hecho es lo que hoy hace inocuo el defecto del baseline del log (Task 6).
    """
    drive = drive_de({"00_Input/doc.pdf": b"BASE"})
    local = montar_local(tmp_path, {"00_Input/doc.pdf": b"LOCAL"},
                         base=base, manifest_crudo=manifest_crudo)

    rc_, fake = _correr(cli, tmp_path, drive, local)

    assert rc_ == 0, "el amarillo del conflicto sale con 0"
    assert drive["00_Input/doc.pdf"] == b"BASE", \
        "no sube: el conflicto no se auto-resuelve (y por eso no hay pérdida)"
    assert estado_de(drive, tmp_path) == "conflicto"
    assert not liberado(drive, tmp_path), "el ciclo no cierra"
    # El defecto se asierta por lo que el operador SÍ recibe, no por la ausencia de una
    # palabra en la salida capturada: el nombre de este test lleva «baseline» y viaja
    # dentro de `tmp_path`, que el frontal imprime, así que un `not in salida` lo
    # rompería el propio test. (Me pasó al escribirlo.)
    delta = (tmp_path / "work" / "DELTA_PREVIO.md").read_text(encoding="utf-8")
    assert "Creado distinto en local y en Drive" in delta, \
        ("el motivo que se le da al operador es un diagnóstico FALSO: nadie creó nada "
         "distinto, lo que pasó es que se perdió el baseline. Ahí está el defecto.")


# ---------------------------------------------------------------------------
# Fila 3-4 · el `lsjson` del CP1: se juzga por CONTENIDO, no por retorno
#
# Es el PRIMERO de los dos retornos que el frontal no examina.
# ---------------------------------------------------------------------------

def test_inventario_truncado_aborta_con_1_y_cero_mutacion(cli, tmp_path):
    """`stdout` truncado con rc 0 → `InventarioInvalido` → 1, sin tocar el Drive."""
    drive = drive_de({"00_Input/doc.pdf": b"BASE"})
    antes = dict(drive)
    local = montar_local(tmp_path, {"00_Input/doc.pdf": b"LOCAL"},
                         base={"00_Input/doc.pdf": b"BASE"})
    fake = FakeRclone(drive, raiz_local=tmp_path,
                      resultados={("lsjson", 1): (0, "[", "")})

    rc_, fake = _correr(cli, tmp_path, drive, local, fake=fake)

    assert rc_ == 1
    assert drive == antes
    assert _subs(fake) == ["lsjson"]


def test_lsjson_con_retorno_no_cero_pero_salida_parseable_SIGUE_ADELANTE(cli, tmp_path):
    """**El retorno del `lsjson` del CP1 no se examina**: manda el contenido.

    Uno de los dos únicos retornos que el frontal descarta. Se guioniza con
    `resultados` porque los `fallos*` heredados aplanan todo fallo a `rc=3` con
    `stdout="["`, que es JSON inválido: con ellos esta fila es **inconstruible**.

    Que Drive emita *exactamente* esta forma (rc≠0 con salida utilizable) queda
    **sin verificar**; el patrón sí está documentado para este Drive (`exit 1` por
    dangling shortcuts, de ahí el `--drive-skip-shortcuts`). Lo que la fila fija es
    el hecho del código: producción ignora el retorno.
    """
    drive = drive_de({"00_Input/doc.pdf": b"BASE"})
    local = montar_local(tmp_path, {"00_Input/doc.pdf": b"LOCAL"},
                         base={"00_Input/doc.pdf": b"BASE"})
    inventario = json.dumps([
        {"Path": "00_Input/doc.pdf", "Name": "doc.pdf", "Size": 4, "IsDir": False,
         "Hashes": {"md5": hashlib.md5(b"BASE").hexdigest()}},
        {"Path": "00_Input/_caso.md", "Name": "_caso.md", "Size": 1, "IsDir": False,
         "Hashes": {"md5": hashlib.md5(caso_md()).hexdigest()}},
    ])
    fake = FakeRclone(drive, raiz_local=tmp_path,
                      resultados={("lsjson", 1): (1, inventario, "dangling shortcut")})

    rc_, fake = _correr(cli, tmp_path, drive, local, fake=fake)

    assert rc_ == 0, "rc=1 en el inventario NO aborta el checkin"
    assert drive["00_Input/doc.pdf"] == b"LOCAL", "y el merge se ejecuta hasta el final"
    assert liberado(drive, tmp_path), "incluido liberar el lock"


# ---------------------------------------------------------------------------
# Fila 5 · el `rmdirs` de la bandeja: el OTRO retorno sin examinar
# ---------------------------------------------------------------------------

def test_rmdirs_fallido_se_ignora_y_el_lock_se_libera_igual(cli, tmp_path):
    """El retorno del `rmdirs` se descarta: se asierta lo comprobable, no lo inasertable.

    `FakeDrive` es un `dict` ruta→bytes y **no modela directorios**, así que no se puede
    afirmar «quedan directorios vacíos». Se afirma lo que sí: el comando se emitió, su
    retorno no cambió nada, y el lock quedó liberado.
    """
    bandeja = "_pendiente_checkin/pipeline/00_Input/nuevo.pdf"
    drive = drive_de({"00_Input/doc.pdf": b"igual", bandeja: b"contenido"})
    local = montar_local(tmp_path, {"00_Input/doc.pdf": b"igual"},
                         base={"00_Input/doc.pdf": b"igual"})
    fake = FakeRclone(drive, raiz_local=tmp_path,
                      resultados={("rmdirs", 1): (1, "", "no se pudo limpiar")})

    rc_, fake = _correr(cli, tmp_path, drive, local, fake=fake)

    assert rc_ == 0, "el rmdirs fallido no degrada el resultado"
    assert "rmdirs" in _subs(fake), "el comando se emitió"
    assert drive["00_Input/nuevo.pdf"] == b"contenido", "la bandeja sí se integró"
    assert liberado(drive, tmp_path), "y el lock se liberó pese al rmdirs fallido"


# ---------------------------------------------------------------------------
# Filas 6-7 · los dos caminos que dejan AMARILLO y conservan el lock
# ---------------------------------------------------------------------------

def test_check_con_diferencias_deja_amarillo_y_conserva_el_lock(cli, tmp_path, capsys):
    """`check` rc=1 → `verificacion_limpia` False → amarillo. Los bytes ya subieron."""
    drive = drive_de({"00_Input/doc.pdf": b"BASE"})
    local = montar_local(tmp_path, {"00_Input/doc.pdf": b"LOCAL"},
                         base={"00_Input/doc.pdf": b"BASE"})
    fake = FakeRclone(drive, raiz_local=tmp_path,
                      resultados={("check", 1): (1, "", "1 differences found")})

    rc_, fake = _correr(cli, tmp_path, drive, local, fake=fake)
    salida = capsys.readouterr().out

    assert rc_ == 0, "el amarillo sale con 0, igual que el conflicto"
    assert "AMARILLO" in salida
    assert estado_de(drive, tmp_path) == "prestado"
    assert not liberado(drive, tmp_path), "una verificación sucia no cierra el ciclo"
    assert "NO se libera el lock" in salida


def test_moveto_de_un_borrado_fallido_deja_amarillo_y_conserva_el_lock(cli, tmp_path, capsys):
    """`borrado_fallo` contamina `verificacion_limpia` aunque el `check` salga limpio.

    El rc se guioniza a **1**, que es el real de un `moveto` de origen ausente; los
    `fallos_sub` heredados lo aplanarían a 3 y el doble mentiría sobre el contrato.
    """
    drive = drive_de({"00_Input/borrado.pdf": b"a la papelera"})
    local = montar_local(tmp_path, {"00_Input/nuevo.pdf": b"NUEVO"},
                         base={"00_Input/borrado.pdf": b"a la papelera"})
    fake = FakeRclone(drive, raiz_local=tmp_path,
                      resultados={("moveto", 1): (1, "", "source not found")})

    rc_, fake = _correr(cli, tmp_path, drive, local, fake=fake)
    salida = capsys.readouterr().out

    assert rc_ == 0
    assert "AMARILLO" in salida
    assert "no se pudo mover a backup" in salida
    assert drive["00_Input/borrado.pdf"] == b"a la papelera", "el borrado no se propagó"
    assert estado_de(drive, tmp_path) == "prestado"
    assert not liberado(drive, tmp_path)


# ---------------------------------------------------------------------------
# Fila 8 · los artefactos del protocolo NO contaminan la carpeta del caso
# ---------------------------------------------------------------------------

def test_ningun_artefacto_del_protocolo_cae_en_la_carpeta_del_caso(cli, tmp_path):
    """Todo —DELTA, AUDITLOG, log del check, temporales— vive en el `work_dir`.

    Si alguno cayera en el caso, contaminaría el inventario del **siguiente** checkin:
    el merge lo vería como fichero nuevo en local y lo subiría al Drive.
    """
    drive = drive_de({"00_Input/doc.pdf": b"BASE"})
    local = montar_local(tmp_path, {"00_Input/doc.pdf": b"LOCAL"},
                         base={"00_Input/doc.pdf": b"BASE"})

    rc_, fake = _correr(cli, tmp_path, drive, local)

    assert rc_ == 0
    en_el_caso = sorted(p.name for p in local.rglob("*") if p.is_file())
    assert en_el_caso == ["MANIFEST_CHECKOUT.json", "doc.pdf"], \
        f"el protocolo dejó residuos en la carpeta del caso: {en_el_caso}"
    work = sorted(p.name for p in (tmp_path / "work").iterdir() if p.is_file())
    assert "DELTA_PREVIO.md" in work
    assert any(n.startswith("AUDITLOG_MERGE_") for n in work), \
        "el AUDITLOG se genera en el work_dir, no en el caso"


# ---------------------------------------------------------------------------
# Fila 9 · CP11 con `estado_repositorio` ausente — `MEJORAS #93-B`
# ---------------------------------------------------------------------------

def test_estado_ausente_aborta_con_2_SIN_tocar_nada(cli, tmp_path, capsys):
    """`MEJORAS #93-B`, **arreglado**. Y este test defendia el defecto.

    Su nombre anterior lo decia todo: `...revienta_en_cp11_DESPUES_de_mover_los_bytes`.
    Caracterizaba como esperado que `validar_transicion` lanzara `TransicionInvalida`
    cruda al operador **despues** de subir los bytes, registrar el evento e integrar la
    bandeja — y exigia POR ASERTO que el evento YA estuviera escrito. O sea que la suite
    montaba guardia sobre la traza duplicada de A-2c: cualquier arreglo la ponia roja,
    que es exactamente lo que paso.

    El contrato nuevo: la transicion se valida **antes de la primera escritura**. No se
    copia, no se verifica, no se registra y no se toca el lock — el aborto es de verdad
    «sin efectos», que es lo que el codigo 2 promete en la tabla del modulo.
    """
    from core.utils import build_frontmatter
    # Un `_caso.md` legitimo salvo que le falta `estado_repositorio`.
    sin_estado = (build_frontmatter({"meta": {"id_go": "W-TEST99", "ciudad": "Barcelona"}})
                  + chr(10) + CASO_MD_CUERPO).encode("utf-8")
    drive = {"00_Input/_caso.md": sin_estado,
             "00_Input/_intake_log.jsonl": LOG_PREVIO,
             "00_Input/doc.pdf": b"BASE"}
    local = montar_local(tmp_path, {"00_Input/doc.pdf": b"LOCAL"},
                         base={"00_Input/doc.pdf": b"BASE"})

    antes = {k: v for k, v in drive.items()}
    rc_, _fake = _correr(cli, tmp_path, drive, local)

    assert rc_ == 2, (
        f"se esperaba 2 —«abortado sin efectos», que es lo que la tabla de códigos del "
        f"modulo define para «caso no disponible»—, dio {rc_}")
    assert drive == antes, (
        "abortó «sin efectos» y mutó el Drive. El primer arreglo comprobaba esto DESPUÉS "
        "de copiar y verificar, así que los bytes SÍ se movían; R9/H9-02 midió que por "
        "esa vía un checkin reentrante subía trabajo nuevo al canon sin lock")
    assert drive["00_Input/doc.pdf"] == b"BASE", "el fichero del Drive no se tocó"
    assert len(drive["00_Input/_intake_log.jsonl"].splitlines()) == 1, (
        "el evento case_checkin NO puede quedar registrado: no se cerro ningun ciclo")
    salida = capsys.readouterr().out
    assert "no consta prestado" in salida.lower(), (
        f"la excepcion cruda se cambio por otro silencio: {salida[-300:]}")


# ---------------------------------------------------------------------------
# El ROJO de orquestación es inalcanzable: hecho, no intención
# ---------------------------------------------------------------------------

def test_el_rojo_del_semaforo_es_inalcanzable_por_orquestacion(cli, tmp_path, capsys):
    """`cmd_checkin` retorna en el `if copia_fallo` ANTES de clasificar el semáforo.

    Así que ninguna inyección de fallo de copia puede imprimir «ROJO»: el helper puro
    tiene esa rama y sus propios tests la cubren, pero la orquestación no la alcanza.
    Se fija como hecho para que nadie escriba un test que la busque.
    """
    drive = drive_de({"00_Input/doc.pdf": b"BASE"})
    local = montar_local(tmp_path, {"00_Input/doc.pdf": b"LOCAL"},
                         base={"00_Input/doc.pdf": b"BASE"})
    fake = FakeRclone(drive, raiz_local=tmp_path,
                      resultados={("copy", 1): (1, "", "boom")})

    rc_, fake = _correr(cli, tmp_path, drive, local, fake=fake)
    salida = capsys.readouterr().out

    assert rc_ == 1
    assert "ROJO" not in salida, "el rojo no se imprime nunca desde la orquestación"
    assert "semáforo" not in salida, "porque no se llega a clasificar"
    # Y el helper puro sí clasifica rojo: la rama existe, no la alcanza este camino.
    assert cli.clasificar_semaforo(conflictos=0, copia_fallo_sistemico=True,
                                   verificacion_limpia=False) == "rojo"
