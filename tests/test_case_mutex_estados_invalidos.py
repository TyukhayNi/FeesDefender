"""El mutex falla CERRADO: «no puedo leerlo» nunca es «está libre» (R10/H10-05).

La rev. 1 del plan **arreglaba** el fail-open y no lo probaba, así que un mutante que lo
revirtiera pasaba entera su suite. Aquí el esquema se valida y hay ocho formas de
romperlo, cada una con su caso.

Lo que se contrata en las tres dimensiones que importan: que el error sea el
estructurado (`MutexIlegible`), que **no deje adquirir** —que es el daño real— y que los
bytes del lock roto **se conserven**, porque un lock ilegible es evidencia de algo y
pisarlo destruye el único rastro de qué pasó.
"""
from __future__ import annotations

import pytest

W = "W-MUTEX1"
AHORA = "2026-08-25T12:00:00Z"

_PROP = (b'"propietario":{"host":"h","pid":1,"proceso_uid":"u"},'
         b'"acquired_at":"2026-08-25T12:00:00Z","renewed_at":"2026-08-25T12:00:00Z"')

ESTADOS_INVALIDOS = {
    "bytes_no_utf8": b"\xff\xfe\x00",
    "json_truncado": b'{"nonce": "abc"',
    "una_lista": b"[]",
    "objeto_vacio": b"{}",
    "propietario_no_objeto": b'{"schema":1,"propietario":"yo","nonce":"a",'
                             b'"acquired_at":"2026-08-25T12:00:00Z",'
                             b'"renewed_at":"2026-08-25T12:00:00Z","lease_seconds":60}',
    "nonce_vacio": b'{"schema":1,' + _PROP + b',"nonce":"","lease_seconds":60}',
    "timestamp_sin_zona": b'{"schema":1,"propietario":{"host":"h","pid":1,'
                          b'"proceso_uid":"u"},"nonce":"a",'
                          b'"acquired_at":"2026-08-25T12:00:00",'
                          b'"renewed_at":"2026-08-25T12:00:00","lease_seconds":60}',
    "lease_no_positivo": b'{"schema":1,' + _PROP + b',"nonce":"a","lease_seconds":-1}',
}


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


def _sembrar(raiz, datos: bytes):
    from core.casos.case_mutex import ruta_del_lock
    p = ruta_del_lock(W, raiz=raiz)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(datos)
    return p


@pytest.mark.parametrize("nombre", sorted(ESTADOS_INVALIDOS))
def test_un_estado_invalido_lanza_MUTEX_ILEGIBLE(raiz, nombre):
    from core.casos.case_mutex import leer_estado
    from core.casos.workspace_model import MutexIlegible
    _sembrar(raiz, ESTADOS_INVALIDOS[nombre])
    with pytest.raises(MutexIlegible):
        leer_estado(W, raiz=raiz)


@pytest.mark.parametrize("nombre", sorted(ESTADOS_INVALIDOS))
def test_un_estado_invalido_NO_deja_adquirir(raiz, nombre):
    """Lo que de verdad importa: un lock roto no abre el caso.

    El test de arriba prueba el error; este prueba la CONSECUENCIA. Sin él, una
    implementación que lanzara en `leer_estado` y lo tragara en `adquirir` pasaría.
    """
    from core.casos.case_mutex import adquirir
    from core.casos.workspace_model import MutexIlegible
    _sembrar(raiz, ESTADOS_INVALIDOS[nombre])
    with pytest.raises(MutexIlegible):
        adquirir(W, ahora=AHORA, raiz=raiz)


@pytest.mark.parametrize("nombre", sorted(ESTADOS_INVALIDOS))
def test_los_bytes_del_estado_roto_se_CONSERVAN(raiz, nombre):
    """Un lock ilegible es evidencia: se diagnostica, no se pisa."""
    from core.casos.case_mutex import adquirir
    from core.casos.workspace_model import MutexIlegible
    original = ESTADOS_INVALIDOS[nombre]
    p = _sembrar(raiz, original)
    with pytest.raises(MutexIlegible):
        adquirir(W, ahora=AHORA, raiz=raiz)
    assert p.read_bytes() == original


def test_sin_fichero_SI_es_None(raiz):
    """Control negativo: sin él, «lanza siempre» pasaría todo lo de arriba."""
    from core.casos.case_mutex import leer_estado
    assert leer_estado(W, raiz=raiz) is None


def test_un_estado_VALIDO_se_lee(raiz):
    """El otro control negativo: que el validador no rechace lo bueno."""
    from core.casos.case_mutex import adquirir, leer_estado
    nonce = adquirir(W, ahora=AHORA, raiz=raiz)
    assert leer_estado(W, raiz=raiz)["nonce"] == nonce


class TestLaRaizNoPuedeVivirDondeSeVeria:
    """La barrera de ubicación, comprobada AQUÍ y no heredada (R10/H10-08).

    La rev. 1 afirmaba que el mutex «hereda» la garantía de `WorkspaceRegistry`. Era
    falso: nunca construye uno — llama a `raiz_por_defecto()` directamente.
    """

    def test_bajo_CASOS_ROOT_se_rechaza(self, tmp_casos_root):
        from core.casos.case_mutex import raiz_de_locks
        from core.casos.workspace_model import WorkspaceUnderCatalogRoot
        with pytest.raises(WorkspaceUnderCatalogRoot):
            raiz_de_locks(tmp_casos_root / "locks")

    def test_bajo_el_repo_se_rechaza(self):
        from core import config
        from core.casos.case_mutex import raiz_de_locks
        from core.casos.workspace_model import WorkspaceUnderCatalogRoot
        with pytest.raises(WorkspaceUnderCatalogRoot):
            raiz_de_locks(config.settings.project_root / "locks")

    def test_fuera_de_las_dos_se_acepta(self, tmp_path):
        from core.casos.case_mutex import raiz_de_locks
        assert raiz_de_locks(tmp_path / "locks") == (tmp_path / "locks").resolve()
