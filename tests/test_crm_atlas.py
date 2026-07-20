"""Tests del atlas del CRM sudespacho — Fase A (parseo del OAS3), solo lógica pura.

Sin red: se parsea un fixture OAS3 recortado con la misma forma que el spec real
(`api-crm-commons-pro.sudespacho.biz/api/docs.json`, OpenAPI 3.0.0).
"""

from __future__ import annotations

import copy
import json

import httpx
import pytest

from core.crm_atlas import (
    CrmAtlasAuthError,
    CrmAtlasError,
    Endpoint,
    Field,
    atlas_client,
    auth_healthcheck,
    build_atlas_phase_a,
    fetch_elements,
    find_orphan_paths,
    get_with_retry,
    operation_id_to_dev_slug,
    parse_enums,
    parse_fields_config,
    parse_invalid_property_probe,
    parse_oas3,
    parse_relations_config,
    render_digest,
    render_markdown,
    select_enum_fields,
    summarize_endpoints,
)


_MINI_SPEC = {
        "openapi": "3.0.0",
        "info": {"title": "API CRM reference documentation", "version": "0.0.1"},
        "servers": [{"url": "https://api-crm-commons-pro.sudespacho.biz"}],
        "security": [{"apiKey": []}],
        "components": {
            "securitySchemes": {
                "apiKey": {"type": "apiKey", "name": "Authorization", "in": "header"}
            },
            "parameters": {
                "SharedId": {
                    "name": "id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string"},
                    "description": "Register id",
                }
            },
            "schemas": {"Absences": {"type": "object"}},
        },
        "paths": {
            "/api/absences": {
                "get": {
                    "operationId": "get_absencesAbsencesCollection",
                    "tags": ["Absences"],
                    "summary": "Recovers Absences of a given User",
                    "description": "Send id=<b>me</b> to recover Absences",
                    "parameters": [
                        {
                            "name": "properties[]",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "array", "items": {"type": "string"}},
                            "description": "<i>Example</i> : nombre, email",
                        }
                    ],
                    "responses": {"200": {"description": "ok"}, "404": {"description": "no"}},
                },
                "post": {
                    "operationId": "post_absencesAbsencesCollection",
                    "tags": ["Absences"],
                    "summary": "Create absence",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Absences"}
                            }
                        }
                    },
                    "responses": {"201": {"description": "created"}},
                },
            },
            "/api/public_thing/{id}": {
                "parameters": [{"$ref": "#/components/parameters/SharedId"}],
                "get": {
                    "operationId": "get_publicThingItem",
                    "tags": ["PublicThing"],
                    "summary": "Public read",
                    "security": [],  # override → público
                    "responses": {"200": {"description": "ok"}},
                },
            },
            # path declarado con SOLO parameters, sin operación (huérfano)
            "/api/companies": {
                "parameters": [
                    {"name": "page", "in": "query", "required": False, "schema": {"type": "integer"}}
                ],
            },
        },
    }


@pytest.fixture
def spec() -> dict:
    return copy.deepcopy(_MINI_SPEC)


# --- operation_id_to_dev_slug -------------------------------------------------

def test_dev_slug_matches_portal_pattern():
    assert (
        operation_id_to_dev_slug("get_absencesAbsencesCollection")
        == "get-absences-absences-collection"
    )
    assert operation_id_to_dev_slug("post_publicThingItem") == "post-public-thing-item"


# --- parse_oas3 ---------------------------------------------------------------

def test_parse_counts_and_order(spec):
    eps = parse_oas3(spec)
    # 3 operaciones: 2 en /api/absences, 1 en /api/public_thing/{id}
    assert len(eps) == 3
    # orden determinista por (path, método)
    keys = [(e.path, e.method) for e in eps]
    assert keys == [
        ("/api/absences", "GET"),
        ("/api/absences", "POST"),
        ("/api/public_thing/{id}", "GET"),
    ]


def test_parse_endpoint_fields(spec):
    eps = {(e.path, e.method): e for e in parse_oas3(spec)}
    get_abs = eps[("/api/absences", "GET")]
    assert get_abs.operation_id == "get_absencesAbsencesCollection"
    assert get_abs.tags == ["Absences"]
    assert get_abs.auth == "apiKey"  # hereda seguridad global
    assert get_abs.response_codes == ["200", "404"]
    # HTML limpiado en summary/description y en la descripción del param
    assert get_abs.description == "Send id=me to recover Absences"
    (p,) = get_abs.parameters
    assert p.name == "properties[]"
    assert p.type == "array[string]"
    assert p.description == "Example : nombre, email"
    assert get_abs.dev_doc_url.endswith("/get-absences-absences-collection/")


def test_request_schema_ref_basename(spec):
    post_abs = next(
        e for e in parse_oas3(spec) if e.path == "/api/absences" and e.method == "POST"
    )
    assert post_abs.request_schema == "Absences"


def test_op_security_override_public(spec):
    pub = next(e for e in parse_oas3(spec) if e.path == "/api/public_thing/{id}")
    assert pub.auth == "public"
    # el parámetro compartido a nivel de path se resuelve por $ref y se hereda
    assert [p.name for p in pub.parameters] == ["id"]
    assert pub.parameters[0].location == "path"
    assert pub.parameters[0].required is True


def test_dev_links_can_be_disabled(spec):
    eps = parse_oas3(spec, dev_links=False)
    assert all(e.dev_doc_url is None for e in eps)


# --- summarize ----------------------------------------------------------------

def test_summarize(spec):
    summ = summarize_endpoints(parse_oas3(spec))
    assert summ["total_operations"] == 3
    assert summ["total_paths"] == 2
    assert summ["by_method"] == {"GET": 2, "POST": 1}
    assert summ["by_tag"] == {"Absences": 2, "PublicThing": 1}


# --- build_atlas + render -----------------------------------------------------

def test_find_orphan_paths(spec):
    orphans = find_orphan_paths(spec)
    assert [o["path"] for o in orphans] == ["/api/companies"]
    assert orphans[0]["declared_keys"] == ["parameters"]
    assert orphans[0]["parameters"][0]["name"] == "page"


def test_build_atlas_shape(spec):
    atlas = build_atlas_phase_a(spec, tenant="tnm", generated_at="2026-07-20T00:00:00Z")
    assert atlas["meta"]["tenant"] == "tnm"
    assert atlas["meta"]["phase_a"] == {"complete": True}
    assert atlas["meta"]["phase_b"]["complete"] is False
    assert atlas["meta"]["generator_version"] == 2
    assert atlas["meta"]["sources"]["oas3"]["openapi"] == "3.0.0"
    assert atlas["meta"]["sources"]["oas3"]["global_security_auth"] == "apiKey"
    assert len(atlas["endpoints"]) == 3
    assert atlas["elements"] == []
    # el path huérfano no se descarta: va a paths_without_operations + summary + warning
    assert atlas["summary"]["total_path_keys"] == 3
    assert atlas["summary"]["total_paths"] == 2
    assert atlas["summary"]["paths_without_operations"] == 1
    assert [o["path"] for o in atlas["paths_without_operations"]] == ["/api/companies"]
    assert atlas["warnings"] and "sin operación documentada" in atlas["warnings"][0]
    # serializable a JSON sin sorpresas
    json.dumps(atlas, ensure_ascii=False)


def test_render_markdown_has_tables_and_index(spec):
    atlas = build_atlas_phase_a(spec, tenant="tnm", generated_at="2026-07-20T00:00:00Z")
    md = render_markdown(atlas)
    assert "# Atlas del CRM sudespacho" in md
    assert "GENERADO por" in md
    assert "## Índice por módulo" in md
    assert "### Absences" in md
    assert "### PublicThing" in md
    # el header de seguridad sale del securityScheme
    assert "Authorization" in md
    # una fila con el path y método
    assert "`GET`" in md and "/api/absences" in md
    # sección de paths huérfanos con el path solo-parameters
    assert "## Paths declarados sin operación documentada" in md
    assert "/api/companies" in md


def test_render_markdown_escapes_pipes():
    spec = {
        "openapi": "3.0.0",
        "info": {},
        "security": [{"apiKey": []}],
        "components": {"securitySchemes": {}},
        "paths": {
            "/api/x": {
                "get": {
                    "operationId": "get_x",
                    "tags": ["T"],
                    "summary": "a | b pipe",
                    "responses": {"200": {}},
                }
            }
        },
    }
    atlas = build_atlas_phase_a(spec, tenant="tnm")
    md = render_markdown(atlas)
    assert "a \\| b pipe" in md


# --- Grupo 0: andamiaje --------------------------------------------------------

def test_exception_hierarchy():
    from core.crm_atlas import CrmAtlasError, CrmAtlasAuthError
    import core.crm_atlas as m
    assert issubclass(CrmAtlasAuthError, CrmAtlasError)
    assert all(hasattr(m, n) for n in ("json", "os", "time", "random"))


def test_meta_nested_schema(spec):
    m = build_atlas_phase_a(spec, tenant="tnm")["meta"]
    assert m["generator_version"] == 2
    assert m["phase_a"] == {"complete": True}
    assert m["phase_b"]["complete"] is False and m["phase_b"]["ran"] is False
    assert "x-api-key" in m["auth_note"]
    assert "phase_a_complete" not in m and "phase_b_complete" not in m


def test_render_markdown_tolerates_minimal_phase_b():
    md = render_markdown({"meta": {"tenant": "tnm", "phase_b": {"complete": False}},
                          "summary": {"by_tag": {}}, "endpoints": [], "elements": []})
    assert "# Atlas del CRM" in md  # no KeyError


# --- Grupo 1: hardening Fase A -------------------------------------------------

def test_request_schema_merge_patch_multipart_allof():
    spec = {"openapi": "3.0.0", "info": {}, "security": [{"apiKey": []}],
            "components": {"securitySchemes": {}},
            "paths": {
                "/api/x/{id}": {"patch": {"operationId": "patch_x", "tags": ["X"],
                    "responses": {"200": {}},
                    "requestBody": {"content": {"application/merge-patch+json": {
                        "schema": {"$ref": "#/components/schemas/PatchX"}}}}}},
                "/api/up": {"post": {"operationId": "post_up", "tags": ["X"],
                    "responses": {"201": {}},
                    "requestBody": {"content": {"multipart/form-data": {
                        "schema": {"type": "object"}}}}}},
                "/api/comp": {"post": {"operationId": "post_comp", "tags": ["X"],
                    "responses": {"201": {}},
                    "requestBody": {"content": {"application/json": {
                        "schema": {"allOf": [{"$ref": "#/components/schemas/Base"},
                                             {"type": "object"}]}}}}}}}}
    eps = {(e.path, e.method): e for e in parse_oas3(spec)}
    assert eps[("/api/x/{id}", "PATCH")].request_schema == "PatchX"
    assert eps[("/api/up", "POST")].request_schema == "object"
    assert eps[("/api/comp", "POST")].request_schema == "Base"


def test_deprecated_and_param_enum_default():
    spec = {"openapi": "3.0.0", "info": {}, "security": [{"apiKey": []}],
            "components": {"securitySchemes": {}},
            "paths": {"/api/y": {"get": {"operationId": "get_y", "tags": ["Y"],
                "deprecated": True, "responses": {"200": {}},
                "parameters": [{"name": "mode", "in": "query", "required": False,
                    "schema": {"type": "string", "enum": ["a", "b"], "default": "a"}}]}}}}
    e = parse_oas3(spec)[0]
    assert e.deprecated is True
    assert e.parameters[0].enum == ["a", "b"]
    assert e.parameters[0].default == "a"


def test_digest_lists_module_counts(spec):
    atlas = build_atlas_phase_a(spec, tenant="tnm")
    d = render_digest(atlas)
    assert "# Digest del atlas" in d
    for tag, n in atlas["summary"]["by_tag"].items():
        assert f"- {tag}: {n}" in d          # módulo + su conteo (assert real, no tautología)


def test_cli_discover_a_no_stamp(tmp_path, monkeypatch):
    from typer.testing import CliRunner
    import scripts.crm_atlas as cli
    monkeypatch.setattr(cli, "fetch_oas3", lambda base_url=cli.PUBLIC_BASE_URL, **k: copy.deepcopy(_MINI_SPEC))
    out = tmp_path / "atlas.json"
    md = tmp_path / "atlas.md"
    dig = tmp_path / "atlas.digest.md"
    r = CliRunner().invoke(cli.app, ["discover", "--phase", "a",
                                     "--atlas-json", str(out), "--atlas-md", str(md),
                                     "--digest-md", str(dig)])
    assert r.exit_code == 0, r.output
    assert json.loads(out.read_text(encoding="utf-8"))["meta"]["generated_at"] is None
    assert dig.exists() and md.exists()


# --- Grupo 2A: cliente + parsers de Fase B -------------------------------------

def _mock_client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler), base_url="https://x")


def test_get_with_retry_retries_503(monkeypatch):
    import core.crm_atlas as m
    calls = {"n": 0}
    def handler(req):
        calls["n"] += 1
        return httpx.Response(200, json={}) if calls["n"] >= 3 else httpx.Response(503)
    monkeypatch.setattr(m.time, "sleep", lambda s: None)
    monkeypatch.setattr(m, "_jitter", lambda d: d)
    with _mock_client(handler) as c:
        r = get_with_retry(c, "/api/elements")
    assert r.status_code == 200 and calls["n"] == 3


def test_get_with_retry_no_retry_on_404():
    calls = {"n": 0}
    def handler(req):
        calls["n"] += 1
        return httpx.Response(404)
    with _mock_client(handler) as c:
        r = get_with_retry(c, "/api/x")
    assert r.status_code == 404 and calls["n"] == 1   # 4xx no-429 no reintenta


def test_get_with_retry_exhausts_raises(monkeypatch):
    import core.crm_atlas as m
    monkeypatch.setattr(m.time, "sleep", lambda s: None)
    monkeypatch.setattr(m, "_jitter", lambda d: d)
    with _mock_client(lambda req: httpx.Response(503)) as c:
        with pytest.raises(CrmAtlasError):
            get_with_retry(c, "/api/x", attempts=3)


def test_atlas_client_requires_key(monkeypatch):
    monkeypatch.delenv("SUDESPACHO_API_KEY", raising=False)
    with pytest.raises(CrmAtlasAuthError):
        atlas_client()


def test_auth_healthcheck_401_and_200():
    with _mock_client(lambda req: httpx.Response(401)) as c:
        with pytest.raises(CrmAtlasAuthError):
            auth_healthcheck(c)
    with _mock_client(lambda req: httpx.Response(200, json=[])) as c:
        auth_healthcheck(c)   # no lanza


def test_fetch_elements_list_and_hydra():
    members = [{"label": "Devices", "id": {"value": "devices"}},
               {"label": "Absences", "id": {"value": "absences"}},
               {"label": "Bad"}]  # sin id.value -> ignorado
    def handler(req):
        if "ld+json" in req.headers.get("accept", ""):
            return httpx.Response(200, json={"hydra:member": members, "hydra:totalItems": 3})
        return httpx.Response(200, json=members)
    with _mock_client(handler) as c:
        assert fetch_elements(c) == ["absences", "devices"]


def test_parse_fields_config_ordered_excludes_deleted():
    payload = {"items": [
        {"name": "tipo", "label": "Tipo", "type": "Select", "active": True, "deleted": False},
        {"name": "cuantia", "label": "Cuantía", "type": "Moneda", "active": True, "deleted": False},
        {"name": "x", "label": "x", "type": "TextCorto", "active": False, "deleted": True}]}
    fields = parse_fields_config(payload)
    assert [f.name for f in fields] == ["cuantia", "tipo"]   # ordenado, deleted fuera
    assert {f.name: f.type for f in fields} == {"cuantia": "Moneda", "tipo": "Select"}
    assert fields[0].source == "view/config/fields"


def test_probe_guards():
    ok = httpx.Response(500, json={"detail": "ElementProperty not found : zz The properties are: a,b,c."})
    assert parse_invalid_property_probe(ok) == ["a", "b", "c"]
    other500 = httpx.Response(500, json={"detail": "Array to string conversion"})
    assert parse_invalid_property_probe(other500) is None
    got200 = httpx.Response(200, json={"items": [{"id": 1}]})   # NUNCA esquema desde 200
    assert parse_invalid_property_probe(got200) is None


def test_parse_relations_config_sorted():
    rel = parse_relations_config({"parent": ["sms", "abogados_propios"],
                                  "children": ["actuaciones", "abogados_propios"]})
    assert rel == {"parent": ["abogados_propios", "sms"],
                   "children": ["abogados_propios", "actuaciones"]}
    assert parse_relations_config({}) == {"parent": [], "children": []}


def test_select_enum_fields_allowlist_only_select():
    fields = parse_fields_config({"items": [
        {"name": "tipo", "type": "Select", "label": "", "active": True, "deleted": False},
        {"name": "prof", "type": "ListaUsuarios", "label": "", "active": True, "deleted": False},
        {"name": "banco", "type": "ListaBancos", "label": "", "active": True, "deleted": False},
        {"name": "tags", "type": "Tags", "label": "", "active": True, "deleted": False}]})
    assert select_enum_fields(fields) == ["tipo"]   # SOLO Select


def test_parse_enums_ordered_id_label_only():
    assert parse_enums({"enums": [{"id": "R2", "label": "y", "x": 1}, {"id": "R1", "label": "z"}]}) == \
        [{"id": "R1", "label": "z"}, {"id": "R2", "label": "y"}]
