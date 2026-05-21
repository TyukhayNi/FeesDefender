# copiar_skills.ps1
# ---
# Copia las skills relevantes de FeesDefender desde la instalación de Cowork
# a .claude/skills/ del repo.
#
# Uso:
#   .\docs\migracion_claude_code\skills\copiar_skills.ps1            # solo las que faltan
#   .\docs\migracion_claude_code\skills\copiar_skills.ps1 -Force     # sobreescribe todas

[CmdletBinding()]
param(
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

$repoRoot = "G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes"
Set-Location $repoRoot

$destinoBase = Join-Path $repoRoot ".claude\skills"
if (-not (Test-Path $destinoBase)) {
    New-Item -ItemType Directory -Force -Path $destinoBase | Out-Null
}

# --- Localizar origen de skills ---

$origenCanonico = "C:\Users\tnm33\AppData\Roaming\Claude\local-agent-mode-sessions\skills-plugin\6c9fdc80-48fa-4623-ab08-dae679510ce5\79faa18e-1db3-4cf2-bbba-9a595e4e4b28\skills"

$origen = $null

if (Test-Path $origenCanonico) {
    $origen = $origenCanonico
    Write-Host "[origen] Ruta canonica detectada: $origen" -ForegroundColor DarkGray
} else {
    Write-Host "[origen] Ruta canonica no existe. Buscando..." -ForegroundColor Yellow
    $candidatos = Get-ChildItem -Path "$env:APPDATA\Claude" -Recurse -Filter "SKILL.md" -ErrorAction SilentlyContinue |
        ForEach-Object { Split-Path $_.FullName -Parent | Split-Path -Parent } |
        Select-Object -Unique

    if ($candidatos.Count -eq 0) {
        Write-Host "ERROR: no se encontro ningun directorio de skills bajo $env:APPDATA\Claude" -ForegroundColor Red
        Write-Host "Verifica que Cowork esta instalado y al menos una skill ha sido cargada alguna vez." -ForegroundColor Red
        exit 1
    }

    $origen = $candidatos[0]
    Write-Host "[origen] Detectado: $origen" -ForegroundColor DarkGray
}

# --- Skills a copiar ---

$skills = @(
    'preparacion-litigio-civil',
    'escritos-judiciales',
    'cendoj-descarga',
    'docx',
    'xlsx',
    'pdf'
)

$stats = @{ ok = 0; skip = 0; miss = 0; overwrite = 0 }

foreach ($skill in $skills) {
    $src = Join-Path $origen $skill
    $dst = Join-Path $destinoBase $skill

    if (-not (Test-Path $src)) {
        Write-Host ("MISS  {0,-30}  (no existe en origen)" -f $skill) -ForegroundColor Yellow
        $stats.miss++
        continue
    }

    if ((Test-Path $dst) -and (-not $Force)) {
        Write-Host ("SKIP  {0,-30}  (ya existe en .claude/skills/; usa -Force para sobreescribir)" -f $skill) -ForegroundColor DarkGray
        $stats.skip++
        continue
    }

    if (Test-Path $dst) {
        Remove-Item -Recurse -Force $dst
        $stats.overwrite++
    }

    Copy-Item -Recurse -Force $src $dst

    $skillMd = Join-Path $dst "SKILL.md"
    if (Test-Path $skillMd) {
        Write-Host ("OK    {0,-30}  -> .claude\skills\{0}\" -f $skill) -ForegroundColor Green
        $stats.ok++
    } else {
        Write-Host ("WARN  {0,-30}  copiada pero falta SKILL.md" -f $skill) -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Resumen:" -ForegroundColor Cyan
Write-Host ("  OK         : {0}" -f $stats.ok)
Write-Host ("  Sobreescritas: {0}" -f $stats.overwrite)
Write-Host ("  Saltadas   : {0}" -f $stats.skip)
Write-Host ("  No encontradas: {0}" -f $stats.miss)
Write-Host ""

if ($stats.ok -eq 0 -and $stats.overwrite -eq 0) {
    Write-Host "No se copio nada. Las skills ya estan instaladas o no se encontraron." -ForegroundColor Yellow
} else {
    Write-Host "Skills disponibles en .claude\skills\. Se cargan automaticamente al abrir Claude Code en este directorio." -ForegroundColor Green
}
