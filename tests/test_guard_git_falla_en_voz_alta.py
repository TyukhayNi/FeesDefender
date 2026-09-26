"""Git que falla en voz alta: un fallo de git no puede leerse como «no hay nada».

Lo vio la R1 de Codex de los estados medidos (2026-09-26): en la copia `git archive` sin `.git`
sobre la que trabajan los revisores, `git ls-files` falla, la lista sale vacía y los guards que la
recorren pasan en verde sin haber mirado nada. La frontera eran cinco sitios, no uno (plan
`docs/superpowers/plans/2026-09-26-git-que-falla-en-voz-alta.md`), y la R1 de esa pieza encontró
las otras formas del mismo «no pude mirar»: un código que es respuesta con un stderr que dice que
no leyó algo, una sonda que responde con las consultas rotas, y un paso de CI con la lista vacía.
"""
from __future__ import annotations

import contextlib
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from scripts import check_skills as cs
from tests import _git
from tests import test_docs_gobernanza as gobernanza
from tests import test_gitignore_no_inerte as gitignore
from tests import test_guard_no_basetemp_versionado as basetemp

ROOT = Path(__file__).resolve().parents[1]
NO_ES_REPO = "fatal: not a git repository (or any of the parent directories): .git"
# Lo que git dice cuando NO pudo leer algo y aun así sale con un código que es respuesta: medido
# por el revisor con git 2.53 y un fichero abierto en exclusiva (R1/H-04).
NO_PUDO_LEER = "error: failed to stat 'nota.md': Permission denied"
NO_PUDO_LEER_GITIGNORE = "warning: unable to access '.gitignore': Permission denied"
# Una cita a un plan heredado de `docs/`, para los laboratorios. Partida en dos a propósito: escrita
# de corrido, el guard de referencias heredadas acusaría a ESTE fichero (lo hizo, y tenía razón).
CITA_HEREDADA = "docs/" + "PLAN_PROHIBIDO.md"


class _GitQueFalla:
    """`subprocess.run` de un git que falla como en la copia sin `.git` de los revisores."""

    def __init__(self, rc: int = 128, stderr: str = NO_ES_REPO) -> None:
        self.rc, self.stderr = rc, stderr

    def __call__(self, args, **_kw):
        return subprocess.CompletedProcess(args, self.rc, stdout="", stderr=self.stderr)


@pytest.fixture
def lab_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Un repo de laboratorio sin la configuración de la máquina (ni `core.autocrlf`, ni
    `core.quotePath`, ni plantillas), con el aislamiento ACREDITADO antes de escribir en su
    índice: si `init` fallara y el directorio colgara de otro repo, se escribiría en el ajeno."""
    vacio = tmp_path / "_gitconfig_vacio"
    vacio.write_text("", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(vacio))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for var in ("GIT_DIR", "GIT_COMMON_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        monkeypatch.delenv(var, raising=False)
    lab = tmp_path / "lab"
    lab.mkdir()
    _git.git("init", "-q", "-b", "main", ".", cwd=lab)
    top = _git.git("rev-parse", "--show-toplevel", cwd=lab).stdout.strip()
    assert os.path.samefile(top, lab), f"el laboratorio no está aislado: git resuelve a {top}"
    return lab


@contextlib.contextmanager
def _bloqueado(ruta: Path):
    """Abre `ruta` en exclusiva (Windows, sin compartir): mientras dure, git no la puede leer.
    Es como el revisor reprodujo, con git de verdad, las lecturas que fallan con código válido."""
    import ctypes
    from ctypes import wintypes

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                                wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    k32.CreateFileW.restype = wintypes.HANDLE
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    generic_read, sin_compartir, open_existing, normal = 0x80000000, 0, 3, 0x80
    h = k32.CreateFileW(str(ruta), generic_read, sin_compartir, None, open_existing, normal, None)
    if h in (None, ctypes.c_void_p(-1).value):
        raise OSError(ctypes.get_last_error(), f"no se pudo abrir en exclusiva {ruta}")
    try:
        yield
    finally:
        k32.CloseHandle(h)


solo_windows = pytest.mark.skipif(sys.platform != "win32",
                                  reason="el bloqueo exclusivo de un fichero es de Windows")


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


@pytest.mark.parametrize("rc", [0, 1])
def test_el_helper_para_si_git_avisa_de_que_no_pudo_leer_algo(monkeypatch, rc):
    """R1/H-04: git puede no leer un fichero, decirlo por stderr y salir con un código que ES
    respuesta —`grep` con 1 («sin coincidencias») o con 0 si otro fichero sí casó—. Eso no es una
    respuesta completa: es «no pude mirar todo»."""
    monkeypatch.setattr(subprocess, "run", _GitQueFalla(rc=rc, stderr=NO_PUDO_LEER))
    with pytest.raises(pytest.fail.Exception, match="failed to stat"):
        _git.git("grep", "-l", "x", cwd=ROOT, rc_validos=(0, 1))


def test_trackeados_devuelve_la_ruta_tal_cual_aunque_lleve_tildes(lab_git):
    """Sin `-z`, git entrecomilla y escapa en octal las rutas con bytes no ASCII
    (`core.quotePath`): la ruta que se devolvía no existía en disco."""
    (lab_git / "año.md").write_text("x\n", encoding="utf-8")
    _git.git("add", "año.md", cwd=lab_git)
    assert _git.trackeados(lab_git) == ["año.md"]


# --- los guards de la frontera ------------------------------------------------------------------

@pytest.mark.parametrize("nombre, enumera", [
    ("test_docs_gobernanza._md_trackeados", lambda: gobernanza._md_trackeados()),
    ("test_docs_gobernanza._refs_a_docs_plan_legacy", lambda: gobernanza._refs_a_docs_plan_legacy()),
    ("test_guard_no_basetemp_versionado._trackeados", lambda: basetemp._trackeados()),
    ("test_gitignore_no_inerte._gitignores_trackeados", lambda: gitignore._gitignores_trackeados()),
])
@pytest.mark.parametrize("fallo", [_GitQueFalla(), _GitQueFalla(stderr="")],
                         ids=["con-stderr", "mudo"])
def test_los_guards_que_enumeran_con_git_PARAN_si_git_falla(monkeypatch, nombre, enumera, fallo):
    """Antes devolvían la lista vacía y el guard que la recorría daba verde sin mirar. El cuarto
    lo encontró la R1 (H-02): el guard de comentarios de `.gitignore` recorría un `ls-files` sin
    mirar su código. Y el fallo «mudo» —128 sin stderr— existe para que la regla del stderr no
    tape la del código: cada una tiene que valer sola."""
    monkeypatch.setattr(subprocess, "run", fallo)
    with pytest.raises(pytest.fail.Exception, match="rc=128"):
        enumera()


def test_la_regla_del_gitignore_PARA_si_check_ignore_falla(monkeypatch):
    """Antes leía el fallo como «sin regla», como sus hermanas del mismo fichero no hacen."""
    monkeypatch.setattr(subprocess, "run", _GitQueFalla())
    with pytest.raises(RuntimeError, match="check-ignore"):
        gitignore._regla(".env")


def test_la_consulta_suelta_de_check_ignore_PARA_si_git_falla(monkeypatch):
    """R1/H-02: `ignora()` convertía cualquier código distinto de 0 en «no ignorada»."""
    monkeypatch.setattr(subprocess, "run", _GitQueFalla())
    with pytest.raises(RuntimeError, match="check-ignore"):
        gitignore._ignora(".env", ROOT)


def test_la_decision_del_gitignore_PARA_si_git_no_pudo_leer_las_reglas(monkeypatch):
    """R1/H-04: con el `.gitignore` ilegible, `check-ignore` sale con 1 —«no ignorada»— y lo dice
    por stderr. Leído como respuesta, un fichero trackeado e ignorado dejaba de ser ofensor."""
    monkeypatch.setattr(subprocess, "run", _GitQueFalla(rc=1, stderr=NO_PUDO_LEER_GITIGNORE))
    with pytest.raises(RuntimeError, match="unable to access"):
        gitignore._regla(".env")
    with pytest.raises(RuntimeError, match="unable to access"):
        gitignore._ignorados([".env"], trackeados=[])


def test_control_positivo_con_el_git_real():
    """La otra mitad: con el git de verdad, los mismos helpers miran algo."""
    assert len(gobernanza._md_trackeados()) > 100
    assert len(basetemp._trackeados()) > 1000
    assert isinstance(gobernanza._refs_a_docs_plan_legacy(), list)
    assert ".env" in gitignore._regla(".env")
    assert (ROOT / ".gitignore") in gitignore._gitignores_trackeados()


def test_el_guard_de_referencias_ve_un_ofensor_real_y_respeta_sus_excepciones(lab_git):
    """El control positivo que faltaba (R1/H-06): con solo `isinstance(list)`, un
    `_refs_a_docs_plan_legacy` que devolviera siempre `[]` pasaba la suite entera. Y contra el
    corpus real no sirve contar coincidencias: las que hay hoy son justo las excepciones."""
    (lab_git / "nota.md").write_text(f"ver {CITA_HEREDADA}\n", encoding="utf-8")
    (lab_git / "limpio.md").write_text("nada que ver\n", encoding="utf-8")
    _git.git("add", "nota.md", "limpio.md", cwd=lab_git)
    refs = gobernanza._refs_a_docs_plan_legacy(lab_git)
    assert refs == ["nota.md"]
    assert gobernanza._ofensores_plan_legacy(refs + ["tests/test_docs_gobernanza.py"]) == ["nota.md"]


def test_el_guard_de_comentarios_ve_una_regla_muerta_real(lab_git):
    """R1/H-02: el guard final, con una regla ofensora de verdad en un `.gitignore` trackeado."""
    (lab_git / ".gitignore").write_text("build/ # esto mata la regla\n", encoding="utf-8")
    _git.git("add", ".gitignore", cwd=lab_git)
    assert gitignore._reglas_muertas(lab_git) == {".gitignore": [(1, "build/ # esto mata la regla")]}


def test_los_guards_leen_su_raiz_al_llamar_para_que_se_puedan_redirigir(lab_git, monkeypatch):
    """Quien redirige un guard parcheando su `ROOT` o su `REPO` —como hizo el revisor para
    reproducir sus hallazgos— tiene que seguir redirigiéndolo: una raíz por defecto ligada al
    definir la función seguiría mirando el repo real, y en silencio."""
    (lab_git / "nota.md").write_text(f"ver {CITA_HEREDADA}\n", encoding="utf-8")
    (lab_git / ".gitignore").write_text("build/ # esto mata la regla\n", encoding="utf-8")
    _git.git("add", "nota.md", ".gitignore", cwd=lab_git)
    monkeypatch.setattr(gobernanza, "ROOT", lab_git)
    monkeypatch.setattr(gitignore, "REPO", lab_git)
    assert gobernanza._refs_a_docs_plan_legacy() == ["nota.md"]
    assert list(gitignore._reglas_muertas()) == [".gitignore"]


@solo_windows
def test_un_ofensor_que_git_no_puede_leer_PARA_el_guard_de_referencias(lab_git):
    """El caso del revisor, con git de verdad (R1/H-04): el fichero que cita el plan heredado
    está bloqueado, `git grep` sale con 1 —«sin coincidencias»— y dice `failed to stat` por
    stderr. Antes, el guard daba verde."""
    ofensor = lab_git / "nota.md"
    ofensor.write_text(f"ver {CITA_HEREDADA}\n", encoding="utf-8")
    _git.git("add", "nota.md", cwd=lab_git)
    assert gobernanza._refs_a_docs_plan_legacy(lab_git) == ["nota.md"]  # legible: lo ve
    with _bloqueado(ofensor):
        with pytest.raises(pytest.fail.Exception, match="nota.md"):
            gobernanza._refs_a_docs_plan_legacy(lab_git)


@solo_windows
def test_un_gitignore_que_git_no_puede_leer_PARA_la_decision(lab_git):
    """El otro caso del revisor (R1/H-04): con el `.gitignore` bloqueado, `check-ignore` sale con
    1 y un fichero trackeado e ignorado dejaba de salir como regla inerte."""
    reglas = lab_git / ".gitignore"
    reglas.write_text("secreto.txt\n", encoding="utf-8")
    (lab_git / "secreto.txt").write_text("x\n", encoding="utf-8")
    _git.git("add", "-f", ".gitignore", "secreto.txt", cwd=lab_git)
    trackeados = [".gitignore", "secreto.txt"]
    assert gitignore._ignorados(["secreto.txt"], repo=lab_git, trackeados=trackeados) == [
        "secreto.txt"]  # legible: lo ve
    with _bloqueado(reglas):
        with pytest.raises(RuntimeError, match="gitignore"):
            gitignore._ignorados(["secreto.txt"], repo=lab_git, trackeados=trackeados)
        with pytest.raises(RuntimeError, match="gitignore"):
            gitignore._regla("secreto.txt", repo=lab_git)


# --- session_close: la sonda, y lo que la sonda no certifica ----------------------------------
#
# La sonda pregunta UNA vez si git responde: si no, se dice y cada aviso se declara sin intentarlo.
# Pero que responda a `rev-parse --git-dir` no dice que responda a todo —un índice o un objeto
# corruptos rompen `status` o `log` y dejan la sonda en pie (R1/H-05)—, así que cada consulta
# LANZA si falla, y cada consumidor declara su «no lo sé».

from scripts import session_close as sc  # noqa: E402

INDICE_ROTO = "fatal: index file corrupt"
OBJETO_ROTO = "fatal: bad object HEAD"
NO_PUDO_ABRIR = "warning: could not open directory 'core/anon/x/': Permission denied"


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


@pytest.mark.parametrize("fallo", [
    _GitQueFalla(stderr=INDICE_ROTO),
    _GitQueFalla(rc=0, stderr=NO_PUDO_ABRIR),
], ids=["codigo", "stderr"])
def test_una_consulta_que_falla_LANZA_en_vez_de_devolver_vacio(monkeypatch, fallo):
    """R1/H-05: `_git_lines` devolvía `[]` ante cualquier fallo, y `status`, `log` o las ramas
    vacías se leían como «nada». Y un stderr con código 0 es la misma lectura incompleta: `status`
    avisa del directorio que no pudo abrir y sigue."""
    monkeypatch.setattr(subprocess, "run", fallo)
    with pytest.raises(sc.ConsultaGitFallida, match=fallo.stderr[:20]):
        sc._git_lines(["status", "--porcelain"])


def test_sin_git_en_el_path_la_consulta_LANZA(monkeypatch):
    def sin_git(*_a, **_k):
        raise FileNotFoundError("git")

    monkeypatch.setattr(subprocess, "run", sin_git)
    with pytest.raises(sc.ConsultaGitFallida, match="no se pudo ejecutar"):
        sc._git_lines(["status", "--porcelain"])


def test_con_la_sonda_verde_y_status_roto_la_verja_corre_los_lentos(monkeypatch):
    """El caso del revisor: índice corrupto, `rev-parse --git-dir` responde y `status` no. Antes,
    modo RÁPIDO: se saltaban los lentos sin haber mirado si `core/anon/` estaba tocado."""
    monkeypatch.setattr(subprocess, "run", _GitQueFalla(stderr=INDICE_ROTO))
    corre_lentos, motivo = sc._modo_de_la_verja(False, None)
    assert corre_lentos is True
    assert "core/anon/" in motivo and INDICE_ROTO in motivo


def test_un_recuento_que_git_no_puede_hacer_no_es_un_cero(monkeypatch):
    monkeypatch.setattr(subprocess, "run", _GitQueFalla(stderr="fatal: bad revision"))
    assert sc._git_count(["origin/main..main"]) is None


def test_una_rama_con_el_upstream_desaparecido_se_nombra_y_no_se_cuenta(monkeypatch):
    """Un upstream `[gone]` —la rama remota se borró al mergear— es un estado que git DICE, no un
    fallo: se nombra aparte y no se le pide a `rev-list` un recuento que va a fallar."""
    monkeypatch.setattr(sc, "_git_lines",
                        lambda args: ["vieja\torigin/vieja\t[gone]", "viva\torigin/viva"])
    contados: list[list[str]] = []

    def contar(rango):
        contados.append(rango)
        return 2

    monkeypatch.setattr(sc, "_git_count", contar)
    assert sc._trabajo_sin_publicar() == [("vieja", None, "upstream_desaparecido"),
                                          ("viva", 2, "sin_publicar")]
    assert contados == [["origin/viva..viva"]]


def test_una_rama_que_git_no_puede_contar_sale_NO_comprobada(monkeypatch):
    """El otro caso del revisor: sin `origin/main`, `rev-list` falla y se contaba cero."""
    monkeypatch.setattr(sc, "_git_lines", lambda args: ["main"])
    monkeypatch.setattr(sc, "_git_count", lambda rango: None)
    assert sc._trabajo_sin_publicar() == [("main", None, "no_comprobada")]


def test_el_aviso_de_publicacion_no_dice_que_no_hay_nada_si_no_pudo_contar(monkeypatch, capsys):
    monkeypatch.setattr(sc, "_git_lines", lambda args: ["main"])
    monkeypatch.setattr(sc, "_trabajo_sin_publicar", lambda: [
        ("main", None, "no_comprobada"), ("vieja", None, "upstream_desaparecido")])
    sc._avisar_publicacion()
    salida = capsys.readouterr().out
    assert sc.NADA_SIN_PUBLICAR not in salida
    assert f"{sc.RAMA_NO_COMPROBADA} main" in salida
    assert sc.UPSTREAM_DESAPARECIDO in salida and "vieja" in salida


def test_main_con_la_sonda_verde_y_las_consultas_rotas_lo_declara_todo(monkeypatch, capsys):
    """El caso del revisor de punta a punta: un objeto corrupto deja en pie `rev-parse --git-dir`
    y rompe todo lo demás. La sonda no certifica el cierre: cada aviso declara lo que no miró, y
    ninguno dice «nada que avisar»."""
    monkeypatch.setattr(sc, "deps_que_faltan", lambda *a, **k: [])
    monkeypatch.setattr(sc, "_git_responde", lambda: None)
    verjas: list[list[str]] = []
    monkeypatch.setattr(sc, "correr_la_verja", lambda args: verjas.append(list(args)))
    monkeypatch.setattr(subprocess, "run", _GitQueFalla(stderr=OBJETO_ROTO))
    sc.main()
    salida = capsys.readouterr().out
    assert verjas == [["--runslow"]], "sin saber si core/anon/ está tocado, se corren los lentos"
    for que in (sc.AVISO_PUBLICACION, sc.AVISO_PLAN, sc.AVISO_TRAZA):
        assert f"{sc.NO_COMPROBADO} {que}" in salida, que
    for todo_en_orden in (sc.NADA_SIN_PUBLICAR, sc.NADA_EN_PLAN, sc.NADA_EN_TRAZA):
        assert todo_en_orden not in salida, todo_en_orden


# --- check_skills: el CHANGELOG que no se pudo mirar -------------------------------------------

def test_check_skills_PARA_la_consulta_si_git_falla(monkeypatch):
    """R1 §1: su `run()` devolvía `[]` ante un fallo, y «ninguna skill con el CHANGELOG sin
    actualizar» salía de no haber mirado ninguna."""
    monkeypatch.setattr(subprocess, "run", _GitQueFalla())
    with pytest.raises(cs.GitNoRespondio, match="not a git repository"):
        cs._git_changed_files()


def test_check_skills_declara_el_changelog_NO_comprobado_y_lo_cuenta(monkeypatch, capsys):
    monkeypatch.setattr(cs, "_git_changed_files", lambda: set())
    total_sano = cs.report()
    capsys.readouterr()

    def roto():
        raise cs.GitNoRespondio(f"git status --porcelain fallo (rc=128): {INDICE_ROTO}")

    monkeypatch.setattr(cs, "_git_changed_files", roto)
    total = cs.report()
    salida = capsys.readouterr().out
    linea = next(ln for ln in salida.splitlines() if "CHANGELOG sin actualizar" in ln)
    assert cs.CHANGELOG_NO_COMPROBADO in linea and INDICE_ROTO in linea
    assert total == total_sano + 1, "un chequeo que no corrió no puede acabar en «Todo en orden»"


@pytest.mark.parametrize("consulta, error", [
    pytest.param(lambda: _git.git("ls-files", cwd=ROOT), pytest.fail.Exception, id="tests-_git"),
    pytest.param(lambda: gitignore._consulta("ls-files", ["ls-files"], ROOT), RuntimeError,
                 id="gitignore"),
    pytest.param(lambda: sc._git_lines(["status", "--porcelain"]), sc.ConsultaGitFallida,
                 id="session_close"),
    pytest.param(lambda: cs._git_changed_files(), cs.GitNoRespondio, id="check_skills"),
])
def test_un_fallo_sin_stderr_tambien_para(monkeypatch, consulta, error):
    """Un git que sale con 128 sin decir nada: raro, y posible. Las cuatro consultas validadas
    miran código Y stderr, y esto comprueba que el código sigue valiendo solo."""
    monkeypatch.setattr(subprocess, "run", _GitQueFalla(stderr=""))
    with pytest.raises(error, match="rc=128"):
        consulta()


# --- CI: el paso de leak-scan, EJECUTADO ---------------------------------------------------------
#
# La primera versión de este test buscaba `set -o pipefail` en el texto, y un `set +o pipefail`
# detrás lo dejaba verde (R1/H-06). Ahora se ejecuta el bloque `run:` tal cual lo lee GitHub —con
# `bash -e`, que es como corre un `run:` sin `shell:`—, con un `git` falso y un `python` espía, y se
# mira el código del paso y si el escáner llegó a mirar algo.

WORKFLOW = ROOT / ".github" / "workflows" / "leak-scan.yml"


def _bash() -> Path | None:
    """Un bash como el del runner. En Windows, el que trae git —NUNCA el `bash.exe` de System32,
    que es WSL y ve otro sistema de ficheros—; fuera de Windows, `/bin/bash`."""
    if sys.platform != "win32":
        return Path("/bin/bash") if Path("/bin/bash").exists() else None
    r = subprocess.run(["git", "--exec-path"], capture_output=True, encoding="utf-8",
                       errors="replace")
    if r.returncode != 0:
        return None
    candidato = Path(r.stdout.strip()).parents[2] / "bin" / "bash.exe"
    return candidato if candidato.exists() else None


def _bloque_run_del_escaneo() -> str:
    flujo = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    pasos = [p for job in flujo["jobs"].values() for p in job["steps"]
             if "precommit_leak_guard.py" in p.get("run", "")]
    assert len(pasos) == 1, "el paso que escanea tiene que estar, y uno solo"
    return pasos[0]["run"]


_GIT_FALLA = "git() { echo 'fatal: not a git repository' >&2; return 128; }"
_GIT_LISTA_VACIA = "git() { return 0; }"
_GIT_UN_FICHERO = "git() { printf 'README.md\\0'; }"


@pytest.mark.parametrize("git, escaner_rc, blocklist, verde, escanea", [
    pytest.param(_GIT_FALLA, 0, "CANARIO", False, False, id="git-falla"),
    pytest.param(_GIT_LISTA_VACIA, 0, "CANARIO", False, False, id="lista-vacia-con-codigo-0"),
    pytest.param(_GIT_UN_FICHERO, 0, "CANARIO", True, True, id="escanea-y-limpio"),
    pytest.param(_GIT_UN_FICHERO, 1, "CANARIO", False, True, id="escanea-y-bloquea"),
    pytest.param(_GIT_UN_FICHERO, 0, "", False, False, id="sin-blocklist"),
])
def test_el_paso_de_ci_no_da_verde_sin_haber_escaneado(tmp_path, git, escaner_rc, blocklist,
                                                      verde, escanea):
    bash = _bash()
    if bash is None:
        pytest.skip("no hay un bash como el del runner en esta máquina")
    espia_dir = tmp_path / "bin"
    espia_dir.mkdir()
    espia = espia_dir / "python"
    espia.write_text('#!/bin/sh\nfor a in "$@"; do printf \'%s\\n\' "$a" >> escaneados.txt; done\n'
                     f"exit {escaner_rc}\n", encoding="utf-8", newline="\n")
    espia.chmod(0o755)
    preludio = (f'export PATH="$PWD/bin:$PATH"\nexport PII_BLOCKLIST="{blocklist}"\n{git}\n')
    guion = tmp_path / "paso.sh"
    guion.write_text(preludio + _bloque_run_del_escaneo(), encoding="utf-8", newline="\n")
    r = subprocess.run([str(bash), "--noprofile", "--norc", "-e", guion.name], cwd=tmp_path,
                       capture_output=True, encoding="utf-8", errors="replace")
    escaneados = tmp_path / "escaneados.txt"
    assert (r.returncode == 0) is verde, (r.returncode, r.stdout, r.stderr)
    assert escaneados.exists() is escanea, (r.stdout, r.stderr)
    if escanea:
        assert "README.md" in escaneados.read_text(encoding="utf-8").split()


def test_el_paso_de_ci_con_git_de_verdad_y_sin_indice_no_da_verde(lab_git):
    """El caso que el revisor midió con git real: sin índice, `git ls-files` sale con 0 y no lista
    nada. Con la tubería, el paso daba verde sin haber escaneado un solo fichero."""
    bash = _bash()
    if bash is None:
        pytest.skip("no hay un bash como el del runner en esta máquina")
    (lab_git / "README.md").write_text("x\n", encoding="utf-8")
    _git.git("add", "README.md", cwd=lab_git)
    (lab_git / ".git" / "index").unlink()
    espia_dir = lab_git / "bin"
    espia_dir.mkdir()
    (espia_dir / "python").write_text("#!/bin/sh\ntouch escaneados.txt\nexit 0\n",
                                      encoding="utf-8", newline="\n")
    guion = lab_git / "paso.sh"
    guion.write_text('export PATH="$PWD/bin:$PATH"\nexport PII_BLOCKLIST="CANARIO"\n'
                     + _bloque_run_del_escaneo(), encoding="utf-8", newline="\n")
    r = subprocess.run([str(bash), "--noprofile", "--norc", "-e", guion.name], cwd=lab_git,
                       capture_output=True, encoding="utf-8", errors="replace")
    assert r.returncode != 0, (r.stdout, r.stderr)
    assert not (lab_git / "escaneados.txt").exists()
