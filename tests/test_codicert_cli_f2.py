"""El frontal de F2: `estado` enseña, `cosechar` archiva. Ninguno gasta."""
from __future__ import annotations

from datetime import datetime

import pytest

from core import expedicion_certificada as exp
from scripts import codicert as cli


def _envio(id_envio, tipo="c", **kw):
    base = dict(id_envio=id_envio, tipo=tipo, asunto="REQUERIMIENTO",
                destinatario="x@y.es", id_personalizado="W-04AKM2 - OVC",
                fecha_envio=datetime.fromisoformat("2026-09-10T18:26:08+02:00"),
                historico=(exp.EstadoCertificado(
                    codigo=20, titulo="Leído",
                    fecha=datetime.fromisoformat("2026-09-12T23:03:43+02:00")),))
    base.update(kw)
    return exp.EnvioObservado(**base)


def test_render_estado_ensena_los_dos_relojes():
    e = exp.Expedicion(id_personalizado="W-04AKM2 - OVC", entorno="produccion",
                       envios=(_envio("006a"),))
    partes = [{"nombre": "ANA", "1apellido": "LÓPEZ", "email": "x@y.es"}]
    texto = cli.render_estado(e, partes)
    assert "W-04AKM2 - OVC" in texto and "PRODUCCION" in texto
    assert "ANA LÓPEZ" in texto and "12/09/2026" in texto


def test_render_estado_declara_los_codigos_desconocidos():
    """M-2: un código sin clasificar se nombra, no se disimula."""
    raro = _envio("006z", historico=(exp.EstadoCertificado(
        codigo=999, titulo="?",
        fecha=datetime.fromisoformat("2026-09-12T23:03:43+02:00")),))
    e = exp.Expedicion(id_personalizado="W-04AKM2 - OVC", entorno="produccion",
                       envios=(raro,))
    assert "999" in cli.render_estado(e, [])


def test_render_estado_avisa_de_lo_que_aun_puede_mejorar():
    pendiente = _envio("006p", historico=(exp.EstadoCertificado(
        codigo=21, titulo="Recordatorio lectura entregado",
        fecha=datetime.fromisoformat("2026-09-11T19:00:23+02:00")),))
    e = exp.Expedicion(id_personalizado="W-04AKM2 - OVC", entorno="produccion",
                       envios=(pendiente,))
    texto = cli.render_estado(e, [])
    assert "006p" in texto and "PENDIENTES" in texto


def test_render_estado_sobre_el_VACIO_no_dice_que_este_terminada():
    """§5.2: un censo negativo no prueba ausencia, y el frontal lo escribe."""
    e = exp.Expedicion(id_personalizado="W-04AKM2 - OVC", entorno="produccion")
    texto = cli.render_estado(e, [])
    assert "no prueba" in texto.lower() or "censo" in texto.lower()


def test_render_cosecha_distingue_lo_nuevo_de_lo_que_ya_estaba():
    from pathlib import Path

    c = exp.CertificadoCosechado(
        id_envio="006a", ruta_local=Path("x/y.pdf"), sha256="ab" * 32,
        doc_id="42990", razon_social_emisor="EV MMC SPAIN, S.L.U.",
        usuario_emisor="madrid.bd")
    texto = cli.render_cosecha([c], ())
    assert "42990" in texto and "nuevo" in texto and "madrid.bd" in texto


def test_estado_sin_entorno_en_la_orden_va_a_sandbox(monkeypatch, capsys):
    """Spec §8: la orden manda sobre la variable, también en las lecturas."""
    monkeypatch.setenv("CODICERT_ENTORNO", "produccion")
    assert cli.entorno_de(argumento=None) == "sandbox"
    assert "no autoriza producción" in capsys.readouterr().err


def test_cosechar_NO_declara_confirmar():
    """No gasta ni manda nada a terceros: no hay puerta humana que cerrar.

    `enviar` exige `--confirmar <digest>` porque lo que sale por el otro lado son
    16,97 € y una comunicación irreversible. `cosechar` archiva un PDF y crea un
    documento en el CRM: las dos cosas se deshacen. Pedir un digest aquí sería
    ceremonia, y la ceremonia que no protege nada enseña a saltársela.
    """
    with pytest.raises(SystemExit):   # argparse rechaza el argumento desconocido
        cli.main(["cosechar", "W-04AKM2", "--tipo", "OVC", "--plaza", "Madrid",
                  "--confirmar", "loquesea"])


def test_estado_y_cosechar_NO_exigen_doc():
    """`--doc` es del plan de envío: pedirlo para leer no tendría sentido."""
    for orden in ("estado", "cosechar"):
        parser_ok = True
        try:
            cli.main([orden, "W-04AKM2", "--tipo", "OVC", "--plaza", "NO_EXISTE"])
        except SystemExit as exc:
            # sale por la plaza desconocida, NO por `--doc` ausente
            parser_ok = "plaza" in str(exc)
        assert parser_ok, orden


def test_estado_SIGUE_dando_los_envios_aunque_el_caso_no_este_en_LOCAL():
    """Lo que `estado` lee está en Codicert, no en el disco.

    Medido corriendo el camino real el 2026-09-21: `codicert estado W-04AKM2` murió
    entero con «el caso no está indexado en el catálogo local», y los tres envíos que
    Codicert sí tenía no llegaron a verse. El nivel requerido necesita las partes del
    CRM y el expediente local para resolverlas; **los envíos y sus estados, no**.
    Perder lo segundo por falta de lo primero es tirar la información que se pedía.
    """
    def sin_caso(_w):
        raise exp.ExpedicionError("el caso no está indexado en el catálogo local")

    e = exp.Expedicion(id_personalizado="W-04AKM2 - OVC", entorno="produccion",
                       envios=(_envio("006a"),))
    texto = cli.render_estado(e, sin_caso)
    assert "006a" in texto                        # los envíos se ven igual
    assert "no está indexado" in texto            # y se dice POR QUÉ falta el resto
    assert "REQUERIDO" in texto.upper()


def test_estado_traduce_un_fallo_del_CRM_a_un_mensaje_legible(monkeypatch, capsys):
    """El operador es un abogado: una traza de Python no es lo que debe leer."""
    def revienta(**kw):
        raise exp.ExpedicionError("el caso no está indexado")

    monkeypatch.setattr(exp, "entorno_real", revienta)
    assert cli.main(["estado", "W-04AKM2", "--tipo", "OVC", "--plaza", "Madrid"]) == 1
    assert "el caso no está indexado" in capsys.readouterr().err
