# Dedup Guard Robusto — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent duplicate expedientes in the CRM by normalizing reference comparison in the dedup guard (search + verify) and fixing misleading UI text.

**Architecture:** Two new helpers (`normalize_referencia`, `_extract_w_code`) in `core/sudespacho_relations.py`, a shared `_find_expediente_robust` that replaces the naive first-result logic with W-code search + normalized label matching, and a one-line fix in `verify_expediente_referencia`. UI text correction in `streamlit_app.py`.

**Tech Stack:** Python 3.12, pytest, unittest.mock

**Spec:** `docs/superpowers/specs/2026-06-10-dedup-guard-robusto-design.md`

---

### Task 1: `normalize_referencia` — test + implementation

**Files:**
- Modify: `core/sudespacho_relations.py` (add function after imports, ~line 96)
- Test: `tests/test_sudespacho_relations.py` (append new class)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_sudespacho_relations.py`:

```python
# ---------------------------------------------------------------------------
# normalize_referencia
# ---------------------------------------------------------------------------

from core.sudespacho_relations import normalize_referencia


class TestNormalizeReferencia:
    def test_collapses_double_space(self):
        assert normalize_referencia("(W-02NV4W)  - Vuelta") == normalize_referencia("(W-02NV4W) - Vuelta")

    def test_strips_whitespace(self):
        assert normalize_referencia("  hello  ") == "hello"

    def test_removes_accents(self):
        assert normalize_referencia("María García") == "maria garcia"

    def test_lowercase(self):
        assert normalize_referencia("BaRS1 - [inmueble]") == "bars1 - inmueble"

    def test_combined(self):
        assert normalize_referencia("  BaRS1  - [inmueble]  (W-02VND1)  - Vuelta ") == "bars1 - inmueble (w-02vnd1) - vuelta"

    def test_empty_string(self):
        assert normalize_referencia("") == ""

    def test_preserves_n_tilde(self):
        # ñ → n after NFKD + stripping Mn category
        assert normalize_referencia("Peña") == "pena"

    def test_tabs_and_newlines(self):
        assert normalize_referencia("a\t\tb\nc") == "a b c"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_sudespacho_relations.py::TestNormalizeReferencia -v`
Expected: ImportError — `normalize_referencia` not yet exported.

- [ ] **Step 3: Implement `normalize_referencia`**

Add two imports at the top of `core/sudespacho_relations.py` (after existing imports around line 74):

```python
import re
import unicodedata
```

Add the function after the existing helpers section (after `_autocomplete`, before `find_expediente_by_referencia`, around line 240):

```python
def normalize_referencia(s: str) -> str:
    """Normaliza una referencia de expediente para comparación tolerante.

    Colapsa espacios, quita acentos, lowercase. Útil para detectar duplicados
    cuando la referencia en el CRM difiere tipográficamente del case_id local
    (ej. doble espacio, mayúsculas, acentos).
    """
    if not s:
        return ""
    s = s.strip()
    s = re.sub(r"\s+", " ", s)
    nfkd = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    return s.lower()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_sudespacho_relations.py::TestNormalizeReferencia -v`
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add core/sudespacho_relations.py tests/test_sudespacho_relations.py
git commit -m "feat(dedup): add normalize_referencia for tolerant reference comparison"
```

---

### Task 2: `_extract_w_code` — test + implementation

**Files:**
- Modify: `core/sudespacho_relations.py` (add function near `normalize_referencia`)
- Test: `tests/test_sudespacho_relations.py` (append new class)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_sudespacho_relations.py`:

```python
# ---------------------------------------------------------------------------
# _extract_w_code
# ---------------------------------------------------------------------------

from core.sudespacho_relations import _extract_w_code


class TestExtractWCode:
    def test_standard_case_id(self):
        assert _extract_w_code("BaRS1 - [inmueble] - (W-02VND1) - Vuelta") == "W-02VND1"

    def test_no_w_code(self):
        assert _extract_w_code("MaRS2 - Gran Vía 40 - Vuelta") is None

    def test_lowercase_w_code(self):
        assert _extract_w_code("(w-02nv4w)") == "w-02nv4w"

    def test_w_code_with_5_chars(self):
        assert _extract_w_code("(W-ABCDE)") == "W-ABCDE"

    def test_w_code_with_8_chars(self):
        assert _extract_w_code("(W-ABCDEF12)") == "W-ABCDEF12"

    def test_empty_string(self):
        assert _extract_w_code("") is None

    def test_w_code_at_start(self):
        assert _extract_w_code("W-0466A1 es el código") == "W-0466A1"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_sudespacho_relations.py::TestExtractWCode -v`
Expected: ImportError — `_extract_w_code` not yet exported.

- [ ] **Step 3: Implement `_extract_w_code`**

Add right after `normalize_referencia` in `core/sudespacho_relations.py`:

```python
_W_CODE_RE = re.compile(r"\b(W-[A-Za-z0-9]{5,8})\b")


def _extract_w_code(case_id: str) -> str | None:
    """Extrae el código W-XXXXXX de un case_id, o None si no tiene."""
    m = _W_CODE_RE.search(case_id)
    return m.group(1) if m else None
```

Also add `_extract_w_code` to the import in `tests/test_sudespacho_relations.py` (top-level import block, line ~9-34). Since the test file already imports `_autocomplete` and other private names, adding `_extract_w_code` follows the existing pattern.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_sudespacho_relations.py::TestExtractWCode -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add core/sudespacho_relations.py tests/test_sudespacho_relations.py
git commit -m "feat(dedup): add _extract_w_code helper for W-code extraction"
```

---

### Task 3: Robust `find_expediente_*_by_referencia` — test + implementation

**Files:**
- Modify: `core/sudespacho_relations.py:241-320` (rewrite both functions)
- Test: `tests/test_sudespacho_relations.py` (append new class + update existing tests)

- [ ] **Step 1: Write the failing tests for the new robust behavior**

Append to `tests/test_sudespacho_relations.py`:

```python
# ---------------------------------------------------------------------------
# Robust find_expediente — normalized matching + W-code search
# ---------------------------------------------------------------------------


class TestFindExpedienteRobust:
    """Tests for the dual-search (W-code + full ref) with normalized label matching."""

    def test_double_space_in_crm_label_matches(self):
        """The real bug: CRM has double space, local has single → should match."""
        client = _mock_client()
        # Autocomplete returns result with double space in label
        client._client.get.return_value = _mock_get_response([
            {"id": 1, "label": "BaRS6 - Addr - (W-02NV4W)  - Vuelta", "value": "444", "data": []},
        ])
        result = find_expediente_judicial_by_referencia(
            "BaRS6 - Addr - (W-02NV4W) - Vuelta", client=client,
        )
        assert result == "444"

    def test_accent_difference_matches(self):
        """CRM has accent, local doesn't (or vice versa)."""
        client = _mock_client()
        client._client.get.return_value = _mock_get_response([
            {"id": 1, "label": "MaRS2 - Gran Vía 40 - (W-0001) - Vuelta", "value": "500", "data": []},
        ])
        result = find_expediente_by_referencia(
            "MaRS2 - Gran Via 40 - (W-0001) - Vuelta", client=client,
        )
        assert result == "500"

    def test_case_difference_matches(self):
        client = _mock_client()
        client._client.get.return_value = _mock_get_response([
            {"id": 1, "label": "bars1 - inmueble - (W-02VND1) - vuelta", "value": "100", "data": []},
        ])
        result = find_expediente_by_referencia(
            "BaRS1 - [inmueble] - (W-02VND1) - Vuelta", client=client,
        )
        assert result == "100"

    def test_no_match_in_results_returns_none(self):
        """Autocomplete returns results but none match normalized → None."""
        client = _mock_client()
        client._client.get.return_value = _mock_get_response([
            {"id": 1, "label": "Completely Different Case", "value": "999", "data": []},
        ])
        result = find_expediente_by_referencia(
            "BaRS1 - [inmueble] - (W-02VND1) - Vuelta", client=client,
        )
        assert result is None

    def test_empty_autocomplete_returns_none(self):
        client = _mock_client()
        client._client.get.return_value = _mock_get_response([])
        result = find_expediente_by_referencia("Whatever", client=client)
        assert result is None

    def test_no_w_code_falls_back_to_full_ref(self):
        """Legacy case_id without W-code: searches with full referencia only."""
        client = _mock_client()
        client._client.get.return_value = _mock_get_response([
            {"id": 1, "label": "EV-2026-001", "value": "200", "data": []},
        ])
        result = find_expediente_by_referencia("EV-2026-001", client=client)
        assert result == "200"

    def test_w_code_search_finds_match_on_first_try(self):
        """W-code search succeeds → no second autocomplete call needed."""
        client = _mock_client()
        call_count = 0
        original_get = client._client.get

        def counting_get(url):
            nonlocal call_count
            call_count += 1
            return _mock_get_response([
                {"id": 1, "label": "BaRS1 - X - (W-02VND1) - Vuelta", "value": "100", "data": []},
            ])

        client._client.get = counting_get
        result = find_expediente_judicial_by_referencia(
            "BaRS1 - X - (W-02VND1) - Vuelta", client=client,
        )
        assert result == "100"
        assert call_count == 1  # Only the W-code search, no fallback

    def test_w_code_search_misses_falls_back(self):
        """W-code search returns no match → falls back to full ref search."""
        client = _mock_client()
        call_count = 0

        def two_phase_get(url):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # W-code search: returns unrelated result
                return _mock_get_response([
                    {"id": 1, "label": "Other thing with W-02VND1", "value": "999", "data": []},
                ])
            else:
                # Full ref search: returns the correct match
                return _mock_get_response([
                    {"id": 1, "label": "BaRS1 - X - (W-02VND1) - Vuelta", "value": "100", "data": []},
                ])

        client._client.get = two_phase_get
        result = find_expediente_judicial_by_referencia(
            "BaRS1 - X - (W-02VND1) - Vuelta", client=client,
        )
        assert result == "100"
        assert call_count == 2  # W-code search + fallback
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_sudespacho_relations.py::TestFindExpedienteRobust -v`
Expected: Several FAIL — old implementation returns `results[0]["value"]` without normalized comparison, so `test_no_match_in_results_returns_none` fails (returns "999" instead of None). Others may pass incidentally.

- [ ] **Step 3: Add `_match_in_results` helper and refactor `_find_expediente_robust`**

In `core/sudespacho_relations.py`, add a shared helper right after `_extract_w_code`:

```python
def _match_in_results(
    results: list[dict[str, Any]],
    referencia_cliente: str,
) -> str | None:
    """Devuelve el ID del primer resultado cuya label matchee normalizada."""
    target = normalize_referencia(referencia_cliente)
    for r in results:
        if normalize_referencia(r.get("label", "")) == target:
            return str(r["value"])
    return None


def _find_expediente_robust(
    element: str,
    referencia_cliente: str,
    client: SudespachoLegacyClient,
) -> str | None:
    """Búsqueda robusta de expediente: W-code primero, luego referencia completa.

    Compara las labels de los resultados de autocomplete con normalización
    tolerante (espacios, acentos, case) para evitar falsos negativos por
    variaciones tipográficas en la referencia_cliente del CRM.
    """
    w_code = _extract_w_code(referencia_cliente)
    if w_code:
        results = _autocomplete(element, w_code, client)
        match = _match_in_results(results, referencia_cliente)
        if match:
            return match

    results = _autocomplete(element, referencia_cliente, client)
    return _match_in_results(results, referencia_cliente)
```

Then rewrite `find_expediente_by_referencia` (lines 241-279) to delegate:

```python
def find_expediente_by_referencia(
    referencia_cliente: str,
    *,
    client: SudespachoLegacyClient | None = None,
) -> str | None:
    """Busca un expediente extrajudicial por su referencia_cliente (case_id).

    Útil para detectar duplicados antes de crear un nuevo expediente.
    Usa búsqueda dual (W-code + referencia completa) con comparación
    normalizada para tolerar variaciones tipográficas.

    Args:
        referencia_cliente: El case_id de FeesDefender (ej. "MaRS2 - ...").
        client: Cliente legacy reutilizable (opcional).

    Returns:
        ID del expediente si existe, None si no hay coincidencia.
    """
    owns_client = client is None
    if owns_client:
        client = SudespachoLegacyClient()
    try:
        return _find_expediente_robust("extrajudiciales", referencia_cliente, client)
    except SudespachoLegacyError as exc:
        raise SudespachoRelationsError(str(exc)) from exc
    finally:
        if owns_client:
            try:
                client.__exit__(None, None, None)
            except Exception:
                pass
```

And rewrite `find_expediente_judicial_by_referencia` (lines 282-320) identically but with `"expedientes_judiciales"`:

```python
def find_expediente_judicial_by_referencia(
    referencia_cliente: str,
    *,
    client: SudespachoLegacyClient | None = None,
) -> str | None:
    """Busca un expediente judicial por su referencia_cliente (case_id).

    Útil para detectar duplicados antes de crear un nuevo expediente judicial.
    Usa búsqueda dual (W-code + referencia completa) con comparación
    normalizada para tolerar variaciones tipográficas.

    Args:
        referencia_cliente: El case_id de FeesDefender (ej. "MaRS2 - ...").
        client: Cliente legacy reutilizable (opcional).

    Returns:
        ID del expediente si existe, None si no hay coincidencia.
    """
    owns_client = client is None
    if owns_client:
        client = SudespachoLegacyClient()
    try:
        return _find_expediente_robust(
            "expedientes_judiciales", referencia_cliente, client,
        )
    except SudespachoLegacyError as exc:
        raise SudespachoRelationsError(str(exc)) from exc
    finally:
        if owns_client:
            try:
                client.__exit__(None, None, None)
            except Exception:
                pass
```

- [ ] **Step 4: Update existing tests that relied on the old naive behavior**

The existing tests mock `_autocomplete` via `client._client.get` and check the returned value. With normalized matching, the tests that pass a `label` unrelated to the `referencia_cliente` will now return `None` instead of the `value`. Update these tests so their mock labels match the normalized search term:

In `test_find_expediente_encontrado` (~line 155), change the mock label to match the referencia:

```python
def test_find_expediente_encontrado(monkeypatch):
    client = _mock_client()
    client._client.get.return_value = _mock_get_response(
        [{"id": 1, "label": "TEST-CAPTURA-FEESDEFENDER", "value": "600", "data": []}]
    )
    with patch("core.sudespacho_relations.SudespachoLegacyClient", return_value=client):
        result = find_expediente_by_referencia("TEST-CAPTURA-FEESDEFENDER")
    assert result == "600"
```

In `test_find_expediente_con_client_externo` (~line 173), make the label match:

```python
def test_find_expediente_con_client_externo():
    """Si se pasa client externo, no se llama a SudespachoLegacyClient()."""
    client = _mock_client()
    client._client.get.return_value = _mock_get_response(
        [{"id": 1, "label": "ref", "value": "777", "data": []}]
    )
    result = find_expediente_by_referencia("ref", client=client)
    assert result == "777"
    client.__exit__.assert_not_called()
```

In `test_find_expediente_judicial_encontrado` (~line 188), the mock label `"648 - 2026"` does NOT match the referencia `"MaRS2 - Gran Via 40 - (W-0001) - Dev. Reserva"`, so make it match:

```python
def test_find_expediente_judicial_encontrado(monkeypatch):
    client = _mock_client()
    client._client.get.return_value = _mock_get_response(
        [{"id": 1, "label": "MaRS2 - Gran Via 40 - (W-0001) - Dev. Reserva", "value": "648", "data": []}]
    )
    with patch("core.sudespacho_relations.SudespachoLegacyClient", return_value=client):
        result = find_expediente_judicial_by_referencia("MaRS2 - Gran Via 40 - (W-0001) - Dev. Reserva")
    assert result == "648"
    call_url = client._client.get.call_args[0][0]
    assert "expedientes_judiciales" in call_url
```

In `test_find_expediente_judicial_con_client_externo` (~line 209), make label match:

```python
def test_find_expediente_judicial_con_client_externo():
    """Si se pasa client externo, no se llama a SudespachoLegacyClient()."""
    client = _mock_client()
    client._client.get.return_value = _mock_get_response(
        [{"id": 1, "label": "ref", "value": "999", "data": []}]
    )
    result = find_expediente_judicial_by_referencia("ref", client=client)
    assert result == "999"
    client.__exit__.assert_not_called()
```

- [ ] **Step 5: Run all find_expediente tests**

Run: `python -m pytest tests/test_sudespacho_relations.py -k "find_expediente" -v`
Expected: All pass — both old (updated) and new robust tests.

- [ ] **Step 6: Run full test file to check for regressions**

Run: `python -m pytest tests/test_sudespacho_relations.py -v --tb=short`
Expected: All pass (864+ lines of tests, no regressions).

- [ ] **Step 7: Commit**

```bash
git add core/sudespacho_relations.py tests/test_sudespacho_relations.py
git commit -m "feat(dedup): robust find_expediente with W-code search + normalized matching

Dual search: W-code first (shorter term, better autocomplete hit rate),
then full referencia as fallback. Results compared with normalized labels
(collapsed spaces, no accents, lowercase) to catch the double-space bug
(expediente 444)."
```

---

### Task 4: Normalize `verify_expediente_referencia` comparison

**Files:**
- Modify: `core/sudespacho_relations.py:1515-1520`
- Test: `tests/test_sudespacho_relations.py` (append new class)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_sudespacho_relations.py`:

```python
# ---------------------------------------------------------------------------
# verify_expediente_referencia — normalized comparison
# ---------------------------------------------------------------------------

from core.sudespacho_relations import verify_expediente_referencia


class TestVerifyNormalized:
    """verify_expediente_referencia uses normalized comparison."""

    @patch("core.sudespacho_relations.fetch_referencia_cliente")
    def test_double_space_matches(self, mock_fetch):
        mock_fetch.return_value = ("(W-02NV4W)  - Vuelta", False)
        result = verify_expediente_referencia(
            "444", "expedientes_judiciales",
            expected_referencia="(W-02NV4W) - Vuelta",
        )
        assert result["match"] is True
        assert result["found"] is True

    @patch("core.sudespacho_relations.fetch_referencia_cliente")
    def test_accent_difference_matches(self, mock_fetch):
        mock_fetch.return_value = ("Gran Vía 40", False)
        result = verify_expediente_referencia(
            "500", "extrajudiciales",
            expected_referencia="Gran Via 40",
        )
        assert result["match"] is True

    @patch("core.sudespacho_relations.fetch_referencia_cliente")
    def test_case_difference_matches(self, mock_fetch):
        mock_fetch.return_value = ("bars1 - inmueble", False)
        result = verify_expediente_referencia(
            "100", "extrajudiciales",
            expected_referencia="BaRS1 - [inmueble]",
        )
        assert result["match"] is True

    @patch("core.sudespacho_relations.fetch_referencia_cliente")
    def test_genuinely_different_does_not_match(self, mock_fetch):
        mock_fetch.return_value = ("Completely Different", False)
        result = verify_expediente_referencia(
            "100", "extrajudiciales",
            expected_referencia="Not The Same",
        )
        assert result["match"] is False

    @patch("core.sudespacho_relations.fetch_referencia_cliente")
    def test_none_crm_ref_does_not_match(self, mock_fetch):
        mock_fetch.return_value = (None, False)
        result = verify_expediente_referencia(
            "100", "extrajudiciales",
            expected_referencia="Something",
        )
        assert result["match"] is False
        assert result["found"] is False

    @patch("core.sudespacho_relations.fetch_referencia_cliente")
    def test_crm_unreachable(self, mock_fetch):
        mock_fetch.return_value = (None, True)
        result = verify_expediente_referencia(
            "100", "extrajudiciales",
            expected_referencia="Something",
        )
        assert result["match"] is False
        assert result["crm_unreachable"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_sudespacho_relations.py::TestVerifyNormalized -v`
Expected: `test_double_space_matches`, `test_accent_difference_matches`, and `test_case_difference_matches` FAIL — the current `.strip()` comparison rejects these.

- [ ] **Step 3: Update the comparison in `verify_expediente_referencia`**

In `core/sudespacho_relations.py`, around line 1517-1520, change:

```python
    # Before
    if crm_ref is None or expected_referencia is None:
        match = False
    else:
        match = crm_ref.strip() == expected_referencia.strip()
```

to:

```python
    if crm_ref is None or expected_referencia is None:
        match = False
    else:
        match = normalize_referencia(crm_ref) == normalize_referencia(expected_referencia)
```

Also update the docstring comment (around line 1515-1516) from:

```python
    # Comparación tolerante a espacios; sensible a mayúsculas/acentos (la
    # referencia_cliente del CRM debe coincidir exactamente con el case_id).
```

to:

```python
    # Comparación normalizada: colapsa espacios, quita acentos, lowercase.
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_sudespacho_relations.py::TestVerifyNormalized -v`
Expected: 6 passed.

- [ ] **Step 5: Run full test file**

Run: `python -m pytest tests/test_sudespacho_relations.py -v --tb=short`
Expected: All pass.

- [ ] **Step 6: Commit**

```bash
git add core/sudespacho_relations.py tests/test_sudespacho_relations.py
git commit -m "feat(dedup): normalize comparison in verify_expediente_referencia"
```

---

### Task 5: Fix misleading UI text

**Files:**
- Modify: `streamlit_app.py:1706-1709`

- [ ] **Step 1: Change the warning text**

In `streamlit_app.py`, around line 1706-1709, change:

```python
        st.warning(
            f"⚠️ Este caso ya tiene expediente/s registrado/s en el CRM: {_exp_resumen}. "
            "Al enviar a sudespacho solo se actualizarán relaciones y se hará el pull "
            "(no se creará un expediente duplicado).",
            icon="🗂️",
        )
```

to:

```python
        st.warning(
            f"⚠️ Este caso ya tiene expediente/s registrado/s **localmente**: {_exp_resumen}. "
            "Al enviar a sudespacho se verificará primero en el CRM si ya existe un "
            "expediente con esta referencia.",
            icon="🗂️",
        )
```

- [ ] **Step 2: Run full suite to ensure no regressions**

Run: `python -m pytest -q --tb=no`
Expected: All pass (671+ passed).

- [ ] **Step 3: Commit**

```bash
git add streamlit_app.py
git commit -m "fix(ui): correct misleading duplicate warning text in case creation"
```

---

### Task 6: Final integration check

- [ ] **Step 1: Run the full test suite**

Run: `python -m pytest -q --tb=short`
Expected: All tests pass, same count as before + the new tests (~16 new).

- [ ] **Step 2: Verify no import errors in the module**

Run: `python -c "from core.sudespacho_relations import normalize_referencia, _extract_w_code, find_expediente_by_referencia, find_expediente_judicial_by_referencia, verify_expediente_referencia; print('OK')"`
Expected: `OK`
