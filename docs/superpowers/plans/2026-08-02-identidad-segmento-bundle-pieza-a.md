# Identidad del segmento de bundle — PIEZA A (motor y esquema) — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** que reprocesar un bundle multi-documento **sustituya** sus artefactos en vez de añadir una
generación nueva al lado, dando al segmento una identidad persistente (`doc_id`) que no depende de
sus bytes.

**Architecture:** el slug del segmento pasa de `parent__segNN_TIPO__sha8` a `parent__docNN_TIPO`. El
`doc_id` vive en el manifiesto (`_segmentacion.json`), que gana un ledger monotónico (`next_doc_id`
+ `retirados`). `--force` deja de sustituir el manifiesto y lo **reconcilia**. Todos los manifiestos
en juego se validan en un **preflight** antes de procesar el primer documento. Las tres
representaciones de cada segmento (PDF, MD, `raw_text`) se escriben a un *staging* dentro de la
carpeta del bundle y se publican por renames, archivando la generación anterior como conjunto. Un
**guard bidireccional** aborta la corrida si fila y fichero no se corresponden.

**Tech Stack:** Python 3.11+, `pytest`, `typer`, `pypdf`, `fpdf2` (fixtures de test), Windows +
PowerShell.

**Spec (fuente única del diseño; no reabrir sus decisiones):**
`docs/superpowers/specs/2026-08-01-identidad-segmento-bundle-design.md` — **rev. 3**, secciones
§0 y §3-§9. La **pieza B** (retrofit y saneamiento de los 5 grupos duplicados) está **⛔ BLOQUEADA**
por el lock de exclusión roto y **no entra en este plan**: nada de lo que sigue toca un caso real.

---

## Global Constraints

- **Ningún caso real se toca.** Todo el trabajo es código y tests bajo `tmp_path`. El único paso que
  mira a `G:` es la medición read-only de la Tarea 8, que **no escribe**.
- **Windows + PowerShell.** Los comandos van desde la raíz del worktree. Encoding UTF-8 sin BOM
  siempre (`write_text(..., encoding="utf-8")`; nunca `Add-Content` sin `-Encoding UTF8`).
- **`main` está protegida:** rama + PR, nunca commit directo. Instalar los hooks en el worktree:
  `pre-commit install && pre-commit install --hook-type pre-push`.
- **El CI del PR solo corre `leak-scan`.** `pytest` NO corre en CI: hay que correrlo local antes de
  pedir el merge.
- **El resumen de pytest no se captura por tuberías en Windows:** contar por
  `--junit-xml`. Medir la base ANTES de empezar (ver «Paso 0») y comparar contra esa base, no contra
  el número que diga ningún documento.
- `doc_id` casa **`^d\d{2,}$`** y nada más. Se valida **antes de cualquier I/O**.
- El slug del segmento es exactamente `f"{parent_slug}__{doc_id}_{_norm_tipo(tipo)}"`.
- `next_doc_id` es un **high-water mark**: monotónico, nunca decrece, nunca se reutiliza un
  `doc_id` de `retirados`.
- **`_intake_log.jsonl` NUNCA se reescribe** (append-only, forense). Seguirá citando slugs viejos y
  eso es correcto.
- Cada test nuevo pasa **mutation testing**: retirarle su arreglo debe MATARLO. Un test que sigue
  verde con el arreglo fuera no es un test (memoria: «un guard sin prueba de mutación no es un
  guard»).
- Comentarios y docstrings **en castellano**, con el porqué, al estilo del módulo que se toca.

### Paso 0 — antes de la Tarea 1 (una sola vez)

```powershell
python -m pytest -q --tb=no --junit-xml=$env:TEMP\base_pieza_a.xml
```

Anota `tests`, `failures`, `errors`, `skipped` del `<testsuite>` del XML: esa es **la base**. El
criterio de salida (§9 del spec) es «suite verde» contra ESA base, no contra 2612 ni 2679.

---

## File Structure

| Fichero | Responsabilidad tras este plan |
|---|---|
| `core/split_documental.py` | **SSOT de la identidad**: `ManifestValidationError`, formato y aritmética del `doc_id`, slug del segmento, esquema del manifiesto (ledger incluido), validación (identidad + rangos + edición) y reconciliación. Es puro salvo `materializar`. |
| `core/sala_maquina.py` | Consume la identidad: `doc_id` en `DocCobertura`, fusión por identidad, preflight de manifiestos, publicación por generación + archivado, guard bidireccional. |
| `scripts/sala_maquina.py` | Cablea preflight (antes de `ejecutar`) y guard (después de persistir), con sus códigos de salida. |
| `tests/test_split_doc_id.py` | **Nuevo.** Identidad: formato, ledger, slug, traversal. |
| `tests/test_split_reconciliacion.py` | **Nuevo.** Reconciliación de `--force`, tombstones y permutación. |
| `tests/test_sala_maquina_generacion.py` | **Nuevo.** Preflight, publicación por generación, archivado, evento no bloqueante y guard. |
| `tests/test_split_reproceso_e2e.py` | **Nuevo.** El test de aceptación: dos materializaciones con bytes distintos → N artefactos y N filas, no 2N. |
| `tests/test_split_documental.py` | Se **actualizan** dos asertos que caracterizaban el slug viejo. |
| `tests/test_split_sala_maquina_e2e.py` | Se **actualiza** el manifiesto escrito a mano (ahora lleva identidad). |
| `tests/test_sala_maquina.py` | Se **añaden** dos tests de fusión por identidad. |
| `docs/superpowers/specs/2026-08-01-identidad-segmento-bundle-design.md` | Cabecera de estado: pieza A construida. |
| `PLAN.md` | Fila #1, punto (f): pieza A cerrada con su hash. |
| `docs/MEJORAS_FUTURAS.md` | Entrada **#113** con los límites declarados de la pieza A. |

---

## Decisiones que este plan cierra (y que el spec dejaba abiertas)

Se escriben aquí para que el revisor adversarial las ataque explícitamente:

1. **`ManifestValidationError` hereda de `ValueError`.** `validar_manifiesto` ya lanzaba `ValueError`
   y hay tests y llamadores que lo esperan; heredar mantiene el contrato vigente y permite un
   `except` específico donde importa.
2. **El preflight valida IDENTIDAD, no rangos.** Los rangos exigen el nº de páginas del **buscable**,
   que para un escaneado no existe todavía (el OCR aún no ha corrido). Pasar `total_pag=0` marcaría
   como «fuera de rango» todo manifiesto válido. Los rangos se siguen validando donde hoy, dentro de
   `_split_o_md`, con el total real.
3. **Alcance declarado del preflight:** los manifiestos **ya en disco** de los documentos que la
   corrida va a procesar. La reconciliación de `--force` sobre un escaneado no se puede preflightar
   por la misma razón que (2); la cubren el aislamiento por documento y el guard.
4. **Manifiesto legacy sin `doc_id`:** en corrida normal **aborta** con un mensaje que nombra el
   bundle y apunta al retrofit (pieza B) y a la salida disponible hoy (`--force`, que reconcilia y
   acuña). No se acuñan identidades en silencio: el `segNN` de un artefacto puede no representar el
   `pp` actual si un `--force` histórico renumeró, y congelar esa identidad equivocada es
   exactamente lo que §11 quiere evitar. El coste operativo está declarado en la entrada #113.
5. **El baseline de la comprobación de permutación** (§3.3) son las filas de cobertura del bundle
   (`doc_id → paginas`). Sin baseline (primera corrida, o caso legacy sin `_cobertura.json`) la
   comprobación **no corre y se declara**; no se finge cobertura.
6. **El slug previo, para archivar, sale del manifiesto anterior**, no de la cobertura: mismo
   `doc_id` con `tipo` distinto ⇒ slug distinto ⇒ renombrado detectable. Los slugs del esquema viejo
   (con sha) NO son derivables del manifiesto y son huérfanos de la **pieza B**.
7. **El guard corre DESPUÉS de persistir** cobertura, estado y evento, y solo entonces sale ≠ 0.
   Abortar antes de escribir perdería justo las filas que el guard existe para proteger.
8. **Alcance del guard:** los documentos **que la corrida procesa, tomados del PLAN** — no de las
   filas resultantes: cuando un bundle revienta, la única fila que queda es la de error, sin
   `parent_slug`, y un alcance derivado de las filas dejaría al guard ciego justo ahí. No audita el
   daño histórico censado (5 grupos duplicados en 2 casos): eso es de la pieza B, y convertirlo en
   aborto dejaría esos dos casos sin poder procesarse mientras B siga bloqueada.
9. **Códigos de salida:** `2` = error de uso o preflight (como `--vision` y `--solo`); **`3` = la
   corrida dejó la Sala de máquina incoherente** (guard). Distintos a propósito: el operador debe
   poder distinguir «no empecé» de «terminé mal».
10. **Al publicar se archiva toda generación ajena al manifiesto** que quede en la carpeta del
    bundle, no solo el slug previo del mismo `doc_id`. Sin esto, la vía de escape de la decisión 4
    estaba rota: los slugs del esquema viejo no son derivables del manifiesto, un `--force` los
    dejaría al lado sin fila, y el guard abortaría con salida 3 justo en el caso que la decisión 4
    manda usar. **Esto no invade la pieza B:** aquí no se elige superviviente ni se migra nada — se
    publica la generación que el manifiesto declara y lo demás se archiva, reversible. La pieza B
    sigue siendo necesaria para los grupos duplicados que nadie va a reprocesar.

---

### Task 1: `doc_id` — formato canónico, ledger y slug independiente del contenido

**Files:**
- Modify: `core/split_documental.py` (nuevo error y helpers; `DocLogico:61-71`;
  `construir_manifiesto:220-229`; `escribir_manifiesto:232-248`; `_slug_seg:280-283`;
  `materializar:286-322`)
- Modify: `tests/test_split_documental.py:174-205` (dos asertos del slug viejo)
- Test: `tests/test_split_doc_id.py` (nuevo)

**Interfaces:**
- Consumes: nada de tareas anteriores.
- Produces:
  - `class ManifestValidationError(ValueError)`
  - `DOC_ID_INICIAL: str = "d01"`, `STAGING: str = "_staging"`
  - `validar_doc_id(doc_id: object, *, contexto: str = "") -> str`
  - `siguiente_doc_id(doc_id: str) -> str`
  - `_slug_seg(parent_slug: str, doc_id: str, tipo: str) -> str`
  - `_destino_en_bundle(destino: Path, carpeta_bundle: Path) -> Path`
  - `construir_manifiesto(...) -> dict` con `segmentos[i]["doc_id"]`, `next_doc_id`, `retirados`
  - `materializar(..., carpeta_salida: Path | None = None) -> list[DocLogico]`, con
    `DocLogico.doc_id`

- [ ] **Step 1: Write the failing test**

Crear `tests/test_split_doc_id.py`:

```python
"""Identidad persistente del segmento de bundle: `doc_id`, ledger y slug sin sha.

Spec: docs/superpowers/specs/2026-08-01-identidad-segmento-bundle-design.md §3.
"""
from __future__ import annotations

import pytest

from core import split_documental as split
from core.split_documental import ManifestValidationError
from tests._pdf_fixtures import build_pdf


def test_slug_no_depende_del_contenido():
    """Mismo (parent, doc_id, tipo) → mismo slug, cambien o no los bytes del segmento.

    El defecto en una línea: el slug llevaba el sha del PDF ya recortado, un artefacto
    DERIVADO, así que re-OCR-izar renombraba todos los artefactos del segmento y el
    reproceso añadía una generación al lado en vez de sustituirla.
    """
    a = split._slug_seg("bundle__aabbccdd", "d01", "DOC_ARRAS")
    b = split._slug_seg("bundle__aabbccdd", "d01", "DOC_ARRAS")
    assert a == b == "bundle__aabbccdd__d01_DOC_ARRAS"


@pytest.mark.parametrize("malo", ["../fuera", "d1", "D01", "d 01", "d01/x", "d01.pdf",
                                  "", "1", None, 7])
def test_doc_id_no_canonico_se_rechaza(malo):
    """El formato es cerrado porque el `doc_id` es un campo EDITABLE que entra en una ruta."""
    with pytest.raises(ManifestValidationError):
        split.validar_doc_id(malo)


def test_siguiente_doc_id_es_monotonico_y_crece_de_ancho():
    assert split.siguiente_doc_id("d01") == "d02"
    assert split.siguiente_doc_id("d09") == "d10"
    assert split.siguiente_doc_id("d99") == "d100"


def test_construir_manifiesto_acuna_doc_ids_y_abre_el_ledger():
    segs = [split.Segmento(1, 1, 4, "CEDULA_EMPLAZAMIENTO"), split.Segmento(2, 6, 12, "AUTO")]
    man = split.construir_manifiesto("01_Drive EV/b.pdf", "a" * 64, segs, {5})
    assert [e["doc_id"] for e in man["segmentos"]] == ["d01", "d02"]
    assert man["next_doc_id"] == "d03"
    assert man["retirados"] == []


def test_el_espejo_md_ensena_el_doc_id_y_pide_no_tocarlo(tmp_path):
    """El `.md` es lo que el letrado lee y edita: si no ve el `doc_id`, lo reasignará."""
    segs = [split.Segmento(1, 1, 4, "CEDULA_EMPLAZAMIENTO")]
    split.escribir_manifiesto(
        tmp_path, split.construir_manifiesto("01_Drive EV/b.pdf", "a" * 64, segs, set()))
    txt = (tmp_path / "_segmentacion.md").read_text(encoding="utf-8")
    assert "doc_id" in txt and "d01" in txt
    assert "NO toques" in txt


def test_destino_en_bundle_rechaza_una_ruta_que_se_sale(tmp_path):
    """Cinturón y tirantes de §3.1: además del formato, el destino final se contiene."""
    carpeta = tmp_path / "02_Documentos" / "bundle"
    with pytest.raises(ManifestValidationError):
        split._destino_en_bundle(carpeta / ".." / "otro.pdf", carpeta)


def test_materializar_rechaza_doc_id_no_canonico_antes_de_tocar_el_disco(tmp_path):
    """Traversal, en Windows real: no aparece NADA fuera de la carpeta del bundle.

    La 2ª revisión adversarial lo ejecutó sobre la rev. 2: un `doc_id` con separadores
    escribía fuera del bundle porque `materializar` arma `destino_pdf` sin pasar por
    `destino_seguro`.
    """
    pdf = build_pdf(tmp_path / "j.pdf",
                    [["CEDULA DE EMPLAZAMIENTO"], [], ["FACTURA", "Total 100"]])
    man = {"fuente": "01_Drive EV/j.pdf", "bundle_sha256": "d" * 64,
           "segmentos": [{"seg": 1, "doc_id": "..\\..\\fuera", "pp": "1-1",
                          "tipo": "X", "role": "documento"}],
           "delimitadores": [2], "next_doc_id": "d02", "retirados": []}
    carpeta = tmp_path / "02_Documentos" / "bundle-slug"
    antes = sorted(p.name for p in tmp_path.iterdir())

    with pytest.raises(ManifestValidationError):
        split.materializar(pdf, man, carpeta, parent_slug="bundle-slug",
                           parent_sha256="d" * 64, bundle_rel_path="01_Drive EV/j.pdf")

    assert sorted(p.name for p in tmp_path.iterdir()) == antes, "escribió fuera del bundle"
    assert not carpeta.exists(), "la validación debe ir ANTES incluso del mkdir"
```

Y **actualizar** en `tests/test_split_documental.py` los dos asertos que caracterizaban el slug
viejo (líneas 203-204), sustituyéndolos por:

```python
    assert len(d0.seg_sha256) == 64          # el sha sigue en la CUSTODIA…
    assert d0.doc_id == "d01"
    assert d0.slug == "bundle-slug__d01_CEDULA_EMPLAZAMIENTO"   # …pero ya no en el NOMBRE
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_split_doc_id.py -x -q`
Expected: FAIL — `ImportError: cannot import name 'ManifestValidationError'`.

- [ ] **Step 3: Write minimal implementation**

En `core/split_documental.py`, añadir tras los imports (después de `_LOG`, línea ~22):

```python
class ManifestValidationError(ValueError):
    """Manifiesto de segmentación inválido: identidad, ledger o destino.

    Hereda de `ValueError` a propósito: `validar_manifiesto` ya lanzaba `ValueError`
    (rangos, solapes) y hay llamadores y tests que lo esperan. Heredar conserva ese
    contrato y a la vez permite un `except` específico en el preflight del CLI.
    """


DOC_ID_INICIAL = "d01"
STAGING = "_staging"          # subcarpeta de publicación por generación (sala_maquina)
_DOC_ID_RE = re.compile(r"^d\d{2,}$")


def validar_doc_id(doc_id: object, *, contexto: str = "") -> str:
    """Formato canónico del `doc_id`, validado ANTES de cualquier I/O (spec §3.1).

    No es celo: el `doc_id` es un campo del manifiesto que **edita el letrado** y que
    entra directamente en el nombre de un fichero. El slug era seguro por construcción
    mientras venía de `f"{seg:02d}"`; en cuanto lo escribe una persona, aparece el
    traversal.
    """
    sufijo = f" ({contexto})" if contexto else ""
    if not isinstance(doc_id, str) or not _DOC_ID_RE.match(doc_id):
        raise ManifestValidationError(
            f"doc_id inválido {doc_id!r}{sufijo}: debe casar ^d\\d{{2,}}$ (p. ej. d01)")
    return doc_id


def siguiente_doc_id(doc_id: str) -> str:
    """Acuña el siguiente `doc_id`. Ancho mínimo 2, sin tope: d99 → d100."""
    validar_doc_id(doc_id, contexto="next_doc_id")
    return f"d{int(doc_id[1:]) + 1:02d}"


def _destino_en_bundle(destino: Path, carpeta_bundle: Path) -> Path:
    """El destino final cae DENTRO de la carpeta del bundle (spec §3.1, cinturón y tirantes).

    No se reutiliza `sala_maquina.destino_seguro` —el equivalente contra el `case_dir`—
    porque importarlo aquí crearía un ciclo: `sala_maquina` ya importa este módulo.
    """
    destino, carpeta_bundle = Path(destino), Path(carpeta_bundle)
    try:
        destino.resolve().relative_to(carpeta_bundle.resolve())
    except ValueError:
        raise ManifestValidationError(
            f"destino fuera de la carpeta del bundle: {destino} (bundle: {carpeta_bundle})")
    return destino
```

`DocLogico` gana el campo (al final: los dataclass no admiten un campo sin default delante de otros
con default, y todos los llamadores construyen por keyword):

```python
@dataclass
class DocLogico:
    slug: str
    seg_sha256: str
    destino: str          # passthrough | split | merge
    tipo: str
    parent_slug: str
    parent_sha256: str
    role_in_bundle: str
    paginas: str | None
    fuentes: list[str] = field(default_factory=list)
    doc_id: str = ""      # identidad persistente del documento lógico (vacío = suelto)
```

`construir_manifiesto` acuña identidades y abre el ledger:

```python
def construir_manifiesto(bundle_rel_path: str, bundle_sha256: str,
                         segmentos: list[Segmento], blancos: set[int]) -> dict:
    """Manifiesto propuesto por `plan`, ya con identidad acuñada y ledger abierto."""
    entradas: list[dict] = []
    doc_id = DOC_ID_INICIAL
    for s in segmentos:
        entradas.append({"seg": s.seg, "doc_id": doc_id,
                         "pp": _pp(s.pagina_inicio, s.pagina_fin),
                         "tipo": s.tipo, "role": s.role})
        doc_id = siguiente_doc_id(doc_id)
    return {
        "fuente": bundle_rel_path,
        "bundle_sha256": bundle_sha256,
        "segmentos": entradas,
        "delimitadores": sorted(blancos),
        "next_doc_id": doc_id,     # high-water mark: nunca decrece (spec §3.2)
        "retirados": [],           # tombstones: un doc_id de baja no se reutiliza
    }
```

`escribir_manifiesto`: el espejo Markdown enseña el `doc_id` y avisa de que no se toca:

```python
    lineas = [
        "<!-- GENERADO — editable: ajusta pp/tipo/role y re-ejecuta apply -->",
        "<!-- NO toques `doc_id`: es la identidad persistente del documento lógico. "
        "Cambiarlo o intercambiarlo entre filas aborta la corrida. -->",
        f"# Segmentación propuesta — {manifiesto['fuente']}",
        "",
        "| seg | doc_id | páginas | tipo | role |",
        "|---|---|---|---|---|",
    ]
    for e in manifiesto["segmentos"]:
        lineas.append(f"| {e['seg']} | {e.get('doc_id', '')} | {e['pp']} | "
                      f"{e['tipo']} | {e['role']} |")
```

`_slug_seg` y `materializar`:

```python
def _slug_seg(parent_slug: str, doc_id: str, tipo: str) -> str:
    """Nombre del segmento por IDENTIDAD, no por contenido.

    `parent_slug` ya viene de `output_slug` (path-safe) y `TIPO` de `_norm_tipo`
    (mayúsculas, NO slugify: bajaría el case — decisión D5 de 2026-07-15). El sha del
    segmento sale del nombre: sigue en la cobertura como cadena de custodia.
    """
    validar_doc_id(doc_id, contexto=f"segmento de {parent_slug}")
    return f"{parent_slug}__{doc_id}_{_norm_tipo(tipo)}"


def materializar(pdf_path: Path, manifiesto: dict, carpeta_bundle: Path, *,
                 parent_slug: str, parent_sha256: str, bundle_rel_path: str,
                 carpeta_salida: Path | None = None,
                 log: logging.Logger | None = None) -> list[DocLogico]:
    """Corta el bundle según el manifiesto → PDFs + `DocLogico` por documento lógico.

    `carpeta_salida` (default: la propia `carpeta_bundle`) es dónde aterrizan los PDFs y
    el `indice.json`; `sala_maquina` la apunta al *staging* para publicar por generación.
    La contención se valida SIEMPRE contra `carpeta_bundle`, que es la frontera real.
    """
    log = log or _LOG
    pdf_path = Path(pdf_path)
    carpeta_bundle = Path(carpeta_bundle)
    carpeta_salida = Path(carpeta_salida) if carpeta_salida else carpeta_bundle

    # Validación COMPLETA antes de tocar disco (ni mkdir): un doc_id no canónico no
    # puede llegar a formar parte de una ruta que se escriba.
    slugs = []
    for e in manifiesto["segmentos"]:
        slug = _slug_seg(parent_slug, e.get("doc_id"), e["tipo"])
        _destino_en_bundle(carpeta_salida / f"{slug}.pdf", carpeta_bundle)
        slugs.append(slug)

    carpeta_salida.mkdir(parents=True, exist_ok=True)

    segs_sep = []
    for e in manifiesto["segmentos"]:
        ini, fin = _pp_a_rango(e["pp"])
        segs_sep.append({"tipo": e["tipo"], "num_doc": e["seg"],
                         "pagina_inicio": ini, "pagina_fin": fin, "lineas_inicio": []})

    resultados = separar.separar_pdf(pdf_path, segs_sep, carpeta_salida, log)

    docs: list[DocLogico] = []
    for e, r, slug in zip(manifiesto["segmentos"], resultados, slugs):
        emitido = carpeta_salida / r["archivo"]
        destino_pdf = carpeta_salida / f"{slug}.pdf"
        emitido.replace(destino_pdf)          # renombrar a identidad persistente
        seg_sha = file_sha256(destino_pdf)    # custodia: el sha se mide, ya no nombra
        r["archivo"] = f"{slug}.pdf"
        docs.append(DocLogico(
            slug=slug, seg_sha256=seg_sha, destino="split", tipo=e["tipo"],
            parent_slug=parent_slug, parent_sha256=parent_sha256,
            role_in_bundle=e.get("role", "documento"), paginas=r["paginas"],
            fuentes=[bundle_rel_path], doc_id=e["doc_id"],
        ))
    separar.generar_indice(resultados, pdf_path, carpeta_salida, log)
    return docs
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_split_doc_id.py tests/test_split_documental.py -q`
Expected: PASS (todos).

Mutación obligatoria: quitar la línea `validar_doc_id(...)` de `_slug_seg` → debe morir
`test_materializar_rechaza_doc_id_no_canonico_antes_de_tocar_el_disco`. Restaurarla.

- [ ] **Step 5: Commit**

```bash
git add core/split_documental.py tests/test_split_doc_id.py tests/test_split_documental.py
```

```bash
git commit -m "feat(split): doc_id persistente, ledger y slug de segmento independiente del contenido"
```

---

### Task 2: reconciliación de `--force`, tombstones y permutación

**Files:**
- Modify: `core/split_documental.py` (`validar_manifiesto:261-270`; nuevas `validar_identidad`,
  `validar_edicion`, `reconciliar_manifiesto`, `Reconciliacion`)
- Modify: `tests/test_split_sala_maquina_e2e.py:90-94` (el manifiesto escrito a mano)
- Test: `tests/test_split_reconciliacion.py` (nuevo)

**Interfaces:**
- Consumes: `ManifestValidationError`, `validar_doc_id`, `siguiente_doc_id`, `_pp_a_rango`.
- Produces:
  - `@dataclass Reconciliacion(manifiesto: dict, heredados: list[str], acunados: list[str], retirados: list[dict])`
  - `reconciliar_manifiesto(previo: dict | None, propuesto: dict) -> Reconciliacion`
  - `validar_identidad(manifiesto: dict, *, exigir_doc_id: bool = True) -> None`
  - `validar_edicion(manifiesto: dict, baseline: dict[str, str]) -> None`
  - `validar_manifiesto(manifiesto: dict, total_pag: int) -> None` (rangos **y luego** identidad)

- [ ] **Step 1: Write the failing test**

Crear `tests/test_split_reconciliacion.py`:

```python
"""Reconciliación del manifiesto en `--force`, ledger monotónico y permutación.

Spec: 2026-08-01-identidad-segmento-bundle-design.md §3.2, §3.3 y §5.
"""
from __future__ import annotations

import pytest

from core import split_documental as split
from core.split_documental import ManifestValidationError


def _man(entradas, *, next_doc_id, retirados=(), fuente="01_Drive EV/b.pdf"):
    """Manifiesto mínimo: [(doc_id, pp, tipo)] → dict con ledger."""
    return {"fuente": fuente, "bundle_sha256": "a" * 64,
            "segmentos": [{"seg": i, "doc_id": did, "pp": pp, "tipo": tipo,
                           "role": "documento"}
                          for i, (did, pp, tipo) in enumerate(entradas, 1)],
            "delimitadores": [], "next_doc_id": next_doc_id, "retirados": list(retirados)}


def _propuesto(rangos):
    """Lo que `construir_manifiesto` produciría de una detección fresca: [(pp, tipo)]."""
    segs = [split.Segmento(i, int(pp.split("-")[0]), int(pp.split("-")[1]), tipo)
            for i, (pp, tipo) in enumerate(rangos, 1)]
    return split.construir_manifiesto("01_Drive EV/b.pdf", "b" * 64, segs, set())


def test_pp_identico_hereda_la_identidad():
    """Caso 1 de §5: reprocesar sin cambiar la segmentación conserva el doc_id.

    Es EL caso de uso real (re-OCR). Si esto no se cumple, todo lo demás sobra.
    """
    previo = _man([("d01", "1-3", "DOC_ARRAS"), ("d02", "5-9", "DOC_PBC")],
                  next_doc_id="d03")
    rec = split.reconciliar_manifiesto(previo, _propuesto([("1-3", "DOC_ARRAS"),
                                                           ("5-9", "DOC_PBC")]))
    assert [e["doc_id"] for e in rec.manifiesto["segmentos"]] == ["d01", "d02"]
    assert rec.heredados == ["d01", "d02"] and rec.acunados == []
    assert rec.manifiesto["next_doc_id"] == "d03"      # no se acuñó nada: no avanza


def test_rango_nuevo_disjunto_acuna_del_high_water_mark():
    """Caso 2 de §5, con el ledger haciendo su trabajo."""
    previo = _man([("d01", "1-3", "DOC_ARRAS")], next_doc_id="d02")
    rec = split.reconciliar_manifiesto(previo, _propuesto([("1-3", "DOC_ARRAS"),
                                                           ("5-9", "DOC_PBC")]))
    assert [e["doc_id"] for e in rec.manifiesto["segmentos"]] == ["d01", "d02"]
    assert rec.acunados == ["d02"]
    assert rec.manifiesto["next_doc_id"] == "d03"


def test_solape_sin_igualdad_detiene_el_force():
    """Caso 3 de §5: un split real (1-6 → 1-3 + 4-6) NO se empareja a ojo.

    Ningún rango nuevo iguala al viejo y los dos solapan: no hay identidad que heredar
    y el desempate por solape admitiría empates. Se para y decide una persona.
    """
    previo = _man([("d01", "1-6", "DOCUMENTO")], next_doc_id="d02")
    with pytest.raises(ManifestValidationError, match="solap"):
        split.reconciliar_manifiesto(previo, _propuesto([("1-3", "DOCUMENTO"),
                                                         ("4-6", "DOCUMENTO")]))


def test_entrada_desaparecida_se_retira_y_se_devuelve_para_archivar():
    """Caso 4 de §5: el doc_id va a tombstones y el llamador archiva sus artefactos."""
    previo = _man([("d01", "1-3", "DOC_ARRAS"), ("d02", "5-9", "DOC_PBC")],
                  next_doc_id="d03")
    rec = split.reconciliar_manifiesto(previo, _propuesto([("1-3", "DOC_ARRAS")]))
    assert rec.manifiesto["retirados"] == ["d02"]
    assert [e["doc_id"] for e in rec.retirados] == ["d02"]
    assert rec.retirados[0]["tipo"] == "DOC_PBC", "hace falta el tipo para el slug viejo"


def test_retirar_el_maximo_no_permite_reutilizarlo():
    """§3.2: «correlativo al máximo existente» y «nunca reutiliza un retirado» no podían
    ser verdad a la vez. Con el high-water mark la contradicción desaparece."""
    previo = _man([("d01", "1-3", "A")], next_doc_id="d03", retirados=["d02"])
    rec = split.reconciliar_manifiesto(previo, _propuesto([("1-3", "A"), ("5-9", "B")]))
    nuevos = [e["doc_id"] for e in rec.manifiesto["segmentos"]]
    assert "d02" not in nuevos, "reutilizó un doc_id dado de baja"
    assert nuevos == ["d01", "d03"] and rec.manifiesto["next_doc_id"] == "d04"


def test_un_doc_id_retirado_en_los_segmentos_aborta():
    man = _man([("d01", "1-3", "A"), ("d02", "5-9", "B")], next_doc_id="d03",
               retirados=["d02"])
    with pytest.raises(ManifestValidationError, match="retirados"):
        split.validar_identidad(man)


def test_doc_id_repetido_aborta():
    man = _man([("d01", "1-3", "A"), ("d01", "5-9", "B")], next_doc_id="d02")
    with pytest.raises(ManifestValidationError, match="repetido"):
        split.validar_identidad(man)


def test_next_doc_id_por_debajo_de_lo_usado_aborta():
    man = _man([("d05", "1-3", "A")], next_doc_id="d02")
    with pytest.raises(ManifestValidationError, match="high-water"):
        split.validar_identidad(man)


def test_manifiesto_legacy_sin_doc_id_pide_el_retrofit_por_su_nombre():
    """No se acuñan identidades en silencio sobre un esquema viejo (decisión 4 del plan)."""
    man = {"fuente": "01_Drive EV/b.pdf", "bundle_sha256": "a" * 64,
           "segmentos": [{"seg": 1, "pp": "1-3", "tipo": "A", "role": "documento"}],
           "delimitadores": []}
    with pytest.raises(ManifestValidationError, match="retrofit"):
        split.validar_identidad(man)
    split.validar_identidad(man, exigir_doc_id=False)   # bajo --force sí se tolera


def test_permutacion_de_identidades_aborta():
    """§3.3: el conjunto de `pp` no cambia pero la correspondencia sí → identidades cruzadas."""
    man = _man([("d01", "5-9", "A"), ("d02", "1-3", "B")], next_doc_id="d03")
    with pytest.raises(ManifestValidationError, match="permutaci"):
        split.validar_edicion(man, {"d01": "1-3", "d02": "5-9"})


def test_editar_el_pp_a_un_rango_nuevo_esta_permitido():
    """La corrección del letrado es legítima: el manifiesto es SU gate."""
    man = _man([("d01", "1-4", "A"), ("d02", "5-9", "B")], next_doc_id="d03")
    split.validar_edicion(man, {"d01": "1-3", "d02": "5-9"})   # no lanza


def test_sin_baseline_no_se_finge_la_comprobacion():
    """Primera corrida o caso legacy sin `_cobertura.json`: no hay contra qué comparar."""
    man = _man([("d01", "5-9", "A")], next_doc_id="d02")
    split.validar_edicion(man, {})                              # no lanza


def test_validar_manifiesto_sigue_mirando_los_rangos_primero():
    """Los mensajes de rango/solape que ya existían no cambian de forma."""
    man = _man([("d01", "1-4", "X"), ("d02", "3-9", "Y")], next_doc_id="d03")
    with pytest.raises(ValueError, match="solap"):
        split.validar_manifiesto(man, total_pag=20)
```

Y **actualizar** el manifiesto escrito a mano de `tests/test_split_sala_maquina_e2e.py:90-94`
(`test_manifiesto_editado_se_respeta`), que hoy no lleva identidad y a partir de esta tarea sería un
esquema legacy — el propio comportamiento que estamos fijando:

```python
    # Manifiesto editado a mano: FUSIONA los 3 en 2 (letrado juntó cédula+auto). Lleva
    # identidad porque el motor ya la exige: el esquema sin `doc_id` es legacy y aborta
    # pidiendo el retrofit (pieza B) o un --force.
    split.escribir_manifiesto(carpeta, {
        "fuente": d.rel_path, "bundle_sha256": d.sha256,
        "segmentos": [{"seg": 1, "doc_id": "d01", "pp": "1-3", "tipo": "EXPEDIENTE",
                       "role": "documento"},
                      {"seg": 2, "doc_id": "d02", "pp": "5-5", "tipo": "DOC_FACTURA",
                       "role": "documento"}],
        "delimitadores": [4], "next_doc_id": "d03", "retirados": []})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_split_reconciliacion.py -x -q`
Expected: FAIL — `AttributeError: module 'core.split_documental' has no attribute 'reconciliar_manifiesto'`.

- [ ] **Step 3: Write minimal implementation**

En `core/split_documental.py`, sustituir `validar_manifiesto` por este bloque:

```python
def _solapa(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] <= b[1] and b[0] <= a[1]


def _next_doc_id_de(manifiesto: dict) -> str:
    """`next_doc_id` del manifiesto, o el que le correspondería si no lo trae (legacy)."""
    declarado = manifiesto.get("next_doc_id")
    if isinstance(declarado, str) and _DOC_ID_RE.match(declarado):
        return declarado
    usados = [e["doc_id"] for e in manifiesto.get("segmentos", []) if e.get("doc_id")]
    usados += list(manifiesto.get("retirados") or [])
    if not usados:
        return DOC_ID_INICIAL
    return siguiente_doc_id(max(usados, key=lambda d: int(d[1:])))


def validar_identidad(manifiesto: dict, *, exigir_doc_id: bool = True) -> None:
    """Formato, unicidad, tombstones y high-water mark del ledger (spec §3.1-§3.2).

    `exigir_doc_id=False` para el manifiesto PREVIO en una reconciliación: bajo `--force`
    un esquema viejo no bloquea (sus entradas simplemente no tienen identidad que heredar).
    """
    fuente = manifiesto.get("fuente", "?")
    vistos: set[str] = set()
    retirados = set(manifiesto.get("retirados") or [])
    for e in manifiesto.get("segmentos", []):
        if "doc_id" not in e:
            if not exigir_doc_id:
                continue
            raise ManifestValidationError(
                f"manifiesto sin `doc_id` (esquema anterior a la identidad persistente) "
                f"en {fuente}, seg={e.get('seg')}: requiere el retrofit de la pieza B "
                f"(spec 2026-08-01-identidad-segmento-bundle §11). Salida disponible hoy: "
                f"`apply --force` sobre este caso, que reconcilia y acuña identidades "
                f"nuevas. No se acuñan en silencio: si un --force histórico renumeró, el "
                f"segNN del artefacto puede no representar el pp actual.")
        did = validar_doc_id(e["doc_id"], contexto=f"{fuente}, seg={e.get('seg')}")
        if did in vistos:
            raise ManifestValidationError(f"doc_id repetido en {fuente}: {did}")
        if did in retirados:
            raise ManifestValidationError(
                f"doc_id {did} está en `retirados` (dado de baja) en {fuente} y no puede "
                f"volver a usarse: el ledger es monotónico.")
        vistos.add(did)
    nxt = _next_doc_id_de(manifiesto)
    validar_doc_id(nxt, contexto=f"next_doc_id de {fuente}")
    tope = max((int(d[1:]) for d in vistos | retirados), default=-1)
    if tope >= int(nxt[1:]):
        raise ManifestValidationError(
            f"next_doc_id ({nxt}) no es un high-water mark en {fuente}: hay doc_id ≥ él")


def validar_edicion(manifiesto: dict, baseline: dict[str, str]) -> None:
    """La correspondencia `doc_id → pp` ya establecida no se reasigna a mano (spec §3.3).

    `baseline`: mapa `doc_id → pp` de la última materialización (filas de cobertura del
    bundle). Sin baseline —primera corrida, o caso legacy sin `_cobertura.json`— no hay
    nada contra qué comparar y la comprobación NO corre: se declara, no se finge.

    Editar el `pp` de un doc_id a un rango nuevo es legítimo (el manifiesto es el gate del
    letrado). Lo que se rechaza es la PERMUTACIÓN: mismo conjunto de rangos, distinta
    correspondencia, que cruza dos identidades semánticas sin que nada lo delate.
    """
    if not baseline:
        return
    actual = {e["doc_id"]: e["pp"] for e in manifiesto.get("segmentos", [])
              if e.get("doc_id")}
    comunes = sorted(set(actual) & set(baseline))
    if not comunes:
        return
    if {actual[d] for d in comunes} != {baseline[d] for d in comunes}:
        return          # el conjunto de rangos cambió: re-segmentación, permitida
    cruzados = [d for d in comunes if actual[d] != baseline[d]]
    if cruzados:
        raise ManifestValidationError(
            f"permutación de identidades en {manifiesto.get('fuente', '?')}: los doc_id "
            f"{cruzados} han intercambiado su rango de páginas sin que cambie el conjunto "
            f"de rangos. Si querías re-segmentar, cambia los `pp`; renombrar no se hace "
            f"a mano.")


def validar_manifiesto(manifiesto: dict, total_pag: int) -> None:
    """Rangos y solapes (como siempre) Y la identidad (spec §3).

    Los rangos van PRIMERO a propósito: sus mensajes son los que ya conocen los
    llamadores y los tests, y un manifiesto con rango imposible es un error más básico
    que uno con identidad mal puesta.
    """
    ultimo_fin = 0
    for e in sorted(manifiesto["segmentos"], key=lambda x: _pp_a_rango(x["pp"])[0]):
        ini, fin = _pp_a_rango(e["pp"])
        if ini < 1 or fin > total_pag or fin < ini:
            raise ValueError(f"Segmento {e['seg']} fuera de rango: {e['pp']} (total {total_pag})")
        if ini <= ultimo_fin:
            raise ValueError(f"Segmento {e['seg']} solapa con el anterior: {e['pp']}")
        ultimo_fin = fin
    validar_identidad(manifiesto)


@dataclass
class Reconciliacion:
    manifiesto: dict
    heredados: list[str]       # doc_id que conservan identidad
    acunados: list[str]        # doc_id nuevos
    retirados: list[dict]      # entradas ANTERIORES dadas de baja (doc_id + tipo, para archivar)


def reconciliar_manifiesto(previo: dict | None, propuesto: dict) -> Reconciliacion:
    """`--force` RECONCILIA el manifiesto en vez de sustituirlo (spec §5).

    1. `pp` idéntico → hereda el doc_id (el caso real: re-OCR sin cambiar segmentación).
    2. Sin igualdad y sin solape → acuña del `next_doc_id`.
    3. Sin igualdad pero con solape → se detiene: no hay emparejamiento difuso.
    4. Entrada anterior sin pareja → tombstone + sus artefactos se archivan (el llamador).

    Lo que esto NO promete (hallazgo N-A-3): un split o merge real de límites no conserva
    ninguna identidad, porque ningún rango nuevo iguala al viejo. Es correcto: el
    documento lógico cambió.
    """
    if previo is None:
        return Reconciliacion(dict(propuesto), [],
                              [e["doc_id"] for e in propuesto["segmentos"]], [])

    validar_identidad(previo, exigir_doc_id=False)
    por_pp = {e["pp"]: e for e in previo.get("segmentos", []) if e.get("doc_id")}
    next_id = _next_doc_id_de(previo)

    entradas: list[dict] = []
    heredados: list[str] = []
    acunados: list[str] = []
    usados: set[str] = set()
    for e in propuesto["segmentos"]:
        pp = e["pp"]
        anterior = por_pp.get(pp)
        if anterior is not None:
            did = anterior["doc_id"]
            heredados.append(did)
            usados.add(pp)
        else:
            rango = _pp_a_rango(pp)
            chocan = sorted((p for p in por_pp if _solapa(rango, _pp_a_rango(p))),
                            key=_pp_a_rango)
            if chocan:
                raise ManifestValidationError(
                    f"reconciliación imposible en {propuesto.get('fuente', '?')}: el "
                    f"segmento {pp} no iguala ninguna entrada anterior y solapa con "
                    f"{chocan}. --force se detiene: reconcilia _segmentacion.json a mano "
                    f"(ajusta los pp o retira las entradas viejas) y vuelve a lanzar.")
            did = next_id
            next_id = siguiente_doc_id(next_id)
            acunados.append(did)
        entradas.append({**e, "doc_id": did})

    retirados_entradas = [e for pp, e in sorted(por_pp.items(), key=lambda kv: _pp_a_rango(kv[0]))
                          if pp not in usados]
    manifiesto = {**propuesto, "segmentos": entradas, "next_doc_id": next_id,
                  "retirados": list(previo.get("retirados") or [])
                  + [e["doc_id"] for e in retirados_entradas]}
    return Reconciliacion(manifiesto, heredados, acunados, retirados_entradas)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_split_reconciliacion.py tests/test_split_doc_id.py tests/test_split_documental.py tests/test_split_sala_maquina_e2e.py -q`
Expected: PASS.

Mutación obligatoria (la que pidió N-M-1: el test 6 no puede admitir un «acuña siempre»):
sustituir en `reconciliar_manifiesto` la rama `if anterior is not None:` por un `if False:` →
debe morir `test_pp_identico_hereda_la_identidad`. Restaurar.

- [ ] **Step 5: Commit**

```bash
git add core/split_documental.py tests/test_split_reconciliacion.py tests/test_split_sala_maquina_e2e.py
```

```bash
git commit -m "feat(split): reconciliacion del manifiesto en --force, tombstones y veto de permutacion"
```

---

### Task 3: `doc_id` en la cobertura y fusión por identidad

**Files:**
- Modify: `core/sala_maquina.py` (`DocCobertura:155-169`; `fusionar_cobertura:323-356`;
  `_split_o_md:592-601`)
- Test: `tests/test_sala_maquina.py` (añadir al final)

**Interfaces:**
- Consumes: `DocLogico.doc_id` (Tarea 1).
- Produces:
  - `DocCobertura.doc_id: str = ""`
  - `_clave_cobertura(d: DocCobertura) -> tuple[str, str]`
  - `fusionar_cobertura` indexando por `(rel_path, doc_id)` cuando hay `doc_id`.

- [ ] **Step 1: Write the failing test**

Añadir al final de `tests/test_sala_maquina.py`:

```python
# --- Pieza A: fusión por IDENTIDAD, no por slug -------------------------------

def test_fusionar_por_doc_id_colapsa_el_cambio_de_tipo():
    """Cambiar el TIPO de un segmento deja UNA fila, no dos (spec §6).

    La rev. 2 daba el cambio de TIPO por inocuo. No lo era: el destino nuevo no existe,
    así que la regla «si el destino existe, archivar» no se dispara y la fusión por slug
    conservaba dos filas del MISMO doc_id.
    """
    from core.sala_maquina import DocCobertura, fusionar_cobertura
    vieja = DocCobertura("b__d01_DOC_A", "01_Drive EV/b.pdf", "pypdf", "ok", 100, False,
                         "", "a" * 64, parent_slug="b", paginas="1-3", tipo="DOC_A",
                         doc_id="d01")
    nueva = DocCobertura("b__d01_DOC_B", "01_Drive EV/b.pdf", "pypdf", "ok", 120, False,
                         "", "c" * 64, parent_slug="b", paginas="1-3", tipo="DOC_B",
                         doc_id="d01")

    out = fusionar_cobertura([vieja], [nueva])

    assert [c.slug for c in out] == ["b__d01_DOC_B"]


def test_fusionar_sin_doc_id_sigue_indexando_por_slug():
    """Los documentos sueltos (y las filas reconstruidas del MD) no tienen doc_id."""
    from core.sala_maquina import DocCobertura, fusionar_cobertura
    a = DocCobertura("encargo__aabbccdd", "01_Drive EV/encargo.pdf", "pypdf", "ok")
    b = DocCobertura("factura__eeff0011", "01_Drive EV/factura.pdf", "pypdf", "ok")

    assert len(fusionar_cobertura([a], [b])) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_sala_maquina.py -q -k "doc_id or slug"`
Expected: FAIL — `TypeError: DocCobertura.__init__() got an unexpected keyword argument 'doc_id'`.

- [ ] **Step 3: Write minimal implementation**

En `core/sala_maquina.py`, añadir el campo al final de `DocCobertura` (los que van delante ya tienen
default; el orden de un dataclass no admite meterlo antes):

```python
    tipo: str = ""           # tipo clasificado del documento lógico
    doc_id: str = ""         # identidad persistente del segmento; vacío = documento suelto
```

Y la fusión:

```python
def _clave_cobertura(d: DocCobertura) -> tuple[str, str]:
    """Identidad de una fila de cobertura: `doc_id` si es segmento, `slug` si es suelto.

    El slug de un segmento cambia cuando cambia su TIPO (y cambiaba, antes, con sus
    bytes), así que indexar por slug dejaba DOS filas del mismo documento lógico. El
    documento suelto no tiene doc_id y conserva la clave de siempre.
    """
    return (d.rel_path, d.doc_id) if d.doc_id else (d.rel_path, d.slug)


def fusionar_cobertura(previa: list[DocCobertura],
                       nueva: list[DocCobertura]) -> list[DocCobertura]:
    """Une la cobertura previa con la de esta corrida: la nueva gana por identidad.

    Simétrico con el estado idempotente (`previo | nuevo`), pero conservando el
    registro COMPLETO en vez de solo el conjunto de shas: una corrida incremental
    procesa solo el delta, así que sin esta fusión `_cobertura.md` perdería las
    filas de las corridas anteriores (el bug de VALERO). Orden estable: las
    previas en su orden (con la versión nueva si se re-tocó ese documento), luego
    las nuevas no vistas.

    La clave la fija `_clave_cobertura` y cubre tres cosas a la vez: (a) dos ficheros
    byte-idénticos con el mismo nombre en carpetas distintas (mismo `slug`, porque
    `output_slug` = stem + sha8 descarta la carpeta) siguen siendo DOS filas de custodia
    porque su `rel_path` difiere; (b) los N documentos lógicos de un bundle (mismo
    `rel_path`) son N filas y NO colapsan; y (c) un segmento se identifica por su
    `doc_id`, no por su slug, que cambia si cambia el TIPO.
    """
    por_clave = {_clave_cobertura(d): d for d in nueva}
    vistos: set[tuple[str, str]] = set()
    out: list[DocCobertura] = []
    for d in previa:
        clave = _clave_cobertura(d)
        out.append(por_clave.get(clave, d))
        vistos.add(clave)
    for d in nueva:
        clave = _clave_cobertura(d)
        if clave not in vistos:
            out.append(d)
            vistos.add(clave)
    return out
```

En `_split_o_md`, al construir la fila de cada segmento, pasar `doc_id=dl.doc_id`:

```python
        filas.append(DocCobertura(dl.slug, d.rel_path, metodo_base, estado, len(texto), ocr, nota,
                                  dl.seg_sha256, parent_slug=dl.parent_slug, parent_sha256=d.sha256,
                                  role=dl.role_in_bundle, paginas=dl.paginas, tipo=dl.tipo,
                                  doc_id=dl.doc_id))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_sala_maquina.py tests/test_split_documental.py -q`
Expected: PASS. `test_fusionar_cobertura_conserva_n_segmentos_mismo_bundle` (filas sin `doc_id`)
sigue dando 3.

Mutación: hacer que `_clave_cobertura` devuelva siempre `(d.rel_path, d.slug)` → debe morir
`test_fusionar_por_doc_id_colapsa_el_cambio_de_tipo`.

- [ ] **Step 5: Commit**

```bash
git add core/sala_maquina.py tests/test_sala_maquina.py
```

```bash
git commit -m "feat(sala-maquina): la cobertura se fusiona por doc_id, no por slug"
```

---

### Task 4: preflight de manifiestos antes de procesar nada

**Files:**
- Modify: `core/sala_maquina.py` (nuevas `carpeta_bundle_de`, `baseline_doc_ids`,
  `preflight_manifiestos`)
- Modify: `scripts/sala_maquina.py` (import de `split`; `apply:290-306`)
- Test: `tests/test_sala_maquina_generacion.py` (nuevo)

**Interfaces:**
- Consumes: `split.validar_identidad`, `split.validar_edicion`, `split.manifiesto_existe`,
  `split.leer_manifiesto`, `DocPlan`, `DocCobertura.doc_id`.
- Produces:
  - `carpeta_bundle_de(case_dir: Path, slug: str) -> Path`
  - `baseline_doc_ids(cobertura: list[DocCobertura], parent_slug: str) -> dict[str, str]`
  - `preflight_manifiestos(case_dir, docs: list[DocPlan], cobertura_previa: list[DocCobertura], *, force: bool = False) -> None`

- [ ] **Step 1: Write the failing test**

Crear `tests/test_sala_maquina_generacion.py` con la cabecera y este primer bloque (los tests de las
Tareas 5-7 se añaden a este mismo fichero):

```python
"""Preflight, publicación por generación y guard bidireccional de la Sala de máquina.

Spec: 2026-08-01-identidad-segmento-bundle-design.md §4, §7.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import typer

import scripts.sala_maquina as cli
from core import sala_maquina as sm
from core import split_documental as split
from tests._pdf_fixtures import build_pdf


def _caso(tmp_path, monkeypatch):
    """Caso mínimo cableado al CLI (idiom del repo: se doblan las 3 dependencias externas)."""
    case_dir = tmp_path / "BaRS9 - Prueba - (W-TEST99) - Negativa oferta aceptada"
    (case_dir / "00_Input" / "01_Drive EV").mkdir(parents=True)
    monkeypatch.setattr(cli, "caso_path", lambda cid: case_dir)
    monkeypatch.setattr(cli, "append_event", lambda cid, ev, *, details=None: None)
    monkeypatch.setattr(cli, "_atomizar_correo", lambda cid, cd: None)
    monkeypatch.setattr(cli.case_locator, "resolve_ref", lambda ref: ref)
    return case_dir


def _bundle(case_dir, nombre="bundle.pdf"):
    """Bundle DIGITAL de 3 documentos lógicos separados por hoja en blanco.

    Texto largo a propósito (mismo motivo que `_bundle_digital` en
    `test_split_sala_maquina_e2e.py`): `_texto_suficiente` exige ≥100 chars y ≥40
    char/pág, y con líneas cortas el motor lo tomaría por escaneado y llamaría a
    OCRmyPDF de verdad.
    """
    return build_pdf(case_dir / "00_Input" / "01_Drive EV" / nombre, [
        ["CEDULA DE EMPLAZAMIENTO",
         "Juzgado de Primera Instancia numero cinco de la ciudad de Barcelona",
         "En la villa de Barcelona se emplaza a la parte demandada para comparecer",
         "en el plazo legalmente establecido conforme a la Ley de Enjuiciamiento Civil."],
        [],
        ["A U T O numero doce dictado por el juzgado en las presentes actuaciones",
         "Vistos los antecedentes de hecho y los fundamentos de derecho aplicables",
         "este tribunal acuerda lo que a continuacion se detalla en la parte dispositiva",
         "con expresa mencion de los recursos que caben contra la presente resolucion."],
        [],
        ["FACTURA por servicios de mediacion inmobiliaria efectivamente prestados",
         "Se detallan a continuacion los conceptos facturados y el importe total",
         "correspondiente a la operacion de intermediacion realizada por la agencia",
         "con el desglose de la base imponible y el impuesto sobre el valor anadido."],
    ])


def _manifiesto_de(case_dir, rel_path):
    """Carpeta y manifiesto del bundle, resueltos como los resuelve el motor."""
    from core.utils import file_sha256, output_slug
    src = case_dir / "00_Input" / rel_path
    slug = output_slug(rel_path, file_sha256(src))
    carpeta = sm.carpeta_bundle_de(case_dir, slug)
    return carpeta, slug


def test_preflight_para_la_corrida_antes_de_escribir_el_primer_bundle(tmp_path, monkeypatch):
    """El manifiesto inválido del SEGUNDO bundle no puede llegar con el primero publicado.

    `validar_manifiesto` corre dentro de `_split_o_md`, documento a documento: sin
    preflight, el primer bundle ya escribió su generación y con `--force` (previa=[]) sus
    filas se pierden al persistir la cobertura.
    """
    case_dir = _caso(tmp_path, monkeypatch)
    _bundle(case_dir, "a.pdf")
    _bundle(case_dir, "z.pdf")
    cli.plan("W-TEST99")                       # deja los dos manifiestos propuestos
    carpeta_z, _ = _manifiesto_de(case_dir, "01_Drive EV/z.pdf")
    man = split.leer_manifiesto(carpeta_z)
    man["segmentos"][0]["doc_id"] = "../fuera"      # el letrado (o un script) lo rompe
    split.escribir_manifiesto(carpeta_z, man)

    with pytest.raises(typer.Exit) as exc:
        cli.apply("W-TEST99")

    assert exc.value.exit_code == 2
    sm_dir = sm._sala_maquina_dir(case_dir)
    assert not (sm_dir / "03_MD").exists(), "el primer bundle no puede haber escrito"
    assert not (sm_dir / "_cobertura.json").exists()


def test_preflight_veta_la_permutacion_con_la_cobertura_como_baseline(tmp_path, monkeypatch):
    case_dir = _caso(tmp_path, monkeypatch)
    _bundle(case_dir, "a.pdf")
    cli.plan("W-TEST99")
    carpeta, slug = _manifiesto_de(case_dir, "01_Drive EV/a.pdf")
    man = split.leer_manifiesto(carpeta)
    pps = [e["pp"] for e in man["segmentos"]]
    cli._guardar_cobertura(case_dir, [
        sm.DocCobertura(f"{slug}__{e['doc_id']}_{e['tipo']}", "01_Drive EV/a.pdf", "pypdf",
                        "ok", parent_slug=slug, paginas=pp, doc_id=e["doc_id"])
        for e, pp in zip(man["segmentos"], pps)])
    man["segmentos"][0]["pp"], man["segmentos"][1]["pp"] = pps[1], pps[0]   # permutación
    split.escribir_manifiesto(carpeta, man)

    with pytest.raises(typer.Exit) as exc:
        cli.apply("W-TEST99")

    assert exc.value.exit_code == 2


def test_preflight_no_mira_los_documentos_saltados(tmp_path, monkeypatch):
    """Un manifiesto legacy de un bundle que esta corrida NO procesa no bloquea nada."""
    case_dir = _caso(tmp_path, monkeypatch)
    _bundle(case_dir, "a.pdf")
    carpeta, _ = _manifiesto_de(case_dir, "01_Drive EV/a.pdf")
    carpeta.mkdir(parents=True, exist_ok=True)
    split.escribir_manifiesto(carpeta, {
        "fuente": "01_Drive EV/a.pdf", "bundle_sha256": "a" * 64, "delimitadores": [],
        "segmentos": [{"seg": 1, "pp": "1-1", "tipo": "X", "role": "documento"}]})
    from dataclasses import replace
    docs = sm.plan(sm.inventariar(case_dir), estado_previo=set())
    saltados = [replace(d, skip=True) for d in docs]

    sm.preflight_manifiestos(case_dir, saltados, [])        # no lanza

    with pytest.raises(split.ManifestValidationError, match="retrofit"):
        sm.preflight_manifiestos(case_dir, docs, [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_sala_maquina_generacion.py -x -q`
Expected: FAIL — `AttributeError: module 'core.sala_maquina' has no attribute 'carpeta_bundle_de'`.

- [ ] **Step 3: Write minimal implementation**

En `core/sala_maquina.py`, tras `destino_seguro`/`_sala_maquina_dir`:

```python
def carpeta_bundle_de(case_dir: Path, slug: str) -> Path:
    """Carpeta de artefactos de un bundle. Un solo sitio que la componga."""
    return destino_seguro(_sala_maquina_dir(case_dir) / "02_Documentos" / slug, case_dir)


def baseline_doc_ids(cobertura: list[DocCobertura], parent_slug: str) -> dict[str, str]:
    """Mapa `doc_id → pp` de la última materialización de ese bundle (spec §3.3)."""
    return {c.doc_id: c.paginas for c in cobertura
            if c.parent_slug == parent_slug and c.doc_id}


def preflight_manifiestos(case_dir: Path, docs: list[DocPlan],
                          cobertura_previa: list[DocCobertura], *,
                          force: bool = False) -> None:
    """Valida los manifiestos en juego ANTES de procesar el primer documento (spec §4).

    `validar_manifiesto` corre hoy dentro de `_split_o_md`, documento a documento, y
    `apply` solo persiste cobertura, estado y evento cuando `ejecutar` retorna: si el
    manifiesto inválido es el del segundo bundle, el primero ya publicó su generación.
    Aquí no se escribe nada — solo se leen JSON — así que la corrida muere antes de tocar
    disco.

    Alcance declarado (decisiones 2 y 3 del plan): se validan IDENTIDAD y EDICIÓN de los
    manifiestos ya en disco de los documentos que esta corrida va a procesar. Los rangos
    exigen el nº de páginas del buscable, que para un escaneado todavía no existe, y se
    siguen validando en `_split_o_md` con el total real. La reconciliación de `--force`
    tampoco es preflightable por lo mismo: la cubren el aislamiento por documento y el
    guard bidireccional.
    """
    case_dir = Path(case_dir)
    for d in docs:
        if d.skip or d.ruta not in ("pdf", "imagen"):
            continue
        carpeta = carpeta_bundle_de(case_dir, d.slug)
        if not split.manifiesto_existe(carpeta):
            continue
        manifiesto = split.leer_manifiesto(carpeta)
        # Con --force el manifiesto en disco se RECONCILIA (no se consume tal cual), así
        # que un esquema viejo sin doc_id no bloquea: se le acuñan identidades nuevas.
        split.validar_identidad(manifiesto, exigir_doc_id=not force)
        if not force:
            split.validar_edicion(manifiesto, baseline_doc_ids(cobertura_previa, d.slug))
```

En `scripts/sala_maquina.py`, añadir el import de módulo (hoy `split` solo se importa dentro de
`plan`) y cablear el preflight en `apply`, entre el plan y `ejecutar`:

```python
from core import split_documental as split
```

```python
    try:
        p = sm.acotar_plan(_construir_plan(case_dir, force=force), rutas)
    except ValueError as exc:              # errata en --solo: parar antes de OCR-izar
        typer.echo(f"ERROR: {exc}", err=True)
        raise typer.Exit(2) from exc

    # Cobertura ACUMULATIVA (ver más abajo). Se lee AQUÍ porque el preflight la necesita
    # como baseline de identidades, y porque leerla dos veces duplicaría su aviso.
    previa = [] if force else _cobertura_previa(case_dir)
    try:
        sm.preflight_manifiestos(case_dir, p, previa, force=force)
    except split.ManifestValidationError as exc:
        typer.echo(f"ERROR: manifiesto de segmentación inválido; no se ha procesado "
                   f"nada.\n{exc}", err=True)
        raise typer.Exit(2) from exc

    cob_delta = sm.ejecutar(case_dir, p, case_id=case_id, vision=vision, force=force)
```

y borrar la línea `previa = [] if force else _cobertura_previa(case_dir)` que quedaba después de
`ejecutar` (ahora se lee antes), conservando su comentario donde estaba la lectura.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_sala_maquina_generacion.py tests/test_sala_maquina_cobertura_legacy.py tests/test_sala_maquina_acotar.py -q`
Expected: PASS.

Mutación: comentar la llamada a `sm.preflight_manifiestos` en el CLI → debe morir
`test_preflight_para_la_corrida_antes_de_escribir_el_primer_bundle`.

- [ ] **Step 5: Commit**

```bash
git add core/sala_maquina.py scripts/sala_maquina.py tests/test_sala_maquina_generacion.py
```

```bash
git commit -m "feat(sala-maquina): preflight de manifiestos antes de procesar el primer documento"
```

---

### Task 5: publicación por generación y archivado como conjunto

**Files:**
- Modify: `core/sala_maquina.py` (`_escribir_md:502-514`; `_split_o_md:549-608`; nuevas
  `_rutas_de`, `_rutas_staging`, `_sello_reproceso`, `publicar_segmentos`)
- Test: `tests/test_sala_maquina_generacion.py` (añadir)

**Interfaces:**
- Consumes: `split.materializar(..., carpeta_salida=)`, `split.reconciliar_manifiesto`,
  `split.STAGING`, `carpeta_bundle_de`.
- Produces:
  - `VERSIONES_ANTERIORES: str = "99_Versiones anteriores"`
  - `_rutas_de(sm_dir: Path, carpeta_bundle: Path, slug: str) -> tuple[Path, Path, Path]`
  - `publicar_segmentos(case_dir, sm_dir, carpeta_bundle, *, publicaciones: list[tuple[str, str]], retirados: list[str], sello: str) -> list[str]`
  - `_escribir_md(..., *, md_path: Path | None = None, raw_path: Path | None = None)`

- [ ] **Step 1: Write the failing test**

Añadir a `tests/test_sala_maquina_generacion.py`:

```python
def _tres(sm_dir, carpeta, slug):
    return sm._rutas_de(sm_dir, carpeta, slug)


def test_publicar_archiva_la_generacion_anterior_como_conjunto(tmp_path):
    """Las tres representaciones viajan juntas: no se publica media generación."""
    case_dir = tmp_path / "caso"
    sm_dir = sm._sala_maquina_dir(case_dir)
    carpeta = sm_dir / "02_Documentos" / "b"
    staging = carpeta / split.STAGING
    staging.mkdir(parents=True)
    for p, texto in zip(_tres(sm_dir, carpeta, "b__d01_A"), ("pdf viejo", "md viejo", "txt viejo")):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(texto, encoding="utf-8")
    for nombre, texto in (("b__d01_A.pdf", "pdf nuevo"), ("b__d01_A.md", "md nuevo"),
                          ("b__d01_A.txt", "txt nuevo")):
        (staging / nombre).write_text(texto, encoding="utf-8")

    archivados = sm.publicar_segmentos(case_dir, sm_dir, carpeta,
                                       publicaciones=[("b__d01_A", "")], retirados=[],
                                       sello="2026-08-02_101010")

    pdf, md, txt = _tres(sm_dir, carpeta, "b__d01_A")
    assert (pdf.read_text(encoding="utf-8"), md.read_text(encoding="utf-8"),
            txt.read_text(encoding="utf-8")) == ("pdf nuevo", "md nuevo", "txt nuevo")
    viejo = case_dir / sm.VERSIONES_ANTERIORES / "reproceso_2026-08-02_101010"
    assert sorted(p.name for p in viejo.iterdir()) == ["b__d01_A.md", "b__d01_A.pdf",
                                                       "b__d01_A.txt"]
    assert len(archivados) == 3
    assert not staging.exists(), "el staging se retira al publicar"


def test_publicar_archiva_tambien_el_slug_previo_cuando_cambia_el_tipo(tmp_path):
    """Mismo doc_id, TIPO distinto ⇒ slug distinto: el renombrado es detectable y se archiva."""
    case_dir = tmp_path / "caso"
    sm_dir = sm._sala_maquina_dir(case_dir)
    carpeta = sm_dir / "02_Documentos" / "b"
    staging = carpeta / split.STAGING
    staging.mkdir(parents=True)
    for p in _tres(sm_dir, carpeta, "b__d01_DOC_A"):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("viejo", encoding="utf-8")
    for ext in ("pdf", "md", "txt"):
        (staging / f"b__d01_DOC_B.{ext}").write_text("nuevo", encoding="utf-8")

    sm.publicar_segmentos(case_dir, sm_dir, carpeta,
                          publicaciones=[("b__d01_DOC_B", "b__d01_DOC_A")], retirados=[],
                          sello="2026-08-02_101010")

    assert not _tres(sm_dir, carpeta, "b__d01_DOC_A")[0].exists(), "quedó el slug viejo"
    assert _tres(sm_dir, carpeta, "b__d01_DOC_B")[0].read_text(encoding="utf-8") == "nuevo"
    viejo = case_dir / sm.VERSIONES_ANTERIORES / "reproceso_2026-08-02_101010"
    assert len(list(viejo.iterdir())) == 3


def test_publicar_archiva_la_generacion_del_esquema_viejo(tmp_path):
    """Sin esto, `--force` sobre un bundle legacy deja los slugs con sha al lado.

    Y esos huérfanos no son inertes: no tienen fila, el guard los ve y aborta con salida
    3 — inutilizando la única vía de escape que la pieza A ofrece para un manifiesto
    legacy mientras la pieza B siga bloqueada.
    """
    case_dir = tmp_path / "caso"
    sm_dir = sm._sala_maquina_dir(case_dir)
    carpeta = sm_dir / "02_Documentos" / "b"
    staging = carpeta / split.STAGING
    staging.mkdir(parents=True)
    for p in _tres(sm_dir, carpeta, "b__seg01_A__aabbccdd"):     # esquema viejo
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("viejo", encoding="utf-8")
    for ext in ("pdf", "md", "txt"):
        (staging / f"b__d01_A.{ext}").write_text("nuevo", encoding="utf-8")

    sm.publicar_segmentos(case_dir, sm_dir, carpeta, publicaciones=[("b__d01_A", "")],
                          retirados=[], sello="2026-08-02_101010")

    assert sorted(p.name for p in carpeta.glob("*.pdf")) == ["b__d01_A.pdf"]
    viejo = case_dir / sm.VERSIONES_ANTERIORES / "reproceso_2026-08-02_101010"
    assert sorted(p.name for p in viejo.iterdir()) == [
        "b__seg01_A__aabbccdd.md", "b__seg01_A__aabbccdd.pdf", "b__seg01_A__aabbccdd.txt"]


def test_si_el_archivado_falla_no_se_publica_ninguna(tmp_path, monkeypatch):
    """El conjunto manda: un archivado a medias deja la generación nueva SIN publicar."""
    case_dir = tmp_path / "caso"
    sm_dir = sm._sala_maquina_dir(case_dir)
    carpeta = sm_dir / "02_Documentos" / "b"
    staging = carpeta / split.STAGING
    staging.mkdir(parents=True)
    for p in _tres(sm_dir, carpeta, "b__d01_A"):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("viejo", encoding="utf-8")
    for ext in ("pdf", "md", "txt"):
        (staging / f"b__d01_A.{ext}").write_text("nuevo", encoding="utf-8")

    real = Path.replace
    def _falla_en_el_md(self, destino):
        if self.suffix == ".md" and sm.VERSIONES_ANTERIORES in str(destino):
            raise OSError("disco lleno")
        return real(self, destino)
    monkeypatch.setattr(Path, "replace", _falla_en_el_md)

    with pytest.raises(OSError):
        sm.publicar_segmentos(case_dir, sm_dir, carpeta,
                              publicaciones=[("b__d01_A", "")], retirados=[],
                              sello="2026-08-02_101010")

    # Sin `monkeypatch.undo()`: revertiría también los dobles del caso, y estas
    # comprobaciones solo leen (el parche está en `replace`, no en `read_text`).
    assert (staging / "b__d01_A.pdf").read_text(encoding="utf-8") == "nuevo", \
        "la generación nueva sigue en staging, sin publicar"
    assert _tres(sm_dir, carpeta, "b__d01_A")[1].read_text(encoding="utf-8") == "viejo"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_sala_maquina_generacion.py -q -k publicar`
Expected: FAIL — `AttributeError: module 'core.sala_maquina' has no attribute '_rutas_de'`.

- [ ] **Step 3: Write minimal implementation**

En `core/sala_maquina.py`, `import shutil` arriba, y tras `carpeta_bundle_de`:

```python
VERSIONES_ANTERIORES = "99_Versiones anteriores"


def _rutas_de(sm_dir: Path, carpeta_bundle: Path, slug: str) -> tuple[Path, Path, Path]:
    """Las TRES representaciones de un documento lógico: PDF, MD y raw_text."""
    return (carpeta_bundle / f"{slug}.pdf",
            sm_dir / "03_MD" / f"{slug}.md",
            sm_dir / "raw_text" / f"{slug}.txt")


def _rutas_staging(staging: Path, slug: str) -> tuple[Path, Path, Path]:
    """Las mismas tres, en el staging del bundle (todas juntas, para publicar por renames)."""
    return staging / f"{slug}.pdf", staging / f"{slug}.md", staging / f"{slug}.txt"


def _sello_reproceso() -> str:
    """`AAAA-MM-DD_HHMMSS`: dos reprocesos del mismo día no se pisan el archivo."""
    return now_iso()[:19].replace(":", "").replace("T", "_")


def publicar_segmentos(case_dir: Path, sm_dir: Path, carpeta_bundle: Path, *,
                       publicaciones: list[tuple[str, str]], retirados: list[str],
                       sello: str) -> list[str]:
    """Publica la generación nueva por renames, archivando la anterior COMO CONJUNTO (§7.1).

    Sacar el sha del nombre tiene un precio: el destino ya existe y `replace` sobrescribe,
    de modo que un fallo a media generación dejaría la fila de cobertura declarando un sha
    que ya no corresponde a esos bytes. Por eso las tres representaciones se escriben a
    `<bundle>/_staging/` y solo al final se mueven; y por eso la anterior se archiva
    entera antes de publicar nada: **si el archivado no puede completarse, no se publica
    ninguna**.

    `publicaciones`: `(slug_nuevo, slug_previo)` — el previo solo cuando el TIPO cambió y
    el slug con él. `retirados`: slugs de documentos lógicos dados de baja, que se archivan
    sin republicar.

    **Y se archiva también toda generación ajena al manifiesto** que quede en la carpeta:
    los slugs del esquema viejo (con sha) no son derivables del manifiesto, así que sin
    esto un `--force` sobre un bundle legacy publicaría los nombres nuevos y dejaría los
    viejos al lado — huérfanos sin fila, que el guard vería y abortaría con salida 3,
    inutilizando la única vía de escape que la pieza A ofrece hasta que se desbloquee la
    pieza B. El manifiesto es la autoridad sobre qué documentos lógicos existen; lo demás
    es generación anterior, y se archiva (no se borra).
    """
    staging = carpeta_bundle / split.STAGING
    archivo = destino_seguro(Path(case_dir) / VERSIONES_ANTERIORES / f"reproceso_{sello}",
                             Path(case_dir))

    publicados = {slug for slug, _ in publicaciones}
    a_archivar: list[Path] = []
    for slug in [s for par in publicaciones for s in par if s] + list(retirados):
        a_archivar += [p for p in _rutas_de(sm_dir, carpeta_bundle, slug) if p.exists()]
    for pdf in sorted(carpeta_bundle.glob("*.pdf")):
        if pdf.stem not in publicados:
            a_archivar += [p for p in _rutas_de(sm_dir, carpeta_bundle, pdf.stem)
                           if p.exists()]
    archivados: list[str] = []
    if a_archivar:
        archivo.mkdir(parents=True, exist_ok=True)
        for p in dict.fromkeys(a_archivar):        # sin duplicados, orden estable
            p.replace(archivo / p.name)            # si falla, sube: no se publica NADA
            archivados.append(p.name)

    for slug_nuevo, _ in publicaciones:
        for origen, destino in zip(_rutas_staging(staging, slug_nuevo),
                                   _rutas_de(sm_dir, carpeta_bundle, slug_nuevo)):
            destino.parent.mkdir(parents=True, exist_ok=True)
            origen.replace(destino)

    # Lo que quede en staging es el índice del bundle (`indice.json` y su resumen): se
    # publica igual, sin enumerarlo por nombre para no atarse a los que escriba `separar`.
    if staging.is_dir():
        for resto in sorted(staging.iterdir()):
            if resto.is_file():
                resto.replace(carpeta_bundle / resto.name)
        shutil.rmtree(staging, ignore_errors=True)
    return archivados
```

`_escribir_md` acepta destinos explícitos (por defecto, los de siempre):

```python
def _escribir_md(case_dir, case_id, slug, rel_path, texto, metodo, ocr, estado,
                 *, md_path: Path | None = None, raw_path: Path | None = None):
    """Escribe el MD y su `raw_text`. Con `md_path`/`raw_path` explícitos escribe al
    staging del bundle, para que la generación se publique entera o no se publique."""
    sm_dir = _sala_maquina_dir(case_dir)
    md_path = destino_seguro(md_path or sm_dir / "03_MD" / f"{slug}.md", case_dir)
    raw_path = destino_seguro(raw_path or sm_dir / "raw_text" / f"{slug}.txt", case_dir)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(texto, encoding="utf-8")
    meta = {
        "case_id": case_id, "tipo": "documento_procesado", "fase": "01_Procesado",
        "fecha": now_iso(), "source_path": rel_path, "extractor": metodo,
        "chars": len(texto), "ocr": ocr, "ocr_quality": estado,
        "text_sha256": text_sha256(texto),
    }
    write_md(md_path, meta, texto)
```

Y la rama de split de `_split_o_md` pasa a reconciliar, estacionar y publicar:

```python
    # split: manifiesto (editable) → reconciliar → materializar a staging → publicar.
    carpeta_bundle = carpeta_bundle_de(case_dir, d.slug)
    previo = (split.leer_manifiesto(carpeta_bundle)
              if split.manifiesto_existe(carpeta_bundle) else None)
    if previo is not None and not force:
        manifiesto, rec = previo, None
    else:
        # --force RECONCILIA en vez de sustituir: sin esto, el manifiesto nuevo perdería
        # las identidades y el reproceso volvería a renombrarlo todo (spec §5).
        rec = split.reconciliar_manifiesto(
            previo, split.construir_manifiesto(d.rel_path, d.sha256, segmentos, blancos))
        manifiesto = rec.manifiesto
    split.validar_manifiesto(manifiesto, _pdf_num_paginas(buscable) or 0)
    if rec is not None:
        split.escribir_manifiesto(carpeta_bundle, manifiesto)

    staging = carpeta_bundle / split.STAGING
    shutil.rmtree(staging, ignore_errors=True)     # restos de una corrida abortada
    doclogicos = split.materializar(buscable, manifiesto, carpeta_bundle,
                                    parent_slug=d.slug, parent_sha256=d.sha256,
                                    bundle_rel_path=d.rel_path, carpeta_salida=staging)
    tipos_previos = {e["doc_id"]: e["tipo"]
                     for e in (previo or {}).get("segmentos", []) if e.get("doc_id")}
    filas: list[DocCobertura] = []
    publicaciones: list[tuple[str, str]] = []
    for dl in doclogicos:
        seg_pdf = staging / f"{dl.slug}.pdf"
        texto = _try_pypdf(seg_pdf) or ""
        estado, nota = _calidad(texto, seg_pdf)
        texto, estado, nota = _aplicar_vision(seg_pdf, texto, estado, nota, vision)
        _escribir_md(case_dir, case_id, dl.slug, d.rel_path, texto, metodo_base, ocr, estado,
                     md_path=staging / f"{dl.slug}.md", raw_path=staging / f"{dl.slug}.txt")
        tipo_previo = tipos_previos.get(dl.doc_id)
        slug_previo = (split._slug_seg(d.slug, dl.doc_id, tipo_previo)
                       if tipo_previo and tipo_previo != dl.tipo else "")
        publicaciones.append((dl.slug, slug_previo))
        filas.append(DocCobertura(dl.slug, d.rel_path, metodo_base, estado, len(texto), ocr, nota,
                                  dl.seg_sha256, parent_slug=dl.parent_slug, parent_sha256=d.sha256,
                                  role=dl.role_in_bundle, paginas=dl.paginas, tipo=dl.tipo,
                                  doc_id=dl.doc_id))
    retirados = [split._slug_seg(d.slug, e["doc_id"], e["tipo"])
                 for e in (rec.retirados if rec else [])]
    archivados = publicar_segmentos(case_dir, _sala_maquina_dir(case_dir), carpeta_bundle,
                                    publicaciones=publicaciones, retirados=retirados,
                                    sello=_sello_reproceso())
    append_event(case_id, "split_documental", details={
        "bundle": d.rel_path, "bundle_sha256": d.sha256, "n_segmentos": len(doclogicos),
        "segmentos": [{"slug": dl.slug, "doc_id": dl.doc_id, "seg_sha256": dl.seg_sha256,
                       "tipo": dl.tipo, "paginas": dl.paginas} for dl in doclogicos],
        "delimitadores": manifiesto["delimitadores"],
        "archivados": archivados,
        "retirados": [e["doc_id"] for e in (rec.retirados if rec else [])],
    })
    return filas
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_sala_maquina_generacion.py tests/test_sala_maquina_ejecutar.py tests/test_split_sala_maquina_e2e.py -q`
Expected: PASS.

Mutación: mover el bloque de archivado DESPUÉS de la publicación → debe morir
`test_si_el_archivado_falla_no_se_publica_ninguna`.

- [ ] **Step 5: Commit**

```bash
git add core/sala_maquina.py tests/test_sala_maquina_generacion.py
```

```bash
git commit -m "feat(sala-maquina): publicacion por generacion con archivado de la anterior como conjunto"
```

---

### Task 6: un fallo del evento no descarta el trabajo publicado

**Files:**
- Modify: `core/sala_maquina.py` (`_split_o_md`, la llamada a `append_event`)
- Test: `tests/test_sala_maquina_generacion.py` (añadir)

**Interfaces:**
- Consumes: `_anotar(filas, aviso)` (ya existe).
- Produces: nada nuevo; cambia el comportamiento de `_split_o_md` ante un `append_event` que lanza.

- [ ] **Step 1: Write the failing test**

```python
def test_un_fallo_al_registrar_el_evento_no_tira_las_filas(tmp_path, monkeypatch):
    """§7.2: hoy la excepción sube a `ejecutar` y se pierden las filas de TODOS los
    segmentos del bundle — el trabajo ya está en disco y el registro lo negaría."""
    case_dir = _caso(tmp_path, monkeypatch)
    _bundle(case_dir, "a.pdf")

    def _revienta(case_id, evento, *, details=None):
        raise OSError("log bloqueado por otro proceso")
    monkeypatch.setattr(sm, "append_event", _revienta)

    docs = sm.plan(sm.inventariar(case_dir), estado_previo=set())
    cob = sm.ejecutar(case_dir, docs, case_id="W-TEST99")

    segmentos = [c for c in cob if c.doc_id]
    assert len(segmentos) == 3, "se perdieron las filas por un fallo de log"
    assert all("evento" in c.nota for c in segmentos), "el fallo debe quedar declarado"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_sala_maquina_generacion.py -q -k evento`
Expected: FAIL — la cobertura trae 1 fila `error/empty` en vez de los 3 segmentos.

- [ ] **Step 3: Write minimal implementation**

En `_split_o_md`, envolver el `append_event` final (mismo payload que dejó la Tarea 5):

```python
    try:
        append_event(case_id, "split_documental", details={
            "bundle": d.rel_path, "bundle_sha256": d.sha256, "n_segmentos": len(doclogicos),
            "segmentos": [{"slug": dl.slug, "doc_id": dl.doc_id, "seg_sha256": dl.seg_sha256,
                           "tipo": dl.tipo, "paginas": dl.paginas} for dl in doclogicos],
            "delimitadores": manifiesto["delimitadores"],
            "archivados": archivados,
            "retirados": [e["doc_id"] for e in (rec.retirados if rec else [])],
        })
    except Exception as exc:  # noqa: BLE001 — el trabajo YA está publicado en disco
        # Sin esto la excepción sube a `ejecutar`, que emite UNA fila de error con el slug
        # del documento físico: los artefactos quedan en disco y la cobertura los niega.
        # El guard bidireccional abortaría después, con razón, por un fallo de log.
        _anotar(filas, f"evento split_documental no registrado: {exc}")
    return filas
```

- [ ] **Step 4: Run tests to verify it passes**

Run: `python -m pytest tests/test_sala_maquina_generacion.py -q`
Expected: PASS.

Mutación: quitar el `try/except` → el test muere.

- [ ] **Step 5: Commit**

```bash
git add core/sala_maquina.py tests/test_sala_maquina_generacion.py
```

```bash
git commit -m "fix(sala-maquina): un fallo de append_event ya no descarta las filas del bundle"
```

---

### Task 7: guard bidireccional, y que aborte

**Files:**
- Modify: `core/sala_maquina.py` (nueva `verificar_integridad_bundles`)
- Modify: `scripts/sala_maquina.py` (`apply` y `reforzar`, tras persistir)
- Test: `tests/test_sala_maquina_generacion.py` (añadir)

**Interfaces:**
- Consumes: `_rutas_de`, `_sala_maquina_dir`, `file_sha256`, `DocCobertura`.
- Produces:
  - `verificar_integridad_bundles(case_dir: Path, cobertura: list[DocCobertura], parents: set[str]) -> list[str]`
  - Salida **3** del CLI cuando devuelve discrepancias.

- [ ] **Step 1: Write the failing test**

```python
def _cob_seg(slug, *, parent, doc_id, sha):
    return sm.DocCobertura(slug, "01_Drive EV/a.pdf", "pypdf", "ok", 10, False, "", sha,
                           parent_slug=parent, paginas="1-1", tipo="A", doc_id=doc_id)


def test_guard_detecta_la_fila_sin_fichero(tmp_path):
    case_dir = tmp_path / "caso"
    sm_dir = sm._sala_maquina_dir(case_dir)
    carpeta = sm_dir / "02_Documentos" / "b"
    carpeta.mkdir(parents=True)
    (carpeta / "b__d01_A.pdf").write_text("pdf", encoding="utf-8")
    from core.utils import file_sha256
    fila = _cob_seg("b__d01_A", parent="b", doc_id="d01",
                    sha=file_sha256(carpeta / "b__d01_A.pdf"))

    fallos = sm.verificar_integridad_bundles(case_dir, [fila], {"b"})

    assert any("MD" in f for f in fallos) and any("raw_text" in f for f in fallos)


def test_guard_detecta_el_fichero_sin_fila(tmp_path):
    """El caso para el que se escribe: el bundle reventó a medias y `ejecutar` emitió UNA
    fila de error con el slug del documento FÍSICO. Con --force, además, previa=[]."""
    case_dir = tmp_path / "caso"
    carpeta = sm._sala_maquina_dir(case_dir) / "02_Documentos" / "b"
    carpeta.mkdir(parents=True)
    (carpeta / "b__d01_A.pdf").write_text("pdf publicado", encoding="utf-8")
    error = sm.DocCobertura("b", "01_Drive EV/a.pdf", "error", "empty", 0, False,
                            "fallo al procesar: X", "a" * 64)

    fallos = sm.verificar_integridad_bundles(case_dir, [error], {"b"})

    assert any("sin fila" in f for f in fallos)


def test_guard_detecta_el_sha_que_no_casa(tmp_path):
    case_dir = tmp_path / "caso"
    sm_dir = sm._sala_maquina_dir(case_dir)
    carpeta = sm_dir / "02_Documentos" / "b"
    carpeta.mkdir(parents=True)
    for p in _tres(sm_dir, carpeta, "b__d01_A"):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x", encoding="utf-8")

    fallos = sm.verificar_integridad_bundles(
        case_dir, [_cob_seg("b__d01_A", parent="b", doc_id="d01", sha="f" * 64)], {"b"})

    assert any("sha" in f for f in fallos)


def test_guard_no_audita_los_bundles_que_esta_corrida_no_toco(tmp_path):
    """El daño histórico (5 grupos duplicados en 2 casos) es de la pieza B: convertirlo en
    aborto dejaría esos casos sin poder procesarse mientras B siga bloqueada."""
    case_dir = tmp_path / "caso"
    carpeta = sm._sala_maquina_dir(case_dir) / "02_Documentos" / "viejo"
    carpeta.mkdir(parents=True)
    (carpeta / "viejo__seg01_A__aabbccdd.pdf").write_text("huérfano", encoding="utf-8")

    assert sm.verificar_integridad_bundles(case_dir, [], set()) == []


def test_apply_sale_con_3_si_la_corrida_deja_la_sala_incoherente(tmp_path, monkeypatch):
    """Y persiste ANTES de abortar: abortar sin escribir perdería justo lo que protege."""
    case_dir = _caso(tmp_path, monkeypatch)
    _bundle(case_dir, "a.pdf")
    monkeypatch.setattr(sm, "verificar_integridad_bundles",
                        lambda cd, cob, parents: ["b__d01_A: falta la representación MD"])

    with pytest.raises(typer.Exit) as exc:
        cli.apply("W-TEST99")

    assert exc.value.exit_code == 3
    assert (sm._sala_maquina_dir(case_dir) / "_cobertura.json").exists(), \
        "la cobertura debe quedar en disco para poder inspeccionarla"


def test_un_fallo_a_media_publicacion_deja_la_anterior_intacta_y_el_guard_aborta(
        tmp_path, monkeypatch):
    """§8.8(a): fallo TRAS publicar el PDF y ANTES del MD, de punta a punta.

    Las dos mitades del contrato en un solo test: la generación anterior está entera en
    `99_Versiones anteriores/` y el guard aborta. Y es el caso que deja ciego a un guard
    que solo mire filas: `ejecutar` aísla el fallo y emite UNA fila de error con el slug
    del documento FÍSICO, sin `parent_slug` — por eso el alcance del guard sale del PLAN
    (los documentos que la corrida procesa), no de las filas resultantes.
    """
    case_dir = _caso(tmp_path, monkeypatch)
    _bundle(case_dir, "a.pdf")
    cli.apply("W-TEST99")                                   # generación 1, publicada
    sm_dir = sm._sala_maquina_dir(case_dir)
    md_previos = {p.name: p.read_bytes() for p in (sm_dir / "03_MD").glob("*.md")}
    assert len(md_previos) == 3

    real = Path.replace
    def _falla_al_publicar_el_md(self, destino):
        if Path(destino).suffix == ".md" and "03_MD" in str(destino):
            raise OSError("disco lleno")
        return real(self, destino)
    monkeypatch.setattr(Path, "replace", _falla_al_publicar_el_md)

    with pytest.raises(typer.Exit) as exc:
        cli.apply("W-TEST99", force=True)

    assert exc.value.exit_code == 3
    archivo = next((case_dir / sm.VERSIONES_ANTERIORES).glob("reproceso_*"))
    assert {p.name: p.read_bytes() for p in archivo.glob("*.md")} == md_previos, \
        "la generación anterior tiene que quedar íntegra en el archivo"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_sala_maquina_generacion.py -q -k guard`
Expected: FAIL — `AttributeError: … has no attribute 'verificar_integridad_bundles'`.

- [ ] **Step 3: Write minimal implementation**

En `core/sala_maquina.py`:

```python
def verificar_integridad_bundles(case_dir: Path, cobertura: list[DocCobertura],
                                 parents: set[str]) -> list[str]:
    """Guard BIDIRECCIONAL sobre los bundles tocados por esta corrida (spec §7.3).

    No basta con recorrer las filas: en el fallo real no hay filas de segmento —`ejecutar`
    emite UNA fila de error con el slug del documento físico— y con `--force` además la
    cobertura previa va vacía. Un guard que solo mirase filas estaría ciego justo en el
    caso para el que se escribe. Por eso se mira en los dos sentidos:

    - fila → fichero: las tres representaciones existen y el sha del PDF casa con el
      declarado en la cobertura;
    - fichero → fila: todo `02_Documentos/<parent>/*.pdf` tiene fila.

    `parents` son los slugs de los documentos que la corrida procesó, y los pone el
    llamador desde el PLAN: derivarlos de las filas dejaría el alcance vacío justo cuando
    el bundle falla (la fila de error no lleva `parent_slug`). El daño histórico censado
    —segmentos duplicados de antes de la identidad persistente— es de la pieza B;
    auditarlo aquí bloquearía dos casos reales mientras B siga bloqueada.
    """
    case_dir = Path(case_dir)
    sm_dir = _sala_maquina_dir(case_dir)
    con_fila = {c.slug for c in cobertura}
    fallos: list[str] = []
    for parent in sorted(parents):
        carpeta = sm_dir / "02_Documentos" / parent
        if not carpeta.is_dir():
            continue
        for c in cobertura:
            if c.parent_slug != parent or not c.doc_id:
                continue
            pdf, md, txt = _rutas_de(sm_dir, carpeta, c.slug)
            for etiqueta, p in (("PDF", pdf), ("MD", md), ("raw_text", txt)):
                if not p.exists():
                    fallos.append(f"{c.slug}: falta la representación {etiqueta} ({p})")
            if pdf.exists() and c.sha256 and file_sha256(pdf) != c.sha256:
                fallos.append(
                    f"{c.slug}: el sha del PDF no casa con el declarado en la cobertura")
        for pdf in sorted(carpeta.glob("*.pdf")):
            if pdf.stem not in con_fila:
                fallos.append(f"{pdf.name}: PDF de segmento sin fila en la cobertura")
    return fallos
```

En `scripts/sala_maquina.py`, un helper y su uso en `apply` **y** en `reforzar`, siempre **después**
de persistir cobertura, estado y evento:

```python
def _exigir_integridad(case_dir: Path, cob: list[sm.DocCobertura],
                       procesados: set[str]) -> None:
    """Aborta si la corrida dejó la Sala de máquina incoherente (spec §7.3).

    `procesados` son los slugs de los documentos que esta corrida procesó, tomados del
    PLAN y no de las filas resultantes. La diferencia es justo el caso para el que se
    escribe el guard: cuando un bundle revienta, `ejecutar` aísla el fallo y emite UNA
    fila de error con el slug del documento físico y **sin `parent_slug`**, así que un
    alcance derivado de las filas saldría vacío y el guard se quedaría ciego.

    Corre DESPUÉS de persistir: abortar antes de escribir perdería justo las filas que el
    guard existe para proteger, y dejaría el disco sin registro de lo que sí se publicó.
    Salida 3 (distinta de la 2 de los errores de uso y preflight): el operador debe poder
    distinguir «no empecé» de «terminé mal».
    """
    fallos = sm.verificar_integridad_bundles(case_dir, cob, procesados)
    if not fallos:
        return
    typer.echo("ERROR: la Sala de máquina quedó incoherente tras esta corrida "
               "(cobertura y artefactos no se corresponden):", err=True)
    for f in fallos:
        typer.echo(f"  - {f}", err=True)
    typer.echo("La cobertura y el estado SÍ se han persistido: revisa los segmentos "
               "citados antes de volver a lanzar.", err=True)
    raise typer.Exit(3)
```

En `apply`, tras `append_event(...)` y antes del resumen:

```python
    _exigir_integridad(case_dir, cob, {d.slug for d in p if not d.skip})
```

En `reforzar`, en el mismo punto (tras su `append_event`) — su plan filtrado se llama `plan` y no
trae saltados:

```python
    _exigir_integridad(case_dir, cob, {d.slug for d in plan})
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_sala_maquina_generacion.py -q`
Expected: PASS.

Mutación: quitar el bucle `fichero → fila` → debe morir `test_guard_detecta_el_fichero_sin_fila`.

- [ ] **Step 5: Commit**

```bash
git add core/sala_maquina.py scripts/sala_maquina.py tests/test_sala_maquina_generacion.py
```

```bash
git commit -m "feat(sala-maquina): guard bidireccional de artefactos de bundle, con salida 3"
```

---

### Task 8: test de aceptación (el defecto, de punta a punta), medición read-only y documentación

**Files:**
- Test: `tests/test_split_reproceso_e2e.py` (nuevo)
- Modify: `docs/superpowers/specs/2026-08-01-identidad-segmento-bundle-design.md` (cabecera)
- Modify: `PLAN.md` (fila #1, punto (f), pieza A)
- Modify: `docs/MEJORAS_FUTURAS.md` (entrada nueva **#113**)

**Interfaces:**
- Consumes: todo lo anterior. No produce API nueva.

- [ ] **Step 1: Write the failing test**

Crear `tests/test_split_reproceso_e2e.py`:

```python
"""El defecto de punta a punta: reprocesar un bundle SUSTITUYE, no añade.

Es el test que el spec (§8.1) declara que «falla hoy»: dos materializaciones del mismo
bundle con bytes distintos dejaban 2N artefactos y 2N filas.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.sala_maquina as cli
from core import sala_maquina as sm
from core.anon.ocr import ResultadoEscalera
from core.utils import file_sha256, output_slug
from tests._pdf_fixtures import build_pdf


@pytest.fixture
def caso(tmp_path, monkeypatch):
    case_dir = tmp_path / "BaRS9 - Prueba - (W-TEST99) - Negativa oferta aceptada"
    (case_dir / "00_Input" / "01_Drive EV").mkdir(parents=True)
    # Origen "escaneado": PDF real (pypdf lo lee sin reventar) pero con texto MUY por
    # debajo de `_texto_suficiente` → el motor baja a la escalera de OCR, que aquí va
    # doblada. Sin dependencia de OCRmyPDF.
    build_pdf(case_dir / "00_Input" / "01_Drive EV" / "bundle.pdf", [["Escaneado"]])
    monkeypatch.setattr(cli, "caso_path", lambda cid: case_dir)
    monkeypatch.setattr(cli, "append_event", lambda cid, ev, *, details=None: None)
    monkeypatch.setattr(cli, "_atomizar_correo", lambda cid, cd: None)
    monkeypatch.setattr(cli.case_locator, "resolve_ref", lambda ref: ref)
    monkeypatch.setattr(sm, "append_event", lambda cid, ev, *, details=None: None)
    return case_dir


def _escalera_que_reescribe(corrida: dict):
    """Doble de la escalera: cada corrida produce un buscable con los MISMOS documentos
    lógicos y BYTES DISTINTOS — exactamente lo que hace un re-OCR."""
    def _fake(entrada, salida, **kw):
        salida = Path(salida)
        salida.parent.mkdir(parents=True, exist_ok=True)
        n = corrida["n"]
        build_pdf(salida, [
            ["CEDULA DE EMPLAZAMIENTO",
             "Juzgado de Primera Instancia numero cinco de la ciudad de Barcelona",
             f"En la villa de Barcelona se emplaza a la parte demandada (pase {n})"], [],
            ["A U T O numero doce dictado por el juzgado en las presentes actuaciones",
             "Vistos los antecedentes de hecho y los fundamentos de derecho aplicables",
             f"este tribunal acuerda lo que se detalla a continuacion (pase {n})"], [],
            ["FACTURA por servicios de mediacion inmobiliaria efectivamente prestados",
             "Se detallan a continuacion los conceptos facturados y el importe total",
             f"con el desglose de la base imponible y el impuesto (pase {n})"],
        ])
        return ResultadoEscalera(salida, "redo")
    return _fake


def test_reprocesar_sustituye_en_vez_de_anadir(caso, monkeypatch):
    corrida = {"n": 1}
    monkeypatch.setattr(sm, "ocr_pdf_escalera", _escalera_que_reescribe(corrida))

    cli.apply("W-TEST99")
    corrida["n"] = 2
    cli.apply("W-TEST99", force=True)

    sm_dir = sm._sala_maquina_dir(caso)
    rel = "01_Drive EV/bundle.pdf"
    src = caso / "00_Input" / rel
    parent = output_slug(rel, file_sha256(src))
    carpeta = sm_dir / "02_Documentos" / parent

    pdfs = sorted(p.name for p in carpeta.glob("*.pdf"))
    mds = sorted(p.name for p in (sm_dir / "03_MD").glob(f"{parent}__*.md"))
    txts = sorted(p.name for p in (sm_dir / "raw_text").glob(f"{parent}__*.txt"))
    assert len(pdfs) == 3, f"una generación por documento lógico, no dos: {pdfs}"
    assert len(mds) == 3 and len(txts) == 3

    filas = json.loads((sm_dir / "_cobertura.json").read_text(encoding="utf-8"))
    segmentos = [f for f in filas if f["rel_path"] == rel and f["doc_id"]]
    assert len(segmentos) == 3, "la cobertura acumuló dos generaciones"
    assert sorted(f["doc_id"] for f in segmentos) == ["d01", "d02", "d03"]

    # Los tres hashes coherentes: la fila declara los bytes que hay en disco.
    for f in segmentos:
        assert file_sha256(carpeta / f"{f['slug']}.pdf") == f["sha256"]
        assert (sm_dir / "03_MD" / f"{f['slug']}.md").exists()
        assert (sm_dir / "raw_text" / f"{f['slug']}.txt").exists()

    # Y la generación anterior está archivada entera, no borrada.
    archivos = sorted((caso / sm.VERSIONES_ANTERIORES).glob("reproceso_*/*"))
    assert len(archivos) == 9, f"9 = 3 documentos × 3 representaciones; hay {len(archivos)}"

    # El reproceso SÍ escribió: el MD nuevo trae el texto del segundo pase.
    md = next((sm_dir / "03_MD").glob(f"{parent}__d01_*.md")).read_text(encoding="utf-8")
    assert "pase 2" in md
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_split_reproceso_e2e.py -x -q`
Expected: **PASS** si las Tareas 1-7 están bien. Para comprobar que el test **mide el defecto** y no
es vacuo, revertir temporalmente `_slug_seg` a la forma vieja
(`f"{parent_slug}__seg{seg:02d}_{_norm_tipo(tipo)}__{seg_sha256[:8]}"`, con su llamada) y volver a
correrlo: debe fallar con 6 PDFs y 6 filas. Restaurar después.

- [ ] **Step 3: Suite completa, medición read-only y documentación**

Suite completa y comparación contra la base del Paso 0:

```powershell
python -m pytest -q --tb=no --junit-xml=$env:TEMP\pieza_a.xml
```

Medición **read-only** sobre los 5 casos con Sala de máquina — comprueba si el guard abortaría por
daño histórico (decisión 8 del plan). **No escribe nada**; si abortase en algún caso, es un hallazgo
para Nikolai, no una razón para relajar el guard:

```powershell
python -c "import json,pathlib,sys; sys.path.insert(0,'.'); from core import sala_maquina as sm; from core.config import CASOS_ROOT
for caso in pathlib.Path(CASOS_ROOT).rglob('_cobertura.json'):
    cd = caso.parent.parent.parent
    cob = sm.cobertura_desde_dicts(json.loads(caso.read_text(encoding='utf-8')))
    parents = {c.parent_slug for c in cob if c.parent_slug}
    fallos = sm.verificar_integridad_bundles(cd, cob, parents)
    print(cd.name, len(parents), 'bundles ->', len(fallos), 'discrepancias')"
```

Documentación:

1. Cabecera del spec → `> **Estado:** rev. 3 · **pieza A CONSTRUIDA** (PR #NNN). Pieza B sigue ⛔ bloqueada.`
2. `PLAN.md`, fila #1 punto (f), segunda viñeta: marcar la **pieza A** como ✅ con el hash del
   squash, conservando la pieza B como bloqueada y su gate.
3. `docs/MEJORAS_FUTURAS.md`, entrada nueva al final:

```markdown
## 113. Límites declarados de la identidad persistente del segmento (pieza A)

*Abierta 2026-08-02 al construir la pieza A de
`docs/superpowers/specs/2026-08-01-identidad-segmento-bundle-design.md`. No es un bug: son
las tres fronteras que la pieza A deja dibujadas a propósito, escritas para que nadie las
descubra al pisarlas.*

1. **El preflight valida identidad, no rangos.** Los rangos exigen el nº de páginas del
   buscable, que en un escaneado no existe antes del OCR. Se siguen validando dentro de
   `_split_o_md`, con el total real. Consecuencia: un manifiesto con rangos imposibles
   sigue muriendo documento a documento, no en el preflight.
2. **La reconciliación de `--force` sobre un escaneado tampoco es preflightable** (su
   manifiesto propuesto sale de `detectar`, que exige el buscable). La cubren el
   aislamiento por documento y el guard bidireccional, que aborta con salida 3.
3. **Un manifiesto legacy sin `doc_id` aborta la corrida normal** de ese bundle, con un
   mensaje que apunta al retrofit de la pieza B y a la salida disponible hoy (`--force`).
   Coste operativo real: hasta que la pieza B se desbloquee, un bundle ya materializado
   con el esquema viejo solo se reprocesa con `--force`. Se eligió fail-closed porque
   acuñar identidades en silencio congelaría la identidad equivocada si un `--force`
   histórico renumeró los `seg`.
```

- [ ] **Step 4: Verificar**

Run: `python -m pytest -q --tb=no --junit-xml=$env:TEMP\pieza_a.xml`
Expected: `failures=0`, `errors=0`; `tests` = base + los tests nuevos; `skipped` y `xfailed`
iguales a la base (los 7 `xfail` de la arquitectura dual siguen `xfail`, ninguno en `XPASS`).

Run: `python -m pytest tests/test_split_reproceso_e2e.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_split_reproceso_e2e.py docs/superpowers/specs/2026-08-01-identidad-segmento-bundle-design.md PLAN.md docs/MEJORAS_FUTURAS.md
```

```bash
git commit -m "test+docs(split): aceptacion del reproceso que sustituye, y limites declarados (MEJORAS #113)"
```

---

## Criterio de salida (spec §9)

- [ ] Los tests de reconciliación (6), preflight (7) y custodia (8) pasan **y mueren al retirarles su
      arreglo** — mutación verificada, incluida la de «acuñar siempre».
- [ ] Preflight: manifiesto inválido aborta desde la CLI con exit ≠ 0 y **cero artefactos escritos**.
- [ ] Suite verde contra la base medida en el Paso 0; `xfail` sin `XPASS`.
- [ ] **Ningún caso real tocado** (la única mirada a `G:` es read-only y no escribe).
- [ ] Revisión adversarial de este plan **y** de la rev. 3 del spec consumida y adjudicada: la
      adjudicación va embebida en el documento revisado con su encabezado canónico, y el informe
      literal del revisor a su acta hermana `…-adversarial-review.md` con su `sha256` (guards G7/G8
      de `tests/test_docs_gobernanza.py`).
- [ ] PR con `leak-scan` verde. `pytest` corrido en local: **el CI no lo corre**.

## Lo que este plan NO hace

- **Pieza B** (retrofit de manifiestos existentes, saneamiento de los 5 grupos duplicados, journal
  con `resume`/`rollback`/`adopt`): ⛔ bloqueada por el lock de exclusión roto
  (`test_defecto_doble_titular` sigue en `xfail`; `cmd_checkin` no verifica nonce al empezar). Gate:
  la Fase 2 de la fila #3 de `PLAN.md`.
- **Auditar el daño histórico** (5 segmentos duplicados y 12 ficheros huérfanos en W-02VND1 y
  W-02VUDR): es de la pieza B. El guard mira solo lo que la corrida toca.
- **`MEJORAS #111`** (el reproceso puede perder palabras: 77 de 6.405 en un segmento medido). Es un
  problema del motor de OCR, no de la identidad, y sigue abierto.
