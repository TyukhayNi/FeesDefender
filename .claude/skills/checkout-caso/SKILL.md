---
name: checkout-caso
description: Checkout (préstamo) de un caso FeesDefender del Drive del despacho (unidad EXPEDIENTES - TYUKHAY LEGAL) a una carpeta local del PC, con rclone. Adquiere el lock en el _caso.md del Drive (write-then-verify con nonce), copia el caso a local excluyendo ficheros de protocolo y 90_Notas personales, y genera el baseline MANIFEST_CHECKOUT.json que el checkin usará para el merge de 3 vías. Úsala cuando el usuario quiera "sacar", "prestarse" o "bajar a local" un caso; dispara con "checkout del caso", "sácame el caso W-XXXXX a local", "préstame el expediente", "quiero trabajar en local el caso". Es la operación INVERSA de checkin-caso. NO hace el merge de vuelta (checkin-caso), ni organiza el contenido (organizar-sala-lectura), ni valora viabilidad.
---

# Checkout de caso — préstamo Drive→Desktop (FeesDefender)

Implementa el checkout del sistema de biblioteca del despacho (DISEÑO_V2 merge+biblioteca), en su versión orquestada por skill: Claude adquiere el lock y verifica; rclone, en la máquina del usuario, mueve los bytes. Es la operación inversa de `checkin-caso`.

## Contexto que necesitas entender

- El Drive del despacho es la fuente de verdad; la carpeta local es una **copia de trabajo prescindible**. El checkout marca el caso como **prestado** en el Drive para que nadie más lo mueva a la vez (lock).
- Tú no puedes ejecutar rclone (tu sandbox no llega a la API de Google): tu papel es localizar el caso, adquirir y verificar el lock, generar el script y el manifiesto, y registrar el evento. El usuario pega comandos en CMD.
- El remote correcto es **`gdrive_tl`** (cuenta del despacho, `team_drive=0AAhcjDaZBWe6Uk9PVA`). El remote `gdrive_ev` es de Engel & Völkers y NO ve la unidad de expedientes — no lo uses jamás. Referir carpetas por **ID** antes que por ruta cuando el usuario lo aporte.
- **Paridad con la CLI local.** Esta skill y la CLI `python -m scripts.repository_cli checkout` del repo FeesDefender comparten un ÚNICO comportamiento: el mismo cerebro (`core.repository_checkout`) y los mismos flags de rclone. La skill es la vía por chat; la CLI, la de terminal.
- El **hecho vigente del lock vive en el `_caso.md` del Drive** (única autoridad). Nunca es autoridad el `_caso.md` de la copia local.

## Flujo

### 1. Localizar el caso y comprobar disponibilidad (CP0)

- Localiza la carpeta del caso en el Drive con el conector de Google Drive (por `W-XXXXX` o URL/ID que aporte el usuario). Confirma título y ruta (normalmente `CASOS/<ciudad>/<nombre>` en `EXPEDIENTES - TYUKHAY LEGAL`).
- Lee el `_caso.md` del Drive (frontmatter `meta.estado_repositorio`). **Si NO es `disponible`** (está `prestado` o en `conflicto`), **aborta** e informa de quién lo tiene (`checkout_user`) y desde cuándo (`checkout_timestamp`). No se hace doble checkout.

### 2. Adquirir el lock (write-then-verify con nonce, §2.2)

1. Genera un `nonce` aleatorio.
2. Escribe en el `meta` del `_caso.md` del Drive: `estado_repositorio: prestado`, `checkout_user`, `checkout_timestamp` (ISO-8601 con zona, p. ej. `2026-07-07T09:45:12Z`), `checkout_nonce`, `checkout_maquina` (hostname). **NUNCA escribas la ruta local completa en `_caso.md`** (es visible para E&V): esa ruta va solo al `_intake_log.jsonl`.
3. Espera unos segundos (sync lag del Drive), **relee** el `_caso.md` del Drive y confirma que `checkout_nonce` es el tuyo. Si otro ganó la carrera, **aborta limpio** (no copies nada).

### 3. Copiar Drive→local (§3)

Usa la plantilla `assets/checkout_template.cmd`. Sustituye `__REMOTE__`, `__LOCAL__`, `__TS__` (timestamp `AAAAMMDDTHHMM`) y `__WCODE__`. Escríbelo en una carpeta de trabajo nueva `C:\Users\<usuario>\_checkout_<W-CODE>\` (UTF-8 **sin BOM**, CRLF; la plantilla lleva `chcp 65001`).

La plantilla copia el caso a la ruta local **excluyendo** los ficheros de protocolo (`_caso.md`, `_intake_log.jsonl`, `MANIFEST_CHECKOUT.json`, `AUDITLOG_MERGE_*.jsonl`, `_snapshot/**`, `_pendiente_checkin/**`) y `90_Notas personales/**` (D5: la zona reservada del abogado queda fuera del checkout por completo — vive solo en Drive). Entrega al usuario UNA línea para pegar en CMD.

### 4. Generar el baseline `MANIFEST_CHECKOUT.json` (§3.3)

Tras la copia, genera el inventario de lo copiado (ruta relativa + hash MD5 + tamaño) y guárdalo como `MANIFEST_CHECKOUT.json`. La plantilla vuelca `rclone lsjson -R --hash` a un fichero; tú lo reformas al schema `{"generado": <ISO>, "n_ficheros": N, "inventario": {"<rel>": {"hash": "<md5>", "size": N}}}`. **Súbelo al Drive** junto al caso (debe sobrevivir a la muerte del Desktop): es el baseline que el checkin usará para el merge de 3 vías (distinguir borrados de altas, y cambios de un lado de conflictos reales).

### 5. Cierre forense

Registra en el `_intake_log.jsonl` del caso (en Drive, vía conector expedientes-xl `append_text`) el evento canónico **`case_checkout`** (así lo nombra `INTAKE_EVENTS` del repo) con `details`: `user`, `checkout_timestamp`, `checkout_nonce`, `checkout_maquina`, `ruta_local` (la ruta local COMPLETA vive aquí, no en `_caso.md`), `n_ficheros`, `manifest_hash`.

Confirma al usuario la ruta local y recuérdale el **plazo de cortesía** (un préstamo >7 días conviene cerrarlo con checkin o cancelarlo).

## Reglas que no se rompen

- **Nunca doble checkout**: si el `_caso.md` del Drive no está `disponible`, aborta.
- **El lock lo escribe solo el protocolo** en el `_caso.md` del Drive; verifica siempre el nonce tras el sync lag antes de copiar.
- **`90_Notas personales/` fuera del checkout** (D5): no se copia a local, ni se inventaría, ni se lee.
- La ruta local completa **no** va a `_caso.md` (solo hostname); va al `_intake_log.jsonl`.
- Nombres de artefacto únicos con timestamp. La salida de rclone jamás por tubería de PowerShell (corrompe UTF-8 vía CP850): redirección CMD `>`, `--log-file` o `subprocess` con `encoding="utf-8"`.
- Scripts para el usuario en `.cmd` (no `.ps1`); todo bloque empieza con `cd`.
- Verifica por conteo y contenido, nunca por código de salida a secas.
- Si el usuario pega un transcript con `rclone config` y token dentro: avísale de rotarlo.

## Cancelación de checkout (runbook §7.1)

Si el usuario perdió/borró la carpeta local o quiere descartar el préstamo sin devolver trabajo: pon el `_caso.md` del Drive de vuelta a `estado_repositorio: disponible`, limpia los campos `checkout_*`, y avisa explícitamente «el Drive queda como en el checkout; el trabajo local se descarta». No registres checkin (no hubo merge).

## Solución de problemas

Consulta `references/lecciones.md` — recoge los fallos reales de producción (rutas de log inexistentes, `--backup-dir` en remote distinto, UTF-8, cuota API) y su solución, compartidos con `checkin-caso`.
