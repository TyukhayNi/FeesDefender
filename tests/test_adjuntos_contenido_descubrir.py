from pathlib import Path

from core.adjuntos_contenido.descubrir import descubrir

SIDECAR = (
    "# GENERADO por core.email_atomize — NO editar.\n\n"
    "- att_id: ATT-00053\n"
    "- nombre_original: Contrato honorarios profesionales.pdf\n"
    "- tipo: application/pdf\n"
    "- sha256: 12ece1abc\n"
    "- primera_aparicion: 2024-10-05\n"
    "- mensajes: MSG-00050, MSG-00133\n"
    "- etiquetas: []\n\n"
    "## Descripción\n\n(pendiente; OCR en fase 2)\n"
)


def test_descubre_y_empareja(tmp_path: Path):
    adj_dir = tmp_path / "adjuntos"
    adj_dir.mkdir()
    base = "2024-10-05_Contrato_honorarios_profesionales_ATT-00053"
    (adj_dir / f"{base}.md").write_text(SIDECAR, encoding="utf-8")
    (adj_dir / f"{base}.pdf").write_bytes(b"%PDF-1.4 fake")
    # un .contenido.md ajeno NO debe tomarse como sidecar
    (adj_dir / f"{base}.contenido.md").write_text("ruido", encoding="utf-8")

    res = descubrir(adj_dir)

    assert len(res) == 1
    a = res[0]
    assert a.att_id == "ATT-00053"
    assert a.sha256 == "12ece1abc"
    assert a.tipo == "application/pdf"
    assert a.nombre_original == "Contrato honorarios profesionales.pdf"
    assert a.mensajes == ["MSG-00050", "MSG-00133"]
    assert a.base == base
    assert a.ruta_binario == adj_dir / f"{base}.pdf"


def test_sidecar_ficha_md_para_original_md(tmp_path: Path):
    adj_dir = tmp_path / "adjuntos"
    adj_dir.mkdir()
    base = "2024-01-01_nota_ATT-00099"
    sidecar = SIDECAR.replace(
        "Contrato honorarios profesionales.pdf", "nota.md"
    ).replace("ATT-00053", "ATT-00099")
    (adj_dir / f"{base}.ficha.md").write_text(sidecar, encoding="utf-8")
    (adj_dir / f"{base}.md").write_bytes(b"# nota original")

    res = descubrir(adj_dir)

    assert len(res) == 1
    assert res[0].base == base
    assert res[0].ruta_binario == adj_dir / f"{base}.md"
