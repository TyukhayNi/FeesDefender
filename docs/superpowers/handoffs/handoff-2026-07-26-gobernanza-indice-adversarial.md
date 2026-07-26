---
tipo: handoff
estado: consumido
creado: 2026-07-26
origen: conversación de diagnóstico (Claude chat) — auditoría manual de INDICE.md/PLAN.md/MEJORAS_FUTURAS.md vs. specs/plans reales
destino: sesión de revisión adversarial (múltiples subagentes en paralelo) — verificar el diagnóstico y decidir remediación
consumido_por: "docs/superpowers/specs/2026-07-26-gobernanza-indice-adversarial-review.md (2026-07-26): H1/H3/H4/H5 REFUTADOS, H2 CONFIRMADO CON MATIZ; test de INDICE descartado; 6 defectos reales D1-D6 (D1/D2 P1 en core/crm_atlas.py). Remediación pendiente en 3 PR."
---

# HANDOFF — Revisión adversarial del diagnóstico de gobernanza documental (INDICE/PLAN/specs/plans)

> Andamio de traspaso (efímero). El contenido durable que produzca la revisión va a `PLAN.md` /
> `docs/INDICE.md` / `docs/MEJORAS_FUTURAS.md` / tests nuevos en `tests/`, no a este fichero.
> Marcar `estado: consumido` + `consumido_por:` cuando la revisión arranque y su resultado quede en su SSOT.

## Encargo (prompt de arranque)

ENCARGO: Revisión adversarial del diagnóstico de huecos de gobernanza documental detectado en una
conversación de chat (no en sesión de Claude Code) el 2026-07-26. El diagnóstico se hizo por `grep`
manual cruzando `docs/superpowers/{specs,plans,handoffs}/`, `PLAN.md`, `docs/INDICE.md` y
`docs/MEJORAS_FUTURAS.md`. **No se verificó contra el estado real del código ni contra git log** — es
un diagnóstico puramente documental, de superficie. Esta sesión debe verificar cada hallazgo con el
mismo rigor que exige `docs/superpowers/handoffs/handoff-2026-07-19-triaje-plan.md` (verificación
anclada, no fiarse de la prosa) y ADEMÁS actuar de forma adversarial: buscar activamente por qué el
diagnóstico podría estar equivocado, incompleto, o resolviendo el síntoma equivocado.

CONTEXTO Y PORQUÉ. Nikolai preguntó en chat "cómo evitar perder ideas/decisiones del proyecto" y la
conversación derivó en auditar la gobernanza documental existente (`GOBERNANZA_FUENTES_VERDAD.md`,
`session_close.py`, `INDICE.md`). Se encontraron varios huecos de completitud. El riesgo de que este
diagnóstico esté sesgado es alto porque: (a) se hizo con `grep` de texto simple, que da falsos
negativos si el nombre del fichero se cita parcialmente o con guiones distintos; (b) no se distinguió
sistemáticamente "spec/plan legítimamente cerrado sin necesidad de estar en la cola activa" de
"spec/plan verdaderamente perdido"; (c) no se leyó el contenido de los plans "NO citados" para
confirmar si de verdad están huérfanos o si el trabajo se completó y se documentó con otro nombre en
el ledger.

ENTORNO. Windows + PowerShell. Repo: `C:\Users\tnm33\Dev\FeesDefender` (main protegida → rama+PR,
leak-scan obligatorio). Responder en castellano. Sesión de GOBERNANZA/ANÁLISIS (docs-only hasta que
Nikolai apruebe acciones): no construir features, no tocar código de producción.

LEE ENTERO ANTES DE EMPEZAR:

- `PLAN.md` completo (cola + `## Cerrados`).
- `docs/INDICE.md` completo.
- `docs/MEJORAS_FUTURAS.md` (backlog + regla de promoción `[PROMOVIDO → PLAN.md]` / `MEJORAS #NN`).
- `docs/GOBERNANZA_FUENTES_VERDAD.md` (principio rector + diagnóstico de drift original + fases).
- `docs/ARQUITECTURA_RELACIONES.md` (tabla SSOT).
- `scripts/session_close.py` (funciones `_avisar_plan_desfasado`, `_avisar_higiene_planificacion`).
- `tests/test_docs_gobernanza.py`.
- Los 44 ficheros de `docs/superpowers/specs/*.md` y 54 de `docs/superpowers/plans/*.md` — al menos el
  nombre y fecha de cada uno; leer completos los marcados como "hueco" abajo.
- `docs/bitacora/2026.md` (para confirmar si un plan "no citado en PLAN.md" en realidad se cerró y
  quedó registrado ahí en vez de en el ledger de `PLAN.md`).
- `git log --oneline -100` y, si aplica, `gh pr list --state all` para contrastar fechas de merge
  contra las fechas de spec/plan.

MÉTODO — verificación adversarial, no confirmatoria: para cada hallazgo de la sección "Hallazgos a
verificar" de abajo, el objetivo NO es confirmar que el hueco existe — es intentar refutarlo primero.
Concretamente:

1. Re-ejecutar el cruce con `grep -i` y también buscando por fragmentos parciales del nombre (no solo
   el stem completo), por si el diagnóstico original tuvo falsos negativos por variantes de nombre.
2. Para cada plan "NO citado en PLAN.md", comprobar en `git log --oneline -- <ruta_del_plan>` y en
   `docs/bitacora/2026.md` si el trabajo asociado se mergeó y se documentó allí sin usar el nombre
   exacto del fichero — en ese caso el hueco es falso o menos grave de lo diagnosticado.
3. Para `crm-atlas` en particular: confirmar el commit `87ff113` existe en `git log`, confirmar que
   Fase A está realmente en producción (no solo mergeada a una rama), y confirmar si Fase B tiene
   algún rastro en código (aunque no esté en PLAN.md) que indique que ya arrancó.
4. Cuestionar la propuesta de remediación (test `test_specs_plans_handoffs_citados_en_indice`): ¿es el
   nivel correcto de rigor, o generaría demasiado ruido/falsos positivos (p. ej. specs deliberadamente
   no indexados, drafts, ficheros de exploración que no deberían promocionarse a INDICE.md)?

RECOMENDADO: subagentes en paralelo, uno por hallazgo, con veredicto anclado a fichero:línea o commit.

CLASIFICA cada hallazgo en:

- CONFIRMADO — el hueco es real tal como se describe, sin matices.
- CONFIRMADO CON MATIZ — el hueco existe pero la severidad o el alcance dicho es incorrecto.
- REFUTADO — el hallazgo es un falso positivo (ej.: el trabajo sí está documentado, solo que con otro
  nombre/ubicación que el `grep` original no encontró).
- NO VERIFICABLE — no hay suficiente rastro (código, git, docs) para confirmar ni refutar.

ENTREGABLE (gate de Nikolai): informe adversarial por hallazgo (veredicto + evidencia ancla + acción
recomendada si CONFIRMADO). Al final, veredicto sobre la remediación propuesta (test de completitud
INDICE.md + aviso no-bloqueante de specs/plans sin cola activa): ¿implementarla tal cual, con qué
umbral de fecha (p. ej. solo aplica desde 2026-07-XX en adelante, sin exigir retrofit de todo el
histórico), o rediseñarla? Presentar y ESPERAR OK antes de tocar `PLAN.md`/`INDICE.md`/`tests/`.

REGLAS: no reinventar (ancla a lo existente); YAGNI; parar a preguntar ante cualquier decisión de
arquitectura o si algo no cuadra; no construir features en esta sesión; no marcar nada como
CONFIRMADO sin evidencia anclada a fichero:línea, commit o entrada de bitácora.

## Hallazgos a verificar (diagnóstico de origen, sin verificar contra código/git)

### H1 — `docs/INDICE.md` no indexa nada posterior al 2026-07-19

La última fecha citada en `docs/INDICE.md` es `2026-07-19-triaje-plan`. Todo spec/plan con fecha
2026-07-20 en adelante no aparece:

- `2026-07-20-crm-atlas-descubrimiento-design.md` (spec)
- `2026-07-20-crm-atlas-fase-b.md` (plan)
- `2026-07-21-preclasificacion-sala-lectura.md` (plan) — **este sí está en PLAN.md** como
  `[SIGUIENTE-PRECLASIFICACION-SALA-LECTURA]`, pero no en INDICE.md
- `2026-07-21-robustez-velocidad-sala-lectura.md` (plan)
- `2026-07-21-robustez-velocidad-sala-lectura-tdd.md` (plan)
- `2026-07-22-robustez-velocidad-sala-lectura-tdd-9-16.md` (plan)
- `2026-07-23-emails-atomizados-sala-lectura-design.md` (spec)
- `2026-07-23-emails-atomizados-sala-lectura-adversarial-review.md` (spec/revisión)

Verificar: ¿alguno de estos ya se cerró y el criterio real es "solo se indexan specs/plans activos",
en cuyo caso el hueco es menor? ¿O `INDICE.md` simplemente dejó de mantenerse tras el 19-07?

### H2 — `crm-atlas` (Fase A y Fase B) ausente de `PLAN.md` y de `docs/bitacora/2026.md`

Ni el string `atlas` ni el commit `87ff113` (citado en `docs/CRM_SUDESPACHO_ATLAS.md` como el commit
donde se construyó y testeó Fase A) aparecen en `PLAN.md`, `STATUS.md` ni `docs/bitacora/2026.md`.
`docs/CRM_SUDESPACHO_ATLAS.md` marca Fase B como `⏳ pendiente` con plan de implementación detallado
(`docs/superpowers/plans/2026-07-20-crm-atlas-fase-b.md`) que nunca entró en la cola `[SIGUIENTE-...]`
de `PLAN.md`. Verificar: ¿el commit `87ff113` existe realmente en `git log`? ¿Fase A está en `main`
actual? ¿Hay algún motivo legítimo (p. ej. decisión consciente de mantenerlo fuera de la cola porque
no hay disparador todavía, similar a los "specs dormidos" que ya identificó
`handoff-2026-07-19-triaje-plan.md`) que el diagnóstico original no consideró?

### H3 — 24 de 54 plans sin cita textual en `PLAN.md` ni `docs/INDICE.md`

Cruce por `grep` del stem de cada fichero de `docs/superpowers/plans/*.md` contra `PLAN.md`: 19 de 54
SÍ aparecen citados, 35 NO. De esos 35, 9 son `PLAN_*.md` legacy que SÍ están en `docs/INDICE.md` con
`estado: historico/aparcado/revisar` (sin problema, ciclo de vida documentado). Los otros 24 no
aparecen en ningún sitio:

Franja junio (probable trabajo cerrado hace tiempo, colapsado sin preservar referencia):
`2026-06-10-dedup-guard-robusto`, `2026-06-12-f2-bandeja-correos-ui`,
`2026-06-12-search-expedientes-rest`, `2026-06-15-intake-whatsapp-fase-a`,
`2026-06-17-sala-lectura-f0a3`, `2026-06-17-sala-lectura-f4f6`,
`2026-06-18-organizar-sala-lectura-y-triaje-drive`, `2026-06-22-empaquetado-plugin-feesdefender`,
`2026-06-22-expedientes-xl-conector`, `2026-06-22-intake-skill-trazabilidad`,
`2026-06-25-adjuntos-contenido-fase2`, `2026-06-25-email-atomize-fase2`,
`2026-06-25-email-atomize-fase3-capa-caso`, `2026-06-25-email-atomize-media-reconstruida`,
`2026-06-25-whatsapp-atomize`.

Franja julio 13-20 (zona ciega más reciente, más urgente de verificar):
`2026-07-13-gmail-mcp-escritura-etiquetas`, `2026-07-13-mcp-sudespacho-f1`,
`2026-07-14-viabilidad-prerelleno-mejoras`, `2026-07-16-mcp-drive-disco-local-v1`,
`2026-07-18-apertura-b1-b5-pr1-quickwins`, `2026-07-18-apertura-b1-b5-pr2-case-id`,
`2026-07-18-apertura-b1-b5-pr3-ficha-crm`, `2026-07-18-apertura-b5-autoderivar`,
`2026-07-18-gobernanza-planificacion` (⚠ el propio plan que diseñó el sistema de gobernanza que se
está auditando), `2026-07-20-crm-atlas-fase-b` (ver H2).

Verificar caso por caso (o por lotes/subagente) si cada uno: (a) se completó y está en `main` —
revisar git log del código asociado; (b) se completó y está registrado en `docs/bitacora/2026.md` con
otro nombre/redacción; (c) es un sub-plan de otro spec ya cerrado (p. ej. los tres PR de
`apertura-b1-b5` podrían estar cubiertos por la entrada `[abrir-caso]` de `PLAN.md` línea ~131, que sí
existe pero no cita los stems exactos de los PR — **esto podría ser un falso positivo del diagnóstico
original, revisar primero**).

### H4 — Frontmatter inconsistente entre specs (YAML vs. prosa libre)

Ejemplo confirmado: `docs/superpowers/specs/2026-07-18-gobernanza-planificacion-design.md` usa YAML
(`titulo`, `estado`, `dueño`, `fecha`); `docs/superpowers/specs/2026-06-10-dedup-guard-robusto-design.md`
usa prosa libre en negrita (`**Fecha:**`, `**Estado:**`). Los `plans/` no tienen frontmatter en
absoluto — el enlace a su spec vive como texto libre en el cuerpo. Verificar alcance real: ¿cuántos de
los 44 specs usan cada formato? ¿Migrar todos a YAML es proporcionado, o basta con exigirlo solo en
specs nuevos a partir de una fecha de corte?

### H5 — `docs/MEJORAS_FUTURAS.md` sin cableado hacia trabajo reciente

La regla de promoción (`[PROMOVIDO → PLAN.md]` + `MEJORAS #NN`) está documentada y se ve aplicada en
títulos de `PLAN.md` (`MEJORAS #54`, `MEJORAS #48`, `MEJORAS #37`). Pero no se encontró ninguna entrada
de `MEJORAS_FUTURAS.md` que origine `crm-atlas` ni los specs de sala-lectura de julio — el propio spec
de `crm-atlas` declara como origen "petición de Nikolai", saltándose el backlog. Verificar: ¿esto es
sistemático (trabajo por petición directa nunca pasa por MEJORAS_FUTURAS.md, lo cual podría ser
correcto por diseño) o hay entradas de backlog relevantes que sí deberían haberse citado y no se
citaron?

## Remediación propuesta (NO implementada, pendiente del veredicto de esta revisión)

Test propuesto en la conversación de origen (no escrito, solo esbozado):

```py
# tests/test_indice_completo.py — BORRADOR, no confirmado por revisión adversarial
"""Guard: todo spec/plan/handoff de superpowers debe estar citado en INDICE.md."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUPERPOWERS = ROOT / "docs" / "superpowers"

def _stems(carpeta: str) -> set[str]:
    return {p.stem for p in (SUPERPOWERS / carpeta).glob("*.md")}

def test_specs_plans_handoffs_citados_en_indice():
    indice = (ROOT / "docs" / "INDICE.md").read_text(encoding="utf-8")
    faltan = []
    for carpeta in ("specs", "plans", "handoffs"):
        for stem in _stems(carpeta):
            if stem not in indice:
                faltan.append(f"{carpeta}/{stem}.md")
    assert not faltan, f"Ficheros sin citar en INDICE.md: {faltan}"
```

Además se esbozó (sin código) un aviso no-bloqueante en `session_close.py`,
`_avisar_specs_sin_plan_activo()`, análogo a `_avisar_plan_desfasado`, para specs/plans recientes sin
mención en `PLAN.md` ni `docs/bitacora/2026.md`.

La revisión adversarial debe pronunciarse sobre si este diseño es el correcto antes de implementarlo:
en particular, si un test bloqueante sobre TODO el histórico (89 ficheros) generaría trabajo de
retrofit desproporcionado, y si conviene acotar el test a ficheros con fecha posterior a un corte
(p. ej. solo exigir la cita para specs/plans creados después de la fecha en que el test se active).

## Notas de origen

Este handoff se generó desde una conversación de chat (no una sesión de Claude Code), en la que se usó
`bash_tool` para clonar el repo público de GitHub (`https://github.com/TyukhayNi/FeesDefender`) y
`grep` manual — no se ejecutó ningún test existente ni se corrió `session_close.py`. Tratar todo lo
anterior como hipótesis a verificar, no como hechos establecidos.
