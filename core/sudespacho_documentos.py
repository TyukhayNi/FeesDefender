"""Subir un documento al gestor documental del CRM sudespacho, y acreditarlo.

Contrato completo y medido: `docs/INTEGRACION_SUDESPACHO.md` **§17**. Tres pasos —
`GET /api/files/presigned_upload_url`, `PUT` de los bytes a S3 **sin la clave del
CRM**, y `POST /api/documents`— más un cuarto que el §17 exige y que aquí es parte
del contrato de la función: **bajar lo subido y comparar el `sha256`**.

Vive en la familia `sudespacho_*` y no dentro de `core/expedicion_certificada.py`
aunque el envío certificado sea su primer consumidor (spec §4.1): no es su dueño, y
un cuarto cliente `x-api-key` naciendo dentro del módulo de expediciones es
exactamente cómo se multiplican los clientes huérfanos.

Tres trampas del CRM, las tres medidas, que este módulo evita por construcción:

1. **`POST /api/documents/multiple` devuelve `201` y NO crea nada** (§17.2, probado
   con seis payloads distintos). Se usa el singular, que es lo que usa el front y lo
   único verificado.
2. **El identificador va en `origen_id`, no en `fileIdentifier`** (§17.1). Con la
   clave equivocada el servidor responde `500 Missing mandatory properties`, que no
   dice qué falta; costó seis intentos a ciegas.
3. **El listado filtrado tiene latencia y `related_register` no** (§17.4). Censar por
   el listado fue lo que duplicó un certificado el 2026-09-09, así que
   `buscar_por_origen_id` va por `related_register` y nunca por el listado.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from typing import Any, Callable, Protocol

#: Fachada de ESCRITURA del CRM (§2.1 y §18: escritura y lectura van a hosts
#: distintos, y se puede crear por una y borrar por la otra sin notarlo).
BASE_POR_DEFECTO = "https://api-crm-commons-pro.sudespacho.biz"

#: Raíz del gestor documental (§13.5, confirmada el 2026-05-08). `int`, no `str`:
#: como cadena, el servidor responde `400 The type of the "id_carpeta" attribute
#: must be "int"`.
CARPETA_RAIZ = 1

TIMEOUT = 120


class SudespachoDocumentosError(RuntimeError):
    """Fallo de la subida, de la descarga o de su verificación."""


class ClienteHTTP(Protocol):
    """Superficie mínima de `httpx` que usa este módulo."""

    def request(self, metodo: str, url: str, **kw: Any) -> Any: ...


@dataclass(frozen=True)
class DocumentoSubido:
    """Lo que queda en el CRM, ya verificado por resultado."""

    doc_id: str
    origen_id: str
    nombrefinal: str
    sha256: str


def _base() -> str:
    return (os.getenv("SUDESPACHO_BASE_URL") or BASE_POR_DEFECTO).rstrip("/")


def _api_key() -> str:
    clave = (os.getenv("SUDESPACHO_API_KEY") or "").strip()
    if not clave:
        raise SudespachoDocumentosError(
            "SUDESPACHO_API_KEY vacío — ve a tnm.sudespacho.net → Ajustes → API. No "
            "se intenta ninguna llamada sin ella.")
    return clave


def _cliente_real() -> ClienteHTTP:
    import httpx

    class _C:
        def request(self, metodo: str, url: str, **kw: Any) -> Any:
            return httpx.request(metodo, url, timeout=kw.pop("timeout", TIMEOUT), **kw)

    return _C()


def _json_o_vacio(r: Any) -> Any:
    """El cuerpo como JSON, o `{}` si no parsea — sin mirar `status_code`."""
    try:
        return r.json()
    except ValueError:
        return {}


def _peticion(cliente: ClienteHTTP, metodo: str, url: str, *, que: str,
              esperado: tuple[int, ...], **kw: Any) -> Any:
    """Petición con traducción de fallos y comprobación de status.

    Todo fallo sale como `SudespachoDocumentosError`: el contrato del módulo es que
    no se escapa el tipo crudo de la librería de transporte, igual que hace
    `core/codicert.py::_peticion`. `AssertionError` NO se traduce: es la señal con la
    que los dobles de test marcan un guion mal construido — un fallo del TEST, no del
    transporte, y disfrazarlo de error de dominio ocultaría el defecto real.
    """
    try:
        r = cliente.request(metodo, url, **kw)
    except AssertionError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise SudespachoDocumentosError(
            f"{que}: fallo de transporte ({type(exc).__name__}: {exc})") from exc
    if r.status_code not in esperado:
        raise SudespachoDocumentosError(
            f"{que}: HTTP {r.status_code} (se esperaba {esperado})")
    return r


def _valores(payload: Any) -> dict[str, Any]:
    """Aplana la relectura de un registro, aceptando SUS DOS FORMAS (§17.4-bis).

    `element_register/gdocu/{id}` devuelve una LISTA de `RegisterValue` en la raíz;
    el mismo endpoint sobre un expediente devuelve un `Register` con
    `values.hydra:member`. Un parser escrito contra el segundo revienta con
    `AttributeError: 'list' object has no attribute 'get'` contra el primero — y ya
    costó una excepción a mitad de una subida, con el documento ya creado.
    """
    if isinstance(payload, list):
        crudos = payload
    elif isinstance(payload, dict):
        crudos = (payload.get("values") or {}).get("hydra:member") or []
    else:
        crudos = []
    return {(v.get("property") or {}).get("name", ""): v.get("value")
            for v in crudos if isinstance(v, dict)}


def subir_documento(contenido: bytes, *, nombrefinal: str, mime: str, related: str,
                    id_carpeta: int = CARPETA_RAIZ, nombreoriginal: str | None = None,
                    cliente: ClienteHTTP | None = None,
                    al_reservar: Callable[[str], None] | None = None) -> DocumentoSubido:
    """Sube `contenido` al gestor y **acredita que llegó bien bajándolo otra vez**.

    `related` es la gramática del §17.3 para relacionar AL CREAR:
    `"<elemento>:<id>:left"` — con el lado DETRÁS, incompatible con la del endpoint
    de relaciones, que lo pone delante. No se deduce una de otra.

    `al_reservar` recibe el `origen_id` **antes** del `POST` que crea el documento.
    Es el gancho de idempotencia y su momento no es negociable: si el `POST` sale y
    su respuesta se pierde (timeout), el documento queda creado y el `origen_id` es
    lo ÚNICO que permite reencontrarlo por clave de contenido (§17.4), porque el
    `doc_id` viajaba en la respuesta que no llegó. Anotarlo después no cubre nada.
    """
    clave = _api_key()
    cliente = cliente or _cliente_real()
    base = _base()
    cabeceras = {"x-api-key": clave, "Accept": "application/json"}

    # Paso 1 — la URL prefirmada. Caduca a los 600 s: se pide justo antes de subir.
    r1 = _peticion(cliente, "GET", f"{base}/api/files/presigned_upload_url",
                   que="presigned_upload_url", esperado=(200,), headers=cabeceras)
    datos = _json_o_vacio(r1)
    if not isinstance(datos, dict):
        raise SudespachoDocumentosError(
            f"presigned_upload_url: cuerpo no es un objeto — {datos!r}")
    origen_id, url_s3 = datos.get("fileIdentifier"), datos.get("url")
    if not origen_id or not url_s3:
        raise SudespachoDocumentosError(
            f"presigned_upload_url sin fileIdentifier/url — claves {sorted(datos)}")

    # Paso 2 — los bytes a S3, SIN la cabecera de auth del CRM (§17.1).
    _peticion(cliente, "PUT", str(url_s3), que="PUT a S3", esperado=(200, 201, 204),
              content=contenido, headers={"Content-Type": mime})

    # El gancho va aquí: con los bytes ya en S3 y ANTES de crear el registro.
    if al_reservar is not None:
        al_reservar(str(origen_id))

    # Paso 3 — el registro en el CRM. El SINGULAR (§17.2).
    cuerpo = {
        "origen": "fuploaders3",
        "origen_id": str(origen_id),
        "nombreoriginal": nombreoriginal or nombrefinal,
        "nombrefinal": nombrefinal,
        "mime": mime,
        "tamano": len(contenido),
        "id_carpeta": int(id_carpeta),
        "estado": "-1", "categoria": "-1", "tipo": "-1",
        "relatedRegisters": [related],
    }
    r3 = _peticion(cliente, "POST", f"{base}/api/documents", que="POST /api/documents",
                   esperado=(200, 201),
                   headers={**cabeceras, "Content-Type": "application/json"},
                   json=cuerpo)
    creado = _json_o_vacio(r3)
    doc_id = str(creado.get("id") or "") if isinstance(creado, dict) else ""
    if not doc_id:
        raise SudespachoDocumentosError(
            "POST /api/documents respondió sin `id`: el documento PUDO HABER QUEDADO "
            f"CREADO. Búscalo por su origen_id {str(origen_id)!r} antes de "
            "reintentar; no relances la subida a ciegas, que es como se duplica "
            "(§17.4).")

    # Paso 4 — la verificación por resultado. El `201` no acredita el binario.
    sha_local = hashlib.sha256(contenido).hexdigest()
    sha_remoto = hashlib.sha256(descargar_documento(doc_id, cliente=cliente)).hexdigest()
    if sha_remoto != sha_local:
        raise SudespachoDocumentosError(
            f"el documento {doc_id} se creó pero sus bytes NO coinciden: sha256 local "
            f"{sha_local[:16]}… contra remoto {sha_remoto[:16]}…. El documento EXISTE "
            "en el CRM: revísalo a mano, no vuelvas a subirlo.")
    return DocumentoSubido(doc_id=doc_id, origen_id=str(origen_id),
                           nombrefinal=nombrefinal, sha256=sha_local)


def descargar_documento(doc_id: str, *, cliente: ClienteHTTP | None = None) -> bytes:
    """Los bytes de un documento del gestor, por `downloadUri` (§16.7).

    ⚠️ **No por `/api/files/presigned_download_url/{doc_id}` ni por
    `/api/documents/presigned_urls/s3/download/{id}`**: el CRM los rompió en mayo de
    2026 y `DEAD_ENDS.md` los da por muertos.
    """
    clave = _api_key()
    cliente = cliente or _cliente_real()
    r = _peticion(cliente, "GET", f"{_base()}/api/documents/{doc_id}/downloadUri",
                  que=f"downloadUri de {doc_id}", esperado=(200,),
                  headers={"x-api-key": clave, "Accept": "application/json"})
    cuerpo = _json_o_vacio(r)
    url = None
    if isinstance(cuerpo, dict):
        url = (cuerpo.get("presignedDownloadUrl") or cuerpo.get("url")
               or (cuerpo.get("doc") or {}).get("url"))
    if not url:
        raise SudespachoDocumentosError(
            f"downloadUri de {doc_id} no trae URL de descarga — {cuerpo!r}")
    return _peticion(cliente, "GET", str(url), que=f"descarga de {doc_id}",
                     esperado=(200,)).content


def buscar_por_origen_id(origen_id: str, *, element: str, exp_id: str,
                         cliente: ClienteHTTP | None = None) -> str | None:
    """El `doc_id` del documento con ese `origen_id`, o `None`. **Sin latencia.**

    Va por `GET /api/related_register/{element}/{id}`, que responde inmediatamente, y
    **nunca por el listado filtrado**, cuya latencia hizo que una guarda anti-duplicado
    dijera «aún no está» sobre algo que ya estaba y lo subiera dos veces (§17.4).

    ⚠️ **`related_register` arrastra fantasmas**: sigue listando documentos ya
    borrados. Para una guarda anti-duplicado eso cae del lado seguro —un fantasma
    produce «ya existe» y NO se sube— y el precio es no re-subir algo que se borró a
    propósito. Se prefiere así: el error caro es el duplicado.
    """
    clave = _api_key()
    cliente = cliente or _cliente_real()
    base = _base()
    cabeceras = {"x-api-key": clave, "Accept": "application/json"}
    r = _peticion(cliente, "GET", f"{base}/api/related_register/{element}/{exp_id}",
                  que=f"related_register de {element}/{exp_id}", esperado=(200,),
                  headers=cabeceras)
    bloques = _json_o_vacio(r)
    docs = bloques.get("gdocu") or [] if isinstance(bloques, dict) else []
    for documento in docs:
        doc_id = str((documento or {}).get("id") or "")
        if not doc_id:
            continue
        rr = _peticion(cliente, "GET", f"{base}/api/element_register/gdocu/{doc_id}",
                       que=f"relectura de gdocu/{doc_id}", esperado=(200,),
                       headers=cabeceras,
                       params={"properties": "origen,origen_id"})
        if _valores(_json_o_vacio(rr)).get("origen_id") == origen_id:
            return doc_id
    return None
