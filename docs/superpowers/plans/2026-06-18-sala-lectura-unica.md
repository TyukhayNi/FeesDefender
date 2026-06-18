# Sala de lectura única (plana, una skill) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unificar las dos salas de lectura en UNA sola, **plana**, alimentada por la skill `organizar-sala-lectura` ampliada a **todo `00_Input`**; con catálogo SSOT derivado por helper, taxonomía DRY desde el canon, y deprecación del camino de sala del core.

**Architecture:** La skill (prompt-driven, Cowork/local) clasifica leyendo contenido y escribe `01_Procesado/Sala lectura/` PLANA (`AAAA-MM-DD_descripcion.ext`; compuestos = subcarpeta fechada) + `_MANIFIESTO.md`. Un helper Python determinista deriva `indice_documental.yaml` del manifiesto. La taxonomía/criterios viven en un canon (`core/config.py::TAXONOMIA_EV` + `data/_prompts/clasificador_ev.md`) y se generan a la skill con `sync_taxonomia_skills.py`, con gate anti-drift en `check_skills.py`. El pipeline confidencial (extractor→MD→anon→frontier) NO se toca; el camino de sala del core se deprecna.

**Tech Stack:** Python 3 (stdlib + `pyyaml`), pytest, Windows/PowerShell, UTF-8 sin BOM. Skills markdown + `scripts/package_skill.py`/`validate_skills.py`/`check_skills.py`. Spec: `docs/superpowers/specs/2026-06-18-sala-lectura-unica-design.md`.

**Regla de concurrencia:** working tree compartido en `main`. Commits ACOTADOS (nunca `add -A`). `PLAN.md`/`STATUS.md` arrastran cambios ajenos → tocarlos solo en el `/cierre`, acotando.

---

## Fase 1 — Canon de criterios + DRY de taxonomía + gate anti-drift

### Task 1: Canon de criterios `clasificador_ev.md`

**Files:**
- Create: `data/_prompts/clasificador_ev.md`

- [ ] **Step 1: Escribir el canon** (fuente única de criterios; la lista de 8 categorías sigue siendo `core/config.py::TAXONOMIA_EV`, este doc añade enrutado PBC-por-parte + jerarquía de fecha + naming)

```markdown
# Criterio de clasificación E&V — canon (fuente única)

> Canon consumido por `scripts/sync_taxonomia_skills.py` para generar la sección
> de clasificación de las skills. NO editar la copia generada en las skills; editar
> aquí. La lista cerrada de categorías vive en `core/config.py::TAXONOMIA_EV`.

## Enrutado de identidad / PBC POR PARTE
La identidad/PBC NO va toda a `06. PBC`. Se enruta por la parte, decidida LEYENDO el doc:
- Lado VENDEDOR (nota mercantil, nota simple/titularidad, titular real, poderes del
  vendedor, catastro) → `01. ACTIVACIÓN`.
  - EXCEPCIÓN: Anexos 1 y 2 de los vendedores (anexos PBC/KYC formales de E&V) → `06. PBC`.
- Lado COMPRADOR (identidad/KYC de compradores) → `03. OFERTAS` (subcarpeta por oferta si hay varias).

## Jerarquía de fecha del documento
(a) otorgamiento/firma en el cuerpo → (b) otra fecha inequívoca del contenido →
(c) fecha del nombre del fichero → (d) `0000-00-00`.
`mtime` NO es fuente; si se usa como aproximación, marcar `(*)` en CRONOLOGIA y _MANIFIESTO.

## Regla de ambigüedad
Lo ambiguo o ilegible → `08. PENDIENTE DE CLASIFICAR`. NUNCA forzar a otra categoría.

## Nombre canónico
`AAAA-MM-DD_descripcion.ext` — `descripcion`: ≤50 car., minúsculas, **guiones_bajos**,
SIN PII (sin nombres, DNI/NIE, direcciones). Describe el documento, no a las partes.
El tipo NO va en el nombre (la categoría vive en `INDICE.md`, no en carpetas).
```

- [ ] **Step 2: Commit**

```bash
git add data/_prompts/clasificador_ev.md
git commit -m "feat(canon): clasificador_ev.md — criterio único de clasificación E&V (PBC por parte + fecha + naming)"
```

### Task 2: Generador `sync_taxonomia_skills.py`

**Files:**
- Create: `scripts/sync_taxonomia_skills.py`
- Test: `tests/test_sync_taxonomia_skills.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_sync_taxonomia_skills.py
from __future__ import annotations
import importlib


def test_genera_taxonomia_con_las_8_categorias(tmp_path, monkeypatch):
    import scripts.sync_taxonomia_skills as sync
    importlib.reload(sync)
    from core.config import TAXONOMIA_EV

    out = tmp_path / "taxonomia_ev.md"
    sync.generar(out)
    texto = out.read_text(encoding="utf-8")
    for cat in TAXONOMIA_EV:
        assert cat in texto                      # las 8 categorías del canon
    assert "POR PARTE" in texto                  # enrutado PBC del canon
    assert "guiones_bajos" in texto              # naming del canon
    assert "GENERADO" in texto.upper()           # cabecera no-editar


def test_idempotente(tmp_path):
    import scripts.sync_taxonomia_skills as sync
    out = tmp_path / "t.md"
    sync.generar(out)
    a = out.read_text(encoding="utf-8")
    sync.generar(out)
    assert out.read_text(encoding="utf-8") == a  # misma salida, sin drift
```

- [ ] **Step 2: Verificar que falla**

Run: `python -m pytest tests/test_sync_taxonomia_skills.py -q`
Expected: FAIL (`ModuleNotFoundError: scripts.sync_taxonomia_skills`).

- [ ] **Step 3: Implementar el generador**

```python
# scripts/sync_taxonomia_skills.py
"""Genera la referencia de taxonomía de las skills desde el canon.

Fuente: core/config.py::TAXONOMIA_EV (lista cerrada) + data/_prompts/clasificador_ev.md
(enrutado PBC por parte + jerarquía de fecha + naming). Destino: la copia en cada skill
(p. ej. .claude/skills/organizar-sala-lectura/references/taxonomia_ev.md). NO editar la
copia a mano: edita el canon y re-genera. El gate de check_skills detecta el drift.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.config import TAXONOMIA_EV  # noqa: E402

_CANON = ROOT / "data" / "_prompts" / "clasificador_ev.md"
# Skills cuya referencia de taxonomía se sincroniza desde el canon.
DESTINOS = [
    ROOT / ".claude" / "skills" / "organizar-sala-lectura" / "references" / "taxonomia_ev.md",
]


def _render() -> str:
    cats = "\n".join(f"- `{c}`" for c in TAXONOMIA_EV)
    canon = _CANON.read_text(encoding="utf-8")
    return (
        "<!-- GENERADO desde data/_prompts/clasificador_ev.md + core/config.py::TAXONOMIA_EV "
        "por scripts/sync_taxonomia_skills.py — NO EDITAR A MANO -->\n\n"
        "# Taxonomía E&V + criterio de clasificación (generado)\n\n"
        "## Las categorías (set cerrado = `TAXONOMIA_EV`)\n\n"
        f"{cats}\n\n"
        "(No existe el `02`; se respeta la numeración de E&V.)\n\n"
        f"{canon}"
    )


def generar(destino: Path) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(_render(), encoding="utf-8")
    return destino


def main() -> int:
    for d in DESTINOS:
        generar(d)
        print(f"taxonomía sincronizada → {d.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Verificar que pasa**

Run: `python -m pytest tests/test_sync_taxonomia_skills.py -q`
Expected: PASS.

- [ ] **Step 5: Generar la referencia real y revisar el diff**

Run: `python scripts/sync_taxonomia_skills.py`
Expected: reescribe `.claude/skills/organizar-sala-lectura/references/taxonomia_ev.md` con la cabecera GENERADO, las 8 categorías y el canon. Revisar el diff (debe perder el framing «carpetas por categoría» y el kebab-case).

- [ ] **Step 6: Commit**

```bash
git add scripts/sync_taxonomia_skills.py tests/test_sync_taxonomia_skills.py ".claude/skills/organizar-sala-lectura/references/taxonomia_ev.md"
git commit -m "feat(skills): sync_taxonomia_skills — genera la taxonomía de la skill desde el canon (DRY)"
```

### Task 3: Gate anti-drift de taxonomía en `check_skills.py`

**Files:**
- Modify: `scripts/check_skills.py` (añadir un check; integrarlo en `report()`)
- Test: `tests/test_check_skills_taxonomia.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_check_skills_taxonomia.py
from __future__ import annotations
import importlib


def test_detecta_drift_de_taxonomia(tmp_path, monkeypatch):
    import scripts.check_skills as cs
    importlib.reload(cs)
    import scripts.sync_taxonomia_skills as sync

    destino = tmp_path / "taxonomia_ev.md"
    sync.generar(destino)
    # Sin drift: la copia coincide con lo que generaría el canon
    assert cs.taxonomia_drift([destino]) == []
    # Con drift: alguien editó la copia a mano
    destino.write_text(destino.read_text(encoding="utf-8") + "\nDRIFT\n", encoding="utf-8")
    assert destino.name in " ".join(cs.taxonomia_drift([destino]))
```

- [ ] **Step 2: Verificar que falla**

Run: `python -m pytest tests/test_check_skills_taxonomia.py -q`
Expected: FAIL (`AttributeError: module 'scripts.check_skills' has no attribute 'taxonomia_drift'`).

- [ ] **Step 3: Implementar el check** (añadir a `scripts/check_skills.py`)

```python
def taxonomia_drift(destinos=None) -> list[str]:
    """Devuelve los destinos cuya taxonomía generada NO coincide con la copia en disco
    (alguien editó la copia a mano en vez del canon). Aviso, no bloqueante."""
    import scripts.sync_taxonomia_skills as sync
    objetivos = destinos if destinos is not None else sync.DESTINOS
    drift: list[str] = []
    esperado_por = {}
    for d in objetivos:
        from pathlib import Path
        d = Path(d)
        actual = d.read_text(encoding="utf-8") if d.exists() else None
        # Generar en un temporal hermano para comparar sin tocar el real
        tmp = d.with_suffix(d.suffix + ".sync_check")
        sync.generar(tmp)
        esperado = tmp.read_text(encoding="utf-8")
        tmp.unlink()
        if actual != esperado:
            drift.append(str(d))
    return drift
```

E integrar en `report()` (junto a los avisos existentes de CHANGELOG/`.skill` caducado):

```python
    tax_drift = taxonomia_drift()
    if tax_drift:
        print("AVISO taxonomía desincronizada (corre scripts/sync_taxonomia_skills.py):")
        for d in tax_drift:
            print(f"  - {d}")
```

- [ ] **Step 4: Verificar que pasa**

Run: `python -m pytest tests/test_check_skills_taxonomia.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/check_skills.py tests/test_check_skills_taxonomia.py
git commit -m "feat(check_skills): gate anti-drift de taxonomía canon↔skill (modo aviso)"
```

---

## Fase 2 — Helper manifiesto → catálogo (SSOT)

### Task 4: `manifiesto_a_catalogo.py` (bundled en la skill, self-contained)

**Files:**
- Create: `.claude/skills/organizar-sala-lectura/scripts/manifiesto_a_catalogo.py`
- Test: `tests/test_manifiesto_a_catalogo.py`

Contrato del `_MANIFIESTO.md` (tabla markdown con cabecera fija):

```
| sha256 | ruta_original | nombre_canonico | tipo | fecha | parte | parent_id |
|---|---|---|---|---|---|---|
| <hex64> | 01_Drive EV/Catastro.pdf | 2024-04-26_catastro.pdf | 08. PENDIENTE DE CLASIFICAR | 2024-04-26 | propietario |  |
```

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_manifiesto_a_catalogo.py
from __future__ import annotations
import importlib.util
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
HELPER = ROOT / ".claude" / "skills" / "organizar-sala-lectura" / "scripts" / "manifiesto_a_catalogo.py"


def _load():
    spec = importlib.util.spec_from_file_location("manifiesto_a_catalogo", HELPER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_MANIF = """<!-- GENERADO — NO EDITAR A MANO -->
| sha256 | ruta_original | nombre_canonico | tipo | fecha | parte | parent_id |
|---|---|---|---|---|---|---|
| aaaa | 01_Drive EV/Catastro.pdf | 2024-04-26_catastro.pdf | 08. PENDIENTE DE CLASIFICAR | 2024-04-26 | propietario |  |
| bbbb | 04_Manual/RESPUESTA_RESOLUCION.pdf | 2025-07-22_requerimiento.pdf | 07. RECLAMACIONES | 2025-07-22 | propietario |  |
"""


def test_deriva_catalogo_yaml(tmp_path):
    mod = _load()
    (tmp_path / "_MANIFIESTO.md").write_text(_MANIF, encoding="utf-8")
    out = mod.derivar(tmp_path / "_MANIFIESTO.md", tmp_path / "indice_documental.yaml")
    data = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert len(data) == 2
    e0 = {d["hash"]: d for d in data}["aaaa"]
    assert e0["nombre_original"] == "Catastro.pdf"
    assert e0["fuente"] == "drive_ev"
    assert e0["tipo_documental"] == "08. PENDIENTE DE CLASIFICAR"
    assert e0["fecha_doc"] == "2024-04-26"
    assert e0["parte"] == "propietario"
    assert e0["estado"] == "original"


def test_campos_coinciden_con_CatalogEntry():
    """Anti-drift: los campos que emite el helper existen en core.CatalogEntry."""
    import dataclasses
    from core.catalogo_documental import CatalogEntry
    mod = _load()
    validos = {f.name for f in dataclasses.fields(CatalogEntry)}
    assert set(mod.CAMPOS_EMITIDOS) <= validos


def test_idempotente(tmp_path):
    mod = _load()
    (tmp_path / "_MANIFIESTO.md").write_text(_MANIF, encoding="utf-8")
    o = tmp_path / "indice_documental.yaml"
    mod.derivar(tmp_path / "_MANIFIESTO.md", o)
    a = o.read_text(encoding="utf-8")
    mod.derivar(tmp_path / "_MANIFIESTO.md", o)
    assert o.read_text(encoding="utf-8") == a
```

- [ ] **Step 2: Verificar que falla**

Run: `python -m pytest tests/test_manifiesto_a_catalogo.py -q`
Expected: FAIL (no existe el helper).

- [ ] **Step 3: Implementar el helper** (self-contained; NO importa `core`)

```python
# .claude/skills/organizar-sala-lectura/scripts/manifiesto_a_catalogo.py
"""Deriva indice_documental.yaml (SSOT) del _MANIFIESTO.md que escribe la skill.

Determinista, idempotente. Self-contained (corre en Cowork sin core/). El test del
repo verifica que CAMPOS_EMITIDOS ⊆ core.catalogo_documental.CatalogEntry (anti-drift).
El LLM NO escribe YAML: lo escribe este helper.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

# Mapeo fuente: prefijo de ruta en 00_Input → etiqueta de fuente del catálogo.
_SOURCE_MAP = {
    "01_Drive EV": "drive_ev", "02_Whatsapp": "whatsapp", "03_Email": "email",
    "04_Manual": "manual", "05_CRM": "crm", "06_Entrevistas": "entrevistas",
}
# Columnas del _MANIFIESTO.md (orden fijo).
_COLS = ["sha256", "ruta_original", "nombre_canonico", "tipo", "fecha", "parte", "parent_id"]
# Campos que el helper escribe en el catálogo (subconjunto de CatalogEntry).
CAMPOS_EMITIDOS = [
    "id_doc", "ruta_relativa", "nombre_original", "tipo_documental", "fecha_doc",
    "parte", "fuente", "estado", "hash", "parent_id", "nombre_canonico",
]


def _fuente(ruta_rel: str) -> str:
    top = ruta_rel.replace("\\", "/").split("/", 1)[0]
    return _SOURCE_MAP.get(top, "manual")


def _parse_filas(texto: str) -> list[dict]:
    filas = []
    for line in texto.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        celdas = [c.strip() for c in s.strip("|").split("|")]
        if len(celdas) != len(_COLS):
            continue
        if celdas[0] == "sha256" or set(celdas[0]) <= {"-"}:
            continue
        filas.append(dict(zip(_COLS, celdas)))
    return filas


def derivar(manifiesto: Path, salida: Path) -> Path:
    filas = _parse_filas(Path(manifiesto).read_text(encoding="utf-8"))
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


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("uso: manifiesto_a_catalogo.py <_MANIFIESTO.md> <indice_documental.yaml>")
        return 2
    derivar(Path(argv[1]), Path(argv[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 4: Verificar que pasa**

Run: `python -m pytest tests/test_manifiesto_a_catalogo.py -q`
Expected: PASS (incluido `test_campos_coinciden_con_CatalogEntry`).

- [ ] **Step 5: Commit**

```bash
git add ".claude/skills/organizar-sala-lectura/scripts/manifiesto_a_catalogo.py" tests/test_manifiesto_a_catalogo.py
git commit -m "feat(skill): manifiesto_a_catalogo — deriva indice_documental.yaml del _MANIFIESTO.md (SSOT, self-contained)"
```

---

## Fase 3 — Reescribir la skill `organizar-sala-lectura` (plana, todo 00_Input)

> Tareas de prompt: el «test» es `validate_skills`/`check_skills` + la corrida real en Cowork (Task 10). Cada edit es de contenido concreto.

### Task 5: Frontmatter, alcance y estructura plana en `SKILL.md`

**Files:**
- Modify: `.claude/skills/organizar-sala-lectura/SKILL.md`

- [ ] **Step 1: Frontmatter + nota de modelo** — `version: "1.3"`; `description` reescrita: lee **todo `00_Input`** (no solo `01_Drive EV`), copia a `01_Procesado/Sala lectura/` (sin "Drive EV"), **plana** con nombre `AAAA-MM-DD_descripcion`. Mantener los `NO se activa cuando` (triaje/viabilidad). Añadir en el cuerpo (§Autonomía o §Cuándo se activa) una **nota de uso de modelo**: «Ejecútese con Sonnet o Haiku (clasificación atómica + visto bueno humano); **no requiere Opus**. El grueso de la velocidad lo da el skip incremental por sha256.»

- [ ] **Step 2: §"Entrada y montaje"** — sustituir "Lee de `00_Input/01_Drive EV/`. Las demás fuentes … fuera de alcance" por: **"Lee de TODO `00_Input/` (`01_Drive EV`, `02_Whatsapp`, `03_Email`, `04_Manual`, `05_CRM`, `06_Entrevistas`), excluyendo `90_Notas personales`."** Escribe en `01_Procesado/Sala lectura/`.

- [ ] **Step 3: §"Qué produce"** — reemplazar el árbol por categorías por el árbol **PLANO**:

```
<Expediente (Drive del despacho)>/
├── 00_Input/                       ← crudo (todas las fuentes), NO se toca
└── 01_Procesado/
    └── Sala lectura/
        ├── INDICE.md · CRONOLOGIA.md · _MANIFIESTO.md · indice_documental.yaml
        ├── AAAA-MM-DD_descripcion.ext                 (documento suelto)
        └── AAAA-MM-DD_descripcion/                    (documento compuesto)
            ├── AAAA-MM-DD_descripcion.ext             (principal)
            └── AAAA-MM-DD_descripcion_anexo_N_x.ext   (anexos)
```

- [ ] **Step 4: Validar**

Run: `python scripts/validate_skills.py` y `python scripts/check_skills.py`
Expected: sin errores nuevos (avisos de CHANGELOG esperables hasta Task 9).

- [ ] **Step 5: Commit**

```bash
git add ".claude/skills/organizar-sala-lectura/SKILL.md"
git commit -m "feat(skill): organizar-sala-lectura v1.3 — alcance todo 00_Input + salida plana (WIP)"
```

### Task 6: Procedimiento (Paso 0 conector/URL/permiso; clasificación; bundles; fecha; índices+catálogo)

**Files:**
- Modify: `.claude/skills/organizar-sala-lectura/SKILL.md` (§Procedimiento, §Propuesta visual, §Re-aplicación, §Gotchas)

- [ ] **Step 1: Añadir Paso 0 (bloqueante)** antes del actual paso 1:

```markdown
0. **Montaje (bloqueante).** Carga el conector de Drive (ToolSearch). Acepta una URL de
   carpeta pegada en el chat: resuelve `folderId` y DETECTA nivel — si la URL es la raíz
   del expediente, baja a `00_Input/`; si ya es una subcarpeta de `00_Input`, úsala.
   Pide activar **"Permitir siempre"** en el conector de Drive (CERO diálogos durante la
   ejecución). Disparador: "organiza esta carpeta <url>".
```

- [ ] **Step 2: Reescribir paso 1-2 (recogida + clasificación)** — listar **todo `00_Input`** (excl. `90_Notas personales`); clasificar leyendo contenido con `references/taxonomia_ev.md` (categoría, **PBC por parte**, ambiguo→`08`); **fecha por la jerarquía del canon** (cuerpo→contenido→nombre→`0000-00-00`; `mtime` solo aprox. marcada `(*)`); `sha256` de los bytes; detectar **bundles** (§nueva).

- [ ] **Step 3: Añadir §"Documentos compuestos (bundles)"**:

```markdown
## Documentos compuestos (bundles)
Un documento con anexos = una SUBCARPETA fechada con el principal + sus anexos. Se
agrupan SOLO con señal determinista:
- WhatsApp: chat + su `media/` (estructura del export).
- Email `.eml`: cuerpo (principal) + adjuntos MIME.
- CRM: clúster por subida en lote (mejor esfuerzo; desde Cowork puede degradarse a plano).
- Sueltos (Drive/Manual): solo si hay convención `_anexo_N` o un PDF troceado; si no → plano.
Nombre: carpeta `AAAA-MM-DD_descripcion/`; principal `AAAA-MM-DD_descripcion.ext`; anexos
`AAAA-MM-DD_descripcion_anexo_N_x.ext`. `parent_id`/`orden` van al `_MANIFIESTO.md`.
```

- [ ] **Step 4: Reescribir paso 4 (ejecución) a PLANO** — copiar cada fichero a
  `01_Procesado/Sala lectura/` (raíz) con nombre `AAAA-MM-DD_descripcion.ext` (descripción
  con **guiones_bajos**, sin PII); los compuestos a su subcarpeta fechada. **Guarda de
  colisión:** si el nombre destino ya se usó en la corrida, sufijo `_2`/`_3`.

- [ ] **Step 5: Reescribir paso 5 (índices) + paso nuevo de catálogo**:

```markdown
5. **Escribe en `01_Procesado/Sala lectura/`:**
   - `_MANIFIESTO.md` — tabla: `sha256 | ruta_original | nombre_canonico | tipo | fecha | parte | parent_id`. Cabecera "GENERADO — NO EDITAR".
   - `INDICE.md` — agrupado **por categoría** (la categoría vive aquí, no en carpetas),
     orden **fecha DESCENDENTE**; cada entrada enlaza a la copia plana + nombre original.
   - `CRONOLOGIA.md` — por fecha ASCENDENTE; `0000-00-00`/`(*)` al final.
6. **Deriva el catálogo:** ejecuta `scripts/manifiesto_a_catalogo.py _MANIFIESTO.md indice_documental.yaml`
   (el LLM NO escribe el YAML). Es la SSOT máquina.
7. **Reporta:** nº por categoría, nº a `08. PENDIENTE`, bundles, duplicados saltados.
```

- [ ] **Step 6: Actualizar §"Propuesta visual"** — orden **fecha descendente**; quitar el
  agrupado por carpeta-tipo (ahora la categoría es etiqueta, no carpeta); mantener panel
  "Requiere tu visto bueno" (reclasificaciones, PBC por parte, bundles propuestos,
  duplicados sha, sin fecha, `08` con motivo).

- [ ] **Step 7: Actualizar §"Gotchas"** — quitar "Solo `01_Drive EV`" y la nota de
  "colisión con el motor local" (el motor de sala se deprecna, Task 8); añadir "estructura
  plana: la categoría vive en `INDICE.md`, no en carpetas"; conservar PBC-por-parte, sha256, sin-PII.

- [ ] **Step 8: Validar**

Run: `python scripts/validate_skills.py`
Expected: sin errores.

- [ ] **Step 9: Commit**

```bash
git add ".claude/skills/organizar-sala-lectura/SKILL.md"
git commit -m "feat(skill): organizar-sala-lectura v1.3 — Paso 0, bundles, fecha-cuerpo, índices+catálogo plano"
```

---

## Fase 4 — Repuntar `triaje-viabilidad` a `00_Input`

### Task 7: Entrada de triaje → `00_Input` directo

**Files:**
- Modify: `.claude/skills/triaje-viabilidad/SKILL.md`

- [ ] **Step 1: Localizar la referencia** a `02_Sala lectura/` (y cualquier "Sala lectura")
  en `SKILL.md` (buscar `02_Sala lectura` / `Sala lectura`).

- [ ] **Step 2: Reescribir la "Entrada"** para que lea **`00_Input/` directo** (todas las
  fuentes, como `viabilidad-prerelleno`), **no** la sala. El triaje busca sus 6 factores
  (encargo firmado, nexo causal, obligado al pago, prueba de la intermediación, importe/base,
  prescripción) por **lectura dirigida** del contenido; **no hereda** la clasificación de la
  sala (un doc mal clasificado a `08. PENDIENTE` no debe escaparse del dictamen). Texto a
  incorporar:

```markdown
## Entrada
Lee `00_Input/` del expediente (todas las fuentes), igual que `viabilidad-prerelleno`.
La fuente de verdad es el crudo: el triaje localiza sus factores leyendo el contenido,
sin depender de la clasificación de la sala de lectura. **Opcional:** si existe
`01_Procesado/Sala lectura/INDICE.md`, úsalo solo como **pista de navegación** (atajo para
encontrar candidatos), pero verifica siempre contra `00_Input`. NO requiere haber corrido
`organizar-sala-lectura` antes.
```

- [ ] **Step 3: Quitar/ajustar** cualquier instrucción que dijera "si la sala no existe,
  corre organizar-sala-lectura" (ya no es prerrequisito). No fusionar con `viabilidad-prerelleno`.

- [ ] **Step 4: Validar**

Run: `python scripts/validate_skills.py`
Expected: sin errores.

- [ ] **Step 5: Commit**

```bash
git add ".claude/skills/triaje-viabilidad/SKILL.md"
git commit -m "fix(skill): triaje-viabilidad lee 00_Input directo (no hereda clasificación de la sala)"
```

---

## Fase 5 — Deprecación del camino de sala del core

### Task 8: Marcar deprecado el core de sala + quitar el paso `catalogo.build`

**Files:**
- Modify: `core/sala_lectura.py` (banner de módulo deprecado)
- Modify: `core/pipeline.py` (quitar el paso `catalogo.build`)
- Test: `tests/test_pipeline.py` (actualizar la expectativa del paso)

- [ ] **Step 1: Banner de deprecación** al inicio del docstring de `core/sala_lectura.py`:

```python
"""[DEPRECADO 2026-06-18] El camino de sala de lectura del motor (clasificar_caso/
aplicar_clasificacion/render_indices/poblar_sala_lectura/clasificar_residuo_llm) queda
SUPERSEDIDO por la skill `organizar-sala-lectura` (sala única plana sobre todo 00_Input;
ver docs/superpowers/specs/2026-06-18-sala-lectura-unica-design.md). No ampliar; se
conserva temporalmente. El pipeline confidencial (extractor/MD/anon) NO depende de esto.
"""
```
(Mantener el docstring existente debajo.)

- [ ] **Step 2: Actualizar el test del pipeline** — el paso `catalogo.build` se elimina.
  En `tests/test_pipeline.py::test_pipeline_construye_catalogo`: convertirlo en
  `test_pipeline_no_construye_catalogo` que asserta que **NO** existe el paso
  `catalogo.build` en `pr.steps`.

```python
def test_pipeline_no_construye_catalogo(tmp_casos_root, monkeypatch):
    from core import pipeline
    import importlib; importlib.reload(pipeline)
    monkeypatch.setattr(pipeline.case_manager, "ensure_case", lambda *a, **k: None)
    monkeypatch.setattr(pipeline.inventory, "scan", lambda *a, **k: 0)
    monkeypatch.setattr(pipeline.extractor, "extract_all", lambda *a, **k: [])
    monkeypatch.setattr(pipeline.markdown_generator, "build", lambda *a, **k: [])
    monkeypatch.setattr(pipeline.scorer, "score", lambda *a, **k: None)
    monkeypatch.setattr(pipeline.viability, "analyze", lambda *a, **k: None)
    monkeypatch.setattr(pipeline.linker, "crosslink", lambda *a, **k: 0)
    pr = pipeline.run("EV-2026-TEST", do_sync=False, do_demanda=False)
    assert "catalogo.build" not in {s.name for s in pr.steps}
```

- [ ] **Step 3: Verificar que el test nuevo falla**

Run: `python -m pytest tests/test_pipeline.py -q`
Expected: FAIL (el paso aún existe).

- [ ] **Step 4: Quitar el paso `catalogo.build`** de `core/pipeline.py` (el bloque
  `_catalogo_step` + su `pr.steps.append(...)` añadido en `45dd5ad`) y el import
  `catalogo_documental` si queda sin uso.

- [ ] **Step 5: Verificar que pasa + suite**

Run: `python -m pytest tests/test_pipeline.py -q` → PASS.
Run: `python -m pytest -q -p no:randomly -ra | grep -aE "passed|failed"` → sin fallos nuevos.

- [ ] **Step 6: Commit**

```bash
git add core/sala_lectura.py core/pipeline.py tests/test_pipeline.py
git commit -m "refactor(core): deprecar el camino de sala del motor + quitar paso catalogo.build (lo posee la skill)"
```

---

## Fase 6 — Empaquetado, CHANGELOG y verificación real

### Task 9: CHANGELOG + empaquetado del `.skill`

**Files:**
- Modify: `.claude/skills/organizar-sala-lectura/CHANGELOG.md`

- [ ] **Step 1: Añadir entrada v1.3** al CHANGELOG (alcance todo 00_Input; salida plana; Paso 0; bundles; fecha-cuerpo; helper manifiesto→catálogo; taxonomía DRY).

- [ ] **Step 2: Empaquetar**

Run: `python scripts/package_skill.py .claude/skills/organizar-sala-lectura`
Expected: `dist/skills/organizar-sala-lectura.skill` regenerado (incluye `scripts/manifiesto_a_catalogo.py`).

- [ ] **Step 3: Gate de skills**

Run: `python scripts/check_skills.py`
Expected: sin avisos de CHANGELOG/`.skill` caducado/taxonomía drift para esta skill.

- [ ] **Step 4: Commit**

```bash
git add ".claude/skills/organizar-sala-lectura/CHANGELOG.md"
git commit -m "docs(skill): CHANGELOG organizar-sala-lectura v1.3"
```

### Task 10: Verificación real sobre BaRS1 (manual, en Cowork) + cierre

> La skill corre en el servidor (Cowork/claude.ai), no en este proceso. Checklist manual.

- [ ] **Step 1: Re-importar** `dist/skills/organizar-sala-lectura.skill` (v1.3) en Cowork.
- [ ] **Step 2: Vaciar** en BaRS1 las salas v1.0: `01_Procesado/Sala lectura/` (por fuente) y `01_Procesado/Sala lectura Drive EV/` (por categoría). El crudo de `00_Input` no se toca.
- [ ] **Step 3: Correr** la skill sobre BaRS1 (URL del expediente). Verificar: estructura PLANA; nombres `AAAA-MM-DD_descripcion`; compuestos en subcarpeta; `INDICE.md` (fecha desc) + `CRONOLOGIA.md` (asc) + `_MANIFIESTO.md` + `indice_documental.yaml` derivado coherente; fecha del cuerpo correcta (p. ej. PODERES JAIME → 2023-01-17).
- [ ] **Step 4: 2ª pasada** sin cambios → skip total (reporta lo saltado), casi instantánea.
- [ ] **Step 5: Cierre** (`/cierre`): dejar `STATUS.md` al día y marcar `[SIGUIENTE-SALA-UNICA-PLANA]` en `PLAN.md` (acotado, respetando cambios ajenos). Anotar pendiente: re-import en Cowork hecho/por hacer.

---

## Self-review (cobertura del spec)

- T1 plana → Task 5/6. T5 sin slug + guiones_bajos → Task 1/6. T4 skill único + deprecación → Task 8. T2 manifiesto+catálogo derivado → Task 4 + Task 6 paso 6. T3 canon+sync+gate → Task 1/2/3.
- RGPD → ya aprobado (sin tarea de código). sha256 → Task 4/6. Modelo Sonnet/Haiku → nota de uso en SKILL.md (Task 5 Step 1). Bundles → Task 6 Step 3. Fecha → Task 1 + Task 6 Step 2. Colisión #36 → Task 6 Step 4. Lectores → Task 7 (triaje) + viabilidad-prerelleno intacta (sin tarea). Deprecación/migración → Task 8 + Task 10.
- Pendiente operativo (#34 resuelto por esta vía, #35/#36/#38 incorporados, #39 a reevaluar) → anotar en el cierre (Task 10 Step 5).
```
