# Spec: Guard de deduplicación robusto

**Fecha:** 2026-06-10
**Tag:** `[SIGUIENTE-DEDUP-GUARD-ROBUSTO]`
**Estado:** Aprobado — pendiente de implementación

---

## Problema

Al crear un caso, la búsqueda de duplicados en el CRM falla cuando la
`referencia_cliente` almacenada difiere tipográficamente del `case_id` local.
Ejemplo real: expediente 444 tiene `(W-02NV4W)  - Vuelta` (doble espacio) en
el CRM; el case_id estándar lleva un solo espacio →
`find_expediente_judicial_by_referencia` devuelve `None` → crearía un duplicado.

Además, `verify_expediente_referencia` (validación post-creación) compara con
`.strip()` solamente, sin normalización de espacios internos ni acentos.

El warning de la UI ("no se creará un expediente duplicado") es engañoso: solo
mira `_caso.md` local, no el CRM.

## Alcance

| Pieza | En alcance | Motivo |
|-------|:----------:|--------|
| Guard CRM (`find_expediente_*_by_referencia`) | ✅ | Causa raíz del bug |
| `verify_expediente_referencia` | ✅ | Comparación frágil |
| Texto UI duplicado | ✅ | Engañoso |
| Guard Drive | ❌ | Hoy el match es por `folder_id` (URL), no por nombre |

## Diseño

### 1. `normalize_referencia(s: str) -> str`

Nueva función **pública** en `core/sudespacho_relations.py`.

Operaciones, en orden:
1. `s.strip()`
2. Colapsar espacios múltiples a uno: `re.sub(r'\s+', ' ', s)`
3. NFKD → quitar marcas combinantes (acentos): `unicodedata.normalize('NFKD', s)` → filtrar `Mn`
4. Lowercase

No se reutiliza `_normalize_label` de `case_manager.py` porque (a) es privada,
(b) hace `encode('ascii', 'ignore')` que elimina más de lo necesario (ej. ñ),
y (c) acoplar módulos por una utilidad genérica viola la separación de capas.

### 2. `_extract_w_code(case_id: str) -> str | None`

Helper **privado** en `core/sudespacho_relations.py`.

Regex: `r'\b(W-[A-Z0-9]{5,8})\b'` (case-insensitive).
Devuelve el primer match o `None` (casos legacy sin W-code).

### 3. Búsqueda robusta en `find_expediente_*_by_referencia`

Ambas funciones (`find_expediente_by_referencia`,
`find_expediente_judicial_by_referencia`) cambian de:

```python
results = _autocomplete(element, referencia_cliente, client)
if results:
    return str(results[0]["value"])
return None
```

a:

```python
def _match_in_results(results, referencia_cliente):
    """Devuelve el ID del primer resultado cuya label matchee normalizada."""
    target = normalize_referencia(referencia_cliente)
    for r in results:
        if normalize_referencia(r.get("label", "")) == target:
            return str(r["value"])
    return None

# 1. Buscar por W-code (término corto, más tolerante al fuzzy del CRM)
w_code = _extract_w_code(referencia_cliente)
if w_code:
    results = _autocomplete(element, w_code, client)
    match = _match_in_results(results, referencia_cliente)
    if match:
        return match

# 2. Fallback: buscar con referencia completa
results = _autocomplete(element, referencia_cliente, client)
return _match_in_results(results, referencia_cliente)
```

**Cambio de comportamiento**: hoy se devuelve `results[0]["value"]` a ciegas.
Con el cambio, solo se devuelve un resultado cuya label matchee normalizada.
Esto evita falsos positivos (autocomplete que devuelve expedientes de otra
operación que comparten prefijo).

**Coste**: una llamada HTTP extra en el peor caso (cuando la búsqueda por
W-code no matchea y se recurre a la búsqueda completa). En el caso habitual
(W-code presente y el CRM devuelve el expediente) es una sola llamada.

### 4. `verify_expediente_referencia`

Cambiar la comparación:

```python
# Antes
match = crm_ref.strip() == expected_referencia.strip()

# Después
match = normalize_referencia(crm_ref) == normalize_referencia(expected_referencia)
```

### 5. UI: texto corregido

`streamlit_app.py` ~L1706-1709. Cambiar de:

> "Al enviar a sudespacho solo se actualizarán relaciones y se hará el pull
> (no se creará un expediente duplicado)."

a:

> "Al enviar a sudespacho se verificará primero en el CRM si ya existe un
> expediente con esta referencia."

El guard real (L1857-1892) ya funciona y bloquea — solo el texto era engañoso.

### 6. Tests

| Test | Fichero | Qué cubre |
|------|---------|-----------|
| `TestNormalizeReferencia` | `tests/test_sudespacho_relations.py` | Doble espacio, acentos, case, combinaciones, string vacío |
| `TestExtractWCode` | `tests/test_sudespacho_relations.py` | Case_id estándar, sin W-code, W-code con variaciones |
| `TestFindExpedienteRobust` | `tests/test_sudespacho_relations.py` | Mock de `_autocomplete` con label con doble espacio → detecta duplicado; sin W-code → fallback funciona; autocomplete vacía → None; resultado sin match normalizado → None |
| `TestVerifyNormalized` | `tests/test_sudespacho_relations.py` | Variaciones que antes fallaban (doble espacio, acento) ahora matchean |

## Fuera de alcance

- Guard de Drive (matching por `folder_id`, no por nombre).
- Normalizar la `referencia_cliente` en el CRM remoto.
- Cambiar el endpoint de autocomplete por REST.
- Ampliar la guarda a otros campos (nombre, dirección).
