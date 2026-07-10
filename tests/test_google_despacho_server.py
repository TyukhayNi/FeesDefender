"""Tests del server MCP google-despacho vía build_server con service_factory
inyectado (sin API viva ni tokens). Comprueba enrutado account→service,
delegación a drive_ops y saneado del DL-root."""
from __future__ import annotations

import os
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


def test_search_files_taggea_cada_cuenta_sin_contaminar():
    # Aunque el service devuelva el MISMO objeto dict, cada resultado debe quedar
    # etiquetado con SU cuenta. Acceso a .fn: API privada de mcp (1.28.0);
    # puede requerir ajuste al subir de versión de mcp.
    shared = FakeService(files={"list": {"files": [{"id": "f1", "name": "a.pdf"}]}})
    mcp = srv.build_server(
        service_factory=lambda e: shared,
        account_lister=lambda: ["a@tyukhay.legal", "b@engelvoelkers.com"],
    )
    fn = mcp._tool_manager._tools["search_files"].fn
    out = fn(query="x")
    assert sorted(r["account"] for r in out) == ["a@tyukhay.legal", "b@engelvoelkers.com"]


def test_resolve_dest_rechaza_symlink_que_escapa(tmp_path, monkeypatch):
    root = tmp_path / "dl_root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    try:
        (root / "escape").symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks no soportados en este entorno")
    monkeypatch.setenv("GOOGLE_DESPACHO_DL_ROOT", str(root))
    with pytest.raises(ValueError):
        srv._resolve_dest(str(root / "escape" / "evil.bin"))


def test_resolve_upload_dentro_de_root(tmp_path, monkeypatch):
    root = tmp_path / "up"
    root.mkdir()
    f = root / "doc.pdf"
    f.write_bytes(b"x")
    monkeypatch.setenv("GOOGLE_DESPACHO_UPLOAD_ROOT", str(root))
    out = srv._resolve_upload(str(f))
    assert out == os.path.realpath(str(f))


def test_resolve_upload_fuera_de_root_rechaza(tmp_path, monkeypatch):
    root = tmp_path / "up"
    root.mkdir()
    fuera = tmp_path / "otro.pdf"
    fuera.write_bytes(b"x")
    monkeypatch.setenv("GOOGLE_DESPACHO_UPLOAD_ROOT", str(root))
    with pytest.raises(ValueError):
        srv._resolve_upload(str(fuera))


def test_resolve_upload_fichero_inexistente_rechaza(tmp_path, monkeypatch):
    monkeypatch.delenv("GOOGLE_DESPACHO_UPLOAD_ROOT", raising=False)
    with pytest.raises(FileNotFoundError):
        srv._resolve_upload(str(tmp_path / "no_existe.pdf"))
