from importlib import import_module
from pathlib import Path
import hashlib
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / ".claude/skills/organizar-sala-lectura/scripts"))
verificar_sala = import_module("verificar_sala")


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _montar_sala(tmp_path, filas_extra="", ficheros=None):
    sala = tmp_path / "Sala lectura"
    sala.mkdir()
    (sala / "_plan").mkdir()
    (sala / "_plan" / "plan-x.md").write_text("ignorame", encoding="utf-8")
    for nombre, contenido in (ficheros or {}).items():
        p = sala / nombre
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(contenido)
    return sala


def test_listar_sala_excluye_indices_y_plan(tmp_path):
    sala = _montar_sala(tmp_path, ficheros={"2025-01-01_doc.pdf": b"x"})
    (sala / "INDICE.md").write_text("i", encoding="utf-8")
    (sala / "_MANIFIESTO.md").write_text("m", encoding="utf-8")
    (sala / "indice_documental.yaml").write_text("y", encoding="utf-8")
    encontrados = verificar_sala._listar_sala(sala)
    assert encontrados == {"2025-01-01_doc.pdf"}


def test_main_exit_0_cuando_cuadra(tmp_path):
    contenido = b"contenido del doc"
    sala = _montar_sala(tmp_path, ficheros={"2025-01-01_doc.pdf": contenido})
    (sala / "_MANIFIESTO.md").write_text(
        "| sha256 | ruta_original | nombre_canonico | tipo | fecha | parte | parent_id |\n"
        "|---|---|---|---|---|---|---|\n"
        f"| {_sha(contenido)} | 00_Input/x.pdf | 2025-01-01_doc.pdf | pdf | 2025-01-01 | propietario |  |\n",
        encoding="utf-8")
    assert verificar_sala.main(["verificar_sala.py", str(sala)]) == 0


def test_main_exit_1_cuando_falta_fichero(tmp_path):
    sala = _montar_sala(tmp_path, ficheros={})
    (sala / "_MANIFIESTO.md").write_text(
        "| sha256 | ruta_original | nombre_canonico | tipo | fecha | parte | parent_id |\n"
        "|---|---|---|---|---|---|---|\n"
        "| aaaa | 00_Input/x.pdf | 2025-01-01_doc.pdf | pdf | 2025-01-01 | propietario |  |\n",
        encoding="utf-8")
    assert verificar_sala.main(["verificar_sala.py", str(sala)]) == 1


def test_main_hash_completo_detecta_copia_corrupta(tmp_path):
    sala = _montar_sala(tmp_path, ficheros={"2025-01-01_doc.pdf": b"contenido REAL en disco"})
    (sala / "_MANIFIESTO.md").write_text(
        "| sha256 | ruta_original | nombre_canonico | tipo | fecha | parte | parent_id |\n"
        "|---|---|---|---|---|---|---|\n"
        f"| {_sha(b'otro contenido esperado')} | 00_Input/x.pdf | 2025-01-01_doc.pdf | pdf | 2025-01-01 | propietario |  |\n",
        encoding="utf-8")
    assert verificar_sala.main(["verificar_sala.py", str(sala), "--hash", "completo"]) == 1
