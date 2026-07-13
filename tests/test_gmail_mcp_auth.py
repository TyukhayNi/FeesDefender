"""Auth del MCP gmail: scope fijado a gmail.modify y config-home configurable."""
from __future__ import annotations

from pathlib import Path

from plugins.gmail_mcp import gmail_auth


def test_scope_es_gmail_modify():
    # Único scope, deliberadamente fijado (no readonly, no mail.google.com).
    assert gmail_auth.SCOPES == ["https://www.googleapis.com/auth/gmail.modify"]


def test_config_home_respeta_env(tmp_path, monkeypatch):
    monkeypatch.setenv("GMAIL_MCP_HOME", str(tmp_path / "cfg"))
    home = gmail_auth.config_home()
    assert home == Path(tmp_path / "cfg")
    assert (home / "tokens").is_dir()


def test_config_home_por_defecto(monkeypatch):
    monkeypatch.delenv("GMAIL_MCP_HOME", raising=False)
    assert gmail_auth.config_home() == Path.home() / ".gmail-mcp"
