"""Los tres detectores cuyo modulo tiene un SEAM parcheado por tests (Task 6).

`core/anon/api.py` (x2) y `scripts/sala_maquina.py` son distintos del resto: sus
tests parchean el binding de modulo —`anon_api.caso_path`, y `cli.caso_path` en
**veinte** tests de sala de maquina— para montar el caso FUERA de `CASOS_ROOT`.

Migrarlos a `buscar()` repetiria el error del paso 3: un import dentro de la
funcion se salta el parche, y la guarda dispararia la rama elegante contra un caso
que SI existe. Aqui el patron es otro — capturar sobre **el binding del propio
modulo**, que sigue pasando por el parche:

    try:
        base = caso_path(case_id)
    except FileNotFoundError:
        return []                       # el caso no existe

Funciona porque `LocalWorkspaceMissing` **es** un `FileNotFoundError` desde que se
midio que 15 sitios de produccion capturaban ese tipo. Los dos hallazgos encajan:
la herencia que se puso para no romper manejadores es la que hace viable este
patron en los modulos con seam.

Hoy `caso_path` no lanza, asi que el `except` no se ejercita en produccion. Estos
tests lo ejercitan **simulando el paso 5**, que es la unica forma de que la rama
no nazca muerta.
"""
from __future__ import annotations

import importlib

import pytest


@pytest.fixture
def root(tmp_path, monkeypatch):
    r = tmp_path / "CASOS"
    r.mkdir()
    monkeypatch.setenv("CASOS_ROOT", str(r))
    from core import config as cfg
    importlib.reload(cfg)
    yield r


def _estricto(_case_id):
    """`caso_path` como quedara tras el paso 5."""
    from core.casos.workspace_model import LocalWorkspaceMissing
    raise LocalWorkspaceMissing(detalle="simulacion del paso 5")


class TestAnonApi:
    def test_variantes_no_propaga_con_el_localizador_estricto(self, root, monkeypatch):
        from core.anon import api as anon_api
        monkeypatch.setattr(anon_api, "caso_path", _estricto)
        assert anon_api._derivar_variantes_cliente("NO-EXISTE") == []

    def test_documentos_no_propaga_con_el_localizador_estricto(self, root, monkeypatch):
        from core.anon import api as anon_api
        monkeypatch.setattr(anon_api, "caso_path", _estricto)
        assert anon_api._listar_documentos("NO-EXISTE") == []

    def test_el_seam_sigue_funcionando(self, root, monkeypatch, tmp_path):
        """Lo que el paso 3 rompio: un caso FUERA de `CASOS_ROOT`, via parche.

        Si la guarda usara `buscar()` en vez del binding del modulo, este caso
        —que existe— se tratraria como ausente y devolveria vacio.
        """
        from core.anon import api as anon_api
        fuera = tmp_path / "fuera" / "BaRS9 - Prueba - (W-TEST99) - Vuelta"
        (fuera / "00_Input").mkdir(parents=True)
        (fuera / "00_Input" / "un_doc.pdf").write_bytes(b"x")
        monkeypatch.setattr(anon_api, "caso_path", lambda cid: fuera)
        assert anon_api._listar_documentos("W-TEST99") != [], (
            "la guarda se salto el parche: trato como ausente un caso que existe")


class TestSalaMaquina:
    def test_error_legible_con_el_localizador_estricto(self, root, monkeypatch):
        import scripts.sala_maquina as cli
        monkeypatch.setattr(cli, "caso_path", _estricto)
        import typer
        with pytest.raises(typer.Exit) as exc:
            cli._resolver_caso("NO-EXISTE")
        assert exc.value.exit_code == 1

    def test_el_error_no_publica_la_ruta_local(self, root, monkeypatch, capsys, tmp_path):
        """§16: el mensaje interpolaba `case_dir`, o sea la ruta absoluta."""
        import typer
        import scripts.sala_maquina as cli
        vacio = tmp_path / "vacio" / "BaRS9 - Prueba - (W-TEST99) - Vuelta"
        vacio.mkdir(parents=True)                      # existe, pero sin 00_Input
        monkeypatch.setattr(cli, "caso_path", lambda cid: vacio)
        with pytest.raises(typer.Exit):
            cli._resolver_caso("W-TEST99")
        err = capsys.readouterr().err
        assert str(tmp_path) not in err, err
