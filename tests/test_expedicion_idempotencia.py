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


# ---------------------------------------------------------------------------------
# H-07 (medio, estructural; revisión adversarial r2). `cerrar()` solo sabe resolver
# una intención con un IdEnvio real. Un rechazo DEFINITIVO -- del que sabemos con
# certeza que no salió -- necesita su PROPIA transición persistida, que la deje
# fuera de `en_vuelo()` sin inventar un identificador ni contarla como `hecho()`.
# ---------------------------------------------------------------------------------

def test_rechazar_cierra_la_intencion_sin_inventar_un_id_de_envio(tmp_path):
    reg = exp.RegistroIntencion(tmp_path / "i.jsonl")
    clave = reg.anotar("W-1 - REQ", "burofax", "ANA")
    reg.rechazar(clave, motivo="422: datos inválidos")
    assert reg.en_vuelo() == []       # ya no bloquea una reanudación
    assert reg.hechos() == set()      # tampoco se cuenta como un envío real


def test_rechazar_una_clave_que_no_esta_en_vuelo_lanza_error(tmp_path):
    reg = exp.RegistroIntencion(tmp_path / "i.jsonl")
    with pytest.raises(exp.ExpedicionError):
        reg.rechazar("clave-que-nunca-se-anoto", motivo="422")


def test_rechazar_dos_veces_la_misma_clave_lanza_error(tmp_path):
    reg = exp.RegistroIntencion(tmp_path / "i.jsonl")
    clave = reg.anotar("W-1 - REQ", "burofax", "ANA")
    reg.rechazar(clave, motivo="422")
    with pytest.raises(exp.ExpedicionError):
        reg.rechazar(clave, motivo="422 otra vez")


# ---------------------------------------------------------------------------------
# H-15 (medio, acotado; revisión adversarial r2). Se detectaba JSON sintácticamente
# inválido, pero no se validaba ni el esquema ni la secuencia de transiciones: en
# `en_vuelo()`, CUALQUIER estado distinto de "en_vuelo" se interpretaba como un
# cierre legítimo, y los cierres duplicados solo se impedían llamando a `cerrar()`
# -- no si ya venían escritos en el fichero.
# ---------------------------------------------------------------------------------

def test_H15_un_estado_desconocido_para_declarando_fichero_y_linea(tmp_path):
    """Tras una intención legítima, una línea JSON VÁLIDA con la MISMA clave y un
    estado mal escrito ("hehco", un typo real) no debe hacer que el pendiente
    desaparezca en silencio de los dos controles a la vez -- antes, `en_vuelo()`
    lo daba por cerrado (cualquier estado que no fuera "en_vuelo" cerraba) y
    `hechos()` no lo reconocía (exige la cadena exacta "hecho"): el rastro del
    envío se esfumaba sin aviso. Un estado que no se entiende no puede consumirse
    como si cerrara la intención: debe pararse, igual que ya hace el JSON
    ilegible."""
    ruta = tmp_path / "i.jsonl"
    reg = exp.RegistroIntencion(ruta)
    clave = reg.anotar("W-1 - REQ", "burofax", "ANA")
    with ruta.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps({"clave": clave, "estado": "hehco", "id_envio": "x"}) + "\n")

    with pytest.raises(exp.ExpedicionError) as e:
        reg.en_vuelo()
    mensaje = str(e.value)
    assert str(ruta) in mensaje
    assert "línea 2" in mensaje

    with pytest.raises(exp.ExpedicionError):
        reg.hechos()  # tampoco se cuela como "hecho": ningún control lo da por bueno


def test_H15_dos_cierres_para_la_misma_clave_paran_en_vez_de_explicar_los_dos(tmp_path):
    """Dos líneas de cierre "hecho" para la MISMA clave, con IdEnvio distintos --
    corrupción que la API en vivo no permite (`cerrar()` comprueba que la clave
    siga en vuelo antes de escribir), pero que un fichero reparado a mano o
    importado sí puede traer ya escrita. Antes, `ids_hechos_de()` devolvía LAS DOS
    como envíos explicados: un cierre duplicado se contaba dos veces como si
    fueran dos envíos legítimos -- justo lo que este registro existe para
    detectar."""
    ruta = tmp_path / "i.jsonl"
    reg = exp.RegistroIntencion(ruta)
    clave = reg.anotar("W-1 - REQ", "burofax", "ANA")
    reg.cerrar(clave, "id-legitimo")
    with ruta.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps({"clave": clave, "estado": "hecho", "id_envio": "id-fantasma"}) + "\n")

    with pytest.raises(exp.ExpedicionError) as e:
        reg.ids_hechos_de("W-1 - REQ")
    mensaje = str(e.value)
    assert str(ruta) in mensaje
    assert "línea 3" in mensaje


def test_H15_un_cierre_sin_apertura_previa_es_huerfano_y_para(tmp_path):
    """Una línea "hecho" para una clave que NUNCA se anotó "en_vuelo" -- un
    fichero reparado a mano que perdió la línea de apertura, por ejemplo -- no
    debe aceptarse como un envío explicado: no hay con qué contrastarla."""
    ruta = tmp_path / "i.jsonl"
    ruta.write_text(
        json.dumps({"clave": "nunca-anotada", "estado": "hecho", "id_envio": "x"}) + "\n",
        encoding="utf-8", newline="\n")
    reg = exp.RegistroIntencion(ruta)
    with pytest.raises(exp.ExpedicionError) as e:
        reg.hechos()
    assert str(ruta) in str(e.value)
    assert "línea 1" in str(e.value)
