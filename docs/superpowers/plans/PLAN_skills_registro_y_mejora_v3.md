---
estado: historico
dueño: Nikolai Tyukhay
---

# Plan de implementación — Skills: registro en expediente + mejora continua (v3, consolidado)

**Destinatario:** Claude Code (`C:\Users\tnm33\Dev\FeesDefender`).
**Origen:** análisis desde Cowork (solo lectura del repo).
**Fecha:** 2026-06-12. **Versión:** v3 — consolida registro de outputs (Parte I) y sistema de mejora continua (Parte II). Sustituye a v1 y v2.

## 1. Objetivo

Dos capacidades para las skills procesales del despacho:

- **Parte I — Registro:** que toda skill que genere un documento lo **guarde en la carpeta del expediente** y lo **registre en el fichero maestro** (`00_Input/_caso.md`), igual en E&V y en particulares.
- **Parte II — Mejora continua:** que cada skill **aprenda de su uso real** (telemetría, correcciones del letrado, resultado en sala) y proponga mejoras a su propio `SKILL.md`, respetando la frontera Cowork (captura/análisis) / Code (edición de la skill).

## 2. Decisiones cerradas

**Arquitectura y alcance**
- **Opción A:** helpers canónicos versionados en el repo (`.claude/skills/_shared/`), copiados a cada skill al empaquetar. Skills autónomas (PC y móvil).
- **Alcance:** skills procesales conscientes de expediente — `escritos-judiciales`, `preparacion-juicio-oral`, `cendoj-descarga`, `preparacion-audiencia-previa` — más alinear `preparacion-litigio-civil`. `docx/xlsx/pdf` no se tocan.
- **Modo por estructura, no por cliente:** existe `00_Input/_caso.md` → modo expediente estructurado (guarda + registra). Si no → modo ad-hoc (pregunta carpeta, sin registro).

**Escenarios de expediente (cubiertos por igual)**
- **Particulares reutilizan la estructura de E&V** (`CASO_SUBDIRS` + `00_Input/_caso.md`). Las skills no los distinguen; solo difiere quién abre el expediente.

**Cuestiones abiertas resueltas (recomendación adoptada; revisable)**
1. **`preparacion-juicio-oral`:** copiar la skill instalada a `.claude/skills/preparacion-juicio-oral/` y versionarla como fuente única.
2. **Jurisprudencia CENDOJ:** subcarpeta dedicada `05_Procedimiento/Jurisprudencia/`.
3. **`PREPARACION_X.md` / `HECHOS_X.md`:** en `02_Analisis/`.
4. **Empaquetado `.skill`:** script `scripts/package_skill.py` (zip dir → `.skill`) + instalación manual vía Configuración → Capacidades.
5. **Particulares:** discriminador `tipo_expediente: ev | particular` en `_caso.md`; frontmatter mínimo sin campos E&V; `00_Input` sin subcarpetas E&V (solo intake manual); terminología **propietario/buscador solo en intermediación** (en compraventa/arrendamiento entre particulares, roles contractuales propios; la perspectiva procesal actora/demandada siempre es independiente).

**Mejora continua**
- **Señal:** delta de edición (borrador vs versión `_FIRMADO`) + checklist post.
- **Cadencia del cierre de bucle:** por umbral (5+ usos reales con su post).
- **Logs:** central en repo `data/_skill_logs/<skill>/` (fuera del bundle `.skill`).

## 3. Escenarios de expediente

| | A — E&V (FeesDefender) | B — Cliente particular |
|---|---|---|
| Cliente | EV MMC SPAIN / E&V Spain | Particular |
| Estructura | `CASO_SUBDIRS` | **La misma** `CASO_SUBDIRS` |
| Maestro | `00_Input/_caso.md` | `00_Input/_caso.md` (mínimo, `tipo_expediente: particular`) |
| Apertura | `core/case_manager.py` (intake Drive E&V) | `preparacion-litigio-civil` (scaffolding alineado, sin E&V) |
| Guardado + registro | Sí | Sí |
| Subcarpetas E&V de `00_Input` | Se usan | No se crean (solo intake manual) |

## 4. Anclajes verificados

- Skills editables: `C:\Users\tnm33\Dev\FeesDefender\.claude\skills\` (`escritos-judiciales` = solo `SKILL.md`; `cendoj-descarga`, `preparacion-litigio-civil`, `docx/pdf/xlsx`, `viabilidad-prerelleno`).
- `preparacion-audiencia-previa` en `_skills_drafts/` (con `scripts/`, `references/`, `templates/`, `logs/`); su `registrar_outputs.py` es el patrón de referencia. `preparacion-juicio-oral` **no está en el repo**.
- `core/config.py` es E&V por diseño (`POSICION_ACTORA/DEFENSIVA`, `CLIENTES_PROPIOS_EV`). Abrir un particular exige un camino sin esos campos.
- `CASO_SUBDIRS` = `00_Input, 01_Procesado, 02_Analisis, 03_Decision, 04_Output predemanda, 05_Procedimiento, 06_Anonimizado, 07_AI cowork, 90_Notas personales`.
- Maestro `00_Input/_caso.md` con `## Navegación` (creada por `case_manager` ~L119); escritura atómica `_atomic_write_caso_md`.
- `05_Procedimiento` hoy inerte (lo crea el scaffolding, lo barre `linker.py`; nadie escribe).
- AP/juicio ya se auto-instrumentan (`logs/uso.jsonl`, checklists pre/post, revisión programada, cierre a 5+).

---

# PARTE I — Guardado y registro

## 5. Helper canónico de registro

- **Ruta:** `.claude/skills/_shared/registrar_outputs.py`. CLI: `python registrar_outputs.py <case_dir> <outputs.json>`.
- **`outputs.json`** (lista de objetos):
  ```json
  [{"fichero":"DEMANDA_W-XXXXXX.docx","tipo":"demanda","perspectiva":"actora",
    "destino":"05_Procedimiento","fuentes":["informe_viabilidad","encargo"],
    "wikilink":"DEMANDA_W-XXXXXX","estado":"borrador","meta":{"roj":"","ecli":""}}]
  ```
  - `tipo`: `demanda|contestacion|reconvencion|recurso|requerimiento|escrito_tramite|minuta_ap|solicitud_prueba|conclusiones|interrogatorio|orden_vista|cuadro_hechos|jurisprudencia`.
  - `destino`: subcarpeta de `CASO_SUBDIRS`; validar; **rechazar `90_Notas personales`**.
  - `wikilink`: si falta, *stem* del fichero.
- **Comportamiento:** (1) por cada `destino`, crear/actualizar `<case>/<destino>/_index.md` (append idempotente por fichero); (2) añadir wikilinks a `## Navegación` de `_caso.md` (idempotente; crear sección si falta; **no tocar frontmatter**); (3) sin `_caso.md` → solo manifiesto + aviso stderr.
- **Robustez:** idempotente; escritura atómica UTF-8 sin BOM; guardia `90`; best-effort (no invalida el `.docx`; salida ≠ 0 = aviso).

## 6. Mapa de carpeta destino

| Tipo | Destino |
|---|---|
| demanda, contestación, reconvención, recurso, escrito de trámite | `05_Procedimiento` |
| requerimiento extrajudicial | `04_Output predemanda` |
| minuta AP, solicitud de prueba, conclusiones, interrogatorios, orden de vista, cuadro de hechos | `05_Procedimiento` |
| jurisprudencia (PDF CENDOJ) | `05_Procedimiento/Jurisprudencia` |

Cada skill: salida primaria a `<case>/<destino>/` + copia a `outputs/` (para `present_files`).

## 7. Detección de expediente (Fase 0)

`escritos-judiciales` y `preparacion-juicio-oral` ganan Fase 0 (como AP): localizar `00_Input/_caso.md`. Existe → estructurado (guarda + registra). No existe → ad-hoc (pregunta carpeta, sin registro).

## 8. Cambios por skill (Parte I)

- **`escritos-judiciales`:** crear `scripts/registrar_outputs.py`; en `SKILL.md`, Fase 0 + sección «Guardado y registro» (salida a `<case>/<destino>/`, copia a `outputs/`, invocación del helper). Documentar modo ad-hoc.
- **`cendoj-descarga`:** crear `scripts/registrar_outputs.py`; Paso 7-bis de registro (`tipo: jurisprudencia`, `fuentes:[ROJ,ECLI]`, destino `05_Procedimiento/Jurisprudencia`).
- **`preparacion-juicio-oral`** (tras versionarla, #1): generadores escriben en `<case>/05_Procedimiento/` y registran cada `.docx`.
- **`preparacion-litigio-civil` (escenario B):** sustituir `scaffold_expediente.py` por scaffolding alineado a `CASO_SUBDIRS` + `_caso.md` mínimo (`tipo_expediente: particular`, frontmatter sin E&V, `## Navegación` vacía); `00_Input` solo intake manual. En modo estructurado ya existente, no recrear; ubicar maestros en `02_Analisis/`. **Función común de scaffolding** compartida con el core (E&V) para que ambos produzcan el mismo árbol y el mismo formato de `_caso.md`.

## 9. Sincronización y empaquetado

- `scripts/sync_skill_helpers.py`: copia los `_shared/*.py` a `scripts/` de cada skill objetivo y a AP; `tests/test_skill_helpers_sync.py` exige copias byte-idénticas.
- Migrar AP al `registrar_outputs.py` canónico.
- `scripts/package_skill.py` (#4): empaqueta tras el `sync`.

## 10. Core (track no bloqueante)

Promover a `docs/MEJORAS_FUTURAS.md`: que el core reconozca `<subdir>/_index.md` y resuelva los wikilinks de `## Navegación` para todos los tipos.

---

# PARTE II — Sistema de mejora continua

Generaliza la auto-instrumentación de AP/juicio a todas las skills procesales. **Captura y análisis = Cowork; edición del `SKILL.md` = Code.** El artefacto de *handoff* es un informe de mejora por skill.

## 11. Componentes

**11.1 Telemetría de uso — helper bundled `_shared/registrar_uso.py`.**
- CLI: `python registrar_uso.py <skill> <ref> <accion> [--archivos ...] [--metricas '<json>']`.
- Escribe JSONL `{ts(ISO-UTC), skill, version, ref, accion, archivos, metricas}`.
- **Resolución del directorio de logs:** variable de entorno `FEESDEFENDER_SKILL_LOGS` → por defecto `<repo>/data/_skill_logs/<skill>/`. Si no resuelve (p. ej. móvil), *fallback* portable a `logs/` de la skill. Best-effort: si falla, stderr y nunca rompe la generación.
- Inyectar `version` desde el frontmatter del `SKILL.md` (requiere campo `version`, ver 11.6).
- Generalizar a `escritos-judiciales` y `cendoj-descarga` (AP/juicio ya lo tienen → migrar a este helper común).

**11.2 Delta de edición — `scripts/capturar_delta.py` (ejecuta Cowork).**
- Convención: la versión definitiva se guarda como `<NOMBRE>_FIRMADO.docx` en la misma carpeta destino.
- El script extrae texto de borrador y `_FIRMADO` (python-docx), calcula diferencias a nivel de párrafo (difflib) y escribe `data/_skill_logs/<skill>/<ref>_delta.md` con las **correcciones del letrado** (añadido / suprimido / reescrito).
- Es la señal más rica: cada reescritura manual se convierte en dato. **Contiene texto del escrito → material sensible**: vive en el store central del repo, nunca se empaqueta en `.skill`, nunca toca `90_Notas personales`.

**11.3 Checklists pre/post — generalizados.**
- `pre`: objetivo, frentes, riesgos, prueba clave → `<ref>_pre.jsonl` al iniciar.
- `post`: qué fijó el juez, prueba admitida/inadmitida, pregunta no prevista, valoración → `<ref>_post.jsonl` tras el acto/presentación.

**11.4 Revisión programada (skill `schedule`).**
- Al generar un output con horizonte procesal, emitir descriptor de tarea y programar: AP/juicio → `fecha_acto + N días`; escritos → `presentación + N días` o al detectar `_FIRMADO`. La tarea pide a Cowork rellenar el `post` y correr `capturar_delta.py`.

**11.5 Cierre del bucle — `scripts/motor_mejora.py` (ejecuta Cowork, por umbral).**
- Disparo: una skill acumula ≥5 entradas en `uso.jsonl` con su `<ref>_post` correspondiente.
- Agrega uso + deltas + post; detecta patrones recurrentes (jurisprudencia que el juez rechaza, cláusulas siempre reescritas, alegaciones que no cuelan, prueba que se inadmite).
- Produce `data/_skill_logs/<skill>/MEJORAS_<skill>.md`: propuestas concretas de cambio al `SKILL.md`, **cada una anclada al dato que la motiva** (referencias a líneas de log/delta).
- *Handoff:* Code revisa el informe, aplica las mejoras aprobadas al `SKILL.md`, sube `version` y anota el changelog.

**11.6 Versionado y trazabilidad.**
- Añadir a cada `SKILL.md` frontmatter `version: X.Y` y una sección `## Changelog`.
- Cada mejora promovida cita su evidencia (log/delta). Da auditabilidad (encaja con «El Auditor» y con la cultura source-locked).

## 12. Frontera Cowork / Code

| Acción | Quién |
|---|---|
| Telemetría, checklists, delta, informe `MEJORAS_<skill>.md` | Cowork (helpers + scripts de análisis) |
| Editar `SKILL.md`, subir `version`, changelog, sincronizar helpers, empaquetar | Claude Code |

---

## 13. Plan de ejecución por fases

| Fase | Trabajo | Criterio de aceptación |
|---|---|---|
| 1 | `_shared/registrar_outputs.py` + tests | Tests verdes (idempotencia, _caso.md ausente, Navegación, rechazo 90, destino inválido, atómica) |
| 2 | `sync_skill_helpers.py` + drift test; migrar AP | Copias byte-idénticas; AP registra igual |
| 3 | `escritos-judiciales`: Fase 0 + guardado/registro | Demanda en `05_Procedimiento`, `_index.md`, Navegación, `outputs/` |
| 4 | `cendoj-descarga`: Paso 7-bis (jurisprudencia) | PDF registrado con ROJ/ECLI en `05_Procedimiento/Jurisprudencia` |
| 5 | Versionar `preparacion-juicio-oral` + aplicar registro | Conclusiones/interrogatorios/orden de vista registrados |
| 6 | `preparacion-litigio-civil`: scaffolding alineado + `_caso.md` mínimo (escenario B) + función común con core | Abrir caso particular crea `CASO_SUBDIRS` + maestro; escrito se guarda y registra igual que E&V |
| 7 | `package_skill.py` + e2e (E&V y particular) | e2e OK en ambos escenarios |
| 8 | Core follow-up a `MEJORAS_FUTURAS.md` | Entrada registrada |
| 9 | `_shared/registrar_uso.py` + `version`/changelog en SKILL.md + generalizar a escritos/cendoj | Cada generación deja línea en `data/_skill_logs/<skill>/uso.jsonl` |
| 10 | `capturar_delta.py` + convención `_FIRMADO` | Delta borrador↔firmado en `<ref>_delta.md` |
| 11 | Checklists pre/post generalizados + revisión programada | Tarea de revisión creada al generar; `pre/post.jsonl` poblados |
| 12 | `motor_mejora.py` (umbral 5+) → `MEJORAS_<skill>.md` + handoff a Code | Informe generado con propuestas ancladas a datos |
| 13 | Gobernanza: changelog + flujo de aplicación por Code | `SKILL.md` versionados; primer ciclo de mejora cerrado |

Orden: Parte I (1→8) antes que Parte II (9→13). Fases 3 y 4 independientes tras 1–2. Fase 5 bloqueada hasta resolver #1.

## 14. Pruebas

- **Unitarias `registrar_outputs`:** idempotencia, `_caso.md` ausente, creación de Navegación, rechazo `90`, destino inválido, escritura atómica UTF-8.
- **Unitarias `registrar_uso` / `capturar_delta`:** línea JSONL bien formada; resolución de `FEESDEFENDER_SKILL_LOGS` y fallback; delta detecta párrafos añadidos/suprimidos/reescritos.
- **e2e ambos escenarios:** E&V (`W-EJEMPLO`) y particular: generar escrito → verificar carpeta, `_index.md`, Navegación, `outputs/`; luego simular `_FIRMADO` → delta → checklist post → (forzando 5 usos) informe de mejora.

## 15. Riesgos y mitigaciones

- **Corromper `_caso.md`** → escritura atómica + idempotencia + no tocar frontmatter + tests.
- **Escribir en `90_Notas personales`** → guardia explícito (registro y delta).
- **Divergencia de copias de helpers** → test de sincronía byte a byte.
- **`preparacion-juicio-oral` sin fuente** → bloquea Fase 5 hasta versionarla.
- **Dos caminos de apertura (core E&V vs skill particular) que divergen** → función común de scaffolding + formato único de `_caso.md`.
- **Datos sensibles en logs/deltas** → store central en repo, nunca en `.skill`, tratados como material de expediente.
- **Confusión con genéricas** → `docx/xlsx/pdf` no se tocan; `escritos-judiciales` genera con Node inline.

## 16. Cuestiones abiertas restantes

- **`N` días de la revisión programada** por tipo de acto (sugerencia: AP +3, juicio +7, escritos +15). Confirmar.
- **Ubicación del `MEJORAS_<skill>.md`**: store central (`data/_skill_logs/<skill>/`) vs `docs/` del repo para que Code lo consuma. Sugerencia: store central + enlace desde `docs/`.
- **Privacidad de deltas**: ¿anonimizar el `<ref>_delta.md` (reusando `core/anon`) antes de archivarlo, o mantenerlo como material de expediente sin anonimizar? Sugerencia: sin anonimizar (es work-product interno), pero excluido del empaquetado.

## 17. Checklist final para Code

- [ ] `_shared/registrar_outputs.py` (guardia 90, validación destino, idempotencia, atómica) + tests verdes.
- [ ] `sync_skill_helpers.py` + drift test; AP migrada.
- [ ] `escritos-judiciales`: Fase 0 + guardado + registro + copia a `outputs/`.
- [ ] `cendoj-descarga`: Paso 7-bis (jurisprudencia en subcarpeta dedicada).
- [ ] `preparacion-juicio-oral` versionada y con registro.
- [ ] `preparacion-litigio-civil`: scaffolding `CASO_SUBDIRS` + `_caso.md` mínimo; función común con core; maestros en `02_Analisis/`.
- [ ] `package_skill.py`; `.skill` regeneradas; e2e E&V y particular OK.
- [ ] `_shared/registrar_uso.py`; `version`+changelog en cada `SKILL.md`; logs en `data/_skill_logs/`.
- [ ] `capturar_delta.py` + convención `_FIRMADO`.
- [ ] Checklists pre/post generalizados + revisión programada (`schedule`).
- [ ] `motor_mejora.py` (umbral 5+) → `MEJORAS_<skill>.md` + flujo de aplicación por Code.
- [ ] Entrada en `docs/MEJORAS_FUTURAS.md` (reconocimiento de manifiesto/wikilinks por el core).
