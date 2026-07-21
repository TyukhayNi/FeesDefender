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


def test_agrupar_por_hilo_junta_variantes_del_mismo_dia_y_asunto():
    nombres = [
        "2025-03-20_consulta_de_procedimiento_en_el_caso_salto_de_clientes.eml",
        "2025-03-20_consulta_de_procedimiento_en_el_caso_salto_de_clientes_2.eml",
        "2025-03-20_consulta_de_procedimiento_en_el_caso_salto_de_clientes_3.eml",
        "2025-04-22_ubicacion_propietario_tonet.eml",
    ]
    grupos = preclasificar.agrupar_por_hilo(nombres)
    assert len(grupos) == 2
    clave_consulta = "2025-03-20_consulta_de_procedimiento_en_el_caso_salto_de_clientes"
    assert len(grupos[clave_consulta]) == 3


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
