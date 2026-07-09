# MCP `google-despacho` — F1 (lectura de Drive multicuenta)

Servidor stdio local (FastMCP) que da lectura de Google Drive sobre varias
cuentas a la vez (`@tyukhay.legal` + `@engelvoelkers.com`), incluidas todas las
unidades compartidas, sin reautenticar al cambiar de cuenta.

**F1 es SOLO LECTURA**: scope `drive.readonly` + solo tools de lectura. La
escritura llega en F2.

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
`python plugins/google_despacho_mcp/server.py` como server stdio.

## Variables de entorno

- `GOOGLE_DESPACHO_HOME` — raíz de config (default `~/.google-despacho`).
- `GOOGLE_DESPACHO_DL_ROOT` — si se define, confina los destinos de
  `download_file_content` a esa carpeta.

## Tools (F1)

`list_accounts`, `list_shared_drives`, `search_files`, `list_recent_files`,
`get_file_metadata`, `get_file_permissions`, `read_file_content`,
`download_file_content`, `about_get`. Todas aceptan `account`; las de búsqueda/
listado lo omiten para consultar todas las cuentas.
