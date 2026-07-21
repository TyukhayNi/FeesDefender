# Robustez y velocidad de `organizar-sala-lectura` — Plan de implementación (TDD)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** convertir en chequeos deterministas (código + exit codes) las 8 palancas de prioridad ALTA del backlog `2026-07-21-robustez-velocidad-sala-lectura.md`, para que la skill deje de delegar en el juicio del agente cosas que caben en un chequeo de 1 segundo, no permita "arreglar" un verify fallido editando datos generados, y genere índices por script en vez de a mano.

**Architecture:** helpers Python **self-contained** (cero `import core.*`, corren en Cowork igual que `manifiesto_a_catalogo.py`) bajo `.claude/skills/organizar-sala-lectura/scripts/`, invocados por la skill como pasos deterministas; más ediciones de prosa en `SKILL.md`/frontmatter/`CHANGELOG.md`. Un único cambio en `core/` (dos campos opcionales en `CatalogEntry`) para que el catálogo YAML pueda llevar la categoría. Un test de sincronía frontmatter↔CHANGELOG que evita el drift de versión.

**Tech Stack:** Python 3.11+ (stdlib; `yaml` solo en `manifiesto_a_catalogo.py`, que ya lo usa), `pytest`, sin dependencias nuevas.

## Global Constraints

- **Self-contained:** cero `import core.*` en los scripts bajo `.claude/skills/organizar-sala-lectura/scripts/` (deben correr en Cowork sin el repo Python). El parser compartido nuevo es **stdlib puro** (sin `yaml`).
- **Determinista e idempotente:** mismo input → mismo output, siempre. Ningún `Date.now()`/aleatoriedad en la lógica.
- **No destructivo:** ningún helper mueve/borra el crudo ni la sala; `verificar()` **solo detecta, nunca arregla**.
- **Test anti-drift obligatorio** para cualquier constante duplicada de `core/` (patrón ya establecido: `test_categorias_sin_drift`, `test_campos_coinciden_con_CatalogEntry`).
- **`main` protegida:** el trabajo va en rama + PR (nunca commit directo); el PR debe pasar `leak-scan`. CI **no** corre pytest → correr la suite **en local** antes de mergear (`python -m pytest -q`), sobre todo por los guards de docs.
- **Conteo de pytest SIEMPRE por `--junit-xml`** en este Windows (el resumen por tubería no se captura fiable). Para confirmar RED/GREEN de un test concreto, `-v` de ese test basta; para el conteo total, `--junit-xml`.
- **Entorno:** Windows + PowerShell; venv en la **raíz compartida** `C:\Users\tnm33\Dev\FeesDefender\.venv` (este worktree no tiene `.venv` propio). Ejecutar con `& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" -m pytest ...` **desde el worktree**. UTF-8 sin BOM en todo fichero.
- **NO repetir lo ya cerrado (PR #114, `main` `117b7c1`):** el reconocimiento de `parent_id` como carpeta de bundle en `verificar()`, el `POST` de `_rc_activo()`, la detección de `fecha 0000-00-00` contra cobertura y el cruce por `parent_sha256` YA están en el código — estas tareas **añaden encima**, no las rehacen.
- **Versión:** este trabajo estrena la **1.11** de la skill. El frontmatter y la primera entrada del `CHANGELOG.md` deben quedar en `1.11` y un test lo verifica (Task 10). Tras editar, re-empaquetar con `scripts/package_skill.py`; el re-import del `.skill` en Cowork queda como paso manual fuera de este plan.

---

### Task 1: Parser compartido del `_MANIFIESTO.md` (stdlib)

**Por qué:** los ítems 7 (CLI de verify) y 8 (índices por script) necesitan parsear el `_MANIFIESTO.md`; hoy solo `manifiesto_a_catalogo._parse_filas` lo hace, y arrastra `yaml`. Un parser stdlib compartido evita que el mismo agente que clasifica ensamble a mano el parseo que debe verificarlo, y hace el parseo robusto a columnas añadidas (Task 2).

**Files:**
- Create: `.claude/skills/organizar-sala-lectura/scripts/manifiesto_parser.py`
- Modify: `.claude/skills/organizar-sala-lectura/scripts/manifiesto_a_catalogo.py` (usar el parser; retirar `_parse_filas`/`_COLS` locales)
- Test: `tests/test_manifiesto_parser.py`

**Interfaces:**
- Produces: `manifiesto_parser.parse_manifiesto(texto: str) -> list[dict]` — una fila-dict por fila de datos; claves tomadas de la cabecera de la tabla, o de `manifiesto_parser.COLS_CANON` (7 columnas) si no hay cabecera.
- Produces: `manifiesto_parser.COLS_CANON: list[str]` = `["sha256","ruta_original","nombre_canonico","tipo","fecha","parte","parent_id"]`.
- Consumes (Task 3, 5): `parse_manifiesto` por `indices_desde_manifiesto.py` y `verificar_sala.py`.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_manifiesto_parser.py
from importlib import import_module
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / ".claude/skills/organizar-sala-lectura/scripts"))
mp = import_module("manifiesto_parser")

_MANIF_7COL = """<!-- GENERADO — NO EDITAR A MANO -->
| sha256 | ruta_original | nombre_canonico | tipo | fecha | parte | parent_id |
|---|---|---|---|---|---|---|
| aaaa | 01_Drive EV/Catastro.pdf | 2024-04-26_catastro.pdf | 08. PENDIENTE DE CLASIFICAR | 2024-04-26 | propietario |  |
| bbbb | 04_Manual/req.pdf | 2025-07-22_requerimiento.pdf | 07. RECLAMACIONES | 2025-07-22 | propietario |  |
"""

_MANIF_9COL = """<!-- GENERADO — NO EDITAR A MANO -->
| sha256 | ruta_original | nombre_canonico | tipo | fecha | parte | parent_id | categoria | subcategoria_crm |
|---|---|---|---|---|---|---|---|---|
| aaaa | sudespacho_1/civil/x.pdf | 2025-01-01_x.pdf | pdf | 2025-01-01 | propietario |  | 07. RECLAMACIONES | civil |
"""


def test_parsea_7_columnas_por_cabecera():
    filas = mp.parse_manifiesto(_MANIF_7COL)
    assert len(filas) == 2
    assert filas[0]["sha256"] == "aaaa"
    assert filas[0]["nombre_canonico"] == "2024-04-26_catastro.pdf"
    assert filas[0]["parent_id"] == ""


def test_parsea_columnas_extra_por_cabecera():
    filas = mp.parse_manifiesto(_MANIF_9COL)
    assert len(filas) == 1
    assert filas[0]["categoria"] == "07. RECLAMACIONES"
    assert filas[0]["subcategoria_crm"] == "civil"


def test_salta_cabecera_y_separador():
    filas = mp.parse_manifiesto(_MANIF_7COL)
    assert all(f["sha256"] not in ("sha256", "---") for f in filas)


def test_sin_cabecera_usa_cols_canon():
    texto = "| ccc | a/b.pdf | 2025-05-05_b.pdf | pdf | 2025-05-05 | comprador |  |"
    filas = mp.parse_manifiesto(texto)
    assert filas[0]["ruta_original"] == "a/b.pdf"
    assert list(filas[0].keys()) == mp.COLS_CANON
```

- [ ] **Step 2: Confirmar que falla**

Run: `& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" -m pytest tests/test_manifiesto_parser.py -v`
Expected: `ModuleNotFoundError: No module named 'manifiesto_parser'`.

- [ ] **Step 3: Crear `manifiesto_parser.py`**

```python
# .claude/skills/organizar-sala-lectura/scripts/manifiesto_parser.py
"""Parser compartido de la tabla del `_MANIFIESTO.md` — stdlib puro (sin `core/`
ni `yaml`). Lo consumen `manifiesto_a_catalogo.py`, `verificar_sala.py` e
`indices_desde_manifiesto.py`, para que las tres herramientas lean la MISMA
tabla igual (backlog robustez-velocidad, ítems 7 y 8): el agente que clasifica
no debe además ensamblar a mano el parseo que lo verifica.

Parseo por CABECERA: los nombres de columna se toman de la fila de cabecera del
propio manifiesto, así que añadir columnas (p. ej. `categoria`,
`subcategoria_crm`) no rompe manifiestos viejos de 7 columnas. Sin cabecera
reconocible, se asume el orden canónico de 7 columnas.
"""
from __future__ import annotations

COLS_CANON = [
    "sha256", "ruta_original", "nombre_canonico", "tipo", "fecha", "parte", "parent_id",
]


def _es_separador(celdas: list[str]) -> bool:
    return bool(celdas) and all(c and set(c) <= {"-", ":"} for c in celdas)


def parse_manifiesto(texto: str) -> list[dict]:
    """Una fila-dict por fila de datos. Claves de la cabecera (o `COLS_CANON`).
    Filas con nº de celdas != nº de columnas se saltan (tolerancia heredada; el
    endurecimiento estricto es el ítem 12, fuera de alcance)."""
    cols: list[str] | None = None
    filas: list[dict] = []
    for linea in texto.splitlines():
        s = linea.strip()
        if not s.startswith("|"):
            continue
        celdas = [c.strip() for c in s.strip("|").split("|")]
        if _es_separador(celdas):
            continue
        if celdas and celdas[0] == "sha256":
            cols = celdas
            continue
        if cols is None:
            cols = COLS_CANON
        if len(celdas) != len(cols):
            continue
        filas.append(dict(zip(cols, celdas)))
    return filas
```

- [ ] **Step 4: Refactorizar `manifiesto_a_catalogo.py` para usar el parser**

En `manifiesto_a_catalogo.py`: retirar `_COLS` y `_parse_filas`; importar el parser sibling (con guard de sys.path por si se carga con un loader que no ponga el dir de scripts en el path — p. ej. `spec_from_file_location` en `test_manifiesto_a_catalogo`); usar `parse_manifiesto` en `derivar`.

Sustituir el bloque de imports/constantes de cabecera (líneas ~7-30) por:

```python
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

# Import del parser sibling robusto al loader: si se carga vía
# spec_from_file_location (test) el dir de scripts no está en sys.path.
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
import manifiesto_parser  # noqa: E402

# Duplica (self-contained, sin `core/`) el contrato único core.intake_lotes.fuente_de
# (spec §8, MEJORAS #54 T11). El test anti-drift `test_fuente_skill_sin_drift_con_core`
# compara `_fuente` contra `fuente_de` — mantener ambos en sincronía a mano.
_PATRON_LOTE = re.compile(r"^(\d{4}-\d{2}-\d{2})_(whatsapp|email|manual|entrevista)_(\d{2,})$")
_SOURCE_MAP = {
    "01_Drive EV": "drive_ev", "02_Whatsapp": "whatsapp", "03_Email": "email",
    "04_Manual": "manual", "05_CRM": "crm", "06_Entrevistas": "entrevista",
}
# Campos que el helper escribe en el catálogo (subconjunto de CatalogEntry).
CAMPOS_EMITIDOS = [
    "id_doc", "ruta_relativa", "nombre_original", "tipo_documental", "fecha_doc",
    "parte", "fuente", "estado", "hash", "parent_id", "nombre_canonico",
]
```

Y en `derivar`, la primera línea pasa de `filas = _parse_filas(...)` a:

```python
def derivar(manifiesto: Path, salida: Path) -> Path:
    filas = manifiesto_parser.parse_manifiesto(Path(manifiesto).read_text(encoding="utf-8"))
    entradas = []
    for f in filas:
        rel = f["ruta_original"]
        sha = f["sha256"]
        entradas.append({
            "id_doc": sha[:12] if sha else rel,
            "ruta_relativa": rel,
            "nombre_original": rel.replace("\\", "/").rsplit("/", 1)[-1],
            "tipo_documental": f["tipo"] or None,
            "fecha_doc": f["fecha"] or None,
            "parte": f["parte"] or None,
            "fuente": _fuente(rel),
            "estado": "original",
            "hash": sha,
            "parent_id": f["parent_id"] or None,
            "nombre_canonico": f["nombre_canonico"] or None,
        })
    Path(salida).write_text(
        yaml.dump(entradas, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    return Path(salida)
```

(El resto del fichero —`_fuente`, `main`, `__main__`— no cambia.)

- [ ] **Step 5: Confirmar que pasa (nuevo + regresión de catálogo)**

Run: `& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" -m pytest tests/test_manifiesto_parser.py tests/test_manifiesto_a_catalogo.py -v`
Expected: `test_manifiesto_parser` (4) PASS y `test_manifiesto_a_catalogo` (4) siguen en PASS.

- [ ] **Step 6: Commit**

```bash
git add ".claude/skills/organizar-sala-lectura/scripts/manifiesto_parser.py" ".claude/skills/organizar-sala-lectura/scripts/manifiesto_a_catalogo.py" tests/test_manifiesto_parser.py
git commit -m "refactor(sala-lectura): parser compartido del _MANIFIESTO (stdlib, por cabecera)"
```

---

### Task 2: Columnas `categoria` y `subcategoria_crm` en el manifiesto y el catálogo

**Por qué:** la promesa de re-aplicación ("conserva la clasificación previa") es incumplible porque el manifiesto no persiste la categoría; y el YAML (SSOT máquina) omite el dato por el que se construyó la sala. Ítem 8 (parte columnas).

**Files:**
- Modify: `core/catalogo_documental.py:32-51` (dos campos opcionales en `CatalogEntry`)
- Modify: `.claude/skills/organizar-sala-lectura/scripts/manifiesto_a_catalogo.py` (`CAMPOS_EMITIDOS` + `derivar`)
- Test: `tests/test_manifiesto_a_catalogo.py` (nuevo caso 9-columnas + regresión anti-drift)

**Interfaces:**
- Consumes: `manifiesto_parser.parse_manifiesto` (Task 1) — las columnas `categoria`/`subcategoria_crm` llegan por cabecera.
- Produces: catálogo YAML con `categoria` y `subcategoria_crm` por entrada (o `None` si el manifiesto es viejo de 7 columnas).

- [ ] **Step 1: Escribir el test que falla**

```python
# añadir a tests/test_manifiesto_a_catalogo.py
_MANIF_CAT = """<!-- GENERADO — NO EDITAR A MANO -->
| sha256 | ruta_original | nombre_canonico | tipo | fecha | parte | parent_id | categoria | subcategoria_crm |
|---|---|---|---|---|---|---|---|---|
| aaaa | sudespacho_1/civil/x.pdf | 2025-01-01_x.pdf | pdf | 2025-01-01 | propietario |  | 07. RECLAMACIONES | civil |
"""


def test_deriva_categoria_y_subcategoria(tmp_path):
    mod = _load()
    (tmp_path / "_MANIFIESTO.md").write_text(_MANIF_CAT, encoding="utf-8")
    out = mod.derivar(tmp_path / "_MANIFIESTO.md", tmp_path / "indice_documental.yaml")
    data = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert data[0]["categoria"] == "07. RECLAMACIONES"
    assert data[0]["subcategoria_crm"] == "civil"


def test_manifiesto_viejo_7col_da_categoria_none(tmp_path):
    mod = _load()
    (tmp_path / "_MANIFIESTO.md").write_text(_MANIF, encoding="utf-8")
    out = mod.derivar(tmp_path / "_MANIFIESTO.md", tmp_path / "indice_documental.yaml")
    data = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert data[0]["categoria"] is None
    assert data[0]["subcategoria_crm"] is None
```

- [ ] **Step 2: Confirmar que falla**

Run: `& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" -m pytest tests/test_manifiesto_a_catalogo.py -v -k "categoria"`
Expected: `KeyError: 'categoria'` (el YAML aún no lleva el campo).

- [ ] **Step 3: Añadir los campos a `CatalogEntry`**

En `core/catalogo_documental.py`, al final del dataclass `CatalogEntry` (tras `ruta_sala_lectura`):

```python
    nombre_canonico: str | None = None
    ruta_sala_lectura: str | None = None
    categoria: str | None = None          # categoría E&V (por la que se construyó la sala)
    subcategoria_crm: str | None = None   # subcarpeta del Gestor Documental CRM (etiqueta secundaria)
```

- [ ] **Step 4: Emitir los campos desde el helper**

En `manifiesto_a_catalogo.py`, extender `CAMPOS_EMITIDOS`:

```python
CAMPOS_EMITIDOS = [
    "id_doc", "ruta_relativa", "nombre_original", "tipo_documental", "fecha_doc",
    "parte", "fuente", "estado", "hash", "parent_id", "nombre_canonico",
    "categoria", "subcategoria_crm",
]
```

Y en el dict de `entradas` dentro de `derivar`, añadir (usando `.get`, que devuelve `None` en manifiestos viejos de 7 columnas):

```python
            "parent_id": f["parent_id"] or None,
            "nombre_canonico": f["nombre_canonico"] or None,
            "categoria": f.get("categoria") or None,
            "subcategoria_crm": f.get("subcategoria_crm") or None,
```

- [ ] **Step 5: Confirmar que pasa (incl. anti-drift)**

Run: `& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" -m pytest tests/test_manifiesto_a_catalogo.py -v`
Expected: PASS incluyendo `test_campos_coinciden_con_CatalogEntry` (los dos campos nuevos ∈ `CatalogEntry`).

- [ ] **Step 6: Commit**

```bash
git add core/catalogo_documental.py ".claude/skills/organizar-sala-lectura/scripts/manifiesto_a_catalogo.py" tests/test_manifiesto_a_catalogo.py
git commit -m "feat(sala-lectura): categoria + subcategoria_crm en el manifiesto y el catalogo YAML"
```

---

### Task 3: `indices_desde_manifiesto.py` — INDICE.md y CRONOLOGIA.md por script

**Por qué:** los índices a mano son parte medible de la fase lenta (30+ min) y el LLM transcribe ~350 líneas por corrida. Ítem 8 (parte índices).

**Files:**
- Create: `.claude/skills/organizar-sala-lectura/scripts/indices_desde_manifiesto.py`
- Test: `tests/test_indices_desde_manifiesto.py`

**Interfaces:**
- Consumes: `manifiesto_parser.parse_manifiesto` (Task 1); columnas `categoria`/`subcategoria_crm` (Task 2).
- Produces: `construir_indice(filas) -> str`, `construir_cronologia(filas) -> str`, `derivar(manifiesto: Path, out_dir: Path) -> tuple[Path, Path]`, `main(argv) -> int`.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_indices_desde_manifiesto.py
from importlib import import_module
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / ".claude/skills/organizar-sala-lectura/scripts"))
idx = import_module("indices_desde_manifiesto")

_MANIF = """<!-- GENERADO — NO EDITAR A MANO -->
| sha256 | ruta_original | nombre_canonico | tipo | fecha | parte | parent_id | categoria | subcategoria_crm |
|---|---|---|---|---|---|---|---|---|
| a | sudespacho_1/civil/auto.pdf | 2025-03-01_auto.pdf | pdf | 2025-03-01 | propietario |  | 07. RECLAMACIONES | civil |
| b | sudespacho_1/demanda/dda.pdf | 2025-05-10_demanda.pdf | pdf | 2025-05-10 | propietario |  | 07. RECLAMACIONES | demanda |
| c | 03_Email/corr.eml | 2025-06-01_correo.eml | eml | 2025-06-01 | propietario |  | 07. RECLAMACIONES |  |
| d | 01_Drive EV/encargo.pdf | 2024-01-01_encargo.pdf | pdf | 2024-01-01 | propietario |  | 01. ACTIVACIÓN |  |
| e | 01_Drive EV/sin_fecha.pdf | 0000-00-00_sinfecha.pdf | pdf | 0000-00-00 | propietario |  | 01. ACTIVACIÓN |  |
"""


def _filas():
    import manifiesto_parser
    return manifiesto_parser.parse_manifiesto(_MANIF)


def test_indice_agrupa_por_categoria_y_ordena_fecha_desc():
    txt = idx.construir_indice(_filas())
    assert "## 01. ACTIVACIÓN" in txt
    assert "## 07. RECLAMACIONES" in txt
    # Dentro de ACTIVACIÓN, 2024-01-01 (con fecha) va ANTES que 0000-00-00 (incierta, al final).
    act = txt.split("## 01. ACTIVACIÓN", 1)[1].split("## ", 1)[0]
    assert act.index("2024-01-01_encargo") < act.index("0000-00-00_sinfecha")


def test_reclamaciones_subagrupa_por_subcategoria_crm():
    txt = idx.construir_indice(_filas())
    rec = txt.split("## 07. RECLAMACIONES", 1)[1]
    assert "### civil" in rec
    assert "### demanda" in rec
    assert "### correspondencia" in rec  # el .eml sin subcategoria


def test_cronologia_orden_ascendente_incierta_al_final():
    txt = idx.construir_cronologia(_filas())
    assert txt.index("2024-01-01_encargo") < txt.index("2025-06-01_correo")
    assert txt.index("2025-06-01_correo") < txt.index("0000-00-00_sinfecha")


def test_derivar_escribe_ambos_ficheros_idempotente(tmp_path):
    (tmp_path / "_MANIFIESTO.md").write_text(_MANIF, encoding="utf-8")
    i1, c1 = idx.derivar(tmp_path / "_MANIFIESTO.md", tmp_path)
    a, b = i1.read_text(encoding="utf-8"), c1.read_text(encoding="utf-8")
    idx.derivar(tmp_path / "_MANIFIESTO.md", tmp_path)
    assert i1.read_text(encoding="utf-8") == a
    assert c1.read_text(encoding="utf-8") == b
    assert a.startswith("<!-- GENERADO — NO EDITAR A MANO -->")
```

- [ ] **Step 2: Confirmar que falla**

Run: `& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" -m pytest tests/test_indices_desde_manifiesto.py -v`
Expected: `ModuleNotFoundError: No module named 'indices_desde_manifiesto'`.

- [ ] **Step 3: Crear `indices_desde_manifiesto.py`**

```python
# .claude/skills/organizar-sala-lectura/scripts/indices_desde_manifiesto.py
"""Deriva INDICE.md (por categoría, fecha DESC; "07. RECLAMACIONES" sub-agrupada
por subcategoria_crm) y CRONOLOGIA.md (fecha ASC; 0000-00-00 y fechas
aproximadas (*) al final) del `_MANIFIESTO.md`. Determinista, idempotente,
stdlib puro (sin `core/` ni `yaml`). El LLM ya no transcribe ~350 líneas de
markdown por corrida (backlog robustez-velocidad, ítem 8): escribe solo el
`_MANIFIESTO.md` y ejecuta este script.
"""
from __future__ import annotations

import sys
from pathlib import Path

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
import manifiesto_parser  # noqa: E402

_GEN = "<!-- GENERADO — NO EDITAR A MANO -->"
_RECLAMACIONES = "07. RECLAMACIONES"
_SIN_FECHA = "0000-00-00"
_SIN_CATEGORIA = "08. PENDIENTE DE CLASIFICAR"


def _fecha_limpia(fecha: str) -> str:
    return (fecha or "").replace("(*)", "").strip()


def _es_fecha_incierta(fecha: str) -> bool:
    f = (fecha or "").strip()
    return (not f) or f.startswith(_SIN_FECHA) or "(*)" in f


def _linea(f: dict) -> str:
    nombre = f.get("nombre_canonico") or ""
    orig = (f.get("ruta_original") or "").replace("\\", "/").rsplit("/", 1)[-1]
    fecha = f.get("fecha") or _SIN_FECHA
    return f"- {fecha} · [{nombre}]({nombre}) — original: {orig}"


def _subcat(f: dict) -> str:
    return (f.get("subcategoria_crm") or "").strip() or "correspondencia"


def construir_indice(filas: list[dict]) -> str:
    def clave_desc(f: dict):
        return (0 if _es_fecha_incierta(f.get("fecha", "")) else 1, _fecha_limpia(f.get("fecha", "")))

    por_cat: dict[str, list[dict]] = {}
    for f in filas:
        por_cat.setdefault((f.get("categoria") or _SIN_CATEGORIA).strip(), []).append(f)

    out = [_GEN, "", "# Índice documental", ""]
    for cat in sorted(por_cat):
        out += [f"## {cat}", ""]
        grupo = por_cat[cat]
        if cat == _RECLAMACIONES and any((f.get("subcategoria_crm") or "").strip() for f in grupo):
            por_sub: dict[str, list[dict]] = {}
            for f in grupo:
                por_sub.setdefault(_subcat(f), []).append(f)
            for sub in sorted(por_sub):
                out += [f"### {sub}", ""]
                out += [_linea(f) for f in sorted(por_sub[sub], key=clave_desc, reverse=True)]
                out += [""]
        else:
            out += [_linea(f) for f in sorted(grupo, key=clave_desc, reverse=True)]
            out += [""]
    return "\n".join(out).rstrip() + "\n"


def construir_cronologia(filas: list[dict]) -> str:
    def clave_asc(f: dict):
        return (1 if _es_fecha_incierta(f.get("fecha", "")) else 0, _fecha_limpia(f.get("fecha", "")))

    out = [_GEN, "", "# Cronología", ""]
    out += [_linea(f) for f in sorted(filas, key=clave_asc)]
    return "\n".join(out).rstrip() + "\n"


def derivar(manifiesto: Path, out_dir: Path) -> tuple[Path, Path]:
    filas = manifiesto_parser.parse_manifiesto(Path(manifiesto).read_text(encoding="utf-8"))
    indice = Path(out_dir) / "INDICE.md"
    crono = Path(out_dir) / "CRONOLOGIA.md"
    indice.write_text(construir_indice(filas), encoding="utf-8")
    crono.write_text(construir_cronologia(filas), encoding="utf-8")
    return indice, crono


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("uso: indices_desde_manifiesto.py <_MANIFIESTO.md> <sala_dir>")
        return 2
    derivar(Path(argv[1]), Path(argv[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 4: Confirmar que pasa**

Run: `& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" -m pytest tests/test_indices_desde_manifiesto.py -v`
Expected: `4 passed`.

- [ ] **Step 5: Commit**

```bash
git add ".claude/skills/organizar-sala-lectura/scripts/indices_desde_manifiesto.py" tests/test_indices_desde_manifiesto.py
git commit -m "feat(sala-lectura): INDICE.md y CRONOLOGIA.md derivados por script del manifiesto"
```

---

### Task 4: `verificar()` — colisiones de `nombre_canonico` + aviso de fallos homogéneos

**Por qué:** (a) colisión de `nombre_canonico` es el único modo de fallo que puede hacer DESAPARECER un documento sin rastro en ningún check (el `set` colapsa duplicados y verify pasa verde); en honorarios, perder un requerimiento de pago es perder prueba (ítem 3, parte verify). (b) El modo de fallo más caro observado fue parchear 21 filas a mano por un falso positivo homogéneo: si ≥5 problemas son del mismo tipo, la hipótesis por defecto debe ser bug del check (ítem 4, parte código).

**Files:**
- Modify: `.claude/skills/organizar-sala-lectura/scripts/verificar_sala.py` (`verificar`)
- Test: `tests/test_verificar_sala.py`

**Interfaces:**
- Produces (sin cambio de firma): `verificar(manifiesto_filas, ficheros_en_disco, cobertura_filas=None) -> list[str]`. Nuevas detecciones: `nombre_canonico` repetido; y una línea `ATENCIÓN: N problemas homogéneos del tipo '<tipo>'` **antepuesta** cuando algún tipo alcanza el umbral (5).

- [ ] **Step 1: Escribir el test que falla**

```python
# añadir a tests/test_verificar_sala.py
def test_detecta_colision_de_nombre_canonico():
    filas = [
        {"nombre_canonico": "2025-01-01_doc.pdf", "sha256": "a", "parent_id": ""},
        {"nombre_canonico": "2025-01-01_doc.pdf", "sha256": "b", "parent_id": ""},
    ]
    problemas = verificar_sala.verificar(filas, ficheros_en_disco={"2025-01-01_doc.pdf"})
    assert any("nombre_canonico repetido" in p and "2025-01-01_doc.pdf" in p for p in problemas)


def test_avisa_de_fallos_homogeneos_por_encima_del_umbral():
    # 6 anexos con parent_id que no resuelve -> mismo tipo 'parent_huerfano'.
    filas = [{"nombre_canonico": "p.pdf", "sha256": "p", "parent_id": ""}]
    for i in range(6):
        filas.append({"nombre_canonico": f"a{i}.pdf", "sha256": f"s{i}", "parent_id": "no-existe"})
    disco = {f["nombre_canonico"] for f in filas}
    problemas = verificar_sala.verificar(filas, ficheros_en_disco=disco)
    assert problemas[0].startswith("ATENCIÓN:")
    assert "homogéneos" in problemas[0] and "parent_huerfano" in problemas[0]


def test_no_avisa_homogeneo_por_debajo_del_umbral():
    filas = [{"nombre_canonico": "p.pdf", "sha256": "p", "parent_id": ""}]
    for i in range(3):
        filas.append({"nombre_canonico": f"a{i}.pdf", "sha256": f"s{i}", "parent_id": "no-existe"})
    disco = {f["nombre_canonico"] for f in filas}
    problemas = verificar_sala.verificar(filas, ficheros_en_disco=disco)
    assert not any(p.startswith("ATENCIÓN:") for p in problemas)
```

- [ ] **Step 2: Confirmar que falla**

Run: `& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" -m pytest tests/test_verificar_sala.py -v -k "colision or homogeneo"`
Expected: FAIL (no existe la detección de colisión ni el aviso homogéneo).

- [ ] **Step 3: Reescribir `verificar` (preservando lo del PR #114)**

Sustituir el cuerpo de `verificar()` por la versión tipada. La cabecera del módulo y `_CHARS_MINIMOS_SOSPECHOSO = 200` no cambian; añadir `_UMBRAL_HOMOGENEO = 5` y `from collections import Counter` bajo el `from __future__`:

```python
from __future__ import annotations

from collections import Counter

_CHARS_MINIMOS_SOSPECHOSO = 200
_UMBRAL_HOMOGENEO = 5


def verificar(
    manifiesto_filas: list[dict],
    ficheros_en_disco: set[str],
    cobertura_filas: list[dict] | None = None,
) -> list[str]:
    """Nunca arregla nada — solo detecta. Devuelve la lista de problemas (vacía
    si todo cuadra). Si ≥`_UMBRAL_HOMOGENEO` problemas son del MISMO tipo,
    antepone un aviso: la hipótesis por defecto es bug del CHECK, no de los
    datos (modo de fallo más caro observado: 21 filas parcheadas a mano por un
    falso positivo de parent_id, sesión anterior W-02VUDR)."""
    tipados: list[tuple[str, str]] = []
    nombres_lista = [f["nombre_canonico"] for f in manifiesto_filas]
    nombres_manifiesto = set(nombres_lista)

    for nombre, n in Counter(nombres_lista).items():
        if n > 1:
            tipados.append(("colision_nombre",
                f"{nombre}: nombre_canonico repetido en {n} filas — colisión, un "
                f"documento pisaría a otro en disco; desambigua con _2/_3"))

    for fila in manifiesto_filas:
        nombre = fila["nombre_canonico"]
        if nombre not in ficheros_en_disco:
            tipados.append(("sin_fichero", f"{nombre}: fila en manifiesto pero no existe en disco"))

    for nombre in ficheros_en_disco:
        if nombre not in nombres_manifiesto:
            tipados.append(("huerfano_disco", f"{nombre}: fichero en disco sin fila en el manifiesto"))

    shas_manifiesto = {f.get("sha256") for f in manifiesto_filas}
    for fila in manifiesto_filas:
        parent = fila.get("parent_id") or ""
        if not parent:
            continue
        # parent_id resuelve por sha256, por nombre_canonico exacto, o —convención
        # real de bundles desde v1.1— por ser el nombre PELADO de la carpeta del
        # bundle (prefijo de directorio de algún nombre_canonico). (PR #114.)
        resuelve = (
            parent in shas_manifiesto
            or parent in nombres_manifiesto
            or any(n.startswith(parent + "/") for n in nombres_manifiesto)
        )
        if not resuelve:
            tipados.append(("parent_huerfano",
                f"{fila['nombre_canonico']}: parent_id {parent!r} no resuelve a "
                f"ningún documento del manifiesto (anexo huérfano)"))

    if cobertura_filas:
        chars_ok_por_origen: dict[str, int] = {}
        for c in cobertura_filas:
            if c.get("estado") not in ("ok", "low"):
                continue
            origen = c.get("parent_sha256") or c.get("sha256")
            chars = c.get("chars") or 0
            if chars > chars_ok_por_origen.get(origen, -1):
                chars_ok_por_origen[origen] = chars
        for fila in manifiesto_filas:
            if fila.get("fecha") != "0000-00-00":
                continue
            chars = chars_ok_por_origen.get(fila.get("sha256"))
            if chars is not None and chars >= _CHARS_MINIMOS_SOSPECHOSO:
                tipados.append(("fecha_0000",
                    f"{fila['nombre_canonico']}: fecha 0000-00-00 pero hay texto "
                    f"extraído ({chars} chars) en sala de máquina -- revisar si "
                    f"contiene una fecha real antes de dar por bueno el 0000-00-00"))

    por_tipo = Counter(t for t, _ in tipados)
    avisos = [
        f"ATENCIÓN: {n} problemas homogéneos del tipo '{t}' — sospecha del check, "
        f"no de los datos; contrasta 2-3 filas a mano antes de tocar nada"
        for t, n in por_tipo.items() if n >= _UMBRAL_HOMOGENEO
    ]
    return avisos + [msg for _, msg in tipados]
```

- [ ] **Step 4: Confirmar que pasa (nuevo + regresión completa de verify)**

Run: `& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" -m pytest tests/test_verificar_sala.py -v`
Expected: PASS de los 3 nuevos y de los ~10 previos (incl. `test_todo_correcto_no_da_problemas`, que sigue devolviendo `[]`).

- [ ] **Step 5: Commit**

```bash
git add ".claude/skills/organizar-sala-lectura/scripts/verificar_sala.py" tests/test_verificar_sala.py
git commit -m "feat(sala-lectura): verify detecta colision de nombre_canonico y avisa de fallos homogeneos"
```

---

### Task 5: CLI de `verificar_sala.py` — verify determinista de extremo a extremo

**Por qué:** hoy las ENTRADAS del verify (parseo del manifiesto, listado del directorio) las ensambla cada agente por juicio — el mismo agente que se equivocó decide qué ve el check que debe cazarlo. Y verify comprueba existencia, no integridad. Ítem 7.

**Files:**
- Modify: `.claude/skills/organizar-sala-lectura/scripts/verificar_sala.py` (`main`, `_listar_sala`, `_problemas_hash`)
- Test: `tests/test_verificar_sala_cli.py`

**Interfaces:**
- Consumes: `manifiesto_parser.parse_manifiesto` (Task 1); `verificar` (Task 4).
- Produces: `main(argv) -> int` — `verificar_sala.py <sala_dir> [--cobertura <ruta>] [--hash {no|muestra|completo}]`; exit 1 si hay problemas, 0 si cuadra, 2 uso incorrecto. `_listar_sala(sala_dir) -> set[str]` (relpaths posix, excluye índices generados y `_plan/`).

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_verificar_sala_cli.py
from importlib import import_module
from pathlib import Path
import hashlib
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / ".claude/skills/organizar-sala-lectura/scripts"))
verificar_sala = import_module("verificar_sala")


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _montar_sala(tmp_path, filas_extra="", ficheros=None):
    sala = tmp_path / "Sala lectura"
    sala.mkdir()
    (sala / "_plan").mkdir()
    (sala / "_plan" / "plan-x.md").write_text("ignorame", encoding="utf-8")
    for nombre, contenido in (ficheros or {}).items():
        p = sala / nombre
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(contenido)
    return sala


def test_listar_sala_excluye_indices_y_plan(tmp_path):
    sala = _montar_sala(tmp_path, ficheros={"2025-01-01_doc.pdf": b"x"})
    (sala / "INDICE.md").write_text("i", encoding="utf-8")
    (sala / "_MANIFIESTO.md").write_text("m", encoding="utf-8")
    (sala / "indice_documental.yaml").write_text("y", encoding="utf-8")
    encontrados = verificar_sala._listar_sala(sala)
    assert encontrados == {"2025-01-01_doc.pdf"}


def test_main_exit_0_cuando_cuadra(tmp_path):
    contenido = b"contenido del doc"
    sala = _montar_sala(tmp_path, ficheros={"2025-01-01_doc.pdf": contenido})
    (sala / "_MANIFIESTO.md").write_text(
        "| sha256 | ruta_original | nombre_canonico | tipo | fecha | parte | parent_id |\n"
        "|---|---|---|---|---|---|---|\n"
        f"| {_sha(contenido)} | 00_Input/x.pdf | 2025-01-01_doc.pdf | pdf | 2025-01-01 | propietario |  |\n",
        encoding="utf-8")
    assert verificar_sala.main(["verificar_sala.py", str(sala)]) == 0


def test_main_exit_1_cuando_falta_fichero(tmp_path):
    sala = _montar_sala(tmp_path, ficheros={})
    (sala / "_MANIFIESTO.md").write_text(
        "| sha256 | ruta_original | nombre_canonico | tipo | fecha | parte | parent_id |\n"
        "|---|---|---|---|---|---|---|\n"
        "| aaaa | 00_Input/x.pdf | 2025-01-01_doc.pdf | pdf | 2025-01-01 | propietario |  |\n",
        encoding="utf-8")
    assert verificar_sala.main(["verificar_sala.py", str(sala)]) == 1


def test_main_hash_completo_detecta_copia_corrupta(tmp_path):
    sala = _montar_sala(tmp_path, ficheros={"2025-01-01_doc.pdf": b"contenido REAL en disco"})
    (sala / "_MANIFIESTO.md").write_text(
        "| sha256 | ruta_original | nombre_canonico | tipo | fecha | parte | parent_id |\n"
        "|---|---|---|---|---|---|---|\n"
        f"| {_sha(b'otro contenido esperado')} | 00_Input/x.pdf | 2025-01-01_doc.pdf | pdf | 2025-01-01 | propietario |  |\n",
        encoding="utf-8")
    assert verificar_sala.main(["verificar_sala.py", str(sala), "--hash", "completo"]) == 1
```

- [ ] **Step 2: Confirmar que falla**

Run: `& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" -m pytest tests/test_verificar_sala_cli.py -v`
Expected: `AttributeError: module 'verificar_sala' has no attribute '_listar_sala'`.

- [ ] **Step 3: Añadir la CLI a `verificar_sala.py`**

Añadir imports al principio del módulo (tras `from collections import Counter`) y las funciones al final del fichero:

```python
import hashlib
import json
import sys
from pathlib import Path

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
import manifiesto_parser  # noqa: E402

_EXCLUIR_NOMBRES = {"INDICE.md", "CRONOLOGIA.md", "_MANIFIESTO.md", "indice_documental.yaml"}
_EXCLUIR_DIRS_TOP = {"_plan"}


def _listar_sala(sala_dir) -> set[str]:
    """Relpaths posix de los ficheros COPIADOS de la sala (bundles incluidos como
    `subcarpeta/fichero.ext`, que es como se escribe su `nombre_canonico`),
    excluyendo los índices generados y el directorio `_plan/`."""
    sala_dir = Path(sala_dir)
    encontrados: set[str] = set()
    for p in sala_dir.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(sala_dir)
        if rel.parts and rel.parts[0] in _EXCLUIR_DIRS_TOP:
            continue
        if p.name in _EXCLUIR_NOMBRES:
            continue
        encontrados.add(rel.as_posix())
    return encontrados


def _sha256_fichero(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _problemas_hash(sala_dir, filas, ficheros_en_disco, modo) -> list[str]:
    """Contrasta el sha256 de la COPIA en disco contra el del manifiesto (que es
    el del ORIGEN; una copia byte-idéntica debe coincidir). `muestra` = 10%
    determinista; `completo` = todos. Filas sin sha256 de 64 hex (Modo 3 md5 o
    pendiente) no se pueden contrastar y se saltan."""
    if modo == "no":
        return []
    objetivo = sorted(ficheros_en_disco)
    if modo == "muestra":
        objetivo = objetivo[::10] or objetivo[:1]
    sha_por_nombre = {f["nombre_canonico"]: f.get("sha256") for f in filas}
    problemas: list[str] = []
    for rel in objetivo:
        esperado = sha_por_nombre.get(rel)
        if not esperado or len(esperado) != 64:
            continue
        real = _sha256_fichero(Path(sala_dir) / rel)
        if real != esperado:
            problemas.append(
                f"{rel}: sha256 en disco {real[:12]} != manifiesto {esperado[:12]} "
                f"(copia corrupta o alterada)")
    return problemas


def main(argv: list[str]) -> int:
    args = argv[1:]
    if not args:
        print("uso: verificar_sala.py <sala_dir> [--cobertura <ruta>] [--hash {no|muestra|completo}]")
        return 2
    sala_dir = Path(args[0])
    cobertura_path = None
    modo_hash = "no"
    i = 1
    while i < len(args):
        if args[i] == "--cobertura" and i + 1 < len(args):
            cobertura_path = Path(args[i + 1]); i += 2
        elif args[i] == "--hash" and i + 1 < len(args):
            modo_hash = args[i + 1]; i += 2
        else:
            print(f"argumento no reconocido: {args[i]}"); return 2
    if modo_hash not in ("no", "muestra", "completo"):
        print(f"--hash debe ser no|muestra|completo, no {modo_hash!r}"); return 2
    manif = sala_dir / "_MANIFIESTO.md"
    if not manif.exists():
        print(f"no existe {manif}"); return 2
    filas = manifiesto_parser.parse_manifiesto(manif.read_text(encoding="utf-8"))
    cobertura = None
    if cobertura_path and cobertura_path.exists():
        cobertura = json.loads(cobertura_path.read_text(encoding="utf-8"))
    ficheros = _listar_sala(sala_dir)
    problemas = verificar(filas, ficheros, cobertura)
    problemas += _problemas_hash(sala_dir, filas, ficheros, modo_hash)
    for p in problemas:
        print(p)
    if problemas:
        print(f"\n{len(problemas)} problema(s).")
        return 1
    print("Verify OK: manifiesto y disco cuadran.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 4: Confirmar que pasa**

Run: `& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" -m pytest tests/test_verificar_sala_cli.py tests/test_verificar_sala.py -v`
Expected: PASS de los 4 nuevos y de los previos.

- [ ] **Step 5: Commit**

```bash
git add ".claude/skills/organizar-sala-lectura/scripts/verificar_sala.py" tests/test_verificar_sala_cli.py
git commit -m "feat(sala-lectura): CLI de verificar_sala (parseo+listado deterministas, --cobertura, --hash)"
```

---

### Task 6: `validar_pares` en `copiar_manifiesto_rclone` — abortar antes de tocar Drive

**Por qué:** una colisión de `dst_relpath` (dos orígenes escribiendo el mismo destino) hace que uno pise al otro sin rastro. Detectarla en el verify (Task 4) es tarde: el documento ya desapareció. Hay que abortar ANTES de copiar. Ítem 3 (parte copia).

**Files:**
- Modify: `.claude/skills/organizar-sala-lectura/scripts/copiar_manifiesto_rclone.py` (`validar_pares` + guard en `copiar_manifiesto`)
- Test: `tests/test_copiar_manifiesto_rclone.py`

**Interfaces:**
- Produces: `validar_pares(pares: list[tuple[str, str]]) -> None` — lanza `ValueError` si hay `dst_relpath` duplicados.
- Modifies: `copiar_manifiesto(remote, pares)` llama `validar_pares(pares)` antes de cualquier copia.

- [ ] **Step 1: Escribir el test que falla**

```python
# añadir a tests/test_copiar_manifiesto_rclone.py
import pytest


def test_validar_pares_lanza_si_hay_destino_duplicado():
    with pytest.raises(ValueError, match="destinos duplicados"):
        cmr.validar_pares([("a/x.pdf", "b/dup.pdf"), ("a/y.pdf", "b/dup.pdf")])


def test_validar_pares_ok_si_destinos_unicos():
    cmr.validar_pares([("a/x.pdf", "b/x.pdf"), ("a/y.pdf", "b/y.pdf")])  # no lanza


def test_copiar_manifiesto_aborta_antes_de_copiar_si_hay_colision():
    from unittest.mock import patch
    with patch("urllib.request.urlopen") as m:
        with pytest.raises(ValueError, match="destinos duplicados"):
            cmr.copiar_manifiesto("gdrive_tl:", [("a/x.pdf", "b/dup.pdf"), ("a/y.pdf", "b/dup.pdf")])
        m.assert_not_called()  # ningún fichero se copió
```

- [ ] **Step 2: Confirmar que falla**

Run: `& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" -m pytest tests/test_copiar_manifiesto_rclone.py -v -k "validar or colision"`
Expected: `AttributeError: module 'copiar_manifiesto_rclone' has no attribute 'validar_pares'`.

- [ ] **Step 3: Implementar `validar_pares` + enganchar en `copiar_manifiesto`**

Añadir `from collections import Counter` a los imports, y la función; luego llamarla al inicio de `copiar_manifiesto`:

```python
def validar_pares(pares: list[tuple[str, str]]) -> None:
    """Aborta ANTES de tocar Drive si dos orígenes escriben el MISMO destino
    (`dst_relpath` duplicado) — uno pisaría al otro sin rastro. Backlog
    robustez-velocidad ítem 3: único modo de fallo que puede hacer DESAPARECER
    un documento sin que ningún check posterior lo cace."""
    dups = sorted(d for d, n in Counter(dst for _, dst in pares).items() if n > 1)
    if dups:
        raise ValueError(
            "destinos duplicados en el plan de copia (colisión de nombre_canonico): "
            + ", ".join(dups) + " — desambigua con _2/_3 antes de copiar")
```

En `copiar_manifiesto`, primera línea del cuerpo:

```python
def copiar_manifiesto(
    remote: str, pares: list[tuple[str, str]],
) -> tuple[list[str], list[tuple[str, str]]]:
    """... (docstring existente) ..."""
    validar_pares(pares)
    ok: list[str] = []
    fallidos: list[tuple[str, str]] = []
    ...
```

- [ ] **Step 4: Confirmar que pasa (nuevo + regresión)**

Run: `& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" -m pytest tests/test_copiar_manifiesto_rclone.py -v`
Expected: PASS de los 3 nuevos y de los 2 previos (`test_copiar_manifiesto_no_aborta_si_uno_falla` usa destinos únicos → `validar_pares` no lanza).

- [ ] **Step 5: Commit**

```bash
git add ".claude/skills/organizar-sala-lectura/scripts/copiar_manifiesto_rclone.py" tests/test_copiar_manifiesto_rclone.py
git commit -m "feat(sala-lectura): validar_pares aborta la copia si hay destino duplicado (colision)"
```

---

### Task 7: `senales_gate` en `preclasificar.py` — señales del gate por código

**Por qué:** 3 de las 4 señales del gate condicional son hoy comprobaciones mentales del agente, y ya falló en producción (un fichero de W-02X270 se copió a la sala de W-02VUDR). Ítem 1.

**Files:**
- Modify: `.claude/skills/organizar-sala-lectura/scripts/preclasificar.py` (`senales_gate` + helpers)
- Test: `tests/test_preclasificar_sala_lectura.py`

**Interfaces:**
- Produces: `senales_gate(filas: list[dict], wcode_caso: str, cobertura_filas: list[dict] | None = None) -> list[str]` — lista de señales (vacía → auto-aprueba; no vacía → presentar y esperar). Cada `fila` usa `ruta_original`, `nombre_canonico`, `sha256`, `motivo`.

- [ ] **Step 1: Escribir el test que falla**

```python
# añadir a tests/test_preclasificar_sala_lectura.py
def test_senales_gate_detecta_wcode_ajeno():
    filas = [{"ruta_original": "05_CRM/sudespacho_9/W-02X270_doc.pdf",
              "nombre_canonico": "2025-01-01_doc.pdf", "sha256": "a", "motivo": "default_reclamaciones"}]
    señales = preclasificar.senales_gate(filas, wcode_caso="W-02VUDR")
    assert any("W-02X270" in s for s in señales)


def test_senales_gate_ignora_wcode_propio():
    filas = [{"ruta_original": "05_CRM/sudespacho_9/W-02VUDR_doc.pdf",
              "nombre_canonico": "2025-01-01_doc.txt", "sha256": "a", "motivo": "default_reclamaciones"}]
    assert preclasificar.senales_gate(filas, wcode_caso="W-02VUDR") == []


def test_senales_gate_detecta_casi_duplicado_mismo_nombre_distinto_sha():
    filas = [
        {"ruta_original": "a/OFERTA.pdf", "nombre_canonico": "2025-01-01_oferta.pdf", "sha256": "aaa", "motivo": "x"},
        {"ruta_original": "b/OFERTA.pdf", "nombre_canonico": "2025-02-01_oferta.pdf", "sha256": "bbb", "motivo": "x"},
    ]
    señales = preclasificar.senales_gate(filas, wcode_caso="W-02VUDR")
    assert any("casi-duplicado" in s and "oferta.pdf".lower() in s.lower() for s in señales)


def test_senales_gate_detecta_binario_opaco_sin_espejo_md():
    filas = [{"ruta_original": "a/escaneo.pdf", "nombre_canonico": "2025-01-01_escaneo.pdf", "sha256": "a", "motivo": "default_reclamaciones"}]
    señales = preclasificar.senales_gate(filas, wcode_caso="W-02VUDR", cobertura_filas=[])
    assert any("sin espejo MD" in s for s in señales)


def test_senales_gate_binario_opaco_con_espejo_no_es_senal():
    filas = [{"ruta_original": "a/escaneo.pdf", "nombre_canonico": "2025-01-01_escaneo.pdf", "sha256": "a", "motivo": "x"}]
    cobertura = [{"sha256": "seg", "parent_sha256": "a", "estado": "ok", "chars": 300}]
    assert preclasificar.senales_gate(filas, wcode_caso="W-02VUDR", cobertura_filas=cobertura) == []


def test_senales_gate_pasa_requiere_identificar_parte():
    filas = [{"ruta_original": "a/chat.txt", "nombre_canonico": "2024-01-01_chat.txt", "sha256": "a", "motivo": "requiere_identificar_parte"}]
    señales = preclasificar.senales_gate(filas, wcode_caso="W-02VUDR", cobertura_filas=None)
    assert any("requiere_identificar_parte" in s for s in señales)


def test_senales_gate_limpio_da_lista_vacia():
    # .eml (texto, no binario opaco), nombre único, wcode propio -> auto-aprueba.
    filas = [{"ruta_original": "03_Email/corr.eml", "nombre_canonico": "2025-01-01_correo.eml", "sha256": "a", "motivo": "default_reclamaciones"}]
    assert preclasificar.senales_gate(filas, wcode_caso="W-02VUDR", cobertura_filas=None) == []
```

- [ ] **Step 2: Confirmar que falla**

Run: `& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" -m pytest tests/test_preclasificar_sala_lectura.py -v -k senales_gate`
Expected: `AttributeError: module 'preclasificar' has no attribute 'senales_gate'`.

- [ ] **Step 3: Implementar `senales_gate`**

Añadir a `preclasificar.py`:

```python
_WCODE_RE = re.compile(r"W-[0-9A-Z]{5,6}", re.I)
_EXT_OPACAS = {
    "pdf", "jpg", "jpeg", "png", "gif", "tif", "tiff", "bmp", "heic", "webp",
    "xlsx", "xls", "mp4", "mov", "avi", "mkv", "m4a", "ogg", "opus",
}


def _ext(nombre: str) -> str:
    nombre = (nombre or "").rsplit("/", 1)[-1]
    return nombre.rsplit(".", 1)[-1].lower() if "." in nombre else ""


def _es_binario_opaco(fila: dict) -> bool:
    return _ext(fila.get("nombre_canonico") or fila.get("ruta_original") or "") in _EXT_OPACAS


def senales_gate(
    filas: list[dict],
    wcode_caso: str,
    cobertura_filas: list[dict] | None = None,
) -> list[str]:
    """Señales deterministas para el gate condicional (Paso 2.5). Lista VACÍA →
    auto-aprueba (sin anomalías); NO vacía → presenta la propuesta y espera OK.
    `filas`: dicts con `ruta_original`, `nombre_canonico`, `sha256`, `motivo`
    (de `clasificar_por_patron`). `wcode_caso`: el W-code propio del caso (las
    señales saltan para cualquier OTRO). `cobertura_filas`: filas de
    `_cobertura.json` de sala de máquina para saber qué sha256 tienen espejo MD
    (None = no hay sala de máquina → todo binario opaco es señal)."""
    señales: list[str] = []
    propio = (wcode_caso or "").upper()

    # (a) W-code ajeno en nombre o ruta -> excluir, nunca copiar.
    for f in filas:
        texto = f"{f.get('ruta_original', '')} {f.get('nombre_canonico', '')}"
        for m in _WCODE_RE.findall(texto):
            if m.upper() != propio:
                ref = f.get("ruta_original") or f.get("nombre_canonico")
                señales.append(f"W-code ajeno {m!r} en {ref} — excluir, nunca copiar")

    # (b) mismo nombre de origen con sha256 distinto (casi-duplicado).
    por_nombre: dict[str, set[str]] = {}
    for f in filas:
        base = (f.get("ruta_original") or "").replace("\\", "/").rsplit("/", 1)[-1].lower()
        if not base:
            continue
        por_nombre.setdefault(base, set()).add(f.get("sha256") or "")
    for base, shas in por_nombre.items():
        distintos = {s for s in shas if s}
        if len(distintos) > 1:
            señales.append(
                f"casi-duplicado: mismo nombre de origen {base!r} con {len(distintos)} sha256 distintos")

    # (c) binarios opacos sin espejo MD (cruzando por parent_sha256 or sha256).
    con_espejo: set[str] = set()
    for c in (cobertura_filas or []):
        if c.get("estado") in ("ok", "low"):
            con_espejo.add(c.get("parent_sha256") or c.get("sha256"))
    for f in filas:
        if _es_binario_opaco(f) and (f.get("sha256") not in con_espejo):
            ref = f.get("nombre_canonico") or f.get("ruta_original")
            señales.append(f"binario opaco sin espejo MD: {ref} — clasificado a ciegas por nombre")

    # (d) pass-through de requiere_identificar_parte (bundle sin parte).
    for f in filas:
        if f.get("motivo") == "requiere_identificar_parte":
            ref = f.get("nombre_canonico") or f.get("ruta_original")
            señales.append(f"bundle conversacional sin parte identificable: {ref} — requiere_identificar_parte")

    return señales
```

- [ ] **Step 4: Confirmar que pasa (nuevo + regresión de preclasificar)**

Run: `& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" -m pytest tests/test_preclasificar_sala_lectura.py -v`
Expected: PASS de los 7 nuevos y de los previos (incl. `test_categorias_sin_drift`).

- [ ] **Step 5: Commit**

```bash
git add ".claude/skills/organizar-sala-lectura/scripts/preclasificar.py" tests/test_preclasificar_sala_lectura.py
git commit -m "feat(sala-lectura): senales_gate determinista (W-code ajeno, casi-duplicado, binario sin espejo, parte)"
```

---

### Task 8: `precheck_rclone.py` — el prerrequisito OAuth por exit code, no por documentación

**Por qué:** en la pasada 2 el agente concluyó desde un doc archivado pre-julio que el client propio no existía (falso; un comando de 1s lo confirmaba) — la mejora de velocidad estrella de v1.9 nunca se probó. Ítem 6. **Nunca** volcar la config completa: `rclone config show` expone `token`/`client_secret` en claro (memoria [[feedback-rclone-config-show-secrets]]).

**Files:**
- Create: `.claude/skills/organizar-sala-lectura/scripts/precheck_rclone.py`
- Test: `tests/test_precheck_rclone.py`

**Interfaces:**
- Produces: `precheck(remote: str) -> int` (0 client propio / 3 client compartido o sin client_id / 4 rclone ausente o remote inexistente); `client_id_de_config(salida: str) -> str | None`; `project_de_client_id(client_id: str) -> str | None`; `main(argv) -> int`.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_precheck_rclone.py
from importlib import import_module
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / ".claude/skills/organizar-sala-lectura/scripts"))
pr = import_module("precheck_rclone")

_CONFIG_PROPIO = """[gdrive_tl]
type = drive
client_id = 111222333444-abcdef.apps.googleusercontent.com
client_secret = GOCSPX-secretazo
token = {"access_token":"ya29.secretoooo","refresh_token":"1//refrescooo"}
"""
_CONFIG_COMPARTIDO = """[gdrive_tl]
type = drive
token = {"access_token":"ya29.x"}
"""
_CONFIG_CLIENT_COMPARTIDO = """[gdrive_tl]
type = drive
client_id = 202264815644-xxxx.apps.googleusercontent.com
"""


def _run(stdout, returncode=0):
    m = MagicMock()
    m.stdout = stdout
    m.returncode = returncode
    return m


def test_exit_0_con_client_propio():
    with patch("subprocess.run", return_value=_run(_CONFIG_PROPIO)):
        assert pr.precheck("gdrive_tl:") == 0


def test_exit_3_sin_client_id():
    with patch("subprocess.run", return_value=_run(_CONFIG_COMPARTIDO)):
        assert pr.precheck("gdrive_tl") == 3


def test_exit_3_con_client_compartido_de_rclone():
    with patch("subprocess.run", return_value=_run(_CONFIG_CLIENT_COMPARTIDO)):
        assert pr.precheck("gdrive_tl") == 3


def test_exit_4_si_rclone_no_existe():
    with patch("subprocess.run", side_effect=FileNotFoundError):
        assert pr.precheck("gdrive_tl") == 4


def test_main_nunca_imprime_secretos(capsys):
    with patch("subprocess.run", return_value=_run(_CONFIG_PROPIO)):
        pr.main(["precheck_rclone.py", "gdrive_tl:"])
    out = capsys.readouterr().out
    assert "GOCSPX" not in out and "refresh_token" not in out and "ya29" not in out
```

- [ ] **Step 2: Confirmar que falla**

Run: `& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" -m pytest tests/test_precheck_rclone.py -v`
Expected: `ModuleNotFoundError: No module named 'precheck_rclone'`.

- [ ] **Step 3: Crear `precheck_rclone.py`**

```python
# .claude/skills/organizar-sala-lectura/scripts/precheck_rclone.py
"""Precheck determinista del prerrequisito OAuth de rclone para la copia en
bloque vía `rclone rcd` (backlog robustez-velocidad ítem 6). El prerrequisito
(client OAuth PROPIO del despacho, no el compartido `202264815644`) se comprueba
SOLO por exit code — NO se deduce leyendo documentación (en la pasada 2 un
agente concluyó desde un doc archivado que no existía; un comando de 1s lo
confirmaba).

NUNCA vuelca la config completa: `rclone config show` expone `token` y
`client_secret` en claro. Este script extrae SOLO la línea `client_id` por
regex y deriva de ella el project number; jamás imprime `stdout` de rclone.

exit 0 → client propio (project != 202264815644): rcd puede ser ruta primaria.
exit 3 → remote sin client propio (usa el compartido) → copia secuencial.
exit 4 → `rclone` no instalado / remote inexistente / timeout.
exit 2 → uso incorrecto.
"""
from __future__ import annotations

import re
import subprocess
import sys

_CLIENT_COMPARTIDO_PROJECT = "202264815644"
_CLIENT_ID_RE = re.compile(r"^\s*client_id\s*=\s*(\S+)", re.M)


def client_id_de_config(salida: str) -> str | None:
    m = _CLIENT_ID_RE.search(salida or "")
    return m.group(1) if m else None


def project_de_client_id(client_id: str) -> str | None:
    # Un client_id OAuth de Google es `<project_number>-<hash>.apps.googleusercontent.com`.
    m = re.match(r"(\d+)-", client_id or "")
    return m.group(1) if m else None


def precheck(remote: str) -> int:
    nombre = (remote or "").rstrip(":")  # `config show` no lleva el ':' del remote
    try:
        r = subprocess.run(
            ["rclone", "config", "show", nombre],
            capture_output=True, encoding="utf-8", errors="replace", timeout=15,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return 4
    if r.returncode != 0:
        return 4
    cid = client_id_de_config(r.stdout)
    if not cid:
        return 3
    project = project_de_client_id(cid)
    if project and project != _CLIENT_COMPARTIDO_PROJECT:
        return 0
    return 3


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("uso: precheck_rclone.py <remote>  (p. ej. gdrive_tl:)")
        return 2
    code = precheck(argv[1])
    # Solo un veredicto legible; JAMÁS el stdout de rclone (secretos en claro).
    print({0: "client propio: rcd primario", 3: "client compartido: copia secuencial",
           4: "rclone/remote no disponible"}.get(code, "uso incorrecto"))
    return code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 4: Confirmar que pasa**

Run: `& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" -m pytest tests/test_precheck_rclone.py -v`
Expected: `5 passed`.

- [ ] **Step 5: Commit**

```bash
git add ".claude/skills/organizar-sala-lectura/scripts/precheck_rclone.py" tests/test_precheck_rclone.py
git commit -m "feat(sala-lectura): precheck_rclone (prerrequisito OAuth por exit code, sin volcar secretos)"
```

---

### Task 9: Enganchar los helpers en el procedimiento de la skill (`SKILL.md`)

**Por qué:** los helpers deterministas de las Tasks 1-8 no cambian la conducta de la skill hasta que su procedimiento los invoca. Cubre la prosa de los ítems 1 (gate por `senales_gate`), 3 (desambiguación de nombre + verify de colisión), 4 (prohibir editar generados), 5 (fallback `ERROR_FILE_NOT_HYDRATED` → `rclone rcd`), 6 (precheck primario), 8 (columnas + índices por script), 7 (verify por CLI).

**Files:**
- Modify: `.claude/skills/organizar-sala-lectura/SKILL.md` (Pasos 2, 2.5→3, 4, 5, 6.5; sección "Qué produce"/manifiesto)

- [ ] **Step 1: Paso 2 — regla de desambiguación de `nombre_canonico`** (ítem 3, parte plan)

Al final del bloque de viñetas del Paso 2 (tras "**Bundle:**"), añadir:

```markdown
   - **Desambigua colisiones de nombre ANTES de persistir el plan:** si dos
     documentos derivan el MISMO `nombre_canonico` (misma fecha + misma
     descripción), añade sufijo `_2`/`_3` al segundo y siguientes. Una colisión
     no resuelta hace que una copia pise a otra en disco sin rastro; el verify
     del Paso 6.5 (`verificar()`) también la caza, pero es más barato evitarla aquí.
```

- [ ] **Step 2: Paso 2.5 — el gate lee `senales_gate`** (ítem 1)

Reemplazar el cuerpo del Paso 3 (gate condicional) para que las señales salgan del helper, no de la impresión del agente:

```markdown
3. **(Paso 2.5 — GATE condicional, por código).** Ejecuta
   `senales_gate(filas, wcode_caso, cobertura_filas)` (de
   `scripts/preclasificar.py`) sobre las filas propuestas, con `wcode_caso` = el
   W-code del caso (del nombre de la carpeta / `case_id`) y `cobertura_filas` =
   `_cobertura.json` de sala de máquina si existe. Detecta de forma determinista:
   W-code AJENO al caso (remedio por defecto: **excluir, nunca copiar** — no es
   de este expediente), casi-duplicado (mismo nombre de origen, sha256 distinto),
   binario opaco SIN espejo MD, y bundle sin parte (`requiere_identificar_parte`).
   - **Lista vacía → procede directo al Paso 4 sin esperar aprobación**, y deja
     constancia en el plan persistido (`estado: auto-aprobado, sin anomalías`).
   - **Lista NO vacía → presenta la propuesta** (tarjeta visual) con esas señales
     en el panel "Requiere tu visto bueno" y **espera confirmación**. Si piden
     ajustes, reclasifica y vuelve a presentar. Solo con OK explícito pasas al
     Paso 4. Es un chequeo de 1 segundo, no una impresión del agente: si
     `senales_gate` devuelve vacío, no inventes anomalías; si devuelve algo, no
     lo ignores.
```

- [ ] **Step 3: Paso 4 — precheck primario + fallback `ERROR_FILE_NOT_HYDRATED`** (ítems 6 y 5)

Reemplazar el Paso 4 por:

```markdown
4. **(tras OK) Copia+renombra.** Aplica solo a casos Drive-residentes (Modo 1/3);
   en **Modo 2 (local-nativo)** copia con `cp`/`shutil`. Decide la ruta de copia
   **por exit code, no leyendo documentación**: ejecuta
   `python scripts/precheck_rclone.py <remote>` (p. ej. `gdrive_tl:`).
   - **exit 0** (client OAuth propio del despacho) → ruta PRIMARIA: `rclone rcd`.
     `levantar_rcd_si_falta()` una vez, luego `copiar_manifiesto(remote, pares)`
     con TODAS las filas del plan persistido (Paso 2-bis) de una vez — el pacer
     de cuota se mantiene estable dentro del mismo proceso.
     `copiar_manifiesto` **aborta antes de tocar Drive** (`validar_pares`) si hay
     destinos duplicados: eso es una colisión de `nombre_canonico` sin resolver
     (vuelve al Paso 2, desambigua con `_2`/`_3`).
   - **exit != 0** (client compartido, o `rclone` no disponible) → copia
     secuencial server-side con `copy_path`/`cp` (más lenta, sin prerrequisito).
   - **`ERROR_FILE_NOT_HYDRATED` (fichero frío no hidratado):** NO lo anotes como
     pendiente a la primera. Reintenta ESE fichero vía `copiar_renombrar(remote,
     src, dst)` (RC API server-side, inmune al caché de hidratación local): en
     W-02VUDR esa ruta copió 3 ficheros atascados —incl. uno de 1,1 GB— en 19s.
     Solo si el reintento server-side también falla se anota pendiente en el
     `_MANIFIESTO.md`. Nunca se fuerza ni se fabrica un éxito.
   Al terminar, si `levantar_rcd_si_falta()` devolvió un `Popen` (lo arrancó esta
   corrida), ciérralo (`proc.terminate()`) para no dejar un rcd huérfano.
```

(Nota para el ejecutor: el fix de raíz del plugin `expedientes-xl` —re-stat en frío antes de devolver `ERROR_FILE_NOT_HYDRATED`— es una tarea aparte del plugin, fuera de este plan; anótalo en `docs/MEJORAS_FUTURAS.md` si aún no está.)

- [ ] **Step 4: Paso 5 — columnas del manifiesto + índices por script** (ítem 8)

Reemplazar el Paso 5 por:

```markdown
5. **Escribe SOLO el `_MANIFIESTO.md`, y deriva el resto por script.** El LLM ya
   no transcribe INDICE/CRONOLOGIA/YAML a mano.
   - `_MANIFIESTO.md` — tabla por documento, columnas (orden fijo):
     `sha256 | ruta_original | nombre_canonico | tipo | fecha | parte | parent_id | categoria | subcategoria_crm`.
     `categoria` = una de las 8 de `references/taxonomia_ev.md`; `subcategoria_crm`
     = lo que devuelva `subcategoria_crm(ruta)` (o vacío). `sha256` de los bytes
     (el `md5` de Drive NO sirve). Cabecera `<!-- GENERADO — NO EDITAR A MANO -->`.
   - `INDICE.md` y `CRONOLOGIA.md` → ejecuta
     `python scripts/indices_desde_manifiesto.py _MANIFIESTO.md <sala_dir>`
     (agrupa por categoría fecha DESC, sub-agrupa "07. RECLAMACIONES" por
     `subcategoria_crm`; cronología fecha ASC con `0000-00-00`/`(*)` al final).
   - `indice_documental.yaml` → ejecuta
     `python scripts/manifiesto_a_catalogo.py _MANIFIESTO.md indice_documental.yaml`.
   Los tres derivados llevan cabecera GENERADO; **no los edites a mano** (ver Paso 6.5).
```

- [ ] **Step 5: Paso 6.5 — verify por CLI + prohibición de editar generados** (ítems 7 y 4)

Reemplazar el Paso 6.5 por:

```markdown
6.5. **Verify determinista — falla ruidosamente, no resumas bonito.** Ejecuta
   `python scripts/verificar_sala.py <sala_dir> [--cobertura 01_Procesado/02_Sala de máquina/_cobertura.json]`
   (añade `--hash muestra` para contrastar sha origen↔copia de un 10%, o
   `--hash completo` si sospechas corrupción). El script parsea él mismo el
   `_MANIFIESTO.md` y lista el directorio — no ensambles a mano sus entradas.
   Exit 1 = hay problemas: NO sigas al Paso 7 con un reporte de éxito; lístalos.
   - **PROHIBIDO editar `_MANIFIESTO.md`/`INDICE.md`/`CRONOLOGIA.md`/
     `indice_documental.yaml` a mano para "hacer pasar" el verify.** La cabecera
     `GENERADO — NO EDITAR A MANO` es vinculante; toda corrección real se
     re-deriva volviendo a escribir el `_MANIFIESTO.md` y re-ejecutando los
     scripts del Paso 5.
   - Si el verify antepone `ATENCIÓN: N problemas homogéneos del tipo ...` (≥5 del
     mismo tipo), la hipótesis por defecto es **bug del check, no de los datos**:
     contrasta 2-3 filas a mano y PARA reportando al letrado, en vez de parchear
     N filas (modo de fallo más caro observado: 21 filas parcheadas a mano por un
     falso positivo).
```

- [ ] **Step 6: Actualizar la doc del manifiesto en "Qué produce"** (columnas nuevas)

En la sección de índices (dentro de "Qué produce" o donde se describa el `_MANIFIESTO.md`), reflejar que las columnas ahora incluyen `categoria | subcategoria_crm` y que INDICE/CRONOLOGIA/YAML se derivan por script (no a mano). Ajustar cualquier frase que diga que el LLM escribe los índices.

- [ ] **Step 7: Verificación manual + chequeo de skill**

- Re-leer el `SKILL.md` completo confirmando que: (a) el Paso 2.5 invoca `senales_gate`; (b) el Paso 4 decide por `precheck_rclone` y tiene el fallback `ERROR_FILE_NOT_HYDRATED`; (c) el Paso 5 lista las 9 columnas y ejecuta `indices_desde_manifiesto.py`; (d) el Paso 6.5 ejecuta `verificar_sala.py` y prohíbe editar generados.
- Run: `& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" scripts/check_skills.py` — confirmar que no aparece `organizar-sala-lectura` en "CHANGELOG sin actualizar" tras la Task 10 (en esta task el CHANGELOG aún no se tocó; el aviso es esperado hasta la Task 10).

- [ ] **Step 8: Commit**

```bash
git add ".claude/skills/organizar-sala-lectura/SKILL.md"
git commit -m "docs(sala-lectura): gate por senales_gate, precheck+fallback rcd, indices por script, verify CLI, prohibir editar generados"
```

---

### Task 10: Versión 1.11 + guard de sincronía frontmatter↔CHANGELOG + frescura del checkout

**Por qué:** el frontmatter (`1.9`) diverge del CHANGELOG (`1.10`); y en la pasada 2 un subagente corrió parcialmente v1.8 creyéndose v1.9 y se auto-reparó con `git checkout origin/main --` sobre la raíz git COMPARTIDA, arriesgando el trabajo de otra sesión concurrente. Ítem 2.

**Files:**
- Create: `tests/test_sala_lectura_version_changelog.py`
- Modify: `.claude/skills/organizar-sala-lectura/SKILL.md` (frontmatter `version` + Paso 0 frescura + gotcha de subagentes)
- Modify: `.claude/skills/organizar-sala-lectura/CHANGELOG.md` (entrada `1.11`)

**Interfaces:**
- Produces: test que compara el `version` del frontmatter con la primera entrada `## X.Y` del `CHANGELOG.md` de `organizar-sala-lectura` y falla si difieren.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_sala_lectura_version_changelog.py
"""Guard de sincronía: el `version` del frontmatter de organizar-sala-lectura
debe coincidir con la primera entrada del CHANGELOG. Motivo (backlog
robustez-velocidad ítem 2): el frontmatter quedó en 1.9 mientras el CHANGELOG
iba por 1.10 — un subagente corrió v1.8 creyéndose v1.9 (A/B invalidado).

Alcance intencionadamente acotado a esta skill: los CHANGELOG del resto del
despacho no usan un encabezado uniforme «## X.Y» (unos llevan fecha primero),
así que un guard repo-wide daría falsos positivos ajenos a este trabajo.
"""
from __future__ import annotations

import re
from pathlib import Path

_SKILL = Path(__file__).resolve().parent.parent / ".claude/skills/organizar-sala-lectura"


def _version_frontmatter() -> str:
    txt = (_SKILL / "SKILL.md").read_text(encoding="utf-8")
    m = re.search(r'^\s*version:\s*"?([0-9][0-9.]*)"?\s*$', txt, re.M)
    assert m, "no se encontró `version:` en el frontmatter"
    return m.group(1)


def _version_changelog() -> str:
    txt = (_SKILL / "CHANGELOG.md").read_text(encoding="utf-8")
    m = re.search(r'^##\s+([0-9][0-9.]*)\b', txt, re.M)
    assert m, "no se encontró un encabezado `## X.Y` en el CHANGELOG"
    return m.group(1)


def test_version_frontmatter_coincide_con_changelog():
    assert _version_frontmatter() == _version_changelog(), (
        f"frontmatter={_version_frontmatter()} != changelog={_version_changelog()} "
        "— actualiza ambos al mismo número")
```

- [ ] **Step 2: Confirmar que falla**

Run: `& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" -m pytest tests/test_sala_lectura_version_changelog.py -v`
Expected: FAIL — `frontmatter=1.9 != changelog=1.10`.

- [ ] **Step 3: Añadir la entrada `1.11` al CHANGELOG**

Al principio de `.claude/skills/organizar-sala-lectura/CHANGELOG.md` (reciente primero), tras la línea `# Changelog — organizar-sala-lectura`:

```markdown
## 1.11 — 2026-07-21
- **Señales del gate por código (`scripts/preclasificar.py::senales_gate`).** El
  gate condicional (Paso 2.5) deja de depender de comprobaciones mentales del
  agente: `senales_gate(filas, wcode_caso, cobertura_filas)` detecta de forma
  determinista W-code AJENO al caso (excluir, nunca copiar — falló en producción:
  un fichero de W-02X270 se copió a W-02VUDR), casi-duplicado (mismo nombre,
  sha256 distinto), binario opaco sin espejo MD y bundle sin parte. Lista vacía →
  auto-aprueba; no vacía → presenta y espera.
- **Verify determinista de extremo a extremo (`scripts/verificar_sala.py` CLI).**
  `python verificar_sala.py <sala_dir> [--cobertura ...] [--hash no|muestra|completo]`
  parsea él mismo el `_MANIFIESTO.md` (parser compartido) y lista el directorio —
  el mismo agente que clasifica ya no ensambla a mano lo que el check debe cazar.
  `verificar()` ahora detecta colisiones de `nombre_canonico` (el `set` las
  colapsaba y el verify pasaba verde — podía DESAPARECER un documento) y antepone
  un aviso si ≥5 problemas son del mismo tipo (sospecha del check, no de los
  datos: 21 filas se parchearon a mano por un falso positivo).
- **Prohibido editar artefactos generados para pasar el verify.** Paso 6.5: la
  cabecera `GENERADO — NO EDITAR` es vinculante; toda corrección se re-deriva.
- **`precheck_rclone.py` — prerrequisito OAuth por exit code, no por doc.** Un
  agente concluyó desde un doc archivado que no había client propio (falso; un
  comando de 1s lo confirmaba). Extrae SOLO `client_id` (nunca vuelca la config —
  `token`/`client_secret` en claro). exit 0 → `rcd` primario; 3 → copia secuencial.
- **Fallback `ERROR_FILE_NOT_HYDRATED` cableado (Paso 4).** Reintento automático
  de ese fichero vía `copiar_renombrar()` (server-side) antes de anotar pendiente;
  `copiar_manifiesto` aborta antes de tocar Drive (`validar_pares`) si hay destinos
  duplicados.
- **Columna `categoria` + `subcategoria_crm` en el `_MANIFIESTO.md` y el YAML;
  índices por script.** `indices_desde_manifiesto.py` deriva INDICE/CRONOLOGIA y el
  LLM deja de transcribir ~350 líneas por corrida; el catálogo YAML ya no omite la
  categoría por la que se construyó la sala (`CatalogEntry` gana `categoria`/
  `subcategoria_crm`). Parser del manifiesto compartido (`manifiesto_parser.py`).
- **Frescura del checkout + guard de versión (Paso 0 + test).** Frontmatter y
  CHANGELOG se validan en sincronía; Paso 0 aborta (no auto-repara) si el checkout
  git está desactualizado, y prohíbe `git checkout` sobre la raíz compartida.
```

- [ ] **Step 4: Bump del frontmatter a 1.11**

En `.claude/skills/organizar-sala-lectura/SKILL.md`, frontmatter:

```yaml
  version: "1.11"
```

- [ ] **Step 5: Confirmar que el guard pasa**

Run: `& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" -m pytest tests/test_sala_lectura_version_changelog.py -v`
Expected: PASS (`frontmatter=1.11 == changelog=1.11`).

- [ ] **Step 6: Paso 0 — frescura del checkout + prohibir auto-reparación sobre la raíz compartida**

En `SKILL.md`, al inicio del Paso 0 (antes de la elección de modo), añadir:

```markdown
   - **Frescura (solo si la skill se ejecuta desde un checkout git del repo —
     Claude Code local, no el `.skill` importado en Cowork):** antes de leer el
     resto del procedimiento, verifica que tu copia está al día:
     `git fetch origin main --quiet && git diff --quiet origin/main HEAD -- .claude/skills/organizar-sala-lectura/`.
     Si difiere, **ABORTA y avisa** ("la skill local está desactualizada respecto
     a origin/main; actualiza tu rama antes de correrla"). **NUNCA auto-repares
     con `git checkout origin/main -- .claude/skills/...` sobre la raíz git
     compartida:** otra sesión concurrente puede tener trabajo sin commitear ahí y
     lo pisarías (pasó en la pasada 2 de W-02VUDR). Actualizar la rama es decisión
     del humano, no de la skill.
```

- [ ] **Step 7: Gotcha de subagentes — frescura antes de leer SKILL.md**

En el gotcha "Casos grandes (>80 ficheros): reparte la clasificación por fuente en subagentes paralelos", añadir al final:

```markdown
  Cada subagente **verifica frescura ANTES de leer `SKILL.md`** (misma comprobación
  del Paso 0); si está desactualizado respecto a `origin/main`, **para y avisa** —
  nunca corre una versión mezclada ni auto-repara con `git checkout` sobre la raíz
  compartida (en la pasada 2 un subagente corrió parcialmente v1.8 creyéndose v1.9
  e invalidó el A/B).
```

- [ ] **Step 8: Re-empaquetar el `.skill` + confirmar check_skills limpio**

Run:
```bash
& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" scripts/package_skill.py .claude/skills/organizar-sala-lectura dist/skills
& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" scripts/check_skills.py
```
Expected: `organizar-sala-lectura` NO aparece en "CHANGELOG sin actualizar" ni en ".skill caducado". (El re-import del `.skill` en Cowork queda como paso manual posterior.)

- [ ] **Step 9: Commit**

```bash
git add tests/test_sala_lectura_version_changelog.py ".claude/skills/organizar-sala-lectura/SKILL.md" ".claude/skills/organizar-sala-lectura/CHANGELOG.md" dist/skills/organizar-sala-lectura.skill
git commit -m "feat(sala-lectura): version 1.11 + guard frontmatter/CHANGELOG + Paso 0 frescura del checkout"
```

---

### Task 11: Suite completa verde + actualizar `PLAN.md`

**Files:**
- Modify: `PLAN.md` (marcar el estado del backlog de 16 en `[SIGUIENTE-PRECLASIFICACION-SALA-LECTURA]`)

- [ ] **Step 1: Correr la suite completa (conteo por junit-xml)**

Run:
```bash
& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" -m pytest -q --junit-xml=.pytest-junit.xml
```
Expected: 0 failed, 0 errors. Anotar el nuevo total (previo + los tests añadidos en Tasks 1-10).

- [ ] **Step 2: Marcar el estado en `PLAN.md`**

En `PLAN.md`, bajo `[SIGUIENTE-PRECLASIFICACION-SALA-LECTURA]`, anotar qué ítems del backlog de 16 quedaron HECHOS (ítems 1-8, prioridad alta, con el hash del PR una vez mergeado) y cuáles quedan PENDIENTES (ítems 9-16, media/baja), con puntero al plan TDD `docs/superpowers/plans/2026-07-21-robustez-velocidad-sala-lectura-tdd.md`.

- [ ] **Step 3: Commit**

```bash
git add PLAN.md
git commit -m "docs(plan): backlog robustez sala-lectura — 8 items alta hechos, 9-16 pendientes"
```

---

## Auto-revisión

**Cobertura de los 8 ítems de prioridad alta:**
- Ítem 1 (señales del gate por código incl. W-code ajeno) → Task 7 (`senales_gate`) + Task 9 Step 2 (Paso 2.5).
- Ítem 2 (frescura del checkout + versión 1.10/1.11 + prohibir auto-reparación) → Task 10 (guard + frontmatter + CHANGELOG + Paso 0 + gotcha subagentes).
- Ítem 3 (colisiones de `nombre_canonico` antes de copiar y en verify) → Task 4 (verify) + Task 6 (`validar_pares`) + Task 9 Step 1 (Paso 2 desambiguación).
- Ítem 4 (prohibir editar generados + aviso de fallos homogéneos) → Task 4 (código homogéneo) + Task 9 Step 5 (Paso 6.5 prohibición).
- Ítem 5 (fallback `ERROR_FILE_NOT_HYDRATED` → rcd) → Task 9 Step 3 (Paso 4); reusa `copiar_renombrar` existente; fix de raíz del plugin anotado como fuera de alcance.
- Ítem 6 (`precheck_rclone.py` determinista) → Task 8 + Task 9 Step 3 (Paso 4 precheck primario).
- Ítem 7 (CLI de `verificar_sala.py`) → Task 5 (+ Task 1 parser compartido) + Task 9 Step 5 (Paso 6.5).
- Ítem 8 (columna `categoria` + índices por script) → Task 1 (parser) + Task 2 (columnas + YAML + `CatalogEntry`) + Task 3 (`indices_desde_manifiesto.py`) + Task 9 Step 4 (Paso 5).

**Placeholders:** ninguno — código completo y ejecutable en Tasks 1-8 y 10; Tasks 9 y 11 son inserciones de texto exactas + comandos.

**Consistencia de tipos:** `parse_manifiesto(texto)->list[dict]` (Task 1) consumido idéntico por Tasks 2/3/5. `verificar(filas, ficheros_en_disco, cobertura_filas=None)->list[str]` conserva firma (Task 4 no la rompe; Task 5 la invoca). `senales_gate(filas, wcode_caso, cobertura_filas=None)->list[str]` (Task 7). `precheck(remote)->int` (Task 8). `validar_pares(pares)->None` lanza `ValueError` (Task 6).

**Fuera de alcance (no se fuerzan, quedan para 3ª sesión):** ítems 9-16 (prioridad media/baja) del backlog, incluida la telemetría de fases (ítem 16) y el fix de raíz del plugin `expedientes-xl` para `ERROR_FILE_NOT_HYDRATED`.

**Decisión de versión:** el backlog (ítem 2) pedía subir el frontmatter a 1.10 para casar con el CHANGELOG; como esta sesión añade features sustanciales, se estrena **1.11** (frontmatter + entrada nueva de CHANGELOG), y el guard nuevo garantiza que no vuelvan a divergir. Cumple el intento real del ítem (guard anti-drift) y versiona honestamente el trabajo.

**Guard de versión — alcance acotado:** el test compara solo `organizar-sala-lectura` porque los CHANGELOG del resto del despacho no usan encabezado uniforme `## X.Y` (varios llevan fecha primero) y un guard repo-wide daría falsos positivos ajenos a este trabajo.
