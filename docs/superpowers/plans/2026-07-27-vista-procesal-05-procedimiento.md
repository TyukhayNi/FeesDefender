# Vista procesal en `05_Procedimiento` — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir en `05_Procedimiento` cinco carpetas procesales a partir de un mapping explícito `doc_id → carpeta`, sin tocar `00_Input/05_CRM`.

**Architecture:** Tres piezas. (1) Un arreglo en `core/intake_manifest.py` para que el `doc_id` se persista en la entrada canónica del manifiesto de intake y no solo en los alias — sin eso, `doc_id → ruta` no tiene respuesta para 62 de los 70 documentos del caso piloto. (2) Un cerebro nuevo `core/procedimiento.py`, puro y **sin red**: lee el manifiesto local y el YAML del letrado, calcula un diff y lo aplica. (3) Un CLI `scripts/procedimiento.py` con subcomandos `plan`/`apply`, siguiendo el patrón de `sala_maquina` y `migrate_05crm_buckets`.

**Tech Stack:** Python 3, `pytest`, `typer` (CLI), `PyYAML`, `dataclasses`. Sin dependencias nuevas.

**Spec:** [`docs/superpowers/specs/2026-07-27-vista-procesal-05-procedimiento-design.md`](../specs/2026-07-27-vista-procesal-05-procedimiento-design.md)

## Global Constraints

- **`00_Input/05_CRM` no se modifica jamás.** Ninguna tarea escribe, mueve ni borra bajo `00_Input`.
- **`apply` solo puede destruir lo que figura en `05_Procedimiento/_MANIFIESTO_PROCESAL.json`.** Escritos generados, `Jurisprudencia/` y cualquier fichero ajeno dentro de las cinco carpetas se reportan y no se tocan.
- **Nunca se adivina la carpeta de un documento.** Un `doc_id` sin asignar va a `sin_asignar:` y bloquea `apply`.
- **Encoding:** UTF-8 sin BOM en todo fichero escrito. En Windows usar `Path.write_text(..., encoding="utf-8")`, nunca `Add-Content` sin `-Encoding UTF8`.
- **Nombres de carpeta sin acentos** (`02_Monitorio - Oposicion`, no `Oposición`): rutas compartidas entre Windows local, `G:` de Drive Stream y rclone.
- **Límite de ruta de Windows (260 caracteres):** `descripcion` se trunca a 60 caracteres. La ruta base en Drive ya consume ~175.
- **Terminología de partes:** propietario / buscador, nunca vendedor / comprador, en todo texto nuevo. Los nombres de fichero que vienen del CRM se respetan tal cual: son un hecho del expediente.
- **Suite en verde antes de cada commit:** `python -m pytest -q --tb=no`. El orden es aleatorio (`pytest-randomly`): ningún test puede depender del orden.
- **Rama:** el trabajo va en la rama actual y entra a `main` por PR. `main` está protegida.

---

### Task 1: Persistir `doc_id` en la entrada canónica del manifiesto

Hoy `register()` recibe el `doc_id` en `**alias_details` pero solo lo guarda si crea un alias. Cuando el hash es nuevo —el caso normal— se descarta. Esta tarea lo arregla y añade el resolutor inverso.

**Files:**
- Modify: `core/intake_manifest.py:292-300` (rama `entry is None` de `register`) y zona de introspección (tras `lookup`, ~línea 325)
- Test: `tests/test_intake_manifest.py`

**Interfaces:**
- Consumes: nada.
- Produces: `IntakeManifest.lookup_doc_id(doc_id: str) -> tuple[str, str] | None` que devuelve `(sha256, primary_path)`. Entradas nuevas con claves `doc_id: str`, `expediente_id: str`, `source: str`, `modified_at: str` junto a `primary_path` y `aliases`.

> **`expediente_id` es obligatorio, no adorno.** Un caso puede tener varios expedientes en el CRM (`sudespacho_expedientes` es una lista). Sin él en la entrada canónica, `_docs_del_expediente` de la Task 5 no puede filtrar y mezclaría documentos de expedientes distintos en la misma vista procesal.

- [ ] **Step 1: Escribir los tests que fallan**

En `tests/test_intake_manifest.py`, añadir al final:

```python
def test_register_persiste_doc_id_en_entrada_canonica(tmp_path, monkeypatch):
    """Un hash nuevo debe conservar su doc_id: hoy se descarta (solo vive en alias)."""
    m = _manifest_vacio(tmp_path, monkeypatch)
    action, primary = m.register(
        "a" * 64, "05_CRM/01_Demanda/demanda.pdf",
        source="crm", expediente_id="487", doc_id="33428",
        modified_at="2025-04-01T12:38:01.000+02:00",
    )
    assert action == "write"
    entry = m.lookup("a" * 64)
    assert entry["doc_id"] == "33428"
    assert entry["expediente_id"] == "487"
    assert entry["source"] == "crm"
    assert entry["modified_at"] == "2025-04-01T12:38:01.000+02:00"


def test_lookup_doc_id_encuentra_en_entrada_y_en_alias(tmp_path, monkeypatch):
    """El doc_id canónico y el de un alias resuelven ambos al primary_path."""
    m = _manifest_vacio(tmp_path, monkeypatch)
    m.register("b" * 64, "05_CRM/01_Demanda/factura.pdf",
               source="crm", expediente_id="487", doc_id="36791")
    # mismo contenido, otra rama -> alias
    m.register("b" * 64, "05_CRM/99_Sin categoria/487/factura_debida.pdf",
               source="crm", expediente_id="487", doc_id="33437")

    assert m.lookup_doc_id("36791") == ("b" * 64, "05_CRM/01_Demanda/factura.pdf")
    assert m.lookup_doc_id("33437") == ("b" * 64, "05_CRM/01_Demanda/factura.pdf")
    assert m.lookup_doc_id("99999") is None


def test_lookup_doc_id_tolera_entrada_antigua_sin_doc_id(tmp_path, monkeypatch):
    """Retrocompatibilidad: manifiestos escritos antes de este cambio."""
    m = _manifest_vacio(tmp_path, monkeypatch)
    m.data["c" * 64] = {"primary_path": "05_CRM/99_Otros/viejo.pdf", "aliases": []}
    assert m.lookup_doc_id("12345") is None
    # y lo adquiere al re-registrar el mismo hash en la misma ruta
    m.register("c" * 64, "05_CRM/99_Otros/viejo.pdf", source="crm", doc_id="12345")
    assert m.lookup_doc_id("12345") == ("c" * 64, "05_CRM/99_Otros/viejo.pdf")
```

Y el helper, junto a los demás del fichero:

```python
def _manifest_vacio(tmp_path, monkeypatch):
    """IntakeManifest sobre un caso sintético en tmp_path."""
    from core import config
    monkeypatch.setattr(config.settings, "casos_root", tmp_path)
    (tmp_path / "CASO" / "00_Input").mkdir(parents=True)
    from core.intake_manifest import IntakeManifest
    return IntakeManifest("CASO")
```

- [ ] **Step 2: Ejecutar los tests y verificar que fallan**

Run: `python -m pytest tests/test_intake_manifest.py -k "doc_id" -v`
Expected: FAIL. Los dos primeros por `KeyError: 'doc_id'` / `AttributeError: 'IntakeManifest' object has no attribute 'lookup_doc_id'`.

- [ ] **Step 3: Implementar el cambio en `register`**

En `core/intake_manifest.py`, sustituir la rama `entry is None`:

```python
        entry = self.data.get(sha256)
        if entry is None:
            nuevo: dict[str, Any] = {"primary_path": rel, "aliases": [], "source": source}
            # doc_id, expediente_id y fecha del origen se persisten en la entrada
            # canónica, no solo en los alias: sin esto `doc_id -> ruta` no tiene
            # respuesta para el documento que se escribe primero, y sin
            # expediente_id no se pueden separar dos expedientes del mismo caso.
            for clave in ("doc_id", "expediente_id", "modified_at"):
                valor = alias_details.get(clave)
                if valor is not None and str(valor) != "":
                    nuevo[clave] = str(valor)
            if message_id:
                nuevo["message_id"] = message_id
            self.data[sha256] = nuevo
            self._dirty = True
            return ("write", rel)
```

Y en la rama del no-op (`rel == primary`), adquirir los campos si faltan —es lo que hace retrocompatible un manifiesto viejo:

```python
        primary = entry.get("primary_path", "")
        if rel == primary:
            # Misma ubicación lógica — no-op, no hay alias que añadir. Pero sí
            # se adquieren los campos que un manifiesto anterior a este cambio
            # no tenía (retrocompatibilidad, sin sobrescribir lo ya presente).
            for clave in ("doc_id", "expediente_id", "modified_at"):
                valor = alias_details.get(clave)
                if valor is not None and str(valor) != "" and not entry.get(clave):
                    entry[clave] = str(valor)
                    self._dirty = True
            if source and not entry.get("source"):
                entry["source"] = source
                self._dirty = True
            return ("skip", primary)
```

- [ ] **Step 4: Implementar `lookup_doc_id`**

En la sección de introspección, justo después de `lookup`:

```python
    def lookup_doc_id(self, doc_id: str) -> tuple[str, str] | None:
        """Resuelve un ``doc_id`` del CRM a ``(sha256, primary_path)``.

        Busca en DOS sitios: el ``doc_id`` de la entrada canónica y los
        ``doc_id`` de sus alias. Una entrada solo puede llevar un ``doc_id``
        canónico; los demás documentos con contenido idéntico cuelgan como
        alias, y deben resolver igualmente (al ``primary_path``, que es donde
        está el fichero físico).

        Devuelve None si el ``doc_id`` no está registrado.
        """
        if not doc_id:
            return None
        clave = str(doc_id).strip()
        for sha, entry in self.data.items():
            if str(entry.get("doc_id") or "") == clave:
                return (sha, entry.get("primary_path", ""))
            for alias in entry.get("aliases", []):
                if isinstance(alias, dict) and str(alias.get("doc_id") or "") == clave:
                    return (sha, entry.get("primary_path", ""))
        return None
```

- [ ] **Step 5: Ejecutar los tests y verificar que pasan**

Run: `python -m pytest tests/test_intake_manifest.py -v`
Expected: PASS, incluidos los tests preexistentes del fichero.

- [ ] **Step 6: Suite completa**

Run: `python -m pytest -q --tb=no`
Expected: 0 failed. `register` la usan el pull del CRM, el export de correo y los atomizadores; cualquier rotura sale aquí.

- [ ] **Step 7: Commit**

```bash
git add core/intake_manifest.py tests/test_intake_manifest.py
git commit -m "fix(intake): persistir doc_id/source/modified_at en la entrada canonica del manifiesto"
```

---

### Task 2: El pull pasa `modified_at` al manifiesto

El pull ya pasa `doc_id` y `expediente_id`, pero no la fecha de modificación del CRM. Sin ella, `plan` no puede proponer el `orden` por fecha de lote de los escritos sueltos.

**Files:**
- Modify: `core/sync_sudespacho.py:1527-1533`
- Modify: `tests/test_pull_expediente_v2.py:118-130` (el helper `_make_doc`)
- Test: `tests/test_pull_expediente_v2.py`

**Interfaces:**
- Consumes: `IntakeManifest.register(..., modified_at=...)` y `lookup_doc_id` de la Task 1.
- Produces: entradas de manifiesto con `modified_at` y `expediente_id` poblados para documentos del CRM.

- [ ] **Step 1: Extender el helper `_make_doc`**

`_make_doc` no expone `modified_at`. Añadir el kwarg, con `None` por defecto para no tocar las 15 llamadas existentes:

```python
def _make_doc(modules, doc_id, *, filename, id_carpeta=None, id_carpeta_label=None,
              modified_at=None):
    """Construye un ``GdocuDocInfo`` con los campos mínimos del fake."""
    GdocuDocInfo = modules["sync_sudespacho"].GdocuDocInfo
    return GdocuDocInfo(
        doc_id=str(doc_id),
        filename=filename,
        id_carpeta=id_carpeta,
        id_carpeta_label=id_carpeta_label,
        mime="application/pdf",
        size=None,
        raw={},
        modified_at=modified_at,
    )
```

- [ ] **Step 2: Escribir el test que falla**

Añadir a `tests/test_pull_expediente_v2.py`, siguiendo el patrón de
`test_pull_v2_un_doc_con_id_canonico_se_escribe_y_loggea`:

```python
def test_pull_v2_registra_modified_at_y_expediente_en_el_manifiesto(
    modules, tmp_casos_root,
):
    """La fecha del CRM llega al manifiesto: `plan` la usa para el orden por lote."""
    cm = modules["case_manager"]
    ss = modules["sync_sudespacho"]
    cm.ensure_case("PV2-MOD")

    doc = _make_doc(modules, "33428", filename="DEMANDA MONITORIO.pdf",
                    id_carpeta="307", id_carpeta_label="DEMANDA",
                    modified_at="2025-04-01T12:38:01.000+02:00")
    client = FakeSudespachoClient(docs=[doc], docs_content={"33428": b"%PDF demo"})

    ss.pull_expediente_v2("PV2-MOD", "487", client=client)

    IntakeManifest = modules["intake_manifest"].IntakeManifest
    m = IntakeManifest("PV2-MOD")
    m.load()
    hit = m.lookup_doc_id("33428")
    assert hit is not None
    sha, primary = hit
    assert primary.startswith("05_CRM/01_Demanda/")
    entry = m.lookup(sha)
    assert entry["modified_at"] == "2025-04-01T12:38:01.000+02:00"
    assert entry["expediente_id"] == "487"
```

> Si `modules` no expone todavía la clave `"intake_manifest"`, añadirla en la fixture `modules` (línea 36) junto a las demás; no importar el módulo directamente, que rompería el aislamiento de `tmp_casos_root`.

- [ ] **Step 3: Ejecutar y verificar que falla**

Run: `python -m pytest tests/test_pull_expediente_v2.py -k modified_at -v`
Expected: FAIL con `KeyError: 'modified_at'`.

- [ ] **Step 4: Pasar el campo en la llamada**

En `core/sync_sudespacho.py`, en la llamada a `manifest.register`:

```python
                action, primary_rel = manifest.register(
                    sha,
                    rel_path,
                    source="crm",
                    expediente_id=str(expediente_id),
                    doc_id=info.doc_id,
                    modified_at=info.modified_at,
                )
```

- [ ] **Step 5: Ejecutar y verificar que pasa**

Run: `python -m pytest tests/test_pull_expediente_v2.py -v`
Expected: PASS, incluidos los ~15 tests preexistentes del fichero (el kwarg nuevo de `_make_doc` tiene default `None`).

- [ ] **Step 6: Commit**

```bash
git add core/sync_sudespacho.py tests/test_pull_expediente_v2.py
git commit -m "feat(intake): el pull del CRM registra modified_at en el manifiesto"
```

---

### Task 3: Constantes, modelo y carga del `_mapa_procesal.yaml`

**Files:**
- Create: `core/procedimiento.py`
- Test: `tests/test_procedimiento.py`

**Interfaces:**
- Consumes: `core.config.caso_path`.
- Produces:
  - `CARPETAS_PROCESALES: tuple[str, ...]` (5 nombres, en orden)
  - `CARPETA_OTROS: str`
  - `MAPA_REL: str`, `MANIFIESTO_REL: str`
  - `@dataclass(frozen=True) EntradaMapa(doc_id: str, carpeta: str, orden: str, descripcion: str)`
  - `@dataclass DocPendiente(doc_id: str, fichero: str, lote: str)`
  - `@dataclass MapaProcesal(version: int, expediente_crm: str, entradas: list[EntradaMapa], sin_asignar: list[DocPendiente])`
  - `cargar_mapa(case_id: str) -> MapaProcesal | None`
  - `guardar_mapa(case_id: str, mapa: MapaProcesal) -> Path`
  - `MapaInvalidoError(Exception)`

- [ ] **Step 1: Escribir los tests que fallan**

Crear `tests/test_procedimiento.py`:

```python
import pytest

from core.procedimiento import (
    CARPETAS_PROCESALES,
    CARPETA_OTROS,
    EntradaMapa,
    MapaInvalidoError,
    MapaProcesal,
    cargar_mapa,
    guardar_mapa,
)


@pytest.fixture
def caso(tmp_path, monkeypatch):
    from core import config
    monkeypatch.setattr(config.settings, "casos_root", tmp_path)
    d = tmp_path / "CASO"
    (d / "00_Input").mkdir(parents=True)
    (d / "05_Procedimiento").mkdir(parents=True)
    return "CASO"


def test_carpetas_procesales_son_cinco_y_otros_es_la_ultima():
    assert len(CARPETAS_PROCESALES) == 5
    assert CARPETAS_PROCESALES[-1] == CARPETA_OTROS
    assert CARPETA_OTROS == "05_Otros escritos"
    # Sin acentos: rutas compartidas Windows / Drive Stream / rclone.
    assert all(c.isascii() for c in CARPETAS_PROCESALES)


def test_cargar_mapa_devuelve_none_si_no_existe(caso):
    assert cargar_mapa(caso) is None


def test_guardar_y_cargar_ida_y_vuelta(caso):
    mapa = MapaProcesal(
        version=1, expediente_crm="487",
        entradas=[EntradaMapa(doc_id="33428", carpeta=CARPETAS_PROCESALES[0],
                              orden="00", descripcion="demanda_monitorio")],
        sin_asignar=[],
    )
    guardar_mapa(caso, mapa)
    leido = cargar_mapa(caso)
    assert leido.expediente_crm == "487"
    assert leido.entradas == mapa.entradas
    assert leido.sin_asignar == []


def test_cargar_mapa_rechaza_carpeta_desconocida(caso):
    ruta = _ruta_mapa(caso)
    ruta.write_text(
        "version: 1\nexpediente_crm: '487'\ncarpetas:\n"
        "  \"07_Inventada\":\n    - {doc_id: '1', orden: '00', descripcion: x}\n",
        encoding="utf-8",
    )
    with pytest.raises(MapaInvalidoError, match="07_Inventada"):
        cargar_mapa(caso)


def test_cargar_mapa_rechaza_doc_id_repetido(caso):
    ruta = _ruta_mapa(caso)
    ruta.write_text(
        "version: 1\nexpediente_crm: '487'\ncarpetas:\n"
        f"  \"{CARPETAS_PROCESALES[0]}\":\n"
        "    - {doc_id: '33428', orden: '00', descripcion: a}\n"
        f"  \"{CARPETA_OTROS}\":\n"
        "    - {doc_id: '33428', orden: '2025-01-01', descripcion: b}\n",
        encoding="utf-8",
    )
    with pytest.raises(MapaInvalidoError, match="33428"):
        cargar_mapa(caso)


def _ruta_mapa(case_id):
    from core.config import caso_path
    from core.procedimiento import MAPA_REL
    return caso_path(case_id) / MAPA_REL
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `python -m pytest tests/test_procedimiento.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'core.procedimiento'`.

- [ ] **Step 3: Implementar el módulo**

Crear `core/procedimiento.py`:

```python
"""Vista procesal del expediente en ``05_Procedimiento``.

Construye cinco carpetas procesales a partir de un mapping explícito
``doc_id -> carpeta`` que decide el letrado. NO toca ``00_Input/05_CRM``, que
sigue siendo espejo fiel de cómo está archivado el expediente en el CRM.

Diseño: ``docs/superpowers/specs/2026-07-27-vista-procesal-05-procedimiento-design.md``.

El módulo es puro y **sin red**: la fuente de qué documentos existen es el
manifiesto de intake local, no el CRM. El intake trae; esto organiza.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from core.config import caso_path

# Las cinco carpetas, en orden de aparición. Sin acentos a propósito: la ruta
# se comparte entre Windows local, la unidad G: de Drive Stream y rclone.
CARPETAS_PROCESALES: tuple[str, ...] = (
    "01_Monitorio - Demanda y documentos",
    "02_Monitorio - Oposicion",
    "03_Ordinario - Demanda y documentos",
    "04_Ordinario - Contestacion",
    "05_Otros escritos",
)

# La carpeta de escritos sueltos: no tiene escrito rector, y su `orden` es la
# fecha del lote en vez del número de documento.
CARPETA_OTROS: str = CARPETAS_PROCESALES[-1]

MAPA_REL: str = "05_Procedimiento/_mapa_procesal.yaml"
MANIFIESTO_REL: str = "05_Procedimiento/_MANIFIESTO_PROCESAL.json"

# Longitud máxima de `descripcion`. La ruta base en Drive consume ~175 de los
# 260 caracteres que tolera Windows; el nombre de carpeta, otros ~38.
MAX_DESCRIPCION: int = 60


class MapaInvalidoError(Exception):
    """El ``_mapa_procesal.yaml`` no cumple su contrato."""


@dataclass(frozen=True)
class EntradaMapa:
    doc_id: str
    carpeta: str
    orden: str
    descripcion: str


@dataclass(frozen=True)
class DocPendiente:
    doc_id: str
    fichero: str
    lote: str


@dataclass
class MapaProcesal:
    version: int
    expediente_crm: str
    entradas: list[EntradaMapa] = field(default_factory=list)
    sin_asignar: list[DocPendiente] = field(default_factory=list)


def ruta_mapa(case_id: str) -> Path:
    return caso_path(case_id) / MAPA_REL


def cargar_mapa(case_id: str) -> MapaProcesal | None:
    """Lee y valida el mapa. Devuelve None si no existe.

    Raises:
        MapaInvalidoError: carpeta desconocida, doc_id repetido, o estructura
            que no casa con el contrato.
    """
    ruta = ruta_mapa(case_id)
    if not ruta.is_file():
        return None
    try:
        crudo = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise MapaInvalidoError(f"YAML ilegible en {MAPA_REL}: {exc}") from exc
    if not isinstance(crudo, dict):
        raise MapaInvalidoError(f"{MAPA_REL} debe ser un mapa YAML")

    entradas: list[EntradaMapa] = []
    vistos: dict[str, str] = {}
    carpetas = crudo.get("carpetas") or {}
    if not isinstance(carpetas, dict):
        raise MapaInvalidoError("`carpetas` debe ser un mapa carpeta -> lista")

    for carpeta, items in carpetas.items():
        if carpeta not in CARPETAS_PROCESALES:
            raise MapaInvalidoError(
                f"Carpeta desconocida: {carpeta!r}. Válidas: {list(CARPETAS_PROCESALES)}"
            )
        for item in items or []:
            if not isinstance(item, dict) or not item.get("doc_id"):
                raise MapaInvalidoError(f"Entrada sin doc_id en {carpeta!r}: {item!r}")
            doc_id = str(item["doc_id"]).strip()
            if doc_id in vistos:
                raise MapaInvalidoError(
                    f"doc_id {doc_id} aparece en {vistos[doc_id]!r} y en {carpeta!r}"
                )
            vistos[doc_id] = carpeta
            entradas.append(EntradaMapa(
                doc_id=doc_id,
                carpeta=carpeta,
                orden=str(item.get("orden") or "").strip(),
                descripcion=str(item.get("descripcion") or "").strip(),
            ))

    pendientes = [
        DocPendiente(
            doc_id=str(p.get("doc_id") or "").strip(),
            fichero=str(p.get("fichero") or ""),
            lote=str(p.get("lote") or ""),
        )
        for p in (crudo.get("sin_asignar") or [])
        if isinstance(p, dict)
    ]

    return MapaProcesal(
        version=int(crudo.get("version") or 1),
        expediente_crm=str(crudo.get("expediente_crm") or "").strip(),
        entradas=entradas,
        sin_asignar=pendientes,
    )


def guardar_mapa(case_id: str, mapa: MapaProcesal) -> Path:
    """Escribe el mapa en UTF-8 sin BOM, agrupado por carpeta y en orden."""
    carpetas: dict[str, list[dict]] = {}
    for carpeta in CARPETAS_PROCESALES:
        items = [e for e in mapa.entradas if e.carpeta == carpeta]
        if items:
            carpetas[carpeta] = [
                {"doc_id": e.doc_id, "orden": e.orden, "descripcion": e.descripcion}
                for e in sorted(items, key=lambda x: (x.orden, x.descripcion))
            ]
    doc = {
        "version": mapa.version,
        "expediente_crm": mapa.expediente_crm,
        "carpetas": carpetas,
        "sin_asignar": [
            {"doc_id": p.doc_id, "fichero": p.fichero, "lote": p.lote}
            for p in mapa.sin_asignar
        ],
    }
    ruta = ruta_mapa(case_id)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(
        yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )
    return ruta
```

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `python -m pytest tests/test_procedimiento.py -v`
Expected: PASS, 5 tests.

- [ ] **Step 5: Commit**

```bash
git add core/procedimiento.py tests/test_procedimiento.py
git commit -m "feat(procedimiento): contrato y carga del _mapa_procesal.yaml"
```

---

### Task 4: Propuesta de `orden` y `descripcion`

Funciones puras de nombrado. Se testean solas porque son donde vive toda la casuística real del expediente.

**Files:**
- Modify: `core/procedimiento.py` (añadir al final)
- Test: `tests/test_procedimiento.py` (añadir)

**Interfaces:**
- Consumes: `core.utils.slugify`, `CARPETA_OTROS`, `MAX_DESCRIPCION` de la Task 3.
- Produces:
  - `proponer_orden(crm_filename: str, carpeta: str, modified_at: str | None) -> str`
  - `proponer_descripcion(crm_filename: str) -> str`
  - `nombre_final(orden: str, descripcion: str, extension: str) -> str`

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `tests/test_procedimiento.py`:

```python
from core.procedimiento import nombre_final, proponer_descripcion, proponer_orden

P0 = CARPETAS_PROCESALES[0]  # 01_Monitorio - Demanda y documentos


@pytest.mark.parametrize("filename,esperado", [
    ("D 02 - CONTRATO MEDIACION.pdf", "D-02"),
    ("D 02-A - MODIFICACION HONORARIOS EV - VENDEDOR - 365_001.pdf", "D-02A"),
    ("D 14- REQUERIMIENTO EXTRAJUDICIAL - ENTREGAO ALBARAN.pdf", "D-14"),
    ("002_DOC 1 MAILS", "D-01"),
    ("DOC 10 CORREOS RAQUEL ARAPDIS.pdf", "D-10"),
    ("004_DOC 3 ESCRITURA DE COMPRAVENTA", "D-03"),
])
def test_proponer_orden_lee_el_numero_de_documento(filename, esperado):
    assert proponer_orden(filename, P0, "2025-04-01T12:51:01.000+02:00") == esperado


def test_escrito_rector_sin_numero_en_carpeta_procesal_es_00():
    assert proponer_orden("DEMANDA_MONITORIO_-_COMPRADOR.pdf", P0,
                          "2025-04-01T12:38:01.000+02:00") == "00"


def test_demanda_no_se_confunde_con_documento_D():
    """'DEMANDA' empieza por D pero no lleva número: no debe leerse como D-nn."""
    assert proponer_orden("DEMANDA MONITORIO - COMPRADOR.rtf", P0, None) == "00"


def test_en_otros_escritos_sin_numero_el_orden_es_la_fecha_del_lote():
    assert proponer_orden("DECRETO - ADMITE A TRAMITE + EMPLAZA DDO", CARPETA_OTROS,
                          "2025-10-16T10:11:16.000+02:00") == "2025-10-16"


def test_en_otros_escritos_sin_fecha_el_orden_queda_vacio_para_que_lo_ponga_el_letrado():
    assert proponer_orden("ESCRITO SUELTO", CARPETA_OTROS, None) == ""


def test_proponer_descripcion_normaliza_y_trunca():
    assert proponer_descripcion("D 03 - RECONOCIMEINTO GESTION HONORARIOS.pdf") == \
        "d_03_reconocimeinto_gestion_honorarios"
    largo = "A" * 200 + ".pdf"
    assert len(proponer_descripcion(largo)) <= 60


def test_nombre_final_compone_orden_descripcion_extension():
    assert nombre_final("00", "demanda_monitorio", ".pdf") == "00_demanda_monitorio.pdf"
    assert nombre_final("D-02", "contrato_mediacion", ".pdf") == "D-02_contrato_mediacion.pdf"


def test_nombre_final_sin_orden_no_deja_guion_bajo_inicial():
    assert nombre_final("", "escrito_suelto", ".pdf") == "escrito_suelto.pdf"
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `python -m pytest tests/test_procedimiento.py -k "orden or descripcion or nombre_final" -v`
Expected: FAIL con `ImportError: cannot import name 'proponer_orden'`.

- [ ] **Step 3: Implementar**

Añadir a `core/procedimiento.py`:

```python
import re
import unicodedata

from core.utils import slugify

# "D 02", "D 02-A", "D-14", "D14". Exige dígito tras la D para que DEMANDA,
# DECRETO o DILIGENCIA no se lean como número de documento.
_RE_DOC_D = re.compile(r"\bD\s*[-_]?\s*(\d{1,2})\s*-?\s*([A-Za-z])?\b")
# "DOC 1", "DOC 10". El prefijo de orden del CRM ("002_DOC 1") no interfiere:
# el número que cuenta es el que sigue a DOC.
_RE_DOC_NUM = re.compile(r"\bDOC\s*[-_]?\s*(\d{1,2})\b", re.IGNORECASE)


def _sin_acentos(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    )


def proponer_orden(crm_filename: str, carpeta: str, modified_at: str | None) -> str:
    """Propone el prefijo de orden del fichero. El letrado puede sobrescribirlo.

    Reglas, en este orden:

    1. Si el nombre del CRM lleva número de documento (``D 02``, ``DOC 3``) →
       ``D-02`` / ``D-03``, con sufijo de letra si lo hay (``D 02-A`` →
       ``D-02A``).
    2. Si no lo lleva y la carpeta es una de las cuatro procesales, el
       documento es el **escrito rector** de esa carpeta → ``00``. Si hubiera
       más de un candidato en la misma carpeta, ambos reciben ``00`` y la
       puerta de colisión de nombre final lo pone delante del letrado: no se
       elige por antigüedad ni por ninguna otra regla implícita.
    3. Si no lo lleva y la carpeta es ``05_Otros escritos`` —que no tiene
       escrito rector— → la fecha del lote (``AAAA-MM-DD``).
    4. Sin fecha disponible → cadena vacía, para que la ponga el letrado.
    """
    base = _sin_acentos(crm_filename)

    m = _RE_DOC_NUM.search(base)
    if m:
        return f"D-{int(m.group(1)):02d}"

    m = _RE_DOC_D.search(base)
    if m:
        sufijo = (m.group(2) or "").upper()
        return f"D-{int(m.group(1)):02d}{sufijo}"

    if carpeta != CARPETA_OTROS:
        return "00"

    if modified_at:
        return modified_at[:10]
    return ""


def proponer_descripcion(crm_filename: str) -> str:
    """Slug del nombre del CRM, truncado a ``MAX_DESCRIPCION``."""
    stem = Path(crm_filename).stem or crm_filename
    return slugify(stem, max_length=MAX_DESCRIPCION)


def nombre_final(orden: str, descripcion: str, extension: str) -> str:
    """``<orden>_<descripcion><ext>``; sin ``orden``, solo ``<descripcion><ext>``."""
    ext = extension if extension.startswith(".") or not extension else f".{extension}"
    if not orden:
        return f"{descripcion}{ext}"
    return f"{orden}_{descripcion}{ext}"
```

> Mover el `import re`, `import unicodedata`, y `from core.utils import slugify` al bloque de imports de la cabecera del módulo; aquí se muestran junto al código que los usa solo para que se vea qué hace falta.

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `python -m pytest tests/test_procedimiento.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/procedimiento.py tests/test_procedimiento.py
git commit -m "feat(procedimiento): propuesta de orden y descripcion por nombre del CRM"
```

---

### Task 5: `plan()` — el diff

**Files:**
- Modify: `core/procedimiento.py`
- Test: `tests/test_procedimiento.py`

**Interfaces:**
- Consumes: `IntakeManifest.lookup_doc_id` (Task 1), `cargar_mapa` (Task 3), `proponer_orden`/`proponer_descripcion`/`nombre_final` (Task 4).
- Produces:
  - `@dataclass(frozen=True) AccionCopiar(doc_id: str, origen_rel: str, destino_rel: str, sha256: str)`
  - `@dataclass(frozen=True) AccionMover(doc_id: str, desde_rel: str, hasta_rel: str)`
  - `@dataclass(frozen=True) AccionBorrar(destino_rel: str)`
  - `@dataclass PlanProcesal` con `case_id, expediente_id, copiar, mover, borrar, sin_asignar, ajenos, errores` y método `ok() -> bool`
  - `plan(case_id: str, expediente_id: str) -> PlanProcesal`

`destino_rel` y `desde_rel` son relativos a la **raíz del caso** (p. ej. `05_Procedimiento/01_Monitorio - Demanda y documentos/00_demanda.pdf`). `origen_rel` es relativo a **`00_Input/`**, que es el convenio del manifiesto de intake.

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `tests/test_procedimiento.py`:

```python
from core.procedimiento import plan


def _sembrar(caso_id, docs):
    """Crea ficheros en 05_CRM y los registra en el manifiesto. docs: lista de
    (doc_id, rel_bajo_00_Input, contenido, modified_at)."""
    from core.config import caso_path
    from core.intake_manifest import IntakeManifest, compute_sha256_bytes
    raiz = caso_path(caso_id)
    m = IntakeManifest(caso_id)
    m.load()
    for doc_id, rel, contenido, modified in docs:
        p = raiz / "00_Input" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        data = contenido.encode("utf-8")
        p.write_bytes(data)
        m.register(compute_sha256_bytes(data), rel, source="crm",
                   expediente_id="487", doc_id=doc_id, modified_at=modified)
    m.save()


def test_plan_propone_copiar_lo_asignado(caso):
    _sembrar(caso, [("33428", "05_CRM/03_Monitorio_Demanda/demanda.pdf", "x",
                     "2025-04-01T12:38:01.000+02:00")])
    guardar_mapa(caso, MapaProcesal(
        version=1, expediente_crm="487",
        entradas=[EntradaMapa("33428", P0, "00", "demanda_monitorio")],
        sin_asignar=[],
    ))
    p = plan(caso, "487")
    assert p.ok()
    assert [a.destino_rel for a in p.copiar] == [
        f"05_Procedimiento/{P0}/00_demanda_monitorio.pdf"
    ]


def test_plan_marca_sin_asignar_los_doc_id_nuevos_y_no_esta_ok(caso):
    _sembrar(caso, [
        ("33428", "05_CRM/03_Monitorio_Demanda/demanda.pdf", "x", "2025-04-01T12:38:01+02:00"),
        ("41219", "05_CRM/99_Otros/justif.pdf", "y", "2026-05-29T12:07:48+02:00"),
    ])
    guardar_mapa(caso, MapaProcesal(
        version=1, expediente_crm="487",
        entradas=[EntradaMapa("33428", P0, "00", "demanda_monitorio")],
        sin_asignar=[],
    ))
    p = plan(caso, "487")
    assert [d.doc_id for d in p.sin_asignar] == ["41219"]
    assert not p.ok()


def test_plan_detecta_doc_id_fantasma(caso):
    _sembrar(caso, [])
    guardar_mapa(caso, MapaProcesal(
        version=1, expediente_crm="487",
        entradas=[EntradaMapa("99999", P0, "00", "inventado")],
        sin_asignar=[],
    ))
    p = plan(caso, "487")
    assert any("99999" in e for e in p.errores)
    assert not p.ok()


def test_plan_detecta_colision_de_nombre_final(caso):
    _sembrar(caso, [
        ("36142", "05_CRM/99_Otros/oposicion_a.pdf", "a", "2025-11-03T17:56:03+01:00"),
        ("39885", "05_CRM/99_Otros/oposicion_b.pdf", "b", "2026-04-13T11:20:13+02:00"),
    ])
    guardar_mapa(caso, MapaProcesal(
        version=1, expediente_crm="487",
        entradas=[EntradaMapa("36142", CARPETAS_PROCESALES[1], "00", "oposicion_monitorio"),
                  EntradaMapa("39885", CARPETAS_PROCESALES[1], "00", "oposicion_monitorio")],
        sin_asignar=[],
    ))
    p = plan(caso, "487")
    assert any("00_oposicion_monitorio.pdf" in e for e in p.errores)
    assert not p.ok()


def test_plan_detecta_origen_ausente_en_disco(caso):
    from core.config import caso_path
    _sembrar(caso, [("33428", "05_CRM/03_Monitorio_Demanda/demanda.pdf", "x", None)])
    (caso_path(caso) / "00_Input/05_CRM/03_Monitorio_Demanda/demanda.pdf").unlink()
    guardar_mapa(caso, MapaProcesal(
        version=1, expediente_crm="487",
        entradas=[EntradaMapa("33428", P0, "00", "demanda_monitorio")],
        sin_asignar=[],
    ))
    p = plan(caso, "487")
    assert any("demanda.pdf" in e for e in p.errores)
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `python -m pytest tests/test_procedimiento.py -k plan -v`
Expected: FAIL con `ImportError: cannot import name 'plan'`.

- [ ] **Step 3: Implementar**

Añadir a `core/procedimiento.py`:

```python
import json

from core.intake_manifest import IntakeManifest


@dataclass(frozen=True)
class AccionCopiar:
    doc_id: str
    origen_rel: str      # relativo a 00_Input/
    destino_rel: str     # relativo a la raíz del caso
    sha256: str


@dataclass(frozen=True)
class AccionMover:
    doc_id: str
    desde_rel: str
    hasta_rel: str


@dataclass(frozen=True)
class AccionBorrar:
    destino_rel: str


@dataclass
class PlanProcesal:
    case_id: str
    expediente_id: str
    copiar: list[AccionCopiar] = field(default_factory=list)
    mover: list[AccionMover] = field(default_factory=list)
    borrar: list[AccionBorrar] = field(default_factory=list)
    sin_asignar: list[DocPendiente] = field(default_factory=list)
    ajenos: list[str] = field(default_factory=list)
    errores: list[str] = field(default_factory=list)

    def ok(self) -> bool:
        """True si `apply` puede correr: sin errores y sin decisiones pendientes."""
        return not self.errores and not self.sin_asignar


def _leer_manifiesto_procesal(case_id: str) -> dict:
    ruta = caso_path(case_id) / MANIFIESTO_REL
    if not ruta.is_file():
        return {}
    try:
        return json.loads(ruta.read_text(encoding="utf-8")).get("ficheros", {})
    except (json.JSONDecodeError, OSError):
        return {}


def _docs_del_expediente(manifest: IntakeManifest, expediente_id: str) -> dict[str, dict]:
    """``doc_id -> {sha256, primary_path, modified_at}`` para un expediente CRM.

    Recorre entradas y alias: un mismo contenido presentado dos veces en el CRM
    tiene dos doc_id, uno canónico y otro en alias, y ambos deben salir.
    """
    fuera: dict[str, dict] = {}
    for sha, entry in manifest.data.items():
        primary = entry.get("primary_path", "")
        candidatos = [(entry.get("doc_id"), entry.get("expediente_id"),
                       entry.get("modified_at"))]
        for alias in entry.get("aliases", []):
            if isinstance(alias, dict):
                candidatos.append((alias.get("doc_id"), alias.get("expediente_id"),
                                   alias.get("modified_at") or entry.get("modified_at")))
        for doc_id, exp, modified in candidatos:
            if not doc_id:
                continue
            if exp is not None and str(exp) != str(expediente_id):
                continue
            fuera[str(doc_id)] = {
                "sha256": sha, "primary_path": primary, "modified_at": modified or "",
            }
    return fuera


def plan(case_id: str, expediente_id: str) -> PlanProcesal:
    """Calcula el diff entre el mapa del letrado y lo que hay en disco.

    No escribe nada. `apply` solo debe correr si ``resultado.ok()``.
    """
    res = PlanProcesal(case_id=case_id, expediente_id=str(expediente_id))
    raiz = caso_path(case_id)

    manifest = IntakeManifest(case_id)
    manifest.load()
    disponibles = _docs_del_expediente(manifest, expediente_id)

    try:
        mapa = cargar_mapa(case_id)
    except MapaInvalidoError as exc:
        res.errores.append(str(exc))
        return res
    if mapa is None:
        mapa = MapaProcesal(version=1, expediente_crm=str(expediente_id))

    asignados = {e.doc_id for e in mapa.entradas}

    # 1. Deriva: doc_id presentes en el crudo que el mapa no contempla.
    for doc_id, info in sorted(disponibles.items()):
        if doc_id in asignados:
            continue
        res.sin_asignar.append(DocPendiente(
            doc_id=doc_id,
            fichero=Path(info["primary_path"]).name,
            lote=(info.get("modified_at") or "")[:16],
        ))

    # 2. Destinos deseados, con las puertas de fallo.
    deseado: dict[str, AccionCopiar] = {}   # destino_rel -> acción
    for entrada in mapa.entradas:
        info = disponibles.get(entrada.doc_id)
        if info is None:
            res.errores.append(
                f"doc_id {entrada.doc_id} del mapa no existe en el manifiesto de "
                f"intake del expediente {expediente_id} (mapping obsoleto)"
            )
            continue
        origen_abs = raiz / "00_Input" / info["primary_path"]
        if not origen_abs.is_file():
            res.errores.append(
                f"falta en disco el origen de doc_id {entrada.doc_id}: "
                f"00_Input/{info['primary_path']}"
            )
            continue
        nombre = nombre_final(entrada.orden, entrada.descripcion, origen_abs.suffix)
        destino_rel = f"05_Procedimiento/{entrada.carpeta}/{nombre}"
        if destino_rel in deseado:
            res.errores.append(
                f"colisión de nombre final {nombre!r} en {entrada.carpeta!r}: "
                f"doc_id {deseado[destino_rel].doc_id} y {entrada.doc_id}"
            )
            continue
        deseado[destino_rel] = AccionCopiar(
            doc_id=entrada.doc_id,
            origen_rel=info["primary_path"],
            destino_rel=destino_rel,
            sha256=info["sha256"],
        )

    # 3. Diff contra el manifiesto procesal (lo que apply creó la vez anterior).
    previo = _leer_manifiesto_procesal(case_id)
    previo_por_doc = {v.get("doc_id"): k for k, v in previo.items()}

    for destino_rel, accion in deseado.items():
        anterior = previo_por_doc.get(accion.doc_id)
        if anterior == destino_rel and (raiz / destino_rel).is_file():
            continue                      # ya está en su sitio: no-op
        if anterior and anterior != destino_rel:
            res.mover.append(AccionMover(accion.doc_id, anterior, destino_rel))
        else:
            res.copiar.append(accion)

    for destino_rel, meta in previo.items():
        if destino_rel not in deseado and meta.get("doc_id") not in {
            a.doc_id for a in res.mover
        }:
            res.borrar.append(AccionBorrar(destino_rel))

    # 4. Ficheros ajenos dentro de las cinco carpetas: se reportan, no se tocan.
    for carpeta in CARPETAS_PROCESALES:
        base = raiz / "05_Procedimiento" / carpeta
        if not base.is_dir():
            continue
        for f in sorted(base.rglob("*")):
            if not f.is_file():
                continue
            rel = f.relative_to(raiz).as_posix()
            if rel not in previo and rel not in deseado:
                res.ajenos.append(rel)

    return res
```

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `python -m pytest tests/test_procedimiento.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/procedimiento.py tests/test_procedimiento.py
git commit -m "feat(procedimiento): plan() calcula el diff con sus cuatro puertas de fallo"
```

---

### Task 6: `apply()` y el manifiesto procesal

**Files:**
- Modify: `core/procedimiento.py`
- Test: `tests/test_procedimiento.py`

**Interfaces:**
- Consumes: `PlanProcesal` (Task 5).
- Produces:
  - `@dataclass ResultadoProcesal(copiados: int, movidos: int, borrados: int, manifiesto: Path | None, errores: list[str])`
  - `apply(plan_: PlanProcesal) -> ResultadoProcesal`
  - `AplicacionBloqueadaError(Exception)`

- [ ] **Step 1: Escribir los tests que fallan**

```python
from core.procedimiento import AplicacionBloqueadaError, apply as aplicar


def test_apply_copia_y_escribe_manifiesto(caso):
    from core.config import caso_path
    _sembrar(caso, [("33428", "05_CRM/03_Monitorio_Demanda/demanda.pdf", "x", None)])
    guardar_mapa(caso, MapaProcesal(
        version=1, expediente_crm="487",
        entradas=[EntradaMapa("33428", P0, "00", "demanda_monitorio")], sin_asignar=[]))
    r = aplicar(plan(caso, "487"))
    assert r.copiados == 1
    destino = caso_path(caso) / "05_Procedimiento" / P0 / "00_demanda_monitorio.pdf"
    assert destino.read_bytes() == b"x"
    assert r.manifiesto.is_file()


def test_apply_es_idempotente(caso):
    _sembrar(caso, [("33428", "05_CRM/03_Monitorio_Demanda/demanda.pdf", "x", None)])
    guardar_mapa(caso, MapaProcesal(
        version=1, expediente_crm="487",
        entradas=[EntradaMapa("33428", P0, "00", "demanda_monitorio")], sin_asignar=[]))
    aplicar(plan(caso, "487"))
    r2 = aplicar(plan(caso, "487"))
    assert (r2.copiados, r2.movidos, r2.borrados) == (0, 0, 0)


def test_apply_no_toca_ficheros_ajenos_ni_jurisprudencia(caso):
    from core.config import caso_path
    raiz = caso_path(caso)
    ajeno = raiz / "05_Procedimiento" / P0 / "NOTA_DEL_LETRADO.docx"
    ajeno.parent.mkdir(parents=True, exist_ok=True)
    ajeno.write_text("mio", encoding="utf-8")
    juris = raiz / "05_Procedimiento" / "Jurisprudencia" / "STS_123.pdf"
    juris.parent.mkdir(parents=True, exist_ok=True)
    juris.write_text("sts", encoding="utf-8")

    _sembrar(caso, [("33428", "05_CRM/03_Monitorio_Demanda/demanda.pdf", "x", None)])
    guardar_mapa(caso, MapaProcesal(
        version=1, expediente_crm="487",
        entradas=[EntradaMapa("33428", P0, "00", "demanda_monitorio")], sin_asignar=[]))
    p = plan(caso, "487")
    assert "05_Procedimiento/01_Monitorio - Demanda y documentos/NOTA_DEL_LETRADO.docx" in p.ajenos
    aplicar(p)
    assert ajeno.read_text(encoding="utf-8") == "mio"
    assert juris.read_text(encoding="utf-8") == "sts"


def test_apply_mueve_cuando_cambia_la_carpeta_en_el_mapa(caso):
    """Cambiar la asignación reubica el fichero; no deja copia en la carpeta vieja."""
    from core.config import caso_path
    _sembrar(caso, [("36142", "05_CRM/99_Otros/oposicion.pdf", "x", None)])
    guardar_mapa(caso, MapaProcesal(
        version=1, expediente_crm="487",
        entradas=[EntradaMapa("36142", CARPETA_OTROS, "2025-11-03", "oposicion")],
        sin_asignar=[]))
    aplicar(plan(caso, "487"))
    vieja = caso_path(caso) / "05_Procedimiento" / CARPETA_OTROS / "2025-11-03_oposicion.pdf"
    assert vieja.is_file()

    guardar_mapa(caso, MapaProcesal(
        version=1, expediente_crm="487",
        entradas=[EntradaMapa("36142", CARPETAS_PROCESALES[1], "00", "oposicion_monitorio")],
        sin_asignar=[]))
    r = aplicar(plan(caso, "487"))
    assert r.movidos == 1
    assert not vieja.exists()
    nueva = (caso_path(caso) / "05_Procedimiento" / CARPETAS_PROCESALES[1]
             / "00_oposicion_monitorio.pdf")
    assert nueva.read_bytes() == b"x"


def test_retirar_un_doc_del_mapa_lo_deja_sin_asignar_y_bloquea(caso):
    """Quitarlo del mapa no lo borra: vuelve a ser una decisión pendiente."""
    _sembrar(caso, [("33428", "05_CRM/03_Monitorio_Demanda/demanda.pdf", "x", None)])
    guardar_mapa(caso, MapaProcesal(
        version=1, expediente_crm="487",
        entradas=[EntradaMapa("33428", P0, "00", "demanda_monitorio")], sin_asignar=[]))
    aplicar(plan(caso, "487"))
    guardar_mapa(caso, MapaProcesal(version=1, expediente_crm="487",
                                    entradas=[], sin_asignar=[]))
    with pytest.raises(AplicacionBloqueadaError, match="sin asignar"):
        aplicar(plan(caso, "487"))


def test_apply_se_niega_si_hay_sin_asignar(caso):
    _sembrar(caso, [("41219", "05_CRM/99_Otros/justif.pdf", "y", None)])
    guardar_mapa(caso, MapaProcesal(version=1, expediente_crm="487",
                                    entradas=[], sin_asignar=[]))
    with pytest.raises(AplicacionBloqueadaError, match="sin asignar"):
        aplicar(plan(caso, "487"))
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `python -m pytest tests/test_procedimiento.py -k apply -v`
Expected: FAIL con `ImportError: cannot import name 'apply'`.

- [ ] **Step 3: Implementar**

```python
import shutil

from core.utils import now_iso


class AplicacionBloqueadaError(Exception):
    """El plan no está en condiciones de aplicarse."""


@dataclass
class ResultadoProcesal:
    copiados: int = 0
    movidos: int = 0
    borrados: int = 0
    manifiesto: Path | None = None
    errores: list[str] = field(default_factory=list)


def apply(plan_: PlanProcesal) -> ResultadoProcesal:
    """Ejecuta el plan y reescribe ``_MANIFIESTO_PROCESAL.json``.

    Raises:
        AplicacionBloqueadaError: si el plan tiene errores o decisiones
            pendientes del letrado (``sin_asignar`` no vacío).
    """
    if plan_.sin_asignar:
        raise AplicacionBloqueadaError(
            f"{len(plan_.sin_asignar)} documento(s) sin asignar en el mapa: "
            + ", ".join(d.doc_id for d in plan_.sin_asignar)
            + f". Asígnalos en {MAPA_REL} y vuelve a ejecutar."
        )
    if plan_.errores:
        raise AplicacionBloqueadaError(
            "El plan tiene errores:\n  - " + "\n  - ".join(plan_.errores)
        )

    raiz = caso_path(plan_.case_id)
    res = ResultadoProcesal()
    ficheros: dict[str, dict] = _leer_manifiesto_procesal(plan_.case_id)

    for accion in plan_.borrar:
        destino = raiz / accion.destino_rel
        if destino.is_file():
            destino.unlink()
        ficheros.pop(accion.destino_rel, None)
        res.borrados += 1

    for mov in plan_.mover:
        desde, hasta = raiz / mov.desde_rel, raiz / mov.hasta_rel
        hasta.parent.mkdir(parents=True, exist_ok=True)
        if desde.is_file():
            shutil.move(str(desde), str(hasta))
        meta = ficheros.pop(mov.desde_rel, {"doc_id": mov.doc_id})
        ficheros[mov.hasta_rel] = meta
        res.movidos += 1

    for cop in plan_.copiar:
        origen = raiz / "00_Input" / cop.origen_rel
        destino = raiz / cop.destino_rel
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(origen), str(destino))
        ficheros[cop.destino_rel] = {
            "doc_id": cop.doc_id, "sha256": cop.sha256, "origen_rel": cop.origen_rel,
        }
        res.copiados += 1

    ruta = raiz / MANIFIESTO_REL
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(
        json.dumps({"generado": now_iso(), "version": 1,
                    "expediente_crm": plan_.expediente_id,
                    "ficheros": ficheros},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    res.manifiesto = ruta
    return res
```

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `python -m pytest tests/test_procedimiento.py -v`
Expected: PASS.

- [ ] **Step 5: Suite completa y commit**

Run: `python -m pytest -q --tb=no`
Expected: 0 failed.

```bash
git add core/procedimiento.py tests/test_procedimiento.py
git commit -m "feat(procedimiento): apply() acotado por su propio manifiesto"
```

---

### Task 7: CLI `scripts/procedimiento.py`

**Files:**
- Create: `scripts/procedimiento.py`
- Test: `tests/test_procedimiento_cli.py`

**Interfaces:**
- Consumes: `plan`, `apply`, `guardar_mapa`, `MapaProcesal`, `DocPendiente` del core.
- Produces: comandos `plan` y `apply`. `plan --escribir-mapa` siembra el YAML con todo en `sin_asignar` la primera vez.

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/test_procedimiento_cli.py`:

```python
from typer.testing import CliRunner

from scripts.procedimiento import app

runner = CliRunner()


def test_plan_lista_sin_asignar_y_sale_con_codigo_1(caso_sembrado):
    r = runner.invoke(app, ["plan", "--case", caso_sembrado, "--expediente", "487"])
    assert r.exit_code == 1
    assert "sin asignar" in r.stdout.lower()


def test_plan_escribir_mapa_siembra_el_yaml(caso_sembrado):
    from core.procedimiento import cargar_mapa
    r = runner.invoke(app, ["plan", "--case", caso_sembrado, "--expediente", "487",
                            "--escribir-mapa"])
    assert r.exit_code == 1          # sigue habiendo decisiones pendientes
    mapa = cargar_mapa(caso_sembrado)
    assert [d.doc_id for d in mapa.sin_asignar] == ["33428"]


def test_apply_sin_mapa_completo_sale_con_error(caso_sembrado):
    r = runner.invoke(app, ["apply", "--case", caso_sembrado, "--expediente", "487"])
    assert r.exit_code == 2
    assert "sin asignar" in r.stdout.lower()
```

Con la fixture, en el mismo fichero:

```python
import pytest


@pytest.fixture
def caso_sembrado(tmp_path, monkeypatch):
    from core import config
    from core.intake_manifest import IntakeManifest, compute_sha256_bytes
    monkeypatch.setattr(config.settings, "casos_root", tmp_path)
    d = tmp_path / "CASO"
    (d / "00_Input/05_CRM/03_Monitorio_Demanda").mkdir(parents=True)
    (d / "05_Procedimiento").mkdir(parents=True)
    rel = "05_CRM/03_Monitorio_Demanda/demanda.pdf"
    (d / "00_Input" / rel).write_bytes(b"x")
    m = IntakeManifest("CASO")
    m.load()
    m.register(compute_sha256_bytes(b"x"), rel, source="crm",
               expediente_id="487", doc_id="33428",
               modified_at="2025-04-01T12:38:01.000+02:00")
    m.save()
    return "CASO"
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `python -m pytest tests/test_procedimiento_cli.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'scripts.procedimiento'`.

- [ ] **Step 3: Implementar el CLI**

Crear `scripts/procedimiento.py`:

```python
"""CLI de la vista procesal: construye 05_Procedimiento desde el mapa del letrado.

    python -m scripts.procedimiento plan  --case "<case_id>" --expediente 487
    python -m scripts.procedimiento plan  --case "<case_id>" --expediente 487 --escribir-mapa
    python -m scripts.procedimiento apply --case "<case_id>" --expediente 487

Códigos de salida: 0 nada pendiente · 1 hay decisiones o cambios por aplicar ·
2 `apply` bloqueado.
"""
from __future__ import annotations

import typer

from core.procedimiento import (
    AplicacionBloqueadaError,
    MapaProcesal,
    apply as aplicar_plan,
    cargar_mapa,
    guardar_mapa,
    plan as calcular_plan,
)

app = typer.Typer(help="Vista procesal del expediente en 05_Procedimiento.")


def _informe(p) -> None:
    for accion in p.copiar:
        typer.echo(f"  + copiar  {accion.destino_rel}")
    for accion in p.mover:
        typer.echo(f"  ~ mover   {accion.desde_rel} -> {accion.hasta_rel}")
    for accion in p.borrar:
        typer.echo(f"  - borrar  {accion.destino_rel}")
    for ajeno in p.ajenos:
        typer.echo(f"  · ajeno (no se toca)  {ajeno}")
    if p.sin_asignar:
        typer.echo(f"\n📋 {len(p.sin_asignar)} documento(s) sin asignar:")
        for d in p.sin_asignar:
            typer.echo(f"     {d.doc_id}  {d.lote}  {d.fichero}")
    for err in p.errores:
        typer.echo(f"  ❌ {err}")


@app.command("plan")
def cmd_plan(
    case: str = typer.Option(..., "--case"),
    expediente: str = typer.Option(..., "--expediente"),
    escribir_mapa: bool = typer.Option(
        False, "--escribir-mapa/--no-escribir-mapa",
        help="Siembra o actualiza el bloque sin_asignar del _mapa_procesal.yaml."),
) -> None:
    """Muestra el diff. No escribe nada salvo con --escribir-mapa."""
    p = calcular_plan(case, expediente)
    _informe(p)

    if escribir_mapa:
        actual = cargar_mapa(case) or MapaProcesal(version=1, expediente_crm=str(expediente))
        actual.sin_asignar = p.sin_asignar
        ruta = guardar_mapa(case, actual)
        typer.echo(f"\n✍️  mapa actualizado: {ruta}")

    pendiente = bool(p.copiar or p.mover or p.borrar or p.sin_asignar or p.errores)
    raise typer.Exit(code=1 if pendiente else 0)


@app.command("apply")
def cmd_apply(
    case: str = typer.Option(..., "--case"),
    expediente: str = typer.Option(..., "--expediente"),
) -> None:
    """Aplica el plan. Se niega si hay decisiones pendientes o errores."""
    p = calcular_plan(case, expediente)
    try:
        r = aplicar_plan(p)
    except AplicacionBloqueadaError as exc:
        typer.echo(f"⛔ {exc}")
        raise typer.Exit(code=2)
    typer.echo(
        f"✓ {r.copiados} copiados, {r.movidos} movidos, {r.borrados} borrados. "
        f"Manifiesto: {r.manifiesto}"
    )
    if p.ajenos:
        typer.echo(f"  · {len(p.ajenos)} fichero(s) ajeno(s) intactos.")


if __name__ == "__main__":
    app()
```

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `python -m pytest tests/test_procedimiento_cli.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/procedimiento.py tests/test_procedimiento_cli.py
git commit -m "feat(procedimiento): CLI plan/apply"
```

---

### Task 8: Regresión con el mapping real del expediente 487

Blinda la casuística que motivó el diseño: dos procedimientos, un cajón «CIVIL» con 38 documentos, un duplicado byte-idéntico y un fallback sin mapear.

**Files:**
- Create: `tests/fixtures/procedimiento_487.json`
- Create: `tests/test_procedimiento_487.py`

**Interfaces:**
- Consumes: todo lo anterior.
- Produces: nada que consuman otras tareas.

- [ ] **Step 1: Generar la fixture desde el dump real**

El dump y la asignación aprobada viven en el scratchpad de la sesión del 2026-07-27:
`gdocu_487.tsv` (70 filas: `doc_id`, `id_carpeta`, `id_carpeta_label`, `bucket`, `kind`,
`modified_at`, `filename`) y `propuesta_487.py` (los conjuntos de `doc_id` por carpeta,
aprobados por Nikolai). Conversión:

```python
# scratchpad/generar_fixture_487.py — de un solo uso, no va al repo.
import json
from pathlib import Path

TSV = Path("gdocu_487.tsv")
DESTINO = Path("tests/fixtures/procedimiento_487.json")

# Conjuntos aprobados el 2026-07-27 (mismos que propuesta_487.py).
MONITORIO_DDA = {"33382", "33428", "33432", "33433", "33434", "33435", "33436",
                 "33437", "33438"}
MONITORIO_OPO = {"36142", "36143", "36144", "36145", "39885"}
ORDINARIO_CONT = {"40719", "40720", "40721", "40722", "40723", "40724", "40725",
                  "40726", "40727", "40728", "40729", "40730"}

def carpeta_de(doc_id: str, id_carpeta: str) -> str:
    if doc_id in MONITORIO_DDA:
        return "01_Monitorio - Demanda y documentos"
    if doc_id in MONITORIO_OPO:
        return "02_Monitorio - Oposicion"
    if id_carpeta == "307":
        return "03_Ordinario - Demanda y documentos"
    if doc_id in ORDINARIO_CONT:
        return "04_Ordinario - Contestacion"
    return "05_Otros escritos"

filas = []
for linea in TSV.read_text(encoding="utf-8").splitlines():
    if not linea or linea.startswith("#") or linea.startswith("doc_id\t"):
        continue
    p = linea.split("\t")
    if len(p) < 7:
        continue
    filas.append({"doc_id": p[0], "filename": p[6], "id_carpeta": p[1],
                  "modified_at": p[5],
                  "carpeta_destino": carpeta_de(p[0], p[1])})

assert len(filas) == 70, len(filas)
assert len({f["doc_id"] for f in filas}) == 70
DESTINO.parent.mkdir(parents=True, exist_ok=True)
DESTINO.write_text(json.dumps(filas, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"{len(filas)} documentos -> {DESTINO}")
```

**Revisión de PII antes de commitear la fixture.** Los nombres son de documentos procesales,
no de personas físicas, pero hay al menos uno que incluye el nombre de pila de una persona
(`DOC 10 CORREOS RAQUEL ARAPDIS.pdf`). Sustituir esos casos por `<PARTICULAR>` en el campo
`filename` de la fixture antes de `git add`. `pre-commit` (hook `leak-guard`) es la red, no el
criterio: revisar las 70 filas a ojo.

Formato resultante:

```json
[{"doc_id": "33428", "filename": "DEMANDA_MONITORIO_-_COMPRADOR.pdf",
  "id_carpeta": "304", "modified_at": "2025-04-01T12:38:01.000+02:00",
  "carpeta_destino": "01_Monitorio - Demanda y documentos"}]
```

`carpeta_destino` es la asignación aprobada por el letrado el 2026-07-27.

- [ ] **Step 2: Escribir el test que falla**

```python
import json
from pathlib import Path

import pytest

FIXTURE = Path(__file__).parent / "fixtures" / "procedimiento_487.json"
REPARTO_ESPERADO = {
    "01_Monitorio - Demanda y documentos": 9,
    "02_Monitorio - Oposicion": 5,
    "03_Ordinario - Demanda y documentos": 15,
    "04_Ordinario - Contestacion": 12,
    "05_Otros escritos": 29,
}


def test_la_fixture_cubre_los_70_documentos_una_sola_vez():
    docs = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert len(docs) == 70
    assert len({d["doc_id"] for d in docs}) == 70


def test_el_reparto_por_carpeta_es_el_aprobado():
    docs = json.loads(FIXTURE.read_text(encoding="utf-8"))
    reparto = {}
    for d in docs:
        reparto[d["carpeta_destino"]] = reparto.get(d["carpeta_destino"], 0) + 1
    assert reparto == REPARTO_ESPERADO


def test_plan_y_apply_reproducen_el_reparto(caso_487):
    from core.procedimiento import CARPETAS_PROCESALES, apply, plan
    from core.config import caso_path
    p = plan(caso_487, "487")
    assert p.errores == []
    assert p.sin_asignar == []
    apply(p)
    raiz = caso_path(caso_487) / "05_Procedimiento"
    real = {c: len(list((raiz / c).glob("*"))) for c in CARPETAS_PROCESALES}
    assert real == REPARTO_ESPERADO
```

Y la fixture, en el mismo fichero:

```python
@pytest.fixture
def caso_487(tmp_path, monkeypatch):
    """Reconstruye el expediente 487 sintético: 70 docs, manifiesto y mapa completo."""
    from core import config
    from core.intake_manifest import IntakeManifest, compute_sha256_bytes
    from core.procedimiento import (
        EntradaMapa, MapaProcesal, guardar_mapa,
        proponer_descripcion, proponer_orden,
    )
    monkeypatch.setattr(config.settings, "casos_root", tmp_path)
    raiz = tmp_path / "CASO487"
    (raiz / "00_Input").mkdir(parents=True)
    (raiz / "05_Procedimiento").mkdir(parents=True)

    docs = json.loads(FIXTURE.read_text(encoding="utf-8"))
    m = IntakeManifest("CASO487")
    m.load()
    entradas = []
    for d in docs:
        # Los dos TASA ORDINARIO comparten contenido: reproduce el byte-idéntico
        # que en el caso real deja 70 doc_id sobre 69 ficheros físicos.
        contenido = ("TASA" if "TASA ORDINARIO" in d["filename"] else d["doc_id"])
        data = contenido.encode("utf-8")
        rel = f"05_CRM/99_Otros/{d['doc_id']}_{Path(d['filename']).stem[:20]}.pdf"
        p = raiz / "00_Input" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        m.register(compute_sha256_bytes(data), rel, source="crm",
                   expediente_id="487", doc_id=d["doc_id"],
                   modified_at=d["modified_at"])
        entradas.append(EntradaMapa(
            doc_id=d["doc_id"],
            carpeta=d["carpeta_destino"],
            orden=proponer_orden(d["filename"], d["carpeta_destino"], d["modified_at"]),
            descripcion=proponer_descripcion(d["filename"]),
        ))
    m.save()
    guardar_mapa("CASO487", MapaProcesal(
        version=1, expediente_crm="487", entradas=entradas, sin_asignar=[]))
    return "CASO487"
```

> **Sobre el byte-idéntico:** los dos `TASA ORDINARIO` comparten SHA, así que el segundo `register` devuelve `("skip", primary)` y su `doc_id` queda como alias. `lookup_doc_id` debe resolverlo igualmente al `primary_path` (Task 1) — este test lo verifica de paso. Sus `orden` difieren (fechas de lote 2026-02-11 y 2026-03-23), así que producen dos nombres finales distintos y **no** disparan la puerta 3: la carpeta acaba con dos copias, que es el reflejo fiel de dos presentaciones.

- [ ] **Step 3: Ejecutar y verificar que falla**

Run: `python -m pytest tests/test_procedimiento_487.py -v`
Expected: FAIL — la fixture aún no existe o el reparto no cuadra.

- [ ] **Step 4: Ajustar hasta verde**

Si el reparto real no da 9/5/15/12/29, el fallo está en la fixture o en el mapa, no en el código: revisar contra `propuesta_487.txt`. Si salta una colisión de nombre final, es legítima (los dos `TASA ORDINARIO`, la segunda copia de la oposición): desambiguar en el mapa con `orden` distinto, que es exactamente lo que la puerta 3 pide al letrado.

- [ ] **Step 5: Ejecutar y verificar que pasa**

Run: `python -m pytest tests/test_procedimiento_487.py -v`
Expected: PASS, 3 tests.

- [ ] **Step 6: Suite completa y commit**

Run: `python -m pytest -q --tb=no`
Expected: 0 failed.

```bash
git add tests/fixtures/procedimiento_487.json tests/test_procedimiento_487.py
git commit -m "test(procedimiento): regresion con el reparto real del expediente 487"
```

---

## Cierre

Al terminar las ocho tareas:

- Abrir PR contra `main` (protegida; el check `leak-scan` debe pasar).
- `PLAN.md`: entrada `[SIGUIENTE-VISTA-PROCESAL]` con `✅` y el hash del PR en `## Cerrados`.
- `docs/MEJORAS_FUTURAS.md`: los dos hallazgos colaterales del spec §8 que no se resuelven aquí —el pull state que se pierde durante un checkout, y el `id_carpeta` 304 pendiente de doble verificación en la UI.
- `docs/ARQUITECTURA.md`: añadir `core/procedimiento.py` a la tabla de módulos y sus consumidores.
