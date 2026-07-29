"""Task 3 de la Fase 0: caracterización de `cmd_checkout`. Fija lo que HACE HOY.

**Red de seguridad, no especificación.** Estos tests se escriben ANTES de enhebrar el
`Entorno` por los `cmd_*` (Task 1B), y con el frontal **sin tocar**: la inyección es por
`monkeypatch` de `run_rclone`, `_tmp_dir`, `_SYNC_LAG_S`, `_nonce` y
`_usuario_por_defecto`, exactamente como hacen los 16 tests de #156/#160. En la Task 1B
cambiará el **montaje** a `entorno=` inyectado; **asertos, snapshots y trazas quedan
idénticos**, y cualquier aserto que haya que cambiar es señal de que el refactor no fue
neutral.

**Si algo de aquí falla, es un bug vivo que no conocíamos: para y repórtalo.** No se
arregla nada en la Fase 0.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from tests._barrera import REMOTO_SINTETICO as REMOTO
from tests._dobles import FakeRclone

CASO_MD_CUERPO = "# Caso W-TEST99\n\nDatos canónicos que NO se deben perder.\n"
NONCE_FIJO = "abcdef0123456789"


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


@pytest.fixture
def cli(monkeypatch, tmp_path):
    from scripts import repository_cli
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.setattr(repository_cli, "_SYNC_LAG_S", 0)
    monkeypatch.setattr(repository_cli, "_tmp_dir", lambda: work)
    monkeypatch.setattr(repository_cli, "_nonce", lambda: NONCE_FIJO)
    monkeypatch.setattr(repository_cli, "_usuario_por_defecto", lambda: "tester")
    return repository_cli


def args_checkout(local: Path, **kw) -> argparse.Namespace:
    base = dict(case_id="BaRS9 - Prueba - (W-TEST99) - Vuelta", local=str(local),
                remote_path="", folder_id=None, remote="r", team_drive="T",
                user="tester", dry_run=False, notas=None)
    base.update(kw)
    return argparse.Namespace(**base)


def _correr(cli, monkeypatch, tmp_path, drive, **kw):
    """Monta el doble, lo inyecta en `run_rclone` y ejecuta el checkout."""
    local = tmp_path / "local"
    fake = FakeRclone(drive, raiz_local=tmp_path)
    monkeypatch.setattr(cli, "run_rclone", fake)
    rc_ = cli.cmd_checkout(args_checkout(local, **kw))
    return rc_, fake, local


def _subs(fake) -> list[str]:
    return [c[1] for c in fake.cmds]


# ---------------------------------------------------------------------------
# Abortos sin efectos
# ---------------------------------------------------------------------------

def test_caso_prestado_aborta_con_2_sin_tocar_drive_ni_local(cli, monkeypatch, tmp_path):
    """Death snapshot de las DOS caras, no solo «no hay copy».

    Comprobar únicamente la ausencia del `copy` dejaría pasar una escritura del lock o
    un residuo en el árbol local, que es lo que de verdad importa aquí.
    """
    drive = {"00_Input/_caso.md": caso_md("prestado", checkout_user="otro"),
             "00_Input/doc.pdf": b"contenido"}
    antes = dict(drive)

    rc_, fake, local = _correr(cli, monkeypatch, tmp_path, drive)

    assert rc_ == 2
    assert drive == antes, "el Drive no se toca al encontrar el caso prestado"
    assert not local.exists(), "tampoco se crea el árbol local"
    assert _subs(fake) == ["copyto"], "solo el pull del CP0"


def test_caso_en_conflicto_aborta_con_2(cli, monkeypatch, tmp_path):
    drive = {"00_Input/_caso.md": caso_md("conflicto"), "00_Input/doc.pdf": b"x"}
    antes = dict(drive)

    rc_, fake, local = _correr(cli, monkeypatch, tmp_path, drive)

    assert rc_ == 2
    assert drive == antes
    assert "copy" not in _subs(fake)


def test_dry_run_no_escribe_nada(cli, monkeypatch, tmp_path):
    drive = {"00_Input/_caso.md": caso_md(), "00_Input/doc.pdf": b"x"}
    antes = dict(drive)

    rc_, fake, local = _correr(cli, monkeypatch, tmp_path, drive, dry_run=True)

    assert rc_ == 0
    assert drive == antes, "un dry-run que escribe el lock sería el peor de los bugs"
    assert not local.exists()
    assert _subs(fake) == ["copyto"]


def test_nonce_ajeno_tras_el_sync_lag_aborta_sin_copiar(cli, monkeypatch, tmp_path):
    """Otro checkout ganó la carrera: se abandona sin copiar y sin pisar su lock."""
    drive = {"00_Input/_caso.md": caso_md(), "00_Input/doc.pdf": b"x"}
    fake = FakeRclone(drive, raiz_local=tmp_path)
    # Tras el push del lock propio, un tercero deja el suyo: el nonce releído es ajeno.
    fake.armar(2, lambda n, cmd, d: d.escribir(
        "00_Input/_caso.md",
        caso_md("prestado", checkout_user="otro", checkout_nonce="9999999999999999")))
    monkeypatch.setattr(cli, "run_rclone", fake)
    local = tmp_path / "local"

    rc_ = cli.cmd_checkout(args_checkout(local))

    assert rc_ == 2
    assert "copy" not in _subs(fake), "no se copia sin ganar la carrera del lock"
    assert meta_de(drive["00_Input/_caso.md"], tmp_path)["checkout_user"] == "otro", \
        "el lock del ganador queda intacto"


# ---------------------------------------------------------------------------
# Camino feliz
# ---------------------------------------------------------------------------

def test_camino_feliz_orden_relativo_y_lock_completo(cli, monkeypatch, tmp_path):
    """Orden de operaciones y contenido del lock, en un solo sitio.

    El orden se fija **dentro** del test del camino feliz, como tramo de su traza, para
    que la Fase 2 tenga un único punto que actualizar cuando cambie.
    """
    drive = {"00_Input/_caso.md": caso_md(), "00_Input/doc.pdf": b"contenido",
             "90_Notas personales/n.md": b"privado"}

    rc_, fake, local = _correr(cli, monkeypatch, tmp_path, drive)

    assert rc_ == 0
    # contrato temporal (A-2): pull CP0 → push lock → pull verificación → copy →
    # push MANIFEST → pull log → **lsjson** → push log.
    #
    # El `lsjson` de la posición 7 es la sonda `_remoto_existe` de
    # `_append_evento_drive`: este caso todavía no tiene `_intake_log.jsonl`, así que el
    # pull del log falla con rc 3 y el frontal comprueba si el fichero **existe** antes
    # de decidir. Es el diseño de #156 —«ausente» es legítimo, «ilegible» no— y cuesta
    # una operación extra en el primer checkout de un caso. Lo esperaba en siete y son
    # ocho: la caracterización manda sobre la predicción.
    assert _subs(fake) == ["copyto", "copyto", "copyto", "copy",
                           "copyto", "copyto", "lsjson", "copyto"]

    meta = meta_de(drive["00_Input/_caso.md"], tmp_path)
    assert meta["estado_repositorio"] == "prestado"
    assert meta["checkout_user"] == "tester"
    assert meta["checkout_nonce"] == NONCE_FIJO
    assert meta["checkout_maquina"], "la máquina del lock no puede quedar vacía"
    assert meta["checkout_timestamp"], "el timestamp del lock tampoco"
    assert "ruta_local" not in meta and "checkout_ruta_local" not in meta, \
        "el lock NO publica la ruta local (§2.2): solo el hostname"
    assert meta["id_go"] == "W-TEST99", "los metadatos canónicos sobreviven al lock"


def test_el_protocolo_no_baja_a_local(cli, monkeypatch, tmp_path):
    """`_caso.md` y `_intake_log.jsonl` son proyección protocolaria, no contenido.

    Es el fichero cuya materialización dispara `MEJORAS #96`, así que la Fase 2 se
    diseñaría sobre una mentira si el doble lo bajara.
    """
    drive = {"00_Input/_caso.md": caso_md(),
             "00_Input/_intake_log.jsonl": b'{"event":"x"}\n',
             "00_Input/doc.pdf": b"contenido",
             "90_Notas personales/n.md": b"privado"}

    rc_, fake, local = _correr(cli, monkeypatch, tmp_path, drive)

    assert rc_ == 0
    assert (local / "00_Input/doc.pdf").exists()
    assert not (local / "00_Input/_caso.md").exists()
    assert not (local / "00_Input/_intake_log.jsonl").exists()
    assert not (local / "90_Notas personales").exists()


def test_el_manifest_se_genera_en_local_y_se_sube(cli, monkeypatch, tmp_path):
    drive = {"00_Input/_caso.md": caso_md(), "00_Input/doc.pdf": b"contenido"}

    rc_, fake, local = _correr(cli, monkeypatch, tmp_path, drive)

    assert rc_ == 0
    mf = local / "MANIFEST_CHECKOUT.json"
    assert mf.exists(), "el baseline que lee el checkin es el LOCAL"
    datos = json.loads(mf.read_text(encoding="utf-8"))
    assert datos["n_ficheros"] == len(datos["inventario"]) == 1
    assert "00_Input/doc.pdf" in datos["inventario"]
    assert "MANIFEST_CHECKOUT.json" in drive, "y se sube como redundancia del §3.3"


def test_el_evento_lleva_los_campos_del_contrato(cli, monkeypatch, tmp_path):
    """Incluye `ruta_local`, que la SPEC §6.1 **retira en la Fase 2**.

    Este es el test que habrá que actualizar entonces: hoy caracteriza que se publica,
    y el contrato nuevo la mantendrá solo en el registro privado.
    """
    drive = {"00_Input/_caso.md": caso_md(), "00_Input/doc.pdf": b"contenido"}

    rc_, fake, local = _correr(cli, monkeypatch, tmp_path, drive)

    assert rc_ == 0
    lineas = drive["00_Input/_intake_log.jsonl"].decode("utf-8").strip().splitlines()
    evento = json.loads(lineas[-1])
    assert evento["event"] == "case_checkout"
    assert evento["actor"] == "tester"
    assert evento["case_id"] == "BaRS9 - Prueba - (W-TEST99) - Vuelta"
    d = evento["details"]
    assert d["checkout_nonce"] == NONCE_FIJO
    assert d["ruta_local"] == str(local)          # ← la Fase 2 retira este campo
    assert d["n_ficheros"] == 1
    assert d["manifest_hash"], "el hash del MANIFEST es la prueba del baseline"


def test_esperar_el_sync_lag_ocurre_una_vez_y_no_duerme(cli, monkeypatch, tmp_path):
    """El write-then-verify del lock necesita la espera; un test no puede dormirla.

    Hoy el frontal llama a `time.sleep(_SYNC_LAG_S)` directamente, así que se sustituye
    `time.sleep`. En la Task 1B esto pasa a `entorno.esperar` y el **montaje** cambia;
    el aserto —una espera, con el valor del módulo— no.
    """
    import time as _time
    dormido: list[float] = []
    monkeypatch.setattr(cli, "_SYNC_LAG_S", 4)
    monkeypatch.setattr(_time, "sleep", dormido.append)
    drive = {"00_Input/_caso.md": caso_md(), "00_Input/doc.pdf": b"x"}

    rc_, fake, local = _correr(cli, monkeypatch, tmp_path, drive)

    assert rc_ == 0
    assert dormido == [4], "una sola espera, con el sync lag del módulo"


# ---------------------------------------------------------------------------
# Fallo de la copia
# ---------------------------------------------------------------------------

def test_copy_fallido_revierte_el_lock_y_devuelve_1(cli, monkeypatch, tmp_path):
    drive = {"00_Input/_caso.md": caso_md(), "00_Input/doc.pdf": b"contenido"}
    fake = FakeRclone(drive, raiz_local=tmp_path,
                      resultados={("copy", 1): (1, "", "boom")})
    monkeypatch.setattr(cli, "run_rclone", fake)
    local = tmp_path / "local"

    rc_ = cli.cmd_checkout(args_checkout(local))

    assert rc_ == 1
    meta = meta_de(drive["00_Input/_caso.md"], tmp_path)
    assert meta["estado_repositorio"] == "disponible", "el lock se revierte"
    assert meta["id_go"] == "W-TEST99", "y el rollback no degrada el _caso.md a un stub"
    assert "MANIFEST_CHECKOUT.json" not in drive, "no hay baseline de un checkout fallido"


# ---------------------------------------------------------------------------
# El entrypoint público
# ---------------------------------------------------------------------------

def test_smoke_del_parser_publico(cli, monkeypatch, tmp_path):
    """Sin esto, el `Namespace` a mano podría divergir del que produce la CLI real."""
    drive = {"00_Input/_caso.md": caso_md(), "00_Input/doc.pdf": b"x"}
    fake = FakeRclone(drive, raiz_local=tmp_path)
    monkeypatch.setattr(cli, "run_rclone", fake)
    local = tmp_path / "local"

    args = cli.build_parser().parse_args([
        "checkout", "BaRS9 - Prueba - (W-TEST99) - Vuelta",
        "--local", str(local), "--remote-path", "",
        "--remote", "r", "--team-drive", "T", "--user", "tester",
    ])

    assert cli.cmd_checkout(args) == 0
    assert (local / "00_Input/doc.pdf").exists()
