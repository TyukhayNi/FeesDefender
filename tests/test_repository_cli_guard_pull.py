"""Guard: un pull fallido del protocolo NUNCA se confunde con contenido vacío.

Dos defectos vivos del frontal, medidos contra rclone v1.73.5 (Windows amd64):

1. ``_pull_caso_md`` devolvía ``{}`` tanto si el ``_caso.md`` no existía como si
   rclone falló. ``estado_de_fm({})`` vale ``"disponible"``, así que un hipo de red
   durante el checkout hacía que el caso pareciera libre, se adquiriera el lock
   sobre un frontmatter vacío y ``_push_caso_md`` **sobrescribiera el ``_caso.md``
   del Drive** con solo los campos del lock y un cuerpo ``# Caso`` — perdiendo
   ``id_go``, ``partes``, ``tipo_caso``, ``ciudad`` y ``sudespacho_expedientes``.
   Sin ``id_go``, ``case_locator.resolve_ref`` deja de encontrar el caso por W-code.

2. ``_append_evento_drive`` ignoraba el ``returncode`` del pull del log: si el pull
   fallaba, ``lineas`` quedaba vacía y el push **reemplazaba todo el
   ``_intake_log.jsonl`` canónico por una sola línea**.

Ambos son fallos del mismo tipo —tratar «no pude leer» como «estaba vacío»— en el
camino que mueve expedientes reales. La política es *fail closed* (SPEC dual,
invariante 2): ante duda no se muta y no se libera el lock.

Contrato de rclone verificado en v1.73.5: ``copyto`` de un origen inexistente
devuelve **exit 3** y NO crea el destino; ``lsjson`` de una ruta inexistente
devuelve **exit 3** con ``stdout`` = ``"["`` (JSON inválido). Eso permite
distinguir «no existe» de «no se pudo leer» sin adivinar.

Datos SIEMPRE sintéticos. Sin red, sin rclone real, sin unidad ``G:``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from tests._barrera import REMOTO_SINTETICO as REMOTO   # fuente unica del remote


# ---------------------------------------------------------------------------
# Doble mínimo de rclone (se sustituye por el de la Fase 0 cuando exista)
# ---------------------------------------------------------------------------

# El doble vive ahora en `tests/_dobles/fake_drive.py` (Task 2 de la Fase 0), que
# PROMUEVE el embrionario que estaba aqui: mismos `fallos`/`fallos_push`/`fallos_sub`,
# mas el canal `resultados` y el hook con `armar(n_objetivo, callback)`. La migracion
# solo toca imports y montaje: ningun aserto de este fichero cambia.
#
# Paridad comprobada en los tres ejes antes de borrar el doble viejo:
#  - `registro` de comandos: `.cmds` se conserva como ALIAS contractual;
#  - precondiciones: mismo remote sintetico (ahora importado, no redefinido) y
#    `FakeDrive` guarda la REFERENCIA al dict del test, no una copia — copiarla
#    habria dejado los asertos `drive[...] == original` mirando un objeto congelado;
#  - snapshot final del Drive: identico, comprobado corriendo los 16 sin tocarlos.
from tests._dobles import FakeRclone


CASO_MD_CUERPO = "# Caso W-TEST99\n\nDatos canónicos que NO se deben perder.\n"


def caso_md(estado: str = "disponible", **lock) -> bytes:
    from core.utils import build_frontmatter
    meta = {"id_go": "W-TEST99", "tipo_caso": "VUELTA", "ciudad": "Barcelona",
            "estado_repositorio": estado}
    meta.update(lock)
    fm = {"meta": meta}
    return (build_frontmatter(fm) + "\n" + CASO_MD_CUERPO).encode("utf-8")


def meta_de(data: bytes, tmp_path: Path) -> dict:
    from core.utils import read_md
    p = tmp_path / "_leido.md"
    p.write_bytes(data)
    fm, _ = read_md(p)
    return (fm or {}).get("meta") or {}


def cuerpo_de(data: bytes, tmp_path: Path) -> str:
    from core.utils import read_md
    p = tmp_path / "_leido2.md"
    p.write_bytes(data)
    _, cuerpo = read_md(p)
    return cuerpo


@pytest.fixture
def cli(monkeypatch, tmp_path):
    from scripts import repository_cli
    monkeypatch.setattr(repository_cli, "_SYNC_LAG_S", 0)          # sin esperas reales
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.setattr(repository_cli, "_tmp_dir", lambda: work)  # inspeccionable
    return repository_cli


def args_checkout(local: Path, **kw) -> argparse.Namespace:
    base = dict(case_id="BaRS9 - Prueba - (W-TEST99) - Vuelta", local=str(local),
                remote_path="", folder_id=None, remote="r", team_drive="T",
                user="tester", dry_run=False, notas=None)
    base.update(kw)
    return argparse.Namespace(**base)


def args_checkin(local: Path, **kw) -> argparse.Namespace:
    base = dict(case_id="BaRS9 - Prueba - (W-TEST99) - Vuelta", local=str(local),
                remote_path="", folder_id=None, remote="r", team_drive="T",
                user="tester", dry_run=False, wcode="W-TEST99", yes=True)
    base.update(kw)
    return argparse.Namespace(**base)


def pushes_de_caso_md(fake: FakeRclone) -> list[list[str]]:
    return [c for c in fake.cmds
            if c[1] == "copyto" and c[3].endswith("00_Input/_caso.md")]


# ---------------------------------------------------------------------------
# 1. El defecto del `_caso.md`
# ---------------------------------------------------------------------------

def test_checkout_aborta_si_no_puede_leer_el_caso_md(cli, monkeypatch, tmp_path):
    """Un pull fallido NO es un caso disponible: se aborta sin tocar el Drive."""
    original = caso_md()
    drive = {"00_Input/_caso.md": original, "00_Input/doc.pdf": b"contenido"}
    fake = FakeRclone(drive, raiz_local=tmp_path, fallos={"00_Input/_caso.md": 3})
    monkeypatch.setattr(cli, "run_rclone", fake)

    rc_code = cli.cmd_checkout(args_checkout(tmp_path / "local"))

    assert rc_code != 0
    assert not pushes_de_caso_md(fake), "no se puede escribir un lock que no se pudo leer"
    assert drive["00_Input/_caso.md"] == original, "el `_caso.md` del Drive quedó intacto"


def test_checkout_conserva_el_cuerpo_y_los_metadatos_al_adquirir_el_lock(
        cli, monkeypatch, tmp_path):
    """El push del lock no puede degradar el `_caso.md` a un stub `# Caso`."""
    drive = {"00_Input/_caso.md": caso_md(), "00_Input/doc.pdf": b"contenido"}
    fake = FakeRclone(drive, raiz_local=tmp_path)
    monkeypatch.setattr(cli, "run_rclone", fake)

    rc_code = cli.cmd_checkout(args_checkout(tmp_path / "local"))

    assert rc_code == 0
    meta = meta_de(drive["00_Input/_caso.md"], tmp_path)
    assert meta["estado_repositorio"] == "prestado"
    assert meta["id_go"] == "W-TEST99"          # sin esto resolve_ref pierde el caso
    assert meta["tipo_caso"] == "VUELTA"
    assert "Datos canónicos" in cuerpo_de(drive["00_Input/_caso.md"], tmp_path)


def test_checkout_no_verificable_conserva_el_lock_y_no_copia(cli, monkeypatch, tmp_path):
    """Si la relectura del nonce no se puede leer: no se copia y NO se cancela el lock."""
    drive = {"00_Input/_caso.md": caso_md(), "00_Input/doc.pdf": b"contenido"}
    fake = FakeRclone(drive, raiz_local=tmp_path)
    llamadas = {"n": 0}
    real = fake.__call__

    def con_fallo_en_la_relectura(cmd):
        if cmd[1] == "copyto" and cmd[2].endswith("00_Input/_caso.md"):
            llamadas["n"] += 1
            if llamadas["n"] == 2:                       # el pull de verificación
                return subprocess.CompletedProcess([], 3, "", "fake")
        return real(cmd)

    monkeypatch.setattr(cli, "run_rclone", con_fallo_en_la_relectura)

    rc_code = cli.cmd_checkout(args_checkout(tmp_path / "local"))

    assert rc_code != 0
    assert not [c for c in fake.cmds if c[1] == "copy"], "no se copia sin nonce verificado"
    meta = meta_de(drive["00_Input/_caso.md"], tmp_path)
    assert meta["estado_repositorio"] == "prestado", "el lock se conserva, no se cancela a ciegas"


def test_push_caso_md_exige_el_cuerpo_explicito(cli, tmp_path):
    """El cuerpo se pasa, no se adivina con un glob del directorio de trabajo."""
    with pytest.raises(TypeError):
        cli._push_caso_md({"meta": {}}, REMOTO, tmp_path)     # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# 2. El defecto del `_intake_log.jsonl`
# ---------------------------------------------------------------------------

def test_append_evento_no_trunca_el_log_si_falla_el_pull(cli, monkeypatch, tmp_path):
    """Un pull fallido del log no puede convertirse en «el log estaba vacío»."""
    log = (b'{"event":"upload_manual"}\n'
           b'{"event":"pull_crm"}\n'
           b'{"event":"procesado_sala_maquina"}\n')
    drive = {"00_Input/_intake_log.jsonl": log}
    fake = FakeRclone(drive, raiz_local=tmp_path, fallos={"00_Input/_intake_log.jsonl": 3})
    monkeypatch.setattr(cli, "run_rclone", fake)

    with pytest.raises(cli.ProtocoloIOError):
        cli._append_evento_drive(REMOTO, tmp_path, case_id="W-TEST99",
                                 event="case_checkout", details={}, actor="tester")

    assert drive["00_Input/_intake_log.jsonl"] == log, "los 3 eventos siguen ahí"


def test_append_evento_trata_un_log_ausente_como_log_vacio(cli, monkeypatch, tmp_path):
    """Un caso sin log todavía es legítimo: se crea con el evento nuevo."""
    drive: dict[str, bytes] = {"00_Input/_caso.md": caso_md()}
    fake = FakeRclone(drive, raiz_local=tmp_path)
    monkeypatch.setattr(cli, "run_rclone", fake)

    cli._append_evento_drive(REMOTO, tmp_path, case_id="W-TEST99",
                             event="case_checkout", details={}, actor="tester")

    lineas = drive["00_Input/_intake_log.jsonl"].decode("utf-8").strip().splitlines()
    assert len(lineas) == 1
    assert json.loads(lineas[0])["event"] == "case_checkout"


# ---------------------------------------------------------------------------
# 3. El checkin no libera ni marca conflicto a ciegas
# ---------------------------------------------------------------------------

def montar_checkin(tmp_path: Path, drive: dict[str, bytes]) -> Path:
    """Local == Drive == baseline: el plan sale vacío y el semáforo verde."""
    local = tmp_path / "local"
    (local / "00_Input").mkdir(parents=True)
    (local / "00_Input" / "doc.pdf").write_bytes(b"contenido")
    inv = {"00_Input/doc.pdf": {"hash": hashlib.md5(b"contenido").hexdigest(), "size": 9}}
    (local / "MANIFEST_CHECKOUT.json").write_text(
        json.dumps({"generado": "2026-07-29T10:00:00Z", "n_ficheros": 1, "inventario": inv}),
        encoding="utf-8")
    drive["00_Input/doc.pdf"] = b"contenido"
    return local


def test_checkin_no_libera_el_lock_si_no_puede_leer_el_caso_md(cli, monkeypatch, tmp_path):
    prestado = caso_md("prestado", checkout_user="tester", checkout_nonce="abc")
    drive = {"00_Input/_caso.md": prestado, "00_Input/_intake_log.jsonl": b""}
    local = montar_checkin(tmp_path, drive)
    fake = FakeRclone(drive, raiz_local=tmp_path, fallos={"00_Input/_caso.md": 3})
    monkeypatch.setattr(cli, "run_rclone", fake)

    rc_code = cli.cmd_checkin(args_checkin(local))

    assert rc_code != 0
    meta = meta_de(drive["00_Input/_caso.md"], tmp_path)
    assert meta["estado_repositorio"] == "prestado", "no se libera un lock que no se pudo leer"
    assert not pushes_de_caso_md(fake)


def test_checkin_no_marca_conflicto_si_no_puede_leer_el_caso_md(cli, monkeypatch, tmp_path):
    """Con conflictos y sin poder leer el protocolo: nada se escribe en el Drive."""
    prestado = caso_md("prestado", checkout_user="tester", checkout_nonce="abc")
    drive = {"00_Input/_caso.md": prestado, "00_Input/_intake_log.jsonl": b""}
    local = tmp_path / "local"
    (local / "00_Input").mkdir(parents=True)
    (local / "00_Input" / "doc.pdf").write_bytes(b"LOCAL")        # cambió en local
    drive["00_Input/doc.pdf"] = b"DRIVE"                          # y en Drive
    inv = {"00_Input/doc.pdf": {"hash": hashlib.md5(b"BASE").hexdigest(), "size": 4}}
    (local / "MANIFEST_CHECKOUT.json").write_text(
        json.dumps({"inventario": inv}), encoding="utf-8")
    fake = FakeRclone(drive, raiz_local=tmp_path, fallos={"00_Input/_caso.md": 3})
    monkeypatch.setattr(cli, "run_rclone", fake)

    rc_code = cli.cmd_checkin(args_checkin(local))

    assert rc_code != 0
    assert meta_de(drive["00_Input/_caso.md"], tmp_path)["estado_repositorio"] == "prestado"
    assert not pushes_de_caso_md(fake)


# ---------------------------------------------------------------------------
# 4. El otro lado del mismo fallo: un PUSH que falla no puede reportarse como éxito
#
# El guard del pull (arriba) cerró la LECTURA del protocolo y dejó la ESCRITURA
# igual: el retorno de `_push_caso_md` y del push del log se ignoraban, así que un
# fallo de red al liberar el lock dejaba el caso `prestado` en el Drive mientras la
# CLI imprimía «✓ VERDE … lock liberado» y devolvía 0.
#
# Regla: un fallo al escribir ESTADO DE PROTOCOLO (lock, log de custodia) es fatal
# (salida 4); un fallo al escribir CORROBORACIÓN (evidencia, redundancia del
# manifest en Drive) es un aviso ruidoso que no bloquea, porque los bytes del caso
# ya están donde deben.
# ---------------------------------------------------------------------------

def test_checkout_no_declara_lock_adquirido_si_el_push_falla(cli, monkeypatch, tmp_path, capsys):
    original = caso_md()
    drive = {"00_Input/_caso.md": original, "00_Input/doc.pdf": b"contenido"}
    fake = FakeRclone(drive, raiz_local=tmp_path, fallos_push={"00_Input/_caso.md": [1]})
    monkeypatch.setattr(cli, "run_rclone", fake)

    rc_code = cli.cmd_checkout(args_checkout(tmp_path / "local"))

    assert rc_code == 4
    assert drive["00_Input/_caso.md"] == original, "el Drive no se mutó"
    assert not [c for c in fake.cmds if c[1] == "copy"], "no se copia sin lock confirmado"
    assert "lock adquirido" not in capsys.readouterr().out


def test_rollback_del_checkout_no_afirma_haber_revertido_si_el_push_falla(
        cli, monkeypatch, tmp_path, capsys):
    """El mensaje «Lock revertido a disponible» era una afirmación sin comprobar."""
    drive = {"00_Input/_caso.md": caso_md(), "00_Input/doc.pdf": b"contenido"}
    # 1er push (adquisición) OK; falla el 2º, que es el del rollback. Y el `copy`
    # falla para llegar hasta ahí.
    fake = FakeRclone(drive, raiz_local=tmp_path, fallos_push={"00_Input/_caso.md": [2]},
                      fallos_sub={"copy": [1]})
    monkeypatch.setattr(cli, "run_rclone", fake)

    rc_code = cli.cmd_checkout(args_checkout(tmp_path / "local"))
    salida = capsys.readouterr().out

    assert rc_code == 4
    assert meta_de(drive["00_Input/_caso.md"], tmp_path)["estado_repositorio"] == "prestado"
    # Frase con espacios a propósito: `tmp_path` lleva el NOMBRE DEL TEST y el
    # frontal imprime rutas, así que un aserto sobre la subcadena "revertido" lo
    # cumpliría el propio nombre del test. Es la trampa que invalidó la primera
    # versión de este fichero.
    assert "Lock revertido a disponible" not in salida, \
        "no puede afirmar que revirtió si el push falló"


def test_checkin_no_declara_lock_liberado_si_el_push_falla(cli, monkeypatch, tmp_path, capsys):
    prestado = caso_md("prestado", checkout_user="tester", checkout_nonce="abc")
    drive = {"00_Input/_caso.md": prestado, "00_Input/_intake_log.jsonl": b""}
    local = montar_checkin(tmp_path, drive)
    fake = FakeRclone(drive, raiz_local=tmp_path, fallos_push={"00_Input/_caso.md": [1]})
    monkeypatch.setattr(cli, "run_rclone", fake)

    rc_code = cli.cmd_checkin(args_checkin(local))
    salida = capsys.readouterr().out

    assert rc_code == 4
    assert meta_de(drive["00_Input/_caso.md"], tmp_path)["estado_repositorio"] == "prestado"
    assert "lock liberado" not in salida
    # `semáforo: VERDE` SÍ debe seguir apareciendo: el merge está subido y
    # verificado, y eso es cierto. Lo que no puede aparecer es la línea de cierre.
    assert "AUDITLOG subido" not in salida


def test_checkin_no_afirma_conflicto_escrito_si_el_push_falla(cli, monkeypatch, tmp_path, capsys):
    prestado = caso_md("prestado", checkout_user="tester", checkout_nonce="abc")
    drive = {"00_Input/_caso.md": prestado, "00_Input/_intake_log.jsonl": b"",
             "00_Input/doc.pdf": b"DRIVE"}
    local = tmp_path / "local"
    (local / "00_Input").mkdir(parents=True)
    (local / "00_Input" / "doc.pdf").write_bytes(b"LOCAL")
    (local / "MANIFEST_CHECKOUT.json").write_text(
        json.dumps({"inventario": {"00_Input/doc.pdf": {
            "hash": hashlib.md5(b"BASE").hexdigest(), "size": 4}}}), encoding="utf-8")
    fake = FakeRclone(drive, raiz_local=tmp_path, fallos_push={"00_Input/_caso.md": [1]})
    monkeypatch.setattr(cli, "run_rclone", fake)

    rc_code = cli.cmd_checkin(args_checkin(local))
    salida = capsys.readouterr().out

    assert rc_code == 4
    assert meta_de(drive["00_Input/_caso.md"], tmp_path)["estado_repositorio"] == "prestado"
    assert "escrito en el Drive" not in salida


def test_append_evento_lanza_si_el_push_del_log_falla(cli, monkeypatch, tmp_path):
    log = b'{"event":"upload_manual"}\n'
    drive = {"00_Input/_intake_log.jsonl": log}
    fake = FakeRclone(drive, raiz_local=tmp_path, fallos_push={"_intake_log.jsonl": [1]})
    monkeypatch.setattr(cli, "run_rclone", fake)

    with pytest.raises(cli.ProtocoloIOError):
        cli._append_evento_drive(REMOTO, tmp_path, case_id="W-TEST99",
                                 event="case_checkin", details={}, actor="tester")

    assert drive["00_Input/_intake_log.jsonl"] == log


def test_evidencia_fallida_avisa_pero_no_bloquea_el_checkin(cli, monkeypatch, tmp_path, capsys):
    """La evidencia es corroboración, no el merge: no puede dejar el caso prestado."""
    prestado = caso_md("prestado", checkout_user="tester", checkout_nonce="abc")
    drive = {"00_Input/_caso.md": prestado, "00_Input/_intake_log.jsonl": b""}
    local = montar_checkin(tmp_path, drive)
    fake = FakeRclone(drive, raiz_local=tmp_path, fallos_push={"07_AI cowork": [1, 2]})
    monkeypatch.setattr(cli, "run_rclone", fake)

    rc_code = cli.cmd_checkin(args_checkin(local))
    salida = capsys.readouterr().out

    assert rc_code == 0
    assert meta_de(drive["00_Input/_caso.md"], tmp_path)["estado_repositorio"] == "disponible"
    # Ídem: "evidencia" a secas lo cumple el nombre de este test dentro de la ruta
    # que el frontal imprime. El aserto tiene que ser una frase del mensaje.
    assert "No se pudo subir la evidencia" in salida


def test_manifest_no_subido_avisa_y_el_checkout_no_finge(cli, monkeypatch, tmp_path, capsys):
    """El MANIFEST local es el baseline real; el del Drive es redundancia (§3.3)."""
    drive = {"00_Input/_caso.md": caso_md(), "00_Input/doc.pdf": b"contenido"}
    fake = FakeRclone(drive, raiz_local=tmp_path, fallos_push={"MANIFEST_CHECKOUT.json": [1]})
    monkeypatch.setattr(cli, "run_rclone", fake)
    local = tmp_path / "local"

    rc_code = cli.cmd_checkout(args_checkout(local))
    salida = capsys.readouterr().out

    assert rc_code == 0
    assert (local / "MANIFEST_CHECKOUT.json").is_file(), "el baseline local sí existe"
    assert "MANIFEST_CHECKOUT.json" in salida and "no se pudo subir" in salida.lower()


def test_bandeja_ilegible_no_libera_el_lock(cli, monkeypatch, tmp_path, capsys):
    """8º defecto: `_integrar_bandeja` devolvía (0,0) y el checkin liberaba igual.

    Mismo patrón que el guard del pull —un listado que no se pudo leer no es una
    bandeja vacía— con la misma consecuencia: se libera el lock creyendo que no
    quedaba nada por integrar.
    """
    prestado = caso_md("prestado", checkout_user="tester", checkout_nonce="abc")
    drive = {"00_Input/_caso.md": prestado, "00_Input/_intake_log.jsonl": b""}
    local = montar_checkin(tmp_path, drive)
    # El 1er lsjson es el inventario de CP1; el 2º es el de la bandeja (CP10).
    fake = FakeRclone(drive, raiz_local=tmp_path, fallos_sub={"lsjson": [2]})
    monkeypatch.setattr(cli, "run_rclone", fake)

    rc_code = cli.cmd_checkin(args_checkin(local))

    assert rc_code == 4
    assert meta_de(drive["00_Input/_caso.md"], tmp_path)["estado_repositorio"] == "prestado"
    assert "lock liberado" not in capsys.readouterr().out
