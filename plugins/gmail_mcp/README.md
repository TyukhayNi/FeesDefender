# MCP `gmail-multiaccount` — lectura + etiquetado

Servidor MCP local (stdio) que mantiene varias cuentas de Gmail del despacho
autenticadas simultáneamente. Permite **buscar y leer** correo y **etiquetar**
(crear una etiqueta de usuario y aplicarla/quitarla a un mensaje o hilo) desde
Claude Code y Cowork.

Gemelo de `plugins/google_despacho_mcp/` (mismo patrón: `build_server` con
inyección de `service`, CLI de cuentas, `run_server.bat`, `dxt-build/`).

## Alcance (scope OAuth)

`https://www.googleapis.com/auth/gmail.modify` — subsume `gmail.readonly` y NO
permite borrado permanente ni IMAP/SMTP total. Fijado en `gmail_auth.SCOPES`;
ampliarlo exige editar ese fichero y reautorizar cada cuenta.

## Herramientas

| Herramienta | Función |
|---|---|
| `list_accounts` | Lista las cuentas conectadas |
| `search_messages` | Busca con sintaxis Gmail; en una cuenta o en todas |
| `read_message` | Lee un mensaje completo (cuerpo en texto) |
| `read_thread` | Lee un hilo completo ordenado por fecha |
| `list_labels` | Lista etiquetas `{id, name}` de una o todas las cuentas |
| `list_attachments` | Lista adjuntos de un mensaje |
| `get_attachment` | Descarga un adjunto a disco (confinable con `GMAIL_DL_ROOT`) |
| `create_label` | Crea (idempotente) una etiqueta de usuario |
| `apply_label` | Aplica una etiqueta de usuario a un mensaje/hilo |
| `remove_label` | Quita una etiqueta de usuario de un mensaje/hilo |

## Guardarraíles

- **Solo etiquetas de usuario.** Se rechazan las de sistema (INBOX, SENT, DRAFT,
  TRASH, SPAM, IMPORTANT, STARRED, UNREAD, CHAT y `CATEGORY_*`) por el campo
  `type` de la API + blocklist defensiva. Fail-closed ante etiqueta desconocida.
- **`account` obligatorio en toda escritura** (sin fan-out: nunca se modifican las
  cuentas a la vez).
- **Sin borrado** (mensajes ni etiquetas), **sin envío/borradores**, **sin
  archivar**, **sin marcar leído/no leído**. Esas tools no existen.

## Cuentas y tokens

Config-home en `~/.gmail-mcp/` (override `GMAIL_MCP_HOME`): `credentials.json`
(secreto OAuth de cliente, App de escritorio) + `tokens/<cuenta>.json` por cuenta.

```
python -m plugins.gmail_mcp.gmail_cli add       # alta (abre navegador)
python -m plugins.gmail_mcp.gmail_cli list      # cuentas conectadas
python -m plugins.gmail_mcp.gmail_cli remove EMAIL
```

Con scope `gmail.modify`, una cuenta con token `readonly` viejo dará
`invalid_scope` hasta reautorizar. Verifica que la app OAuth esté en
**Producción** antes de reautorizar (en *Testing* el refresh token caduca a 7
días).

## Requisitos

Python 3.10+ y las dependencias de `requirements.txt`.
