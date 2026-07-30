"""MEJORAS #109, pieza barata: un portador VETADO deja localizable su historial citado.

Antes de esto, cuando `_sandwich` vetaba un portador HTML, `reconstruir` devolvia cero
candidatos Y cero punteros: los bloques citados no aparecian en ningun artefacto -- ni como
ficha (correcto: sin cabecera no se puede atribuir), ni como puntero (eso era el defecto).
Medido en el corpus real: 1493 palabras de historial de un hilo que solo sobrevivian en el
`.eml` crudo.

La regla que estos tests fijan: el veto sigue intacto (cero ancestros, cero candidatos, nada
de atribucion) pero los bloques citados salen como PUNTEROS SIN `de`. Es aditivo sobre la
cola de revision y no puede misatribuir, porque no acuna remitente.
"""
from __future__ import annotations

import json
from email.message import EmailMessage
from pathlib import Path

from core.email_atomize import inline as I
from core.email_atomize import pipeline as P


class _MA:
    """Doble minimo del mensaje de Capa A que `reconstruir` consume."""

    def __init__(self, msg_id: str = "MSG-00001", fecha_iso: str = "2026-07-28"):
        self.msg_id, self.fecha_iso = msg_id, fecha_iso


# Intercalada REAL: texto de autor entre dos citas CON CONTENIDO. El veto es correcto.
_HTML_VETADO = ('<div>Respondo abajo</div>'
                '<blockquote>PRIMERA CITA con bastante texto para que el extracto se vea</blockquote>'
                '<div>Esto no lo aceptamos</div>'
                '<blockquote>SEGUNDA CITA con bastante texto para que el extracto se vea</blockquote>')


def test_el_veto_conserva_las_citas_sin_devolverlas_como_ancestros():
    """La invariante que hace segura a esta pieza: el veto sigue dando CERO ancestros —así la
    Capa B no corre y no hay atribucion posible— pero las citas quedan conservadas aparte."""
    seg = I.segmentar_html(_HTML_VETADO)
    assert seg.respuesta_intercalada is True
    assert seg.ancestros == [], "el veto debe seguir dando CERO ancestros: sin Capa B"
    assert len(seg.citas_vetadas) == 2, "las dos citas deben quedar localizables"
    assert [len(c.texto.split()) > 0 for c in seg.citas_vetadas] == [True, True]

    # Y en un portador NO vetado la lista va vacia: no se duplica lo que ya son ancestros.
    limpio = I.segmentar_html('<div>hola</div><blockquote>una cita</blockquote>')
    assert limpio.respuesta_intercalada is False
    assert len(limpio.ancestros) == 1 and limpio.citas_vetadas == []


def test_reconstruir_convierte_las_citas_vetadas_en_punteros_sin_de(monkeypatch):
    """Contrato duro: punteros SI, atribucion NO. Ni `de`, ni fingerprint, ni candidatos."""
    seg = I.segmentar_html(_HTML_VETADO)
    monkeypatch.setattr(I, "segmentar", lambda raw: seg)

    res = I.reconstruir(_MA("MSG-00007"), b"raw irrelevante")

    assert res.intercalada is True
    assert res.candidatos == [], "un portador vetado NUNCA produce ficha"
    vetadas = [p for p in res.punteros if p.motivo == "cita_en_portador_vetado"]
    assert len(vetadas) == 2, f"se esperaban 2 punteros de cita; hay {len(res.punteros)}"
    for p in vetadas:
        assert p.portador_msg_id == "MSG-00007"
        assert p.de == "", "MISATRIBUCION: un puntero de portador vetado no puede llevar remitente"
        assert p.fingerprint == "", "sin fingerprint: no puede colapsar ni promoverse"
        assert p.confianza == "baja"
        assert p.extracto, "el puntero existe para hacer LOCALIZABLE el texto: extracto vacio no sirve"
    assert {p.extracto.split()[0] for p in vetadas} == {"PRIMERA", "SEGUNDA"}, \
        "cada puntero lleva el extracto de SU cita"


def test_una_cita_vacia_no_produce_puntero(monkeypatch):
    """Un `blockquote` sin contenido no es un localizador de nada: seria una fila en la cola que
    dice «aqui hay una cita» y no ensena ninguna. La forma NO es hipotetica — de los portadores
    del corpus real medido, tres tenian los dos `blockquote` genuinamente vacios."""
    html = ('<div>Respondo abajo</div><blockquote></blockquote>'
            '<div>Esto no lo aceptamos</div><blockquote></blockquote>')
    seg = I.segmentar_html(html)
    assert seg.respuesta_intercalada is True, "sigue siendo intercalada: el veto no cambia"
    assert len(seg.citas_vetadas) == 2, "el parser las ve; el filtro actua al emitir el puntero"

    monkeypatch.setattr(I, "segmentar", lambda raw: seg)
    res = I.reconstruir(_MA(), b"raw irrelevante")
    assert [p for p in res.punteros if p.motivo == "cita_en_portador_vetado"] == []


def _eml(mid: str, subject: str, *, fecha: str, html: str) -> bytes:
    m = EmailMessage()
    m["Message-ID"] = mid
    m["Subject"] = subject
    m["Date"] = fecha
    m["From"] = "car@example.invalid"
    m["To"] = "dest@example.invalid"
    m.set_content("cuerpo del portador")
    m.add_alternative(f"<html><body>{html}</body></html>", subtype="html")
    m.set_boundary(f"=====FRONTERA-FIJA-{subject.replace(' ', '-')}=====")
    return m.as_bytes()


def test_el_historial_del_portador_vetado_llega_a_la_cola_de_revision(tmp_path):
    """Integracion contra el motor real: el texto citado pasa a ser LOCALIZABLE en
    `_revision/cola.md`, que es el valor de esta pieza, sin que aparezca ninguna ficha nueva."""
    src, out = tmp_path / "03_Email", tmp_path / "Emails"
    src.mkdir(parents=True)
    (src / "2026-07-28_vetado.eml").write_bytes(
        _eml("<vetado@example.invalid>", "Intercalada real",
             fecha="Tue, 28 Jul 2026 10:00:00 +0200", html=_HTML_VETADO))

    P.atomize_dir(src, out)

    reg = json.loads((out / "_registro.json").read_text(encoding="utf-8"))
    # Los Message-ID se guardan SIN angulos.
    msg = reg["mensajes"]["vetado@example.invalid"]["id"]
    fichas = list((out / "mensajes").glob("*.md"))
    assert len(fichas) == 1, "el portador vetado no debe generar fichas nuevas"

    cola = (out / "_revision" / "cola.md").read_text(encoding="utf-8")
    filas = [l for l in cola.splitlines() if l.startswith(f"| {msg} ")]
    vetadas = [l for l in filas if "cita_en_portador_vetado" in l]
    assert len(vetadas) == 2, f"las 2 citas deben quedar en la cola; filas: {filas}"
    assert any("PRIMERA CITA" in l for l in vetadas)
    assert any("SEGUNDA CITA" in l for l in vetadas)
    # Y el portador sigue declarandose sin segmentar: la pieza es aditiva, no sustituye el aviso.
    assert any("intercalada_no_segmentada" in l for l in filas)
