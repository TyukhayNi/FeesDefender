# STATUS — FeesDefender

> Snapshot rápido del estado del proyecto. Actualizar al cerrar cada sesión.

**Última actualización:** 2026-04-28

---

## Estado general

| Ítem | Estado |
|------|--------|
| Tests | ✅ 25/25 |
| Pipeline | ⏳ No ejecutado aún end-to-end |
| Primer caso real | ✅ Creado, docs descargados |
| Taxonomía de casos | ✅ Actualizada en config.py |
| Task Scheduler | ⏳ Pendiente configurar |

---

## Arquitectura v2 — Decisiones tomadas (2026-04-28)

### Flujo de intake por tipo de caso

| Tipo | Trigger | Fuente documentos |
|------|---------|-------------------|
| Bad Debt | Marta Reynares comparte carpeta Drive operación | Drive engelvoelkers.com (W-XXXXXX) |
| Negativas / Vueltas / Incumplimiento | Nikolai crea expediente en CRM | Drive engelvoelkers.com (W-XXXXXX) |
| Defensiva (demandado) | Demanda llega por email a nikolai.tyukhay@engelvoelkers.com | Upload manual desde UI Streamlit |

### Drop Zone para documentos E&V

- Cuenta `engelvoelkers.com` pendiente de conectar en Cowork.
- Mientras tanto: upload directo desde la UI de Streamlit + opción carpeta designada en Drive tyukhay.legal.

### Output anonimizado

- Destino: `07_ANONIMIZADO/` en cada caso local.
- Subida al Drive de `tyukhay.legal` para acceso del equipo con sus LLMs.
- Anonymizer: integrar proyecto externo de anonimización ya en desarrollo (no construir desde cero).

### Creación expediente en sudespacho

- **Semiautomática**: FeesDefender prepara datos → botón "Crear en sudespacho" que el usuario confirma.
- Endpoint POST aún no confirmado. **Acción pendiente**: capturar POST en DevTools al crear un extrajudicial manualmente.

### Roles de intake

- Bad Debt y Negativas: Paola / Ana (cuando reciben notificación de Marta o de Nikolai).
- Defensiva: Nikolai (cuando recibe la demanda en su cuenta corporativa).
- Futuro: dar acceso a la UI a todo el equipo para que suban documentos ellos mismos.

---

## Taxonomía de casos (confirmada 2026-04-28)

### Posición actora — Engel reclama (7 tipos)

| Clave interna | Tag CRM | Descripción |
|---------------|---------|-------------|
| BAD_DEBT | BAD DEBT | Impago de factura de honorarios |
| NEGATIVA_OFERTA | NEGATIVA OFERTA | Cliente rechaza la oferta en condiciones del encargo |
| NEGATIVA_ARRAS | NEGATIVA ARRAS | Cliente rechaza firmar arras tras aceptar oferta |
| NEGATIVA_ESCRITURA | NEGATIVA ESCRITURA | Cliente rechaza firmar escritura tras firmar arras |
| NEGATIVA_CONTRATO_ARRENDAMIENTO | NEGATIVA CONTRATO ARRENDAMIENTO | Cliente rechaza formalizar contrato de arrendamiento |
| VUELTA | VUELTA | Cliente cierra la operación sin la agencia aprovechando su gestión |
| INCUMPLIMIENTO_EXCLUSIVA | INCUMPLIMIENTO EXCLUSIVA | Cliente incumple pacto de exclusividad del encargo |

### Posición defensiva — Engel demandado (3 tipos)

| Clave interna | Tag CRM | Descripción |
|---------------|---------|-------------|
| RESPONSABILIDAD_PROFESIONAL | RESPONSABILIDAD PROFESIONAL | Cliente reclama daños por negligencia de la agencia |
| DEVOLUCION_RESERVA | DEVOLUCION RESERVA | Cliente reclama devolución de reserva o compromiso de seriedad |
| LAU_20 | LAU 20 | Arrendatario reclama devolución honorarios (art. 20.1 LAU) |

---

## Primer caso real

**Case ID:** `BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU`
**Cliente:** EV MMC SPAIN, S.L.U.
**Expediente:** 648 (`expedientes_judiciales`)
**Docs descargados:** 5 archivos, 5,35 MB

**⚠️ Acción pendiente antes de lanzar pipeline:**
```powershell
cd "G:\Unidades compartidas\DESPACHO - PRODUCCION\Sudespacho.net\Base datos expedientes"
Remove-Item -Recurse -Force "data\CASOS\BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU\00_INPUT\sudespacho"
python -m scripts.run_pipeline "BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU"
```

---

## Próximas tareas (orden de prioridad)

1. **[NIKOLAI — 5 min]** Capturar en DevTools el POST de creación de expediente extrajudicial en sudespacho → endpoint + payload → desbloquea integración CRM.
2. **[NIKOLAI]** Conectar cuenta `nikolai.tyukhay@engelvoelkers.com` en Cowork → desbloquea intake Drive E&V.
3. **[Nuevo hilo]** Módulo `core/intake_drive.py` — pull desde carpeta Drive operación E&V al `00_INPUT/`.
4. **[Nuevo hilo]** Módulo `core/anonymizer.py` — integrar proyecto externo de anonimización.
5. **[Nuevo hilo]** Streamlit: nueva pestaña "Nuevo Caso" con formulario + botón "Crear en sudespacho".
6. **[Nuevo hilo]** Subida output anonimizado al Drive tyukhay.legal.
7. Limpiar `sudespacho/` residual y ejecutar pipeline end-to-end en caso real.
8. Configurar Windows Task Scheduler para `scheduled_sync.py` (diario 08:00).
9. Reforzar `prompts/viabilidad.md` con jurisprudencia sobre nexo causal.
10. Tests adicionales: `test_linker`, `test_scorer`, `test_pipeline`.

---

## Credenciales / variables de entorno críticas

- `SUDESPACHO_LEGACY_PHPSESSID` — caduca por inactividad. Si `check_legacy` falla, renovar desde DevTools → Application → Cookies → tnm.sudespacho.net.
- `SUDESPACHO_API_KEY` — API REST, estable.
- `SUDESPACHO_LEGACY_HOST` — `tnm.sudespacho.net` (fijo).
- `DRIVE_OUTPUT_FOLDER_ID` — carpeta Drive tyukhay.legal para output anonimizado (pendiente configurar).
- `DRIVE_EV_ROOT_FOLDER_ID` — carpeta raíz Drive engelvoelkers.com para intake E&V (pendiente cuenta corporativa).

---

## Arquitectura multi-expediente (implementada 2026-04-26)

- Una subcarpeta `sudespacho_{id}/` por expediente en `00_INPUT/`.
- Marcador `.pulled` JSON: `{doc_ids, last_sync, by_carpeta}`.
- 3 modos pull: skip (default) / incremental / force.
- `register_expediente(case_id, exp_id, element)` — registra en `_caso.md` frontmatter.
- `scheduled_sync.py` — itera todos los casos, pull incremental, log en `06_AI_COWORK/`.

---

## Estructura de carpetas de un caso (v2 — con anonimizado)

```
data/CASOS/{case_id}/
├── 00_INPUT/
│   ├── _caso.md
│   ├── sudespacho_{id}/      ← pull desde CRM
│   └── manual/               ← docs subidos manualmente / intake Drive
├── 01_PROCESADO/
├── 02_ANALISIS/
├── 03_DECISION/
├── 04_OUTPUT_PREDEMANDA/
├── 05_PROCEDIMIENTO/
├── 06_AI_COWORK/
├── 07_ANONIMIZADO/           ← Markdown sin PII → Drive tyukhay.legal → LLMs online
└── 90_NOTAS_PERSONALES/      ← zona del abogado, intocable
```

---

## Tests — última ejecución

```
pytest -q   →   25 passed
```
Módulos cubiertos: `case_manager`, `inventory`, `utils`,
`sync_sudespacho`, `sync_sudespacho_legacy`.
