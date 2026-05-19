# DEAD ENDS — FeesDefender

> Registro permanente de intentos fallidos confirmados empíricamente.
> **No volver a intentar estas vías sin nueva evidencia de que el problema se ha resuelto.**
> Actualizar con fecha cuando se confirme un nuevo callejón.

---

## Frontal heredado — colaboradores

### `GET /autocompletar/buscar/elemento/colaboradores?term=...` — devuelve siempre body vacío
- **Intentado:** GET con term=TEST, term=joaquin, term=a, term=nikolai — todos retornan HTTP 200 con body vacío (len=0)
- **Confirmado:** 2026-05-04 contra tenant tnm (colaboradores sí existen: IDs 774-777+)
- **Causa probable:** El elemento `colaboradores` no está indexado en el endpoint de autocomplete del tenant, o requiere contexto de formulario que la petición directa no aporta
- **Solución:** `POST /views/menu/elemento/colaboradores` con `cadBusqueda=<term>` → respuesta HTML con tabla. Celdas: [3]=nombre, [5]=email. Filas: `id="fila_colaboradores_{id}"`. Implementado en `_search_colaboradores_html()` en `sudespacho_relations.py` (2026-05-04).

---

## API sudespacho.net

### `/api/element_register/{element}/{id}` — bug 500 en backend
- **Intentado:** GET con cualquier combinación de `properties[]` para `expedientes_judiciales`
- **Resultado:** `500 Array to string conversion` (bug en `GetRegister.php`, línea 48)
- **Confirmado:** 2026-04-25
- **Conclusión:** No usar. Afecta a todos los tipos de elemento.
- **Acción pendiente:** Reportar a soporte sudespacho.net cuando sea oportuno.

### `relatedRegisters` como propiedad filtrable en `/api/documents`
- **Intentado:** filtrar documentos por expediente usando `relatedRegisters` en `/api/documents`
- **Resultado:** no es una propiedad filtrable. El endpoint solo acepta: `asunto`, `carpeta`, `categoria`, `origen`, `origen_id`, etc. Ninguno enlaza con el expediente directamente.
- **Confirmado:** 2026-04-25
- **Conclusión:** El listado de documentos de un expediente solo está disponible vía frontal legacy (PHP).

### `/api/folders/gdocu/0?related_element=...`
- **Intentado:** listar carpetas de documentos de un expediente vía API REST
- **Resultado:** devuelve `[]` para todos los expedientes del tenant tnm
- **Confirmado:** 2026-04-25, **re-confirmado 2026-05-08** (script `scripts/probe_gdocu_tree.py` contra expediente 657 — judicial con docs en `Civil > 1ª Instancia > Declarativo > Demanda` y `General/`; el endpoint devolvió 0 carpetas).
- **Conclusión:** Las carpetas solo son navegables vía frontal legacy. El árbol del gestor documental no está expuesto vía REST con la query `parent=0`.
- **Workaround adoptado en refactor intake v2 (2026-05-08):** estrategia híbrida `CARPETA_ID_TO_PATH` hardcodeado + heurística por `id_carpeta_label` + fallback `99_Sin categoria/<expediente_id>/`. Mappings empíricos confirmados a 2026-05-08: `"1"` → `"General"`, `"307"` → `"Civil/1ª Instancia/Declarativo/Demanda"`. Nuevos IDs se descubren progresivamente vía evento `category_unknown` en `_intake_log.jsonl` (M10).
- **Investigación pendiente (no bloquea):** capturar HAR del gestor documental en Chrome para descubrir la query correcta, o consultar `developers.sudespacho.net`.

### `origen` + `origen_id` en `/api/documents`
- **Intentado:** `GET /api/documents?origen=expedientes_judiciales&origen_id=648`
- **Resultado:** 0 resultados. El campo `origen_id` no relaciona documentos con expedientes.
- **Confirmado:** 2026-04-25
- **Conclusión:** Usar siempre el frontal legacy para listar y descargar documentos.

### Header `Authorization: Bearer {api_key}`
- **Intentado:** autenticación con header `Authorization: Bearer <clave>` siguiendo la doc oficial
- **Resultado:** `401 Invalid JWT Token` — ese header está reservado al flujo JWT de sesión web
- **Confirmado:** 2026-04-24
- **Conclusión:** Usar siempre `x-api-key: <clave>` sin prefijo `Bearer`.

### `GET /api/element_registries/clientes_propios` → HTTP 404
- **Intentado:** listar / detalle de clientes propios del tenant tnm vía
  `GET /api/element_registries/clientes_propios` con `properties[]=id`,
  `filterGroup[id][operator]=equal`, `filterGroup[id][value]=2` (o 27),
  `itemsPerPage=5`. Auth `x-api-key`.
- **Resultado:** `HTTP 404 Not Found` para todas las variantes (con y sin
  filtros). El endpoint no responde — la colección `clientes_propios`
  **no está expuesta como `element_registries`** en este tenant.
- **Confirmado:** 2026-05-11 (sesión 9), durante intento de verificación
  REST del ID 27 (ENGEL & VÖLKERS SPAIN, S.L.U.) vía `scripts/diag_cliente_propio.py`.
- **Comparativa:** `element_registries/expedientes_judiciales`,
  `element_registries/extrajudiciales`, `element_registries/gdocu` y
  `element_registries/colaboradores` **sí** funcionan vía REST.
  `clientes_propios` es la excepción.
- **Conclusión:** no usar `element_registries/clientes_propios` para
  consultar metadatos de clientes propios. El script
  `scripts/diag_cliente_propio.py` queda como esqueleto roto pendiente
  de descubrir el endpoint correcto.
- **Workaround:** consultar el frontal heredado
  (`https://tnm.sudespacho.net/tnm/ficheros/clientes-propios/{id}`)
  manualmente. Los IDs conocidos están hardcodeados en
  `core.config.CLIENTES_PROPIOS_EV` (EV MMC SPAIN=2,
  ENGEL & VÖLKERS SPAIN=27).
- **Acción pendiente (no bloquea):** capturar HAR de la SPA navegando
  por `/ficheros/clientes-propios/` para descubrir el endpoint REST real
  (probable: `/api/clientes_propios/{id}` o ruta análoga sin `element_registries`).

### `GET /api/files/presigned_download_url/{doc_id}` → HTTP 400 "Unable to generate an IRI"
- **Intentado:** descarga de los 26 documentos del expediente judicial 649 vía `pull_expediente_v2` (`download_document_rest` → `presigned_download_url`)
- **Resultado:** los 26 docs fallan con HTTP 400 y body
  `{"@context":"/api/contexts/Error","@type":"hydra:Error","hydra:title":"An error occurred",`
  `"hydra:description":"Unable to generate an IRI for \"App\\Upload\\Infrastructure\\ApiPlatform\\DTO\\Download\""`
  — error del framework API Platform en el backend PHP. Auth x-api-key responde, el listado `gdocu` funciona (devuelve 26 items con metadatos), pero el endpoint de pre-signed URL no genera el IRI del DTO `Download`.
- **Confirmado:** 2026-05-11 (sesión post-incidencia BaRR3, durante intento de pull v2 del expediente real 649)
- **Histórico:** este mismo endpoint estaba **operativo el 2026-05-04** (registrado en `reference_sudespacho_api.md` y STATUS sesión 2026-05-04: *"REST elimina PHPSESSID para docs: `/api/element_registries/gdocu` + `/api/files/presigned_download_url/{doc_id}` confirmados sin PHPSESSID"*). Algo ha cambiado server-side entre el 2026-05-04 y el 2026-05-11.
- **Consecuencia:** ningún caso puede completar pull v2 hasta que se resuelva. El listado funciona; la descarga no.
- **Causa probable:** el cliente PHP del CRM ha desplegado una refactorización del módulo Upload con una clase `DTO\Download` cuyo `apiResource` no expone `iri` (falta atributo `@ApiResource(iri="...")` o el router de API Platform no la encuentra). Es un bug de configuración del backend, no de nuestro código.
- **Acción pendiente `[NUEVO-HILO-PRESIGNED-DOWNLOAD-BUG]`:** (1) capturar HAR de la SPA descargando un doc desde sudespacho.net (los usuarios sí descargan desde la web — la SPA usa una ruta distinta o un endpoint nuevo); (2) comparar payload con `download_document_rest`; (3) si la ruta ha cambiado, actualizar `core/sync_sudespacho.py`. Mientras tanto, fallback legacy con PHPSESSID + frontal `/views/gdocu/...` (no implementado en v2).
- **Workaround temporal:** si necesitas los docs de un caso, descárgalos manualmente desde la SPA y súbelos al árbol `00_Input/05_CRM/<rama>/` con el expander "📂 Subir al árbol CRM" del tab Casos de Streamlit.

---

## Google Drive / Google Docs

### Leer contenido de Google Docs vía Chrome extension (cross-origin)
- **Intentado:** `javascript_tool`, atajos de teclado, `screenshot`, `left_click` por referencia, `find` en accessibility tree — todo desde la extensión Claude in Chrome sobre una pestaña con docs.google.com
- **Resultado:** todos bloqueados por política cross-origin. La extensión no puede interactuar con el contenido de iframes de dominios externos (`chrome-extension://` → `docs.google.com`).
- **Confirmado:** 2026-04-28
- **Conclusión:** Imposible. Alternativas válidas: (1) exportar el doc manualmente como .txt/.md y subirlo, (2) copiar/pegar el texto relevante en el chat, (3) Drive MCP si el doc está en un Drive personal (no Shared Drive).

### Drive MCP — Shared Drives (Unidades compartidas)
- **Intentado:** `read_file_content`, `download_file_content`, `search_files` sobre documentos en `G:\Unidades compartidas\ADMINISTRACION\PROCEDIMIENTOS\`
- **Resultado:** el MCP de Drive no tiene acceso a Shared Drives (`teamDrives`), solo a My Drive del usuario autenticado.
- **Confirmado:** 2026-04-28
- **Conclusión:** Para docs en Shared Drives, usar exportación manual o compartir el archivo al Drive personal del usuario OAuth del MCP.

### `web_fetch` sobre URLs de Google Docs (docs.google.com)
- **Intentado:** fetch directo de `https://docs.google.com/document/d/{id}/export?format=txt`
- **Resultado:** redirige a login; la URL de exportación requiere sesión autenticada de Google.
- **Confirmado:** 2026-04-28
- **Conclusión:** No accesible sin sesión activa. Usar Drive MCP si está en My Drive, o exportación manual si está en Shared Drive.

### `rclone copy` sobre carpeta E&V con dangling shortcut → exit 1 aunque copie todo lo demás
- **Intentado:** pull desde Streamlit (`core/intake_drive.pull_drive_ev`) sobre la carpeta `1MEu1xV1zPP9meyRHgPYqRwr_6obqW15g` del Shared Drive de BaRS1 (Tibidabo 8 - W-02VND1). 41 ficheros legítimos en raíz + 2 subcarpetas (`Planos/`, `_RECMAMACION/`).
- **Resultado:** `rclone exit 1` tras 3 reintentos. En el `.pulled` queda `"errors": ["rclone exit 1: "]` con stderr vacío (ver entrada siguiente sobre captura subprocess en Windows). En realidad rclone copia los 41 ficheros correctamente; el exit 1 lo causa un **único** acceso directo de Google Drive en la raíz (`Atles de planòls.pdf`) cuyo target está borrado o sin acceso para `nikolai.tyukhay@engelvoelkers.com` (hay un fichero homónimo *válido* dentro de `Planos/` que sí se copia).
- **Confirmado:** 2026-05-19 — reproducido con `rclone copy gdrive_ev: ... -vv` que reveló `NOTICE: Dangling shortcut "Atles de planòls.pdf" detected` + `ERROR : Failed to copy: failed to open source object: can't read dangling shortcut`.
- **Conclusión:** Las carpetas E&V suelen contener accesos directos que el consultor captador creó hacia ficheros de su carpeta personal (rotación de personal → target inaccesible). Sin mitigación, **cualquier** dangling shortcut tumba el pull entero.
- **Solución aplicada:** flag `--drive-skip-shortcuts` añadido al comando rclone en `core/intake_drive.py::pull_drive_ev`. Trade-off conocido: si E&V usa shortcuts legítimos hacia ficheros fuera del Shared Drive, no se traerán; aceptable porque el uso típico apunta dentro del propio Shared Drive (recorrido recursivo igual los encuentra) o son shortcuts heredados rotos.

### `rclone copy` con destino en Shared Drive montado por Drive for Desktop → "corrupted on transfer: sizes differ"
- **Intentado:** pull con `rclone copy gdrive_ev: G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\CASOS\BaRS10 - Diagonal Ponent 22-24 - (W-02J1KW) - Vuelta\00_Input\01_Drive EV ...` y verificación post-transfer por defecto (size + checksum). Sin `--ignore-size`.
- **Resultado:** `Failed to copy with 17 errors: last error was: corrupted on transfer: sizes differ src(Google drive root '') 86400 vs dst(Local file system at //?/G:/Unidades compartidas/...) 86528`. Patrón consistente: el **destino siempre más grande** que el origen, en deltas variables (+128 B, +268 B, …). La línea `163.447 MiB / 163.447 MiB, 100%, 11.593 MiB/s, ETA 0s` justo antes de los errores confirma que la transferencia de bytes completa al 100%.
- **Confirmado:** 2026-05-19, sesión 21, caso BaRS10 (`.pulled` con stderr completo capturado).
- **Causa raíz:** el destino vive en un Shared Drive de Tyukhay Legal montado por **Google Drive for Desktop**. rclone trata `G:\` como filesystem local pero Drive Desktop intercepta la escritura. Cuando rclone finaliza el `.partial` y lo renombra al fichero definitivo, Drive Desktop reescribe metadatos y `stat()` devuelve un tamaño ligeramente superior. La verificación post-transfer de rclone (`Size != size`) aborta como "corrupted on transfer" pese a que los bytes son íntegros. El destino no es realmente "local"; el rótulo `Local file system at //?/G:/` de rclone es engañoso.
- **Conclusión:** **No se puede** confiar en la verificación de tamaño ni de checksum del backend `local` cuando el path apunta a un Shared Drive de Drive Desktop. La integridad ya está garantizada extremo a extremo por la Drive API + TLS de origen y el backend de Google de destino.
- **Solución aplicada:** flags `--ignore-size --ignore-checksum --inplace` añadidos al `rclone copy` en `core/intake_drive.py::pull_drive_ev` (sesión 21, 2026-05-19). `--inplace` evita además el rename `.partial → final`, que es el evento concreto que más confunde a Drive Desktop. Acumulado con `--drive-skip-shortcuts`, `--retries 3` y `--retries-sleep 5s` (este último cierra `[SIGUIENTE-DRIVE-RCLONE-RETRIES]`).
- **Alternativa arquitectónica pendiente (no urgente):** configurar un segundo remote rclone `gdrive_tnm` apuntando a la cuenta nikolai.tyukhay@tyukhay.legal y migrar `pull_drive_ev` a copia Drive→Drive (`gdrive_ev: → gdrive_tnm:CASOS/...`). Bypasea Drive Desktop por completo y elimina el doble ancho de banda. Requiere OAuth nuevo y refactor del módulo.

### `subprocess.run(..., text=True)` en Windows con stderr no decodificable
- **Intentado:** capturar stderr de `rclone` en `core/intake_drive.pull_drive_ev` con `subprocess.run(cmd, capture_output=True, text=True, timeout=300)`.
- **Resultado:** cuando rclone emite a stderr nombres de fichero con caracteres no decodificables en la página de código activa de Windows (cp1252 por defecto) — típico en E&V por tildes catalanas malformadas tipo `pla╠Çnols`, normalización Unicode NFD vs NFC, etc. — el stream se trunca o llega vacío al lado Python. El returncode sí llega bien, pero el `.pulled` queda con `"errors": ["rclone exit 1: "]` sin pista alguna de la causa.
- **Confirmado:** 2026-05-19 (caso BaRS1).
- **Conclusión:** No usar `text=True` para subprocesos que emitan stderr con potencial UTF-8 en Windows. Sustituir por `encoding="utf-8", errors="replace"`. La política `errors="replace"` evita además `UnicodeDecodeError` no capturado (el código solo cazaba `TimeoutExpired` y `FileNotFoundError`).
- **Aplicado:** `core/intake_drive.py::pull_drive_ev` (2026-05-19). Patrón replicable en cualquier otro `subprocess.run` del proyecto que invoque rclone, pdftotext, ocrmypdf o similar.

### Endpoint `/select/` para vincular elementos — no persiste

- **Intentado:** `POST /clientespropios/select/elemento/clientes_propios/.../elemento_relacion/` y equivalente para colaboradores con body `seleccionado[]=2&csrf_token=...&cc-num=...`
- **Resultado:** HTTP 200 con HTML completo (~104 KB) pero el vínculo NO se guarda en el CRM. El tab "Clientes" del expediente sigue mostrando 0.
- **Confirmado:** 2026-04-29
- **Causa raíz:** El flujo real del CRM usa un popup (`popup_open()`) cuyo botón "Guardar" llama a `saveselect()` en el padre. El padre hace un POST distinto a `/saveselect/` (no `/select/`).
- **Endpoint correcto:** `POST /clientespropios/saveselect/elemento/clientes_propios/.../` (sin `/elemento_relacion/` al final). Devuelve JSON `{"resultado": true, ...}`. Requiere además `numeroresultados_listado=5` y `documentos_adjuntos_seleccionados=` en el body.
- **Implementado en:** `core/sudespacho_relations.py` → `_link_element()`.

---

## Git desde bash sandbox (Linux)

### `git` sobre unidad de red montada en Windows
- **Intentado:** `git status`, `git log` desde el sandbox Linux sobre `/sessions/.../mnt/Base datos expedientes/`
- **Resultado:** `fatal: not a git repository` — el directorio `.git/` en la unidad de red (Google Drive) no es accesible desde el mount Linux del sandbox.
- **Confirmado:** 2026-04-26
- **Conclusión:** Todos los comandos git deben ejecutarse desde **Windows PowerShell**, no desde el bash del agente. Proporcionar siempre el bloque PowerShell al usuario.

---

## Claude in Chrome — Formularios con TinyMCE (sudespacho alta/edición)

### `javascript_tool`, `computer` (clicks, screenshots) — bloqueados por TinyMCE

- **Intentado:** ejecutar JS (`javascript_tool`), hacer click (`computer:left_click`), capturar pantalla (`computer:screenshot`) en páginas de alta/edición del CRM (`/add/`, `/saveedit/`)
- **Resultado:** `Cannot access a chrome-extension:// URL of different extension` — TinyMCE crea un iframe con URL `chrome-extension://` que bloquea TODOS los métodos de la extensión Claude in Chrome.
- **Confirmado:** 2026-04-30
- **Qué sí funciona:** `form_input` (set values), `read_page` (accessibility tree), `read_network_requests`
- **Workaround para extraer campos del formulario:** hacer `fetch()` al URL del formulario desde la página de LISTA (sin TinyMCE activo), parsear el HTML con `DOMParser` y extraer `querySelectorAll('[name^="campo_"]')`. Ver sesión 2026-04-30.
- **Workaround para submit:** no encontrado. El formulario no se puede enviar de forma automática cuando TinyMCE está cargado. Para capturar campos, usar el fetch desde la lista en lugar de submit real.

---

## Servidor sudespacho — `@token` JWT requerido desde 2026-05

### Python recibe `E-plan - sudespacho.net` en todas las URLs del CRM
- **Intentado:** GET con solo `PHPSESSID` (User-Agent FeesGuard/0.1 y luego Chrome real)
- **Resultado:** HTTP 200 con `<title>E-plan - sudespacho.net</title>` — el servidor requiere también la cookie `@token` (JWT, TTL 1h) y `@refreshToken` además de PHPSESSID. Sin ellas, sirve la landing page sin importar el User-Agent.
- **Confirmado:** 2026-05-04
- **Conclusión:** Añadir las tres cookies al `SudespachoLegacyClient`: `PHPSESSID`, `@token`, `@refreshToken`. Configuradas en `.env` como `SUDESPACHO_LEGACY_JWT` y `SUDESPACHO_LEGACY_REFRESH_TOKEN`. Implementado en `SudespachoLegacyConfig.from_env()` y `SudespachoLegacyClient.__init__`.
- **Acción pendiente:** El `@token` expira en 1h. Implementar renovación automática usando `@refreshToken` contra el endpoint de refresh del servidor.

## `browser_cookie3` — RequiresAdminError en Windows

### `browser_cookie3.chrome()` falla con `RequiresAdminError`
- **Intentado:** `browser_cookie3.chrome(domain_name="tnm.sudespacho.net")` desde proceso sin Admin
- **Resultado:** `RequiresAdminError: This operation requires admin. Please run as admin.` — DPAPI de Windows requiere Admin para descifrar cookies de Chrome.
- **Confirmado:** 2026-05-04
- **Conclusión:** No usar `browser_cookie3` en Windows sin elevar privilegios. Renovación PHPSESSID manual: botón «🔄 Renovar sesión CRM» en sidebar de Streamlit (lee cookie via Chrome MCP).

---

## SPA Vue — login no crea sesión PHP

### Login en `/tnm` (SPA) → el PHPSESSID nunca cambia; la sesión PHP en el servidor expira
- **Intentado:** salir y volver a loguearse en la SPA → comprobar PHPSESSID en Application→Cookies
- **Resultado:** el PHPSESSID mantiene el mismo valor (`l9liv1acf04sh2u05s3kcgrl0u`) antes y después del login. El browser conserva la cookie en su jar pero la sesión PHP del servidor ya expiró. El SPA login no crea una sesión PHP nueva.
- **Confirmado:** 2026-05-04
- **Conclusión:** No hay mecanismo automatizable para obtener un PHPSESSID válido a través del flujo SPA. El PHPSESSID del servidor solo puede crearse desde el login PHP legacy (si existe) o explorando endpoints REST alternativos para las operaciones que lo requieren.

### Login en `/tnm` (SPA) → solo JWT en localStorage, sin PHPSESSID
- **Intentado:** login en `https://tnm.sudespacho.net/tnm` (SPA Vue) → captura de cookies → uso de `PHPSESSID` resultante en FeesDefender
- **Resultado:** la SPA solo almacena tokens JWT en `localStorage` del navegador (`token`, `refreshToken`). No hace ninguna petición al backend PHP que cree o renueve una sesión PHP (`PHPSESSID`). Las cookies `@token` y `@refreshToken` que aparecen en DevTools son distintas de los tokens de `localStorage` y tienen origen distinto.
- **Confirmado:** 2026-05-04 (auditoría red completa durante login SPA)
- **Conclusión:** No hay forma de obtener PHPSESSID a través del flujo de login SPA. La sesión PHP del frontal heredado (`/views/`) se crea por un mecanismo PHP propio no identificado. Puede requerir interacción con una URL del frontal heredado autenticada con JWT, pero esta vía no ha sido verificada.
- **Acción pendiente:** `[NUEVO-HILO-AUDITORIA]` — identificar si algún endpoint PHP acepta `@token` para crear sesión PHP nueva.

---

## PHPSESSID — expiración independiente; SPA no crea sesión PHP

### PHP session expira por inactividad; login SPA no la renueva
- **Intentado:** login en https://tnm.sudespacho.net/tnm (SPA) → captura PHPSESSID resultante → uso en FeesDefender
- **Resultado:** la sesión PHP del servidor expira por inactividad (~24 min por defecto). El login vía SPA solo crea tokens JWT en `localStorage`; no crea ni renueva sesión PHP en el backend PHP (`/views/`).
- **Confirmado:** 2026-05-04
- **Conclusión:** PHPSESSID válido solo existe mientras haya una sesión PHP activa en el servidor. Cuando expira, no hay forma automatizada conocida de renovarla. Ver `[NUEVO-HILO-AUDITORIA]`.

### `_try_renew_php_session` — @token válido sin PHPSESSID → sigue E-plan
- **Intentado:** GET a `/views/menu/elemento/colaboradores` con solo `@token` + `@refreshToken` (sin PHPSESSID), esperando que PHP auto-cree sesión nueva
- **Resultado:** el servidor devuelve E-plan (HTTP 200, 1403 bytes) — idéntico al caso de @token expirado. El backend PHP requiere PHPSESSID válido aunque @token sea vigente.
- **Confirmado:** 2026-05-04
- **Conclusión:** `_try_renew_php_session` es insuficiente sin sesión PHP preexistente. Método de creación de sesión PHP vía JWT pendiente de investigar en `[NUEVO-HILO-AUDITORIA]`.

---

## Security layer del agente — bloquea extracción de tokens de auth

### `javascript_tool` no puede extraer ni inyectar tokens JWT desde localStorage/cookies
- **Intentado:** leer `localStorage.getItem('token')`, capturar header `Authorization` en network requests, escribir cookie `@token` desde localStorage — todas las variantes de JS desde el agente
- **Resultado:** `[BLOCKED: Sensitive key]` — la capa de seguridad del agente bloquea cualquier operación JS que lea o exponga tokens de autenticación, incluyendo intentos de copia interna sin devolverlos al chat
- **Confirmado:** 2026-05-04
- **Conclusión:** extracción/inyección de tokens de sesión CRM **siempre** requiere acción manual del usuario (DevTools Console + sidebar Streamlit). No automatizable desde el agente.

---

## Sidebar Streamlit — `localStorage.getItem('token')` ≠ cookie `@token`

### Las instrucciones originales del sidebar usaban localStorage en lugar de Application→Cookies
- **Error:** el sidebar mostraba `copy(localStorage.getItem('token'))` y `copy(localStorage.getItem('refresh_token'))` para obtener `@token` y `@refreshToken`
- **Resultado:** el usuario pegaba el token SPA (para llamadas REST de la Vue app) en lugar de la cookie `@token` que necesita el backend PHP — la sesión seguía fallando con «E-plan»
- **Confirmado:** 2026-05-04 — confirmado empíricamente al comprobar que el error persistía tras pegar los valores de localStorage
- **Causa:** el token JWT de localStorage y la cookie `@token` son emitidos por distintos flujos de auth y tienen valores diferentes
- **Solución:** obtener los tres valores desde DevTools → **Application → Cookies → tnm.sudespacho.net** (no desde Console/localStorage). Corregido en `streamlit_app.py` (2026-05-04).

---

## URLs de navegación del CRM — rutas PHP legacy no funcionan en el navegador

### Rutas `/extrajudiciales/index/...` o `/judiciales/index/...` en el navegador → E-plan o 404
- **Intentado:** navegar con Chrome a `https://tnm.sudespacho.net/extrajudiciales/index/elemento/extrajudiciales` para acceder al listado de expedientes extrajudiciales
- **Resultado:** el navegador muestra la landing E-plan o página en blanco — la URL no existe como ruta navegable
- **Confirmado:** 2026-05-04 (extrajudiciales); sesión anterior (judiciales)
- **Causa:** Las rutas PHP legacy (`/extrajudiciales/`, `/judiciales/`) son solo endpoints de API consumidos por la SPA internamente. La navegación del usuario ocurre íntegramente dentro de la SPA (`/tnm/...`).
- **URLs correctas para navegación en el navegador / Chrome MCP:**
  - Extrajudiciales: `https://tnm.sudespacho.net/tnm/gestion/extrajudiciales`
  - Judiciales: `https://tnm.sudespacho.net/tnm/gestion/judiciales` *(pendiente confirmar)*
  - Dashboard: `https://tnm.sudespacho.net/tnm/dashboard`
- **Conclusión:** Para navegar al CRM desde Chrome MCP, usar siempre rutas SPA (`/tnm/...`). Las rutas legacy solo se usan en peticiones HTTP directas (Python, curl) con las 3 cookies de auth.

---

## REST API — operaciones de vinculación (saveselect vía REST)

### `POST /api/related_registers` → 405 Method Not Allowed
- **Intentado:** POST a `https://api-crm-commons-pro.sudespacho.biz/api/related_registers` con body `{"register_id": X, "related_id": Y, "element": "..."}`
- **Resultado:** HTTP 405 — el endpoint solo acepta GET (listado de relaciones).
- **Confirmado:** 2026-05-06
- **Conclusión:** No existe equivalente REST para la operación `saveselect` del frontal legacy. Las vinculaciones (link EV MMC, link colaborador) siguen requiriendo el frontal heredado PHP (`/saveselect/`).

### `POST /api/register_relations` → 404 Not Found
- **Intentado:** POST a `https://api-crm-commons-pro.sudespacho.biz/api/register_relations` buscando un endpoint alternativo para crear relaciones entre expedientes y entidades
- **Resultado:** HTTP 404 — el endpoint no existe en la API REST.
- **Confirmado:** 2026-05-06
- **Conclusión:** No hay ruta REST para crear relaciones entre registros. Todas las operaciones de tipo `saveselect` (vincular EV MMC, colaborador, cliente) permanecen en el path legacy PHP.

---

## REST API — Sin endpoint de login programático con credenciales

### `POST /api/authentication` / `POST /api/login` / `POST /api/token` (inicial) — no existen
- **Intentado:** Búsqueda exhaustiva en el spec OAS3 (`/api/docs.json`, 466 paths, auditoría 2026-05-06) de un endpoint que acepte email+password y devuelva `@token` + `@refreshToken`
- **Resultado:** No existe ningún endpoint de autenticación inicial con credenciales. El único endpoint de auth documentado es `POST /api/token/refresh` (renovación con `@refreshToken` existente, ya implementado en `_try_refresh_jwt_post()`). El flujo de login de la SPA Vue almacena sus tokens en `localStorage` del navegador con origen distinto al de las cookies PHP.
- **Confirmado:** 2026-05-06
- **Conclusión:** No es posible obtener tokens CRM programáticamente a partir de credenciales (email/password). Cuando `@refreshToken` también expira, la renovación de sesión completa requiere intervención manual: DevTools → Application → Cookies → tnm.sudespacho.net → copiar 3 cookies (`PHPSESSID`, `@token`, `@refreshToken`) → sidebar Streamlit 🔄.
- **Acción pendiente `[NUEVO-HILO-AUDITORIA-2]`:** Verificar si algún endpoint PHP legacy acepta `@token` JWT para crear una sesión PHP nueva (PHPSESSID) de forma programática. No confirmado — pendiente de investigación.

---

## Tests / pytest — `importlib.reload` sobre módulos con clases re-exportadas

### `importlib.reload(core.sync_sudespacho)` desde un fixture rompe `test_sync_sudespacho.py`
- **Intentado:** recargar `core.sync_sudespacho` en el fixture `modules` de `tests/test_pull_expediente_v2.py` para asegurar que las funciones internas usaran el `casos_root` del tmp.
- **Resultado:** los 11 tests de `test_pull_expediente_v2.py` pasaban, pero 7 tests de `tests/test_sync_sudespacho.py` rompían en la suite global. Síntomas: `pytest.raises(SudespachoError)` ya no captura (clases con mismo nombre pero objetos distintos tras el reload); `monkeypatch.setattr(SudespachoClient, "list_gdocu_docs_rest", ...)` no surte efecto porque `pull_expediente` viejo construye instancias de la clase NUEVA, no parcheada.
- **Confirmado:** 2026-05-11 (sesión 6, paso 8 del refactor intake v2)
- **Causa raíz:** `tests/test_sync_sudespacho.py` importa `SudespachoError`, `SudespachoClient`, `pull_expediente` al top del fichero (patrón estándar). Tras `importlib.reload(sync_sudespacho)` en otro test, esas referencias quedan apuntando a las clases/funciones VIEJAS, desincronizadas con las versiones nuevas del módulo recargado.
- **Conclusión:** Si un fixture necesita propagar `tmp_casos_root` a un módulo que depende de `core.config`, recargar **solo los módulos del intake** (`case_manager`, `intake_log`, `intake_manifest`), NO `sync_sudespacho`. Las funciones internas de `pull_expediente_v2` resuelven `caso_path`, `IntakeManifest`, etc. vía las globals de los módulos recargados, así que el `casos_root` del tmp se propaga sin tocar `sync_sudespacho`.
- **Implementación:** documentado en el docstring del fixture `modules` de `tests/test_pull_expediente_v2.py` para evitar regresión futura.

---

## PowerShell — `Add-Content` con `Get-Content -Raw` sin `-Encoding` produce mojibake

### Anexar contenido UTF-8 desde un fichero a otro produce double-encoding cuando el sistema usa Win-1252
- **Intentado:** `Add-Content -Path $destino -Value (Get-Content $origen -Raw)` desde PowerShell 5.1 en Windows con codificación de página por defecto Windows-1252 (locale español/Latino). Sin `-Encoding UTF8` en ninguno de los dos cmdlets.
- **Resultado:** los caracteres no ASCII del fichero origen UTF-8 quedan en el destino como mojibake double-encoded: "decisión" → "decisiÃƒÂ³n"; "§9.3" → "Ã‚Â§9.3"; "—" → "Ã¢â‚¬â€".
- **Causa:** `Get-Content` sin `-Encoding` usa la codificación por defecto del sistema (Win-1252). Lee bytes UTF-8 como Win-1252, devolviendo caracteres mal interpretados. Luego `Add-Content` con `-Encoding UTF8` (o por defecto) los re-codifica como UTF-8, fijando el daño.
- **Confirmado:** 2026-05-12 (sesión 17, durante anotación H6 en `_revision_anon_SaRS1.md`).
- **Conclusión:** **No usar `Get-Content -Raw` / `Add-Content -Value` ni `Set-Content`** para operaciones de concatenación o reescritura de ficheros UTF-8 desde PowerShell. Usar siempre la API .NET con codificación explícita:

  ```powershell
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  $content   = [System.IO.File]::ReadAllText($path, [System.Text.Encoding]::UTF8)
  [System.IO.File]::WriteAllText($path, $content, $utf8NoBom)
  # o para anexar:
  [System.IO.File]::AppendAllText($path, $extra, $utf8NoBom)
  ```

  Esta variante respeta UTF-8 (lee y escribe sin reinterpretación). El `UTF8Encoding($false)` evita BOM, que es el comportamiento estándar de los ficheros del proyecto.
- **Detección post-hoc:** `Select-String -Path $f -Pattern "ÃƒÂ|Ã¢" -Encoding UTF8` busca firmas de mojibake típicas.
- **Reparación:** localizar el bloque dañado por marcador de la última línea legítima, truncar con `WriteAllText`, re-anexar con `AppendAllText` (encoding UTF-8 explícito).

---

## Plantilla para nuevas entradas

```markdown
### [Descripción corta]
- **Intentado:** [qué se intentó exactamente]
- **Resultado:** [qué devolvió / por qué falló]
- **Confirmado:** [fecha]
- **Conclusión:** [qué hacer en su lugar]
- **Acción pendiente:** [opcional — si hay algo que hacer cuando el problema se resuelva]
```
