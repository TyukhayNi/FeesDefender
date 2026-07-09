@echo off
chcp 65001 >nul
setlocal
set "LOCAL=__LOCAL__"
set "REMOTE=__REMOTE__"
set "TS=__TS__"
cd /d "C:\Users\tnm33\_merge___WCODE__"

echo [1/5] Copia local a Drive (lo sobrescrito se aparta a respaldo, nada se pierde)...
rclone copy "%LOCAL%" "%REMOTE%" --checksum --drive-skip-shortcuts --transfers 4 ^
  --exclude "desktop.ini" --exclude "90_Notas personales/**" ^
  --exclude "_caso.md" --exclude "_intake_log.jsonl" ^
  --exclude "MANIFEST_CHECKOUT.json" --exclude "AUDITLOG_MERGE_*.jsonl" ^
  --exclude "_snapshot/**" --exclude "_pendiente_checkin/**" ^
  --backup-dir "gdrive_tl:_merge_backups/__WCODE___%TS%" ^
  --log-level INFO --log-file "auditlog_merge_%TS%.log"
if errorlevel 1 goto :fail

echo [2/5] Ficheros de protocolo (solo si no existen ya en Drive)...
rclone copy "%LOCAL%\00_Input" "%REMOTE%/00_Input" --include "_caso.md" --include "_intake_log.jsonl" --ignore-existing --log-level INFO --log-file "auditlog_merge_%TS%.log"

echo [3/5] Notas personales (copia ciega, sin inventario)...
if exist "%LOCAL%\90_Notas personales" rclone copy "%LOCAL%\90_Notas personales" "%REMOTE%/90_Notas personales" --checksum --transfers 4 --log-level ERROR --log-file "notas_%TS%.log"

echo [4/5] Verificacion por hash (local contra Drive)...
rclone check "%LOCAL%" "%REMOTE%" --one-way --drive-skip-shortcuts --fast-list ^
  --exclude "desktop.ini" --exclude "90_Notas personales/**" ^
  --exclude "_caso.md" --exclude "_intake_log.jsonl" ^
  --exclude "MANIFEST_CHECKOUT.json" --exclude "AUDITLOG_MERGE_*.jsonl" ^
  --exclude "_snapshot/**" --exclude "_pendiente_checkin/**" ^
  --log-level INFO --log-file "check_%TS%.log"
if errorlevel 1 goto :revisar

echo [5/5] Subiendo evidencia al expediente...
rclone copy . "%REMOTE%/07_AI cowork/merge_%TS%" --include "auditlog_merge_%TS%.log" --include "check_%TS%.log"

echo.
echo ============================================
echo  VERDE: merge completado y verificado por hash.
echo ============================================
goto :fin

:revisar
echo.
echo ============================================
echo  AMARILLO: copia hecha pero la verificacion encontro diferencias.
echo  NO borres nada. Revisa con Claude: check_%TS%.log
echo ============================================
goto :fin

:fail
echo.
echo ============================================
echo  ROJO: fallo en la copia. NO borres nada.
echo  Revisa con Claude: auditlog_merge_%TS%.log
echo ============================================

:fin
endlocal
