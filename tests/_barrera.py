"""Barrera de test de la Fase 0: ningún test alcanza rclone real, el Drive real ni `CASOS_ROOT`.

**Alcance: TODA la suite.** Un `subprocess.run` real desde `scripts/repository_cli.py`
no es legítimo en ningún test del repo, y limitar la barrera a una fase dejaría el
agujero abierto para el siguiente test que se escriba.

## Las dos mitades, y por qué hacen falta las dos

`run_rclone` es la **única superficie de `subprocess`** del frontal (`repository_cli.py`
`:391` la anotación y `:399` la llamada, ambas dentro de ella). De ahí que:

- **El proxy** (`_ProxySubprocess`) cierra la ejecución **mientras `run_rclone` es la
  de verdad**. Sustituye el *binding del módulo*, no `subprocess.run`: el frontal hace
  `import subprocess`, así que `repository_cli.subprocess` **es** el módulo global y
  parchear su `run` afectaría a toda la suite.
- **El validador** (`assert_operandos_sinteticos`) cierra el Drive real y las rutas
  fuera del test **también cuando `run_rclone` está doblado** — que es lo que hacen los
  tests de caracterización. Sin esta segunda mitad el proxy queda con superficie cero
  justo en los tests que más I/O hacen, y la barrera valida exactamente nada.
  `FakeRclone` (Task 2) invoca **este mismo** validador; si hubiera dos copias,
  divergirían.

## Por qué `raiz_local` es un parámetro y no se deduce

`CASOS_ROOT` **no gobierna** la ruta local del frontal: `cmd_checkout` hace
`local = Path(args.local)` (`:454`), `local.mkdir(parents=True, exist_ok=True)` (`:517`)
y escribe el `MANIFEST_CHECKOUT.json` (`:545-548`) sobre lo que venga en `args.local`.
La raíz permitida es por tanto un dato **explícito** del montaje del test (su `tmp_path`).

## El binario sintético

`Settings` es `@dataclass(frozen=True)`, así que `settings.rclone_binary` no se puede
mutar. Tampoco se fija `RCLONE_BINARY` por entorno: lo leen también
`core/intake_drive.py` y `core/sync.py`, y no hay motivo para perturbarlos. Se sustituye
el **binding cacheado** `repository_cli.settings` por una copia
(`dataclasses.replace`, legítimo sobre un frozen) con el binario sintético.
"""

from __future__ import annotations

import dataclasses
import importlib
import os
import subprocess as _subprocess_real
from pathlib import Path
from typing import Any

#: Remote sintético ÚNICO de la suite. Todo test que hable con el frontal usa este.
REMOTO_SINTETICO = "r,team_drive=T:"

#: Binario que no existe en ninguna máquina: si algo se ejecutara, fallaría ruidoso.
#: Tiene **forma de ruta y termina en `rclone`** a propósito, por dos razones: en
#: producción `settings.rclone_binary` puede ser una ruta absoluta al ejecutable, y
#: `test_build_copy_cmd_flags_obligatorios` (que NO se toca) asierta justo eso. Un
#: nombre inventado sin esa forma habría sido menos fiel, no más seguro: lo que da la
#: garantía es que la ruta no existe, no cómo se llame.
BINARIO_SINTETICO = "/sintetico-de-test/no-existe/rclone"

#: Flags cuyo valor es una RUTA (local o remota) y por tanto se valida.
FLAGS_CON_RUTA = frozenset({"--files-from", "--files-from-raw", "--backup-dir",
                            "--log-file", "--filter-from", "--exclude-from",
                            "--include-from"})

#: Flags cuyo valor NO es una ruta: patrones, números, niveles. Se salta.
FLAGS_CON_VALOR_OPACO = frozenset({"--transfers", "--log-level", "--exclude",
                                   "--include", "--filter", "--checkers",
                                   "--max-depth", "--hash-type", "--drive-team-drive",
                                   "--drive-root-folder-id"})


class BarreraViolada(AssertionError):
    """Un test intentó salir del entorno sintético.

    Hereda de `AssertionError` a propósito: es un fallo del test, no del código bajo
    prueba, y así ningún `except Exception` del frontal se lo come por accidente.
    """


# ---------------------------------------------------------------------------
# Validador de operandos — lo comparten el proxy y `FakeRclone`
# ---------------------------------------------------------------------------

def _es_remoto(token: str) -> bool:
    """¿Es una cadena de conexión rclone y no una ruta local?

    Discriminante: la posición del primer `:`. En Windows `C:\\x` lo tiene en el
    índice 1 (letra de unidad); un remote rclone —`r,team_drive=T:`,
    `gdrive_tl,team_drive=ID:`— lo tiene en 2 o más. Confundirlos es exactamente el
    agujero que esta barrera existe para cerrar, así que hay test propio
    (`test_letra_de_unidad_windows_es_ruta_local_no_remote`).
    """
    return token.find(":") >= 2


def _norm(p: Path) -> str:
    return os.path.normcase(str(p))


def _bajo(candidata: Path, raiz: Path) -> bool:
    c, r = _norm(candidata), _norm(raiz)
    return c == r or c.startswith(r + os.sep)


def _validar_operando(token: str, *, raiz: Path, cmd: list[str]) -> None:
    if _es_remoto(token):
        if not token.startswith(REMOTO_SINTETICO):
            raise BarreraViolada(
                f"remote no sintético en el comando: {token!r}\n"
                f"Los defaults del frontal son el remote y el team_drive REALES: un "
                f"test que no pase --remote/--team-drive apunta al Drive de producción. "
                f"Usa {REMOTO_SINTETICO!r}.\ncomando: {cmd}"
            )
        return
    try:
        resuelta = Path(token).resolve()
    except (OSError, ValueError) as exc:      # ruta imposible en esta plataforma
        raise BarreraViolada(f"operando local ilegible {token!r}: {exc}") from exc
    if not _bajo(resuelta, raiz):
        raise BarreraViolada(
            f"ruta local fuera de la raíz permitida: {token!r}\n"
            f"  resuelta : {resuelta}\n"
            f"  permitida: {raiz}\n"
            f"Recuerda que CASOS_ROOT NO gobierna `args.local`, y que `_tmp_dir()` "
            f"hace `mkdtemp` fuera del test: inyéctalo.\ncomando: {cmd}"
        )


def assert_operandos_sinteticos(cmd: list[str], *, raiz_local: Path | str) -> None:
    """Lanza `BarreraViolada` si el comando toca algo que no es del test.

    Recorre el comando entendiendo qué flags llevan valor y cuáles de esos valores son
    rutas. Un flag desconocido con valor de ruta se trataría como booleano y su valor
    como operando, que es el lado **seguro** del error: se valida de más, no de menos.
    """
    raiz = Path(raiz_local).resolve()
    if len(cmd) < 2:
        raise BarreraViolada(f"comando rclone incompleto: {cmd}")
    if str(cmd[0]) != BINARIO_SINTETICO:
        raise BarreraViolada(
            f"binario no sintético: {cmd[0]!r} (esperado {BINARIO_SINTETICO!r}). "
            f"La barrera sustituye el binding `repository_cli.settings`; si ves el "
            f"binario real, algo lo ha restaurado (¿un reload?).\ncomando: {cmd}"
        )
    i = 2                                     # 0 = binario, 1 = subcomando
    while i < len(cmd):
        tok = str(cmd[i])
        if tok.startswith("-"):
            if "=" in tok:                    # --flag=valor: inline, nada que mirar
                i += 1
            elif tok in FLAGS_CON_RUTA:
                if i + 1 >= len(cmd):
                    raise BarreraViolada(f"{tok} sin valor en {cmd}")
                _validar_operando(str(cmd[i + 1]), raiz=raiz, cmd=cmd)
                i += 2
            elif tok in FLAGS_CON_VALOR_OPACO:
                i += 2
            else:
                i += 1
        else:
            _validar_operando(tok, raiz=raiz, cmd=cmd)
            i += 1


# ---------------------------------------------------------------------------
# Proxy de `subprocess`
# ---------------------------------------------------------------------------

class _ProxySubprocess:
    """Delega todo en el módulo real salvo lo que crea procesos, que lanza.

    Se instala en `repository_cli.subprocess`. Antes de lanzar, valida los operandos
    para que el mensaje diga **qué** intentaba tocar el test y no solo que se bloqueó.
    """

    _PROHIBIDO = ("run", "Popen", "call", "check_call", "check_output")

    def __init__(self, *, raiz_local: Path) -> None:
        self._raiz = Path(raiz_local).resolve()

    def __getattr__(self, nombre: str) -> Any:
        return getattr(_subprocess_real, nombre)

    def _cerrado(self, nombre: str, args: tuple, kwargs: dict) -> BarreraViolada:
        cmd = args[0] if args else kwargs.get("args")
        detalle = ""
        if isinstance(cmd, list):
            try:
                assert_operandos_sinteticos([str(c) for c in cmd], raiz_local=self._raiz)
            except BarreraViolada as exc:
                detalle = f"\nY ADEMÁS el comando no era sintético:\n{exc}"
        return BarreraViolada(
            f"la Fase 0 no puede ejecutar procesos desde scripts/repository_cli.py "
            f"(`subprocess.{nombre}`).\nInyecta un doble de `run_rclone` "
            f"(tests/_dobles/fake_drive.py).\ncomando: {cmd}{detalle}"
        )

    def run(self, *args: Any, **kwargs: Any):
        raise self._cerrado("run", args, kwargs)

    def Popen(self, *args: Any, **kwargs: Any):
        raise self._cerrado("Popen", args, kwargs)

    def call(self, *args: Any, **kwargs: Any):
        raise self._cerrado("call", args, kwargs)

    def check_call(self, *args: Any, **kwargs: Any):
        raise self._cerrado("check_call", args, kwargs)

    def check_output(self, *args: Any, **kwargs: Any):
        raise self._cerrado("check_output", args, kwargs)


# ---------------------------------------------------------------------------
# Instalación
# ---------------------------------------------------------------------------

def instalar(monkeypatch, *, raiz_local: Path) -> None:
    """Instala la barrera para un test. La llama la fixture `autouse` del `conftest`.

    Es `autouse` de **función**, no de sesión: una fixture de sesión se monta en el
    setup del primer test, o sea **después de la colección**, así que no puede proteger
    ningún efecto de import (y `core.config` se importa a nivel de módulo en varios
    ficheros de test). Lo que necesita ir antes de la colección va en el cuerpo del
    `conftest`, no aquí.
    """
    from scripts import repository_cli

    monkeypatch.setattr(repository_cli, "subprocess",
                        _ProxySubprocess(raiz_local=raiz_local))
    monkeypatch.setattr(
        repository_cli, "settings",
        dataclasses.replace(repository_cli.settings, rclone_binary=BINARIO_SINTETICO),
    )

    reload_real = importlib.reload

    def _reload_vetado(modulo):
        if getattr(modulo, "__name__", "") == "scripts.repository_cli":
            raise BarreraViolada(
                "prohibido `importlib.reload(scripts.repository_cli)` durante los "
                "tests: restauraría los bindings reales de `subprocess` y `settings` "
                "a mitad de la suite. Recargar `core.config` SÍ está permitido."
            )
        return reload_real(modulo)

    monkeypatch.setattr(importlib, "reload", _reload_vetado)
