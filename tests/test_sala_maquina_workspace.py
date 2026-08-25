"""`sala_maquina` resuelve por workspace y acepta `--case-dir` (Task 9, cierra A-7).

Primer consumidor real de todo lo construido en la Fase 1. Y es también lo que hace
**utilizable** el modo `local_scratch`, que hasta ahora no tenía ninguna vía: el
Cluster B del diseño de scratch nunca se construyó, así que trabajar en una copia
local dependía de sobrescribir `CASOS_ROOT` por entorno.

## Lo que este task añade, y por qué importa

Hoy `sala_maquina` resuelve por `caso_path` y **escribe sin preguntar a nadie** si le
corresponde escribir. Si el caso está prestado a otra máquina, el motor arranca igual:
atomiza el correo, deja `_segmentacion.md`, actualiza estado y cobertura y emite el
evento. Todo eso, sobre una copia que otro tiene en curso.

Después de este task, los tres subcomandos **abortan con código 2 y cero bytes**.

## La costura que se conserva a propósito

~28 sitios de test parchean `cli.caso_path` para montar casos fuera de `CASOS_ROOT`.
El diseño lo respeta preguntando **primero al catálogo**: si el canon no conoce el
caso, no hay lock que respetar y se usa el binding del módulo (`legacy_unresolved`,
Fase 4); si lo conoce, manda el resolver y puede bloquear. Así el bloqueo es real donde
hay algo que bloquear, y la costura sobrevive donde no.
"""
from __future__ import annotations

import hashlib
import importlib
import textwrap

import pytest
import typer

from scripts import sala_maquina as cli

AHORA = "2026-08-25T10:00:00Z"
YO = "nikolai"
ESTA = "ESTA-MAQUINA"
CASO = "BaRS9 - Prueba - (W-TEST99) - Vuelta"


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


def _huella(raiz) -> dict[str, str]:
    return {p.relative_to(raiz).as_posix():
            ("d" if p.is_dir() else hashlib.sha256(p.read_bytes()).hexdigest()[:16])
            for p in sorted(raiz.rglob("*"))}


def _canon(root, *, estado="disponible", titular=None, maquina=None, nonce=None):
    d = root / CASO / "00_Input"
    d.mkdir(parents=True, exist_ok=True)
    meta = {"id_go": "W-TEST99", "estado_repositorio": estado}
    for k, v in (("checkout_user", titular), ("checkout_maquina", maquina),
                 ("checkout_nonce", nonce)):
        if v:
            meta[k] = v
    if estado == "prestado":
        meta["checkout_timestamp"] = AHORA
    cuerpo = "\n".join(f"  {k}: {v}" for k, v in meta.items())
    (d / "_caso.md").write_text(
        textwrap.dedent(f"---\nmeta:\n{cuerpo}\n---\n"), encoding="utf-8")
    return root / CASO


def _identidad_fija(monkeypatch):
    monkeypatch.setattr(cli, "_identidad_actor", lambda: (YO, ESTA), raising=False)


# ==========================================================================
# El bloqueo: sobre un caso prestado por OTRO, cero bytes
# ==========================================================================

class TestCasoPrestadoPorOtro:
    """Los TRES subcomandos, no dos (R7/H7-13).

    La interfaz promete que «los tres abortan con codigo 2 y cero bytes», y el Step
    original solo probaba `plan` y `apply`. `reforzar` escribe cobertura, estado y
    evento, asi que podia omitir el guard y dejar la suite verde.
    """

    @pytest.mark.parametrize("comando", ["plan", "apply", "reforzar"])
    def test_aborta_con_codigo_2(self, root, monkeypatch, comando):
        _identidad_fija(monkeypatch)
        _canon(root, estado="prestado", titular="otro", maquina="OTRA", nonce="n9")
        with pytest.raises(typer.Exit) as exc:
            getattr(cli, comando)("W-TEST99")
        assert exc.value.exit_code == 2

    @pytest.mark.parametrize("comando", ["plan", "apply", "reforzar"])
    def test_no_escribe_NI_UN_byte(self, root, monkeypatch, comando):
        """El death test. Hash del arbol antes y despues, identico."""
        _identidad_fija(monkeypatch)
        _canon(root, estado="prestado", titular="otro", maquina="OTRA", nonce="n9")
        antes = _huella(root)
        with pytest.raises(typer.Exit):
            getattr(cli, comando)("W-TEST99")
        assert _huella(root) == antes

    @pytest.mark.parametrize("comando", ["plan", "apply", "reforzar"])
    def test_no_deja_evento_en_el_log(self, root, monkeypatch, comando):
        """Ni rastro: un caso ajeno no se toca ni para decir que se intento."""
        from core.intake_log import read_events_de
        _identidad_fija(monkeypatch)
        canon = _canon(root, estado="prestado", titular="otro", maquina="OTRA",
                       nonce="n9")
        with pytest.raises(typer.Exit):
            getattr(cli, comando)("W-TEST99")
        assert read_events_de(canon) == []

    def test_el_mensaje_dice_quien_lo_tiene_y_no_la_ruta(self, root, monkeypatch, capsys):
        _identidad_fija(monkeypatch)
        _canon(root, estado="prestado", titular="otro", maquina="OTRA", nonce="n9")
        with pytest.raises(typer.Exit):
            cli.plan("W-TEST99")
        err = capsys.readouterr().err
        assert "otro" in err
        assert str(root) not in err


# ==========================================================================
# El conflicto también bloquea
# ==========================================================================

class TestCasoEnConflicto:
    @pytest.mark.parametrize("comando", ["plan", "apply", "reforzar"])
    def test_aborta_y_no_escribe(self, root, monkeypatch, comando):
        _identidad_fija(monkeypatch)
        _canon(root, estado="conflicto")
        antes = _huella(root)
        with pytest.raises(typer.Exit) as exc:
            getattr(cli, comando)("W-TEST99")
        assert exc.value.exit_code == 2
        assert _huella(root) == antes


# ==========================================================================
# `--case-dir`: el scratch por fin tiene vía
# ==========================================================================

class TestCaseDir:

    def test_case_dir_junto_con_identidad_es_error_de_uso(self, root, tmp_path,
                                                          monkeypatch):
        """Las dos formas de decir «este caso» son mutuamente excluyentes.

        El `--case-dir` que se pasa **funcionaria por si solo**: es un scratch
        registrado. A proposito. Con una ruta inexistente el rechazo lo producia la
        guarda de EXISTENCIA —que tambien sale con 2— y el test pasaba aunque la
        exclusion mutua desapareciera. Lo cazo la mutacion, y es la quinta vez en
        esta sesion que el escenario mas facil de montar no aisla la guarda.
        """
        from core.casos.workspace_registry import (SCHEMA_SOPORTADO,
                                                   WorkspaceEntry, WorkspaceRegistry)
        _identidad_fija(monkeypatch)
        scratch = tmp_path / "Desktop" / CASO
        (scratch / "00_Input").mkdir(parents=True)
        reg = WorkspaceRegistry(tmp_path / "registro", ahora=AHORA)
        reg.alta(WorkspaceEntry(
            case_id=CASO, w_code="W-TEST99", canonical_ref=None, local_path=scratch,
            nonce="s1", maquina=ESTA, tipo="scratch", ultima_validacion=AHORA,
            schema=SCHEMA_SOPORTADO))
        monkeypatch.setattr(cli, "_registro_de_workspaces", lambda ahora: reg,
                            raising=False)
        monkeypatch.setattr(cli.sm, "ejecutar", lambda *a, **k: [])
        monkeypatch.setattr(cli, "_atomizar_correo", lambda *a, **k: None)
        with pytest.raises(typer.Exit) as exc:
            cli.plan("W-TEST99", case_dir=str(scratch))
        assert exc.value.exit_code == 2

    def test_sin_identidad_ni_case_dir_es_error_de_uso(self, root, monkeypatch):
        _identidad_fija(monkeypatch)
        with pytest.raises(typer.Exit):
            cli.plan(None)

    def test_case_dir_sobre_un_scratch_registrado_procesa(self, root, tmp_path,
                                                          monkeypatch):
        """A-7: hasta ahora `local_scratch` no tenia NINGUNA via de trabajo."""
        from core.casos.workspace_registry import (SCHEMA_SOPORTADO,
                                                   WorkspaceEntry, WorkspaceRegistry)
        _identidad_fija(monkeypatch)
        scratch = tmp_path / "Desktop" / CASO
        (scratch / "00_Input").mkdir(parents=True)
        reg = WorkspaceRegistry(tmp_path / "registro", ahora=AHORA)
        reg.alta(WorkspaceEntry(
            case_id=CASO, w_code="W-TEST99", canonical_ref=None, local_path=scratch,
            nonce="s1", maquina=ESTA, tipo="scratch", ultima_validacion=AHORA,
            schema=SCHEMA_SOPORTADO))
        monkeypatch.setattr(cli, "_registro_de_workspaces", lambda ahora: reg,
                            raising=False)
        monkeypatch.setattr(cli.sm, "ejecutar", lambda *a, **k: [])
        monkeypatch.setattr(cli, "_atomizar_correo", lambda *a, **k: None)
        cli.plan(None, case_dir=str(scratch))

    def test_el_evento_del_case_dir_cae_en_el_SCRATCH(self, root, tmp_path, monkeypatch):
        """B0-1 en el consumidor: el rastro va con los bytes."""
        from core.casos.workspace_registry import (SCHEMA_SOPORTADO,
                                                   WorkspaceEntry, WorkspaceRegistry)
        from core.intake_log import read_events_de
        _identidad_fija(monkeypatch)
        canon = _canon(root)
        scratch = tmp_path / "Desktop" / CASO
        (scratch / "00_Input").mkdir(parents=True)
        reg = WorkspaceRegistry(tmp_path / "registro", ahora=AHORA)
        reg.alta(WorkspaceEntry(
            case_id=CASO, w_code="W-TEST99", canonical_ref=None, local_path=scratch,
            nonce="s1", maquina=ESTA, tipo="scratch", ultima_validacion=AHORA,
            schema=SCHEMA_SOPORTADO))
        monkeypatch.setattr(cli, "_registro_de_workspaces", lambda ahora: reg,
                            raising=False)
        monkeypatch.setattr(cli.sm, "ejecutar", lambda *a, **k: [])
        monkeypatch.setattr(cli, "_atomizar_correo", lambda *a, **k: None)
        monkeypatch.setattr(cli, "_procesar_adjuntos", lambda *a, **k: None)
        cli.apply(None, case_dir=str(scratch))
        assert read_events_de(scratch)
        assert read_events_de(canon) == []

    def test_case_dir_bajo_casos_root_se_rechaza(self, root, monkeypatch):
        """§5.1: un workspace dentro de la biblioteca mezcla copia y original."""
        _identidad_fija(monkeypatch)
        dentro = root / "copia-de-trabajo"
        (dentro / "00_Input").mkdir(parents=True)
        with pytest.raises(typer.Exit):
            cli.plan(None, case_dir=str(dentro))


# ==========================================================================
# Regresión: el camino de siempre sigue funcionando
# ==========================================================================

class TestRegresion:

    def test_un_caso_DISPONIBLE_se_procesa_como_siempre(self, root, monkeypatch):
        _identidad_fija(monkeypatch)
        _canon(root, estado="disponible")
        monkeypatch.setattr(cli.sm, "ejecutar", lambda *a, **k: [])
        monkeypatch.setattr(cli, "_atomizar_correo", lambda *a, **k: None)
        cli.plan("W-TEST99")

    def test_un_caso_PRESTADO_A_MI_con_registro_se_procesa(self, root, tmp_path,
                                                           monkeypatch):
        from core.casos.workspace_registry import (SCHEMA_SOPORTADO,
                                                   WorkspaceEntry, WorkspaceRegistry)
        _identidad_fija(monkeypatch)
        _canon(root, estado="prestado", titular=YO, maquina=ESTA, nonce="n1")
        local = tmp_path / "Desktop" / CASO
        (local / "00_Input").mkdir(parents=True)
        reg = WorkspaceRegistry(tmp_path / "registro", ahora=AHORA)
        reg.alta(WorkspaceEntry(
            case_id=CASO, w_code="W-TEST99", canonical_ref=None, local_path=local,
            nonce="n1", maquina=ESTA, tipo="checkout", ultima_validacion=AHORA,
            schema=SCHEMA_SOPORTADO))
        monkeypatch.setattr(cli, "_registro_de_workspaces", lambda ahora: reg,
                            raising=False)
        monkeypatch.setattr(cli.sm, "ejecutar", lambda *a, **k: [])
        monkeypatch.setattr(cli, "_atomizar_correo", lambda *a, **k: None)
        cli.plan("W-TEST99")

    def test_la_costura_de_los_tests_viejos_sobrevive(self, root, tmp_path, monkeypatch):
        """~28 sitios parchean `cli.caso_path` para montar casos FUERA del catalogo.

        El diseno pregunta primero al catalogo: si el canon no conoce el caso, no
        hay lock que respetar y se usa el binding del modulo. Si esta costura se
        rompiera, media suite de sala de maquina caeria — y no por un defecto, sino
        por haber elegido mal donde poner la resolucion.
        """
        _identidad_fija(monkeypatch)
        fuera = tmp_path / "fuera" / CASO
        (fuera / "00_Input").mkdir(parents=True)
        monkeypatch.setattr(cli, "caso_path", lambda cid: fuera)
        monkeypatch.setattr(cli.sm, "ejecutar", lambda *a, **k: [])
        monkeypatch.setattr(cli, "_atomizar_correo", lambda *a, **k: None)
        cli.plan("W-TEST99")


# ==========================================================================
# `plan` declara que escribe
# ==========================================================================

def test_plan_declara_que_escribe():
    """Dejaba `_segmentacion.md` de los bundles y se anunciaba como preview inocuo.

    Que un comando llamado `plan` escriba en el expediente es justo el tipo de cosa
    que hay que decir en su ayuda, no descubrir.
    """
    doc = (cli.plan.__doc__ or "").lower()
    assert "escrib" in doc, "el docstring de `plan` no declara que escribe"
