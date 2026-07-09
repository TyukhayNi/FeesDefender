@echo off
chcp 65001 >nul
setlocal
set "REMOTE=__REMOTE__"
set "LOCAL=__LOCAL__"
set "TS=__TS__"
cd /d "C:\Users\tnm33\_checkout___WCODE__"

echo [1/3] Copia Drive a local (excluye protocolo + notas personales)...
rclone copy "%REMOTE%" "%LOCAL%" --checksum --drive-skip-shortcuts --transfers 4 ^
  --exclude "desktop.ini" --exclude "90_Notas personales/**" ^
  --exclude "_caso.md" --exclude "_intake_log.jsonl" ^
  --exclude "MANIFEST_CHECKOUT.json" --exclude "AUDITLOG_MERGE_*.jsonl" ^
  --exclude "_snapshot/**" --exclude "_pendiente_checkin/**" ^
  --log-level INFO --log-file "checkout_%TS%.log"
if errorlevel 1 goto :fail

echo [2/3] Inventario local para el baseline (ruta + hash MD5)...
rem  Vuelca lsjson a fichero (Claude lo reforma a MANIFEST_CHECKOUT.json y lo sube al Drive).
rclone lsjson "%LOCAL%" -R --hash --files-only ^
  --exclude "desktop.ini" --exclude "90_Notas personales/**" > "inventario_%TS%.json"

echo [3/3] Verificacion por hash (Drive contra local, solo lo copiado)...
rclone check "%REMOTE%" "%LOCAL%" --one-way --drive-skip-shortcuts --fast-list ^
  --exclude "desktop.ini" --exclude "90_Notas personales/**" ^
  --exclude "_caso.md" --exclude "_intake_log.jsonl" ^
  --exclude "MANIFEST_CHECKOUT.json" --exclude "AUDITLOG_MERGE_*.jsonl" ^
  --exclude "_snapshot/**" --exclude "_pendiente_checkin/**" ^
  --log-level INFO --log-file "check_%TS%.log"
if errorlevel 1 goto :revisar

echo.
echo ============================================
echo  VERDE: caso copiado a local y verificado por hash.
echo  Falta (lo hace Claude): reformar inventario_%TS%.json a
echo  MANIFEST_CHECKOUT.json, subirlo al Drive y registrar case_checkout.
echo ============================================
goto :fin

:revisar
echo.
echo ============================================
echo  AMARILLO: copia hecha pero la verificacion encontro diferencias.
echo  Revisa con Claude: check_%TS%.log  (NO empieces a trabajar aun)
echo ============================================
goto :fin

:fail
echo.
echo ============================================
echo  ROJO: fallo en la copia Drive a local.
echo  Revisa con Claude: checkout_%TS%.log
echo  El lock del Drive debe revertirse a 'disponible' (checkout no completado).
echo ============================================

:fin
endlocal
