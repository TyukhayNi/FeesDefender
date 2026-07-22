from __future__ import annotations

from core.email_atomize import vistas as V
from core.email_atomize.identidades import Identidades, Persona
from core.email_atomize.model import RegistroMensaje


def _m(msg_id, de="", para=None, cc=None, asunto="", cuerpo="", fecha="2024-05-01",
       hora="0900", capa="A", confianza="alta", reconstruido_de=""):
    return RegistroMensaje(
        msg_id=msg_id, de=de, para=para or [], cc=cc or [], asunto=asunto, cuerpo=cuerpo,
        fecha_iso=fecha, hora=hora, capa=capa, confianza=confianza,
        reconstruido_de=reconstruido_de)


def _ident_db():
    p = Persona(id="persona_uno", nombre="PersonaUno", vigilada=True,
                direcciones=[("per01a@example.invalid", "confirmada"),
                             ("per01b@example.invalid", "candidata")])
    ig = Persona(id="ignacio", nombre="Ignacio", vigilada=False,
                 direcciones=[("ignacio@despacho-ab.example", "confirmada")])
    return Identidades(
        vigiladas=frozenset({"per01a@example.invalid"}),
        candidatas=frozenset({"per01b@example.invalid"}),
        personas={"persona_uno": p, "ignacio": ig})


def test_vista_persona_agrupa_autor_y_destinatario_no_a_ignacio():
    ident = _ident_db()
    mensajes = [
        _m("MSG-1", de="per01a@example.invalid", asunto="autor confirmada"),
        _m("MSG-2", de="otro@x.com", para=["per01b@example.invalid"], asunto="destino candidata"),
        _m("MSG-3", de="ignacio@despacho-ab.example", asunto="ignacio fuera"),
    ]
    d = V.DefVista(id="dossier_persona_vigilada", titulo="Dossier", tipo="persona",
                   persona="persona_uno")
    salidas, notas = V.render_vistas(mensajes, ident, [d])
    doc = salidas["dossier_persona_vigilada.md"]
    assert "MSG-1" in doc and "MSG-2" in doc       # autor + destinatario (candidata incluida)
    assert "MSG-3" not in doc                       # Ignacio NUNCA entra
    assert notas == []


def test_vista_tematica_keyword_incluye_excluye_rango():
    ident = _ident_db()
    mensajes = [
        _m("MSG-1", asunto="[inmueble] arras", fecha="2024-03-01"),     # keyword + en rango
        _m("MSG-2", cuerpo="hablamos del ENCARGO", fecha="2024-03-02"),  # keyword en cuerpo
        _m("MSG-3", asunto="nada que ver", fecha="2024-03-03"),       # sin keyword
        _m("MSG-4", asunto="[inmueble]", fecha="2025-01-01"),           # keyword pero fuera de rango
        _m("MSG-5", asunto="[inmueble]", fecha="2024-03-04"),           # keyword pero excluido
    ]
    d = V.DefVista(id="nexo_causal", titulo="Nexo", tipo="tematica",
                   palabras_clave=["inmueble", "encargo"],
                   incluye_msg=["MSG-3"], excluye_msg=["MSG-5"],
                   desde="2024-01-01", hasta="2024-12-31")
    salidas, _notas = V.render_vistas(mensajes, ident, [d])
    doc = salidas["nexo_causal.md"]
    assert "MSG-1" in doc and "MSG-2" in doc        # keyword en asunto y en cuerpo
    assert "MSG-3" in doc                            # incluye_msg fuerza dentro (sin keyword)
    assert "MSG-4" not in doc                         # fuera de rango
    assert "MSG-5" not in doc                         # excluye_msg fuerza fuera


def test_vista_persona_inexistente_se_omite_con_nota():
    ident = _ident_db()
    d = V.DefVista(id="rota", tipo="persona", persona="no_existe")
    salidas, notas = V.render_vistas([_m("MSG-1")], ident, [d])
    assert "rota.md" not in salidas
    assert any("no_existe" in n for n in notas)


def test_vista_tipo_desconocido_se_omite_con_nota():
    ident = _ident_db()
    d = V.DefVista(id="rara", tipo="quesoyo")
    salidas, notas = V.render_vistas([_m("MSG-1")], ident, [d])
    assert "rara.md" not in salidas
    assert any("quesoyo" in n for n in notas)


def test_cargar_vistas_sin_fichero_es_vacio(tmp_path):
    assert V.cargar_vistas(tmp_path) == []


def test_render_vistas_lista_vacia_no_crashea():
    ident = _ident_db()
    dp = V.DefVista(id="dossier_persona_vigilada", tipo="persona", persona="persona_uno")
    dt = V.DefVista(id="nexo_causal", tipo="tematica", palabras_clave=["inmueble"])
    salidas, notas = V.render_vistas([], ident, [dp, dt])
    assert "dossier_persona_vigilada.md" in salidas and "nexo_causal.md" in salidas
    assert notas == []


def test_tematica_sin_palabras_clave_no_incluye_nada():
    ident = _ident_db()
    mensajes = [_m("MSG-1", asunto="[inmueble] arras"), _m("MSG-2", cuerpo="lo que sea")]
    d = V.DefVista(id="nexo_causal", tipo="tematica", palabras_clave=[])
    salidas, _notas = V.render_vistas(mensajes, ident, [d])
    doc = salidas["nexo_causal.md"]
    assert "MSG-1" not in doc and "MSG-2" not in doc   # sin keywords → no casa nada


def test_vista_persona_normaliza_de_en_mayusculas():
    ident = _ident_db()
    mensajes = [_m("MSG-1", de="per01a@example.invalid", asunto="autor mayusculas")]
    d = V.DefVista(id="dossier_persona_vigilada", tipo="persona", persona="persona_uno")
    salidas, _notas = V.render_vistas(mensajes, ident, [d])
    assert "MSG-1" in salidas["dossier_persona_vigilada.md"]   # de en mayúsculas SÍ casa
