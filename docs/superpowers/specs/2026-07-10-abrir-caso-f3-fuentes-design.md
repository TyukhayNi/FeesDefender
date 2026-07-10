---
estado: vigente
dueño: Nikolai (arquitectura) + Claude Code (implementación)
disparador: los casos entran por WhatsApp / email / carpeta suelta, no solo por el Drive de E&V
banco_de_pruebas: casos reales E&V (mismo patrón que F1)
---

# SPEC — `abrir-caso` F3 (A+C): fuentes no-Drive + `init_caso`

**Versión:** 1.0
**Fecha:** 2026-07-10
**Naturaleza:** documento de DISEÑO. El siguiente paso es `writing-plans`, no construir.
**Predecesor:** `docs/superpowers/specs/2026-07-09-abrir-caso-design.md` (F1 mergeada, F2a mergeada).
**Alcance de esta tanda:** parte **(A)** fuentes no-Drive + parte **(C)** `init_caso`. La parte
**(B)** expediente **judicial** en el CRM se aplaza a un frente propio (`F3-judicial`), por
superficie CRM grande (juzgado propiedad no-relación → 404, autos, procedimiento, partes M2M).

---

## 0. Problema

`abrir-caso` (F1) abre un expediente en una pasada (carpeta + intake + CRM), pero **asume que
el material inicial viene del Drive de E&V** (`--fuente drive_ev`, `pull_drive_ev`). En la
práctica, un caso también llega por:

- **WhatsApp** — un export `.zip` de un chat con cliente/consultor.
- **Email** — una etiqueta de Gmail del asunto.
- **Carpeta manual** — documentos sueltos que se aportan localmente.

Hoy, sembrar un caso desde esos canales exige **dos tandas**: abrir el caso y, por separado,
correr la herramienta de intake de esa fuente. F3-(A) hace que **cada canal entre por la
misma puerta**, en un solo comando, con la **misma cadena de custodia** (SHA-256 + evento
forense) que ya tiene `drive_ev`.

**Premio principal (no el ahorro de un clic):** custodia forense **uniforme** para todos los
canales. Hoy el intake **manual no deja huella** (`intake_manual.save_file`/`extract_zip` no
hashean ni emiten evento); F3 lo cierra.

---

## 1. Alcance

**Incluye:**
- Fuentes `manual`, `whatsapp`, `email` en el orquestador CLI `scripts/abrir_caso.py`.
- Cierre del hueco de custodia del intake **manual** (evento forense `upload_manual` con SHA-256).
- Documentar la relación `init_caso.py` ↔ `abrir_caso.py` (parte C, sin cambio funcional).

**No incluye:**
- Expediente **judicial** en el CRM (frente propio `F3-judicial`).
- Fuente `entrevista`/llamada: **excluida** por decisión de Nikolai (canal informal que
  normalmente precede a un email; no se materializa como fuente propia de apertura).
- La skill Cowork `abrir-caso` (es F2b) — este trabajo es solo la CLI local / cerebro.
- Cambios en el cerebro `core/abrir_caso.py`: **no hacen falta** (`plan_intake`/`FUENTE_A_*`
  ya soportan las fuentes). Si algún test los toca, es de lectura.

---

## 2. Decisiones cerradas (brainstorming 2026-07-10)

| # | Decisión | Resolución |
|---|---|---|
| D1 | **Mecanismo de depósito** | **Delegar a los escritores nativos.** `abrir-caso` despacha por fuente al módulo dedicado. No reimplementa depósito. |
| D2 | **Fuente email** | **Export de etiqueta Gmail** (`email_export.export_label`, escritor nativo). Requiere `--cuenta` + `--label` + token `gmail_source`. |
| D3 | **Quién loguea** | **Cada fuente loguea exactamente una vez, en la capa que sabe cómo.** WhatsApp/email se **auto-loguean** (el escritor nativo); Drive/manual los **loguea el orquestador** (hash→plan→reconcile→`append_event`). |
| D4 | **Fuentes por invocación** | **Una.** `abrir-caso` es reentrante (dedup por sha vs log; no re-alta CRM). Sembrar desde varias fuentes = ejecutar otra vez con otra `--fuente`. Sin estado combinado. |
| D5 | **`entrevista`** | **Excluida** (ver §1). |
| D6 | **`init_caso.py`** | **Conservar + documentar.** Es el atajo ligero "solo esqueleto"; `abrir_caso` es el flujo completo. Sin disparador para borrarlo. Se documenta la relación en ambos docstrings + spec. |

---

## 3. Arquitectura

El cerebro `core/abrir_caso.py` **no cambia**. Todo el trabajo está en el orquestador CLI
`scripts/abrir_caso.py`, hoy con `drive_ev` cableado a fuego. Se separan las fases:

- **Compartidas (toda fuente, sin cambios de F1):** resolver identidad + colisión →
  `ensure_case` → gate CRM extrajudicial → reporte.
- **Central por fuente (NUEVO):** obtener + depositar + loguear.

### 3.1 Regla de custodia (D3)

| Fuente | Depósito | Evento forense lo emite |
|---|---|---|
| `drive_ev` | `pull_drive_ev` (rclone) | **orquestador** (F1, sin cambios) |
| `manual` | `intake_manual.extract_zip` (zip) o copia de árbol (carpeta) | **orquestador** (mismo camino genérico) |
| `whatsapp` | `whatsapp_intake.deposit_export` | **escritor nativo** (`upload_whatsapp` + dedup por hash de zip) |
| `email` | `email_export.export_label(..., case_id=...)` | **escritor nativo** (`upload_email` + SHA del disco, idempotente por Message-ID) |

### 3.2 Refactor mínimo (isolación)

Extraer la lógica genérica hoy inline en `main()` (F1) a un helper reutilizable por
`drive_ev` y `manual`:

```
_intake_generico(case_dir, case_id, fuente, subdir, dry_run) -> None
    # hash_tree_local(subdir) → plan_intake → reconcile (aborta si mismatch)
    # → append_event(evento_de_fuente, files con sha256)
```

Dispatch por fuente **antes** del helper:

- `drive_ev` → `pull_drive_ev(case_id, folder_id, team_id)` → `_intake_generico`
- `manual`   → `_depositar_manual(case_id, src)` (zip ⇒ `extract_zip`; carpeta ⇒ copytree a
  `04_Manual`) → `_intake_generico`
- `whatsapp` → leer bytes de `--src` → `deposit_export(case_id, rol, bytes, zip_name=...)` →
  reportar (NO `_intake_generico`, ya logueó el nativo)
- `email`    → `export_label(cuenta, label, dest=case/00_Input/03_Email, case_id=case_id)` →
  reportar (NO `_intake_generico`)

**Invariante:** cada fichero se loguea **una sola vez**. `whatsapp`/`email` no pasan por
`_intake_generico` (evita doble-log contra su manifest nativo).

---

## 4. Contrato CLI

```
python -m scripts.abrir_caso \
  --w-code W-XXXXXX --ciudad <C> --tipo-caso <T> --codigo-caso <cod> \
  --sufijo <s> --direccion "<dir>" \
  --fuente drive_ev|manual|whatsapp|email        (default drive_ev)
  # drive_ev:  --folder-id / --team-id           (F1, ya existen)
  # manual:    --src   <ruta local: carpeta o .zip>
  # whatsapp:  --src   <ruta .zip export>   --rol <uno de WHATSAPP_SUBDIRS>
  # email:     --cuenta <cuenta gmail>      --label <etiqueta>
  [--cuantia --crm api|skip --force --dry-run --yes]
```

**Validación temprana por fuente (fail-fast, antes de tocar disco):** exigir los flags de la
fuente elegida y **rechazar los ajenos** con exit 1 y mensaje claro (p. ej. `--rol` con
`--fuente email`). El `rol` de whatsapp se valida contra `config.WHATSAPP_SUBDIRS`; la ciudad
contra `core.ciudades.CIUDADES` (ya en F1).

Gate CRM, `--force`, `--dry-run`, `--yes`, `--crm api|skip` **sin cambios** (comunes).

---

## 5. Manejo de errores e idempotencia (por fuente)

| Situación | Comportamiento |
|---|---|
| `manual`: `--src` inexistente / zip corrupto | abortar antes de tocar nada (exit 1) |
| `manual`/`drive_ev`: mismatch de hash en reconcile | abortar **sin** escribir log, reportar diffs |
| `whatsapp`: export ya importado | `deposit_export` devuelve `skipped_dedup`; reportar, no abortar |
| `whatsapp`: `--rol` inválido | exit 1 con los válidos |
| `email`: etiqueta ya exportada / nada nuevo | `export_label` idempotente (salta Message-IDs); no emite evento si no hay nada |
| CRM caído / rechaza | Drive+intake completados; `referencia_crm` pendiente + TODO; exit 0 con warning (§9 F1) |
| Reejecución global | `ensure_case` reentrante; CRM no re-da de alta (§8 F1) |
| Caso prestado (lock §6) | guard §6 de los escritores nativos desvía a `_pendiente_checkin/` (conducta existente; para un caso recién abierto = `disponible`, no aplica) |

`--dry-run` para toda fuente: `manual` reporta el plan sin depositar; `whatsapp`/`email` no
ejecutan el escritor nativo (solo anuncian qué haría).

---

## 6. Seguridad y custodia (invariantes, heredados de F1 §10)

- Bytes en disco local / server-side; **nunca** por el chat.
- **SHA-256 obligatorio de todo lo depositado**, incluido el **manual** (hueco que F3 cierra).
- Crudo intacto (el `.zip` de origen no se borra; solo temporales de extracción si los hay).
- Nombres de fichero se preservan en `00_Input`.
- Docs/commits por `W-XXXXX`, sin PII (`docs/SEGURIDAD_DATOS.md`).
- `90_Notas personales/` intocable.

---

## 7. `init_caso.py` (parte C)

Sin cambio funcional. Añadir a los docstrings de `scripts/init_caso.py` y
`scripts/abrir_caso.py` una nota de relación:

> `init_caso` = **solo esqueleto** (`validate_case_id` + `ensure_case`), atajo ligero sin
> intake ni CRM. `abrir_caso` = **esqueleto + intake + CRM** en una pasada. Elegir según se
> quiera solo montar la carpeta o abrir el caso completo.

Registrar la decisión (conservar, sin disparador de deprecación) en `PLAN.md`.

---

## 8. Tests

- **Orquestador (integración con mocks; patrón F1 + Typer `CliRunner`):**
  - dispatch correcto por fuente.
  - `manual` (zip **y** carpeta) → depósito + hash + reconcile + evento `upload_manual` con
    sha256; estructura de subcarpetas preservada en el caso carpeta.
  - `whatsapp` → llama a `deposit_export` con `rol` correcto; **no** emite un segundo evento.
  - `email` → llama a `export_label` con `case_id` y `dest = .../00_Input/03_Email`; **no**
    emite un segundo evento.
  - validación de flags por fuente: falta el propio ⇒ exit 1; se pasa uno ajeno ⇒ exit 1.
  - `--dry-run` por fuente no deposita ni loguea.
  - `whatsapp` con export duplicado → `skipped_dedup`, exit 0.
- **No regresión:** el camino `drive_ev` de F1 intacto tras extraer `_intake_generico`
  (los tests F1 existentes deben seguir verdes).
- **Cerebro:** sin cambios ⇒ sin tests nuevos de `core/abrir_caso.py`.

---

## 9. Relación con el ecosistema

`abrir-caso` con fuente no-Drive **envuelve** el intake de esa fuente para el escenario "caso
nuevo". La skill **`intake-expediente`** se queda para su caso propio: **añadir** material a
un caso **ya existente** (el escenario "el WhatsApp/correo llega días después de abrir con el
Drive"). Ambos comparten el mismo cerebro y los mismos escritores nativos, así que el trabajo
de F3 sirve a los dos caminos. La sección "Relación con el ecosistema" formal en todas las
skills sigue siendo `docs/MEJORAS_FUTURAS.md` #50.

---

## 10. Fases de build (incremental, tests por paso)

1. Refactor no destructivo: extraer `_intake_generico` del `main()` F1; suite F1 verde.
2. Fuente `manual` (zip + carpeta) + evento `upload_manual` + validación de flags + tests.
3. Fuente `whatsapp` (delegación a `deposit_export`) + validación de `--rol` + tests.
4. Fuente `email` (delegación a `export_label`) + validación `--cuenta/--label` + tests.
5. Parte C: docstrings `init_caso`/`abrir_caso` + nota en `PLAN.md`.
6. Suite completa verde; PR con check `leak-scan`.
