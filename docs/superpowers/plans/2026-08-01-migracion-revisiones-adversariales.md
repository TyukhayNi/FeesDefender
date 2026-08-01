# Migración de la gobernanza de revisiones adversariales — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> 🔴 **NO EJECUTAR TODAVÍA — este plan está alineado con la rev. 5 del spec y la vigente es la rev. 6.**
> La ronda 4 devolvió NO-SHIP con ocho hallazgos (§17 del spec) y la rev. 6 cambió el contrato en cinco
> puntos que este plan codifica literalmente:
>
> 1. **`clase` se parte en dos ejes**: `clase: diseño | rama` **más** `independencia: independiente |
>    autor`. Desaparece `autorrevision` como clase → afecta a `_CLASES` (Tarea 1) y a la **Tarea 8**
>    entera.
> 2. **La ficha pasa de ocho a nueve líneas** (entra `Independencia`) → `_CAMPOS_FICHA` y todas las
>    fichas de las Tareas 2, 3, 6, 7 y 8.
> 3. **G7 aplica una relación nueva y fail-closed**: `Cobertura: ejecutada` exige que `Informe recibido`
>    resuelva a un acta existente. Cambia el cuerpo del test de la Tarea 1.
> 4. **El frontmatter del acta gana `independencia` y `marcador_nonce`**, y los marcadores llevan nonce
>    → `_CLAVES_ACTA` (Tarea 4) y el extractor del bloque literal (Tarea 5).
> 5. **El nombre del acta lleva revisor y commit siempre** y admite `diagnostico` → la regla de
>    renombrado de la Tarea 5.
>
> **Orden correcto:** primero la **comprobación dirigida del diff `24f8abe` → HEAD** que ordena el §13
> del spec; después se realinea este plan; después se ejecuta. Realinearlo ahora sería retrabajo, porque
> esa comprobación puede tocar los mismos ejes.

**Goal:** llevar el corpus de revisiones adversariales postcorte al contrato del spec —encabezado canónico, ficha de ocho campos, acta con informe literal verificable por hash— y cerrar el cambio con dos guards que impidan la regresión.

**Architecture:** migración documental en verticales por clase (`diseño` → `rama` → `autorrevision`), con los guards G7/G8 creciendo desde el primer PR sobre una **población migrada explícita** que se amplía en cada tarea y se retira en la última. Nada de código de producción: solo `docs/` y `tests/test_docs_gobernanza.py`.

**Tech Stack:** Python 3, `pytest`, `re`, `hashlib`. Windows + PowerShell. UTF-8 sin BOM.

## Global Constraints

- **Fuente única del diseño:** `docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md` **rev. 5** (commit `5558dfd`). No reabrir sus decisiones cerradas. Las tres adjudicaciones (§14, §15, §16) y las tres actas son el ejemplo de referencia: ante duda de formato, copiar de ahí.
- **La rev. 5 añade cinco mejoras (§13.1) que este plan ya incorpora:** el `mandato` obligatorio en el frontmatter del acta (M-2, Tareas 4 y 5), el alcance real de G8 (M-4, sin efecto en el código) y la regla de parada de rondas (M-5, doctrina, Tarea 9). **M-1 y M-3 cambian decisiones y su cobertura es ausente y declarada:** si la cuarta ronda acotada las modifica, este plan se ajusta antes de ejecutar las Tareas 7 y 9.
- **Vocabularios cerrados** (spec §4), literales: `clase` ∈ `diseño` · `rama` · `autorrevision`; `veredicto` ∈ `SHIP` · `LISTA-CON-CAMBIOS` · `REQUIERE-REVISION` · `NO-SHIP` · `NO-EJECUTABLE` · `SIN-VEREDICTO`; `estado_remediacion` ∈ `remediado` · `parcial` · `sin-cambios` · `pendiente`; `cobertura` ∈ `ejecutada` · `no-ejecutada`.
- **Tercera población de vocabularios.** NO tocar `_ESTADOS_DOCS` ni `_ESTADOS_HANDOFF`, NO volver recursivo el glob de `_docs_con_frontmatter`. Es la trampa D3 que documenta la cabecera de `tests/test_docs_gobernanza.py`: unificar los sets rompe 11 ficheros al instante.
- **No se inventa lo que no consta.** Si un campo no está en la fuente, el valor es `no registrado`. Prohibido reconstruir un commit, un recuento o un veredicto «a ojo».
- **Encoding:** UTF-8 sin BOM. En PowerShell usar `[System.IO.File]::ReadAllText/WriteAllText` con `UTF8Encoding($false)`. Nunca `Add-Content`/`Get-Content -Raw` sin `-Encoding UTF8`.
- **`main` está protegida:** todo va por rama + PR. Un PR por tarea salvo donde el plan diga lo contrario.
- **Suite base:** 2696 tests, 0 fallos, 84 skip (medido en `f32e19c`). Cualquier número distinto se explica antes de seguir.
- **Comando de suite:** `python -m pytest -q --tb=no`. Para el fichero de guards: `python -m pytest tests/test_docs_gobernanza.py -q`.

---

## Censo de la población postcorte

Una fila por identidad `(objeto, rev./commit, ronda, revisor, fecha)`, spec §1.3. **28 revisiones** desde el corte del 2026-07-23. Es el inventario que el spec §1.5 delega en este plan, y la base del criterio 6.

| # | Objeto | Clase | Ronda | Revisor | Dónde consta hoy | Tarea |
|---|---|---|---|---|---|---|
| 1 | emails atomizados sala lectura (spec) | diseño | 1 | Codex | acta `2026-07-23-…-adversarial-review.md:3` | 4, 6 |
| 2 | emails atomizados sala lectura (spec) | diseño | 2 | Claude | misma acta, `:9-16` («segunda revisión, independiente») | 4, 6 |
| 3 | `handoff-2026-07-26-gobernanza-indice-adversarial.md` | diseño | 1 | Claude Code (orquestador + 5 subagentes) | acta `2026-07-26-…-adversarial-review.md`; cerrada en `PLAN.md:2128` | 4, 6 |
| 4 | cableado atomize (spec) | diseño | 1 | Codex | acta `2026-07-27-…-adversarial-review.md:3-6` | 4, 6 |
| 5 | cableado atomize (spec) | autorrevision | 1 | Claude (autor) | misma acta, `:3-6` («pasada propia de Claude») | 8 |
| 6 | cableado atomize (plan) | diseño | 1 | Codex | `plans/2026-07-28-cableado-atomize-sala-maquina.md:1220` | 3 |
| 7 | cableado atomize (rama, PR #151) | rama | 1 | Opus | `docs/bitacora/2026.md:138` («revisión de rama»); NO-SHIP con un Critical destructivo | 7 |
| 8 | vista procesal (spec v3) | diseño | 1 | Codex | 2 handoffs + §10 del spec | 3, 6 |
| 9 | vista procesal (spec v3.1) | diseño | 2 | Codex | `handoff-…-codex-review-2.md`; adjudicada en PR #137 | 6 |
| 10 | dual case workspace (spec rev. 1) | diseño | 1 | Claude | acta `2026-07-29-…-adversarial-review.md` + §20 del spec | 4 |
| 11 | dual workspace Fase 0 (plan rev. 1) | diseño | 1 | Codex | `PLAN.md`, primer bloque `GATE CONSUMIDO`; produjo la rev. 2 y el PR #156 | 6 |
| 12 | dual workspace Fase 0 (plan rev. 2) | diseño | 2 | Codex | `PLAN.md:587-593`: NO EJECUTABLE, 3 B0 + 4 A + 1 M, nada refutado; produjo rev. 3 y PR #160 | 6 |
| 13 | dual workspace Fase 0 (plan rev. 3) | diseño | 3 | Codex | `PLAN.md:595-597`: REQUIERE REVISIÓN, 3 B0 + 2 A, 5 confirmados / 1 refutado / 1 sin verificar; PR #166 | 6 |
| 14 | email atomize enumeración (spec) | diseño | 1 | Codex | §11 del spec: `NO-SHIP, resuelto` | 2 |
| 15 | email atomize enumeración (plan) | diseño | 1 | Codex | `docs/bitacora/2026.md:134` | 6 |
| 16 | email atomize enumeración (rama, PR #155) | rama | 1 | Codex | `PLAN.md:383-386` («la revisión final de rama», que añadió el Gate 2) | 7 |
| 17 | sandwich firma (spec) | diseño | 1 | Codex | §9 del spec: `NO-SHIP, remediado` — **único que ya casa** | 2 |
| 18 | sandwich firma (plan) | diseño | 1 | Codex | `plans/2026-07-29-sandwich-firma-falso-positivo.md:1061` | 3 |
| 19 | sandwich firma (rama) | rama | 1 | no registrado | mismo plan, `:1089` | 3 |
| 20 | historial citado (plan) | diseño | 1 | Codex | `docs/bitacora/2026.md:70`: NO EJECUTABLE | 6 |
| 21 | historial citado (rama construida) | rama | 1 | Codex | `docs/bitacora/2026.md:70`: otro NO EJECUTABLE, 2 defectos vivos; adjudicación en `specs/2026-07-30-historial-citado-localizable-design.md:238` | 3, 7 |
| 22 | bundle por hilo (diseño) | diseño | 1 | no registrado | `docs/bitacora/2026.md:150` («dos revisiones adversariales») | 6 |
| 23 | bundle por hilo (diseño) | diseño | 2 | no registrado | ídem | 6 |
| 24 | bundle por hilo (rama, PR #131/#132) | rama | 1 | no registrado | `docs/bitacora/2026.md:150` + `PLAN.md:757-761`: tres caminos de pérdida/sobrescritura | 7 |
| 25 | OCR ciego bajo el sello (diff, PR #147) | autorrevision | 1 | Claude (autor) | `docs/bitacora/2026.md:144` | 8 |
| 26 | este spec (rev. 1) | diseño | 1 | Codex | §14 + acta r1 — **ya conforme** | 5 |
| 27 | este spec (rev. 2) | diseño | 2 | Codex | §15 + acta r2 — **ya conforme** | 5 |
| 28 | este spec (rev. 3) | diseño | 3 | Codex | §16 + acta r3 — **ya conforme** | 5 |

**Cobertura agregada, no filas propias** (spec §1.2): las **7 revisiones por tarea** del build de cableado (`docs/bitacora/2026.md:138`) se declaran en la `Cobertura` de la fila 7.

**Fuera de la población, declarado:** todo lo anterior al 2026-07-23 (`PLAN.md:924-928`, `:933`, `:953`, `:1033-1044`), el `code-review` de rutina, `pase-de-estilo`, los tests y el brainstorming.

---

## File Structure

| Fichero | Responsabilidad | Tarea |
|---|---|---|
| `tests/test_docs_gobernanza.py` | **Modificar** (append). G7 + G8 como tercera población, con su cabecera de aviso anti-D3 y `_POBLACION_MIGRADA` | 1, 2-8 (ampliar), 10 (retirar) |
| `docs/superpowers/specs/2026-07-29-sandwich-firma-falso-positivo-design.md:287` | Modificar: añadir ficha al §9 | 2 |
| `docs/superpowers/specs/2026-07-28-email-atomize-enumeracion-recursiva-design.md:455` | Modificar: token + ficha en §11 | 2 |
| `docs/superpowers/specs/2026-07-30-historial-citado-localizable-design.md:238` | Modificar: token + ficha en §10-bis | 3 |
| `docs/superpowers/plans/2026-07-29-sandwich-firma-falso-positivo.md:1061,1089` | Modificar: dos encabezados + fichas | 3 |
| `docs/superpowers/plans/2026-07-28-cableado-atomize-sala-maquina.md:1220` | Modificar: encabezado + ficha | 3 |
| `docs/superpowers/specs/2026-07-27-vista-procesal-05-procedimiento-design.md:671` | Modificar: encabezado completo + ficha en §10 | 3 |
| `docs/superpowers/specs/2026-07-29-feesdefender-dual-case-workspace-design.md:1225` | Modificar: encabezado completo + ficha en §20 | 3 |
| Las 4 actas heredadas | Modificar: frontmatter + `formato: hibrido-legacy` + `no-disponible-legacy` | 4 |
| Las 3 actas de este spec | Modificar: marcadores `informe-literal`; **Renombrar** al esquema del §6 | 5 |
| `docs/superpowers/specs/2026-07-23-…-design.md`, `…cableado…-design.md`, `handoff-2026-07-26-…` | Modificar: encabezado + ficha + puntero al acta (hoy no tienen ninguno) | 6 |
| `docs/superpowers/plans/2026-07-29-dual-workspace-fase0-fase1.md` | Modificar: tres encabezados + fichas (rondas 1-3) | 6 |
| `docs/superpowers/plans/2026-07-26-sala-lectura-bundle-por-hilo.md` | Modificar: encabezados de diseño r1/r2 y de rama | 6, 7 |
| `docs/superpowers/plans/2026-07-28-cableado-atomize-sala-maquina.md` | Modificar: encabezado de rama + cobertura por tarea | 7 |
| `docs/superpowers/plans/2026-07-29-email-atomize-enumeracion-recursiva.md` | Modificar: encabezados de plan y rama | 6, 7 |
| `CLAUDE.md`, `AGENTS.md`, `docs/GOBERNANZA_FUENTES_VERDAD.md` | Modificar: doctrina (spec §10 y §10.1) | 9 |

**Desviación declarada respecto del spec §9.1.** El spec dice «los guards se activan en el ÚLTIMO PR» para evitar que estén en rojo durante la migración. Este plan lo consigue mejor: G7/G8 nacen en la Tarea 1 con una **población migrada explícita** (`_POBLACION_MIGRADA`), que cada tarea amplía. Los guards están verdes en cada commit, cubren lo ya migrado desde el primer día, y la Tarea 10 retira la lista para que cubran todo. Mismo objetivo —nunca rojo, sin PR gigante— con cobertura incremental en vez de nula.

---

### Task 1: G7 — adjudicación bien formada, sobre población migrada explícita

**Files:**
- Modify: `tests/test_docs_gobernanza.py` (append al final)
- Test: el propio fichero

**Interfaces:**
- Consumes: `ROOT` (ya definido en la línea 7 del fichero), `re`, `Path`.
- Produces: `_CLASES`, `_VEREDICTOS_REV`, `_ESTADOS_REM`, `_DISPARADOR_ADJ`, `_RE_ADJUDICACION`, `_CAMPOS_FICHA`, `_POBLACION_MIGRADA`, `_sin_cercas(txt) -> list[str]`, `_adjudicaciones(txt) -> list[tuple[int, str]]`. Las tareas 2-8 solo añaden nombres de fichero a `_POBLACION_MIGRADA`.

- [ ] **Step 1: Escribir el test que falla**

Añadir al final de `tests/test_docs_gobernanza.py`:

```python
# ===========================================================================
# G7-G8 — poblacion de REVISIONES ADVERSARIALES.
#
# ⚠️ TERCERA POBLACION de vocabularios (spec 2026-08-01-gobernanza-revisiones-
# adversariales-design.md §4). NO comparte set con _ESTADOS_DOCS (docs de raiz)
# ni con _ESTADOS_HANDOFF (handoffs). El campo se llama `estado_remediacion` y
# NO `estado` precisamente para que la colision sea imposible por construccion.
# Misma disciplina que G4-G6: poblaciones separadas, nunca unificar los sets.
#
# _POBLACION_MIGRADA es ANDAMIO de la migracion: crece en cada tarea del plan
# 2026-08-01-migracion-revisiones-adversariales.md y la Tarea 10 la RETIRA para
# que los guards cubran todo `docs/superpowers/`.
# ===========================================================================

_SP = ROOT / "docs" / "superpowers"

_CLASES = {"diseño", "rama", "autorrevision"}
_VEREDICTOS_REV = {"SHIP", "LISTA-CON-CAMBIOS", "REQUIERE-REVISION",
                   "NO-SHIP", "NO-EJECUTABLE", "SIN-VEREDICTO"}
_ESTADOS_REM = {"remediado", "parcial", "sin-cambios", "pendiente"}
_COBERTURAS = {"ejecutada", "no-ejecutada"}

_DISPARADOR_ADJ = "Adjudicación de la revisión"

_RE_ADJUDICACION = re.compile(
    r"^#{2,3}\s+(?:\S+\s+)?"                    # ## o ###, numeracion opcional (10., 10-bis.)
    r"Adjudicación de la revisión adversarial"
    r"[^(\n]*"                                 # calificador: "del PLAN", "de rama completa"
    r"\((?P<revisor>[^,)]+),\s*(?P<fecha>\d{4}-\d{2}-\d{2})\)"
    r"\s*—\s*(?P<veredicto>[A-Z-]+),\s*(?P<estado>[a-z-]+)\s*$")

_CAMPOS_FICHA = ("Clase", "Objeto revisado", "Ronda", "Revisor", "Cobertura",
                 "Informe recibido", "Hallazgos", "Remediado en")

_RE_CAMPO = re.compile(r"^- \*\*(?P<campo>[^:*]+):\*\*\s*(?P<valor>.+)$")

# Crece por tarea. Tarea 10 la retira.
_POBLACION_MIGRADA = {
    "2026-08-01-gobernanza-revisiones-adversariales-design.md",
}


def _sin_cercas(txt: str) -> list[str]:
    """Lineas del texto con el contenido de los bloques ``` vaciado.

    Imprescindible: la PLANTILLA del §5 del spec vive dentro de una cerca y
    empieza por `## … Adjudicación de la revisión…`. Sin este filtro el guard
    se autodetecta — defecto observado, no deducido (ronda 1, H-03).
    """
    fuera, dentro = [], False
    for ln in txt.splitlines():
        if ln.lstrip().startswith("```"):
            dentro = not dentro
            fuera.append("")
            continue
        fuera.append("" if dentro else ln)
    return fuera


def _adjudicaciones(txt: str) -> list[tuple[int, str]]:
    """(indice de linea, linea) de cada encabezado disparador fuera de cerca."""
    return [(i, ln) for i, ln in enumerate(_sin_cercas(txt))
            if ln.startswith("#") and _DISPARADOR_ADJ in ln]


def _ficha(lineas: list[str], desde: int) -> dict[str, str]:
    """Campos `- **Campo:** valor` contiguos tras el encabezado (salta blancos)."""
    campos, i = {}, desde + 1
    while i < len(lineas) and not lineas[i].strip():
        i += 1
    while i < len(lineas):
        m = _RE_CAMPO.match(lineas[i])
        if not m:
            break
        campos[m.group("campo").strip()] = m.group("valor").strip()
        i += 1
    return campos


def _es_acta(txt: str) -> bool:
    return txt.startswith("---") and "tipo: revision-adversarial" in txt[:600]


def _md_superpowers():
    for p in sorted(_SP.rglob("*.md")):
        yield p, p.read_text(encoding="utf-8")


def test_adjudicaciones_bien_formadas():
    """G7 — encabezado canonico + ficha de 8 campos con vocabulario valido.

    Alcance: `_POBLACION_MIGRADA` mientras dure la migracion. Las actas
    (`tipo: revision-adversarial`) quedan fuera: su informe literal puede
    contener cualquier encabezado y no debe reinterpretarse como adjudicacion.
    """
    malos: dict[str, list[str]] = {}
    for p, txt in _md_superpowers():
        if p.name not in _POBLACION_MIGRADA or _es_acta(txt):
            continue
        lineas = _sin_cercas(txt)
        for i, ln in _adjudicaciones(txt):
            fallos = []
            m = _RE_ADJUDICACION.match(ln)
            if not m:
                fallos.append(f"encabezado fuera de formato: {ln[:90]!r}")
            else:
                if m.group("veredicto") not in _VEREDICTOS_REV:
                    fallos.append(f"veredicto {m.group('veredicto')!r} fuera del set")
                if m.group("estado") not in _ESTADOS_REM:
                    fallos.append(f"estado_remediacion {m.group('estado')!r} fuera del set")
            fi = _ficha(lineas, i)
            faltan = [c for c in _CAMPOS_FICHA if c not in fi]
            if faltan:
                fallos.append(f"ficha incompleta, faltan {faltan}")
            else:
                if fi["Clase"] not in _CLASES:
                    fallos.append(f"Clase {fi['Clase']!r} fuera del set")
                if fi["Cobertura"].split("(")[0].split("—")[0].strip() not in _COBERTURAS:
                    fallos.append(f"Cobertura {fi['Cobertura']!r} fuera del set")
            if fallos:
                malos.setdefault(f"{p.name}:{i + 1}", []).extend(fallos)
    assert not malos, (
        f"adjudicaciones que incumplen el spec §5: {malos}\n\n"
        f"Forma esperada (ojo a la raya larga `—`, NO un guion, y a las tildes):\n"
        f"  ## N. Adjudicación de la revisión adversarial (Revisor, AAAA-MM-DD) — VEREDICTO, estado\n"
        f"  veredicto ∈ {sorted(_VEREDICTOS_REV)}\n"
        f"  estado    ∈ {sorted(_ESTADOS_REM)}\n"
        f"  ficha     = {list(_CAMPOS_FICHA)}")


def test_g7_no_se_autodetecta_en_la_plantilla_del_spec():
    """G7-bis — la plantilla cercada del §5 NO cuenta como adjudicacion.

    Test de regresion del defecto de la ronda 1: un grep de encabezados sobre
    `docs/superpowers/` devolvia la linea 118 del propio spec.
    """
    spec = _SP / "specs" / "2026-08-01-gobernanza-revisiones-adversariales-design.md"
    txt = spec.read_text(encoding="utf-8")
    crudos = [ln for ln in txt.splitlines()
              if ln.startswith("#") and _DISPARADOR_ADJ in ln]
    fuera = [ln for _, ln in _adjudicaciones(txt)]
    assert len(crudos) > len(fuera), (
        "el spec deberia tener al menos una plantilla cercada que el filtro descarte")
    assert all(_RE_ADJUDICACION.match(ln) for ln in fuera), (
        f"tras filtrar cercas deben quedar solo adjudicaciones reales: {fuera}")
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `python -m pytest tests/test_docs_gobernanza.py -q`
Expected: **FAIL**. `test_adjudicaciones_bien_formadas` no falla (el spec ya es conforme), pero `test_g7_no_se_autodetecta_en_la_plantilla_del_spec` puede fallar si `_sin_cercas` tiene un error de paridad. Si ambos pasan a la primera, **rómpelos a propósito** para comprobar que el arnés funciona: cambia temporalmente `_ESTADOS_REM` a `{"remediado"}` y confirma que el primero falla con los tres §14-§16; deshaz el cambio.

- [ ] **Step 3: Añadir fixtures negativas**

Añadir a continuación:

```python
_ADJ_OK = """## 3. Adjudicación de la revisión adversarial (Codex, 2026-08-01) — NO-SHIP, remediado

- **Clase:** diseño
- **Objeto revisado:** `docs/x.md` rev. 1, commit `abc1234`
- **Ronda:** 1
- **Revisor:** Codex (solo lectura)
- **Cobertura:** ejecutada
- **Informe recibido:** `x-adversarial-review.md`
- **Hallazgos:** 1 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** PR #1 (`abc1234`)
"""


def _valida(txt: str) -> list[str]:
    """Errores que G7 detectaria en `txt`. Vacio = conforme."""
    lineas, fallos = _sin_cercas(txt), []
    for i, ln in _adjudicaciones(txt):
        m = _RE_ADJUDICACION.match(ln)
        if not m:
            fallos.append("encabezado")
            continue
        if m.group("veredicto") not in _VEREDICTOS_REV:
            fallos.append("veredicto")
        if m.group("estado") not in _ESTADOS_REM:
            fallos.append("estado")
        fi = _ficha(lineas, i)
        if [c for c in _CAMPOS_FICHA if c not in fi]:
            fallos.append("ficha")
        elif fi["Clase"] not in _CLASES:
            fallos.append("clase")
    return fallos


def test_g7_acepta_la_forma_canonica():
    assert _valida(_ADJ_OK) == []


def test_g7_rechaza_estado_fuera_del_set():
    # `resuelto` es el token real de email-enumeracion §11 antes del retrofit.
    assert "estado" in _valida(_ADJ_OK.replace("NO-SHIP, remediado", "NO-SHIP, resuelto"))


def test_g7_rechaza_veredicto_con_espacios():
    # `NO EJECUTABLE` es el token real de historial §10-bis y sandwich plan.
    assert "encabezado" in _valida(
        _ADJ_OK.replace("NO-SHIP, remediado", "NO EJECUTABLE, remediado"))


def test_g7_rechaza_ficha_incompleta():
    assert "ficha" in _valida(_ADJ_OK.replace("- **Ronda:** 1\n", ""))


def test_g7_rechaza_encabezado_sin_revisor_ni_fecha():
    # Forma real de vista procesal §10 y dual §20.
    roto = _ADJ_OK.replace(
        "## 3. Adjudicación de la revisión adversarial (Codex, 2026-08-01) — NO-SHIP, remediado",
        "## 10. Adjudicación de la revisión adversarial")
    assert "encabezado" in _valida(roto)


def test_g7_admite_numeracion_bis_y_calificador():
    for enc in ("## 10-bis. Adjudicación de la revisión adversarial (Codex, 2026-08-01) — NO-SHIP, remediado",
                "## Adjudicación de la revisión adversarial del PLAN (Codex, 2026-08-01) — NO-SHIP, remediado",
                "## Adjudicación de la revisión adversarial de rama completa (Opus, 2026-08-01) — LISTA-CON-CAMBIOS, remediado"):
        txt = _ADJ_OK.replace(_ADJ_OK.splitlines()[0], enc)
        assert _valida(txt) == [], f"deberia aceptar: {enc}"


def test_g7_ignora_lo_que_esta_en_cerca():
    cercado = "```\n" + _ADJ_OK + "```\n"
    assert _adjudicaciones(cercado) == []
```

- [ ] **Step 4: Correr y verificar que pasan**

Run: `python -m pytest tests/test_docs_gobernanza.py -q`
Expected: **PASS**, 16 tests (8 previos + G7 + G7-bis + 6 fixtures).

- [ ] **Step 5: Suite completa**

Run: `python -m pytest -q --tb=no`
Expected: 2696 passed → **2704 passed**, 0 failed, 84 skipped.

- [ ] **Step 6: Commit**

```bash
git add tests/test_docs_gobernanza.py && git commit -m "test(gobernanza): G7 — adjudicaciones bien formadas, sobre poblacion migrada"
```

---

### Task 2: retrofit barato — los dos encabezados que ya casi casan

**Files:**
- Modify: `docs/superpowers/specs/2026-07-29-sandwich-firma-falso-positivo-design.md:287`
- Modify: `docs/superpowers/specs/2026-07-28-email-atomize-enumeracion-recursiva-design.md:455`
- Modify: `tests/test_docs_gobernanza.py` (`_POBLACION_MIGRADA`)

**Interfaces:**
- Consumes: `_POBLACION_MIGRADA` de la Tarea 1.
- Produces: nada nuevo; solo amplía el conjunto.

- [ ] **Step 1: Ampliar la población y ver el guard en rojo**

En `_POBLACION_MIGRADA` añadir:

```python
    "2026-07-29-sandwich-firma-falso-positivo-design.md",
    "2026-07-28-email-atomize-enumeracion-recursiva-design.md",
```

Run: `python -m pytest tests/test_docs_gobernanza.py::test_adjudicaciones_bien_formadas -q`
Expected: **FAIL**, con `ficha incompleta` en sandwich y `estado 'resuelto' fuera del set` + `ficha incompleta` en enumeración.

- [ ] **Step 2: Añadir la ficha a sandwich §9**

El encabezado de `…sandwich-firma-falso-positivo-design.md:287` **ya casa** y no se toca:
`## 9. Adjudicación de la revisión adversarial (Codex, 2026-07-29) — NO-SHIP, remediado`

Insertar inmediatamente debajo, seguido de una línea en blanco:

```markdown
- **Clase:** diseño
- **Objeto revisado:** `docs/superpowers/specs/2026-07-29-sandwich-firma-falso-positivo-design.md` rev. 1, commit `no registrado`
- **Ronda:** 1
- **Revisor:** Codex (solo lectura)
- **Cobertura:** ejecutada
- **Informe recibido:** no archivado (anterior a esta regla)
- **Hallazgos:** no registrado
- **Remediado en:** rev. 2 de este documento
```

**`Hallazgos: no registrado`** porque el §9 no publica recuento por categoría. No inventarlo.

- [ ] **Step 3: Corregir el token y añadir la ficha a enumeración §11**

Cambiar el encabezado de la línea 455:

```
-## 11. Adjudicación de la revisión adversarial (Codex, 2026-07-29) — NO-SHIP, resuelto
+## 11. Adjudicación de la revisión adversarial (Codex, 2026-07-29) — NO-SHIP, remediado
```

E insertar debajo:

```markdown
- **Clase:** diseño
- **Objeto revisado:** `docs/superpowers/specs/2026-07-28-email-atomize-enumeracion-recursiva-design.md` rev. 1, commit `no registrado`
- **Ronda:** 1
- **Revisor:** Codex (solo lectura)
- **Cobertura:** ejecutada
- **Informe recibido:** no archivado (anterior a esta regla)
- **Hallazgos:** no registrado
- **Remediado en:** PR #155
```

- [ ] **Step 4: Verificar verde**

Run: `python -m pytest tests/test_docs_gobernanza.py -q`
Expected: **PASS**, 16 tests.

- [ ] **Step 5: Suite y commit**

Run: `python -m pytest -q --tb=no` → 2704 passed.

```bash
git add docs/superpowers/specs/2026-07-29-sandwich-firma-falso-positivo-design.md docs/superpowers/specs/2026-07-28-email-atomize-enumeracion-recursiva-design.md tests/test_docs_gobernanza.py && git commit -m "docs(gobernanza): retrofit de las dos adjudicaciones mas cercanas al formato"
```

---

### Task 3: retrofit estructural — los seis encabezados restantes

**Files:**
- Modify: `docs/superpowers/specs/2026-07-30-historial-citado-localizable-design.md:238`
- Modify: `docs/superpowers/plans/2026-07-29-sandwich-firma-falso-positivo.md:1061` y `:1089`
- Modify: `docs/superpowers/plans/2026-07-28-cableado-atomize-sala-maquina.md:1220`
- Modify: `docs/superpowers/specs/2026-07-27-vista-procesal-05-procedimiento-design.md:671`
- Modify: `docs/superpowers/specs/2026-07-29-feesdefender-dual-case-workspace-design.md:1225`
- Modify: `tests/test_docs_gobernanza.py`

**Interfaces:** consume `_POBLACION_MIGRADA`; no produce nombres nuevos.

- [ ] **Step 1: Ampliar la población y ver el rojo**

Añadir a `_POBLACION_MIGRADA`:

```python
    "2026-07-30-historial-citado-localizable-design.md",
    "2026-07-29-sandwich-firma-falso-positivo.md",
    "2026-07-28-cableado-atomize-sala-maquina.md",
    "2026-07-27-vista-procesal-05-procedimiento-design.md",
    "2026-07-29-feesdefender-dual-case-workspace-design.md",
```

Run: `python -m pytest tests/test_docs_gobernanza.py::test_adjudicaciones_bien_formadas -q`
Expected: **FAIL** con seis entradas.

- [ ] **Step 2: historial §10-bis — normalizar token**

```
-## 10-bis. Adjudicación de la revisión adversarial (Codex, 2026-07-30) — NO EJECUTABLE, remediado
+## 10-bis. Adjudicación de la revisión adversarial (Codex, 2026-07-30) — NO-EJECUTABLE, remediado
```

Ficha debajo (fila 21 del censo; es la revisión de la **rama construida**, según `docs/bitacora/2026.md:70`):

```markdown
- **Clase:** rama
- **Objeto revisado:** rama de `MEJORAS #109`, commit `no registrado`
- **Ronda:** 1
- **Revisor:** Codex (solo lectura)
- **Cobertura:** ejecutada
- **Informe recibido:** no archivado (anterior a esta regla)
- **Hallazgos:** 2 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** PR #175 (`31b5943`)
```

Los **2 confirmados** son los dos defectos vivos que la bitácora enumera: pérdida de datos en fallo transitorio, y líneas de cabecera pegadas a la primera frase citada.

- [ ] **Step 3: sandwich plan — dos encabezados**

Línea 1061:

```
-## Adjudicación de la revisión adversarial (Codex, 2026-07-29) — NO EJECUTABLE, remediado
+## Adjudicación de la revisión adversarial del PLAN (Codex, 2026-07-29) — NO-EJECUTABLE, remediado
```

```markdown
- **Clase:** diseño
- **Objeto revisado:** `docs/superpowers/plans/2026-07-29-sandwich-firma-falso-positivo.md` rev. 1, commit `no registrado`
- **Ronda:** 1
- **Revisor:** Codex (solo lectura)
- **Cobertura:** ejecutada
- **Informe recibido:** no archivado (anterior a esta regla)
- **Hallazgos:** no registrado
- **Remediado en:** rev. 2 de este documento
```

Línea 1089:

```
-## Adjudicación de la revisión de rama completa (2026-07-29) — LISTA CON CAMBIOS, aplicados
+## Adjudicación de la revisión adversarial de rama completa (no registrado, 2026-07-29) — LISTA-CON-CAMBIOS, remediado
```

`(no registrado, 2026-07-29)` porque el documento no nombra al revisor y el censo (fila 19) lo deja así. El regex exige `(revisor, fecha)`, y `no registrado` es un valor legítimo del Global Constraint.

```markdown
- **Clase:** rama
- **Objeto revisado:** rama de `2026-07-29-sandwich-firma-falso-positivo`, commit `no registrado`
- **Ronda:** 1
- **Revisor:** no registrado
- **Cobertura:** ejecutada
- **Informe recibido:** no archivado (anterior a esta regla)
- **Hallazgos:** no registrado
- **Remediado en:** cambios aplicados en la propia rama
```

- [ ] **Step 4: cableado plan §Adjudicación**

```
-## Adjudicación de la revisión adversarial del PLAN (Codex, 2026-07-28) — veredicto NO-SHIP, remediado
+## Adjudicación de la revisión adversarial del PLAN (Codex, 2026-07-28) — NO-SHIP, remediado
```

Se retira la palabra `veredicto`, que rompe el grupo del regex.

```markdown
- **Clase:** diseño
- **Objeto revisado:** `docs/superpowers/plans/2026-07-28-cableado-atomize-sala-maquina.md` rev. 1, commit `no registrado`
- **Ronda:** 1
- **Revisor:** Codex (solo lectura)
- **Cobertura:** ejecutada
- **Informe recibido:** no archivado (anterior a esta regla)
- **Hallazgos:** no registrado
- **Remediado en:** rev. 2 de este documento
```

- [ ] **Step 5: vista procesal §10 — encabezado sin datos**

Hoy es `## 10. Adjudicación de la revisión adversarial`, sin revisor, fecha, veredicto ni estado. Los cuatro se toman de sus handoffs, que **sí** los declaran: `handoff-2026-07-27-vista-procesal-codex-review.md` tiene `revisor: Codex` y `veredicto: NO SHIP`.

```
-## 10. Adjudicación de la revisión adversarial
+## 10. Adjudicación de la revisión adversarial (Codex, 2026-07-27) — NO-SHIP, remediado
```

```markdown
- **Clase:** diseño
- **Objeto revisado:** `docs/superpowers/specs/2026-07-27-vista-procesal-05-procedimiento-design.md` v3, commit `no registrado`
- **Ronda:** 1
- **Revisor:** Codex (solo lectura)
- **Cobertura:** ejecutada
- **Informe recibido:** `handoff-2026-07-27-vista-procesal-codex-informe.md` (excepción histórica, gobernanza §5)
- **Hallazgos:** 25 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** PR #137 (`12c8a91`)
```

Los **25** salen de la fila del `INDICE.md §Handoffs` para `…-codex-informe.md` («NO SHIP, 25 hallazgos»). **Verifícalo abriendo el INDICE antes de escribirlo**; si no cuadra, `no registrado`.

- [ ] **Step 6: dual workspace §20**

Hoy es `## 20. Adjudicación de la revisión adversarial (rev. 2)`. Los datos están en su acta: revisor Claude Code, veredicto `REQUIERE REVISIÓN`, y `docs/bitacora/2026.md:136` da el recuento **4 B0 + 10 A + 5 M**.

```
-## 20. Adjudicación de la revisión adversarial (rev. 2)
+## 20. Adjudicación de la revisión adversarial (Claude, 2026-07-29) — REQUIERE-REVISION, remediado
```

```markdown
- **Clase:** diseño
- **Objeto revisado:** `docs/superpowers/specs/2026-07-29-feesdefender-dual-case-workspace-design.md` rev. 1, commit `8d9c96c`
- **Ronda:** 1
- **Revisor:** Claude (no independiente: el spec lo escribió Codex en `codex/feesdefender-dual-spec`)
- **Cobertura:** ejecutada
- **Informe recibido:** `2026-07-29-feesdefender-dual-case-workspace-adversarial-review.md`
- **Hallazgos:** 19 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** rev. 2 de este documento
```

**19 = 4 B0 + 10 A + 5 M**, todos aceptados según el acta («todos los B0 y los A aceptados… Los M van a `MEJORAS #101-#103`»). El `Revisor: Claude` **no** es autorrevisión: el objeto lo escribió Codex, así que la clase es `diseño`, no `autorrevision`.

- [ ] **Step 7: Verificar verde y commit**

Run: `python -m pytest tests/test_docs_gobernanza.py -q` → **PASS**.
Run: `python -m pytest -q --tb=no` → 2704 passed.

```bash
git add docs/superpowers tests/test_docs_gobernanza.py && git commit -m "docs(gobernanza): retrofit estructural de los seis encabezados restantes"
```

---

### Task 4: las cuatro actas heredadas + G8

**Files:**
- Modify: las 4 actas (`2026-07-23-emails-atomizados-sala-lectura-`, `2026-07-26-gobernanza-indice-`, `2026-07-27-cableado-atomize-sala-maquina-`, `2026-07-29-feesdefender-dual-case-workspace-` + `adversarial-review.md`)
- Modify: `tests/test_docs_gobernanza.py`

**Interfaces:**
- Consumes: `_es_acta`, `_md_superpowers` de la Tarea 1.
- Produces: `_ALLOWLIST_HIBRIDA`, `_CLAVES_ACTA`, `test_actas_bien_formadas`.

- [ ] **Step 1: Escribir G8, base (frontmatter + puntero + allowlist)**

```python
# Allowlist CERRADA de actas hibridas heredadas: nacieron con informe y
# adjudicacion en el mismo fichero (spec §6). Sin esta lista, la exencion se
# aplicaria a toda acta futura y crearia una clase permanente fuera de guard
# (ronda 3, H-03). NO ampliar sin tocar el spec.
_ALLOWLIST_HIBRIDA = frozenset({
    "2026-07-23-emails-atomizados-sala-lectura-adversarial-review.md",
    "2026-07-26-gobernanza-indice-adversarial-review.md",
    "2026-07-27-cableado-atomize-sala-maquina-adversarial-review.md",
    "2026-07-29-feesdefender-dual-case-workspace-adversarial-review.md",
})

_CLAVES_ACTA = ("tipo", "objeto", "objeto_rev", "commit", "ronda", "clase",
                "revisor", "cobertura", "veredicto", "mandato", "sha256_informe",
                "adjudicado_en")
_RE_SECCION = re.compile(r"§(\d+[\w-]*)")


def _fm(txt: str) -> dict[str, str]:
    fm = txt.split("---")[1] if txt.startswith("---") else ""
    return dict(re.findall(r"^([a-z0-9_]+):\s*(.+)$", fm, re.MULTILINE))


def test_actas_bien_formadas():
    """G8 — frontmatter del spec §6 + `adjudicado_en` a fichero Y seccion reales."""
    malos: dict[str, list[str]] = {}
    for p, txt in _md_superpowers():
        if not _es_acta(txt):
            continue
        fm, fallos = _fm(txt), []
        fallos += [f"falta {k}" for k in _CLAVES_ACTA if not fm.get(k)]
        if fm.get("clase") and fm["clase"] not in _CLASES:
            fallos.append(f"clase {fm['clase']!r} fuera del set")
        if fm.get("veredicto") and fm["veredicto"] not in _VEREDICTOS_REV:
            fallos.append(f"veredicto {fm['veredicto']!r} fuera del set")
        if fm.get("cobertura") and fm["cobertura"] not in _COBERTURAS:
            fallos.append(f"cobertura {fm['cobertura']!r} fuera del set")
        hibrida = p.name in _ALLOWLIST_HIBRIDA
        if hibrida and fm.get("formato") != "hibrido-legacy":
            fallos.append("acta de la allowlist sin `formato: hibrido-legacy`")
        if not hibrida and fm.get("formato") == "hibrido-legacy":
            fallos.append("`formato: hibrido-legacy` fuera de la allowlist cerrada")
        destino = fm.get("adjudicado_en", "")
        ruta = destino.split("§")[0].strip()
        if ruta:
            f = ROOT / ruta
            if not f.exists():
                fallos.append(f"adjudicado_en apunta a un fichero inexistente: {ruta}")
            else:
                m = _RE_SECCION.search(destino)
                if not m:
                    fallos.append("adjudicado_en sin §seccion")
                elif not re.search(rf"^#{{1,3}}\s+{re.escape(m.group(1))}\.\s",
                                   f.read_text(encoding="utf-8"), re.MULTILINE):
                    fallos.append(f"adjudicado_en apunta a §{m.group(1)}, que no existe en {ruta}")
        if fallos:
            malos[p.name] = fallos
    assert not malos, f"actas que incumplen el spec §6: {malos}"
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `python -m pytest tests/test_docs_gobernanza.py::test_actas_bien_formadas -q`
Expected: **FAIL** con las cuatro heredadas (`falta tipo`, `falta objeto`… — no tienen frontmatter) y **sin** errores en las tres de este spec, salvo `falta formato` no aplicable.

- [ ] **Step 3: Frontmatter de las cuatro heredadas**

`2026-07-23-emails-atomizados-sala-lectura-adversarial-review.md` — contiene **dos** revisiones (censo 1 y 2); el frontmatter escalar declara la **ronda 1** y el cuerpo conserva la 2:

```yaml
---
tipo: revision-adversarial
objeto: docs/superpowers/specs/2026-07-23-emails-atomizados-sala-lectura-design.md
objeto_rev: "1"
commit: no registrado
ronda: "1"
clase: diseño
revisor: Codex
cobertura: ejecutada
veredicto: no registrado
sha256_informe: no-disponible-legacy
adjudicado_en: docs/superpowers/specs/2026-07-23-emails-atomizados-sala-lectura-design.md §1
formato: hibrido-legacy
---
```

**Antes de escribirlo:** abre el acta y extrae `veredicto` de su §Veredicto; si no hay palabra del set, deja `no registrado`. Y `adjudicado_en` debe apuntar a la sección que la **Tarea 6** creará en el design; si aún no existe, esta acta se queda fuera de `_POBLACION_MIGRADA`… no aplica (G8 no usa esa lista), así que **el orden importa: haz la Tarea 6 antes del Step 3 para este fichero**, o apunta a `§1` solo si existe.

> **Dependencia declarada:** G8 exige que `adjudicado_en` resuelva a una sección real. Las tres actas cuyo objeto **no tiene aún encabezado** (censo 1-4) dependen de la Tarea 6. Ejecuta **Tarea 6 antes de esta Tarea 4** si el subagente encuentra el rojo; el plan las separa por responsabilidad, no por orden obligatorio.

`2026-07-26-gobernanza-indice-adversarial-review.md`:

```yaml
---
tipo: revision-adversarial
objeto: docs/superpowers/handoffs/handoff-2026-07-26-gobernanza-indice-adversarial.md
objeto_rev: "1"
commit: no registrado
ronda: "1"
clase: diseño
revisor: Claude Code (orquestador + 5 subagentes)
cobertura: ejecutada
veredicto: no registrado
sha256_informe: no-disponible-legacy
adjudicado_en: docs/superpowers/specs/2026-07-26-gobernanza-indice-adversarial-review.md §Adjudicación
formato: hibrido-legacy
---
```

Su adjudicación vive **en el propio acta** (línea 388), que es lo que la hace híbrida. `§Adjudicación` no casa `_RE_SECCION`, que espera un número: **usa `§1`** y renumera el encabezado del acta a `## 1. Adjudicación` — o, si prefieres no tocar el cuerpo, extiende `_RE_SECCION` a `§(\d+[\w-]*|[A-ZÁÉÍÓÚ][\w áéíóú]+)` y ajusta la comprobación. Decide **una** vía y aplícala a las cuatro.

`2026-07-27-cableado-atomize-sala-maquina-adversarial-review.md` (censo 4; la pasada de Claude es la fila 5, Tarea 8):

```yaml
---
tipo: revision-adversarial
objeto: docs/superpowers/specs/2026-07-27-cableado-atomize-sala-maquina-design.md
objeto_rev: "1"
commit: no registrado
ronda: "1"
clase: diseño
revisor: Codex
cobertura: ejecutada
veredicto: REQUIERE-REVISION
sha256_informe: no-disponible-legacy
adjudicado_en: docs/superpowers/specs/2026-07-27-cableado-atomize-sala-maquina-design.md §1
formato: hibrido-legacy
---
```

`veredicto: REQUIERE-REVISION` porque su §Veredicto dice «Revisión sustancial de la spec, no rediseño» y rechaza el REWORK de Codex como veredicto global. **Compruébalo abriendo el fichero**; si no lo sostiene, `SIN-VEREDICTO`.

`2026-07-29-feesdefender-dual-case-workspace-adversarial-review.md`:

```yaml
---
tipo: revision-adversarial
objeto: docs/superpowers/specs/2026-07-29-feesdefender-dual-case-workspace-design.md
objeto_rev: "1"
commit: 8d9c96c
ronda: "1"
clase: diseño
revisor: Claude
cobertura: ejecutada
veredicto: REQUIERE-REVISION
sha256_informe: no-disponible-legacy
adjudicado_en: docs/superpowers/specs/2026-07-29-feesdefender-dual-case-workspace-design.md §20
formato: hibrido-legacy
---
```

Esta ya resuelve: el §20 existe tras la Tarea 3.

- [ ] **Step 4: Añadir fixture negativa de la allowlist**

```python
def test_g8_rechaza_hibrido_legacy_fuera_de_la_allowlist():
    """El marcador no puede aplicarse a un acta nueva: seria una clase
    permanente fuera de guard (ronda 3, H-03)."""
    assert "2026-08-01-gobernanza-revisiones-adversariales-adversarial-review.md" \
        not in _ALLOWLIST_HIBRIDA
    assert len(_ALLOWLIST_HIBRIDA) == 4
```

- [ ] **Step 5: Verde, suite y commit**

Run: `python -m pytest tests/test_docs_gobernanza.py -q` → **PASS** (18 tests).
Run: `python -m pytest -q --tb=no` → **2706 passed**.

```bash
git add docs/superpowers tests/test_docs_gobernanza.py && git commit -m "docs(gobernanza): G8 + frontmatter de las cuatro actas hibridas heredadas"
```

---

### Task 5: cadena de custodia — marcadores, recómputo de hash y renombrado

**Files:**
- Modify + Rename: las 3 actas `2026-08-01-gobernanza-revisiones-adversariales-adversarial-review{,-r2,-r3}.md`
- Modify: `docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md` (§14-§16, campo `Informe recibido`)
- Modify: `tests/test_docs_gobernanza.py`

**Interfaces:**
- Consumes: `_fm`, `_es_acta`, `_ALLOWLIST_HIBRIDA`.
- Produces: `_MARCA_INI`, `_MARCA_FIN`, `_bloque_literal(txt) -> bytes | None`, `test_actas_cadena_de_custodia`.

- [ ] **Step 1: Escribir el test de integridad**

```python
_MARCA_INI = "<!-- informe-literal:inicio -->"
_MARCA_FIN = "<!-- informe-literal:fin -->"


def _bloque_literal(txt: str) -> bytes | None:
    """Bloque entre marcadores, canonicalizado: UTF-8, LF, un salto final.

    La canonicalizacion se fija sobre la FORMA, no sobre los bytes que llegaron:
    un informe escrito con CRLF hasharia distinto y la cadena se rompería sin
    que nadie hubiera alterado nada. Los tres informes del 2026-08-01 son LF, y
    para ellos digest bruto y canonico coinciden.
    """
    if _MARCA_INI not in txt or _MARCA_FIN not in txt:
        return None
    cuerpo = txt.split(_MARCA_INI, 1)[1].split(_MARCA_FIN, 1)[0]
    return (cuerpo.replace("\r\n", "\n").strip("\n") + "\n").encode("utf-8")


def test_actas_cadena_de_custodia():
    """G8b — el digest del bloque literal DEBE coincidir con `sha256_informe`.

    Presencia no es comparacion (ronda 3, H-04): una transcripcion alterada con
    un hash meramente presente pasaba el guard. Una desigualdad es ROJO, nunca
    aviso: un aviso convierte una cadena de custodia rota en suite verde.
    """
    import hashlib
    malos: dict[str, str] = {}
    for p, txt in _md_superpowers():
        if not _es_acta(txt) or p.name in _ALLOWLIST_HIBRIDA:
            continue
        fm = _fm(txt)
        declarado = fm.get("sha256_informe", "")
        if declarado == "no-disponible-legacy":
            malos[p.name] = "token legacy fuera de la allowlist cerrada"
            continue
        bloque = _bloque_literal(txt)
        if bloque is None:
            malos[p.name] = f"faltan los marcadores {_MARCA_INI} / {_MARCA_FIN}"
            continue
        real = hashlib.sha256(bloque).hexdigest()
        if real != declarado:
            malos[p.name] = f"sha256 declarado {declarado[:12]}… != recomputado {real[:12]}…"
        secciones = ["Informe recibido, sin modificar", "Evidencia verificada"]
        # M-2 (spec rev. 5): el §0 Mandato es obligatorio en el CUERPO solo si el
        # frontmatter no apunta fuera. `mandato` en si lo exige _CLAVES_ACTA.
        if fm.get("mandato", "").strip().startswith("§0"):
            secciones.append("Mandato")
        for sec in secciones:
            if sec not in txt:
                malos[p.name] = f"falta la sección «{sec}» del spec §6"
    assert not malos, f"actas con cadena de custodia rota: {malos}"
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `python -m pytest tests/test_docs_gobernanza.py::test_actas_cadena_de_custodia -q`
Expected: **FAIL**, `faltan los marcadores` en las tres actas de este spec.

- [ ] **Step 3: Poner los marcadores**

En cada una de las tres actas, el bloque literal es lo que hoy va entre la línea `---` que sigue al blockquote introductorio del §1 y la línea `---` que precede a `## 2. Evidencia verificada`. Sustituir esos dos `---` por los marcadores:

```
-  ---
+  <!-- informe-literal:inicio -->
```

```
-  ---
+  <!-- informe-literal:fin -->
```

- [ ] **Step 3-bis: Añadir `mandato:` a las tres actas (M-2 de la rev. 5)**

Los tres mandatos existen y están publicados: son el §13 del spec **en la revisión que se atacó**. No
se copian al acta; se apunta a ellos con su hash, que es lo que los hace localizables:

| Acta | Valor de `mandato:` |
|---|---|
| ronda 1 | `§13 de la rev. 1 del objeto (git 3126214)` |
| ronda 2 | `§13 de la rev. 2 del objeto (git 2c2a6d0)` |
| ronda 3 | `§13 de la rev. 3 del objeto (git 1a6e3d8)` |

Como ninguno usa `§0 de este acta`, **el cuerpo no necesita una sección `Mandato`** y el guard no la
exige. Las cuatro actas heredadas de la Tarea 4 llevan `mandato: no registrado`: sus encargos no se
publicaron en ningún sitio, y eso se declara en vez de reconstruirse.

- [ ] **Step 4: Verificar el digest y corregirlo si no cuadra**

Run:

```bash
python -c "import hashlib,pathlib,re,sys; sys.path.insert(0,'tests'); [print(p.name, hashlib.sha256((p.read_text(encoding='utf-8').split('<!-- informe-literal:inicio -->',1)[1].split('<!-- informe-literal:fin -->',1)[0].replace(chr(13)+chr(10),chr(10)).strip(chr(10))+chr(10)).encode()).hexdigest()) for p in sorted(pathlib.Path('docs/superpowers/specs').glob('2026-08-01-*adversarial-review*.md'))]"
```

Expected, y **estos son los valores que deben salir**:

- `…-adversarial-review.md` → `4f45f867de828badfdcd9f583e1731856001265ee345bb910f450b5142663f58`
- `…-adversarial-review-r2.md` → `20c45f93c0460a8f91ba426c9570ac918b01882a43f07aec9f549166070f4114`
- `…-adversarial-review-r3.md` → `43b945e24a9aa990bc7aea1ffc0d4aae205e21a55f6f3241383bc6781587a325`

Si alguno **no** coincide con su `sha256_informe`, la transcripción difiere del original en algún byte. **No cambies el frontmatter para que cuadre**: recupera el original de `%TEMP%\revision-gobernanza-revisiones{,-rev2,-r3}.md`, diffea, corrige el **bloque**, y solo entonces vuelve a medir. El frontmatter es la referencia; el cuerpo es lo que se ajusta.

- [ ] **Step 5: Renombrar al esquema del §6**

Esquema: `AAAA-MM-DD-<tema>-<objeto>-r<N>[-<revisor>]-adversarial-review.md`.

**Este plan no puede escribir los tres nombres destino**, y la razón es la misma restricción que manda el informe de Codex a `%TEMP%`: `test_citas_a_specs_y_plans_existen` (G2) exige que toda cita a un fichero de `docs/superpowers/specs|plans` **resuelva en disco**, y el destino no existe hasta que corras el `git mv`. Escribirlo aquí deja la suite en rojo desde el momento en que se commitea el plan. Se da como **regla de transformación**:

| Parte del nombre | Actual | Nuevo |
|---|---|---|
| tema | `…-gobernanza-revisiones-adversariales-…` | `…-gobernanza-revisiones-…` |
| objeto + ronda | sufijo `-adversarial-review.md`, `-adversarial-review-r2.md`, `-adversarial-review-r3.md` | infijo `-spec-r1-`, `-spec-r2-`, `-spec-r3-` antes de `adversarial-review.md` |
| revisor | — | se omite: los tres son de Codex y no hay colisión |

Construye cada destino aplicando esa regla y ejecútalo con `git mv`, un fichero por comando. Verifica antes con `git mv --dry-run` y después con `ls docs/superpowers/specs/*adversarial-review*.md`, que debe listar siete ficheros: las cuatro heredadas y las tres renombradas.

- [ ] **Step 6: Actualizar las tres referencias del spec**

En `…-design.md`, campo `Informe recibido` de §14, §15 y §16, y las dos menciones del bloque de cabecera. **G2 (`test_citas_a_specs_y_plans_existen`) fallará si el rename y la actualización de citas no entran en el MISMO commit.**

- [ ] **Step 7: Verde, suite y commit**

Run: `python -m pytest tests/test_docs_gobernanza.py -q` → **PASS** (19 tests).
Run: `python -m pytest -q --tb=no` → **2707 passed**.

```bash
git add -A docs/superpowers tests/test_docs_gobernanza.py && git commit -m "docs(gobernanza): marcadores del bloque literal, recomputo de hash en G8 y renombrado de actas"
```

---

### Task 6: reconstruir la clase `diseño` sin encabezado

**Files:**
- Modify: `docs/superpowers/specs/2026-07-23-emails-atomizados-sala-lectura-design.md` (nuevo §; censo 1-2)
- Modify: `docs/superpowers/specs/2026-07-27-cableado-atomize-sala-maquina-design.md` (nuevo §; censo 4)
- Modify: `docs/superpowers/handoffs/handoff-2026-07-26-gobernanza-indice-adversarial.md` (censo 3)
- Modify: `docs/superpowers/plans/2026-07-29-dual-workspace-fase0-fase1.md` (censo 11-13)
- Modify: `docs/superpowers/plans/2026-07-26-sala-lectura-bundle-por-hilo.md` (censo 22-23)
- Modify: `docs/superpowers/plans/2026-07-29-email-atomize-enumeracion-recursiva.md` (censo 15)
- Modify: `docs/superpowers/specs/2026-07-27-vista-procesal-05-procedimiento-design.md` (censo 9, ronda 2)
- Modify: `tests/test_docs_gobernanza.py`

**Interfaces:** consume `_POBLACION_MIGRADA`; no produce nombres nuevos.

> **Nota sobre el handoff (censo 3).** El objeto es un handoff, y su población tiene guards propios (G4-G6). Añadirle una sección de adjudicación **no** rompe G4 (comprueba presencia de campos, nunca ausencia) ni G5 (nombre) ni G6 (fila en INDICE). Verifícalo corriendo el fichero de guards tras el cambio.

- [ ] **Step 1: Ampliar población y ver el rojo**

Añadir los siete nombres a `_POBLACION_MIGRADA`. Run el guard: **FAIL**, cero adjudicaciones detectadas en esos ficheros (el test solo valida lo que encuentra, así que **el rojo real llega en el Step 8**, con el chequeo de completitud). Si el guard pasa, es esperado: sigue.

- [ ] **Step 2: Fase 0 dual, tres rondas**

En `plans/2026-07-29-dual-workspace-fase0-fase1.md`, añadir al final tres secciones. Datos de `PLAN.md:583-597` y `docs/bitacora/2026.md:132-136`. **Abre las dos fuentes y confirma cada campo antes de escribirlo.**

```markdown
## Adjudicación de la revisión adversarial del PLAN (Codex, 2026-07-29) — no registrado, remediado

- **Clase:** diseño
- **Objeto revisado:** `docs/superpowers/plans/2026-07-29-dual-workspace-fase0-fase1.md` rev. 1, commit `no registrado`
- **Ronda:** 1
- **Revisor:** Codex (solo lectura)
- **Cobertura:** ejecutada
- **Informe recibido:** no archivado (anterior a esta regla)
- **Hallazgos:** no registrado
- **Remediado en:** rev. 2 de este plan; produjo de rebote el PR #156

## Adjudicación de la revisión adversarial del PLAN (Codex, 2026-07-29) — NO-EJECUTABLE, remediado

- **Clase:** diseño
- **Objeto revisado:** `docs/superpowers/plans/2026-07-29-dual-workspace-fase0-fase1.md` rev. 2, commit `no registrado`
- **Ronda:** 2
- **Revisor:** Codex (solo lectura)
- **Cobertura:** ejecutada
- **Informe recibido:** no archivado (anterior a esta regla)
- **Hallazgos:** 8 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** rev. 3 de este plan; produjo de rebote el PR #160

## Adjudicación de la revisión adversarial del PLAN (Codex, 2026-07-29) — REQUIERE-REVISION, remediado

- **Clase:** diseño
- **Objeto revisado:** `docs/superpowers/plans/2026-07-29-dual-workspace-fase0-fase1.md` rev. 3, commit `no registrado`
- **Ronda:** 3
- **Revisor:** Codex (solo lectura)
- **Cobertura:** ejecutada
- **Informe recibido:** no archivado (anterior a esta regla)
- **Hallazgos:** 5 confirmados · 0 rebajados · 1 refutados · 0 escalados · 1 sin verificar
- **Remediado en:** rev. 4 de este plan, PR #166 (`716b483`)
```

**Ronda 1 lleva `no registrado` como veredicto** y por tanto **no casará el regex**, que exige un token del set. Dos vías: (a) extraer el veredicto del primer bloque `GATE CONSUMIDO` de `PLAN.md` —lo más probable es `NO-EJECUTABLE`, como dice la bitácora del 45º cierre— y usarlo; (b) si la fuente no lo dice, usar `SIN-VEREDICTO`, que **sí** está en el set y significa exactamente eso. **Usa (a) si la fuente lo sostiene; si no, (b). Nunca `no registrado` en el encabezado.**

**Ronda 2, 8 confirmados = 3 B0 + 4 A + 1 M**, «todo confirmado contra el fuente y nada refutado» (`PLAN.md:587-593`).
**Ronda 3 = 5 confirmados, 1 refutado, 1 sin verificar** (`PLAN.md:595-597`), sobre 3 B0 + 2 A.

- [ ] **Step 3: emails atomizados, dos rondas**

En `specs/2026-07-23-emails-atomizados-sala-lectura-design.md`, dos secciones. Los datos están en su acta; **ábrela y extrae veredicto y recuento de cada ronda**. Plantilla de la ronda 1:

```markdown
## Adjudicación de la revisión adversarial (Codex, 2026-07-23) — <VEREDICTO del acta>, remediado

- **Clase:** diseño
- **Objeto revisado:** `docs/superpowers/specs/2026-07-23-emails-atomizados-sala-lectura-design.md` rev. 1, commit `no registrado`
- **Ronda:** 1
- **Revisor:** Codex (solo lectura)
- **Cobertura:** ejecutada
- **Informe recibido:** `2026-07-23-emails-atomizados-sala-lectura-adversarial-review.md` (híbrida legacy)
- **Hallazgos:** <del acta, o no registrado>
- **Remediado en:** <del acta o de PLAN.md>
```

Ronda 2: igual, con `**Ronda:** 2`, `**Revisor:** Claude` y la fecha `2026-07-27` que declara el acta en su `:9-16`.

- [ ] **Step 4: cableado atomize spec (censo 4)**

En `specs/2026-07-27-cableado-atomize-sala-maquina-design.md`, una sección con `Ronda: 1`, `Revisor: Codex (solo lectura)`, `Informe recibido: 2026-07-27-cableado-atomize-sala-maquina-adversarial-review.md (híbrida legacy)`, y el veredicto que fije la Tarea 4 Step 3 para esa acta. Los **13 hallazgos** de su tabla de adjudicación dan el recuento: cuéntalos en el acta y desglósalos por veredicto adjudicado (hay al menos dos «rebajados» explícitos: H-06 de ALTO a MEDIO y H-10 de MEDIO a BAJO).

- [ ] **Step 5: handoff de gobernanza (censo 3)**

En `handoffs/handoff-2026-07-26-gobernanza-indice-adversarial.md`, añadir la sección. Datos de `docs/bitacora/2026.md:152` y `PLAN.md:2128`: **4 de 5 refutados**, H2 confirmado con matiz, más 6 defectos reales D1-D6 encontrados de rebote.

```markdown
## Adjudicación de la revisión adversarial (Claude Code + 5 subagentes, 2026-07-26) — SIN-VEREDICTO, sin-cambios

- **Clase:** diseño
- **Objeto revisado:** `docs/superpowers/handoffs/handoff-2026-07-26-gobernanza-indice-adversarial.md` rev. 1, commit `no registrado`
- **Ronda:** 1
- **Revisor:** Claude Code (orquestador + 5 subagentes en paralelo, uno por hallazgo)
- **Cobertura:** ejecutada
- **Informe recibido:** `2026-07-26-gobernanza-indice-adversarial-review.md` (híbrida legacy)
- **Hallazgos:** 1 confirmados · 0 rebajados · 4 refutados · 6 escalados · 0 sin verificar
- **Remediado en:** PR #127, #128 y #129
```

`SIN-VEREDICTO` porque el objeto era un diagnóstico y el resultado fue por hallazgo, no un veredicto global. `estado_remediacion: sin-cambios` porque el diagnóstico no se corrigió: se refutó. Los **6 escalados** son los D1-D6 encontrados de rebote. **Contrasta los tres números con `PLAN.md:2128` antes de escribirlos.**

- [ ] **Step 6: bundle por hilo, dos rondas de diseño (censo 22-23)**

En `plans/2026-07-26-sala-lectura-bundle-por-hilo.md`. `docs/bitacora/2026.md:150` confirma «dos revisiones adversariales» y un «re-tajo» posterior; el revisor no consta. Dos secciones con `Revisor: no registrado`, veredicto del set según lo que la bitácora sostenga (`REQUIERE-REVISION` si forzaron re-tajo), `Hallazgos: no registrado`, `Remediado en: PR #131 + PR #132`.

- [ ] **Step 7: enumeración recursiva, plan (censo 15) y vista procesal ronda 2 (censo 9)**

Enumeración: sección en `plans/2026-07-29-email-atomize-enumeracion-recursiva.md`, datos de `docs/bitacora/2026.md:134`.

Vista procesal ronda 2: **segunda** sección en su design (la ronda 1 quedó en la Tarea 3, §10). Datos de `handoff-2026-07-27-vista-procesal-codex-review-2.md`, que declara `veredicto: NO SHIP` y **6 hallazgos N1-N6**; el `INDICE.md` añade que N6 fue al código, N1 a la pieza 2 (PR #140) y N3 sigue abierta → `estado_remediacion: parcial`.

- [ ] **Step 8: Chequeo de completitud del censo**

```python
def test_censo_postcorte_completo():
    """Criterio 6 del spec: cada revision postcorte esta representada EXACTAMENTE
    una vez. La matriz vive en el plan de migracion; aqui se comprueba el conteo
    por fichero, que es lo que un guard puede sostener.
    """
    esperado = {
        "2026-07-23-emails-atomizados-sala-lectura-design.md": 2,
        "handoff-2026-07-26-gobernanza-indice-adversarial.md": 1,
        "2026-07-27-cableado-atomize-sala-maquina-design.md": 1,
        "2026-07-27-vista-procesal-05-procedimiento-design.md": 2,
        "2026-07-28-cableado-atomize-sala-maquina.md": 2,
        "2026-07-28-email-atomize-enumeracion-recursiva-design.md": 1,
        "2026-07-29-dual-workspace-fase0-fase1.md": 3,
        "2026-07-29-email-atomize-enumeracion-recursiva.md": 2,
        "2026-07-29-feesdefender-dual-case-workspace-design.md": 1,
        "2026-07-29-sandwich-firma-falso-positivo-design.md": 1,
        "2026-07-29-sandwich-firma-falso-positivo.md": 2,
        "2026-07-30-historial-citado-localizable-design.md": 1,
        "2026-07-26-sala-lectura-bundle-por-hilo.md": 3,
        "2026-08-01-gobernanza-revisiones-adversariales-design.md": 3,
    }
    real = {}
    for p, txt in _md_superpowers():
        if _es_acta(txt):
            continue
        n = len(_adjudicaciones(txt))
        if n:
            real[p.name] = n
    assert real == esperado, (
        f"censo desalineado.\nsobran/faltan: "
        f"{ {k: (real.get(k), esperado.get(k)) for k in set(real) ^ set(esperado) | "
        f"{k for k in set(real) & set(esperado) if real[k] != esperado[k]} } }")
```

Los conteos suman **25** adjudicaciones embebidas: las 28 del censo menos las 3 de clase `autorrevision` de la Tarea 8… **no**: las autorrevisiones también llevan encabezado. Recuenta contra la tabla del censo antes de fijar `esperado`, y ajústalo en la Tarea 8 cuando entren las filas 5 y 25.

- [ ] **Step 9: Verde, suite y commit**

Run: `python -m pytest tests/test_docs_gobernanza.py -q` → **PASS**.
Run: `python -m pytest -q --tb=no`.

```bash
git add docs/superpowers tests/test_docs_gobernanza.py && git commit -m "docs(gobernanza): reconstruida la clase diseno sin encabezado (censo 1-4, 9, 11-13, 15, 22-23)"
```

---

### Task 7: reconstruir la clase `rama` y su cobertura por tarea

**Files:**
- Modify: `docs/superpowers/plans/2026-07-28-cableado-atomize-sala-maquina.md` (censo 7 + las 7 por tarea)
- Modify: `docs/superpowers/plans/2026-07-29-email-atomize-enumeracion-recursiva.md` (censo 16)
- Modify: `docs/superpowers/plans/2026-07-26-sala-lectura-bundle-por-hilo.md` (censo 24)
- Modify: `tests/test_docs_gobernanza.py` (`esperado` del censo)

**Interfaces:** consume todo lo anterior; no produce nombres nuevos.

- [ ] **Step 1: cableado, rama + cobertura agregada**

`docs/bitacora/2026.md:138`: build por subagentes, **7 tareas, revisión por tarea + revisión de rama**, y el informe de la ronda 2 añade que la de rama devolvió NO-SHIP con un Critical destructivo.

```markdown
## Adjudicación de la revisión adversarial de rama completa (Opus, 2026-07-28) — NO-SHIP, remediado

- **Clase:** rama
- **Objeto revisado:** rama del build de cableado atomize, PR #151
- **Ronda:** 1
- **Revisor:** Opus (otra sesión)
- **Cobertura:** ejecutada (7 revisiones por tarea agregadas)
- **Informe recibido:** no archivado (anterior a esta regla)
- **Hallazgos:** 1 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** PR #151
```

Debajo de la ficha, la enumeración que el spec §1.2 exige para la cobertura agregada:

```markdown
**Hallazgos sustantivos de las revisiones por tarea** (7 tareas, agregadas en esta revisión de rama):
un Critical destructivo en la revisión de rama —descrito en `docs/bitacora/2026.md:138`— y las
correcciones por tarea que el propio build absorbió. No consta informe por tarea: se declara la
cobertura, no se reconstruyen hallazgos que no dejaron rastro.
```

**Verifica en la bitácora si el Critical era de la rama o de una tarea** y ajusta la prosa. No lo dupliques en las dos.

- [ ] **Step 2: enumeración recursiva, rama (censo 16)**

`PLAN.md:383-386` la nombra («el que añadió la revisión final de rama») y da su producto: el Gate 2, medido y negativo.

```markdown
## Adjudicación de la revisión adversarial de rama completa (Codex, 2026-07-29) — LISTA-CON-CAMBIOS, remediado

- **Clase:** rama
- **Objeto revisado:** rama de `MEJORAS #98`, PR #155
- **Ronda:** 1
- **Revisor:** Codex (solo lectura)
- **Cobertura:** ejecutada
- **Informe recibido:** no archivado (anterior a esta regla)
- **Hallazgos:** 1 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** PR #155, Gate 2 añadido al plan
```

- [ ] **Step 3: bundle por hilo, rama (censo 24)**

`PLAN.md:757-761`: la revisión final encontró **tres caminos de pérdida/sobrescritura** y forzó «nombres como función pura del fichero de origen»; `docs/bitacora/2026.md:150` la sitúa entre el build y el merge.

```markdown
## Adjudicación de la revisión adversarial de rama completa (no registrado, 2026-07-27) — NO-SHIP, remediado

- **Clase:** rama
- **Objeto revisado:** rama del bundle por hilo, PR #131 + PR #132
- **Ronda:** 1
- **Revisor:** no registrado
- **Cobertura:** ejecutada
- **Informe recibido:** no archivado (anterior a esta regla)
- **Hallazgos:** 3 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** PR #131 + PR #132; +10 tests del §6 del spec
```

- [ ] **Step 4: Actualizar `esperado` y verificar**

Sube a 2 el conteo de `2026-07-28-cableado-atomize-sala-maquina.md` (ya estaba), a 2 el de `…-enumeracion-recursiva.md` (plan + rama) y a 3 el de bundle (2 diseño + 1 rama).

Run: `python -m pytest tests/test_docs_gobernanza.py -q` → **PASS**.

- [ ] **Step 5: Suite y commit**

Run: `python -m pytest -q --tb=no`.

```bash
git add docs/superpowers tests/test_docs_gobernanza.py && git commit -m "docs(gobernanza): reconstruida la clase rama y la cobertura por tarea (censo 7, 16, 24)"
```

---

### Task 8: reconstruir la clase `autorrevision`

**Files:**
- Modify: `docs/superpowers/specs/2026-07-27-cableado-atomize-sala-maquina-design.md` (censo 5, segunda sección)
- Modify: un documento del PR #147 para el censo 25 — si no hay spec ni plan de `MEJORAS #90`, la sección va en `docs/MEJORAS_FUTURAS.md` bajo la entrada `#90`
- Modify: `tests/test_docs_gobernanza.py`

**Interfaces:** consume todo lo anterior.

> **Decisión que el ejecutor debe tomar y declarar:** el censo 25 (OCR ciego, PR #147) es una autorrevisión sobre un diff cuyo objeto **no tiene spec ni plan propio**. Si `docs/MEJORAS_FUTURAS.md` recibe la sección, entra en la población de G7 y hay que añadirlo a `_POBLACION_MIGRADA` — comprueba antes que G1 (`test_mejoras_futuras_numeracion_unica`) sigue verde, porque ese fichero tiene su propio guard de numeración `## NN.`.

- [ ] **Step 1: cableado, pasada propia de Claude (censo 5)**

El acta de cableado declara «Codex (independiente) + pasada propia de Claude (no independiente: autor de la spec)». Son dos revisiones (spec §1.3), así que el design lleva **dos** secciones: la de la Tarea 6 Step 4 (Codex) y esta.

```markdown
## Adjudicación de la autorrevisión (Claude, 2026-07-27) — SIN-VEREDICTO, remediado

- **Clase:** autorrevision
- **Objeto revisado:** `docs/superpowers/specs/2026-07-27-cableado-atomize-sala-maquina-design.md` rev. 1, commit `no registrado`
- **Ronda:** 1
- **Revisor:** Claude (no independiente: autor del objeto)
- **Cobertura:** ejecutada
- **Informe recibido:** sin informe (autorrevisión)
- **Hallazgos:** 2 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** rev. 2 de este documento
```

⚠️ **El encabezado dice «autorrevisión», no «revisión adversarial», así que NO casa `_RE_ADJUDICACION` ni lo detecta el disparador.** Dos vías, elige **una** y aplícala a las dos autorrevisiones: (a) usar `## Adjudicación de la revisión adversarial (Claude, 2026-07-27) — …` y dejar que la `Clase: autorrevision` de la ficha sea lo que la distinga —**recomendada**, no toca el regex—; o (b) ampliar el disparador y el regex a `(?:revisión adversarial|autorrevisión)`, lo que obliga a un test nuevo. **La (a) mantiene un solo formato y es la que el spec §5 describe.**

Los **2 confirmados** son los hallazgos propios H-04 y H-06 de la tabla del acta de cableado. Cuéntalos en el acta.

- [ ] **Step 2: OCR ciego (censo 25)**

Datos de `docs/bitacora/2026.md:144`: PR #147, `MEJORAS #90` (a)+(b), y la revisión propia sobre el diff con **tres correcciones**. **Abre esa línea completa y confirma las tres antes de escribir el recuento.**

```markdown
## Adjudicación de la revisión adversarial (Claude, 2026-07-27) — LISTA-CON-CAMBIOS, remediado

- **Clase:** autorrevision
- **Objeto revisado:** diff de `MEJORAS #90` (a)+(b), PR #147
- **Ronda:** 1
- **Revisor:** Claude (no independiente: autor del objeto)
- **Cobertura:** ejecutada
- **Informe recibido:** sin informe (autorrevisión)
- **Hallazgos:** 3 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** PR #147
```

- [ ] **Step 3: Cerrar el censo**

Extrae `esperado` a constante de módulo `_CENSO_ESPERADO` y añade las dos autorrevisiones.

**NO escribas un test que afirme un total literal** (`sum(...) == 28`). Sería el defecto H-07 por tercera vez: un número que la siguiente adjudicación invalida — y la siguiente es la de **este mismo plan**, que al adjudicarse añade una fila y sube el censo a 29. `_CENSO_ESPERADO` ya obliga a actualizarlo cuando entra una revisión nueva, y eso es exactamente lo que debe hacer el guard; un total agregado no añade cobertura y sí añade una trampa.

Comprueba a mano, una vez, que `sum(_CENSO_ESPERADO.values())` coincide con las filas de la tabla del censo de este plan, y deja constancia en el mensaje de commit. Ese cuadre es una verificación de migración, no un invariante permanente.

- [ ] **Step 4: Verde, suite y commit**

Run: `python -m pytest tests/test_docs_gobernanza.py -q` → **PASS**.
Run: `python -m pytest -q --tb=no`.

```bash
git add docs tests/test_docs_gobernanza.py && git commit -m "docs(gobernanza): reconstruida la clase autorrevision y cerrado el censo en 28"
```

---

### Task 9: doctrina

**Files:**
- Modify: `CLAUDE.md` §«Revisión adversarial»
- Modify: `AGENTS.md` (los cuatro cambios del spec §10.1)
- Modify: `docs/GOBERNANZA_FUENTES_VERDAD.md` §5
- Modify: `tests/test_docs_gobernanza.py` (cabecera)

**Interfaces:** ninguna dependencia de código.

- [ ] **Step 1: `CLAUDE.md` — resolver el «o»**

Sustituir «Claude adjudica cada hallazgo contra el código real y registra la adjudicación **en el spec o el plan**» por el reparto del spec §3: la adjudicación va **embebida** en el objeto con encabezado canónico y ficha; el informe recibido va al **acta** siempre que exista respuesta textual recuperable; y nombrar las tres clases con su traza.

- [ ] **Step 2: `AGENTS.md` — los cuatro cambios del §10.1**

**No** debilitar «solo lectura». Redacción exacta a incorporar:

> El repo, los ficheros ignorados, `data/CASOS/` y los sistemas externos (CRM, Drive) son **entradas de solo lectura durante toda la revisión**. Se permite **ejecutar código y tests** cuando todas sus escrituras están redirigidas fuera del repo y no hay efectos externos: `PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider`, `--basetemp` fuera del árbol. `git status --porcelain --untracked-files=all` antes y después es evidencia adicional, **no sustituto** de la prohibición.

Más: informe **fuera del repo** con nombre por `(objeto, ronda)` y **sin sobrescribir** informes anteriores; hallazgos `H-NN` con severidad; el mandato llega **numerado y ordenado por daño** y el informe lo contesta punto por punto; el objeto se ancla a un **commit**. Y el caso resuelto del §10.1.3: el revisor no adjudica porque un hallazgo correcto puede traer un remedio que se lleve por delante el objetivo del encargo.

- [ ] **Step 3: `GOBERNANZA_FUENTES_VERDAD.md` §5**

Añadir: el acta `…-adversarial-review.md` es el hogar del **informe recibido**, con su `sha256_informe`; los tres `handoff-2026-07-27-vista-procesal-codex-*` quedan como **excepción histórica declarada**, igual que `prompt_handoff_expedientes_seguros.md`.

- [ ] **Step 4: Cabecera del fichero de guards**

Añadir la tercera población al aviso anti-D3 existente, nombrando los tres sets y el porqué de `estado_remediacion`.

- [ ] **Step 5: Verde, suite y commit**

Run: `python -m pytest -q --tb=no`.

```bash
git add CLAUDE.md AGENTS.md docs/GOBERNANZA_FUENTES_VERDAD.md tests/test_docs_gobernanza.py && git commit -m "docs(doctrina): las tres clases, la traza y el contrato del revisor sin debilitar solo-lectura"
```

---

### Task 10: retirar el andamio y activar los guards sobre todo el corpus

**Files:**
- Modify: `tests/test_docs_gobernanza.py`

- [ ] **Step 1: Retirar `_POBLACION_MIGRADA`**

En `test_adjudicaciones_bien_formadas`, sustituir

```python
        if p.name not in _POBLACION_MIGRADA or _es_acta(txt):
```

por

```python
        if _es_acta(txt):
```

y borrar la constante y su comentario de andamio.

- [ ] **Step 2: Correr y ver qué aparece**

Run: `python -m pytest tests/test_docs_gobernanza.py::test_adjudicaciones_bien_formadas -q`
Expected: **PASS** si el censo está completo. Si falla, cada entrada es una adjudicación que las Tareas 2-8 no cubrieron: **añádela al censo de este plan y arréglala**, no la excluyas.

- [ ] **Step 3: Suite completa y verificación final**

Run: `python -m pytest -q --tb=no`
Expected: **0 failed**. El total sube ~13 tests sobre 2696.

Run: `git status --short` → vacío.

- [ ] **Step 4: Commit**

```bash
git add tests/test_docs_gobernanza.py && git commit -m "test(gobernanza): retirado el andamio de poblacion migrada; G7/G8 cubren todo el corpus"
```

- [ ] **Step 5: Cerrar el ítem**

Marcar `[x]` en `PLAN.md` con el hash del PR, y anotar en `docs/bitacora/2026.md` el bloque de cierre: tres rondas de revisión adversarial sobre el spec (NO-SHIP → NO-SHIP → LISTA-CON-CAMBIOS, 16/16 confirmados) y la migración de 28 revisiones postcorte.

---

## Self-Review

**1. Cobertura del spec.** §1.1 predicado → censo + Tarea 6 Step 5 (handoff). §1.2 tres clases y traza → Tareas 6, 7, 8. §1.3 identidad → censo (una fila por tupla). §1.4 corte → censo, «fuera de la población». §1.5 cardinalidad → censo (aquí sí se publica: 28). §3 modelo → Tareas 2-8. §4 vocabularios → Tarea 1 (sets) + Global Constraints. §5 encabezado y ficha → Tarea 1 (regex, `_CAMPOS_FICHA`). §5.1 parser y cercas → Tarea 1 (`_sin_cercas`, G7-bis). §6 acta y nombre → Tareas 4 y 5. §6.1 hash → Tarea 5. §7 generador diferido → **no se escribe**, correcto. §8 G7/G8 → Tareas 1, 4, 5. §9 política de migración → estructura de tareas + desviación declarada. §10 y §10.1 doctrina → Tarea 9. §12 criterios → Tarea 10 Step 3 (1), Tareas 2-4 (2), Tarea 1 G7-bis (3), Tareas 4-5 fixtures (4), censo + Tarea 10 (5), `test_censo_suma_28` (6), nada crea el registro ni el generador (7), Global Constraints (8).

**2. Placeholders.** Los `no registrado` son valores definidos por el spec, no huecos. Los tres puntos donde el plan **delega una decisión al ejecutor** están marcados y acotados: la forma de `_RE_SECCION` para `§Adjudicación` (Tarea 4 Step 3), el encabezado de las autorrevisiones (Tarea 8 Step 1, con recomendación) y el hogar de la sección del censo 25 (Tarea 8 Step 2). Cada uno dice qué elegir y por qué.

**3. Consistencia de tipos.** `_POBLACION_MIGRADA` (Tarea 1, retirada en 10), `_ALLOWLIST_HIBRIDA` (4), `_MARCA_INI`/`_MARCA_FIN` y `_bloque_literal` (5), `_CENSO_ESPERADO` (6, extraída a constante en 8). `_sin_cercas` devuelve `list[str]` y `_adjudicaciones` `list[tuple[int, str]]` en todas las tareas. `_es_acta` y `_md_superpowers` se definen una vez en la Tarea 1.

**4. Riesgo que el ejecutor debe vigilar.** El `esperado` del censo (Tarea 6 Step 8) es el punto frágil: se fija antes de que entren las autorrevisiones y se cierra en la Tarea 8. Si un conteo no cuadra, la respuesta es **recontar contra la tabla del censo**, nunca ajustar `esperado` para que pase.
