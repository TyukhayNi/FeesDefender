"""La fachada: cómo se construye el resolver y qué se le pasa.

**Por qué existe este fichero.** Los tests de los módulos inyectan sus dependencias, así
que ninguno pasaba por `core.procedimiento._resolver` — y ahí había dos bugs que el
`--help` del CLI no podía cazar porque typer solo importa:

1. `WorkspaceRegistry()` sin argumentos: `TypeError` en la primera invocación real.
2. `drive_accesible=True` a pelo, que es exactamente lo que dejó **muerta la rama offline
   entera** en `sala_maquina` hasta su Task 10 — el modo existía, tenía tests unitarios en
   el resolver, y ningún entrypoint podía llegar a él.

Los dos se cazan ejecutando la fachada, no leyéndola.
"""
import pytest

import core.procedimiento as proc
from core.procedimiento import sede


class _WsFalso:
    def __init__(self, root=None, case_id="CASO"):
        from core.casos.workspace_model import CaseRef
        self.working_root = root
        self.case_ref = CaseRef(case_id=case_id)
        self.capabilities = frozenset()

    def exigir(self, cap):
        pass


class _ResolverFalso:
    """Registra con qué se le llamó, que es justo lo que hay que comprobar."""

    ultima = {}

    def __init__(self, catalogo, registro, *, usuario, maquina, ahora):
        _ResolverFalso.ultima = {"registro": registro, "usuario": usuario,
                                 "maquina": maquina, "ahora": ahora}

    def resolver_por_ruta(self, ruta, *, drive_accesible):
        _ResolverFalso.ultima["drive_accesible"] = drive_accesible
        _ResolverFalso.ultima["via"] = "ruta"
        return _WsFalso(ruta)

    def resolver_por_identidad(self, ref, *, drive_accesible):
        _ResolverFalso.ultima["drive_accesible"] = drive_accesible
        _ResolverFalso.ultima["via"] = "identidad"
        return _WsFalso(None, ref.case_id)


@pytest.fixture()
def resolver_falso(monkeypatch, tmp_path):
    """Sustituye el resolver, el catálogo y el registro, y deja pasar el resto.

    Se parchea donde se USA (dentro de `_resolver`, que importa en el cuerpo), así que
    hay que parchear los módulos de origen.
    """
    import core.casos.workspace_registry as wr
    import core.casos.workspace_resolver as wres
    import core.casos.case_catalog as cc

    monkeypatch.setattr(wres, "CaseWorkspaceResolver", _ResolverFalso)
    monkeypatch.setattr(cc, "CaseCatalog", lambda *a, **k: object())
    monkeypatch.setattr(wr, "raiz_por_defecto", lambda: tmp_path)
    _ResolverFalso.ultima = {}
    return _ResolverFalso


def test_el_registro_se_construye_con_su_raiz_y_su_instante(resolver_falso, tmp_path):
    """El bug real: `WorkspaceRegistry()` sin argumentos revienta con TypeError, y ningún
    test de módulo pasaba por aquí."""
    proc._resolver("W-02VEKE", None)
    reg = resolver_falso.ultima["registro"]
    assert reg is not None
    assert resolver_falso.ultima["ahora"], "el resolver necesita el instante"
    assert resolver_falso.ultima["usuario"] and resolver_falso.ultima["maquina"]


def test_drive_accesible_sale_del_entorno_y_NO_es_un_True_a_pelo(resolver_falso,
                                                                monkeypatch):
    """Pasar `True` constante deja inalcanzable la rama offline del resolver."""
    monkeypatch.delenv("FEESDEFENDER_OFFLINE", raising=False)
    proc._resolver("W-02VEKE", None)
    assert resolver_falso.ultima["drive_accesible"] is True

    monkeypatch.setenv("FEESDEFENDER_OFFLINE", "1")
    proc._resolver("W-02VEKE", None)
    assert resolver_falso.ultima["drive_accesible"] is False, (
        "con FEESDEFENDER_OFFLINE=1 el resolver tiene que enterarse")


def test_las_dos_vias_son_mutuamente_excluyentes(resolver_falso, tmp_path):
    with pytest.raises(ValueError):
        proc._resolver("W-02VEKE", str(tmp_path))
    with pytest.raises(ValueError):
        proc._resolver(None, None)


def test_case_dir_va_por_ruta_y_la_identidad_por_identidad(resolver_falso, tmp_path):
    proc._resolver(None, str(tmp_path))
    assert resolver_falso.ultima["via"] == "ruta"
    proc._resolver("W-02VEKE", None)
    assert resolver_falso.ultima["via"] == "identidad"


def test_drive_accesible_no_DIVERGE_de_la_de_sala_de_maquina(monkeypatch):
    """Duplicación **declarada y fijada**: `sala_maquina._drive_accesible` decide lo mismo.

    Unificarlas exige tocar un módulo ya mergeado, así que en vez de dejarlas divergir en
    silencio se atan aquí. Si alguien cambia una y no la otra, este test lo dice.
    """
    from scripts.sala_maquina import _drive_accesible

    for valor, esperado in ((None, True), ("1", False), ("0", True), (" 1 ", False)):
        if valor is None:
            monkeypatch.delenv("FEESDEFENDER_OFFLINE", raising=False)
        else:
            monkeypatch.setenv("FEESDEFENDER_OFFLINE", valor)
        assert sede.drive_accesible() is esperado
        assert _drive_accesible() is sede.drive_accesible(), (
            f"las dos definiciones divergen con FEESDEFENDER_OFFLINE={valor!r}")
