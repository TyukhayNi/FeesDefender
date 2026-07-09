"""Tests del server MCP google-despacho vía build_server con service_factory
inyectado (sin API viva ni tokens). Comprueba enrutado account→service,
delegación a drive_ops y saneado del DL-root."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("mcp")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from google_despacho_fakes import FakeService  # noqa: E402

from plugins.google_despacho_mcp import server as srv  # noqa: E402


def _factory(mapping):
    """Devuelve un service_factory(email)->FakeService a partir de un dict."""
    def factory(email):
        if email not in mapping:
            raise FileNotFoundError(email)
        return mapping[email]
    return factory


def test_build_server_devuelve_fastmcp():
    mcp = srv.build_server(
        service_factory=lambda e: FakeService(),
        account_lister=lambda: ["a@tyukhay.legal"],
    )
    assert mcp is not None
    assert mcp.name == "google-despacho"


def test_resolve_dest_confina_a_dl_root(tmp_path, monkeypatch):
    monkeypatch.setenv("GOOGLE_DESPACHO_DL_ROOT", str(tmp_path))
    ok = srv._resolve_dest(str(tmp_path / "sub" / "a.bin"))
    assert Path(ok).is_absolute()
    with pytest.raises(ValueError):
        srv._resolve_dest(str(tmp_path.parent / "fuera.bin"))


def test_resolve_accounts_todas_si_omitido():
    lister = lambda: ["a@tyukhay.legal", "b@engelvoelkers.com"]
    assert srv._resolve_accounts(None, lister) == [
        "a@tyukhay.legal", "b@engelvoelkers.com"
    ]
    assert srv._resolve_accounts("a@tyukhay.legal", lister) == ["a@tyukhay.legal"]


def test_resolve_accounts_sin_cuentas_da_error():
    with pytest.raises(RuntimeError):
        srv._resolve_accounts(None, lambda: [])
