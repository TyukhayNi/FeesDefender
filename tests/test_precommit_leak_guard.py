"""Tests de la barrera local anti-fugas (scripts/precommit_leak_guard.py).

No usa PII real: la blocklist de prueba se fabrica en un repo temporal.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.precommit_leak_guard import cargar_blocklist, escanear


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Repo temporal con una replacements.txt sintética (literal + regex)."""
    saneado = tmp_path / "data" / "_saneado"
    saneado.mkdir(parents=True)
    (saneado / "replacements.txt").write_text(
        "Fulano Menganez==>PersonaX\n"
        "Alba==>PersonaY\n"
        r"regex:(?i)(?<![\w])Zutano\ Perez(?![\w@])==>PersonaZ" + "\n",
        encoding="utf-8",
    )
    return tmp_path


def _crea(repo: Path, rel: str, contenido: str) -> str:
    fp = repo / rel
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(contenido, encoding="utf-8")
    return rel


def test_blocklist_parsea_literal_y_regex(repo: Path):
    bl = cargar_blocklist(repo)
    assert "Fulano Menganez" in bl
    assert "Alba" in bl
    assert "Zutano Perez" in bl  # regex desenvuelto


def test_fichero_limpio_no_dispara(repo: Path):
    r = _crea(repo, "doc.md", "Reclamacion de honorarios W-02VND1, todo correcto.")
    assert escanear([r], repo) == []


def test_pii_literal_en_contenido_bloquea(repo: Path):
    r = _crea(repo, "nota.md", "Contrato firmado por Fulano Menganez el lunes.")
    problemas = escanear([r], repo)
    assert any("Fulano Menganez" in p for p in problemas)


def test_pii_regex_en_contenido_bloquea(repo: Path):
    r = _crea(repo, "acta.txt", "Declaro que Zutano Perez compareció.")
    problemas = escanear([r], repo)
    assert any("Zutano Perez" in p for p in problemas)


def test_limite_de_palabra_evita_falso_positivo(repo: Path):
    # 'Albacete' NO debe casar con el termino 'Alba'.
    r = _crea(repo, "viaje.md", "Fuimos a Albacete en verano.")
    assert escanear([r], repo) == []


def test_ruta_har_vetada_aunque_no_exista(repo: Path):
    problemas = escanear(["docs/captura/sesion.har"], repo)
    assert any("RUTA VETADA" in p for p in problemas)


def test_ruta_descubrimiento_vetada(repo: Path):
    r = _crea(repo, "docs/_descubrimiento/dump.json", "{}")
    problemas = escanear([r], repo)
    assert any("RUTA VETADA" in p for p in problemas)


def test_binario_no_se_escanea(repo: Path):
    fp = repo / "img.bin"
    fp.write_bytes(b"\x00\x01Fulano Menganez\x00")
    assert escanear(["img.bin"], repo) == []


def test_sin_blocklist_solo_rutas(fuera_de_git: Path):
    # Carpeta sin replacements.txt y fuera de todo repo (fixture `fuera_de_git`, R1/H-06: desde
    # MEJORAS #161 el guard pregunta a git, y un temporal colgado de un repo con lista lo
    # encontraría): no hay escaneo de PII, pero las rutas siguen vetadas.
    tmp_path = fuera_de_git
    assert cargar_blocklist(tmp_path) == []
    r = _crea(tmp_path, "nota.md", "Fulano Menganez")
    assert escanear([r], tmp_path) == []  # sin blocklist, no dispara por contenido
    assert escanear(["x.har"], tmp_path)  # ruta sigue vetada


# ── MEJORAS #161: la lista se resuelve desde el checkout principal, y su ausencia se declara ──
#
# Un worktree no tiene los ficheros gitignored; hasta el 2026-09-05 el guard pasaba en verde
# sin haber comprobado nada. Estos tests fabrican repositorios git REALES, porque la frontera
# es «qué contesta git», no un mock de ello. Y aíslan a git del entorno de la máquina (R1/H-05,
# H-06): sin ese aislamiento la fixture heredaba `commit.gpgsign=true` de la config global —y
# fallaba con 128 en cualquier sandbox sin la clave— y los tests «fuera de git» dependían de
# que el temporal de pytest no colgara de un repositorio.

import os
import subprocess

import yaml

from scripts.precommit_leak_guard import (
    Blocklist,
    aviso_blocklist_vacia,
    main,
    raices_blocklist,
    resolver_blocklist,
    rutas_blocklist,
)

REPO_REAL = Path(__file__).resolve().parent.parent


@pytest.fixture
def git_aislado(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Git sin la configuración global/sistema ni la plantilla de hooks de la máquina, sin
    variables que lo redirijan a otro repo, y con `GIT_CEILING_DIRECTORIES` en `tmp_path`:
    por encima de ahí no descubre repositorios, así que «fuera de git» es un estado que se
    CONSTRUYE, no que se supone. Devuelve `tmp_path`."""
    vacio = tmp_path / "_gitconfig_vacio"
    vacio.write_text("", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(vacio))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    monkeypatch.setenv("GIT_TEMPLATE_DIR", str(tmp_path / "_plantilla_vacia"))
    (tmp_path / "_plantilla_vacia").mkdir()
    for var in ("GIT_DIR", "GIT_COMMON_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        monkeypatch.delenv(var, raising=False)
    # Los CINCO canales por los que git recibe configuración: sistema, global, local (el del
    # repo sintético, que es nuestro), `-c` (no aplica) y el ENTORNO — `GIT_CONFIG_PARAMETERS`
    # y `GIT_CONFIG_COUNT` + `GIT_CONFIG_KEY_n`/`VALUE_n`. Cerrar solo global y sistema deja
    # abierto el quinto, y por ahí volvía a entrar `commit.gpgsign=true` (R1/H-05).
    for var in [v for v in os.environ if v.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_"))]:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.delenv("GIT_CONFIG_COUNT", raising=False)
    monkeypatch.delenv("GIT_CONFIG_PARAMETERS", raising=False)
    monkeypatch.setenv("GIT_AUTHOR_NAME", "t")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "t@example.invalid")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "t")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "t@example.invalid")
    return tmp_path


def _git(cwd: Path, *args: str) -> str:
    out = subprocess.run(
        ["git", *args], cwd=str(cwd), capture_output=True, encoding="utf-8",
        errors="replace", check=False,
    )
    assert out.returncode == 0, f"git {' '.join(args)} en {cwd}: {out.stderr}"
    return out.stdout.strip()


def _repo_con_lista(raiz: Path, *terminos: str) -> None:
    raiz.mkdir(parents=True, exist_ok=True)
    _git(raiz, "init", "-q", "-b", "main")
    (raiz / ".gitignore").write_text("data/\n", encoding="utf-8")
    _git(raiz, "add", ".gitignore")
    _git(raiz, "commit", "-q", "-m", "init")
    if terminos:
        cfg = raiz / "data" / "_config"
        cfg.mkdir(parents=True)
        (cfg / "pii_blocklist.txt").write_text(
            "# lista\n" + "\n".join(terminos) + "\n", encoding="utf-8"
        )


@pytest.fixture
def repo_con_worktree(git_aislado: Path) -> tuple[Path, Path]:
    """(raíz principal, worktree) de un repo git real. La blocklist SOLO está en la raíz."""
    raiz = git_aislado / "principal"
    _repo_con_lista(raiz, "Fulano Menganez")
    wt = git_aislado / "wt"
    _git(raiz, "worktree", "add", "-q", str(wt), "-b", "rama")
    return raiz, wt


@pytest.fixture
def fuera_de_git(git_aislado: Path) -> Path:
    """Carpeta que git NO puede asociar a ningún repositorio, aunque `tmp_path` cuelgue de uno
    (R1/H-06): el techo de descubrimiento es `tmp_path`."""
    solo = git_aislado / "suelto"
    solo.mkdir()
    return solo


# --- (P1) resolución del checkout principal ---------------------------------------------------

def test_worktree_resuelve_la_blocklist_desde_el_principal(repo_con_worktree):
    raiz, wt = repo_con_worktree
    assert not (wt / "data").exists()  # el worktree no tiene los gitignored
    assert raices_blocklist(wt) == [wt, raiz.resolve()]
    assert "Fulano Menganez" in cargar_blocklist(wt)
    assert resolver_blocklist(wt).principal.startswith("resuelto: ")


def test_principal_no_se_lee_dos_veces(repo_con_worktree):
    raiz, _ = repo_con_worktree
    bl = resolver_blocklist(raiz)
    assert bl.raices == [raiz]
    assert bl.principal == "este árbol ES el checkout principal"


def test_fuera_de_git_solo_la_raiz_dada(fuera_de_git: Path):
    bl = resolver_blocklist(fuera_de_git)
    assert bl.raices == [fuera_de_git]
    assert bl.terminos == []
    assert "no se pudo consultar git" in bl.principal


def test_union_de_terminos_de_ambas_raices(repo_con_worktree):
    raiz, wt = repo_con_worktree
    saneado = wt / "data" / "_saneado"
    saneado.mkdir(parents=True)
    (saneado / "replacements.txt").write_text("Zutano Perez==>PersonaZ\n", encoding="utf-8")
    bl = cargar_blocklist(wt)
    assert "Fulano Menganez" in bl and "Zutano Perez" in bl


def test_git_dir_separado_no_se_toma_la_carpeta_de_metadatos_por_checkout(git_aislado: Path):
    """R1/H-02: con `--separate-git-dir`, el padre de los metadatos NO es un checkout. Antes se
    leía como si lo fuera (y podía cargar una lista ajena que viviera allí). Ahora el principal
    queda «no determinado» y se dice; la lista ajena no entra."""
    storage = git_aislado / "storage"
    storage.mkdir()
    (storage / "data" / "_config").mkdir(parents=True)
    (storage / "data" / "_config" / "pii_blocklist.txt").write_text("Lista Ajena\n", encoding="utf-8")
    sep = git_aislado / "separate"
    sep.mkdir()
    _git(sep, "init", "-q", "-b", "main", "--separate-git-dir", str(storage / "metadata"))
    _git(sep, "commit", "-q", "--allow-empty", "-m", "init")
    wt = git_aislado / "sep_wt"
    _git(sep, "worktree", "add", "-q", str(wt), "-b", "rama")
    bl = resolver_blocklist(wt)
    assert "Lista Ajena" not in bl.terminos
    assert storage not in [r.resolve() for r in bl.raices]
    assert bl.raices == [wt]
    assert not bl.principal.startswith("resuelto")


def test_repo_bare_no_inventa_checkout(git_aislado: Path):
    bare = git_aislado / "bare.git"
    bare.mkdir()
    _git(bare, "init", "-q", "--bare")
    bl = resolver_blocklist(bare)
    assert bl.raices == [bare]
    assert "bare" in bl.principal


def test_git_dir_ajeno_en_el_entorno_no_redirige(repo_con_worktree, git_aislado, monkeypatch):
    """R1/P1: `GIT_DIR` apuntando a OTRO repositorio se ignora; el repo lo fija el árbol."""
    raiz, wt = repo_con_worktree
    otro = git_aislado / "otro"
    _repo_con_lista(otro, "Termino Del Otro Repo")
    monkeypatch.setenv("GIT_DIR", str(otro / ".git"))
    bl = resolver_blocklist(wt)
    assert "Fulano Menganez" in bl.terminos
    assert "Termino Del Otro Repo" not in bl.terminos


# --- (P2) la ausencia se declara, y describe la misma carga que el escaneo ----------------------

def test_mutante_161_termino_conocido_commiteado_desde_worktree_bloquea(repo_con_worktree, capsys):
    """El mutante que MEJORAS #161 describe: commitear un término de la lista desde un
    worktree sin la lista. Antes: verde y en silencio. Ahora: bloquea."""
    _, wt = repo_con_worktree
    r = _crea(wt, "nota.md", "Reunión con Fulano Menganez.")
    assert main(["guard", r], repo=wt) == 1
    err = capsys.readouterr().err
    assert "Fulano Menganez" in err
    assert "blocklist VACÍA" not in err


def test_sin_blocklist_en_ninguna_raiz_main_lo_declara(fuera_de_git: Path, capsys):
    r = _crea(fuera_de_git, "nota.md", "Texto limpio.")
    assert main(["guard", r], repo=fuera_de_git) == 0  # no falla cerrado (todavía)
    err = capsys.readouterr().err
    assert "blocklist VACÍA" in err
    assert "NO se ha ejecutado" in err
    for ruta in rutas_blocklist(fuera_de_git):
        assert str(ruta) in err
    assert "no existe" in err
    assert "no se pudo consultar git" in err


def test_con_blocklist_main_no_avisa(repo: Path, git_aislado, capsys):
    r = _crea(repo, "doc.md", "Texto limpio.")
    assert main(["guard", r], repo=repo) == 0
    assert "blocklist VACÍA" not in capsys.readouterr().err


def test_aviso_distingue_no_existe_de_existe_sin_terminos(repo_con_worktree):
    """R1/H-04: el aviso no afirma «el principal tampoco la tiene» sin haberlo mirado; dice
    por ruta lo observado."""
    raiz, wt = repo_con_worktree
    (raiz / "data" / "_config" / "pii_blocklist.txt").write_text("# solo\nAna\nLi\n", encoding="utf-8")
    bl = resolver_blocklist(wt)
    assert bl.terminos == []
    texto = aviso_blocklist_vacia(bl)
    estados = dict(bl.rutas)
    assert estados[raiz.resolve() / "data" / "_config" / "pii_blocklist.txt"].startswith("existe, 0 términos")
    assert estados[raiz.resolve() / "data" / "_saneado" / "replacements.txt"] == "no existe"
    # TODAS las rutas del worktree —los dos ficheros— dicen «no existe»: la frontera es el
    # estado por ruta, no el de un fichero concreto (un mutante que fijaba el estado de
    # replacements.txt sobrevivió a la primera versión de este test).
    del_wt = {r: e for r, e in estados.items() if r.is_relative_to(wt)}
    assert len(del_wt) == 2 and set(del_wt.values()) == {"no existe"}
    assert "existe, 0 términos utilizables" in texto and "no existe" in texto
    assert "tampoco la tiene" not in texto
    assert len(bl.rutas) == 4  # dos ficheros × dos raíces
    for ruta, _ in bl.rutas:
        assert str(ruta) in texto


def test_main_resuelve_la_blocklist_una_sola_vez(repo_con_worktree, monkeypatch, capsys):
    """R1/H-03: el aviso y el escaneo describen la MISMA carga. Con dos cargas independientes,
    un fallo transitorio entre ambas dejaba pasar el término sin aviso."""
    _, wt = repo_con_worktree
    import scripts.precommit_leak_guard as plg

    llamadas = []
    original = plg.resolver_blocklist

    def contada(repo):
        llamadas.append(repo)
        return original(repo)

    monkeypatch.setattr(plg, "resolver_blocklist", contada)
    r = _crea(wt, "nota.md", "Reunión con Fulano Menganez.")
    assert plg.main(["guard", r], repo=wt) == 1
    assert len(llamadas) == 1


def test_escanear_usa_la_blocklist_que_le_pasan(tmp_path: Path):
    bl = Blocklist(["Termino Inyectado"], [tmp_path], [], "inyectada")
    r = _crea(tmp_path, "nota.md", "Aparece Termino Inyectado aquí.")
    assert any("Termino Inyectado" in p for p in escanear([r], tmp_path, bl))


# --- (H-01) el aviso tiene que LLEGAR: el hook es verbose ---------------------------------------

def test_hook_leak_guard_es_verbose_para_que_el_aviso_se_vea():
    """pre-commit solo muestra la salida de un hook que devuelve 0 si el hook es `verbose`
    (`pre_commit/commands/run.py`). Sin esto, (P2) es cosmética."""
    cfg = yaml.safe_load((REPO_REAL / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
    hooks = [h for r in cfg["repos"] for h in r.get("hooks", []) if h.get("id") == "leak-guard"]
    assert len(hooks) == 1
    assert hooks[0].get("verbose") is True
