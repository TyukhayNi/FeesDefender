"""El puerto de las fuentes externas de `verificar_apertura`, y su adaptador real.

`core/verificar_apertura.py` **no importa red**: recibe un objeto que cumple `Fuentes` y
pregunta. Esto existe por un hallazgo concreto de la R1 de la primera tanda (H-07): sus
tests del CLI sustituían `case_locator.buscar`, así que **probaban el doble y no la
integración**, y una forma de invocación que la ayuda anunciaba llevaba tiempo sin
funcionar sin que ningún verde lo dijera.

## Cómo se evita repetirlo, dicho sin adornos

No se evita del todo, y conviene que esté escrito:

1. **El puerto es estrecho y el adaptador es tonto.** `DeLaRed` no decide nada: traduce
   una llamada a los módulos que ya existen y normaliza la forma. Lo que se prueba con
   dobles es la **lógica de la comprobación**; lo que queda sin probar es una traducción.
2. **Hay un test de contrato** que compara la firma del adaptador contra el protocolo.
   No prueba la red: prueba que el cableado existe y no se ha desfasado.
3. **Lo demás queda SIN VERIFICAR y se declara.** Que el CRM siga respondiendo con esta
   forma, o que `rclone` siga aceptando estos flags, solo lo acredita una corrida real.

## `None` no es «no hay»

Todo método devuelve `None` cuando **no se pudo consultar** (sin token, sin red, sin
`rclone`). La comprobación lo traduce a `fallo`, nunca a `ok`: es la regla que salió de
la R1 —*no poder mirar no es «no hay nada que ver»*— y aquí es donde entra al sistema.
Una lista vacía, en cambio, es un dato: se consultó y no había nada.

## Lo que se midió antes de escribir esto, en vez de suponerlo

- La propiedad de la **cuantía** se llama `cuantia` en los dos elementos, judicial y
  extrajudicial (`docs/CRM_SUDESPACHO_ATLAS.md`, campos por elemento). Llega como
  **cadena**, no como número — medido el 2026-09-11 sobre un expediente real.
- **`actuaciones` es hijo** de `extrajudiciales` y de `expedientes_judiciales` (atlas,
  bloque `actuaciones` · Relaciones · parent), así que aparece en `related_register` y
  **se lee por el lado del expediente**, que es lo que `MEJORAS #209` exige: preguntar
  al elemento «actuaciones» por las suyas no acredita que estén asociadas a ESTE
  expediente.
- La respuesta de `element_registries/extrajudiciales` llega con **`items`**, no con
  `hydra:member` — medido el mismo día. La documentación se contradice en sus §15.6 y
  §2110 contra su propia recomendación de aceptar las dos formas; aquí se aceptan las
  dos, que es lo único que no depende de cuál tenga razón.
"""
from __future__ import annotations

import dataclasses
import os
import subprocess
from typing import Any, Protocol, runtime_checkable


@dataclasses.dataclass(frozen=True)
class FicheroRemoto:
    """Un fichero tal como lo declara el remoto. `sha256` vacío = el remoto no lo da."""
    ruta: str
    sha256: str = ""


@dataclasses.dataclass(frozen=True)
class ExpedienteCRM:
    """Lo que el CRM dice de un expediente, releído por API.

    `encontrado=False` significa que se consultó y el expediente no está — que es un
    dato, y distinto de no haber podido consultar (eso es `None` en el método).
    """
    encontrado: bool
    referencia: str | None = None
    #: Cadena tal como la devuelve el CRM. La comparación numérica la hace la
    #: comprobación, que es quien sabe con qué comparar.
    cuantia: str | None = None
    #: `{elemento_hijo: [registro, ...]}`, ya desarrastrado por `get_relaciones`.
    relaciones: dict[str, list[dict[str, Any]]] = dataclasses.field(default_factory=dict)

    @property
    def actuaciones(self) -> list[dict[str, Any]]:
        """Las del bloque `actuaciones` de las relaciones — por el lado del expediente."""
        return list(self.relaciones.get("actuaciones") or [])


@runtime_checkable
class Fuentes(Protocol):
    """Lo que `verificar_apertura` necesita del mundo exterior, y nada más."""

    def censo_drive(self, team_id: str, folder_id: str) -> list[FicheroRemoto] | None:
        """Los ficheros que el remoto de E&V declara, o `None` si no se pudo consultar."""

    def expediente_crm(self, exp_id: str, element: str) -> ExpedienteCRM | None:
        """Lo que el CRM dice del expediente, o `None` si no se pudo consultar."""


class SinRed:
    """El puerto cerrado: todo devuelve `None`.

    Es el **default** de `verificar()`, y por eso las cinco comprobaciones de red salen
    en `fallo` con «no se pudo consultar» en vez de en verde. Un verificador cuyo modo
    por defecto sea «no preguntar y aprobar» es peor que no tenerlo.
    """

    def censo_drive(self, team_id: str, folder_id: str) -> list[FicheroRemoto] | None:
        return None

    def expediente_crm(self, exp_id: str, element: str) -> ExpedienteCRM | None:
        return None


class DeLaRed:
    """El adaptador real. **Traduce, no decide.**

    Cada método hace una llamada a un módulo que ya existe, normaliza su forma y
    devuelve `None` ante cualquier problema.
    """

    def censo_drive(self, team_id: str, folder_id: str) -> list[FicheroRemoto] | None:
        """Los ficheros del remoto, con su `sha256Checksum` cuando Drive lo publica.

        Se usa la **Drive API** y no `rclone lsf`, por una razón medida: el hash es la
        mitad de lo que hace falta (`MEJORAS #225`, el pull que rellenaba con ceros) y
        `rclone` no lo publica por esta vía. Una sola consulta da el censo Y el hash, y
        dos consultas distintas darían dos fotos de momentos distintos.
        """
        from core import intake_drive

        if not folder_id:
            return None
        token = intake_drive._get_drive_access_token()
        if not token:
            return None
        try:
            import httpx
        except ImportError:                                # pragma: no cover
            return None

        salida: list[FicheroRemoto] = []
        pendientes = [(folder_id, "")]
        pagina_token = None
        try:
            while pendientes:
                actual, prefijo = pendientes.pop()
                while True:
                    params = {
                        "q": f"'{actual}' in parents and trashed=false",
                        "fields": "nextPageToken,files(id,name,mimeType,sha256Checksum)",
                        "pageSize": "1000", "supportsAllDrives": "true",
                        "includeItemsFromAllDrives": "true",
                    }
                    if pagina_token:
                        params["pageToken"] = pagina_token
                    r = httpx.get("https://www.googleapis.com/drive/v3/files",
                                  params=params, timeout=60,
                                  headers={"Authorization": f"Bearer {token}"})
                    if r.status_code != 200:
                        return None
                    data = r.json()
                    for f in data.get("files", []):
                        nombre = f.get("name") or ""
                        rel = f"{prefijo}{nombre}"
                        if f.get("mimeType") == "application/vnd.google-apps.folder":
                            pendientes.append((f.get("id"), f"{rel}/"))
                        else:
                            salida.append(FicheroRemoto(
                                ruta=rel, sha256=f.get("sha256Checksum") or ""))
                    pagina_token = data.get("nextPageToken")
                    if not pagina_token:
                        break
        except Exception:                                  # noqa: BLE001
            return None
        return salida

    def expediente_crm(self, exp_id: str, element: str) -> ExpedienteCRM | None:
        """Referencia y cuantía por `element_registries`, relaciones por `related_register`."""
        from core import sudespacho_relations as sr

        elem = sr._normalize_element(element)
        if elem is None:
            return None
        prop_ref = sr._REFERENCIA_PROP_BY_ELEMENT.get(elem)
        if prop_ref is None:
            return None
        api_key = (os.getenv("SUDESPACHO_API_KEY") or "").strip()
        if not api_key:
            return None
        try:
            import httpx
        except ImportError:                                # pragma: no cover
            return None

        params = [("properties[0]", prop_ref), ("properties[1]", "cuantia"),
                  ("filterGroup[condition]", "AND"),
                  ("filterGroup[filterGroups][0][condition]", "AND"),
                  ("filterGroup[filterGroups][0][filters][0][operator]", "equal"),
                  ("filterGroup[filterGroups][0][filters][0][value]", str(exp_id)),
                  ("filterGroup[filterGroups][0][filters][0][property]", "id"),
                  ("itemsPerPage", "5"), ("return_totals", "true")]
        try:
            r = httpx.get(f"{sr._REST_BASE}/api/element_registries/{elem}",
                          params=params, timeout=sr._REST_TIMEOUT,
                          headers={"x-api-key": api_key, "Accept": "application/json"})
            if r.status_code != 200:
                return None
            data = r.json()
        except Exception:                                  # noqa: BLE001
            return None

        # Las DOS formas: la documentación se contradice sobre cuál usa este endpoint, y
        # aceptar ambas es lo único que no depende de cuál tenga razón.
        items = data.get("items") or data.get("hydra:member") or []
        if not items:
            return ExpedienteCRM(encontrado=False)
        valores = {(v.get("property") or {}).get("name"): v.get("value")
                   for v in (items[0].get("values") or [])}
        try:
            relaciones = sr.get_relaciones(elem, str(exp_id))
        except Exception:                                  # noqa: BLE001
            relaciones = {}
        return ExpedienteCRM(
            encontrado=True,
            referencia=valores.get(prop_ref),
            cuantia=valores.get("cuantia"),
            relaciones=relaciones or {})
