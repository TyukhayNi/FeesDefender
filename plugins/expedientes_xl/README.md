# expedientes-xl

Servidor MCP stdio **genérico** de operaciones de fichero acotadas a un sandbox de
directorios. Sin lógica de FeesDefender (no `import core`): solo opera sobre bytes.

## Requisitos
- Python 3 + `python -m pip install -r requirements.txt` (instala `mcp`).
- El directorio permitido montado en disco (p. ej. el Drive del despacho).

## Registro

### Claude Code
```
claude mcp add expedientes-xl -- python <ruta>/plugins/expedientes_xl/server.py "<allowed_dir>"
```

### Cowork (Claude Desktop, vía claude_desktop_config.json)
```json
{
  "mcpServers": {
    "expedientes-xl": {
      "command": "python",
      "args": ["<ruta>/plugins/expedientes_xl/server.py", "<allowed_dir>"]
    }
  }
}
```

Opcional: añadir `--max-b64-bytes N` tras `<allowed_dir>` para el tope de
`write_file_base64` (def. 8 MiB). Se pueden pasar varios `<allowed_dir>`.

## Tools
`hash_path` · `copy_path` · `copy_dir` · `extract_archive` · `write_file_base64` ·
`append_text` · `delete_path`.

Toda ruta se valida contra los `allowedDirectories` (saneado anti path-traversal,
incluido por miembro en `extract_archive`); `write_file_base64` tiene tope de tamaño
duro. La lógica pura vive en `fsops.py` (testeada en `tests/test_expedientes_xl_fsops.py`);
`server.py` es el wrapper FastMCP.

## Verificación
- `python -m pytest tests/test_expedientes_xl_fsops.py tests/test_expedientes_xl_server.py -v`
- `claude mcp add … && claude mcp list` → debe salir `expedientes-xl … √ Connected`.
