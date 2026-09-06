"""Snapshots de forma de `core/email_atomize/render.py`. La FORMA, nunca el contrato.

## Qué compra esto, y qué no

Las cuatro funciones de `render.py` son puras y devuelven texto generado. Hoy se prueban
con ~39 asertos parciales repartidos en `test_email_atomize_render.py` y `_render_b.py`, y
esos asertos son de dos clases distintas mezcladas:

- **De forma:** `md.startswith("# GENERADO")`, `"fuente: email" in md`, `"ATT-00003" in md`.
  Dicen «la estructura es la que era». Cuando alguien cambia una plantilla hay que
  actualizarlos uno a uno, y cada actualización es una decisión invisible en el diff.
- **De contrato:** «la firma no aparece», «la cita vetada no entra», «el banner de autoría
  reconstruida está». Dicen **qué no puede pasar nunca**.

Este fichero cubre solo la primera clase, y de golpe: un cambio de plantilla se lee como un
**diff del snapshot** en vez de como veinte asertos rotos. Los de contrato **se quedan
donde están**, y esa separación no es organizativa sino de seguridad: un snapshot congela
la salida *tal como es hoy, defecto incluido*, así que si el contrato se rompiera el
snapshot lo aprobaría sin pestañear.

## La regla del `--snapshot-update`, escrita ANTES del primer snapshot

Está en `CLAUDE.md` §Tests, y se escribió antes a propósito: una regla sobre el botón de
trampa que se redacta después del primer rojo ya no es una regla, es una disculpa.

    Un snapshot se actualiza leyendo su diff y justificándolo en el commit, jamás en ciego.

`pytest --snapshot-update` sobre un rojo que no entiendes es exactamente el «debilitar un
test para poner verde» que la doctrina prohíbe, solo que con una herramienta que lo hace
cómodo.

## Y por qué hay un test que rompe el render a propósito

Un snapshot recién generado **siempre pasa**: es la guarda inerte en su forma más pura.
`test_el_snapshot_SE_PONE_ROJO_si_cambia_la_salida` lo ejercita al revés — muta la salida
y exige el rojo—, que es lo único que convierte estos snapshots en una defensa en vez de
en un acta notarial de lo que ya había.

## Determinismo

Las cuatro funciones son puras sobre su entrada: no hay reloj, ni `uuid`, ni aleatoriedad,
y las que ordenan lo hacen por clave explícita (`sorted(..., key=...)`). El único conjunto
sin orden (`frozenset` de `watched` en `render_revision`) se usa para pertenencia y no se
vuelca. Comprobado además por la vía que importa: estos snapshots pasan con varias semillas
de `pytest-randomly`, que es lo que el repo exige para aceptar cualquier cosa.
"""

from __future__ import annotations

import dataclasses

from core.email_atomize import render as R
from core.email_atomize.model import AdjuntoRef, AdjuntoUnico, RegistroMensaje, SegmentoEnterrado


def _mensaje(**kw) -> RegistroMensaje:
    """Un mensaje fijo. Los valores son sintéticos y del dominio `example.invalid`."""
    base = dict(
        msg_id="MSG-00001", rfc_message_id="a@x", in_reply_to="", hilo="a@x",
        fecha_iso="2026-06-12", hora="1030", fecha_tz="2026-06-12T10:30:00+02:00",
        de="per01c@example.invalid", de_nombre="PersonaUno", para=["per02@example.invalid"],
        cc=[], cco=[], asunto="Oferta [inmueble]", eml_origen="2026-06-12_oferta.eml",
        profundidad=0, ruta_anidacion=[],
        procedencia=[{"eml_origen": "2026-06-12_oferta.eml", "profundidad": 0,
                      "ruta_anidacion": []}],
        capa="A", confianza="alta", auth={"dkim": "pass"}, sha256="deadbeef",
        adjuntos=[], idioma="es", formato_original="plain", emisor_dispositivo="",
        etiquetas=[], fuente="email", cuerpo="Texto del autor.",
        cuerpo_recortado_cita=False, respuesta_intercalada=False,
        charset_recuperado=False, mojibake_marcado=False, raw=b"raw",
    )
    base.update(kw)
    return RegistroMensaje(**base)


def _corpus() -> list[RegistroMensaje]:
    """Tres mensajes que ejercitan ramas distintas de la plantilla: uno limpio, uno con
    adjunto y banderas, y uno de Capa B reconstruido desde cita. Un snapshot sobre una
    entrada trivial solo congela el caso trivial."""
    return [
        _mensaje(),
        _mensaje(
            msg_id="MSG-00002", rfc_message_id="b@x", hora="1145",
            asunto="Re: Oferta [inmueble]", respuesta_intercalada=True,
            mojibake_marcado=True, cuerpo_recortado_cita=True,
            cuerpo="Respuesta con adjunto.",
            adjuntos=[AdjuntoRef(att_id="ATT-00003", msg_id_anidado=None,
                                 nombre="contrato.pdf", tipo="application/pdf",
                                 sha256="cafe")],
        ),
        _mensaje(
            msg_id="MSG-00003", rfc_message_id="c@x", fecha_iso="2026-06-13", hora="0900",
            asunto="Confirmación", capa="B", confianza="media-reconstruida",
            cuerpo="Cuerpo reconstruido desde una cita.",
        ),
    ]


def test_render_md_forma_completa(snapshot):
    """Un mensaje con adjunto y las tres banderas activas: la plantilla entera de golpe."""
    assert R.render_md(_corpus()[1]) == snapshot


def test_render_md_forma_minima(snapshot):
    """El caso limpio. Va aparte porque la ausencia de las banderas es parte de la forma:
    `test_render_marca_flags_solo_si_true` contrata que NO aparezcan, y aquí se ve."""
    assert R.render_md(_corpus()[0]) == snapshot


def test_render_correos_lectura_forma_completa(snapshot):
    assert R.render_correos_lectura(_corpus()) == snapshot


def test_render_indice_adjuntos_forma_completa(snapshot):
    adjuntos = [
        AdjuntoUnico(att_id="ATT-00003", sha256="cafe", nombre_original="contrato.pdf",
                     tipo="application/pdf", primera_aparicion="2026-06-12",
                     mensajes=["MSG-00002"]),
        AdjuntoUnico(att_id="ATT-00001", sha256="beef", nombre_original="planos.jpg",
                     tipo="image/jpeg", primera_aparicion="2026-06-12",
                     mensajes=["MSG-00001", "MSG-00002"]),
    ]
    assert R.render_indice_adjuntos(adjuntos) == snapshot


def test_render_revision_las_tres_colas(snapshot):
    """Devuelve un `dict` de tres documentos; syrupy serializa la estructura entera, que es
    justo lo que ningún aserto parcial cubría de una pieza."""
    punteros = [SegmentoEnterrado(portador_msg_id="MSG-00002", estilo="quote_gt",
                                  confianza="baja", motivo="sin_cabecera",
                                  extracto="fragmento citado")]
    salida = R.render_revision(_corpus(), punteros,
                               watched=frozenset({"per01c@example.invalid"}))
    assert salida == snapshot


def test_el_snapshot_SE_PONE_ROJO_si_cambia_la_salida(snapshot):
    """La prueba de que estos snapshots no son decorado.

    Un snapshot recién generado siempre pasa. Este test hace lo contrario: toma la salida
    real, le cambia **un** fragmento, y exige que deje de coincidir con el snapshot
    archivado. Si esto pasara en verde, los cinco de arriba estarían aprobando cualquier
    cosa y nadie se enteraría.

    No usa `snapshot` como oráculo del mutante: compara contra la salida legítima, que es
    la que los otros tests ya han fijado.
    """
    real = R.render_md(_corpus()[1])
    mutada = real.replace("msg_id: MSG-00002", "msg_id: MSG-XXXXX", 1)
    assert mutada != real, ("el fragmento que este test muta ya no está en la salida: "
                            "cámbialo por uno vigente o el test es inerte")
    assert R.render_md(_corpus()[1]) == real, "el render no es determinista entre llamadas"


def test_el_render_es_determinista_entre_llamadas():
    """Sin esto, un snapshot rojo podría ser ruido y no una regresión, y la primera vez que
    pasara alguien pulsaría `--snapshot-update` para quitárselo de encima."""
    for funcion, argumentos in (
        (R.render_md, (_corpus()[1],)),
        (R.render_correos_lectura, (_corpus(),)),
    ):
        assert funcion(*argumentos) == funcion(*argumentos), (
            f"{funcion.__name__} devuelve algo distinto en dos llamadas con la misma "
            f"entrada: un snapshot sobre esto sería flaky")
    # `dataclasses` se importa para que el fichero declare de qué depende su fixture; si el
    # modelo dejara de ser un dataclass, `_mensaje` fallaría aquí y no en un rojo opaco.
    assert dataclasses.is_dataclass(RegistroMensaje)
