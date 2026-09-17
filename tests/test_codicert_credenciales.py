"""Resolución de credenciales de Codicert: entorno, .env de la raíz real y registro."""
from __future__ import annotations

import subprocess
from unittest.mock import MagicMock

import pytest

from core import codicert


def test_credenciales_del_sandbox_salen_del_entorno(monkeypatch):
    monkeypatch.setenv("CODICERT_SANDBOX_USUARIO", "engelvoelkersalfa")
    monkeypatch.setenv("CODICERT_SANDBOX_CLAVE", "secreto")
    assert codicert.credenciales(None, "sandbox") == ("engelvoelkersalfa", "secreto")


def test_credenciales_de_una_plaza_usan_su_prefijo(monkeypatch):
    monkeypatch.setenv("CODICERT_MADRID_USUARIO", "madrid.bd")
    monkeypatch.setenv("CODICERT_MADRID_CLAVE", "secreto")
    assert codicert.credenciales("Madrid", "produccion") == ("madrid.bd", "secreto")


def test_san_sebastian_no_lleva_espacio_ni_tilde_en_la_variable(monkeypatch):
    monkeypatch.setenv("CODICERT_SANSEBASTIAN_USUARIO", "sansebastian.bd")
    monkeypatch.setenv("CODICERT_SANSEBASTIAN_CLAVE", "secreto")
    assert codicert.credenciales("San Sebastián", "produccion")[0] == "sansebastian.bd"


def test_de_fuentes_lentas_lee_el_env_de_la_raiz_real_via_git_common_dir(tmp_path, monkeypatch):
    """Ejercita de verdad la lectura del `.env`: sin este test, borrar el bloque
    entero de `_de_fuentes_lentas` dejaba la suite en verde (hallazgo de revisión
    de cobertura cero).

    Usa `--git-common-dir` (la raíz REAL del repo, incluso desde un worktree) y
    NO `--show-toplevel` (que desde un worktree devuelve el propio worktree, que
    es justo donde no hay `.env`). Si el código vuelve a `--show-toplevel`, la
    primera aserción se pone roja — verificado a mano, ver
    `.superpowers/sdd/task-1-report.md`.
    """
    raiz_real = tmp_path / "repo_real"
    raiz_real.mkdir()
    (raiz_real / ".env").write_text(
        "CODICERT_SINTETICA_USUARIO=usuario_desde_env", encoding="utf-8",
    )
    # Lo que devolvería `--show-toplevel` desde un worktree: un directorio real,
    # pero sin `.env` — el defecto que el hallazgo 1 corrige.
    worktree_falso = tmp_path / "worktree_falso"
    worktree_falso.mkdir()

    llamadas: list[list[str]] = []

    def _git_falso(cmd, **kwargs):
        llamadas.append(list(cmd))
        resultado = MagicMock(spec=subprocess.CompletedProcess)
        resultado.returncode = 0
        if cmd == ["git", "rev-parse", "--git-common-dir"]:
            resultado.stdout = str(raiz_real / ".git")
        elif cmd == ["git", "rev-parse", "--show-toplevel"]:
            resultado.stdout = str(worktree_falso)
        else:  # registro de Windows: no debe alcanzarse si el .env resuelve
            resultado.stdout = ""
        return resultado

    monkeypatch.setattr("subprocess.run", _git_falso)

    valor = codicert._de_fuentes_lentas("CODICERT_SINTETICA_USUARIO")

    assert llamadas, "subprocess.run no fue invocado por _de_fuentes_lentas"
    assert llamadas[0] == ["git", "rev-parse", "--git-common-dir"], (
        "debe pedir --git-common-dir: --show-toplevel devuelve el worktree, sin .env"
    )
    assert valor == "usuario_desde_env"
    assert len(llamadas) == 1  # resuelto por el .env; no cae al registro de Windows


def test_sin_clave_el_error_NO_filtra_el_usuario_presente(monkeypatch):
    """Escenario real de la fuga: el usuario SÍ está poblado (valor reconocible)
    y falta la clave. La versión anterior de este test borraba usuario y clave
    a la vez, así que no había ningún valor que filtrar: un mensaje que añadiera
    el usuario en claro habría seguido pasando (hallazgo de revisión)."""
    monkeypatch.setenv("CODICERT_SEVILLA_USUARIO", "usuario_sevilla_reconocible")
    monkeypatch.delenv("CODICERT_SEVILLA_CLAVE", raising=False)
    monkeypatch.setattr(codicert, "_de_fuentes_lentas", lambda nombre: None)
    with pytest.raises(codicert.CodicertAuthError) as exc:
        codicert.credenciales("Sevilla", "produccion")
    mensaje = str(exc.value)
    assert "CODICERT_SEVILLA_CLAVE" in mensaje
    assert "usuario_sevilla_reconocible" not in mensaje


def test_una_ciudad_desconocida_no_inventa_prefijo():
    with pytest.raises(codicert.CodicertError):
        codicert.credenciales("Cuenca", "produccion")
