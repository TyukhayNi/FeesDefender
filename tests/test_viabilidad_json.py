"""El contrato del JSON de viabilidad, y su validador.

Los cuatro defectos que se prueban aqui son los que `MEJORAS #262` publico como
contrato «derivado por ejecucion» y que resultaron INCORRECTOS, medidos el
2026-09-15 corriendo el consumidor real. Cada `test_rechaza_*` es uno de ellos.

Spec: docs/superpowers/specs/2026-09-15-corrida-prepara-sesion-remata-design.md §2.
"""
import json

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


@pytest.mark.parametrize("valor", [{"cantidad": 12000}, [12000]],
                         ids=["objeto_anidado", "lista"])
def test_rechaza_un_valor_de_importes_que_el_consumidor_no_puede_escribir(valor):
    """H-03 de la revisión adversarial (2026-09-15): `validar` comprobaba el NOMBRE de
    la clave de `importes` pero no el TIPO de su valor. `{"precio": {"cantidad":
    12000}}` pasaba entera -"precio" es una clave válida-, `escribir` la persistía, y
    el consumidor (`render_informe.py`) moría con `ValueError: Cannot convert {...} to
    Excel` ya con el fichero escrito. La clave sigue siendo la correcta: lo que falla
    es su forma."""
    d = _valido()
    d["importes"] = {"precio": valor}

    problemas = vj.validar(d)

    assert any("importes.precio" in p for p in problemas)


def test_el_validador_admite_los_tipos_que_SI_caben_en_una_celda():
    """Control positivo del de arriba: la validación de tipo no puede volverse una
    validación de negocio. Texto, número, cero y booleano son formas legítimas de un
    importe (una nota, un porcentaje con decimales, un pago a cero, un booleano
    heredado de un JSON de origen) y ninguna debe rechazarse."""
    d = _valido()
    d["importes"] = {"precio": "12.000 €", "pct_honorarios": 5.5,
                     "pagos_parciales": 0, "propuesta_pago": False}

    assert vj.validar(d) == []


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
    nada: es el defecto que dejo pasar los cuatro campos de #262."""
    assert vj.validar(_valido()) == []
    assert vj.validar({**_valido(), "motivos_impago": []}) != []


class _Ident:
    case_id = "BaRS9 - Calle de Prueba 1 (W-TEST01) - Vuelta"
    w_code = "W-TEST01"
    tipo_caso = "Vuelta"


def test_preparar_rellena_los_cuatro_derivables():
    d = vj.preparar(_Ident(), hoy="2026-09-15")

    assert d["case_id"] == "BaRS9 - Calle de Prueba 1 (W-TEST01) - Vuelta"
    assert d["ref"] == "W-TEST01"
    assert d["fecha"] == "2026-09-15"
    assert d["observaciones"] == "Vuelta"


def test_preparar_deja_el_equipo_VACIO_y_nunca_inventado():
    """H2: el rol no existe como dato en la apertura. Medido sobre 10 fichas reales y
    25 colaboradores: cero claves de rol, cargo o lado. Rellenarlo seria inventar."""
    d = vj.preparar(_Ident(), hoy="2026-09-15")

    assert set(d["equipo"]) == set(vj.CLAVES_EQUIPO)
    assert all(v == "" for v in d["equipo"].values())


def test_lo_que_preparar_produce_es_valido():
    """El productor y el validador tienen que estar de acuerdo, o uno de los dos miente."""
    assert vj.validar(vj.preparar(_Ident(), hoy="2026-09-15")) == []


def test_la_marca_nombra_lo_que_falta_y_por_que():
    """Un esqueleto vacio sin marca es indistinguible de un JSON que alguien creyo
    completo. Y un valor vacio es ambiguo: no distingue «nadie lo puso» de «se miro y
    no habia»."""
    d = vj.preparar(_Ident(), hoy="2026-09-15")
    marca = d[vj.MARCA]

    assert "equipo" in marca["campos"]
    assert "hitos" in marca["campos"] and "preguntas" in marca["campos"]
    assert "case_id" not in marca["campos"], "lo derivado no es residuo"
    assert "_ficha_crm.yaml" in marca["por_que"]["equipo"], (
        "la razon de `equipo` es distinta de las demas: el dato NO EXISTE en la "
        "apertura, no es que haya que leer el expediente")


def test_escribir_deja_el_fichero_donde_vive_el_protocolo(tmp_path):
    (tmp_path / "00_Input").mkdir()

    p = vj.escribir(tmp_path, vj.preparar(_Ident(), hoy="2026-09-15"))

    assert p == tmp_path / "00_Input" / "_viabilidad.json"
    assert json.loads(p.read_text(encoding="utf-8"))["ref"] == "W-TEST01"


def test_escribir_NUNCA_sobrescribe(tmp_path):
    """Lo unico caro de este fichero es lo que puso la sesion que lo remato. Un
    reintento que lo pisa destruye justo eso."""
    (tmp_path / "00_Input").mkdir()
    p = vj.ruta(tmp_path)
    p.write_text('{"ref": "LO QUE PUSO LA SESION"}', encoding="utf-8")

    with pytest.raises(FileExistsError):
        vj.escribir(tmp_path, vj.preparar(_Ident(), hoy="2026-09-15"))

    assert "LO QUE PUSO LA SESION" in p.read_text(encoding="utf-8")


def test_escribir_no_valida_a_medias_deja_el_fichero(tmp_path):
    """Si el JSON no cumple el contrato no se escribe NADA: un fichero a medias es
    peor que ninguno, porque bloquea el reintento sin contener el trabajo."""
    (tmp_path / "00_Input").mkdir()

    with pytest.raises(ValueError):
        vj.escribir(tmp_path, {"motivos_impago": []})

    assert not vj.ruta(tmp_path).exists()


# ---------------------------------------------------------------------------
# Escritura atómica: el caso intermedio que el pliego original de Task 5 no cubría
# -JSON VÁLIDO pero la escritura a disco falla A MITAD- está protegido por el
# temporal+rename de `escribir()` (informe: .superpowers/sdd/task-5-report.md,
# sección "Fix: la escritura se vuelve atomica").
# ---------------------------------------------------------------------------

def test_escribir_no_deja_fichero_a_medias_si_la_escritura_falla(tmp_path, monkeypatch):
    """La garantía del docstring de `escribir` ('nunca deja un fichero a medias') cubre
    también un fallo de IO real a mitad de la escritura, no solo el rechazo por
    contrato (ver el test anterior): el temporal+rename hace que un fallo aquí no deje
    ni el destino ni un temporal huérfano.
    """
    (tmp_path / "00_Input").mkdir()
    datos = vj.preparar(_Ident(), hoy="2026-09-15")
    if vj.validar(datos) != []:
        raise RuntimeError(
            "precondicion: datos debe pasar validar(); si no, este test probaria el "
            "rechazo por contrato (ya cubierto arriba), no el fallo de IO")

    def _falla_a_medias(self, data, encoding=None, errors=None, newline=None):
        """Simula lo que deja un ENOSPC/IOError real: algunos bytes SI llegan a disco
        antes de que el fallo interrumpa la escritura. Intercepta el write_text de
        CUALQUIER Path: hoy le toca al temporal, no al destino, porque escribir() ya
        no escribe el destino directamente."""
        self.write_bytes(data[:20].encode(encoding or "utf-8"))
        raise OSError(28, "No space left on device (simulado)")

    monkeypatch.setattr(vj.Path, "write_text", _falla_a_medias)

    try:
        vj.escribir(tmp_path, datos)
    except OSError:
        pass
    else:
        raise RuntimeError(
            "precondicion: la escritura simulada no fallo; este test no esta "
            "probando un fallo de IO a mitad")

    # --- los dos asertos normativos: ni el destino ni un temporal sobreviven al fallo.
    destino = vj.ruta(tmp_path)
    assert not destino.exists(), (
        f"escribir() dejó {destino} a medias tras un fallo de IO simulado.")
    restos = list(destino.parent.iterdir())
    assert restos == [], (
        f"escribir() dejó temporales huérfanos tras el fallo: {restos!r}")


# ---------------------------------------------------------------------------
# La carrera del destino: un revisor reprodujo que `escribir()` SÍ sobrescribía si
# el destino aparecía entre la comprobación inicial y el `os.replace` final -la
# ventana se ensanchó justo al pasar a temporal+rename (caben `mkstemp`, `close` y la
# escritura del temporal). Informe: .superpowers/sdd/task-5-report.md, sección
# "Fix: la carrera del destino".
# ---------------------------------------------------------------------------

def test_escribir_no_deja_huerfanos_si_falla_el_commit_final(tmp_path, monkeypatch):
    """Hueco de cobertura que señaló el revisor: el fallo de IO ya estaba cubierto en
    la escritura del temporal (test anterior), pero no en el OTRO tramo -el propio
    acto de publicar, antes `os.replace`, ahora `os.link`-, que es justo donde vivía
    la carrera que arregla este fix. Un fallo ahí tampoco debe dejar el destino a
    medias ni un temporal huérfano."""
    (tmp_path / "00_Input").mkdir()
    datos = vj.preparar(_Ident(), hoy="2026-09-15")
    if vj.validar(datos) != []:
        raise RuntimeError(
            "precondición: datos debe pasar validar(); si no, este test probaría el "
            "rechazo por contrato, no un fallo en el commit final")

    def _falla_el_commit(src, dst):
        raise OSError(5, "fallo de E/S simulado en el commit final (no es la carrera)")

    monkeypatch.setattr(vj.os, "link", _falla_el_commit)

    try:
        vj.escribir(tmp_path, datos)
    except FileExistsError:
        raise RuntimeError(
            "precondición: el fallo simulado no debe ser FileExistsError -eso "
            "prueba la carrera (otro test), no un fallo de commit genérico")
    except OSError:
        pass
    else:
        raise RuntimeError(
            "precondición: el commit simulado no falló; este test no está probando "
            "un fallo en el renombrado/commit final")

    destino = vj.ruta(tmp_path)
    assert not destino.exists(), (
        f"escribir() publicó {destino} pese a que el commit falló.")
    restos = list(destino.parent.iterdir())
    assert restos == [], (
        f"escribir() dejó temporales huérfanos tras el fallo de commit: {restos!r}")


def test_escribir_no_sobrescribe_si_el_destino_aparece_durante_la_escritura(
        tmp_path, monkeypatch):
    """El defecto que reprodujo el revisor: si el destino aparece DESPUÉS de la
    comprobación inicial de `destino.exists()` y ANTES del commit final, `escribir()`
    no debe pisarlo. Se abre esa ventana de forma determinista parcheando el
    `write_text` del temporal -el único paso que hoy ocurre en ese hueco-: nada más
    escribirse el temporal, una "sesión concurrente" crea el destino por su cuenta,
    exactamente como hizo el revisor para reproducirlo."""
    (tmp_path / "00_Input").mkdir()
    destino = vj.ruta(tmp_path)
    contenido_ajeno = '{"ref": "SESION CONCURRENTE"}'
    escritura_real = vj.Path.write_text
    colado = False

    def _cuela_una_escritura_concurrente(self, *args, **kwargs):
        nonlocal colado
        resultado = escritura_real(self, *args, **kwargs)
        if not colado:
            colado = True
            escritura_real(destino, contenido_ajeno, encoding="utf-8")
        return resultado

    monkeypatch.setattr(vj.Path, "write_text", _cuela_una_escritura_concurrente)

    if destino.exists():
        raise RuntimeError(
            "precondición: el destino no debía existir antes de llamar a escribir()")

    with pytest.raises(FileExistsError):
        vj.escribir(tmp_path, vj.preparar(_Ident(), hoy="2026-09-15"))

    if not colado:
        raise RuntimeError(
            "precondición: la escritura concurrente simulada no se coló; este test "
            "no está probando la carrera")

    assert destino.read_text(encoding="utf-8") == contenido_ajeno, (
        "escribir() pisó el contenido de la sesión concurrente: exactamente el "
        "defecto que reprodujo el revisor")
    restos = [p.name for p in destino.parent.iterdir()]
    assert restos == [destino.name], (
        f"escribir() dejó temporales huérfanos tras perder la carrera: {restos!r}")
