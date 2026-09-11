"""El generador del informe de viabilidad marca las 88 filas, no solo las que recibe.

`render_informe.py` recorría `d["preguntas"]`: las preguntas que el JSON no traía
se quedaban **sin** la marca «¿PENDIENTE ENTREVISTA?» de la columna M, que es lo que
filtra el guion de entrevista. Medido dos veces el 2026-09-10: **51 de 88** filas
marcadas en W-048UOL y **70 de 88** en W-02YZO4 (`MEJORAS`, fila #28 de `PLAN.md`,
pieza P5). Un informe con 37 filas en blanco no se lee como «37 pendientes»: se lee
como «sin cuestionario», que es lo contrario.

Los tests corren contra la **plantilla real** de `assets/` —el defecto vivía en la
relación entre el JSON y esa plantilla, así que un fixture sintético lo rodearía—, que
solo se **lee**. Todo lo que estos tests escriben va a `tmp_path`: nada toca el árbol de
producción. (La R1 midió que openpyxl crea además sus propios temporales en el directorio
temporal del proceso al serializar el libro; eso no es el árbol de producción, pero la
frase «siempre en tmp_path» se leía como si lo cubriera todo.)
"""
import json
import sys
from importlib import import_module
from pathlib import Path

import openpyxl
import pytest

RAIZ = Path(__file__).parent.parent
SCRIPTS = RAIZ / ".claude" / "skills" / "viabilidad-prerelleno" / "scripts"
PLANTILLA = RAIZ / ".claude" / "skills" / "viabilidad-prerelleno" / "assets" / "plantilla_informe_viabilidad.xlsx"

sys.path.insert(0, str(SCRIPTS))
render_informe = import_module("render_informe")

COL_RESPUESTA = 9    # I
COL_PENDIENTE = 13   # M

# Tres ids reales de la plantilla, del primer bloque del cuestionario.
TRES_IDS = ["cap_01", "cap_02", "cap_03"]


def _generar(tmp_path, datos: dict) -> Path:
    """Corre el generador como lo corre la skill y devuelve el .xlsx de salida."""
    entrada = tmp_path / "datos.json"
    entrada.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    salida = tmp_path / "Informe viabilidad LLM - W-TEST00.xlsx"
    argv = ["render_informe.py", str(entrada), "--salida", str(salida)]
    orig, sys.argv = sys.argv, argv
    try:
        render_informe.main()
    finally:
        sys.argv = orig
    return salida


def _mapa_de_la_plantilla() -> dict[str, int]:
    wb = openpyxl.load_workbook(PLANTILLA, read_only=True)
    try:
        return render_informe.build_id_row_map(wb["PREGUNTAS"])
    finally:
        wb.close()


def test_la_plantilla_declara_88_preguntas():
    """El «88» del que habla la pieza sale de la plantilla, no de la memoria.

    Si la plantilla cambia de cuestionario, este test lo dice en vez de dejar que
    los demás se ajusten solos al número nuevo.
    """
    assert len(_mapa_de_la_plantilla()) == 88


@pytest.fixture
def informe_con_tres_respuestas(tmp_path):
    datos = {
        "case_id": "W-TEST00",
        "preguntas": {qid: {"respuesta": f"respuesta documental {i}",
                            "cita": "[doc: prueba.pdf] cita",
                            "confianza": "alta"}
                      for i, qid in enumerate(TRES_IDS, 1)},
    }
    salida = _generar(tmp_path, datos)
    wb = openpyxl.load_workbook(salida)
    yield wb["PREGUNTAS"]
    wb.close()


def test_las_88_filas_salen_marcadas(informe_con_tres_respuestas):
    """La propiedad: ninguna pregunta del cuestionario queda sin marca.

    ROJO antes del arreglo: salían 3 de 88, que es el mismo modo de fallo que
    el 51/88 y el 70/88 medidos en producción.
    """
    ws = informe_con_tres_respuestas
    id_row = render_informe.build_id_row_map(ws)
    sin_marcar = [qid for qid, r in id_row.items()
                  if ws.cell(r, COL_PENDIENTE).value in (None, "")]
    assert not sin_marcar, (
        f"{len(sin_marcar)} de {len(id_row)} preguntas sin «¿PENDIENTE ENTREVISTA?»: "
        f"{sorted(sin_marcar)[:8]}…")


def test_las_no_respondidas_van_al_guion_y_las_respondidas_no(informe_con_tres_respuestas):
    """`sí` es «al guion de entrevista»; `no` es «resuelta en documental»."""
    ws = informe_con_tres_respuestas
    id_row = render_informe.build_id_row_map(ws)
    marcas = {qid: ws.cell(r, COL_PENDIENTE).value for qid, r in id_row.items()}

    assert [marcas[q] for q in TRES_IDS] == ["no", "no", "no"]
    resto = {q: v for q, v in marcas.items() if q not in TRES_IDS}
    assert len(resto) == 85
    assert set(resto.values()) == {"sí"}


def test_no_inventa_respuestas_al_marcar(informe_con_tres_respuestas):
    """Marcar la pendiente NO es rellenar la respuesta.

    La columna I de las 85 no resueltas tiene que seguir vacía: el valor de la
    hoja es distinguir «pendiente» de «contestada», y escribir un placeholder en I
    borraría esa distinción.
    """
    ws = informe_con_tres_respuestas
    id_row = render_informe.build_id_row_map(ws)
    con_respuesta = [qid for qid, r in id_row.items()
                     if ws.cell(r, COL_RESPUESTA).value not in (None, "")]
    assert sorted(con_respuesta) == sorted(TRES_IDS)


def test_las_filas_de_seccion_no_se_manchan(informe_con_tres_respuestas):
    """La frontera: se marcan PREGUNTAS, no filas.

    La hoja intercala cabeceras de sección («1. Captación (encargo)») que llevan
    texto en B y la columna C vacía. `build_id_row_map` ya las deja fuera; este test
    fija esa frontera para que el barrido nuevo no la cruce.
    """
    ws = informe_con_tres_respuestas
    filas_pregunta = set(render_informe.build_id_row_map(ws).values())
    manchadas = [r for r in range(5, ws.max_row + 1)
                 if r not in filas_pregunta and ws.cell(r, COL_PENDIENTE).value not in (None, "")]
    assert not manchadas, f"filas sin ID con marca escrita: {manchadas}"


def test_pendiente_explicito_del_json_manda(tmp_path):
    """El JSON puede decir `pendiente: 'no'` sin respuesta, y eso gana.

    Es el caso de una pregunta resuelta por una vía que no deja respuesta en I
    (por ejemplo, «no aplica a este tipo de caso»). El barrido nuevo no puede
    pisar una decisión explícita.
    """
    datos = {
        "case_id": "W-TEST00",
        "preguntas": {"cap_01": {"pendiente": "no"},
                      "cap_02": {"respuesta": "sí", "pendiente": "sí"}},
    }
    salida = _generar(tmp_path, datos)
    wb = openpyxl.load_workbook(salida)
    try:
        ws = wb["PREGUNTAS"]
        id_row = render_informe.build_id_row_map(ws)
        assert ws.cell(id_row["cap_01"], COL_PENDIENTE).value == "no"
        assert ws.cell(id_row["cap_02"], COL_PENDIENTE).value == "sí"
    finally:
        wb.close()


def test_una_pregunta_ajena_al_cuestionario_sigue_avisando(tmp_path, capsys):
    """El aviso de `qid` desconocido no se pierde con el barrido nuevo."""
    datos = {"case_id": "W-TEST00",
             "preguntas": {"no_existe_99": {"respuesta": "x"}}}
    _generar(tmp_path, datos)
    assert "no_existe_99" in capsys.readouterr().err


def _validacion_de_la_columna_M(ws):
    """La validación que la plantilla declara sobre la columna M, buscada con rigor.

    La primera versión de este helper cogía la primera validación cuyo `sqref`
    contuviera la letra `M`, lo que casa con casi cualquier cosa. Se exige el tipo
    `list` y que el rango sea de la columna M.
    """
    candidatas = [d for d in ws.data_validations.dataValidation
                  if d.type == "list" and all(str(c).startswith("M")
                                              for c in str(d.sqref).split())]
    assert len(candidatas) == 1, f"esperaba UNA validación de lista en M: {candidatas}"
    return candidatas[0]


def test_las_marcas_caben_en_la_validacion_de_la_columna(informe_con_tres_respuestas):
    """`sí`/`no` son el dominio que la propia plantilla declara para M6:M103."""
    ws = informe_con_tres_respuestas
    dv = _validacion_de_la_columna_M(ws)
    dominio = set(dv.formula1.strip('"').split(","))
    id_row = render_informe.build_id_row_map(ws)
    assert set(id_row.values()) <= _filas_del_rango(dv), (
        "hay preguntas fuera del rango que la validación cubre")
    escritos = {ws.cell(r, COL_PENDIENTE).value for r in id_row.values()}
    assert escritos <= dominio, f"valores fuera de la validación {dominio}: {escritos - dominio}"


def _filas_del_rango(dv):
    """Filas que cubre el `sqref` de una validación de una sola columna."""
    filas = set()
    for trozo in str(dv.sqref).split():
        ini, _, fin = trozo.partition(":")
        a = int("".join(c for c in ini if c.isdigit()))
        b = int("".join(c for c in (fin or ini) if c.isdigit()))
        filas |= set(range(a, b + 1))
    return filas


# --- Lo que la R1 midió y estos tests no cubrían ---------------------------------
#
# El test de dominio de arriba solo veía respuestas documentales SIN `pendiente`
# explícito. La R1 mutó el generador para escribir `FUERA_DOMINIO` ante cualquier
# explícito y el test **siguió verde**: probaba la mitad derivada de la columna y se
# presentaba como si cubriera la columna entera.


@pytest.mark.parametrize("valor, marca", [
    ("sí", "sí"), ("no", "no"),
    ("SÍ", "sí"),          # mayúsculas: misma palabra del dominio
    ("si", "sí"),          # sin tilde: equivalencia de GRAFÍA, no de significado
    (" no ", "no"),        # espacios del emisor
])
def test_el_pendiente_explicito_valido_se_normaliza_al_dominio(tmp_path, valor, marca):
    salida = _generar(tmp_path, {"case_id": "W-TEST00",
                                 "preguntas": {"cap_01": {"pendiente": valor}}})
    wb = openpyxl.load_workbook(salida)
    try:
        ws = wb["PREGUNTAS"]
        assert ws.cell(render_informe.build_id_row_map(ws)["cap_01"], COL_PENDIENTE).value == marca
    finally:
        wb.close()


@pytest.mark.parametrize("valor", ["", "SI SEÑOR", "pendiente", True, 1, [], {"a": 1}])
def test_un_pendiente_explicito_invalido_no_deja_la_fila_a_medias(tmp_path, valor, capsys):
    """El agujero que la R1 midió: `{"pendiente": ""}` daba 87 de 88 y un «OK».

    Es el mismo modo de fallo que esta pieza vino a cerrar, en pequeño — una fila sin
    marca no se lee como pendiente, se lee como no valorada—, y la plantilla no
    protege: su validación es `list "sí,no"` pero con `allowBlank=True` y
    `showErrorMessage=False`, así que Excel se come el blanco sin decir nada.
    """
    salida = _generar(tmp_path, {"case_id": "W-TEST00",
                                 "preguntas": {"cap_01": {"pendiente": valor}}})
    assert "cap_01" in capsys.readouterr().err, "el valor inválido se aceptó en silencio"
    wb = openpyxl.load_workbook(salida)
    try:
        ws = wb["PREGUNTAS"]
        id_row = render_informe.build_id_row_map(ws)
        sin_marcar = [q for q, r in id_row.items()
                      if ws.cell(r, COL_PENDIENTE).value not in ("sí", "no")]
        assert not sin_marcar, f"{len(sin_marcar)} de {len(id_row)} sin marca válida"
    finally:
        wb.close()


@pytest.mark.parametrize("valor", [None, False, 0, [], "una cadena suelta"])
def test_una_entrada_que_no_es_un_objeto_avisa_en_vez_de_callar(tmp_path, valor, capsys):
    """Antes del recorrido completo esto reventaba con `AttributeError`.

    El recorrido nuevo lo normalizaba a `{}` y seguía, que es peor que el crash: un
    productor que emita `cap_01: false` en vez de `cap_01: {"respuesta": false}`
    generaría un informe sin esa respuesta y sin que nadie se entere. Ahora avisa.
    """
    _generar(tmp_path, {"case_id": "W-TEST00", "preguntas": {"cap_01": valor}})
    err = capsys.readouterr().err
    if valor is None:
        assert "cap_01" not in err, "un `null` es ausencia declarada, no un error de tipo"
    else:
        assert "cap_01" in err, f"{valor!r} se aceptó como objeto sin decir nada"


def test_los_ids_de_la_plantilla_son_unicos(informe_con_tres_respuestas):
    """El «cuestionario entero» depende de que el mapa no colapse dos filas en una.

    `build_id_row_map` indexa por ID en un `dict`: dos filas con el mismo ID dejarían
    una sin marca y nadie lo diría. Se cuenta **sin** usar el helper como oráculo —la
    R1 señaló justamente que el test del 88 se apoyaba en él— comparando las filas con
    ID contra los IDs distintos.
    """
    ws = informe_con_tres_respuestas
    ids = [str(ws.cell(r, 3).value).strip()
           for r in range(5, ws.max_row + 1) if ws.cell(r, 3).value]
    assert len(ids) == len(set(ids)) == 88, (
        f"{len(ids)} filas con ID y {len(set(ids))} IDs distintos")
