"""El registro de intención: un timeout no puede perder un burofax pagado."""
from __future__ import annotations

import json
from datetime import datetime

import pytest

from core import expedicion_certificada as exp


def test_el_registro_NO_persiste_datos_personales(tmp_path):
    """`SEGURIDAD_DATOS` §7: una persona no se escribe a disco por su nombre."""
    ruta = tmp_path / "intencion.jsonl"
    exp.RegistroIntencion(ruta).anotar(
        "W-1 - REQ", "burofax", "ANA LOPEZ · ana@correo.es · 34665130883")
    crudo = ruta.read_text(encoding="utf-8")
    for pii in ("ANA LOPEZ", "ana@correo.es", "34665130883"):
        assert pii not in crudo
    # El id_personalizado es un código de expediente, no un dato personal: va en claro.
    assert "W-1 - REQ" in crudo


def test_anotar_antes_del_post_y_cerrar_despues(tmp_path):
    reg = exp.RegistroIntencion(tmp_path / "intencion.jsonl")
    clave = reg.anotar("W-1 - REQ", "burofax", "ANA · C Mayor 1")
    assert reg.en_vuelo() and reg.hechos() == set()
    reg.cerrar(clave, "006ar9bel3n")
    assert reg.en_vuelo() == [] and reg.hechos() == {"006ar9bel3n"}


def test_un_en_vuelo_sin_id_sobrevive_al_reinicio(tmp_path):
    ruta = tmp_path / "intencion.jsonl"
    exp.RegistroIntencion(ruta).anotar("W-1 - REQ", "burofax", "ANA")
    assert len(exp.RegistroIntencion(ruta).en_vuelo()) == 1


def test_anotar_persiste_id_personalizado_y_timestamp_iso_utc(tmp_path):
    """El diseño (§4.3) exige `(id_personalizado, canal, destinatario, timestamp,
    en_vuelo)` antes de cada POST. Sin `id_personalizado` ni `timestamp`, quien lea un
    "SIN VERIFICAR" no sabe de qué expedición era el pendiente ni cuándo se abrió.
    """
    ruta = tmp_path / "intencion.jsonl"
    reg = exp.RegistroIntencion(ruta)
    clave = reg.anotar("W-1 - REQ", "burofax", "ANA")
    fila = json.loads(ruta.read_text(encoding="utf-8").splitlines()[0])
    assert fila["clave"] == clave
    assert fila["id_personalizado"] == "W-1 - REQ"
    marca = datetime.fromisoformat(fila["timestamp"])
    offset = marca.utcoffset()
    assert offset is not None and offset.total_seconds() == 0


def test_en_vuelo_acotado_por_id_personalizado(tmp_path):
    """`en_vuelo()` puede acotarse a una sola expedición: sin el parámetro, mira todo."""
    reg = exp.RegistroIntencion(tmp_path / "i.jsonl")
    reg.anotar("W-1 - REQ", "burofax", "ANA")
    reg.anotar("W-2 - REQ", "burofax", "BEA")
    assert len(reg.en_vuelo()) == 2
    acotado = reg.en_vuelo("W-1 - REQ")
    assert [f["id_personalizado"] for f in acotado] == ["W-1 - REQ"]


def test_exigir_sin_pendientes_acotado_por_id_personalizado(tmp_path):
    """`exigir_sin_pendientes()` acotado no debe reaccionar a pendientes de OTRO expediente."""
    reg = exp.RegistroIntencion(tmp_path / "i.jsonl")
    reg.anotar("W-1 - REQ", "burofax", "ANA")
    reg.exigir_sin_pendientes("W-2 - REQ")  # no lanza: el pendiente es de otra expedición
    with pytest.raises(exp.ExpedicionError):
        reg.exigir_sin_pendientes("W-1 - REQ")
    with pytest.raises(exp.ExpedicionError):
        reg.exigir_sin_pendientes()


def test_linea_corrupta_lanza_expedicionerror_con_fichero_y_linea(tmp_path):
    """Un corte a mitad de `write` deja la última línea truncada. Esta pieza existe para
    no perder el rastro de un envío ya pagado: la línea ilegible no se ignora en
    silencio, se declara con fichero y número de línea para que un humano la mire.
    """
    ruta = tmp_path / "intencion.jsonl"
    buena = json.dumps({"clave": "a", "id_personalizado": "W-1 - REQ", "canal": "burofax",
                         "destinatario_huella": "x", "timestamp": "2026-09-17T00:00:00+00:00",
                         "estado": "en_vuelo"})
    ruta.write_text(buena + "\n{esto no es json\n", encoding="utf-8", newline="\n")
    reg = exp.RegistroIntencion(ruta)
    with pytest.raises(exp.ExpedicionError) as e:
        reg.en_vuelo()
    mensaje = str(e.value)
    assert str(ruta) in mensaje
    assert "línea 2" in mensaje


def test_cerrar_la_misma_clave_dos_veces_lanza_error(tmp_path):
    """Justo la pieza que existe para detectar duplicados no puede ser ciega ante uno
    en su propio punto de cierre: `hechos()` no puede devolver dos ids como si fueran
    dos envíos legítimos.
    """
    reg = exp.RegistroIntencion(tmp_path / "i.jsonl")
    clave = reg.anotar("W-1 - REQ", "burofax", "ANA")
    reg.cerrar(clave, "id1")
    with pytest.raises(exp.ExpedicionError):
        reg.cerrar(clave, "id2")
    assert reg.hechos() == {"id1"}


def test_dos_anotaciones_abiertas_cerrar_una_no_deja_en_vuelo_la_otra(tmp_path):
    """Regresión dirigida: sustituir `abiertas.pop(clave, None)` por `abiertas.clear()`
    en `en_vuelo()` pasaría los tests previos porque ninguno tenía dos anotaciones
    vivas a la vez. Esta sí, y debe distinguir cuál se cerró.
    """
    reg = exp.RegistroIntencion(tmp_path / "i.jsonl")
    c1 = reg.anotar("W-1 - REQ", "burofax", "ANA")
    c2 = reg.anotar("W-1 - REQ", "sms", "BEA")
    reg.cerrar(c1, "id1")
    abiertas = reg.en_vuelo()
    assert len(abiertas) == 1
    assert abiertas[0]["clave"] == c2


def test_cerrar_clave_huerfana_sin_anotacion_previa_lanza_error(tmp_path):
    reg = exp.RegistroIntencion(tmp_path / "i.jsonl")
    with pytest.raises(exp.ExpedicionError):
        reg.cerrar("clave-que-nunca-se-anoto", "id1")


def test_ya_expedido_solo_cuenta_el_id_personalizado_pedido():
    listado = [{"id": "a", "id_personalizado": "W-1 - REQ", "tipo": "b"},
               {"id": "b", "id_personalizado": "W-1 - OVC", "tipo": "b"},
               {"id": "c", "id_personalizado": "W-1 - REQ", "tipo": "ce"}]
    assert exp.ya_expedido(listado, "W-1 - REQ") == {"a", "c"}


def test_la_ovc_NO_se_confunde_con_el_requerimiento_del_mismo_expediente():
    listado = [{"id": "a", "id_personalizado": "W-1 - REQ"}]
    assert exp.ya_expedido(listado, "W-1 - OVC") == set()


def test_un_en_vuelo_pendiente_bloquea_la_ejecucion(tmp_path):
    reg = exp.RegistroIntencion(tmp_path / "i.jsonl")
    reg.anotar("W-1 - REQ", "burofax", "ANA")
    with pytest.raises(exp.ExpedicionError) as e:
        reg.exigir_sin_pendientes()
    assert "SIN VERIFICAR" in str(e.value)


def test_exigir_sin_pendientes_mensaje_incluye_clave_y_timestamp(tmp_path):
    """Dos pendientes del mismo canal con la misma huella solo se distinguen por su
    clave y su timestamp: sin ellos, el mensaje no le dice al humano cuál es cuál.
    """
    ruta = tmp_path / "i.jsonl"
    reg = exp.RegistroIntencion(ruta)
    clave = reg.anotar("W-1 - REQ", "burofax", "ANA")
    fila = json.loads(ruta.read_text(encoding="utf-8").splitlines()[0])
    with pytest.raises(exp.ExpedicionError) as e:
        reg.exigir_sin_pendientes()
    mensaje = str(e.value)
    assert clave in mensaje
    assert fila["timestamp"] in mensaje
