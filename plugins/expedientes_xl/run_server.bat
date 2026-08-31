@echo off
REM ===========================================================================
REM  expedientes-xl consolidado - wrapper de arranque (poll-until-mount)
REM ---------------------------------------------------------------------------
REM  Espera el montaje de G: (Drive Tyukhay) Y H: (Drive E&V) antes de arrancar
REM  el server consolidado.
REM
REM  REGLAS DE ORO (no romper al editar; rompen el pipe JSON-RPC de MCP):
REM    * JAMAS redirigir NINGUN descriptor en la linea de python: ni 1> ni 2>>.
REM      Medido el 2026-08-31 con dos .bat identicos salvo el `2>>`: el que
REM      redirige stderr a fichero da CONNECTION_CLOSED en Claude Code y el
REM      server muere en `stdout.flush()` con OSError 22 sin haber recibido
REM      `initialize`; el que no redirige, conecta. Claude Desktop lo toleraba
REM      -de ahi la regla vieja "solo 2>>"-, Claude Code no. El stderr del
REM      server lo recoge el cliente; al LOG solo va el diagnostico del propio
REM      wrapper, y siempre en lineas ANTERIORES a la de python.
REM    * JAMAS escribir a stdout (fd 1) desde el .bat.
REM    * JAMAS usar "timeout": lee stdin y falla bajo pipe MCP
REM      ("Input redirection is not supported"). Usar "ping -n" (no toca stdin).
REM    * JAMAS usar "start" ni "call": crean proceso/consola nueva y rompen la
REM      herencia de stdin/stdout que el cliente conecta al pipe MCP.
REM    * python debe ser la ULTIMA linea (primer plano) para heredar el pipe y
REM      para que el .bat viva tanto como el server.
REM ===========================================================================
setlocal
set "PROBE_G=G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\CASOS"
set "PROBE_H=H:\Unidades compartidas"
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
set "PYTHONPATH=%~dp0..;%PYTHONPATH%"

REM --- Interprete: el venv del repo, y NUNCA "cualquier python del PATH" -------
REM Este server usa la API 1.x del SDK (`mcp.server.fastmcp`). El 2026-08-23 un
REM `pip install --user mcp` sin pin trajo mcp 2.0.0 al site de usuario, que ya
REM no expone ese modulo: los tres conectores del despacho murieron a la vez y
REM en silencio porque el .bat resolvia el interprete por RUTA que existe, no
REM por CAPACIDAD de arrancar el server. Sin fallback ciego al PATH.
set "PYEXE="
if defined FEESDEFENDER_PYTHON if exist "%FEESDEFENDER_PYTHON%" set "PYEXE=%FEESDEFENDER_PYTHON%"
if not defined PYEXE if exist "%~dp0..\..\.venv\Scripts\python.exe" set "PYEXE=%~dp0..\..\.venv\Scripts\python.exe"
if not defined PYEXE if exist "%USERPROFILE%\Dev\FeesDefender\.venv\Scripts\python.exe" set "PYEXE=%USERPROFILE%\Dev\FeesDefender\.venv\Scripts\python.exe"
if not defined PYEXE (
  echo [xl-wrapper] no encuentro el venv del repo; define FEESDEFENDER_PYTHON>>"%LOG%"
  echo [xl-wrapper] no encuentro el venv del repo; define FEESDEFENDER_PYTHON 1>&2
  exit /b 1
)
"%PYEXE%" -c "import mcp.server.fastmcp" >NUL 2>NUL
if errorlevel 1 (
  echo [xl-wrapper] %PYEXE% no puede importar mcp.server.fastmcp: revisa que mcp sea 1.x>>"%LOG%"
  echo [xl-wrapper] %PYEXE% no puede importar mcp.server.fastmcp: revisa que mcp sea 1.x 1>&2
  exit /b 1
)

"%PYEXE%" -m expedientes_xl.server --rw G:\ --ro H:\
