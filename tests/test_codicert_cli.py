"""El frontal: lo que el humano lee antes de gastar, y la precedencia del entorno."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal
from pathlib import Path

import pytest

from core import case_manager
from core import expedicion_certificada as exp
from core import sudespacho_relations
from core.casos import case_locator
from core.sudespacho_relations import SudespachoRelationsError
from scripts import codicert as cli


def _pdf_bytes() -> bytes:
    """PDF real, abrible por `pypdf` -- no una cabecera falsa (hallazgo H-09,
    revisión adversarial r2): desde ese hallazgo, `planificar` valida que cada
    documento sea un PDF de verdad, así que un doble de este fichero necesita uno
    real para seguir probando lo que dice probar (mutex, credenciales, errores del
    CRM), no el preflight de formato."""
    import io as _io
    from pypdf import PdfWriter
    w = PdfWriter()
    w.add_blank_page(width=595, height=842)
    buf = _io.BytesIO()
    w.write(buf)
    return buf.getvalue()


# H-06: campos separados, como los devuelve `clientes_contrarios` de verdad (docs/
# CRM_SUDESPACHO_ATLAS.md § clientes_contrarios).
_ANA = {"nombre": "ANA", "1apellido": "LOPEZ", "2apellido": "", "direccion": "C Mayor 1",
        "poblacion": "Madrid", "provincia": "Madrid", "cp": "28001", "email": "ana@x.es",
        "movil": "665130883"}


def _plan(tmp_path):
    envios = [exp.EnvioPrevisto("burofax", {"nombre": "ANA LOPEZ Y LUIS PEREZ"},
                                "ANA LOPEZ Y LUIS PEREZ · C Mayor 1, Madrid  "
                                "⚠ sobre conjunto: acredita entrega EN EL DOMICILIO, no a cada uno"),
              exp.EnvioPrevisto("correo", {"correo": "ana@x.es"}, "ANA LOPEZ · ana@x.es")]
    return exp.Plan(w_code="W-04AKM2", tipo="OVC", id_personalizado="W-04AKM2 - OVC",
                    plaza="Madrid", entorno="sandbox", envios=envios,
                    ausencias=["LUIS PEREZ: sin canal SMS (el CRM no tiene un móvil español)"],
                    coste=Decimal("17.7647"), credito=Decimal("398.1388"),
                    documentos=[tmp_path / "A.pdf"], documentos_sha256=["abc"],
                    asunto="Comunicación certificada · expediente W-04AKM2",
                    cuerpo="<p>…</p>", digest="d1")


def test_el_plan_enseña_entorno_emisor_coste_y_credito(tmp_path):
    texto = cli.render_plan(_plan(tmp_path))
    for esperado in ("SANDBOX", "W-04AKM2 - OVC", "17.7647", "398.1388", "Madrid"):
        assert esperado in texto


def test_el_plan_enseña_las_ausencias_y_el_aviso_del_sobre_conjunto(tmp_path):
    texto = cli.render_plan(_plan(tmp_path))
    assert "sin canal SMS" in texto
    assert "no a cada uno" in texto


def test_el_plan_enseña_el_digest_que_habra_que_confirmar(tmp_path):
    assert "d1" in cli.render_plan(_plan(tmp_path))


def test_el_plan_enseña_el_texto_que_leera_el_requerido(tmp_path):
    texto = cli.render_plan(_plan(tmp_path))
    assert "Comunicación certificada · expediente W-04AKM2" in texto


def test_produccion_exige_la_orden_aunque_la_variable_lo_diga(monkeypatch):
    monkeypatch.setenv("CODICERT_ENTORNO", "produccion")
    assert cli.entorno_de(argumento=None) == "sandbox"
    assert cli.entorno_de(argumento="produccion") == "produccion"


def test_un_entorno_inventado_se_rechaza():
    import pytest
    with pytest.raises(SystemExit):
        cli.entorno_de(argumento="preproduccion")


# ---------------------------------------------------------------------------------
# Hallazgo 1 (CRÍTICO). `partes_de` recibe el W-code a secas -- lo que su propio
# `--help` documenta -- pero llamaba a `case_manager.get_case_status(w_code)`, que
# busca la carpeta por NOMBRE EXACTO. Las carpetas reales se llaman por su nombre
# canónico completo ("BaRS11 - Falsa 1 (W-000AAA) - Vuelta"), nunca por el W-code
# solo: toda invocación real fallaba, incluso con un caso perfectamente indexado y
# su expediente extrajudicial registrado. Repro con árbol sintético en `tmp_path`
# (nunca Drive ni CRM reales): monkeypatch de `case_locator._root`, exactamente el
# patrón ya probado en `tests/test_crm_ficha_cli.py::caso_con_ficha`.
# ---------------------------------------------------------------------------------

def _caso_sintetico(tmp_path, monkeypatch, *, case_id, w_code, direccion, exp_id=None):
    """Un caso real (mismo mecanismo que usa `case_manager.ensure_case` en
    producción) bajo un CASOS_ROOT sintético en `tmp_path`. Con `exp_id`, registra
    además el expediente `extrajudiciales`. Nunca toca el catálogo real."""
    root = tmp_path / "CASOS"
    root.mkdir(exist_ok=True)
    monkeypatch.setattr(case_locator, "_root", lambda: root)
    case_manager.ensure_case(
        case_id, titulo=case_id, referencia_crm=case_id,
        tipo_caso="VUELTA", ciudad="Barcelona", direccion=direccion, id_go=w_code,
    )
    if exp_id is not None:
        case_manager.register_expediente(case_id, exp_id, "extrajudiciales")
    return root


def test_partes_de_resuelve_el_w_code_desnudo_a_su_caso_real(tmp_path, monkeypatch):
    """El arreglo resuelve primero con `case_locator.resolve_ref`, igual que
    `scripts/crm_ficha.py::main` -- antes de preguntarle nada a `get_case_status`."""
    _caso_sintetico(tmp_path, monkeypatch,
                    case_id="BaRS11 - Falsa 1 (W-000AAA) - Vuelta",
                    w_code="W-000AAA", direccion="Falsa 1", exp_id="606")

    # H-06: campos separados, como los devuelve `clientes_contrarios` de verdad (docs/
    # CRM_SUDESPACHO_ATLAS.md); este test compara paso-a-través (partes_de == esperado),
    # no la composición del nombre, pero la fixture debe reflejar la forma real.
    esperado = [{"nombre": "JUAN", "1apellido": "PEREZ", "2apellido": "",
                "direccion": "C Mayor 1", "poblacion": "Madrid",
                "provincia": "Madrid", "cp": "28001", "email": "juan@x.es",
                "movil": "600111222"}]
    monkeypatch.setattr(
        sudespacho_relations, "get_relaciones",
        lambda element, exp_id: {"clientes_contrarios": esperado}
        if (element, exp_id) == ("extrajudiciales", "606") else {})

    assert exp.partes_de("W-000AAA") == esperado


def test_partes_de_caso_no_indexado_lo_distingue_de_falta_de_expediente(tmp_path, monkeypatch):
    """Hallazgo 3, causa 1: el caso no está en el catálogo local. Remedio distinto
    del de la causa 2 (más abajo) -- aquí no hay ni carpeta que abrir -- así que el
    mensaje no puede ser el mismo, ni mencionar 'extrajudiciales'."""
    root = tmp_path / "CASOS"
    root.mkdir()
    monkeypatch.setattr(case_locator, "_root", lambda: root)

    with pytest.raises(exp.ExpedicionError) as excinfo:
        exp.partes_de("W-999ZZZ")
    mensaje = str(excinfo.value).lower()
    assert "no está indexado" in mensaje or "catálogo local" in mensaje
    assert "extrajudiciales" not in mensaje


def test_partes_de_caso_indexado_sin_expediente_sugiere_el_remedio(tmp_path, monkeypatch):
    """Hallazgo 3, causa 2: el caso SÍ está indexado pero no tiene expediente
    'extrajudiciales' registrado. `scripts/crm_ficha.py::main` sugiere el comando
    para darlo de alta; este mensaje hace lo mismo."""
    _caso_sintetico(tmp_path, monkeypatch,
                    case_id="BaRS11 - Falsa 2 (W-000BBB) - Vuelta",
                    w_code="W-000BBB", direccion="Falsa 2")  # sin exp_id: sin expediente

    with pytest.raises(exp.ExpedicionError) as excinfo:
        exp.partes_de("W-000BBB")
    mensaje = str(excinfo.value)
    assert "extrajudiciales" in mensaje
    assert "crm_ficha" in mensaje


# ---------------------------------------------------------------------------------
# Hallazgo 4. `entorno_real` -- con `_Transporte` y `partes_de` -- es lógica de
# dominio (cómo resolver un expediente del CRM desde un W-code y qué hacer si
# falta) y vive en `core/expedicion_certificada.py`; el CLI solo lo importa y lo
# llama.
# ---------------------------------------------------------------------------------

def test_entorno_real_y_partes_de_viven_en_core_no_en_el_script():
    assert hasattr(exp, "entorno_real")
    assert hasattr(exp, "partes_de")
    assert not hasattr(cli, "entorno_real")


# ---------------------------------------------------------------------------------
# Hallazgo 2. Un fallo del CRM (`SudespachoRelationsError`, o `ValueError` si falta
# la API key) tiene que salir como mensaje legible -- el operador es un abogado --
# no como traza de Python cruda. Los dos tests doblan `_cod.credenciales` (que si
# no, leería `.env`/el registro de Windows de verdad: no hermético) y `entorno_real`
# entero (los tests nunca lo construyen de verdad), para que la única variable sea
# el tipo de excepción que revienta dentro de `partes_de`.
# ---------------------------------------------------------------------------------

class _CodTransporteFalso:
    """Doble mínimo del transporte. `credito()` es lo único que se llega a invocar
    en los tests de este bloque, y solo en el que no revienta antes."""

    def credito(self):
        return Decimal("100")


def _entorno_falso_que_revienta(excepcion, *, raiz):
    def _fabrica(*, plaza, entorno):
        def _partes_de(_w):
            raise excepcion
        return exp.EntornoExpedicion(
            codicert=_CodTransporteFalso(), partes_de=_partes_de,
            ahora=lambda: dt.datetime(2026, 9, 17, 12, 0, tzinfo=dt.timezone.utc),
            raiz=raiz, plaza=plaza, entorno=entorno, usuario="BD-PRUEBA")
    return _fabrica


def _cli_main_hermetico(monkeypatch, *, entorno_real_falso, argv):
    """Corre `cli.main(argv)` sin tocar red ni construir el `entorno_real` real."""
    monkeypatch.setattr(cli._cod, "credenciales", lambda *a, **kw: ("BD-FALSO", "clave"))
    monkeypatch.setattr(cli.exp, "entorno_real", entorno_real_falso)
    return cli.main(argv)


def test_un_fallo_de_relaciones_del_crm_sale_legible(tmp_path, monkeypatch, capsys):
    doc = tmp_path / "A.pdf"
    doc.write_bytes(_pdf_bytes())
    codigo = _cli_main_hermetico(
        monkeypatch,
        entorno_real_falso=_entorno_falso_que_revienta(
            SudespachoRelationsError("502 Bad Gateway leyendo relaciones"), raiz=tmp_path),
        argv=["plan", "W-04AKM2", "--tipo", "OVC", "--plaza", "Madrid", "--doc", str(doc)])
    assert codigo == 1
    err = capsys.readouterr().err
    assert "ERROR" in err
    assert "502 Bad Gateway" in err


def test_un_fallo_de_api_key_ausente_sale_legible(tmp_path, monkeypatch, capsys):
    doc = tmp_path / "A.pdf"
    doc.write_bytes(_pdf_bytes())
    codigo = _cli_main_hermetico(
        monkeypatch,
        entorno_real_falso=_entorno_falso_que_revienta(
            ValueError("SUDESPACHO_API_KEY vacío en .env"), raiz=tmp_path),
        argv=["plan", "W-04AKM2", "--tipo", "OVC", "--plaza", "Madrid", "--doc", str(doc)])
    assert codigo == 1
    err = capsys.readouterr().err
    assert "ERROR" in err
    assert "SUDESPACHO_API_KEY" in err


# ---------------------------------------------------------------------------------
# Hallazgo 5 (menor). `entorno_real` expone el usuario ya resuelto; `main()` no
# debe volver a llamar `credenciales(...)` con los mismos argumentos solo para
# tener qué enseñar en la cabecera del plan.
# ---------------------------------------------------------------------------------

def test_main_no_vuelve_a_resolver_credenciales_usa_el_usuario_de_entorno_real(
        tmp_path, monkeypatch, capsys):
    llamadas = []
    monkeypatch.setattr(
        cli._cod, "credenciales",
        lambda *a, **kw: llamadas.append((a, kw)) or ("BD-FALSO", "clave"))

    def _entorno_real_falso(*, plaza, entorno):
        return exp.EntornoExpedicion(
            # H-16: `planificar` rechaza una expedición sin requeridos -- este
            # test no es sobre destinatarios, así que necesita al menos uno real
            # para seguir probando lo que dice probar (credenciales).
            codicert=_CodTransporteFalso(), partes_de=lambda _w: [_ANA],
            ahora=lambda: dt.datetime(2026, 9, 17, 12, 0, tzinfo=dt.timezone.utc),
            raiz=tmp_path, plaza=plaza, entorno=entorno, usuario="BD-YA-RESUELTO")
    monkeypatch.setattr(cli.exp, "entorno_real", _entorno_real_falso)

    doc = tmp_path / "A.pdf"
    doc.write_bytes(_pdf_bytes())
    codigo = cli.main(["plan", "W-04AKM2", "--tipo", "OVC", "--plaza", "Madrid",
                       "--doc", str(doc)])

    assert codigo == 0
    assert llamadas == []
    assert "BD-YA-RESUELTO" in capsys.readouterr().out


# ---------------------------------------------------------------------------------
# H-05 (alto, estructural; revisión adversarial r2). `enviar` tiene que sostener el
# mutex de la expedición ANTES de llamar a `exp.ejecutar` -- si no, dos terminales
# pueden admitir y ejecutar la MISMA expedición a la vez y duplicar el envío. La
# mitad de esa exclusión que vive en `core/` (exigirla, nunca adquirirla) la prueba
# `tests/test_expedicion_ejecutar.py`; esta prueba la otra mitad, la que vive aquí:
# que `main()` la ADQUIERE antes de ejecutar, y que si otro proceso de esta máquina
# ya la sostiene, aborta limpio sin llegar a mandar nada.
# ---------------------------------------------------------------------------------

def test_enviar_con_el_mutex_ya_ocupado_aborta_sin_llegar_a_ejecutar(
        tmp_path, monkeypatch, capsys):
    """Simula OTRO proceso sosteniendo el lock de esta misma expedición con la
    primitiva de verdad (`case_mutex.tomado`, no `mutex_sesion`: esta última es
    reentrante DENTRO de un proceso -- se uniría a la sesión en vez de chocar con
    ella -- así que hace falta la primitiva cruda para reproducir fielmente "otro
    proceso ya lo tiene". Los tests, a diferencia de `core/`/`scripts/`, no están
    vetados de llamarla directamente -- el guard de
    `tests/test_escritura_censo.py::test_produccion_no_llama_a_la_primitiva_en_crudo`
    solo vigila producción).

    `enviar` tiene que abortar con código 2 -- el mismo que usan los demás
    entrypoints ocupados -- SIN alcanzar `exp.ejecutar`: el doble de transporte
    revienta con `AssertionError` si se le llega a invocar `listar`/`enviar_*`.
    """
    from core.casos import case_mutex
    from core.utils import now_iso_utc

    class _CodTransporteQueRevienta(_CodTransporteFalso):
        def listar(self, **kw):
            raise AssertionError("no debía alcanzar listar(): el mutex estaba ocupado")

        def enviar_burofax(self, **kw):
            raise AssertionError("no debía alcanzar enviar_burofax(): el mutex estaba ocupado")

        def enviar_eec(self, **kw):
            raise AssertionError("no debía alcanzar enviar_eec(): el mutex estaba ocupado")

    def _entorno_real_falso(*, plaza, entorno):
        return exp.EntornoExpedicion(
            # H-16: `planificar` rechaza una expedición sin requeridos -- este
            # test es sobre el mutex ocupado, así que necesita al menos un
            # requerido real para llegar a construir el plan.
            codicert=_CodTransporteQueRevienta(), partes_de=lambda _w: [_ANA],
            ahora=lambda: dt.datetime(2026, 9, 17, 12, 0, tzinfo=dt.timezone.utc),
            raiz=tmp_path, plaza=plaza, entorno=entorno, usuario="BD-OCUPADO")

    monkeypatch.setattr(cli._cod, "credenciales", lambda *a, **kw: ("BD-FALSO", "clave"))
    monkeypatch.setattr(cli.exp, "entorno_real", _entorno_real_falso)

    doc = tmp_path / "A.pdf"
    doc.write_bytes(_pdf_bytes())
    plan = exp.planificar("W-04AKM2", "OVC", [doc],
                          entorno_exp=_entorno_real_falso(plaza="Madrid", entorno="sandbox"),
                          plaza="Madrid")
    clave = exp.clave_mutex_expedicion(plan)

    with case_mutex.tomado(clave, ahora_fn=now_iso_utc):
        codigo = cli.main(["enviar", "W-04AKM2", "--tipo", "OVC", "--plaza", "Madrid",
                           "--doc", str(doc), "--confirmar", "lo-que-sea"])

    assert codigo == 2
    err = capsys.readouterr().err
    assert "ERROR" in err


# ---------------------------------------------------------------------------------
# H-16 (medio, acotado; revisión adversarial r2). Se rechazaba un requerido SIN
# canales, pero no la AUSENCIA de requeridos: `get_relaciones` puede devolver
# legítimamente ninguna relación (un expediente extrajudicial sin contrarios
# vinculados en el CRM), `partes_de` lo convierte en `[]`, y coste cero más cero
# envíos se aceptaban como un plan ejecutable. Reproducido: `enviar` no mandaba
# nada, devolvía código 0 e imprimía "ENVIADO: " vacío -- no es la detección de una
# expedición ya completa (no hay ningún envío previo ni ningún destinatario).
# ---------------------------------------------------------------------------------

def test_H16_enviar_sin_ningun_requerido_no_imprime_ENVIADO_y_falla(
        tmp_path, monkeypatch, capsys):
    """`partes_de` reproduce exactamente lo que devuelve `get_relaciones` para un
    expediente sin contrarios vinculados: una lista vacía, sin ninguna excepción --
    el mismo dato de entrada que `test_H16_ningun_requerido_en_absoluto_detiene_el_
    plan` (tests/test_expedicion_plan.py) prueba a nivel de `destinatarios_de`. Este
    test prueba el frontal entero: ni éxito, ni "ENVIADO", ni ningún envío real."""

    class _CodTransporteQueRevienta(_CodTransporteFalso):
        """Si `enviar`/`listar` se llegaran a invocar, el defecto seguiría vivo:
        un plan sin destinatarios no debe llegar ni siquiera a consultarlos."""

        def listar(self, **kw):
            raise AssertionError("no debía alcanzar listar(): no hay destinatarios")

        def enviar_burofax(self, **kw):
            raise AssertionError("no debía alcanzar enviar_burofax(): no hay destinatarios")

        def enviar_eec(self, **kw):
            raise AssertionError("no debía alcanzar enviar_eec(): no hay destinatarios")

    def _entorno_real_falso(*, plaza, entorno):
        return exp.EntornoExpedicion(
            codicert=_CodTransporteQueRevienta(), partes_de=lambda _w: [],
            ahora=lambda: dt.datetime(2026, 9, 17, 12, 0, tzinfo=dt.timezone.utc),
            raiz=tmp_path, plaza=plaza, entorno=entorno, usuario="BD-SIN-CONTRARIOS")

    monkeypatch.setattr(cli._cod, "credenciales", lambda *a, **kw: ("BD-FALSO", "clave"))
    monkeypatch.setattr(cli.exp, "entorno_real", _entorno_real_falso)

    doc = tmp_path / "A.pdf"
    doc.write_bytes(_pdf_bytes())
    codigo = cli.main(["enviar", "W-04AKM2", "--tipo", "OVC", "--plaza", "Madrid",
                       "--doc", str(doc), "--confirmar", "lo-que-sea"])

    assert codigo == 1  # nunca 0: el defecto imprimía "ENVIADO: " vacío con código 0
    salida = capsys.readouterr()
    assert "ENVIADO" not in salida.out
    err = salida.err.lower()
    assert "error" in err
    assert "requerido" in err or "contrario" in err
