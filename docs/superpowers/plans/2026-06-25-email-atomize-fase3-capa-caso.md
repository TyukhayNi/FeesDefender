# Email-atomize Fase 3 (capa de caso) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sacar las identidades del caso del código a `identidades.yaml`/`vistas.yaml` curados, generar vistas temáticas (`dossier_persona_vigilada`, `nexo_causal`) de solo-lectura y sellar entregas con manifiesto de hashes — manteniendo el motor genérico y los 277 Capa A byte-idénticos.

**Architecture:** Capa de caso sobre el motor congelado `core/email_atomize/`. Dos ficheros YAML curados en la raíz del caso (sin ellos = genérico). Tres módulos nuevos (`identidades.py`, `vistas.py`, `entregas.py`) + inyección de `Identidades` por el pipeline (sin estado global). Vistas y entregas son ficheros nuevos en subdirectorios nuevos → no alteran bytes existentes.

**Tech Stack:** Python 3.14, PyYAML (`yaml.safe_load`), `pytest`, stdlib (`shutil`, `subprocess`, `datetime`, `hashlib`). Spec: `docs/superpowers/specs/2026-06-25-email-atomize-fase3-capa-caso-design.md`.

**Reglas duras (verificar tras cada tarea):**
- 277 `.md` de Capa A BYTE-IDÉNTICOS; IDs congelados; cero misatribución; lo del caso SOLO por config.
- Working tree compartido: commits acotados a ficheros propios (NO `git add -A`); NO commitear `PLAN.md`/`CLAUDE.md`; hay post-commit hook que auto-pushea `main`.
- Suite: `python -m pytest -q --tb=no --ignore=tests/test_email_export_mcp_server.py --ignore=tests/test_expedientes_xl_server.py`
- PowerShell: pytest NO expande globs → pasar rutas explícitas o `-k`. Para leer `G:` usar `dangerouslyDisableSandbox` solo en lecturas; commits con cuerpo largo vía `git commit -F`.

---

## Task 1: Módulo `identidades.py` (registro de actores)

**Files:**
- Create: `core/email_atomize/identidades.py`
- Test: `tests/test_email_atomize_identidades.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_email_atomize_identidades.py
from __future__ import annotations

import pytest

from core.email_atomize import identidades as ID


_YAML_PILOTO = """
version: 1
caso: "W-02VND1"
personas:
  - id: persona_uno
    nombre: "PersonaUno"
    vigilada: true
    rol: "tesis: administrador de hecho"
    direcciones:
      - { email: per01a@example.invalid,            estado: confirmada }
      - { email: per01c@example.invalid,                 estado: confirmada }
      - { email: per01b@example.invalid,  estado: candidata }
  - id: persona_dos
    nombre: "PersonaDos"
    vigilada: false
    direcciones:
      - { email: ignacio@despacho-ab.example, estado: confirmada }
    notas: "PERSONA DISTINTA — nunca fundir."
"""


def test_carga_piloto_sets_derivados(tmp_path):
    (tmp_path / "identidades.yaml").write_text(_YAML_PILOTO, encoding="utf-8")
    ident = ID.cargar_identidades(tmp_path)
    # vigiladas = confirmadas de personas vigiladas (email en minúsculas)
    assert ident.vigiladas == frozenset({"per01a@example.invalid", "per01c@example.invalid"})
    # candidatas = estado candidata
    assert ident.candidatas == frozenset({"per01b@example.invalid"})
    # Ignacio NO es vigilado → su email no entra en vigiladas
    assert "ignacio@despacho-ab.example" not in ident.vigiladas


def test_unificacion_y_persona_distinta(tmp_path):
    (tmp_path / "identidades.yaml").write_text(_YAML_PILOTO, encoding="utf-8")
    ident = ID.cargar_identidades(tmp_path)
    # unificación: las 3 direcciones cuelgan de la misma persona
    assert ident.persona_de("per01a@example.invalid") == "persona_uno"
    assert ident.persona_de("per01c@example.invalid") == "persona_uno"
    assert ident.persona_de("per01b@example.invalid") == "persona_uno"
    # persona DISTINTA: nunca se funde con PersonaUno
    assert ident.persona_de("ignacio@despacho-ab.example") == "persona_dos"
    assert ident.estado_de("per01b@example.invalid") == "candidata"


def test_sin_fichero_es_generico(tmp_path):
    ident = ID.cargar_identidades(tmp_path)   # no hay identidades.yaml
    assert ident.vigiladas == frozenset()
    assert ident.candidatas == frozenset()
    assert ident.persona_de("per01a@example.invalid") is None


def test_email_en_dos_personas_es_error(tmp_path):
    yml = """
personas:
  - id: a
    vigilada: false
    direcciones: [ { email: x@y.com, estado: confirmada } ]
  - id: b
    vigilada: false
    direcciones: [ { email: x@y.com, estado: confirmada } ]
"""
    (tmp_path / "identidades.yaml").write_text(yml, encoding="utf-8")
    with pytest.raises(ValueError):
        ID.cargar_identidades(tmp_path)


def test_estado_invalido_es_error(tmp_path):
    yml = """
personas:
  - id: a
    vigilada: true
    direcciones: [ { email: x@y.com, estado: dudosa } ]
"""
    (tmp_path / "identidades.yaml").write_text(yml, encoding="utf-8")
    with pytest.raises(ValueError):
        ID.cargar_identidades(tmp_path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_email_atomize_identidades.py -q --tb=short`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.email_atomize.identidades'`

- [ ] **Step 3: Write minimal implementation**

```python
# core/email_atomize/identidades.py
"""Capa de caso: registro de actores (identidades.yaml). El motor SOLO lee este fichero.

Sin identidades.yaml en la raíz del caso → Identidades() vacío = comportamiento genérico.
Diseño: docs/superpowers/specs/2026-06-25-email-atomize-fase3-capa-caso-design.md §4.1, §5.1.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

_ESTADOS = {"confirmada", "candidata"}


@dataclass
class Persona:
    id: str
    nombre: str = ""
    vigilada: bool = False
    direcciones: list[tuple[str, str]] = field(default_factory=list)  # (email_lower, estado)
    rol: str = ""
    notas: str = ""

    def emails(self) -> set[str]:
        return {e for e, _estado in self.direcciones}


@dataclass
class Identidades:
    vigiladas: frozenset[str] = frozenset()
    candidatas: frozenset[str] = frozenset()
    personas: dict[str, Persona] = field(default_factory=dict)
    _por_email: dict[str, str] = field(default_factory=dict)

    def persona_de(self, email: str) -> str | None:
        return self._por_email.get((email or "").strip().lower())

    def persona(self, persona_id: str) -> Persona | None:
        return self.personas.get(persona_id)

    def estado_de(self, email: str) -> str:
        e = (email or "").strip().lower()
        pid = self._por_email.get(e)
        if not pid:
            return ""
        for addr, estado in self.personas[pid].direcciones:
            if addr == e:
                return estado
        return ""


def desde_dict(data: dict) -> Identidades:
    """Construye Identidades desde un dict ya parseado. Valida invariantes (§4.1)."""
    personas: dict[str, Persona] = {}
    por_email: dict[str, str] = {}
    vigiladas: set[str] = set()
    candidatas: set[str] = set()
    for raw in (data or {}).get("personas", []) or []:
        pid = str(raw.get("id") or "").strip()
        if not pid:
            raise ValueError("identidades.yaml: persona sin 'id'")
        if pid in personas:
            raise ValueError(f"identidades.yaml: id duplicado {pid!r}")
        vigilada = bool(raw.get("vigilada", False))
        direcciones: list[tuple[str, str]] = []
        for d in raw.get("direcciones", []) or []:
            email = str(d.get("email") or "").strip().lower()
            estado = str(d.get("estado") or "").strip().lower()
            if not email:
                raise ValueError(f"identidades.yaml: dirección sin email en {pid!r}")
            if estado not in _ESTADOS:
                raise ValueError(
                    f"identidades.yaml: estado inválido {estado!r} en {email} ({pid!r})")
            if email in por_email and por_email[email] != pid:
                raise ValueError(
                    f"identidades.yaml: email {email} en dos personas "
                    f"({por_email[email]!r} y {pid!r})")
            por_email[email] = pid
            direcciones.append((email, estado))
            if estado == "candidata":
                candidatas.add(email)
            elif estado == "confirmada" and vigilada:
                vigiladas.add(email)
        personas[pid] = Persona(
            id=pid, nombre=str(raw.get("nombre") or ""), vigilada=vigilada,
            direcciones=direcciones, rol=str(raw.get("rol") or ""),
            notas=str(raw.get("notas") or ""))
    return Identidades(vigiladas=frozenset(vigiladas), candidatas=frozenset(candidatas),
                       personas=personas, _por_email=por_email)


def cargar_identidades(case_dir: Path | str) -> Identidades:
    """Lee <case_dir>/identidades.yaml. Sin fichero → Identidades() vacío (genérico)."""
    path = Path(case_dir) / "identidades.yaml"
    if not path.exists():
        return Identidades()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return desde_dict(data)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_email_atomize_identidades.py -q --tb=short`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add core/email_atomize/identidades.py tests/test_email_atomize_identidades.py
git commit -m "feat(email-atomize): identidades.yaml — registro de actores del caso (F3 T1)"
```

---

## Task 2: Inyectar `Identidades` en el motor (quitar sets hardcodeados)

Mueve la consulta de identidades de variables module-level de `inline.py` a un objeto `Identidades` inyectado por el pipeline. Conducta idéntica cuando el caso aporta los mismos datos; genérica sin YAML. Migra los 5 tests que dependían de los sets hardcodeados (cambio correcto: de hardcodeado a config-driven).

**Files:**
- Modify: `core/email_atomize/inline.py` (quitar sets `IDENTIDADES_*`; `reconstruir` acepta `identidades`)
- Modify: `core/email_atomize/render.py:124-132` (`render_revision` default vacío en vez del set)
- Modify: `core/email_atomize/pipeline.py:54,83,110,117,127` (cargar+enhebrar `Identidades`)
- Modify (migración de tests):
  - `tests/test_email_atomize_inline.py:200-206`
  - `tests/test_email_atomize_render_b.py:30-37`
  - `tests/test_email_atomize_hardening.py:67-74`
  - `tests/test_email_atomize_pipeline_b.py:23-42`
  - `tests/test_email_atomize_regresion_b.py:20-28`

- [ ] **Step 1: Migrar los 5 tests al nuevo contrato (escribir primero — fallarán)**

En `tests/test_email_atomize_inline.py`, reemplazar `test_reconstruir_watched_va_a_identidades_vigiladas_queue` (líneas 200-206):

```python
def test_reconstruir_watched_va_a_identidades_vigiladas_queue():
    from core.email_atomize.identidades import Identidades
    ident = Identidades(vigiladas=frozenset({"per01a@example.invalid"}))
    raw = _eml_cita_gmail("x", "per01a@example.invalid", "1 de mayo de 2020",
                          "cuerpo largo de prueba suficiente para todo")
    res = I.reconstruir(_ra(), raw, ident)
    db = [s for s in res.candidatos if s.de == "per01a@example.invalid"]
    assert db and db[0].en_revision is True   # doble control sobre identidad vigilada
```

En `tests/test_email_atomize_render_b.py`, en `test_render_revision_tres_colas` (línea 34) cambiar la llamada:

```python
    out = R.render_revision(msgs_b, punteros, watched=frozenset({"per01a@example.invalid"}))
```

En `tests/test_email_atomize_hardening.py`, reemplazar `test_candidato_outlook_capped_media` (líneas 67-74):

```python
def test_candidato_outlook_capped_media():
    """per01b@example.invalid (candidato) NUNCA llega a alta; va a revisión."""
    from core.email_atomize.identidades import Identidades
    ident = Identidades(candidatas=frozenset({"per01b@example.invalid"}))
    res = I.reconstruir(_ra(fecha_iso="2026-06-01"),
                        _eml_gmail("per01b@example.invalid", "1 de mayo de 2020",
                                   "cuerpo largo de prueba suficiente para fingerprint"),
                        ident)
    assert all(s.de != "per01b@example.invalid" for s in res.candidatos)
    assert any(p.de == "per01b@example.invalid" and "candidata" in p.motivo
               for p in res.punteros)
```

En `tests/test_email_atomize_pipeline_b.py`, en `test_layerb_promueve_y_no_renumera_capaA` reemplazar las líneas 28 y 39 (las dos llamadas `P.atomize_dir(src, out)`) y añadir el YAML antes de la primera. El bloque 24-42 queda:

```python
    src = tmp_path / "03_Email"; out = tmp_path / "Emails"; src.mkdir()
    (tmp_path / "identidades.yaml").write_text(
        "personas:\n"
        "  - id: persona_uno\n"
        "    vigilada: true\n"
        "    direcciones: [ { email: per01a@example.invalid, estado: confirmada } ]\n",
        encoding="utf-8")
    (src / "2026-06-01_carrier.eml").write_bytes(_carrier_gmail(
        "<carrier@x>", "Te reenvío.", "per01a@example.invalid", "1 de mayo de 2020", "[inmueble]",
        "contenido citado suficientemente largo para superar el floor de 24"))
    rep = P.atomize_dir(src, out, case_dir=tmp_path)
    # Capa A: 1 portador; Capa B: 1 reconstruida (PersonaUno)
    mds = sorted((out / "mensajes").glob("*.md"))
    assert len(mds) == 2
    reg = json.loads((out / "_registro.json").read_text(encoding="utf-8"))
    assert reg["version"] == 2 and len(reg["mensajes_fp"]) == 1     # 1 fp-keyed B
    assert (out / "_revision" / "identidades_vigiladas.md").exists()
    db = (out / "_revision" / "identidades_vigiladas.md").read_text(encoding="utf-8")
    assert "per01a@example.invalid" in db
    assert rep.reconstruidos_b == 1
    # idempotencia: re-run no renumera ni duplica
    P.atomize_dir(src, out, case_dir=tmp_path)
    reg2 = json.loads((out / "_registro.json").read_text(encoding="utf-8"))
    assert reg2["mensajes_fp"] == reg["mensajes_fp"]
    assert len(sorted((out / "mensajes").glob("*.md"))) == 2
```

En `tests/test_email_atomize_regresion_b.py`, en `test_gmail_identidades_vigiladas_en_identidades_vigiladas_md` reemplazar el bloque 22-28:

```python
    src = tmp_path / "03_Email"; out = tmp_path / "Emails"; src.mkdir()
    (tmp_path / "identidades.yaml").write_text(
        "personas:\n"
        "  - id: persona_uno\n"
        "    vigilada: true\n"
        "    direcciones: [ { email: per01a@example.invalid, estado: confirmada } ]\n",
        encoding="utf-8")
    (src / "a.eml").write_bytes(_gmail(
        "<c@x>", "Te reenvío.", "per01a@example.invalid", "1 de mayo de 2020",
        "contenido citado suficientemente largo para fingerprint PersonaUno"))
    P.atomize_dir(src, out, case_dir=tmp_path)
    db = (out / "_revision" / "identidades_vigiladas.md").read_text(encoding="utf-8")
    assert "per01a@example.invalid" in db
```

- [ ] **Step 2: Run migrated tests to verify they fail (old code)**

Run: `python -m pytest tests/test_email_atomize_inline.py::test_reconstruir_watched_va_a_identidades_vigiladas_queue tests/test_email_atomize_pipeline_b.py::test_layerb_promueve_y_no_renumera_capaA -q --tb=short`
Expected: FAIL — `reconstruir()` aún no acepta 3er arg / `atomize_dir()` no acepta `case_dir`.

- [ ] **Step 3: Implementar el enhebrado**

En `core/email_atomize/inline.py`, **borrar** las líneas 22-33 (el bloque de comentario + `IDENTIDADES_VIGILADAS` + `IDENTIDADES_CANDIDATAS`) y añadir tras la línea `from .model import RegistroMensaje, SegmentoEnterrado`:

```python
from .identidades import Identidades
```

Cambiar la firma de `reconstruir` (línea ~670) y su cuerpo. Firma:

```python
def reconstruir(m_a, raw: bytes, identidades: "Identidades | None" = None) -> ReconResult:
    """Segmenta el portador, atribuye/clasifica cada cita y separa candidatos (alta) de
    punteros (media/baja → revisión). NO asigna MSG-id (eso lo hace el pipeline).

    ``identidades`` aporta las identidades del caso (vigiladas/candidatas). Sin él → genérico.
    """
    if identidades is None:
        identidades = Identidades()
```

Dentro de `reconstruir`, sustituir las dos consultas a los sets module-level:

```python
        # Identidad candidata (no confirmada) → nunca alta (decisión Nikolai).
        if conf == "alta-reconstruida" and anc and anc.de in identidades.candidatas:
            conf, motivo = "media", "identidad_candidata"
```

```python
        watched = bool(seg.de) and seg.de in identidades.vigiladas
```

En `core/email_atomize/render.py`, reemplazar el inicio de `render_revision` (líneas 124-132). Lo de hoy:

```python
def render_revision(mensajes_b: list[RegistroMensaje], punteros: list, watched=None,
                    upgrades: list | None = None) -> dict:
    """..."""
    if watched is None:
        from . import inline
        watched = inline.IDENTIDADES_VIGILADAS
    upgrades = upgrades or []
```

queda:

```python
def render_revision(mensajes_b: list[RegistroMensaje], punteros: list, watched=None,
                    upgrades: list | None = None) -> dict:
    """Colas de revisión Layer B: ``cola.md`` (punteros media/baja), ``casi_duplicados.md``
    (upgrades de fidelidad: cita inline resuelta a una copia limpia de Capa A), ``identidades_vigiladas.md``
    (autoría vigilada). Regenerado cada corrida (determinista → idempotente). ``watched`` =
    identidades vigiladas del caso; sin caso → vacío (identidades_vigiladas.md vacío)."""
    watched = frozenset(watched) if watched is not None else frozenset()
    upgrades = upgrades or []
```

En `core/email_atomize/pipeline.py`:
- Añadir junto a los imports (tras la línea `from . import inline as INL`):

```python
from . import identidades as ID
```

- Cambiar la firma de `atomize_dir` (línea 54):

```python
def atomize_dir(src_dir: Path | str, out_dir: Path | str, *,
                case_dir: Path | str | None = None) -> AtomizeReport:
```

- Tras `out = Path(out_dir)` (línea 56), añadir:

```python
    if case_dir is None:
        case_dir = out.parent.parent          # <caso>/01_Procesado/Emails → <caso>
    ident = ID.cargar_identidades(case_dir)
```

- Cambiar la llamada a `_pase_layer_b` (línea 83):

```python
    mensajes_b, punteros, upgrades = _pase_layer_b(reg, mensajes, carriers, report, ident)
```

- Cambiar la llamada a `render_revision` (línea 110) para pasar `watched`:

```python
    for nombre, contenido in R.render_revision(
            mensajes_b, punteros, watched=ident.vigiladas, upgrades=upgrades).items():
```

- Cambiar la firma de `_pase_layer_b` (línea 117) y la llamada a `reconstruir` (línea 127):

```python
def _pase_layer_b(reg, mensajes, carriers, report, identidades):
```

```python
            res = INL.reconstruir(m_a, raw, identidades)
```

- [ ] **Step 4: Run tests to verify they pass + suite verde**

Run: `python -m pytest tests/test_email_atomize_inline.py tests/test_email_atomize_render_b.py tests/test_email_atomize_hardening.py tests/test_email_atomize_pipeline_b.py tests/test_email_atomize_regresion_b.py -q --tb=short`
Expected: PASS (todos)

Run: `python -m pytest -q --tb=no --ignore=tests/test_email_export_mcp_server.py --ignore=tests/test_expedientes_xl_server.py`
Expected: exit 0, 58 skipped, 0 fallos

- [ ] **Step 5: Commit**

```bash
git add core/email_atomize/inline.py core/email_atomize/render.py core/email_atomize/pipeline.py tests/test_email_atomize_inline.py tests/test_email_atomize_render_b.py tests/test_email_atomize_hardening.py tests/test_email_atomize_pipeline_b.py tests/test_email_atomize_regresion_b.py
git commit -m "refactor(email-atomize): identidades por inyección, no hardcodeadas (F3 T2)"
```

---

## Task 3: Módulo `vistas.py` (vistas temáticas, función pura)

**Files:**
- Create: `core/email_atomize/vistas.py`
- Test: `tests/test_email_atomize_vistas.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_email_atomize_vistas.py
from __future__ import annotations

from core.email_atomize import vistas as V
from core.email_atomize.identidades import Identidades, Persona
from core.email_atomize.model import RegistroMensaje


def _m(msg_id, de="", para=None, cc=None, asunto="", cuerpo="", fecha="2024-05-01",
       hora="0900", capa="A", confianza="alta", reconstruido_de=""):
    return RegistroMensaje(
        msg_id=msg_id, de=de, para=para or [], cc=cc or [], asunto=asunto, cuerpo=cuerpo,
        fecha_iso=fecha, hora=hora, capa=capa, confianza=confianza,
        reconstruido_de=reconstruido_de)


def _ident_db():
    p = Persona(id="persona_uno", nombre="PersonaUno", vigilada=True,
                direcciones=[("per01a@example.invalid", "confirmada"),
                             ("per01b@example.invalid", "candidata")])
    ig = Persona(id="ignacio", nombre="Ignacio", vigilada=False,
                 direcciones=[("ignacio@despacho-ab.example", "confirmada")])
    return Identidades(
        vigiladas=frozenset({"per01a@example.invalid"}),
        candidatas=frozenset({"per01b@example.invalid"}),
        personas={"persona_uno": p, "ignacio": ig},
        _por_email={"per01a@example.invalid": "persona_uno",
                    "per01b@example.invalid": "persona_uno",
                    "ignacio@despacho-ab.example": "ignacio"})


def test_vista_persona_agrupa_autor_y_destinatario_no_a_ignacio():
    ident = _ident_db()
    mensajes = [
        _m("MSG-1", de="per01a@example.invalid", asunto="autor confirmada"),
        _m("MSG-2", de="otro@x.com", para=["per01b@example.invalid"], asunto="destino candidata"),
        _m("MSG-3", de="ignacio@despacho-ab.example", asunto="ignacio fuera"),
    ]
    d = V.DefVista(id="dossier_persona_vigilada", titulo="Dossier", tipo="persona",
                   persona="persona_uno")
    salidas, notas = V.render_vistas(mensajes, ident, [d])
    doc = salidas["dossier_persona_vigilada.md"]
    assert "MSG-1" in doc and "MSG-2" in doc       # autor + destinatario (candidata incluida)
    assert "MSG-3" not in doc                       # Ignacio NUNCA entra
    assert notas == []


def test_vista_tematica_keyword_incluye_excluye_rango():
    ident = _ident_db()
    mensajes = [
        _m("MSG-1", asunto="[inmueble] arras", fecha="2024-03-01"),     # keyword + en rango
        _m("MSG-2", cuerpo="hablamos del ENCARGO", fecha="2024-03-02"),  # keyword en cuerpo
        _m("MSG-3", asunto="nada que ver", fecha="2024-03-03"),       # sin keyword
        _m("MSG-4", asunto="[inmueble]", fecha="2025-01-01"),           # keyword pero fuera de rango
        _m("MSG-5", asunto="[inmueble]", fecha="2024-03-04"),           # keyword pero excluido
    ]
    d = V.DefVista(id="nexo_causal", titulo="Nexo", tipo="tematica",
                   palabras_clave=["inmueble", "encargo"],
                   incluye_msg=["MSG-3"], excluye_msg=["MSG-5"],
                   desde="2024-01-01", hasta="2024-12-31")
    salidas, _notas = V.render_vistas(mensajes, ident, [d])
    doc = salidas["nexo_causal.md"]
    assert "MSG-1" in doc and "MSG-2" in doc        # keyword en asunto y en cuerpo
    assert "MSG-3" in doc                            # incluye_msg fuerza dentro (sin keyword)
    assert "MSG-4" not in doc                         # fuera de rango
    assert "MSG-5" not in doc                         # excluye_msg fuerza fuera


def test_vista_persona_inexistente_se_omite_con_nota():
    ident = _ident_db()
    d = V.DefVista(id="rota", tipo="persona", persona="no_existe")
    salidas, notas = V.render_vistas([_m("MSG-1")], ident, [d])
    assert "rota.md" not in salidas
    assert any("no_existe" in n for n in notas)


def test_vista_tipo_desconocido_se_omite_con_nota():
    ident = _ident_db()
    d = V.DefVista(id="rara", tipo="quesoyo")
    salidas, notas = V.render_vistas([_m("MSG-1")], ident, [d])
    assert "rara.md" not in salidas
    assert any("quesoyo" in n for n in notas)


def test_cargar_vistas_sin_fichero_es_vacio(tmp_path):
    assert V.cargar_vistas(tmp_path) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_email_atomize_vistas.py -q --tb=short`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.email_atomize.vistas'`

- [ ] **Step 3: Write minimal implementation**

```python
# core/email_atomize/vistas.py
"""Capa de caso: vistas temáticas (vistas.yaml). Artefacto de SOLO-LECTURA: no muta ningún .md.

Diseño: spec §4.2, §5.2. ``render_vistas`` es función pura sobre la lista de RegistroMensaje
en memoria; devuelve ({fichero: contenido}, notas). Una vista inválida se omite con nota.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .identidades import Identidades
from .inline import _fold, normaliza_cuerpo
from .model import RegistroMensaje

_GEN = "<!-- GENERADO por core.email_atomize — NO editar a mano. -->\n"


@dataclass
class DefVista:
    id: str
    titulo: str = ""
    tipo: str = ""
    persona: str = ""
    palabras_clave: list[str] = field(default_factory=list)
    incluye_msg: list[str] = field(default_factory=list)
    excluye_msg: list[str] = field(default_factory=list)
    desde: str = ""
    hasta: str = ""


def cargar_vistas(case_dir: Path | str) -> list[DefVista]:
    """Lee <case_dir>/vistas.yaml. Sin fichero → [] (no se genera ninguna vista)."""
    path = Path(case_dir) / "vistas.yaml"
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    defs: list[DefVista] = []
    for raw in data.get("vistas", []) or []:
        defs.append(DefVista(
            id=str(raw.get("id") or ""), titulo=str(raw.get("titulo") or ""),
            tipo=str(raw.get("tipo") or ""), persona=str(raw.get("persona") or ""),
            palabras_clave=list(raw.get("palabras_clave") or []),
            incluye_msg=list(raw.get("incluye_msg") or []),
            excluye_msg=list(raw.get("excluye_msg") or []),
            desde=str(raw.get("desde") or ""), hasta=str(raw.get("hasta") or "")))
    return defs


def _orden(m: RegistroMensaje):
    return (m.fecha_iso, m.hora, m.msg_id)


def _seleccion_persona(mensajes, identidades, d):
    """Devuelve [(mensaje, rol, estado_dir)] o None si la persona no existe."""
    p = identidades.persona(d.persona)
    if p is None:
        return None
    emails = p.emails()
    filas = []
    for m in mensajes:
        autor = (m.de or "").lower() in emails
        dest = any(v in emails for v in m.para) or any(v in emails for v in m.cc)
        if not (autor or dest):
            continue
        if autor:
            email_match = (m.de or "").lower()
        else:
            email_match = next((v for v in list(m.para) + list(m.cc) if v in emails), "")
        filas.append((m, "autor" if autor else "destinatario",
                      identidades.estado_de(email_match)))
    filas.sort(key=lambda t: _orden(t[0]))
    return filas


def _seleccion_tematica(mensajes, d):
    kw = [_fold(k) for k in d.palabras_clave if k]
    inc, exc = set(d.incluye_msg), set(d.excluye_msg)
    out = []
    for m in mensajes:
        if m.msg_id in exc:          # excluye gana siempre
            continue
        if m.msg_id in inc:          # incluye fuerza dentro (bypassa keyword y rango)
            out.append(m)
            continue
        if d.desde and m.fecha_iso < d.desde:
            continue
        if d.hasta and m.fecha_iso > d.hasta:
            continue
        texto = _fold(m.asunto or "") + " " + normaliza_cuerpo(m.cuerpo or "")
        if kw and any(k in texto for k in kw):
            out.append(m)
    out.sort(key=_orden)
    return out


def _celda(s: str) -> str:
    return (s or "").replace("|", " ").replace("\n", " ").strip()


def _render_persona(d, p, filas):
    out = [_GEN, f"# {d.titulo or d.id} ({len(filas)} mensajes)\n",
           f"_Persona: {p.nombre} · vigilada: {'sí' if p.vigilada else 'no'} · "
           f"direcciones: {', '.join(sorted(p.emails()))}_\n",
           "| Fecha | Hora | Asunto | Ref | Rol | De | Capa | Confianza | Estado dir | Portador |",
           "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for m, rol, estado in filas:
        out.append(f"| {m.fecha_iso} | {m.hora or '----'} | {_celda(m.asunto) or '(sin asunto)'} "
                   f"| {m.msg_id} | {rol} | {m.de} | {m.capa} | {m.confianza} | {estado or '—'} "
                   f"| {m.reconstruido_de or '—'} |")
    return "\n".join(out) + "\n"


def _render_tematica(d, mensajes):
    out = [_GEN, f"# {d.titulo or d.id} ({len(mensajes)} mensajes)\n",
           f"_Palabras clave: {', '.join(d.palabras_clave) or '—'}_\n",
           "| Fecha | Hora | Asunto | Ref | De | Capa | Confianza |",
           "| --- | --- | --- | --- | --- | --- | --- |"]
    for m in mensajes:
        out.append(f"| {m.fecha_iso} | {m.hora or '----'} | {_celda(m.asunto) or '(sin asunto)'} "
                   f"| {m.msg_id} | {m.de} | {m.capa} | {m.confianza} |")
    return "\n".join(out) + "\n"


def render_vistas(mensajes, identidades: Identidades, defs: list[DefVista]):
    """({fichero: contenido}, notas). No toca disco. Vista inválida → omitida + nota."""
    salidas: dict[str, str] = {}
    notas: list[str] = []
    for d in defs:
        if not d.id:
            notas.append("vista sin 'id' omitida")
            continue
        if d.tipo == "persona":
            filas = _seleccion_persona(mensajes, identidades, d)
            if filas is None:
                notas.append(f"vista {d.id}: persona {d.persona!r} no existe en identidades.yaml")
                continue
            salidas[f"{d.id}.md"] = _render_persona(d, identidades.persona(d.persona), filas)
        elif d.tipo == "tematica":
            salidas[f"{d.id}.md"] = _render_tematica(d, _seleccion_tematica(mensajes, d))
        else:
            notas.append(f"vista {d.id}: tipo desconocido {d.tipo!r}")
    return salidas, notas
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_email_atomize_vistas.py -q --tb=short`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add core/email_atomize/vistas.py tests/test_email_atomize_vistas.py
git commit -m "feat(email-atomize): vistas temáticas (persona/tematica) — función pura (F3 T3)"
```

---

## Task 4: Cablear vistas en el pipeline

Genera `vistas/` tras `corpus.jsonl`, con poda de huérfanos (idempotente). Añade contadores al report.

**Files:**
- Modify: `core/email_atomize/pipeline.py` (imports, `AtomizeReport`, `atomize_dir`, `resumen`)
- Test: `tests/test_email_atomize_pipeline_f3.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_email_atomize_pipeline_f3.py
from __future__ import annotations
from email.message import EmailMessage
from core.email_atomize import pipeline as P


def _eml(mid, de, to, subject, body, fecha="Mon, 03 Feb 2020 18:42:00 +0100"):
    m = EmailMessage()
    m["Message-ID"] = mid; m["Subject"] = subject; m["From"] = de; m["To"] = to
    m["Date"] = fecha
    m.set_content(body)
    return m.as_bytes()


def _caso(tmp_path):
    case = tmp_path / "caso"
    src = case / "00_Input" / "03_Email"
    out = case / "01_Procesado" / "Emails"
    src.mkdir(parents=True)
    return case, src, out


def test_genera_vistas_desde_config(tmp_path):
    case, src, out = _caso(tmp_path)
    (case / "identidades.yaml").write_text(
        "personas:\n"
        "  - id: persona_uno\n"
        "    nombre: PersonaUno\n"
        "    vigilada: true\n"
        "    direcciones: [ { email: per01a@example.invalid, estado: confirmada } ]\n",
        encoding="utf-8")
    (case / "vistas.yaml").write_text(
        "vistas:\n"
        "  - id: dossier_persona_vigilada\n"
        "    titulo: Dossier\n"
        "    tipo: persona\n"
        "    persona: persona_uno\n"
        "  - id: nexo_causal\n"
        "    titulo: Nexo\n"
        "    tipo: tematica\n"
        "    palabras_clave: [inmueble]\n",
        encoding="utf-8")
    (src / "a.eml").write_bytes(_eml("<a@x>", "Jaime <per01a@example.invalid>", "x@y.com",
                                     "[inmueble]", "cuerpo sobre arras y inmueble"))
    rep = P.atomize_dir(src, out)   # case_dir derivado = out.parent.parent = case
    assert (out / "vistas" / "dossier_persona_vigilada.md").exists()
    assert (out / "vistas" / "nexo_causal.md").exists()
    assert rep.vistas_generadas == 2
    dossier = (out / "vistas" / "dossier_persona_vigilada.md").read_text(encoding="utf-8")
    assert "per01a@example.invalid" in dossier


def test_sin_config_no_genera_vistas(tmp_path):
    case, src, out = _caso(tmp_path)
    (src / "a.eml").write_bytes(_eml("<a@x>", "x@y.com", "z@y.com", "hola", "cuerpo"))
    rep = P.atomize_dir(src, out)
    assert rep.vistas_generadas == 0
    assert not (out / "vistas").exists()


def test_poda_vista_huerfana(tmp_path):
    case, src, out = _caso(tmp_path)
    (case / "identidades.yaml").write_text(
        "personas:\n  - id: p\n    vigilada: false\n"
        "    direcciones: [ { email: a@x.com, estado: confirmada } ]\n", encoding="utf-8")
    (case / "vistas.yaml").write_text(
        "vistas:\n  - id: v1\n    tipo: persona\n    persona: p\n", encoding="utf-8")
    (src / "a.eml").write_bytes(_eml("<a@x>", "a@x.com", "z@y.com", "hola", "cuerpo"))
    P.atomize_dir(src, out)
    assert (out / "vistas" / "v1.md").exists()
    # quitar la vista del config y re-correr → v1.md debe podarse
    (case / "vistas.yaml").write_text("vistas: []\n", encoding="utf-8")
    P.atomize_dir(src, out)
    assert not (out / "vistas" / "v1.md").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_email_atomize_pipeline_f3.py -q --tb=short`
Expected: FAIL — `AttributeError: 'AtomizeReport' object has no attribute 'vistas_generadas'`

- [ ] **Step 3: Write minimal implementation**

En `core/email_atomize/pipeline.py`, añadir junto a los imports (tras `from . import identidades as ID`):

```python
from . import vistas as V
```

En `AtomizeReport` (tras `upgrades: int = 0`, línea ~34), añadir:

```python
    vistas_generadas: int = 0
    notas: list[str] = field(default_factory=list)
```

En `resumen` (línea ~37), añadir las vistas al final del string retornado (antes de `f"{len(self.errores)} errores")`):

```python
    def resumen(self) -> str:
        return (f"{self.mensajes} mensajes atómicos ({self.reconstruidos_b} reconstruidos B), "
                f"{self.citas_a_revision} citas a revisión, {self.upgrades} upgrades; "
                f"{self.adjuntos_unicos} adjuntos únicos "
                f"({self.adjuntos_decorativos} decorativos filtrados), "
                f"{self.vistas_generadas} vistas, "
                f"{len(self.errores)} errores")
```

En `atomize_dir`, tras el bloque que escribe `_revision/` (después de las líneas 108-111 que crean `revision` y escriben `render_revision`), y antes de `reg.save()` (línea 113), insertar:

```python
    # --- Vistas temáticas (capa de caso; solo-lectura, no toca ningún .md) ---
    defs = V.cargar_vistas(case_dir)
    salidas, notas = V.render_vistas(mensajes, ident, defs)
    report.notas.extend(notas)
    vistas_dir = out / "vistas"
    if salidas:
        vistas_dir.mkdir(exist_ok=True)
        for nombre, contenido in salidas.items():
            (vistas_dir / nombre).write_text(contenido, encoding="utf-8")
    if vistas_dir.exists():           # poda huérfanos (idempotencia)
        for p in vistas_dir.glob("*.md"):
            if p.name not in salidas:
                p.unlink()
    report.vistas_generadas = len(salidas)
```

- [ ] **Step 4: Run test to verify it passes + suite verde**

Run: `python -m pytest tests/test_email_atomize_pipeline_f3.py -q --tb=short`
Expected: PASS (3 passed)

Run: `python -m pytest -q --tb=no --ignore=tests/test_email_export_mcp_server.py --ignore=tests/test_expedientes_xl_server.py`
Expected: exit 0, 0 fallos

- [ ] **Step 5: Commit**

```bash
git add core/email_atomize/pipeline.py tests/test_email_atomize_pipeline_f3.py
git commit -m "feat(email-atomize): generar vistas/ en el pipeline, idempotente (F3 T4)"
```

---

## Task 5: Módulo `entregas.py` (snapshot sellado)

**Files:**
- Create: `core/email_atomize/entregas.py`
- Test: `tests/test_email_atomize_entregas.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_email_atomize_entregas.py
from __future__ import annotations
from datetime import datetime
from core.email_atomize import entregas as E


def _out_con_set(tmp_path):
    out = tmp_path / "Emails"
    (out / "mensajes").mkdir(parents=True)
    (out / "mensajes" / "m1.md").write_text("uno", encoding="utf-8")
    (out / "vistas").mkdir()
    (out / "vistas" / "dossier_persona_vigilada.md").write_text("dossier", encoding="utf-8")
    (out / "corpus.jsonl").write_text('{"x":1}\n', encoding="utf-8")
    (out / "CORREOS_LECTURA.md").write_text("lectura", encoding="utf-8")
    return out


def test_sella_copia_y_manifiesto(tmp_path):
    out = _out_con_set(tmp_path)
    dest = E.sellar(out, "entrega instructora", commit="abc123",
                    ahora=datetime(2026, 6, 25, 9, 0, 0))
    assert dest.name == "2026-06-25_entrega-instructora"
    assert dest.parent == out / "_entregas"
    # set entregable copiado congelado
    assert (dest / "mensajes" / "m1.md").read_text(encoding="utf-8") == "uno"
    assert (dest / "vistas" / "dossier_persona_vigilada.md").exists()
    assert (dest / "corpus.jsonl").exists()
    # _SELLO.md con metadatos + sha256 por fichero
    sello = (dest / "_SELLO.md").read_text(encoding="utf-8")
    assert "commit_motor: abc123" in sello
    assert "mensajes/m1.md" in sello
    # sha256 de "uno"
    import hashlib
    assert hashlib.sha256(b"uno").hexdigest() in sello


def test_append_only_segunda_entrega_no_pisa(tmp_path):
    out = _out_con_set(tmp_path)
    d1 = E.sellar(out, "x", commit="c", ahora=datetime(2026, 6, 25, 9, 0, 0))
    d2 = E.sellar(out, "x", commit="c", ahora=datetime(2026, 6, 25, 9, 0, 0))
    assert d1 != d2
    assert d1.exists() and d2.exists()
    assert d2.name == "2026-06-25_x_2"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_email_atomize_entregas.py -q --tb=short`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.email_atomize.entregas'`

- [ ] **Step 3: Write minimal implementation**

```python
# core/email_atomize/entregas.py
"""Capa de caso: entrega sellada (_entregas/). Snapshot congelado + manifiesto de hashes.

Diseño: spec §5.3. Acción manual; append-only (cada sello = entrega distinta, NO idempotente).
"""
from __future__ import annotations

import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from core.email_export import _slug_descripcion
from core.intake_manifest import compute_sha256_bytes

SET_ENTREGABLE = ["mensajes", "adjuntos", "vistas",
                  "corpus.jsonl", "CORREOS_LECTURA.md", "INDICE_ADJUNTOS.md"]


def _git_commit() -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                           encoding="utf-8", errors="replace")
        return r.stdout.strip() if r.returncode == 0 else "desconocido"
    except Exception:  # noqa: BLE001 — git ausente / no es repo
        return "desconocido"


def _destino_unico(base: Path) -> Path:
    if not base.exists():
        return base
    n = 2
    while (cand := base.with_name(f"{base.name}_{n}")).exists():
        n += 1
    return cand


def sellar(out_dir, descr: str, *, commit: str | None = None,
           ahora: datetime | None = None) -> Path:
    """Copia congelada del SET_ENTREGABLE a _entregas/<fecha>_<slug>/ + _SELLO.md (sha256)."""
    out = Path(out_dir)
    ahora = ahora or datetime.now()
    commit = commit if commit is not None else _git_commit()
    slug = _slug_descripcion(descr) or "entrega"
    dest = _destino_unico(out / "_entregas" / f"{ahora.strftime('%Y-%m-%d')}_{slug}")
    dest.mkdir(parents=True)
    for item in SET_ENTREGABLE:
        src = out / item
        if not src.exists():
            continue
        if src.is_dir():
            shutil.copytree(src, dest / item)
        else:
            shutil.copy2(src, dest / item)
    filas = []
    for p in sorted(dest.rglob("*")):
        if p.is_file() and p.name != "_SELLO.md":
            filas.append((p.relative_to(dest).as_posix(), compute_sha256_bytes(p.read_bytes())))
    sello = [
        "# SELLO DE ENTREGA — GENERADO por core.email_atomize. NO editar.\n",
        f"- descripcion: {descr}",
        f"- fecha: {ahora.isoformat(timespec='seconds')}",
        f"- commit_motor: {commit}",
        f"- n_ficheros: {len(filas)}\n",
        "| Fichero | sha256 |",
        "| --- | --- |",
    ]
    sello += [f"| {rel} | {h} |" for rel, h in filas]
    (dest / "_SELLO.md").write_text("\n".join(sello) + "\n", encoding="utf-8")
    return dest
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_email_atomize_entregas.py -q --tb=short`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add core/email_atomize/entregas.py tests/test_email_atomize_entregas.py
git commit -m "feat(email-atomize): _entregas/ selladas con manifiesto sha256 (F3 T5)"
```

---

## Task 6: CLI `--entrega` + wrapper de pipeline

**Files:**
- Modify: `core/email_atomize/pipeline.py` (añadir `sellar_entrega`)
- Modify: `scripts/atomize_emails.py` (flag `--entrega`)
- Test: `tests/test_atomize_emails_cli.py` (extender)

- [ ] **Step 1: Write the failing test**

Añadir al final de `tests/test_atomize_emails_cli.py`:

```python
def test_cli_entrega_invoca_sellar(monkeypatch, tmp_path, capsys):
    import scripts.atomize_emails as CLI
    from core.email_atomize import pipeline as P

    llamadas = {}

    def fake_atomize_case(ref):
        from core.email_atomize.pipeline import AtomizeReport
        return AtomizeReport(mensajes=1)

    def fake_out_dir(ref):
        return tmp_path / "Emails"

    def fake_sellar(out_dir, descr):
        llamadas["out_dir"] = out_dir
        llamadas["descr"] = descr
        return tmp_path / "Emails" / "_entregas" / "2026-06-25_x"

    monkeypatch.setattr(P, "atomize_case", fake_atomize_case)
    monkeypatch.setattr(P, "emails_out_dir", fake_out_dir)
    monkeypatch.setattr(P, "sellar_entrega", fake_sellar)

    rc = CLI.main(["--ref", "W-02VND1", "--entrega", "entrega instructora"])
    assert rc == 0
    assert llamadas["descr"] == "entrega instructora"
    assert llamadas["out_dir"] == tmp_path / "Emails"
    assert "Entrega sellada" in capsys.readouterr().out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_atomize_emails_cli.py::test_cli_entrega_invoca_sellar -q --tb=short`
Expected: FAIL — `AttributeError: ... has no attribute 'sellar_entrega'` (o el flag `--entrega` no existe)

- [ ] **Step 3: Write minimal implementation**

En `core/email_atomize/pipeline.py`, añadir tras `atomize_case` (final del fichero):

```python
def sellar_entrega(out_dir, descr: str):
    """Sella una entrega del set entregable en <out_dir>/_entregas/. Acción manual."""
    from . import entregas as ENT
    return ENT.sellar(out_dir, descr)
```

En `scripts/atomize_emails.py`, dentro de `main`:
- Añadir el argumento (tras la línea `parser.add_argument("--out", ...)`):

```python
    parser.add_argument("--entrega", help="sella una entrega con esta descripción tras atomizar")
```

- Reemplazar el bloque de despacho (líneas 24-32) para capturar `out_dir` y sellar:

```python
    if args.ref:
        report = P.atomize_case(args.ref)
        out_dir = P.emails_out_dir(args.ref)
    elif args.src and args.out:
        report = P.atomize_dir(args.src, args.out)
        out_dir = args.out
    else:
        parser.error("usa --ref, o --src junto con --out")
        return 2

    print(report.resumen())
    if args.entrega:
        dest = P.sellar_entrega(out_dir, args.entrega)
        print(f"Entrega sellada en: {dest}")
```

(La impresión de `report.errores` por stderr de las líneas 33-34 se mantiene tras este bloque.)

- [ ] **Step 4: Run test to verify it passes + suite verde**

Run: `python -m pytest tests/test_atomize_emails_cli.py -q --tb=short`
Expected: PASS

Run: `python -m pytest -q --tb=no --ignore=tests/test_email_export_mcp_server.py --ignore=tests/test_expedientes_xl_server.py`
Expected: exit 0, 0 fallos

- [ ] **Step 5: Commit**

```bash
git add core/email_atomize/pipeline.py scripts/atomize_emails.py tests/test_atomize_emails_cli.py
git commit -m "feat(email-atomize): CLI --entrega para sellar la entrega (F3 T6)"
```

---

## Task 7: Verificación EN VIVO sobre W-02VND1 (lección dura F2)

No es TDD: es verificación sobre los 277 reales. Ruta del caso:
`G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\CASOS\Barcelona\BaRS1 - [inmueble] - (W-02VND1) - Vuelta`.
**No tocar `00_Input`.** Las `palabras_clave` del nexo las fija Nikolai antes de correr.

- [ ] **Step 1: Capturar la línea base de hashes de los 277 Capa A (ANTES)**

Run (PowerShell, lectura sobre `G:` → `dangerouslyDisableSandbox`):

```powershell
$emails = "G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\CASOS\Barcelona\BaRS1 - [inmueble] - (W-02VND1) - Vuelta\01_Procesado\Emails\mensajes"
Get-ChildItem $emails -Filter *_MSG-*.md |
  Where-Object { (Get-Content $_.FullName -Raw) -notmatch "capa: B" } |
  Get-FileHash -Algorithm SHA256 |
  Sort-Object Path | Export-Csv "$env:TEMP\capaA_antes.csv" -NoTypeInformation
```
Expected: CSV con ~277 filas (las Capa A; los `.md` de Capa B llevan `capa: B`).

- [ ] **Step 2: Crear `identidades.yaml` + `vistas.yaml` del piloto en la raíz del caso**

Crear `<caso>\identidades.yaml` con el contenido del §4.1 del spec (las 2 personas, 3+1 direcciones). Crear `<caso>\vistas.yaml` con `dossier_persona_vigilada` (`tipo: persona`, `persona: persona_uno`) y `nexo_causal` (`tipo: tematica`, `palabras_clave` que apruebe Nikolai). Usar el editor (UTF-8 sin BOM); NO meterlos en `01_Procesado/`.

- [ ] **Step 3: Re-correr la atomización**

Run:
```powershell
cd "C:\Users\tnm33\Dev\FeesDefender"
python -m scripts.atomize_emails --ref W-02VND1
```
Expected: resumen con `277 mensajes atómicos (89 reconstruidos B)`, `2 vistas`, `0 errores` (cifras de la Fase 2 + 2 vistas).

- [ ] **Step 4: Verificar 277 Capa A byte-idénticos (DESPUÉS)**

Run:
```powershell
Get-ChildItem $emails -Filter *_MSG-*.md |
  Where-Object { (Get-Content $_.FullName -Raw) -notmatch "capa: B" } |
  Get-FileHash -Algorithm SHA256 |
  Sort-Object Path | Export-Csv "$env:TEMP\capaA_despues.csv" -NoTypeInformation
if (Compare-Object (Import-Csv "$env:TEMP\capaA_antes.csv") (Import-Csv "$env:TEMP\capaA_despues.csv") -Property Hash) {
  Write-Host "FALLO: hay Capa A que cambió"
} else { Write-Host "OK: 277 Capa A byte-idénticos" }
```
Expected: `OK: 277 Capa A byte-idénticos`. **Si algo cambió → STOP**: investigar (no debería; la capa de caso no toca Capa A) antes de seguir.

- [ ] **Step 5: Verificar Layer B sin cambios + vistas**

Run:
```powershell
$rev = "G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\CASOS\Barcelona\BaRS1 - [inmueble] - (W-02VND1) - Vuelta\01_Procesado\Emails"
(Get-Content "$rev\_revision\identidades_vigiladas.md" -Raw)  # 12+13 PersonaUno, idéntico a F2
(Get-Content "$rev\vistas\dossier_persona_vigilada.md" -Raw)
(Get-Content "$rev\vistas\nexo_causal.md" -Raw)
```
Expected: `identidades_vigiladas.md` igual a la F2; `dossier_persona_vigilada.md` agrupa las 3 direcciones de PersonaUno y **NO** lista a `ignacio@despacho-ab.example`; `nexo_causal.md` con los mensajes de las palabras clave en orden cronológico.

- [ ] **Step 6: Probar el sellado de entrega (append-only)**

Run:
```powershell
python -m scripts.atomize_emails --ref W-02VND1 --entrega "verificacion F3"
python -m scripts.atomize_emails --ref W-02VND1 --entrega "verificacion F3"
Get-ChildItem "$rev\_entregas"
```
Expected: dos carpetas (`..._verificacion-f3` y `..._verificacion-f3_2`), cada una con `_SELLO.md` y la copia del set.

- [ ] **Step 7: No hay commit de código.** Los YAML del caso viven en `G:` (no en el repo). Anotar las cifras observadas para el cierre de STATUS.

---

## Task 8: Revisión adversarial de código (workflow)

- [ ] **Step 1: Lanzar la revisión adversarial** de todo el diff de la F3 (`identidades.py`, `vistas.py`, `entregas.py`, los cambios de `inline.py`/`render.py`/`pipeline.py` y el CLI) con un workflow de 3 lentes (correctness / cero-misatribución-y-byte-idéntico / regresión-idempotencia) → verificación de cada hallazgo. Buscar específicamente: ¿alguna vía por la que la capa de caso mute un `.md` de Capa A? ¿la unificación funde personas distintas? ¿el selector temático incluye/excluye mal por precedencia? ¿`sellar` puede pisar una entrega previa?

- [ ] **Step 2: Corregir** los hallazgos confirmados con tests de regresión (cada uno: test→fail→fix→pass→commit acotado). Refutados → documentar por qué.

- [ ] **Step 3: Suite final verde** + actualizar `STATUS.md` (cierre) y marcar la Fase 3 `[x]` en la entrada `[SIGUIENTE-EMAIL-ATOMIZE]` de `PLAN.md` (si `PLAN.md` no trae cambios ajenos sin commitear; si los trae, dejar la marca en working tree sin commitear).

---

## Self-Review (cobertura del spec)

- §4.1 identidades.yaml (esquema, sets derivados, invariantes) → Task 1. ✓
- §4.2 vistas.yaml (persona/tematica, overrides) → Task 3. ✓
- §5.1 identidades.py / §5.4 inyección sin estado global → Task 1 + Task 2. ✓
- §5.2 vistas.py (función pura, omitir vista inválida con nota) → Task 3. ✓
- §5.3 entregas.py (copia + _SELLO.md, append-only) → Task 5. ✓
- §5.5 CLI (`--entrega`) → Task 6. ✓
- §6 salidas nuevas (vistas/ en pipeline) → Task 4. ✓
- §7 migración de tests (5 tests) → Task 2 (los 5 ficheros listados). ✓
- §8 verificación en vivo (277 byte-idénticos + vistas + entrega) → Task 7. ✓
- §3 byte-idéntico / idempotencia → verificado en Task 4 (poda), Task 7 (hashes), Task 8 (adversarial). ✓
- Regla "lo del caso solo por config" → Task 1/3 (YAML), Task 2 (sets hardcodeados eliminados). ✓
- Decomposición (recall MSG-00018 fuera) → no aparece como tarea. ✓

Consistencia de tipos: `Identidades`/`Persona` (Task 1) usados con los mismos nombres de campo (`vigiladas`, `candidatas`, `persona`, `persona_de`, `estado_de`, `emails()`) en Tasks 2-4. `DefVista` (Task 3) campos consistentes con el YAML (Task 4). `sellar(out_dir, descr, *, commit, ahora)` (Task 5) ↔ `sellar_entrega(out_dir, descr)` (Task 6). ✓
