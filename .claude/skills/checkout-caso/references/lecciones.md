# Lecciones de producción — checkout (compartidas con checkin-caso)

Fallos reales de la validación en vivo del sistema de biblioteca (2026-07-07), con diagnóstico y solución. Consulta esto cuando algo se comporte de forma inexplicable.

## 1. `--log-file` a un directorio inexistente → rclone falla al arrancar

**Síntoma:** `rclone copy` devuelve rc=1 sin transferir nada y sin escribir el log.
**Causa:** el `--log-file` apuntaba a una carpeta que aún no existe (p. ej. el propio `%LOCAL%` cuando aún no se ha creado). rclone no crea el directorio del log.
**Solución:** escribe los logs/artefactos del protocolo en una carpeta de trabajo que YA exista (`C:\Users\<usuario>\_checkout_<W-CODE>\`), no dentro del destino que se está creando.

## 2. UTF-8 de rclone corrompido por tubería de PowerShell (CRÍTICO)

**Síntoma:** ficheros con acentos/ñ/ª ausentes «sin errores».
**Causa:** la salida de rclone pasó por `| Out-File` de PowerShell (decodifica UTF-8 como CP850: «ó»→«├│»).
**Solución:** jamás canalizar rclone por PowerShell. Redirección CMD `>`, `--log-file`, o `subprocess` con `encoding="utf-8"`.

## 3. Dos remotes, dos cuentas — no confundirlos

`gdrive_tl` = cuenta del despacho (ve `EXPEDIENTES - TYUKHAY LEGAL`). `gdrive_ev` = cuenta Engel & Völkers (NO ve la unidad de expedientes). El checkout usa **siempre `gdrive_tl`**. El remote `gdrive_tl` ya lleva el `team_drive` configurado, así que `gdrive_tl:` apunta directamente al Shared Drive del despacho. Referir carpetas por ID es más robusto que por ruta.

## 4. Validar por contenido, no por código de salida

`rclone` contra una unidad sin acceso puede terminar «bien» y vacío. Valida siempre el resultado (nº de ficheros copiados coherente con lo esperado, JSON del inventario parseable), nunca el exit code a secas.

## 5. Listado recursivo lento tras operaciones grandes → `--fast-list`

La cuota de la API de Google frena el `lsjson`/`check` recursivo tras muchas operaciones. Usa `--fast-list` en los listados. Si aun así se atasca, esperar ~10 min.

## 6. El lock vive en el `_caso.md` del Drive (write-then-verify)

El checkout marca `estado_repositorio: prestado` en el `_caso.md` del **Drive** (única autoridad). Escribe el lock con un `nonce`, espera el sync lag y **relee** para confirmar que el nonce ganador es el tuyo antes de copiar. Si otro ganó, aborta sin copiar. Si la copia falla tras adquirir el lock, **revierte** el lock a `disponible` (no dejar el caso «prestado» sin copia local útil).

## 7. `90_Notas personales/` fuera del checkout (D5)

Zona reservada del abogado: no se copia a local, ni se inventaría, ni se lee. Vive solo en el Drive.

## 8. `rclone config create/reconnect` imprime el token en consola

Si el usuario pega el transcript, el token queda expuesto. Avisar de inmediato y guiar la rotación (revocar «rclone» en la cuenta Google + `rclone config reconnect`).

## 9. La operativa de la biblioteca es idempotente

Ante cualquier fallo (red, OAuth, corte), re-ejecutar desde cero converge (`--checksum` salta lo ya copiado). No hay «reanudación por puntero»: se relanza el checkout completo.
