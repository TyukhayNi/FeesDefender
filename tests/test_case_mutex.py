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
