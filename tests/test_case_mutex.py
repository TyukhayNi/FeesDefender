"""Contrato unitario de la primitiva de mutex por caso (decisión D2 del §24)."""
from __future__ import annotations

import io
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
AHORA = "2026-08-25T12:00:00Z"
W = "W-MUTEX1"


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


def _requisitos() -> dict[str, str]:
    """`{nombre: especificador}` parseado de verdad, no por subcadena.

    `"filelock" in texto` pasaría con el nombre dentro de un comentario o como
    subcadena de otro paquete (R10/H10-10). `packaging` es la única lectura que
    acredita que un clon instalaría algo.
    """
    from packaging.requirements import Requirement
    reqs = {}
    for linea in io.open(RAIZ / "requirements.txt", encoding="utf-8"):
        linea = linea.split("#", 1)[0].strip()
        if not linea:
            continue
        r = Requirement(linea)
        reqs[r.name.lower().replace("_", "-")] = str(r.specifier)
    return reqs


def test_filelock_esta_declarado_con_version_fijada():
    reqs = _requisitos()
    assert "filelock" in reqs, (
        "core/casos/case_mutex.py importa filelock y requirements.txt no lo declara")
    assert ">=3.29" in reqs["filelock"], (
        "la versión se fija: el backend Windows se midió en 3.29.0 y `>=3.12` no lo "
        "reproduce (R10/H10-06)")


def test_psutil_NO_se_declara():
    """Se retiró con el `boot_id` (§0.2). Un requisito sin importador es ruido."""
    assert "psutil" not in _requisitos()


class TestElRelojNoSeAceptaACiegas:
    """R10/H10-02: un timestamp sin zona se lee en hora LOCAL.

    Medido: `2026-08-25T12:00:00` y `...Z` difieren en **7.200 s**. Con el lease por
    defecto, el segundo proceso da por vencido el lock del primero al instante.
    """

    def test_un_timestamp_SIN_offset_se_rechaza(self):
        from core.casos.case_mutex import _instante
        with pytest.raises(ValueError, match="offset"):
            _instante("2026-08-25T12:00:00")

    @pytest.mark.parametrize("ts", ["2026-08-25T12:00:00Z",
                                    "2026-08-25T14:00:00+02:00"])
    def test_con_offset_son_el_MISMO_instante(self, ts):
        from core.casos.case_mutex import _instante
        assert _instante(ts) == _instante("2026-08-25T12:00:00Z")

    def test_una_cadena_que_no_es_fecha_se_rechaza(self):
        from core.casos.case_mutex import _instante
        with pytest.raises(ValueError):
            _instante("ahora mismo")


class TestElLeaseNoAceptaValoresQueLoRompen:
    """R10/H10-03: `int(0.5)` es 0 y `-1` vence al instante."""

    @pytest.mark.parametrize("malo", [0, -1, 0.5, True, False, "60", None])
    def test_valores_que_permitirian_dos_titulares(self, malo):
        from core.casos.case_mutex import _lease_valido
        with pytest.raises((TypeError, ValueError)):
            _lease_valido(malo)

    def test_un_entero_positivo_pasa(self):
        from core.casos.case_mutex import _lease_valido
        assert _lease_valido(300) == 300


class TestElWCodeNoPuedeEscaparDeLaRaiz:
    """R10/H10-08: `..\escape` resolvia FUERA del registro. El revisor lo ejecuto."""

    @pytest.mark.parametrize("malo", ["", "   ", "..", r"..\escape", "C:/tmp/escape",
                                      "W-A/B", "W-A B", "CON", "W-", "sin-prefijo"])
    def test_un_w_code_que_no_lo_es_se_rechaza(self, malo):
        from core.casos.case_mutex import _w_code_valido
        with pytest.raises(ValueError):
            _w_code_valido(malo)

    def test_se_canoniza_a_mayusculas(self):
        from core.casos.case_mutex import _w_code_valido
        assert _w_code_valido(" w-test01 ") == "W-TEST01"


class TestIdentidadDeProceso:
    """El propietario es DIAGNOSTICO: la titularidad la decide el nonce (§0.2)."""

    def test_es_estable_dentro_del_proceso(self):
        from core.casos.case_mutex import identidad_proceso
        assert identidad_proceso() == identidad_proceso()

    def test_NO_depende_del_reloj(self):
        """R10/H10-07: `psutil.boot_time()` cambia con NTP y con la hibernacion."""
        import inspect
        from core.casos import case_mutex
        fuente = inspect.getsource(case_mutex.identidad_proceso)
        assert "boot_time" not in fuente and "psutil" not in fuente

    def test_distingue_un_PID_reutilizado(self):
        from core.casos.case_mutex import identidad_proceso
        yo = identidad_proceso()
        impostor = {"host": yo.host, "pid": yo.pid, "proceso_uid": "otro"}
        assert yo.es_el_mismo(impostor) is False


class TestAdquirir:

    def test_escribe_el_estado_que_D2_exige(self, raiz):
        from core.casos.case_mutex import adquirir, identidad_proceso, leer_estado
        nonce = adquirir(W, ahora=AHORA, raiz=raiz)
        estado = leer_estado(W, raiz=raiz)
        assert estado["nonce"] == nonce and nonce
        assert estado["acquired_at"] == estado["renewed_at"] == AHORA
        assert estado["lease_seconds"] == 300
        assert identidad_proceso().es_el_mismo(estado["propietario"])

    def test_un_segundo_adquirir_con_lease_vivo_lanza_CASE_BUSY(self, raiz):
        from core.casos.case_mutex import adquirir
        from core.casos.workspace_model import CaseBusy
        adquirir(W, ahora=AHORA, raiz=raiz)
        with pytest.raises(CaseBusy):
            adquirir(W, ahora="2026-08-25T12:00:30Z", raiz=raiz)

    def test_dos_W_codes_distintos_no_se_excluyen(self, raiz):
        from core.casos.case_mutex import adquirir
        adquirir("W-AAA111", ahora=AHORA, raiz=raiz)
        adquirir("W-BBB222", ahora=AHORA, raiz=raiz)

    def test_el_registro_no_confunde_el_lock_con_una_entrada(self, raiz):
        """El Task 5 de la Fase 1 dejo sitio a proposito: `cargar()` recorre `*.json`."""
        from core.casos.case_mutex import adquirir
        from core.casos.workspace_registry import WorkspaceRegistry
        adquirir(W, ahora=AHORA, raiz=raiz)
        assert WorkspaceRegistry(raiz, ahora=AHORA).cargar() == []

    def test_un_ahora_SIN_offset_no_llega_a_escribir(self, raiz):
        """R10/H10-02, en la puerta de entrada: se valida ANTES de crear nada."""
        from core.casos.case_mutex import adquirir, ruta_del_lock
        with pytest.raises(ValueError):
            adquirir(W, ahora="2026-08-25T12:00:00", raiz=raiz)
        assert not ruta_del_lock(W, raiz=raiz).exists()


class TestElLease:

    def test_caducado_se_puede_tomar(self, raiz):
        from core.casos.case_mutex import adquirir
        adquirir(W, ahora="2026-08-25T12:00:00Z", raiz=raiz, lease_seconds=60)
        assert adquirir(W, ahora="2026-08-25T12:01:01Z", raiz=raiz)

    def test_renovar_lo_alarga_y_lo_defiende(self, raiz):
        from core.casos.case_mutex import adquirir, renovar
        from core.casos.workspace_model import CaseBusy
        nonce = adquirir(W, ahora="2026-08-25T12:00:00Z", raiz=raiz, lease_seconds=60)
        renovar(W, nonce=nonce, ahora="2026-08-25T12:00:50Z", raiz=raiz)
        with pytest.raises(CaseBusy):
            adquirir(W, ahora="2026-08-25T12:01:01Z", raiz=raiz)

    def test_el_abandono_NO_se_decide_por_el_PID(self, raiz):
        """El corazon de H3-02: el sistema reutiliza PIDs tras un reinicio."""
        import json
        from core.casos.case_mutex import adquirir, ruta_del_lock
        from core.casos.workspace_model import CaseBusy
        adquirir(W, ahora="2026-08-25T12:00:00Z", raiz=raiz, lease_seconds=600)
        p = ruta_del_lock(W, raiz=raiz)
        estado = json.loads(p.read_text(encoding="utf-8"))
        estado["propietario"]["pid"] = 999999          # un PID que no existe
        p.write_text(json.dumps(estado), encoding="utf-8")
        with pytest.raises(CaseBusy):
            adquirir(W, ahora="2026-08-25T12:05:00Z", raiz=raiz)

    def test_renovar_hacia_ATRAS_se_rechaza(self, raiz):
        """R10/H10-02: sin monotonia, un `ahora` retrasado acorta el lease propio."""
        from core.casos.case_mutex import adquirir, renovar
        nonce = adquirir(W, ahora="2026-08-25T12:00:30Z", raiz=raiz)
        with pytest.raises(ValueError):
            renovar(W, nonce=nonce, ahora="2026-08-25T12:00:00Z", raiz=raiz)

    def test_renovar_con_nonce_ajeno_lanza_MUTEX_NOT_MINE(self, raiz):
        from core.casos.case_mutex import adquirir, renovar
        from core.casos.workspace_model import MutexNotMine
        adquirir(W, ahora=AHORA, raiz=raiz)
        with pytest.raises(MutexNotMine):
            renovar(W, nonce="nonce-de-otro", ahora=AHORA, raiz=raiz)


class TestLiberar:

    def test_con_nonce_ajeno_NO_suelta_el_mutex(self, raiz):
        """El defecto A-1 del frontal —cancelar un lock ajeno— aqui no se repite."""
        from core.casos.case_mutex import adquirir, leer_estado, liberar
        from core.casos.workspace_model import MutexNotMine
        nonce = adquirir(W, ahora=AHORA, raiz=raiz)
        with pytest.raises(MutexNotMine):
            liberar(W, nonce="nonce-de-otro", raiz=raiz)
        assert leer_estado(W, raiz=raiz)["nonce"] == nonce

    def test_dos_veces_no_es_un_error(self, raiz):
        from core.casos.case_mutex import adquirir, liberar
        nonce = adquirir(W, ahora=AHORA, raiz=raiz)
        liberar(W, nonce=nonce, raiz=raiz)
        liberar(W, nonce=nonce, raiz=raiz)

    def test_tras_liberar_otro_puede_entrar(self, raiz):
        from core.casos.case_mutex import adquirir, liberar
        nonce = adquirir(W, ahora=AHORA, raiz=raiz)
        liberar(W, nonce=nonce, raiz=raiz)
        assert adquirir(W, ahora=AHORA, raiz=raiz)


def _esperar_a_que_renueve(raiz, *, intentos: int = 150) -> None:
    """Espera activa acotada. Un `sleep` fijo haria el test lento o inestable."""
    import time
    from core.casos.case_mutex import leer_estado
    for _ in range(intentos):
        estado = leer_estado(W, raiz=raiz)
        if estado and estado["renewed_at"] != estado["acquired_at"]:
            return
        time.sleep(0.02)
    raise AssertionError("el renovador no latio en 3 s")


class TestElGestorRenueva:

    def test_libera_aunque_el_cuerpo_reviente(self, raiz):
        from core.casos.case_mutex import adquirir, leer_estado, tomado
        with pytest.raises(RuntimeError):
            with tomado(W, ahora_fn=lambda: AHORA, raiz=raiz, lease_seconds=60):
                raise RuntimeError("boom")
        assert leer_estado(W, raiz=raiz) is None
        assert adquirir(W, ahora=AHORA, raiz=raiz)

    def test_RENUEVA_mientras_el_cuerpo_corre(self, raiz):
        """El hallazgo critico R10/H10-04: sin esto, el lease vence y otro entra.

        Reloj falso que avanza un minuto por lectura y lease de 1 s, para que el latido
        caiga en fracciones de segundo REALES sin hacer el test lento.
        """
        import itertools
        from core.casos.case_mutex import adquirir, leer_estado, tomado
        from core.casos.workspace_model import CaseBusy

        contador = itertools.count()

        def reloj():
            return f"2026-08-25T12:{next(contador) % 60:02d}:00Z"

        with tomado(W, ahora_fn=reloj, raiz=raiz, lease_seconds=1):
            _esperar_a_que_renueve(raiz)
            estado = leer_estado(W, raiz=raiz)
            assert estado["renewed_at"] != estado["acquired_at"], (
                "el lease no se renovo ni una vez durante el cuerpo")
            with pytest.raises(CaseBusy):
                adquirir(W, ahora=estado["renewed_at"], raiz=raiz)

    def test_el_renovador_para_al_salir(self, raiz):
        """Un hilo que sobreviva al `with` renovaria un lock que ya es de otro."""
        import threading
        from core.casos.case_mutex import tomado
        antes = threading.active_count()
        with tomado(W, ahora_fn=lambda: AHORA, raiz=raiz, lease_seconds=1):
            pass
        assert threading.active_count() == antes
