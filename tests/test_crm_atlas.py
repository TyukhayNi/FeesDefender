"""Tests del atlas del CRM sudespacho — Fase A (parseo del OAS3), solo lógica pura.

Sin red: se parsea un fixture OAS3 recortado con la misma forma que el spec real
(`api-crm-commons-pro.sudespacho.biz/api/docs.json`, OpenAPI 3.0.0).
"""

from __future__ import annotations

import json

import pytest

from core.crm_atlas import (
    Endpoint,
    build_atlas_phase_a,
    find_orphan_paths,
    operation_id_to_dev_slug,
    parse_oas3,
    render_markdown,
    summarize_endpoints,
)


@pytest.fixture
def spec() -> dict:
    return {
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
    assert get_abs.dev_doc_url.endswith("/get-absences-absences-collection")


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
    assert atlas["meta"]["phase_a_complete"] is True
    assert atlas["meta"]["phase_b_complete"] is False
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
