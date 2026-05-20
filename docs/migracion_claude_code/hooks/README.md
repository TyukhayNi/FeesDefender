# Hooks (opcionales)

Los hooks de Claude Code permiten ejecutar scripts automáticos en momentos clave:
antes de un commit, antes de tocar un fichero, tras una llamada de tool, etc.

No son necesarios para arrancar. Esta guía propone tres hooks que tienen sentido
para FeesDefender; añádelos cuando los necesites.

## 1. Pre-commit — bloquear commit si core/ rompe tests

`core/` tiene tests obligatorios. Este hook valida que la suite pasa antes de
permitir un commit que toque `core/**`.

Crear `.claude/hooks/pre-commit-core-tests.ps1`:

```powershell
# Si el diff staged toca core/, ejecutar tests; abortar si fallan.
$stagedCore = git diff --cached --name-only | Select-String "^core/"
if (-not $stagedCore) { exit 0 }

cd "G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes"
python -m pytest -q --tb=no
if ($LASTEXITCODE -ne 0) {
    Write-Host "Suite roja — commit bloqueado." -ForegroundColor Red
    exit 1
}
exit 0
```

Registrar en `.claude/settings.json`:

```json
"hooks": {
  "PreToolUse": [
    {
      "matcher": "Bash",
      "command": "powershell -ExecutionPolicy Bypass -File .\\.claude\\hooks\\pre-commit-core-tests.ps1",
      "when": "tool.input.command =~ /^git commit/"
    }
  ]
}
```

## 2. Post-edit — recordatorio sobre data/CASOS/

Si por error se intenta editar algo en `data/CASOS/`, la regla `deny` ya lo
bloquea. Este hook complementa con un mensaje recordatorio cuando se edita
algo en una ruta sospechosamente cercana.

Crear `.claude/hooks/post-edit-warn-casos.ps1`:

```powershell
param([string]$Path)
if ($Path -match "data\\CASOS") {
    Write-Host "AVISO: data/CASOS/ esta en .gitignore. Verifica que no commiteas datos reales." -ForegroundColor Yellow
}
```

## 3. Pre-tool — comprobar PHPSESSID antes de scripts CRM

Antes de cualquier `python -m scripts.sync_sudespacho ...`, validar que la
sesión está viva. Si está caducada, sugerir `/renovar-php`.

Crear `.claude/hooks/pre-tool-check-php.ps1`:

```powershell
param([string]$Command)
if ($Command -match "sync_sudespacho|scheduled_sync|bulk_pull") {
    cd "G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes"
    $out = python -m scripts.sync_sudespacho check-legacy 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "PHPSESSID caducada. Ejecuta /renovar-php antes de continuar." -ForegroundColor Yellow
        exit 1
    }
}
exit 0
```

## Cuándo añadirlos

No al principio. Empieza sin hooks, opera 1-2 semanas con la configuración
mínima, y añade hooks solo si detectas un patrón de error que un hook podría
prevenir.

Los hooks pueden ser fuente de fricción si están mal escritos — un PreToolUse
que falla aleatoriamente bloquea el agente. Mejor 0 hooks que 1 hook frágil.
