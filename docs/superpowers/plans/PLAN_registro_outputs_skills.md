---
estado: historico
dueño: Nikolai Tyukhay
---

# Plan de implementación — Registro de outputs de skills en el expediente

**Destinatario:** Claude Code (edición de código y skills en `C:\Users\tnm33\Dev\FeesDefender`).
**Origen:** análisis desde Cowork (solo lectura del repo).
**Fecha:** 2026-06-12.

## 1. Objetivo

Que toda skill que genere un documento (escrito, soporte de vista, jurisprudencia) **guarde el output en la carpeta correspondiente del expediente** y **lo registre en el fichero maestro del caso**, replicando el mecanismo que ya funciona en `preparacion-audiencia-previa`.

Resultado esperado tras la ejecución:

1. Una rutina de registro **única y generalizada**, mantenida en el repo y copiada (idéntica) dentro de cada skill objetivo.
2. `escritos-judiciales`, `cendoj-descarga` y `preparacion-juicio-oral` guardan en la carpeta del caso y registran el output.
3. `preparacion-litigio-civil` deja de crear una estructura de carpetas paralela y reutiliza la del expediente FeesDefender.
4. Un guardia de sincronización que impide que las copias del helper diverjan.

## 2. Decisiones tomadas (cerradas)

- **Arquitectura (Opción A):** helper canónico versionado en el repo, copiado a `scripts/` de cada skill al empaquetar. Las skills siguen siendo autónomas (PC y móvil).
- **Alcance:** solo skills procesales conscientes de expediente — `escritos-judiciales`, `preparacion-juicio-oral`, `cendoj-descarga` — más alinear `preparacion-litigio-civil`. Las skills genéricas `docx/xlsx/pdf` **no se tocan** (son motor de formato).
- **Modo:** patrón de la audiencia previa. Si existe `00_Input/_caso.md` → modo FeesDefender (guarda en carpeta + registra automático). Si no → modo civil genérico (pregunta carpeta destino, sin registro).

## 3. Anclajes verificados (no asumir, ya comprobado)

- Skills editables en `C:\Users\tnm33\Dev\FeesDefender\.claude\skills\`: `escritos-judiciales` (solo `SKILL.md`), `cendoj-descarga`, `preparacion-litigio-civil`, `docx`, `pdf`, `xlsx`, `viabilidad-prerelleno`.
- `preparacion-audiencia-previa` vive en `_skills_drafts/preparacion-audiencia-previa/` (con `scripts/`, `references/`, `templates/`, `assets/`, `evals/`, `logs/`) y su bundle `_skills_drafts/preparacion-audiencia-previa.skill`.
- **`preparacion-juicio-oral` NO está en el repo** (solo en la caché instalada). → Cuestión abierta #1.
- Estructura canónica del caso: `core/config.py → CASO_SUBDIRS` =
  `00_Input, 01_Procesado, 02_Analisis, 03_Decision, 04_Output predemanda, 05_Procedimiento, 06_Anonimizado, 07_AI cowork, 90_Notas personales`.
- Fichero maestro: `00_Input/_caso.md`, con sección `## Navegación` (la crea `core/case_manager.py`, línea ~119). Escritura atómica del maestro vía `_atomic_write_caso_md` en `case_manager`.
- `05_Procedimiento` está hoy **inerte**: lo crea el scaffolding y lo barre `core/linker.py`, pero ningún módulo escribe en él. El primer escritor es la skill de AP.
- Patrón de registro de referencia: `_skills_drafts/preparacion-audiencia-previa/scripts/registrar_outputs.py` y `references/manifiesto_y_registro.md` (doble registro idempotente: manifiesto `_index.md` + wikilinks en `_caso.md`).

## 4. Diseño de la solución

### 4.1 Helper canónico generalizado

Generalizar el `registrar_outputs.py` de la AP y promoverlo a fuente única.

- **Ruta canónica en repo:** `.claude/skills/_shared/registrar_outputs.py`.
- **Interfaz (CLI):**
  ```
  python registrar_outputs.py <case_dir> <outputs.json>
  ```
  - `case_dir`: raíz del expediente (la carpeta que contiene `00_Input/`, `05_Procedimiento/`…).
  - `outputs.json`: lista de objetos (esquema abajo). Cada objeto declara su propia carpeta destino, de modo que una sola llamada puede registrar outputs en carpetas distintas.

- **Esquema `outputs.json` (generalizado):**
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
  - `tipo` (enum ampliado): `demanda | contestacion | reconvencion | recurso | requerimiento | escrito_tramite | minuta_ap | solicitud_prueba | conclusiones | interrogatorio | orden_vista | cuadro_hechos | jurisprudencia`.
  - `destino`: una subcarpeta de `CASO_SUBDIRS`. **Validar** contra esa lista; **rechazar** `90_Notas personales` (zona reservada del letrado).
  - `wikilink`: opcional; si falta, usar el *stem* del fichero (sin extensión). Garantiza unicidad cuando hay varios outputs del mismo tipo.
  - `meta`: opcional (p. ej. ROJ/ECLI en jurisprudencia).

- **Comportamiento:**
  1. Para cada `destino` distinto, crear/actualizar `<case_dir>/<destino>/_index.md` (tabla append, **idempotente por nombre de fichero**). Cabecera genérica del manifiesto (no atada a AP).
  2. Añadir los wikilinks a la sección `## Navegación` de `00_Input/_caso.md` (idempotente). Si la sección no existe, crearla al final. **Nunca tocar el frontmatter YAML.**
  3. Si `00_Input/_caso.md` no existe → escribir solo el/los manifiesto(s) y avisar por `stderr` (defensa; en la práctica las skills solo llaman al helper en modo FeesDefender).

- **Robustez (requisitos):**
  - **Idempotente:** re-ejecutar no duplica filas ni wikilinks (clave de dedupe: `(destino, fichero)` en manifiesto; `wikilink` en `_caso.md`).
  - **Escritura atómica + UTF-8 sin BOM:** escribir a temporal y `os.replace`. No dejar `_caso.md` a medias.
  - **Guardia 90:** abortar el registro de cualquier output con `destino == "90_Notas personales"`, con mensaje claro.
  - **Best-effort:** el helper es un proceso posterior a la generación del documento. Si falla, **no** debe invalidar el `.docx` ya creado. La skill tratará un código de salida ≠ 0 como **aviso**, no como aborto, y lo comunicará al letrado.

### 4.2 Mapa de carpeta destino por tipo de output

| Tipo de output | Carpeta destino por defecto |
|---|---|
| demanda, contestación, reconvención | `05_Procedimiento` |
| recurso (apelación, casación…) | `05_Procedimiento` |
| escrito de trámite | `05_Procedimiento` |
| requerimiento extrajudicial | `04_Output predemanda` |
| minuta AP, solicitud de prueba | `05_Procedimiento` (ya implementado en AP) |
| conclusiones, interrogatorios, orden de vista, cuadro de hechos | `05_Procedimiento` |
| jurisprudencia (PDF CENDOJ) | `05_Procedimiento/Jurisprudencia` → **confirmar (cuestión abierta #2)** |

Cada skill **guarda el documento directamente en `<case_dir>/<destino>/`** (salida primaria) **y** copia a `outputs/` (salida secundaria) para poder enlazarlo con `present_files`. Es el doble guardado que ya hacen AP y CENDOJ.

### 4.3 Detección de expediente (Fase 0 de cada skill)

`escritos-judiciales` y `preparacion-juicio-oral` **no tienen hoy conciencia de caso**. Añadir una Fase 0 que replique la de AP:

- El expediente es la carpeta que contiene `00_Input/_caso.md`. La skill recibe la ruta del expediente (o la referencia W-XXXXXX que el letrado indique) y comprueba la existencia de `00_Input/_caso.md`.
- Si existe → **modo FeesDefender**: guardar en la carpeta destino del mapa (§4.2) y llamar al helper.
- Si no existe → **modo civil genérico**: preguntar al letrado la carpeta destino, guardar ahí y **omitir** el registro.

### 4.4 Cambios por skill

**A) `escritos-judiciales`** (`.claude/skills/escritos-judiciales/`)
- Crear `scripts/registrar_outputs.py` (copia del canónico).
- `SKILL.md`: añadir Fase 0 (detección de expediente, §4.3) y una sección «Guardado y registro» que (i) fije la salida primaria en `<case>/<destino>/` según el mapa §4.2, (ii) copie a `outputs/`, (iii) invoque `registrar_outputs.py` con un `outputs.json` construido a partir del escrito generado. Documentar el modo genérico como fallback.

**B) `cendoj-descarga`** (`.claude/skills/cendoj-descarga/`)
- Ya guarda en la carpeta del expediente (Paso 7). Crear `scripts/registrar_outputs.py` (copia del canónico) y añadir un **Paso 7-bis: registro**, que da de alta cada PDF descargado con `tipo: "jurisprudencia"`, `fuentes: [ROJ, ECLI]`, `wikilink`= *stem*, `meta` con ROJ/ECLI.
- Confirmar la subcarpeta destino de jurisprudencia (cuestión abierta #2).

**C) `preparacion-juicio-oral`** (fuente pendiente de localizar — cuestión abierta #1)
- Una vez versionada en `.claude/skills/`: mismos cambios. Sus generadores (`gen_conclusiones`, `gen_interrogatorio`, `gen_cuadro_hechos`, `gen_orden_vista`) deben escribir en `<case>/05_Procedimiento/` y, tras cada `.docx`, registrar (`tipo` correspondiente; un wikilink por fichero, contemplando varios interrogatorios). Reutilizar el canónico, no duplicar lógica.

**D) `preparacion-litigio-civil`** (`.claude/skills/preparacion-litigio-civil/`)
- Hoy `scripts/scaffold_expediente.py` crea una estructura paralela (`00_PREPARACION … 05_BORRADORES`) que **no coincide** con `CASO_SUBDIRS`.
- En **modo FeesDefender** la apertura del expediente la hace el core (`case_manager`), no la skill: detectar `00_Input/_caso.md` y, si existe, **no** crear el árbol genérico; ubicar `PREPARACION_X.md` / `HECHOS_X.md` dentro de la estructura del expediente (propuesta: `02_Analisis/`) — **decisión pendiente (cuestión abierta #3)**.
- En modo genérico, mantener el scaffolding actual.

### 4.5 Sincronización del helper (guardia anti-drift) y empaquetado

- `scripts/sync_skill_helpers.py` (repo): copia `.claude/skills/_shared/registrar_outputs.py` a `scripts/` de cada skill objetivo (`escritos-judiciales`, `cendoj-descarga`, fuente de `preparacion-juicio-oral`) y a `_skills_drafts/preparacion-audiencia-previa/scripts/` (unificar AP con el canónico).
- `tests/test_skill_helpers_sync.py`: comprueba que todas las copias son **byte-idénticas** al canónico (falla si alguien edita una copia a mano).
- **Migrar AP al canónico:** su `registrar_outputs.py` actual se generaliza y pasa a ser el canónico; AP deja de tener lógica propia.
- **Empaquetado `.skill`:** regenerar el bundle de cada skill tocada por la vía habitual del despacho (confirmar mecanismo — cuestión abierta #4). El `sync` debe ejecutarse **antes** de empaquetar.

### 4.6 Lado core (track separado, no bloqueante)

Promover desde `references/manifiesto_y_registro.md` a `docs/MEJORAS_FUTURAS.md` (y a `PLAN.md` cuando haya disparador real) que el core:
- (a) reconozca y lea `<subdir>/_index.md` al listar el expediente;
- (b) resuelva los wikilinks de `## Navegación` para todos los tipos (no solo AP).

No bloquea las skills: el registro funciona aunque el core aún no lea el manifiesto.

## 5. Plan de ejecución por fases

| Fase | Trabajo | Archivos | Criterio de aceptación |
|---|---|---|---|
| 1 | Helper canónico generalizado + tests unitarios | `.claude/skills/_shared/registrar_outputs.py`, `tests/test_registrar_outputs.py` | Tests verdes (idempotencia, _caso.md ausente, creación de Navegación, rechazo 90, destino inválido, escritura atómica) |
| 2 | Sync script + drift test; migrar AP al canónico | `scripts/sync_skill_helpers.py`, `tests/test_skill_helpers_sync.py`, AP `scripts/` | Copias byte-idénticas; AP sigue registrando igual |
| 3 | `escritos-judiciales`: Fase 0 + guardado/registro | `.claude/skills/escritos-judiciales/{SKILL.md,scripts/}` | Una demanda de prueba aparece en `05_Procedimiento`, en `_index.md`, en Navegación y en `outputs/` |
| 4 | `cendoj-descarga`: Paso 7-bis registro | `.claude/skills/cendoj-descarga/{SKILL.md,scripts/}` | Un PDF descargado queda registrado con ROJ/ECLI |
| 5 | `preparacion-juicio-oral`: localizar fuente + aplicar | (pendiente de ubicación) | Conclusiones/interrogatorios/orden de vista registrados |
| 6 | `preparacion-litigio-civil`: alinear estructura | `.claude/skills/preparacion-litigio-civil/{SKILL.md,scripts/}` | En modo FeesDefender no crea árbol paralelo; maestros en la ubicación decidida |
| 7 | Empaquetar `.skill` de las skills tocadas + e2e | bundles | Verificación end-to-end manual OK |
| 8 | Core follow-up a backlog | `docs/MEJORAS_FUTURAS.md` | Entrada registrada |

Orden recomendado: 1 → 2 → 3 → 4 → (5 cuando se localice la fuente) → 6 → 7 → 8. Las fases 3 y 4 son independientes entre sí una vez cerradas 1–2.

## 6. Pruebas

**Unitarias (`tests/test_registrar_outputs.py`):** sobre un expediente temporal (fixture con `00_Input/_caso.md` y `CASO_SUBDIRS`):
- doble ejecución no duplica filas ni wikilinks;
- `_caso.md` ausente → solo manifiesto + aviso por stderr;
- sección `## Navegación` inexistente → se crea al final, frontmatter intacto;
- `destino == "90_Notas personales"` → rechazado;
- `destino` fuera de `CASO_SUBDIRS` → error claro;
- escritura UTF-8 sin BOM y atómica (sin fichero a medias ante fallo simulado).

**Manual end-to-end:** en un caso `W-EJEMPLO`, generar una demanda con `escritos-judiciales`; verificar fichero en `05_Procedimiento/`, fila en `05_Procedimiento/_index.md`, wikilink en `00_Input/_caso.md`, copia en `outputs/`.

## 7. Riesgos y mitigaciones

- **Corromper `_caso.md`** → escritura atómica + idempotencia + no tocar frontmatter + tests. (Nota: el helper bundleado no puede importar `core`, por lo que reimplementa la escritura segura; cubrir con test.)
- **Escribir en zona reservada** (`90_Notas personales`) → guardia explícito que rechaza ese destino.
- **Divergencia de copias del helper** → test de sincronía byte a byte.
- **`preparacion-juicio-oral` sin fuente en repo** → bloquea Fase 5 hasta localizar/versionar su origen.
- **Confusión con skills genéricas** → `docx/xlsx/pdf` no se tocan; `escritos-judiciales` genera su `.docx` con Node inline (no usa la skill `docx`), así que el registro lo hace la skill procesal, no el motor de formato.

## 8. Cuestiones abiertas (requieren decisión antes o durante la ejecución)

1. **Fuente de `preparacion-juicio-oral`:** no está en el repo. ¿Se baja de la caché instalada y se versiona en `.claude/skills/`? ¿Dónde está el origen real?
2. **Subcarpeta destino de jurisprudencia CENDOJ:** ¿`05_Procedimiento/Jurisprudencia/`, raíz del expediente, u otra?
3. **Ubicación de `PREPARACION_X.md` / `HECHOS_X.md`** en la estructura FeesDefender: propuesta `02_Analisis/`. Confirmar.
4. **Mecanismo de empaquetado `.skill`:** ¿manual, `skill-creator`, u otro script? Necesario para regenerar bundles tras el `sync`.

## 9. Checklist final para Code

- [ ] Helper canónico en `.claude/skills/_shared/registrar_outputs.py` con guardia 90, validación de `destino`, idempotencia y escritura atómica.
- [ ] Tests unitarios del helper en verde.
- [ ] `sync_skill_helpers.py` + `test_skill_helpers_sync.py`; AP migrada al canónico.
- [ ] `escritos-judiciales`: Fase 0 + guardado en `05_Procedimiento`/`04_Output predemanda` + registro + copia a `outputs/`.
- [ ] `cendoj-descarga`: Paso 7-bis de registro (tipo jurisprudencia).
- [ ] `preparacion-juicio-oral`: fuente localizada y cambios aplicados.
- [ ] `preparacion-litigio-civil`: sin árbol paralelo en modo FeesDefender; maestros reubicados.
- [ ] `.skill` regeneradas; verificación end-to-end manual OK.
- [ ] Entrada en `docs/MEJORAS_FUTURAS.md` para el reconocimiento del manifiesto y wikilinks por el core.
