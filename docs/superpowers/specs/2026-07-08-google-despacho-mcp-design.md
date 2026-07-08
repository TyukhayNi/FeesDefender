# Diseño — MCP `google-despacho` (Drive + Calendar, multicuenta)

_Brainstorming Claude Code · FeesDefender · 2026-07-08_
_Fuente del encargo: `ENCARGO_MCP_Google_despacho.md` (fuera del repo)._

## 0. Estado de las decisiones (cerradas en brainstorming)

| Decisión | Resuelto |
|---|---|
| Topología | **Un solo MCP** `google-despacho` (Drive + Calendar), por fases (Approach 1) |
| Entrega a Cowork | **stdio local + `.dxt` + puente de Claude Desktop** (P1 verificado en vivo: sin túnel, sin hosting remoto, sin OAuth propio del MCP) |
| `expedientes` nativo del repo | **Convive, NO se jubila** (gana en alcance nube, pierde en latencia disco) |
| OAuth | Reutiliza proyecto Cloud de Gmail; External+Testing → recautenticación 7 días (cadencia ya asumida) |
| Orden de fases | **O1**: F1 lectura → F2 escritura+permisos → F3 lote+intake → F4 Calendar |
| Ubicación | En el repo, `plugins/google_despacho_mcp/` |
| Export de Docs nativos | Default PDF (hasheable); flag `keep_editable` → Office |

## 1. Propósito y alcance

Un conector Google **multicuenta** que sostiene las dos cuentas a la vez,
seleccionadas por parámetro `account`, calcado del patrón del conector
Gmail-despacho. Elimina la reautenticación al cambiar de cuenta (el conector
nativo de Drive es mono-cuenta).

Cuentas y alcance subjetivo:
- `nikolai.tyukhay@engelvoelkers.com` → My Drive + compartido con esa cuenta + Calendar.
- `nikolai.tyukhay@tyukhay.legal` → My Drive completo + **todas** las unidades
  compartidas accesibles + Calendar.

Toda búsqueda/listado con soporte de unidades compartidas:
`corpora=allDrives`, `includeItemsFromAllDrives=true`, `supportsAllDrives=true`.

**Consolidación de conectores:**
- **Drive nativo:** candidato a retirar *tras* verificar el MCP contra un caso real.
- **`expedientes` (filesystem MCP local sobre `G:`):** **se queda.** Este MCP le
  gana en alcance (Cowork nube) pero pierde en latencia (API Drive ~15 s/llamada
  vs disco). Enrutado: lectura local intensiva (sala de lectura en el PC) →
  `expedientes`; alcance nube / cross-cuenta → este MCP.
- **EXPEDIENTES XL:** fuera de este encargo; sigue operativo (ingesta de bytes
  locales, zips, WhatsApp, hash de lo que no traiga checksum).
- **Gmail-despacho:** fuera (otro radio de fallo).

## 2. Topología y estructura

Servidor **stdio local FastMCP**, calcado del molde `Gmail MCP Desktop`
(`gmail_auth.py` + `server.py` + `gmail_cli.py`). Empaquetado como `.dxt` y/o
entrada en `claude_desktop_config.json`. Llega a Cowork/claude.ai por el
**puente de Claude Desktop** (verificado: los conectores locales se exponen a las
sesiones nube; requisito operativo = PC encendido + app de escritorio + puente
activo, lo mismo que ya vive el conector Gmail).

Separación lógica-pura / wrapper (patrón `plugins/expedientes_xl/`):

```
plugins/google_despacho_mcp/
    __init__.py
    google_auth.py      # OAuth multicuenta; tokens ~/.google-despacho/tokens/<email>.json
    drive_ops.py        # operaciones puras de Drive; `service` inyectable
    calendar_ops.py     # operaciones puras de Calendar; `service` inyectable
    server.py           # registro de tools FastMCP; todas con `account`
    google_cli.py       # alta/lista/baja de cuentas por navegador (OAuth interactivo)
    run_server.bat       # wrapper de arranque (patrón expedientes_mcp)
    README.md
    requirements.txt
```

Credenciales y tokens **fuera del repo**, en `~/.google-despacho/` (gitignored),
override por `GOOGLE_DESPACHO_HOME`. Tests en `tests/`.

**Principio de aislamiento:** `drive_ops`/`calendar_ops` no conocen `mcp` ni el
transporte; reciben un `service` de la API de Google ya construido. `server.py`
es un wrapper fino que resuelve `account` → `service` y delega. `google_auth`
es el único que toca OAuth/tokens.

## 3. Autenticación / OAuth

- **Reutiliza el proyecto de Google Cloud de Gmail-despacho**: habilitar Drive API
  + Calendar API y añadir los scopes a la pantalla de consentimiento. Reutiliza el
  mismo `credentials.json` (secreto de cliente OAuth de tipo App de escritorio).
- **Scopes** (fijados en `google_auth.py`, no parametrizados, para que ampliarlos
  exija edición consciente):
  - `https://www.googleapis.com/auth/drive` (completo — justificado por escritura/mover/borrar/permisos)
  - `https://www.googleapis.com/auth/calendar.events`
  - scopes de ACL/settings de Calendar según se necesiten en F4
- **Modo External + Testing** → el refresh token de scopes sensibles/restricted
  **caduca a los 7 días**. Se acepta la recautenticación periódica (`google_cli.py add`),
  misma cadencia que Gmail. Pasar a Producción exigiría auditoría CASA (scope `drive`
  es restricted) — no se hace.
- Ambas cuentas como **test users** (ya lo son para Gmail; el admin de
  engelvoelkers.com no bloquea apps sin verificar — verificado empíricamente).
- Token por cuenta en `~/.google-despacho/tokens/<email>.json`; refresco perezoso
  al construir el `service`, igual que `gmail_auth.load_credentials`.

## 4. Tools por fase (orden O1)

Todas aceptan `account` explícito. Ninguna cruza datos entre cuentas de forma
implícita.

### F1 — Lectura cross-cuenta (valida toda la fontanería)
`list_accounts`, `list_shared_drives`, `search_files` (con `drive_id`/`corpora`/
`supportsAllDrives`), `list_recent_files`, `get_file_metadata`,
`get_file_permissions`, `read_file_content`, `download_file_content`, `about.get`.

Meta de F1: dar a Cowork el alcance de lectura de ambas cuentas y validar auth de
las 2 cuentas + unidades compartidas + puente antes de invertir en escritura.

### F2 — Escritura CRUD + permisos
`create_file`, `create_folder`, `copy_file`, `update_file_content` (edición
in-place), `update_file_metadata` (renombrar), `move_file`, `delete_file`
(papelera por defecto; `permanent=true` solo con flag), `create_permission`,
`update_permission`, `delete_permission` (con guardarraíl §5).

### F3 — Lote + intake
`copy_tree(account, src_folder_id, dst_folder_id)`,
`move_batch(account, ids[], ...)`, `delete_batch(account, ids[])`.
- Operan **server-side por `file_id`**, llamadas a Google paralelizadas, **nunca**
  devuelven ni aceptan bytes masivos (base64) por el modelo. Intra-cuenta:
  preferir `files.copy` (Google-interno).

`import_drive_folder(src_account, src_folder_id, dst_expediente)`:
1. Lista el árbol recursivamente.
2. Transfiere Drive→Drive **cross-cuenta** (EV→TL) server-side: descarga con token
   origen + sube con token destino; los bytes pasan por el servidor, **no por el
   modelo**. Docs nativos se exportan (default PDF; ver §6).
3. Cadena forense: SHA-256 de binarios leído del metadato `sha256Checksum`
   (poblado solo para binarios, no Docs nativos ni shortcuts); para Docs nativos,
   hash sobre el artefacto exportado que realmente se guarda.
4. Escribe evento `upload_*` en `_intake_log.jsonl`.

Reparto: este tool cubre la fuente «01_Drive EV» del intake. **XL** sigue con
zips, exports de WhatsApp, bytes locales del PC y hash de lo que no traiga checksum.

### F4 — Calendar (agendar citas)
`list_calendars`, `list_events`, `get_event`, `get_availability`, `create_event`,
`update_event`, `delete_event`, `respond_to_event`, `acl.*` (compartir calendario),
`colors`/`settings`.
Fuera: crear/borrar calendarios, `events.move`, quick-add, instancias de recurrentes.

### Diferido (YAGNI — solo si un caso lo pincha)
Comentarios/respuestas, revisiones/historial de versiones, papelera (restaurar +
vaciar), accesos directos (shortcuts), Drive Labels, feed de cambios/notificaciones
push (`changes`/`watch`). Regla de promoción backlog→cola del proyecto: solo por
disparador concreto.

## 5. Seguridad y segregación

- **Guardarraíl de compartición externa** (único control aprobado) en
  `create_permission`/`update_permission`: bloquear o exigir confirmación reforzada
  para `type=anyone` (enlace público) y dominios externos distintos de
  `tyukhay.legal`/`engelvoelkers.com`; **nunca** conceder `role=owner`
  automáticamente. (Rechazados: log forense append-only, allow-list de raíces.)
- **Borrado**: expuesto por el MCP; la contención la aplica Nikolai en la consola
  de Cowork (aprobación por acción, sin «permitir siempre» para borrado), no en
  lógica del servidor.
- **Aislamiento por `account`**: ninguna tool cruza datos entre cuentas de forma
  implícita; el intake cross-cuenta es la única transferencia EV→TL, siempre con
  `account` explícito en origen y destino.
- **Bytes masivos nunca por el modelo**: lote/intake operan server-side por
  `file_id`; el base64 no se devuelve para volúmenes.
- **Credenciales** en `~/.google-despacho/` / variable de entorno; nunca en el
  árbol del repo ni en el chat.

## 6. Formato de export de Docs nativos

`import_drive_folder`, Docs nativos:
- **Default = PDF**: fidelidad fija, artefacto hasheable forense; SHA-256 sobre el
  PDF que se guarda.
- **Flag `keep_editable=true`** → exporta a Office (docx/xlsx/pptx) y sube eso
  (también hasheable).
- **No** re-convertir a Google nativo en destino (hash inestable).
- Binarios: SHA-256 del metadato `sha256Checksum` de Drive.

## 7. Rendimiento (expectativa)

- **Sin mejora de latencia por llamada** frente al nativo (~15 s/llamada, API Drive
  + round-trip MCP). La ganancia es de flujo: sin reautenticar, multicuenta, batch,
  hash por metadato.
- Enrutado: reorg intra-Drive → tools de lote (con `files.copy` interno puede
  superar a XL); ingesta de bytes locales, zips y hash forense → EXPEDIENTES XL;
  copia entre cuentas distintas → servidor del MCP (más lenta que intra-cuenta,
  aceptable).

## 8. Tests

- `drive_ops`/`calendar_ops`: `service` **fake inyectado** (patrón de inyección de
  `plugins/email_export_mcp/server.py::build_server`); sin API viva en unitarios.
- Guardarraíl de dominios (§5): unit-tested (allow/deny por `type` y dominio).
- Saneado de rutas de descarga local (patrón `_resolve_dest` de Gmail).
- Check de integración manual contra una carpeta desechable de Drive antes de dar
  una fase por viva.
- Regla del proyecto: todo cambio en código → tests en `tests/`.

## 9. Entregable / hecho cuando

- `.dxt` construido (manifest calcado del de Gmail) e instalado en Claude Desktop.
- Visible en Cowork por puente; ejecutable también desde Claude Code (mcp-config).
- `list_accounts` devuelve las dos cuentas.
- Drive (lectura, búsqueda, creación, edición, mover, borrar con aprobación,
  permisos con guardarraíl, lote e intake) y Calendar operativos en ambas cuentas
  sin reconectar.
- Verificado contra un caso real → luego evaluar retirar el **Drive nativo**
  (no `expedientes`).
- Hito registrado en `STATUS.md` / `PLAN.md` + commit.

## 10. Referencias técnicas

- Drive API v3 `sha256Checksum` (output-only, solo binarios):
  https://developers.google.com/workspace/drive/api/reference/rest/v3/files
- Conector Google Workspace nativo = mono-cuenta:
  https://support.claude.com/en/articles/10166901-use-google-workspace-connectors
- Molde local: `~/Dev/Gmail MCP Desktop/` (`gmail_auth.py`, `server.py`, `gmail_cli.py`, `dxt-build/manifest.json`).
- Patrón lógica-pura/wrapper y saneado: `plugins/expedientes_xl/`.
- Patrón de inyección de dependencias para tests: `plugins/email_export_mcp/server.py`.
