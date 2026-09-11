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
import re
import zipfile
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


# --- El semáforo de la plantilla (`MEJORAS #228`) -------------------------------------


def _informacion():
    wb = openpyxl.load_workbook(PLANTILLA)
    try:
        yield_ = wb["INFORMACION"]
        return (wb, yield_)
    except Exception:
        wb.close()
        raise


@pytest.mark.parametrize("fila", [21, 22])
def test_las_dos_filas_del_semaforo_tienen_sus_tres_colores(fila):
    """Tres reglas, con el alfa `FF` que `modelo_xlsx.md` exige.

    El rango de la 22 es `E22:H22` y cubre sus **dos** bloques combinados
    (`E22:F22` + `G22:H22`), que es donde la 21 tiene uno solo: sin ese rango, escribir
    en `E22` colorearía la mitad izquierda y la derecha quedaría en blanco al lado.
    """
    wb, inf = _informacion()
    try:
        bloque = next((r for r in inf.conditional_formatting
                       if str(r.sqref) == f"E{fila}:H{fila}"), None)
        assert bloque is not None, f"no hay formato condicional en E{fila}:H{fila}"
        colores = {}
        for regla in bloque.rules:
            valor = regla.formula[0].split('"')[1]
            colores[valor] = regla.dxf.fill.bgColor.rgb
        assert set(colores) == {"verde", "amarillo", "rojo"}
        assert all(str(c).upper().startswith("FF") and len(str(c)) == 8
                   for c in colores.values()), f"alfa distinto de FF: {colores}"
    finally:
        wb.close()


def test_el_prerelleno_deja_el_semaforo_en_blanco(tmp_path):
    """La otra mitad del contrato, que el cableado no puede romper.

    `modelo_xlsx.md`: «En el pre-relleno SIEMPRE se dejan en blanco» — el semáforo lo
    firma el abogado, no el generador. Añadirle validación y color a `E22` no puede
    hacer que el render empiece a escribir ahí.
    """
    salida = _generar(tmp_path, {"case_id": "W-TEST00", "preguntas": {}})
    wb = openpyxl.load_workbook(salida)
    try:
        inf = wb["INFORMACION"]
        assert inf["E21"].value is None and inf["E22"].value is None
    finally:
        wb.close()


# --- Lo que la R1 rompió de estos cuatro tests ---------------------------------------
#
# Tres mutantes sobrevivían a los seis casos nuevos, y los tres importan:
#
# - Mover la validación a **`E220`** dejaba `E22` sin desplegable, y pasaba: la
#   comprobación era `"E22" in str(sqref)`, una **subcadena**. Pertenencia geométrica,
#   no textual.
# - Apuntar las tres fórmulas de FINANZAS a **`$E$21`** hacía que FINANZAS se pintara
#   según JURÍDICO, y pasaba: los tests extraían el valor entre comillas sin mirar **qué
#   celda gobierna**.
# - Quitar la protección de PREGUNTAS pasaba los 32 casos del módulo, pese a que el PR
#   anunciaba «protección conservada». Anunciar una propiedad que ningún test vigila es
#   la misma clase de «OK» que toda esta pieza persigue.


def _regla_de(inf, fila):
    """Las reglas de la fila, con la celda que las gobierna. No por subcadena."""
    from openpyxl.utils import range_boundaries

    bloques = [r for r in inf.conditional_formatting
               if str(r.sqref) == f"E{fila}:H{fila}"]
    assert len(bloques) == 1, f"esperaba UN bloque en E{fila}:H{fila}: {bloques}"
    fuera = {}
    for g in bloques[0].rules:
        formula = g.formula[0]
        fuera[formula] = g
    return fuera, range_boundaries(f"E{fila}:H{fila}")


@pytest.mark.parametrize("fila", [21, 22])
def test_la_validacion_cubre_la_celda_ANCLA_del_semaforo(fila):
    """Pertenencia geométrica, no `"E22" in sqref`.

    Con la validación en `E220`, la comprobación por subcadena pasaba y la celda se
    quedaba sin desplegable (R1, H-02).
    """
    from openpyxl.utils import range_boundaries

    wb, inf = _informacion()
    try:
        cubren = []
        for d in inf.data_validations.dataValidation:
            for trozo in str(d.sqref).split():
                min_c, min_r, max_c, max_r = range_boundaries(trozo)
                if min_c <= 5 <= max_c and min_r <= fila <= max_r:   # E = columna 5
                    cubren.append(d)
        assert len(cubren) == 1, f"E{fila} está cubierta por {len(cubren)} validaciones"
        assert cubren[0].type == "list"
    finally:
        wb.close()


@pytest.mark.parametrize("fila", [21, 22])
def test_cada_fila_del_semaforo_se_gobierna_por_SU_PROPIA_celda(fila):
    """CONTROL POSITIVO de H-02: las fórmulas de FINANZAS podían leer `$E$21`.

    Con eso, elegir «jurídico verde, finanzas rojo» pintaba FINANZAS de verde — y los
    tests pasaban, porque solo miraban el literal entre comillas.
    """
    wb, inf = _informacion()
    try:
        reglas, _ = _regla_de(inf, fila)
        esperadas = {f'$E${fila}="{v}"' for v in ("verde", "amarillo", "rojo")}
        assert set(reglas) == esperadas, (
            f"la fila {fila} no se gobierna por E{fila}: {sorted(reglas)}")
    finally:
        wb.close()


@pytest.mark.parametrize("fila", [21, 22])
def test_el_rango_del_color_cubre_la_fila_ENTERA_del_semaforo(fila):
    """De `E` a `H`, que es lo que ocupa el semáforo.

    La fila 22 tiene dos bloques combinados (`E22:F22` + `G22:H22`): con un rango que
    cubriera solo el primero, la mitad derecha se quedaría sin pintar al lado de la
    izquierda pintada.
    """
    from openpyxl.utils import range_boundaries

    wb, inf = _informacion()
    try:
        _, (min_c, min_r, max_c, max_r) = _regla_de(inf, fila)
        assert (min_c, max_c) == (5, 8), f"el rango va de {min_c} a {max_c}, no de E a H"
        assert min_r == max_r == fila
    finally:
        wb.close()


def test_las_dos_filas_del_semaforo_son_EL_MISMO_semaforo():
    """Fondo **y** fuente, no solo fondo (R1, H-04).

    Las reglas de `E21` llevan negrita y color de texto; las primeras que escribí para
    `E22` solo llevaban relleno. Con `amarillo` en las dos, JURÍDICO salía en marrón y
    negrita y FINANZAS en negro normal: mismo fondo, distinto semáforo. Un lector que ve
    dos estilos en el mismo recuadro tiene que aprender cuál es cuál.
    """
    wb, inf = _informacion()
    try:
        def perfil(fila):
            reglas, _ = _regla_de(inf, fila)
            return {f.split('"')[1]: (
                g.dxf.fill.bgColor.rgb,
                getattr(g.dxf.font, "b", None),
                getattr(getattr(g.dxf.font, "color", None), "rgb", None))
                for f, g in reglas.items()}

        assert perfil(21) == perfil(22)
    finally:
        wb.close()


@pytest.mark.parametrize("fila", [21, 22])
def test_las_dos_validaciones_tienen_las_MISMAS_opciones(fila):
    """CONTROL POSITIVO de H-01, que fue un error de hecho mío.

    Afirmé replicar `E21` «exactamente» y puse `showErrorMessage=False` donde `E21`
    tiene `True`: medí esa opción en la validación de la hoja PREGUNTAS y **la
    extrapolé**. O sea que introduje la asimetría que decía estar evitando, y la
    justifiqué con una premisa falsa.
    """
    wb, inf = _informacion()
    try:
        dv = {str(d.sqref): d for d in inf.data_validations.dataValidation}
        assert dv["E21"].allowBlank == dv["E22"].allowBlank
        assert dv["E21"].showErrorMessage == dv["E22"].showErrorMessage
        assert dv[f"E{fila}"].showErrorMessage is True
    finally:
        wb.close()


def test_la_plantilla_conserva_sus_invariantes():
    """Lo que el PR anunciaba y ningún test vigilaba (R1, H-02).

    Quitar la protección de `PREGUNTAS` pasaba los 32 casos del módulo. Anunciar una
    propiedad que nadie comprueba es exactamente el «OK» que esta skill persigue en las
    demás herramientas.
    """
    wb = openpyxl.load_workbook(PLANTILLA)
    try:
        assert wb.sheetnames == ["INFORMACION", "PREGUNTAS", "AVISOS LLM", "BITACORA"]
        assert wb["PREGUNTAS"].protection.sheet is True, "PREGUNTAS dejó de estar protegida"
        assert wb["INFORMACION"]["F39"].value == "=SUM(F25:G38)", "la fórmula del TOTAL cambió"
        validaciones = {h: len(list(wb[h].data_validations.dataValidation))
                        for h in wb.sheetnames}
        assert validaciones == {"INFORMACION": 2, "PREGUNTAS": 2,
                                "AVISOS LLM": 3, "BITACORA": 0}, validaciones
        merges = sorted(str(m) for m in wb["INFORMACION"].merged_cells.ranges
                        if m.min_row in (21, 22))
        assert merges == ["B21:D21", "B22:D22", "E21:H21", "E22:F22",
                          "G22:H22"], merges
    finally:
        wb.close()


# ---------------------------------------------------------------------------
# `MEJORAS #243` — el filtro que produce el guion de entrevista
#
# `autoFilter` era `B3:M88` y los 88 IDs llegan a la **fila 103**: doce preguntas
# —las de Team leader, Escritura y Reclamación— quedaban fuera del ámbito del
# filtro. Marcar las 88 filas (la pieza P5) sirve de poco si el filtro solo
# alcanza a 76, porque entonces el guion que sale del filtro NO es el
# cuestionario.
#
# Los dos tests miden contra la plantilla, no contra un número escrito a mano: el
# día que se añada una sección 12 tienen que ponerse rojos solos.
# ---------------------------------------------------------------------------

def _ultima_fila_del_rango(ref: str) -> int:
    """`"B3:M103"` -> `103`."""
    return int(re.search(r"(\d+)$", ref).group(1))


def test_el_filtro_del_guion_alcanza_a_TODAS_las_preguntas():
    wb = openpyxl.load_workbook(PLANTILLA)
    try:
        ws = wb["PREGUNTAS"]
        filas_con_id = [r for r in range(5, ws.max_row + 1) if ws.cell(r, 3).value]
        ref = ws.auto_filter.ref
    finally:
        wb.close()
    assert ref, "PREGUNTAS perdió su autoFilter"
    assert _ultima_fila_del_rango(ref) >= max(filas_con_id), (
        f"el autoFilter es {ref} y hay IDs hasta la fila {max(filas_con_id)}: "
        f"{sum(1 for f in filas_con_id if f > _ultima_fila_del_rango(ref))} preguntas "
        "quedan fuera del filtro que produce el guion de entrevista"
    )


def test_el_FilterDatabase_dice_lo_MISMO_que_el_autoFilter():
    """La otra mitad del mismo hecho, y openpyxl no la enseña.

    El rango del filtro vive en DOS sitios: el `autoFilter` de la hoja y el nombre
    definido oculto `_xlnm._FilterDatabase` del libro. `wb.defined_names` viene
    vacío —openpyxl enseña lo que entiende—, así que esto se lee del zip.
    """
    wb = openpyxl.load_workbook(PLANTILLA)
    try:
        ref_hoja = wb["PREGUNTAS"].auto_filter.ref
    finally:
        wb.close()
    with zipfile.ZipFile(PLANTILLA) as z:
        wbx = z.read("xl/workbook.xml").decode("utf-8")
    m = re.search(r"<definedName name=\"_xlnm\._FilterDatabase\"[^>]*>"
                  r"'PREGUNTAS'!(\$[A-Z]+\$\d+:\$[A-Z]+\$\d+)</definedName>", wbx)
    assert m, "no hay _xlnm._FilterDatabase para PREGUNTAS en workbook.xml"
    assert m.group(1).replace("$", "") == ref_hoja, (
        f"el nombre definido dice {m.group(1)} y el autoFilter {ref_hoja}: "
        "cambiar uno y no el otro deja el filtro a medias"
    )


# ---------------------------------------------------------------------------
# `MEJORAS #242` — el semáforo en blanco se veía ROJO
#
# `E21` tenía un relleno sólido `FFFF0000` en su estilo base, bajo el formato
# condicional. Sin valor no se activa ninguna regla y quedaba el relleno: un
# informe **sin valorar** enseñaba JURÍDICO en rojo puro, que ni siquiera es el
# rojo del semáforo (`FFC7CE`). `E22` no lo tenía, así que las dos filas vacías
# se veían distinto.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fila", [21, 22])
def test_el_semaforo_SIN_VALORAR_no_pinta_ningun_color(fila):
    wb, inf = _informacion()
    try:
        celda = inf[f"E{fila}"]
        assert celda.value is None, "la plantilla trae el semáforo valorado"
        assert celda.fill.patternType != "solid", (
            f"E{fila} tiene relleno sólido {celda.fill.start_color.rgb} en su estilo "
            "base: sin valor no se activa ninguna regla del condicional y esa es la "
            "que se ve, así que un informe sin valorar enseña un color que nadie puso"
        )
    finally:
        wb.close()


def test_las_dos_filas_del_semaforo_se_ven_IGUAL_estando_vacias():
    """El defecto no era solo el rojo: era que las dos filas no coincidían."""
    wb, inf = _informacion()
    try:
        a, b = inf["E21"].fill, inf["E22"].fill
        assert (a.patternType, a.start_color.rgb) == (b.patternType, b.start_color.rgb), (
            f"E21 {a.patternType}/{a.start_color.rgb} contra "
            f"E22 {b.patternType}/{b.start_color.rgb}"
        )
    finally:
        wb.close()


def test_quitar_el_relleno_de_E21_no_se_llevo_su_borde_ni_su_alineacion():
    """La mitad conservadora: el `xf` de `E21` lleva más cosas que el relleno.

    Sin esto, «quitar el relleno» podría hacerse apuntando `E21` al estilo 0 y
    llevarse por delante el recuadro del bloque VIABILIDAD sin que nada avisara.
    """
    wb, inf = _informacion()
    try:
        celda = inf["E21"]
        assert celda.alignment.horizontal == "center", "E21 perdió su alineación"
        assert celda.border.top.style or celda.border.left.style, "E21 perdió su borde"
        assert celda.font.b or celda.font.sz, "E21 perdió su fuente"
    finally:
        wb.close()
