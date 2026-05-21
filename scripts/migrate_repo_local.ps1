# scripts/migrate_repo_local.ps1
# ------------------------------------------------------------------------------
# Migracion del repo FeesDefender desde Drive for Desktop al SSD local.
# Resultado: repo en C:\Repos\FeesDefender + push a GitHub privado.
# data/CASOS/ se queda en Drive (parametrizado via CASOS_ROOT en .env).
#
# Uso (PowerShell, NO elevado):
#   cd "G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes"
#   .\scripts\migrate_repo_local.ps1 -GithubRemote git@github.com:USUARIO/feesdefender.git
#
# El script es idempotente: se puede reejecutar para reanudar.
# Cada paso valida el estado previo antes de actuar.
# ------------------------------------------------------------------------------

param(
    [string]$GithubRemote = "",
    [string]$LocalPath   = "C:\Repos\FeesDefender",
    [string]$CasosRoot   = "G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes\data\CASOS"
)

$ErrorActionPreference = "Stop"

# Helpers de salida ------------------------------------------------------------
function Write-Step($msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function Write-OK($msg)   { Write-Host "[OK]   $msg"   -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[WARN] $msg"   -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "[ERR]  $msg"   -ForegroundColor Red }

$DriveRoot = "G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes"

# --- 1. Pre-checks ------------------------------------------------------------
Write-Step "1. Pre-checks (repo origen, git status, suite verde)"

if (-not (Test-Path $DriveRoot)) {
    Write-Err "No encuentro el repo en $DriveRoot"
    exit 1
}
Set-Location $DriveRoot

# Git status limpio
$status = git status --porcelain
if ($status) {
    Write-Err "Hay cambios sin commitear. Resuelvelos antes de migrar:"
    git status --short
    exit 1
}
Write-OK "Git status limpio"

# Tests verdes
Write-Host "Ejecutando suite en Drive (puede tardar)..."
python -m pytest -q --tb=no
if ($LASTEXITCODE -ne 0) {
    Write-Err "La suite no esta verde en Drive. Aborta y arregla antes de migrar."
    exit 1
}
Write-OK "Suite verde en Drive"

# --- 2. Grep rutas hardcoded --------------------------------------------------
Write-Step "2. Buscar rutas hardcoded a Drive en codigo"

$patterns = @("core","scripts","tests","pages")
$hits = @()
foreach ($p in $patterns) {
    if (Test-Path $p) {
        $hits += Select-String -Path "$p\**\*.py" -Pattern "G:\\Unidades compartidas" -SimpleMatch -ErrorAction SilentlyContinue
    }
}
# Tambien revisar ficheros .py en raiz
$hits += Select-String -Path ".\*.py" -Pattern "G:\\Unidades compartidas" -SimpleMatch -ErrorAction SilentlyContinue

if ($hits.Count -gt 0) {
    Write-Warn "Encontradas rutas hardcoded a Drive ($($hits.Count) coincidencias):"
    $hits | ForEach-Object { Write-Host "  $($_.Path):$($_.LineNumber): $($_.Line.Trim())" }
    Write-Warn "Recomendado: parametrizar via os.environ['CASOS_ROOT'] antes de seguir."
    $resp = Read-Host "Continuar de todos modos? (s/N)"
    if ($resp -ne "s") { exit 1 }
} else {
    Write-OK "Sin rutas hardcoded a Drive en codigo"
}

# --- 3. Verificar remoto GitHub -----------------------------------------------
Write-Step "3. Verificar remoto GitHub"

$existingRemote = $null
try { $existingRemote = git remote get-url origin 2>$null } catch {}

if ($existingRemote) {
    Write-OK "Remoto 'origin' ya configurado: $existingRemote"
} elseif ($GithubRemote) {
    git remote add origin $GithubRemote
    $existingRemote = $GithubRemote
    Write-OK "Remoto 'origin' anadido: $GithubRemote"
} else {
    Write-Err "No hay remoto 'origin' configurado y no se paso -GithubRemote."
    Write-Host @"

Pasos previos manuales:
  1. Crear repo PRIVADO en github.com (nombre sugerido: feesdefender)
  2. NO inicializar con README/gitignore (ya existen)
  3. Copiar la URL SSH (git@github.com:USUARIO/feesdefender.git)
  4. Reejecutar este script con -GithubRemote esa-url

"@
    exit 1
}

# --- 4. Push a GitHub ---------------------------------------------------------
Write-Step "4. Push a GitHub"

$branch = git rev-parse --abbrev-ref HEAD
Write-Host "Pusheando rama '$branch' a origin..."
git push -u origin $branch
if ($LASTEXITCODE -ne 0) {
    Write-Err "Push fallo. Causas posibles: auth SSH no configurada, repo remoto no vacio, etc."
    exit 1
}
Write-OK "Push completado"

# --- 5. Clone local -----------------------------------------------------------
Write-Step "5. Clone a $LocalPath"

if (Test-Path $LocalPath) {
    Write-Warn "$LocalPath ya existe. Saltando clone."
} else {
    $parentDir = Split-Path $LocalPath -Parent
    if (-not (Test-Path $parentDir)) {
        New-Item -Path $parentDir -ItemType Directory -Force | Out-Null
    }
    git clone $existingRemote $LocalPath
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Clone fallo."
        exit 1
    }
    Write-OK "Clonado a $LocalPath"
}

# --- 6. Crear .venv local -----------------------------------------------------
Write-Step "6. Crear .venv en local"
Set-Location $LocalPath

if (Test-Path ".\.venv") {
    Write-Warn ".venv ya existe. Saltando creacion."
} else {
    python -m venv .venv
    Write-OK ".venv creado"
}

# --- 7. Instalar dependencias -------------------------------------------------
Write-Step "7. Instalar dependencias"

& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
if (Test-Path "requirements.txt") {
    & ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Err "pip install fallo."
        exit 1
    }
    Write-OK "Dependencias instaladas desde requirements.txt"
} else {
    Write-Warn "No hay requirements.txt. Revisa pyproject.toml o instala manualmente."
}

# --- 8. Configurar .env -------------------------------------------------------
Write-Step "8. Configurar .env local (con CASOS_ROOT apuntando a Drive)"

$envLocal  = Join-Path $LocalPath ".env"
$envSource = Join-Path $DriveRoot ".env"

if (Test-Path $envLocal) {
    Write-Warn ".env ya existe en local. NO se sobrescribe."
} elseif (Test-Path $envSource) {
    Copy-Item $envSource $envLocal
    Write-OK ".env copiado desde Drive"
} else {
    Write-Warn "No hay .env en Drive. Creando uno minimo."
    "" | Out-File $envLocal -Encoding utf8
}

# Parchear CASOS_ROOT (UTF-8 sin BOM)
if (Test-Path $envLocal) {
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $envContent = [System.IO.File]::ReadAllText($envLocal, $utf8NoBom)
    if ($envContent -match "(?m)^CASOS_ROOT=") {
        $envContent = $envContent -replace "(?m)^CASOS_ROOT=.*", "CASOS_ROOT=$CasosRoot"
    } else {
        if ($envContent -and -not $envContent.EndsWith("`n")) { $envContent += "`n" }
        $envContent += "CASOS_ROOT=$CasosRoot`n"
    }
    [System.IO.File]::WriteAllText($envLocal, $envContent, $utf8NoBom)
    Write-OK "CASOS_ROOT en .env apunta a $CasosRoot"
}

# --- 9. Validar suite desde local ---------------------------------------------
Write-Step "9. Ejecutar suite desde local (validacion final)"

& ".\.venv\Scripts\python.exe" -m pytest -q --tb=no
if ($LASTEXITCODE -ne 0) {
    Write-Err "La suite NO pasa desde local. Investigar antes de trabajar aqui."
    Write-Host @"

Posibles causas:
  - Rutas hardcoded que el grep del paso 2 no detecto
  - Dependencias que dependen de algun fichero solo presente en Drive
  - .env incompleto (credenciales, paths adicionales)

"@
    exit 1
}
Write-OK "Suite verde desde $LocalPath"

# --- 10. Resumen y siguientes pasos -------------------------------------------
Write-Step "Migracion completada"

Write-Host @"

Siguientes pasos manuales:

  1. Actualizar STATUS.md indicando la nueva ruta de trabajo:
       $LocalPath

  2. Actualizar CLAUDE.md (seccion 'Entorno de ejecucion') si hay menciones
     hardcoded de G:\Unidades compartidas. La logica debe seguir funcionando
     porque CASOS_ROOT lo parametriza, pero los ejemplos quedan obsoletos.

  3. Abrir Claude Code en la nueva ruta:
       cd $LocalPath

  4. Marcar el repo viejo en Drive para no usarlo:
     Renombrarlo a 'Base datos expedientes _BACKUP_PRE_MIGRACION' es la forma
     mas segura de evitar despistes. NO borrar todavia.

  5. Tras 1-2 semanas sin incidencias trabajando desde local:
     Borrar la copia vieja del repo en Drive (manteniendo data/CASOS/).
     data/CASOS/ se queda en Drive para que Paola y Ana sigan accediendo.

Recordatorio:
  - Esta migracion es independiente del despliegue E&V (Fases 0-5).
  - En la Fase 2 del despliegue, CASOS_ROOT pasara a apuntar al VPS Hetzner.

"@ -ForegroundColor Green
