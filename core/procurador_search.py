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


# ---------------------------------------------------------------------------
# Stubs para Tasks 3-4 — se implementarán en esas entregas.
# Declarados aquí para que el módulo importe completo desde el primer commit
# y los tests de Tasks 3-4 puedan importarlos.
# ---------------------------------------------------------------------------

def fetch_expediente_datos(
    expediente_id: str,
    *,
    client: Any = None,
) -> dict[str, Any]:
    """Stub — lee campos del expediente por id desde la API REST del CRM."""
    raise NotImplementedError("fetch_expediente_datos se implementa en Task 3")


def recompute_coincidencias(
    signals: IntakeSignals,
    expediente_datos: dict[str, Any],
) -> dict[str, bool]:
    """Stub — recalcula checks 🟢/🔴 para un expediente elegido manualmente."""
    raise NotImplementedError("recompute_coincidencias se implementa en Task 4")
