"""Task 0 de la Fase 0: la barrera es implementable, automática y COMPROBABLE.

Estos tests son el juez de la barrera. Lo que fijan, y por qué cada uno existe:

1. **Nada se ejecuta.** ``run_rclone`` sin doble no llega a `subprocess.run`.
2. **El remote real se rechaza.** Los defaults del frontal son el remote y el
   `team_drive` REALES (`RCLONE_REMOTE_TL`/`TEAM_DRIVE_TL`), así que un test que
   olvide pasar `--remote` apunta a producción.
3. **Las rutas locales viven bajo la raíz del test.** `CASOS_ROOT` **no** gobierna
   `args.local` (`repository_cli.py:454`), así que la raíz permitida es un dato
   explícito del montaje y no una consecuencia de la configuración.
4. **El validador es UNO.** El mismo que usa el proxy lo usará `FakeRclone`
   (Task 2), porque doblar `run_rclone` deja el proxy sin superficie: es la única
   función del módulo que llama a `subprocess` (`:391`, `:399`).
5. **Control positivo.** Un comando legítimo PASA. Sin este test, una barrera que
   rechazara todo pasaría por buena.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from tests._barrera import (
    BINARIO_SINTETICO,
    REMOTO_SINTETICO,
    BarreraViolada,
    assert_operandos_sinteticos,
)


@pytest.fixture
def cli():
    from scripts import repository_cli
    return repository_cli


def _cmd(*resto: str) -> list[str]:
    return [BINARIO_SINTETICO, *resto]


# ---------------------------------------------------------------------------
# 1. Nada se ejecuta: el proxy de subprocess
# ---------------------------------------------------------------------------

def test_run_rclone_sin_doble_no_ejecuta_nada(cli):
    """El camino por defecto de un test es NO alcanzar rclone."""
    with pytest.raises(BarreraViolada) as exc:
        cli.run_rclone(_cmd("lsjson", f"{REMOTO_SINTETICO}x"))
    assert "no puede ejecutar procesos" in str(exc.value)


def test_el_proxy_delega_lo_que_no_ejecuta(cli):
    """Sustituir el binding no puede romper el resto del módulo `subprocess`."""
    assert cli.subprocess.CompletedProcess([], 0, "", "").returncode == 0


def test_popen_tambien_esta_cerrado(cli):
    with pytest.raises(BarreraViolada):
        cli.subprocess.Popen([BINARIO_SINTETICO, "version"])


def test_el_binario_del_frontal_es_sintetico(cli):
    """`Settings` es frozen: se sustituye el binding, no el campo."""
    assert cli._rclone_bin() == BINARIO_SINTETICO


# ---------------------------------------------------------------------------
# 2 y 3. El validador de operandos
# ---------------------------------------------------------------------------

def test_comando_legitimo_pasa(tmp_path):
    """CONTROL POSITIVO: sin esto, una barrera que lo rechace todo parecería buena."""
    log = tmp_path / "work" / "checkout.log"
    assert_operandos_sinteticos(
        _cmd("copy", f"{REMOTO_SINTETICO}CASOS/W-X", str(tmp_path / "caso"),
             "--checksum", "--transfers", "4",
             "--exclude", "desktop.ini", "--exclude", "90_Notas personales/**",
             "--log-level", "INFO", "--log-file", str(log)),
        raiz_local=tmp_path,
    )


def test_remote_real_rechazado(tmp_path):
    from core.config import RCLONE_REMOTE_TL, TEAM_DRIVE_TL
    real = f"{RCLONE_REMOTE_TL},team_drive={TEAM_DRIVE_TL}:CASOS"
    with pytest.raises(BarreraViolada) as exc:
        assert_operandos_sinteticos(_cmd("lsjson", real), raiz_local=tmp_path)
    assert "remote no sintético" in str(exc.value)


def test_ruta_local_fuera_de_la_raiz_rechazada(tmp_path):
    fuera = tmp_path.parent / "fuera_del_test"
    with pytest.raises(BarreraViolada) as exc:
        assert_operandos_sinteticos(
            _cmd("copy", f"{REMOTO_SINTETICO}x", str(fuera)), raiz_local=tmp_path)
    assert "fuera de la raíz permitida" in str(exc.value)


def test_el_valor_de_log_file_tambien_se_valida(tmp_path):
    """`--log-file`, `--files-from` y `--backup-dir` llevan rutas, no son opacos."""
    with pytest.raises(BarreraViolada):
        assert_operandos_sinteticos(
            _cmd("copy", str(tmp_path / "a"), f"{REMOTO_SINTETICO}x",
                 "--log-file", str(tmp_path.parent / "escapado.log")),
            raiz_local=tmp_path,
        )


def test_los_patrones_de_exclude_no_son_rutas(tmp_path):
    """`--exclude 90_Notas personales/**` es un patrón; validarlo como ruta daría falso positivo."""
    assert_operandos_sinteticos(
        _cmd("copy", str(tmp_path / "a"), f"{REMOTO_SINTETICO}x",
             "--exclude", "90_Notas personales/**", "--exclude", "_caso.md"),
        raiz_local=tmp_path,
    )


def test_letra_de_unidad_windows_es_ruta_local_no_remote(tmp_path):
    """`C:\\x` tiene dos puntos como `r,team_drive=T:`. Confundirlos abre el agujero."""
    with pytest.raises(BarreraViolada) as exc:
        assert_operandos_sinteticos(
            _cmd("copyto", r"C:\Users\publico\secreto.md", f"{REMOTO_SINTETICO}x"),
            raiz_local=tmp_path,
        )
    assert "fuera de la raíz permitida" in str(exc.value)


def test_backup_dir_sintetico_pasa_y_real_no(tmp_path):
    from scripts.repository_cli import backup_dir_arg
    ok = backup_dir_arg("r", "W-X", "20260729_1200", team_drive="T")
    assert_operandos_sinteticos(
        _cmd("copy", str(tmp_path / "a"), f"{REMOTO_SINTETICO}x", "--backup-dir", ok),
        raiz_local=tmp_path)
    malo = backup_dir_arg("gdrive_tl", "W-X", "20260729_1200", team_drive="REAL")
    with pytest.raises(BarreraViolada):
        assert_operandos_sinteticos(
            _cmd("copy", str(tmp_path / "a"), f"{REMOTO_SINTETICO}x", "--backup-dir", malo),
            raiz_local=tmp_path)


def test_binario_no_sintetico_rechazado(tmp_path):
    with pytest.raises(BarreraViolada) as exc:
        assert_operandos_sinteticos(
            ["rclone", "lsjson", f"{REMOTO_SINTETICO}x"], raiz_local=tmp_path)
    assert "binario" in str(exc.value)


# ---------------------------------------------------------------------------
# 4. El veto de `importlib.reload`
# ---------------------------------------------------------------------------

def test_reload_de_repository_cli_prohibido(cli):
    """Recargarlo restauraría `subprocess` y `settings` reales a mitad de la suite."""
    with pytest.raises(BarreraViolada) as exc:
        importlib.reload(cli)
    assert "reload" in str(exc.value)


def test_reload_de_core_config_permitido():
    """`tmp_casos_root` y varios tests lo recargan; el veto es solo del frontal."""
    from core import config as cfg
    importlib.reload(cfg)


# ---------------------------------------------------------------------------
# 5. Guard estático del estilo de import
# ---------------------------------------------------------------------------

def test_el_frontal_no_importa_run_desde_subprocess():
    """`from subprocess import run` eludiría el proxy: se veta por estático.

    No es un defecto de hoy (el módulo hace `import subprocess`); es el guard que
    impide que mañana lo sea.
    """
    fuente = Path("scripts/repository_cli.py").read_text(encoding="utf-8")
    assert "from subprocess import" not in fuente, (
        "usa `import subprocess` (el proxy sustituye el binding del módulo); "
        "`from subprocess import run` cachea la función real y elude la barrera"
    )
