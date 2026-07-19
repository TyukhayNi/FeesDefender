---
tipo: handoff
estado: activo
creado: 2026-07-19
origen: sesión fase-2 despliegue MCP Drive-disco (20º cierre)
destino: sesión nueva de Claude Code — triaje de la cola de planificación
consumido_por: "(pendiente — apuntar el PR/spec que resulte del triaje)"
---

# HANDOFF — Triaje de la cola de planificación de FeesDefender

> Andamio de traspaso (efímero). El contenido durable que produzca el triaje va a `PLAN.md` /
> `docs/MEJORAS_FUTURAS.md` / ledger `## Cerrados`, no a este fichero. Marcar `estado: consumido` +
> `consumido_por:` cuando el triaje arranque y su resultado quede en su SSOT.

## Encargo (prompt de arranque)

ENCARGO: Triaje de la cola de planificación de FeesDefender (PLAN.md + backlog).

CONTEXTO Y PORQUÉ. El proyecto acumula diseño sin construir ("specs dormidos"): p. ej. Cronología
Unificada v7 (DISEÑO COMPLETO desde 2026-06-25, sin build), Motor Documental #48 (aparcado
2026-07-04), MEJORAS #75/#76 (sala de lectura, con una decisión-madre sin resolver). Nikolai quiere
ACABAR planes empezados, no abrir nuevos. Esta sesión es de GOBERNANZA/ANÁLISIS (docs-only hasta que
Nikolai apruebe acciones): NO construyas features.

ENTORNO. Windows + PowerShell. Repo: C:\Users\tnm33\Dev\FeesDefender (main PROTEGIDA → rama+PR,
leak-scan obligatorio; instala pre-commit si trabajas en worktree). Responder en castellano. GOTCHA
REAL: antes de fiarte de nada, verifica que estás en main ACTUALIZADO (git fetch + git status); la
raíz/worktree puede quedar en un commit viejo (detached) y mostrar estado obsoleto (pasó el 2026-07-19).

LEE ENTERO ANTES DE EMPEZAR:
- PLAN.md (cola priorizada "fila #1 = ahora" + bloques [SIGUIENTE-*] + ledger "## Cerrados").
- docs/MEJORAS_FUTURAS.md (backlog #1-#76).
- docs/GOBERNANZA_FUENTES_VERDAD.md (el estado de ciclo de vida vive SOLO en PLAN; STATUS =
  puntero+bitácora; git es el hogar de rama/pendiente-commit; regla de promoción backlog→cola).
- docs/bitacora/2026.md (cierres recientes = estado real de muchas cosas).
- docs/superpowers/2026-07-19-sala-lectura-procesado-exploracion.md (ya identifica los specs dormidos
  y la decisión-madre #56 vs #75).
- git log --oneline -40 y `gh pr list`.

MÉTODO — verificación anclada, NO fiarse de la prosa (puede estar desactualizada): para CADA ítem de la
cola y cada entrada relevante del backlog, verifica el ESTADO REAL contra código y git (¿el código
existe y está en main? grep/lectura del módulo + git log del fichero; ¿hay spec/plan?; ¿construido, a
medias o solo diseño?; ¿disparador concreto o especulativo?; ¿decisión pendiente que lo bloquea?).
RECOMENDADO: subagentes en paralelo (uno por ítem/cluster) que devuelvan un veredicto anclado a
fichero:línea; luego sintetiza. Es trabajo divisible.

CLASIFICA cada ítem en:
- CERRAR ✅ — ya hecho (verificado) pero la prosa no lo refleja → mover al ledger "## Cerrados" con hash.
- CONSTRUIR YA — disparador real + spec/plan listos → mantener/subir en la cola.
- RESOLVER DECISIÓN — bloqueado por decisión de arquitectura pendiente (p. ej. #56 vs #75) → escalar a
  Nikolai con opciones.
- ARCHIVAR — diseño dormido sin disparador → marcar formalmente (estado: historico/aparcado), sacar de
  la cola activa; conservar el spec como referencia.
- MANTENER (diferido) — válido pero esperando disparador → dejar el disparador explícito.

ENTREGABLE (gate de Nikolai): informe de triaje (por ítem: estado real verificado con anclas → categoría
→ acción concreta → disparador/bloqueante). Destaca al principio (a) victorias rápidas (CERRAR ya), (b)
DECISIONES pendientes que desatascan varios ítems, (c) lo que recomiendas ARCHIVAR. Presenta y ESPERA OK
antes de tocar PLAN.md/MEJORAS/STATUS. Tras el OK, aplica los cambios de gobernanza (mover a ledger,
marcar archivado, actualizar disparadores) en rama+PR (docs-only), respetando GOBERNANZA_FUENTES_VERDAD.

REGLAS: no reinventar (ancla a lo existente); YAGNI; parar a preguntar ante cualquier decisión de
arquitectura o si algo no cuadra; no construir features en esta sesión.

## Mapa de estado conocido (2026-07-19, ventaja de arranque)

**PRs recientes:** #85 mergeado (`bc929e8`, skills migradas al consolidado `expedientes-xl` +
`CLAUDE.md` + MEJORAS #75/#76); #86 mergeado (`3b57348`, exploración del brainstorming + punto de retome
+ bitácora 20º cierre); #83 (`.dxt` de `expedientes-xl` a Cowork); #82/#80 (bugs de arranque del wrapper).

**Cola de PLAN.md (7 ítems, al 20º cierre):** (1) Split F2 sala de máquina; (2) Infra C — art. 156 LEC
(quick win); (3) Infra B — expediente scratch; (4) MCP sudespacho F1 (spec lista, gates de despliegue);
(5) Drive-disco pasos 5-7 + bundle Code (EN CURSO — ver punto de retome abajo); (6) abrir-caso
F3-judicial (diferida, caso real); (7) Google MCP F4 Calendar (diferida).

**Specs dormidos identificados (candidatos a ARCHIVAR o CONSTRUIR-con-disparador):**
- Cronología Unificada v7 — `docs/superpowers/specs/2026-06-25-cronologia-unificada-design.md`: DISEÑO
  COMPLETO (8 fases) desde junio, "siguiente paso = BUILD", sin construir.
- Motor Documental #48 — `docs/superpowers/plans/PLAN_MOTOR_DOCUMENTAL.md`: aparcado 2026-07-04.
- PLAN_BITACORA_CASOS — `docs/superpowers/plans/PLAN_BITACORA_CASOS.md`: aparcado, nunca implementado.
- Varios `historico` ya marcados en `docs/INDICE.md` (no requieren acción, confirmar).

**Decisión-madre pendiente (RESOLVER DECISIÓN, desatasca la sala de lectura):** #56 (revivir
`core.sala_lectura` determinista + tool MCP; la skill pasa a orquestador fino) **vs** #75 (skill
prompt-driven que consume MD). Detalle y trade-offs en la exploración citada arriba. Empezar por aquí.

**Ítem con trabajo pendiente CONCRETO (no dormido — NO archivar):** despliegue MCP Drive-disco fase 2,
`PLAN.md [SIGUIENTE-MCP-DRIVE-DISCO-PASOS-5-7]` (punto de retome: import en Cowork + verificación
funcional de `organizar-sala-lectura` → bundle Code B1-B3 → paso 7 irreversible jubilar `expedientes`
Node). Runbook en `docs/DESPLIEGUE_MCP_DRIVE_DISCO.md`.

**Fleco de gobernanza detectado (2026-07-19, aparte del triaje de PLAN):** los handoffs no tienen regla
de creación/almacenamiento/estado (dispersos en `docs/superpowers/`, `docs/`, `scratchpad`; INDICE
parcial). Propuesta de regla pendiente de aprobar (ubicación única `docs/superpowers/handoffs/` +
frontmatter de estado). Este fichero estrena la nomenclatura; la migración de los existentes queda para
cuando Nikolai apruebe la regla.
