"""La matriz del §14.1 aplicada a `scripts.sala_maquina`, y el arnés probándose.

Task 10 de la Fase 1. Dos mitades que se necesitan:

1. **El arnés se prueba a sí mismo.** `tests/_matriz_contractual.py` promete detectar
   efectos en los cuatro planos del §3.2-bis. Un arnés que solo detectara ficheros
   dejaría el canon, los servicios externos y el estado local sin participar en
   ninguna aserción, y la suite quedaría verde declarando «cero bytes» sobre tres
   planos que nadie mira. Aquí van los **cuatro mutantes, uno por plano** (R7/H7-07),
   y cada uno se exige que muera **por el suyo**: el aserto comprueba que el mensaje
   nombra su plano y **no** el de los otros tres. Un mutante que muere por el aserto
   de otro plano no prueba el suyo.

2. **`sala_maquina` corre la matriz entera.** Primer consumidor real, y la prueba de
   que el arnés vale para un entrypoint de verdad y no solo para dobles.

## Lo que esta ronda encontró, dicho antes que lo bueno

**La fila 8 no era inducible: `_resolver_workspace` pasaba `drive_accesible=True`
literal.** Toda la rama offline del §7.2.9-10 —el modo que la spec diseñó para
trabajar sin la unidad del despacho, con sus tests unitarios en el resolver— era
**código muerto en producción**, y ningún test lo decía porque ningún test miraba al
entrypoint. Se cierra con `_drive_accesible()`, que es una costura con dos condiciones
reales (`FEESDEFENDER_OFFLINE=1` y la raíz del catálogo desmontada), no un doble.

**Y el plano 3 es, para este entrypoint, cierto por vacío.** `sala_maquina` no llama
a ningún servicio externo mutante: hace OCR local. Así que `llamadas == 0` se cumple
sin que nadie lo induzca. El arnés **obliga a decirlo** (`sin_superficie_externa`) en
vez de dejar que el aserto pase en silencio, y el detector del plano 3 se prueba
donde sí se puede: contra el mutante 3 de la primera mitad.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts import sala_maquina as cli
from tests._matriz_contractual import (ESCENARIOS, PLANO_ARBOL, PLANO_CANON,
                                       PLANO_ESTADO_LOCAL, PLANO_EXTERNOS, Escenario,
                                       Esperado, Mundo, ServicioExterno,
                                       assert_matriz_completa, hash_arbol, matriz_para)

YO = "nikolai"
ESTA = "ESTA-MAQUINA"

#: Motivo por escrito de que el plano 3 no tenga superficie que inducir aquí.
SIN_SUPERFICIE = (
    "sala_maquina no hace ninguna llamada mutante a CRM, Gmail ni Drive: su motor es "
    "OCR local sobre el arbol ya resuelto. El detector del plano 3 se prueba con el "
    "mutante 3 de TestElArnesMuereEnCadaPlano, no aqui."
)

#: Ninguna fila se declara no aplicable. Se fija como conjunto EXACTO, igual que el
#: techo de `test_guard_localizador`: solo puede cambiar si alguien lo cambia.
NO_APLICABLES: dict[str, str] = {}


# ==========================================================================
# Montaje común
# ==========================================================================

@pytest.fixture
def fabrica_de_mundos(tmp_path):
    """Un `Mundo` nuevo por escenario, cada uno con SU propio `MonkeyPatch`.

    Lo del monkeypatch propio no es un detalle: `Mundo.cerrar()` hace `undo()`, y si
    compartiera el del test desharía también los parches del adaptador a mitad de la
    matriz — un fallo que se habría leído como «el escenario 3 rompe el 4».
    """
    creados: list[Mundo] = []

    def fabricar(nombre: str) -> Mundo:
        mp = pytest.MonkeyPatch()
        m = Mundo(tmp_path / nombre, mp, usuario=YO, maquina=ESTA)
        creados.append(m)
        return m

    try:
        yield fabricar
    finally:
        for m in creados:
            try:
                m.cerrar()
            except Exception:                    # noqa: BLE001 - ya cerrado
                pass


@pytest.fixture
def adaptador(monkeypatch):
    """`invocar` sobre `sala_maquina apply`: identidad o `--case-dir`, y re-resuelve.

    El adaptador **no** recibe workspace, recibe identidad: si el arnés le entregara
    la autorización ya hecha, lo que se probaría sería el arnés.
    """
    monkeypatch.setattr(cli, "_identidad_actor", lambda: (YO, ESTA), raising=False)
    monkeypatch.setattr(cli.sm, "ejecutar", lambda *a, **k: [])
    monkeypatch.setattr(cli, "_atomizar_correo", lambda *a, **k: None)
    monkeypatch.setattr(cli, "_procesar_adjuntos", lambda *a, **k: None)

    def invocar(objetivo):
        if isinstance(objetivo, Path):
            cli.apply(None, case_dir=str(objetivo))
        else:
            cli.apply(objetivo.case_id)
        return 0

    return invocar


def _cablear_fallo(m: Mundo, doble: ServicioExterno) -> None:
    """Fila 9: el doble que falla sustituye al motor, con el `Mundo` como dueño.

    Se instala en el `MonkeyPatch` del mundo y no en el del test a propósito: así se
    deshace al cerrar el escenario y no contamina a los demás.
    """
    m.monkeypatch.setattr(cli.sm, "ejecutar", doble)


# ==========================================================================
# 1. El arnés se prueba a sí mismo: CUATRO mutantes, uno por plano
# ==========================================================================

ESC_NONCE = next(e for e in ESCENARIOS if e.id == "nonce_divergente")


def _instalar_contador(m: Mundo) -> ServicioExterno:
    """Doble que SOLO cuenta, sobre la superficie que el mutante 3 va a tocar."""
    doble = ServicioExterno()
    m.monkeypatch.setattr(cli.sm, "ejecutar", doble)
    return doble


def _copia_local() -> Path:
    from core.casos.workspace_model import CaseRef
    from core.casos.workspace_registry import WorkspaceRegistry, raiz_por_defecto
    reg = WorkspaceRegistry(raiz_por_defecto(), ahora=Mundo.AHORA)
    entradas = reg.buscar(CaseRef(w_code=Mundo.W_CODE))
    assert entradas, "el escenario debía haber sembrado una copia local"
    return Path(entradas[0].local_path)


def _mutante(plano: str, invocar):
    """Adaptador defectuoso: hace el efecto ilícito de UN plano y luego lo normal.

    El escenario es `nonce_divergente` porque es el único de las nueve filas donde
    los cuatro planos son **disjuntos**: hay copia local (plano 1) *y* canon (plano 2)
    *y* registro (plano 4) en tres raíces distintas. En «checkout ajeno», que es el
    escenario obvio, el árbol del caso vive DENTRO del canon y un mutante del plano 1
    mataría también al 2 — el mutante que no prueba lo suyo.
    """
    def defectuoso(objetivo):
        from core import config as cfg
        from core.casos.workspace_registry import raiz_por_defecto
        if plano == PLANO_ARBOL:
            (_copia_local() / "_mutante_arbol.txt").write_text("x", encoding="utf-8")
        elif plano == PLANO_CANON:
            (Path(cfg.settings.casos_root) / "W-FANTASMA").mkdir(exist_ok=True)
        elif plano == PLANO_EXTERNOS:
            cli.sm.ejecutar(None, [])
        elif plano == PLANO_ESTADO_LOCAL:
            raiz = raiz_por_defecto()
            raiz.mkdir(parents=True, exist_ok=True)
            (raiz / "_mutante_sentinel.txt").write_text("x", encoding="utf-8")
        else:                                        # pragma: no cover - defensivo
            raise AssertionError(f"plano desconocido: {plano!r}")
        return invocar(objetivo)

    return defectuoso


class TestElArnesMuereEnCadaPlano:
    """R7/H7-07: si el contrato enumera N fronteras, hacen falta N mutantes.

    El Step original mandaba «introducir a mano **una** escritura en un caso
    bloqueado». Un solo mutante prueba el detector de ficheros y deja el canon, los
    servicios externos y el estado local sin participar en ninguna aserción.
    """

    @pytest.mark.parametrize("plano", [PLANO_ARBOL, PLANO_CANON, PLANO_EXTERNOS,
                                       PLANO_ESTADO_LOCAL])
    def test_el_mutante_muere_POR_SU_PLANO(self, plano, fabrica_de_mundos, adaptador):
        with pytest.raises(AssertionError) as exc:
            matriz_para(_mutante(plano, adaptador), mundo=fabrica_de_mundos,
                        escenarios=(ESC_NONCE,), contador_externo=_instalar_contador)
        mensaje = str(exc.value)
        assert plano in mensaje, (
            f"el mutante del {plano} murió, pero no por su plano:\n{mensaje}")
        otros = [p for p in (PLANO_ARBOL, PLANO_CANON, PLANO_EXTERNOS,
                             PLANO_ESTADO_LOCAL) if p != plano]
        for otro in otros:
            assert otro not in mensaje, (
                f"el mutante del {plano} murió por el aserto del {otro}: ese aserto "
                f"no prueba el plano que dice probar.\n{mensaje}")

    def test_sin_mutante_la_fila_pasa(self, fabrica_de_mundos, adaptador):
        """El control negativo. Sin él, los cuatro de arriba podrían morir por
        cualquier cosa del montaje y yo estaría leyendo el rojo que quiero leer."""
        informe = matriz_para(adaptador, mundo=fabrica_de_mundos,
                              escenarios=(ESC_NONCE,),
                              contador_externo=_instalar_contador)
        assert list(informe) == ["nonce_divergente"]


class TestElArnesNoSeDejaCallar:
    """Las cuatro formas de tener una matriz verde que no prueba la matriz."""

    def test_una_fila_no_aplicable_sin_motivo_se_rechaza(self, fabrica_de_mundos,
                                                         adaptador):
        with pytest.raises(ValueError, match="sin motivo"):
            matriz_para(adaptador, mundo=fabrica_de_mundos,
                        sin_superficie_externa=SIN_SUPERFICIE,
                        no_aplicables={"conflicto": "   "})

    def test_el_plano_3_sin_contador_ni_motivo_se_rechaza(self, fabrica_de_mundos,
                                                          adaptador):
        with pytest.raises(ValueError, match="plano 3"):
            matriz_para(adaptador, mundo=fabrica_de_mundos,
                        escenarios=(ESC_NONCE,))

    def test_la_fila_9_sin_doble_se_rechaza(self, fabrica_de_mundos, adaptador):
        """R7/H7-08: sin mecanismo, la fila existe y el fallo externo no se induce."""
        fila9 = next(e for e in ESCENARIOS if e.id == "servicio_externo_falla")
        with pytest.raises(ValueError, match="R7/H7-08"):
            matriz_para(adaptador, mundo=fabrica_de_mundos, escenarios=(fila9,),
                        sin_superficie_externa=SIN_SUPERFICIE)

    def test_un_informe_incompleto_no_pasa_por_completo(self):
        with pytest.raises(AssertionError, match="Sin cubrir"):
            assert_matriz_completa({"drive_disponible": "ok"})

    def test_una_fila_sin_veredicto_no_pasa(self):
        completo = {e.id: "" for e in ESCENARIOS}
        with pytest.raises(AssertionError, match="no dejó veredicto"):
            assert_matriz_completa(completo)


def test_los_escenarios_son_las_NUEVE_filas_del_14_1():
    """Doble aserto —longitud **y** conjunto—, que es la lección de R7/H7-06.

    «28 + 5 no son 32»: una comprobación de longitud sola pasa con una fila repetida
    y otra ausente, y una de conjunto sola pasa con duplicados.
    """
    esperadas = [
        "drive_disponible", "checkout_propio", "checkout_ajeno", "scratch_local",
        "conflicto", "registro_local_ausente", "nonce_divergente",
        "runtime_sin_acceso", "servicio_externo_falla",
    ]
    ids = [e.id for e in ESCENARIOS]
    assert len(ids) == 9
    assert ids == esperadas
    assert len(set(ids)) == 9
    # Cada fila declara su texto del §14.1: sin él, el `id` es un nombre inventado
    # que nadie puede contrastar contra la spec.
    assert all(e.fila.strip() for e in ESCENARIOS)


def test_hash_arbol_ve_los_DIRECTORIOS(tmp_path):
    """Una carpeta fantasma vacía no tiene ni un byte: si la huella solo mirara
    ficheros, el defecto que la Fase 1 existe para cerrar sería indetectable."""
    antes = hash_arbol(tmp_path)
    (tmp_path / "W-FANTASMA").mkdir()
    assert hash_arbol(tmp_path) != antes


def test_hash_arbol_excluye_la_copia_de_trabajo(tmp_path):
    """La separabilidad del plano 2, que es lo que hace posible la prueba de mutación."""
    (tmp_path / "caso" / "sub").mkdir(parents=True)
    antes = hash_arbol(tmp_path, excluir=tmp_path / "caso")
    (tmp_path / "caso" / "sub" / "nuevo.txt").write_text("x", encoding="utf-8")
    assert hash_arbol(tmp_path, excluir=tmp_path / "caso") == antes
    (tmp_path / "fantasma").mkdir()
    assert hash_arbol(tmp_path, excluir=tmp_path / "caso") != antes


# ==========================================================================
# 2. `sala_maquina` contra la matriz entera
# ==========================================================================

class TestSalaMaquinaContraLaMatriz:

    def test_las_nueve_filas(self, fabrica_de_mundos, adaptador):
        informe = matriz_para(adaptador, mundo=fabrica_de_mundos,
                              servicio=_cablear_fallo,
                              sin_superficie_externa=SIN_SUPERFICIE,
                              no_aplicables=NO_APLICABLES)
        assert_matriz_completa(informe, no_aplicables=NO_APLICABLES)

    def test_ninguna_fila_se_declara_no_aplicable(self):
        """Fijado como conjunto exacto: la cobertura ausente solo puede aparecer si
        alguien la escribe aquí, y entonces hay que justificarla."""
        assert NO_APLICABLES == {}


class TestLaFilaOchoEsRealYNoUnDoble:
    """La 8 dejó de ser indatable al construir `_drive_accesible`."""

    def test_offline_por_variable_de_entorno(self, monkeypatch, tmp_path):
        monkeypatch.setenv("FEESDEFENDER_OFFLINE", "1")
        assert cli._drive_accesible() is False

    def test_catalogo_desmontado(self, monkeypatch, tmp_path):
        monkeypatch.delenv("FEESDEFENDER_OFFLINE", raising=False)
        monkeypatch.setenv("CASOS_ROOT", str(tmp_path / "no-existe"))
        import importlib

        from core import config as cfg
        importlib.reload(cfg)
        try:
            assert cli._drive_accesible() is False
        finally:
            monkeypatch.undo()
            importlib.reload(cfg)

    def test_con_catalogo_montado_y_sin_bandera_hay_drive(self, monkeypatch, tmp_path):
        monkeypatch.delenv("FEESDEFENDER_OFFLINE", raising=False)
        monkeypatch.setenv("CASOS_ROOT", str(tmp_path))
        import importlib

        from core import config as cfg
        importlib.reload(cfg)
        try:
            assert cli._drive_accesible() is True
        finally:
            monkeypatch.undo()
            importlib.reload(cfg)

    def test_el_resolver_ya_no_recibe_un_True_literal(self):
        """Guard de regresión sobre la fuente: el literal era el que mataba la fila.

        No se comprueba por comportamiento porque el comportamiento es idéntico
        mientras el catálogo esté montado — que es el 100 % de las corridas de la
        suite. Lo que hay que impedir es que el literal **vuelva**.
        """
        import io
        fuente = io.open(cli.__file__, encoding="utf-8").read()
        assert "drive_accesible=True" not in fuente, (
            "`drive_accesible=True` literal deja la rama offline del §7.2.9-10 "
            "inalcanzable y la fila 8 de la matriz sin inducir")
        assert fuente.count("drive_accesible=drive_ok") == 2, (
            "las DOS vías de resolución —por identidad y por ruta— consultan la "
            "costura; si una se queda con el literal, la fila 8 solo cubre la otra")
