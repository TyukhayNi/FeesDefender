---
estado: historico
dueño: Nikolai Tyukhay
---

# Spec — MCP propio "Google despacho" (Drive + Calendar, multicuenta)

_Encargo a Claude Code · FeesDefender · 2026-07-08_

## 1. Objetivo
Un único conector Google multicuenta que sostenga las dos cuentas a la vez, seleccionadas por parámetro `account`, calcado del patrón del conector Gmail-despacho. Elimina la reautenticación al cambiar de cuenta (el conector nativo de Drive es mono-cuenta; la doble instancia no existe, confirmado en docs Anthropic).

## 2. Cuentas y scope subjetivo
- `nikolai.tyukhay@engelvoelkers.com` → My Drive + todo lo compartido con esa cuenta + Calendar.
- `nikolai.tyukhay@tyukhay.legal` → **My Drive completo + TODAS las unidades compartidas** accesibles + Calendar.

Toda búsqueda/listado con soporte de unidades compartidas: `corpora=allDrives`, `includeItemsFromAllDrives=true`, `supportsAllDrives=true`.

## 3. Consolidación de conectores
- **Jubilar el conector nativo "EXPEDIENTES"** en cuanto la capa Drive del MCP esté viva (el MCP es superconjunto). Un conector menos, sin pérdida.
- **Fundir EXPEDIENTES XL: apuntado, NO se ejecuta ahora.** Requeriría un MCP híbrido con capa filesystem/rclone en el PC y migración en paralelo por haber usuarias en producción. Queda como idea futura; XL sigue operativo.
- **Gmail-despacho: fuera.** Otro servicio, otro radio de fallo.

## 4. Tools de Drive (todas con `account`, ambas cuentas)
Lectura/búsqueda: `list_accounts`, `list_shared_drives`, `search_files` (con `drive_id`/`corpora`/`supportsAllDrives`), `list_recent_files`, `get_file_metadata`, `get_file_permissions`, `read_file_content`, `download_file_content`.

Escritura: `create_file`, `create_folder`, `copy_file`, `update_file_content` (edición in-place), `update_file_metadata` (renombrar), `move_file`, `delete_file` (papelera por defecto; `permanent=true` solo con flag).

Permisos: `create_permission`, `update_permission`, `delete_permission`.

Resto (todas incluidas): comentarios/respuestas (crear/editar/borrar), revisiones/historial de versiones (listar/restaurar/borrar), papelera (restaurar + vaciar), accesos directos (shortcuts), Drive Labels, feed de cambios/notificaciones push (`changes`/`watch`), cuota/ajustes (`about.get`).

## 5. Tools de lote (rendimiento en bytes masivos)
`copy_tree(account, src_folder_id, dst_folder_id)`, `move_batch(account, ids[], ...)`, `delete_batch(account, ids[])`.

Reglas: operan **server-side por file_id**, recorren la API de Drive internamente con llamadas a Google **paralelizadas**; **nunca** devuelven ni aceptan bytes masivos (base64) a través del modelo; preferir `files.copy` (Google-interno) siempre que sea intra-cuenta.

## 6. Tool de intake desde Drive
`import_drive_folder(src_account, src_folder_id, dst_expediente)`:

1. Lista el árbol recursivamente.
2. Transfiere Drive→Drive **cross-cuenta** (EV→TL) server-side: descarga con token EV + sube con token TL; los bytes pasan por el servidor, **no por el modelo**. Docs nativos se exportan (formato a fijar) y se suben.
3. Cadena forense: SHA-256 de binarios leído del metadato `sha256Checksum` de Drive (poblado solo para binarios, **no** Docs nativos ni shortcuts); para Docs nativos, hash calculado sobre el artefacto exportado que realmente se guarda.
4. Escribe evento `upload_*` en `_intake_log.jsonl`.

Reparto: este tool cubre la fuente "01_Drive EV" del intake. **XL** sigue con zips, exports de WhatsApp, ingesta de bytes locales del PC y hash de lo que no traiga checksum.

## 7. Tools de Calendar (fase 1, con `account`)
`list_calendars`, `list_events`, `get_event`, `get_availability`, `create_event`, `update_event`, `delete_event`, `respond_to_event`, más **ACL/compartir calendario** (`acl.*`) y **colores/ajustes** (`colors`/`settings`).

Fuera: crear/borrar calendarios, `events.move`, quick-add, instancias de recurrentes.

## 8. Seguridad y segregación
- **Único control aprobado — guardarraíl de compartición externa** en `create_permission`/`update_permission`: bloquear o exigir confirmación reforzada para `type=anyone` (enlace público) y dominios externos distintos de `tyukhay.legal`/`engelvoelkers.com`; **nunca** conceder `role=owner` de forma automática. (Rechazados: log forense append-only y allow-list de raíces.)
- **Borrado**: expuesto por el MCP; la contención la aplica Nikolai en la **consola de Cowork** (aprobación por acción, sin "permitir siempre" para borrado), no en lógica del servidor.
- **Aislamiento por `account`**: ninguna tool cruza datos entre cuentas de forma implícita; el intake cross-cuenta es la única transferencia EV→TL y siempre con `account` explícito en origen y destino.
- **Credenciales** en variable de entorno / almacén seguro; nunca en claro ni en chat.

## 9. Scopes OAuth
Drive completo (`drive`) para crear/editar/mover/borrar/permisos; Calendar (`calendar.events` + ACL/settings). Documentar en el README los scopes y justificar `drive` por los requisitos de escritura.

## 10. Rendimiento (expectativa)
- **No se espera mejora de latencia por llamada** frente al nativo: ambos van por API Drive + round-trip MCP (~15 s/llamada). La ganancia es de flujo (sin reautenticar, multicuenta, batch, hash por metadato).
- Enrutado: reorg **intra-Drive** → tools de lote del MCP (con `files.copy` interno puede superar a XL); **ingesta de bytes locales, zips y hash forense** → EXPEDIENTES XL. Copia entre cuentas distintas va por el servidor del MCP (aceptable, más lenta que intra-cuenta).

## 11. Entregable
MCP instalado y visible en Cowork; `list_accounts` devuelve las dos cuentas; Drive (lectura, búsqueda, creación, edición, mover, borrar con aprobación, permisos con guardarraíl, lote e intake) y Calendar operativos en ambas cuentas sin reconectar. Tras verificarlo contra un caso real, **retirar el conector nativo EXPEDIENTES**. Registrar el hito en ESTADO.md/commits.log.

---

### Referencias técnicas
- Drive API v3 expone `sha256Checksum` (output-only, solo binarios): https://developers.google.com/workspace/drive/api/reference/rest/v3/files
- Conector Google Workspace nativo = mono-cuenta: https://support.claude.com/en/articles/10166901-use-google-workspace-connectors
