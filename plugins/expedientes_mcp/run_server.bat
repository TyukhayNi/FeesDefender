@echo off
REM ===========================================================================
REM  expedientes MCP - wrapper de arranque (poll-until-mount)
REM ---------------------------------------------------------------------------
REM  PROBLEMA QUE RESUELVE:
REM    @modelcontextprotocol/server-filesystem valida su directorio permitido
REM    AL ARRANCAR con fs.stat + process.exit(1) (fail-fast). Google Drive for
REM    Desktop monta G: de forma ASINCRONA tras el login (~3-14 s). Si Claude
REM    lanza el server antes de que G: exista -> ENOENT -> exit -> "failed", y
REM    Claude Desktop NO reinicia servers stdio caidos en la sesion.
REM    Este wrapper NO lanza node hasta que G: este montado y poblado.
REM
REM  REGLAS DE ORO (no romper al editar; rompen el pipe JSON-RPC de MCP):
REM    * JAMAS escribir a stdout (fd 1). Todo diagnostico -> fd 2 (1>&2) o al LOG.
REM    * JAMAS redirigir NINGUN descriptor en la linea final de node.
REM      OJO: esta linea decia "jamas 1>, solo 2>>" y ESO ERA LA TRAMPA.
REM      Medido el 2026-08-31 en los conectores Python: con `2>>fichero` en la
REM      linea del interprete, Claude Code da CONNECTION_CLOSED (Claude Desktop
REM      lo toleraba). Este server Node esta JUBILADO -lo sustituyo
REM      expedientes_xl-, asi que no se toca su codigo; pero NO copies de aqui
REM      la regla vieja: la buena esta en plugins/expedientes_xl/run_server.bat
REM      y en docs/DEAD_ENDS.md.
REM    * JAMAS usar "timeout": lee stdin y falla bajo pipe MCP
REM      ("Input redirection is not supported"). Usar "ping -n" (no toca stdin).
REM    * JAMAS usar "start" ni "call": crean proceso/consola nueva y rompen la
REM      herencia de stdin/stdout que Claude Desktop conecta al pipe MCP.
REM    * node debe ser la ULTIMA linea (primer plano) para heredar el pipe y
REM      para que el .bat viva tanto como el server.
REM
REM  MANTENIMIENTO: si se reinstala node-portable a otra version, editar las
REM    dos variables NODE y SRV de abajo (unico punto de cambio).
REM ===========================================================================
setlocal

set "TARGET=G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL"
set "PROBE=G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\CASOS"
set "NODE=C:\Users\tnm33\node-portable\node-v24.16.0-win-x64\node.exe"
set "SRV=C:\Users\tnm33\node-portable\node-v24.16.0-win-x64\node_modules\@modelcontextprotocol\server-filesystem\dist\index.js"
set "LOG=%APPDATA%\Claude\logs\mcp-server-expedientes-wrapper.log"

REM -- Asegurar carpeta de log (perfil nuevo / primera ejecucion) --
if not exist "%APPDATA%\Claude\logs" mkdir "%APPDATA%\Claude\logs" 2>NUL

REM -- Guarda: rutas de node y del server (fallo diagnosticable, no "no se reconoce") --
if not exist "%NODE%" (
  echo [expedientes-wrapper] ERROR: node.exe no encontrado en "%NODE%" - revisa la version de node-portable>>"%LOG%"
  echo [expedientes-wrapper] ERROR: node.exe no encontrado en "%NODE%" 1>&2
  exit /b 2
)
if not exist "%SRV%" (
  echo [expedientes-wrapper] ERROR: server-filesystem no encontrado en "%SRV%">>"%LOG%"
  echo [expedientes-wrapper] ERROR: server-filesystem no encontrado en "%SRV%" 1>&2
  exit /b 2
)

REM -- Espera al montaje de G:. MAXTRIES*~2s DEBE quedar POR DEBAJO del timeout de
REM    handshake del cliente MCP (60 s), para que el abort legible GANE la carrera.
REM    25 ciclos * ~2s = ~50 s < 60 s. Holgura ~3,5x sobre el peor montaje visto (14,35 s).
set /a TRIES=0
set /a MAXTRIES=25

echo [expedientes-wrapper] %DATE% %TIME% arranque; esperando montaje de G:>>"%LOG%"

:waitloop
REM Comprobar la HOJA poblada del arbol (\CASOS), no solo la letra: evita el
REM falso positivo de un montaje Dokan parcial (letra creada, arbol aun vacio).
if exist "%PROBE%\" goto ready
if exist "%TARGET%\" if exist "%PROBE%" goto ready
set /a TRIES+=1
if %TRIES% GEQ %MAXTRIES% (
  echo [expedientes-wrapper] TIMEOUT: G: no monto tras %MAXTRIES% intentos ^(~50s^). Ruta: "%TARGET%". Abre Google Drive, espera a ver G:, y reinicia Claude Desktop.>>"%LOG%"
  echo [expedientes-wrapper] TIMEOUT: G: no monto tras ~50s - abre Google Drive y reinicia Claude Desktop 1>&2
  exit /b 1
)
echo [expedientes-wrapper] esperando G: intento %TRIES%/%MAXTRIES%...>>"%LOG%"
ping -n 3 127.0.0.1 >NUL
goto waitloop

:ready
echo [expedientes-wrapper] G: montado; lanzando server-filesystem>>"%LOG%"
"%NODE%" "%SRV%" "%TARGET%" 2>>"%LOG%"
