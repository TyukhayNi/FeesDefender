"""La verificación compara vínculos y datos por IGUALDAD (spec rev. 3 §4, Parte B).

`_auditar` comprobaba lo pedido y nunca lo que sobra: el expediente 653 salió «VERIFICADA por
lectura» con cuatro colaboradores declarados y seis vinculados (`#288`). Y una igualdad de ids
exacta certificaba una ficha cuyos datos no se habían escrito: el apellido de W-030A13 (`#283`,
R1/H-03). Funciones puras: el CLI lee el CRM y se lo da.
"""
import pytest

from core import crm_ficha as cf


def _rel(**bloques):
    return {k: [{"id": i} for i in v] for k, v in bloques.items()}


# ---------------------------------------------------------------------------
# Vínculos (B.1)
# ---------------------------------------------------------------------------

def test_R288_el_653_dos_colaboradores_de_mas_son_sobrantes():
    esperado = {"clientes_propios": ["2"], "clientes_contrarios": ["1128"],
                "colaboradores": ["256", "805", "102", "552"]}
    leido = _rel(clientes_propios=["2"], clientes_contrarios=["1128"],
                 colaboradores=["256", "805", "102", "552", "624", "677"])
    a = cf.auditar_relaciones(esperado, leido)
    assert a.faltan == [] and a.sobran == ["colaboradores id=624", "colaboradores id=677"]


def test_sobrantes_en_los_tres_bloques_incluso_con_cero_esperados():
    a = cf.auditar_relaciones({"clientes_propios": ["2"], "clientes_contrarios": [],
                               "colaboradores": []},
                              _rel(clientes_propios=["2", "27"], clientes_contrarios=["9"],
                                   colaboradores=["8"]))
    assert a.sobran == ["clientes_propios id=27", "clientes_contrarios id=9",
                        "colaboradores id=8"]


def test_multiplicidad_en_los_dos_sentidos_y_id_int_frente_a_str():
    a = cf.auditar_relaciones({"clientes_propios": ["2"], "clientes_contrarios": ["5", "5"],
                               "colaboradores": ["7"]},
                              {"clientes_propios": [{"id": 2}], "clientes_contrarios": [{"id": 5}],
                               "colaboradores": [{"id": "7"}, {"id": "7"}]})
    assert a.faltan == ["clientes_contrarios id=5 (la corrida escribió 2, la lectura ve 1)"]
    assert a.sobran == ["colaboradores id=7"]


def test_faltan_y_sobran_a_la_vez():
    a = cf.auditar_relaciones({"clientes_propios": ["2"], "clientes_contrarios": ["5"],
                               "colaboradores": []},
                              _rel(clientes_propios=["2"], clientes_contrarios=["6"]))
    assert a.faltan == ["clientes_contrarios id=5 (la corrida escribió 1, la lectura ve 0)"]
    assert a.sobran == ["clientes_contrarios id=6"]


def test_exacto_es_todo_ok_y_los_bloques_ajenos_no_se_miran():     # control positivo
    a = cf.auditar_relaciones({"clientes_propios": ["2"], "clientes_contrarios": ["5", "5"],
                               "colaboradores": []},
                              _rel(clientes_propios=["2"], clientes_contrarios=["5", "5"],
                                   actuaciones=["21496"]))
    assert a.ok == ["clientes_propios id=2", "clientes_contrarios id=5 (x2)"]
    assert a.faltan == [] and a.sobran == []


# ---------------------------------------------------------------------------
# Datos (B.2)
# ---------------------------------------------------------------------------

def test_R1H03_la_ficha_de_w030a13_con_el_apellido_vacio_no_pasa():
    decl = {"nombre": "ANA", "apellido1": "GARCIA", "nif": "00000000T"}
    [d] = cf.auditar_datos("clientes_contrarios", "1128", decl,
                           {"nombre": "ANA", "1apellido": "", "nif_cif": "00000000T"})
    assert (d.propiedad, d.tipo) == ("1apellido", "vacio")
    assert str(d) == "clientes_contrarios id=1128 1apellido: vacío en el CRM"


def test_mayusculas_espacios_y_formato_no_son_diferencia_y_lo_distinto_se_dice():
    decl = {"nombre": "Ana", "apellido1": "García", "nif": "00.000.000-t", "email": "Ana@X.es",
            "movil": "+34 600 111 222", "direccion": "CALLE  MAYOR 1"}
    ficha = {"nombre": "ANA ", "1apellido": "GARCÍA", "nif_cif": "00000000T",
             "email": "ana@x.es", "movil": "600111222", "direccion": "calle mayor 1"}
    assert cf.auditar_datos("clientes_contrarios", "1", decl, ficha) == []
    ficha["1apellido"] = "PEREZ"
    [d] = cf.auditar_datos("clientes_contrarios", "1", decl, ficha)
    assert str(d) == "clientes_contrarios id=1 1apellido: distinto (CRM 'PEREZ', YAML 'García')"


#: (campo del YAML, propiedad del CRM, un valor, otro valor) — fijado aquí, fuera de la tupla
#: que lo implementa, para que un cruce en `CAMPOS_*_CRM` no se pruebe contra sí mismo.
_MAPA_CONTRARIO = [
    ("nombre", "nombre", "ANA", "LUISA"), ("apellido1", "1apellido", "GARCIA", "PEREZ"),
    ("apellido2", "2apellido", "RUIZ", "SOLER"), ("email", "email", "a@x.es", "b@x.es"),
    ("movil", "movil", "600111222", "699999999"), ("nif", "nif_cif", "00000000T", "11111111H"),
    ("direccion", "direccion", "CALLE UNO 1", "CALLE DOS 2"),
    ("poblacion", "poblacion", "BADALONA", "GIRONA"), ("cp", "cp", "08019", "08028"),
    ("provincia", "provincia", "Barcelona", "Madrid"),
    ("telefono", "telefono1", "931112233", "932223344"),
]
_MAPA_COLABORADOR = [
    ("nombre", "nombre", "ANA CONSULTORA", "BEA ASESORA"), ("email", "email", "a@x.es", "b@x.es"),
    ("movil", "movil", "600111222", "699999999"),
    ("telefono", "telefono1", "931112233", "932223344"),
    ("nif", "nif_cif", "00000000T", "11111111H"),
]
_MATRIZ = ([("clientes_contrarios", *f) for f in _MAPA_CONTRARIO]
           + [("colaboradores", *f) for f in _MAPA_COLABORADOR])


def test_cada_campo_va_a_su_propiedad_del_CRM():
    assert ([(c, p) for c, p, _ in cf.CAMPOS_CONTRARIO_CRM]
            == [(c, p) for c, p, *_ in _MAPA_CONTRARIO])
    assert ([(c, p) for c, p, _ in cf.CAMPOS_COLABORADOR_CRM]
            == [(c, p) for c, p, *_ in _MAPA_COLABORADOR])


@pytest.mark.parametrize("elemento, campo, prop, valor, otro", _MATRIZ)
def test_la_matriz_campo_por_rol(elemento, campo, prop, valor, otro):
    decl = {campo: valor}
    assert cf.auditar_datos(elemento, "9", decl, {prop: valor}) == []          # igual
    [v] = cf.auditar_datos(elemento, "9", decl, {prop: ""})                     # vacío
    [a] = cf.auditar_datos(elemento, "9", decl, {})                             # ausente = vacío
    [d] = cf.auditar_datos(elemento, "9", decl, {prop: otro})                   # distinto
    assert (v.tipo, a.tipo, d.tipo) == ("vacio", "vacio", "distinto")
    assert v.propiedad == a.propiedad == d.propiedad == prop


def test_lo_que_el_yaml_no_declara_no_se_compara():                     # control positivo
    assert cf.auditar_datos("colaboradores", "7", {"nombre": "ANA", "email": "ana@x.es",
                                                   "movil": None},
                            {"nombre": "ANA", "email": "ana@x.es", "movil": "699"}) == []


@pytest.mark.parametrize("en_el_crm, esperado", [
    ("Barcelona", []), ("", ["vacio"]), ("1", ["vacio"]), ("Sin Asignar", ["vacio"]),
    ("Madrid", ["distinto"]),
])
def test_R2H03_la_provincia_se_compara_igual_en_los_dos_lados(en_el_crm, esperado):
    """`provincia_canonica('barcelona')` es `'Barcelona'`; normalizar solo un lado no casaba
    NUNCA. Y el `1` del enum es «Sin Asignar» (atlas): el vacío del Select, no una provincia."""
    got = cf.auditar_datos("clientes_contrarios", "1", {"provincia": "barcelona"},
                           {"provincia": en_el_crm})
    assert [d.tipo for d in got] == esperado


# ---------------------------------------------------------------------------
# La fase previa (A.4): lo que no deja pasar
# ---------------------------------------------------------------------------

def test_la_fase_previa_solo_para_lo_DISTINTO():
    """Lo vacío no es contradicción: lo completa la corrida, o lo dice la lectura final."""
    decl = {"nombre": "ANA", "apellido1": "GARCIA", "nif": "00000000T", "email": "ana@x.es"}
    vacia = {"nombre": "ANA", "1apellido": "", "nif_cif": "00000000T", "email": ""}
    assert cf.contradicciones_previas("clientes_contrarios", "1128", decl, vacia,
                                      por_id=False) == []
    otra = {**vacia, "1apellido": "PEREZ"}
    assert cf.contradicciones_previas("clientes_contrarios", "1128", decl, otra, por_id=False) == [
        "clientes_contrarios id=1128 1apellido: distinto (CRM 'PEREZ', YAML 'GARCIA')"]


def test_por_id_una_ficha_sin_nombre_es_que_no_existe():
    decl = {"nombre": "ANA", "email": "a@x.es"}
    assert cf.contradicciones_previas("colaboradores", "9", decl, {}, por_id=True) == [
        "colaboradores id=9: la ficha no existe o no tiene nombre; revisa el id_crm"]
    # Sin `id_crm`, una ficha hallada por NIF o email sin nombre no es contradicción: su nombre
    # vacío lo dirá la lectura final como `[DATO]`.
    assert cf.contradicciones_previas("colaboradores", "9", decl, {}, por_id=False) == []
