# FeesDefender — Instrucciones del proyecto (Claude Code)

> Equivalente al "Project instructions" de Cowork. Se carga automáticamente al abrir Claude Code en este directorio.

## Qué es esto

Sistema legal-tech para automatizar análisis y defensa de honorarios de
intermediación inmobiliaria en España. Cliente principal: Engel & Völkers
(EV MMC SPAIN, S.L.U.). Usuario: Nikolai Tyukhay, abogado.

## Idioma

Responder siempre en castellano salvo que el usuario inicie en otro idioma.
Las comunicaciones a clientes de origen ruso o ex-URSS van en ruso por defecto.

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

Código: este directorio (`C:\Users\tnm33\Dev\FeesDefender`), versionado en Git →
`github.com/TyukhayNi/FeesDefender`. Disco local, sin latencia de Drive.

## Reglas que nunca se rompen

- Arquitectura 3 capas: UI → Core (`core/`) → Datos (`data/CASOS/`). La lógica
  vive en el core, la UI solo orquesta. Nunca mover lógica a Streamlit.
- `data/CASOS/` está en `.gitignore`. Nunca a GitHub. Contiene expedientes reales.
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

### Cierre de sesión

```powershell
python -m scripts.session_close
```

Equivalentemente, slash command `/cierre`.

El cierre actualiza `STATUS.md`, valida que la suite sigue verde, prepara
mensaje de commit. La memoria persistente (en mi memoria global, no en el
repo) la actualizo yo en el chat antes de cerrar.

## Tests

- Framework: `pytest`.
- Comando rápido: `python -m pytest -q --tb=no`.
- Comando con cobertura por fichero: `python -m pytest -q --tb=no <ruta>`.
- 546/546 verdes en s20 (2026-05-19). Cualquier número distinto debe ser
  explicado en `STATUS.md`.

Atajo: `/tests` ejecuta la suite completa.

## Referencias rápidas

- **Estado y tareas**: `STATUS.md` (raíz del proyecto)
- **Arquitectura y deps**: `docs/ARQUITECTURA.md`
- **API sudespacho**: `docs/INTEGRACION_SUDESPACHO.md` (su §14 fusiona la **referencia común sudespacho**)
- **Referencia común sudespacho** (fuente única agnóstica: auth, API de elementos, permisos + presets por
  rol, enums; compartida con El Contable / El Auditor): [`../ElContable/docs/REFERENCIA_SUDESPACHO_API_PERMISOS.md`](../ElContable/docs/REFERENCIA_SUDESPACHO_API_PERMISOS.md)
- **Callejones sin salida**: `docs/DEAD_ENDS.md` ← consultar antes de reintentar algo
- **Plan subdivisión ciudades**: `docs/PLAN_SUBDIVISION_CIUDADES.md`
- **Plan SaRS1 anon**: `docs/PLAN_SaRS1_anon_pipeline.md`
- **Plan pre-relleno LLM**: `docs/PLAN_PRERELLENO_LLM_VIABILIDAD.md`
- **Motor documental (split/OCR/MD) + empaquetado**: `docs/PLAN_MOTOR_DOCUMENTAL.md` (`MEJORAS #48`)
- **Mejoras futuras**: `docs/MEJORAS_FUTURAS.md`
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

Cowork NO debe trabajar la carpeta obsoleta de Drive
(`...\Base datos expedientes _OBSOLETO_borrar_tras_2026-06-10`).
