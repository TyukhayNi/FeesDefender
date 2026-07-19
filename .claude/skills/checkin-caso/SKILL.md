---
name: checkin-caso
description: Checkin (merge) de un caso FeesDefender desde una carpeta local del PC al repositorio canónico del Drive del despacho (unidad EXPEDIENTES - TYUKHAY LEGAL), con rclone como motor, verificación por hash, respaldo automático de lo sobrescrito y cierre forense en _intake_log.jsonl. Úsala SIEMPRE que el usuario quiera sincronizar, mergear, subir o "devolver" al Drive una carpeta local de caso; dispara con "checkin del caso", "mergea esta carpeta al Drive", "sube el caso W-XXXXX al Drive", "sincroniza el expediente con el Drive", "quiero retirar la copia local", o cuando aporte una ruta local de caso (Desktop\BaXXX - ... - (W-XXXXX) - ...) junto a una carpeta de Drive. También cubre la retirada segura del local tras el merge (manifiesto + BKUP_ + recordatorio de borrado). NO hace el checkout (Drive→local) ni organiza el contenido del caso (organizar-sala-lectura) ni valora viabilidad.
metadata:
  rol: transversal
  naturaleza: atomica
  jurisdiction: ES
  area: [civil, procesal]
  version: "1.0"
  author: "Nikolai Tyukhay"
  organization: "Tyukhay Legal"
  contact: "nikolai.tyukhay@tyukhay.legal"
  status: vigente
  requires: []
license: "Proprietary — Tyukhay Legal (todos los derechos reservados)"
---

# Checkin de caso — merge Desktop→Drive (FeesDefender)

Implementa el checkin del sistema de biblioteca del despacho (DISEÑO_V2 merge+biblioteca), en su versión orquestada por skill: Claude calcula y verifica; rclone, en la máquina del usuario, mueve los bytes. Procedimiento validado en producción (piloto W-02VND1 y W-02THLJ, 2026-07-07).

## Contexto que necesitas entender

- El Drive del despacho es la fuente de verdad; la carpeta local es una copia de trabajo prescindible. **Nunca puede perderse nada que esté en Drive** — de ahí el `--backup-dir` y la papelera en todos los borrados.
- Tú no puedes ejecutar rclone (tu sandbox no llega a la API de Google): tu papel es localizar, emparejar, generar el script, auditar los logs y registrar el cierre. El usuario pega comandos en CMD.
- El remote correcto es **`gdrive_tl`** (cuenta del despacho, `team_drive=0AAhcjDaZBWe6Uk9PVA`). El remote `gdrive_ev` es de la cuenta Engel & Völkers y NO ve la unidad de expedientes — no lo uses jamás para esto. Referir carpetas por **ID** antes que por ruta cuando el usuario lo aporte.
- **Paridad con la CLI local.** Esta skill y la CLI `python -m scripts.repository_cli checkin` del repo FeesDefender comparten un ÚNICO comportamiento: el mismo cerebro (`core.repository_checkout`) y los mismos flags de rclone (`--checksum`, `--backup-dir`, exclusiones de protocolo, `check --one-way --fast-list`, semáforo). La skill es la vía por chat; la CLI, la vía de terminal. No inventes un `rclone sync` a mano: si dudas, remite a la CLI.
- **Baseline de 3 vías.** Si en la carpeta existe `MANIFEST_CHECKOUT.json` (creado en el checkout), el merge es de **3 vías** y puede distinguir un borrado local (propagar a Drive, con confirmación y a papelera) de un fichero nuevo en Drive (preservar), y un conflicto real (ambos lados cambiaron) de un cambio trivial. **La copia del `.cmd` por sí sola NUNCA borra en Drive** (es conservadora): la propagación de borrados y la resolución de conflictos con baseline las hace la CLI con su plan 3-vías. Sin manifiesto, el merge degrada a 2 vías conservador (lo que validó el piloto): «solo-local» se copia, «solo-Drive» se preserva, «distinto» va a decisión manual.

## Flujo

### 1. Localizar y emparejar

- Local: verifica que la carpeta existe vía bash sobre la carpeta montada (`<mount>/Desktop/...` u otra ruta que dé el usuario). Cuenta ficheros y tamaño (`find | wc -l`, `du -sh`).
- Drive: localiza la carpeta homónima con el conector de Google Drive (busca por `W-XXXXX` o usa la URL/ID que aporte el usuario). Confirma título y ruta (normalmente `CASOS/<ciudad>/<nombre del caso>` en la unidad compartida `EXPEDIENTES - TYUKHAY LEGAL`, team_drive `0AAhcjDaZBWe6Uk9PVA`).
- Si los nombres local/Drive no coinciden exactamente, muestra ambos y pide confirmación antes de seguir.

### 2. Generar el script de merge

Usa la plantilla `assets/merge_template.cmd`. Sustituye los marcadores `__LOCAL__`, `__REMOTE__`, `__TS__` (timestamp `AAAAMMDDTHHMM`) y `__WCODE__`. Escríbelo en una carpeta de trabajo nueva `C:\Users\<usuario>\_merge_<W-CODE>\` (vía bash sobre el montaje, codificación UTF-8 **sin BOM** y saltos CRLF — la plantilla lleva `chcp 65001` para que CMD lea bien los acentos y `ª` de los nombres).

Por qué la plantilla es como es (no lo cambies sin motivo):

- `--checksum`: compara por hash, no por fecha → re-ejecutable: si se corta, se relanza y continúa. Esta es la doctrina de recuperación ante cualquier fallo (red, OAuth, cierre): re-ejecutar desde cero converge.
- `--backup-dir gdrive_tl:_merge_backups/<W-CODE>_<TS>`: todo lo que la copia sobrescribiría en Drive se aparta ahí en vez de perderse. Es lo que permite ejecutar sin puertas interactivas: las decisiones de conflicto pasan de "antes" a "revisables después".
- **Exclusiones de protocolo** (gestionadas por el protocolo, nunca por el sync): `_caso.md`, `_intake_log.jsonl`, `MANIFEST_CHECKOUT.json`, `AUDITLOG_MERGE_*.jsonl`, `_snapshot/**`, `_pendiente_checkin/**` y `90_Notas personales/**`. Coinciden con `MERGE_EXCLUSIONS` del repo (`core.config`). `_caso.md` y `_intake_log.jsonl` se suben aparte con `--ignore-existing` (son el lock y el log forense append-only; una sobreescritura ciega destruiría historia y el estado del lock). El AUDITLOG se sube al final, controlado (no por la copia general): por eso se excluye.
- `90_Notas personales/` va en copia ciega aparte: es zona reservada del abogado — **ni su contenido ni sus nombres de fichero pasan por ti**; no la inventaríes, no la listes, no la leas. Bajo la decisión D5 del diseño, las notas quedan **fuera del checkout por completo** (viven solo en Drive), así que en la práctica la copia ciega suele ser un no-op de cortesía para carpetas locales heredadas.
- `rclone check --one-way` al final: verificación por hash local→Drive. Los ficheros que solo estén en Drive se preservan (regla conservadora).
- Semáforo final VERDE/AMARILLO/ROJO con instrucción explícita de no borrar nada si no es verde.

Entrega al usuario UNA sola línea para pegar en CMD (la ruta del `.cmd`) y explica el semáforo en dos frases.

### 3. Auditar (cuando el usuario reporte el color)

- **VERDE**: lee los logs desde el montaje (`auditlog_merge_*.log`, `check_*.log`) y confirma: nº de `Copied` coherente con lo esperado, `ERROR: 0`, check sin diferencias. No te fíes del semáforo sin mirar los logs: rclone puede terminar "sin error" sin haber hecho lo pedido (visto en producción con rutas inválidas).
- **AMARILLO**: lee `check_*.log`, clasifica las diferencias (¿solo-local sin copiar? ¿hash distinto?) y resuélvelas con el usuario vía AskUserQuestion: por cada conflicto real, quién gana; recuerda que lo sobrescrito está en `_merge_backups/` y el historial de revisiones de Drive guarda lo demás.
- **ROJO**: lee `auditlog_merge_*.log`, identifica la causa (permisos, ruta, red) y corrige. La re-ejecución es siempre segura.
- Si `_caso.md` o `_intake_log.jsonl` existían en Drive y difieren del local: descarga la versión Drive junto a la carpeta de trabajo (`rclone copyto`, comando para el usuario), compara por líneas y aplica **unión** (el log es append-only: nunca se pierde una línea de ningún lado). Sube el resultado.

### 4. Cierre forense (solo si el semáforo es VERDE)

1. Registra en el `_intake_log.jsonl` del caso (en Drive, vía conector expedientes-xl `append_text`, ruta formato `G:/Unidades compartidas/EXPEDIENTES - TYUKHAY LEGAL/CASOS/...`) el evento canónico **`case_checkin`** (así lo nombra `INTAKE_EVENTS` del repo; no uses nombres inventados como `merge_sync_completado`, que el guard rechazaría) con `details`: `user`, `checkin_timestamp` (ISO con zona), `copiados`, `preservados`, `borrados`, `conflictos`, `renombrados`, `resultado`, `auditlog` (nombre del `AUDITLOG_MERGE_<TS>.jsonl`).
2. **Libera el lock (CP11).** El caso queda `prestado` en el `_caso.md` del Drive desde el checkout; al cerrar el checkin hay que ponerlo `disponible`. Descarga el `_caso.md` del Drive (`rclone copyto`), pon `estado_repositorio: disponible`, limpia los campos `checkout_*` y fija `ultimo_checkin_timestamp` / `ultimo_checkin_auditlog`, y súbelo. La CLI hace esto con `repository_checkout.aplicar_lock_liberado`; por chat, edita el frontmatter a mano respetando esos campos. Si quedan conflictos → NO liberes: el caso pasa a `conflicto` (`estado_repositorio: conflicto`) y el local se conserva.
3. La evidencia (logs) ya la subió el script a `07_AI cowork/merge_<TS>/` — verifica con el conector de Drive que está ahí.

### 5. Retirada del local (solo si el usuario la quiere)

1. Genera `MANIFEST_BORRADO_<TS>.json` (TS ISO-UTC compacto `AAAA-MM-DDTHHMMZ`, sin colisión intra-día): inventario con hashes de lo que se va a retirar (`rclone lsjson -R --hash` local — comando para el usuario, salida por redirección CMD `>`), quién autoriza, fecha de borrado definitivo (+7 días). El borrado del local (CP12) es **cortesía, no backup**: la garantía es Drive verificado por hash + el AUDITLOG. El Desktop se asume volátil.
2. Súbelo a la carpeta de evidencia (`07_AI cowork/merge_<TS>/`). La retirada del local NO emite un evento de `_intake_log.jsonl` propio (no hay evento canónico para ello; CP12 es opcional): basta el `MANIFEST_BORRADO_` como prueba, referenciado desde el `case_checkin` si procede.
3. Renombra la carpeta local a `BKUP_<TS>_<nombre>` (comando `move` para el usuario; si da «Acceso denegado», hay un fichero abierto o el montaje de esta sesión lo bloquea — se hace tras cerrar sesión o reiniciar, no insistas).
4. Ofrece programar el recordatorio del borrado definitivo a +7 días (tarea programada): ese día se verifica la integridad en Drive ANTES de dar el comando `rd /s /q`.

## Reglas que no se rompen

- Nombres de artefacto siempre únicos con timestamp — nunca sobrescribir un log/inventario existente (tu vista del montaje se congela con los ficheros sobrescritos o en crecimiento; si te pasa, pide al usuario `copy fichero fichero_copia2` y lee la copia).
- La salida de rclone jamás se canaliza por PowerShell (`| Out-File` corrompe UTF-8 vía CP850 y deja fuera silenciosamente los ficheros con acentos). Redirección CMD `>` o `--log-file`.
- Scripts para el usuario: `.cmd`, nunca `.ps1` (CMD no los ejecuta). Todo bloque de comandos empieza con `cd`.
- Verifica por conteo y hash, nunca por código de salida ni por "no hubo errores".
- Listados recursivos de Drive tras subidas grandes: añade `--fast-list` (la cuota de la API frena el listado normal).
- Si el usuario pega un transcript con `rclone config` y token dentro: avísale de rotarlo (revocar en cuenta Google + `rclone config reconnect`).
- Los tests y ejemplos con datos reales del despacho no salen de la conversación.

## Solución de problemas

Si algo se comporta raro (carpeta que "desaparece", move que falla, listados incompletos), consulta `references/lecciones.md` — recoge los fallos reales de producción y su solución.
