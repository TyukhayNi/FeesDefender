from importlib import import_module
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / ".claude/skills/organizar-sala-lectura/scripts"))
preclasificar = import_module("preclasificar")


def test_clasifica_encargo_por_patron():
    cat, motivo = preclasificar.clasificar_por_patron("doc_02_encargo_y_poderes.pdf")
    assert cat == "01. ACTIVACIÓN"
    assert motivo == "doc_NN_encargo"


def test_clasifica_factura_por_patron():
    cat, _ = preclasificar.clasificar_por_patron("FACTURA 158 - 25-11-2025 - EV MMC SPAIN.pdf")
    assert cat == "05. FACTURACIÓN - FINANZAS"


def test_prefijo_de_fecha_no_rompe_el_patron():
    # bug de la v1: el ^ no casaba con nombres con fecha delante
    cat, _ = preclasificar.clasificar_por_patron("2025-04-08_requerimiento_pago_honorarios_s_r_vars5.eml")
    assert cat == "07. RECLAMACIONES"  # cae al default, correcto — "requerimiento_pago" no es de los 6 patrones estrechos


def test_nombre_generico_cae_al_default_reclamaciones():
    cat, motivo = preclasificar.clasificar_por_patron("2025-03-20_consulta_de_procedimiento_en_el_caso_salto_de_clientes.eml")
    assert cat == "07. RECLAMACIONES"
    assert motivo == "default_reclamaciones"


def test_bundle_conversacional_sin_patron_va_a_pendiente():
    cat, motivo = preclasificar.clasificar_por_patron(
        "Chat de WhatsApp con Projecto Denia Aldebaran", es_bundle_conversacional=True)
    assert cat == "08. PENDIENTE DE CLASIFICAR"
    assert motivo == "requiere_identificar_parte"


def test_captura_screenshot_va_a_fotos():
    cat, _ = preclasificar.clasificar_por_patron("Screenshot_20250331_124123_WhatsAppBusiness.jpg")
    assert cat == "00. FOTOS"


def test_dedup_por_sha_agrupa_y_reporta_duplicados():
    ficheros = [
        {"ruta": "sudespacho_499/demanda/doc_02_encargo_y_poderes.pdf", "sha256": "aaa"},
        {"ruta": "sudespacho_602/demanda/doc_02_encargo_y_poderes.pdf", "sha256": "aaa"},
        {"ruta": "sudespacho_603/demanda/doc_02_encargo_y_poderes.pdf", "sha256": "aaa"},
        {"ruta": "01_Drive EV/OFERTA.PDF", "sha256": "bbb"},
    ]
    unicos, duplicados = preclasificar.dedup_por_sha(ficheros)
    assert len(unicos) == 2
    assert len(duplicados) == 2
    assert duplicados[0]["duplicado_de"] == "sudespacho_499/demanda/doc_02_encargo_y_poderes.pdf"


def test_agrupar_por_hilo_junta_el_mismo_asunto_en_fechas_distintas():
    # Comportamiento NUEVO (v1.13): la clave es la descripción, no el stem con fecha.
    nombres = [
        "2025-03-20_oferta_calle_x.eml",
        "2025-03-21_oferta_calle_x.eml",
        "2025-04-02_oferta_calle_x.eml",
        "2025-04-22_ubicacion_propietario.eml",
    ]
    grupos = preclasificar.agrupar_por_hilo(nombres)
    assert set(grupos) == {"oferta_calle_x", "ubicacion_propietario"}
    assert len(grupos["oferta_calle_x"]) == 3


def test_agrupar_por_hilo_junta_variantes_del_mismo_dia_y_asunto():
    nombres = [
        "2025-03-20_consulta_procedimiento.eml",
        "2025-03-20_consulta_procedimiento_2.eml",
        "2025-03-20_consulta_procedimiento_3.eml",
        "2025-04-22_ubicacion_propietario.eml",
    ]
    grupos = preclasificar.agrupar_por_hilo(nombres)
    assert len(grupos) == 2
    assert len(grupos["consulta_procedimiento"]) == 3


def test_agrupar_por_hilo_no_fusiona_por_cifra_en_el_asunto():
    # Regresión del ítem 11: "_000" NO es sufijo de hilo (no existe "oferta_vivienda_1_990").
    nombres = [
        "2025-05-10_oferta_vivienda_1_990_000.eml",
        "2025-06-01_otra_cosa.eml",
    ]
    grupos = preclasificar.agrupar_por_hilo(nombres)
    assert set(grupos) == {"oferta_vivienda_1_990_000", "otra_cosa"}


def test_agrupar_por_hilo_sin_base_no_fusiona():
    # _2 y _3 SIN la base -> no se puede afirmar que sean el mismo hilo.
    nombres = ["2025-03-20_consulta_2.eml", "2025-03-20_consulta_3.eml"]
    grupos = preclasificar.agrupar_por_hilo(nombres)
    assert set(grupos) == {"consulta_2", "consulta_3"}


def test_agrupar_por_hilo_nombre_sin_prefijo_de_fecha():
    # Fichero legacy/manual sin fecha delante: la descripción es el nombre pelado.
    grupos = preclasificar.agrupar_por_hilo(["oferta_suelta.eml"])
    assert set(grupos) == {"oferta_suelta"}


def test_fecha_de_nombre():
    assert preclasificar.fecha_de_nombre("2025-03-20_consulta.eml") == "2025-03-20"
    assert preclasificar.fecha_de_nombre("0000-00-00_sin_fecha.eml") == "0000-00-00"
    assert preclasificar.fecha_de_nombre("oferta_suelta.eml") == "0000-00-00"


# ── MEJORAS #131 (PLAN fila #18): el centinela «sin fecha» es truthy y hay que preguntar bien ──

def test_131_el_centinela_es_publico_truthy_y_tiene_fecha_lo_reconoce():
    """El valor «sin fecha» va en nombres canónicos y en el manifiesto, así que es una
    cadena no vacía: `not` NO lo detecta. La pregunta correcta es `tiene_fecha`."""
    assert preclasificar.SIN_FECHA == "0000-00-00"
    assert preclasificar.fecha_de_nombre("oferta_suelta.eml") == preclasificar.SIN_FECHA
    assert bool(preclasificar.SIN_FECHA) is True            # la trampa, documentada
    assert preclasificar.tiene_fecha(preclasificar.SIN_FECHA) is False
    assert preclasificar.tiene_fecha(preclasificar.fecha_de_nombre("oferta_suelta.eml")) is False
    assert preclasificar.tiene_fecha("2025-03-20") is True
    assert preclasificar.tiene_fecha(None) is False
    assert preclasificar.tiene_fecha("") is False
    assert preclasificar.tiene_fecha("0000-00-00 (*)") is False
    assert preclasificar.tiene_fecha("2025-03 (*)") is False   # aproximada: sigue sin fecha cierta


def test_131_candidatos_sin_fecha_es_el_filtro_del_paso_1bis_d():
    """Reproduce el defecto de W-02X1WJ: con el filtro a mano `not f["fecha"]` salían 0;
    el helper devuelve exactamente los binarios opacos sin fecha real."""
    filas = [
        {"nombre_canonico": "0000-00-00_burofax.pdf", "fecha": "0000-00-00", "sha256": "a"},
        {"nombre_canonico": "0000-00-00_foto.jpg", "fecha": preclasificar.SIN_FECHA, "sha256": "b"},
        {"nombre_canonico": "2025-04-08_burofax.pdf", "fecha": "2025-04-08", "sha256": "c"},
        {"nombre_canonico": "0000-00-00_hilo.eml", "fecha": "0000-00-00", "sha256": "d"},  # no opaco
        {"nombre_canonico": "sin_fecha_clave.pdf", "fecha": None, "sha256": "e"},
        {"nombre_canonico": "2025-03 (*)_escritura.pdf", "fecha": "2025-03 (*)", "sha256": "f"},
    ]
    a_mano = [f for f in filas if not f["fecha"]]
    assert [f["sha256"] for f in a_mano] == ["e"]              # el filtro que falló: 1 de 4
    candidatos = preclasificar.candidatos_sin_fecha(filas)
    assert [f["sha256"] for f in candidatos] == ["a", "b", "e", "f"]
    assert candidatos[0] is filas[0]                           # las filas mismas, para rellenar en sitio


def test_131_la_skill_cita_el_helper_y_no_el_filtro_a_mano():
    """Condición de cierre de MEJORAS #131: existe el helper Y la skill lo cita en el paso que
    lo necesita. Y el paso no vuelve a decir `not f["fecha"]`."""
    skill = (Path(__file__).parent.parent / ".claude/skills/organizar-sala-lectura/SKILL.md"
             ).read_text(encoding="utf-8")
    ini = skill.index("d. **Para TODO binario opaco")
    paso = skill[ini: skill.index("   e. `subcategoria_crm(ruta)`", ini)]
    assert "candidatos_sin_fecha(filas)" in paso
    assert "SIN_FECHA" in paso and "truthy" in paso
    assert 'not f["fecha"]' in paso            # citado como lo que NO se hace…
    assert "NO\n      escribas el filtro a mano" in paso or "NO escribas el filtro a mano" in paso.replace("\n      ", " ")


def test_subcategoria_crm_extrae_la_subcarpeta():
    assert preclasificar.subcategoria_crm("sudespacho_602/civil/auto_inadmite_diligencias_preliminares.pdf") == "civil"
    assert preclasificar.subcategoria_crm("01_Drive EV/OFERTA.PDF") is None


def test_categorias_sin_drift():
    from core.config import TAXONOMIA_EV
    assert set(preclasificar._CATEGORIAS) == set(TAXONOMIA_EV)


def test_texto_espejo_md_encuentra_por_parent_sha256(tmp_path):
    sm_dir = tmp_path / "02_Sala de máquina"
    (sm_dir / "03_MD").mkdir(parents=True)
    (sm_dir / "03_MD" / "hoja_visita__a1b2c3d4.md").write_text(
        "---\nchars: 120\n---\nHoja de visita firmada el 31 de marzo de 2025.", encoding="utf-8")
    import json
    (sm_dir / "_cobertura.json").write_text(json.dumps([
        {"slug": "hoja_visita__a1b2c3d4", "sha256": "a1b2c3d4", "parent_sha256": "origen_sha_xyz", "estado": "ok"},
    ]), encoding="utf-8")
    texto = preclasificar.texto_espejo_md(sm_dir, "origen_sha_xyz")
    assert "31 de marzo de 2025" in texto


def test_texto_espejo_md_none_si_no_hay_cobertura(tmp_path):
    assert preclasificar.texto_espejo_md(tmp_path / "no_existe", "cualquier_sha") is None


def test_texto_espejo_md_none_si_estado_vacio(tmp_path):
    sm_dir = tmp_path / "02_Sala de máquina"
    sm_dir.mkdir()
    import json
    (sm_dir / "_cobertura.json").write_text(json.dumps([
        {"slug": "x__y", "sha256": "s1", "parent_sha256": "origen", "estado": "empty"},
    ]), encoding="utf-8")
    assert preclasificar.texto_espejo_md(sm_dir, "origen") is None


def test_senales_gate_detecta_wcode_ajeno():
    filas = [{"ruta_original": "05_CRM/sudespacho_9/W-02X270_doc.pdf",
              "nombre_canonico": "2025-01-01_doc.pdf", "sha256": "a", "motivo": "default_reclamaciones"}]
    señales = preclasificar.senales_gate(filas, wcode_caso="W-02VUDR")
    assert any("W-02X270" in s for s in señales)


def test_senales_gate_ignora_wcode_propio():
    filas = [{"ruta_original": "05_CRM/sudespacho_9/W-02VUDR_doc.pdf",
              "nombre_canonico": "2025-01-01_doc.txt", "sha256": "a", "motivo": "default_reclamaciones"}]
    assert preclasificar.senales_gate(filas, wcode_caso="W-02VUDR") == []


def test_senales_gate_detecta_casi_duplicado_mismo_nombre_distinto_sha():
    filas = [
        {"ruta_original": "a/OFERTA.pdf", "nombre_canonico": "2025-01-01_oferta.pdf", "sha256": "aaa", "motivo": "x"},
        {"ruta_original": "b/OFERTA.pdf", "nombre_canonico": "2025-02-01_oferta.pdf", "sha256": "bbb", "motivo": "x"},
    ]
    señales = preclasificar.senales_gate(filas, wcode_caso="W-02VUDR")
    assert any("casi-duplicado" in s and "oferta.pdf".lower() in s.lower() for s in señales)


def test_senales_gate_detecta_binario_opaco_sin_espejo_md():
    filas = [{"ruta_original": "a/escaneo.pdf", "nombre_canonico": "2025-01-01_escaneo.pdf", "sha256": "a", "motivo": "default_reclamaciones"}]
    señales = preclasificar.senales_gate(filas, wcode_caso="W-02VUDR", cobertura_filas=[])
    assert any("sin espejo MD" in s for s in señales)


def test_senales_gate_binario_opaco_con_espejo_no_es_senal():
    filas = [{"ruta_original": "a/escaneo.pdf", "nombre_canonico": "2025-01-01_escaneo.pdf", "sha256": "a", "motivo": "x"}]
    cobertura = [{"sha256": "seg", "parent_sha256": "a", "estado": "ok", "chars": 300}]
    assert preclasificar.senales_gate(filas, wcode_caso="W-02VUDR", cobertura_filas=cobertura) == []


def test_senales_gate_pasa_requiere_identificar_parte():
    filas = [{"ruta_original": "a/chat.txt", "nombre_canonico": "2024-01-01_chat.txt", "sha256": "a", "motivo": "requiere_identificar_parte"}]
    señales = preclasificar.senales_gate(filas, wcode_caso="W-02VUDR", cobertura_filas=None)
    assert any("requiere_identificar_parte" in s for s in señales)


def test_senales_gate_limpio_da_lista_vacia():
    # .eml (texto, no binario opaco), nombre único, wcode propio -> auto-aprueba.
    filas = [{"ruta_original": "03_Email/corr.eml", "nombre_canonico": "2025-01-01_correo.eml", "sha256": "a", "motivo": "default_reclamaciones"}]
    assert preclasificar.senales_gate(filas, wcode_caso="W-02VUDR", cobertura_filas=None) == []


def test_emparejar_exports_whatsapp_marca_el_zip_crudo_como_duplicado():
    rutas = [
        "2026-07-21_whatsapp_01/propietario/Chat con Tonet/_chat.txt",
        "2026-07-21_whatsapp_01/propietario/Chat con Tonet/media/IMG-0001.jpg",
        "2026-07-21_whatsapp_01/propietario/Chat con Tonet/_export_original.zip",
    ]
    limpias, crudos = preclasificar.emparejar_exports_whatsapp(rutas)
    assert "2026-07-21_whatsapp_01/propietario/Chat con Tonet/_export_original.zip" not in limpias
    assert len(crudos) == 1
    assert crudos[0]["motivo"] == "export_crudo_whatsapp"
    assert crudos[0]["duplicado_de"].endswith("Chat con Tonet/_chat.txt")


def test_emparejar_exports_whatsapp_conserva_zip_sin_chat_hermano():
    # Un .zip suelto (Manual) SIN _chat.txt hermano NO es un export crudo -> se conserva.
    rutas = ["04_Manual/documentacion_aportada.zip", "04_Manual/otro.pdf"]
    limpias, crudos = preclasificar.emparejar_exports_whatsapp(rutas)
    assert "04_Manual/documentacion_aportada.zip" in limpias
    assert crudos == []


def test_emparejar_exports_whatsapp_sin_zip_no_toca_nada():
    rutas = ["01_Drive EV/a.pdf", "03_Email/corr.eml"]
    limpias, crudos = preclasificar.emparejar_exports_whatsapp(rutas)
    assert limpias == rutas
    assert crudos == []


def test_emparejar_exports_whatsapp_conserva_zip_no_original_junto_a_chat():
    # Un .zip que NO es _export_original.zip, aunque comparta carpeta con un
    # _chat.txt, es documentación legítima aportada: se conserva (hallazgo de la
    # revisión adversarial — el matcher no debe ser un `.endswith('.zip')` genérico).
    rutas = [
        "2026-07-21_whatsapp_01/propietario/Chat con Tonet/_chat.txt",
        "2026-07-21_whatsapp_01/propietario/Chat con Tonet/adjuntos_aportados.zip",
    ]
    limpias, crudos = preclasificar.emparejar_exports_whatsapp(rutas)
    assert "2026-07-21_whatsapp_01/propietario/Chat con Tonet/adjuntos_aportados.zip" in limpias
    assert crudos == []


def test_nombre_export_crudo_sin_drift_con_core():
    from core.whatsapp_intake import _ORIGINAL_ZIP_NAME
    assert preclasificar._NOMBRE_EXPORT_CRUDO_WHATSAPP == _ORIGINAL_ZIP_NAME



def test_layout_bundle_de_tres_mensajes():
    grupo = [
        "2025-04-02_oferta_calle_x.eml",
        "2025-03-20_oferta_calle_x.eml",
        "2025-03-21_oferta_calle_x.eml",
    ]
    filas = preclasificar.layout_bundle_hilo(grupo, "oferta_calle_x")
    assert [f["rol"] for f in filas] == ["principal", "anexo", "anexo"]
    principal = filas[0]
    assert principal["nombre_origen"] == "2025-03-20_oferta_calle_x.eml"
    assert principal["nombre_canonico"] == "2025-03-20_oferta_calle_x/2025-03-20_oferta_calle_x.eml"
    assert principal["parent_id"] == ""
    # Cada anexo lleva SU PROPIA fecha, el parent_id pelado de la carpeta y un
    # discriminante derivado de su propio origen (no de su posicion en el grupo).
    assert filas[1]["fecha"] == "2025-03-21"
    assert filas[1]["parent_id"] == "2025-03-20_oferta_calle_x"
    assert filas[1]["nombre_canonico"].startswith(
        "2025-03-20_oferta_calle_x/2025-03-21_oferta_calle_x_")
    assert filas[2]["fecha"] == "2025-04-02"


def test_layout_nombre_de_anexo_es_estable_al_llegar_uno_anterior():
    # REGRESION: con indice posicional, un mensaje nuevo que ordenase antes se
    # llevaba el `_anexo_1` de otro YA COPIADO y lo sobrescribia.
    corrida1 = ["2025-03-20_x.eml", "2025-04-02_x.eml"]
    nombre_c = [f for f in preclasificar.layout_bundle_hilo(corrida1, "x")
                if f["nombre_origen"] == "2025-04-02_x.eml"][0]["nombre_canonico"]
    corrida2 = corrida1 + ["2025-03-25_x.eml"]
    filas2 = preclasificar.layout_bundle_hilo(
        corrida2, "x", carpeta_existente="2025-03-20_x")
    nombre_c2 = [f for f in filas2 if f["nombre_origen"] == "2025-04-02_x.eml"][0]["nombre_canonico"]
    assert nombre_c2 == nombre_c  # el ya copiado conserva su nombre exacto
    nombres = [f["nombre_canonico"] for f in filas2]
    assert len(set(nombres)) == len(nombres)  # y nadie pisa a nadie


def test_layout_nombres_repetidos_abortan_ruidosamente():
    # Dos lotes distintos pueden traer el MISMO basename con sha distinto
    # (`_ruta_unica` solo desambigua dentro de su lote). Silenciarlo perderia un
    # mensaje; y con nombres repetidos el llamante tampoco puede resolver el origen.
    import pytest
    with pytest.raises(ValueError, match="repetid"):
        preclasificar.layout_bundle_hilo(
            ["2025-03-20_x.eml", "2025-03-20_x.eml"], "x")


def test_layout_mensaje_unico_sin_adjuntos_queda_plano():
    filas = preclasificar.layout_bundle_hilo(["2025-03-20_consulta.eml"], "consulta")
    assert len(filas) == 1
    assert filas[0]["rol"] == "principal"
    assert filas[0]["nombre_canonico"] == "2025-03-20_consulta.eml"
    assert filas[0]["parent_id"] == ""


def test_layout_mensaje_unico_con_adjuntos_abre_bundle():
    filas = preclasificar.layout_bundle_hilo(
        ["2025-03-20_consulta.eml"], "consulta",
        con_adjuntos=frozenset({"2025-03-20_consulta.eml"}))
    assert filas[0]["nombre_canonico"] == "2025-03-20_consulta/2025-03-20_consulta.eml"


def test_layout_fecha_incierta_no_es_principal():
    grupo = ["0000-00-00_oferta_calle_x.eml", "2025-03-20_oferta_calle_x.eml"]
    filas = preclasificar.layout_bundle_hilo(grupo, "oferta_calle_x")
    assert filas[0]["nombre_origen"] == "2025-03-20_oferta_calle_x.eml"
    assert filas[1]["fecha"] == "0000-00-00"


def test_layout_carpeta_existente_no_se_renombra_con_mensaje_anterior():
    grupo = [
        "2025-03-20_oferta_calle_x.eml",
        "2025-03-21_oferta_calle_x.eml",
        "2025-01-05_oferta_calle_x.eml",
    ]
    filas = preclasificar.layout_bundle_hilo(
        grupo, "oferta_calle_x", carpeta_existente="2025-03-20_oferta_calle_x")
    assert all(f["nombre_canonico"].startswith("2025-03-20_oferta_calle_x/") for f in filas)
    nuevo = [f for f in filas if f["nombre_origen"] == "2025-01-05_oferta_calle_x.eml"][0]
    assert nuevo["rol"] == "anexo"
    assert nuevo["fecha"] == "2025-01-05"
    assert nuevo["parent_id"] == "2025-03-20_oferta_calle_x"


def test_layout_carpeta_existente_sin_candidato_no_adjudica_principal():
    # El principal original ya no esta en el grupo (borrado de 00_Input, o el
    # llamante pasa solo lo nuevo): NADIE debe recibir `{carpeta}/{carpeta}.eml`,
    # que es la ruta del principal YA COPIADO.
    filas = preclasificar.layout_bundle_hilo(
        ["2025-05-01_x.eml", "2025-06-01_x.eml"], "x", carpeta_existente="2025-03-20_x")
    assert all(f["rol"] == "anexo" for f in filas)
    assert all(f["parent_id"] == "2025-03-20_x" for f in filas)
    assert "2025-03-20_x/2025-03-20_x.eml" not in [f["nombre_canonico"] for f in filas]


def test_layout_plano_existente_no_crea_carpeta():
    # El hilo ya se materializo PLANO (1 mensaje sin adjuntos). Al llegar un
    # segundo, NO se abre carpeta: se anadiria un bundle sin principal dentro y el
    # hilo quedaria partido en dos sitios.
    filas = preclasificar.layout_bundle_hilo(
        ["2025-04-01_x.eml"], "x", plano_existente=True)
    assert all("/" not in f["nombre_canonico"] for f in filas)
    assert all(f["parent_id"] == "" for f in filas)


def test_layout_es_determinista():
    grupo = ["2025-03-21_x.eml", "2025-03-20_x.eml"]
    assert preclasificar.layout_bundle_hilo(grupo, "x") == preclasificar.layout_bundle_hilo(
        list(reversed(grupo)), "x")
