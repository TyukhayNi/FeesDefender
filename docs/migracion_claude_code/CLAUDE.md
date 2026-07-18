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
  `cd "G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes"`.
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
cd "G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes"
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
- **API sudespacho**: `docs/INTEGRACION_SUDESPACHO.md`
- **Callejones sin salida**: `docs/DEAD_ENDS.md` ← consultar antes de reintentar algo
- **Plan subdivisión ciudades**: `docs/superpowers/plans/PLAN_SUBDIVISION_CIUDADES.md`
- **Plan SaRS1 anon**: `docs/superpowers/plans/PLAN_SaRS1_anon_pipeline.md`
- **Plan pre-relleno LLM**: `docs/superpowers/plans/PLAN_PRERELLENO_LLM_VIABILIDAD.md`
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

## Cuándo NO usar Claude Code para algo

Estos trabajos son más cómodos en Cowork — mantenerlos allí:

- Redacción de escritos procesales `.docx` (preview + Save button).
- Comunicaciones a clientes vía Gmail / Drive (MCPs preinstalados).
- Investigación CENDOJ (Chrome MCP listo).
- Análisis de un caso concreto sin tocar código.

Para el resto: usar Claude Code.
