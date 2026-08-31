@echo off
REM ===========================================================================
REM  expedientes-xl consolidado - wrapper de arranque (poll-until-mount)
REM ---------------------------------------------------------------------------
REM  Espera el montaje de G: (Drive Tyukhay) Y H: (Drive E&V) antes de arrancar.
REM
REM  REGLAS DE ORO (no romper al editar; rompen el pipe JSON-RPC de MCP):
REM    * JAMAS redirigir NINGUN descriptor en la linea que lanza el server: ni
REM      1> ni 2>>. Medido el 2026-08-31 con dos .bat identicos salvo el `2>>`:
REM      el que redirige stderr a fichero da CONNECTION_CLOSED en Claude Code y
REM      el server muere en `stdout.flush()` con OSError 22 sin haber recibido
REM      `initialize`; el que no redirige, conecta. Claude Desktop lo toleraba
REM      -de ahi la regla vieja "solo 2>>"-, Claude Code no. El stderr del server
REM      lo recoge el cliente. Las lineas ANTERIORES si pueden redirigir al LOG:
REM      en cmd la redireccion pertenece al comando, no a la sesion.
REM    * La linea del interprete debe ser la ULTIMA ejecutable y en primer plano,
REM      para heredar el pipe y para que el .bat viva tanto como el server. Nada
REM      detras: ni `exit /b`, ni `::`, ni limpieza.
REM    * JAMAS escribir a stdout (fd 1) desde el .bat.
REM    * JAMAS usar "timeout": lee stdin y falla bajo pipe MCP
REM      ("Input redirection is not supported"). Usar "ping -n" (no toca stdin).
REM    * JAMAS usar "start": crea consola nueva y rompe la herencia de stdio.
REM ===========================================================================
setlocal enabledelayedexpansion
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
echo [xl-wrapper] montadas; resolviendo interprete>>"%LOG%"
set "PYTHONPATH=%~dp0..;%PYTHONPATH%"

REM --- El interprete se ELIGE POR CAPACIDAD, no por ruta ----------------------
REM Este server usa la API 1.x del SDK (`mcp.server.fastmcp`). El 2026-08-23 un
REM `pip install --user mcp` sin pin trajo mcp 2.0.0, que retiro ese modulo, y
REM tres conectores murieron a la vez y en silencio: el wrapper elegia el
REM interprete por RUTA QUE EXISTE y lanzaba uno que arranca y muere.
REM
REM La primera version de este arreglo (2026-08-31) PROHIBIA el PATH. Eso cerraba
REM el ejemplo, no la frontera, y rompio de paso el caso documentado del README
REM del plugin -este conector se anuncia "auto-contenido: Python 3 + pip install
REM mcp", sin clonar el repo, y desde el bundle `..\..\.venv` no existe-. La
REM frontera es "no lanzar lo que no se ha comprobado", asi que el PATH vuelve a
REM ser candidato: lo que no vuelve es aceptarlo sin probarlo. El stub de la
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
  echo [xl-wrapper] ningun interprete puede importar mcp.server.fastmcp>>"%LOG%"
  echo [xl-wrapper] ningun interprete de Python puede importar mcp.server.fastmcp. 1>&2
  echo [xl-wrapper] Instala `mcp^>=1.0,^<2` -la 2.0 retiro ese modulo- o apunta 1>&2
  echo [xl-wrapper] FEESDEFENDER_PYTHON a un interprete que lo tenga. 1>&2
  exit /b 1
)
echo [xl-wrapper] arrancando server consolidado>>"%LOG%"

"%PYEXE%" -m expedientes_xl.server --rw G:\ --ro H:\
