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
