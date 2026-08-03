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
import hashlib
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
    enum: list | None = None
    default: Any = None


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
    deprecated: bool = False


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
    # colapsar toda tanda de no-alfanuméricos a un solo '-' (kebab lodash);
    # evita paréntesis y guiones dobles que dan 404 en el portal.
    s = re.sub(r"[^0-9a-zA-Z]+", "-", s.lower())
    return s.strip("-")


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
    schema = raw.get("schema", {})
    schema = schema if isinstance(schema, dict) else {}
    return Param(
        name=raw.get("name", ""),
        location=raw.get("in", ""),
        required=bool(raw.get("required", False)),
        type=_param_type(schema),
        description=_clean(raw.get("description")),
        enum=schema.get("enum"),
        default=schema.get("default"),
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
    for ctype in ("application/json", "application/ld+json",
                  "application/merge-patch+json", "multipart/form-data"):
        ct = content.get(ctype, {})
        schema = ct.get("schema", {}) if isinstance(ct, dict) else {}
        if not isinstance(schema, dict):
            continue
        for comp in ("allOf", "oneOf", "anyOf"):
            parts = schema.get(comp)
            if isinstance(parts, list) and parts:
                first = parts[0]
                if isinstance(first, dict) and "$ref" in first:
                    return first["$ref"].rsplit("/", 1)[-1]
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
                        f"{DEV_PORTAL_BASE}/{operation_id_to_dev_slug(op_id)}/"
                        if dev_links and op_id
                        else None
                    ),
                    deprecated=bool(op.get("deprecated", False)),
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
        "schemas_peticion": resolver_schemas_peticion(spec, endpoints),
        "paths_without_operations": orphans,
        "elements": [],
        "warnings": warnings,
    }


_DETALLES_PROPIEDAD = ("format", "example", "enum", "nullable", "default", "description")


def _tipo_de_propiedad(schema: Any) -> str | None:
    """Tipo legible de una propiedad: `$ref`, `array[Ref]`, `oneOf/anyOf` o `_param_type`."""
    if not isinstance(schema, dict):
        return None
    ref = schema.get("$ref")
    if isinstance(ref, str):
        return ref.rsplit("/", 1)[-1]
    items = schema.get("items")
    if schema.get("type") == "array" and isinstance(items, dict) and items.get("$ref"):
        return f"array[{items['$ref'].rsplit('/', 1)[-1]}]"
    for clave in ("oneOf", "anyOf"):
        variantes = schema.get(clave)
        if isinstance(variantes, list) and variantes:
            tipos = [t for t in (_tipo_de_propiedad(v) for v in variantes) if t]
            if tipos:
                return "|".join(dict.fromkeys(tipos))
    return _param_type(schema)


def _detalles_de_propiedad(schema: Any) -> dict[str, Any]:
    """Metadatos que ahorran prueba y error: `format`, `example`, `enum`, `nullable`…"""
    if not isinstance(schema, dict):
        return {}
    return {k: schema[k] for k in _DETALLES_PROPIEDAD if k in schema and schema[k] != ""}


def resolver_schemas_peticion(spec: dict, endpoints: list[Endpoint]) -> dict[str, dict]:
    """Resuelve los `requestBody.$ref` de las operaciones a su contenido.

    `Endpoint.request_schema` guardaba solo el **nombre** del ref, con lo que el
    cuerpo que hay que enviar para escribir quedaba invisible en el atlas. Sobre el
    tenant `tnm`: 244 operaciones declaran ref y **107 resuelven a un schema con
    `properties`**; las otras 137 son `{type: object}` sin propiedades y se marcan
    `stub` en vez de ocultarlas (un stub es información: el contrato no está
    declarado y hay que capturarlo del front).

    **`readOnly` se separa** (737 propiedades del tenant lo llevan): son de SALIDA y
    enviarlas es un error, así que no pueden aparecer mezcladas con las enviables —
    listarlas juntas invita a mandarlas. Ídem `writeOnly` (33), al revés.

    Devuelve `{nombre: {propiedades, solo_lectura, solo_escritura, obligatorias,
    detalles, stub, operaciones}}`, ordenado. `propiedades` son **solo las
    enviables**.
    """
    schemas = (spec.get("components") or {}).get("schemas") or {}
    ops_por_schema: dict[str, set[str]] = {}
    for ep in endpoints:
        if ep.request_schema:
            ops_por_schema.setdefault(ep.request_schema, set()).add(f"{ep.method} {ep.path}")
    salida: dict[str, dict] = {}
    for nombre in sorted(ops_por_schema):
        sch = schemas.get(nombre) or {}
        props = {n: d for n, d in (sch.get("properties") or {}).items() if isinstance(n, str)}
        solo_lectura = sorted(
            n for n, d in props.items() if isinstance(d, dict) and d.get("readOnly")
        )
        solo_escritura = sorted(
            n for n, d in props.items() if isinstance(d, dict) and d.get("writeOnly")
        )
        enviables = {
            n: _tipo_de_propiedad(d) for n, d in props.items() if n not in solo_lectura
        }
        detalles = {
            n: det for n, d in props.items() if (det := _detalles_de_propiedad(d))
        }
        salida[nombre] = {
            "propiedades": enviables,
            "solo_lectura": solo_lectura,
            "solo_escritura": solo_escritura,
            "obligatorias": sorted(sch.get("required") or []),
            "detalles": detalles,
            "stub": not props,
            "operaciones": sorted(ops_por_schema[nombre]),
        }
    return salida


def _render_flags_de_vista(elemento: dict) -> list[str]:
    """Del alta rápida: qué campos participan, cuáles obligatorios, cuáles protegidos.

    Se renderiza **solo `quick_creation`** (el flujo de creación, que es lo que hace
    falta para escribir) más los `protected` vistos en cualquier vista. Las cuatro
    vistas completas viven en `atlas.json`, que es lo que consumiría un agente.
    """
    vistas = elemento.get("vistas") or {}
    if not vistas:
        return []
    lines: list[str] = []
    alta = vistas.get("quick_creation") or []
    if alta:
        piezas = []
        for c in alta:
            marca = "**obligatorio**" if c.get("mandatory") else ("requerido" if c.get("required") else "")
            extra = f"={c['defaultValue']}" if c.get("defaultValue") is not None else ""
            piezas.append(
                f"`{_md_escape(c['name'])}{extra}`" + (f" ({marca})" if marca else "")
            )
        lines.append("- Alta rápida (`view/quick_creation`): " + ", ".join(piezas))
    protegidos = sorted({
        c["name"] for campos in vistas.values() for c in campos if c.get("protected")
    })
    if protegidos:
        lines.append(
            "- **protegidos** (no escribir): "
            + ", ".join(f"`{_md_escape(n)}`" for n in protegidos)
        )
    otras = sorted(v for v in vistas if v != "quick_creation")
    if otras:
        lines.append(
            "- otras vistas con flags (en `atlas.json`): "
            + ", ".join(f"`{v}` ({len(vistas[v])})" for v in otras)
        )
    return lines


def _sufijo_propiedad(tipo: str | None, detalles: dict | None, solo_escritura: bool) -> str:
    """`(string, date-time, ej. 2024-12-25)` — lo que evita descubrirlo por 500s."""
    partes: list[str] = []
    if tipo:
        partes.append(_md_escape(tipo) or "")
    for clave, plantilla in (("format", "{}"), ("enum", "enum: {}"), ("example", "ej. {}")):
        valor = (detalles or {}).get(clave)
        if valor is None:
            continue
        texto = ", ".join(str(v) for v in valor) if isinstance(valor, list) else str(valor)
        partes.append(plantilla.format(_md_escape(texto)))
    if (detalles or {}).get("nullable"):
        partes.append("nullable")
    if solo_escritura:
        partes.append("solo escritura")
    return f" ({'; '.join(p for p in partes if p)})" if partes else ""


def _render_cuerpos_escritura(atlas: dict) -> list[str]:
    esquemas = atlas.get("schemas_peticion") or {}
    if not esquemas:
        return []
    con_props = {n: e for n, e in esquemas.items() if not e["stub"]}
    stubs = sorted(n for n, e in esquemas.items() if e["stub"])
    lines = ["## Cuerpos de escritura declarados", ""]
    lines.append(
        f"Los `requestBody` que el OpenAPI declara, resueltos: **{len(esquemas)} schemas** "
        f"referenciados por las operaciones de escritura, de los que **{len(con_props)} traen "
        "`properties`**. Es el contrato de lo que hay que enviar; sin él solo se aprende a base "
        "de 500s. Cada schema se lista **una vez**, con las operaciones que lo usan (las parejas "
        "crear/actualizar suelen compartirlo). Las **obligatorias** (`required` del spec) van en "
        "negrita."
    )
    lines.append("")
    if con_props:
        lines.append(
            "⚠️ Las **`readOnly`** van en su propia columna: son de SALIDA y **no se envían**."
        )
        lines.append("")
        lines.append("| Schema | Operaciones | Propiedades a enviar | Solo lectura (no enviar) |")
        lines.append("|---|---|---|---|")
        for nombre in sorted(con_props):
            e = con_props[nombre]
            obl = set(e["obligatorias"])
            props = ", ".join(
                (f"**`{_md_escape(n)}`**" if n in obl else f"`{_md_escape(n)}`")
                + _sufijo_propiedad(t, e["detalles"].get(n), n in e["solo_escritura"])
                for n, t in sorted(e["propiedades"].items())
            )
            solo = ", ".join(f"`{_md_escape(n)}`" for n in e["solo_lectura"]) or "—"
            ops = "<br>".join(f"`{_md_escape(o)}`" for o in e["operaciones"])
            lines.append(f"| `{_md_escape(nombre)}` | {ops} | {props} | {solo} |")
        lines.append("")
    if stubs:
        lines.append(
            f"**{len(stubs)} schemas declarados sin `properties`** (`{{type: object}}` a secas). "
            "El ref existe pero el contrato no está declarado: hay que capturarlo del front antes "
            "de escribir contra ellos."
        )
        lines.append("")
        lines.append(", ".join(f"`{_md_escape(n)}`" for n in stubs))
        lines.append("")
    return lines


def query_param_families(atlas: dict) -> list[dict]:
    """Agrupa los nombres de parámetro `in=query` por familia (`filterGroup[..]`, `sort[..]`…).

    El atlas parsea los `parameters` de cada operación desde el OpenAPI, pero las tablas
    de endpoints solo emiten su **recuento**. Eso dejaba invisible la gramática que el
    spec declara literalmente —`filterGroup[filters][0][value][]` y compañía—, y de ahí
    salió un bug real en El Contable: filtros construidos con la raíz en plural, que la
    API **ignora en silencio** devolviendo 200 con el listado completo
    (INTEGRACION_SUDESPACHO §14.2).

    Devuelve, ordenado por familia (alfabético, para que el `git diff` entre corridas sea
    legible y añadir un parámetro no reordene la tabla):
    `[{familia, nombres:[...], ops:<nº de operaciones que la usan>}]`.
    """
    variantes: dict[str, set[str]] = {}
    ops: dict[str, set[tuple[str, str]]] = {}
    for ep in atlas.get("endpoints", []):
        for p in ep.get("parameters") or []:
            if p.get("location") != "query":
                continue
            nombre = p.get("name") or ""
            if not nombre:
                continue
            familia = nombre.split("[")[0] + ("[..]" if "[" in nombre else "")
            variantes.setdefault(familia, set()).add(nombre)
            ops.setdefault(familia, set()).add((ep.get("method", ""), ep.get("path", "")))
    return [
        {"familia": fam, "nombres": sorted(variantes[fam]), "ops": len(ops[fam])}
        for fam in sorted(variantes)
    ]


def _render_query_conventions(atlas: dict) -> list[str]:
    familias = query_param_families(atlas)
    if not familias:
        return []
    n_nombres = sum(len(f["nombres"]) for f in familias)
    estructuradas = [f for f in familias if len(f["nombres"]) > 1]
    simples = [f for f in familias if len(f["nombres"]) == 1]
    lines = ["## Convenciones de query (Fase A)", ""]
    lines.append(
        f"Nombres de parámetro `in=query` que declara el OpenAPI: **{n_nombres} distintos** en "
        f"**{len(familias)} familias**. Las tablas de arriba solo dan el *recuento* por operación "
        "(columna `Params`); aquí están los nombres, que es lo que hace falta para construir la "
        "query. Se listan una sola vez por familia: las que se repiten en decenas de operaciones "
        "comparten forma."
    )
    lines.append("")
    if estructuradas:
        lines.append("### Familias con varias variantes")
        lines.append("")
        lines.append("| Familia | Ops | Nombres declarados |")
        lines.append("|---|---|---|")
        for f in estructuradas:
            nombres = ", ".join(f"`{_md_escape(n)}`" for n in f["nombres"])
            lines.append(f"| `{_md_escape(f['familia'])}` | {f['ops']} | {nombres} |")
        lines.append("")
    if simples:
        lines.append("### Parámetros simples")
        lines.append("")
        lines.append(", ".join(f"`{_md_escape(f['nombres'][0])}`" for f in simples))
        lines.append("")
    return lines


def _md_escape(text: str | None) -> str:
    if not text:
        return ""
    return text.replace("|", "\\|").replace("\n", " ")


def _fase_b_estado(pb: dict) -> str:
    """Estado de la Fase B en TRES valores (D2, 2026-07-26).

    `ran` = se ejecutó; `complete` = se ejecutó **sin degradados**. El render
    original solo miraba `complete`, así que una corrida con 2 elementos
    degradados se presentaba como «⏳ pendiente» mientras el propio documento
    llevaba abajo las ~2.300 líneas del esquema. Son estados distintos:

    - `⏳ no ejecutada`      — nunca corrió la Fase B.
    - `✅ 89/89`             — corrió y resolvió todo.
    - `⚠️ 87/89 (2 degradados)` — corrió, pero con elementos sin resolver.
    """
    if not pb.get("ran"):
        return "⏳ no ejecutada"
    ok = pb.get("elements_ok", "?")
    total = pb.get("elements_total", "?")
    if pb.get("complete"):
        return f"✅ {ok}/{total}"
    return f"⚠️ {ok}/{total} ({pb.get('elements_degraded', '?')} degradados)"


def render_markdown(atlas: dict) -> str:
    """Render humano del atlas (generado — no editar a mano). Tolera atlas de Fase A y B."""
    meta = atlas.get("meta", {})
    summ = atlas.get("summary", {})
    oas = meta.get("sources", {}).get("oas3", {})
    lines: list[str] = []
    # Frontmatter (D6b): el atlas es doc de raíz de docs/ y entra en INDICE.md;
    # el guard de gobernanza exige `estado:`. Al ser generado, no se puede
    # añadir a mano de forma estable — lo emite el propio render.
    lines.append("---")
    lines.append("estado: vigente")
    lines.append("dueño: Nikolai Tyukhay")
    lines.append("---")
    lines.append("")
    lines.append("# Atlas del CRM sudespacho — inventario de endpoints")
    lines.append("")
    lines.append("> **GENERADO por `scripts.crm_atlas discover` — NO editar a mano.**")
    lines.append("> Regenerar: `python -m scripts.crm_atlas discover --phase all`. "
                 "El `git diff` entre corridas = deriva del tenant.")
    lines.append("> Diseño: `docs/superpowers/specs/2026-07-20-crm-atlas-descubrimiento-design.md`.")
    lines.append("> Única excepción al «NO editar a mano»: alinear a mano estas líneas de cabecera "
                 "con lo que ya emite el render corregido, cuando no hay corrida en vivo "
                 "disponible. Cualquier otra edición se pierde en la siguiente corrida.")
    lines.append("")
    lines.append("| Meta | Valor |")
    lines.append("|---|---|")
    lines.append(f"| Tenant | `{meta.get('tenant', '?')}` |")
    lines.append(f"| Generado | {meta.get('generated_at') or '(sin sello)'} |")
    lines.append(f"| Fuente OAS3 | `{oas.get('url', '?')}` |")
    lines.append(f"| OpenAPI | {oas.get('openapi')} · {oas.get('info_title')} v{oas.get('info_version')} |")
    lines.append(f"| Auth global | `{oas.get('global_security_auth', '?')}` "
                 f"(header `{_security_header(oas)}`) |")
    lines.append(f"| Fase B (esquema por elemento) | {_fase_b_estado(meta.get('phase_b', {}))} |")
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

    lines.extend(_render_query_conventions(atlas))
    lines.extend(_render_cuerpos_escritura(atlas))

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

    # Fase B — esquema por elemento
    elements = atlas.get("elements", [])
    if elements:
        pb = meta.get("phase_b", {})
        total = pb.get("elements_total", len(elements))
        ok = pb.get("elements_ok", "?")
        lines.append(f"## Esquema por elemento — {ok}/{total} resueltos")
        lines.append("")
        degraded = [e for e in elements if "failed" in (e.get("probes") or {}).values()]
        if degraded:
            lines.append("### Elementos con descubrimiento degradado")
            lines.append("")
            lines.append("| Elemento | Sondas fallidas |")
            lines.append("|---|---|")
            for e in degraded:
                failed = [k for k, v in (e.get("probes") or {}).items() if v == "failed"]
                lines.append(f"| `{_md_escape(e['slug'])}` | {', '.join(sorted(failed))} |")
            lines.append("")
        for e in elements:
            lines.append(f"### {_md_escape(e['slug'])}")
            lines.append("")
            flds = e.get("fields") or []
            if flds:
                lines.append("| Campo | Tipo |")
                lines.append("|---|---|")
                for f in flds:
                    lines.append(f"| `{_md_escape(f.get('name'))}` | {_md_escape(f.get('type') or '')} |")
                lines.append("")
            rel = e.get("relations")
            if rel:
                lines.append(f"- Relaciones · parent: {', '.join(rel.get('parent', []))} · "
                             f"children: {', '.join(rel.get('children', []))}")
            for prop, vals in (e.get("enums") or {}).items():
                labs = ", ".join(_md_escape(f"{v.get('id')}={v.get('label')}") for v in vals)
                lines.append(f"- enum `{_md_escape(prop)}`: {labs}")
            ftne = e.get("field_types_no_enumerados") or {}
            if ftne:
                lines.append(f"- campos no enumerados (por tipo): "
                             + ", ".join(f"`{k}`={v}" for k, v in sorted(ftne.items())))
            lines.extend(_render_flags_de_vista(e))
            lines.append("")
    return "\n".join(lines) + "\n"


def render_digest(atlas: dict) -> str:
    """Digest de deriva (~100-200 líneas): superficie legible en `git diff`.

    Por módulo (tag): nº de ops. Por elemento: nº de campos + hash del esquema.
    Es el artefacto commiteado cuyo diff se REVISA (el `atlas.json` es demasiado
    grande; el `.md` es para leer, no para revisar el diff).
    """
    meta = atlas.get("meta", {})
    summ = atlas.get("summary", {})
    out: list[str] = []
    out.append("# Digest del atlas del CRM sudespacho")
    out.append("")
    out.append("> Superficie de DERIVA (legible en diff). Regenerar: "
               "`python -m scripts.crm_atlas discover --phase all`. NO editar a mano.")
    out.append("")
    out.append(f"## Digest — tenant `{meta.get('tenant', '?')}`")
    out.append("")
    out.append(f"- endpoints: {summ.get('total_operations', '?')} ops / "
               f"{summ.get('total_path_keys', '?')} paths "
               f"({summ.get('paths_without_operations', 0)} huérfanos)")
    familias = query_param_families(atlas)
    if familias:
        # La superficie de query también deriva: si el CRM renombra un parámetro (o cambia
        # `[value][]` por `[value]`), el hash lo delata en el diff.
        blob = json.dumps([{f["familia"]: f["nombres"]} for f in familias],
                          sort_keys=True, ensure_ascii=False)
        h = hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]
        n_nombres = sum(len(f["nombres"]) for f in familias)
        out.append(f"- query: {n_nombres} nombres / {len(familias)} familias · {h}")
    esquemas = atlas.get("schemas_peticion") or {}
    if esquemas:
        # Si el CRM cambia un cuerpo de escritura (campo nuevo, uno que pasa a
        # obligatorio), el hash lo delata en el diff antes de que falle una alta.
        blob = json.dumps(esquemas, sort_keys=True, ensure_ascii=False)
        h = hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]
        con_props = sum(1 for e in esquemas.values() if not e["stub"])
        out.append(
            f"- cuerpos: {len(esquemas)} schemas de peticion "
            f"({con_props} con properties) · {h}"
        )
    out.append("")
    out.append("### Endpoints por módulo")
    for tag, n in summ.get("by_tag", {}).items():
        out.append(f"- {tag}: {n}")
    elements = atlas.get("elements", [])
    if elements:
        out.append("")
        out.append("### Elementos (campos · hash de esquema)")
        for el in elements:
            blob = json.dumps(
                {"fields": el.get("fields"), "relations": el.get("relations"),
                 "enums": el.get("enums")},
                sort_keys=True, ensure_ascii=False,
            )
            h = hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]
            out.append(f"- {el['slug']}: {len(el.get('fields') or [])} campos · {h}")
    return "\n".join(out) + "\n"


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


# ===========================================================================
# Fase B — esquema por elemento (x-api-key). Solo lectura de esquema.
# ===========================================================================

SELECT_TYPE = "Select"

# C1 — vistas que exponen `headers[].elementProperty` con los flags de escritura.
# Verificadas en vivo (2026-08-03) sobre `actuaciones`: quick_creation=3 campos,
# preview_view=11, global_quick_search=3, mass_update=15. Son las que aceptan
# `{elemento}` en la ruta; el resto (`view/list/{id}`, `view/search/{id}`…) van por
# id de vista y no se pueden recorrer por elemento.
VISTAS_CON_METADATOS = ("quick_creation", "preview_view", "global_quick_search", "mass_update")
# Tipos dinámicos respaldados por tabla — sus VALORES nunca se vuelcan (PII/config):
ENUM_DENYLIST = frozenset({
    "ListaUsuarios", "ListaBancos", "ListaGrupos", "ListaElemento",
    "ListaElementoSelect", "Tags",
})

_RETRY_STATUS = {429, 500, 502, 503, 504}
_PROBE_RE = re.compile(r"properties are\s*:?\s*(.+)", re.IGNORECASE)


@dataclass
class Field:
    name: str
    type: str | None
    label: str | None
    active: bool = True
    source: str = "view/config/fields"


# --- cliente + reintentos ---------------------------------------------------

def _jitter(delay: float) -> float:
    return delay * (1 + random.uniform(-0.2, 0.2))


def get_with_retry(client: httpx.Client, path: str, *, attempts: int = 5,
                   params: dict | None = None) -> httpx.Response:
    """GET con backoff exponencial ante 429/5xx (respeta `Retry-After`).

    NO la usa el probe 4b (su 500 es la respuesta esperada, no un error).
    Los 4xx no-429 se devuelven sin reintentar. Agotados los intentos → lanza.
    """
    resp = None
    for n in range(attempts):
        resp = client.get(path, params=params)
        if resp.status_code not in _RETRY_STATUS:
            return resp
        if n < attempts - 1:
            ra = resp.headers.get("Retry-After")
            delay = float(ra) if (ra and str(ra).isdigit()) else min(1.0 * (2 ** n), 30.0)
            time.sleep(_jitter(delay))
    raise CrmAtlasError(
        f"{path}: agotados {attempts} reintentos (último HTTP "
        f"{resp.status_code if resp is not None else '?'})."
    )


def atlas_client(base_url: str = PUBLIC_BASE_URL, *, timeout: float = 60.0) -> httpx.Client:
    """Cliente `x-api-key` para la Fase B. La key viene del entorno (secreto Windows)."""
    key = os.environ.get("SUDESPACHO_API_KEY", "").strip()
    if not key:
        raise CrmAtlasAuthError("Falta SUDESPACHO_API_KEY en el entorno.")
    return httpx.Client(
        base_url=base_url.rstrip("/"),
        headers={"x-api-key": key, "Accept": "application/json"},
        timeout=timeout,
    )


def auth_healthcheck(client: httpx.Client) -> None:
    """Fail-fast: si la auth global falla (401/403), aborta antes del bucle."""
    r = client.get("/api/elements")
    if r.status_code in (401, 403):
        raise CrmAtlasAuthError(f"Auth global rechazada (HTTP {r.status_code}). Revisa SUDESPACHO_API_KEY.")
    r.raise_for_status()


def fetch_elements(client: httpx.Client) -> list[str]:
    """Catálogo de slugs del tenant. Tolera lista plana y colección Hydra."""
    r = get_with_retry(client, "/api/elements")
    r.raise_for_status()
    data = r.json()
    members = data.get("hydra:member", data.get("items", data)) if isinstance(data, dict) else data
    if not isinstance(members, list):
        raise CrmAtlasError("/api/elements devolvió una forma inesperada.")
    slugs: set[str] = set()
    for it in members:
        if isinstance(it, dict):
            ident = it.get("id")
            slug = ident.get("value") if isinstance(ident, dict) else (ident if isinstance(ident, str) else None)
            if slug:
                slugs.add(slug)
    return sorted(slugs)


# --- parsers de esquema por elemento ----------------------------------------

def parse_fields_config(payload: Any) -> list[Field]:
    """4a: `{items:[{name,type,label,active,deleted}]}` → Field[] (ordenado, sin borrados)."""
    items = payload.get("items", []) if isinstance(payload, dict) else []
    fields: list[Field] = []
    for it in items:
        if not isinstance(it, dict) or it.get("deleted"):
            continue
        fields.append(Field(name=it.get("name", ""), type=it.get("type"),
                            label=it.get("label"), active=bool(it.get("active", True))))
    return sorted(fields, key=lambda f: f.name)


def parse_invalid_property_probe(resp: httpx.Response) -> list[str] | None:
    """4b (fallback): exige HTTP 500 + patrón `properties are:`.

    Un 200 (elemento que valida laxo) → None (NUNCA se trata como esquema: guarda
    anti-lectura-de-registros). Un 500 con otro mensaje → None.
    """
    if resp.status_code != 500:
        return None
    try:
        detail = resp.json().get("detail") or ""
    except Exception:
        return None
    m = _PROBE_RE.search(detail)
    if not m:
        return None
    return [f.strip() for f in m.group(1).replace(".", "").split(",") if f.strip()]


def parse_view_fields(payload: Any) -> list[dict]:
    """Campos de una vista (`/api/view/{vista}/{elemento}`) con sus flags de escritura.

    `view/config/{el}/fields` (4a) solo trae `id,name,label,type,active,deleted`. Los
    flags que hacen falta para **escribir** —`required`, `mandatory`, `protected`—
    viven aquí, dentro de `headers[].elementProperty`.

    ⚠️ **Son flags de la VISTA, no del campo:** `Subject` en `actuaciones` es
    `mandatory=true` en `quick_creation` y `false` en `mass_update`. Por eso se
    guardan por vista y nunca se colapsan a un invariante.
    """
    headers = payload.get("headers") or [] if isinstance(payload, dict) else []
    campos: list[dict] = []
    for h in headers:
        if not isinstance(h, dict):
            continue
        ep = h.get("elementProperty")
        if not isinstance(ep, dict) or not ep.get("name"):
            continue
        campo = {
            "name": ep["name"],
            "type": ep.get("type"),
            "label": ep.get("label"),
            "required": bool(ep.get("required")),
            "mandatory": bool(ep.get("mandatory")),
            "protected": bool(ep.get("protected")),
        }
        if ep.get("defaultValue") not in (None, ""):
            campo["defaultValue"] = ep["defaultValue"]
        campos.append(campo)
    return sorted(campos, key=lambda c: c["name"])


def parse_relations_config(payload: Any) -> dict:
    """5a: `{parent:[...],children:[...]}` (ordenado; tolera claves ausentes)."""
    if not isinstance(payload, dict):
        return {"parent": [], "children": []}
    return {
        "parent": sorted(payload.get("parent") or []),
        "children": sorted(payload.get("children") or []),
    }


def select_enum_fields(fields: list[Field]) -> list[str]:
    """Allowlist dura: solo `type=="Select"` se enumera. Los `Lista*`/`Tags` quedan fuera."""
    return [f.name for f in fields if f.type == SELECT_TYPE]


def parse_enums(payload: Any) -> list[dict]:
    """5b: `{enums:[{id,label}]}` → solo `{id,label}`, ordenado por id."""
    enums = payload.get("enums", []) if isinstance(payload, dict) else []
    out = [{"id": e.get("id"), "label": e.get("label")} for e in enums if isinstance(e, dict)]
    return sorted(out, key=lambda e: str(e.get("id")))


# --- orquestación por elemento ----------------------------------------------

def discover_element(client: httpx.Client, slug: str) -> dict:
    """Descubre el esquema de un elemento. Degrada por sub-llamada (no aborta).

    4a/5a/5b vía `get_with_retry`; 4b (probe) vía `client.get` directo (su 500 es
    la respuesta esperada). `relations=None` si falló; los campos no-`Select` se
    registran por tipo en `field_types_no_enumerados` (sus valores nunca se piden).
    """
    probes = {"fields": "failed", "relations": "failed", "enums": "ok"}
    fields: list[Field] = []
    # 4a — view/config/fields
    try:
        r = get_with_retry(client, f"/api/view/config/{slug}/fields")
        if r.status_code == 200:
            fields = parse_fields_config(r.json())
            probes["fields"] = "view/config/fields"
    except CrmAtlasError:
        pass
    # 4b — fallback (probe de propiedad inválida; SIN capa de reintento)
    if probes["fields"] == "failed":
        try:
            rp = client.get(f"/api/element_registries/{slug}",
                            params={"properties[0]": "zzz__invalid_probe__"})
            names = parse_invalid_property_probe(rp)
            if names is not None:
                fields = [Field(name=n, type=None, label=None, source="500-probe")
                          for n in sorted(names)]
                probes["fields"] = "500-probe"
        except Exception:  # noqa: BLE001 — degradación, nunca aborta
            pass
    # 5a — relaciones
    relations = None
    try:
        r = get_with_retry(client, f"/api/view/config/{slug}/relations")
        if r.status_code == 200:
            relations = parse_relations_config(r.json())
            probes["relations"] = "ok"
    except CrmAtlasError:
        relations = None
    # reparto de campos + 5b enums (solo Select)
    field_types_no_enumerados = {f.name: f.type for f in fields if f.type != SELECT_TYPE}
    enums: dict[str, list] = {}
    for prop in select_enum_fields(fields):
        try:
            r = get_with_retry(client, f"/api/view/enums/{slug}/{prop}")
            if r.status_code == 200:
                vals = parse_enums(r.json())
                if vals:
                    enums[prop] = vals
            else:
                probes["enums"] = "failed"
        except CrmAtlasError:
            probes["enums"] = "failed"
    # C1 — metadatos por vista (`required`/`mandatory`/`protected`/`defaultValue`).
    # Van en `probes_vistas`, NO en `probes`: una vista ausente no debe marcar el
    # elemento como degradado (`is_resolved`) ni disparar el circuit breaker.
    vistas: dict[str, list[dict]] = {}
    probes_vistas: dict[str, str] = {}
    for vista in VISTAS_CON_METADATOS:
        try:
            r = get_with_retry(client, f"/api/view/{vista}/{slug}")
            if r.status_code == 200:
                campos = parse_view_fields(r.json())
                probes_vistas[vista] = "ok"
                if campos:
                    vistas[vista] = campos
            else:
                probes_vistas[vista] = "failed"
        except CrmAtlasError:
            probes_vistas[vista] = "failed"
    return {
        "slug": slug,
        "fields": [asdict(f) for f in fields],
        "relations": relations,
        "enums": enums,
        "field_types_no_enumerados": field_types_no_enumerados,
        "vistas": vistas,
        "probes": probes,
        "probes_vistas": probes_vistas,
    }


def is_resolved(el: dict) -> bool:
    """Un elemento está resuelto si ninguna sonda falló (para --resume)."""
    return "failed" not in (el.get("probes") or {}).values()


# --- gate anti-PII ----------------------------------------------------------

_EMAIL_RE = re.compile(r"[\w.+-]+\s*@\s*[\w-]+(?:\s*\.\s*[\w]+)+")


def _parece_persona(s: str) -> bool:
    """Heurística: 3-4 tokens Title-Case, sin dígitos ni acrónimos (nombre completo).

    Deliberadamente NO marca 1-2 tokens (evita falsos positivos con provincias/países
    como 'A Coruña') ni tokens ALL-CAPS (códigos) ni con dígitos. Es un backstop sobre
    la barrera primaria (denylist `Lista*`), no el detector principal.
    """
    if not s:
        return False
    toks = s.split()
    if not (3 <= len(toks) <= 4):
        return False
    for t in toks:
        if any(ch.isdigit() for ch in t):
            return False
        if not (t[:1].isupper() and not t.isupper()):
            return False
    return True


def scan_atlas_for_pii(atlas: dict) -> list[str]:
    """Gate anti-PII: EMAIL (regex, bloqueante) + heurística de persona (→ cuarentena).

    Devuelve hits `"{slug}.{prop}: email|parece-persona"`; sin volcar el valor.
    Escanea `enums` y `warnings`. NO se confía en leak-scan (salta docs/).
    """
    hits: list[str] = []
    for el in atlas.get("elements", []):
        slug = el.get("slug", "?")
        for prop, vals in (el.get("enums") or {}).items():
            for v in vals:
                blob = f"{v.get('id', '')} {v.get('label', '')}"
                if _EMAIL_RE.search(blob):
                    hits.append(f"{slug}.{prop}: email")
                    break
                if _parece_persona(str(v.get("label", ""))):
                    hits.append(f"{slug}.{prop}: parece-persona")
                    break
    for w in atlas.get("warnings", []):
        if _EMAIL_RE.search(str(w)):
            hits.append("warnings: email")
    return hits


def quarantine_person_enums(atlas: dict) -> int:
    """Mueve a `field_types_no_enumerados` los enums `Select` con pinta de persona.

    No borra información de esquema (el campo sigue registrado por tipo), pero sus
    VALORES no se vuelcan. Devuelve cuántos enums se pusieron en cuarentena.
    """
    moved = 0
    for el in atlas.get("elements", []):
        enums = el.get("enums") or {}
        to_move = [p for p, vals in enums.items()
                   if any(_parece_persona(str(v.get("label", ""))) for v in vals)]
        for p in to_move:
            el.setdefault("field_types_no_enumerados", {})[p] = "Select(cuarentena-PII)"
            del enums[p]
            moved += 1
    return moved


# --- build + resume ---------------------------------------------------------

def build_atlas_phase_b(phase_a_atlas: dict, elements_results: list, *, tenant: str) -> dict:
    """Fusiona los resultados por elemento sobre el atlas de Fase A (hereda meta/summary/endpoints).

    `meta.phase_b` = métrica de completitud; `complete` solo si 0 degradados.
    `circuit_broken` si >50% degradados (fallo probablemente global → la CLI aborta).
    """
    atlas = dict(phase_a_atlas)
    meta = dict(atlas.get("meta", {}))
    meta["tenant"] = tenant
    results = sorted([r for r in elements_results if r], key=lambda e: e["slug"])
    n_deg = sum(1 for r in results if not is_resolved(r))
    total = len(results)
    meta["phase_b"] = {
        "ran": True,
        "elements_total": total,
        "elements_ok": total - n_deg,
        "elements_degraded": n_deg,
        "complete": n_deg == 0,
        "circuit_broken": total > 0 and n_deg > total // 2,
    }
    atlas["meta"] = meta
    atlas["elements"] = results
    atlas["warnings"] = sorted(atlas.get("warnings", []))
    return atlas


def load_previous_atlas(path) -> dict | None:
    """Lee el atlas.json previo (utf-8 explícito) para --resume. None si no existe."""
    from pathlib import Path
    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))
