"""Aviso de cierre: trabajo grapado (commits) que no ha llegado al archivo central.

Prueba la lógica pura de detección (`_trabajo_sin_publicar`) monkeypatcheando las
dos consultas a git (`_git_lines` para enumerar ramas, `_git_count` para contar
commits por rango). Sin tocar git real.
"""

import scripts.session_close as sc


def _fake_lines(mapa):
    """Devuelve un _git_lines falso: mapea el 1er arg del comando a su salida."""
    def _inner(args):
        return mapa.get(args[0], [])
    return _inner


def test_detecta_rama_con_commits_sin_pushear(monkeypatch):
    # Una rama local con upstream, 3 commits por delante del archivo central.
    monkeypatch.setattr(
        sc, "_git_lines",
        _fake_lines({"for-each-ref": ["feat/x\torigin/feat/x"]}),
    )
    monkeypatch.setattr(
        sc, "_git_count",
        lambda rango: 3 if rango == ["origin/feat/x..feat/x"] else 0,
    )

    filas = sc._trabajo_sin_publicar()

    assert filas == [("feat/x", 3, "sin_publicar")]


def test_detecta_rama_nunca_subida(monkeypatch):
    # Rama local SIN upstream, con 5 commits propios sobre origin/main.
    monkeypatch.setattr(
        sc, "_git_lines",
        _fake_lines({"for-each-ref": ["feat/nueva\t"]}),
    )
    monkeypatch.setattr(
        sc, "_git_count",
        lambda rango: 5 if rango == ["origin/main..feat/nueva"] else 0,
    )

    filas = sc._trabajo_sin_publicar()

    assert filas == [("feat/nueva", 5, "nunca_subida")]


def test_nada_pendiente_cuando_todo_esta_publicado(monkeypatch):
    # Dos ramas, ambas al día con su upstream (0 commits por delante).
    monkeypatch.setattr(
        sc, "_git_lines",
        _fake_lines({"for-each-ref": [
            "main\torigin/main",
            "feat/y\torigin/feat/y",
        ]}),
    )
    monkeypatch.setattr(sc, "_git_count", lambda rango: 0)

    filas = sc._trabajo_sin_publicar()

    assert filas == []


def test_aviso_lista_ramas_y_recuerda_el_pr(monkeypatch, capsys):
    monkeypatch.setattr(sc, "_git_lines", _fake_lines({"branch": ["feat/x"]}))
    monkeypatch.setattr(
        sc, "_trabajo_sin_publicar",
        lambda: [("feat/x", 3, "sin_publicar")],
    )

    sc._avisar_publicacion()
    salida = capsys.readouterr().out

    assert "feat/x" in salida
    assert "3" in salida
    assert "PR" in salida  # recuerda la vía rama + PR


def test_aviso_sin_pendientes_dice_todo_publicado(monkeypatch, capsys):
    monkeypatch.setattr(sc, "_git_lines", _fake_lines({"branch": ["main"]}))
    monkeypatch.setattr(sc, "_trabajo_sin_publicar", lambda: [])

    sc._avisar_publicacion()
    salida = capsys.readouterr().out

    assert "main" in salida
    assert "sin commits sin publicar" in salida.lower() or "nada que llevar" in salida.lower()
