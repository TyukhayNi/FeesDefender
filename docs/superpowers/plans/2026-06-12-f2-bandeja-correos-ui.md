# F2 UI «Bandeja de correos» (§18.6 completo) + CLI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cerrar F2 del intake de procuradores con la pestaña Streamlit «Bandeja de correos» (tarjeta rica §18.6: 3 estados 🟢/🟡/🔴, checks verdes, combobox de reasignación, vista Descartados) y un CLI thin sobre `fetch_and_run`, todo en dry-run.

**Architecture:** 3 capas (CLAUDE.md): la lógica vive en `core/`, la UI solo orquesta. Se ensancha el snapshot persistido en la cola (`RobotProposal`) para que la tarjeta se reconstruya sin llamar al CRM; un módulo nuevo `core/procurador_search.py` aporta la búsqueda/lectura del CRM para el combobox; la pestaña Streamlit cablea el core ya existente (`load_queue`, `transicionar`, `record_decision`, `upsert_queue_item`, `set_actor`).

**Tech Stack:** Python 3, pytest, Streamlit, `httpx` (clientes Sudespacho REST x-api-key + legacy PHPSESSID), dataclasses + JSONL append-only.

**Spec:** `docs/superpowers/specs/2026-06-12-f2-bandeja-correos-ui-design.md`

> **✅ EJECUTADO (2026-06-12, subagent-driven).** T1 `9490eca` · T2 superada por REST (`feat/search-expedientes-rest`, fusionada) · T3 `945030b`+`1300719` · T4 `15df2f2` · T5 `1f336dc`+`c3bc790` · T6 `cbfafba`+`3b24f45` (fix bug crítico de estado del combobox) · T7 planificación. Suite **935 passed, 58 skipped**. Cada tarea revisada (spec + calidad) por subagentes.

---

## File Structure

- **Modify** `core/procurador_review.py` — ensanchar `RobotProposal` con `signals`/`datos_expediente`/`coincidencias`; `from_intake_proposal` los copia; `_item_from_dict` los relee con defaults.
- **Create** `core/procurador_search.py` — `search_expedientes`, `fetch_expediente_datos`, `recompute_coincidencias` (búsqueda/lectura CRM para el combobox).
- **Create** `scripts/intake_procuradores.py` — CLI thin sobre `fetch_and_run` (dry-run).
- **Modify** `streamlit_app.py` — 5ª pestaña «Bandeja de correos» (solo orquesta).
- **Modify** `tests/test_procurador_review.py` — round-trip del snapshot ensanchado + `from_intake_proposal`.
- **Create** `tests/test_procurador_search.py` — los 3 helpers del módulo nuevo.
- **Create** `tests/test_intake_procuradores_cli.py` — smoke del CLI con `fetch_fn` inyectado.

**Nota de entorno (CLAUDE.md):** Windows + PowerShell. Comandos `pytest` desde la raíz del repo. UTF-8 sin BOM en todos los ficheros nuevos. La suite completa **muta el working tree** (flake conocido de `test_skill_helpers_sync`), así que cada `git add` debe ser **acotado a los ficheros de la tarea**, nunca `git add -A`.

---

## Task 1: Ensanchar `RobotProposal` con el contexto de la tarjeta

**Files:**
- Modify: `core/procurador_review.py` (dataclass `RobotProposal` ~36-44; `from_intake_proposal` ~47-62; `_item_from_dict` ~311-330)
- Test: `tests/test_procurador_review.py`

- [ ] **Step 1: Write the failing tests**

Añadir al final de `tests/test_procurador_review.py`:

```python
# ---------------------------------------------------------------------------
# Contexto de la tarjeta persistido en la cola (§18.6)
# ---------------------------------------------------------------------------

def test_from_intake_proposal_copia_contexto_de_la_tarjeta():
    """from_intake_proposal congela señales + datos_expediente + coincidencias."""
    signals = IntakeSignals(
        su_ref="13/2026", num_expediente=13, serie_expediente="2026",
        contrario="ACME S.L.", juzgado="JPI nº 4 de Valencia",
        num_asunto="123/2025", tipo_procedimiento="ordinario",
        tipo_actuacion="auto",
    )
    match = MatchResult(
        expediente_id=532, confianza="alta",
        datos_expediente={"id": 532, "num_expediente": 13, "serie_expediente": "2026",
                          "juzgado": "JPI 4 Valencia"},
        senales_usadas=["su_ref", "num_expediente", "serie_expediente"],
    )
    proposal = IntakeProposal(signals=signals, match=match, attachments=[],
                              carpeta_sugerida="General", carpeta_id=1)

    robot = from_intake_proposal("m1", proposal)

    assert robot.signals["su_ref"] == "13/2026"
    assert robot.signals["contrario"] == "ACME S.L."
    assert "raw_llm" not in robot.signals          # no se persiste el JSON del LLM
    assert robot.datos_expediente["num_expediente"] == 13
    # coincidencias = solo los nombres de campo (sin tokens de control "su_ref")
    assert set(robot.coincidencias) == {"num_expediente", "serie_expediente"}


def test_robot_proposal_contexto_default_vacio():
    """Construir un RobotProposal sin contexto → dicts/listas vacías (retrocompat)."""
    robot = RobotProposal(email_id="m9", expediente_id=None, confianza="ninguna",
                          carpeta_id=None, carpeta=None)
    assert robot.signals == {}
    assert robot.datos_expediente == {}
    assert robot.coincidencias == []


def test_cola_round_trip_conserva_contexto(tmp_path):
    """upsert + load preserva señales/datos/coincidencias del snapshot."""
    store = tmp_path / "cola.jsonl"
    robot = RobotProposal(
        email_id="m1", expediente_id=532, confianza="alta", carpeta_id=1,
        carpeta="General",
        signals={"su_ref": "13/2026", "contrario": "ACME S.L."},
        datos_expediente={"id": 532, "juzgado": "JPI 4 Valencia"},
        coincidencias=["num_expediente"],
    )
    item = ReviewItem(email_id="m1", proposal=robot, estado="pendiente",
                      remitente="p@x.com", asunto="13/2026", fecha="2026-06-12")
    upsert_queue_item(item, store_path=store)

    loaded = load_queue(store_path=store)
    assert len(loaded) == 1
    p = loaded[0].proposal
    assert p.signals["contrario"] == "ACME S.L."
    assert p.datos_expediente["juzgado"] == "JPI 4 Valencia"
    assert p.coincidencias == ["num_expediente"]


def test_cola_load_item_viejo_sin_contexto(tmp_path):
    """Un item persistido SIN los campos nuevos se relee con defaults vacíos."""
    store = tmp_path / "cola.jsonl"
    # Línea "vieja": proposal sin signals/datos_expediente/coincidencias.
    store.write_text(
        '{"email_id": "m1", "estado": "pendiente", "proposal": '
        '{"email_id": "m1", "expediente_id": 5, "confianza": "alta", '
        '"carpeta_id": 1, "carpeta": "General", "attachment_names": {}}}\n',
        encoding="utf-8",
    )
    loaded = load_queue(store_path=store)
    assert loaded[0].proposal.signals == {}
    assert loaded[0].proposal.datos_expediente == {}
    assert loaded[0].proposal.coincidencias == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_procurador_review.py -k "contexto or round_trip or item_viejo" -v`
Expected: FAIL — `RobotProposal.__init__() got an unexpected keyword argument 'signals'` (y `from_intake_proposal` sin `.signals`).

- [ ] **Step 3: Implement — ensanchar `RobotProposal`**

En `core/procurador_review.py`, sustituir la dataclass `RobotProposal` (líneas ~36-44) por:

```python
@dataclass
class RobotProposal:
    """La pata *propuesta-del-robot* de la terna: lo que F1 propuso para un correo.

    Lleva además el **contexto de la tarjeta** (§18.6) congelado en el snapshot,
    para que la bandeja Streamlit lo renderice sin volver a llamar al CRM:
    - ``signals``: señales crudas del correo (sin ``raw_llm``).
    - ``datos_expediente``: campos del expediente emparejado.
    - ``coincidencias``: campos que coinciden (checks verdes 🟢).
    """
    email_id: str
    expediente_id: int | None
    confianza: str                       # "alta" | "dudosa" | "ninguna"
    carpeta_id: int | None
    carpeta: str | None
    attachment_names: dict[str, str] = field(default_factory=dict)
    signals: dict[str, Any] = field(default_factory=dict)
    datos_expediente: dict[str, Any] = field(default_factory=dict)
    coincidencias: list[str] = field(default_factory=list)
```

Justo encima de `from_intake_proposal`, añadir las constantes de filtrado:

```python
# Campos de señal que la tarjeta muestra/compara (sin raw_llm, que infla el store).
_SIGNAL_FIELDS = (
    "su_ref", "num_expediente", "serie_expediente", "contrario", "cliente",
    "juzgado", "num_asunto", "tipo_procedimiento", "tipo_actuacion",
    "fecha_actuacion", "es_ruido",
)

# Nombres de campo que cuentan como "dato que coincide" (checks verdes 🟢).
# Subconjunto de senales_usadas; el resto son tokens de control (su_ref,
# su_ref_multiple, es_ruido_advisory, sin_su_ref, ...) que NO son coincidencias.
_FIELD_COINCIDENCIAS = frozenset({
    "num_expediente", "serie_expediente", "juzgado", "num_asunto",
    "tipo_procedimiento",
})
```

Sustituir el cuerpo de `from_intake_proposal` (líneas ~53-62) por:

```python
    signals_dict = {
        k: getattr(proposal.signals, k, None) for k in _SIGNAL_FIELDS
    }
    coincidencias = [
        s for s in proposal.match.senales_usadas if s in _FIELD_COINCIDENCIAS
    ]
    return RobotProposal(
        email_id=email_id,
        expediente_id=proposal.match.expediente_id,
        confianza=proposal.match.confianza,
        carpeta_id=proposal.carpeta_id,
        carpeta=proposal.carpeta_sugerida,
        attachment_names={
            a.original_filename: a.proposed_name for a in proposal.attachments
        },
        signals=signals_dict,
        datos_expediente=dict(proposal.match.datos_expediente),
        coincidencias=coincidencias,
    )
```

En `_item_from_dict` (líneas ~311-330), ampliar la reconstrucción del `RobotProposal` para releer los campos nuevos con defaults:

```python
    proposal = RobotProposal(
        email_id=prop.get("email_id", d.get("email_id", "")),
        expediente_id=prop.get("expediente_id"),
        confianza=prop.get("confianza", "ninguna"),
        carpeta_id=prop.get("carpeta_id"),
        carpeta=prop.get("carpeta"),
        attachment_names=prop.get("attachment_names") or {},
        signals=prop.get("signals") or {},
        datos_expediente=prop.get("datos_expediente") or {},
        coincidencias=prop.get("coincidencias") or [],
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_procurador_review.py -v`
Expected: PASS (todos, incl. los previos — los campos nuevos tienen defaults).

- [ ] **Step 5: Commit**

```bash
git add core/procurador_review.py tests/test_procurador_review.py
git commit -m "feat(intake-procuradores): persistir contexto de tarjeta en la cola (F2 §18.6)"
```

---

## Task 2: `search_expedientes` (combobox del CRM)

> **[x] HECHA — superada por la implementación REST en `feat/search-expedientes-rest` (fusionada a esta rama por fast-forward, 2026-06-12).** El probe contra el CRM real demostró que el autocomplete legacy devuelve body vacío para expedientes (`DEAD_ENDS.md` "Frontal heredado"), así que la versión legacy de esta tarea quedó obsoleta y fue reescrita a REST (`/api/element_registries` + `like`, x-api-key). Contrato vigente: `search_expedientes(term, *, element="expedientes_judiciales", client=None) -> list[{"id","label"}]`; `ELEMENTOS_BUSCABLES = ("expedientes_judiciales", "expedientes_extrajudiciales")` (sin `clientes`); `client` se ignora (REST, sin gotcha PHPSESSID); nunca lanza (`[]` ante error). `fetch_expediente_datos` (T3) y `recompute_coincidencias` (T4) se conservan. **La Task 6 consume este contrato.**

**Files:**
- Create: `core/procurador_search.py`
- Test: `tests/test_procurador_search.py`

- [ ] **Step 1: Write the failing test**

Crear `tests/test_procurador_search.py`:

```python
"""Tests de core.procurador_search — búsqueda/lectura del CRM para el combobox F2."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from core.procurador_search import (
    fetch_expediente_datos,
    recompute_coincidencias,
    search_expedientes,
)


def _mock_legacy_client():
    client = MagicMock()
    client._check_session = MagicMock()
    client.__exit__ = MagicMock(return_value=False)
    return client


def _mock_get(json_data, status=200):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = json_data
    return r


def test_search_expedientes_mapea_value_a_id():
    """El id del expediente es el campo `value` del autocomplete; label se conserva."""
    client = _mock_legacy_client()
    client._client.get.return_value = _mock_get(
        [{"id": 1, "label": "13 - 2026 · ACME", "value": "532", "data": []},
         {"id": 2, "label": "14 - 2026 · OTRO", "value": "533", "data": []}]
    )
    out = search_expedientes("ACME", client=client)
    assert out == [
        {"id": "532", "label": "13 - 2026 · ACME"},
        {"id": "533", "label": "14 - 2026 · OTRO"},
    ]


def test_search_expedientes_element_judicial_por_defecto():
    """Por defecto busca en expedientes_judiciales (el caso de procuradores)."""
    client = _mock_legacy_client()
    client._client.get.return_value = _mock_get([])
    search_expedientes("algo", client=client)
    url = client._client.get.call_args[0][0]
    assert "expedientes_judiciales" in url


def test_search_expedientes_element_override():
    """Se puede buscar en extrajudiciales / clientes (🔴 toggle)."""
    client = _mock_legacy_client()
    client._client.get.return_value = _mock_get([])
    search_expedientes("algo", element="clientes", client=client)
    url = client._client.get.call_args[0][0]
    assert "clientes" in url
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_procurador_search.py -k search_expedientes -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.procurador_search'`.

- [ ] **Step 3: Implement `search_expedientes`**

Crear `core/procurador_search.py`:

```python
"""F2 — Búsqueda y lectura del CRM para la bandeja de procuradores (combobox §18.6).

Lógica de core que la pestaña Streamlit «Bandeja de correos» orquesta para
reasignar el expediente de un correo 🟡/🔴 y refrescar los checks verdes 🟢.

Dos clientes (ya existentes): el **autocomplete** del CRM usa el cliente *legacy*
(PHPSESSID); la lectura de campos por id usa el cliente **REST** (x-api-key), el
mismo que el matcher F1. Ambos inyectables → tests sin red.

Solo lectura: NO escribe en el CRM (la escritura es F3).
"""

from __future__ import annotations

import logging
from typing import Any

from .procurador_intake import (
    _MATCH_PROPERTIES,
    IntakeSignals,
    _check_signal_matches,
)
from .sudespacho_relations import (
    SudespachoLegacyClient,
    SudespachoRelationsError,
    _autocomplete,
)

logger = logging.getLogger("feesdefender.procurador_search")

# Elementos CRM buscables desde el combobox (🔴 ofrece los tres).
ELEMENTOS_BUSCABLES = ("expedientes_judiciales", "expedientes_extrajudiciales", "clientes")


def search_expedientes(
    term: str,
    *,
    element: str = "expedientes_judiciales",
    client: SudespachoLegacyClient | None = None,
) -> list[dict[str, str]]:
    """Busca expedientes en el CRM por texto libre → ``[{"id", "label"}]``.

    Reutiliza el autocomplete del CRM (``_autocomplete``). El id del expediente es
    el campo ``value`` del autocomplete (no ``id``, que es el índice de la fila).

    Args:
        term: texto libre (referencia, contrario, cliente, autos).
        element: ``expedientes_judiciales`` (default) | ``expedientes_extrajudiciales`` | ``clientes``.
        client: cliente legacy reutilizable (tests / sesión de la UI).
    """
    if not term or not term.strip():
        return []
    owns = client is None
    if owns:
        client = SudespachoLegacyClient()
    try:
        rows = _autocomplete(element, term.strip(), client)
    except SudespachoRelationsError as exc:
        logger.warning("search_expedientes(%r) falló: %s", term, exc)
        return []
    finally:
        if owns:
            try:
                client.__exit__(None, None, None)
            except Exception:
                pass
    return [
        {"id": str(r.get("value", "")), "label": str(r.get("label", ""))}
        for r in rows
        if r.get("value")
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_procurador_search.py -k search_expedientes -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/procurador_search.py tests/test_procurador_search.py
git commit -m "feat(intake-procuradores): search_expedientes (combobox CRM F2)"
```

---

## Task 3: `fetch_expediente_datos` (lectura de campos por id)

**Files:**
- Modify: `core/procurador_search.py`
- Test: `tests/test_procurador_search.py`

- [ ] **Step 1: Write the failing test**

Añadir a `tests/test_procurador_search.py`:

```python
def test_fetch_expediente_datos_parsea_values_por_id():
    """Lee los _MATCH_PROPERTIES del expediente vía element_registries (REST)."""
    client = MagicMock()
    client.__exit__ = MagicMock(return_value=False)
    client._client.get.return_value = _mock_get({
        "hydra:member": [{
            "id": 532,
            "values": [
                {"property": {"name": "num_expediente"}, "value": 13},
                {"property": {"name": "serie_expediente"}, "value": "2026"},
                {"property": {"name": "juzgado"}, "value": "JPI 4 Valencia"},
                {"property": {"name": "ignorada"}, "value": "x"},
            ],
        }]
    })
    datos = fetch_expediente_datos(532, client=client)
    assert datos["id"] == 532
    assert datos["num_expediente"] == 13
    assert datos["juzgado"] == "JPI 4 Valencia"
    assert "ignorada" not in datos                 # solo _MATCH_PROPERTIES


def test_fetch_expediente_datos_sin_resultado():
    """Expediente inexistente / HTTP no-200 → dict vacío (no rompe la tarjeta)."""
    client = MagicMock()
    client.__exit__ = MagicMock(return_value=False)
    client._client.get.return_value = _mock_get({"hydra:member": []}, status=200)
    assert fetch_expediente_datos(999, client=client) == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_procurador_search.py -k fetch_expediente_datos -v`
Expected: FAIL — `ImportError: cannot import name 'fetch_expediente_datos'`.

- [ ] **Step 3: Implement**

En `core/procurador_search.py`, añadir el import del cliente REST al bloque de imports:

```python
from .sync_sudespacho import SudespachoClient
```

Y añadir la función:

```python
def fetch_expediente_datos(
    expediente_id: int | str,
    *,
    element: str = "expedientes_judiciales",
    client: SudespachoClient | None = None,
) -> dict[str, Any]:
    """Lee los ``_MATCH_PROPERTIES`` de un expediente por id (REST x-api-key).

    Mismo patrón de parseo de ``values`` que ``_search_by_num_serie``. Devuelve
    ``{}`` si no hay resultado o el CRM responde != 200 (la tarjeta degrada, no
    rompe). Solo lectura.
    """
    owns = client is None
    if owns:
        client = SudespachoClient()
    try:
        path = f"/api/element_registries/{element}"
        params: list[tuple[str, str]] = [
            (f"properties[{i}]", p) for i, p in enumerate(_MATCH_PROPERTIES)
        ] + [
            ("filterGroup[condition]", "AND"),
            ("filterGroup[filterGroups][0][condition]", "AND"),
            ("filterGroup[filterGroups][0][filters][0][operator]", "equal"),
            ("filterGroup[filterGroups][0][filters][0][value]", str(expediente_id)),
            ("filterGroup[filterGroups][0][filters][0][property]", "id"),
            ("itemsPerPage", "1"),
        ]
        r = client._client.get(path, params=params)
        if r.status_code != 200:
            logger.warning("fetch_expediente_datos(%s) → HTTP %d", expediente_id, r.status_code)
            return {}
        data = r.json()
        items = data.get("hydra:member", data.get("items", []))
        if not items:
            return {}
        item = items[0]
        out: dict[str, Any] = {"id": item.get("id")}
        for val_obj in item.get("values", []):
            name = (val_obj.get("property") or {}).get("name", "")
            if name in _MATCH_PROPERTIES:
                out[name] = val_obj.get("value")
        return out
    finally:
        if owns:
            client.__exit__(None, None, None)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_procurador_search.py -k fetch_expediente_datos -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/procurador_search.py tests/test_procurador_search.py
git commit -m "feat(intake-procuradores): fetch_expediente_datos por id (REST)"
```

---

## Task 4: `recompute_coincidencias` (checks verdes al reasignar)

**Files:**
- Modify: `core/procurador_search.py`
- Test: `tests/test_procurador_search.py`

- [ ] **Step 1: Write the failing test**

Añadir a `tests/test_procurador_search.py`:

```python
def test_recompute_coincidencias_delega_en_check_signal_matches():
    """Reconstruye IntakeSignals desde el dict persistido y recomputa coincidencias."""
    signals_dict = {
        "num_expediente": 13, "serie_expediente": "2026",
        "juzgado": "Juzgado de Primera Instancia nº 4 de Valencia",
        "num_asunto": "123/2025", "tipo_procedimiento": "ordinario",
    }
    datos_expediente = {
        "id": 532, "num_expediente": 13, "serie_expediente": "2026",
        "juzgado": "JPI 4 Valencia", "num_asunto": "123 / 2025",
        "tipo_procedimiento": "Juicio ordinario",
    }
    out = recompute_coincidencias(signals_dict, datos_expediente)
    assert set(out) == {"num_expediente", "serie_expediente", "juzgado",
                        "num_asunto", "tipo_procedimiento"}


def test_recompute_coincidencias_parcial():
    """Solo num/serie coinciden → solo esos dos."""
    signals_dict = {"num_expediente": 13, "serie_expediente": "2026", "juzgado": "X"}
    datos = {"num_expediente": 13, "serie_expediente": "2026", "juzgado": "Y distinto"}
    out = recompute_coincidencias(signals_dict, datos)
    assert set(out) == {"num_expediente", "serie_expediente"}


def test_recompute_coincidencias_sin_datos():
    """datos_expediente vacío → sin coincidencias (no rompe)."""
    assert recompute_coincidencias({"num_expediente": 13}, {}) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_procurador_search.py -k recompute -v`
Expected: FAIL — `ImportError: cannot import name 'recompute_coincidencias'`.

- [ ] **Step 3: Implement**

En `core/procurador_search.py`, añadir:

```python
# Campos de IntakeSignals que `_check_signal_matches` compara (reconstrucción).
_SIGNAL_KEYS = (
    "su_ref", "num_expediente", "serie_expediente", "contrario", "cliente",
    "juzgado", "num_asunto", "tipo_procedimiento", "tipo_actuacion",
    "fecha_actuacion",
)


def recompute_coincidencias(
    signals_dict: dict[str, Any],
    datos_expediente: dict[str, Any],
) -> list[str]:
    """Recomputa los checks verdes 🟢 tras reasignar expediente en el combobox.

    Reconstruye un ``IntakeSignals`` desde el dict persistido en la cola y delega
    en ``_check_signal_matches`` (la misma comparación tolerante que usa el
    matcher F1: juzgado por tokens, num_asunto normalizado, etc.).
    """
    if not datos_expediente:
        return []
    kwargs = {k: signals_dict.get(k) for k in _SIGNAL_KEYS}
    kwargs["es_ruido"] = bool(signals_dict.get("es_ruido", False))
    signals = IntakeSignals(**kwargs)
    return _check_signal_matches(signals, datos_expediente)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_procurador_search.py -v`
Expected: PASS (todos los del módulo).

- [ ] **Step 5: Commit**

```bash
git add core/procurador_search.py tests/test_procurador_search.py
git commit -m "feat(intake-procuradores): recompute_coincidencias al reasignar (checks verdes)"
```

---

## Task 5: CLI thin `scripts/intake_procuradores.py`

**Files:**
- Create: `scripts/intake_procuradores.py`
- Test: `tests/test_intake_procuradores_cli.py`

- [ ] **Step 1: Write the failing test**

Crear `tests/test_intake_procuradores_cli.py`:

```python
"""Smoke del CLI de ingesta de procuradores (dry-run, fetch inyectado)."""

from __future__ import annotations

from core.procurador_runner import EmailMessage, ReviewItem
from core.procurador_review import RobotProposal
from scripts.intake_procuradores import resumen_recuentos


def _item(email_id, confianza, estado="pendiente", motivo=None):
    return ReviewItem(
        email_id=email_id,
        proposal=RobotProposal(email_id=email_id, expediente_id=None,
                               confianza=confianza, carpeta_id=None, carpeta=None),
        estado=estado, motivo_descarte=motivo,
    )


def test_resumen_recuentos_agrupa_por_estado_y_confianza():
    items = [
        _item("a", "alta"),
        _item("b", "dudosa"),
        _item("c", "ninguna"),
        _item("d", "ninguna", estado="descartado", motivo="ruido_llm"),
        _item("e", "ninguna", estado="descartado", motivo="remitente_no_procurador"),
    ]
    res = resumen_recuentos(items)
    assert res["total"] == 5
    assert res["pendiente"]["alta"] == 1
    assert res["pendiente"]["dudosa"] == 1
    assert res["pendiente"]["ninguna"] == 1
    assert res["descartado"]["ruido_llm"] == 1
    assert res["descartado"]["remitente_no_procurador"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_intake_procuradores_cli.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.intake_procuradores'`.

- [ ] **Step 3: Implement**

Crear `scripts/intake_procuradores.py`:

```python
"""CLI thin de ingesta de correos de procuradores → cola de la bandeja (dry-run).

Robot del plan §3: trae los buzones del despacho, corre el matcher F1 y puebla la
cola de revisión (``core.procurador_review``). NO escribe en el CRM. La
confirmación humana es la pestaña Streamlit «Bandeja de correos» (F2.3b).

Uso:
    python -m scripts.intake_procuradores [--once] [--query "..."] [--account a@b]

Scheduling: se delega al SO / skill `schedule` (no demonio propio). El gotcha de
PHPSESSID (~24 min) NO afecta a este runner (usa REST x-api-key).

Salida en ASCII (gotcha cp1252 en PowerShell, CLAUDE.md).
"""

from __future__ import annotations

import argparse
from collections import Counter
from typing import Any

from core.gmail_source import BUZONES_DESPACHO, DEFAULT_QUERY, fetch_and_run
from core.procurador_runner import ReviewItem


def resumen_recuentos(items: list[ReviewItem]) -> dict[str, Any]:
    """Agrega los items procesados por estado y (pendientes) por confianza."""
    pendientes = Counter(i.proposal.confianza for i in items if i.estado == "pendiente")
    descartados = Counter(
        i.motivo_descarte or "sin_motivo" for i in items if i.estado == "descartado"
    )
    return {
        "total": len(items),
        "pendiente": dict(pendientes),
        "descartado": dict(descartados),
    }


def _print_resumen(res: dict[str, Any]) -> None:
    p = res["pendiente"]
    d = res["descartado"]
    print(f"[intake-procuradores] procesados: {res['total']}")
    print(
        "  a bandeja (pendiente): "
        f"alta={p.get('alta', 0)} dudosa={p.get('dudosa', 0)} ninguna={p.get('ninguna', 0)}"
    )
    if d:
        detalle = " ".join(f"{k}={v}" for k, v in sorted(d.items()))
        print(f"  descartados: {detalle}")
    else:
        print("  descartados: 0")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingesta de correos de procuradores (dry-run).")
    parser.add_argument("--once", action="store_true",
                        help="Una sola pasada (default; reservado para futuro modo loop).")
    parser.add_argument("--query", default=DEFAULT_QUERY, help="Query Gmail.")
    parser.add_argument("--account", action="append", default=None,
                        help="Cuenta a sondear (repetible). Default: buzones del despacho.")
    args = parser.parse_args(argv)

    accounts = tuple(args.account) if args.account else BUZONES_DESPACHO
    items = fetch_and_run(accounts, query=args.query)
    _print_resumen(resumen_recuentos(items))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_intake_procuradores_cli.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/intake_procuradores.py tests/test_intake_procuradores_cli.py
git commit -m "feat(intake-procuradores): CLI thin sobre fetch_and_run (dry-run, §3)"
```

---

## Task 6: Pestaña Streamlit «Bandeja de correos»

**Files:**
- Modify: `streamlit_app.py` (fila de tabs ~445-447; añadir bloque `with tab_bandeja:` al final del archivo)

> Sin tests automáticos (patrón del repo para la UI). La UI **solo orquesta**: toda la lógica vive en el core ya testeado. Verificación = smoke manual (Step 4).

- [ ] **Step 1: Añadir la pestaña a la fila de tabs**

En `streamlit_app.py`, sustituir (líneas ~445-447):

```python
tab_nuevo, tab_casos, tab_pipeline, tab_visor = st.tabs(
    ["Nuevo caso", "Casos", "Pipeline", "Visor"]
)
```

por:

```python
tab_nuevo, tab_casos, tab_pipeline, tab_visor, tab_bandeja = st.tabs(
    ["Nuevo caso", "Casos", "Pipeline", "Visor", "Bandeja de correos"]
)
```

- [ ] **Step 2: Añadir el bloque de la pestaña al final de `streamlit_app.py`**

Añadir al final del archivo:

```python
# ── TAB: Bandeja de correos (F2 §18.6) ──────────────────────────────────────
with tab_bandeja:
    from core import procurador_review as _pr
    from core import procurador_search as _ps
    from core.intake_log import set_actor, get_actor

    st.subheader("Bandeja de correos de procuradores")
    st.caption("Dry-run: confirmar registra la decision (terna §18.9); NO escribe en el CRM (eso es F3).")

    # Login ligero por persona (alimenta el "quien confirmo").
    _actor = st.radio("Yo soy", ["Nikolai", "Paola", "Ana"], horizontal=True,
                      key="bandeja_actor",
                      help="Tu nombre queda en el log de auditoria de cada decision.")
    set_actor(_actor)

    pendientes = _pr.load_queue(estado="pendiente")
    descartados = _pr.load_queue(estado="descartado")

    # Cabecera de triaje: recuentos por confianza.
    n_alta = sum(1 for i in pendientes if i.proposal.confianza == "alta")
    n_dud = sum(1 for i in pendientes if i.proposal.confianza == "dudosa")
    n_sin = sum(1 for i in pendientes if i.proposal.confianza == "ninguna")
    c1, c2, c3 = st.columns(3)
    c1.metric("🟢 Alta", n_alta)
    c2.metric("🟡 Dudosa", n_dud)
    c3.metric("🔴 Sin expediente", n_sin)

    # Filtro por procurador (remitente).
    remitentes = sorted({i.remitente or "(desconocido)" for i in pendientes})
    filtro = st.selectbox("Filtrar por procurador", ["(todos)"] + remitentes,
                          key="bandeja_filtro")
    st.checkbox("Confirmar en bloque las de alta", value=False, disabled=True,
                key="bandeja_bloque",
                help="Desactivado de inicio: empezar revisando todo (plan §6).")

    st.divider()

    if not pendientes:
        st.info("No hay correos pendientes en la cola. Lanza la ingesta: "
                "`python -m scripts.intake_procuradores`.")

    _ICONO = {"alta": "🟢", "dudosa": "🟡", "ninguna": "🔴"}

    for item in pendientes:
        if filtro != "(todos)" and (item.remitente or "(desconocido)") != filtro:
            continue
        prop = item.proposal
        icono = _ICONO.get(prop.confianza, "🔴")
        with st.expander(f"{icono} {item.asunto or '(sin asunto)'} — {item.remitente or ''}",
                         expanded=(prop.confianza != "alta")):
            st.caption(f"Recibido: {item.fecha or 's/f'} · email_id `{item.email_id}`")

            # --- Datos detectados en el correo (siempre visibles, util en 🔴) ---
            sig = prop.signals or {}
            if sig:
                detectados = {k: v for k, v in sig.items() if v not in (None, "", False)}
                if detectados:
                    st.markdown("**Datos detectados en el correo**")
                    st.json(detectados, expanded=False)

            # --- Expediente + checks verdes ---
            exp_id = prop.expediente_id
            datos = dict(prop.datos_expediente or {})
            coincidencias = list(prop.coincidencias or [])

            if prop.confianza == "alta" and exp_id:
                st.success(f"Expediente #{exp_id} — {len(coincidencias)} datos coinciden")
                for campo in ("num_expediente", "serie_expediente", "juzgado",
                              "num_asunto", "tipo_procedimiento"):
                    if campo in datos:
                        check = "✅" if campo in coincidencias else "▫️"
                        st.write(f"{check} {campo}: {datos.get(campo)}")
                cambiar = st.toggle("Cambiar expediente", key=f"chg_{item.email_id}")
            else:
                if prop.confianza == "dudosa":
                    st.warning("Match debil — VERIFICA el expediente antes de confirmar.")
                else:
                    st.error("Sin expediente. Busca y asignalo abajo.")
                cambiar = True

            # --- Combobox de busqueda (reasignacion) ---
            sel_exp_id = exp_id
            if cambiar:
                elemento = st.selectbox(
                    "Buscar en", _ps.ELEMENTOS_BUSCABLES,
                    key=f"elem_{item.email_id}",
                )
                term = st.text_input("Buscar expediente (ref / contrario / autos)",
                                     key=f"term_{item.email_id}")
                if term:
                    try:
                        candidatos = _ps.search_expedientes(term, element=elemento)
                    except Exception as exc:  # PHPSESSID caducado, etc.
                        candidatos = []
                        st.warning(f"Busqueda no disponible (¿renovar sesion CRM?): {exc}")
                    if candidatos:
                        etiqueta = st.selectbox(
                            "Candidatos", candidatos,
                            format_func=lambda c: f"{c['label']} (#{c['id']})",
                            key=f"cand_{item.email_id}",
                        )
                        if st.button("Usar este expediente", key=f"use_{item.email_id}"):
                            sel_exp_id = int(etiqueta["id"])
                            datos = _ps.fetch_expediente_datos(sel_exp_id, element=elemento)
                            coincidencias = _ps.recompute_coincidencias(sig, datos)
                            st.success(f"Expediente #{sel_exp_id}: {len(coincidencias)} coinciden")

            # --- Carpeta destino ---
            carpeta_id = st.number_input("Carpeta destino (id)", value=int(prop.carpeta_id or 0),
                                         step=1, key=f"carp_{item.email_id}")

            # --- Acciones ---
            puede_confirmar = sel_exp_id is not None
            col_ok, col_no = st.columns(2)
            if col_ok.button("Confirmar", key=f"ok_{item.email_id}",
                             disabled=not puede_confirmar, type="primary"):
                action = _pr.HumanAction(
                    tipo="confirmar",
                    expediente_id=(sel_exp_id if sel_exp_id != exp_id else None),
                    carpeta_id=(int(carpeta_id) if int(carpeta_id) != (prop.carpeta_id or 0) else None),
                )
                _pr.record_decision(prop, action, quien=get_actor())
                nuevo = _pr.transicionar(item, "confirmar")
                _pr.upsert_queue_item(nuevo)
                st.toast(f"Confirmado (dry-run): {item.email_id}")
                st.rerun()
            if col_no.button("Descartar", key=f"no_{item.email_id}"):
                action = _pr.HumanAction(tipo="descartar")
                _pr.record_decision(prop, action, quien=get_actor())
                nuevo = _pr.transicionar(item, "descartar", motivo="descartado_humano")
                _pr.upsert_queue_item(nuevo)
                st.toast(f"Descartado: {item.email_id}")
                st.rerun()

    # --- Vista Descartados (baja prioridad, colapsada) ---
    st.divider()
    with st.expander(f"Descartados ({len(descartados)})", expanded=False):
        if not descartados:
            st.caption("Nada descartado.")
        for item in descartados:
            cols = st.columns([3, 2, 2, 1])
            cols[0].write(item.asunto or "(sin asunto)")
            cols[1].write(item.remitente or "")
            cols[2].write(item.motivo_descarte or "")
            if cols[3].button("Recuperar", key=f"rec_{item.email_id}"):
                nuevo = _pr.transicionar(item, "recuperar")
                _pr.upsert_queue_item(nuevo)
                st.toast(f"Recuperado a bandeja: {item.email_id}")
                st.rerun()
```

- [ ] **Step 3: Verificar que el resto de la suite no se rompe por el import**

Run: `python -m pytest -q --tb=short tests/test_procurador_review.py tests/test_procurador_search.py tests/test_intake_procuradores_cli.py`
Expected: PASS (la UI no tiene tests, pero confirma que los imports nuevos de `streamlit_app` no rompen nada al colectar).

- [ ] **Step 4: Smoke manual (documentar resultado)**

```powershell
cd "C:\Users\tnm33\Dev\FeesDefender"
# (con la cola poblada: python -m scripts.intake_procuradores)
streamlit run streamlit_app.py
```
Verificar en la pestaña «Bandeja de correos»: recuentos correctos, tarjeta 🟢 con checks verdes, combobox en 🟡/🔴, Confirmar/Descartar mueven el item, vista Descartados con Recuperar. Anotar el resultado del smoke en `STATUS.md` al cierre.

- [ ] **Step 5: Commit**

```bash
git add streamlit_app.py
git commit -m "feat(intake-procuradores): pestana Streamlit Bandeja de correos (F2 §18.6)"
```

---

## Task 7: Suite completa + cierre

- [ ] **Step 1: Suite verde**

Run: `python -m pytest -q --tb=short -p no:randomly`
Expected: el conteo previo (899 passed, 58 skipped) **+ los tests nuevos** (≈ +12). Cualquier fallo ajeno preexistente (p. ej. `test_llm_local` por Ollama ausente) se documenta, no se silencia.

- [ ] **Step 2: Actualizar planificación**

En `PLAN.md`, marcar F2 como UI ✅ (entrada `[SIGUIENTE-INTAKE-PROCURADORES-EMAIL]`, línea ~50-59) y anotar los hashes de commit. En `docs/PLAN_INTAKE_PROCURADORES_EMAIL.md` §15, marcar F2 completa.

- [ ] **Step 3: Commit de planificación (acotado)**

```bash
git add PLAN.md docs/PLAN_INTAKE_PROCURADORES_EMAIL.md
git commit -m "docs(intake-procuradores): F2 UI completa — bandeja + CLI"
```

> El cierre formal (`STATUS.md` + memoria) lo hace `/cierre` al final de la sesion.

---

## Self-Review (cobertura del spec)

- **Persistir contexto en la cola** → Task 1 (señales/datos/coincidencias + retrocompat). ✅
- **`search_expedientes` (combobox)** → Task 2. ✅
- **`fetch_expediente_datos`** → Task 3. ✅
- **`recompute_coincidencias` (reusa `_check_signal_matches`)** → Task 4. ✅
- **CLI thin sobre `fetch_and_run`** → Task 5. ✅
- **Pestaña Streamlit (login, 3 tarjetas, checks, combobox, Descartados+Recuperar, dry-run)** → Task 6. ✅
- **`record_decision` cableado (terna + divergencia)** → Task 6 (Confirmar/Descartar). ✅
- **Tests TDD** → Tasks 1-5. **UI sin tests automáticos** (declarado en spec). ✅
- **Límites (F3 escritura CRM, F4 OCR, scheduler persistente) fuera** → respetado. ✅
- **Gotchas (PHPSESSID, ASCII, UTF-8, `git add` acotado)** → cableados en Tasks 5, 6, 7. ✅

Type consistency: `RobotProposal(signals, datos_expediente, coincidencias)`, `HumanAction(tipo, expediente_id, carpeta_id, ...)`, `transicionar(item, accion, motivo=)`, `record_decision(proposal, action, quien=)`, `search_expedientes(...)→[{"id","label"}]`, `fetch_expediente_datos(...)→dict`, `recompute_coincidencias(dict, dict)→list[str]` — coherentes entre tareas y con el core existente.
