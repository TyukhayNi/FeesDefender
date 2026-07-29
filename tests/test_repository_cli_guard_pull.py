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

REMOTO = "r,team_drive=T:"


# ---------------------------------------------------------------------------
# Doble mínimo de rclone (se sustituye por el de la Fase 0 cuando exista)
# ---------------------------------------------------------------------------

class FakeRclone:
    """Interpreta los subcomandos que el frontal usa, sobre un Drive en memoria.

    ``drive``: ``{ruta_relativa_posix: bytes}``.
    ``fallos``: ``{ruta_relativa: rc}`` — el PULL de esa ruta devuelve ``rc`` y no
    escribe nada (modela el hipo de red, que es el disparador de los dos defectos).
    """

    def __init__(self, drive: dict[str, bytes], *, fallos: dict[str, int] | None = None):
        self.drive = drive
        self.fallos = fallos or {}
        self.cmds: list[list[str]] = []

    # -- helpers
    @staticmethod
    def _es_remoto(arg: str) -> bool:
        return arg.startswith(REMOTO)

    @staticmethod
    def _rel(arg: str) -> str:
        return arg[len(REMOTO):]

    def _ok(self, stdout: str = "") -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess([], 0, stdout, "")

    def _err(self, rc: int, stderr: str = "fake") -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess([], rc, "", stderr)

    def _inventario_json(self, prefijo: str = "") -> str:
        items = []
        for rel, data in sorted(self.drive.items()):
            if prefijo and not rel.startswith(prefijo):
                continue
            items.append({
                "Path": rel[len(prefijo):] if prefijo else rel,
                "Name": rel.rsplit("/", 1)[-1],
                "Size": len(data),
                "MimeType": "application/octet-stream",
                "ModTime": "2026-07-29T10:00:00.000Z",
                "IsDir": False,
                "ID": "fake-id",
                # v1.73.5 backend Drive: claves en minúscula, 3 algoritmos.
                "Hashes": {"md5": hashlib.md5(data).hexdigest(),
                           "sha1": "0" * 40, "sha256": "0" * 64},
            })
        return json.dumps(items)

    # -- dispatch
    def __call__(self, cmd: list[str]) -> subprocess.CompletedProcess:
        self.cmds.append(list(cmd))
        sub = cmd[1]

        if sub == "copyto":
            origen, destino = cmd[2], cmd[3]
            if self._es_remoto(origen):                      # PULL remoto → local
                rel = self._rel(origen)
                if rel in self.fallos:
                    return self._err(self.fallos[rel])
                if rel not in self.drive:
                    return self._err(3, "directory not found")   # contrato v1.73.5
                p = Path(destino)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(self.drive[rel])
                return self._ok()
            # PUSH local → remoto
            src = Path(origen)
            if not src.exists():
                return self._err(3, "directory not found")
            self.drive[self._rel(destino)] = src.read_bytes()
            return self._ok()

        if sub == "lsjson":
            destino = cmd[2]
            rel = self._rel(destino)
            if rel and rel not in self.drive and not any(
                    k.startswith(rel.rstrip("/") + "/") for k in self.drive):
                return subprocess.CompletedProcess([], 3, "[", "directory not found")
            if rel in self.drive:                            # lsjson de UN fichero
                return self._ok(self._inventario_json(prefijo=rel.rsplit("/", 1)[0] + "/"
                                                      if "/" in rel else ""))
            return self._ok(self._inventario_json())

        if sub == "copy":
            # Drive→local (checkout): materializa lo que no está excluido.
            origen, destino = cmd[2], cmd[3]
            if self._es_remoto(origen):
                from core import repository_checkout as rc
                for rel, data in self.drive.items():
                    if rc.esta_excluido(rel):
                        continue
                    p = Path(destino) / rel
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_bytes(data)
            self._crear_log_si_procede(cmd)
            return self._ok()

        if sub == "check":
            self._crear_log_si_procede(cmd)
            return self._ok()

        if sub in ("moveto", "rmdirs"):
            return self._ok()

        return self._ok()

    @staticmethod
    def _crear_log_si_procede(cmd: list[str]) -> None:
        """rclone crea el ``--log-file``; sin esto ``_upload_evidencia`` lo saltaría."""
        if "--log-file" in cmd:
            p = Path(cmd[cmd.index("--log-file") + 1])
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("fake log\n", encoding="utf-8")


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
    fake = FakeRclone(drive, fallos={"00_Input/_caso.md": 3})
    monkeypatch.setattr(cli, "run_rclone", fake)

    rc_code = cli.cmd_checkout(args_checkout(tmp_path / "local"))

    assert rc_code != 0
    assert not pushes_de_caso_md(fake), "no se puede escribir un lock que no se pudo leer"
    assert drive["00_Input/_caso.md"] == original, "el `_caso.md` del Drive quedó intacto"


def test_checkout_conserva_el_cuerpo_y_los_metadatos_al_adquirir_el_lock(
        cli, monkeypatch, tmp_path):
    """El push del lock no puede degradar el `_caso.md` a un stub `# Caso`."""
    drive = {"00_Input/_caso.md": caso_md(), "00_Input/doc.pdf": b"contenido"}
    fake = FakeRclone(drive)
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
    fake = FakeRclone(drive)
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
    fake = FakeRclone(drive, fallos={"00_Input/_intake_log.jsonl": 3})
    monkeypatch.setattr(cli, "run_rclone", fake)

    with pytest.raises(cli.ProtocoloIOError):
        cli._append_evento_drive(REMOTO, tmp_path, case_id="W-TEST99",
                                 event="case_checkout", details={}, actor="tester")

    assert drive["00_Input/_intake_log.jsonl"] == log, "los 3 eventos siguen ahí"


def test_append_evento_trata_un_log_ausente_como_log_vacio(cli, monkeypatch, tmp_path):
    """Un caso sin log todavía es legítimo: se crea con el evento nuevo."""
    drive: dict[str, bytes] = {"00_Input/_caso.md": caso_md()}
    fake = FakeRclone(drive)
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
    fake = FakeRclone(drive, fallos={"00_Input/_caso.md": 3})
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
    fake = FakeRclone(drive, fallos={"00_Input/_caso.md": 3})
    monkeypatch.setattr(cli, "run_rclone", fake)

    rc_code = cli.cmd_checkin(args_checkin(local))

    assert rc_code != 0
    assert meta_de(drive["00_Input/_caso.md"], tmp_path)["estado_repositorio"] == "prestado"
    assert not pushes_de_caso_md(fake)
