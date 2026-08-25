@echo off
REM Resolver un Python REAL y PORTABLE.
REM   * El stub de la Microsoft Store (WindowsApps) aborta el server MCP.
REM   * Una ruta ABSOLUTA ataba el plugin a un perfil de Windows concreto: es la
REM     bomba A.6-ter del handoff de migracion, que se parcheo en la copia del
REM     perfil destino y NO en esta fuente, asi que cada build la reproducia.
REM Reglas de oro (romperlas rompe el pipe JSON-RPC de MCP):
REM   * JAMAS escribir a stdout (fd 1). Diagnostico -> fd 2 o al LOG.
REM   * JAMAS redirigir 1> en la linea de python (solo 2>>).
REM   * python debe ser la ULTIMA linea, en primer plano, para heredar el pipe.
setlocal
set "LOG=%APPDATA%\Claude\email-export-mcp.log"
set "PYEXE="
if exist "%LOCALAPPDATA%\Python\bin\python.exe" set "PYEXE=%LOCALAPPDATA%\Python\bin\python.exe"
if not defined PYEXE for /f "delims=" %%p in ('where python 2^>nul ^| findstr /v /i "WindowsApps"') do if not defined PYEXE set "PYEXE=%%p"
if not defined PYEXE set "PYEXE=python"
"%PYEXE%" "%~dp0server.py" 2>>"%LOG%"
