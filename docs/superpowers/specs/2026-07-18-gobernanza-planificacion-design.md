---
titulo: Gobernanza de la planificación — cola legible, ledger de cerrados, guardarraíl y reubicación de planes
estado: vigente
dueño: Nikolai Tyukhay
fecha: 2026-07-18
---

# Gobernanza de la planificación — diseño

> Spec de mejora organizativa de la planificación de FeesDefender. Extiende, sin
> contradecirla, la doctrina de `docs/GOBERNANZA_FUENTES_VERDAD.md` (2026-07-05) y
> el mapa SSOT de `docs/ARQUITECTURA_RELACIONES.md`. **Revierte** una decisión
> puntual de aquella doctrina (§Fase 3.6, "etiquetar, no mover") — ver §9.

## 1. Contexto y motivación

El modelo de planificación ("cada hecho tiene un único hogar; todo lo demás
enlaza") es correcto y **no se rediseña**. Lo que está roto es la *ejecución*: la
cola no se lee de un vistazo y la gobernanza manual se ha degradado justo donde no
se automatizó. Diagnóstico cuantificado (verificado contra el repo el 2026-07-18):

- **`STATUS.md` es ilegible como "estado".** 502 líneas / 315 KB / **125 bloques
  de cierre** apilados en orden inverso *antes* de las secciones de estado real
  (`Estado general` está en la línea ~294). Un fichero de estado de 315 KB deja de
  leerse → los hechos se copian a otro sitio → drift.
- **La rotación de STATUS se hizo una vez y se abandonó.** `docs/bitacora/` tiene
  **un solo fichero** (`STATUS_cola_historica_pre_2026-07.md`). La recomendación
  nº1 de la doctrina (rotar a `bitacora/AAAA.md` cuando STATUS supere ~400 líneas)
  quedó como prosa manual y se evaporó; hoy STATUS es más grande que las 253 KB que
  la motivaron.
- **`PLAN.md` no responde "¿qué toca ahora?".** 1620 líneas / 141 KB, **14 bloques
  ✅ completados expandidos inline** ("patrón del repo"), 55 `[x]` frente a 35 `[ ]`.
  El `[SIGUIENTE]` real vive en `STATUS.md`, no en la cola; la sección "MÁXIMA
  PRIORIDAD" está vacía. No hay orden de prioridad explícito.
- **`MEJORAS_FUTURAS.md` acumula igual.** 2668 líneas, 71 entradas, 25 resueltas
  pero expandidas inline (fuera del alcance de este spec; se aplica la misma lógica
  cuando toque).

**La lección rectora.** De las recomendaciones de 2026-07-05, sobrevivieron las que
se cablearon en un test (taxonomía) o en `session_close` (guardarraíl PLAN↔git); se
degradaron las que se dejaron como "acuérdate de rotar/podar". Por tanto: **toda
regla de este spec se convierte en un test o en un aviso de `session_close`, nunca
en prosa que hay que recordar.**

## 2. Objetivos

- Que `PLAN.md` responda "qué toca ahora y en qué orden" de un vistazo.
- Que los ítems cerrados no ahoguen la cola, sin partir su hogar de ciclo de vida.
- Que la limpieza no se vuelva a degradar (cerrojo automático).
- Que se sepa de un vistazo qué plan legacy está ejecutado y qué no.
- Que `docs/` raíz contenga solo documentos de gobernanza/referencia; los planes
  viven en un único hogar de planes.

## 3. No-objetivos

- **No** rediseñar el modelo "un hecho → un hogar" (es correcto).
- **No** rotar STATUS.md ni terminar la migración prosa→puntero en este spec — es la
  fase **C**, registrada como fast-follow (§7).
- **No** estampar `estado:` en los 69 specs/planes de `docs/superpowers/` (delegan su
  ciclo de vida en `PLAN.md`; hacerlo crearía un segundo hogar de estado para ellos).
- **No** tocar `MEJORAS_FUTURAS.md` en este spec.

## 4. Diseño

### D1 — Cabecera de cola priorizada en `PLAN.md`

Tabla compacta al inicio de `PLAN.md`, ordenada por prioridad, con columnas fijas:

```
## 🎯 Cola priorizada  (orden = prioridad; fila #1 = lo que toca ahora)

| # | Ítem | Estado | Gate / disparador | Esf. |
|---|------|--------|-------------------|------|
| 1 | B5 auto-derivar --folder-id | en curso | desbloqueado | medio |
| 2 | MCP Drive-disco V1 | spec lista | mergear PR #48 | alto |
| 3 | Split F2 (sala de máquina) | pendiente | desbloqueado | medio |
| … | … | … | … | … |

> Detalle de cada ítem en su bloque [SIGUIENTE-*] más abajo.
```

- **Convención: la fila #1 es "lo que toca ahora".** No hay bloque "AHORA" aparte
  (sería un segundo hogar que se desincroniza).
- **El `[SIGUIENTE]` sale de `STATUS.md`.** STATUS deja de restatar el siguiente paso
  y **enlaza** a esta cola. Hogar único del "qué sigue".
- Cada fila enlaza (ancla markdown) a su bloque `[SIGUIENTE-*]` completo, que se
  mantiene tal cual más abajo.
- La columna **Gate/disparador** es la de mayor valor: recorriéndola se ve al
  instante qué está desbloqueado y qué está bloqueado (y por qué).

### D2 — Sección `## Cerrados` (colapsar los bloques ✅)

Los 14 bloques ✅ hoy expandidos se colapsan a **una línea cada uno**, en una sección
`## Cerrados` dentro del propio `PLAN.md` (no en subcarpeta: mover partiría el hogar
del ciclo de vida, que el modelo fija en `PLAN.md`).

```
## ✅ Cerrados
> Ciclo de vida cerrado. Narrativa completa: git log + el spec/plan enlazado.

- ✅ **[APERTURA B1-B4]** ficha CRM + quick wins — PR #69/#71/#72 · [spec](2026-07-18-apertura-expediente-b1-b5-design.md)
- ✅ **[INPUT-LOTES]** layout 00_Input por lotes — PR #57 (8142d97) · [spec](2026-07-17-layout-00-input-lotes-design.md)
- ✅ **[BIBLIOTECA-CHECKOUT]** checkout/checkin Desktop↔Drive — PR #4/5/6/7
- …
```

- **Lista plana, reciente primero** (espeja `git log`). Cada línea = etiqueta +
  título breve + PR/hash + enlace al spec. Es un *ledger fino*, no un archivo
  navegable: la narrativa vive en git y en el spec enlazado.
- **Al cerrar un ítem**, su bloque se colapsa a una línea y esa línea salta al
  principio de `## Cerrados`.
- **Promoción a agrupación por área** (subtítulos temáticos: Intake / MCP /
  Seguridad / Salas…) cuando `## Cerrados` supere **~30 entradas** — punto donde la
  lista plana deja de escanearse. El disparador lo avisa E1 (D3); no es "cuando
  parezca". Pasar de lista plana a agrupada es trivial cuando llegue.

### D3 — Guardarraíl E1 en `session_close` (avisa, no bloquea)

Aviso al cierre de sesión (mismo patrón que `_avisar_plan_desfasado` /
`_avisar_publicacion`; lógica pura extraíble a función testeable). Dispara si:

1. `STATUS.md` supera **400 líneas** → recordatorio de rotar (fase C).
2. `PLAN.md` tiene una cabecera `✅` **por encima** de la sección `## Cerrados` (es
   decir, un ítem cerrado sin colapsar) → recordatorio de colapsarlo al ledger.
3. `## Cerrados` tiene **≥ 30** entradas → recordatorio de agrupar por área (D2).

- **Avisa, no bloquea** (coherente con los avisos existentes; el cierre no debe
  fallar por higiene de docs).
- Se engancha en `scripts/session_close.py` donde ya corren los otros avisos.
- Red anti-regresión en `tests/test_session_close_aviso.py` (RED→GREEN) sobre la
  lógica pura (umbral de líneas, detección de `✅` fuera de Cerrados, conteo de
  Cerrados), sin depender del árbol real.

### D4 — Auditoría de estados de los planes legacy

Verificar y corregir el `estado:` del frontmatter para que INDICE refleje la verdad
de ejecutado/no. INDICE advierte que los estados actuales son "un primer pase
automatizado" — probablemente stale.

- **Ficheros:** los **11 `docs/PLAN_*.md`** + los **2 docs sin frontmatter**
  (`DESPLIEGUE_MCP_DRIVE_DISCO.md`, `prompt_handoff_expedientes_seguros.md`). Cierra
  el frontmatter de todo `docs/` de una pasada. Superpowers no se toca (§3).
- **Método:** por cada fichero, cruzar con `PLAN.md` / `STATUS.md` / `git log` /
  código y fijar `estado:` ∈ {`vigente`, `historico`, `aparcado`, `revisar`}. Los
  ambiguos van a `revisar` para que Nikolai confirme (convención de INDICE).
- **Salida:** actualizar el frontmatter de cada fichero **y** la columna de estado
  de la tabla de `docs/INDICE.md` (índice único). Cero enlaces rotos (solo se
  edita frontmatter y una tabla; los ficheros no se mueven en D4 — eso es D5).

Estado de partida de los 11 (a verificar, no dar por bueno):

| Plan | estado actual | ¿referenciado en código? |
|---|---|---|
| PLAN_DESPLIEGUE_EV | vigente | — |
| PLAN_INTAKE_CRM_COMPLETO | vigente | sí (`sync_sudespacho_legacy`) |
| PLAN_INTAKE_PROCURADORES_EMAIL | vigente | sí (`procurador_*`) |
| PLAN_PRERELLENO_LLM_VIABILIDAD | vigente | — |
| PLAN_SaRS1_anon_pipeline | vigente | sí (`test_anon_regresion_SaRS1`) |
| PLAN_SALA_LECTURA_01_PROCESADO | historico | — |
| PLAN_SUBDIVISION_CIUDADES | historico | sí (`ciudades`, `case_locator`, 2 scripts, 1 test) |
| PLAN_email_aplanado_anidados | historico | — |
| PLAN_email_enlaces_drive | historico | — |
| PLAN_BITACORA_CASOS | aparcado | — |
| PLAN_MOTOR_DOCUMENTAL | aparcado | — |

### D5 — Reubicar los planes legacy fuera de `docs/` raíz

Objetivo: `docs/` raíz = solo gobernanza/referencia; los planes en un **único** hogar
de planes.

- **Destino: `docs/superpowers/plans/`** — el hogar que YA existe para planes. Mover
  ahí los legacy **arregla** el drift #6 ("dos hogares para lo mismo") en vez de
  agravarlo. No se crea un tercer hogar (`docs/planes/`).
- **Se mueven los 11**, conservando su nombre `PLAN_*.md` (renombrarlos a la
  convención fechada solo rompería más enlaces sin ganar nada; la carpeta admite
  "nuevos con fecha + legacy con prefijo `PLAN_`", y se entiende solo).
- **Corrección de referencias en el mismo commit atómico:**
  - Código/tests (4 planes anclados): `SUBDIVISION_CIUDADES`
    (`core/ciudades.py`, `core/casos/case_locator.py`,
    `scripts/migrate_to_city_structure.py`, `scripts/verify_city_layout.py`,
    `tests/test_config_ciudades.py`), `INTAKE_CRM_COMPLETO`
    (`core/sync_sudespacho_legacy.py`), `INTAKE_PROCURADORES_EMAIL`
    (`core/procurador_*.py`), `SaRS1` (`tests/test_anon_regresion_SaRS1.py`). Son
    comentarios/docstrings, no lógica → la suite sigue verde.
  - Docs: `INDICE.md`, `PLAN.md`, `STATUS.md` y `docs/bitacora/`, y los specs de
    superpowers que los citen.
- **Verificación:** `grep` repo-wide final que confirme **cero** rutas `docs/PLAN_`
  colgando.
- **Desde el worktree**, no la raíz compartida (STATUS es fichero de alta
  contención entre sesiones/Cowork).

## 5. Enforcement y pruebas

- **D3 (E1)** es el enforcement central: convierte "rota STATUS / colapsa cerrados /
  agrupa" en avisos que corren solos en cada cierre.
- Tests: `tests/test_session_close_aviso.py` amplía la cobertura a los 3 nuevos
  avisos (lógica pura, sin árbol real).
- La auditoría (D4) se apoya en `INDICE.md` como índice único; no requiere test
  nuevo (es corrección de datos), pero D3.1 vigila el tamaño de STATUS que motiva C.

## 6. Secuenciación (2 PR + fast-follow)

- **PR-A:** D1 + D2 + D3 + D4 (cola, ledger Cerrados, guardarraíl, auditoría de
  estados, INDICE). Independiente de D5.
- **PR-B:** D5 (reubicación de los 11 planes + corrección de referencias). Separado
  para que el arreglo de la cola no quede rehén del chase de enlaces.
- **C:** fase aparte, por disparador (§7).

## 7. Fase C — fast-follow (registrada, no en este spec)

Rotación y saneado de `STATUS.md`, mayor superficie:

- Rotar los 125 bloques de cierre a `docs/bitacora/2026.md`.
- Partir STATUS en "estado vigente" (arriba, pequeño) + log (rotado).
- Terminar la migración prosa→puntero: `Arquitectura v2`, taxonomía y estructura de
  carpetas pasan a enlaces a `core/config.py` / `ARQUITECTURA.md` (Drifts #3/#4 de la
  doctrina).

**Disparador:** el primer aviso de E1 por STATUS>400 (ya se cumple hoy) o
inmediatamente tras aterrizar B. Se registra además como entrada de backlog en
`docs/MEJORAS_FUTURAS.md` con este disparador, para que no se vuelva a evaporar como
la rotación anterior.

## 8. Riesgos y mitigaciones

- **Reversión de decisión previa (D5).** La doctrina de 2026-07-05 rechazó mover los
  `PLAN_*.md` por churn + enlaces rotos. Se revierte a petición explícita del dueño;
  el beneficio es organizativo, no funcional. Mitigación: commit atómico + `grep` de
  cierre + suite verde; fallback documentado = "no mover + INDICE distingue".
- **Contención de `STATUS.md`.** Editado por `session_close` en cada cierre.
  Mitigación: trabajar desde worktree; PR-B en un momento sin otra sesión en cierre.
- **Degradación futura de la limpieza.** Es la causa raíz de este spec. Mitigación:
  D3 (guardarraíl), que es la única defensa real frente al "acuérdate de".

## 9. Qué revierte de la doctrina anterior

`GOBERNANZA_FUENTES_VERDAD.md §Fase 3.6` decidió "etiquetar, no mover" los 11
`PLAN_*.md`. Este spec **mueve** (D5) por decisión de Nikolai (2026-07-18), con el
objetivo nuevo de "docs/ raíz = solo gobernanza". Se conserva la parte de esa
decisión que sigue vigente: los specs/planes **nuevos** nacen en
`docs/superpowers/{specs,plans}/` (regla intacta). Tras D5, esa regla y la ubicación
de los legacy convergen en el mismo hogar.
