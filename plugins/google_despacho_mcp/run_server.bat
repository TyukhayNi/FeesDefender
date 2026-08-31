@echo off
REM Wrapper de arranque del MCP google-despacho.
REM
REM REGLAS DE ORO (romperlas rompe el pipe JSON-RPC de MCP):
REM   * JAMAS redirigir NINGUN descriptor en la linea de python: ni 1> ni 2>>.
REM     Medido el 2026-08-31 con dos .bat identicos salvo el `2>>`: el que
REM     redirige stderr a fichero da CONNECTION_CLOSED en Claude Code y el
REM     server muere en `stdout.flush()` con OSError 22 sin haber recibido
REM     `initialize`; el que no redirige, conecta. Claude Desktop lo toleraba
REM     -de ahi que la regla vieja dijera "solo 2>>"-, Claude Code no. El
REM     stderr del server lo recoge el propio cliente.
REM   * JAMAS escribir a stdout (fd 1) desde el .bat.
REM   * JAMAS usar "timeout" (lee stdin y falla bajo pipe MCP); usar "ping -n".
REM   * JAMAS usar "start" ni "call": rompen la herencia de stdin/stdout.
REM   * python debe ser la ULTIMA linea y en primer plano, para heredar el pipe
REM     y para que el .bat viva tanto como el server.
setlocal

REM --- Interprete: el venv del repo, y NUNCA "cualquier python del PATH" -------
REM Este server usa la API 1.x del SDK (`mcp.server.fastmcp`). El 2026-08-23 un
REM `pip install --user mcp` sin pin trajo mcp 2.0.0 al site de usuario, que ya
REM no expone ese modulo: los tres conectores del despacho murieron a la vez y
REM en silencio porque el .bat resolvia el interprete por RUTA que existe, no
REM por CAPACIDAD de arrancar el server. Orden: env var, venv del repo, venv en
REM la ubicacion convencional del perfil. Sin fallback ciego al PATH.
set "PYEXE="
if defined FEESDEFENDER_PYTHON if exist "%FEESDEFENDER_PYTHON%" set "PYEXE=%FEESDEFENDER_PYTHON%"
if not defined PYEXE if exist "%~dp0..\..\.venv\Scripts\python.exe" set "PYEXE=%~dp0..\..\.venv\Scripts\python.exe"
if not defined PYEXE if exist "%USERPROFILE%\Dev\FeesDefender\.venv\Scripts\python.exe" set "PYEXE=%USERPROFILE%\Dev\FeesDefender\.venv\Scripts\python.exe"
if not defined PYEXE (
  echo [google-despacho] no encuentro el venv del repo; define FEESDEFENDER_PYTHON 1>&2
  exit /b 1
)

REM --- Verificar por CAPACIDAD, no por ruta ------------------------------------
"%PYEXE%" -c "import mcp.server.fastmcp" >NUL 2>NUL
if errorlevel 1 (
  echo [google-despacho] %PYEXE% no puede importar mcp.server.fastmcp: revisa que mcp sea 1.x 1>&2
  exit /b 1
)

"%PYEXE%" "%~dp0server.py"
