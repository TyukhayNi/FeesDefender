"""Remediaciones de la R1 de la acción 6b — un test por hallazgo.

Acta literal:
`docs/superpowers/specs/2026-09-06-accion-6b-adjuntos-firmas-r1-adversarial-review.md`
(veredicto `NO-SHIP`, 4 hallazgos, 4 confirmados, 0 refutados).

**El hallazgo que cambió el diseño, no solo el código.** H-01 demostró que el filtro
descartaba imágenes que pueden ser prueba —una aceptación escaneada, un justificante— y
que la red de seguridad no existía: `adjuntos_contenido/router.py` vuelve a omitir las
imágenes < 50 KB, así que el atomizador tampoco rescataba el texto. **Decisión de Nikolai
(2026-09-06): marcar, no excluir.** Es la doctrina de `contaminacion.py` aplicada donde
tenía que estar desde el principio — en material probatorio se avisa, no se descarta —, y
convierte el falso positivo en un nombre feo en vez de una pérdida.
"""
from __future__ import annotations

from email.message import EmailMessage

import pytest

from core import email_export as ee
from tests.test_email_export import _ETIQUETA, _LABELS, _FakeService, _build_raw
from tests.test_email_export_firmas_incrustadas import _PNG, _mensaje

_CUENTA = "nikolai@engelvoelkers.com"


def _svc(raws):
    return _FakeService(
        labels=_LABELS, pages=[{"messages": [{"id": g} for g in raws]}], raws=raws)


# ==========================================================================
# H-01 (ALTO) — marcar, no excluir
# ==========================================================================

def _aceptacion_pequena() -> dict[str, bytes]:
    """El escenario que el revisor construyó: una imagen que SÍ es prueba y que el
    filtro descartaba — pequeña, `inline`, con `Content-ID`."""
    return {"g1": _mensaje([
        (_PNG, "image/png", "aceptacion_honorarios.png", "inline", "<doc@x>"),
    ])}


def test_H01_la_imagen_marcada_como_firma_SE_ESCRIBE_igual(tmp_path):
    """Lo que este hallazgo cambia: el filtro clasifica, no descarta. Un falso
    positivo cuesta un nombre feo, no un documento perdido."""
    ee.export_label(_CUENTA, _ETIQUETA, tmp_path, service=_svc(_aceptacion_pequena()))

    escritos = [p for p in tmp_path.rglob("*") if p.is_file()
                and p.suffix.lower() == ".png"]
    assert len(escritos) == 1, "la imagen está en el expediente"
    assert "aceptacion_honorarios" in escritos[0].name


def test_H01_pero_va_marcada_con_prefijo(tmp_path):
    """La marca hace dos cosas: la hunde en el orden de la carpeta y le dice al
    letrado por qué está ahí abajo. No la esconde."""
    ee.export_label(_CUENTA, _ETIQUETA, tmp_path, service=_svc(_aceptacion_pequena()))

    png = next(p for p in tmp_path.rglob("*.png"))
    assert png.name.startswith(ee.PREFIJO_FIRMA)


def test_H01_el_report_dice_MARCADAS_no_filtradas(tmp_path):
    rep = ee.export_label(_CUENTA, _ETIQUETA, tmp_path, service=_svc(_aceptacion_pequena()))

    assert rep.firmas_marcadas == 1
    assert rep.attachments == 1, "cuenta como adjunto depositado, porque lo está"
    assert "1 marcadas como firma" in rep.resumen()
    assert not hasattr(rep, "firmas_filtradas"), "el contador de descarte ya no existe"


def test_H01_lo_que_NO_parece_firma_sale_sin_prefijo(tmp_path):
    raws = {"g1": _mensaje([
        (b"%PDF-1.4 contrato", "application/pdf", "contrato.pdf", "attachment", None)])}
    rep = ee.export_label(_CUENTA, _ETIQUETA, tmp_path, service=_svc(raws))

    pdf = next(p for p in tmp_path.rglob("*.pdf"))
    assert pdf.name == "contrato.pdf"
    assert rep.firmas_marcadas == 0


def test_H01_un_correo_cuyo_unico_adjunto_es_firma_SI_crea_subcarpeta(tmp_path):
    """Cambia respecto a la versión anterior: si la firma se conserva, hay algo que
    depositar, así que la subcarpeta tiene contenido y razón de ser."""
    ee.export_label(_CUENTA, _ETIQUETA, tmp_path, service=_svc(_aceptacion_pequena()))
    assert (tmp_path / "2026-06-12_con_imagenes").is_dir()


# ==========================================================================
# H-02 (ALTO) — el `.eml` con MIME genérico no es un correo del caso
# ==========================================================================

def _eml_generico_con_ruido() -> dict[str, bytes]:
    """Un correo del caso que adjunta un `.eml` con MIME genérico, y ese `.eml` es
    ruido administrativo. El escenario exacto del revisor."""
    hijo = _build_raw(
        message_id="<factura@x>", subject="Factura agosto",
        to_addr="Proveedores.ES@engelvoelkers.com")
    padre = EmailMessage()
    padre["Message-ID"] = "<padre-gen@x>"
    padre["Subject"] = "Documentación del caso"
    padre["Date"] = "Thu, 12 Jun 2026 10:00:00 +0200"
    padre["From"] = "eva@engelvoelkers.com"
    padre["To"] = "despacho@tyukhay.legal"
    padre.set_content("Te adjunto lo hablado.")
    # MIME GENERICO, no message/rfc822: la bifurcación de `MEJORAS #55.1`.
    padre.add_attachment(hijo, maintype="application", subtype="octet-stream",
                         filename="tercero.eml")
    return {"g1": padre.as_bytes()}


def test_H02_un_eml_generico_NO_se_publica_como_correo_del_caso(tmp_path):
    """`particionar_eml` saltaba `message/rfc822` **por MIME**, así que un
    `application/octet-stream; filename="x.eml"` pasaba y se escribía como correo
    independiente — eludiendo el filtro de ruido de la 6a y sin procedencia.

    `MEJORAS_FUTURAS.md` §55.1 ya documentaba esta bifurcación, y advertía que estos
    ficheros «solo aparecen si `--extraer-adjuntos` los escribe a disco»: invertir el
    default es exactamente lo que abre la puerta. Estaba escrito.
    """
    rep = ee.export_label(_CUENTA, _ETIQUETA, tmp_path, service=_svc(_eml_generico_con_ruido()))

    assert rep.written == 1, "solo el padre"
    nombres = " ".join(p.name.lower() for p in tmp_path.rglob("*") if p.is_file())
    assert "factura" not in nombres
    assert not list(tmp_path.rglob("tercero.eml"))


def test_H02_el_eml_generico_pasa_por_la_POLITICA_DE_RUIDO(tmp_path):
    """No basta con no escribirlo: tiene que quedar dicho por qué, como cualquier otro
    mensaje que el filtro para."""
    rep = ee.export_label(_CUENTA, _ETIQUETA, tmp_path, service=_svc(_eml_generico_con_ruido()))

    marcado = rep.excluidos_ruido + rep.ruido_transportado
    assert marcado, "el .eml genérico ruidoso se declara"
    assert any(e.get("regla") == "facturacion_despacho" for e in marcado)


def test_H02_un_eml_generico_LEGITIMO_conserva_su_procedencia(tmp_path):
    """La otra dirección: si el `.eml` adjunto es del caso, entra — pero por la vía del
    aplanado, que conserva la relación padre-hijo, no como correo suelto."""
    hijo = _build_raw(message_id="<hijo-ok@x>", subject="Oferta del inmueble")
    padre = EmailMessage()
    padre["Message-ID"] = "<padre-ok@x>"
    padre["Subject"] = "RV: la oferta"
    padre["Date"] = "Thu, 12 Jun 2026 10:00:00 +0200"
    padre["From"] = "eva@engelvoelkers.com"
    padre["To"] = "despacho@tyukhay.legal"
    padre.set_content("Adjunto.")
    padre.add_attachment(hijo, maintype="application", subtype="octet-stream",
                         filename="oferta.eml")

    rep = ee.export_label(_CUENTA, _ETIQUETA, tmp_path, service=_svc({"g1": padre.as_bytes()}))

    assert rep.nested_flattened == 1, "entra por el aplanado, con procedencia"
    assert rep.written == 1


# ==========================================================================
# H-03 (MEDIO) — el CLI no puede romper invocaciones existentes
# ==========================================================================

@pytest.mark.parametrize("extra,esperado", [
    ([], True),
    (["--extraer-adjuntos"], True),
    (["--no-extraer-adjuntos"], False),
])
def test_H03_las_TRES_formas_del_flag_se_parsean(monkeypatch, tmp_path, extra, esperado):
    """Cambiar el default no exigía dejar de reconocer el flag positivo. Con solo el
    negativo, una invocación existente muere con `SystemExit(2)` antes de llegar al
    motor — y la skill del equipo todavía documenta el positivo."""
    import contextlib

    import scripts.export_label_emails as cli

    capturado: dict = {}
    monkeypatch.setattr(cli, "export_label",
                        lambda a, l, d, **kw: (capturado.update(kw),
                                               ee.ExportReport(account=a, label=l))[1])
    monkeypatch.setattr(cli, "resolve_ref", lambda r: r)
    monkeypatch.setattr(cli, "email_dest_dir", lambda c: tmp_path)
    monkeypatch.setattr(cli, "w_code_de", lambda c: "W-TEST01")

    @contextlib.contextmanager
    def _sin_mutex(*a, **kw):
        yield

    monkeypatch.setattr(cli, "sostener", _sin_mutex)

    cli.main(["--ref", "X", "--account", "a@b.c", "--label", "L", *extra])
    assert capturado["extract_attachments"] is esperado


# ==========================================================================
# H-04 (MEDIO) — `filtrar_ruido=False` tiene que llegar a TODAS las puertas
# ==========================================================================

def _padre_con_hijo_ruidoso() -> dict[str, bytes]:
    from tests.test_email_export import _child, _envoltorio, _parte_rfc822
    hijo = _child(mid=b"<ruido@x>", subject=b"Circularizacion de auditoria 2026",
                  date=b"Mon, 08 Jun 2026 11:00:00 +0200")
    return {"g1": _envoltorio(b"BTOP", [_parte_rfc822(hijo)])}


def test_H04_con_el_filtro_APAGADO_el_hijo_anidado_SI_se_extrae(tmp_path):
    """La vía de vuelta que el plan anuncia no funcionaba por esta puerta: cablée
    `clasificar_ruido` en `_aplana_anidados` sin propagarle la opción. Defecto mío del
    mismo día, al remediar el H-01 de la ronda anterior."""
    rep = ee.export_label(_CUENTA, _ETIQUETA, tmp_path, service=_svc(_padre_con_hijo_ruidoso()),
                          filtrar_ruido=False)

    assert rep.nested_flattened == 1
    assert rep.ruido_transportado == []


def test_H04_con_el_filtro_ENCENDIDO_sigue_sin_extraerse(tmp_path):
    rep = ee.export_label(_CUENTA, _ETIQUETA, tmp_path, service=_svc(_padre_con_hijo_ruidoso()))

    assert rep.nested_flattened == 0
    assert len(rep.ruido_transportado) == 1


def test_H04_el_rescate_por_enlace_tambien_respeta_la_opcion(tmp_path):
    """Y el resultado tiene que distinguir «excluido» de «ya presente»: el rescate
    marcaba `dedup=True` para un mensaje que nunca se depositó."""
    ruidoso = _build_raw(message_id="<r@x>", subject="Circularización de auditoría 2026")
    rep = ee.ExportReport(account=_CUENTA, label=_ETIQUETA)

    ruta = ee._deposita_mensaje_rescatado(tmp_path, ruidoso, set(), {}, rep,
                                          filtrar_ruido=False)

    assert ruta is not None, "con el filtro apagado, se deposita"
    assert rep.excluidos_ruido == []
