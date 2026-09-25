"""Liga las referencias de adjunto del chat a los bytes presentes, dedup por sha256."""
from __future__ import annotations

import hashlib

from core.email_atomize.model import AdjuntoUnico
from core.whatsapp_export import resolver_adjunto

_MARCADORES_AUSENTE = {"<Media omitted>", "<archivo adjunto>"}


def construir_adjuntos(refs, media: dict[str, bytes], registro, crudos=None):
    """Devuelve (list[AdjuntoUnico] dedup por sha, dict ref→{att_id|None, ausente}).

    refs: lista de nombres referenciados en el chat (en orden de aparición), ya limpios.
    media: {nombre_fichero: bytes} presentes en el export.
    crudos: {ref: la referencia tal como la escribe el export}. El nombre en disco se
    resuelve con las dos (`resolver_adjunto`, R1/H-04), y el adjunto se nombra por el
    fichero cuyos bytes se eligieron, no por la referencia.
    """
    crudos = crudos or {}
    por_sha: dict[str, AdjuntoUnico] = {}
    por_ref: dict[str, dict] = {}
    for ref in refs:
        if ref in por_ref:
            continue
        nombre = (None if ref in _MARCADORES_AUSENTE
                  else resolver_adjunto(ref, media, crudos.get(ref)))
        if nombre is None:
            por_ref[ref] = {"att_id": None, "ausente": True}
            continue
        data = media[nombre]
        sha = hashlib.sha256(data).hexdigest()
        att_id = registro.att_id_for(sha)
        unico = por_sha.get(sha)
        if unico is None:
            unico = AdjuntoUnico(att_id=att_id, sha256=sha, nombre_original=nombre,
                                 tipo="", data=data)
            por_sha[sha] = unico
        por_ref[ref] = {"att_id": att_id, "ausente": False}
    return list(por_sha.values()), por_ref
