# FeesDefender — Instrucciones del proyecto (Claude Code)

> Equivalente al "Project instructions" de Cowork. Se carga automáticamente al abrir Claude Code en este directorio.

## Qué es esto

Sistema legal-tech para automatizar análisis y defensa de honorarios de
intermediación inmobiliaria en España. Cliente principal: Engel & Völkers
(EV MMC SPAIN, S.L.U.). Usuario: Nikolai Tyukhay, abogado.

## Idioma

Responder siempre en castellano salvo que el usuario inicie en otro idioma.
Las comunicaciones a clientes de origen ruso o ex-URSS van en ruso por defecto.

## Revisión adversarial: OBLIGATORIA, la ejecuta Codex, la adjudica Claude

**Todo diseño (spec/plan) y todo diff de código no trivial pasa por una revisión adversarial
antes de mergearse.** Eso no es opcional y no ha cambiado. Lo que cambió (2026-08-01) es quién la
ejecuta: **Codex**, con su propia bolsa de tokens. Antes se delegaba a Gemini vía la CLI `agy` de
Antigravity; esa vía se retiró por cupo agotado de forma persistente — el porqué, con la evidencia,
en `docs/DEAD_ENDS.md`. **No la reintentes.**

- **Patrón:** Codex ataca (**solo lectura, sin escribir en el repo**) → escribe sus hallazgos a un
  fichero **fuera del repo**, en la ruta que fija el encargo → devuelve **ruta y `sha256` canónico**
  → **Claude adjudica** cada hallazgo contra el código real.
- **Dónde va cada cosa** (esto era el «o» ambiguo, resuelto el 2026-08-01):
  la **adjudicación** va *embebida* en el spec o el plan revisado, con el encabezado canónico y su
  ficha; el **informe del revisor** va *literal* a un **acta hermana** `…-adversarial-review.md`, con
  su digest. Nunca al revés: la decisión pertenece al documento que la decisión modificó, y el acta
  es el archivo de la voz del revisor, no un segundo hogar de la decisión. Los guards **G7 y G8** de
  `tests/test_docs_gobernanza.py` lo comprueban y recomputan el digest — una desigualdad es roja.
  Contrato completo: `docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md`.
- **Para qué sirve el acta, en una frase:** yo soy la parte revisada, así que sin el original
  archivado nadie puede contrastar **qué dijo el revisor** con **qué decidí yo que dijo**.
- **Claude es siempre el juez.** Codex nunca tiene la última palabra sobre corrección. Un hallazgo
  se confirma o se refuta **contra la fuente**, no contra el diff ni contra la seguridad con que
  venga redactado.
- **Un revisor que no corre no refuta: deja sin verificar.** Si la revisión no se ejecuta, se declara
  la cobertura ausente en el documento — nunca se da por refutado lo que nadie miró.
- **Se queda en Claude, sin delegar:** juicio jurídico, escritos con la voz del despacho, veredictos,
  anclaje a fuente y revisión final.
- **El trabajo mecánico pesado vuelve a Claude** (barridos de corpus, OCR/extracción, resúmenes
  masivos, boilerplate): con `agy` fuera ya no hay a quién delegarlo en bloque. Para lo paralelizable,
  subagentes; para lo grande, trocearlo.

## Al iniciar cada sesión

Leer `STATUS.md` — es la fuente de verdad única del proyecto. Contiene
estado actual, próximas tareas (`[SIGUIENTE]`), credenciales, estructura
de carpetas y el checklist de apertura con los comandos exactos.

Ruta: `STATUS.md` en la raíz del repo (este directorio).

## Planificación y estado

Desde 2026-05-29 la bitácora vive en el **repo como única fuente de verdad**
(antes en Drive; abandonado por divergencia PC→nube y por duplicados del conector
de Cowork, que solo soporta create). Drive queda solo para expedientes jurídicos
(`CASOS_ROOT`) y entregables a cliente.

- `PLAN.md` (raíz del repo): planificación compartida. Cowork (PC) y Claude Code
  lo editan ambos. Cowork móvil queda fuera del lazo hasta que exista un conector
  MCP de GitHub.
- `STATUS.md` (raíz del repo): estado del proyecto y bitácora de cierre de sesión.
  Lo escribe Claude Code en cada cierre; Cowork lo lee.
- `docs/MEJORAS_FUTURAS.md`: backlog técnico (ideas, bugs latentes, mejoras
  diferidas). Cubre todo el repo, no solo `core/anon/`.
- Historial: `git log`. No se mantiene `commits.log` como artefacto separado.
- Acceso móvil: app de GitHub (lectura). Edición ocasional vía GitHub web.

**Regla de promoción backlog → cola**: una entrada de `docs/MEJORAS_FUTURAS.md`
se promueve a `PLAN.md` cuando tiene **disparador concreto**: caso real que lo
necesita, bug bloqueante que lo activa, o decisión explícita de Nikolai. Al
promover: (1) marcar en `MEJORAS_FUTURAS.md` con `[PROMOVIDO → PLAN.md]`;
(2) crear entrada en `PLAN.md` con referencia `MEJORAS #NN`. No promover por
completitud de diseño ni por anticipación — solo por necesidad demostrada.

**Al iniciar sesión**: leer `PLAN.md` además de `STATUS.md`; los puntos en la cola
de prioridad son entrada directa de trabajo, y las "Decisiones pendientes" sin
resolver se plantean antes de avanzar. **Al completar un punto**: marcarlo `[x]` en
`PLAN.md` y anotar el hash del commit. **Al cerrar sesión**: dejar `PLAN.md` al día.

**Hogar único del estado de un ítem (regla, tras el drift de `[BIBLIOTECA-CHECKOUT]`
2026-07-08):** el *estado de ciclo de vida* de un ítem de trabajo (pendiente / en curso /
`✅` completado + hash del PR) vive **solo en `PLAN.md`** — es su hogar autoritativo. El
bloque de sesión de `STATUS.md` es un **log cronológico** que narra y enlaza por etiqueta,
no el sitio donde se lee "en qué punto está X". Y a la inversa: **`PLAN.md` no restata
hechos que son de git** (nombre de rama, ruta de worktree, "sin commitear", "pendiente
commit/PR"): git es el hogar de esos hechos. Al cerrar un ítem se pone `✅` + hash del PR
y se retira la prosa de rama/worktree. `scripts/session_close` avisa (no bloquea) si
`PLAN.md` marca trabajo pendiente en una rama que git ya no conoce. Fundamento y modelo
completo: `docs/GOBERNANZA_FUENTES_VERDAD.md` (Drift #5).

Código: este directorio (`C:\Users\tnm33\Dev\FeesDefender`), versionado en Git →
`github.com/TyukhayNi/FeesDefender`. Disco local, sin latencia de Drive.

## Reglas que nunca se rompen

- Arquitectura 3 capas: UI → Core (`core/`) → Datos (`data/CASOS/`). La lógica
  vive en el core, la UI solo orquesta. Nunca mover lógica a Streamlit.
- `data/CASOS/` está en `.gitignore`. Nunca a GitHub. Contiene expedientes reales.
- **Higiene de datos y secretos (nunca se rompe):** el dato real vive fuera del repo;
  las capturas de depuración (HAR, dumps, exports) **nunca se commitean**; los secretos
  solo por entorno (`.env`/`$env:`), nunca en el árbol ni en el chat; en docs/bitácora/
  commits se referencia por `W-XXXXX`, no por nombre/email/dirección de tercero. Doctrina,
  controles y runbook: `docs/SEGURIDAD_DATOS.md`.
- **`main` protegida (branch protection, desde 2026-07-07):** NO se pushea directo a
  `main`. El trabajo va en **rama + PR**, que debe pasar el check `leak-scan` para poder
  mergear (cubre todas las máquinas y Cowork). El auto-push `post-commit` ya no existe.
  Instalar en cada clon/worktree: `pre-commit install && pre-commit install --hook-type pre-push`.
- `90_NOTAS_PERSONALES/` en cada caso es zona del abogado — ningún módulo
  del core la lee ni la escribe.
- Los prompts nunca inventan jurisprudencia. Solo citan lo que está en contexto.
- Pipeline idempotente: re-ejecutar nunca toca `00_Input/` ni `90_NOTAS_PERSONALES/`.
- `core/anon/` — cero pérdida de lógica del Anonimizador original. No tocar
  regex/listas/thresholds. Mejoras solo en `docs/MEJORAS_FUTURAS.md`.
- Nombres de carpetas: tipo oración siempre (`06_Anonimizado`, no `06_ANONIMIZADO`).
- Terminología de partes en operaciones inmobiliarias: **propietario / buscador**
  (no vendedor / comprador).
- NIG no se usa en formularios, payloads ni plantillas.

## Entorno de ejecución

- Sistema: **Windows + PowerShell**. Todo comando shell debe empezar con
  `cd "C:\Users\tnm33\Dev\FeesDefender"`.
- Python: venv local en `.venv/`. Activar con `.\.venv\Scripts\Activate.ps1`
  o usar `python -m ...` directamente desde la raíz del repo.
- Git: nativo Windows. Commits desde PowerShell.
- Encoding: SIEMPRE UTF-8 sin BOM. Usar `[System.IO.File]::ReadAllText/WriteAllText`
  con `UTF8Encoding($false)`. **Nunca** `Add-Content`/`Get-Content -Raw` sin
  `-Encoding UTF8` (produce mojibake en sistemas cp1252).
- `subprocess.run` con stderr UTF-8: usar `encoding="utf-8", errors="replace"`
  (NO `text=True` en Windows — decodifica con cp1252 y trunca tildes).
- **Códigos de salida: nunca leer `$LASTEXITCODE` detrás de un `Select-Object -First N`.**
  La terminación temprana del pipe puede dejarlo en `0` y hacer pasar por bueno un
  comando que falló. Medido el 2026-07-29 con rclone: `copyto` de un origen
  inexistente parecía devolver `0` tras `| Select-Object -First 3` y devuelve **3**
  sin tubería. Patrón correcto: `$out = & cmd args 2>&1` y leer `$LASTEXITCODE` acto
  seguido. `Select-String` sí consume el flujo entero y no contamina.

## Gotchas críticos

- **PHPSESSID** caduca por inactividad (~24 min). Si `check-legacy` falla:
  Chrome → DevTools → Application → Cookies → tnm.sudespacho.net → copiar
  `PHPSESSID` + `@token` + `@refreshToken` → `.env`. Más detalle en
  `docs/INTEGRACION_SUDESPACHO.md`.
- **rclone** sobre Drive E&V: siempre incluir `--drive-skip-shortcuts` para
  evitar `exit 1` por dangling shortcuts. Si destino es Drive for Desktop
  (`G:\Unidades compartidas\...`): añadir `--ignore-size --ignore-checksum --inplace`
  para evitar falsos positivos "corrupted on transfer".
- **Auto-fill Drive E&V**: solo marcar `session_state` sentinel TRAS éxito del
  side effect. Marcarlo antes deja cacheado un fallo durante toda la sesión.
- **Streamlit cache**: igual regla. Cualquier sentinel de "ya hecho" solo
  después de validar éxito.
- **gdrive_ev token**: keep-alive diario + renovación proactiva por expiry
  ya implementada en `core/intake_drive._get_drive_access_token`.

## Permisos y secretos

- Las credenciales viven en `.env` (gitignored) o variables de entorno Windows.
- **Nunca** pedir que se peguen API keys en chat o en ficheros del repo.
- Para inyectar una key temporal: `$env:NOMBRE_VAR = "..."` en la sesión PS.

## Usuarios del sistema

- **Nikolai Tyukhay** — admin, desarrollo, decisiones de arquitectura.
- **Paola + Ana** — UI Streamlit. No tocan código.
- **Marta Reynares (E&V)** — comparte Drive, no entra al repo.

## Flujo de trabajo estándar

> **Flujo git completo (modelo, apertura, cierre, poda, recuperación): fuente única
> `docs/FLUJO_GIT.md`.** Regla de oro: una mesa = una tarea = una rama; **la raíz compartida
> vive siempre en `main`**; el trabajo va en rama/worktree y entra a `main` solo por **PR**
> (nunca commit directo — `main` está protegida).

### Apertura de sesión

```powershell
cd "C:\Users\tnm33\Dev\FeesDefender"
git log --oneline -5                              # qué cambió desde la última sesión
python -m pytest -q --tb=no                       # suite verde
python -m scripts.sync_sudespacho check-legacy    # PHPSESSID válida
```

Atajo: `/status` ejecuta los 3 comandos y muestra un resumen.

### Durante la sesión

- Cambios en `core/` → siempre acompañados de tests en `tests/`.
- Antes de tocar un endpoint del CRM: leer `docs/INTEGRACION_SUDESPACHO.md`
  y consultar HAR si lo hay (`docs/captura/`).
- Antes de reintentar algo que falló raro: leer `docs/DEAD_ENDS.md`.
- **Para abrir un expediente nuevo** (alta → intake → sala de máquina → sala de
  lectura → viabilidad → ficha CRM → archivo → cierre): seguir
  `docs/RUNBOOK_APERTURA_EXPEDIENTE.md` (fuente única operativa, con los gotchas
  embebidos y punteros a `INTEGRACION_SUDESPACHO.md` como SSOT del detalle CRM).

### Cierre de sesión

```powershell
python -m scripts.session_close
```

Equivalentemente, slash command `/cierre`.

El cierre va por **rama → PR** (`main` protegida; nunca commit directo) y termina **podando la
rama y el worktree** y devolviendo la raíz a `main`. Procedimiento completo: `docs/FLUJO_GIT.md §4`.

El cierre valida que la suite sigue verde y prepara el mensaje de commit. El
**bloque de cierre** (fecha + resumen + [SIGUIENTE]) se escribe en
`docs/bitacora/AAAA.md` (reciente primero), **NO** en el top de `STATUS.md`;
STATUS mantiene solo estado vigente + puntero a la bitácora (el aviso E1 de
`session_close` avisa si STATUS crece >400 líneas). Fundamento:
`docs/GOBERNANZA_FUENTES_VERDAD.md`. La memoria persistente (en mi memoria
global, no en el repo) la actualizo yo en el chat antes de cerrar.

## Tests

- Framework: `pytest`.
- Comando rápido: `python -m pytest -q --tb=no`.
- Comando con cobertura por fichero: `python -m pytest -q --tb=no <ruta>`.
- 546/546 verdes en s20 (2026-05-19). Cualquier número distinto debe ser
  explicado en `STATUS.md`.

Atajo: `/tests` ejecuta la suite completa.

## Referencias rápidas

- **Estado y tareas**: `STATUS.md` (raíz del proyecto)
- **Flujo git + protocolo de cierre (SSOT)**: `docs/FLUJO_GIT.md`
- **Índice de `docs/` + ciclo de vida**: `docs/INDICE.md`
- **Runbook de apertura de expediente**: `docs/RUNBOOK_APERTURA_EXPEDIENTE.md` (flujo E2E con gotchas)
- **Arquitectura y deps**: `docs/ARQUITECTURA.md`
- **Relaciones código/plugin/skills + SSOT**: `docs/ARQUITECTURA_RELACIONES.md`
- **API sudespacho**: `docs/INTEGRACION_SUDESPACHO.md` (su §14 fusiona la **referencia común sudespacho**)
- **Atlas del CRM sudespacho (SSOT de la superficie)**: `docs/CRM_SUDESPACHO_ATLAS.md` — inventario
  generado y re-ejecutable de "qué existe" (endpoints Fase A + campos/relaciones/enums por elemento,
  Fase B). Consultarlo ANTES de descubrir un endpoint a mano. Regenerar: `python -m scripts.crm_atlas
  discover --phase all`. El "cómo se usa" (payloads confirmados, auth, dead-ends) sigue en `INTEGRACION`.
- **Referencia común sudespacho** (fuente única agnóstica: auth, API de elementos, permisos + presets por
  rol, enums; compartida con El Contable / El Auditor): [`../ElContable/docs/REFERENCIA_SUDESPACHO_API_PERMISOS.md`](../ElContable/docs/REFERENCIA_SUDESPACHO_API_PERMISOS.md)
- **Callejones sin salida**: `docs/DEAD_ENDS.md` ← consultar antes de reintentar algo
- **Arquitectura dual del expediente activo (local/Drive) — SSOT del diseño**:
  `docs/superpowers/specs/2026-07-29-feesdefender-dual-case-workspace-design.md` (**rev. 2**;
  revisión adversarial adjudicada en `…-adversarial-review.md`, plan de las dos primeras fases en
  `docs/superpowers/plans/2026-07-29-dual-workspace-fase0-fase1.md`). **Consultarlo antes de tocar
  la resolución de un caso**: quién decide qué copia es la operativa (`CaseWorkspace`), qué está
  prohibido durante un checkout y por qué `caso_path`/`CASOS_ROOT` dejan de ser un selector.
  Absorbe el «expediente scratch» (`MEJORAS #59`).
- **Plan subdivisión ciudades**: `docs/superpowers/plans/PLAN_SUBDIVISION_CIUDADES.md`
- **Plan SaRS1 anon**: `docs/superpowers/plans/PLAN_SaRS1_anon_pipeline.md`
- **Plan pre-relleno LLM**: `docs/superpowers/plans/PLAN_PRERELLENO_LLM_VIABILIDAD.md`
- **Motor documental (split/OCR/MD) + empaquetado**: `docs/superpowers/plans/PLAN_MOTOR_DOCUMENTAL.md` (`MEJORAS #48`)
- **Mejoras futuras**: `docs/MEJORAS_FUTURAS.md`
- **Gobernanza de fuentes de verdad**: `docs/GOBERNANZA_FUENTES_VERDAD.md` (su §5 gobierna los
  **handoffs**: andamios efímeros en `docs/superpowers/handoffs/`, con `estado:` en el frontmatter)
- **Seguridad de datos (fugas PII/secretos)**: `docs/SEGURIDAD_DATOS.md`
- **Convenciones del despacho**: `docs/CONVENCIONES_DESPACHO.md`

## Estilo de respuesta

- Tono neutral y directo en conversación.
- Estilo formal y riguroso en documentos legales.
- Nivel jurídico avanzado — no explicar conceptos básicos ni añadir
  advertencias genéricas.
- Priorizar precisión, concisión, rigor. Sin introducciones de relleno.
- Antes de plantear vía judicial, considerar siempre medios alternativos
  (mediación, negociación, conciliación) salvo que el contexto del caso
  haga inviable esa vía.

## Formato de documentos legales

Criterios formales de la Sala 1ª del TS (admisión de recursos de casación):

- Extensión máxima recomendada: 25 páginas.
- Fuente: Times New Roman 12 pt. Notas a pie y citas: 10 pt.
- Citas: 10 pt, cursiva, justificada, sangría izquierda 1 cm.
- Márgenes: 2,5 cm.
- Párrafo: justificado, interlineado 1,5, espaciado anterior 6 pt.
- Numeración de párrafos para facilitar referencias.
- Listas jerárquicas estándar (1., 1.1., 1.1.1.).
- Páginas: TNR 12, centradas.
- Citas documentales: insertadas en el cuerpo cuando el formato lo permita.

Para generación automática de escritos `.docx`, usar la skill
`escritos-judiciales` (en `.claude/skills/escritos-judiciales/`).

### Estilo de la casa (claridad + persuasión + no-IA)

Todo output del despacho (escritos, contratos, comunicaciones a cliente y a E&V) se
redacta en el **estilo de la casa**, definido en el contrato canónico
`data/_estilo/contrato_estilo.md` (fuente única; capa 1): claro, persuasivo y sin
marcas de IA, con la voz del despacho. Antes de guardar o firmar, revísalo con la
skill `pase-de-estilo` (capa 2). **Regla de oro: la precisión jurídica y las citas
verificadas prevalecen sobre cualquier regla de estilo; el estilo opera dentro del
formato Sala 1ª TS, no lo sustituye.**

### Fuente única de verdad de las skills del despacho

**Las skills del despacho se editan SIEMPRE en `.claude/skills/`** de este repo (más
helpers canónicos en `.claude/skills/_shared/`, sincronizados con
`scripts/sync_skill_helpers.py`). Es la fuente única de desarrollo desde 2026-06-12.
El repo externo `despacho-skills` quedó **archivado/deprecado** (no editar ahí; solo
conserva `SKILL_AUTHORING.md` como guía de autoría). La ejecución sigue en el SERVIDOR
(Cowork/claude.ai): tras editar, empaquetar con `scripts/package_skill.py` y re-importar
el `.skill`. Detalle en `docs/MEJORA_CONTINUA_SKILLS.md`.

## División Claude Code vs. Cowork (tras separar repo de Drive, 2026-05-27)

Desde la migración, el reparto es estricto porque **el código vive en disco local
(`C:\Users\tnm33\Dev\FeesDefender`) y Cowork NO puede acceder a él** (Cowork solo
ve Google Drive).

**Claude Code (aquí, local) → todo lo que toque CÓDIGO:**
- Cambios en `core/`, `scripts/`, `tests/`, `streamlit_app.py`, etc.
- Git (commit, push), pytest, ejecución de la app.

**Cowork (nube/móvil) → trabajo jurídico, sin tocar código:**
- Redacción de escritos procesales `.docx` (preview + Save button).
- Comunicaciones a clientes vía Gmail / Drive (MCPs preinstalados).
- Investigación CENDOJ (Chrome MCP listo).
- Análisis de un caso concreto sin tocar código.
- Lectura del estado del proyecto y la planificación en el repo (`STATUS.md`,
  `PLAN.md`); desde el móvil, vía app de GitHub.

**Constructor de la sala de lectura — reparto real (2026-07-19, MCP consolidado):**
**Cowork ES el organizador de la sala.** Por el MCP `expedientes-xl` (extensión `.dxt`,
puente Claude Desktop) lee el Drive del despacho a velocidad de disco y **copia
server-side texto Y binarios** (`copy_path`/`copy_dir`; los bytes no pasan por el
modelo): crea la estructura plana, clasifica y nombra canónicamente, copia los
documentos (texto y PDF/fotos/vídeos/`.xlsx`) y genera los índices (`INDICE.md`,
`CRONOLOGIA.md`, `_MANIFIESTO.md`, `indice_documental.yaml`). Cowork-en-PC es por tanto
**constructor completo**, no solo texto: desaparece el antiguo "residuo de binarios" y el
paso local mecánico obligatorio (`MEJORAS #40` cerrado; el viejo `server-filesystem` Node
`expedientes` queda jubilado). Si el caso está en **local** (Desktop tras un checkout),
`expedientes-xl` no llega (sandbox `G:`/`H:`): se usa el filesystem del entorno (nativo en
Claude Code, montaje bash en Cowork). En **nube pura** (sin montaje) se prefiere el conector
`google-despacho` (ve el Drive del despacho, cuenta TL) sobre el conector nativo de E&V
(`nikolai.tyukhay@engelvoelkers.com`), que no ve «EXPEDIENTES - TYUKHAY LEGAL». Detalle en
`docs/superpowers/specs/2026-07-16-mcp-drive-disco-local-design.md` y `docs/DEAD_ENDS.md`.

Cowork NO debe trabajar la carpeta obsoleta de Drive
(`...\Base datos expedientes _OBSOLETO_borrar_tras_2026-06-10`).
