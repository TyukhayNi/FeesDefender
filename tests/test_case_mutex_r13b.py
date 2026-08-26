"""Los seis hallazgos VIVOS de R13, la cuarta ronda sobre el mismo componente.

De los ocho del informe, dos (`H13-02` y `H13-03`) los había cerrado yo en `97670d2`
antes de que llegara: el objeto revisado se archivó antes de ese commit. Se declaran
superados, no refutados. Quedan seis.

## El que justifica la ronda

**H13-01: la cota de desvío protege los leases LARGOS y no los cortos.** `DESVIO_MAXIMO`
son 600 s y `_lease_valido` admite desde 1 s, así que cualquier lease menor que el desvío
tolerado se puede agotar con un reloj **dentro** de lo admitido. Medido: con lease de 60 s,
un `ahora` 300 s adelantado —aceptado sin rechistar— da el lease vivo por caducado y lo
sustituye. Y en sentido contrario igual.

**Y mi propio control negativo de R12 usaba exactamente esa combinación insegura**
(`±5 min` con `lease_seconds=60`) para demostrar que «los desvíos normales se aceptan».
El test que escribí para probar que el arreglo no era demasiado estricto documentaba el
agujero.

Es la cuarta vez seguida con la misma forma: la propiedad no era «el desvío es menor que
600» sino **«el error de reloj no puede agotar el lease que protege»**, y esa relación no
la vi ninguna de las tres veces anteriores.
"""
from __future__ import annotations

import json

import pytest

W = "W-R13BTS"
AHORA = "2026-08-26T12:00:00Z"


@pytest.fixture
def raiz(tmp_path):
    return tmp_path / "locks"


@pytest.fixture(autouse=True)
def _reloj_del_sistema_fijo(monkeypatch):
    from core.casos import case_mutex
    monkeypatch.setattr(case_mutex, "_ahora_del_sistema",
                        lambda: case_mutex._instante(AHORA))


# ==========================================================================
# H13-01 (CRÍTICO) — el desvío tolerado no puede agotar el lease
# ==========================================================================

class TestElDesvioNoPuedeAgotarElLease:

    @pytest.mark.parametrize("ahora_segundo", ["2026-08-26T12:05:00Z",
                                               "2026-08-26T11:55:00Z"])
    def test_un_desvio_MENOR_que_la_cota_no_roba_un_lease_corto(self, raiz,
                                                                ahora_segundo):
        """300 s de desvío están «admitidos», y se llevan por delante un lease de 60 s."""
        from core.casos.case_mutex import adquirir
        from core.casos.workspace_model import CaseBusy
        nonce = adquirir(W, ahora=AHORA, raiz=raiz, lease_seconds=60)
        with pytest.raises((CaseBusy, ValueError)):
            adquirir(W, ahora=ahora_segundo, raiz=raiz, lease_seconds=60)
        from core.casos.case_mutex import leer_estado
        assert leer_estado(W, raiz=raiz)["nonce"] == nonce

    def test_el_desvio_admitido_se_mide_CONTRA_el_lease(self, raiz):
        """La frontera, enunciada: con lease de 60 s, 300 s de reloj es inadmisible."""
        from core.casos.case_mutex import adquirir
        with pytest.raises(ValueError, match="lease"):
            adquirir(W, ahora="2026-08-26T12:05:00Z", raiz=raiz, lease_seconds=60)

    def test_un_lease_LARGO_sigue_tolerando_el_desvio_normal(self, raiz):
        """Control negativo: la cota no puede volverse «cero tolerancia»."""
        from core.casos.case_mutex import adquirir
        assert adquirir(W, ahora="2026-08-26T12:05:00Z", raiz=raiz, lease_seconds=3600)

    def test_la_cota_absoluta_sigue_vigente_para_leases_enormes(self, raiz):
        """Un lease de un año no autoriza un reloj de 2099."""
        from core.casos.case_mutex import adquirir
        with pytest.raises(ValueError):
            adquirir(W, ahora="2099-01-01T00:00:00Z", raiz=raiz,
                     lease_seconds=60 * 60 * 24 * 365)


# ==========================================================================
# H13-04 (MEDIO) — una terminación no se convierte en `MutexPerdido`
# ==========================================================================

def test_un_SystemExit_al_liberar_NO_se_disfraza_de_perdida(raiz, monkeypatch):
    """R12 amplió a `BaseException` el `except` de `liberar`, y con eso se tragaba
    `SystemExit` y `KeyboardInterrupt` para convertirlos en `MutexPerdido`.

    El hilo sí necesita `BaseException` —ahí el objetivo es no morir callado—; la
    liberación no: una terminación tiene que llegar al llamador como lo que es.
    """
    from core.casos import case_mutex
    monkeypatch.setattr(case_mutex, "liberar",
                        lambda *a, **k: (_ for _ in ()).throw(SystemExit("apagando")))
    with pytest.raises(SystemExit):
        with case_mutex.tomado(W, ahora_fn=lambda: AHORA, raiz=raiz, lease_seconds=60):
            pass


def test_un_error_ORDINARIO_al_liberar_sigue_siendo_perdida(raiz, monkeypatch):
    """Control negativo: distinguir terminación de fallo no puede tragarse el fallo."""
    from core.casos import case_mutex
    from core.casos.workspace_model import MutexPerdido
    monkeypatch.setattr(case_mutex, "liberar",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("disco")))
    with pytest.raises(MutexPerdido):
        with case_mutex.tomado(W, ahora_fn=lambda: AHORA, raiz=raiz, lease_seconds=60):
            pass


# ==========================================================================
# H13-05 (MEDIO) — la nota no puede filtrar la ruta
# ==========================================================================

def test_la_nota_de_perdida_no_reproduce_el_texto_de_la_causa(raiz, monkeypatch):
    """H12-04 abrió por la nota la salida que H12-06 acababa de cerrar por la causa.

    Un `OSError` de escritura lleva la ruta en su mensaje, y la nota lo copiaba literal.
    """
    from core.casos import case_mutex
    monkeypatch.setattr(
        case_mutex, "liberar",
        lambda *a, **k: (_ for _ in ()).throw(OSError(f"no puedo escribir {raiz}")))
    with pytest.raises(RuntimeError) as exc:
        with case_mutex.tomado(W, ahora_fn=lambda: AHORA, raiz=raiz, lease_seconds=60):
            raise RuntimeError("del cuerpo")
    notas = getattr(exc.value, "__notes__", [])
    assert notas, "la pérdida tiene que llegar al llamador"
    assert not any(str(raiz) in n for n in notas), f"la ruta viaja en la nota: {notas}"
    assert any("OSError" in n for n in notas), (
        "sanear no puede costar el diagnóstico: el tipo debe constar")


# ==========================================================================
# H13-06 (MEDIO) — los campos desconocidos, también dentro del propietario
# ==========================================================================

def test_un_campo_desconocido_DENTRO_del_propietario_se_rechaza(raiz):
    """La política era «lo que esta versión no entiende, se rechaza». Solo miraba el
    nivel superior, así que el sub-objeto quedaba exento sin decirlo."""
    from core.casos.case_mutex import adquirir, leer_estado, ruta_del_lock
    from core.casos.workspace_model import MutexIlegible
    adquirir(W, ahora=AHORA, raiz=raiz)
    p = ruta_del_lock(W, raiz=raiz)
    estado = json.loads(p.read_text(encoding="utf-8"))
    estado["propietario"]["inventado"] = "x"
    p.write_text(json.dumps(estado), encoding="utf-8")
    with pytest.raises(MutexIlegible):
        leer_estado(W, raiz=raiz)


# ==========================================================================
# H13-07 (BAJO) — el test del reloj tiene que matar la desconexión
# ==========================================================================

def test_la_cota_CONSULTA_de_verdad_la_costura(raiz, monkeypatch):
    """El test anterior comparaba la costura con `time.time()`, pero no probaba que
    `_sin_desvio_absurdo` la **use**: desconectarla no lo mataba."""
    from core.casos import case_mutex
    llamadas = []
    monkeypatch.setattr(case_mutex, "_ahora_del_sistema",
                        lambda: (llamadas.append(1),
                                 case_mutex._instante(AHORA))[1])
    case_mutex._sin_desvio_absurdo(AHORA)
    assert llamadas, "`_sin_desvio_absurdo` no consultó `_ahora_del_sistema`"


# ==========================================================================
# H13-08 (BAJO) — el control negativo de la nota tiene que mirar las notas
# ==========================================================================

def test_el_camino_feliz_no_deja_notas(raiz):
    """`test_sin_perdida_no_se_anota_nada` de R12 solo comprobaba que saliera el error:
    pasaba igual con una nota espuria dentro."""
    from core.casos.case_mutex import tomado
    with pytest.raises(RuntimeError) as exc:
        with tomado(W, ahora_fn=lambda: AHORA, raiz=raiz, lease_seconds=600):
            raise RuntimeError("solo el del cuerpo")
    assert not any("[mutex]" in n for n in getattr(exc.value, "__notes__", []))
