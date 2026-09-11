"""`verificar_apertura` — el «OK» del expediente (pieza P2 de la fila #28 de `PLAN.md`).

**El control positivo no es un extra aquí: es la razón de ser del fichero.** Esta pieza
existe porque ocho herramientas dijeron «OK» de su paso el 2026-09-10 mientras el
expediente estaba a medias. Una verja que solo puede decir `ok` repite ese defecto una
capa más arriba, con el agravante de que ahora el «OK» dice ser del expediente.

Así que **cada comprobación implementada tiene aquí su caso en rojo**, construido a mano
sobre un árbol sintético, y ese caso reproduce el defecto real que la motivó. Si alguna
comprobación dejara de poder ponerse roja, su test lo diría.

Todo se monta en `tmp_path`: ningún test escribe en el árbol de producción.
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
    assert r.evidencia["preguntas"] == 88


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


# --- La propiedad transversal -------------------------------------------------------


def test_cada_comprobacion_implementada_PUEDE_decir_fallo(tmp_path):
    """La guarda contra la guarda inerte, y el único test que de verdad protege la pieza.

    Recorre las comprobaciones que dicen estar implementadas y exige que **exista en
    este fichero** un caso que las pone en `fallo`. Si mañana alguien añade una décima
    comprobación implementada y no le escribe su rojo, esto se pone rojo.

    No comprueba la calidad del caso —eso lo hace la revisión—, sino que el instrumento
    puede dar el otro valor. Es la lección de la guarda inerte, aplicada al instrumento
    que existe para que un «OK» signifique algo.
    """
    implementadas = {r.id for r in va.verificar(_caso(tmp_path)).resultados
                     if r.estado != va.SIN_IMPLEMENTAR}
    fuente = __import__("pathlib").Path(__file__).read_text(encoding="utf-8")
    sin_rojo = sorted(i for i in implementadas
                      if f'"{i}")\n    assert r.estado == va.FALLO' not in fuente
                      and f'_r(c, "{i}")\n    assert r.estado == va.FALLO' not in fuente)
    assert not sin_rojo, (
        f"comprobaciones implementadas sin un caso que las ponga en FALLO: {sin_rojo}. "
        "Una verja que solo puede decir `ok` no verifica nada.")


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
