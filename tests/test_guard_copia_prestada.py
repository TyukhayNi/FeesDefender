"""El guard de escritura decide por DÓNDE escribe, no solo por el estado (`MEJORAS #96`).

## El defecto, y por qué es de sitio y no de implementación

`guard_escritura` decide leyendo el `estado_repositorio` del `_caso.md` **local**. Si ese
fichero dice `prestado`, toda escritura de intake se desvía a
`_pendiente_checkin/<origen>/…`, que está **fuera de `00_Input`** — y `00_Input` es
justamente lo que `sala_maquina.inventariar()` recorre. Consecuencia medida el 2026-07-27
sobre `W-02MA0R`: se depositan documentos nuevos, la sala de máquina **no ve ni uno**, la
de lectura tampoco, y la corrida se reporta como correcta. El pipeline se rompe en
silencio.

El propósito del guard (DISEÑO_V2 §6) es proteger **el Drive**: que el pipeline no pise un
caso que otro tiene prestado. Sobre una **copia local prestada** desviar no protege de
nada — esa copia entera ya es «pendiente de checkin» por definición, y el merge de tres
vías sube sus altas como `COPY_LOCAL`. Es una bandeja dentro de la bandeja.

## El discriminante, y el que NO vale — que es la parte que costó

El primer intento fue **la presencia de `MANIFEST_CHECKOUT.json`**: parecía la marca
inequívoca de copia prestada, la escribe el propio `cmd_checkout` y el checkin la lee como
baseline. **Es falso, y abría un agujero de autorización.** `cmd_checkout` sube además una
copia del manifiesto **al Drive** (`repository_cli.py`, «debe sobrevivir a la muerte del
Desktop, §3.3»), así que mientras un caso está prestado el fichero está en **las dos
copias**. Un guard que discriminara por él quedaría desactivado precisamente **sobre el
canon y precisamente mientras está prestado**, que es el único momento en que hace falta.

Lo que sí discrimina es el **registro privado de workspaces** (Fase 1): la lista de qué
copias locales conoce **esta** máquina. El canon nunca está ahí —el resolver rechaza
registrar una ruta bajo el catálogo (`WORKSPACE_UNDER_CATALOG_ROOT`)— y una copia local sí,
en cuanto se registra al prestarla o se **adopta** por la puerta del §15.

**Consecuencia declarada:** un checkout **anterior al registro y sin adoptar** sigue
desviando. Es deliberado: el sistema no adivina sobre qué copia está: o consta, o no. La vía
de desbloqueo existe y es explícita (`workspace_adopcion`, Task 8b).
"""
from __future__ import annotations

import importlib
import json

import pytest

from core import case_manager

CASE_ID = "EV-2026-001"
AHORA = "2026-08-25T12:00:00Z"


@pytest.fixture(autouse=True)
def _reload(tmp_casos_root):
    from core import config as cfg
    importlib.reload(cfg)
    importlib.reload(case_manager)


@pytest.fixture
def registro(tmp_path, monkeypatch):
    """Registro privado en `tmp_path`, FUERA de `CASOS_ROOT` (lo exige la clase)."""
    raiz = tmp_path / "registro_privado"
    monkeypatch.setenv("FEESDEFENDER_WORKSPACE_REGISTRY", str(raiz))
    from core.casos.workspace_registry import WorkspaceRegistry
    return WorkspaceRegistry(raiz, ahora=AHORA)


def _caso_prestado(case_id: str = CASE_ID) -> str:
    case_manager.ensure_case(case_id, titulo="Caso guard")
    case_manager.escribir_lock(case_id, user="Nikolai Tyukhay",
                               timestamp=AHORA, nonce="n")
    return case_id


def _con_manifiesto(case_id: str) -> None:
    """El `MANIFEST_CHECKOUT.json` que `cmd_checkout` deja **en las dos copias**."""
    from core.config import caso_path
    (caso_path(case_id) / "MANIFEST_CHECKOUT.json").write_text(
        json.dumps({"generado": AHORA, "n_ficheros": 0, "inventario": {}}),
        encoding="utf-8")


def _registrar_como_copia_local(registro, case_id: str, raiz_local,
                                tipo: str = "checkout"):
    """Registra una copia local REAL: **fuera** del catálogo, y devuelve su ruta.

    ## Por qué cambió esta función, que es lo que enseña el fichero

    Hasta el 2026-09-02 daba de alta `caso_path(case_id)` —**el canon**—, saltándose al
    resolver que lo prohíbe. Fabricaba el estado que producción tiene prohibido, y en ese
    estado la rama que estos tests dicen probar sí funcionaba: **nueve tests verdes
    defendían el defecto** (`MEJORAS #124`, hallazgo H16-01 de la R16).

    Es un caso de libro de cobertura al revés: añadir tests no lo encuentra, hay que
    preguntar **quién** lo defiende.

    Ahora registra una ruta fuera del catálogo, que es el único estado que producción
    puede producir desde que `alta` rechaza el canon (`MEJORAS #136`). Con esta fixture
    honesta, cuatro de los tests **fallan** — y ése es el resultado correcto: la rama que
    describen está muerta mientras `MEJORAS #124` siga abierta.
    """
    from core.casos.workspace_registry import SCHEMA_SOPORTADO, WorkspaceEntry
    local = raiz_local / case_id
    local.mkdir(parents=True, exist_ok=True)
    registro.alta(WorkspaceEntry(
        case_id=case_id, w_code="W-GUARD1", canonical_ref=None,
        local_path=local, nonce="n", maquina="ESTA",
        tipo=tipo, ultima_validacion=AHORA, schema=SCHEMA_SOPORTADO))
    return local


#: Motivo compartido de los `xfail` de `MEJORAS #124`.
_MOTIVO_124 = (
    "MEJORAS #124: `es_copia_prestada` compara la ruta que devuelve `buscar()` —que "
    "solo mira bajo CASOS_ROOT— contra un registro que solo contiene rutas de fuera, "
    "asi que la rama de copia local no puede activarse. Verde hasta el 2026-09-02 "
    "solo porque la fixture registraba el canon. Se reactivan con la rev. 2 del plan "
    "de #124; si alguno pasa (XPASS), PARA: significa que #124 se cerro y hay que "
    "retirar el marcador."
)


class TestSobreElCanon:
    """Donde el guard SÍ protege. Es la mitad que no se toca, y la que casi rompo."""

    def test_prestado_CON_manifiesto_sigue_desviando(self, tmp_casos_root, registro):
        """El hallazgo que mató al primer discriminante.

        `cmd_checkout` sube el manifiesto al Drive (§3.3), así que este es el estado
        REAL del canon mientras un caso está prestado. Un guard que discriminara por la
        presencia del fichero quedaría desactivado aquí — sobre la copia canónica y
        justo mientras otro la tiene tomada.
        """
        _caso_prestado()
        _con_manifiesto(CASE_ID)
        decision = case_manager.guard_escritura(CASE_ID, "00_Input/nuevo.pdf", "intake")
        assert decision.desviar is True, (
            "el guard se desactivó sobre el CANON de un caso prestado: el manifiesto "
            "está en las dos copias y no discrimina nada")

    def test_prestado_sin_manifiesto_desvia(self, tmp_casos_root, registro):
        _caso_prestado()
        decision = case_manager.guard_escritura(CASE_ID, "00_Input/nuevo.pdf", "intake")
        assert decision.desviar is True

    def test_el_conflicto_tambien_desvia(self, tmp_casos_root, registro):
        from core.config import caso_path
        from core.utils import read_md, write_md
        _caso_prestado()
        p = caso_path(CASE_ID) / "00_Input" / "_caso.md"
        fm, cuerpo = read_md(p)
        fm["meta"]["estado_repositorio"] = "conflicto"
        write_md(p, fm, cuerpo)
        decision = case_manager.guard_escritura(CASE_ID, "00_Input/nuevo.pdf", "intake")
        assert decision.desviar is True


class TestSobreLaCopiaLocalRegISTRADA:
    """Donde el guard no protege de nada y sí rompe el pipeline.

    **Los cuatro están en `xfail(strict=True)` desde el 2026-09-02**, y eso NO es una
    regresión de ese día: es el día en que la fixture dejó de mentir. Describen lo que
    `MEJORAS #96` quería y `MEJORAS #124` demuestra que no ocurre. Ver `_MOTIVO_124`.

    Disciplina del `xfail` (la misma de `test_repository_cli_defectos.py`): **ninguna
    precondición usa `assert`**, para que el marcador solo pueda darse por satisfecho con
    la aserción que de verdad prueba el defecto.
    """

    @pytest.mark.xfail(strict=True, raises=AssertionError, reason=_MOTIVO_124)
    def test_NO_desvia(self, tmp_casos_root, registro, tmp_path):
        _caso_prestado()
        _con_manifiesto(CASE_ID)
        _registrar_como_copia_local(registro, CASE_ID, tmp_path / "Desktop")
        decision = case_manager.guard_escritura(CASE_ID, "00_Input/nuevo.pdf", "intake")
        assert decision.desviar is False, (
            "el guard desvió sobre una copia local registrada: los documentos caen "
            "fuera de 00_Input y la sala de máquina no los ve (MEJORAS #96)")

    @pytest.mark.xfail(strict=True, raises=AssertionError, reason=_MOTIVO_124)
    def test_dir_intake_devuelve_el_arbol_vivo(self, tmp_casos_root, registro, tmp_path):
        """Y «el árbol vivo» es **la copia local**, no el canon.

        La versión anterior esperaba `caso_path(case_id)`, que es el canon — coherente
        con su fixture y con nada más. Con la copia registrada donde de verdad está, la
        expectativa correcta es la copia; que hoy no se cumpla es justo `MEJORAS #124`.
        """
        _caso_prestado()
        local = _registrar_como_copia_local(registro, CASE_ID, tmp_path / "Desktop")
        destino = case_manager.dir_intake(CASE_ID, "00_Input/01_Drive EV", "intake")
        assert destino == local / "00_Input/01_Drive EV", (
            f"el intake no apunta a la copia de trabajo registrada: {destino}")

    @pytest.mark.xfail(strict=True, raises=AssertionError, reason=_MOTIVO_124)
    def test_no_emite_evento_de_desvio(self, tmp_casos_root, registro, tmp_path):
        """Un desvío que no ocurre no se registra: el log no puede narrar ficción."""
        from core.intake_log import read_events
        _caso_prestado()
        _registrar_como_copia_local(registro, CASE_ID, tmp_path / "Desktop")
        case_manager.guard_escritura(CASE_ID, "00_Input/nuevo.pdf", "intake")
        assert [e for e in read_events(CASE_ID) if e["event"] == "pendiente_checkin"] == []

    @pytest.mark.xfail(strict=True, raises=AssertionError, reason=_MOTIVO_124)
    def test_un_scratch_registrado_tambien_cuenta(self, tmp_casos_root, registro,
                                                  tmp_path):
        """`local_scratch` es la otra forma de copia local del §5.2."""
        _caso_prestado()
        _registrar_como_copia_local(registro, CASE_ID, tmp_path / "Desktop",
                                    tipo="scratch")
        decision = case_manager.guard_escritura(CASE_ID, "00_Input/nuevo.pdf", "intake")
        assert decision.desviar is False


class TestFallaCerrado:
    """Ante la duda, desviar: el lado seguro es el que protege el canon."""

    def test_un_registro_ilegible_NO_desactiva_el_guard(self, tmp_casos_root, registro,
                                                        monkeypatch, tmp_path):
        """`RegistryUnreadable` no puede leerse como «no es copia local, adelante».

        Es la misma regla que el registro aplica a sí mismo (falla cerrado, R7/H7-02):
        «no puedo saberlo» no es «no lo es».

        ## Sí discrimina, y lo digo aquí porque llegué a escribir lo contrario

        Escribí en su día que con `MEJORAS #124` abierta este test «no puede distinguir»
        lo que su nombre promete, razonando que `es_copia_prestada` devuelve `False` por
        las dos vías. **Es falso, y lo midió R22/H22-08**: el `monkeypatch` obliga a pasar
        por el `except`, así que mutar ese `except` a `return True` pone el test **rojo**.
        La polaridad del fallo cerrado está contratada aquí y solo aquí.

        Que la vía sana de `#124` también devuelva `False` no le quita valor probatorio:
        el test no compara las dos vías, ejerce una.

        Conviene registrarlo porque el error iba en la dirección **contraria** a la
        habitual: no inflé lo que el test probaba, lo rebajé — y una nota de humildad
        falsa habría retirado de la vista la única prueba de esa polaridad.
        """
        from core.casos import workspace_registry as wr
        _caso_prestado()
        _registrar_como_copia_local(registro, CASE_ID, tmp_path / "Desktop")

        def _revienta(self):
            raise wr.RegistryUnreadable(detalle="ilegible")

        monkeypatch.setattr(wr.WorkspaceRegistry, "cargar", _revienta)
        decision = case_manager.guard_escritura(CASE_ID, "00_Input/nuevo.pdf", "intake")
        assert decision.desviar is True, (
            "un registro ilegible desactivó el guard: 'no puedo saberlo' se leyó como "
            "'no es el canon'")

    def test_un_caso_que_no_existe_no_revienta(self, tmp_casos_root, registro):
        """El guard no puede convertirse en una vía nueva de excepción."""
        decision = case_manager.guard_escritura("NO-EXISTE", "00_Input/x.pdf", "intake")
        assert decision.desviar is False        # caso ausente ⇒ estado `disponible`
