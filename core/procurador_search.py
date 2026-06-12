"""F2 — Búsqueda y lectura del CRM para la bandeja de procuradores (combobox §18.6).

Lógica de core que la pestaña Streamlit «Bandeja de correos» orquesta para
reasignar el expediente de un correo 🟡/🔴 y refrescar los checks verdes 🟢.

Dos vías de lectura (ambas REST x-api-key, inyectables vía mock de ``httpx``):
el **combobox** busca con ``_rest_search_por_texto`` / ``_rest_search_num_serie``
(``sudespacho_relations``); la lectura de campos por id usa ``SudespachoClient``.
Solo lectura: NO escribe en el CRM (la escritura es F3).
"""

from __future__ import annotations

import logging
import re
from typing import Any

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

logger = logging.getLogger("feesdefender.procurador_search")

# Elementos CRM buscables desde el combobox. `clientes` se retiró (2026-06-12):
# no tiene property de referencia ni alimenta recompute_coincidencias.
ELEMENTOS_BUSCABLES = ("expedientes_judiciales", "expedientes_extrajudiciales")
# Nota: la forma larga de aquí se normaliza al slug canónico (extrajudiciales)
# vía _normalize_element dentro de search_expedientes; el combobox puede pasar
# directamente cualquier valor de esta tupla.

# Nº interno del despacho citado por procuradores: "63/2024" (num/AÑO). El año
# (19xx/20xx) va DETRÁS, lo que lo distingue de refs de procurador "AÑO/nº"
# (p. ej. "2025/7449"), que van a la búsqueda por texto.
_NUM_SERIE_RE = re.compile(r"^\s*(\d{1,4})\s*/\s*((?:19|20)\d{2})\s*$")

# Campos de IntakeSignals que `_check_signal_matches` compara (reconstrucción).
_SIGNAL_KEYS = (
    "su_ref", "num_expediente", "serie_expediente", "contrario", "cliente",
    "juzgado", "num_asunto", "tipo_procedimiento", "tipo_actuacion",
    "fecha_actuacion",
)


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
            try:
                client.__exit__(None, None, None)
            except Exception:
                pass


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
