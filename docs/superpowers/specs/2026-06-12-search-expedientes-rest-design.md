# Migración de `search_expedientes` (combobox F2) del autocomplete legacy a REST

**Fecha:** 2026-06-12
**Autor:** Claude Code + Nikolai Tyukhay
**Estado:** Diseño aprobado — pendiente de plan de implementación
**Relacionado:** F2 §18.6 (`docs/superpowers/specs/2026-06-12-f2-bandeja-correos-ui-design.md`), `docs/DEAD_ENDS.md` ("Frontal heredado")

## Objetivo

El combobox de reasignación de la bandeja de procuradores (F2 §18.6) usa
`core.procurador_search.search_expedientes()`, que llama al autocomplete legacy
(`_autocomplete`, `GET /autocompletar/buscar/elemento/{element}`). Ese endpoint
**devuelve body vacío contra el CRM real** para expedientes (confirmado
2026-06-12, `DEAD_ENDS.md`). Sus tests pasan solo porque mockean `_autocomplete`.
Por tanto el buscador **no funciona en producción**.

Migrar `search_expedientes` al mecanismo REST (`GET /api/element_registries/
{element}` con filtro `like`, header `x-api-key`), el mismo ya usado por
`find_expediente_by_referencia` / `list_expedientes_judiciales_candidatos`.

## Evidencia empírica (probe read-only, 2026-06-12, tenant tnm)

Probe contra `https://api-crm-commons-pro.sudespacho.biz` (script de un disparo,
borrado tras el diseño). Resultados que fundamentan el alcance:

1. **`like` sobre `referencia_cliente`** → funciona (cubre equipo/finca/W-code,
   porque la referencia es el `case_id` completo, p. ej.
   `"BaRS3 - Torrent de les Flors 41 - (W-02MA0R) - Vuelta - COMPRADOR"`).
2. **`like` sobre `referencia_procurador`** → funciona y el campo **está
   poblado**: 6 expedientes con `"P-"`, 106 con `"/"`, 9 con `"2025"`. Es el
   identificador que el procurador escribe en su correo (`P-2025/3447`,
   `SP-3599`, `2026/7476`, `FJ | 2026/58`…).
3. **OR multi-property** (`filterGroup[...][condition]=OR` con dos filtros
   `like`) → aceptado (HTTP 200).
4. **`num_expediente` + serie** (la ref interna del despacho, `63/2024`):
   `equal num_expediente=63` → **4 expedientes, uno por serie** (2025, 2024,
   2023-n, 2019-p). El número se repite cada año → **la serie es necesaria**
   para desambiguar. `like` sobre el número es ruidoso (matchea 263, 163). El
   operador correcto es `equal` + casar serie normalizada (lo que ya hace
   `procurador_intake._search_by_num_serie`, medido 100% en F1).
5. **`num_asunto` (nº de autos)** → vacío en TODO el tenant (total=0 incluso
   con `like ~ "20"`). El operador funciona; no hay datos. **Fuera de alcance.**
6. **Contrario** → es elemento relacionado (`clientes_contrarios`), no property
   del expediente:
   - `element_registries/clientes_contrarios` con `properties[0]=nombre` →
     HTTP 200, total=1083 (buscar contrario por nombre SÍ es viable).
   - Pero **no existe ruta REST inversa contrario→expedientes**:
     `GET /api/relation_element/...` → 405 (solo POST/PUT/DELETE); otras rutas
     404. El JSON del expediente no trae relaciones embebidas (solo
     `@type, isPrimary, id, values`). **Bloqueado por API. Fuera de alcance.**

## Decisiones (cerradas con Nikolai 2026-06-12)

1. **Alcance de búsqueda:** tres identificadores, en paralelo:
   - nombre del caso (`referencia_cliente`),
   - referencia del procurador (`referencia_procurador`),
   - número interno del despacho (`num_expediente`/serie), solo con patrón
     `nº/AÑO`.
2. **`clientes`** se elimina de `ELEMENTOS_BUSCABLES`: no tiene property de
   referencia, no alimenta `recompute_coincidencias` (un cliente no recompone
   los checks de un expediente), y F2 reasigna un correo a un EXPEDIENTE.
3. **Autos (`num_asunto`)** y **contrario**: a `DEAD_ENDS.md` / `MEJORAS_FUTURAS.md`.
4. **`_rest_search_expedientes` NO se toca** (lo usa el dedup con extracción de
   W-code y match exacto). El combobox usa un helper nuevo, con semántica
   distinta: texto **literal** (sin extraer W-code) y OR multi-property.

## Diseño

### Desambiguación del término

El despacho cita el expediente como `nº/AÑO` (`63/2024`); algunas refs de
procurador son `AÑO/nº` (`2025/7449`). Para no confundirlas, el término se trata
como número de expediente del despacho **solo** si casa
`^\s*(\d{1,4})\s*/\s*((?:19|20)\d{2})\s*$` (el año, 19xx/20xx, va detrás). Todo
lo demás (incluido `2025/7449`, `3447`, `Torrent`) va a la búsqueda por texto.

### `core/sudespacho_relations.py` — helper nuevo

```python
# Properties buscables por elemento (texto libre, OR-like).
_SEARCH_PROPS_BY_ELEMENT = {
    "expedientes_judiciales": ("referencia_cliente", "referencia_procurador"),
    "extrajudiciales":        ("Referencia_Cliente",),   # extrajudicial no tiene procurador
}

# Properties que se piden SIEMPRE (para construir el label uniforme).
_LABEL_PROPS = ("referencia_cliente", "referencia_procurador",
                "Referencia_Cliente")  # se filtra por las presentes en cada elemento

def rest_search_expedientes_por_texto(element, term, *, limit=50) -> list[dict[str, str]]:
    """OR-like sobre las _SEARCH_PROPS_BY_ELEMENT del elemento. Término LITERAL
    (sin extraer W-code). Devuelve [{"id", "label"}]; nunca lanza ([] ante
    api-key ausente / elemento desconocido / CRM no-200 / red caída)."""
```

- Construye un `filterGroup` con `condition=OR` y un filtro `like` por cada
  property buscable; pide en `properties[]` las de búsqueda + las de label.
- `label` = valor de `referencia_cliente`/`Referencia_Cliente`; si hay
  `referencia_procurador`, se añade `"  ·  {ref_proc}"` (desambigua en la lista,
  patrón de `search_colaboradores_for_ui`). Si la referencia está vacía, label
  cae a la ref de procurador.
- Reutiliza el bloque HTTP+parseo extrayendo un `_rest_get_items(url, params)`
  común con `_rest_search_expedientes` (mejora contenida; el dedup debe seguir
  verde).

### `core/sudespacho_relations.py` — num+serie para el combobox

`procurador_intake._search_by_num_serie(num, serie, client=...)` ya hace
`equal num_expediente` + match de serie normalizada, pero (a) requiere un
`SudespachoClient` y (b) no pide `referencia_cliente` (su label quedaría sin el
nombre del caso). Para mantener el label uniforme, el combobox usa una variante
ligera en `sudespacho_relations` que pide `referencia_cliente` +
`referencia_procurador` + `num_expediente` + `serie_expediente`, filtra
`equal num_expediente` en servidor y casa la serie en cliente con
`_norm_serie` (importado o reimplementado mínimamente). Devuelve `[{"id","label"}]`.

> Alternativa considerada y descartada: reutilizar `_search_by_num_serie` tal
> cual y enriquecer el label con una segunda llamada por id — añade una llamada
> de red por resultado y acopla el combobox al cliente REST del matcher.

### `core/procurador_search.py` — `search_expedientes`

```python
ELEMENTOS_BUSCABLES = ("expedientes_judiciales", "expedientes_extrajudiciales")  # sin "clientes"

def search_expedientes(term, *, element="expedientes_judiciales", client=None):
    # term vacío → []
    # element se normaliza (alias expedientes_extrajudiciales → extrajudiciales)
    # 1. resultados = rest_search_expedientes_por_texto(elem, term)
    # 2. si elem es judicial y term casa nº/AÑO:
    #       extra = búsqueda num+serie  → fusionar por id (sin duplicar)
    # 3. devolver [{"id","label"}]
    # client se conserva en la firma pero se IGNORA (búsqueda REST x-api-key),
    #   igual que find_expediente_by_referencia.
```

- Fusión: dict por `id` preservando orden (texto primero, luego num/serie que no
  estuvieran ya). El `client` legacy ya no se usa (se documenta).
- Se elimina la dependencia de `_autocomplete` y `SudespachoLegacyClient` en este
  módulo si ningún otro punto los usa (verificar en implementación).

## Tests (TDD)

Reescribir `tests/test_procurador_search.py` (los 3 tests de `search_expedientes`)
mockeando `core.sudespacho_relations.httpx.get` (fixture `_api_key` con
`monkeypatch.setenv`, `patch(...httpx.get, side_effect=_capturing_get)`, patrón
de `test_sudespacho_relations.py`). `fetch_expediente_datos` y
`recompute_coincidencias` NO cambian.

Casos:
- Texto libre → OR-like; el `filterGroup` enviado lleva `condition=OR` y un
  `like` por `referencia_cliente` y `referencia_procurador` (capturar params).
- Match por `referencia_procurador` (`"3447"`) → devuelve el expediente; label
  incluye `· P-2025/3447`.
- `"63/2024"` → rama num+serie: `equal num_expediente=63` + serie `2024`;
  no confundir con `"2025/7449"` (que NO dispara num+serie y va a texto).
- Fusión/dedup: un id que aparece por texto y por num+serie sale una sola vez.
- Alias `expedientes_extrajudiciales` → normaliza a `extrajudiciales`, OR-like
  solo sobre `Referencia_Cliente` (sin `referencia_procurador`).
- Término vacío / solo espacios → `[]` sin tocar red.
- Sin `SUDESPACHO_API_KEY` → `[]` (no lanza).
- CRM HTTP != 200 / red caída → `[]` (degrada, no rompe la tarjeta).
- `client` legacy pasado → ignorado (no se usa; búsqueda REST igualmente).

Suite completa verde (`python -m pytest -q`).

## Fuera de alcance (documentar, no implementar)

- **`DEAD_ENDS.md`:** (a) `num_asunto` vacío en todo el tenant → búsqueda por
  autos inútil hoy; (b) contrario→expedientes sin ruta REST inversa (405),
  `clientes_contrarios` listable por `nombre` pero sin puente al expediente.
- **`MEJORAS_FUTURAS.md`:** búsqueda por contrario (requeriría frontal legacy o
  endpoint inverso inexistente); búsqueda por autos cuando `num_asunto` se pueble.

## Riesgos / gotchas

- Encoding UTF-8 sin BOM en todos los artefactos (CLAUDE.md).
- El combobox ya no depende de PHPSESSID (usa x-api-key) → desaparece el gotcha
  de caducidad de sesión que el spec de UI señalaba para el combobox.
- `_rest_search_expedientes` (dedup) NO debe alterarse: sus tests
  (`test_sudespacho_relations.py`, `test_dedup_*`) deben seguir verdes tras el
  refactor del helper HTTP común.
- La UI de F2 aún no consume `search_expedientes` (no hay caller en
  `streamlit_app.py`) → cambiar la firma/semántica es de bajo riesgo.
```
