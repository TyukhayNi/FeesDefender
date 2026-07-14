# Mejoras a `viabilidad-prerelleno` — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminar el `PermissionError` latente del render (con test) e incorporar seis mejoras metodológicas en su hogar correcto (código / `SKILL.md` / `references/`), más una propagación mínima (C6 en `triaje-viabilidad`).

**Architecture:** El fix de escritura vive en el script `render_informe.py` (copyfile + makedirs + guardado con fallback, unidad aislada `save_with_fallback` testeable). Las reglas metodológicas van a `SKILL.md` (ediciones tersas de líneas existentes) y a `references/hitos_derivacion.md` (carga bajo demanda). Dos PR: PR 1 = todo `viabilidad-prerelleno`; PR 2 = `triaje-viabilidad` (C6) en rama aparte.

**Tech Stack:** Python 3 + openpyxl; pytest; skills en `.claude/skills/`; empaquetado con `scripts/package_skill.py`. Entorno Windows + PowerShell; rama+PR con `leak-scan` (nunca push directo a `main`).

**Contexto de repo:** ya estamos en la rama `claude/viabilidad-prerelleno-review-5cb695` (worktree aislado). El spec de referencia es `docs/superpowers/specs/2026-07-14-viabilidad-prerelleno-mejoras-design.md`.

---

## PR 1 — `viabilidad-prerelleno`

### Task 1: Fix de escritura del render (TDD)

**Files:**
- Create: `tests/test_render_informe_viabilidad.py`
- Modify: `.claude/skills/viabilidad-prerelleno/scripts/render_informe.py` (líneas 106-107, 205; nueva función tras `set_cell`)

- [ ] **Step 1: Escribe el test que falla**

Crea `tests/test_render_informe_viabilidad.py` con exactamente:

```python
# -*- coding: utf-8 -*-
"""Tests del render del Informe de Viabilidad (skill viabilidad-prerelleno)."""
import importlib.util
import json
import os
import pathlib
import shutil
import stat
import sys

import openpyxl

REPO = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO / ".claude/skills/viabilidad-prerelleno/scripts/render_informe.py"
PLANTILLA = REPO / ".claude/skills/viabilidad-prerelleno/assets/plantilla_informe_viabilidad.xlsx"


def _load():
    spec = importlib.util.spec_from_file_location("render_informe", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


render_informe = _load()


def _datos(tmp_path):
    p = tmp_path / "datos.json"
    p.write_text(json.dumps({"case_id": "TEST"}), encoding="utf-8")
    return p


def _run(monkeypatch, argv):
    monkeypatch.setattr(sys, "argv", ["render_informe.py", *argv])
    render_informe.main()


def test_render_con_plantilla_read_only(tmp_path, monkeypatch):
    ro = tmp_path / "plantilla_ro.xlsx"
    shutil.copyfile(PLANTILLA, ro)
    os.chmod(ro, stat.S_IREAD)  # solo lectura: reproduce el asset empaquetado
    salida = tmp_path / "out.xlsx"
    try:
        _run(monkeypatch, [str(_datos(tmp_path)), "--salida", str(salida), "--plantilla", str(ro)])
        assert salida.exists()
        openpyxl.load_workbook(salida)  # es un .xlsx válido
    finally:
        os.chmod(ro, stat.S_IWRITE)  # que tmp_path pueda limpiarlo en Windows


def test_render_crea_directorio_salida(tmp_path, monkeypatch):
    salida = tmp_path / "nueva" / "sub" / "out.xlsx"
    _run(monkeypatch, [str(_datos(tmp_path)), "--salida", str(salida)])
    assert salida.exists()


def test_save_with_fallback(tmp_path, monkeypatch, capsys):
    salida = tmp_path / "destino" / "out.xlsx"

    class FakeWB:
        def __init__(self):
            self.saved = []

        def save(self, path):
            if str(path) == str(salida):
                raise OSError("destino no escribible")
            self.saved.append(str(path))

    monkeypatch.chdir(tmp_path)
    wb = FakeWB()
    resultado = render_informe.save_with_fallback(wb, str(salida))
    assert resultado != str(salida)
    assert os.path.dirname(os.path.abspath(resultado)) == str(tmp_path)
    assert wb.saved == [resultado]
    assert "No pude escribir" in capsys.readouterr().err
```

- [ ] **Step 2: Corre los tests y verifica que fallan**

Run: `python -m pytest tests/test_render_informe_viabilidad.py -q`
Expected: FAIL — `test_save_with_fallback` con `AttributeError: module 'render_informe' has no attribute 'save_with_fallback'`; `test_render_crea_directorio_salida` con `FileNotFoundError`; `test_render_con_plantilla_read_only` con `PermissionError` en `wb.save`.

- [ ] **Step 3: Añade `save_with_fallback` tras `set_cell`**

En `render_informe.py`, inserta esta función justo después del bloque de `set_cell` (tras la línea 73, antes de `build_id_row_map`):

```python
def save_with_fallback(wb, salida):
    """Guarda el workbook; si el destino no es escribible (p. ej. Drive no
    montado o permisos), cae a un fichero en el directorio de trabajo y avisa."""
    try:
        wb.save(salida)
        return salida
    except OSError as e:
        fallback = os.path.join(os.getcwd(), os.path.basename(salida))
        if os.path.abspath(fallback) == os.path.abspath(salida):
            raise
        wb.save(fallback)
        warn(f"No pude escribir en '{salida}' ({e}). Lo dejé en '{fallback}'. "
             f"Cópialo a 02_Analisis (o deposítalo con el conector expedientes-xl).")
        return fallback
```

- [ ] **Step 4: Cambia el copy por copyfile + makedirs**

En `render_informe.py`, reemplaza la línea 106:

```python
    shutil.copy(args.plantilla, salida)
```

por:

```python
    os.makedirs(os.path.dirname(os.path.abspath(salida)), exist_ok=True)
    shutil.copyfile(args.plantilla, salida)
```

- [ ] **Step 5: Enruta el guardado final por el fallback**

En `render_informe.py`, reemplaza la línea 205:

```python
    wb.save(salida)
```

por:

```python
    salida = save_with_fallback(wb, salida)
```

- [ ] **Step 6: Corre los tests y verifica que pasan**

Run: `python -m pytest tests/test_render_informe_viabilidad.py -q`
Expected: PASS (3 passed).

- [ ] **Step 7: Corre la suite completa**

Run: `python -m pytest -q --tb=no`
Expected: verde (mismos que antes + 3 nuevos). Cualquier fallo ajeno se explica en `STATUS.md`, no se ignora.

- [ ] **Step 8: Commit**

```bash
git add tests/test_render_informe_viabilidad.py ".claude/skills/viabilidad-prerelleno/scripts/render_informe.py"
git commit -m "fix(viabilidad-prerelleno): render robusto a plantilla read-only y destino no escribible (copyfile+makedirs+fallback) con tests"
```

---

### Task 2: Texto de `SKILL.md` (B1, B2, B3, B4, B6)

**Files:**
- Modify: `.claude/skills/viabilidad-prerelleno/SKILL.md`

Lee el fichero completo antes de editar. Aplica las cinco ediciones siguientes.

- [ ] **Step 1: B4 — corrige la cláusula de §3 (reconcilia línea 69)**

Reemplaza este bloque exacto:

```
- Si ningún documento la resuelve (o es `clase_fuente: testifical`) → deja respuesta vacía y `¿PENDIENTE?` = `sí`. Esa fila es guion de entrevista.
- `clase_fuente` es solo un **default**: una pregunta "documental" cuyo documento no aparece también pasa a `pendiente`. Nunca rellenes por inferencia.
```

por:

```
- Si ningún documento la resuelve → deja respuesta vacía y `¿PENDIENTE?` = `sí`. Esa fila es guion de entrevista.
- `clase_fuente` es solo un **default**, no una prohibición: una pregunta "documental" cuyo documento no aparece pasa a `pendiente`; y a la inversa, una pregunta marcada `testifical` que un documento (email, WhatsApp, transcripción) resuelve con cita literal se **rellena igual que una documental**, sin esperar a la entrevista. La etiqueta solo decide el comportamiento cuando NINGÚN documento resuelve la pregunta. Nunca rellenes por inferencia.
```

- [ ] **Step 2: B3 + B6 — orden de lectura y conciliación en el paso 1**

Reemplaza este bloque exacto:

```
### 1. Localiza el expediente y lee `00_Input/`
Subcarpetas: `01_Drive EV`, `02_Whatsapp`, `03_Email`, `04_Manual`, `05_CRM`. Whatsapp/Email se subdividen por consultor (`00_Consultor propietario`, `01_Consultor buscador`, `02_Grupo/Dirección`, `03_Otros`). Lee todo lo que haya. No leas `06_Entrevistas/` ni `90_Notas personales/`.
```

por:

```
### 1. Localiza el expediente y lee `00_Input/`
Subcarpetas: `01_Drive EV`, `02_Whatsapp`, `03_Email`, `04_Manual`, `05_CRM`. Whatsapp/Email se subdividen por consultor (`00_Consultor propietario`, `01_Consultor buscador`, `02_Grupo/Dirección`, `03_Otros`). Lee todo lo que haya. No leas `06_Entrevistas/` ni `90_Notas personales/`.

**Orden de lectura (aceleración, no cita).** Si existe `01_Procesado/02_Sala de máquina/`, lee primero los espejos Markdown de `03_MD` (texto plano, rápido) para localizar y skimear; si el espejo no resuelve la pregunta, aparece vacío o su cabecera marca `ocr_quality` dudoso, consulta el PDF buscable de `01_OCR`. **Ancla siempre la CITA al documento original** (el espejo conserva el nombre del fichero fuente): baja al original de `00_Input` para verbatim delicado, firmas manuscritas, imágenes o autenticidad. Si NO existe la sala de máquina, lee `00_Input` directo.

**Conciliación con lo previo.** Antes de derivar hitos, comprueba si ya existe un informe de viabilidad previo (de E&V, de una entrevista anterior o una versión anterior del propio `.xlsx`-bitácora; el "informe existente" del paso 2 ayuda a localizarlo). Si existe, compáralo con lo que halles documentalmente y vuelca a `AVISOS LLM` cualquier discrepancia de cifras, fechas o puntuaciones — no la ignores ni la sobrescribas en silencio.
```

- [ ] **Step 3: B2 — nota de entrega en el paso 7**

Reemplaza este bloque exacto:

```
El script **parte de `assets/plantilla_informe_viabilidad.xlsx`** (formato, fórmulas, semáforo, validaciones y protección ya incorporados), solo escribe valores, deja VIABILIDAD y el recuadro en blanco, y **se niega a sobrescribir** un fichero existente. Construir el formato a mano rompería el semáforo y la protección; por eso siempre se parte de la plantilla.
```

por:

```
El script **parte de `assets/plantilla_informe_viabilidad.xlsx`** (formato, fórmulas, semáforo, validaciones y protección ya incorporados), solo escribe valores, deja VIABILIDAD y el recuadro en blanco, y **se niega a sobrescribir** un fichero existente. Construir el formato a mano rompería el semáforo y la protección; por eso siempre se parte de la plantilla.

> **Entrega cuando el expediente no es alcanzable por shell.** El script escribe en la ruta `--salida`; si esa ruta vive en una unidad no montada (Drive de Google en la nube) y la escritura falla, el propio script deja el `.xlsx` en el directorio local de trabajo y avisa de la ruta (cópialo a `02_Analisis`). Cuando el conector `expedientes-xl` esté disponible, deposita el binario con `write_file_base64`/`copy_path` (no con el MCP `expedientes`, que es solo-texto). No asumas acceso de shell al expediente.
```

- [ ] **Step 4: B1 — nota del fix en "Ficheros de la skill"**

Reemplaza esta línea exacta:

```
- `scripts/render_informe.py` — render del .xlsx desde el JSON (salida paralela, no sobrescribe).
```

por:

```
- `scripts/render_informe.py` — render del .xlsx desde el JSON (salida paralela, no sobrescribe). Usa `copyfile` (no `copy`) para no heredar el permiso de la plantilla, que puede venir en solo lectura en el entorno empaquetado; si el destino no es escribible, cae a un fichero local y avisa de la ruta. No hay que "arreglar" el permiso del asset.
```

- [ ] **Step 5: Verifica que no quedan contradicciones**

Run: `python - <<'PY'
import pathlib
t = pathlib.Path(".claude/skills/viabilidad-prerelleno/SKILL.md").read_text(encoding="utf-8")
assert "o es `clase_fuente: testifical`) → deja" not in t, "queda la cláusula absoluta vieja"
assert "Orden de lectura (aceleración, no cita)" in t
assert "Conciliación con lo previo" in t
assert "no asumas acceso de shell" in t.lower() or "No asumas acceso de shell" in t
assert "copyfile" in t
print("OK")
PY`
Expected: `OK`.

- [ ] **Step 6: Commit**

```bash
git add ".claude/skills/viabilidad-prerelleno/SKILL.md"
git commit -m "docs(viabilidad-prerelleno): orden de lectura MD->OCR->crudo (cita al original), precedencia documental/testifical, conciliacion previa y notas de entrega/permisos"
```

---

### Task 3: Texto de `references/hitos_derivacion.md` (B5)

**Files:**
- Modify: `.claude/skills/viabilidad-prerelleno/references/hitos_derivacion.md`

Lee el fichero completo antes de editar.

- [ ] **Step 1: B5 — precedencia regla específica vs. general (sentido correcto)**

Reemplaza esta línea exacta (última viñeta de "Reglas de oro del scoring"):

```
- Las observaciones por hito **ya no van en INFORMACION**: el rastro `[doc: fichero] "cita" (confianza)` vive en `PREGUNTAS` (col. CITA/FUENTE) y las banderas en `AVISOS LLM`.
```

por:

```
- Las observaciones por hito **ya no van en INFORMACION**: el rastro `[doc: fichero] "cita" (confianza)` vive en `PREGUNTAS` (col. CITA/FUENTE) y las banderas en `AVISOS LLM`.
- **Precedencia regla específica vs. general.** El cierre `0` de un hito concreto (p. ej. HOJA DE VISITA: "si no, 0") solo aplica **cuando consta que la acción se intentó o el documento existe** (aquí: que hubo visita). Si no consta rastro alguno, sigue rigiendo la regla general: `pendiente` (vacío), nunca `0` por inferencia. La regla del hito nunca convierte la ausencia total de documento en `0`.
```

- [ ] **Step 2: Verifica**

Run: `python - <<'PY'
import pathlib
t = pathlib.Path(".claude/skills/viabilidad-prerelleno/references/hitos_derivacion.md").read_text(encoding="utf-8")
assert "Precedencia regla específica vs. general" in t
assert "nunca convierte la ausencia total de documento en `0`" in t
print("OK")
PY`
Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
git add ".claude/skills/viabilidad-prerelleno/references/hitos_derivacion.md"
git commit -m "docs(viabilidad-prerelleno): aclara precedencia de cierre de hito sin invertir el salvaguarda conservador (B5)"
```

---

### Task 4: Empaquetado, gobernanza y PR 1

**Files:**
- Modify: `PLAN.md`, `docs/MEJORAS_FUTURAS.md`
- Genera: el `.skill` de `viabilidad-prerelleno` (artefacto, no se commitea salvo convención del repo)

- [ ] **Step 1: Empaqueta la skill**

Run: `python scripts/package_skill.py viabilidad-prerelleno`
Expected: genera el `.skill` sin error. (La ejecución sigue en el servidor: tras mergear, re-importar el `.skill` en Cowork — anótalo, no es paso de código.)

- [ ] **Step 2: Backlog — añade las entradas diferidas**

Lee `docs/MEJORAS_FUTURAS.md` y añade, bajo la sección de backlog que corresponda, estas entradas (con la etiqueta de "promover solo por necesidad demostrada"):

```
- **[cross-skill] Entrega sin-shell (C2) en más skills** — replicar la nota de `viabilidad-prerelleno` (paso 7) en `triaje-viabilidad`, `preparacion-audiencia-previa` y demás skills que escriben `.docx`/`.xlsx` de vuelta al expediente. Promover cuando un caso real falle por Drive no montado en esa skill.
- **[cross-skill] Conciliación con lo previo (C6) en escritos-judiciales y organizar-sala-lectura** — sub-paso "revisa qué existe antes de generar/sobrescribir". Promover por caso real.
- **[cross-skill] Cascada MD->OCR->crudo (C3) / precedencia documental-testifical (C4) fuera de viabilidad** — NO centralizar en `verificacion-anclada-fuente` (mala altitud, tensiona con su Regla 9, sin herencia automática). Añadir localmente y con guarda "si existe sala de máquina" solo donde un caso lo pida.
- **[bundled] Bug de permisos latente en la skill `docx`** — `scripts/comment.py:236,254,273,282` hace `shutil.copy(TEMPLATE_DIR/*.xml, dest)` + escritura posterior; mismo `PermissionError` si esos XML vienen read-only. Skill de terceros; fix defensivo (`copyfile`) solo si se vendoriza.
```

- [ ] **Step 3: PLAN.md — marca el ítem**

Lee `PLAN.md` y añade en la cola/estado una línea que refleje el trabajo de PR 1 (mejoras a `viabilidad-prerelleno` tras revisión BaRS8), con referencia al spec `docs/superpowers/specs/2026-07-14-viabilidad-prerelleno-mejoras-design.md`. Sigue el formato existente del fichero.

- [ ] **Step 4: Commit gobernanza**

```bash
git add PLAN.md docs/MEJORAS_FUTURAS.md
git commit -m "docs(gobernanza): registra mejoras viabilidad-prerelleno (PR1) y difiere cross-skill C2/C3/C4/C6 + bug latente docx al backlog"
```

- [ ] **Step 5: Push y PR 1**

```bash
git push -u origin claude/viabilidad-prerelleno-review-5cb695
gh pr create --base main --title "Mejoras a viabilidad-prerelleno (fricción BaRS8): fix de render + metodología" --body "Ver docs/superpowers/specs/2026-07-14-viabilidad-prerelleno-mejoras-design.md. Fix de escritura del render con tests; orden de lectura MD->OCR->crudo (cita al original); precedencia documental/testifical; conciliación previa; notas de entrega/permisos. Cross-skill diferido al backlog salvo C6-en-triaje (PR aparte)."
```
Expected: el check `leak-scan` debe pasar antes de poder mergear. No se hace push directo a `main`.

---

## PR 2 — `triaje-viabilidad` (C6, rama aparte)

### Task 5: Conciliación con lo previo en triaje

**Files:**
- Modify: `.claude/skills/triaje-viabilidad/SKILL.md`

- [ ] **Step 1: Crea la rama (tras mergear PR 1, o desde `main` al día)**

```bash
git fetch origin
git switch -c claude/triaje-conciliacion-c6 origin/main
```

- [ ] **Step 2: Añade la nota de conciliación en la sección "Entrada"**

Lee `.claude/skills/triaje-viabilidad/SKILL.md`. Reemplaza esta línea exacta (final de la sección "Entrada"):

```
`organizar-sala-lectura` antes.
```

por:

```
`organizar-sala-lectura` antes.

**Conciliación con lo previo.** Si ya existe un triaje o informe de viabilidad anterior del caso, cotéjalo: si tu semáforo difiere del previo, dilo explícitamente en el veredicto y señala la discrepancia (cifras, factor, fecha) — no la sobrescribas en silencio.
```

- [ ] **Step 3: Verifica**

Run: `python - <<'PY'
import pathlib
t = pathlib.Path(".claude/skills/triaje-viabilidad/SKILL.md").read_text(encoding="utf-8")
assert "Conciliación con lo previo" in t
print("OK")
PY`
Expected: `OK`.

- [ ] **Step 4: Empaqueta**

Run: `python scripts/package_skill.py triaje-viabilidad`
Expected: genera el `.skill` sin error.

- [ ] **Step 5: Commit, push y PR 2**

```bash
git add ".claude/skills/triaje-viabilidad/SKILL.md"
git commit -m "docs(triaje-viabilidad): conciliacion con triaje/informe previo antes del veredicto (C6)"
git push -u origin claude/triaje-conciliacion-c6
gh pr create --base main --title "triaje-viabilidad: conciliación con lo previo (C6)" --body "Propagación mínima demostrada de C6. Ver docs/superpowers/specs/2026-07-14-viabilidad-prerelleno-mejoras-design.md."
```
Expected: `leak-scan` verde para poder mergear.

---

## Notas de ejecución

- **Encoding:** todos los ficheros UTF-8 sin BOM. Las ediciones vía herramienta Edit lo respetan; no uses `Add-Content`/`Get-Content -Raw` sin `-Encoding UTF8`.
- **Commits acotados:** `git add` solo de los ficheros de cada task; nunca `git add -A` (working tree compartido entre sesiones).
- **Re-importar en Cowork:** tras mergear cada PR, re-importar el `.skill` correspondiente (paso operativo, fuera del repo).
- **No tocar** `references/cuestionario_viabilidad.yaml` (GENERADO); B4 vive en `SKILL.md`.
