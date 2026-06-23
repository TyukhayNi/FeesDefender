# Plugin `feesdefender`

Plugin del despacho Tyukhay Legal:
- **Conector `expedientes-xl`** — depósito de ficheros al expediente (server-side, auto-contenido)
- **Conector `email-export`** — vuelca una etiqueta Gmail al expediente como `.eml` fieles + adjuntos (requiere `core/` del repo)
- **Skill `intake-expediente`** — intake con trazabilidad forense
- **Skill `exportar-correos-etiqueta`** — guía para invocar el export desde Cowork/Claude Code

Esto es la **SSOT de metadatos** del plugin; los conectores y las skills viven en sus propias
ubicaciones (`plugins/expedientes_xl/`, `plugins/email_export_mcp/`, `.claude/skills/<skill>/`)
y se ensamblan con el build.

## Build (reproducible)
```
python -m scripts.package_plugin
```
Ensambla `dist/plugin/` (gitignored) copiando este `plugin-src/` + los conectores + las skills.

---

## Conector `expedientes-xl`

Copia ficheros (incluidos binarios) al Drive del despacho montado en `G:`. Auto-contenido.

### Prerrequisitos
- Python 3 + `pip install mcp`
- Drive montado en `G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL`

---

## Conector `email-export`

Exporta todos los mensajes de una etiqueta Gmail al expediente como `.eml` fieles.

### Tool expuesta
`export_label_emails(ref, account, label, extraer_adjuntos?, workers?, force?)`
- `ref`: case_id canónico o W-code (p.ej. `W-02VND1`)
- `account`: cuenta Gmail (los casos E&V → `nikolai.tyukhay@engelvoelkers.com`)
- `label`: nombre exacto de la etiqueta Gmail
- `extraer_adjuntos`: False por defecto (estructura plana); True → subcarpetas fechadas
- `workers`: hilos paralelos de descarga (default 8)
- `force`: True → re-descarga aunque el mensaje ya esté en el índice

### Prerrequisitos (específicos del conector `email-export`)

Este conector importa `core/` del repo FeesDefender (a diferencia de `expedientes-xl`,
que es auto-contenido). Solo funciona en la máquina donde:
1. Existe el clon del repo (`C:\Users\tnm33\Dev\FeesDefender`).
2. Existe el token OAuth para la cuenta Gmail en `~/.gmail-mcp/tokens/<cuenta>.json`.
3. El Drive del despacho está montado en `G:` (para escribir los `.eml`).
4. Las deps de Google están instaladas (`google-auth`, `google-api-python-client`, etc.).

**Limitación — dónde NO funciona:**
- Móvil / navegador (sin token, sin `G:`).
- PC de Paola o Ana (no tienen token OAuth; para ellas → botón Streamlit en el PC del abogado).
- Cowork en la nube (no accede al token local ni a `G:`).

Para esos casos, el motor equivalente es el **botón Streamlit** («✉️ Exportar correos por etiqueta»)
o el **CLI** `scripts/export_label_emails.py` ejecutados en el PC del abogado.

---

## Instalación local (Claude Code)
```powershell
python -m scripts.package_plugin
claude plugin marketplace add <ruta>\dist\plugin
claude plugin install feesdefender@despacho-tyukhay
```
Las tools del MCP cargan al reiniciar la sesión (host-side).

---

## Cowork (Claude Desktop en el PC del abogado)

El plugin **no carga nativo en Cowork** (Cowork no hereda los plugins de Claude Code).
Para que Cowork use los conectores desde el mismo PC, añadir las entradas en
`%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "expedientes-xl": {
      "command": "python",
      "args": [
        "C:\\Users\\tnm33\\Dev\\FeesDefender\\plugins\\expedientes_xl\\server.py",
        "G:\\Unidades compartidas\\EXPEDIENTES - TYUKHAY LEGAL"
      ]
    },
    "email-export": {
      "command": "python",
      "args": [
        "C:\\Users\\tnm33\\Dev\\FeesDefender\\plugins\\email_export_mcp\\server.py"
      ]
    }
  }
}
```

> El server `email-export` detecta la raíz del repo automáticamente a partir de la
> ubicación del script; no hace falta pasar `--repo-root` si el script se ejecuta
> desde la ruta canónica del repo.

Reiniciar Claude Desktop (Cowork) tras editar el config.

Para las **skills** → re-import del `.skill` (flujo actual del despacho).

---

## Distribución al despacho (repo privado)
1. `python -m scripts.package_plugin`
2. Copiar `dist/plugin/` al clon de `despacho-plugins` → commit/push.
3. Cada compañero: añade el marketplace `TyukhayNi/despacho-plugins` en Claude Desktop e instala `feesdefender`.
4. Prerrequisito por máquina: Drive en `G:` + `pip install mcp` + (para `email-export`) token OAuth + repo FeesDefender clonado.

## Crecer incremental
Añadir más skills al plugin: incluirlas en la lista `SKILLS` de `scripts/package_plugin.py`
y re-ejecutar el build. Añadir más conectores: incluirlos en `CONECTORES`.
