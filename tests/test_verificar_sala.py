from importlib import import_module
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / ".claude/skills/organizar-sala-lectura/scripts"))
verificar_sala = import_module("verificar_sala")


def test_detecta_fila_sin_fichero_en_disco():
    filas = [{"nombre_canonico": "2025-01-01_doc.pdf", "sha256": "a", "parent_id": ""}]
    problemas = verificar_sala.verificar(filas, ficheros_en_disco=set())
    assert any("2025-01-01_doc.pdf" in p and "no existe en disco" in p for p in problemas)


def test_detecta_fichero_en_disco_sin_fila_en_manifiesto():
    filas = []
    problemas = verificar_sala.verificar(filas, ficheros_en_disco={"2025-01-01_huerfano.pdf"})
    assert any("2025-01-01_huerfano.pdf" in p and "sin fila" in p for p in problemas)


def test_detecta_anexo_sin_parent_id_resoluble():
    filas = [
        {"nombre_canonico": "2025-01-01_doc.pdf", "sha256": "a", "parent_id": ""},
        {"nombre_canonico": "2025-01-01_doc_anexo_1.pdf", "sha256": "b", "parent_id": "id-que-no-existe"},
    ]
    problemas = verificar_sala.verificar(filas, ficheros_en_disco={
        "2025-01-01_doc.pdf", "2025-01-01_doc_anexo_1.pdf"})
    assert any("parent_id" in p and "id-que-no-existe" in p for p in problemas)


def test_todo_correcto_no_da_problemas():
    filas = [{"nombre_canonico": "2025-01-01_doc.pdf", "sha256": "a", "parent_id": ""}]
    problemas = verificar_sala.verificar(filas, ficheros_en_disco={"2025-01-01_doc.pdf"})
    assert problemas == []


def test_parent_id_como_nombre_de_carpeta_de_bundle_no_es_huerfano():
    # Convención real de la skill desde v1.1 (ver "Documentos compuestos"): el
    # parent_id de un anexo es el nombre PELADO de la carpeta del bundle, no el
    # nombre_canonico completo del principal (que incluye la subcarpeta +
    # extensión). Bug real detectado en W-02VUDR 2026-07-21: la v1 de esta
    # función solo aceptaba match exacto contra nombre_canonico o sha256, así
    # que TODO anexo de TODO bundle salía como "huérfano" (falso positivo).
    filas = [
        {
            "nombre_canonico": "2024-06-18_chat_whatsapp_propietario_tonet/2024-06-18_chat_whatsapp_propietario_tonet.txt",
            "sha256": "a", "parent_id": "",
        },
        {
            "nombre_canonico": "2024-06-18_chat_whatsapp_propietario_tonet/2024-06-18_chat_whatsapp_propietario_tonet_anexo_1_foto.jpg",
            "sha256": "b", "parent_id": "2024-06-18_chat_whatsapp_propietario_tonet",
        },
    ]
    problemas = verificar_sala.verificar(filas, ficheros_en_disco={f["nombre_canonico"] for f in filas})
    assert problemas == []


def test_detecta_fecha_0000_con_texto_ya_extraido_sin_usar():
    # Bug real (W-02VUDR, 2026-07-21): 7 binarios opacos quedaron en 0000-00-00
    # pese a que su espejo MD en sala de maquina ya tenia texto extraido con una
    # fecha inequivoca (p.ej. un burofax certificado con "Fecha y hora del
    # envio: 08/04/2025"). texto_espejo_md() existe desde la v1.9 pero es
    # invocacion opcional en el procedimiento -- nada lo hacia obligatorio ni
    # lo verificaba despues. cobertura_filas (de _cobertura.json) permite
    # cruzar: si hay texto util (estado ok/low, chars por encima de un umbral)
    # para un sha256 que quedo en 0000-00-00, es sospechoso y hay que avisar.
    filas = [{"nombre_canonico": "0000-00-00_burofax.pdf", "sha256": "a", "parent_id": "", "fecha": "0000-00-00"}]
    cobertura = [{"sha256": "a", "estado": "ok", "chars": 500}]
    problemas = verificar_sala.verificar(
        filas, ficheros_en_disco={"0000-00-00_burofax.pdf"}, cobertura_filas=cobertura)
    assert any("0000-00-00" in p and "texto extraído" in p for p in problemas)


def test_no_flaggea_fecha_0000_sin_cobertura():
    filas = [{"nombre_canonico": "0000-00-00_doc.pdf", "sha256": "a", "parent_id": "", "fecha": "0000-00-00"}]
    problemas = verificar_sala.verificar(
        filas, ficheros_en_disco={"0000-00-00_doc.pdf"}, cobertura_filas=[])
    assert problemas == []


def test_no_flaggea_fecha_0000_con_texto_insuficiente_o_vacio():
    filas = [{"nombre_canonico": "0000-00-00_doc.pdf", "sha256": "a", "parent_id": "", "fecha": "0000-00-00"}]
    cobertura = [{"sha256": "a", "estado": "sin_soporte", "chars": 0}]
    problemas = verificar_sala.verificar(
        filas, ficheros_en_disco={"0000-00-00_doc.pdf"}, cobertura_filas=cobertura)
    assert problemas == []


def test_no_flaggea_fecha_con_valor_real_aunque_haya_cobertura():
    filas = [{"nombre_canonico": "2025-04-08_burofax.pdf", "sha256": "a", "parent_id": "", "fecha": "2025-04-08"}]
    cobertura = [{"sha256": "a", "estado": "ok", "chars": 500}]
    problemas = verificar_sala.verificar(
        filas, ficheros_en_disco={"2025-04-08_burofax.pdf"}, cobertura_filas=cobertura)
    assert problemas == []


def test_detecta_fecha_0000_con_texto_de_bundle_spliteado_via_parent_sha256():
    # Hueco real (auditoria fable-5, 2026-07-21): un PDF escaneado multi-documento
    # spliteado por sala de maquina (core/sala_maquina.py) tiene filas de
    # cobertura donde `sha256` es el hash del SEGMENTO y el hash del fichero de
    # origen (el que consta en el _MANIFIESTO.md de la sala de lectura) va en
    # `parent_sha256`. texto_espejo_md() ya resuelve por "parent_sha256 or
    # sha256"; verificar() solo miraba `sha256` y por tanto los binarios
    # multi-documento -- justo los mas propensos a 0000-00-00 -- escapaban a
    # esta red de seguridad.
    filas = [{"nombre_canonico": "0000-00-00_escaneado.pdf", "sha256": "origen_a", "parent_id": "", "fecha": "0000-00-00"}]
    cobertura = [{"sha256": "seg_1", "parent_sha256": "origen_a", "estado": "ok", "chars": 500}]
    problemas = verificar_sala.verificar(
        filas, ficheros_en_disco={"0000-00-00_escaneado.pdf"}, cobertura_filas=cobertura)
    assert any("0000-00-00" in p and "texto extraído" in p for p in problemas)


def test_detecta_colision_de_nombre_canonico():
    filas = [
        {"nombre_canonico": "2025-01-01_doc.pdf", "sha256": "a", "parent_id": ""},
        {"nombre_canonico": "2025-01-01_doc.pdf", "sha256": "b", "parent_id": ""},
    ]
    problemas = verificar_sala.verificar(filas, ficheros_en_disco={"2025-01-01_doc.pdf"})
    assert any("nombre_canonico repetido" in p and "2025-01-01_doc.pdf" in p for p in problemas)


def test_avisa_de_fallos_homogeneos_por_encima_del_umbral():
    # 6 anexos con parent_id que no resuelve -> mismo tipo 'parent_huerfano'.
    filas = [{"nombre_canonico": "p.pdf", "sha256": "p", "parent_id": ""}]
    for i in range(6):
        filas.append({"nombre_canonico": f"a{i}.pdf", "sha256": f"s{i}", "parent_id": "no-existe"})
    disco = {f["nombre_canonico"] for f in filas}
    problemas = verificar_sala.verificar(filas, ficheros_en_disco=disco)
    assert problemas[0].startswith("ATENCIÓN:")
    assert "homogéneos" in problemas[0] and "parent_huerfano" in problemas[0]


def test_no_avisa_homogeneo_por_debajo_del_umbral():
    filas = [{"nombre_canonico": "p.pdf", "sha256": "p", "parent_id": ""}]
    for i in range(3):
        filas.append({"nombre_canonico": f"a{i}.pdf", "sha256": f"s{i}", "parent_id": "no-existe"})
    disco = {f["nombre_canonico"] for f in filas}
    problemas = verificar_sala.verificar(filas, ficheros_en_disco=disco)
    assert not any(p.startswith("ATENCIÓN:") for p in problemas)
