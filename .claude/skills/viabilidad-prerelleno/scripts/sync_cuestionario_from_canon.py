#!/usr/bin/env python3
"""
sync_cuestionario_from_canon.py — Genera references/cuestionario_viabilidad.yaml
(la VISTA de la skill) a partir de la fuente única del repo:
data/_plantillas/cuestionario_viabilidad.yaml.

La skill NO mantiene un cuestionario propio: el canónico manda. Este script
deriva la vista que necesita el LLM en la 1ª pasada (pregunta + objetivo +
tipo + fuente + HITO de display + clase_fuente para enrutar documental/
testifical). Reejecutar tras cualquier cambio del canónico.

    python scripts/sync_cuestionario_from_canon.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]          # <repo>/_skills_drafts/viabilidad-prerelleno/scripts -> <repo>
# Tolera también la instalación en .claude/skills/<skill>/scripts/
_CANDIDATOS = [
    REPO_ROOT / "data" / "_plantillas" / "cuestionario_viabilidad.yaml",
    HERE.parents[3] / "data" / "_plantillas" / "cuestionario_viabilidad.yaml",
]
CANON = next((p for p in _CANDIDATOS if p.exists()), _CANDIDATOS[0])
OUT = HERE.parent / "references" / "cuestionario_viabilidad.yaml"

# slug `respalda` del canónico -> rótulo de HITO en la hoja INFORMACION (14 hitos)
SLUG2HITO = {
    "encargo": "ENCARGO", "identificacion_propietario": "IDENT. PROPIETARIO",
    "titularidad": "TITULARIDAD", "hoja_visita": "HOJA DE VISITA",
    "identificacion_buscador": "IDENT. BUSCADOR", "oferta": "OFERTA",
    "arras_arrendamiento": "ARRAS / ARRENDAMIENTO", "reconocimiento_arras": "RECON. HON. — ARRAS",
    "escritura": "ESCRITURA", "reconocimiento_escritura": "RECON. HON. — ESCRITURA",
    "reclamacion_juridico": "RECLAMACIÓN JURÍDICO", "respuesta_reclamacion": "RESPUESTA A LA RECLAMACIÓN",
    "oferta_vinculante_confidencial": "OFERTA VINCULANTE CONFIDENCIAL",
}
TIPO_DISP = {"texto_libre": "texto", "numero": "número"}
# Preguntas sin `respalda` que aun así alimentan una casilla de display.
SEC_OVERRIDE = {"comercializacion": "ACTIVIDADES", "vueltas": "(VUELTA)"}


def hito_for(sec_id: str, p: dict) -> str | None:
    r = p.get("respalda")
    if r:
        return SLUG2HITO.get(r[0], "—")
    return SEC_OVERRIDE.get(sec_id)


def main() -> int:
    c = yaml.safe_load(CANON.read_text(encoding="utf-8"))
    secciones = []
    for sec in c["secciones"]:
        preguntas = []
        for p in sec["preguntas"]:
            preguntas.append({
                "id": p["id"],
                "pregunta": p["texto"],
                "objetivo_probatorio": (p.get("objetivo_probatorio") or "").strip(),
                "tipo": TIPO_DISP.get(p.get("tipo_respuesta"), p.get("tipo_respuesta")),
                "fuente_probable": list(p.get("fuente_probable") or []),
                "hito": hito_for(sec["id"], p),
                "clase_fuente": p.get("clase_fuente"),
            })
        secciones.append({"seccion": sec["titulo"], "preguntas": preguntas})

    doc = {
        "cuestionario_viabilidad": {
            "descripcion": (
                "VISTA de la skill viabilidad-prerelleno. GENERADO desde "
                "data/_plantillas/cuestionario_viabilidad.yaml — NO editar a mano; "
                "regenerar con scripts/sync_cuestionario_from_canon.py. Columnas fijas "
                "de plantilla (NO TOCAR): SECCIÓN, ID, PREGUNTA, OBJETIVO PROBATORIO, TIPO, "
                "FUENTE PROBABLE, HITO."
            ),
            "regla_enrutamiento": (
                "clase_fuente es un DEFAULT: 'documental' = pre-rellenable si un documento de "
                "00_Input la responde; 'testifical' = el documento no la acredita → "
                "¿PENDIENTE ENTREVISTA?=sí. En ejecución, si un documento NO resuelve una "
                "pregunta documental, también pasa a ¿PENDIENTE?=sí. Nunca se rellena por inferencia."
            ),
            "terminologia": {
                "propietario": "quien ofrece el bien (nunca 'vendedor')",
                "buscador": "quien busca (nunca 'comprador' ni 'arrendatario')",
            },
            "secciones": secciones,
        }
    }

    OUT.write_text(
        "# === FICHERO GENERADO — no editar a mano (ver cabecera 'descripcion') ===\n"
        + yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, default_flow_style=False, width=100),
        encoding="utf-8",
    )
    n = sum(len(s["preguntas"]) for s in secciones)
    print(f"OK · {OUT} · {n} preguntas desde {CANON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
