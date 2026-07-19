---
estado: historico
dueño: Nikolai Tyukhay
---

# DISEÑO V2 (CONGELADO): Merge Desktop→Drive + Sistema de Biblioteca

**Fecha:** 2026-07-07
**Sustituye a:** HANDOFF_SESION_20260707_MERGE_BIBLIOTECA.md (v1) en todo lo que contradiga
**Base:** REVISION_20260707_MERGE_BIBLIOTECA.md (hallazgos H1-H14) + decisiones de Nikolai del 07-07
**Estado:** DISEÑO CONGELADO — siguiente paso: piloto manual en W-02VND1 (Paso 1 del roadmap)
**Implementa código:** Claude Code. Cowork no toca el repo.

---

## 0. DECISIONES CONGELADAS

| # | Decisión | Resolución |
|---|----------|------------|
| D1 | Algoritmo de merge | **3 vías** con baseline de checkout (`MANIFEST_CHECKOUT.json`). El timestamp deja de ser criterio de decisión. |
| D2 | Borrados locales | **Se propagan con confirmación explícita**; destino: papelera de Drive (recuperable 30 días). |
| D3 | Escrituras al caso prestado | **Bandeja `_pendiente_checkin/`** dentro del caso en Drive; se integran tras el checkin. |
| D4 | Usuarios de checkout | **Nikolai, Paola, Ana y Sergio.** Ninguno de los tres últimos tiene Streamlit hoy → el frontal no puede depender de Streamlit. |
| D5 | `90_NOTAS_PERSONALES/` | **Fuera del checkout por completo.** No se copia a local, no participa en el merge, vive solo en Drive. |
| D6 | Motor de copia | **rclone** (remote API `gdrive_ev`, nunca el montaje `G:`). Un solo motor para todos los usuarios. |
| D7 | Snapshot pre-merge | **Inventario (hashes) + backup selectivo** de lo que se sobrescribe/borra vía `--backup-dir`. Sin copia completa. |
| D8 | Máquina de estados | **3 estados:** `disponible` / `prestado` / `conflicto`. |

---

## 1. ARQUITECTURA: CEREBRO / MÚSCULO / FRONTALES

```
CEREBRO  core/repository_checkout.py (repo, Claude Code)
         Lógica PURA: validar transiciones, calcular plan de merge 3 vías
         (entrada: 3 inventarios; salida: lista de acciones), mutar CaseMeta,
         generar eventos de _intake_log.jsonl. CERO I/O contra Drive.

MÚSCULO  rclone contra remote gdrive_ev (API, nunca G:)
         Mueve bytes según el plan que el cerebro calculó.
         Flags obligatorios: --checksum --drive-skip-shortcuts
         Snapshot: --backup-dir   Informe previo: --dry-run

FRONTALES (todos llaman al MISMO script local)
  a) CLI local `feesdefender checkout|checkin W-XXXXXX`
     → vía de Paola/Ana/Sergio (y Nikolai). Independiente de Streamlit.
  b) Skills Cowork checkout-caso / checkin-caso
     → vía de Nikolai en sesiones con Claude. La skill orquesta, presenta
       gates y decisiones; la ejecución la hace el script local.
  c) Streamlit (futuro, opcional).
```

Restricciones de frontera confirmadas: el código del repo **no puede** llamar a expedientes-xl (es conector MCP de Cowork). El sandbox de Cowork **no ejecuta** programas del Windows del usuario; en el piloto se probará si rclone corre dentro del sandbox contra `gdrive_ev` — si sí, la skill dirige de punta a punta; si no, la skill entrega el comando PowerShell verificado (con `cd` inicial, regla del despacho) y el usuario lo pega. En ambos casos el plan de merge lo calcula el cerebro; nunca se improvisa un `rclone sync` a mano.

Secretos: `rclone.conf` (token) nunca se pega en chat ni se lee al contexto del modelo; rclone lo lee él solo.

---

## 2. MÁQUINA DE ESTADOS (SSOT: config.py)

```python
ESTADO_REPO_DISPONIBLE = "disponible"   # en Drive, nadie lo tiene
ESTADO_REPO_PRESTADO   = "prestado"     # checked out, copia de trabajo local
ESTADO_REPO_CONFLICTO  = "conflicto"    # checkin detectó conflicto; local SE CONSERVA

TRANSICIONES_PERMITIDAS: dict[str, tuple[str, ...]] = {
    "disponible": ("prestado",),
    "prestado":   ("disponible", "conflicto"),
    "conflicto":  ("prestado", "disponible"),
}
```

Condiciones adjuntas (validadas por el cerebro, no solo por la tabla):

- `prestado → disponible` solo por: (a) checkin completado con verificación, o (b) **cancelación de checkout** con confirmación explícita «el trabajo local se descarta».
- `conflicto → disponible` solo con resolución registrada en `CONFLICTOS_RESUELTOS.md`.
- `conflicto → prestado` = reabrir para resolver en local y reintentar checkin.
- El checkin es una **operación**, no un estado. Nada de `modified` / `sync_pendiente` / `sincronizado`.

### 2.1 Autoridad del lock

- El hecho vigente vive en **`_caso.md` del Drive**, único árbitro. El `_caso.md` de la copia local **nunca** es autoridad de su propio lock.
- Homes declarados: definición = `config.py` · hecho vigente = `_caso.md` (Drive) · historia = `_intake_log.jsonl` · STATUS.md = **vista derivada regenerable** (nunca se edita a mano).

### 2.2 Protocolo de adquisición (write-then-verify con nonce)

1. Leer `_caso.md` Drive → si no `disponible`, abortar informando quién lo tiene.
2. Escribir lock: `estado_repositorio: prestado` + `checkout_user`, `checkout_timestamp` (ISO 8601 con zona), `checkout_nonce` (aleatorio).
3. Esperar 3-5 s (sync lag conocido del Drive), **releer por API** y confirmar que el nonce ganador es el propio. Si no, otro ganó: abortar limpio.
4. Ventana residual de carrera: riesgo aceptado y documentado (4 usuarios conocidos, velocidad humana).
5. Campo `checkout_local_path`: NO se escribe en `_caso.md` (visible para E&V); la ruta local completa queda solo en el evento de `_intake_log.jsonl`. En `_caso.md`, como mucho, nombre de máquina.

### 2.3 CaseMeta (campos nuevos)

```python
estado_repositorio: str = "disponible"
checkout_user: str | None = None
checkout_timestamp: str | None = None      # ISO 8601 con zona
checkout_nonce: str | None = None
checkout_maquina: str | None = None        # hostname, no ruta
checkout_notas: str | None = None
ultimo_checkin_timestamp: str | None = None
ultimo_checkin_auditlog: str | None = None # nombre del AUDITLOG en Drive
```

---

## 3. CHECKOUT

1. Adquirir lock (§2.2).
2. Copiar caso Drive → local con rclone (`--checksum --drive-skip-shortcuts`), **excluyendo** `MERGE_EXCLUSIONS` (§5) y `90_NOTAS_PERSONALES/`.
3. Generar **`MANIFEST_CHECKOUT.json`** (baseline): inventario ruta relativa + hash + tamaño de todo lo copiado. Se guarda **en el Drive**, junto al caso (no solo en local: debe sobrevivir a la muerte del Desktop).
4. Evento `case_checkout` en `_intake_log.jsonl` (usuario, timestamp, ruta local, nonce, nº ficheros, hash del manifest).
5. Confirmación al usuario con ruta local y recordatorio del plazo de cortesía (alerta >7 días).

---

## 4. CHECKIN — MERGE DE 3 VÍAS

### 4.1 Tabla canónica de decisión (por fichero, comparación por hash)

Entradas: `L` = local ahora, `D` = Drive ahora, `B` = baseline (MANIFEST_CHECKOUT).

| Caso | L vs B | D vs B | Acción | Nota |
|------|--------|--------|--------|------|
| 1 | igual | igual | `SKIP` | Sin cambios |
| 2 | cambiado | igual | `COPY_LOCAL` | Solo cambió local |
| 3 | igual | cambiado | `PRESERVE_DRIVE` | Solo cambió Drive (Marta/pipeline) |
| 4 | cambiado | cambiado | `CONFLICT` | Divergencia real, decisión manual |
| 5 | ausente (borrado local) | igual | `DELETE_DRIVE` | **Solo con confirmación**; a papelera Drive (D2) |
| 6 | ausente | cambiado | `CONFLICT` | Borraste algo que otro cambió |
| 7 | nuevo en local (no en B) | no existe | `COPY_LOCAL` | Fichero nuevo |
| 8 | no existe | nuevo en Drive (no en B) | `PRESERVE_DRIVE` | Nuevo en Drive durante el préstamo |
| 9 | nuevo local, hash ya existe en D con otra ruta | — | `RENAME` | Renombrado detectado: mover, no duplicar |

Regla por defecto: **todo fichero del caso pasa por esta tabla**, salvo §4.2 y §5. No hay carpetas «sin categoría».

### 4.2 Excepción única: derivados regenerables (antigua Cat. A, recortada)

`INDICE.md`, `CRONOLOGIA.md`, `_MANIFIESTO.md`, `_TRIAJE_VIABILIDAD.docx` → `COPY_LOCAL` directo (local gana) **salvo** que `hash(D) != hash(B)`: entonces `CONFLICT` (alguien tocó el Drive durante el préstamo; nada de overwrite ciego). `identidades.yaml` es **maestro, no derivado**: va por la tabla general 4.1.

Google-native (Docs/Sheets sin hash MD5): siempre `PRESERVE_DRIVE` + aviso en el DELTA. No se intenta mergear.

### 4.3 Secuencia y checkpoints canónicos (tabla única, sustituye CP1-CP12 v1)

| CP | Gate | Detalle |
|----|------|---------|
| CP0 | Lock verificado | Caso `prestado` a este usuario; ruta local existe (si no → runbook §7.1) |
| CP1 | Inventarios | L (hash local), D (hash vía API, no G:), B (manifest del Drive) |
| CP2 | Validación SSOT local | Informativa: INDICE/CRONOLOGIA/_MANIFIESTO citan ficheros reales. Si ⚠️, avisar y pedir confirmación |
| CP3 | Plan de merge aprobado | Tabla 4.1 aplicada → `DELTA_PREVIO.md` (equivale a dry-run); **el usuario aprueba** antes de tocar nada. Borrados (acción 5) listados aparte con confirmación específica |
| CP4 | Backup selectivo armado | `--backup-dir` apuntando a `_snapshot/AAAA-MM-DDTHHMMZ/` dentro del caso; solo recibe lo que se sobrescriba/borre |
| CP5 | Copias ejecutadas y verificadas | Por fichero: `log(intent)` → copiar → **releer hash del Drive por API** → `log(OK)`. Fallos: `log(FAIL)`, continuar; abortar solo si sistémico (≥5 consecutivos) |
| CP6 | Borrados ejecutados | Solo los confirmados en CP3; a papelera de Drive; log por fichero |
| CP7 | Conflictos cerrados o parada | Si quedan `CONFLICT` sin resolver → estado `conflicto`, local SE CONSERVA, saltar a CP9 y **parar** (no CP10-CP12) |
| CP8 | Verificación global | Conteos esperados (calculados del plan) vs reales; hashes de maestros. Sin gate por ratio de tamaños (el V6 del v1 se elimina) |
| CP9 | AUDITLOG subido y verificado | `AUDITLOG_MERGE_AAAA-MM-DDTHHMMZ.jsonl` al Drive como **último artefacto**, hash verificado. Antes de esto no se toca el local |
| CP10 | Bandeja integrada | Contenido de `_pendiente_checkin/` procesado (§6); bandeja vaciada |
| CP11 | Lock liberado | `prestado → disponible` en `_caso.md` Drive + eventos `case_checkin_*` en `_intake_log.jsonl`; STATUS.md regenerado |
| CP12 | Local a papelera (opcional) | Solo tras confirmación del usuario; mover a `BKUP_AAAA-MM-DDTHHMMZ_<caso>`; `MANIFEST_BORRADO_*.json`; borrado definitivo a los 7 días con **recordatorio programado**, no de memoria |

La papelera local (CP12) es cortesía, no backup: la garantía es CP5+CP8+CP9. El Desktop se asume volátil.

### 4.4 Doctrina de idempotencia

**La recuperación ante cualquier fallo (OAuth, crash, red, corte) es re-ejecutar el checkin desde cero.** La comparación por hash previa a cada copia hace que lo ya hecho se salte solo (convergencia). El AUDITLOG es **evidencia forense**, no mecanismo de recovery; no hay «reanudación por puntero». Test obligatorio: interrumpir un merge a mitad y verificar que la re-ejecución converge al mismo estado final.

---

## 5. EXCLUSIONES DEL MERGE (gestionadas por protocolo, jamás por el sync)

```python
MERGE_EXCLUSIONS: tuple[str, ...] = (
    "_caso.md",                  # lock: solo lo escribe el protocolo (§2)
    "_intake_log.jsonl",         # forense append-only: solo eventos del protocolo
    "MANIFEST_CHECKOUT.json",
    "AUDITLOG_MERGE_*.jsonl",    # subida controlada en CP9
    "_snapshot/**",
    "_pendiente_checkin/**",     # bandeja: integración controlada en CP10
    "90_NOTAS_PERSONALES/**",    # D5: fuera del checkout por completo
)
```

`_intake_log.jsonl` durante el préstamo: **solo escribe el lado Drive** (eventos del protocolo y de la bandeja). El local no genera eventos propios en su copia; si algún proceso local necesita registrar, lo hace en un buffer local que el checkin vuelca como eventos nuevos al log del Drive (append, nunca overwrite).

---

## 6. BANDEJA `_PENDIENTE_CHECKIN/` (guard del pipeline)

- Toda escritura al caso en Drive (intake, skills, pipeline, CRM-pull) **verifica `estado_repositorio` antes de escribir**. Cambio REQUERIDO en el MVP (faltaba en el v1).
- Si `prestado`: el fichero va a `_pendiente_checkin/<origen>/...` con metadato de procedencia (quién, cuándo, fuente) + evento en `_intake_log.jsonl`. Nadie se bloquea, nada se pierde.
- Si `conflicto`: igual que `prestado`.
- En CP10 el checkin procesa la bandeja por la ruta de intake normal (a `00_Input/<fuente>`) y la vacía. Si algo de la bandeja colisiona con lo recién mergeado → se trata como intake nuevo (nunca sobrescribe silenciosamente).
- Excepción al guard: el propio protocolo (lock, log, bandeja) escribe siempre.

---

## 7. RUNBOOKS DE ERROR

### 7.1 Ruta local perdida (Desktop borrado/movido con caso `prestado`)
El checkin valida la ruta en CP0. Si no existe: ofrecer (a) señalar nueva ruta, o (b) cancelar checkout con aviso explícito «el Drive queda como en el checkout; el trabajo local se ha perdido». Descubrimiento: alerta de préstamo >7 días.

### 7.2 Fallo de auth / red a mitad de merge
Parar, reautenticar/reconectar, **re-ejecutar desde cero** (§4.4). Sin estado intermedio que limpiar: el Drive nunca queda en estado que la re-ejecución no repare.

### 7.3 Caso pegado en `conflicto`
El local se conserva siempre. Resolver fichero a fichero (elegir lado, combinar o versionar), registrar en `CONFLICTOS_RESUELTOS.md`, reintentar checkin (`conflicto → prestado` → checkin).

### 7.4 Dos préstamos simultáneos del mismo caso
Prevenido por §2.2. Si pese a todo ocurre (ventana residual): el segundo checkin detectará `hash(D) != hash(B)` masivo → conflictos, no pérdida silenciosa. El 3 vías es la red de seguridad del lock.

Dos casos distintos en paralelo por el mismo usuario: **permitido** (lock por caso).

---

## 8. ARTEFACTOS Y NOMBRES

- Timestamps siempre ISO 8601 completos con zona (`2026-07-07T09:45:12Z`), también dentro de los `.jsonl`.
- `AUDITLOG_MERGE_<ISO>.jsonl`, `MANIFEST_BORRADO_<ISO>.json`, `_snapshot/<ISO>/` — sin colisiones intra-día.
- Orden por fichero en el AUDITLOG: `intent` → copia → verificación hash → `OK|FAIL`.
- `DELTA_PREVIO.md` (CP3) y `REPORTE_CHECKIN_<ISO>.md` (CP8) en la raíz del caso.
- Tests y fixtures del repo (público): **solo datos sintéticos** — nunca W-IDs reales, nombres de inmuebles ni rutas de usuario.

---

## 9. CAMBIOS EN FEESDEFENDER (MVP revisado)

| Componente | Cambio | Notas |
|---|---|---|
| `config.py` | 3 estados + `TRANSICIONES_PERMITIDAS` + `MERGE_EXCLUSIONS` + derivados regenerables | SSOT de definición |
| `case_manager.py` | Campos CaseMeta §2.3 | Retrocompatible (defaults) |
| `core/repository_checkout.py` | **Puro**: transiciones, plan 3 vías (función inventarios→acciones), eventos | Sin I/O Drive |
| `scripts/` o CLI | `feesdefender checkout|checkin` — orquesta cerebro + rclone | Frontal de los 4 usuarios (D4) |
| Guard de escritura | Todo punto que escribe al caso en Drive respeta §6 | **Nuevo respecto al v1; imprescindible** |
| `tests/` | Transiciones; tabla 4.1 completa (9 casos); doble checkout rechazado; re-ejecución converge; round-trip `_caso.md`; bandeja | |
| Skills Cowork | `checkout-caso` / `checkin-caso` llamando al mismo script | Fase 2, tras piloto |

Diferidos (sin cambios respecto al v1): `audit_log.py`, alertas de timeout como tarea programada, sección STATUS.md (vista derivada), UI Streamlit.

---

## 10. SIGUIENTE PASO — PILOTO MANUAL EN W-02VND1 (Paso 1)

Antes de escribir código: ejecutar el procedimiento completo una vez, dirigido por checklist con gates humanos, para descubrir lo que el diseño no ve. Verificaciones específicas del piloto:

1. ¿rclone corre dentro del sandbox de Cowork contra `gdrive_ev`? (decide la variante de orquestación de la skill, §1)
2. ¿Hay Google-native en los casos reales? (activa la regla §4.2)
3. Volumen real de conflictos con 3 vías (¿fatiga de confirmaciones?)
4. Sync lag efectivo en el write-then-verify del lock (§2.2: ajustar la espera)
5. Ubicación de `_snapshot/` — confirmar que no ensucia la vista de Marta/E&V; si molesta, moverla a zona interna

### Preguntas abiertas (no bloquean el piloto)

- ¿Paola/Ana/Sergio tendrán sesiones Cowork con las skills, o solo la CLI local? (condiciona cuánta ergonomía meter en la CLI)
- ¿Recordatorio del borrado definitivo (CP12): tarea programada de Cowork o del sistema?

---

**FIN DEL DISEÑO V2** — Congelado 2026-07-07. Cambios posteriores: versionar como V2.1 con nota de qué decisión se reabre y por qué.
