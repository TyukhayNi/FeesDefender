# Lecciones de producción (sesión 2026-07-07, casos W-02VND1 y W-02THLJ)

Fallos reales encontrados durante la validación del procedimiento, con su diagnóstico y solución. Consulta esto cuando algo se comporte de forma inexplicable.

## 1. Ficheros con acentos ausentes «sin errores» (CRÍTICO)

**Síntoma:** rclone copia N ficheros de una lista de M (N < M), termina con 0 errores, y todos los ausentes tienen acentos/ñ/ª en el nombre.
**Causa:** la salida de rclone pasó por una tubería de PowerShell (`rclone ... | Out-File`). PowerShell decodifica el UTF-8 de rclone como CP850 («ó» → «├│») y el fichero resultante contiene nombres corruptos que luego no casan con el disco.
**Solución:** jamás canalizar rclone por PowerShell. Usar redirección de CMD (`>`), `--log-file`, o `subprocess` de Python con `encoding="utf-8"`. La detección: verificación por conteo esperado vs real (nunca por código de salida).

## 2. Listado de unidad sin acceso termina «bien» y vacío

**Síntoma:** `rclone lsjson` contra una carpeta de Drive a la que el token no tiene acceso puede terminar sin error visible y con salida vacía o truncada.
**Solución:** validar siempre el resultado (JSON parseable + nº de entradas plausible), no el código de salida. Si sale vacío, comprobar cuenta del remote: `rclone backend drives <remote>:` lista las unidades que el token ve.

## 3. Dos remotes, dos cuentas — no confundirlos

`gdrive_ev` = cuenta Engel & Völkers (ve las unidades E&V: Madrid S1..., operaciones). `gdrive_tl` = cuenta del despacho (ve `EXPEDIENTES - TYUKHAY LEGAL`: CASOS, CASOS - NO FEESDEFENDER, _ingest). El checkin usa siempre `gdrive_tl`. Si hay duda sobre a qué unidad apunta un remote, `rclone backend drives` la resuelve. Referirse a unidades/carpetas por ID (`team_drive=`, `root_folder_id=` como parámetros en línea `"remote,team_drive=ID,root_folder_id=ID:"`) es más robusto que las rutas por nombre.

## 4. Vista congelada del montaje en la sesión de Cowork

**Síntoma:** un fichero que el usuario acaba de sobrescribir (o que crece, como un log en curso) se ve desde el sandbox con el contenido/tamaño antiguo, indefinidamente.
**Solución:** nombres únicos con timestamp para cada artefacto; si hay que releer un fichero regenerado con el mismo nombre, pedir al usuario `copy fichero fichero_copiaN` y leer la copia (la creación de ficheros nuevos sí se propaga). La herramienta Read del sistema de ficheros a veces ve la versión buena cuando bash no.

## 5. Listado recursivo lentísimo tras subida grande

**Síntoma:** `rclone lsjson -R` de la carpeta recién sincronizada se queda parado (cuota de la API de Google tras cientos de subidas).
**Solución:** `--fast-list` en todos los listados post-merge (menos llamadas, más grandes). Si aun así se atasca, esperar ~10 min.

## 6. Carpeta que «desaparece» del Desktop

**Síntoma:** `dir` no la muestra y `move`/`ren` dicen «no se encuentra el archivo», pero `dir /s /b /ad` la encuentra.
**Causa:** atributo oculto/sistema (`S` o `H`) puesto por Explorer/OneDrive. `dir /b` los omite; `move` no los resuelve.
**Solución:** `attrib "ruta"` para diagnosticar; `attrib -h -s "ruta"` para limpiar; reintentar el move.

## 7. «Acceso denegado» al renombrar la carpeta del caso

**Causa:** un proceso tiene un handle dentro (Explorer, Word/Acrobat con un documento del caso abierto, otra ventana de terminal con cwd dentro, o el propio montaje de la sesión de Cowork que ha estado listando la carpeta).
**Solución:** cerrar ventanas y reintentar; si persiste, hacerlo tras cerrar la sesión de Cowork o reiniciar. No es urgente: el rename del BKUP_ es cosmético, la seguridad la dan Drive verificado + manifiesto.

## 8. `.ps1` desde CMD no se ejecuta (y a veces sin error visible)

Los scripts para el usuario van en `.cmd`. Si hay que ejecutar PowerShell sí o sí: `powershell -ExecutionPolicy Bypass -File script.ps1`. Los bloques de comandos siempre empiezan con `cd` (regla del despacho).

## 9. `rclone config create/reconnect` imprime el token en consola

Si el usuario pega el transcript, el token queda expuesto en el chat. Avisar de inmediato y guiar la rotación: revocar la entrada «rclone» en https://myaccount.google.com/connections (solo esa — las de Claude/Anthropic son de los conectores) + `rclone config reconnect <remote>:`. La rotación no afecta al código ni a los conectores: cada aplicación tiene su grant independiente.

## 10. `--backup-dir` no puede solaparse con el destino

Debe estar en el mismo remote pero fuera del árbol de destino. Convención: `gdrive_tl:_merge_backups/<W-CODE>_<TS>/` en la raíz de la unidad.

## 11. Google-native (Docs/Sheets) no tienen MD5

`rclone check`/comparaciones por hash no pueden verificarlos. Regla conservadora: preservar la versión Drive y avisar en el reporte.

## 12. Detección de renombrados

Un fichero movido/renombrado en local aparece como «solo local» + «solo Drive». Antes de tratarlo como nuevo+huérfano, cruzar por MD5: si coincide, es un renombrado — copiar la ruta nueva y borrar (a papelera) la vieja, no duplicar.

## 13. Los artefactos de protocolo NO se sincronizan por la copia general

`MANIFEST_CHECKOUT.json`, `AUDITLOG_MERGE_*.jsonl`, `_snapshot/**` y `_pendiente_checkin/**` los gestiona el protocolo, no el sync. Deben ir en `--exclude` de la copia Y del `check` (además de `_caso.md`, `_intake_log.jsonl` y `90_Notas personales/**`). Si no se excluyen: el baseline y los logs se pisan, el AUDITLOG viaja sin control (debía subirse al final, verificado) y la bandeja `_pendiente_checkin/` se duplica. Coinciden con `MERGE_EXCLUSIONS` del repo (`core.config`) — es la fuente única; si cambian ahí, actualizar la plantilla.

## 14. El checkin cierra liberando el lock (CP11)

El checkout deja el caso `prestado` en el `_caso.md` del Drive. El checkin, si es VERDE, debe ponerlo `disponible` (limpiar `checkout_*`, fijar `ultimo_checkin_*`). Si quedan conflictos, NO liberar: `estado_repositorio: conflicto` y el local se conserva. El evento del log es el canónico `case_checkin` (no `merge_sync_completado`: el guard del repo rechaza eventos fuera de `INTAKE_EVENTS`). La CLI lo hace con `repository_checkout.aplicar_lock_liberado`; por chat, editar el frontmatter respetando esos campos.
