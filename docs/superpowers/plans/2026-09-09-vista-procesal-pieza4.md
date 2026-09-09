---
estado: vigente
dueño: Nikolai Tyukhay
fecha: 2026-09-09
spec: docs/superpowers/specs/2026-07-27-vista-procesal-05-procedimiento-design.md
---

# Vista procesal de `05_Procedimiento` — pieza 4 · Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** construir la vista procesal de `05_Procedimiento` — cinco carpetas de fase, autocontenidas,
donde el letrado lee un procedimiento entero sin salir de su carpeta y la máquina tiene un ledger de
propiedad de lo que puede tocar.

**Architecture:** paquete `core/procedimiento/` con siete módulos de una responsabilidad cada uno
(mapa, artefacto, ledger, índice, diff, aplicar, fachada) más un CLI `plan`/`apply` en
`scripts/procedimiento.py`. Puro sobre el árbol del caso, **sin red**: lee el registro de ocurrencias
(`core/ocurrencias_crm.py`, ya construido), `_cobertura.json` de la sala de máquina y el YAML que
escribe el letrado; emite un diff; lo aplica transaccionalmente. `00_Input/05_CRM` **no se toca
nunca**.

**Tech Stack:** Python 3.14, `pyyaml`, `pytest`, `typer` (CLI, patrón de `scripts/sala_maquina.py`).
Sin dependencias nuevas.

---

## Global Constraints

Requisitos de proyecto que aplican a **todas** las tareas. Valores copiados literalmente del spec.

- **La vista se construye SOLO en `05_Procedimiento`. `00_Input/05_CRM` no se modifica** (spec §0).
- **Precedencia de fuentes: CRM > ocurrencias > manifiesto de intake.** `_intake_hashes.json` queda
  **fuera de la ruta de confianza**: no se lee (spec §0, §2.1).
- **Nada escribe fuera de las cinco carpetas de `05_Procedimiento`** (spec §5).
- **Un fichero `origen: despacho` nunca entra en una operación destructiva** (spec §5.14).
- **La herramienta no renombra lo que no ha creado.** Los escritos propios conservan su nombre
  (spec §0).
- **`plan` nunca propone la carpeta.** La asignación es del letrado (spec §0, §3).
- **Un diff vacío produce cero escrituras**, incluido el campo `generado` del ledger (spec §4.1).
- **La vista no promete buscabilidad.** Copia el mejor artefacto disponible y reporta lo que la
  cobertura declara, sabiendo que la declaración puede ser optimista (spec §0, §2.4).
- **Encoding UTF-8 sin BOM** en todo fichero escrito (`CLAUDE.md`).
- **Higiene PII:** en docs, commits y nombres de rama el caso se referencia solo por `W-XXXXXX`
  (`CLAUDE.md`). **Aplica a este plan tambien:** ni una ruta con nombre de tercero, ni un
  nombre de persona, ni una direccion — **ni siquiera dentro de un script que «no se va a
  commitear»**, porque el script vive en el plan y el plan se versiona. Lo sensible se
  resuelve en ejecucion, desde el localizador y desde la blocklist gitignored. **Y el verde
  del leak-guard no acredita lo contrario:** es una denylist de terminos enumerados, y los
  de este caso no estaban en ella (medido el 2026-09-09: 70 terminos, 0 coincidencias).
- **Tests: ningún test escribe en el árbol de producción.** Árbol sintético en `tmp_path` y pasado
  a la función (`CLAUDE.md`; patrón en `tests/test_guard_localizador.py::_arbol_sintetico`).

### Tres ajustes del spec a la realidad del código (declarados, no silenciosos)

El spec se escribió el 2026-07-27. Tres cosas han cambiado desde entonces y el plan se ajusta a lo
que el código hace **hoy**:

1. **El registro de ocurrencias tiene TRES estados, no dos.** El spec §2.1 dice `active` /
   `superseded`; `core/ocurrencias_crm.py` (PR #140) implementa `listada` / `materializada` /
   `superseded`. La distinción es sustantiva y **mejora** el diseño: `listada` es «el CRM lo
   enumera», `materializada` es «además está en disco». Consecuencias para este plan:
   - Donde el spec dice «ocurrencia `active`», se lee **`materializada`** para todo lo que se pueda
     copiar. `RegistroOcurrencias.resolver()` ya devuelve `None` para una `listada`, y su docstring
     lo dice: «la vista procesal no puede copiarla».
   - Aparece una **categoría de bloqueo que el spec no tenía nombrada**: un `doc_id` `solo_listadas`
     dentro del expediente. Es un documento que el CRM tiene y el caso no bajó (intake acotado).
     Bloquea, con remedio nombrado: `sync_sudespacho intake-judicial --full`.
2. **`DocCobertura.metodo` tiene dos valores más que el spec:** `ofimatica` (LibreOffice headless,
   `MEJORAS #61`, ya mergeado) y `vision`. El selector por clase documental los cubre. `ofimatica`
   **cierra el hueco del `.doc`** que el spec §2.4 declaraba abierto.
3. **Las cinco carpetas: el spec nombra tres literalmente y deduce dos.** Literales: `01_Monitorio -
   Demanda y documentos`, `03_Ordinario - Demanda y documentos`, `05_Otros escritos`. Los dos
   intermedios se fijan **en este plan**, derivados de la tabla de bloques de §11.1 («Oposición al
   monitorio + documentos», «Contestación + documentos») y **sin tilde**, por coherencia con
   `02_Analisis` y `99_Sin categoria` del propio repo: `02_Monitorio - Oposicion y documentos` y
   `04_Ordinario - Contestacion y documentos`. Si Nikolai prefiere otros rótulos, se cambia la
   constante de la Tarea 1 y nada más.

---

## File Structure

| Fichero | Responsabilidad |
|---|---|
| `core/procedimiento/__init__.py` | Fachada: `plan()`, `apply()` y los dataclass del resultado. Nada de lógica |
| `core/procedimiento/carpetas.py` | La lista blanca de las cinco carpetas de fase. Un solo sitio que las nombre |
| `core/procedimiento/mapa.py` | Carga y **validación** de `_mapa_procesal.yaml` (spec §3, §3.1, §3.2) |
| `core/procedimiento/artefacto.py` | Selector por clase documental: qué fichero se copia (spec §2.4) |
| `core/procedimiento/ledger.py` | `_MANIFIESTO_PROCESAL.json`: leer, escribir atómico, consultar |
| `core/procedimiento/diff.py` | Puerta de integridad + las nueve categorías del diff (spec §4.1) |
| `core/procedimiento/aplicar.py` | La transacción y las puertas de propiedad (spec §4.1, §5.10-5.14) |
| `core/procedimiento/indice.py` | Reconciliador de `<carpeta>/_index.md` (spec §2.3) |
| `scripts/procedimiento.py` | CLI `plan` / `apply`, patrón de `scripts/sala_maquina.py` |
| `.claude/skills/_shared/registrar_outputs.py` | **Modificar:** ampliar `SUBDESTINOS_EXTRA` |

Se elige paquete y no módulo único porque el repo ya usa paquetes en `core/` para piezas de este
tamaño (`core/anon/`, `core/casos/`, `core/email_atomize/`, `core/whatsapp_atomize/`) y porque la
validación del mapa, el selector de artefacto y la transacción son tres cuerpos de reglas que se
revisan por separado.

---

## Task 1: la lista blanca de carpetas, y las skills pueden escribir en ellas

Es la tarea más pequeña del plan y va primera a propósito: desbloquea a `escritos-judiciales` y a
`preparacion-audiencia-previa` sin depender de nada más (spec §7: «Entra: ampliar
`DESTINOS_VALIDOS`»).

**Files:**
- Create: `core/procedimiento/__init__.py` (vacío por ahora)
- Create: `core/procedimiento/carpetas.py`
- Modify: `.claude/skills/_shared/registrar_outputs.py:56-58`
- Test: `tests/test_procedimiento_carpetas.py`

**Interfaces:**
- Consumes: nada.
- Produces: `carpetas.CARPETAS_FASE: tuple[str, ...]` (las cinco, en orden),
  `carpetas.es_carpeta_fase(nombre: str) -> bool`,
  `carpetas.CARPETA_OTROS: str` (la quinta, el cajón).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_procedimiento_carpetas.py
"""Las cinco carpetas de fase son un set CERRADO y un solo sitio las nombra."""
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


@pytest.mark.parametrize("nombre", list(carpetas.CARPETAS_FASE))
def test_reconoce_las_cinco(nombre):
    assert carpetas.es_carpeta_fase(nombre) is True


@pytest.mark.parametrize("nombre", [
    "Jurisprudencia",                      # subcarpeta legitima, pero NO de fase
    "01_Monitorio",                        # prefijo, no el nombre completo
    "06_Otra cosa",
    "",
    "05_Otros escritos/sub",               # una ruta no es una carpeta de fase
    "05_OTROS ESCRITOS",                   # el set es sensible a la grafia exacta
])
def test_rechaza_lo_que_no_es_carpeta_de_fase(nombre):
    assert carpetas.es_carpeta_fase(nombre) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_procedimiento_carpetas.py -q --tb=short`
Expected: FAIL con `ModuleNotFoundError: No module named 'core.procedimiento'`

- [ ] **Step 3: Write minimal implementation**

```python
# core/procedimiento/__init__.py
"""Vista procesal de `05_Procedimiento` (spec 2026-07-27, pieza 4)."""
```

```python
# core/procedimiento/carpetas.py
"""Las cinco carpetas de fase de `05_Procedimiento`. Un solo sitio que las nombre.

Set CERRADO: el mapa del letrado se valida contra esta tupla y `registrar_outputs`
la consume para que un escrito generado se registre en su fase (spec §7).

Los rotulos de la 2.a y la 4.a los fija este modulo, derivados de la tabla de bloques
del spec §11.1 («Oposicion al monitorio + documentos», «Contestacion + documentos»).
Van SIN tilde por coherencia con `02_Analisis` y `99_Sin categoria` del repo.
"""
from __future__ import annotations

#: En orden de lectura del pleito. El prefijo numerico es parte del nombre.
CARPETAS_FASE: tuple[str, ...] = (
    "01_Monitorio - Demanda y documentos",
    "02_Monitorio - Oposicion y documentos",
    "03_Ordinario - Demanda y documentos",
    "04_Ordinario - Contestacion y documentos",
    "05_Otros escritos",
)

#: El cajon que recoge lo procesal que no es un escrito rector con sus documentos.
#: Es lo que hace que la puerta de `sin_asignar` sea cumplible (spec §11.1).
CARPETA_OTROS: str = "05_Otros escritos"

#: Las cuatro primeras llevan escrito rector: `plan` les propone `orden: "00"` cuando el
#: nombre del CRM no trae numero de documento. La quinta usa la fecha del lote (spec §3).
CARPETAS_CON_RECTOR: tuple[str, ...] = CARPETAS_FASE[:4]

_SET = frozenset(CARPETAS_FASE)


def es_carpeta_fase(nombre: str) -> bool:
    """`True` solo para una de las cinco, con su grafia exacta.

    No normaliza: un rotulo aproximado es un error del mapa que hay que ver, no
    algo que adivinar. La comparacion `casefold` del spec §3.1 es para detectar
    COLISIONES entre destinos, no para aceptar variantes de la carpeta.
    """
    return nombre in _SET
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_procedimiento_carpetas.py -q --tb=short`
Expected: PASS (10 tests)

- [ ] **Step 5: Ampliar `DESTINOS_VALIDOS` del helper de las skills**

En `.claude/skills/_shared/registrar_outputs.py`, sustituir el bloque de
`SUBDESTINOS_EXTRA` (líneas 56-58) por:

```python
# Subcarpeta dedicada a jurisprudencia descargada (decisión #2 del plan v3).
# Y las cinco carpetas de fase de la vista procesal (spec 2026-07-27 §7): un escrito
# generado se registra en la fase donde `escritos-judiciales` lo escribió. Se repiten
# aquí como literales, y NO se importan de `core.procedimiento.carpetas`, porque este
# helper viaja dentro del `.skill` empaquetado y ahí `core/` no existe: importarlo
# rompería la skill en el servidor. El test de no-drift de abajo es lo que mantiene
# las dos listas alineadas.
SUBDESTINOS_EXTRA: tuple[str, ...] = (
    "05_Procedimiento/Jurisprudencia",
    "05_Procedimiento/01_Monitorio - Demanda y documentos",
    "05_Procedimiento/02_Monitorio - Oposicion y documentos",
    "05_Procedimiento/03_Ordinario - Demanda y documentos",
    "05_Procedimiento/04_Ordinario - Contestacion y documentos",
    "05_Procedimiento/05_Otros escritos",
)
```

- [ ] **Step 6: Test de no-drift entre las dos listas**

Añadir a `tests/test_procedimiento_carpetas.py`:

```python
def test_registrar_outputs_admite_las_cinco_sin_drift():
    """Las dos listas viven en sitios distintos por una razón (el `.skill` no tiene
    `core/`), así que un test las ata: si alguien añade una carpeta de fase y no toca
    el helper, el escrito se registraría fuera de su fase."""
    import importlib.util
    import pathlib

    ruta = (pathlib.Path(__file__).resolve().parents[1]
            / ".claude" / "skills" / "_shared" / "registrar_outputs.py")
    spec = importlib.util.spec_from_file_location("registrar_outputs_shared", ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    esperadas = {f"05_Procedimiento/{c}" for c in carpetas.CARPETAS_FASE}
    assert esperadas <= set(mod.SUBDESTINOS_EXTRA), (
        "faltan carpetas de fase en SUBDESTINOS_EXTRA: "
        f"{sorted(esperadas - set(mod.SUBDESTINOS_EXTRA))}"
    )
    assert esperadas <= mod.DESTINOS_VALIDOS
```

- [ ] **Step 7: Run test to verify it passes**

Run: `python -m pytest tests/test_procedimiento_carpetas.py -q --tb=short`
Expected: PASS (11 tests)

- [ ] **Step 8: Sincronizar el helper a las siete skills**

`registrar_outputs.py` está replicado **byte a byte** en las carpetas `scripts/` de siete
skills, porque el `.skill` empaquetado tiene que ser autónomo: `sync_skill_helpers.py` copia
**todo** `_shared/*.py` a esas siete y `tests/test_skill_helpers_sync.py::test_helpers_sin_drift`
se pone **rojo** en cuanto la fuente y una copia difieren. Editar el Step 5 sin este paso deja
la suite en rojo y las skills registrando con la lista vieja.

Run: `python scripts/sync_skill_helpers.py`
Expected: imprime los ficheros escritos; entre ellos siete `registrar_outputs.py`

- [ ] **Step 9: Verificar que no queda drift**

Run: `python -m pytest tests/test_skill_helpers_sync.py -q --tb=short`
Expected: PASS (2 tests). Si sale rojo, **no** se toca el test: se vuelve a correr el sync.

- [ ] **Step 10: Commit**

Las siete copias entran en el MISMO commit que la fuente: separarlas deja un commit intermedio
con la suite en rojo.

```bash
git add core/procedimiento/__init__.py core/procedimiento/carpetas.py \
        tests/test_procedimiento_carpetas.py \
        .claude/skills/_shared/registrar_outputs.py \
        .claude/skills/*/scripts/registrar_outputs.py
git commit -m "vista procesal: las cinco carpetas de fase, y las skills pueden escribir en ellas"
```

---

## Task 2: cargar y validar el mapa del letrado

Las quince validaciones de §3.1 más el preflight de longitud de §3.2. Es la tarea con más superficie
de ataque del plan: todo lo que entre por aquí acaba siendo una escritura en el expediente.

**Files:**
- Create: `core/procedimiento/mapa.py`
- Test: `tests/test_procedimiento_mapa.py`

**Interfaces:**
- Consumes: `carpetas.CARPETAS_FASE`, `carpetas.es_carpeta_fase`.
- Produces:
  - `mapa.EntradaMapa` — dataclass frozen: `carpeta: str`, `origen: str`, `doc_id: str | None`,
    `orden: str | None`, `descripcion: str | None`, `fichero: str | None`, `eco_crm: str | None`,
    `sin_cobertura_ok: bool`, `logical_key: str`.
  - `mapa.MapaProcesal` — dataclass frozen: `version: int`, `expediente_crm: str`,
    `entradas: tuple[EntradaMapa, ...]`, `sin_asignar: tuple[dict, ...]`.
  - `mapa.MapaInvalidoError(Exception)` con `.problemas: list[str]`.
  - `mapa.cargar(case_dir: Path) -> MapaProcesal` — lanza `MapaInvalidoError` con **todos** los
    problemas, no el primero.
  - `mapa.mapa_path(case_dir: Path) -> Path`.
  - `mapa.nombre_destino(e: EntradaMapa, ext: str) -> str`.
  - `mapa.preflight_longitud(case_dir: Path, carpeta: str, nombre: str) -> str` — devuelve el nombre,
    truncado con sufijo hash estable si la ruta absoluta no cabe.

- [ ] **Step 1: Write the failing test — el camino feliz y la acumulación de problemas**

```python
# tests/test_procedimiento_mapa.py
"""Carga y validación de `_mapa_procesal.yaml` (spec §3, §3.1, §3.2)."""
import pytest

from core.procedimiento import mapa


def _escribir(tmp_path, texto: str):
    d = tmp_path / "05_Procedimiento"
    d.mkdir(parents=True, exist_ok=True)
    (d / "_mapa_procesal.yaml").write_text(texto, encoding="utf-8")
    return tmp_path


def test_carga_el_camino_feliz(tmp_path):
    case_dir = _escribir(tmp_path, """
version: 1
expediente_crm: '540'
carpetas:
  "03_Ordinario - Demanda y documentos":
    - {origen: crm, doc_id: '34939', orden: 'D-01', descripcion: encargo_de_venta}
    - {origen: despacho, fichero: CONCLUSIONES_W-02VEKE.docx}
sin_asignar:
  - {doc_id: '42498', fichero: dior_citacion.pdf, lote: '2026-07-27T16:35'}
""")
    m = mapa.cargar(case_dir)
    assert m.version == 1
    assert m.expediente_crm == "540"
    assert len(m.entradas) == 2
    crm, desp = m.entradas
    assert crm.logical_key == "crm:540:34939"
    assert crm.carpeta == "03_Ordinario - Demanda y documentos"
    assert crm.sin_cobertura_ok is False
    assert desp.logical_key == "despacho:CONCLUSIONES_W-02VEKE.docx"
    assert desp.doc_id is None
    assert len(m.sin_asignar) == 1


def test_acumula_TODOS_los_problemas_no_solo_el_primero(tmp_path):
    """Un mapa con tres errores los reporta los tres. Reportar el primero obliga al
    letrado a N pasadas para N errores."""
    case_dir = _escribir(tmp_path, """
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
        mapa.cargar(case_dir)
    problemas = "\n".join(exc.value.problemas)
    assert len(exc.value.problemas) == 3
    assert "99_Carpeta inventada" in problemas
    assert "marciano" in problemas
    assert "sub/dir/escrito.docx" in problemas
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_procedimiento_mapa.py -q --tb=short`
Expected: FAIL con `ModuleNotFoundError: No module named 'core.procedimiento.mapa'`

- [ ] **Step 3: Write the implementation**

```python
# core/procedimiento/mapa.py
"""Carga y validacion de `05_Procedimiento/_mapa_procesal.yaml` (spec §3).

El mapa lo escribe el LETRADO: es la unica fuente de la asignacion documento -> carpeta.
`plan` propone `orden` y `descripcion`, nunca la carpeta (spec §0).

Esta capa no toca disco mas que para leer el YAML. Todo lo que valide aqui deja de ser
un riesgo aguas abajo, porque aguas abajo hay escrituras en el expediente.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .carpetas import CARPETAS_FASE, es_carpeta_fase

MAPA_FILENAME = "_mapa_procesal.yaml"
VERSION_SOPORTADA = 1

ORIGEN_CRM = "crm"
ORIGEN_DESPACHO = "despacho"
ORIGENES = (ORIGEN_CRM, ORIGEN_DESPACHO)

#: Windows reserva estos nombres de dispositivo: un fichero asi es increable.
_RESERVADOS_WINDOWS = frozenset(
    ["con", "prn", "aux", "nul"]
    + [f"com{i}" for i in range(1, 10)]
    + [f"lpt{i}" for i in range(1, 10)]
)

#: Tope practico de ruta absoluta en Windows. El expediente ya contiene una ruta de 301
#: caracteres (spec §3.2), asi que la cadena depende de soporte de rutas largas; el
#: preflight es dinamico y no un tope fijo sobre `descripcion`.
LIMITE_RUTA = 259
LIMITE_SEGMENTO = 255


class MapaInvalidoError(Exception):
    """El mapa no cumple el contrato. Trae TODOS los problemas, no el primero."""

    def __init__(self, problemas: list[str]) -> None:
        self.problemas = problemas
        super().__init__(f"{len(problemas)} problema(s) en {MAPA_FILENAME}:\n" +
                         "\n".join(f"  - {p}" for p in problemas))


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


def mapa_path(case_dir: Path) -> Path:
    return Path(case_dir) / "05_Procedimiento" / MAPA_FILENAME


def _slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def nombre_destino(e: EntradaMapa, ext: str) -> str:
    """Nombre final del fichero en su carpeta.

    `origen: despacho` conserva SU nombre: la herramienta no renombra lo que no ha
    creado (spec §0). `origen: crm` se nombra `<orden>_<descripcion>.<ext>`.
    """
    if e.origen == ORIGEN_DESPACHO:
        return e.fichero or ""
    ext = ext.lstrip(".")
    return f"{e.orden}_{_slug(e.descripcion or '')}" + (f".{ext}" if ext else "")


def preflight_longitud(case_dir: Path, carpeta: str, nombre: str) -> str:
    """`nombre`, truncado con sufijo hash ESTABLE si la ruta absoluta no cabe.

    El sufijo sale del nombre completo, asi que es determinista entre corridas: dos
    `apply` seguidos producen el mismo destino y el segundo no ve un `mover`.
    """
    base = Path(case_dir).resolve() / "05_Procedimiento" / carpeta
    if len(str(base / nombre)) <= LIMITE_RUTA and len(nombre) <= LIMITE_SEGMENTO:
        return nombre
    stem, _, ext = nombre.rpartition(".")
    if not stem:
        stem, ext = nombre, ""
    sufijo = "~" + hashlib.sha256(nombre.encode("utf-8")).hexdigest()[:8]
    cola = (f".{ext}" if ext else "")
    margen = LIMITE_RUTA - len(str(base)) - 1 - len(sufijo) - len(cola)
    margen = min(margen, LIMITE_SEGMENTO - len(sufijo) - len(cola))
    if margen < 1:
        raise MapaInvalidoError([
            f"la ruta de {carpeta!r} no admite ningun nombre: "
            f"{len(str(base))} caracteres de carpeta sobre un limite de {LIMITE_RUTA}"
        ])
    return f"{stem[:margen]}{sufijo}{cola}"


def _validar_entrada(carpeta: str, i: int, raw: object,
                     problemas: list[str]) -> EntradaMapa | None:
    donde = f"{carpeta!r}[{i}]"
    if not isinstance(raw, dict):
        problemas.append(f"{donde}: cada entrada debe ser un mapa, no {type(raw).__name__}")
        return None

    origen = str(raw.get("origen") or "").strip()
    if origen not in ORIGENES:
        problemas.append(f"{donde}: `origen` es {origen!r}; validos: {list(ORIGENES)}")
        return None

    if origen == ORIGEN_CRM:
        faltan = [c for c in ("doc_id", "orden", "descripcion") if not raw.get(c)]
        if faltan:
            problemas.append(f"{donde}: la rama `crm` exige {faltan}")
            return None
        doc_id = str(raw["doc_id"]).strip()
        return EntradaMapa(
            carpeta=carpeta, origen=origen, doc_id=doc_id,
            orden=str(raw["orden"]).strip(),
            descripcion=str(raw["descripcion"]).strip(),
            sin_cobertura_ok=bool(raw.get("sin_cobertura_ok", False)),
            logical_key="",   # lo pone `cargar`, que conoce el expediente
        )

    fichero = str(raw.get("fichero") or "").strip()
    if not fichero:
        problemas.append(f"{donde}: la rama `despacho` exige `fichero`")
        return None
    if "/" in fichero or "\\" in fichero:
        problemas.append(f"{donde}: `fichero` debe ser un basename, no una ruta: {fichero!r}")
        return None
    if Path(fichero).is_absolute():
        problemas.append(f"{donde}: `fichero` no puede ser una ruta absoluta: {fichero!r}")
        return None
    if fichero in (".", ".."):
        problemas.append(f"{donde}: `fichero` no puede ser {fichero!r}")
        return None
    if Path(fichero).stem.lower() in _RESERVADOS_WINDOWS:
        problemas.append(f"{donde}: {fichero!r} usa un nombre reservado de Windows")
        return None
    if fichero != fichero.rstrip(" .") or fichero.startswith(" "):
        problemas.append(f"{donde}: {fichero!r} tiene espacios o puntos al principio o al final")
        return None
    eco = raw.get("eco_crm")
    return EntradaMapa(
        carpeta=carpeta, origen=origen, fichero=fichero,
        eco_crm=None if eco is None else str(eco).strip(),
        logical_key=f"{ORIGEN_DESPACHO}:{fichero}",
    )


def cargar(case_dir: Path) -> MapaProcesal:
    """Lee y valida el mapa. Lanza `MapaInvalidoError` con TODOS los problemas."""
    p = mapa_path(case_dir)
    problemas: list[str] = []
    if not p.is_file():
        raise MapaInvalidoError([f"no existe {p}"])
    try:
        datos = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise MapaInvalidoError([f"YAML ilegible: {exc}"]) from exc
    if not isinstance(datos, dict):
        raise MapaInvalidoError([f"la raiz debe ser un mapa, no {type(datos).__name__}"])

    version = datos.get("version")
    if version != VERSION_SOPORTADA:
        problemas.append(f"`version` es {version!r}; soportada: {VERSION_SOPORTADA}")
    expediente = str(datos.get("expediente_crm") or "").strip()
    if not expediente:
        problemas.append("falta `expediente_crm`")

    crudas = datos.get("carpetas") or {}
    if not isinstance(crudas, dict):
        problemas.append(f"`carpetas` debe ser un mapa, no {type(crudas).__name__}")
        crudas = {}

    entradas: list[EntradaMapa] = []
    for carpeta, lista in crudas.items():
        if not es_carpeta_fase(str(carpeta)):
            problemas.append(
                f"carpeta fuera de la lista blanca: {carpeta!r}; validas: {list(CARPETAS_FASE)}")
            continue
        if not isinstance(lista, list):
            problemas.append(f"{carpeta!r}: debe contener una lista de entradas")
            continue
        for i, raw in enumerate(lista):
            e = _validar_entrada(str(carpeta), i, raw, problemas)
            if e is None:
                continue
            if e.origen == ORIGEN_CRM:
                e = EntradaMapa(**{**e.__dict__,
                                   "logical_key": f"{ORIGEN_CRM}:{expediente}:{e.doc_id}"})
            entradas.append(e)

    # clave logica duplicada
    vistas: dict[str, str] = {}
    for e in entradas:
        if e.logical_key in vistas:
            problemas.append(
                f"clave logica duplicada {e.logical_key!r}: en {vistas[e.logical_key]!r} "
                f"y en {e.carpeta!r}")
        else:
            vistas[e.logical_key] = e.carpeta

    if problemas:
        raise MapaInvalidoError(problemas)

    sin_asignar = tuple(d for d in (datos.get("sin_asignar") or []) if isinstance(d, dict))
    return MapaProcesal(version=int(version), expediente_crm=expediente,
                        entradas=tuple(entradas), sin_asignar=sin_asignar)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_procedimiento_mapa.py -q --tb=short`
Expected: PASS (2 tests)

- [ ] **Step 5: Write the remaining validation tests (§3.1 completo)**

Añadir a `tests/test_procedimiento_mapa.py`:

```python
@pytest.mark.parametrize("entrada,fragmento", [
    ("{origen: despacho, fichero: '../fuera.docx'}", "basename"),
    ("{origen: despacho, fichero: '/abs/escrito.docx'}", "basename"),
    ("{origen: despacho, fichero: 'CON'}", "reservado"),
    ("{origen: despacho, fichero: 'NUL.docx'}", "reservado"),
    ("{origen: despacho, fichero: 'escrito.docx '}", "espacios o puntos"),
    ("{origen: despacho, fichero: 'escrito.'}", "espacios o puntos"),
    ("{origen: despacho}", "exige `fichero`"),
    ("{origen: crm, doc_id: '1'}", "exige"),
    ("{origen: crm, orden: '00', descripcion: x}", "exige"),
])
def test_rechaza_entradas_invalidas(tmp_path, entrada, fragmento):
    case_dir = _escribir(tmp_path, f"""
version: 1
expediente_crm: '540'
carpetas:
  "05_Otros escritos":
    - {entrada}
""")
    with pytest.raises(mapa.MapaInvalidoError) as exc:
        mapa.cargar(case_dir)
    assert fragmento in "\\n".join(exc.value.problemas)


def test_rechaza_clave_logica_duplicada_entre_carpetas(tmp_path):
    """El mismo `doc_id` en dos carpetas es el error que produciria dos destinos para
    una identidad. Distinto de §4.2, que son doc_id DISTINTOS con el mismo contenido."""
    case_dir = _escribir(tmp_path, """
version: 1
expediente_crm: '540'
carpetas:
  "01_Monitorio - Demanda y documentos":
    - {origen: crm, doc_id: '77', orden: '00', descripcion: demanda}
  "03_Ordinario - Demanda y documentos":
    - {origen: crm, doc_id: '77', orden: '00', descripcion: demanda}
""")
    with pytest.raises(mapa.MapaInvalidoError) as exc:
        mapa.cargar(case_dir)
    assert "duplicada" in "\\n".join(exc.value.problemas)
    assert "crm:540:77" in "\\n".join(exc.value.problemas)


def test_version_desconocida_no_se_lee_como_cero_documentos(tmp_path):
    case_dir = _escribir(tmp_path, "version: 99\nexpediente_crm: '540'\ncarpetas: {}\n")
    with pytest.raises(mapa.MapaInvalidoError) as exc:
        mapa.cargar(case_dir)
    assert "version" in "\\n".join(exc.value.problemas)


def test_yaml_ilegible_no_degrada_a_mapa_vacio(tmp_path):
    case_dir = _escribir(tmp_path, "version: 1\ncarpetas: [[[\n")
    with pytest.raises(mapa.MapaInvalidoError):
        mapa.cargar(case_dir)


def test_mapa_ausente_lanza_y_no_devuelve_vacio(tmp_path):
    (tmp_path / "05_Procedimiento").mkdir(parents=True)
    with pytest.raises(mapa.MapaInvalidoError) as exc:
        mapa.cargar(tmp_path)
    assert "no existe" in "\\n".join(exc.value.problemas)
```

- [ ] **Step 6: Run test to verify it passes**

Run: `python -m pytest tests/test_procedimiento_mapa.py -q --tb=short`
Expected: PASS (16 tests)

- [ ] **Step 7: Write the naming and length tests (§3.2)**

```python
def test_nombre_destino_crm_y_despacho():
    crm = mapa.EntradaMapa(carpeta="05_Otros escritos", origen="crm", doc_id="1",
                           orden="D-02", descripcion="Contrato de Mediación")
    assert mapa.nombre_destino(crm, "pdf") == "D-02_contrato_de_mediacion.pdf"
    desp = mapa.EntradaMapa(carpeta="05_Otros escritos", origen="despacho",
                            fichero="CONCLUSIONES_W-02VEKE.docx")
    assert mapa.nombre_destino(desp, "docx") == "CONCLUSIONES_W-02VEKE.docx"


def test_preflight_no_toca_un_nombre_que_cabe(tmp_path):
    n = mapa.preflight_longitud(tmp_path, "05_Otros escritos", "D-02_corto.pdf")
    assert n == "D-02_corto.pdf"


def test_preflight_trunca_con_sufijo_hash_ESTABLE(tmp_path):
    """Estable = dos llamadas dan lo mismo. Si el sufijo variara, cada `apply` veria
    un `mover` sobre el mismo documento."""
    largo = "D-02_" + ("x" * 400) + ".pdf"
    a = mapa.preflight_longitud(tmp_path, "05_Otros escritos", largo)
    b = mapa.preflight_longitud(tmp_path, "05_Otros escritos", largo)
    assert a == b
    assert a.endswith(".pdf")
    assert "~" in a
    assert len(str((tmp_path / "05_Procedimiento" / "05_Otros escritos" / a).resolve())) <= mapa.LIMITE_RUTA


def test_preflight_conserva_la_extension_al_truncar(tmp_path):
    n = mapa.preflight_longitud(tmp_path, "05_Otros escritos", "D-02_" + "y" * 400 + ".docx")
    assert n.endswith(".docx")
```

- [ ] **Step 8: Run test to verify it passes**

Run: `python -m pytest tests/test_procedimiento_mapa.py -q --tb=short`
Expected: PASS (20 tests)

- [ ] **Step 9: Commit**

```bash
git add core/procedimiento/mapa.py tests/test_procedimiento_mapa.py
git commit -m "vista procesal: carga y validacion del mapa del letrado (spec 3.1, 3.2)"
```

---

## Task 3: qué fichero se copia — el selector por clase documental

Implementa la tabla de §2.4. La regla que gobierna: **la fuente de estado es `_cobertura.json`, no la
presencia de ficheros.**

**Files:**
- Create: `core/procedimiento/artefacto.py`
- Test: `tests/test_procedimiento_artefacto.py`

**Interfaces:**
- Consumes: `core.sala_maquina.DocCobertura`, `core.sala_maquina.cobertura_desde_dicts`,
  `core.utils.output_slug`.
- Produces:
  - `artefacto.Eleccion` — dataclass frozen: `source_kind: str` (`"raw"`|`"converted"`),
    `source_rel: str` (ruta relativa al caso), `ext: str`, `aviso: str`, `bloqueo: str`.
  - `artefacto.elegir(case_dir: Path, cob: DocCobertura, *, raw_rel: str, sin_cobertura_ok: bool) -> Eleccion`
  - `artefacto.cargar_cobertura(case_dir: Path) -> dict[str, DocCobertura]` — indexada por
    `sha256` del origen; agrupa bundles por `parent_sha256` y devuelve la **peor** calidad.
  - `artefacto.PEOR_CALIDAD: tuple[str, ...]` — orden de peor a mejor.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_procedimiento_artefacto.py
"""Selector por clase documental (spec §2.4): la cobertura decide, no el disco."""
import pytest

from core.procedimiento import artefacto
from core.sala_maquina import DocCobertura

SM = "01_Procesado/02_Sala de máquina"


def _cob(**kw):
    base = dict(slug="s", rel_path="05_CRM/01_Demanda/d.pdf", metodo="pypdf",
                estado="ok", sha256="a" * 64)
    base.update(kw)
    return DocCobertura(**base)


def test_pdf_con_texto_se_copia_el_crudo():
    e = artefacto.elegir(".", _cob(metodo="pypdf"),
                         raw_rel="00_Input/05_CRM/01_Demanda/d.pdf",
                         sin_cobertura_ok=False)
    assert e.source_kind == "raw"
    assert e.source_rel == "00_Input/05_CRM/01_Demanda/d.pdf"
    assert e.ext == "pdf"
    assert e.bloqueo == ""


def test_escaneado_se_copia_el_OCR_y_su_ruta_se_DERIVA_del_slug(tmp_path):
    (tmp_path / SM / "01_OCR").mkdir(parents=True)
    (tmp_path / SM / "01_OCR" / "mi_slug.pdf").write_bytes(b"%PDF-1.4 ocr")
    e = artefacto.elegir(tmp_path, _cob(metodo="ocr", slug="mi_slug"),
                         raw_rel="00_Input/05_CRM/99_Otros/escaneo.pdf",
                         sin_cobertura_ok=False)
    assert e.source_kind == "converted"
    assert e.source_rel == f"{SM}/01_OCR/mi_slug.pdf"
    assert e.bloqueo == ""


def test_escaneado_SIN_su_artefacto_BLOQUEA_y_no_degrada_al_crudo(tmp_path):
    """`metodo: ocr` dice que hay OCR. Si el fichero no esta, se bloquea: degradar al
    crudo en silencio entregaria un documento no buscable haciendolo pasar por bueno."""
    e = artefacto.elegir(tmp_path, _cob(metodo="ocr", slug="ausente"),
                         raw_rel="00_Input/05_CRM/99_Otros/escaneo.pdf",
                         sin_cobertura_ok=False)
    assert e.bloqueo != ""
    assert "01_OCR" in e.bloqueo
    assert e.source_kind == ""


def test_nativo_textual_se_copia_el_crudo():
    e = artefacto.elegir(".", _cob(metodo="nativo", rel_path="x.docx"),
                         raw_rel="00_Input/05_CRM/01_Demanda/x.docx",
                         sin_cobertura_ok=False)
    assert e.source_kind == "raw"
    assert e.ext == "docx"


def test_ofimatica_se_copia_el_PDF_convertido_y_CAMBIA_de_extension(tmp_path):
    """`metodo: ofimatica` es la ruta LibreOffice (MEJORAS #61): el `.doc` de origen
    produce un PDF en 01_OCR. Es el caso de la demanda del ordinario del piloto."""
    (tmp_path / SM / "01_OCR").mkdir(parents=True)
    (tmp_path / SM / "01_OCR" / "dem.pdf").write_bytes(b"%PDF-1.4")
    e = artefacto.elegir(tmp_path, _cob(metodo="ofimatica", slug="dem", rel_path="dem.doc"),
                         raw_rel="00_Input/05_CRM/01_Demanda/dem.doc",
                         sin_cobertura_ok=False)
    assert e.source_kind == "converted"
    assert e.ext == "pdf"


def test_sin_soporte_se_copia_el_crudo_CON_AVISO():
    e = artefacto.elegir(".", _cob(metodo="sin_soporte", estado="sin_soporte",
                                   rel_path="v.mkv"),
                         raw_rel="00_Input/05_CRM/99_Otros/v.mkv",
                         sin_cobertura_ok=False)
    assert e.source_kind == "raw"
    assert e.aviso != ""
    assert e.bloqueo == ""


def test_vision_produce_MD_sin_PDF_y_por_tanto_se_copia_el_crudo_con_aviso():
    """`metodo: vision` deja MD pero no artefacto de custodia en 01_OCR (ocr=False).
    El MD suelto NUNCA sustituye a un documento visual (criterio 2026-07-19)."""
    e = artefacto.elegir(".", _cob(metodo="vision", ocr=False),
                         raw_rel="00_Input/05_CRM/99_Otros/f.pdf",
                         sin_cobertura_ok=False)
    assert e.source_kind == "raw"
    assert "vision" in e.aviso.lower()


def test_imagen_sin_texto_se_copia_el_crudo():
    """Una foto de algo, no de una pagina: el PDF no aporta nada (spec §2.4)."""
    e = artefacto.elegir(".", _cob(metodo="ocr", estado="empty", rel_path="foto.jpg"),
                         raw_rel="00_Input/01_Drive EV/foto.jpg",
                         sin_cobertura_ok=False)
    assert e.source_kind == "raw"
    assert e.ext == "jpg"


def test_sin_cobertura_BLOQUEA():
    e = artefacto.elegir(".", None, raw_rel="00_Input/05_CRM/01_Demanda/d.pdf",
                         sin_cobertura_ok=False)
    assert e.bloqueo != ""


def test_sin_cobertura_con_override_pasa_y_deja_constancia():
    e = artefacto.elegir(".", None, raw_rel="00_Input/05_CRM/01_Demanda/d.pdf",
                         sin_cobertura_ok=True)
    assert e.bloqueo == ""
    assert e.source_kind == "raw"
    assert "override" in e.aviso.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_procedimiento_artefacto.py -q --tb=short`
Expected: FAIL con `ModuleNotFoundError: No module named 'core.procedimiento.artefacto'`

- [ ] **Step 3: Write the implementation**

```python
# core/procedimiento/artefacto.py
"""Que fichero se copia a la vista (spec §2.4).

La fuente de estado es `_cobertura.json`, NO la presencia de ficheros: inferir «no hay
01_OCR/ => el crudo ya tenia texto» es falso con un OCR borrado, con una extraccion por
vision y con un estado idempotente obsoleto. Quien dice que hay OCR es `metodo`; la ruta
del artefacto se DERIVA del slug y su existencia es una VERIFICACION, no una inferencia.

Esta capa no promete buscabilidad: `estado: ok` puede ser falso para un escaneo cuyo
unico texto es el pie de firma electronica (`MEJORAS #90`). Copia el mejor artefacto
disponible y reporta lo que la cobertura declara.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from core.sala_maquina import DocCobertura, cobertura_desde_dicts

SM_REL = "01_Procesado/02_Sala de máquina"
OCR_REL = f"{SM_REL}/01_OCR"

#: De peor a mejor. La calidad de un bundle es la PEOR de sus segmentos (spec §2.4).
PEOR_CALIDAD: tuple[str, ...] = ("error", "sin_soporte", "empty", "low", "ok")

#: Metodos que producen un PDF de custodia en `01_OCR/<slug>.pdf`.
_METODOS_CON_ARTEFACTO = frozenset({"ocr", "ofimatica"})
#: Metodos cuyo origen se copia crudo.
_METODOS_CRUDO = frozenset({"pypdf", "nativo", "sin_soporte", "vision"})


@dataclass(frozen=True)
class Eleccion:
    source_kind: str = ""      # "raw" | "converted" | "" si hay bloqueo
    source_rel: str = ""
    ext: str = ""
    aviso: str = ""
    bloqueo: str = ""


def cobertura_path(case_dir: Path) -> Path:
    return Path(case_dir) / SM_REL / "_cobertura.json"


def cargar_cobertura(case_dir: Path) -> dict[str, DocCobertura]:
    """`sha256 del origen -> fila`. Los bundles se agrupan por `parent_sha256` y la
    fila resultante lleva la PEOR calidad de sus segmentos.

    Devuelve `{}` solo si el fichero no existe. Un JSON corrupto LANZA: «cero
    documentos» y «no pude leerlo» no son lo mismo, y confundirlos haria que la vista
    se construyera entera desde crudo creyendo que no hay sala de maquina.
    """
    p = cobertura_path(case_dir)
    if not p.is_file():
        return {}
    filas = cobertura_desde_dicts(json.loads(p.read_text(encoding="utf-8")))
    out: dict[str, DocCobertura] = {}
    for f in filas:
        clave = f.parent_sha256 or f.sha256
        if not clave:
            continue
        previo = out.get(clave)
        if previo is None:
            out[clave] = f
            continue
        # peor calidad gana; ante empate se conserva la primera (orden del fichero)
        if _rango(f.estado) < _rango(previo.estado):
            out[clave] = f
    return out


def _rango(estado: str) -> int:
    try:
        return PEOR_CALIDAD.index(estado)
    except ValueError:
        return 0        # un estado desconocido es lo peor: no se le da el beneficio


def _ext_de(rel: str) -> str:
    nombre = rel.replace("\\", "/").rsplit("/", 1)[-1]
    return nombre.rsplit(".", 1)[-1].lower() if "." in nombre else ""


def elegir(case_dir: Path, cob: DocCobertura | None, *, raw_rel: str,
           sin_cobertura_ok: bool) -> Eleccion:
    """Que fichero se copia para este documento, o por que se bloquea."""
    if cob is None:
        if not sin_cobertura_ok:
            return Eleccion(bloqueo=(
                f"sin cobertura vigente para {raw_rel!r}: corre la sala de maquina, o "
                f"declara `sin_cobertura_ok: true` en su entrada del mapa"))
        return Eleccion(source_kind="raw", source_rel=raw_rel, ext=_ext_de(raw_rel),
                        aviso="override `sin_cobertura_ok`: se copia el crudo, no buscable")

    metodo = (cob.metodo or "").strip()

    # Imagen sin texto: es una foto de algo, no de una pagina.
    if cob.estado == "empty" and _ext_de(raw_rel) not in {"pdf", ""}:
        return Eleccion(source_kind="raw", source_rel=raw_rel, ext=_ext_de(raw_rel),
                        aviso="imagen sin texto: se copia el original")

    if metodo in _METODOS_CON_ARTEFACTO:
        if not cob.slug:
            return Eleccion(bloqueo=(
                f"`metodo: {metodo}` sin `slug` en la cobertura de {raw_rel!r}: "
                f"no se puede derivar la ruta del artefacto"))
        rel = f"{OCR_REL}/{cob.slug}.pdf"
        if not (Path(case_dir) / rel).is_file():
            return Eleccion(bloqueo=(
                f"`metodo: {metodo}` declara artefacto para {raw_rel!r} pero no existe "
                f"{rel}: no se degrada al crudo en silencio"))
        aviso = ""
        if cob.estado in ("low", "empty"):
            aviso = f"calidad declarada `{cob.estado}`: puede faltar texto"
        return Eleccion(source_kind="converted", source_rel=rel, ext="pdf", aviso=aviso)

    if metodo in _METODOS_CRUDO:
        avisos = []
        if metodo == "sin_soporte":
            avisos.append("`sin_soporte`: ni MD ni OCR; lo abre el letrado, ningun LLM lo lee")
        if metodo == "vision":
            avisos.append("extraido por vision: hay MD pero no PDF buscable de custodia")
        if cob.estado in ("low", "empty") and metodo != "sin_soporte":
            avisos.append(f"calidad declarada `{cob.estado}`")
        return Eleccion(source_kind="raw", source_rel=raw_rel, ext=_ext_de(raw_rel),
                        aviso="; ".join(avisos))

    return Eleccion(bloqueo=(
        f"`metodo: {metodo!r}` desconocido para {raw_rel!r}: el selector no adivina"))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_procedimiento_artefacto.py -q --tb=short`
Expected: PASS (11 tests)

- [ ] **Step 5: Write the bundle and corruption tests**

```python
def test_bundle_toma_la_PEOR_calidad_de_sus_segmentos(tmp_path):
    (tmp_path / SM).mkdir(parents=True)
    (tmp_path / SM / "_cobertura.json").write_text(json.dumps([
        {"slug": "b__1", "rel_path": "05_CRM/x.pdf", "metodo": "ocr", "estado": "ok",
         "sha256": "s1", "parent_sha256": "P"},
        {"slug": "b__2", "rel_path": "05_CRM/x.pdf", "metodo": "ocr", "estado": "low",
         "sha256": "s2", "parent_sha256": "P"},
    ]), encoding="utf-8")
    cob = artefacto.cargar_cobertura(tmp_path)
    assert cob["P"].estado == "low"


def test_cobertura_ausente_devuelve_vacio_pero_corrupta_LANZA(tmp_path):
    assert artefacto.cargar_cobertura(tmp_path) == {}
    (tmp_path / SM).mkdir(parents=True)
    (tmp_path / SM / "_cobertura.json").write_text("{{{", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        artefacto.cargar_cobertura(tmp_path)


def test_metodo_desconocido_bloquea_en_vez_de_adivinar():
    e = artefacto.elegir(".", _cob(metodo="teletransporte"),
                         raw_rel="00_Input/05_CRM/d.pdf", sin_cobertura_ok=False)
    assert e.bloqueo != ""
```

Añadir `import json` al principio del fichero de test.

- [ ] **Step 6: Run test to verify it passes**

Run: `python -m pytest tests/test_procedimiento_artefacto.py -q --tb=short`
Expected: PASS (14 tests)

- [ ] **Step 7: Commit**

```bash
git add core/procedimiento/artefacto.py tests/test_procedimiento_artefacto.py
git commit -m "vista procesal: selector por clase documental, la cobertura decide (spec 2.4)"
```

---

## Task 4: el ledger de propiedad

`_MANIFIESTO_PROCESAL.json`: qué creó `apply` y qué puede tocar. Es lo que separa «este fichero es
mío» de «este fichero es del letrado».

**Files:**
- Create: `core/procedimiento/ledger.py`
- Test: `tests/test_procedimiento_ledger.py`

**Interfaces:**
- Consumes: nada de las tareas anteriores.
- Produces:
  - `ledger.AsientoLedger` — dataclass frozen con los campos del spec §4.1: `logical_key`,
    `origen`, `carpeta`, `destino`, `raw_path`, `raw_sha256`, `source_kind`, `source_path`,
    `source_sha256`, `destination_sha256`.
  - `ledger.Ledger` — `asientos: dict[str, AsientoLedger]` por `logical_key`.
  - `ledger.LedgerInvalidoError(Exception)`
  - `ledger.ledger_path(case_dir) -> Path`
  - `ledger.cargar(case_dir) -> Ledger`
  - `ledger.guardar(case_dir, ledger) -> Path` — escritura **atómica** (`os.replace`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_procedimiento_ledger.py
"""Ledger de propiedad de la vista procesal."""
import json

import pytest

from core.procedimiento import ledger


def _asiento(**kw):
    base = dict(logical_key="crm:540:1", origen="crm",
                carpeta="03_Ordinario - Demanda y documentos",
                destino="D-01_encargo.pdf",
                raw_path="00_Input/05_CRM/01_Demanda/e.pdf", raw_sha256="r" * 64,
                source_kind="raw", source_path="00_Input/05_CRM/01_Demanda/e.pdf",
                source_sha256="r" * 64, destination_sha256="d" * 64)
    base.update(kw)
    return ledger.AsientoLedger(**base)


def test_ida_y_vuelta(tmp_path):
    (tmp_path / "05_Procedimiento").mkdir(parents=True)
    l = ledger.Ledger(asientos={"crm:540:1": _asiento()})
    ledger.guardar(tmp_path, l)
    leido = ledger.cargar(tmp_path)
    assert leido.asientos["crm:540:1"].destination_sha256 == "d" * 64
    assert leido.asientos["crm:540:1"].carpeta == "03_Ordinario - Demanda y documentos"


def test_ledger_ausente_es_un_ledger_VACIO_no_un_error(tmp_path):
    """Una vista que no se ha construido nunca no tiene ledger. Eso es legitimo."""
    (tmp_path / "05_Procedimiento").mkdir(parents=True)
    assert ledger.cargar(tmp_path).asientos == {}


def test_ledger_CORRUPTO_lanza_y_nunca_se_lee_como_vacio(tmp_path):
    """Un ledger vacio autoriza a crear todo; uno corrupto leido como vacio autorizaria
    a PISAR todo. La distincion es la puerta 1 del spec §5."""
    (tmp_path / "05_Procedimiento").mkdir(parents=True)
    ledger.ledger_path(tmp_path).write_text("{{{", encoding="utf-8")
    with pytest.raises(ledger.LedgerInvalidoError):
        ledger.cargar(tmp_path)


def test_version_desconocida_lanza(tmp_path):
    (tmp_path / "05_Procedimiento").mkdir(parents=True)
    ledger.ledger_path(tmp_path).write_text(
        json.dumps({"version": 99, "asientos": []}), encoding="utf-8")
    with pytest.raises(ledger.LedgerInvalidoError):
        ledger.cargar(tmp_path)


def test_guardar_es_atomico_y_no_deja_temporales(tmp_path):
    (tmp_path / "05_Procedimiento").mkdir(parents=True)
    ledger.guardar(tmp_path, ledger.Ledger(asientos={"crm:540:1": _asiento()}))
    sobrantes = [p.name for p in (tmp_path / "05_Procedimiento").iterdir()
                 if p.name != ledger.LEDGER_FILENAME]
    assert sobrantes == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_procedimiento_ledger.py -q --tb=short`
Expected: FAIL con `ModuleNotFoundError: No module named 'core.procedimiento.ledger'`

- [ ] **Step 3: Write the implementation**

```python
# core/procedimiento/ledger.py
"""`05_Procedimiento/_MANIFIESTO_PROCESAL.json` — ledger de propiedad (spec §4.1).

Dice QUE creo `apply` y, por tanto, que puede tocar. Un fichero de la vista que no
consta aqui es ajeno y no se toca; uno que consta pero cuyo SHA no cuadra se aborta.

Guarda procedencia DOBLE: el SHA del crudo y el del fichero copiado, mas de que se
derivo. Sin eso no hay cadena de custodia del artefacto (spec §2.4).
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from core.utils import now_iso

LEDGER_FILENAME = "_MANIFIESTO_PROCESAL.json"
VERSION_SOPORTADA = 1


class LedgerInvalidoError(Exception):
    """El ledger existe y no se puede interpretar. NUNCA se degrada a vacio."""


@dataclass(frozen=True)
class AsientoLedger:
    logical_key: str
    origen: str
    carpeta: str
    destino: str                 # basename dentro de la carpeta
    raw_path: str = ""           # relativo al caso
    raw_sha256: str = ""
    source_kind: str = ""        # raw | converted
    source_path: str = ""
    source_sha256: str = ""
    destination_sha256: str = ""

    @property
    def destino_rel(self) -> str:
        return f"05_Procedimiento/{self.carpeta}/{self.destino}"


@dataclass
class Ledger:
    asientos: dict[str, AsientoLedger]


def ledger_path(case_dir: Path) -> Path:
    return Path(case_dir) / "05_Procedimiento" / LEDGER_FILENAME


def cargar(case_dir: Path) -> Ledger:
    p = ledger_path(case_dir)
    if not p.is_file():
        return Ledger(asientos={})
    try:
        datos = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise LedgerInvalidoError(f"{p} ilegible: {exc}") from exc
    if not isinstance(datos, dict):
        raise LedgerInvalidoError(f"{p}: la raiz debe ser un objeto")
    if datos.get("version") != VERSION_SOPORTADA:
        raise LedgerInvalidoError(
            f"{p}: version {datos.get('version')!r}; soportada {VERSION_SOPORTADA}")
    validos = {f.name for f in fields(AsientoLedger)}
    out: dict[str, AsientoLedger] = {}
    for raw in datos.get("asientos") or []:
        if not isinstance(raw, dict) or not raw.get("logical_key"):
            raise LedgerInvalidoError(f"{p}: asiento sin `logical_key`: {raw!r}")
        a = AsientoLedger(**{k: v for k, v in raw.items() if k in validos})
        if a.logical_key in out:
            raise LedgerInvalidoError(f"{p}: `logical_key` duplicada: {a.logical_key!r}")
        out[a.logical_key] = a
    return Ledger(asientos=out)


def guardar(case_dir: Path, l: Ledger) -> Path:
    """Escritura atomica: temporal en el MISMO directorio + `os.replace`.

    El ledger es el ULTIMO commit de `apply` (spec §4.1): si la corrida muere antes,
    el ledger sigue describiendo el estado anterior y `plan` reconcilia.
    """
    p = ledger_path(case_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    cuerpo = {
        "version": VERSION_SOPORTADA,
        "generado": now_iso(),
        "asientos": [asdict(a) for a in sorted(l.asientos.values(),
                                               key=lambda a: a.logical_key)],
    }
    tmp = p.with_name(f".{p.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(cuerpo, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8")
    os.replace(tmp, p)
    return p
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_procedimiento_ledger.py -q --tb=short`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add core/procedimiento/ledger.py tests/test_procedimiento_ledger.py
git commit -m "vista procesal: ledger de propiedad con procedencia doble"
```

---

## Task 5: la puerta de integridad y el diff

Las nueve categorías de §4.1 y las puertas 1-9 de §5. `plan` **no escribe nada**.

**Files:**
- Create: `core/procedimiento/diff.py`
- Test: `tests/test_procedimiento_diff.py`

**Interfaces:**
- Consumes: `mapa.MapaProcesal`, `mapa.EntradaMapa`, `mapa.nombre_destino`,
  `mapa.preflight_longitud`, `artefacto.elegir`, `artefacto.cargar_cobertura`,
  `ledger.Ledger`, `core.ocurrencias_crm.RegistroOcurrencias`,
  `core.case_manager.read_pull_state`.
- Produces:
  - `diff.Operacion` — dataclass frozen: `accion: str`, `logical_key: str`, `carpeta: str`,
    `destino: str`, `source_rel: str`, `source_kind: str`, `motivo: str`.
    `accion` ∈ `copiar | adoptar | reemplazar | mover | registrar | borrar | desregistrar`.
    **`adoptar`** es el residuo de un `apply` interrumpido: el destino existe con **exactamente
    los bytes** que íbamos a escribir y no tiene asiento. Se registra sin tocar el fichero.
  - `diff.PlanProcesal` — dataclass frozen: `case_id`, `expediente_id`,
    `operaciones: tuple[Operacion, ...]`, `sin_asignar: tuple[str, ...]`,
    `avisos: tuple[str, ...]`, `ajenos: tuple[str, ...]`, `bloqueos: tuple[str, ...]`.
    Propiedad `vacio: bool`.
  - `diff.construir(case_dir, case_id, expediente_id, *, m, reg, cob, led) -> PlanProcesal`

- [ ] **Step 1: Write the failing test — el diff básico**

```python
# tests/test_procedimiento_diff.py
"""Puerta de integridad y diff (spec §4.1, §5.1-5.9). `plan` no escribe nada."""
import json

import pytest

from core.procedimiento import diff, ledger, mapa
from core.ocurrencias_crm import RegistroOcurrencias

CARP = "03_Ordinario - Demanda y documentos"


def _arbol(tmp_path):
    """Arbol sintetico: nada de esto toca el arbol de produccion."""
    for sub in ("00_Input/05_CRM/01_Demanda", f"05_Procedimiento/{CARP}",
                "01_Procesado/02_Sala de máquina"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    return tmp_path


def _cob(tmp_path, filas):
    (tmp_path / "01_Procesado/02_Sala de máquina/_cobertura.json").write_text(
        json.dumps(filas), encoding="utf-8")


def test_una_entrada_crm_sin_fichero_en_destino_es_COPIAR(tmp_path):
    case_dir = _arbol(tmp_path)
    (case_dir / "00_Input/05_CRM/01_Demanda/e.pdf").write_bytes(b"%PDF-1.4 encargo")
    _cob(case_dir, [{"slug": "e", "rel_path": "05_CRM/01_Demanda/e.pdf",
                     "metodo": "pypdf", "estado": "ok", "sha256": "SHA_E"}])

    reg = RegistroOcurrencias.__new__(RegistroOcurrencias)
    reg.ocurrencias = {"crm:540:1": {
        "source": "crm", "expediente_id": "540", "doc_id": "1",
        "revisiones": [{"estado": "materializada", "filename": "e.pdf",
                        "modified_at": "2025-08-14T00:00:00+02:00", "id_carpeta": "307",
                        "path": "05_CRM/01_Demanda/e.pdf", "sha256": "SHA_E"}]}}

    m = mapa.MapaProcesal(version=1, expediente_crm="540", entradas=(
        mapa.EntradaMapa(carpeta=CARP, origen="crm", doc_id="1", orden="D-01",
                         descripcion="encargo_de_venta", logical_key="crm:540:1"),))

    p = diff.construir(case_dir, "CASO", "540", m=m, reg=reg,
                       cob=None, led=ledger.Ledger(asientos={}),
                       pull_state={"documents_total_crm": 1, "doc_ids": ["1"]})
    assert p.bloqueos == ()
    assert [o.accion for o in p.operaciones] == ["copiar"]
    o = p.operaciones[0]
    assert o.destino == "D-01_encargo_de_venta.pdf"
    assert o.source_rel == "00_Input/05_CRM/01_Demanda/e.pdf"
    assert o.source_kind == "raw"


def test_un_docid_del_pull_state_sin_ocurrencia_BLOQUEA(tmp_path):
    """Puerta §5.2: el CRM dice N documentos y el registro no los tiene. Correr asi
    construiria una vista incompleta creyendola completa."""
    case_dir = _arbol(tmp_path)
    reg = RegistroOcurrencias.__new__(RegistroOcurrencias)
    reg.ocurrencias = {}
    m = mapa.MapaProcesal(version=1, expediente_crm="540", entradas=())
    p = diff.construir(case_dir, "CASO", "540", m=m, reg=reg, cob=None,
                       led=ledger.Ledger(asientos={}),
                       pull_state={"documents_total_crm": 1, "doc_ids": ["9"]})
    assert any("9" in b for b in p.bloqueos)


def test_una_ocurrencia_SOLO_LISTADA_bloquea_con_el_remedio_nombrado(tmp_path):
    """Ajuste del spec a la implementacion: `listada` != disponible en disco. Es el
    intake acotado (2 de 76 documentos), y el remedio es `--full`."""
    case_dir = _arbol(tmp_path)
    reg = RegistroOcurrencias.__new__(RegistroOcurrencias)
    reg.ocurrencias = {"crm:540:1": {
        "source": "crm", "expediente_id": "540", "doc_id": "1",
        "revisiones": [{"estado": "listada", "filename": "e.pdf",
                        "modified_at": "x", "id_carpeta": "307",
                        "path": None, "sha256": None}]}}
    m = mapa.MapaProcesal(version=1, expediente_crm="540", entradas=(
        mapa.EntradaMapa(carpeta=CARP, origen="crm", doc_id="1", orden="D-01",
                         descripcion="e", logical_key="crm:540:1"),))
    p = diff.construir(case_dir, "CASO", "540", m=m, reg=reg, cob=None,
                       led=ledger.Ledger(asientos={}),
                       pull_state={"documents_total_crm": 1, "doc_ids": ["1"]})
    texto = "\n".join(p.bloqueos)
    assert "listada" in texto
    assert "--full" in texto


def test_sin_asignar_no_vacio_BLOQUEA(tmp_path):
    """Puerta §5.6: garantiza que nada que exista se queda fuera EN SILENCIO."""
    case_dir = _arbol(tmp_path)
    (case_dir / "00_Input/05_CRM/01_Demanda/e.pdf").write_bytes(b"x")
    reg = RegistroOcurrencias.__new__(RegistroOcurrencias)
    reg.ocurrencias = {"crm:540:7": {
        "source": "crm", "expediente_id": "540", "doc_id": "7",
        "revisiones": [{"estado": "materializada", "filename": "e.pdf",
                        "modified_at": "x", "id_carpeta": "307",
                        "path": "05_CRM/01_Demanda/e.pdf", "sha256": "S"}]}}
    m = mapa.MapaProcesal(version=1, expediente_crm="540", entradas=())
    p = diff.construir(case_dir, "CASO", "540", m=m, reg=reg, cob=None,
                       led=ledger.Ledger(asientos={}),
                       pull_state={"documents_total_crm": 1, "doc_ids": ["7"]})
    assert "7" in "\n".join(p.sin_asignar)
    assert any("sin_asignar" in b for b in p.bloqueos)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_procedimiento_diff.py -q --tb=short`
Expected: FAIL con `ModuleNotFoundError: No module named 'core.procedimiento.diff'`

- [ ] **Step 3: Write the implementation**

```python
# core/procedimiento/diff.py
"""Puerta de integridad y diff de la vista procesal (spec §4.1, §5.1-§5.9).

`construir` NO escribe nada. Devuelve las operaciones, lo no asignado, los avisos, los
ficheros ajenos y los bloqueos. Si hay un solo bloqueo, `apply` no corre.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from . import artefacto as art
from . import mapa as mp
from .carpetas import CARPETAS_FASE
from .ledger import Ledger

ACCIONES = ("copiar", "adoptar", "reemplazar", "mover", "registrar", "borrar",
            "desregistrar")

#: Ficheros de control de la vista: nunca cuentan como ajenos (spec §2.3).
_CONTROL = ("_index.md", "_MANIFIESTO_PROCESAL.json", "_mapa_procesal.yaml")


@dataclass(frozen=True)
class Operacion:
    accion: str
    logical_key: str
    carpeta: str
    destino: str
    source_rel: str = ""
    source_kind: str = ""
    motivo: str = ""


@dataclass(frozen=True)
class PlanProcesal:
    case_id: str
    expediente_id: str
    operaciones: tuple[Operacion, ...] = ()
    sin_asignar: tuple[str, ...] = ()
    avisos: tuple[str, ...] = ()
    ajenos: tuple[str, ...] = ()
    bloqueos: tuple[str, ...] = ()

    @property
    def vacio(self) -> bool:
        return not self.operaciones


def _sha_de(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def _sha_rel(case_dir: Path, rel: str) -> str:
    """`sha256` de una ruta relativa al caso; `""` si no hay ruta o no existe.

    Devolver `""` para el ausente hace que la comparacion de identidad FALLE en vez de
    coincidir con otro ausente: dos huecos no son el mismo fichero.
    """
    if not rel:
        return ""
    p = Path(case_dir) / rel
    return _sha_de(p) if p.is_file() else ""


def _es_control(nombre: str) -> bool:
    return nombre in _CONTROL or (nombre.startswith("_") and
                                  nombre.endswith((".md", ".json", ".yaml")))


def construir(case_dir, case_id: str, expediente_id: str, *, m: mp.MapaProcesal,
              reg, cob: dict | None, led: Ledger, pull_state: dict | None) -> PlanProcesal:
    case_dir = Path(case_dir)
    bloqueos: list[str] = []
    avisos: list[str] = []
    ops: list[Operacion] = []

    if str(m.expediente_crm) != str(expediente_id):
        bloqueos.append(
            f"el mapa declara `expediente_crm: {m.expediente_crm!r}` y se pidio "
            f"{expediente_id!r}")
        return PlanProcesal(case_id, expediente_id, bloqueos=tuple(bloqueos))

    listadas = reg.listadas(expediente_id)
    materializadas = reg.materializadas(expediente_id)
    solo_listadas = reg.solo_listadas(expediente_id)

    # --- §5.2: cruce con el pull_state -----------------------------------
    ps = pull_state or {}
    doc_ids_ps = {str(d) for d in (ps.get("doc_ids") or [])}
    if doc_ids_ps:
        faltan = sorted(doc_ids_ps - set(listadas))
        if faltan:
            bloqueos.append(
                f"el `pull_state` declara doc_id sin ocurrencia en el registro: {faltan}. "
                f"Regenera con `sync_sudespacho pull` o `intake-judicial`")
        sobran = sorted(set(listadas) - doc_ids_ps)
        if sobran:
            bloqueos.append(
                f"ocurrencias del expediente fuera del `pull_state`: {sobran}. "
                f"El registro y el estado del pull discrepan; regenera el pull")
    total = ps.get("documents_total_crm")
    if isinstance(total, int) and total != len(listadas):
        avisos.append(
            f"el `pull_state` dice {total} documentos en el CRM y el registro tiene "
            f"{len(listadas)} ocurrencias")

    # --- cobertura -------------------------------------------------------
    if cob is None:
        cob = art.cargar_cobertura(case_dir)
    if not cob:
        avisos.append(
            "la sala de maquina no ha corrido sobre este caso: sin cobertura, todo "
            "documento soportado bloquea (usa `sin_cobertura_ok` solo a sabiendas)")

    # --- entradas del mapa ------------------------------------------------
    ecos = {e.eco_crm for e in m.entradas
            if e.origen == mp.ORIGEN_DESPACHO and e.eco_crm}
    asignados: set[str] = set()
    destinos_vistos: dict[str, str] = {}

    for e in m.entradas:
        if e.origen == mp.ORIGEN_CRM:
            asignados.add(e.doc_id or "")
            rev = materializadas.get(e.doc_id or "")
            if rev is None:
                if (e.doc_id or "") in solo_listadas:
                    bloqueos.append(
                        f"{e.logical_key}: la ocurrencia esta `listada` y no "
                        f"`materializada` — el CRM la enumera pero no esta en disco. "
                        f"Bajala con `sync_sudespacho intake-judicial --full`")
                else:
                    bloqueos.append(
                        f"{e.logical_key}: sin ocurrencia `materializada` en el registro")
                continue
            raw_rel = f"00_Input/{rev['path']}"
            if not (case_dir / raw_rel).is_file():
                bloqueos.append(f"{e.logical_key}: la ruta de origen no existe: {raw_rel}")
                continue
            eleccion = art.elegir(case_dir, cob.get(rev["sha256"]), raw_rel=raw_rel,
                                  sin_cobertura_ok=e.sin_cobertura_ok)
            if eleccion.bloqueo:
                bloqueos.append(f"{e.logical_key}: {eleccion.bloqueo}")
                continue
            if eleccion.aviso:
                avisos.append(f"{e.logical_key}: {eleccion.aviso}")
            nombre = mp.preflight_longitud(
                case_dir, e.carpeta, mp.nombre_destino(e, eleccion.ext))
        else:
            nombre = e.fichero or ""
            destino_abs = case_dir / "05_Procedimiento" / e.carpeta / nombre
            if not destino_abs.is_file():
                bloqueos.append(
                    f"{e.logical_key}: `origen: despacho` declara {nombre!r} en "
                    f"{e.carpeta!r} y el fichero no esta ahi")
                continue
            eleccion = art.Eleccion(source_kind="despacho", source_rel="", ext="")

        # §5.9: dos entradas que producen el mismo nombre final
        clave_col = f"{e.carpeta}/{nombre}".casefold()
        if clave_col in destinos_vistos:
            bloqueos.append(
                f"dos entradas producen el mismo nombre final {e.carpeta}/{nombre!r}: "
                f"{destinos_vistos[clave_col]} y {e.logical_key}")
            continue
        destinos_vistos[clave_col] = e.logical_key

        asiento = led.asientos.get(e.logical_key)
        destino_abs = case_dir / "05_Procedimiento" / e.carpeta / nombre
        if e.origen == mp.ORIGEN_DESPACHO:
            if asiento is None:
                ops.append(Operacion("registrar", e.logical_key, e.carpeta, nombre,
                                     motivo="entrada del despacho no inventariada"))
            continue
        if asiento is None:
            # Sin asiento y con el destino OCUPADO hay dos mundos distintos, y la
            # frontera NO es «existe» sino «son exactamente los bytes que yo iba a
            # escribir»: si lo son, es el residuo de un `apply` que murio antes de
            # commitear el ledger y adoptarlo es seguro; si no, es de otro y se aborta.
            # Sin esta distincion una corrida interrumpida deja el caso bloqueado para
            # siempre, porque toda pasada posterior llama «ajeno» a su propia copia.
            if not destino_abs.is_file():
                ops.append(Operacion("copiar", e.logical_key, e.carpeta, nombre,
                                     eleccion.source_rel, eleccion.source_kind,
                                     "sin asiento en el ledger"))
            elif _sha_de(destino_abs) == _sha_rel(case_dir, eleccion.source_rel):
                ops.append(Operacion("adoptar", e.logical_key, e.carpeta, nombre,
                                     eleccion.source_rel, eleccion.source_kind,
                                     "residuo de un apply interrumpido: mismos bytes, "
                                     "sin asiento"))
            else:
                bloqueos.append(
                    f"{e.logical_key}: el destino {e.carpeta}/{nombre!r} existe, no tiene "
                    f"asiento y su contenido NO es el que produciria esta corrida: es "
                    f"ajeno y no se pisa. Retiralo o dale entrada como `origen: despacho`")
        elif (asiento.carpeta, asiento.destino) != (e.carpeta, nombre):
            ops.append(Operacion("mover", e.logical_key, e.carpeta, nombre,
                                 eleccion.source_rel, eleccion.source_kind,
                                 f"estaba en {asiento.carpeta}/{asiento.destino}"))
        else:
            src_abs = case_dir / eleccion.source_rel
            src_sha = _sha_de(src_abs) if src_abs.is_file() else ""
            if src_sha != asiento.source_sha256 or eleccion.source_kind != asiento.source_kind:
                ops.append(Operacion("reemplazar", e.logical_key, e.carpeta, nombre,
                                     eleccion.source_rel, eleccion.source_kind,
                                     "el origen vigente cambio de bytes o de clase"))
            elif not destino_abs.is_file():
                ops.append(Operacion("copiar", e.logical_key, e.carpeta, nombre,
                                     eleccion.source_rel, eleccion.source_kind,
                                     "el asiento existe y el fichero no"))

    # --- §4.1 borrar / desregistrar ---------------------------------------
    claves_mapa = {e.logical_key for e in m.entradas}
    for k, a in sorted(led.asientos.items()):
        if k in claves_mapa:
            continue
        if a.origen == mp.ORIGEN_DESPACHO:
            ops.append(Operacion("desregistrar", k, a.carpeta, a.destino,
                                 motivo="sale del mapa; el fichero se queda"))
        else:
            ops.append(Operacion("borrar", k, a.carpeta, a.destino,
                                 motivo="en el ledger y no en el mapa"))

    # --- §4.1 sin_asignar -------------------------------------------------
    sin_asignar = tuple(
        f"{d} ({r.get('filename') or '?'}, lote {r.get('modified_at') or '?'})"
        for d, r in sorted(materializadas.items())
        if d not in asignados and d not in ecos)
    if sin_asignar:
        bloqueos.append(
            f"`sin_asignar` no vacio ({len(sin_asignar)} documentos): asignales carpeta "
            f"en el mapa. `apply` no corre mientras quede uno")

    # --- §4.1 ajenos ------------------------------------------------------
    propios = {f"{a.carpeta}/{a.destino}" for a in led.asientos.values()}
    propios |= {f"{o.carpeta}/{o.destino}" for o in ops}
    ajenos: list[str] = []
    for carpeta in CARPETAS_FASE:
        d = case_dir / "05_Procedimiento" / carpeta
        if not d.is_dir():
            continue
        for p in sorted(d.iterdir()):
            if not p.is_file() or _es_control(p.name):
                continue
            if f"{carpeta}/{p.name}" not in propios:
                ajenos.append(f"{carpeta}/{p.name}")

    return PlanProcesal(case_id, expediente_id, tuple(ops), sin_asignar,
                        tuple(avisos), tuple(ajenos), tuple(bloqueos))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_procedimiento_diff.py -q --tb=short`
Expected: PASS (4 tests)

- [ ] **Step 5: Write the remaining diff tests**

```python
def test_mismo_contenido_en_dos_procedimientos_se_copia_DOS_veces(tmp_path):
    """Spec §4.2: el reparto es por doc_id, NO por SHA. Deduplicar colapsaria dos
    aportaciones con numeracion, fecha y funcion distintas."""
    case_dir = _arbol(tmp_path)
    (case_dir / "05_Procedimiento/01_Monitorio - Demanda y documentos").mkdir(parents=True)
    (case_dir / "00_Input/05_CRM/01_Demanda/e.pdf").write_bytes(b"%PDF mismo")
    _cob(case_dir, [{"slug": "e", "rel_path": "05_CRM/01_Demanda/e.pdf",
                     "metodo": "pypdf", "estado": "ok", "sha256": "IGUAL"}])
    reg = RegistroOcurrencias.__new__(RegistroOcurrencias)
    reg.ocurrencias = {
        f"crm:540:{d}": {"source": "crm", "expediente_id": "540", "doc_id": d,
                         "revisiones": [{"estado": "materializada", "filename": "e.pdf",
                                         "modified_at": "x", "id_carpeta": "307",
                                         "path": "05_CRM/01_Demanda/e.pdf",
                                         "sha256": "IGUAL"}]}
        for d in ("10", "11")}
    m = mapa.MapaProcesal(version=1, expediente_crm="540", entradas=(
        mapa.EntradaMapa(carpeta="01_Monitorio - Demanda y documentos", origen="crm",
                         doc_id="10", orden="D-02", descripcion="mediacion",
                         logical_key="crm:540:10"),
        mapa.EntradaMapa(carpeta=CARP, origen="crm", doc_id="11", orden="D-02",
                         descripcion="mediacion", logical_key="crm:540:11")))
    p = diff.construir(case_dir, "CASO", "540", m=m, reg=reg, cob=None,
                       led=ledger.Ledger(asientos={}),
                       pull_state={"documents_total_crm": 2, "doc_ids": ["10", "11"]})
    assert p.bloqueos == ()
    assert len([o for o in p.operaciones if o.accion == "copiar"]) == 2


def test_eco_crm_saca_el_docid_de_sin_asignar_y_no_lo_copia(tmp_path):
    case_dir = _arbol(tmp_path)
    (case_dir / f"05_Procedimiento/{CARP}/DEMANDA.docx").write_bytes(b"propia")
    (case_dir / "00_Input/05_CRM/01_Demanda/e.pdf").write_bytes(b"x")
    reg = RegistroOcurrencias.__new__(RegistroOcurrencias)
    reg.ocurrencias = {"crm:540:99": {
        "source": "crm", "expediente_id": "540", "doc_id": "99",
        "revisiones": [{"estado": "materializada", "filename": "e.pdf", "modified_at": "x",
                        "id_carpeta": "307", "path": "05_CRM/01_Demanda/e.pdf",
                        "sha256": "S"}]}}
    m = mapa.MapaProcesal(version=1, expediente_crm="540", entradas=(
        mapa.EntradaMapa(carpeta=CARP, origen="despacho", fichero="DEMANDA.docx",
                         eco_crm="99", logical_key="despacho:DEMANDA.docx"),))
    p = diff.construir(case_dir, "CASO", "540", m=m, reg=reg, cob=None,
                       led=ledger.Ledger(asientos={}),
                       pull_state={"documents_total_crm": 1, "doc_ids": ["99"]})
    assert p.sin_asignar == ()
    assert [o.accion for o in p.operaciones] == ["registrar"]


def test_un_despacho_que_no_esta_en_su_carpeta_BLOQUEA(tmp_path):
    case_dir = _arbol(tmp_path)
    reg = RegistroOcurrencias.__new__(RegistroOcurrencias)
    reg.ocurrencias = {}
    m = mapa.MapaProcesal(version=1, expediente_crm="540", entradas=(
        mapa.EntradaMapa(carpeta=CARP, origen="despacho", fichero="NO_ESTA.docx",
                         logical_key="despacho:NO_ESTA.docx"),))
    p = diff.construir(case_dir, "CASO", "540", m=m, reg=reg, cob=None,
                       led=ledger.Ledger(asientos={}), pull_state=None)
    assert any("NO_ESTA.docx" in b for b in p.bloqueos)


def test_un_fichero_no_declarado_se_reporta_AJENO_y_no_se_toca(tmp_path):
    case_dir = _arbol(tmp_path)
    (case_dir / f"05_Procedimiento/{CARP}/suelto.pdf").write_bytes(b"x")
    reg = RegistroOcurrencias.__new__(RegistroOcurrencias)
    reg.ocurrencias = {}
    m = mapa.MapaProcesal(version=1, expediente_crm="540", entradas=())
    p = diff.construir(case_dir, "CASO", "540", m=m, reg=reg, cob=None,
                       led=ledger.Ledger(asientos={}), pull_state=None)
    assert f"{CARP}/suelto.pdf" in p.ajenos
    assert p.operaciones == ()


def test_los_ficheros_de_control_NO_cuentan_como_ajenos(tmp_path):
    case_dir = _arbol(tmp_path)
    (case_dir / f"05_Procedimiento/{CARP}/_index.md").write_text("x", encoding="utf-8")
    reg = RegistroOcurrencias.__new__(RegistroOcurrencias)
    reg.ocurrencias = {}
    m = mapa.MapaProcesal(version=1, expediente_crm="540", entradas=())
    p = diff.construir(case_dir, "CASO", "540", m=m, reg=reg, cob=None,
                       led=ledger.Ledger(asientos={}), pull_state=None)
    assert p.ajenos == ()


def test_un_asiento_que_sale_del_mapa_es_BORRAR_si_es_crm_y_DESREGISTRAR_si_es_despacho(tmp_path):
    case_dir = _arbol(tmp_path)
    led = ledger.Ledger(asientos={
        "crm:540:1": ledger.AsientoLedger(logical_key="crm:540:1", origen="crm",
                                          carpeta=CARP, destino="D-01_x.pdf"),
        "despacho:MIO.docx": ledger.AsientoLedger(
            logical_key="despacho:MIO.docx", origen="despacho", carpeta=CARP,
            destino="MIO.docx")})
    reg = RegistroOcurrencias.__new__(RegistroOcurrencias)
    reg.ocurrencias = {}
    m = mapa.MapaProcesal(version=1, expediente_crm="540", entradas=())
    p = diff.construir(case_dir, "CASO", "540", m=m, reg=reg, cob=None, led=led,
                       pull_state=None)
    acciones = {o.logical_key: o.accion for o in p.operaciones}
    assert acciones["crm:540:1"] == "borrar"
    assert acciones["despacho:MIO.docx"] == "desregistrar"


def _entrada_unica(tmp_path):
    """Arbol con un documento del CRM ya asignado. Devuelve `(case_dir, reg, m)`."""
    case_dir = _arbol(tmp_path)
    (case_dir / "00_Input/05_CRM/01_Demanda/e.pdf").write_bytes(b"%PDF-1.4 encargo")
    _cob(case_dir, [{"slug": "e", "rel_path": "05_CRM/01_Demanda/e.pdf",
                     "metodo": "pypdf", "estado": "ok", "sha256": "SHA_E"}])
    reg = RegistroOcurrencias.__new__(RegistroOcurrencias)
    reg.ocurrencias = {"crm:540:1": {
        "source": "crm", "expediente_id": "540", "doc_id": "1",
        "revisiones": [{"estado": "materializada", "filename": "e.pdf",
                        "modified_at": "2025-08-14T00:00:00+02:00", "id_carpeta": "307",
                        "path": "05_CRM/01_Demanda/e.pdf", "sha256": "SHA_E"}]}}
    m = mapa.MapaProcesal(version=1, expediente_crm="540", entradas=(
        mapa.EntradaMapa(carpeta=CARP, origen="crm", doc_id="1", orden="D-01",
                         descripcion="encargo_de_venta", logical_key="crm:540:1"),))
    return case_dir, reg, m


def test_destino_con_MIS_bytes_y_sin_asiento_es_ADOPTAR(tmp_path):
    """El residuo de un `apply` que murio antes de commitear el ledger. Emitir `copiar`
    aqui haria que el preflight lo llamara ajeno y el caso quedara bloqueado para
    siempre; emitir `adoptar` lo reconcilia sin escribir un byte."""
    case_dir, reg, m = _entrada_unica(tmp_path)
    (case_dir / f"05_Procedimiento/{CARP}/D-01_encargo_de_venta.pdf").write_bytes(
        (case_dir / "00_Input/05_CRM/01_Demanda/e.pdf").read_bytes())

    p = diff.construir(case_dir, "CASO", "540", m=m, reg=reg, cob=None,
                       led=ledger.Ledger(asientos={}),
                       pull_state={"documents_total_crm": 1, "doc_ids": ["1"]})
    assert p.bloqueos == ()
    assert [o.accion for o in p.operaciones] == ["adoptar"]
    assert p.ajenos == (), "lo adoptado no es ajeno"


def test_destino_con_OTROS_bytes_y_sin_asiento_BLOQUEA(tmp_path):
    """Mismo nombre canonico, contenido que esta corrida no produciria: es de otro."""
    case_dir, reg, m = _entrada_unica(tmp_path)
    (case_dir / f"05_Procedimiento/{CARP}/D-01_encargo_de_venta.pdf").write_bytes(
        b"LO QUE PUSO OTRO")

    p = diff.construir(case_dir, "CASO", "540", m=m, reg=reg, cob=None,
                       led=ledger.Ledger(asientos={}),
                       pull_state={"documents_total_crm": 1, "doc_ids": ["1"]})
    assert any("ajeno" in b for b in p.bloqueos)
    assert p.operaciones == ()


def test_un_diff_sin_cambios_es_VACIO(tmp_path):
    """Base de «cero escrituras en una re-ejecucion» (spec §4.1)."""
    case_dir = _arbol(tmp_path)
    reg = RegistroOcurrencias.__new__(RegistroOcurrencias)
    reg.ocurrencias = {}
    m = mapa.MapaProcesal(version=1, expediente_crm="540", entradas=())
    p = diff.construir(case_dir, "CASO", "540", m=m, reg=reg, cob=None,
                       led=ledger.Ledger(asientos={}), pull_state=None)
    assert p.vacio is True
```

- [ ] **Step 6: Run test to verify it passes**

Run: `python -m pytest tests/test_procedimiento_diff.py -q --tb=short`
Expected: PASS (13 tests)

- [ ] **Step 7: Commit**

```bash
git add core/procedimiento/diff.py tests/test_procedimiento_diff.py
git commit -m "vista procesal: puerta de integridad y diff de nueve categorias (spec 4.1, 5.1-5.9)"
```

---

## Task 6: la transacción y las puertas de propiedad

`apply` en el orden de §4.1, con las puertas 10-14 de §5. **«Está en el ledger» no basta para
destruir.**

**Files:**
- Create: `core/procedimiento/aplicar.py`
- Test: `tests/test_procedimiento_aplicar.py`

**Interfaces:**
- Consumes: `diff.PlanProcesal`, `diff.Operacion`, `ledger.Ledger`, `ledger.AsientoLedger`,
  `ledger.guardar`.
- Produces:
  - `aplicar.ResultadoProcesal` — dataclass frozen: `aplicadas: tuple` (de `diff.Operacion`;
    va sin parametrizar para no importar `diff` desde `aplicar`, que no lo necesita para
    nada mas), `abortos: tuple[str, ...]`, `ledger_escrito: bool`.
  - `aplicar.ejecutar(case_dir, p: PlanProcesal, led: Ledger, *, actor: str) -> ResultadoProcesal`

`ejecutar` **no lanza**: un problema de propiedad vuelve en `abortos` y con `ledger_escrito`
en `False`. Es deliberado — el CLI tiene que poder enumerar TODOS los problemas de una
corrida, y una excepcion solo cuenta el primero.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_procedimiento_aplicar.py
"""La transaccion de `apply` y las puertas de propiedad (spec §4.1, §5.10-§5.14)."""
import hashlib

import pytest

from core.procedimiento import aplicar, diff, ledger

CARP = "05_Otros escritos"


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _arbol(tmp_path):
    (tmp_path / "00_Input/05_CRM/99_Otros").mkdir(parents=True)
    (tmp_path / f"05_Procedimiento/{CARP}").mkdir(parents=True)
    return tmp_path


def test_un_diff_VACIO_no_escribe_NADA_ni_el_generado_del_ledger(tmp_path):
    case_dir = _arbol(tmp_path)
    p = diff.PlanProcesal("CASO", "540")
    r = aplicar.ejecutar(case_dir, p, ledger.Ledger(asientos={}), actor="test")
    assert r.aplicadas == ()
    assert r.ledger_escrito is False
    assert not ledger.ledger_path(case_dir).exists()


def test_copiar_escribe_el_destino_y_deja_su_asiento(tmp_path):
    case_dir = _arbol(tmp_path)
    cuerpo = b"%PDF-1.4 contenido"
    (case_dir / "00_Input/05_CRM/99_Otros/f.pdf").write_bytes(cuerpo)
    p = diff.PlanProcesal("CASO", "540", operaciones=(
        diff.Operacion("copiar", "crm:540:1", CARP, "00_decreto.pdf",
                       "00_Input/05_CRM/99_Otros/f.pdf", "raw"),))
    r = aplicar.ejecutar(case_dir, p, ledger.Ledger(asientos={}), actor="test")
    assert r.abortos == ()
    dst = case_dir / "05_Procedimiento" / CARP / "00_decreto.pdf"
    assert dst.read_bytes() == cuerpo
    led = ledger.cargar(case_dir)
    a = led.asientos["crm:540:1"]
    assert a.destination_sha256 == _sha(cuerpo)
    assert a.source_sha256 == _sha(cuerpo)
    assert a.source_kind == "raw"


def test_borrar_ABORTA_si_el_destino_lo_cambio_el_letrado_a_mano(tmp_path):
    """Puerta §5.12: «esta en el ledger» no basta. Si el SHA no cuadra, alguien lo
    sustituyo y destruirlo perderia su trabajo."""
    case_dir = _arbol(tmp_path)
    dst = case_dir / "05_Procedimiento" / CARP / "00_decreto.pdf"
    dst.write_bytes(b"LO QUE PUSO EL LETRADO")
    led = ledger.Ledger(asientos={"crm:540:1": ledger.AsientoLedger(
        logical_key="crm:540:1", origen="crm", carpeta=CARP, destino="00_decreto.pdf",
        destination_sha256=_sha(b"lo que escribio apply"))})
    p = diff.PlanProcesal("CASO", "540", operaciones=(
        diff.Operacion("borrar", "crm:540:1", CARP, "00_decreto.pdf"),))
    r = aplicar.ejecutar(case_dir, p, led, actor="test")
    assert any("sha" in a.lower() for a in r.abortos)
    assert dst.exists()                      # no se toco
    assert r.ledger_escrito is False         # y no se commiteo nada


def test_un_fichero_DESPACHO_nunca_entra_en_una_operacion_destructiva(tmp_path):
    """Puerta §5.14. `desregistrar` retira del inventario; el fichero se queda."""
    case_dir = _arbol(tmp_path)
    dst = case_dir / "05_Procedimiento" / CARP / "MIO.docx"
    dst.write_bytes(b"escrito del despacho")
    led = ledger.Ledger(asientos={"despacho:MIO.docx": ledger.AsientoLedger(
        logical_key="despacho:MIO.docx", origen="despacho", carpeta=CARP,
        destino="MIO.docx", destination_sha256=_sha(b"escrito del despacho"))})
    p = diff.PlanProcesal("CASO", "540", operaciones=(
        diff.Operacion("desregistrar", "despacho:MIO.docx", CARP, "MIO.docx"),))
    r = aplicar.ejecutar(case_dir, p, led, actor="test")
    assert r.abortos == ()
    assert dst.exists()
    assert "despacho:MIO.docx" not in ledger.cargar(case_dir).asientos


def test_un_destino_existente_NO_registrado_aborta_como_ajeno(tmp_path):
    """Puerta §5.13: pisar un fichero que no consta es destruir a ciegas."""
    case_dir = _arbol(tmp_path)
    (case_dir / "00_Input/05_CRM/99_Otros/f.pdf").write_bytes(b"nuevo")
    (case_dir / "05_Procedimiento" / CARP / "00_decreto.pdf").write_bytes(b"AJENO")
    p = diff.PlanProcesal("CASO", "540", operaciones=(
        diff.Operacion("copiar", "crm:540:1", CARP, "00_decreto.pdf",
                       "00_Input/05_CRM/99_Otros/f.pdf", "raw"),))
    r = aplicar.ejecutar(case_dir, p, ledger.Ledger(asientos={}), actor="test")
    assert any("ajeno" in a.lower() for a in r.abortos)
    assert (case_dir / "05_Procedimiento" / CARP / "00_decreto.pdf").read_bytes() == b"AJENO"


def test_un_plan_con_BLOQUEOS_no_ejecuta_nada(tmp_path):
    case_dir = _arbol(tmp_path)
    p = diff.PlanProcesal("CASO", "540",
                          operaciones=(diff.Operacion("copiar", "k", CARP, "x.pdf"),),
                          bloqueos=("algo pasa",))
    r = aplicar.ejecutar(case_dir, p, ledger.Ledger(asientos={}), actor="test")
    assert r.aplicadas == ()
    assert any("bloqueo" in a.lower() for a in r.abortos)


def test_reemplazar_cambia_los_bytes_Y_la_extension(tmp_path):
    """El `.doc` convertido a PDF: el destino cambia de extension y el anterior se
    retira. Sin esto quedarian dos ficheros y un ledger inconsistente (spec §2.4)."""
    case_dir = _arbol(tmp_path)
    viejo = case_dir / "05_Procedimiento" / CARP / "00_demanda.doc"
    viejo.write_bytes(b"doc binario")
    (case_dir / "00_Input/05_CRM/99_Otros/conv.pdf").write_bytes(b"%PDF convertido")
    led = ledger.Ledger(asientos={"crm:540:1": ledger.AsientoLedger(
        logical_key="crm:540:1", origen="crm", carpeta=CARP, destino="00_demanda.doc",
        destination_sha256=_sha(b"doc binario"), source_kind="raw")})
    p = diff.PlanProcesal("CASO", "540", operaciones=(
        diff.Operacion("reemplazar", "crm:540:1", CARP, "00_demanda.pdf",
                       "00_Input/05_CRM/99_Otros/conv.pdf", "converted"),))
    r = aplicar.ejecutar(case_dir, p, led, actor="test")
    assert r.abortos == ()
    assert not viejo.exists()
    assert (case_dir / "05_Procedimiento" / CARP / "00_demanda.pdf").read_bytes() == b"%PDF convertido"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_procedimiento_aplicar.py -q --tb=short`
Expected: FAIL con `ModuleNotFoundError: No module named 'core.procedimiento.aplicar'`

- [ ] **Step 3: Write the implementation**

```python
# core/procedimiento/aplicar.py
"""La transaccion de `apply` (spec §4.1) y las puertas de propiedad (§5.10-§5.14).

Orden, y el orden es el contrato: (1) preflight COMPLETO sobre todas las operaciones;
(2) copia a temporales en el MISMO volumen; (3) verificacion de tamano y SHA de lo
escrito; (4) reemplazos y movimientos atomicos; (5) borrados AL FINAL; (6) el ledger
como ULTIMO commit.

Si el preflight encuentra un problema, no se escribe nada: un aborto a mitad con el
ledger sin commitear deja el estado anterior intacto y `plan` reconcilia.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, replace
from pathlib import Path

from . import mapa as mp
from .ledger import AsientoLedger, Ledger, guardar

DESTRUCTIVAS = ("borrar", "reemplazar", "mover")


@dataclass(frozen=True)
class ResultadoProcesal:
    aplicadas: tuple = ()
    abortos: tuple[str, ...] = ()
    ledger_escrito: bool = False


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def _preflight(case_dir: Path, p, led: Ledger) -> list[str]:
    problemas: list[str] = []
    if p.bloqueos:
        problemas.append(
            f"el plan trae {len(p.bloqueos)} bloqueo(s): no se ejecuta nada. "
            f"Primero: {p.bloqueos[0]}")
        return problemas

    for o in p.operaciones:
        carpeta_abs = case_dir / "05_Procedimiento" / o.carpeta
        destino_abs = carpeta_abs / o.destino
        asiento = led.asientos.get(o.logical_key)

        # nada escribe fuera de las cinco carpetas
        try:
            destino_abs.resolve().relative_to(
                (case_dir / "05_Procedimiento").resolve())
        except ValueError:
            problemas.append(f"{o.logical_key}: el destino escapa de 05_Procedimiento")
            continue

        if o.accion in DESTRUCTIVAS:
            if asiento is None:
                problemas.append(
                    f"{o.logical_key}: {o.accion} sin asiento en el ledger")
                continue
            if asiento.origen == mp.ORIGEN_DESPACHO:
                problemas.append(
                    f"{o.logical_key}: es `origen: despacho` y {o.accion} es destructiva")
                continue
            anterior = carpeta_abs.parent / asiento.carpeta / asiento.destino
            if not anterior.exists():
                problemas.append(f"{o.logical_key}: el destino anterior no existe: "
                                 f"{asiento.carpeta}/{asiento.destino}")
                continue
            if anterior.is_symlink() or not anterior.is_file():
                problemas.append(f"{o.logical_key}: el destino anterior no es un fichero "
                                 f"regular")
                continue
            if asiento.destination_sha256 and _sha(anterior) != asiento.destination_sha256:
                problemas.append(
                    f"{o.logical_key}: el sha del destino no coincide con el del ledger "
                    f"— alguien lo sustituyo a mano; se aborta antes de tocarlo")
                continue

        if o.accion == "adoptar":
            if asiento is not None:
                problemas.append(
                    f"{o.logical_key}: adoptar sobre una clave que YA tiene asiento")
                continue
            if destino_abs.is_symlink() or not destino_abs.is_file():
                problemas.append(
                    f"{o.logical_key}: adoptar exige un fichero regular en el destino")
                continue
            src = case_dir / o.source_rel
            if not src.is_file() or _sha(destino_abs) != _sha(src):
                problemas.append(
                    f"{o.logical_key}: adoptar exige que el destino tenga los MISMOS bytes "
                    f"que el origen, y ya no los tiene: algo cambio entre `plan` y `apply`")
                continue

        if o.accion == "copiar":
            if destino_abs.exists() and asiento is None:
                problemas.append(
                    f"{o.logical_key}: el destino {o.carpeta}/{o.destino} ya existe y no "
                    f"esta registrado: es ajeno y no se pisa")
                continue
            src = case_dir / o.source_rel
            if not src.is_file():
                problemas.append(f"{o.logical_key}: el origen no existe: {o.source_rel}")

        if o.accion in ("reemplazar", "mover"):
            src = case_dir / o.source_rel
            if not src.is_file():
                problemas.append(f"{o.logical_key}: el origen no existe: {o.source_rel}")

    return problemas


def ejecutar(case_dir, p, led: Ledger, *, actor: str) -> ResultadoProcesal:
    case_dir = Path(case_dir)

    problemas = _preflight(case_dir, p, led)
    if problemas:
        return ResultadoProcesal(abortos=tuple(problemas))
    if not p.operaciones:
        return ResultadoProcesal()          # cero escrituras, ni el `generado`

    asientos = dict(led.asientos)
    aplicadas: list = []
    borrar_al_final: list[tuple[str, Path]] = []

    for o in p.operaciones:
        carpeta_abs = case_dir / "05_Procedimiento" / o.carpeta
        carpeta_abs.mkdir(parents=True, exist_ok=True)
        destino_abs = carpeta_abs / o.destino
        asiento = asientos.get(o.logical_key)

        if o.accion == "desregistrar":
            asientos.pop(o.logical_key, None)
            aplicadas.append(o)
            continue

        if o.accion == "borrar":
            borrar_al_final.append((o.logical_key,
                                    carpeta_abs.parent / asiento.carpeta / asiento.destino))
            aplicadas.append(o)
            continue

        if o.accion == "adoptar":
            # Cero escrituras sobre el fichero: ya tiene los bytes correctos, verificados
            # en el preflight. Lo unico que falta es el asiento que la corrida anterior
            # no llego a commitear.
            sha_dst = _sha(destino_abs)
            asientos[o.logical_key] = AsientoLedger(
                logical_key=o.logical_key, origen=mp.ORIGEN_CRM, carpeta=o.carpeta,
                destino=o.destino,
                raw_path=o.source_rel if o.source_kind == "raw" else "",
                raw_sha256=sha_dst if o.source_kind == "raw" else "",
                source_kind=o.source_kind, source_path=o.source_rel,
                source_sha256=sha_dst, destination_sha256=sha_dst)
            aplicadas.append(o)
            continue

        if o.accion == "registrar":
            sha_dst = _sha(destino_abs)
            asientos[o.logical_key] = AsientoLedger(
                logical_key=o.logical_key, origen=mp.ORIGEN_DESPACHO, carpeta=o.carpeta,
                destino=o.destino, destination_sha256=sha_dst)
            aplicadas.append(o)
            continue

        # copiar / reemplazar / mover: temporal en el MISMO directorio + os.replace
        src = case_dir / o.source_rel
        tmp = carpeta_abs / f".{o.destino}.{os.getpid()}.tmp"
        tmp.write_bytes(src.read_bytes())
        if tmp.stat().st_size != src.stat().st_size:
            tmp.unlink(missing_ok=True)
            return ResultadoProcesal(abortos=(
                f"{o.logical_key}: el tamano de lo escrito no coincide con el origen",))
        sha_dst = _sha(tmp)
        if sha_dst != _sha(src):
            tmp.unlink(missing_ok=True)
            return ResultadoProcesal(abortos=(
                f"{o.logical_key}: el sha de lo escrito no coincide con el origen",))
        os.replace(tmp, destino_abs)

        # el anterior se retira cuando cambia de nombre o de carpeta
        if asiento is not None:
            anterior = carpeta_abs.parent / asiento.carpeta / asiento.destino
            if anterior.resolve() != destino_abs.resolve() and anterior.is_file():
                anterior.unlink()

        asientos[o.logical_key] = AsientoLedger(
            logical_key=o.logical_key, origen=mp.ORIGEN_CRM, carpeta=o.carpeta,
            destino=o.destino, raw_path=o.source_rel if o.source_kind == "raw" else "",
            raw_sha256=sha_dst if o.source_kind == "raw" else "",
            source_kind=o.source_kind, source_path=o.source_rel,
            source_sha256=sha_dst, destination_sha256=sha_dst)
        aplicadas.append(o)

    for clave, ruta in borrar_al_final:      # (5) borrados AL FINAL
        if ruta.is_file():
            ruta.unlink()
        asientos.pop(clave, None)

    guardar(case_dir, Ledger(asientos=asientos))     # (6) ULTIMO commit
    return ResultadoProcesal(tuple(aplicadas), (), True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_procedimiento_aplicar.py -q --tb=short`
Expected: PASS (7 tests)

- [ ] **Step 5: Write the adoption tests**

```python
def test_adoptar_registra_SIN_reescribir_el_fichero(tmp_path):
    """El residuo de un `apply` interrumpido: los bytes ya están bien y solo falta el
    asiento. Se comprueba que el fichero NO se reescribe comparando su mtime_ns."""
    case_dir = _arbol(tmp_path)
    cuerpo = b"%PDF-1.4 ya copiado"
    (case_dir / "00_Input/05_CRM/99_Otros/f.pdf").write_bytes(cuerpo)
    dst = case_dir / "05_Procedimiento" / CARP / "00_decreto.pdf"
    dst.write_bytes(cuerpo)
    mtime = dst.stat().st_mtime_ns

    p = diff.PlanProcesal("CASO", "540", operaciones=(
        diff.Operacion("adoptar", "crm:540:1", CARP, "00_decreto.pdf",
                       "00_Input/05_CRM/99_Otros/f.pdf", "raw"),))
    r = aplicar.ejecutar(case_dir, p, ledger.Ledger(asientos={}), actor="test")
    assert r.abortos == ()
    assert dst.stat().st_mtime_ns == mtime, "adoptar reescribio el fichero"
    a = ledger.cargar(case_dir).asientos["crm:540:1"]
    assert a.destination_sha256 == _sha(cuerpo)


def test_adoptar_ABORTA_si_los_bytes_cambiaron_entre_plan_y_apply(tmp_path):
    """El plan vio identidad de contenido; si deja de haberla antes de aplicar, adoptar
    convertiria un fichero ajeno en propio con una firma que no le corresponde."""
    case_dir = _arbol(tmp_path)
    (case_dir / "00_Input/05_CRM/99_Otros/f.pdf").write_bytes(b"origen")
    (case_dir / "05_Procedimiento" / CARP / "00_decreto.pdf").write_bytes(b"OTRA COSA")
    p = diff.PlanProcesal("CASO", "540", operaciones=(
        diff.Operacion("adoptar", "crm:540:1", CARP, "00_decreto.pdf",
                       "00_Input/05_CRM/99_Otros/f.pdf", "raw"),))
    r = aplicar.ejecutar(case_dir, p, ledger.Ledger(asientos={}), actor="test")
    assert any("MISMOS bytes" in a for a in r.abortos)
    assert r.ledger_escrito is False
```

- [ ] **Step 6: Run test to verify it passes**

Run: `python -m pytest tests/test_procedimiento_aplicar.py -q --tb=short`
Expected: PASS (9 tests)

- [ ] **Step 7: Write the idempotence test**

```python
def test_re_ejecutar_sin_cambios_no_escribe_nada(tmp_path):
    """Spec §4.1: idempotencia. El segundo `apply` sobre el mismo estado ve un diff
    vacio y no toca el ledger — ni su campo `generado`."""
    case_dir = _arbol(tmp_path)
    (case_dir / "00_Input/05_CRM/99_Otros/f.pdf").write_bytes(b"%PDF x")
    p = diff.PlanProcesal("CASO", "540", operaciones=(
        diff.Operacion("copiar", "crm:540:1", CARP, "00_d.pdf",
                       "00_Input/05_CRM/99_Otros/f.pdf", "raw"),))
    aplicar.ejecutar(case_dir, p, ledger.Ledger(asientos={}), actor="t")
    antes = ledger.ledger_path(case_dir).read_text(encoding="utf-8")

    r2 = aplicar.ejecutar(case_dir, diff.PlanProcesal("CASO", "540"),
                          ledger.cargar(case_dir), actor="t")
    assert r2.ledger_escrito is False
    assert ledger.ledger_path(case_dir).read_text(encoding="utf-8") == antes
```

- [ ] **Step 8: Run test to verify it passes**

Run: `python -m pytest tests/test_procedimiento_aplicar.py -q --tb=short`
Expected: PASS (10 tests)

- [ ] **Step 9: Commit**

```bash
git add core/procedimiento/aplicar.py tests/test_procedimiento_aplicar.py
git commit -m "vista procesal: transaccion de apply y puertas de propiedad (spec 4.1, 5.10-5.14)"
```

---

## Task 7: el reconciliador del índice del letrado

`<carpeta>/_index.md`. Gestiona **solo** las filas cuya columna `Fuentes` sea `CRM:<doc_id>`,
preserva intactas las del despacho y las manuales, y **no toca `## Navegación` de `_caso.md`**.

**Files:**
- Create: `core/procedimiento/indice.py`
- Test: `tests/test_procedimiento_indice.py`

**Interfaces:**
- Consumes: `ledger.AsientoLedger`, `carpetas.CARPETAS_FASE`.
- Produces:
  - `indice.MARCA_INICIO: str`, `indice.MARCA_FIN: str`
  - `indice.reconciliar(case_dir, carpeta: str, asientos: list[AsientoLedger], *, avisos: dict[str, str]) -> Path`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_procedimiento_indice.py
"""Reconciliador de `<carpeta>/_index.md` (spec §2.3)."""
from core.procedimiento import indice, ledger

CARP = "05_Otros escritos"


def _asiento(destino, key):
    return ledger.AsientoLedger(logical_key=key, origen="crm", carpeta=CARP,
                                destino=destino, destination_sha256="d" * 64)


def test_crea_el_indice_con_su_bloque_delimitado(tmp_path):
    (tmp_path / "05_Procedimiento" / CARP).mkdir(parents=True)
    p = indice.reconciliar(tmp_path, CARP,
                           [_asiento("00_decreto.pdf", "crm:540:1")], avisos={})
    t = p.read_text(encoding="utf-8")
    assert indice.MARCA_INICIO in t and indice.MARCA_FIN in t
    assert "00_decreto.pdf" in t
    assert "CRM:1" in t


def test_PRESERVA_las_filas_del_despacho_y_las_manuales(tmp_path):
    """La razon de ser del reconciliador propio: `registrar()` del helper solo anade
    filas por nombre, y aqui hay que mover y borrar sin tocar lo ajeno."""
    d = tmp_path / "05_Procedimiento" / CARP
    d.mkdir(parents=True)
    (d / "_index.md").write_text(
        "# 05_Otros escritos — Índice de work-product\n\n"
        "| Fichero | Tipo | Perspectiva | Fecha | Fuentes | Estado |\n"
        "|---|---|---|---|---|---|\n"
        "| MINUTA.docx | minuta | actora | 2026-09-09 | despacho | borrador |\n"
        "| nota_a_mano.md | nota | | 2026-09-01 | a mano | vigente |\n",
        encoding="utf-8")
    p = indice.reconciliar(tmp_path, CARP,
                           [_asiento("00_decreto.pdf", "crm:540:1")], avisos={})
    t = p.read_text(encoding="utf-8")
    assert "MINUTA.docx" in t
    assert "nota_a_mano.md" in t
    assert "00_decreto.pdf" in t


def test_una_fila_CRM_que_desaparece_del_ledger_se_RETIRA(tmp_path):
    d = tmp_path / "05_Procedimiento" / CARP
    d.mkdir(parents=True)
    indice.reconciliar(tmp_path, CARP, [
        _asiento("00_a.pdf", "crm:540:1"), _asiento("01_b.pdf", "crm:540:2")], avisos={})
    p = indice.reconciliar(tmp_path, CARP, [_asiento("00_a.pdf", "crm:540:1")], avisos={})
    t = p.read_text(encoding="utf-8")
    assert "00_a.pdf" in t
    assert "01_b.pdf" not in t


def test_reconciliar_dos_veces_da_EL_MISMO_fichero(tmp_path):
    """Sin esto, cada `apply` ensuciaria el diff de git del expediente."""
    d = tmp_path / "05_Procedimiento" / CARP
    d.mkdir(parents=True)
    a = [_asiento("00_a.pdf", "crm:540:1")]
    p1 = indice.reconciliar(tmp_path, CARP, a, avisos={}).read_text(encoding="utf-8")
    p2 = indice.reconciliar(tmp_path, CARP, a, avisos={}).read_text(encoding="utf-8")
    assert p1 == p2


def test_el_aviso_de_calidad_viaja_a_la_columna_Estado(tmp_path):
    (tmp_path / "05_Procedimiento" / CARP).mkdir(parents=True)
    p = indice.reconciliar(tmp_path, CARP, [_asiento("00_a.pdf", "crm:540:1")],
                           avisos={"crm:540:1": "calidad declarada `low`"})
    assert "low" in p.read_text(encoding="utf-8")


def test_NO_toca_el_caso_md(tmp_path):
    (tmp_path / "05_Procedimiento" / CARP).mkdir(parents=True)
    (tmp_path / "00_Input").mkdir(parents=True)
    caso = tmp_path / "00_Input" / "_caso.md"
    caso.write_text("---\ncase_id: X\n---\n\n## Navegación\n\n- nada\n", encoding="utf-8")
    antes = caso.read_text(encoding="utf-8")
    indice.reconciliar(tmp_path, CARP, [_asiento("00_a.pdf", "crm:540:1")], avisos={})
    assert caso.read_text(encoding="utf-8") == antes
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_procedimiento_indice.py -q --tb=short`
Expected: FAIL con `ModuleNotFoundError: No module named 'core.procedimiento.indice'`

- [ ] **Step 3: Write the implementation**

```python
# core/procedimiento/indice.py
"""Reconciliador de `<carpeta>/_index.md` (spec §2.3).

Gestiona SOLO las filas cuya columna `Fuentes` empieza por `CRM:`. Las del despacho y
las manuales se preservan intactas, y `## Navegacion` de `_caso.md` no se toca.

El bloque generado va delimitado por marcadores para que el manual y el generado sean
distinguibles a ojo y por herramienta.
"""
from __future__ import annotations

import os
from pathlib import Path

from .ledger import AsientoLedger

INDICE_FILENAME = "_index.md"
MARCA_INICIO = "<!-- vista-procesal: INICIO — bloque generado, no editar a mano -->"
MARCA_FIN = "<!-- vista-procesal: FIN -->"

_CABECERA = ("| Fichero | Tipo | Perspectiva | Fecha | Fuentes | Estado |\n"
             "|---|---|---|---|---|---|\n")


def indice_path(case_dir: Path, carpeta: str) -> Path:
    return Path(case_dir) / "05_Procedimiento" / carpeta / INDICE_FILENAME


def _es_fila_crm(linea: str) -> bool:
    if not linea.strip().startswith("|"):
        return False
    celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
    return len(celdas) >= 5 and celdas[4].upper().startswith("CRM:")


def reconciliar(case_dir, carpeta: str, asientos: list[AsientoLedger], *,
                avisos: dict[str, str]) -> Path:
    """Reescribe el bloque generado del indice y devuelve su ruta.

    Idempotente: con los mismos asientos produce byte a byte el mismo fichero.
    """
    p = indice_path(case_dir, carpeta)
    p.parent.mkdir(parents=True, exist_ok=True)

    previo = p.read_text(encoding="utf-8") if p.is_file() else ""
    # se conserva TODO lo previo menos el bloque generado y las filas CRM sueltas
    conservado: list[str] = []
    dentro = False
    for linea in previo.splitlines():
        if linea.strip() == MARCA_INICIO:
            dentro = True
            continue
        if linea.strip() == MARCA_FIN:
            dentro = False
            continue
        if dentro or _es_fila_crm(linea):
            continue
        conservado.append(linea)

    cuerpo = "\n".join(conservado).rstrip()
    if not cuerpo:
        cuerpo = (f"# 05_Procedimiento/{carpeta} — Índice de work-product\n\n"
                  "> Las filas `CRM:` las reconcilia la vista procesal. Las demás son\n"
                  "> del despacho o manuales y no se tocan.\n\n" + _CABECERA.rstrip())

    filas = []
    for a in sorted(asientos, key=lambda x: x.destino):
        doc_id = a.logical_key.rsplit(":", 1)[-1]
        fecha = a.destino[:10] if a.destino[:4].isdigit() else ""
        estado = avisos.get(a.logical_key, "copiado")
        filas.append(f"| {a.destino} | procesal | | {fecha} | CRM:{doc_id} | {estado} |")

    nuevo = (f"{cuerpo}\n{MARCA_INICIO}\n" + "\n".join(filas) +
             ("\n" if filas else "") + f"{MARCA_FIN}\n")

    tmp = p.with_name(f".{p.name}.{os.getpid()}.tmp")
    tmp.write_text(nuevo, encoding="utf-8")
    os.replace(tmp, p)
    return p
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_procedimiento_indice.py -q --tb=short`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add core/procedimiento/indice.py tests/test_procedimiento_indice.py
git commit -m "vista procesal: reconciliador del indice, preserva lo del letrado"
```

---

## Task 8: la fachada y el CLI

`plan` y `apply` cableados, y el CLI que los expone. Aquí se junta todo y aparece el mutex.

**Files:**
- Modify: `core/procedimiento/__init__.py`
- Create: `scripts/procedimiento.py`
- Test: `tests/test_procedimiento_fachada.py`

**Interfaces:**
- Consumes: todo lo anterior, `core.ocurrencias_crm.RegistroOcurrencias`,
  `core.case_manager.read_pull_state`, `core.casos.case_locator.buscar`,
  `scripts._mutex_cli.sostener`.
- Produces:
  - `core.procedimiento.plan(case_id: str, expediente_id: str) -> diff.PlanProcesal`
  - `core.procedimiento.apply(case_id: str, expediente_id: str, *, actor: str | None = None) -> aplicar.ResultadoProcesal`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_procedimiento_fachada.py
"""La fachada `plan`/`apply` sobre un arbol sintetico completo."""
import json

import pytest

import core.procedimiento as proc

CARP = "05_Otros escritos"


@pytest.fixture()
def caso(tmp_path, monkeypatch):
    """Arbol sintetico con un documento del CRM listo para entrar en la vista."""
    case_dir = tmp_path / "BaRS10 - X (W-02VEKE) - Negativa arras"
    for sub in ("00_Input/05_CRM/99_Otros", f"05_Procedimiento/{CARP}",
                "01_Procesado/02_Sala de máquina"):
        (case_dir / sub).mkdir(parents=True)
    (case_dir / "00_Input/05_CRM/99_Otros/decreto.pdf").write_bytes(b"%PDF-1.4 decreto")
    sha = __import__("hashlib").sha256(b"%PDF-1.4 decreto").hexdigest()
    (case_dir / "01_Procesado/02_Sala de máquina/_cobertura.json").write_text(
        json.dumps([{"slug": "decreto", "rel_path": "05_CRM/99_Otros/decreto.pdf",
                     "metodo": "pypdf", "estado": "ok", "sha256": sha}]),
        encoding="utf-8")
    (case_dir / "00_Input/_ocurrencias_crm.json").write_text(json.dumps({
        "version": 1, "generado": "2026-09-09T00:00:00",
        "ocurrencias": {"crm:540:1": {
            "source": "crm", "expediente_id": "540", "doc_id": "1",
            "revisiones": [{"estado": "materializada", "filename": "decreto.pdf",
                            "modified_at": "2026-01-01T00:00:00+01:00",
                            "id_carpeta": "306", "path": "05_CRM/99_Otros/decreto.pdf",
                            "sha256": sha, "registrada_en": "2026-09-09T00:00:00"}]}}}),
        encoding="utf-8")
    (case_dir / f"05_Procedimiento/_mapa_procesal.yaml").write_text(
        "version: 1\nexpediente_crm: '540'\ncarpetas:\n"
        f'  "{CARP}":\n'
        "    - {origen: crm, doc_id: '1', orden: '00', descripcion: decreto_admision}\n",
        encoding="utf-8")

    monkeypatch.setattr("core.casos.case_locator.buscar", lambda _c: case_dir)
    monkeypatch.setattr("core.case_manager.read_pull_state",
                        lambda _c, _e: {"documents_total_crm": 1, "doc_ids": ["1"]})
    return case_dir


def test_plan_no_escribe_nada(caso):
    antes = sorted(p.name for p in (caso / "05_Procedimiento").rglob("*"))
    p = proc.plan("CASO", "540")
    assert p.bloqueos == ()
    assert [o.accion for o in p.operaciones] == ["copiar"]
    assert sorted(q.name for q in (caso / "05_Procedimiento").rglob("*")) == antes


def test_apply_copia_escribe_ledger_e_indice(caso):
    r = proc.apply("CASO", "540", actor="test")
    assert r.abortos == ()
    assert r.ledger_escrito is True
    assert (caso / "05_Procedimiento" / CARP / "00_decreto_admision.pdf").is_file()
    assert (caso / "05_Procedimiento" / "_MANIFIESTO_PROCESAL.json").is_file()
    assert (caso / "05_Procedimiento" / CARP / "_index.md").is_file()


def test_apply_dos_veces_es_idempotente(caso):
    proc.apply("CASO", "540", actor="test")
    led1 = (caso / "05_Procedimiento" / "_MANIFIESTO_PROCESAL.json").read_text(encoding="utf-8")
    r2 = proc.apply("CASO", "540", actor="test")
    assert r2.aplicadas == ()
    assert r2.ledger_escrito is False
    assert (caso / "05_Procedimiento" / "_MANIFIESTO_PROCESAL.json").read_text(
        encoding="utf-8") == led1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_procedimiento_fachada.py -q --tb=short`
Expected: FAIL con `AttributeError: module 'core.procedimiento' has no attribute 'plan'`

- [ ] **Step 3: Write the facade**

```python
# core/procedimiento/__init__.py
"""Vista procesal de `05_Procedimiento` (spec 2026-07-27, pieza 4).

`plan` no escribe nada. `apply` es transaccional y deja el ledger como ultimo commit.
Ninguno toca `00_Input/05_CRM`.
"""
from __future__ import annotations

from pathlib import Path

from . import aplicar, artefacto, carpetas, diff, indice, ledger, mapa

__all__ = ["plan", "apply", "aplicar", "artefacto", "carpetas", "diff", "indice",
           "ledger", "mapa"]


def _case_dir(case_id: str) -> Path:
    from core.casos.case_locator import buscar
    d = buscar(case_id)
    if d is None:
        raise FileNotFoundError(f"caso no encontrado: {case_id!r}")
    return d


def plan(case_id: str, expediente_id: str) -> diff.PlanProcesal:
    """Diff de la vista. NO escribe nada."""
    from core.case_manager import read_pull_state
    from core.ocurrencias_crm import RegistroOcurrencias

    case_dir = _case_dir(case_id)
    m = mapa.cargar(case_dir)
    reg = RegistroOcurrencias(case_id)
    reg.load()
    return diff.construir(case_dir, case_id, str(expediente_id), m=m, reg=reg,
                          cob=artefacto.cargar_cobertura(case_dir),
                          led=ledger.cargar(case_dir),
                          pull_state=read_pull_state(case_id, expediente_id))


def apply(case_id: str, expediente_id: str, *,
          actor: str | None = None) -> aplicar.ResultadoProcesal:
    """Aplica el diff y reconcilia los indices. Corre bajo el mutex del caso."""
    case_dir = _case_dir(case_id)
    p = plan(case_id, expediente_id)
    led = ledger.cargar(case_dir)
    r = aplicar.ejecutar(case_dir, p, led, actor=actor or "desconocido")
    if r.ledger_escrito:
        final = ledger.cargar(case_dir)
        avisos = {}
        for a in p.avisos:
            clave, _, texto = a.partition(": ")
            if clave.startswith(("crm:", "despacho:")):
                avisos[clave] = texto
        por_carpeta: dict[str, list] = {}
        for asiento in final.asientos.values():
            if asiento.origen == mapa.ORIGEN_CRM:
                por_carpeta.setdefault(asiento.carpeta, []).append(asiento)
        for carpeta in carpetas.CARPETAS_FASE:
            if (case_dir / "05_Procedimiento" / carpeta).is_dir():
                indice.reconciliar(case_dir, carpeta, por_carpeta.get(carpeta, []),
                                   avisos=avisos)
    return r
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_procedimiento_fachada.py -q --tb=short`
Expected: PASS (3 tests)

- [ ] **Step 5: Write the interrupted-run reconciliation test**

El spec §6 lo exige literalmente: «fallo a mitad de `apply` y reconciliación por `plan`». Es
además lo que sostiene que este plan pueda dejar el journal fuera de alcance: si `plan` no
reconciliara, la omisión no sería una decisión sino un agujero.

```python
def test_un_apply_INTERRUMPIDO_lo_reconcilia_el_siguiente_plan(caso):
    """Se simula la muerte de la corrida donde de verdad duele: el fichero copiado y el
    ledger sin commitear. La siguiente pasada NO debe volver a copiar ni llamar ajeno a
    su propia copia: debe adoptarla y quedar idéntica a una corrida limpia."""
    import shutil

    # (1) corrida limpia, para tener el estado de referencia
    proc.apply("CASO", "540", actor="test")
    ledger_bueno = (caso / "05_Procedimiento" / "_MANIFIESTO_PROCESAL.json").read_text(
        encoding="utf-8")
    copia = (caso / "05_Procedimiento" / CARP / "00_decreto_admision.pdf").read_bytes()

    # (2) se rebobina AL ESTADO DE UNA CORRIDA MUERTA: el fichero está, el ledger no
    (caso / "05_Procedimiento" / "_MANIFIESTO_PROCESAL.json").unlink()
    shutil.rmtree(caso / "05_Procedimiento" / CARP / "_index.md", ignore_errors=True)
    (caso / "05_Procedimiento" / CARP / "_index.md").unlink(missing_ok=True)
    assert (caso / "05_Procedimiento" / CARP / "00_decreto_admision.pdf").is_file()

    # (3) `plan` lo ve como lo que es, no como un fichero ajeno
    p = proc.plan("CASO", "540")
    assert p.bloqueos == (), f"plan bloqueó tras una corrida interrumpida: {p.bloqueos}"
    assert [o.accion for o in p.operaciones] == ["adoptar"]

    # (4) y `apply` converge al MISMO estado, sin reescribir los bytes
    r = proc.apply("CASO", "540", actor="test")
    assert r.abortos == ()
    assert (caso / "05_Procedimiento" / CARP / "00_decreto_admision.pdf").read_bytes() == copia
    import json
    assert (json.loads((caso / "05_Procedimiento" / "_MANIFIESTO_PROCESAL.json")
                       .read_text(encoding="utf-8"))["asientos"]
            == json.loads(ledger_bueno)["asientos"]), (
        "la reconciliación no converge al ledger de una corrida limpia")
```

- [ ] **Step 6: Run test to verify it passes**

Run: `python -m pytest tests/test_procedimiento_fachada.py -q --tb=short`
Expected: PASS (4 tests)

- [ ] **Step 7: Write the CLI**

```python
# scripts/procedimiento.py
"""CLI de la vista procesal de `05_Procedimiento`.

    python -m scripts.procedimiento plan  --case "<case_id|W-code>" --expediente 540
    python -m scripts.procedimiento apply --case "<case_id|W-code>" --expediente 540

`plan` no escribe nada. `apply` corre bajo el mutex del caso (MEJORAS #126): el mutex lo
pide quien escribe, y esta pieza escribe en `05_Procedimiento`.
"""
from __future__ import annotations

import sys

import typer

from core import procedimiento as proc
from core.casos.case_locator import resolve_ref
from scripts._mutex_cli import CasoOcupado, MutexPerdidoEnCli, sostener, w_code_de

app = typer.Typer(add_completion=False, help=__doc__)


def _imprimir(p) -> None:
    typer.echo(f"expediente {p.expediente_id} — {len(p.operaciones)} operacion(es)")
    for o in p.operaciones:
        typer.echo(f"  {o.accion:<13} {o.carpeta}/{o.destino}"
                   + (f"   ({o.motivo})" if o.motivo else ""))
    for etiqueta, items in (("sin_asignar", p.sin_asignar), ("avisos", p.avisos),
                            ("ajenos", p.ajenos), ("BLOQUEOS", p.bloqueos)):
        if items:
            typer.echo(f"\n{etiqueta} ({len(items)}):")
            for x in items:
                typer.echo(f"  - {x}")


@app.command()
def plan(case: str = typer.Option(..., "--case"),
         expediente: str = typer.Option(..., "--expediente")) -> None:
    """Diff de la vista. No escribe nada."""
    case_id = resolve_ref(case)
    p = proc.plan(case_id, expediente)
    _imprimir(p)
    raise typer.Exit(code=1 if p.bloqueos else 0)


@app.command()
def apply(case: str = typer.Option(..., "--case"),
          expediente: str = typer.Option(..., "--expediente"),
          actor: str = typer.Option("CLI", "--actor")) -> None:
    """Aplica el diff. Corre bajo el mutex del caso."""
    case_id = resolve_ref(case)
    w = w_code_de(case_id)
    try:
        with sostener(w, avisar=lambda m: typer.echo(m, err=True),
                      que="la vista procesal"):
            r = proc.apply(case_id, expediente, actor=actor)
    except CasoOcupado as exc:
        typer.echo(f"[ERROR] {exc}", err=True)
        raise typer.Exit(code=2) from exc
    except MutexPerdidoEnCli as exc:
        typer.echo(f"[ERROR] {exc} Artefactos: 05_Procedimiento de este caso.", err=True)
        raise typer.Exit(code=2) from exc

    for o in r.aplicadas:
        typer.echo(f"  {o.accion:<13} {o.carpeta}/{o.destino}")
    if r.abortos:
        typer.echo(f"\nABORTADO ({len(r.abortos)}):", err=True)
        for a in r.abortos:
            typer.echo(f"  - {a}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"\n{len(r.aplicadas)} operacion(es) aplicadas; "
               f"ledger {'escrito' if r.ledger_escrito else 'sin cambios'}")


if __name__ == "__main__":
    app()
```

- [ ] **Step 8: Run the CLI smoke test**

Run: `python -m scripts.procedimiento --help`
Expected: la ayuda con los subcomandos `plan` y `apply`, exit 0

- [ ] **Step 9: Run the full suite**

Run: `python -m pytest -q --tb=no -n auto`
Expected: PASS. El conteo debe subir en el número de tests nuevos y **no** debe aparecer
ningún `skip` ni `xfail` nuevo.

- [ ] **Step 10: Commit**

```bash
git add core/procedimiento/__init__.py scripts/procedimiento.py \
        tests/test_procedimiento_fachada.py
git commit -m "vista procesal: fachada plan/apply y CLI bajo el mutex del caso"
```

---

## Task 9: el fixture de regresión, sobre un caso real

El spec §11.3 exige el fixture del piloto W-02MA0R con sus 70 `doc_id`. **Este plan usa W-02VEKE en
su lugar**, y la razón es medible: el piloto **no tiene sala de máquina corrida** (spec §2.4: «en el
piloto no se puede correr todavía»), así que no ejercita el selector por clase documental, que es la
mitad de la pieza. W-02VEKE tiene 76 documentos del CRM, sala de máquina corrida el 2026-09-08 (340
documentos, `metodo` en `pypdf`/`ocr`/`ofimatica`/`nativo`/`sin_soporte`) y un `empty` real.

**Files:**
- Create: `tests/fixtures/procedimiento/w02veke_ocurrencias.json`
- Create: `tests/fixtures/procedimiento/w02veke_cobertura.json`
- Create: `tests/test_procedimiento_regresion.py`

**Interfaces:**
- Consumes: todo lo anterior.
- Produces: nada que consuman otras tareas.

- [ ] **Step 1: Generar los dos fixtures anonimizados desde el caso real**

Los fixtures se generan **una vez** con este script, que se ejecuta a mano y no se commitea.
Sustituye todo nombre de persona por `<PARTICULAR>` y recorta a los campos que la pieza lee.

```python
"""Genera los dos fixtures anonimizados. Se ejecuta A MANO y NO se commitea.

CERO literales de datos personales en este fichero, y por tanto ninguno en el plan que
lo contiene: la ruta del caso la resuelve el localizador desde su W-code, y los terminos
a redactar salen de `data/_config/pii_blocklist.txt`, que esta GITIGNORED y existe
exactamente para que los nombres reales no entren nunca en un fichero versionado
(`scripts/precommit_leak_guard.py`, `MEJORAS #161`).
"""
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
        "la blocklist salio VACIA: sin ella la redaccion no comprueba nada y el fixture "
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
          "parent_slug", "parent_sha256", "role", "paginas", "tipo", "alias_de"}
cob = json.loads(
    (CASO / "01_Procesado/02_Sala de máquina/_cobertura.json").read_text(encoding="utf-8"))
cob = [{k: limpia(v) for k, v in f.items() if k in CAMPOS}
       for f in cob if str(f.get("rel_path", "")).startswith("05_CRM/")]
(DST / "w02veke_cobertura.json").write_text(
    json.dumps(cob, ensure_ascii=False, indent=1), encoding="utf-8")

print(f"ocurrencias: {len(oc['ocurrencias'])} · cobertura 05_CRM: {len(cob)} · "
      f"terminos redactados: {len(TERMINOS)}")
```

- [ ] **Step 2: Verificar los fixtures contra la blocklist ENTERA, no contra una muestra**

Un grep de seis substrings elegidas a mano **no es prueba de anonimizacion**: es el verde
de un guard sin su blocklist. La comprobacion corre contra los mismos terminos que uso la
redaccion, y **falla si la blocklist esta vacia** — sin ella no se comprueba nada.

Run:
```bash
python -c "import pathlib,re,sys; sys.path.insert(0,'.'); from scripts.precommit_leak_guard import cargar_blocklist; T=cargar_blocklist(pathlib.Path('.')); t=''.join(p.read_text(encoding='utf-8') for p in pathlib.Path('tests/fixtures/procedimiento').glob('*.json')); m=sorted({x for x in T if re.search(re.escape(x),t,re.I)}); print(f'terminos={len(T)} supervivientes={len(m)}'); sys.exit(1 if (m or not T) else 0)"
```
Expected: `terminos=<N>` con N>0, `supervivientes=0`, exit 0

- [ ] **Step 3: Write the regression test**

```python
# tests/test_procedimiento_regresion.py
"""Regresion sobre el corpus real de W-02VEKE (fixtures anonimizados).

Se usa W-02VEKE y no el piloto W-02MA0R del spec §11.3 porque el piloto NO tiene sala
de maquina corrida y por tanto no ejercita el selector por clase documental, que es la
mitad de esta pieza.
"""
import json
import pathlib

import pytest

from core.procedimiento import artefacto, carpetas, diff, ledger, mapa

FIX = pathlib.Path(__file__).parent / "fixtures" / "procedimiento"
CARP = carpetas.CARPETA_OTROS


@pytest.fixture()
def corpus():
    oc = json.loads((FIX / "w02veke_ocurrencias.json").read_text(encoding="utf-8"))
    cob = json.loads((FIX / "w02veke_cobertura.json").read_text(encoding="utf-8"))
    return oc, cob


def test_el_corpus_tiene_los_metodos_que_esta_pieza_debe_cubrir(corpus):
    """Control positivo del fixture: si el corpus no trae variedad de `metodo`, el test
    de abajo pasaria sin probar nada."""
    _, cob = corpus
    metodos = {f["metodo"] for f in cob}
    assert "pypdf" in metodos
    assert "ocr" in metodos
    assert len(metodos) >= 3


def test_el_selector_resuelve_todo_el_corpus_sin_excepciones(tmp_path, corpus):
    """Ninguna fila del corpus real hace que `elegir` lance. Bloquear es una respuesta
    valida; petar no."""
    _, cob = corpus
    from core.sala_maquina import cobertura_desde_dicts
    for fila in cobertura_desde_dicts(cob):
        e = artefacto.elegir(tmp_path, fila,
                             raw_rel=f"00_Input/{fila.rel_path}",
                             sin_cobertura_ok=False)
        assert e.bloqueo or e.source_kind, f"ni eleccion ni bloqueo para {fila.slug}"


def test_un_mapa_que_asigna_TODO_el_expediente_deja_sin_asignar_vacio(tmp_path, corpus):
    """La propiedad que la vista garantiza: nada que exista se queda fuera en silencio."""
    oc, cob = corpus
    case_dir = tmp_path
    (case_dir / "05_Procedimiento" / CARP).mkdir(parents=True)
    (case_dir / "00_Input").mkdir(parents=True, exist_ok=True)

    class _Reg:
        ocurrencias = oc["ocurrencias"]
        def listadas(self, exp, **kw):
            return {v["doc_id"]: v["revisiones"][-1] for v in self.ocurrencias.values()
                    if v["expediente_id"] == str(exp)}
        def materializadas(self, exp, **kw):
            return {d: r for d, r in self.listadas(exp).items()
                    if r["estado"] == "materializada"}
        def solo_listadas(self, exp, **kw):
            return {d: r for d, r in self.listadas(exp).items()
                    if r["estado"] == "listada"}

    reg = _Reg()
    docs = sorted(reg.materializadas("540"))
    entradas = tuple(
        mapa.EntradaMapa(carpeta=CARP, origen="crm", doc_id=d, orden=f"D-{i:02d}",
                         descripcion=f"documento_{i:02d}", logical_key=f"crm:540:{d}")
        for i, d in enumerate(docs, 1))
    m = mapa.MapaProcesal(version=1, expediente_crm="540", entradas=entradas)

    p = diff.construir(case_dir, "CASO", "540", m=m, reg=reg, cob={}, 
                       led=ledger.Ledger(asientos={}), pull_state=None)
    assert p.sin_asignar == (), f"quedaron sin asignar: {p.sin_asignar[:5]}"
    assert docs, "el fixture no tiene documentos materializados: el test no probaria nada"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_procedimiento_regresion.py -q --tb=short`
Expected: PASS (3 tests)

- [ ] **Step 5: Run the full suite with two seeds**

Run: `python -m scripts.session_close`
Expected: la verja corre la suite con las semillas 777 y 31337 y las dos salen verdes.
Un verde de una sola corrida no dice nada sobre el orden.

- [ ] **Step 6: Commit**

```bash
git add tests/fixtures/procedimiento/ tests/test_procedimiento_regresion.py
git commit -m "vista procesal: regresion sobre el corpus real de W-02VEKE, anonimizado"
```

---

## Lo que este plan NO construye

Copiado del alcance del spec §7, para que no se lea como una omisión:

- **Que `plan` proponga la carpeta.** La asignación es del letrado, por decisión cerrada.
- **Cualquier modificación de `00_Input/05_CRM`.**
- **La reescritura de `intake_manifest`** al modelo de ocurrencias (opción A).
- **La preparación de la documental numerada** (el `D-04_chat_whatsapp.pdf`). Hoy nada lo produce y
  es un proyecto propio con su propia decisión sobre quién numera.
- **La subida carpeta → CRM.** El cliente documental de `core/` solo lee.
- **La resolución de emails** `.eml` → MD atomizado + adjuntos: requiere entrar en `email_atomize`.
- **Journal y recuperación automática** tras un fallo parcial de `apply`. Con el ledger como último
  commit, re-ejecutar `plan` reconcilia y es determinista.
- **Retirar los procesales de `01_Procesado/Sala lectura`.** El spec §7 lo pide con exclusión
  operativa por ocurrencias y SHA. La sala de W-02VEKE se montó el 2026-09-09 **con** los 78
  documentos del CRM dentro; decidir si se retiran es una tarea aparte y necesita este mapa primero.
- **El cambio de comportamiento de las seis skills del spec §8.1** (`organizar-sala-lectura`,
  `preparacion-audiencia-previa`, `preparacion-juicio-oral`, `escritos-judiciales`,
  `contestacion-honorarios-art20-lau`, `oposicion-alegacion-nulidad`), el handoff de §8.2 y la
  documentación de §8.4. Este plan construye **la capacidad** —las cinco carpetas existen y
  `registrar_outputs` las admite (Tarea 1, que es lo único que §7 mete en alcance)— y deja el
  **consumo** para una pieza 5. Dos razones: cada skill hay que re-empaquetarla e importarla en
  el servidor, que es un paso manual fuera de este repo; y `preparacion-audiencia-previa` arrastra
  un aviso a retirar («FeesDefender core aún no lee `05_Procedimiento`») que solo deja de ser
  cierto **cuando esta pieza esté mergeada**, no cuando esté escrita. Lo que sí entra aquí es la
  sincronización mecánica del helper (§8.3), porque sin ella la suite queda roja.

**Y lo que no falta aunque el spec lo pida:** los tests de biblioteca de §6 —conflicto de mapa
durante el checkin sin subir ledger ni PDF, y borrado remoto del ledger sin resurrección— son de
la **pieza 1**, ya mergeada: el grupo indivisible vive en `core/config.py:441` y lo aplica
`core/repository_checkout.py:420`, con sus tests en `tests/test_repository_checkout.py` y
`tests/test_repository_cli_checkin.py`. No se reescriben aquí.

## Revisión adversarial

Esta pieza **decide quién puede escribir sobre qué copia** (el ledger de propiedad) y **puede
destruir datos de cliente** (`borrar`, `reemplazar`, `mover` sobre el expediente). Por el presupuesto
de rondas de `CLAUDE.md` le corresponden **dos rondas**:

- **Ronda 1 — sobre este plan**, antes de escribir código.
- **Ronda 2 — sobre el diff**, antes de mergear.

Las dos las ejecuta Codex en solo lectura, volcando a un fichero fuera del repo, y las adjudica
Claude contra la fuente. El informe literal va a un acta hermana
`2026-09-09-vista-procesal-pieza4-r<N>-adversarial-review.md` con su digest; la adjudicación va
embebida en este plan.
