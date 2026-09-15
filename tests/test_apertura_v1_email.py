"""La etapa `email` de la secuencia de apertura.

Spec: docs/superpowers/specs/2026-09-15-corrida-prepara-sesion-remata-design.md §4.
"""
import pytest

from core import apertura_v1 as av1
from scripts import abrir_caso as cli


class _Ident:
    case_id = "BaRS9 - Calle de Prueba 1 (W-TEST01) - Vuelta"
    w_code = "W-TEST01"
    tipo_caso = "Vuelta"


class _Report:
    """Lo mínimo de `ExportReport` que la etapa lee."""

    def __init__(self, written=3, total_in_label=3, errors=None):
        self.written = written
        self.total_in_label = total_in_label
        self.errors = errors or []


def test_sin_cuenta_ni_label_sale_saltada_con_su_pendiente(tmp_path):
    """Sin etiqueta que traer no hay nada que hacer, y eso se DECLARA.

    `saltada` no es `hecha`: es una decisión con razón declarada. Y lleva pendiente
    porque una corrida sin correo tiene que ser distinguible de una con correo.
    """
    r = cli.etapa_email(_Ident(), tmp_path, cuenta=None, label=None)

    assert r.nombre == "email"
    assert r.estado == "saltada"
    assert r.pendientes, "una etapa saltada sin pendiente es un silencio"
    assert r.pendientes[0].codigo == "email_no_pedido"


def test_con_cuenta_y_label_sale_hecha_y_cuenta_lo_escrito(tmp_path):
    r = cli.etapa_email(_Ident(), tmp_path, cuenta="a@b.c", label="CASO/X",
                        exportar=lambda: _Report(written=3, total_in_label=5))

    assert r.estado == "hecha"
    assert r.pendientes == ()
    assert "3" in r.detalle and "5" in r.detalle


def test_un_fallo_del_exportador_no_tumba_la_corrida(tmp_path):
    """El estado de V1 es el producto, no la traza: la etapa traduce, no propaga."""
    def _revienta():
        raise RuntimeError("token caducado")

    r = cli.etapa_email(_Ident(), tmp_path, cuenta="a@b.c", label="CASO/X",
                        exportar=_revienta)

    assert r.estado == "fallo"
    assert "RuntimeError" in r.detalle and "token caducado" in r.detalle


def test_los_errores_parciales_del_export_se_dicen_sin_ser_un_fallo(tmp_path):
    """Un export que escribe y además acumula errores NO es un fallo, pero tampoco
    es un `hecha` limpio: los errores viajan como pendiente o la corrida los pierde."""
    r = cli.etapa_email(_Ident(), tmp_path, cuenta="a@b.c", label="CASO/X",
                        exportar=lambda: _Report(written=2, total_in_label=4,
                                                 errors=["msg 7 sin adjunto"]))

    assert r.estado == "hecha"
    assert r.pendientes, "un export con errores que no deja pendiente los pierde"
    assert r.pendientes[0].codigo == "email_export_con_errores"


def test_la_etapa_nunca_llama_a_gmail_por_su_cuenta(tmp_path, monkeypatch):
    """La costura es obligatoria en test: si `exportar` no se inyecta, la etapa
    construiría el cliente real. Aquí se prueba que la costura MANDA."""
    llamadas = []
    monkeypatch.setattr(cli.email_export, "export_label",
                        lambda *a, **k: llamadas.append(a) or _Report())

    cli.etapa_email(_Ident(), tmp_path, cuenta="a@b.c", label="L",
                    exportar=lambda: _Report())

    assert llamadas == [], "con `exportar` inyectado no se toca `export_label`"


def test_exportar_none_construye_bien_la_llamada_a_email_export(tmp_path, monkeypatch):
    """Los cinco tests de arriba inyectan `exportar`: la rama real (`exportar=None`,
    la que corre en producción) no la ejercita ninguno. Si esa rama invirtiera el
    orden de los argumentos, olvidara el `case_id=` o pusiera `extract_attachments`
    a `False`, esta suite seguiría en verde. Aquí se sustituyen `email_dest_dir` y
    `export_label` por dobles que graban los argumentos con los que se las llama,
    sin tocar red ni disco: no basta con que la etapa no reviente, hay que
    comprobar que la llamada se arma bien.
    """
    llamadas_dest = []
    llamadas_export = []
    destino = tmp_path / "00_Input" / "2026-09-15_email_01"

    def _fake_dest_dir(case_id):
        llamadas_dest.append(case_id)
        return destino

    def _fake_export_label(*args, **kwargs):
        llamadas_export.append((args, kwargs))
        return _Report(written=1, total_in_label=1)

    monkeypatch.setattr(cli.email_export, "email_dest_dir", _fake_dest_dir)
    monkeypatch.setattr(cli.email_export, "export_label", _fake_export_label)

    ident = _Ident()
    r = cli.etapa_email(ident, tmp_path, cuenta="a@b.c", label="CASO/X")

    assert llamadas_dest == [ident.case_id]
    assert len(llamadas_export) == 1
    args, kwargs = llamadas_export[0]
    assert args == ("a@b.c", "CASO/X", destino)
    assert kwargs == {"case_id": ident.case_id, "extract_attachments": True}
    assert r.estado == "hecha"
