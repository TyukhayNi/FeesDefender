"""Escalera de OCR con degradación explícita (MEJORAS #90, sub-ítem (a)).

Peldaño 1: `--redo-ocr` sobre el documento entero.
Peldaño 2: si falla (típicamente AcroForm), aislar con pypdf las páginas ciegas
           —extraerlas QUITA el AcroForm, que era el bloqueo— y OCR-izarlas.
Peldaño 3: si nada funciona, `degradado=True` → el llamador marca `low`, nunca `ok`.

Validada en vivo sobre 7 documentos, 3 casos y 2 destinos antes de codificarla
(ver `PLAN.md` [SIGUIENTE-OCR-CIEGO] (c1)/(c2)). `--force-ocr` no aparece: no hizo
falta en ninguno.
"""
from pathlib import Path

import pytest

from core.anon import ocr as ocr_mod
from core.anon.exceptions import OCRError

_ACROFORM = ("PDF inválido: x.pdf (This PDF has a user fillable form. "
             "--redo-ocr (or --mode redo) is not currently possible on such files)")


def test_redo_ocr_no_pide_deskew(tmp_path, monkeypatch):
    """ocrmypdf rechaza `--redo-ocr` junto a `--deskew` (verificado en vivo contra
    17.4.2: *"not currently compatible with --deskew, --clean-final and
    --remove-background"*), y `deskew=True` es el default de `ocr_pdf`. El modo
    redo era por tanto inalcanzable dos veces: ningún llamador lo pasaba y, si lo
    hubiera pasado, habría reventado antes de OCR-izar nada.
    """
    import ocrmypdf

    visto = {}

    def _fake(entrada, salida, **kw):
        visto.update(kw)
        Path(salida).write_bytes(b"%PDF-1.4\n")
        return 0

    monkeypatch.setattr(ocrmypdf, "ocr", _fake)
    entrada = tmp_path / "e.pdf"
    entrada.write_bytes(b"%PDF-1.4\n")

    ocr_mod.ocr_pdf(entrada, tmp_path / "s.pdf", redo_ocr=True)

    assert visto["redo_ocr"] is True
    assert visto["deskew"] is False
    assert "skip_text" not in visto


def test_skip_text_conserva_el_deskew(tmp_path, monkeypatch):
    """El camino histórico no cambia: `--skip-text` sí es compatible con deskew."""
    import ocrmypdf

    visto = {}

    def _fake(entrada, salida, **kw):
        visto.update(kw)
        Path(salida).write_bytes(b"%PDF-1.4\n")
        return 0

    monkeypatch.setattr(ocrmypdf, "ocr", _fake)
    entrada = tmp_path / "e.pdf"
    entrada.write_bytes(b"%PDF-1.4\n")

    ocr_mod.ocr_pdf(entrada, tmp_path / "s.pdf")

    assert visto["skip_text"] is True and visto["deskew"] is True


def _imagen(ancho: int, alto: int):
    from PIL import Image
    return Image.new("RGB", (ancho, alto), (210, 210, 210))


def _pdf(path: Path, paginas: list[tuple[str, tuple[int, int] | None]]) -> Path:
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path))
    for texto, raster in paginas:
        if raster is not None:
            c.drawImage(ImageReader(_imagen(*raster)), 0, 0, width=595, height=842)
        if texto:
            c.drawString(40, 800, texto)
        c.showPage()
    c.save()
    return path


_DIGITAL = "Estipulacion cuarta sobre honorarios de intermediacion inmobiliaria pactados."
_SELLO = "Firmado electronicamente por LexNET"
_CUERPO = "BALANCE ABREVIADO PATRIMONIO NETO Y PASIVO ejercicio dos mil veinticuatro. " * 8


def _doc_con_pagina_ciega(tmp_path: Path) -> Path:
    return _pdf(tmp_path / "cuentas.pdf", [(_DIGITAL, None), (_SELLO, (1200, 1600))])


def test_peldano_1_usa_redo_ocr_sobre_el_documento_entero(tmp_path, monkeypatch):
    entrada = _doc_con_pagina_ciega(tmp_path)
    salida = tmp_path / "out" / "cuentas.pdf"
    visto = {}

    def _fake(ruta_entrada, ruta_salida, **kw):
        visto.update(kw)
        Path(ruta_salida).parent.mkdir(parents=True, exist_ok=True)
        _pdf(Path(ruta_salida), [(_DIGITAL, None), (_CUERPO[:400], (1200, 1600))])
        return Path(ruta_salida)

    monkeypatch.setattr(ocr_mod, "ocr_pdf", _fake)

    res = ocr_mod.ocr_pdf_escalera(entrada, salida)

    assert visto.get("redo_ocr") is True
    assert res.peldano == "redo"
    assert res.ruta == salida
    assert res.degradado is False


def test_un_escaneo_sin_capa_de_texto_no_pierde_el_deskew(tmp_path, monkeypatch):
    """Sin texto embebido no hay nada que «rehacer»: `--skip-text` y `--redo-ocr`
    dan lo mismo, pero el primero conserva `--deskew`, que endereza el escaneo.
    El modo redo se reserva para donde hace falta; la calidad no se regala."""
    entrada = _pdf(tmp_path / "escaneo.pdf", [("", (1200, 1600))])
    visto = {}

    def _fake(ruta_entrada, ruta_salida, **kw):
        visto.update(kw)
        _pdf(Path(ruta_salida), [(_CUERPO[:400], (1200, 1600))])
        return Path(ruta_salida)

    monkeypatch.setattr(ocr_mod, "ocr_pdf", _fake)

    res = ocr_mod.ocr_pdf_escalera(entrada, tmp_path / "out" / "escaneo.pdf")

    assert visto["redo_ocr"] is False
    assert res.peldano == "redo"


def test_un_escaneo_con_sello_si_exige_el_modo_redo(tmp_path, monkeypatch):
    entrada = _pdf(tmp_path / "sellado.pdf", [(_SELLO, (1200, 1600))])
    visto = {}

    def _fake(ruta_entrada, ruta_salida, **kw):
        visto.update(kw)
        _pdf(Path(ruta_salida), [(_CUERPO[:400], (1200, 1600))])
        return Path(ruta_salida)

    monkeypatch.setattr(ocr_mod, "ocr_pdf", _fake)

    ocr_mod.ocr_pdf_escalera(entrada, tmp_path / "out" / "sellado.pdf")

    assert visto["redo_ocr"] is True


def test_el_peldano_2_elige_el_modo_pagina_a_pagina(tmp_path, monkeypatch):
    # pág. 2 muda (nada que rehacer → skip_text + deskew), pág. 3 con sello (redo).
    entrada = _pdf(tmp_path / "mixto.pdf", [
        (_DIGITAL, None), ("", (1200, 1600)), (_SELLO, (1200, 1600))])
    modos = {}

    def _fake(ruta_entrada, ruta_salida, **kw):
        origen = Path(ruta_entrada)
        if origen == entrada:
            raise OCRError(_ACROFORM)
        modos[origen.name[-6:]] = kw["redo_ocr"]
        _pdf(Path(ruta_salida), [(_CUERPO[:400], (1200, 1600))])
        return Path(ruta_salida)

    monkeypatch.setattr(ocr_mod, "ocr_pdf", _fake)

    ocr_mod.ocr_pdf_escalera(entrada, tmp_path / "out" / "mixto.pdf", conservador=True)

    assert modos == {"p2.pdf": False, "p3.pdf": True}


def test_peldano_2_aisla_la_pagina_ciega_cuando_el_acroform_rechaza_el_redo(tmp_path, monkeypatch):
    entrada = _doc_con_pagina_ciega(tmp_path)
    salida = tmp_path / "out" / "cuentas.pdf"
    paginas_ocrizadas = []

    def _fake(ruta_entrada, ruta_salida, **kw):
        origen = Path(ruta_entrada)
        if origen == entrada:                      # documento entero → AcroForm
            raise OCRError(_ACROFORM)
        paginas_ocrizadas.append(origen.name)      # página aislada → sí OCR-iza
        _pdf(Path(ruta_salida), [(_CUERPO[:500], (1200, 1600))])
        return Path(ruta_salida)

    monkeypatch.setattr(ocr_mod, "ocr_pdf", _fake)

    res = ocr_mod.ocr_pdf_escalera(entrada, salida)

    assert res.peldano == "paginas"
    assert res.paginas_ocr == (2,)
    assert res.paginas_fallidas == ()
    assert res.degradado is False
    assert len(paginas_ocrizadas) == 1             # solo la ciega, no la digital


def test_peldano_2_conserva_el_texto_de_las_paginas_digitales(tmp_path, monkeypatch):
    from pypdf import PdfReader

    entrada = _doc_con_pagina_ciega(tmp_path)
    salida = tmp_path / "out" / "cuentas.pdf"

    def _fake(ruta_entrada, ruta_salida, **kw):
        if Path(ruta_entrada) == entrada:
            raise OCRError(_ACROFORM)
        _pdf(Path(ruta_salida), [(_CUERPO[:500], (1200, 1600))])
        return Path(ruta_salida)

    monkeypatch.setattr(ocr_mod, "ocr_pdf", _fake)

    res = ocr_mod.ocr_pdf_escalera(entrada, salida)

    paginas = PdfReader(str(res.ruta)).pages
    assert len(paginas) == 2
    assert "honorarios" in (paginas[0].extract_text() or "")     # digital intacta
    assert "BALANCE" in (paginas[1].extract_text() or "")        # ciega recuperada


def test_conservador_no_intenta_el_peldano_1(tmp_path, monkeypatch):
    """Un documento con capa de texto real: el peldaño 1 reescribiría páginas
    digitales (aditivo, pero reescribe). Con cifras críticas se fuerza el 2."""
    entrada = _doc_con_pagina_ciega(tmp_path)
    salida = tmp_path / "out" / "cuentas.pdf"
    entradas = []

    def _fake(ruta_entrada, ruta_salida, **kw):
        entradas.append(Path(ruta_entrada))
        _pdf(Path(ruta_salida), [(_CUERPO[:500], (1200, 1600))])
        return Path(ruta_salida)

    monkeypatch.setattr(ocr_mod, "ocr_pdf", _fake)

    res = ocr_mod.ocr_pdf_escalera(entrada, salida, conservador=True)

    assert entrada not in entradas                 # nunca el documento entero
    assert res.peldano == "paginas" and res.paginas_ocr == (2,)


def test_peldano_3_degrada_cuando_ninguna_pagina_se_recupera(tmp_path, monkeypatch):
    entrada = _doc_con_pagina_ciega(tmp_path)
    salida = tmp_path / "out" / "cuentas.pdf"

    def _fake(ruta_entrada, ruta_salida, **kw):
        raise OCRError("tesseract se atragantó")

    monkeypatch.setattr(ocr_mod, "ocr_pdf", _fake)

    res = ocr_mod.ocr_pdf_escalera(entrada, salida)

    assert res.peldano == "fallido"
    assert res.degradado is True                   # el llamador debe marcar low
    assert res.paginas_fallidas == (2,)
    assert res.ruta == entrada                     # sin artefacto: no se miente


def test_la_nota_dice_por_que_fallo_la_pagina(tmp_path, monkeypatch):
    """En el camino conservador el peldaño 1 ni se intenta, así que el único
    motivo que existe es el de la página. Sin él la nota dice «no recuperado» y
    no sirve para diagnosticar nada."""
    entrada = _doc_con_pagina_ciega(tmp_path)

    def _fake(ruta_entrada, ruta_salida, **kw):
        raise OCRError("tesseract sin el paquete de idioma cat")

    monkeypatch.setattr(ocr_mod, "ocr_pdf", _fake)

    res = ocr_mod.ocr_pdf_escalera(entrada, tmp_path / "out" / "x.pdf", conservador=True)

    assert res.degradado is True
    assert "paquete de idioma cat" in res.nota


def test_recuperacion_parcial_sigue_siendo_degradada(tmp_path, monkeypatch):
    entrada = _pdf(tmp_path / "tres.pdf", [
        (_DIGITAL, None), (_SELLO, (1200, 1600)), (_SELLO, (1200, 1600))])
    salida = tmp_path / "out" / "tres.pdf"

    def _fake(ruta_entrada, ruta_salida, **kw):
        origen = Path(ruta_entrada)
        if origen == entrada or origen.name.endswith("__p3.pdf"):
            raise OCRError(_ACROFORM)
        _pdf(Path(ruta_salida), [(_CUERPO[:500], (1200, 1600))])
        return Path(ruta_salida)

    monkeypatch.setattr(ocr_mod, "ocr_pdf", _fake)

    res = ocr_mod.ocr_pdf_escalera(entrada, salida)

    assert res.paginas_ocr == (2,) and res.paginas_fallidas == (3,)
    assert res.degradado is True                   # queda texto ciego sin recuperar


def test_sin_paginas_ciegas_el_conservador_no_toca_el_documento(tmp_path, monkeypatch):
    entrada = _pdf(tmp_path / "digital.pdf", [(_DIGITAL, None)])
    salida = tmp_path / "out" / "digital.pdf"

    def _boom(*a, **k):
        raise AssertionError("no hay página ciega: no debe invocarse OCR")

    monkeypatch.setattr(ocr_mod, "ocr_pdf", _boom)

    res = ocr_mod.ocr_pdf_escalera(entrada, salida, conservador=True)

    assert res.peldano == "sin_paginas_ciegas"
    assert res.ruta == entrada and res.degradado is False
    assert not salida.exists()


def test_pdf_ilegible_propaga_el_error_para_que_actue_la_red_de_vision(tmp_path, monkeypatch):
    entrada = tmp_path / "roto.pdf"
    entrada.write_bytes(b"no soy un pdf")

    def _fake(*a, **k):
        raise OCRError("PDF inválido: roto.pdf")

    monkeypatch.setattr(ocr_mod, "ocr_pdf", _fake)

    with pytest.raises(OCRError):
        ocr_mod.ocr_pdf_escalera(entrada, tmp_path / "out" / "roto.pdf")


def test_peldano_1_sin_artefacto_baja_al_peldano_2(tmp_path, monkeypatch):
    """rc=6 / PriorOcrFound: `ocr_pdf` devuelve la ENTRADA y no escribe nada. Eso
    no es éxito — no se recuperó ni un carácter ciego: hay que bajar de peldaño."""
    entrada = _doc_con_pagina_ciega(tmp_path)
    salida = tmp_path / "out" / "cuentas.pdf"

    def _fake(ruta_entrada, ruta_salida, **kw):
        origen = Path(ruta_entrada)
        if origen == entrada:
            return origen                          # rc=6: ni artefacto ni recuperación
        _pdf(Path(ruta_salida), [(_CUERPO[:500], (1200, 1600))])
        return Path(ruta_salida)

    monkeypatch.setattr(ocr_mod, "ocr_pdf", _fake)

    res = ocr_mod.ocr_pdf_escalera(entrada, salida)

    assert res.peldano == "paginas" and res.paginas_ocr == (2,)


@pytest.mark.slow
def test_integracion_acroform_real_recupera_el_cuerpo_escaneado(tmp_path):
    """Contra ocrmypdf y Tesseract reales, la premisa completa de la escalera.

    El peldaño 1 tiene que ser rechazado por el AcroForm, y el peldaño 2 tiene
    que recuperar el cuerpo aislando la página — que es lo que valida que
    extraer la página con pypdf QUITA el formulario, el bloqueo original.
    """
    from PIL import Image, ImageDraw, ImageFont
    from pypdf import PdfReader
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    from core.pdf_paginas import tiene_acroform

    cuerpo = ["BALANCE ABREVIADO", "PATRIMONIO NETO Y PASIVO",
              "HONORARIOS DEVENGADOS", "TOTAL ACTIVO 1.234.567"]
    img = Image.new("RGB", (1400, 1900), "white")
    dibujo = ImageDraw.Draw(img)
    try:
        fuente = ImageFont.truetype("arial.ttf", 64)
    except Exception:                                     # pragma: no cover
        fuente = ImageFont.load_default(size=64)
    for i, linea in enumerate(cuerpo):
        dibujo.text((80, 150 + i * 130), linea, fill="black", font=fuente)

    entrada = tmp_path / "cuentas_acroform.pdf"
    c = canvas.Canvas(str(entrada))
    c.drawString(60, 780, "Portada digital con texto nativo de las cuentas anuales.")
    c.acroForm.textfield(name="depositante", x=60, y=700, width=200, height=20)
    c.showPage()
    c.drawImage(ImageReader(img), 0, 0, width=595, height=842)
    c.drawString(40, 20, _SELLO)                          # el pie que engaña al pipeline
    c.showPage()
    c.save()
    assert tiene_acroform(entrada) is True

    with pytest.raises(OCRError, match="fillable form"):
        ocr_mod.ocr_pdf(entrada, tmp_path / "redo.pdf", redo_ocr=True, idiomas="spa")

    res = ocr_mod.ocr_pdf_escalera(entrada, tmp_path / "out.pdf", idiomas="spa")

    assert res.peldano == "paginas" and res.paginas_ocr == (2,) and res.degradado is False
    paginas = PdfReader(str(res.ruta)).pages
    recuperado = paginas[1].extract_text() or ""
    assert "BALANCE" in recuperado and "HONORARIOS" in recuperado
    assert "Portada digital" in (paginas[0].extract_text() or "")


def test_pdf_cifrado_no_baja_a_aislar_paginas(tmp_path, monkeypatch):
    entrada = _doc_con_pagina_ciega(tmp_path)
    llamadas = []

    def _fake(ruta_entrada, ruta_salida, **kw):
        llamadas.append(Path(ruta_entrada))
        raise OCRError(f"PDF cifrado: {Path(ruta_entrada).name}")

    monkeypatch.setattr(ocr_mod, "ocr_pdf", _fake)

    with pytest.raises(OCRError):
        ocr_mod.ocr_pdf_escalera(entrada, tmp_path / "out" / "cifrado.pdf")
    assert llamadas == [entrada]                   # una sola: no se insiste por página
