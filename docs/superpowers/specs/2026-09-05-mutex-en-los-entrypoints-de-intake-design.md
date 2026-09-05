---
tipo: spec
estado: en-revision
creado: 2026-09-05
objeto: "MEJORAS #126 — tres entrypoints de intake escriben en el expediente sin pedir el mutex del caso"
rev: "1"
---

# El mutex del caso lo pide quien escribe, no quien lo recuerda

> **Rev. 1 (2026-09-05).** Fila #17 de `PLAN.md`, promovida de `MEJORAS #126` por disparador real
> (apertura de W-02X1WJ, 2026-09-01). Alcance **recortado a tres** de los cuatro entrypoints que la
> entrada nombra: `scripts/crm_ficha.py` es de la sesión hermana «Completar fichas de
> colaboradores» (reparto de Nikolai del 2026-09-05) y queda fuera con nombre. Radio de daño:
> **decide quién puede escribir sobre el árbol del caso → dos rondas** (`CLAUDE.md` §«Cuántas
> rondas»): esta sobre el diseño, otra sobre el diff.

## 1. El problema, medido

El mutex de sesión existe, tiene cuatro rondas de revisión y 17 mutantes, y lo piden **tres**
entrypoints: `scripts/abrir_caso.py`, `scripts/sala_maquina.py` y, desde el PR #290,
`scripts/migrar_layout_intake.py`. Todo lo demás que escribe en el árbol del caso entra sin
llamar:

| Entrypoint | Escribe en | Sin mutex desde | Por qué duele |
|---|---|---|---|
| `scripts/export_label_emails.py` | `00_Input/<lote_email>/`, `_intake_hashes.json`, `_exported_ids.json`, `_intake_log.jsonl` | siempre | escribe en `00_Input` mientras `sala_maquina apply` lo lee durante una hora de OCR: el escenario de `[APER-39]`, ~1h40 de OCR repetido más huérfanos (medido) |
| `scripts/atomize_emails.py` | `01_Procesado/Emails/`, `_intake_log.jsonl` | siempre | ídem: la atomización corre sobre el mismo `00_Input` que el OCR está inventariando |
| `scripts/sync_sudespacho.py` (`pull`, `intake_judicial`, `sync_all`) | `00_Input/05_CRM/<rama>/`, `_caso.md`, `_intake_hashes.json`, `_intake_log.jsonl` | siempre | `[APER-37]` manda ejecutar `pull` **justo antes** del `apply`; y `sync_all` barre TODOS los casos, incluido el que otra sesión tiene tomado |

En W-02X1WJ la regla la sostuvo a mano quien ejecutaba: retuvo el export y la atomización tres
veces mientras corría el OCR. Y el contraste que lo hace irrefutable: cuando retuvo el pull de
`--fuente drive_ev`, el mutex lo habría bloqueado igual con `CaseBusy` — la disciplina manual
solo era *load-bearing* en los caminos que no lo tienen.

**Y el residuo de la R2 de `#149` (H-01):** la migración adquiere el mutex, pero `email_export` y
`sync_sudespacho` no, así que su exclusión es **unilateral**: un `export` concurrente puede seguir
cambiando `_exported_ids.json` entre la relectura y el `unlink()`. Esta pieza es la que cierra
ese hueco por el otro lado.

## 2. La frontera

**Todo entrypoint que escriba bajo el árbol de un caso con W-code sostiene el mutex de ese caso
durante toda la escritura, y aborta limpio (código 2, cero bytes) si otro proceso lo tiene.** Sin
W-code no hay namespace: se avisa y se sigue (trinquete E2 de `tests/test_entrypoints_mutex.py`:
cerrar en falso una vía que hoy funciona le rompe el día al equipo).

Lo que NO cambia: `core/casos/case_mutex.py` y `core/casos/mutex_sesion.py` no se tocan (cuatro
rondas, 17 mutantes; esta pieza **añade adquirentes**, no primitivas). `core/` sigue **exigiendo**
y nunca adquiriendo (guard E5).

## 3. Diseño

### 3.1. Un solo sitio para adquirir desde un CLI: `scripts/_mutex_cli.py`

Hoy hay **tres** copias casi iguales de «sostener el mutex desde un entrypoint»:
`sala_maquina._bajo_mutex(ws, case_id)` (con `CaseWorkspace`), `migrar_layout_intake._bajo_mutex`
(con `case_id`, resolviendo el W-code de `_caso.md`) y la que `abrir_caso` hace en línea. Tres
copias es una de más para una pieza que decide quién escribe: la cuarta y quinta irían con la
misma prosa y sus propias divergencias. Se extrae a un módulo de `scripts/` (no de `core/`, por
E5):

```python
# scripts/_mutex_cli.py
@contextlib.contextmanager
def sostener(case_id: str, *, avisar: Callable[[str], None]) -> Iterator[SesionMutex | None]:
    """Sostiene el mutex del caso `case_id` durante el bloque.
    - W-code: `meta.id_go` del `_caso.md` (`w_code_de(case_id)`); si el caso no lo declara,
      `avisar(...)` con el texto canónico y `yield None` (trinquete E2).
    - `CaseBusy` -> se relanza como `CasoOcupado(RuntimeError)` con el mensaje de la primitiva
      (quién lo tiene, desde cuándo), para que cada CLI lo convierta en SU código de salida 2.
    - `MutexPerdido` a mitad -> se relanza como `MutexPerdidoEnCli` con el aviso de que puede
      haber trabajo a medio publicar (mismo texto que `sala_maquina`).
    - `ahora_fn=now_iso_utc` SIEMPRE (guard E4 por AST; un reloj naive se lee en hora local).
    """

def w_code_de(case_id: str) -> str | None: ...   # movido desde migrar_layout_intake
```

`migrar_layout_intake` pasa a usarlo (su `_bajo_mutex` y `_w_code_de` se retiran).
`sala_maquina` **no cambia**: ya tiene el `CaseWorkspace` resuelto y su `_bajo_mutex` toma el
W-code de ahí; unificarlo obligaría a releer `_caso.md` donde el resolver ya lo hizo. Se declara
como la única copia que queda, y por qué.

### 3.2. Los tres entrypoints

| Entrypoint | Dónde se adquiere | Qué queda dentro | Qué queda fuera |
|---|---|---|---|
| `export_label_emails.main` | tras `resolve_ref(args.ref)`, alrededor de `export_label(...)` | la exportación entera (descarga, escritura del lote, índices, M9, traza) | el parseo de argumentos y el informe final |
| `atomize_emails.main` con `--ref` | alrededor de `P.atomize_case(args.ref)` + `sellar_entrega` | atomización y sellado | la rama `--src/--out` (sin caso: no hay qué sostener; se **avisa** de que no va bajo mutex) |
| `sync_sudespacho pull` | desde `ensure_case(...)` hasta `_siguiente_paso` | `ensure_case`, `register_expediente`, `pull_expediente_v2` | la validación de referencia CRM (solo lee el CRM) puede ir dentro sin coste; se deja dentro por simplicidad |
| `sync_sudespacho intake_judicial` | ídem, alrededor de `ensure_case` → `intake_demanda_contestacion` | todo lo que escribe | — |
| `sync_sudespacho sync_all` | **por caso**, dentro del bucle | el `pull_expediente_v2` de cada expediente del caso | un `CasoOcupado` **no aborta el barrido**: el caso se salta, se anota en `bloqueados_por_mutex` y se resume al final, como hoy los `blocked_legacy_v1` |

`ensure_case` **exige** el mutex en modo `v1` (E3): con el mutex ya sostenido por el CLI, la
capa reentrante lo une; sin él, la exigencia sigue siendo lo que es hoy. No cambia.

**Código de salida:** `CasoOcupado` → **2** en `export_label_emails`, `atomize_emails`, `pull` e
`intake_judicial` (el mismo que `sala_maquina` y `migrar_layout_intake`; distinto del 1 de «hubo
errores»); en `sync_all`, 0 si el barrido terminó, con el caso saltado en el resumen. **Cero
bytes**: el mutex se pide **antes** de la primera escritura, no después de `ensure_case`.

### 3.3. Lo que no se toca, con nombre

- `scripts/crm_ficha.py`: de la sesión hermana. Queda en `MEJORAS #126` como cuarto entrypoint
  pendiente, con la frase exacta: «se cierra cuando la hermana cierre la acción 8».
- `core/email_export.py`, `core/email_atomize/pipeline.py`, `core/sync_sudespacho.py`: `core/`
  exige, no adquiere (E5). Ningún cambio.
- `streamlit_app.py`: la UI llama a estos motores del core, no a los scripts; si adquiere, lo
  hace por su propio camino y no es objeto de esta pieza. Se anota como cobertura ausente.

## 4. Mutantes y tests (`tests/test_entrypoints_mutex.py`, fronteras E7-E12)

| # | Test | Qué debe pasar |
|---|---|---|
| E7 | otro proceso tiene el caso (`case_mutex.adquirir(W)`) y se invoca `export_label_emails.main(["--ref", W, ...])` con `export_label` **espiado** | código 2, `export_label` NO llamado, árbol byte a byte igual, mensaje con «ocupado»/`CASE_BUSY` |
| E8 | ídem `atomize_emails.main(["--ref", W])` con `P.atomize_case` espiado | ídem |
| E9 | ídem `sync_sudespacho pull --case <cid> --expediente 1` con `pull_expediente_v2` espiado y `ensure_case` espiado | código 2, **ninguno** de los dos llamado (cero bytes: el mutex va antes de `ensure_case`) |
| E10 | `sync_all` con dos casos, uno tomado por otro proceso | el tomado se salta y se resume; el otro se sincroniza; código 0 |
| E11 | `atomize_emails --src/--out` sin caso | aviso «no va bajo el mutex» y sigue |
| E12 | cada entrypoint sostiene el mutex **durante** la escritura: el espía del motor comprueba `mutex_sesion.vigente(CaseRef(w_code=W)) is not None` cuando lo llaman, y `None` al terminar | así se prueba la frontera «durante toda la escritura», no solo «antes» |
| E4 (ampliado) | `parametrize` con `scripts/_mutex_cli.py`, `scripts/migrar_layout_intake.py` y los tres módulos nuevos | `ahora_fn=now_iso_utc` por AST |
| E13 | **dos procesos reales** (`subprocess`) lanzan `atomize_emails --ref W` sobre el mismo caso con un motor que duerme 2 s (inyectado por variable de entorno de test) | exactamente uno termina 0 y el otro 2; ninguno deja trabajo a medias (condición de cierre literal de `MEJORAS #126`) |

**Mutantes, uno por entrypoint y uno por frontera:** retirar el `with` en cada uno de los cinco
subcomandos (E7-E10 en rojo); adquirir DESPUÉS de `ensure_case` en `pull` (E9 en rojo por bytes
escritos); tratar `CasoOcupado` en `sync_all` como abort del barrido (E10 en rojo); pasar
`now_iso` (E4 en rojo); `w_code_de` devolviendo `None` siempre (E7 pasa a «avisa y sigue» y E12
muere).

## 5. Alcance explícito

- **Toca:** `scripts/_mutex_cli.py` (nuevo), `scripts/export_label_emails.py`,
  `scripts/atomize_emails.py`, `scripts/sync_sudespacho.py`, `scripts/migrar_layout_intake.py`
  (usa el helper), `tests/test_entrypoints_mutex.py`, `docs/RUNBOOK_APERTURA_EXPEDIENTE.md`
  (`[APER-37]`/`[APER-39]`: la advertencia deja de ser prosa), `MEJORAS #126`, `PLAN.md` fila #17.
- **No toca:** `core/casos/*`, `core/` en general (E5), `scripts/crm_ficha.py` (hermana),
  `scripts/sala_maquina.py`, `streamlit_app.py`.
- **No cubre:** exclusión entre máquinas (el mutex es por máquina y el canon vive en Drive: eso
  es el lock de `_caso.md` del checkout, otra pieza); la UI.

## 6. Lo que esta rev. no sabe

Cuántas veces un `sync_all` real se ha cruzado con un `apply`: no está medido. Si `ensure_case`
en modo `libre` escribe antes de que un CLI pueda adquirir (hoy `pull` llama a `ensure_case`
primero; el diseño mueve el mutex delante, y la R1 debe comprobar que no queda ninguna escritura
por delante del `with`).
