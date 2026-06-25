"""Dataclasses del motor de atomización de WhatsApp (solo estructura)."""
from __future__ import annotations

from dataclasses import dataclass

from core.email_atomize.model import AdjuntoRef  # reuso transversal


@dataclass
class RegistroMensajeWA:
    """Un mensaje del chat, ya atomizado y numerado."""

    msg_id: str = ""                 # "MSG-00042" (congelado por _registro.json)
    fingerprint: str = ""            # hash estable de timestamp+autor+texto
    chat_id: str = ""                # carpeta del chat de origen
    fecha_iso: str = "0000-00-00"
    hora: str = ""                   # "HHMM" local (WhatsApp no exporta tz)
    autor_export: str = ""           # lo que trae el chat (nombre de contacto o número)
    persona_id: str = ""             # resuelto vía identidades (o "")
    rol: str = ""                    # propietario | buscador | E&V | tercero | ""
    de_confianza: str = ""           # "" si autor crudo; "identidades" si resuelto
    texto: str = ""                  # verbatim del mensaje
    es_sistema: bool = False
    es_reenviado: bool = False
    adjunto: AdjuntoRef | None = None
    contiene_enterrado: bool = False
    en_revision: bool = False
    responde_a: str = ""             # MSG-id ligado por quote, o ""


@dataclass
class AtomEnterrado:
    """Unidad reconstruida (email/mensaje pegado) promovida a .md propio."""

    enterrado_id: str = ""           # "ENT-00001"
    portador_msg_id: str = ""        # de qué mensaje del chat salió
    de: str = ""
    de_nombre: str = ""
    fecha_iso: str = "0000-00-00"
    extracto: str = ""
    confianza: str = "media"
    en_revision: bool = True


@dataclass
class SegmentoEnterradoWA:
    """Fila de la cola de revisión: candidato detectado pero NO promovido."""

    portador_msg_id: str = ""
    motivo: str = ""                 # sin_cabecera | ambiguo | quote_no_ligado
    extracto: str = ""
    confianza: str = ""
