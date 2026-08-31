# MCP `google-despacho` — F1+F2 (lectura + escritura de Drive multicuenta)

Servidor stdio local (FastMCP) que da acceso a Google Drive sobre varias
cuentas a la vez (`@tyukhay.legal` + `@engelvoelkers.com`), incluidas todas las
unidades compartidas, sin reautenticar al cambiar de cuenta.

**F1** era SOLO LECTURA (scope `drive.readonly`). **F2** añade ESCRITURA (CRUD
de ficheros/carpetas), PERMISOS (con guardarraíl de compartición externa) y
NAVEGACIÓN. El scope OAuth pasa a `drive` (completo) — ver «Actualizar de F1 a
F2» más abajo.

## Prerrequisitos (una vez)

1. En Google Cloud Console (proyecto `Gmail MCP Despacho`, el mismo de Gmail):
   habilitar **Google Drive API**. La pantalla de consentimiento ya está
   `En producción` (R2) → no hay caduca-7-días.
2. Descargar el secreto OAuth de cliente (tipo **App de escritorio**) →
   guardarlo como `~/.google-despacho/credentials.json`
   (o `$GOOGLE_DESPACHO_HOME/credentials.json`). Puede ser el mismo cliente que Gmail.
3. Instalar dependencias en el intérprete que usará el server:
   `python -m pip install -r plugins/google_despacho_mcp/requirements.txt`

## Conectar las cuentas

```powershell
cd "C:\Users\tnm33\Dev\FeesDefender"
python plugins\google_despacho_mcp\google_cli.py add   # repetir para cada cuenta
python plugins\google_despacho_mcp\google_cli.py list
```

Al autorizar aparecerá el aviso **"Google no ha verificado esta app"** (app sin
verificar, scope restringido) → *Configuración avanzada → Ir a … (no seguro)*.
Es esperado; tope de 100 usuarios, sobra para 2.

## Registrar en Claude Desktop

En `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "google-despacho": {
      "command": "C:\\Users\\tnm33\\Dev\\FeesDefender\\plugins\\google_despacho_mcp\\run_server.bat"
    }
  }
}
```

Reiniciar Claude Desktop. El puente expone el conector a Cowork/claude.ai
(igual que Gmail). Requisito operativo: PC encendido + app de escritorio + puente.

## Ejecutar desde Claude Code

Añadir a la config MCP de Claude Code el mismo comando, o lanzar
`cmd /c plugins/google_despacho_mcp/run_server.bat` como server stdio (el wrapper
elige el intérprete probando que puede importar `mcp.server.fastmcp`; con `python`
pelado puede tocarte uno con mcp 2.0, que retiró ese módulo).

## Actualizar de F1 a F2

F2 sube el scope OAuth de `drive.readonly` a `drive` (completo). Los tokens de
F1 quedan cortos de scope: hay que **reautorizar ambas cuentas una vez**:

```powershell
cd "C:\Users\tnm33\Dev\FeesDefender"
python plugins\google_despacho_mcp\google_cli.py add   # repetir para cada cuenta
```

## Variables de entorno

- `GOOGLE_DESPACHO_HOME` — raíz de config (default `~/.google-despacho`).
- `GOOGLE_DESPACHO_DL_ROOT` — si se define, confina los destinos de
  `download_file_content` a esa carpeta.
- `GOOGLE_DESPACHO_UPLOAD_ROOT` — si se define, confina los orígenes locales de
  `upload_file` y `update_file_content` (parámetro `local_path`) a esa carpeta.

Ninguna de las dos raíces deja pasar los bytes por el modelo: son solo el
punto de entrada/salida a disco local.

## Tools (F1 — lectura)

`list_accounts`, `list_shared_drives`, `search_files`, `list_recent_files`,
`get_file_metadata`, `get_file_permissions`, `read_file_content`,
`download_file_content`, `about_get`. Todas aceptan `account`; las de búsqueda/
listado lo omiten para consultar todas las cuentas.

## Tools (F2 — escritura, permisos, navegación)

**Escritura** (CRUD de ficheros/carpetas):

- `create_file(name, parent_id, text, account, mime_type="text/plain")` — crea
  un fichero de TEXTO con contenido del modelo. Para binarios/grandes usa
  `upload_file`.
- `upload_file(local_path, parent_id, account, name=None)` — sube un fichero
  desde ruta LOCAL (confinada por `GOOGLE_DESPACHO_UPLOAD_ROOT`); los bytes NO
  pasan por el modelo.
- `create_folder(name, parent_id, account)` — crea una carpeta.
- `ensure_folder_path(path, parent_id, account)` — crea los segmentos de
  `path` que falten bajo `parent_id`, IDEMPOTENTE (no duplica carpetas
  existentes).
- `copy_file(file_id, dst_folder_id, account, new_name=None)` — copia un
  fichero a otra carpeta (server-side).
- `update_file_content(file_id, account, text=None, local_path=None)` —
  reemplaza el contenido de un fichero existente; `text` O `local_path`
  (confinado por `GOOGLE_DESPACHO_UPLOAD_ROOT`), no ambos.
- `update_file_metadata(file_id, name, account)` — renombra un fichero.
- `move_file(file_id, dst_folder_id, account)` — mueve un fichero de carpeta.
- `delete_file(file_id, account, permanent=False)` — a la papelera por
  defecto (reversible con `restore_file`); `permanent=true` borra
  irreversiblemente.
- `restore_file(file_id, account)` — saca un fichero de la papelera.
- `append_text(file_id, text, account)` — añade texto al final de un fichero
  de TEXTO existente (p. ej. `_intake_log.jsonl`); read-modify-write
  server-side.
- `export_to_drive(file_id, account, format="pdf", dst_folder_id=None, new_name=None)`
  — exporta un Doc nativo a PDF u Office y guarda el resultado en Drive
  (server-side, sin bytes por el modelo).
- `create_shortcut(target_id, dst_folder_id, account, name=None)` — crea un
  acceso directo (enlaza un doc en varias carpetas sin duplicar bytes).

**Permisos** (ACL):

- `create_permission(file_id, perm_type, role, account, email_address=None, domain=None, allow_external=False, send_notification_email=False)`
- `update_permission(file_id, permission_id, role, account, allow_external=False)`
- `delete_permission(file_id, permission_id, account)`

Guardarraíl (`allow_external`): `perm_type` es `user|group|domain|anyone`;
`role` es `reader|commenter|writer` (**`owner` nunca se concede**, en
`create_permission` ni en `update_permission`). Compartir con `type=anyone` o
con un dominio distinto de `tyukhay.legal`/`engelvoelkers.com` está bloqueado
salvo que se pase `allow_external=true` explícitamente. `send_notification_email`
por defecto `false` (no se avisa por email salvo que se pida).

**Navegación**:

- `list_folder(folder_id, account, max_results=200)` — hijos DIRECTOS de una
  carpeta (no recursivo).
- `list_trash(account, max_results=100)` — ficheros en la papelera de la
  cuenta.
- `get_folder_path(folder_id, account)` — miga de pan / ruta completa
  (raíz→hoja).
