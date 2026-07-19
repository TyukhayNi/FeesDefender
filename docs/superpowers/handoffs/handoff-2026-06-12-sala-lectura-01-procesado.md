---
tipo: handoff
estado: historico
creado: 2026-06-12
origen: sesión de planificación Cowork
destino: Claude Code (implementación de 01_Procesado)
consumido_por: "core/sala_lectura.py (F4–F6), luego DEPRECADO por la skill organizar-sala-lectura v1.3+"
migrado: "2026-07-19 (regla MEJORAS #77 / GOBERNANZA §5)"
---

# HANDOFF — Sala de lectura y organización de `01_Procesado`

> **Origen:** sesión de planificación Cowork, 2026-06-12.
> **Destino:** Claude Code (implementación).
> **Estado:** aprobado por Nikolai. Listo para llevar a `PLAN.md` e implementar.
> **Frontera:** todo el código lo implementa Claude Code. Cowork ha hecho el diseño,
> los prototipos (`INDICE.md` / `CRONOLOGIA.md`) y este handoff.

---

## 1. Objetivo

Montar en `01_Procesado` una capa orientada al humano:

- una **sala de lectura** donde el abogado consulte el caso completo (documentos, conversaciones, entrevistas, procesal) **en claro y en orden**;
- una **capa de texto** (`MD/`) para búsqueda a texto completo.

Aprovechar la API de **Scaleway** (Generative APIs, LLM soberano UE) para clasificar y **fechar** documentos sin exponer datos personales fuera de la UE.

## 2. Decisiones cerradas

1. **`procesal@` NO se conecta como fuente de documentos.** Los documentos ya entran por el CRM (sudespacho) → `00_Input/05_CRM`. Conectar Gmail duplicaría el ciclo subida/descarga del CRM.
2. **Scaleway, doble rol:**
   - (a) Clasificador/extractor de **tipo** y **fecha** de documento para organizar el intake.
   - (b) Sobre `procesal@`, solo como **señal** (plazos, señalamientos, vinculación al expediente → El Contable/alertas), nunca re-ingiriendo adjuntos.
   - Motor **híbrido**: reglas deterministas primero; LLM solo para el residuo ambiguo.
3. **Capas** (sobre la estructura existente del expediente):
   `00_Input` (crudo, inmutable, fuente de verdad) → `01_Procesado` (capa humana) → `06_Anonimizado` (MD tapado para LLM) → `07_AI cowork` (taller del LLM).
   Todo aguas abajo de `00_Input` es **regenerable**.

## 3. Estructura de `01_Procesado`

```
01_Procesado/
├── Sala lectura/        lo que el abogado LEE
│   ├── INDICE.md · CRONOLOGIA.md      (portada: por fuente / narrativa)
│   ├── Drive E&V/   CRM/              PDF originales OCR'd, en bundles
│   └── WhatsApp/   Entrevistas/       MD nativos (aquí el .md ES el documento)
├── MD/                  rendiciones en claro de los binarios (PDF→texto),
│                        espeja la estructura de Sala lectura, solo para búsqueda
├── _manifiesto.jsonl    trazabilidad: original → nombre canónico, SHA-256, fuente, fecha
└── _revisar/            cuarentena de lo no clasificado con confianza (repaso humano)
```

## 4. Reglas de organización

- **Subcarpetas por fuente:** Drive E&V, CRM, WhatsApp, Entrevistas.
- **Nombre de fichero:** `<AAAA-MM-DD>_<tipo>_<descripción breve>.<ext>`, en tipo oración.
- **Documentos compuestos** (escrito + adjuntos; chat + multimedia) → **bundle**: subcarpeta con el principal (conserva su **nombre descriptivo**) y los anexos en **subcarpeta**: `adjuntos/` para escritos, `media/` para chats. Decisión a cargo del *detector de conjunto* previsto en la reorg de `05_CRM`.
- **Copia, no mueve:** `00_Input` queda intacto.
- **Dedup por SHA-256:** mismo documento en dos fuentes → una sola entrada (mismo hash que ya usa el anonimizador).
- **Índices:** un documento = una entrada (PDF + MD no duplican línea); el enlace va al **original**, con "ver texto" opcional al MD. Generados automáticamente desde `indice_documental.yaml`; **solo lectura**.

## 5. Routing de los outputs del pipeline

De una sola extracción (OCR → texto → anonimización):

| Output | Destino |
|---|---|
| PDF con capa de texto (OCR'd) | `01_Procesado/Sala lectura/<fuente>/` (original legible) |
| MD en claro (paso intermedio) | `01_Procesado/MD/` (**derivación NUEVA a implementar**) |
| MD anonimizado (paso final) | `06_Anonimizado/` (sin cambios) |

El MD anonimizado **nunca** entra en `MD/`. `MD/` (claro, en 01) y `06_Anonimizado` (tapado) son gemelos de la misma extracción.

## 6. Fronteras y RGPD

- `01_Procesado` es **en claro** → acceso restringido al despacho (fuera del rol `ev_team_leader`).
- El LLM **solo lee de `06`**, nunca de `01`.
- `90_Notas personales` queda reservada y fuera de la automatización.
- Persistir texto claro en `MD/` es acto relevante a efectos RGPD → confinado a 01.

## 7. Alcance de la primera fase

Empezar por **ficheros en `01_Procesado`** (formato ya prototipado: `INDICE.md` + `CRONOLOGIA.md`). Streamlit y artifact de Cowork quedan **diferidos**.

## 8. Tareas de implementación (Claude Code)

1. Crear subcarpetas `Sala lectura/` y `MD/` dentro de `01_Procesado` (scaffolding del caso). Mantener `_manifiesto.jsonl` y `_revisar/`.
2. **Grifo de MD en claro:** que el pipeline persista el paso intermedio (texto en claro) a `01_Procesado/MD/`, espejando la ruta de `Sala lectura/`, antes de anonimizar a `06`.
3. **Copiador organizado:** poblar `Sala lectura/<fuente>/` desde `00_Input` (CRM ← `05_CRM`; Drive E&V; WhatsApp; Entrevistas), aplicando taxonomía + patrón de nombre. Copia, no mueve.
4. **Detector de conjunto / bundles** (reaprovechar el de la reorg `05_CRM`): atómico → fichero; compuesto → carpeta con principal + `adjuntos/`|`media/`.
5. **Dedup por SHA-256** y registro en `_manifiesto.jsonl` (original → canónico, SHA, fuente, fecha).
6. **Generador de índices** `INDICE.md` (por fuente) y `CRONOLOGIA.md` (narrativa, ascendente) desde `indice_documental.yaml`; un documento = una entrada; enlaces relativos al original.
7. **Clasificador/fechador** (Scaleway, híbrido): tipo + fecha por documento; *fallback* de fecha = fecha de entrada en CRM/Drive; sin confianza → `_revisar/`.

### Criterios de aceptación

- `00_Input` no se modifica en ninguna ejecución.
- Re-ejecución **idempotente**: no duplica ficheros ni re-renombra lo ya canónico.
- Ningún camino de IA accede a `01_Procesado`.
- Cada documento en `Sala lectura/` tiene su entrada en los índices y su rendición en `MD/` (si es binario), o es MD nativo.

## 9. Pendientes de decisión (no bloquean el arranque)

1. **Cerrar la taxonomía documental** (lista cerrada de tipos + patrón de nombre) en `indice_documental.yaml`. — Lo redacta Cowork.
2. **DPA / encargo de tratamiento con Scaleway** antes de enviarle documental de E&V.
3. **Correspondencia suelta** (email que nunca llega a ser documento del CRM): ¿nota normalizada en el expediente o fuera de la sala de lectura?

## 10. Referencias del repo

- `core/config.py` → `CASO_SUBDIRS`, subcarpetas de intake.
- `core/anon/api.py`, `core/anon/mapa_caso.py` → pipeline y mapa (SHA-256, idempotencia, `06`→`07`).
- Plan reorg `05_CRM` (detector de conjunto + bundles por metadato) → reaprovechar para los bundles de `01_Procesado`.
