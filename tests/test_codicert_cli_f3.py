"""El frontal de F3: `aportable` prepara lo que va al juzgado. No gasta ni sube nada."""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("reportlab", reason="hace falta para fabricar los certificados")

from core import expedicion_certificada as exp  # noqa: E402
from scripts import codicert as cli  # noqa: E402
from tests.test_expedicion_aportable import W, _escenario  # noqa: E402


def test_render_aportables_ensena_estado_ruta_retiradas_y_avisos():
    r = exp.AportablePreparado(
        id_envio="006c", canal="electronico", estado=exp.PRODUCIDO,
        ruta_aportable=Path("x - APORTABLE.pdf"), ruta_manifiesto=Path("x - MANIFIESTO.json"),
        retiradas=(5,), avisos=("un aviso",))
    texto = cli.render_aportables([r])
    assert "006c" in texto and "PRODUCIDO" in texto and "APORTABLE" in texto
    assert "páginas 5 del certificado" in texto and "un aviso" in texto
    assert "NO lleva la firma" in texto
    assert "IMAGEN" in texto and "OCR" in texto        # R2/H-01: qué es, dicho donde se usa


def test_render_aportables_ensena_el_MOTIVO_de_una_parada():
    r = exp.AportablePreparado(id_envio="006b", canal="burofax", estado=exp.PARADO,
                               motivo="no aparece en la reproducción")
    assert "no aparece en la reproducción" in cli.render_aportables([r])


def test_aportable_NO_exige_doc_ni_confirmar(capsys):
    """No gasta ni manda nada a terceros: ni `--doc` ni `--confirmar` le hacen falta.

    Se exige el rechazo CONCRETO de `--confirmar`: un `SystemExit` a secas también lo
    daría una orden que no existiera, y el test pasaría por la razón equivocada.
    """
    with pytest.raises(SystemExit):
        cli.main(["aportable", W, "--tipo", "OVC", "--plaza", "Madrid",
                  "--confirmar", "loquesea"])
    assert "unrecognized arguments: --confirmar" in capsys.readouterr().err


def test_main_APORTABLE_cablea_y_escribe_junto_al_integro(monkeypatch, capsys, tmp_path):
    """El cableado CLI → entorno → core, que es donde vivía el H-01 de F2."""
    entorno, _, carpeta = _escenario(tmp_path)
    monkeypatch.setattr(exp, "entorno_real", lambda **kw: entorno)
    assert cli.main(["aportable", W, "--tipo", "OVC", "--plaza", "Madrid",
                     "--entorno", "produccion"]) == 0
    salida = capsys.readouterr().out
    assert "PRODUCIDO" in salida
    assert list(carpeta.glob("* - APORTABLE.pdf"))


def test_main_APORTABLE_sale_con_1_si_algun_envio_queda_parado(monkeypatch, capsys,
                                                               tmp_path):
    entorno, _, carpeta = _escenario(tmp_path)
    integro = carpeta / exp.nombre_canonico("OFERTA VINCULANTE", W, "006c")
    exp.ruta_aportable(integro).write_bytes(b"%PDF-1.4 otro")
    monkeypatch.setattr(exp, "entorno_real", lambda **kw: entorno)
    assert cli.main(["aportable", W, "--tipo", "OVC", "--plaza", "Madrid",
                     "--entorno", "produccion"]) == 1
    assert "no se pisa" in capsys.readouterr().out
