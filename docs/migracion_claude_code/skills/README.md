# Skills — qué copiar y cómo

Las skills que ya usas en Cowork pueden funcionar igual en Claude Code copiándolas a `.claude/skills/<nombre>/SKILL.md` dentro del repo.

## Skills relevantes para FeesDefender

| Skill | Origen (Cowork) | Por qué la necesitas en el repo |
|---|---|---|
| `preparacion-litigio-civil` | `~/.claude/skills/preparacion-litigio-civil/` | Abrir expedientes nuevos, decisiones estratégicas previas |
| `escritos-judiciales` | `~/.claude/skills/escritos-judiciales/` | Generar `.docx` finales con formato Sala 1ª TS |
| `cendoj-descarga` | `~/.claude/skills/cendoj-descarga/` | Localizar y descargar sentencias del CENDOJ (requiere Chrome MCP) |
| `docx` | Anthropic skills | Manipulación de Word genérica |
| `xlsx` | Anthropic skills | Manipulación de Excel — usado por `scripts/render_plantillas.py` |
| `pdf` | Anthropic skills | Extracción/OCR de PDFs — usado en pipeline de anonimización |

Las **no relevantes** (no copiar): `pptx`, `setup-cowork`, `cowork-plugin-management:*`, `consolidate-memory`.

## Ruta exacta de origen

En tu instalación actual de Cowork, las skills viven en:

```
C:\Users\tnm33\AppData\Roaming\Claude\local-agent-mode-sessions\skills-plugin\6c9fdc80-48fa-4623-ab08-dae679510ce5\79faa18e-1db3-4cf2-bbba-9a595e4e4b28\skills\
```

(Esa ruta puede variar tras actualizaciones de Cowork. Si no existe, búscalas con `Get-ChildItem $env:APPDATA\Claude -Recurse -Filter SKILL.md`.)

## Método A — script automático (recomendado)

Ejecutar `copiar_skills.ps1` desde la raíz del repo:

```powershell
cd "G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes"
.\docs\migracion_claude_code\skills\copiar_skills.ps1
```

El script:

1. Localiza el directorio de skills de Cowork (con fallback si la ruta canónica no existe).
2. Copia las 6 skills relevantes a `.claude/skills/<nombre>/`.
3. Verifica que cada `SKILL.md` se ha copiado correctamente.
4. Imprime un resumen.

Si alguna skill no se encuentra, el script avisa pero no aborta — copia lo que pueda.

## Método B — copia manual

```powershell
cd "G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes"
New-Item -ItemType Directory -Force -Path ".claude\skills" | Out-Null

$origen = "C:\Users\tnm33\AppData\Roaming\Claude\local-agent-mode-sessions\skills-plugin\6c9fdc80-48fa-4623-ab08-dae679510ce5\79faa18e-1db3-4cf2-bbba-9a595e4e4b28\skills"

$skills = @(
    "preparacion-litigio-civil",
    "escritos-judiciales",
    "cendoj-descarga",
    "docx",
    "xlsx",
    "pdf"
)

foreach ($s in $skills) {
    $src = Join-Path $origen $s
    $dst = ".\.claude\skills\$s"
    if (Test-Path $src) {
        Copy-Item -Recurse -Force $src $dst
        Write-Host "OK   $s"
    } else {
        Write-Host "MISS $s (no encontrada en $src)"
    }
}
```

## Activación en Claude Code

Las skills copiadas a `.claude/skills/` se descubren automáticamente al abrir el repo. No requieren registro adicional.

Para invocarlas en una sesión, basta con que el contexto del mensaje encaje con su `description` — el agente la cargará proactivamente. También puedes forzarla con `/skill <nombre>`.

## Versionado

Las skills SÍ se versionan en el repo (`.claude/skills/` está fuera del `.gitignore`). Esto significa que cualquier mejora que hagas a una skill en este proyecto queda registrada en git y se propaga al equipo.

Si en algún momento quieres mantener tu copia divergente respecto a Cowork, no actualices con `copiar_skills.ps1` y edita directamente en `.claude/skills/`.

## Actualizar skills desde Cowork

Si Anthropic publica una nueva versión de una skill (o tú la mejoras dentro de Cowork), puedes re-sincronizar:

```powershell
cd "G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes"
.\docs\migracion_claude_code\skills\copiar_skills.ps1 -Force
```

El flag `-Force` sobreescribe lo que haya en `.claude/skills/`. Sin el flag, el script salta las que ya existen.
