"""`crm_ficha` de punta a punta, con `ensure_*`, los resolutores y el completado REALES.

Un doble que sustituye `ensure_*` no ve un PUT que ocurre DENTRO de `ensure_*` (R2/H-01: el
revisor midió con el completado real que salía un PUT del email sobre una ficha cuyo apellido
el YAML contradecía). Por eso las garantías de «cero writers» se prueban aquí, con `CRMFalso`:
un CRM en memoria y con estado que sustituye solo el TRANSPORTE —las funciones de
`core.sudespacho_relations` que hablan HTTP— y deja correr de verdad `ensure_*`,
`resolver_*_existente`, `resolver_parte`, `_exigir_identidad_cierta` y `_completar_*` (spec
rev. 3 §6; plan rev. 2, Task 8).
"""
from __future__ import annotations

from collections import Counter

import pytest
from typer.testing import CliRunner

from core import case_manager
from core import sudespacho_relations as sr
from core.casos import case_locator
from scripts import crm_ficha as cli


class FugaDeRedEnTest(BaseException):
    """No hereda de Exception: ningún `except Exception` del CLI puede tragársela."""


@pytest.fixture(autouse=True)
def _sin_red(monkeypatch):
    def _prohibido(metodo):
        def _f(*a, **k):
            raise FugaDeRedEnTest(f"httpx.{metodo} salió a la red en un test")
        return _f
    for metodo in ("get", "post", "put", "delete", "patch", "request"):
        monkeypatch.setattr(f"httpx.{metodo}", _prohibido(metodo))


class _ClienteInerte:
    """El cliente legacy: `link_ev_mmc` y `ensure_colaborador_vinculado` lo construyen siempre,
    y solo se usa si la vía REST cae. Aquí no tiene vía que ofrecer."""

    def get_csrf_token(self):
        raise sr.SudespachoRelationsError("sin legacy en el test")

    def __exit__(self, *a):
        return None


class CRMFalso:
    """El CRM entero, en memoria: fichas por elemento, los vínculos del expediente, las Notas, y
    un registro de cada ESCRITURA (intento incluido), de cada BÚSQUEDA y de cada LECTURA."""

    def __init__(self, fichas=None, vinculos=None):
        self.fichas = {"clientes_contrarios": {}, "colaboradores": {}}
        for elemento, porid in (fichas or {}).items():
            self.fichas[elemento].update({k: dict(v) for k, v in porid.items()})
        self.vinculos = {"clientes_propios": [], "clientes_contrarios": [], "colaboradores": []}
        for bloque, ids in (vinculos or {}).items():
            self.vinculos[bloque].extend(ids)
        self.notas = ""
        self.escrituras: list[tuple] = []
        self.busquedas: list[tuple] = []
        self.lecturas: list[tuple] = []
        #: {(operación, id): {nº de llamada, …}} que fallan. Para una ficha existente, la 1.ª
        #: lectura es la de la fase previa, la 2.ª la del completado y la 3.ª la final.
        self.fallos: dict[tuple, set[int]] = {}
        #: Writers que fallan siempre: "crear_contrario", "notas", o "vincular:<bloque>".
        self.writers_caidos: set[str] = set()
        #: Propiedades que el CRM «pierde» al crear: un POST que no guardó un dato.
        self.pierde_al_crear: set[str] = set()
        self._cuenta: Counter = Counter()
        self._siguiente = 5000

    # --- utilidades -------------------------------------------------------------------------
    def _falla(self, operacion: str, id_: str) -> bool:
        self._cuenta[(operacion, id_)] += 1
        return self._cuenta[(operacion, id_)] in self.fallos.get((operacion, id_), set())

    def _nuevo_id(self) -> str:
        self._siguiente += 1
        return str(self._siguiente - 1)

    def creados(self) -> list[tuple]:
        return [e for e in self.escrituras if e[0].startswith("crear")]

    # --- lecturas ---------------------------------------------------------------------------
    def buscar_registros(self, elemento, propiedad, valor, *, operador="equal", limite=5,
                         properties=()):
        self.busquedas.append((elemento, propiedad, valor))
        norma = sr._canonizar_documento if propiedad == "nif_cif" else (
            lambda v: str(v or "").strip().lower())
        registros = [
            {"id": fid, "values": [{"property": {"name": p}, "value": ficha.get(p)}
                                   for p in (propiedad, *properties)]}
            for fid, ficha in self.fichas.get(elemento, {}).items()
            if ficha.get(propiedad) and norma(ficha.get(propiedad)) == norma(valor)
        ]
        return sr.Consulta(registros=registros)

    def find_colaborador_by_email(self, email, *, client=None):
        self.busquedas.append(("colaboradores", "email(listado)", email))
        for fid, ficha in self.fichas["colaboradores"].items():
            if str(ficha.get("email") or "").strip().lower() == str(email).strip().lower():
                return fid
        return None

    def _get(self, elemento, id_):
        self.lecturas.append((elemento, str(id_)))
        if self._falla(f"get:{elemento}", str(id_)):
            raise sr.SudespachoRelationsError(f"REST GET {elemento}/{id_} -> HTTP 500")
        if str(id_) not in self.fichas[elemento]:
            raise sr.SudespachoRelationsError(f"REST GET {elemento}/{id_} -> HTTP 404")
        return dict(self.fichas[elemento][str(id_)])

    def get_cliente_contrario(self, id_):
        return self._get("clientes_contrarios", id_)

    def get_colaborador(self, id_):
        return self._get("colaboradores", id_)

    def get_relaciones(self, element, exp_id):
        self.lecturas.append(("relaciones", str(exp_id)))
        return {b: [{"id": i} for i in ids] for b, ids in self.vinculos.items() if ids}

    def get_expediente(self, exp_id, properties=None):
        self.lecturas.append(("expediente", str(exp_id)))
        return {"Numero_Expediente": "1", "Notas": self.notas}

    # --- escrituras -------------------------------------------------------------------------
    def _update(self, elemento, id_, cambios):
        self.escrituras.append(("actualizar", elemento, str(id_), dict(cambios)))
        if self._falla(f"put:{elemento}", str(id_)):
            raise sr.SudespachoRelationsError(f"REST PUT {elemento}/{id_} -> HTTP 500")
        self.fichas[elemento][str(id_)].update(cambios)
        return dict(self.fichas[elemento][str(id_)])

    def update_cliente_contrario(self, id_, cambios):
        return self._update("clientes_contrarios", id_, cambios)

    def update_colaborador(self, id_, cambios):
        return self._update("colaboradores", id_, cambios)

    def create_cliente_contrario(self, datos):
        self.escrituras.append(("crear_contrario", datos.nombre))
        if "crear_contrario" in self.writers_caidos:
            raise sr.SudespachoRelationsError("REST POST clientes_contrarios -> HTTP 500")
        ficha = {"nombre": datos.nombre, "1apellido": datos.apellido1,
                 "2apellido": datos.apellido2, "email": datos.email, "movil": datos.movil,
                 "nif_cif": datos.nif, "direccion": datos.direccion,
                 "poblacion": datos.poblacion, "cp": datos.cp, "telefono1": datos.telefono,
                 "provincia": sr.provincia_canonica(datos.provincia) or ""}
        fid = self._nuevo_id()
        self.fichas["clientes_contrarios"][fid] = {k: v for k, v in ficha.items()
                                                  if v and k not in self.pierde_al_crear}
        return fid

    def create_colaborador(self, datos, *, client=None):
        self.escrituras.append(("crear_colaborador", datos.nombre))
        ficha = {"nombre": datos.nombre, "email": datos.email, "movil": datos.movil,
                 "telefono1": datos.telefono, "nif_cif": datos.nif}
        fid = self._nuevo_id()
        self.fichas["colaboradores"][fid] = {k: v for k, v in ficha.items()
                                            if v and k not in self.pierde_al_crear}
        return fid

    def link_rest(self, element, exp_id, relations):
        for rel in relations:
            _, bloque, id_ = rel.split(".", 2)
            self.escrituras.append(("vincular", bloque, id_))
            if f"vincular:{bloque}" in self.writers_caidos:
                raise sr.SudespachoRelationsError(f"REST POST relation_element {rel} -> 500")
            if id_ not in self.vinculos[bloque]:        # idempotente, como el real
                self.vinculos[bloque].append(id_)

    def update_expediente(self, exp_id, cambios):
        self.escrituras.append(("notas", str(exp_id)))
        if "notas" in self.writers_caidos:
            raise RuntimeError("PUT extrajudiciales -> HTTP 500")
        self.notas = cambios.get("Notas", self.notas)
        return {}

    # --- instalación ------------------------------------------------------------------------
    def instalar(self, monkeypatch):
        transporte = {"_buscar_registros": self.buscar_registros,
                      "find_colaborador_by_email": self.find_colaborador_by_email,
                      "get_cliente_contrario": self.get_cliente_contrario,
                      "get_colaborador": self.get_colaborador,
                      "update_cliente_contrario": self.update_cliente_contrario,
                      "update_colaborador": self.update_colaborador,
                      "create_cliente_contrario": self.create_cliente_contrario,
                      "create_colaborador": self.create_colaborador,
                      "_link_rest": self.link_rest,
                      "get_relaciones": self.get_relaciones,
                      "SudespachoLegacyClient": _ClienteInerte}
        for nombre, doble in transporte.items():
            monkeypatch.setattr(sr, nombre, doble)
        # Los nombres que el CLI importó: apuntan al objeto original, no al del módulo.
        for nombre, doble in (("get_cliente_contrario", self.get_cliente_contrario),
                              ("get_colaborador", self.get_colaborador),
                              ("get_relaciones", self.get_relaciones),
                              ("get_expediente", self.get_expediente),
                              ("update_expediente", self.update_expediente)):
            monkeypatch.setattr(cli, nombre, doble)
        return self


_YAML_BASE = ("contrario:\n  nombre: JUAN\n  apellido1: PEREZ\n  nif: 00000000T\n"
              "  movil: '+34 600 111 222'\n"
              "colaboradores:\n  - nombre: ANA\n    email: ana@engelvoelkers.example\n"
              "notas_html: '<p>Vuelta</p>'\n")
_ANA_776 = {"nombre": "ANA", "email": "ana@engelvoelkers.example", "movil": ""}


@pytest.fixture
def caso(tmp_path, monkeypatch):
    """CASOS_ROOT en tmp y un caso con el expediente extrajudicial 606. El YAML lo escribe cada
    test con `_yaml`."""
    root = tmp_path / "CASOS"
    root.mkdir()
    monkeypatch.setattr(case_locator, "_root", lambda: root)
    case_id = "BaRS11 - Falsa 1 (W-000AAA) - Vuelta"
    case_manager.ensure_case(case_id, titulo=case_id, referencia_crm=case_id, tipo_caso="VUELTA",
                             ciudad="Barcelona", direccion="Falsa 1", id_go="W-000AAA")
    case_manager.register_expediente(case_id, "606", "extrajudiciales")
    return case_id


def _yaml(caso, texto):
    (case_locator.path_for(caso) / "00_Input" / "_ficha_crm.yaml").write_text(
        texto, encoding="utf-8")


def _corre():
    return CliRunner().invoke(cli.app, ["--case-id", "W-000AAA", "--yes"])


# ---------------------------------------------------------------------------
# Convergencia y la vía por id
# ---------------------------------------------------------------------------

def test_convergencia_dos_corridas_no_crean_otra_ficha_ni_sobrantes(caso, monkeypatch):
    crm = CRMFalso(fichas={"colaboradores": {"776": _ANA_776}}).instalar(monkeypatch)
    _yaml(caso, _YAML_BASE)
    r1 = _corre()
    assert r1.exit_code == 0, r1.output
    assert cli.EXITO_VERIFICADA in r1.output
    vinculos_1 = {b: list(v) for b, v in crm.vinculos.items()}
    r2 = _corre()
    assert r2.exit_code == 0, r2.output
    assert cli.EXITO_VERIFICADA in r2.output
    assert len(crm.creados()) == 1, crm.creados()          # JUAN, una sola vez
    assert crm.vinculos == vinculos_1                      # la segunda no añade ni sobra nada


def test_un_colaborador_por_id_se_completa_y_vincula_sin_buscar(caso, monkeypatch):
    crm = CRMFalso(fichas={"colaboradores": {"776": {"nombre": "ANA", "movil": ""}}}).instalar(
        monkeypatch)
    _yaml(caso, "colaboradores:\n  - {nombre: ANA, id_crm: '776', movil: '600111222'}\n")
    r = _corre()
    assert r.exit_code == 0, r.output
    assert cli.EXITO_VERIFICADA in r.output
    assert crm.busquedas == []                              # con id_crm no se busca
    assert ("actualizar", "colaboradores", "776", {"movil": "600111222"}) in crm.escrituras
    assert ("vincular", "colaboradores", "776") in crm.escrituras


# ---------------------------------------------------------------------------
# La fase previa, con el completado real: CERO writers
# ---------------------------------------------------------------------------

def test_R2H01_dato_distinto_preexistente_cero_writers_con_el_completado_real(caso, monkeypatch):
    """El caso que midió el revisor: con el completado real, el email vacío de la ficha se
    rellenaba aunque su apellido contradijera al YAML. Ahora no sale NI ese PUT."""
    crm = CRMFalso(fichas={"clientes_contrarios": {"1128": {
        "nombre": "ANA", "1apellido": "OTRO", "nif_cif": "00000000T", "email": ""}}}).instalar(
        monkeypatch)
    _yaml(caso, "contrario: {nombre: ANA, apellido1: PEREZ, nif: 00000000T, email: ana@x.es}\n")
    r = _corre()
    assert r.exit_code == 1, r.output
    assert "1apellido: distinto" in r.output
    assert crm.escrituras == []


def test_por_id_contradicho_cero_writers_y_sin_buscar(caso, monkeypatch):
    crm = CRMFalso(fichas={"clientes_contrarios": {"1128": {
        "nombre": "JUAN", "1apellido": "LOPEZ", "nif_cif": "22222222J"}}}).instalar(monkeypatch)
    _yaml(caso, "contrario: {nombre: JUAN, apellido1: PEREZ, nif: '11111111H', id_crm: '1128'}\n")
    r = _corre()
    assert r.exit_code == 1, r.output
    assert crm.escrituras == [] and crm.busquedas == []


def test_la_segunda_parte_invalida_cero_writers_para_la_primera(caso, monkeypatch):
    crm = CRMFalso(fichas={"clientes_contrarios": {"1100": {
        "nombre": "MARIA", "1apellido": "GOMEZ", "nif_cif": "11111111H"}}}).instalar(monkeypatch)
    _yaml(caso, "contrario:\n  - {nombre: JUAN, apellido1: PEREZ, nif: 00000000T}\n"
                "  - {nombre: MARIA, apellido1: LOPEZ, nif: 11111111H}\n")
    r = _corre()
    assert r.exit_code == 1, r.output
    assert crm.escrituras == []


# ---------------------------------------------------------------------------
# La lectura final, por RESULTADO (spec §4 B.2)
# ---------------------------------------------------------------------------

_CON_CP = "contrario: {nombre: JUAN, apellido1: PEREZ, nif: 00000000T, cp: '08019'}\n"
_JUAN_SIN_CP = {"nombre": "JUAN", "1apellido": "PEREZ", "nif_cif": "00000000T", "cp": ""}


def test_un_GET_del_completado_fallido_sale_como_DATO(caso, monkeypatch):
    crm = CRMFalso(fichas={"clientes_contrarios": {"1128": _JUAN_SIN_CP}}).instalar(monkeypatch)
    crm.fallos[("get:clientes_contrarios", "1128")] = {2}      # la lectura del completado
    _yaml(caso, _CON_CP)
    r = _corre()
    assert r.exit_code == 1, r.output
    assert "[DATO] clientes_contrarios id=1128 cp: vacío en el CRM" in r.output


def test_un_PUT_del_completado_fallido_sale_como_DATO(caso, monkeypatch):
    crm = CRMFalso(fichas={"clientes_contrarios": {"1128": _JUAN_SIN_CP}}).instalar(monkeypatch)
    crm.fallos[("put:clientes_contrarios", "1128")] = {1}
    _yaml(caso, _CON_CP)
    r = _corre()
    assert r.exit_code == 1, r.output
    assert "[DATO] clientes_contrarios id=1128 cp: vacío en el CRM" in r.output


def test_una_parte_CREADA_a_la_que_el_CRM_no_guardo_un_dato_da_DATO(caso, monkeypatch):
    crm = CRMFalso().instalar(monkeypatch)
    crm.pierde_al_crear = {"2apellido"}
    _yaml(caso, "contrario: {nombre: JUAN, apellido1: PEREZ, apellido2: GOMEZ, nif: 00000000T}\n")
    r = _corre()
    assert r.exit_code == 1, r.output
    assert "[DATO] clientes_contrarios id=5000 2apellido: vacío en el CRM" in r.output


# ---------------------------------------------------------------------------
# Cada writer que falla: código 1, sin «VERIFICADA» y sin sobrantes emitidos (B.4)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("caido", ["vincular:clientes_propios", "crear_contrario",
                                   "vincular:clientes_contrarios", "vincular:colaboradores",
                                   "notas"])
def test_cada_writer_que_falla_da_1_sin_VERIFICADA_ni_sobrantes(caso, monkeypatch, caido):
    # Un colaborador AJENO ya vinculado de otra corrida: si la parcial emitiera sobrantes, se
    # vería aquí.
    crm = CRMFalso(fichas={"colaboradores": {"776": _ANA_776}},
                   vinculos={"colaboradores": ["999"]}).instalar(monkeypatch)
    crm.writers_caidos = {caido}
    _yaml(caso, _YAML_BASE)
    r = _corre()
    assert r.exit_code == 1, r.output
    assert cli.EXITO_VERIFICADA not in r.output
    assert "[SOBRA]" not in r.output


# ---------------------------------------------------------------------------
# Una entrada inválida no llega al CRM: ni escrituras, ni búsquedas, ni lecturas
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("texto", [
    "contrario: {nombre: UNO, nif: '1'}\ncontrario: {nombre: DOS, nif: '2'}\n",   # repetida
    "a: &x {nombre: A, nif: '1'}\ncontrario: *x\n",                              # alias
    "contrario: {<<: {nombre: A, nif: '1'}}\n",                                  # merge
    "contrario: {nombre: A, nif: '1', apellido: X}\n",                           # desconocida
    "contrario: {nombre: A, nif: '1', apellido1: {x: y}}\n",                     # mapping
    "contrario: {nombre: A}\n",                                                  # sin identidad
    "contrario: {nombre: A, id_crm: '12a'}\n",                                   # id no numérico
    "contrario: {nombre: A, nif: '1', provincia: Atlantida}\n",                  # no llega
    "contrario: {nombre: A, nif: '1', movil: '+34'}\n",                          # se queda vacío
    "cliente_propio: NO_EXISTE\n",
    "- una lista\n",                                                             # raíz
])
def test_cero_writers_y_cero_llamadas_ante_una_entrada_invalida(caso, monkeypatch, texto):
    crm = CRMFalso().instalar(monkeypatch)
    _yaml(caso, texto)
    r = _corre()
    assert r.exit_code == 1, r.output
    assert crm.escrituras == [] and crm.busquedas == [] and crm.lecturas == []
