"""Tests del server MCP gmail-multiaccount vía build_server con service_factory
inyectado (sin API viva ni tokens). Comprueba enrutado account→service,
tools de lectura migradas y guardarraíles de etiquetado."""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest

pytest.importorskip("mcp")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gmail_mcp_fakes import FakeGmailService  # noqa: E402

from plugins.gmail_mcp import server as srv  # noqa: E402


def _tool(mcp, name):
    return mcp._tool_manager._tools[name].fn


# ------------------------------- lectura / DI -------------------------------

def test_build_server_es_fastmcp_y_se_renombra():
    mcp = srv.build_server(
        service_factory=lambda e: FakeGmailService(),
        account_lister=lambda: ["a@tyukhay.legal"],
    )
    assert mcp is not None
    assert mcp.name == "gmail-multiaccount"


def test_list_accounts_usa_lister():
    mcp = srv.build_server(
        service_factory=lambda e: FakeGmailService(),
        account_lister=lambda: ["a@tyukhay.legal", "b@engelvoelkers.com"],
    )
    assert _tool(mcp, "list_accounts")() == ["a@tyukhay.legal", "b@engelvoelkers.com"]


def test_search_messages_taggea_cada_cuenta():
    msg = {
        "id": "m1", "threadId": "t1",
        "payload": {"headers": [{"name": "Subject", "value": "Reserva"}]},
        "snippet": "hola", "labelIds": [],
    }
    shared = FakeGmailService(messages={"list": {"messages": [{"id": "m1"}]},
                                        "get": msg})
    mcp = srv.build_server(
        service_factory=lambda e: shared,
        account_lister=lambda: ["a@tyukhay.legal", "b@engelvoelkers.com"],
    )
    out = _tool(mcp, "search_messages")(query="reserva")
    assert sorted(r["account"] for r in out) == ["a@tyukhay.legal", "b@engelvoelkers.com"]
    assert all(r["subject"] == "Reserva" for r in out)


def test_resolve_accounts_sin_cuentas_da_error():
    with pytest.raises(RuntimeError):
        srv._resolve_accounts(None, lambda: [])


# ------------------------------- list_labels -------------------------------

def test_list_labels_devuelve_id_y_nombre_ordenado():
    labels = {"list": {"labels": [
        {"id": "Label_9", "name": "W-02XOR7", "type": "user"},
        {"id": "INBOX", "name": "INBOX", "type": "system"},
        {"id": "Label_1", "name": "Arras", "type": "user"},
    ]}}
    svc = FakeGmailService(labels=labels)
    mcp = srv.build_server(service_factory=lambda e: svc,
                           account_lister=lambda: ["a@tyukhay.legal"])
    out = _tool(mcp, "list_labels")(account="a@tyukhay.legal")
    assert out == {"a@tyukhay.legal": [
        {"id": "Label_1", "name": "Arras"},
        {"id": "INBOX", "name": "INBOX"},
        {"id": "Label_9", "name": "W-02XOR7"},
    ]}
