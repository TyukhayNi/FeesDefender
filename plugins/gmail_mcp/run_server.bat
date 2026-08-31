@echo off
REM Wrapper de arranque del MCP gmail-multiaccount.
REM
REM REGLAS DE ORO (romperlas rompe el pipe JSON-RPC de MCP):
REM   * JAMAS redirigir NINGUN descriptor en la linea de python: ni 1> ni 2>>.
REM     Medido el 2026-08-31 con dos .bat identicos salvo el `2>>`: el que
REM     redirige stderr a fichero da CONNECTION_CLOSED en Claude Code; el que no
REM     redirige, conecta. Este conector se libro del apagon de agosto solo
REM     porque su entrada en la config de Claude Code lanza python directamente
REM     y no pasa por este .bat. El stderr lo recoge el cliente.
REM   * JAMAS escribir a stdout (fd 1) desde el .bat.
REM   * python debe ser la ULTIMA linea, en primer plano.
setlocal

REM --- Interprete: el venv del repo, y NUNCA "cualquier python del PATH" -------
REM Este server usa la API 1.x del SDK (`mcp.server.fastmcp`), que mcp 2.0 retiro.
set "PYEXE="
if defined FEESDEFENDER_PYTHON if exist "%FEESDEFENDER_PYTHON%" set "PYEXE=%FEESDEFENDER_PYTHON%"
if not defined PYEXE if exist "%~dp0..\..\.venv\Scripts\python.exe" set "PYEXE=%~dp0..\..\.venv\Scripts\python.exe"
if not defined PYEXE if exist "%USERPROFILE%\Dev\FeesDefender\.venv\Scripts\python.exe" set "PYEXE=%USERPROFILE%\Dev\FeesDefender\.venv\Scripts\python.exe"
if not defined PYEXE (
  echo [gmail-multiaccount] no encuentro el venv del repo; define FEESDEFENDER_PYTHON 1>&2
  exit /b 1
)
"%PYEXE%" -c "import mcp.server.fastmcp" >NUL 2>NUL
if errorlevel 1 (
  echo [gmail-multiaccount] %PYEXE% no puede importar mcp.server.fastmcp: revisa que mcp sea 1.x 1>&2
  exit /b 1
)

"%PYEXE%" "%~dp0server.py"
