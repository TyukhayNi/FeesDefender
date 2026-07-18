# Apertura B1–B5 · PR-3 (B1: ficha CRM end-to-end) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rellenar la **ficha CRM completa** de un expediente extrajudicial: tags equipo+ciudad en el alta, y un subcomando reentrante `crm-ficha` que vincula cliente propio EV, contrario y colaboradores y escribe las Notas — todo a partir de un `_ficha_crm.yaml` revisable.

**Architecture:** Patrón biblioteca. (1) El alta se enriquece con los tags equipo(rojo)+ciudad(azul) derivados del `codigo` en `crm_payload` (cerebro puro). (2) Un nuevo par puro+IO en `core/sudespacho_create.py` (`merge_expediente_update` puro + `get_expediente`/`update_expediente` IO) da el round-trip PUT que preserva `Numero_Expediente`. (3) `core/crm_ficha.py` (nuevo, puro) modela y carga el `_ficha_crm.yaml` → `FichaCRMInput`. (4) `scripts/crm_ficha.py` (nuevo) orquesta `link_ev_mmc` + `ensure_contrario_vinculado` + `ensure_colaborador_vinculado` + `update_expediente(Notas)`, con GET de verificación.

**Tech Stack:** Python 3, Typer, `dataclasses`, `httpx`, `yaml`, `pytest` (+ `unittest.mock` para httpx). Sin dependencias nuevas.

**Spec:** `docs/superpowers/specs/2026-07-18-apertura-expediente-b1-b5-design.md` (§7). SSOT CRM: `docs/INTEGRACION_SUDESPACHO.md` §10–§11.

## Global Constraints

- **Plataforma:** Windows. Encoding **UTF-8 sin BOM**.
- **Worktree:** editar SOLO en este worktree; **nunca** `cd`/ruta absoluta a la raíz compartida.
- **pytest** con el intérprete del repo principal desde la raíz del worktree:
  `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest <ruta>::<test> -v`.
  Conteo global: `--junit-xml`. Los 5 fallos `test_sudespacho_relations::test_list_colaboradores_rest_*` son **ambientales** (falta `SUDESPACHO_*`), no regresión.
- **`main` protegida:** rama + PR, `leak-scan` verde. Nunca push directo ni `--no-verify`.
- **No tocar** `core/anon/`. **PII por W-code** en docs/commits/ramas; los datos reales de contrario/colaboradores (nombre/NIF/email/móvil) **solo** viven en `data/CASOS/<caso>/00_Input/_ficha_crm.yaml` (gitignored), **nunca** en el repo, tests ni chat. Los tests usan datos sintéticos.
- **Rama:** `claude/apertura-pr3-ficha-crm` (ya creada desde `main` con PR-1). **No toca `scripts/abrir_caso.py`** (evita conflicto con PR-2 #71).
- **Tarifa/precio_hora:** confidencial, **solo por UI**. Este PR NO crea actuaciones facturables.
- **Datos REST confirmados** (`core/sudespacho_create.py`): `_REST_BASE = "https://api-crm-commons-pro.sudespacho.biz"` (`:89`), `_REST_TIMEOUT = 60` (`:90`), `_REST_CREATE_EXTRAJUDICIAL = "/api/element_register/extrajudiciales"` (`:101`), `_get_api_key()` (`:134`), patrón `_rest_post` (`:1434-1485`, httpx + headers `x-api-key`/`Content-Type`/`Accept`, `SudespachoCreateError`). Campos del registro extrajudicial: `Referencia_Cliente`, `Notas`, `Numero_Expediente`, `tags`, `cuantia`, `total`, `tnm_posicionprocesal`, … (`:1194-1228`).
- **Primitivas existentes** (`core/sudespacho_relations.py`, PR #53): `ensure_contrario_vinculado(exp_id, datos: NuevoClienteContrario) -> tuple[str,bool]` (dedup NIF), `ensure_colaborador_vinculado(exp_id, datos: NuevoColaborador, *, client=None) -> tuple[str,bool]` (dedup email), `link_ev_mmc(exp_id, *, cliente_propio_id=EV_MMC_SPAIN_ID, client=None) -> None`. DTOs (con normalización de teléfono B3 ya en `main`): `NuevoClienteContrario(nombre, apellido1, apellido2, email, movil, nif, direccion, poblacion)`, `NuevoColaborador(nombre, email, movil, telefono, nif, grupos, usuarios)`.
- TDD estricto, DRY, YAGNI, commits frecuentes.

**Nota de diseño (deviación consciente de la spec §7.1):** el tag azul de ciudad se deriva del **prefijo de 2 letras del `codigo`** (`Ba/Ma/Va/Bi/Sa/Se`), no de un `--ciudad` en `Identidad`. Motivo: evita cambiar `resolver_identidad`/`Identidad`/`scripts/abrir_caso.py` (que PR-2 reescribió → conflicto de merge). El prefijo del `codigo` de equipo ES la ciudad por construcción (`{ciudad(2)}{tipo_op(2)}{nº}`, INTEGRACION §11.3).

---

### Task 1: Mapas de tags equipo(rojo) + ciudad(azul)

**Files:**
- Modify: `core/sudespacho_create.py` (añadir 2 funciones tras `tag_defaults_for_tipo_caso`, `:982-1046`; usan las constantes `TAG_ROJO_*` `:284-357` y `TAG_AZUL_*` `:266-272`)
- Test: `tests/test_sudespacho_create.py`

**Interfaces:**
- Consumes: nada.
- Produces:
  - `tag_rojo_equipo(codigo: str) -> str | None` → token del tag rojo del equipo (`TAG_ROJO_<codigo>`), o `None` si el código no tiene tag.
  - `tag_azul_de_codigo(codigo: str) -> str | None` → token del tag azul de ciudad derivado del prefijo de 2 letras del `codigo`, o `None`.

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `tests/test_sudespacho_create.py`:

```python
from core.sudespacho_create import (
    tag_rojo_equipo, tag_azul_de_codigo,
    TAG_ROJO_BaRS11, TAG_AZUL_BARCELONA, TAG_AZUL_MADRID,
)


def test_tag_rojo_equipo_conocido():
    assert tag_rojo_equipo("BaRS11") == TAG_ROJO_BaRS11


def test_tag_rojo_equipo_desconocido_es_none():
    assert tag_rojo_equipo("ZzZZ99") is None


@pytest.mark.parametrize("codigo,esperado", [
    ("BaRS11", TAG_AZUL_BARCELONA),
    ("BaCR1", TAG_AZUL_BARCELONA),
    ("MaRS2", TAG_AZUL_MADRID),
])
def test_tag_azul_de_codigo(codigo, esperado):
    assert tag_azul_de_codigo(codigo) == esperado


def test_tag_azul_de_codigo_prefijo_desconocido_es_none():
    assert tag_azul_de_codigo("ZzRS1") is None
```

(Verificar que `import pytest` ya está en el fichero; si no, añadirlo.)

- [ ] **Step 2: Ejecutar para verificar que fallan**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest tests/test_sudespacho_create.py -k "tag_rojo_equipo or tag_azul_de_codigo" -v`
Expected: FAIL con `ImportError: cannot import name 'tag_rojo_equipo'`.

- [ ] **Step 3: Implementar las funciones**

Añadir a `core/sudespacho_create.py`, tras `tag_defaults_for_tipo_caso` (`:1046`):

```python
import sys as _sys

# Prefijo de 2 letras del código de equipo → tag azul de ciudad.
# El código de equipo es "{ciudad(2)}{tipo_op(2)}{nº}" (INTEGRACION §11.3),
# así que sus 2 primeras letras identifican la plaza sin ambigüedad.
_PREFIJO_CIUDAD_A_TAG_AZUL: dict[str, str] = {
    "Ba": TAG_AZUL_BARCELONA,
    "Ma": TAG_AZUL_MADRID,
    "Va": TAG_AZUL_VALENCIA,
    "Bi": TAG_AZUL_BILBAO,
    "Sa": TAG_AZUL_SANTANDER,
    "Se": TAG_AZUL_SEVILLA,
}


def tag_rojo_equipo(codigo: str) -> str | None:
    """Token del tag rojo de equipo para un código (p. ej. "BaRS11"), o None.

    Resuelve la constante ``TAG_ROJO_<codigo>`` de este módulo (las constantes se
    nombran exactamente así: ``TAG_ROJO_BaRS11``).
    """
    return getattr(_sys.modules[__name__], f"TAG_ROJO_{codigo}", None)


def tag_azul_de_codigo(codigo: str) -> str | None:
    """Token del tag azul de ciudad derivado del prefijo de 2 letras del código, o None."""
    return _PREFIJO_CIUDAD_A_TAG_AZUL.get(codigo[:2])
```

- [ ] **Step 4: Ejecutar para verificar que pasan**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest tests/test_sudespacho_create.py -k "tag_rojo_equipo or tag_azul_de_codigo" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/sudespacho_create.py tests/test_sudespacho_create.py
git commit -m "feat(crm): mapas tag_rojo_equipo + tag_azul_de_codigo (B1)"
```

---

### Task 2: `crm_payload` enriquece el alta con equipo + ciudad

**Files:**
- Modify: `core/abrir_caso.py` (`crm_payload`, `:219-238`)
- Test: `tests/test_abrir_caso.py`

**Interfaces:**
- Consumes: `sudespacho_create.tag_rojo_equipo`, `sudespacho_create.tag_azul_de_codigo` (Task 1), `sudespacho_create.tag_defaults_for_tipo_caso` (existente).
- Produces: `crm_payload(identidad, *, cuantia=0.0)` (misma firma) ahora incluye, en orden, el tag rojo de equipo y el azul de ciudad (si existen) **antes** de los defaults verde+lila.

- [ ] **Step 1: Escribir el test que falla**

Añadir a `tests/test_abrir_caso.py`:

```python
def test_crm_payload_incluye_tags_equipo_y_ciudad():
    from core import abrir_caso as brain
    from core import sudespacho_create as sc

    ident = brain.resolver_identidad(
        codigo="BaRS11", direccion="Falsa 1", w_code="W-000AAA", sufijo="Vuelta",
        tipo_caso="VUELTA", nombres_existentes=[], force=True,
    )
    payload = brain.crm_payload(ident, cuantia=1000.0)

    assert sc.tag_rojo_equipo("BaRS11") in payload.tags       # equipo (rojo)
    assert sc.tag_azul_de_codigo("BaRS11") in payload.tags    # ciudad (azul)
    # los defaults de tipo (verde asunto + valoración) siguen presentes
    for t in sc.tag_defaults_for_tipo_caso("VUELTA"):
        assert t in payload.tags
    # orden canónico: rojo primero, azul después, defaults al final
    assert payload.tags.index(sc.tag_rojo_equipo("BaRS11")) == 0
```

- [ ] **Step 2: Ejecutar para verificar que falla**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest tests/test_abrir_caso.py -k crm_payload_incluye_tags -v`
Expected: FAIL (los tags de equipo/ciudad no están en el payload actual).

- [ ] **Step 3: Implementar**

En `core/abrir_caso.py`, en `crm_payload` (`:233-238`), sustituir la construcción del DTO por:

```python
    tags: list[str] = []
    rojo = sc.tag_rojo_equipo(identidad.codigo)
    azul = sc.tag_azul_de_codigo(identidad.codigo)
    if rojo:
        tags.append(rojo)
    if azul:
        tags.append(azul)
    tags += sc.tag_defaults_for_tipo_caso(identidad.tipo_caso)

    return sc.NuevoExpedienteExtrajudicial(
        referencia_cliente=identidad.case_id,
        cuantia=cuantia,
        tags=tags,
        posicion=posicion_crm,
    )
```

- [ ] **Step 4: Ejecutar para verificar que pasa**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest tests/test_abrir_caso.py -k crm_payload -v`
Expected: PASS (el nuevo test + los existentes de `crm_payload`).

- [ ] **Step 5: Commit**

```bash
git add core/abrir_caso.py tests/test_abrir_caso.py
git commit -m "feat(abrir-caso): crm_payload enriquece el alta con tags equipo+ciudad (B1)"
```

---

### Task 3: `get_expediente` + `merge_expediente_update` + `update_expediente`

**Files:**
- Modify: `core/sudespacho_create.py` (añadir tras `create_expediente_rest`, `:1507`)
- Test: `tests/test_sudespacho_create.py`

**Interfaces:**
- Consumes: `_REST_BASE`, `_REST_TIMEOUT`, `_get_api_key`, `_REST_CREATE_EXTRAJUDICIAL`, `SudespachoCreateError` (existentes).
- Produces:
  - `merge_expediente_update(actual: dict, cambios: dict) -> dict` (**puro**): copia de `actual` con `cambios` aplicados, garantizando que `Numero_Expediente` se preserva; lanza `ValueError` si `actual` no trae `Numero_Expediente` válido (no-"0", no vacío).
  - `get_expediente(exp_id: str) -> dict`: GET del registro extrajudicial.
  - `update_expediente(exp_id: str, cambios: dict) -> dict`: GET → merge → PUT; devuelve el registro actualizado.

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `tests/test_sudespacho_create.py`:

```python
from unittest.mock import patch, MagicMock

from core.sudespacho_create import (
    merge_expediente_update, get_expediente, update_expediente, SudespachoCreateError,
)


def test_merge_expediente_update_preserva_numero_y_aplica_cambios():
    actual = {"Numero_Expediente": "49", "Notas": "viejo", "Referencia_Cliente": "X"}
    out = merge_expediente_update(actual, {"Notas": "nuevo"})
    assert out["Numero_Expediente"] == "49"     # preservado
    assert out["Notas"] == "nuevo"              # cambiado
    assert out["Referencia_Cliente"] == "X"     # intacto


def test_merge_expediente_update_no_deja_numero_a_cero():
    # Aunque los cambios intenten ponerlo a "0", se preserva el actual.
    actual = {"Numero_Expediente": "49", "Notas": "v"}
    out = merge_expediente_update(actual, {"Numero_Expediente": "0", "Notas": "n"})
    assert out["Numero_Expediente"] == "49"


def test_merge_expediente_update_lanza_si_actual_sin_numero_valido():
    with pytest.raises(ValueError):
        merge_expediente_update({"Numero_Expediente": "0"}, {"Notas": "n"})
    with pytest.raises(ValueError):
        merge_expediente_update({"Notas": "n"}, {"Notas": "n2"})


def test_get_expediente_hace_get_con_api_key():
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"id": 606, "Numero_Expediente": "49"}
    with patch("core.sudespacho_create._get_api_key", return_value="K"), \
         patch("core.sudespacho_create.httpx.get", return_value=resp) as mget:
        rec = get_expediente("606")
    assert rec["Numero_Expediente"] == "49"
    url = mget.call_args.args[0]
    assert url.endswith("/api/element_register/extrajudiciales/606")
    assert mget.call_args.kwargs["headers"]["x-api-key"] == "K"


def test_update_expediente_round_trip_preserva_numero():
    getresp = MagicMock(status_code=200)
    getresp.json.return_value = {"Numero_Expediente": "49", "Notas": "viejo", "Referencia_Cliente": "X"}
    putresp = MagicMock(status_code=200)
    putresp.json.return_value = {"Numero_Expediente": "49", "Notas": "nuevo", "Referencia_Cliente": "X"}
    with patch("core.sudespacho_create._get_api_key", return_value="K"), \
         patch("core.sudespacho_create.httpx.get", return_value=getresp), \
         patch("core.sudespacho_create.httpx.put", return_value=putresp) as mput:
        out = update_expediente("606", {"Notas": "nuevo"})
    body = mput.call_args.kwargs["json"]
    assert body["Numero_Expediente"] == "49"    # el PUT reenvía el número
    assert body["Notas"] == "nuevo"
    assert out["Notas"] == "nuevo"


def test_get_expediente_error_lanza():
    resp = MagicMock(status_code=404, text="not found")
    resp.json.side_effect = ValueError
    with patch("core.sudespacho_create._get_api_key", return_value="K"), \
         patch("core.sudespacho_create.httpx.get", return_value=resp):
        with pytest.raises(SudespachoCreateError):
            get_expediente("999")
```

- [ ] **Step 2: Ejecutar para verificar que fallan**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest tests/test_sudespacho_create.py -k "merge_expediente_update or get_expediente or update_expediente" -v`
Expected: FAIL con `ImportError`.

- [ ] **Step 3: Implementar**

Añadir a `core/sudespacho_create.py`, tras `create_expediente_rest` (`:1507`):

```python
def _rest_headers() -> dict[str, str]:
    return {
        "x-api-key":    _get_api_key(),
        "Content-Type": "application/json",
        "Accept":       "application/json",
    }


def merge_expediente_update(actual: dict, cambios: dict) -> dict:
    """Fusiona ``cambios`` sobre ``actual`` para un PUT de reemplazo total,
    garantizando que ``Numero_Expediente`` NO se pierde (el PUT es de reemplazo
    completo y un valor "0"/ausente dejaría el expediente sin número).

    Lanza ``ValueError`` si ``actual`` no trae un ``Numero_Expediente`` válido
    (ausente, vacío o "0"): sin un número real que preservar, no es seguro hacer
    el PUT.
    """
    num = str(actual.get("Numero_Expediente", "")).strip()
    if not num or num == "0":
        raise ValueError(
            f"actual sin Numero_Expediente válido ({num!r}); no es seguro el PUT"
        )
    out = dict(actual)
    out.update(cambios)
    out["Numero_Expediente"] = num  # siempre el del GET, pase lo que pase en cambios
    return out


def get_expediente(exp_id: str) -> dict:
    """GET del registro extrajudicial completo por id (x-api-key)."""
    url = f"{_REST_BASE}{_REST_CREATE_EXTRAJUDICIAL}/{exp_id}"
    try:
        r = httpx.get(url, headers=_rest_headers(), timeout=_REST_TIMEOUT)
    except httpx.HTTPError as exc:
        raise SudespachoCreateError(f"REST GET extrajudiciales/{exp_id} falló: {exc}") from exc
    if r.status_code == 200:
        try:
            return r.json()
        except Exception as exc:
            raise SudespachoCreateError(
                f"REST GET extrajudiciales/{exp_id}: 200 sin JSON válido"
            ) from exc
    try:
        detail = r.json().get("detail") or r.text[:300]
    except Exception:
        detail = r.text[:300]
    raise SudespachoCreateError(f"REST GET extrajudiciales/{exp_id} → HTTP {r.status_code}: {detail}")


def update_expediente(exp_id: str, cambios: dict) -> dict:
    """GET → merge (preservando Numero_Expediente) → PUT de reemplazo total.

    Único punto de reescritura de un expediente extrajudicial. Devuelve el
    registro actualizado que responde el servidor.
    """
    actual = get_expediente(exp_id)
    body = merge_expediente_update(actual, cambios)
    url = f"{_REST_BASE}{_REST_CREATE_EXTRAJUDICIAL}/{exp_id}"
    try:
        r = httpx.put(url, json=body, headers=_rest_headers(), timeout=_REST_TIMEOUT)
    except httpx.HTTPError as exc:
        raise SudespachoCreateError(f"REST PUT extrajudiciales/{exp_id} falló: {exc}") from exc
    if r.status_code == 200:
        try:
            return r.json()
        except Exception:
            return body
    try:
        detail = r.json().get("detail") or r.text[:300]
    except Exception:
        detail = r.text[:300]
    raise SudespachoCreateError(f"REST PUT extrajudiciales/{exp_id} → HTTP {r.status_code}: {detail}")
```

- [ ] **Step 4: Ejecutar para verificar que pasan**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest tests/test_sudespacho_create.py -k "merge_expediente_update or get_expediente or update_expediente" -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add core/sudespacho_create.py tests/test_sudespacho_create.py
git commit -m "feat(crm): get_expediente + update_expediente (GET->merge->PUT preserva Numero_Expediente) (B1)"
```

---

### Task 4: `FichaCRMInput` + carga del `_ficha_crm.yaml`

**Files:**
- Create: `core/crm_ficha.py`
- Test: `tests/test_crm_ficha.py`

**Interfaces:**
- Consumes: `core.sudespacho_relations.NuevoClienteContrario`, `NuevoColaborador` (los DTOs normalizan el teléfono por B3).
- Produces:
  - `@dataclass FichaCRMInput` con: `contrario: NuevoClienteContrario | None`, `colaboradores: list[NuevoColaborador]`, `notas_html: str`, `cliente_propio: str` (default `"EV_MMC_SPAIN"`).
  - `cargar_ficha_yaml(path: Path) -> FichaCRMInput`: parsea el YAML → DTOs. Lanza `FileNotFoundError` si no existe, `ValueError` si el YAML es inválido o un contrario sin `nombre`.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `tests/test_crm_ficha.py`:

```python
from pathlib import Path

import pytest

from core.crm_ficha import FichaCRMInput, cargar_ficha_yaml
from core.sudespacho_relations import NuevoClienteContrario, NuevoColaborador


def _escribir(path: Path, texto: str) -> Path:
    path.write_text(texto, encoding="utf-8")
    return path


def test_cargar_ficha_yaml_completo(tmp_path):
    y = _escribir(tmp_path / "_ficha_crm.yaml", """
cliente_propio: EV_MMC_SPAIN
contrario:
  nombre: JUAN
  apellido1: PEREZ
  apellido2: GOMEZ
  nif: 00000000T
  email: juan@example.invalid
  movil: "+34 600 111 222"
  direccion: Calle Falsa 1
  poblacion: Barcelona
colaboradores:
  - nombre: ANA CONSULTORA
    email: ana@engelvoelkers.example
    movil: "600 333 444"
    telefono: "934 000 111"
notas_html: "<p>Reclamación de honorarios (Vuelta).</p>"
""")
    ficha = cargar_ficha_yaml(y)
    assert isinstance(ficha, FichaCRMInput)
    assert ficha.cliente_propio == "EV_MMC_SPAIN"
    assert isinstance(ficha.contrario, NuevoClienteContrario)
    assert ficha.contrario.apellido1 == "PEREZ"
    assert ficha.contrario.movil == "600111222"          # normalizado por el DTO (B3)
    assert len(ficha.colaboradores) == 1
    assert isinstance(ficha.colaboradores[0], NuevoColaborador)
    assert ficha.colaboradores[0].telefono == "934000111"  # normalizado
    assert "honorarios" in ficha.notas_html


def test_cargar_ficha_yaml_contrario_opcional(tmp_path):
    y = _escribir(tmp_path / "_ficha_crm.yaml",
                  "colaboradores: []\nnotas_html: hola\n")
    ficha = cargar_ficha_yaml(y)
    assert ficha.contrario is None
    assert ficha.colaboradores == []
    assert ficha.cliente_propio == "EV_MMC_SPAIN"   # default


def test_cargar_ficha_yaml_no_existe_lanza(tmp_path):
    with pytest.raises(FileNotFoundError):
        cargar_ficha_yaml(tmp_path / "no.yaml")


def test_cargar_ficha_yaml_contrario_sin_nombre_lanza(tmp_path):
    y = _escribir(tmp_path / "_ficha_crm.yaml", "contrario:\n  nif: X\n")
    with pytest.raises(ValueError):
        cargar_ficha_yaml(y)
```

- [ ] **Step 2: Ejecutar para verificar que fallan**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest tests/test_crm_ficha.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'core.crm_ficha'`.

- [ ] **Step 3: Implementar el módulo**

Crear `core/crm_ficha.py`:

```python
"""Cerebro de la ficha CRM completa (B1): modelo de entrada + carga del YAML.

Determinista, sin red: parsea ``00_Input/_ficha_crm.yaml`` a un ``FichaCRMInput``
con los DTOs de ``sudespacho_relations`` (que normalizan el teléfono, B3). El
orquestador (``scripts/crm_ficha.py``) ejecuta los efectos contra el CRM.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from core.sudespacho_relations import NuevoClienteContrario, NuevoColaborador

CLIENTE_PROPIO_DEFAULT = "EV_MMC_SPAIN"


@dataclass
class FichaCRMInput:
    contrario: NuevoClienteContrario | None = None
    colaboradores: list[NuevoColaborador] = field(default_factory=list)
    notas_html: str = ""
    cliente_propio: str = CLIENTE_PROPIO_DEFAULT


def _contrario_de(d: dict) -> NuevoClienteContrario:
    if not d.get("nombre"):
        raise ValueError("contrario sin 'nombre' en _ficha_crm.yaml")
    return NuevoClienteContrario(
        nombre=d.get("nombre", ""),
        apellido1=d.get("apellido1", ""),
        apellido2=d.get("apellido2", ""),
        email=d.get("email", ""),
        movil=str(d.get("movil", "")),
        nif=d.get("nif", ""),
        direccion=d.get("direccion", ""),
        poblacion=d.get("poblacion", ""),
    )


def _colaborador_de(d: dict) -> NuevoColaborador:
    if not d.get("nombre"):
        raise ValueError("colaborador sin 'nombre' en _ficha_crm.yaml")
    return NuevoColaborador(
        nombre=d.get("nombre", ""),
        email=d.get("email", ""),
        movil=str(d.get("movil", "")),
        telefono=str(d.get("telefono", "")),
        nif=d.get("nif", ""),
    )


def cargar_ficha_yaml(path: Path) -> FichaCRMInput:
    """Carga ``_ficha_crm.yaml`` → ``FichaCRMInput``.

    Lanza ``FileNotFoundError`` si no existe y ``ValueError`` si el YAML no es un
    mapping o un contrario/colaborador no tiene ``nombre``.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"No existe _ficha_crm.yaml: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"_ficha_crm.yaml inválido: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("_ficha_crm.yaml debe ser un mapping YAML")

    contrario_raw = data.get("contrario")
    contrario = _contrario_de(contrario_raw) if isinstance(contrario_raw, dict) else None
    colaboradores = [
        _colaborador_de(c) for c in (data.get("colaboradores") or []) if isinstance(c, dict)
    ]
    return FichaCRMInput(
        contrario=contrario,
        colaboradores=colaboradores,
        notas_html=str(data.get("notas_html", "")),
        cliente_propio=str(data.get("cliente_propio") or CLIENTE_PROPIO_DEFAULT),
    )
```

- [ ] **Step 4: Ejecutar para verificar que pasan**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest tests/test_crm_ficha.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add core/crm_ficha.py tests/test_crm_ficha.py
git commit -m "feat(crm-ficha): FichaCRMInput + carga del _ficha_crm.yaml (B1)"
```

---

### Task 5: Orquestador `scripts/crm_ficha.py`

**Files:**
- Create: `scripts/crm_ficha.py`
- Test: `tests/test_crm_ficha_cli.py`

**Interfaces:**
- Consumes: `case_locator.resolve_ref`/`path_for`, `case_manager.get_case_status`, `crm_ficha.cargar_ficha_yaml`, `sudespacho_relations.link_ev_mmc`/`ensure_contrario_vinculado`/`ensure_colaborador_vinculado`, `sudespacho_create.update_expediente`/`get_expediente`.
- Produces: CLI `python -m scripts.crm_ficha --case-id <ref> [--dry-run] [--yes]` que rellena la ficha CRM completa del expediente extrajudicial del caso.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `tests/test_crm_ficha_cli.py`:

```python
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from core import case_manager
from core.casos import case_locator
from scripts import crm_ficha as cli


@pytest.fixture
def caso_con_ficha(tmp_path, monkeypatch):
    """CASOS_ROOT en tmp, un caso con expediente extrajudicial registrado y un _ficha_crm.yaml."""
    root = tmp_path / "CASOS"
    root.mkdir()
    monkeypatch.setattr(case_locator, "_root", lambda: root)

    case_id = "BaRS11 - Falsa 1 (W-000AAA) - Vuelta"
    case_manager.ensure_case(
        case_id, titulo=case_id, referencia_crm=case_id,
        tipo_caso="VUELTA", ciudad="Barcelona", direccion="Falsa 1", id_go="W-000AAA",
    )
    case_manager.register_expediente(case_id, "606", "extrajudiciales")

    ficha = case_locator.path_for(case_id) / "00_Input" / "_ficha_crm.yaml"
    ficha.write_text(
        "contrario:\n  nombre: JUAN\n  apellido1: PEREZ\n  nif: 00000000T\n"
        "  movil: '+34 600 111 222'\n"
        "colaboradores:\n  - nombre: ANA\n    email: ana@engelvoelkers.example\n"
        "notas_html: '<p>Vuelta</p>'\n",
        encoding="utf-8",
    )
    return case_id


def test_crm_ficha_orquesta_todo(caso_con_ficha, monkeypatch):
    link_ev = MagicMock()
    ensure_c = MagicMock(return_value=("1099", True))
    ensure_col = MagicMock(return_value=("776", False))
    upd = MagicMock(return_value={"Numero_Expediente": "49", "Notas": "<p>Vuelta</p>"})
    monkeypatch.setattr("scripts.crm_ficha.link_ev_mmc", link_ev)
    monkeypatch.setattr("scripts.crm_ficha.ensure_contrario_vinculado", ensure_c)
    monkeypatch.setattr("scripts.crm_ficha.ensure_colaborador_vinculado", ensure_col)
    monkeypatch.setattr("scripts.crm_ficha.update_expediente", upd)
    # GET de verificación: devuelve algo plausible
    monkeypatch.setattr("scripts.crm_ficha.get_expediente",
                        MagicMock(return_value={"Numero_Expediente": "49"}))

    r = CliRunner().invoke(cli.app, ["--case-id", "W-000AAA", "--yes"])
    assert r.exit_code == 0, r.output

    link_ev.assert_called_once_with("606")
    assert ensure_c.call_args.args[0] == "606"          # exp_id
    assert ensure_c.call_args.args[1].apellido1 == "PEREZ"
    assert ensure_col.call_args.args[0] == "606"
    assert upd.call_args.args[0] == "606"
    assert upd.call_args.args[1] == {"Notas": "<p>Vuelta</p>"}


def test_crm_ficha_dry_run_no_escribe(caso_con_ficha, monkeypatch):
    link_ev = MagicMock()
    monkeypatch.setattr("scripts.crm_ficha.link_ev_mmc", link_ev)
    monkeypatch.setattr("scripts.crm_ficha.update_expediente", MagicMock())
    r = CliRunner().invoke(cli.app, ["--case-id", "W-000AAA", "--dry-run"])
    assert r.exit_code == 0, r.output
    link_ev.assert_not_called()


def test_crm_ficha_sin_yaml_falla(caso_con_ficha, monkeypatch):
    # Borrar el yaml
    (case_locator.path_for(caso_con_ficha) / "00_Input" / "_ficha_crm.yaml").unlink()
    r = CliRunner().invoke(cli.app, ["--case-id", "W-000AAA", "--yes"])
    assert r.exit_code != 0
    assert "_ficha_crm.yaml" in r.output


def test_crm_ficha_sin_expediente_falla(tmp_path, monkeypatch):
    root = tmp_path / "CASOS"; root.mkdir()
    monkeypatch.setattr(case_locator, "_root", lambda: root)
    case_id = "BaRS11 - Falsa 2 (W-000BBB) - Vuelta"
    case_manager.ensure_case(case_id, titulo=case_id, referencia_crm=case_id,
                             tipo_caso="VUELTA", ciudad="Barcelona", direccion="Falsa 2", id_go="W-000BBB")
    (case_locator.path_for(case_id) / "00_Input" / "_ficha_crm.yaml").write_text(
        "notas_html: x\n", encoding="utf-8")
    r = CliRunner().invoke(cli.app, ["--case-id", "W-000BBB", "--yes"])
    assert r.exit_code != 0
    assert "expediente" in r.output.lower()
```

- [ ] **Step 2: Ejecutar para verificar que fallan**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest tests/test_crm_ficha_cli.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'scripts.crm_ficha'`.

- [ ] **Step 3: Implementar el orquestador**

Crear `scripts/crm_ficha.py`:

```python
"""CLI local: rellenar la ficha CRM completa de un expediente extrajudicial (B1).

Orquestador fino sobre core: resuelve el caso por --case-id, carga el
``_ficha_crm.yaml`` y ejecuta (idempotente) cliente propio EV + contrario +
colaboradores + Notas, con GET de verificación tras cada escritura.

Uso:
  python -m scripts.crm_ficha --case-id W-XXXXXX [--dry-run] [--yes]

Requiere SUDESPACHO_API_KEY (.env). El _ficha_crm.yaml (PII) vive en
data/CASOS/<caso>/00_Input/ y nunca se commitea.
"""
from __future__ import annotations

import typer

from core import case_manager
from core.casos import case_locator
from core.crm_ficha import cargar_ficha_yaml
from core.sudespacho_create import get_expediente, update_expediente
from core.sudespacho_relations import (
    ensure_colaborador_vinculado, ensure_contrario_vinculado, link_ev_mmc,
)

app = typer.Typer(add_completion=False, help="Rellenar la ficha CRM completa de un expediente")

_ELEMENT_EXTRAJUDICIAL = "extrajudiciales"
_FICHA_YAML = "_ficha_crm.yaml"


def _exp_id_de(case_id: str) -> str | None:
    for e in case_manager.get_case_status(case_id)["expedientes"]:
        if isinstance(e, dict) and e.get("element") == _ELEMENT_EXTRAJUDICIAL:
            return str(e.get("id"))
    return None


@app.command()
def main(
    case_id: str = typer.Option(..., "--case-id", help="case_id canónico o W-code"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    yes: bool = typer.Option(False, "--yes", help="auto-confirma la escritura al CRM"),
) -> None:
    resolved = case_locator.resolve_ref(case_id)
    case_dir = case_locator.path_for(resolved)
    if not (case_dir / "00_Input" / "_caso.md").is_file():
        typer.echo(f"[ERROR] Caso no encontrado: {case_id!r} (resuelto: {resolved!r})", err=True)
        raise typer.Exit(code=1)

    exp_id = _exp_id_de(resolved)
    if not exp_id:
        typer.echo(f"[ERROR] El caso {resolved!r} no tiene expediente extrajudicial "
                   "registrado; da de alta primero con abrir_caso --crm api", err=True)
        raise typer.Exit(code=1)

    ficha_path = case_dir / "00_Input" / _FICHA_YAML
    try:
        ficha = cargar_ficha_yaml(ficha_path)
    except FileNotFoundError:
        typer.echo(f"[ERROR] Falta {_FICHA_YAML} en {case_dir / '00_Input'}", err=True)
        raise typer.Exit(code=1)
    except ValueError as exc:
        typer.echo(f"[ERROR] {_FICHA_YAML} inválido: {exc}", err=True)
        raise typer.Exit(code=1)

    plan = [f"cliente propio EV → exp {exp_id}"]
    if ficha.contrario:
        plan.append(f"contrario: {ficha.contrario.apellido1} (dedup NIF)")
    plan += [f"colaborador: {c.email or c.nombre} (dedup email)" for c in ficha.colaboradores]
    if ficha.notas_html:
        plan.append("Notas (update_expediente)")
    typer.echo("Plan ficha CRM:\n  - " + "\n  - ".join(plan))

    if dry_run:
        typer.echo("[dry-run] no se escribe nada.")
        raise typer.Exit(code=0)
    if not (yes or typer.confirm("¿Escribir la ficha en el CRM?")):
        typer.echo("Cancelado.")
        raise typer.Exit(code=0)

    link_ev_mmc(exp_id)
    typer.echo(f"OK cliente propio EV vinculado (exp {exp_id})")

    if ficha.contrario:
        cid, creado = ensure_contrario_vinculado(exp_id, ficha.contrario)
        typer.echo(f"OK contrario id={cid} ({'creado' if creado else 'existente'}) vinculado")
    for col in ficha.colaboradores:
        colid, creado = ensure_colaborador_vinculado(exp_id, col)
        typer.echo(f"OK colaborador id={colid} ({'creado' if creado else 'existente'}) vinculado")
    if ficha.notas_html:
        update_expediente(exp_id, {"Notas": ficha.notas_html})
        typer.echo("OK Notas actualizadas")

    # GET de verificación (el 201/200 no prueba el vínculo; confirmar por lectura).
    try:
        rec = get_expediente(exp_id)
        typer.echo(f"Verificación: expediente {exp_id} Numero_Expediente="
                   f"{rec.get('Numero_Expediente')} (verificar partes visualmente en el CRM)")
    except Exception as exc:  # noqa: BLE001 — la verificación no debe tumbar el éxito
        typer.echo(f"[AVISO] GET de verificación falló ({exc!r}); revisa manualmente el CRM")

    typer.echo(f"OK ficha CRM completada: {resolved}")


if __name__ == "__main__":
    app()
```

- [ ] **Step 4: Ejecutar para verificar que pasan**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest tests/test_crm_ficha_cli.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/crm_ficha.py tests/test_crm_ficha_cli.py
git commit -m "feat(crm-ficha): orquestador scripts/crm_ficha.py (ficha CRM end-to-end, B1)"
```

---

### Task 6: Docs + verificación + PR

**Files:** `docs/RUNBOOK_APERTURA_EXPEDIENTE.md`, `docs/INTEGRACION_SUDESPACHO.md` (+ git).

- [ ] **Step 1: Actualizar la doc (spec §10)**

- `docs/INTEGRACION_SUDESPACHO.md §11.3`: quitar el aviso de que Barcelona/Bilbao/Sevilla/Santander/San Sebastián "no tienen tag azul de ciudad" — ya existen en código (`TAG_AZUL_BARCELONA=296`, etc.).
- `docs/INTEGRACION_SUDESPACHO.md §10.7`: anotar que `update_expediente` (GET→merge→PUT, preserva `Numero_Expediente`) **ya existe** en `core/sudespacho_create.py`.
- `docs/RUNBOOK_APERTURA_EXPEDIENTE.md §9`: los tags equipo+ciudad los pone el **alta** (`crm_payload`), no un PUT; los pasos 2-5 de la ficha (cliente propio, contrario, colaboradores, Notas) los orquesta `python -m scripts.crm_ficha --case-id <ref>` desde el `_ficha_crm.yaml`.

Commit:
```bash
git add docs/RUNBOOK_APERTURA_EXPEDIENTE.md docs/INTEGRACION_SUDESPACHO.md
git commit -m "docs(apertura): ficha CRM por crm_ficha + tags en el alta + update_expediente (B1)"
```

- [ ] **Step 2: Suite completa a JUnit XML**

Run: `C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest -q -p no:randomly --junit-xml=.pr3_report.xml`
Expected: 0 fallos nuevos; solo los 5 ambientales `test_list_colaboradores_rest_*`. Verificar en el XML que los nuevos tests (Tasks 1-5) están en `passed`.

- [ ] **Step 3: Limpiar el artefacto**

```bash
rm -f .pr3_report.xml
```

- [ ] **Step 4: Push + PR (con la verificación en vivo marcada como gate pre-merge)**

```bash
git push -u origin claude/apertura-pr3-ficha-crm
```

Abrir PR con `gh` hacia `main` (título: `PR-3 apertura: ficha CRM end-to-end (B1)`; cuerpo enlazando spec §7 y este plan). **El cuerpo DEBE marcar como pendiente la VERIFICACIÓN EN VIVO del CRM** (no se puede correr en el worktree, sin `SUDESPACHO_*`): contra un expediente **desechable**, confirmar por GET/visualmente que `update_expediente` preserva `Numero_Expediente`, que `get_expediente` funciona (y si necesita el workaround coma-500 `?properties=`), y el riesgo **R1** (los `ensure_*` re-vinculan siempre → ¿el re-POST de relación duplica? sin ruta REST fiable de lectura de relaciones, `DEAD_ENDS.md`). Confirmar `leak-scan` verde.

- [ ] **Step 5: Revisión adversarial + verificación en vivo antes de mergear**

Revisión de rama completa (workflow) + la verificación en vivo del §4 (la corre Nikolai o se inyecta `SUDESPACHO_*` y se corre desde el repo principal). No mergear sin la verificación en vivo (regla del proyecto: el 201 no prueba el vínculo).

---

## Self-Review (hecho al escribir el plan)

- **Cobertura de spec §7:** tags equipo+ciudad en el alta (Tasks 1-2) ✓; `update_expediente` seguro con merge puro (Task 3) ✓; `FichaCRMInput`+YAML en `00_Input/` (Task 4) ✓; orquestador con `link_ev_mmc`+`ensure_*`+Notas+GET de verificación (Task 5) ✓; docs + gate de verificación en vivo (Task 6) ✓.
- **Deviación consciente:** tag azul por prefijo del `codigo` (no `ciudad` en `Identidad`) — documentada arriba; evita tocar `scripts/abrir_caso.py` y por tanto **cero conflicto con PR-2**.
- **Placeholders:** ninguno; todo el código y comandos son literales.
- **Consistencia de tipos/firmas:** `tag_rojo_equipo`/`tag_azul_de_codigo` (Task 1) usados en `crm_payload` (Task 2); `merge_expediente_update`/`get_expediente`/`update_expediente` (Task 3) usados por el orquestador (Task 5); `FichaCRMInput`/`cargar_ficha_yaml` (Task 4) usados por el orquestador (Task 5). Firmas de `ensure_*`/`link_ev_mmc` verificadas contra `core/sudespacho_relations.py`.
- **No conflicto con PR-2:** PR-3 toca `core/sudespacho_create.py`, `core/abrir_caso.py` (solo `crm_payload`), `core/crm_ficha.py` (nuevo), `scripts/crm_ficha.py` (nuevo) + docs; PR-2 tocó `descomponer_case_id` de `core/abrir_caso.py` (función distinta), `case_locator.py`, `scripts/abrir_caso.py`. Sin solape de líneas.
- **Riesgo asumido:** la verificación en vivo del CRM (R1/R2/R3 de la spec §9) NO se puede correr en el worktree (sin credenciales) → es gate pre-merge explícito en Task 6.
