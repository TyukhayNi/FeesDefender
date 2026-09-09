---
estado: vigente
dueño: Nikolai Tyukhay
fecha: 2026-09-09
spec: docs/superpowers/specs/2026-07-27-vista-procesal-05-procedimiento-design.md
diseño: docs/superpowers/plans/2026-09-09-vista-procesal-pieza4.md
---

# Vista procesal — pieza 4a: la vista que solo lee · Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** que el letrado pueda ver, para un expediente judicial, **qué documentos tiene el
procedimiento, en qué fase va cada uno, qué falta y qué bloquea** — y que la máquina tenga esa
misma respuesta en un objeto. Sin escribir un byte en el expediente.

**Architecture:** paquete `core/procedimiento/` con siete módulos de una responsabilidad cada
uno. **No existe ruta de escritura en el código de esta mitad**: no hay `copiar`, no hay ledger,
no hay `os.replace`, y la única capacidad que se exige al workspace es `READ_CASE`. La
autorización y la raíz de trabajo vienen del *resolver* del workspace, no de una ruta del
catálogo. El CLI emite el informe y, opcionalmente, un **borrador de mapa** a `stdout`.

**Tech Stack:** Python 3.14, `pyyaml`, `pytest`, `typer`. Sin dependencias nuevas.

**Por qué esta mitad existe:** la rev. 1 del plan de la pieza 4 volvió de revisión adversarial
en **NO-SHIP con 23 hallazgos**, y cuatro de sus seis críticos vivían en la parte que solo lee —
estaban ahí porque la parte que escribe contaminaba su diseño. El reparto, los ocho invariantes y
la adjudicación completa están en el documento de diseño
`2026-09-09-vista-procesal-pieza4.md`. **Esta mitad no puede destruir datos de cliente por
construcción**, y por eso le corresponde **1** ronda de revisión, sobre su diff.

---

## Global Constraints

Aplican a **todas** las tareas.

- **Ninguno de los módulos de esta pieza escribe en el expediente. Ni un fichero de estado,
  ni un log, ni un `mkdir`.** Si una tarea de este plan necesita escribir en el caso, la tarea
  está mal: es de 4b, o de una pieza propia.
  - **Redacción exacta a propósito.** La versión anterior decía «cero escrituras» a secas, y la
    revisión adversarial demostró que era falsa por dos vías: la propia Tarea 2 ampliaba los
    destinos de un escritor (H-01, ya retirado a su pieza), y la cadena que la fachada invoca
    puede escribir **fuera** del expediente — `WorkspaceRegistry` renombra un registro corrupto
    al leerlo (H-05, pendiente). Lo que se sostiene es lo que dice esta línea.
- **La única capacidad que se exige es `READ_CASE`** (`core/casos/workspace_model.Capability`).
  No se pide `WRITE_CASE` ni `GENERATE_DERIVATIVES` en ningún sitio.
- **La autoridad viene del *resolver*, no del catálogo** (I0). Nada usa
  `case_locator.buscar()` para decidir dónde trabajar; la raíz es `ws.working_root`.
- **La raíz autorizada se identifica primero y no se re-deriva** de la ruta que se juzga (I3).
- **Precedencia de fuentes: CRM > ocurrencias > manifiesto de intake.** `_intake_hashes.json`
  queda **fuera de la ruta de confianza** (spec §0, §2.1).
- **Tres conjuntos, nunca uno por otro** (I4): universo `listadas`, materialización
  `materializadas`, y `pull_state.doc_ids` = lo que bajó *la última corrida*.
- **La vista no promete buscabilidad.** Reporta lo que la cobertura declara, sabiendo que la
  declaración puede ser optimista (spec §0, §2.4).
- **Encoding UTF-8 sin BOM** en todo fichero escrito (`CLAUDE.md`).
- **Higiene PII:** el caso se referencia solo por `W-XXXXXX` — en el plan, en los tests, en los
  commits y en los fixtures. Ni nombres, ni direcciones, **ni dentro de un script que «no se va a
  commitear»**. Lo sensible se resuelve en ejecución, desde el localizador y desde
  `data/_config/pii_blocklist.txt` (gitignored). El verde del `leak-guard` no acredita limpieza:
  es una denylist, y los términos de este caso no estaban en ella hasta el 2026-09-09.
- **Tests: ningún test escribe en el árbol de producción.** Árbol sintético en `tmp_path`, pasado
  a la función (`CLAUDE.md`; patrón en `tests/test_guard_localizador.py::_arbol_sintetico`).
- **Un test se acepta cuando se le ha visto ponerse ROJO con su defecto puesto** (I6). Los pasos
  de mutante de este plan no son opcionales: son la única prueba de que el test apunta a algo.
- **Intérprete:** el `python` del PATH en este equipo es un Python pelado sin las dependencias.
  Usar `C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe` (los worktrees no llevan venv
  propio) o activar el venv de la raíz.

---

## File Structure

| Fichero | Responsabilidad |
|---|---|
| `core/procedimiento/__init__.py` | Fachada: `informe()`. Nada de lógica |
| `core/procedimiento/carpetas.py` | La lista blanca de las cinco carpetas de fase |
| `core/procedimiento/sede.py` | **I0 + I3.** Autorización, raíz autorizada, y contención de rutas |
| `core/procedimiento/mapa.py` | **I3.** Carga y validación de `_mapa_procesal.yaml`, con gramática |
| `core/procedimiento/universo.py` | **I4.** Los tres conjuntos del CRM y sus puertas |
| `core/procedimiento/artefacto.py` | **I5.** Qué fichero *representa* a cada documento, y su calidad |
| `core/procedimiento/informe.py` | El resultado: por fase, lo asignado, lo pendiente, lo bloqueado |
| `core/procedimiento/borrador.py` | Propone `orden` y `descripción` para un mapa nuevo (a `stdout`) |
| `scripts/procedimiento.py` | CLI `informe` / `borrador-mapa` |
| `.claude/skills/_shared/registrar_outputs.py` | **Modificar:** ampliar `SUBDESTINOS_EXTRA` |

Paquete y no módulo único porque `core/` ya usa paquetes para piezas de este tamaño
(`core/anon/`, `core/casos/`, `core/email_atomize/`), y porque la autorización, la gramática del
mapa y el selector de artefacto son tres cuerpos de reglas que se revisan por separado.

---

## Task 1: la sede — de dónde viene la autoridad, y qué rutas son legítimas

Va primera porque **todo lo demás depende de ella**: sin raíz autorizada no hay ruta que leer, y
sin autorización no hay derecho a leerla. Cierra los invariantes I0 y la base de I3.

**Files:**
- Create: `core/procedimiento/__init__.py`
- Create: `core/procedimiento/sede.py`
- Test: `tests/test_procedimiento_sede.py`

**Interfaces:**
- Consumes: `core.casos.workspace_model.{CaseRef, Capability, CapabilityDenied, WorkspaceError}`,
  `core.casos.workspace_resolver.CaseWorkspaceResolver`, `core.casos.case_catalog.CaseCatalog`.
- Produces:
  - `sede.SedeError(Exception)` — no hay sede utilizable; su `.motivo` explica por qué.
  - `sede.raiz_autorizada(ws) -> Path` — `ws.working_root` **resuelto una vez**, tras exigir
    `READ_CASE`. Lanza `SedeError` si el workspace no tiene raíz (modos bloqueados).
  - `sede.contener(raiz: Path, *partes: str) -> Path` — construye una ruta **desde** la raíz ya
    identificada y verifica que ningún componente de la cadena redirige. Lanza `SedeError`.
  - `sede.TAGS_QUE_REDIRIGEN: frozenset[int]` — solo *junction* y *symlink*.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_procedimiento_sede.py
"""I0 e I3: la autoridad viene del resolver, y la raíz se identifica ANTES de juzgar rutas."""
import os
import pathlib

import pytest

from core.casos.workspace_model import Capability
from core.procedimiento import sede


class _WsFalso:
    """Doble mínimo de `CaseWorkspace`: lo que `sede` consume y nada más.

    Se usa un doble y no un `CaseWorkspace` real porque el real DERIVA
    `capabilities` del modo y no las acepta en el constructor — es su garantía, y
    fabricar un modo concreto aquí probaría el resolver, no la sede.
    """

    def __init__(self, working_root, caps=(Capability.READ_CASE,)):
        self.working_root = working_root
        self.capabilities = frozenset(caps)
        self.exigidas = []

    def exigir(self, cap):
        self.exigidas.append(cap)
        if cap not in self.capabilities:
            from core.casos.workspace_model import CapabilityDenied
            raise CapabilityDenied(f"falta {cap}")


def test_la_raiz_sale_del_workspace_y_EXIGE_read_case(tmp_path):
    ws = _WsFalso(tmp_path)
    r = sede.raiz_autorizada(ws)
    assert r == tmp_path.resolve()
    assert Capability.READ_CASE in ws.exigidas, (
        "la raíz se entregó sin exigir la capacidad: la autorización sería decorativa")


def test_un_workspace_SIN_read_case_no_recibe_raiz(tmp_path):
    ws = _WsFalso(tmp_path, caps=())
    with pytest.raises(sede.SedeError) as exc:
        sede.raiz_autorizada(ws)
    assert "read_case" in str(exc.value).lower()


def test_un_workspace_sin_raiz_de_trabajo_es_SedeError(tmp_path):
    """Los modos bloqueados (`blocked_foreign_checkout`) traen `working_root=None`.
    Devolver `None` haría que el llamador construyera rutas contra la cwd."""
    with pytest.raises(sede.SedeError):
        sede.raiz_autorizada(_WsFalso(None))


def test_contener_construye_desde_la_raiz_y_no_desde_la_ruta(tmp_path):
    (tmp_path / "05_Procedimiento").mkdir()
    p = sede.contener(tmp_path, "05_Procedimiento")
    assert p == (tmp_path / "05_Procedimiento").resolve()


@pytest.mark.parametrize("parte", [
    "..", "../fuera", "05_Procedimiento/../..", "/abs", "C:/otra", r"\\servidor\share",
])
def test_contener_rechaza_lo_que_sale_de_la_raiz(tmp_path, parte):
    with pytest.raises(sede.SedeError):
        sede.contener(tmp_path, parte)


def test_solo_se_vetan_los_dos_tags_que_REDIRIGEN(tmp_path):
    """**La trampa que haría inservible la pieza.** Un placeholder de Drive Stream (`G:`)
    también lleva `st_reparse_tag`, pero NO redirige la ruta: virtualiza el contenido.
    Vetar «cualquier tag» haría que la vista se negara a leer TODOS los casos reales,
    que es donde viven. Solo se vetan *junction* y *symlink*."""
    import stat as _stat
    assert sede.TAGS_QUE_REDIRIGEN == frozenset({
        getattr(_stat, "IO_REPARSE_TAG_MOUNT_POINT", 0xA0000003),
        getattr(_stat, "IO_REPARSE_TAG_SYMLINK", 0xA000000C),
    })
    # un tag de nube inventado no está en el set y por tanto no veta
    assert 0x9000001A not in sede.TAGS_QUE_REDIRIGEN


@pytest.mark.skipif(os.name != "nt", reason="las junctions son de Windows")
def test_una_JUNCTION_en_la_cadena_veta_la_ruta(tmp_path):
    """El defecto que el revisor reprodujo: si `05_Procedimiento` es una junction al
    crudo, una comprobación que resuelva AMBOS lados se aprueba a sí misma."""
    import subprocess
    destino = tmp_path / "crudo"
    destino.mkdir()
    enlace = tmp_path / "05_Procedimiento"
    subprocess.run(["cmd", "/c", "mklink", "/J", str(enlace), str(destino)],
                   check=True, capture_output=True)
    with pytest.raises(sede.SedeError) as exc:
        sede.contener(tmp_path, "05_Procedimiento")
    assert "redirige" in str(exc.value).lower()


@pytest.mark.skipif(os.name != "nt", reason="las junctions son de Windows")
def test_una_junction_en_un_ANCESTRO_tambien_veta(tmp_path):
    """`is_symlink()` sobre la hoja no ve un reparse point en un directorio padre."""
    import subprocess
    real = tmp_path / "real"
    (real / "05_Procedimiento").mkdir(parents=True)
    enlace = tmp_path / "via"
    subprocess.run(["cmd", "/c", "mklink", "/J", str(enlace), str(real)],
                   check=True, capture_output=True)
    with pytest.raises(sede.SedeError):
        sede.contener(enlace, "05_Procedimiento")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_procedimiento_sede.py -q --tb=short`
Expected: FAIL con `ModuleNotFoundError: No module named 'core.procedimiento'`

- [ ] **Step 3: Write the implementation**

```python
# core/procedimiento/__init__.py
"""Vista procesal de `05_Procedimiento` — pieza 4a: la mitad que solo lee.

No hay ruta de escritura en este paquete. La única capacidad que se exige es `READ_CASE`.
"""
```

```python
# core/procedimiento/sede.py
"""De dónde viene la autoridad, y qué rutas son legítimas (invariantes I0 e I3).

**I0 — la autoridad la da el resolver del workspace, no el catálogo.** El mutex del caso
(`MEJORAS #126`) impide que otro proceso de ESTA máquina entre a la vez; no dice nada
sobre si el caso está prestado a OTRA. Eso lo dice el modo del workspace, y la raíz de
trabajo es `ws.working_root` — nunca una ruta que resolvamos nosotros. `sala_maquina` ya
pasó por aquí y su docstring lo cuenta: «antes esto resolvía una ruta y escribía sin
preguntar a nadie».

**I3 — la raíz se identifica PRIMERO y no se re-deriva de la ruta que se juzga.** Una
comprobación del estilo `destino.resolve().relative_to((base / "x").resolve())` se aprueba
a sí misma cuando `x` es una junction: los dos lados resuelven al mismo sitio ajeno. Aquí
la raíz entra ya resuelta y la ruta se CONSTRUYE desde ella.
"""
from __future__ import annotations

import os
import stat
from pathlib import Path, PurePosixPath, PureWindowsPath

from core.casos.workspace_model import Capability, CapabilityDenied

#: Los DOS tags que redirigen una ruta a otro sitio. No se veta ningún otro, y eso es
#: deliberado: un placeholder de Drive Stream o de OneDrive también trae
#: `st_reparse_tag` (`IO_REPARSE_TAG_CLOUD*`) y **no redirige nada** — virtualiza el
#: contenido. Vetar «cualquier tag distinto de cero» dejaría la vista incapaz de leer los
#: expedientes reales, que viven precisamente en `G:`.
TAGS_QUE_REDIRIGEN: frozenset[int] = frozenset({
    getattr(stat, "IO_REPARSE_TAG_MOUNT_POINT", 0xA0000003),   # junction
    getattr(stat, "IO_REPARSE_TAG_SYMLINK", 0xA000000C),       # symlink
})


class SedeError(Exception):
    """No hay sede utilizable, o la ruta pedida no es legítima. Falla CERRADO."""


def raiz_autorizada(ws) -> Path:
    """Raíz de trabajo del caso, **resuelta una vez**, tras exigir `READ_CASE`.

    Se exige la capacidad ANTES de devolver la ruta: al revés, el llamador tendría la
    ruta en la mano y la autorización sería decorativa.
    """
    try:
        ws.exigir(Capability.READ_CASE)
    except CapabilityDenied as exc:
        raise SedeError(
            f"este workspace no autoriza `read_case`: {exc}") from exc
    raiz = getattr(ws, "working_root", None)
    if raiz is None:
        raise SedeError(
            "el workspace no tiene raíz de trabajo (modo bloqueado o sin copia local): "
            "no hay nada que leer, y no se sustituye por la cwd")
    return Path(raiz).resolve()


def _redirige(p: Path) -> bool:
    """`True` si este componente concreto redirige a otro sitio."""
    try:
        st = os.lstat(p)
    except OSError:
        return False                    # no existe: no puede redirigir
    if stat.S_ISLNK(st.st_mode):
        return True
    return getattr(st, "st_reparse_tag", 0) in TAGS_QUE_REDIRIGEN


def contener(raiz: Path, *partes: str) -> Path:
    """Ruta bajo `raiz`, verificando que ningún componente de la cadena redirige.

    `raiz` entra **ya identificada** (de `raiz_autorizada`). Las `partes` son relativas y
    no pueden salir: ni `..`, ni absoluta, ni UNC.
    """
    raiz = Path(raiz).resolve()
    if not _redirige_cadena_ok(raiz):
        raise SedeError(f"la propia raíz autorizada redirige: {raiz}")

    rel = PurePosixPath(*[str(x).replace("\\", "/") for x in partes if str(x)])
    if rel.is_absolute() or PureWindowsPath(str(rel)).is_absolute():
        raise SedeError(f"la parte pedida es absoluta y no relativa a la raíz: {rel}")
    if str(rel).startswith("//") or str(rel).startswith("\\\\"):
        raise SedeError(f"ruta UNC no admitida: {rel}")
    if any(seg in ("..", "") for seg in rel.parts):
        raise SedeError(f"la ruta intenta salir de la raíz: {rel}")

    destino = raiz
    for seg in rel.parts:
        destino = destino / seg
        if _redirige(destino):
            raise SedeError(
                f"un componente de la ruta redirige a otro sitio y no se sigue: "
                f"{destino}. Si es legítimo, resuélvelo fuera de la vista")
    # Comparación final SIN volver a resolver la raíz desde el destino: la raíz manda.
    try:
        destino.resolve().relative_to(raiz)
    except ValueError as exc:
        raise SedeError(
            f"{destino} no cae bajo la raíz autorizada {raiz}") from exc
    return destino


def _redirige_cadena_ok(raiz: Path) -> bool:
    """La raíz y sus ancestros no redirigen. Se comprueba una vez, no por ruta."""
    p = raiz
    vistos = 0
    while vistos < 64:                  # cota: cadenas patológicas no cuelgan
        if _redirige(p):
            return False
        if p.parent == p:
            return True
        p = p.parent
        vistos += 1
    return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_procedimiento_sede.py -q --tb=short`
Expected: PASS (13 tests, 0 skipped en Windows)

- [ ] **Step 5: Ver los mutantes ROJOS — sin esto los tests no acreditan nada (I6)**

Tres mutantes, uno por invariante. Cada uno se aplica **en memoria** (no se edita el módulo),
se comprueba que el test correspondiente **falla**, y se descarta.

```python
# scratch/mutantes_sede.py — NO se commitea: es un arnés de un solo uso
"""Cada mutante rompe UNA propiedad. Si su test sigue verde, el test está mal apuntado."""
import subprocess
import sys

MUTANTES = {
    # (1) la raíz se entrega sin exigir la capacidad
    "sin_exigir": ("core/procedimiento/sede.py",
                   "        ws.exigir(Capability.READ_CASE)",
                   "        pass  # MUTANTE"),
    # (2) se vetan TODOS los tags, no solo los que redirigen
    "veta_todo": ("core/procedimiento/sede.py",
                  "    return getattr(st, \\"st_reparse_tag\\", 0) in TAGS_QUE_REDIRIGEN",
                  "    return getattr(st, \\"st_reparse_tag\\", 0) != 0  # MUTANTE"),
    # (3) la contención se re-deriva del destino: se aprueba a sí misma
    "reresuelve": ("core/procedimiento/sede.py",
                   "        if _redirige(destino):",
                   "        if False:  # MUTANTE"),
}
TESTS = {
    "sin_exigir": "tests/test_procedimiento_sede.py::test_la_raiz_sale_del_workspace_y_EXIGE_read_case",
    "veta_todo": "tests/test_procedimiento_sede.py::test_solo_se_vetan_los_dos_tags_que_REDIRIGEN",
    "reresuelve": "tests/test_procedimiento_sede.py::test_una_JUNCTION_en_la_cadena_veta_la_ruta",
}
PY = sys.executable
for nombre, (fichero, viejo, nuevo) in MUTANTES.items():
    original = open(fichero, encoding="utf-8").read()
    assert viejo in original, f"{nombre}: el ancla no existe, el mutante no muta nada"
    try:
        open(fichero, "w", encoding="utf-8").write(original.replace(viejo, nuevo, 1))
        r = subprocess.run([PY, "-m", "pytest", TESTS[nombre], "-q", "--no-header",
                            "-p", "no:randomly"], capture_output=True, text=True)
        veredicto = "MUERTO (test rojo, bien)" if r.returncode != 0 else \
                    "VIVO  (test verde: EL TEST ESTA MAL APUNTADO)"
        print(f"  {nombre:<12} {veredicto}")
    finally:
        open(fichero, "w", encoding="utf-8").write(original)
```

Run: `.venv\Scripts\python.exe scratch/mutantes_sede.py`
Expected: los tres **MUERTO**. Un `VIVO` significa que hay que arreglar el test, no el mutante.

- [ ] **Step 6: Run test to verify the module is intact after the harness**

Run: `.venv\Scripts\python.exe -m pytest tests/test_procedimiento_sede.py -q --tb=short`
Expected: PASS (13). El arnés restaura el fichero en un `finally`; esto lo comprueba.

- [ ] **Step 7: Medir el reparse tag real de un caso en `G:` — declarado SIN MEDIR hoy**

**Esto no se pudo medir el 2026-09-09**: `G:` tenía letra asignada pero el montaje estaba
vacío (Drive for Desktop sin arrancar), y este worktree no hereda `CASOS_ROOT`. Queda como
paso del plan, no como afirmación.

```bash
CASOS_ROOT="<raíz de casos>" .venv/Scripts/python.exe -c "import os,stat,pathlib,sys; sys.path.insert(0,'.'); from core.procedimiento.sede import TAGS_QUE_REDIRIGEN as T; r=pathlib.Path(os.environ['CASOS_ROOT']); f=next(r.rglob('*.pdf')); t=getattr(os.lstat(f),'st_reparse_tag',0); print(f'tag={t:#010x} vetado={t in T}')"
```
Expected: `vetado=False`. **Si sale `True`, el set de tags está mal y la pieza no puede leer
los casos reales** — es el fallo que el test del Step 1 existe para evitar, y aquí se
confirma contra el Drive de verdad. Si `G:` sigue sin montar, se anota SIN MEDIR y **no** se
declara verificado.

- [ ] **Step 8: Commit**

```bash
git add core/procedimiento/__init__.py core/procedimiento/sede.py tests/test_procedimiento_sede.py
git commit -m "vista procesal 4a: la sede — autorizacion por workspace y contencion de rutas (I0, I3)"
```

---

## Task 2: las cinco carpetas de fase, como set cerrado

La tarea más pequeña del plan. Es la **fuente** de la lista que valida el mapa del letrado:
`mapa.es_carpeta_fase` y `vista.por_carpeta` la consumen, y no escribe nada.

> **Lo que esta tarea YA NO hace, y por qué.** Su primera versión ampliaba además
> `SUBDESTINOS_EXTRA` de `registrar_outputs`, para que un escrito generado se registrara en su
> fase (spec §7). **La revisión adversarial lo sacó de aquí** (su H-01): ampliar esa tupla
> amplía dónde puede escribir un helper que escribe, y contradecía la restricción global de
> esta pieza. Nikolai decidió el 2026-09-09 darle su propia pieza, con su propia revisión:
> `docs/superpowers/plans/2026-09-09-destinos-de-fase-registrar-outputs.md`.
>
> Con ello 4a vuelve a tener radio de daño **cero por construcción** y su ronda única queda
> bien fundada, que es el punto de la decisión.

**Files:**
- Create: `core/procedimiento/carpetas.py`
- Modify: `.claude/skills/_shared/registrar_outputs.py` (el bloque `SUBDESTINOS_EXTRA`)
- Test: `tests/test_procedimiento_carpetas.py`

**Interfaces:**
- Consumes: nada.
- Produces: `carpetas.CARPETAS_FASE: tuple[str, ...]` (las cinco, en orden),
  `carpetas.CARPETA_OTROS: str`, `carpetas.CARPETAS_CON_RECTOR: tuple[str, ...]`,
  `carpetas.es_carpeta_fase(nombre: str) -> bool`.

**Nota sobre los rótulos:** el spec nombra tres literalmente (`01_Monitorio - Demanda y
documentos`, `03_Ordinario - Demanda y documentos`, `05_Otros escritos`) y deduce dos de la tabla
de bloques de §11.1. Los dos intermedios se fijan **aquí**, y van **sin tilde** por coherencia
con `02_Analisis` y `99_Sin categoria` del propio repo. Si Nikolai prefiere otros rótulos, se
cambia esta constante y nada más.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_procedimiento_carpetas.py
"""Las cinco carpetas de fase son un set CERRADO y un solo sitio las nombra."""
import importlib.util
import pathlib

import pytest

from core.procedimiento import carpetas


def test_son_exactamente_cinco_y_en_orden():
    assert carpetas.CARPETAS_FASE == (
        "01_Monitorio - Demanda y documentos",
        "02_Monitorio - Oposicion y documentos",
        "03_Ordinario - Demanda y documentos",
        "04_Ordinario - Contestacion y documentos",
        "05_Otros escritos",
    )


def test_el_cajon_de_otros_es_la_quinta():
    assert carpetas.CARPETA_OTROS == "05_Otros escritos"
    assert carpetas.CARPETA_OTROS in carpetas.CARPETAS_FASE


def test_las_cuatro_primeras_llevan_escrito_rector():
    assert carpetas.CARPETAS_CON_RECTOR == carpetas.CARPETAS_FASE[:4]
    assert carpetas.CARPETA_OTROS not in carpetas.CARPETAS_CON_RECTOR


@pytest.mark.parametrize("nombre", list(carpetas.CARPETAS_FASE))
def test_reconoce_las_cinco(nombre):
    assert carpetas.es_carpeta_fase(nombre) is True


@pytest.mark.parametrize("nombre", [
    "Jurisprudencia",                      # subcarpeta legítima, pero NO de fase
    "01_Monitorio",                        # prefijo, no el nombre completo
    "06_Otra cosa",
    "",
    "05_Otros escritos/sub",               # una ruta no es una carpeta de fase
    "05_OTROS ESCRITOS",                   # el set es sensible a la grafía exacta
    " 05_Otros escritos",                  # ni con espacio delante
])
def test_rechaza_lo_que_no_es_carpeta_de_fase(nombre):
    assert carpetas.es_carpeta_fase(nombre) is False


def test_registrar_outputs_admite_las_cinco_sin_drift():
    """Las dos listas viven en sitios distintos por una razón —el `.skill` empaquetado no
    tiene `core/`, así que importarlo rompería la skill en el servidor— y este test las
    ata: si alguien añade una carpeta de fase y no toca el helper, el escrito se
    registraría fuera de su fase."""
    ruta = (pathlib.Path(__file__).resolve().parents[1]
            / ".claude" / "skills" / "_shared" / "registrar_outputs.py")
    spec = importlib.util.spec_from_file_location("registrar_outputs_shared", ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    esperadas = {f"05_Procedimiento/{c}" for c in carpetas.CARPETAS_FASE}
    assert esperadas <= set(mod.SUBDESTINOS_EXTRA), (
        "faltan carpetas de fase en SUBDESTINOS_EXTRA: "
        f"{sorted(esperadas - set(mod.SUBDESTINOS_EXTRA))}")
    assert esperadas <= mod.DESTINOS_VALIDOS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_procedimiento_carpetas.py -q --tb=short`
Expected: FAIL con `ImportError: cannot import name 'carpetas'`

- [ ] **Step 3: Write the implementation**

```python
# core/procedimiento/carpetas.py
"""Las cinco carpetas de fase de `05_Procedimiento`. Un solo sitio que las nombre.

Set CERRADO: el mapa del letrado se valida contra esta tupla y `registrar_outputs` la
replica para que un escrito generado se registre en su fase (spec §7).
"""
from __future__ import annotations

#: En orden de lectura del pleito. El prefijo numérico es parte del nombre.
CARPETAS_FASE: tuple[str, ...] = (
    "01_Monitorio - Demanda y documentos",
    "02_Monitorio - Oposicion y documentos",
    "03_Ordinario - Demanda y documentos",
    "04_Ordinario - Contestacion y documentos",
    "05_Otros escritos",
)

#: El cajón que recoge lo procesal que no es un escrito rector con sus documentos.
#: Es lo que hace cumplible la exigencia de que nada quede sin asignar (spec §11.1).
CARPETA_OTROS: str = "05_Otros escritos"

#: Las cuatro primeras llevan escrito rector: el borrador les propone `orden: "00"` cuando
#: el nombre del CRM no trae número de documento. La quinta usa la fecha del lote.
CARPETAS_CON_RECTOR: tuple[str, ...] = CARPETAS_FASE[:4]

_SET = frozenset(CARPETAS_FASE)


def es_carpeta_fase(nombre: str) -> bool:
    """`True` solo para una de las cinco, con su grafía exacta.

    No normaliza: un rótulo aproximado es un error del mapa que hay que ver, no algo que
    adivinar. La comparación `casefold` del spec §3.1 es para detectar COLISIONES entre
    destinos, no para aceptar variantes del nombre de la carpeta.
    """
    return nombre in _SET
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_procedimiento_carpetas.py -q --tb=short`
Expected: FAIL en `test_registrar_outputs_admite_las_cinco_sin_drift` (el helper aún no las
tiene) y PASS en el resto (12 de 13). Es el rojo que pide el Step 5.

- [ ] **Step 5: Ampliar `DESTINOS_VALIDOS` del helper de las skills**

En `.claude/skills/_shared/registrar_outputs.py`, sustituir el bloque de `SUBDESTINOS_EXTRA`
por:

```python
# Subcarpeta dedicada a jurisprudencia descargada (decisión #2 del plan v3).
# Y las cinco carpetas de fase de la vista procesal (spec 2026-07-27 §7): un escrito
# generado se registra en la fase donde `escritos-judiciales` lo escribió. Se repiten
# aquí como literales, y NO se importan de `core.procedimiento.carpetas`, porque este
# helper viaja dentro del `.skill` empaquetado y ahí `core/` no existe: importarlo
# rompería la skill en el servidor. El test de no-drift de
# `tests/test_procedimiento_carpetas.py` es lo que mantiene las dos listas alineadas.
SUBDESTINOS_EXTRA: tuple[str, ...] = (
    "05_Procedimiento/Jurisprudencia",
    "05_Procedimiento/01_Monitorio - Demanda y documentos",
    "05_Procedimiento/02_Monitorio - Oposicion y documentos",
    "05_Procedimiento/03_Ordinario - Demanda y documentos",
    "05_Procedimiento/04_Ordinario - Contestacion y documentos",
    "05_Procedimiento/05_Otros escritos",
)
```

- [ ] **Step 6: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_procedimiento_carpetas.py -q --tb=short`
Expected: PASS (13 tests)

- [ ] **Step 7: Sincronizar el helper a las siete skills**

`registrar_outputs.py` está replicado **byte a byte** en las carpetas `scripts/` de siete
skills, porque el `.skill` empaquetado tiene que ser autónomo. `sync_skill_helpers.py` copia
**todo** `_shared/*.py` a esas siete, y `tests/test_skill_helpers_sync.py::test_helpers_sin_drift`
se pone **rojo** en cuanto la fuente y una copia difieren. Editar el Step 5 sin este paso deja
la suite en rojo y las skills registrando con la lista vieja.

Run: `.venv\Scripts\python.exe scripts/sync_skill_helpers.py`
Expected: imprime los ficheros escritos; entre ellos siete `registrar_outputs.py`

- [ ] **Step 8: Verificar que no queda drift**

Run: `.venv\Scripts\python.exe -m pytest tests/test_skill_helpers_sync.py -q --tb=short`
Expected: PASS (2 tests). Si sale rojo, **no** se toca el test: se vuelve a correr el sync.

- [ ] **Step 9: Commit**

Las siete copias entran en el MISMO commit que la fuente: separarlas deja un commit intermedio
con la suite en rojo.

```bash
git add core/procedimiento/carpetas.py tests/test_procedimiento_carpetas.py \
        ".claude/skills/_shared/registrar_outputs.py" \
        ".claude/skills/*/scripts/registrar_outputs.py"
git commit -m "vista procesal 4a: las cinco carpetas de fase, y las skills pueden registrar en ellas"
```

---

## Task 3: los tres conjuntos del CRM

El invariante I4, que es donde la rev. 1 se rompió de la forma más caraforma: su puerta habría
bloqueado 74 de los 76 documentos del expediente para el que se diseñó la pieza.

**Files:**
- Create: `core/procedimiento/universo.py`
- Test: `tests/test_procedimiento_universo.py`

**Interfaces:**
- Consumes: `core.ocurrencias_crm.{RegistroOcurrencias, RegistroInvalidoError}`,
  `core.case_manager.read_pull_state`.
- Produces:
  - `universo.Conjuntos` — dataclass frozen: `listadas: dict[str, dict]`,
    `materializadas: dict[str, dict]`, `descargadas: frozenset[str]`,
    `total_crm: int | None`, `errores_pull: tuple[str, ...]`.
  - `universo.UniversoError(Exception)`
  - `universo.leer(case_id: str, expediente_id: str, *, registro=None, pull_state=None) -> Conjuntos`
  - `universo.incoherencias(c: Conjuntos) -> tuple[str, ...]` — lo que hay que mirar, en
    prosa; **vacío no significa completo**, significa coherente.

**Los tres conjuntos, y por qué no se pueden usar uno por otro** (verificado el 2026-09-09):

| Conjunto | De dónde sale | Qué significa |
|---|---|---|
| `listadas` | `RegistroOcurrencias.listadas(exp)` | **el universo**: todo lo que el CRM enumeró |
| `materializadas` | `RegistroOcurrencias.materializadas(exp)` | además está en disco y se puede leer |
| `descargadas` | `pull_state.doc_ids` (D8) | lo que bajó **la última corrida**, y nada más |

`core/case_manager.py:1638` lo dice literal: «`doc_ids`: IDs numéricos de los documentos
**descargados**». Y `core/sync_sudespacho.py:1669` hace el `append` **dentro** del bucle de
descarga, después de filtrar `only_doc_ids` — el régimen de **intake acotado**, que mantiene
`documents_total_crm` con el total real del CRM. Por eso `total_crm` puede superar a
`len(descargadas)` sin que nada esté mal.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_procedimiento_universo.py
"""I4: universo, materialización y descargas de la última corrida son TRES cosas."""
import pytest

from core.ocurrencias_crm import RegistroOcurrencias
from core.procedimiento import universo


def _registro(filas):
    """Doble del registro con `revisiones` reales, para no depender de su constructor."""
    reg = RegistroOcurrencias.__new__(RegistroOcurrencias)
    reg.ocurrencias = {
        f"crm:540:{d}": {"source": "crm", "expediente_id": "540", "doc_id": d,
                         "revisiones": [{"estado": estado, "filename": f"{d}.pdf",
                                         "modified_at": "2026-01-01T00:00:00+01:00",
                                         "id_carpeta": "307",
                                         "path": (f"05_CRM/99_Otros/{d}.pdf"
                                                  if estado == "materializada" else None),
                                         "sha256": (f"SHA{d}" if estado == "materializada"
                                                    else None)}]}
        for d, estado in filas.items()
    }
    return reg


def test_el_intake_ACOTADO_no_produce_ni_una_incoherencia(tmp_path):
    """**El defecto que mató la rev. 1.** 76 enumerados, 2 bajados: es el régimen normal
    del intake judicial acotado (spec §1.1), no un error. Una puerta que exija
    `listadas ⊆ descargadas` bloquearía los otros 74 y haría la pieza inservible."""
    filas = {str(i): ("materializada" if i in (1, 2) else "listada") for i in range(1, 77)}
    c = universo.leer("CASO", "540", registro=_registro(filas),
                      pull_state={"documents_total_crm": 76, "doc_ids": ["1", "2"]})
    assert len(c.listadas) == 76
    assert len(c.materializadas) == 2
    assert c.descargadas == frozenset({"1", "2"})
    assert universo.incoherencias(c) == (), (
        f"el régimen acotado se reportó como incoherente: {universo.incoherencias(c)}")


def test_una_descargada_que_no_esta_en_el_universo_SI_es_incoherente(tmp_path):
    """Al revés sí es un problema: el pull dice haber bajado algo que el registro no
    enumera, así que uno de los dos está rancio."""
    c = universo.leer("CASO", "540", registro=_registro({"1": "materializada"}),
                      pull_state={"documents_total_crm": 1, "doc_ids": ["1", "99"]})
    assert any("99" in x for x in universo.incoherencias(c))


def test_una_descargada_sin_materializar_es_incoherente(tmp_path):
    """El pull dice que la bajó y el registro dice que no está en disco."""
    c = universo.leer("CASO", "540", registro=_registro({"1": "listada"}),
                      pull_state={"documents_total_crm": 1, "doc_ids": ["1"]})
    assert any("1" in x for x in universo.incoherencias(c))


def test_un_total_del_CRM_que_no_cuadra_con_el_universo_se_reporta(tmp_path):
    c = universo.leer("CASO", "540", registro=_registro({"1": "listada"}),
                      pull_state={"documents_total_crm": 9, "doc_ids": []})
    assert any("9" in x for x in universo.incoherencias(c))


def test_un_pull_state_AUSENTE_no_se_lee_como_cero_descargas(tmp_path):
    """`None` es «no lo sé», no «no bajó nada». Confundirlos haría que un caso sin
    `_caso.md` pareciera coherente."""
    c = universo.leer("CASO", "540", registro=_registro({"1": "materializada"}),
                      pull_state=None)
    assert c.descargadas is None
    assert c.total_crm is None
    assert any("pull_state" in x.lower() for x in universo.incoherencias(c))


def test_un_registro_AUSENTE_es_UniversoError_y_no_un_universo_vacio(tmp_path):
    """`RegistroOcurrencias.load()` devuelve vacío si el fichero no está —contrato
    legítimo para su productor— y la vista NO puede aceptarlo (spec §5.1): un universo
    vacío diría «este expediente no tiene documentos», que es indistinguible de
    «todavía no se ha hecho el pull»."""
    reg = RegistroOcurrencias.__new__(RegistroOcurrencias)
    reg.ocurrencias = {}
    with pytest.raises(universo.UniversoError) as exc:
        universo.leer("CASO", "540", registro=reg,
                      pull_state={"documents_total_crm": 3, "doc_ids": []})
    assert "sync_sudespacho" in str(exc.value)


def test_ocurrencias_de_OTRO_expediente_no_se_mezclan(tmp_path):
    reg = _registro({"1": "materializada"})
    reg.ocurrencias["crm:999:7"] = {
        "source": "crm", "expediente_id": "999", "doc_id": "7",
        "revisiones": [{"estado": "materializada", "filename": "x.pdf",
                        "modified_at": "x", "id_carpeta": "1",
                        "path": "05_CRM/99_Otros/x.pdf", "sha256": "S"}]}
    c = universo.leer("CASO", "540", registro=reg,
                      pull_state={"documents_total_crm": 1, "doc_ids": ["1"]})
    assert set(c.listadas) == {"1"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_procedimiento_universo.py -q --tb=short`
Expected: FAIL con `ImportError: cannot import name 'universo'`

- [ ] **Step 3: Write the implementation**

```python
# core/procedimiento/universo.py
"""Los tres conjuntos del CRM y sus puertas (invariante I4).

La rev. 1 de este plan conflató dos de ellos y el efecto fue doble: en el régimen de
intake **acotado** —2 documentos bajados de 76, que es el normal en el intake judicial—
habría bloqueado los otros 74; y con `doc_ids` vacío se saltaba el cruce entero y las
`solo_listadas` no aparecían por ningún lado. O sea: inservible y a la vez silencioso.

    listadas        el UNIVERSO: todo lo que el CRM enumeró
    materializadas  además está en disco
    descargadas     lo que bajó LA ÚLTIMA CORRIDA (`pull_state.doc_ids`, D8)

`core/case_manager.py:1638` y `core/sync_sudespacho.py:1669` son la prueba de la tercera.
"""
from __future__ import annotations

from dataclasses import dataclass


class UniversoError(Exception):
    """No se puede establecer el universo del expediente. Falla CERRADO."""


@dataclass(frozen=True)
class Conjuntos:
    expediente_id: str
    listadas: dict[str, dict]
    materializadas: dict[str, dict]
    #: `None` = no se pudo leer el `pull_state`. NO es «no bajó nada».
    descargadas: frozenset[str] | None
    total_crm: int | None
    errores_pull: tuple[str, ...] = ()

    @property
    def solo_listadas(self) -> dict[str, dict]:
        """Enumeradas por el CRM y NO en disco. El hueco del intake acotado."""
        return {d: r for d, r in self.listadas.items() if d not in self.materializadas}


def leer(case_id: str, expediente_id: str, *, registro=None,
         pull_state: dict | None = ...) -> Conjuntos:
    """Los tres conjuntos. `registro` y `pull_state` se inyectan en los tests."""
    expediente_id = str(expediente_id).strip()

    if registro is None:
        from core.ocurrencias_crm import RegistroOcurrencias
        registro = RegistroOcurrencias(case_id)
        registro.load()
    if pull_state is ...:
        from core.case_manager import read_pull_state
        pull_state = read_pull_state(case_id, expediente_id)

    listadas = registro.listadas(expediente_id)
    materializadas = registro.materializadas(expediente_id)

    if not listadas:
        raise UniversoError(
            f"el registro de ocurrencias no enumera ni un documento del expediente "
            f"{expediente_id!r}. Un universo vacío es indistinguible de «todavía no se ha "
            f"hecho el pull», y la vista no puede decidir sobre esa ambigüedad: corre "
            f"`sync_sudespacho intake-judicial` (o `pull`) y vuelve")

    ps = pull_state or {}
    descargadas = (frozenset(str(d) for d in ps["doc_ids"])
                   if isinstance(ps.get("doc_ids"), list) else None)
    total = ps.get("documents_total_crm")
    return Conjuntos(
        expediente_id=expediente_id,
        listadas=listadas,
        materializadas=materializadas,
        descargadas=descargadas,
        total_crm=total if isinstance(total, int) else None,
        errores_pull=tuple(str(e) for e in (ps.get("errors") or [])),
    )


def incoherencias(c: Conjuntos) -> tuple[str, ...]:
    """Lo que no cuadra entre los tres conjuntos. **Vacío = coherente, no completo.**

    Lo que NO es una incoherencia: que haya `listadas` sin materializar. Eso es el
    régimen acotado y es normal (spec §1.1).
    """
    out: list[str] = []

    if c.descargadas is None:
        out.append(
            "no se pudo leer el `pull_state` del expediente: sin él no se puede cruzar lo "
            "que el CRM enumeró con lo que la última corrida bajó. No se asume que no bajó "
            "nada")
    else:
        fuera = sorted(c.descargadas - set(c.listadas))
        if fuera:
            out.append(
                f"el `pull_state` dice haber descargado doc_id que el registro no enumera: "
                f"{fuera}. Uno de los dos está rancio; regenera el pull")
        sin_disco = sorted(c.descargadas & set(c.solo_listadas))
        if sin_disco:
            out.append(
                f"el `pull_state` dice haber descargado {sin_disco} y el registro los tiene "
                f"solo como `listada`: el fichero no está en disco")

    if c.total_crm is not None and c.total_crm != len(c.listadas):
        out.append(
            f"el `pull_state` dice {c.total_crm} documentos en el CRM y el registro enumera "
            f"{len(c.listadas)}: el universo puede estar incompleto")

    if c.errores_pull:
        out.append(
            f"la última corrida del pull dejó {len(c.errores_pull)} error(es), así que el "
            f"universo puede no estar completo: {list(c.errores_pull[:3])}")

    return tuple(out)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_procedimiento_universo.py -q --tb=short`
Expected: PASS (7 tests)

- [ ] **Step 5: Ver el mutante ROJO del invariante que mató la rev. 1**

```python
# scratch/mutantes_universo.py — NO se commitea
"""El mutante es literalmente el defecto de la rev. 1: exigir que el universo esté bajado."""
import subprocess
import sys

FICHERO = "core/procedimiento/universo.py"
VIEJO = "        fuera = sorted(c.descargadas - set(c.listadas))"
NUEVO = "        fuera = sorted(set(c.listadas) - c.descargadas)  # MUTANTE: la rev. 1"
TEST = ("tests/test_procedimiento_universo.py::"
        "test_el_intake_ACOTADO_no_produce_ni_una_incoherencia")

original = open(FICHERO, encoding="utf-8").read()
assert VIEJO in original, "el ancla no existe: el mutante no muta nada"
try:
    open(FICHERO, "w", encoding="utf-8").write(original.replace(VIEJO, NUEVO, 1))
    r = subprocess.run([sys.executable, "-m", "pytest", TEST, "-q", "--no-header",
                        "-p", "no:randomly"], capture_output=True, text=True)
    print("MUERTO (rojo, bien)" if r.returncode else "VIVO (EL TEST ESTA MAL APUNTADO)")
finally:
    open(FICHERO, "w", encoding="utf-8").write(original)
```

Run: `.venv\Scripts\python.exe scratch/mutantes_universo.py`
Expected: `MUERTO`. Con el mutante puesto, el test del intake acotado debe reportar 74
incoherencias y fallar.

- [ ] **Step 6: Run test to verify the module is intact**

Run: `.venv\Scripts\python.exe -m pytest tests/test_procedimiento_universo.py -q --tb=short`
Expected: PASS (7)

- [ ] **Step 7: Commit**

```bash
git add core/procedimiento/universo.py tests/test_procedimiento_universo.py
git commit -m "vista procesal 4a: los tres conjuntos del CRM, y el intake acotado deja de bloquear (I4)"
```

---

## Task 4: el mapa del letrado, con gramática

El invariante I3 en su mitad de entrada: todo lo que entre por aquí acabará, en 4b, siendo una
escritura en el expediente. Que 4a no escriba no rebaja la validación — la adelanta.

**Files:**
- Create: `core/procedimiento/mapa.py`
- Test: `tests/test_procedimiento_mapa.py`

**Interfaces:**
- Consumes: `carpetas.{CARPETAS_FASE, es_carpeta_fase}`, `sede.{contener, SedeError}`.
- Produces:
  - `mapa.EntradaMapa` — frozen: `carpeta`, `origen`, `doc_id`, `orden`, `descripcion`,
    `fichero`, `eco_crm`, `sin_cobertura_ok`, `logical_key`.
  - `mapa.MapaProcesal` — frozen: `version`, `expediente_crm`, `entradas`, `sin_asignar`.
  - `mapa.MapaInvalidoError(Exception)` con `.problemas: list[str]`.
  - `mapa.MAPA_FILENAME`, `mapa.VERSION_SOPORTADA`, `mapa.ORIGEN_CRM`, `mapa.ORIGEN_DESPACHO`
  - `mapa.cargar(raiz: Path) -> MapaProcesal` — lanza con **todos** los problemas.
  - `mapa.nombre_destino(e: EntradaMapa, ext: str) -> str`
  - `mapa.presupuesto_longitud(raiz, carpeta, nombre) -> str`

**Tres cosas que la rev. 1 dejaba pasar y aquí no:**

1. **`orden` sin gramática.** `orden: ../00` producía `../00_x.pdf` y salía de la carpeta de
   fase. Ahora `orden` casa `^[A-Z]{0,2}-?\d{1,3}[A-Z]?$` (cubre `00`, `D-01`, `D-02A`) y nada
   más.
2. **Tipos YAML coercionados.** `sin_cobertura_ok: 'false'` se volvía `True` con `bool()`, y
   `version: true` pasaba por `1`. Ahora un booleano tiene que ser booleano y la versión, `int`.
3. **Nombres reservados de Windows con varias extensiones.** `.stem` de `NUL.extra.docx` es
   `NUL.extra`, que no casaba el set; ahora se mira el **primer** componente.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_procedimiento_mapa.py
"""Carga y validación de `_mapa_procesal.yaml` (spec §3.1, §3.2) con gramática (I3)."""
import pytest

from core.procedimiento import mapa


def _escribir(tmp_path, texto: str):
    d = tmp_path / "05_Procedimiento"
    d.mkdir(parents=True, exist_ok=True)
    (d / mapa.MAPA_FILENAME).write_text(texto, encoding="utf-8")
    return tmp_path


CARP = "03_Ordinario - Demanda y documentos"


def test_carga_el_camino_feliz(tmp_path):
    raiz = _escribir(tmp_path, f"""
version: 1
expediente_crm: '540'
carpetas:
  "{CARP}":
    - {{origen: crm, doc_id: '34939', orden: 'D-01', descripcion: encargo_de_venta}}
    - {{origen: despacho, fichero: CONCLUSIONES_W-02VEKE.docx}}
sin_asignar:
  - {{doc_id: '42498', fichero: citacion.pdf, lote: '2026-07-27T16:35'}}
""")
    m = mapa.cargar(raiz)
    assert m.version == 1
    assert m.expediente_crm == "540"
    crm, desp = m.entradas
    assert crm.logical_key == "crm:540:34939"
    assert crm.sin_cobertura_ok is False
    assert desp.logical_key == "despacho:CONCLUSIONES_W-02VEKE.docx"
    assert len(m.sin_asignar) == 1


def test_acumula_TODOS_los_problemas_no_solo_el_primero(tmp_path):
    """Reportar el primero obliga al letrado a N pasadas para N errores."""
    raiz = _escribir(tmp_path, """
version: 1
expediente_crm: '540'
carpetas:
  "99_Carpeta inventada":
    - {origen: crm, doc_id: '1', orden: '00', descripcion: x}
  "05_Otros escritos":
    - {origen: marciano, doc_id: '2', orden: '00', descripcion: y}
    - {origen: despacho, fichero: 'sub/dir/escrito.docx'}
""")
    with pytest.raises(mapa.MapaInvalidoError) as exc:
        mapa.cargar(raiz)
    assert len(exc.value.problemas) == 3
    txt = "\n".join(exc.value.problemas)
    assert "99_Carpeta inventada" in txt and "marciano" in txt and "sub/dir" in txt


@pytest.mark.parametrize("orden", ["../00", "..", "00/..", "a" * 40, "", "00 ", "./00"])
def test_un_orden_sin_gramatica_se_RECHAZA(tmp_path, orden):
    """El defecto de la rev. 1: `orden` se incrustaba en el nombre sin validar, así que
    `../00` producía un destino fuera de la carpeta de fase."""
    raiz = _escribir(tmp_path, f"""
version: 1
expediente_crm: '540'
carpetas:
  "05_Otros escritos":
    - {{origen: crm, doc_id: '1', orden: '{orden}', descripcion: x}}
""")
    with pytest.raises(mapa.MapaInvalidoError) as exc:
        mapa.cargar(raiz)
    assert "orden" in "\n".join(exc.value.problemas)


@pytest.mark.parametrize("orden", ["00", "01", "D-01", "D-02A", "999", "DA-9"])
def test_los_ordenes_legitimos_pasan(tmp_path, orden):
    raiz = _escribir(tmp_path, f"""
version: 1
expediente_crm: '540'
carpetas:
  "05_Otros escritos":
    - {{origen: crm, doc_id: '1', orden: '{orden}', descripcion: x}}
""")
    assert mapa.cargar(raiz).entradas[0].orden == orden


def test_un_string_false_NO_autoriza_el_override(tmp_path):
    """`bool('false')` es `True`. El operador puede creer desactivado un permiso que está
    ejercido, y este permiso autoriza a copiar documentos no buscables."""
    raiz = _escribir(tmp_path, """
version: 1
expediente_crm: '540'
carpetas:
  "05_Otros escritos":
    - {origen: crm, doc_id: '1', orden: '00', descripcion: x, sin_cobertura_ok: 'false'}
""")
    with pytest.raises(mapa.MapaInvalidoError) as exc:
        mapa.cargar(raiz)
    assert "sin_cobertura_ok" in "\n".join(exc.value.problemas)


def test_una_version_booleana_no_pasa_por_uno(tmp_path):
    raiz = _escribir(tmp_path, "version: true\nexpediente_crm: '540'\ncarpetas: {}\n")
    with pytest.raises(mapa.MapaInvalidoError) as exc:
        mapa.cargar(raiz)
    assert "version" in "\n".join(exc.value.problemas)


@pytest.mark.parametrize("fichero,fragmento", [
    ("'../fuera.docx'", "basename"),
    ("'/abs/escrito.docx'", "basename"),
    ("'CON'", "reservado"),
    ("'NUL.extra.docx'", "reservado"),
    ("'COM1.docx'", "reservado"),
    ("'escrito.docx '", "espacios o puntos"),
    ("'escrito.'", "espacios o puntos"),
    ("'a:b.docx'", "caracter"),
    ("'q?.docx'", "caracter"),
])
def test_rechaza_ficheros_invalidos_del_despacho(tmp_path, fichero, fragmento):
    raiz = _escribir(tmp_path, f"""
version: 1
expediente_crm: '540'
carpetas:
  "05_Otros escritos":
    - {{origen: despacho, fichero: {fichero}}}
""")
    with pytest.raises(mapa.MapaInvalidoError) as exc:
        mapa.cargar(raiz)
    assert fragmento in "\n".join(exc.value.problemas)


def test_una_clave_YAML_duplicada_no_sustituye_una_decision_en_silencio(tmp_path):
    """`safe_load` se queda la última y el letrado no se enteraría de que su primera
    asignación de esa carpeta desapareció."""
    raiz = _escribir(tmp_path, """
version: 1
expediente_crm: '540'
carpetas:
  "05_Otros escritos":
    - {origen: crm, doc_id: '1', orden: '00', descripcion: primera}
  "05_Otros escritos":
    - {origen: crm, doc_id: '2', orden: '01', descripcion: segunda}
""")
    with pytest.raises(mapa.MapaInvalidoError) as exc:
        mapa.cargar(raiz)
    assert "duplicada" in "\n".join(exc.value.problemas)


def test_rechaza_clave_logica_duplicada_entre_carpetas(tmp_path):
    raiz = _escribir(tmp_path, f"""
version: 1
expediente_crm: '540'
carpetas:
  "01_Monitorio - Demanda y documentos":
    - {{origen: crm, doc_id: '77', orden: '00', descripcion: demanda}}
  "{CARP}":
    - {{origen: crm, doc_id: '77', orden: '00', descripcion: demanda}}
""")
    with pytest.raises(mapa.MapaInvalidoError) as exc:
        mapa.cargar(raiz)
    assert "crm:540:77" in "\n".join(exc.value.problemas)


def test_dos_entradas_que_producen_el_MISMO_nombre_final_colisionan(tmp_path):
    """Distinto de la clave lógica duplicada: son dos documentos distintos que darían el
    mismo destino, y en Windows la comparación es `casefold`."""
    raiz = _escribir(tmp_path, """
version: 1
expediente_crm: '540'
carpetas:
  "05_Otros escritos":
    - {origen: crm, doc_id: '1', orden: '00', descripcion: Decreto_Admision}
    - {origen: crm, doc_id: '2', orden: '00', descripcion: decreto_admision}
""")
    with pytest.raises(mapa.MapaInvalidoError) as exc:
        mapa.cargar(raiz)
    assert "mismo nombre" in "\n".join(exc.value.problemas)


def test_yaml_ilegible_y_mapa_ausente_no_degradan_a_vacio(tmp_path):
    raiz = _escribir(tmp_path, "version: 1\ncarpetas: [[[\n")
    with pytest.raises(mapa.MapaInvalidoError):
        mapa.cargar(raiz)
    (tmp_path / "otro" / "05_Procedimiento").mkdir(parents=True)
    with pytest.raises(mapa.MapaInvalidoError) as exc:
        mapa.cargar(tmp_path / "otro")
    assert "no existe" in "\n".join(exc.value.problemas)


def test_nombre_destino_crm_y_despacho():
    crm = mapa.EntradaMapa(carpeta=CARP, origen="crm", doc_id="1", orden="D-02",
                           descripcion="Contrato de Mediación")
    assert mapa.nombre_destino(crm, "pdf") == "D-02_contrato_de_mediacion.pdf"
    desp = mapa.EntradaMapa(carpeta=CARP, origen="despacho",
                            fichero="CONCLUSIONES_W-02VEKE.docx")
    assert mapa.nombre_destino(desp, "docx") == "CONCLUSIONES_W-02VEKE.docx", (
        "la herramienta no renombra lo que no ha creado")


def test_el_presupuesto_de_longitud_cuenta_el_TEMPORAL(tmp_path):
    """La rev. 1 presupuestaba la ruta final y se olvidaba del temporal, que sale 11
    caracteres más largo: la promesa de respetar el límite quedaba incumplida."""
    largo = "D-02_" + ("x" * 400) + ".pdf"
    n = mapa.presupuesto_longitud(tmp_path, "05_Otros escritos", largo)
    final = tmp_path / "05_Procedimiento" / "05_Otros escritos" / n
    temporal = final.with_name(f".{n}.{'9' * 6}.tmp")
    assert len(str(final)) <= mapa.LIMITE_RUTA
    assert len(str(temporal)) <= mapa.LIMITE_RUTA, (
        "el temporal no cabe: la escritura de 4b fallaría con el nombre que 4a bendijo")
    assert n.endswith(".pdf")


def test_el_truncado_es_ESTABLE_entre_llamadas(tmp_path):
    largo = "D-02_" + ("y" * 400) + ".pdf"
    a = mapa.presupuesto_longitud(tmp_path, "05_Otros escritos", largo)
    b = mapa.presupuesto_longitud(tmp_path, "05_Otros escritos", largo)
    assert a == b, "un sufijo inestable haría que cada corrida viera un cambio"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_procedimiento_mapa.py -q --tb=short`
Expected: FAIL con `ImportError: cannot import name 'mapa'`

- [ ] **Step 3: Write the implementation**

```python
# core/procedimiento/mapa.py
"""Carga y validación de `05_Procedimiento/_mapa_procesal.yaml` (spec §3).

El mapa lo escribe el LETRADO: es la única fuente de la asignación documento → carpeta.
La vista **no** propone la carpeta (spec §0); sí propone `orden` y `descripción`, y eso
vive en `borrador.py`.

Que esta mitad no escriba no rebaja la validación: la adelanta. Todo lo que se acepte aquí
acabará, en 4b, siendo una escritura en el expediente real.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, replace
from pathlib import Path

import yaml

from .carpetas import CARPETAS_FASE, es_carpeta_fase

MAPA_FILENAME = "_mapa_procesal.yaml"
VERSION_SOPORTADA = 1

ORIGEN_CRM = "crm"
ORIGEN_DESPACHO = "despacho"
ORIGENES = (ORIGEN_CRM, ORIGEN_DESPACHO)

#: Gramática de `orden`. Cubre `00`, `01`, `D-01`, `D-02A`, `DA-9`; y NADA más — porque
#: este valor se incrusta en un nombre de fichero. La rev. 1 no lo validaba y `../00`
#: producía un destino fuera de la carpeta de fase.
_RE_ORDEN = re.compile(r"^[A-Z]{0,2}-?\d{1,3}[A-Z]?$")

#: Caracteres que Windows no admite en un nombre de fichero.
_PROHIBIDOS = set('<>:"/\\|?*') | {chr(c) for c in range(32)}

#: Nombres de dispositivo reservados. Se compara el PRIMER componente: el `.stem` de
#: `NUL.extra.docx` es `NUL.extra` y no casaría.
_RESERVADOS_WINDOWS = frozenset(
    ["con", "prn", "aux", "nul"]
    + [f"com{i}" for i in range(1, 10)]
    + [f"lpt{i}" for i in range(1, 10)])

#: Tope práctico de ruta absoluta en Windows sin rutas largas activadas.
LIMITE_RUTA = 259
LIMITE_SEGMENTO = 255
#: Lo que 4b añadirá al nombre para el temporal: `.<nombre>.<pid>.tmp`. Se presupuesta
#: aquí porque quien bendice el nombre es esta mitad.
MARGEN_TEMPORAL = len(".") + len(".") + 6 + len(".tmp")


class MapaInvalidoError(Exception):
    """El mapa no cumple el contrato. Trae TODOS los problemas, no el primero."""

    def __init__(self, problemas: list[str]) -> None:
        self.problemas = problemas
        super().__init__(f"{len(problemas)} problema(s) en {MAPA_FILENAME}:\n"
                         + "\n".join(f"  - {p}" for p in problemas))


@dataclass(frozen=True)
class EntradaMapa:
    carpeta: str
    origen: str
    doc_id: str | None = None
    orden: str | None = None
    descripcion: str | None = None
    fichero: str | None = None
    eco_crm: str | None = None
    sin_cobertura_ok: bool = False
    logical_key: str = ""


@dataclass(frozen=True)
class MapaProcesal:
    version: int
    expediente_crm: str
    entradas: tuple[EntradaMapa, ...] = ()
    sin_asignar: tuple[dict, ...] = ()


class _CargadorSinDuplicados(yaml.SafeLoader):
    """`safe_load` se queda la última de dos claves iguales, en silencio.

    En un mapa eso significa que la asignación de una carpeta entera desaparece sin que
    el letrado se entere. Aquí es un error.
    """


def _sin_duplicados(loader, node, deep=False):
    salida = {}
    for k_node, v_node in node.value:
        k = loader.construct_object(k_node, deep=deep)
        if k in salida:
            raise yaml.YAMLError(f"clave duplicada en el YAML: {k!r}")
        salida[k] = loader.construct_object(v_node, deep=deep)
    return salida


_CargadorSinDuplicados.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _sin_duplicados)


def mapa_path(raiz: Path) -> Path:
    return Path(raiz) / "05_Procedimiento" / MAPA_FILENAME


def _slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def nombre_destino(e: EntradaMapa, ext: str) -> str:
    """Nombre final del fichero en su carpeta.

    `origen: despacho` conserva SU nombre: la herramienta no renombra lo que no ha creado
    (spec §0). `origen: crm` se nombra `<orden>_<descripcion>.<ext>`.
    """
    if e.origen == ORIGEN_DESPACHO:
        return e.fichero or ""
    ext = str(ext).lstrip(".")
    return f"{e.orden}_{_slug(e.descripcion or '')}" + (f".{ext}" if ext else "")


def presupuesto_longitud(raiz: Path, carpeta: str, nombre: str) -> str:
    """`nombre`, truncado con sufijo hash ESTABLE si la ruta no cabe **con su temporal**.

    El sufijo sale del nombre completo, así que es determinista entre corridas: dos
    lecturas seguidas producen el mismo destino.
    """
    base = (Path(raiz).resolve() / "05_Procedimiento" / carpeta)
    tope = LIMITE_RUTA - MARGEN_TEMPORAL
    if len(str(base / nombre)) <= tope and len(nombre) + MARGEN_TEMPORAL <= LIMITE_SEGMENTO:
        return nombre
    stem, _, ext = nombre.rpartition(".")
    if not stem:
        stem, ext = nombre, ""
    sufijo = "~" + hashlib.sha256(nombre.encode("utf-8")).hexdigest()[:8]
    cola = f".{ext}" if ext else ""
    margen = min(tope - len(str(base)) - 1 - len(sufijo) - len(cola),
                 LIMITE_SEGMENTO - MARGEN_TEMPORAL - len(sufijo) - len(cola))
    if margen < 1:
        raise MapaInvalidoError([
            f"la ruta de {carpeta!r} no admite ningún nombre con su temporal: "
            f"{len(str(base))} caracteres de carpeta sobre un tope de {tope}"])
    return f"{stem[:margen]}{sufijo}{cola}"


def _validar_nombre_windows(nombre: str, donde: str, problemas: list[str]) -> bool:
    malos = sorted(_PROHIBIDOS & set(nombre))
    if malos:
        problemas.append(f"{donde}: {nombre!r} lleva un caracter que Windows no admite: "
                         f"{[c if c.isprintable() else hex(ord(c)) for c in malos]}")
        return False
    if nombre.split(".")[0].lower() in _RESERVADOS_WINDOWS:
        problemas.append(f"{donde}: {nombre!r} usa un nombre reservado de Windows")
        return False
    if nombre != nombre.strip() or nombre.rstrip(" .") != nombre:
        problemas.append(f"{donde}: {nombre!r} tiene espacios o puntos al principio o al "
                         f"final")
        return False
    return True


def _validar_entrada(carpeta: str, i: int, raw: object,
                     problemas: list[str]) -> EntradaMapa | None:
    donde = f"{carpeta!r}[{i}]"
    if not isinstance(raw, dict):
        problemas.append(f"{donde}: cada entrada debe ser un mapa, no "
                         f"{type(raw).__name__}")
        return None

    origen = raw.get("origen")
    if origen not in ORIGENES:
        problemas.append(f"{donde}: `origen` es {origen!r}; válidos: {list(ORIGENES)}")
        return None

    if origen == ORIGEN_CRM:
        faltan = [c for c in ("doc_id", "orden", "descripcion") if not raw.get(c)]
        if faltan:
            problemas.append(f"{donde}: la rama `crm` exige {faltan}")
            return None
        orden = str(raw["orden"])
        if not _RE_ORDEN.match(orden):
            problemas.append(
                f"{donde}: `orden` {orden!r} no casa la gramática {_RE_ORDEN.pattern} — "
                f"este valor se incrusta en el nombre del fichero")
            return None
        descripcion = str(raw["descripcion"])
        if not _slug(descripcion):
            problemas.append(f"{donde}: `descripcion` {descripcion!r} queda vacía al "
                             f"normalizarla, así que no puede nombrar un fichero")
            return None
        sco = raw.get("sin_cobertura_ok", False)
        if not isinstance(sco, bool):
            problemas.append(
                f"{donde}: `sin_cobertura_ok` debe ser un booleano de YAML y es "
                f"{sco!r} ({type(sco).__name__}). `'false'` no desactiva nada: "
                f"`bool('false')` es True, y este permiso autoriza a copiar documentos "
                f"no buscables")
            return None
        return EntradaMapa(carpeta=carpeta, origen=origen, doc_id=str(raw["doc_id"]),
                           orden=orden, descripcion=descripcion, sin_cobertura_ok=sco)

    fichero = raw.get("fichero")
    if not fichero or not isinstance(fichero, str):
        problemas.append(f"{donde}: la rama `despacho` exige `fichero` como texto")
        return None
    if "/" in fichero or "\\" in fichero or Path(fichero).is_absolute():
        problemas.append(f"{donde}: `fichero` debe ser un basename, no una ruta: "
                         f"{fichero!r}")
        return None
    if fichero in (".", ".."):
        problemas.append(f"{donde}: `fichero` no puede ser {fichero!r}")
        return None
    if not _validar_nombre_windows(fichero, donde, problemas):
        return None
    eco = raw.get("eco_crm")
    if eco is not None and not isinstance(eco, (str, int)):
        problemas.append(f"{donde}: `eco_crm` debe ser el doc_id, no "
                         f"{type(eco).__name__}")
        return None
    return EntradaMapa(carpeta=carpeta, origen=origen, fichero=fichero,
                       eco_crm=None if eco is None else str(eco),
                       logical_key=f"{ORIGEN_DESPACHO}:{fichero}")


def cargar(raiz: Path) -> MapaProcesal:
    """Lee y valida el mapa. Lanza `MapaInvalidoError` con TODOS los problemas."""
    p = mapa_path(raiz)
    problemas: list[str] = []
    if not p.is_file():
        raise MapaInvalidoError([
            f"no existe {p}. La asignación documento → fase es del letrado; usa "
            f"`procedimiento borrador-mapa` para partir de una propuesta"])
    try:
        datos = yaml.load(p.read_text(encoding="utf-8"), _CargadorSinDuplicados) or {}
    except yaml.YAMLError as exc:
        raise MapaInvalidoError([f"YAML ilegible: {exc}"]) from exc
    if not isinstance(datos, dict):
        raise MapaInvalidoError([f"la raíz debe ser un mapa, no {type(datos).__name__}"])

    version = datos.get("version")
    if not isinstance(version, int) or isinstance(version, bool) \
            or version != VERSION_SOPORTADA:
        problemas.append(f"`version` es {version!r} ({type(version).__name__}); "
                         f"soportada: el entero {VERSION_SOPORTADA}")
    expediente = datos.get("expediente_crm")
    if not expediente or not isinstance(expediente, (str, int)):
        problemas.append("falta `expediente_crm`, o no es el id del expediente")
    expediente = str(expediente).strip() if expediente else ""

    crudas = datos.get("carpetas") or {}
    if not isinstance(crudas, dict):
        problemas.append(f"`carpetas` debe ser un mapa, no {type(crudas).__name__}")
        crudas = {}

    entradas: list[EntradaMapa] = []
    for carpeta, lista in crudas.items():
        if not es_carpeta_fase(str(carpeta)):
            problemas.append(f"carpeta fuera de la lista blanca: {carpeta!r}; válidas: "
                             f"{list(CARPETAS_FASE)}")
            continue
        if not isinstance(lista, list):
            problemas.append(f"{carpeta!r}: debe contener una lista de entradas")
            continue
        for i, raw in enumerate(lista):
            e = _validar_entrada(str(carpeta), i, raw, problemas)
            if e is None:
                continue
            if e.origen == ORIGEN_CRM:
                e = replace(e, logical_key=f"{ORIGEN_CRM}:{expediente}:{e.doc_id}")
            entradas.append(e)

    vistas: dict[str, str] = {}
    destinos: dict[str, str] = {}
    for e in entradas:
        if e.logical_key in vistas:
            problemas.append(f"clave lógica duplicada {e.logical_key!r}: en "
                             f"{vistas[e.logical_key]!r} y en {e.carpeta!r}")
        else:
            vistas[e.logical_key] = e.carpeta
        # Colisión de nombre final. La extensión no se conoce todavía, así que se
        # compara el tronco: dos entradas con el mismo tronco en la misma carpeta
        # colisionan en cualquier extensión.
        tronco = f"{e.carpeta}/{nombre_destino(e, '')}".casefold()
        if tronco in destinos:
            problemas.append(
                f"dos entradas producen el mismo nombre final en {e.carpeta!r}: "
                f"{destinos[tronco]} y {e.logical_key}")
        else:
            destinos[tronco] = e.logical_key

    if problemas:
        raise MapaInvalidoError(problemas)

    sin_asignar = tuple(d for d in (datos.get("sin_asignar") or [])
                        if isinstance(d, dict))
    return MapaProcesal(version=int(version), expediente_crm=expediente,
                        entradas=tuple(entradas), sin_asignar=sin_asignar)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_procedimiento_mapa.py -q --tb=short`
Expected: PASS (37 tests, contando las parametrizaciones)

- [ ] **Step 5: Ver los mutantes ROJOS de las tres cosas que la rev. 1 dejaba pasar**

```python
# scratch/mutantes_mapa.py — NO se commitea
import subprocess
import sys

F = "core/procedimiento/mapa.py"
MUTANTES = {
    "orden_sin_gramatica": (
        "        if not _RE_ORDEN.match(orden):",
        "        if False:  # MUTANTE: la rev. 1",
        "tests/test_procedimiento_mapa.py::test_un_orden_sin_gramatica_se_RECHAZA"),
    "bool_coercionado": (
        "        if not isinstance(sco, bool):",
        "        if False:  # MUTANTE: la rev. 1",
        "tests/test_procedimiento_mapa.py::test_un_string_false_NO_autoriza_el_override"),
    "reservado_por_stem": (
        '    if nombre.split(".")[0].lower() in _RESERVADOS_WINDOWS:',
        "    if Path(nombre).stem.lower() in _RESERVADOS_WINDOWS:  # MUTANTE: la rev. 1",
        "tests/test_procedimiento_mapa.py::test_rechaza_ficheros_invalidos_del_despacho"),
    "temporal_no_presupuestado": (
        "    tope = LIMITE_RUTA - MARGEN_TEMPORAL",
        "    tope = LIMITE_RUTA  # MUTANTE: la rev. 1",
        "tests/test_procedimiento_mapa.py::test_el_presupuesto_de_longitud_cuenta_el_TEMPORAL"),
}
original = open(F, encoding="utf-8").read()
for nombre, (viejo, nuevo, test) in MUTANTES.items():
    assert viejo in original, f"{nombre}: el ancla no existe"
    try:
        open(F, "w", encoding="utf-8").write(original.replace(viejo, nuevo, 1))
        r = subprocess.run([sys.executable, "-m", "pytest", test, "-q", "--no-header",
                            "-p", "no:randomly"], capture_output=True, text=True)
        print(f"  {nombre:<26} "
              + ("MUERTO (rojo, bien)" if r.returncode else "VIVO (TEST MAL APUNTADO)"))
    finally:
        open(F, "w", encoding="utf-8").write(original)
```

Run: `.venv\Scripts\python.exe scratch/mutantes_mapa.py`
Expected: los cuatro **MUERTO**.

- [ ] **Step 6: Run test to verify the module is intact**

Run: `.venv\Scripts\python.exe -m pytest tests/test_procedimiento_mapa.py -q --tb=short`
Expected: PASS (37)

- [ ] **Step 7: Commit**

```bash
git add core/procedimiento/mapa.py tests/test_procedimiento_mapa.py
git commit -m "vista procesal 4a: el mapa con gramatica, tipos estrictos y presupuesto del temporal (I3)"
```

---

## Task 5: qué fichero representa a cada documento, y con qué calidad

El invariante I5. Aquí no se copia nada: se **decide y se reporta** cuál sería el fichero
representativo y qué calidad declara la cobertura. 4b usará esta misma decisión para copiar, y
por eso vive aquí y no allí.

**Files:**
- Create: `core/procedimiento/artefacto.py`
- Test: `tests/test_procedimiento_artefacto.py`

**Interfaces:**
- Consumes: `core.sala_maquina.{DocCobertura, cobertura_desde_dicts}`, `sede.{contener, SedeError}`.
- Produces:
  - `artefacto.Clase` — `StrEnum`: `CRUDO`, `CONVERTIDO`, `SIN_REPRESENTANTE`.
  - `artefacto.Eleccion` — frozen: `clase: Clase`, `rel: str`, `ext: str`, `calidad: str`,
    `avisos: tuple[str, ...]`, `bloqueo: str`.
  - `artefacto.Cobertura` — frozen: `por_sha: dict[str, DocCobertura]`,
    `grupos: dict[str, GrupoBundle]`, `titulares: dict[str, str]`.
  - `artefacto.GrupoBundle` — frozen: `parent_sha256`, `parent_slug`, `peor_estado`,
    `n_segmentos`.
  - `artefacto.cargar(raiz: Path) -> Cobertura` — lanza si el JSON es ilegible.
  - `artefacto.elegir(raiz, cob: Cobertura, *, raw_rel, raw_sha256, sin_cobertura_ok) -> Eleccion`
  - `artefacto.ORDEN_ESTADO: tuple[str, ...]`

**Lo que la rev. 1 tenía mal, verificado contra `core/sala_maquina.py`:**

1. **`clase` y `estado` eran el mismo eje.** Su `PEOR_CALIDAD` mezclaba `error` (que es un
   `metodo`) con `empty`/`low`/`ok` (que son `estado`). El módulo ordena los estados
   `{empty:0, sin_soporte:1, low:2, ok:3}` (`_peor_estado`) y aquí se respeta ese orden.
2. **`duplicado` y `error` faltaban.** `METODO_DUPLICADO = "duplicado"` (`:1069`, `MEJORAS
   #147`) marca una copia byte-idéntica cuyo espejo es el del **titular**, y se resuelve por
   `alias_de`. `"error"` (`:1409`) es el método de un documento que reventó. La rev. 1 los
   mandaba a su rama de «desconocido → bloqueo».
3. **El bundle no era un grupo.** El OCR del bundle se escribe en `01_OCR/<parent_slug>.pdf`
   (`:1023`, con `d` = el **padre**) mientras las filas de segmento llevan `slug` del segmento
   y `parent_slug` del padre (`:975`). La rev. 1 conservaba la fila de peor calidad —una de
   segmento— y derivaba la ruta de **su** slug: apuntaba a un fichero inexistente y bloqueaba
   teniendo el PDF íntegro al lado.
4. **El SHA del crudo no se cruzaba con nada.** Bastaba que el fichero existiera.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_procedimiento_artefacto.py
"""I5: clase y estado son ejes distintos, el bundle es un grupo, y la cadena se verifica."""
import hashlib
import json

import pytest

from core.procedimiento import artefacto

SM = "01_Procesado/02_Sala de máquina"


def _arbol(tmp_path, filas, *, ocr=()):
    (tmp_path / SM).mkdir(parents=True, exist_ok=True)
    (tmp_path / SM / "_cobertura.json").write_text(json.dumps(filas), encoding="utf-8")
    if ocr:
        (tmp_path / SM / "01_OCR").mkdir(parents=True, exist_ok=True)
        for slug in ocr:
            (tmp_path / SM / "01_OCR" / f"{slug}.pdf").write_bytes(b"%PDF-1.4")
    return tmp_path


def _crudo(tmp_path, rel, cuerpo=b"%PDF-1.4 crudo"):
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(cuerpo)
    return hashlib.sha256(cuerpo).hexdigest()


def test_pdf_con_texto_lo_representa_el_crudo(tmp_path):
    sha = _crudo(tmp_path, "00_Input/05_CRM/01_Demanda/d.pdf")
    raiz = _arbol(tmp_path, [{"slug": "d", "rel_path": "05_CRM/01_Demanda/d.pdf",
                              "metodo": "pypdf", "estado": "ok", "sha256": sha}])
    e = artefacto.elegir(raiz, artefacto.cargar(raiz),
                         raw_rel="00_Input/05_CRM/01_Demanda/d.pdf", raw_sha256=sha,
                         sin_cobertura_ok=False)
    assert e.clase is artefacto.Clase.CRUDO
    assert e.ext == "pdf" and e.calidad == "ok" and e.bloqueo == ""


def test_un_BUNDLE_resuelve_al_artefacto_DEL_PADRE_con_la_peor_calidad(tmp_path):
    """El defecto más caro del selector de la rev. 1: el OCR está en
    `01_OCR/<parent_slug>.pdf` y las filas son de segmento. Derivar la ruta del slug del
    segmento apunta a un fichero que no existe."""
    sha = _crudo(tmp_path, "00_Input/05_CRM/99_Otros/bundle.pdf")
    raiz = _arbol(tmp_path, [
        {"slug": "bundle__a", "rel_path": "05_CRM/99_Otros/bundle.pdf", "metodo": "ocr",
         "estado": "ok", "sha256": "SEG_A", "parent_slug": "bundle", "parent_sha256": sha},
        {"slug": "bundle__b", "rel_path": "05_CRM/99_Otros/bundle.pdf", "metodo": "ocr",
         "estado": "low", "sha256": "SEG_B", "parent_slug": "bundle", "parent_sha256": sha},
    ], ocr=["bundle"])
    e = artefacto.elegir(raiz, artefacto.cargar(raiz),
                         raw_rel="00_Input/05_CRM/99_Otros/bundle.pdf", raw_sha256=sha,
                         sin_cobertura_ok=False)
    assert e.bloqueo == "", f"bloqueó teniendo el PDF del padre al lado: {e.bloqueo}"
    assert e.clase is artefacto.Clase.CONVERTIDO
    assert e.rel == f"{SM}/01_OCR/bundle.pdf"
    assert e.calidad == "low", "la calidad de un bundle es la PEOR de sus segmentos"
    assert any("2 segmento" in a for a in e.avisos)


def test_un_DUPLICADO_se_resuelve_por_su_titular(tmp_path):
    """`metodo: duplicado` (MEJORAS #147) dice «este fichero existe aquí y su espejo es el
    del titular». La rev. 1 lo mandaba a «desconocido → bloqueo»."""
    sha = _crudo(tmp_path, "00_Input/01_Drive EV/copia.pdf")
    raiz = _arbol(tmp_path, [
        {"slug": "titular", "rel_path": "05_CRM/01_Demanda/orig.pdf", "metodo": "ocr",
         "estado": "ok", "sha256": sha},
        {"slug": "copia", "rel_path": "01_Drive EV/copia.pdf", "metodo": "duplicado",
         "estado": "ok", "sha256": sha, "alias_de": "titular"},
    ], ocr=["titular"])
    e = artefacto.elegir(raiz, artefacto.cargar(raiz),
                         raw_rel="00_Input/01_Drive EV/copia.pdf", raw_sha256=sha,
                         sin_cobertura_ok=False)
    assert e.bloqueo == ""
    assert e.rel == f"{SM}/01_OCR/titular.pdf"
    assert any("titular" in a for a in e.avisos)


def test_un_metodo_ERROR_bloquea_diciendo_QUE_paso(tmp_path):
    """`metodo: error` es un documento que reventó al procesarse. Bloquea, pero no como
    «desconocido»: el remedio es distinto."""
    sha = _crudo(tmp_path, "00_Input/05_CRM/99_Otros/roto.pdf")
    raiz = _arbol(tmp_path, [{"slug": "roto", "rel_path": "05_CRM/99_Otros/roto.pdf",
                              "metodo": "error", "estado": "empty", "sha256": sha,
                              "nota": "fallo al procesar: PdfReadError"}])
    e = artefacto.elegir(raiz, artefacto.cargar(raiz),
                         raw_rel="00_Input/05_CRM/99_Otros/roto.pdf", raw_sha256=sha,
                         sin_cobertura_ok=False)
    assert e.bloqueo != ""
    assert "sala de máquina" in e.bloqueo
    assert "PdfReadError" in e.bloqueo, "el bloqueo debe llevar el motivo real"


def test_ofimatica_representa_el_PDF_convertido_y_CAMBIA_de_extension(tmp_path):
    sha = _crudo(tmp_path, "00_Input/05_CRM/01_Demanda/dem.doc", b"doc binario")
    raiz = _arbol(tmp_path, [{"slug": "dem", "rel_path": "05_CRM/01_Demanda/dem.doc",
                              "metodo": "ofimatica", "estado": "ok", "sha256": sha}],
                  ocr=["dem"])
    e = artefacto.elegir(raiz, artefacto.cargar(raiz),
                         raw_rel="00_Input/05_CRM/01_Demanda/dem.doc", raw_sha256=sha,
                         sin_cobertura_ok=False)
    assert e.clase is artefacto.Clase.CONVERTIDO and e.ext == "pdf"


def test_el_OCR_declarado_y_AUSENTE_bloquea_sin_degradar_al_crudo(tmp_path):
    sha = _crudo(tmp_path, "00_Input/05_CRM/99_Otros/esc.pdf")
    raiz = _arbol(tmp_path, [{"slug": "ausente", "rel_path": "05_CRM/99_Otros/esc.pdf",
                              "metodo": "ocr", "estado": "ok", "sha256": sha}])
    e = artefacto.elegir(raiz, artefacto.cargar(raiz),
                         raw_rel="00_Input/05_CRM/99_Otros/esc.pdf", raw_sha256=sha,
                         sin_cobertura_ok=False)
    assert e.bloqueo != "" and "01_OCR" in e.bloqueo
    assert e.clase is artefacto.Clase.SIN_REPRESENTANTE


def test_el_SHA_del_crudo_se_CRUZA_con_la_cobertura(tmp_path):
    """La rev. 1 solo miraba que el fichero existiera: con el crudo sustituido, copiaba
    bytes nuevos confiando en la clase y la calidad de los viejos."""
    _crudo(tmp_path, "00_Input/05_CRM/01_Demanda/d.pdf", b"AHORA OTRO CONTENIDO")
    raiz = _arbol(tmp_path, [{"slug": "d", "rel_path": "05_CRM/01_Demanda/d.pdf",
                              "metodo": "pypdf", "estado": "ok", "sha256": "SHA_VIEJO"}])
    e = artefacto.elegir(raiz, artefacto.cargar(raiz),
                         raw_rel="00_Input/05_CRM/01_Demanda/d.pdf",
                         raw_sha256=hashlib.sha256(b"AHORA OTRO CONTENIDO").hexdigest(),
                         sin_cobertura_ok=False)
    assert e.bloqueo != ""
    assert "cobertura" in e.bloqueo.lower()


def test_sin_cobertura_bloquea_y_el_override_deja_constancia(tmp_path):
    sha = _crudo(tmp_path, "00_Input/05_CRM/01_Demanda/d.pdf")
    raiz = _arbol(tmp_path, [])
    cob = artefacto.cargar(raiz)
    e = artefacto.elegir(raiz, cob, raw_rel="00_Input/05_CRM/01_Demanda/d.pdf",
                         raw_sha256=sha, sin_cobertura_ok=False)
    assert e.bloqueo != ""
    e2 = artefacto.elegir(raiz, cob, raw_rel="00_Input/05_CRM/01_Demanda/d.pdf",
                          raw_sha256=sha, sin_cobertura_ok=True)
    assert e2.bloqueo == "" and e2.clase is artefacto.Clase.CRUDO
    assert any("override" in a.lower() for a in e2.avisos)


def test_sin_soporte_lo_representa_el_crudo_con_aviso(tmp_path):
    sha = _crudo(tmp_path, "00_Input/05_CRM/99_Otros/v.mkv", b"video")
    raiz = _arbol(tmp_path, [{"slug": "v", "rel_path": "05_CRM/99_Otros/v.mkv",
                              "metodo": "sin_soporte", "estado": "sin_soporte",
                              "sha256": sha}])
    e = artefacto.elegir(raiz, artefacto.cargar(raiz),
                         raw_rel="00_Input/05_CRM/99_Otros/v.mkv", raw_sha256=sha,
                         sin_cobertura_ok=False)
    assert e.clase is artefacto.Clase.CRUDO and e.bloqueo == "" and e.avisos


def test_vision_deja_MD_pero_no_PDF_de_custodia(tmp_path):
    sha = _crudo(tmp_path, "00_Input/05_CRM/99_Otros/f.pdf")
    raiz = _arbol(tmp_path, [{"slug": "f", "rel_path": "05_CRM/99_Otros/f.pdf",
                              "metodo": "vision", "estado": "ok", "sha256": sha,
                              "ocr": False}])
    e = artefacto.elegir(raiz, artefacto.cargar(raiz),
                         raw_rel="00_Input/05_CRM/99_Otros/f.pdf", raw_sha256=sha,
                         sin_cobertura_ok=False)
    assert e.clase is artefacto.Clase.CRUDO
    assert any("visión" in a or "vision" in a for a in e.avisos)


def test_el_orden_de_los_estados_es_el_de_sala_de_maquina():
    """No se inventa un orden propio: `_peor_estado` del módulo usa este."""
    assert artefacto.ORDEN_ESTADO == ("empty", "sin_soporte", "low", "ok")


def test_una_cobertura_corrupta_LANZA_y_no_se_lee_como_vacia(tmp_path):
    (tmp_path / SM).mkdir(parents=True)
    (tmp_path / SM / "_cobertura.json").write_text("{{{", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        artefacto.cargar(tmp_path)


def test_una_cobertura_ausente_es_vacia_y_eso_NO_es_un_error(tmp_path):
    assert artefacto.cargar(tmp_path).por_sha == {}


def test_el_grupo_de_bundle_NO_depende_del_orden_de_las_filas(tmp_path):
    """La rev. 1 conservaba «la primera en caso de empate», así que invertir dos filas
    cambiaba la decisión."""
    sha = _crudo(tmp_path, "00_Input/05_CRM/99_Otros/b.pdf")
    filas = [
        {"slug": "b__1", "rel_path": "05_CRM/99_Otros/b.pdf", "metodo": "ocr",
         "estado": "low", "sha256": "S1", "parent_slug": "b", "parent_sha256": sha},
        {"slug": "b__2", "rel_path": "05_CRM/99_Otros/b.pdf", "metodo": "ocr",
         "estado": "ok", "sha256": "S2", "parent_slug": "b", "parent_sha256": sha},
    ]
    a = artefacto.cargar(_arbol(tmp_path, filas, ocr=["b"])).grupos[sha]
    b = artefacto.cargar(_arbol(tmp_path, list(reversed(filas)), ocr=["b"])).grupos[sha]
    assert a == b
    assert a.peor_estado == "low"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_procedimiento_artefacto.py -q --tb=short`
Expected: FAIL con `ImportError: cannot import name 'artefacto'`

- [ ] **Step 3: Write the implementation**

```python
# core/procedimiento/artefacto.py
"""Qué fichero REPRESENTA a cada documento, y con qué calidad (invariante I5).

Esta mitad no copia: decide y reporta. 4b usará la misma decisión para copiar, y por eso
la decisión vive aquí — que la tome quien no puede escribir es justo lo que permite
revisarla sin riesgo.

Tres cosas que la rev. 1 tenía mal, y que se comprobaron contra `core/sala_maquina.py`:

* **`clase` y `estado` son ejes distintos.** `metodo` dice de dónde sale el texto;
  `estado` dice qué calidad tiene. La rev. 1 mezclaba `error` (un método) con
  `empty`/`low`/`ok` (estados) en una sola escala.
* **`duplicado` y `error` existen** (`:1069`, `:1409`). El primero se resuelve por
  `alias_de` al espejo de su titular; el segundo bloquea con su motivo.
* **El bundle es un GRUPO.** Su OCR está en `01_OCR/<parent_slug>.pdf` (`:1023`) y sus
  filas de cobertura son de segmento (`:975`). Se agrupa por `parent_sha256` y se resuelve
  al artefacto del padre con la peor calidad de los segmentos.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from core.sala_maquina import DocCobertura, cobertura_desde_dicts

SM_REL = "01_Procesado/02_Sala de máquina"
OCR_REL = f"{SM_REL}/01_OCR"
COBERTURA_REL = f"{SM_REL}/_cobertura.json"

#: De PEOR a mejor. Es el orden de `sala_maquina._peor_estado`
#: (`{empty:0, sin_soporte:1, low:2, ok:3}`), no uno propio.
ORDEN_ESTADO: tuple[str, ...] = ("empty", "sin_soporte", "low", "ok")

#: Métodos que producen un PDF de custodia en `01_OCR/<slug>.pdf`.
METODOS_CON_ARTEFACTO = frozenset({"ocr", "ofimatica"})
#: Métodos cuyo original es su propio representante.
METODOS_CRUDO = frozenset({"pypdf", "nativo", "sin_soporte", "vision"})
#: Copia byte-idéntica: su espejo es el del titular (`MEJORAS #147`).
METODO_DUPLICADO = "duplicado"
#: El documento reventó al procesarse.
METODO_ERROR = "error"


class Clase(StrEnum):
    CRUDO = "crudo"
    CONVERTIDO = "convertido"
    SIN_REPRESENTANTE = "sin_representante"


@dataclass(frozen=True)
class Eleccion:
    clase: Clase = Clase.SIN_REPRESENTANTE
    rel: str = ""
    ext: str = ""
    calidad: str = ""
    avisos: tuple[str, ...] = ()
    bloqueo: str = ""


@dataclass(frozen=True)
class GrupoBundle:
    parent_sha256: str
    parent_slug: str
    peor_estado: str
    n_segmentos: int


@dataclass(frozen=True)
class Cobertura:
    por_sha: dict[str, DocCobertura] = field(default_factory=dict)
    grupos: dict[str, GrupoBundle] = field(default_factory=dict)
    #: `slug del alias -> slug del titular`
    titulares: dict[str, str] = field(default_factory=dict)
    por_slug: dict[str, DocCobertura] = field(default_factory=dict)


def _rango(estado: str) -> int:
    try:
        return ORDEN_ESTADO.index(estado)
    except ValueError:
        return -1               # desconocido: peor que el peor, y se dice


def cargar(raiz: Path) -> Cobertura:
    """Índices de `_cobertura.json`. Ausente = vacía; **corrupta LANZA**.

    «Cero documentos» y «no pude leerlo» no son lo mismo: confundirlos haría que la vista
    se construyera entera desde crudo creyendo que no hay sala de máquina.
    """
    p = Path(raiz) / COBERTURA_REL
    if not p.is_file():
        return Cobertura()
    filas = cobertura_desde_dicts(json.loads(p.read_text(encoding="utf-8")))

    por_sha: dict[str, DocCobertura] = {}
    por_slug: dict[str, DocCobertura] = {}
    titulares: dict[str, str] = {}
    segmentos: dict[str, list[DocCobertura]] = {}

    for f in filas:
        if f.slug:
            por_slug[f.slug] = f
        if f.parent_sha256:
            segmentos.setdefault(f.parent_sha256, []).append(f)
            continue
        if f.metodo == METODO_DUPLICADO and getattr(f, "alias_de", ""):
            titulares[f.slug] = f.alias_de
        if f.sha256:
            por_sha[f.sha256] = f

    grupos = {}
    for sha, segs in segmentos.items():
        peor = min((s.estado for s in segs), key=_rango)
        padres = {s.parent_slug for s in segs if s.parent_slug}
        grupos[sha] = GrupoBundle(
            parent_sha256=sha,
            parent_slug=sorted(padres)[0] if padres else "",
            peor_estado=peor,
            n_segmentos=len(segs))
    return Cobertura(por_sha=por_sha, grupos=grupos, titulares=titulares,
                     por_slug=por_slug)


def _artefacto_de(raiz: Path, slug: str) -> tuple[str, bool]:
    rel = f"{OCR_REL}/{slug}.pdf"
    return rel, (Path(raiz) / rel).is_file()


def elegir(raiz: Path, cob: Cobertura, *, raw_rel: str, raw_sha256: str,
           sin_cobertura_ok: bool) -> Eleccion:
    """Qué fichero representa a este documento, o por qué no hay ninguno.

    `raw_sha256` es el hash **actual** del crudo, que el llamador ya calculó. Se cruza con
    la cobertura: si no coincide, la clase y la calidad que la cobertura declara son de
    otros bytes.
    """
    ext = raw_rel.replace("\\", "/").rsplit("/", 1)[-1]
    ext = ext.rsplit(".", 1)[-1].lower() if "." in ext else ""
    avisos: list[str] = []

    # (1) ¿es un bundle? El grupo manda sobre la fila individual.
    grupo = cob.grupos.get(raw_sha256)
    if grupo is not None:
        if not grupo.parent_slug:
            return Eleccion(bloqueo=(
                f"{raw_rel}: la cobertura tiene {grupo.n_segmentos} segmentos sin "
                f"`parent_slug`, así que no se puede localizar el artefacto del padre"))
        rel, existe = _artefacto_de(raiz, grupo.parent_slug)
        if not existe:
            return Eleccion(bloqueo=(
                f"{raw_rel}: es un bundle de {grupo.n_segmentos} segmentos y su artefacto "
                f"{rel} no está. Vuelve a correr la sala de máquina"))
        avisos.append(f"bundle de {grupo.n_segmentos} segmentos: la calidad es la peor de "
                      f"ellos ({grupo.peor_estado})")
        return Eleccion(clase=Clase.CONVERTIDO, rel=rel, ext="pdf",
                        calidad=grupo.peor_estado, avisos=tuple(avisos))

    fila = cob.por_sha.get(raw_sha256)
    if fila is None:
        if not cob.por_sha and not cob.grupos:
            motivo = ("la sala de máquina no ha corrido sobre este caso")
        else:
            motivo = ("el sha256 actual del crudo no aparece en la cobertura, así que la "
                      "clase y la calidad que se declararían son de otros bytes")
        if not sin_cobertura_ok:
            return Eleccion(bloqueo=(
                f"{raw_rel}: {motivo}. Corre la sala de máquina, o declara "
                f"`sin_cobertura_ok: true` en su entrada del mapa"))
        return Eleccion(clase=Clase.CRUDO, rel=raw_rel, ext=ext, calidad="",
                        avisos=(f"override `sin_cobertura_ok`: {motivo}",))

    metodo = (fila.metodo or "").strip()

    # (2) duplicado: el representante es el del TITULAR
    if metodo == METODO_DUPLICADO:
        titular = cob.titulares.get(fila.slug) or getattr(fila, "alias_de", "")
        if not titular:
            return Eleccion(bloqueo=(
                f"{raw_rel}: `metodo: duplicado` sin `alias_de`, así que no se sabe de "
                f"qué fichero es copia"))
        ft = cob.por_slug.get(titular)
        rel, existe = _artefacto_de(raiz, titular)
        avisos.append(f"copia byte-idéntica: su representante es el del titular "
                      f"{titular!r}")
        if existe:
            return Eleccion(clase=Clase.CONVERTIDO, rel=rel, ext="pdf",
                            calidad=(ft.estado if ft else fila.estado),
                            avisos=tuple(avisos))
        return Eleccion(clase=Clase.CRUDO, rel=raw_rel, ext=ext,
                        calidad=(ft.estado if ft else fila.estado),
                        avisos=tuple(avisos))

    # (3) error: bloquea, pero diciendo QUÉ pasó
    if metodo == METODO_ERROR:
        return Eleccion(bloqueo=(
            f"{raw_rel}: la sala de máquina no pudo procesarlo — "
            f"{fila.nota or 'sin nota'}. No hay representante hasta arreglarlo"))

    # (4) imagen sin texto: es una foto de algo, no de una página
    if fila.estado == "empty" and ext not in {"pdf", ""}:
        return Eleccion(clase=Clase.CRUDO, rel=raw_rel, ext=ext, calidad=fila.estado,
                        avisos=("imagen sin texto: el original es su mejor representante",))

    if metodo in METODOS_CON_ARTEFACTO:
        if not fila.slug:
            return Eleccion(bloqueo=(
                f"{raw_rel}: `metodo: {metodo}` sin `slug`, no se puede derivar la ruta "
                f"del artefacto"))
        rel, existe = _artefacto_de(raiz, fila.slug)
        if not existe:
            return Eleccion(bloqueo=(
                f"{raw_rel}: `metodo: {metodo}` declara un artefacto y {rel} no existe. "
                f"No se degrada al crudo en silencio"))
        if fila.estado in ("low", "empty"):
            avisos.append(f"calidad declarada `{fila.estado}`: puede faltar texto")
        return Eleccion(clase=Clase.CONVERTIDO, rel=rel, ext="pdf",
                        calidad=fila.estado, avisos=tuple(avisos))

    if metodo in METODOS_CRUDO:
        if metodo == "sin_soporte":
            avisos.append("`sin_soporte`: ni MD ni OCR; lo abre el letrado, ningún LLM lo "
                          "lee")
        if metodo == "vision":
            avisos.append("extraído por visión: hay MD pero no PDF buscable de custodia")
        if fila.estado in ("low", "empty") and metodo != "sin_soporte":
            avisos.append(f"calidad declarada `{fila.estado}`")
        if _rango(fila.estado) < 0:
            avisos.append(f"estado `{fila.estado}` desconocido: no se le da el beneficio "
                          f"de la duda")
        return Eleccion(clase=Clase.CRUDO, rel=raw_rel, ext=ext, calidad=fila.estado,
                        avisos=tuple(avisos))

    return Eleccion(bloqueo=(
        f"{raw_rel}: `metodo: {metodo!r}` no está cubierto por el selector. No se adivina: "
        f"si es un método nuevo de la sala de máquina, hay que decidir qué representa"))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_procedimiento_artefacto.py -q --tb=short`
Expected: PASS (14 tests)

- [ ] **Step 5: Ver los mutantes ROJOS de los cuatro defectos de la rev. 1**

```python
# scratch/mutantes_artefacto.py — NO se commitea
import subprocess
import sys

F = "core/procedimiento/artefacto.py"
MUTANTES = {
    "bundle_por_fila": (
        "    grupo = cob.grupos.get(raw_sha256)",
        "    grupo = None  # MUTANTE: la rev. 1 trataba el bundle como una fila",
        "tests/test_procedimiento_artefacto.py::test_un_BUNDLE_resuelve_al_artefacto_DEL_PADRE_con_la_peor_calidad"),
    "sin_duplicado": (
        "    if metodo == METODO_DUPLICADO:",
        "    if False:  # MUTANTE: la rev. 1 no cubría `duplicado`",
        "tests/test_procedimiento_artefacto.py::test_un_DUPLICADO_se_resuelve_por_su_titular"),
    "sin_error": (
        "    if metodo == METODO_ERROR:",
        "    if False:  # MUTANTE: la rev. 1 no cubría `error`",
        "tests/test_procedimiento_artefacto.py::test_un_metodo_ERROR_bloquea_diciendo_QUE_paso"),
    "sha_no_cruzado": (
        "    fila = cob.por_sha.get(raw_sha256)",
        "    fila = next(iter(cob.por_sha.values()), None)  # MUTANTE: la rev. 1",
        "tests/test_procedimiento_artefacto.py::test_el_SHA_del_crudo_se_CRUZA_con_la_cobertura"),
}
original = open(F, encoding="utf-8").read()
for nombre, (viejo, nuevo, test) in MUTANTES.items():
    assert viejo in original, f"{nombre}: el ancla no existe"
    try:
        open(F, "w", encoding="utf-8").write(original.replace(viejo, nuevo, 1))
        r = subprocess.run([sys.executable, "-m", "pytest", test, "-q", "--no-header",
                            "-p", "no:randomly"], capture_output=True, text=True)
        print(f"  {nombre:<16} "
              + ("MUERTO (rojo, bien)" if r.returncode else "VIVO (TEST MAL APUNTADO)"))
    finally:
        open(F, "w", encoding="utf-8").write(original)
```

Run: `.venv\Scripts\python.exe scratch/mutantes_artefacto.py`
Expected: los cuatro **MUERTO**.

- [ ] **Step 6: Run test to verify the module is intact**

Run: `.venv\Scripts\python.exe -m pytest tests/test_procedimiento_artefacto.py -q --tb=short`
Expected: PASS (14)

- [ ] **Step 7: Commit**

```bash
git add core/procedimiento/artefacto.py tests/test_procedimiento_artefacto.py
git commit -m "vista procesal 4a: el representante de cada documento — clase vs estado, bundle como grupo (I5)"
```

---

## Task 6: el informe, el borrador del mapa, y el CLI sin ruta de escritura

Aquí se junta todo y aparece lo que el letrado ve. Dos entregables: el **informe** (qué hay, qué
falta, qué bloquea) y el **borrador de mapa** (`orden` y `descripción` propuestos, la carpeta
**nunca**), los dos a `stdout`.

**Files:**
- Create: `core/procedimiento/informe.py`
- Create: `core/procedimiento/borrador.py`
- Modify: `core/procedimiento/__init__.py` (la fachada)
- Create: `scripts/procedimiento.py`
- Test: `tests/test_procedimiento_informe.py`

**Interfaces:**
- Consumes: todo lo anterior, `core.casos.workspace_resolver.CaseWorkspaceResolver`,
  `core.casos.case_catalog.CaseCatalog`, `core.casos.case_locator.resolve_ref`.
- Produces:
  - `informe.Fila` — frozen, **en este orden** (se construye por posición):
    `logical_key`, `carpeta`, `destino`, `origen`, `doc_id`, `clase`, `rel_origen`,
    `calidad`, `avisos`.
  - `informe.Informe` — frozen: `case_id`, `expediente_id`, `filas`, `sin_asignar`,
    `solo_listadas`, `incoherencias`, `bloqueos`. Propiedades `por_carpeta`, `completo`.
  - `informe.construir(raiz, case_id, expediente_id, *, m, c, cob, incoherencias=()) -> Informe`
  - `borrador.proponer(c: Conjuntos) -> str` — YAML con `sin_asignar` poblado y `carpetas`
    **vacías**, listo para que el letrado reparta.
  - `core.procedimiento.informe(case_id, expediente_id, *, case_dir=None) -> Informe`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_procedimiento_informe.py
"""El informe: lo que el letrado ve. Y la garantía de que 4a no escribe."""
import hashlib
import json

import pytest

from core.casos.workspace_model import Capability
from core.procedimiento import artefacto, borrador, informe, mapa, universo

CARP = "05_Otros escritos"
SM = "01_Procesado/02_Sala de máquina"


class _Ws:
    def __init__(self, root):
        self.working_root = root
        self.capabilities = frozenset({Capability.READ_CASE})

    def exigir(self, cap):
        if cap not in self.capabilities:
            from core.casos.workspace_model import CapabilityDenied
            raise CapabilityDenied(str(cap))


@pytest.fixture()
def caso(tmp_path):
    cuerpo = b"%PDF-1.4 decreto"
    sha = hashlib.sha256(cuerpo).hexdigest()
    (tmp_path / "00_Input/05_CRM/99_Otros").mkdir(parents=True)
    (tmp_path / "00_Input/05_CRM/99_Otros/decreto.pdf").write_bytes(cuerpo)
    (tmp_path / SM).mkdir(parents=True)
    (tmp_path / SM / "_cobertura.json").write_text(json.dumps(
        [{"slug": "decreto", "rel_path": "05_CRM/99_Otros/decreto.pdf",
          "metodo": "pypdf", "estado": "ok", "sha256": sha}]), encoding="utf-8")
    (tmp_path / "05_Procedimiento").mkdir(parents=True)
    (tmp_path / "05_Procedimiento" / mapa.MAPA_FILENAME).write_text(
        "version: 1\nexpediente_crm: '540'\ncarpetas:\n"
        f'  "{CARP}":\n'
        "    - {origen: crm, doc_id: '1', orden: '00', descripcion: decreto_admision}\n",
        encoding="utf-8")
    return tmp_path, sha


def _conjuntos(sha, extra=None):
    from core.ocurrencias_crm import RegistroOcurrencias
    reg = RegistroOcurrencias.__new__(RegistroOcurrencias)
    reg.ocurrencias = {"crm:540:1": {
        "source": "crm", "expediente_id": "540", "doc_id": "1",
        "revisiones": [{"estado": "materializada", "filename": "decreto.pdf",
                        "modified_at": "2026-01-01T00:00:00+01:00", "id_carpeta": "306",
                        "path": "05_CRM/99_Otros/decreto.pdf", "sha256": sha}]}}
    if extra:
        reg.ocurrencias.update(extra)
    return universo.leer("CASO", "540", registro=reg,
                         pull_state={"documents_total_crm": len(reg.ocurrencias),
                                     "doc_ids": ["1"]})


def test_el_informe_dice_donde_va_cada_documento(caso):
    raiz, sha = caso
    inf = informe.construir(raiz, "CASO", "540", m=mapa.cargar(raiz),
                            c=_conjuntos(sha), cob=artefacto.cargar(raiz))
    assert inf.bloqueos == ()
    assert inf.completo is True
    (fila,) = inf.filas
    assert fila.carpeta == CARP
    assert fila.destino == "00_decreto_admision.pdf"
    assert fila.clase == artefacto.Clase.CRUDO
    assert fila.calidad == "ok"
    assert inf.por_carpeta[CARP][0] is fila


def test_construir_el_informe_NO_escribe_NADA(caso):
    """La garantía de esta mitad, comprobada por censo del árbol y no por promesa."""
    raiz, sha = caso

    def censo():
        return {str(p.relative_to(raiz)): (p.stat().st_mtime_ns, p.stat().st_size)
                for p in raiz.rglob("*") if p.is_file()}

    antes = censo()
    informe.construir(raiz, "CASO", "540", m=mapa.cargar(raiz), c=_conjuntos(sha),
                      cob=artefacto.cargar(raiz))
    assert censo() == antes, "el informe tocó el árbol del caso"


def test_lo_no_asignado_se_mide_contra_el_UNIVERSO_no_contra_lo_bajado(caso):
    """I4 aplicado al informe: un documento que el CRM enumera y el caso no bajó **sale
    en `solo_listadas`**, no desaparece. La rev. 1 calculaba `sin_asignar` sobre
    `materializadas` y los ocultaba."""
    raiz, sha = caso
    extra = {"crm:540:9": {
        "source": "crm", "expediente_id": "540", "doc_id": "9",
        "revisiones": [{"estado": "listada", "filename": "otro.pdf",
                        "modified_at": "2026-02-01T00:00:00+01:00", "id_carpeta": "306",
                        "path": None, "sha256": None}]}}
    inf = informe.construir(raiz, "CASO", "540", m=mapa.cargar(raiz),
                            c=_conjuntos(sha, extra), cob=artefacto.cargar(raiz))
    assert "9" in inf.solo_listadas
    assert any("9" in x for x in inf.sin_asignar)
    assert inf.completo is False, "un documento sin asignar no puede dar «completo»"


def test_un_documento_del_mapa_que_esta_solo_LISTADO_bloquea_con_su_remedio(caso):
    raiz, sha = caso
    (raiz / "05_Procedimiento" / mapa.MAPA_FILENAME).write_text(
        "version: 1\nexpediente_crm: '540'\ncarpetas:\n"
        f'  "{CARP}":\n'
        "    - {origen: crm, doc_id: '9', orden: '00', descripcion: otro}\n",
        encoding="utf-8")
    extra = {"crm:540:9": {
        "source": "crm", "expediente_id": "540", "doc_id": "9",
        "revisiones": [{"estado": "listada", "filename": "otro.pdf",
                        "modified_at": "x", "id_carpeta": "306",
                        "path": None, "sha256": None}]}}
    inf = informe.construir(raiz, "CASO", "540", m=mapa.cargar(raiz),
                            c=_conjuntos(sha, extra), cob=artefacto.cargar(raiz))
    txt = "\n".join(inf.bloqueos)
    assert "listada" in txt and "--full" in txt


def test_el_eco_saca_un_docid_de_lo_no_asignado(caso):
    raiz, sha = caso
    (raiz / "05_Procedimiento" / CARP).mkdir(parents=True)
    (raiz / "05_Procedimiento" / CARP / "DEMANDA.docx").write_bytes(b"propia")
    (raiz / "05_Procedimiento" / mapa.MAPA_FILENAME).write_text(
        "version: 1\nexpediente_crm: '540'\ncarpetas:\n"
        f'  "{CARP}":\n'
        "    - {origen: despacho, fichero: DEMANDA.docx, eco_crm: '1'}\n",
        encoding="utf-8")
    inf = informe.construir(raiz, "CASO", "540", m=mapa.cargar(raiz), c=_conjuntos(sha),
                            cob=artefacto.cargar(raiz))
    assert inf.sin_asignar == ()
    assert inf.bloqueos == ()


def test_un_eco_a_un_docid_INEXISTENTE_bloquea(caso):
    """La puerta 7-bis del spec, que la rev. 1 no tenía: un eco es una afirmación sobre
    el CRM y puede ser falsa."""
    raiz, sha = caso
    (raiz / "05_Procedimiento" / CARP).mkdir(parents=True)
    (raiz / "05_Procedimiento" / CARP / "DEMANDA.docx").write_bytes(b"propia")
    (raiz / "05_Procedimiento" / mapa.MAPA_FILENAME).write_text(
        "version: 1\nexpediente_crm: '540'\ncarpetas:\n"
        f'  "{CARP}":\n'
        "    - {origen: despacho, fichero: DEMANDA.docx, eco_crm: '404'}\n",
        encoding="utf-8")
    inf = informe.construir(raiz, "CASO", "540", m=mapa.cargar(raiz), c=_conjuntos(sha),
                            cob=artefacto.cargar(raiz))
    assert any("404" in b for b in inf.bloqueos)


def test_el_borrador_propone_orden_y_descripcion_y_NUNCA_la_carpeta(caso):
    """Spec §0: la asignación es del letrado. El borrador le ahorra la mecánica —los 76
    `orden` y `descripción`— y le deja la decisión."""
    raiz, sha = caso
    y = borrador.proponer(_conjuntos(sha))
    import yaml
    d = yaml.safe_load(y)
    assert d["version"] == 1 and d["expediente_crm"] == "540"
    assert d["carpetas"] == {}, "el borrador NO asigna carpetas"
    (prop,) = d["sin_asignar"]
    assert prop["doc_id"] == "1"
    assert prop["orden"] and prop["descripcion"]
    assert "decreto" in prop["descripcion"]


def test_el_borrador_es_YAML_valido_que_el_cargador_acepta_al_repartirlo(caso, tmp_path):
    """Un borrador que el propio cargador rechaza no sirve de nada. Se comprueba
    moviendo sus propuestas a una carpeta, que es lo que hará el letrado."""
    raiz, sha = caso
    import yaml
    d = yaml.safe_load(borrador.proponer(_conjuntos(sha)))
    d["carpetas"] = {CARP: [{"origen": "crm", "doc_id": p["doc_id"],
                             "orden": p["orden"], "descripcion": p["descripcion"]}
                            for p in d["sin_asignar"]]}
    d["sin_asignar"] = []
    destino = tmp_path / "otro"
    (destino / "05_Procedimiento").mkdir(parents=True)
    (destino / "05_Procedimiento" / mapa.MAPA_FILENAME).write_text(
        yaml.safe_dump(d, allow_unicode=True), encoding="utf-8")
    m = mapa.cargar(destino)
    assert len(m.entradas) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_procedimiento_informe.py -q --tb=short`
Expected: FAIL con `ImportError: cannot import name 'informe'`

- [ ] **Step 3: Write `informe.py`**

```python
# core/procedimiento/informe.py
"""El informe de la vista procesal: qué hay, qué falta, qué bloquea. No escribe nada.

Lo no asignado se mide contra el **universo** (`listadas`), no contra lo que se bajó: la
rev. 1 lo medía contra `materializadas` y por tanto ocultaba justo lo que el CRM tiene y el
caso no. Ver el invariante I4.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from . import artefacto as art
from . import mapa as mp
from .carpetas import CARPETAS_FASE
from .sede import SedeError, contener


@dataclass(frozen=True)
class Fila:
    logical_key: str
    carpeta: str
    destino: str
    origen: str
    doc_id: str | None
    clase: str
    rel_origen: str
    calidad: str
    avisos: tuple[str, ...] = ()


@dataclass(frozen=True)
class Informe:
    case_id: str
    expediente_id: str
    filas: tuple[Fila, ...] = ()
    sin_asignar: tuple[str, ...] = ()
    solo_listadas: tuple[str, ...] = ()
    incoherencias: tuple[str, ...] = ()
    bloqueos: tuple[str, ...] = ()

    @property
    def por_carpeta(self) -> dict[str, list[Fila]]:
        out: dict[str, list[Fila]] = {c: [] for c in CARPETAS_FASE}
        for f in self.filas:
            out.setdefault(f.carpeta, []).append(f)
        for v in out.values():
            v.sort(key=lambda f: f.destino)
        return out

    @property
    def completo(self) -> bool:
        """Todo lo que el CRM enumera está asignado y nada bloquea.

        **No** dice que la vista esté publicada: esta mitad no publica.
        """
        return not self.sin_asignar and not self.bloqueos


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def construir(raiz: Path, case_id: str, expediente_id: str, *, m: mp.MapaProcesal,
              c, cob: art.Cobertura,
              incoherencias: tuple[str, ...] = ()) -> Informe:
    """El informe. `incoherencias` las calcula el llamador con `universo.incoherencias(c)`.

    Se pasan como parametro y no se calculan aqui a proposito: `construir` recibe `c` ya
    leido —los tests lo inyectan— y hacerle llamar a `incoherencias` lo ataria al modulo
    que lo produce. `Conjuntos` NO tiene un atributo `incoherencias`.
    """
    raiz = Path(raiz)
    bloqueos: list[str] = []
    filas: list[Fila] = []

    if str(m.expediente_crm) != str(expediente_id):
        return Informe(case_id, expediente_id, bloqueos=(
            f"el mapa declara `expediente_crm: {m.expediente_crm!r}` y se pidió "
            f"{expediente_id!r}",))

    ecos: dict[str, str] = {}
    for e in m.entradas:
        if e.origen == mp.ORIGEN_DESPACHO and e.eco_crm:
            ecos[e.eco_crm] = e.logical_key

    # Puerta 7-bis del spec: un eco es una afirmación sobre el CRM y puede ser falsa.
    for doc_id, clave in sorted(ecos.items()):
        if doc_id not in c.listadas:
            bloqueos.append(
                f"{clave}: declara `eco_crm: {doc_id!r}` y el CRM no enumera ese "
                f"documento en el expediente {expediente_id}")

    asignados: set[str] = set()
    for e in m.entradas:
        if e.origen == mp.ORIGEN_DESPACHO:
            try:
                destino = contener(raiz, "05_Procedimiento", e.carpeta, e.fichero or "")
            except SedeError as exc:
                bloqueos.append(f"{e.logical_key}: {exc}")
                continue
            if not destino.is_file():
                bloqueos.append(
                    f"{e.logical_key}: `origen: despacho` declara {e.fichero!r} en "
                    f"{e.carpeta!r} y el fichero no está ahí")
                continue
            filas.append(Fila(e.logical_key, e.carpeta, e.fichero or "", e.origen, None,
                              "despacho", str(destino.relative_to(raiz)).replace("\\", "/"),
                              "", ()))
            continue

        asignados.add(e.doc_id or "")
        rev = c.materializadas.get(e.doc_id or "")
        if rev is None:
            if (e.doc_id or "") in c.solo_listadas:
                bloqueos.append(
                    f"{e.logical_key}: el CRM lo enumera pero no está en disco (ocurrencia "
                    f"`listada`, no `materializada`). Bájalo con "
                    f"`sync_sudespacho intake-judicial --full`")
            else:
                bloqueos.append(
                    f"{e.logical_key}: sin ocurrencia en el registro de este expediente")
            continue

        try:
            crudo = contener(raiz, "00_Input", str(rev["path"]))
        except SedeError as exc:
            bloqueos.append(f"{e.logical_key}: {exc}")
            continue
        if not crudo.is_file():
            bloqueos.append(f"{e.logical_key}: la ruta de origen no existe: "
                            f"00_Input/{rev['path']}")
            continue

        eleccion = art.elegir(raiz, cob,
                              raw_rel=f"00_Input/{rev['path']}",
                              raw_sha256=_sha(crudo),
                              sin_cobertura_ok=e.sin_cobertura_ok)
        if eleccion.bloqueo:
            bloqueos.append(f"{e.logical_key}: {eleccion.bloqueo}")
            continue
        nombre = mp.presupuesto_longitud(
            raiz, e.carpeta, mp.nombre_destino(e, eleccion.ext))
        filas.append(Fila(e.logical_key, e.carpeta, nombre, e.origen, e.doc_id,
                          str(eleccion.clase), eleccion.rel, eleccion.calidad,
                          eleccion.avisos))

    # Lo no asignado se mide contra el UNIVERSO (I4).
    sin_asignar = tuple(
        f"{d} ({(r.get('filename') or '?')}, lote {r.get('modified_at') or '?'}"
        f"{', no descargado' if d in c.solo_listadas else ''})"
        for d, r in sorted(c.listadas.items())
        if d not in asignados and d not in ecos)

    return Informe(case_id, str(expediente_id), tuple(filas), sin_asignar,
                   tuple(sorted(c.solo_listadas)), tuple(incoherencias),
                   tuple(bloqueos))
```

- [ ] **Step 4: Write `borrador.py`**

```python
# core/procedimiento/borrador.py
"""Propone `orden` y `descripción` para un mapa nuevo. **Nunca la carpeta.**

Spec §0: la asignación documento → fase es del letrado, y esa decisión no se automatiza.
Lo que sí se puede quitar de en medio es la mecánica: en un expediente de 76 documentos,
escribir a mano 76 pares `orden`/`descripción` es lo que hace que la pieza no se use. La
rev. 1 dejó esto fuera sin declararlo (spec §2.5).

Sale a `stdout`. Esta mitad no escribe en el expediente.
"""
from __future__ import annotations

import re
import unicodedata

import yaml

#: `D 02-A - Contrato.pdf` → `D-02A`. El número de documento que el CRM ya trae en el
#: nombre es la mejor propuesta de `orden` que existe: es la que usó el procurador.
_RE_NUM_DOC = re.compile(r"^\s*D\s*[-_ ]?\s*(\d{1,3})\s*[-_ ]?\s*([A-Z])?\b", re.I)


def _slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:50]


def _propuesta(doc_id: str, rev: dict, i: int) -> dict:
    nombre = str(rev.get("filename") or "")
    m = _RE_NUM_DOC.match(nombre)
    if m:
        orden = f"D-{int(m.group(1)):02d}{(m.group(2) or '').upper()}"
        resto = nombre[m.end():]
    else:
        orden = f"{i:02d}"
        resto = nombre
    resto = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", resto)
    return {
        "doc_id": str(doc_id),
        "orden": orden,
        "descripcion": _slug(resto) or f"documento_{i:02d}",
        "fichero": nombre,
        "lote": rev.get("modified_at") or "",
        "en_disco": bool(rev.get("path")),
    }


def proponer(c) -> str:
    """YAML de partida: `carpetas` VACÍAS y una propuesta por documento del universo."""
    propuestas = [_propuesta(d, r, i)
                  for i, (d, r) in enumerate(sorted(c.listadas.items(),
                                                    key=lambda kv: int(kv[0])
                                                    if kv[0].isdigit() else 0), 1)]
    cuerpo = {
        "version": 1,
        "expediente_crm": c.expediente_id,
        "carpetas": {},
        "sin_asignar": propuestas,
    }
    cabecera = (
        "# BORRADOR del mapa procesal — generado por `procedimiento borrador-mapa`.\n"
        "#\n"
        "# `carpetas` está VACÍO a propósito: la asignación documento -> fase es tuya.\n"
        "# Mueve cada entrada de `sin_asignar` a la carpeta que le toque, dejando\n"
        "# `origen: crm`, `doc_id`, `orden` y `descripcion`. `orden` y `descripcion` son\n"
        "# propuestas: cámbialas si no te cuadran.\n"
        "#\n"
        "# `en_disco: false` significa que el CRM lo enumera y este caso NO lo bajó. Si lo\n"
        "# necesitas en la vista, bájalo antes con `sync_sudespacho intake-judicial --full`.\n"
        "#\n"
        "# Mientras quede algo en `sin_asignar`, el informe no dirá «completo».\n")
    return cabecera + yaml.safe_dump(cuerpo, allow_unicode=True, sort_keys=False)
```

- [ ] **Step 5: Write the facade**

```python
# core/procedimiento/__init__.py
"""Vista procesal de `05_Procedimiento` — pieza 4a: la mitad que solo lee.

**No hay ruta de escritura en este paquete.** La única capacidad que se exige es
`READ_CASE`, y la autoridad la da el resolver del workspace, no el catálogo (invariante I0).
"""
from __future__ import annotations

from pathlib import Path

from . import artefacto, borrador, carpetas, informe as _informe, mapa, sede, universo

__all__ = ["informe", "borrador_mapa", "artefacto", "borrador", "carpetas", "mapa",
           "sede", "universo"]


def _resolver(case_id: str | None, case_dir: str | None):
    """Workspace autorizado para leer este caso. Lanza `WorkspaceError` o `SedeError`."""
    from core.casos.case_catalog import CaseCatalog
    from core.casos.case_locator import resolve_ref
    from core.casos.workspace_model import CaseRef
    from core.casos.workspace_registry import WorkspaceRegistry
    from core.casos.workspace_resolver import CaseWorkspaceResolver
    from core.utils import now_iso
    import getpass
    import socket

    ahora = now_iso()
    resolver = CaseWorkspaceResolver(
        CaseCatalog(), WorkspaceRegistry(), usuario=getpass.getuser(),
        maquina=socket.gethostname(), ahora=ahora)
    if case_dir:
        ws = resolver.resolver_por_ruta(Path(case_dir), drive_accesible=True)
        return (ws.case_ref.case_id or Path(case_dir).name), ws
    cid = resolve_ref(str(case_id))
    ws = resolver.resolver_por_identidad(CaseRef(case_id=cid), drive_accesible=True)
    return cid, ws


def informe(case_id: str | None = None, expediente_id: str = "", *,
            case_dir: str | None = None) -> _informe.Informe:
    """Qué hay en el procedimiento, qué falta y qué bloquea. **No escribe nada.**"""
    case_id, ws = _resolver(case_id, case_dir)
    raiz = sede.raiz_autorizada(ws)
    c = universo.leer(case_id, expediente_id)
    return _informe.construir(raiz, case_id, expediente_id,
                              m=mapa.cargar(raiz), c=c,
                              cob=artefacto.cargar(raiz),
                              incoherencias=universo.incoherencias(c))


def borrador_mapa(case_id: str | None = None, expediente_id: str = "", *,
                  case_dir: str | None = None) -> str:
    """YAML de partida para el mapa. **No escribe nada:** se devuelve como texto."""
    case_id, ws = _resolver(case_id, case_dir)
    sede.raiz_autorizada(ws)          # se exige READ_CASE aunque no se lea el árbol
    return borrador.proponer(universo.leer(case_id, expediente_id))
```

- [ ] **Step 6: Write the CLI**

```python
# scripts/procedimiento.py
"""CLI de la vista procesal de `05_Procedimiento` — pieza 4a (solo lectura).

    python -m scripts.procedimiento informe        --case "<case_id|W-code>" --expediente 540
    python -m scripts.procedimiento borrador-mapa  --case "<case_id|W-code>" --expediente 540

**Ninguno de los dos escribe en el expediente**, así que no se toma el mutex del caso: el
mutex lo pide quien escribe (`MEJORAS #126`), y aquí no escribe nadie. `borrador-mapa` emite
a `stdout`; redirígelo tú si quieres guardarlo.
"""
from __future__ import annotations

import typer

from core import procedimiento as proc
from core.casos.workspace_model import WorkspaceError
from core.procedimiento.mapa import MapaInvalidoError
from core.procedimiento.sede import SedeError
from core.procedimiento.universo import UniversoError

app = typer.Typer(add_completion=False, help=__doc__)

_CASE = typer.Option(None, "--case", help="case_id o W-code")
_DIR = typer.Option(None, "--case-dir", help="ruta explícita del caso")
_EXP = typer.Option(..., "--expediente", help="id del expediente en el CRM")


def _fatal(exc: Exception, code: int = 2):
    typer.echo(f"[ERROR] {exc}", err=True)
    raise typer.Exit(code=code)


@app.command()
def informe(case: str = _CASE, case_dir: str = _DIR, expediente: str = _EXP) -> None:
    """Qué hay en el procedimiento, qué falta y qué bloquea. No escribe nada."""
    try:
        inf = proc.informe(case, expediente, case_dir=case_dir)
    except (WorkspaceError, SedeError, UniversoError, MapaInvalidoError) as exc:
        _fatal(exc)

    typer.echo(f"expediente {inf.expediente_id} — {len(inf.filas)} documento(s) asignados")
    for carpeta, filas in inf.por_carpeta.items():
        if not filas:
            continue
        typer.echo(f"\n  {carpeta}")
        for f in filas:
            cal = f" [{f.calidad}]" if f.calidad else ""
            typer.echo(f"    {f.destino}{cal}   <- {f.rel_origen}")
            for a in f.avisos:
                typer.echo(f"        · {a}")
    for etiqueta, items in (("sin asignar", inf.sin_asignar),
                            ("enumerados y no descargados", inf.solo_listadas),
                            ("incoherencias", inf.incoherencias),
                            ("BLOQUEOS", inf.bloqueos)):
        if items:
            typer.echo(f"\n{etiqueta} ({len(items)}):")
            for x in items:
                typer.echo(f"  - {x}")
    typer.echo(f"\ncompleto: {'sí' if inf.completo else 'no'}")
    raise typer.Exit(code=0 if inf.completo else 1)


@app.command("borrador-mapa")
def borrador_mapa(case: str = _CASE, case_dir: str = _DIR,
                  expediente: str = _EXP) -> None:
    """Emite a stdout un mapa de partida, con `orden` y `descripción` propuestos."""
    try:
        typer.echo(proc.borrador_mapa(case, expediente, case_dir=case_dir), nl=False)
    except (WorkspaceError, SedeError, UniversoError) as exc:
        _fatal(exc)


if __name__ == "__main__":
    app()
```

- [ ] **Step 7: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_procedimiento_informe.py -q --tb=short`
Expected: PASS (8 tests)

- [ ] **Step 8: Guard — que NO exista ruta de escritura en el paquete**

Es la garantía que hace que esta mitad merezca una sola ronda. Se comprueba por AST, no por
promesa.

```python
# tests/test_procedimiento_sin_escritura.py
"""4a no escribe. Se comprueba por AST y no por confianza.

Si una tarea futura necesita escribir, este guard se pone rojo — y esa es la señal de que
lo que se está construyendo es 4b, con sus dos rondas de revisión.
"""
import ast
import pathlib

PAQUETE = pathlib.Path(__file__).resolve().parents[1] / "core" / "procedimiento"

#: Nombres cuya sola presencia significa «esto escribe».
PROHIBIDOS = {
    "write_text", "write_bytes", "mkdir", "touch", "unlink", "rmdir", "replace",
    "rename", "chmod", "copy", "copy2", "copyfile", "copytree", "move", "rmtree",
    "makedirs", "remove", "removedirs",
}
#: `open(...)` en modo de escritura.
MODOS_ESCRITURA = {"w", "a", "x", "wb", "ab", "xb", "w+", "r+", "a+"}


def test_ningun_modulo_de_4a_llama_a_algo_que_escriba():
    malos = []
    for f in sorted(PAQUETE.glob("*.py")):
        arbol = ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.Call):
                continue
            nombre = (nodo.func.attr if isinstance(nodo.func, ast.Attribute)
                      else getattr(nodo.func, "id", ""))
            if nombre in PROHIBIDOS:
                malos.append(f"{f.name}:{nodo.lineno} {nombre}()")
            if nombre == "open":
                for arg in list(nodo.args[1:2]) + [k.value for k in nodo.keywords
                                                   if k.arg == "mode"]:
                    if isinstance(arg, ast.Constant) and arg.value in MODOS_ESCRITURA:
                        malos.append(f"{f.name}:{nodo.lineno} open(mode={arg.value!r})")
    assert not malos, (
        "4a es la mitad que SOLO LEE y aquí hay llamadas que escriben: " + repr(malos))


def test_el_guard_CAZA_una_escritura_de_verdad(tmp_path):
    """Control positivo: sin esto, el test de arriba pasaría también con un AST vacío o
    con la lista de prohibidos mal escrita."""
    sonda = tmp_path / "sonda.py"
    sonda.write_text("import pathlib\n"
                     "pathlib.Path('x').write_text('y')\n", encoding="utf-8")
    arbol = ast.parse(sonda.read_text(encoding="utf-8"))
    encontrados = [n.func.attr for n in ast.walk(arbol)
                   if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                   and n.func.attr in PROHIBIDOS]
    assert encontrados == ["write_text"]


def test_4a_no_pide_capacidad_de_ESCRITURA_en_ningun_sitio():
    """La otra mitad de la garantía: aunque el código no escribiera, pedir `WRITE_CASE`
    sería pedir un permiso que no necesita."""
    malos = []
    for f in sorted(PAQUETE.glob("*.py")):
        txt = f.read_text(encoding="utf-8")
        for cap in ("WRITE_CASE", "MUTATE_CANONICAL", "GENERATE_DERIVATIVES", "INGEST"):
            if cap in txt:
                malos.append(f"{f.name}: {cap}")
    assert not malos, f"4a pide capacidades que no necesita: {malos}"
```

- [ ] **Step 9: Run the guard**

Run: `.venv\Scripts\python.exe -m pytest tests/test_procedimiento_sin_escritura.py -q --tb=short`
Expected: PASS (3 tests). Si el primero sale rojo, **no se relaja el guard**: se mueve la
llamada a 4b.

- [ ] **Step 10: CLI smoke test**

Run: `.venv\Scripts\python.exe -m scripts.procedimiento --help`
Expected: la ayuda con `informe` y `borrador-mapa`, exit 0

- [ ] **Step 11: Run the full suite with two seeds**

Run: `.venv\Scripts\python.exe -m scripts.session_close`
Expected: la verja corre la suite con las semillas 777 y 31337 y las dos salen verdes. Un
verde de una sola corrida no dice nada sobre el orden. El conteo debe subir en el número de
tests nuevos y **no** debe aparecer ningún `skip` ni `xfail` nuevo (salvo los dos `skipif`
de junction en no-Windows, que aquí es Windows y por tanto corren).

- [ ] **Step 12: Commit**

```bash
git add core/procedimiento/informe.py core/procedimiento/borrador.py \
        core/procedimiento/__init__.py scripts/procedimiento.py \
        tests/test_procedimiento_informe.py tests/test_procedimiento_sin_escritura.py
git commit -m "vista procesal 4a: el informe, el borrador del mapa, y el guard de que no escribe"
```

---

## Task 7: la regresión sobre el corpus real

**Files:**
- Create: `tests/fixtures/procedimiento/w02veke_ocurrencias.json`
- Create: `tests/fixtures/procedimiento/w02veke_cobertura.json`
- Create: `tests/test_procedimiento_regresion.py`

Se usa **W-02VEKE** y no el piloto W-02MA0R del spec §11.3 porque el piloto **no tiene sala de
máquina corrida** (spec §2.4: «en el piloto no se puede correr todavía») y por tanto no
ejercita el selector, que es media pieza. W-02VEKE tiene 76 documentos del CRM, sala de máquina
corrida el 2026-09-08 (340 documentos) y variedad real de `metodo`. **El reparto 9/5/15/12/29
del piloto sigue SIN VALIDAR** y se declara así: este fixture no lo sustituye.

- [ ] **Step 1: Generar los fixtures, sin un solo literal de dato personal**

Se ejecuta **a mano** y **no se commitea**. La ruta la resuelve el localizador desde el W-code y
los términos a redactar salen de `data/_config/pii_blocklist.txt`, que está **gitignored** y
existe exactamente para que los nombres reales no entren en un fichero versionado
(`scripts/precommit_leak_guard.py`, `MEJORAS #161`).

```python
# scratch/fixtures_w02veke.py — NO se commitea
import json
import pathlib
import re
import sys

sys.path.insert(0, ".")
from core.casos.case_locator import buscar, resolve_ref          # noqa: E402
from scripts.precommit_leak_guard import cargar_blocklist        # noqa: E402

W_CODE = "W-02VEKE"                       # identidad, no dato personal
CASO = buscar(resolve_ref(W_CODE))
if CASO is None:
    raise SystemExit(f"caso no encontrado: {W_CODE}")

TERMINOS = cargar_blocklist(pathlib.Path("."))
if not TERMINOS:
    raise SystemExit(
        "la blocklist salió VACÍA: sin ella la redacción no comprueba nada y el fixture "
        "NO se genera. Puebla `data/_config/pii_blocklist.txt` primero")
_RE = re.compile("|".join(re.escape(x) for x in TERMINOS), re.I)

DST = pathlib.Path("tests/fixtures/procedimiento")
DST.mkdir(parents=True, exist_ok=True)


def limpia(s):
    return _RE.sub("<PARTICULAR>", s) if isinstance(s, str) else s


oc = json.loads((CASO / "00_Input/_ocurrencias_crm.json").read_text(encoding="utf-8"))
for v in oc.get("ocurrencias", {}).values():
    for rev in v.get("revisiones", []):
        rev["filename"] = limpia(rev.get("filename"))
        rev["path"] = limpia(rev.get("path"))
(DST / "w02veke_ocurrencias.json").write_text(
    json.dumps(oc, ensure_ascii=False, indent=1), encoding="utf-8")

CAMPOS = {"slug", "rel_path", "metodo", "estado", "chars", "ocr", "sha256",
          "parent_slug", "parent_sha256", "role", "paginas", "tipo", "alias_de", "nota"}
cob = json.loads(
    (CASO / "01_Procesado/02_Sala de máquina/_cobertura.json").read_text(encoding="utf-8"))
cob = [{k: limpia(v) for k, v in f.items() if k in CAMPOS}
       for f in cob if str(f.get("rel_path", "")).startswith("05_CRM/")]
(DST / "w02veke_cobertura.json").write_text(
    json.dumps(cob, ensure_ascii=False, indent=1), encoding="utf-8")

print(f"ocurrencias: {len(oc['ocurrencias'])} · cobertura 05_CRM: {len(cob)} · "
      f"términos redactados: {len(TERMINOS)}")
```

Run: `.venv\Scripts\python.exe scratch/fixtures_w02veke.py`

- [ ] **Step 2: Verificar los fixtures contra la blocklist ENTERA**

Un grep de unas cuantas substrings elegidas a mano **no es prueba de anonimización**: es el
verde de un guard sin su blocklist. La comprobación corre contra los mismos términos que usó
la redacción y **falla si la lista está vacía**.

```bash
.venv/Scripts/python.exe -c "import pathlib,re,sys; sys.path.insert(0,'.'); from scripts.precommit_leak_guard import cargar_blocklist; T=cargar_blocklist(pathlib.Path('.')); t=''.join(p.read_text(encoding='utf-8') for p in pathlib.Path('tests/fixtures/procedimiento').glob('*.json')); m=sorted({x for x in T if re.search(re.escape(x),t,re.I)}); print(f'terminos={len(T)} supervivientes={len(m)}'); sys.exit(1 if (m or not T) else 0)"
```
Expected: `terminos=<N>` con N>0, `supervivientes=0`, exit 0

- [ ] **Step 3: Write the regression test**

```python
# tests/test_procedimiento_regresion.py
"""Regresión sobre el corpus real de W-02VEKE (fixtures anonimizados).

Los tres tests llevan **control positivo**: sin él, «el selector resolvió todo el corpus»
pasaría también con un corpus vacío o con todo bloqueado, que es el defecto que la R1
encontró en los tres tests de corpus de la rev. 1.
"""
import json
import pathlib

import pytest

from core.ocurrencias_crm import RegistroOcurrencias
from core.procedimiento import artefacto, universo
from core.sala_maquina import cobertura_desde_dicts

FIX = pathlib.Path(__file__).parent / "fixtures" / "procedimiento"
pytestmark = pytest.mark.skipif(
    not (FIX / "w02veke_cobertura.json").is_file(),
    reason="fixtures del corpus no generados: correr scratch/fixtures_w02veke.py")


@pytest.fixture()
def corpus():
    oc = json.loads((FIX / "w02veke_ocurrencias.json").read_text(encoding="utf-8"))
    cob = json.loads((FIX / "w02veke_cobertura.json").read_text(encoding="utf-8"))
    return oc, cob


def test_CONTROL_el_corpus_trae_lo_que_esta_pieza_debe_cubrir(corpus):
    """Sin este control, los dos tests de abajo pasarían sobre un corpus vacío."""
    oc, cob = corpus
    assert len(oc.get("ocurrencias", {})) >= 50, "el corpus no tiene volumen real"
    assert len(cob) >= 50
    metodos = {f["metodo"] for f in cob}
    assert {"pypdf", "ocr"} <= metodos, f"faltan métodos base: {sorted(metodos)}"
    assert len(metodos) >= 3, f"el corpus no tiene variedad: {sorted(metodos)}"


def test_el_selector_resuelve_TODO_el_corpus_sin_excepciones_y_con_mayoria_resuelta(
        tmp_path, corpus):
    """Bloquear es una respuesta válida; petar no. Y **la mayoría debe resolverse**: un
    selector que bloquea todo pasaría el primer aserto y sería inútil."""
    _, cob = corpus
    filas = cobertura_desde_dicts(cob)
    resueltos = bloqueados = 0
    for fila in filas:
        e = artefacto.elegir(tmp_path, artefacto.Cobertura(),
                             raw_rel=f"00_Input/{fila.rel_path}",
                             raw_sha256=fila.sha256 or "",
                             sin_cobertura_ok=True)
        assert e.bloqueo or e.clase, f"ni elección ni bloqueo para {fila.slug}"
        resueltos += bool(not e.bloqueo)
        bloqueados += bool(e.bloqueo)
    assert resueltos > bloqueados, (
        f"el selector bloqueó más de lo que resolvió ({bloqueados} vs {resueltos}): "
        f"pasaría el test sin servir para nada")


def test_el_universo_del_corpus_se_lee_y_separa_los_tres_conjuntos(corpus):
    oc, _ = corpus
    reg = RegistroOcurrencias.__new__(RegistroOcurrencias)
    reg.ocurrencias = oc["ocurrencias"]
    exp = next(iter(oc["ocurrencias"].values()))["expediente_id"]
    c = universo.leer("CASO", exp, registro=reg,
                      pull_state={"documents_total_crm": None, "doc_ids": []})
    assert len(c.listadas) >= 50
    assert len(c.materializadas) <= len(c.listadas)
    assert set(c.solo_listadas) == set(c.listadas) - set(c.materializadas)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_procedimiento_regresion.py -q --tb=short`
Expected: PASS (3 tests). Si los fixtures no están, 3 `skipped` con su motivo — y entonces la
regresión se declara **SIN VERIFICAR**, no cubierta.

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/procedimiento/ tests/test_procedimiento_regresion.py
git commit -m "vista procesal 4a: regresion sobre el corpus real de W-02VEKE, anonimizado por blocklist"
```

---

## Revisión adversarial

**Una ronda, sobre el diff.** Le corresponde una y no dos porque 4a **no decide quién escribe
sobre qué copia y no puede destruir datos de cliente** — y eso no es una promesa del plan: lo
sostiene el guard de la Tarea 6, que falla si aparece una llamada que escriba, y el hecho de
que el paquete no pida ninguna capacidad de escritura. El presupuesto de rondas lo fija el radio
de daño, y aquí el radio es cero.

Cuando se planifique **4b**, le corresponden **dos**: una sobre su diseño y una sobre su diff.

El encargo al revisor debe pedirle expresamente:

1. Que ataque el guard de «no escribe»: ¿hay alguna vía de escritura que el AST no vea
   (`getattr`, `eval`, un módulo de terceros, un `Path` pasado a algo que escribe)?
2. Que compruebe los **mutantes** de las tareas 1, 3, 4 y 5: ¿mata cada test lo que dice matar,
   y hay algún mutante **mejor** que el propuesto que sobreviva?
3. Que verifique la afirmación sobre los tres conjuntos del CRM contra `core/case_manager.py` y
   `core/sync_sudespacho.py` — es la corrección más importante de la rev. 1 y no me creo a mí
   mismo.
4. Que mida el **reparse tag** de un fichero real en `G:` si el Drive está montado: es el paso
   que quedó SIN MEDIR y decide si la pieza puede leer los casos reales.
5. Y el veredicto, en una palabra del set cerrado.

---

## 8. Adjudicación de la revisión adversarial (Codex, 2026-09-09) — NO-SHIP, parcial

- **Objeto revisado:** diff `e783464..9c4d5c1` (2.894 líneas, 26 ficheros), copias externas sin `.git`; parche `sha256 f4986a50…e080dd2`
- **Ronda:** 1 de 1 según el presupuesto declarado — **y el propio revisor invalida ese presupuesto** (su H-01)
- **Revisor:** Codex (`codex-cli 0.153.4`, `model_reasoning_effort=high`), en solo lectura sobre copia congelada
- **Informe recibido:** `docs/superpowers/plans/2026-09-09-vista-procesal-pieza4a-r1-adversarial-review.md` (`sha256 4d32d8b3…3dc003`)
- **Hallazgos:** 17 — 2 CRÍTICO, 10 ALTO, 5 MEDIO. **17 confirmados, 0 refutados.** Dos ya remediados en `16c646a`, anterior al informe y posterior al objeto
- **Remediado en:** los 17. `16c646a` (H-02), `a9630aa` (H-03, H-04, H-12), `0fb10df` (H-01, por decisión de alcance de Nikolai) y esta pasada (H-05 a H-11, H-13 a H-17)

**Acepto el NO-SHIP.** No se mergea 4a como está. Y acepto lo primero que dice el informe, que
es lo que más me importa: **el presupuesto de una sola ronda estaba mal fundado.**

### Lo que se cae, y es mío

**El presupuesto de rondas descansaba en una afirmación que yo mismo contradije en el mismo
plan** (H-01). La restricción global dice, literalmente, «Cero escrituras en el expediente.
Ninguna. Ni un fichero de estado, ni un log, ni un `mkdir`» — y la **Tarea 2 de este plan**
amplía `SUBDESTINOS_EXTRA` de una entrada a seis, con lo que `registrar_outputs` puede crear
`05_Procedimiento/<fase>/` y su `_index.md`. El revisor lo ejecutó: la versión `base` rechaza
ese destino y la `head` escribe el fichero. Las dos cosas no pueden ser verdad a la vez.

Lo correcto es lo que el informe propone y no lo que yo escribí: la afirmación exacta es
**«los nueve módulos nuevos no escriben en el expediente»**, y esa sí se sostiene — el revisor
la comprobó módulo a módulo y con un *audit hook* durante el import. Lo que no se sostiene es
la versión plana.

**Resuelto el 2026-09-09: Nikolai decidió sacar la ampliación del helper a su propia pieza**
(`2026-09-09-destinos-de-fase-registrar-outputs.md`), que es una de las dos salidas que el
informe dejaba abiertas. Con ella fuera, 4a **sí** tiene radio de daño cero en lo que a este
hallazgo respecta y su ronda única queda bien fundada. La restricción global se reescribió con
la redacción exacta, y 4a lleva ahora un test que fija el estado intermedio —el helper todavía
**no** tiene las carpetas— para que el hueco no se lea como un olvido: se pondrá rojo cuando la
pieza nueva entre, y ese rojo es la señal de retirarlo.

**Lo que esta decisión NO cierra:** H-05. La cadena que la fachada invoca puede escribir fuera
del expediente, porque `WorkspaceRegistry` renombra un registro corrupto al leerlo. Eso no es
«cero escrituras» y no se arregla moviendo una tupla.

**Y el guard que sostenía la afirmación tiene un agujero ejecutado** (H-04). Mi analizador
busca el modo de `open` en `nodo.args[1:2]`, y en `Path(x).open("w")` el modo va en `args[0]`.
El revisor añadió a la copia un `Path(...).open('w')` que **escribe al importar el paquete**, y
los 120 tests siguieron verdes. El hueco no estaba en mi inventario de huecos declarados, que
es lo que agrava el hallazgo: el test enumeraba tres excepciones y presentaba la lista como
completa. Un segundo escritor añadido al **CLI** también sobrevive, porque el glob del guard
solo mira `core/procedimiento/*.py` y `scripts/procedimiento.py` no cae ahí.

### El defecto funcional más caro, y por qué mis tests no podían verlo

**H-03: agrupé los bundles por la clave equivocada.** Usé `parent_sha256`, y ese campo es —lo
dice su propio comentario en `core/sala_maquina.py:196`— «sha del fichero **FÍSICO** de origen;
**clave del estado idempotente** por bundle». El marcador de segmento es `parent_slug`
(«slug del bundle **si es un segmento**; vacío si documento suelto`) o `doc_id` («vacío =
documento suelto»). Y `sala_maquina.py:937-938` rellena `parent_sha256` **también en el camino
passthrough**, con `parent_slug` vacío. Resultado: un documento suelto real se trata como
bundle sin padre y **se bloquea**.

Lo que me deja peor no es el error, es **por qué era invisible para mí**: en todos mis fixtures
puse `parent_slug` siempre que puse `parent_sha256`. Fabriqué un mundo en el que mi error no
existe, y luego probé ese mundo. El revisor no leyó el productor: lo **llamó**, aisló sus
dependencias y miró qué filas devuelve de verdad. Esa es la diferencia entre un fixture escrito
por el autor y una fila producida por el sistema, y es exactamente lo que la R1 anterior me
había dicho con otras palabras.

**Y lo repetí una segunda vez en el mismo diff** (H-16): mi test del corpus llama al selector
con `artefacto.Cobertura()` **vacía** y `sin_cobertura_ok=True`, así que solo recorre la rama de
override. La «mayoría resuelta» que el test exige sale del *fallback*, no del selector. El
revisor inutilizó los dos sets de métodos y el test siguió pasando. La R1 anterior había
señalado ese mismo defecto en los tests de corpus de la rev. 1, y yo escribí el test nuevo
—con su control positivo y su exigencia de mayoría— y aun así dejé el instrumento desconectado.

### Los quince que quedan, agrupados

**La sede no llega a todos los lectores.** H-06: `universo.leer` recibe el `case_id` y no la
raíz autorizada, así que `RegistroOcurrencias` y `read_pull_state` vuelven a `CASOS_ROOT` por
`case_locator`. Autorizo una raíz y leo otra: en un checkout con el mismo identificador, la
vista mezcla mapa y bytes locales con ocurrencias y D8 del canon. H-07: el mapa, la cobertura y
el artefacto derivado se abren por concatenación y no pasan por `contener`; y `contener` recibe
la raíz **ya resuelta**, que es donde mi propia corrección de la junction del ancestro deja de
aplicar en la secuencia de producción. H-05: `WorkspaceRegistry`, al leer un registro corrupto,
lo **renombra** — una escritura real fuera del expediente, en la cadena que mi fachada invoca.

**Puertas incompletas.** H-10: hasheo el crudo y lo busco en la cobertura, pero **nunca lo
comparo con el `sha256` de la ocurrencia**, así que un fichero sustituido por bytes de otro
documento con cobertura se acepta para el `doc_id` original. H-11: la comparación de destinos
cruza el tronco sin extensión (CRM) con el basename completo (despacho), así que dos entradas
pueden acabar en el mismo fichero y el informe dice «completo». H-12: `Informe.completo` ignora
las incoherencias, y el CLI sale con 0 — puede imprimir «D8 dice 99 documentos» y «completo:
sí» a la vez. H-15: valido que un `eco_crm` exista en el universo, pero no que ese `doc_id` no
esté ya asignado como entrada CRM, que es la otra mitad de la puerta 7-bis. H-17: publico
`materializadas` como «en disco» cuando es un **estado del registro** y no una comprobación de
I/O, y el borrador escribe `en_disco: true` solo porque la ruta no está vacía.

**Clasificación y validación.** H-09: el índice por SHA se queda la última fila, así que el
orden decide si un titular `error` bloquea o su alias degrada a crudo; y una cadena de alias, un
ciclo o un titular inexistente pasan a crudo sin bloqueo. H-08: «solo dos tags redirigen» no es
una clasificación, es una lista — y convierto cualquier `OSError` de `lstat` en «no redirige».
H-13: mi gramática usa `match` con `$`, que **acepta un salto de línea final**, y `COM¹.docx`
pasa el filtro de reservados; varios tipos se coercionan antes de validarse. H-14: presupuesto
puntos de código y no unidades UTF-16, y no presupuesto los nombres de despacho.

### Los dos que ya estaban arreglados, con su fecha

H-02 (el `TypeError` de `WorkspaceRegistry()`) y el `drive_accesible=True` a pelo salieron de
**mi propio *smoke test* del CLI** y están corregidos en `16c646a`, con
`tests/test_procedimiento_fachada.py`. El objeto revisado es `9c4d5c1`, anterior. **El revisor
los reporta con razón** y no los cuento como pendientes; su verificación con `CliRunner` es
mejor que la mía, y su observación de que `TypeError` tampoco estaba en `_ERRORES` del CLI es un
defecto adicional que yo no había visto y que entra en la remediación.

### Lo que no acredito

Las tres contrapruebas que sobreviven las **ejecutó él**; yo confirmé la causa leyendo mi
código, pero no reproduje sus corridas. H-07 a H-11, H-13 a H-15 y H-17 los acepté leyendo mi
código y siguiendo su escenario. Y **la afirmación «25 mutantes muertos» de este plan queda SIN
VERIFICAR para un tercero**: el arnés vive en `scratch/`, que está gitignored, así que no forma
parte del objeto — el revisor solo pudo reconstruir 13, y los 13 murieron. Eso es un defecto de
mi propia trazabilidad, no suyo: una afirmación cuantitativa cuyo instrumento no viaja con el
diff no es auditable.

### Cierre de los doce restantes (2026-09-09, misma sesión)

**Una corrección de esta propia adjudicación antes que nada: eran DOCE, no once.** 17 menos
los 5 remediados son 12, y yo escribí «los 11 restantes». Lo destapó contarlos al ir a
cerrarlos. Es la segunda vez en esta pieza que un reparto mío no cuadra —la primera fue dejar
H-06 sin frontera— y las dos veces lo encontró **contar**, no releer.

| | Qué se hizo |
|---|---|
| **H-05** | `sede.registro_legible` mira el registro de workspaces **antes** de que el resolver lo lea: `WorkspaceRegistry` renombra un JSON ilegible al leerlo, así que una lectura de 4a provocaba una escritura. Queda declarada la ventana entre el preflight y la lectura real (`MEJORAS #208`) |
| **H-06** | `universo.leer` **exige** la raíz autorizada y falla cerrado sin ella. El registro se construye redirigiendo su `path` —reutilizando su parser— y el `pull_state` reusa `read_md` y `_find_expediente_entry` cambiando solo la base. Un test con dos árboles del mismo `case_id` prueba que la raíz manda |
| **H-07** | La cadena se inspecciona en `raiz_autorizada`, **antes** de `resolve()`, que es donde la ruta entra por primera vez |
| **H-08** | La política pasa de una lista de dos tags al **bit Name Surrogate**, que es la propiedad. Y se cierran los tres fallos abiertos: un `OSError` que no sea «no existe» ya no es «no redirige», y agotar la cota de ancestros devuelve `False` |
| **H-09** | El alias se resuelve como **grafo** —ciclos, cadenas, titular ausente— y se hereda la **decisión** del titular, no solo su ruta. Con el mismo SHA el titular gana al alias, así que el orden del JSON deja de decidir |
| **H-10** | El SHA de la **ocurrencia** se cruza con los bytes actuales. Faltaba el primer eslabón de la cadena |
| **H-11** | La colisión de destinos **efectivos** se comprueba en la vista, que es donde se conocen las extensiones |
| **H-13** | `fullmatch` en vez de `match` —el `$` casaba antes del salto final—, `COM¹`/`LPT²`/`³`, y tipos estrictos para `doc_id`, `descripcion` y `expediente_crm` |
| **H-14** | El presupuesto cuenta **unidades UTF-16**, y el truncado no parte un par suplente |
| **H-15** | La otra mitad de la puerta 7-bis: un eco a un `doc_id` ya asignado como `crm` bloquea, y dos ecos al mismo `doc_id` también |
| **H-16** | El test del corpus recibe **su** cobertura y exige la **clase esperada por fila** |
| **H-17** | `materializadas` es un estado del registro y se dice; la presencia física se comprueba bajo la raíz, y «no la miré» se separa de «no cuadra» |

**187 tests de la pieza, 32 mutantes y todos muertos, suite verde con las dos semillas
(5028 tests, 0 fallos, 92 `skip`).**

**Cuatro cosas que salieron del arnés y no de escribir, que es la parte que vale:**

1. El mutante de H-16 **sobrevivió a mi primer arreglo**. Había corregido la *entrada* del
   test —darle la cobertura real— y dejado la aserción débil: «la mayoría se resuelve» pasa
   con 40 contra 15. La contraprueba exacta del revisor seguía viva hasta que exigí la **clase
   esperada por fila**. Arreglar la mitad de un defecto se parece mucho a arreglarlo.
2. El mutante de H-14 sobrevivía porque **mi test medía con la función que probaba**: al
   degradar `_unidades_utf16` a `len()`, la aserción se degradaba con ella. El instrumento del
   test tiene que ser independiente del que mide el código.
3. Añadí al mapa una validación del nombre del CRM que resultó **inerte**: el prefijo
   `<orden>_` hace estructuralmente imposible un reservado. Se conserva como defensa en
   profundidad, pero su test dice que prueba **la razón**, no una captura — una guarda inerte
   que se cree activa es peor que no tenerla.
4. Poner «no comprobé el disco» entre las incoherencias hacía falso el `completo` en cuanto
   alguien inyectaba los lectores. Eso no es un desacuerdo entre fuentes, es **cobertura
   ausente**, y va por otro canal. Me lo dijo el test antes que ningún revisor.

### Qué pasa ahora

**Los 17 están cerrados y 4a queda lista para PR.** El presupuesto de rondas se resolvió
sacando la ampliación del helper a su propia pieza (decisión de Nikolai, `0fb10df`), con lo que
el radio de daño de esta mitad vuelve a ser cero por construcción; el resto se remedió sobre
este mismo plan, porque el diseño no estaba mal — estaban mal la clave de agrupación, la
propagación de la raíz, cuatro puertas y el instrumento que las medía.

**Lo que sigue SIN VERIFICAR y no lo cierra esta pasada**, porque no depende de escribir
código: la regresión sobre el corpus real de W-02VEKE —el Drive no estaba montado, los fixtures
no se generaron y sus 4 tests se saltan con ese motivo—, el *reparse tag* real de un fichero en
`G:`, y el reparto del piloto W-02MA0R. Los tres estaban declarados desde el plan y siguen
declarados.

**Y una deuda nueva:** la ventana entre el preflight del registro y la lectura del resolver
(`MEJORAS #208`). El preflight cubre el caso práctico —un registro corrupto ya puesto— y no
cierra la carrera.
