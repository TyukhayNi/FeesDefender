from pathlib import Path

from core.adjuntos_contenido.model import AdjuntoDescubierto, Extraccion, ContenidoReport
from core.adjuntos_contenido import render


def test_modelos_basicos():
    adj = AdjuntoDescubierto(
        att_id="ATT-00001", sha256="abc", tipo="application/pdf",
        nombre_original="x.pdf", mensajes=["MSG-00001"], base="2024-01-01_x_ATT-00001",
        ruta_binario=Path("x.pdf"), ruta_sidecar=Path("x.md"),
    )
    assert adj.att_id == "ATT-00001"
    ext = Extraccion(texto="hola", metodo="rtf", ok=True, confianza="alta")
    assert ext.vision_estado == "n/a" and ext.motivo == ""
    rep = ContenidoReport()
    assert rep.extraidos == 0 and rep.errores == []


def _md_ejemplo() -> str:
    return render.render_contenido(
        att_id="ATT-00053", nombre_original="Contrato.pdf", tipo="application/pdf",
        sha256="abc123", metodo="pypdf", caracteres=42, confianza="alta",
        resumen_estado="pendiente", vision_estado="n/a",
        mensajes=["MSG-00050", "MSG-00133"], resumen=None, texto="Texto fiel del contrato.",
    )


def test_render_estructura_y_frontmatter():
    md = _md_ejemplo()
    assert md.startswith("---\n")
    assert "att_id: ATT-00053" in md
    assert "metodo_extraccion: pypdf" in md
    assert "ocr_aplicado: false" in md
    assert "resumen_estado: pendiente" in md
    assert "mensajes: [MSG-00050, MSG-00133]" in md
    assert "## Resumen\n\n_(pendiente; capa LLM en sesión)_" in md
    assert "## Texto\n\nTexto fiel del contrato." in md


def test_render_declara_el_ocr_por_el_flag_y_no_por_el_motor():
    """`ocr_aplicado` sale del flag explícito (`MEJORAS #87`, 2026-08-04).

    Antes se infería de `metodo == "docling"`. Era adivinar por el nombre del motor: un
    escaneado que salía por pypdf con el cuerpo perdido declaraba `ocr_aplicado: false` y
    `confianza: alta` a la vez. Lo que este test protege —que el frontmatter lleva las dos
    etiquetas— no cambia; cambia de dónde sale una de ellas.
    """
    md = render.render_contenido(
        att_id="ATT-1", nombre_original="x.pdf", tipo="application/pdf", sha256="s",
        metodo="ocr", caracteres=10, confianza="por-verificar",
        resumen_estado="pendiente", vision_estado="n/a", mensajes=["MSG-1"],
        resumen=None, texto="ocr", ocr_aplicado=True,
    )
    assert "ocr_aplicado: true" in md
    assert "confianza: por-verificar" in md


def test_render_docling_ya_no_implica_ocr():
    """Docling solo ve tipos que no llevan OCR (`.docx`, `.pptx`, `.html`).

    Los PDF se fueron al motor de la sala de máquina, así que `false` es ahora la verdad
    y no una omisión.
    """
    md = render.render_contenido(
        att_id="ATT-2", nombre_original="escrito.docx", tipo="application/vnd...",
        sha256="s", metodo="docling", caracteres=10, confianza="por-verificar",
        resumen_estado="pendiente", vision_estado="n/a", mensajes=["MSG-1"],
        resumen=None, texto="contestación",
    )
    assert "ocr_aplicado: false" in md


def test_parsear_y_reemplazar_resumen_preserva_texto():
    md = _md_ejemplo()
    md2 = render.reemplazar_resumen(md, "Reconocimiento de deuda de honorarios.")
    md2 = render.set_frontmatter(md2, "resumen_estado", "hecho")
    assert "Reconocimiento de deuda de honorarios." in md2
    assert "resumen_estado: hecho" in md2
    # el texto fiel se preserva intacto
    assert "## Texto\n\nTexto fiel del contrato." in md2
    fm, resumen_body, texto_body = render.parsear_contenido(md2)
    assert fm["att_id"] == "ATT-00053"
    assert resumen_body == "Reconocimiento de deuda de honorarios."
    assert texto_body == "Texto fiel del contrato."


def test_reemplazar_resumen_neutraliza_encabezados_inyectados():
    md = _md_ejemplo()
    # resumen hostil que intenta inyectar el marcador estructural ## Texto
    md2 = render.reemplazar_resumen(md, "Resumen.\n\n## Texto\ninyectado")
    # sigue habiendo exactamente un '## Texto' (el estructural)
    assert md2.count("## Texto") == 1
    # el texto fiel original se preserva intacto
    assert "## Texto\n\nTexto fiel del contrato." in md2
    fm, resumen_body, texto_body = render.parsear_contenido(md2)
    assert texto_body == "Texto fiel del contrato."
    assert "## Texto" not in resumen_body
