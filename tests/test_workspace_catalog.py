"""`CaseCatalog` — el fichero de la biblioteca (Fase 1, Task 6).

Responde cuatro preguntas, y **todas sobre el CANON**, nunca sobre una copia local:

    localizar(ref)            ¿donde esta este expediente?
    estado_compartido(ref)    ¿que dice el canon: disponible, prestado, en conflicto?
    bajo_catalogo(path)       ¿esta ruta cae dentro de la biblioteca?
    es_proyeccion_local(dir)  ¿esto es un expediente, o el reflejo de uno?

## Por que existe, en un defecto concreto

El **A-8** del §5.1: `resolve_ref` resuelve el W-code recorriendo `list_cases()` y
devolviendo **el primero** cuyo `meta.id_go` casa, sin comprobar duplicados. Medido
antes de escribir esto: con dos carpetas que declaran `id_go: W-DUPLI`, devolvia
«Calle A» **sin aviso**, elegida por orden de escaneo. Renombrar una carpeta cambia
la respuesta. Traducido: pides un expediente y el sistema trabaja sobre otro.

Y no es rebuscado. En cuanto exista la proyeccion local del §6.3 habra
**deliberadamente** dos ficheros de identidad con el mismo W-code —el del Drive y el
de la copia—. Por eso la regla de ambiguedad y la marca de proyeccion van juntas: sin
la marca, el propio diseno fabricaria el conflicto que la regla detecta.

## Lo que NO hace

No decide sobre que copia se trabaja —eso es el resolver del Task 7— ni conoce las
copias locales de esta maquina —eso es el registro—. Solo lee el canon.
"""
from __future__ import annotations

import importlib
import textwrap

import pytest


@pytest.fixture
def root(tmp_path, monkeypatch):
    r = tmp_path / "CASOS"
    r.mkdir()
    monkeypatch.setenv("CASOS_ROOT", str(r))
    from core import config as cfg
    importlib.reload(cfg)
    from core.casos import case_locator
    monkeypatch.setattr(case_locator, "_root", lambda: r)
    yield r


def _caso(root, nombre, *, id_go=None, estado=None, titular=None,
          proyeccion_local=False):
    d = root / nombre / "00_Input"
    d.mkdir(parents=True, exist_ok=True)
    meta = {}
    if id_go:
        meta["id_go"] = id_go
    if estado:
        meta["estado_repositorio"] = estado
    if titular:
        meta["checkout_user"] = titular
        meta["checkout_maquina"] = "OTRA-MAQUINA"
        meta["checkout_timestamp"] = "2026-08-24T10:00:00Z"
    if proyeccion_local:
        meta["proyeccion_local"] = True
    cuerpo = "\n".join(f"  {k}: {v}" for k, v in meta.items())
    (d / "_caso.md").write_text(
        textwrap.dedent(f"---\nmeta:\n{cuerpo}\n---\n"), encoding="utf-8")
    return root / nombre


# ------------------------------------------------------------------ localizar

class TestLocalizar:
    def test_devuelve_la_ruta_del_caso(self, root):
        from core.casos.case_catalog import CaseCatalog
        from core.casos.workspace_model import CaseRef
        d = _caso(root, "BaRS9 - Prueba - (W-TEST99) - Vuelta", id_go="W-TEST99")
        assert CaseCatalog().localizar(CaseRef(w_code="W-TEST99")) == d

    def test_de_un_caso_ausente_LANZA(self, root):
        from core.casos.case_catalog import CaseCatalog
        from core.casos.workspace_model import CaseRef, LocalWorkspaceMissing
        with pytest.raises(LocalWorkspaceMissing):
            CaseCatalog().localizar(CaseRef(w_code="W-NOEXISTE"))


# ------------------------------------------------------- la ambiguedad (A-8)

class TestAmbiguedad:
    def test_dos_carpetas_con_el_mismo_id_go_LANZAN(self, root):
        """El A-8. Medido antes de escribir esto: hoy devuelve la primera."""
        from core.casos.case_catalog import CaseCatalog
        from core.casos.workspace_model import AmbiguousCase, CaseRef
        _caso(root, "BaRS9 - Calle A - (W-DUPLI) - Vuelta", id_go="W-DUPLI")
        _caso(root, "BaRS9 - Calle B - (W-DUPLI) - Bad debt", id_go="W-DUPLI")
        with pytest.raises(AmbiguousCase):
            CaseCatalog().localizar(CaseRef(w_code="W-DUPLI"))

    def test_el_error_no_publica_las_rutas(self, root):
        """§16: puede decir CUANTAS hay, no donde estan.

        **Aviso para quien lo mute:** `detalle` NO sirve como vector. El modelo lo
        acepta y no lo renderiza nunca (diseno del Task 4), asi que un mutante que
        meta las rutas ahi SOBREVIVE — y no porque el test este vacio, sino porque
        ataca algo estructuralmente inerte. Van tres veces cometido en esta misma
        sesion. El vector real es un campo que SI se renderiza, como `w_code`:
        mutar `w_code=str(candidatas)` mata este test, comprobado.
        """
        from core.casos.case_catalog import CaseCatalog
        from core.casos.workspace_model import AmbiguousCase, CaseRef
        _caso(root, "BaRS9 - Calle A - (W-DUPLI) - Vuelta", id_go="W-DUPLI")
        _caso(root, "BaRS9 - Calle B - (W-DUPLI) - Bad debt", id_go="W-DUPLI")
        with pytest.raises(AmbiguousCase) as exc:
            CaseCatalog().localizar(CaseRef(w_code="W-DUPLI"))
        assert str(root) not in str(exc.value)
        assert "Calle A" not in str(exc.value)

    def test_resolve_ref_tambien_lanza_y_no_elige_por_orden(self, root):
        """La puerta vieja tambien se cierra: era la que elegia en silencio."""
        from core.casos import case_locator
        from core.casos.workspace_model import AmbiguousCase
        _caso(root, "BaRS9 - Calle A - (W-DUPLI) - Vuelta", id_go="W-DUPLI")
        _caso(root, "BaRS9 - Calle B - (W-DUPLI) - Bad debt", id_go="W-DUPLI")
        with pytest.raises(AmbiguousCase):
            case_locator.resolve_ref("W-DUPLI")

    def test_un_solo_caso_sigue_resolviendo(self, root):
        from core.casos import case_locator
        _caso(root, "BaRS9 - Prueba - (W-TEST99) - Vuelta", id_go="W-TEST99")
        assert case_locator.resolve_ref("W-TEST99") == \
            "BaRS9 - Prueba - (W-TEST99) - Vuelta"


# --------------------------------------------------- la proyeccion local

class TestProyeccionLocal:
    def test_una_proyeccion_no_cuenta_como_expediente(self, root):
        from core.casos.case_catalog import CaseCatalog
        d = _caso(root, "BaRS9 - Reflejo - (W-TEST99) - Vuelta",
                  id_go="W-TEST99", proyeccion_local=True)
        assert CaseCatalog().es_proyeccion_local(d) is True

    def test_un_expediente_normal_no_es_proyeccion(self, root):
        from core.casos.case_catalog import CaseCatalog
        d = _caso(root, "BaRS9 - Prueba - (W-TEST99) - Vuelta", id_go="W-TEST99")
        assert CaseCatalog().es_proyeccion_local(d) is False

    def test_list_cases_EXCLUYE_la_proyeccion(self, root):
        from core.casos import case_locator
        _caso(root, "BaRS9 - Real - (W-AAAA1) - Vuelta", id_go="W-AAAA1")
        _caso(root, "BaRS9 - Reflejo - (W-AAAA1) - Vuelta",
              id_go="W-AAAA1", proyeccion_local=True)
        nombres = sorted(p.name for p in case_locator.list_cases())
        assert nombres == ["BaRS9 - Real - (W-AAAA1) - Vuelta"]

    def test_y_por_eso_la_proyeccion_NO_crea_ambiguedad(self, root):
        """La razon de ser de la marca: el diseno fabrica dos ficheros de
        identidad con el mismo W-code a proposito, y sin la marca chocarian."""
        from core.casos.case_catalog import CaseCatalog
        from core.casos.workspace_model import CaseRef
        real = _caso(root, "BaRS9 - Real - (W-AAAA1) - Vuelta", id_go="W-AAAA1")
        _caso(root, "BaRS9 - Reflejo - (W-AAAA1) - Vuelta",
              id_go="W-AAAA1", proyeccion_local=True)
        assert CaseCatalog().localizar(CaseRef(w_code="W-AAAA1")) == real


# ------------------------------------------------------- estado compartido

class TestEstadoCompartido:
    def test_un_caso_sin_campos_de_lock_esta_disponible(self, root):
        """Retrocompatible: un `_caso.md` viejo no tiene los campos."""
        from core.casos.case_catalog import CaseCatalog
        from core.casos.workspace_model import CaseRef
        _caso(root, "BaRS9 - Prueba - (W-TEST99) - Vuelta", id_go="W-TEST99")
        est = CaseCatalog().estado_compartido(CaseRef(w_code="W-TEST99"))
        assert est["estado"] == "disponible"
        assert est["checkout_user"] is None

    def test_un_caso_prestado_dice_quien_lo_tiene(self, root):
        from core.casos.case_catalog import CaseCatalog
        from core.casos.workspace_model import CaseRef
        _caso(root, "BaRS9 - Prueba - (W-TEST99) - Vuelta", id_go="W-TEST99",
              estado="prestado", titular="otro.usuario")
        est = CaseCatalog().estado_compartido(CaseRef(w_code="W-TEST99"))
        assert est["estado"] == "prestado"
        assert est["checkout_user"] == "otro.usuario"
        assert est["checkout_maquina"] == "OTRA-MAQUINA"

    def test_reutiliza_el_vocabulario_que_ya_existe(self, root):
        """No inventa estados: son los de `config.ESTADO_REPO_*`."""
        from core.casos.case_catalog import CaseCatalog
        from core.casos.workspace_model import CaseRef
        from core.config import (ESTADO_REPO_CONFLICTO, ESTADO_REPO_DISPONIBLE,
                                 ESTADO_REPO_PRESTADO)
        _caso(root, "BaRS9 - Prueba - (W-TEST99) - Vuelta", id_go="W-TEST99",
              estado=ESTADO_REPO_CONFLICTO)
        est = CaseCatalog().estado_compartido(CaseRef(w_code="W-TEST99"))
        assert est["estado"] in {ESTADO_REPO_DISPONIBLE, ESTADO_REPO_PRESTADO,
                                 ESTADO_REPO_CONFLICTO}
        assert est["estado"] == ESTADO_REPO_CONFLICTO


# ---------------------------------------------------------- bajo_catalogo

class TestBajoCatalogo:
    def test_un_subdirectorio_de_casos_root_esta_dentro(self, root):
        from core.casos.case_catalog import CaseCatalog
        assert CaseCatalog().bajo_catalogo(root / "lo-que-sea") is True

    def test_la_propia_raiz_esta_dentro(self, root):
        from core.casos.case_catalog import CaseCatalog
        assert CaseCatalog().bajo_catalogo(root) is True

    def test_una_ruta_de_fuera_no(self, root, tmp_path):
        from core.casos.case_catalog import CaseCatalog
        assert CaseCatalog().bajo_catalogo(tmp_path / "Desktop" / "copia") is False

    def test_un_hermano_con_prefijo_parecido_NO_cuenta_como_dentro(self, root):
        """`CASOS_maligno` no esta bajo `CASOS`, aunque su nombre empiece igual.

        Comparar por prefijo de cadena sin separador es el error clasico aqui, y
        daria por bueno un destino de checkout que esta fuera de la biblioteca.
        """
        from core.casos.case_catalog import CaseCatalog
        hermano = root.parent / (root.name + "_maligno")
        assert CaseCatalog().bajo_catalogo(hermano) is False
