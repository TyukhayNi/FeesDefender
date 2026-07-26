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


# --- Grupo 2B: discover / gate / build / CLI -----------------------------------

def test_discover_element_happy():
    from core.crm_atlas import discover_element
    def handler(req):
        p = req.url.path
        if p.endswith("/view/config/x/fields"):
            return httpx.Response(200, json={"items": [
                {"name": "tipo", "type": "Select", "label": "T", "active": True, "deleted": False},
                {"name": "resp", "type": "ListaUsuarios", "label": "R", "active": True, "deleted": False}]})
        if p.endswith("/view/config/x/relations"):
            return httpx.Response(200, json={"parent": [], "children": ["actuaciones"]})
        if "/view/enums/x/tipo" in p:
            return httpx.Response(200, json={"enums": [{"id": "A", "label": "a"}]})
        return httpx.Response(404)
    with _mock_client(handler) as c:
        el = discover_element(c, "x")
    assert [f["name"] for f in el["fields"]] == ["resp", "tipo"]
    assert el["enums"] == {"tipo": [{"id": "A", "label": "a"}]}
    assert el["field_types_no_enumerados"] == {"resp": "ListaUsuarios"}
    assert el["relations"] == {"parent": [], "children": ["actuaciones"]}
    assert el["probes"] == {"fields": "view/config/fields", "relations": "ok", "enums": "ok"}


def test_discover_element_degrades_relations(monkeypatch):
    import core.crm_atlas as m
    monkeypatch.setattr(m.time, "sleep", lambda s: None)
    monkeypatch.setattr(m, "_jitter", lambda d: d)
    def handler(req):
        p = req.url.path
        if p.endswith("/fields"):
            return httpx.Response(200, json={"items": []})
        if p.endswith("/relations"):
            return httpx.Response(500, json={"detail": "boom"})
        return httpx.Response(404)
    with _mock_client(handler) as c:
        el = m.discover_element(c, "y")
    assert el["relations"] is None
    assert el["probes"]["relations"] == "failed"
    assert el["probes"]["enums"] == "ok"


def test_discover_element_probe_4b_uses_client_get(monkeypatch):
    import core.crm_atlas as m
    def fake_retry(client, path, **k):
        if path.endswith("/fields"):
            return httpx.Response(404)
        if path.endswith("/relations"):
            return httpx.Response(200, json={"parent": [], "children": []})
        return httpx.Response(404)
    monkeypatch.setattr(m, "get_with_retry", fake_retry)
    probe_calls = []
    class _C:
        def get(self, path, params=None):
            probe_calls.append(path)
            return httpx.Response(500, json={"detail": "... The properties are: a,b."})
    el = m.discover_element(_C(), "x")
    assert probe_calls and probe_calls[0].endswith("/element_registries/x")
    assert el["probes"]["fields"] == "500-probe"
    assert [f["name"] for f in el["fields"]] == ["a", "b"]


def test_scan_atlas_for_pii_email_persona_clean_warnings():
    from core.crm_atlas import scan_atlas_for_pii
    dirty = {"elements": [{"slug": "u", "enums": {"c": [{"id": "1", "label": "Fulano fulano@x.com"}]}}]}
    assert any(h.startswith("u.c") and h.endswith("email") for h in scan_atlas_for_pii(dirty))
    persona = {"elements": [{"slug": "u", "enums": {"c": [{"id": "1", "label": "Maria Gonzalez Ruiz"}]}}]}
    assert any(h.endswith("parece-persona") for h in scan_atlas_for_pii(persona))
    clean = {"elements": [{"slug": "y", "enums": {"iva": [{"id": "R1", "label": "Operaciones interiores"}]}}]}
    assert scan_atlas_for_pii(clean) == []
    warn = {"elements": [], "warnings": ["algo raro con a@b.com"]}
    assert any(h.endswith("email") for h in scan_atlas_for_pii(warn))


def test_build_atlas_phase_b_metric_and_order():
    from core.crm_atlas import build_atlas_phase_b
    results = [
        {"slug": "b", "probes": {"fields": "ok", "relations": "ok", "enums": "ok"}},
        {"slug": "a", "probes": {"fields": "ok", "relations": "failed", "enums": "ok"}}]
    atlas = build_atlas_phase_b({"meta": {}, "summary": {}, "endpoints": []}, results, tenant="tnm")
    assert [e["slug"] for e in atlas["elements"]] == ["a", "b"]
    pb = atlas["meta"]["phase_b"]
    assert pb["ran"] is True and pb["elements_total"] == 2
    assert pb["elements_ok"] == 1 and pb["elements_degraded"] == 1 and pb["complete"] is False


def test_build_atlas_phase_b_circuit_breaker():
    from core.crm_atlas import build_atlas_phase_b
    results = [{"slug": s, "probes": {"fields": "failed", "relations": "ok", "enums": "ok"}}
               for s in ["a", "b", "c"]]
    atlas = build_atlas_phase_b({"meta": {}, "summary": {}, "endpoints": []}, results, tenant="tnm")
    assert atlas["meta"]["phase_b"]["circuit_broken"] is True


def test_phase_b_deterministic_under_permutation():
    from core.crm_atlas import build_atlas_phase_b, render_digest
    import random
    base = [{"slug": s, "fields": [], "relations": {"parent": [], "children": []},
             "enums": {}, "field_types_no_enumerados": {},
             "probes": {"fields": "ok", "relations": "ok", "enums": "ok"}} for s in ["b", "a", "c"]]
    p2 = list(base)
    random.Random(1).shuffle(p2)
    a1 = build_atlas_phase_b({"meta": {}, "summary": {"by_tag": {}}, "endpoints": []}, list(base), tenant="tnm")
    a2 = build_atlas_phase_b({"meta": {}, "summary": {"by_tag": {}}, "endpoints": []}, p2, tenant="tnm")
    assert json.dumps(a1, sort_keys=True, ensure_ascii=False) == json.dumps(a2, sort_keys=True, ensure_ascii=False)
    assert render_markdown(a1) == render_markdown(a2)
    assert render_digest(a1) == render_digest(a2)


def test_render_md_phase_b_degraded_section():
    from core.crm_atlas import build_atlas_phase_b
    results = [{"slug": "extrajudiciales_zzz", "fields": [], "relations": None, "enums": {},
                "field_types_no_enumerados": {},
                "probes": {"fields": "ok", "relations": "failed", "enums": "ok"}}]
    md = render_markdown(build_atlas_phase_b(
        {"meta": {}, "summary": {"by_tag": {}}, "endpoints": []}, results, tenant="tnm"))
    assert "0/1 resueltos" in md
    assert "degradado" in md.lower()
    assert "extrajudiciales_zzz" in md
    assert md.index("degradado") < md.index("extrajudiciales_zzz")


def test_load_previous_atlas_utf8(tmp_path):
    from core.crm_atlas import load_previous_atlas
    p = tmp_path / "a.json"
    p.write_text(json.dumps({"x": "Anio/Categoria|N"}, ensure_ascii=False), encoding="utf-8")
    assert load_previous_atlas(p)["x"] == "Anio/Categoria|N"
    assert load_previous_atlas(tmp_path / "nope.json") is None


def _cli(monkeypatch, handler):
    from typer.testing import CliRunner
    import scripts.crm_atlas as cli
    monkeypatch.delenv("SUDESPACHO_API_KEY", raising=False)
    monkeypatch.setattr(cli, "fetch_oas3", lambda base_url=cli.PUBLIC_BASE_URL, **k: copy.deepcopy(_MINI_SPEC))
    monkeypatch.setattr(cli, "atlas_client",
                        lambda *a, **k: httpx.Client(transport=httpx.MockTransport(handler), base_url="https://x"))
    return CliRunner(), cli


def _invoke(runner, cli, tmp_path, *extra):
    out = tmp_path / "a.json"
    md = tmp_path / "a.md"
    dig = tmp_path / "d.md"
    r = runner.invoke(cli.app, ["discover", "--phase", "all",
                                "--atlas-json", str(out), "--atlas-md", str(md),
                                "--digest-md", str(dig), *extra])
    return r, out, md, dig


def test_cli_phase_all_writes(tmp_path, monkeypatch):
    def handler(req):
        p = req.url.path
        if p == "/api/elements":
            return httpx.Response(200, json=[{"label": "Extra", "id": {"value": "extra"}}])
        if p.endswith("/view/config/extra/fields"):
            return httpx.Response(200, json={"items": [
                {"name": "tipo", "type": "Select", "label": "T", "active": True, "deleted": False}]})
        if p.endswith("/view/config/extra/relations"):
            return httpx.Response(200, json={"parent": [], "children": []})
        if "/view/enums/extra/tipo" in p:
            return httpx.Response(200, json={"enums": [{"id": "A", "label": "Alfa"}]})
        return httpx.Response(404)
    runner, cli = _cli(monkeypatch, handler)
    r, out, md, dig = _invoke(runner, cli, tmp_path)
    assert r.exit_code == 0, r.output
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["meta"]["phase_b"]["elements_total"] == 1
    assert data["elements"][0]["slug"] == "extra"
    assert data["elements"][0]["enums"] == {"tipo": [{"id": "A", "label": "Alfa"}]}
    assert dig.exists() and md.exists()


def test_cli_phase_all_aborts_on_401_writes_nothing(tmp_path, monkeypatch):
    runner, cli = _cli(monkeypatch, lambda req: httpx.Response(401))
    r, out, md, dig = _invoke(runner, cli, tmp_path)
    assert r.exit_code != 0
    assert not out.exists() and not md.exists() and not dig.exists()


def test_cli_phase_all_email_blocks_write(tmp_path, monkeypatch):
    def handler(req):
        p = req.url.path
        if p == "/api/elements":
            return httpx.Response(200, json=[{"label": "E", "id": {"value": "e"}}])
        if p.endswith("/view/config/e/fields"):
            return httpx.Response(200, json={"items": [
                {"name": "c", "type": "Select", "label": "", "active": True, "deleted": False}]})
        if p.endswith("/view/config/e/relations"):
            return httpx.Response(200, json={"parent": [], "children": []})
        if "/view/enums/e/c" in p:
            return httpx.Response(200, json={"enums": [{"id": "1", "label": "foo bar@correo.com"}]})
        return httpx.Response(404)
    runner, cli = _cli(monkeypatch, handler)
    r, out, md, dig = _invoke(runner, cli, tmp_path)
    assert r.exit_code != 0
    assert not out.exists() and not md.exists()


def test_cli_phase_all_persona_quarantined(tmp_path, monkeypatch):
    def handler(req):
        p = req.url.path
        if p == "/api/elements":
            return httpx.Response(200, json=[{"label": "E", "id": {"value": "e"}}])
        if p.endswith("/view/config/e/fields"):
            return httpx.Response(200, json={"items": [
                {"name": "c", "type": "Select", "label": "", "active": True, "deleted": False}]})
        if p.endswith("/view/config/e/relations"):
            return httpx.Response(200, json={"parent": [], "children": []})
        if "/view/enums/e/c" in p:
            return httpx.Response(200, json={"enums": [{"id": "1", "label": "Maria Gonzalez Ruiz"}]})
        return httpx.Response(404)
    runner, cli = _cli(monkeypatch, handler)
    r, out, md, dig = _invoke(runner, cli, tmp_path)
    assert r.exit_code == 0, r.output
    el = json.loads(out.read_text(encoding="utf-8"))["elements"][0]
    assert "c" not in el["enums"]
    assert el["field_types_no_enumerados"].get("c") == "Select(cuarentena-PII)"


def test_cli_resume_keeps_resolved_retries_degraded(tmp_path, monkeypatch):
    prev = {"meta": {}, "summary": {}, "endpoints": [], "elements": [
        {"slug": "a", "fields": [], "relations": {"parent": [], "children": []}, "enums": {},
         "field_types_no_enumerados": {}, "probes": {"fields": "ok", "relations": "ok", "enums": "ok"}},
        {"slug": "b", "fields": [], "relations": None, "enums": {},
         "field_types_no_enumerados": {}, "probes": {"fields": "ok", "relations": "failed", "enums": "ok"}}]}
    out = tmp_path / "a.json"
    md = tmp_path / "a.md"
    dig = tmp_path / "d.md"
    out.write_text(json.dumps(prev), encoding="utf-8")
    def handler(req):
        p = req.url.path
        if p == "/api/elements":
            return httpx.Response(200, json=[{"label": "A", "id": {"value": "a"}},
                                             {"label": "B", "id": {"value": "b"}}])
        if p.endswith("/fields"):
            return httpx.Response(200, json={"items": []})
        if p.endswith("/relations"):
            return httpx.Response(200, json={"parent": [], "children": []})
        return httpx.Response(404)
    runner, cli = _cli(monkeypatch, handler)
    r = runner.invoke(cli.app, ["discover", "--phase", "all", "--resume",
                                "--atlas-json", str(out), "--atlas-md", str(md), "--digest-md", str(dig)])
    assert r.exit_code == 0, r.output
    data = json.loads(out.read_text(encoding="utf-8"))
    assert {e["slug"] for e in data["elements"]} == {"a", "b"}
    b = next(e for e in data["elements"] if e["slug"] == "b")
    assert b["relations"] == {"parent": [], "children": []} and b["probes"]["relations"] == "ok"


# --- Grupo 4: D1/D2/D6b — el atlas no debe ordenar el comando que lo mutila ------
# Revisión adversarial 2026-07-26:
# docs/superpowers/specs/2026-07-26-gobernanza-indice-adversarial-review.md

def test_renders_ordenan_phase_all_no_phase_a(spec):
    """D1 — ambos renders imprimen `--phase all`; ninguno el `--phase a` destructivo.

    Dos vectores: el .md ordenaba `--phase a` y el digest imprimía `discover`
    sin fase (y el default del CLI es `a`).
    """
    atlas = build_atlas_phase_a(spec, tenant="tnm")
    for render in (render_markdown, render_digest):
        txt = render(atlas)
        assert "scripts.crm_atlas discover --phase all" in txt, render.__name__
        assert "discover --phase a." not in txt, render.__name__
        assert "`python -m scripts.crm_atlas discover`" not in txt, render.__name__


def test_fila_fase_b_distingue_tres_estados(spec):
    """D2 — `ran` (ejecución) y `complete` (0 degradados) son estados distintos."""
    from core.crm_atlas import _fase_b_estado
    base = build_atlas_phase_a(spec, tenant="tnm")

    assert _fase_b_estado(base["meta"]["phase_b"]) == "⏳ no ejecutada"
    assert "⏳ no ejecutada" in render_markdown(base)

    completa = {"ran": True, "elements_total": 89, "elements_ok": 89,
                "elements_degraded": 0, "complete": True}
    assert _fase_b_estado(completa) == "✅ 89/89"

    degradada = {"ran": True, "elements_total": 89, "elements_ok": 87,
                 "elements_degraded": 2, "complete": False}
    assert _fase_b_estado(degradada) == "⚠️ 87/89 (2 degradados)"
    # el bug original: `complete=False` con Fase B corrida se rendía como "pendiente"
    md = render_markdown({**base, "meta": {**base["meta"], "phase_b": degradada}})
    assert "| Fase B (esquema por elemento) | ⚠️ 87/89 (2 degradados) |" in md
    assert "pendiente" not in md.split("## Índice por módulo")[0]


def test_render_markdown_emite_frontmatter_estado(spec):
    """D6b — el atlas es doc de raíz de docs/: necesita frontmatter, y es generado."""
    md = render_markdown(build_atlas_phase_a(spec, tenant="tnm"))
    assert md.startswith("---\nestado: vigente\n")
    cabecera = md.split("---\n")[1]
    assert "dueño:" in cabecera


def test_cli_rehusa_pisar_atlas_con_fase_b(tmp_path, monkeypatch):
    """D1 — guarda dura: un atlas sin Fase B no pisa un .md que sí la tiene."""
    from typer.testing import CliRunner
    import scripts.crm_atlas as cli
    monkeypatch.setattr(cli, "fetch_oas3",
                        lambda base_url=cli.PUBLIC_BASE_URL, **k: copy.deepcopy(_MINI_SPEC))
    md = tmp_path / "atlas.md"
    previo = "# Atlas\n\n## Esquema por elemento — 87/89 resueltos\n\n### abogados\n"
    md.write_text(previo, encoding="utf-8")
    out, dig = tmp_path / "a.json", tmp_path / "d.md"

    r = CliRunner().invoke(cli.app, ["discover", "--phase", "a", "--atlas-json", str(out),
                                     "--atlas-md", str(md), "--digest-md", str(dig)])
    assert r.exit_code == 1, r.output
    assert md.read_text(encoding="utf-8") == previo   # intacto
    assert not out.exists() and not dig.exists()      # ninguna de las tres escrituras

    # sin .md previo (o sin Fase B en él) la corrida de Fase A sigue siendo legítima
    md.unlink()
    r2 = CliRunner().invoke(cli.app, ["discover", "--phase", "a", "--atlas-json", str(out),
                                      "--atlas-md", str(md), "--digest-md", str(dig)])
    assert r2.exit_code == 0, r2.output
    assert md.exists() and out.exists() and dig.exists()


def test_artefacto_atlas_coherente_con_su_fase_b():
    """DECISIVO — valida el ARTEFACTO commiteado, no el generador.

    Es el único que caza la deriva: el generador puede estar corregido y el .md
    en disco seguir mintiendo (que es justo lo que pasó entre `b2d624c` y hoy).
    """
    import re
    from pathlib import Path
    ruta = Path(__file__).resolve().parent.parent / "docs" / "CRM_SUDESPACHO_ATLAS.md"
    txt = ruta.read_text(encoding="utf-8")

    fila = re.search(r"^\| Fase B \(esquema por elemento\) \| (.+?) \|$", txt, re.MULTILINE)
    assert fila, "falta la fila «Fase B» en el atlas"
    estado = fila.group(1)
    esquema = re.search(r"^## Esquema por elemento — (\d+)/(\d+) resueltos$", txt, re.MULTILINE)

    if esquema is None:
        assert estado == "⏳ no ejecutada", (
            f"el atlas no trae esquema por elemento pero la fila dice «{estado}»")
        return
    ok, total = esquema.group(1), esquema.group(2)
    assert "no ejecutada" not in estado and "pendiente" not in estado, (
        f"el atlas trae el esquema de {ok}/{total} elementos pero la fila dice «{estado}»")
    assert f"{ok}/{total}" in estado, (
        f"la fila «{estado}» no cuadra con el encabezado «{ok}/{total} resueltos»")
    n_deg = int(total) - int(ok)
    assert estado.startswith("✅" if n_deg == 0 else "⚠️"), estado
    if n_deg:
        assert f"({n_deg} degradados)" in estado, estado

    # D1 en el artefacto: el documento no puede ordenar el comando que lo borra
    assert "discover --phase all" in txt
    assert "discover --phase a." not in txt
