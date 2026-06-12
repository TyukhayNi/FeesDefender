# Migración `search_expedientes` a REST (combobox F2 §18.6) — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que el combobox de reasignación de la bandeja de procuradores busque expedientes contra el CRM real (REST OR-like sobre referencia_cliente + referencia_procurador, más número interno del despacho `nº/AÑO`), en lugar del autocomplete legacy que devuelve body vacío.

**Architecture:** Dos helpers REST nuevos en `core/sudespacho_relations.py` (texto libre OR-like; num+serie con `equal`), apoyados en un `_rest_get_items` común que también podrá reusar el dedup. `core.procurador_search.search_expedientes` se reescribe como orquestador fino: siempre busca por texto y, si el término casa `nº/AÑO`, fusiona la búsqueda por num+serie. Todo REST x-api-key (sin PHPSESSID). No se toca la lógica de dedup `_rest_search_expedientes`.

**Tech Stack:** Python 3, httpx, pytest (mock de `httpx.get`), Windows/PowerShell, venv en `.venv`.

**Spec:** `docs/superpowers/specs/2026-06-12-search-expedientes-rest-design.md`

---

## Estructura de ficheros

- **Modify:** `core/sudespacho_relations.py`
  - Nuevos: `_rest_get_items()`, `_values_dict()`, `_label_expediente()`, `_norm_serie_local()`, `_SEARCH_PROPS_BY_ELEMENT`, `_rest_search_por_texto()`, `_rest_search_num_serie()`.
- **Modify:** `core/procurador_search.py`
  - Reescribir `search_expedientes()`; actualizar imports y `ELEMENTOS_BUSCABLES`; quitar dependencia de `_autocomplete`/`SudespachoLegacyClient`.
- **Modify (tests):** `tests/test_procurador_search.py` (reescribir los 3 tests de `search_expedientes`), `tests/test_sudespacho_relations.py` (tests de los helpers nuevos).
- **Modify (docs):** `docs/DEAD_ENDS.md`, `docs/MEJORAS_FUTURAS.md`.

Las firmas exactas:

```python
_SEARCH_PROPS_BY_ELEMENT: dict[str, tuple[str, ...]] = {
    "expedientes_judiciales": ("referencia_cliente", "referencia_procurador"),
    "extrajudiciales":        ("Referencia_Cliente",),
}

def _rest_get_items(url: str, params: list[tuple[str, str]]) -> list[dict[str, Any]]: ...
def _values_dict(item: dict) -> dict[str, Any]: ...
def _label_expediente(vals: dict[str, Any]) -> str: ...
def _norm_serie_local(s: Any) -> str: ...
def _rest_search_por_texto(element: str, term: str, *, limit: int = 50) -> list[dict[str, str]]: ...
def _rest_search_num_serie(num: str, serie: str, *, limit: int = 50) -> list[dict[str, str]]: ...

# core/procurador_search.py
def search_expedientes(term, *, element="expedientes_judiciales", client=None) -> list[dict[str, str]]: ...
```

---

## Task 1: Helpers comunes + búsqueda por texto OR-like

**Files:**
- Modify: `core/sudespacho_relations.py` (añadir tras `_rest_search_expedientes`, antes de `_find_expediente_rest`)
- Test: `tests/test_sudespacho_relations.py`

- [ ] **Step 1: Escribir los tests que fallan**

Añadir al final de `tests/test_sudespacho_relations.py` (reutilizan `_api_key`, `_mock_get_response` y el patrón `_capturing_get` ya presentes en el fichero; importar los símbolos nuevos en el bloque `from core.sudespacho_relations import (...)`):

```python
# --- _rest_search_por_texto (combobox F2 §18.6) --------------------------

def _items_multi(*rows: tuple[str, dict]) -> dict:
    """Respuesta REST con (id, {prop: value, ...}) por fila."""
    items = []
    for eid, props in rows:
        vals = [{"property": {"name": k}, "value": v} for k, v in props.items()]
        items.append({"id": str(eid), "values": vals})
    return {"totalItems": len(items), "items": items}


def test_rest_texto_judicial_or_like_dos_properties(_api_key):
    captured: dict = {}

    def _capturing_get(url, *, params, headers, timeout):
        captured["url"] = url
        captured["params"] = params
        return _mock_get_response(_items_multi(
            ("487", {"referencia_cliente": "BaRS3 - Torrent 41 - (W-02MA0R)",
                     "referencia_procurador": "P-2025/3447"}),
        ))

    with patch("core.sudespacho_relations.httpx.get", side_effect=_capturing_get):
        out = _rest_search_por_texto("expedientes_judiciales", "3447")

    assert out == [{"id": "487",
                    "label": "BaRS3 - Torrent 41 - (W-02MA0R)  ·  P-2025/3447"}]
    assert "element_registries/expedientes_judiciales" in captured["url"]
    p = captured["params"]
    assert ("filterGroup[filterGroups][0][condition]", "OR") in p
    assert ("filterGroup[filterGroups][0][filters][0][operator]", "like") in p
    assert ("filterGroup[filterGroups][0][filters][0][value]", "3447") in p
    assert ("filterGroup[filterGroups][0][filters][0][property]", "referencia_cliente") in p
    assert ("filterGroup[filterGroups][0][filters][1][property]", "referencia_procurador") in p
    assert ("filterGroup[filterGroups][0][filters][1][value]", "3447") in p


def test_rest_texto_extrajudicial_solo_referencia_camelcase(_api_key):
    captured: dict = {}

    def _capturing_get(url, *, params, headers, timeout):
        captured["url"] = url
        captured["params"] = params
        return _mock_get_response(_items_multi(
            ("500", {"Referencia_Cliente": "MaRS2 - Gran Via 40 - (W-0001)"}),
        ))

    with patch("core.sudespacho_relations.httpx.get", side_effect=_capturing_get):
        out = _rest_search_por_texto("extrajudiciales", "Gran Via")

    assert out == [{"id": "500", "label": "MaRS2 - Gran Via 40 - (W-0001)"}]
    assert "element_registries/extrajudiciales" in captured["url"]
    p = captured["params"]
    assert ("filterGroup[filterGroups][0][filters][0][property]", "Referencia_Cliente") in p
    # extrajudicial NO busca por referencia_procurador
    assert all(v != "referencia_procurador" for (_k, v) in p)


def test_rest_texto_normaliza_alias_extrajudicial(_api_key):
    captured: dict = {}

    def _capturing_get(url, *, params, headers, timeout):
        captured["url"] = url
        captured["params"] = params
        return _mock_get_response(_items_multi())

    with patch("core.sudespacho_relations.httpx.get", side_effect=_capturing_get):
        _rest_search_por_texto("expedientes_extrajudiciales", "algo")

    assert "element_registries/extrajudiciales" in captured["url"]


def test_rest_texto_label_cae_a_procurador_si_no_hay_referencia(_api_key):
    with patch("core.sudespacho_relations.httpx.get",
               return_value=_mock_get_response(_items_multi(
                   ("9", {"referencia_procurador": "SP-3599"}),
               ))):
        out = _rest_search_por_texto("expedientes_judiciales", "SP-3599")
    assert out == [{"id": "9", "label": "SP-3599"}]


def test_rest_texto_sin_api_key_devuelve_vacio(monkeypatch):
    monkeypatch.setenv("SUDESPACHO_API_KEY", "")
    assert _rest_search_por_texto("expedientes_judiciales", "x") == []


def test_rest_texto_elemento_desconocido_devuelve_vacio(_api_key):
    assert _rest_search_por_texto("clientes", "x") == []


def test_rest_texto_termino_vacio_devuelve_vacio(_api_key):
    assert _rest_search_por_texto("expedientes_judiciales", "   ") == []


def test_rest_texto_http_500_devuelve_vacio(_api_key):
    with patch("core.sudespacho_relations.httpx.get",
               return_value=_mock_get_response({}, status=500)):
        assert _rest_search_por_texto("expedientes_judiciales", "x") == []
```

Añadir a los imports del fichero (bloque `from core.sudespacho_relations import (...)`):

```python
    _rest_search_por_texto,
```

(El import de `_rest_search_num_serie` se añade en Task 2, cuando esa función ya exista — añadirlo aquí rompería la recolección de pytest por ImportError.)

- [ ] **Step 2: Ejecutar y verificar que fallan**

Run: `python -m pytest tests/test_sudespacho_relations.py -k rest_texto -q`
Expected: FAIL — `ImportError: cannot import name '_rest_search_por_texto'`.

- [ ] **Step 3: Implementar los helpers**

En `core/sudespacho_relations.py`, justo **después** de la función `_rest_search_expedientes` (línea ~368) y antes de `_find_expediente_rest`:

```python
# ---------------------------------------------------------------------------
# Búsqueda para el combobox F2 §18.6 (texto libre + nº/serie del despacho)
# ---------------------------------------------------------------------------
#
# A diferencia de _rest_search_expedientes (dedup: extrae W-code, match exacto),
# el combobox busca por TEXTO LITERAL en varias properties con OR-like, y por el
# número interno del despacho (num_expediente/serie). Confirmado contra tenant
# tnm el 2026-06-12: like sobre referencia_cliente y referencia_procurador
# funciona; num_asunto (autos) está vacío y contrario no tiene ruta REST inversa
# (ver docs/DEAD_ENDS.md).

# Properties sobre las que el combobox hace OR-like (texto del usuario). Judicial
# añade referencia_procurador (lo que el procurador cita en su correo, p. ej.
# "P-2025/3447"); extrajudicial no tiene procurador.
_SEARCH_PROPS_BY_ELEMENT: dict[str, tuple[str, ...]] = {
    "expedientes_judiciales": ("referencia_cliente", "referencia_procurador"),
    "extrajudiciales":        ("Referencia_Cliente",),
}


def _rest_get_items(url: str, params: list[tuple[str, str]]) -> list[dict[str, Any]]:
    """GET REST element_registries → lista de items.

    Nunca lanza: devuelve ``[]`` ante api-key ausente, red caída, status != 200
    o JSON inválido. Centraliza el bloque HTTP+parseo de las búsquedas REST.
    """
    api_key = (os.getenv("SUDESPACHO_API_KEY") or "").strip()
    if not api_key:
        return []
    headers = {"x-api-key": api_key, "Accept": "application/json"}
    try:
        r = httpx.get(url, params=params, headers=headers, timeout=_REST_TIMEOUT)
    except Exception:  # noqa: BLE001 — red caída no debe romper el caller
        return []
    if r.status_code != 200:
        return []
    try:
        data = r.json()
    except Exception:  # noqa: BLE001
        return []
    return data.get("items") or data.get("hydra:member") or []


def _values_dict(item: dict) -> dict[str, Any]:
    """Aplana ``item["values"]`` a ``{property_name: value}``."""
    return {
        (v.get("property") or {}).get("name", ""): v.get("value")
        for v in item.get("values", []) or []
    }


def _label_expediente(vals: dict[str, Any]) -> str:
    """Etiqueta para la UI: nombre del caso, con la ref del procurador si la hay."""
    ref = str(vals.get("referencia_cliente") or vals.get("Referencia_Cliente") or "")
    proc = str(vals.get("referencia_procurador") or "")
    if ref and proc:
        return f"{ref}  ·  {proc}"
    return ref or proc


def _rest_search_por_texto(element: str, term: str, *, limit: int = 50) -> list[dict[str, str]]:
    """Busca expedientes por TEXTO LIBRE (literal) vía REST OR-like.

    Filtra ``like`` sobre el término literal en TODAS las properties buscables
    del elemento (``_SEARCH_PROPS_BY_ELEMENT``), combinadas con OR. Para el
    combobox de reasignación F2 §18.6.

    Returns:
        Lista ``[{"id","label"}]``. Nunca lanza: ``[]`` ante elemento
        desconocido / api-key ausente / término vacío / CRM no accesible.
    """
    elem = _normalize_element(element)
    props = _SEARCH_PROPS_BY_ELEMENT.get(elem) if elem else None
    if not props:
        return []
    term = (term or "").strip()
    if not term:
        return []

    url = f"{_REST_BASE}/api/element_registries/{elem}"
    params: list[tuple[str, str]] = [
        (f"properties[{i}]", p) for i, p in enumerate(props)
    ]
    params += [
        ("filterGroup[condition]", "AND"),
        ("filterGroup[filterGroups][0][condition]", "OR"),
    ]
    for i, p in enumerate(props):
        params += [
            (f"filterGroup[filterGroups][0][filters][{i}][operator]", "like"),
            (f"filterGroup[filterGroups][0][filters][{i}][value]", term),
            (f"filterGroup[filterGroups][0][filters][{i}][property]", p),
        ]
    params += [("itemsPerPage", str(limit)), ("return_totals", "true")]

    return [
        {"id": str(it.get("id", "")), "label": _label_expediente(_values_dict(it))}
        for it in _rest_get_items(url, params)
    ]
```

Verificar que `Any` ya está importado (sí: `from typing import Any`, línea 78) y `os`, `re`, `httpx`, `_REST_BASE`, `_REST_TIMEOUT`, `_normalize_element`, `_REFERENCIA_PROP_BY_ELEMENT` existen en el módulo.

> NOTA: `_normalize_element` está definido más abajo en el fichero (línea ~1530). En Python las funciones se resuelven en tiempo de llamada, así que la referencia hacia adelante es válida (no es import). No mover nada.

- [ ] **Step 4: Ejecutar y verificar que pasan**

Run: `python -m pytest tests/test_sudespacho_relations.py -k rest_texto -q`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```powershell
cd "C:\Users\tnm33\Dev\FeesDefender"
git add core/sudespacho_relations.py tests/test_sudespacho_relations.py
git commit -m "feat(intake-procuradores): _rest_search_por_texto (OR-like combobox F2)"
```

---

## Task 2: Búsqueda por nº interno del despacho (num + serie)

**Files:**
- Modify: `core/sudespacho_relations.py` (tras `_rest_search_por_texto`)
- Test: `tests/test_sudespacho_relations.py`

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `tests/test_sudespacho_relations.py`:

```python
# --- _rest_search_num_serie (nº interno del despacho "63/2024") ----------

def test_rest_num_serie_equal_y_casa_serie(_api_key):
    captured: dict = {}

    def _capturing_get(url, *, params, headers, timeout):
        captured["params"] = params
        # El CRM devuelve los 4 expedientes con num=63 (uno por serie).
        return _mock_get_response(_items_multi(
            ("605", {"num_expediente": "63", "serie_expediente": "2025",
                     "referencia_cliente": "SaRS1 - Pérez Galdós (W-02ET8N)"}),
            ("487", {"num_expediente": "63", "serie_expediente": "2024",
                     "referencia_cliente": "BaRS3 - Torrent 41 (W-02MA0R)",
                     "referencia_procurador": "P-2025/3447"}),
            ("406", {"num_expediente": "63", "serie_expediente": "2023-n",
                     "referencia_cliente": "MaRS1 - Velazquez 54 (W-02PLYH)"}),
        ))

    with patch("core.sudespacho_relations.httpx.get", side_effect=_capturing_get):
        out = _rest_search_num_serie("63", "2024")

    # Filtro equal sobre num_expediente en servidor
    p = captured["params"]
    assert ("filterGroup[filterGroups][0][filters][0][operator]", "equal") in p
    assert ("filterGroup[filterGroups][0][filters][0][value]", "63") in p
    assert ("filterGroup[filterGroups][0][filters][0][property]", "num_expediente") in p
    # Serie casada en cliente → solo el 487
    assert out == [{"id": "487",
                    "label": "BaRS3 - Torrent 41 (W-02MA0R)  ·  P-2025/3447"}]


def test_rest_num_serie_tolera_sufijo_de_serie(_api_key):
    """El usuario teclea el año; el CRM guarda '2023-n' → casa por prefijo."""
    with patch("core.sudespacho_relations.httpx.get",
               return_value=_mock_get_response(_items_multi(
                   ("406", {"num_expediente": "63", "serie_expediente": "2023-n",
                            "referencia_cliente": "MaRS1 - Velazquez (W-02PLYH)"}),
               ))):
        out = _rest_search_num_serie("63", "2023")
    assert out == [{"id": "406", "label": "MaRS1 - Velazquez (W-02PLYH)"}]


def test_rest_num_serie_sin_api_key_vacio(monkeypatch):
    monkeypatch.setenv("SUDESPACHO_API_KEY", "")
    assert _rest_search_num_serie("63", "2024") == []
```

- [ ] **Step 2: Ejecutar y verificar que fallan**

Run: `python -m pytest tests/test_sudespacho_relations.py -k rest_num_serie -q`
Expected: FAIL — `ImportError: cannot import name '_rest_search_num_serie'`.

- [ ] **Step 3: Implementar**

En `core/sudespacho_relations.py`, tras `_rest_search_por_texto`:

```python
def _norm_serie_local(s: Any) -> str:
    """Normaliza una serie para comparar: sin espacios, minúscula.

    El CRM guarda el sufijo de subserie de forma inconsistente ('2023-n',
    '2022 - p'); el usuario teclea el año a secas. (Misma semántica que
    ``procurador_intake._norm_serie``, reimplementada aquí para evitar el ciclo
    de import procurador_intake ↔ sudespacho_relations.)
    """
    return re.sub(r"\s+", "", str(s)).lower()


def _rest_search_num_serie(num: str, serie: str, *, limit: int = 50) -> list[dict[str, str]]:
    """Busca expedientes JUDICIALES por nº interno del despacho (num/serie).

    El ``num_expediente`` se repite por serie (uno por año), así que se filtra
    ``equal num_expediente`` en servidor y se casa la serie en cliente
    (normalizada, por prefijo: el CRM guarda '2023-n', el usuario teclea '2023').
    Para el combobox F2.

    Returns:
        Lista ``[{"id","label"}]``. Nunca lanza ([] ante api-key ausente / CRM
        no accesible).
    """
    num = str(num).strip()
    if not num:
        return []
    url = f"{_REST_BASE}/api/element_registries/expedientes_judiciales"
    params: list[tuple[str, str]] = [
        ("properties[0]", "referencia_cliente"),
        ("properties[1]", "referencia_procurador"),
        ("properties[2]", "num_expediente"),
        ("properties[3]", "serie_expediente"),
        ("filterGroup[condition]", "AND"),
        ("filterGroup[filterGroups][0][condition]", "AND"),
        ("filterGroup[filterGroups][0][filters][0][operator]", "equal"),
        ("filterGroup[filterGroups][0][filters][0][value]", num),
        ("filterGroup[filterGroups][0][filters][0][property]", "num_expediente"),
        ("itemsPerPage", str(limit)),
        ("return_totals", "true"),
    ]
    target = _norm_serie_local(serie)
    out: list[dict[str, str]] = []
    for it in _rest_get_items(url, params):
        vals = _values_dict(it)
        crm_serie = _norm_serie_local(vals.get("serie_expediente", ""))
        if target and not crm_serie.startswith(target):
            continue
        out.append({"id": str(it.get("id", "")), "label": _label_expediente(vals)})
    return out
```

Añadir `_rest_search_num_serie` al bloque de import del test (`from core.sudespacho_relations import (...)`), junto a `_rest_search_por_texto`.

- [ ] **Step 4: Ejecutar y verificar que pasan**

Run: `python -m pytest tests/test_sudespacho_relations.py -k rest_num_serie -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```powershell
cd "C:\Users\tnm33\Dev\FeesDefender"
git add core/sudespacho_relations.py tests/test_sudespacho_relations.py
git commit -m "feat(intake-procuradores): _rest_search_num_serie (nº/serie del despacho)"
```

---

## Task 3: Reescribir `search_expedientes`

**Files:**
- Modify: `core/procurador_search.py:13-72` (imports, `ELEMENTOS_BUSCABLES`, `search_expedientes`)
- Test: `tests/test_procurador_search.py:1-57` (rehacer los 3 tests de búsqueda)

- [ ] **Step 1: Reescribir los tests (que fallarán)**

Sustituir en `tests/test_procurador_search.py` el bloque de imports y los tres tests `test_search_expedientes_*` (líneas 1-57) por:

```python
"""Tests de core.procurador_search — búsqueda/lectura del CRM para el combobox F2."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.procurador_search import (
    ELEMENTOS_BUSCABLES,
    fetch_expediente_datos,
    recompute_coincidencias,
    search_expedientes,
)


@pytest.fixture
def _api_key(monkeypatch):
    monkeypatch.setenv("SUDESPACHO_API_KEY", "test_key_abc")


def _mock_get(json_data, status=200):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = json_data
    return r


def _items_multi(*rows):
    items = []
    for eid, props in rows:
        vals = [{"property": {"name": k}, "value": v} for k, v in props.items()]
        items.append({"id": str(eid), "values": vals})
    return {"totalItems": len(items), "items": items}


def test_clientes_fuera_de_elementos_buscables():
    """`clientes` se retiró: no tiene referencia ni alimenta recompute."""
    assert "clientes" not in ELEMENTOS_BUSCABLES
    assert "expedientes_judiciales" in ELEMENTOS_BUSCABLES


def test_search_termino_vacio_no_toca_red(_api_key):
    with patch("core.sudespacho_relations.httpx.get") as g:
        assert search_expedientes("   ") == []
        g.assert_not_called()


def test_search_por_texto_mapea_id_y_label(_api_key):
    """Búsqueda libre → REST OR-like; devuelve [{id,label}] con ref del procurador."""
    with patch("core.sudespacho_relations.httpx.get",
               return_value=_mock_get(_items_multi(
                   ("487", {"referencia_cliente": "BaRS3 - Torrent 41 (W-02MA0R)",
                            "referencia_procurador": "P-2025/3447"}),
               ))):
        out = search_expedientes("Torrent")
    assert out == [{"id": "487",
                    "label": "BaRS3 - Torrent 41 (W-02MA0R)  ·  P-2025/3447"}]


def test_search_num_serie_dispara_rama_numerica_y_fusiona(_api_key):
    """'63/2024' → texto (sin hits) + num/serie (hit 487), fusionado sin duplicar."""
    def _get(url, *, params, headers, timeout):
        es_num = ("filterGroup[filterGroups][0][filters][0][property]",
                  "num_expediente") in params
        if es_num:
            return _mock_get(_items_multi(
                ("487", {"num_expediente": "63", "serie_expediente": "2024",
                         "referencia_cliente": "BaRS3 - Torrent 41 (W-02MA0R)"}),
            ))
        return _mock_get(_items_multi())  # la búsqueda por texto no encuentra "63/2024"

    with patch("core.sudespacho_relations.httpx.get", side_effect=_get):
        out = search_expedientes("63/2024")
    assert out == [{"id": "487", "label": "BaRS3 - Torrent 41 (W-02MA0R)"}]


def test_search_ano_barra_num_no_dispara_rama_numerica(_api_key):
    """'2025/7449' (ref de procurador, año delante) NO va a num/serie, solo texto."""
    llamadas: list = []

    def _get(url, *, params, headers, timeout):
        llamadas.append(params)
        return _mock_get(_items_multi(
            ("487", {"referencia_cliente": "BaRS3 - Torrent 41 (W-02MA0R)",
                     "referencia_procurador": "2025/7449"}),
        ))

    with patch("core.sudespacho_relations.httpx.get", side_effect=_get):
        out = search_expedientes("2025/7449")
    # Solo una llamada (texto); ninguna con equal num_expediente
    assert len(llamadas) == 1
    assert all(("filterGroup[filterGroups][0][filters][0][property]",
                "num_expediente") not in p for p in llamadas)
    assert out == [{"id": "487",
                    "label": "BaRS3 - Torrent 41 (W-02MA0R)  ·  2025/7449"}]


def test_search_alias_extrajudicial_normaliza_slug(_api_key):
    captured: dict = {}

    def _get(url, *, params, headers, timeout):
        captured["url"] = url
        return _mock_get(_items_multi())

    with patch("core.sudespacho_relations.httpx.get", side_effect=_get):
        search_expedientes("algo", element="expedientes_extrajudiciales")
    assert "element_registries/extrajudiciales" in captured["url"]


def test_search_sin_api_key_devuelve_vacio(monkeypatch):
    monkeypatch.setenv("SUDESPACHO_API_KEY", "")
    assert search_expedientes("Torrent") == []
```

(Los tests de `fetch_expediente_datos`/`recompute_coincidencias` de las líneas 60+ se mantienen sin cambios.)

- [ ] **Step 2: Ejecutar y verificar que fallan**

Run: `python -m pytest tests/test_procurador_search.py -q`
Expected: FAIL — `ImportError: cannot import name 'ELEMENTOS_BUSCABLES'`… o `AssertionError`/llamadas al cliente legacy. (La implementación vieja usa `_autocomplete`.)

- [ ] **Step 3: Reescribir la implementación**

En `core/procurador_search.py`, sustituir el bloque de imports (líneas 18-28) por:

```python
from .procurador_intake import (
    _MATCH_PROPERTIES,
    IntakeSignals,
    _check_signal_matches,
)
from .sudespacho_relations import (
    _SEARCH_PROPS_BY_ELEMENT,
    _normalize_element,
    _rest_search_num_serie,
    _rest_search_por_texto,
)
from .sync_sudespacho import SudespachoClient
```

Añadir `import re` junto a los imports de arriba (tras `import logging`).

Sustituir `ELEMENTOS_BUSCABLES` (línea 33) por:

```python
# Elementos CRM buscables desde el combobox. `clientes` se retiró (2026-06-12):
# no tiene property de referencia ni alimenta recompute_coincidencias.
ELEMENTOS_BUSCABLES = ("expedientes_judiciales", "expedientes_extrajudiciales")

# Nº interno del despacho citado por procuradores: "63/2024" (num/AÑO). El año
# (19xx/20xx) va DETRÁS, lo que lo distingue de refs de procurador "AÑO/nº"
# (p. ej. "2025/7449"), que van a la búsqueda por texto.
_NUM_SERIE_RE = re.compile(r"^\s*(\d{1,4})\s*/\s*((?:19|20)\d{2})\s*$")
```

Sustituir toda la función `search_expedientes` (líneas 36-72) por:

```python
def search_expedientes(
    term: str,
    *,
    element: str = "expedientes_judiciales",
    client: object | None = None,
) -> list[dict[str, str]]:
    """Busca expedientes en el CRM por texto libre → ``[{"id", "label"}]``.

    Vía REST (x-api-key), no el autocomplete legacy (que devuelve body vacío
    contra el CRM real — ver docs/DEAD_ENDS.md "Frontal heredado"). Busca en
    paralelo por:

    - **texto libre** (OR-``like``): nombre del caso (``referencia_cliente``) y
      ref del procurador (``referencia_procurador``) en judicial; solo
      ``Referencia_Cliente`` en extrajudicial.
    - **nº interno del despacho** (``num_expediente``/serie): solo si ``term``
      casa ``nº/AÑO`` y el elemento es judicial. Se fusiona sin duplicar.

    Args:
        term: texto libre (nombre del caso, ref del procurador, o ``nº/AÑO``).
        element: ``expedientes_judiciales`` (default) |
            ``expedientes_extrajudiciales``.
        client: ignorado — la búsqueda es REST. Se conserva por compatibilidad
            de firma con el resto del módulo / la UI.

    Nunca lanza: ``[]`` ante término vacío / elemento no buscable / CRM no
    accesible / api-key ausente.
    """
    term = (term or "").strip()
    if not term:
        return []
    elem = _normalize_element(element)
    if elem not in _SEARCH_PROPS_BY_ELEMENT:
        return []

    resultados = _rest_search_por_texto(elem, term)

    m = _NUM_SERIE_RE.match(term)
    if m and elem == "expedientes_judiciales":
        vistos = {r["id"] for r in resultados}
        for r in _rest_search_num_serie(m.group(1), m.group(2)):
            if r["id"] not in vistos:
                resultados.append(r)
                vistos.add(r["id"])
    return resultados
```

Actualizar el docstring del módulo (líneas 6-8) para que no afirme que el combobox usa el cliente legacy/autocomplete:

```python
Dos vías de lectura (ambas REST x-api-key, inyectables vía mock de ``httpx``):
el **combobox** busca con ``_rest_search_por_texto`` / ``_rest_search_num_serie``
(``sudespacho_relations``); la lectura de campos por id usa ``SudespachoClient``.
Solo lectura: NO escribe en el CRM (la escritura es F3).
```

- [ ] **Step 4: Ejecutar y verificar que pasan**

Run: `python -m pytest tests/test_procurador_search.py -q`
Expected: PASS (todos: los nuevos de búsqueda + los de `fetch_expediente_datos`/`recompute_coincidencias` intactos).

- [ ] **Step 5: Suite completa (sin regresiones en dedup)**

Run: `python -m pytest -q`
Expected: PASS, mismo nº de tests verde que antes + los nuevos (ningún fallo en `test_sudespacho_relations.py` de dedup, `test_dedup_*`, ni en el matcher F1).

- [ ] **Step 6: Commit**

```powershell
cd "C:\Users\tnm33\Dev\FeesDefender"
git add core/procurador_search.py tests/test_procurador_search.py
git commit -m "feat(intake-procuradores): search_expedientes por REST (texto + nº/serie); quita clientes"
```

---

## Task 4: Documentar callejones (autos vacío, contrario sin ruta REST)

**Files:**
- Modify: `docs/DEAD_ENDS.md` (sección "Frontal heredado" / API sudespacho)
- Modify: `docs/MEJORAS_FUTURAS.md`

- [ ] **Step 1: Cerrar el pendiente y añadir hallazgos en `DEAD_ENDS.md`**

En `docs/DEAD_ENDS.md`, en la línea del pendiente de `search_expedientes` (la `⚠️ Pendiente relacionado`, ~línea 23), sustituir por:

```markdown
- **✅ Resuelto (2026-06-12):** `core.procurador_search.search_expedientes` migrado a REST (`_rest_search_por_texto` + `_rest_search_num_serie`). Ver plan `docs/superpowers/plans/2026-06-12-search-expedientes-rest.md`.
```

Y añadir una entrada nueva en la sección "API sudespacho.net":

```markdown
### Búsqueda de expedientes por `num_asunto` (autos) y por contrario — sin datos / sin ruta
- **`num_asunto` (nº de autos):** el operador `like` se acepta (HTTP 200) pero el campo está **vacío en todo el tenant** (total=0 incluso con `like ~ "20"`, probe 2026-06-12). Buscar por autos no devuelve nada hoy. El día que se pueble, `_rest_search_por_texto` podría añadirlo a `_SEARCH_PROPS_BY_ELEMENT["expedientes_judiciales"]`.
- **Contrario → expedientes (relación inversa):** el contrario es elemento relacionado (`clientes_contrarios`), NO property del expediente. `element_registries/clientes_contrarios` con `properties[0]=nombre` sí lista (total=1083), pero NO hay ruta REST para ir del contrario a sus expedientes: `GET /api/relation_element/...` → 405 (solo POST/PUT/DELETE); el JSON del expediente no trae relaciones embebidas. Buscar por contrario exigiría frontal legacy (roto: autocomplete vacío) o un endpoint inverso inexistente. **Confirmado 2026-06-12.**
```

- [ ] **Step 2: Añadir backlog en `MEJORAS_FUTURAS.md`**

Añadir (en la sección de intake/procuradores o backlog general):

```markdown
- **Combobox F2 — búsqueda por contrario:** bloqueada por API (sin ruta REST inversa contrario→expedientes, 405; ver DEAD_ENDS). Reabrir solo si aparece endpoint inverso o se decide scraping del frontal legacy. Disparador: caso real que lo necesite.
- **Combobox F2 — búsqueda por nº de autos (`num_asunto`):** trivial de añadir a `_SEARCH_PROPS_BY_ELEMENT` cuando el campo deje de estar vacío en el tenant. Disparador: que se empiece a poblar `num_asunto`.
```

- [ ] **Step 3: Commit**

```powershell
cd "C:\Users\tnm33\Dev\FeesDefender"
git add docs/DEAD_ENDS.md docs/MEJORAS_FUTURAS.md
git commit -m "docs(intake-procuradores): cierra pendiente search_expedientes; autos/contrario a DEAD_ENDS+MEJORAS"
```

---

## Verificación final

- [ ] `python -m pytest -q` → suite verde completa.
- [ ] `git log --oneline -5` → 4 commits de la entrega.
- [ ] Revisar que `core/procurador_search.py` ya no importa `_autocomplete` ni `SudespachoLegacyClient` (búsqueda 100% REST).
```
