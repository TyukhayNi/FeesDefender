@echo off
REM Wrapper de arranque del MCP gmail-multiaccount.
REM
REM REGLAS DE ORO (romperlas rompe el pipe JSON-RPC de MCP):
REM   * JAMAS redirigir NINGUN descriptor en la linea que lanza el server: ni 1>
REM     ni 2>>. Medido el 2026-08-31 con dos .bat identicos salvo el `2>>`: el que
REM     redirige stderr a fichero da CONNECTION_CLOSED en Claude Code; el que no
REM     redirige, conecta. Este conector se libro del apagon de agosto solo porque
REM     su entrada en la config de Claude Code lanza python directamente y no pasa
REM     por este .bat. El stderr lo recoge el cliente.
REM   * La linea del interprete debe ser la ULTIMA ejecutable y en primer plano.
REM     Nada detras: ni `exit /b`, ni `::`, ni limpieza.
REM   * JAMAS escribir a stdout (fd 1) desde el .bat.
setlocal enabledelayedexpansion

REM --- El interprete se ELIGE POR CAPACIDAD, no por ruta ----------------------
REM Este server usa la API 1.x del SDK (`mcp.server.fastmcp`), que mcp 2.0 retiro.
REM Se prueba cada candidato y se toma el primero que la importa; el PATH es
REM candidato legitimo, lo que no es legitimo es aceptarlo sin probarlo (el stub
REM de la Microsoft Store cae por si solo, sin nombrarlo).
REM
REM `!VAR!` y no `%VAR%` dentro de los bloques a proposito: con expansion en
REM tiempo de parseo, una ruta legitima como `C:\Program Files (x86)\...` rompe
REM el parser de cmd al cerrar el bloque en su `)`.
set "PYEXE="
set "CAND=%FEESDEFENDER_PYTHON%"
if not defined PYEXE if defined CAND if exist "!CAND!" (
  "!CAND!" -c "import mcp.server.fastmcp" >NUL 2>NUL
  if not errorlevel 1 set "PYEXE=!CAND!"
)
set "CAND=%~dp0..\..\.venv\Scripts\python.exe"
if not defined PYEXE if exist "!CAND!" (
  "!CAND!" -c "import mcp.server.fastmcp" >NUL 2>NUL
  if not errorlevel 1 set "PYEXE=!CAND!"
)
set "CAND=%USERPROFILE%\Dev\FeesDefender\.venv\Scripts\python.exe"
if not defined PYEXE if exist "!CAND!" (
  "!CAND!" -c "import mcp.server.fastmcp" >NUL 2>NUL
  if not errorlevel 1 set "PYEXE=!CAND!"
)
set "CAND=%LOCALAPPDATA%\Python\bin\python.exe"
if not defined PYEXE if exist "!CAND!" (
  "!CAND!" -c "import mcp.server.fastmcp" >NUL 2>NUL
  if not errorlevel 1 set "PYEXE=!CAND!"
)
if not defined PYEXE for /f "delims=" %%p in ('where python 2^>nul') do if not defined PYEXE (
  set "CAND=%%p"
  "!CAND!" -c "import mcp.server.fastmcp" >NUL 2>NUL
  if not errorlevel 1 set "PYEXE=!CAND!"
)
if not defined PYEXE (
  echo [gmail-multiaccount] ningun interprete de Python puede importar 1>&2
  echo [gmail-multiaccount] mcp.server.fastmcp. Instala `mcp^>=1.2.0,^<2` -la 2.0 1>&2
  echo [gmail-multiaccount] retiro ese modulo- o apunta FEESDEFENDER_PYTHON a uno 1>&2
  echo [gmail-multiaccount] que lo tenga. 1>&2
  exit /b 1
)

"%PYEXE%" "%~dp0server.py"
