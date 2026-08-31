@echo off
REM Wrapper de arranque del MCP google-despacho.
REM
REM REGLAS DE ORO (romperlas rompe el pipe JSON-RPC de MCP):
REM   * JAMAS redirigir NINGUN descriptor en la linea que lanza el server: ni 1>
REM     ni 2>>. Medido el 2026-08-31 con dos .bat identicos salvo el `2>>`: el que
REM     redirige stderr a fichero da CONNECTION_CLOSED en Claude Code y el server
REM     muere en `stdout.flush()` con OSError 22 sin haber recibido `initialize`;
REM     el que no redirige, conecta. Claude Desktop lo toleraba -de ahi la regla
REM     vieja "solo 2>>"-, Claude Code no. El stderr lo recoge el cliente.
REM     Las lineas ANTERIORES si pueden redirigir: en cmd la redireccion pertenece
REM     al comando, no a la sesion (comprobado con un probe de dos comandos).
REM   * La linea del interprete debe ser la ULTIMA ejecutable y en primer plano,
REM     para heredar el pipe y para que el .bat viva tanto como el server. Nada
REM     detras: ni `exit /b`, ni `::`, ni limpieza.
REM   * JAMAS escribir a stdout (fd 1) desde el .bat.
REM   * JAMAS usar "timeout" (lee stdin y falla bajo pipe MCP); usar "ping -n".
REM   * JAMAS usar "start": crea consola nueva y rompe la herencia de stdio.
setlocal enabledelayedexpansion

REM --- El interprete se ELIGE POR CAPACIDAD, no por ruta ----------------------
REM Este server usa la API 1.x del SDK (`mcp.server.fastmcp`). El 2026-08-23 un
REM `pip install --user mcp` sin pin trajo mcp 2.0.0, que retiro ese modulo, y
REM tres conectores murieron a la vez y en silencio: el wrapper elegia el
REM interprete por RUTA QUE EXISTE y lanzaba uno que arranca y muere.
REM
REM La primera version de este arreglo (2026-08-31) PROHIBIA el PATH. Eso cerraba
REM el ejemplo, no la frontera, y rompio de paso el caso documentado del README
REM del plugin -"auto-contenido: Python 3 + pip install mcp", sin clonar el repo-.
REM La frontera es "no lanzar lo que no se ha comprobado", asi que el PATH vuelve
REM a ser candidato: lo que no vuelve es aceptarlo sin probarlo. El stub de la
REM Microsoft Store cae por si solo al no pasar la prueba, sin nombrarlo.
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
  echo [google-despacho] ningun interprete de Python puede importar mcp.server.fastmcp. 1>&2
  echo [google-despacho] Instala `mcp^>=1.0,^<2` -la 2.0 retiro ese modulo- o apunta 1>&2
  echo [google-despacho] FEESDEFENDER_PYTHON a un interprete que lo tenga. 1>&2
  exit /b 1
)

"%PYEXE%" "%~dp0server.py"
