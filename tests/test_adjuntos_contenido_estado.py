from pathlib import Path

from core.adjuntos_contenido import estado


def test_guardar_y_cargar_roundtrip(tmp_path: Path):
    files = {"sha1": {"metodo": "pypdf", "chars": 10, "ok": True,
                      "resumen_estado": "pendiente", "vision_estado": "n/a", "base": "b1"}}
    estado.guardar_estado(tmp_path, files)
    assert estado.cargar_estado(tmp_path) == files


def test_version_distinta_invalida_cache(tmp_path: Path):
    estado.guardar_estado(tmp_path, {"sha1": {"ok": True}})
    p = tmp_path / estado._ESTADO
    p.write_text(p.read_text(encoding="utf-8").replace(
        f'"contenido_version": {estado.CONTENIDO_VERSION}', '"contenido_version": 999'),
        encoding="utf-8")
    assert estado.cargar_estado(tmp_path) == {}


def test_sin_fichero_devuelve_vacio(tmp_path: Path):
    assert estado.cargar_estado(tmp_path) == {}
