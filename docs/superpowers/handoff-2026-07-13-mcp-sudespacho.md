# Handoff — MCP `sudespacho` (envolver → sustituir progresivo)

> **Autocontenido para una sesión nueva de Claude Code (sin memoria de la
> conversación previa).** Este handoff viene de un brainstorming hecho en
> Cowork (jurídico/planificación) con Nikolai el 2026-07-13. Cowork NO ha
> tocado código ni el repo — este fichero se entrega para que Claude Code lo
> mueva a `docs/superpowers/` y encadene el flujo habitual (spec → plan).

Antes de empezar, leer `docs/INTEGRACION_SUDESPACHO.md`,
`docs/ARQUITECTURA_CRM_SUDESPACHO.md` y `docs/DEAD_ENDS.md` (bug
`presigned_download_url`). Verificar contra el código actual de
`core/sudespacho_create.py` y `core/sync_sudespacho_legacy.py` — los datos de
abajo vienen de memoria de Cowork con 46-69 días de antigüedad y pueden haber
cambiado.

## Qué ya existe (estado conocido, a verificar)

- Dos superficies: API REST (`api-crm-commons-pro.sudespacho.biz`, auth
  `x-api-key`, sirve lectura y escritura) y frontal legacy PHP
  (`tnm.sudespacho.net`, tres cookies: PHPSESSID + `@token` JWT +
  `@refreshToken`).
- Endpoints REST confirmados (2026-05-06/11): listar documentos, crear
  expediente judicial/extrajudicial, crear colaborador, vincular entidades
  (`relation_element`), buscar colaboradores — todos con `x-api-key`, sin
  PHPSESSID.
- Roto desde 2026-05-11: `GET /api/files/presigned_download_url/{doc_id}` →
  400 (bug backend, API Platform IRI generation). Bloquea descarga de
  documentos vía REST.
- Pendientes de validar: convertir extrajudicial→judicial
  (`POST /api/expedient/convert/{id}`), crear tags
  (`POST /api/tags/{element}?field=tags`).
- Gotchas de esquema: `properties[]` obligatorio (o 500), operador `equal` no
  `eq`, ids namespace-independientes entre judicial/extrajudicial (mismo id
  numérico = expedientes distintos), autoincrementales que el cliente debe
  calcular (`max(...)+1`), no confiar en auto-asignación del servidor.

## Objetivo del MCP

Dar acceso directo (desde Cowork/chat, sin pasar por la app Streamlit) a
consultar y —más adelante— operar el CRM sudespacho. Mono-tenant (`tnm`), sin
necesidad de multicuenta.

**Estrategia acordada con Nikolai: envolver primero, sustituir después, por
operación — nunca de golpe.**

1. **Envolver**: el MCP llama a la misma API REST que ya usa
   `sudespacho_create.py`. Los dos caminos conviven; la app en producción
   (Ana/Paola) no se toca.
2. **Validar en paralelo**: comparar, operación por operación, lo que
   devuelve el MCP contra el código existente.
3. **Sustituir por operación cuando madura**: empezar por operaciones de
   solo lectura (menos riesgo) antes que escritura (crear expediente,
   vincular). La operación con usuarias activas en Streamlit se sustituye la
   última, y solo tras un periodo sin discrepancias.

Precedente directo de patrón a copiar: `plugins/google_despacho_mcp/`
(`docs/superpowers/specs/2026-07-08-google-despacho-mcp-design.md`) —
FastMCP stdio local, lógica pura (`*_ops.py`, `service`/cliente inyectable)
separada del wrapper de tools (`server.py`), tests con fake inyectado sin API
viva, entrega `.dxt` + puente Claude Desktop.

## Credenciales (decisión cerrada en brainstorming)

- Hoy el `x-api-key` vive en `.env` (`SudespachoLegacyConfig`), lo lee la app.
- Fase envolver: el MCP (proceso aparte) necesita su propia copia/acceso a la
  misma clave — duplicación temporal aceptable.
- Fase sustituir: cuando una operación deja de vivir en la app y pasa a
  delegar en el MCP, la clave para esa operación solo necesita vivir en el
  entorno del proceso del MCP (fuera del repo, patrón
  `~/.google-despacho/` / variable de entorno) — nunca en el repo ni en el
  chat.

## Abierto — pendiente de cerrar con Nikolai antes del spec

1. **Alcance de escritura**: ¿el MCP expone solo lectura (consultar
   expedientes/documentos/colaboradores) en su primera fase, o también
   escritura (crear expediente, vincular) con guardarraíles análogos al de
   compartición externa de Drive?
2. **Prioridad de la descarga de documentos**: ¿destrabar
   `presigned_download_url` (o usar el frontal legacy como fallback) es parte
   de la fase 1 del MCP, o queda fuera de alcance inicial?
3. **Orden de fases**: por precedente (Google despacho), conviene F1 =
   lectura pura (valida fontanería) antes de F2 = escritura.

## Regla dura que no se rompe

Antes de implementar cualquier endpoint nuevo (los "pendientes de validar",
o cualquier otro no listado arriba): **leer la spec OAS3**
(`https://api-crm-commons-pro.sudespacho.biz/api/docs`) **y capturar un HAR**
real desde el CRM (DevTools → Network, crear un registro de prueba, exportar
HAR, borrar el registro de prueba después). La spec OAS3 no da los nombres
reales de las `properties` — eso solo lo da el HAR. Protocolo ya validado en
`docs/INTEGRACION_SUDESPACHO.md` sección 0.

## Próximo paso

Brainstorming en Claude Code con Nikolai para cerrar los 3 puntos de
"Abierto", luego spec en `docs/superpowers/specs/` (mismo formato que
`2026-07-08-google-despacho-mcp-design.md`), luego encadenar `writing-plans`
para el plan de implementación de F1.
