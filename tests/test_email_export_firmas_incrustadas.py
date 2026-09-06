"""El filtro de firmas, extendido a los adjuntos EMBEBIDOS (acción 6b).

El filtro conjuntivo de firmas existía **solo para enlaces** `<img src>`
(`_resuelve_enlaces`, `links_filtered_sig`). Los adjuntos embebidos no pasaban por él,
así que activar `--extraer-adjuntos` por defecto habría depositado en `00_Input` la
avalancha entera.

**Medido sobre el corpus real el 2026-09-06** (24 casos, 462 `.eml`, 444 adjuntos):

| Imágenes por `(disposition, Content-ID, tamaño)` | n |
|---|---|
| `inline` / sin disposition + CID + <50 KB | **140** ← logotipos de firma |
| `inline` + CID + ≥50 KB | 25 |
| `attachment` + CID | 31 |
| `inline` + sin CID + <50 KB | 6 |
| `attachment` + sin CID + <50 KB | 3 |

Es decir: **140 de 444 adjuntos (32%) son logotipos**, mediana 9,1 KB.

**El criterio es el mismo conjuntivo del §4 que ya rige para enlaces**, traducido a la
señal estructural que existe en un adjunto embebido:

    NO adjuntada a propósito  AND  imagen  AND  referenciada desde el cuerpo  AND  pequeña

y con su regla de oro intacta: **una imagen con `Content-Disposition: attachment` NUNCA
se filtra, por pequeña que sea** — alguien la adjuntó queriendo, y ante la duda es prueba.
"""
from __future__ import annotations

from email.message import EmailMessage

import pytest

from core import email_export as ee

_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200
_GRANDE = b"\x89PNG\r\n\x1a\n" + b"\x00" * (60 * 1024)


def _mensaje(partes) -> bytes:
    """`partes`: lista de (datos, mime, filename, disposition, cid)."""
    msg = EmailMessage()
    msg["Message-ID"] = "<m@x>"
    msg["Subject"] = "Con imágenes"
    msg["Date"] = "Thu, 12 Jun 2026 10:00:00 +0200"
    msg["From"] = "eva@engelvoelkers.com"
    msg["To"] = "despacho@tyukhay.legal"
    msg.set_content("Cuerpo con firma.")
    for datos, mime, fn, disp, cid in partes:
        maintype, _, subtype = mime.partition("/")
        cabeceras = {}
        if cid:
            cabeceras["cid"] = cid
        msg.add_attachment(datos, maintype=maintype, subtype=subtype,
                           filename=fn, disposition=disp, **cabeceras)
    return msg.as_bytes()


def _adjuntos(raw: bytes):
    return ee.particionar_eml(raw)[1]


# ---------------------------------------------------------------------------
# La capa pura: los cuatro términos de la conjunción, uno a uno
# ---------------------------------------------------------------------------

def test_logo_inline_con_CID_y_pequeno_ES_firma():
    """El caso medido 140 veces en el corpus."""
    adj = _adjuntos(_mensaje([(_PNG, "image/png", "image001.png", "inline", "<logo@ev>")]))
    assert [a.es_firma for a in adj] == [True]


def test_adjuntada_a_PROPOSITO_no_es_firma_por_pequena_que_sea():
    """La regla de oro, heredada del filtro de enlaces: `attachment` NUNCA se filtra.

    En el corpus hay 25 imágenes así, `attachment` y por debajo de 50 KB. Filtrarlas
    por tamaño habría descartado prueba que alguien adjuntó queriendo.
    """
    adj = _adjuntos(_mensaje([(_PNG, "image/png", "recorte.png", "attachment", "<x@y>")]))
    assert [a.es_firma for a in adj] == [False]


def test_imagen_grande_no_es_firma_aunque_sea_inline():
    """25 en el corpus: inline y ≥50 KB. Una captura pegada en el cuerpo es contenido."""
    adj = _adjuntos(_mensaje([(_GRANDE, "image/png", "captura.png", "inline", "<c@y>")]))
    assert [a.es_firma for a in adj] == [False]


def test_sin_Content_ID_no_es_firma():
    """Sin referencia desde el cuerpo no hay logo que sustituir: 6 así en el corpus."""
    adj = _adjuntos(_mensaje([(_PNG, "image/png", "suelta.png", "inline", None)]))
    assert [a.es_firma for a in adj] == [False]


def test_un_PDF_pequeno_inline_con_CID_no_es_firma():
    """El término «imagen» de la conjunción. Un PDF nunca es un logotipo."""
    adj = _adjuntos(_mensaje([(b"%PDF-1.4 x", "application/pdf", "nota.pdf",
                               "inline", "<p@y>")]))
    assert [a.es_firma for a in adj] == [False]


def test_la_frontera_de_tamano_es_estricta():
    """Exactamente 50 KB NO es firma: `<` y no `<=`, como el filtro de enlaces."""
    justo = b"\x89PNG\r\n\x1a\n" + b"\x00" * (ee._FIRMA_MAX_BYTES - 8)
    adj = _adjuntos(_mensaje([(justo, "image/png", "j.png", "inline", "<j@y>")]))
    assert len(justo) == ee._FIRMA_MAX_BYTES
    assert [a.es_firma for a in adj] == [False]


def test_convive_firma_y_prueba_en_el_mismo_correo():
    """El caso real: el consultor manda el contrato y su firma lleva el logo."""
    adj = _adjuntos(_mensaje([
        (b"%PDF-1.4 contrato", "application/pdf", "contrato.pdf", "attachment", None),
        (_PNG, "image/png", "image001.png", "inline", "<logo@ev>"),
    ]))
    assert [(a.nombre, a.es_firma) for a in adj] == [
        ("contrato.pdf", False), ("image001.png", True)]


# ---------------------------------------------------------------------------
# `split_eml` no cambia de contrato: sus tres llamadores no se tocan
# ---------------------------------------------------------------------------

def test_split_eml_conserva_su_contrato_de_tres_elementos_por_adjunto():
    raw = _mensaje([(_PNG, "image/png", "image001.png", "inline", "<logo@ev>")])
    _, adjuntos = ee.split_eml(raw)
    assert [(n, m) for n, m, _ in adjuntos] == [("image001.png", "image/png")]


def test_split_eml_NO_filtra_por_defecto():
    """Compatibilidad: `email_atomize` la llama y su comportamiento no cambia aquí."""
    raw = _mensaje([(_PNG, "image/png", "image001.png", "inline", "<logo@ev>")])
    assert len(ee.split_eml(raw)[1]) == 1


# ---------------------------------------------------------------------------
# El cableado: qué se escribe y qué se declara
# ---------------------------------------------------------------------------

from tests.test_email_export import (  # noqa: E402
    _ETIQUETA,
    _LABELS,
    _FakeService,
)

_CUENTA = "nikolai@engelvoelkers.com"


def _svc(raws):
    return _FakeService(
        labels=_LABELS, pages=[{"messages": [{"id": g} for g in raws]}], raws=raws)


def _correo_con_firma() -> dict[str, bytes]:
    return {"g1": _mensaje([
        (b"%PDF-1.4 contrato", "application/pdf", "contrato.pdf", "attachment", None),
        (_PNG, "image/png", "image001.png", "inline", "<logo@ev>"),
        (_PNG, "image/gif", "image002.gif", "inline", "<sep@ev>"),
    ])}


def test_el_logo_no_se_escribe_y_el_contrato_si(tmp_path):
    rep = ee.export_label(_CUENTA, _ETIQUETA, tmp_path, service=_svc(_correo_con_firma()),
                          extract_attachments=True)

    escritos = {p.name for p in tmp_path.rglob("*") if p.is_file()}
    assert "contrato.pdf" in escritos
    assert "image001.png" not in escritos
    assert "image002.gif" not in escritos
    assert rep.attachments == 1, "el contador cuenta lo depositado, no lo visto"


def test_las_firmas_filtradas_se_CUENTAN(tmp_path):
    """Como `links_filtered_sig` para enlaces: lo filtrado se declara, no desaparece."""
    rep = ee.export_label(_CUENTA, _ETIQUETA, tmp_path, service=_svc(_correo_con_firma()),
                          extract_attachments=True)
    assert rep.firmas_filtradas == 2
    assert "2 firmas" in rep.resumen()


def test_sin_extraer_adjuntos_el_eml_sigue_siendo_FIEL(tmp_path):
    """El filtro decide qué se extrae, NUNCA qué contiene el `.eml`. Un `.eml` mutilado
    no es prueba, y ese es el mismo principio que rige el correo padre de R1/H-01."""
    raws = _correo_con_firma()
    ee.export_label(_CUENTA, _ETIQUETA, tmp_path, service=_svc(raws),
                    extract_attachments=True)
    eml = next(p for p in tmp_path.rglob("*.eml"))
    assert eml.read_bytes() == raws["g1"], "byte-fiel, con su firma dentro"


# ---------------------------------------------------------------------------
# El default invertido (acción 6b): extraer pasa a ser lo normal
# ---------------------------------------------------------------------------

def test_por_DEFECTO_los_adjuntos_se_extraen(tmp_path):
    """La decisión que este bloque venía a cerrar. Gate 1 y Gate 2 pasados; el Gate 2
    re-medido el 2026-09-06 sobre 444 adjuntos reales: CERO adjuntos que sean correo,
    y no por suerte del corpus — `particionar_eml` salta `message/rfc822` por
    construcción."""
    rep = ee.export_label(_CUENTA, _ETIQUETA, tmp_path, service=_svc(_correo_con_firma()))

    assert rep.attachments == 1
    assert (tmp_path / "2026-06-12_con_imagenes" / "contrato.pdf").is_file()


def test_el_flag_de_vuelta_deja_el_eml_plano(tmp_path):
    rep = ee.export_label(_CUENTA, _ETIQUETA, tmp_path, service=_svc(_correo_con_firma()),
                          extract_attachments=False)

    assert rep.attachments == 0
    assert (tmp_path / "2026-06-12_con_imagenes.eml").is_file()
    assert not (tmp_path / "2026-06-12_con_imagenes").exists()


def test_un_correo_cuyo_UNICO_adjunto_es_la_firma_NO_crea_subcarpeta(tmp_path):
    """Si lo único que traía era el logotipo, extraer no aporta nada y una subcarpeta
    con un solo `.eml` dentro es peor que el fichero plano: ensucia la cronología."""
    raws = {"g1": _mensaje([(_PNG, "image/png", "image001.png", "inline", "<l@ev>")])}
    rep = ee.export_label(_CUENTA, _ETIQUETA, tmp_path, service=_svc(raws))

    assert rep.firmas_filtradas == 1
    assert rep.attachments == 0
    assert (tmp_path / "2026-06-12_con_imagenes.eml").is_file()
    assert not (tmp_path / "2026-06-12_con_imagenes").is_dir()
