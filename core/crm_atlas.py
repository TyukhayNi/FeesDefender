"""Atlas del CRM sudespacho — descubrimiento exhaustivo, re-ejecutable.

Diseño: `docs/superpowers/specs/2026-07-20-crm-atlas-descubrimiento-design.md`.

Fase A (esta entrega) = **inventario de endpoints desde el OpenAPI público**
(`/api/docs.json`), sin credenciales. Fase B (esquema por elemento, `x-api-key`)
se añade después reutilizando este módulo.

Todo aquí es **solo lectura** y **solo esquema**: se parsea el spec OAS3, nunca se
leen datos de registros ni se escribe en el CRM. Las funciones de parseo son puras
(testeables offline); `fetch_oas3` es la única con red.
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import random
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any

import httpx


# ---------------------------------------------------------------------------
# Excepciones
# ---------------------------------------------------------------------------

class CrmAtlasError(RuntimeError):
    """Error base del atlas del CRM."""


class CrmAtlasAuthError(CrmAtlasError):
    """Auth global rechazada (401/403) o credencial ausente."""


# ---------------------------------------------------------------------------
# Constantes de fuente
# ---------------------------------------------------------------------------

PUBLIC_BASE_URL = "https://api-crm-commons-pro.sudespacho.biz"
OAS3_PATH = "/api/docs.json"
DEV_PORTAL_BASE = "https://developers.sudespacho.net/docs/api-crm"

HTTP_METHODS = ("get", "post", "put", "patch", "delete")

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Param:
    name: str
    location: str          # el `in` del OpenAPI (path/query/header/cookie)
    required: bool
    type: str | None
    description: str | None


@dataclass
class Endpoint:
    path: str
    method: str            # mayúsculas: GET/POST/PUT/PATCH/DELETE
    operation_id: str | None
    summary: str | None
    description: str | None
    tags: list[str]
    auth: str              # "apiKey" | "public" | esquema(s) del op
    parameters: list[Param]
    request_schema: str | None
    response_codes: list[str]
    dev_doc_url: str | None


# ---------------------------------------------------------------------------
# Helpers de parseo (puros)
# ---------------------------------------------------------------------------

def _clean(text: Any) -> str | None:
    """Limpia HTML inline (`<i>…`) y colapsa espacios. Devuelve None si vacío."""
    if not text:
        return None
    s = _TAG_RE.sub("", str(text))
    s = _WS_RE.sub(" ", s).strip()
    return s or None


def operation_id_to_dev_slug(op_id: str) -> str:
    """`get_absencesAbsencesCollection` → `get-absences-absences-collection`.

    Transforma el operationId (guiones bajos + camelCase) al slug kebab que usa
    el portal Docusaurus de sudespacho. Verificado contra la página real de
    `Absences` (2026-07-20).
    """
    s = op_id.replace("_", " ")
    # frontera minúscula/dígito → mayúscula
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", s)
    # frontera acrónimo (HTMLPage → HTML Page)
    s = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", s)
    return "-".join(s.lower().split())


def _resolve_ref(spec: dict, ref: str) -> dict:
    """Resuelve un `$ref` local (`#/components/…`) contra el spec."""
    node: Any = spec
    for part in ref.lstrip("#/").split("/"):
        if not isinstance(node, dict):
            return {}
        node = node.get(part, {})
    return node if isinstance(node, dict) else {}


def _param_type(schema: Any) -> str | None:
    if not isinstance(schema, dict):
        return None
    t = schema.get("type")
    if t == "array":
        items = schema.get("items", {})
        item_t = items.get("type", "?") if isinstance(items, dict) else "?"
        return f"array[{item_t}]"
    return t


def _parse_param(spec: dict, raw: Any) -> Param:
    if not isinstance(raw, dict):
        return Param(name="", location="", required=False, type=None, description=None)
    if "$ref" in raw:
        raw = _resolve_ref(spec, raw["$ref"])
    return Param(
        name=raw.get("name", ""),
        location=raw.get("in", ""),
        required=bool(raw.get("required", False)),
        type=_param_type(raw.get("schema", {})),
        description=_clean(raw.get("description")),
    )


def _global_auth(spec: dict) -> str:
    sec = spec.get("security") or []
    schemes = [name for entry in sec for name in entry]
    return "+".join(schemes) if schemes else "public"


def _op_auth(op: dict, global_auth: str) -> str:
    if "security" not in op:
        return global_auth
    sec = op.get("security") or []
    if not sec:
        return "public"
    schemes = [name for entry in sec for name in entry]
    return "+".join(schemes) if schemes else "public"


def _request_schema(spec: dict, op: dict) -> str | None:
    body = op.get("requestBody", {})
    if "$ref" in body:
        body = _resolve_ref(spec, body["$ref"])
    content = body.get("content", {})
    if not isinstance(content, dict):
        return None
    for ctype in ("application/json", "application/ld+json"):
        ct = content.get(ctype, {})
        schema = ct.get("schema", {}) if isinstance(ct, dict) else {}
        if not isinstance(schema, dict):
            continue
        if "$ref" in schema:
            return schema["$ref"].rsplit("/", 1)[-1]
        if schema.get("type"):
            t = schema["type"]
            if t == "array":
                items = schema.get("items", {})
                ref = items.get("$ref")
                return f"array[{ref.rsplit('/', 1)[-1]}]" if ref else f"array[{items.get('type', '?')}]"
            return t
    return None


def parse_oas3(spec: dict, *, dev_links: bool = True) -> list[Endpoint]:
    """Normaliza un spec OAS3 a una lista ordenada de `Endpoint`.

    Ordena por (path, orden de método) para que el `git diff` entre corridas
    refleje cambios reales del tenant, no reordenamientos.
    """
    global_auth = _global_auth(spec)
    endpoints: list[Endpoint] = []
    paths = spec.get("paths", {})
    for path in sorted(paths):
        item = paths[path] or {}
        shared_params = item.get("parameters", [])
        for method in HTTP_METHODS:
            op = item.get(method)
            if not isinstance(op, dict):
                continue
            raw_params = list(shared_params) + list(op.get("parameters", []))
            op_id = op.get("operationId")
            endpoints.append(
                Endpoint(
                    path=path,
                    method=method.upper(),
                    operation_id=op_id,
                    summary=_clean(op.get("summary")),
                    description=_clean(op.get("description")),
                    tags=list(op.get("tags", [])),
                    auth=_op_auth(op, global_auth),
                    parameters=[_parse_param(spec, p) for p in raw_params],
                    request_schema=_request_schema(spec, op),
                    response_codes=sorted((op.get("responses") or {}).keys()),
                    dev_doc_url=(
                        f"{DEV_PORTAL_BASE}/{operation_id_to_dev_slug(op_id)}"
                        if dev_links and op_id
                        else None
                    ),
                )
            )
    return endpoints


def find_orphan_paths(spec: dict) -> list[dict]:
    """Paths declarados en el spec **sin ninguna operación estándar** (solo `parameters`).

    No son endpoints ocultos: son entradas de `paths` que el OpenAPI declara pero cuya
    operación no está documentada. Se conservan (no se descartan en silencio) como
    candidatos a sondeo empírico en la Fase B.
    """
    out: list[dict] = []
    paths = spec.get("paths", {})
    for path in sorted(paths):
        item = paths[path] or {}
        if not isinstance(item, dict):
            continue
        if any(m in item for m in HTTP_METHODS):
            continue
        params = [asdict(_parse_param(spec, p)) for p in item.get("parameters", [])]
        out.append({"path": path, "declared_keys": sorted(item.keys()), "parameters": params})
    return out


def summarize_endpoints(endpoints: list[Endpoint]) -> dict:
    """Conteos agregados: total, por método y por tag."""
    by_method: dict[str, int] = {}
    by_tag: dict[str, int] = {}
    for ep in endpoints:
        by_method[ep.method] = by_method.get(ep.method, 0) + 1
        for tag in ep.tags or ["(sin tag)"]:
            by_tag[tag] = by_tag.get(tag, 0) + 1
    return {
        "total_operations": len(endpoints),
        "total_paths": len({ep.path for ep in endpoints}),
        "by_method": dict(sorted(by_method.items())),
        "by_tag": dict(sorted(by_tag.items())),
    }


# ---------------------------------------------------------------------------
# Fetch (única función con red)
# ---------------------------------------------------------------------------

def fetch_oas3(base_url: str = PUBLIC_BASE_URL, *, client: httpx.Client | None = None,
               timeout: float = 60.0) -> dict:
    """Descarga y parsea el spec OAS3 público. Sin credenciales."""
    url = base_url.rstrip("/") + OAS3_PATH
    owns = client is None
    cli = client or httpx.Client(timeout=timeout)
    try:
        resp = cli.get(url)
        resp.raise_for_status()
        return resp.json()
    finally:
        if owns:
            cli.close()


# ---------------------------------------------------------------------------
# Build + render
# ---------------------------------------------------------------------------

def build_atlas_phase_a(
    spec: dict,
    *,
    tenant: str,
    base_url: str = PUBLIC_BASE_URL,
    generated_at: str | None = None,
    dev_links: bool = True,
) -> dict:
    """Construye el atlas (Fase A: solo endpoints) como dict serializable."""
    endpoints = parse_oas3(spec, dev_links=dev_links)
    orphans = find_orphan_paths(spec)
    info = spec.get("info", {})
    servers = [s.get("url") for s in spec.get("servers", []) if isinstance(s, dict)]
    summary = summarize_endpoints(endpoints)
    summary["total_path_keys"] = len(spec.get("paths", {}))
    summary["paths_without_operations"] = len(orphans)
    warnings: list[str] = []
    if orphans:
        warnings.append(
            f"{len(orphans)} paths declarados en el OpenAPI sin operación documentada "
            "(solo 'parameters'); candidatos a sondeo empírico en Fase B."
        )
    return {
        "meta": {
            "tenant": tenant,
            "generated_at": generated_at,
            "generator": "scripts.crm_atlas",
            "generator_version": 2,
            "phase_a": {"complete": True},
            "phase_b": {"ran": False, "complete": False},
            "auth_note": ("El spec declara header 'Authorization' (apiKey) pero devuelve "
                          "401; el header operativo es 'x-api-key' (INTEGRACION §2.1)."),
            "sources": {
                "oas3": {
                    "url": base_url.rstrip("/") + OAS3_PATH,
                    "openapi": spec.get("openapi"),
                    "info_title": info.get("title"),
                    "info_version": info.get("version"),
                    "servers": servers,
                    "security_schemes": spec.get("components", {}).get("securitySchemes", {}),
                    "global_security_auth": _global_auth(spec),
                },
                "dev_portal": {"base": DEV_PORTAL_BASE, "linked": dev_links},
            },
        },
        "summary": summary,
        "endpoints": [asdict(ep) for ep in endpoints],
        "paths_without_operations": orphans,
        "elements": [],
        "warnings": warnings,
    }


def _md_escape(text: str | None) -> str:
    if not text:
        return ""
    return text.replace("|", "\\|").replace("\n", " ")


def render_markdown(atlas: dict) -> str:
    """Render humano del atlas (generado — no editar a mano). Tolera atlas de Fase A y B."""
    meta = atlas.get("meta", {})
    summ = atlas.get("summary", {})
    oas = meta.get("sources", {}).get("oas3", {})
    phase_b_complete = meta.get("phase_b", {}).get("complete", False)
    lines: list[str] = []
    lines.append("# Atlas del CRM sudespacho — inventario de endpoints")
    lines.append("")
    lines.append("> **GENERADO por `scripts.crm_atlas discover` — NO editar a mano.**")
    lines.append("> Regenerar: `python -m scripts.crm_atlas discover --phase a`. "
                 "El `git diff` entre corridas = deriva del tenant.")
    lines.append("> Diseño: `docs/superpowers/specs/2026-07-20-crm-atlas-descubrimiento-design.md`.")
    lines.append("")
    lines.append("| Meta | Valor |")
    lines.append("|---|---|")
    lines.append(f"| Tenant | `{meta.get('tenant', '?')}` |")
    lines.append(f"| Generado | {meta.get('generated_at') or '(sin sello)'} |")
    lines.append(f"| Fuente OAS3 | `{oas.get('url', '?')}` |")
    lines.append(f"| OpenAPI | {oas.get('openapi')} · {oas.get('info_title')} v{oas.get('info_version')} |")
    lines.append(f"| Auth global | `{oas.get('global_security_auth', '?')}` "
                 f"(header `{_security_header(oas)}`) |")
    lines.append(f"| Fase B (esquema por elemento) | {'✅' if phase_b_complete else '⏳ pendiente'} |")
    lines.append("")
    total_ops = summ.get("total_operations", "?")
    total_paths = summ.get("total_paths", "?")
    total_keys = summ.get("total_path_keys", total_paths)
    by_method = summ.get("by_method", {})
    lines.append(f"**{total_ops} operaciones** sobre "
                 f"**{total_keys} paths declarados** "
                 f"({total_paths} con operación documentada). Por método: "
                 + " · ".join(f"{m} {n}" for m, n in by_method.items()) + ".")
    orphan_n = summ.get("paths_without_operations", 0)
    if orphan_n:
        lines.append("")
        lines.append(f"> ⚠️ {orphan_n} paths declarados sin operación documentada en el "
                     "OpenAPI (ver sección final) — candidatos a sondeo empírico (Fase B).")
    lines.append("")

    # Índice de tags
    lines.append("## Índice por módulo (tag)")
    lines.append("")
    lines.append("| Módulo | Operaciones |")
    lines.append("|---|---|")
    for tag, n in summ.get("by_tag", {}).items():
        anchor = _anchor(tag)
        lines.append(f"| [{_md_escape(tag)}](#{anchor}) | {n} |")
    lines.append("")

    # Endpoints agrupados por tag
    by_tag: dict[str, list[dict]] = {}
    for ep in atlas.get("endpoints", []):
        for tag in ep["tags"] or ["(sin tag)"]:
            by_tag.setdefault(tag, []).append(ep)

    lines.append("## Endpoints por módulo")
    lines.append("")
    for tag in sorted(by_tag):
        lines.append(f"### {_md_escape(tag)}")
        lines.append("")
        lines.append("| Método | Path | Resumen | Auth | Params | Doc |")
        lines.append("|---|---|---|---|---|---|")
        rows = sorted(by_tag[tag], key=lambda e: (e["path"], e["method"]))
        for ep in rows:
            doc = f"[↗]({ep['dev_doc_url']})" if ep.get("dev_doc_url") else ""
            lines.append(
                f"| `{ep['method']}` | `{_md_escape(ep['path'])}` | "
                f"{_md_escape(ep['summary'])} | `{ep['auth']}` | "
                f"{len(ep['parameters'])} | {doc} |"
            )
        lines.append("")

    orphans = atlas.get("paths_without_operations", [])
    if orphans:
        lines.append("## Paths declarados sin operación documentada")
        lines.append("")
        lines.append("Entradas de `paths` que el OpenAPI declara con `parameters` pero **sin** "
                     "operación (GET/POST/…). No son endpoints ocultos; su verbo real, si existe, "
                     "se confirma por sondeo empírico (Fase B). No se descartan para no ocultar "
                     "superficie.")
        lines.append("")
        lines.append("| Path | Claves declaradas |")
        lines.append("|---|---|")
        for o in sorted(orphans, key=lambda x: x["path"]):
            lines.append(f"| `{_md_escape(o['path'])}` | {', '.join(o.get('declared_keys', []))} |")
        lines.append("")
    return "\n".join(lines) + "\n"


def _security_header(oas: dict) -> str:
    schemes = oas.get("security_schemes", {})
    for scheme in schemes.values():
        if isinstance(scheme, dict) and scheme.get("in") == "header":
            return scheme.get("name", "?")
    return "?"


def _anchor(text: str) -> str:
    """Ancla estilo GitHub para el índice."""
    s = text.lower()
    s = re.sub(r"[^\w\s-]", "", s)
    return re.sub(r"\s+", "-", s).strip("-")
