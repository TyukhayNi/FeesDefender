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


# ------------------------------- guardarraíles -------------------------------

_USER_LABELS = {"list": {"labels": [
    {"id": "Label_1", "name": "W-02XOR7", "type": "user"},
    {"id": "INBOX", "name": "INBOX", "type": "system"},
    {"id": "CATEGORY_PROMOTIONS", "name": "CATEGORY_PROMOTIONS", "type": "system"},
]}}


def test_resolve_user_label_por_id():
    svc = FakeGmailService(labels=_USER_LABELS)
    match = srv._resolve_user_label(svc, "Label_1")
    assert match["id"] == "Label_1" and match["name"] == "W-02XOR7"


def test_resolve_user_label_por_nombre():
    svc = FakeGmailService(labels=_USER_LABELS)
    match = srv._resolve_user_label(svc, "W-02XOR7")
    assert match["id"] == "Label_1"


def test_resolve_user_label_inexistente_error():
    svc = FakeGmailService(labels=_USER_LABELS)
    with pytest.raises(ValueError):
        srv._resolve_user_label(svc, "NoExiste")


def test_resolve_user_label_sistema_rechazado_por_type():
    svc = FakeGmailService(labels=_USER_LABELS)
    with pytest.raises(ValueError):
        srv._resolve_user_label(svc, "INBOX")


def test_resolve_user_label_category_rechazado():
    svc = FakeGmailService(labels=_USER_LABELS)
    with pytest.raises(ValueError):
        srv._resolve_user_label(svc, "CATEGORY_PROMOTIONS")


def test_resolve_user_label_ambigua_id_y_nombre_error():
    # `Alpha` casa como id de una etiqueta y como nombre de otra distinta:
    # fail-closed (spec §6), no elegir silenciosamente una.
    labels = {"list": {"labels": [
        {"id": "Label_1", "name": "Alpha", "type": "user"},
        {"id": "Alpha", "name": "Beta", "type": "user"},
    ]}}
    svc = FakeGmailService(labels=labels)
    with pytest.raises(ValueError):
        srv._resolve_user_label(svc, "Alpha")


def test_solo_tools_permitidas_registradas():
    # Blinda el guardarraíl §3/§9: NUNCA debe aparecer una tool de borrado/envío/
    # archivado. Una edición futura que registre delete_*/send_* rompe este test.
    mcp = srv.build_server(service_factory=lambda e: FakeGmailService(),
                           account_lister=lambda: [])
    assert set(mcp._tool_manager._tools) == {
        "list_accounts", "search_messages", "read_message", "read_thread",
        "list_labels", "list_attachments", "get_attachment",
        "create_label", "apply_label", "remove_label", "rename_label",
    }


# ------------------------------- create_label -------------------------------

def test_create_label_idempotente_si_existe():
    svc = FakeGmailService(labels={"list": {"labels": [
        {"id": "Label_1", "name": "W-02XOR7", "type": "user"}]}})
    mcp = srv.build_server(service_factory=lambda e: svc,
                           account_lister=lambda: ["a@tyukhay.legal"])
    out = _tool(mcp, "create_label")(account="a@tyukhay.legal", name="W-02XOR7")
    assert out["id"] == "Label_1" and out["created"] is False
    # No debe haber llamado a labels().create
    assert not any(m == "create" for m, _ in svc.recorded("labels"))


def test_create_label_crea_si_no_existe():
    svc = FakeGmailService(labels={
        "list": {"labels": []},
        "create": {"id": "Label_new", "name": "W-99", "type": "user"}})
    mcp = srv.build_server(service_factory=lambda e: svc,
                           account_lister=lambda: ["a@tyukhay.legal"])
    out = _tool(mcp, "create_label")(account="a@tyukhay.legal", name="W-99")
    assert out["id"] == "Label_new" and out["created"] is True
    assert any(m == "create" for m, _ in svc.recorded("labels"))


def test_create_label_rechaza_nombre_de_sistema():
    svc = FakeGmailService(labels={"list": {"labels": []}})
    mcp = srv.build_server(service_factory=lambda e: svc,
                           account_lister=lambda: ["a@tyukhay.legal"])
    tool = _tool(mcp, "create_label")
    for bad in ["INBOX", "inbox", "CATEGORY_X", "TRASH"]:
        with pytest.raises(ValueError):
            tool(account="a@tyukhay.legal", name=bad)


def test_create_label_account_obligatorio():
    svc = FakeGmailService(labels={"list": {"labels": []}})
    mcp = srv.build_server(service_factory=lambda e: svc,
                           account_lister=lambda: ["a@tyukhay.legal"])
    fn = _tool(mcp, "create_label")
    assert inspect.signature(fn).parameters["account"].default is inspect._empty


# ------------------------------- apply_label -------------------------------

def _label_svc(**extra):
    """FakeGmailService con etiquetas de usuario + respuestas de modify."""
    labels = {"list": {"labels": [
        {"id": "Label_1", "name": "W-02XOR7", "type": "user"},
        {"id": "INBOX", "name": "INBOX", "type": "system"},
    ]}}
    return FakeGmailService(labels=labels, **extra)


def test_apply_label_a_mensaje_por_id():
    svc = _label_svc(messages={"modify": {"id": "m1", "labelIds": ["Label_1"]}})
    mcp = srv.build_server(service_factory=lambda e: svc,
                           account_lister=lambda: ["a@tyukhay.legal"])
    out = _tool(mcp, "apply_label")(account="a@tyukhay.legal", label="Label_1",
                                    target_id="m1", target_type="message")
    assert out["label_id"] == "Label_1" and out["action"] == "apply"
    assert out["target_type"] == "message"
    method, kwargs = svc.recorded("messages")[-1]
    assert method == "modify"
    assert kwargs["body"] == {"addLabelIds": ["Label_1"]}
    assert kwargs["id"] == "m1"


def test_apply_label_por_nombre_resuelve_id():
    svc = _label_svc(messages={"modify": {"id": "m1", "labelIds": ["Label_1"]}})
    mcp = srv.build_server(service_factory=lambda e: svc,
                           account_lister=lambda: ["a@tyukhay.legal"])
    out = _tool(mcp, "apply_label")(account="a@tyukhay.legal", label="W-02XOR7",
                                    target_id="m1", target_type="message")
    assert out["label_id"] == "Label_1"


def test_apply_label_a_hilo():
    svc = _label_svc(threads={"modify": {"id": "t1", "labelIds": ["Label_1"]}})
    mcp = srv.build_server(service_factory=lambda e: svc,
                           account_lister=lambda: ["a@tyukhay.legal"])
    out = _tool(mcp, "apply_label")(account="a@tyukhay.legal", label="Label_1",
                                    target_id="t1", target_type="thread")
    method, kwargs = svc.recorded("threads")[-1]
    assert method == "modify" and kwargs["body"] == {"addLabelIds": ["Label_1"]}
    assert out["target_type"] == "thread"


def test_apply_label_nombre_inexistente_error():
    svc = _label_svc()
    mcp = srv.build_server(service_factory=lambda e: svc,
                           account_lister=lambda: ["a@tyukhay.legal"])
    with pytest.raises(ValueError):
        _tool(mcp, "apply_label")(account="a@tyukhay.legal", label="NoExiste",
                                  target_id="m1", target_type="message")


def test_apply_label_sistema_rechazado():
    svc = _label_svc()
    mcp = srv.build_server(service_factory=lambda e: svc,
                           account_lister=lambda: ["a@tyukhay.legal"])
    with pytest.raises(ValueError):
        _tool(mcp, "apply_label")(account="a@tyukhay.legal", label="INBOX",
                                  target_id="m1", target_type="message")


def test_apply_label_target_type_invalido_error():
    svc = _label_svc()
    mcp = srv.build_server(service_factory=lambda e: svc,
                           account_lister=lambda: ["a@tyukhay.legal"])
    with pytest.raises(ValueError):
        _tool(mcp, "apply_label")(account="a@tyukhay.legal", label="Label_1",
                                  target_id="x", target_type="foo")


def test_apply_label_account_obligatorio():
    svc = _label_svc()
    mcp = srv.build_server(service_factory=lambda e: svc,
                           account_lister=lambda: ["a@tyukhay.legal"])
    fn = _tool(mcp, "apply_label")
    assert inspect.signature(fn).parameters["account"].default is inspect._empty


# ------------------------------- remove_label -------------------------------

def test_remove_label_de_mensaje():
    svc = _label_svc(messages={"modify": {"id": "m1", "labelIds": []}})
    mcp = srv.build_server(service_factory=lambda e: svc,
                           account_lister=lambda: ["a@tyukhay.legal"])
    out = _tool(mcp, "remove_label")(account="a@tyukhay.legal", label="Label_1",
                                     target_id="m1", target_type="message")
    assert out["action"] == "remove" and out["label_id"] == "Label_1"
    method, kwargs = svc.recorded("messages")[-1]
    assert method == "modify" and kwargs["body"] == {"removeLabelIds": ["Label_1"]}


def test_remove_label_de_hilo():
    svc = _label_svc(threads={"modify": {"id": "t1", "labelIds": []}})
    mcp = srv.build_server(service_factory=lambda e: svc,
                           account_lister=lambda: ["a@tyukhay.legal"])
    out = _tool(mcp, "remove_label")(account="a@tyukhay.legal", label="W-02XOR7",
                                     target_id="t1", target_type="thread")
    method, kwargs = svc.recorded("threads")[-1]
    assert method == "modify" and kwargs["body"] == {"removeLabelIds": ["Label_1"]}


def test_remove_label_sistema_rechazado():
    svc = _label_svc()
    mcp = srv.build_server(service_factory=lambda e: svc,
                           account_lister=lambda: ["a@tyukhay.legal"])
    with pytest.raises(ValueError):
        _tool(mcp, "remove_label")(account="a@tyukhay.legal", label="INBOX",
                                   target_id="m1", target_type="message")


def test_remove_label_account_obligatorio():
    svc = _label_svc()
    mcp = srv.build_server(service_factory=lambda e: svc,
                           account_lister=lambda: ["a@tyukhay.legal"])
    fn = _tool(mcp, "remove_label")
    assert inspect.signature(fn).parameters["account"].default is inspect._empty


def test_remove_label_nombre_inexistente_error():
    svc = _label_svc()
    mcp = srv.build_server(service_factory=lambda e: svc,
                           account_lister=lambda: ["a@tyukhay.legal"])
    with pytest.raises(ValueError):
        _tool(mcp, "remove_label")(account="a@tyukhay.legal", label="NoExiste",
                                   target_id="m1", target_type="message")


def test_remove_label_target_type_invalido_error():
    svc = _label_svc()
    mcp = srv.build_server(service_factory=lambda e: svc,
                           account_lister=lambda: ["a@tyukhay.legal"])
    with pytest.raises(ValueError):
        _tool(mcp, "remove_label")(account="a@tyukhay.legal", label="Label_1",
                                   target_id="m1", target_type="foo")


# ------------------------------- rename_label -------------------------------

def test_rename_label_por_id_llama_a_patch():
    svc = _label_svc(labels={
        "list": {"labels": [
            {"id": "Label_1", "name": "01. CONTING/01. EXTRAJUD/05. SEVILLA/Caso",
             "type": "user"},
            {"id": "INBOX", "name": "INBOX", "type": "system"},
        ]},
        "patch": {"id": "Label_1",
                  "name": "01. CONTING/02. JUDICIALES/05. SEVILLA/Caso"},
    })
    mcp = srv.build_server(service_factory=lambda e: svc,
                           account_lister=lambda: ["a@tyukhay.legal"])
    out = _tool(mcp, "rename_label")(
        account="a@tyukhay.legal", label="Label_1",
        new_name="01. CONTING/02. JUDICIALES/05. SEVILLA/Caso")
    assert out["id"] == "Label_1"
    assert out["old_name"] == "01. CONTING/01. EXTRAJUD/05. SEVILLA/Caso"
    assert out["new_name"] == "01. CONTING/02. JUDICIALES/05. SEVILLA/Caso"
    method, kwargs = svc.recorded("labels")[-1]
    assert method == "patch"
    assert kwargs["id"] == "Label_1"
    assert kwargs["body"] == {"name": "01. CONTING/02. JUDICIALES/05. SEVILLA/Caso"}


def test_rename_label_por_nombre_resuelve_id():
    svc = _label_svc(labels={
        "list": {"labels": [{"id": "Label_1", "name": "W-02XOR7", "type": "user"}]},
        "patch": {"id": "Label_1", "name": "W-02XOR7-renombrada"},
    })
    mcp = srv.build_server(service_factory=lambda e: svc,
                           account_lister=lambda: ["a@tyukhay.legal"])
    out = _tool(mcp, "rename_label")(account="a@tyukhay.legal", label="W-02XOR7",
                                     new_name="W-02XOR7-renombrada")
    assert out["id"] == "Label_1"


def test_rename_label_origen_inexistente_error():
    svc = _label_svc()
    mcp = srv.build_server(service_factory=lambda e: svc,
                           account_lister=lambda: ["a@tyukhay.legal"])
    with pytest.raises(ValueError):
        _tool(mcp, "rename_label")(account="a@tyukhay.legal", label="NoExiste",
                                   new_name="Lo que sea")


def test_rename_label_sistema_rechazado():
    svc = _label_svc()
    mcp = srv.build_server(service_factory=lambda e: svc,
                           account_lister=lambda: ["a@tyukhay.legal"])
    with pytest.raises(ValueError):
        _tool(mcp, "rename_label")(account="a@tyukhay.legal", label="INBOX",
                                   new_name="Lo que sea")


def test_rename_label_nombre_destino_de_sistema_rechazado():
    svc = _label_svc()
    mcp = srv.build_server(service_factory=lambda e: svc,
                           account_lister=lambda: ["a@tyukhay.legal"])
    with pytest.raises(ValueError):
        _tool(mcp, "rename_label")(account="a@tyukhay.legal", label="Label_1",
                                   new_name="INBOX")


def test_rename_label_account_obligatorio():
    svc = _label_svc()
    mcp = srv.build_server(service_factory=lambda e: svc,
                           account_lister=lambda: ["a@tyukhay.legal"])
    fn = _tool(mcp, "rename_label")
    assert inspect.signature(fn).parameters["account"].default is inspect._empty
