"""Diagnóstico Fase 0 — descarga de documentos del CRM (expediente judicial 649).

Objetivo: identificar la ruta REST (solo x-api-key) que sustituya al endpoint
roto ``GET /api/files/presigned_download_url/{doc_id}`` (HTTP 400 "Unable to
generate an IRI for App\\Upload\\...\\DTO\\Download"; ver docs/DEAD_ENDS.md).

Qué hace (una sola corrida, evidencia en el boundary):
  1. Lista los docs del expediente 649 via list_gdocu_docs_rest (debe dar 26).
  2. Toma 2 doc_ids reales.
  3. Consulta la spec OAS3 (/api/docs.json) y vuelca los paths que casen con
     download / presigned / Download / zip.
  4. Para cada doc, prueba varias rutas candidatas con x-api-key y registra
     status + content-type + body[:400] de cada una.
  5. Si alguna devuelve una URL S3, intenta el GET de esa URL (sin auth) y
     reporta status + bytes.

Uso:
    python -m scripts.diag_presigned_download            # expediente 649
    python -m scripts.diag_presigned_download 657        # otro expediente
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402

import core.config  # noqa: E402,F401  (fuerza load_dotenv)
from core.sync_sudespacho import SudespachoClient, SudespachoConfig  # noqa: E402


def _short(s: str, n: int = 400) -> str:
    s = s.replace("\n", " ").strip()
    return s if len(s) <= n else s[:n] + "…"


def probe(client: httpx.Client, method: str, path: str, **params) -> dict:
    try:
        r = client.request(method, path, params=params or None)
    except httpx.HTTPError as exc:
        return {"path": path, "error": str(exc)}
    ct = (r.headers.get("content-type") or "").lower()
    body = "" if "application/zip" in ct or "octet-stream" in ct else r.text
    return {
        "path": path,
        "params": params or None,
        "status": r.status_code,
        "content_type": ct,
        "len": len(r.content),
        "body": _short(body),
    }


def main() -> int:
    expediente_id = sys.argv[1] if len(sys.argv) > 1 else "649"
    element = "expedientes_judiciales"

    cfg = SudespachoConfig.from_env()
    print(f"# base_url   : {cfg.base_url}")
    print(f"# auth_header: {cfg.auth_header}  (scheme={cfg.auth_scheme!r})")
    print(f"# expediente : {expediente_id}  element={element}\n")

    client = SudespachoClient(cfg)

    # --- 1. Listado de docs (debe funcionar) -------------------------------
    docs = client.list_gdocu_docs_rest(expediente_id, element=element)
    print(f"## list_gdocu_docs_rest → {len(docs)} documentos")
    for d in docs[:5]:
        print(f"   - id={d.doc_id}  carpeta={d.id_carpeta_label!r}  "
              f"mime={d.mime}  size={d.size}  name={d.filename!r}")
    if not docs:
        print("!! sin documentos — no se puede continuar")
        return 1
    sample = [d.doc_id for d in docs[:2]]
    print(f"\n## muestra de doc_ids a probar: {sample}\n")

    raw = client._client  # httpx.Client con x-api-key ya inyectado

    # --- 2. Spec OAS3: localizar rutas de descarga -------------------------
    print("## OAS3 (/api/docs.json) — paths que casan con download/presigned/zip")
    try:
        spec = raw.get("/api/docs.json")
        if spec.status_code == 200:
            data = spec.json()
            paths = data.get("paths", {})
            hits = [p for p in paths
                    if any(k in p.lower()
                           for k in ("download", "presigned", "/zip", "/file"))]
            for p in sorted(hits):
                methods = ",".join(sorted(paths[p].keys()))
                print(f"   [{methods}] {p}")
            # buscar el DTO Download en components
            comps = data.get("components", {}).get("schemas", {})
            dl_schemas = [k for k in comps if "download" in k.lower()]
            print(f"   schemas con 'download': {dl_schemas}")
        else:
            print(f"   !! /api/docs.json → HTTP {spec.status_code}")
    except Exception as exc:  # noqa: BLE001
        print(f"   !! error consultando OAS: {exc}")
    print()

    # --- 3. Probar rutas candidatas por doc -------------------------------
    candidates = [
        # (method, path_template, params)
        ("GET", "/api/files/presigned_download_url/{id}",
         {"relatedElement": element, "relatedId": expediente_id, "direction": "left"}),
        ("GET", "/api/files/presigned_download_url/{id}", {}),
        ("GET", "/api/documents/presigned_urls/s3/download/{id}", {}),
        ("GET", "/api/documents/presigned_urls/local/download/{id}", {}),
        ("GET", "/api/documents/{id}/downloadUri", {}),
        ("GET", "/api/documents/{id}/download", {}),
        ("GET", "/api/documents/{id}/file", {}),
        ("GET", "/api/files/{id}/download", {}),
        ("GET", "/api/files/download/{id}", {}),
    ]

    for doc_id in sample:
        print(f"### doc_id={doc_id}")
        for method, tpl, params in candidates:
            path = tpl.format(id=doc_id)
            res = probe(raw, method, path, **params)
            tag = f"{res.get('status', 'ERR')}"
            print(f"  [{tag:>4}] {method} {path}  params={res.get('params')}")
            print(f"         ct={res.get('content_type','')} len={res.get('len','')} "
                  f"body={res.get('body', res.get('error',''))}")
            # Si parece una URL S3, intentar el GET real
            body = res.get("body", "") or ""
            url = None
            txt = body.strip().strip('"')
            if txt.startswith("http"):
                url = txt
            else:
                try:
                    payload = json.loads(body)
                    if isinstance(payload, dict):
                        for k in ("url", "downloadUrl", "presignedUrl",
                                  "presigned_url", "doc"):
                            v = payload.get(k)
                            if isinstance(v, str) and v.startswith("http"):
                                url = v
                                break
                except Exception:  # noqa: BLE001
                    pass
            if url:
                try:
                    with httpx.Client(timeout=60, follow_redirects=True) as ext:
                        rr = ext.get(url)
                    print(f"         ↳ S3 GET {url[:70]}… → {rr.status_code} "
                          f"({len(rr.content)} bytes)")
                except httpx.HTTPError as exc:
                    print(f"         ↳ S3 GET falló: {exc}")
        print()

    client.__exit__(None, None, None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
