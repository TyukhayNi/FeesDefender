"""Rebanada 1 del cableado de F3: el inventario de adjuntos, de Gmail a la cola.

Spec: `docs/superpowers/specs/2026-09-07-f3-cableado-bandeja-y-verificacion-design.md`
**§9.1**, remedio del hallazgo **CRÍTICO H-01** de la R1 adversarial.

## Qué defiende este fichero, en una frase

Que el inventario de adjuntos **exista y viaje**, y —lo que de verdad cierra el crítico— que
el sistema **distinga tres estados** que hoy colapsan en uno:

| Estado | Cómo se representa |
|---|---|
| el correo NO trae adjuntos, y lo sabemos | inventario **vacío**, `adjuntos_inventariados=True` |
| el correo trae adjuntos y aquí están | inventario con nombres, `adjuntos_inventariados=True` |
| **no lo sabemos** (ítem viejo de la cola) | `adjuntos_inventariados=False` |

Sin el tercero, `archivar` lee «sin pedidos» como «nada que subir» y **confirma un correo sin
archivar su documento, con `ok=True`, sin que nadie se entere** (H-01). El campo booleano existe
para que ese caso sea distinguible; no es adorno.

**Por qué un campo nuevo y no reinterpretar `attachment_names`:** el store ya tiene líneas escritas
con `attachment_names: {}` porque `procurador_runner` ponía `attachments=[]` a pelo, y
`_item_from_dict` hace `prop.get("attachment_names") or {}`. Así que en el JSONL vigente «medido,
sin adjuntos» y «nunca se miró» son **el mismo dato**. Un booleano ausente en las líneas viejas sí
los separa.

Nada de red: la Gmail API se representa con payloads sintéticos y el store va a `tmp_path`.
"""
from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.gmail_source import gmail_message_to_email  # noqa: E402
from core.procurador_intake import IntakeSignals, MatchResult  # noqa: E402
from core.procurador_review import (  # noqa: E402
    load_queue, upsert_queue_item,
)
from core.procurador_runner import process_email  # noqa: E402

# Remitente FICTICIO. `.invalid` está reservado por la RFC 2606 y no puede ser
# de nadie: el guard `test_no_pii_en_tests` cazó una versión anterior de este
# fichero con un dominio y un nombre REALES, copiados de los datos que estaba
# leyendo. Hizo justo su trabajo.
PROCURADOR = "Procuradora Ficticia <procuradora@ejemplo.invalid>"


# ---------------------------------------------------------------------------
# Payloads sintéticos de la Gmail API (`format=full`)
# ---------------------------------------------------------------------------

def _b64(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode()).decode()


def _cuerpo(texto: str = "Adjunto la notificación.") -> dict:
    return {"mimeType": "text/plain", "body": {"data": _b64(texto)}}


def _adjunto(nombre: str, att_id: str, *, inline: bool = False) -> dict:
    cabeceras = [{"name": "Content-Type", "value": "application/pdf"}]
    if inline:
        cabeceras.append({"name": "Content-Disposition",
                          "value": f'inline; filename="{nombre}"'})
        cabeceras.append({"name": "Content-ID", "value": "<logo@firma>"})
    else:
        cabeceras.append({"name": "Content-Disposition",
                          "value": f'attachment; filename="{nombre}"'})
    return {"filename": nombre, "headers": cabeceras,
            "body": {"attachmentId": att_id, "size": 1234}}


def _mensaje(*partes: dict, msg_id: str = "mensaje-1@ejemplo.invalid") -> dict:
    return {
        "id": "gmail-interno",
        "payload": {
            "mimeType": "multipart/mixed",
            "headers": [
                {"name": "Message-ID", "value": f"<{msg_id}>"},
                {"name": "From", "value": PROCURADOR},
                {"name": "Subject", "value": "Ref : 6845  Su ref : 51/2024"},
                {"name": "Date", "value": "Mon, 8 Sep 2026 10:00:00 +0200"},
            ],
            "parts": [_cuerpo(), *partes],
        },
    }


# ---------------------------------------------------------------------------
# A. La extracción: `gmail_source` deja de tirar el inventario
# ---------------------------------------------------------------------------

class TestExtraccionDelInventario:
    def test_inventaria_los_dos_adjuntos_en_orden(self):
        em = gmail_message_to_email(_mensaje(
            _adjunto("LXN202609071009040422.PDF", "att-1"),
            _adjunto("Todos-1531714.pdf", "att-2"),
        ))
        assert [a.nombre for a in em.adjuntos] == [
            "LXN202609071009040422.PDF", "Todos-1531714.pdf"
        ]

    def test_captura_el_attachment_id(self):
        """Sin el id no se pueden bajar los bytes (`MEJORAS #181`). Se recoge ahora
        porque es la misma pasada; bajarlos NO entra en esta rebanada."""
        em = gmail_message_to_email(_mensaje(_adjunto("a.pdf", "att-XYZ")))
        assert em.adjuntos[0].attachment_id == "att-XYZ"

    def test_correo_sin_adjuntos_da_inventario_VACIO_y_no_None(self):
        """La distinción que cierra H-01: «medido, no hay» es una tupla vacía."""
        em = gmail_message_to_email(_mensaje())
        assert em.adjuntos == (), "sin adjuntos es () medido, no None desconocido"

    def test_marca_inline_el_logo_de_firma(self):
        """Un logo de firma tiene `filename` y no es un documento archivable. Se
        inventaría —es lo observado— y se MARCA, para que el filtro de F4 pueda
        decidir sin volver a Gmail."""
        em = gmail_message_to_email(_mensaje(
            _adjunto("image001.png", "att-logo", inline=True),
            _adjunto("DECRETO.pdf", "att-doc"),
        ))
        por_nombre = {a.nombre: a for a in em.adjuntos}
        assert por_nombre["image001.png"].inline is True
        assert por_nombre["DECRETO.pdf"].inline is False

    def test_encuentra_adjuntos_en_multipart_anidado(self):
        """Los correos reales anidan `multipart/alternative` + `multipart/mixed`."""
        anidado = {"mimeType": "multipart/mixed",
                   "parts": [_adjunto("dentro.pdf", "att-hondo")]}
        em = gmail_message_to_email(_mensaje(anidado))
        assert [a.nombre for a in em.adjuntos] == ["dentro.pdf"]


# ---------------------------------------------------------------------------
# B. El viaje: del `EmailMessage` a la propuesta de la tarjeta
# ---------------------------------------------------------------------------

def _senales_falsas(*_a, **_k) -> IntakeSignals:
    return IntakeSignals(su_ref="51/2024", es_ruido=False)


def _match_falso(*_a, **_k) -> MatchResult:
    return MatchResult(expediente_id=683, confianza="alta", senales_usadas=["su_ref"])


@pytest.fixture(autouse=True)
def _remitente_reconocido(monkeypatch):
    """El catálogo de procuradores vive en un YAML **gitignored** y en un worktree
    carga VACÍO —medido: 0 dominios, 0 emails—, así que `is_procurador_email` diría
    `False` a todo y `process_email` descartaría cada correo como
    «remitente_no_procurador». Estos tests miden el INVENTARIO, no el catálogo, así
    que la puerta se abre a propósito.

    Que ese vacío sea silencioso es un defecto aparte, anotado en
    `docs/MEJORAS_FUTURAS.md` **#183** — no se arregla aquí.
    """
    monkeypatch.setattr("core.procurador_runner.is_procurador_email", lambda _a: True)


def _procesar(em):
    return process_email(em, extract_fn=_senales_falsas, match_fn=_match_falso)


class TestElInventarioLlegaALaPropuesta:
    def test_los_nombres_llegan_y_se_marca_inventariado(self):
        em = gmail_message_to_email(_mensaje(
            _adjunto("DECRETO.pdf", "att-1"), _adjunto("ACUSE.pdf", "att-2")))
        prop = _procesar(em).proposal
        assert prop.adjuntos_inventariados is True
        assert prop.attachment_names == {"DECRETO.pdf": "DECRETO.pdf",
                                         "ACUSE.pdf": "ACUSE.pdf"}, \
            "el prerellenado es el nombre ORIGINAL: renombrar es de la persona (D3)"

    def test_inventario_vacio_es_INVENTARIADO_con_cero_nombres(self):
        """El caso que H-01 confundía: se midió, y no hay. Eso SÍ se puede confirmar."""
        prop = _procesar(gmail_message_to_email(_mensaje())).proposal
        assert prop.adjuntos_inventariados is True
        assert prop.attachment_names == {}

    def test_sin_inventario_la_propuesta_dice_NO_inventariado(self):
        """Un `EmailMessage` que nadie inventarió (otra fuente, o código viejo)."""
        em = gmail_message_to_email(_mensaje(_adjunto("x.pdf", "att-1")))
        crudo = type(em)(**{**em.__dict__, "adjuntos": None})
        assert _procesar(crudo).proposal.adjuntos_inventariados is False


# ---------------------------------------------------------------------------
# C. La cola: los ítems viejos NO se dan por inventariados
# ---------------------------------------------------------------------------

class TestPersistencia:
    def test_una_linea_VIEJA_sin_la_clave_carga_como_NO_inventariado(self, tmp_path):
        """Regresión del store: las líneas ya escritas tienen `attachment_names: {}`
        porque `attachments` era `[]` a pelo. No se pueden leer como «no hay adjuntos»."""
        store = tmp_path / "cola.jsonl"
        store.write_text(json.dumps({
            "email_id": "viejo@ejemplo.invalid",
            "estado": "pendiente",
            "proposal": {"email_id": "viejo@ejemplo.invalid", "expediente_id": 683,
                         "confianza": "alta", "carpeta_id": None, "carpeta": None,
                         "attachment_names": {}},
        }, ensure_ascii=False) + "\n", encoding="utf-8")
        item = load_queue(store_path=store)[0]
        assert item.proposal.adjuntos_inventariados is False, \
            "sin la clave no se sabe: nunca se asume que no había adjuntos"

    def test_ida_y_vuelta_conserva_el_inventario(self, tmp_path):
        store = tmp_path / "cola.jsonl"
        em = gmail_message_to_email(_mensaje(_adjunto("DECR.pdf", "att-1")))
        upsert_queue_item(_procesar(em), store_path=store)
        prop = load_queue(store_path=store)[0].proposal
        assert prop.adjuntos_inventariados is True
        assert prop.attachment_names == {"DECR.pdf": "DECR.pdf"}
