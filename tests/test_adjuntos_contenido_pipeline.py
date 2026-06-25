from pathlib import Path

from core.adjuntos_contenido.pipeline import procesar_dir

HEADER = "# GENERADO por core.email_atomize — NO editar.\n\n"


def _sidecar(att_id: str, nombre: str, tipo: str, sha: str) -> str:
    return (
        HEADER
        + f"- att_id: {att_id}\n- nombre_original: {nombre}\n- tipo: {tipo}\n"
        + f"- sha256: {sha}\n- primera_aparicion: 2024-01-01\n"
        + "- mensajes: MSG-00001\n- etiquetas: []\n\n## Descripción\n\n(pendiente; OCR en fase 2)\n"
    )


def _crea_adjunto(adj_dir: Path, base: str, ext: str, sidecar: str, data: bytes):
    (adj_dir / f"{base}.md").write_text(sidecar, encoding="utf-8")
    (adj_dir / f"{base}{ext}").write_bytes(data)


def test_pipeline_familias(tmp_path: Path):
    adj = tmp_path / "adjuntos"
    adj.mkdir()
    # RTF (texto)
    _crea_adjunto(adj, "2024-01-01_burofax_ATT-00001", ".rtf",
                  _sidecar("ATT-00001", "burofax.rtf", "application/rtf", "sha-rtf"),
                  br"{\rtf1\ansi Hola burofax\par}")
    # imagen pequeña (omitida)
    _crea_adjunto(adj, "2024-01-01_icon_ATT-00002", ".png",
                  _sidecar("ATT-00002", "icon.png", "image/png", "sha-png"),
                  b"x" * 1024)
    # imagen grande (visión pendiente)
    _crea_adjunto(adj, "2024-01-01_foto_ATT-00003", ".jpg",
                  _sidecar("ATT-00003", "foto.jpg", "image/jpeg", "sha-jpg"),
                  b"x" * (60 * 1024))
    # emz (omitido)
    _crea_adjunto(adj, "2024-01-01_blob_ATT-00004", ".emz",
                  _sidecar("ATT-00004", "blob.emz", "application/octet-stream", "sha-emz"),
                  b"x" * (60 * 1024))

    rep = procesar_dir(adj)

    assert rep.extraidos == 1            # rtf
    assert rep.omitidos == 2             # png pequeño + emz
    assert rep.pendientes_vision == 1    # jpg grande
    assert rep.pendientes_resumen == 2   # rtf (texto) + jpg (visión)
    # se generaron los .contenido.md
    assert (adj / "2024-01-01_burofax_ATT-00001.contenido.md").exists()
    rtf_md = (adj / "2024-01-01_burofax_ATT-00001.contenido.md").read_text(encoding="utf-8")
    assert "Hola burofax" in rtf_md
    assert "metodo_extraccion: rtf" in rtf_md
    # el binario y el sidecar NO se tocan
    assert (adj / "2024-01-01_burofax_ATT-00001.rtf").read_bytes() == br"{\rtf1\ansi Hola burofax\par}"
    assert "NO editar" in (adj / "2024-01-01_burofax_ATT-00001.md").read_text(encoding="utf-8")


def test_pipeline_idempotente_y_skip(tmp_path: Path):
    adj = tmp_path / "adjuntos"
    adj.mkdir()
    _crea_adjunto(adj, "2024-01-01_burofax_ATT-00001", ".rtf",
                  _sidecar("ATT-00001", "burofax.rtf", "application/rtf", "sha-rtf"),
                  br"{\rtf1\ansi Hola burofax\par}")
    rep1 = procesar_dir(adj)
    md1 = (adj / "2024-01-01_burofax_ATT-00001.contenido.md").read_text(encoding="utf-8")
    rep2 = procesar_dir(adj)
    md2 = (adj / "2024-01-01_burofax_ATT-00001.contenido.md").read_text(encoding="utf-8")
    assert rep1.extraidos == 1
    assert rep2.saltados == 1 and rep2.extraidos == 0
    assert md1 == md2  # byte-idéntico


def test_pipeline_poda_huerfanos(tmp_path: Path):
    adj = tmp_path / "adjuntos"
    adj.mkdir()
    _crea_adjunto(adj, "2024-01-01_burofax_ATT-00001", ".rtf",
                  _sidecar("ATT-00001", "burofax.rtf", "application/rtf", "sha-rtf"),
                  br"{\rtf1\ansi Hola burofax\par}")
    huerfano = adj / "2020-01-01_viejo_ATT-99999.contenido.md"
    huerfano.write_text("contenido viejo sin sidecar", encoding="utf-8")

    rep = procesar_dir(adj)

    assert rep.podados == 1
    assert not huerfano.exists()
    assert (adj / "2024-01-01_burofax_ATT-00001.contenido.md").exists()


def test_api_publica_expone_simbolos():
    import core.adjuntos_contenido as ac
    assert hasattr(ac, "procesar_caso")
    assert hasattr(ac, "aplicar_resumenes")
    assert hasattr(ac, "Resumidor")
    assert hasattr(ac, "ResumidorNoop")
    assert hasattr(ac, "ContenidoReport")
