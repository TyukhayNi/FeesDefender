"""El puerto de las fuentes externas de `verificar_apertura`, y su adaptador real.

`core/verificar_apertura.py` **no importa red**: recibe un objeto que cumple `Fuentes` y
pregunta. Esto existe por H-07 de una ronda anterior: unos tests sustituían
`case_locator.buscar`, así que **probaban el doble y no la integración**, y una forma de
invocación que la ayuda anunciaba llevaba tiempo sin funcionar.

## `None` no es «no hay»

Todo método devuelve `None` cuando **no se pudo consultar**, y la comprobación lo traduce
a `fallo`. Una lista vacía es un dato: se consultó y no había nada. Mantener esa
distinción **hasta el final** costó un hallazgo (H-10): el adaptador atrapaba el error
de la consulta de relaciones y devolvía un expediente con `relaciones={}`, de modo que
el informe atribuía al expediente una ausencia que nadie había observado.

## Lo que se midió antes de escribir esto, en vez de suponerlo

- La propiedad de la **cuantía** se llama `cuantia` en los dos elementos (atlas del CRM).
  Llega como **cadena**, medido sobre un expediente real.
- **`actuaciones` es hijo** de `extrajudiciales` y `expedientes_judiciales`, así que
  aparece en `related_register` y se lee **por el lado del expediente** — lo que
  `MEJORAS #209` exige. Confirmado contra el CRM real.
- `element_registries/extrajudiciales` responde con **`items`**, no `hydra:member`. La
  documentación se contradice; se aceptan las dos formas, que es lo único que no depende
  de cuál tenga razón.
"""
from __future__ import annotations

import dataclasses
import os
from typing import Any, Protocol, runtime_checkable


@dataclasses.dataclass(frozen=True)
class FicheroRemoto:
    """Un fichero tal como lo declara el remoto.

    `file_id` distingue **dos objetos con el mismo nombre**, que en Drive es posible y
    que la primera versión fundía en uno: con un `set` de rutas, dos objetos remotos
    homónimos —uno de ellos con checksum distinto— se contaban como uno y el expediente
    salía en verde (H-01).
    """
    ruta: str
    sha256: str = ""
    file_id: str = ""


@dataclasses.dataclass(frozen=True)
class CensoRemoto:
    """El censo, con su declaración de completitud.

    `completo=False` significa que el servicio **dijo** que la enumeración se quedó
    corta (`incompleteSearch` de la Drive API). Sin este campo, un censo truncado se leía
    como «el remoto tiene menos ficheros», y un expediente al que le faltaba media
    carpeta salía en verde (H-14).
    """
    ficheros: list[FicheroRemoto]
    completo: bool = True


@dataclasses.dataclass(frozen=True)
class ExpedienteCRM:
    """Lo que el CRM dice de un expediente, releído por API.

    `encontrado=False` = se consultó y no está. Distinto de no haber podido consultar,
    que es `None` en el método.
    """
    encontrado: bool
    exp_id: str = ""
    referencia: str | None = None
    #: Cadena tal como la devuelve el CRM. La comparación numérica la hace la
    #: comprobación, que es quien sabe con qué comparar.
    cuantia: str | None = None
    #: `{elemento_hijo: [registro, ...]}`, ya desarrastrado por `get_relaciones`.
    #: `None` = **no se pudieron leer**, que no es lo mismo que no tener ninguna.
    relaciones: dict[str, list[dict[str, Any]]] | None = None

    #: Bloques de `related_register` que son PARTES del expediente. `actuaciones` no lo
    #: es —es trabajo, no parte— y contarla como tal hacía que un expediente sin ninguna
    #: parte vinculada pasara la comprobación de ficha (H-07).
    NO_SON_PARTES = frozenset({"actuaciones", "gdocu", "mail", "calendario",
                               "seguimientos", "conceptos_honorario"})

    @property
    def actuaciones(self) -> list[dict[str, Any]] | None:
        if self.relaciones is None:
            return None
        return list(self.relaciones.get("actuaciones") or [])

    @property
    def partes(self) -> dict[str, int] | None:
        if self.relaciones is None:
            return None
        return {k: len(v) for k, v in sorted(self.relaciones.items())
                if v and k not in self.NO_SON_PARTES}


@runtime_checkable
class Fuentes(Protocol):
    """Lo que `verificar_apertura` necesita del mundo exterior, y nada más."""

    def censo_drive(self, team_id: str, folder_id: str) -> CensoRemoto | None:
        """El censo del remoto de E&V, o `None` si no se pudo consultar."""

    def expediente_crm(self, exp_id: str, element: str) -> ExpedienteCRM | None:
        """Lo que el CRM dice del expediente, o `None` si no se pudo consultar."""


class SinRed:
    """El puerto cerrado: todo devuelve `None`.

    Es el **default** de `verificar()`, y por eso las comprobaciones de red salen en
    `fallo` con «no se pudo consultar» en vez de en verde. Un verificador cuyo modo por
    defecto fuera «no preguntar y aprobar» sería peor que no tenerlo.
    """

    def censo_drive(self, team_id: str, folder_id: str) -> CensoRemoto | None:
        return None

    def expediente_crm(self, exp_id: str, element: str) -> ExpedienteCRM | None:
        return None


class DeLaRed:
    """El adaptador real. **Traduce, no decide.**"""

    def __init__(self, *, transporte: Any = None) -> None:
        #: Inyectable para poder ejercer la TRADUCCIÓN en un test sin salir a la red.
        #: Sin esto, los dobles del puerto dejaban el adaptador entero sin recorrer, y
        #: tres mutantes del cableado sobrevivían (H-11).
        self._t = transporte

    # -- Drive ---------------------------------------------------------------------

    def censo_drive(self, team_id: str, folder_id: str) -> CensoRemoto | None:
        """Censo recursivo con el `sha256Checksum` que Drive publica.

        Se usa la **Drive API** y no `rclone lsf` porque el hash es la mitad de lo que
        hace falta (`MEJORAS #225`, el pull que rellenaba con ceros) y `rclone` no lo
        publica por esa vía. Una consulta da censo Y hash.
        """
        if not folder_id:
            return None
        get = self._get_drive()
        if get is None:
            return None

        ficheros: list[FicheroRemoto] = []
        completo = True
        pendientes = [(folder_id, "")]
        try:
            while pendientes:
                actual, prefijo = pendientes.pop()
                pagina = None
                while True:
                    params = {
                        "q": f"'{actual}' in parents and trashed=false",
                        # `incompleteSearch` se pide EXPRESAMENTE: sin él, una
                        # enumeración que el servicio declara incompleta se leía como
                        # «el remoto tiene menos ficheros» (H-14).
                        "fields": ("nextPageToken,incompleteSearch,"
                                   "files(id,name,mimeType,sha256Checksum)"),
                        "pageSize": "1000", "supportsAllDrives": "true",
                        "includeItemsFromAllDrives": "true",
                    }
                    if pagina:
                        params["pageToken"] = pagina
                    data = get("https://www.googleapis.com/drive/v3/files", params)
                    if data is None or not isinstance(data.get("files"), list):
                        return None
                    if data.get("incompleteSearch"):
                        completo = False
                    for f in data["files"]:
                        rel = f"{prefijo}{f.get('name') or ''}"
                        if f.get("mimeType") == "application/vnd.google-apps.folder":
                            pendientes.append((f.get("id"), f"{rel}/"))
                        else:
                            ficheros.append(FicheroRemoto(
                                ruta=rel, sha256=f.get("sha256Checksum") or "",
                                file_id=str(f.get("id") or "")))
                    pagina = data.get("nextPageToken")
                    if not pagina:
                        break
        except Exception:                                  # noqa: BLE001
            return None
        return CensoRemoto(ficheros=ficheros, completo=completo)

    def _get_drive(self):
        if self._t is not None:
            return self._t
        from core import intake_drive

        token = intake_drive._get_drive_access_token()
        if not token:
            return None
        try:
            import httpx
        except ImportError:                                # pragma: no cover
            return None

        def get(url, params):
            r = httpx.get(url, params=params, timeout=60,
                          headers={"Authorization": f"Bearer {token}"})
            return r.json() if r.status_code == 200 else None

        return get

    # -- CRM -----------------------------------------------------------------------

    def expediente_crm(self, exp_id: str, element: str) -> ExpedienteCRM | None:
        from core import sudespacho_relations as sr

        elem = sr._normalize_element(element)
        if elem is None:
            return None
        prop_ref = sr._REFERENCIA_PROP_BY_ELEMENT.get(elem)
        if prop_ref is None:
            return None
        data = self._get_crm(sr, elem, prop_ref, exp_id)
        if data is None:
            return None

        # Las DOS formas: la documentación se contradice sobre cuál usa este endpoint.
        items = data.get("items") or data.get("hydra:member") or []
        if not items:
            return ExpedienteCRM(encontrado=False, exp_id=str(exp_id))
        # El id se comprueba en vez de confiarlo al servidor: pedir por filtro y leer
        # `items[0]` da por supuesto que el filtro se aplicó (H-07).
        elegido = next((i for i in items if str(i.get("id")) == str(exp_id)), None)
        if elegido is None:
            return None
        valores = {(v.get("property") or {}).get("name"): v.get("value")
                   for v in (elegido.get("values") or [])}
        try:
            relaciones = sr.get_relaciones(elem, str(exp_id))
        except Exception:                                  # noqa: BLE001
            # `None`, no `{}`: el lector lanza precisamente para conservar la
            # distinción entre «no se pudo leer» y «no hay vínculos», y aplanarla aquí
            # hacía que el informe atribuyera al expediente una ausencia que nadie
            # había observado (H-10).
            relaciones = None
        return ExpedienteCRM(
            encontrado=True, exp_id=str(exp_id),
            referencia=valores.get(prop_ref), cuantia=valores.get("cuantia"),
            relaciones=relaciones)

    def _get_crm(self, sr, elem: str, prop_ref: str, exp_id: str):
        params = [("properties[0]", prop_ref), ("properties[1]", "cuantia"),
                  ("filterGroup[condition]", "AND"),
                  ("filterGroup[filterGroups][0][condition]", "AND"),
                  ("filterGroup[filterGroups][0][filters][0][operator]", "equal"),
                  ("filterGroup[filterGroups][0][filters][0][value]", str(exp_id)),
                  ("filterGroup[filterGroups][0][filters][0][property]", "id"),
                  ("itemsPerPage", "5"), ("return_totals", "true")]
        url = f"{sr._REST_BASE}/api/element_registries/{elem}"
        if self._t is not None:
            return self._t(url, dict(params))
        api_key = (os.getenv("SUDESPACHO_API_KEY") or "").strip()
        if not api_key:
            return None
        try:
            import httpx

            r = httpx.get(url, params=params, timeout=sr._REST_TIMEOUT,
                          headers={"x-api-key": api_key, "Accept": "application/json"})
            return r.json() if r.status_code == 200 else None
        except Exception:                                  # noqa: BLE001
            return None
