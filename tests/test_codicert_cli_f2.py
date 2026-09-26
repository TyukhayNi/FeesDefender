"""El frontal de F2: `estado` enseña, `cosechar` archiva. Ninguno gasta."""
from __future__ import annotations

from datetime import datetime

import pytest

from core import expedicion_certificada as exp
from scripts import codicert as cli

#: Cuándo se «leyó» la expedición de los tests (D-4: la hora de la lectura es
#: obligatoria). Cerca de las fechas de sus históricos, para que nada salga estancado.
LEIDA = datetime.fromisoformat("2026-09-13T10:00:00+02:00")


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
                       envios=(_envio("006a"),), leida_en=LEIDA)
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
                       envios=(raro,), leida_en=LEIDA)
    assert "999" in cli.render_estado(e, [])


def test_render_estado_avisa_de_lo_que_aun_puede_mejorar():
    pendiente = _envio("006p", historico=(exp.EstadoCertificado(
        codigo=21, titulo="Recordatorio lectura entregado",
        fecha=datetime.fromisoformat("2026-09-11T19:00:23+02:00")),))
    e = exp.Expedicion(id_personalizado="W-04AKM2 - OVC", entorno="produccion",
                       envios=(pendiente,), leida_en=LEIDA)
    texto = cli.render_estado(e, [])
    assert "006p" in texto and "PENDIENTES" in texto


def test_render_estado_sobre_el_VACIO_no_dice_que_este_terminada():
    """§5.2: un censo negativo no prueba ausencia, y el frontal lo escribe."""
    e = exp.Expedicion(id_personalizado="W-04AKM2 - OVC", entorno="produccion",
                       leida_en=LEIDA)
    texto = cli.render_estado(e, [])
    assert "no prueba" in texto.lower() or "censo" in texto.lower()


def test_render_cosecha_distingue_lo_nuevo_de_lo_que_ya_estaba():
    from pathlib import Path

    c = exp.CertificadoCosechado(
        id_envio="006a", ruta_local=Path("x/y.pdf"), sha256="ab" * 32,
        doc_id="42990", razon_social_emisor="EV MMC SPAIN, S.L.U.",
        usuario_emisor="madrid.bd")
    texto = cli.render_cosecha([c], exp.Expedicion(
        id_personalizado="W-04AKM2 - OVC", entorno="produccion", leida_en=LEIDA))
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
                       envios=(_envio("006a"),), leida_en=LEIDA)
    texto = cli.render_estado(e, sin_caso)
    assert "006a" in texto                        # los envíos se ven igual
    assert "no está indexado" in texto            # y se dice POR QUÉ falta el resto
    assert "REQUERIDO" in texto.upper()


def _entorno_doble(tmp_path, gestor=None):
    """Un `EntornoExpedicion` completo, como el que monta `entorno_real`."""
    from datetime import timezone

    cert = b"%PDF-1.4 certificado"

    class _T:
        def listar(self, **kw):
            return [{"id": "006a", "tipo": "c", "asunto": "SONDA",
                     "destinatarios": "x@y.es", "id_personalizado": "W-04AKM2 - OVC",
                     "fecha": "2026-09-10T18:26:08+02:00"}]

        def estados(self, i):
            return [{"codigo": 20, "titulo": "Leído",
                     "fecha": "2026-09-12T23:03:43+02:00", "detalle": None}]

        def certificado(self, i):
            return cert

    class _G:
        def __init__(self):
            self.subidos = []

        def subir(self, contenido, *, nombrefinal, mime, related, al_reservar=None):
            if al_reservar:
                al_reservar("uuid-0")
            self.subidos.append(nombrefinal)
            return exp.DocumentoEnCrm(doc_id="doc1", origen_id="uuid-0",
                                      nombrefinal=nombrefinal, sha256="ab" * 32)

        def buscar_por_origen_id(self, oid, *, element, exp_id):
            return None

        def buscar_por_nombre(self, n, *, element, exp_id):
            return None

        def descargar(self, doc_id):
            return cert

    return exp.EntornoExpedicion(
        codicert=_T(), partes_de=lambda w: [],
        ahora=lambda: datetime(2026, 9, 21, tzinfo=timezone.utc),
        raiz=tmp_path, plaza="Madrid", entorno="produccion", usuario="madrid.bd",
        carpeta_certificados=lambda w: tmp_path / "caso" / "Certificados",
        gestor=gestor if gestor is not None else _G(),
        exp_crm=lambda w: ("extrajudiciales", "123"),
        leer_emisor=lambda pdf: exp.EmisorLeido(
            razon_social="EV MMC SPAIN, S.L.U.", usuario="madrid.bd"))


def test_main_ESTADO_cablea_el_frontal_con_el_entorno_real(monkeypatch, capsys,
                                                           tmp_path):
    """El cableado CLI → entorno → transporte, que es donde vivía H-01.

    Los tests de `render_estado` prueban el formato con datos armados a mano; este
    prueba que la orden **llega** hasta el transporte y vuelve. El hallazgo H-01 —
    el transporte real sin `estados`— pasó inadvertido precisamente porque nada
    ejercitaba este tramo.
    """
    monkeypatch.setattr(exp, "entorno_real",
                        lambda **kw: _entorno_doble(tmp_path))
    assert cli.main(["estado", "W-04AKM2", "--tipo", "OVC", "--plaza", "Madrid",
                     "--entorno", "produccion"]) == 0
    salida = capsys.readouterr().out
    assert "006a" in salida and "PRODUCCION" in salida


def test_main_COSECHAR_cablea_y_archiva(monkeypatch, capsys, tmp_path):
    """Lo mismo para `cosechar`, que además escribe y sube."""
    monkeypatch.setattr(exp, "entorno_real",
                        lambda **kw: _entorno_doble(tmp_path))
    assert cli.main(["cosechar", "W-04AKM2", "--tipo", "OVC", "--plaza", "Madrid",
                     "--entorno", "produccion"]) == 0
    salida = capsys.readouterr().out
    assert "doc1" in salida and "nuevo" in salida
    assert (tmp_path / "caso" / "Certificados").is_dir()


def test_main_COSECHAR_con_incluir_pendientes_llega_al_core(monkeypatch, capsys,
                                                            tmp_path):
    """El flag tiene que viajar: un argparse que no lo pase es un flag inerte."""
    visto = {}

    def espia(w, t, *, entorno_exp, ordinal=1, **kw):
        visto.update(kw)
        return []

    monkeypatch.setattr(exp, "entorno_real", lambda **kw: _entorno_doble(tmp_path))
    monkeypatch.setattr(exp, "cosechar", espia)
    cli.main(["cosechar", "W-04AKM2", "--tipo", "OVC", "--plaza", "Madrid",
              "--incluir-pendientes"])
    assert visto.get("incluir_pendientes") is True


def test_estado_traduce_un_fallo_del_CRM_a_un_mensaje_legible(monkeypatch, capsys):
    """El operador es un abogado: una traza de Python no es lo que debe leer."""
    def revienta(**kw):
        raise exp.ExpedicionError("el caso no está indexado")

    monkeypatch.setattr(exp, "entorno_real", revienta)
    assert cli.main(["estado", "W-04AKM2", "--tipo", "OVC", "--plaza", "Madrid"]) == 1
    assert "el caso no está indexado" in capsys.readouterr().err


def test_render_estado_separa_lo_estancado_de_lo_que_puede_mejorar():
    """M-19/M-21: un burofax 88 días en 17 no «puede mejorar»; se dice, con la salida."""
    estancado = _envio("006e", tipo="b", historico=(exp.EstadoCertificado(
        codigo=17, titulo="Entregado",
        fecha=datetime.fromisoformat("2026-06-17T10:00:00+02:00")),))
    reciente = _envio("006m", historico=(exp.EstadoCertificado(
        codigo=21, titulo="Recordatorio lectura entregado",
        fecha=datetime.fromisoformat("2026-09-11T19:00:23+02:00")),))
    e = exp.Expedicion(id_personalizado="W-04AKM2 - OVC", entorno="produccion",
                       envios=(estancado, reciente), leida_en=LEIDA)
    texto = cli.render_estado(e, [])
    bloque_estancado = texto.index(exp.QUE_SIGNIFICA[exp.ESTANCADO])
    bloque_mejora = texto.index(exp.QUE_SIGNIFICA[exp.PUEDE_MEJORAR])
    assert bloque_estancado < texto.index("· 006e") < bloque_mejora < texto.index("· 006m")
    assert "88 días sin moverse" in texto and "--incluir-pendientes" in texto


def test_render_estado_declara_los_canales_sin_clasificar():
    """M-18: el tipo `s` sale con su aviso, como un código sin clasificar."""
    e = exp.Expedicion(id_personalizado="W-04AKM2 - OVC", entorno="produccion",
                       envios=(_envio("006s", tipo="s"),), leida_en=LEIDA)
    texto = cli.render_estado(e, [])
    assert "CANALES SIN CLASIFICAR: tipo s" in texto
    assert exp.QUE_SIGNIFICA[exp.CANAL_SIN_CLASIFICAR] in texto
    assert "sus fechas no cuentan en «POR REQUERIDO»" in texto


def test_render_cosecha_dice_por_que_no_cosecho():
    estancado = _envio("006e", tipo="b", historico=(exp.EstadoCertificado(
        codigo=17, titulo="Entregado",
        fecha=datetime.fromisoformat("2026-06-17T10:00:00+02:00")),))
    e = exp.Expedicion(id_personalizado="W-04AKM2 - OVC", entorno="produccion",
                       envios=(estancado,), leida_en=LEIDA)
    texto = cli.render_cosecha([], e)
    assert exp.QUE_SIGNIFICA[exp.ESTANCADO] in texto and "· 006e" in texto
    assert exp.QUE_SIGNIFICA[exp.PUEDE_MEJORAR] not in texto
