---
tipo: revision-adversarial
objeto: "diff de los wrappers de los cuatro conectores MCP del despacho"
objeto_rev: "rama claude/mcps-revision-bb6cf5, commit 0bb56db"
commit: 0bb56db
ronda: "1"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: k7pq
sha256_informe: 981c6602ee0fa118d1102d202bc1ac24de05114c75eb41729298ec6f87bd8c11
adjudicado_en: docs/superpowers/specs/2026-08-31-conectores-mcp-resolucion-por-capacidad-design.md §5
adjudicador: Claude Code
independencia_adjudicacion: restablecida
---

> **Acta de revisión adversarial R1.** El §1 conserva la voz del revisor sin una coma
> cambiada; la **adjudicación** vive en el **§5 del diseño**
> (`2026-08-31-conectores-mcp-resolucion-por-capacidad-design.md`). Es una ronda **sobre
> código**: el diff ya estaba escrito y commiteado, y el presupuesto de la pieza es de una
> sola ronda — no decide quién escribe sobre qué copia ni puede destruir datos de cliente.
>
> Veredicto **`NO-SHIP`**: **9 hallazgos** — 4 ALTOS, 4 MEDIOS, 1 BAJO. Adjudicados: **9
> confirmados, 0 refutados.**
>
> **Por qué el §1 archiva DOS textos del revisor.** El mandato que le pasé no pedía palabra
> de veredicto —error mío de proceso—, así que el informe no la traía. Se le pidió aparte,
> con instrucción expresa de **no reatacar el objeto ni tocar el informe**, y su addendum es
> el §5 del bloque literal. Comprobado que no lo tocó: el `sha256` de `INFORME.md` antes y
> después de esa segunda llamada es el mismo. Escribir yo un `NO-SHIP` que él no hubiera
> escrito habría vaciado el propósito de esta acta.
>
> **Esta ronda EJECUTÓ**, y de ahí salió lo que más duele: calculó resoluciones de ruta
> reales, corrió los dos módulos de test sobre una copia (20/20), lanzó probes de `cmd.exe`
> que demostraron el fallo del parser con `(x86)`, y cargó mi propio helper de test con
> `runpy` para pasarle contraejemplos — con los que tumbó tres de mis cinco guards.
>
> **Lo que no pudo correr lo declaró SIN VERIFICAR, no refutado:** no tenía el cliente de
> Claude Code, así que la causalidad del `CONNECTION_CLOSED` y el experimento A/B del `2>>`
> los sostiene la medición del autor, no esta acta.
>
> **Prueba de no-mutación:** los `sha256` de apertura y de cierre de los cuatro ficheros
> revisados coinciden (§0 del informe), y el objeto era una copia externa hecha con
> `git archive`, fuera del repo.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:k7pq -->

# Informe R1 — conectores MCP del despacho

## 0. Prueba de no-mutación

Los cuatro hashes coinciden entre apertura y cierre.

| Fichero bajo `../head/` | SHA-256 apertura | SHA-256 cierre |
|---|---|---|
| `plugins/expedientes_xl/run_server.bat` | `25a5538c7602a76f126a96a17d0f8a589b280112d9f50d175abfb69e7dea9a86` | `25a5538c7602a76f126a96a17d0f8a589b280112d9f50d175abfb69e7dea9a86` |
| `plugins/google_despacho_mcp/run_server.bat` | `c84d0c42ccacca8e6a0d582b069ffdb8043c2a48c27a87f301bb625f6a41a137` | `c84d0c42ccacca8e6a0d582b069ffdb8043c2a48c27a87f301bb625f6a41a137` |
| `plugins/email_export_mcp/run_server.bat` | `71e688baa2dca676786c38c183db375bd0f88fa3f3a0bb1cf33b24df46eb3336` | `71e688baa2dca676786c38c183db375bd0f88fa3f3a0bb1cf33b24df46eb3336` |
| `tests/test_mcp_wrappers.py` | `3f96c0d79eb3a6ed2dcdcd8c21ada74498a7538be4d08452c5aa6dd4c70812ca` | `3f96c0d79eb3a6ed2dcdcd8c21ada74498a7538be4d08452c5aa6dd4c70812ca` |

Comando de apertura y de cierre:

```powershell
$targets = @('plugins/expedientes_xl/run_server.bat','plugins/google_despacho_mcp/run_server.bat','plugins/email_export_mcp/run_server.bat','tests/test_mcp_wrappers.py'); foreach ($rel in $targets) { $p = Join-Path '..\head' $rel; $h = Get-FileHash -Algorithm SHA256 -LiteralPath $p; '{0}  {1}' -f $h.Hash.ToLowerInvariant(), $rel }
```

No se escribió en `../base/` ni en `../head/`. Para pytest se creó una copia transitoria `./_scratch_r1_head`, retirada al terminar. Al cierre, el workdir volvió a contener solo los dos ficheros preexistentes (`_stdout.txt`, `MANDATO.md`) antes de crear este informe.

## 1. Qué ejecuté

### 1.1 Inventario y lectura del diff

```powershell
git diff --no-index --name-status -- ..\base ..\head
```

Resultado: exactamente los 13 cambios declarados por el encargo (12 modificados y `tests/test_mcp_wrappers.py` añadido).

Para cada fichero tocado ejecuté la forma siguiente, variando `$rel`:

```powershell
git diff --no-index --unified=30 -- "..\base\$rel" "..\head\$rel"
$n=0; Get-Content -LiteralPath "..\head\$rel" | ForEach-Object { $n++; '{0,4}: {1}' -f $n,$_ }
```

Barrí configuraciones, manifiestos, documentación, specs y planes con:

```powershell
Get-ChildItem -LiteralPath '..\head' -Recurse -File -Include *.json,*.jsonc,*.toml,*.md,*.yaml,*.yml,*.bat,*.cmd |
  Select-String -Pattern 'mcpServers|mcp_config|run_server\.bat|server\.py|python\.exe|"command"\s*:\s*"python"|2>>' -CaseSensitive:$false
```

Resultado material: aparecieron los tres `dxt-build/manifest.json`, `requirements-dev.txt`, los README operativos y el wrapper Node jubilado que se detallan en los hallazgos.

### 1.2 Resolución de rutas y entornos

Calculé `GetFullPath($dp0 + '..\..\.venv\Scripts\python.exe')` para los cinco sitios. Resultado:

```text
repo/google -> <head>\.venv\Scripts\python.exe
repo/xl     -> <head>\.venv\Scripts\python.exe
repo/email  -> <head>\.venv\Scripts\python.exe
bundle/xl   -> <head>\dist\plugin\.venv\Scripts\python.exe
bundle/email-> <head>\dist\plugin\.venv\Scripts\python.exe
```

En los dos bundles, el marcador análogo `..\..\core\__init__.py` resuelve a `dist\plugin\core\__init__.py`, no a la raíz FeesDefender. La copia no contiene `dist/plugin`; `scripts/package_plugin.py:18-24,51-53` demuestra la topología que construye.

Comprobé existencias reales:

```text
../head/.venv/Scripts/python.exe                         False
../head/core/__init__.py                                 True
C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe True
C:\Users\tnm33\Dev\FeesDefender\core\__init__.py        True
```

Comprobé ambos intérpretes disponibles, con bytecode desactivado:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
& 'C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe' -c "import mcp.server.fastmcp,pytest; import importlib.metadata as md; print(md.version('mcp')); print(pytest.__version__)"
& 'C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe' -c "import mcp.server.fastmcp; import importlib.metadata as md; print(md.version('mcp'))"
```

Resultado: `mcp 1.29.1`, `pytest 9.1.1` en el primero; `mcp 1.28.1` en el venv. Ambos importaron `mcp.server.fastmcp`.

### 1.3 Pytest sobre copia, nunca sobre `head`

```powershell
Copy-Item -LiteralPath '..\head' -Destination '.\_scratch_r1_head' -Recurse -Force
Set-Location '.\_scratch_r1_head'
$env:PYTHONDONTWRITEBYTECODE='1'
& 'C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe' -m pytest tests/test_mcp_wrappers.py tests/test_expedientes_xl_wrapper.py -q -p no:cacheprovider --basetemp=C:/t/r1
```

Resultado del primer intento: `20 errors`, todos en setup por `PermissionError: [WinError 5]` al crear `C:\t\r1`. Es un límite del sandbox, no un fallo del objeto.

Repetición sobre la misma copia:

```powershell
& 'C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe' -m pytest tests/test_mcp_wrappers.py tests/test_expedientes_xl_wrapper.py -q -p no:cacheprovider --basetemp=.t
```

Resultado: `20 passed`, exit `0`. La ruta larga no afectó a estos dos módulos. La copia se retiró después; la comprobación final dio `removed=True`.

Comprobación de `pytest-randomly`:

```powershell
& 'C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe' -c "import importlib.util; print(importlib.util.find_spec('pytest_randomly'))"
```

Resultado: `None`. No ejecuté dos semillas; queda **SIN VERIFICAR**, aunque los tests atacados son esencialmente lecturas deterministas.

### 1.4 Probes de `cmd.exe`

Ámbito de redirección:

```cmd
"C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe" -c "import sys;print('PRE-OUT');print('PRE-ERR',file=sys.stderr)" >NUL 2>NUL
"C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe" -c "import sys;print('SERVER-OUT');print('SERVER-ERR',file=sys.stderr)"
```

Resultado: solo aparecieron `SERVER-OUT` y `SERVER-ERR`; exit `0`. La redirección del primer comando no persistió en el segundo.

Expansión de `%PYEXE%` dentro del bloque:

```powershell
$env:PYEXE='C:\Program Files (x86)\Python\python.exe'
cmd.exe /D /V:OFF /C 'ver >NUL & if errorlevel 1 (echo [probe] %PYEXE% no puede importar mcp.server.fastmcp 1>&2 & exit /b 7) & echo AFTER'
```

Resultado, pese a que `ver` dejó `errorlevel=0`: `No se esperaba \Python\python.exe en este momento.`, exit `1`. Con `C:\Plain\Python\python.exe` el parser no falló. Con `C:\A&B\...` el `&` se interpretó como separador cuando se tomó la rama de error.

### 1.5 Contraejemplos ejecutados contra los guards

Cargué `tests/test_mcp_wrappers.py` con `runpy.run_path` y llamé a `_linea_de_lanzamiento` sobre cuatro strings, sin escribir ficheros. Resultado:

```text
python ... 2>>log + "exit /b 0"       -> selecciona "exit /b 0"; guard verde
python ... 2>>log + ":: final"        -> selecciona ":: final"; guard verde
python ... 2>>log ^ + continuación     -> selecciona "--arg x"; guard verde
python limpio + "echo fin 1>&2"       -> selecciona el echo; guard rojo
```

Comprobé con `packaging`:

```powershell
& 'C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe' -c "from packaging.requirements import Requirement; from packaging.version import Version; specs=['mcp>=1.28','mcp>=1.0,<2','mcp>=1,<20','mcp>=1,<2.1']; [print(s,Version('2.0.0') in Requirement(s).specifier) for s in specs]"
```

Resultado: `mcp>=1.28`, `mcp>=1,<20` y `mcp>=1,<2.1` admiten `2.0.0`; `mcp>=1.0,<2` no.

### 1.6 Configuración viva local

Leí de forma dirigida, sin volcar secretos, los nombres y comandos MCP de `%USERPROFILE%\.claude.json`, `%APPDATA%\Claude\claude_desktop_config.json` y `%APPDATA%\Claude\extensions-installations.json`.

Resultados:

```text
Claude Code global: gmail-multiaccount -> C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe
Claude Code global: google-despacho    -> C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe
Claude Desktop raw: solo email-export
DXT instalado: gmail-multiaccount -> C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe
DXT instalado: expedientes-xl     -> el mismo pythoncore-3.14-64, `-m expedientes_xl.server`
```

No apareció una entrada viva `expedientes`/`expedientes_mcp` en esos registros conocidos.

No pude ejecutar el cliente de Claude Code ni reproducir `CONNECTION_CLOSED`; todo lo que depende de ese cliente queda marcado **SIN VERIFICAR**.

## 2. Hallazgos

### H1 — ALTO — el wrapper de `expedientes-xl` no encuentra intérprete en el bundle distribuido según sus propios prerrequisitos

**Fichero:línea:** `plugins/expedientes_xl/run_server.bat:52-60`; `plugin-src/.mcp.json:3-8`; `scripts/package_plugin.py:18-24,51-53`; `plugin-src/README.md:21-27,109-113`.

**Qué falla:** un compañero que instala el plugin con los prerrequisitos documentados para `expedientes-xl` —Python 3, `pip install mcp` y Drive— pero sin clonar FeesDefender no puede arrancar el conector desde el bundle.

**Por qué:** dentro de `dist/plugin/feesdefender/expedientes_xl/`, `%~dp0..\..\.venv` resuelve a `dist/plugin/.venv`, que el empaquetador no crea. El segundo fallback exige `%USERPROFILE%\Dev\FeesDefender\.venv`, aunque el README dice que solo `email-export` requiere el repo. Si `FEESDEFENDER_PYTHON` no está definida —el README tampoco manda definirla— el wrapper sale por `exit /b 1`. Un Python capaz en `PATH` no cuenta porque se retiró deliberadamente ese fallback.

**Cómo lo comprobé:** resolución con `GetFullPath`, lectura del ensamblador del bundle y contraste con los prerrequisitos publicados. Es un fallo determinista de selección, no una conjetura sobre Claude.

El mismo patrón da otro caso de “no encuentro”: desde un checkout/worktree de FeesDefender que tenga `core/` pero no `.venv`, `email-export` fija `FDROOT` a ese checkout y después exige *su* `.venv`; no llega al repo canónico aunque allí exista un venv. En el árbol de revisión se da exactamente esa topología (`head/core` existe, `head/.venv` no, el venv canónico sí existe). No lo elevo a otro ID porque preservar la pareja checkout/venv puede ser una decisión intencionada, pero contradice una lectura amplia del fallback “ubicación convencional”.

### H2 — ALTO — el venv preferido por los wrappers conserva una especificación que admite `mcp 2.0`

**Fichero:línea:** `requirements-dev.txt:1-5`; `tests/test_mcp_wrappers.py:96-109`; `plugins/google_despacho_mcp/run_server.bat:28-29`; `plugins/expedientes_xl/run_server.bat:54-55`; `plugins/email_export_mcp/run_server.bat:38-44`.

**Qué falla:** un `pip install -r requirements-dev.txt` fresco puede instalar `mcp 2.0` en precisamente el venv que los wrappers prefieren. Los wrappers entonces fallan ruidosamente en el preflight; no quedan operativos. Los pins añadidos bajo los requirements de cada conector no gobiernan esa instalación raíz.

**Por qué:** `requirements-dev.txt` sigue diciendo `mcp>=1.28`. `packaging` confirmó que `2.0.0` satisface esa spec. El guard solo itera `plugins/<conector>/requirements.txt`, por lo que queda verde y no ve la especificación raíz; además `email_export_mcp` no tiene `requirements.txt` propio y usa el venv del repo.

**Cómo lo comprobé:** lectura del glob del test y evaluación de las specs con `packaging`. El venv actual está sano (`mcp 1.28.1`), pero la instalación declarada sigue abierta a la misma causa.

### H3 — ALTO — superficies `.dxt` vivas siguen lanzando el intérprete por ruta, sin wrapper ni comprobación de capacidad

**Fichero:línea:** `plugins/expedientes_xl/dxt-build/manifest.json:10-25`; `plugins/gmail_mcp/dxt-build/manifest.json:10-18`; `plugins/google_despacho_mcp/dxt-build/manifest.json:10-18`; `plugins/expedientes_xl/dxt-build/README.md:1-18`; `tests/test_mcp_wrappers.py:39-44,96-109`.

**Qué falla:** la reparación por capacidad no cubre Cowork/Claude Desktop vía `.dxt`. Esas superficies siguen expuestas a que el Python absoluto tenga `mcp 2.x` o carezca de otra dependencia.

**Por qué:** los manifests ejecutan directamente `C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe`; ninguno pasa por `run_server.bat` ni ejecuta el preflight. Los guards solo recorren wrappers y requirements. La configuración instalada confirma que `expedientes-xl` y `gmail-multiaccount` están actualmente cableados así; el intérprete está sano hoy (`mcp 1.29.1`), pero la propiedad reparada no existe en esa vía. En otro perfil, la ruta absoluta ni siquiera existe.

**Cómo lo comprobé:** inspección de los tres manifests y lectura dirigida de `extensions-installations.json`. La conexión efectiva con Claude queda **SIN VERIFICAR**, pero el bypass del wrapper es inequívoco.

### H4 — MEDIO — `%PYEXE%` sin comillas dentro del bloque rompe el parser de `cmd` con rutas válidas que contengan paréntesis

**Fichero:línea:** `plugins/google_despacho_mcp/run_server.bat:37-40`; `plugins/expedientes_xl/run_server.bat:62-66`; `plugins/email_export_mcp/run_server.bat:45-48`; también `plugins/gmail_mcp/run_server.bat:26-29`.

**Qué falla:** una definición válida como `FEESDEFENDER_PYTHON=C:\Program Files (x86)\Python\python.exe` impide llegar a la línea del server, incluso si el preflight acaba con `errorlevel=0`.

**Por qué:** `cmd.exe` expande `%PYEXE%` al parsear el bloque entero. El `)` de `(x86)` se interpreta como cierre del bloque porque la expansión aparece sin comillas en el `echo`. Un `&` en la ruta se interpreta como separador de comandos en la rama de error.

**Cómo lo comprobé:** probe real con `cmd.exe /D /V:OFF`; con `errorlevel=0` y la ruta `(x86)` devolvió `No se esperaba \Python\python.exe en este momento`, exit `1`, antes de `AFTER`. Con una ruta sin metacaracteres, no falló. Las invocaciones de Python sí están entrecomilladas; el defecto es el `echo` expandido dentro del bloque.

### H5 — MEDIO — `FEESDEFENDER_PYTHON` desacopla el Python de la raíz seleccionada para `email-export`

**Fichero:línea:** `plugins/email_export_mcp/run_server.bat:24-27,38-50`; `plugins/email_export_mcp/server.py:25-34,49-53,106-112`.

**Qué falla:** el wrapper puede cargar `core/` del repo A bajo el entorno/dependencias del repo B. El preflight solo prueba `mcp.server.fastmcp`, de modo que no detecta incompatibilidades de las dependencias reales de `core.email_export`.

**Por qué:** `FDROOT` se resuelve primero e independientemente. Después `FEESDEFENDER_PYTHON`, si existe, sobreescribe `%FDROOT%\.venv\...`; finalmente `--repo-root "%FDROOT%"` inserta A en `sys.path`. No existe una comprobación de que el Python pertenezca a A ni una importación de `core.email_export` en el preflight.

**Cómo lo comprobé:** con `FEESDEFENDER_ROOT=<head>` y `FEESDEFENDER_PYTHON=C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe`, las mismas reglas del batch seleccionaron literalmente esas dos rutas distintas; ese Python pasó el import de MCP. El fallo concreto por version skew queda **SIN VERIFICAR** porque los dos checkouts actuales son compatibles, pero la mezcla que preguntaba el mandato sí es real y no se detecta.

### H6 — MEDIO — el guard de “línea de lanzamiento” puede dar verde falso y rojo falso

**Fichero:línea:** `tests/test_mcp_wrappers.py:47-67`.

**Qué falla:** el test no garantiza que la línea que lanza el server carezca de redirección.

**Por qué:** `_linea_de_lanzamiento` toma la última línea física no vacía que no empiece exactamente por `REM`. No entiende flujo batch, continuaciones `^`, `@REM`, comentarios `::`, labels, `endlocal`, `exit /b` ni comandos de limpieza posteriores. Después solo busca el carácter literal `>` en esa línea física.

**Cómo lo comprobé:** ejecuté el helper real. Estos wrappers defectuosos quedaron verdes:

```bat
"%PYEXE%" server.py 2>>log
exit /b 0
```

```bat
"%PYEXE%" server.py 2>>log ^
  --arg x
```

También quedó verde con `:: comentario final`. A la inversa, un lanzamiento limpio seguido de `echo fin 1>&2` dio rojo porque el helper examinó el `echo`, no el lanzamiento. Además, una redirección real por `<`, un pipe `|` o una redirección introducida mediante `%REDIR%` no necesita contener `>` literalmente en la línea examinada; un `^>` literal legítimo sería prohibido aunque no sea redirección para ese nivel de `cmd`.

### H7 — MEDIO — los guards de intérprete y pin comprueban subcadenas, no las propiedades afirmadas

**Fichero:línea:** `tests/test_mcp_wrappers.py:70-109`; `tests/test_expedientes_xl_wrapper.py:50-72`.

**Qué falla:** wrappers sin preflight real o con fallback ciego y requirements que admiten 2.0 pueden pasar.

**Por qué y contraejemplos comprobados:**

- La “capacidad” solo exige que `import mcp.server.fastmcp` aparezca en cualquier lugar. Un `REM import mcp.server.fastmcp` satisface ambos tests aunque nunca se ejecute.
- El fallback solo veta las cadenas `where python` y el patrón exacto `set "PYEXE=python"`. Pasan `set PYEXE=python.exe`, `set "PYEXE=py -3"` y `for %%I in (python.exe) do set "PYEXE=%%~$PATH:I"`.
- El pin solo exige la subcadena `<2`. `mcp>=1,<20` y `mcp>=1,<2.1` pasan y `packaging` confirmó que admiten `2.0.0`. `MCP>=1,<2` se ignora por comparación case-sensitive pese a que los nombres de distribución son case-insensitive.

**Cómo lo comprobé:** evaluación directa de las expresiones regulares del test y de los specifiers con `packaging`.

### H8 — ALTO — documentación operativa vigente reinstala las vías que el diff intenta cerrar

**Fichero:línea:** `plugin-src/README.md:13-17,21-27,63-69,73-103,109-113`; `plugins/expedientes_xl/README.md:19-33`; `plugins/google_despacho_mcp/README.md:41-55`; `docs/DESPLIEGUE_MCP_DRIVE_DISCO.md:1-5,17-30,107-122,130-136`.

**Qué falla:** seguir la documentación puede registrar `expedientes-xl` y `email-export` como `command: "python"` directo a `server.py`, instalar `mcp` sin techo o intentar una vía Cowork que el propio árbol declara inoperante.

**Por qué:** `plugin-src/README.md` manda para Cowork una entrada cruda `mcpServers` con Python pelado, mientras `docs/DEAD_ENDS.md:167-171` dice que esa vía no llega a Cowork. El snippet salta el wrapper nuevo y, para `email-export`, vuelve a omitir `--repo-root`. Los README de `expedientes-xl` y `google-despacho` conservan invocaciones directas. El documento de despliegue, marcado `estado: vigente`, todavía afirma que el wrapper usa `python "%SRV%"` y propone rollback a `server.py` directo o al Node jubilado.

**Cómo lo comprobé:** barrido de textos operativos y contraste interno contra `.mcp.json`, los wrappers actuales y las dos entradas nuevas de `DEAD_ENDS`. No depende del cliente.

### H9 — BAJO — `DEAD_ENDS` atribuye a PATH un wrapper que en `base` estaba cableado a una ruta absoluta

**Fichero:línea:** `docs/DEAD_ENDS.md:204-209`; `../base/plugins/google_despacho_mcp/run_server.bat:5`; `../base/plugins/expedientes_xl/run_server.bat:44-47`; `../base/plugins/email_export_mcp/run_server.bat:13-17`.

**Qué falla:** la afirmación “los tres conectores que resolvían el intérprete por PATH (`google-despacho`, `expedientes-xl`, `email-export`)" no describe el objeto anterior.

**Por qué:** `google-despacho` ejecutaba directamente `C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe`. `expedientes-xl` y `email-export` sí probaban `%LOCALAPPDATA%\Python\bin` y después `where python`; Google no resolvía por PATH. La ruta absoluta podía recibir el `mcp --user` defectuoso, pero ese es otro mecanismo.

**Cómo lo comprobé:** diff directo base/head. El resto de la frase —fecha de instalación, muerte simultánea y contenido histórico del log— queda **SIN VERIFICAR**, no refutado.

## 3. Lo que ataqué y NO cayó

### Resolución normal en la máquina canónica

- En el árbol del repo, `%~dp0..\..` resuelve correctamente a la raíz del repo para los tres wrappers.
- En el bundle, `expedientes-xl` no encuentra un venv relativo, pero en esta máquina concreta sí lo cubre el fallback `%USERPROFILE%\Dev\FeesDefender\.venv`.
- En el bundle, `email-export` no confunde `dist/plugin` con el repo: no encuentra allí `core/__init__.py`, cae a la raíz canónica y deriva de ella el venv. Sin `FEESDEFENDER_PYTHON`, raíz y Python quedan emparejados.
- `google-despacho` no forma parte del plugin `feesdefender`; su segunda superficie es el `.dxt`, tratada en H3, no `dist/plugin/feesdefender`.

### Sintaxis batch que sí resistió

- `if defined X if exist "%X%"`, el `setlocal`, las comillas de las invocaciones finales y `if errorlevel 1` son válidos para rutas sin metacaracteres. No encontré expansión diferida necesaria en el bucle de `TRIES`: el bloque se vuelve a parsear en cada iteración y el incremento ocurre fuera del bloque.
- Las cuatro líneas finales Python de `head` están en primer plano y no contienen redirección.
- El defecto sintáctico localizado es la expansión sin comillas dentro de los `echo` de H4, no el anidamiento de `if` en sí.

### El preflight redirigido no heredó su redirección al server

No cayó la hipótesis de que `"%PYEXE%" -c ... >NUL 2>NUL` rompa por sí misma el pipe del comando siguiente. En `cmd`, la redirección pertenece a ese comando/proceso; el probe mostró que stdout y stderr del segundo Python siguieron visibles. Esto no reproduce Claude, pero sí decide la semántica de `cmd`: el preflight no altera persistentemente los handles del lanzamiento posterior.

### El test reescrito y `WindowsApps`

El nuevo `test_wrapper_bat_no_lanza_un_interprete_sin_verificar` no pierde una propiedad real que el viejo cerrara. El viejo solo exigía la subcadena `WindowsApps`, que también podía vivir en un comentario y no probaba resolución. Conceptualmente, exigir `%PYEXE%`, preflight de capacidad y ausencia de fallback PATH subsume el caso del stub y amplía la intención a otros intérpretes incapaces.

Sí es verdad que el test nuevo **aislado** ya no exige ni siquiera aquella mención y que la suite combinada sigue siendo sintácticamente burlable (H7). Por tanto: no es más débil en intención, pero tampoco demuestra la subsunción que proclama.

### `expedientes_mcp` jubilado

El wrapper Node conserva `2>>` en su línea final (`plugins/expedientes_mcp/run_server.bat:81`), pero no lo convierto en hallazgo de runtime. `plugin-src/.mcp.json` no lo declara; la configuración local de Claude Code no lo declara; `claude_desktop_config.json` solo tiene `email-export`; y `extensions-installations.json` contiene `expedientes-xl`, no el server Node. `plugins/expedientes_mcp/config_ejemplo.json` sigue incluyéndolo, pero se presenta como copia histórica y la documentación de despliegue registra su retirada. No encontré una config viva que lo lance.

### Afirmaciones de `DEAD_ENDS` que sí tienen apoyo

- Las cuatro implementaciones Python importan `from mcp.server.fastmcp import FastMCP`.
- En `base`, las líneas finales de google, XL, email y gmail tenían `2>>`; en `head`, las activas ya no.
- Los tres requirements de conector cambiaron a specs reales `<2`, que `packaging` confirmó que excluyen 2.0.
- La configuración viva de Claude Code confirma que `gmail-multiaccount` apunta al venv del repo, tal como afirma la segunda entrada. No confundirla con el `.dxt` de Gmail, que usa el Python de usuario.
- La corrección de `email-export` en `.mcp.json` sí es material: ahora pasa por el wrapper, resuelve raíz y añade `--repo-root`.

## 4. Cobertura ausente

- **Claude Code / handshake MCP:** no está instalado el cliente. No pude reproducir `CONNECTION_CLOSED`, `stdout.flush() -> OSError 22`, ausencia de `initialize` ni el experimento A/B con y sin `2>>`. Toda esa causalidad histórica queda **SIN VERIFICAR**, no refutada.
- **Histórico del 23/31 de agosto:** las copias no contienen los logs ni el historial de `pip`. No verifiqué las fechas, la simultaneidad de las tres caídas ni el comando exacto de reparación.
- **Contenido de `mcp 2.0.0`:** el entorno solo conserva 1.29.1/1.28.1. Verifiqué que el objeto depende de `mcp.server.fastmcp` y que sus specs abiertas admiten 2.0, pero no ejecuté una instalación 2.0 ni confirmé desde esa distribución la retirada del módulo.
- **Dos semillas:** `pytest-randomly` no está instalado (`find_spec -> None`).
- **Suite completa:** ejecuté solo `tests/test_mcp_wrappers.py` y `tests/test_expedientes_xl_wrapper.py` sobre copia: 20/20. No atribuí al objeto el primer fallo de `C:\t\r1`, que fue del sandbox.
- **Build/instalación real:** no reconstruí `dist/plugin`, no reinstalé plugins ni `.dxt` y no muté configs. Inspeccioné el ensamblador y las configuraciones ya instaladas en modo lectura.
- **Otros equipos/perfiles:** el fallo de portabilidad de H1 se deriva del contrato y de rutas; no pude ejecutar en los PCs de otros compañeros.
- **Efecto final del desacoplamiento de H5:** probé la selección cruzada y el preflight, pero no provoqué una incompatibilidad real entre dos revisiones distintas de `core`/venv.

## 5. Veredicto (addendum solicitado tras el informe)

NO-SHIP

Los cuatro hallazgos ALTOS muestran que el objeto conserva fallos materiales de arranque, instalación y cobertura en superficies vivas, además de documentación operativa que reinstala las vías que el diff pretende cerrar. No corresponde `REQUIERE-REVISION` porque el informe no deja solo incertidumbres que deban volverse a mirar: acredita defectos deterministas por los que el objeto no debe entrar como está.

<!-- informe-literal:fin:k7pq -->

## 2. Evidencia verificada por el adjudicador

Cada hallazgo se contrastó **contra la fuente**, no contra el informe. Lo que reproduje yo,
con el comando y su resultado:

- **H6 (verdes falsos del guard).** Cargué mi propio helper con `runpy.run_path` y le pasé los
  cuatro contraejemplos del revisor. Confirmado: `python … 2>>log` + `exit /b 0` → el helper
  elige `exit /b 0` y el guard pasa **verde**; con `:: fin` detrás, igual; y un lanzamiento
  **limpio** seguido de `echo fin 1>&2` daba **rojo**. Tres de los cuatro casos eran defectos
  reales invisibles para mi guard.
- **H7 (pin por subcadena).** `packaging`: `mcp>=1,<20` y `mcp>=1,<2.1` contienen `<2` y
  **admiten 2.0.0**; `mcp>=1.28` no contiene `<2` y también la admite. El guard viejo pasaba
  verde sobre los tres.
- **H1 (resolución en el bundle).** Probe de `cmd` que imprime qué candidatos existen desde
  cada ubicación: desde `dist/plugin/feesdefender/expedientes_xl/`, `..\..\.venv` **no
  existe** y `..\..\core\__init__.py` tampoco. Contrastado con `plugin-src/README.md`, que
  publica el conector como auto-contenido.
- **H2 (requirements de la raíz).** `requirements-dev.txt:5` decía `mcp>=1.28`; el glob del
  guard era `plugins/*/requirements.txt`, así que no lo miraba.
- **H9 (frase de DEAD_ENDS).** Diff base/head de los tres wrappers: `google-despacho`
  arrancaba `...\pythoncore-3.14-64\python.exe` **cableado**, no por PATH. Mi frase era falsa.
- **H3 (.dxt).** Los tres `dxt-build/manifest.json` cablean el mismo intérprete absoluto, que
  es el que se envenenó. Ya lo había detectado antes del informe y está en
  `MEJORAS_FUTURAS.md` #125.

Después de remediar: **7 mutantes contra los guards reescritos, 7 muertos**, más un control
negativo que verifica que no reaparecen rojos falsos; handshake `initialize` real contra los
cuatro wrappers; y `claude mcp list` con los cuatro conectores `Connected`.

## 3. Coste de la ronda

Nueve hallazgos, todos confirmados, y **tres de ellos eran defectos que introduje al
remediar** (H1, H6, H7). Es la cuarta medición de mi propio modo de fallo —cerrar el caso del
informe en vez de la propiedad de la que es ejemplo— y la primera en la que el remedio de la
propiedad fue *ampliar* lo permitido (devolver el PATH como candidato probado) en vez de
restringirlo. Prohibir es la forma cómoda de parecer que se ha cerrado una frontera.

El `NO-SHIP` es correcto sobre el objeto que revisó, y por eso el commit `0bb56db` no se
mergeó tal cual: lo que entra es el árbol remediado, con su verificación en el §5 del diseño.
