"""La puerta humana: sin confirmación válida no sale nada, y un plan rancio se rechaza."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from core import expedicion_certificada as exp

ANA = {"nombre": "ANA LOPEZ", "direccion": "C Mayor 1", "poblacion": "Madrid",
       "provincia": "Madrid", "cp": "28001", "email": "ana@x.es", "movil": "665130883"}


class _CodicertFalso:
    """Doble del transporte. Cuenta lo que se manda y no toca la red."""

    def __init__(self, credito=Decimal("100"), listado=()):
        self.credito_ = credito
        self.listado = list(listado)
        self.enviados: list[tuple[str, str]] = []

    def credito(self): return self.credito_
    def listar(self, **_): return list(self.listado)

    def enviar_burofax(self, **kw):
        self.enviados.append(("burofax", kw["id_personalizado"])); return "B1"

    def enviar_eec(self, **kw):
        self.enviados.append((kw["tipo_entrega"], kw["id_personalizado"])); return "E1"


def _entorno(tmp_path, cod=None, partes=(ANA,)):
    return exp.EntornoExpedicion(
        codicert=cod or _CodicertFalso(),
        partes_de=lambda _w: list(partes),
        ahora=lambda: dt.datetime(2026, 9, 17, 12, 0, tzinfo=dt.timezone.utc),
        raiz=tmp_path)


def _doc(tmp_path):
    d = tmp_path / "A.pdf"; d.write_bytes(b"%PDF A")
    return [d]


def test_planificar_resuelve_identificador_coste_y_ausencias(tmp_path):
    plan = exp.planificar("W-04AKM2", "OVC", _doc(tmp_path), entorno_exp=_entorno(tmp_path),
                          plaza="Madrid")
    assert plan.id_personalizado == "W-04AKM2 - OVC"
    assert plan.coste == exp.coste_de(plan.envios)
    assert len(plan.envios) == 3


def test_ejecutar_sin_confirmacion_NO_manda_nada(tmp_path):
    cod = _CodicertFalso()
    ent = _entorno(tmp_path, cod)
    plan = exp.planificar("W-04AKM2", "OVC", _doc(tmp_path), entorno_exp=ent, plaza="Madrid")
    with pytest.raises(exp.ExpedicionError):
        exp.ejecutar(plan, exp.Confirmacion(digest="digest-que-no-es"), entorno_exp=ent)
    assert cod.enviados == []


def test_ejecutar_con_la_confirmacion_del_plan_manda_los_tres(tmp_path):
    cod = _CodicertFalso()
    ent = _entorno(tmp_path, cod)
    plan = exp.planificar("W-04AKM2", "OVC", _doc(tmp_path), entorno_exp=ent, plaza="Madrid")
    exp.ejecutar(plan, exp.Confirmacion(digest=plan.digest), entorno_exp=ent)
    assert sorted(c for c, _ in cod.enviados) == ["burofax", "correo", "sms"]
    assert {i for _, i in cod.enviados} == {"W-04AKM2 - OVC"}


def test_un_plan_rancio_se_rechaza_si_el_CRM_cambio(tmp_path):
    cod = _CodicertFalso()
    ent = _entorno(tmp_path, cod)
    plan = exp.planificar("W-04AKM2", "OVC", _doc(tmp_path), entorno_exp=ent, plaza="Madrid")
    otro = exp.EntornoExpedicion(codicert=cod, ahora=ent.ahora, raiz=ent.raiz,
                                 partes_de=lambda _w: [{**ANA, "direccion": "OTRA CALLE 9"}])
    with pytest.raises(exp.ExpedicionError) as e:
        exp.ejecutar(plan, exp.Confirmacion(digest=plan.digest), entorno_exp=otro)
    assert "cambiado" in str(e.value).lower()
    assert cod.enviados == []


def test_no_repite_lo_que_la_plataforma_ya_tiene(tmp_path):
    cod = _CodicertFalso(listado=[{"id": "x", "id_personalizado": "W-04AKM2 - OVC"}])
    ent = _entorno(tmp_path, cod)
    plan = exp.planificar("W-04AKM2", "OVC", _doc(tmp_path), entorno_exp=ent, plaza="Madrid")
    with pytest.raises(exp.ExpedicionError) as e:
        exp.ejecutar(plan, exp.Confirmacion(digest=plan.digest), entorno_exp=ent)
    assert "ya existe" in str(e.value).lower()
    assert cod.enviados == []


def test_sin_credito_suficiente_el_plan_nace_NO_ejecutable(tmp_path):
    ent = _entorno(tmp_path, _CodicertFalso(credito=Decimal("1")))
    plan = exp.planificar("W-04AKM2", "OVC", _doc(tmp_path), entorno_exp=ent, plaza="Madrid")
    assert plan.ejecutable is False
    with pytest.raises(exp.ExpedicionError):
        exp.ejecutar(plan, exp.Confirmacion(digest=plan.digest), entorno_exp=ent)


def test_un_pendiente_de_otro_expediente_no_bloquea_este(tmp_path):
    """`exigir_sin_pendientes` se acota al `id_personalizado` que se ejecuta (spec §4.3):
    un pendiente anotado para OTRO expediente no debe impedir esta expedición.

    Firma viva de `RegistroIntencion.exigir_sin_pendientes(id_personalizado=None)`: el
    brief del task traía `registro.exigir_sin_pendientes()` sin acotar, desactualizado
    tras las rondas de revisión que movieron esta firma.
    """
    cod = _CodicertFalso()
    ent = _entorno(tmp_path, cod)
    exp.RegistroIntencion(tmp_path / "_codicert_intencion.jsonl").anotar(
        "W-OTRO - REQ", "burofax", "alguien")
    plan = exp.planificar("W-04AKM2", "OVC", _doc(tmp_path), entorno_exp=ent, plaza="Madrid")
    ids = exp.ejecutar(plan, exp.Confirmacion(digest=plan.digest), entorno_exp=ent)
    assert len(ids) == 3


def test_un_pendiente_del_MISMO_expediente_si_bloquea(tmp_path):
    """El mismo mecanismo, pero con el pendiente anotado para ESTA expedición: sí debe
    bloquear el envío en vez de arriesgar un duplicado."""
    cod = _CodicertFalso()
    ent = _entorno(tmp_path, cod)
    exp.RegistroIntencion(tmp_path / "_codicert_intencion.jsonl").anotar(
        "W-04AKM2 - OVC", "burofax", "alguien")
    plan = exp.planificar("W-04AKM2", "OVC", _doc(tmp_path), entorno_exp=ent, plaza="Madrid")
    with pytest.raises(exp.ExpedicionError):
        exp.ejecutar(plan, exp.Confirmacion(digest=plan.digest), entorno_exp=ent)
    assert cod.enviados == []
