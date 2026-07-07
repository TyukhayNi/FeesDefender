"""Tests de los helpers PUROS del frontal CLI (scripts.repository_cli).

Solo se testean las partes deterministas y sin I/O: parseo de inventarios de
``rclone lsjson``, validación por contenido (no por exit code — hallazgo 3 del
piloto), clasificación del semáforo y construcción de comandos rclone
(flags obligatorios, exclusiones, remote con team_drive, backup-dir, --fast-list).

La orquestación real contra el Drive (subprocess + rclone) NO se testea aquí:
es I/O contra un sistema externo no reproducible en un repo público. Se mantiene
fina y delega toda decisión en el cerebro (``core.repository_checkout``).

Datos SIEMPRE sintéticos.
"""

from __future__ import annotations

import json

import pytest


@pytest.fixture
def cli():
    from scripts import repository_cli
    return repository_cli


# ---------------------------------------------------------------------------
# Parseo de inventario (rclone lsjson -R --hash)
# ---------------------------------------------------------------------------

def test_parse_inventario_lsjson_basico(cli):
    salida = json.dumps([
        {"Path": "00_Input/04_Manual/a.pdf", "Size": 100, "IsDir": False,
         "Hashes": {"md5": "aaa"}},
        {"Path": "00_Input/04_Manual", "Size": 0, "IsDir": True},
        {"Path": "01_Procesado/INDICE.md", "Size": 50, "IsDir": False,
         "Hashes": {"md5": "bbb"}},
    ])
    inv = cli.parse_inventario_lsjson(salida)
    assert inv == {
        "00_Input/04_Manual/a.pdf": {"hash": "aaa", "size": 100},
        "01_Procesado/INDICE.md": {"hash": "bbb", "size": 50},
    }


def test_parse_inventario_google_native_sin_md5(cli):
    salida = json.dumps([
        {"Path": "doc_google", "Size": -1, "IsDir": False, "Hashes": {}},
        {"Path": "hoja_google", "Size": -1, "IsDir": False},
    ])
    inv = cli.parse_inventario_lsjson(salida)
    assert inv["doc_google"]["hash"] is None
    assert inv["hoja_google"]["hash"] is None


def test_parse_inventario_normaliza_backslashes(cli):
    salida = json.dumps([
        {"Path": "00_Input\\04_Manual\\a.pdf", "Size": 1, "IsDir": False,
         "Hashes": {"md5": "x"}},
    ])
    inv = cli.parse_inventario_lsjson(salida)
    assert "00_Input/04_Manual/a.pdf" in inv


# ---------------------------------------------------------------------------
# Validación por CONTENIDO, no por exit code (hallazgo 3 del piloto)
# ---------------------------------------------------------------------------

def test_validar_inventario_json_invalido_lanza(cli):
    with pytest.raises(cli.InventarioInvalido):
        cli.validar_inventario_texto("no soy json {")


def test_validar_inventario_vacio_lanza(cli):
    # rclone contra unidad sin acceso puede terminar "bien" y vacío.
    with pytest.raises(cli.InventarioInvalido):
        cli.validar_inventario_texto("[]")


def test_validar_inventario_ok_devuelve_inventario(cli):
    salida = json.dumps([
        {"Path": "a.pdf", "Size": 1, "IsDir": False, "Hashes": {"md5": "x"}},
    ])
    inv = cli.validar_inventario_texto(salida)
    assert "a.pdf" in inv


# ---------------------------------------------------------------------------
# Semáforo VERDE / AMARILLO / ROJO
# ---------------------------------------------------------------------------

def test_semaforo_verde(cli):
    assert cli.clasificar_semaforo(conflictos=0, copia_fallo_sistemico=False,
                                   verificacion_limpia=True) == "verde"


def test_semaforo_amarillo_por_conflictos(cli):
    assert cli.clasificar_semaforo(conflictos=2, copia_fallo_sistemico=False,
                                   verificacion_limpia=True) == "amarillo"


def test_semaforo_amarillo_por_verificacion_sucia(cli):
    assert cli.clasificar_semaforo(conflictos=0, copia_fallo_sistemico=False,
                                   verificacion_limpia=False) == "amarillo"


def test_semaforo_rojo_por_fallo_copia(cli):
    assert cli.clasificar_semaforo(conflictos=0, copia_fallo_sistemico=True,
                                   verificacion_limpia=True) == "rojo"


# ---------------------------------------------------------------------------
# Construcción de comandos rclone (flags obligatorios)
# ---------------------------------------------------------------------------

def test_remote_arg_incluye_team_drive(cli):
    arg = cli.remote_arg("gdrive_tl", "0AAhcjDaZBWe6Uk9PVA", "CASOS/x")
    # IDs de carpeta antes que rutas por nombre (hallazgo 2 del piloto).
    assert arg.startswith("gdrive_tl,")
    assert "team_drive=0AAhcjDaZBWe6Uk9PVA" in arg
    assert arg.endswith(":CASOS/x")


def test_build_copy_cmd_flags_obligatorios(cli):
    cmd = cli.build_copy_cmd(
        origen="C:/local", destino="gdrive_tl,team_drive=ID:CASOS/x",
        backup_dir="gdrive_tl:_merge_backups/W_TS", log_file="auditlog.log")
    assert cmd[0].endswith("rclone") or cmd[0] == "rclone"
    assert "copy" in cmd
    assert "--checksum" in cmd
    assert "--drive-skip-shortcuts" in cmd
    # backup-dir presente
    assert "--backup-dir" in cmd
    i = cmd.index("--backup-dir")
    assert cmd[i + 1] == "gdrive_tl:_merge_backups/W_TS"
    # exclusiones de protocolo (por basename) presentes
    joined = " ".join(cmd)
    assert "_caso.md" in joined
    assert "_intake_log.jsonl" in joined
    assert "90_Notas personales/**" in joined
    # log a fichero, NUNCA pipe de PowerShell
    assert "--log-file" in cmd
    assert "|" not in joined


def test_build_check_cmd_one_way_fast_list(cli):
    cmd = cli.build_check_cmd(
        local="C:/local", destino="gdrive_tl,team_drive=ID:CASOS/x",
        log_file="check.log")
    assert "check" in cmd
    assert "--one-way" in cmd     # los solo-Drive se preservan
    assert "--fast-list" in cmd   # hallazgo 6 del piloto (cuota API)
    assert "--drive-skip-shortcuts" in cmd


def test_build_lsjson_cmd_recursivo_con_hash_y_fast_list(cli):
    cmd = cli.build_lsjson_cmd("gdrive_tl,team_drive=ID:CASOS/x")
    assert "lsjson" in cmd
    assert "-R" in cmd or "--recursive" in cmd
    assert "--hash" in cmd
    assert "--fast-list" in cmd


def test_nombre_auditlog_y_snapshot_usan_ts_compacto(cli):
    ts = "2026-07-07T0945Z"
    assert cli.nombre_auditlog(ts) == "AUDITLOG_MERGE_2026-07-07T0945Z.jsonl"
    assert cli.backup_dir_arg("gdrive_tl", "W-XXXXX", ts) == \
        "gdrive_tl:_merge_backups/W-XXXXX_2026-07-07T0945Z"
