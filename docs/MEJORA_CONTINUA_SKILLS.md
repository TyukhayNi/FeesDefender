# Mejora continua y registro en expediente de las skills procesales

Gobernanza del sistema que (Parte I) hace que las skills procesales **guarden y
registren** sus outputs en el expediente, y (Parte II) hace que **aprendan de su
uso real**. Implementa el plan v3 (`PLAN_skills_registro_y_mejora_v3`).

> **Fuente única de verdad (desde 2026-06-12):** todas las skills del despacho se
> versionan y editan en **`.claude/skills/`** de este repo. El repo externo
> `despacho-skills` quedó **archivado** (no editar ahí; solo conserva
> `SKILL_AUTHORING.md`). La fuente de **ejecución** es el SERVIDOR (Cowork/claude.ai):
> editar aquí → `scripts/package_skill.py` → re-importar el `.skill`.

## Skills en alcance

`escritos-judiciales`, `cendoj-descarga`, `preparacion-audiencia-previa`,
`preparacion-juicio-oral` y `preparacion-litigio-civil`. Las genéricas
(`docx`, `xlsx`, `pdf`) no se tocan.

## Helpers canónicos (fuente única en `.claude/skills/_shared/`)

Se copian byte a byte a la carpeta `scripts/` de cada skill con
`scripts/sync_skill_helpers.py` (test de no-drift: `tests/test_skill_helpers_sync.py`).
Son stdlib pura: una skill empaquetada (`.skill`) es autónoma, también en móvil.

| Helper | Función |
|---|---|
| `registrar_outputs.py` | Registra cada output: manifiesto `<destino>/_index.md` + wikilinks en `## Navegación` de `_caso.md`. Idempotente, atómico, guardia contra `90_Notas personales`. |
| `scaffold_caso.py` | Scaffolder común (árbol `CASO_SUBDIRS` + `_caso.md` mínimo). Mismo árbol que el core E&V → no divergencia (`tests/test_scaffold_particular.py`). |
| `registrar_uso.py` | Telemetría de uso (JSONL `ts/skill/version/ref/accion/archivos/metricas`). |
| `programar_revision.py` | Emite el descriptor de revisión para la skill `schedule` con los plazos del despacho. |

## Scripts de análisis (en `scripts/`, los ejecuta Cowork — no se empaquetan)

| Script | Función |
|---|---|
| `capturar_delta.py` | Delta borrador↔`_FIRMADO` (python-docx + difflib) → `<ref>_delta.md`. La señal más rica. |
| `motor_mejora.py` | Por umbral (5+ usos con post): agrega uso+post+deltas → `MEJORAS_<skill>.md` con propuestas ancladas a datos. |

## El bucle

1. **Generación** → la skill guarda en `<case>/<destino>/`, registra (`registrar_outputs.py`) y deja telemetría (`registrar_uso.py`).
2. **Checklist previo** → `<ref>_pre.jsonl` al iniciar.
3. **Revisión programada** → `programar_revision.py` agenda (vía skill `schedule`) la revisión post-acto.
4. **Tras el acto/firma** → checklist post (`<ref>_post.jsonl`) + `capturar_delta.py` sobre borrador y `_FIRMADO`.
5. **Cierre del bucle** → con 5+ usos con post, `motor_mejora.py` emite `MEJORAS_<skill>.md`.
6. **Handoff a Code** → se aplican las mejoras aprobadas al `SKILL.md` (ver «Flujo de aplicación»).

### Plazos de la revisión programada (decisión del despacho)

| Tipo de acto | Plazo |
|---|---|
| Audiencia previa (`ap`) | fecha del acto **+ 3 días** |
| Juicio (`juicio`) | fecha del acto **+ 7 días** |
| Escrito (`escrito`) | presentación **+ 15 días** (o al detectar `_FIRMADO`) |

## Store de datos (sensible)

`data/_skill_logs/<skill>/` — `uso.jsonl`, `<ref>_pre/post.jsonl`,
`<ref>_delta.md`, `<ref>_schedule.json`, `MEJORAS_<skill>.md`. Contiene
referencias reales y **texto de escritos** (en los deltas). Por eso:

- Está **git-ignorado** (`data/_skill_logs/`): nunca se versiona ni se empuja a origin.
- **Nunca** se empaqueta en un `.skill` (`package_skill.py` excluye `logs/` salvo `README.md`).
- Los deltas son work-product interno **sin anonimizar** (decisión del despacho); excluidos del empaquetado.
- Nunca se escribe en `90_Notas personales`.

## Frontera Cowork / Claude Code

| Acción | Quién |
|---|---|
| Telemetría, checklists, delta, informe `MEJORAS_<skill>.md` | **Cowork** (helpers + scripts de análisis) |
| Editar `SKILL.md`, subir `version`, `## Changelog`, sincronizar helpers, empaquetar | **Claude Code** |

## Flujo de aplicación por Claude Code (handoff)

Cuando existe `data/_skill_logs/<skill>/MEJORAS_<skill>.md`:

1. **Revisar** cada propuesta y su evidencia (ref + fichero de log/delta citados).
2. **Aplicar** al `SKILL.md` solo las aprobadas (defaults y procedimientos, no menús).
3. **Subir `version`** en el frontmatter (`X.Y`).
4. **Anotar `## Changelog`** con la mejora y **la evidencia que la motiva** (auditabilidad: encaja con la cultura source-locked del despacho).
5. **Sincronizar y empaquetar**: `python scripts/sync_skill_helpers.py` + `python scripts/package_skill.py <skill_dir>`.
6. **Reinstalar** la skill (re-importar en Cowork/claude.ai — el servidor es la fuente de verdad de las skills de usuario).

## Estado

Mecanismo completo y con tests. Líneas base en `version: "1.0"`. El **primer
ciclo real** de mejora se cerrará cuando una skill acumule 5+ usos reales con su
checklist post; hasta entonces `motor_mejora.py` informa «aún no» (o `--force`).

## Seguimiento del core

Ver `docs/MEJORAS_FUTURAS.md` #30: que el core reconozca los manifiestos
`<subdir>/_index.md` y resuelva los wikilinks de `## Navegación`.
