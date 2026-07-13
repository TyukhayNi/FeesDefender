@echo off
REM Wrapper de arranque del MCP gmail-multiaccount para Claude Desktop.
REM stdout (fd1) queda para el pipe JSON-RPC de MCP; stderr al log.
REM Si el interprete no esta en esta ruta, editar la linea de abajo.
C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe "%~dp0server.py" 2>>"%APPDATA%\Claude\gmail-multiaccount-mcp.log"
