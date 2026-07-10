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
  exija edición consciente). **CORREGIDO por R2 (§11) y por la decisión de scope de F1
  (2026-07-09):**
  - **F1 (implementada):** `https://www.googleapis.com/auth/drive.readonly` (mínimo
    privilegio; doble restricción con la ausencia de tools de escritura).
  - **F2 ampliará** a `https://www.googleapis.com/auth/drive` completo (edición
    consciente de `google_auth.SCOPES` + una reautorización).
  - `https://www.googleapis.com/auth/calendar.events` y ACL/settings: en F4.
- **Modo External + `En producción`** (R2, §11): el caduca-7-días **NO aplica** (era
  tope de modo `Testing`). Ambas cuentas funcionan sin reautenticación semanal —
  verificado en vivo el 2026-07-09 (la cuenta EV `engelvoelkers.com` autorizó con el
  aviso normal de app-sin-verificar, sin bloqueo de organización). **Este párrafo
  supera la redacción original «External+Testing / caduca 7 días / no Producción».**
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

## 11. Ajustes de revisión (2026-07-08)

Revisión del spec tras el primer borrador. Estos ajustes prevalecen sobre las
secciones §2–§6 donde discrepen.

**R1 — `import_drive_folder`: destino y log forense (APROBADO).**
- `dst_expediente` = **W-code**, resuelto contra la **carpeta canónica del caso en
  la unidad compartida «EXPEDIENTES - TYUKHAY LEGAL»** (búsqueda por nombre/patrón
  del W-code → `folder_id` de destino en TL).
- `_intake_log.jsonl` se escribe **en esa misma carpeta de Drive** (leer-modificar-
  subir vía `update_file_content`/`create_file`), para que la traza forense viaje
  con el expediente. (No en local.)

**R3 — `download_file_content` no devuelve bytes por el modelo (APROBADO).**
- `download_file_content` **escribe a una ruta local** acotada por un DL-root
  (patrón `GMAIL_DL_ROOT`/`_resolve_dest` del molde Gmail); nunca base64 al modelo.
- Solo `read_file_content` devuelve **texto** (Docs exportados a texto / ficheros
  planos). Con esto se sostiene el principio §5 "bytes masivos nunca por el modelo".

**R4 — diferidos (APROBADO).** Scopes exactos de ACL/settings de Calendar: pinchar
en F4, no ahora. Cachear el objeto `service` por cuenta dentro del proceso (evita
reconstruir credenciales en cada llamada).

**R2 — credenciales por-cuenta / caduca-7-días (CERRADA 2026-07-09).**
- **Decisión: un solo cliente OAuth, `External` + `En producción`, SIN split. NO
  marcar el proyecto como `Internal`.** Se reutiliza el proyecto Cloud de Gmail
  (`Gmail MCP Despacho`), que ya está `En producción`. Un `credentials.json` único
  para ambas cuentas (TL + EV).
- **Fundamento (dato nuevo de la comprobación):** al mirar la consola se vio que la
  app **ya está `En producción`**, no en `Testing`. El caduca-7-días del refresh
  token es un tope **exclusivo del modo `Testing`**; en `Producción` no aplica — ni
  para TL ni para la cuenta EV (`engelvoelkers.com`, org ajena). Luego desaparece la
  única motivación del split.
- **Por qué NO Internal (aunque el botón "Marcar como interno" SÍ estaba disponible,
  confirmando que `tyukhay.legal` es Workspace):** una app `Internal` solo autoriza
  usuarios de su propia organización. Marcarla `Internal` **expulsaría la cuenta EV**
  (org distinta), que es justo la que se necesita. El split habría sido
  contraproducente.
- **Diseño de código:** el mapeo por-cuenta (`google_auth.py`: cuenta → fichero de
  credenciales, con *fallback* a `credentials.json` único) se **conserva** como
  capacidad, pero en la práctica ambas cuentas comparten el `credentials.json` único.
  Internal-vs-External era config de consola, no código → el cierre no altera el diseño.
- **Residuo para F1 (no de OAuth):** la consola avisa *"Tu app requiere una
  verificación"* y hay tope de **5/100 usuarios** para scopes sensibles/restringidos
  sin aprobar. Con 2 usuarios sobra; con la app sin verificar, Drive funciona
  mostrando el aviso *"app no verificada"* al autorizar. Al añadir `drive.readonly`
  (restricted) se decide en F1 si se asume ese aviso o se acota scope. Nota colateral:
  estar en `Producción` probablemente también resuelve el viejo `invalid_grant` de
  7 días del propio Gmail MCP.

## 12. Próximo paso

1. ~~Nikolai: comprobación R2 (¿Internal disponible en `tyukhay.legal`?).~~ HECHA
   2026-07-09: Internal disponible pero app ya `En producción` → R2 cerrada sin split.
2. ~~Cerrar R2 en este spec.~~ HECHA.
3. ~~Encadenar la skill `writing-plans` para desglosar **F1** (lectura cross-cuenta)
   en plan de implementación.~~ HECHA: F1 MERGEADA (PR #12, `4056d6b`), validada en
   vivo y cableada. Siguiente: **F2** — ver §13.

## 13. F2 — Escritura CRUD + permisos (brainstorming 2026-07-10)

Delta de diseño que **supera y detalla** el esbozo de F2 de §4 y §5. Cerrado en
brainstorming con Nikolai (Claude Code). Decisiones tomadas con recomendación
explícita y aprobadas.

### 13.1 Frontera de fase (decisión clave)

**F2 entrega los *ladrillos*; el intake de una sola orden es F3.** Con las tools de
F2 se puede hacer un intake EV→TL **paso a paso** (`search_files` → `list_folder` →
`download_file_content` a local con token EV → `upload_file` a carpeta TL con token
TL → `append_text` al log). Lo que NO entra en F2 es el orquestador de una sola orden
`import_drive_folder` (resolver `W-code`→carpeta canónica en «EXPEDIENTES - TYUKHAY
LEGAL» + recorrido recursivo + transferencia cross-cuenta server-side + log forense
en Drive): eso es **F3**, con su propio spec/plan. Motivo: fases pequeñas y
verificables por PR.

### 13.2 Inventario de tools (F2)

Todas con `account` explícito; `drive_ops` puro (service inyectable) + wrapper fino en
`server.py`. Ninguna cruza cuentas de forma implícita.

**Escritura CRUD:**
| Tool | Nota |
|---|---|
| `create_file(name, parent_id, text=…)` | texto generado por el modelo (logs/notas/`.md`); tope pequeño (p. ej. 1 MB) |
| `upload_file(local_path, parent_id, name=…)` | bytes desde ruta local acotada por **UPLOAD-root** (`GOOGLE_DESPACHO_UPLOAD_ROOT`), simétrico al DL-root |
| `create_folder(name, parent_id)` | creación simple |
| `ensure_folder_path(path, parent_id)` | **idempotente**: crea solo los segmentos que falten y devuelve el `folder_id` final; evita carpetas duplicadas (Drive las permite) |
| `copy_file(file_id, dst_folder_id, new_name=None)` | `files.copy` interno, `supportsAllDrives` |
| `update_file_content(file_id, text= \| local_path=)` | edición in-place, mismo `file_id`; exactamente uno de los dos |
| `update_file_metadata(file_id, name=…)` | renombrar |
| `move_file(file_id, dst_folder_id)` | `addParents`/`removeParents` |
| `delete_file(file_id, permanent=False)` | papelera por defecto; `permanent=true` solo con flag |
| `restore_file(file_id)` | des-papelera (untrash), reverso de `delete_file` |
| `append_text(file_id, text)` | append read-modify-write server-side (p. ej. `_intake_log.jsonl`); espeja XL |
| `export_to_drive(file_id, format='pdf', dst_folder_id=None)` | exporta Doc nativo/Office a PDF (o Office) y **guarda de vuelta EN Drive**, server-side; sin bytes por el modelo. Default carpeta = la del origen |
| `create_shortcut(target_id, dst_folder_id)` | enlaza un doc en varias carpetas sin duplicar bytes (fuente única) |

**Permisos (guardarraíl §5):**
`create_permission`, `update_permission`, `delete_permission`.
- **Guardarraíl `allow_external`** (decisión): por defecto BLOQUEA `type=anyone`
  (enlace público) y dominios ajenos a `tyukhay.legal`/`engelvoelkers.com` con error
  claro. Solo procede si se pasa `allow_external=true` explícito (= "confirmación
  reforzada" del §5). Segunda barrera: aprobación por acción en la consola de Cowork.
- `role=owner` **nunca** automático.
- `sendNotificationEmail=false` por defecto (no spamear a terceros al compartir).

**Navegación / lectura (complementan la F1):**
| Tool | Nota |
|---|---|
| `list_folder(folder_id, account)` | hijos directos (name/type/id); Drive navegable como explorador sin escribir queries |
| `list_trash(account)` | ver la papelera (complementa `restore_file`) |
| `get_folder_path(folder_id)` | miga de pan / ruta completa de una carpeta |

### 13.3 Refinamientos dentro de tools

- `upload_file` y `update_file_content` devuelven **`sha256` + `webViewLink`** del
  artefacto guardado (cierra la cadena forense en la subida, igual que
  `download_file_content` ya devuelve hash; el link es clicable para pasar a cliente).

### 13.4 OAuth / scope

- Subir `google_auth.SCOPES` de `drive.readonly` a
  **`https://www.googleapis.com/auth/drive`** (completo). `drive.file` NO sirve:
  solo opera sobre ficheros creados por la app, y F2 toca expedientes existentes.
- `drive` subsume `drive.readonly` → las 9 tools de F1 siguen igual.
- Requiere **edición consciente** de `SCOPES` + **reautorizar las 2 cuentas** una vez
  (`google_cli.py add`). `drive` es scope *restricted*: con la app sin verificar y
  2 usuarios (tope 100), funciona mostrando el aviso "app no verificada" (ya asumido
  en R2 para `drive.readonly`).

### 13.5 Seguridad (F2)

- **UPLOAD-root** (`GOOGLE_DESPACHO_UPLOAD_ROOT`) confina los orígenes de
  `upload_file`, variable **independiente** del DL-root; mismo saneado `realpath`
  contra symlink-escape que `_resolve_dest`.
- **Bytes masivos nunca por el modelo**: `upload_file`/`export_to_drive` operan por
  ruta/`file_id`; `create_file`/`update_file_content(text=)` son solo para texto corto
  del modelo con tope.
- **Borrado**: papelera por defecto; `permanent` tras flag; contención por aprobación
  en Cowork (sin "permitir siempre" para borrado).

### 13.6 Tests (F2)

- `drive_ops`: `service` fake inyectado (patrón `build_server`); sin API viva.
- Guardarraíl de dominios (`allow_external`): unit-test allow/deny por `type` y dominio.
- `ensure_folder_path` idempotente: no duplica un segmento existente.
- Saneado de UPLOAD-root (symlink-escape) como el del DL-root.
- Check de integración manual contra una carpeta desechable de Drive antes de dar F2
  por viva.

### 13.7 Fuera de F2 (F3/F4 o YAGNI)

`import_drive_folder` + resolución `W-code` + lote (`copy_tree`/`move_batch`/
`delete_batch`) → **F3**. Calendar → **F4**. Vaciar papelera, revisiones/historial,
propiedades/etiquetas (`appProperties`/Labels) → diferidos (regla de promoción del
proyecto: solo por disparador concreto).

### 13.8 Próximo paso F2

Encadenar `writing-plans` para desglosar la F2 en plan de implementación.
