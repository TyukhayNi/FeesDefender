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

~~Encadenar `writing-plans` para desglosar la F2 en plan de implementación.~~ HECHO:
F2 MERGEADA (PR #23 squash `52a5845`, cierre docs PR #24 `3a00442`). Siguiente: **F3** — ver §14.

## 14. F3 — `import_drive_folder` (intake forense EV→TL de una orden) (brainstorming 2026-07-10)

Delta de diseño que **supera y detalla** el esbozo de F3 de §4 (parte `import_drive_folder`)
y §6/§7/§11 R1. Cerrado en brainstorming con Nikolai (Claude Code) sobre un mapeo previo del
ecosistema (workflow de 7 lectores + síntesis). Decisiones tomadas con recomendación explícita
y aprobadas.

**Desambiguación de nombre:** este es el **F3 de `google-despacho`** (lote + intake Drive EV→TL).
NO confundir con el **F3 de `abrir-caso`** (fuentes no-Drive manual/whatsapp/email + `init_caso`,
ya mergeado, PR #22 `e68f59e`). Son trabajos distintos.

### 14.1 Alcance (decisión clave)

**F3 entrega SOLO `import_drive_folder`** (+ resolución `W-code` + recorrido recursivo). Las tools
de **lote** (`copy_tree`/`move_batch`/`delete_batch`) de §4 quedan **DIFERIDAS** (YAGNI: reorg
intra-Drive sin demanda real todavía; se promueven cuando un caso lo pida). Calendar → **F4**.

`import_drive_folder` es el orquestador de una sola orden que compone las **primitivas atómicas de
F2** (ya mergeadas en `drive_ops.py`): `search_files(drive_id=)`, `list_folder`, `get_file_metadata`,
`download_file_content`, `ensure_folder_path`, `upload_file`, `append_text`. No inventa acceso nuevo
a Drive; orquesta.

**Relación con `pull_drive_ev` (no duplica):** es el **hermano nube/sin-PC** del camino local
`intake_drive.pull_drive_ev` (rclone `gdrive_ev`→`00_Input/01_Drive EV/` sobre el mirror `G:`). Misma
fuente de intake («01_Drive EV»), **transporte distinto**: rclone-local (con PC + `G:` montado) vs
**Drive API cross-cuenta server-side** (descarga con token EV → sube con token TL, sin PC, sin bytes
por el modelo). Lógica de negocio compartida como **contrato** (mismo evento, mismo path relativo,
mismo shape de `details`), no reimplementada → las dos vías conviven sin doble-contar gracias al
dedup por SHA.

### 14.2 Firma y comportamiento

`import_drive_folder(src_account, src_folder_id, dst_expediente, keep_editable=False) -> dict`

- `src_account` explícito (normalmente EV; permite también TL→TL). Destino **implícito = TL**
  (`GOOGLE_DESPACHO_TL_DRIVE_ID`, ver §14.6).
- `dst_expediente` = **W-code** → se resuelve a `folder_id` de la carpeta canónica del caso en TL
  (§14.3).
- Recorre `src_folder_id` recursivamente, transfiere cada fichero EV→TL bajo `00_Input/01_Drive EV/`
  del caso (espejando la estructura de subcarpetas), escribe el evento forense y devuelve un resumen
  `{transferidos, omitidos_por_dedup, fallidos[], destino_folder_id}`.

**Función pura** en `drive_ops.py` con **dos `service` inyectables** (`src_service`, `dst_service`)
para testear sin API viva (patrón `build_server`/`email_export_mcp`); wrapper `@mcp.tool()` fino en
`server.py` que resuelve `service_factory(src_account)` y `service_factory(TL)`.

### 14.3 Resolución de `W-code` → `folder_id` (nueva pieza)

No existe equivalente en código reutilizable (el `case_locator` local depende del mirror `G:`,
indisponible en Cowork; el CRM resuelve a un ID de expediente, no a una carpeta). Se construye:

- `resolve_expediente(dst_service, w_code) -> folder_id`: `search_files` sobre `TEAM_DRIVE_TL` con
  `q` = carpetas cuyo nombre contiene el `W-code`, casando el **mismo patrón `(W-XXXXX)` de
  `core.abrir_caso`** (replicado con test de equivalencia, §14.6), no una regex nueva.
- **0 coincidencias → error ruidoso** (no crea nada). **>1 coincidencias → error** listando los
  candidatos (nunca adivina).
- Optimización diferida (YAGNI, sin disparador): cachear el `folder_id` resuelto en
  `_caso.md.meta`.

### 14.4 Recorrido y transferencia cross-cuenta

- **Walker recursivo propio** (BFS): `list_folder` es NO recursivo. Mantiene `visited` de `file_id`
  (guarda de ciclos), tope de profundidad, y **salta shortcuts** (`application/vnd.google-apps.shortcut`,
  equivalente del `--drive-skip-shortcuts` de rclone) para no duplicar bytes ni buclear.
- **Transferencia por fichero**: `download_file_content` (con service EV) a un **scratch temporal del
  servidor** (`tempfile.mkdtemp`, limpieza en `finally`; la ruta NO viene del modelo → no aplica
  symlink-escape) → `upload_file` (con service TL) a la subcarpeta espejo creada con
  `ensure_folder_path`. `files.copy` NO cruza cuentas → siempre vía temp.
- **Docs nativos** (§6): default **PDF**, `keep_editable`→Office; el `export_mime` + extensión se
  derivan de `get_file_metadata().mimeType` + `keep_editable` con las tablas `_EXPORT_PDF`/
  `_EXPORT_OFFICE`/`_EXPORT_EXT`, **sin confiar** en el `mime_type` que devuelve
  `download_file_content` (bug §14.5). Se nombra el temporal con la extensión correcta y se pasan
  `mime_type`+`name` explícitos a `upload_file`.
- **Integridad forense**: binarios → asertar `sha256Checksum` (metadato de origen) vs `sha256`
  recalculado tras descarga; Docs nativos (sin `sha256Checksum`) → SHA del artefacto exportado.

### 14.5 Fix del bug de contrato en `download_file_content`

`drive_ops.py` devuelve el **mime nativo** tras exportar un Doc (en vez del `export_mime`) y no añade
la extensión al `dest_path`. Se corrige el `return` + un test pequeño (el fichero ya está mergeado en
F2, pero el bug es latente para cualquier consumidor y F3 es el primero que lo pincha).

### 14.6 Aislamiento (híbrido) — anti-drift

El plugin sigue **standalone** (sin `import core`; corre bajo el puente de Claude Desktop). Las **tres
convenciones compartidas** con `core` se anclan por **tests de equivalencia/paridad**, no por copia a fe:

- **ID del Shared Drive TL**: `GOOGLE_DESPACHO_TL_DRIVE_ID` (ENV, default = `0AAhcjDaZBWe6Uk9PVA`) con
  test que asegura `== core.config.TEAM_DRIVE_TL`.
- **Regex de `W-code`**: replicada en el plugin con test de equivalencia contra
  `core.abrir_caso._W_CODE_EN_NOMBRE`.
- **Schema del evento forense**: constructor de evento propio del plugin (sin `import core`) que emite
  EXACTO el envelope `{ts, actor, event, case_id, details}` con `event ∈ INTAKE_EVENTS` y
  `details {count, files:[{path, sha256}]}`, blindado por un **test de paridad** calcado de
  `tests/test_intake_traza.py` (mismo patrón ya probado para `intake-expediente/scripts/traza.py`).

### 14.7 Log forense — dónde y cómo (decisión)

**El MCP escribe él mismo el `_intake_log.jsonl` en la carpeta del caso en Drive** (R1: la traza viaja
con el expediente; F3 no depende del PC), vía `append_text`. Reutiliza el evento **`pull_drive_ev`**
(misma fuente/shape/dedup) añadiendo en `details`: `transport='drive_api_cross_account'` y
`hash_source` (`sha256Checksum` para binarios, `export` para nativos) — honestidad forense sin romper
el dedup por SHA. `path` relativo a `00_Input/` (`'01_Drive EV/<rel posix>'`), nunca absoluto.

Mitigaciones del `append_text` (read-modify-write no atómico, sin lock, tope 5 MB): **guard §6**
(no escribe a un caso `prestado`/`conflicto`) + **relectura del `headRevisionId`** antes de escribir.
Los contras son de baja probabilidad real (log de caso normal <1 MB; import discreto).
**Disparador documentado para promover a ficheros rotados por-evento:** el día que un caso real roce el
tope 5 MB o aparezca una carrera. YAGNI hasta entonces.

### 14.8 Guard §6 (lock de checkout)

Antes de escribir en la carpeta del caso en TL, leer `estado_repositorio` del `_caso.md`
(frontmatter de dos niveles, lock en `fm['meta']`) vía Drive API y **rechazar** el import si el caso
está `prestado`/`conflicto` (equivalente nube de `case_manager.dir_intake`). Reutiliza los lectores
puros del lock de `core.repository_checkout` (parseo sobre el meta leído por API), no reimplementa el
parseo del frontmatter.

### 14.9 Fallo parcial y rendimiento

- **Sin rollback**: las copias de Drive no son destructivas. Ante fallo a medias se escribe lo
  logrado, se devuelve **manifiesto de fallidos** y el re-run **deduplica por SHA** (reanudable).
- **Concurrencia acotada + backoff** en 429/5xx (grado de paralelismo modesto, no fijado por §4).

### 14.10 Frontera con EXPEDIENTES-XL (sin solape)

Se honra el reparto del spec §7: `import_drive_folder` es Drive→Drive por temp del servidor; **XL**
se queda con bytes locales/zips/WhatsApp/hash-sin-checksum. Como TL está espejado en `G:`
(Drive-for-Desktop), al subir a TL por API el cliente ya sincroniza a `G:` — un aterrizaje local
explícito sería redundante. La **fuente del hash difiere por canal** (metadato `sha256Checksum` en el
MCP vs recálculo `hashlib` en XL); se documenta para que no se lea como inconsistencia.

### 14.11 Tests

- Todo función pura con `service` fake inyectado (dos: EV origen + TL destino); sin API viva.
- `resolve_expediente`: 0 / 1 / >1 coincidencias (error ruidoso en 0 y >1).
- Walker: árbol fake con subcarpetas, shortcut (se salta), ciclo (visited-set lo corta), profundidad.
- Transferencia: binario (aserción sha256), Doc nativo (export_mime + extensión correctos, PDF y
  Office), dedup por SHA (omite lo ya presente en el log).
- Guard §6: rechaza si `estado_repositorio ∈ {prestado, conflicto}`.
- Paridad/equivalencia (§14.6): schema del evento, regex W-code, `GOOGLE_DESPACHO_TL_DRIVE_ID`.
- Fix del bug de `download_file_content`.
- Manifiesto de fallidos ante fallo parcial (fake que lanza en un fichero).
- Check de integración manual (§13.6) contra una carpeta desechable de Drive antes de dar F3 por viva.

### 14.12 Fuera de F3

Lote (`copy_tree`/`move_batch`/`delete_batch`) → diferido (YAGNI). Calendar → **F4**. Rotación del log
por-evento → solo si un caso pincha el tope 5 MB o una carrera.

### 14.13 Próximo paso F3

Encadenar `writing-plans` para desglosar la F3 en plan de implementación.
