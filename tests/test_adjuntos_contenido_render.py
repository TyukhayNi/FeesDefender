from pathlib import Path

from core.adjuntos_contenido.model import AdjuntoDescubierto, Extraccion, ContenidoReport


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
