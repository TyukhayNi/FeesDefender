"""Las seis regresiones de la revisión R11 sobre el diff del mutex.

## Cómo se obtuvieron, dicho con precisión

**R11 no llegó a emitir informe**: el arnés del revisor se ejecutó entero y produjo sus
siete salidas, pero la redacción del informe la cortó el filtro de contenido de su propia
plataforma (multiproceso + borrado de un lockfile + escape por enlace, leídos como
ataque). Así que **no hay veredicto del revisor**: hay evidencia cruda, y el veredicto
`NO-SHIP` lo firmo yo tras verificar las siete sondas **contra la fuente**, una por una.

Tres las había medido yo antes de que el arnés corriera (renovación tragada, excepción
enmascarada, `Timeout` crudo). **Tres no**, y son las que justifican la ronda:

| Sonda | Salida cruda del arnés | Verificado por mí |
|---|---|---|
| `FUTURE_TAKEOVER` | `True True 2099-01-01T00:00:00Z` | un `ahora` futuro **roba** un lease vivo |
| `INVALID_SCHEMA_ACCEPTED` | `999 {}` | `schema` desconocido y `propietario: {}` pasan |
| `SYMLINK_ESCAPE` | `lexically_safe True … inside_repo_target` | una junction **escapa** la contención |

Y una sonda **no** encontró nada (`GUARD_DELETE` → `WinError 32`): el guard no se puede
borrar mientras se sostiene. Se declara igual, porque un informe que solo lista lo que
falló no permite saber qué se miró.

## Las dos que más duelen, y por qué

**El futuro robando el lease es la mitad de R10/H10-02 que no cerré.** El hallazgo decía
«un `ahora` naïve **o futuro**». Cerré el naïve, añadí monotonía a `renovar`, y di el
crítico por remediado. La mitad que quedaba abierta es justo la que un revisor volvió a
encontrar una ronda después.

**El escape por enlace es una regresión que introduje AL ARREGLAR otra cosa.** La
comprobación de contención era `resolve()`, y la hice **léxica** para matar una carrera
real (dos procesos creando la raíz a la vez resolvían distinto). Al hacerlo dejé de ver a
dónde apunta un enlace. Las dos propiedades son ciertas y se necesitan las dos: la
comprobación **por llamada** tiene que ser léxica, y la de la **raíz** tiene que resolver.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import pytest

W = "W-R11TST"
AHORA = "2026-08-26T10:00:00Z"


@pytest.fixture
def raiz(tmp_path):
    return tmp_path / "locks"


@pytest.fixture(autouse=True)
def _reloj_del_sistema_fijo(monkeypatch):
    """Fija el reloj REAL al `AHORA` del fichero (R11/H11-01).

    `adquirir` y `renovar` rechazan un `ahora` que venga del futuro respecto del reloj
    del sistema, porque sin esa cota un llamador con un bug roba el lease de un titular
    vivo. La costura `_ahora_del_sistema` existe justamente para que eso no convierta
    los tests en dependientes de la hora a la que se corran: aqui se ancla, y los
    timestamps fijos siguen valiendo dentro de su ventana.
    """
    from core.casos import case_mutex
    monkeypatch.setattr(case_mutex, "_ahora_del_sistema",
                        lambda: case_mutex._instante(AHORA))


# ==========================================================================
# H11-01 (CRÍTICO) — un `ahora` futuro roba un lease vivo
# ==========================================================================

class TestUnRelojFuturoNoRobaElLease:
    """R10/H10-02 decía «naïve **o futuro**». Solo cerré la primera mitad.

    El reloj es inyectado, así que la primitiva no puede confiar en él sin más: un
    llamador con un bug —o una máquina con la hora disparatada— se lleva por delante el
    lease de otro proceso que sigue trabajando.
    """

    def test_un_ahora_disparatadamente_futuro_se_rechaza(self, raiz):
        from core.casos.case_mutex import adquirir
        adquirir(W, ahora=AHORA, raiz=raiz, lease_seconds=600)
        with pytest.raises(ValueError, match="futuro|desvío|desvio"):
            adquirir(W, ahora="2099-01-01T00:00:00Z", raiz=raiz, lease_seconds=600)

    def test_el_titular_conserva_su_nonce(self, raiz):
        from core.casos.case_mutex import adquirir, leer_estado
        nonce = adquirir(W, ahora=AHORA, raiz=raiz, lease_seconds=600)
        with pytest.raises(ValueError):
            adquirir(W, ahora="2099-01-01T00:00:00Z", raiz=raiz)
        assert leer_estado(W, raiz=raiz)["nonce"] == nonce

    def test_renovar_hacia_el_futuro_tambien_se_rechaza(self, raiz):
        """Si no, se alarga el lease propio indefinidamente y nadie lo recupera."""
        from core.casos.case_mutex import adquirir, renovar
        nonce = adquirir(W, ahora=AHORA, raiz=raiz, lease_seconds=60)
        with pytest.raises(ValueError):
            renovar(W, nonce=nonce, ahora="2099-01-01T00:00:00Z", raiz=raiz)

    def test_un_desvio_PEQUENO_se_acepta(self, raiz):
        """Control negativo: relojes que difieren en segundos son lo normal."""
        from core.casos.case_mutex import adquirir, renovar
        nonce = adquirir(W, ahora=AHORA, raiz=raiz, lease_seconds=600)
        renovar(W, nonce=nonce, ahora="2026-08-26T10:00:30Z", raiz=raiz)


# ==========================================================================
# H11-02 (CRÍTICO) — el hilo traga el fallo y el cuerpo sigue de titular
# ==========================================================================

class TestPerderElMutexNoSePuedeCallar:
    """El arnés lo midió con dos procesos: `BODY_CONTINUES_AFTER_RENEW_ERROR`,
    `SECOND_ENTERED`, `EXIT:MutexNotMine`.

    O sea: H10-04 —«`tomado()` puede perder el lock y seguir»— **seguía vivo**, movido de
    sitio. El hilo de renovación hacía `except Exception: return`, así que moría callado
    y el cuerpo continuaba escribiendo mientras otro entraba.

    No se puede interrumpir código Python arbitrario a mitad, y eso se declara. Lo que sí
    se puede es **no callarlo**: el cuerpo puede preguntar, y la salida nombra el problema
    real en vez de un `MutexNotMine` que parece un error de programación del llamador.
    """

    def test_el_cuerpo_puede_PREGUNTAR_si_sigue_siendo_titular(self, raiz):
        """La salida lanza `MutexPerdido` —correcto— pero lo que se mide aquí es que el
        cuerpo pudo enterarse **antes** de terminar, que es lo único que le sirve."""
        from core.casos.case_mutex import ruta_del_lock, tomado
        from core.casos.workspace_model import MutexPerdido
        visto = {}
        with pytest.raises(MutexPerdido):
            with tomado(W, ahora_fn=lambda: AHORA, raiz=raiz,
                        lease_seconds=60) as sesion:
                visto["al_entrar"] = sesion.perdido()
                p = ruta_del_lock(W, raiz=raiz)
                estado = json.loads(p.read_text(encoding="utf-8"))
                estado["nonce"] = "de-otro"
                p.write_text(json.dumps(estado), encoding="utf-8")
                sesion.revalidar()
                visto["tras_revalidar"] = sesion.perdido()
        assert visto["al_entrar"] is False
        assert visto["tras_revalidar"] is True, (
            "el cuerpo no tiene forma de enterarse de que perdió el mutex")

    def test_al_salir_el_error_NOMBRA_la_perdida(self, raiz):
        from core.casos.case_mutex import ruta_del_lock, tomado
        from core.casos.workspace_model import MutexPerdido
        with pytest.raises(MutexPerdido):
            with tomado(W, ahora_fn=lambda: AHORA, raiz=raiz, lease_seconds=60):
                p = ruta_del_lock(W, raiz=raiz)
                estado = json.loads(p.read_text(encoding="utf-8"))
                estado["nonce"] = "de-otro"
                p.write_text(json.dumps(estado), encoding="utf-8")

    def test_es_EL_HILO_quien_detecta_la_perdida_sin_que_nadie_pregunte(self, raiz):
        """La vía que los otros dos tests de esta clase NO tocaban.

        Lo destapó una corrida de mutación: al revertir el `marcar_perdido` del hilo
        —o sea, al reponer el `except Exception: return` que ERA el defecto crítico—
        los tres tests de esta clase seguían **verdes**. Pasaban por `revalidar()`,
        que lo llama el cuerpo, y por `liberar()`, que lo llama la salida: dos caminos
        que no son el del hilo.

        Aquí nadie pregunta y nadie libera todavía: se rompe la titularidad en disco, se
        espera a que **lata la renovación**, y se comprueba que el hilo lo registró él
        solo. Si el hilo vuelve a tragarse la excepción, esto se pone rojo y los otros
        tres no.
        """
        import time

        from core.casos.case_mutex import ruta_del_lock, tomado
        from core.casos.workspace_model import MutexPerdido

        detectado_por_el_hilo = {}
        with pytest.raises(MutexPerdido):
            with tomado(W, ahora_fn=lambda: AHORA, raiz=raiz,
                        lease_seconds=1) as sesion:
                p = ruta_del_lock(W, raiz=raiz)
                estado = json.loads(p.read_text(encoding="utf-8"))
                estado["nonce"] = "de-otro"
                p.write_text(json.dumps(estado), encoding="utf-8")
                # Espera acotada a que el latido intente renovar y falle. NO se llama a
                # `revalidar()`: la detección tiene que venir del hilo.
                for _ in range(150):
                    if sesion.perdido():
                        break
                    time.sleep(0.02)
                detectado_por_el_hilo["perdido"] = sesion.perdido()
        assert detectado_por_el_hilo["perdido"] is True, (
            "el hilo de renovación falló y no lo registró: el cuerpo habría seguido "
            "escribiendo como titular sin enterarse (R11/H11-02)")

    def test_MutexPerdido_esta_en_la_tabla_del_10(self):
        from core.casos.workspace_model import MutexPerdido, errores_conocidos
        assert MutexPerdido in errores_conocidos()
        assert MutexPerdido.codigo == "MUTEX_PERDIDO"


# ==========================================================================
# H11-03 (ALTO) — `liberar` en el `finally` enmascara el error del cuerpo
# ==========================================================================

class TestElErrorDelCuerpoNoSeEnmascara:
    """Medido por mí antes del arnés: el llamador veía `MutexNotMine` y **no** su
    `RuntimeError`, así que un `except RuntimeError` suyo no entraba.

    Perder el error de liberación es molesto; perder el del cuerpo es perder la causa.
    """

    def test_si_el_cuerpo_lanza_ese_error_es_el_que_sale(self, raiz):
        from core.casos.case_mutex import ruta_del_lock, tomado
        with pytest.raises(RuntimeError, match="EL ERROR REAL"):
            with tomado(W, ahora_fn=lambda: AHORA, raiz=raiz, lease_seconds=60):
                p = ruta_del_lock(W, raiz=raiz)
                estado = json.loads(p.read_text(encoding="utf-8"))
                estado["nonce"] = "de-otro"
                p.write_text(json.dumps(estado), encoding="utf-8")
                raise RuntimeError("EL ERROR REAL DEL CUERPO")

    def test_si_el_cuerpo_NO_lanza_la_perdida_si_sale(self, raiz):
        """Control negativo: sin él, «tragar siempre» pasaría el test de arriba."""
        from core.casos.case_mutex import ruta_del_lock, tomado
        from core.casos.workspace_model import MutexPerdido
        with pytest.raises(MutexPerdido):
            with tomado(W, ahora_fn=lambda: AHORA, raiz=raiz, lease_seconds=60):
                p = ruta_del_lock(W, raiz=raiz)
                estado = json.loads(p.read_text(encoding="utf-8"))
                estado["nonce"] = "de-otro"
                p.write_text(json.dumps(estado), encoding="utf-8")


# ==========================================================================
# H11-04 (ALTO) — esquema: `schema` desconocido y `propietario` vacío pasan
# ==========================================================================

class TestElEsquemaSeValidaDeVerdad:
    """`INVALID_SCHEMA_ACCEPTED 999 {}`. Mi `_validar_estado` comprobaba que el campo
    `schema` **estuviera**, nunca que valiera lo que esta versión sabe leer — y que
    `propietario` fuera un `dict`, que `{}` cumple.

    El registro de la Fase 1 ya tenía `SchemaNoSoportado` para exactamente esto. No
    usarlo aquí es tener dos vocabularios para el mismo hecho.
    """

    def _sembrar(self, raiz, **cambios):
        from core.casos.case_mutex import adquirir, ruta_del_lock
        adquirir(W, ahora=AHORA, raiz=raiz)
        p = ruta_del_lock(W, raiz=raiz)
        estado = json.loads(p.read_text(encoding="utf-8"))
        estado.update(cambios)
        p.write_text(json.dumps(estado), encoding="utf-8")
        return p

    def test_un_schema_del_futuro_no_se_adivina(self, raiz):
        from core.casos.case_mutex import leer_estado
        from core.casos.workspace_model import MutexIlegible
        self._sembrar(raiz, schema=999)
        with pytest.raises(MutexIlegible):
            leer_estado(W, raiz=raiz)

    def test_un_propietario_VACIO_no_es_un_propietario(self, raiz):
        from core.casos.case_mutex import leer_estado
        from core.casos.workspace_model import MutexIlegible
        self._sembrar(raiz, propietario={})
        with pytest.raises(MutexIlegible):
            leer_estado(W, raiz=raiz)

    def test_un_propietario_a_MEDIAS_tampoco(self, raiz):
        from core.casos.case_mutex import leer_estado
        from core.casos.workspace_model import MutexIlegible
        self._sembrar(raiz, propietario={"host": "h"})
        with pytest.raises(MutexIlegible):
            leer_estado(W, raiz=raiz)

    def test_ninguno_de_los_dos_deja_ADQUIRIR(self, raiz):
        from core.casos.case_mutex import adquirir
        from core.casos.workspace_model import MutexIlegible
        self._sembrar(raiz, schema=999)
        with pytest.raises(MutexIlegible):
            adquirir(W, ahora=AHORA, raiz=raiz)


# ==========================================================================
# H11-05 (ALTO) — una junction escapa la contención léxica
# ==========================================================================

def _crear_junction(enlace: Path, destino: Path) -> bool:
    r = subprocess.run(["cmd", "/c", "mklink", "/J", str(enlace), str(destino)],
                       capture_output=True, text=True)
    return r.returncode == 0


class TestUnEnlaceNoEsUnaPuertaTrasera:
    """Regresión que introduje YO al arreglar la carrera de `resolve()`.

    Las dos propiedades son ciertas a la vez y hacen falta las dos:

    - la comprobación **por llamada** (`ruta_del_lock`) tiene que ser **léxica**, porque
      `resolve()` consulta el disco y devuelve distinto según el directorio exista, y eso
      rompía con dos procesos creando la raíz a la vez;
    - la comprobación de la **raíz** (`raiz_de_locks`) tiene que **resolver**, porque si
      no, una junction al repo o a `CASOS_ROOT` pasa el filtro.

    Arreglar una rompiendo la otra es lo que pasó, y por eso el test las fija juntas.
    """

    def test_una_junction_al_repo_se_rechaza(self, tmp_path):
        from core import config
        from core.casos.case_mutex import raiz_de_locks
        from core.casos.workspace_model import WorkspaceUnderCatalogRoot
        # Apunta a `core/`, que YA EXISTE, en vez de crear un directorio dentro del repo.
        # Este test escribía en el árbol de producción para fabricarse un destino, y era
        # el único que quedaba haciéndolo aparte del guard del localizador (R2 de Codex,
        # H-02: mi primer detector no lo veía). Como el contrato que prueba es «una
        # junction que apunta DENTRO del repo se rechaza», un directorio que ya está
        # dentro sirve igual — y de hecho es un caso más realista que uno fabricado.
        destino = Path(config.settings.project_root) / "core"
        assert destino.is_dir(), (
            "la premisa del test no se cumple: no hay `core/` bajo `project_root`")
        enlace = tmp_path / "raiz_enlazada"
        try:
            if not _crear_junction(enlace, destino):
                pytest.skip("esta máquina no permite crear junctions")
            with pytest.raises(WorkspaceUnderCatalogRoot):
                raiz_de_locks(enlace)
        finally:
            # Solo el enlace, que vive en `tmp_path`. El destino no es nuestro.
            try:
                enlace.rmdir()
            except OSError:
                pass

    def test_una_raiz_normal_fuera_de_las_dos_sigue_valiendo(self, tmp_path):
        """Control negativo: el arreglo no puede rechazar lo legítimo."""
        from core.casos.case_mutex import raiz_de_locks
        assert raiz_de_locks(tmp_path / "locks")

    def test_la_comprobacion_POR_LLAMADA_sigue_sin_tocar_el_disco(self, tmp_path):
        """La otra mitad: si `ruta_del_lock` volviera a `resolve()`, vuelve la carrera.

        Se comprueba sobre la fuente porque el síntoma solo aparece con dos procesos
        compitiendo, y un test que lo reprodujera sería más frágil que el guard.
        """
        import inspect
        from core.casos import case_mutex
        fuente = inspect.getsource(case_mutex.ruta_del_lock)
        assert ".resolve()" not in fuente, (
            "`ruta_del_lock` volvió a resolver contra el disco: eso reabre la carrera "
            "que reventó en la ronda 8 de 12 de la prueba de concurrencia")


# ==========================================================================
# H11-06 (MEDIO) — `filelock.Timeout` sale crudo, fuera del §10
# ==========================================================================

class TestLaEsperaAgotadaEsUnErrorDeLaCasa:
    """`RAW_TIMEOUT filelock.Timeout structured= False`.

    El §10 existe para que toda interfaz presente el mismo error sin cambiar su
    significado. Un `filelock.Timeout` crudo se salta la tabla entera: ni código, ni
    W-code, ni la garantía de que el mensaje no lleva rutas.
    """

    def test_si_la_seccion_critica_esta_ocupada_sale_CASE_BUSY(self, raiz, monkeypatch):
        from filelock import Timeout

        from core.casos import case_mutex
        from core.casos.workspace_model import CaseBusy

        def _guard_ocupado(w_code, raiz_):
            raise Timeout("simulado: otro proceso tiene la sección crítica")

        monkeypatch.setattr(case_mutex, "_abrir_guard", _guard_ocupado)
        with pytest.raises(CaseBusy):
            case_mutex.adquirir(W, ahora=AHORA, raiz=raiz)

    def test_el_mensaje_no_lleva_la_ruta(self, raiz, monkeypatch):
        from filelock import Timeout

        from core.casos import case_mutex
        from core.casos.workspace_model import CaseBusy

        def _guard_ocupado(w_code, raiz_):
            raise Timeout(str(raiz))

        monkeypatch.setattr(case_mutex, "_abrir_guard", _guard_ocupado)
        with pytest.raises(CaseBusy) as exc:
            case_mutex.adquirir(W, ahora=AHORA, raiz=raiz)
        assert str(raiz) not in str(exc.value)
