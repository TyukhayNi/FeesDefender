"""Dataclasses del motor de atomización (sin lógica; solo estructura compartida).

Todos los campos llevan default para poder construir los registros incrementalmente y
evitar problemas de orden; el pipeline los rellena por palabra clave.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AdjuntoRef:
    """Referencia a un adjunto desde un mensaje (va en el frontmatter del ``.md``)."""

    att_id: str | None = None          # "ATT-00007" si es adjunto indexado
    msg_id_anidado: str | None = None  # MSG-id si la parte es message/rfc822 (Fase 2 lo enlaza)
    nombre: str = ""
    tipo: str = ""                     # mime
    sha256: str = ""


@dataclass
class AdjuntoUnico:
    """Un adjunto único (deduplicado por sha256) con su catálogo de apariciones."""

    att_id: str = ""
    sha256: str = ""
    nombre_original: str = ""
    tipo: str = ""
    data: bytes = b""
    primera_aparicion: str = ""        # fecha ISO del primer mensaje que lo trae
    mensajes: list[str] = field(default_factory=list)  # MSG-ids que lo referencian
    etiquetas: list[str] = field(default_factory=list)


@dataclass
class RegistroMensaje:
    """Un mensaje atómico final, listo para render/corpus."""

    msg_id: str = ""                   # "MSG-00001"
    rfc_message_id: str = ""           # Message-ID RFC (puede ser "")
    in_reply_to: str = ""
    hilo: str = ""
    fecha_iso: str = "0000-00-00"
    hora: str = ""                     # "HHMM" Europe/Madrid ("" si no consta)
    fecha_tz: str = ""                 # ISO completo con tz, o ""
    de: str = ""
    de_nombre: str = ""
    para: list[str] = field(default_factory=list)
    cc: list[str] = field(default_factory=list)
    cco: list[str] = field(default_factory=list)
    asunto: str = ""
    eml_origen: str = ""
    profundidad: int = 0
    ruta_anidacion: list[str] = field(default_factory=list)
    procedencia: list[dict] = field(default_factory=list)
    capa: str = "A"
    confianza: str = "alta"
    auth: dict = field(default_factory=dict)
    sha256: str = ""                   # sha256 del .eml verbatim de este mensaje
    adjuntos: list[AdjuntoRef] = field(default_factory=list)
    idioma: str = ""
    formato_original: str = ""         # "plain" | "html" | "plain+html"
    emisor_dispositivo: str = ""
    etiquetas: list[str] = field(default_factory=list)
    fuente: str = "email"
    cuerpo: str = ""                   # texto limpio (solo lo que escribió el autor)
    # flags de cuerpo (al frontmatter solo si True)
    cuerpo_recortado_cita: bool = False
    respuesta_intercalada: bool = False
    charset_recuperado: bool = False
    mojibake_marcado: bool = False
    raw: bytes = b""                   # bytes verbatim del mensaje (para sha y verbatim)
