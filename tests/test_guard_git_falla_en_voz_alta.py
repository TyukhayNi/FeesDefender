"""Git que falla en voz alta: un fallo de git no puede leerse como «no hay nada».

Lo vio la R1 de Codex de los estados medidos (2026-09-26): en la copia `git archive` sin `.git`
sobre la que trabajan los revisores, `git ls-files` falla, la lista sale vacía y los guards que la
recorren pasan en verde sin haber mirado nada. La frontera eran cinco sitios, no uno (plan
`docs/superpowers/plans/2026-09-26-git-que-falla-en-voz-alta.md`).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests import _git
from tests import test_docs_gobernanza as gobernanza
from tests import test_gitignore_no_inerte as gitignore
from tests import test_guard_no_basetemp_versionado as basetemp

ROOT = Path(__file__).resolve().parents[1]
NO_ES_REPO = "fatal: not a git repository (or any of the parent directories): .git"


class _GitQueFalla:
    """`subprocess.run` de un git que falla como en la copia sin `.git` de los revisores."""

    def __init__(self, rc: int = 128, stderr: str = NO_ES_REPO) -> None:
        self.rc, self.stderr = rc, stderr

    def __call__(self, args, **_kw):
        return subprocess.CompletedProcess(args, self.rc, stdout="", stderr=self.stderr)


# --- el helper ----------------------------------------------------------------------------------

def test_el_helper_para_con_el_stderr_si_git_falla(monkeypatch):
    monkeypatch.setattr(subprocess, "run", _GitQueFalla())
    with pytest.raises(pytest.fail.Exception, match="not a git repository"):
        _git.git("ls-files", cwd=ROOT)


def test_el_helper_admite_los_codigos_que_el_comando_usa_como_respuesta(monkeypatch):
    """`git grep` devuelve 1 cuando no encuentra nada: para un guard de «esto no aparece», el
    éxito. Si no se declara, el 1 también para."""
    monkeypatch.setattr(subprocess, "run", _GitQueFalla(rc=1, stderr=""))
    assert _git.git("grep", "-l", "x", cwd=ROOT, rc_validos=(0, 1)).returncode == 1
    with pytest.raises(pytest.fail.Exception):
        _git.git("grep", "-l", "x", cwd=ROOT)


def test_el_helper_para_si_git_no_se_puede_ejecutar(monkeypatch):
    def sin_git(*_a, **_k):
        raise FileNotFoundError("git")

    monkeypatch.setattr(subprocess, "run", sin_git)
    with pytest.raises(pytest.fail.Exception, match="no se pudo ejecutar"):
        _git.git("ls-files", cwd=ROOT)


# --- los guards de la frontera ------------------------------------------------------------------

@pytest.mark.parametrize("nombre, enumera", [
    ("test_docs_gobernanza._md_trackeados", lambda: gobernanza._md_trackeados()),
    ("test_docs_gobernanza._refs_a_docs_plan_legacy", lambda: gobernanza._refs_a_docs_plan_legacy()),
    ("test_guard_no_basetemp_versionado._trackeados", lambda: basetemp._trackeados()),
])
def test_los_guards_que_enumeran_con_git_PARAN_si_git_falla(monkeypatch, nombre, enumera):
    """Antes devolvían la lista vacía y el guard que la recorría daba verde sin mirar."""
    monkeypatch.setattr(subprocess, "run", _GitQueFalla())
    with pytest.raises(pytest.fail.Exception, match="not a git repository"):
        enumera()


def test_la_regla_del_gitignore_PARA_si_check_ignore_falla(monkeypatch):
    """Antes leía el fallo como «sin regla», como sus hermanas del mismo fichero no hacen."""
    monkeypatch.setattr(subprocess, "run", _GitQueFalla())
    with pytest.raises(RuntimeError, match="check-ignore"):
        gitignore._regla(".env")


def test_control_positivo_con_el_git_real():
    """La otra mitad: con el git de verdad, los mismos helpers miran algo."""
    assert len(gobernanza._md_trackeados()) > 100
    assert len(basetemp._trackeados()) > 1000
    assert isinstance(gobernanza._refs_a_docs_plan_legacy(), list)
    assert ".env" in gitignore._regla(".env")
