# Plugin `feesdefender`

Plugin del despacho Tyukhay Legal: **conector `expedientes-xl`** (depósito de ficheros
al expediente, server-side) + **skill `intake-expediente`** (intake con trazabilidad).
Esto es la **SSOT de metadatos** del plugin; el conector y la skill viven en sus propias
ubicaciones (`plugins/expedientes_xl/`, `.claude/skills/intake-expediente/`) y se ensamblan
con el build.

## Build (reproducible)
```
python -m scripts.package_plugin
```
Ensambla `dist/plugin/` (gitignored) copiando este `plugin-src/` + el conector + la skill.

## Prerrequisitos por máquina
- Python 3 + `pip install mcp` (para el server `expedientes-xl`).
- Google Drive del despacho montado en `G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL`
  (ruta hardcodeada en `.mcp.json`; debe ser consistente entre máquinas).

## Instalación local (Claude Code)
```
claude plugin marketplace add <ruta>\dist\plugin
claude plugin install feesdefender@despacho-tyukhay
```
Las tools del MCP cargan al reiniciar la sesión (host-side).

## Distribución al despacho
La UI de Claude Desktop exige un marketplace en **repo git** (owner/repo o URL), no ruta
local. Para repartir:
1. Crear un repo **privado** `despacho-plugins` en GitHub.
2. Subir el contenido de `dist/plugin/` (marketplace + plugin) a ese repo.
3. Cada compañero: añade el marketplace en Claude Desktop por `owner/repo` e instala
   `feesdefender`. Necesita además el Drive montado + `pip install mcp`.

## Cowork
El plugin **no carga nativo en Cowork** (Cowork no hereda los plugins de Claude Code).
Para Cowork, la entrega es por los canales verificados:
- **Conector** → entrada `expedientes-xl` en `claude_desktop_config.json` (puente host-side).
- **Skills** → re-import del `.skill` (flujo actual del despacho).

## Crecer incremental
Añadir más skills al plugin = incluirlas en la copia de `scripts/package_plugin.py`
(la lista de skills) y `python -m scripts.package_plugin`. Empezamos mínimo
(intake + conector); las demás (sala-lectura, triaje, estilo…) se añaden luego.
