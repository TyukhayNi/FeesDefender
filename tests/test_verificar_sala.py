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
