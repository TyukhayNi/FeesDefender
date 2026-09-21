"""El registro local de cosecha: la clave inmediata que sostiene la idempotencia."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from core import expedicion_certificada as exp


def _registro(tmp_path, entorno="produccion", usuario="madrid.bd"):
    return exp.RegistroCosecha(tmp_path / "_codicert_cosecha.jsonl",
                               entorno=entorno, usuario=usuario,
                               ahora=lambda: datetime(2026, 9, 21, tzinfo=timezone.utc))


def test_una_cosecha_cerrada_consta_como_hecha(tmp_path):
    r = _registro(tmp_path)
    r.reservar("006a", "uuid-1")
    r.cerrar("006a", doc_id="42990", sha256="ab" * 32)
    assert r.hecho("006a")["doc_id"] == "42990"


def test_lo_no_cosechado_no_consta(tmp_path):
    assert _registro(tmp_path).hecho("006a") is None


def test_una_reserva_SIN_cerrar_no_es_una_cosecha_hecha_y_se_declara(tmp_path):
    """El caso del timeout: el POST pudo salir. No se da por hecho ni por no hecho."""
    r = _registro(tmp_path)
    r.reservar("006a", "uuid-1")
    assert r.hecho("006a") is None
    assert [a["origen_id"] for a in r.abiertas()] == ["uuid-1"]


def test_una_reserva_ya_cerrada_deja_de_estar_abierta(tmp_path):
    r = _registro(tmp_path)
    r.reservar("006a", "uuid-1")
    r.cerrar("006a", doc_id="42990", sha256="ab" * 32)
    assert r.abiertas() == []


def test_una_cosecha_de_OTRO_entorno_no_cuenta(tmp_path):
    """Mismo fichero para sandbox y producción: sin esto, un cierre de sandbox
    haría creer que el certificado de producción ya está subido."""
    otro = _registro(tmp_path, entorno="sandbox")
    otro.reservar("006a", "uuid-1")
    otro.cerrar("006a", doc_id="1", sha256="cd" * 32)
    assert _registro(tmp_path, entorno="produccion").hecho("006a") is None


def test_una_cosecha_de_OTRA_cuenta_tampoco(tmp_path):
    otra = _registro(tmp_path, usuario="valencia.bd")
    otra.reservar("006a", "uuid-1")
    otra.cerrar("006a", doc_id="1", sha256="cd" * 32)
    assert _registro(tmp_path, usuario="madrid.bd").hecho("006a") is None


def test_no_guarda_datos_del_destinatario_en_claro(tmp_path):
    """`docs/SEGURIDAD_DATOS.md` §7: el dato personal no baja al registro."""
    r = _registro(tmp_path)
    r.reservar("006a", "uuid-1")
    r.cerrar("006a", doc_id="42990", sha256="ab" * 32)
    crudo = (tmp_path / "_codicert_cosecha.jsonl").read_text(encoding="utf-8")
    assert "@" not in crudo


def test_una_linea_corrupta_se_declara_con_su_numero(tmp_path):
    """Nunca se traga: puede ser el rastro de un documento ya creado."""
    ruta = tmp_path / "_codicert_cosecha.jsonl"
    ruta.write_text('{"clave":"006a"}\nesto no es json\n', encoding="utf-8")
    with pytest.raises(exp.ExpedicionError, match="línea 2"):
        exp.RegistroCosecha(ruta, entorno="produccion",
                            usuario="madrid.bd").hecho("006a")


def test_cerrar_sin_reservar_es_un_cierre_huerfano_y_se_para(tmp_path):
    r = _registro(tmp_path)
    with pytest.raises(exp.ExpedicionError, match="sin reserva|huérfan"):
        r.cerrar("006a", doc_id="42990", sha256="ab" * 32)
