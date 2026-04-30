# DEAD ENDS — FeesDefender

> Registro permanente de intentos fallidos confirmados empíricamente.
> **No volver a intentar estas vías sin nueva evidencia de que el problema se ha resuelto.**
> Actualizar con fecha cuando se confirme un nuevo callejón.

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
- **Confirmado:** 2026-04-25
- **Conclusión:** Las carpetas solo son navegables vía frontal legacy.

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

## Plantilla para nuevas entradas

```markdown
### [Descripción corta]
- **Intentado:** [qué se intentó exactamente]
- **Resultado:** [qué devolvió / por qué falló]
- **Confirmado:** [fecha]
- **Conclusión:** [qué hacer en su lugar]
- **Acción pendiente:** [opcional — si hay algo que hacer cuando el problema se resuelva]
```
