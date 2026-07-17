@echo off
REM ===========================================================================
REM  expedientes-xl consolidado - wrapper de arranque (poll-until-mount)
REM ---------------------------------------------------------------------------
REM  Espera el montaje de G: (Drive Tyukhay) Y H: (Drive E&V) antes de arrancar
REM  el server consolidado. Mismo patron y mismas REGLAS DE ORO que
REM  plugins/expedientes_mcp/run_server.bat (leer ese fichero para el detalle
REM  del problema que resuelve el poll-until-mount).
REM
REM  REGLAS DE ORO (no romper al editar; rompen el pipe JSON-RPC de MCP):
REM    * JAMAS escribir a stdout (fd 1). Todo diagnostico -> fd 2 (1>&2) o al LOG.
REM    * JAMAS redirigir 1> en la linea final de python (solo 2>>).
REM    * JAMAS usar "timeout": lee stdin y falla bajo pipe MCP
REM      ("Input redirection is not supported"). Usar "ping -n" (no toca stdin).
REM    * JAMAS usar "start" ni "call": crean proceso/consola nueva y rompen la
REM      herencia de stdin/stdout que Claude Desktop conecta al pipe MCP.
REM    * python debe ser la ULTIMA linea (primer plano) para heredar el pipe y
REM      para que el .bat viva tanto como el server.
REM ===========================================================================
REM expedientes-xl consolidado - espera el montaje de G: y H: antes de arrancar.
REM Reglas de oro: ver plugins/expedientes_mcp/run_server.bat (mismo patron).
setlocal
set "PROBE_G=G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\CASOS"
set "PROBE_H=H:\Unidades compartidas"
set "SRV=%~dp0server.py"
set "LOG=%APPDATA%\Claude\logs\mcp-server-expedientes-xl-wrapper.log"
if not exist "%APPDATA%\Claude\logs" mkdir "%APPDATA%\Claude\logs" 2>NUL
set /a TRIES=0
set /a MAXTRIES=25
:waitloop
if exist "%PROBE_G%\" if exist "%PROBE_H%\" goto ready
set /a TRIES+=1
if %TRIES% GEQ %MAXTRIES% (
  echo [xl-wrapper] TIMEOUT: G:/H: no montaron tras ~50s>>"%LOG%"
  echo [xl-wrapper] TIMEOUT: G:/H: no montaron - abre Google Drive y reinicia 1>&2
  exit /b 1
)
ping -n 3 127.0.0.1 >NUL
goto waitloop
:ready
echo [xl-wrapper] montadas; arrancando server consolidado>>"%LOG%"
python "%SRV%" --rw "G:\" --ro "H:\" 2>>"%LOG%"
