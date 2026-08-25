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
entrypoint. Se cierra con `_drive_accesible()`, una costura con una condición real y
explícita: `FEESDEFENDER_OFFLINE=1`, el control del operador que el §7.1.5 prevé.

**Y la segunda condición que le añadí duró una corrida.** Puse también «…o la raíz del
catálogo no está montada», mirando `settings.casos_root`. Tres tests de
`test_sala_maquina_ejecutar` la mataron en la primera suite completa: parchean
`case_locator._root` sin tocar el entorno, así que el catálogo encontraba el caso y mi
comprobación decía que no había Drive — un caso disponible abortando con
`RUNTIME_CANNOT_ACCESS_WORKSPACE`. Y en producción era peor: `data/CASOS` no existe en
un clon limpio, así que **toda** invocación se habría ido al modo offline en silencio.
Meter una segunda fuente de verdad sobre dónde está el canon es el defecto, no el
detalle de implementación.

**Y el plano 3 es, para este entrypoint, cierto por vacío.** `sala_maquina` no llama
a ningún servicio externo mutante: hace OCR local. Así que `llamadas == 0` se cumple
sin que nadie lo induzca. El arnés **obliga a decirlo** (`sin_superficie_externa`) en
vez de dejar que el aserto pase en silencio, y el detector del plano 3 se prueba
donde sí se puede: contra el mutante 3 de la primera mitad.
"""
from __future__ import annotations

import re
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

#: Los TRES comandos mutantes de `sala_maquina`. R8/H8-03: la matriz corría solo
#: `apply`, y el §14.1 pide matriz mínima **por entrypoint mutante**, no por fichero.
COMANDOS = ("plan", "apply", "reforzar")

_MOTIVO_PLAN = (
    "`plan` solo escribe cuando detecta un bundle multi-documento (deja "
    "`_segmentacion.md`); con la semilla del arnés —un documento suelto— no escribe "
    "nada, asi que la fila de escritura exigiria montar OCR y split reales. Las cinco "
    "filas BLOQUEADAS, que son las que impiden escribir sobre un caso ajeno, SI corren."
)
_MOTIVO_REFORZAR = (
    "`reforzar` exige transcriptor de vision cableado y cobertura previa; sin eso "
    "aborta en su preflight, que corre DESPUES del guard de workspace. Las cinco filas "
    "BLOQUEADAS SI corren; las de escritura exigirian cablear vision, que es flujo de "
    "skill/sesion y no de suite."
)

#: Qué fila no corre para qué comando, y **por qué**. Se fija como conjunto EXACTO,
#: igual que el techo de `test_guard_localizador`: la cobertura ausente solo puede
#: aparecer si alguien la escribe aquí, y entonces hay que justificarla.
NO_APLICABLES_POR_COMANDO: dict[str, dict[str, str]] = {
    "apply": {},
    "plan": {"drive_disponible": _MOTIVO_PLAN, "checkout_propio": _MOTIVO_PLAN,
             "scratch_local": _MOTIVO_PLAN, "servicio_externo_falla": _MOTIVO_PLAN},
    "reforzar": {"drive_disponible": _MOTIVO_REFORZAR,
                 "checkout_propio": _MOTIVO_REFORZAR,
                 "scratch_local": _MOTIVO_REFORZAR,
                 "servicio_externo_falla": _MOTIVO_REFORZAR},
}


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


def _adaptador_de(comando: str, monkeypatch):
    """`invocar` sobre un comando de `sala_maquina`: identidad o `--case-dir`.

    El adaptador **no** recibe workspace, recibe identidad y **vuelve a resolver**: si
    el arnés le entregara la autorización ya hecha, lo que se probaría sería el arnés.

    Los tres comandos comparten firma en lo que aquí importa —`(case_id, …, case_dir=)`—
    así que un solo adaptador vale para los tres.
    """
    monkeypatch.setattr(cli, "_identidad_actor", lambda: (YO, ESTA), raising=False)
    monkeypatch.setattr(cli.sm, "ejecutar", lambda *a, **k: [])
    monkeypatch.setattr(cli, "_atomizar_correo", lambda *a, **k: None)
    monkeypatch.setattr(cli, "_procesar_adjuntos", lambda *a, **k: None)

    def invocar(objetivo):
        fn = getattr(cli, comando)
        if isinstance(objetivo, Path):
            fn(None, case_dir=str(objetivo))
        else:
            fn(objetivo.case_id)
        return 0

    return invocar


@pytest.fixture
def adaptador(monkeypatch):
    """El de `apply`, que es el que usan las pruebas del propio arnés."""
    return _adaptador_de("apply", monkeypatch)


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


class TestElAbortoTieneQueSerPORSUMOTIVO:
    """R8/H8-01: el juez exigía `codigo != 0` y **cualquier** aborto pasaba.

    El revisor lo midió sustituyendo el adaptador por uno que lanza `typer.Exit(99)`:
    la fila devolvía «cero efectos … salida 99» en verde. Es mi modo de fallo dominante
    en su forma más pura — la fila que dice aislar el `LOCK_MISMATCH` quedaba verde
    aunque el aborto viniera de una guarda completamente distinta.
    """

    def test_un_exit_de_otra_guarda_ya_NO_pasa(self, fabrica_de_mundos, adaptador):
        import typer

        def se_va_por_otra_puerta(objetivo):
            raise typer.Exit(99)

        with pytest.raises(AssertionError, match="motivo EQUIVOCADO|NADA en stderr"):
            matriz_para(se_va_por_otra_puerta, mundo=fabrica_de_mundos,
                        escenarios=(ESC_NONCE,),
                        sin_superficie_externa=SIN_SUPERFICIE)

    def test_un_codigo_del_10_que_no_es_el_suyo_tampoco_pasa(self, fabrica_de_mundos,
                                                             adaptador):
        """Más fino que el anterior: aborta con un código del §10, pero el ajeno."""
        import typer

        def se_confunde_de_error(objetivo):
            typer.echo("[ERROR] [CASE_CONFLICT] — caso W-MTZ01", err=True)
            raise typer.Exit(2)

        with pytest.raises(AssertionError, match="motivo EQUIVOCADO"):
            matriz_para(se_confunde_de_error, mundo=fabrica_de_mundos,
                        escenarios=(ESC_NONCE,),
                        sin_superficie_externa=SIN_SUPERFICIE)

    def test_abortar_en_silencio_tampoco_pasa(self, fabrica_de_mundos, adaptador):
        """Un canal vacío haría vacua la comprobación: el §10 exige presentar el error."""
        import typer

        def calla(objetivo):
            raise typer.Exit(2)

        with pytest.raises(AssertionError, match="NADA en stderr"):
            matriz_para(calla, mundo=fabrica_de_mundos, escenarios=(ESC_NONCE,),
                        sin_superficie_externa=SIN_SUPERFICIE)

    def test_las_cinco_filas_bloqueadas_declaran_su_codigo(self):
        """Sin `codigo_error` la comprobación se autodesactiva: se fija por conjunto."""
        esperados = {
            "checkout_ajeno": "CASE_LOCKED",
            "conflicto": "CASE_CONFLICT",
            "registro_local_ausente": "LOCAL_WORKSPACE_MISSING",
            "nonce_divergente": "LOCK_MISMATCH",
            "runtime_sin_acceso": "RUNTIME_CANNOT_ACCESS_WORKSPACE",
        }
        declarados = {e.id: e.codigo_error for e in ESCENARIOS
                      if e.esperado is Esperado.CERO_EFECTOS}
        assert declarados == esperados
        # Y cada código tiene que existir de verdad en el §10, no ser una cadena bonita.
        from core.casos.workspace_model import errores_conocidos
        del_10 = {c.codigo for c in errores_conocidos()}
        assert set(esperados.values()) <= del_10, (
            f"códigos inventados: {set(esperados.values()) - del_10}")


class TestLaFilaNueveYaNoEsCiega:
    """R8/H8-02: la fila 9 solo comparaba el árbol ENTRE los dos intentos.

    No tomaba baseline previo, no miraba canon ni estado local, y descartaba los
    `(codigo, error)` de las dos invocaciones. El revisor ejecutó dos mutantes y los
    dos quedaron verdes, rotulados «aborto idempotente»: uno incrementaba el estado
    local en cada intento; el otro hacía lo mismo **y además se tragaba el fallo
    externo devolviendo salida 0**.

    Un entrypoint que muta el registro en cada reintento, o que informa de éxito
    aunque el servicio se haya caído, es exactamente lo que esta fila dice descartar.
    """

    FILA9 = tuple(e for e in ESCENARIOS if e.id == "servicio_externo_falla")

    def _contador_creciente(self):
        from core.casos.workspace_registry import raiz_por_defecto
        raiz = raiz_por_defecto()
        raiz.mkdir(parents=True, exist_ok=True)
        marca = raiz / "_mutante_contador.txt"
        n = int(marca.read_text(encoding="utf-8")) if marca.exists() else 0
        marca.write_text(str(n + 1), encoding="utf-8")

    def test_mutar_el_estado_local_en_cada_intento_ya_NO_pasa(self, fabrica_de_mundos,
                                                              adaptador):
        def muta_el_registro(objetivo):
            self._contador_creciente()
            return adaptador(objetivo)

        with pytest.raises(AssertionError, match=re.escape(PLANO_ESTADO_LOCAL)):
            matriz_para(muta_el_registro, mundo=fabrica_de_mundos,
                        servicio=_cablear_fallo, escenarios=self.FILA9,
                        sin_superficie_externa=SIN_SUPERFICIE)

    def test_tragarse_el_fallo_externo_y_devolver_0_ya_NO_pasa(self, fabrica_de_mundos,
                                                               adaptador):
        """El más grave de los dos: éxito informado sobre un servicio caído."""
        def se_traga_el_fallo(objetivo):
            try:
                return adaptador(objetivo)
            except RuntimeError:
                return 0                      # «no ha pasado nada aquí»

        with pytest.raises(AssertionError, match="fallo tragado|ÉXITO"):
            matriz_para(se_traga_el_fallo, mundo=fabrica_de_mundos,
                        servicio=_cablear_fallo, escenarios=self.FILA9,
                        sin_superficie_externa=SIN_SUPERFICIE)

    def test_contaminar_el_canon_durante_el_fallo_ya_NO_pasa(self, fabrica_de_mundos,
                                                             adaptador):
        """El plano 2 en la fila 9: un fallo externo no deja carpetas fantasma."""
        def ensucia_el_canon(objetivo):
            from core import config as cfg
            (Path(cfg.settings.casos_root) / "W-FANTASMA-9").mkdir(exist_ok=True)
            return adaptador(objetivo)

        with pytest.raises(AssertionError, match=re.escape(PLANO_CANON)):
            matriz_para(ensucia_el_canon, mundo=fabrica_de_mundos,
                        servicio=_cablear_fallo, escenarios=self.FILA9,
                        sin_superficie_externa=SIN_SUPERFICIE)

    def test_las_dos_ramas_del_14_1_estan_en_los_datos(self):
        """R8/H8-05: el docstring prometía dos ramas y los datos traían una."""
        fila9 = self.FILA9[0]
        assert fila9.variantes_de_fallo == ((1, 0), (2, 1)), (
            "la fila 9 debe correr las DOS ramas del §14.1: cero publicación "
            "(falla_en=1) y una única publicación estable (falla_en=2)")


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
    """La matriz por **entrypoint mutante**, que son tres y no uno (R8/H8-03)."""

    @pytest.mark.parametrize("comando", COMANDOS)
    def test_la_matriz_del_14_1(self, comando, fabrica_de_mundos, monkeypatch):
        no_aplicables = NO_APLICABLES_POR_COMANDO[comando]
        informe = matriz_para(_adaptador_de(comando, monkeypatch),
                              mundo=fabrica_de_mundos,
                              servicio=_cablear_fallo,
                              sin_superficie_externa=SIN_SUPERFICIE,
                              no_aplicables=no_aplicables)
        assert_matriz_completa(informe, no_aplicables=no_aplicables)

    @pytest.mark.parametrize("comando", COMANDOS)
    def test_las_cinco_filas_BLOQUEADAS_corren_en_los_tres(self, comando):
        """La cobertura que no se negocia: ningún comando puede quedar fuera.

        Las filas de escritura pueden declararse no aplicables con motivo —montar un
        bundle real o cablear visión no es de esta suite—, pero las **bloqueadas** son
        justamente las que impiden escribir sobre el checkout de otro. Si alguna se
        colara en `no_aplicables`, este aserto se pone rojo.
        """
        bloqueadas = {e.id for e in ESCENARIOS if e.esperado is Esperado.CERO_EFECTOS}
        declaradas = set(NO_APLICABLES_POR_COMANDO[comando])
        assert not (bloqueadas & declaradas), (
            f"[{comando}] se declararon no aplicables filas BLOQUEADAS: "
            f"{sorted(bloqueadas & declaradas)}")

    def test_apply_no_declara_ninguna_fila_no_aplicable(self):
        """`apply` es el comando que escribe de verdad: corre la matriz entera."""
        assert NO_APLICABLES_POR_COMANDO["apply"] == {}

    def test_los_comandos_son_TODOS_los_mutantes_del_modulo(self):
        """Un comando nuevo que escriba y no entre aquí es cobertura perdida en silencio.

        Se cuenta por AST sobre el fuente, no por una lista a mano: la lista a mano es
        lo que dejó fuera a `plan` y `reforzar` en primer lugar.
        """
        import ast
        import io as _io

        arbol = ast.parse(_io.open(cli.__file__, encoding="utf-8").read())
        comandos = {
            n.name for n in ast.walk(arbol)
            if isinstance(n, ast.FunctionDef)
            for d in n.decorator_list
            if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
            and d.func.attr == "command"
        }
        assert comandos == set(COMANDOS), (
            f"los comandos Typer del módulo son {sorted(comandos)} y la matriz corre "
            f"{sorted(COMANDOS)}: cada entrypoint mutante necesita su matriz (§14.1)")


class TestPrecedenciaDelCatalogoSobreLaCosturaLegacy:
    """El riesgo que el 65º cierre dejó anotado y NO arreglado, aquí contratado.

    ~28 tests parchean `cli.caso_path` como **override explícito**, y
    `_resolver_workspace` pregunta **primero al catálogo**: el override queda por
    debajo del estado ambiental del canon. Hoy no colisiona porque los `case_id`
    reales son `BaXXX - … - (W-XXXXX) - tipo` y los de esos tests no, pero eso es
    **precedencia por azar de nombres**, no por contrato — y una convención de nombres
    no es una autorización.

    Las dos direcciones se fijan aquí, y son las dos mitades de la misma regla:

    1. si el canon **conoce** el caso, manda el canon, y un `caso_path` parcheado
       **no puede** saltarse un lock;
    2. si el canon **no** lo conoce, manda el binding del módulo — porque donde no hay
       nada que bloquear no hay bloqueo que respetar.

    La primera es la que importa: sin ella, cualquier código que parchee o reconfigure
    `caso_path` se convierte en una vía de escritura sobre un expediente prestado.
    """

    def _mundo(self, tmp_path, monkeypatch) -> Mundo:
        m = Mundo(tmp_path / "precedencia", pytest.MonkeyPatch(),
                  usuario=YO, maquina=ESTA)
        monkeypatch.setattr(cli, "_identidad_actor", lambda: (YO, ESTA), raising=False)
        monkeypatch.setattr(cli.sm, "ejecutar", lambda *a, **k: [])
        monkeypatch.setattr(cli, "_atomizar_correo", lambda *a, **k: None)
        monkeypatch.setattr(cli, "_procesar_adjuntos", lambda *a, **k: None)
        return m

    def test_un_caso_prestado_NO_se_salta_parcheando_caso_path(self, tmp_path,
                                                               monkeypatch):
        import typer
        m = self._mundo(tmp_path, monkeypatch)
        try:
            m.sembrar_canon(estado="prestado", titular="otro.abogado",
                            maquina="OTRA-MAQUINA", nonce="n9")
            desvio = tmp_path / "desvio" / Mundo.CASE_ID
            (desvio / "00_Input").mkdir(parents=True)
            monkeypatch.setattr(cli, "caso_path", lambda cid: desvio)

            antes_desvio = hash_arbol(desvio)
            antes_canon = hash_arbol(m.casos_root)
            with pytest.raises(typer.Exit) as exc:
                cli.apply(Mundo.CASE_ID)
            assert exc.value.exit_code == 2
            assert hash_arbol(desvio) == antes_desvio, (
                "el override de `caso_path` recibió escrituras: la precedencia del "
                "catálogo se ha invertido y un caso prestado es escribible desviando "
                "la ruta")
            assert hash_arbol(m.casos_root) == antes_canon
        finally:
            m.cerrar()

    def test_si_el_canon_NO_conoce_el_caso_manda_el_binding_del_modulo(self, tmp_path,
                                                                      monkeypatch):
        """La otra mitad: sin esto, media suite de sala de máquina caería."""
        m = self._mundo(tmp_path, monkeypatch)
        try:
            fuera = tmp_path / "fuera" / Mundo.CASE_ID
            (fuera / "00_Input").mkdir(parents=True)
            monkeypatch.setattr(cli, "caso_path", lambda cid: fuera)
            antes = hash_arbol(fuera)
            cli.apply(Mundo.CASE_ID)
            assert hash_arbol(fuera) != antes
        finally:
            m.cerrar()


class TestLaFilaOchoEsRealYNoUnDoble:
    """La 8 dejó de ser indatable al construir `_drive_accesible`."""

    def test_offline_por_variable_de_entorno(self, monkeypatch, tmp_path):
        monkeypatch.setenv("FEESDEFENDER_OFFLINE", "1")
        assert cli._drive_accesible() is False

    def test_sin_bandera_hay_drive(self, monkeypatch):
        monkeypatch.delenv("FEESDEFENDER_OFFLINE", raising=False)
        assert cli._drive_accesible() is True

    def test_la_bandera_solo_cuenta_con_el_valor_exacto(self, monkeypatch):
        """`FEESDEFENDER_OFFLINE=0` o vacia NO es offline.

        Una comprobacion por veracidad —`if os.getenv(...)`— haria que el `0` de quien
        cree estar desactivandola la ACTIVARA, que es el modo de fallo clasico de las
        banderas por entorno.
        """
        for valor in ("0", "", "false", "no"):
            monkeypatch.setenv("FEESDEFENDER_OFFLINE", valor)
            assert cli._drive_accesible() is True, f"{valor!r} no deberia ser offline"

    def test_la_comprobacion_NO_mira_la_raiz_del_catalogo(self):
        """Regresion medida: mirar `settings.casos_root` aqui abre dos agujeros.

        Divergia de la fuente que usa el catalogo (`case_locator._root`) y daba
        offline en cualquier clon donde `data/CASOS` no exista. Lo cazaron tres tests
        de `test_sala_maquina_ejecutar` en la primera corrida completa.
        """
        import inspect
        fuente = inspect.getsource(cli._drive_accesible)
        cuerpo = fuente.split('"""')[-1]
        assert "casos_root" not in cuerpo, (
            "`_drive_accesible` volvio a mirar la raiz del catalogo: eso diverge de "
            "`case_locator._root` y da offline en un clon sin `data/CASOS`")

    def test_offline_por_identidad_resuelve_el_CHECKOUT_LOCAL(self, tmp_path):
        """R8/H8-04: la capacidad offline no funcionaba por su vía principal.

        Con la unidad desmontada, `catalogo.localizar` falla, `caso_path` falla detrás
        y el usuario recibía «Caso no encontrado» **teniendo el checkout delante**. El
        §7.2.9-10 existe justo para esto y el resolver ya lo implementaba: lo que
        faltaba era que alguien le pasara la pregunta.

        Verificado en vivo antes de arreglarlo, no deducido del código.
        """
        import importlib

        from core import config as cfg

        mp = pytest.MonkeyPatch()
        m = Mundo(tmp_path / "offline", mp, usuario=YO, maquina=ESTA)
        try:
            local = m.sembrar_local(tipo="checkout", nonce="n1")
            mp.setattr(cli, "_identidad_actor", lambda: (YO, ESTA), raising=False)
            mp.setattr(cli.sm, "ejecutar", lambda *a, **k: [])
            mp.setattr(cli, "_atomizar_correo", lambda *a, **k: None)
            mp.setenv("CASOS_ROOT", str(tmp_path / "offline" / "NO-MONTADO"))
            mp.setenv("FEESDEFENDER_OFFLINE", "1")
            importlib.reload(cfg)

            case_id, ws = cli._resolver_workspace(Mundo.CASE_ID, None)
            assert Path(ws.working_root) == local, (
                "no resolvió sobre la copia local registrada")
            assert ws.mode == "local_checkout"
        finally:
            m.cerrar()

    def test_offline_NO_anuncia_capacidades_que_no_puede_ejercer(self, tmp_path):
        """Y el arreglo de arriba no puede reabrir el defecto que el Task 7 cerró.

        Sin Drive no se puede revalidar el nonce ni publicar, así que un checkout
        resuelto por esa rama **no** conserva `CHECKIN`. Es la misma «resta de
        capacidad» que allí resultó ser inerte: aquí se comprueba que muerde.
        """
        import importlib

        from core import config as cfg
        from core.casos.workspace_model import Capability

        mp = pytest.MonkeyPatch()
        m = Mundo(tmp_path / "offline_caps", mp, usuario=YO, maquina=ESTA)
        try:
            m.sembrar_local(tipo="checkout", nonce="n1")
            mp.setattr(cli, "_identidad_actor", lambda: (YO, ESTA), raising=False)
            mp.setenv("CASOS_ROOT", str(tmp_path / "offline_caps" / "NO-MONTADO"))
            mp.setenv("FEESDEFENDER_OFFLINE", "1")
            importlib.reload(cfg)

            _cid, ws = cli._resolver_workspace(Mundo.CASE_ID, None)
            assert not ws.permite(Capability.CHECKIN), (
                "un checkout sin Drive anuncia CHECKIN: no puede ni revalidar el "
                "nonce ni publicar")
            assert ws.permite(Capability.WRITE_CASE), (
                "…pero sí puede seguir trabajando en local, que es el sentido del §7.1.5")
        finally:
            m.cerrar()

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
        # Se cuenta por INTENCIÓN y no con un número fijo: la primera versión ponía
        # `== 2` y se puso roja al añadir la tercera llamada (la rama offline de
        # R8/H8-04), que es un cambio legítimo. Un guard que caduca al primer cambio
        # correcto es un guard que alguien desactiva.
        llamadas = (fuente.count("resolver.resolver_por_identidad(")
                    + fuente.count("resolver.resolver_por_ruta("))
        assert llamadas >= 2, "esperaba al menos las dos vías de resolución"
        assert fuente.count("drive_accesible=drive_ok") == llamadas, (
            f"{llamadas} llamadas al resolver y solo "
            f"{fuente.count('drive_accesible=drive_ok')} consultan la costura: la que "
            f"se quede con un valor fijo deja su vía fuera de la fila 8")
