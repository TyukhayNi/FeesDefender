# expedientes-xl — extensión `.dxt` para Cowork

Empaquetado del MCP `expedientes-xl` como extensión Claude Desktop (`.dxt`) para que
**Cowork** (la VM del espacio de trabajo) lo consuma. **Importante:** las entradas de
`claude_desktop_config.json` alimentan el chat directo de Desktop y Claude Code, pero
**NO llegan a Cowork** — Cowork solo consume extensiones `.dxt` (mismo patrón que
`gmail_mcp` y `google_despacho_mcp`).

## Manifest (`manifest.json`)

- Arranca `python -m expedientes_xl.server --rw G:\ --ro H:\`.
- `command` = **ruta absoluta** al Python real (`pythoncore-3.14-64\python.exe`), no
  `python` a secas: el stub de la Microsoft Store (`WindowsApps\python.exe`) que ve
  Claude Desktop en su PATH aborta el arranque (mismo motivo por el que gmail/google
  usan ruta absoluta).
- `-m expedientes_xl.server` (no `server.py` suelto): los módulos hermanos usan imports
  de paquete (`from . import ...`).
- `env.PYTHONPATH` apunta a `plugins/` del repo para que `-m` encuentre el paquete.

## Rebuild del `.dxt`

```powershell
python - <<'PY'
import zipfile, os
root = r"C:\Users\tnm33\Dev\FeesDefender\plugins\expedientes_xl"
dxt = os.path.join(root, "dxt-build")
out = os.path.join(dxt, "expedientes-xl.dxt")
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    z.write(os.path.join(dxt, "manifest.json"), "manifest.json")
    for f in sorted(os.listdir(root)):
        if f.endswith((".py", ".txt", ".md")) and f != "run_server.bat":
            z.write(os.path.join(root, f), f"expedientes_xl/{f}")
PY
```

## Importar en Cowork

Claude Desktop → **Ajustes → Extensiones → Instalar extensión** → seleccionar
`expedientes-xl.dxt`. Reiniciar Cowork. Verificar en un chat de Cowork:
`list_dir` sobre `G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\CASOS`.
