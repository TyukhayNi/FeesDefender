from pathlib import Path

from core.adjuntos_contenido.pipeline import procesar_dir
from core.adjuntos_contenido.resumen import ResumidorNoop, aplicar_resumenes_dir

HEADER = "# GENERADO por core.email_atomize — NO editar.\n\n"


def _sidecar(att_id, nombre, tipo, sha):
    return (HEADER + f"- att_id: {att_id}\n- nombre_original: {nombre}\n- tipo: {tipo}\n"
            + f"- sha256: {sha}\n- primera_aparicion: 2024-01-01\n"
            + "- mensajes: MSG-00001\n- etiquetas: []\n\n## Descripción\n\n(pendiente)\n")


def _setup_rtf(tmp_path: Path) -> Path:
    adj = tmp_path / "adjuntos"
    adj.mkdir()
    (adj / "2024-01-01_burofax_ATT-00001.md").write_text(
        _sidecar("ATT-00001", "burofax.rtf", "application/rtf", "sha-rtf"), encoding="utf-8")
    (adj / "2024-01-01_burofax_ATT-00001.rtf").write_text(
        r"{\rtf1\ansi Hola burofax\par}", encoding="ascii")
    procesar_dir(adj)
    return adj


class _FakeResumidor:
    def resumir(self, texto: str) -> str:
        return "Resumen falso del burofax."

    def describir_imagen(self, ruta: Path) -> str:
        return "Foto de un inmueble."


def test_noop_deja_pendiente(tmp_path: Path):
    adj = _setup_rtf(tmp_path)
    aplicados = aplicar_resumenes_dir(adj, ResumidorNoop())
    assert aplicados == 0
    md = (adj / "2024-01-01_burofax_ATT-00001.contenido.md").read_text(encoding="utf-8")
    assert "resumen_estado: pendiente" in md
    assert "_(pendiente; capa LLM en sesión)_" in md


def test_resumidor_rellena_sin_tocar_texto(tmp_path: Path):
    adj = _setup_rtf(tmp_path)
    aplicados = aplicar_resumenes_dir(adj, _FakeResumidor())
    assert aplicados == 1
    md = (adj / "2024-01-01_burofax_ATT-00001.contenido.md").read_text(encoding="utf-8")
    assert "Resumen falso del burofax." in md
    assert "resumen_estado: hecho" in md
    assert "## Texto\n\nHola burofax" in md  # texto fiel intacto
    # 2ª pasada: ya está hecho, no reaplica
    assert aplicar_resumenes_dir(adj, _FakeResumidor()) == 0
