# Plan — Subdivisión de `CASOS_ROOT` por ciudades

**Trazado:** 2026-05-12 (sesión 14, planificación).
**Estado:** plan aprobado, implementación pendiente.

---

## 1. Objetivo

Reorganizar `CASOS_ROOT` (hoy plano con los expedientes directamente bajo la raíz) a estructura `CASOS_ROOT / <Ciudad> / <expediente>`. Dejar el core preparado para un futuro segundo nivel `<Ciudad> / <Equipo> / <expediente>` sin necesidad de una segunda migración masiva. Operativa segura, reversible y auditada.

En el entorno productivo `CASOS_ROOT` apunta a `G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\CASOS` (configurado en `.env`). El plan trabaja contra `settings.casos_root`; no hay rutas hardcodeadas.

---

## 2. Inventario de expedientes existentes (2026-05-12)

| Expediente | Prefijo equipo | Ciudad inferida |
|---|---|---|
| `MaRS2 - Puerto Rico 2, 5 º 2 - (W-0470GM) - Negativa arras` | Ma | Madrid |
| `MaRS15 - Pedro Lain Entralgo 4 Chalet 4 - (W-02W4PJ) - Devolucion reserva` | Ma | Madrid |
| `MaRR2 - XXXX - (XXXX) - Bad debt` | Ma | Madrid |
| `BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU` | Ba | Barcelona |
| `SeRS6 - 393. Hacienda Vadillo - (W-02RRO3) - Bad debt` | Se | Sevilla |
| `SaRS1 - Castelar, 37-39, Santander - (SIN REFERENCIA) - Otros` | Sa | Santander |
| `_PLANTILLA` | — | (carpeta de sistema) |

---

## 3. Decisiones cerradas

| # | Punto | Decisión |
|---|---|---|
| 1 | Ámbito | Única jerarquía sobre `CASOS_ROOT`. No hay doble migración (local vs Drive). |
| 2 | Catálogo de ciudades | Las 7 ciudades de `_CIUDADES` en `streamlit_app.py`: Barcelona, Bilbao, Madrid, San Sebastián, Santander, Sevilla, Valencia. Extraer a `core/config/ciudades.py`. Sin botón "añadir nueva" — coherente con dar de alta tags y equipos en el mismo commit. |
| 3 | Forma canónica del nombre | Tal cual `_CIUDADES`, incluida la tilde en "San Sebastián". |
| 4 | Detección prefijo→ciudad | Derivada de `_EQUIPOS_POR_CIUDAD` mediante `ciudad_de_equipo(codigo)`. Una sola fuente de verdad. |
| 5 | Validación coherencia | Warning no bloqueante con motivo + registro en audit log. |
| 6 | Carpeta fallback | `_Sin clasificar` (guion bajo inicial → ordena primera). |
| 7 | Carpetas de sistema | Convención "prefijo `_` = no es ciudad". Aplicada a `_PLANTILLA`, `_Sin clasificar`, `_audit`. |
| 8 | Cambio post-alta | Permitido desde acción "Reasignar ciudad" en la UI del caso. Audit log + motivo obligatorio ≥10 caracteres. |
| 9 | Audit log | `CASOS_ROOT/_audit/relocations.jsonl`. JSONL append-only. Pestaña admin en Streamlit. |
| 10 | Migración inicial | Script Python en dos fases (`--plan` → CSV editable; `--apply` → ejecución con confirmación literal y rollback). Idempotente. |
| 11 | Refactor previo | Introducir `core/casos/case_locator.py` con tolerancia legacy. Refactor de call-sites antes de mover una sola carpeta. |

---

## 4. Fase 0 — Preparación

Rama: `feature/subdivision-ciudades`.

Extraer constantes desde `streamlit_app.py` a `core/config/ciudades.py`:

- `CIUDADES` (dict ciudad → tag_azul_crm).
- `EQUIPOS_POR_CIUDAD` (dict anidado).
- `EQUIPOS` (dict plano derivado).
- `ciudad_de_equipo(codigo: str) -> str | None`.
- `es_carpeta_de_sistema(nombre: str) -> bool` (regla `_`).

`streamlit_app.py` importa del nuevo módulo. Sin cambios funcionales en la UI.

Tests dedicados `tests/test_config_ciudades.py`: mapping, derivación prefijo→ciudad para los códigos vivos hoy, regla del guion bajo, idempotencia del catálogo.

**Criterio de aceptación:** suite completa verde tras el refactor.

---

## 5. Fase 1 — `case_locator`

Crear `core/casos/case_locator.py`. API mínima:

```python
def path_for(expediente_id: str) -> Path: ...
def path_for_ciudad(expediente_id: str, ciudad: str) -> Path: ...
def move_to_city(expediente_id: str, ciudad_destino: str, motivo: str, usuario: str) -> Path: ...
def list_cases(ciudad: str | None = None) -> Iterator[Path]: ...
def all_cities_present() -> list[str]: ...
```

`path_for` con **tolerancia legacy**: primero busca `<Ciudad>/<expediente>` leyendo metadato; si no existe, fallback a `<expediente>` en raíz. Permite mergear el refactor antes de migrar.

Tests `tests/test_case_locator.py`: caso con metadato ciudad, caso legacy sin metadato, caso en `_Sin clasificar`, caso inexistente (raises), composición para futuro nivel equipo (parametrizado, marcado `xfail`).

Refactor de call-sites (barrido y sustitución de construcciones tipo `settings.casos_root / case_id`):

- `core/case_manager.py`
- `core/sync_sudespacho.py`
- `scripts/init_caso.py`
- `scripts/sync_sudespacho.py`
- `scripts/bulk_pull_expedientes.py`
- `scripts/scheduled_sync.py`
- `tests/conftest.py` y tests dependientes

**Criterio de aceptación:** suite completa verde. Grep manual confirma cero accesos directos a `casos_root / <expediente>` fuera de `case_locator.py`.

---

## 6. Fase 2 — Campo `ciudad` en metadatos del caso

Añadir campo `ciudad` al frontmatter de `_caso.md`. Tipo string opcional, valores del catálogo o `"_Sin clasificar"`.

Modificar el flujo de alta de la UI Streamlit: el `nc_ciudad` que ya existe ahora se persiste en `_caso.md` además de su uso actual.

Validación blanda al crear: si `ciudad_de_equipo(codigo) != ciudad_seleccionada`, mostrar warning con confirmar/cancelar. Si confirma, persistir con flag `prefijo_coherente: false` y registrar entrada en `_audit/relocations.jsonl` con `operacion: alta_caso_incoherente`.

Tests: alta coherente, alta incoherente confirmada, alta cancelada por incoherencia.

**Criterio de aceptación:** crear un nuevo caso en local con la UI produce un `_caso.md` con `ciudad` rellenado y la carpeta queda directamente bajo `<Ciudad>/`.

---

## 7. Fase 3 — Acción "Reasignar ciudad" en UI

Botón en la pantalla de detalle del caso. Modal con: ciudad actual, selector destino, motivo obligatorio (≥10 caracteres).

Implementación: `case_locator.move_to_city(expediente_id, ciudad_destino, motivo, usuario)` que ejecuta atómicamente:

1. Mover carpeta.
2. Actualizar metadato `ciudad`.
3. Escribir audit log.
4. Rollback si falla algún paso.

Pestaña administrativa en Streamlit (visible sólo para Nikolai) que lee `relocations.jsonl` y muestra el histórico con filtros básicos.

Tests: reasignación exitosa, motivo vacío rechazado, rollback ante fallo simulado en la escritura del metadato.

**Criterio de aceptación:** reasignar un caso de Madrid a Barcelona desde UI mueve la carpeta, actualiza `_caso.md` y deja entrada en el log con todos los campos.

---

## 8. Fase 4 — Migración inicial

Script `scripts/migrate_to_city_structure.py` (Typer).

`--plan`: genera `_audit/migration_plan_<fecha>.csv` con todos los expedientes en raíz y su ciudad detectada. Columnas: `expediente | prefijo | ciudad_detectada | ciudad_final | accion | observaciones`.

Revisión manual en Excel del CSV.

`--apply <csv>`: lee, muestra resumen ("6 movimientos: 3 a Madrid, 1 a Barcelona, 1 a Sevilla, 1 a Santander; 0 a Sin clasificar; 0 ignorados"), exige confirmación literal (escribir `MIGRAR`), ejecuta `move_to_city` para cada fila, registra cada movimiento con `operacion: migracion_inicial`. Rollback si falla.

Pre-flight obligatorio: dump del estado pre-migración a `_audit/snapshot_pre_migration_<fecha>.json` con la ruta original de cada expediente. Permite reconstrucción manual en caso de catástrofe.

Idempotencia: re-ejecutar tras migración exitosa reporta "nada que migrar" para cada caso ya bajo subcarpeta-ciudad.

**Criterio de aceptación:** ejecución completa de los 6 casos. `CASOS_ROOT` queda con `Barcelona/`, `Madrid/`, `Santander/`, `Sevilla/`, `_PLANTILLA/`, `_audit/` y opcionalmente `_Sin clasificar/`. Pipeline FeesDefender (test E2E con un caso) sigue funcionando.

---

## 9. Fase 5 — Documentación

- Actualizar `STATUS.md` con la nueva estructura de directorio y el cierre de la migración.
- Actualizar `docs/ARQUITECTURA.md` con `case_locator` y la jerarquía `CASOS_ROOT/<Ciudad>/<expediente>`. Anotar que el segundo nivel `equipo` está preparado pero no activado.
- Actualizar `README.md`: ejemplos de paths corregidos.
- Memoria: actualizar `project_motor_honorarios.md` y crear `project_subdivision_ciudades.md` con resumen del cambio, fecha de migración, nota de que `case_locator` es la única fuente de paths.
- Si aparece algún callejón durante la implementación → entrada en `docs/DEAD_ENDS.md`.

---

## 10. Fase 6 — Verificación final

- Suite completa verde (objetivo: ~500 tests tras añadir los nuevos).
- Test E2E manual:
  - Alta de caso nuevo con la UI → carpeta en ciudad correcta, metadato correcto.
  - Reasignación → carpeta movida, log generado.
  - Re-ejecución del script de migración → idempotente.
- Script de verificación del filesystem post-migración: ninguna carpeta huérfana en raíz, todos los `_caso.md` con campo `ciudad` coherente con su ubicación.
- Commit final, push, cierre del hilo en `STATUS.md`.

---

## 11. Dependencias críticas

- Fase 1 (`case_locator`) **debe** mergearse antes de Fase 4 (migración). Si se ejecuta la migración sin el refactor, los pipelines rompen al primer acceso.
- Fase 2 (campo ciudad en metadatos) **debe** estar antes de Fase 3 (reasignación).
- Fases 5 y 6 son siempre lo último.

---

## 12. Estimación

Fases 0, 2, 3 y 4: entre media y una sesión cada una. Fase 1: dos sesiones (toca muchos call-sites y tests). Total estimado: 5-6 sesiones cowork.

---

## 13. Pre-condición para arrancar la implementación

Antes de tocar nada: copia de seguridad de `CASOS_ROOT` mediante snapshot manual del Shared Drive o rclone copy a una ubicación fría. No es estrictamente necesaria para fases 0-3 (no mueven ficheros), pero sí obligatoria antes de ejecutar `--apply` en Fase 4.
