"""`refrescar`: descubrir los envíos de una expedición y darles sus dos relojes."""
from __future__ import annotations

from datetime import datetime, timezone

from core import expedicion_certificada as exp


class FakeTransporte:
    """Doble del transporte: solo `listar` y `estados`."""

    def __init__(self, listado, historicos):
        self._listado, self._historicos = listado, historicos
        self.filtros_vistos: list[dict] = []

    def listar(self, **filtros):
        self.filtros_vistos.append(filtros)
        return list(self._listado)

    def estados(self, id_envio):
        return list(self._historicos.get(id_envio, []))


def _entorno(tmp_path, transporte, partes=()):
    return exp.EntornoExpedicion(
        codicert=transporte, partes_de=lambda w: list(partes),
        ahora=lambda: datetime(2026, 9, 21, tzinfo=timezone.utc),
        raiz=tmp_path, plaza="Madrid", entorno="produccion", usuario="madrid.bd")


def _ev(id_envio, tipo, dest, idp="W-04AKM2 - OVC"):
    return {"id": id_envio, "tipo": tipo, "asunto": idp, "destinatarios": dest,
            "id_personalizado": idp, "fecha": "2026-09-10T18:26:08+02:00",
            "estado": {"codigo": 5, "titulo": "Procesado",
                       "fecha": "2026-09-10T18:26:10+02:00", "detalle": None}}


def _h(*pares):
    return [{"codigo": c, "titulo": "", "fecha": f, "detalle": None} for c, f in pares]


def test_filtra_por_id_personalizado_EXACTO(tmp_path):
    """M-8: en la cuenta conviven identificadores hechos a mano. No se adivinan."""
    t = FakeTransporte(
        [_ev("006a", "c", "x@y.es"),
         _ev("006b", "c", "z@y.es", idp="W-04AKM2"),           # sin tipo
         _ev("006c", "c", "w@y.es", idp="W-04AKM2 - OVC 2")],  # otra expedición
        {"006a": _h((20, "2026-09-12T23:03:43+02:00"))})
    e = exp.refrescar("W-04AKM2", "OVC", entorno_exp=_entorno(tmp_path, t))
    assert [x.id_envio for x in e.envios] == ["006a"]


def test_lee_el_HISTORICO_de_cada_envio_no_el_estado_del_listado(tmp_path):
    """M-1: el listado dice 19/17-09; el histórico, 17/14-09. Manda el histórico."""
    listado = [_ev("006b", "b", "ACME S.L.")]
    listado[0]["estado"] = {"codigo": 19, "titulo": "Entregado con albarán",
                            "fecha": "2026-09-17T13:00:52+02:00", "detalle": None}
    t = FakeTransporte(listado, {"006b": _h((17, "2026-09-14T11:31:08+02:00"),
                                            (19, "2026-09-17T13:00:52+02:00"))})
    e = exp.refrescar("W-04AKM2", "OVC", entorno_exp=_entorno(tmp_path, t))
    assert e.envios[0].recibido_en == datetime.fromisoformat("2026-09-14T11:31:08+02:00")


def test_acota_la_consulta_por_fecha(tmp_path):
    """§4.3: el denominador es el Market Center, no el jurídico. Siempre acotado."""
    t = FakeTransporte([], {})
    exp.refrescar("W-04AKM2", "OVC", entorno_exp=_entorno(tmp_path, t))
    assert "fecha_inicio" in t.filtros_vistos[0] and "fecha_fin" in t.filtros_vistos[0]


def test_la_ventana_arranca_en_el_registro_de_intencion_si_lo_hay(tmp_path):
    """El registro local sabe CUÁNDO se expidió; la ventana por defecto solo adivina."""
    reg = exp.RegistroIntencion(tmp_path / "_codicert_intencion.jsonl",
                                entorno="produccion", usuario="madrid.bd",
                                ahora=lambda: datetime(2026, 6, 1, tzinfo=timezone.utc))
    clave = reg.anotar("W-04AKM2 - OVC", "correo", "huella")
    reg.cerrar(clave, "006a")
    t = FakeTransporte([], {})
    exp.refrescar("W-04AKM2", "OVC", entorno_exp=_entorno(tmp_path, t))
    assert t.filtros_vistos[0]["fecha_inicio"] <= "2026-06-01"


def test_un_vacio_se_declara_y_NO_se_lee_como_expedicion_terminada(tmp_path):
    """§5.2: un censo negativo no prueba ausencia."""
    t = FakeTransporte([], {})
    e = exp.refrescar("W-04AKM2", "OVC", entorno_exp=_entorno(tmp_path, t))
    assert e.envios == () and e.completa is False


def test_por_requerido_casa_el_destinatario_con_la_parte(tmp_path):
    """§6.1: el nivel que manda. Dos requeridos, dos relojes."""
    partes = [{"nombre": "ANA", "1apellido": "LÓPEZ", "email": "ana@y.es",
               "movil": "600111222"},
              {"nombre": "LUIS", "1apellido": "GIL", "email": "luis@y.es"}]
    t = FakeTransporte(
        [_ev("006a", "c", "ana@y.es"), _ev("006b", "c", "luis@y.es")],
        {"006a": _h((20, "2026-09-12T23:03:43+02:00")),
         "006b": _h((21, "2026-09-18T19:00:00+02:00"))})
    e = exp.refrescar("W-04AKM2", "OVC", entorno_exp=_entorno(tmp_path, t, partes))
    req = {r.etiqueta: r for r in e.por_requerido(partes)}
    assert req["ANA LÓPEZ"].recibido_en == datetime.fromisoformat(
        "2026-09-12T23:03:43+02:00")
    assert req["LUIS GIL"].recibido_en == datetime.fromisoformat(
        "2026-09-18T19:00:00+02:00")


def test_un_destinatario_que_no_casa_NO_se_atribuye_a_nadie(tmp_path):
    """Lo que no casa se declara. Atribuirlo al primero inventaría un reloj."""
    partes = [{"nombre": "ANA", "1apellido": "LÓPEZ", "email": "ana@y.es"}]
    t = FakeTransporte([_ev("006z", "b", "QUIEN SEA S.L.")],
                       {"006z": _h((17, "2026-09-14T11:31:08+02:00"))})
    e = exp.refrescar("W-04AKM2", "OVC", entorno_exp=_entorno(tmp_path, t, partes))
    reqs = e.por_requerido(partes)
    assert [r.etiqueta for r in reqs if r.clave == exp.SIN_CASAR] == ["(sin casar)"]
    assert all(r.recibido_en is None for r in reqs if r.etiqueta == "ANA LÓPEZ")


def test_el_movil_casa_con_prefijo_y_sin_el(tmp_path):
    """§1.1: el destinatario SMS real de producción lleva `34` delante."""
    partes = [{"nombre": "ANA", "1apellido": "LÓPEZ", "movil": "600111222"}]
    t = FakeTransporte([_ev("006s", "c", "34600111222")],
                       {"006s": _h((20, "2026-09-12T23:03:43+02:00"))})
    e = exp.refrescar("W-04AKM2", "OVC", entorno_exp=_entorno(tmp_path, t, partes))
    req = {r.etiqueta: r for r in e.por_requerido(partes)}
    assert req["ANA LÓPEZ"].recibido_en is not None
