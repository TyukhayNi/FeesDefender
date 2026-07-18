# Gobernanza de la planificación — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hacer `PLAN.md` legible de un vistazo (cola priorizada + ledger de cerrados), blindar la limpieza con un guardarraíl en `session_close`, auditar el estado de los planes legacy y reubicarlos fuera de `docs/` raíz.

**Architecture:** Dos entregables independientes. PR-A (Tasks 1-6): código nuevo en `scripts/session_close.py` (detectores puros + aviso, TDD) que además sirve de verificación para la reestructuración de `PLAN.md`, más la auditoría de `estado:` y la anotación de la fase C. PR-B (Task 7): mover los 11 `docs/PLAN_*.md` a `docs/superpowers/plans/` corrigiendo referencias, con test-guard anti-regresión.

**Tech Stack:** Python 3, pytest, git. Edición de Markdown. Sin dependencias nuevas.

## Global Constraints

- **Encoding SIEMPRE UTF-8 sin BOM.** Al leer/escribir `.md` desde Python usar `encoding="utf-8"`.
- **Trabajar SOLO en el worktree** `C:\Users\tnm33\Dev\FeesDefender\.claude\worktrees\nuevo-caso-crm-intake-149a57`. Nunca rutas absolutas a la raíz compartida `Dev\FeesDefender` (otra sesión puede sobrescribir sin conflicto de git). `STATUS.md`/`PLAN.md` son ficheros de alta contención: releer en fresco justo antes de editar.
- **`main` protegida:** el trabajo va en rama + PR (check `leak-scan` obligatorio). Nunca push directo a `main`.
- **Commits acotados:** `git add <rutas exactas>`, **nunca** `git add -A`.
- **Los avisos de `session_close` NUNCA bloquean el cierre** (se envuelven en `try/except` en `main()`, patrón de los avisos existentes).
- **PowerShell (Windows):** los comandos de test usan `python -m pytest`; van desde la raíz del worktree.

---

## File Structure

- `scripts/session_close.py` — MODIFY. Añade constantes de umbral, 4 funciones puras (`_contar_lineas`, `_indice_cerrados`, `_cerrados_sin_colapsar`, `_contar_cerrados`), la función de aviso `_avisar_higiene_planificacion` y su enganche en `main()`. Es el único código nuevo.
- `tests/test_session_close_aviso.py` — MODIFY. Añade tests de las funciones puras y del aviso (patrón existente: `import scripts.session_close as sc`, `monkeypatch` de `ROOT` con `tmp_path`).
- `PLAN.md` — MODIFY. Cabecera de cola priorizada (D1) + sección `## Cerrados` con los 14 bloques ✅ colapsados (D2).
- `STATUS.md` — MODIFY. El `[SIGUIENTE]` deja de restatarse y enlaza a la cola de `PLAN.md`.
- `docs/PLAN_*.md` (11) + `docs/DESPLIEGUE_MCP_DRIVE_DISCO.md` + `docs/prompt_handoff_expedientes_seguros.md` — MODIFY frontmatter `estado:` (D4).
- `docs/INDICE.md` — MODIFY. Estados corregidos + (PR-B) rutas nuevas de los planes.
- `docs/MEJORAS_FUTURAS.md` — MODIFY. Entrada de backlog para la fase C.
- `tests/test_docs_gobernanza.py` — CREATE. Guard de `estado:` válido (PR-A) + guard anti-referencia a `docs/PLAN_*` (PR-B).
- Los 11 `docs/PLAN_*.md` → `docs/superpowers/plans/` (PR-B, Task 7) + refs en `core/`, `scripts/`, `tests/`, docs.

---

## PR-A — Cola, ledger, guardarraíl y auditoría

### Task 1: Detectores puros de higiene de PLAN.md

**Files:**
- Modify: `scripts/session_close.py` (añadir tras `_plan_items_desfasados`, antes de `_avisar_plan_desfasado`)
- Test: `tests/test_session_close_aviso.py`

**Interfaces:**
- Consumes: nada (funciones puras sobre texto).
- Produces:
  - `_STATUS_MAX_LINEAS: int = 400`, `_CERRADOS_MAX: int = 30`
  - `_contar_lineas(texto: str) -> int`
  - `_indice_cerrados(lineas: list[str]) -> int | None`
  - `_cerrados_sin_colapsar(plan_texto: str) -> list[str]` — títulos de encabezados **cuyo texto empieza por `✅`** situados ANTES de la sección `## Cerrados`. Un encabezado con ✅ a mitad (p. ej. `[SIGUIENTE-GOOGLE-MCP] F1 ✅ …`) es un ítem ABIERTO con una fase hecha → NO se marca.
  - `_contar_cerrados(plan_texto: str) -> int` — nº de entradas `- ` bajo la sección `## Cerrados`.

- [ ] **Step 1: Write the failing tests**

Añadir al final de `tests/test_session_close_aviso.py`:

```python
# --- Higiene de PLAN.md: detectores puros (D3) ---

_PLAN_CON_LEDGER = (
    "# PLAN\n"
    "## 🎯 Cola priorizada\n"
    "| # | Ítem | Estado |\n"
    "| 1 | B5 | en curso |\n"
    "## [SIGUIENTE-GOOGLE-MCP] F1 ✅ MERGEADA · F4 pendiente\n"
    "texto de un item ABIERTO con una fase hecha\n"
    "## ✅ Cerrados\n"
    "> ledger\n"
    "- ✅ **[FOO]** algo — PR #1\n"
    "- ✅ **[BAR]** otra — PR #2\n"
)

_PLAN_CON_CERRADO_SUELTO = (
    "# PLAN\n"
    "## ✅ [VIEJO] COMPLETA\n"
    "MERGEADA a main. Rama podada.\n"
    "## ✅ Cerrados\n"
    "- ✅ **[FOO]** algo — PR #1\n"
)


def test_contar_lineas():
    assert sc._contar_lineas("a\nb\nc") == 3
    assert sc._contar_lineas("") == 0


def test_indice_cerrados_encuentra_la_seccion():
    lineas = _PLAN_CON_LEDGER.splitlines()
    i = sc._indice_cerrados(lineas)
    assert lineas[i].strip() == "## ✅ Cerrados"


def test_indice_cerrados_none_si_no_existe():
    assert sc._indice_cerrados(["# PLAN", "## Cola"]) is None


def test_cerrados_sin_colapsar_ignora_item_abierto_con_fase_hecha():
    # El ✅ va a mitad del encabezado (fase hecha de un item ABIERTO) -> no se marca.
    # Y las entradas del ledger (bajo ## Cerrados) tampoco se marcan.
    assert sc._cerrados_sin_colapsar(_PLAN_CON_LEDGER) == []


def test_cerrados_sin_colapsar_detecta_bloque_cerrado_arriba():
    # Encabezado cuyo TEXTO empieza por ✅ y está antes de ## Cerrados -> sin colapsar.
    assert sc._cerrados_sin_colapsar(_PLAN_CON_CERRADO_SUELTO) == ["[VIEJO] COMPLETA"]


def test_contar_cerrados_cuenta_las_entradas_del_ledger():
    assert sc._contar_cerrados(_PLAN_CON_LEDGER) == 2


def test_contar_cerrados_sin_seccion_es_cero():
    assert sc._contar_cerrados("# PLAN\n## Cola\n- [ ] tarea\n") == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_session_close_aviso.py -k "cerrados or contar_lineas or indice_cerrados" -v`
Expected: FAIL con `AttributeError: module 'scripts.session_close' has no attribute '_contar_lineas'` (y análogas).

- [ ] **Step 3: Write the implementation**

En `scripts/session_close.py`, tras la función `_plan_items_desfasados` (línea ~188) y antes de `_avisar_plan_desfasado`, añadir:

```python
# --- Higiene de PLAN.md / STATUS.md (presupuesto de tamaño + ledger) ---
_STATUS_MAX_LINEAS = 400
_CERRADOS_MAX = 30
_RE_HEADING_CERRADOS = re.compile(r"^#{2,}\s+.*Cerrados\b", re.IGNORECASE)


def _contar_lineas(texto: str) -> int:
    """Nº de líneas de un texto (0 si vacío)."""
    return len(texto.splitlines())


def _indice_cerrados(lineas: list[str]) -> int | None:
    """Índice de la línea del encabezado '## … Cerrados' (None si no existe)."""
    for i, ln in enumerate(lineas):
        if _RE_HEADING_CERRADOS.match(ln.strip()):
            return i
    return None


def _cerrados_sin_colapsar(plan_texto: str) -> list[str]:
    """Títulos de encabezados de ítems CERRADOS que no se han colapsado al ledger.

    Puro y testeable. Un ítem cerrado se escribe con el encabezado empezando por
    ✅ (`## ✅ [FOO] COMPLETA`). Un ✅ a mitad del encabezado marca una FASE hecha
    de un ítem abierto (`[SIGUIENTE-GOOGLE-MCP] F1 ✅ …`) y NO se marca. Solo se
    miran los encabezados ANTES de la sección '## … Cerrados' (el encabezado de la
    propia sección y las entradas del ledger quedan fuera del corte).
    """
    lineas = plan_texto.splitlines()
    corte = _indice_cerrados(lineas)
    limite = corte if corte is not None else len(lineas)
    titulos: list[str] = []
    for ln in lineas[:limite]:
        s = ln.strip()
        if not s.startswith("#"):
            continue
        texto = s.lstrip("#").strip()
        if texto.startswith("✅"):
            titulos.append(texto.lstrip("✅").strip())
    return titulos


def _contar_cerrados(plan_texto: str) -> int:
    """Nº de entradas del ledger '## … Cerrados' (líneas '- ' hasta el siguiente
    encabezado o el fin del fichero). 0 si no hay sección Cerrados."""
    lineas = plan_texto.splitlines()
    corte = _indice_cerrados(lineas)
    if corte is None:
        return 0
    n = 0
    for ln in lineas[corte + 1:]:
        s = ln.strip()
        if s.startswith("#"):
            break
        if s.startswith("- "):
            n += 1
    return n
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_session_close_aviso.py -k "cerrados or contar_lineas or indice_cerrados" -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/session_close.py tests/test_session_close_aviso.py
git commit -m "feat(session_close): detectores puros de higiene de PLAN.md (ledger + tamaño)"
```

---

### Task 2: Aviso de higiene en `session_close`

**Files:**
- Modify: `scripts/session_close.py` (añadir `_avisar_higiene_planificacion` tras `_avisar_plan_desfasado`; engancharla en `main()`)
- Test: `tests/test_session_close_aviso.py`

**Interfaces:**
- Consumes: `_contar_lineas`, `_cerrados_sin_colapsar`, `_contar_cerrados`, `ROOT`, `_STATUS_MAX_LINEAS`, `_CERRADOS_MAX` (Task 1).
- Produces: `_avisar_higiene_planificacion() -> None` (imprime; no bloquea).

- [ ] **Step 1: Write the failing tests**

Añadir a `tests/test_session_close_aviso.py`:

```python
# --- Aviso de higiene de planificacion (D3) ---

def _prep_higiene(monkeypatch, tmp_path, status_lineas, plan_texto):
    (tmp_path / "STATUS.md").write_text("x\n" * status_lineas, encoding="utf-8")
    (tmp_path / "PLAN.md").write_text(plan_texto, encoding="utf-8")
    monkeypatch.setattr(sc, "ROOT", tmp_path)


def test_higiene_avisa_status_grande(monkeypatch, capsys, tmp_path):
    _prep_higiene(monkeypatch, tmp_path, 500, "# PLAN\n## ✅ Cerrados\n")
    sc._avisar_higiene_planificacion()
    out = capsys.readouterr().out
    assert "[!]" in out and "STATUS.md" in out and "500" in out


def test_higiene_avisa_item_sin_colapsar(monkeypatch, capsys, tmp_path):
    _prep_higiene(monkeypatch, tmp_path, 10, _PLAN_CON_CERRADO_SUELTO)
    sc._avisar_higiene_planificacion()
    out = capsys.readouterr().out
    assert "[!]" in out and "[VIEJO] COMPLETA" in out


def test_higiene_avisa_ledger_lleno(monkeypatch, capsys, tmp_path):
    ledger = "# PLAN\n## ✅ Cerrados\n" + "".join(
        f"- ✅ **[I{i}]** x — PR #{i}\n" for i in range(31)
    )
    _prep_higiene(monkeypatch, tmp_path, 10, ledger)
    sc._avisar_higiene_planificacion()
    out = capsys.readouterr().out
    assert "[!]" in out and "31" in out and "area" in out.lower()


def test_higiene_limpia_no_alarma(monkeypatch, capsys, tmp_path):
    _prep_higiene(monkeypatch, tmp_path, 100, _PLAN_CON_LEDGER)
    sc._avisar_higiene_planificacion()
    out = capsys.readouterr().out
    assert "[!]" not in out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_session_close_aviso.py -k higiene -v`
Expected: FAIL con `AttributeError: … has no attribute '_avisar_higiene_planificacion'`.

- [ ] **Step 3: Write the implementation**

En `scripts/session_close.py`, tras `_avisar_plan_desfasado` (línea ~214), añadir:

```python
def _avisar_higiene_planificacion() -> None:
    """AVISO no bloqueante: higiene de STATUS.md y PLAN.md.

    (1) STATUS.md supera el presupuesto de tamaño -> rotar a docs/bitacora/.
    (2) PLAN.md tiene item(s) ✅ sin colapsar al ledger '## Cerrados'.
    (3) El ledger '## Cerrados' supera el tope -> agrupar por area.
    Solo lee ficheros del repo; sin git ni red. Cablea las reglas que la
    doctrina 2026-07-05 dejo como prosa y por eso se degradaron.
    """
    print("\n" + "-" * 40)
    print("Higiene de planificacion (STATUS.md / PLAN.md)")
    hay_aviso = False

    status = ROOT / "STATUS.md"
    if status.exists():
        n = _contar_lineas(status.read_text(encoding="utf-8"))
        if n > _STATUS_MAX_LINEAS:
            hay_aviso = True
            print(f"[!] STATUS.md: {n} lineas (> {_STATUS_MAX_LINEAS}). "
                  "Rota el historico de cierres a docs/bitacora/2026.md (fase C).")

    plan = ROOT / "PLAN.md"
    if plan.exists():
        texto = plan.read_text(encoding="utf-8")
        sin_colapsar = _cerrados_sin_colapsar(texto)
        if sin_colapsar:
            hay_aviso = True
            print(f"[!] PLAN.md: {len(sin_colapsar)} item(s) ✅ sin colapsar al "
                  "ledger '## Cerrados':")
            for titulo in sin_colapsar:
                print(f"  -> {titulo}")
        n_cerrados = _contar_cerrados(texto)
        if n_cerrados > _CERRADOS_MAX:
            hay_aviso = True
            print(f"[!] PLAN.md: '## Cerrados' tiene {n_cerrados} entradas "
                  f"(> {_CERRADOS_MAX}). Promueve el ledger a agrupacion por area.")

    if not hay_aviso:
        print("STATUS.md y PLAN.md dentro de presupuesto; sin ✅ sin colapsar.")
```

Y en `main()`, tras el bloque `try/except` de `_avisar_plan_desfasado` (línea ~264), añadir:

```python
    # Aviso de higiene de planificacion (modo AVISO, no bloquea).
    try:
        _avisar_higiene_planificacion()
    except Exception as e:  # el aviso nunca debe romper el cierre
        print(f"[aviso] no se pudo comprobar higiene de planificacion: {e}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_session_close_aviso.py -k higiene -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/session_close.py tests/test_session_close_aviso.py
git commit -m "feat(session_close): aviso de higiene de planificacion (E1)"
```

> Nota: tras este commit, el aviso marcará STATUS.md (502 > 400) en cada cierre. Es lo esperado: es el disparador de la fase C.

---

### Task 3: Cabecera de cola priorizada en `PLAN.md` (D1)

**Files:**
- Modify: `PLAN.md` (insertar la cabecera tras la introducción, antes del primer bloque de contenido; retirar el bloque vestigial "MÁXIMA PRIORIDAD — CERRADA")
- Modify: `STATUS.md` (el `[SIGUIENTE]` pasa a puntero)

**Interfaces:**
- Consumes: `_cerrados_sin_colapsar` NO aplica aquí; la verificación de D1 es visual/estructural.
- Produces: sección `## 🎯 Cola priorizada` con la convención "fila #1 = ahora".

- [ ] **Step 1: Releer PLAN.md en fresco**

Run: `git -C . pull --ff-only` (si aplica) y abrir `PLAN.md`. Enumerar los bloques `[SIGUIENTE-*]` ABIERTOS y su estado real (cruzar con la tabla de prioridad ya acordada).

- [ ] **Step 2: Insertar la cabecera de cola**

Tras el bloque introductorio de `PLAN.md` (la línea `Historial de commits: …` y su `---`), insertar:

```markdown
## 🎯 Cola priorizada  (orden = prioridad; fila #1 = lo que toca ahora)

| # | Ítem | Estado | Gate / disparador | Esf. |
|---|------|--------|-------------------|------|
| 1 | [B5 auto-derivar `--folder-id`](#siguiente-apertura-expediente) | en curso (otra sesión) | desbloqueado | medio |
| 2 | [MCP Drive-disco V1](#siguiente-mcp-drive-disco) | spec lista | mergear PR #48 | alto |
| 3 | [Split F2 sala de máquina](#siguiente-infra-post-valero) | pendiente | desbloqueado | medio |
| 4 | [Infra C — art. 156 LEC](#siguiente-infra-post-valero) | pendiente | desbloqueado (quick win) | bajo |
| 5 | [Infra B — expediente scratch](#siguiente-infra-post-valero) | pendiente | desbloqueado | medio |
| 6 | [MCP sudespacho F1](#siguiente-mcp-sudespacho) | spec lista | gates de despliegue | alto |
| 7 | [abrir-caso F3-judicial](#abrir-caso) | diferida | caso judicial real | alto |
| 8 | [Google MCP F4 (Calendar)](#siguiente-google-mcp) | diferida | disparador | medio |

> Detalle de cada ítem en su bloque `[SIGUIENTE-*]` más abajo. Backlog sin
> promover: `docs/MEJORAS_FUTURAS.md`. Ledger de cerrados: `## Cerrados` (final).

---
```

(Los anclas markdown `#siguiente-…` se derivan del texto del encabezado en minúsculas con guiones; ajustar a los reales de cada bloque tras insertarlos.)

- [ ] **Step 3: Retirar el bloque vestigial de máxima prioridad**

Borrar de `PLAN.md` el bloque `## ✅ MÁXIMA PRIORIDAD — CERRADA (…)` completo (afirma "No hay tarea de código en cola", ya falso: la cola es la tabla nueva). Su contenido histórico ya está en git.

- [ ] **Step 4: Convertir el `[SIGUIENTE]` de STATUS.md en puntero**

En `STATUS.md`, la sección `## Próximas tareas → ver PLAN.md` ya es un puntero; verificar que ningún bloque de estado vigente restate el "siguiente paso" como hecho autoritativo. (Los bloques de cierre históricos NO se tocan aquí; eso es fase C.) Añadir, si falta, una línea: `El siguiente paso vive en la **cola priorizada** de PLAN.md (fila #1).`

- [ ] **Step 5: Verificar y commitear**

Run: `python -c "import scripts.session_close as sc; print(sc._indice_cerrados(open('PLAN.md',encoding='utf-8').read().splitlines()) is not None or 'sin ledger aun (ok en Task 3)')"`
Expected: imprime `True` o el mensaje (el ledger se crea en Task 4; aquí basta con que la tabla exista).

```bash
git add PLAN.md STATUS.md
git commit -m "docs(plan): cabecera de cola priorizada + STATUS enlaza al siguiente"
```

---

### Task 4: Colapsar los bloques ✅ al ledger `## Cerrados` (D2)

**Files:**
- Modify: `PLAN.md` (añadir `## Cerrados` al final; colapsar los 14 bloques ✅ a una línea cada uno)

**Interfaces:**
- Consumes: `_cerrados_sin_colapsar` (Task 1) como verificación.
- Produces: sección `## ✅ Cerrados` (lista plana, reciente primero); cero encabezados ✅ fuera de ella.

- [ ] **Step 1: Añadir la sección Cerrados al final de PLAN.md**

```markdown
## ✅ Cerrados

> Ciclo de vida cerrado. Narrativa completa: `git log` + el spec/plan enlazado.
> Lista plana, reciente primero. Promover a agrupación por área cuando supere ~30
> entradas (lo avisa `session_close`).

```

- [ ] **Step 2: Colapsar cada bloque ✅ a una línea**

Por cada uno de los 14 bloques con encabezado ✅ (p. ej. `## ✅ [SIGUIENTE-SKILL-EXPEDIENTE-A-MD] …`, `### ✅ [BIBLIOTECA-CHECKOUT] …`, `### ✅ [SANEADO-PII-FASE-2] …`, `### ✅ [SIGUIENTE-CONTROLES-ANTIFUGA] …`, `### ✅ [CRITICO-PRESIGNED-DOWNLOAD-BUG] …`, `## ✅ [SIGUIENTE-EMAIL-APLANADO-ANIDADOS] …`, `## ✅ [INTAKE-WHATSAPP-FASE-A] …`, `## ✅ [ESTILO-DE-LA-CASA] …`, `## ✅ [SKILL-CONTESTACION-ART20-LAU] …`, `## ✅ [SIGUIENTE-EXPORT-ETIQUETA-EMAIL] …`, etc.): (1) borrar el bloque completo; (2) añadir una línea al principio de la lista de `## Cerrados` con la forma:

```markdown
- ✅ **[ETIQUETA]** título breve — PR #NN (hash) · [spec](docs/superpowers/specs/AAAA-MM-DD-...-design.md)
```

extrayendo etiqueta/PR/hash/spec del propio bloque. Reciente primero (los de fecha más alta arriba). Los `[SIGUIENTE-GOOGLE-MCP]`, `[abrir-caso]` y similares con fases MIXTAS (✅ a mitad de encabezado) **NO se colapsan**: siguen siendo ítems abiertos en la cola; si tienen una sub-fase ✅ como *encabezado* interno, convertirla a `- [x]` (sub-bullet) para que no dispare el detector.

- [ ] **Step 3: Verificar que no queda ✅ sin colapsar**

Run: `python -c "import scripts.session_close as sc; print(sc._cerrados_sin_colapsar(open('PLAN.md',encoding='utf-8').read()))"`
Expected: `[]`

Run: `python -c "import scripts.session_close as sc; t=open('PLAN.md',encoding='utf-8').read(); print('cerrados:', sc._contar_cerrados(t))"`
Expected: `cerrados: 14` (o el nº real de bloques colapsados).

- [ ] **Step 4: Commit**

```bash
git add PLAN.md
git commit -m "docs(plan): colapsar bloques ✅ al ledger '## Cerrados' (D2)"
```

---

### Task 5: Auditoría de `estado:` + fase C en backlog (D4)

**Files:**
- Modify: los 11 `docs/PLAN_*.md` (frontmatter `estado:`) + `docs/DESPLIEGUE_MCP_DRIVE_DISCO.md` + `docs/prompt_handoff_expedientes_seguros.md` (añadir frontmatter con `estado:`)
- Modify: `docs/INDICE.md` (columna de estado)
- Modify: `docs/MEJORAS_FUTURAS.md` (entrada de la fase C)
- Create: `tests/test_docs_gobernanza.py`

**Interfaces:**
- Consumes: nada.
- Produces: guard `test_estado_frontmatter_valido`.

- [ ] **Step 1: Auditar y corregir cada `estado:`**

Por cada uno de los 11 `docs/PLAN_*.md`: leer el fichero, cruzar con `PLAN.md` (cola/Cerrados), `STATUS.md`, `git log` y (si aplica) el código que lo cita; fijar `estado:` ∈ `{vigente, historico, aparcado, revisar}`. Punto de partida a verificar (no dar por bueno): `DESPLIEGUE_EV=vigente`, `INTAKE_CRM_COMPLETO=vigente`, `INTAKE_PROCURADORES_EMAIL=vigente`, `PRERELLENO_LLM_VIABILIDAD=vigente`, `SaRS1_anon_pipeline=vigente`, `SALA_LECTURA_01_PROCESADO=historico`, `SUBDIVISION_CIUDADES=historico`, `email_aplanado_anidados=historico`, `email_enlaces_drive=historico`, `BITACORA_CASOS=aparcado`, `MOTOR_DOCUMENTAL=aparcado`. Cualquier caso sin señal clara → `revisar` (Nikolai confirma).

- [ ] **Step 2: Estampar frontmatter en los 2 docs sueltos**

Añadir al principio de `docs/DESPLIEGUE_MCP_DRIVE_DISCO.md` y `docs/prompt_handoff_expedientes_seguros.md`:

```markdown
---
estado: <vigente|historico|aparcado|revisar>
dueño: Nikolai Tyukhay
fecha: 2026-07-18
---
```

(Para `prompt_handoff_expedientes_seguros.md` INDICE ya lo da como `historico`.)

- [ ] **Step 3: Actualizar INDICE.md**

Reflejar en las tablas de `docs/INDICE.md` los estados corregidos. Sin mover ficheros todavía (eso es Task 7).

- [ ] **Step 4: Anotar la fase C en el backlog**

Añadir a `docs/MEJORAS_FUTURAS.md` una entrada nueva (siguiente número libre):

```markdown
## NN. Rotación y saneado de STAT.md (fase C de gobernanza de planificación)

**Estado actual.** STATUS.md acumula ~125 bloques de cierre (>400 líneas) antes de
las secciones de estado. `session_close` ya avisa del tamaño (guardarraíl E1).

**Mejora propuesta.** Rotar el histórico de cierres a `docs/bitacora/2026.md`;
partir STATUS en "estado vigente" + log; terminar la migración prosa→puntero
(Arquitectura/taxonomía/estructura → enlaces a `core/config.py`/`ARQUITECTURA.md`,
Drifts #3/#4 de `GOBERNANZA_FUENTES_VERDAD.md`).

**Disparador de promoción.** El primer aviso de E1 por STATUS>400 (ya se cumple) o
tras aterrizar el arreglo de la cola. Spec de referencia:
`docs/superpowers/specs/2026-07-18-gobernanza-planificacion-design.md` §7.
```

- [ ] **Step 5: Guard de estado válido — test que falla**

Crear `tests/test_docs_gobernanza.py`:

```python
"""Guards de gobernanza de docs: frontmatter estado: valido en docs/*.md."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_ESTADOS = {"vigente", "historico", "aparcado", "revisar"}
_RE_ESTADO = re.compile(r"^estado:\s*(\S+)\s*$", re.MULTILINE)


def _docs_con_frontmatter():
    """docs/*.md de nivel superior que llevan frontmatter (--- al inicio)."""
    for p in sorted((ROOT / "docs").glob("*.md")):
        txt = p.read_text(encoding="utf-8")
        if txt.startswith("---"):
            yield p, txt


def test_estado_frontmatter_valido():
    malos = []
    for p, txt in _docs_con_frontmatter():
        m = _RE_ESTADO.search(txt)
        if not m or m.group(1) not in _ESTADOS:
            malos.append(p.name)
    assert not malos, f"docs con estado: ausente o invalido: {malos}"
```

- [ ] **Step 6: Run — falla si algún doc quedó sin estado válido**

Run: `python -m pytest tests/test_docs_gobernanza.py -v`
Expected: PASS si todos los `estado:` son válidos; si falla, corregir el fichero listado.

- [ ] **Step 7: Commit**

```bash
git add docs/PLAN_*.md docs/DESPLIEGUE_MCP_DRIVE_DISCO.md docs/prompt_handoff_expedientes_seguros.md docs/INDICE.md docs/MEJORAS_FUTURAS.md tests/test_docs_gobernanza.py
git commit -m "docs(gobernanza): auditar estado: de planes legacy + guard + backlog fase C"
```

---

### Task 6: Verificación completa de PR-A

- [ ] **Step 1: Suite verde**

Run: `python -m pytest -q --tb=short`
Expected: verde salvo los 5 fallos ambientales conocidos de `test_sudespacho_relations` (faltan `SUDESPACHO_*` en el worktree, = main).

- [ ] **Step 2: Simular el aviso de cierre (sin correr toda la suite)**

Run:
```bash
python -c "import scripts.session_close as sc; sc._avisar_higiene_planificacion()"
```
Expected: marca `[!] STATUS.md: … (> 400)` (esperado, dispara fase C) y **NO** marca ítems ✅ sin colapsar.

- [ ] **Step 3: Abrir PR-A**

```bash
git push -u origin <rama>
gh pr create --fill --base main
```
Expected: check `leak-scan` verde. PR-A listo para revisión.

---

## PR-B — Reubicar los planes legacy fuera de `docs/` raíz (D5)

> Entregable separado. Rebasar sobre `main` con PR-A ya mergeado (INDICE se toca en ambos).

### Task 7: Mover los 11 `docs/PLAN_*.md` a `docs/superpowers/plans/`

**Files:**
- Move: los 11 `docs/PLAN_*.md` → `docs/superpowers/plans/PLAN_*.md` (mismo nombre)
- Modify (refs en código/tests): `core/ciudades.py`, `core/casos/case_locator.py`, `scripts/migrate_to_city_structure.py`, `scripts/verify_city_layout.py`, `tests/test_config_ciudades.py` (→ `SUBDIVISION_CIUDADES`); `core/sync_sudespacho_legacy.py` (→ `INTAKE_CRM_COMPLETO`); `core/procurador_intake.py`, `core/procurador_review.py`, `core/procurador_runner.py` (→ `INTAKE_PROCURADORES_EMAIL`); `tests/test_anon_regresion_SaRS1.py` (→ `SaRS1`)
- Modify (refs en docs): `docs/INDICE.md`, `PLAN.md`, `STATUS.md`, `docs/bitacora/STATUS_cola_historica_pre_2026-07.md`, `docs/MEJORAS_FUTURAS.md`, `docs/MEJORA_CONTINUA_SKILLS.md`, `docs/ARQUITECTURA.md`, `docs/migracion_claude_code/CLAUDE.md`, y los specs/planes de superpowers que citen `PLAN_*` (ver Step 1)
- Create/Modify: `tests/test_docs_gobernanza.py` (añadir guard anti-referencia)

**Interfaces:**
- Consumes: nada.
- Produces: guard `test_sin_refs_a_docs_plan_legacy`.

- [ ] **Step 1: Inventario de referencias actuales**

Run: `git grep -n -E "docs/PLAN_[A-Za-z]" -- . ':!docs/superpowers/plans/2026-07-18-gobernanza-planificacion.md'`
Anotar cada ocurrencia. Estas son las rutas a reescribir de `docs/PLAN_X.md` → `docs/superpowers/plans/PLAN_X.md`.

- [ ] **Step 2: Mover los 11 ficheros con git**

```bash
git mv docs/PLAN_BITACORA_CASOS.md docs/superpowers/plans/PLAN_BITACORA_CASOS.md
git mv docs/PLAN_DESPLIEGUE_EV.md docs/superpowers/plans/PLAN_DESPLIEGUE_EV.md
git mv docs/PLAN_INTAKE_CRM_COMPLETO.md docs/superpowers/plans/PLAN_INTAKE_CRM_COMPLETO.md
git mv docs/PLAN_INTAKE_PROCURADORES_EMAIL.md docs/superpowers/plans/PLAN_INTAKE_PROCURADORES_EMAIL.md
git mv docs/PLAN_MOTOR_DOCUMENTAL.md docs/superpowers/plans/PLAN_MOTOR_DOCUMENTAL.md
git mv docs/PLAN_PRERELLENO_LLM_VIABILIDAD.md docs/superpowers/plans/PLAN_PRERELLENO_LLM_VIABILIDAD.md
git mv docs/PLAN_SALA_LECTURA_01_PROCESADO.md docs/superpowers/plans/PLAN_SALA_LECTURA_01_PROCESADO.md
git mv docs/PLAN_SUBDIVISION_CIUDADES.md docs/superpowers/plans/PLAN_SUBDIVISION_CIUDADES.md
git mv docs/PLAN_SaRS1_anon_pipeline.md docs/superpowers/plans/PLAN_SaRS1_anon_pipeline.md
git mv docs/PLAN_email_aplanado_anidados.md docs/superpowers/plans/PLAN_email_aplanado_anidados.md
git mv docs/PLAN_email_enlaces_drive.md docs/superpowers/plans/PLAN_email_enlaces_drive.md
```

- [ ] **Step 3: Reescribir todas las referencias**

Para cada ocurrencia del Step 1, sustituir `docs/PLAN_X.md` → `docs/superpowers/plans/PLAN_X.md` (y las citas relativas dentro de `docs/` que usen solo `PLAN_X.md`, ajustar a la ruta nueva). Incluye comentarios/docstrings de código (no cambian lógica) y prosa de docs.

- [ ] **Step 4: Guard anti-referencia — test que falla si queda una ruta vieja**

Añadir a `tests/test_docs_gobernanza.py`:

```python
def test_sin_refs_a_docs_plan_legacy():
    """Tras la reubicacion, ningun fichero trackeado debe citar docs/PLAN_*.md
    en la raiz de docs/ (ahora viven en docs/superpowers/plans/)."""
    import subprocess
    r = subprocess.run(
        ["git", "grep", "-l", "-E", r"docs/PLAN_[A-Za-z]"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    # git grep devuelve 1 (sin match) => vacio => OK.
    ofensores = [
        ln for ln in r.stdout.splitlines()
        if ln and "test_docs_gobernanza.py" not in ln
        and "docs/superpowers/plans/2026-07-18-gobernanza-planificacion.md" not in ln
    ]
    assert not ofensores, f"referencias a docs/PLAN_* sin actualizar: {ofensores}"
```

- [ ] **Step 5: Run — verificar guard + grep manual**

Run: `python -m pytest tests/test_docs_gobernanza.py -v`
Expected: PASS.

Run: `git grep -n -E "docs/PLAN_[A-Za-z]" -- . ':!tests/test_docs_gobernanza.py' ':!docs/superpowers/plans/2026-07-18-gobernanza-planificacion.md'`
Expected: sin salida (0 rutas colgando).

- [ ] **Step 6: Suite verde**

Run: `python -m pytest -q --tb=short`
Expected: verde salvo los 5 fallos ambientales conocidos de `test_sudespacho_relations`.

- [ ] **Step 7: Commit y PR-B**

```bash
git add -- core/ scripts/ tests/ docs/ PLAN.md STATUS.md
git commit -m "docs(gobernanza): reubicar planes legacy a superpowers/plans + guard de refs (D5)"
git push -u origin <rama-pr-b>
gh pr create --fill --base main
```
Expected: `leak-scan` verde.

---

## Self-Review

**Spec coverage:**
- D1 (cola) → Task 3. D2 (Cerrados) → Task 4. D3 (guardarraíl E1) → Tasks 1-2. D4 (auditoría + INDICE + fase C backlog) → Task 5. D5 (reubicación + refs) → Task 7. C registrada → Task 5 Step 4. Secuenciación 2 PR → PR-A (Tasks 1-6) / PR-B (Task 7). Cubierto.

**Placeholder scan:** sin TBD/TODO. Todo paso con código muestra el código; los pasos de edición de Markdown especifican contenido exacto y comando de verificación.

**Type consistency:** `_cerrados_sin_colapsar` / `_contar_cerrados` / `_indice_cerrados` / `_contar_lineas` / `_avisar_higiene_planificacion` usados con el mismo nombre y firma en Tasks 1, 2, 3, 4 y 6. Constantes `_STATUS_MAX_LINEAS`/`_CERRADOS_MAX` consistentes. El detector distingue ✅-al-inicio-de-encabezado (cerrado) de ✅-a-mitad (fase de ítem abierto) — cubierto por `test_cerrados_sin_colapsar_ignora_item_abierto_con_fase_hecha`.
