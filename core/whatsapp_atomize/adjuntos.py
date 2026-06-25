"""Liga las referencias de adjunto del chat a los bytes presentes, dedup por sha256."""
from __future__ import annotations

import hashlib

from core.email_atomize.model import AdjuntoUnico

_MARCADORES_AUSENTE = {"<Media omitted>", "<archivo adjunto>"}


def construir_adjuntos(refs, media: dict[str, bytes], registro):
    """Devuelve (list[AdjuntoUnico] dedup por sha, dict ref→{att_id|None, ausente}).

    refs: lista de nombres referenciados en el chat (en orden de aparición).
    media: {nombre_fichero: bytes} presentes en el export.
    """
    por_sha: dict[str, AdjuntoUnico] = {}
    por_ref: dict[str, dict] = {}
    for ref in refs:
        if ref in por_ref:
            continue
        data = media.get(ref)
        if data is None or ref in _MARCADORES_AUSENTE:
            por_ref[ref] = {"att_id": None, "ausente": True}
            continue
        sha = hashlib.sha256(data).hexdigest()
        att_id = registro.att_id_for(sha)
        unico = por_sha.get(sha)
        if unico is None:
            unico = AdjuntoUnico(att_id=att_id, sha256=sha, nombre_original=ref,
                                 tipo="", data=data)
            por_sha[sha] = unico
        por_ref[ref] = {"att_id": att_id, "ausente": False}
    return list(por_sha.values()), por_ref
