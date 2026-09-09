# Skill `demanda-honorarios-ev` v1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir la capa de dominio —preparar y revisar— de la demanda de reclamación de honorarios de intermediación de Engel & Völkers en posición actora, sin duplicar nada de `preparacion-litigio-civil`, `escritos-judiciales` ni `verificacion-anclada-fuente`.

**Architecture:** Una skill nueva con cuatro `references/` de dominio y un script de cruce documental, más dos ediciones quirúrgicas a `preparacion-litigio-civil`. Todo el flujo genérico (expediente, maestros, cronología, anclaje 🟢/🟡/🔴, `.docx`, estilo, citas) sigue siendo de sus dueños; esta skill solo aporta el fondo del asunto, las puertas de cauce y el modo revisión, que hoy no existe en ninguna.

**Tech Stack:** Markdown (SKILL.md + references), Python 3.14 con `pytest` para el script y los guards, `scripts/validate_skills.py` y `scripts/sync_skill_helpers.py` como contrato de conformidad.

## Global Constraints

- **Spec:** `docs/superpowers/specs/2026-09-08-demanda-honorarios-ev-design.md` rev. 2 (commits `15bce7e` → `acbe6d0`). Toda referencia «§N del spec» es a ese fichero.
- **Frontmatter obligatorio** (`scripts/validate_skills.py`): `name` idéntico al nombre de la carpeta · `description` presente, ≤ 1024 chars y **sin etiquetas tipo XML** (Cowork rechaza la importación) · `license` de primer nivel · `metadata.rol` ∈ `{transversal, fase, cliente, output, input, procesado}` · `metadata.naturaleza` ∈ `{atomica, orquestadora}` · `metadata.version` **siempre entre comillas** · `metadata.status` ∈ `{vigente, deprecada, experimental}`.
- **Módulo OPERACIÓN:** la skill produce outputs en expediente, así que `scripts/` debe contener los cuatro helpers canónicos (`registrar_outputs.py`, `registrar_uso.py`, `programar_revision.py`, `scaffold_caso.py`) **copiados por el sincronizador**, y la carpeta debe estar en el tuple `_TARGETS` de `scripts/sync_skill_helpers.py:29`.
- **Ningún test escribe en el árbol de producción.** Árbol sintético en `tmp_path` y pasado a la función. Lo vigila `tests/test_guard_aislamiento_paralelo.py`. Agrupar con `xdist_group` no vale.
- **Encoding:** UTF-8 sin BOM. Nunca `Add-Content`/`Get-Content -Raw` sin `-Encoding UTF8`.
- **Suite:** subconjuntos en serie (`python -m pytest -q --tb=short <ruta>`); la suite completa solo por `scripts.session_close`, que corre **dos semillas** (777 y 31337).
- **Higiene PII:** en el repo el caso se referencia solo por `W-02USSI`. Los ejemplos de los `references/` y de los tests usan datos **sintéticos** (`W-TEST99`, «la Agencia», «el Deudor»), nunca nombres, NIF, direcciones ni correos reales.
- **Rama y PR:** `main` está protegida. Todo va en la rama actual y entra por PR con el check `leak-scan`.
- **Revisión adversarial:** **una ronda, sobre el diff** (§15 del spec). No se mergea sin ella.

---

## File Structure

| Fichero | Responsabilidad |
|---|---|
| `.claude/skills/demanda-honorarios-ev/SKILL.md` | Frontmatter, los dos modos, el flujo y el encadenamiento. Nada de contenido de dominio: lo delega a `references/`. |
| `.claude/skills/demanda-honorarios-ev/references/cadena-de-devengo.md` | Los 5 eslabones × 7 `TIPOS_CASO_ACTORA` y el §5.1 (las condiciones del contrato privado). |
| `.claude/skills/demanda-honorarios-ev/references/donde-esta-cada-cosa.md` | Resolución de documentos por censo y por rol, con el orden de preferencia y el fallback. |
| `.claude/skills/demanda-honorarios-ev/references/puertas-de-dominio.md` | Las 7 puertas del §7 del spec. |
| `.claude/skills/demanda-honorarios-ev/references/catalogo-de-defectos.md` | Las 8 familias del §8 del spec. Es el corazón del modo revisión. |
| `.claude/skills/demanda-honorarios-ev/scripts/cruzar_documental.py` | Único código propio: cruce bidireccional de remisiones + anclaje verificable contra el censo. |
| `.claude/skills/demanda-honorarios-ev/evals/evals.json` | Evals, sembradas con W-02USSI en modo revisión. |
| `.claude/skills/demanda-honorarios-ev/CHANGELOG.md` | Historia de versiones de la skill. |
| `tests/test_skill_demanda_honorarios_ev.py` | Guards de la skill: conformidad del frontmatter, las 8 familias, y los nombres de artefacto que cita `donde-esta-cada-cosa.md`. |
| `tests/test_cruzar_documental.py` | Tests del script. |
| `scripts/sync_skill_helpers.py:29` | Modificar: añadir el target. |
| `.claude/skills/preparacion-litigio-civil/SKILL.md:91` (paso 5) y `:120` (paso 8) | Modificar: bloque MASC y criterio deontológico. |

---

## Task 1: Esqueleto de la skill, conforme a los guards

**Files:**
- Create: `.claude/skills/demanda-honorarios-ev/SKILL.md` (solo frontmatter + títulos; el cuerpo es la Task 8)
- Create: `.claude/skills/demanda-honorarios-ev/CHANGELOG.md`
- Modify: `scripts/sync_skill_helpers.py:29-37` (tuple `_TARGETS`)
- Test: `tests/test_skill_demanda_honorarios_ev.py`

**Interfaces:**
- Consumes: nada.
- Produces: la carpeta `.claude/skills/demanda-honorarios-ev/` con `scripts/` poblado por el sincronizador, y el módulo de test `tests/test_skill_demanda_honorarios_ev.py` con la función `_skill_dir()` que las Tasks 4 y 7 reutilizan.

- [ ] **Step 1: Write the failing test**

Crear `tests/test_skill_demanda_honorarios_ev.py`:

```python
"""Guards de la skill `demanda-honorarios-ev`.

No prueban el contenido jurídico —eso lo adjudica el letrado— sino las
propiedades que se rompen en silencio: el frontmatter que Cowork rechaza al
importar, el conteo del catálogo que se descuadra al editar, y los nombres de
artefacto del expediente que la skill cita y el código podría renombrar.
"""
from __future__ import annotations

from pathlib import Path

import yaml

_ROLES = {"transversal", "fase", "cliente", "output", "input", "procesado"}
_NATURALEZAS = {"atomica", "orquestadora"}
_ESTADOS = {"vigente", "deprecada", "experimental"}


def _skill_dir() -> Path:
    return Path(__file__).resolve().parents[1] / ".claude" / "skills" / "demanda-honorarios-ev"


def _frontmatter() -> dict:
    texto = (_skill_dir() / "SKILL.md").read_text(encoding="utf-8")
    assert texto.startswith("---\n"), "SKILL.md debe abrir con frontmatter YAML"
    _, fm, _ = texto.split("---", 2)
    return yaml.safe_load(fm)


def test_el_frontmatter_cumple_el_contrato_del_validador():
    fm = _frontmatter()
    assert fm["name"] == "demanda-honorarios-ev"
    assert "license" in fm and fm["license"]
    desc = fm["description"]
    assert desc and len(desc) <= 1024
    assert "<" not in desc and ">" not in desc, "Cowork rechaza descriptions con etiquetas XML"
    meta = fm["metadata"]
    assert meta["rol"] in _ROLES
    assert meta["naturaleza"] in _NATURALEZAS
    assert meta["status"] in _ESTADOS
    assert isinstance(meta["version"], str), "version debe ir entre comillas en el YAML"


def test_declara_las_skills_que_orquesta_y_no_se_reimplementa():
    """La skill es la capa de dominio: si no declara a quién delega, el diseño
    se ha perdido por el camino (spec §3)."""
    meta = _frontmatter()["metadata"]
    orquestadas = set(meta.get("orchestrates") or [])
    for necesaria in {
        "preparacion-litigio-civil",
        "escritos-judiciales",
        "verificacion-anclada-fuente",
        "cendoj-descarga",
        "pase-de-estilo",
    }:
        assert necesaria in orquestadas, f"falta {necesaria} en metadata.orchestrates"


def test_el_sincronizador_tiene_la_skill_como_target():
    """Módulo OPERACIÓN: sin el target, los helpers canónicos no se copian y la
    telemetría de la skill no existe."""
    import scripts.sync_skill_helpers as ssh

    assert ".claude/skills/demanda-honorarios-ev/scripts" in ssh._TARGETS


def test_los_cuatro_helpers_canonicos_estan_copiados():
    import scripts.sync_skill_helpers as ssh

    esperados = {p.name for p in ssh._shared_helpers()}
    presentes = {p.name for p in (_skill_dir() / "scripts").glob("*.py")}
    assert esperados <= presentes, f"faltan helpers: {sorted(esperados - presentes)}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -q --tb=short tests/test_skill_demanda_honorarios_ev.py`
Expected: FAIL — `FileNotFoundError` sobre `SKILL.md` (la carpeta no existe).

- [ ] **Step 3: Crear la carpeta desde la plantilla canónica**

```powershell
Set-Location "C:\Users\tnm33\Dev\FeesDefender\.claude\worktrees\demanda-sergio-inventario-ecc7fa"
Copy-Item -Recurse ".claude\skills\_shared\_plantilla-skill" ".claude\skills\demanda-honorarios-ev"
Remove-Item ".claude\skills\demanda-honorarios-ev\_LEEME.md"
New-Item -ItemType Directory -Force ".claude\skills\demanda-honorarios-ev\references" | Out-Null
New-Item -ItemType Directory -Force ".claude\skills\demanda-honorarios-ev\evals" | Out-Null
```

- [ ] **Step 4: Escribir el frontmatter**

Sustituir íntegro el frontmatter de `.claude/skills/demanda-honorarios-ev/SKILL.md` por:

```yaml
---
name: demanda-honorarios-ev
description: >-
  Prepara y revisa la demanda de reclamación de honorarios de intermediación
  inmobiliaria de Engel & Völkers en posición ACTORA (tipos BAD_DEBT,
  NEGATIVA_OFERTA, NEGATIVA_ARRAS, NEGATIVA_ESCRITURA,
  NEGATIVA_CONTRATO_ARRENDAMIENTO, VUELTA, INCUMPLIMIENTO_EXCLUSIVA). Dos modos
  que detecta sola: si no hay borrador PREPARA la capa de dominio del escrito
  (cadena de devengo, condiciones del contrato privado, puertas del cauce,
  índice documental resuelto por rol); si ya hay borrador lo REVISA contra ocho
  familias de defecto medidas y devuelve un informe con las puertas comprobadas
  y las que no se pudieron comprobar. Úsala cuando el usuario diga "prepara la
  demanda de honorarios", "revisa la demanda que preparó X", "reclamamos los
  honorarios a la propiedad", "el vendedor no otorgó escritura", "el cliente
  cerró por su cuenta". Cauce verbal u ordinario según cuantía; el monitorio
  exige constancia de autorización. NO monta el expediente ni fija los hechos
  (preparacion-litigio-civil), NO genera el .docx (escritos-judiciales), NO
  valora la viabilidad (triaje-viabilidad) y NO cubre la posición defensiva
  (contestacion-honorarios-art20-lau).
metadata:
  rol: fase
  naturaleza: orquestadora
  jurisdiction: ES
  area: [civil, procesal]
  version: "1.0"
  author: "Nikolai Tyukhay"
  organization: "Tyukhay Legal"
  contact: "nikolai.tyukhay@tyukhay.legal"
  status: vigente
  orchestrates:
    - engel-volkers
    - preparacion-litigio-civil
    - verificacion-anclada-fuente
    - cendoj-descarga
    - escritos-judiciales
    - pase-de-estilo
  requires:
    - "expediente FeesDefender con 00_Input/_caso.md"
license: "Proprietary — Tyukhay Legal (todos los derechos reservados)"
---

# demanda-honorarios-ev

<!-- El cuerpo se escribe en la Task 8. -->
```

- [ ] **Step 5: Añadir el target al sincronizador**

En `scripts/sync_skill_helpers.py`, dentro del tuple `_TARGETS` (línea 29), añadir como última entrada:

```python
    ".claude/skills/contestacion-honorarios-art20-lau/scripts",
    ".claude/skills/demanda-honorarios-ev/scripts",
)
```

- [ ] **Step 6: Sincronizar los helpers**

Run: `python -m scripts.sync_skill_helpers`
Expected: escribe los cuatro `.py` en `.claude/skills/demanda-honorarios-ev/scripts/`.

- [ ] **Step 7: Run tests to verify they pass**

Run: `python -m pytest -q --tb=short tests/test_skill_demanda_honorarios_ev.py tests/test_skill_helpers_sync.py`
Expected: PASS (5 tests nuevos + los del sincronizador).

- [ ] **Step 8: Comprobar el validador, que es modo aviso y no gate**

Run: `python -m scripts.validate_skills`
Expected: **cero avisos** cuyo texto contenga `demanda-honorarios-ev`. Los avisos de otras skills son preexistentes y no se tocan en este plan.

- [ ] **Step 9: Commit**

```bash
git add .claude/skills/demanda-honorarios-ev scripts/sync_skill_helpers.py tests/test_skill_demanda_honorarios_ev.py
git commit -m "skill(demanda-honorarios-ev): esqueleto conforme al contrato de frontmatter y al modulo OPERACION"
```

---

## Task 2: `cruzar_documental.py` — cruce bidireccional de remisiones

Cubre las familias 2 y 3 del catálogo (§8 del spec): documento invocado que no está en el ramo, y documento del ramo que el escrito no cita.

**Files:**
- Create: `.claude/skills/demanda-honorarios-ev/scripts/cruzar_documental.py`
- Test: `tests/test_cruzar_documental.py`

**Interfaces:**
- Consumes: nada de tasks anteriores.
- Produces: `remisiones_del_escrito(texto: str) -> tuple[Remision, ...]`, `etiqueta_de_fichero(nombre: str) -> str | None`, `cruzar(texto: str, nombres_censo: Sequence[str]) -> CruceDocumental`, y las dataclasses `Remision(etiqueta: str, linea: int)` y `CruceDocumental(citados_sin_documento: tuple[Remision, ...], documentos_sin_citar: tuple[str, ...])`. La Task 3 amplía este módulo.

- [ ] **Step 1: Write the failing test**

Crear `tests/test_cruzar_documental.py`:

```python
"""El cruce documental: lo que el escrito invoca contra lo que el ramo tiene.

Las formas de remisión y los nombres de fichero de los casos de prueba son las
formas REALES observadas en un escrito y en un gestor documental del despacho,
con los datos sustituidos por sintéticos.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_MOD = (Path(__file__).resolve().parents[1] / ".claude" / "skills"
        / "demanda-honorarios-ev" / "scripts" / "cruzar_documental.py")


def _cargar():
    spec = importlib.util.spec_from_file_location("cruzar_documental", _MOD)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["cruzar_documental"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def cd():
    return _cargar()


class TestRemisionesDelEscrito:
    def test_forma_simple(self, cd):
        r = cd.remisiones_del_escrito("Se acompaña como DOCUMENTO Nº 1 la escritura.")
        assert [x.etiqueta for x in r] == ["1"]

    def test_sufijo_de_letra_con_guion_o_raya(self, cd):
        texto = ("como DOCUMENTO Nº 2 – B la nota informativa y como "
                 "DOCUMENTO Nº 11 - A la nota simple")
        assert [x.etiqueta for x in cd.remisiones_del_escrito(texto)] == ["2-B", "11-A"]

    def test_lista_con_y(self, cd):
        r = cd.remisiones_del_escrito("Se acompañan como DOCUMENTO Nº 6 y 7 los contratos.")
        assert [x.etiqueta for x in r] == ["6", "7"]

    def test_lista_con_comas_y_final_en_y(self, cd):
        r = cd.remisiones_del_escrito("como DOCUMENTO Nº 14, 15 y 16 los requerimientos")
        assert [x.etiqueta for x in r] == ["14", "15", "16"]

    def test_normaliza_ceros_a_la_izquierda(self, cd):
        r = cd.remisiones_del_escrito("el DOCUMENTO Nº 02 y el DOCUMENTO Nº 2")
        assert [x.etiqueta for x in r] == ["2", "2"]

    def test_registra_la_linea_para_poder_senalar_el_parrafo(self, cd):
        texto = "primera\nsegunda con DOCUMENTO Nº 9\ntercera"
        assert cd.remisiones_del_escrito(texto)[0].linea == 2

    def test_no_confunde_la_palabra_documento_suelta(self, cd):
        assert cd.remisiones_del_escrito("aporta el documento de identidad") == ()


class TestEtiquetaDeFichero:
    @pytest.mark.parametrize("nombre,esperado", [
        ("doc_02_encargo_de_venta_firmado.pdf", "2"),
        ("doc_02_b_nota_mercantil.pdf", "2-B"),
        ("d_11_b_mail_vendedor_agencia.pdf", "11-B"),
        ("DOC 05 - OFERTA ACEPTADA.pdf", "5"),
        ("doc_20_burofax_abogado_deudor.pdf", "20"),
    ])
    def test_extrae_la_etiqueta(self, cd, nombre, esperado):
        assert cd.etiqueta_de_fichero(nombre) == esperado

    def test_devuelve_none_si_el_nombre_no_lleva_numero_de_documento(self, cd):
        assert cd.etiqueta_de_fichero("demanda_monitorio.rtf") is None


class TestCruce:
    def test_caza_el_documento_invocado_que_no_existe(self, cd):
        """El defecto real: el escrito promete un 11-A que el ramo no tiene."""
        texto = "como DOCUMENTO Nº 11 - A la nota simple que acredita la venta"
        res = cd.cruzar(texto, ["doc_11_chat.pdf", "d_11_b_mail.pdf"])
        assert [x.etiqueta for x in res.citados_sin_documento] == ["11-A"]

    def test_caza_el_documento_del_ramo_que_nadie_cita(self, cd):
        texto = "como DOCUMENTO Nº 12 la factura"
        res = cd.cruzar(texto, ["doc_12_factura.pdf", "doc_11_chat.pdf"])
        assert res.documentos_sin_citar == ("doc_11_chat.pdf",)

    def test_no_cuenta_como_huerfano_lo_que_no_es_documento_numerado(self, cd):
        res = cd.cruzar("como DOCUMENTO Nº 12 la factura",
                        ["doc_12_factura.pdf", "demanda_monitorio.rtf"])
        assert res.documentos_sin_citar == ()

    def test_ramo_completo_y_escrito_coherente_no_da_hallazgos(self, cd):
        texto = "DOCUMENTO Nº 1 y DOCUMENTO Nº 2 – B"
        res = cd.cruzar(texto, ["doc_01_poder.pdf", "doc_02_b_nota.pdf"])
        assert res.citados_sin_documento == ()
        assert res.documentos_sin_citar == ()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -q --tb=short tests/test_cruzar_documental.py`
Expected: FAIL — `FileNotFoundError` sobre `cruzar_documental.py`.

- [ ] **Step 3: Write minimal implementation**

Crear `.claude/skills/demanda-honorarios-ev/scripts/cruzar_documental.py`:

```python
"""Cruza las remisiones documentales de un escrito contra el censo del ramo.

Dos direcciones, porque los dos defectos son reales y distintos: un
«DOCUMENTO Nº X» que el ramo no tiene (la promesa incumplida) y un documento
del ramo que el escrito no cita (la prueba que nadie invoca).

Trabaja sobre TEXTO y una LISTA DE NOMBRES, no sobre rutas ni sobre el CRM: así
se prueba entero sin disco, sin red y sin expediente, y sirve igual con el
espejo de la sala de máquina, con un `.txt` pegado a mano o con el censo de
`indice_documental.yaml`.
"""
from __future__ import annotations

import dataclasses
import re
from collections.abc import Sequence

#: «DOCUMENTO Nº» + lista de números con sufijo opcional de letra. Acepta guion,
#: raya y raya larga entre número y letra, y `Nº`/`N°`/`No` con o sin punto.
_RE_REMISION = re.compile(
    r"DOCUMENTO\s+N[.ºo°]{1,2}\s*"
    r"((?:\d+\s*(?:[-–—]\s*[A-Z])?)(?:\s*(?:,|y)\s*\d+\s*(?:[-–—]\s*[A-Z])?)*)",
    re.IGNORECASE,
)
_RE_UNA = re.compile(r"(\d+)\s*(?:[-–—]\s*([A-Z]))?", re.IGNORECASE)

#: `doc_02_b_…`, `d_11_b_…`, `DOC 05 - …`: número y sufijo opcional al principio.
_RE_FICHERO = re.compile(
    r"^(?:doc|d)[\s_-]*(\d+)(?:[\s_-]+([a-z])(?=[\s_-]|$))?", re.IGNORECASE
)


@dataclasses.dataclass(frozen=True)
class Remision:
    """Una remisión tal como aparece en el escrito, con su línea."""

    etiqueta: str
    linea: int


@dataclasses.dataclass(frozen=True)
class CruceDocumental:
    citados_sin_documento: tuple[Remision, ...]
    documentos_sin_citar: tuple[str, ...]


def _normalizar(numero: str, letra: str | None) -> str:
    base = str(int(numero))
    return f"{base}-{letra.upper()}" if letra else base


def remisiones_del_escrito(texto: str) -> tuple[Remision, ...]:
    """Las remisiones del escrito, en orden de aparición y con su nº de línea.

    No deduplica: una etiqueta repetida es información (primera mención vs.
    posteriores), y quitarla aquí se lo esconde a quien presenta.
    """
    salida: list[Remision] = []
    for linea_n, linea in enumerate(texto.splitlines(), start=1):
        for grupo in _RE_REMISION.finditer(linea):
            for num, letra in _RE_UNA.findall(grupo.group(1)):
                salida.append(Remision(_normalizar(num, letra or None), linea_n))
    return tuple(salida)


def etiqueta_de_fichero(nombre: str) -> str | None:
    """La etiqueta de documento que declara el nombre del fichero, o `None`.

    `None` significa «este fichero no es un documento numerado del ramo» —el
    propio escrito, un índice, un manifiesto—, y por eso no cuenta como huérfano.
    """
    m = _RE_FICHERO.match(nombre.strip())
    return _normalizar(m.group(1), m.group(2)) if m else None


def cruzar(texto: str, nombres_censo: Sequence[str]) -> CruceDocumental:
    """El cruce en las dos direcciones."""
    remisiones = remisiones_del_escrito(texto)
    citadas = {r.etiqueta for r in remisiones}

    del_ramo: dict[str, list[str]] = {}
    for nombre in nombres_censo:
        etiqueta = etiqueta_de_fichero(nombre)
        if etiqueta is not None:
            del_ramo.setdefault(etiqueta, []).append(nombre)

    vistas: set[str] = set()
    faltan: list[Remision] = []
    for r in remisiones:
        if r.etiqueta not in del_ramo and r.etiqueta not in vistas:
            faltan.append(r)
            vistas.add(r.etiqueta)

    sobran = tuple(
        nombre
        for etiqueta, nombres in sorted(del_ramo.items())
        for nombre in nombres
        if etiqueta not in citadas
    )
    return CruceDocumental(tuple(faltan), sobran)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest -q --tb=short tests/test_cruzar_documental.py`
Expected: PASS, 15 tests.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/demanda-honorarios-ev/scripts/cruzar_documental.py tests/test_cruzar_documental.py
git commit -m "skill(demanda-honorarios-ev): cruce bidireccional de remisiones documentales (familias 2 y 3)"
```

---

## Task 3: `cruzar_documental.py` — el anclaje verificable contra el censo

Implementa el §6.1 del spec: un Hecho 🟢 exige que su documento de soporte tenga `estado: ok` en el censo de la sala de máquina.

**Files:**
- Modify: `.claude/skills/demanda-honorarios-ev/scripts/cruzar_documental.py` (añadir al final)
- Modify: `tests/test_cruzar_documental.py` (añadir clase al final)

**Interfaces:**
- Consumes: `etiqueta_de_fichero` de la Task 2.
- Produces: `AnclajeDudoso(etiqueta: str, fichero: str, estado: str, chars: int, nota: str)` y `anclajes_sin_texto(nombres_por_etiqueta: Mapping[str, Sequence[Mapping]], etiquetas_verdes: Iterable[str]) -> tuple[AnclajeDudoso, ...]`.

- [ ] **Step 1: Write the failing test**

Añadir al final de `tests/test_cruzar_documental.py`:

```python
class TestAnclajeVerificable:
    """§6.1 del spec: un 🟢 exige `estado: ok` en el censo. Lo demás baja a 🟡.

    Los estados y las notas son los que emite de verdad la sala de máquina.
    """

    def test_un_documento_ok_sostiene_el_verde(self, cd):
        censo = {"6": [{"rel_path": "doc_06_arras.pdf", "estado": "ok", "chars": 14178, "nota": ""}]}
        assert cd.anclajes_sin_texto(censo, ["6"]) == ()

    def test_un_documento_empty_no_sostiene_el_verde(self, cd):
        censo = {"9": [{"rel_path": "doc_09_carta.pdf", "estado": "empty",
                        "chars": 2, "nota": "sin texto o residual"}]}
        (dudoso,) = cd.anclajes_sin_texto(censo, ["9"])
        assert (dudoso.etiqueta, dudoso.estado, dudoso.chars) == ("9", "empty", 2)

    def test_un_documento_low_tampoco(self, cd):
        censo = {"2": [{"rel_path": "doc_02_encargo.pdf", "estado": "low", "chars": 5599,
                        "nota": "1 de 2 páginas escaneadas sin texto (págs. 2)"}]}
        (dudoso,) = cd.anclajes_sin_texto(censo, ["2"])
        assert dudoso.estado == "low"
        assert "páginas escaneadas sin texto" in dudoso.nota

    def test_sin_soporte_tampoco(self, cd):
        censo = {"7": [{"rel_path": "nota_voz.opus", "estado": "sin_soporte", "chars": 0,
                        "nota": "sin soporte para esta extensión"}]}
        assert cd.anclajes_sin_texto(censo, ["7"])[0].estado == "sin_soporte"

    def test_basta_UNA_copia_con_texto_para_sostener_el_verde(self, cd):
        """La redundancia del intake es lo que salvó tres documentos nucleares en
        W-02USSI: si otra copia extrajo, el anclaje se sostiene en esa."""
        censo = {"9": [
            {"rel_path": "doc_09_carta.pdf", "estado": "empty", "chars": 2, "nota": ""},
            {"rel_path": "desistimiento_vendedor.jpg", "estado": "ok", "chars": 2858, "nota": ""},
        ]}
        assert cd.anclajes_sin_texto(censo, ["9"]) == ()

    def test_una_etiqueta_verde_sin_documento_en_el_censo_es_dudosa(self, cd):
        (dudoso,) = cd.anclajes_sin_texto({}, ["11-A"])
        assert dudoso.etiqueta == "11-A"
        assert dudoso.estado == "ausente"

    def test_un_fallo_de_extraccion_no_se_confunde_con_un_documento_vacio(self, cd):
        """MEJORAS #190: `empty` mezcla «no tiene texto» y «no pude leerlo». La
        nota es lo único que hoy los separa, así que se propaga."""
        censo = {"1": [{"rel_path": "demanda.rtf", "estado": "empty", "chars": 0,
                        "nota": "fallo al procesar: 'utf-8' codec can't encode characters"}]}
        (dudoso,) = cd.anclajes_sin_texto(censo, ["1"])
        assert dudoso.nota.startswith("fallo al procesar")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -q --tb=short tests/test_cruzar_documental.py::TestAnclajeVerificable`
Expected: FAIL con `AttributeError: module 'cruzar_documental' has no attribute 'anclajes_sin_texto'`.

- [ ] **Step 3: Write minimal implementation**

Añadir al final de `cruzar_documental.py`:

```python
#: Estados del censo de la sala de máquina que NO sostienen un anclaje 🟢.
ESTADOS_SIN_TEXTO = frozenset({"empty", "low", "sin_soporte"})


@dataclasses.dataclass(frozen=True)
class AnclajeDudoso:
    """Un Hecho marcado 🟢 cuyo documento de soporte no tiene texto usable."""

    etiqueta: str
    fichero: str
    estado: str
    chars: int
    nota: str


def anclajes_sin_texto(
    nombres_por_etiqueta: "Mapping[str, Sequence[Mapping[str, object]]]",
    etiquetas_verdes: "Iterable[str]",
) -> tuple[AnclajeDudoso, ...]:
    """Las etiquetas marcadas 🟢 que el censo no puede sostener.

    Basta **una** copia con `estado: ok` para sostener el anclaje: la
    redundancia del intake es real y rescató tres documentos nucleares en
    W-02USSI (la demanda por la copia del CRM, el desistimiento por el jpg de
    E&V, el encargo por el export de WhatsApp).

    Una etiqueta sin ninguna entrada en el censo sale con `estado="ausente"`,
    que no es lo mismo que sin texto y hay que poder distinguirlo.
    """
    dudosos: list[AnclajeDudoso] = []
    for etiqueta in etiquetas_verdes:
        entradas = list(nombres_por_etiqueta.get(etiqueta) or [])
        if not entradas:
            dudosos.append(AnclajeDudoso(etiqueta, "", "ausente", 0, ""))
            continue
        if any(str(e.get("estado")) == "ok" for e in entradas):
            continue
        peor = entradas[0]
        dudosos.append(AnclajeDudoso(
            etiqueta,
            str(peor.get("rel_path") or ""),
            str(peor.get("estado") or ""),
            int(peor.get("chars") or 0),
            str(peor.get("nota") or ""),
        ))
    return tuple(dudosos)
```

Y añadir el import necesario en la cabecera del módulo, junto al de `Sequence`:

```python
from collections.abc import Iterable, Mapping, Sequence
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest -q --tb=short tests/test_cruzar_documental.py`
Expected: PASS, 22 tests.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/demanda-honorarios-ev/scripts/cruzar_documental.py tests/test_cruzar_documental.py
git commit -m "skill(demanda-honorarios-ev): el anclaje verde exige estado ok en el censo (spec 6.1)"
```

---

## Task 4: `references/donde-esta-cada-cosa.md` + guard anti-podredumbre

**Files:**
- Create: `.claude/skills/demanda-honorarios-ev/references/donde-esta-cada-cosa.md`
- Modify: `tests/test_skill_demanda_honorarios_ev.py` (añadir clase)

**Interfaces:**
- Consumes: `_skill_dir()` de la Task 1.
- Produces: el fichero de referencia que la Task 8 enlaza desde el `SKILL.md`.

- [ ] **Step 1: Write the failing test**

Añadir al final de `tests/test_skill_demanda_honorarios_ev.py`:

```python
class TestDondeEstaCadaCosa:
    """El reference nombra artefactos del expediente. Si el código los renombra,
    la skill queda mintiendo en silencio — y una skill que miente sobre dónde
    está el encargo es peor que ninguna."""

    @staticmethod
    def _texto() -> str:
        return (_skill_dir() / "references" / "donde-esta-cada-cosa.md").read_text(encoding="utf-8")

    def test_nombra_los_tres_censos_en_orden_de_preferencia(self):
        t = self._texto()
        for artefacto in ("_caso.md", "_cobertura.json", "indice_documental.yaml"):
            assert artefacto in t, f"el reference no nombra {artefacto}"

    def test_los_nombres_de_artefacto_siguen_existiendo_en_el_codigo(self):
        """Guard de podredumbre: los nombres que el reference promete tienen que
        seguir siendo los que el core escribe."""
        import core.config as config

        assert config.ENTREVISTAS_SUBDIR  # el módulo carga
        raiz = Path(__file__).resolve().parents[1]
        fuentes = "\n".join(
            p.read_text(encoding="utf-8", errors="replace")
            for p in [
                raiz / "core" / "case_manager.py",
                raiz / "core" / "sala_maquina.py",
                raiz / "core" / "sync_sudespacho.py",
            ]
            if p.exists()
        )
        assert "_caso.md" in fuentes
        assert "_cobertura.json" in fuentes

    def test_declara_el_fallback_de_no_adivinar_rutas(self):
        t = self._texto().lower()
        assert "no se adivinan rutas" in t or "no adivina rutas" in t

    def test_advierte_que_la_ruta_canonica_del_crm_puede_no_resolver(self):
        """Lo medido: `id_carpeta 304` sin mapear mandó 23 documentos a
        `99_Sin categoria`. Un reference que no lo advierta invita al defecto."""
        t = self._texto()
        assert "99_Sin categoria" in t
        assert "MEJORAS #192" in t
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -q --tb=short tests/test_skill_demanda_honorarios_ev.py::TestDondeEstaCadaCosa`
Expected: FAIL — `FileNotFoundError` sobre `donde-esta-cada-cosa.md`.

- [ ] **Step 3: Escribir el reference**

Crear `.claude/skills/demanda-honorarios-ev/references/donde-esta-cada-cosa.md` con **el contenido del §6 del spec**, expandido así:

1. **Cabecera con la regla en una frase:** «los documentos se resuelven por CENSO y por ROL, nunca por ruta canónica», y la medición que la sostiene (los 23 + 9 documentos de W-02USSI en `99_Sin categoria` y `99_Otros` por el `id_carpeta 304` sin mapear, `MEJORAS #192`).
2. **Tabla del orden de preferencia** con las cuatro filas del §6 del spec: `_caso.md` → `sudespacho_expedientes[].doc_ids` y el rol `demanda_doc_id`; `_cobertura.json`; `indice_documental.yaml`; y el fallback «**no se adivinan rutas**: se dice qué falta correr (`scripts.sala_maquina apply`, `organizar-sala-lectura`) y se sigue con lo que haya, declarando qué eslabones quedan sin resolver».
3. **Sección «El anclaje deja de ser un juicio»** con la regla del §6.1 y el puntero a `scripts/cruzar_documental.py::anclajes_sin_texto`.
4. **Sección «Cautelas medidas»**: `estado: empty` mezcla «no tiene texto» y «no pude leerlo» (`MEJORAS #190`), así que se lee también `nota`; y basta una copia con `estado: ok` para sostener el anclaje.
5. **Tabla «el eslabón y su documento»**: por cada uno de los cinco eslabones del §5, qué rol o qué patrón de nombre lo resuelve.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest -q --tb=short tests/test_skill_demanda_honorarios_ev.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/demanda-honorarios-ev/references/donde-esta-cada-cosa.md tests/test_skill_demanda_honorarios_ev.py
git commit -m "skill(demanda-honorarios-ev): resolucion de documentos por censo y por rol, con guard de podredumbre"
```

---

## Task 5: `references/cadena-de-devengo.md`

**Files:**
- Create: `.claude/skills/demanda-honorarios-ev/references/cadena-de-devengo.md`

**Interfaces:**
- Consumes: nada.
- Produces: el reference que la Task 8 enlaza y que alimenta el paso 7 de `preparacion-litigio-civil`.

- [ ] **Step 1: Escribir el reference**

Crear el fichero con **el §5 y el §5.1 del spec**, expandidos así:

1. **La tabla de los cinco eslabones** tal cual (§5 del spec).
2. **Una sección por cada `TIPOS_CASO_ACTORA`** —siete— diciendo, en tres líneas: qué eslabón se rompe, qué documento lo acredita, y qué módulo de Hecho debe existir en `HECHOS_X.md`. Los siete nombres y sus glosas se copian de `core/config.py::TIPOS_CASO_ACTORA`, que es la fuente única.
3. **El núcleo doctrinal** con las tres citas ya verificadas contra CENDOJ el 2026-09-09, con sus datos oficiales: **STS 685/2012, de 19-11-2012** (ROJ STS 8018/2012, ECLI:ES:TS:2012:8018, Sala 1ª, ponente Sancho Gargallo, rec. 978/2010 — «reclamación de los honorarios de éxito»); **STS 774/2011, de 10-11-2011** (ROJ STS 9245/2011, ECLI:ES:TS:2011:9245, ponente Xiol Ríos, rec. 1544/2009 — «contrato de mediación o corretaje para la venta de inmuebles»); **STS 713/2010, de 15-11-2010** (ROJ STS 6254/2010, ECLI:ES:TS:2010:6254, ponente Xiol Ríos, rec. 2637/2005 — fuentes del corretaje por analogía). **Con la advertencia de que el nº de resolución es el que va en el texto y el ROJ en la nota al pie**, nunca al revés.
4. **El §5.1 íntegro**: las condiciones del contrato privado como parte del eslabón 4, con sus tres obligaciones en orden y la comprobación del modo revisión en una línea.
5. **La regla de la estipulación**: se transcribe como texto, nunca solo como imagen, y la paráfrasis casa rama por rama.
6. **Aviso de doctrina adversa**: la doctrina del TS de que el corretaje «se halla sometido a la condición suspensiva de la celebración del contrato pretendido» opera **salvo pacto**, y el pacto es el eslabón 2. Enlace a la familia 7 del catálogo.

- [ ] **Step 2: Comprobar que los siete tipos están y coinciden con el código**

Run:
```bash
python -c "from core import config; import pathlib; t = pathlib.Path('.claude/skills/demanda-honorarios-ev/references/cadena-de-devengo.md').read_text(encoding='utf-8'); faltan = [k for k in config.TIPOS_CASO_ACTORA if k not in t]; print('faltan:', faltan or 'ninguno')"
```
Expected: `faltan: ninguno`

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/demanda-honorarios-ev/references/cadena-de-devengo.md
git commit -m "skill(demanda-honorarios-ev): la cadena de devengo y las condiciones del contrato privado"
```

---

## Task 6: `references/puertas-de-dominio.md`

**Files:**
- Create: `.claude/skills/demanda-honorarios-ev/references/puertas-de-dominio.md`

**Interfaces:**
- Consumes: nada.
- Produces: el reference que la Task 8 enlaza.

- [ ] **Step 1: Escribir el reference**

Crear el fichero con **la tabla de siete puertas del §7 del spec**, y por cada una cuatro campos: **qué es · su fuente con pinpoint · cómo falla · qué prueba la cierra**. Los preceptos van con su cita verificada:

- **art. 812.1.2ª LEC** y **art. 813 LEC** — texto consolidado BOE-A-2000-323. Del 813 se transcribe literal el párrafo tercero («…el deudor es localizado en otro partido judicial, el juez dictará auto dando por terminado el proceso…»), porque es la consecuencia y sin ella la puerta no se entiende.
- **art. 815 LEC** — el riesgo de no localización, con la regla operativa: si algún requerimiento previo volvió **fallido**, es bandera roja del cauce.
- **arts. 1964.2 CC** (prescripción) y **Ley 3/2004** (intereses **desde la factura, no desde una proforma**).
- **IVA sobre honorarios** con las tres resoluciones ya verificadas: **SAP Madrid 530/2014, de 23-12-2014** (ROJ SAP M 18304/2014, ECLI:ES:APM:2014:18304, ponente Legido Gil, rec. 359/2013), **SAP Valencia 103/2014, de 20-03-2014, Sección 11ª** (ROJ SAP V 2062/2014, ECLI:ES:APV:2014:2062, ponente López Orellana, rec. 555/2013) y **SAP Cádiz 285/2011, de 16-11-2011, Sección 2ª** (ROJ SAP CA 1493/2011, ECLI:ES:APCA:2011:1493, ponente Ruiz de Velasco, rec. 441/2011). **Con la marca ⚠️ sobre la de Valencia**: su *ratio* contiene doctrina adversa al devengo (ver familia 7 del catálogo).
- **Autorización del cauce**: si el CRM dice monitorio, exigir constancia nombrada (actuación, correo o hilo) y, si no la hay, **parar y preguntar**.

Y la regla de cierre, que es la que hace honesto el informe: **una puerta que no se pudo comprobar se declara «sin verificar», nunca «cumplida»**.

- [ ] **Step 2: Comprobar que las siete puertas están**

Run:
```bash
python -c "import pathlib; t = pathlib.Path('.claude/skills/demanda-honorarios-ev/references/puertas-de-dominio.md').read_text(encoding='utf-8'); faltan = [x for x in ['812.1.2', '813', '815', '1964.2', '3/2004', 'IVA', 'autorizaci'] if x not in t]; print('faltan:', faltan or 'ninguna')"
```
Expected: `faltan: ninguna`

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/demanda-honorarios-ev/references/puertas-de-dominio.md
git commit -m "skill(demanda-honorarios-ev): las siete puertas de dominio, con sus preceptos anclados"
```

---

## Task 7: `references/catalogo-de-defectos.md` + guard de las ocho familias

**Files:**
- Create: `.claude/skills/demanda-honorarios-ev/references/catalogo-de-defectos.md`
- Modify: `tests/test_skill_demanda_honorarios_ev.py` (añadir clase)

**Interfaces:**
- Consumes: `_skill_dir()` de la Task 1.
- Produces: el reference que la Task 8 enlaza; es el corazón del modo revisión.

- [ ] **Step 1: Write the failing test**

Añadir al final de `tests/test_skill_demanda_honorarios_ev.py`:

```python
class TestCatalogoDeDefectos:
    """El conteo del catálogo se descuadra al editar: me pasó tres veces en el
    propio spec, en la misma sesión. El guard lo hace imposible en silencio."""

    _FAMILIAS = (
        "Puerta de cauce sin comprobar",
        "Documento invocado que no está en el ramo",
        "Documento del ramo que el escrito no cita",
        "Título documental débil",
        "Contradicción interna entre párrafos",
        "Paráfrasis que no casa con la cláusula",
        "Cita de apoyo cuya",
        "Parte contractual omitida",
    )

    @staticmethod
    def _texto() -> str:
        return (_skill_dir() / "references" / "catalogo-de-defectos.md").read_text(encoding="utf-8")

    def test_estan_las_ocho_familias(self):
        t = self._texto()
        faltan = [f for f in self._FAMILIAS if f not in t]
        assert not faltan, f"familias ausentes del catálogo: {faltan}"

    def test_el_catalogo_declara_exactamente_ocho(self):
        assert "ocho familias" in self._texto().lower()

    def test_el_skill_md_no_contradice_el_conteo(self):
        """El descuadre real es entre el catálogo y quien lo resume."""
        skill = (_skill_dir() / "SKILL.md").read_text(encoding="utf-8").lower()
        assert "seis familias" not in skill
        assert "siete familias" not in skill

    def test_las_familias_mecanizables_apuntan_al_script(self):
        t = self._texto()
        assert "cruzar_documental.py" in t

    def test_declara_la_metarregla_de_la_frontera(self):
        t = self._texto().lower()
        assert "de qué frontera es esto un ejemplo" in t
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -q --tb=short tests/test_skill_demanda_honorarios_ev.py::TestCatalogoDeDefectos`
Expected: FAIL — `FileNotFoundError` sobre `catalogo-de-defectos.md`.

- [ ] **Step 3: Escribir el reference**

Crear el fichero con **las ocho familias del §8 del spec**, cada una con cuatro campos: **síntoma · cómo se detecta · fuente · consecuencia**. Requisitos que el guard comprueba y que hay que respetar literalmente:

- El texto dice «**ocho familias**».
- Los ocho títulos contienen las cadenas de `_FAMILIAS` del test.
- Las familias 2 y 3 remiten a `scripts/cruzar_documental.py`.
- Cierra con la meta-regla: ante cada hallazgo, «**¿de qué frontera es esto un ejemplo?**» antes de remediarlo.

Y, por cada familia, el ejemplo **medido** con datos sintéticos —el defecto tal como se manifestó, sin identificar a nadie—, más el desarrollo de las dos nuevas del spec rev. 2: la 7 (cita de apoyo con *ratio* adversa: identidad verificada no basta, hay que leer supuesto de hecho y *ratio*) y la 8 (parte contractual omitida: cotejar la comparecencia del contrato privado contra el hecho que identifica a las partes).

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest -q --tb=short tests/test_skill_demanda_honorarios_ev.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/demanda-honorarios-ev/references/catalogo-de-defectos.md tests/test_skill_demanda_honorarios_ev.py
git commit -m "skill(demanda-honorarios-ev): catalogo de ocho familias de defecto, con guard de conteo"
```

---

## Task 8: El cuerpo del `SKILL.md`, las evals y el CHANGELOG

**Files:**
- Modify: `.claude/skills/demanda-honorarios-ev/SKILL.md` (sustituir el cuerpo marcador de la Task 1)
- Create: `.claude/skills/demanda-honorarios-ev/evals/evals.json`
- Modify: `.claude/skills/demanda-honorarios-ev/CHANGELOG.md`

**Interfaces:**
- Consumes: los cuatro `references/` (Tasks 4-7) y `scripts/cruzar_documental.py` (Tasks 2-3).
- Produces: la skill completa y lista para empaquetar.

- [ ] **Step 1: Escribir el cuerpo del `SKILL.md`**

Secciones, en este orden:

1. **Qué resuelve** y **la frontera** (§2 del spec), con la frase que el spec exige decir en voz alta: **la v1 revisa mejor de lo que prepara**, porque hay un escrito real que auditar y ninguno aprobado que imitar.
2. **Cuándo se activa** y los falsos amigos: no se activa en posición defensiva (`TIPOS_CASO_DEFENSIVA`), ni para valorar viabilidad, ni para generar el `.docx`.
3. **Coordinación: quién posee qué** — el diagrama del §3 del spec, tal cual. Es la sección que impide que la skill se reimplemente sola.
4. **Fase 0: las tres resoluciones** (§4 del spec), con la regla dura: `tipo_caso`, modo y cauce se **leen**; nunca del nombre de la carpeta.
5. **Modo PREPARAR** — qué rellena de los maestros de `preparacion-litigio-civil` y en qué paso entra cada reference.
6. **Modo REVISAR** — el recorrido: censo → puertas → catálogo → los checklists de las otras dos skills, y el informe con sus **dos secciones no fusionables** (hallazgos por gravedad; puertas comprobadas y **no comprobadas**). Con la línea roja: **el informe se escribe fuera del repo** porque lleva PII de terceros.
7. **Recursos bundleados** — tabla con los cuatro `references/` y cuándo leer cada uno.
8. **Lo que la v1 NO trae** — sin plantilla maestra, y por qué: entra con el primer escrito aprobado por el letrado.
9. **Mejora continua** — telemetría por `scripts/registrar_uso.py`, y el puntero a `docs/MEJORA_CONTINUA_SKILLS.md`.

- [ ] **Step 2: Escribir las evals**

Crear `.claude/skills/demanda-honorarios-ev/evals/evals.json`, siguiendo la forma de `preparacion-audiencia-previa/evals/evals.json` (`{skill_name, evals: [{id, name, prompt, expected_output, files}]}`), con tres evals y **datos sintéticos**:

- `id 0`, `revisar_borrador_ocho_familias`: prompt de revisión de un borrador; `expected_output` = informe con las dos secciones y las ocho familias comprobadas.
- `id 1`, `preparar_negativa_escritura`: prompt de preparación; `expected_output` = módulos de Hecho de los cinco eslabones con su anclaje verificado contra el censo, y las condiciones del contrato privado inventariadas.
- `id 2`, `para_si_el_cauce_es_monitorio_sin_autorizacion`: prompt con `tipo_procedimiento = monitorio` y sin constancia; `expected_output` = **la skill para y pregunta**, no redacta.

Con esta nota literal dentro del JSON, como campo `"aviso"` del objeto raíz:

> «Las evals 0 y 1 están sembradas del caso que parió la skill: son una **regresión**, no una generalización. Lo que prueba la skill es el segundo caso.»

- [ ] **Step 3: Actualizar el CHANGELOG**

Entrada `## 1.0 — 2026-09-09` con: nacimiento de la skill, el spec del que sale, las ocho familias, el script, y las dos aportaciones a `preparacion-litigio-civil`.

- [ ] **Step 4: Run tests to verify everything passes**

Run: `python -m pytest -q --tb=short tests/test_skill_demanda_honorarios_ev.py tests/test_cruzar_documental.py tests/test_skill_descriptions_no_xml.py tests/test_validate_skills_roles.py`
Expected: PASS.

- [ ] **Step 5: Comprobar el JSON y el validador**

Run:
```bash
python -c "import json,pathlib; d=json.loads(pathlib.Path('.claude/skills/demanda-honorarios-ev/evals/evals.json').read_text(encoding='utf-8')); print(d['skill_name'], len(d['evals']), 'aviso' in d)"
```
Expected: `demanda-honorarios-ev 3 True`

Run: `python -m scripts.validate_skills`
Expected: cero avisos que mencionen `demanda-honorarios-ev`.

- [ ] **Step 6: Commit**

```bash
git add .claude/skills/demanda-honorarios-ev
git commit -m "skill(demanda-honorarios-ev): cuerpo del SKILL.md, evals sembradas y changelog"
```

---

## Task 9: Las dos aportaciones a `preparacion-litigio-civil`

**Files:**
- Modify: `.claude/skills/preparacion-litigio-civil/SKILL.md:91-103` (paso 5) y `:120-123` (paso 8)
- Modify: `.claude/skills/preparacion-litigio-civil/CHANGELOG.md`
- Test: `tests/test_skill_preparacion_litigio_civil_masc.py`

**Interfaces:**
- Consumes: nada.
- Produces: el bloque MASC del paso 5, que el modo preparar de `demanda-honorarios-ev` da por existente.

- [ ] **Step 1: Write the failing test**

Crear `tests/test_skill_preparacion_litigio_civil_masc.py`:

```python
"""El paso 5 tiene que preguntar por el MASC.

La skill es v1.0 y la LO 1/2025 impone la actividad negociadora previa como
requisito de procedibilidad de todo declarativo civil: sin este bloque, la fase
estratégica del despacho puede cerrarse sin haberlo mirado. Pasó en W-02USSI.
"""
from __future__ import annotations

from pathlib import Path


def _skill() -> str:
    p = (Path(__file__).resolve().parents[1] / ".claude" / "skills"
         / "preparacion-litigio-civil" / "SKILL.md")
    return p.read_text(encoding="utf-8")


def test_el_paso_5_pregunta_por_el_masc():
    t = _skill()
    assert "MASC" in t
    assert "1/2025" in t


def test_nombra_los_cuatro_preceptos_que_deciden():
    t = _skill()
    for precepto in ("5.2", "7.3", "10.4", "264.4"):
        assert precepto in t, f"falta el art. {precepto}"


def test_distingue_las_dos_ramas_del_plazo_de_un_ano():
    """El error caro: invocar la rama de «sin respuesta» cuando hubo respuesta
    acorta el plazo contra uno mismo."""
    t = _skill().lower()
    assert "sin respuesta" in t
    assert "terminación del proceso" in t or "terminacion del proceso" in t


def test_recoge_el_10_4_d_como_palanca():
    t = _skill().lower()
    assert "10.4.d" in t


def test_el_paso_8_deja_escrito_el_criterio_del_burofax_del_letrado_contrario():
    t = _skill()
    assert "21 EGAE" in t
    assert "burofax" in t.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -q --tb=short tests/test_skill_preparacion_litigio_civil_masc.py`
Expected: FAIL — `assert "MASC" in t`.

- [ ] **Step 3: Añadir el bloque MASC al paso 5**

En `.claude/skills/preparacion-litigio-civil/SKILL.md`, dentro del paso 5 y **después** de la viñeta de `Documental`, añadir:

```markdown
- **MASC (requisito de procedibilidad, LO 1/2025).** Bloque obligatorio en todo
  declarativo civil desde abril de 2025. Verificado contra el texto consolidado
  BOE-A-2025-76:
  - **¿Es exigible?** Art. 5.2: sí en «todos los procesos declarativos del libro II
    y los procesos especiales del **libro IV**» de la LEC. La lista de excepciones
    incluye el **juicio cambiario** y **no** el monitorio; el art. 5.3 exceptúa el
    **monitorio europeo**, no el español.
  - **¿Qué MASC se usó y cuándo se recibió?** Fecha de recepción por la contraparte,
    con su acreditación (art. 10.2: a falta de documento firmado por ambas partes,
    cualquier documento que pruebe que la otra parte recibió la solicitud y pudo
    acceder a su contenido íntegro).
  - **¿En qué rama estamos del plazo del art. 7.3?** Un año, «respectivamente»:
    desde la **recepción de la solicitud** si NO hubo respuesta, o desde la
    **terminación del proceso negociador** si la hubo. **Alegar la rama equivocada
    acorta el plazo contra uno mismo**, así que la rama se decide con la prueba
    delante, no con la que suene mejor.
  - **¿Cuándo terminó sin acuerdo?** Es el art. **10.4** (a-d), no el 7.3. Fijar la
    letra aplicable y su fecha.
  - **Palanca disponible:** el art. **10.4.d** — un escrito a la contraparte dando
    por terminadas las negociaciones fija fecha documentada y reinicia el año.
  - **¿Está el documento del art. 264.4ª LEC** que acredita el intento? Sin él la
    demanda no se admite.
```

- [ ] **Step 4: Añadir el criterio al paso 8**

En el paso 8, tras el párrafo existente, añadir:

```markdown
**Criterio del despacho sobre el burofax del letrado contrario (escrito el 2026-09-09).**
Un **burofax** del letrado de la contraparte, remitido a esta parte y que acusa recibo de
nuestro requerimiento, se ha aportado como documental. Un **intercambio de correos entre
letrados con aviso de confidencialidad**, no: se recorta o se omite. La distinción es la que
resolvió el asunto W-02USSI y queda aquí para que no se decida dos veces. Ante la duda —un
burofax que sí lleve aviso, un correo sin él— la decisión es del Abogado Titular y se anota
en `PREPARACION_X.md`.
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest -q --tb=short tests/test_skill_preparacion_litigio_civil_masc.py`
Expected: PASS, 5 tests.

- [ ] **Step 6: Actualizar el CHANGELOG de la skill modificada**

Entrada nueva en `.claude/skills/preparacion-litigio-civil/CHANGELOG.md`: versión `1.1`, con el bloque MASC del paso 5 y el criterio deontológico del paso 8. Y **subir `version` a `"1.1"`** en su frontmatter.

- [ ] **Step 7: Commit**

```bash
git add .claude/skills/preparacion-litigio-civil tests/test_skill_preparacion_litigio_civil_masc.py
git commit -m "skill(preparacion-litigio-civil): bloque MASC en el paso 5 y criterio deontologico en el paso 8"
```

---

## Cierre: verificación, revisión adversarial y entrega

- [ ] **Suite completa con las dos semillas.** `python -m scripts.session_close`. Cualquier variación del conteo que no esté explicada es bandera roja y se explica en el bloque de cierre.
- [ ] **Cobertura del diff.** `session_close` la mide y avisa (umbral 90 %). La respuesta por defecto ante un aviso es **escribir el test**, no bajar el umbral.
- [ ] **Empaquetado, desde la raíz del repo** (no desde el worktree: `dist/` está gitignorado y no existe aquí). `python scripts/package_skill.py demanda-honorarios-ev` y `python scripts/package_skill.py preparacion-litigio-civil`. Verificar **la versión dentro del zip**, nunca la fecha del fichero.
- [ ] **Revisión adversarial: UNA ronda, sobre el diff.** Codex en solo lectura, informe a un fichero **fuera del repo**, devuelve ruta y `sha256`. La adjudicación va **embebida** en este plan con su encabezado canónico; el informe literal va a un **acta hermana** con el sufijo `-r<N>-adversarial-review.md` sobre el nombre de este fichero (el `-r<N>` no es opcional). Guards G7/G8 de `tests/test_docs_gobernanza.py` lo comprueban y recomputan el digest.

  > **Nota de método, aprendida al escribir este plan.** La primera versión citaba el acta por su ruta completa y `test_citas_a_specs_y_plans_existen` la rechazó, con razón: el fichero no existe hasta que la revisión corre, y crear un stub para callar al guard sería fingir una revisión que nadie ha hecho. Se nombra la **convención**, no la ruta.
- [ ] **PR** con el check `leak-scan`, y `PLAN.md` al día con la etiqueta y el hash.
- [ ] **Re-import en Cowork** de las dos skills: sin eso, Paola, Ana y Sergio siguen con la versión anterior. Es el fallo de «el guard no ve lo desplegado»: fuente ✅, build ✅, instalado ❌ — y solo la tercera importa.

---

## Self-Review

**Cobertura del spec.** §2 → T1 (frontmatter y alcance) y T8 (frontera). §3 → T8 paso 3. §4 → T8 paso 4. §5 y §5.1 → T5. §6 y §6.1 → T4 y T3. §7 → T6. §8 → T7. §9.1 y §9.2 → T9. §10 → T8 pasos 5-6. §11 → T1 (estructura) y T8. §12 → T8 paso 2 y los guards de T1/T4/T7. §13 (decisiones cerradas) → recogidas en Global Constraints y en T8. §14 (backlog) → ya commiteado, no es trabajo de este plan. §15 → Cierre. **Sin huecos.**

**Placeholders.** Ninguno de los prohibidos. Los `references/` no llevan su prosa íntegra pero **no son «TBD»**: apuntan a secciones concretas de un spec commiteado y enumeran los requisitos que sus guards comprueban, más las citas oficiales verificadas con sus datos completos.

**Consistencia de tipos.** `Remision(etiqueta, linea)`, `CruceDocumental(citados_sin_documento, documentos_sin_citar)` y `AnclajeDudoso(etiqueta, fichero, estado, chars, nota)` se definen en T2/T3 y se usan con esos mismos nombres. `_skill_dir()` se define en T1 y la reutilizan T4 y T7. `ESTADOS_SIN_TEXTO` solo en T3. El import de `Iterable`/`Mapping` se añade explícitamente en T3 paso 3.
