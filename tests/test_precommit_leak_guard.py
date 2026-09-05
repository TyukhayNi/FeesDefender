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


def test_sin_blocklist_solo_rutas(tmp_path: Path):
    # Repo sin replacements.txt: no hay escaneo de PII, pero las rutas siguen vetadas.
    assert cargar_blocklist(tmp_path) == []
    r = _crea(tmp_path, "nota.md", "Fulano Menganez")
    assert escanear([r], tmp_path) == []  # sin blocklist, no dispara por contenido
    assert escanear(["x.har"], tmp_path)  # ruta sigue vetada


# ── MEJORAS #161: la lista se resuelve desde la raíz común, y su ausencia se declara ──────
#
# Un worktree no tiene los ficheros gitignored; hasta el 2026-09-05 el guard pasaba en verde
# sin haber comprobado nada. Estos tests fabrican un repositorio git REAL con un worktree,
# porque la frontera es «qué contesta `git rev-parse --git-common-dir`», no un mock de ello.

import subprocess

from scripts.precommit_leak_guard import (
    aviso_blocklist_vacia,
    main,
    raices_blocklist,
    rutas_blocklist,
)


def _git(cwd: Path, *args: str) -> str:
    out = subprocess.run(
        ["git", *args], cwd=str(cwd), capture_output=True, encoding="utf-8",
        errors="replace", check=True,
    )
    return out.stdout.strip()


@pytest.fixture
def repo_con_worktree(tmp_path: Path) -> tuple[Path, Path]:
    """(raíz principal, worktree) de un repo git real. La blocklist SOLO está en la raíz."""
    raiz = tmp_path / "principal"
    raiz.mkdir()
    _git(raiz, "init", "-q", "-b", "main")
    _git(raiz, "config", "user.email", "t@example.invalid")
    _git(raiz, "config", "user.name", "t")
    (raiz / ".gitignore").write_text("data/\n", encoding="utf-8")
    _git(raiz, "add", ".gitignore")
    _git(raiz, "commit", "-q", "-m", "init")
    cfg = raiz / "data" / "_config"
    cfg.mkdir(parents=True)
    (cfg / "pii_blocklist.txt").write_text("# lista\nFulano Menganez\n", encoding="utf-8")
    wt = tmp_path / "wt"
    _git(raiz, "worktree", "add", "-q", str(wt), "-b", "rama")
    return raiz, wt


def test_worktree_resuelve_la_blocklist_desde_la_raiz_comun(repo_con_worktree):
    raiz, wt = repo_con_worktree
    assert not (wt / "data").exists()  # el worktree no tiene los gitignored
    assert raices_blocklist(wt) == [wt, raiz.resolve()]
    assert "Fulano Menganez" in cargar_blocklist(wt)


def test_raiz_principal_no_se_lee_dos_veces(repo_con_worktree):
    raiz, _ = repo_con_worktree
    assert raices_blocklist(raiz) == [raiz]


def test_fuera_de_git_solo_la_raiz_dada(tmp_path: Path):
    solo = tmp_path / "suelto"
    solo.mkdir()
    assert raices_blocklist(solo) == [solo]
    assert cargar_blocklist(solo) == []


def test_union_de_terminos_de_ambas_raices(repo_con_worktree):
    raiz, wt = repo_con_worktree
    saneado = wt / "data" / "_saneado"
    saneado.mkdir(parents=True)
    (saneado / "replacements.txt").write_text("Zutano Perez==>PersonaZ\n", encoding="utf-8")
    bl = cargar_blocklist(wt)
    assert "Fulano Menganez" in bl and "Zutano Perez" in bl


def test_mutante_161_termino_conocido_commiteado_desde_worktree_bloquea(repo_con_worktree, capsys):
    """El mutante que MEJORAS #161 describe: commitear un término de la lista desde un
    worktree sin la lista. Antes: verde y en silencio. Ahora: bloquea."""
    _, wt = repo_con_worktree
    r = _crea(wt, "nota.md", "Reunión con Fulano Menganez.")
    assert main(["guard", r], repo=wt) == 1
    err = capsys.readouterr().err
    assert "Fulano Menganez" in err
    assert "blocklist VACÍA" not in err


def test_sin_blocklist_en_ninguna_raiz_main_lo_declara(tmp_path: Path, capsys):
    solo = tmp_path / "suelto"
    solo.mkdir()
    r = _crea(solo, "nota.md", "Texto limpio.")
    assert main(["guard", r], repo=solo) == 0  # no falla cerrado (todavía)
    err = capsys.readouterr().err
    assert "blocklist VACÍA" in err
    assert "NO se ha ejecutado" in err
    for ruta in rutas_blocklist(solo):
        assert str(ruta) in err


def test_con_blocklist_main_no_avisa(repo: Path, capsys):
    r = _crea(repo, "doc.md", "Texto limpio.")
    assert main(["guard", r], repo=repo) == 0
    assert "blocklist VACÍA" not in capsys.readouterr().err


def test_aviso_nombra_todas_las_rutas_buscadas(repo_con_worktree):
    raiz, wt = repo_con_worktree
    texto = aviso_blocklist_vacia(wt)
    rutas = rutas_blocklist(wt)
    assert len(rutas) == 4  # dos ficheros × dos raíces
    for ruta in rutas:
        assert str(ruta) in texto
