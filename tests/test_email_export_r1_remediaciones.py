"""Remediaciones de la R1 de Codex sobre la acción 6a — un test por hallazgo.

Acta literal:
`docs/superpowers/specs/2026-09-06-accion-6a-filtro-ruido-r1-adversarial-review.md`
(veredicto `NO-SHIP`, 6 hallazgos, 6 confirmados, 0 refutados).
Adjudicación: §6 del plan `docs/superpowers/plans/2026-09-06-accion-6a-…md`.

**Viven aparte del fichero de la pieza a propósito:** cada uno nombra el hallazgo que lo
motivó, y si alguno vuelve a ponerse rojo se lee de inmediato QUÉ regresión es. Metidos
entre los otros treinta, esa procedencia se pierde en un mes.
"""
from __future__ import annotations

import pytest

from core import email_export as ee
from tests.test_email_export import (
    _ETIQUETA,
    _LABELS,
    _FakeService,
    _build_raw,
    _child,
    _envoltorio,
    _parte_rfc822,
    _setup_caso,
)

_CUENTA = "nikolai@engelvoelkers.com"


def _svc(raws: dict[str, bytes]) -> "_FakeService":
    return _FakeService(
        labels=_LABELS, pages=[{"messages": [{"id": g} for g in raws]}], raws=raws)


# ==========================================================================
# H-05 (MEDIO) — la señal de destinatario es una DIRECCIÓN, no una subcadena
# ==========================================================================

def test_H05_el_buzon_en_el_NOMBRE_MOSTRADO_no_excluye():
    """El destinatario real es el `addr-spec`, no lo que diga el display name.

    Escribí en el código que este falso positivo «no era realista» — una afirmación
    sin medir, y el revisor construyó uno en una línea. Una cabecera válida basta.
    """
    regla = ee.clasificar_ruido({
        "subject": "Oferta del inmueble",
        "to": '"proveedores.es@engelvoelkers.com" <abogado@ejemplo.test>',
    })
    assert regla is None


def test_H05_la_direccion_REAL_sigue_excluyendo():
    """La otra dirección de la frontera: estrechar no puede cegar la regla."""
    assert ee.clasificar_ruido({
        "subject": "Factura", "to": "Proveedores ES <Proveedores.ES@engelvoelkers.com>",
    }) == "facturacion_despacho"


def test_H05_apellido_coma_nombre_no_rompe_el_parseo():
    """El gotcha conocido de `parseaddr` con «Apellido, Nombre <addr>»: la coma parece
    un separador de lista. Con el buzón presente en la lista, la regla debe seguir
    cazándolo."""
    assert ee.clasificar_ruido({
        "subject": "Factura",
        "to": '"Tyukhay, Nikolai" <n@t.legal>, Proveedores.ES@engelvoelkers.com',
    }) == "facturacion_despacho"


# ==========================================================================
# H-03 (ALTO) — las regex excluían asuntos probatorios
# ==========================================================================

@pytest.mark.parametrize("asunto", [
    # Los dos que el revisor EJECUTÓ y que se excluían.
    "W-ABC123 · Acta notarial aportada por el CFO del propietario",
    "W-ABC123 · Carta de auditoria tecnica del inmueble",
    # De la misma familia: documentación del caso que roza el vocabulario.
    "Carta de auditoría energética del edificio",
    "Acta de la junta de propietarios con el CFO de la promotora",
])
def test_H03_asuntos_PROBATORIOS_que_se_excluian_ya_no(asunto):
    """`\\bacta\\b.*\\bcfo\\b` casaba a cualquier distancia, y `auditor` es prefijo de
    `auditoria`. El falso positivo aquí OMITE PRUEBA, que es el error caro."""
    assert ee.clasificar_ruido({"subject": asunto, "to": "despacho@tyukhay.legal"}) is None


@pytest.mark.parametrize("asunto,esperada", [
    ("Acta reunión CFO + Legal", "gobernanza_interna"),
    ("Acta reunion CFO+Legal 12 de junio", "gobernanza_interna"),
    ("RV: Acta CFO y Legal de julio", "gobernanza_interna"),
    ("Circularización de auditoría 2026", "auditoria"),
    ("Carta a los auditores", "auditoria"),
    ("Carta de auditores Deloitte", "auditoria"),
])
def test_H03_lo_que_SI_es_administrativo_sigue_excluyendose(asunto, esperada):
    assert ee.clasificar_ruido({"subject": asunto, "to": "x@y.z"}) == esperada


# ==========================================================================
# H-02 (ALTO) — el guard aceptaba destinos con rutas de manifiesto falsas
# ==========================================================================

def test_H02_un_lote_ANIDADO_bajo_00_Input_no_se_traza(tmp_casos_root):
    """`_emit_traza` usa `dest.parent` como raíz de las rutas relativas. Un `dest` a
    dos niveles pasaba el guard «bajo 00_Input» y registraba
    `2026-09-06_email_01/x.eml`, omitiendo `subcarpeta/` — una ruta que no existe.

    La frontera real no es «descendiente de `00_Input`» sino **hijo directo**: es la
    topología que el escritor sabe trazar. Remediar el ejemplo (el destino externo) y
    no la frontera es el modo de fallo que esta casa ya tiene medido seis veces.
    """
    from core import config
    from core.intake_manifest import IntakeManifest

    case_id = _setup_caso("EMAIL-H02-001")
    hondo = config.caso_path(case_id) / "00_Input" / "subcarpeta" / "2026-09-06_email_01"
    hondo.mkdir(parents=True)
    raws = {"g1": _build_raw(message_id="<h2@x>", subject="Oferta del inmueble")}

    rep = ee.export_label(_CUENTA, _ETIQUETA, hondo, service=_svc(raws), case_id=case_id)

    assert rep.written == 1
    with IntakeManifest(case_id) as m:
        assert m.all_paths() == set()
    assert not rep.intake_logged
    assert rep.errors and "00_Input" in " ".join(rep.errors)


# ==========================================================================
# H-04 (MEDIO) — el evento se dirigía a otra raíz si `00_Input` es un alias
# ==========================================================================

def test_H04_el_evento_llega_al_caso_aunque_la_raiz_se_resuelva_a_otro_sitio(
        tmp_casos_root, monkeypatch):
    """`_input_root_de` resolvía físicamente y el emisor tomaba su `.parent`. Con un
    `00_Input` que resuelve a otra carpeta, ese `.parent` no es el caso: el evento
    moría con `LocalWorkspaceMissing` y se perdía el único rastro durable —
    precisamente cuando TODO se excluyó y no queda nada más que mirar.

    La raíz LÓGICA del caso (para escribir el log) y la FÍSICA (para comparar
    pertenencia) son dos cosas y no pueden salir de la misma variable.
    """
    from core import config, intake_log

    case_id = _setup_caso("EMAIL-H04-001")
    caso = config.caso_path(case_id)
    dest = caso / "00_Input" / "2026-09-06_email_01"
    dest.mkdir(parents=True)

    fisica = tmp_casos_root / "physical_input"
    fisica.mkdir(parents=True, exist_ok=True)
    real = ee._input_root_de

    def _resuelve_a_otro_sitio(cid):
        return fisica if cid == case_id else real(cid)

    monkeypatch.setattr(ee, "_input_root_de", _resuelve_a_otro_sitio)

    raws = {"g-ruido": _build_raw(
        message_id="<h4@x>", subject="Factura agosto",
        to_addr="Proveedores.ES@engelvoelkers.com")}
    rep = ee.export_label(_CUENTA, _ETIQUETA, dest, service=_svc(raws), case_id=case_id)

    assert len(rep.excluidos_ruido) == 1
    eventos = [e for e in intake_log.read_events(case_id)
               if e.get("event") == "email_excluido_ruido"]
    assert len(eventos) == 1, "el rastro durable no puede depender de dónde resuelva la raíz"


# ==========================================================================
# H-01 (ALTO) — la exclusión se rodeaba por los depósitos alternativos
# ==========================================================================

def _con_hijo_ruidoso() -> dict[str, bytes]:
    """Un correo legítimo del caso que REENVÍA una circularización de auditoría.

    MIME crudo a mano, como el resto de los tests de anidados: `add_attachment` con
    `message/rfc822` NO produce un anidado que `iter_nested_originals` reconozca, y la
    primera versión de este fixture pasaba el test por el camino equivocado —el hijo
    "no se extraía" porque nunca se detectó, no porque el filtro lo parara.
    """
    hijo = _child(
        mid=b"<hijo-ruido@x>",
        subject="Circularizacion de auditoria 2026".encode(),
        date=b"Mon, 08 Jun 2026 11:00:00 +0200")
    return {"g-padre": _envoltorio(b"BTOP", [_parte_rfc822(hijo)])}


def test_H01_el_hijo_anidado_de_ruido_NO_se_extrae_como_fichero(tmp_path):
    """El aplanado depositaba el hijo sin pasar por el filtro. Extraerlo lo hace MÁS
    accesible que dejarlo dentro del padre: fichero propio, indexado y en la
    cronología. Ahí el filtro sí decide."""
    rep = ee.export_label(_CUENTA, _ETIQUETA, tmp_path, service=_svc(_con_hijo_ruidoso()))

    nombres = " ".join(rep.files).lower()
    assert "circulariz" not in nombres and "auditor" not in nombres
    assert not list(tmp_path.rglob("*circulariz*"))
    assert not list(tmp_path.rglob("cartera_litigios.pdf"))


def test_H01_el_padre_entra_INTEGRO_y_se_avisa(tmp_path):
    """Decisión de Nikolai (2026-09-06): el `.eml` del padre se deposita tal cual —es
    correspondencia real del caso y su FIDELIDAD es lo que lo hace prueba— pero el
    report declara que transporta material administrativo.

    Mutilar un `.eml` para purgarlo lo invalida como prueba; avisar no.
    """
    rep = ee.export_label(_CUENTA, _ETIQUETA, tmp_path, service=_svc(_con_hijo_ruidoso()))

    assert rep.written == 1, "el padre SÍ entra"
    assert rep.ruido_transportado, "y su carga se declara"
    aviso = rep.ruido_transportado[0]
    assert aviso["regla"] == "auditoria"
    assert aviso["dentro_de"] == "RV bloque"


def test_H01_transportado_y_excluido_son_LISTAS_DISTINTAS(tmp_path):
    """Lo que no se depositó y lo que viaja dentro de un padre no pueden ir en la
    misma lista: el evento diría «excluí la circularización» con sus bytes en el
    expediente, que es justo lo que el revisor llama engañoso."""
    rep = ee.export_label(_CUENTA, _ETIQUETA, tmp_path, service=_svc(_con_hijo_ruidoso()))
    assert rep.excluidos_ruido == []
    assert len(rep.ruido_transportado) == 1
    assert "transporta" in rep.resumen()


def test_H01_un_mensaje_rescatado_por_ENLACE_pasa_por_el_filtro(tmp_path, monkeypatch):
    """`_deposita_mensaje_rescatado` escribía sin clasificar, así que un permalink de
    Gmail al mensaje ya excluido lo devolvía al expediente por la puerta de atrás.
    Es el MISMO mensaje entrando por otro sitio."""
    ruidoso = _build_raw(
        message_id="<rescatado@x>", subject="Circularización de auditoría 2026")
    rep = ee.ExportReport(account=_CUENTA, label=_ETIQUETA)
    vistos: set[str] = set()

    ruta = ee._deposita_mensaje_rescatado(tmp_path, ruidoso, vistos, {}, rep)

    assert ruta is None, "no se deposita"
    assert not list(tmp_path.rglob("*.eml"))
    assert [e["regla"] for e in rep.excluidos_ruido] == ["auditoria"]
    assert vistos == set(), "ni entra en la dedup"


def test_H01_un_mensaje_rescatado_LEGITIMO_se_sigue_depositando(tmp_path):
    """La otra dirección: el rescate de enlaces es una función que existe para
    recuperar prueba, y el filtro no puede desactivarla."""
    bueno = _build_raw(message_id="<bueno@x>", subject="Oferta del inmueble")
    rep = ee.ExportReport(account=_CUENTA, label=_ETIQUETA)

    ruta = ee._deposita_mensaje_rescatado(tmp_path, bueno, set(), {}, rep)

    assert ruta is not None
    assert rep.excluidos_ruido == []
