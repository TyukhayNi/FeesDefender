---
tipo: handoff
estado: activo
creado: 2026-08-14
origen: sesión de Claude Code en el perfil "Nikolai Tyukhay 1" (procesal@tyukhay.legal) —
  continuación de HANDOFF_migracion_perfil_procesal.md (v5) y de
  HANDOFF_continuacion_perfil2_para_Claude_Code.md (auditoría de Cowork del 13/08)
destino: sesión de Claude Code en el perfil "tnm33"
---

# Handoff — Migración al perfil procesal: lo que queda por cerrar desde `tnm33`

**Andamio efímero, no fuente de verdad** (`GOBERNANZA_FUENTES_VERDAD §5`). Lo que sobreviva
se promueve a `PLAN.md`/`STATUS.md`; esto pasa a `consumido` cuando se cierre.

Lee primero los dos handoffs originales (adjuntos en `C:\Users\Nikolai Tyukhay 1\Downloads\`
y también en `C:\Users\Public\Documents\HANDOFF_migracion_perfil_procesal.md` — Nikolai
decidió dejarlo ahí de momento, no es urgente moverlo, pero está en una ruta legible por
cualquier cuenta de la máquina). Este fichero solo añade lo que pasó **hoy**, desde el
perfil procesal, con acceso real a shell — y los tres puntos que solo se pueden cerrar
desde aquí.

## 1. Estado antes de seguir: haz `git pull`

`main` está en `6e43ff0` tras tres PRs mergeados hoy desde el perfil procesal:

- **#220** — `fix(config): añadir "Nikolai Tyukhay (procesal)" a ACTORES_DESPACHO` (cierra F.4.2).
- **#221** — `fix(ui): resolver el actor por defecto del sidebar vía FEESDEFENDER_ACTOR` (cierra F.4.4).
- **#222** — `chore(claude): añadir launch.json para previsualizar Streamlit` (sin relación con la migración, solo dev-ex).

```powershell
cd C:\Users\tnm33\Dev\FeesDefender
git pull
git log --oneline -5   # debe mostrar 6e43ff0 en la punta
```

## 2. Los tres puntos que solo se cierran desde `tnm33`

### 2.1 F.4.1 — confirmar `$PROFILE` de `tnm33`

Comprobar que `$PROFILE` de esta sesión fija `FEESDEFENDER_ACTOR` explícito y con un valor
**distinto** al del perfil procesal ("Nikolai Tyukhay (procesal)"):

```powershell
notepad $PROFILE
# debe contener: $env:FEESDEFENDER_ACTOR = "Nikolai Tyukhay"
```

**Importante, hallazgo de hoy (ver §3):** esta variable en la práctica **no llega** a
procesos no interactivos (Bash tool, PowerShell tool de Claude Code, `run_app.bat` vía
`cmd.exe`) — solo se carga en una PowerShell interactiva abierta a mano que ejecute
`$PROFILE`. Fíjala igualmente (es lo correcto y barato), pero no la trates como la garantía
real de aislamiento: esa la da `os.getlogin()`, que ya funciona sin configurar nada.

### 2.2 E.6 — publicar el marketplace del plugin en git (D4, nunca ejecutado)

`known_marketplaces.json`/`settings.json` en el perfil procesal **siguen** con la entrada
`despacho-tyukhay` de tipo `directory` apuntando a `dist\plugin` (que no existe en ese
clon, porque `dist/` está en `.gitignore`). El plugin funciona hoy solo porque la caché de
`~\.claude\plugins\cache\...` viajó entera por el puente de migración — no por la vía
diseñada. La decisión D4 ("el marketplace se publica en git") sigue sin ejecutarse.

Pasos (documento original, Bloque E.6, líneas ~689-733):

1. **E.6.1** (aquí, en `tnm33`): decidir dónde se publica `dist/plugin` — ¿repo dedicado, o
   rama de distribución en este mismo repo con `dist/` desexcluido? Es una decisión de
   Nikolai, no la tomes tú. Antes de publicar, control bloqueante de secretos:
   ```powershell
   Get-ChildItem "C:\Users\tnm33\Dev\FeesDefender\dist\plugin" -Recurse -File -Force -Include *.json,*.py,*.bat,*.ps1,*.env,*.txt,*.md |
       Select-String -Pattern 'sk-ant-','client_secret','refresh_token','AIza','ghp_','password','tnm33' -SimpleMatch |
       Select-Object Path, LineNumber, @{n='Match';e={$_.Matches[0].Value}}
   ```
   Debe salir vacío. Ojo especial a `tnm33`: si el bundle lleva rutas de este perfil, no es portable.
2. **E.6.2** (en el perfil procesal, después de 1): `/plugin marketplace add <owner>/<repo>` +
   `/plugin install feesdefender@despacho-tyukhay`. Verificar que `expedientes-xl` y
   `email-export` siguen cargando.
3. **E.6.3** (en el perfil procesal): retirar la entrada `directory` huérfana con
   `/plugin marketplace remove` (no editando el JSON a mano). Debe quedar una sola entrada
   `despacho-tyukhay` y un solo `feesdefender` instalado.

### 2.3 E.1 — otros repos en `Dev\` de `tnm33`

Solo se migró `FeesDefender` al perfil procesal. Si hay otros repos en
`C:\Users\tnm33\Dev\` que también vayan a necesitar el perfil procesal, comprobar antes de
tocarlos que no quedan sucios ni sin `push` (script en el handoff original, Bloque E.1):

```powershell
Get-ChildItem "C:\Users\tnm33\Dev" -Directory -ErrorAction SilentlyContinue | ForEach-Object {
    $d = $_.FullName
    if (Test-Path (Join-Path $d ".git")) {
        [pscustomobject]@{
            Repo    = $_.Name
            Rama    = (git -C $d rev-parse --abbrev-ref HEAD 2>$null)
            Sucio   = [bool]((git -C $d status --porcelain 2>$null) | Select-Object -First 1)
            SinPush = (git -C $d log --oneline "@{u}..HEAD" 2>$null | Measure-Object).Count
        }
    }
} | Format-Table -AutoSize
```

## 3. Hallazgos de hoy que conviene tener en cuenta (no bloquean nada, pero informan)

- **`FEESDEFENDER_ACTOR` no discrimina en la práctica** — ver §2.1. Verificado en vivo con
  un checkout real de prueba sobre `VaRS3` (Valencia, W-02TH0W): el `_intake_log.jsonl` del
  caso registró `actor: "Nikolai Tyukhay 1"` (el login crudo de Windows), no
  `"Nikolai Tyukhay (procesal)"`. La discriminación real entre perfiles SÍ funciona (los
  valores difieren de los que dejó `tnm33` en julio en ese mismo log), pero vía
  `os.getlogin()`, no vía la variable de entorno. Checkout revertido y limpiado tras la
  prueba (`estado_repositorio: disponible`, sin rastro).
- **`rclone` no estaba instalado en el perfil procesal** (ni el handoff original ni la
  auditoría de Cowork lo comprobaron). Se instaló hoy con `winget install --id Rclone.Rclone
  --scope user` y se configuró el remote `gdrive_tl` (team_drive
  `0AAhcjDaZBWe6Uk9PVA`) vía OAuth. Si `tnm33` no lo tenía ya de antes por alguna razón,
  mismo patrón sirve ahí.
- **Aviso de rclone:** el `client_id` compartido por defecto de rclone se retira durante
  2026 — en algún momento conviene crear uno propio
  (https://rclone.org/drive/#making-your-own-client-id). No es bloqueante hoy; candidato a
  `docs/MEJORAS_FUTURAS.md`.
- **`reportlab` falta en `requirements.txt`** — rompe ~30 tests de OCR/PDF en cualquier
  `.venv` reconstruido desde cero (confirmado al montar el venv del perfil procesal). No se
  arregló, queda como deuda.
- **Un test sensible a la longitud del nombre de perfil:**
  `tests/test_migrar_nombres_informe.py::test_resumen_cuenta_por_estado` falla en el perfil
  procesal (assert de un contador "fuera_de_presupuesto") — probablemente por el nombre de
  cuenta más largo ("Nikolai Tyukhay 1" vs "tnm33"). No investigado a fondo.
- **`settings.json` usa `bypassPermissions`** heredado sin cambios de `tnm33` (confirmado
  comparando los backups `.premig`/`.premig2`) — no es un artefacto de la migración, es una
  decisión de confianza preexistente. Se le explicó a Nikolai; sigue sin tocar.
- **F.2 (montaje `G:`/`H:`) cerrado del todo hoy**, incluida la prueba de escritura
  (`H:` rechaza escritura, correcto). Hubo un incidente intermedio: al reasignar letras,
  quedó un proceso `GoogleDriveFS.exe` huérfano sirviendo `G:`/`H:` como "Disco local"
  fantasma tras una reasignación fallida — se resolvió con un reinicio completo de Windows.
  Si algo similar pasa en `tnm33` al tocar letras de unidad, mismo diagnóstico.
- **C.4.b cerrado**: hashes SHA-256 de `.credentials.json` confirmados distintos entre
  perfiles (procesal: `53DBE7FC...`; `tnm33`: `88D07C63...`).
- **F.1 cerrado**: `G:` y `H:` son dos cuentas de Google distintas
  (`nikolai.tyukhay@tyukhay.legal` / `nikolai.tyukhay@engelvoelkers`), no una cuenta con dos
  unidades compartidas.

## 4. Reglas duras que siguen sin excepción

`.credentials.json` nunca cruza entre perfiles · `FEESDEFENDER_ACTOR` con valores distintos
en cada perfil (hoy: procesal fijado; `tnm33` pendiente de confirmar en §2.1) · las
extensiones DXT (`gmail-multiaccount`, `google-despacho`) no migran · nunca el mismo
expediente abierto desde los dos perfiles a la vez · nunca el mismo repo trabajado sin
`push` entre sesión y sesión · ningún secreto por `C:\Users\Public`.
