"""Carga y validación de `_mapa_procesal.yaml` (spec §3.1, §3.2) con gramática (I3)."""
import pytest

from core.procedimiento import mapa

CARP = "03_Ordinario - Demanda y documentos"


def _escribir(tmp_path, texto: str):
    d = tmp_path / "05_Procedimiento"
    d.mkdir(parents=True, exist_ok=True)
    (d / mapa.MAPA_FILENAME).write_text(texto, encoding="utf-8")
    return tmp_path


def test_carga_el_camino_feliz(tmp_path):
    raiz = _escribir(tmp_path, f"""
version: 1
expediente_crm: '540'
carpetas:
  "{CARP}":
    - {{origen: crm, doc_id: '34939', orden: 'D-01', descripcion: encargo_de_venta}}
    - {{origen: despacho, fichero: CONCLUSIONES_W-02VEKE.docx}}
sin_asignar:
  - {{doc_id: '42498', fichero: citacion.pdf, lote: '2026-07-27T16:35'}}
""")
    m = mapa.cargar(raiz)
    assert m.version == 1
    assert m.expediente_crm == "540"
    crm, desp = m.entradas
    assert crm.logical_key == "crm:540:34939"
    assert crm.sin_cobertura_ok is False
    assert desp.logical_key == "despacho:CONCLUSIONES_W-02VEKE.docx"
    assert len(m.sin_asignar) == 1


def test_acumula_TODOS_los_problemas_no_solo_el_primero(tmp_path):
    """Reportar el primero obliga al letrado a N pasadas para N errores."""
    raiz = _escribir(tmp_path, """
version: 1
expediente_crm: '540'
carpetas:
  "99_Carpeta inventada":
    - {origen: crm, doc_id: '1', orden: '00', descripcion: x}
  "05_Otros escritos":
    - {origen: marciano, doc_id: '2', orden: '00', descripcion: y}
    - {origen: despacho, fichero: 'sub/dir/escrito.docx'}
""")
    with pytest.raises(mapa.MapaInvalidoError) as exc:
        mapa.cargar(raiz)
    assert len(exc.value.problemas) == 3
    txt = "\n".join(exc.value.problemas)
    assert "99_Carpeta inventada" in txt and "marciano" in txt and "sub/dir" in txt


@pytest.mark.parametrize("orden", ["../00", "..", "00/..", "aaaa40", "", "00 ", "./00"])
def test_un_orden_sin_gramatica_se_RECHAZA(tmp_path, orden):
    """El defecto de la rev. 1: `orden` se incrustaba en el nombre sin validar, así que
    `../00` producía un destino fuera de la carpeta de fase."""
    raiz = _escribir(tmp_path, f"""
version: 1
expediente_crm: '540'
carpetas:
  "05_Otros escritos":
    - {{origen: crm, doc_id: '1', orden: '{orden}', descripcion: x}}
""")
    with pytest.raises(mapa.MapaInvalidoError) as exc:
        mapa.cargar(raiz)
    assert "orden" in "\n".join(exc.value.problemas)


@pytest.mark.parametrize("orden", ["00", "01", "D-01", "D-02A", "999", "DA-9"])
def test_los_ordenes_legitimos_pasan(tmp_path, orden):
    raiz = _escribir(tmp_path, f"""
version: 1
expediente_crm: '540'
carpetas:
  "05_Otros escritos":
    - {{origen: crm, doc_id: '1', orden: '{orden}', descripcion: x}}
""")
    assert mapa.cargar(raiz).entradas[0].orden == orden


def test_un_string_false_NO_autoriza_el_override(tmp_path):
    """`bool('false')` es `True`. El operador puede creer desactivado un permiso que está
    ejercido, y este permiso autoriza a copiar documentos no buscables."""
    raiz = _escribir(tmp_path, """
version: 1
expediente_crm: '540'
carpetas:
  "05_Otros escritos":
    - {origen: crm, doc_id: '1', orden: '00', descripcion: x, sin_cobertura_ok: 'false'}
""")
    with pytest.raises(mapa.MapaInvalidoError) as exc:
        mapa.cargar(raiz)
    assert "sin_cobertura_ok" in "\n".join(exc.value.problemas)


def test_un_booleano_de_verdad_si_autoriza(tmp_path):
    raiz = _escribir(tmp_path, """
version: 1
expediente_crm: '540'
carpetas:
  "05_Otros escritos":
    - {origen: crm, doc_id: '1', orden: '00', descripcion: x, sin_cobertura_ok: true}
""")
    assert mapa.cargar(raiz).entradas[0].sin_cobertura_ok is True


def test_una_version_booleana_no_pasa_por_uno(tmp_path):
    raiz = _escribir(tmp_path, "version: true\nexpediente_crm: '540'\ncarpetas: {}\n")
    with pytest.raises(mapa.MapaInvalidoError) as exc:
        mapa.cargar(raiz)
    assert "version" in "\n".join(exc.value.problemas)


@pytest.mark.parametrize("fichero,fragmento", [
    ("'../fuera.docx'", "basename"),
    ("'/abs/escrito.docx'", "basename"),
    ("'CON'", "reservado"),
    ("'NUL.extra.docx'", "reservado"),
    ("'COM1.docx'", "reservado"),
    ("'escrito.docx '", "espacios o puntos"),
    ("'escrito.'", "espacios o puntos"),
    ("'a:b.docx'", "caracter"),
    ("'q?.docx'", "caracter"),
])
def test_rechaza_ficheros_invalidos_del_despacho(tmp_path, fichero, fragmento):
    raiz = _escribir(tmp_path, f"""
version: 1
expediente_crm: '540'
carpetas:
  "05_Otros escritos":
    - {{origen: despacho, fichero: {fichero}}}
""")
    with pytest.raises(mapa.MapaInvalidoError) as exc:
        mapa.cargar(raiz)
    assert fragmento in "\n".join(exc.value.problemas)


def test_una_clave_YAML_duplicada_no_sustituye_una_decision_en_silencio(tmp_path):
    """`safe_load` se queda la última y el letrado no se enteraría de que su primera
    asignación de esa carpeta desapareció."""
    raiz = _escribir(tmp_path, """
version: 1
expediente_crm: '540'
carpetas:
  "05_Otros escritos":
    - {origen: crm, doc_id: '1', orden: '00', descripcion: primera}
  "05_Otros escritos":
    - {origen: crm, doc_id: '2', orden: '01', descripcion: segunda}
""")
    with pytest.raises(mapa.MapaInvalidoError) as exc:
        mapa.cargar(raiz)
    assert "duplicada" in "\n".join(exc.value.problemas)


def test_rechaza_clave_logica_duplicada_entre_carpetas(tmp_path):
    raiz = _escribir(tmp_path, f"""
version: 1
expediente_crm: '540'
carpetas:
  "01_Monitorio - Demanda y documentos":
    - {{origen: crm, doc_id: '77', orden: '00', descripcion: demanda}}
  "{CARP}":
    - {{origen: crm, doc_id: '77', orden: '00', descripcion: demanda}}
""")
    with pytest.raises(mapa.MapaInvalidoError) as exc:
        mapa.cargar(raiz)
    assert "crm:540:77" in "\n".join(exc.value.problemas)


def test_dos_entradas_que_producen_el_MISMO_nombre_final_colisionan(tmp_path):
    """Distinto de la clave lógica duplicada: son dos documentos distintos que darían el
    mismo destino, y en Windows la comparación es `casefold`."""
    raiz = _escribir(tmp_path, """
version: 1
expediente_crm: '540'
carpetas:
  "05_Otros escritos":
    - {origen: crm, doc_id: '1', orden: '00', descripcion: Decreto_Admision}
    - {origen: crm, doc_id: '2', orden: '00', descripcion: decreto_admision}
""")
    with pytest.raises(mapa.MapaInvalidoError) as exc:
        mapa.cargar(raiz)
    assert "mismo nombre" in "\n".join(exc.value.problemas)


def test_dos_ficheros_del_DESPACHO_que_solo_difieren_en_mayusculas_colisionan(tmp_path):
    """Aquí es donde el `casefold` del tronco paga, y no en la rama CRM.

    `_slug()` ya pasa a minúsculas la descripción del CRM, así que dos entradas `crm` que
    solo difieran en mayúsculas colisionan igual sin `casefold` — el mutante que lo quita
    sobrevivía a mi primer test por eso. La rama `despacho` conserva el nombre TAL CUAL, y
    en Windows `MINUTA.docx` y `minuta.docx` son el mismo fichero.
    """
    raiz = _escribir(tmp_path, """
version: 1
expediente_crm: '540'
carpetas:
  "05_Otros escritos":
    - {origen: despacho, fichero: MINUTA.docx}
    - {origen: despacho, fichero: minuta.docx}
""")
    with pytest.raises(mapa.MapaInvalidoError) as exc:
        mapa.cargar(raiz)
    assert "mismo nombre" in chr(10).join(exc.value.problemas)


def test_dos_descripciones_que_NORMALIZAN_al_mismo_slug_colisionan(tmp_path):
    """`Mediación` y `Mediacion` dan el mismo slug: son un destino, no dos."""
    raiz = _escribir(tmp_path, """
version: 1
expediente_crm: '540'
carpetas:
  "05_Otros escritos":
    - {origen: crm, doc_id: '1', orden: 'D-02', descripcion: 'Contrato de Mediación'}
    - {origen: crm, doc_id: '2', orden: 'D-02', descripcion: 'contrato de mediacion'}
""")
    with pytest.raises(mapa.MapaInvalidoError) as exc:
        mapa.cargar(raiz)
    assert "mismo nombre" in "\n".join(exc.value.problemas)


def test_una_descripcion_que_queda_vacia_al_normalizar_se_rechaza(tmp_path):
    raiz = _escribir(tmp_path, """
version: 1
expediente_crm: '540'
carpetas:
  "05_Otros escritos":
    - {origen: crm, doc_id: '1', orden: '00', descripcion: '...---...'}
""")
    with pytest.raises(mapa.MapaInvalidoError) as exc:
        mapa.cargar(raiz)
    assert "descripcion" in "\n".join(exc.value.problemas)


def test_yaml_ilegible_y_mapa_ausente_no_degradan_a_vacio(tmp_path):
    raiz = _escribir(tmp_path, "version: 1\ncarpetas: [[[\n")
    with pytest.raises(mapa.MapaInvalidoError):
        mapa.cargar(raiz)
    (tmp_path / "otro" / "05_Procedimiento").mkdir(parents=True)
    with pytest.raises(mapa.MapaInvalidoError) as exc:
        mapa.cargar(tmp_path / "otro")
    assert "no existe" in "\n".join(exc.value.problemas)


def test_nombre_destino_crm_y_despacho():
    crm = mapa.EntradaMapa(carpeta=CARP, origen="crm", doc_id="1", orden="D-02",
                           descripcion="Contrato de Mediación")
    assert mapa.nombre_destino(crm, "pdf") == "D-02_contrato_de_mediacion.pdf"
    desp = mapa.EntradaMapa(carpeta=CARP, origen="despacho",
                            fichero="CONCLUSIONES_W-02VEKE.docx")
    assert mapa.nombre_destino(desp, "docx") == "CONCLUSIONES_W-02VEKE.docx", (
        "la herramienta no renombra lo que no ha creado")


def test_el_presupuesto_de_longitud_cuenta_el_TEMPORAL(tmp_path):
    """La rev. 1 presupuestaba la ruta final y se olvidaba del temporal, que sale unos
    caracteres más largo: la promesa de respetar el límite quedaba incumplida."""
    largo = "D-02_" + ("x" * 400) + ".pdf"
    n = mapa.presupuesto_longitud(tmp_path, "05_Otros escritos", largo)
    final = (tmp_path / "05_Procedimiento" / "05_Otros escritos" / n).resolve()
    temporal = final.with_name(f".{n}.{'9' * 6}.tmp")
    assert len(str(final)) <= mapa.LIMITE_RUTA
    assert len(str(temporal)) <= mapa.LIMITE_RUTA, (
        "el temporal no cabe: la escritura de 4b fallaría con el nombre que 4a bendijo")
    assert n.endswith(".pdf")


def test_el_truncado_es_ESTABLE_entre_llamadas(tmp_path):
    largo = "D-02_" + ("y" * 400) + ".pdf"
    a = mapa.presupuesto_longitud(tmp_path, "05_Otros escritos", largo)
    b = mapa.presupuesto_longitud(tmp_path, "05_Otros escritos", largo)
    assert a == b, "un sufijo inestable haría que cada corrida viera un cambio"


def test_un_nombre_que_cabe_no_se_toca(tmp_path):
    assert mapa.presupuesto_longitud(
        tmp_path, "05_Otros escritos", "D-02_corto.pdf") == "D-02_corto.pdf"


# ---------------------------------------------------------------- R1/H-13 y H-14

def test_un_orden_con_SALTO_DE_LINEA_final_se_rechaza(tmp_path):
    """En Python `$` casa tambien justo antes de un salto final, asi que `match` aceptaba
    `orden: "00\n"` y metia un caracter de control en el nombre del fichero. `fullmatch`
    no (R1/H-13)."""
    raiz = _escribir(tmp_path, """
version: 1
expediente_crm: '540'
carpetas:
  "05_Otros escritos":
    - {origen: crm, doc_id: '1', orden: "00\n", descripcion: x}
""")
    with pytest.raises(mapa.MapaInvalidoError) as exc:
        mapa.cargar(raiz)
    assert "orden" in chr(10).join(exc.value.problemas)


@pytest.mark.parametrize("fichero", ["'COM¹.docx'", "'LPT².txt'", "'com³'"])
def test_los_reservados_con_SUPERINDICE_tambien_se_rechazan(tmp_path, fichero):
    """Windows reserva COM/LPT con ¹ ² ³ ademas de con 1-9 (R1/H-13)."""
    raiz = _escribir(tmp_path, f"""
version: 1
expediente_crm: '540'
carpetas:
  "05_Otros escritos":
    - {{origen: despacho, fichero: {fichero}}}
""")
    with pytest.raises(mapa.MapaInvalidoError) as exc:
        mapa.cargar(raiz)
    assert "reservado" in chr(10).join(exc.value.problemas)


@pytest.mark.parametrize("valor,que", [
    ("['1']", "doc_id"),
    ("{a: b}", "doc_id"),
])
def test_un_doc_id_que_no_es_un_id_se_rechaza(tmp_path, valor, que):
    """Se convertian a su repr de Python y acababan en la clave logica."""
    raiz = _escribir(tmp_path, f"""
version: 1
expediente_crm: '540'
carpetas:
  "05_Otros escritos":
    - {{origen: crm, doc_id: {valor}, orden: '00', descripcion: x}}
""")
    with pytest.raises(mapa.MapaInvalidoError) as exc:
        mapa.cargar(raiz)
    assert que in chr(10).join(exc.value.problemas)


def test_una_descripcion_que_es_una_lista_se_rechaza(tmp_path):
    raiz = _escribir(tmp_path, """
version: 1
expediente_crm: '540'
carpetas:
  "05_Otros escritos":
    - {origen: crm, doc_id: '1', orden: '00', descripcion: [a, b]}
""")
    with pytest.raises(mapa.MapaInvalidoError) as exc:
        mapa.cargar(raiz)
    assert "descripcion" in chr(10).join(exc.value.problemas)


@pytest.mark.parametrize("valor", ["true", "'   '"])
def test_un_expediente_crm_que_no_es_un_id_se_rechaza(tmp_path, valor):
    """`true` pasaba a `'True'` y un expediente de espacios quedaba vacio DESPUES de
    validarse."""
    raiz = _escribir(tmp_path, f"version: 1\nexpediente_crm: {valor}\ncarpetas: {{}}\n")
    with pytest.raises(mapa.MapaInvalidoError) as exc:
        mapa.cargar(raiz)
    assert "expediente_crm" in chr(10).join(exc.value.problemas)


def test_el_presupuesto_cuenta_UNIDADES_UTF16_y_no_puntos_de_codigo(tmp_path):
    """R1/H-14: un caracter fuera del BMP ocupa DOS unidades. Presupuestar con `len()`
    autorizaba un temporal de 294 unidades creyendo que eran 259."""
    def u16(s):
        """Se mide AQUÍ y no con `mapa._unidades_utf16`: un test que usa la función que
        prueba **muta con ella**, y el mutante que la degrada a `len()` sobrevivía por
        eso. El instrumento del test tiene que ser independiente del que mide el código.
        """
        return len(s.encode("utf-16-le")) // 2

    raiz = tmp_path / ("emoji_" + "\U0001F600" * 40)      # 40 pares suplentes
    n = mapa.presupuesto_longitud(raiz, "05_Otros escritos", "D-02_" + "x" * 300 + ".pdf")
    final = (raiz / "05_Procedimiento" / "05_Otros escritos" / n)
    temporal = final.with_name(f".{n}.{'9' * 6}.tmp")
    assert u16(str(temporal)) <= mapa.LIMITE_RUTA, (
        f"{u16(str(temporal))} unidades UTF-16 sobre un límite de {mapa.LIMITE_RUTA}; "
        f"`len()` decía {len(str(temporal))} — esa es justo la diferencia")


def test_el_truncado_no_parte_un_par_suplente(tmp_path):
    """Cortar directamente en unidades UTF-16 partiria un emoji por la mitad."""
    n = mapa.presupuesto_longitud(tmp_path, "05_Otros escritos",
                                  "D-02_" + "\U0001F600" * 200 + ".pdf")
    n.encode("utf-8")                       # no lanza: no hay surrogate suelto
    assert n.endswith(".pdf")


def test_el_nombre_del_CRM_no_PUEDE_ser_un_reservado_y_por_que(tmp_path):
    """**La validacion del nombre CRM es defensa en profundidad INERTE hoy, y se dice.**

    Se le pasa `nombre_destino(e, "pdf")` por `_validar_nombre_windows` igual que al del
    despacho, pero **no puede disparar**: el nombre del CRM es siempre
    `<orden>_<slug>.<ext>`, el `orden` esta constrenido por la gramatica a empezar por
    letra o digito, y `_slug` reduce la descripcion a `[a-z0-9_]`. Un reservado de Windows
    es un token unico sin `_`, asi que el prefijo lo hace estructuralmente imposible.

    Se conserva porque si manana cambia la gramatica o el slug, la guarda ya esta puesta.
    Pero un test que afirmara que «caza» algo seria falso, y una guarda inerte que se cree
    activa es peor que no tenerla. Lo que este test prueba es la razon, no la captura.
    """
    raiz = _escribir(tmp_path, """
version: 1
expediente_crm: '540'
carpetas:
  "05_Otros escritos":
    - {origen: crm, doc_id: '1', orden: '00', descripcion: 'nul'}
""")
    (e,) = mapa.cargar(raiz).entradas
    nombre = mapa.nombre_destino(e, "pdf")
    assert nombre == "00_nul.pdf"
    assert nombre.split(".")[0].lower() not in mapa._RESERVADOS_WINDOWS, (
        "el prefijo del orden es lo que lo hace imposible")
    # y el control: sin el prefijo, la guarda SI cazaria
    problemas = []
    assert mapa._validar_nombre_windows("nul.pdf", "sonda", problemas) is False
    assert "reservado" in problemas[0]
