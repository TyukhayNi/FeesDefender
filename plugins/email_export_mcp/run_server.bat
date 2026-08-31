@echo off
REM Wrapper de arranque del MCP email-export.
REM
REM A diferencia de expedientes-xl, este server NO es auto-contenido: importa
REM `core/` del repo. Cuando corre desde el bundle del plugin
REM (dist/plugin/feesdefender/) su deteccion automatica de la raiz apunta DENTRO
REM del bundle, donde no hay `core/`, y muere con ModuleNotFoundError antes de
REM contestar `initialize`. Por eso aqui la raiz se resuelve explicitamente y se
REM pasa con --repo-root.
REM
REM REGLAS DE ORO (romperlas rompe el pipe JSON-RPC de MCP):
REM   * JAMAS redirigir NINGUN descriptor en la linea que lanza el server: ni 1>
REM     ni 2>>. Medido el 2026-08-31 con dos .bat identicos salvo el `2>>`: el que
REM     redirige stderr a fichero da CONNECTION_CLOSED en Claude Code; el que no
REM     redirige, conecta. El stderr del server lo recoge el cliente. Las lineas
REM     ANTERIORES si pueden redirigir: en cmd la redireccion pertenece al
REM     comando, no a la sesion.
REM   * La linea del interprete debe ser la ULTIMA ejecutable y en primer plano.
REM     Nada detras: ni `exit /b`, ni `::`, ni limpieza.
REM   * JAMAS escribir a stdout (fd 1) desde el .bat.
setlocal enabledelayedexpansion

REM --- Raiz del repo: es un REQUISITO de este server, no un extra -------------
REM Marcador: core\__init__.py. Nada de rutas absolutas de un perfil concreto
REM (la bomba A.6-ter del handoff de migracion): env var, arbol del repo, o la
REM ubicacion convencional bajo %USERPROFILE%.
set "FDROOT="
if defined FEESDEFENDER_ROOT if exist "%FEESDEFENDER_ROOT%\core\__init__.py" set "FDROOT=%FEESDEFENDER_ROOT%"
if not defined FDROOT if exist "%~dp0..\..\core\__init__.py" set "FDROOT=%~dp0..\.."
if not defined FDROOT if exist "%USERPROFILE%\Dev\FeesDefender\core\__init__.py" set "FDROOT=%USERPROFILE%\Dev\FeesDefender"
if not defined FDROOT (
  echo [email-export] no encuentro la raiz del repo; define FEESDEFENDER_ROOT. 1>&2
  exit /b 1
)

REM --- El interprete se ELIGE POR CAPACIDAD, y la capacidad AQUI incluye core --
REM Este server usa la API 1.x del SDK (`mcp.server.fastmcp`), que mcp 2.0
REM retiro, y ADEMAS necesita importar `core.email_export` con la raiz elegida.
REM Por eso la prueba importa las dos cosas y no solo mcp: asi un interprete que
REM tenga mcp pero no las dependencias de `core` no pasa, y sobre todo NO puede
REM colarse la pareja incoherente "python del repo A, --repo-root del repo B" que
REM el desacoplamiento de FEESDEFENDER_PYTHON permitia en silencio. La prueba es
REM la MISMA importacion que hace el server al arrancar, no un proxy de ella.
REM
REM `!VAR!` y no `%VAR%` dentro de los bloques a proposito: con expansion en
REM tiempo de parseo, una ruta legitima como `C:\Program Files (x86)\...` rompe
REM el parser de cmd al cerrar el bloque en su `)`.
set "SONDA=import sys; sys.path.insert(0, sys.argv[1]); import mcp.server.fastmcp; import core.email_export"
set "PYEXE="
set "CAND=%FEESDEFENDER_PYTHON%"
if not defined PYEXE if defined CAND if exist "!CAND!" (
  "!CAND!" -c "!SONDA!" "!FDROOT!" >NUL 2>NUL
  if not errorlevel 1 set "PYEXE=!CAND!"
)
set "CAND=%FDROOT%\.venv\Scripts\python.exe"
if not defined PYEXE if exist "!CAND!" (
  "!CAND!" -c "!SONDA!" "!FDROOT!" >NUL 2>NUL
  if not errorlevel 1 set "PYEXE=!CAND!"
)
set "CAND=%USERPROFILE%\Dev\FeesDefender\.venv\Scripts\python.exe"
if not defined PYEXE if exist "!CAND!" (
  "!CAND!" -c "!SONDA!" "!FDROOT!" >NUL 2>NUL
  if not errorlevel 1 set "PYEXE=!CAND!"
)
if not defined PYEXE for /f "delims=" %%p in ('where python 2^>nul') do if not defined PYEXE (
  set "CAND=%%p"
  "!CAND!" -c "!SONDA!" "!FDROOT!" >NUL 2>NUL
  if not errorlevel 1 set "PYEXE=!CAND!"
)
if not defined PYEXE (
  echo [email-export] ningun interprete puede importar a la vez mcp.server.fastmcp 1>&2
  echo [email-export] y core.email_export con la raiz "!FDROOT!". Revisa que mcp sea 1>&2
  echo [email-export] `mcp^>=1.0,^<2`, que el venv de esa raiz tenga las deps de 1>&2
  echo [email-export] core, o apunta FEESDEFENDER_PYTHON a un interprete que valga. 1>&2
  exit /b 1
)

"%PYEXE%" "%~dp0server.py" --repo-root "%FDROOT%"
