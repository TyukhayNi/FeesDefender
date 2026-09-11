"""`verificar_apertura` — el «OK» del expediente (pieza P2 de la fila #28 de `PLAN.md`).

**El control positivo no es un extra aquí: es la razón de ser del fichero.** Esta pieza
existe porque ocho herramientas dijeron «OK» de su paso el 2026-09-10 mientras el
expediente estaba a medias. Una verja que solo puede decir `ok` repite ese defecto una
capa más arriba, con el agravante de que ahora el «OK» dice ser del expediente.

Así que **cada comprobación implementada tiene aquí su caso en rojo**, construido a mano
sobre un árbol sintético, y ese caso reproduce el defecto real que la motivó. Si alguna
comprobación dejara de poder ponerse roja, su test lo diría.

Ningún test escribe en el árbol de producción: todo lo que estos tests crean va a
`tmp_path`. (La R1 midió que openpyxl abre además sus propios temporales en el
directorio temporal del proceso al serializar un libro — no es el árbol de
producción, pero «todo en tmp_path» se leía como si lo cubriera.)
"""
import json

import pytest
import yaml

from core import verificar_apertura as va

CASE = "BaRS3 - Calle de Prueba 1 (W-TEST01) - Vuelta"


# --- Árbol sintético ---------------------------------------------------------------


def _caso(tmp_path, nombre=CASE):
    d = tmp_path / nombre
    (d / "00_Input").mkdir(parents=True)
    return d


def _con_sala_maquina(case_dir, filas):
    sm = case_dir / "01_Procesado" / "02_Sala de máquina"
    sm.mkdir(parents=True, exist_ok=True)
    (sm / "_cobertura.json").write_text(json.dumps(filas, ensure_ascii=False),
                                        encoding="utf-8")
    return sm


def _con_catalogo(case_dir, n):
    proc = case_dir / "01_Procesado"
    proc.mkdir(parents=True, exist_ok=True)
    entradas = [{"slug": f"doc_{i}", "titulo": f"Documento {i}"} for i in range(n)]
    (proc / "indice_documental.yaml").write_text(
        yaml.dump(entradas, allow_unicode=True), encoding="utf-8")


def _con_sala_lectura(case_dir, *, artefactos=("INDICE.md", "CRONOLOGIA.md",
                                               "_MANIFIESTO.md")):
    sala = case_dir / "01_Procesado" / "Sala lectura"
    sala.mkdir(parents=True, exist_ok=True)
    for a in artefactos:
        (sala / a).write_text(f"# {a}\ncontenido\n", encoding="utf-8")
    return sala


def _con_espejos(case_dir, textos: dict[str, str]):
    md = case_dir / "01_Procesado" / "02_Sala de máquina" / "03_MD"
    md.mkdir(parents=True, exist_ok=True)
    for nombre, texto in textos.items():
        (md / nombre).write_text(texto, encoding="utf-8")
    return md


def _r(case_dir, ident):
    """El resultado de una comprobación por su id."""
    return next(r for r in va.verificar(case_dir).resultados if r.id == ident)


# --- El contrato del informe --------------------------------------------------------


def test_el_informe_enumera_SIEMPRE_las_nueve(tmp_path):
    """Un informe que solo lista lo que sabe mirar es el falso «OK» de siempre.

    Sobre un expediente vacío, donde casi nada se puede comprobar, tienen que salir las
    nueve igualmente: cinco declaradas sin implementar y cuatro en `pendiente`.
    """
    informe = va.verificar(_caso(tmp_path))
    assert len(informe.resultados) == 9
    assert len({r.id for r in informe.resultados}) == 9


def test_sin_implementar_NO_cuenta_como_comprobada(tmp_path):
    """Si contara, el resumen diría «9 de 9» habiendo mirado 4.

    Es el mismo modo de fallo que la pieza cierra, cometido por la pieza. El resumen
    tiene que separar lo medido de lo declarado.
    """
    informe = va.verificar(_caso(tmp_path))
    sin_impl = [r for r in informe.resultados if r.estado == va.SIN_IMPLEMENTAR]
    assert len(sin_impl) == 5, "cambió el reparto: revisa el resumen y el plan"
    assert len(informe.comprobadas) == 4
    assert "4 de 9" in informe.resumen
    for r in sin_impl:
        assert "no construida" in r.detalle
        assert r.detalle != "", "un hueco sin motivo no es una declaración"


def test_un_estado_inventado_revienta_al_construir(tmp_path):
    """El vocabulario es cerrado: `casi_ok` no puede existir."""
    with pytest.raises(ValueError, match="fuera de"):
        va.Resultado("x", "X", "casi_ok", "…")


def test_una_comprobacion_que_revienta_no_tumba_el_informe(tmp_path, monkeypatch):
    """Las otras ocho siguen valiendo, y se dice cuál murió.

    Un verificador que muere a mitad deja al operador sin lo que sí podía darle.
    """
    def revienta(case_dir):
        raise RuntimeError("boom")

    monkeypatch.setattr(va, "COMPROBACIONES", (revienta,) + va.COMPROBACIONES[1:])
    informe = va.verificar(_caso(tmp_path))
    assert len(informe.resultados) == 9
    roto = informe.resultados[0]
    assert roto.estado == va.FALLO and "reventó" in roto.detalle and "boom" in roto.detalle


# --- C3: cobertura contra catálogo --------------------------------------------------


def test_c3_ok_cuando_los_documentos_logicos_cuadran(tmp_path):
    c = _caso(tmp_path)
    _con_sala_maquina(c, [{"slug": "a", "parent_slug": ""},
                          {"slug": "b", "parent_slug": ""}])
    _con_catalogo(c, 2)
    r = _r(c, "cobertura_vs_catalogo")
    assert r.estado == va.OK, r.detalle


def test_c3_los_hijos_de_bundle_NO_cuentan(tmp_path):
    """`[APER-60]` con la corrección del 102º, y es lo que hace comparables los lados.

    Un PDF segmentado en tres piezas da cuatro filas de cobertura y **una** entrada de
    catálogo. Sin restar los hijos, el caso sano saldría en rojo — y una verja que grita
    sobre lo correcto se acaba ignorando.
    """
    c = _caso(tmp_path)
    _con_sala_maquina(c, [{"slug": "bundle", "parent_slug": ""},
                          {"slug": "s1", "parent_slug": "bundle"},
                          {"slug": "s2", "parent_slug": "bundle"},
                          {"slug": "s3", "parent_slug": "bundle"}])
    _con_catalogo(c, 1)
    r = _r(c, "cobertura_vs_catalogo")
    assert r.estado == va.OK, r.detalle
    assert r.evidencia["hijos_de_bundle"] == 3
    assert r.evidencia["documentos_logicos"] == 1


def test_c3_FALLA_cuando_faltan_documentos_en_el_catalogo(tmp_path):
    """CONTROL POSITIVO. Es el defecto de `poblar` pisando por nombre canónico: la
    sala de máquina procesó 21 documentos y a la sala llegaron 17."""
    c = _caso(tmp_path)
    _con_sala_maquina(c, [{"slug": f"d{i}", "parent_slug": ""} for i in range(21)])
    _con_catalogo(c, 17)
    r = _r(c, "cobertura_vs_catalogo")
    assert r.estado == va.FALLO
    assert "21" in r.detalle and "17" in r.detalle
    assert r.evidencia["documentos_logicos"] == 21
    assert r.evidencia["entradas_catalogo"] == 17


def test_c3_pendiente_si_la_sala_de_maquina_no_ha_corrido(tmp_path):
    """`pendiente` no es `fallo`: un caso a medias no puede salir en rojo."""
    r = _r(_caso(tmp_path), "cobertura_vs_catalogo")
    assert r.estado == va.PENDIENTE


def test_c3_FALLA_con_un_cobertura_json_ilegible(tmp_path):
    c = _caso(tmp_path)
    sm = _con_sala_maquina(c, [])
    (sm / "_cobertura.json").write_text("{roto", encoding="utf-8")
    _con_catalogo(c, 1)
    r = _r(c, "cobertura_vs_catalogo")
    assert r.estado == va.FALLO and "ilegible" in r.detalle


# --- C4: los cuatro artefactos de la sala -------------------------------------------


def test_c4_ok_con_los_cuatro(tmp_path):
    c = _caso(tmp_path)
    _con_sala_lectura(c)
    _con_catalogo(c, 1)
    r = _r(c, "artefactos_sala")
    assert r.estado == va.OK, r.detalle


def test_c4_FALLA_con_dos_de_cuatro(tmp_path):
    """CONTROL POSITIVO, y es el escenario literal de `MEJORAS #221`: el CLI dijo
    «Sala de lectura organizada» habiendo escrito dos de los cuatro artefactos."""
    c = _caso(tmp_path)
    _con_sala_lectura(c, artefactos=("INDICE.md", "CRONOLOGIA.md"))
    r = _r(c, "artefactos_sala")
    assert r.estado == va.FALLO
    assert "_MANIFIESTO.md" in r.detalle and "indice_documental.yaml" in r.detalle
    assert sorted(r.evidencia["presentes"]) == ["CRONOLOGIA.md", "INDICE.md"]


def test_c4_un_artefacto_VACIO_cuenta_como_ausente(tmp_path):
    """CONTROL POSITIVO de la otra mitad. Un fichero de cero bytes existe para
    `is_file()` y no dice nada: el modo de fallo es el mismo que si faltara, y
    distinguirlo solo sirve para que el operador sepa qué mirar."""
    c = _caso(tmp_path)
    sala = _con_sala_lectura(c)
    _con_catalogo(c, 1)
    (sala / "CRONOLOGIA.md").write_text("", encoding="utf-8")
    r = _r(c, "artefactos_sala")
    assert r.estado == va.FALLO and "VACÍOS" in r.detalle
    assert r.evidencia["vacios"] == ["CRONOLOGIA.md"]


def test_c4_pendiente_sin_sala(tmp_path):
    r = _r(_caso(tmp_path), "artefactos_sala")
    assert r.estado == va.PENDIENTE


# --- C8: W-codes ajenos en los espejos ----------------------------------------------


def test_c8_ok_sin_ajenos(tmp_path):
    c = _caso(tmp_path)
    _con_espejos(c, {"a.md": "Expediente W-TEST01, sin nada más.\n",
                     "b.md": "Un documento cualquiera.\n"})
    r = _r(c, "wcodes_ajenos")
    assert r.estado == va.OK, r.detalle
    assert r.evidencia["propio"] == "W-TEST01"
    assert r.evidencia["espejos_leidos"] == 2


def test_c8_FALLA_con_un_wcode_ajeno_DENTRO_del_texto(tmp_path):
    """CONTROL POSITIVO, y es exactamente `MEJORAS #235`.

    El barrido de documental ajena mira los NOMBRES de fichero, así que un W-code que va
    dentro del documento le es invisible. En W-02V48N eso obligó a barrer 235 ficheros a
    mano en cuatro tandas.
    """
    c = _caso(tmp_path)
    _con_espejos(c, {"propio.md": "Caso W-TEST01.\n",
                     "colado.md": "…referencia al expediente W-04AAAA de otro caso.\n"})
    r = _r(c, "wcodes_ajenos")
    assert r.estado == va.FALLO
    assert "W-04AAAA" in r.detalle
    assert r.evidencia["ajenos"]["W-04AAAA"] == ["colado.md"]


def test_c8_pendiente_si_no_hay_referencia_contra_la_que_comparar(tmp_path):
    """Sin W-code propio, un barrido diría «todos ajenos»: se declara, no se inventa."""
    c = _caso(tmp_path, nombre="Carpeta sin codigo")
    _con_espejos(c, {"a.md": "W-04AAAA\n"})
    r = _r(c, "wcodes_ajenos")
    assert r.estado == va.PENDIENTE and "sin referencia" in r.detalle


def test_c8_pendiente_sin_espejos(tmp_path):
    r = _r(_caso(tmp_path), "wcodes_ajenos")
    assert r.estado == va.PENDIENTE


# --- C5: las 88 filas de viabilidad -------------------------------------------------


def _informe_viabilidad(case_dir, filas):
    """`filas` = [(id, respuesta, pendiente)] sobre una hoja PREGUNTAS mínima."""
    openpyxl = pytest.importorskip("openpyxl")
    an = case_dir / "02_Analisis"
    an.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "PREGUNTAS"
    for i, (idq, resp, pend) in enumerate(filas, start=6):
        ws.cell(i, 3).value = idq
        ws.cell(i, 9).value = resp
        ws.cell(i, 13).value = pend
    destino = an / "Informe viabilidad LLM - W-TEST01.xlsx"
    wb.save(destino)
    wb.close()
    return destino


def test_c5_ok_con_todas_marcadas(tmp_path):
    c = _caso(tmp_path)
    _informe_viabilidad(c, [(f"q{i}", None, "sí") for i in range(88)])
    r = _r(c, "viabilidad_completa")
    assert r.estado == va.OK, r.detalle
    assert r.evidencia["filas_con_id"] == 88
    assert r.evidencia["preguntas_distintas"] == 88


def test_c5_FALLA_con_filas_en_blanco(tmp_path):
    """CONTROL POSITIVO, con las cifras reales del 2026-09-10: 51 de 88 marcadas.

    El generador decía «OK». Ésta es la comprobación que el letrado hizo a mano contando
    la columna del `.xlsx`.
    """
    c = _caso(tmp_path)
    filas = ([(f"q{i}", None, "sí") for i in range(51)]
             + [(f"q{i}", None, None) for i in range(51, 88)])
    _informe_viabilidad(c, filas)
    r = _r(c, "viabilidad_completa")
    assert r.estado == va.FALLO
    assert "37" in r.detalle and "88" in r.detalle
    assert r.evidencia["sin_marcar"] == 37


def test_c5_una_respuesta_sin_marca_NO_es_un_hueco(tmp_path):
    """La fila está resuelta: tiene respuesta documental aunque falte la marca.

    Sin este caso, la comprobación gritaría sobre informes correctos y acabaría
    ignorada — que es como muere una verja.
    """
    c = _caso(tmp_path)
    _informe_viabilidad(c, [(f"q{i}", "consta en el encargo", None) for i in range(88)])
    r = _r(c, "viabilidad_completa")
    assert r.estado == va.OK, r.detalle


def test_c5_pendiente_si_la_plantilla_cambia_de_numero(tmp_path):
    """Todas marcadas pero no son 88: no es un fallo del expediente, es que el «88» de
    todas partes dejó de ser cierto. Se dice en vez de normalizarlo."""
    c = _caso(tmp_path)
    _informe_viabilidad(c, [(f"q{i}", None, "sí") for i in range(90)])
    r = _r(c, "viabilidad_completa")
    assert r.estado == va.PENDIENTE and "90" in r.detalle


def test_c5_pendiente_sin_informe(tmp_path):
    r = _r(_caso(tmp_path), "viabilidad_completa")
    assert r.estado == va.PENDIENTE


def test_c5_FALLA_si_el_xlsx_no_tiene_hoja_PREGUNTAS(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    c = _caso(tmp_path)
    an = c / "02_Analisis"
    an.mkdir(parents=True)
    wb = openpyxl.Workbook()
    wb.active.title = "OTRA"
    wb.save(an / "Informe viabilidad - X.xlsx")
    wb.close()
    r = _r(c, "viabilidad_completa")
    assert r.estado == va.FALLO and "PREGUNTAS" in r.detalle


# --- El CLI --------------------------------------------------------------------------


def _cli(tmp_path, monkeypatch, case_dir, args=()):
    from typer.testing import CliRunner

    from core.casos import case_locator as cl
    from scripts import verificar_apertura as cli

    monkeypatch.setattr(cl, "buscar", lambda cid: case_dir)
    return CliRunner().invoke(cli.app, ["--case-id", "W-TEST01", *args])


def test_cli_sale_con_1_si_hay_un_fallo(tmp_path, monkeypatch):
    """El código de salida es el resultado, no el «se ejecutó sin excepciones»."""
    c = _caso(tmp_path)
    _con_sala_lectura(c, artefactos=("INDICE.md",))
    r = _cli(tmp_path, monkeypatch, c)
    assert r.exit_code == 1, r.output
    assert "FALLO" in r.output


def test_cli_sale_con_0_con_pendientes_pero_sin_fallos(tmp_path, monkeypatch):
    """`pendiente` NO es fallo. Si lo fuera, un expediente a medias saldría en rojo
    siempre y el rojo dejaría de significar algo."""
    r = _cli(tmp_path, monkeypatch, _caso(tmp_path))
    assert r.exit_code == 0, r.output
    assert "pendiente" in r.output


def test_cli_dice_SIEMPRE_lo_que_no_ha_comprobado(tmp_path, monkeypatch):
    """Incluso con `--solo-problemas`, que filtra esas líneas.

    Un resumen que solo cuenta lo que miró es el falso «OK» que este comando cierra. El
    aviso tiene que sobrevivir al filtro, porque el filtro es justo cuando el operador
    deja de ver la lista entera.
    """
    r = _cli(tmp_path, monkeypatch, _caso(tmp_path), ["--solo-problemas"])
    assert "NO construidas todavía" in r.output
    assert "SIN VERIFICAR" in r.output
    assert "4 de 9" in r.output


def test_cli_json_lleva_las_nueve_con_su_evidencia(tmp_path, monkeypatch):
    import json as _json

    c = _caso(tmp_path)
    _con_sala_maquina(c, [{"slug": "a", "parent_slug": ""}])
    _con_catalogo(c, 3)
    r = _cli(tmp_path, monkeypatch, c, ["--json"])
    d = _json.loads(r.output)
    assert len(d["resultados"]) == 9
    cob = next(x for x in d["resultados"] if x["id"] == "cobertura_vs_catalogo")
    assert cob["estado"] == "fallo"
    assert cob["evidencia"]["entradas_catalogo"] == 3


def test_cli_caso_inexistente_sale_con_2(tmp_path, monkeypatch):
    """Distinto de `1`: «no pude mirar» no es «hay un fallo»."""
    from typer.testing import CliRunner

    from core.casos import case_locator as cl
    from scripts import verificar_apertura as cli

    monkeypatch.setattr(cl, "buscar", lambda cid: None)
    r = CliRunner().invoke(cli.app, ["--case-id", "W-NADA0"])
    assert r.exit_code == 2


# --- Las ramas de fallo que la cobertura destapó sin control positivo -----------------
#
# La medición del diff las señaló como líneas nuevas sin cubrir. En un módulo cualquiera
# eso sería una nota; aquí son **ramas que devuelven `fallo`**, y una rama de fallo que
# nadie ha visto disparar es indistinguible de una que no puede disparar.


def test_c3_FALLA_con_un_catalogo_ilegible(tmp_path):
    """CONTROL POSITIVO de la otra mitad de C3: el YAML roto, no el JSON."""
    c = _caso(tmp_path)
    _con_sala_maquina(c, [{"slug": "a", "parent_slug": ""}])
    proc = c / "01_Procesado"
    proc.mkdir(parents=True, exist_ok=True)
    (proc / "indice_documental.yaml").write_text("[[[ no soy yaml", encoding="utf-8")
    r = _r(c, "cobertura_vs_catalogo")
    assert r.estado == va.FALLO and "ilegible" in r.detalle


def test_c3_pendiente_si_falta_el_catalogo_pero_hay_cobertura(tmp_path):
    """La sala de máquina corrió y la de lectura no: a medias, no roto."""
    c = _caso(tmp_path)
    _con_sala_maquina(c, [{"slug": "a", "parent_slug": ""}])
    r = _r(c, "cobertura_vs_catalogo")
    assert r.estado == va.PENDIENTE and "catálogo" in r.detalle


def test_c3_un_catalogo_VACIO_no_es_ilegible(tmp_path):
    """Un catálogo sin entradas es un dato, no un error de lectura — y con cobertura
    no vacía tiene que salir en FALLO, que es lo que de verdad pasó cuando `poblar`
    dejó la sala sin poblar."""
    c = _caso(tmp_path)
    _con_sala_maquina(c, [{"slug": "a", "parent_slug": ""}])
    proc = c / "01_Procesado"
    proc.mkdir(parents=True, exist_ok=True)
    (proc / "indice_documental.yaml").write_text("", encoding="utf-8")
    r = _r(c, "cobertura_vs_catalogo")
    assert r.estado == va.FALLO
    assert r.evidencia["entradas_catalogo"] == 0


def test_c5_FALLA_si_el_xlsx_esta_corrupto(tmp_path):
    """CONTROL POSITIVO: un `.xlsx` que openpyxl no puede abrir.

    Pasa de verdad — un informe copiado a medias por rclone —, y la diferencia entre
    `fallo` y una excepción sin capturar es que el operador ve las otras ocho.
    """
    c = _caso(tmp_path)
    an = c / "02_Analisis"
    an.mkdir(parents=True)
    (an / "Informe viabilidad - roto.xlsx").write_bytes(b"esto no es un zip")
    r = _r(c, "viabilidad_completa")
    assert r.estado == va.FALLO and "no se puede abrir" in r.detalle


# ===========================================================================
# Lo que la R1 de Codex rompió (2026-09-11) — 13 hallazgos, 13 confirmados
# ===========================================================================
#
# Siete ALTOS, y todos de la misma clase: **el verificador decía `ok` de un expediente
# roto**. Es el único defecto que invalida esta pieza entera, porque es el defecto que
# la pieza existe para cerrar.
#
# La regla que salió de ahí, y que ahora gobierna el módulo: **no poder mirar NO es «no
# hay nada que ver»**. Toda imposibilidad de leer, toda forma inválida y toda colisión
# de tipo son `fallo`. `pendiente` queda para la ausencia legítima.


# --- H-01: descartar basura en silencio hacía cuadrar los conteos --------------------


@pytest.mark.parametrize("cobertura, catalogo_yaml", [
    ([1, "broken", None], "[]"),                       # todas las filas, basura
    ([{"slug": "a"}, 42], "- slug: a"),                # una fila buena y una basura
])
def test_c3_FALLA_con_entradas_que_no_son_mapas(tmp_path, cobertura, catalogo_yaml):
    """CONTROL POSITIVO de H-01, el falso verde más caro de la ronda.

    `_leer_json_lista` filtraba con `isinstance(x, dict)`: una lista con basura se
    convertía en una lista **más corta**, y el conteo podía cuadrar con el otro lado. Un
    `_cobertura.json` corrupto salía en VERDE. Ahora una entrada que no es un mapa es
    forma inválida, y se dice cuántas y dónde.
    """
    c = _caso(tmp_path)
    _con_sala_maquina(c, cobertura)
    proc = c / "01_Procesado"
    proc.mkdir(parents=True, exist_ok=True)
    (proc / "indice_documental.yaml").write_text(catalogo_yaml, encoding="utf-8")
    r = _r(c, "cobertura_vs_catalogo")
    assert r.estado == va.FALLO
    assert "no son mapas" in r.detalle and "forma inválida" in r.detalle


def test_c3_FALLA_con_un_catalogo_de_cadenas(tmp_path):
    """La misma forma, del lado del YAML: `- bad\\n- rows` daba `ok` contra cobertura
    vacía."""
    c = _caso(tmp_path)
    _con_sala_maquina(c, [])
    proc = c / "01_Procesado"
    proc.mkdir(parents=True, exist_ok=True)
    (proc / "indice_documental.yaml").write_text("- bad\n- rows\n", encoding="utf-8")
    r = _r(c, "cobertura_vs_catalogo")
    assert r.estado == va.FALLO and "no son mapas" in r.detalle


# --- H-02: cualquier `parent_slug` verdadero descontaba un documento -----------------


@pytest.mark.parametrize("fila, senal", [
    ({"slug": "a", "parent_slug": "a"}, "hijo de sí mismo"),
    ({"slug": "a", "parent_slug": 17}, "no es texto"),
    ({"slug": "a", "parent_slug": "missing"}, "no está en la cobertura"),
])
def test_c3_FALLA_con_un_parent_slug_que_no_apunta_a_un_bundle(tmp_path, fila, senal):
    """CONTROL POSITIVO de H-02.

    Bastaba un valor verdadero para que la fila se contara como hijo de bundle y
    desapareciera del conteo: el documento podía faltar del catálogo y el verificador lo
    bendecía. Un hijo solo cuenta si su padre **existe** en la propia cobertura.
    """
    c = _caso(tmp_path)
    _con_sala_maquina(c, [fila])
    _con_catalogo(c, 0)
    r = _r(c, "cobertura_vs_catalogo")
    assert r.estado == va.FALLO
    assert senal in r.detalle, r.detalle


def test_c3_un_hijo_con_padre_REAL_sigue_sin_contar(tmp_path):
    """La otra mitad: el caso legítimo tiene que seguir en verde, o la verja grita
    sobre lo correcto y se acaba ignorando."""
    c = _caso(tmp_path)
    _con_sala_maquina(c, [{"slug": "bundle", "parent_slug": ""},
                          {"slug": "s1", "parent_slug": "bundle"}])
    _con_catalogo(c, 1)
    r = _r(c, "cobertura_vs_catalogo")
    assert r.estado == va.OK, r.detalle
    assert r.evidencia["hijos_de_bundle"] == 1


# --- H-04: contar no-vacíos no es contar preguntas -----------------------------------


def test_c5_FALLA_con_marcas_fuera_del_dominio(tmp_path):
    """CONTROL POSITIVO de H-04. 88 filas con la columna M a `basura` daban `ok`.

    El dominio es el que la plantilla declara y el generador escribe: `sí`/`si`/`no`.
    Contar «no está vacío» convierte cualquier cadena en una marca válida.
    """
    c = _caso(tmp_path)
    _informe_viabilidad(c, [(f"q{i}", None, "basura") for i in range(88)])
    r = _r(c, "viabilidad_completa")
    assert r.estado == va.FALLO and "fuera del dominio" in r.detalle


def test_c5_FALLA_con_la_misma_pregunta_repetida(tmp_path):
    """CONTROL POSITIVO de H-04, segunda mitad: 88 copias de `q0` daban `ok`.

    «Las 88 preguntas» es una afirmación sobre **identidades**, no sobre filas.
    """
    c = _caso(tmp_path)
    _informe_viabilidad(c, [("q0", None, "sí") for _ in range(88)])
    r = _r(c, "viabilidad_completa")
    assert r.estado == va.FALLO and "repetidos" in r.detalle
    assert r.evidencia["preguntas_distintas"] == 1


@pytest.mark.parametrize("marca", ["sí", "si", "no", "NO", " Sí "])
def test_c5_acepta_el_dominio_del_generador(tmp_path, marca):
    """Incluida la equivalencia de grafía `si` que `render_informe` normaliza."""
    c = _caso(tmp_path)
    _informe_viabilidad(c, [(f"q{i}", None, marca) for i in range(88)])
    assert _r(c, "viabilidad_completa").estado == va.OK


def test_c5_pendiente_con_dos_informes_de_la_misma_fecha(tmp_path):
    """H-11: el empate de mtime se resolvía por orden alfabético, y podía **ocultar el
    informe malo detrás del bueno**. Sin regla de vigencia, elegir es adivinar."""
    import os

    c = _caso(tmp_path)
    a = _informe_viabilidad(c, [(f"q{i}", None, "sí") for i in range(88)])
    an = c / "02_Analisis"
    malo = an / "Informe viabilidad Z malo.xlsx"
    malo.write_bytes(a.read_bytes())
    for p in (a, malo):
        os.utime(p, (2_000_000, 2_000_000))
    r = _r(c, "viabilidad_completa")
    assert r.estado == va.PENDIENTE and "misma fecha" in r.detalle
    assert len(r.evidencia["empatados"]) == 2


# --- H-05: no haber podido leer no es prueba de que no haya nada ---------------------


def test_c8_FALLA_si_un_espejo_no_se_puede_leer(tmp_path, monkeypatch):
    """CONTROL POSITIVO de H-05, el falso verde que vivía en la única línea que la
    cobertura del diff no cubría — y que yo había declarado «defensiva de E/S».

    El revisor lo midió en Windows con un handle exclusivo: mientras duraba el bloqueo,
    la comprobación devolvía `ok`, «ninguno en 0 espejos». Aquí se inyecta el mismo
    `PermissionError` que él observó.
    """
    c = _caso(tmp_path)
    _con_espejos(c, {"ajeno.md": "W-04AAAA\n"})
    real = type(tmp_path).read_text

    def bloqueado(self, *a, **kw):
        if self.name == "ajeno.md":
            raise PermissionError(13, "Permission denied")
        return real(self, *a, **kw)

    monkeypatch.setattr(type(tmp_path), "read_text", bloqueado)
    r = _r(c, "wcodes_ajenos")
    assert r.estado == va.FALLO
    assert "NO se pueden leer" in r.detalle
    assert "PermissionError" in r.evidencia["ilegibles"][0]


def test_c8_mira_tambien_los_subdirectorios(tmp_path):
    """H-05: solo recorría el primer nivel. Un espejo anidado quedaba fuera del barrido
    y su W-code ajeno era invisible."""
    c = _caso(tmp_path)
    md = _con_espejos(c, {"a.md": "W-TEST01\n"})
    (md / "nested").mkdir()
    (md / "nested" / "b.md").write_text("W-04AAAA\n", encoding="utf-8")
    r = _r(c, "wcodes_ajenos")
    assert r.estado == va.FALLO and "W-04AAAA" in r.detalle


# --- H-06: una ruta ocupada por un fichero no es «aún no ha corrido» -----------------


def test_una_ruta_estructural_OCUPADA_es_fallo_y_no_pendiente(tmp_path):
    """CONTROL POSITIVO de H-06.

    Con `01_Procesado` siendo un **fichero**, la primera versión informaba las cuatro
    locales en `pendiente`, cero fallos, y el CLI salía con 0. No es que falte una
    etapa: es que la etapa **no puede** correr.
    """
    c = _caso(tmp_path)
    (c / "01_Procesado").write_text("not a directory", encoding="utf-8")
    informe = va.verificar(c)
    fallos = {r.id for r in informe.fallos}
    assert fallos, "un expediente estructuralmente imposible salía en verde"
    assert "cobertura_vs_catalogo" in fallos or "artefactos_sala" in fallos
    for r in informe.fallos:
        assert "estructura inválida" in r.detalle or "no es un" in r.detalle


def test_la_identidad_sobrevive_a_una_comprobacion_que_revienta(tmp_path):
    """Al capturar la excepción se perdía el id (quedaba el nombre de la función).

    Un informe donde el fallo se llama `c3_cobertura_vs_catalogo` y el resto
    `cobertura_vs_catalogo` obliga a mirar el código para cruzarlos.
    """
    c = _caso(tmp_path)
    (c / "01_Procesado").write_text("x", encoding="utf-8")
    ids = {r.id for r in va.verificar(c).resultados}
    assert "cobertura_vs_catalogo" in ids
    assert not any(i.startswith("c3_") for i in ids)


# --- H-09 y H-10: la identidad del caso y la grafía del W-code ------------------------


def test_c8_el_wcode_propio_es_el_de_ENTRE_PARENTESIS(tmp_path):
    """CONTROL POSITIVO de H-09.

    En `Relacionado W-04AAAA - Caso (W-TEST01)` la primera versión tomaba como propio el
    **primero que aparecía**, así que el ajeno quedaba exento del barrido. El compositor
    del `case_id` pone el W-code entre paréntesis: ésa es la fuente.
    """
    c = _caso(tmp_path, nombre="Relacionado W-04AAAA - Caso (W-TEST01)")
    _con_espejos(c, {"a.md": "W-04AAAA\n"})
    r = _r(c, "wcodes_ajenos")
    assert r.estado == va.FALLO
    assert r.evidencia["propio"] == "W-TEST01"


def test_c8_dos_wcodes_entre_parentesis_son_identidad_AMBIGUA(tmp_path):
    """Elegir entre dos es adivinar: se declara."""
    c = _caso(tmp_path, nombre="Caso (W-TEST01) y (W-04AAAA)")
    _con_espejos(c, {"a.md": "texto\n"})
    r = _r(c, "wcodes_ajenos")
    assert r.estado == va.FALLO and "ambigua" in r.detalle


@pytest.mark.parametrize("texto", [
    "Documento W-\n04AAAA de otro caso",     # partido por maquetación
    "Documento W‐04AAAA de otro caso",  # guion U+2010
    "Documento w-04aaaa de otro caso",       # minúsculas (ya cubierto, se conserva)
])
def test_c8_detecta_las_variantes_de_grafia(tmp_path, texto):
    """CONTROL POSITIVO de H-10. La extracción de texto de un PDF parte identificadores
    por maquetación y mete guiones tipográficos; los tres son el mismo W-code."""
    c = _caso(tmp_path)
    _con_espejos(c, {"propio.md": "W-TEST01\n", "colado.md": texto})
    r = _r(c, "wcodes_ajenos")
    assert r.estado == va.FALLO and "W-04AAAA" in r.detalle


# --- H-08: la guarda del control positivo, que ahora EJECUTA --------------------------
#
# La anterior buscaba una **cadena literal** en este mismo fichero. El revisor la
# sobrevivió de tres formas legítimas —`@pytest.mark.skip`, `xfail(strict=True)`, y el
# ejemplo dentro de un docstring— y la rompió cambiando unas comillas dobles por simples
# en un test que seguía funcionando. Leer texto no demuestra ejecución, ni resultado, ni
# siquiera que exista una función de test.
#
# Ahora el registro vive **en código** y la guarda lo **corre**.


def _roto_cobertura(tmp_path):
    c = _caso(tmp_path)
    _con_sala_maquina(c, [{"slug": f"d{i}", "parent_slug": ""} for i in range(21)])
    _con_catalogo(c, 17)
    return c


def _roto_artefactos(tmp_path):
    c = _caso(tmp_path)
    _con_sala_lectura(c, artefactos=("INDICE.md", "CRONOLOGIA.md"))
    return c


def _roto_viabilidad(tmp_path):
    c = _caso(tmp_path)
    _informe_viabilidad(c, [(f"q{i}", None, "sí") for i in range(51)]
                        + [(f"q{i}", None, None) for i in range(51, 88)])
    return c


def _roto_wcodes(tmp_path):
    c = _caso(tmp_path)
    _con_espejos(c, {"propio.md": "W-TEST01\n", "colado.md": "W-04AAAA\n"})
    return c


#: Un expediente roto por comprobación, que la guarda EJECUTA. No es documentación: es
#: el instrumento. Añadir una comprobación implementada sin su entrada aquí pone la
#: guarda en rojo, y una entrada que no produzca `fallo` de verdad también.
CASOS_DE_FALLO = {
    "cobertura_vs_catalogo": _roto_cobertura,
    "artefactos_sala": _roto_artefactos,
    "viabilidad_completa": _roto_viabilidad,
    "wcodes_ajenos": _roto_wcodes,
}


def test_toda_comprobacion_implementada_se_declara_en_IMPLEMENTADAS(tmp_path):
    """El registro del módulo y lo que el informe hace tienen que coincidir.

    Si divergieran, la guarda de abajo miraría una lista y el informe otra — y una
    comprobación podría quedar sin control positivo sin que nadie lo viera.
    """
    reales = {r.id for r in va.verificar(_caso(tmp_path)).resultados
              if r.estado != va.SIN_IMPLEMENTAR}
    assert reales == set(va.IMPLEMENTADAS)


@pytest.mark.parametrize("ident", sorted(CASOS_DE_FALLO))
def test_cada_comprobacion_implementada_PUEDE_decir_fallo(tmp_path, ident):
    """La guarda contra la guarda inerte, **ejecutada**.

    Construye el expediente roto de esa comprobación y exige que devuelva `fallo`. No
    hay texto que inspeccionar ni cadena que se pueda romper con unas comillas: o el
    caso produce el rojo, o este test cae.
    """
    r = _r(CASOS_DE_FALLO[ident](tmp_path), ident)
    assert r.estado == va.FALLO, (
        f"«{ident}» no se pone en fallo ni con su caso roto: "
        f"estado={r.estado}, detalle={r.detalle!r}")


def test_ninguna_implementada_se_queda_sin_su_caso_roto(tmp_path):
    """Y el cierre: que el registro cubra **todas** las implementadas.

    Sin esto, añadir una décima comprobación y olvidar su entrada dejaría la
    parametrización de arriba sin ese id — verde por omisión, que es la forma más
    silenciosa de que una verja deje de verificar.
    """
    assert set(CASOS_DE_FALLO) == set(va.IMPLEMENTADAS), (
        "hay comprobaciones implementadas sin un caso que las ponga en FALLO, o al "
        "revés. Una verja que solo puede decir `ok` no verifica nada.")


def test_cli_resuelve_el_W_code_corto_que_su_ayuda_anuncia(tmp_path, monkeypatch):
    """CONTROL POSITIVO de H-07, y el test que faltaba por mockear de más.

    La ayuda dice `--case-id W-XXXXXX`, y `buscar` casa el **nombre literal** de la
    carpeta: sobre un expediente que existía, esa forma devolvía salida 2, «caso no
    encontrado». No lo veía ningún test porque todos sustituían `buscar` — probaban el
    doble, no la integración.

    Aquí se sustituye únicamente la **raíz** de casos, así que `resolve_ref` y `buscar`
    corren de verdad.
    """
    from typer.testing import CliRunner

    from core.casos import case_locator as cl
    from scripts import verificar_apertura as cli

    root = tmp_path / "CASOS"
    caso = root / "BaRS3 - Calle (W-TEST01) - Vuelta" / "00_Input"
    caso.mkdir(parents=True)
    (caso / "_caso.md").write_text(
        "---\ncase_id: x\nmeta:\n  id_go: W-TEST01\n---\n\n# Caso\n", encoding="utf-8")
    monkeypatch.setattr(cl, "_root", lambda: root)

    r = CliRunner().invoke(cli.app, ["--case-id", "W-TEST01"])
    assert r.exit_code == 0, r.output
    assert "W-TEST01" in r.output
