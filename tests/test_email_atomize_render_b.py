from __future__ import annotations
import json
from core.email_atomize.model import RegistroMensaje, SegmentoEnterrado
from core.email_atomize import render as R
from core.email_atomize import corpus as C


def _b(**kw):
    base = dict(msg_id="MSG-00050", capa="B", confianza="alta-reconstruida",
                de="per01a@example.invalid", de_nombre="PersonaUno", fecha_iso="2020-05-01",
                hora="0900", asunto="[inmueble]", cuerpo="texto reconstruido",
                reconstruido_desde_cita=True, reconstruido_de="MSG-00042",
                fingerprint="fp:abc", procedencia=[{"citado_en": "MSG-00042", "profundidad": 1}])
    base.update(kw)
    return RegistroMensaje(**base)


def test_md_capa_b_lleva_banner_y_flags():
    md = R.render_md(_b())
    assert "capa: B" in md and "confianza: alta-reconstruida" in md
    assert "reconstruido_desde_cita: true" in md and "reconstruido_de: MSG-00042" in md
    assert "RECONSTRUIDO DESDE CITA" in md  # banner en el cuerpo


def test_correos_lectura_de_reconstruido_distinto():
    doc = R.render_correos_lectura([_b()])
    assert "De (reconstruido)" in doc


def test_render_revision_tres_colas():
    punteros = [SegmentoEnterrado(portador_msg_id="MSG-1", estilo="quote_gt",
                                  confianza="baja", motivo="sin_cabecera", extracto="...")]
    msgs_b = [_b(en_revision=True)]
    out = R.render_revision(msgs_b, punteros, watched=frozenset({"per01a@example.invalid"}))
    assert "cola.md" in out and "casi_duplicados.md" in out and "del_burgo.md" in out
    assert "MSG-1" in out["cola.md"]
    assert "per01a@example.invalid" in out["del_burgo.md"]


def test_corpus_incluye_fingerprint_y_capa_b():
    fila = json.loads(C.corpus_jsonl([_b()]).strip().splitlines()[1])
    assert fila["capa"] == "B" and fila["fingerprint"] == "fp:abc"
    assert fila["en_revision"] is False


def test_render_revision_sin_watched_produce_del_burgo_vacio():
    out = R.render_revision([], [], watched=None)
    assert "del_burgo.md" in out
    # sin watched → del_burgo.md solo cabecera, ninguna fila de dirección
    filas = [l for l in out["del_burgo.md"].splitlines()
             if l.startswith("|") and "---" not in l and "Ref" not in l]
    assert filas == []
