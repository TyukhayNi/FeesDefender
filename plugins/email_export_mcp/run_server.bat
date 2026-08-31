@echo off
REM Wrapper de arranque del MCP email-export.
REM
REM A diferencia de expedientes-xl, este server NO es auto-contenido: importa
REM `core/` del repo. Cuando corre desde el bundle del plugin
REM (dist/plugin/feesdefender/) su deteccion automatica de la raiz apunta DENTRO
REM del bundle, donde no hay `core/`, y muere con ModuleNotFoundError antes de
REM contestar `initialize`. Por eso aqui se resuelve la raiz explicitamente y se
REM pasa con --repo-root.
REM
REM REGLAS DE ORO (romperlas rompe el pipe JSON-RPC de MCP):
REM   * JAMAS redirigir NINGUN descriptor en la linea de python: ni 1> ni 2>>.
REM     Medido el 2026-08-31 con dos .bat identicos salvo el `2>>`: el que
REM     redirige stderr a fichero da CONNECTION_CLOSED en Claude Code; el que no
REM     redirige, conecta. El stderr del server lo recoge el cliente.
REM   * JAMAS escribir a stdout (fd 1) desde el .bat.
REM   * python debe ser la ULTIMA linea, en primer plano.
setlocal

REM --- Raiz del repo: es un REQUISITO de este server, no un extra -------------
REM Marcador: core\__init__.py. Nada de rutas absolutas de un perfil concreto
REM (la bomba A.6-ter del handoff de migracion): env var, arbol del repo, o la
REM ubicacion convencional bajo %USERPROFILE%.
set "FDROOT="
if defined FEESDEFENDER_ROOT if exist "%FEESDEFENDER_ROOT%\core\__init__.py" set "FDROOT=%FEESDEFENDER_ROOT%"
if not defined FDROOT if exist "%~dp0..\..\core\__init__.py" set "FDROOT=%~dp0..\.."
if not defined FDROOT if exist "%USERPROFILE%\Dev\FeesDefender\core\__init__.py" set "FDROOT=%USERPROFILE%\Dev\FeesDefender"
if not defined FDROOT (
  echo [email-export] no encuentro la raiz del repo; define FEESDEFENDER_ROOT 1>&2
  exit /b 1
)

REM --- Interprete: el venv de esa raiz, y NUNCA "cualquier python del PATH" ----
REM Este server usa la API 1.x del SDK (`mcp.server.fastmcp`). El 2026-08-23 un
REM `pip install --user mcp` sin pin trajo mcp 2.0.0 al site de usuario, que ya
REM no expone ese modulo. Ademas el `command: "python"` del .mcp.json cogia el
REM primer python del PATH, que ni tiene el venv ni garantiza las deps.
set "PYEXE=%FDROOT%\.venv\Scripts\python.exe"
if defined FEESDEFENDER_PYTHON if exist "%FEESDEFENDER_PYTHON%" set "PYEXE=%FEESDEFENDER_PYTHON%"
if not exist "%PYEXE%" (
  echo [email-export] no existe el interprete %PYEXE% 1>&2
  exit /b 1
)
"%PYEXE%" -c "import mcp.server.fastmcp" >NUL 2>NUL
if errorlevel 1 (
  echo [email-export] %PYEXE% no puede importar mcp.server.fastmcp: revisa que mcp sea 1.x 1>&2
  exit /b 1
)

"%PYEXE%" "%~dp0server.py" --repo-root "%FDROOT%"
