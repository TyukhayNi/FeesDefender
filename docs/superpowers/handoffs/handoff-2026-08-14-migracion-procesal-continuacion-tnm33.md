---
tipo: handoff
estado: activo
creado: 2026-08-14
origen: sesión de Claude Code en el perfil "Nikolai Tyukhay 1" (procesal@tyukhay.legal) —
  continuación de HANDOFF_migracion_perfil_procesal.md (v5) y de
  HANDOFF_continuacion_perfil2_para_Claude_Code.md (auditoría de Cowork del 13/08)
destino: sesión de Claude Code en el perfil "tnm33" y, desde el 2026-08-25, también en el
  perfil "Nikolai Tyukhay 1" (procesal@tyukhay.legal) — ver §5: dos de las acciones que
  quedan solo se pueden ejecutar desde ese perfil
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

> **Estado al 2026-08-25, medido desde `tnm33`: de los tres queda uno.** 2.1 ✅ y 2.3 ✅ (detalle
> en cada apartado). **2.2 (E.6 / D4) sigue abierto y es el único punto vivo de toda la
> migración**, así que sale del andamio y pasa a `PLAN.md` como fila #16 —
> `[SIGUIENTE-MARKETPLACE-PLUGIN]`—, según el §5 de `docs/GOBERNANZA_FUENTES_VERDAD.md`. Este
> fichero **no** pasa a `consumido` todavía: los hallazgos del §3 siguen siendo su única sede.

### 2.1 F.4.1 — `$PROFILE` de `tnm33`: ⚠️ CONFIGURADO, pero el defecto que venía a cerrar sigue VIVO

> **Errata de la misma jornada.** Este apartado se marcó `✅ CERRADO` el 2026-08-25 y **el `✅` era
> engañoso**, corregido horas después el mismo día. La comprobación que pedía F.4.1 —¿está fijada la
> variable?— sí pasa. Lo que **no** pasa es el defecto que fijarla debía corregir. Un punto se cierra
> cuando su *efecto* está cerrado, no cuando su *comando* se ejecutó.

**Lo que sí está hecho:** `C:\Users\tnm33\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1`
(13/08/2026 19:41) fija `$env:FEESDEFENDER_ACTOR = "Nikolai Tyukhay"` y define la función
`claude-procesal`. Valor distinto del perfil procesal, como exige la regla 5-bis.

**Lo que sigue roto, medido el 2026-08-25 ejecutando el código, no leyendo la config:**

```
_default_actor()     = 'tnm33'
in ACTORES_DESPACHO  = False
```

Es **literalmente** el defecto que el F.4.1 del runbook v5 decía corregir: «*hoy cualquier evento
lanzado desde CLI registra `actor = "tnm33"`, un nombre de cuenta de Windows que no está en
`ACTORES_DESPACHO`*». Sigue así, porque el `$PROFILE` solo se carga en una PowerShell 5.1
interactiva y los procesos que registran eventos no pasan por ahí: en la sesión de Claude Code la
variable sale **vacía**, ni en el proceso ni a nivel de usuario
(`[Environment]::GetEnvironmentVariable('FEESDEFENDER_ACTOR','User')`). El «conjunto cerrado para
que el log forense quede limpio de typos» sigue incumpliéndose en **esta** cuenta cada vez que un
evento nace del CLI.

**El remedio, que alcanza a los procesos no interactivos** (pendiente, es config de Windows y la
ejecuta Nikolai):

```powershell
[Environment]::SetEnvironmentVariable('FEESDEFENDER_ACTOR','Nikolai Tyukhay','User')
```

Dos avisos: **no afecta a una sesión ya lanzada** —Claude Code no hereda variables puestas después
de arrancar, así que hay que reabrir— y el valor **debe seguir siendo distinto** del de `procesal@`
(«Nikolai Tyukhay (procesal)»), porque la variable tiene **precedencia sobre `os.getlogin()`** y el
mismo valor en los dos destruiría la discriminación del lock y del log. Mientras no se aplique, lo
que discrimina de verdad es `os.getlogin()` — que funciona, pero devuelve un valor fuera de la tupla.

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

### 2.2 E.6 — publicar el marketplace del plugin en git (D4, nunca ejecutado) — ⏩ PROMOVIDO

> **Promovido a `PLAN.md` fila #16 el 2026-08-25** (`[SIGUIENTE-MARKETPLACE-PLUGIN]`). Verificado
> ese día que el defecto sigue vivo **también en `tnm33`**, no solo en el perfil procesal:
> `~\.claude\plugins\known_marketplaces.json` y el `extraKnownMarketplaces` de
> `~\.claude\settings.json` mantienen `despacho-tyukhay` de tipo `directory` apuntando a
> `Dev\FeesDefender\dist\plugin` (`lastUpdated: 2026-07-20`). Lo que sigue debajo es el
> procedimiento; el bloque de `PLAN.md` lleva el disparador y la decisión pendiente.

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

### 2.3 E.1 — otros repos en `Dev\` de `tnm33` ✅ CERRADO (2026-08-25)

**Censo ejecutado, sin bloqueo:** cuatro repos —`ElContable`, `FeesDefender`, `FeesDefender-crm`,
`MCP-BOE`—, los cuatro en `main`, `Sucio=False` y `SinPush=0`. Ninguno impide clonar al perfil
procesal si en algún momento lo necesita (D2: el perfil 2 clona del remoto, `Dev\` no se mueve).
El script sigue abajo por si hay que repetirlo.

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
  `docs/MEJORAS_FUTURAS.md`. **✅ ESCRITO el 2026-08-25 como `MEJORAS #122`**, y al medirlo
  cambió de forma: los dos remotes de `tnm33` **ya tienen `client_id` propio**, así que la
  exposición se reduce al `gdrive_tl` de este perfil — cuyo `rclone.conf` no es legible desde
  `tnm33`, de modo que **la comprobación que decide si hay algo que arreglar solo se puede
  hacer desde aquí**, y es una línea. La fuente además no lo plantea como consejo sino como
  obligación con plazo. Detalle en la entrada.
- ~~**`reportlab` falta en `requirements.txt`**~~ — **enunciado CORREGIDO el 2026-08-25 desde
  `tnm33`: la dependencia no falta.** Está declarada en `requirements-dev.txt:7` (`reportlab>=4.0`)
  desde el 2026-07-09 (`1144a30`). Lo que falla es el **procedimiento de montaje**: el E.4 del
  handoff v5 (`C:\Users\Public\Documents\HANDOFF_migracion_perfil_procesal.md`, línea 667) instala
  solo `requirements.txt`, así que el venv del perfil procesal se quedó sin las dependencias de
  desarrollo. **Remedio, en el perfil procesal:**
  `python -m pip install -r requirements-dev.txt` — nada que añadir al repo, y **no** añadir
  `reportlab` a `requirements.txt`, que es de runtime.
  **Radio medido** (no estimado): bloqueando el módulo por `PYTHONPATH` sobre los 4 ficheros de
  test que lo importan, **37 de 59 tests caen** — `test_ocr_escalera` 13, `test_pdf_paginas` 5,
  `test_sala_maquina_ejecutar` 13, `test_sala_maquina_escalera` 6; con `reportlab` presente, 0
  fallos y 1 `skip` de `--runslow`. El «~30» era buena estimación; lo falso era la causa, y creerla
  habría llevado a duplicar la línea en el fichero equivocado.
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
en cada perfil (**fijada en los dos `$PROFILE`** —procesal el 13/08, `tnm33` confirmado el
2026-08-25— pero **sin efecto sobre los procesos que registran eventos**: en `tnm33` el actor
sigue saliendo `'tnm33'`, fuera de la tupla. Ver §2.1) · las
extensiones DXT (`gmail-multiaccount`, `google-despacho`) no migran · nunca el mismo
expediente abierto desde los dos perfiles a la vez · nunca el mismo repo trabajado sin
`push` entre sesión y sesión · ningún secreto por `C:\Users\Public`.

---

## 5. Lo que queda, y en qué perfil se hace (añadido el 2026-08-25)

**Este apartado existe porque faltaba.** Al cerrar la sesión del 2026-08-25 se comprobó que una
sesión abierta en el perfil `procesal@` **no tenía por dónde retomar**: `STATUS.md` no menciona
nada de ese perfil, `MEJORAS #122` es backlog que nadie lee al abrir, y este fichero declaraba
`destino: tnm33`, así que una sesión de allí lo lee como dirigido a la otra — justo donde vivían
las dos acciones que solo ella puede ejecutar.

### En el perfil `Nikolai Tyukhay 1` (procesal@) — dos acciones, ninguna bloqueada

1. **Devolver los tests que allí caen.** `python -m pip install -r requirements-dev.txt` en el
   venv de ese perfil. Son **37 tests de 59** en los 4 ficheros que fabrican PDFs con capa de
   texto (radio medido el 2026-08-25, ver §3). No toca el repo: el venv se montó solo con
   `requirements.txt`.
2. **La comprobación que decide `MEJORAS #122`.** Ver si el `client_id` del remote `gdrive_tl`
   está vacío; si lo está, usa el compartido de rclone, que **deja de funcionar durante 2026**.
   Es una línea, y **solo se puede hacer desde ahí** (`rclone.conf` de ese perfil no es legible
   desde `tnm33`). Al comprobarlo: **nunca volcar la configuración completa** —expone el
   `client_secret`—, solo mirar si el campo está vacío. Si lo está, el remedio no es crear un
   `client_id` nuevo sino reutilizar el proyecto que ya sostiene los dos remotes de `tnm33`.

### En `tnm33` — una decisión y una línea de config

1. **E.6.1: dónde se publica el marketplace del plugin** (repo dedicado, o rama de distribución en
   este repo con `dist/` desexcluido). Es lo único que bloquea `PLAN.md` **#16**; los pasos E.6.2 y
   E.6.3 son mecánicos después, y el **E.6.3 hay que hacerlo en los dos perfiles**, porque la
   entrada `directory` huérfana está en ambos (verificado el 2026-08-25 en `tnm33`:
   `known_marketplaces.json` y `settings.json`).
2. **Fijar `FEESDEFENDER_ACTOR` a nivel de Usuario**, no solo en el `$PROFILE` — ver §2.1. Sin eso,
   el log forense de esta cuenta sigue registrando `actor = 'tnm33'`, **fuera de
   `ACTORES_DESPACHO`**. Es una línea, y es el único defecto de la migración que sigue vivo.

### Lo ya cerrado, para que nadie lo repita

E.1 ✅ (§2.3, censo del 2026-08-25) · E.6 ⏩ promovido a `PLAN.md` #16 · el aviso del `client_id` ✅
escrito como `MEJORAS #122` · el enunciado de `reportlab` ✅ corregido aquí, en
`requirements-dev.txt` y en `docs/INDICE.md`.

**F.4.1 NO está en esta lista a propósito.** Se marcó `✅` el 2026-08-25 y el `✅` era engañoso: la
variable está fijada y el defecto que fijarla debía cerrar sigue vivo. Detalle y remedio en §2.1.

