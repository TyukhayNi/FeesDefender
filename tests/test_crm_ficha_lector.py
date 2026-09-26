"""El `_ficha_crm.yaml` se lee entero o no se lee (spec rev. 3 §3, Parte A).

`yaml.safe_load` se queda con la ÚLTIMA de dos claves repetidas y no avisa: una parte entera
desaparecía antes de que existiera el diccionario que las validaciones miran (R1/H-01). Y la
R2 midió que el primer lector propuesto dejaba escapar `TypeError` y `ParserError` donde
prometía `ValueError`, y de varias repetidas decía solo la primera (R2/H-04).
"""
import re

import pytest
import yaml

from core import crm_ficha as cf


def _yaml(tmp_path, texto):
    p = tmp_path / "_ficha_crm.yaml"
    p.write_text(texto, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Task 1 — lector sin pérdida (A.1)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("texto, clave, linea, primera", [
    ("contrario: {nombre: UNO}\ncontrario: {nombre: DOS}\n", "contrario", 2, 1),   # una parte entera
    ("contrario:\n  nombre: A\n  apellido1: X\n  apellido1: Y\n", "apellido1", 4, 3),
    ("colaboradores:\n  - {nombre: A, email: a@x.es, email: b@x.es}\n", "email", 2, 2),
])
def test_R1H01_una_clave_repetida_se_rechaza_con_su_linea(tmp_path, texto, clave, linea, primera):
    with pytest.raises(ValueError) as e:
        cf.leer_yaml_ficha(_yaml(tmp_path, texto))
    assert (f"línea {linea}: la clave {clave!r} está repetida (ya en la línea {primera})"
            in str(e.value))


def test_R2H04_dos_repetidas_salen_las_dos(tmp_path):
    with pytest.raises(ValueError) as e:
        cf.leer_yaml_ficha(_yaml(tmp_path, "a: 1\na: 2\nb: 1\nb: 2\n"))
    assert "línea 2: la clave 'a'" in str(e.value) and "línea 4: la clave 'b'" in str(e.value)


@pytest.mark.parametrize("texto, forma", [("? [a, b]\n: c\n", "una lista"),
                                          ("? {a: 1}\n: c\n", "un mapping")])
def test_R2H04_una_clave_que_no_es_texto_se_rechaza_con_su_linea(tmp_path, texto, forma):
    with pytest.raises(ValueError,
                       match=f"línea 1: una clave tiene que ser un texto, y aquí es {forma}"):
        cf.leer_yaml_ficha(_yaml(tmp_path, texto))


def test_los_alias_se_rechazan_con_su_linea(tmp_path):
    with pytest.raises(ValueError, match=r"línea 1: los alias"):
        cf.leer_yaml_ficha(_yaml(tmp_path, "a: &x {nombre: A}\ncontrario: *x\n"))


def test_R2_el_merge_SIN_alias_se_rechaza(tmp_path):
    """`{<<: {nombre: A}}` no lleva alias: lo para la comprobación del merge, no la de alias.

    La rev. 1 del plan lo probaba solo junto a un alias, con el comentario «un merge necesita un
    alias», que es falso: quitar la comprobación del merge habría dejado ese test en verde."""
    with pytest.raises(ValueError, match=r"línea 1: el merge"):
        cf.leer_yaml_ficha(_yaml(tmp_path, "contrario: {<<: {nombre: A}}\n"))


def test_el_merge_con_alias_tambien(tmp_path):
    with pytest.raises(ValueError, match="alias"):
        cf.leer_yaml_ficha(_yaml(tmp_path, "base: &b {nombre: A}\ncontrario: {<<: *b}\n"))


def test_R2H04_una_sintaxis_rota_sale_como_ValueError(tmp_path):
    with pytest.raises(ValueError, match="inválido"):
        cf.leer_yaml_ficha(_yaml(tmp_path, 'notas_html: ["*",\n'))


@pytest.mark.parametrize("texto", ["", "# solo un comentario\n"])
def test_documento_vacio_es_ficha_vacia(tmp_path, texto):
    assert cf.leer_yaml_ficha(_yaml(tmp_path, texto)) == {}


def test_un_yaml_normal_se_lee_igual_que_con_safe_load(tmp_path):     # control positivo
    texto = "contrario:\n  nombre: JUAN\n  nif: '00000000T'\nnotas_html: '<p>E&amp;V</p>'\n"
    assert cf.leer_yaml_ficha(_yaml(tmp_path, texto)) == yaml.safe_load(texto)


def test_si_no_existe_FileNotFoundError(tmp_path):
    with pytest.raises(FileNotFoundError):
        cf.leer_yaml_ficha(tmp_path / "no.yaml")


# ---------------------------------------------------------------------------
# Task 2 — claves y tipos, todos los problemas en un error (A.2, A.3, A.5)
# ---------------------------------------------------------------------------

#: El inventario, fijado aquí y no leído de la tupla que lo implementa: si alguien quita una
#: clave de `CLAVES_*`, lo dice este test y no el silencio (R2, acta §5).
_INVENTARIO_CONTRARIO = ("nombre", "apellido1", "apellido2", "email", "movil", "nif",
                         "direccion", "poblacion", "cp", "provincia", "telefono")
_INVENTARIO_COLABORADOR = ("nombre", "email", "movil", "telefono", "nif")


def test_las_tuplas_son_el_inventario_del_spec():
    """Los datos de cada parte, y `id_crm` al final (literal del contrato de la Task 7)."""
    assert cf.CLAVES_RAIZ == ("contrario", "colaboradores", "notas_html", "cliente_propio",
                              "firmante")
    assert cf.CLAVES_CONTRARIO == _INVENTARIO_CONTRARIO + ("id_crm",)
    assert cf.CLAVES_COLABORADOR == _INVENTARIO_COLABORADOR + ("id_crm",)


def _parte(rol, clave, valor_yaml):
    """Una parte válida salvo `clave`, que lleva `valor_yaml` (texto YAML en flujo)."""
    base = {"contrario": {"nombre": "A", "nif": "'00000000T'"},
            "colaborador": {"nombre": "A", "email": "a@x.es"}}[rol]
    cuerpo = "{" + ", ".join(f"{k}: {v}" for k, v in {**base, clave: valor_yaml}.items()) + "}"
    return f"contrario: {cuerpo}\n" if rol == "contrario" else f"colaboradores:\n  - {cuerpo}\n"


def _linea(error, ruta):
    return next(l for l in str(error.value).splitlines() if f"{ruta}:" in l)


@pytest.mark.parametrize("texto, ruta, sugerencias", [
    ("contrario: {nombre: A, nif: '1', apellido: X}\n", "contrario.apellido",
     ["apellido1", "apellido2"]),
    ("contrario:\n  - {nombre: A, nif: '1', apellido: X}\n", "contrario[0].apellido",
     ["apellido1", "apellido2"]),
    ("colaboradores:\n  - {nombre: A, email: a@x.es, mail: b}\n", "colaboradores[0].mail",
     ["email"]),
    ("contrarios: {nombre: A, nif: '1'}\n", "contrarios", ["contrario"]),
])
def test_clave_desconocida_con_ruta_y_TODAS_las_sugerencias(tmp_path, texto, ruta, sugerencias):
    with pytest.raises(ValueError) as e:
        cf.cargar_ficha_yaml(_yaml(tmp_path, texto))
    linea = _linea(e, ruta)
    assert "clave desconocida" in linea
    for s in sugerencias:
        assert repr(s) in linea


def test_sin_candidata_cercana_no_se_inventa_sugerencia(tmp_path):
    with pytest.raises(ValueError) as e:
        cf.cargar_ficha_yaml(_yaml(tmp_path, "contrario: {nombre: A, nif: '1', zzzz: X}\n"))
    assert "¿querías" not in _linea(e, "contrario.zzzz")


def test_varios_problemas_salen_todos(tmp_path):
    texto = "contrario: {nombre: A, nif: '1', apellido: X, dni: Y}\nnotas: z\n"
    with pytest.raises(ValueError) as e:
        cf.cargar_ficha_yaml(_yaml(tmp_path, texto))
    for trozo in ("contrario.apellido:", "contrario.dni:", "notas:"):
        assert trozo in str(e.value)


_ESCALARES = ([("contrario", f"contrario.{c}", c) for c in _INVENTARIO_CONTRARIO]
              + [("colaborador", f"colaboradores[0].{c}", c) for c in _INVENTARIO_COLABORADOR])


@pytest.mark.parametrize("rol, ruta, clave", _ESCALARES)
@pytest.mark.parametrize("valor", ["{x: y}", "[x]"])
def test_R1H02_un_mapping_o_una_lista_en_CUALQUIER_escalar_se_rechaza(tmp_path, rol, ruta,
                                                                      clave, valor):
    with pytest.raises(ValueError) as e:
        cf.cargar_ficha_yaml(_yaml(tmp_path, _parte(rol, clave, valor)))
    assert f"{ruta}: tiene que ser un texto o null" in str(e.value)


@pytest.mark.parametrize("clave", ["notas_html", "firmante"])
@pytest.mark.parametrize("valor", ["{texto: importante}", "[x]"])
def test_R1H02_tambien_en_notas_y_firmante(tmp_path, clave, valor):
    with pytest.raises(ValueError, match=re.escape(f"{clave}: tiene que ser un texto o null")):
        cf.cargar_ficha_yaml(_yaml(tmp_path, f"{clave}: {valor}\n"))


@pytest.mark.parametrize("rol, ruta", [("contrario", "contrario"),
                                       ("colaborador", "colaboradores[0]")])
def test_un_nombre_de_solo_espacios_se_rechaza(tmp_path, rol, ruta):
    with pytest.raises(ValueError, match=re.escape(f"{ruta}.nombre: falta o está vacío")):
        cf.cargar_ficha_yaml(_yaml(tmp_path, _parte(rol, "nombre", "'   '")))


@pytest.mark.parametrize("valor", ["false", "0", "[]", "{}", "NO_EXISTE"])
def test_cliente_propio_fuera_del_catalogo_se_rechaza(tmp_path, valor):
    with pytest.raises(ValueError, match="cliente_propio desconocido"):
        cf.cargar_ficha_yaml(_yaml(tmp_path, f"cliente_propio: {valor}\n"))


@pytest.mark.parametrize("texto, ruta", [
    ("colaboradores: {nombre: A, email: a@x.es}\n", "colaboradores"),
    ("colaboradores:\n  - texto suelto\n", "colaboradores[0]"),
    ("contrario: [texto suelto]\n", "contrario[0]"),
])
def test_una_coleccion_con_otra_forma_se_rechaza(tmp_path, texto, ruta):
    with pytest.raises(ValueError, match=re.escape(f"{ruta}: tiene que ser")):
        cf.cargar_ficha_yaml(_yaml(tmp_path, texto))


@pytest.mark.parametrize("texto", ["false\n", "0\n", "[]\n", "texto\n"])
def test_una_raiz_que_no_es_mapping_se_rechaza(tmp_path, texto):
    with pytest.raises(ValueError, match="raíz"):
        cf.cargar_ficha_yaml(_yaml(tmp_path, texto))


def test_R2H02_una_provincia_que_no_existe_se_rechaza_al_validar(tmp_path):
    with pytest.raises(ValueError, match=re.escape("contrario.provincia:")):
        cf.cargar_ficha_yaml(_yaml(tmp_path, _parte("contrario", "provincia", "Atlantida")))


def test_una_provincia_con_otra_caja_vale(tmp_path):                  # control positivo
    f = cf.cargar_ficha_yaml(_yaml(tmp_path, _parte("contrario", "provincia", "barcelona")))
    assert f.contrarios[0].provincia == "barcelona"


@pytest.mark.parametrize("rol, ruta", [("contrario", "contrario"),
                                       ("colaborador", "colaboradores[0]")])
@pytest.mark.parametrize("clave, valor", [("movil", "'+34'"), ("telefono", "'0034'")])
def test_R2H02_un_telefono_que_se_queda_vacio_se_rechaza(tmp_path, rol, ruta, clave, valor):
    with pytest.raises(ValueError, match=re.escape(f"{ruta}.{clave}:")):
        cf.cargar_ficha_yaml(_yaml(tmp_path, _parte(rol, clave, valor)))


@pytest.mark.parametrize("rol", ["contrario", "colaborador"])
def test_un_telefono_legitimo_vale(tmp_path, rol):                     # control positivo
    f = cf.cargar_ficha_yaml(_yaml(tmp_path, _parte(rol, "movil", "'+34 600 111 222'")))
    parte = f.contrarios[0] if rol == "contrario" else f.colaboradores[0]
    assert parte.movil == "600111222"


def test_null_y_ausente_son_no_hay_dato(tmp_path):                    # controles positivos
    f = cf.cargar_ficha_yaml(_yaml(tmp_path,
        "contrario: {nombre: A, nif: '1', apellido2: null}\ncolaboradores: null\n"))
    assert f.contrarios[0].apellido2 == "" and f.colaboradores == []
    assert f.cliente_propio == cf.CLIENTE_PROPIO_DEFAULT
    assert (cf.cargar_ficha_yaml(_yaml(tmp_path, "cliente_propio: null\n")).cliente_propio
            == cf.CLIENTE_PROPIO_DEFAULT)


def test_cargar_ficha_yaml_lee_con_el_lector_sin_perdida(tmp_path):
    """El consumidor 1 del lector (el 2 es `apply`, Task 4)."""
    with pytest.raises(ValueError, match="repetida"):
        cf.cargar_ficha_yaml(_yaml(tmp_path,
            "contrario: {nombre: UNO, nif: '1'}\ncontrario: {nombre: DOS, nif: '2'}\n"))


def test_cada_clave_llega_a_su_atributo(tmp_path):
    """Centinela distinto por campo: mata el cruce de asignaciones, no solo la tupla.

    `V_movil` y `W_telefono` sobreviven a `normalize_es_phone`, que solo quita `[\\s.\\-/()]` y
    el prefijo de país (medido); la provincia tiene que ser una real, porque la validación
    rechaza la que el Select no reconocería."""
    valores = {c: f"V_{c}" for c in _INVENTARIO_CONTRARIO}
    valores["provincia"] = "Zaragoza"
    texto = "contrario:\n" + "".join(f"  {c}: '{v}'\n" for c, v in valores.items())
    f = cf.cargar_ficha_yaml(_yaml(tmp_path, texto))
    for c, v in valores.items():
        assert getattr(f.contrarios[0], c) == v, c
    valores_col = {c: f"W_{c}" for c in _INVENTARIO_COLABORADOR}
    texto = ("colaboradores:\n  - " + "\n    ".join(f"{c}: '{v}'" for c, v in valores_col.items())
             + "\n")
    f = cf.cargar_ficha_yaml(_yaml(tmp_path, texto))
    for c, v in valores_col.items():
        assert getattr(f.colaboradores[0], c) == v, c


# ---------------------------------------------------------------------------
# Task 3 — identidad estable antes de escribir (A.4), todavía sin `id_crm`
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("texto, ruta", [
    ("contrario: {nombre: A}\n", "contrario"),
    ("contrario:\n  - {nombre: A, nif: '1'}\n  - {nombre: B}\n", "contrario[1]"),
    ("colaboradores:\n  - {nombre: A}\n", "colaboradores[0]"),
    ("colaboradores:\n  - {nombre: A, nif: '  ', email: ''}\n", "colaboradores[0]"),
])
def test_R1H04_una_parte_sin_identidad_estable_se_rechaza(tmp_path, texto, ruta):
    """`resolver_parte` identifica solo por NIF o email: sin ninguno, cada relanzamiento
    crearía otra ficha y la anterior quedaría como sobrante, sin salida (R1/H-04)."""
    with pytest.raises(ValueError) as e:
        cf.cargar_ficha_yaml(_yaml(tmp_path, texto))
    assert f"{ruta}: {cf.SIN_IDENTIDAD}" in str(e.value)


@pytest.mark.parametrize("identidad", ["nif: '00000000T'", "email: a@x.es"])
def test_basta_el_nif_o_el_email(tmp_path, identidad):                # control positivo
    assert cf.cargar_ficha_yaml(_yaml(tmp_path,
                                      f"contrario: {{nombre: A, {identidad}}}\n")).contrarios


def test_id_crm_basta_como_identidad(tmp_path):
    """Sustituye a `test_R2H06_id_crm_todavia_NO_es_una_clave`, que fijaba el estado
    intermedio seguro de la Task 3 y deja de ser verdad en la Task 7: `id_crm` entra con su
    consumidor, en el mismo commit (R2/H-06)."""
    f = cf.cargar_ficha_yaml(_yaml(tmp_path, "contrario: {nombre: A, id_crm: '1128'}\n"))
    c = f.contrarios[0]
    assert (c.id_crm, c.nif, c.email) == ("1128", "", "")


def test_sin_nif_email_ni_id_crm_el_mensaje_nombra_las_tres(tmp_path):
    with pytest.raises(ValueError) as e:
        cf.cargar_ficha_yaml(_yaml(tmp_path, "contrario: {nombre: A}\n"))
    assert "falta NIF, email o id_crm" in str(e.value)


@pytest.mark.parametrize("rol", ["contrario", "colaborador"])
@pytest.mark.parametrize("valor, canonico", [("'1128'", "1128"), ("1128", "1128"),
                                             ("' 01128 '", "1128")])
def test_id_crm_admite_entero_o_digitos(tmp_path, rol, valor, canonico):
    texto = (f"contrario: {{nombre: A, id_crm: {valor}}}\n" if rol == "contrario"
             else f"colaboradores:\n  - {{nombre: A, id_crm: {valor}}}\n")
    f = cf.cargar_ficha_yaml(_yaml(tmp_path, texto))
    parte = f.contrarios[0] if rol == "contrario" else f.colaboradores[0]
    assert parte.id_crm == canonico


@pytest.mark.parametrize("valor", ["'12a'", "true", "[1]", "''", "0", "-3", "1.5"])
def test_id_crm_que_no_es_el_numero_de_una_ficha_se_rechaza(tmp_path, valor):
    # El motivo, no solo la ruta: «contrario.id_crm: clave desconocida» también empieza así, y
    # con él este test pasaba antes de que `id_crm` existiera.
    with pytest.raises(ValueError,
                       match=re.escape("contrario.id_crm:") + ".*no es el número de una ficha"):
        cf.cargar_ficha_yaml(_yaml(tmp_path,
                                   f"contrario: {{nombre: A, nif: '1', id_crm: {valor}}}\n"))


def test_id_crm_null_es_no_hay_dato(tmp_path):                     # control positivo
    f = cf.cargar_ficha_yaml(_yaml(tmp_path, "contrario: {nombre: A, nif: '1', id_crm: null}\n"))
    assert f.contrarios[0].id_crm == ""


def test_id_crm_no_entra_en_la_declaracion(tmp_path):
    """La declaración es lo que se COMPARA con la ficha; el id es cómo se llega a ella."""
    f = cf.cargar_ficha_yaml(_yaml(tmp_path, "contrario: {nombre: A, id_crm: '1128'}\n"
                                             "colaboradores:\n  - {nombre: B, id_crm: 776}\n"))
    assert f.declarados_contrarios == [{"nombre": "A"}]
    assert f.declarados_colaboradores == [{"nombre": "B"}]


# ---------------------------------------------------------------------------
# Task 6 — lo que se audita es la declaración (B.2)
# ---------------------------------------------------------------------------

def test_la_declaracion_se_conserva_sin_normalizar(tmp_path):
    """La auditoría compara la DECLARACIÓN (R2/H-02): el DTO normaliza, la declaración no."""
    f = cf.cargar_ficha_yaml(_yaml(tmp_path,
        "contrario: {nombre: ' A ', nif: '1', movil: '+34 600 111 222'}\n"
        "colaboradores:\n  - {nombre: B, email: b@x.es, telefono: '93 111 22 33'}\n"))
    assert f.contrarios[0].movil == "600111222"
    assert f.declarados_contrarios == [{"nombre": "A", "nif": "1", "movil": "+34 600 111 222"}]
    assert f.declarados_colaboradores == [{"nombre": "B", "email": "b@x.es",
                                           "telefono": "93 111 22 33"}]
