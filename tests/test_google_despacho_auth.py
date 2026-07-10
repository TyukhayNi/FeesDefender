"""Tests de los helpers puros de google_auth (rutas y listado de cuentas).

El flujo OAuth interactivo (add_account) NO se testea aquí: requiere navegador.
Se aísla el HOME con la variable GOOGLE_DESPACHO_HOME apuntando a un tmp_path.
"""
from __future__ import annotations

import pytest

from plugins.google_despacho_mcp import google_auth


@pytest.fixture
def auth_home(tmp_path, monkeypatch):
    monkeypatch.setenv("GOOGLE_DESPACHO_HOME", str(tmp_path))
    return tmp_path


def test_config_home_crea_estructura(auth_home):
    base = google_auth.config_home()
    assert base == auth_home
    assert (auth_home / "tokens").is_dir()


def test_scope_es_drive_completo(auth_home):
    assert google_auth.SCOPES == ["https://www.googleapis.com/auth/drive"]


def test_list_account_emails_vacio_y_ordenado(auth_home):
    assert google_auth.list_account_emails() == []
    (auth_home / "tokens" / "b@tyukhay.legal.json").write_text("{}")
    (auth_home / "tokens" / "a@engelvoelkers.com.json").write_text("{}")
    assert google_auth.list_account_emails() == [
        "a@engelvoelkers.com",
        "b@tyukhay.legal",
    ]


def test_load_credentials_sin_token_da_error(auth_home):
    with pytest.raises(FileNotFoundError):
        google_auth.load_credentials("nadie@tyukhay.legal")


def test_remove_account_borra_existente_y_devuelve_true(auth_home):
    token = google_auth.tokens_dir() / "a@tyukhay.legal.json"
    token.write_text("{}")
    assert google_auth.remove_account("a@tyukhay.legal") is True
    assert not token.exists()


def test_remove_account_inexistente_devuelve_false(auth_home):
    assert google_auth.remove_account("nadie@tyukhay.legal") is False


def test_scope_es_drive_completo_f2():
    from plugins.google_despacho_mcp import google_auth
    assert google_auth.SCOPES == ["https://www.googleapis.com/auth/drive"]
