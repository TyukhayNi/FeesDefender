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
from .sync_sudespacho import SudespachoClient

logger = logging.getLogger("feesdefender.procurador_search")

# Elementos CRM buscables desde el combobox (🔴 ofrece los tres).
ELEMENTOS_BUSCABLES = ("expedientes_judiciales", "expedientes_extrajudiciales", "clientes")

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


# ---------------------------------------------------------------------------
# Stubs para Tasks 3-4 — se implementarán en esas entregas.
# Declarados aquí para que el módulo importe completo desde el primer commit
# y los tests de Tasks 3-4 puedan importarlos.
# ---------------------------------------------------------------------------

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
