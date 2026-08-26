"""Contrato de la capa reentrante sobre el mutex por caso — Plan 3A, Task 1.

Diez fronteras, M1-M10, y cada una con su mutante. La que compró R14 es **M8**: el
adquirente puede salir antes que un prestatario de otro hilo, y `case_mutex.tomado()` liga
la liberación al `finally` del que adquirió — así que sin esta capa el primero en salir
libera el lock bajo los pies del que sigue dentro.
"""
from __future__ import annotations

import threading

import pytest

AHORA = "2026-08-26T12:00:00Z"
W = "W-SESION1"
W2 = "W-SESION2"
ESPERA = 5  # segundos: tope de toda barrera, para que un fallo sea rojo y no un cuelgue


def reloj() -> str:
    return AHORA


def ref(w: str = W):
    from core.casos.workspace_model import CaseRef
    return CaseRef(w_code=w)


@pytest.fixture
def raiz(tmp_path):
    return tmp_path / "locks"


@pytest.fixture(autouse=True)
def _reloj_del_sistema_fijo(monkeypatch):
    """Ancla el reloj REAL al `AHORA` del fichero, igual que `test_case_mutex.py`.

    `adquirir` acota el desvío entre el `ahora` inyectado y el del sistema, así que sin
    esto los timestamps fijos caducarían según la hora a la que se corra la suite.
    """
    from core.casos import case_mutex
    monkeypatch.setattr(case_mutex, "_ahora_del_sistema",
                        lambda: case_mutex._instante(AHORA))


@pytest.fixture(autouse=True)
def _mapa_limpio():
    """El mapa de sesiones es estado de MÓDULO, y eso ya nos costó una vez.

    Si un test lo deja sucio, el siguiente hereda una titularidad que no pidió y el
    resultado depende del orden — la misma clase de fuga que `tmp_casos_root` dejaba con
    `core.config` y que en el 65º produjo ocho fallos según la semilla.
    """
    from core.casos import mutex_sesion
    with mutex_sesion._CANDADO:
        mutex_sesion._SESIONES.clear()
    yield
    with mutex_sesion._CANDADO:
        mutex_sesion._SESIONES.clear()


# --------------------------------------------------------------------------- M1

def test_m1_unirse_revalida_contra_el_disco_no_contra_la_memoria(raiz, monkeypatch):
    """M1 — la unión CONSULTA el disco. Rama de éxito.

    Se cuenta la revalidación en vez de comprobar solo que la unión funciona: una unión
    que devolviera la sesión sin mirar el disco pasaría igual, y es justo lo que M6
    demuestra que sería peligroso.
    """
    from core.casos import case_mutex, mutex_sesion

    llamadas = []
    original = case_mutex.SesionMutex.revalidar

    def espia(self):
        llamadas.append(self.w_code)
        return original(self)

    monkeypatch.setattr(case_mutex.SesionMutex, "revalidar", espia)

    with mutex_sesion.sostenido(ref(), ahora_fn=reloj, raiz=raiz):
        assert llamadas == [], "adquirir no debe revalidar: aún no hay nada que revalidar"
        with mutex_sesion.sostenido(ref(), ahora_fn=reloj, raiz=raiz):
            assert llamadas == [W], (
                "unirse a una sesión viva tiene que revalidarla contra el disco "
                "exactamente una vez")


# --------------------------------------------------------------------------- M2

def test_m2_unirse_devuelve_la_misma_sesion_y_no_arranca_otro_latido(raiz):
    """M2 — un segundo hilo de latido sobre el mismo lock es el fallo que la unión evita."""
    from core.casos import mutex_sesion

    def latidos() -> int:
        return sum(1 for h in threading.enumerate() if h.name == f"mutex-{W}")

    with mutex_sesion.sostenido(ref(), ahora_fn=reloj, raiz=raiz) as fuera:
        assert latidos() == 1
        with mutex_sesion.sostenido(ref(), ahora_fn=reloj, raiz=raiz) as dentro:
            assert dentro is fuera, "unirse cede LA sesión, no una copia"
            assert latidos() == 1, "unirse no puede arrancar un segundo renovador"


# --------------------------------------------------------------------------- M3

def test_m3_la_salida_interna_no_libera(raiz):
    """M3 — solo suelta el último. Anidamiento léxico."""
    from core.casos import case_mutex, mutex_sesion

    with mutex_sesion.sostenido(ref(), ahora_fn=reloj, raiz=raiz):
        with mutex_sesion.sostenido(ref(), ahora_fn=reloj, raiz=raiz):
            pass
        assert case_mutex.leer_estado(W, raiz=raiz) is not None, (
            "la salida del bloque interno soltó el lock: el externo sigue dentro")
    assert case_mutex.leer_estado(W, raiz=raiz) is None


# --------------------------------------------------------------------------- M4

def test_m4_la_profundidad_se_decrementa_aunque_el_cuerpo_lance(raiz):
    """M4 — `finally`, no camino feliz.

    Si la cuenta se decrementara solo al salir bien, una excepción dentro del bloque
    interno dejaría la profundidad inflada para siempre y el lock nunca se liberaría.
    """
    from core.casos import case_mutex, mutex_sesion

    with mutex_sesion.sostenido(ref(), ahora_fn=reloj, raiz=raiz):
        with pytest.raises(RuntimeError):
            with mutex_sesion.sostenido(ref(), ahora_fn=reloj, raiz=raiz):
                raise RuntimeError("el cuerpo interno revienta")
        assert case_mutex.leer_estado(W, raiz=raiz) is not None
    assert case_mutex.leer_estado(W, raiz=raiz) is None, (
        "la excepción del bloque interno dejó la profundidad sin decrementar")


# --------------------------------------------------------------------------- M5

def test_m5_otro_w_code_es_sesion_independiente(raiz):
    """M5 — no toda entrada anidada es una unión."""
    from core.casos import case_mutex, mutex_sesion

    with mutex_sesion.sostenido(ref(W), ahora_fn=reloj, raiz=raiz) as s1:
        with mutex_sesion.sostenido(ref(W2), ahora_fn=reloj, raiz=raiz) as s2:
            assert s1 is not s2
            assert case_mutex.leer_estado(W, raiz=raiz) is not None
            assert case_mutex.leer_estado(W2, raiz=raiz) is not None
        assert case_mutex.leer_estado(W2, raiz=raiz) is None, "W2 debía soltarse"
        assert case_mutex.leer_estado(W, raiz=raiz) is not None, "W no era el que salía"


# --------------------------------------------------------------------------- M6

def test_m6_revalidacion_fallida_al_unirse_lanza_y_no_crea_un_lock_nuevo(raiz):
    """M6 — la rama de fallo, y la parte que de verdad importa: **no** adquiere otro.

    Adquirir uno nuevo al ver que el propio se perdió sería el peor resultado posible:
    dos escritores, los dos con nonce válido, los dos creyéndose titulares.
    """
    from core.casos import case_mutex, mutex_sesion
    from core.casos.workspace_model import MutexPerdido

    with pytest.raises(MutexPerdido):
        with mutex_sesion.sostenido(ref(), ahora_fn=reloj, raiz=raiz):
            case_mutex.ruta_del_lock(W, raiz=raiz).unlink()
            with mutex_sesion.sostenido(ref(), ahora_fn=reloj, raiz=raiz):
                pytest.fail("no debería haberse podido unir a una sesión perdida")

    assert case_mutex.leer_estado(W, raiz=raiz) is None, (
        "la unión fallida fabricó un lock nuevo: eso es dos titulares")
    assert mutex_sesion._SESIONES == {}, "el mapa quedó sucio tras la unión fallida"


# --------------------------------------------------------------------------- M7

def test_m7_unirse_entre_hilos_comparte_la_sesion(raiz):
    """M7 — el lock del SO es del PROCESO, así que unirse entre hilos es lo correcto."""
    from core.casos import case_mutex, mutex_sesion

    vistas, fallos = {}, []
    t1_dentro = threading.Event()
    t2_hecho = threading.Event()

    def primero():
        try:
            with mutex_sesion.sostenido(ref(), ahora_fn=reloj, raiz=raiz) as s:
                vistas["t1"] = s
                t1_dentro.set()
                assert t2_hecho.wait(ESPERA), "el segundo hilo no terminó"
        except BaseException as exc:                      # noqa: BLE001
            fallos.append(exc)
            t1_dentro.set()

    def segundo():
        try:
            assert t1_dentro.wait(ESPERA), "el primer hilo no entró"
            with mutex_sesion.sostenido(ref(), ahora_fn=reloj, raiz=raiz) as s:
                vistas["t2"] = s
        except BaseException as exc:                      # noqa: BLE001
            fallos.append(exc)
        finally:
            t2_hecho.set()

    hilos = [threading.Thread(target=primero), threading.Thread(target=segundo)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=ESPERA * 3)
        assert not h.is_alive(), "hilo colgado: la unión entre hilos se bloqueó"

    assert not fallos, f"fallos en los hilos: {fallos!r}"
    assert vistas["t1"] is vistas["t2"], "los dos hilos deben compartir LA sesión"
    assert case_mutex.leer_estado(W, raiz=raiz) is None, "al salir los dos, se suelta"


# --------------------------------------------------------------------------- M8

def test_m8_el_adquirente_puede_salir_antes_que_el_prestatario(raiz):
    """M8 — la frontera que compró R14 (H14-03).

    Orden exacto: `A entra → B entra → A sale → B comprueba y escribe → B sale`.
    `case_mutex.tomado()` para el latido y libera en el `finally` del que adquirió, así
    que sin separar *propietario* de *prestatarios* la salida de A deja a B escribiendo
    sin mutex y autoriza a otro proceso a entrar.
    """
    from core.casos import case_mutex, mutex_sesion

    fallos = []
    a_dentro, b_dentro = threading.Event(), threading.Event()
    a_puede_salir, b_puede_salir = threading.Event(), threading.Event()
    a_salio = threading.Event()

    def a():
        try:
            with mutex_sesion.sostenido(ref(), ahora_fn=reloj, raiz=raiz):
                a_dentro.set()
                assert a_puede_salir.wait(ESPERA)
        except BaseException as exc:                      # noqa: BLE001
            fallos.append(("A", exc))
        finally:
            a_dentro.set()
            a_salio.set()

    def b():
        try:
            assert a_dentro.wait(ESPERA)
            with mutex_sesion.sostenido(ref(), ahora_fn=reloj, raiz=raiz) as s:
                b_dentro.set()
                assert b_puede_salir.wait(ESPERA)
                # A ya salió. El lock TIENE que seguir vivo y siendo nuestro.
                estado = case_mutex.leer_estado(W, raiz=raiz)
                assert estado is not None, (
                    "A soltó el lock al salir y B sigue dentro: exclusión falsa")
                assert estado["nonce"] == s.nonce
                assert s.revalidar(), "B ya no es titular de lo que cree sostener"
        except BaseException as exc:                      # noqa: BLE001
            fallos.append(("B", exc))
        finally:
            b_dentro.set()

    ha, hb = threading.Thread(target=a), threading.Thread(target=b)
    ha.start(); hb.start()
    assert b_dentro.wait(ESPERA), "B no llegó a entrar"
    a_puede_salir.set()
    assert a_salio.wait(ESPERA), "A no salió"
    ha.join(timeout=ESPERA)
    assert case_mutex.leer_estado(W, raiz=raiz) is not None, (
        "el lock murió con la salida de A, que era la única cosa que este test mide")
    b_puede_salir.set()
    hb.join(timeout=ESPERA * 3)
    assert not hb.is_alive() and not ha.is_alive()
    assert not fallos, f"fallos en los hilos: {fallos!r}"
    assert case_mutex.leer_estado(W, raiz=raiz) is None, (
        "al salir el ÚLTIMO prestatario el lock tiene que soltarse")


def test_m8b_el_adquirente_sale_por_excepcion_y_el_prestatario_sigue(raiz):
    """M8-bis — la variante que R14 pidió explícitamente: A sale lanzando.

    Una salida por excepción recorre el mismo `finally`, así que si el cierre estuviera
    atado al adquirente el daño sería idéntico y además silencioso.
    """
    from core.casos import case_mutex, mutex_sesion

    fallos = []
    a_dentro, b_dentro = threading.Event(), threading.Event()
    a_salio, b_puede_salir = threading.Event(), threading.Event()

    def a():
        try:
            with mutex_sesion.sostenido(ref(), ahora_fn=reloj, raiz=raiz):
                a_dentro.set()
                # A tiene que esperar a que B esté DENTRO antes de reventar. La primera
                # versión de este test no lo hacía y A salía antes de que B se uniera:
                # entonces lo que saltaba era la guarda `cerrando` —«no se admiten
                # uniones nuevas»—, que es correcta y no es lo que este test mide.
                assert b_dentro.wait(ESPERA), "B no entró antes de que A reventara"
                raise RuntimeError("A revienta con B dentro")
        except RuntimeError:
            pass
        except BaseException as exc:                      # noqa: BLE001
            fallos.append(("A", exc))
        finally:
            a_dentro.set()
            a_salio.set()

    def b():
        try:
            assert a_dentro.wait(ESPERA)
            with mutex_sesion.sostenido(ref(), ahora_fn=reloj, raiz=raiz) as s:
                b_dentro.set()
                assert b_puede_salir.wait(ESPERA)
                assert case_mutex.leer_estado(W, raiz=raiz) is not None, (
                    "la excepción de A soltó el lock con B dentro")
                assert s.revalidar()
        except BaseException as exc:                      # noqa: BLE001
            fallos.append(("B", exc))
        finally:
            b_dentro.set()

    ha, hb = threading.Thread(target=a), threading.Thread(target=b)
    ha.start()
    assert a_dentro.wait(ESPERA)
    hb.start()
    assert b_dentro.wait(ESPERA), "B no entró"
    # Con B dentro, A ya puede reventar: es lo que estaba esperando.
    assert a_salio.wait(ESPERA), "A no salió"
    ha.join(timeout=ESPERA)
    assert case_mutex.leer_estado(W, raiz=raiz) is not None, (
        "la excepción de A soltó el lock teniendo a B dentro")
    b_puede_salir.set()
    hb.join(timeout=ESPERA * 3)
    assert not hb.is_alive()
    assert not fallos, f"fallos en los hilos: {fallos!r}"
    assert case_mutex.leer_estado(W, raiz=raiz) is None


# --------------------------------------------------------------------------- M9

def test_m9_la_raiz_es_parte_de_la_clave(raiz, tmp_path):
    """M9 — H14-04: el lock lo nombra `(raíz, W-code)`, no el W-code solo.

    Con la clave incompleta, entrar con la misma identidad bajo otra raíz se «uniría» a
    una sesión que sostiene un fichero **distinto**: garantía sobre el lock equivocado.
    """
    from core.casos import case_mutex, mutex_sesion

    otra = tmp_path / "otros_locks"
    with mutex_sesion.sostenido(ref(), ahora_fn=reloj, raiz=raiz) as s1:
        with mutex_sesion.sostenido(ref(), ahora_fn=reloj, raiz=otra) as s2:
            assert s1 is not s2, "misma identidad y otra raíz son sesiones DISTINTAS"
            assert case_mutex.leer_estado(W, raiz=raiz) is not None
            assert case_mutex.leer_estado(W, raiz=otra) is not None
            assert (case_mutex.ruta_del_lock(W, raiz=raiz)
                    != case_mutex.ruta_del_lock(W, raiz=otra))
        assert case_mutex.leer_estado(W, raiz=otra) is None
        assert case_mutex.leer_estado(W, raiz=raiz) is not None


def test_m9b_la_misma_raiz_escrita_de_dos_formas_es_una_sola_sesion(raiz):
    """M9-bis — la otra mitad: equivalente no es distinto.

    Si la clave no normalizara, `locks` y `locks/./` serían dos sesiones sobre EL MISMO
    fichero, y la segunda chocaría contra el lock de la primera (o peor, se creería
    titular). Se usa la misma normalización léxica con la que se compone la ruta del lock.
    """
    from core.casos import mutex_sesion

    equivalente = raiz / "." / ".." / raiz.name
    with mutex_sesion.sostenido(ref(), ahora_fn=reloj, raiz=raiz) as s1:
        with mutex_sesion.sostenido(ref(), ahora_fn=reloj, raiz=equivalente) as s2:
            assert s1 is s2, (
                "dos grafías de la misma raíz tienen que dar UNA sesión; si no, la "
                "segunda compite con la primera por su propio fichero")


# -------------------------------------------------------------------------- M10

def test_m10_vigente_distingue_los_tres_estados(raiz):
    """M10 — `vigente()` es lo que consume la costura, y «perdido» no es «no tener».

    Colapsar los dos en `None` haría que la costura tratara una pérdida a mitad de
    operación como si nunca hubiera habido mutex — que en modo `libre` significa
    «escribe y cuéntalo» en vez de «para».
    """
    from core.casos import case_mutex, mutex_sesion
    from core.casos.workspace_model import MutexPerdido

    # (1) nunca lo tuve
    assert mutex_sesion.vigente(ref(), raiz=raiz) is None

    # El `raises` de fuera NO es decoración: perder el mutex a mitad del bloque se
    # denuncia OTRA VEZ al salir, porque `tomado()` no puede liberar lo que ya no es suyo.
    # Que la pérdida se note en los dos sitios es el contrato, no un efecto colateral.
    with pytest.raises(MutexPerdido):
        # (2) lo tengo
        with mutex_sesion.sostenido(ref(), ahora_fn=reloj, raiz=raiz) as s:
            assert mutex_sesion.vigente(ref(), raiz=raiz) is s

            # (3) lo perdí
            case_mutex.ruta_del_lock(W, raiz=raiz).unlink()
            with pytest.raises(MutexPerdido):
                mutex_sesion.vigente(ref(), raiz=raiz)

    assert mutex_sesion._SESIONES == {}, (
        "una sesión perdida dejó entrada en el mapa: el próximo `sostenido` se uniría a "
        "una titularidad inexistente")


def test_m10b_vigente_exige_identidad_resuelta(raiz):
    """M10-bis — sin `w_code` no hay namespace, y no se adivina.

    Resolver la identidad es trabajo de la costura (C0), no de esta capa: aquí un
    `CaseRef` sin W-code es un error de programación, no un caso a tratar.
    """
    from core.casos import mutex_sesion
    from core.casos.workspace_model import CaseRef

    solo_nombre = CaseRef(case_id="Ba001 - x - (W-NOPE1) - t")
    assert solo_nombre.w_code is None
    with pytest.raises(ValueError, match="w_code"):
        mutex_sesion.vigente(solo_nombre, raiz=raiz)
