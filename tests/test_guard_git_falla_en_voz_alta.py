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


# --- session_close: la sonda ------------------------------------------------------------------
#
# Allí el remedio no es que cada llamada lance: `_git_count` usa un fallo por rama como respuesta
# legítima (una rama cuyo remoto ya no existe cuenta cero), y si lanzara, una sola rama así
# tumbaría el aviso de todas. Lo que se pregunta es UNA vez: ¿responde git en este árbol?

from scripts import session_close as sc  # noqa: E402


def test_la_sonda_dice_por_que_git_no_responde(monkeypatch):
    monkeypatch.setattr(subprocess, "run", _GitQueFalla())
    assert "not a git repository" in (sc._git_responde() or "")


def test_la_sonda_con_el_git_real_responde():
    assert sc._git_responde() is None


def test_sin_git_la_verja_corre_los_lentos_y_dice_por_que(monkeypatch):
    """Sin git no se sabe si `core/anon/` está tocado: saltarse los lentos era leer «no» donde
    había «no lo sé»."""
    def no_debe_preguntar():
        raise AssertionError("con git caído no se le pregunta a git por core/anon/")

    monkeypatch.setattr(sc, "_anon_tocado", no_debe_preguntar)
    corre_lentos, motivo = sc._modo_de_la_verja(False, NO_ES_REPO)
    assert corre_lentos is True
    assert "git no responde" in motivo and NO_ES_REPO in motivo


@pytest.mark.parametrize("forzado, tocado, esperado", [
    (True, False, True), (False, True, True), (False, False, False)])
def test_con_git_sano_el_modo_de_la_verja_no_cambia(monkeypatch, forzado, tocado, esperado):
    monkeypatch.setattr(sc, "_anon_tocado", lambda: tocado)
    assert sc._modo_de_la_verja(forzado, None)[0] is esperado


def test_un_aviso_que_depende_de_git_sale_como_NO_comprobado(capsys):
    llamado: list[int] = []
    sc._si_git_responde(NO_ES_REPO, "el trabajo sin publicar", lambda: llamado.append(1))
    assert llamado == []
    salida = capsys.readouterr().out
    assert sc.NO_COMPROBADO in salida and "el trabajo sin publicar" in salida


def test_con_git_sano_el_aviso_corre():
    llamado: list[int] = []
    sc._si_git_responde(None, "el trabajo sin publicar", lambda: llamado.append(1))
    assert llamado == [1]


def test_main_sin_git_corre_los_lentos_y_declara_los_avisos_que_no_comprueba(monkeypatch, capsys):
    """La cadena entera, con la suite puenteada: lo que se lee al cerrar con git caído."""
    monkeypatch.setattr(sc, "deps_que_faltan", lambda *a, **k: [])
    monkeypatch.setattr(sc, "_git_responde", lambda: NO_ES_REPO)
    verjas: list[list[str]] = []
    monkeypatch.setattr(sc, "correr_la_verja", lambda args: verjas.append(list(args)))
    monkeypatch.setattr(sc, "_anon_tocado", lambda: pytest.fail("no se pregunta a git"))
    sc.main()
    salida = capsys.readouterr().out
    assert verjas == [["--runslow"]], "sin git, la verja corre los lentos por si acaso"
    for que in sc.AVISOS_QUE_DEPENDEN_DE_GIT:
        assert f"{sc.NO_COMPROBADO} {que}" in salida, que
