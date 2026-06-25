"""Reconstrucción de contenido enterrado en mensajes de WhatsApp.

Tres reglas (spec §6): reenviado puro (marcado, sin autor), email/mensaje pegado
(body-scan reutilizado de email_atomize → recupera autor original), quote de reply
(mínimo). Prime directive: nunca afirma un autor que no esté literal en el cuerpo.
"""
from __future__ import annotations

import re

from core.email_atomize.inline import Anclaje, atribucion_en_cuerpo

# Marcador de reenvío de WhatsApp (iOS/Android, ES/EN), tolerante al LRM (U+200E) inicial.
_RE_REENVIADO = re.compile(
    r"(?im)^\s*‎?(?:reenviado(?:\s+muchas\s+veces)?|forwarded(?:\s+many\s+times)?)\b")


def es_reenviado(texto: str) -> bool:
    """True si el texto abre con el marcador de reenvío de WhatsApp."""
    return bool(_RE_REENVIADO.match(texto or ""))


def detectar_enterrado(texto: str) -> Anclaje | None:
    """Email/mensaje pegado con cabecera → Anclaje (de, fecha). None si no hay autor
    literal recuperable.

    Pass-through del body-scan endurecido de email_atomize (``atribucion_en_cuerpo``):
    exige un ``<addr>`` literal (G1) y una atribución Apple o ``De:/From:`` bien formada
    en la CABEZA del texto, y nunca devuelve un Anclaje sin ``.de`` (prime directive).

    LÍMITE v1 (decisión 2026-06-25): la cabecera debe ir al INICIO del mensaje. El preámbulo
    conversacional ("os reenvío esto:" + email pegado) NO se maneja todavía: reposicionar la
    ventana de búsqueda relajaría la acotación-a-la-cabeza de G2 y abriría misatribución por
    citas profundas. Diferido a mejora futura (ver spec §16).
    """
    return atribucion_en_cuerpo(texto or "")


def ligar_quote(extracto: str, textos_previos: dict[str, str]) -> str:
    """Si el extracto citado coincide EXACTO con el texto de un mensaje previo del mismo
    chat, devuelve su MSG-id; si no liga, "" (no inventa). v1 mínimo."""
    objetivo = (extracto or "").strip()
    if not objetivo:
        return ""
    for msg_id, texto in textos_previos.items():
        if (texto or "").strip() == objetivo:
            return msg_id
    return ""
