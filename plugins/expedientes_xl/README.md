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

Zonas por *tier* (spec §2): pasar `--rw DIR` (lectura+escritura, repetible) y/o
`--ro DIR` (solo-lectura en V1, repetible); un `<allowed_dir>` posicional se trata como
`--rw` (compat). Opcional: `--max-b64-bytes N` para el tope de `write_file_base64`
(def. 8 MiB).

## Tools
`hash_path` · `hash_tree` · `copy_path` · `copy_dir` · `extract_archive` ·
`write_file_base64` · `append_text`.

**Sin borrado** (`delete_path` retirado de la superficie, spec §2).

Toda ruta se valida contra los `allowedDirectories` (saneado anti path-traversal,
incluido por miembro en `extract_archive`) y contra las zonas: Tier 0
(`90_Notas personales`) nunca se lee ni se escribe; Tier 1 (`00_Input` y backups) es
forense-inmutable salvo el carve-out de protocolo. Las operaciones pesadas
(`hash_tree`/`copy_dir`/`extract_archive`) pasan por un semáforo de E/S y responden con
error legible si superan `XL_OP_TIMEOUT`. `write_file_base64` tiene tope de tamaño duro.
La lógica pura vive en `fsops.py`/`tiers.py`/`guards.py` (testeadas en `tests/`);
`server.py` es el wrapper FastMCP.

## Verificación
- `python -m pytest tests/test_expedientes_xl_fsops.py tests/test_expedientes_xl_server.py -v`
- `claude mcp add … && claude mcp list` → debe salir `expedientes-xl … √ Connected`.
