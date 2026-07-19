# Changelog — exportar-correos-etiqueta

## 1.2 (2026-07-18)
- **Fix de compatibilidad Cowork:** la `description` contenía placeholders con ángulos
  (`<AAAA-MM-DD>`, `<NN>`, `<caso>`) que claude.ai rechaza al importar («SKILL.md description
  cannot contain XML tags»). Reescritos sin ángulos (`AAAA-MM-DD_email_NN`, «un caso»). Solo
  texto del frontmatter; sin cambios de comportamiento.

## 1.1 (2026-06-23)
- Motor implementado y validado en Claude Code (`core/email_export.py` + CLI + botón
  Streamlit + plugin v0.2.0). Corrida real W-02VND1: 122 `.eml` + adjuntos.
- **Estructura plana por defecto** (solo `.eml`, con adjuntos embebidos); extracción
  de adjuntos a subcarpetas pasa a ser opcional (`--extraer-adjuntos` / checkbox).
- La `ref` acepta el **W-code** (`meta.id_go`), que se resuelve al case_id canónico
  (nombre de carpeta) — evita crear carpetas erróneas al pasar el W-code.
- **Traza forense:** registra SHA-256 en `IntakeManifest` + evento `upload_email`.

## 1.0 (2026-06-22) — borrador
- Alta de la skill (rol:input, atomica). Redactada en Cowork (hilo BaRS1 [inmueble]).
- Orquesta el motor local `core/email_export.py` + CLI `scripts/export_label_emails.py`
  (pendientes de implementar en Claude Code; ver PLAN.md [SIGUIENTE-EXPORT-ETIQUETA-EMAIL]).
- Pendiente: empaquetar con `scripts/package_skill.py` y re-importar el `.skill` tras
  validar la implementación con `pytest`.
