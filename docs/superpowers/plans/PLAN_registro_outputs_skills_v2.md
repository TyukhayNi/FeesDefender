---
estado: historico
dueño: Nikolai Tyukhay
---

# Plan de implementación — Registro de outputs de skills en el expediente (v2)

**Destinatario:** Claude Code (edición de código y skills en `C:\Users\tnm33\Dev\FeesDefender`).
**Origen:** análisis desde Cowork (solo lectura del repo).
**Fecha:** 2026-06-12. **Versión:** v2 — incorpora la decisión sobre clientes particulares.

## 1. Objetivo

Que toda skill que genere un documento (escrito, soporte de vista, jurisprudencia) **guarde el output en la carpeta correspondiente del expediente** y **lo registre en el fichero maestro del caso**, replicando el mecanismo que ya funciona en `preparacion-audiencia-previa`. Aplica por igual a expedientes E&V y de clientes particulares.

Resultado esperado tras la ejecución:

1. Una rutina de registro **única y generalizada**, mantenida en el repo y copiada (idéntica) dentro de cada skill objetivo.
2. `escritos-judiciales`, `cendoj-descarga` y `preparacion-juicio-oral` guardan en la carpeta del caso y registran el output.
3. `preparacion-litigio-civil` deja de crear una estructura paralela y abre expedientes de particulares con **la misma estructura que E&V** (`CASO_SUBDIRS`).
4. Un guardia de sincronización que impide que las copias del helper diverjan.

## 2. Decisiones tomadas (cerradas)

- **Arquitectura (Opción A):** helper canónico versionado en el repo, copiado a `scripts/` de cada skill al empaquetar. Las skills siguen siendo autónomas (PC y móvil).
- **Alcance:** solo skills procesales conscientes de expediente — `escritos-judiciales`, `preparacion-juicio-oral`, `cendoj-descarga` — más alinear `preparacion-litigio-civil`. Las skills genéricas `docx/xlsx/pdf` **no se tocan** (son motor de formato).
- **Modo por estructura, no por cliente:** si existe `00_Input/_caso.md` → **modo expediente estructurado** (guarda en carpeta + registra automático). Si no → modo ad-hoc (pregunta carpeta destino, sin registro). Esto reemplaza la etiqueta «modo FeesDefender / E&V» de la skill de AP, que ataba el comportamiento a que el cliente fuera E&V.
- **Clientes particulares (no E&V):** reutilizan **la misma estructura de expediente que E&V** (`CASO_SUBDIRS` + `00_Input/_caso.md`) y, por tanto, también se benefician del guardado + registro. La única diferencia es el **origen del expediente** (§4.4-D).

## 3. Escenarios de expediente (los dos casos a cubrir)

| | Escenario A — E&V (FeesDefender) | Escenario B — Cliente particular |
|---|---|---|
| Cliente | EV MMC SPAIN, S.L.U. / E&V Spain | Particular (p. ej. cliente ruso/ex-URSS) |
| Estructura de carpetas | `CASO_SUBDIRS` | **La misma** `CASO_SUBDIRS` |
| Fichero maestro | `00_Input/_caso.md` | `00_Input/_caso.md` (versión mínima) |
| Quién abre el expediente | `core/case_manager.py` (intake Drive E&V, cliente propio EV) | `preparacion-litigio-civil` (scaffolding alineado, sin intake E&V) |
| Guardado + registro de outputs | Sí (automático) | Sí (automático) |
| Subcarpetas E&V de `00_Input` (p. ej. `01_drive_ev`) | Se usan | Quedan vacías / no aplican (cuestión abierta #5) |

Las skills **no necesitan distinguir A de B**: ambas tienen `00_Input/_caso.md` y `CASO_SUBDIRS`, así que el guardado y el registro son idénticos. La distinción solo importa en el momento de **abrir** el expediente.

## 4. Anclajes verificados (no asumir, ya comprobado)

- Skills editables en `C:\Users\tnm33\Dev\FeesDefender\.claude\skills\`: `escritos-judiciales` (solo `SKILL.md`), `cendoj-descarga`, `preparacion-litigio-civil`, `docx`, `pdf`, `xlsx`, `viabilidad-prerelleno`.
- `preparacion-audiencia-previa` vive en `_skills_drafts/preparacion-audiencia-previa/` (con `scripts/`, `references/`, `templates/`, `assets/`, `evals/`, `logs/`) y su bundle `.skill`.
- **`preparacion-juicio-oral` NO está en el repo** (solo en la caché instalada). → cuestión abierta #1.
- **El sistema FeesDefender es E&V por diseño:** `core/config.py` ata cliente, posición procesal (`POSICION_ACTORA = "Engel reclama"`, `POSICION_DEFENSIVA = "Engel es demandado"`) y `CLIENTES_PROPIOS_EV` a Engel & Völkers. Abrir un expediente de **particular** requiere un camino que **no** dependa de esos campos E&V.
- Estructura canónica del caso: `core/config.py → CASO_SUBDIRS` = `00_Input, 01_Procesado, 02_Analisis, 03_Decision, 04_Output predemanda, 05_Procedimiento, 06_Anonimizado, 07_AI cowork, 90_Notas personales`.
- Fichero maestro: `00_Input/_caso.md`, con sección `## Navegación` (la crea `core/case_manager.py`, línea ~119). Escritura atómica del maestro vía `_atomic_write_caso_md`.
- `05_Procedimiento` está hoy **inerte**: lo crea el scaffolding y lo barre `core/linker.py`, pero ningún módulo escribe en él. El primer escritor es la skill de AP.
- Patrón de registro de referencia: `_skills_drafts/preparacion-audiencia-previa/scripts/registrar_outputs.py` y `references/manifiesto_y_registro.md` (doble registro idempotente).

## 5. Diseño de la solución

### 5.1 Helper canónico generalizado

Generalizar el `registrar_outputs.py` de la AP y promoverlo a fuente única.

- **Ruta canónica en repo:** `.claude/skills/_shared/registrar_outputs.py`.
- **Interfaz (CLI):** `python registrar_outputs.py <case_dir> <outputs.json>`.
  - `case_dir`: raíz del expediente (la carpeta que contiene `00_Input/`, `05_Procedimiento/`…).
  - `outputs.json`: lista de objetos. Cada objeto declara su carpeta destino, de modo que una sola llamada puede registrar en carpetas distintas.

- **Esquema `outputs.json`:**
  ```json
  [
    {
      "fichero": "DEMANDA_W-XXXXXX.docx",
      "tipo": "demanda",
      "perspectiva": "actora",
      "destino": "05_Procedimiento",
      "fuentes": ["informe_viabilidad", "encargo", "doc. 3"],
      "wikilink": "DEMANDA_W-XXXXXX",
      "estado": "borrador",
      "meta": {"roj": "", "ecli": ""}
    }
  ]
  ```
  - `tipo` (enum): `demanda | contestacion | reconvencion | recurso | requerimiento | escrito_tramite | minuta_ap | solicitud_prueba | conclusiones | interrogatorio | orden_vista | cuadro_hechos | jurisprudencia`.
  - `destino`: subcarpeta de `CASO_SUBDIRS`. **Validar** contra esa lista; **rechazar** `90_Notas personales`.
  - `wikilink`: opcional; si falta, usar el *stem* del fichero.
  - `meta`: opcional (ROJ/ECLI en jurisprudencia).

- **Comportamiento:** (1) por cada `destino`, crear/actualizar `<case_dir>/<destino>/_index.md` (tabla append, idempotente por fichero); (2) añadir wikilinks a `## Navegación` de `00_Input/_caso.md` (idempotente; crear sección si falta; **nunca tocar el frontmatter**); (3) si `_caso.md` no existe → solo manifiesto + aviso por stderr.

- **Robustez:** idempotente; escritura atómica UTF-8 sin BOM; guardia que rechaza `90_Notas personales`; **best-effort** (un fallo del registro no invalida el `.docx` ya generado; la skill trata salida ≠ 0 como aviso).

### 5.2 Mapa de carpeta destino por tipo de output

| Tipo de output | Carpeta destino por defecto |
|---|---|
| demanda, contestación, reconvención | `05_Procedimiento` |
| recurso (apelación, casación…) | `05_Procedimiento` |
| escrito de trámite | `05_Procedimiento` |
| requerimiento extrajudicial | `04_Output predemanda` |
| minuta AP, solicitud de prueba | `05_Procedimiento` (ya en AP) |
| conclusiones, interrogatorios, orden de vista, cuadro de hechos | `05_Procedimiento` |
| jurisprudencia (PDF CENDOJ) | `05_Procedimiento/Jurisprudencia` → confirmar (cuestión abierta #2) |

Cada skill guarda el documento en `<case_dir>/<destino>/` (salida primaria) **y** copia a `outputs/` (secundaria) para enlazar con `present_files`.

### 5.3 Detección de expediente (Fase 0 de cada skill)

`escritos-judiciales` y `preparacion-juicio-oral` no tienen hoy conciencia de caso. Añadir Fase 0 (igual que AP):

- El expediente es la carpeta que contiene `00_Input/_caso.md`. La skill recibe la ruta del expediente (o la referencia que indique el letrado) y comprueba la existencia de `00_Input/_caso.md`.
- Si existe → **modo expediente estructurado** (E&V o particular, indistinto): guardar según §5.2 y llamar al helper.
- Si no existe → modo ad-hoc: preguntar carpeta destino, guardar, **omitir** registro.

### 5.4 Cambios por skill

**A) `escritos-judiciales`** — crear `scripts/registrar_outputs.py` (copia del canónico); en `SKILL.md`, añadir Fase 0 (§5.3) y sección «Guardado y registro»: salida primaria a `<case>/<destino>/` según §5.2, copia a `outputs/`, e invocación del helper con un `outputs.json` derivado del escrito. Documentar el modo ad-hoc.

**B) `cendoj-descarga`** — ya guarda en la carpeta del expediente (Paso 7). Crear `scripts/registrar_outputs.py` y añadir **Paso 7-bis: registro** (`tipo: "jurisprudencia"`, `fuentes: [ROJ, ECLI]`, `wikilink`=stem, `meta` con ROJ/ECLI). Confirmar subcarpeta (cuestión abierta #2).

**C) `preparacion-juicio-oral`** (fuente pendiente — cuestión abierta #1) — una vez versionada en `.claude/skills/`: que `gen_conclusiones`, `gen_interrogatorio`, `gen_cuadro_hechos`, `gen_orden_vista` escriban en `<case>/05_Procedimiento/` y registren cada `.docx` (un wikilink por fichero; contemplar varios interrogatorios).

**D) `preparacion-litigio-civil` — clave para el escenario B (particulares).**
- Hoy `scripts/scaffold_expediente.py` crea una estructura paralela (`00_PREPARACION … 05_BORRADORES`) que **no coincide** con `CASO_SUBDIRS`. **Reemplazarla** por un scaffolding que cree el árbol `CASO_SUBDIRS` y un **`00_Input/_caso.md` mínimo** con: frontmatter YAML básico (referencia, cliente=particular, posición, contraparte, fecha) y una sección `## Navegación` vacía, de modo que el helper de registro funcione igual que en E&V.
- En **modo expediente estructurado** (ya existe `00_Input/_caso.md`): no recrear nada; localizar `PREPARACION_X.md` / `HECHOS_X.md` dentro del expediente (propuesta: `02_Analisis/` — cuestión abierta #3).
- Para casos E&V, la apertura la sigue haciendo el core (`case_manager`); la skill no duplica ese camino.
- Reutilizar, si es posible, una **función común de scaffolding** de `CASO_SUBDIRS` para que E&V (core) y particulares (skill) produzcan exactamente el mismo árbol y el mismo formato de `_caso.md` (evita divergencias).

### 5.5 Sincronización del helper (guardia anti-drift) y empaquetado

- `scripts/sync_skill_helpers.py`: copia `.claude/skills/_shared/registrar_outputs.py` a cada skill objetivo y a `_skills_drafts/preparacion-audiencia-previa/scripts/` (unificar AP con el canónico).
- `tests/test_skill_helpers_sync.py`: comprueba copias **byte-idénticas** (falla si alguien edita una copia a mano).
- **Migrar AP al canónico:** su `registrar_outputs.py` se generaliza y pasa a ser el canónico.
- **Empaquetado `.skill`:** regenerar bundles por la vía habitual (cuestión abierta #4); ejecutar el `sync` antes de empaquetar.

### 5.6 Lado core (track separado, no bloqueante)

Promover a `docs/MEJORAS_FUTURAS.md` (y a `PLAN.md` con disparador) que el core (a) reconozca/lea `<subdir>/_index.md` al listar el expediente y (b) resuelva los wikilinks de `## Navegación` para todos los tipos. No bloquea las skills.

## 6. Plan de ejecución por fases

| Fase | Trabajo | Archivos | Criterio de aceptación |
|---|---|---|---|
| 1 | Helper canónico generalizado + tests | `.claude/skills/_shared/registrar_outputs.py`, `tests/test_registrar_outputs.py` | Tests verdes (idempotencia, _caso.md ausente, creación de Navegación, rechazo 90, destino inválido, escritura atómica) |
| 2 | Sync script + drift test; migrar AP | `scripts/sync_skill_helpers.py`, `tests/test_skill_helpers_sync.py` | Copias byte-idénticas; AP registra igual |
| 3 | `escritos-judiciales`: Fase 0 + guardado/registro | `.claude/skills/escritos-judiciales/{SKILL.md,scripts/}` | Una demanda de prueba aparece en `05_Procedimiento`, `_index.md`, Navegación y `outputs/` |
| 4 | `cendoj-descarga`: Paso 7-bis | `.claude/skills/cendoj-descarga/{SKILL.md,scripts/}` | Un PDF descargado queda registrado con ROJ/ECLI |
| 5 | `preparacion-juicio-oral`: localizar fuente + aplicar | (pendiente) | Conclusiones/interrogatorios/orden de vista registrados |
| 6 | `preparacion-litigio-civil`: scaffolding alineado a `CASO_SUBDIRS` + `_caso.md` mínimo (escenario B) | `.claude/skills/preparacion-litigio-civil/{SKILL.md,scripts/}` | Abrir un caso de particular crea `CASO_SUBDIRS` + `_caso.md` con Navegación; un escrito se guarda y registra igual que en E&V |
| 7 | Empaquetar `.skill` + e2e (caso E&V y caso particular) | bundles | Verificación end-to-end OK en ambos escenarios |
| 8 | Core follow-up a backlog | `docs/MEJORAS_FUTURAS.md` | Entrada registrada |

Orden: 1 → 2 → 3 → 4 → (5 cuando se localice la fuente) → 6 → 7 → 8. Las fases 3 y 4 son independientes tras cerrar 1–2.

## 7. Pruebas

**Unitarias (`tests/test_registrar_outputs.py`):** sobre expediente temporal (con `00_Input/_caso.md` y `CASO_SUBDIRS`): doble ejecución no duplica; `_caso.md` ausente → solo manifiesto + aviso; `## Navegación` inexistente → se crea, frontmatter intacto; `destino == "90_Notas personales"` → rechazado; `destino` inválido → error claro; escritura UTF-8 sin BOM y atómica.

**Manual end-to-end (ambos escenarios):**
- *E&V:* en un caso `W-EJEMPLO`, generar una demanda; verificar fichero en `05_Procedimiento/`, fila en `_index.md`, wikilink en `_caso.md`, copia en `outputs/`.
- *Particular:* abrir un expediente de particular con `preparacion-litigio-civil`, generar un escrito y verificar el mismo resultado.

## 8. Riesgos y mitigaciones

- **Corromper `_caso.md`** → escritura atómica + idempotencia + no tocar frontmatter + tests. (El helper bundleado no importa `core`; reimplementa escritura segura, cubierta por test.)
- **Escribir en `90_Notas personales`** → guardia explícito.
- **Divergencia de copias del helper** → test de sincronía.
- **`preparacion-juicio-oral` sin fuente en repo** → bloquea Fase 5 hasta localizar/versionar su origen.
- **Dos caminos de apertura de expediente (core E&V vs skill particular) que divergen** → mitigar con función común de scaffolding de `CASO_SUBDIRS` y formato único de `_caso.md`.
- **Confusión con skills genéricas** → `docx/xlsx/pdf` no se tocan; `escritos-judiciales` genera su `.docx` con Node inline.

## 9. Cuestiones abiertas (requieren decisión)

1. **Fuente de `preparacion-juicio-oral`:** no está en el repo. ¿Se versiona en `.claude/skills/` desde la caché instalada? ¿Dónde está el origen real?
2. **Subcarpeta destino de jurisprudencia CENDOJ:** ¿`05_Procedimiento/Jurisprudencia/`, raíz del expediente, u otra?
3. **Ubicación de `PREPARACION_X.md` / `HECHOS_X.md`** en la estructura del expediente: propuesta `02_Analisis/`. Confirmar.
4. **Mecanismo de empaquetado `.skill`:** ¿manual, `skill-creator`, u otro? Necesario para regenerar bundles tras el `sync`.
5. **Escenario B (particulares) — campos E&V:** el `_caso.md` mínimo no debe exigir cliente propio EV ni intake de Drive E&V. ¿Qué frontmatter mínimo se quiere? ¿Las subcarpetas E&V de `00_Input` (p. ej. `01_drive_ev`) se omiten en particulares o se crean vacías? ¿La terminología propietario/buscador aplica también a disputas de particulares, o solo a intermediación?

## 10. Checklist final para Code

- [ ] Helper canónico en `.claude/skills/_shared/registrar_outputs.py` con guardia 90, validación de `destino`, idempotencia y escritura atómica.
- [ ] Tests unitarios del helper en verde.
- [ ] `sync_skill_helpers.py` + `test_skill_helpers_sync.py`; AP migrada al canónico.
- [ ] `escritos-judiciales`: Fase 0 + guardado + registro + copia a `outputs/`.
- [ ] `cendoj-descarga`: Paso 7-bis de registro (tipo jurisprudencia).
- [ ] `preparacion-juicio-oral`: fuente localizada y cambios aplicados.
- [ ] `preparacion-litigio-civil`: scaffolding alineado a `CASO_SUBDIRS` + `_caso.md` mínimo para particulares; sin árbol paralelo.
- [ ] Función común de scaffolding compartida entre core (E&V) y skill (particulares), si es viable.
- [ ] `.skill` regeneradas; e2e OK en escenario E&V y en escenario particular.
- [ ] Entrada en `docs/MEJORAS_FUTURAS.md` para el reconocimiento del manifiesto y wikilinks por el core.
