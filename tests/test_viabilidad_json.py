"""El contrato del JSON de viabilidad, y su validador.

Los cinco defectos que se prueban aqui son los que `MEJORAS #262` publico como
contrato «derivado por ejecucion» y que resultaron INCORRECTOS, medidos el
2026-09-15 corriendo el consumidor real. Cada `test_rechaza_*` es uno de ellos.

Spec: docs/superpowers/specs/2026-09-15-corrida-prepara-sesion-remata-design.md §2.
"""
import pytest

from core import viabilidad_json as vj


def _valido():
    """Un JSON minimo que el contrato acepta."""
    return {
        "case_id": "BaRS9 - Calle de Prueba 1 (W-TEST01) - Vuelta",
        "ref": "W-TEST01",
        "fecha": "2026-09-15",
        "equipo": {"director_captador": "", "asesor_captador": "",
                   "director_buscador": "", "asesor_buscador": ""},
        "observaciones": "Vuelta",
        "importes": {},
        "hitos": {},
        "preguntas": {},
        "actividades": {},
        "motivos_impago": "",
        "avisos": [],
        "bitacora_inicial": True,
        vj.MARCA: {"campos": [], "por_que": {}},
    }


def test_un_json_bien_formado_no_tiene_problemas():
    assert vj.validar(_valido()) == []


def test_rechaza_importes_con_las_claves_de_la_262():
    """H1, el defecto caro: `principal/costas/intereses` NO existen para el consumidor,
    que lee `precio/pct_honorarios/pagos_parciales/propuesta_pago`. Medido: con
    `principal: 12000` la celda H13 queda vacia y el script imprime OK."""
    d = _valido()
    d["importes"] = {"principal": 12000, "costas": 500, "intereses": 300}

    problemas = vj.validar(d)

    assert any("principal" in p for p in problemas)
    assert any("precio" in p for p in problemas), "el error debe decir cual es la buena"


def test_rechaza_motivos_impago_como_lista():
    """El consumidor hace `.strip()` y `.upper()`: una lista revienta con AttributeError."""
    d = _valido()
    d["motivos_impago"] = ["no reconoce la intermediacion"]

    assert any("motivos_impago" in p for p in vj.validar(d))


def test_rechaza_actividades_como_lista():
    """El consumidor hace `.get()`: una lista revienta con AttributeError."""
    d = _valido()
    d["actividades"] = [{"exposes_propiedad": 3}]

    assert any("actividades" in p for p in vj.validar(d))


def test_rechaza_bitacora_inicial_como_texto():
    """El consumidor la usa como BOOLEANO: el texto se descarta y se escribe uno fijo.
    Aceptar una cadena haria creer que ese texto viaja al informe."""
    d = _valido()
    d["bitacora_inicial"] = "mi texto"

    assert any("bitacora_inicial" in p for p in vj.validar(d))


def test_rechaza_avisos_como_lista_de_cadenas():
    """`avisos` es lista de OBJETOS: el consumidor hace `a.get("n")` sobre cada uno."""
    d = _valido()
    d["avisos"] = ["algo pasa"]

    assert any("avisos" in p for p in vj.validar(d))


def test_rechaza_equipo_como_texto():
    d = _valido()
    d["equipo"] = "APELLIDO, Nombre"

    assert any("equipo" in p for p in vj.validar(d))


def test_avisa_de_una_clave_de_equipo_que_no_existe():
    d = _valido()
    d["equipo"]["director_comercial"] = "X"

    assert any("director_comercial" in p for p in vj.validar(d))


def test_avisa_de_un_campo_de_primer_nivel_desconocido():
    d = _valido()
    d["importe_total"] = 1

    assert any("importe_total" in p for p in vj.validar(d))


def test_el_validador_puede_dar_los_DOS_valores():
    """Control positivo. Un validador que solo se ha visto decir «bien» no acredita
    nada: es el defecto que dejo pasar los cinco campos de #262."""
    assert vj.validar(_valido()) == []
    assert vj.validar({**_valido(), "motivos_impago": []}) != []
